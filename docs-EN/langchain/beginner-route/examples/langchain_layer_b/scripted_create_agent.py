"""Credential-free, version-pinned checks for LangChain's ``create_agent`` loop.

The scripted model deliberately bypasses provider-specific ``bind_tools``
serialization.  This exercise proves the LangChain 1.3.14 harness, tool-node
dispatch, ToolMessage correlation, and configured validation-error behavior.
It does not prove a provider accepts a schema, that a real model selects the
right tool, or that an application has authorization for an external action.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from importlib.metadata import version
import json
import sys
from typing import Any


try:
    from langchain.agents import create_agent
    from langchain_core.language_models.fake_chat_models import (
        FakeMessagesListChatModel,
    )
    from langchain_core.messages import AIMessage, ToolMessage
    from langchain_core.tools import BaseTool, StructuredTool
    from pydantic import BaseModel, Field, StrictInt
except ModuleNotFoundError as exc:  # pragma: no cover - CLI dependency branch
    raise SystemExit(
        "dependency_missing: install langchain_layer_b/requirements.txt"
    ) from exc


EXPECTED_DEPENDENCIES = {
    "langchain": "1.3.14",
    "langchain-core": "1.4.9",
    "langgraph": "1.2.9",
}
MAX_ABSOLUTE_OPERAND = 100
VALID_MODES = frozenset({"success", "unknown_tool", "invalid_arguments"})


class AddArguments(BaseModel):
    """Deliberately small schema so invalid values do not reach the function."""

    a: StrictInt = Field(ge=-MAX_ABSOLUTE_OPERAND, le=MAX_ABSOLUTE_OPERAND)
    b: StrictInt = Field(ge=-MAX_ABSOLUTE_OPERAND, le=MAX_ABSOLUTE_OPERAND)


class ScriptedToolModel(FakeMessagesListChatModel):
    """A test double that feeds prebuilt AI messages to the real agent harness.

    ``FakeMessagesListChatModel`` intentionally leaves ``bind_tools``
    unimplemented.  Returning this model here lets ``create_agent`` run its
    actual graph and ToolNode while making the boundary explicit: a provider's
    schema conversion and network protocol are outside this fixture.
    """

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool],
        **_: Any,
    ) -> "ScriptedToolModel":
        return self


def _scripted_responses(mode: str) -> list[AIMessage]:
    if mode == "success":
        call = {
            "name": "bounded_add",
            "args": {"a": 2, "b": 3},
            "id": "call-add-2-3",
            "type": "tool_call",
        }
        final = "2 + 3 = 5"
    elif mode == "unknown_tool":
        call = {
            "name": "unavailable_tool",
            "args": {},
            "id": "call-unknown-tool",
            "type": "tool_call",
        }
        final = "That tool is unavailable and cannot be executed."
    elif mode == "invalid_arguments":
        call = {
            "name": "bounded_add",
            "args": {"a": "2", "b": 3},
            "id": "call-invalid-arguments",
            "type": "tool_call",
        }
        final = "Arguments do not satisfy the tool contract and cannot be executed."
    else:
        raise ValueError(f"unsupported mode: {mode}")
    return [AIMessage(content="", tool_calls=[call]), AIMessage(content=final)]


def _bounded_add_tool(invocations: list[dict[str, int]]) -> StructuredTool:
    def bounded_add(a: int, b: int) -> str:
        """Add two bounded integers after the schema has accepted them."""

        invocations.append({"a": a, "b": b})
        return str(a + b)

    tool = StructuredTool.from_function(
        func=bounded_add,
        name="bounded_add",
        description="Add two integers in the inclusive range -100 through 100.",
        args_schema=AddArguments,
    )
    # The default ToolNode behavior can re-raise validation errors.  This
    # fixture makes the policy explicit and deterministic so the model receives
    # one bounded error observation instead of an unhandled exception.
    tool.handle_validation_error = "invalid_tool_arguments"
    return tool


def _tool_records(messages: Sequence[Any]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for message in messages:
        if isinstance(message, ToolMessage):
            records.append(
                {
                    "name": str(message.name),
                    "tool_call_id": message.tool_call_id,
                    "status": str(message.status),
                    "content": str(message.content),
                }
            )
    return records


def _verified_dependencies(
    version_lookup: Callable[[str], str] = version,
) -> dict[str, str]:
    actual = {package: version_lookup(package) for package in EXPECTED_DEPENDENCIES}
    mismatches = {
        package: {"expected": expected, "actual": actual[package]}
        for package, expected in EXPECTED_DEPENDENCIES.items()
        if actual[package] != expected
    }
    if mismatches:
        raise RuntimeError(
            "dependency_version_mismatch: "
            + json.dumps(mismatches, ensure_ascii=False, sort_keys=True)
        )
    return actual


def run_case(mode: str = "success") -> dict[str, object]:
    """Run one deterministic tool-call trajectory through real ``create_agent``."""

    if mode not in VALID_MODES:
        raise ValueError(f"mode must be one of {sorted(VALID_MODES)}")
    dependencies = _verified_dependencies()
    invocations: list[dict[str, int]] = []
    agent = create_agent(
        model=ScriptedToolModel(responses=_scripted_responses(mode)),
        tools=[_bounded_add_tool(invocations)],
        system_prompt="Use only registered tools and report their result.",
    )
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Run the scripted case."}]}
    )
    messages = list(result["messages"])
    tool_records = _tool_records(messages)
    if len(tool_records) != 1:
        raise RuntimeError("the scripted trajectory must contain exactly one tool result")
    if not isinstance(messages[-1], AIMessage):
        raise RuntimeError("the scripted trajectory must terminate in an AI message")
    return {
        "status": "completed",
        "mode": mode,
        "dependencies": dependencies,
        "message_types": [type(message).__name__ for message in messages],
        "tool_records": tool_records,
        "tool_invocations": invocations,
        "final_answer": str(messages[-1].content),
        "verification_boundary": (
            "real create_agent and ToolMessage dispatch; scripted model bypasses "
            "provider tool-schema conversion, model quality, authorization, and network"
        ),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=sorted(VALID_MODES), default="success")
    return parser


def main(argv: list[str] | None = None) -> int:
    # JSON is a process contract here, so do not inherit a legacy Windows code
    # page when stdout/stderr are redirected by a test runner or another tool.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = _parser().parse_args(argv)
    try:
        print(json.dumps(run_case(args.mode), ensure_ascii=False, sort_keys=True))
        return 0
    except (RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {"error": type(exc).__name__, "message": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


