"""Offline Tool Result v2 reference implementation.

The module uses only the Python standard library and performs no network calls.
It demonstrates the trusted host boundary around model-proposed tool calls:
strict input/output contracts, authorization, bound approval, idempotency,
explicit unknown-outcome reconciliation, dual result projections, and
schema-only provider adapters.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Callable


FIXTURE_SCHEMA_VERSION = "tool-cases-v2"
MODEL_RESULT_SCHEMA_VERSION = "tool-model-result-v2"
AUDIT_SCHEMA_VERSION = "tool-audit-v2"
DISPATCHER_REVISION = "offline-dispatcher-v2"
MAX_FIXTURE_BYTES = 65_536
MAX_JSON_DEPTH = 32
MAX_IDENTIFIER_CHARS = 255
MAX_ROLES = 32
MAX_CASES = 256
MAX_STEPS_PER_CASE = 256
MAX_PORTABLE_UNIX_SECONDS = 253_402_300_799  # 9999-12-31T23:59:59Z
APPROVAL_TTL_SECONDS = 60
DEFAULT_APPROVER_ID = "human-reviewer-1"
AUTHORIZED_APPROVER_IDS = frozenset({DEFAULT_APPROVER_ID})
UTC_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

ROOT_FIELDS = {"schema_version", "contract", "cases"}
CONTRACT_FIELDS = {"model_result", "protected_audit"}
CASE_FIELDS = {"id", "principal", "steps"}
PRINCIPAL_FIELDS = {"tenant_id", "subject_id", "roles"}
STEP_FIELDS = {
    "step_id",
    "action",
    "proposal",
    "execution_context",
    "approval",
    "now",
    "failure",
    "status_ref_from",
    "expected",
}
PROPOSAL_FIELDS = {"name", "arguments"}
CONTEXT_FIELDS = {
    "provider",
    "api_family",
    "response_id",
    "call_id",
    "operation_id",
    "idempotency_key",
    "adapter_revision",
}
EXPECTED_FIELDS = {
    "code",
    "status",
    "outcome",
    "recovery",
    "delivery",
    "data",
    "side_effect_count",
}

PACKAGE_FIELDS = {"model_result", "protected_audit"}
MODEL_RESULT_FIELDS = {
    "schema_version",
    "status",
    "data",
    "error",
    "execution",
    "provenance",
}
MODEL_ERROR_FIELDS = {
    "code",
    "category",
    "safe_message",
    "recovery",
    "retry_after_ms",
}
EXECUTION_FIELDS = {"outcome", "delivery", "complete", "truncated"}
PROVENANCE_FIELDS = {
    "source_label",
    "producer_revision",
    "resource_revision",
    "observed_at",
    "trust",
}
AUDIT_FIELDS = {
    "schema_version",
    "visibility",
    "operation_id",
    "principal_ref",
    "provider_context",
    "tool_contract",
    "binding",
    "downstream",
    "redactions",
}
PROVIDER_CONTEXT_FIELDS = {
    "provider",
    "api_family",
    "response_id",
    "call_id",
    "adapter_revision",
}
TOOL_CONTRACT_FIELDS = {
    "name",
    "input_schema_revision",
    "output_schema_revision",
    "effect_revision",
    "handler_revision",
    "producer_revision",
    "policy_revision",
}
BINDING_FIELDS = {"request_sha256", "result_sha256", "call_binding_sha256"}
DOWNSTREAM_FIELDS = {"request_id", "receipt_id", "status_ref"}

VALID_APPROVAL_MODES = {"none", "valid", "expired", "mismatched"}
VALID_ACTIONS = {"dispatch", "query_status"}
VALID_FAILURES = {
    "none",
    "timeout_before_execute",
    "timeout_after_commit",
    "timeout_after_commit_receipt_unavailable",
    "rate_limit",
    "tool_error",
}
VALID_STATUSES = {"succeeded", "failed", "unknown"}
VALID_OUTCOMES = {"not_started", "committed", "unknown"}
VALID_RECOVERIES = {
    "none",
    "correct_input",
    "request_approval",
    "retry_after",
    "query_status",
    "human_review",
}
VALID_DELIVERIES = {"fresh", "local_replay", "receipt_reconciled"}
VALID_TRUST = {"untrusted_data", "trusted_control"}
PROVIDER_PROFILES = {
    ("openai", "responses"): "openai-responses-v1",
    ("anthropic", "messages"): "anthropic-messages-v1",
    ("google", "interactions"): "gemini-interactions-v1",
}
HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RFC3339_UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
STATUS_REF_PATTERN = re.compile(r"^status_[0-9a-f]{32}$")
SENSITIVE_OR_CONTROL_KEYS = {
    "authorization",
    "api_key",
    "access_token",
    "refresh_token",
    "password",
    "secret",
    "cookie",
    "set_cookie",
    "call_id",
    "operation_id",
    "request_digest",
    "request_sha256",
    "result_sha256",
    "call_binding_sha256",
}


class FixtureError(ValueError):
    """Raised when a fixture violates its exact JSON contract."""


class FixtureIOError(FixtureError):
    """Raised when a fixture cannot be read without exposing its path."""


class ResultContractError(ValueError):
    """Raised when an invalid package reaches a provider adapter."""


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    subject_id: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class ModelProposal:
    """Fields accepted from a model/provider tool proposal."""

    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ExecutionContext:
    """Correlation fields supplied by the trusted host adapter."""

    call_id: str
    operation_id: str
    idempotency_key: str | None
    provider: str = "openai"
    api_family: str = "responses"
    response_id: str = "response-local"
    adapter_revision: str = "openai-responses-v1"


@dataclass(frozen=True)
class ToolCall:
    """Host-internal call after proposal/context binding."""

    call_id: str
    operation_id: str
    name: str
    arguments: dict[str, Any]
    idempotency_key: str | None
    provider: str = "openai"
    api_family: str = "responses"
    response_id: str = "response-local"
    adapter_revision: str = "openai-responses-v1"


def bind_tool_call(proposal: ModelProposal, context: ExecutionContext) -> ToolCall:
    """Bind model-controlled intent to host-controlled correlation metadata."""

    return ToolCall(
        call_id=context.call_id,
        operation_id=context.operation_id,
        name=proposal.name,
        arguments=copy.deepcopy(proposal.arguments),
        idempotency_key=context.idempotency_key,
        provider=context.provider,
        api_family=context.api_family,
        response_id=context.response_id,
        adapter_revision=context.adapter_revision,
    )


@dataclass(frozen=True)
class Approval:
    approval_id: str
    operation_id: str
    call_id: str
    provider: str
    api_family: str
    adapter_revision: str
    idempotency_key: str | None
    tool_name: str
    subject_id: str
    schema_version: str
    approval_revision: str
    approval_digest: str
    expires_at: int
    approver_id: str


@dataclass(frozen=True)
class ArgumentRule:
    python_type: type
    min_length: int | None = None
    max_length: int | None = None
    enum: frozenset[str] | None = None


@dataclass(frozen=True)
class OutputRule:
    python_type: type
    min_length: int | None = None
    max_length: int | None = None
    enum: frozenset[str] | None = None
    pattern: re.Pattern[str] | None = None
    equals_argument: str | None = None


@dataclass(frozen=True)
class HandlerResult:
    """Raw handler output; metadata is checked against the trusted registry."""

    data: dict[str, Any]
    producer_revision: str
    resource_revision: str | None
    observed_at: str
    downstream_request_id: str | None = None
    receipt_id: str | None = None


@dataclass(frozen=True)
class ToolSpec:
    schema_version: str
    approval_revision: str
    risk: str
    arguments: dict[str, ArgumentRule]
    output_schema_revision: str
    output: dict[str, OutputRule]
    max_output_bytes: int
    max_output_depth: int
    effect_revision: str
    handler_revision: str
    producer_label: str
    producer_revision: str
    timeout_ms: int
    business_validator: Callable[[Principal, dict[str, Any]], bool]
    handler: Callable[[dict[str, Any]], HandlerResult]


@dataclass(frozen=True)
class IdempotencyRecord:
    request_sha256: str
    provider: str
    api_family: str
    adapter_revision: str
    data: dict[str, Any]
    source_label: str
    producer_revision: str
    resource_revision: str | None
    observed_at: str
    output_schema_revision: str
    effect_revision: str
    handler_revision: str
    downstream_request_id: str | None
    receipt_id: str | None
    status_ref: str | None


@dataclass(frozen=True)
class UnknownOutcome:
    scope: tuple[str, str, str, str]
    request_sha256: str
    provider: str
    api_family: str
    adapter_revision: str
    effect_revision: str
    producer_revision: str
    status_ref: str


@dataclass(frozen=True)
class ErrorPolicy:
    category: str
    outcome: str
    recovery: str
    safe_message: str
    retry_after_ms: int | None = None


ERROR_CATALOG: dict[str, ErrorPolicy] = {
    "UNKNOWN_TOOL": ErrorPolicy("contract", "not_started", "correct_input", "The tool is not allowlisted."),
    "INVALID_ARGUMENTS": ErrorPolicy("contract", "not_started", "correct_input", "Arguments do not satisfy the tool contract."),
    "OUTPUT_CONTRACT_VIOLATION": ErrorPolicy("execution", "unknown", "human_review", "The tool result failed output-contract validation."),
    "NOT_FOUND": ErrorPolicy("authorization", "not_started", "none", "The resource does not exist or is inaccessible to the current principal."),
    "BUSINESS_RULE_VIOLATION": ErrorPolicy("business", "not_started", "human_review", "The current resource state does not allow this action."),
    "CALL_ID_CONFLICT": ErrorPolicy("conflict", "not_started", "human_review", "The same provider response/call identity maps to different requests."),
    "IDEMPOTENCY_KEY_REQUIRED": ErrorPolicy("contract", "not_started", "correct_input", "A write action requires an idempotency key."),
    "IDEMPOTENCY_CONFLICT": ErrorPolicy("conflict", "not_started", "human_review", "The same idempotency key maps to a different request or contract revision."),
    "APPROVAL_REQUIRED": ErrorPolicy("approval", "not_started", "request_approval", "This action requires approval bound to the current arguments."),
    "APPROVAL_INVALID": ErrorPolicy("approval", "not_started", "request_approval", "Approval expired or is not bound to the current request."),
    "TIMEOUT_BEFORE_EXECUTE": ErrorPolicy("execution", "not_started", "retry_after", "The tool exceeded its deadline before side effects began.", 1000),
    "OUTCOME_UNKNOWN": ErrorPolicy("execution", "unknown", "query_status", "The downstream operation may have committed; query status instead of automatically replaying the write."),
    "STATUS_CONFLICT": ErrorPolicy("conflict", "unknown", "human_review", "The status receipt does not match the original request or contract revision."),
    "RATE_LIMIT": ErrorPolicy("dependency", "not_started", "retry_after", "The tool is currently rate limited.", 1000),
    "TOOL_ERROR": ErrorPolicy("execution", "not_started", "human_review", "Tool execution failed."),
}
ERROR_MESSAGES = {code: policy.safe_message for code, policy in ERROR_CATALOG.items()}
RETRYABLE_CODES = {
    code for code, policy in ERROR_CATALOG.items() if policy.recovery == "retry_after"
}


def _reject_constant(value: str) -> None:
    raise FixtureError(f"JSON disallows non-finite constants: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FixtureError(f"JSON contains a duplicate field: {key}")
        result[key] = value
    return result


def _reject_excessive_json_nesting(text: str) -> None:
    """Bound container nesting before Python's recursive JSON decoder runs."""

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
                raise FixtureError(f"JSON nesting exceeds {MAX_JSON_DEPTH} levels")
        elif character in "]}":
            depth = max(0, depth - 1)


