"""Offline model-tool loop with strict schemas and bounded execution.

This standard-library project mirrors stable agent-loop responsibilities. It
does not import LangChain, call a model, access a network, or execute writes.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import operator
import re
import sys
from dataclasses import dataclass
from typing import Any, Callable


MAX_EXPRESSION_CHARACTERS = 120
MAX_AST_NODES = 64
MAX_AST_DEPTH = 12
MAX_ABSOLUTE_RESULT = 1_000_000_000_000
TOOL_CALL_ID_PATTERN = re.compile(r"call-[a-f0-9]{12}\Z")
POLICIES = {
    "refund": "Refund requests must be submitted within 7 days after order completion and initiated by the order owner.",
    "privacy": "Do not send credentials, payment data, or unauthorized customer data to the model.",
}

BINARY_OPERATORS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class ContractError(ValueError):
    """Raised when a model or tool message violates the local contract."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    argument_name: str
    handler: Callable[[str], Any]


def _depth(node: ast.AST) -> int:
    children = list(ast.iter_child_nodes(node))
    return 1 if not children else 1 + max(_depth(child) for child in children)


def safe_calculate(expression: str) -> float | int:
    """Evaluate bounded arithmetic without eval, names, calls, or exponentiation."""
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("expression must be a non-empty string")
    if len(expression) > MAX_EXPRESSION_CHARACTERS:
        raise ValueError("expression is too long")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("expression syntax is invalid") from exc
    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        raise ValueError("expression contains too many nodes")
    if _depth(tree) > MAX_AST_DEPTH:
        raise ValueError("expression nesting is too deep")

    def visit(node: ast.AST) -> float | int:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            value = node.value
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("constant must be a finite number")
            return value
        if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPERATORS:
            left = visit(node.left)
            right = visit(node.right)
            try:
                result = BINARY_OPERATORS[type(node.op)](left, right)
            except ZeroDivisionError as exc:
                raise ValueError("division by zero is not allowed") from exc
            return _bounded_number(result)
        if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPERATORS:
            return _bounded_number(UNARY_OPERATORS[type(node.op)](visit(node.operand)))
        raise ValueError(f"syntax is not allowed: {type(node).__name__}")

    return _bounded_number(visit(tree))


def _bounded_number(value: float | int) -> float | int:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("result is not a finite number")
    if abs(value) > MAX_ABSOLUTE_RESULT:
        raise ValueError("result exceeds the example tool limit")
    return value


def lookup_policy(topic: str) -> dict[str, str]:
    """Return a deterministic local policy excerpt with a source identifier."""
    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("topic must be a non-empty string")
    normalized = topic.strip().lower()
    if normalized not in POLICIES:
        raise ValueError("unknown policy topic; available topics: refund, privacy")
    return {
        "topic": normalized,
        "text": POLICIES[normalized],
        "source_id": f"offline-policy:{normalized}:v1",
    }


TOOLS: dict[str, ToolSpec] = {
    "calculator": ToolSpec("calculator", "expression", safe_calculate),
    "lookup_policy": ToolSpec("lookup_policy", "topic", lookup_policy),
}


def stable_call_id(name: str, argument: str) -> str:
    digest = hashlib.sha256(f"{name}\0{argument}".encode("utf-8")).hexdigest()[:12]
    return f"call-{digest}"


