"""Build a deterministic, provenance-aware context pack without model APIs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Sequence, TextIO


DEFAULT_FIXTURE = Path(__file__).with_name("chunks.json")
OUTPUT_SCHEMA = Path(__file__).with_name("context-pack.schema.json")
ALLOWED_SECTIONS = ("policy", "state", "evidence", "current-input")
SECTION_ORDER = {name: index for index, name in enumerate(ALLOWED_SECTIONS)}
ALLOWED_TRUST = frozenset(
    {
        "application-policy",
        "confirmed-state",
        "approved-source",
        "user-input",
        "unverified",
    }
)
EXCLUSION_REASONS = frozenset(
    {
        "permission_denied",
        "trust_denied",
        "not_yet_effective",
        "expired",
        "duplicate",
        "budget",
    }
)
ROOT_FIELDS = frozenset(
    {"fixture_version", "selector_version", "request", "chunks"}
)
REQUEST_FIELDS = frozenset(
    {"as_of", "pack_budget_tokens", "granted_permissions", "allowed_trust"}
)
CHUNK_FIELDS = frozenset(
    {
        "id",
        "section",
        "source_uri",
        "source_version",
        "effective_from",
        "expires_on",
        "required_permission",
        "trust",
        "dedupe_key",
        "estimated_tokens",
        "priority",
        "required",
        "content",
    }
)
IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
URI_PATTERN = re.compile(r"^[a-z][a-z0-9+.-]*://\S+$")
MAX_BUDGET_TOKENS = 10_000_000
MAX_CONTENT_CHARS = 10_000


class ContextPackError(ValueError):
    """Base class for fixture and selection failures."""


@dataclass(frozen=True)
class RequestPolicy:
    as_of: date
    pack_budget_tokens: int
    granted_permissions: frozenset[str]
    allowed_trust: frozenset[str]


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    section: str
    source_uri: str
    source_version: str
    effective_from: date
    expires_on: date | None
    required_permission: str
    trust: str
    dedupe_key: str
    estimated_tokens: int
    priority: int
    required: bool
    content: str


@dataclass(frozen=True)
class Fixture:
    fixture_version: str
    selector_version: str
    request: RequestPolicy
    chunks: tuple[Chunk, ...]


@dataclass(frozen=True)
class Exclusion:
    chunk_id: str
    reason: str


@dataclass(frozen=True)
class ContextPack:
    fixture_version: str
    selector_version: str
    as_of: date
    budget_tokens: int
    used_tokens: int
    selected: tuple[Chunk, ...]
    excluded: tuple[Exclusion, ...]

    @property
    def remaining_tokens(self) -> int:
        return self.budget_tokens - self.used_tokens

    def as_dict(self) -> dict[str, Any]:
        return {
            "fixture_version": self.fixture_version,
            "selector_version": self.selector_version,
            "as_of": self.as_of.isoformat(),
            "budget_tokens": self.budget_tokens,
            "used_tokens": self.used_tokens,
            "remaining_tokens": self.remaining_tokens,
            "selected": [
                {
                    "id": chunk.chunk_id,
                    "section": chunk.section,
                    "source_uri": chunk.source_uri,
                    "source_version": chunk.source_version,
                    "effective_from": chunk.effective_from.isoformat(),
                    "expires_on": (
                        chunk.expires_on.isoformat()
                        if chunk.expires_on is not None
                        else None
                    ),
                    "trust": chunk.trust,
                    "required": chunk.required,
                    "estimated_tokens": chunk.estimated_tokens,
                    "content": chunk.content,
                }
                for chunk in self.selected
            ],
            "excluded": [
                {"id": item.chunk_id, "reason": item.reason}
                for item in self.excluded
            ],
        }


def _reject_constant(value: str) -> None:
    raise ContextPackError(f"non-finite JSON number is not allowed: {value}")


def _object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContextPackError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json_strict(text: str, context: str) -> Any:
    if not isinstance(text, str) or not text.strip():
        raise ContextPackError(f"{context} must be non-blank JSON text")
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ContextPackError(
            f"{context} is invalid JSON at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContextPackError(f"{context} must be a JSON object")
    return value


def _require_exact_fields(
    value: dict[str, Any], expected: frozenset[str], context: str
) -> None:
    actual = set(value)
    missing = expected - actual
    unknown = actual - expected
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing={sorted(missing)}")
        if unknown:
            details.append(f"unknown={sorted(unknown)}")
        raise ContextPackError(
            f"{context} has invalid fields: {', '.join(details)}"
        )


def _require_text(
    value: Any,
    context: str,
    *,
    maximum: int = 200,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContextPackError(f"{context} must be a non-blank string")
    text = value.strip()
    if len(text) > maximum:
        raise ContextPackError(f"{context} exceeds {maximum} characters")
    return text


def _require_identifier(value: Any, context: str) -> str:
    text = _require_text(value, context, maximum=64)
    if not IDENTIFIER_PATTERN.fullmatch(text):
        raise ContextPackError(
            f"{context} must match {IDENTIFIER_PATTERN.pattern}"
        )
    return text


def _require_integer(
    value: Any,
    context: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContextPackError(f"{context} must be an integer")
    if not minimum <= value <= maximum:
        raise ContextPackError(
            f"{context} must be between {minimum} and {maximum}"
        )
    return value


def _require_date(value: Any, context: str) -> date:
    text = _require_text(value, context, maximum=10)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ContextPackError(f"{context} must use YYYY-MM-DD") from exc
    if parsed.isoformat() != text:
        raise ContextPackError(f"{context} must use YYYY-MM-DD")
    return parsed


def _require_string_list(
    value: Any,
    context: str,
    *,
    allowed: frozenset[str] | None = None,
) -> frozenset[str]:
    if not isinstance(value, list) or not value:
        raise ContextPackError(f"{context} must be a non-empty array")
    items = [
        _require_identifier(item, f"{context}[{index}]")
        for index, item in enumerate(value)
    ]
    if len(set(items)) != len(items):
        raise ContextPackError(f"{context} values must be unique")
    if allowed is not None:
        unsupported = set(items) - allowed
        if unsupported:
            raise ContextPackError(
                f"{context} contains unsupported values: {sorted(unsupported)}"
            )
    return frozenset(items)


def _parse_request(raw: Any) -> RequestPolicy:
    value = _require_object(raw, "request")
    _require_exact_fields(value, REQUEST_FIELDS, "request")
    return RequestPolicy(
        as_of=_require_date(value["as_of"], "request.as_of"),
        pack_budget_tokens=_require_integer(
            value["pack_budget_tokens"],
            "request.pack_budget_tokens",
            minimum=1,
            maximum=MAX_BUDGET_TOKENS,
        ),
        granted_permissions=_require_string_list(
            value["granted_permissions"], "request.granted_permissions"
        ),
        allowed_trust=_require_string_list(
            value["allowed_trust"],
            "request.allowed_trust",
            allowed=ALLOWED_TRUST,
        ),
    )


def _parse_chunk(raw: Any, index: int) -> Chunk:
    context = f"chunks[{index}]"
    value = _require_object(raw, context)
    _require_exact_fields(value, CHUNK_FIELDS, context)

    section = _require_text(value["section"], f"{context}.section")
    if section not in SECTION_ORDER:
        raise ContextPackError(f"{context}.section is unsupported: {section!r}")

    source_uri = _require_text(
        value["source_uri"], f"{context}.source_uri", maximum=300
    )
    if not URI_PATTERN.fullmatch(source_uri):
        raise ContextPackError(f"{context}.source_uri must be an absolute URI")

    trust = _require_text(value["trust"], f"{context}.trust")
    if trust not in ALLOWED_TRUST:
        raise ContextPackError(f"{context}.trust is unsupported: {trust!r}")

    effective_from = _require_date(
        value["effective_from"], f"{context}.effective_from"
    )
    expires_raw = value["expires_on"]
    expires_on = (
        None
        if expires_raw is None
        else _require_date(expires_raw, f"{context}.expires_on")
    )
    if expires_on is not None and expires_on <= effective_from:
        raise ContextPackError(
            f"{context}.expires_on must be later than effective_from"
        )

    required = value["required"]
    if not isinstance(required, bool):
        raise ContextPackError(f"{context}.required must be a boolean")

    return Chunk(
        chunk_id=_require_identifier(value["id"], f"{context}.id"),
        section=section,
        source_uri=source_uri,
        source_version=_require_text(
            value["source_version"], f"{context}.source_version", maximum=80
        ),
        effective_from=effective_from,
        expires_on=expires_on,
        required_permission=_require_identifier(
            value["required_permission"], f"{context}.required_permission"
        ),
        trust=trust,
        dedupe_key=_require_identifier(
            value["dedupe_key"], f"{context}.dedupe_key"
        ),
        estimated_tokens=_require_integer(
            value["estimated_tokens"],
            f"{context}.estimated_tokens",
            minimum=1,
            maximum=MAX_BUDGET_TOKENS,
        ),
        priority=_require_integer(
            value["priority"],
            f"{context}.priority",
            minimum=0,
            maximum=100,
        ),
        required=required,
        content=_require_text(
            value["content"],
            f"{context}.content",
            maximum=MAX_CONTENT_CHARS,
        ),
    )


def load_fixture(path: Path) -> Fixture:
    """Load and validate a strict, versioned context-selection fixture."""
    if not path.is_file():
        raise ContextPackError(f"fixture does not exist: {path}")
    root = _require_object(
        parse_json_strict(path.read_text(encoding="utf-8"), str(path)), "root"
    )
    _require_exact_fields(root, ROOT_FIELDS, "root")
    raw_chunks = root["chunks"]
    if not isinstance(raw_chunks, list) or not 1 <= len(raw_chunks) <= 500:
        raise ContextPackError("chunks must contain 1 to 500 entries")
    chunks = tuple(_parse_chunk(raw, index) for index, raw in enumerate(raw_chunks))

    ids = [chunk.chunk_id for chunk in chunks]
    if len(set(ids)) != len(ids):
        raise ContextPackError("chunk ids must be unique")
    groups: dict[str, list[Chunk]] = {}
    for chunk in chunks:
        groups.setdefault(chunk.dedupe_key, []).append(chunk)
    ambiguous_required = sorted(
        key
        for key, members in groups.items()
        if len(members) > 1 and any(member.required for member in members)
    )
    if ambiguous_required:
        raise ContextPackError(
            "required chunks cannot share a dedupe_key: "
            f"{ambiguous_required}"
        )

    return Fixture(
        fixture_version=_require_identifier(
            root["fixture_version"], "fixture_version"
        ),
        selector_version=_require_identifier(
            root["selector_version"], "selector_version"
        ),
        request=_parse_request(root["request"]),
        chunks=chunks,
    )


def _eligibility_reason(chunk: Chunk, request: RequestPolicy) -> str | None:
    if chunk.required_permission not in request.granted_permissions:
        return "permission_denied"
    if chunk.trust not in request.allowed_trust:
        return "trust_denied"
    if chunk.effective_from > request.as_of:
        return "not_yet_effective"
    if chunk.expires_on is not None and request.as_of >= chunk.expires_on:
        return "expired"
    return None


def _preference_key(chunk: Chunk) -> tuple[int, int, int, str]:
    return (
        -chunk.priority,
        -chunk.effective_from.toordinal(),
        chunk.estimated_tokens,
        chunk.chunk_id,
    )


def _output_order(chunk: Chunk) -> tuple[int, int, int, str]:
    return (
        SECTION_ORDER[chunk.section],
        0 if chunk.required else 1,
        -chunk.priority,
        chunk.chunk_id,
    )


def build_context_pack(fixture: Fixture) -> ContextPack:
    """Apply access, date, dedupe, and budget gates in a fixed order."""
    request = fixture.request
    eligible: list[Chunk] = []
    excluded: list[Exclusion] = []

    for chunk in sorted(fixture.chunks, key=lambda item: item.chunk_id):
        reason = _eligibility_reason(chunk, request)
        if reason is None:
            eligible.append(chunk)
            continue
        if chunk.required:
            raise ContextPackError(
                f"required chunk {chunk.chunk_id!r} failed gate: {reason}"
            )
        excluded.append(Exclusion(chunk.chunk_id, reason))

    deduped: list[Chunk] = []
    groups: dict[str, list[Chunk]] = {}
    for chunk in eligible:
        groups.setdefault(chunk.dedupe_key, []).append(chunk)
    for key in sorted(groups):
        members = sorted(groups[key], key=_preference_key)
        deduped.append(members[0])
        excluded.extend(
            Exclusion(chunk.chunk_id, "duplicate") for chunk in members[1:]
        )

    required = sorted(
        (chunk for chunk in deduped if chunk.required), key=_output_order
    )
    used = sum(chunk.estimated_tokens for chunk in required)
    if used > request.pack_budget_tokens:
        raise ContextPackError(
            "required chunks exceed the pack budget; split or compress the task"
        )

    selected = list(required)
    optional = sorted(
        (chunk for chunk in deduped if not chunk.required), key=_preference_key
    )
    for chunk in optional:
        if used + chunk.estimated_tokens <= request.pack_budget_tokens:
            selected.append(chunk)
            used += chunk.estimated_tokens
        else:
            excluded.append(Exclusion(chunk.chunk_id, "budget"))

    selected.sort(key=_output_order)
    excluded.sort(key=lambda item: item.chunk_id)
    if used > request.pack_budget_tokens:
        raise ContextPackError("internal error: selected chunks exceed budget")
    if any(chunk.required and chunk not in selected for chunk in fixture.chunks):
        raise ContextPackError("internal error: a required chunk was not selected")
    if len({chunk.chunk_id for chunk in selected}) != len(selected):
        raise ContextPackError("internal error: duplicate selected chunk ids")

    return ContextPack(
        fixture_version=fixture.fixture_version,
        selector_version=fixture.selector_version,
        as_of=request.as_of,
        budget_tokens=request.pack_budget_tokens,
        used_tokens=used,
        selected=tuple(selected),
        excluded=tuple(excluded),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a deterministic context pack from explicit estimates."
    )
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--json-pack", type=Path)
    return parser


def run(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        fixture = load_fixture(args.fixture)
        pack = build_context_pack(fixture)
        print(
            f"budget={pack.budget_tokens} used={pack.used_tokens} "
            f"remaining={pack.remaining_tokens}",
            file=stdout,
        )
        print(
            "selected: " + ", ".join(chunk.chunk_id for chunk in pack.selected),
            file=stdout,
        )
        print(
            "excluded: "
            + (
                ", ".join(
                    f"{item.chunk_id}({item.reason})" for item in pack.excluded
                )
                or "none"
            ),
            file=stdout,
        )
        if args.json_pack is not None:
            args.json_pack.parent.mkdir(parents=True, exist_ok=True)
            args.json_pack.write_text(
                json.dumps(
                    pack.as_dict(), ensure_ascii=False, indent=2, sort_keys=True
                )
                + "\n",
                encoding="utf-8",
            )
            print(f"wrote {args.json_pack.resolve()}", file=stdout)
        return 0
    except (ContextPackError, OSError) as exc:
        print(f"context pack error: {exc}", file=stderr)
        return 2


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
