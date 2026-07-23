"""Offline contract checks for the OpenAI API lesson's Python snippets."""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path
from types import SimpleNamespace


LESSON_PATH = Path(__file__).parents[1] / "AI API 调用" / "01-OpenAI API.md"
PYTHON_FENCE = re.compile(r"```python\s*\n(.*?)\n```", re.DOTALL)


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


class OpenAIMarkdownContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.markdown = LESSON_PATH.read_text(encoding="utf-8")
        cls.blocks = PYTHON_FENCE.findall(cls.markdown)

    def test_all_python_fences_parse(self) -> None:
        self.assertEqual(len(self.blocks), 16)
        for index, block in enumerate(self.blocks, start=1):
            with self.subTest(block=index):
                ast.parse(block, filename=f"openai-lesson-block-{index}.py")

    def test_every_responses_call_makes_storage_explicit(self) -> None:
        calls: list[tuple[int, ast.Call]] = []
        for index, block in enumerate(self.blocks, start=1):
            tree = ast.parse(block)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = dotted_name(node.func)
                if name.endswith(".responses.create") or name.endswith(".responses.parse"):
                    calls.append((index, node))

        self.assertGreater(len(calls), 0)
        for index, call in calls:
            with self.subTest(block=index):
                self.assertIn("store", {keyword.arg for keyword in call.keywords})

    def test_file_example_has_expiry_and_final_cleanup(self) -> None:
        block = next(item for item in self.blocks if "client.files.create" in item)
        self.assertIn("expires_after=", block)
        self.assertRegex(block, r"finally:\s*\n\s+client\.files\.delete\(uploaded\.id\)")
        self.assertIn('require_text(response, context="文件分析")', block)

    def test_text_commit_rejects_mixed_text_and_refusal(self) -> None:
        tree = ast.parse(self.blocks[0])
        helpers = ast.Module(
            body=[
                node
                for node in tree.body
                if isinstance(node, ast.FunctionDef)
                and node.name in {"require_completed", "require_text"}
            ],
            type_ignores=[],
        )
        namespace: dict[str, object] = {}
        exec(compile(ast.fix_missing_locations(helpers), "<openai-helpers>", "exec"), namespace)
        require_text = namespace["require_text"]

        valid = SimpleNamespace(
            status="completed",
            output_text="verified text",
            output=[SimpleNamespace(content=[SimpleNamespace(type="output_text")])],
        )
        self.assertEqual(require_text(valid, context="test"), "verified text")

        mixed = SimpleNamespace(
            status="completed",
            output_text="provisional text",
            output=[
                SimpleNamespace(
                    content=[
                        SimpleNamespace(type="output_text"),
                        SimpleNamespace(type="refusal"),
                    ]
                )
            ],
        )
        with self.assertRaisesRegex(RuntimeError, "包含拒答"):
            require_text(mixed, context="test")

    def test_tool_loop_is_bounded_and_fail_closed(self) -> None:
        block = next(item for item in self.blocks if "MAX_TOOL_ROUNDS" in item)
        for required in [
            'require_completed(response, context=f"工具轮次 {_round + 1}")',
            "range(MAX_TOOL_ROUNDS)",
            "seen_call_ids",
            "parse_constant=reject_non_finite",
            'item.name != "get_weather"',
            "allow_nan=False",
            "previous_response_id=response.id",
            'raise RuntimeError("超过工具调用轮数上限")',
        ]:
            with self.subTest(required=required):
                self.assertIn(required, block)

    def test_stream_requires_one_legal_terminal(self) -> None:
        block = next(item for item in self.blocks if "terminal_event" in item)
        for event_type in [
            "response.completed",
            "response.failed",
            "response.incomplete",
            "response.refusal.delta",
            "response.refusal.done",
            '"error"',
        ]:
            with self.subTest(event_type=event_type):
                self.assertIn(event_type, block)
        self.assertIn('terminal_event != "response.completed"', block)
        self.assertIn('committed_text = "".join(fragments)', block)


if __name__ == "__main__":
    unittest.main()
