"""Offline, versioned provider-contract exercises for three LLM APIs.

The module deliberately does not import vendor SDKs or perform network calls.
It consumes small provider-shaped fixtures, preserves opaque provider identity,
and releases client-owned tool calls only after each provider's documented
stream terminal.  It is a focused contract harness, not a complete OpenAPI or
live-service conformance suite.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import unquote, urlsplit


FIXTURE_SCHEMA_VERSION = "provider-stream-fixture-v1"
SOURCE_CHECKED = "2026-07-21"
MAX_JSON_DEPTH = 32
MAX_STRING_CHARS = 100_000
MAX_COLLECTION_ITEMS = 4_096
MAX_STREAM_EVENTS = 4_096
MAX_OPAQUE_ID_CHARS = 512
INT32_MIN = -(2**31)
INT32_MAX = 2**31 - 1

FIXTURE_FIELDS = {
    "schema_version",
    "provider",
    "api_family",
    "api_version",
    "contract_revision",
    "fixture_layer",
    "sdk_baseline",
    "source_checked",
    "source_urls",
    "events",
}
PROVIDER_FIXTURE_PROFILES = {
    ("openai", "responses"): ("v1", "typed-sse-projection"),
    ("anthropic", "messages"): (
        "2023-06-01",
        "wire-sse-envelope-projection",
    ),
    ("google", "interactions"): ("v1", "typed-sse-projection"),
}
PROVIDER_FIXTURE_CONTRACTS = {
    ("openai", "responses"): (
        "openai-responses-reference-2026-07-21",
        "openai-python 2.46.0",
    ),
    ("anthropic", "messages"): (
        "anthropic-messages-wire-2026-07-21",
        "anthropic-python 0.117.0",
    ),
    ("google", "interactions"): (
        "gemini-interactions-ga-v1-2026-07-21",
        "google-genai 2.12.1",
    ),
}
PROVIDER_SOURCE_HOSTS = {
    ("openai", "responses"): frozenset({"developers.openai.com", "github.com"}),
    ("anthropic", "messages"): frozenset({"platform.claude.com", "github.com"}),
    ("google", "interactions"): frozenset({"ai.google.dev", "github.com"}),
}
PROVIDER_SDK_REPOSITORY_SEGMENTS = {
    ("openai", "responses"): ("openai", "openai-python"),
    ("anthropic", "messages"): ("anthropics", "anthropic-sdk-python"),
    ("google", "interactions"): ("googleapis", "python-genai"),
}
LOCAL_FIXTURE_SOURCE_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
TERMINAL_INTERACTION_STATUSES = {
    "requires_action",
    "completed",
    "failed",
    "cancelled",
    "incomplete",
}
KNOWN_INTERACTION_STATUSES = TERMINAL_INTERACTION_STATUSES | {"in_progress"}
# Stable v1 only. The v1beta MCP server steps deliberately fail closed here.
GEMINI_INTERACTION_STEP_TYPES = {
    "user_input",
    "model_output",
    "thought",
    "function_call",
    "function_result",
    "code_execution_call",
    "code_execution_result",
    "url_context_call",
    "url_context_result",
    "google_search_call",
    "google_search_result",
    "file_search_call",
    "file_search_result",
    "google_maps_call",
    "google_maps_result",
}
GEMINI_RESPONSE_FORMAT_TYPES = {"audio", "text", "image", "video"}
GEMINI_TOOL_TYPES = {
    "function",
    "code_execution",
    "url_context",
    "google_search",
    "file_search",
    "google_maps",
}
ANTHROPIC_SERVER_RESULT_BLOCK_TYPES = {
    "web_search_tool_result",
    "web_fetch_tool_result",
    "code_execution_tool_result",
    "bash_code_execution_tool_result",
    "text_editor_code_execution_tool_result",
    "tool_search_tool_result",
}
ANTHROPIC_COMPLETE_BLOCK_TYPES = ANTHROPIC_SERVER_RESULT_BLOCK_TYPES | {
    "container_upload",
    "redacted_thinking",
}


class ProviderContractError(ValueError):
    """Base class for deterministic provider-contract failures."""


class FixtureError(ProviderContractError):
    """A fixture cannot be decoded or violates its provenance envelope."""


class ProtocolError(ProviderContractError):
    """A provider event stream violates the selected versioned contract."""


class ProviderStreamError(ProviderContractError):
    """A provider emitted an in-band failure or non-success terminal."""

    def __init__(
        self,
        provider: str,
        category: str,
        message: str,
        *,
        turn_id: str | None,
        partial_call_count: int,
    ) -> None:
        _require_nonempty_string(provider, "provider", maximum=50)
        _require_nonempty_string(category, "category", maximum=100)
        _require_nonempty_string(message, "message", maximum=1_000)
        if turn_id is not None:
            _require_opaque_id(turn_id, "turn_id")
        _require_integer(
            partial_call_count,
            "partial_call_count",
            minimum=0,
            maximum=MAX_COLLECTION_ITEMS,
        )
        super().__init__(f"{provider}:{category}: {message}")
        self.provider = provider
        self.category = category
        self.turn_id = turn_id
        self.partial_call_count = partial_call_count


class UnsupportedProviderState(ProviderContractError):
    """The fixture reached a valid provider state this harness will not flatten."""


class ContinuationError(ProviderContractError):
    """Tool results cannot be bound to one exact provider turn."""


def _reject_constant(value: str) -> None:
    raise FixtureError(f"JSON forbids non-finite constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FixtureError(f"JSON contains duplicate field: {key}")
        result[key] = value
    return result


def _decode_strict_json(text: str, context: str) -> Any:
    if not isinstance(text, str):
        raise ProtocolError(f"{context} must be a JSON string")
    if len(text) > MAX_STRING_CHARS:
        raise ProtocolError(f"{context} JSON text is too long")
    _scan_json_nesting(text, context, ProtocolError)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, FixtureError, RecursionError) as exc:
        raise ProtocolError(f"{context} is not strict JSON: {exc}") from exc
    _validate_json_domain(value, path=context)
    return value


def _scan_json_nesting(
    text: str,
    context: str,
    error_type: type[ProviderContractError],
) -> None:
    """Reject pathological container nesting before json.loads recurses."""

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
            if depth > MAX_JSON_DEPTH + 1:
                raise error_type(f"{context} exceeds JSON depth {MAX_JSON_DEPTH}")
        elif character in "]}":
            depth = max(0, depth - 1)


def _snapshot_digest(value: Any) -> str:
    canonical = _canonical_json(value).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _assert_snapshot_unchanged(
    value: Any,
    expected_digest: str,
    context: str,
) -> None:
    try:
        actual_digest = _snapshot_digest(value)
    except ProviderContractError as exc:
        raise ContinuationError(f"{context} is no longer valid: {exc}") from exc
    if actual_digest != expected_digest:
        raise ContinuationError(f"{context} changed after stream parsing")


def _bounded_events(events: Iterable[Any], provider: str) -> Iterable[Any]:
    """Bound raw event count and JSON shape before provider-specific parsing."""

    for index, event in enumerate(events):
        if index >= MAX_STREAM_EVENTS:
            raise ProtocolError(
                f"{provider} stream exceeds {MAX_STREAM_EVENTS} events"
            )
        _validate_json_domain(event, path=f"{provider} event[{index}]")
        yield event


def _append_bounded_fragment(
    chunks: list[str],
    fragment: Any,
    context: str,
) -> None:
    if not isinstance(fragment, str):
        raise ProtocolError(f"{context} must be a string")
    if len(fragment) + sum(len(chunk) for chunk in chunks) > MAX_STRING_CHARS:
        raise ProtocolError(f"{context} exceeds {MAX_STRING_CHARS} characters")
    chunks.append(fragment)


def _validate_json_domain(value: Any, *, path: str = "$", depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise ProviderContractError(f"{path} exceeds JSON depth {MAX_JSON_DEPTH}")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if abs(value) > 9_007_199_254_740_991:
            raise ProviderContractError(f"{path} exceeds the portable integer range")
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ProviderContractError(f"{path} contains a non-finite number")
        return
    if isinstance(value, str):
        if len(value) > MAX_STRING_CHARS:
            raise ProviderContractError(f"{path} string is too long")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ProviderContractError(f"{path} is not valid UTF-8 text") from exc
        return
    if isinstance(value, list):
        if len(value) > MAX_COLLECTION_ITEMS:
            raise ProviderContractError(f"{path} array is too long")
        for index, item in enumerate(value):
            _validate_json_domain(item, path=f"{path}[{index}]", depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > MAX_COLLECTION_ITEMS:
            raise ProviderContractError(f"{path} object has too many fields")
        for key, item in value.items():
            if not isinstance(key, str):
                raise ProviderContractError(f"{path} contains a non-string key")
            _validate_json_domain(key, path=f"{path}.<key>", depth=depth + 1)
            _validate_json_domain(item, path=f"{path}.{key}", depth=depth + 1)
        return
    raise ProviderContractError(f"{path} is outside the portable JSON domain")


def _require_mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolError(f"{context} must be an object")
    return value


def _require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProtocolError(f"{context} must be an array")
    if len(value) > MAX_COLLECTION_ITEMS:
        raise ProtocolError(f"{context} has too many items")
    return value


def _require_fields(value: Any, required: set[str], context: str) -> dict[str, Any]:
    obj = _require_mapping(value, context)
    missing = required - set(obj)
    if missing:
        raise ProtocolError(f"{context} is missing fields: {sorted(missing)}")
    return obj


def _require_nonempty_string(value: Any, context: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProviderContractError(f"{context} must be a non-blank string")
    if len(value) > maximum:
        raise ProviderContractError(f"{context} exceeds {maximum} characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ProviderContractError(f"{context} is not valid UTF-8 text") from exc
    return value


def _require_opaque_id(value: Any, context: str) -> str:
    """Validate bounded text without relying on undocumented provider prefixes."""

    text = _require_nonempty_string(value, context, maximum=MAX_OPAQUE_ID_CHARS)
    if any(ord(character) < 32 or ord(character) == 127 for character in text):
        raise ProviderContractError(f"{context} contains a control character")
    return text


def _require_integer(value: Any, context: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProviderContractError(f"{context} must be an integer")
    if not minimum <= value <= maximum:
        raise ProviderContractError(
            f"{context} must be between {minimum} and {maximum}"
        )
    return value


def _portable_copy(value: Any, context: str) -> Any:
    try:
        _validate_json_domain(value, path=context)
    except ProviderContractError as exc:
        raise ContinuationError(str(exc)) from exc
    return copy.deepcopy(value)


def _canonical_json(value: Any) -> str:
    _validate_json_domain(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _has_percent_escape(value: str) -> bool:
    hexadecimal = "0123456789abcdefABCDEF"
    return any(
        value[index] == "%"
        and index + 2 < len(value)
        and value[index + 1] in hexadecimal
        and value[index + 2] in hexadecimal
        for index in range(len(value))
    )


def _has_malformed_percent_escape(value: str) -> bool:
    hexadecimal = "0123456789abcdefABCDEF"
    for index, character in enumerate(value):
        if character != "%":
            continue
        if (
            index + 2 >= len(value)
            or value[index + 1] not in hexadecimal
            or value[index + 2] not in hexadecimal
        ):
            return True
    return False


def _normalized_github_path_segments(path: str) -> tuple[str, ...] | None:
    """Decode a GitHub path once and reject ambiguous routing syntax."""

    if not path.startswith("/") or "\\" in path or "//" in path:
        return None
    raw_segments = path[1:].split("/")
    if raw_segments and raw_segments[-1] == "":
        raw_segments.pop()
    if not raw_segments or any(not segment for segment in raw_segments):
        return None

    normalized: list[str] = []
    for raw_segment in raw_segments:
        if _has_malformed_percent_escape(raw_segment):
            return None
        try:
            segment = unquote(raw_segment, encoding="utf-8", errors="strict")
        except UnicodeDecodeError:
            return None
        if (
            not segment
            or segment in {".", ".."}
            or "/" in segment
            or "\\" in segment
            or _has_percent_escape(segment)
            or any(
                ord(character) < 32 or ord(character) == 127
                for character in segment
            )
        ):
            return None
        normalized.append(segment)
    return tuple(normalized)


def validate_fixture(
    fixture: Any, *, allow_local_source_urls: bool = False
) -> list[str]:
    """Validate metadata hygiene, not source authenticity or every API field."""

    if type(allow_local_source_urls) is not bool:
        raise TypeError("allow_local_source_urls must be a boolean")
    errors: list[str] = []
    if not isinstance(fixture, dict):
        return ["fixture root must be an object"]
    actual = set(fixture)
    if actual != FIXTURE_FIELDS:
        errors.append(
            f"fixture fields mismatch: missing={sorted(FIXTURE_FIELDS - actual)}, "
            f"extra={sorted(actual - FIXTURE_FIELDS)}"
        )
        return errors
    if fixture["schema_version"] != FIXTURE_SCHEMA_VERSION:
        errors.append(f"schema_version must be {FIXTURE_SCHEMA_VERSION!r}")
    provider = fixture["provider"]
    api_family = fixture["api_family"]
    if not isinstance(provider, str) or not provider.strip():
        errors.append("provider must be a non-blank string")
    if not isinstance(api_family, str) or not api_family.strip():
        errors.append("api_family must be a non-blank string")
    profile: tuple[str, str] | None = None
    if isinstance(provider, str) and isinstance(api_family, str):
        profile = (provider, api_family)
        expected = PROVIDER_FIXTURE_PROFILES.get(profile)
        if expected is None:
            errors.append(f"unsupported provider profile: {profile!r}")
        else:
            expected_version, expected_layer = expected
            if fixture["api_version"] != expected_version:
                errors.append(f"api_version must be {expected_version!r}")
            if fixture["fixture_layer"] != expected_layer:
                errors.append(f"fixture_layer must be {expected_layer!r}")
            expected_revision, expected_sdk = PROVIDER_FIXTURE_CONTRACTS[profile]
            if fixture["contract_revision"] != expected_revision:
                errors.append(f"contract_revision must be {expected_revision!r}")
            if fixture["sdk_baseline"] != expected_sdk:
                errors.append(f"sdk_baseline must be {expected_sdk!r}")
    for field in ("contract_revision", "sdk_baseline"):
        value = fixture[field]
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-blank string")
    if fixture["source_checked"] != SOURCE_CHECKED:
        errors.append(f"source_checked must be {SOURCE_CHECKED!r}")
    urls = fixture["source_urls"]
    if not isinstance(urls, list) or not urls:
        errors.append("source_urls must be a non-empty array")
    else:
        seen_urls: set[str] = set()
        duplicate_url = False
        for index, url in enumerate(urls):
            if not isinstance(url, str):
                errors.append(f"source_urls[{index}] must be a string")
                continue
            if url in seen_urls:
                duplicate_url = True
            seen_urls.add(url)
            try:
                parsed = urlsplit(url)
                port = parsed.port
            except ValueError as exc:
                errors.append(f"source_urls[{index}] is not a valid URL: {exc}")
                continue
            hostname = (
                parsed.hostname.lower().rstrip(".")
                if parsed.hostname is not None
                else None
            )
            is_allowed_local = (
                allow_local_source_urls and hostname in LOCAL_FIXTURE_SOURCE_HOSTS
            )
            if (
                not hostname
                or parsed.scheme
                not in ({"http", "https"} if is_allowed_local else {"https"})
            ):
                errors.append(f"source_urls[{index}] must be an absolute HTTPS URL")
            elif parsed.username is not None or parsed.password is not None:
                errors.append(f"source_urls[{index}] must not contain URL userinfo")
            elif not is_allowed_local and port not in {None, 443}:
                errors.append(
                    f"source_urls[{index}] must use the default HTTPS port"
                )
            elif not is_allowed_local and profile in PROVIDER_SOURCE_HOSTS:
                if hostname not in PROVIDER_SOURCE_HOSTS[profile]:
                    errors.append(
                        f"source_urls[{index}] is not an approved source host "
                        f"for {profile!r}"
                    )
                elif hostname == "github.com":
                    path_segments = _normalized_github_path_segments(parsed.path)
                    repository_segments = PROVIDER_SDK_REPOSITORY_SEGMENTS[profile]
                    if (
                        path_segments is None
                        or path_segments[: len(repository_segments)]
                        != repository_segments
                    ):
                        errors.append(
                            f"source_urls[{index}] must reference the approved SDK repository"
                        )
        if duplicate_url:
            errors.append("source_urls must not contain duplicates")
    events = fixture["events"]
    if not isinstance(events, list) or not events:
        errors.append("events must be a non-empty array")
    return errors


def load_fixture(
    path: Path, *, allow_local_source_urls: bool = False
) -> dict[str, Any]:
    """Load strict UTF-8 JSON; local provenance requires an explicit test-only opt-in."""

    try:
        fixture_text = path.read_text(encoding="utf-8")
        _scan_json_nesting(fixture_text, "fixture", FixtureError)
        fixture = json.loads(
            fixture_text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise FixtureError(f"cannot read fixture: {exc}") from exc
    errors = validate_fixture(
        fixture, allow_local_source_urls=allow_local_source_urls
    )
    if errors:
        raise FixtureError("fixture validation failed:\n- " + "\n- ".join(errors))
    if not isinstance(fixture, dict):
        raise FixtureError("fixture root must be an object")
    _validate_json_domain(fixture)
    return fixture


@dataclass(frozen=True)
class ModelVisibleToolResult:
    """A projection already approved for release back to the model."""

    call_id: str
    output: str
    is_error: bool = False

    def __post_init__(self) -> None:
        _require_opaque_id(self.call_id, "call_id")
        if not isinstance(self.output, str):
            raise ContinuationError("output must be a string")
        if len(self.output) > MAX_STRING_CHARS:
            raise ContinuationError("output is too long")
        try:
            self.output.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ContinuationError("output is not valid UTF-8 text") from exc
        if not isinstance(self.is_error, bool):
            raise ContinuationError("is_error must be a boolean")


def _bind_results(
    expected_call_ids: Iterable[str],
    results: Iterable[ModelVisibleToolResult],
) -> dict[str, ModelVisibleToolResult]:
    expected = list(expected_call_ids)
    if len(expected) != len(set(expected)):
        raise ContinuationError("provider turn contains duplicate call IDs")
    bound: dict[str, ModelVisibleToolResult] = {}
    for index, result in enumerate(results):
        if not isinstance(result, ModelVisibleToolResult):
            raise ContinuationError("each result must be ModelVisibleToolResult")
        if result.call_id in bound:
            raise ContinuationError(f"duplicate result for call {result.call_id!r}")
        if index >= len(expected):
            raise ContinuationError(
                "extra tool result received before exhausting expected calls"
            )
        bound[result.call_id] = result
    missing = set(expected) - set(bound)
    extra = set(bound) - set(expected)
    if missing or extra:
        raise ContinuationError(
            f"tool result set mismatch: missing={sorted(missing)}, extra={sorted(extra)}"
        )
    return bound


def _require_observed_tool_names(
    observed_names: Iterable[str],
    declared_names: Iterable[str],
    context: str,
) -> None:
    observed = set(observed_names)
    declared = list(declared_names)
    if len(declared) != len(set(declared)):
        raise ContinuationError(f"{context} declares duplicate tool names")
    missing = observed - set(declared)
    if missing:
        raise ContinuationError(
            f"{context} is missing observed tool names: {sorted(missing)}"
        )


@dataclass(frozen=True)
class OpenAIFunctionCall:
    response_id: str
    item_id: str
    call_id: str
    name: str
    arguments: dict[str, Any]
    output_index: int
    caller: dict[str, Any] | None
    raw_item: dict[str, Any]


@dataclass(frozen=True)
class OpenAIResponsesTurn:
    response_id: str
    terminal_status: str
    calls: tuple[OpenAIFunctionCall, ...]
    raw_output: tuple[dict[str, Any], ...]
    usage: dict[str, Any] | None
    last_sequence_number: int
    unknown_events: tuple[dict[str, Any], ...]
    snapshot_digest: str


@dataclass
class _OpenAICallBuffer:
    item_id: str
    call_id: str
    name: str
    output_index: int
    caller: dict[str, Any] | None
    chunks: list[str]
    arguments_done: str | None = None
    raw_done_item: dict[str, Any] | None = None


def _openai_snapshot_payload(
    response_id: str,
    calls: Iterable[OpenAIFunctionCall],
    raw_output: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "response_id": response_id,
        "calls": [
            {
                "response_id": call.response_id,
                "item_id": call.item_id,
                "call_id": call.call_id,
                "name": call.name,
                "arguments": call.arguments,
                "output_index": call.output_index,
                "caller": call.caller,
                "raw_item": call.raw_item,
            }
            for call in calls
        ],
        "raw_output": list(raw_output),
    }


def _assert_openai_snapshot(turn: OpenAIResponsesTurn) -> None:
    _assert_snapshot_unchanged(
        _openai_snapshot_payload(turn.response_id, turn.calls, turn.raw_output),
        turn.snapshot_digest,
        "OpenAI turn snapshot",
    )


def _openai_sequence(event: dict[str, Any], previous: int | None) -> int:
    sequence = _require_integer(
        event.get("sequence_number"),
        "OpenAI event.sequence_number",
        minimum=0,
        maximum=9_007_199_254_740_991,
    )
    if previous is not None and sequence <= previous:
        raise ProtocolError("OpenAI sequence_number must be strictly increasing")
    return sequence


def _openai_response_identity(
    event: dict[str, Any],
    context: str,
    expected_id: str | None,
) -> tuple[str, dict[str, Any]]:
    response = _require_fields(event.get("response"), {"id", "status"}, context)
    response_id = _require_opaque_id(response["id"], f"{context}.id")
    _require_nonempty_string(response["status"], f"{context}.status", maximum=50)
    if expected_id is not None and response_id != expected_id:
        raise ProtocolError(f"{context}.id changed within one stream")
    return response_id, response


def _openai_function_item(value: Any, context: str) -> dict[str, Any]:
    item = _require_fields(
        value,
        {"type", "id", "call_id", "name", "arguments"},
        context,
    )
    if item["type"] != "function_call":
        raise UnsupportedProviderState(f"{context} is not a client function_call")
    namespace = item.get("namespace")
    if namespace is not None:
        raise UnsupportedProviderState(
            f"{context} uses an unsupported function namespace"
        )
    caller = item.get("caller")
    if caller is not None:
        caller_obj = _require_fields(caller, {"type"}, f"{context}.caller")
        caller_type = _require_nonempty_string(
            caller_obj["type"], f"{context}.caller.type", maximum=50
        )
        if caller_type != "direct":
            raise UnsupportedProviderState(
                f"{context} uses unsupported programmatic caller {caller_type!r}"
            )
    _require_opaque_id(item["id"], f"{context}.id")
    _require_opaque_id(item["call_id"], f"{context}.call_id")
    _require_nonempty_string(item["name"], f"{context}.name", maximum=256)
    if not isinstance(item["arguments"], str):
        raise ProtocolError(f"{context}.arguments must be a string")
    return item


def parse_openai_responses_stream(
    events: Iterable[dict[str, Any]],
) -> OpenAIResponsesTurn:
    """Parse current Responses typed SSE data and commit calls at a terminal."""

    response_id: str | None = None
    last_sequence: int | None = None
    terminal = False
    calls_by_index: dict[int, _OpenAICallBuffer] = {}
    item_to_index: dict[str, int] = {}
    added_output_indexes: set[int] = set()
    done_output_indexes: set[int] = set()
    added_item_types: dict[int, str] = {}
    done_items_by_index: dict[int, dict[str, Any]] = {}
    unknown_events: list[dict[str, Any]] = []
    raw_output: list[dict[str, Any]] = []
    usage: dict[str, Any] | None = None

    for raw_event in _bounded_events(events, "OpenAI"):
        event = _require_fields(raw_event, {"type", "sequence_number"}, "OpenAI event")
        if terminal:
            raise ProtocolError("OpenAI event received after terminal")
        last_sequence = _openai_sequence(event, last_sequence)
        event_type = _require_nonempty_string(
            event["type"], "OpenAI event.type", maximum=150
        )

        if event_type in {"response.created", "response.in_progress"}:
            current_id, response = _openai_response_identity(
                event,
                f"{event_type}.response",
                response_id,
            )
            if event_type == "response.created":
                if response_id is not None:
                    raise ProtocolError("OpenAI response.created must appear once")
                if response["status"] not in {"queued", "in_progress"}:
                    raise ProtocolError("OpenAI response.created has invalid initial status")
            elif response_id is None:
                raise ProtocolError("OpenAI response.in_progress arrived before created")
            elif response["status"] != "in_progress":
                raise ProtocolError("OpenAI response.in_progress has invalid status")
            response_id = current_id
            continue

        if response_id is None:
            raise ProtocolError("OpenAI stream event arrived before response.created")

        if event_type == "response.output_item.added":
            _require_fields(event, {"output_index", "item"}, event_type)
            output_index = _require_integer(
                event["output_index"],
                f"{event_type}.output_index",
                minimum=0,
                maximum=MAX_COLLECTION_ITEMS - 1,
            )
            if output_index in added_output_indexes:
                raise ProtocolError("OpenAI output_index was added twice")
            added_output_indexes.add(output_index)
            item = _require_fields(event["item"], {"type"}, f"{event_type}.item")
            item_type = _require_nonempty_string(
                item["type"], f"{event_type}.item.type", maximum=100
            )
            added_item_types[output_index] = item_type
            if item_type != "function_call":
                unknown_events.append(copy.deepcopy(event))
                continue
            item = _openai_function_item(item, f"{event_type}.item")
            item_id = item["id"]
            if item_id in item_to_index:
                raise ProtocolError("OpenAI item_id was added twice")
            if any(buffer.call_id == item["call_id"] for buffer in calls_by_index.values()):
                raise ProtocolError("OpenAI call_id was added twice")
            if item["arguments"] != "":
                raise ProtocolError("streamed OpenAI function_call must start with empty arguments")
            calls_by_index[output_index] = _OpenAICallBuffer(
                item_id=item_id,
                call_id=item["call_id"],
                name=item["name"],
                output_index=output_index,
                caller=copy.deepcopy(item.get("caller")),
                chunks=[],
            )
            item_to_index[item_id] = output_index
            continue

        if event_type in {
            "response.function_call_arguments.delta",
            "response.function_call_arguments.done",
        }:
            required = {"item_id", "output_index"}
            required.add("delta" if event_type.endswith(".delta") else "arguments")
            if event_type.endswith(".done"):
                required.add("name")
            _require_fields(event, required, event_type)
            output_index = _require_integer(
                event["output_index"],
                f"{event_type}.output_index",
                minimum=0,
                maximum=MAX_COLLECTION_ITEMS - 1,
            )
            item_id = _require_opaque_id(event["item_id"], f"{event_type}.item_id")
            buffer = calls_by_index.get(output_index)
            if buffer is None or buffer.item_id != item_id:
                raise ProtocolError("OpenAI argument event does not match an open call")
            if buffer.arguments_done is not None:
                raise ProtocolError("OpenAI argument event arrived after arguments.done")
            if event_type.endswith(".delta"):
                _append_bounded_fragment(
                    buffer.chunks,
                    event["delta"],
                    "OpenAI function argument delta",
                )
            else:
                name = _require_nonempty_string(
                    event["name"], f"{event_type}.name", maximum=256
                )
                arguments = event["arguments"]
                if not isinstance(arguments, str):
                    raise ProtocolError("OpenAI finalized arguments must be a string")
                if name != buffer.name:
                    raise ProtocolError("OpenAI function name changed at arguments.done")
                if "".join(buffer.chunks) != arguments:
                    raise ProtocolError("OpenAI argument deltas do not match arguments.done")
                parsed = _decode_strict_json(arguments, "OpenAI function arguments")
                if not isinstance(parsed, dict):
                    raise ProtocolError("OpenAI function arguments must decode to an object")
                buffer.arguments_done = arguments
            continue

        if event_type == "response.output_item.done":
            _require_fields(event, {"output_index", "item"}, event_type)
            output_index = _require_integer(
                event["output_index"],
                f"{event_type}.output_index",
                minimum=0,
                maximum=MAX_COLLECTION_ITEMS - 1,
            )
            if output_index in done_output_indexes:
                raise ProtocolError("OpenAI output item was completed twice")
            if output_index not in added_output_indexes:
                raise ProtocolError("OpenAI output_item.done has no matching added event")
            done_output_indexes.add(output_index)
            item = _require_fields(event["item"], {"type"}, f"{event_type}.item")
            item_type = _require_nonempty_string(
                item["type"], f"{event_type}.item.type", maximum=100
            )
            if item_type != added_item_types[output_index]:
                raise ProtocolError("OpenAI output_item.done changed the added item type")
            if item_type != "function_call":
                if output_index in calls_by_index:
                    raise ProtocolError(
                        "OpenAI output_item.done changed the added item type"
                    )
                done_items_by_index[output_index] = copy.deepcopy(item)
                raw_output.append(copy.deepcopy(item))
                continue
            item = _openai_function_item(item, f"{event_type}.item")
            buffer = calls_by_index.get(output_index)
            if buffer is None:
                raise ProtocolError("OpenAI output_item.done has no matching added event")
            if buffer.raw_done_item is not None:
                raise ProtocolError("OpenAI output item was completed twice")
            if buffer.arguments_done is None:
                raise ProtocolError("OpenAI output item completed before arguments.done")
            expected = (
                buffer.item_id,
                buffer.call_id,
                buffer.name,
                buffer.arguments_done,
                buffer.caller,
            )
            actual_item = (
                item["id"],
                item["call_id"],
                item["name"],
                item["arguments"],
                item.get("caller"),
            )
            if actual_item != expected:
                raise ProtocolError("OpenAI output_item.done changed function-call identity")
            buffer.raw_done_item = copy.deepcopy(item)
            done_items_by_index[output_index] = copy.deepcopy(item)
            raw_output.append(copy.deepcopy(item))
            continue

        if event_type in {"response.completed", "response.failed", "response.incomplete"}:
            current_id, response = _openai_response_identity(
                event, f"{event_type}.response", response_id
            )
            response_id = current_id
            status = response["status"]
            terminal = True
            expected_status = {
                "response.completed": "completed",
                "response.failed": "failed",
                "response.incomplete": "incomplete",
            }[event_type]
            if status != expected_status:
                raise ProtocolError(
                    f"OpenAI {event_type} disagrees with response status {status!r}"
                )
            if event_type != "response.completed":
                category = status
                if event_type == "response.failed":
                    detail = response.get("error")
                    if isinstance(detail, dict) and isinstance(detail.get("code"), str):
                        category = f"failed:{detail['code']}"
                else:
                    detail = response.get("incomplete_details")
                    if isinstance(detail, dict) and isinstance(detail.get("reason"), str):
                        category = f"incomplete:{detail['reason']}"
                raise ProviderStreamError(
                    "openai",
                    category,
                    f"Responses stream ended with {event_type}",
                    turn_id=response_id,
                    partial_call_count=len(calls_by_index),
                )
            raw_usage = response.get("usage")
            if raw_usage is not None:
                usage = copy.deepcopy(_require_mapping(raw_usage, "OpenAI response.usage"))
                _validate_json_domain(usage, path="OpenAI response.usage")
            output_items = _require_list(
                response.get("output"), "OpenAI response.output"
            )
            if added_output_indexes != done_output_indexes:
                raise ProtocolError(
                    "OpenAI terminal arrived before every added output item was done"
                )
            if added_output_indexes != set(range(len(output_items))):
                raise ProtocolError(
                    "OpenAI terminal output omitted or added streamed output indexes"
                )
            final_call_indexes: set[int] = set()
            checked_output: list[dict[str, Any]] = []
            for output_index, raw_item in enumerate(output_items):
                item = _require_mapping(raw_item, "OpenAI response.output item")
                done_item = done_items_by_index.get(output_index)
                if done_item is None or item != done_item:
                    raise ProtocolError(
                        "OpenAI terminal output changed a completed output item"
                    )
                checked_output.append(copy.deepcopy(item))
                if item.get("type") != "function_call":
                    continue
                final_item = _openai_function_item(
                    item, f"OpenAI response.output[{output_index}]"
                )
                buffer = calls_by_index.get(output_index)
                if buffer is None or buffer.arguments_done is None:
                    raise ProtocolError(
                        "OpenAI terminal output contains an unobserved function call"
                    )
                identity = (
                    final_item["id"],
                    final_item["call_id"],
                    final_item["name"],
                    final_item["arguments"],
                    final_item.get("caller"),
                )
                expected = (
                    buffer.item_id,
                    buffer.call_id,
                    buffer.name,
                    buffer.arguments_done,
                    buffer.caller,
                )
                if identity != expected:
                    raise ProtocolError(
                        "OpenAI terminal output changed function-call identity"
                    )
                final_call_indexes.add(output_index)
            if final_call_indexes != set(calls_by_index):
                raise ProtocolError(
                    "OpenAI terminal output omitted an observed function call"
                )
            raw_output = checked_output
            continue

        if event_type == "error":
            _require_fields(event, {"code", "message", "param"}, event_type)
            message = _require_nonempty_string(
                event["message"], "OpenAI error.message", maximum=1_000
            )
            category = event["code"] if isinstance(event["code"], str) else "stream_error"
            raise ProviderStreamError(
                "openai",
                category or "stream_error",
                message,
                turn_id=response_id,
                partial_call_count=len(calls_by_index),
            )

        unknown_events.append(copy.deepcopy(event))

    if not terminal or response_id is None or last_sequence is None:
        raise ProtocolError("OpenAI stream ended without a completed terminal")

    calls: list[OpenAIFunctionCall] = []
    for output_index in sorted(calls_by_index):
        buffer = calls_by_index[output_index]
        if buffer.arguments_done is None or buffer.raw_done_item is None:
            raise ProtocolError("OpenAI completed terminal contains a provisional call")
        parsed = _decode_strict_json(
            buffer.arguments_done,
            f"OpenAI call {buffer.call_id!r} arguments",
        )
        if not isinstance(parsed, dict):
            raise ProtocolError("OpenAI function arguments must be an object")
        calls.append(
            OpenAIFunctionCall(
                response_id=response_id,
                item_id=buffer.item_id,
                call_id=buffer.call_id,
                name=buffer.name,
                arguments=copy.deepcopy(parsed),
                output_index=output_index,
                caller=copy.deepcopy(buffer.caller),
                raw_item=copy.deepcopy(buffer.raw_done_item),
            )
        )
    turn = OpenAIResponsesTurn(
        response_id=response_id,
        terminal_status="completed",
        calls=tuple(calls),
        raw_output=tuple(raw_output),
        usage=usage,
        last_sequence_number=last_sequence,
        unknown_events=tuple(unknown_events),
        snapshot_digest="",
    )
    return OpenAIResponsesTurn(
        response_id=turn.response_id,
        terminal_status=turn.terminal_status,
        calls=turn.calls,
        raw_output=turn.raw_output,
        usage=turn.usage,
        last_sequence_number=turn.last_sequence_number,
        unknown_events=turn.unknown_events,
        snapshot_digest=_snapshot_digest(
            _openai_snapshot_payload(turn.response_id, turn.calls, turn.raw_output)
        ),
    )


def _openai_continuation_base(
    *,
    model: str,
    instructions: str,
    tools: list[dict[str, Any]],
    store: bool,
    request_controls: dict[str, Any],
) -> dict[str, Any]:
    model = _require_nonempty_string(model, "model", maximum=256)
    instructions = _require_nonempty_string(
        instructions, "instructions", maximum=MAX_STRING_CHARS
    )
    if not isinstance(tools, list) or not tools:
        raise ContinuationError("tools must be a non-empty array replayed on every turn")
    if not isinstance(store, bool):
        raise ContinuationError("store must be an explicit boolean")
    if not isinstance(request_controls, dict):
        raise ContinuationError("request_controls must be an explicit object")
    reserved = {
        "input",
        "instructions",
        "model",
        "previous_response_id",
        "store",
        "tools",
    }
    collisions = reserved & set(request_controls)
    if collisions:
        raise ContinuationError(
            f"request_controls cannot replace protected fields: {sorted(collisions)}"
        )
    safe_tools = _portable_copy(tools, "tools")
    for index, tool in enumerate(safe_tools):
        if not isinstance(tool, dict):
            raise ContinuationError(f"tools[{index}] must be an object")
        try:
            tool_type = _require_nonempty_string(
                tool.get("type"), f"tools[{index}].type", maximum=100
            )
        except ProviderContractError as exc:
            raise ContinuationError(str(exc)) from exc
        if tool_type == "function":
            try:
                _require_nonempty_string(
                    tool.get("name"), f"tools[{index}].name", maximum=256
                )
            except ProviderContractError as exc:
                raise ContinuationError(str(exc)) from exc
            if not isinstance(tool.get("parameters"), dict):
                raise ContinuationError(
                    f"tools[{index}].parameters must be an object"
                )
            if "strict" in tool and type(tool["strict"]) is not bool:
                raise ContinuationError(f"tools[{index}].strict must be a boolean")
    safe_controls = _portable_copy(request_controls, "request_controls")
    safe_controls.update(
        {
            "model": model,
            "instructions": instructions,
            "tools": safe_tools,
            "store": store,
        }
    )
    return safe_controls


def _openai_result_items(
    turn: OpenAIResponsesTurn,
    results: Iterable[ModelVisibleToolResult],
) -> list[dict[str, Any]]:
    _assert_openai_snapshot(turn)
    if not turn.calls:
        raise ContinuationError("OpenAI turn does not require function results")
    bound = _bind_results((call.call_id for call in turn.calls), results)
    items: list[dict[str, Any]] = []
    for call in turn.calls:
        item: dict[str, Any] = {
            "type": "function_call_output",
            "call_id": call.call_id,
            "output": bound[call.call_id].output,
        }
        if call.caller is not None:
            item["caller"] = copy.deepcopy(call.caller)
        items.append(item)
    return items


def build_openai_responses_continuation(
    turn: OpenAIResponsesTurn,
    results: Iterable[ModelVisibleToolResult],
    *,
    model: str,
    instructions: str,
    tools: list[dict[str, Any]],
    previous_response_was_stored: bool,
    store: bool,
    request_controls: dict[str, Any],
) -> dict[str, Any]:
    """Build an HTTP Responses continuation while replaying control config."""

    if not isinstance(turn, OpenAIResponsesTurn):
        raise ContinuationError("turn must be OpenAIResponsesTurn")
    _assert_openai_snapshot(turn)
    _require_opaque_id(turn.response_id, "response_id")
    if previous_response_was_stored is not True:
        raise ContinuationError(
            "previous_response_id requires an explicitly stored prior response"
        )
    body = _openai_continuation_base(
        model=model,
        instructions=instructions,
        tools=tools,
        store=store,
        request_controls=request_controls,
    )
    _require_observed_tool_names(
        (call.name for call in turn.calls),
        (
            tool["name"]
            for tool in body["tools"]
            if isinstance(tool, dict) and tool.get("type") == "function"
        ),
        "OpenAI tools",
    )
    body.update(
        {
            "previous_response_id": turn.response_id,
            "input": _openai_result_items(turn, results),
        }
    )
    return body


def build_openai_responses_stateless_continuation(
    turn: OpenAIResponsesTurn,
    results: Iterable[ModelVisibleToolResult],
    *,
    model: str,
    instructions: str,
    tools: list[dict[str, Any]],
    prior_input_items: list[Any],
    request_controls: dict[str, Any],
) -> dict[str, Any]:
    """Replay canonical input Items, complete output Items, and function results."""

    if not isinstance(turn, OpenAIResponsesTurn):
        raise ContinuationError("turn must be OpenAIResponsesTurn")
    _assert_openai_snapshot(turn)
    if not isinstance(prior_input_items, list) or not prior_input_items:
        raise ContinuationError(
            "prior_input_items must be the non-empty canonical input Item list"
        )
    safe_prior = _portable_copy(prior_input_items, "prior_input_items")
    for index, item in enumerate(safe_prior):
        if not isinstance(item, dict):
            raise ContinuationError(
                "prior_input_items must contain canonical input Item objects"
            )
        if "type" in item:
            if not isinstance(item["type"], str) or not item["type"].strip():
                raise ContinuationError(
                    f"prior_input_items[{index}].type must be a non-empty string"
                )
        elif not (
            item.get("role") in {"user", "assistant", "system", "developer"}
            and "content" in item
        ):
            raise ContinuationError(
                f"prior_input_items[{index}] is not a caller-validated input Item"
            )
    body = _openai_continuation_base(
        model=model,
        instructions=instructions,
        tools=tools,
        store=False,
        request_controls=request_controls,
    )
    _require_observed_tool_names(
        (call.name for call in turn.calls),
        (
            tool["name"]
            for tool in body["tools"]
            if isinstance(tool, dict) and tool.get("type") == "function"
        ),
        "OpenAI tools",
    )
    body["input"] = (
        safe_prior
        + copy.deepcopy(list(turn.raw_output))
        + _openai_result_items(turn, results)
    )
    return body


@dataclass(frozen=True)
class AnthropicToolUse:
    message_id: str
    tool_use_id: str
    name: str
    input: dict[str, Any] | None
    raw_input: str
    input_error: str | None
    block_index: int
    raw_block: dict[str, Any]


@dataclass(frozen=True)
class AnthropicMessagesTurn:
    message_id: str
    model: str
    stop_reason: str
    assistant_content: tuple[dict[str, Any], ...]
    calls: tuple[AnthropicToolUse, ...]
    recovery_calls: tuple[AnthropicToolUse, ...]
    usage: dict[str, Any]
    unknown_events: tuple[dict[str, Any], ...]
    snapshot_digest: str


@dataclass
class _AnthropicBlockBuffer:
    index: int
    block_type: str
    raw_start: dict[str, Any]
    text_chunks: list[str]
    json_chunks: list[str]
    thinking_chunks: list[str]
    signature_chunks: list[str]
    citations: list[dict[str, Any]]


def _anthropic_snapshot_payload(
    turn: AnthropicMessagesTurn,
) -> dict[str, Any]:
    def call_value(call: AnthropicToolUse) -> dict[str, Any]:
        return {
            "message_id": call.message_id,
            "tool_use_id": call.tool_use_id,
            "name": call.name,
            "input": call.input,
            "raw_input": call.raw_input,
            "input_error": call.input_error,
            "block_index": call.block_index,
            "raw_block": call.raw_block,
        }

    return {
        "message_id": turn.message_id,
        "model": turn.model,
        "stop_reason": turn.stop_reason,
        "assistant_content": list(turn.assistant_content),
        "calls": [call_value(call) for call in turn.calls],
        "recovery_calls": [call_value(call) for call in turn.recovery_calls],
        "usage": turn.usage,
        "unknown_events": list(turn.unknown_events),
    }


def _assert_anthropic_snapshot(turn: AnthropicMessagesTurn) -> None:
    _assert_snapshot_unchanged(
        _anthropic_snapshot_payload(turn),
        turn.snapshot_digest,
        "Anthropic turn snapshot",
    )


def _anthropic_envelope(value: Any) -> tuple[str, dict[str, Any]]:
    envelope = _require_fields(value, {"event", "data"}, "Anthropic SSE envelope")
    event_name = _require_nonempty_string(
        envelope["event"], "Anthropic SSE event", maximum=150
    )
    data = _require_fields(envelope["data"], {"type"}, f"Anthropic {event_name}.data")
    data_type = _require_nonempty_string(
        data["type"], f"Anthropic {event_name}.data.type", maximum=150
    )
    if data_type != event_name:
        raise ProtocolError("Anthropic SSE event name does not match data.type")
    return event_name, data


def parse_anthropic_messages_stream(
    envelopes: Iterable[dict[str, Any]],
    *,
    allow_invalid_tool_input: bool = False,
) -> AnthropicMessagesTurn:
    """Parse raw Messages SSE envelopes and commit client tools at message_stop."""

    if not isinstance(allow_invalid_tool_input, bool):
        raise ProtocolError("allow_invalid_tool_input must be a boolean")
    message_id: str | None = None
    model: str | None = None
    terminal = False
    open_block: _AnthropicBlockBuffer | None = None
    completed_blocks: dict[int, dict[str, Any]] = {}
    calls_by_index: dict[int, AnthropicToolUse] = {}
    stop_reason: str | None = None
    usage: dict[str, Any] = {}
    unknown_events: list[dict[str, Any]] = []
    phase = "before_start"

    for raw_envelope in _bounded_events(envelopes, "Anthropic"):
        event_name, data = _anthropic_envelope(raw_envelope)
        if terminal:
            raise ProtocolError("Anthropic event received after message_stop")

        if event_name == "ping":
            continue

        if event_name == "error":
            error = _require_fields(data.get("error"), {"type", "message"}, "Anthropic error")
            category = _require_nonempty_string(
                error["type"], "Anthropic error.type", maximum=150
            )
            message = _require_nonempty_string(
                error["message"], "Anthropic error.message", maximum=1_000
            )
            request_id = data.get("request_id")
            if request_id is not None:
                _require_opaque_id(request_id, "Anthropic error.request_id")
            raise ProviderStreamError(
                "anthropic",
                category,
                message,
                turn_id=message_id,
                partial_call_count=len(calls_by_index)
                + int(
                    open_block is not None
                    and open_block.block_type == "tool_use"
                ),
            )

        if event_name == "message_start":
            if message_id is not None:
                raise ProtocolError("Anthropic message_start must appear once")
            message = _require_fields(
                data.get("message"),
                {"id", "type", "role", "content", "model", "usage"},
                "Anthropic message_start.message",
            )
            if message["type"] != "message" or message["role"] != "assistant":
                raise ProtocolError("Anthropic stream must start an assistant message")
            if message["content"] != []:
                raise ProtocolError("Anthropic streamed message must start with empty content")
            message_id = _require_opaque_id(message["id"], "Anthropic message.id")
            model = _require_nonempty_string(
                message["model"], "Anthropic message.model", maximum=256
            )
            initial_usage = _require_fields(
                message["usage"],
                {"input_tokens", "output_tokens"},
                "Anthropic message_start.usage",
            )
            _require_integer(
                initial_usage["input_tokens"],
                "Anthropic usage.input_tokens",
                minimum=0,
                maximum=10_000_000_000,
            )
            _require_integer(
                initial_usage["output_tokens"],
                "Anthropic usage.output_tokens",
                minimum=0,
                maximum=10_000_000_000,
            )
            usage = copy.deepcopy(initial_usage)
            phase = "content"
            continue

        if message_id is None:
            if event_name in {
                "content_block_start",
                "content_block_delta",
                "content_block_stop",
                "message_delta",
                "message_stop",
            }:
                raise ProtocolError(
                    f"Anthropic {event_name} arrived before message_start"
                )
            unknown_events.append(copy.deepcopy(raw_envelope))
            continue

        if event_name == "content_block_start":
            if phase != "content":
                raise ProtocolError(
                    "Anthropic content block arrived after message_delta"
                )
            if open_block is not None:
                raise ProtocolError("Anthropic content blocks must not overlap")
            _require_fields(data, {"index", "content_block"}, event_name)
            index = _require_integer(
                data["index"],
                "Anthropic content block index",
                minimum=0,
                maximum=MAX_COLLECTION_ITEMS - 1,
            )
            if index in completed_blocks:
                raise ProtocolError("Anthropic content block index was reused")
            block = _require_fields(
                data["content_block"], {"type"}, "Anthropic content_block"
            )
            block_type = _require_nonempty_string(
                block["type"], "Anthropic content_block.type", maximum=100
            )
            citations: list[dict[str, Any]] = []
            if block_type in {"tool_use", "server_tool_use"}:
                label = f"Anthropic {block_type}"
                _require_fields(block, {"id", "name", "input"}, label)
                _require_opaque_id(block["id"], f"{label}.id")
                _require_nonempty_string(
                    block["name"], f"{label}.name", maximum=256
                )
                if block["input"] != {}:
                    raise ProtocolError(
                        f"streamed Anthropic {block_type} must start with empty input"
                    )
            elif block_type == "text":
                _require_fields(block, {"text"}, "Anthropic text block")
                if not isinstance(block["text"], str):
                    raise ProtocolError("Anthropic text block text must be a string")
                initial_citations = block.get("citations")
                if initial_citations is not None:
                    for citation in _require_list(
                        initial_citations, "Anthropic text block citations"
                    ):
                        citations.append(
                            copy.deepcopy(
                                _require_mapping(citation, "Anthropic text citation")
                            )
                        )
            elif block_type == "thinking":
                _require_fields(
                    block, {"thinking", "signature"}, "Anthropic thinking block"
                )
                if not isinstance(block["thinking"], str):
                    raise ProtocolError("Anthropic thinking must be a string")
                if not isinstance(block["signature"], str):
                    raise ProtocolError("Anthropic thinking signature must be a string")
            elif block_type == "redacted_thinking":
                _require_fields(block, {"data"}, "Anthropic redacted_thinking block")
                if not isinstance(block["data"], str):
                    raise ProtocolError("Anthropic redacted thinking data must be a string")
            elif block_type in ANTHROPIC_COMPLETE_BLOCK_TYPES:
                pass
            else:
                raise UnsupportedProviderState(
                    f"unsupported Anthropic content block: {block_type!r}"
                )
            open_block = _AnthropicBlockBuffer(
                index=index,
                block_type=block_type,
                raw_start=copy.deepcopy(block),
                text_chunks=[block.get("text", "")] if block_type == "text" else [],
                json_chunks=[],
                thinking_chunks=(
                    [block.get("thinking", "")] if block_type == "thinking" else []
                ),
                signature_chunks=(
                    [block.get("signature", "")] if block_type == "thinking" else []
                ),
                citations=citations,
            )
            continue

        if event_name == "content_block_delta":
            if phase != "content":
                raise ProtocolError(
                    "Anthropic content delta arrived after message_delta"
                )
            if open_block is None:
                raise ProtocolError("Anthropic content delta arrived without an open block")
            _require_fields(data, {"index", "delta"}, event_name)
            index = _require_integer(
                data["index"],
                "Anthropic content delta index",
                minimum=0,
                maximum=MAX_COLLECTION_ITEMS - 1,
            )
            if index != open_block.index:
                raise ProtocolError("Anthropic content delta index changed")
            delta = _require_fields(data["delta"], {"type"}, "Anthropic content delta")
            delta_type = delta["type"]
            if (
                open_block.block_type in {"tool_use", "server_tool_use"}
                and delta_type == "input_json_delta"
            ):
                _require_fields(delta, {"partial_json"}, "Anthropic input_json_delta")
                _append_bounded_fragment(
                    open_block.json_chunks,
                    delta["partial_json"],
                    "Anthropic partial_json",
                )
            elif open_block.block_type == "text" and delta_type == "text_delta":
                _require_fields(delta, {"text"}, "Anthropic text_delta")
                _append_bounded_fragment(
                    open_block.text_chunks,
                    delta["text"],
                    "Anthropic text delta",
                )
            elif open_block.block_type == "text" and delta_type == "citations_delta":
                citation = _require_mapping(
                    delta.get("citation"), "Anthropic citations_delta.citation"
                )
                open_block.citations.append(copy.deepcopy(citation))
            elif open_block.block_type == "thinking" and delta_type == "thinking_delta":
                _require_fields(delta, {"thinking"}, "Anthropic thinking_delta")
                _append_bounded_fragment(
                    open_block.thinking_chunks,
                    delta["thinking"],
                    "Anthropic thinking delta",
                )
            elif open_block.block_type == "thinking" and delta_type == "signature_delta":
                _require_fields(delta, {"signature"}, "Anthropic signature_delta")
                _append_bounded_fragment(
                    open_block.signature_chunks,
                    delta["signature"],
                    "Anthropic signature delta",
                )
            else:
                raise UnsupportedProviderState(
                    "Anthropic delta type does not match the open content block"
                )
            continue

        if event_name == "content_block_stop":
            if phase != "content":
                raise ProtocolError(
                    "Anthropic content block stop arrived after message_delta"
                )
            if open_block is None:
                raise ProtocolError("Anthropic content_block_stop has no open block")
            _require_fields(data, {"index"}, event_name)
            index = _require_integer(
                data["index"],
                "Anthropic content block stop index",
                minimum=0,
                maximum=MAX_COLLECTION_ITEMS - 1,
            )
            if index != open_block.index:
                raise ProtocolError("Anthropic content_block_stop index changed")
            if open_block.block_type in {"tool_use", "server_tool_use"}:
                encoded = "".join(open_block.json_chunks)
                parsed: dict[str, Any] | None
                input_error: str | None = None
                if not open_block.json_chunks or not encoded:
                    parsed = copy.deepcopy(open_block.raw_start["input"])
                else:
                    try:
                        parsed_value = _decode_strict_json(
                            encoded, f"Anthropic {open_block.block_type} input"
                        )
                        if not isinstance(parsed_value, dict):
                            raise ProtocolError(
                                f"Anthropic {open_block.block_type} input must decode to an object"
                            )
                        parsed = parsed_value
                    except ProtocolError:
                        if (
                            open_block.block_type != "tool_use"
                            or not allow_invalid_tool_input
                        ):
                            raise
                        parsed = None
                        input_error = "invalid_json"
                block = copy.deepcopy(open_block.raw_start)
                if parsed is not None:
                    block["input"] = copy.deepcopy(parsed)
                if open_block.block_type == "tool_use":
                    tool_use_id = block["id"]
                    if any(
                        call.tool_use_id == tool_use_id
                        for call in calls_by_index.values()
                    ):
                        raise ProtocolError("Anthropic tool_use ID was reused")
                    calls_by_index[index] = AnthropicToolUse(
                        message_id=message_id,
                        tool_use_id=tool_use_id,
                        name=block["name"],
                        input=copy.deepcopy(parsed),
                        raw_input=encoded,
                        input_error=input_error,
                        block_index=index,
                        raw_block=copy.deepcopy(block),
                    )
            elif open_block.block_type == "text":
                block = {
                    **copy.deepcopy(open_block.raw_start),
                    "text": "".join(open_block.text_chunks),
                }
                if open_block.citations:
                    block["citations"] = copy.deepcopy(open_block.citations)
            elif open_block.block_type == "thinking":
                block = {
                    **copy.deepcopy(open_block.raw_start),
                    "thinking": "".join(open_block.thinking_chunks),
                    "signature": "".join(open_block.signature_chunks),
                }
            else:
                block = copy.deepcopy(open_block.raw_start)
            completed_blocks[index] = block
            open_block = None
            continue

        if event_name == "message_delta":
            if open_block is not None:
                raise ProtocolError("Anthropic message_delta arrived before block stop")
            _require_fields(data, {"delta", "usage"}, event_name)
            delta = _require_mapping(data["delta"], "Anthropic message_delta.delta")
            if "stop_reason" in delta and delta["stop_reason"] is not None:
                candidate = _require_nonempty_string(
                    delta["stop_reason"], "Anthropic stop_reason", maximum=100
                )
                if stop_reason is not None and candidate != stop_reason:
                    raise ProtocolError("Anthropic stop_reason changed within one stream")
                stop_reason = candidate
            delta_usage = _require_fields(
                data["usage"], {"output_tokens"}, "Anthropic message_delta.usage"
            )
            output_tokens = _require_integer(
                delta_usage["output_tokens"],
                "Anthropic usage.output_tokens",
                minimum=0,
                maximum=10_000_000_000,
            )
            previous_output = usage.get("output_tokens", 0)
            if isinstance(previous_output, int) and output_tokens < previous_output:
                raise ProtocolError("Anthropic cumulative output_tokens moved backwards")
            usage.update(copy.deepcopy(delta_usage))
            phase = "message_delta"
            continue

        if event_name == "message_stop":
            if open_block is not None:
                raise ProtocolError("Anthropic message_stop arrived with an open block")
            if stop_reason is None:
                raise ProtocolError("Anthropic message_stop lacks a final stop_reason")
            if phase != "message_delta":
                raise ProtocolError("Anthropic message_stop arrived before message_delta")
            terminal = True
            phase = "stopped"
            continue

        unknown_events.append(copy.deepcopy(raw_envelope))

    if not terminal or message_id is None or model is None or stop_reason is None:
        raise ProtocolError("Anthropic stream ended without message_stop")
    if completed_blocks and sorted(completed_blocks) != list(range(len(completed_blocks))):
        raise ProtocolError("Anthropic content block indexes must be contiguous from zero")
    invalid_calls = [
        call for call in calls_by_index.values() if call.input_error is not None
    ]
    if calls_by_index and not (
        stop_reason == "tool_use"
        or (stop_reason == "max_tokens" and invalid_calls)
    ):
        raise ProviderStreamError(
            "anthropic",
            stop_reason,
            "client tool blocks were not committed by a tool_use terminal",
            turn_id=message_id,
            partial_call_count=len(calls_by_index),
        )
    if not calls_by_index and stop_reason == "tool_use":
        raise ProtocolError(
            "Anthropic tool_use terminal contains no client tool_use block"
        )
    if not calls_by_index and stop_reason != "end_turn":
        raise ProviderStreamError(
            "anthropic",
            stop_reason,
            "Messages stream did not end as a usable client turn",
            turn_id=message_id,
            partial_call_count=0,
        )
    ordered_blocks = tuple(
        copy.deepcopy(completed_blocks[index]) for index in sorted(completed_blocks)
    )
    ordered_calls = tuple(calls_by_index[index] for index in sorted(calls_by_index))
    if stop_reason == "tool_use":
        executable_calls = tuple(
            call for call in ordered_calls if call.input_error is None
        )
        recovery_calls = tuple(
            call for call in ordered_calls if call.input_error is not None
        )
    else:
        # A truncated turn is never executable, including complete sibling calls.
        executable_calls = ()
        recovery_calls = ordered_calls
    turn = AnthropicMessagesTurn(
        message_id=message_id,
        model=model,
        stop_reason=stop_reason,
        assistant_content=ordered_blocks,
        calls=executable_calls,
        recovery_calls=recovery_calls,
        usage=copy.deepcopy(usage),
        unknown_events=tuple(unknown_events),
        snapshot_digest="",
    )
    return AnthropicMessagesTurn(
        message_id=turn.message_id,
        model=turn.model,
        stop_reason=turn.stop_reason,
        assistant_content=turn.assistant_content,
        calls=turn.calls,
        recovery_calls=turn.recovery_calls,
        usage=turn.usage,
        unknown_events=turn.unknown_events,
        snapshot_digest=_snapshot_digest(_anthropic_snapshot_payload(turn)),
    )


def _anthropic_system_value(system: Any) -> str | list[dict[str, Any]]:
    if isinstance(system, str):
        return _require_nonempty_string(
            system, "system", maximum=MAX_STRING_CHARS
        )
    if not isinstance(system, list) or not system:
        raise ContinuationError(
            "system must be a non-empty string or text-block array"
        )
    safe_system = _portable_copy(system, "system")
    for index, block in enumerate(safe_system):
        if not isinstance(block, dict) or block.get("type") != "text":
            raise ContinuationError(f"system[{index}] must be a text block")
        text = block.get("text")
        if not isinstance(text, str):
            raise ContinuationError(f"system[{index}].text must be a string")
    return safe_system


def _anthropic_assistant_ends_server_result(message: dict[str, Any]) -> bool:
    content = message.get("content")
    return bool(
        isinstance(content, list)
        and content
        and isinstance(content[-1], dict)
        and content[-1].get("type") in ANTHROPIC_SERVER_RESULT_BLOCK_TYPES
    )


def _anthropic_tools_value(tools: Any) -> list[dict[str, Any]]:
    if not isinstance(tools, list) or not tools:
        raise ContinuationError("tools must be replayed as a non-empty array")
    safe_tools = _portable_copy(tools, "tools")
    for index, tool in enumerate(safe_tools):
        if not isinstance(tool, dict):
            raise ContinuationError(f"tools[{index}] must be an object")
        if "parameters" in tool or "strict" in tool or tool.get("type") == "function":
            raise ContinuationError(
                f"tools[{index}] uses an OpenAI/Gemini function-tool shape"
            )
        try:
            _require_nonempty_string(
                tool.get("name"), f"tools[{index}].name", maximum=256
            )
        except ProviderContractError as exc:
            raise ContinuationError(str(exc)) from exc
        if "input_schema" in tool:
            if not isinstance(tool["input_schema"], dict):
                raise ContinuationError(
                    f"tools[{index}].input_schema must be an object"
                )
        else:
            try:
                _require_nonempty_string(
                    tool.get("type"), f"tools[{index}].type", maximum=150
                )
            except ProviderContractError as exc:
                raise ContinuationError(
                    f"tools[{index}] must be a custom input_schema tool or "
                    "a typed Anthropic server tool"
                ) from exc
    return safe_tools


def build_anthropic_messages_continuation(
    turn: AnthropicMessagesTurn,
    results: Iterable[ModelVisibleToolResult],
    *,
    model: str,
    max_tokens: int,
    system: str | list[dict[str, Any]],
    tools: list[dict[str, Any]],
    prior_messages: list[dict[str, Any]],
    request_controls: dict[str, Any],
    allow_mid_conversation_system: bool = False,
) -> dict[str, Any]:
    """Build a stateless Messages request by replaying history and tool config."""

    if not isinstance(turn, AnthropicMessagesTurn):
        raise ContinuationError("turn must be AnthropicMessagesTurn")
    _assert_anthropic_snapshot(turn)
    pending_calls = tuple(
        sorted(
            (*turn.calls, *turn.recovery_calls),
            key=lambda call: call.block_index,
        )
    )
    if turn.stop_reason not in {"tool_use", "max_tokens"} or not pending_calls:
        raise ContinuationError("Anthropic turn does not require client tool results")
    model = _require_nonempty_string(model, "model", maximum=256)
    max_tokens = _require_integer(
        max_tokens, "max_tokens", minimum=1, maximum=10_000_000
    )
    safe_system = _anthropic_system_value(system)
    safe_tools = _anthropic_tools_value(tools)
    _require_observed_tool_names(
        (call.name for call in pending_calls),
        (
            tool["name"]
            for tool in safe_tools
            if isinstance(tool, dict) and "input_schema" in tool
        ),
        "Anthropic tools",
    )
    if not isinstance(prior_messages, list) or not prior_messages:
        raise ContinuationError("prior_messages must contain the pre-turn history")
    if not isinstance(request_controls, dict):
        raise ContinuationError("request_controls must be an explicit object")
    reserved = {"max_tokens", "messages", "model", "system", "tools"}
    collisions = reserved & set(request_controls)
    if collisions:
        raise ContinuationError(
            f"request_controls cannot replace protected fields: {sorted(collisions)}"
        )
    safe_controls = _portable_copy(request_controls, "request_controls")
    if not isinstance(allow_mid_conversation_system, bool):
        raise ContinuationError("allow_mid_conversation_system must be a boolean")
    safe_history = _portable_copy(prior_messages, "prior_messages")
    for index, message in enumerate(safe_history):
        if not isinstance(message, dict) or message.get("role") not in {
            "user",
            "assistant",
            "system",
        }:
            raise ContinuationError(
                f"prior_messages[{index}] has an unsupported role"
            )
        if "content" not in message:
            raise ContinuationError(f"prior_messages[{index}] lacks content")
        content = message["content"]
        if isinstance(content, str):
            continue
        if not isinstance(content, list):
            raise ContinuationError(
                f"prior_messages[{index}].content must be a string or block array"
            )
        for block_index, block in enumerate(content):
            if not isinstance(block, dict) or not isinstance(block.get("type"), str):
                raise ContinuationError(
                    f"prior_messages[{index}].content[{block_index}] "
                    "must be a typed content block"
                )
    index = 0
    while index < len(safe_history):
        if safe_history[index]["role"] != "system":
            index += 1
            continue
        if not allow_mid_conversation_system:
            raise ContinuationError(
                "mid-conversation system requires an explicit model capability"
            )
        if index == 0:
            raise ContinuationError("mid-conversation system cannot be the first message")
        previous = safe_history[index - 1]
        if previous["role"] == "assistant" and not _anthropic_assistant_ends_server_result(
            previous
        ):
            raise ContinuationError(
                "mid-conversation system cannot interrupt an assistant client-tool turn"
            )
        if previous["role"] not in {"user", "assistant", "system"}:
            raise ContinuationError("invalid mid-conversation system placement")
        run_end = index + 1
        while (
            run_end < len(safe_history)
            and safe_history[run_end]["role"] == "system"
        ):
            run_end += 1
        if run_end < len(safe_history) and safe_history[run_end]["role"] != "assistant":
            raise ContinuationError(
                "mid-conversation system must be followed by an assistant turn"
            )
        index = run_end
    bound = _bind_results((call.tool_use_id for call in pending_calls), results)
    result_blocks: list[dict[str, Any]] = []
    for call in pending_calls:
        result = bound[call.tool_use_id]
        if (call.input_error is not None or turn.stop_reason == "max_tokens") and not result.is_error:
            raise ContinuationError(
                f"call {call.tool_use_id!r} is not executable and requires is_error"
            )
        block: dict[str, Any] = {
            "type": "tool_result",
            "tool_use_id": call.tool_use_id,
            "content": result.output,
        }
        if result.is_error:
            block["is_error"] = True
        result_blocks.append(block)
    messages = safe_history + [
        {"role": "assistant", "content": copy.deepcopy(list(turn.assistant_content))},
        {"role": "user", "content": result_blocks},
    ]
    safe_controls.update(
        {
            "model": model,
            "max_tokens": max_tokens,
            "system": safe_system,
            "tools": safe_tools,
            "messages": messages,
        }
    )
    return safe_controls


@dataclass(frozen=True)
class GeminiFunctionCall:
    interaction_id: str
    call_id: str
    name: str
    arguments: dict[str, Any]
    step_index: int
    raw_step: dict[str, Any]


@dataclass(frozen=True)
class GeminiInteractionsTurn:
    interaction_id: str
    status: str
    calls: tuple[GeminiFunctionCall, ...]
    raw_steps: tuple[dict[str, Any], ...]
    raw_step_indexes: tuple[int, ...]
    usage: dict[str, Any] | None
    status_updates: tuple[str, ...]
    last_event_id: str | None
    stateless_replay_complete: bool
    opaque_step_events: tuple[dict[str, Any], ...]
    unknown_events: tuple[dict[str, Any], ...]
    snapshot_digest: str


@dataclass
class _GeminiStepBuffer:
    index: int
    call_id: str
    name: str
    initial_arguments: dict[str, Any]
    argument_chunks: list[str]
    raw_start: dict[str, Any]


@dataclass
class _GeminiOpaqueStepBuffer:
    index: int
    step_type: str
    raw_start: dict[str, Any]
    raw_events: list[dict[str, Any]]


def _gemini_snapshot_payload(turn: GeminiInteractionsTurn) -> dict[str, Any]:
    return {
        "interaction_id": turn.interaction_id,
        "status": turn.status,
        "calls": [
            {
                "interaction_id": call.interaction_id,
                "call_id": call.call_id,
                "name": call.name,
                "arguments": call.arguments,
                "step_index": call.step_index,
                "raw_step": call.raw_step,
            }
            for call in turn.calls
        ],
        "raw_steps": list(turn.raw_steps),
        "raw_step_indexes": list(turn.raw_step_indexes),
        "usage": turn.usage,
        "status_updates": list(turn.status_updates),
        "last_event_id": turn.last_event_id,
        "stateless_replay_complete": turn.stateless_replay_complete,
        "opaque_step_events": list(turn.opaque_step_events),
        "unknown_events": list(turn.unknown_events),
    }


def _assert_gemini_snapshot(turn: GeminiInteractionsTurn) -> None:
    _assert_snapshot_unchanged(
        _gemini_snapshot_payload(turn),
        turn.snapshot_digest,
        "Gemini turn snapshot",
    )


def _gemini_event_id(
    event: dict[str, Any],
    ledger: dict[str, str],
) -> tuple[bool, str | None]:
    raw_event_id = event.get("event_id")
    if raw_event_id is None:
        return False, None
    event_id = _require_opaque_id(raw_event_id, "Gemini event_id")
    fingerprint = _canonical_json(event)
    previous = ledger.get(event_id)
    if previous is None:
        ledger[event_id] = fingerprint
        return False, event_id
    if previous != fingerprint:
        raise ProtocolError("Gemini event_id was reused with different payload")
    return True, event_id


def _gemini_interaction_identity(
    event: dict[str, Any],
    context: str,
    expected_id: str | None,
) -> tuple[str, str, dict[str, Any]]:
    interaction = _require_fields(
        event.get("interaction"), {"id", "status"}, context
    )
    interaction_id = _require_opaque_id(interaction["id"], f"{context}.id")
    status = _require_nonempty_string(
        interaction["status"], f"{context}.status", maximum=100
    )
    if expected_id is not None and interaction_id != expected_id:
        raise ProtocolError(f"{context}.id changed within one stream")
    return interaction_id, status, interaction


def parse_gemini_interactions_stream(
    events: Iterable[dict[str, Any]],
) -> GeminiInteractionsTurn:
    """Parse Gemini Interactions v1 typed SSE data with event-ID deduplication."""

    interaction_id: str | None = None
    status: str | None = None
    terminal = False
    open_steps: dict[int, _GeminiStepBuffer | _GeminiOpaqueStepBuffer] = {}
    calls_by_index: dict[int, GeminiFunctionCall] = {}
    raw_steps: dict[int, dict[str, Any]] = {}
    step_order: list[int] = []
    incomplete_replay_indexes: set[int] = set()
    opaque_step_events: list[dict[str, Any]] = []
    usage: dict[str, Any] | None = None
    status_updates: list[str] = []
    event_ledger: dict[str, str] = {}
    last_event_id: str | None = None
    unknown_events: list[dict[str, Any]] = []

    for raw_event in _bounded_events(events, "Gemini"):
        event = _require_fields(raw_event, {"event_type"}, "Gemini event")
        duplicate, event_id = _gemini_event_id(event, event_ledger)
        if event_id is not None and not duplicate:
            last_event_id = event_id
        if duplicate:
            continue
        if terminal:
            raise ProtocolError("Gemini event received after interaction.completed")
        event_type = _require_nonempty_string(
            event["event_type"], "Gemini event_type", maximum=150
        )

        if event_type == "interaction.created":
            if interaction_id is not None:
                raise ProtocolError("Gemini interaction.created must appear once")
            interaction_id, status, _ = _gemini_interaction_identity(
                event, "Gemini interaction.created.interaction", None
            )
            if status != "in_progress":
                raise ProtocolError("Gemini interaction must begin in_progress")
            continue

        if event_type == "error":
            error = event.get("error")
            category = "stream_error"
            message = "Gemini Interactions emitted an error event"
            if error is not None:
                error_obj = _require_mapping(error, "Gemini error")
                if "code" in error_obj and error_obj["code"] is not None:
                    category = _require_nonempty_string(
                        error_obj["code"], "Gemini error.code", maximum=150
                    )
                if "message" in error_obj and error_obj["message"] is not None:
                    message = _require_nonempty_string(
                        error_obj["message"], "Gemini error.message", maximum=1_000
                    )
            raise ProviderStreamError(
                "google",
                category,
                message,
                turn_id=interaction_id,
                partial_call_count=len(calls_by_index)
                + sum(
                    isinstance(buffer, _GeminiStepBuffer)
                    for buffer in open_steps.values()
                ),
            )

        if interaction_id is None:
            if event_type in {
                "step.start",
                "step.delta",
                "step.stop",
                "interaction.status_update",
                "interaction.completed",
            }:
                raise ProtocolError(
                    f"Gemini {event_type} arrived before interaction.created"
                )
            unknown_events.append(copy.deepcopy(event))
            continue

        if event_type == "step.start":
            _require_fields(event, {"index", "step"}, event_type)
            index = _require_integer(
                event["index"],
                "Gemini step.start.index",
                minimum=INT32_MIN,
                maximum=INT32_MAX,
            )
            if index in open_steps or index in raw_steps:
                raise ProtocolError("Gemini step index was started twice")
            step = _require_fields(event["step"], {"type"}, "Gemini step.start.step")
            step_type = _require_nonempty_string(
                step["type"], "Gemini step type", maximum=100
            )
            if step_type not in GEMINI_INTERACTION_STEP_TYPES:
                raise UnsupportedProviderState(
                    f"unknown Gemini Interaction step type: {step_type!r}"
                )
            step_order.append(index)
            if step_type != "function_call":
                open_steps[index] = _GeminiOpaqueStepBuffer(
                    index=index,
                    step_type=step_type,
                    raw_start=copy.deepcopy(step),
                    raw_events=[copy.deepcopy(event)],
                )
                continue
            _require_fields(
                step,
                {"arguments", "id", "name"},
                "Gemini function_call step",
            )
            arguments = _require_mapping(
                step["arguments"], "Gemini function_call.arguments"
            )
            call_id = _require_opaque_id(step["id"], "Gemini function_call.id")
            name = _require_nonempty_string(
                step["name"], "Gemini function_call.name", maximum=256
            )
            if any(
                isinstance(buffer, _GeminiStepBuffer)
                and buffer.call_id == call_id
                for buffer in open_steps.values()
            ) or any(call.call_id == call_id for call in calls_by_index.values()):
                raise ProtocolError("Gemini function-call ID was reused")
            open_steps[index] = _GeminiStepBuffer(
                index=index,
                call_id=call_id,
                name=name,
                initial_arguments=copy.deepcopy(arguments),
                argument_chunks=[],
                raw_start=copy.deepcopy(step),
            )
            continue

        if event_type == "step.delta":
            _require_fields(event, {"index", "delta"}, event_type)
            index = _require_integer(
                event["index"],
                "Gemini step.delta.index",
                minimum=INT32_MIN,
                maximum=INT32_MAX,
            )
            buffer = open_steps.get(index)
            if buffer is None:
                raise ProtocolError("Gemini step.delta has no open step")
            if isinstance(buffer, _GeminiOpaqueStepBuffer):
                buffer.raw_events.append(copy.deepcopy(event))
                continue
            delta = _require_fields(event["delta"], {"type"}, "Gemini step.delta")
            if delta["type"] != "arguments_delta":
                raise UnsupportedProviderState(
                    "Gemini function_call received a non-argument delta"
                )
            arguments_delta = delta.get("arguments", "")
            if not isinstance(arguments_delta, str):
                raise ProtocolError("Gemini arguments_delta.arguments must be a string")
            if arguments_delta:
                _append_bounded_fragment(
                    buffer.argument_chunks,
                    arguments_delta,
                    "Gemini arguments delta",
                )
            continue

        if event_type == "step.stop":
            _require_fields(event, {"index"}, event_type)
            index = _require_integer(
                event["index"],
                "Gemini step.stop.index",
                minimum=INT32_MIN,
                maximum=INT32_MAX,
            )
            buffer = open_steps.pop(index, None)
            if buffer is None:
                raise ProtocolError("Gemini step.stop has no open step")
            if isinstance(buffer, _GeminiOpaqueStepBuffer):
                buffer.raw_events.append(copy.deepcopy(event))
                raw_steps[index] = copy.deepcopy(buffer.raw_start)
                incomplete_replay_indexes.add(index)
                opaque_step_events.extend(copy.deepcopy(buffer.raw_events))
                continue
            if buffer.argument_chunks:
                if buffer.initial_arguments:
                    raise ProtocolError(
                        "Gemini streamed arguments must start from an empty object"
                    )
                encoded = "".join(buffer.argument_chunks)
                parsed = _decode_strict_json(encoded, "Gemini function arguments")
                if not isinstance(parsed, dict):
                    raise ProtocolError("Gemini function arguments must decode to an object")
            else:
                parsed = copy.deepcopy(buffer.initial_arguments)
                _validate_json_domain(parsed, path="Gemini function arguments")
            raw_step = copy.deepcopy(buffer.raw_start)
            raw_step["arguments"] = copy.deepcopy(parsed)
            raw_steps[index] = copy.deepcopy(raw_step)
            calls_by_index[index] = GeminiFunctionCall(
                interaction_id=interaction_id,
                call_id=buffer.call_id,
                name=buffer.name,
                arguments=copy.deepcopy(parsed),
                step_index=index,
                raw_step=copy.deepcopy(raw_step),
            )
            continue

        if event_type == "interaction.status_update":
            _require_fields(event, {"interaction_id", "status"}, event_type)
            update_id = _require_opaque_id(
                event["interaction_id"], "Gemini status_update.interaction_id"
            )
            if update_id != interaction_id:
                raise ProtocolError("Gemini status update changed interaction ID")
            candidate = _require_nonempty_string(
                event["status"], "Gemini status_update.status", maximum=100
            )
            if candidate not in KNOWN_INTERACTION_STATUSES:
                raise UnsupportedProviderState(
                    f"unknown Gemini interaction status update: {candidate!r}"
                )
            status_updates.append(candidate)
            continue

        if event_type == "interaction.completed":
            completed_id, completed_status, interaction = _gemini_interaction_identity(
                event,
                "Gemini interaction.completed.interaction",
                interaction_id,
            )
            interaction_id = completed_id
            status = completed_status
            raw_usage = interaction.get("usage")
            if raw_usage is not None:
                usage = copy.deepcopy(_require_mapping(raw_usage, "Gemini interaction.usage"))
                _validate_json_domain(usage, path="Gemini interaction.usage")
                legacy_usage_fields = {"input_tokens", "output_tokens"} & set(usage)
                if legacy_usage_fields:
                    raise ProtocolError(
                        "Gemini Interactions usage used legacy aliases: "
                        f"{sorted(legacy_usage_fields)}"
                    )
                for field in (
                    "total_cached_tokens",
                    "total_input_tokens",
                    "total_output_tokens",
                    "total_thought_tokens",
                    "total_tokens",
                    "total_tool_use_tokens",
                ):
                    if field in usage:
                        _require_integer(
                            usage[field],
                            f"Gemini interaction.usage.{field}",
                            minimum=0,
                            maximum=10_000_000_000,
                        )
            if open_steps:
                raise ProtocolError("Gemini interaction completed with an open step")
            terminal = True
            continue

        unknown_events.append(copy.deepcopy(event))

    if not terminal or interaction_id is None or status is None:
        raise ProtocolError("Gemini stream ended without interaction.completed")
    if status not in KNOWN_INTERACTION_STATUSES:
        raise UnsupportedProviderState(f"unknown Gemini interaction status: {status!r}")
    if calls_by_index and status != "requires_action":
        raise ProviderStreamError(
            "google",
            status,
            "function calls were not committed by a requires_action terminal",
            turn_id=interaction_id,
            partial_call_count=len(calls_by_index),
        )
    if not calls_by_index and status != "completed":
        raise ProviderStreamError(
            "google",
            status,
            "interaction did not produce a usable completed turn",
            turn_id=interaction_id,
            partial_call_count=0,
        )
    turn = GeminiInteractionsTurn(
        interaction_id=interaction_id,
        status=status,
        calls=tuple(
            calls_by_index[index] for index in step_order if index in calls_by_index
        ),
        raw_steps=tuple(
            copy.deepcopy(raw_steps[index]) for index in step_order if index in raw_steps
        ),
        raw_step_indexes=tuple(index for index in step_order if index in raw_steps),
        usage=usage,
        status_updates=tuple(status_updates),
        last_event_id=last_event_id,
        stateless_replay_complete=not incomplete_replay_indexes and not unknown_events,
        opaque_step_events=tuple(opaque_step_events),
        unknown_events=tuple(unknown_events),
        snapshot_digest="",
    )
    return GeminiInteractionsTurn(
        interaction_id=turn.interaction_id,
        status=turn.status,
        calls=turn.calls,
        raw_steps=turn.raw_steps,
        raw_step_indexes=turn.raw_step_indexes,
        usage=turn.usage,
        status_updates=turn.status_updates,
        last_event_id=turn.last_event_id,
        stateless_replay_complete=turn.stateless_replay_complete,
        opaque_step_events=turn.opaque_step_events,
        unknown_events=turn.unknown_events,
        snapshot_digest=_snapshot_digest(_gemini_snapshot_payload(turn)),
    )


def _gemini_result_steps(
    turn: GeminiInteractionsTurn,
    results: Iterable[ModelVisibleToolResult],
) -> list[dict[str, Any]]:
    if turn.status != "requires_action" or not turn.calls:
        raise ContinuationError("Gemini turn does not require function results")
    bound = _bind_results((call.call_id for call in turn.calls), results)
    steps: list[dict[str, Any]] = []
    for call in turn.calls:
        result = bound[call.call_id]
        step: dict[str, Any] = {
            "type": "function_result",
            "call_id": call.call_id,
            "name": call.name,
            "result": [{"type": "text", "text": result.output}],
        }
        if result.is_error:
            step["is_error"] = True
        steps.append(step)
    return steps


def _gemini_replayed_config(
    *,
    model: str,
    tools: list[dict[str, Any]],
    system_instruction: str,
    generation_config: dict[str, Any],
    response_format: dict[str, Any] | list[dict[str, Any]] | None,
) -> dict[str, Any]:
    model = _require_nonempty_string(model, "model", maximum=256)
    if not isinstance(tools, list) or not tools:
        raise ContinuationError("tools must be replayed as a non-empty array")
    safe_tools = _portable_copy(tools, "tools")
    for index, tool in enumerate(safe_tools):
        if not isinstance(tool, dict):
            raise ContinuationError(f"tools[{index}] must be an object")
        try:
            tool_type = _require_nonempty_string(
                tool.get("type"), f"tools[{index}].type", maximum=100
            )
        except ProviderContractError as exc:
            raise ContinuationError(str(exc)) from exc
        if tool_type not in GEMINI_TOOL_TYPES:
            raise ContinuationError(
                f"tools[{index}] has an unknown Gemini type: {tool_type!r}"
            )
        if "strict" in tool:
            raise ContinuationError(
                f"tools[{index}].strict is an OpenAI field, not a Gemini tool field"
            )
        if tool_type == "function":
            try:
                _require_nonempty_string(
                    tool.get("name"), f"tools[{index}].name", maximum=256
                )
            except ProviderContractError as exc:
                raise ContinuationError(str(exc)) from exc
            if "parameters" in tool and not isinstance(tool["parameters"], dict):
                raise ContinuationError(
                    f"tools[{index}].parameters must be an object"
                )
    system_instruction = _require_nonempty_string(
        system_instruction,
        "system_instruction",
        maximum=MAX_STRING_CHARS,
    )
    if not isinstance(generation_config, dict):
        raise ContinuationError("generation_config must be an object")
    body: dict[str, Any] = {
        "model": model,
        "tools": safe_tools,
        "system_instruction": system_instruction,
        "generation_config": _portable_copy(
            generation_config, "generation_config"
        ),
    }
    if response_format is not None:
        safe_format = _portable_copy(response_format, "response_format")
        formats = safe_format if isinstance(safe_format, list) else [safe_format]
        if not formats or any(not isinstance(value, dict) for value in formats):
            raise ContinuationError(
                "response_format must be an object or a non-empty object array"
            )
        for index, value in enumerate(formats):
            try:
                format_type = _require_nonempty_string(
                    value.get("type"),
                    f"response_format[{index}].type",
                    maximum=100,
                )
            except ProviderContractError as exc:
                raise ContinuationError(str(exc)) from exc
            if format_type not in GEMINI_RESPONSE_FORMAT_TYPES:
                raise ContinuationError(
                    f"response_format[{index}] has an unknown Gemini type: "
                    f"{format_type!r}"
                )
            if (
                format_type == "text"
                and "mime_type" in value
                and (
                    not isinstance(value["mime_type"], str)
                    or value["mime_type"] not in {"application/json", "text/plain"}
                )
            ):
                raise ContinuationError(
                    f"response_format[{index}].mime_type is not a Gemini text MIME type"
                )
            if "schema" in value:
                if format_type != "text" or value.get("mime_type") != "application/json":
                    raise ContinuationError(
                        "Gemini JSON schema requires type='text' and "
                        "mime_type='application/json'"
                    )
                if not isinstance(value["schema"], dict):
                    raise ContinuationError(
                        f"response_format[{index}].schema must be an object"
                    )
        body["response_format"] = safe_format
    return body


def build_gemini_interactions_stateful_continuation(
    turn: GeminiInteractionsTurn,
    results: Iterable[ModelVisibleToolResult],
    *,
    model: str,
    tools: list[dict[str, Any]],
    system_instruction: str,
    generation_config: dict[str, Any],
    previous_interaction_was_stored: bool,
    store: bool,
    response_format: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Continue from a stored predecessor and choose storage for the new turn."""

    if not isinstance(turn, GeminiInteractionsTurn):
        raise ContinuationError("turn must be GeminiInteractionsTurn")
    _assert_gemini_snapshot(turn)
    if previous_interaction_was_stored is not True:
        raise ContinuationError(
            "previous_interaction_id requires an explicitly stored interaction"
        )
    if type(store) is not bool:
        raise ContinuationError("store must be a boolean for the new interaction")
    body = _gemini_replayed_config(
        model=model,
        tools=tools,
        system_instruction=system_instruction,
        generation_config=generation_config,
        response_format=response_format,
    )
    _require_observed_tool_names(
        (call.name for call in turn.calls),
        (
            tool["name"]
            for tool in body["tools"]
            if isinstance(tool, dict) and tool.get("type") == "function"
        ),
        "Gemini tools",
    )
    body.update(
        {
            "store": store,
            "previous_interaction_id": turn.interaction_id,
            "input": _gemini_result_steps(turn, results),
        }
    )
    return body


