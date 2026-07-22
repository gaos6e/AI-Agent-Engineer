"""Red-team tests for the offline three-provider contract harness."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import tempfile
import unittest

import provider_contracts as contracts


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"


def fixture(name: str) -> dict[str, object]:
    return contracts.load_fixture(FIXTURES / name)


def openai_events() -> list[dict[str, object]]:
    return copy.deepcopy(fixture("openai_responses_tool_stream.json")["events"])


def anthropic_events() -> list[dict[str, object]]:
    return copy.deepcopy(fixture("anthropic_messages_tool_stream.json")["events"])


def gemini_events() -> list[dict[str, object]]:
    return copy.deepcopy(fixture("gemini_interactions_tool_stream.json")["events"])


def first_event(events: list[dict[str, object]], field: str, value: str) -> dict[str, object]:
    return next(event for event in events if event.get(field) == value)


def renumber_openai(events: list[dict[str, object]]) -> list[dict[str, object]]:
    for sequence, event in enumerate(events, start=1):
        event["sequence_number"] = sequence
    return events


def openai_parallel_events() -> list[dict[str, object]]:
    base = openai_events()
    created = base[:3]
    added_b = {
        "type": "response.output_item.added",
        "output_index": 1,
        "item": {
            "type": "function_call",
            "id": "item-B",
            "call_id": "call-B",
            "name": "lookup_customer",
            "arguments": "",
        },
    }
    delta_a_1 = copy.deepcopy(base[3])
    delta_a_2 = copy.deepcopy(base[4])
    delta_b = {
        "type": "response.function_call_arguments.delta",
        "item_id": "item-B",
        "output_index": 1,
        "delta": "{\"customer_ref\":\"C-9\"}",
    }
    done_b = {
        "type": "response.function_call_arguments.done",
        "item_id": "item-B",
        "output_index": 1,
        "name": "lookup_customer",
        "arguments": "{\"customer_ref\":\"C-9\"}",
    }
    item_b = {
        "type": "function_call",
        "id": "item-B",
        "call_id": "call-B",
        "name": "lookup_customer",
        "arguments": "{\"customer_ref\":\"C-9\"}",
        "status": "completed",
    }
    item_done_b = {
        "type": "response.output_item.done",
        "output_index": 1,
        "item": copy.deepcopy(item_b),
    }
    done_a = copy.deepcopy(base[5])
    item_done_a = copy.deepcopy(base[6])
    terminal = copy.deepcopy(base[7])
    terminal["response"]["output"] = [
        copy.deepcopy(item_done_a["item"]),
        copy.deepcopy(item_b),
    ]
    return renumber_openai(
        created
        + [added_b, delta_a_1, delta_b, delta_a_2, done_b, item_done_b, done_a, item_done_a, terminal]
    )


def openai_with_reasoning_events() -> list[dict[str, object]]:
    events = openai_events()
    for event in events:
        if event["type"].startswith("response.function_call_arguments"):
            event["output_index"] = 1
        elif event["type"] in {"response.output_item.added", "response.output_item.done"}:
            event["output_index"] = 1
    reasoning = {
        "type": "reasoning",
        "id": "reasoning-A",
        "summary": [],
    }
    events.insert(
        2,
        {
            "type": "response.output_item.added",
            "sequence_number": 0,
            "output_index": 0,
            "item": copy.deepcopy(reasoning),
        },
    )
    function_done = next(
        index for index, event in enumerate(events) if event["type"] == "response.output_item.done"
    )
    events.insert(
        function_done,
        {
            "type": "response.output_item.done",
            "sequence_number": 0,
            "output_index": 0,
            "item": copy.deepcopy(reasoning),
        },
    )
    events[-1]["response"]["output"].insert(0, copy.deepcopy(reasoning))
    return renumber_openai(events)


def anthropic_two_call_events() -> list[dict[str, object]]:
    events = anthropic_events()
    insert_at = next(
        index
        for index, envelope in enumerate(events)
        if envelope["event"] == "message_delta"
    )
    extra = [
        {
            "event": "content_block_start",
            "data": {
                "type": "content_block_start",
                "index": 2,
                "content_block": {
                    "type": "tool_use",
                    "id": "tool-use-B",
                    "name": "lookup_customer",
                    "input": {},
                },
            },
        },
        {
            "event": "content_block_delta",
            "data": {
                "type": "content_block_delta",
                "index": 2,
                "delta": {
                    "type": "input_json_delta",
                    "partial_json": "{\"customer_ref\":\"C-9\"}",
                },
            },
        },
        {
            "event": "content_block_stop",
            "data": {"type": "content_block_stop", "index": 2},
        },
    ]
    events[insert_at:insert_at] = extra
    return events


def anthropic_extended_mixed_events() -> list[dict[str, object]]:
    events = anthropic_events()
    for envelope in events:
        data = envelope.get("data")
        if isinstance(data, dict) and isinstance(data.get("index"), int):
            data["index"] += 2
    extended = [
        {
            "event": "content_block_start",
            "data": {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "thinking", "thinking": "", "signature": ""},
            },
        },
        {
            "event": "content_block_delta",
            "data": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "thinking_delta", "thinking": "fixture summary"},
            },
        },
        {
            "event": "content_block_delta",
            "data": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "signature_delta", "signature": "opaque-signature"},
            },
        },
        {
            "event": "content_block_stop",
            "data": {"type": "content_block_stop", "index": 0},
        },
        {
            "event": "content_block_start",
            "data": {
                "type": "content_block_start",
                "index": 1,
                "content_block": {"type": "redacted_thinking", "data": "opaque-data"},
            },
        },
        {
            "event": "content_block_stop",
            "data": {"type": "content_block_stop", "index": 1},
        },
    ]
    events[2:2] = extended
    message_delta = next(
        index for index, envelope in enumerate(events) if envelope["event"] == "message_delta"
    )
    server_tool = [
        {
            "event": "content_block_start",
            "data": {
                "type": "content_block_start",
                "index": 4,
                "content_block": {
                    "type": "server_tool_use",
                    "id": "server-tool-A",
                    "name": "web_search",
                    "input": {},
                },
            },
        },
        {
            "event": "content_block_delta",
            "data": {
                "type": "content_block_delta",
                "index": 4,
                "delta": {
                    "type": "input_json_delta",
                    "partial_json": '{"query":"fixture"}',
                },
            },
        },
        {
            "event": "content_block_stop",
            "data": {"type": "content_block_stop", "index": 4},
        },
    ]
    events[message_delta:message_delta] = server_tool
    return events


def gemini_parallel_events() -> list[dict[str, object]]:
    events = gemini_events()
    events.insert(
        2,
        {
            "event_type": "step.start",
            "event_id": "event-B-start",
            "index": 1,
            "step": {
                "type": "function_call",
                "arguments": {},
                "id": "call-B",
                "name": "lookup_customer",
            },
        },
    )
    stop_a = next(
        index for index, event in enumerate(events) if event["event_type"] == "step.stop"
    )
    events[stop_a + 1 : stop_a + 1] = [
        {
            "event_type": "step.delta",
            "event_id": "event-B-delta",
            "index": 1,
            "delta": {
                "type": "arguments_delta",
                "arguments": "{\"customer_ref\":\"C-9\"}",
            },
        },
        {
            "event_type": "step.stop",
            "event_id": "event-B-stop",
            "index": 1,
        },
    ]
    return events


def gemini_with_thought_events() -> list[dict[str, object]]:
    events = gemini_events()
    events.insert(
        1,
        {
            "event_type": "step.start",
            "event_id": "event-thought-start",
            "index": 17,
            "step": {"type": "thought", "summary": []},
        },
    )
    function_stop = next(
        index
        for index, event in enumerate(events)
        if event["event_type"] == "step.stop" and event["index"] == 0
    )
    events[function_stop + 1 : function_stop + 1] = [
        {
            "event_type": "step.delta",
            "event_id": "event-thought-summary",
            "index": 17,
            "delta": {
                "type": "thought_summary",
                "content": {"type": "text", "text": "fixture summary"},
            },
        },
        {
            "event_type": "step.delta",
            "event_id": "event-thought-signature",
            "index": 17,
            "delta": {
                "type": "thought_signature",
                "signature": "opaque-signature",
            },
        },
        {
            "event_type": "step.stop",
            "event_id": "event-thought-stop",
            "index": 17,
        },
    ]
    return events


TOOLS = [
    {
        "type": "function",
        "name": "lookup_order",
        "description": "Look up one order.",
        "parameters": {
            "type": "object",
            "properties": {"order_ref": {"type": "string"}},
            "required": ["order_ref"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]
ANTHROPIC_TOOLS = [
    {
        "name": "lookup_order",
        "description": "Look up one order.",
        "input_schema": {
            "type": "object",
            "properties": {"order_ref": {"type": "string"}},
            "required": ["order_ref"],
            "additionalProperties": False,
        },
    },
    {
        "name": "lookup_customer",
        "description": "Look up one customer.",
        "input_schema": {
            "type": "object",
            "properties": {"customer_ref": {"type": "string"}},
            "required": ["customer_ref"],
            "additionalProperties": False,
        },
    }
]
ANTHROPIC_CONTROLS = {
    "tool_choice": {"type": "auto"},
    "temperature": 0,
    "service_tier": "auto",
}
GEMINI_TOOLS = [
    {
        "type": "function",
        "name": "lookup_order",
        "description": "Look up one order.",
        "parameters": {
            "type": "object",
            "properties": {"order_ref": {"type": "string"}},
            "required": ["order_ref"],
            "additionalProperties": False,
        },
    }
]
GEMINI_USER_STEPS = [
    {
        "type": "user_input",
        "content": [{"type": "text", "text": "Where is A-17?"}],
    }
]
GEMINI_JSON_RESPONSE_FORMAT = {
    "type": "text",
    "mime_type": "application/json",
    "schema": {
        "type": "object",
        "properties": {"status": {"type": "string"}},
        "required": ["status"],
    },
}
OPENAI_CONTROLS = {
    "tool_choice": "auto",
    "parallel_tool_calls": False,
    "max_output_tokens": 512,
}
RESULT_A = contracts.ModelVisibleToolResult("call-A", '{"status":"shipped"}')


class FixtureTests(unittest.TestCase):
    def test_all_golden_fixtures_have_strict_current_provenance(self) -> None:
        names = (
            "openai_responses_tool_stream.json",
            "anthropic_messages_tool_stream.json",
            "gemini_interactions_tool_stream.json",
        )
        profiles = []
        for name in names:
            with self.subTest(name=name):
                loaded = fixture(name)
                self.assertEqual(contracts.SOURCE_CHECKED, loaded["source_checked"])
                self.assertTrue(all(url.startswith("https://") for url in loaded["source_urls"]))
                profiles.append((loaded["provider"], loaded["api_family"]))
        self.assertEqual(3, len(set(profiles)))

    def write_bad_fixture(self, text: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "bad.json"
        path.write_text(text, encoding="utf-8")
        return path

    def test_duplicate_json_field_is_rejected(self) -> None:
        path = self.write_bad_fixture('{"schema_version":1,"schema_version":2}')
        with self.assertRaisesRegex(contracts.FixtureError, "duplicate"):
            contracts.load_fixture(path)

    def test_non_finite_json_is_rejected(self) -> None:
        path = self.write_bad_fixture('{"value":NaN}')
        with self.assertRaisesRegex(contracts.FixtureError, "non-finite"):
            contracts.load_fixture(path)

    def test_utf8_bom_is_not_silently_accepted(self) -> None:
        valid = (FIXTURES / "openai_responses_tool_stream.json").read_text(encoding="utf-8")
        path = self.write_bad_fixture("\ufeff" + valid)
        with self.assertRaises(contracts.FixtureError):
            contracts.load_fixture(path)

    def test_invalid_utf8_bytes_are_rejected(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "invalid-utf8.json"
        path.write_bytes(b"\xff\xfe")
        with self.assertRaisesRegex(contracts.FixtureError, "cannot read"):
            contracts.load_fixture(path)

    def test_json_depth_and_collection_limits_are_enforced(self) -> None:
        deep: object = None
        for _ in range(contracts.MAX_JSON_DEPTH + 2):
            deep = [deep]
        with self.assertRaisesRegex(contracts.ProviderContractError, "depth"):
            contracts._validate_json_domain(deep)  # type: ignore[attr-defined]
        with self.assertRaisesRegex(contracts.ProviderContractError, "too long"):
            contracts._validate_json_domain(  # type: ignore[attr-defined]
                [None] * (contracts.MAX_COLLECTION_ITEMS + 1)
            )

    def test_stream_event_and_aggregate_fragment_limits_are_enforced(self) -> None:
        events = [
            {"event_type": "provider.notice"}
            for _ in range(contracts.MAX_STREAM_EVENTS + 1)
        ]
        with self.assertRaisesRegex(contracts.ProtocolError, "exceeds"):
            contracts.parse_gemini_interactions_stream(events)

        events = openai_events()
        events[3]["delta"] = "a" * 60_000
        events[4]["delta"] = "b" * 60_000
        with self.assertRaisesRegex(contracts.ProtocolError, "exceeds"):
            contracts.parse_openai_responses_stream(events)

    def test_fixture_root_is_exact(self) -> None:
        changed = fixture("openai_responses_tool_stream.json")
        changed["unreviewed"] = True
        errors = contracts.validate_fixture(changed)
        self.assertTrue(any("extra" in error for error in errors))

    def test_fixture_profile_version_and_layer_are_bound(self) -> None:
        changed = fixture("gemini_interactions_tool_stream.json")
        changed["api_version"] = "v1beta"
        changed["fixture_layer"] = "wire-sse-envelope"
        changed["contract_revision"] = "unreviewed"
        changed["sdk_baseline"] = "unreviewed"
        errors = contracts.validate_fixture(changed)
        self.assertTrue(any("api_version" in error for error in errors))
        self.assertTrue(any("fixture_layer" in error for error in errors))
        self.assertTrue(any("contract_revision" in error for error in errors))
        self.assertTrue(any("sdk_baseline" in error for error in errors))

        changed = fixture("gemini_interactions_tool_stream.json")
        changed["provider"] = []
        changed["source_urls"] = [[]]
        errors = contracts.validate_fixture(changed)
        self.assertTrue(any("provider" in error for error in errors))
        self.assertTrue(any("source_urls[0]" in error for error in errors))

    def test_fixture_sources_must_be_https_and_events_nonempty(self) -> None:
        changed = fixture("anthropic_messages_tool_stream.json")
        changed["source_urls"] = ["http://example.test/source"]
        changed["events"] = []
        errors = contracts.validate_fixture(changed)
        self.assertTrue(any("HTTPS" in error for error in errors))
        self.assertTrue(any("events" in error for error in errors))

        changed = fixture("anthropic_messages_tool_stream.json")
        changed["source_urls"] = ["https://secret@example.test/source"]
        errors = contracts.validate_fixture(changed)
        self.assertTrue(any("userinfo" in error for error in errors))

        changed = fixture("anthropic_messages_tool_stream.json")
        changed["source_urls"] = ["https://["]
        errors = contracts.validate_fixture(changed)
        self.assertTrue(any("valid URL" in error for error in errors))

    def test_fixture_sources_are_bound_to_official_provider_hosts(self) -> None:
        changed = fixture("openai_responses_tool_stream.json")
        changed["source_urls"] = [
            "https://developers.openai.com.evil.example/openai-reference"
        ]
        errors = contracts.validate_fixture(changed)
        self.assertTrue(any("approved source host" in error for error in errors))

        changed["source_urls"] = [
            "https://github.com/unrelated/project/releases/tag/v1"
        ]
        errors = contracts.validate_fixture(changed)
        self.assertTrue(any("approved SDK repository" in error for error in errors))

        changed["source_urls"] = [
            "https://github.com/openai/openai-python"
        ]
        self.assertEqual([], contracts.validate_fixture(changed))

        changed["source_urls"] = [
            "https://developers.openai.com:8443/api/docs/guides/function-calling"
        ]
        errors = contracts.validate_fixture(changed)
        self.assertTrue(any("default HTTPS port" in error for error in errors))

        changed["source_urls"] = ["http://localhost:8765/local-fixture"]
        errors = contracts.validate_fixture(changed)
        self.assertTrue(any("HTTPS" in error for error in errors))
        self.assertEqual(
            [], contracts.validate_fixture(changed, allow_local_source_urls=True)
        )
        local_path = self.write_bad_fixture(json.dumps(changed))
        with self.assertRaisesRegex(contracts.FixtureError, "HTTPS"):
            contracts.load_fixture(local_path)
        loaded = contracts.load_fixture(
            local_path, allow_local_source_urls=True
        )
        self.assertEqual(changed, loaded)

        with self.assertRaisesRegex(TypeError, "must be a boolean"):
            contracts.validate_fixture(changed, allow_local_source_urls=1)  # type: ignore[arg-type]

    def test_github_source_paths_reject_ambiguous_or_escaping_segments(self) -> None:
        escaping_suffixes = (
            "/../evil",
            "/%2e%2e/evil",
            "//../evil",
            "/%2f..%2fevil",
            "/%5c..%5cevil",
            "/..%5cevil",
            "/..\\evil",
            "/%252e%252e/evil",
            "/%252f..%252fevil",
            "/%ZZ/evil",
            "/%c0%af/evil",
        )
        for suffix in escaping_suffixes:
            with self.subTest(suffix=suffix):
                changed = fixture("openai_responses_tool_stream.json")
                changed["source_urls"] = [
                    "https://github.com/openai/openai-python" + suffix
                ]
                errors = contracts.validate_fixture(changed)
                self.assertTrue(
                    any("approved SDK repository" in error for error in errors),
                    errors,
                )

        changed = fixture("openai_responses_tool_stream.json")
        changed["source_urls"] = [
            "https://github.com/openai/openai-python/blob/main/README%2Emd"
        ]
        self.assertEqual([], contracts.validate_fixture(changed))


class OpenAIResponsesTests(unittest.TestCase):
    def test_golden_stream_commits_call_only_after_completed(self) -> None:
        turn = contracts.parse_openai_responses_stream(openai_events())
        self.assertEqual("response-A", turn.response_id)
        self.assertEqual("completed", turn.terminal_status)
        self.assertEqual({"order_ref": "A-17"}, turn.calls[0].arguments)
        self.assertEqual("call-A", turn.calls[0].call_id)
        self.assertEqual(8, turn.last_sequence_number)

    def test_extra_provider_fields_are_forward_compatible(self) -> None:
        events = openai_events()
        events[3]["new_optional_field"] = {"kept": True}
        turn = contracts.parse_openai_responses_stream(events)
        self.assertEqual(1, len(turn.calls))

    def test_direct_caller_is_preserved_while_programmatic_and_namespace_fail_closed(self) -> None:
        events = openai_events()
        for event in events:
            if event["type"] in {"response.output_item.added", "response.output_item.done"}:
                event["item"]["caller"] = {"type": "direct"}
        events[-1]["response"]["output"][0]["caller"] = {"type": "direct"}
        turn = contracts.parse_openai_responses_stream(events)
        body = contracts.build_openai_responses_continuation(
            turn,
            [RESULT_A],
            model="m",
            instructions="i",
            tools=TOOLS,
            previous_response_was_stored=True,
            store=True,
            request_controls=OPENAI_CONTROLS,
        )
        self.assertEqual({"type": "direct"}, body["input"][0]["caller"])

        for field, value in (
            ("caller", {"type": "program", "caller_id": "program-A"}),
            ("namespace", "orders"),
        ):
            events = openai_events()
            events[2]["item"][field] = value
            with self.subTest(field=field):
                with self.assertRaises(contracts.UnsupportedProviderState):
                    contracts.parse_openai_responses_stream(events)

    def test_unknown_semantic_event_is_preserved_but_not_a_terminal(self) -> None:
        events = openai_events()
        events.insert(-1, {"type": "response.vendor_telemetry", "sequence_number": 0, "data": 1})
        turn = contracts.parse_openai_responses_stream(renumber_openai(events))
        self.assertEqual("response.vendor_telemetry", turn.unknown_events[0]["type"])

    def test_sequence_must_strictly_increase(self) -> None:
        events = openai_events()
        events[4]["sequence_number"] = events[3]["sequence_number"]
        with self.assertRaisesRegex(contracts.ProtocolError, "strictly increasing"):
            contracts.parse_openai_responses_stream(events)

    def test_stream_must_begin_with_created(self) -> None:
        with self.assertRaisesRegex(contracts.ProtocolError, "before created"):
            contracts.parse_openai_responses_stream(openai_events()[1:])

    def test_in_progress_status_and_all_item_lifecycles_are_bound(self) -> None:
        events = openai_events()
        events[1]["response"]["status"] = "failed"
        with self.assertRaisesRegex(contracts.ProtocolError, "invalid status"):
            contracts.parse_openai_responses_stream(events)

        events = openai_events()
        events.insert(
            -1,
            {
                "type": "response.output_item.done",
                "sequence_number": 0,
                "output_index": 1,
                "item": {"type": "message"},
            },
        )
        with self.assertRaisesRegex(contracts.ProtocolError, "no matching added"):
            contracts.parse_openai_responses_stream(renumber_openai(events))

        events = openai_events()
        events[2] = {
            "type": "response.output_item.added",
            "sequence_number": events[2]["sequence_number"],
            "output_index": 0,
            "item": {"type": "message"},
        }
        events[6] = {
            "type": "response.output_item.done",
            "sequence_number": events[6]["sequence_number"],
            "output_index": 0,
            "item": {"type": "reasoning"},
        }
        del events[3:6]
        with self.assertRaisesRegex(contracts.ProtocolError, "changed the added item type"):
            contracts.parse_openai_responses_stream(renumber_openai(events))

        events = openai_with_reasoning_events()
        terminal = next(event for event in events if event["type"] == "response.completed")
        terminal["response"]["output"][0]["summary"] = [
            {"type": "text", "text": "tampered"}
        ]
        with self.assertRaisesRegex(contracts.ProtocolError, "completed output item"):
            contracts.parse_openai_responses_stream(events)

    def test_argument_event_must_match_item_and_index(self) -> None:
        for field, value in (("item_id", "wrong-item"), ("output_index", 3)):
            events = openai_events()
            first_event(events, "type", "response.function_call_arguments.delta")[field] = value
            with self.subTest(field=field):
                with self.assertRaisesRegex(contracts.ProtocolError, "match an open call"):
                    contracts.parse_openai_responses_stream(events)

    def test_argument_done_must_equal_all_deltas(self) -> None:
        events = openai_events()
        first_event(events, "type", "response.function_call_arguments.done")["arguments"] = '{}'
        with self.assertRaisesRegex(contracts.ProtocolError, "do not match"):
            contracts.parse_openai_responses_stream(events)

    def test_arguments_are_strict_json_objects(self) -> None:
        cases = (
            ('{"order_ref":"A","order_ref":"B"}', "duplicate"),
            ('["A-17"]', "object"),
            ('{"order_ref":NaN}', "non-finite"),
            (" " * (contracts.MAX_STRING_CHARS + 1) + "{}", "too long"),
        )
        for encoded, message in cases:
            events = openai_events()
            deltas = [
                event
                for event in events
                if event["type"] == "response.function_call_arguments.delta"
            ]
            deltas[0]["delta"] = encoded
            deltas[1]["delta"] = ""
            first_event(events, "type", "response.function_call_arguments.done")["arguments"] = encoded
            first_event(events, "type", "response.output_item.done")["item"]["arguments"] = encoded
            events[-1]["response"]["output"][0]["arguments"] = encoded
            with self.subTest(encoded=encoded):
                with self.assertRaisesRegex(contracts.ProviderContractError, message):
                    contracts.parse_openai_responses_stream(events)

    def test_output_item_done_cannot_change_call_identity(self) -> None:
        events = openai_events()
        first_event(events, "type", "response.output_item.done")["item"]["call_id"] = "other-call"
        with self.assertRaisesRegex(contracts.ProtocolError, "identity"):
            contracts.parse_openai_responses_stream(events)

        events = openai_events()
        first_event(events, "type", "response.output_item.done")["item"] = {
            "type": "message",
            "id": "message-A",
        }
        with self.assertRaisesRegex(contracts.ProtocolError, "item type"):
            contracts.parse_openai_responses_stream(events)

        events = openai_events()
        events.insert(
            2,
            {
                "type": "response.output_item.added",
                "sequence_number": 0,
                "output_index": 0,
                "item": {"type": "message", "id": "message-A"},
            },
        )
        with self.assertRaisesRegex(contracts.ProtocolError, "added twice"):
            contracts.parse_openai_responses_stream(renumber_openai(events))

    def test_terminal_output_cannot_change_or_omit_observed_call(self) -> None:
        events = openai_events()
        events[-1]["response"]["output"][0]["call_id"] = "other-call"
        with self.assertRaisesRegex(contracts.ProtocolError, "terminal output changed"):
            contracts.parse_openai_responses_stream(events)

        events = openai_events()
        events[-1]["response"]["output"] = []
        with self.assertRaisesRegex(contracts.ProtocolError, "omitted"):
            contracts.parse_openai_responses_stream(events)

        events = openai_events()
        events[-1]["response"].pop("output")
        with self.assertRaisesRegex(contracts.ProtocolError, "must be an array"):
            contracts.parse_openai_responses_stream(events)

    def test_output_item_cannot_finish_before_arguments_done(self) -> None:
        events = [
            event
            for event in openai_events()
            if event["type"] != "response.function_call_arguments.done"
        ]
        with self.assertRaisesRegex(contracts.ProtocolError, "before arguments.done"):
            contracts.parse_openai_responses_stream(renumber_openai(events))

    def test_eof_is_not_success(self) -> None:
        with self.assertRaisesRegex(contracts.ProtocolError, "without a completed terminal"):
            contracts.parse_openai_responses_stream(openai_events()[:-1])

    def test_incomplete_and_failed_terminal_never_release_calls(self) -> None:
        for event_type, status, detail_field, detail, category in (
            (
                "response.incomplete",
                "incomplete",
                "incomplete_details",
                {"reason": "max_output_tokens"},
                "incomplete:max_output_tokens",
            ),
            (
                "response.failed",
                "failed",
                "error",
                {"code": "server_error", "message": "redacted"},
                "failed:server_error",
            ),
        ):
            events = openai_events()
            terminal = events[-1]
            terminal["type"] = event_type
            terminal["response"]["status"] = status
            terminal["response"][detail_field] = detail
            with self.subTest(event_type=event_type):
                with self.assertRaises(contracts.ProviderStreamError) as captured:
                    contracts.parse_openai_responses_stream(events)
                self.assertEqual(category, captured.exception.category)

        events = openai_events()
        events[-1]["type"] = "response.failed"
        with self.assertRaisesRegex(contracts.ProtocolError, "disagrees"):
            contracts.parse_openai_responses_stream(events)

    def test_in_band_error_is_not_success(self) -> None:
        events = openai_events()
        events[-1] = {
            "type": "error",
            "sequence_number": 8,
            "code": "stream_error",
            "message": "connection lost",
            "param": None,
        }
        with self.assertRaises(contracts.ProviderStreamError) as captured:
            contracts.parse_openai_responses_stream(events)
        self.assertEqual("response-A", captured.exception.turn_id)

    def test_event_after_terminal_is_rejected(self) -> None:
        events = openai_events() + [
            {"type": "response.vendor_telemetry", "sequence_number": 9}
        ]
        with self.assertRaisesRegex(contracts.ProtocolError, "after terminal"):
            contracts.parse_openai_responses_stream(events)

    def test_parallel_argument_deltas_are_keyed_by_item_and_index(self) -> None:
        turn = contracts.parse_openai_responses_stream(openai_parallel_events())
        self.assertEqual(["call-A", "call-B"], [call.call_id for call in turn.calls])
        self.assertEqual({"customer_ref": "C-9"}, turn.calls[1].arguments)

    def test_response_completed_with_call_is_not_mislabeled_final_text(self) -> None:
        turn = contracts.parse_openai_responses_stream(openai_events())
        self.assertEqual("function_call", turn.raw_output[0]["type"])
        self.assertFalse(any(item.get("type") == "message" for item in turn.raw_output))

    def test_opaque_ids_do_not_require_documentation_example_prefixes(self) -> None:
        events = openai_events()
        for event in events:
            if isinstance(event.get("response"), dict):
                event["response"]["id"] = "opaque-response-id"
        turn = contracts.parse_openai_responses_stream(events)
        self.assertEqual("opaque-response-id", turn.response_id)


class AnthropicMessagesTests(unittest.TestCase):
    def test_golden_stream_preserves_ordered_assistant_blocks(self) -> None:
        turn = contracts.parse_anthropic_messages_stream(anthropic_events())
        self.assertEqual("tool_use", turn.stop_reason)
        self.assertEqual(["text", "tool_use"], [block["type"] for block in turn.assistant_content])
        self.assertEqual({"order_ref": "A-17"}, turn.calls[0].input)
        self.assertEqual(28, turn.usage["output_tokens"])

    def test_ping_and_empty_partial_json_are_valid(self) -> None:
        turn = contracts.parse_anthropic_messages_stream(anthropic_events())
        self.assertEqual(1, len(turn.calls))
        self.assertEqual((), turn.unknown_events)

    def test_unknown_top_level_event_is_preserved(self) -> None:
        events = anthropic_events()
        events.insert(2, {"event": "vendor_notice", "data": {"type": "vendor_notice", "x": 1}})
        turn = contracts.parse_anthropic_messages_stream(events)
        self.assertEqual("vendor_notice", turn.unknown_events[0]["event"])

    def test_server_side_fallback_block_fails_closed_until_supported(self) -> None:
        events = anthropic_events()
        events[2]["data"]["content_block"] = {
            "type": "fallback",
            "from": {"model": "requested-model"},
            "to": {"model": "fallback-model"},
        }
        with self.assertRaisesRegex(
            contracts.UnsupportedProviderState, "unsupported Anthropic content block"
        ):
            contracts.parse_anthropic_messages_stream(events)

    def test_sse_event_name_must_match_data_type(self) -> None:
        events = anthropic_events()
        events[1]["data"]["type"] = "not_ping"
        with self.assertRaisesRegex(contracts.ProtocolError, "does not match"):
            contracts.parse_anthropic_messages_stream(events)

    def test_delta_cannot_arrive_without_open_block(self) -> None:
        events = anthropic_events()
        delta = copy.deepcopy(events[3])
        events.insert(1, delta)
        with self.assertRaisesRegex(contracts.ProtocolError, "without an open block"):
            contracts.parse_anthropic_messages_stream(events)

    def test_content_blocks_must_not_overlap(self) -> None:
        events = anthropic_events()
        events.insert(3, copy.deepcopy(events[5]))
        with self.assertRaisesRegex(contracts.ProtocolError, "must not overlap"):
            contracts.parse_anthropic_messages_stream(events)

        events = anthropic_events()
        message_delta = events.pop(-2)
        events.insert(2, message_delta)
        with self.assertRaisesRegex(contracts.ProtocolError, "after message_delta"):
            contracts.parse_anthropic_messages_stream(events)

    def test_delta_and_stop_index_are_bound(self) -> None:
        for envelope_index in (7, 9):
            events = anthropic_events()
            events[envelope_index]["data"]["index"] = 9
            with self.subTest(envelope_index=envelope_index):
                with self.assertRaisesRegex(contracts.ProtocolError, "index changed"):
                    contracts.parse_anthropic_messages_stream(events)

    def test_tool_input_is_parsed_only_after_block_stop(self) -> None:
        events = anthropic_events()
        events[8]["data"]["delta"]["partial_json"] = "ref\":"
        with self.assertRaisesRegex(contracts.ProtocolError, "strict JSON"):
            contracts.parse_anthropic_messages_stream(events)

    def test_duplicate_and_non_object_tool_json_are_rejected(self) -> None:
        for encoded, message in (
            ('{"x":1,"x":2}', "duplicate"),
            ('[1,2]', "object"),
            ("[" * 100 + "0" + "]" * 100, "depth"),
        ):
            events = anthropic_events()
            events[6]["data"]["delta"]["partial_json"] = encoded
            events[7]["data"]["delta"]["partial_json"] = ""
            events[8]["data"]["delta"]["partial_json"] = ""
            with self.subTest(encoded=encoded):
                with self.assertRaisesRegex(contracts.ProviderContractError, message):
                    contracts.parse_anthropic_messages_stream(events)

    def test_eager_invalid_tool_json_is_recoverable_but_never_executable(self) -> None:
        events = anthropic_events()
        deltas = [
            envelope
            for envelope in events
            if envelope["event"] == "content_block_delta"
            and envelope["data"]["delta"]["type"] == "input_json_delta"
        ]
        deltas[0]["data"]["delta"]["partial_json"] = '{"order_ref":'
        for envelope in deltas[1:]:
            envelope["data"]["delta"]["partial_json"] = ""

        with self.assertRaisesRegex(contracts.ProtocolError, "strict JSON"):
            contracts.parse_anthropic_messages_stream(events)

        turn = contracts.parse_anthropic_messages_stream(
            events, allow_invalid_tool_input=True
        )
        self.assertEqual([], list(turn.calls))
        self.assertIsNone(turn.recovery_calls[0].input)
        self.assertEqual("invalid_json", turn.recovery_calls[0].input_error)
        with self.assertRaisesRegex(contracts.ContinuationError, "requires is_error"):
            contracts.build_anthropic_messages_continuation(
                turn,
                [contracts.ModelVisibleToolResult("tool-use-A", "do not execute")],
                model="m",
                max_tokens=32,
                system="s",
                tools=ANTHROPIC_TOOLS,
                prior_messages=[{"role": "user", "content": "q"}],
                request_controls=ANTHROPIC_CONTROLS,
            )
        body = contracts.build_anthropic_messages_continuation(
            turn,
            [
                contracts.ModelVisibleToolResult(
                    "tool-use-A", '{"INVALID_JSON":"redacted"}', True
                )
            ],
            model="m",
            max_tokens=32,
            system="s",
            tools=ANTHROPIC_TOOLS,
            prior_messages=[{"role": "user", "content": "q"}],
            request_controls=ANTHROPIC_CONTROLS,
        )
        self.assertIs(body["messages"][-1]["content"][0]["is_error"], True)

        events[-2]["data"]["delta"]["stop_reason"] = "max_tokens"
        truncated = contracts.parse_anthropic_messages_stream(
            events, allow_invalid_tool_input=True
        )
        self.assertEqual("max_tokens", truncated.stop_reason)

        parallel = anthropic_two_call_events()
        for envelope in parallel:
            data = envelope.get("data", {})
            if (
                data.get("index") == 2
                and data.get("delta", {}).get("type") == "input_json_delta"
            ):
                data["delta"]["partial_json"] = '{"customer_ref":'
        for envelope in parallel:
            if envelope["event"] == "message_delta":
                envelope["data"]["delta"]["stop_reason"] = "max_tokens"
        truncated_parallel = contracts.parse_anthropic_messages_stream(
            parallel, allow_invalid_tool_input=True
        )
        self.assertEqual([], list(truncated_parallel.calls))
        self.assertEqual(
            ["tool-use-A", "tool-use-B"],
            [call.tool_use_id for call in truncated_parallel.recovery_calls],
        )

    def test_zero_argument_tool_commits_the_initial_empty_object(self) -> None:
        events = anthropic_events()
        for envelope in events:
            if (
                envelope["event"] == "content_block_delta"
                and envelope["data"]["delta"]["type"] == "input_json_delta"
            ):
                envelope["data"]["delta"]["partial_json"] = ""
        turn = contracts.parse_anthropic_messages_stream(events)
        self.assertEqual({}, turn.calls[0].input)
        self.assertEqual("", turn.calls[0].raw_input)

    def test_server_tool_is_not_reclassified_as_client_tool(self) -> None:
        turn = contracts.parse_anthropic_messages_stream(
            anthropic_extended_mixed_events()
        )
        self.assertEqual(
            ["thinking", "redacted_thinking", "text", "tool_use", "server_tool_use"],
            [block["type"] for block in turn.assistant_content],
        )
        self.assertEqual(["tool-use-A"], [call.tool_use_id for call in turn.calls])
        self.assertEqual("opaque-signature", turn.assistant_content[0]["signature"])
        body = contracts.build_anthropic_messages_continuation(
            turn,
            [contracts.ModelVisibleToolResult("tool-use-A", "ok")],
            model="m",
            max_tokens=32,
            system="s",
            tools=ANTHROPIC_TOOLS,
            prior_messages=[{"role": "user", "content": "q"}],
            request_controls=ANTHROPIC_CONTROLS,
        )
        self.assertEqual(
            ["thinking", "redacted_thinking", "text", "tool_use", "server_tool_use"],
            [block["type"] for block in body["messages"][-2]["content"]],
        )

    def test_delta_type_must_match_block_type(self) -> None:
        events = anthropic_events()
        events[7]["data"]["delta"]["type"] = "text_delta"
        events[7]["data"]["delta"]["text"] = "bad"
        with self.assertRaisesRegex(contracts.UnsupportedProviderState, "does not match"):
            contracts.parse_anthropic_messages_stream(events)

    def test_sse_error_after_partial_call_never_commits(self) -> None:
        events = anthropic_events()
        events[-1] = {
            "event": "error",
            "data": {
                "type": "error",
                "error": {"type": "overloaded_error", "message": "try later"},
                "request_id": "request-A",
            },
        }
        with self.assertRaises(contracts.ProviderStreamError) as captured:
            contracts.parse_anthropic_messages_stream(events)
        self.assertEqual(1, captured.exception.partial_call_count)

        events = anthropic_events()[:6] + [
            {
                "event": "error",
                "data": {
                    "type": "error",
                    "error": {"type": "overloaded_error", "message": "try later"},
                },
            }
        ]
        with self.assertRaises(contracts.ProviderStreamError) as captured:
            contracts.parse_anthropic_messages_stream(events)
        self.assertEqual(1, captured.exception.partial_call_count)

    def test_eof_without_message_stop_is_not_success(self) -> None:
        with self.assertRaisesRegex(contracts.ProtocolError, "without message_stop"):
            contracts.parse_anthropic_messages_stream(anthropic_events()[:-1])

    def test_non_tool_terminal_does_not_release_completed_tool_block(self) -> None:
        events = anthropic_events()
        events[-2]["data"]["delta"]["stop_reason"] = "max_tokens"
        with self.assertRaises(contracts.ProviderStreamError):
            contracts.parse_anthropic_messages_stream(events)

        events = [
            envelope
            for envelope in anthropic_events()
            if not (
                envelope["event"].startswith("content_block")
                and envelope["data"].get("index") == 1
            )
        ]
        with self.assertRaisesRegex(contracts.ProtocolError, "no client"):
            contracts.parse_anthropic_messages_stream(events)

    def test_cumulative_usage_cannot_move_backwards(self) -> None:
        events = anthropic_events()
        events[-2]["data"]["usage"]["output_tokens"] = 0
        with self.assertRaisesRegex(contracts.ProtocolError, "backwards"):
            contracts.parse_anthropic_messages_stream(events)

    def test_content_indexes_cannot_hide_a_missing_block(self) -> None:
        events = anthropic_events()
        for index in (5, 6, 7, 8, 9):
            events[index]["data"]["index"] = 2
        with self.assertRaisesRegex(contracts.ProtocolError, "contiguous"):
            contracts.parse_anthropic_messages_stream(events)

    def test_two_parallel_calls_are_preserved_in_block_order(self) -> None:
        turn = contracts.parse_anthropic_messages_stream(anthropic_two_call_events())
        self.assertEqual(["tool-use-A", "tool-use-B"], [call.tool_use_id for call in turn.calls])
        body = contracts.build_anthropic_messages_continuation(
            turn,
            [
                contracts.ModelVisibleToolResult("tool-use-B", "b"),
                contracts.ModelVisibleToolResult("tool-use-A", "a"),
            ],
            model="m",
            max_tokens=32,
            system="s",
            tools=ANTHROPIC_TOOLS,
            prior_messages=[{"role": "user", "content": "q"}],
            request_controls=ANTHROPIC_CONTROLS,
        )
        self.assertEqual(
            ["tool-use-A", "tool-use-B"],
            [
                block["tool_use_id"]
                for block in body["messages"][-1]["content"]
            ],
        )

    def test_opaque_ids_do_not_require_msg_or_toolu_prefix(self) -> None:
        turn = contracts.parse_anthropic_messages_stream(anthropic_events())
        self.assertEqual("message-A", turn.message_id)
        self.assertEqual("tool-use-A", turn.calls[0].tool_use_id)


class GeminiInteractionsTests(unittest.TestCase):
    def test_golden_ga_v1_stream_commits_requires_action_call(self) -> None:
        turn = contracts.parse_gemini_interactions_stream(gemini_events())
        self.assertEqual("requires_action", turn.status)
        self.assertEqual({"order_ref": "A-17"}, turn.calls[0].arguments)
        self.assertEqual("event-8", turn.last_event_id)
        self.assertEqual(("in_progress",), turn.status_updates)
        self.assertEqual(22, turn.usage["total_input_tokens"])

    def test_identical_replayed_event_id_is_idempotent(self) -> None:
        events = gemini_events()
        events.insert(4, copy.deepcopy(events[3]))
        turn = contracts.parse_gemini_interactions_stream(events)
        self.assertEqual(1, len(turn.calls))

    def test_reused_event_id_with_changed_payload_is_rejected(self) -> None:
        events = gemini_events()
        conflicting = copy.deepcopy(events[2])
        conflicting["delta"]["arguments"] = "different"
        events.insert(3, conflicting)
        with self.assertRaisesRegex(contracts.ProtocolError, "reused"):
            contracts.parse_gemini_interactions_stream(events)

    def test_missing_optional_arguments_delta_is_empty_not_stringified_none(self) -> None:
        turn = contracts.parse_gemini_interactions_stream(gemini_events())
        self.assertEqual("A-17", turn.calls[0].arguments["order_ref"])

        events = gemini_events()
        for event in events:
            if event.get("event_type") == "step.delta":
                event["delta"]["arguments"] = ""
        turn = contracts.parse_gemini_interactions_stream(events)
        self.assertEqual({}, turn.calls[0].arguments)

    def test_optional_function_signature_and_partial_usage_are_preserved(self) -> None:
        events = gemini_events()
        events[1]["step"]["signature"] = "function-signature"
        events[-1]["interaction"]["usage"] = {"total_tokens": 33}
        turn = contracts.parse_gemini_interactions_stream(events)
        self.assertEqual("function-signature", turn.calls[0].raw_step["signature"])
        self.assertEqual({"total_tokens": 33}, turn.usage)

    def test_unknown_event_is_preserved_if_terminal_still_proves_completion(self) -> None:
        events = gemini_events()
        events.insert(-1, {"event_type": "provider.notice", "event_id": "event-notice", "x": 1})
        turn = contracts.parse_gemini_interactions_stream(events)
        self.assertEqual("provider.notice", turn.unknown_events[0]["event_type"])

    def test_step_before_interaction_created_cannot_produce_a_call(self) -> None:
        events = gemini_events()
        events[0], events[1] = events[1], events[0]
        with self.assertRaises(contracts.ProtocolError):
            contracts.parse_gemini_interactions_stream(events)

    def test_duplicate_step_index_and_delta_without_start_are_rejected(self) -> None:
        events = gemini_events()
        events.insert(2, copy.deepcopy(events[1]))
        events[2]["event_id"] = "event-duplicate-start"
        with self.assertRaisesRegex(contracts.ProtocolError, "started twice"):
            contracts.parse_gemini_interactions_stream(events)

        events = gemini_events()
        del events[1]
        with self.assertRaisesRegex(contracts.ProtocolError, "no open step"):
            contracts.parse_gemini_interactions_stream(events)

    def test_non_argument_delta_is_not_flattened(self) -> None:
        events = gemini_events()
        events[2]["delta"]["type"] = "text_delta"
        with self.assertRaisesRegex(contracts.UnsupportedProviderState, "non-argument"):
            contracts.parse_gemini_interactions_stream(events)

    def test_streamed_arguments_require_empty_initial_object(self) -> None:
        events = gemini_events()
        events[1]["step"]["arguments"] = {"early": True}
        with self.assertRaisesRegex(contracts.ProtocolError, "empty object"):
            contracts.parse_gemini_interactions_stream(events)

    def test_arguments_are_strict_json_objects(self) -> None:
        for encoded, message in (
            ('{"x":1,"x":2}', "duplicate"),
            ('[1,2]', "object"),
        ):
            events = gemini_events()
            events[2]["delta"]["arguments"] = encoded
            events[3]["delta"].pop("arguments", None)
            events[4]["delta"]["arguments"] = ""
            with self.subTest(encoded=encoded):
                with self.assertRaisesRegex(contracts.ProviderContractError, message):
                    contracts.parse_gemini_interactions_stream(events)

    def test_step_stop_without_start_is_rejected(self) -> None:
        events = gemini_events()
        del events[1:5]
        with self.assertRaisesRegex(contracts.ProtocolError, "no open step"):
            contracts.parse_gemini_interactions_stream(events)

    def test_status_update_is_bound_to_interaction(self) -> None:
        events = gemini_events()
        events[-2]["interaction_id"] = "other-interaction"
        with self.assertRaisesRegex(contracts.ProtocolError, "changed interaction ID"):
            contracts.parse_gemini_interactions_stream(events)

    def test_status_update_is_optional_and_not_the_terminal_authority(self) -> None:
        turn = contracts.parse_gemini_interactions_stream(gemini_events())
        self.assertEqual(("in_progress",), turn.status_updates)
        self.assertEqual("requires_action", turn.status)

        events = gemini_events()
        del events[-2]
        turn = contracts.parse_gemini_interactions_stream(events)
        self.assertEqual((), turn.status_updates)
        self.assertEqual("requires_action", turn.status)

    def test_error_event_never_releases_calls(self) -> None:
        events = gemini_events()
        events[-1] = {
            "event_type": "error",
            "event_id": "event-8",
            "error": {"code": "unavailable", "message": "try later"},
        }
        with self.assertRaises(contracts.ProviderStreamError):
            contracts.parse_gemini_interactions_stream(events)

        events = gemini_events()[:2] + [
            {
                "event_type": "error",
                "event_id": "event-error",
                "error": {"code": "unavailable", "message": "try later"},
            }
        ]
        with self.assertRaises(contracts.ProviderStreamError) as captured:
            contracts.parse_gemini_interactions_stream(events)
        self.assertEqual(1, captured.exception.partial_call_count)

    def test_eof_without_interaction_completed_is_not_success(self) -> None:
        with self.assertRaisesRegex(contracts.ProtocolError, "without interaction.completed"):
            contracts.parse_gemini_interactions_stream(gemini_events()[:-1])

    def test_function_calls_require_requires_action_terminal(self) -> None:
        events = gemini_events()
        events[-1]["interaction"]["status"] = "completed"
        with self.assertRaises(contracts.ProviderStreamError):
            contracts.parse_gemini_interactions_stream(events)

    def test_unknown_status_update_and_terminal_fail_closed(self) -> None:
        events = gemini_events()
        events[-2]["status"] = "future_status"
        with self.assertRaisesRegex(contracts.UnsupportedProviderState, "unknown"):
            contracts.parse_gemini_interactions_stream(events)

    def test_usage_rejects_legacy_aliases_and_negative_totals(self) -> None:
        events = gemini_events()
        events[-1]["interaction"]["usage"] = {"input_tokens": 1}
        with self.assertRaisesRegex(contracts.ProtocolError, "legacy aliases"):
            contracts.parse_gemini_interactions_stream(events)

        events = gemini_events()
        events[-1]["interaction"]["usage"]["total_thought_tokens"] = -1
        with self.assertRaisesRegex(contracts.ProviderContractError, "between"):
            contracts.parse_gemini_interactions_stream(events)

        events = gemini_events()
        events[-1]["interaction"]["status"] = "future_status"
        with self.assertRaisesRegex(contracts.UnsupportedProviderState, "unknown"):
            contracts.parse_gemini_interactions_stream(events)

    def test_event_after_completed_is_rejected(self) -> None:
        events = gemini_events() + [
            {"event_type": "provider.notice", "event_id": "event-9"}
        ]
        with self.assertRaisesRegex(contracts.ProtocolError, "after interaction.completed"):
            contracts.parse_gemini_interactions_stream(events)

    def test_parallel_calls_are_bound_by_step_index(self) -> None:
        turn = contracts.parse_gemini_interactions_stream(gemini_parallel_events())
        self.assertEqual(["call-A", "call-B"], [call.call_id for call in turn.calls])
        self.assertEqual({"customer_ref": "C-9"}, turn.calls[1].arguments)

    def test_step_index_is_correlation_not_a_zero_based_array_offset(self) -> None:
        events = gemini_events()
        for event in events:
            if event["event_type"].startswith("step."):
                event["index"] = -17
        turn = contracts.parse_gemini_interactions_stream(events)
        self.assertEqual(-17, turn.calls[0].step_index)

    def test_known_nonclient_step_is_preserved_without_becoming_a_call(self) -> None:
        turn = contracts.parse_gemini_interactions_stream(gemini_with_thought_events())
        self.assertEqual(1, len(turn.calls))
        self.assertFalse(turn.stateless_replay_complete)
        self.assertEqual("thought", turn.raw_steps[0]["type"])
        self.assertEqual("thought", turn.opaque_step_events[0]["step"]["type"])

    def test_unknown_step_type_fails_closed(self) -> None:
        for step_type in (
            "future_client_action",
            "mcp_server_tool_call",
            "mcp_server_tool_result",
        ):
            with self.subTest(step_type=step_type):
                events = gemini_events()
                events[1]["step"]["type"] = step_type
                with self.assertRaisesRegex(
                    contracts.UnsupportedProviderState,
                    "unknown",
                ):
                    contracts.parse_gemini_interactions_stream(events)

    def test_opaque_ids_do_not_require_int_or_call_prefix(self) -> None:
        turn = contracts.parse_gemini_interactions_stream(gemini_events())
        self.assertEqual("interaction-A", turn.interaction_id)
        self.assertEqual("call-A", turn.calls[0].call_id)


class ContinuationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.openai = contracts.parse_openai_responses_stream(openai_events())
        self.anthropic = contracts.parse_anthropic_messages_stream(anthropic_events())
        self.gemini = contracts.parse_gemini_interactions_stream(gemini_events())

    def test_openai_continuation_uses_call_id_and_replays_controls(self) -> None:
        body = contracts.build_openai_responses_continuation(
            self.openai,
            [RESULT_A],
            model="fixture-model",
            instructions="Stay within the approved workflow.",
            tools=TOOLS,
            previous_response_was_stored=True,
            store=False,
            request_controls=OPENAI_CONTROLS,
        )
        self.assertEqual("response-A", body["previous_response_id"])
        self.assertEqual("call-A", body["input"][0]["call_id"])
        self.assertNotEqual("item-A", body["input"][0]["call_id"])
        self.assertEqual(TOOLS, body["tools"])
        self.assertIn("instructions", body)
        self.assertIs(body["store"], False)
        self.assertEqual(OPENAI_CONTROLS["tool_choice"], body["tool_choice"])

        with self.assertRaisesRegex(contracts.ContinuationError, "stored prior"):
            contracts.build_openai_responses_continuation(
                self.openai,
                [RESULT_A],
                model="m",
                instructions="i",
                tools=TOOLS,
                previous_response_was_stored=False,
                store=True,
                request_controls=OPENAI_CONTROLS,
            )

        with self.assertRaisesRegex(contracts.ContinuationError, "type"):
            contracts.build_openai_responses_continuation(
                self.openai,
                [RESULT_A],
                model="m",
                instructions="i",
                tools=ANTHROPIC_TOOLS,
                previous_response_was_stored=True,
                store=True,
                request_controls=OPENAI_CONTROLS,
            )

    def test_openai_does_not_invent_native_is_error(self) -> None:
        result = contracts.ModelVisibleToolResult("call-A", '{"error":"not found"}', True)
        body = contracts.build_openai_responses_continuation(
            self.openai,
            [result],
            model="fixture-model",
            instructions="Continue safely.",
            tools=TOOLS,
            previous_response_was_stored=True,
            store=True,
            request_controls=OPENAI_CONTROLS,
        )
        self.assertNotIn("is_error", body["input"][0])

    def test_openai_stateless_continuation_replays_complete_items_in_order(self) -> None:
        turn = contracts.parse_openai_responses_stream(openai_with_reasoning_events())
        body = contracts.build_openai_responses_stateless_continuation(
            turn,
            [RESULT_A],
            model="m",
            instructions="i",
            tools=TOOLS,
            prior_input_items=[{"role": "user", "content": "Where is A-17?"}],
            request_controls=OPENAI_CONTROLS,
        )
        self.assertIs(body["store"], False)
        self.assertNotIn("previous_response_id", body)
        self.assertEqual(
            [None, "reasoning", "function_call", "function_call_output"],
            [item.get("type") for item in body["input"]],
        )

        tampered_turn = contracts.parse_openai_responses_stream(
            openai_with_reasoning_events()
        )
        tampered_turn.raw_output[0]["summary"].append(
            {"type": "text", "text": "mutated after parse"}
        )
        with self.assertRaisesRegex(contracts.ContinuationError, "snapshot changed"):
            contracts.build_openai_responses_stateless_continuation(
                tampered_turn,
                [RESULT_A],
                model="m",
                instructions="i",
                tools=TOOLS,
                prior_input_items=[{"role": "user", "content": "Where is A-17?"}],
                request_controls=OPENAI_CONTROLS,
            )

        with self.assertRaisesRegex(contracts.ContinuationError, "Item list"):
            contracts.build_openai_responses_stateless_continuation(
                turn,
                [RESULT_A],
                model="m",
                instructions="i",
                tools=TOOLS,
                prior_input_items="question",  # type: ignore[arg-type]
                request_controls=OPENAI_CONTROLS,
            )

        with self.assertRaisesRegex(contracts.ContinuationError, "Item objects"):
            contracts.build_openai_responses_stateless_continuation(
                turn,
                [RESULT_A],
                model="m",
                instructions="i",
                tools=TOOLS,
                prior_input_items=[42],
                request_controls=OPENAI_CONTROLS,
            )

    def test_result_sets_are_exact_for_every_provider(self) -> None:
        builders = (
            lambda results: contracts.build_openai_responses_continuation(
                self.openai,
                results,
                model="m",
                instructions="i",
                tools=TOOLS,
                previous_response_was_stored=True,
                store=True,
                request_controls=OPENAI_CONTROLS,
            ),
            lambda results: contracts.build_anthropic_messages_continuation(
                self.anthropic,
                results,
                model="m",
                max_tokens=10,
                system="s",
                tools=ANTHROPIC_TOOLS,
                prior_messages=[{"role": "user", "content": "question"}],
                request_controls=ANTHROPIC_CONTROLS,
            ),
            lambda results: contracts.build_gemini_interactions_stateful_continuation(
                self.gemini,
                results,
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={},
                previous_interaction_was_stored=True,
                store=True,
            ),
        )
        for builder in builders:
            with self.subTest(builder=builder):
                with self.assertRaisesRegex(contracts.ContinuationError, "missing"):
                    builder([])
                with self.assertRaisesRegex(contracts.ContinuationError, "extra"):
                    builder([RESULT_A, contracts.ModelVisibleToolResult("extra", "x")])
                with self.assertRaisesRegex(contracts.ContinuationError, "duplicate"):
                    builder([RESULT_A, RESULT_A])

    def test_anthropic_continuation_replays_full_ordered_history(self) -> None:
        result = contracts.ModelVisibleToolResult("tool-use-A", "order shipped")
        body = contracts.build_anthropic_messages_continuation(
            self.anthropic,
            [result],
            model="fixture-model",
            max_tokens=512,
            system="Use approved tools only.",
            tools=ANTHROPIC_TOOLS,
            prior_messages=[{"role": "user", "content": "Where is A-17?"}],
            request_controls=ANTHROPIC_CONTROLS,
        )
        self.assertEqual("Use approved tools only.", body["system"])
        self.assertEqual("assistant", body["messages"][-2]["role"])
        self.assertEqual(["text", "tool_use"], [b["type"] for b in body["messages"][-2]["content"]])
        result_blocks = body["messages"][-1]["content"]
        self.assertTrue(all(block["type"] == "tool_result" for block in result_blocks))
        self.assertEqual("tool-use-A", result_blocks[0]["tool_use_id"])
        self.assertEqual(ANTHROPIC_CONTROLS["tool_choice"], body["tool_choice"])
        self.assertEqual("auto", body["service_tier"])

        self.anthropic.assistant_content[1]["id"] = "tampered-after-parse"
        with self.assertRaisesRegex(contracts.ContinuationError, "snapshot changed"):
            contracts.build_anthropic_messages_continuation(
                self.anthropic,
                [result],
                model="fixture-model",
                max_tokens=512,
                system="Use approved tools only.",
                tools=ANTHROPIC_TOOLS,
                prior_messages=[{"role": "user", "content": "Where is A-17?"}],
                request_controls=ANTHROPIC_CONTROLS,
            )

    def test_anthropic_native_is_error_is_preserved(self) -> None:
        result = contracts.ModelVisibleToolResult("tool-use-A", "not found", True)
        body = contracts.build_anthropic_messages_continuation(
            self.anthropic,
            [result],
            model="fixture-model",
            max_tokens=100,
            system="s",
            tools=ANTHROPIC_TOOLS,
            prior_messages=[{"role": "user", "content": "q"}],
            request_controls=ANTHROPIC_CONTROLS,
        )
        self.assertIs(body["messages"][-1]["content"][0]["is_error"], True)

    def test_anthropic_system_blocks_and_capability_gated_mid_system_are_preserved(self) -> None:
        history = [
            {"role": "user", "content": "q"},
            {"role": "system", "content": "Apply the approved policy from now on."},
        ]
        system_blocks = [
            {
                "type": "text",
                "text": "Base policy.",
                "cache_control": {"type": "ephemeral"},
            }
        ]
        body = contracts.build_anthropic_messages_continuation(
            self.anthropic,
            [contracts.ModelVisibleToolResult("tool-use-A", "ok")],
            model="m",
            max_tokens=10,
            system=system_blocks,
            tools=ANTHROPIC_TOOLS,
            prior_messages=history,
            request_controls=ANTHROPIC_CONTROLS,
            allow_mid_conversation_system=True,
        )
        self.assertEqual(system_blocks, body["system"])
        self.assertEqual("system", body["messages"][1]["role"])

        with self.assertRaisesRegex(contracts.ContinuationError, "model capability"):
            contracts.build_anthropic_messages_continuation(
                self.anthropic,
                [contracts.ModelVisibleToolResult("tool-use-A", "ok")],
                model="m",
                max_tokens=10,
                system="s",
                tools=ANTHROPIC_TOOLS,
                prior_messages=history,
                request_controls=ANTHROPIC_CONTROLS,
            )

        with self.assertRaisesRegex(contracts.ContinuationError, "first message"):
            contracts.build_anthropic_messages_continuation(
                self.anthropic,
                [contracts.ModelVisibleToolResult("tool-use-A", "ok")],
                model="m",
                max_tokens=10,
                system="s",
                tools=ANTHROPIC_TOOLS,
                prior_messages=[{"role": "system", "content": "wrong"}],
                request_controls=ANTHROPIC_CONTROLS,
                allow_mid_conversation_system=True,
            )

    def test_anthropic_rejects_cross_provider_shapes_and_control_collisions(self) -> None:
        kwargs = {
            "model": "m",
            "max_tokens": 10,
            "system": "s",
            "prior_messages": [{"role": "user", "content": "q"}],
        }
        with self.assertRaisesRegex(contracts.ContinuationError, "function-tool shape"):
            contracts.build_anthropic_messages_continuation(
                self.anthropic,
                [contracts.ModelVisibleToolResult("tool-use-A", "ok")],
                tools=TOOLS,
                request_controls=ANTHROPIC_CONTROLS,
                **kwargs,
            )
        with self.assertRaisesRegex(contracts.ContinuationError, "protected fields"):
            contracts.build_anthropic_messages_continuation(
                self.anthropic,
                [contracts.ModelVisibleToolResult("tool-use-A", "ok")],
                tools=ANTHROPIC_TOOLS,
                request_controls={"messages": []},
                **kwargs,
            )
        with self.assertRaisesRegex(contracts.ContinuationError, "string or block array"):
            contracts.build_anthropic_messages_continuation(
                self.anthropic,
                [contracts.ModelVisibleToolResult("tool-use-A", "ok")],
                tools=ANTHROPIC_TOOLS,
                request_controls=ANTHROPIC_CONTROLS,
                prior_messages=[{"role": "user", "content": 1}],
                model="m",
                max_tokens=10,
                system="s",
            )

    def test_gemini_stateful_continuation_replays_non_inherited_config(self) -> None:
        body = contracts.build_gemini_interactions_stateful_continuation(
            self.gemini,
            [RESULT_A],
            model="fixture-model",
            tools=GEMINI_TOOLS,
            system_instruction="Use approved tools only.",
            generation_config={"temperature": 0},
            response_format=[GEMINI_JSON_RESPONSE_FORMAT],
            previous_interaction_was_stored=True,
            store=False,
        )
        self.assertEqual("interaction-A", body["previous_interaction_id"])
        self.assertIs(body["store"], False)
        self.assertEqual(GEMINI_TOOLS, body["tools"])
        self.assertEqual([GEMINI_JSON_RESPONSE_FORMAT], body["response_format"])
        self.assertEqual("function_result", body["input"][0]["type"])
        self.assertEqual("text", body["input"][0]["result"][0]["type"])

        self.gemini.raw_steps[0]["id"] = "tampered-after-parse"
        with self.assertRaisesRegex(contracts.ContinuationError, "snapshot changed"):
            contracts.build_gemini_interactions_stateful_continuation(
                self.gemini,
                [RESULT_A],
                model="fixture-model",
                tools=GEMINI_TOOLS,
                system_instruction="Use approved tools only.",
                generation_config={"temperature": 0},
                response_format=[GEMINI_JSON_RESPONSE_FORMAT],
                previous_interaction_was_stored=True,
                store=False,
            )

    def test_gemini_previous_id_requires_explicit_storage(self) -> None:
        with self.assertRaisesRegex(contracts.ContinuationError, "stored"):
            contracts.build_gemini_interactions_stateful_continuation(
                self.gemini,
                [RESULT_A],
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={},
                previous_interaction_was_stored=False,
                store=True,
            )

        with self.assertRaisesRegex(contracts.ContinuationError, "boolean"):
            contracts.build_gemini_interactions_stateful_continuation(
                self.gemini,
                [RESULT_A],
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={},
                previous_interaction_was_stored=True,
                store=1,  # type: ignore[arg-type]
            )

    def test_gemini_stateless_continuation_replays_raw_steps(self) -> None:
        body = contracts.build_gemini_interactions_stateless_continuation(
            self.gemini,
            [RESULT_A],
            model="fixture-model",
            tools=GEMINI_TOOLS,
            system_instruction="s",
            generation_config={},
            prior_input_steps=GEMINI_USER_STEPS,
        )
        self.assertIs(body["store"], False)
        self.assertNotIn("previous_interaction_id", body)
        self.assertEqual("user_input", body["input"][0]["type"])
        self.assertEqual("function_call", body["input"][1]["type"])
        self.assertEqual("function_result", body["input"][2]["type"])

        with self.assertRaisesRegex(contracts.ContinuationError, "object"):
            contracts.build_gemini_interactions_stateless_continuation(
                self.gemini,
                [RESULT_A],
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={},
                prior_input_steps=["question"],  # type: ignore[list-item]
            )
        with self.assertRaisesRegex(contracts.ContinuationError, "unknown Step type"):
            contracts.build_gemini_interactions_stateless_continuation(
                self.gemini,
                [RESULT_A],
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={},
                prior_input_steps=[{"type": []}],  # type: ignore[dict-item]
            )
        with self.assertRaisesRegex(contracts.ContinuationError, "orphan function result"):
            contracts.build_gemini_interactions_stateless_continuation(
                self.gemini,
                [RESULT_A],
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={},
                prior_input_steps=[
                    {"type": "user_input", "content": []},
                    {"type": "function_result", "call_id": "orphan", "result": []},
                ],
            )
        with self.assertRaisesRegex(contracts.ContinuationError, "source"):
            contracts.build_gemini_interactions_stateless_continuation(
                self.gemini,
                [RESULT_A],
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={},
                prior_input_steps=GEMINI_USER_STEPS,
                complete_steps=[copy.deepcopy(self.gemini.calls[0].raw_step)],
                complete_steps_source=[],  # type: ignore[arg-type]
                complete_steps_interaction_id=self.gemini.interaction_id,
            )

    def test_gemini_opaque_stream_step_requires_complete_snapshot_for_stateless_replay(self) -> None:
        turn = contracts.parse_gemini_interactions_stream(gemini_with_thought_events())
        with self.assertRaisesRegex(contracts.ContinuationError, "steps snapshot"):
            contracts.build_gemini_interactions_stateless_continuation(
                turn,
                [RESULT_A],
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={},
                prior_input_steps=GEMINI_USER_STEPS,
            )

        complete_steps = [
            {
                "type": "thought",
                "signature": "opaque-signature",
                "summary": [{"type": "text", "text": "fixture summary"}],
            },
            copy.deepcopy(turn.calls[0].raw_step),
        ]
        body = contracts.build_gemini_interactions_stateless_continuation(
            turn,
            [RESULT_A],
            model="m",
            tools=GEMINI_TOOLS,
            system_instruction="s",
            generation_config={},
            prior_input_steps=GEMINI_USER_STEPS,
            complete_steps=complete_steps,
            complete_steps_source="create",
            complete_steps_interaction_id=turn.interaction_id,
        )
        self.assertEqual("thought", body["input"][1]["type"])
        self.assertEqual("function_call", body["input"][2]["type"])
        self.assertEqual("function_result", body["input"][3]["type"])

        get_steps = copy.deepcopy(GEMINI_USER_STEPS) + complete_steps
        get_body = contracts.build_gemini_interactions_stateless_continuation(
            turn,
            [RESULT_A],
            model="m",
            tools=GEMINI_TOOLS,
            system_instruction="s",
            generation_config={},
            prior_input_steps=None,
            complete_steps=get_steps,
            complete_steps_source="get",
            complete_steps_interaction_id=turn.interaction_id,
        )
        self.assertEqual(
            ["user_input", "thought", "function_call", "function_result"],
            [step["type"] for step in get_body["input"]],
        )

    def test_gemini_complete_snapshot_must_bind_sequence_signature_and_identity(self) -> None:
        turn = contracts.parse_gemini_interactions_stream(gemini_with_thought_events())
        thought = {
            "type": "thought",
            "signature": "opaque-signature",
            "summary": [{"type": "text", "text": "fixture summary"}],
        }
        with self.assertRaisesRegex(contracts.ContinuationError, "sequence"):
            contracts.build_gemini_interactions_stateless_continuation(
                turn,
                [RESULT_A],
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={},
                prior_input_steps=GEMINI_USER_STEPS,
                complete_steps=[copy.deepcopy(turn.calls[0].raw_step)],
                complete_steps_source="create",
                complete_steps_interaction_id=turn.interaction_id,
            )

        changed_thought = copy.deepcopy(thought)
        changed_thought["signature"] = "changed"
        with self.assertRaisesRegex(contracts.ContinuationError, "signature"):
            contracts.build_gemini_interactions_stateless_continuation(
                turn,
                [RESULT_A],
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={},
                prior_input_steps=GEMINI_USER_STEPS,
                complete_steps=[changed_thought, copy.deepcopy(turn.calls[0].raw_step)],
                complete_steps_source="create",
                complete_steps_interaction_id=turn.interaction_id,
            )

        with self.assertRaisesRegex(contracts.ContinuationError, "different interaction"):
            contracts.build_gemini_interactions_stateless_continuation(
                turn,
                [RESULT_A],
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={},
                prior_input_steps=GEMINI_USER_STEPS,
                complete_steps=[thought, copy.deepcopy(turn.calls[0].raw_step)],
                complete_steps_source="create",
                complete_steps_interaction_id="other-interaction",
            )

    def test_gemini_unknown_event_requires_authoritative_snapshot(self) -> None:
        events = gemini_events()
        events.insert(
            -1,
            {"event_type": "provider.notice", "event_id": "event-notice", "x": 1},
        )
        turn = contracts.parse_gemini_interactions_stream(events)
        self.assertFalse(turn.stateless_replay_complete)
        with self.assertRaisesRegex(contracts.ContinuationError, "steps snapshot"):
            contracts.build_gemini_interactions_stateless_continuation(
                turn,
                [RESULT_A],
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={},
                prior_input_steps=GEMINI_USER_STEPS,
            )

    def test_gemini_opaque_model_output_snapshot_fails_closed(self) -> None:
        events = gemini_events()
        events.insert(
            1,
            {
                "event_type": "step.start",
                "event_id": "event-model-start",
                "index": 17,
                "step": {"type": "model_output", "content": []},
            },
        )
        function_stop = next(
            index
            for index, event in enumerate(events)
            if event["event_type"] == "step.stop" and event["index"] == 0
        )
        events[function_stop + 1 : function_stop + 1] = [
            {
                "event_type": "step.delta",
                "event_id": "event-model-delta",
                "index": 17,
                "delta": {"type": "text", "text": "I will check."},
            },
            {
                "event_type": "step.stop",
                "event_id": "event-model-stop",
                "index": 17,
            },
        ]
        turn = contracts.parse_gemini_interactions_stream(events)
        complete_steps = [
            {
                "type": "model_output",
                "content": [{"type": "text", "text": "changed"}],
            },
            copy.deepcopy(turn.calls[0].raw_step),
        ]
        with self.assertRaisesRegex(contracts.ContinuationError, "cannot prove"):
            contracts.build_gemini_interactions_stateless_continuation(
                turn,
                [RESULT_A],
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={},
                prior_input_steps=GEMINI_USER_STEPS,
                complete_steps=complete_steps,
                complete_steps_source="create",
                complete_steps_interaction_id=turn.interaction_id,
            )

    def test_gemini_rejects_cross_provider_config_shapes(self) -> None:
        with self.assertRaisesRegex(contracts.ContinuationError, "OpenAI field"):
            contracts.build_gemini_interactions_stateful_continuation(
                self.gemini,
                [RESULT_A],
                model="m",
                tools=TOOLS,
                system_instruction="s",
                generation_config={},
                previous_interaction_was_stored=True,
                store=True,
            )
        with self.assertRaisesRegex(contracts.ContinuationError, "unknown Gemini type"):
            contracts.build_gemini_interactions_stateful_continuation(
                self.gemini,
                [RESULT_A],
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={},
                response_format={"type": "json_schema", "schema": {}},
                previous_interaction_was_stored=True,
                store=True,
            )
        for mime_type in ("not/a-real-type", []):
            with self.subTest(mime_type=mime_type):
                with self.assertRaisesRegex(contracts.ContinuationError, "text MIME type"):
                    contracts.build_gemini_interactions_stateful_continuation(
                        self.gemini,
                        [RESULT_A],
                        model="m",
                        tools=GEMINI_TOOLS,
                        system_instruction="s",
                        generation_config={},
                        response_format={"type": "text", "mime_type": mime_type},
                        previous_interaction_was_stored=True,
                        store=True,
                    )

    def test_gemini_native_is_error_is_preserved(self) -> None:
        result = contracts.ModelVisibleToolResult("call-A", "not found", True)
        body = contracts.build_gemini_interactions_stateful_continuation(
            self.gemini,
            [result],
            model="m",
            tools=GEMINI_TOOLS,
            system_instruction="s",
            generation_config={},
            previous_interaction_was_stored=True,
            store=True,
        )
        self.assertIs(body["input"][0]["is_error"], True)

    def test_non_finite_replayed_config_is_rejected(self) -> None:
        with self.assertRaisesRegex(contracts.ContinuationError, "non-finite"):
            contracts.build_gemini_interactions_stateful_continuation(
                self.gemini,
                [RESULT_A],
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={"temperature": math.nan},
                previous_interaction_was_stored=True,
                store=True,
            )

    def test_builder_copies_caller_owned_config(self) -> None:
        tools = copy.deepcopy(TOOLS)
        body = contracts.build_openai_responses_continuation(
            self.openai,
            [RESULT_A],
            model="m",
            instructions="i",
            tools=tools,
            previous_response_was_stored=True,
            store=True,
            request_controls=OPENAI_CONTROLS,
        )
        tools[0]["name"] = "mutated"
        self.assertEqual("lookup_order", body["tools"][0]["name"])

    def test_model_visible_result_contract_is_bounded_and_typed(self) -> None:
        with self.assertRaisesRegex(contracts.ContinuationError, "string"):
            contracts.ModelVisibleToolResult("call-A", {"x": 1})  # type: ignore[arg-type]
        with self.assertRaisesRegex(contracts.ContinuationError, "boolean"):
            contracts.ModelVisibleToolResult("call-A", "ok", 1)  # type: ignore[arg-type]

    def test_safe_projection_does_not_add_protected_audit_fields(self) -> None:
        bodies = [
            contracts.build_openai_responses_continuation(
                self.openai,
                [RESULT_A],
                model="m",
                instructions="i",
                tools=TOOLS,
                previous_response_was_stored=True,
                store=True,
                request_controls=OPENAI_CONTROLS,
            ),
            contracts.build_anthropic_messages_continuation(
                self.anthropic,
                [contracts.ModelVisibleToolResult("tool-use-A", "ok")],
                model="m",
                max_tokens=10,
                system="s",
                tools=ANTHROPIC_TOOLS,
                prior_messages=[{"role": "user", "content": "q"}],
                request_controls=ANTHROPIC_CONTROLS,
            ),
            contracts.build_gemini_interactions_stateful_continuation(
                self.gemini,
                [RESULT_A],
                model="m",
                tools=GEMINI_TOOLS,
                system_instruction="s",
                generation_config={},
                previous_interaction_was_stored=True,
                store=True,
            ),
        ]
        for body in bodies:
            serialized = json.dumps(body, ensure_ascii=False)
            self.assertNotIn("protected_audit", serialized)
            self.assertNotIn("principal_ref", serialized)


if __name__ == "__main__":
    unittest.main()
