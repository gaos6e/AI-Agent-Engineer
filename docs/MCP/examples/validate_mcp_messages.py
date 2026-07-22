"""Validate a deliberately small, offline MCP teaching profile.

This module is not an official MCP conformance suite.  It turns the course's
most important protocol invariants into deterministic checks without a network,
an SDK, or credentials.  The profile is intentionally stricter than JSON-RPC
where strictness makes mistakes easier for beginners to see.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse, urlsplit


PROTOCOL_VERSION = "2025-11-25"
CLIENT_TO_SERVER = "client_to_server"
SERVER_TO_CLIENT = "server_to_client"
DIRECTIONS = {CLIENT_TO_SERVER, SERVER_TO_CLIENT}
TOOL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
URI_SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*$")
URI_CHARACTER_PATTERN = re.compile(r"^[A-Za-z0-9:/?#\[\]@!$&'()*+,;=._~%-]+$")
MIME_TYPE_PATTERN = re.compile(
    r"^[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+(?:\s*;\s*[^\s=;]+=[^\s;]+)*$"
)
URI_TEMPLATE_OPERATORS = "+#./;?&"
URI_TEMPLATE_VARNAME_PATTERN = re.compile(
    r"^(?:[A-Za-z0-9_]|%[0-9A-Fa-f]{2})+"
    r"(?:\.(?:[A-Za-z0-9_]|%[0-9A-Fa-f]{2})+)*$"
)
RESOURCE_METHODS = {
    "resources/list",
    "resources/read",
    "resources/templates/list",
    "resources/subscribe",
    "resources/unsubscribe",
}
RESOURCE_SCOPES = {
    "resources/list": "resources:list",
    "resources/templates/list": "resources:list",
    "resources/read": "resources:read",
    "resources/subscribe": "resources:subscribe",
    "resources/unsubscribe": "resources:subscribe",
}
MAX_URI_LENGTH = 2048
MAX_CURSOR_LENGTH = 1024
MAX_RESOURCE_CONTENT_BYTES = 64 * 1024
MAX_RESOURCE_CONTENT_ITEMS = 64
MAX_RESOURCE_LIST_ITEMS = 256
MAX_TOOL_LIST_ITEMS = 256
MAX_JSON_BYTES = 2_000_000
MAX_JSON_DEPTH = 64
MAX_SCHEMA_DEPTH = 16
MAX_SCHEMA_PROPERTIES = 256
MAX_SCHEMA_ENUM_ITEMS = 256
MAX_SCHEMA_COLLECTION_ITEMS = 1_024
MAX_SCHEMA_STRING_CHARS = 100_000
MAX_FIXTURE_CASES = 256
MAX_CASE_STEPS = 512
MAX_PENDING_REQUESTS = 1_024
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


def _reject_excessive_json_nesting(text: str) -> None:
    """Bound container nesting before the recursive decoder runs."""

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
            require(depth <= MAX_JSON_DEPTH, f"JSON nesting exceeds {MAX_JSON_DEPTH}")
        elif character in "]}":
            depth = max(0, depth - 1)


def loads_strict(text: str) -> Any:
    """Parse strict JSON: duplicate keys and NaN/Infinity are rejected."""
    require(isinstance(text, str), "JSON input must be text")
    try:
        raw = text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ValidationError("JSON input contains invalid Unicode") from exc
    require(len(raw) <= MAX_JSON_BYTES, f"JSON input exceeds {MAX_JSON_BYTES} UTF-8 bytes")
    _reject_excessive_json_nesting(text)
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON at line {exc.lineno}: {exc.msg}") from exc
    except RecursionError as exc:
        raise ValidationError("JSON nesting exceeds the decoder limit") from exc


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_JSON_BYTES + 1)
        require(len(raw) <= MAX_JSON_BYTES, f"fixture exceeds {MAX_JSON_BYTES} UTF-8 bytes")
        text = raw.decode("utf-8", errors="strict")
    except ValidationError:
        raise
    except (OSError, UnicodeError) as exc:
        raise ValidationError(f"unable to read fixture: {type(exc).__name__}") from exc
    data = loads_strict(text)
    require(isinstance(data, dict), "fixture root must be an object")
    return data


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        # JSON permits arbitrarily large integer literals, but this compact
        # teaching profile validates numbers through Python's finite-float
        # domain.  Reject rather than leaking a conversion exception.
        return False


def _matches_schema_type(value: Any, expected: str) -> bool:
    """Use JSON types, not Python's bool-is-int equality, for schema checks."""

    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return _is_integer(value)
    if expected == "number":
        return _is_number(value)
    if expected == "boolean":
        return isinstance(value, bool)
    return False


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


def _validate_meta(value: dict[str, Any], label: str) -> None:
    if "_meta" in value:
        require(isinstance(value["_meta"], dict), f"{label}._meta must be an object")


def _validate_cursor(value: Any, label: str) -> None:
    require(isinstance(value, str) and value, f"{label} cursor must be a non-empty string")
    require(len(value) <= MAX_CURSOR_LENGTH, f"{label} cursor exceeds the size limit")


def _validate_absolute_uri(value: Any, label: str) -> str:
    require(isinstance(value, str) and value, f"{label} must be a non-empty URI string")
    require(len(value) <= MAX_URI_LENGTH, f"{label} exceeds the URI size limit")
    require(re.search(r"[\s\x00-\x1f\x7f]", value) is None, f"{label} contains forbidden whitespace/control characters")
    require(
        URI_CHARACTER_PATTERN.fullmatch(value) is not None,
        f"{label} contains characters outside the RFC 3986 URI character set",
    )
    require(re.search(r"%(?![0-9A-Fa-f]{2})", value) is None, f"{label} contains malformed percent encoding")
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError as exc:
        raise ValidationError(f"{label} is not a valid absolute URI: {exc}") from exc
    require(bool(parsed.scheme) and URI_SCHEME_PATTERN.fullmatch(parsed.scheme) is not None, f"{label} must be an absolute URI")
    return value


def _validate_uri_template_varspec(value: str, label: str) -> None:
    modifier = ""
    variable = value
    if value.endswith("*"):
        modifier = "*"
        variable = value[:-1]
    elif ":" in value:
        variable, prefix = value.rsplit(":", 1)
        require(
            re.fullmatch(r"[1-9][0-9]{0,3}", prefix) is not None,
            f"{label} has an invalid RFC 6570 prefix modifier",
        )
        modifier = f":{prefix}"
    require(variable != "", f"{label} has an empty RFC 6570 variable name")
    require(
        URI_TEMPLATE_VARNAME_PATTERN.fullmatch(variable) is not None,
        f"{label} has an invalid RFC 6570 variable name: {variable}",
    )
    require(not (modifier == "*" and ":" in variable), f"{label} combines incompatible modifiers")


def _validate_uri_template(value: Any, label: str) -> str:
    require(isinstance(value, str) and value, f"{label} must be a non-empty URI template string")
    require(len(value) <= MAX_URI_LENGTH, f"{label} exceeds the URI template size limit")
    matches = list(re.finditer(r"\{([^{}]+)\}", value))
    require(matches, f"{label} must contain at least one RFC 6570 expression")
    for match in matches:
        expression = match.group(1)
        if expression[0] in URI_TEMPLATE_OPERATORS:
            expression = expression[1:]
        require(expression != "", f"{label} contains an empty RFC 6570 expression")
        for varspec in expression.split(","):
            _validate_uri_template_varspec(varspec, label)
    expanded = re.sub(r"\{[^{}]+\}", "sample", value)
    require("{" not in expanded and "}" not in expanded, f"{label} contains unbalanced braces")
    _validate_absolute_uri(expanded, label)
    return value


