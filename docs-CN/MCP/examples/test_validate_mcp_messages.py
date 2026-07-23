"""Regression tests for the offline MCP teaching validator."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from validate_mcp_messages import (
    CLIENT_TO_SERVER,
    MAX_JSON_BYTES,
    MAX_JSON_DEPTH,
    MAX_SCHEMA_DEPTH,
    PROTOCOL_VERSION,
    SERVER_TO_CLIENT,
    McpSessionValidator,
    ValidationError,
    build_initialize_messages,
    classify_message,
    execute_case,
    load_json,
    loads_strict,
    validate_fixture,
    validate_tool_descriptor,
    validate_value,
)


FIXTURE_PATH = Path(__file__).with_name("mcp-cases.json")
SCRIPT_PATH = Path(__file__).with_name("validate_mcp_messages.py")
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
    validator = McpSessionValidator(
        PROTOCOL_VERSION,
        tool or FIXTURE["tool"],
        authorization=FIXTURE["authorization"],
    )
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
        changed["schema_version"] = 4
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

    def test_size_depth_and_file_error_boundaries_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValidationError, "nesting"):
            loads_strict("[" * (MAX_JSON_DEPTH + 1) + "0" + "]" * (MAX_JSON_DEPTH + 1))
        with self.assertRaisesRegex(ValidationError, "exceeds"):
            loads_strict(" " * (MAX_JSON_BYTES + 1))

        missing = Path("do-not-disclose-this-local-path") / "fixture.json"
        with self.assertRaises(ValidationError) as captured:
            load_json(missing)
        self.assertNotIn(str(missing), str(captured.exception))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized.json"
            path.write_bytes(b" " * (MAX_JSON_BYTES + 1))
            with self.assertRaisesRegex(ValidationError, "fixture exceeds"):
                load_json(path)


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

    def test_nonfinite_programmatic_number_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "must be a number"):
            validate_value({"type": "number"}, float("inf"))

    def test_overflowing_json_integer_is_rejected_as_a_number(self) -> None:
        with self.assertRaisesRegex(ValidationError, "must be a number"):
            validate_value({"type": "number"}, 10**400)

    def test_arbitrary_precision_integer_still_respects_numeric_bounds(self) -> None:
        with self.assertRaisesRegex(ValidationError, "above maximum"):
            validate_value({"type": "integer", "maximum": 100}, 10**400)

    def test_schema_depth_and_unsupported_keywords_are_rejected(self) -> None:
        nested: dict = {"type": "string"}
        for _ in range(MAX_SCHEMA_DEPTH + 1):
            nested = {
                "type": "object",
                "properties": {"child": nested},
                "additionalProperties": False,
            }
        tool = copy.deepcopy(FIXTURE["tool"])
        tool["inputSchema"] = nested
        with self.assertRaisesRegex(ValidationError, "schema depth"):
            validate_tool_descriptor(tool)

        tool = copy.deepcopy(FIXTURE["tool"])
        tool["inputSchema"]["properties"]["city"]["oneOf"] = [
            {"type": "string"}
        ]
        with self.assertRaisesRegex(ValidationError, "unsupported schema keywords"):
            validate_tool_descriptor(tool)

    def test_schema_rejects_enum_items_with_the_wrong_json_type(self) -> None:
        tool = copy.deepcopy(FIXTURE["tool"])
        tool["inputSchema"]["properties"]["unit"]["enum"] = [True]
        with self.assertRaisesRegex(ValidationError, "incompatible with declared type"):
            validate_tool_descriptor(tool)

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

    def test_message_cannot_mix_method_with_result(self) -> None:
        with self.assertRaisesRegex(ValidationError, "cannot mix"):
            classify_message(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "ping",
                    "result": {},
                }
            )

    def test_invalid_initialize_result_does_not_consume_pending_request(self) -> None:
        validator = McpSessionValidator(PROTOCOL_VERSION, FIXTURE["tool"])
        request, response, initialized = build_initialize_messages(
            PROTOCOL_VERSION,
            FIXTURE["client"],
            FIXTURE["server"],
        )
        validator.process(CLIENT_TO_SERVER, request)
        malformed = copy.deepcopy(response)
        malformed["result"]["serverInfo"] = {}
        with self.assertRaisesRegex(ValidationError, "serverInfo"):
            validator.process(SERVER_TO_CLIENT, malformed)
        self.assertEqual(1, len(validator.pending))

        validator.process(SERVER_TO_CLIENT, response)
        validator.process(CLIENT_TO_SERVER, initialized)
        self.assertEqual("ready", validator.state)

    def test_success_response_schema_is_bound_to_pending_method_atomically(self) -> None:
        validator = ready_validator()
        request = {"jsonrpc": "2.0", "id": 104, "method": "tools/list"}
        validator.process(CLIENT_TO_SERVER, request)

        with self.assertRaisesRegex(ValidationError, "tool descriptor"):
            validator.process(
                SERVER_TO_CLIENT,
                {"jsonrpc": "2.0", "id": 104, "result": {"tools": [{}]}},
            )
        self.assertEqual(1, len(validator.pending))

        validator.process(
            SERVER_TO_CLIENT,
            {
                "jsonrpc": "2.0",
                "id": 104,
                "result": {"tools": [copy.deepcopy(FIXTURE["tool"])]},
            },
        )
        self.assertEqual({}, validator.pending)

    def test_unimplemented_method_schema_is_rejected_before_pending_state(self) -> None:
        validator = ready_validator()
        with self.assertRaisesRegex(ValidationError, "not implemented"):
            validator.process(
                CLIENT_TO_SERVER,
                {"jsonrpc": "2.0", "id": 105, "method": "prompts/list"},
            )
        self.assertEqual({}, validator.pending)

    def test_tasks_list_validates_each_task_snapshot_before_consuming_pending(self) -> None:
        validator = ready_validator()
        request = {"jsonrpc": "2.0", "id": 106, "method": "tasks/list", "params": {}}
        validator.process(CLIENT_TO_SERVER, request)
        with self.assertRaisesRegex(ValidationError, "taskId required"):
            validator.process(
                SERVER_TO_CLIENT,
                {"jsonrpc": "2.0", "id": 106, "result": {"tasks": [{}]}},
            )
        self.assertEqual(1, len(validator.pending))

        validator.process(
            SERVER_TO_CLIENT,
            {
                "jsonrpc": "2.0",
                "id": 106,
                "result": {
                    "tasks": [
                        {
                            "taskId": "task-106",
                            "status": "working",
                            "createdAt": "2025-11-25T10:30:00Z",
                            "lastUpdatedAt": "2025-11-25T10:30:00Z",
                            "ttl": 60000,
                            "pollInterval": 5000,
                        }
                    ]
                },
            },
        )
        self.assertEqual({}, validator.pending)

    def test_task_snapshot_requires_ttl(self) -> None:
        validator = ready_validator()
        with self.assertRaisesRegex(ValidationError, "ttl required"):
            validator._validate_task(
                {
                    "taskId": "task-no-ttl",
                    "status": "working",
                    "createdAt": "2025-11-25T10:30:00Z",
                    "lastUpdatedAt": "2025-11-25T10:30:00Z",
                },
                "task",
            )

    def test_task_snapshot_rejects_null_poll_interval(self) -> None:
        validator = ready_validator()
        with self.assertRaisesRegex(ValidationError, "pollInterval"):
            validator._validate_task(
                {
                    "taskId": "task-null-poll",
                    "status": "working",
                    "createdAt": "2025-11-25T10:30:00Z",
                    "lastUpdatedAt": "2025-11-25T10:30:00Z",
                    "ttl": 60_000,
                    "pollInterval": None,
                },
                "task",
            )


def transport_context(
    *,
    subject: str = "alice",
    tenant: str = "tenant-a",
    scopes: list[str] | None = None,
    revision: str = "authz-v1",
    transport: str = "streamable_http",
    token_active: bool = True,
    token_audience: str | None = None,
    resource: str | None = None,
) -> dict:
    protected_resource = FIXTURE["authorization"]["protected_resource"]
    return {
        "transport": transport,
        "token_active": token_active,
        "token_audience": token_audience or protected_resource,
        "resource": resource or protected_resource,
        "subject": subject,
        "tenant": tenant,
        "scopes": scopes
        if scopes is not None
        else ["resources:list", "resources:read", "resources:subscribe"],
        "authorization_revision": revision,
    }


class ResourceContractTests(unittest.TestCase):
    def test_http_transport_binds_active_token_audience_and_resource(self) -> None:
        attempts = (
            (transport_context(token_active=False), "active access token"),
            (
                transport_context(token_audience="https://other.example.test/mcp"),
                "token audience",
            ),
            (
                transport_context(resource="https://other.example.test/mcp"),
                "resource indicator",
            ),
            (transport_context(transport="stdio"), "streamable_http"),
        )
        for request_id, (context, error) in enumerate(attempts, start=190):
            with self.subTest(error=error):
                validator = ready_validator()
                with self.assertRaisesRegex(ValidationError, error):
                    validator.process(
                        CLIENT_TO_SERVER,
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "method": "resources/list",
                        },
                        transport_context=context,
                    )

    def test_roots_never_substitute_for_resource_authorization(self) -> None:
        validator = ready_validator(
            client_capabilities={"roots": {"listChanged": True}},
            server_capabilities={"resources": {}},
        )
        with self.assertRaisesRegex(ValidationError, "transport_context"):
            validator.process(
                CLIENT_TO_SERVER,
                {"jsonrpc": "2.0", "id": 199, "method": "resources/list"},
            )

    def test_authorization_rejects_malformed_uri_and_rfc6570_variable_name(self) -> None:
        authorization = copy.deepcopy(FIXTURE["authorization"])
        authorization["revisions"]["authz-v1"]["resourceTemplates"][0][
            "uriTemplate"
        ] = "kb://tenant-a/docs/{bad%}"
        with self.assertRaisesRegex(ValidationError, "RFC 6570 variable name"):
            McpSessionValidator(
                PROTOCOL_VERSION,
                FIXTURE["tool"],
                authorization=authorization,
            )
        authorization = copy.deepcopy(FIXTURE["authorization"])
        authorization["revisions"]["authz-v1"]["resources"][0][
            "uri"
        ] = "kb://tenant-a\\handbook"
        with self.assertRaisesRegex(ValidationError, "RFC 3986 URI character set"):
            McpSessionValidator(
                PROTOCOL_VERSION,
                FIXTURE["tool"],
                authorization=authorization,
            )

    def test_valid_list_and_template_results_are_authorized(self) -> None:
        validator = ready_validator()
        context = transport_context()
        validator.process(
            CLIENT_TO_SERVER,
            {
                "jsonrpc": "2.0",
                "id": 200,
                "method": "resources/list",
                "params": {"cursor": "page-1"},
            },
            transport_context=context,
        )
        validator.process(
            SERVER_TO_CLIENT,
            {
                "jsonrpc": "2.0",
                "id": 200,
                "result": {
                    "resources": [
                        {
                            "uri": "kb://tenant-a/handbook",
                            "name": "handbook",
                            "title": "Course handbook",
                            "mimeType": "text/markdown",
                            "size": 42,
                        }
                    ],
                    "nextCursor": "page-2",
                },
            },
        )
        validator.process(
            CLIENT_TO_SERVER,
            {
                "jsonrpc": "2.0",
                "id": 201,
                "method": "resources/templates/list",
            },
            transport_context=context,
        )
        validator.process(
            SERVER_TO_CLIENT,
            {
                "jsonrpc": "2.0",
                "id": 201,
                "result": {
                    "resourceTemplates": [
                        {
                            "uriTemplate": "kb://tenant-a/docs/{doc_id}",
                            "name": "tenant-doc",
                            "mimeType": "text/markdown",
                        }
                    ]
                },
            },
        )

    def test_read_accepts_text_blob_and_explicit_child_uri(self) -> None:
        validator = ready_validator()
        validator.process(
            CLIENT_TO_SERVER,
            {
                "jsonrpc": "2.0",
                "id": 202,
                "method": "resources/read",
                "params": {"uri": "kb://tenant-a/handbook"},
            },
            transport_context=transport_context(),
        )
        validator.process(
            SERVER_TO_CLIENT,
            {
                "jsonrpc": "2.0",
                "id": 202,
                "result": {
                    "contents": [
                        {
                            "uri": "kb://tenant-a/handbook",
                            "mimeType": "text/markdown",
                            "text": "# Handbook",
                        },
                        {
                            "uri": "kb://tenant-a/handbook/chapter-1",
                            "mimeType": "application/octet-stream",
                            "blob": "aGVsbG8=",
                        },
                    ]
                },
            },
        )

    def test_read_rejects_invalid_base64_and_oversized_text(self) -> None:
        for request_id, content, error in (
            (
                203,
                {"uri": "kb://tenant-a/handbook", "blob": "not base64!"},
                "base64",
            ),
            (
                204,
                {"uri": "kb://tenant-a/handbook", "text": "x" * 65537},
                "size limit",
            ),
            (
                205,
                {"uri": "kb://tenant-a/handbook", "blob": "Zh=="},
                "canonical padded base64",
            ),
        ):
            with self.subTest(error=error):
                validator = ready_validator()
                validator.process(
                    CLIENT_TO_SERVER,
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "method": "resources/read",
                        "params": {"uri": "kb://tenant-a/handbook"},
                    },
                    transport_context=transport_context(),
                )
                with self.assertRaisesRegex(ValidationError, error):
                    validator.process(
                        SERVER_TO_CLIENT,
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {"contents": [content]},
                        },
                    )

    def test_read_rejects_aggregate_content_over_profile_limit(self) -> None:
        validator = ready_validator()
        validator.process(
            CLIENT_TO_SERVER,
            {
                "jsonrpc": "2.0",
                "id": 206,
                "method": "resources/read",
                "params": {"uri": "kb://tenant-a/handbook"},
            },
            transport_context=transport_context(scopes=["resources:read"]),
        )
        with self.assertRaisesRegex(ValidationError, "aggregate contents"):
            validator.process(
                SERVER_TO_CLIENT,
                {
                    "jsonrpc": "2.0",
                    "id": 206,
                    "result": {
                        "contents": [
                            {"uri": "kb://tenant-a/handbook", "text": "a" * 40000},
                            {
                                "uri": "kb://tenant-a/handbook/chapter-1",
                                "text": "b" * 40000,
                            },
                        ]
                    },
                },
            )

        validator = ready_validator()
        validator.process(
            CLIENT_TO_SERVER,
            {
                "jsonrpc": "2.0",
                "id": 2061,
                "method": "resources/read",
                "params": {"uri": "kb://tenant-a/handbook"},
            },
            transport_context=transport_context(scopes=["resources:read"]),
        )
        with self.assertRaisesRegex(ValidationError, "content item limit"):
            validator.process(
                SERVER_TO_CLIENT,
                {
                    "jsonrpc": "2.0",
                    "id": 2061,
                    "result": {
                        "contents": [
                            {"uri": "kb://tenant-a/handbook", "text": ""}
                            for _ in range(65)
                        ]
                    },
                },
            )

    def test_resource_methods_reject_unknown_method_and_bad_cursor(self) -> None:
        validator = ready_validator()
        with self.assertRaisesRegex(ValidationError, "unsupported resource method"):
            validator.process(
                CLIENT_TO_SERVER,
                {"jsonrpc": "2.0", "id": 207, "method": "resources/delete"},
                transport_context=transport_context(),
            )
        with self.assertRaisesRegex(ValidationError, "cursor"):
            validator.process(
                CLIENT_TO_SERVER,
                {
                    "jsonrpc": "2.0",
                    "id": 208,
                    "method": "resources/list",
                    "params": {"cursor": 1},
                },
                transport_context=transport_context(),
            )
        with self.assertRaisesRegex(ValidationError, "unknown keys"):
            validator.process(
                CLIENT_TO_SERVER,
                {
                    "jsonrpc": "2.0",
                    "id": 209,
                    "method": "resources/read",
                    "params": {
                        "uri": "kb://tenant-a/handbook",
                        "unexpected": True,
                    },
                },
                transport_context=transport_context(),
            )

    def test_authorization_rejects_tenant_scope_principal_and_stale_revision(self) -> None:
        attempts = (
            (transport_context(tenant="tenant-b"), "tenant"),
            (transport_context(scopes=["resources:list"]), "resources:read"),
            (transport_context(subject="unknown"), "principal"),
            (transport_context(revision="stale"), "authorization revision"),
        )
        for index, (context, error) in enumerate(attempts, start=207):
            with self.subTest(error=error):
                validator = ready_validator()
                with self.assertRaisesRegex(ValidationError, error):
                    validator.process(
                        CLIENT_TO_SERVER,
                        {
                            "jsonrpc": "2.0",
                            "id": index,
                            "method": "resources/read",
                            "params": {"uri": "kb://tenant-a/handbook"},
                        },
                        transport_context=context,
                    )

    def test_subscribe_state_changes_only_after_success(self) -> None:
        validator = ready_validator()
        context = transport_context()
        request = {
            "jsonrpc": "2.0",
            "id": 211,
            "method": "resources/subscribe",
            "params": {"uri": "kb://tenant-a/handbook"},
        }
        validator.process(CLIENT_TO_SERVER, request, transport_context=context)
        self.assertEqual(validator.subscriptions, {})
        validator.process(SERVER_TO_CLIENT, {"jsonrpc": "2.0", "id": 211, "result": {}})
        self.assertIn("kb://tenant-a/handbook", validator.subscriptions)

    def test_failed_subscribe_adds_nothing_and_failed_unsubscribe_keeps_state(self) -> None:
        validator = ready_validator()
        context = transport_context()
        validator.process(
            CLIENT_TO_SERVER,
            {
                "jsonrpc": "2.0",
                "id": 212,
                "method": "resources/subscribe",
                "params": {"uri": "kb://tenant-a/handbook"},
            },
            transport_context=context,
        )
        validator.process(
            SERVER_TO_CLIENT,
            {
                "jsonrpc": "2.0",
                "id": 212,
                "error": {"code": -32002, "message": "not available"},
            },
        )
        self.assertEqual(validator.subscriptions, {})

        validator.process(
            CLIENT_TO_SERVER,
            {
                "jsonrpc": "2.0",
                "id": 213,
                "method": "resources/subscribe",
                "params": {"uri": "kb://tenant-a/handbook"},
            },
            transport_context=context,
        )
        validator.process(SERVER_TO_CLIENT, {"jsonrpc": "2.0", "id": 213, "result": {}})
        validator.process(
            CLIENT_TO_SERVER,
            {
                "jsonrpc": "2.0",
                "id": 214,
                "method": "resources/unsubscribe",
                "params": {"uri": "kb://tenant-a/handbook"},
            },
            transport_context=context,
        )
        validator.process(
            SERVER_TO_CLIENT,
            {
                "jsonrpc": "2.0",
                "id": 214,
                "error": {"code": -32603, "message": "temporary failure"},
            },
        )
        self.assertIn("kb://tenant-a/handbook", validator.subscriptions)

    def test_duplicate_pending_unsubscribe_is_rejected(self) -> None:
        validator = ready_validator()
        context = transport_context(scopes=["resources:subscribe"])
        validator.process(
            CLIENT_TO_SERVER,
            {
                "jsonrpc": "2.0",
                "id": 2140,
                "method": "resources/subscribe",
                "params": {"uri": "kb://tenant-a/handbook"},
            },
            transport_context=context,
        )
        validator.process(
            SERVER_TO_CLIENT,
            {"jsonrpc": "2.0", "id": 2140, "result": {}},
        )
        first_unsubscribe = {
            "jsonrpc": "2.0",
            "id": 2141,
            "method": "resources/unsubscribe",
            "params": {"uri": "kb://tenant-a/handbook"},
        }
        validator.process(
            CLIENT_TO_SERVER,
            first_unsubscribe,
            transport_context=context,
        )
        with self.assertRaisesRegex(ValidationError, "pending unsubscription"):
            validator.process(
                CLIENT_TO_SERVER,
                {**first_unsubscribe, "id": 2142},
                transport_context=context,
            )

    def test_updated_allows_declared_child_but_not_prefix_collision(self) -> None:
        validator = ready_validator()
        context = transport_context()
        validator.process(
            CLIENT_TO_SERVER,
            {
                "jsonrpc": "2.0",
                "id": 215,
                "method": "resources/subscribe",
                "params": {"uri": "kb://tenant-a/handbook"},
            },
            transport_context=context,
        )
        validator.process(SERVER_TO_CLIENT, {"jsonrpc": "2.0", "id": 215, "result": {}})
        validator.process(
            SERVER_TO_CLIENT,
            {
                "jsonrpc": "2.0",
                "method": "notifications/resources/updated",
                "params": {"uri": "kb://tenant-a/handbook/chapter-1"},
            },
            transport_context=context,
        )
        with self.assertRaisesRegex(ValidationError, "active subscription"):
            validator.process(
                SERVER_TO_CLIENT,
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/resources/updated",
                    "params": {"uri": "kb://tenant-a/handbookish"},
                },
                transport_context=context,
            )

    def test_revision_change_invalidates_subscription_and_old_reread(self) -> None:
        validator = ready_validator()
        context = transport_context()
        validator.process(
            CLIENT_TO_SERVER,
            {
                "jsonrpc": "2.0",
                "id": 216,
                "method": "resources/subscribe",
                "params": {"uri": "kb://tenant-a/handbook"},
            },
            transport_context=context,
        )
        validator.process(SERVER_TO_CLIENT, {"jsonrpc": "2.0", "id": 216, "result": {}})
        validator.apply_control_event(
            {"type": "activate_authorization_revision", "revision": "authz-v2"}
        )
        self.assertEqual(validator.subscriptions, {})
        with self.assertRaisesRegex(ValidationError, "authorization revision"):
            validator.process(
                CLIENT_TO_SERVER,
                {
                    "jsonrpc": "2.0",
                    "id": 217,
                    "method": "resources/read",
                    "params": {"uri": "kb://tenant-a/handbook"},
                },
                transport_context=context,
            )

    def test_resource_list_changed_requires_its_subcapability(self) -> None:
        validator = ready_validator()
        validator.process(
            SERVER_TO_CLIENT,
            {"jsonrpc": "2.0", "method": "notifications/resources/list_changed"},
        )
        validator = ready_validator(server_capabilities={"resources": {}})
        with self.assertRaisesRegex(ValidationError, "resources.listChanged"):
            validator.process(
                SERVER_TO_CLIENT,
                {"jsonrpc": "2.0", "method": "notifications/resources/list_changed"},
            )


class FixtureCaseTests(unittest.TestCase):
    """One unittest per fixture case keeps every behavior visible in counts."""


class CliBoundaryTests(unittest.TestCase):
    def test_overflowing_json_integer_is_a_controlled_cli_error(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        task = next(
            step["message"]["params"]["task"]
            for case in changed["cases"]
            for step in case["steps"]
            if isinstance(step.get("message"), dict)
            and isinstance(step["message"].get("params"), dict)
            and isinstance(step["message"]["params"].get("task"), dict)
            and "ttl" in step["message"]["params"]["task"]
        )
        task["ttl"] = 10**400
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "overflow.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "-B", "-W", "error", str(SCRIPT_PATH), str(path)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        self.assertEqual(1, completed.returncode)
        self.assertIn("task.ttl must be a positive number", completed.stderr)
        self.assertNotIn("OverflowError", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)


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
