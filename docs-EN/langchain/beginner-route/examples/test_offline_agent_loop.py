"""Regression tests for the offline LangChain concept-mapping project."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any


EXAMPLES = Path(__file__).resolve().parent
LOOP_PATH = EXAMPLES / "offline_agent_loop.py"
LCEL_PATH = EXAMPLES / "lcel_no_key.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


agent = load_module("offline_agent_loop_teaching", LOOP_PATH)


class CalculatorTests(unittest.TestCase):
    def test_addition(self) -> None:
        self.assertEqual(agent.safe_calculate("2 + 3"), 5)

    def test_precedence(self) -> None:
        self.assertEqual(agent.safe_calculate("12 * (3 + 2)"), 60)

    def test_unary(self) -> None:
        self.assertEqual(agent.safe_calculate("-(2 + 3)"), -5)

    def test_floor_division(self) -> None:
        self.assertEqual(agent.safe_calculate("7 // 2"), 3)

    def test_modulo(self) -> None:
        self.assertEqual(agent.safe_calculate("7 % 3"), 1)

    def test_division(self) -> None:
        self.assertEqual(agent.safe_calculate("5 / 2"), 2.5)

    def test_empty_expression(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty"):
            agent.safe_calculate("")

    def test_long_expression(self) -> None:
        with self.assertRaisesRegex(ValueError, "too long"):
            agent.safe_calculate("1+" * 100 + "1")

    def test_invalid_syntax(self) -> None:
        with self.assertRaisesRegex(ValueError, "syntax is invalid"):
            agent.safe_calculate("1 +")

    def test_function_call_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "not allowed"):
            agent.safe_calculate("abs(-1)")

    def test_attribute_access_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "not allowed"):
            agent.safe_calculate("x.real")

    def test_name_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "not allowed"):
            agent.safe_calculate("secret + 1")

    def test_power_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "not allowed"):
            agent.safe_calculate("2 ** 8")

    def test_boolean_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "not allowed"):
            agent.safe_calculate("True")

    def test_division_by_zero(self) -> None:
        with self.assertRaisesRegex(ValueError, "division by zero"):
            agent.safe_calculate("1 / 0")

    def test_modulo_by_zero(self) -> None:
        with self.assertRaisesRegex(ValueError, "division by zero"):
            agent.safe_calculate("1 % 0")

    def test_infinite_float_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite number"):
            agent.safe_calculate("1e309")

    def test_large_result_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "exceeds"):
            agent.safe_calculate("1000000000000 + 1")

    def test_too_many_nodes_are_rejected(self) -> None:
        expression = "+".join("1" for _ in range(34))
        with self.assertRaisesRegex(ValueError, "too many nodes"):
            agent.safe_calculate(expression)

    def test_deep_tree_is_rejected(self) -> None:
        expression = "-" * 20 + "1"
        with self.assertRaisesRegex(ValueError, "nesting is too deep"):
            agent.safe_calculate(expression)


class PolicyAndIdentifierTests(unittest.TestCase):
    def test_refund_policy_has_source(self) -> None:
        result = agent.lookup_policy("refund")
        self.assertEqual(result["source_id"], "offline-policy:refund:v1")

    def test_policy_topic_is_normalized(self) -> None:
        self.assertEqual(agent.lookup_policy(" PRIVACY ")["topic"], "privacy")

    def test_unknown_policy_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown policy"):
            agent.lookup_policy("other")

    def test_empty_policy_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty"):
            agent.lookup_policy("")

    def test_stable_call_id_is_deterministic(self) -> None:
        first = agent.stable_call_id("calculator", "2+3")
        self.assertEqual(first, agent.stable_call_id("calculator", "2+3"))
        self.assertRegex(first, agent.TOOL_CALL_ID_PATTERN)

    def test_different_argument_changes_call_id(self) -> None:
        self.assertNotEqual(
            agent.stable_call_id("calculator", "2+3"),
            agent.stable_call_id("calculator", "2+4"),
        )


class ContractTests(unittest.TestCase):
    def valid_call(self) -> dict[str, Any]:
        return {
            "type": "tool_call",
            "id": agent.stable_call_id("calculator", "2+3"),
            "name": "calculator",
            "arguments": {"expression": "2+3"},
        }

    def test_final_response_is_valid(self) -> None:
        response = {"type": "final", "content": "done"}
        self.assertIs(agent.validate_model_response(response), response)

    def test_non_object_response_is_rejected(self) -> None:
        with self.assertRaisesRegex(agent.ContractError, "must be an object"):
            agent.validate_model_response("done")

    def test_unknown_response_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(agent.ContractError, "type"):
            agent.validate_model_response({"type": "other"})

    def test_final_extra_field_is_rejected(self) -> None:
        with self.assertRaisesRegex(agent.ContractError, "fields"):
            agent.validate_model_response({"type": "final", "content": "x", "extra": 1})

    def test_final_empty_content_is_rejected(self) -> None:
        with self.assertRaisesRegex(agent.ContractError, "non-empty"):
            agent.validate_model_response({"type": "final", "content": ""})

    def test_tool_call_extra_field_is_rejected(self) -> None:
        call = self.valid_call()
        call["extra"] = True
        with self.assertRaisesRegex(agent.ContractError, "fields"):
            agent.validate_model_response(call)

    def test_tool_call_bad_id_is_rejected(self) -> None:
        call = self.valid_call()
        call["id"] = "call-1"
        with self.assertRaisesRegex(agent.ContractError, "id"):
            agent.validate_model_response(call)

    def test_tool_call_arguments_must_be_object(self) -> None:
        call = self.valid_call()
        call["arguments"] = []
        with self.assertRaisesRegex(agent.ContractError, "arguments"):
            agent.validate_model_response(call)

    def test_execute_known_tool(self) -> None:
        result = agent.execute_tool(self.valid_call())
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["content"], 5)

    def test_execute_unknown_tool_returns_error(self) -> None:
        call = self.valid_call()
        call["name"] = "shell"
        result = agent.execute_tool(call)
        self.assertEqual(result["error_code"], "TOOL_NOT_ALLOWED")

    def test_execute_extra_argument_returns_error(self) -> None:
        call = self.valid_call()
        call["arguments"]["extra"] = 1
        result = agent.execute_tool(call)
        self.assertEqual(result["error_code"], "INVALID_ARGUMENT_SHAPE")

    def test_execute_wrong_argument_type_returns_error(self) -> None:
        call = self.valid_call()
        call["arguments"]["expression"] = 3
        result = agent.execute_tool(call)
        self.assertEqual(result["error_code"], "INVALID_ARGUMENT_TYPE")

    def test_tool_rejection_is_structured(self) -> None:
        call = self.valid_call()
        call["arguments"]["expression"] = "open('x')"
        result = agent.execute_tool(call)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_code"], "TOOL_INPUT_REJECTED")

    def test_tool_message_call_id_must_match(self) -> None:
        call = self.valid_call()
        message = agent.execute_tool(call)
        message["tool_call_id"] = agent.stable_call_id("calculator", "9")
        with self.assertRaisesRegex(agent.ContractError, "tool_call_id"):
            agent.validate_tool_message(message, call)

    def test_tool_message_name_must_match(self) -> None:
        call = self.valid_call()
        message = agent.execute_tool(call)
        message["name"] = "lookup_policy"
        with self.assertRaisesRegex(agent.ContractError, "tool name"):
            agent.validate_tool_message(message, call)

    def test_success_message_needs_content(self) -> None:
        call = self.valid_call()
        message = agent.execute_tool(call)
        message.pop("content")
        with self.assertRaisesRegex(agent.ContractError, "successful tool-message"):
            agent.validate_tool_message(message, call)

    def test_error_message_needs_code(self) -> None:
        call = self.valid_call()
        call["name"] = "shell"
        message = agent.execute_tool(call)
        message.pop("error_code")
        with self.assertRaisesRegex(agent.ContractError, "failed tool-message"):
            agent.validate_tool_message(message, call)


class AgentLoopTests(unittest.TestCase):
    def test_calculation_uses_one_tool(self) -> None:
        state = agent.run_agent("calculate 12 * (3 + 2)")
        self.assertEqual(state["status"], "done")
        self.assertEqual(state["tool_calls"], 1)
        self.assertEqual(state["messages"][-1]["content"], 60)

    def test_policy_lookup_has_citation(self) -> None:
        state = agent.run_agent("look up policy privacy")
        self.assertIn("offline-policy:privacy:v1", state["answer"])

    def test_direct_answer_uses_no_tool(self) -> None:
        state = agent.run_agent("explain tool calling")
        self.assertEqual(state["tool_calls"], 0)
        self.assertEqual(len(state["trace"]), 1)

    def test_dangerous_expression_is_not_executed(self) -> None:
        state = agent.run_agent("calculate __import__('os').getcwd()")
        self.assertEqual(state["messages"][-1]["status"], "error")
        self.assertEqual(state["messages"][-1]["error_code"], "TOOL_INPUT_REJECTED")

    def test_query_must_be_nonempty(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty"):
            agent.run_agent("")

    def test_model_budget_must_be_positive(self) -> None:
        with self.assertRaisesRegex(ValueError, "budget"):
            agent.run_agent("x", max_model_steps=0)

    def test_tool_budget_must_not_be_negative(self) -> None:
        with self.assertRaisesRegex(ValueError, "budget"):
            agent.run_agent("x", max_tool_calls=-1)

    def test_zero_tool_budget_stops_before_execution(self) -> None:
        state = agent.run_agent("calculate 2 + 3", max_tool_calls=0)
        self.assertEqual(state["status"], "tool_budget_exhausted")
        self.assertEqual(state["tool_calls"], 0)

    def test_model_step_limit_is_explicit(self) -> None:
        state = agent.run_agent("calculate 2 + 3", max_model_steps=1)
        self.assertEqual(state["status"], "model_step_limit")

    def test_repeated_tool_call_is_stopped(self) -> None:
        call = {
            "type": "tool_call",
            "id": agent.stable_call_id("calculator", "2+3"),
            "name": "calculator",
            "arguments": {"expression": "2+3"},
        }

        def repeating_model(_messages: list[dict[str, Any]]) -> dict[str, Any]:
            return dict(call)

        state = agent.run_agent("x", model=repeating_model)
        self.assertEqual(state["status"], "repeated_tool_call")
        self.assertEqual(state["tool_calls"], 1)

    def test_invalid_model_response_fails_closed(self) -> None:
        def invalid_model(_messages: list[dict[str, Any]]) -> dict[str, Any]:
            return {"type": "tool_call", "name": "calculator"}

        with self.assertRaises(agent.ContractError):
            agent.run_agent("x", model=invalid_model)

    def test_custom_registry_can_deny_default_tool(self) -> None:
        state = agent.run_agent("calculate 2 + 3", tools={})
        self.assertEqual(state["messages"][-1]["error_code"], "TOOL_NOT_ALLOWED")

    def test_trace_binds_tool_call_id(self) -> None:
        state = agent.run_agent("calculate 2 + 3")
        self.assertRegex(state["trace"][0]["tool_call_id"], agent.TOOL_CALL_ID_PATTERN)

    def test_public_result_omits_raw_messages(self) -> None:
        state = agent.run_agent("calculate 2 + 3")
        output = agent.public_result(state)
        self.assertNotIn("messages", output)

    def test_self_test_under_explicit_checks(self) -> None:
        self.assertIsNone(agent.self_test())


class CliTests(unittest.TestCase):
    def run_python(self, path: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(path), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

    def test_cli_calculation(self) -> None:
        result = self.run_python(LOOP_PATH, "calculate 2 + 3")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["tool_calls"], 1)

    def test_cli_output_omits_messages(self) -> None:
        result = self.run_python(LOOP_PATH, "calculate 2 + 3")
        self.assertNotIn("messages", json.loads(result.stdout))

    def test_cli_self_test(self) -> None:
        result = self.run_python(LOOP_PATH, "--self-test")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["checks"], 5)

    def test_cli_empty_query_is_error(self) -> None:
        result = self.run_python(LOOP_PATH, "")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["status"], "error")

    def test_lcel_example_reports_dependency_state(self) -> None:
        result = self.run_python(LCEL_PATH, " hello   agent ")
        self.assertIn(result.returncode, {0, 4})
        stream = result.stdout if result.returncode == 0 else result.stderr
        self.assertIn(json.loads(stream)["status"], {"ok", "dependency_missing"})


if __name__ == "__main__":
    unittest.main(verbosity=2)