def _validate_mime_type(value: Any, label: str) -> None:
    require(
        isinstance(value, str) and MIME_TYPE_PATTERN.fullmatch(value) is not None,
        f"{label} must be a valid MIME type",
    )


def _validate_annotations(value: Any, label: str) -> None:
    require(isinstance(value, dict), f"{label} must be an object")
    _require_exact_keys(value, set(), {"audience", "priority", "lastModified"}, label)
    if "audience" in value:
        audience = value["audience"]
        require(isinstance(audience, list), f"{label}.audience must be an array")
        require(
            all(isinstance(role, str) and role in {"user", "assistant"} for role in audience),
            f"{label}.audience contains an invalid role",
        )
        require(len(audience) == len(set(audience)), f"{label}.audience contains duplicates")
    if "priority" in value:
        priority = value["priority"]
        require(_is_number(priority) and 0 <= priority <= 1, f"{label}.priority must be between 0 and 1")
    if "lastModified" in value:
        require(isinstance(value["lastModified"], str) and value["lastModified"], f"{label}.lastModified must be a timestamp string")


def _validate_icons(value: Any, label: str) -> None:
    require(isinstance(value, list), f"{label} must be an array")
    for index, icon in enumerate(value):
        item_label = f"{label}[{index}]"
        require(isinstance(icon, dict), f"{item_label} must be an object")
        _require_exact_keys(icon, {"src"}, {"mimeType", "sizes", "theme"}, item_label)
        _validate_absolute_uri(icon["src"], f"{item_label}.src")
        if "mimeType" in icon:
            _validate_mime_type(icon["mimeType"], f"{item_label}.mimeType")
        if "sizes" in icon:
            require(
                isinstance(icon["sizes"], list)
                and all(isinstance(size, str) and size for size in icon["sizes"]),
                f"{item_label}.sizes must be an array of non-empty strings",
            )
        if "theme" in icon:
            require(icon["theme"] in {"light", "dark"}, f"{item_label}.theme must be light or dark")


def _validate_resource_common(value: dict[str, Any], label: str) -> None:
    require(isinstance(value["name"], str) and 1 <= len(value["name"]) <= 255, f"{label}.name must be 1-255 characters")
    for key in ("title", "description"):
        if key in value:
            require(isinstance(value[key], str) and value[key], f"{label}.{key} must be a non-empty string")
    if "mimeType" in value:
        _validate_mime_type(value["mimeType"], f"{label}.mimeType")
    if "annotations" in value:
        _validate_annotations(value["annotations"], f"{label}.annotations")
    if "icons" in value:
        _validate_icons(value["icons"], f"{label}.icons")
    _validate_meta(value, label)


def _validate_resource_descriptor(value: Any, label: str) -> str:
    require(isinstance(value, dict), f"{label} must be an object")
    _require_exact_keys(
        value,
        {"uri", "name"},
        {"title", "description", "mimeType", "annotations", "icons", "size", "_meta"},
        label,
    )
    uri = _validate_absolute_uri(value["uri"], f"{label}.uri")
    _validate_resource_common(value, label)
    if "size" in value:
        require(_is_integer(value["size"]) and value["size"] >= 0, f"{label}.size must be a non-negative integer")
        require(value["size"] <= MAX_RESOURCE_CONTENT_BYTES, f"{label}.size exceeds the teaching-profile size limit")
    return uri


def _validate_resource_template_descriptor(value: Any, label: str) -> str:
    require(isinstance(value, dict), f"{label} must be an object")
    _require_exact_keys(
        value,
        {"uriTemplate", "name"},
        {"title", "description", "mimeType", "annotations", "icons", "_meta"},
        label,
    )
    template = _validate_uri_template(value["uriTemplate"], f"{label}.uriTemplate")
    _validate_resource_common(value, label)
    return template


