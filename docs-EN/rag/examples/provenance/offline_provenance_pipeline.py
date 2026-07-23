"""Offline source-to-citation provenance lab.

This standard-library project intentionally supports only UTF-8 Markdown whose
line-oriented parser can map extracted text back to exact canonical character
spans.  It demonstrates identities and publication gates; it is not a PDF/OCR,
vector-search, identity-provider, distributed-job, or physical-erasure system.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Sequence


SCHEMA_VERSION = "1.0"
PUBLIC_SCHEMA_VERSION = "provenance-public-v1"
AUDIT_SCHEMA_VERSION = "provenance-audit-v1"
ARTIFACT_SCHEMA_VERSION = "provenance-eval-v2"
HARNESS_REVISION = "offline-provenance-harness-v2"
COORDINATE_SPACE = "canonical-text-lf-nfc-char-v1"
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
MIN_LEXICAL_SCORE = 4
MAX_FIXTURE_BYTES = 4_000_000
MAX_JSON_DEPTH = 64
MAX_SOURCE_BYTES = 100_000
MAX_SOURCE_EVENTS = 256
MAX_QUERIES = 256
MAX_LIST_ITEMS = 128
MAX_TOP_K = 20
MAX_PROCESSED_EVENTS = 10_000


class ContractError(ValueError):
    """Input, lineage, publication, or evidence contract violation."""


def _reject_constant(value: str) -> None:
    raise ContractError(f"JSON does not allow non-finite numbers: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            # Avoid reflecting an untrusted key into terminal/error output.  A
            # JSON-escaped lone surrogate cannot be emitted as strict UTF-8.
            raise ContractError("JSON object contains duplicate keys")
        result[key] = value
    return result


def _reject_invalid_unicode(value: Any) -> None:
    """Reject decoded JSON strings/keys that cannot become evidence UTF-8 bytes."""

    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise ContractError("JSON contains invalid Unicode") from exc
        return
    if isinstance(value, list):
        for item in value:
            _reject_invalid_unicode(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_invalid_unicode(key)
            _reject_invalid_unicode(item)


def _reject_excessive_json_nesting(text: str) -> None:
    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise ContractError(f"JSON container nesting must not exceed {MAX_JSON_DEPTH} levels")
        elif character in "]}":
            depth = max(0, depth - 1)


def strict_json_loads(text: str) -> Any:
    if not isinstance(text, str):
        raise ContractError("JSON boundary must be text")
    try:
        raw = text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ContractError("JSON contains invalid Unicode") from exc
    if len(raw) > MAX_FIXTURE_BYTES:
        raise ContractError(f"JSON must not exceed {MAX_FIXTURE_BYTES} UTF-8 bytes")
    _reject_excessive_json_nesting(text)
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except ContractError:
        raise
    except json.JSONDecodeError as exc:
        raise ContractError(f"JSON could not be parsed: {exc.msg}") from exc
    except RecursionError as exc:
        raise ContractError("JSON nesting exceeds the parser limit") from exc
    except ValueError as exc:
        # CPython can reject an oversized integer before allocating it.  Keep
        # that parser-specific failure on the contract-error path.
        raise ContractError("JSON numeric value exceeds the parser limit") from exc
    _reject_invalid_unicode(parsed)
    return parsed


def canonical_json(value: Any) -> str:
    """Canonical JSON for this deliberately restricted teaching domain.

    This is not an RFC 8785 implementation.  Values are first checked so the
    digest domain contains only JSON null/bool/int/string/list/object values;
    floats are rejected to avoid cross-runtime number ambiguity.
    """

    def check(item: Any, path: str) -> None:
        if item is None or isinstance(item, bool):
            return
        if isinstance(item, str):
            try:
                item.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise ContractError(f"{path} contains invalid Unicode") from exc
            return
        if isinstance(item, int) and not isinstance(item, bool):
            return
        if isinstance(item, float):
            if not math.isfinite(item):
                raise ContractError(f"{path} contains a non-finite number")
            raise ContractError(f"{path} contains a float outside this project's canonical domain")
        if isinstance(item, list) or isinstance(item, tuple):
            for index, child in enumerate(item):
                check(child, f"{path}[{index}]")
            return
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ContractError(f"{path} contains a non-string key")
                try:
                    key.encode("utf-8", errors="strict")
                except UnicodeEncodeError as exc:
                    raise ContractError(f"{path} contains an invalid Unicode key") from exc
                check(child, f"{path}.{key}")
            return
        raise ContractError(f"{path} contains an unsupported type: {type(item).__name__}")

    check(value, "value")
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_text(value: str) -> str:
    try:
        return digest_bytes(value.encode("utf-8", errors="strict"))
    except UnicodeEncodeError as exc:
        raise ContractError("text contains invalid Unicode and cannot produce a UTF-8 digest") from exc


def digest_object(value: Any) -> str:
    return digest_text(canonical_json(value))


def _exact_fields(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ContractError(f"{label} fields mismatch; missing={missing}, extra={extra}")
    return value


def _token(name: str, value: Any, maximum: int = 300) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name} must be a non-empty string")
    cleaned = value.strip()
    if len(cleaned) > maximum or any(ord(char) < 32 for char in cleaned):
        raise ContractError(f"{name} is too long or contains a control character")
    try:
        cleaned.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ContractError(f"{name} contains invalid Unicode") from exc
    return cleaned


def _sha(name: str, value: Any) -> str:
    if not isinstance(value, str) or HEX_64.fullmatch(value) is None:
        raise ContractError(f"{name} must be a complete 64-character lowercase SHA-256")
    return value


def _positive_int(name: str, value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ContractError(f"{name} must be a positive integer")
    return value


def _sorted_unique_strings(
    name: str,
    value: Any,
    *,
    nonempty: bool = True,
    maximum_items: int = MAX_LIST_ITEMS,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ContractError(f"{name} must be an array of strings")
    if len(value) > maximum_items:
        raise ContractError(f"{name} must not exceed {maximum_items} items")
    result = tuple(_token(f"{name}[]", item, 100) for item in value)
    if nonempty and not result:
        raise ContractError(f"{name} must not be empty")
    if tuple(sorted(set(result))) != result:
        raise ContractError(f"{name} must be sorted and unique")
    return result


def normalize_text(value: str) -> str:
    if not isinstance(value, str):
        raise ContractError("content must be a string")
    if "\x00" in value:
        raise ContractError("content must not contain NUL")
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ContractError("content contains invalid Unicode") from exc
    if len(encoded) > MAX_SOURCE_BYTES:
        raise ContractError(f"content must not exceed {MAX_SOURCE_BYTES} UTF-8 bytes")
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))


@dataclass(frozen=True)
class PipelineContract:
    pipeline_revision: str
    normalizer_revision: str
    parser_revision: str
    parser_config: dict[str, Any]
    parser_config_sha256: str
    chunker_revision: str
    index_revision: str
    active_authorization_revision: str
    known_authorization_revisions: tuple[str, ...]
    pipeline_fingerprint: str


@dataclass(frozen=True)
class SourceEvent:
    event_id: str
    kind: str
    connector: str
    tenant_id: str
    document_id: str
    sequence: int
    source_uri: str
    source_version: str
    media_type: str
    content: str | None
    raw_sha256: str | None
    allowed_groups: tuple[str, ...]
    state_sha256: str


@dataclass(frozen=True)
class CanonicalRevision:
    tenant_id: str
    document_id: str
    source_event_id: str
    source_uri: str
    source_version: str
    raw_content: str
    raw_sha256: str
    canonical_text: str
    canonical_text_sha256: str
    normalizer_revision: str
    acl_snapshot_sha256: str
    allowed_groups: tuple[str, ...]
    canonical_revision_id: str


@dataclass(frozen=True)
class Element:
    element_id: str
    parse_revision_id: str
    kind: str
    order: int
    text: str
    text_sha256: str
    coordinate_space: str
    char_start: int
    char_end: int
    section_path: tuple[str, ...]


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    canonical_revision_id: str
    parse_revision_id: str
    chunker_revision: str
    element_id: str
    text: str
    content_sha256: str
    retrieval_text: str
    retrieval_sha256: str
    acl_snapshot_sha256: str
    coordinate_space: str
    char_start: int
    char_end: int


@dataclass(frozen=True)
class IndexEntry:
    index_entry_id: str
    tenant_id: str
    document_id: str
    canonical_revision_id: str
    parse_revision_id: str
    chunk_id: str
    element_id: str
    index_revision: str
    retrieval_text: str
    retrieval_sha256: str
    content_text: str
    content_sha256: str
    allowed_groups: tuple[str, ...]
    acl_snapshot_sha256: str
    coordinate_space: str
    char_start: int
    char_end: int


@dataclass
class DocumentState:
    tenant_id: str
    document_id: str
    source_sequence: int
    event_state_sha256: str
    canonical_revision_id: str | None
    allowed_groups: tuple[str, ...]
    acl_snapshot_sha256: str
    deleted: bool
    access_blocked: bool


@dataclass
class IndexGeneration:
    generation_id: str
    snapshot_state_sha256: str
    tombstone_state_sha256: str
    authorization_revision: str
    pipeline_fingerprint: str
    entries: tuple[IndexEntry, ...]
    entry_set_sha256: str
    manifest_sha256: str
    status: str
    errors: tuple[str, ...]


def parse_contract(value: Any) -> PipelineContract:
    obj = _exact_fields(
        value,
        {
            "pipeline_revision",
            "normalizer_revision",
            "parser_revision",
            "parser_config",
            "chunker_revision",
            "index_revision",
            "authorization",
        },
        "contract",
    )
    parser_config = _exact_fields(
        obj["parser_config"],
        {"media_types", "coordinate_space", "line_oriented"},
        "contract.parser_config",
    )
    if parser_config["media_types"] != ["text/markdown"]:
        raise ContractError("this project declares only text/markdown")
    if parser_config["coordinate_space"] != COORDINATE_SPACE:
        raise ContractError("coordinate_space does not match the implementation")
    if parser_config["line_oriented"] is not True:
        raise ContractError("line_oriented must be true")
    authorization = _exact_fields(
        obj["authorization"],
        {"active_revision", "known_revisions"},
        "contract.authorization",
    )
    known = _sorted_unique_strings(
        "contract.authorization.known_revisions", authorization["known_revisions"]
    )
    active = _token("contract.authorization.active_revision", authorization["active_revision"])
    if active not in known:
        raise ContractError("active authorization revision must be in known_revisions")
    base = {
        "pipeline_revision": _token("pipeline_revision", obj["pipeline_revision"]),
        "normalizer_revision": _token("normalizer_revision", obj["normalizer_revision"]),
        "parser_revision": _token("parser_revision", obj["parser_revision"]),
        "parser_config": parser_config,
        "chunker_revision": _token("chunker_revision", obj["chunker_revision"]),
        "index_revision": _token("index_revision", obj["index_revision"]),
    }
    return PipelineContract(
        pipeline_revision=base["pipeline_revision"],
        normalizer_revision=base["normalizer_revision"],
        parser_revision=base["parser_revision"],
        parser_config=copy.deepcopy(parser_config),
        parser_config_sha256=digest_object(parser_config),
        chunker_revision=base["chunker_revision"],
        index_revision=base["index_revision"],
        active_authorization_revision=active,
        known_authorization_revisions=known,
        pipeline_fingerprint=digest_object(base),
    )


def parse_source_event(value: Any) -> SourceEvent:
    obj = _exact_fields(
        value,
        {
            "event_id",
            "kind",
            "connector",
            "tenant_id",
            "document_id",
            "sequence",
            "source_uri",
            "source_version",
            "media_type",
            "content",
            "raw_sha256",
            "allowed_groups",
        },
        "source_event",
    )
    kind = _token("source_event.kind", obj["kind"])
    if kind not in {"upsert", "delete"}:
        raise ContractError("source_event.kind must be upsert or delete")
    media_type = _token("source_event.media_type", obj["media_type"])
    if media_type != "text/markdown":
        raise ContractError("this project accepts only text/markdown")
    allowed_groups = _sorted_unique_strings(
        "source_event.allowed_groups", obj["allowed_groups"], nonempty=kind == "upsert"
    )
    content = obj["content"]
    raw_sha = obj["raw_sha256"]
    if kind == "upsert":
        if not isinstance(content, str):
            raise ContractError("upsert.content must be a string")
        normalize_text(content)
        declared = _sha("source_event.raw_sha256", raw_sha)
        actual = digest_text(content)
        if declared != actual:
            raise ContractError("source_event.raw_sha256 does not match the UTF-8 source")
        raw_sha = declared
    elif content is not None or raw_sha is not None or allowed_groups:
        raise ContractError("delete must set content/raw_sha256 to null and allowed_groups to an empty array")
    state = {
        "kind": kind,
        "connector": _token("connector", obj["connector"]),
        "tenant_id": _token("tenant_id", obj["tenant_id"]),
        "document_id": _token("document_id", obj["document_id"]),
        "source_uri": _token("source_uri", obj["source_uri"]),
        "source_version": _token("source_version", obj["source_version"]),
        "media_type": media_type,
        "content": content,
        "raw_sha256": raw_sha,
        "allowed_groups": list(allowed_groups),
    }
    return SourceEvent(
        event_id=_token("event_id", obj["event_id"]),
        kind=kind,
        connector=state["connector"],
        tenant_id=state["tenant_id"],
        document_id=state["document_id"],
        sequence=_positive_int("source_event.sequence", obj["sequence"]),
        source_uri=state["source_uri"],
        source_version=state["source_version"],
        media_type=media_type,
        content=content,
        raw_sha256=raw_sha,
        allowed_groups=allowed_groups,
        state_sha256=digest_object(state),
    )


def validate_query(value: Any) -> dict[str, Any]:
    obj = _exact_fields(
        value,
        {
            "query_id",
            "query",
            "tenant_id",
            "subject_groups",
            "authorization_revision",
            "top_k",
        },
        "query",
    )
    result = {
        "query_id": _token("query.query_id", obj["query_id"]),
        "query": _token("query.query", obj["query"], 2000),
        "tenant_id": _token("query.tenant_id", obj["tenant_id"]),
        "subject_groups": list(
            _sorted_unique_strings(
                "query.subject_groups",
                obj["subject_groups"],
                maximum_items=MAX_LIST_ITEMS,
            )
        ),
        "authorization_revision": _token(
            "query.authorization_revision", obj["authorization_revision"]
        ),
        "top_k": _positive_int("query.top_k", obj["top_k"]),
    }
    if result["top_k"] > MAX_TOP_K:
        raise ContractError(f"query.top_k must not exceed {MAX_TOP_K}")
    return result


def load_fixture(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            raw_bytes = handle.read(MAX_FIXTURE_BYTES + 1)
        if len(raw_bytes) > MAX_FIXTURE_BYTES:
            raise ContractError(
                f"fixture must not exceed {MAX_FIXTURE_BYTES} UTF-8 bytes"
            )
        raw = raw_bytes.decode("utf-8", errors="strict")
    except ContractError:
        raise
    except (OSError, UnicodeError) as exc:
        raise ContractError(f"could not read fixture: {type(exc).__name__}") from exc
    fixture = _exact_fields(
        strict_json_loads(raw),
        {"schema_version", "contract", "source_events", "queries", "oracle"},
        "fixture",
    )
    if fixture["schema_version"] != SCHEMA_VERSION:
        raise ContractError(f"only fixture schema {SCHEMA_VERSION} is supported")
    contract = parse_contract(fixture["contract"])
    if (
        not isinstance(fixture["source_events"], list)
        or not 1 <= len(fixture["source_events"]) <= MAX_SOURCE_EVENTS
    ):
        raise ContractError(f"source_events must be an array with 1..{MAX_SOURCE_EVENTS} items")
    events = [parse_source_event(item) for item in fixture["source_events"]]
    event_ids = [item.event_id for item in events]
    if len(event_ids) != len(set(event_ids)):
        raise ContractError("source_event.event_id must be unique")
    if (
        not isinstance(fixture["queries"], list)
        or not 1 <= len(fixture["queries"]) <= MAX_QUERIES
    ):
        raise ContractError(f"queries must be an array with 1..{MAX_QUERIES} items")
    queries = [validate_query(item) for item in fixture["queries"]]
    query_ids = [item["query_id"] for item in queries]
    if len(query_ids) != len(set(query_ids)):
        raise ContractError("query_id must be unique")
    if not isinstance(fixture["oracle"], list):
        raise ContractError("oracle must be an array")
    oracle: list[dict[str, Any]] = []
    for item in fixture["oracle"]:
        entry = _exact_fields(
            item,
            {
                "query_id",
                "expected_status",
                "expected_documents",
                "forbidden_documents",
                "critical",
                "slice",
            },
            "oracle[]",
        )
        query_id = _token("oracle.query_id", entry["query_id"])
        if query_id not in query_ids:
            raise ContractError(f"oracle references an unknown query_id: {query_id}")
        if not isinstance(entry["critical"], bool):
            raise ContractError("oracle.critical must be a boolean")
        expected_status = _token("oracle.expected_status", entry["expected_status"])
        if expected_status not in {"answered", "insufficient_evidence"}:
            raise ContractError("oracle.expected_status is unsupported")
        oracle.append(
            {
                "query_id": query_id,
                "expected_status": expected_status,
                "expected_documents": list(
                    _sorted_unique_strings(
                        "oracle.expected_documents",
                        entry["expected_documents"],
                        nonempty=False,
                    )
                ),
                "forbidden_documents": list(
                    _sorted_unique_strings(
                        "oracle.forbidden_documents",
                        entry["forbidden_documents"],
                        nonempty=False,
                    )
                ),
                "critical": entry["critical"],
                "slice": _token("oracle.slice", entry["slice"]),
            }
        )
    if sorted(item["query_id"] for item in oracle) != sorted(query_ids):
        raise ContractError("each query must have exactly one oracle")
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract": contract,
        "source_events": events,
        "queries": queries,
        "oracle": oracle,
        "fixture_sha256": digest_text(raw),
    }
    result["fixture_model_sha256"] = fixture_model_sha256(result)
    return result


def fixture_model_sha256(fixture: dict[str, Any]) -> str:
    contract = fixture.get("contract")
    events = fixture.get("source_events")
    if not isinstance(contract, PipelineContract) or not isinstance(events, list):
        raise ContractError("fixture model has not passed typed loading")
    return digest_object(
        {
            "schema_version": fixture.get("schema_version"),
            "contract": asdict(contract),
            "source_events": [asdict(item) for item in events],
            "queries": fixture.get("queries"),
            "oracle": fixture.get("oracle"),
        }
    )


def require_fixture_integrity(fixture: dict[str, Any]) -> None:
    supplied = fixture.get("fixture_model_sha256")
    if not isinstance(supplied, str) or HEX_64.fullmatch(supplied) is None:
        raise ContractError("fixture_model_sha256 is missing or invalid")
    if supplied != fixture_model_sha256(fixture):
        raise ContractError("fixture changed after strict loading; it must be validated again")


def _acl_hash(groups: Iterable[str]) -> str:
    return digest_object({"allowed_groups": sorted(groups)})


def _canonical_revision(event: SourceEvent, contract: PipelineContract) -> CanonicalRevision:
    if event.content is None or event.raw_sha256 is None:
        raise ContractError("delete cannot create a canonical revision")
    canonical = normalize_text(event.content)
    canonical_hash = digest_text(canonical)
    acl_hash = _acl_hash(event.allowed_groups)
    identity = {
        "tenant_id": event.tenant_id,
        "document_id": event.document_id,
        "source_uri": event.source_uri,
        "source_version": event.source_version,
        "raw_sha256": event.raw_sha256,
        "canonical_text_sha256": canonical_hash,
        "normalizer_revision": contract.normalizer_revision,
        "acl_snapshot_sha256": acl_hash,
    }
    revision_id = "can_" + digest_object(identity)
    return CanonicalRevision(
        tenant_id=event.tenant_id,
        document_id=event.document_id,
        source_event_id=event.event_id,
        source_uri=event.source_uri,
        source_version=event.source_version,
        raw_content=event.content,
        raw_sha256=event.raw_sha256,
        canonical_text=canonical,
        canonical_text_sha256=canonical_hash,
        normalizer_revision=contract.normalizer_revision,
        acl_snapshot_sha256=acl_hash,
        allowed_groups=event.allowed_groups,
        canonical_revision_id=revision_id,
    )


def _line_spans(text: str) -> Iterable[tuple[str, int, int]]:
    cursor = 0
    for line in text.splitlines(keepends=True):
        body = line[:-1] if line.endswith("\n") else line
        yield body, cursor, cursor + len(body)
        cursor += len(line)
    if not text:
        return
    if text.endswith("\n"):
        return


def parse_elements(
    revision: CanonicalRevision, contract: PipelineContract
) -> tuple[str, tuple[Element, ...]]:
    parse_identity = {
        "canonical_revision_id": revision.canonical_revision_id,
        "parser_revision": contract.parser_revision,
        "parser_config_sha256": contract.parser_config_sha256,
    }
    parse_revision_id = "par_" + digest_object(parse_identity)
    sections: list[str] = []
    elements: list[Element] = []
    for line, line_start, _line_end in _line_spans(revision.canonical_text):
        if not line.strip():
            continue
        match = HEADING_RE.fullmatch(line)
        if match:
            level = len(match.group(1))
            text = match.group(2)
            relative_start = match.start(2)
            kind = "heading"
            sections = sections[: level - 1]
            sections.append(text)
            section_path = tuple(sections)
        else:
            leading = len(line) - len(line.lstrip(" \t"))
            trailing = len(line.rstrip(" \t"))
            text = line[leading:trailing]
            relative_start = leading
            kind = "paragraph"
            section_path = tuple(sections)
        char_start = line_start + relative_start
        char_end = char_start + len(text)
        text_hash = digest_text(text)
        identity = {
            "parse_revision_id": parse_revision_id,
            "kind": kind,
            "coordinate_space": COORDINATE_SPACE,
            "char_start": char_start,
            "char_end": char_end,
            "text_sha256": text_hash,
        }
        elements.append(
            Element(
                element_id="el_" + digest_object(identity),
                parse_revision_id=parse_revision_id,
                kind=kind,
                order=len(elements) + 1,
                text=text,
                text_sha256=text_hash,
                coordinate_space=COORDINATE_SPACE,
                char_start=char_start,
                char_end=char_end,
                section_path=section_path,
            )
        )
    if not elements or not any(item.kind == "paragraph" for item in elements):
        raise ContractError("parse result must contain at least one citable paragraph")
    return parse_revision_id, tuple(elements)


def build_chunks(
    revision: CanonicalRevision,
    parse_revision_id: str,
    elements: Sequence[Element],
    contract: PipelineContract,
) -> tuple[Chunk, ...]:
    chunks: list[Chunk] = []
    for element in elements:
        if element.kind != "paragraph":
            continue
        context = " > ".join(element.section_path)
        retrieval_text = f"title path: {context}\n{element.text}" if context else element.text
        content_hash = digest_text(element.text)
        retrieval_hash = digest_text(retrieval_text)
        identity = {
            "canonical_revision_id": revision.canonical_revision_id,
            "parse_revision_id": parse_revision_id,
            "chunker_revision": contract.chunker_revision,
            "element_id": element.element_id,
            "content_sha256": content_hash,
            "acl_snapshot_sha256": revision.acl_snapshot_sha256,
        }
        chunks.append(
            Chunk(
                chunk_id="chk_" + digest_object(identity),
                canonical_revision_id=revision.canonical_revision_id,
                parse_revision_id=parse_revision_id,
                chunker_revision=contract.chunker_revision,
                element_id=element.element_id,
                text=element.text,
                content_sha256=content_hash,
                retrieval_text=retrieval_text,
                retrieval_sha256=retrieval_hash,
                acl_snapshot_sha256=revision.acl_snapshot_sha256,
                coordinate_space=COORDINATE_SPACE,
                char_start=element.char_start,
                char_end=element.char_end,
            )
        )
    return tuple(chunks)


def build_entries(
    revision: CanonicalRevision,
    parse_revision_id: str,
    chunks: Sequence[Chunk],
    contract: PipelineContract,
) -> tuple[IndexEntry, ...]:
    entries: list[IndexEntry] = []
    for chunk in chunks:
        identity = {
            "chunk_id": chunk.chunk_id,
            "retrieval_sha256": chunk.retrieval_sha256,
            "index_revision": contract.index_revision,
            "acl_snapshot_sha256": revision.acl_snapshot_sha256,
        }
        entries.append(
            IndexEntry(
                index_entry_id="idx_" + digest_object(identity),
                tenant_id=revision.tenant_id,
                document_id=revision.document_id,
                canonical_revision_id=revision.canonical_revision_id,
                parse_revision_id=parse_revision_id,
                chunk_id=chunk.chunk_id,
                element_id=chunk.element_id,
                index_revision=contract.index_revision,
                retrieval_text=chunk.retrieval_text,
                retrieval_sha256=chunk.retrieval_sha256,
                content_text=chunk.text,
                content_sha256=chunk.content_sha256,
                allowed_groups=revision.allowed_groups,
                acl_snapshot_sha256=revision.acl_snapshot_sha256,
                coordinate_space=chunk.coordinate_space,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
            )
        )
    return tuple(entries)


def _snapshot_rows(documents: dict[tuple[str, str], DocumentState]) -> list[dict[str, Any]]:
    return [
        {
            "tenant_id": state.tenant_id,
            "document_id": state.document_id,
            "source_sequence": state.source_sequence,
            "canonical_revision_id": state.canonical_revision_id,
            "acl_snapshot_sha256": state.acl_snapshot_sha256,
            "deleted": state.deleted,
        }
        for _key, state in sorted(documents.items())
    ]


class ProvenanceEngine:
    def __init__(self, contract: PipelineContract):
        self.contract = contract
        self.active_authorization_revision = contract.active_authorization_revision
        self.documents: dict[tuple[str, str], DocumentState] = {}
        self.revisions: dict[str, CanonicalRevision] = {}
        self.elements: dict[str, tuple[Element, ...]] = {}
        self.chunks: dict[str, tuple[Chunk, ...]] = {}
        self.tombstones: dict[tuple[str, str], int] = {}
        self.generations: dict[str, IndexGeneration] = {}
        self.published_generation_id: str | None = None
        self.processed_event_sha256: dict[str, str] = {}

    def apply_event(self, event_or_value: SourceEvent | dict[str, Any]) -> str:
        event = (
            event_or_value
            if isinstance(event_or_value, SourceEvent)
            else parse_source_event(event_or_value)
        )
        event_fingerprint = digest_object(asdict(event))
        previous_event_fingerprint = self.processed_event_sha256.get(event.event_id)
        if previous_event_fingerprint is not None:
            if previous_event_fingerprint == event_fingerprint:
                return "noop"
            raise ContractError("the same event_id cannot bind different source events")
        if len(self.processed_event_sha256) >= MAX_PROCESSED_EVENTS:
            raise ContractError(
                "processed-event deduplication window is full; persist or rotate it before accepting new events"
            )

        def remember(action: str) -> str:
            self.processed_event_sha256[event.event_id] = event_fingerprint
            return action

        key = (event.tenant_id, event.document_id)
        previous = self.documents.get(key)
        if previous is not None:
            if event.sequence < previous.source_sequence:
                return remember("stale_ignored")
            if event.sequence == previous.source_sequence:
                if event.state_sha256 == previous.event_state_sha256:
                    return remember("noop")
                raise ContractError("the same source sequence maps to a different state")
            if event.state_sha256 == previous.event_state_sha256:
                previous.source_sequence = event.sequence
                return remember("checkpoint_advanced")

        if event.kind == "delete":
            if previous is None:
                acl_hash = _acl_hash(())
                self.documents[key] = DocumentState(
                    event.tenant_id,
                    event.document_id,
                    event.sequence,
                    event.state_sha256,
                    None,
                    (),
                    acl_hash,
                    True,
                    True,
                )
            else:
                previous.source_sequence = event.sequence
                previous.event_state_sha256 = event.state_sha256
                previous.deleted = True
                previous.access_blocked = True
                previous.allowed_groups = ()
                previous.acl_snapshot_sha256 = _acl_hash(())
            self.tombstones[key] = event.sequence
            return remember("deleted")

        revision = _canonical_revision(event, self.contract)
        self.revisions.setdefault(revision.canonical_revision_id, revision)
        acl_changed = previous is not None and previous.acl_snapshot_sha256 != revision.acl_snapshot_sha256
        resurrected = previous is not None and previous.deleted
        already_blocked = previous is not None and previous.access_blocked
        state = DocumentState(
            tenant_id=event.tenant_id,
            document_id=event.document_id,
            source_sequence=event.sequence,
            event_state_sha256=event.state_sha256,
            canonical_revision_id=revision.canonical_revision_id,
            allowed_groups=revision.allowed_groups,
            acl_snapshot_sha256=revision.acl_snapshot_sha256,
            deleted=False,
            access_blocked=acl_changed or resurrected or already_blocked,
        )
        self.documents[key] = state
        return remember("upserted")

    def capture_snapshot(self) -> dict[str, Any]:
        rows = _snapshot_rows(self.documents)
        tombstones = [
            {"tenant_id": key[0], "document_id": key[1], "sequence": sequence}
            for key, sequence in sorted(self.tombstones.items())
        ]
        return {
            "documents": copy.deepcopy(rows),
            "snapshot_state_sha256": digest_object(rows),
            "tombstone_state_sha256": digest_object(tombstones),
        }

    def rotate_authorization(self, revision: str) -> None:
        revision = _token("authorization_revision", revision)
        if revision not in self.contract.known_authorization_revisions:
            raise ContractError("unknown authorization revision")
        self.active_authorization_revision = revision

    def stage_generation(
        self,
        *,
        authorization_revision: str | None = None,
        snapshot: dict[str, Any] | None = None,
        failure: str | None = None,
    ) -> IndexGeneration:
        auth = authorization_revision or self.active_authorization_revision
        if auth not in self.contract.known_authorization_revisions:
            raise ContractError("unknown authorization revision")
        captured = copy.deepcopy(snapshot) if snapshot is not None else self.capture_snapshot()
        _exact_fields(
            captured,
            {"documents", "snapshot_state_sha256", "tombstone_state_sha256"},
            "snapshot",
        )
        _sha("snapshot_state_sha256", captured["snapshot_state_sha256"])
        _sha("tombstone_state_sha256", captured["tombstone_state_sha256"])
        if digest_object(captured["documents"]) != captured["snapshot_state_sha256"]:
            raise ContractError("snapshot documents do not match the snapshot hash")
        entries: list[IndexEntry] = []
        errors: list[str] = []
        for row in captured["documents"]:
            row = _exact_fields(
                row,
                {
                    "tenant_id",
                    "document_id",
                    "source_sequence",
                    "canonical_revision_id",
                    "acl_snapshot_sha256",
                    "deleted",
                },
                "snapshot.documents[]",
            )
            if row["deleted"]:
                continue
            revision_id = row["canonical_revision_id"]
            if not isinstance(revision_id, str) or revision_id not in self.revisions:
                errors.append("missing_canonical_revision")
                continue
            revision = self.revisions[revision_id]
            parse_id, elements = parse_elements(revision, self.contract)
            chunks = build_chunks(revision, parse_id, elements, self.contract)
            document_entries = build_entries(revision, parse_id, chunks, self.contract)
            self.elements[revision_id] = elements
            self.chunks[revision_id] = chunks
            for entry in document_entries:
                entries.append(entry)
                if failure == "after_n_index_entries" and len(entries) == 1:
                    errors.append("partial_index_build")
                    break
            if errors:
                break
        entries.sort(key=lambda item: item.index_entry_id)
        entry_set_hash = digest_object([item.index_entry_id for item in entries])
        generation_identity = {
            "snapshot_state_sha256": captured["snapshot_state_sha256"],
            "tombstone_state_sha256": captured["tombstone_state_sha256"],
            "authorization_revision": auth,
            "pipeline_fingerprint": self.contract.pipeline_fingerprint,
            "entry_set_sha256": entry_set_hash,
        }
        generation_id = "gen_" + digest_object(generation_identity)
        manifest = {
            **generation_identity,
            "generation_id": generation_id,
            "entry_ids": [item.index_entry_id for item in entries],
        }
        generation = IndexGeneration(
            generation_id=generation_id,
            snapshot_state_sha256=captured["snapshot_state_sha256"],
            tombstone_state_sha256=captured["tombstone_state_sha256"],
            authorization_revision=auth,
            pipeline_fingerprint=self.contract.pipeline_fingerprint,
            entries=tuple(entries),
            entry_set_sha256=entry_set_hash,
            manifest_sha256=digest_object(manifest),
            status="failed" if errors else "staged",
            errors=tuple(errors),
        )
        self.generations[generation_id] = generation
        return generation

    def _entry_errors(self, entry: IndexEntry) -> list[str]:
        errors: list[str] = []
        revision = self.revisions.get(entry.canonical_revision_id)
        if revision is None:
            return ["missing_canonical_revision"]
        if (entry.tenant_id, entry.document_id) != (
            revision.tenant_id,
            revision.document_id,
        ):
            errors.append("entry_document_binding_mismatch")
        if (
            entry.allowed_groups != revision.allowed_groups
            or entry.acl_snapshot_sha256 != revision.acl_snapshot_sha256
        ):
            errors.append("entry_acl_revision_mismatch")
        if digest_text(revision.raw_content) != revision.raw_sha256:
            errors.append("canonical_raw_hash_mismatch")
        if digest_text(revision.canonical_text) != revision.canonical_text_sha256:
            errors.append("canonical_text_hash_mismatch")
        actual_text = revision.canonical_text[entry.char_start : entry.char_end]
        if entry.coordinate_space != COORDINATE_SPACE:
            errors.append("bad_coordinate_space")
        if not 0 <= entry.char_start < entry.char_end <= len(revision.canonical_text):
            errors.append("source_span_out_of_bounds")
            actual_text = ""
        if actual_text != entry.content_text:
            errors.append("source_span_text_mismatch")
        if digest_text(entry.content_text) != entry.content_sha256:
            errors.append("entry_content_hash_mismatch")
        if digest_text(entry.retrieval_text) != entry.retrieval_sha256:
            errors.append("entry_retrieval_hash_mismatch")
        if _acl_hash(entry.allowed_groups) != entry.acl_snapshot_sha256:
            errors.append("entry_acl_hash_mismatch")
        expected_id = "idx_" + digest_object(
            {
                "chunk_id": entry.chunk_id,
                "retrieval_sha256": entry.retrieval_sha256,
                "index_revision": entry.index_revision,
                "acl_snapshot_sha256": entry.acl_snapshot_sha256,
            }
        )
        if expected_id != entry.index_entry_id:
            errors.append("index_entry_id_mismatch")
        matching_chunks = [
            item
            for item in self.chunks.get(entry.canonical_revision_id, ())
            if item.chunk_id == entry.chunk_id
        ]
        if len(matching_chunks) != 1:
            errors.append("chunk_lineage_missing")
        else:
            chunk = matching_chunks[0]
            if (
                chunk.parse_revision_id != entry.parse_revision_id
                or chunk.element_id != entry.element_id
                or chunk.text != entry.content_text
                or chunk.content_sha256 != entry.content_sha256
                or chunk.retrieval_text != entry.retrieval_text
                or chunk.retrieval_sha256 != entry.retrieval_sha256
                or chunk.char_start != entry.char_start
                or chunk.char_end != entry.char_end
            ):
                errors.append("chunk_entry_binding_mismatch")
        return errors

    def _generation_identity_errors(self, generation: IndexGeneration) -> list[str]:
        errors: list[str] = []
        entry_ids = sorted(item.index_entry_id for item in generation.entries)
        actual_entry_set = digest_object(entry_ids)
        if actual_entry_set != generation.entry_set_sha256:
            errors.append("entry_set_hash_mismatch")
        identity = {
            "snapshot_state_sha256": generation.snapshot_state_sha256,
            "tombstone_state_sha256": generation.tombstone_state_sha256,
            "authorization_revision": generation.authorization_revision,
            "pipeline_fingerprint": generation.pipeline_fingerprint,
            "entry_set_sha256": generation.entry_set_sha256,
        }
        expected_generation_id = "gen_" + digest_object(identity)
        if expected_generation_id != generation.generation_id:
            errors.append("generation_id_mismatch")
        manifest = {
            **identity,
            "generation_id": generation.generation_id,
            "entry_ids": entry_ids,
        }
        if digest_object(manifest) != generation.manifest_sha256:
            errors.append("generation_manifest_hash_mismatch")
        return errors

    def validate_generation(self, generation: IndexGeneration) -> list[str]:
        errors = list(generation.errors)
        current = self.capture_snapshot()
        if generation.snapshot_state_sha256 != current["snapshot_state_sha256"]:
            errors.append("stale_snapshot")
        if generation.tombstone_state_sha256 != current["tombstone_state_sha256"]:
            errors.append("stale_tombstone_state")
        if generation.authorization_revision != self.active_authorization_revision:
            errors.append("authorization_snapshot_mismatch")
        if generation.pipeline_fingerprint != self.contract.pipeline_fingerprint:
            errors.append("pipeline_fingerprint_mismatch")
        errors.extend(self._generation_identity_errors(generation))
        active_documents = {
            (state.tenant_id, state.document_id)
            for state in self.documents.values()
            if not state.deleted
        }
        indexed_documents = {
            (entry.tenant_id, entry.document_id) for entry in generation.entries
        }
        if indexed_documents != active_documents:
            errors.append("active_document_coverage_mismatch")
        expected_entry_ids: list[str] = []
        for state in self.documents.values():
            if state.deleted or state.canonical_revision_id is None:
                continue
            revision = self.revisions.get(state.canonical_revision_id)
            if revision is None:
                errors.append("current_canonical_revision_missing")
                continue
            parse_id, elements = parse_elements(revision, self.contract)
            chunks = build_chunks(revision, parse_id, elements, self.contract)
            expected_entry_ids.extend(
                item.index_entry_id
                for item in build_entries(revision, parse_id, chunks, self.contract)
            )
        if sorted(expected_entry_ids) != sorted(
            item.index_entry_id for item in generation.entries
        ):
            errors.append("current_entry_set_mismatch")
        for entry in generation.entries:
            errors.extend(self._entry_errors(entry))
        return sorted(set(errors))

    def publish_generation(self, generation_id: str) -> None:
        generation = self.generations.get(generation_id)
        if generation is None:
            raise ContractError("unknown index generation")
        if generation.status != "staged":
            raise ContractError("only a complete staged generation can be published")
        errors = self.validate_generation(generation)
        if errors:
            generation.status = "blocked"
            generation.errors = tuple(errors)
            raise ContractError("generation publication gate failed: " + ",".join(errors))
        previous_generation_id = self.published_generation_id
        if previous_generation_id is not None and previous_generation_id != generation_id:
            previous = self.generations.get(previous_generation_id)
            if previous is not None and previous.status == "published":
                previous.status = "superseded"
        generation.status = "published"
        self.published_generation_id = generation_id
        published_pairs = {
            (entry.tenant_id, entry.document_id): (
                entry.canonical_revision_id,
                entry.acl_snapshot_sha256,
            )
            for entry in generation.entries
        }
        for key, state in self.documents.items():
            pair = published_pairs.get(key)
            if (
                not state.deleted
                and pair is not None
                and pair == (state.canonical_revision_id, state.acl_snapshot_sha256)
            ):
                state.access_blocked = False

    def build_and_publish(self) -> str:
        generation = self.stage_generation()
        self.publish_generation(generation.generation_id)
        return generation.generation_id

    def _published(self) -> IndexGeneration:
        if self.published_generation_id is None:
            raise ContractError("there is no published index generation")
        generation = self.generations[self.published_generation_id]
        if generation.status != "published":
            raise ContractError("published pointer does not point to a published generation")
        integrity_errors = self._generation_identity_errors(generation)
        for entry in generation.entries:
            integrity_errors.extend(self._entry_errors(entry))
        if integrity_errors:
            raise ContractError(
                "published generation integrity failed: "
                + ",".join(sorted(set(integrity_errors)))
            )
        return generation

    @staticmethod
    def _features(text: str) -> set[str]:
        units = [match.group(0).lower() for match in TOKEN_RE.finditer(text)]  # Extract transparent tokens and normalize ASCII case.
        result = set(units)  # Add individual tokens first; the set deduplicates them.
        for left, right in zip(units, units[1:]):  # Inspect adjacent tokens to construct minimal two-character CJK features.
            if len(left) == 1 and len(right) == 1:  # Combine only two single characters; do not force English words together.
                result.add(left + right)  # Add the two-character feature to retain local order.
        return result  # Return the transparent feature set used only for teaching retrieval.

    def _select_entries(
        self, query: dict[str, Any], generation: IndexGeneration
    ) -> tuple[list[IndexEntry], int, list[IndexEntry]]:
        subject_groups = set(query["subject_groups"])  # Take trusted principal groups from the validated runtime query.
        visible: list[IndexEntry] = []  # Preserve index entries that pass every live authorization and lifecycle check.
        filtered = 0  # Filter count is used only for protected audit.
        for entry in generation.entries:  # Recheck live state for every entry in the current published generation.
            state = self.documents.get((entry.tenant_id, entry.document_id))  # Read the latest state for the corresponding canonical document.
            allowed = (  # Every condition must hold; any missing state fails closed.
                state is not None
                and not state.deleted
                and not state.access_blocked
                and entry.tenant_id == query["tenant_id"]
                and bool(subject_groups.intersection(entry.allowed_groups))
                and state.acl_snapshot_sha256 == entry.acl_snapshot_sha256
            )
            if allowed:  # An entry is visible only when its document is live, tenant matches, ACL matches, and snapshot has not drifted.
                visible.append(entry)  # Add it to the only set eligible for scoring.
            else:  # Unauthorized, deleted, or snapshot-drifted entries do not participate in retrieval.
                filtered += 1  # Accumulate a protected diagnostic count only; do not put it in the public response.
        query_features = self._features(query["query"])  # Parse transparent teaching features from the query.
        ranked: list[tuple[int, IndexEntry]] = []  # Temporarily hold lexical-score and entry pairs.
        for entry in visible:  # Traverse only entries that passed the live safety recheck above.
            score = len(query_features.intersection(self._features(entry.retrieval_text)))  # Calculate the feature-intersection size.
            if score >= MIN_LEXICAL_SCORE:  # Entries below the minimum score do not consume the finite top-k window.
                ranked.append((score, entry))  # Preserve candidates for stable sorting afterward.
        ranked.sort(key=lambda item: (-item[0], item[1].index_entry_id))  # Sort score descending and break ties by stable ID ascending.
        selected = [entry for _score, entry in ranked[: query["top_k"]]]  # Apply the already-validated top-k budget in the query.
        return visible, filtered, selected  # Return the visible set, internal count, and entries actually cited.

    def query(
        self, value: dict[str, Any], *, failure: str | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        query = validate_query(value)  # Accept only a strict runtime query; oracle fields cannot enter this API.
        if failure == "retrieval_unavailable":  # An unavailable dependency must not bypass retrieval to freely generate facts.
            status = "dependency_unavailable"  # Return a general status to the public layer without disclosing sources.
            claims: list[dict[str, Any]] = []  # Factual claims cannot be emitted without retrieved evidence.
            public = {  # Form the minimal public projection without generation, ACL, or filter count.
                "schema_version": PUBLIC_SCHEMA_VERSION,
                "query_id": query["query_id"],
                "status": status,
                "claims": claims,
                "trace_id": digest_object({"query": query, "status": status, "claims": claims}),
            }
            audit = {  # Protected audit can record this failure and the issued authorization revision.
                "schema_version": AUDIT_SCHEMA_VERSION,
                "visibility": "protected_audit",
                "trace_id": public["trace_id"],
                "authorization_revision": query["authorization_revision"],
                "index_generation_id": self.published_generation_id,
                "selected_entry_ids": [],
                "filter_summary": {"visible": 0, "filtered": 0},
                "failure": "retrieval_unavailable",
            }
            return public, audit  # The failure branch returns dual projections without triggering retrieval.
        generation = self._published()  # Read the current published generation; unpublished or invalid state is rejected internally.
        if (  # Both query and current generation must bind the active authorization revision.
            query["authorization_revision"] != self.active_authorization_revision
            or generation.authorization_revision != self.active_authorization_revision
        ):
            status = "insufficient_evidence"  # Do not distinguish authorization-snapshot mismatch from no evidence; avoid public side channels.
            claims = []  # Published entries cannot generate claims when snapshots mismatch.
            public = {  # Still return the fixed public schema.
                "schema_version": PUBLIC_SCHEMA_VERSION,
                "query_id": query["query_id"],
                "status": status,
                "claims": claims,
                "trace_id": digest_object({"query": query, "status": status, "claims": claims}),
            }
            audit = {
                "schema_version": AUDIT_SCHEMA_VERSION,
                "visibility": "protected_audit",
                "trace_id": public["trace_id"],
                "authorization_revision": query["authorization_revision"],
                "index_generation_id": generation.generation_id,
                "selected_entry_ids": [],
                "filter_summary": {"visible": 0, "filtered": len(generation.entries)},
                "failure": "authorization_snapshot_mismatch",
            }
            return public, audit

        visible, filtered, selected = self._select_entries(query, generation)
        claims: list[dict[str, Any]] = []
        for index, entry in enumerate(selected, start=1):
            revision = self.revisions[entry.canonical_revision_id]
            citation = {
                "document_id": entry.document_id,
                "source_uri": revision.source_uri,
                "source_version": revision.source_version,
                "raw_sha256": revision.raw_sha256,
                "canonical_revision_id": revision.canonical_revision_id,
                "parse_revision_id": entry.parse_revision_id,
                "element_id": entry.element_id,
                "chunk_id": entry.chunk_id,
                "index_entry_id": entry.index_entry_id,
                "coordinate_space": entry.coordinate_space,
                "char_start": entry.char_start,
                "char_end": entry.char_end,
                "span_sha256": digest_text(entry.content_text),
            }
            claims.append(
                {
                    "claim_id": f"C{index}",
                    "text": entry.content_text,
                    "citations": [citation],
                }
            )
        status = "answered" if claims else "insufficient_evidence"
        trace_id = digest_object(
            {
                "query": query,
                "status": status,
                "claims": claims,
            }
        )
        public = {
            "schema_version": PUBLIC_SCHEMA_VERSION,
            "query_id": query["query_id"],
            "status": status,
            "claims": claims,
            "trace_id": trace_id,
        }
        audit = {
            "schema_version": AUDIT_SCHEMA_VERSION,
            "visibility": "protected_audit",
            "trace_id": trace_id,
            "authorization_revision": query["authorization_revision"],
            "index_generation_id": generation.generation_id,
            "selected_entry_ids": [entry.index_entry_id for entry in selected],
            "filter_summary": {"visible": len(visible), "filtered": filtered},
            "failure": None,
        }
        evidence_errors = self.validate_evidence(query, public, audit)
        if evidence_errors:
            raise ContractError("evidence validation failed: " + ",".join(evidence_errors))
        return public, audit

    def validate_evidence(
        self,
        query_value: dict[str, Any],
        public: Any,
        audit: Any,
    ) -> list[str]:
        errors: list[str] = []
        try:
            query = validate_query(query_value)
            public_obj = _exact_fields(
                public,
                {"schema_version", "query_id", "status", "claims", "trace_id"},
                "public",
            )
            audit_obj = _exact_fields(
                audit,
                {
                    "schema_version",
                    "visibility",
                    "trace_id",
                    "authorization_revision",
                    "index_generation_id",
                    "selected_entry_ids",
                    "filter_summary",
                    "failure",
                },
                "audit",
            )
        except ContractError as exc:
            return [str(exc)]
        if public_obj["schema_version"] != PUBLIC_SCHEMA_VERSION:
            errors.append("public_schema_mismatch")
        if audit_obj["schema_version"] != AUDIT_SCHEMA_VERSION:
            errors.append("audit_schema_mismatch")
        if audit_obj["visibility"] != "protected_audit":
            errors.append("audit_visibility_mismatch")
        if public_obj["query_id"] != query["query_id"]:
            errors.append("query_id_mismatch")
        if public_obj["status"] not in {
            "answered",
            "insufficient_evidence",
            "dependency_unavailable",
        }:
            errors.append("public_status_invalid")
        if public_obj["trace_id"] != audit_obj["trace_id"]:
            errors.append("trace_id_mismatch")
        if audit_obj["authorization_revision"] != query["authorization_revision"]:
            errors.append("audit_authorization_revision_mismatch")
        generation_id = audit_obj["index_generation_id"]
        if (
            not isinstance(generation_id, str)
            or not generation_id.startswith("gen_")
            or HEX_64.fullmatch(generation_id.removeprefix("gen_")) is None
        ):
            errors.append("index_generation_id_invalid")
            return sorted(set(errors))
        generation = self.generations.get(generation_id)
        if generation is None or generation.status != "published":
            errors.append("generation_not_published")
            return sorted(set(errors))
        if generation_id != self.published_generation_id:
            errors.append("generation_not_current")
            return sorted(set(errors))
        selected_ids = audit_obj["selected_entry_ids"]
        if not isinstance(selected_ids, list) or any(
            not isinstance(item, str) for item in selected_ids
        ):
            errors.append("selected_entry_ids_invalid")
            return sorted(set(errors))
        failure = audit_obj["failure"]
        if failure not in {
            None,
            "retrieval_unavailable",
            "authorization_snapshot_mismatch",
        }:
            errors.append("audit_failure_invalid")
        entry_by_id = {entry.index_entry_id: entry for entry in generation.entries}
        claims = public_obj["claims"]
        if not isinstance(claims, list):
            errors.append("claims_invalid")
            return sorted(set(errors))
        if public_obj["status"] == "answered" and not claims:
            errors.append("answered_without_claims")
        if public_obj["status"] != "answered" and claims:
            errors.append("non_answered_with_claims")
        if failure is None:
            if query["authorization_revision"] != self.active_authorization_revision:
                errors.append("query_authorization_not_active")
            if generation.authorization_revision != self.active_authorization_revision:
                errors.append("generation_authorization_not_active")
            if generation.authorization_revision != audit_obj["authorization_revision"]:
                errors.append("generation_authorization_revision_mismatch")
        elif failure == "retrieval_unavailable":
            if public_obj["status"] != "dependency_unavailable":
                errors.append("retrieval_failure_status_mismatch")
            if claims or selected_ids:
                errors.append("retrieval_failure_must_not_return_evidence")
            if audit_obj["filter_summary"] != {"visible": 0, "filtered": 0}:
                errors.append("retrieval_failure_filter_summary_mismatch")
        elif failure == "authorization_snapshot_mismatch":
            authorization_is_stale = (
                query["authorization_revision"] != self.active_authorization_revision
                or generation.authorization_revision
                != self.active_authorization_revision
            )
            if not authorization_is_stale:
                errors.append("authorization_failure_without_mismatch")
            if public_obj["status"] != "insufficient_evidence":
                errors.append("authorization_failure_status_mismatch")
            if claims or selected_ids:
                errors.append("authorization_failure_must_not_return_evidence")
            if audit_obj["filter_summary"] != {
                "visible": 0,
                "filtered": len(generation.entries),
            }:
                errors.append("authorization_failure_filter_summary_mismatch")
        cited_entry_ids: list[str] = []
        for claim in claims:
            if not isinstance(claim, dict) or set(claim) != {"claim_id", "text", "citations"}:
                errors.append("claim_schema_mismatch")
                continue
            if not isinstance(claim["text"], str) or not claim["text"]:
                errors.append("claim_text_invalid")
                continue
            citations = claim["citations"]
            if not isinstance(citations, list) or not citations:
                errors.append("citation_missing")
                continue
            for citation in citations:
                expected_fields = {
                    "document_id",
                    "source_uri",
                    "source_version",
                    "raw_sha256",
                    "canonical_revision_id",
                    "parse_revision_id",
                    "element_id",
                    "chunk_id",
                    "index_entry_id",
                    "coordinate_space",
                    "char_start",
                    "char_end",
                    "span_sha256",
                }
                if not isinstance(citation, dict) or set(citation) != expected_fields:
                    errors.append("citation_schema_mismatch")
                    continue
                string_fields = expected_fields - {"char_start", "char_end"}
                if any(
                    not isinstance(citation[field], str)
                    or not citation[field]
                    for field in string_fields
                ):
                    errors.append("citation_string_field_invalid")
                    continue
                citation_entry_id = citation["index_entry_id"]
                entry = entry_by_id.get(citation_entry_id)
                cited_entry_ids.append(citation_entry_id)
                if entry is None:
                    errors.append("citation_entry_missing")
                    continue
                if entry.index_entry_id not in selected_ids:
                    errors.append("citation_not_selected")
                state = self.documents.get((entry.tenant_id, entry.document_id))
                if (
                    state is None
                    or state.deleted
                    or state.access_blocked
                    or entry.tenant_id != query["tenant_id"]
                    or not set(query["subject_groups"]).intersection(entry.allowed_groups)
                    or state.acl_snapshot_sha256 != entry.acl_snapshot_sha256
                ):
                    errors.append("citation_not_currently_authorized")
                revision = self.revisions.get(citation["canonical_revision_id"])
                if revision is None:
                    errors.append("citation_revision_missing")
                    continue
                bindings = {
                    "document_id": entry.document_id,
                    "canonical_revision_id": entry.canonical_revision_id,
                    "parse_revision_id": entry.parse_revision_id,
                    "element_id": entry.element_id,
                    "chunk_id": entry.chunk_id,
                    "coordinate_space": entry.coordinate_space,
                    "char_start": entry.char_start,
                    "char_end": entry.char_end,
                }
                if any(citation[key] != expected for key, expected in bindings.items()):
                    errors.append("citation_binding_mismatch")
                if citation["source_uri"] != revision.source_uri:
                    errors.append("citation_source_uri_mismatch")
                if citation["source_version"] != revision.source_version:
                    errors.append("citation_source_version_mismatch")
                if citation["raw_sha256"] != revision.raw_sha256:
                    errors.append("citation_raw_hash_mismatch")
                start, end = citation["char_start"], citation["char_end"]
                if (
                    not isinstance(start, int)
                    or isinstance(start, bool)
                    or not isinstance(end, int)
                    or isinstance(end, bool)
                    or not 0 <= start < end <= len(revision.canonical_text)
                ):
                    errors.append("citation_span_out_of_bounds")
                    continue
                exact = revision.canonical_text[start:end]
                if exact != claim["text"]:
                    errors.append("citation_does_not_support_claim")
                if digest_text(exact) != citation["span_sha256"]:
                    errors.append("citation_span_hash_mismatch")
        if len(cited_entry_ids) != len(set(cited_entry_ids)):
            errors.append("duplicate_citation_entry")
        if sorted(cited_entry_ids) != sorted(selected_ids):
            errors.append("selected_citation_set_mismatch")
        elif cited_entry_ids != selected_ids:
            errors.append("selected_citation_order_mismatch")
        if failure is None:
            visible, filtered, expected_selected = self._select_entries(query, generation)
            expected_selected_ids = [item.index_entry_id for item in expected_selected]
            if selected_ids != expected_selected_ids:
                errors.append("selected_entries_not_recomputed")
            if audit_obj["filter_summary"] != {
                "visible": len(visible),
                "filtered": filtered,
            }:
                errors.append("filter_summary_not_recomputed")
        expected_trace = digest_object(
            {
                "query": query,
                "status": public_obj["status"],
                "claims": public_obj["claims"],
            }
        )
        if public_obj["trace_id"] != expected_trace:
            errors.append("trace_binding_mismatch")
        return sorted(set(errors))

    def reconcile(self) -> dict[str, int]:
        report = {
            "canonical_raw_hash_mismatch": 0,
            "canonical_text_hash_mismatch": 0,
            "canonical_revision_id_mismatch": 0,
            "element_integrity_mismatch": 0,
            "chunk_integrity_mismatch": 0,
            "index_entry_integrity_mismatch": 0,
            "published_generation_mismatch": 0,
        }
        for revision_id, revision in self.revisions.items():
            if digest_text(revision.raw_content) != revision.raw_sha256:
                report["canonical_raw_hash_mismatch"] += 1
            if digest_text(revision.canonical_text) != revision.canonical_text_sha256:
                report["canonical_text_hash_mismatch"] += 1
            identity = {
                "tenant_id": revision.tenant_id,
                "document_id": revision.document_id,
                "source_uri": revision.source_uri,
                "source_version": revision.source_version,
                "raw_sha256": revision.raw_sha256,
                "canonical_text_sha256": revision.canonical_text_sha256,
                "normalizer_revision": revision.normalizer_revision,
                "acl_snapshot_sha256": revision.acl_snapshot_sha256,
            }
            if revision_id != "can_" + digest_object(identity):
                report["canonical_revision_id_mismatch"] += 1
            for element in self.elements.get(revision_id, ()):
                exact = revision.canonical_text[element.char_start : element.char_end]
                expected_id = "el_" + digest_object(
                    {
                        "parse_revision_id": element.parse_revision_id,
                        "kind": element.kind,
                        "coordinate_space": element.coordinate_space,
                        "char_start": element.char_start,
                        "char_end": element.char_end,
                        "text_sha256": element.text_sha256,
                    }
                )
                if (
                    exact != element.text
                    or digest_text(element.text) != element.text_sha256
                    or expected_id != element.element_id
                ):
                    report["element_integrity_mismatch"] += 1
            for chunk in self.chunks.get(revision_id, ()):
                exact = revision.canonical_text[chunk.char_start : chunk.char_end]
                expected_id = "chk_" + digest_object(
                    {
                        "canonical_revision_id": chunk.canonical_revision_id,
                        "parse_revision_id": chunk.parse_revision_id,
                        "chunker_revision": chunk.chunker_revision,
                        "element_id": chunk.element_id,
                        "content_sha256": chunk.content_sha256,
                        "acl_snapshot_sha256": chunk.acl_snapshot_sha256,
                    }
                )
                if (
                    exact != chunk.text
                    or digest_text(chunk.text) != chunk.content_sha256
                    or digest_text(chunk.retrieval_text) != chunk.retrieval_sha256
                    or expected_id != chunk.chunk_id
                ):
                    report["chunk_integrity_mismatch"] += 1
        for generation in self.generations.values():
            if self._generation_identity_errors(generation):
                report["published_generation_mismatch"] += 1
            for entry in generation.entries:
                if self._entry_errors(entry):
                    report["index_entry_integrity_mismatch"] += 1
        if self.published_generation_id is not None:
            published = self.generations.get(self.published_generation_id)
            if published is None or published.status != "published":
                report["published_generation_mismatch"] += 1
        return report

    def require_reconciled(self) -> dict[str, int]:
        report = self.reconcile()
        failures = {key: value for key, value in report.items() if value}
        if failures:
            raise ContractError("reconciliation failed: " + canonical_json(failures))
        return report


def initialize_fixture(fixture: dict[str, Any]) -> ProvenanceEngine:
    require_fixture_integrity(fixture)
    engine = ProvenanceEngine(fixture["contract"])
    for event in fixture["source_events"]:
        engine.apply_event(event)
    engine.build_and_publish()
    engine.require_reconciled()
    return engine


def evaluate_fixture(
    fixture: dict[str, Any], *, failure: str | None = None
) -> dict[str, Any]:
    engine = initialize_fixture(fixture)
    oracle_by_id = {item["query_id"]: item for item in fixture["oracle"]}
    cases: list[dict[str, Any]] = []
    for query in fixture["queries"]:
        public, audit = engine.query(query, failure=failure)
        oracle = oracle_by_id[query["query_id"]]
        actual_documents = sorted(
            {
                citation["document_id"]
                for claim in public["claims"]
                for citation in claim["citations"]
            }
        )
        errors = engine.validate_evidence(query, public, audit)
        if public["status"] != oracle["expected_status"]:
            errors.append("status_mismatch")
        if failure is None and actual_documents != oracle["expected_documents"]:
            errors.append("expected_documents_mismatch")
        if set(actual_documents).intersection(oracle["forbidden_documents"]):
            errors.append("forbidden_document_disclosed")
        cases.append(
            {
                "query_id": query["query_id"],
                "slice": oracle["slice"],
                "critical": oracle["critical"],
                "passed": not errors,
                "failure_codes": sorted(set(errors)),
            }
        )
    generation = engine._published()
    passed = all(item["passed"] for item in cases)
    artifact = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "decision": "PASS" if passed else "BLOCK",
        "case_count": len(cases),
        "passed_case_count": sum(item["passed"] for item in cases),
        "fixture_sha256": fixture["fixture_sha256"],
        "fixture_model_sha256": fixture["fixture_model_sha256"],
        "pipeline_fingerprint": fixture["contract"].pipeline_fingerprint,
        "snapshot_state_sha256": generation.snapshot_state_sha256,
        "tombstone_state_sha256": generation.tombstone_state_sha256,
        "authorization_revision": generation.authorization_revision,
        "index_generation_id": generation.generation_id,
        "index_manifest_sha256": generation.manifest_sha256,
        "harness_revision": HARNESS_REVISION,
        "cases": cases,
    }
    artifact["artifact_sha256"] = digest_object(artifact)
    return artifact


def validate_artifact(value: Any) -> list[str]:
    errors: list[str] = []
    expected = {
        "schema_version",
        "decision",
        "case_count",
        "passed_case_count",
        "fixture_sha256",
        "fixture_model_sha256",
        "pipeline_fingerprint",
        "snapshot_state_sha256",
        "tombstone_state_sha256",
        "authorization_revision",
        "index_generation_id",
        "index_manifest_sha256",
        "harness_revision",
        "cases",
        "artifact_sha256",
    }
    try:
        artifact = _exact_fields(value, expected, "artifact")
    except ContractError as exc:
        return [str(exc)]
    if artifact["schema_version"] != ARTIFACT_SCHEMA_VERSION:
        errors.append("artifact_schema_mismatch")
    if artifact["harness_revision"] != HARNESS_REVISION:
        errors.append("harness_revision_mismatch")
    for field in (
        "fixture_sha256",
        "fixture_model_sha256",
        "pipeline_fingerprint",
        "snapshot_state_sha256",
        "tombstone_state_sha256",
        "index_manifest_sha256",
        "artifact_sha256",
    ):
        if not isinstance(artifact[field], str) or HEX_64.fullmatch(artifact[field]) is None:
            errors.append(f"{field}_invalid")
    if (
        not isinstance(artifact["case_count"], int)
        or isinstance(artifact["case_count"], bool)
        or artifact["case_count"] < 1
    ):
        errors.append("case_count_invalid")
    if (
        not isinstance(artifact["passed_case_count"], int)
        or isinstance(artifact["passed_case_count"], bool)
        or artifact["passed_case_count"] < 0
    ):
        errors.append("passed_case_count_invalid")
    if not isinstance(artifact["authorization_revision"], str) or not artifact[
        "authorization_revision"
    ]:
        errors.append("authorization_revision_invalid")
    if (
        not isinstance(artifact["index_generation_id"], str)
        or not artifact["index_generation_id"].startswith("gen_")
        or HEX_64.fullmatch(
            artifact["index_generation_id"].removeprefix("gen_")
        )
        is None
    ):
        errors.append("index_generation_id_invalid")
    cases = artifact["cases"]
    if not isinstance(cases, list) or not cases:
        errors.append("cases_invalid")
    else:
        expected_case_fields = {
            "query_id",
            "slice",
            "critical",
            "passed",
            "failure_codes",
        }
        seen_query_ids: set[str] = set()
        for index, item in enumerate(cases):
            if not isinstance(item, dict) or set(item) != expected_case_fields:
                errors.append(f"case_{index}_schema_mismatch")
                continue
            query_id = item["query_id"]
            if not isinstance(query_id, str) or not query_id or len(query_id) > 300:
                errors.append(f"case_{index}_query_id_invalid")
            elif query_id in seen_query_ids:
                errors.append("case_query_id_duplicate")
            else:
                seen_query_ids.add(query_id)
            if (
                not isinstance(item["slice"], str)
                or not item["slice"]
                or len(item["slice"]) > 300
            ):
                errors.append(f"case_{index}_slice_invalid")
            if not isinstance(item["critical"], bool):
                errors.append(f"case_{index}_critical_invalid")
            if not isinstance(item["passed"], bool):
                errors.append(f"case_{index}_passed_invalid")
            failure_codes = item["failure_codes"]
            if (
                not isinstance(failure_codes, list)
                or any(not isinstance(code, str) or not code for code in failure_codes)
                or failure_codes != sorted(set(failure_codes))
            ):
                errors.append(f"case_{index}_failure_codes_invalid")
            elif isinstance(item["passed"], bool) and item["passed"] != (
                not failure_codes
            ):
                errors.append(f"case_{index}_pass_failure_mismatch")
        passed = sum(isinstance(item, dict) and item.get("passed") is True for item in cases)
        if artifact["case_count"] != len(cases):
            errors.append("case_count_mismatch")
        if artifact["passed_case_count"] != passed:
            errors.append("passed_case_count_mismatch")
        expected_decision = "PASS" if passed == len(cases) else "BLOCK"
        if artifact["decision"] != expected_decision:
            errors.append("decision_mismatch")
    unsigned = dict(artifact)
    supplied = unsigned.pop("artifact_sha256", None)
    if supplied != digest_object(unsigned):
        errors.append("artifact_hash_mismatch")
    return sorted(set(errors))


def _json_output(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline source-to-citation evidence-chain lab")
    parser.add_argument("--fixture", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("demo")
    ask = subparsers.add_parser("ask")
    ask.add_argument("--query-id", required=True)
    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("--query-id", required=True)
    inspect.add_argument("--operator-view", action="store_true")
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument(
        "--failure", choices=["retrieval_unavailable"], default=None
    )
    manifest = subparsers.add_parser("manifest")
    manifest.add_argument(
        "--operator-view",
        action="store_true",
        help="Explicitly confirm that output contains generation, authorization, and publication diagnostics",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        fixture = load_fixture(args.fixture)
        engine = initialize_fixture(fixture)
        if args.command == "demo":
            _json_output([engine.query(query)[0] for query in fixture["queries"]])
            return 0
        if args.command in {"ask", "inspect"}:
            query = next(
                (item for item in fixture["queries"] if item["query_id"] == args.query_id),
                None,
            )
            if query is None:
                raise ContractError(f"unknown query_id: {args.query_id}")
            public, audit = engine.query(query)
            if args.command == "inspect":
                if not args.operator_view:
                    raise ContractError("inspect requires explicit --operator-view")
                _json_output({"public": public, "protected_audit": audit})
            else:
                _json_output(public)
            return 0
        if args.command == "evaluate":
            artifact = evaluate_fixture(fixture, failure=args.failure)
            _json_output(artifact)
            return 0 if artifact["decision"] == "PASS" else 1
        if args.command == "manifest":
            if not args.operator_view:
                raise ContractError(
                    "manifest requires explicit --operator-view; this flag is only a teaching confirmation and does not replace real authorization"
                )
            generation = engine._published()
            _json_output(
                {
                    "generation_id": generation.generation_id,
                    "snapshot_state_sha256": generation.snapshot_state_sha256,
                    "tombstone_state_sha256": generation.tombstone_state_sha256,
                    "authorization_revision": generation.authorization_revision,
                    "pipeline_fingerprint": generation.pipeline_fingerprint,
                    "entry_set_sha256": generation.entry_set_sha256,
                    "manifest_sha256": generation.manifest_sha256,
                    "entry_count": len(generation.entries),
                }
            )
            return 0
        raise ContractError("unknown command")
    except ContractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
