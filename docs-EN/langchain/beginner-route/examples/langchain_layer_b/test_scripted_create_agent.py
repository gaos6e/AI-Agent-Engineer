from __future__ import annotations

import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType
import unittest


EXAMPLE_DIRECTORY = Path(__file__).resolve().parent
SCRIPT_PATH = EXAMPLE_DIRECTORY / "scripted_create_agent.py"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("scripted_create_agent", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


example = load_module()


class CreateAgentRuntimeTests(unittest.TestCase):
    def test_pinned_langchain_version_is_installed(self) -> None:
        result = example.run_case()
        self.assertEqual(result["dependencies"], example.EXPECTED_DEPENDENCIES)

    def test_dependency_mismatch_fails_before_agent_execution(self) -> None:
        def wrong_version(package: str) -> str:
            return "0.0.0" if package == "langgraph" else example.EXPECTED_DEPENDENCIES[package]

        with self.assertRaisesRegex(RuntimeError, "dependency_version_mismatch"):
            example._verified_dependencies(wrong_version)

    def test_valid_tool_call_runs_once_and_preserves_call_id(self) -> None:
        result = example.run_case("success")
        tool = result["tool_records"][0]
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["message_types"], [
            "HumanMessage",
            "AIMessage",
            "ToolMessage",
            "AIMessage",
        ])
        self.assertEqual(tool["name"], "bounded_add")
        self.assertEqual(tool["tool_call_id"], "call-add-2-3")
        self.assertEqual(tool["status"], "success")
        self.assertEqual(tool["content"], "5")
        self.assertEqual(result["tool_invocations"], [{"a": 2, "b": 3}])
        self.assertEqual(result["final_answer"], "2 + 3 = 5")

    def test_unknown_tool_becomes_an_error_observation_without_execution(self) -> None:
        result = example.run_case("unknown_tool")
        tool = result["tool_records"][0]
        self.assertEqual(tool["name"], "unavailable_tool")
        self.assertEqual(tool["tool_call_id"], "call-unknown-tool")
        self.assertEqual(tool["status"], "error")
        self.assertIn("not a valid tool", tool["content"])
        self.assertEqual(result["tool_invocations"], [])

    def test_schema_rejection_becomes_a_bound_error_without_execution(self) -> None:
        result = example.run_case("invalid_arguments")
        tool = result["tool_records"][0]
        self.assertEqual(tool["name"], "bounded_add")
        self.assertEqual(tool["tool_call_id"], "call-invalid-arguments")
        self.assertEqual(tool["status"], "error")
        self.assertEqual(tool["content"], "invalid_tool_arguments")
        self.assertEqual(result["tool_invocations"], [])

    def test_invalid_mode_fails_before_agent_execution(self) -> None:
        with self.assertRaisesRegex(ValueError, "mode must be one of"):
            example.run_case("send_email")

    def test_runtime_source_uses_no_bare_assert(self) -> None:
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))


class CliTests(unittest.TestCase):
    def test_cli_contract_is_identical_with_and_without_optimization(self) -> None:
        for mode, expected_status in (
            ("success", "success"),
            ("unknown_tool", "error"),
            ("invalid_arguments", "error"),
        ):
            with self.subTest(mode=mode):
                payloads: list[dict[str, object]] = []
                for optimization_flags in ([], ["-O"]):
                    completed = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            *optimization_flags,
                            str(SCRIPT_PATH),
                            "--mode",
                            mode,
                        ],
                        check=False,
                        capture_output=True,
                        encoding="utf-8",
                        env={
                            **os.environ,
                            "PYTHONIOENCODING": "utf-8",
                            "PYTHONWARNINGS": "error",
                        },
                        timeout=30,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    payloads.append(json.loads(completed.stdout))
                self.assertEqual(payloads[0], payloads[1])
                payload = payloads[0]
                self.assertEqual(payload["status"], "completed")
                tool_records = payload["tool_records"]
                self.assertIsInstance(tool_records, list)
                self.assertEqual(tool_records[0]["status"], expected_status)
                self.assertIn("scripted model bypasses", payload["verification_boundary"])


if __name__ == "__main__":
    unittest.main()


