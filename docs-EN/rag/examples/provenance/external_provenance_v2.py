"""Independent consumer for the cross-layer external provenance bundle v2.

The producer's embedded digest proves deterministic self-consistency only.  The
consumer accepts JSON bytes/text (never an in-memory producer object), requires
an out-of-band policy that pins the complete bundle digest and release
identity, rebuilds parser/chunk artifacts with the local trusted
implementations, and imports the result as *staged*.  Publication is a separate
local decision against live authorization and tombstone state.

This remains a deterministic, standard-library teaching implementation for
strict UTF-8 Markdown.  It is not a signature verifier, identity provider,
distributed publication protocol, or physical-erasure system.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
import hashlib
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath
import re
import secrets
import sys
import tempfile
from types import MappingProxyType
from typing import Any, Mapping
import unicodedata


SCHEMA_VERSION = "external-provenance-bundle-v2"
CANONICALIZATION_REVISION = "ai-agent-engineer/restricted-canonical-json/v1"
PUBLIC_SCHEMA_VERSION = "external-provenance-public-v2"
AUDIT_SCHEMA_VERSION = "external-provenance-audit-v2"

ADAPTER_REVISION = "cross-layer-adapter-v1"
NORMALIZER_REVISION = "utf8-no-bom-lf-nfc-v1"
MAPPING_REVISION = "parser-line-to-namespaced-lexical-v1"
LEXICAL_UNIT_REVISION = "chunking-lab/regex-lexical-unit/v1"
LEXICAL_COORDINATE_SPACE = "element-lexical-unit-0-based-half-open-v1"
CANONICAL_MAPPING_SCHEME = "external-provenance/canonical-mapping/v2"
KNOWLEDGE_STATE_REVISION = "knowledge-store/source-build-state/v1"
KNOWLEDGE_STORE_SCHEMA_VERSION = "1.0"
EVIDENCE_LEVEL = "document-revision-bridge"

SOURCE_ID_SCHEME = "ai-agent-engineer/logical-source/v1"
ELEMENT_ID_SCHEME = "ai-agent-engineer/namespaced-parser-element/v1"
CHUNK_ID_SCHEME = "chunking-lab/chunk/v1"
INDEX_ID_SCHEME = "chunking-lab/index-entry/v1"
KB_REVISION_SCHEME = "ai-agent-engineer/knowledge-revision/v1"
GENERATION_ID_SCHEME = "ai-agent-engineer/cross-layer-generation/v1"
PARSER_REVISION_SCHEME = "document-inspector/parse-revision/v2"
PARSER_ELEMENT_SCHEME = "document-inspector/element/v2"

MAX_BUNDLE_BYTES = 32_000_000
MAX_SOURCE_BYTES = 100_000
MAX_DOCUMENTS = 32
MAX_CHUNKS = 4096
MAX_INDEX_ENTRIES = 4096
MAX_TOKEN_CHARS = 2_000
MAX_TOP_K = 20
MAX_JSON_DEPTH = 64
HEX64 = re.compile(r"^[0-9a-f]{64}$")

_VALIDATED_STAGE_MARKER = object()
_LOCAL_PUBLICATION_MARKER = object()
_TRUSTED_CONTEXT_MARKER = object()


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load local teaching module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


DOCS_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DOCS_ROOT = DOCS_ROOT.parent / "docs-EN"
PARSER_PATH = SOURCE_DOCS_ROOT / "document-parsing" / "examples" / "inspect_documents.py"
CHUNK_PATH = SOURCE_DOCS_ROOT / "chunking-strategies" / "examples" / "chunking_lab.py"
PARSER = _load_module("external_provenance_v2_parser", PARSER_PATH)
CHUNK = _load_module("external_provenance_v2_chunk", CHUNK_PATH)


class ExternalProvenanceError(ValueError):
    """A fail-closed, machine-readable import/publication/query error."""

    def __init__(self, code: str, path: str, detail: str):
        self.code = code
        self.path = path
        self.detail = detail
        super().__init__(f"{code} at {path}: {detail}")


def _fail(code: str, path: str, detail: str) -> None:
    raise ExternalProvenanceError(code, path, detail)


def _reject_constant(value: str) -> None:
    _fail("non_standard_number", "$", f"JSON constant {value} is forbidden")


def _reject_float(value: str) -> None:
    _fail("float_not_supported", "$", "floats are outside the canonical domain")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate_json_key", "$", f"duplicate object member {key!r}")
        result[key] = value
    return result


def _reject_excessive_json_nesting(text: str) -> None:
    """Bound container nesting before CPython's recursive JSON decoder runs."""

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
                _fail(
                    "json_depth_exceeded",
                    "$",
                    f"container nesting exceeds {MAX_JSON_DEPTH}",
                )
        elif character in "]}":
            depth = max(0, depth - 1)


def strict_json_loads(value: str | bytes) -> Any:
    """Parse one bounded JSON boundary with duplicate/float/NaN rejection."""

    if isinstance(value, bytes):
        raw = value
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ExternalProvenanceError(
                "invalid_utf8", "$", "bundle bytes are not strict UTF-8"
            ) from exc
    elif isinstance(value, str):
        text = value
        try:
            raw = text.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise ExternalProvenanceError(
                "invalid_unicode", "$", "bundle text contains an unpaired surrogate"
            ) from exc
    else:
        _fail("json_boundary_required", "$", "consumer accepts only JSON text or bytes")
    if len(raw) > MAX_BUNDLE_BYTES:
        _fail("bundle_too_large", "$", "serialized bundle exceeds the consumer limit")
    _reject_excessive_json_nesting(text)
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_reject_float,
        )
    except ExternalProvenanceError:
        raise
    except json.JSONDecodeError as exc:
        raise ExternalProvenanceError(
            "invalid_json", "$", f"JSON syntax error near character {exc.pos}"
        ) from exc
    except RecursionError as exc:
        raise ExternalProvenanceError(
            "json_depth_exceeded", "$", "JSON decoder recursion limit was exceeded"
        ) from exc
    except ValueError as exc:
        raise ExternalProvenanceError(
            "invalid_json", "$", "JSON numeric/string limits were exceeded"
        ) from exc
    _check_json_domain(parsed)
    return parsed


