"""Offline tool dispatcher with strict contracts, approvals, and idempotency.

The module uses only the Python standard library. It does not call a model,
network service, or real business system. The goal is to make the trusted
application boundary around model-proposed tool calls executable and testable.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable


ROOT_FIELDS = {"schema_version", "cases"}
CASE_FIELDS = {"id", "principal", "steps"}
PRINCIPAL_FIELDS = {"tenant_id", "subject_id", "roles"}
STEP_FIELDS = {
    "step_id",
    "call",
    "approval",
    "now",
    "failure",
    "expected_code",
    "expected_cached",
    "expected_side_effect_count",
}
CALL_FIELDS = {
    "call_id",
    "operation_id",
    "name",
    "arguments",
    "idempotency_key",
}
RESULT_FIELDS = {
    "ok",
    "call_id",
    "operation_id",
    "data",
    "error",
    "source",
    "untrusted",
    "cached",
    "request_digest",
}
ERROR_FIELDS = {"code", "retryable", "message"}
VALID_APPROVAL_MODES = {"none", "valid", "expired", "mismatched"}
VALID_FAILURES = {"none", "timeout", "rate_limit", "tool_error"}
ERROR_MESSAGES = {
    "UNKNOWN_TOOL": "工具未在允许列表中。",
    "INVALID_ARGUMENTS": "参数不符合工具合同。",
    "NOT_FOUND": "资源不存在或当前主体不可访问。",
    "CALL_ID_CONFLICT": "同一 operation/call ID 被用于不同请求。",
    "IDEMPOTENCY_KEY_REQUIRED": "写操作缺少幂等键。",
    "IDEMPOTENCY_CONFLICT": "同一幂等键对应了不同请求。",
    "APPROVAL_REQUIRED": "此操作需要绑定当前参数的审批。",
    "APPROVAL_INVALID": "审批已过期或未绑定当前请求。",
    "TIMEOUT": "工具在截止时间内没有完成。",
    "RATE_LIMIT": "工具当前受到速率限制。",
    "TOOL_ERROR": "工具执行失败。",
}
RETRYABLE_CODES = {"TIMEOUT", "RATE_LIMIT"}
HEX12_PATTERN = re.compile(r"^[0-9a-f]{12}$")


class FixtureError(ValueError):
    """Raised when the case fixture violates its strict JSON contract."""


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    subject_id: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    operation_id: str
    name: str
    arguments: dict[str, Any]
    idempotency_key: str | None


@dataclass(frozen=True)
class Approval:
    approval_id: str
    operation_id: str
    call_id: str
    tool_name: str
    subject_id: str
    argument_digest: str
    expires_at: int
    approver_id: str


@dataclass(frozen=True)
class ArgumentRule:
    python_type: type
    min_length: int | None = None
    enum: frozenset[str] | None = None


@dataclass(frozen=True)
class ToolSpec:
    schema_version: str
    risk: str
    arguments: dict[str, ArgumentRule]
    timeout_ms: int
    handler: Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class IdempotencyRecord:
    request_digest: str
    data: dict[str, Any]
    source: str


def _reject_constant(value: str) -> None:
    raise FixtureError(f"JSON 不允许非有限常量：{value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FixtureError(f"JSON 出现重复字段：{key}")
        result[key] = value
    return result


def _exact_fields(value: Any, expected: set[str], label: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{label} 必须是对象")
        return False
    actual = set(value)
    if actual != expected:
        errors.append(
            f"{label} 字段不匹配：missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )
        return False
    return True


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sorted_unique_strings(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not all(_nonempty_string(item) for item in value):
        errors.append(f"{label} 必须是字符串列表")
        return
    if value != sorted(set(value)):
        errors.append(f"{label} 必须已排序且无重复")


def validate_fixture(fixture: Any) -> list[str]:
    """Return all detectable errors in a data-driven dispatcher fixture."""

    errors: list[str] = []
    if not _exact_fields(fixture, ROOT_FIELDS, "root", errors):
        return errors
    if fixture["schema_version"] != "1.0":
        errors.append("schema_version 必须为 '1.0'")
    cases = fixture["cases"]
    if not isinstance(cases, list) or not cases:
        errors.append("cases 必须是非空列表")
        return errors
    case_ids: set[str] = set()
    for case_index, case in enumerate(cases):
        case_label = f"cases[{case_index}]"
        if not _exact_fields(case, CASE_FIELDS, case_label, errors):
            continue
        if not _nonempty_string(case["id"]):
            errors.append(f"{case_label}.id 必须是非空字符串")
        elif case["id"] in case_ids:
            errors.append(f"case id 重复：{case['id']}")
        else:
            case_ids.add(case["id"])

        principal = case["principal"]
        if _exact_fields(principal, PRINCIPAL_FIELDS, f"{case_label}.principal", errors):
            for field in ("tenant_id", "subject_id"):
                if not _nonempty_string(principal[field]):
                    errors.append(f"{case_label}.principal.{field} 必须是非空字符串")
            _sorted_unique_strings(principal["roles"], f"{case_label}.principal.roles", errors)

        steps = case["steps"]
        if not isinstance(steps, list) or not steps:
            errors.append(f"{case_label}.steps 必须是非空列表")
            continue
        step_ids: set[str] = set()
        for step_index, step in enumerate(steps):
            step_label = f"{case_label}.steps[{step_index}]"
            if not _exact_fields(step, STEP_FIELDS, step_label, errors):
                continue
            if not _nonempty_string(step["step_id"]):
                errors.append(f"{step_label}.step_id 必须是非空字符串")
            elif step["step_id"] in step_ids:
                errors.append(f"{case_label} 的 step id 重复：{step['step_id']}")
            else:
                step_ids.add(step["step_id"])

            call = step["call"]
            if _exact_fields(call, CALL_FIELDS, f"{step_label}.call", errors):
                for field in ("call_id", "operation_id", "name"):
                    if not _nonempty_string(call[field]):
                        errors.append(f"{step_label}.call.{field} 必须是非空字符串")
                if not isinstance(call["arguments"], dict):
                    errors.append(f"{step_label}.call.arguments 必须是对象")
                key = call["idempotency_key"]
                if key is not None and not _nonempty_string(key):
                    errors.append(f"{step_label}.call.idempotency_key 必须为 null 或非空字符串")
            if step["approval"] not in VALID_APPROVAL_MODES:
                errors.append(f"{step_label}.approval 非法")
            if type(step["now"]) is not int or step["now"] < 0:
                errors.append(f"{step_label}.now 必须是非负整数")
            if step["failure"] not in VALID_FAILURES:
                errors.append(f"{step_label}.failure 非法")
            if step["expected_code"] != "OK" and step["expected_code"] not in ERROR_MESSAGES:
                errors.append(f"{step_label}.expected_code 非法")
            if type(step["expected_cached"]) is not bool:
                errors.append(f"{step_label}.expected_cached 必须是布尔值")
            if (
                type(step["expected_side_effect_count"]) is not int
                or step["expected_side_effect_count"] < 0
            ):
                errors.append(f"{step_label}.expected_side_effect_count 必须是非负整数")
    return errors


def load_fixture(path: Path) -> dict[str, Any]:
    """Load strict UTF-8 JSON and validate its exact schema."""

    try:
        fixture = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FixtureError(f"无法读取 fixture：{exc}") from exc
    errors = validate_fixture(fixture)
    if errors:
        raise FixtureError("fixture 校验失败：\n- " + "\n- ".join(errors))
    if not isinstance(fixture, dict):
        raise FixtureError("fixture root 必须是对象")
    return fixture


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def request_digest(principal: Principal, call: ToolCall) -> str:
    """Digest the trusted subject, tool, and intent; exclude transient call IDs."""

    return _digest(
        {
            "tenant_id": principal.tenant_id,
            "subject_id": principal.subject_id,
            "tool": call.name,
            "arguments": call.arguments,
        }
    )


def call_fingerprint(principal: Principal, call: ToolCall) -> str:
    """Bind a model call ID to one exact operation and proposed action."""

    return _digest(
        {
            "operation_id": call.operation_id,
            "call_id": call.call_id,
            "idempotency_key": call.idempotency_key,
            "request_digest": request_digest(principal, call),
        }
    )


def approval_digest(principal: Principal, call: ToolCall) -> str:
    """Bind approval to the exact call, operation, subject, tool, and arguments."""

    return _digest(
        {
            "operation_id": call.operation_id,
            "call_id": call.call_id,
            "request_digest": request_digest(principal, call),
        }
    )


def make_approval(
    principal: Principal, call: ToolCall, mode: str, now: int
) -> tuple[Approval, ...]:
    """Create deterministic fixture approvals; production approvals come from trusted UI/workflow."""

    if mode == "none":
        return ()
    if mode not in VALID_APPROVAL_MODES:
        raise ValueError(f"未知 approval mode：{mode}")
    digest = approval_digest(principal, call)
    expires_at = now + 60
    if mode == "expired":
        expires_at = now - 1
    elif mode == "mismatched":
        digest = "0" * 64
    return (
        Approval(
            approval_id=f"approval-{call.call_id}",
            operation_id=call.operation_id,
            call_id=call.call_id,
            tool_name=call.name,
            subject_id=principal.subject_id,
            argument_digest=digest,
            expires_at=expires_at,
            approver_id="human-reviewer-1",
        ),
    )


def _success(
    call: ToolCall,
    data: dict[str, Any],
    source: str,
    digest: str,
    *,
    cached: bool,
) -> dict[str, Any]:
    return {
        "ok": True,
        "call_id": call.call_id,
        "operation_id": call.operation_id,
        "data": data,
        "error": None,
        "source": source,
        "untrusted": True,
        "cached": cached,
        "request_digest": digest[:12],
    }


def _error(call: ToolCall, code: str, digest: str) -> dict[str, Any]:
    return {
        "ok": False,
        "call_id": call.call_id,
        "operation_id": call.operation_id,
        "data": None,
        "error": {
            "code": code,
            "retryable": code in RETRYABLE_CODES,
            "message": ERROR_MESSAGES[code],
        },
        "source": "offline-dispatcher",
        "untrusted": False,
        "cached": False,
        "request_digest": digest[:12],
    }


def validate_result(call: ToolCall, result: Any) -> list[str]:
    """Validate the adapter envelope before it is returned to a model."""

    errors: list[str] = []
    if not _exact_fields(result, RESULT_FIELDS, "result", errors):
        return errors
    if type(result["ok"]) is not bool:
        errors.append("result.ok 必须是布尔值")
    if result["call_id"] != call.call_id or result["operation_id"] != call.operation_id:
        errors.append("result 未关联到当前 call/operation")
    if not _nonempty_string(result["source"]):
        errors.append("result.source 必须是非空字符串")
    if type(result["untrusted"]) is not bool or type(result["cached"]) is not bool:
        errors.append("result.untrusted/cached 必须是布尔值")
    if not isinstance(result["request_digest"], str) or HEX12_PATTERN.fullmatch(
        result["request_digest"]
    ) is None:
        errors.append("result.request_digest 必须是 12 位十六进制摘要")
    if result["ok"] is True:
        if not isinstance(result["data"], dict) or result["error"] is not None:
            errors.append("成功结果必须有对象 data 且 error=null")
        if result["untrusted"] is not True:
            errors.append("成功工具数据必须标记为 untrusted")
    else:
        if result["data"] is not None or not _exact_fields(
            result["error"], ERROR_FIELDS, "result.error", errors
        ):
            errors.append("失败结果必须 data=null 且包含严格 error")
        elif result["error"]["code"] not in ERROR_MESSAGES:
            errors.append("result.error.code 非法")
        else:
            expected_retryable = result["error"]["code"] in RETRYABLE_CODES
            if result["error"]["retryable"] is not expected_retryable:
                errors.append("result.error.retryable 与错误分类不一致")
            if not _nonempty_string(result["error"]["message"]):
                errors.append("result.error.message 必须是非空字符串")
        if result["cached"] is not False:
            errors.append("失败结果不得标记 cached")
    return errors


class Dispatcher:
    """Trusted application-side dispatcher for two deterministic mock tools."""

    def __init__(self) -> None:
        self.side_effect_count = 0
        self.idempotency_records: dict[str, IdempotencyRecord] = {}
        self.call_fingerprints: dict[tuple[str, str], str] = {}
        self.orders = {
            "ORDER-7": {"tenant_id": "tenant-a", "owner_id": "user-1", "status": "paid"},
            "ORDER-8": {"tenant_id": "tenant-a", "owner_id": "user-2", "status": "paid"},
            "ORDER-9": {"tenant_id": "tenant-b", "owner_id": "user-1", "status": "paid"},
        }
        self.registry = {
            "get_order": ToolSpec(
                schema_version="get-order-v1",
                risk="read",
                arguments={"order_ref": ArgumentRule(str, min_length=1)},
                timeout_ms=500,
                handler=self._get_order,
            ),
            "create_refund_draft": ToolSpec(
                schema_version="refund-draft-v1",
                risk="write",
                arguments={
                    "order_ref": ArgumentRule(str, min_length=1),
                    "reason": ArgumentRule(
                        str,
                        min_length=1,
                        enum=frozenset({"duplicate", "damaged", "other"}),
                    ),
                },
                timeout_ms=800,
                handler=self._create_refund_draft,
            ),
        }

    @staticmethod
    def _validate_arguments(spec: ToolSpec, arguments: dict[str, Any]) -> bool:
        if set(arguments) != set(spec.arguments):
            return False
        for name, rule in spec.arguments.items():
            value = arguments[name]
            if type(value) is not rule.python_type:
                return False
            if isinstance(value, str):
                if rule.min_length is not None and len(value.strip()) < rule.min_length:
                    return False
                if rule.enum is not None and value not in rule.enum:
                    return False
        return True

    def _authorized_order(self, principal: Principal, order_ref: str) -> bool:
        order = self.orders.get(order_ref)
        if order is None:
            return False
        if order["tenant_id"] != principal.tenant_id:
            return False
        return order["owner_id"] == principal.subject_id or "support_admin" in principal.roles

    @staticmethod
    def _approval_valid(
        approvals: tuple[Approval, ...],
        principal: Principal,
        call: ToolCall,
        now: int,
    ) -> bool:
        expected_digest = approval_digest(principal, call)
        return any(
            approval.operation_id == call.operation_id
            and approval.call_id == call.call_id
            and approval.tool_name == call.name
            and approval.subject_id == principal.subject_id
            and approval.argument_digest == expected_digest
            and approval.expires_at >= now
            for approval in approvals
        )

    def dispatch(
        self,
        principal: Principal,
        call: ToolCall,
        *,
        approvals: tuple[Approval, ...] = (),
        now: int,
        failure: str = "none",
    ) -> dict[str, Any]:
        """Validate, authorize, deduplicate, approve, execute, and envelope one call."""

        if failure not in VALID_FAILURES:
            raise ValueError(f"未知 failure：{failure}")
        digest = request_digest(principal, call)
        spec = self.registry.get(call.name)
        if spec is None:
            return _error(call, "UNKNOWN_TOOL", digest)
        if not self._validate_arguments(spec, call.arguments):
            return _error(call, "INVALID_ARGUMENTS", digest)

        call_key = (call.operation_id, call.call_id)
        fingerprint = call_fingerprint(principal, call)
        prior_fingerprint = self.call_fingerprints.get(call_key)
        if prior_fingerprint is not None and prior_fingerprint != fingerprint:
            return _error(call, "CALL_ID_CONFLICT", digest)
        self.call_fingerprints[call_key] = fingerprint

        order_ref = call.arguments["order_ref"]
        if not self._authorized_order(principal, order_ref):
            return _error(call, "NOT_FOUND", digest)

        if spec.risk == "write":
            if not call.idempotency_key:
                return _error(call, "IDEMPOTENCY_KEY_REQUIRED", digest)
            record = self.idempotency_records.get(call.idempotency_key)
            if record is not None:
                if record.request_digest != digest:
                    return _error(call, "IDEMPOTENCY_CONFLICT", digest)
                return _success(call, record.data, record.source, digest, cached=True)

        if failure == "timeout":
            return _error(call, "TIMEOUT", digest)
        if failure == "rate_limit":
            return _error(call, "RATE_LIMIT", digest)
        if failure == "tool_error":
            return _error(call, "TOOL_ERROR", digest)

        if spec.risk == "write":
            if not approvals:
                return _error(call, "APPROVAL_REQUIRED", digest)
            if not self._approval_valid(approvals, principal, call, now):
                return _error(call, "APPROVAL_INVALID", digest)

        data = spec.handler(call.arguments)
        source = "order-service-mock"
        result = _success(call, data, source, digest, cached=False)
        if spec.risk == "write" and call.idempotency_key is not None:
            self.idempotency_records[call.idempotency_key] = IdempotencyRecord(
                request_digest=digest,
                data=data,
                source=source,
            )
        return result

    def _get_order(self, arguments: dict[str, Any]) -> dict[str, Any]:
        order = self.orders[arguments["order_ref"]]
        return {"order_ref": arguments["order_ref"], "status": order["status"]}

    def _create_refund_draft(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self.side_effect_count += 1
        return {
            "draft_id": f"DRAFT-{self.side_effect_count}",
            "order_ref": arguments["order_ref"],
            "reason": arguments["reason"],
        }


def _principal_from_fixture(value: dict[str, Any]) -> Principal:
    return Principal(value["tenant_id"], value["subject_id"], tuple(value["roles"]))


def _call_from_fixture(value: dict[str, Any]) -> ToolCall:
    return ToolCall(
        call_id=value["call_id"],
        operation_id=value["operation_id"],
        name=value["name"],
        arguments=value["arguments"],
        idempotency_key=value["idempotency_key"],
    )


def run_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Run every case in isolation and return a machine-checkable evaluation summary."""

    case_results: list[dict[str, Any]] = []
    all_passed = True
    for case in fixture["cases"]:
        dispatcher = Dispatcher()
        principal = _principal_from_fixture(case["principal"])
        step_results: list[dict[str, Any]] = []
        for step in case["steps"]:
            call = _call_from_fixture(step["call"])
            approvals = make_approval(principal, call, step["approval"], step["now"])
            result = dispatcher.dispatch(
                principal,
                call,
                approvals=approvals,
                now=step["now"],
                failure=step["failure"],
            )
            validation_errors = validate_result(call, result)
            actual_code = "OK" if result["ok"] else result["error"]["code"]
            passed = (
                not validation_errors
                and actual_code == step["expected_code"]
                and result["cached"] is step["expected_cached"]
                and dispatcher.side_effect_count == step["expected_side_effect_count"]
            )
            all_passed = all_passed and passed
            step_results.append(
                {
                    "step_id": step["step_id"],
                    "actual_code": actual_code,
                    "cached": result["cached"],
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
        help="严格 JSON 场景文件",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = run_fixture(load_fixture(args.fixture))
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if summary["passed"] else 1
    except (FixtureError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