def build_gemini_interactions_stateless_continuation(
    turn: GeminiInteractionsTurn,
    results: Iterable[ModelVisibleToolResult],
    *,
    model: str,
    tools: list[dict[str, Any]],
    system_instruction: str,
    generation_config: dict[str, Any],
    prior_input_steps: list[dict[str, Any]] | None,
    response_format: dict[str, Any] | list[dict[str, Any]] | None = None,
    complete_steps: list[dict[str, Any]] | None = None,
    complete_steps_source: str | None = None,
    complete_steps_interaction_id: str | None = None,
) -> dict[str, Any]:
    """Build store:false history from canonical Step arrays and bound provenance."""

    if not isinstance(turn, GeminiInteractionsTurn):
        raise ContinuationError("turn must be GeminiInteractionsTurn")
    _assert_gemini_snapshot(turn)
    if complete_steps is None:
        if complete_steps_source is not None or complete_steps_interaction_id is not None:
            raise ContinuationError(
                "complete_steps provenance cannot be supplied without complete_steps"
            )
        if not turn.stateless_replay_complete:
            raise ContinuationError(
                "stateless replay needs a complete non-streaming steps snapshot"
            )
        replay_input = _validated_gemini_prior_steps(prior_input_steps)
        replay_steps = copy.deepcopy(list(turn.raw_steps))
    else:
        replay_steps, includes_input_history = _validated_gemini_steps_snapshot(
            turn,
            complete_steps,
            source=complete_steps_source,
            interaction_id=complete_steps_interaction_id,
        )
        if includes_input_history:
            if prior_input_steps is not None:
                raise ContinuationError(
                    "GET steps already include input history; prior_input_steps would duplicate it"
                )
            replay_input = []
        else:
            replay_input = _validated_gemini_prior_steps(prior_input_steps)
    replay_input = replay_input + replay_steps + _gemini_result_steps(turn, results)
    body = _gemini_replayed_config(
        model=model,
        tools=tools,
        system_instruction=system_instruction,
        generation_config=generation_config,
        response_format=response_format,
    )
    _require_observed_tool_names(
        (call.name for call in turn.calls),
        (
            tool["name"]
            for tool in body["tools"]
            if isinstance(tool, dict) and tool.get("type") == "function"
        ),
        "Gemini tools",
    )
    body.update({"store": False, "input": replay_input})
    return body