def _validate_resource_content(value: Any, label: str) -> tuple[str, int]:
    require(isinstance(value, dict), f"{label} must be an object")
    _require_exact_keys(value, {"uri"}, {"mimeType", "text", "blob", "_meta"}, label)
    uri = _validate_absolute_uri(value["uri"], f"{label}.uri")
    has_text = "text" in value
    has_blob = "blob" in value
    require(has_text != has_blob, f"{label} must contain exactly one of text or blob")
    if "mimeType" in value:
        _validate_mime_type(value["mimeType"], f"{label}.mimeType")
    _validate_meta(value, label)
    if has_text:
        require(isinstance(value["text"], str), f"{label}.text must be a string")
        content_size = len(value["text"].encode("utf-8"))
    else:
        require(isinstance(value["blob"], str), f"{label}.blob must be a base64 string")
        try:
            decoded = base64.b64decode(value["blob"], validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValidationError(f"{label}.blob must be valid base64") from exc
        require(
            base64.b64encode(decoded).decode("ascii") == value["blob"],
            f"{label}.blob must use canonical padded base64",
        )
        content_size = len(decoded)
    require(content_size <= MAX_RESOURCE_CONTENT_BYTES, f"{label} exceeds the teaching-profile size limit")
    return uri, content_size


def classify_message(message: dict[str, Any]) -> str:
    """Return request, notification, or response after strict envelope checks."""
    require(isinstance(message, dict), "JSON-RPC message must be an object")
    require(message.get("jsonrpc") == "2.0", "jsonrpc must be '2.0'")

    has_method = "method" in message
    has_result = "result" in message
    has_error = "error" in message
    require(
        not (has_method and (has_result or has_error)),
        "message cannot mix request/notification method with response result/error",
    )

    if has_method:
        require(isinstance(message["method"], str) and message["method"], "method must be a non-empty string")
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


def _validate_schema_rule(schema: Any, label: str, depth: int = 0) -> None:
    """Validate the deliberately small JSON Schema subset this lab executes."""

    require(isinstance(schema, dict), f"{label} must be a JSON Schema object")
    require(depth <= MAX_SCHEMA_DEPTH, f"{label} exceeds schema depth {MAX_SCHEMA_DEPTH}")
    allowed = {
        "$schema",
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "minItems",
        "maxItems",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "enum",
        "title",
        "description",
    }
    unknown = set(schema) - allowed
    require(not unknown, f"{label} uses unsupported schema keywords: {sorted(unknown)}")
    for field in ("$schema", "title", "description"):
        if field in schema:
            require(isinstance(schema[field], str) and schema[field], f"{label}.{field} must be a non-empty string")

    expected = schema.get("type")
    require(
        expected in {"object", "array", "string", "integer", "number", "boolean"},
        f"{label}.type is unsupported or missing",
    )

    if "enum" in schema:
        enum = schema["enum"]
        require(
            isinstance(enum, list) and 1 <= len(enum) <= MAX_SCHEMA_ENUM_ITEMS,
            f"{label}.enum must contain 1..{MAX_SCHEMA_ENUM_ITEMS} scalar values",
        )
        require(
            all(
                item is None
                or isinstance(item, (str, bool))
                or _is_number(item)
                for item in enum
            ),
            f"{label}.enum supports only finite JSON scalar values in this profile",
        )
        require(
            all(_matches_schema_type(item, expected) for item in enum),
            f"{label}.enum contains values incompatible with declared type {expected}",
        )
        encoded = [
            json.dumps(item, ensure_ascii=False, allow_nan=False, sort_keys=True)
            for item in enum
        ]
        require(len(encoded) == len(set(encoded)), f"{label}.enum contains duplicates")

    if expected == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        require(isinstance(properties, dict), f"{label}.properties must be an object")
        require(
            len(properties) <= MAX_SCHEMA_PROPERTIES,
            f"{label}.properties exceeds {MAX_SCHEMA_PROPERTIES} entries",
        )
        require(
            all(isinstance(key, str) and 1 <= len(key) <= 128 for key in properties),
            f"{label}.properties names must contain 1..128 characters",
        )
        require(isinstance(required, list), f"{label}.required must be an array")
        require(
            len(required) <= MAX_SCHEMA_PROPERTIES
            and all(isinstance(key, str) for key in required),
            f"{label}.required entries must be bounded strings",
        )
        require(len(required) == len(set(required)), f"{label}.required contains duplicates")
        require(all(key in properties for key in required), f"{label}.required references an unknown property")
        if "additionalProperties" in schema:
            require(isinstance(schema["additionalProperties"], bool), f"{label}.additionalProperties must be boolean")
        for key, child in properties.items():
            _validate_schema_rule(child, f"{label}.properties.{key}", depth + 1)
        forbidden = {"items", "minItems", "maxItems", "minLength", "maxLength", "minimum", "maximum"} & set(schema)
        require(not forbidden, f"{label} has keywords incompatible with object: {sorted(forbidden)}")
    elif expected == "array":
        require("items" in schema, f"{label}.items is required for arrays in this profile")
        _validate_schema_rule(schema["items"], f"{label}.items", depth + 1)
        minimum = schema.get("minItems", 0)
        maximum = schema.get("maxItems", MAX_SCHEMA_COLLECTION_ITEMS)
        require(_is_integer(minimum) and 0 <= minimum, f"{label}.minItems must be a non-negative integer")
        require(
            _is_integer(maximum) and minimum <= maximum <= MAX_SCHEMA_COLLECTION_ITEMS,
            f"{label}.maxItems must be between minItems and {MAX_SCHEMA_COLLECTION_ITEMS}",
        )
        forbidden = {"properties", "required", "additionalProperties", "minLength", "maxLength", "minimum", "maximum"} & set(schema)
        require(not forbidden, f"{label} has keywords incompatible with array: {sorted(forbidden)}")
    elif expected == "string":
        minimum = schema.get("minLength", 0)
        maximum = schema.get("maxLength", MAX_SCHEMA_STRING_CHARS)
        require(_is_integer(minimum) and 0 <= minimum, f"{label}.minLength must be a non-negative integer")
        require(
            _is_integer(maximum) and minimum <= maximum <= MAX_SCHEMA_STRING_CHARS,
            f"{label}.maxLength must be between minLength and {MAX_SCHEMA_STRING_CHARS}",
        )
        forbidden = {"properties", "required", "additionalProperties", "items", "minItems", "maxItems", "minimum", "maximum"} & set(schema)
        require(not forbidden, f"{label} has keywords incompatible with string: {sorted(forbidden)}")
    elif expected in {"integer", "number"}:
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None:
            require(_is_number(minimum), f"{label}.minimum must be finite")
        if maximum is not None:
            require(_is_number(maximum), f"{label}.maximum must be finite")
        if minimum is not None and maximum is not None:
            require(minimum <= maximum, f"{label}.minimum must not exceed maximum")
        forbidden = {"properties", "required", "additionalProperties", "items", "minItems", "maxItems", "minLength", "maxLength"} & set(schema)
        require(not forbidden, f"{label} has incompatible numeric keywords: {sorted(forbidden)}")
    else:
        forbidden = set(schema) & {
            "properties",
            "required",
            "additionalProperties",
            "items",
            "minItems",
            "maxItems",
            "minLength",
            "maxLength",
            "minimum",
            "maximum",
        }
        require(not forbidden, f"{label} has keywords incompatible with boolean: {sorted(forbidden)}")


def _validate_schema_shape(schema: Any, label: str) -> None:
    _validate_schema_rule(schema, label)
    require(schema.get("type") == "object", f"{label}.type must be object")


def validate_value(
    rule: dict[str, Any],
    value: Any,
    path: str = "$",
    *,
    _depth: int = 0,
) -> None:
    """Validate the small JSON Schema subset used by the course fixture."""
    require(isinstance(rule, dict), f"schema at {path} must be an object")
    require(_depth <= MAX_SCHEMA_DEPTH, f"{path} exceeds validation depth {MAX_SCHEMA_DEPTH}")
    expected = rule.get("type")
    if expected == "object":
        require(isinstance(value, dict), f"{path} must be an object")
        require(len(value) <= MAX_SCHEMA_COLLECTION_ITEMS, f"{path} has too many properties")
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
                validate_value(properties[key], item, f"{path}.{key}", _depth=_depth + 1)
    elif expected == "array":
        require(isinstance(value, list), f"{path} must be an array")
        require(len(value) <= MAX_SCHEMA_COLLECTION_ITEMS, f"{path} has too many items")
        if "minItems" in rule:
            require(len(value) >= rule["minItems"], f"{path} has too few items")
        if "maxItems" in rule:
            require(len(value) <= rule["maxItems"], f"{path} has too many items")
        if "items" in rule:
            for index, item in enumerate(value):
                validate_value(rule["items"], item, f"{path}[{index}]", _depth=_depth + 1)
    elif expected == "string":
        require(isinstance(value, str), f"{path} must be a string")
        require(len(value) <= MAX_SCHEMA_STRING_CHARS, f"{path} exceeds the profile string limit")
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
    if expected == "integer":
        # Python integers retain arbitrary precision.  Do not route them
        # through _is_number(), which intentionally rejects values that do
        # not fit the finite-float domain used by number schemas.
        if "minimum" in rule:
            require(value >= rule["minimum"], f"{path} is below minimum")
        if "maximum" in rule:
            require(value <= rule["maximum"], f"{path} is above maximum")
    elif _is_number(value):
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


def _validate_server_capabilities(capabilities: dict[str, Any]) -> None:
    resources = capabilities.get("resources")
    if resources is None:
        return
    require(isinstance(resources, dict), "server resources capability must be an object")
    _require_exact_keys(resources, set(), {"subscribe", "listChanged"}, "server resources capability")
    for key in ("subscribe", "listChanged"):
        if key in resources:
            require(isinstance(resources[key], bool), f"server resources.{key} must be boolean")


def validate_authorization_config(authorization: Any) -> None:
    """Validate wire-external teaching policy; this is not an MCP schema."""
    require(isinstance(authorization, dict), "authorization teaching policy must be an object")
    _require_exact_keys(
        authorization,
        {"protected_resource", "initial_revision", "revisions"},
        set(),
        "authorization teaching policy",
    )
    protected_resource = _validate_absolute_uri(
        authorization["protected_resource"],
        "authorization protected_resource",
    )
    parsed_resource = urlsplit(protected_resource)
    require(
        parsed_resource.scheme.lower() == "https" and bool(parsed_resource.hostname),
        "authorization protected_resource must be an absolute HTTPS MCP server URI",
    )
    require(
        parsed_resource.username is None and parsed_resource.password is None,
        "authorization protected_resource must not contain user information",
    )
    require(not parsed_resource.fragment, "authorization protected_resource must not contain a fragment")
    initial_revision = authorization["initial_revision"]
    revisions = authorization["revisions"]
    require(isinstance(initial_revision, str) and initial_revision, "authorization initial_revision required")
    require(isinstance(revisions, dict) and revisions, "authorization revisions must be a non-empty object")
    require(initial_revision in revisions, "authorization initial_revision does not exist")
    allowed_scopes = set(RESOURCE_SCOPES.values())

    for revision, policy in revisions.items():
        require(isinstance(revision, str) and revision, "authorization revision names must be non-empty strings")
        require(isinstance(policy, dict), f"authorization revision {revision} must be an object")
        _require_exact_keys(
            policy,
            {"principals", "resources", "resourceTemplates"},
            set(),
            f"authorization revision {revision}",
        )
        principals = policy["principals"]
        require(isinstance(principals, dict), f"authorization revision {revision}.principals must be an object")
        for subject, principal in principals.items():
            label = f"authorization revision {revision}.principals.{subject}"
            require(isinstance(subject, str) and subject, f"{label} subject must be non-empty")
            require(isinstance(principal, dict), f"{label} must be an object")
            _require_exact_keys(principal, {"tenant", "scopes"}, {"enabled"}, label)
            require(isinstance(principal["tenant"], str) and principal["tenant"], f"{label}.tenant required")
            scopes = principal["scopes"]
            require(isinstance(scopes, list), f"{label}.scopes must be an array")
            require(all(isinstance(scope, str) and scope in allowed_scopes for scope in scopes), f"{label}.scopes contains an unsupported scope")
            require(len(scopes) == len(set(scopes)), f"{label}.scopes contains duplicates")
            if "enabled" in principal:
                require(isinstance(principal["enabled"], bool), f"{label}.enabled must be boolean")

        resources = policy["resources"]
        require(isinstance(resources, list), f"authorization revision {revision}.resources must be an array")
        resource_by_uri: dict[str, dict[str, Any]] = {}
        for index, resource in enumerate(resources):
            label = f"authorization revision {revision}.resources[{index}]"
            require(isinstance(resource, dict), f"{label} must be an object")
            _require_exact_keys(resource, {"uri", "tenant"}, {"children"}, label)
            uri = _validate_absolute_uri(resource["uri"], f"{label}.uri")
            require(uri not in resource_by_uri, f"authorization revision {revision} has duplicate resource URI")
            require(isinstance(resource["tenant"], str) and resource["tenant"], f"{label}.tenant required")
            children = resource.get("children", [])
            require(isinstance(children, list), f"{label}.children must be an array")
            for child_index, child in enumerate(children):
                _validate_absolute_uri(child, f"{label}.children[{child_index}]")
            require(len(children) == len(set(children)), f"{label}.children contains duplicates")
            resource_by_uri[uri] = resource
        for resource in resources:
            for child in resource.get("children", []):
                require(child in resource_by_uri, f"authorization child URI is absent from resource policy: {child}")
                require(
                    resource_by_uri[child]["tenant"] == resource["tenant"],
                    f"authorization child URI crosses a tenant boundary: {child}",
                )

        templates = policy["resourceTemplates"]
        require(isinstance(templates, list), f"authorization revision {revision}.resourceTemplates must be an array")
        seen_templates: set[str] = set()
        for index, template in enumerate(templates):
            label = f"authorization revision {revision}.resourceTemplates[{index}]"
            require(isinstance(template, dict), f"{label} must be an object")
            _require_exact_keys(template, {"uriTemplate", "tenant"}, set(), label)
            uri_template = _validate_uri_template(template["uriTemplate"], f"{label}.uriTemplate")
            require(uri_template not in seen_templates, f"authorization revision {revision} has duplicate resource template")
            seen_templates.add(uri_template)
            require(isinstance(template["tenant"], str) and template["tenant"], f"{label}.tenant required")


@dataclass(frozen=True)
class PendingRequest:
    direction: str
    method: str
    metadata: dict[str, Any]


class McpSessionValidator:
    """Stateful validator for a small but bilateral MCP session."""

    def __init__(
        self,
        protocol_version: str,
        tool: dict[str, Any],
        *,
        authorization: dict[str, Any] | None = None,
    ) -> None:
        require(protocol_version == PROTOCOL_VERSION, f"teaching fixture expects {PROTOCOL_VERSION}")
        validate_tool_descriptor(tool)
        if authorization is not None:
            validate_authorization_config(authorization)
        self.protocol_version = protocol_version
        self.tool = copy.deepcopy(tool)
        self.authorization_revisions = (
            copy.deepcopy(authorization["revisions"]) if authorization is not None else {}
        )
        self.protected_resource = (
            authorization["protected_resource"] if authorization is not None else None
        )
        self.active_authorization_revision = (
            authorization["initial_revision"] if authorization is not None else None
        )
        self.client_capabilities: dict[str, Any] = {}
        self.server_capabilities: dict[str, Any] = {}
        self.state = "new"
        self.pending: dict[tuple[str, tuple[str, Any]], PendingRequest] = {}
        self.subscriptions: dict[str, dict[str, Any]] = {}
        self.invalidated_subscriptions: set[str] = set()

    def process(
        self,
        direction: str,
        message: dict[str, Any],
        *,
        transport_context: dict[str, Any] | None = None,
    ) -> None:
        require(direction in DIRECTIONS, f"unknown direction: {direction}")
        kind = classify_message(message)
        if self.state != "ready":
            require(transport_context is None, "transport_context is not part of MCP lifecycle messages")
            self._process_lifecycle(direction, kind, message)
            return

        if kind == "request":
            self._process_request(direction, message, transport_context)
        elif kind == "notification":
            self._process_notification(direction, message, transport_context)
        else:
            require(transport_context is None, "responses use the authorization snapshot bound to the request")
            self._process_response(direction, message)

    def apply_control_event(self, event: dict[str, Any]) -> None:
        """Apply wire-external teaching control-plane state, never JSON-RPC fields."""
        require(self.state == "ready", "authorization control events require a ready session")
        require(isinstance(event, dict), "control event must be an object")
        _require_exact_keys(
            event,
            {"type", "revision"},
            set(),
            "control event",
        )
        require(
            event["type"] == "activate_authorization_revision",
            "unsupported control event type",
        )
        revision = event["revision"]
        require(
            isinstance(revision, str) and revision in self.authorization_revisions,
            f"unknown authorization revision: {revision}",
        )
        if revision != self.active_authorization_revision:
            self.invalidated_subscriptions.update(self.subscriptions)
            self.subscriptions.clear()
            self.active_authorization_revision = revision

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
            pending_key, pending = self._find_pending_response(direction, message)
            require(pending.method == "initialize", "response does not match initialize")
            if "error" in message:
                self.pending.pop(pending_key)
                raise ValidationError("initialize failed; this transcript cannot enter operation")
            result = message["result"]
            require(isinstance(result, dict), "initialize result must be an object")
            _require_exact_keys(result, {"protocolVersion", "capabilities", "serverInfo"}, {"instructions"}, "initialize result")
            require(result["protocolVersion"] == self.protocol_version, "client does not support server-selected version")
            require(isinstance(result["capabilities"], dict), "server capabilities must be an object")
            _validate_server_capabilities(result["capabilities"])
            _validate_info(result["serverInfo"], "serverInfo")
            self.server_capabilities = copy.deepcopy(result["capabilities"])
            self.pending.pop(pending_key)
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
        require(
            len(self.pending) < MAX_PENDING_REQUESTS,
            f"outstanding request capacity exceeds {MAX_PENDING_REQUESTS}",
        )
        self.pending[key] = PendingRequest(direction, message["method"], metadata)

    def _find_pending_response(
        self,
        direction: str,
        message: dict[str, Any],
    ) -> tuple[tuple[str, tuple[str, Any]], PendingRequest]:
        key = (_opposite(direction), _id_key(message["id"]))
        require(key in self.pending, f"response id has no matching outstanding request: {message['id']!r}")
        return key, self.pending[key]

    def _capabilities_for_receiver(self, direction: str) -> tuple[str, dict[str, Any]]:
        if direction == CLIENT_TO_SERVER:
            return "server", self.server_capabilities
        return "client", self.client_capabilities

    def _require_receiver_capability(self, direction: str, path: tuple[str, ...]) -> None:
        owner, capabilities = self._capabilities_for_receiver(direction)
        require(_has_capability(capabilities, path), f"{owner} did not declare capability: {'.'.join(path)}")

    def _current_authorization_policy(self) -> dict[str, Any]:
        revision = self.active_authorization_revision
        require(
            isinstance(revision, str) and revision in self.authorization_revisions,
            "resource operations require a configured authorization teaching policy",
        )
        return self.authorization_revisions[revision]

    def _validate_transport_context(
        self,
        transport_context: Any,
        required_scope: str,
    ) -> dict[str, Any]:
        require(
            isinstance(transport_context, dict),
            "resource operation requires wire-external transport_context",
        )
        _require_exact_keys(
            transport_context,
            {
                "transport",
                "token_active",
                "token_audience",
                "resource",
                "subject",
                "tenant",
                "scopes",
                "authorization_revision",
            },
            set(),
            "transport_context",
        )
        require(
            transport_context["transport"] == "streamable_http",
            "resource teaching cases require streamable_http transport context",
        )
        require(
            transport_context["token_active"] is True,
            "resource operation requires an active access token",
        )
        protected_resource = self.protected_resource
        require(isinstance(protected_resource, str), "protected resource is not configured")
        token_audience = _validate_absolute_uri(
            transport_context["token_audience"],
            "transport_context token_audience",
        )
        resource_indicator = _validate_absolute_uri(
            transport_context["resource"],
            "transport_context resource",
        )
        require(
            token_audience == protected_resource,
            "access token audience is not bound to this MCP server",
        )
        require(
            resource_indicator == protected_resource,
            "RFC 8707 resource indicator is not bound to this MCP server",
        )
        subject = transport_context["subject"]
        tenant = transport_context["tenant"]
        scopes = transport_context["scopes"]
        revision = transport_context["authorization_revision"]
        require(isinstance(subject, str) and subject, "transport_context subject required")
        require(isinstance(tenant, str) and tenant, "transport_context tenant required")
        require(isinstance(scopes, list), "transport_context scopes must be an array")
        require(all(isinstance(scope, str) and scope for scope in scopes), "transport_context scopes must be strings")
        require(len(scopes) == len(set(scopes)), "transport_context scopes contains duplicates")
        require(
            revision == self.active_authorization_revision,
            "stale or unknown authorization revision in transport_context",
        )
        policy = self._current_authorization_policy()
        principal = policy["principals"].get(subject)
        require(isinstance(principal, dict), f"unknown authorization principal: {subject}")
        require(principal.get("enabled", True) is True, f"authorization principal is revoked: {subject}")
        require(tenant == principal["tenant"], "transport_context tenant does not match the principal binding")
        granted_scopes = set(principal["scopes"])
        require(set(scopes) <= granted_scopes, "transport_context claims a scope not granted to the principal")
        require(required_scope in scopes, f"resource operation requires scope {required_scope}")
        return copy.deepcopy(transport_context)

    def _resource_policy_for_uri(
        self,
        uri: str,
        authorization: dict[str, Any],
    ) -> dict[str, Any]:
        policy = self._current_authorization_policy()
        resource = next((item for item in policy["resources"] if item["uri"] == uri), None)
        require(resource is not None, f"resource URI is absent from the access policy: {uri}")
        require(resource["tenant"] == authorization["tenant"], "resource tenant is not authorized for this principal")
        return resource

    def _template_policy_for_uri(
        self,
        uri_template: str,
        authorization: dict[str, Any],
    ) -> dict[str, Any]:
        policy = self._current_authorization_policy()
        template = next(
            (item for item in policy["resourceTemplates"] if item["uriTemplate"] == uri_template),
            None,
        )
        require(template is not None, f"resource template is absent from the access policy: {uri_template}")
        require(template["tenant"] == authorization["tenant"], "resource template tenant is not authorized for this principal")
        return template

    def _validate_resource_request(
        self,
        method: str,
        params: dict[str, Any],
        transport_context: Any,
    ) -> dict[str, Any]:
        require(method in RESOURCE_METHODS, f"unsupported resource method: {method}")
        authorization = self._validate_transport_context(
            transport_context,
            RESOURCE_SCOPES[method],
        )
        metadata: dict[str, Any] = {"authorization": authorization}

        if method in {"resources/list", "resources/templates/list"}:
            _require_exact_keys(params, set(), {"cursor", "_meta"}, f"{method}.params")
            if "cursor" in params:
                _validate_cursor(params["cursor"], f"{method}.params")
            _validate_meta(params, f"{method}.params")
            return metadata

        _require_exact_keys(params, {"uri"}, {"_meta"}, f"{method}.params")
        uri = _validate_absolute_uri(params["uri"], f"{method}.params.uri")
        self._resource_policy_for_uri(uri, authorization)
        _validate_meta(params, f"{method}.params")
        metadata["uri"] = uri

        if method == "resources/subscribe":
            resources = self.server_capabilities.get("resources")
            require(
                isinstance(resources, dict) and resources.get("subscribe") is True,
                "server did not declare resources.subscribe",
            )
            require(uri not in self.subscriptions, f"resource already has an active subscription: {uri}")
            duplicate_pending = any(
                pending.method == "resources/subscribe" and pending.metadata.get("uri") == uri
                for pending in self.pending.values()
            )
            require(not duplicate_pending, f"resource already has a pending subscription: {uri}")
        elif method == "resources/unsubscribe":
            resources = self.server_capabilities.get("resources")
            require(
                isinstance(resources, dict) and resources.get("subscribe") is True,
                "server did not declare resources.subscribe",
            )
            require(uri in self.subscriptions, f"resource has no active subscription: {uri}")
            duplicate_pending = any(
                pending.method == "resources/unsubscribe" and pending.metadata.get("uri") == uri
                for pending in self.pending.values()
            )
            require(not duplicate_pending, f"resource already has a pending unsubscription: {uri}")
            subscription = self.subscriptions[uri]
            require(
                subscription["subject"] == authorization["subject"]
                and subscription["tenant"] == authorization["tenant"],
                "unsubscribe principal does not own the active subscription",
            )
        return metadata

    def _process_request(
        self,
        direction: str,
        message: dict[str, Any],
        transport_context: dict[str, Any] | None,
    ) -> None:
        method = message["method"]
        params = message.get("params", {})
        metadata: dict[str, Any] = {}

        if direction == CLIENT_TO_SERVER and method in {"tools/list", "tools/call"}:
            self._require_receiver_capability(direction, ("tools",))
        elif direction == CLIENT_TO_SERVER and method in RESOURCE_METHODS:
            self._require_receiver_capability(direction, ("resources",))
        elif direction == CLIENT_TO_SERVER and method.startswith("prompts/"):
            self._require_receiver_capability(direction, ("prompts",))
            raise ValidationError(
                "prompt request schemas are not implemented in this teaching profile"
            )
        elif direction == CLIENT_TO_SERVER and method == "logging/setLevel":
            self._require_receiver_capability(direction, ("logging",))
            raise ValidationError(
                "logging/setLevel schema is not implemented in this teaching profile"
            )
        elif direction == CLIENT_TO_SERVER and method == "completion/complete":
            self._require_receiver_capability(direction, ("completions",))
            raise ValidationError(
                "completion/complete schema is not implemented in this teaching profile"
            )
        elif direction == SERVER_TO_CLIENT and method == "roots/list":
            self._require_receiver_capability(direction, ("roots",))
        elif direction == SERVER_TO_CLIENT and method == "sampling/createMessage":
            self._require_receiver_capability(direction, ("sampling",))
        elif direction == SERVER_TO_CLIENT and method == "elicitation/create":
            self._require_receiver_capability(direction, ("elicitation",))
        elif method.startswith("tasks/"):
            self._validate_task_operation_capability(direction, method)
        elif method.startswith("resources/"):
            raise ValidationError(f"unsupported resource method or wrong direction: {method}")
        elif method != "ping":
            raise ValidationError(f"unsupported method in teaching profile or wrong direction: {method}")

        if method in RESOURCE_METHODS:
            metadata = self._validate_resource_request(method, params, transport_context)
        else:
            require(transport_context is None, "transport_context is only used by resource teaching cases")

        if method == "tools/call":
            metadata = self._validate_tool_call(direction, params)
        elif method == "tools/list":
            _require_exact_keys(params, set(), {"cursor", "_meta"}, "tools/list.params")
            if "cursor" in params:
                _validate_cursor(params["cursor"], "tools/list.params")
            _validate_meta(params, "tools/list.params")
        elif method == "roots/list":
            require(params == {}, "roots/list takes no parameters in this profile")
        elif method == "sampling/createMessage":
            self._validate_sampling_request(params)
            self._validate_task_augmentation(direction, method, params)
        elif method == "elicitation/create":
            metadata = self._validate_elicitation_request(params)
            self._validate_task_augmentation(direction, method, params)
        elif method == "tasks/list":
            _require_exact_keys(params, set(), {"cursor", "_meta"}, "tasks/list.params")
            if "cursor" in params:
                _validate_cursor(params["cursor"], "tasks/list.params")
            _validate_meta(params, "tasks/list.params")
        elif method in {"tasks/get", "tasks/result", "tasks/cancel"}:
            _require_exact_keys(params, {"taskId"}, set(), f"{method}.params")
            require(isinstance(params["taskId"], str) and params["taskId"], f"{method}.taskId required")
            raise ValidationError(
                f"{method} state and result schemas are not implemented in this teaching profile"
            )
        elif method == "ping":
            require(params == {}, "ping takes no parameters in this profile")

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
            require(
                len(params["tools"]) <= MAX_TOOL_LIST_ITEMS,
                "sampling tools exceed the teaching-profile item limit",
            )
            names: set[str] = set()
            for index, tool in enumerate(params["tools"]):
                validate_tool_descriptor(tool)
                require(tool["name"] not in names, f"sampling tools contain duplicate name at index {index}")
                names.add(tool["name"])
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

    def _process_notification(
        self,
        direction: str,
        message: dict[str, Any],
        transport_context: dict[str, Any] | None,
    ) -> None:
        method = message["method"]
        if direction == SERVER_TO_CLIENT and method == "notifications/tools/list_changed":
            require(transport_context is None, "transport_context is only used by resource teaching cases")
            tools = self.server_capabilities.get("tools")
            require(isinstance(tools, dict) and tools.get("listChanged") is True, "server did not declare tools.listChanged")
        elif direction == SERVER_TO_CLIENT and method == "notifications/resources/list_changed":
            require(transport_context is None, "resources/list_changed carries no resource authorization context")
            resources = self.server_capabilities.get("resources")
            require(
                isinstance(resources, dict) and resources.get("listChanged") is True,
                "server did not declare resources.listChanged",
            )
            params = message.get("params", {})
            _require_exact_keys(params, set(), {"_meta"}, "resources list_changed params")
            _validate_meta(params, "resources list_changed params")
        elif direction == SERVER_TO_CLIENT and method == "notifications/resources/updated":
            resources = self.server_capabilities.get("resources")
            require(
                isinstance(resources, dict) and resources.get("subscribe") is True,
                "server did not declare resources.subscribe",
            )
            params = message.get("params", {})
            _require_exact_keys(params, {"uri"}, {"_meta"}, "resources updated params")
            updated_uri = _validate_absolute_uri(params["uri"], "resources updated params.uri")
            _validate_meta(params, "resources updated params")
            authorization = self._validate_transport_context(
                transport_context,
                "resources:subscribe",
            )
            self._resource_policy_for_uri(updated_uri, authorization)
            matching_subscription: tuple[str, dict[str, Any]] | None = None
            for subscribed_uri, subscription in self.subscriptions.items():
                subscribed_resource = self._resource_policy_for_uri(subscribed_uri, subscription)
                if updated_uri == subscribed_uri or updated_uri in subscribed_resource.get("children", []):
                    matching_subscription = (subscribed_uri, subscription)
                    break
            require(matching_subscription is not None, f"resource update has no active subscription: {updated_uri}")
            _, subscription = matching_subscription
            require(
                subscription["subject"] == authorization["subject"]
                and subscription["tenant"] == authorization["tenant"],
                "resource update principal does not match the active subscription",
            )
        elif direction == CLIENT_TO_SERVER and method == "notifications/roots/list_changed":
            require(transport_context is None, "transport_context is only used by resource teaching cases")
            roots = self.client_capabilities.get("roots")
            require(isinstance(roots, dict) and roots.get("listChanged") is True, "client did not declare roots.listChanged")
        elif direction == SERVER_TO_CLIENT and method == "notifications/elicitation/complete":
            require(transport_context is None, "transport_context is only used by resource teaching cases")
            require(_has_capability(self.client_capabilities, ("elicitation", "url")), "client did not declare elicitation.url")
            params = message.get("params", {})
            _require_exact_keys(params, {"elicitationId"}, set(), "elicitation complete params")
        elif method in {"notifications/progress", "notifications/cancelled", "notifications/tasks/status"}:
            require(transport_context is None, "transport_context is only used by resource teaching cases")
            require(isinstance(message.get("params"), dict), f"{method} requires params")
        else:
            raise ValidationError(f"unsupported notification in teaching profile or wrong direction: {method}")

    def _process_response(self, direction: str, message: dict[str, Any]) -> None:
        pending_key, pending = self._find_pending_response(direction, message)
        if "error" in message:
            self.pending.pop(pending_key)
            return
        result = message["result"]
        if pending.method == "tools/call":
            if pending.metadata.get("task_augmented"):
                self._validate_create_task_result(result)
            else:
                self._validate_tool_result(result)
        elif pending.method == "tools/list":
            self._validate_tools_list_result(result)
        elif pending.method == "roots/list":
            self._validate_roots_result(result)
        elif pending.method == "sampling/createMessage":
            self._validate_sampling_result(result)
        elif pending.method == "elicitation/create":
            self._validate_elicitation_result(result, pending.metadata["elicitation_mode"])
        elif pending.method == "tasks/list":
            self._validate_tasks_list_result(result)
        elif pending.method in RESOURCE_METHODS:
            authorization = self._validate_transport_context(
                pending.metadata["authorization"],
                RESOURCE_SCOPES[pending.method],
            )
            if pending.method == "resources/list":
                self._validate_resources_list_result(result, authorization)
            elif pending.method == "resources/templates/list":
                self._validate_resource_templates_list_result(result, authorization)
            elif pending.method == "resources/read":
                self._validate_resource_read_result(
                    result,
                    pending.metadata["uri"],
                    authorization,
                )
            elif pending.method == "resources/subscribe":
                self._validate_empty_resource_result(result, "resources/subscribe result")
                uri = pending.metadata["uri"]
                require(uri not in self.subscriptions, f"resource already has an active subscription: {uri}")
                self.subscriptions[uri] = authorization
                self.invalidated_subscriptions.discard(uri)
            else:
                self._validate_empty_resource_result(result, "resources/unsubscribe result")
                uri = pending.metadata["uri"]
                require(uri in self.subscriptions, f"resource has no active subscription: {uri}")
                self.subscriptions.pop(uri)
        elif pending.method == "ping":
            self._validate_empty_resource_result(result, "ping result")
        else:
            raise ValidationError(
                f"successful result schema is not implemented for {pending.method} in this teaching profile"
            )
        self.pending.pop(pending_key)

    def _validate_tools_list_result(self, result: Any) -> None:
        require(isinstance(result, dict), "tools/list result must be an object")
        _require_exact_keys(result, {"tools"}, {"nextCursor", "_meta"}, "tools/list result")
        tools = result["tools"]
        require(isinstance(tools, list), "tools/list result.tools must be an array")
        require(
            len(tools) <= MAX_TOOL_LIST_ITEMS,
            "tools/list result exceeds the teaching-profile item limit",
        )
        if "nextCursor" in result:
            _validate_cursor(result["nextCursor"], "tools/list result")
        _validate_meta(result, "tools/list result")
        names: set[str] = set()
        for index, tool in enumerate(tools):
            validate_tool_descriptor(tool)
            require(tool["name"] not in names, f"tools/list contains duplicate name at index {index}")
            names.add(tool["name"])

    def _validate_sampling_result(self, result: Any) -> None:
        require(isinstance(result, dict), "sampling result must be an object")
        _require_exact_keys(
            result,
            {"role", "content", "model"},
            {"stopReason", "_meta"},
            "sampling result",
        )
        require(result["role"] in {"user", "assistant"}, "sampling result.role is invalid")
        require(
            isinstance(result["model"], str) and result["model"],
            "sampling result.model must be a non-empty string",
        )
        if "stopReason" in result:
            require(
                isinstance(result["stopReason"], str) and result["stopReason"],
                "sampling result.stopReason must be a non-empty string",
            )
        _validate_meta(result, "sampling result")
        blocks = result["content"] if isinstance(result["content"], list) else [result["content"]]
        require(blocks and len(blocks) <= MAX_RESOURCE_CONTENT_ITEMS, "sampling result.content must be a bounded block or array")
        for index, block in enumerate(blocks):
            require(isinstance(block, dict), f"sampling result.content[{index}] must be an object")
            _require_exact_keys(
                block,
                {"type", "text"},
                {"annotations", "_meta"},
                f"sampling result.content[{index}]",
            )
            require(block["type"] == "text", "this teaching profile accepts text sampling output only")
            require(
                isinstance(block["text"], str)
                and len(block["text"]) <= MAX_SCHEMA_STRING_CHARS,
                f"sampling result.content[{index}].text exceeds the profile limit",
            )
            if "annotations" in block:
                _validate_annotations(block["annotations"], f"sampling result.content[{index}].annotations")
            _validate_meta(block, f"sampling result.content[{index}]")

    def _validate_tasks_list_result(self, result: Any) -> None:
        require(isinstance(result, dict), "tasks/list result must be an object")
        _require_exact_keys(result, {"tasks"}, {"nextCursor", "_meta"}, "tasks/list result")
        require(isinstance(result["tasks"], list), "tasks/list result.tasks must be an array")
        require(
            len(result["tasks"]) <= MAX_RESOURCE_LIST_ITEMS,
            "tasks/list result exceeds the teaching-profile item limit",
        )
        if "nextCursor" in result:
            _validate_cursor(result["nextCursor"], "tasks/list result")
        _validate_meta(result, "tasks/list result")
        for index, task in enumerate(result["tasks"]):
            self._validate_task(task, f"tasks/list result.tasks[{index}]")

    def _validate_task(self, task: Any, label: str) -> None:
        """Validate the common Task fields used by the teaching profile.

        This checks one bounded, structural snapshot only.  It deliberately
        does not claim to model task ownership, state transitions, polling, or
        result retrieval; those methods remain outside this compact lab.
        """

        require(isinstance(task, dict), f"{label} must be an object")
        for field in ("taskId", "status", "createdAt", "lastUpdatedAt"):
            require(
                isinstance(task.get(field), str) and task[field],
                f"{label}.{field} required",
            )
        require("ttl" in task, f"{label}.ttl required")
        require(
            task["status"]
            in {"working", "input_required", "completed", "failed", "cancelled"},
            f"{label}.status is invalid",
        )
        if "statusMessage" in task:
            require(isinstance(task["statusMessage"], str), f"{label}.statusMessage must be a string")
        require(
            task["ttl"] is None or (_is_number(task["ttl"]) and task["ttl"] >= 0),
            f"{label}.ttl must be null or a non-negative finite number",
        )
        if "pollInterval" in task:
            require(
                _is_number(task["pollInterval"]) and task["pollInterval"] >= 0,
                f"{label}.pollInterval must be a non-negative finite number",
            )

    def _validate_resources_list_result(
        self,
        result: Any,
        authorization: dict[str, Any],
    ) -> None:
        require(isinstance(result, dict), "resources/list result must be an object")
        _require_exact_keys(result, {"resources"}, {"nextCursor", "_meta"}, "resources/list result")
        require(isinstance(result["resources"], list), "resources/list result.resources must be an array")
        require(
            len(result["resources"]) <= MAX_RESOURCE_LIST_ITEMS,
            "resources/list result exceeds the teaching-profile item limit",
        )
        if "nextCursor" in result:
            _validate_cursor(result["nextCursor"], "resources/list result")
        _validate_meta(result, "resources/list result")
        seen: set[str] = set()
        for index, descriptor in enumerate(result["resources"]):
            uri = _validate_resource_descriptor(descriptor, f"resources[{index}]")
            require(uri not in seen, f"resources/list contains duplicate URI: {uri}")
            seen.add(uri)
            self._resource_policy_for_uri(uri, authorization)

    def _validate_resource_templates_list_result(
        self,
        result: Any,
        authorization: dict[str, Any],
    ) -> None:
        require(isinstance(result, dict), "resources/templates/list result must be an object")
        _require_exact_keys(
            result,
            {"resourceTemplates"},
            {"nextCursor", "_meta"},
            "resources/templates/list result",
        )
        require(
            isinstance(result["resourceTemplates"], list),
            "resources/templates/list result.resourceTemplates must be an array",
        )
        require(
            len(result["resourceTemplates"]) <= MAX_RESOURCE_LIST_ITEMS,
            "resources/templates/list result exceeds the teaching-profile item limit",
        )
        if "nextCursor" in result:
            _validate_cursor(result["nextCursor"], "resources/templates/list result")
        _validate_meta(result, "resources/templates/list result")
        seen: set[str] = set()
        for index, descriptor in enumerate(result["resourceTemplates"]):
            uri_template = _validate_resource_template_descriptor(
                descriptor,
                f"resourceTemplates[{index}]",
            )
            require(
                uri_template not in seen,
                f"resources/templates/list contains duplicate URI template: {uri_template}",
            )
            seen.add(uri_template)
            self._template_policy_for_uri(uri_template, authorization)

    def _validate_resource_read_result(
        self,
        result: Any,
        requested_uri: str,
        authorization: dict[str, Any],
    ) -> None:
        require(isinstance(result, dict), "resources/read result must be an object")
        _require_exact_keys(result, {"contents"}, {"_meta"}, "resources/read result")
        require(isinstance(result["contents"], list), "resources/read result.contents must be an array")
        require(
            len(result["contents"]) <= MAX_RESOURCE_CONTENT_ITEMS,
            "resources/read result exceeds the teaching-profile content item limit",
        )
        _validate_meta(result, "resources/read result")
        requested_resource = self._resource_policy_for_uri(requested_uri, authorization)
        permitted_uris = {requested_uri, *requested_resource.get("children", [])}
        seen: set[str] = set()
        total_content_size = 0
        for index, content in enumerate(result["contents"]):
            uri, content_size = _validate_resource_content(content, f"contents[{index}]")
            total_content_size += content_size
            require(
                total_content_size <= MAX_RESOURCE_CONTENT_BYTES,
                "resources/read aggregate contents exceed the teaching-profile size limit",
            )
            require(uri in permitted_uris, f"contents[{index}].uri is not the requested resource or an explicit child")
            require(uri not in seen, f"resources/read contains duplicate content URI: {uri}")
            seen.add(uri)
            self._resource_policy_for_uri(uri, authorization)

    def _validate_empty_resource_result(self, result: Any, label: str) -> None:
        require(isinstance(result, dict), f"{label} must be an object")
        _require_exact_keys(result, set(), {"_meta"}, label)
        _validate_meta(result, label)

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
        self._validate_task(result["task"], "task")

    def _validate_roots_result(self, result: Any) -> None:
        require(isinstance(result, dict) and isinstance(result.get("roots"), list), "roots/list result must contain roots array")
        for index, root in enumerate(result["roots"]):
            require(isinstance(root, dict), f"root[{index}] must be an object")
            _require_exact_keys(root, {"uri"}, {"name", "_meta"}, f"root[{index}]")
            uri = _validate_absolute_uri(root["uri"], f"root[{index}].uri")
            parsed = urlsplit(uri)
            require(parsed.scheme.lower() == "file", f"root[{index}].uri must be a file URI")
            require(bool(parsed.netloc or parsed.path), f"root[{index}].uri must identify a location")
            if "name" in root:
                require(isinstance(root["name"], str) and root["name"], f"root[{index}].name must be non-empty")
            _validate_meta(root, f"root[{index}]")

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
    validator = McpSessionValidator(
        fixture["protocol_version"],
        fixture["tool"],
        authorization=fixture["authorization"],
    )
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
    require(
        isinstance(steps, list) and len(steps) <= MAX_CASE_STEPS,
        f"case {case.get('name')} steps must be an array of at most {MAX_CASE_STEPS} items",
    )
    return validator, steps


def execute_case(fixture: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(case.get("name"), str) and case["name"], "case name required")
    expected = case.get("expect")
    require(expected in {"pass", "fail"}, f"case {case['name']} expect must be pass or fail")
    try:
        validator, steps = prepare_case(fixture, case)
        for step in steps:
            require(isinstance(step, dict), f"case {case['name']} step must be an object")
            if "control_event" in step:
                _require_exact_keys(step, {"control_event"}, set(), "case control step")
                validator.apply_control_event(step["control_event"])
                continue
            _require_exact_keys(step, {"direction", "message"}, {"transport_context"}, "case wire step")
            require(isinstance(step["message"], dict), "case step.message must be an object")
            transport_context = step.get("transport_context")
            if transport_context is not None:
                require(isinstance(transport_context, dict), "case transport_context must be an object")
                transport_context = {
                    **copy.deepcopy(fixture["transport_context_defaults"]),
                    **copy.deepcopy(transport_context),
                }
            validator.process(
                step["direction"],
                step["message"],
                transport_context=transport_context,
            )
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
        {
            "schema_version",
            "protocol_version",
            "transport_context_defaults",
            "authorization",
            "client",
            "server",
            "tool",
            "cases",
        },
        set(),
        "fixture",
    )
    require(fixture["schema_version"] == 3, "unsupported fixture schema_version")
    require(fixture["protocol_version"] == PROTOCOL_VERSION, "fixture protocol version mismatch")
    require(isinstance(fixture["client"], dict) and isinstance(fixture["server"], dict), "client/server fixture sections required")
    require(
        isinstance(fixture["cases"], list)
        and 1 <= len(fixture["cases"]) <= MAX_FIXTURE_CASES,
        f"fixture cases must contain 1..{MAX_FIXTURE_CASES} items",
    )
    validate_authorization_config(fixture["authorization"])
    defaults = fixture["transport_context_defaults"]
    require(isinstance(defaults, dict), "fixture transport_context_defaults must be an object")
    _require_exact_keys(
        defaults,
        {"transport", "token_active", "token_audience", "resource"},
        set(),
        "fixture transport_context_defaults",
    )
    require(defaults["transport"] == "streamable_http", "fixture transport must be streamable_http")
    require(defaults["token_active"] is True, "fixture default access token must be active")
    require(
        defaults["token_audience"] == fixture["authorization"]["protected_resource"],
        "fixture token audience must match the protected resource",
    )
    require(
        defaults["resource"] == fixture["authorization"]["protected_resource"],
        "fixture resource indicator must match the protected resource",
    )
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
        "profile": "offline-mcp-teaching-profile-v2",
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
