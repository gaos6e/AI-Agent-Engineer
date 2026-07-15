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
    "refund": "退款申请须在订单完成后 7 天内提交，并由订单所有者发起。",
    "privacy": "不得把凭据、支付信息或未授权客户数据发送给模型。",
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
        raise ValueError("expression 必须是非空字符串")
    if len(expression) > MAX_EXPRESSION_CHARACTERS:
        raise ValueError("表达式过长")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("表达式语法无效") from exc
    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        raise ValueError("表达式节点过多")
    if _depth(tree) > MAX_AST_DEPTH:
        raise ValueError("表达式嵌套过深")

    def visit(node: ast.AST) -> float | int:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            value = node.value
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("常量必须是有限数")
            return value
        if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPERATORS:
            left = visit(node.left)
            right = visit(node.right)
            try:
                result = BINARY_OPERATORS[type(node.op)](left, right)
            except ZeroDivisionError as exc:
                raise ValueError("不能除以零") from exc
            return _bounded_number(result)
        if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPERATORS:
            return _bounded_number(UNARY_OPERATORS[type(node.op)](visit(node.operand)))
        raise ValueError(f"不允许的语法：{type(node).__name__}")

    return _bounded_number(visit(tree))


def _bounded_number(value: float | int) -> float | int:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("结果不是有限数")
    if abs(value) > MAX_ABSOLUTE_RESULT:
        raise ValueError("结果超出示例工具范围")
    return value


def lookup_policy(topic: str) -> dict[str, str]:
    """Return a deterministic local policy excerpt with a source identifier."""
    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("topic 必须是非空字符串")
    normalized = topic.strip().lower()
    if normalized not in POLICIES:
        raise ValueError("未知政策主题；可用主题为 refund、privacy")
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
            return {"type": "final", "content": f"工具未执行：{last['error_code']}。"}
        if last["name"] == "calculator":
            return {"type": "final", "content": f"计算结果是 {last['content']}。"}
        return {
            "type": "final",
            "content": f"查询结果：{last['content']['text']}（来源 {last['content']['source_id']}）",
        }

    text = str(last.get("content", ""))
    calculation = re.fullmatch(r"\s*计算\s+(.+?)\s*", text)
    if calculation:
        expression = calculation.group(1)
        return {
            "type": "tool_call",
            "id": stable_call_id("calculator", expression),
            "name": "calculator",
            "arguments": {"expression": expression},
        }
    policy = re.fullmatch(r"\s*查询政策\s+(refund|privacy)\s*", text, flags=re.IGNORECASE)
    if policy:
        topic = policy.group(1).lower()
        return {
            "type": "tool_call",
            "id": stable_call_id("lookup_policy", topic),
            "name": "lookup_policy",
            "arguments": {"topic": topic},
        }
    return {"type": "final", "content": "该请求无需调用离线白名单工具。"}


def validate_model_response(response: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise ContractError("模型响应必须是对象")
    response_type = response.get("type")
    if response_type == "final":
        if set(response) != {"type", "content"}:
            raise ContractError("final 响应字段不匹配")
        if not isinstance(response["content"], str) or not response["content"].strip():
            raise ContractError("final content 必须是非空字符串")
        return response
    if response_type == "tool_call":
        if set(response) != {"type", "id", "name", "arguments"}:
            raise ContractError("tool_call 响应字段不匹配")
        if not isinstance(response["id"], str) or not TOOL_CALL_ID_PATTERN.fullmatch(response["id"]):
            raise ContractError("tool_call id 格式无效")
        if not isinstance(response["name"], str) or not response["name"]:
            raise ContractError("tool_call name 必须是非空字符串")
        if not isinstance(response["arguments"], dict):
            raise ContractError("tool_call arguments 必须是对象")
        return response
    raise ContractError("模型响应 type 必须是 final 或 tool_call")


def execute_tool(call: dict[str, Any], tools: dict[str, ToolSpec] | None = None) -> dict[str, Any]:
    """Validate a tool request and return a call-ID-bound observation."""
    call = validate_model_response(call)
    if call["type"] != "tool_call":
        raise ContractError("执行器只接受 tool_call")
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
        raise ContractError("工具消息必须是对象")
    required = {"role", "tool_call_id", "name", "status"}
    if not required <= set(message):
        raise ContractError("工具消息缺少必需字段")
    if message["role"] != "tool":
        raise ContractError("工具消息 role 必须是 tool")
    if message["tool_call_id"] != expected_call["id"]:
        raise ContractError("工具消息与 tool_call_id 不匹配")
    if message["name"] != expected_call["name"]:
        raise ContractError("工具消息与工具名不匹配")
    if message["status"] == "ok":
        if "content" not in message or "error_code" in message:
            raise ContractError("成功工具消息形状无效")
    elif message["status"] == "error":
        if not isinstance(message.get("error_code"), str) or "content" in message:
            raise ContractError("失败工具消息形状无效")
    else:
        raise ContractError("工具消息 status 无效")


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
        raise ValueError("query 必须是非空字符串")
    if max_model_steps < 1 or max_tool_calls < 0:
        raise ValueError("预算必须是非负工具数和正模型步数")
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
            state["answer"] = "工具调用预算已耗尽。"
            state["trace"].append({**trace_event, "tool": response["name"]})
            return state
        call_fingerprint = hashlib.sha256(
            json.dumps(response, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if call_fingerprint in seen_calls:
            state["status"] = "repeated_tool_call"
            state["answer"] = "检测到完全重复的工具调用，已停止。"
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
    state["answer"] = "达到模型步骤上限，未继续执行。"
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
        run_agent("计算 12 * (3 + 2)")["status"] == "done",
        run_agent("计算 12 * (3 + 2)")["messages"][-1]["content"] == 60,
        run_agent("解释工具调用")["tool_calls"] == 0,
        run_agent("计算 __import__('os').getcwd()")["messages"][-1]["status"] == "error",
        run_agent("查询政策 privacy")["messages"][-1]["content"]["source_id"]
        == "offline-policy:privacy:v1",
    ]
    if not all(checks):
        raise RuntimeError("self-test failed")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="计算 2 + 3")
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