def _validated_gemini_steps_snapshot(
    turn: GeminiInteractionsTurn,
    complete_steps: list[dict[str, Any]],
    *,
    source: str | None,
    interaction_id: str | None,
) -> tuple[list[dict[str, Any]], bool]:
    """Bind create/GET snapshots without treating SSE indexes as array offsets."""

    if not isinstance(complete_steps, list) or not complete_steps:
        raise ContinuationError("complete_steps must be a non-empty array")
    if not isinstance(source, str) or source not in {"create", "get"}:
        raise ContinuationError("complete_steps_source must be 'create' or 'get'")
    try:
        snapshot_interaction_id = _require_opaque_id(
            interaction_id,
            "complete_steps_interaction_id",
        )
    except ProviderContractError as exc:
        raise ContinuationError(str(exc)) from exc
    if snapshot_interaction_id != turn.interaction_id:
        raise ContinuationError("complete_steps belongs to a different interaction")
    safe_steps = _validated_gemini_step_array(complete_steps, "complete_steps")

    expected_types = [step["type"] for step in turn.raw_steps]
    unsupported_snapshot_types = set(expected_types) - {"thought", "function_call"}
    if unsupported_snapshot_types:
        raise ContinuationError(
            "this harness cannot prove stateless replay fidelity for opaque "
            f"Gemini step types: {sorted(unsupported_snapshot_types)}"
        )
    if source == "create":
        if any(step["type"] == "user_input" for step in safe_steps):
            raise ContinuationError(
                "create response steps must contain only model-generated steps"
            )
        current_steps = safe_steps
        includes_input_history = False
    else:
        if not any(step["type"] == "user_input" for step in safe_steps):
            raise ContinuationError(
                "GET steps snapshot must include its user_input history"
            )
        if len(safe_steps) <= len(expected_types):
            raise ContinuationError(
                "GET steps snapshot omitted input history or model-generated steps"
            )
        current_steps = safe_steps[-len(expected_types) :]
        includes_input_history = True
    if [step["type"] for step in current_steps] != expected_types:
        raise ContinuationError(
            "complete_steps changed or omitted the observed model-step sequence"
        )

    expected = {call.call_id: call for call in turn.calls}
    observed: dict[str, dict[str, Any]] = {}
    for index, (raw_step, raw_index, value) in enumerate(
        zip(turn.raw_steps, turn.raw_step_indexes, current_steps)
    ):
        step_type = value["type"]
        _validate_gemini_observed_step_fields(
            raw_step,
            value,
            context=f"complete_steps current step {index}",
        )
        if step_type == "thought":
            _validate_gemini_thought_snapshot(
                turn,
                raw_index=raw_index,
                raw_step=raw_step,
                snapshot=value,
                context=f"complete_steps current step {index}",
            )
        if step_type != "function_call":
            continue
        try:
            _require_fields(
                value,
                {"id", "name", "arguments"},
                f"complete_steps[{index}]",
            )
            call_id = _require_opaque_id(value["id"], f"complete_steps[{index}].id")
            name = _require_nonempty_string(
                value["name"], f"complete_steps[{index}].name", maximum=256
            )
            arguments = _require_mapping(
                value["arguments"], f"complete_steps[{index}].arguments"
            )
        except ProviderContractError as exc:
            raise ContinuationError(str(exc)) from exc
        if call_id in observed:
            raise ContinuationError(f"complete_steps repeats function call {call_id!r}")
        call = expected.get(call_id)
        if call is None:
            raise ContinuationError(
                f"complete_steps contains unobserved function call {call_id!r}"
            )
        if name != call.name or arguments != call.arguments:
            raise ContinuationError(
                f"complete_steps changed function call {call_id!r}"
            )
        observed[call_id] = value
    missing = set(expected) - set(observed)
    if missing:
        raise ContinuationError(
            f"complete_steps omitted function calls: {sorted(missing)}"
        )
    return safe_steps, includes_input_history


