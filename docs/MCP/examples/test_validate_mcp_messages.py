"""Regression tests for the offline MCP teaching validator."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from validate_mcp_messages import (
    CLIENT_TO_SERVER,
    PROTOCOL_VERSION,
    SERVER_TO_CLIENT,
    McpSessionValidator,
    ValidationError,
    build_initialize_messages,
    execute_case,
    load_json,
    loads_strict,
    validate_fixture,
    validate_tool_descriptor,
    validate_value,
)


FIXTURE_PATH = Path(__file__).with_name("mcp-cases.json")
FIXTURE = load_json(FIXTURE_PATH)


def ready_validator(
    *,
    client_capabilities: dict | None = None,
    server_capabilities: dict | None = None,
    tool: dict | None = None,
) -> McpSessionValidator:
    client = copy.deepcopy(FIXTURE["client"])
    server = copy.deepcopy(FIXTURE["server"])
    if client_capabilities is not None:
        client["capabilities"] = client_capabilities
    if server_capabilities is not None:
        server["capabilities"] = server_capabilities
    validator = McpSessionValidator(PROTOCOL_VERSION, tool or FIXTURE["tool"])
    request, response, initialized = build_initialize_messages(PROTOCOL_VERSION, client, server)
    validator.process(CLIENT_TO_SERVER, request)
    validator.process(SERVER_TO_CLIENT, response)
    validator.process(CLIENT_TO_SERVER, initialized)
    return validator


class FixtureIntegrityTests(unittest.TestCase):
    def test_fixture_has_substantial_positive_and_negative_coverage(self) -> None:
        cases = FIXTURE["cases"]
        self.assertGreaterEqual(len(cases), 30)
        self.assertGreaterEqual(sum(case["expect"] == "pass" for case in cases), 8)
        self.assertGreaterEqual(sum(case["expect"] == "fail" for case in cases), 15)

    def test_fixture_case_names_are_unique(self) -> None:
        names = [case["name"] for case in FIXTURE["cases"]]
        self.assertEqual(len(names), len(set(names)))

    def test_whole_fixture_validates(self) -> None:
        results = validate_fixture(FIXTURE)
        self.assertEqual(len(results), len(FIXTURE["cases"]))

    def test_unknown_fixture_key_is_rejected(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["unexpected"] = True
        with self.assertRaisesRegex(ValidationError, "unknown keys"):
            validate_fixture(changed)

    def test_unknown_fixture_version_is_rejected(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["schema_version"] = 2
        with self.assertRaisesRegex(ValidationError, "schema_version"):
            validate_fixture(changed)


class StrictJsonTests(unittest.TestCase):
    def test_duplicate_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "duplicate JSON key"):
            loads_strict('{"id": 1, "id": 2}')

    def test_nan_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "non-finite"):
            loads_strict('{"value": NaN}')

    def test_infinity_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "non-finite"):
            loads_strict('{"value": Infinity}')

    def test_invalid_json_reports_line(self) -> None:
        with self.assertRaisesRegex(ValidationError, "invalid JSON at line"):
            loads_strict('{\n  "id":\n}')

    def test_normal_unicode_json_loads(self) -> None:
        self.assertEqual(loads_strict('{"城市": "上海"}'), {"城市": "上海"})


class SchemaAndToolTests(unittest.TestCase):
    def test_tool_name_with_space_is_rejected(self) -> None:
        tool = copy.deepcopy(FIXTURE["tool"])
        tool["name"] = "bad tool"
        with self.assertRaisesRegex(ValidationError, "tool name"):
            validate_tool_descriptor(tool)

    def test_required_schema_property_must_exist(self) -> None:
        tool = copy.deepcopy(FIXTURE["tool"])
        tool["inputSchema"]["required"] = ["missing"]
        with self.assertRaisesRegex(ValidationError, "unknown property"):
            validate_tool_descriptor(tool)

    def test_bool_is_not_an_integer(self) -> None:
        with self.assertRaisesRegex(ValidationError, "must be an integer"):
            validate_value({"type": "integer"}, True)

    def test_array_items_are_checked(self) -> None:
        with self.assertRaisesRegex(ValidationError, r"\$\[1\]"):
            validate_value({"type": "array", "items": {"type": "string"}}, ["ok", 2])

    def test_numeric_minimum_is_checked(self) -> None:
        with self.assertRaisesRegex(ValidationError, "below minimum"):
            validate_value({"type": "number", "minimum": 1}, 0.5)

    def test_task_required_tool_rejects_plain_call(self) -> None:
        tool = copy.deepcopy(FIXTURE["tool"])
        tool["execution"]["taskSupport"] = "required"
        validator = ready_validator(tool=tool)
        message = {
            "jsonrpc": "2.0",
            "id": 100,
            "method": "tools/call",
            "params": {"name": tool["name"], "arguments": {"city": "Shanghai"}},
        }
        with self.assertRaisesRegex(ValidationError, "requires task augmentation"):
            validator.process(CLIENT_TO_SERVER, message)

    def test_task_forbidden_tool_rejects_augmented_call(self) -> None:
        tool = copy.deepcopy(FIXTURE["tool"])
        tool["execution"]["taskSupport"] = "forbidden"
        validator = ready_validator(tool=tool)
        message = {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "tools/call",
            "params": {
                "name": tool["name"],
                "arguments": {"city": "Shanghai"},
                "task": {},
            },
        }
        with self.assertRaisesRegex(ValidationError, "tool forbids"):
            validator.process(CLIENT_TO_SERVER, message)


class SessionSemanticsTests(unittest.TestCase):
    def test_string_and_integer_ids_are_distinct(self) -> None:
        validator = ready_validator()
        validator.process(CLIENT_TO_SERVER, {"jsonrpc": "2.0", "id": 5, "method": "tools/list"})
        validator.process(CLIENT_TO_SERVER, {"jsonrpc": "2.0", "id": "5", "method": "tools/list"})
        self.assertEqual(len(validator.pending), 2)

    def test_peers_may_use_same_id_independently(self) -> None:
        validator = ready_validator()
        validator.process(CLIENT_TO_SERVER, {"jsonrpc": "2.0", "id": 6, "method": "tools/list"})
        validator.process(SERVER_TO_CLIENT, {"jsonrpc": "2.0", "id": 6, "method": "roots/list"})
        self.assertEqual(len(validator.pending), 2)

    def test_client_must_start_initialization(self) -> None:
        validator = McpSessionValidator(PROTOCOL_VERSION, FIXTURE["tool"])
        message = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        with self.assertRaisesRegex(ValidationError, "client must initiate"):
            validator.process(SERVER_TO_CLIENT, message)

    def test_unsupported_constructor_version_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, PROTOCOL_VERSION):
            McpSessionValidator("2024-11-05", FIXTURE["tool"])

    def test_server_selected_unsupported_version_is_rejected(self) -> None:
        validator = McpSessionValidator(PROTOCOL_VERSION, FIXTURE["tool"])
        request, response, _ = build_initialize_messages(PROTOCOL_VERSION, FIXTURE["client"], FIXTURE["server"])
        validator.process(CLIENT_TO_SERVER, request)
        response["result"]["protocolVersion"] = "2024-11-05"
        with self.assertRaisesRegex(ValidationError, "does not support"):
            validator.process(SERVER_TO_CLIENT, response)

    def test_http_url_elicitation_is_rejected_by_profile(self) -> None:
        validator = ready_validator()
        message = {
            "jsonrpc": "2.0",
            "id": 102,
            "method": "elicitation/create",
            "params": {
                "mode": "url",
                "message": "Open an external page.",
                "url": "http://example.com/connect",
                "elicitationId": "insecure-url",
            },
        }
        with self.assertRaisesRegex(ValidationError, "HTTPS"):
            validator.process(SERVER_TO_CLIENT, message)

    def test_empty_elicitation_capability_supports_form_for_compatibility(self) -> None:
        validator = ready_validator(client_capabilities={"elicitation": {}})
        message = {
            "jsonrpc": "2.0",
            "id": 103,
            "method": "elicitation/create",
            "params": {
                "message": "Choose a label.",
                "requestedSchema": {
                    "type": "object",
                    "properties": {"label": {"type": "string"}},
                    "required": ["label"],
                },
            },
        }
        validator.process(SERVER_TO_CLIENT, message)
        self.assertEqual(len(validator.pending), 1)

    def test_initialized_notification_cannot_come_from_server(self) -> None:
        validator = McpSessionValidator(PROTOCOL_VERSION, FIXTURE["tool"])
        request, response, initialized = build_initialize_messages(PROTOCOL_VERSION, FIXTURE["client"], FIXTURE["server"])
        validator.process(CLIENT_TO_SERVER, request)
        validator.process(SERVER_TO_CLIENT, response)
        with self.assertRaisesRegex(ValidationError, "must come from client"):
            validator.process(SERVER_TO_CLIENT, initialized)


class FixtureCaseTests(unittest.TestCase):
    """One unittest per fixture case keeps every behavior visible in counts."""


def _safe_test_name(name: str) -> str:
    return re_sub_non_identifier(name)


def re_sub_non_identifier(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value)


def _make_case_test(case: dict) -> callable:
    def test(self: FixtureCaseTests) -> None:
        result = execute_case(FIXTURE, case)
        expected_status = "passed" if case["expect"] == "pass" else "expected_failure"
        self.assertEqual(result["status"], expected_status)

    return test


for _index, _case in enumerate(FIXTURE["cases"], start=1):
    setattr(
        FixtureCaseTests,
        f"test_{_index:02d}_{_safe_test_name(_case['name'])}",
        _make_case_test(_case),
    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