def _check_json_domain(value: Any, path: str = "$", *, depth: int = 0) -> None:
    if depth > 64:
        _fail("json_depth_exceeded", path, "object nesting exceeds the consumer limit")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise ExternalProvenanceError(
                "invalid_unicode", path, "string contains an unpaired surrogate"
            ) from exc
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            _fail("non_standard_number", path, "non-finite number is forbidden")
        _fail("float_not_supported", path, "floats are outside the canonical domain")
    if isinstance(value, list) or isinstance(value, tuple):
        for index, item in enumerate(value):
            _check_json_domain(item, f"{path}[{index}]", depth=depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                _fail("non_string_key", path, "JSON object keys must be strings")
            try:
                key.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise ExternalProvenanceError(
                    "invalid_unicode", path, "object key contains an unpaired surrogate"
                ) from exc
            _check_json_domain(item, f"{path}.{key}", depth=depth + 1)
        return
    _fail("unsupported_json_type", path, f"unsupported value type {type(value).__name__}")


def canonical_json(value: Any) -> str:
    _check_json_domain(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_text(value: str) -> str:
    try:
        return digest_bytes(value.encode("utf-8", errors="strict"))
    except UnicodeEncodeError as exc:
        raise ExternalProvenanceError(
            "invalid_unicode", "$", "value cannot be encoded as strict UTF-8"
        ) from exc


def digest_object(value: Any) -> str:
    return digest_text(canonical_json(value))


def serialize_external_bundle(value: Any) -> str:
    """Serialize a trusted producer value for the mandatory JSON boundary."""

    text = canonical_json(value)
    if len(text.encode("utf-8")) > MAX_BUNDLE_BYTES:
        _fail("bundle_too_large", "$", "serialized bundle exceeds the consumer limit")
    return text


def trusted_bundle_sha256(value: Any) -> str:
    """Compute the complete canonical bundle digest in a trusted control plane.

    Production callers must deliver the returned value independently of the
    untrusted bundle channel.  Computing it from received bytes and immediately
    trusting the result would defeat the policy boundary.
    """

    return digest_object(value)


def _exact_fields(value: Any, expected: set[str], path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("object_required", path, "expected a JSON object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        _fail(
            "fields_mismatch",
            path,
            f"missing={missing!r}, extra={extra!r}",
        )
    return value


def _token(
    value: Any,
    path: str,
    *,
    maximum: int = MAX_TOKEN_CHARS,
) -> str:
    if not isinstance(value, str):
        _fail("string_required", path, "expected a string")
    if not value or len(value) > maximum:
        _fail("string_bounds", path, f"expected 1..{maximum} characters")
    if value != value.strip():
        _fail("string_whitespace", path, "leading/trailing whitespace is forbidden")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        _fail("control_character", path, "control characters are forbidden")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ExternalProvenanceError(
            "invalid_unicode", path, "string contains an unpaired surrogate"
        ) from exc
    return value


def _content_text(value: Any, path: str, *, maximum: int) -> str:
    """Validate bounded UTF-8 content while allowing JSON-escaped layout chars."""

    if not isinstance(value, str):
        _fail("string_required", path, "expected a string")
    if not value or len(value) > maximum:
        _fail("string_bounds", path, f"expected 1..{maximum} characters")
    if any(
        (ord(character) < 32 and character not in {"\t", "\n", "\r"})
        or ord(character) == 127
        for character in value
    ):
        _fail("control_character", path, "unsupported control character in content")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ExternalProvenanceError(
            "invalid_unicode", path, "string contains an unpaired surrogate"
        ) from exc
    return value


def _sha256(value: Any, path: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        _fail("sha256_invalid", path, "expected 64 lowercase hexadecimal characters")
    return value


def _integer(
    value: Any,
    path: str,
    *,
    minimum: int = 0,
    maximum: int = 1_000_000,
) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < minimum
        or value > maximum
    ):
        _fail("integer_bounds", path, f"expected integer in [{minimum}, {maximum}]")
    return value


def _sorted_unique_strings(
    value: Any,
    path: str,
    *,
    nonempty: bool = True,
    maximum_items: int = 128,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        _fail("array_required", path, "expected an array")
    if len(value) > maximum_items or (nonempty and not value):
        _fail("array_bounds", path, "array size is outside the contract")
    result = tuple(_token(item, f"{path}[]", maximum=300) for item in value)
    if result != tuple(sorted(set(result))):
        _fail("sorted_unique_required", path, "values must be sorted and unique")
    return result


def _ordered_strings(
    value: Any,
    path: str,
    *,
    nonempty: bool = True,
    maximum_items: int = 128,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        _fail("array_required", path, "expected an array")
    if len(value) > maximum_items or (nonempty and not value):
        _fail("array_bounds", path, "array size is outside the contract")
    result = tuple(_token(item, f"{path}[]", maximum=300) for item in value)
    return result


_ID_PREFIX = {
    SOURCE_ID_SCHEME: "xsrc_",
    ELEMENT_ID_SCHEME: "xel_",
    CHUNK_ID_SCHEME: "chk_",
    INDEX_ID_SCHEME: "idx_",
    KB_REVISION_SCHEME: "kbr_",
    GENERATION_ID_SCHEME: "xgen_",
    PARSER_ELEMENT_SCHEME: "elm_",
    PARSER_REVISION_SCHEME: "",
}


def _id_object(value: Any, scheme: str, path: str) -> str:
    item = _exact_fields(value, {"scheme", "value"}, path)
    if not isinstance(item["scheme"], str):
        _fail("id_scheme_type_invalid", f"{path}.scheme", "scheme must be a string")
    if item["scheme"] != scheme:
        _fail("id_scheme_mismatch", f"{path}.scheme", "identity scheme is not allowed")
    raw_value = item["value"]
    if not isinstance(raw_value, str):
        _fail("id_type_invalid", f"{path}.value", "identity value must be a string")
    prefix = _ID_PREFIX[scheme]
    suffix = raw_value[len(prefix) :] if prefix and raw_value.startswith(prefix) else raw_value
    if prefix and not raw_value.startswith(prefix):
        _fail("id_prefix_mismatch", f"{path}.value", "identity prefix does not match scheme")
    if HEX64.fullmatch(suffix) is None:
        _fail("id_value_invalid", f"{path}.value", "identity digest is malformed")
    return raw_value


def _same_id(value: Any, scheme: str, expected: str, path: str) -> None:
    actual = _id_object(value, scheme, path)
    if actual != expected:
        _fail("id_binding_mismatch", path, "identity does not match its referenced object")


def _normalize_source_text(value: str) -> str:
    if value.startswith("\ufeff"):
        _fail("bom_forbidden", "$.documents[].raw_representation.text", "BOM is forbidden")
    if "\x00" in value:
        _fail("nul_forbidden", "$.documents[].raw_representation.text", "NUL is forbidden")
    return unicodedata.normalize(
        "NFC", value.replace("\r\n", "\n").replace("\r", "\n")
    )


def _relative_markdown_path(value: Any, path: str) -> str:
    text = _token(value, path, maximum=300)
    if "\\" in text or ":" in text:
        _fail(
            "relative_path_invalid",
            path,
            "portable relative paths forbid backslashes and drive/stream separators",
        )
    candidate = PurePosixPath(text)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        _fail("relative_path_invalid", path, "absolute/traversal paths are forbidden")
    reserved = {"CON", "PRN", "AUX", "NUL"} | {
        f"{prefix}{index}"
        for prefix in ("COM", "LPT")
        for index in range(1, 10)
    }
    for part in candidate.parts:
        if (
            len(part) > 120
            or part.endswith((" ", "."))
            or any(character in '<>"|?*' for character in part)
            or part.split(".", 1)[0].upper() in reserved
        ):
            _fail(
                "relative_path_invalid",
                path,
                "path segment is outside the portable materialization contract",
            )
    if candidate.suffix.lower() != ".md":
        _fail("relative_path_invalid", path, "v2 consumer accepts Markdown only")
    return candidate.as_posix()


@dataclass(frozen=True)
class TrustedImportPolicy:
    """Out-of-band pins supplied independently of the untrusted bundle."""

    expected_bundle_sha256: str
    expected_generation_id: str
    expected_pipeline_fingerprint: str
    expected_authorization_revision: str

    def __post_init__(self) -> None:
        _sha256(self.expected_bundle_sha256, "policy.expected_bundle_sha256")
        if (
            not isinstance(self.expected_generation_id, str)
            or not self.expected_generation_id.startswith("xgen_")
            or HEX64.fullmatch(self.expected_generation_id.removeprefix("xgen_")) is None
        ):
            _fail(
                "policy_invalid",
                "policy.expected_generation_id",
                "expected generation must be xgen_ plus SHA-256",
            )
        _sha256(
            self.expected_pipeline_fingerprint,
            "policy.expected_pipeline_fingerprint",
        )
        _token(
            self.expected_authorization_revision,
            "policy.expected_authorization_revision",
            maximum=300,
        )


@dataclass(frozen=True)
class HostPrincipalGrant:
    """Authorization data owned by the host, never copied from a query body."""

    tenant_id: str
    subject_groups: tuple[str, ...]

    def __post_init__(self) -> None:
        _token(self.tenant_id, "live.principal_grants[].tenant_id", maximum=300)
        if not isinstance(self.subject_groups, tuple) or not self.subject_groups:
            _fail(
                "principal_grant_invalid",
                "live.principal_grants[].subject_groups",
                "subject groups must be a non-empty tuple",
            )
        normalized = tuple(
            _token(item, "live.principal_grants[].subject_groups[]", maximum=300)
            for item in self.subject_groups
        )
        if normalized != tuple(sorted(set(normalized))):
            _fail(
                "principal_grant_invalid",
                "live.principal_grants[].subject_groups",
                "subject groups must be sorted and unique",
            )


@dataclass(frozen=True, init=False)
class TrustedRequestContext:
    """Opaque host-issued identity context bound to one live-state snapshot."""

    principal_id: str
    tenant_id: str
    subject_groups: tuple[str, ...]
    authorization_revision: str
    request_nonce: str
    _live_state_marker: object = field(repr=False, compare=False)
    _issuance_marker: object = field(repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        _fail(
            "trusted_request_context_factory_required",
            "request_context",
            "request contexts must be issued by ConsumerLiveState",
        )


class ProtectedAuditSink:
    """Host-owned sink capability; query requesters never receive audit payloads."""

    def write(self, audit: Mapping[str, Any]) -> None:
        raise NotImplementedError


class InMemoryProtectedAuditSink(ProtectedAuditSink):
    """Deterministic teaching sink; production should use protected storage."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def write(self, audit: Mapping[str, Any]) -> None:
        if not isinstance(audit, Mapping) or audit.get("visibility") != "protected":
            _fail("protected_audit_invalid", "audit", "sink accepts protected audits only")
        trace_id = _token(audit.get("trace_id"), "audit.trace_id")
        record = copy.deepcopy(dict(audit))
        previous = self._records.get(trace_id)
        if previous is not None and canonical_json(previous) != canonical_json(record):
            _fail(
                "protected_audit_conflict",
                "audit.trace_id",
                "trace identity already binds a different protected record",
            )
        self._records[trace_id] = record

    def read(self, trace_id: str) -> dict[str, Any]:
        """Host-only diagnostic read used by the offline tests."""

        key = _token(trace_id, "audit.trace_id")
        record = self._records.get(key)
        if record is None:
            _fail("protected_audit_not_found", "audit.trace_id", "record is absent")
        return copy.deepcopy(record)


@dataclass(frozen=True)
class ConsumerLiveState:
    """Host-owned auth/tombstone/deny state; never sourced from request or bundle."""

    authorization_revision: str
    tombstone_state_sha256: str
    audit_sink: ProtectedAuditSink = field(repr=False, compare=False)
    blocked_documents: frozenset[tuple[str, str]] = frozenset()
    principal_grants: Mapping[str, HostPrincipalGrant] = field(
        default_factory=dict, repr=False
    )
    _context_marker: object = field(
        default_factory=object, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        _token(self.authorization_revision, "live.authorization_revision", maximum=300)
        _sha256(self.tombstone_state_sha256, "live.tombstone_state_sha256")
        if not isinstance(self.audit_sink, ProtectedAuditSink):
            _fail(
                "live_state_invalid",
                "live.audit_sink",
                "host must bind a ProtectedAuditSink",
            )
        if not isinstance(self.blocked_documents, frozenset):
            _fail(
                "live_state_invalid",
                "live.blocked_documents",
                "blocked_documents must be a frozenset",
            )
        for index, key in enumerate(self.blocked_documents):
            if (
                not isinstance(key, tuple)
                or len(key) != 2
                or not all(isinstance(item, str) for item in key)
            ):
                _fail(
                    "live_state_invalid",
                    f"live.blocked_documents[{index}]",
                    "each key must be a (tenant_id, document_id) tuple",
                )
            _token(key[0], f"live.blocked_documents[{index}].tenant_id")
            _token(key[1], f"live.blocked_documents[{index}].document_id")
        if not isinstance(self.principal_grants, Mapping) or len(self.principal_grants) > 128:
            _fail(
                "live_state_invalid",
                "live.principal_grants",
                "principal grants must be a bounded mapping",
            )
        grants: dict[str, HostPrincipalGrant] = {}
        for raw_principal, grant in self.principal_grants.items():
            principal = _token(raw_principal, "live.principal_grants[].principal_id")
            if not isinstance(grant, HostPrincipalGrant):
                _fail(
                    "live_state_invalid",
                    f"live.principal_grants[{principal!r}]",
                    "grant must be HostPrincipalGrant",
                )
            grants[principal] = grant
        object.__setattr__(
            self,
            "principal_grants",
            MappingProxyType(dict(sorted(grants.items()))),
        )

    def issue_request_context(self, principal_id: str) -> TrustedRequestContext:
        """Resolve a verified host principal to immutable tenant/group claims."""

        principal = _token(principal_id, "verified_principal.principal_id")
        grant = self.principal_grants.get(principal)
        if grant is None:
            _fail(
                "principal_not_authorized",
                "verified_principal.principal_id",
                "host authorization state has no grant for this principal",
            )
        context = object.__new__(TrustedRequestContext)
        for name, value in (
            ("principal_id", principal),
            ("tenant_id", grant.tenant_id),
            ("subject_groups", grant.subject_groups),
            ("authorization_revision", self.authorization_revision),
            ("request_nonce", secrets.token_hex(16)),
            ("_live_state_marker", self._context_marker),
            ("_issuance_marker", _TRUSTED_CONTEXT_MARKER),
        ):
            object.__setattr__(context, name, value)
        return context


@dataclass(frozen=True)
class ElementEvidence:
    tenant_id: str
    document_id: str
    logical_source_id: str
    source_revision_ref: str
    element: Any
    native_element_id: str
    native_location: Mapping[str, Any]
    canonical_mapping: Mapping[str, Any]


@dataclass(frozen=True)
class ImportedDocument:
    tenant_id: str
    document_id: str
    logical_source_id: str
    source_revision_ref: str
    allowed_groups: tuple[str, ...]
    access_snapshot_sha256: str
    source_uri: str
    source_version: str
    raw_sha256: str
    parser_record_sha256: str
    parse_revision_id: str
    elements: tuple[Any, ...]
    evidence: tuple[ElementEvidence, ...]


@dataclass(frozen=True)
class ImportedIndexEntry:
    index_entry_id: str
    chunk_id: str
    tenant_id: str
    document_id: str
    logical_source_id: str
    source_revision_ref: str
    access_snapshot_sha256: str
    retrieval_sha256: str


@dataclass(frozen=True, init=False)
class StagedExternalBundle:
    status: str
    bundle_sha256: str
    payload_sha256: str
    generation_id: str
    pipeline_fingerprint: str
    authorization_revision: str
    tombstone_state_sha256: str
    evidence_level: str
    documents: tuple[ImportedDocument, ...]
    chunks: tuple[Any, ...]
    index_entries: tuple[ImportedIndexEntry, ...]
    _validation_marker: object = field(repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        _fail(
            "validated_stage_factory_required",
            "$",
            "staged artifacts can only be created by stage_external_bundle",
        )

    def query(self, *_args: Any, **_kwargs: Any) -> None:
        _fail("consumer_not_published", "$", "staged artifacts are not queryable")


@dataclass(frozen=True, init=False)
class PublishedExternalBundle:
    bundle: StagedExternalBundle
    _publication_marker: object = field(repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        _fail(
            "local_publication_factory_required",
            "$",
            "published artifacts can only be created by publish_staged_bundle",
        )

    def query(
        self,
        value: Any,
        request_context: TrustedRequestContext,
        live_state: ConsumerLiveState,
    ) -> dict[str, Any]:
        if (
            getattr(self, "_publication_marker", None) is not _LOCAL_PUBLICATION_MARKER
            or getattr(self.bundle, "_validation_marker", None)
            is not _VALIDATED_STAGE_MARKER
        ):
            _fail("published_bundle_invalid", "$", "publication provenance marker is absent")
        public, audit = _query_published(
            self.bundle, value, request_context, live_state
        )
        try:
            live_state.audit_sink.write(audit)
        except ExternalProvenanceError:
            raise
        except Exception as exc:
            raise ExternalProvenanceError(
                "protected_audit_write_failed",
                "live.audit_sink",
                type(exc).__name__,
            ) from exc
        return public


def _validated_stage(**values: Any) -> StagedExternalBundle:
    names = (
        "status",
        "bundle_sha256",
        "payload_sha256",
        "generation_id",
        "pipeline_fingerprint",
        "authorization_revision",
        "tombstone_state_sha256",
        "evidence_level",
        "documents",
        "chunks",
        "index_entries",
    )
    if set(values) != set(names):
        _fail("internal_stage_contract_error", "$", "validated stage fields are incomplete")
    staged = object.__new__(StagedExternalBundle)
    for name in names:
        object.__setattr__(staged, name, values[name])
    object.__setattr__(staged, "_validation_marker", _VALIDATED_STAGE_MARKER)
    return staged


def _locally_published(staged: StagedExternalBundle) -> PublishedExternalBundle:
    published = object.__new__(PublishedExternalBundle)
    object.__setattr__(published, "bundle", staged)
    object.__setattr__(published, "_publication_marker", _LOCAL_PUBLICATION_MARKER)
    return published


def _validate_producer_contract(value: Any) -> dict[str, Any]:
    path = "$.producer_contract"
    item = _exact_fields(
        value,
        {
            "adapter_revision",
            "chunk_config",
            "chunk_strategy_version",
            "coordinate_schemes",
            "identity_schemes",
            "index_revision",
            "knowledge_state_revision",
            "knowledge_store_schema_version",
            "lexical_unit_revision",
            "mapping_revision",
            "normalizer_revision",
            "parser",
            "pipeline_fingerprint",
        },
        path,
    )
    if item["adapter_revision"] != ADAPTER_REVISION:
        _fail("contract_revision_mismatch", f"{path}.adapter_revision", "unsupported adapter")
    if item["normalizer_revision"] != NORMALIZER_REVISION:
        _fail("contract_revision_mismatch", f"{path}.normalizer_revision", "unsupported normalizer")
    if item["mapping_revision"] != MAPPING_REVISION:
        _fail("contract_revision_mismatch", f"{path}.mapping_revision", "unsupported mapping")
    if item["lexical_unit_revision"] != LEXICAL_UNIT_REVISION:
        _fail("contract_revision_mismatch", f"{path}.lexical_unit_revision", "unsupported lexical unitizer")
    if item["index_revision"] != CHUNK.LEXICAL_INDEX_REVISION:
        _fail("contract_revision_mismatch", f"{path}.index_revision", "unsupported index revision")
    if item["knowledge_state_revision"] != KNOWLEDGE_STATE_REVISION:
        _fail(
            "contract_revision_mismatch",
            f"{path}.knowledge_state_revision",
            "unsupported knowledge state identity algorithm",
        )
    if item["knowledge_store_schema_version"] != KNOWLEDGE_STORE_SCHEMA_VERSION:
        _fail(
            "contract_revision_mismatch",
            f"{path}.knowledge_store_schema_version",
            "unsupported knowledge store schema",
        )
    strategy = _token(item["chunk_strategy_version"], f"{path}.chunk_strategy_version")
    pipeline = _sha256(item["pipeline_fingerprint"], f"{path}.pipeline_fingerprint")

    config = _exact_fields(
        item["chunk_config"], {"max_units", "overlap_units"}, f"{path}.chunk_config"
    )
    max_units = _integer(config["max_units"], f"{path}.chunk_config.max_units", minimum=1, maximum=4096)
    overlap = _integer(config["overlap_units"], f"{path}.chunk_config.overlap_units", maximum=4095)
    if overlap >= max_units:
        _fail("chunk_config_invalid", f"{path}.chunk_config", "overlap must be smaller than max")

    coordinates = _exact_fields(
        item["coordinate_schemes"],
        {"canonical_mapping", "lexical", "native_location"},
        f"{path}.coordinate_schemes",
    )
    expected_coordinates = {
        "canonical_mapping": CANONICAL_MAPPING_SCHEME,
        "lexical": LEXICAL_COORDINATE_SPACE,
        "native_location": PARSER.LINE_COORDINATE_SPACE,
    }
    if coordinates != expected_coordinates:
        _fail("coordinate_scheme_mismatch", f"{path}.coordinate_schemes", "unsupported coordinate contract")

    schemes = _exact_fields(
        item["identity_schemes"],
        {
            "chunk",
            "generation",
            "index_entry",
            "knowledge_revision",
            "logical_source",
            "namespaced_element",
            "parser_element",
            "parser_revision",
        },
        f"{path}.identity_schemes",
    )
    expected_schemes = {
        "chunk": CHUNK_ID_SCHEME,
        "generation": GENERATION_ID_SCHEME,
        "index_entry": INDEX_ID_SCHEME,
        "knowledge_revision": KB_REVISION_SCHEME,
        "logical_source": SOURCE_ID_SCHEME,
        "namespaced_element": ELEMENT_ID_SCHEME,
        "parser_element": PARSER_ELEMENT_SCHEME,
        "parser_revision": PARSER_REVISION_SCHEME,
    }
    if schemes != expected_schemes:
        _fail("identity_scheme_contract_mismatch", f"{path}.identity_schemes", "unsupported identity map")

    parser = _exact_fields(
        item["parser"],
        {"config_sha256", "name", "schema_version", "version"},
        f"{path}.parser",
    )
    parser_config = _sha256(parser["config_sha256"], f"{path}.parser.config_sha256")
    if (
        parser["name"] != PARSER.PARSER_NAME
        or parser["version"] != PARSER.PARSER_VERSION
        or parser["schema_version"] != PARSER.SCHEMA_VERSION
    ):
        _fail("parser_contract_mismatch", f"{path}.parser", "local parser contract differs")
    return {
        "strategy": strategy,
        "pipeline": pipeline,
        "index_revision": item["index_revision"],
        "max_units": max_units,
        "overlap_units": overlap,
        "parser_config_sha256": parser_config,
    }


def _validate_authorization_contract(value: Any) -> str:
    path = "$.authorization_contract"
    item = _exact_fields(
        value,
        {
            "acl_enforcement",
            "authorization_revision",
            "consumer_live_authorization_check",
            "subject_membership_evidence",
        },
        path,
    )
    if item["acl_enforcement"] != "tenant-and-acl-before-score":
        _fail("authorization_contract_mismatch", f"{path}.acl_enforcement", "unsupported ACL semantics")
    if item["consumer_live_authorization_check"] != "required-before-publish-and-query":
        _fail("authorization_contract_mismatch", f"{path}.consumer_live_authorization_check", "live checks are mandatory")
    if item["subject_membership_evidence"] != "not-in-bundle-host-resolved":
        _fail("authorization_contract_mismatch", f"{path}.subject_membership_evidence", "bundle must not assert membership")
    return _token(item["authorization_revision"], f"{path}.authorization_revision")


def _validate_native_location(value: Any, path: str) -> dict[str, Any]:
    item = _exact_fields(value, {"coordinate_space", "line_start", "line_end"}, path)
    if item["coordinate_space"] != PARSER.LINE_COORDINATE_SPACE:
        _fail("native_coordinate_mismatch", f"{path}.coordinate_space", "unsupported line coordinate")
    start = _integer(item["line_start"], f"{path}.line_start", minimum=1)
    end = _integer(item["line_end"], f"{path}.line_end", minimum=1)
    if end < start:
        _fail("coordinate_out_of_bounds", path, "line_end precedes line_start")
    return {"coordinate_space": PARSER.LINE_COORDINATE_SPACE, "line_start": start, "line_end": end}


def _validate_mapping(value: Any, path: str) -> dict[str, str]:
    item = _exact_fields(value, {"mapping_revision", "reason_code", "status"}, path)
    if item != {
        "mapping_revision": MAPPING_REVISION,
        "reason_code": "parser_projection_is_not_one_exact_canonical_span",
        "status": "unavailable",
    }:
        _fail("evidence_level_overclaim", path, "v2 bridge must not claim a canonical span")
    return dict(item)


def _source_id(tenant_id: str, document_id: str) -> str:
    return "xsrc_" + digest_object(
        {"document_id": document_id, "id_scheme": SOURCE_ID_SCHEME, "tenant_id": tenant_id}
    )


def _adapter_element_id(
    tenant_id: str, document_id: str, revision_ref: str, native_element_id: str
) -> str:
    return "xel_" + digest_object(
        {
            "document_id": document_id,
            "id_scheme": ELEMENT_ID_SCHEME,
            "kb_revision_ref": revision_ref,
            "parser_element_id": native_element_id,
            "tenant_id": tenant_id,
        }
    )


def _kb_source_state_hash(
    *,
    allowed_groups: tuple[str, ...],
    content: str,
    source_uri: str,
    source_version: str,
) -> str:
    """Rebuild the source half of the declared knowledge-state contract."""

    return digest_object(
        {
            "allowed_groups": list(allowed_groups),
            "content": content,
            "source_uri": source_uri,
            "source_version": source_version,
        }
    )


def _kb_build_state_hash(*, pipeline_version: str, source_state_hash: str) -> str:
    """Rebuild the build half of the declared knowledge-state contract."""

    return digest_object(
        {
            "pipeline_version": pipeline_version,
            "source_state_hash": source_state_hash,
        }
    )


def _validate_parser_record_shape(value: Any, path: str) -> dict[str, Any]:
    record = _exact_fields(
        value,
        {
            "relative_path",
            "source_id",
            "raw_sha256",
            "size_bytes",
            "extension_media_type",
            "detected_media_type",
            "detection_method",
            "encoding",
            "status",
            "parser",
            "parser_version",
            "parse_revision_sha256",
            "elements",
            "issues",
        },
        path,
    )
    if record["status"] != "parsed":
        _fail("parser_record_not_parsed", f"{path}.status", "only parsed records are importable")
    if not isinstance(record["elements"], list) or not record["elements"]:
        _fail("parser_elements_invalid", f"{path}.elements", "non-empty element array required")
    if not isinstance(record["issues"], list):
        _fail("parser_issues_invalid", f"{path}.issues", "issues must be an array")
    seen: set[str] = set()
    for index, raw_element in enumerate(record["elements"], start=1):
        element_path = f"{path}.elements[{index - 1}]"
        element = _exact_fields(
            raw_element,
            {
                "element_id",
                "kind",
                "text",
                "text_sha256",
                "order",
                "location",
                "section_path",
                "attributes",
            },
            element_path,
        )
        element_id = _token(element["element_id"], f"{element_path}.element_id", maximum=68)
        if not element_id.startswith("elm_") or HEX64.fullmatch(element_id.removeprefix("elm_")) is None:
            _fail("id_value_invalid", f"{element_path}.element_id", "native element ID is malformed")
        if element_id in seen:
            _fail("duplicate_identity", f"{element_path}.element_id", "native element ID is duplicated")
        seen.add(element_id)
        if element["order"] != index:
            _fail("parser_element_order_invalid", f"{element_path}.order", "orders must be contiguous")
        text = _content_text(
            element["text"], f"{element_path}.text", maximum=MAX_SOURCE_BYTES
        )
        if digest_text(text) != _sha256(element["text_sha256"], f"{element_path}.text_sha256"):
            _fail("parser_element_hash_mismatch", element_path, "element text hash differs")
        _validate_native_location(element["location"], f"{element_path}.location")
        _ordered_strings(
            element["section_path"],
            f"{element_path}.section_path",
            nonempty=False,
            maximum_items=32,
        )
        if not isinstance(element["attributes"], dict):
            _fail("parser_attributes_invalid", f"{element_path}.attributes", "attributes must be an object")
    return record


def _validate_documents(
    value: Any,
    *,
    producer: Mapping[str, Any],
    authorization_revision: str,
) -> tuple[tuple[ImportedDocument, ...], dict[str, ImportedDocument], list[dict[str, Any]]]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_DOCUMENTS:
        _fail("documents_bounds", "$.documents", "document count is outside the contract")
    raw_documents: list[dict[str, Any]] = []
    paths: set[str] = set()
    document_keys: set[tuple[str, str]] = set()
    logical_ids: set[str] = set()
    revision_refs: set[str] = set()

    # First pass validates bounded representations before any local parser work.
    for index, raw_document in enumerate(value):
        path = f"$.documents[{index}]"
        document = _exact_fields(
            raw_document,
            {
                "access_snapshot",
                "adapter_elements",
                "canonical_representation",
                "crosswalk",
                "crosswalk_sha256",
                "document_id",
                "knowledge_revision",
                "logical_source_id",
                "parser_artifact",
                "raw_representation",
                "source_event",
                "tenant_id",
            },
            path,
        )
        tenant_id = _token(document["tenant_id"], f"{path}.tenant_id", maximum=300)
        document_id = _token(document["document_id"], f"{path}.document_id", maximum=300)
        key = (tenant_id, document_id)
        if key in document_keys:
            _fail("duplicate_document", path, "tenant/document identity is duplicated")
        document_keys.add(key)
        logical_source_id = _id_object(document["logical_source_id"], SOURCE_ID_SCHEME, f"{path}.logical_source_id")
        if logical_source_id != _source_id(tenant_id, document_id):
            _fail("logical_source_binding_mismatch", f"{path}.logical_source_id", "source ID does not bind tenant/document")
        if logical_source_id in logical_ids:
            _fail("duplicate_identity", f"{path}.logical_source_id", "logical source ID is duplicated")
        logical_ids.add(logical_source_id)

        event = _exact_fields(
            document["source_event"],
            {
                "connector",
                "media_type",
                "relative_path",
                "root_section_path",
                "run_id",
                "sequence",
                "source_uri",
                "source_version",
                "upstream_event_id",
            },
            f"{path}.source_event",
        )
        relative_path = _relative_markdown_path(event["relative_path"], f"{path}.source_event.relative_path")
        if relative_path in paths:
            _fail("duplicate_relative_path", f"{path}.source_event.relative_path", "relative path is duplicated")
        paths.add(relative_path)
        if event["media_type"] != "text/markdown":
            _fail("media_type_mismatch", f"{path}.source_event.media_type", "consumer accepts Markdown only")
        for name in ("connector", "run_id", "source_version", "upstream_event_id"):
            _token(event[name], f"{path}.source_event.{name}", maximum=300)
        _token(event["source_uri"], f"{path}.source_event.source_uri", maximum=1000)
        _integer(event["sequence"], f"{path}.source_event.sequence", minimum=1)
        root_section = _ordered_strings(
            event["root_section_path"],
            f"{path}.source_event.root_section_path",
            maximum_items=32,
        )

        raw = _exact_fields(
            document["raw_representation"],
            {"encoding", "mode", "sha256", "size_bytes", "text"},
            f"{path}.raw_representation",
        )
        if raw["encoding"] != "utf-8" or raw["mode"] != "inline_utf8":
            _fail("raw_representation_mismatch", f"{path}.raw_representation", "only inline strict UTF-8 is supported")
        raw_text = _content_text(
            raw["text"], f"{path}.raw_representation.text", maximum=MAX_SOURCE_BYTES
        )
        raw_bytes = raw_text.encode("utf-8")
        if len(raw_bytes) > MAX_SOURCE_BYTES:
            _fail("source_too_large", f"{path}.raw_representation.text", "source exceeds byte limit")
        if _integer(raw["size_bytes"], f"{path}.raw_representation.size_bytes", maximum=MAX_SOURCE_BYTES) != len(raw_bytes):
            _fail("raw_size_mismatch", f"{path}.raw_representation", "declared byte size differs")
        raw_sha = _sha256(raw["sha256"], f"{path}.raw_representation.sha256")
        if digest_bytes(raw_bytes) != raw_sha:
            _fail("raw_hash_mismatch", f"{path}.raw_representation", "raw bytes differ from digest")

        canonical = _exact_fields(
            document["canonical_representation"],
            {"mode", "normalizer_revision", "sha256", "text"},
            f"{path}.canonical_representation",
        )
        if canonical["mode"] != "inline_text" or canonical["normalizer_revision"] != NORMALIZER_REVISION:
            _fail("canonical_representation_mismatch", f"{path}.canonical_representation", "unsupported canonical representation")
        canonical_text = _content_text(
            canonical["text"],
            f"{path}.canonical_representation.text",
            maximum=MAX_SOURCE_BYTES,
        )
        expected_canonical = _normalize_source_text(raw_text)
        if canonical_text != expected_canonical:
            _fail("canonical_text_mismatch", f"{path}.canonical_representation", "canonical text is not LF+NFC(raw)")
        canonical_sha = _sha256(canonical["sha256"], f"{path}.canonical_representation.sha256")
        if digest_text(canonical_text) != canonical_sha:
            _fail("canonical_hash_mismatch", f"{path}.canonical_representation", "canonical digest differs")

        access = _exact_fields(
            document["access_snapshot"],
            {"allowed_groups", "authorization_revision", "sha256"},
            f"{path}.access_snapshot",
        )
        groups = _sorted_unique_strings(access["allowed_groups"], f"{path}.access_snapshot.allowed_groups")
        if access["authorization_revision"] != authorization_revision:
            _fail("authorization_binding_mismatch", f"{path}.access_snapshot.authorization_revision", "document auth revision differs")
        access_body = {
            "allowed_groups": list(groups),
            "authorization_revision": authorization_revision,
        }
        access_sha = _sha256(access["sha256"], f"{path}.access_snapshot.sha256")
        if digest_object(access_body) != access_sha:
            _fail("access_snapshot_hash_mismatch", f"{path}.access_snapshot", "access snapshot cannot be recomputed")

        parser_artifact = _exact_fields(
            document["parser_artifact"],
            {
                "config_sha256",
                "name",
                "parse_revision_id",
                "record",
                "record_sha256",
                "schema_version",
                "version",
            },
            f"{path}.parser_artifact",
        )
        if (
            parser_artifact["name"] != PARSER.PARSER_NAME
            or parser_artifact["version"] != PARSER.PARSER_VERSION
            or parser_artifact["schema_version"] != PARSER.SCHEMA_VERSION
            or parser_artifact["config_sha256"] != producer["parser_config_sha256"]
        ):
            _fail("parser_contract_mismatch", f"{path}.parser_artifact", "document parser contract differs")
        parser_record = _validate_parser_record_shape(parser_artifact["record"], f"{path}.parser_artifact.record")
        parser_record_sha = _sha256(parser_artifact["record_sha256"], f"{path}.parser_artifact.record_sha256")
        if digest_object(parser_record) != parser_record_sha:
            _fail("parser_record_hash_mismatch", f"{path}.parser_artifact", "record digest differs")
        parse_revision = _id_object(parser_artifact["parse_revision_id"], PARSER_REVISION_SCHEME, f"{path}.parser_artifact.parse_revision_id")
        if parser_record["parse_revision_sha256"] != parse_revision:
            _fail("parse_revision_binding_mismatch", f"{path}.parser_artifact", "typed parse revision differs from record")
        if parser_record["relative_path"] != relative_path or parser_record["raw_sha256"] != raw_sha:
            _fail("parser_source_binding_mismatch", f"{path}.parser_artifact.record", "parser record references another source")

        knowledge = _exact_fields(
            document["knowledge_revision"],
            {
                "external_snapshot_sha256",
                "identity_inputs",
                "producer_snapshot_sha256",
                "ref",
                "revision_number",
            },
            f"{path}.knowledge_revision",
        )
        revision_ref = _id_object(knowledge["ref"], KB_REVISION_SCHEME, f"{path}.knowledge_revision.ref")
        if revision_ref in revision_refs:
            _fail("duplicate_identity", f"{path}.knowledge_revision.ref", "KB revision ref is duplicated")
        revision_refs.add(revision_ref)
        revision_number = _integer(knowledge["revision_number"], f"{path}.knowledge_revision.revision_number", minimum=1)

        crosswalk_value = document["crosswalk"]
        if not isinstance(crosswalk_value, list) or not crosswalk_value:
            _fail("crosswalk_invalid", f"{path}.crosswalk", "non-empty crosswalk required")
        crosswalk: list[dict[str, Any]] = []
        native_seen: set[str] = set()
        adapter_seen: set[str] = set()
        record_by_id = {item["element_id"]: item for item in parser_record["elements"]}
        body_crosswalk: dict[str, dict[str, Any]] = {}
        for cross_index, raw_cross in enumerate(crosswalk_value):
            cross_path = f"{path}.crosswalk[{cross_index}]"
            cross = _exact_fields(
                raw_cross,
                {
                    "adapter_element_id",
                    "canonical_mapping",
                    "native_element_id",
                    "native_location",
                    "projection_relation",
                },
                cross_path,
            )
            native_id = _id_object(cross["native_element_id"], PARSER_ELEMENT_SCHEME, f"{cross_path}.native_element_id")
            if native_id in native_seen:
                _fail("duplicate_crosswalk", cross_path, "native element occurs more than once")
            native_seen.add(native_id)
            native_record = record_by_id.get(native_id)
            if native_record is None:
                _fail("orphan_crosswalk", cross_path, "crosswalk references unknown parser element")
            native_location = _validate_native_location(cross["native_location"], f"{cross_path}.native_location")
            if native_location != native_record["location"]:
                _fail("crosswalk_location_mismatch", cross_path, "native locator differs from parser record")
            mapping = _validate_mapping(cross["canonical_mapping"], f"{cross_path}.canonical_mapping")
            relation = cross["projection_relation"]
            if native_record["kind"] == "heading":
                if relation != "context_only" or cross["adapter_element_id"] is not None:
                    _fail("projection_relation_mismatch", cross_path, "heading must remain context-only")
                adapter_id = None
            else:
                if relation != "projected_as_body":
                    _fail("projection_relation_mismatch", cross_path, "body must be projected explicitly")
                adapter_id = _id_object(cross["adapter_element_id"], ELEMENT_ID_SCHEME, f"{cross_path}.adapter_element_id")
                expected_adapter_id = _adapter_element_id(tenant_id, document_id, revision_ref, native_id)
                if adapter_id != expected_adapter_id:
                    _fail("adapter_element_binding_mismatch", cross_path, "adapter ID cannot be recomputed")
                if adapter_id in adapter_seen:
                    _fail("duplicate_identity", cross_path, "adapter element ID is duplicated")
                adapter_seen.add(adapter_id)
                body_crosswalk[adapter_id] = {
                    "native": native_record,
                    "native_id": native_id,
                    "location": native_location,
                    "mapping": mapping,
                }
            crosswalk.append(copy.deepcopy(cross))
        native_order = [item["element_id"] for item in parser_record["elements"]]
        crosswalk_native_order = [
            _id_object(
                item["native_element_id"],
                PARSER_ELEMENT_SCHEME,
                f"{path}.crosswalk[{index}].native_element_id",
            )
            for index, item in enumerate(crosswalk)
        ]
        if crosswalk_native_order != native_order:
            _fail(
                "crosswalk_order_mismatch",
                f"{path}.crosswalk",
                "crosswalk rows must preserve fresh parser element order",
            )
        if native_seen != set(record_by_id):
            _fail("crosswalk_coverage_mismatch", f"{path}.crosswalk", "parser elements are not covered exactly once")
        crosswalk_sha = _sha256(document["crosswalk_sha256"], f"{path}.crosswalk_sha256")
        if digest_object(crosswalk) != crosswalk_sha:
            _fail("crosswalk_hash_mismatch", f"{path}.crosswalk", "crosswalk digest differs")

        elements_value = document["adapter_elements"]
        if not isinstance(elements_value, list) or not elements_value:
            _fail("adapter_elements_invalid", f"{path}.adapter_elements", "body elements are required")
        imported_elements: list[Any] = []
        evidence: list[ElementEvidence] = []
        for element_index, raw_element in enumerate(elements_value):
            element_path = f"{path}.adapter_elements[{element_index}]"
            element_value = _exact_fields(
                raw_element,
                {
                    "access_snapshot_sha256",
                    "allowed_groups",
                    "element_id",
                    "kind",
                    "logical_source_id",
                    "native_location",
                    "section_path",
                    "source_revision_ref",
                    "text",
                    "text_sha256",
                },
                element_path,
            )
            element_id = _id_object(element_value["element_id"], ELEMENT_ID_SCHEME, f"{element_path}.element_id")
            bridge = body_crosswalk.get(element_id)
            if bridge is None:
                _fail("orphan_adapter_element", element_path, "element lacks a body crosswalk")
            _same_id(element_value["logical_source_id"], SOURCE_ID_SCHEME, logical_source_id, f"{element_path}.logical_source_id")
            _same_id(element_value["source_revision_ref"], KB_REVISION_SCHEME, revision_ref, f"{element_path}.source_revision_ref")
            if element_value["access_snapshot_sha256"] != access_sha:
                _fail("element_access_binding_mismatch", element_path, "element access snapshot differs")
            element_groups = _sorted_unique_strings(element_value["allowed_groups"], f"{element_path}.allowed_groups")
            if element_groups != groups:
                _fail("element_acl_mismatch", element_path, "element ACL differs from document")
            kind = _token(element_value["kind"], f"{element_path}.kind")
            if kind not in CHUNK.ALLOWED_KINDS or kind != bridge["native"]["kind"]:
                _fail("element_kind_mismatch", element_path, "element kind differs from native parser output")
            text = _content_text(
                element_value["text"], f"{element_path}.text", maximum=MAX_SOURCE_BYTES
            )
            if text != bridge["native"]["text"]:
                _fail("element_text_mismatch", element_path, "adapter quote differs from parser element")
            if digest_text(text) != _sha256(element_value["text_sha256"], f"{element_path}.text_sha256"):
                _fail("element_text_hash_mismatch", element_path, "element digest differs")
            location = _validate_native_location(element_value["native_location"], f"{element_path}.native_location")
            if location != bridge["location"]:
                _fail("element_location_mismatch", element_path, "element locator differs from crosswalk")
            sections = _ordered_strings(
                element_value["section_path"],
                f"{element_path}.section_path",
                maximum_items=32,
            )
            expected_sections = tuple(bridge["native"]["section_path"]) or root_section
            if sections != expected_sections:
                _fail("element_section_mismatch", element_path, "section path differs from trusted mapping")
            element = CHUNK.Element(
                source_id=logical_source_id,
                source_revision=revision_ref,
                element_id=element_id,
                kind=kind,
                text=text,
                section_path=sections,
                acl=groups,
                line_start=location["line_start"],
                line_end=location["line_end"],
            )
            imported_elements.append(element)
            evidence.append(
                ElementEvidence(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    logical_source_id=logical_source_id,
                    source_revision_ref=revision_ref,
                    element=element,
                    native_element_id=bridge["native_id"],
                    native_location=MappingProxyType(dict(location)),
                    canonical_mapping=MappingProxyType(dict(bridge["mapping"])),
                )
            )
        if [item.element_id for item in imported_elements] != list(body_crosswalk):
            _fail(
                "adapter_element_order_mismatch",
                f"{path}.adapter_elements",
                "adapter elements must preserve projected crosswalk order exactly",
            )

        identity = _exact_fields(
            knowledge["identity_inputs"],
            {
                "allowed_groups",
                "build_state_hash",
                "canonical_text_sha256",
                "document_id",
                "id_scheme",
                "parse_revision_sha256",
                "pipeline_version",
                "revision_number",
                "run_id",
                "source_state_hash",
                "source_uri",
                "source_version",
                "tenant_id",
            },
            f"{path}.knowledge_revision.identity_inputs",
        )
        for name in ("build_state_hash", "canonical_text_sha256", "parse_revision_sha256", "source_state_hash"):
            _sha256(identity[name], f"{path}.knowledge_revision.identity_inputs.{name}")
        pipeline_version = _token(
            identity["pipeline_version"],
            f"{path}.knowledge_revision.identity_inputs.pipeline_version",
        )
        expected_source_state_hash = _kb_source_state_hash(
            allowed_groups=groups,
            content=canonical_text,
            source_uri=event["source_uri"],
            source_version=event["source_version"],
        )
        if identity["source_state_hash"] != expected_source_state_hash:
            _fail(
                "knowledge_source_state_mismatch",
                f"{path}.knowledge_revision.identity_inputs.source_state_hash",
                f"KB source state violates {KNOWLEDGE_STATE_REVISION}",
            )
        expected_build_state_hash = _kb_build_state_hash(
            pipeline_version=pipeline_version,
            source_state_hash=expected_source_state_hash,
        )
        if identity["build_state_hash"] != expected_build_state_hash:
            _fail(
                "knowledge_build_state_mismatch",
                f"{path}.knowledge_revision.identity_inputs.build_state_hash",
                f"KB build state violates {KNOWLEDGE_STATE_REVISION}",
            )
        expected_identity = {
            "allowed_groups": list(groups),
            "build_state_hash": expected_build_state_hash,
            "canonical_text_sha256": canonical_sha,
            "document_id": document_id,
            "id_scheme": KB_REVISION_SCHEME,
            "parse_revision_sha256": parse_revision,
            "pipeline_version": pipeline_version,
            "revision_number": revision_number,
            "run_id": event["run_id"],
            "source_state_hash": expected_source_state_hash,
            "source_uri": event["source_uri"],
            "source_version": event["source_version"],
            "tenant_id": tenant_id,
        }
        if identity != expected_identity:
            _fail("knowledge_revision_binding_mismatch", f"{path}.knowledge_revision.identity_inputs", "KB identity disagrees with document")
        expected_revision_ref = "kbr_" + digest_object(expected_identity)
        if revision_ref != expected_revision_ref:
            _fail("knowledge_revision_id_mismatch", f"{path}.knowledge_revision.ref", "KB ref cannot be recomputed")

        control_binding = {
            "allowed_groups": list(groups),
            "connector": event["connector"],
            "document_id": document_id,
            "media_type": event["media_type"],
            "raw_sha256": raw_sha,
            "relative_path": relative_path,
            "root_section_path": list(root_section),
            "run_id": event["run_id"],
            "source_sequence": event["sequence"],
            "source_uri": event["source_uri"],
            "source_version": event["source_version"],
            "tenant_id": tenant_id,
            "upstream_event_id": event["upstream_event_id"],
        }
        external_snapshot_body = {
            "control_binding_sha256": digest_object(control_binding),
            "crosswalk_sha256": crosswalk_sha,
            "identity_inputs": expected_identity,
            "logical_source_id": {"scheme": SOURCE_ID_SCHEME, "value": logical_source_id},
            "normalizer_revision": NORMALIZER_REVISION,
            "parser_config_sha256": producer["parser_config_sha256"],
            "parser_record_sha256": parser_record_sha,
            "raw_sha256": raw_sha,
            "raw_size_bytes": len(raw_bytes),
            "revision_ref": {"scheme": KB_REVISION_SCHEME, "value": revision_ref},
        }
        if digest_object(external_snapshot_body) != _sha256(
            knowledge["external_snapshot_sha256"],
            f"{path}.knowledge_revision.external_snapshot_sha256",
        ):
            _fail("knowledge_snapshot_hash_mismatch", f"{path}.knowledge_revision", "external KB snapshot cannot be recomputed")
        producer_crosswalk = [
            {
                "adapter_element_id": copy.deepcopy(item["adapter_element_id"]),
                "canonical_char_mapping": {
                    "mapping_status": item["canonical_mapping"]["status"],
                    "reason_code": item["canonical_mapping"]["reason_code"],
                },
                "native_element_id": copy.deepcopy(item["native_element_id"]),
                "native_location": copy.deepcopy(item["native_location"]),
                "projection_relation": item["projection_relation"],
            }
            for item in crosswalk
        ]
        producer_snapshot = {
            "kb_identity": expected_identity,
            "kb_revision_ref": revision_ref,
            "kb_revision_scheme": KB_REVISION_SCHEME,
            "normalizer_revision": NORMALIZER_REVISION,
            "parser_record_sha256": parser_record_sha,
            "parser_config_sha256": producer["parser_config_sha256"],
            "raw_sha256": raw_sha,
            "raw_size_bytes": len(raw_bytes),
            "source_id": {"scheme": SOURCE_ID_SCHEME, "value": logical_source_id},
            "crosswalk_sha256": digest_object(producer_crosswalk),
            "control_binding_sha256": digest_object(control_binding),
        }
        if digest_object(producer_snapshot) != _sha256(
            knowledge["producer_snapshot_sha256"],
            f"{path}.knowledge_revision.producer_snapshot_sha256",
        ):
            _fail(
                "producer_snapshot_hash_mismatch",
                f"{path}.knowledge_revision.producer_snapshot_sha256",
                "legacy producer snapshot cannot be recomputed from transported evidence",
            )

        raw_documents.append(
            {
                "imported": ImportedDocument(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    logical_source_id=logical_source_id,
                    source_revision_ref=revision_ref,
                    allowed_groups=groups,
                    access_snapshot_sha256=access_sha,
                    source_uri=event["source_uri"],
                    source_version=event["source_version"],
                    raw_sha256=raw_sha,
                    parser_record_sha256=parser_record_sha,
                    parse_revision_id=parse_revision,
                    elements=tuple(imported_elements),
                    evidence=tuple(evidence),
                ),
                "relative_path": relative_path,
                "raw_text": raw_text,
                "parser_record": copy.deepcopy(parser_record),
                "canonical_manifest": {
                    "mode": canonical["mode"],
                    "normalizer_revision": canonical["normalizer_revision"],
                    "sha256": canonical_sha,
                },
                "raw_manifest": {
                    "encoding": raw["encoding"],
                    "mode": raw["mode"],
                    "sha256": raw_sha,
                    "size_bytes": len(raw_bytes),
                },
                "source_event": copy.deepcopy(event),
            }
        )

    # A fresh parser scan is independent of the producer engine and validates
    # raw bytes, relative paths, parser configuration, and the full record.
    with tempfile.TemporaryDirectory(prefix="external-provenance-v2-") as temporary:
        root = Path(temporary).resolve()
        try:
            for item in raw_documents:
                candidate = root.joinpath(
                    *PurePosixPath(item["relative_path"]).parts
                ).resolve(strict=False)
                if not candidate.is_relative_to(root):
                    _fail(
                        "relative_path_escape",
                        "$.documents",
                        "materialized path escapes the isolated parser root",
                    )
                candidate.parent.mkdir(parents=True, exist_ok=True)
                resolved_parent = candidate.parent.resolve(strict=True)
                if not resolved_parent.is_relative_to(root):
                    _fail(
                        "relative_path_escape",
                        "$.documents",
                        "materialized parent escapes the isolated parser root",
                    )
                target = resolved_parent / candidate.name
                with target.open("xb") as handle:
                    handle.write(item["raw_text"].encode("utf-8"))
        except ExternalProvenanceError:
            raise
        except OSError as exc:
            raise ExternalProvenanceError(
                "fresh_parser_materialization_failed",
                "$.documents",
                type(exc).__name__,
            ) from exc
        try:
            manifest = PARSER.scan_root(
                root,
                PARSER.Limits(
                    max_files=MAX_DOCUMENTS,
                    max_file_bytes=MAX_SOURCE_BYTES,
                    max_total_bytes=MAX_DOCUMENTS * MAX_SOURCE_BYTES,
                ),
            )
        except ExternalProvenanceError:
            raise
        except (OSError, ValueError, PARSER.DocumentError) as exc:
            raise ExternalProvenanceError(
                "fresh_parser_rebuild_failed", "$.documents", type(exc).__name__
            ) from exc
        if manifest["summary"]["gate"] != "pass":
            _fail("fresh_parser_rebuild_failed", "$.documents", "local parser gate did not pass")
        if manifest["config_sha256"] != producer["parser_config_sha256"]:
            _fail("fresh_parser_config_mismatch", "$.producer_contract.parser", "local parser config differs")
        fresh_by_path = {item["relative_path"]: item for item in manifest["documents"]}
        for index, item in enumerate(raw_documents):
            fresh = fresh_by_path.get(item["relative_path"])
            if fresh is None or canonical_json(fresh) != canonical_json(item["parser_record"]):
                _fail("fresh_parser_rebuild_mismatch", f"$.documents[{index}].parser_artifact", "record differs from trusted local parse")

    imported = tuple(item["imported"] for item in raw_documents)
    by_source = {item.logical_source_id: item for item in imported}
    source_manifest = [
        {
            "canonical_representation": item["canonical_manifest"],
            "logical_source_id": {
                "scheme": SOURCE_ID_SCHEME,
                "value": item["imported"].logical_source_id,
            },
            "raw_representation": item["raw_manifest"],
            "source_event": item["source_event"],
        }
        for item in raw_documents
    ]
    return imported, by_source, source_manifest


def _validate_chunks(
    value: Any,
    *,
    documents: tuple[ImportedDocument, ...],
    by_source: Mapping[str, ImportedDocument],
    producer: Mapping[str, Any],
) -> tuple[tuple[Any, ...], dict[str, tuple[str, str]]]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_CHUNKS:
        _fail("chunks_bounds", "$.chunks", "chunk count is outside the contract")
    chunks: list[Any] = []
    routes: dict[str, tuple[str, str]] = {}
    for index, raw_chunk in enumerate(value):
        path = f"$.chunks[{index}]"
        item = _exact_fields(
            raw_chunk,
            {
                "access_snapshot_sha256",
                "allowed_groups",
                "chunk_id",
                "content_sha256",
                "element_spans",
                "family",
                "logical_source_id",
                "ordinal",
                "overlap_units",
                "retrieval_sha256",
                "retrieval_text",
                "retrieval_unit_count",
                "section_path",
                "source_revision_ref",
                "strategy_version",
                "text",
                "unit_count",
            },
            path,
        )
        chunk_id = _id_object(item["chunk_id"], CHUNK_ID_SCHEME, f"{path}.chunk_id")
        if chunk_id in routes:
            _fail("duplicate_identity", f"{path}.chunk_id", "chunk ID is duplicated")
        source_id = _id_object(item["logical_source_id"], SOURCE_ID_SCHEME, f"{path}.logical_source_id")
        document = by_source.get(source_id)
        if document is None:
            _fail("orphan_chunk", path, "chunk references unknown logical source")
        revision_ref = _id_object(item["source_revision_ref"], KB_REVISION_SCHEME, f"{path}.source_revision_ref")
        if revision_ref != document.source_revision_ref:
            _fail("chunk_route_mismatch", path, "chunk references another source revision")
        groups = _sorted_unique_strings(item["allowed_groups"], f"{path}.allowed_groups")
        if groups != document.allowed_groups:
            _fail("chunk_acl_mismatch", path, "chunk ACL differs from document")
        access_sha = _sha256(item["access_snapshot_sha256"], f"{path}.access_snapshot_sha256")
        if access_sha != document.access_snapshot_sha256:
            _fail("chunk_access_binding_mismatch", path, "chunk access snapshot differs")
        if item["strategy_version"] != producer["strategy"]:
            _fail("chunk_strategy_mismatch", f"{path}.strategy_version", "chunk strategy differs")
        text = _content_text(item["text"], f"{path}.text", maximum=MAX_SOURCE_BYTES)
        retrieval_text = _content_text(
            item["retrieval_text"], f"{path}.retrieval_text", maximum=MAX_SOURCE_BYTES
        )
        content_sha = _sha256(item["content_sha256"], f"{path}.content_sha256")
        retrieval_sha = _sha256(item["retrieval_sha256"], f"{path}.retrieval_sha256")
        if digest_text(text) != content_sha:
            _fail("chunk_content_hash_mismatch", path, "chunk content digest differs")
        if digest_text(retrieval_text) != retrieval_sha:
            _fail("chunk_retrieval_hash_mismatch", path, "chunk retrieval digest differs")
        spans_value = item["element_spans"]
        if not isinstance(spans_value, list) or not spans_value:
            _fail("chunk_spans_invalid", f"{path}.element_spans", "non-empty spans required")
        spans: list[Any] = []
        for span_index, raw_span in enumerate(spans_value):
            span_path = f"{path}.element_spans[{span_index}]"
            span = _exact_fields(raw_span, {"element_id", "unit_start", "unit_end"}, span_path)
            element_id = _id_object(span["element_id"], ELEMENT_ID_SCHEME, f"{span_path}.element_id")
            start = _integer(span["unit_start"], f"{span_path}.unit_start")
            end = _integer(span["unit_end"], f"{span_path}.unit_end", minimum=1)
            if end <= start:
                _fail("coordinate_out_of_bounds", span_path, "unit_end must exceed unit_start")
            spans.append(CHUNK.ElementSpan(element_id, start, end))
        sections = _ordered_strings(
            item["section_path"], f"{path}.section_path", nonempty=False, maximum_items=32
        )
        chunk = CHUNK.Chunk(
            chunk_id=chunk_id,
            source_id=source_id,
            source_revision=revision_ref,
            strategy_version=producer["strategy"],
            ordinal=_integer(item["ordinal"], f"{path}.ordinal", minimum=1, maximum=MAX_CHUNKS),
            family=_token(item["family"], f"{path}.family", maximum=30),
            text=text,
            retrieval_text=retrieval_text,
            unit_count=_integer(item["unit_count"], f"{path}.unit_count", minimum=1, maximum=100_000),
            retrieval_unit_count=_integer(item["retrieval_unit_count"], f"{path}.retrieval_unit_count", minimum=1, maximum=100_000),
            overlap_units=_integer(item["overlap_units"], f"{path}.overlap_units", maximum=producer["max_units"]),
            section_path=sections,
            acl=groups,
            element_spans=tuple(spans),
            content_sha256=content_sha,
            retrieval_sha256=retrieval_sha,
        )
        chunks.append(chunk)
        routes[chunk_id] = (document.tenant_id, document.document_id)

    all_elements = [element for document in documents for element in document.elements]
    config = CHUNK.ChunkConfig(
        max_units=producer["max_units"],
        overlap_units=producer["overlap_units"],
        strategy_version=producer["strategy"],
    )
    try:
        CHUNK.validate_chunks(chunks, all_elements, config)
        fresh = CHUNK.structured_chunks(all_elements, config)
    except (ValueError, CHUNK.ChunkingError) as exc:
        raise ExternalProvenanceError(
            "chunk_validation_failed", "$.chunks", str(exc)
        ) from exc
    if canonical_json([asdict(item) for item in chunks]) != canonical_json(
        [asdict(item) for item in fresh]
    ):
        _fail("fresh_chunk_rebuild_mismatch", "$.chunks", "chunks differ from trusted local rebuild")
    return tuple(chunks), routes


def _validate_index_entries(
    value: Any,
    *,
    chunks: tuple[Any, ...],
    routes: Mapping[str, tuple[str, str]],
    documents: tuple[ImportedDocument, ...],
    producer: Mapping[str, Any],
) -> tuple[tuple[ImportedIndexEntry, ...], list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_INDEX_ENTRIES:
        _fail("index_entries_bounds", "$.index_entries", "entry count is outside the contract")
    by_chunk = {chunk.chunk_id: chunk for chunk in chunks}
    doc_by_key = {(item.tenant_id, item.document_id): item for item in documents}
    entries: list[ImportedIndexEntry] = []
    seen_ids: set[str] = set()
    seen_chunks: set[str] = set()
    producer_rows: list[dict[str, Any]] = []
    normalized_values: list[dict[str, Any]] = []
    for index, raw_entry in enumerate(value):
        path = f"$.index_entries[{index}]"
        item = _exact_fields(
            raw_entry,
            {
                "access_snapshot_sha256",
                "chunk_id",
                "document_id",
                "index_entry_id",
                "index_revision",
                "logical_source_id",
                "retrieval_sha256",
                "source_revision_ref",
                "tenant_id",
            },
            path,
        )
        entry_id = _id_object(item["index_entry_id"], INDEX_ID_SCHEME, f"{path}.index_entry_id")
        if entry_id in seen_ids:
            _fail("duplicate_identity", f"{path}.index_entry_id", "entry ID is duplicated")
        seen_ids.add(entry_id)
        chunk_id = _id_object(item["chunk_id"], CHUNK_ID_SCHEME, f"{path}.chunk_id")
        if chunk_id in seen_chunks:
            _fail("duplicate_chunk_entry", path, "one chunk has multiple index entries")
        seen_chunks.add(chunk_id)
        chunk = by_chunk.get(chunk_id)
        if chunk is None:
            _fail("orphan_index_entry", path, "entry references unknown chunk")
        tenant_id = _token(item["tenant_id"], f"{path}.tenant_id")
        document_id = _token(item["document_id"], f"{path}.document_id")
        expected_route = routes.get(chunk_id)
        if expected_route != (tenant_id, document_id):
            _fail("entry_route_mismatch", path, "tenant/document route differs from chunk")
        document = doc_by_key[(tenant_id, document_id)]
        source_id = _id_object(item["logical_source_id"], SOURCE_ID_SCHEME, f"{path}.logical_source_id")
        revision_ref = _id_object(item["source_revision_ref"], KB_REVISION_SCHEME, f"{path}.source_revision_ref")
        if source_id != document.logical_source_id or revision_ref != document.source_revision_ref:
            _fail("entry_source_binding_mismatch", path, "entry source/revision differs")
        access_sha = _sha256(item["access_snapshot_sha256"], f"{path}.access_snapshot_sha256")
        if access_sha != document.access_snapshot_sha256:
            _fail("entry_access_binding_mismatch", path, "entry access snapshot differs")
        retrieval_sha = _sha256(item["retrieval_sha256"], f"{path}.retrieval_sha256")
        if retrieval_sha != chunk.retrieval_sha256:
            _fail("entry_retrieval_binding_mismatch", path, "entry retrieval digest differs")
        if item["index_revision"] != CHUNK.LEXICAL_INDEX_REVISION:
            _fail("entry_index_revision_mismatch", path, "entry index revision differs")
        try:
            expected_id = CHUNK.index_entry_id(
                chunk, index_revision=producer["index_revision"]
            )
        except (ValueError, CHUNK.ChunkingError) as exc:
            raise ExternalProvenanceError(
                "entry_identity_rebuild_failed", path, str(exc)
            ) from exc
        if entry_id != expected_id:
            _fail("entry_identity_mismatch", path, "index entry ID cannot be recomputed")
        entries.append(
            ImportedIndexEntry(
                index_entry_id=entry_id,
                chunk_id=chunk_id,
                tenant_id=tenant_id,
                document_id=document_id,
                logical_source_id=source_id,
                source_revision_ref=revision_ref,
                access_snapshot_sha256=access_sha,
                retrieval_sha256=retrieval_sha,
            )
        )
        normalized = {
            "access_snapshot_sha256": access_sha,
            "chunk_id": {"scheme": CHUNK_ID_SCHEME, "value": chunk_id},
            "document_id": document_id,
            "index_entry_id": {"scheme": INDEX_ID_SCHEME, "value": entry_id},
            "index_revision": CHUNK.LEXICAL_INDEX_REVISION,
            "logical_source_id": {"scheme": SOURCE_ID_SCHEME, "value": source_id},
            "retrieval_sha256": retrieval_sha,
            "source_revision_ref": {"scheme": KB_REVISION_SCHEME, "value": revision_ref},
            "tenant_id": tenant_id,
        }
        normalized_values.append(normalized)
        producer_rows.append(
            {
                "chunk_id": {"scheme": CHUNK_ID_SCHEME, "value": chunk_id},
                "document_key": [tenant_id, document_id],
                "index_entry_id": {"scheme": INDEX_ID_SCHEME, "value": entry_id},
                "retrieval_sha256": retrieval_sha,
            }
        )
    if seen_chunks != set(by_chunk):
        _fail("generation_coverage_mismatch", "$.index_entries", "chunks are not covered exactly once")
    expected_order = sorted(seen_ids)
    if [item.index_entry_id for item in entries] != expected_order:
        _fail("entry_order_mismatch", "$.index_entries", "entries must be sorted by typed ID value")
    producer_rows.sort(key=lambda row: row["index_entry_id"]["value"])
    return tuple(entries), normalized_values, producer_rows


def _validate_release(
    value: Any,
    *,
    documents: tuple[ImportedDocument, ...],
    entries: tuple[ImportedIndexEntry, ...],
    normalized_entries: list[dict[str, Any]],
    producer_rows: list[dict[str, Any]],
    source_manifest: list[dict[str, Any]],
    producer: Mapping[str, Any],
    authorization_revision: str,
) -> dict[str, str]:
    path = "$.release"
    item = _exact_fields(
        value,
        {
            "authorization_revision",
            "capture_artifact_sha256",
            "capture_state_sha256",
            "document_refs",
            "entry_refs",
            "entry_set_sha256",
            "evidence_level",
            "generation_id",
            "pipeline_fingerprint",
            "producer_entry_set_sha256",
            "producer_release_manifest_reference",
            "publication_mode",
            "source_manifest_sha256",
            "tombstone_state_sha256",
        },
        path,
    )
    if item["authorization_revision"] != authorization_revision:
        _fail("release_authorization_mismatch", f"{path}.authorization_revision", "release auth differs")
    if item["pipeline_fingerprint"] != producer["pipeline"]:
        _fail("release_pipeline_mismatch", f"{path}.pipeline_fingerprint", "release pipeline differs")
    if item["evidence_level"] != EVIDENCE_LEVEL:
        _fail("evidence_level_overclaim", f"{path}.evidence_level", "only document bridge is supported")
    if item["publication_mode"] != "producer-published-consumer-must-stage":
        _fail("publication_mode_mismatch", f"{path}.publication_mode", "producer cannot authorize local publish")
    generation_id = _id_object(item["generation_id"], GENERATION_ID_SCHEME, f"{path}.generation_id")
    capture_artifact = _sha256(item["capture_artifact_sha256"], f"{path}.capture_artifact_sha256")
    capture_state = _sha256(item["capture_state_sha256"], f"{path}.capture_state_sha256")
    tombstone = _sha256(item["tombstone_state_sha256"], f"{path}.tombstone_state_sha256")
    producer_entry_set = _sha256(item["producer_entry_set_sha256"], f"{path}.producer_entry_set_sha256")
    producer_manifest_reference = _exact_fields(
        item["producer_release_manifest_reference"],
        {"sha256", "verification"},
        f"{path}.producer_release_manifest_reference",
    )
    _sha256(
        producer_manifest_reference["sha256"],
        f"{path}.producer_release_manifest_reference.sha256",
    )
    if producer_manifest_reference["verification"] != "opaque-producer-reference-only":
        _fail(
            "producer_reference_contract_mismatch",
            f"{path}.producer_release_manifest_reference.verification",
            "omitted producer manifest is an opaque diagnostic reference only",
        )

    document_refs_value = item["document_refs"]
    if not isinstance(document_refs_value, list) or len(document_refs_value) != len(documents):
        _fail("generation_coverage_mismatch", f"{path}.document_refs", "document reference count differs")
    normalized_doc_refs: list[dict[str, Any]] = []
    for index, raw_ref in enumerate(document_refs_value):
        ref_path = f"{path}.document_refs[{index}]"
        ref = _exact_fields(raw_ref, {"logical_source_id", "source_revision_ref"}, ref_path)
        normalized_doc_refs.append(
            {
                "logical_source_id": {
                    "scheme": SOURCE_ID_SCHEME,
                    "value": _id_object(ref["logical_source_id"], SOURCE_ID_SCHEME, f"{ref_path}.logical_source_id"),
                },
                "source_revision_ref": {
                    "scheme": KB_REVISION_SCHEME,
                    "value": _id_object(ref["source_revision_ref"], KB_REVISION_SCHEME, f"{ref_path}.source_revision_ref"),
                },
            }
        )
    expected_doc_refs = [
        {
            "logical_source_id": {"scheme": SOURCE_ID_SCHEME, "value": doc.logical_source_id},
            "source_revision_ref": {"scheme": KB_REVISION_SCHEME, "value": doc.source_revision_ref},
        }
        for doc in documents
    ]
    if normalized_doc_refs != expected_doc_refs:
        _fail("generation_coverage_mismatch", f"{path}.document_refs", "document reference set/order differs")

    entry_refs_value = item["entry_refs"]
    if not isinstance(entry_refs_value, list) or len(entry_refs_value) != len(entries):
        _fail("generation_coverage_mismatch", f"{path}.entry_refs", "entry reference count differs")
    normalized_entry_refs = [
        _id_object(raw, INDEX_ID_SCHEME, f"{path}.entry_refs[{index}]")
        for index, raw in enumerate(entry_refs_value)
    ]
    if normalized_entry_refs != [entry.index_entry_id for entry in entries]:
        _fail("generation_coverage_mismatch", f"{path}.entry_refs", "entry reference set/order differs")
    if digest_object(normalized_entries) != _sha256(item["entry_set_sha256"], f"{path}.entry_set_sha256"):
        _fail("entry_set_hash_mismatch", f"{path}.entry_set_sha256", "external entry set digest differs")
    if digest_object(producer_rows) != producer_entry_set:
        _fail("producer_entry_set_hash_mismatch", f"{path}.producer_entry_set_sha256", "producer entry set cannot be rebuilt")
    if digest_object(source_manifest) != _sha256(item["source_manifest_sha256"], f"{path}.source_manifest_sha256"):
        _fail("source_manifest_hash_mismatch", f"{path}.source_manifest_sha256", "source manifest cannot be rebuilt")

    generation_identity = {
        "authorization_revision": authorization_revision,
        "capture_artifact_sha256": capture_artifact,
        "capture_state_sha256": capture_state,
        "evidence_level": EVIDENCE_LEVEL,
        "external_chunk_to_citation_verified": False,
        "entry_set_sha256": producer_entry_set,
        "generation_id_scheme": GENERATION_ID_SCHEME,
        "pipeline_fingerprint": producer["pipeline"],
        "publication_mode": "offline-single-process-no-concurrent-readers",
    }
    if generation_id != "xgen_" + digest_object(generation_identity):
        _fail("generation_identity_mismatch", f"{path}.generation_id", "producer generation cannot be recomputed")
    return {
        "generation_id": generation_id,
        "pipeline": producer["pipeline"],
        "authorization": authorization_revision,
        "tombstone": tombstone,
    }


def stage_external_bundle(
    serialized_bundle: str | bytes,
    policy: TrustedImportPolicy,
) -> StagedExternalBundle:
    """Validate and import an external bundle into the local *staged* state."""

    if not isinstance(policy, TrustedImportPolicy):  # Expected digest, generation, and policy must come from trusted out-of-band configuration.
        _fail("trusted_policy_required", "policy", "TrustedImportPolicy is mandatory")  # Import is impossible without a trusted policy.
    root = strict_json_loads(serialized_bundle)  # Strictly load the cross-process/cross-language bundle as JSON.
    _check_json_domain(root)  # Reject depth, NaN, duplicate keys, and other values outside the jointly defined JSON domain.
    # Verify the complete bundle pin before trusting embedded integrity or traversing the attacker-controlled deep identity graph.
    actual_bundle_sha = digest_object(root)  # Compute the SHA-256 of the complete canonical object received now.
    if actual_bundle_sha != policy.expected_bundle_sha256:  # Only a bundle that exactly matches the trusted out-of-band digest can continue.
        _fail(
            "trusted_bundle_digest_mismatch",
            "$",
            "complete bundle digest differs from out-of-band policy",
        )
    bundle = _exact_fields(  # Validate the top-level exact field set, rejecting omissions and unknown extension fields.
        root,
        {
            "schema_version",
            "canonicalization_revision",
            "producer_contract",
            "authorization_contract",
            "documents",
            "chunks",
            "index_entries",
            "release",
            "integrity",
        },
        "$",
    )
    if bundle["schema_version"] != SCHEMA_VERSION:  # The consumer understands only the explicitly tested bundle version.
        _fail("schema_version_mismatch", "$.schema_version", "unsupported external bundle")  # Do not automatically fall back to unknown schemas.
    if bundle["canonicalization_revision"] != CANONICALIZATION_REVISION:  # Hash identity relies on consistent canonicalization rules.
        _fail("canonicalization_mismatch", "$.canonicalization_revision", "unsupported canonicalization")  # Differing rules prevent digest comparison.
    integrity = _exact_fields(  # Read self-consistency metadata; it does not replace the trusted pin above.
        bundle["integrity"],
        {
            "attestation",
            "canonicalization_revision",
            "payload_sha256",
            "producer_validation",
        },
        "$.integrity",
    )
    if integrity["canonicalization_revision"] != CANONICALIZATION_REVISION:
        _fail("canonicalization_mismatch", "$.integrity.canonicalization_revision", "integrity canonicalization differs")
    attestation = _exact_fields(
        integrity["attestation"], {"mode", "trust_scope"}, "$.integrity.attestation"
    )
    if attestation != {"mode": "none", "trust_scope": "self-consistency-only"}:
        _fail("attestation_contract_mismatch", "$.integrity.attestation", "unsupported attestation envelope")
    if integrity["producer_validation"] != "fresh-local-rebuild-before-export":
        _fail("producer_validation_mismatch", "$.integrity.producer_validation", "producer validation claim differs")
    payload = {key: copy.deepcopy(value) for key, value in bundle.items() if key != "integrity"}  # Rebuild the payload claimed by integrity after removing integrity itself.
    payload_sha = _sha256(integrity["payload_sha256"], "$.integrity.payload_sha256")  # Validate that the field has the full lowercase SHA-256 shape.
    if digest_object(payload) != payload_sha:  # Reject immediately when the embedded hash does not match the actual payload.
        _fail("payload_hash_mismatch", "$.integrity.payload_sha256", "embedded self-consistency digest differs")

    producer = _validate_producer_contract(bundle["producer_contract"])  # Validate the producer pipeline, coordinate, and identity contract.
    authorization = _validate_authorization_contract(bundle["authorization_contract"])  # Validate the authorization snapshot revision declared by the bundle.
    documents, by_source, source_manifest = _validate_documents(
        bundle["documents"], producer=producer, authorization_revision=authorization
    )
    chunks, routes = _validate_chunks(
        bundle["chunks"], documents=documents, by_source=by_source, producer=producer
    )
    entries, normalized_entries, producer_rows = _validate_index_entries(
        bundle["index_entries"],
        chunks=chunks,
        routes=routes,
        documents=documents,
        producer=producer,
    )
    release = _validate_release(
        bundle["release"],
        documents=documents,
        entries=entries,
        normalized_entries=normalized_entries,
        producer_rows=producer_rows,
        source_manifest=source_manifest,
        producer=producer,
        authorization_revision=authorization,
    )
    if release["generation_id"] != policy.expected_generation_id:  # The locally reconstructed release must match the expected out-of-band generation.
        _fail("trusted_generation_mismatch", "$.release.generation_id", "generation differs from policy")
    if release["pipeline"] != policy.expected_pipeline_fingerprint:
        _fail("trusted_pipeline_mismatch", "$.release.pipeline_fingerprint", "pipeline differs from policy")
    if release["authorization"] != policy.expected_authorization_revision:
        _fail("trusted_authorization_mismatch", "$.release.authorization_revision", "authorization differs from policy")
    return _validated_stage(  # Return only a staged object with a private validation marker; it cannot be queried yet.
        status="staged",
        bundle_sha256=actual_bundle_sha,
        payload_sha256=payload_sha,
        generation_id=release["generation_id"],
        pipeline_fingerprint=release["pipeline"],
        authorization_revision=release["authorization"],
        tombstone_state_sha256=release["tombstone"],
        evidence_level=EVIDENCE_LEVEL,
        documents=documents,
        chunks=chunks,
        index_entries=entries,
    )


def publish_staged_bundle(
    staged: StagedExternalBundle,
    live_state: ConsumerLiveState,
) -> PublishedExternalBundle:
    """Publish only after consumer-owned auth/tombstone/live-deny checks."""

    if (  # Permit only the staged type just validated by this module to enter the publication function.
        type(staged) is not StagedExternalBundle
        or staged.status != "staged"
        or getattr(staged, "_validation_marker", None) is not _VALIDATED_STAGE_MARKER
    ):
        _fail("staged_bundle_required", "$", "only a validated staged bundle can publish")
    if not isinstance(live_state, ConsumerLiveState):  # Consumer-owned live state cannot be supplied by the bundle.
        _fail("live_state_required", "live", "ConsumerLiveState is mandatory")
    if live_state.authorization_revision != staged.authorization_revision:  # Reconfirm at publication time that the authorization snapshot has not changed.
        _fail("live_authorization_mismatch", "live.authorization_revision", "live authorization differs from staged release")
    if live_state.tombstone_state_sha256 != staged.tombstone_state_sha256:  # Tombstone-state drift must also block publication.
        _fail("live_tombstone_mismatch", "live.tombstone_state_sha256", "live tombstone state differs from staged release")
    document_keys = {(item.tenant_id, item.document_id) for item in staged.documents}  # List logical document identities covered by the bundle.
    if document_keys.intersection(live_state.blocked_documents):  # A current live deny cannot be bypassed by an older bundle.
        _fail("live_document_blocked", "live.blocked_documents", "a release document is blocked")
    return _locally_published(staged)  # Promote to an immutable published object only after every local live gate passes.


def _validate_query(value: Any) -> dict[str, Any]:
    item = _exact_fields(
        value,
        {
            "query_id",
            "query",
            "top_k",
        },
        "query",
    )
    return {
        "query_id": _token(item["query_id"], "query.query_id"),
        "query": _token(item["query"], "query.query", maximum=2_000),
        "top_k": _integer(item["top_k"], "query.top_k", minimum=1, maximum=MAX_TOP_K),
    }


def _query_published(
    staged: StagedExternalBundle,
    query_value: Any,
    request_context: TrustedRequestContext,
    live_state: ConsumerLiveState,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(live_state, ConsumerLiveState):
        _fail("live_state_required", "live", "ConsumerLiveState is mandatory for every query")
    if (
        type(request_context) is not TrustedRequestContext
        or getattr(request_context, "_issuance_marker", None)
        is not _TRUSTED_CONTEXT_MARKER
        or getattr(request_context, "_live_state_marker", None)
        is not live_state._context_marker
    ):
        _fail(
            "trusted_request_context_required",
            "request_context",
            "context must be issued by the exact live-state snapshot used for query",
        )
    if re.fullmatch(r"[0-9a-f]{32}", request_context.request_nonce) is None:
        _fail(
            "trusted_request_context_invalid",
            "request_context.request_nonce",
            "host-issued nonce must contain 128 bits of lowercase hexadecimal data",
        )
    query = _validate_query(query_value)
    documents = {(item.tenant_id, item.document_id): item for item in staged.documents}
    entry_by_chunk = {item.chunk_id: item for item in staged.index_entries}
    evidence_by_element = {
        evidence.element.element_id: evidence
        for document in staged.documents
        for evidence in document.evidence
    }
    groups = set(request_context.subject_groups)
    tenant_chunks: list[Any] = []
    live_chunks: list[Any] = []
    acl_chunks: list[Any] = []
    failure: dict[str, Any] | None = None
    live_contract_matches = (
        live_state.authorization_revision == staged.authorization_revision
        and live_state.tombstone_state_sha256 == staged.tombstone_state_sha256
        and request_context.authorization_revision == staged.authorization_revision
    )
    if live_contract_matches:
        for chunk in staged.chunks:
            entry = entry_by_chunk[chunk.chunk_id]
            key = (entry.tenant_id, entry.document_id)
            if entry.tenant_id != request_context.tenant_id:
                continue
            tenant_chunks.append(chunk)
            if key in live_state.blocked_documents:
                continue
            live_chunks.append(chunk)
            if groups.intersection(documents[key].allowed_groups):
                acl_chunks.append(chunk)
    else:
        failure = {"code": "consumer_live_state_mismatch", "retryable": False}
    try:
        selected = CHUNK.retrieve(
            query["query"],
            acl_chunks,
            subject_groups=request_context.subject_groups,
            k=query["top_k"],
            index_revision=CHUNK.LEXICAL_INDEX_REVISION,
        )
    except (ValueError, CHUNK.ChunkingError) as exc:
        raise ExternalProvenanceError("retrieval_failed", "query", str(exc)) from exc
    claims: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for ranked in selected:
        entry = entry_by_chunk[ranked.chunk.chunk_id]
        document = documents[(entry.tenant_id, entry.document_id)]
        for span in ranked.chunk.element_spans:
            span_key = (span.element_id, span.unit_start, span.unit_end)
            if span_key in seen:
                continue
            seen.add(span_key)
            evidence = evidence_by_element[span.element_id]
            units = CHUNK.lexical_units(evidence.element.text)
            start = units[span.unit_start].char_start
            end = units[span.unit_end - 1].char_end
            exact = evidence.element.text[start:end]
            citation_body = {
                "adapter_element_id": {
                    "scheme": ELEMENT_ID_SCHEME,
                    "value": evidence.element.element_id,
                },
                "canonical_mapping": dict(evidence.canonical_mapping),
                "chunk_id": {"scheme": CHUNK_ID_SCHEME, "value": ranked.chunk.chunk_id},
                "document_id": document.document_id,
                "exact": exact,
                "exact_sha256": digest_text(exact),
                "index_entry_id": {
                    "scheme": INDEX_ID_SCHEME,
                    "value": entry.index_entry_id,
                },
                "knowledge_revision_ref": {
                    "scheme": KB_REVISION_SCHEME,
                    "value": document.source_revision_ref,
                },
                "logical_source_id": {
                    "scheme": SOURCE_ID_SCHEME,
                    "value": document.logical_source_id,
                },
                "lexical_coordinate": {
                    "coordinate_space": LEXICAL_COORDINATE_SPACE,
                    "unit_start": span.unit_start,
                    "unit_end": span.unit_end,
                },
                "native_element_id": {
                    "scheme": PARSER_ELEMENT_SCHEME,
                    "value": evidence.native_element_id,
                },
                "native_location": dict(evidence.native_location),
                "parse_revision_id": {
                    "scheme": PARSER_REVISION_SCHEME,
                    "value": document.parse_revision_id,
                },
                "parser_record_sha256": document.parser_record_sha256,
                "prefix": evidence.element.text[max(0, start - 24) : start],
                "raw_sha256": document.raw_sha256,
                "suffix": evidence.element.text[end : end + 24],
            }
            citation = {
                "citation_id": "ecit_" + digest_object(citation_body),
                **citation_body,
            }
            claim_body = {"citations": [citation], "text": exact}
            claims.append(
                {
                    "claim_id": "eclm_"
                    + digest_object({"query_id": query["query_id"], **claim_body}),
                    **claim_body,
                }
            )
    status = "answered" if claims else "insufficient_evidence"
    trace_body = {
        "claims": claims,
        "query_id": query["query_id"],
        "status": status,
    }
    trace_id = "etr_" + digest_object(
        {
            "consumer_bundle_sha256": staged.bundle_sha256,
            "generation_id": staged.generation_id,
            "public_trace": trace_body,
            "request_nonce": request_context.request_nonce,
        }
    )
    public = {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "query_id": query["query_id"],
        "status": status,
        "claims": claims,
        "trace_id": trace_id,
    }
    selected_document_keys = sorted(
        {
            (
                entry_by_chunk[item.chunk.chunk_id].tenant_id,
                entry_by_chunk[item.chunk.chunk_id].document_id,
            )
            for item in selected
        }
    )
    audit = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "visibility": "protected",
        "trace_id": trace_id,
        "authorization_revision": staged.authorization_revision,
        "consumer_bundle_sha256": staged.bundle_sha256,
        "evidence_level": staged.evidence_level,
        "index_generation_id": {
            "scheme": GENERATION_ID_SCHEME,
            "value": staged.generation_id,
        },
        "selected_entry_ids": [
            {
                "scheme": INDEX_ID_SCHEME,
                "value": entry_by_chunk[item.chunk.chunk_id].index_entry_id,
            }
            for item in selected
        ],
        "source_bindings": [
            {
                "document_id": documents[key].document_id,
                "logical_source_id": {
                    "scheme": SOURCE_ID_SCHEME,
                    "value": documents[key].logical_source_id,
                },
                "source_uri": documents[key].source_uri,
                "source_version": documents[key].source_version,
                "tenant_id": documents[key].tenant_id,
            }
            for key in selected_document_keys
        ],
        "filter_summary": {
            "all_chunks": len(staged.chunks),
            "tenant_chunks": len(tenant_chunks),
            "live_chunks": len(live_chunks),
            "acl_chunks": len(acl_chunks),
            "selected_chunks": len(selected),
        },
        "principal_id": request_context.principal_id,
        "request_context_id": "ctx_" + digest_text(request_context.request_nonce),
        "query_binding_sha256": digest_object(
            {
                "authorization_revision": request_context.authorization_revision,
                "principal_id": request_context.principal_id,
                "query": query,
                "request_nonce": request_context.request_nonce,
                "subject_groups": list(request_context.subject_groups),
                "tenant_id": request_context.tenant_id,
            }
        ),
        "failure": failure,
    }
    return public, audit


__all__ = [
    "AUDIT_SCHEMA_VERSION",
    "ConsumerLiveState",
    "ExternalProvenanceError",
    "HostPrincipalGrant",
    "InMemoryProtectedAuditSink",
    "PublishedExternalBundle",
    "ProtectedAuditSink",
    "PUBLIC_SCHEMA_VERSION",
    "StagedExternalBundle",
    "TrustedImportPolicy",
    "TrustedRequestContext",
    "canonical_json",
    "digest_object",
    "publish_staged_bundle",
    "serialize_external_bundle",
    "stage_external_bundle",
    "strict_json_loads",
    "trusted_bundle_sha256",
]