def model_stub(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Return one deterministic tool request or a final response."""
    last = messages[-1]
    if last.get("role") == "tool":
        if last["status"] == "error":
            return {"type": "final", "content": f"Tool was not executed: {last['error_code']}."}
        if last["name"] == "calculator":
            return {"type": "final", "content": f"The calculation result is {last['content']}."}
        return {
            "type": "final",
            "content": f"Policy result: {last['content']['text']} (source {last['content']['source_id']})",
        }

    text = str(last.get("content", ""))
    calculation = re.fullmatch(r"\s*calculate\s+(.+?)\s*", text)
    if calculation:
        expression = calculation.group(1)
        return {
            "type": "tool_call",
            "id": stable_call_id("calculator", expression),
            "name": "calculator",
            "arguments": {"expression": expression},
        }
    policy = re.fullmatch(r"\s*look up policy\s+(refund|privacy)\s*", text, flags=re.IGNORECASE)
    if policy:
        topic = policy.group(1).lower()
        return {
            "type": "tool_call",
            "id": stable_call_id("lookup_policy", topic),
            "name": "lookup_policy",
            "arguments": {"topic": topic},
        }
    return {"type": "final", "content": "This request does not need an offline allowlisted tool."}


def validate_model_response(response: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise ContractError("model response must be an object")
    response_type = response.get("type")
    if response_type == "final":
        if set(response) != {"type", "content"}:
            raise ContractError("final response fields do not match")
        if not isinstance(response["content"], str) or not response["content"].strip():
            raise ContractError("final content must be a non-empty string")
        return response
    if response_type == "tool_call":
        if set(response) != {"type", "id", "name", "arguments"}:
            raise ContractError("tool_call response fields do not match")
        if not isinstance(response["id"], str) or not TOOL_CALL_ID_PATTERN.fullmatch(response["id"]):
            raise ContractError("tool_call id format is invalid")
        if not isinstance(response["name"], str) or not response["name"]:
            raise ContractError("tool_call name must be a non-empty string")
        if not isinstance(response["arguments"], dict):
            raise ContractError("tool_call arguments must be an object")
        return response
    raise ContractError("model response type must be final or tool_call")


def execute_tool(call: dict[str, Any], tools: dict[str, ToolSpec] | None = None) -> dict[str, Any]:
    """Validate a tool request and return a call-ID-bound observation."""
    call = validate_model_response(call)
    if call["type"] != "tool_call":
        raise ContractError("executor accepts only tool_call")
    registry = TOOLS if tools is None else tools
    name = call["name"]
    if name not in registry:
        return _tool_error(call, "TOOL_NOT_ALLOWED")
    spec = registry[name]
    expected = {spec.argument_name}
    if set(call["arguments"]) != expected:
        return _tool_error(call, "INVALID_ARGUMENT_SHAPE")
    argument = call["arguments"][spec.argument_name]
    if not isinstance(argument, str):
        return _tool_error(call, "INVALID_ARGUMENT_TYPE")
    try:
        result = spec.handler(argument)
    except (TypeError, ValueError) as exc:
        return _tool_error(call, "TOOL_INPUT_REJECTED", detail=str(exc))
    return {
        "role": "tool",
        "tool_call_id": call["id"],
        "name": name,
        "status": "ok",
        "content": result,
    }


def _tool_error(call: dict[str, Any], code: str, *, detail: str | None = None) -> dict[str, Any]:
    message = {
        "role": "tool",
        "tool_call_id": call["id"],
        "name": str(call["name"]),
        "status": "error",
        "error_code": code,
    }
    if detail:
        message["detail"] = detail[:160]
    return message


def validate_tool_message(message: Any, expected_call: dict[str, Any]) -> None:
    if not isinstance(message, dict):
        raise ContractError("tool message must be an object")
    required = {"role", "tool_call_id", "name", "status"}
    if not required <= set(message):
        raise ContractError("tool message is missing required fields")
    if message["role"] != "tool":
        raise ContractError("tool message role must be tool")
    if message["tool_call_id"] != expected_call["id"]:
        raise ContractError("tool message does not match tool_call_id")
    if message["name"] != expected_call["name"]:
        raise ContractError("tool message does not match the tool name")
    if message["status"] == "ok":
        if "content" not in message or "error_code" in message:
            raise ContractError("successful tool-message shape is invalid")
    elif message["status"] == "error":
        if not isinstance(message.get("error_code"), str) or "content" in message:
            raise ContractError("failed tool-message shape is invalid")
    else:
        raise ContractError("tool message status is invalid")


def run_agent(
    query: str,
    *,
    max_model_steps: int = 4,
    max_tool_calls: int = 2,
    model: Callable[[list[dict[str, Any]]], dict[str, Any]] = model_stub,
    tools: dict[str, ToolSpec] | None = None,
) -> dict[str, Any]:
    """Run a bounded loop and retain a machine-checkable trace."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if max_model_steps < 1 or max_tool_calls < 0:
        raise ValueError("budget must specify a nonnegative tool count and positive model steps")
    state: dict[str, Any] = {
        "messages": [{"role": "user", "content": query}],
        "trace": [],
        "tool_calls": 0,
        "status": "running",
    }
    seen_calls: set[str] = set()
    for step in range(1, max_model_steps + 1):
        response = validate_model_response(model(state["messages"]))
        trace_event = {"step": step, "response_type": response["type"]}
        if response["type"] == "final":
            state["answer"] = response["content"]
            state["status"] = "done"
            state["trace"].append(trace_event)
            return state
        if state["tool_calls"] >= max_tool_calls:
            state["status"] = "tool_budget_exhausted"
            state["answer"] = "Tool-call budget is exhausted."
            state["trace"].append({**trace_event, "tool": response["name"]})
            return state
        call_fingerprint = hashlib.sha256(
            json.dumps(response, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if call_fingerprint in seen_calls:
            state["status"] = "repeated_tool_call"
            state["answer"] = "An identical tool call was detected; stopped."
            state["trace"].append({**trace_event, "tool": response["name"]})
            return state
        seen_calls.add(call_fingerprint)
        tool_message = execute_tool(response, tools)
        validate_tool_message(tool_message, response)
        state["tool_calls"] += 1
        state["messages"].append(tool_message)
        state["trace"].append(
            {
                **trace_event,
                "tool": response["name"],
                "tool_call_id": response["id"],
                "tool_status": tool_message["status"],
            }
        )
    state["status"] = "model_step_limit"
    state["answer"] = "Model step limit reached; execution did not continue."
    return state


def public_result(state: dict[str, Any]) -> dict[str, Any]:
    """Exclude raw user/tool content from the default CLI result."""
    return {
        "status": state["status"],
        "answer": state["answer"],
        "tool_calls": state["tool_calls"],
        "trace": state["trace"],
    }


def self_test() -> None:
    checks = [
        run_agent("calculate 12 * (3 + 2)")["status"] == "done",
        run_agent("calculate 12 * (3 + 2)")["messages"][-1]["content"] == 60,
        run_agent("explain tool calling")["tool_calls"] == 0,
        run_agent("calculate __import__('os').getcwd()")["messages"][-1]["status"] == "error",
        run_agent("look up policy privacy")["messages"][-1]["content"]["source_id"]
        == "offline-policy:privacy:v1",
    ]
    if not all(checks):
        raise RuntimeError("self-test failed")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="calculate 2 + 3")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.self_test:
            self_test()
            print(json.dumps({"status": "ok", "checks": 5}, ensure_ascii=False))
            return 0
        print(json.dumps(public_result(run_agent(args.query)), ensure_ascii=False, indent=2))
        return 0
    except (ContractError, ValueError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

