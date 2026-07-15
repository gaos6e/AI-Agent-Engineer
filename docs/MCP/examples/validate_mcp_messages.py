"""Validate a deliberately small, offline MCP teaching profile.

This module is not an official MCP conformance suite.  It turns the course's
most important protocol invariants into deterministic checks without a network,
an SDK, or credentials.  The profile is intentionally stricter than JSON-RPC
where strictness makes mistakes easier for beginners to see.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


PROTOCOL_VERSION = "2025-11-25"
CLIENT_TO_SERVER = "client_to_server"
SERVER_TO_CLIENT = "server_to_client"
DIRECTIONS = {CLIENT_TO_SERVER, SERVER_TO_CLIENT}
TOOL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
SENSITIVE_FORM_NAMES = {
    "password",
    "passcode",
    "api_key",
    "apikey",
    "access_token",
    "token",
    "secret",
    "credit_card",
    "cvv",
}


class ValidationError(ValueError):
    """A protocol or teaching-profile invariant was violated."""


def require(condition: bool, message: str) -> None:
    """Raise a readable validation error instead of relying on assert."""
    if not condition:
        raise ValidationError(message)


def _reject_constant(value: str) -> None:
    raise ValidationError(f"non-finite JSON number is forbidden: {value}")


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads_strict(text: str) -> Any:
    """Parse strict JSON: duplicate keys and NaN/Infinity are rejected."""
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON at line {exc.lineno}: {exc.msg}") from exc


def load_json(path: Path) -> dict[str, Any]:
    data = loads_strict(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), "fixture root must be an object")
    return data


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool))


def _is_request_id(value: Any) -> bool:
    return isinstance(value, str) or _is_integer(value)


def _id_key(value: Any) -> tuple[str, Any]:
    require(_is_request_id(value), "id must be a string or integer, not bool/null")
    return (type(value).__name__, value)


def _opposite(direction: str) -> str:
    require(direction in DIRECTIONS, f"unknown direction: {direction}")
    return SERVER_TO_CLIENT if direction == CLIENT_TO_SERVER else CLIENT_TO_SERVER


def _require_exact_keys(
    value: dict[str, Any], required: set[str], optional: set[str], label: str
) -> None:
    missing = required - set(value)
    unknown = set(value) - required - optional
    require(not missing, f"{label} missing keys: {sorted(missing)}")
    require(not unknown, f"{label} has unknown keys: {sorted(unknown)}")


def classify_message(message: dict[str, Any]) -> str:
    """Return request, notification, or response after strict envelope checks."""
    require(isinstance(message, dict), "JSON-RPC message must be an object")
    require(message.get("jsonrpc") == "2.0", "jsonrpc must be '2.0'")

    if "method" in message:
        require(isinstance(message["method"], str) and message["method"], "method must be a non-empty string")
        require("result" not in message and "error" not in message, "request/notification cannot contain result or error")
        if "params" in message:
            require(isinstance(message["params"], dict), "params must be an object in this teaching profile")
        if "id" in message:
            require(not message["method"].startswith("notifications/"), "notification method must not contain id")
            _require_exact_keys(message, {"jsonrpc", "id", "method"}, {"params"}, "request")
            _id_key(message["id"])
            return "request"
        _require_exact_keys(message, {"jsonrpc", "method"}, {"params"}, "notification")
        return "notification"

    require("id" in message, "response must contain id")
    _id_key(message["id"])
    has_result = "result" in message
    has_error = "error" in message
    require(has_result != has_error, "response must contain exactly one of result or error")
    _require_exact_keys(
        message,
        {"jsonrpc", "id", "result" if has_result else "error"},
        set(),
        "response",
    )
    if has_error:
        validate_error(message["error"])
    return "response"


def validate_error(error: Any) -> None:
    require(isinstance(error, dict), "error must be an object")
    _require_exact_keys(error, {"code", "message"}, {"data"}, "error")
    require(_is_integer(error["code"]), "error.code must be an integer")
    require(isinstance(error["message"], str) and error["message"], "error.message must be a non-empty string")


def _validate_schema_shape(schema: Any, label: str) -> None:
    require(isinstance(schema, dict), f"{label} must be a JSON Schema object")
    require(schema.get("type") == "object", f"{label}.type must be object")
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    require(isinstance(properties, dict), f"{label}.properties must be an object")
    require(isinstance(required, list), f"{label}.required must be an array")
    require(all(isinstance(key, str) for key in required), f"{label}.required entries must be strings")
    require(len(required) == len(set(required)), f"{label}.required contains duplicates")
    require(all(key in properties for key in required), f"{label}.required references an unknown property")
    if "additionalProperties" in schema:
        require(isinstance(schema["additionalProperties"], bool), f"{label}.additionalProperties must be boolean")


def validate_value(rule: dict[str, Any], value: Any, path: str = "$") -> None:
    """Validate the small JSON Schema subset used by the course fixture."""
    require(isinstance(rule, dict), f"schema at {path} must be an object")
    expected = rule.get("type")
    if expected == "object":
        require(isinstance(value, dict), f"{path} must be an object")
        properties = rule.get("properties", {})
        required = rule.get("required", [])
        require(isinstance(properties, dict), f"properties at {path} must be an object")
        require(isinstance(required, list), f"required at {path} must be an array")
        for key in required:
            require(key in value, f"missing required value: {path}.{key}")
        if rule.get("additionalProperties") is False:
            unknown = set(value) - set(properties)
            require(not unknown, f"unknown values at {path}: {sorted(unknown)}")
        for key, item in value.items():
            if key in properties:
                validate_value(properties[key], item, f"{path}.{key}")
    elif expected == "array":
        require(isinstance(value, list), f"{path} must be an array")
        if "minItems" in rule:
            require(len(value) >= rule["minItems"], f"{path} has too few items")
        if "maxItems" in rule:
            require(len(value) <= rule["maxItems"], f"{path} has too many items")
        if "items" in rule:
            for index, item in enumerate(value):
                validate_value(rule["items"], item, f"{path}[{index}]")
    elif expected == "string":
        require(isinstance(value, str), f"{path} must be a string")
        if "minLength" in rule:
            require(len(value) >= rule["minLength"], f"{path} is shorter than minLength")
        if "maxLength" in rule:
            require(len(value) <= rule["maxLength"], f"{path} is longer than maxLength")
    elif expected == "integer":
        require(_is_integer(value), f"{path} must be an integer")
    elif expected == "number":
        require(_is_number(value), f"{path} must be a number")
    elif expected == "boolean":
        require(isinstance(value, bool), f"{path} must be a boolean")
    elif expected is not None:
        raise ValidationError(f"unsupported schema type at {path}: {expected}")

    if "enum" in rule:
        require(value in rule["enum"], f"{path} must be one of {rule['enum']}")
    if _is_number(value):
        if "minimum" in rule:
            require(value >= rule["minimum"], f"{path} is below minimum")
        if "maximum" in rule:
            require(value <= rule["maximum"], f"{path} is above maximum")


def validate_tool_descriptor(tool: Any) -> None:
    require(isinstance(tool, dict), "tool descriptor must be an object")
    _require_exact_keys(
        tool,
        {"name", "description", "inputSchema"},
        {"title", "icons", "outputSchema", "annotations", "execution"},
        "tool descriptor",
    )
    require(isinstance(tool["name"], str) and TOOL_NAME_PATTERN.fullmatch(tool["name"]) is not None, "tool name must use 1-128 ASCII letters, digits, dot, underscore, or hyphen")
    require(isinstance(tool["description"], str) and tool["description"], "tool description must be non-empty")
    _validate_schema_shape(tool["inputSchema"], "inputSchema")
    if "outputSchema" in tool:
        _validate_schema_shape(tool["outputSchema"], "outputSchema")
    if "execution" in tool:
        execution = tool["execution"]
        require(isinstance(execution, dict), "tool.execution must be an object")
        _require_exact_keys(execution, set(), {"taskSupport"}, "tool.execution")
        if "taskSupport" in execution:
            require(execution["taskSupport"] in {"forbidden", "optional", "required"}, "invalid tool taskSupport")


def _validate_info(info: Any, label: str) -> None:
    require(isinstance(info, dict), f"{label} must be an object")
    _require_exact_keys(
        info,
        {"name", "version"},
        {"title", "description", "icons", "websiteUrl"},
        label,
    )
    require(isinstance(info["name"], str) and info["name"], f"{label}.name required")
    require(isinstance(info["version"], str) and info["version"], f"{label}.version required")


def _has_capability(capabilities: dict[str, Any], path: Iterable[str]) -> bool:
    current: Any = capabilities
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]
    return isinstance(current, dict)


@dataclass(frozen=True)
class PendingRequest:
    direction: str
    method: str
    metadata: dict[str, Any]


class McpSessionValidator:
    """Stateful validator for a small but bilateral MCP session."""

    def __init__(self, protocol_version: str, tool: dict[str, Any]) -> None:
        require(protocol_version == PROTOCOL_VERSION, f"teaching fixture expects {PROTOCOL_VERSION}")
        validate_tool_descriptor(tool)
        self.protocol_version = protocol_version
        self.tool = copy.deepcopy(tool)
        self.client_capabilities: dict[str, Any] = {}
        self.server_capabilities: dict[str, Any] = {}
        self.state = "new"
        self.pending: dict[tuple[str, tuple[str, Any]], PendingRequest] = {}

    def process(self, direction: str, message: dict[str, Any]) -> None:
        require(direction in DIRECTIONS, f"unknown direction: {direction}")
        kind = classify_message(message)
        if self.state != "ready":
            self._process_lifecycle(direction, kind, message)
            return

        if kind == "request":
            self._process_request(direction, message)
        elif kind == "notification":
            self._process_notification(direction, message)
        else:
            self._process_response(direction, message)

    def _process_lifecycle(self, direction: str, kind: str, message: dict[str, Any]) -> None:
        if self.state == "new":
            require(direction == CLIENT_TO_SERVER, "client must initiate initialization")
            require(kind == "request" and message["method"] == "initialize", "initialize request must be the first interaction")
            params = message.get("params")
            require(isinstance(params, dict), "initialize.params must be an object")
            _require_exact_keys(params, {"protocolVersion", "capabilities", "clientInfo"}, set(), "initialize.params")
            require(params["protocolVersion"] == self.protocol_version, "unsupported client protocol version")
            require(isinstance(params["capabilities"], dict), "client capabilities must be an object")
            _validate_info(params["clientInfo"], "clientInfo")
            self.client_capabilities = copy.deepcopy(params["capabilities"])
            self._remember_request(direction, message, {"phase": "initialize"})
            self.state = "waiting_for_initialize_response"
            return

        if self.state == "waiting_for_initialize_response":
            require(direction == SERVER_TO_CLIENT and kind == "response", "server must answer initialize before normal operation")
            pending = self._take_pending_response(direction, message)
            require(pending.method == "initialize", "response does not match initialize")
            require("result" in message, "initialize failed; this transcript cannot enter operation")
            result = message["result"]
            require(isinstance(result, dict), "initialize result must be an object")
            _require_exact_keys(result, {"protocolVersion", "capabilities", "serverInfo"}, {"instructions"}, "initialize result")
            require(result["protocolVersion"] == self.protocol_version, "client does not support server-selected version")
            require(isinstance(result["capabilities"], dict), "server capabilities must be an object")
            _validate_info(result["serverInfo"], "serverInfo")
            self.server_capabilities = copy.deepcopy(result["capabilities"])
            self.state = "waiting_for_initialized_notification"
            return

        require(self.state == "waiting_for_initialized_notification", "unknown lifecycle state")
        require(direction == CLIENT_TO_SERVER, "initialized notification must come from client")
        require(kind == "notification" and message["method"] == "notifications/initialized", "client must send notifications/initialized")
        require("params" not in message or message["params"] == {}, "initialized notification must not carry data in this profile")
        self.state = "ready"

    def _remember_request(self, direction: str, message: dict[str, Any], metadata: dict[str, Any]) -> None:
        key = (direction, _id_key(message["id"]))
        require(key not in self.pending, f"duplicate outstanding request id for {direction}: {message['id']!r}")
        self.pending[key] = PendingRequest(direction, message["method"], metadata)

    def _take_pending_response(self, direction: str, message: dict[str, Any]) -> PendingRequest:
        key = (_opposite(direction), _id_key(message["id"]))
        require(key in self.pending, f"response id has no matching outstanding request: {message['id']!r}")
        return self.pending.pop(key)

    def _capabilities_for_receiver(self, direction: str) -> tuple[str, dict[str, Any]]:
        if direction == CLIENT_TO_SERVER:
            return "server", self.server_capabilities
        return "client", self.client_capabilities

    def _require_receiver_capability(self, direction: str, path: tuple[str, ...]) -> None:
        owner, capabilities = self._capabilities_for_receiver(direction)
        require(_has_capability(capabilities, path), f"{owner} did not declare capability: {'.'.join(path)}")

    def _process_request(self, direction: str, message: dict[str, Any]) -> None:
        method = message["method"]
        params = message.get("params", {})
        metadata: dict[str, Any] = {}

        if direction == CLIENT_TO_SERVER and method in {"tools/list", "tools/call"}:
            self._require_receiver_capability(direction, ("tools",))
        elif direction == CLIENT_TO_SERVER and method.startswith("resources/"):
            self._require_receiver_capability(direction, ("resources",))
        elif direction == CLIENT_TO_SERVER and method.startswith("prompts/"):
            self._require_receiver_capability(direction, ("prompts",))
        elif direction == CLIENT_TO_SERVER and method == "logging/setLevel":
            self._require_receiver_capability(direction, ("logging",))
        elif direction == CLIENT_TO_SERVER and method == "completion/complete":
            self._require_receiver_capability(direction, ("completions",))
        elif direction == SERVER_TO_CLIENT and method == "roots/list":
            self._require_receiver_capability(direction, ("roots",))
        elif direction == SERVER_TO_CLIENT and method == "sampling/createMessage":
            self._require_receiver_capability(direction, ("sampling",))
        elif direction == SERVER_TO_CLIENT and method == "elicitation/create":
            self._require_receiver_capability(direction, ("elicitation",))
        elif method.startswith("tasks/"):
            self._validate_task_operation_capability(direction, method)
        elif method != "ping":
            raise ValidationError(f"unsupported method in teaching profile or wrong direction: {method}")

        if method == "tools/call":
            metadata = self._validate_tool_call(direction, params)
        elif method == "roots/list":
            require(params == {}, "roots/list takes no parameters in this profile")
        elif method == "sampling/createMessage":
            self._validate_sampling_request(params)
            self._validate_task_augmentation(direction, method, params)
        elif method == "elicitation/create":
            metadata = self._validate_elicitation_request(params)
            self._validate_task_augmentation(direction, method, params)
        elif method == "tasks/list":
            require(set(params) <= {"cursor"}, "tasks/list only accepts an optional cursor in this profile")
        elif method in {"tasks/get", "tasks/result", "tasks/cancel"}:
            _require_exact_keys(params, {"taskId"}, set(), f"{method}.params")
            require(isinstance(params["taskId"], str) and params["taskId"], f"{method}.taskId required")

        self._remember_request(direction, message, metadata)

    def _validate_task_operation_capability(self, direction: str, method: str) -> None:
        if method == "tasks/list":
            self._require_receiver_capability(direction, ("tasks", "list"))
        elif method == "tasks/cancel":
            self._require_receiver_capability(direction, ("tasks", "cancel"))
        elif method in {"tasks/get", "tasks/result"}:
            self._require_receiver_capability(direction, ("tasks",))
        else:
            raise ValidationError(f"unsupported task method: {method}")

    def _validate_task_augmentation(self, direction: str, method: str, params: dict[str, Any]) -> None:
        task_requested = "task" in params
        path_by_method = {
            "tools/call": ("tasks", "requests", "tools", "call"),
            "sampling/createMessage": ("tasks", "requests", "sampling", "createMessage"),
            "elicitation/create": ("tasks", "requests", "elicitation", "create"),
        }
        if task_requested:
            task = params["task"]
            require(isinstance(task, dict), "task parameters must be an object")
            _require_exact_keys(task, set(), {"ttl"}, "task")
            if "ttl" in task:
                require(_is_number(task["ttl"]) and task["ttl"] > 0, "task.ttl must be a positive number")
            self._require_receiver_capability(direction, path_by_method[method])

    def _validate_tool_call(self, direction: str, params: dict[str, Any]) -> dict[str, Any]:
        _require_exact_keys(params, {"name"}, {"arguments", "task", "_meta"}, "tools/call.params")
        require(params["name"] == self.tool["name"], f"unknown tool: {params['name']}")
        arguments = params.get("arguments", {})
        require(isinstance(arguments, dict), "tool arguments must be an object")
        validate_value(self.tool["inputSchema"], arguments, "$.arguments")
        self._validate_task_augmentation(direction, "tools/call", params)
        support = self.tool.get("execution", {}).get("taskSupport", "forbidden")
        if "task" in params:
            require(support in {"optional", "required"}, "tool forbids task augmentation")
        elif support == "required":
            raise ValidationError("tool requires task augmentation")
        return {"tool": params["name"], "task_augmented": "task" in params}

    def _validate_sampling_request(self, params: dict[str, Any]) -> None:
        require(isinstance(params.get("messages"), list) and params["messages"], "sampling messages must be a non-empty array")
        require(_is_integer(params.get("maxTokens")) and params["maxTokens"] > 0, "sampling maxTokens must be a positive integer")
        if "tools" in params:
            require(isinstance(params["tools"], list) and params["tools"], "sampling tools must be a non-empty array")
            self._require_receiver_capability(SERVER_TO_CLIENT, ("sampling", "tools"))
        include_context = params.get("includeContext", "none")
        require(include_context in {"none", "thisServer", "allServers"}, "invalid includeContext")
        if include_context != "none":
            self._require_receiver_capability(SERVER_TO_CLIENT, ("sampling", "context"))

    def _validate_elicitation_request(self, params: dict[str, Any]) -> dict[str, Any]:
        require(isinstance(params.get("message"), str) and params["message"], "elicitation message required")
        mode = params.get("mode", "form")
        require(mode in {"form", "url"}, "elicitation mode must be form or url")
        elicitation_capability = self.client_capabilities.get("elicitation")
        require(isinstance(elicitation_capability, dict), "client elicitation capability must be an object")
        if mode == "form":
            require(not elicitation_capability or "form" in elicitation_capability, "client did not declare elicitation.form")
            _require_exact_keys(params, {"message", "requestedSchema"}, {"mode", "task", "_meta"}, "form elicitation params")
            schema = params["requestedSchema"]
            _validate_schema_shape(schema, "requestedSchema")
            normalized = {key.lower().replace("-", "_") for key in schema.get("properties", {})}
            forbidden = normalized & SENSITIVE_FORM_NAMES
            require(not forbidden, f"form elicitation must not request secrets: {sorted(forbidden)}")
        else:
            require("url" in elicitation_capability, "client did not declare elicitation.url")
            _require_exact_keys(params, {"mode", "message", "url", "elicitationId"}, {"task", "_meta"}, "URL elicitation params")
            parsed = urlparse(params["url"])
            require(parsed.scheme == "https" and bool(parsed.netloc), "URL elicitation requires an absolute HTTPS URL in this profile")
            require(isinstance(params["elicitationId"], str) and params["elicitationId"], "elicitationId required")
        return {"elicitation_mode": mode}

    def _process_notification(self, direction: str, message: dict[str, Any]) -> None:
        method = message["method"]
        if direction == SERVER_TO_CLIENT and method == "notifications/tools/list_changed":
            tools = self.server_capabilities.get("tools")
            require(isinstance(tools, dict) and tools.get("listChanged") is True, "server did not declare tools.listChanged")
        elif direction == CLIENT_TO_SERVER and method == "notifications/roots/list_changed":
            roots = self.client_capabilities.get("roots")
            require(isinstance(roots, dict) and roots.get("listChanged") is True, "client did not declare roots.listChanged")
        elif direction == SERVER_TO_CLIENT and method == "notifications/elicitation/complete":
            require(_has_capability(self.client_capabilities, ("elicitation", "url")), "client did not declare elicitation.url")
            params = message.get("params", {})
            _require_exact_keys(params, {"elicitationId"}, set(), "elicitation complete params")
        elif method in {"notifications/progress", "notifications/cancelled", "notifications/tasks/status"}:
            require(isinstance(message.get("params"), dict), f"{method} requires params")
        else:
            raise ValidationError(f"unsupported notification in teaching profile or wrong direction: {method}")

    def _process_response(self, direction: str, message: dict[str, Any]) -> None:
        pending = self._take_pending_response(direction, message)
        if "error" in message:
            return
        result = message["result"]
        if pending.method == "tools/call":
            if pending.metadata.get("task_augmented"):
                self._validate_create_task_result(result)
            else:
                self._validate_tool_result(result)
        elif pending.method == "roots/list":
            self._validate_roots_result(result)
        elif pending.method == "elicitation/create":
            self._validate_elicitation_result(result, pending.metadata["elicitation_mode"])
        elif pending.method == "tasks/list":
            require(isinstance(result, dict) and isinstance(result.get("tasks"), list), "tasks/list result must contain tasks array")

    def _validate_tool_result(self, result: Any) -> None:
        require(isinstance(result, dict), "tool result must be an object")
        require(isinstance(result.get("content"), list) and result["content"], "tool result.content must be a non-empty array")
        for index, item in enumerate(result["content"]):
            require(isinstance(item, dict) and isinstance(item.get("type"), str), f"content[{index}] needs a type")
            if item["type"] == "text":
                require(isinstance(item.get("text"), str), f"content[{index}].text must be a string")
        if "isError" in result:
            require(isinstance(result["isError"], bool), "tool result.isError must be boolean")
        if "outputSchema" in self.tool and result.get("isError") is not True:
            require("structuredContent" in result, "successful tool result must include structuredContent when outputSchema exists")
            validate_value(self.tool["outputSchema"], result["structuredContent"], "$.structuredContent")

    def _validate_create_task_result(self, result: Any) -> None:
        require(isinstance(result, dict) and isinstance(result.get("task"), dict), "task-augmented response must contain task")
        task = result["task"]
        for key in ("taskId", "status", "createdAt", "lastUpdatedAt"):
            require(isinstance(task.get(key), str) and task[key], f"task.{key} required")
        require(task["status"] in {"working", "input_required", "completed", "failed", "cancelled"}, "invalid task status")

    def _validate_roots_result(self, result: Any) -> None:
        require(isinstance(result, dict) and isinstance(result.get("roots"), list), "roots/list result must contain roots array")
        for index, root in enumerate(result["roots"]):
            require(isinstance(root, dict), f"root[{index}] must be an object")
            uri = root.get("uri")
            require(isinstance(uri, str) and uri.startswith("file://"), f"root[{index}].uri must be a file URI")

    def _validate_elicitation_result(self, result: Any, mode: str) -> None:
        require(isinstance(result, dict), "elicitation result must be an object")
        action = result.get("action")
        require(action in {"accept", "decline", "cancel"}, "invalid elicitation action")
        if mode == "url":
            require("content" not in result, "URL elicitation result must not expose secret content")
        elif action == "accept":
            require(isinstance(result.get("content"), dict), "accepted form elicitation needs content")


def build_initialize_messages(
    protocol_version: str,
    client: dict[str, Any],
    server: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": protocol_version,
            "capabilities": copy.deepcopy(client["capabilities"]),
            "clientInfo": copy.deepcopy(client["info"]),
        },
    }
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": protocol_version,
            "capabilities": copy.deepcopy(server["capabilities"]),
            "serverInfo": copy.deepcopy(server["info"]),
        },
    }
    initialized = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    return request, response, initialized


def prepare_case(fixture: dict[str, Any], case: dict[str, Any]) -> tuple[McpSessionValidator, list[dict[str, Any]]]:
    client = copy.deepcopy(fixture["client"])
    server = copy.deepcopy(fixture["server"])
    if "client_capabilities" in case:
        client["capabilities"] = copy.deepcopy(case["client_capabilities"])
    if "server_capabilities" in case:
        server["capabilities"] = copy.deepcopy(case["server_capabilities"])
    validator = McpSessionValidator(fixture["protocol_version"], fixture["tool"])
    request, response, initialized = build_initialize_messages(fixture["protocol_version"], client, server)
    setup = case.get("setup", "ready")
    if setup == "ready":
        validator.process(CLIENT_TO_SERVER, request)
        validator.process(SERVER_TO_CLIENT, response)
        validator.process(CLIENT_TO_SERVER, initialized)
    elif setup == "initialize_request_only":
        validator.process(CLIENT_TO_SERVER, request)
    elif setup != "none":
        raise ValidationError(f"unknown case setup: {setup}")
    steps = case.get("steps")
    require(isinstance(steps, list), f"case {case.get('name')} steps must be an array")
    return validator, steps


def execute_case(fixture: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(case.get("name"), str) and case["name"], "case name required")
    expected = case.get("expect")
    require(expected in {"pass", "fail"}, f"case {case['name']} expect must be pass or fail")
    try:
        validator, steps = prepare_case(fixture, case)
        for step in steps:
            require(isinstance(step, dict), f"case {case['name']} step must be an object")
            _require_exact_keys(step, {"direction", "message"}, set(), "case step")
            require(isinstance(step["message"], dict), "case step.message must be an object")
            validator.process(step["direction"], step["message"])
    except ValidationError as exc:
        if expected == "pass":
            raise ValidationError(f"case {case['name']} unexpectedly failed: {exc}") from exc
        contains = case.get("error_contains")
        if contains is not None:
            require(isinstance(contains, str) and contains in str(exc), f"case {case['name']} failed for the wrong reason: {exc}")
        return {"name": case["name"], "status": "expected_failure", "reason": str(exc)}
    require(expected == "pass", f"case {case['name']} unexpectedly passed")
    return {"name": case["name"], "status": "passed"}


def validate_fixture(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    _require_exact_keys(
        fixture,
        {"schema_version", "protocol_version", "client", "server", "tool", "cases"},
        set(),
        "fixture",
    )
    require(fixture["schema_version"] == 1, "unsupported fixture schema_version")
    require(fixture["protocol_version"] == PROTOCOL_VERSION, "fixture protocol version mismatch")
    require(isinstance(fixture["client"], dict) and isinstance(fixture["server"], dict), "client/server fixture sections required")
    require(isinstance(fixture["cases"], list) and fixture["cases"], "fixture cases must be non-empty")
    validate_tool_descriptor(fixture["tool"])
    names = [case.get("name") for case in fixture["cases"] if isinstance(case, dict)]
    require(len(names) == len(fixture["cases"]), "every case must be an object with a name")
    require(len(names) == len(set(names)), "fixture case names must be unique")
    return [execute_case(fixture, case) for case in fixture["cases"]]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        type=Path,
        default=Path(__file__).with_name("mcp-cases.json"),
        help="path to the strict JSON fixture",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    fixture = load_json(args.fixture)
    results = validate_fixture(fixture)
    summary = {
        "status": "ok",
        "profile": "offline-mcp-teaching-profile-v1",
        "protocol_version": fixture["protocol_version"],
        "case_count": len(results),
        "passed": sum(result["status"] == "passed" for result in results),
        "expected_failures": sum(result["status"] == "expected_failure" for result in results),
        "cases": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValidationError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1) from exc