def _validated_gemini_step_array(
    steps: Any,
    context: str,
) -> list[dict[str, Any]]:
    if not isinstance(steps, list) or not steps:
        raise ContinuationError(f"{context} must be a non-empty Step array")
    safe_steps = _portable_copy(steps, context)
    for index, step in enumerate(safe_steps):
        if not isinstance(step, dict):
            raise ContinuationError(f"{context}[{index}] must be an object")
        step_type = step.get("type")
        if not isinstance(step_type, str) or step_type not in GEMINI_INTERACTION_STEP_TYPES:
            raise ContinuationError(
                f"{context}[{index}] has an unknown Step type: {step_type!r}"
            )
    return safe_steps


def _validated_gemini_prior_steps(
    prior_input_steps: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    safe_steps = _validated_gemini_step_array(
        prior_input_steps,
        "prior_input_steps",
    )
    if safe_steps[0].get("type") != "user_input":
        raise ContinuationError(
            "prior_input_steps must start with the initial user_input Step"
        )
    calls: dict[str, str] = {}
    results: set[str] = set()
    for index, step in enumerate(safe_steps):
        step_type = step["type"]
        if step_type == "user_input":
            if "content" not in step:
                raise ContinuationError(
                    f"prior_input_steps[{index}] user_input lacks content"
                )
        elif step_type == "function_call":
            try:
                _require_fields(
                    step,
                    {"id", "name", "arguments"},
                    f"prior_input_steps[{index}]",
                )
                call_id = _require_opaque_id(
                    step["id"], f"prior_input_steps[{index}].id"
                )
                name = _require_nonempty_string(
                    step["name"], f"prior_input_steps[{index}].name", maximum=256
                )
                _require_mapping(
                    step["arguments"], f"prior_input_steps[{index}].arguments"
                )
            except ProviderContractError as exc:
                raise ContinuationError(str(exc)) from exc
            if call_id in calls:
                raise ContinuationError(
                    f"prior_input_steps repeats function call {call_id!r}"
                )
            calls[call_id] = name
        elif step_type == "function_result":
            try:
                _require_fields(
                    step,
                    {"call_id", "result"},
                    f"prior_input_steps[{index}]",
                )
                call_id = _require_opaque_id(
                    step["call_id"], f"prior_input_steps[{index}].call_id"
                )
            except ProviderContractError as exc:
                raise ContinuationError(str(exc)) from exc
            if call_id not in calls:
                raise ContinuationError(
                    f"prior_input_steps has an orphan function result {call_id!r}"
                )
            if call_id in results:
                raise ContinuationError(
                    f"prior_input_steps repeats function result {call_id!r}"
                )
            if "name" in step and step["name"] != calls[call_id]:
                raise ContinuationError(
                    f"prior_input_steps function result changed name for {call_id!r}"
                )
            results.add(call_id)
    missing_results = set(calls) - results
    if missing_results:
        raise ContinuationError(
            "prior_input_steps omits function results: "
            f"{sorted(missing_results)}"
        )
    return safe_steps


def _is_empty_stream_placeholder(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _validate_gemini_observed_step_fields(
    raw_step: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    context: str,
) -> None:
    for field, observed_value in raw_step.items():
        if _is_empty_stream_placeholder(observed_value):
            continue
        if field not in snapshot or snapshot[field] != observed_value:
            raise ContinuationError(
                f"{context} changed observed field {field!r}"
            )


def _validate_gemini_thought_snapshot(
    turn: GeminiInteractionsTurn,
    *,
    raw_index: int,
    raw_step: dict[str, Any],
    snapshot: dict[str, Any],
    context: str,
) -> None:
    summary: list[Any] = []
    raw_summary = raw_step.get("summary")
    if isinstance(raw_summary, list):
        summary.extend(copy.deepcopy(raw_summary))
    signatures: list[str] = []
    raw_signature = raw_step.get("signature")
    if isinstance(raw_signature, str) and raw_signature:
        signatures.append(raw_signature)
    for event in turn.opaque_step_events:
        if event.get("event_type") != "step.delta" or event.get("index") != raw_index:
            continue
        delta = event.get("delta")
        if not isinstance(delta, dict):
            continue
        if delta.get("type") == "thought_summary" and delta.get("content") is not None:
            summary.append(copy.deepcopy(delta["content"]))
        if delta.get("type") == "thought_signature":
            signature = delta.get("signature")
            if isinstance(signature, str) and signature:
                signatures.append(signature)
    if summary and snapshot.get("summary") != summary:
        raise ContinuationError(f"{context} changed or omitted thought summary")
    if signatures:
        if len(set(signatures)) != 1:
            raise ContinuationError(f"{context} observed conflicting thought signatures")
        if snapshot.get("signature") != signatures[0]:
            raise ContinuationError(f"{context} changed or omitted thought signature")
