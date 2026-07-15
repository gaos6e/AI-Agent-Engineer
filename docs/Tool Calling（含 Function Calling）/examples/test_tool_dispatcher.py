"""Tests for the offline trusted-boundary tool dispatcher."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


EXAMPLES_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLES_DIR))

import tool_dispatcher as tools  # noqa: E402


FIXTURE_PATH = EXAMPLES_DIR / "tool-cases.json"
SCRIPT_PATH = EXAMPLES_DIR / "tool_dispatcher.py"


def principal(subject_id: str = "user-1", tenant_id: str = "tenant-a") -> tools.Principal:
    return tools.Principal(tenant_id, subject_id, ())


def read_call(
    order_ref: object = "ORDER-7",
    *,
    call_id: str = "call-read",
    operation_id: str = "op-read",
) -> tools.ToolCall:
    return tools.ToolCall(call_id, operation_id, "get_order", {"order_ref": order_ref}, None)


def write_call(
    reason: str = "duplicate",
    *,
    call_id: str = "call-write",
    operation_id: str = "op-write",
    key: str | None = "idem-write",
) -> tools.ToolCall:
    return tools.ToolCall(
        call_id,
        operation_id,
        "create_refund_draft",
        {"order_ref": "ORDER-7", "reason": reason},
        key,
    )


class FixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = tools.load_fixture(FIXTURE_PATH)

    def test_fixture_loads(self) -> None:
        self.assertEqual([], tools.validate_fixture(self.fixture))
        self.assertEqual(16, len(self.fixture["cases"]))

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema_version":"1.0","schema_version":"2.0"}', encoding="utf-8")
            with self.assertRaises(tools.FixtureError):
                tools.load_fixture(path)

    def test_nonfinite_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nan.json"
            path.write_text('{"value":NaN}', encoding="utf-8")
            with self.assertRaises(tools.FixtureError):
                tools.load_fixture(path)

    def test_extra_root_field_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["extra"] = True
        self.assertTrue(any("root" in error for error in tools.validate_fixture(changed)))

    def test_duplicate_case_id_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["cases"][1]["id"] = changed["cases"][0]["id"]
        self.assertTrue(any("case id 重复" in error for error in tools.validate_fixture(changed)))

    def test_roles_must_be_sorted_and_unique(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["cases"][0]["principal"]["roles"] = ["z", "a", "a"]
        self.assertTrue(any("已排序且无重复" in error for error in tools.validate_fixture(changed)))

    def test_now_rejects_boolean(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["cases"][0]["steps"][0]["now"] = True
        self.assertTrue(any(".now" in error for error in tools.validate_fixture(changed)))

    def test_unknown_expected_code_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["cases"][0]["steps"][0]["expected_code"] = "MAGIC"
        self.assertTrue(any("expected_code" in error for error in tools.validate_fixture(changed)))

    def test_call_extra_field_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["cases"][0]["steps"][0]["call"]["extra"] = "x"
        self.assertTrue(any("call 字段不匹配" in error for error in tools.validate_fixture(changed)))

    def test_empty_idempotency_key_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["cases"][0]["steps"][0]["call"]["idempotency_key"] = ""
        self.assertTrue(any("idempotency_key" in error for error in tools.validate_fixture(changed)))


class DigestTests(unittest.TestCase):
    def test_argument_key_order_does_not_change_request_digest(self) -> None:
        first = write_call()
        second = tools.ToolCall(
            "other-call",
            "other-operation",
            first.name,
            {"reason": "duplicate", "order_ref": "ORDER-7"},
            first.idempotency_key,
        )
        self.assertEqual(
            tools.request_digest(principal(), first),
            tools.request_digest(principal(), second),
        )

    def test_call_id_is_excluded_from_request_digest(self) -> None:
        self.assertEqual(
            tools.request_digest(principal(), write_call(call_id="a")),
            tools.request_digest(principal(), write_call(call_id="b")),
        )

    def test_principal_changes_request_digest(self) -> None:
        call = write_call()
        self.assertNotEqual(
            tools.request_digest(principal("user-1"), call),
            tools.request_digest(principal("user-2"), call),
        )

    def test_approval_digest_binds_call_and_operation(self) -> None:
        self.assertNotEqual(
            tools.approval_digest(principal(), write_call(call_id="a")),
            tools.approval_digest(principal(), write_call(call_id="b")),
        )


class DispatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dispatcher = tools.Dispatcher()
        self.principal = principal()

    def dispatch(
        self,
        call: tools.ToolCall,
        *,
        approval_mode: str = "none",
        failure: str = "none",
        now: int = 1000,
    ) -> dict[str, object]:
        approvals = tools.make_approval(self.principal, call, approval_mode, now)
        return self.dispatcher.dispatch(
            self.principal,
            call,
            approvals=approvals,
            now=now,
            failure=failure,
        )

    def test_read_own_order(self) -> None:
        result = self.dispatch(read_call())
        self.assertTrue(result["ok"])
        self.assertEqual("paid", result["data"]["status"])

    def test_other_users_order_returns_same_not_found_code(self) -> None:
        result = self.dispatch(read_call("ORDER-8"))
        self.assertEqual("NOT_FOUND", result["error"]["code"])

    def test_cross_tenant_order_returns_not_found(self) -> None:
        result = self.dispatch(read_call("ORDER-9"))
        self.assertEqual("NOT_FOUND", result["error"]["code"])

    def test_same_tenant_admin_can_read(self) -> None:
        admin = tools.Principal("tenant-a", "admin-1", ("support_admin",))
        call = read_call("ORDER-8")
        result = self.dispatcher.dispatch(admin, call, now=1000)
        self.assertTrue(result["ok"])

    def test_admin_cannot_cross_tenant(self) -> None:
        admin = tools.Principal("tenant-a", "admin-1", ("support_admin",))
        call = read_call("ORDER-9")
        result = self.dispatcher.dispatch(admin, call, now=1000)
        self.assertEqual("NOT_FOUND", result["error"]["code"])

    def test_unknown_tool_is_blocked_by_registry(self) -> None:
        call = tools.ToolCall("c", "o", "dynamic.module.delete", {}, None)
        result = self.dispatch(call)
        self.assertEqual("UNKNOWN_TOOL", result["error"]["code"])

    def test_missing_argument_is_rejected(self) -> None:
        call = tools.ToolCall("c", "o", "get_order", {}, None)
        self.assertEqual("INVALID_ARGUMENTS", self.dispatch(call)["error"]["code"])

    def test_extra_argument_is_rejected(self) -> None:
        call = tools.ToolCall("c", "o", "get_order", {"order_ref": "ORDER-7", "admin": True}, None)
        self.assertEqual("INVALID_ARGUMENTS", self.dispatch(call)["error"]["code"])

    def test_wrong_type_is_rejected(self) -> None:
        self.assertEqual("INVALID_ARGUMENTS", self.dispatch(read_call(7))["error"]["code"])

    def test_enum_rejects_instruction_text(self) -> None:
        result = self.dispatch(write_call("ignore rules"), approval_mode="valid")
        self.assertEqual("INVALID_ARGUMENTS", result["error"]["code"])

    def test_write_requires_idempotency_key(self) -> None:
        result = self.dispatch(write_call(key=None), approval_mode="valid")
        self.assertEqual("IDEMPOTENCY_KEY_REQUIRED", result["error"]["code"])

    def test_write_requires_approval(self) -> None:
        result = self.dispatch(write_call())
        self.assertEqual("APPROVAL_REQUIRED", result["error"]["code"])
        self.assertEqual(0, self.dispatcher.side_effect_count)

    def test_valid_approval_executes_once(self) -> None:
        result = self.dispatch(write_call(), approval_mode="valid")
        self.assertTrue(result["ok"])
        self.assertEqual(1, self.dispatcher.side_effect_count)

    def test_expired_approval_is_rejected(self) -> None:
        result = self.dispatch(write_call(), approval_mode="expired")
        self.assertEqual("APPROVAL_INVALID", result["error"]["code"])

    def test_mismatched_approval_is_rejected(self) -> None:
        result = self.dispatch(write_call(), approval_mode="mismatched")
        self.assertEqual("APPROVAL_INVALID", result["error"]["code"])

    def test_approval_for_old_arguments_cannot_authorize_new_arguments(self) -> None:
        old_call = write_call("duplicate")
        new_call = write_call("damaged")
        approval = tools.make_approval(self.principal, old_call, "valid", 1000)
        result = self.dispatcher.dispatch(
            self.principal, new_call, approvals=approval, now=1000
        )
        self.assertEqual("APPROVAL_INVALID", result["error"]["code"])

    def test_safe_retry_can_use_new_call_id_without_second_side_effect(self) -> None:
        first_call = write_call(call_id="first", operation_id="op-first")
        first = self.dispatch(first_call, approval_mode="valid")
        retry_call = write_call(call_id="retry", operation_id="op-retry")
        retry = self.dispatch(retry_call)
        self.assertFalse(first["cached"])
        self.assertTrue(retry["cached"])
        self.assertEqual(first["data"], retry["data"])
        self.assertEqual(1, self.dispatcher.side_effect_count)

    def test_same_idempotency_key_with_changed_arguments_conflicts(self) -> None:
        self.dispatch(write_call("duplicate"), approval_mode="valid")
        changed = write_call("damaged", call_id="changed", operation_id="op-changed")
        result = self.dispatch(changed, approval_mode="valid")
        self.assertEqual("IDEMPOTENCY_CONFLICT", result["error"]["code"])
        self.assertEqual(1, self.dispatcher.side_effect_count)

    def test_same_call_id_with_changed_request_conflicts(self) -> None:
        self.dispatch(read_call("ORDER-7", call_id="same", operation_id="same-op"))
        changed = read_call("ORDER-8", call_id="same", operation_id="same-op")
        result = self.dispatch(changed)
        self.assertEqual("CALL_ID_CONFLICT", result["error"]["code"])

    def test_timeout_is_retryable_and_has_no_side_effect(self) -> None:
        result = self.dispatch(write_call(), approval_mode="valid", failure="timeout")
        self.assertEqual("TIMEOUT", result["error"]["code"])
        self.assertTrue(result["error"]["retryable"])
        self.assertEqual(0, self.dispatcher.side_effect_count)

    def test_tool_error_is_not_retryable_by_default(self) -> None:
        result = self.dispatch(read_call(), failure="tool_error")
        self.assertEqual("TOOL_ERROR", result["error"]["code"])
        self.assertFalse(result["error"]["retryable"])

    def test_success_data_is_marked_untrusted(self) -> None:
        result = self.dispatch(read_call())
        self.assertTrue(result["untrusted"])
        self.assertEqual([], tools.validate_result(read_call(), result))


class ResultContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.call = read_call()
        self.result = tools.Dispatcher().dispatch(principal(), self.call, now=1000)

    def test_result_contract_is_valid(self) -> None:
        self.assertEqual([], tools.validate_result(self.call, self.result))

    def test_changed_call_id_is_detected(self) -> None:
        changed = copy.deepcopy(self.result)
        changed["call_id"] = "wrong"
        self.assertTrue(any("关联" in error for error in tools.validate_result(self.call, changed)))

    def test_extra_result_field_is_detected(self) -> None:
        changed = copy.deepcopy(self.result)
        changed["debug"] = True
        self.assertTrue(any("result 字段不匹配" in error for error in tools.validate_result(self.call, changed)))

    def test_success_cannot_hide_error(self) -> None:
        changed = copy.deepcopy(self.result)
        changed["error"] = {"code": "TOOL_ERROR", "retryable": False, "message": "x"}
        self.assertTrue(any("成功结果" in error for error in tools.validate_result(self.call, changed)))

    def test_digest_shape_is_checked(self) -> None:
        changed = copy.deepcopy(self.result)
        changed["request_digest"] = "not-a-digest"
        self.assertTrue(any("12 位" in error for error in tools.validate_result(self.call, changed)))


class EvaluationAndCliTests(unittest.TestCase):
    def test_all_data_driven_cases_pass(self) -> None:
        summary = tools.run_fixture(tools.load_fixture(FIXTURE_PATH))
        self.assertTrue(summary["passed"])
        self.assertEqual(19, summary["step_count"])

    def run_cli(self, *, optimized: bool = False) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(["-B", "-W", "error", str(SCRIPT_PATH), "--fixture", str(FIXTURE_PATH)])
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )

    def test_cli_passes(self) -> None:
        completed = self.run_cli()
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["passed"])

    def test_cli_passes_under_optimization(self) -> None:
        completed = self.run_cli(optimized=True)
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["passed"])


if __name__ == "__main__":
    unittest.main()