def _exact_fields(value: Any, expected: set[str], label: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    actual = set(value)
    if actual != expected:
        errors.append(
            f"{label} fields do not match: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )
        return False
    return True


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _bounded_identifier(value: Any) -> bool:
    return _nonempty_string(value) and len(value) <= MAX_IDENTIFIER_CHARS


def _validate_timepoint(now: int, *, approval_window: bool = False) -> None:
    latest = MAX_PORTABLE_UNIX_SECONDS
    if approval_window:
        latest -= APPROVAL_TTL_SECONDS
    if type(now) is not int or now < 0 or now > latest:
        raise ValueError("now is outside the portable UTC datetime range")


def validate_host_context(principal: Principal, call: ToolCall, *, now: int) -> None:
    """Fail closed on malformed trusted-host metadata before any handler runs."""

    _validate_timepoint(now)
    for label, value in (
        ("principal.tenant_id", principal.tenant_id),
        ("principal.subject_id", principal.subject_id),
        ("call.call_id", call.call_id),
        ("call.operation_id", call.operation_id),
        ("call.name", call.name),
        ("call.provider", call.provider),
        ("call.api_family", call.api_family),
        ("call.response_id", call.response_id),
        ("call.adapter_revision", call.adapter_revision),
    ):
        if not _bounded_identifier(value):
            raise ValueError(f"{label} must contain 1..{MAX_IDENTIFIER_CHARS} characters")
    if (
        not isinstance(principal.roles, tuple)
        or len(principal.roles) > MAX_ROLES
        or any(not _bounded_identifier(role) for role in principal.roles)
        or tuple(sorted(set(principal.roles))) != principal.roles
    ):
        raise ValueError("principal.roles must be a bounded, sorted, duplicate-free tuple of strings")
    if call.idempotency_key is not None and not _bounded_identifier(call.idempotency_key):
        raise ValueError(f"call.idempotency_key must be null or contain 1..{MAX_IDENTIFIER_CHARS} characters")
    expected_adapter = PROVIDER_PROFILES.get((call.provider, call.api_family))
    if expected_adapter is None or call.adapter_revision != expected_adapter:
        raise ValueError("call provider profile/adapter revision is not registered")


def _sorted_unique_strings(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not all(_nonempty_string(item) for item in value):
        errors.append(f"{label} must be a list of strings")
        return
    if len(value) > MAX_ROLES or any(len(item) > MAX_IDENTIFIER_CHARS for item in value):
        errors.append(f"{label} exceeds the count or per-item length limit")
        return
    if value != sorted(set(value)):
        errors.append(f"{label} must be sorted and contain no duplicates")


def validate_fixture(fixture: Any) -> list[str]:
    """Return all detectable errors in the strict v2 scenario fixture."""

    errors: list[str] = []
    if not _exact_fields(fixture, ROOT_FIELDS, "root", errors):
        return errors
    try:
        _validate_json_domain(fixture)
    except (TypeError, ValueError, UnicodeError) as exc:
        return [f"fixture is outside the supported JSON domain: {exc}"]
    if fixture["schema_version"] != FIXTURE_SCHEMA_VERSION:
        errors.append(f"schema_version must be  {FIXTURE_SCHEMA_VERSION!r}")
    contract = fixture["contract"]
    if _exact_fields(contract, CONTRACT_FIELDS, "contract", errors):
        if contract["model_result"] != MODEL_RESULT_SCHEMA_VERSION:
            errors.append("contract.model_result revisiondoes not match")
        if contract["protected_audit"] != AUDIT_SCHEMA_VERSION:
            errors.append("contract.protected_audit revisiondoes not match")
    cases = fixture["cases"]
    if not isinstance(cases, list) or not cases or len(cases) > MAX_CASES:
        errors.append(f"cases must contain 1..{MAX_CASES} items list")
        return errors
    case_ids: set[str] = set()
    for case_index, case in enumerate(cases):
        case_label = f"cases[{case_index}]"
        if not _exact_fields(case, CASE_FIELDS, case_label, errors):
            continue
        if not _bounded_identifier(case["id"]):
            errors.append(f"{case_label}.id must be a bounded, non-empty string")
        elif case["id"] in case_ids:
            errors.append(f"duplicate case id: {case['id']}")
        else:
            case_ids.add(case["id"])
        principal = case["principal"]
        if _exact_fields(principal, PRINCIPAL_FIELDS, f"{case_label}.principal", errors):
            for field in ("tenant_id", "subject_id"):
                if not _bounded_identifier(principal[field]):
                    errors.append(f"{case_label}.principal.{field} must be a bounded, non-empty string")
            _sorted_unique_strings(principal["roles"], f"{case_label}.principal.roles", errors)
        steps = case["steps"]
        if not isinstance(steps, list) or not steps or len(steps) > MAX_STEPS_PER_CASE:
            errors.append(f"{case_label}.steps must contain 1..{MAX_STEPS_PER_CASE} items list")
            continue
        step_ids: set[str] = set()
        for step_index, step in enumerate(steps):
            step_label = f"{case_label}.steps[{step_index}]"
            if not _exact_fields(step, STEP_FIELDS, step_label, errors):
                continue
            previous_step_ids = set(step_ids)
            step_id = step["step_id"]
            if not _bounded_identifier(step_id):
                errors.append(f"{step_label}.step_id must be a bounded, non-empty string")
            elif step_id in step_ids:
                errors.append(f"{case_label} has a duplicate step id: {step_id}")
            else:
                step_ids.add(step_id)
            if step["action"] not in VALID_ACTIONS:
                errors.append(f"{step_label}.action is invalid")
            proposal = step["proposal"]
            if _exact_fields(proposal, PROPOSAL_FIELDS, f"{step_label}.proposal", errors):
                if not _bounded_identifier(proposal["name"]):
                    errors.append(f"{step_label}.proposal.name must be a bounded, non-empty string")
                if not isinstance(proposal["arguments"], dict):
                    errors.append(f"{step_label}.proposal.arguments must be an object")
            context = step["execution_context"]
            if _exact_fields(context, CONTEXT_FIELDS, f"{step_label}.execution_context", errors):
                for field in CONTEXT_FIELDS - {"idempotency_key"}:
                    if not _bounded_identifier(context[field]):
                        errors.append(f"{step_label}.execution_context.{field} must be a bounded, non-empty string")
                key = context["idempotency_key"]
                if key is not None and not _bounded_identifier(key):
                    errors.append(f"{step_label}.execution_context.idempotency_key must be null or a bounded, non-empty string")
                profile = (context["provider"], context["api_family"])
                expected_adapter = PROVIDER_PROFILES.get(profile)
                if expected_adapter is None:
                    errors.append(f"{step_label}.execution_context provider profile is not registered")
                elif context["adapter_revision"] != expected_adapter:
                    errors.append(
                        f"{step_label}.execution_context.adapter_revision and provider profile does not match"
                    )
            if step["approval"] not in VALID_APPROVAL_MODES:
                errors.append(f"{step_label}.approval is invalid")
            if (
                type(step["now"]) is not int
                or step["now"] < 0
                or step["now"] > MAX_PORTABLE_UNIX_SECONDS - APPROVAL_TTL_SECONDS
            ):
                errors.append(f"{step_label}.now must be portableandcan accommodateapprovalwindow non-negative integertimestamp")
            if step["failure"] not in VALID_FAILURES:
                errors.append(f"{step_label}.failure is invalid")
            status_ref_from = step["status_ref_from"]
            if status_ref_from is not None and not _bounded_identifier(status_ref_from):
                errors.append(f"{step_label}.status_ref_from must be null or a bounded, non-empty string")
            if step["action"] == "query_status" and status_ref_from not in previous_step_ids:
                errors.append(f"{step_label}.status_ref_from mustreferenceprevious step")
            if step["action"] == "query_status" and step["failure"] != "none":
                errors.append(f"{step_label}.query_status must not inject a dispatch failure")
            if step["action"] == "query_status" and step["approval"] != "none":
                errors.append(f"{step_label}.query_status must not create execution approval")
            if step["action"] == "dispatch" and status_ref_from is not None:
                errors.append(f"{step_label}.dispatch must not set status_ref_from")
            expected = step["expected"]
            if _exact_fields(expected, EXPECTED_FIELDS, f"{step_label}.expected", errors):
                code = expected["code"]
                if code != "OK" and code not in ERROR_CATALOG:
                    errors.append(f"{step_label}.expected.code is invalid")
                if expected["status"] not in VALID_STATUSES:
                    errors.append(f"{step_label}.expected.status is invalid")
                if expected["outcome"] not in VALID_OUTCOMES:
                    errors.append(f"{step_label}.expected.outcome is invalid")
                if expected["recovery"] not in VALID_RECOVERIES:
                    errors.append(f"{step_label}.expected.recovery is invalid")
                if expected["delivery"] not in VALID_DELIVERIES:
                    errors.append(f"{step_label}.expected.delivery is invalid")
                if expected["data"] is not None and not isinstance(expected["data"], dict):
                    errors.append(f"{step_label}.expected.data must be an object or null")
                count = expected["side_effect_count"]
                if type(count) is not int or count < 0:
                    errors.append(f"{step_label}.expected.side_effect_count must be a non-negative integer")
    return errors


def load_fixture(path: Path) -> dict[str, Any]:
    """Load UTF-8 JSON, rejecting duplicate keys and non-finite constants."""

    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_FIXTURE_BYTES + 1)
    except OSError as exc:
        raise FixtureIOError("Cannot read fixture") from exc
    if len(raw) > MAX_FIXTURE_BYTES:
        raise FixtureError(f"fixture exceeds {MAX_FIXTURE_BYTES} bytes")
    try:
        text = raw.decode("utf-8")
        _reject_excessive_json_nesting(text)
        fixture = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise FixtureError(f"fixture is not strict UTF-8 JSON: {exc}") from exc
    errors = validate_fixture(fixture)
    if errors:
        raise FixtureError("fixture validation failed:\n- " + "\n- ".join(errors))
    if not isinstance(fixture, dict):
        raise FixtureError("fixture root must be an object")
    return fixture


def _validate_json_domain(value: Any, *, path: str = "$", depth: int = 0) -> None:
    """Constrain the portable JSON domain used for hashes and provider payloads."""

    if depth > MAX_JSON_DEPTH:
        raise ValueError(f"{path} exceeds the maximum JSON depth {MAX_JSON_DEPTH}")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if abs(value) > 9_007_199_254_740_991:
            raise ValueError(f"{path}  integeris outside the portable JSON-safe range")
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path} does not allow NaN or Infinity")
        return
    if isinstance(value, str):
        if len(value) > 65_536:
            raise ValueError(f"{path} stringis too long")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError(f"{path} is not a valid UTF-8 string") from exc
        return
    if isinstance(value, list):
        if len(value) > 1_024:
            raise ValueError(f"{path} array is too long")
        for index, item in enumerate(value):
            _validate_json_domain(item, path=f"{path}[{index}]", depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > 1_024:
            raise ValueError(f"{path} object has too many fields")
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}  object keys must be strings")
            _validate_json_domain(key, path=f"{path}.<key>", depth=depth + 1)
            _validate_json_domain(item, path=f"{path}.{key}", depth=depth + 1)
        return
    raise ValueError(f"{path} contains a non-JSON type: {type(value).__name__}")


def _canonical_json(value: Any) -> str:
    """Deterministic local encoding; intentionally not claimed as RFC 8785."""

    _validate_json_domain(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _tool_contract(spec: ToolSpec | None, name: str) -> dict[str, str]:
    if spec is None:
        return {
            "name": name,
            "input_schema_revision": "unregistered",
            "output_schema_revision": "unregistered",
            "effect_revision": "unregistered",
            "handler_revision": "unregistered",
            "producer_revision": "unregistered",
            "policy_revision": "unregistered",
        }
    return {
        "name": name,
        "input_schema_revision": spec.schema_version,
        "output_schema_revision": spec.output_schema_revision,
        "effect_revision": spec.effect_revision,
        "handler_revision": spec.handler_revision,
        "producer_revision": spec.producer_revision,
        "policy_revision": spec.approval_revision,
    }


def request_digest(principal: Principal, call: ToolCall, spec: ToolSpec | None = None) -> str:
    """Bind business intent to the subject and semantic contract revisions."""

    contract = _tool_contract(spec, call.name)
    return _digest(
        {
            "tenant_id": principal.tenant_id,
            "subject_id": principal.subject_id,
            "tool": call.name,
            "arguments": call.arguments,
            "input_schema_revision": contract["input_schema_revision"],
            "output_schema_revision": contract["output_schema_revision"],
            "effect_revision": contract["effect_revision"],
        }
    )


def call_binding_digest(
    principal: Principal,
    call: ToolCall,
    spec: ToolSpec | None,
    request_sha256: str,
    result_sha256: str,
    downstream: dict[str, str | None] | None = None,
) -> str:
    """Bind a result and its downstream evidence to one trusted call context."""

    bound_downstream = (
        {"request_id": None, "receipt_id": None, "status_ref": None}
        if downstream is None
        else downstream
    )
    return _digest(
        {
            "tenant_id": principal.tenant_id,
            "subject_id": principal.subject_id,
            "provider": call.provider,
            "api_family": call.api_family,
            "response_id": call.response_id,
            "call_id": call.call_id,
            "operation_id": call.operation_id,
            "idempotency_key": call.idempotency_key,
            "adapter_revision": call.adapter_revision,
            "tool_contract": _tool_contract(spec, call.name),
            "request_sha256": request_sha256,
            "result_sha256": result_sha256,
            "downstream": bound_downstream,
        }
    )


def call_fingerprint(
    principal: Principal,
    call: ToolCall,
    spec: ToolSpec | None = None,
    *,
    purpose: str = "dispatch",
) -> str:
    """Bind a provider call identity to one proposed action before execution."""

    if purpose not in VALID_ACTIONS:
        raise ValueError("call fingerprint purpose is invalid")
    request_sha256 = request_digest(principal, call, spec)
    return _digest(
        {
            "provider": call.provider,
            "api_family": call.api_family,
            "response_id": call.response_id,
            "call_id": call.call_id,
            "operation_id": call.operation_id,
            "idempotency_key": call.idempotency_key,
            "adapter_revision": call.adapter_revision,
            "purpose": purpose,
            "request_sha256": request_sha256,
        }
    )


def approval_digest(
    principal: Principal,
    call: ToolCall,
    spec: ToolSpec,
    *,
    approver_id: str = DEFAULT_APPROVER_ID,
) -> str:
    """Bind approval to intent, correlation, effects, and policy revisions."""

    return _digest(
        {
            "provider": call.provider,
            "api_family": call.api_family,
            "adapter_revision": call.adapter_revision,
            "operation_id": call.operation_id,
            "call_id": call.call_id,
            "response_id": call.response_id,
            "idempotency_key": call.idempotency_key,
            "request_sha256": request_digest(principal, call, spec),
            "input_schema_revision": spec.schema_version,
            "output_schema_revision": spec.output_schema_revision,
            "effect_revision": spec.effect_revision,
            "approval_revision": spec.approval_revision,
            "approver_id": approver_id,
        }
    )


def make_approval(
    principal: Principal,
    call: ToolCall,
    spec: ToolSpec | None,
    mode: str,
    now: int,
) -> tuple[Approval, ...]:
    """Create deterministic fixture approvals; production uses a trusted UI/workflow."""

    validate_host_context(principal, call, now=now)
    if mode == "none":
        return ()
    if mode not in VALID_APPROVAL_MODES:
        raise ValueError(f"unknown approval mode: {mode}")
    if spec is None:
        raise ValueError("an unknown tool cannot create approval")
    _validate_timepoint(now, approval_window=True)
    digest = approval_digest(principal, call, spec, approver_id=DEFAULT_APPROVER_ID)
    expires_at = now + APPROVAL_TTL_SECONDS
    if mode == "expired":
        expires_at = now - 1
    elif mode == "mismatched":
        digest = "0" * 64
    return (
        Approval(
            approval_id=f"approval-{call.call_id}",
            operation_id=call.operation_id,
            call_id=call.call_id,
            provider=call.provider,
            api_family=call.api_family,
            adapter_revision=call.adapter_revision,
            idempotency_key=call.idempotency_key,
            tool_name=call.name,
            subject_id=principal.subject_id,
            schema_version=spec.schema_version,
            approval_revision=spec.approval_revision,
            approval_digest=digest,
            expires_at=expires_at,
            approver_id=DEFAULT_APPROVER_ID,
        ),
    )


def _principal_ref(principal: Principal) -> str:
    return "sha256:" + _digest(
        {"tenant_id": principal.tenant_id, "subject_id": principal.subject_id}
    )


def _observed_at(now: int) -> str:
    _validate_timepoint(now)
    return (UTC_EPOCH + timedelta(seconds=now)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_package(
    principal: Principal,
    call: ToolCall,
    spec: ToolSpec | None,
    model_result: dict[str, Any],
    *,
    request_sha256: str,
    downstream_request_id: str | None = None,
    receipt_id: str | None = None,
    status_ref: str | None = None,
) -> dict[str, Any]:
    result_sha256 = _digest(model_result)
    downstream = {
        "request_id": downstream_request_id,
        "receipt_id": receipt_id,
        "status_ref": status_ref,
    }
    audit = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "visibility": "protected_audit",
        "operation_id": call.operation_id,
        "principal_ref": _principal_ref(principal),
        "provider_context": {
            "provider": call.provider,
            "api_family": call.api_family,
            "response_id": call.response_id,
            "call_id": call.call_id,
            "adapter_revision": call.adapter_revision,
        },
        "tool_contract": _tool_contract(spec, call.name),
        "binding": {
            "request_sha256": request_sha256,
            "result_sha256": result_sha256,
            "call_binding_sha256": call_binding_digest(
                principal,
                call,
                spec,
                request_sha256,
                result_sha256,
                downstream,
            ),
        },
        "downstream": downstream,
        "redactions": [],
    }
    return {"model_result": model_result, "protected_audit": audit}


def _success_package(
    principal: Principal,
    call: ToolCall,
    spec: ToolSpec,
    record: IdempotencyRecord,
    *,
    delivery: str,
) -> dict[str, Any]:
    model_result = {
        "schema_version": MODEL_RESULT_SCHEMA_VERSION,
        "status": "succeeded",
        "data": copy.deepcopy(record.data),
        "error": None,
        "execution": {
            "outcome": "committed",
            "delivery": delivery,
            "complete": True,
            "truncated": False,
        },
        "provenance": {
            "source_label": record.source_label,
            "producer_revision": record.producer_revision,
            "resource_revision": record.resource_revision,
            "observed_at": record.observed_at,
            "trust": "untrusted_data",
        },
    }
    return _build_package(
        principal,
        call,
        spec,
        model_result,
        request_sha256=record.request_sha256,
        downstream_request_id=record.downstream_request_id,
        receipt_id=record.receipt_id,
        status_ref=record.status_ref,
    )


def _error_package(
    principal: Principal,
    call: ToolCall,
    spec: ToolSpec | None,
    code: str,
    request_sha256: str,
    *,
    now: int,
    status_ref: str | None = None,
) -> dict[str, Any]:
    policy = ERROR_CATALOG[code]
    status = "unknown" if policy.outcome == "unknown" else "failed"
    model_result = {
        "schema_version": MODEL_RESULT_SCHEMA_VERSION,
        "status": status,
        "data": None,
        "error": {
            "code": code,
            "category": policy.category,
            "safe_message": policy.safe_message,
            "recovery": policy.recovery,
            "retry_after_ms": policy.retry_after_ms,
        },
        "execution": {
            "outcome": policy.outcome,
            "delivery": "fresh",
            "complete": True,
            "truncated": False,
        },
        "provenance": {
            "source_label": "offline-dispatcher",
            "producer_revision": DISPATCHER_REVISION,
            "resource_revision": None,
            "observed_at": _observed_at(now),
            "trust": "trusted_control",
        },
    }
    return _build_package(
        principal,
        call,
        spec,
        model_result,
        request_sha256=request_sha256,
        status_ref=status_ref,
    )


def _json_depth(value: Any) -> int:
    if isinstance(value, dict):
        return 1 + max((_json_depth(item) for item in value.values()), default=0)
    if isinstance(value, list):
        return 1 + max((_json_depth(item) for item in value), default=0)
    return 0


def _find_forbidden_key(value: Any, *, path: str = "data") -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = key.lower().replace("-", "_") if isinstance(key, str) else ""
            if normalized in SENSITIVE_OR_CONTROL_KEYS:
                return f"{path}.{key}"
            found = _find_forbidden_key(item, path=f"{path}.{key}")
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found = _find_forbidden_key(item, path=f"{path}[{index}]")
            if found is not None:
                return found
    return None


def _is_rfc3339_utc_second(value: Any) -> bool:
    if not isinstance(value, str) or RFC3339_UTC_PATTERN.fullmatch(value) is None:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def validate_handler_result(
    spec: ToolSpec,
    call: ToolCall,
    raw: Any,
) -> list[str]:
    """Validate raw handler output before creating either projection."""

    errors: list[str] = []
    if not isinstance(raw, HandlerResult):
        return ["handler must return HandlerResult, not an arbitrary mapping"]
    if raw.producer_revision != spec.producer_revision:
        errors.append("producer_revision andregistryis inconsistent")
    if raw.resource_revision is not None and not _nonempty_string(raw.resource_revision):
        errors.append("resource_revision must be null or non-emptystring")
    if not _is_rfc3339_utc_second(raw.observed_at):
        errors.append("observed_at must be a UTC RFC 3339 timestamp with second precision")
    if not isinstance(raw.data, dict):
        errors.append("handler data must be an object")
        return errors
    if set(raw.data) != set(spec.output):
        errors.append(
            "output fields do not match: "
            f"missing={sorted(set(spec.output) - set(raw.data))}, "
            f"extra={sorted(set(raw.data) - set(spec.output))}"
        )
        return errors
    # Validate the bounded JSON domain before recursive policy scans.  Handler
    # output is untrusted at this boundary; otherwise a deeply nested mapping
    # can overflow _find_forbidden_key before the canonical encoder rejects it.
    try:
        _validate_json_domain(raw.data, path="data")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        errors.append(f"output is outside the supported JSON domain: {exc}")
        return errors
    forbidden = _find_forbidden_key(raw.data)
    if forbidden is not None:
        errors.append(f"output contains sensitive or control fields: {forbidden}")
    try:
        encoded = _canonical_json(raw.data).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        errors.append(f"output is outside the supported JSON domain: {exc}")
    else:
        if len(encoded) > spec.max_output_bytes:
            errors.append(f"output exceeds {spec.max_output_bytes} bytes")
        if _json_depth(raw.data) > spec.max_output_depth:
            errors.append(f"output depth exceeds {spec.max_output_depth}")
    for name, rule in spec.output.items():
        value = raw.data[name]
        if type(value) is not rule.python_type:
            errors.append(f"data.{name} typedoes not match")
            continue
        if isinstance(value, str):
            if rule.min_length is not None and len(value) < rule.min_length:
                errors.append(f"data.{name} is too short")
            if rule.max_length is not None and len(value) > rule.max_length:
                errors.append(f"data.{name} is too long")
            if rule.enum is not None and value not in rule.enum:
                errors.append(f"data.{name} is not in the enumeration")
            if rule.pattern is not None and rule.pattern.fullmatch(value) is None:
                errors.append(f"data.{name} does not match the required format")
        if rule.equals_argument is not None and value != call.arguments.get(rule.equals_argument):
            errors.append(f"data.{name} is not bound to input argument {rule.equals_argument}")
    return errors


def _validate_error_model(model: dict[str, Any], errors: list[str]) -> None:
    error = model["error"]
    if not _exact_fields(error, MODEL_ERROR_FIELDS, "model_result.error", errors):
        return
    code = error["code"]
    if code not in ERROR_CATALOG:
        errors.append("model_result.error.code is invalid")
        return
    policy = ERROR_CATALOG[code]
    expected = {
        "category": policy.category,
        "safe_message": policy.safe_message,
        "recovery": policy.recovery,
        "retry_after_ms": policy.retry_after_ms,
    }
    for field, value in expected.items():
        if error[field] != value:
            errors.append(f"model_result.error.{field} does not use a fixed error-catalog value")
    expected_status = "unknown" if policy.outcome == "unknown" else "failed"
    if model["status"] != expected_status:
        errors.append("model_result.status anderror outcome is inconsistent")
    execution = model["execution"]
    if isinstance(execution, dict) and execution.get("outcome") != policy.outcome:
        errors.append("model_result.execution.outcome anderrorcatalogis inconsistent")


def validate_result(
    principal: Principal,
    call: ToolCall,
    spec: ToolSpec | None,
    package: Any,
) -> list[str]:
    """Recompute every binding before a package reaches a provider adapter."""

    errors: list[str] = []
    expected_adapter = PROVIDER_PROFILES.get((call.provider, call.api_family))
    if expected_adapter is None or call.adapter_revision != expected_adapter:
        errors.append("current call   provider profile/adapter revision is not registered")
    if not _exact_fields(package, PACKAGE_FIELDS, "package", errors):
        return errors
    model = package["model_result"]
    audit = package["protected_audit"]
    if not _exact_fields(model, MODEL_RESULT_FIELDS, "model_result", errors):
        return errors
    if not _exact_fields(audit, AUDIT_FIELDS, "protected_audit", errors):
        return errors
    if model["schema_version"] != MODEL_RESULT_SCHEMA_VERSION:
        errors.append("model_result.schema_version does not match")
    if model["status"] not in VALID_STATUSES:
        errors.append("model_result.status is invalid")
    execution = model["execution"]
    execution_valid = _exact_fields(
        execution, EXECUTION_FIELDS, "model_result.execution", errors
    )
    if execution_valid:
        if execution["outcome"] not in VALID_OUTCOMES:
            errors.append("model_result.execution.outcome is invalid")
        if execution["delivery"] not in VALID_DELIVERIES:
            errors.append("model_result.execution.delivery is invalid")
        if execution["complete"] is not True or execution["truncated"] is not False:
            errors.append("the example contract accepts only complete=true and truncated=false")
    provenance = model["provenance"]
    provenance_valid = _exact_fields(
        provenance, PROVENANCE_FIELDS, "model_result.provenance", errors
    )
    if provenance_valid:
        for field in ("source_label", "producer_revision"):
            if not _nonempty_string(provenance[field]):
                errors.append(f"model_result.provenance.{field} must be non-emptystring")
        if provenance["resource_revision"] is not None and not _nonempty_string(provenance["resource_revision"]):
            errors.append("model_result.provenance.resource_revision is invalid")
        if not _is_rfc3339_utc_second(provenance["observed_at"]):
            errors.append("model_result.provenance.observed_at is invalid")
        if provenance["trust"] not in VALID_TRUST:
            errors.append("model_result.provenance.trust is invalid")
    if model["status"] == "succeeded":
        if model["error"] is not None or not isinstance(model["data"], dict):
            errors.append("a successful result must have data=object and error=null")
        if not isinstance(execution, dict) or execution.get("outcome") != "committed":
            errors.append("a successful result must have outcome=committed")
        if not isinstance(provenance, dict) or provenance.get("trust") != "untrusted_data":
            errors.append("business results must be marked untrusted_data")
        if spec is None:
            errors.append("an unregistered tool cannot produce a successful result")
        elif isinstance(model["data"], dict) and provenance_valid:
            raw = HandlerResult(
                data=model["data"],
                producer_revision=provenance["producer_revision"],
                resource_revision=provenance["resource_revision"],
                observed_at=provenance["observed_at"],
            )
            errors.extend(validate_handler_result(spec, call, raw))
            if provenance["source_label"] != spec.producer_label:
                errors.append("source_label andregistryis inconsistent")
    else:
        if model["data"] is not None:
            errors.append("a failed or unknown result must have data=null")
        _validate_error_model(model, errors)
        if not isinstance(provenance, dict) or provenance.get("trust") != "trusted_control":
            errors.append("error-catalog control fields must be marked trusted_control")
        if not isinstance(provenance, dict) or provenance.get("source_label") != "offline-dispatcher":
            errors.append("the dispatcher must fix the error origin")
        if not isinstance(provenance, dict) or provenance.get("producer_revision") != DISPATCHER_REVISION:
            errors.append("the dispatcher must fix the error producer_revision")
    if audit["schema_version"] != AUDIT_SCHEMA_VERSION:
        errors.append("protected_audit.schema_version does not match")
    if audit["visibility"] != "protected_audit":
        errors.append("protected_audit.visibility is invalid")
    if audit["operation_id"] != call.operation_id:
        errors.append("protected_audit.operation_id is not bound to the current operation")
    if audit["principal_ref"] != _principal_ref(principal):
        errors.append("protected_audit.principal_ref is not bound to the current principal")
    provider_context = audit["provider_context"]
    if _exact_fields(provider_context, PROVIDER_CONTEXT_FIELDS, "protected_audit.provider_context", errors):
        expected_provider = {
            "provider": call.provider,
            "api_family": call.api_family,
            "response_id": call.response_id,
            "call_id": call.call_id,
            "adapter_revision": call.adapter_revision,
        }
        if provider_context != expected_provider:
            errors.append("provider_context is not bound to the current provider response/call")
    tool_contract = audit["tool_contract"]
    if _exact_fields(tool_contract, TOOL_CONTRACT_FIELDS, "protected_audit.tool_contract", errors):
        if tool_contract != _tool_contract(spec, call.name):
            errors.append("tool_contract is inconsistent with the trusted registry")
    downstream = audit["downstream"]
    downstream_valid = _exact_fields(
        downstream, DOWNSTREAM_FIELDS, "protected_audit.downstream", errors
    )
    if downstream_valid:
        for field in DOWNSTREAM_FIELDS:
            if downstream[field] is not None and not _nonempty_string(downstream[field]):
                errors.append(f"protected_audit.downstream.{field} is invalid")
        if downstream["status_ref"] is not None and STATUS_REF_PATTERN.fullmatch(downstream["status_ref"]) is None:
            errors.append("protected_audit.downstream.status_ref format is invalid")
    binding = audit["binding"]
    if _exact_fields(binding, BINDING_FIELDS, "protected_audit.binding", errors):
        for field in BINDING_FIELDS:
            if not isinstance(binding[field], str) or HEX64_PATTERN.fullmatch(binding[field]) is None:
                errors.append(f"protected_audit.binding.{field} must be full 64-character hexadecimal digest")
        try:
            expected_request = request_digest(principal, call, spec)
            expected_result = _digest(model)
            expected_call_binding = call_binding_digest(
                principal,
                call,
                spec,
                expected_request,
                expected_result,
                downstream if downstream_valid else None,
            )
        except (TypeError, ValueError, UnicodeError) as exc:
            errors.append(f"cannot recompute bindings: {exc}")
        else:
            if binding["request_sha256"] != expected_request:
                errors.append("request_sha256 is inconsistent with the current principal/arguments/contract")
            if binding["result_sha256"] != expected_result:
                errors.append("result_sha256 is inconsistent with the model-visible result")
            if binding["call_binding_sha256"] != expected_call_binding:
                errors.append("call_binding_sha256 is inconsistent with the current provider turn/result")
    if not isinstance(audit["redactions"], list) or not all(
        _nonempty_string(item) for item in audit["redactions"]
    ):
        if audit["redactions"] != []:
            errors.append("protected_audit.redactions must be a list of strings")
    return errors


def validate_result_set(
    principal: Principal,
    calls: list[ToolCall],
    specs: dict[str, ToolSpec],
    packages: list[dict[str, Any]],
) -> list[str]:
    """Reject missing, duplicate, unknown, or swapped multi-call results."""

    errors: list[str] = []
    expected: dict[tuple[str, str], ToolCall] = {}
    for call in calls:
        key = (call.response_id, call.call_id)
        if key in expected:
            errors.append(f"duplicate expected call identity: {key}")
        expected[key] = call
    actual: dict[tuple[str, str], dict[str, Any]] = {}
    for index, package in enumerate(packages):
        try:
            context = package["protected_audit"]["provider_context"]
            key = (context["response_id"], context["call_id"])
        except (KeyError, TypeError):
            errors.append(f"packages[{index}] is missing provider correlation fields")
            continue
        if key in actual:
            errors.append(f"duplicate result identity: {key}")
            continue
        actual[key] = package
    for key in sorted(set(expected) - set(actual)):
        errors.append(f"missing result: {key}")
    for key in sorted(set(actual) - set(expected)):
        errors.append(f"unknown result appears: {key}")
    for key in sorted(set(expected) & set(actual)):
        call = expected[key]
        errors.extend(validate_result(principal, call, specs.get(call.name), actual[key]))
    return errors


class Dispatcher:
    """Trusted host-side dispatcher for two deterministic mock tools."""

    def __init__(self) -> None:
        self.side_effect_count = 0
        self.idempotency_records: dict[tuple[str, str, str, str], IdempotencyRecord] = {}
        self.downstream_receipts: dict[tuple[str, str, str, str], IdempotencyRecord] = {}
        self.uncertain_outcomes: dict[tuple[str, str, str, str], UnknownOutcome] = {}
        self.status_refs: dict[str, UnknownOutcome] = {}
        self.call_fingerprints: dict[tuple[str, str, str, str, str, str], str] = {}
        self.orders = {
            "ORDER-7": {"tenant_id": "tenant-a", "owner_id": "user-1", "status": "paid", "revision": "order-7-r3"},
            "ORDER-8": {"tenant_id": "tenant-a", "owner_id": "user-2", "status": "paid", "revision": "order-8-r2"},
            "ORDER-9": {"tenant_id": "tenant-b", "owner_id": "user-1", "status": "paid", "revision": "order-9-r4"},
        }
        self.registry = {
            "get_order": ToolSpec(
                schema_version="get-order-input-v1",
                approval_revision="get-order-policy-v1",
                risk="read",
                arguments={"order_ref": ArgumentRule(str, min_length=1, max_length=64)},
                output_schema_revision="get-order-output-v2",
                output={
                    "order_ref": OutputRule(str, min_length=1, max_length=64, equals_argument="order_ref"),
                    "status": OutputRule(str, enum=frozenset({"paid", "pending", "refunded"})),
                },
                max_output_bytes=256,
                max_output_depth=1,
                effect_revision="read-order-v1",
                handler_revision="get-order-handler-v2",
                producer_label="orders",
                producer_revision="orders-mock-v2",
                timeout_ms=500,
                business_validator=lambda _principal, _arguments: True,
                handler=self._get_order,
            ),
            "create_refund_draft": ToolSpec(
                schema_version="refund-draft-input-v1",
                approval_revision="refund-draft-policy-v1",
                risk="write",
                arguments={
                    "order_ref": ArgumentRule(str, min_length=1, max_length=64),
                    "reason": ArgumentRule(str, min_length=1, max_length=32, enum=frozenset({"duplicate", "damaged", "other"})),
                },
                output_schema_revision="refund-draft-output-v2",
                output={
                    "draft_id": OutputRule(str, max_length=64, pattern=re.compile(r"^DRAFT-[1-9]\d*$")),
                    "order_ref": OutputRule(str, max_length=64, equals_argument="order_ref"),
                    "reason": OutputRule(str, enum=frozenset({"duplicate", "damaged", "other"}), equals_argument="reason"),
                },
                max_output_bytes=384,
                max_output_depth=1,
                effect_revision="create-refund-draft-v1",
                handler_revision="refund-draft-handler-v2",
                producer_label="refunds",
                producer_revision="refunds-mock-v2",
                timeout_ms=800,
                business_validator=self._refund_business_valid,
                handler=self._create_refund_draft,
            ),
        }

    @staticmethod
    def _validate_arguments(spec: ToolSpec, arguments: Any) -> bool:
        if not isinstance(arguments, dict) or set(arguments) != set(spec.arguments):
            return False
        try:
            _validate_json_domain(arguments)
        except (TypeError, ValueError, UnicodeError):
            return False
        for name, rule in spec.arguments.items():
            value = arguments[name]
            if type(value) is not rule.python_type:
                return False
            if isinstance(value, str):
                stripped = value.strip()
                if rule.min_length is not None and len(stripped) < rule.min_length:
                    return False
                if rule.max_length is not None and len(value) > rule.max_length:
                    return False
                if rule.enum is not None and value not in rule.enum:
                    return False
        return True

    def _authorized_order(self, principal: Principal, order_ref: str) -> bool:
        order = self.orders.get(order_ref)
        if order is None or order["tenant_id"] != principal.tenant_id:
            return False
        return order["owner_id"] == principal.subject_id or "support_admin" in principal.roles

    def _refund_business_valid(
        self, _principal: Principal, arguments: dict[str, Any]
    ) -> bool:
        order = self.orders.get(arguments.get("order_ref"))
        return order is not None and order["status"] == "paid"

    @staticmethod
    def _approval_valid(
        approvals: tuple[Approval, ...],
        principal: Principal,
        call: ToolCall,
        spec: ToolSpec,
        now: int,
    ) -> bool:
        for approval in approvals:
            if not isinstance(approval, Approval):
                continue
            if (
                not _bounded_identifier(approval.approval_id)
                or not _bounded_identifier(approval.approver_id)
                or approval.approver_id not in AUTHORIZED_APPROVER_IDS
                or type(approval.expires_at) is not int
                or approval.expires_at <= now
                or approval.expires_at > MAX_PORTABLE_UNIX_SECONDS
            ):
                continue
            try:
                expected_digest = approval_digest(
                    principal,
                    call,
                    spec,
                    approver_id=approval.approver_id,
                )
            except (TypeError, ValueError, UnicodeError):
                continue
            if (
                approval.operation_id == call.operation_id
                and approval.call_id == call.call_id
                and approval.provider == call.provider
                and approval.api_family == call.api_family
                and approval.adapter_revision == call.adapter_revision
                and approval.idempotency_key == call.idempotency_key
                and approval.tool_name == call.name
                and approval.subject_id == principal.subject_id
                and approval.schema_version == spec.schema_version
                and approval.approval_revision == spec.approval_revision
                and approval.approval_digest == expected_digest
            ):
                return True
        return False

    def _bind_call_identity(
        self,
        principal: Principal,
        call: ToolCall,
        spec: ToolSpec,
        *,
        purpose: str,
    ) -> bool:
        call_key = (
            principal.tenant_id,
            principal.subject_id,
            call.provider,
            call.api_family,
            call.response_id,
            call.call_id,
        )
        fingerprint = call_fingerprint(principal, call, spec, purpose=purpose)
        prior_fingerprint = self.call_fingerprints.get(call_key)
        if prior_fingerprint is not None and prior_fingerprint != fingerprint:
            return False
        self.call_fingerprints[call_key] = fingerprint
        return True

    @staticmethod
    def _idempotency_scope(principal: Principal, call: ToolCall) -> tuple[str, str, str, str]:
        if call.idempotency_key is None:
            raise ValueError("write action is missing an idempotency key")
        return (principal.tenant_id, principal.subject_id, call.name, call.idempotency_key)

    @staticmethod
    def _record_from_handler(
        spec: ToolSpec,
        call: ToolCall,
        raw: HandlerResult,
        request_sha256: str,
        status_ref: str | None,
    ) -> IdempotencyRecord:
        return IdempotencyRecord(
            request_sha256=request_sha256,
            provider=call.provider,
            api_family=call.api_family,
            adapter_revision=call.adapter_revision,
            data=copy.deepcopy(raw.data),
            source_label=spec.producer_label,
            producer_revision=raw.producer_revision,
            resource_revision=raw.resource_revision,
            observed_at=raw.observed_at,
            output_schema_revision=spec.output_schema_revision,
            effect_revision=spec.effect_revision,
            handler_revision=spec.handler_revision,
            downstream_request_id=raw.downstream_request_id,
            receipt_id=raw.receipt_id,
            status_ref=status_ref,
        )

    @staticmethod
    def _record_matches(
        record: IdempotencyRecord,
        call: ToolCall,
        spec: ToolSpec,
        digest: str,
    ) -> bool:
        return (
            record.request_sha256 == digest
            and record.provider == call.provider
            and record.api_family == call.api_family
            and record.adapter_revision == call.adapter_revision
            and record.output_schema_revision == spec.output_schema_revision
            and record.effect_revision == spec.effect_revision
            and record.handler_revision == spec.handler_revision
            and record.producer_revision == spec.producer_revision
        )

    def _remember_unknown(
        self,
        scope: tuple[str, str, str, str],
        call: ToolCall,
        spec: ToolSpec,
        digest: str,
        status_ref: str,
    ) -> UnknownOutcome:
        unknown = UnknownOutcome(
            scope=scope,
            request_sha256=digest,
            provider=call.provider,
            api_family=call.api_family,
            adapter_revision=call.adapter_revision,
            effect_revision=spec.effect_revision,
            producer_revision=spec.producer_revision,
            status_ref=status_ref,
        )
        self.uncertain_outcomes[scope] = unknown
        self.status_refs[status_ref] = unknown
        return unknown

    def dispatch(
        self,
        principal: Principal,
        call: ToolCall,
        *,
        approvals: tuple[Approval, ...] = (),
        now: int,
        failure: str = "none",
    ) -> dict[str, Any]:
        """Validate, authorize, approve, deduplicate, execute, and project one call."""

        validate_host_context(principal, call, now=now)
        if failure not in VALID_FAILURES:
            raise ValueError(f"unknown failure: {failure}")
        spec = self.registry.get(call.name)
        if spec is None:
            digest = request_digest(principal, call, None)
            return _error_package(principal, call, None, "UNKNOWN_TOOL", digest, now=now)
        if not self._validate_arguments(spec, call.arguments):
            # Fixture arguments remain in the supported JSON domain, so the
            # digest is reproducible even for a business-schema failure.
            digest = request_digest(principal, call, spec)
            return _error_package(principal, call, spec, "INVALID_ARGUMENTS", digest, now=now)
        digest = request_digest(principal, call, spec)
        if not self._bind_call_identity(
            principal, call, spec, purpose="dispatch"
        ):
            return _error_package(principal, call, spec, "CALL_ID_CONFLICT", digest, now=now)
        order_ref = call.arguments["order_ref"]
        if not self._authorized_order(principal, order_ref):
            return _error_package(principal, call, spec, "NOT_FOUND", digest, now=now)

        idempotency_scope: tuple[str, str, str, str] | None = None
        if spec.risk == "write":
            if not call.idempotency_key:
                return _error_package(principal, call, spec, "IDEMPOTENCY_KEY_REQUIRED", digest, now=now)
            idempotency_scope = self._idempotency_scope(principal, call)
            record = self.idempotency_records.get(idempotency_scope)
            if record is not None:
                if not self._record_matches(record, call, spec, digest):
                    return _error_package(principal, call, spec, "IDEMPOTENCY_CONFLICT", digest, now=now)
                return _success_package(principal, call, spec, record, delivery="local_replay")
            uncertain = self.uncertain_outcomes.get(idempotency_scope)
            if uncertain is not None:
                if (
                    uncertain.request_sha256 != digest
                    or uncertain.provider != call.provider
                    or uncertain.api_family != call.api_family
                    or uncertain.adapter_revision != call.adapter_revision
                    or uncertain.effect_revision != spec.effect_revision
                    or uncertain.producer_revision != spec.producer_revision
                ):
                    return _error_package(principal, call, spec, "IDEMPOTENCY_CONFLICT", digest, now=now)
                return _error_package(
                    principal,
                    call,
                    spec,
                    "OUTCOME_UNKNOWN",
                    digest,
                    now=now,
                    status_ref=uncertain.status_ref,
                )
            if not spec.business_validator(principal, call.arguments):
                return _error_package(
                    principal,
                    call,
                    spec,
                    "BUSINESS_RULE_VIOLATION",
                    digest,
                    now=now,
                )
            if not approvals:
                return _error_package(principal, call, spec, "APPROVAL_REQUIRED", digest, now=now)
            if not self._approval_valid(approvals, principal, call, spec, now):
                return _error_package(principal, call, spec, "APPROVAL_INVALID", digest, now=now)

        if failure == "timeout_before_execute":
            return _error_package(principal, call, spec, "TIMEOUT_BEFORE_EXECUTE", digest, now=now)
        if failure == "rate_limit":
            return _error_package(principal, call, spec, "RATE_LIMIT", digest, now=now)
        if failure == "tool_error":
            return _error_package(principal, call, spec, "TOOL_ERROR", digest, now=now)
        if failure in {"timeout_after_commit", "timeout_after_commit_receipt_unavailable"} and spec.risk != "write":
            raise ValueError("timeout_after_commit applies only to write actions")

        status_ref: str | None = None
        if spec.risk == "write":
            if idempotency_scope is None:
                raise RuntimeError("internal error: write action is missing an idempotency scope")
            status_ref = "status_" + _digest(
                {"scope": list(idempotency_scope), "request_sha256": digest}
            )[:32]
        try:
            raw = spec.handler(call.arguments)
        except Exception:
            if spec.risk == "write":
                if idempotency_scope is None or status_ref is None:
                    raise RuntimeError("internal error: write action is missing recovery fields")
                self._remember_unknown(idempotency_scope, call, spec, digest, status_ref)
                return _error_package(
                    principal,
                    call,
                    spec,
                    "OUTCOME_UNKNOWN",
                    digest,
                    now=now,
                    status_ref=status_ref,
                )
            return _error_package(
                principal, call, spec, "TOOL_ERROR", digest, now=now
            )
        output_errors = validate_handler_result(spec, call, raw)
        if output_errors:
            if spec.risk == "write":
                if idempotency_scope is None or status_ref is None:
                    raise RuntimeError("internal error: write action is missing recovery fields")
                self._remember_unknown(idempotency_scope, call, spec, digest, status_ref)
            return _error_package(
                principal,
                call,
                spec,
                "OUTPUT_CONTRACT_VIOLATION",
                digest,
                now=now,
                status_ref=status_ref,
            )
        record = self._record_from_handler(spec, call, raw, digest, status_ref)
        if spec.risk == "write":
            if idempotency_scope is None or status_ref is None:
                raise RuntimeError("internal error: write action is missing recovery fields")
            if failure in {"timeout_after_commit", "timeout_after_commit_receipt_unavailable"}:
                self._remember_unknown(idempotency_scope, call, spec, digest, status_ref)
                if failure == "timeout_after_commit":
                    self.downstream_receipts[idempotency_scope] = record
                return _error_package(
                    principal,
                    call,
                    spec,
                    "OUTCOME_UNKNOWN",
                    digest,
                    now=now,
                    status_ref=status_ref,
                )
            self.downstream_receipts[idempotency_scope] = record
            self.idempotency_records[idempotency_scope] = record
        return _success_package(principal, call, spec, record, delivery="fresh")

    def query_operation_status(
        self,
        principal: Principal,
        call: ToolCall,
        *,
        status_ref: str,
        expected_request_sha256: str,
        now: int,
    ) -> dict[str, Any]:
        """Observe/reconcile a prior uncertain write without invoking its handler."""

        validate_host_context(principal, call, now=now)
        if (
            not isinstance(status_ref, str)
            or STATUS_REF_PATTERN.fullmatch(status_ref) is None
            or not isinstance(expected_request_sha256, str)
            or HEX64_PATTERN.fullmatch(expected_request_sha256) is None
        ):
            raise ValueError("status query correlationfieldsformat is invalid")
        spec = self.registry.get(call.name)
        if spec is None or not self._validate_arguments(spec, call.arguments):
            digest = request_digest(principal, call, spec)
            code = "UNKNOWN_TOOL" if spec is None else "INVALID_ARGUMENTS"
            return _error_package(principal, call, spec, code, digest, now=now)
        digest = request_digest(principal, call, spec)
        if not self._bind_call_identity(
            principal, call, spec, purpose="query_status"
        ):
            return _error_package(
                principal, call, spec, "CALL_ID_CONFLICT", digest, now=now
            )
        order_ref = call.arguments["order_ref"]
        if not self._authorized_order(principal, order_ref):
            return _error_package(principal, call, spec, "NOT_FOUND", digest, now=now)
        unknown = self.status_refs.get(status_ref)
        if unknown is None or unknown.scope[:2] != (principal.tenant_id, principal.subject_id):
            return _error_package(principal, call, spec, "NOT_FOUND", digest, now=now)
        try:
            scope = self._idempotency_scope(principal, call)
        except ValueError:
            return _error_package(principal, call, spec, "STATUS_CONFLICT", digest, now=now, status_ref=status_ref)
        if (
            expected_request_sha256 != digest
            or unknown.scope != scope
            or unknown.request_sha256 != digest
            or unknown.provider != call.provider
            or unknown.api_family != call.api_family
            or unknown.adapter_revision != call.adapter_revision
            or unknown.effect_revision != spec.effect_revision
            or unknown.producer_revision != spec.producer_revision
        ):
            return _error_package(principal, call, spec, "STATUS_CONFLICT", digest, now=now, status_ref=status_ref)
        receipt = self.downstream_receipts.get(scope)
        if receipt is None:
            return _error_package(principal, call, spec, "OUTCOME_UNKNOWN", digest, now=now, status_ref=status_ref)
        if not self._record_matches(receipt, call, spec, digest) or receipt.status_ref != status_ref:
            return _error_package(principal, call, spec, "STATUS_CONFLICT", digest, now=now, status_ref=status_ref)
        self.idempotency_records[scope] = copy.deepcopy(receipt)
        self.uncertain_outcomes.pop(scope, None)
        return _success_package(principal, call, spec, receipt, delivery="receipt_reconciled")

    def _get_order(self, arguments: dict[str, Any]) -> HandlerResult:
        order = self.orders[arguments["order_ref"]]
        return HandlerResult(
            data={"order_ref": arguments["order_ref"], "status": order["status"]},
            producer_revision="orders-mock-v2",
            resource_revision=order["revision"],
            observed_at="2026-07-19T00:00:00Z",
            downstream_request_id="orders-request-1",
        )

    def _create_refund_draft(self, arguments: dict[str, Any]) -> HandlerResult:
        self.side_effect_count += 1
        draft_id = f"DRAFT-{self.side_effect_count}"
        return HandlerResult(
            data={
                "draft_id": draft_id,
                "order_ref": arguments["order_ref"],
                "reason": arguments["reason"],
            },
            producer_revision="refunds-mock-v2",
            resource_revision=f"{draft_id.lower()}-r1",
            observed_at="2026-07-19T00:00:00Z",
            downstream_request_id=f"refund-request-{self.side_effect_count}",
            receipt_id=f"refund-receipt-{self.side_effect_count}",
        )


def _require_valid_package(
    principal: Principal,
    call: ToolCall,
    spec: ToolSpec | None,
    package: dict[str, Any],
) -> None:
    errors = validate_result(principal, call, spec, package)
    if errors:
        raise ResultContractError("result-contract validation failed:\n- " + "\n- ".join(errors))


def to_openai_responses(
    principal: Principal,
    call: ToolCall,
    spec: ToolSpec | None,
    package: dict[str, Any],
) -> dict[str, Any]:
    """Serialize only the model projection for OpenAI Responses API."""

    if (call.provider, call.api_family) != ("openai", "responses"):
        raise ResultContractError("call is not an OpenAI Responses context")
    _require_valid_package(principal, call, spec, package)
    return {
        "type": "function_call_output",
        "call_id": call.call_id,
        "output": _canonical_json(package["model_result"]),
    }


def to_anthropic_messages(
    principal: Principal,
    call: ToolCall,
    spec: ToolSpec | None,
    package: dict[str, Any],
) -> dict[str, Any]:
    """Serialize one Anthropic tool_result block; caller keeps blocks first."""

    if (call.provider, call.api_family) != ("anthropic", "messages"):
        raise ResultContractError("call is not an Anthropic Messages context")
    _require_valid_package(principal, call, spec, package)
    model = package["model_result"]
    return {
        "type": "tool_result",
        "tool_use_id": call.call_id,
        "content": [{"type": "text", "text": _canonical_json(model)}],
        "is_error": model["status"] != "succeeded",
    }


def to_gemini_interactions(
    principal: Principal,
    call: ToolCall,
    spec: ToolSpec | None,
    package: dict[str, Any],
) -> dict[str, Any]:
    """Serialize a schema-only Gemini Interactions continuation payload."""

    if (call.provider, call.api_family) != ("google", "interactions"):
        raise ResultContractError("call is not a Gemini Interactions context")
    _require_valid_package(principal, call, spec, package)
    return {
        "previous_interaction_id": call.response_id,
        "input": [
            {
                "type": "function_result",
                "name": call.name,
                "call_id": call.call_id,
                "result": [{"type": "text", "text": _canonical_json(package["model_result"])}],
            }
        ],
    }


def _principal_from_fixture(value: dict[str, Any]) -> Principal:
    return Principal(value["tenant_id"], value["subject_id"], tuple(value["roles"]))


def _call_from_fixture(proposal: dict[str, Any], context: dict[str, Any]) -> ToolCall:
    return bind_tool_call(
        ModelProposal(name=proposal["name"], arguments=proposal["arguments"]),
        ExecutionContext(
            call_id=context["call_id"],
            operation_id=context["operation_id"],
            idempotency_key=context["idempotency_key"],
            provider=context["provider"],
            api_family=context["api_family"],
            response_id=context["response_id"],
            adapter_revision=context["adapter_revision"],
        ),
    )


def run_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Run each case in isolation and return exact, machine-checkable outcomes."""

    case_results: list[dict[str, Any]] = []
    all_passed = True
    for case in fixture["cases"]:
        dispatcher = Dispatcher()
        principal = _principal_from_fixture(case["principal"])
        packages_by_step: dict[str, dict[str, Any]] = {}
        step_results: list[dict[str, Any]] = []
        for step in case["steps"]:
            call = _call_from_fixture(step["proposal"], step["execution_context"])
            spec = dispatcher.registry.get(call.name)
            approvals = make_approval(principal, call, spec, step["approval"], step["now"])
            if step["action"] == "dispatch":
                package = dispatcher.dispatch(
                    principal,
                    call,
                    approvals=approvals,
                    now=step["now"],
                    failure=step["failure"],
                )
            else:
                source_package = packages_by_step[step["status_ref_from"]]
                status_ref = source_package["protected_audit"]["downstream"]["status_ref"]
                if not isinstance(status_ref, str):
                    raise FixtureError("the step referenced by query_status has no status_ref")
                if spec is None:
                    raise FixtureError("query_status cannot reference an unknown tool")
                package = dispatcher.query_operation_status(
                    principal,
                    call,
                    status_ref=status_ref,
                    expected_request_sha256=request_digest(principal, call, spec),
                    now=step["now"],
                )
            packages_by_step[step["step_id"]] = package
            validation_errors = validate_result(principal, call, spec, package)
            model = package["model_result"]
            actual_code = "OK" if model["status"] == "succeeded" else model["error"]["code"]
            actual_recovery = "none" if model["error"] is None else model["error"]["recovery"]
            expected = step["expected"]
            passed = (
                not validation_errors
                and actual_code == expected["code"]
                and model["status"] == expected["status"]
                and model["execution"]["outcome"] == expected["outcome"]
                and actual_recovery == expected["recovery"]
                and model["execution"]["delivery"] == expected["delivery"]
                and model["data"] == expected["data"]
                and dispatcher.side_effect_count == expected["side_effect_count"]
            )
            all_passed = all_passed and passed
            step_results.append(
                {
                    "step_id": step["step_id"],
                    "actual_code": actual_code,
                    "status": model["status"],
                    "outcome": model["execution"]["outcome"],
                    "recovery": actual_recovery,
                    "delivery": model["execution"]["delivery"],
                    "side_effect_count": dispatcher.side_effect_count,
                    "validation_errors": validation_errors,
                    "passed": passed,
                }
            )
        case_results.append(
            {
                "case_id": case["id"],
                "passed": all(step["passed"] for step in step_results),
                "steps": step_results,
            }
        )
    return {
        "schema_version": fixture["schema_version"],
        "case_count": len(case_results),
        "step_count": sum(len(case["steps"]) for case in case_results),
        "passed": all_passed,
        "cases": case_results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path(__file__).with_name("tool-cases.json"),
        help="strict JSON scenario file",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = run_fixture(load_fixture(args.fixture))
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
        return 0 if summary["passed"] else 1
    except (FixtureError, OSError, ResultContractError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
