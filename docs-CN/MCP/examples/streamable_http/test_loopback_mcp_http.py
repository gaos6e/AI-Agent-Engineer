from __future__ import annotations

import contextlib
import http.client
import io
import json
import os
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from loopback_mcp_http import (
    ALL_SCOPES,
    AUTHORIZATION_SERVER,
    MAX_BODY_BYTES,
    MAX_JSON_DEPTH,
    MCP_PATH,
    PROTOCOL_VERSION,
    ROOT_WELL_KNOWN_PATH,
    WELL_KNOWN_PATH,
    BoundaryError,
    LoopbackClient,
    OfflineTokenPolicy,
    RunningServer,
    TeachingState,
    TokenRecord,
    compact_json,
    main,
    make_record,
    parse_sse,
    strict_json_loads,
)


SCRIPT = Path(__file__).with_name("loopback_mcp_http.py")


class ManualClock:
    def __init__(self, value: float = 1_000.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class StrictCodecTests(unittest.TestCase):
    def test_strict_json_accepts_one_object(self) -> None:
        self.assertEqual(strict_json_loads(b'{"a":1}'), {"a": 1})

    def test_strict_json_rejects_duplicate_key(self) -> None:
        with self.assertRaisesRegex(BoundaryError, "invalid_json"):
            strict_json_loads(b'{"a":1,"a":2}')

    def test_strict_json_rejects_excessive_depth_before_decode(self) -> None:
        with self.assertRaisesRegex(BoundaryError, "json_depth_exceeded"):
            strict_json_loads(
                (
                    "[" * (MAX_JSON_DEPTH + 1)
                    + "0"
                    + "]" * (MAX_JSON_DEPTH + 1)
                ).encode("ascii")
            )

    def test_strict_json_rejects_non_finite_number(self) -> None:
        with self.assertRaisesRegex(BoundaryError, "invalid_json"):
            strict_json_loads(b'{"a":NaN}')

    def test_strict_json_rejects_invalid_utf8(self) -> None:
        with self.assertRaisesRegex(BoundaryError, "invalid_utf8"):
            strict_json_loads(b'\xff')

    def test_compact_json_is_deterministic_utf8(self) -> None:
        self.assertEqual(compact_json({"z": "中", "a": 1}), b'{"a":1,"z":"\xe4\xb8\xad"}')

    def test_compact_json_rejects_nan(self) -> None:
        with self.assertRaises(ValueError):
            compact_json({"value": float("nan")})

    def test_parse_sse_accepts_one_event(self) -> None:
        events = parse_sse(b'id: stream:1\ndata: {"jsonrpc":"2.0","method":"ping"}\n\n')
        self.assertEqual(events[0][0], "stream:1")
        self.assertEqual(events[0][1]["method"], "ping")

    def test_parse_sse_accepts_empty_poll(self) -> None:
        self.assertEqual(parse_sse(b""), [])

    def test_parse_sse_rejects_duplicate_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate SSE id"):
            parse_sse(b'id: a\nid: b\ndata: {}\n\n')

    def test_parse_sse_rejects_unknown_field(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported SSE field"):
            parse_sse(b'event: message\nid: a\ndata: {}\n\n')


class OfflinePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = ManualClock()
        self.state = TeachingState(clock=self.clock)
        self.state.configure_endpoint("127.0.0.1", 8123)

    def _register(self, token: str = "token", **changes: object) -> TokenRecord:
        record = make_record(self.state, **changes)
        self.state.policy.register_token(token, record)
        return record

    def test_valid_record_authenticates(self) -> None:
        record = self._register()
        self.assertEqual(self.state.policy.authenticate("Bearer token"), record)
        self.assertEqual(self.state.policy.authenticate("bearer token"), record)

    def test_missing_bearer_is_401(self) -> None:
        with self.assertRaisesRegex(BoundaryError, "authorization_required") as caught:
            self.state.policy.authenticate(None)
        self.assertEqual(caught.exception.status, 401)

    def test_unknown_bearer_is_401(self) -> None:
        with self.assertRaisesRegex(BoundaryError, "invalid_token"):
            self.state.policy.authenticate("Bearer unknown")
        with self.assertRaisesRegex(BoundaryError, "invalid_token"):
            self.state.policy.authenticate("Bearer invalid\ttoken")

    def test_expired_token_is_401(self) -> None:
        self._register(expires_in=1)
        self.clock.advance(1)
        with self.assertRaisesRegex(BoundaryError, "invalid_token"):
            self.state.policy.authenticate("Bearer token")

    def test_inactive_token_is_401(self) -> None:
        self._register(active=False)
        with self.assertRaisesRegex(BoundaryError, "invalid_token"):
            self.state.policy.authenticate("Bearer token")

    def test_revoked_token_is_401(self) -> None:
        self._register(token_id="revoked")
        self.state.policy.revoke("revoked")
        with self.assertRaisesRegex(BoundaryError, "invalid_token"):
            self.state.policy.authenticate("Bearer token")

    def test_wrong_issuer_is_401(self) -> None:
        self._register(issuer="https://evil.example.test")
        with self.assertRaisesRegex(BoundaryError, "invalid_token"):
            self.state.policy.authenticate("Bearer token")

    def test_unicode_claims_are_compared_without_ascii_type_errors(self) -> None:
        self._register(token="unicode-issuer", issuer="https://身份.example.test")
        with self.assertRaisesRegex(BoundaryError, "invalid_token") as issuer_error:
            self.state.policy.authenticate("Bearer unicode-issuer")
        self.assertEqual(401, issuer_error.exception.status)

        self._register(
            token="unicode-resource",
            audience="https://资源.example.test/mcp",
        )
        with self.assertRaisesRegex(BoundaryError, "invalid_token") as resource_error:
            self.state.policy.authenticate("Bearer unicode-resource")
        self.assertEqual(401, resource_error.exception.status)

        self._register(
            token="unicode-revision",
            subject="学习者",
            tenant="租户甲",
            revision="授权-v1",
        )
        self.state.policy.set_revision("学习者", "租户甲", "授权-v2")
        with self.assertRaisesRegex(BoundaryError, "invalid_token") as revision_error:
            self.state.policy.authenticate("Bearer unicode-revision")
        self.assertEqual(401, revision_error.exception.status)

        with self.assertRaisesRegex(ValueError, "UTF-8"):
            self._register(token="surrogate-claim", issuer="\ud800")

    def test_wrong_audience_is_401(self) -> None:
        self._register(audience="https://other.example.test/mcp")
        with self.assertRaisesRegex(BoundaryError, "invalid_token"):
            self.state.policy.authenticate("Bearer token")

    def test_wrong_resource_claim_is_401(self) -> None:
        self._register(resource="https://other.example.test/mcp")
        with self.assertRaisesRegex(BoundaryError, "invalid_token"):
            self.state.policy.authenticate("Bearer token")

    def test_authorization_request_resource_mismatch_is_401(self) -> None:
        self._register(authorization_resource="https://other.example.test/mcp")
        with self.assertRaisesRegex(BoundaryError, "invalid_token"):
            self.state.policy.authenticate("Bearer token")

    def test_token_request_resource_mismatch_is_401(self) -> None:
        self._register(token_resource="https://other.example.test/mcp")
        with self.assertRaisesRegex(BoundaryError, "invalid_token"):
            self.state.policy.authenticate("Bearer token")

    def test_stale_authorization_revision_is_401(self) -> None:
        self._register(revision="authz-v1")
        self.state.policy.set_revision("learner-1", "tenant-a", "authz-v2")
        with self.assertRaisesRegex(BoundaryError, "invalid_token"):
            self.state.policy.authenticate("Bearer token")

    def test_disallowed_tenant_is_403(self) -> None:
        record = self._register()
        self.state.policy.set_allowed_tenants("learner-1", {"tenant-b"})
        authenticated = self.state.policy.authenticate("Bearer token")
        self.assertEqual(authenticated, record)
        with self.assertRaisesRegex(BoundaryError, "forbidden") as caught:
            self.state.policy.authorize(authenticated, "mcp:use")
        self.assertEqual(caught.exception.status, 403)
        self.assertIsNone(caught.exception.required_scope)

    def test_missing_scope_is_403(self) -> None:
        record = self._register(scopes={"mcp:connect"})
        with self.assertRaisesRegex(BoundaryError, "insufficient_scope") as caught:
            self.state.policy.authorize(record, "resources:read")
        self.assertEqual(caught.exception.status, 403)

    def test_policy_does_not_store_raw_token_key(self) -> None:
        self._register(token="sensitive-fixture-token")
        keys = tuple(self.state.policy._records)  # test-only structural audit
        self.assertNotIn("sensitive-fixture-token", repr(keys))
        with self.assertRaisesRegex(ValueError, "b64token"):
            self.state.policy.register_token("contains a space", make_record(self.state))


class HTTPBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = ManualClock()
        self.running = RunningServer(TeachingState(clock=self.clock))
        self.running.__enter__()
        self.addCleanup(self.running.__exit__, None, None, None)
        self.token = "fixture-good-token"
        self.running.state.policy.register_token(
            self.token,
            make_record(self.running.state, token_id="good"),
        )
        self.client = LoopbackClient(*self.running.address, self.token)

    def _ready(self, client: LoopbackClient | None = None) -> LoopbackClient:
        selected = client or self.client
        self.assertEqual(selected.initialize().status, 200)
        self.assertEqual(selected.initialized().status, 202)
        return selected

    def _raw_post(
        self,
        message: dict[str, object],
        *,
        token: str | None = None,
        origin: str | None = "https://client.example.test",
        accept: str | None = "application/json, text/event-stream",
        content_type: str | None = "application/json",
        protocol_version: str | None = None,
        session_id: str | None = None,
        path: str = MCP_PATH,
    ):
        headers: dict[str, str] = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if origin is not None:
            headers["Origin"] = origin
        if accept is not None:
            headers["Accept"] = accept
        if content_type is not None:
            headers["Content-Type"] = content_type
        if protocol_version is not None:
            headers["MCP-Protocol-Version"] = protocol_version
        if session_id is not None:
            headers["Mcp-Session-Id"] = session_id
        return self.client.request("POST", path, headers=headers, body=compact_json(message))

    @staticmethod
    def _initialize_message() -> dict[str, object]:
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        }

    def test_server_binds_only_ipv4_loopback(self) -> None:
        self.assertEqual(self.running.address[0], "127.0.0.1")

    def test_path_specific_protected_resource_metadata(self) -> None:
        result = self.client.request("GET", WELL_KNOWN_PATH, headers={"Accept": "application/json"})
        self.assertEqual(result.status, 200)
        document = result.json()
        self.assertEqual(document["resource"], self.running.state.resource_uri)
        self.assertEqual(document["authorization_servers"], [AUTHORIZATION_SERVER])

    def test_root_protected_resource_metadata_fallback(self) -> None:
        result = self.client.request("GET", ROOT_WELL_KNOWN_PATH, headers={"Accept": "*/*"})
        self.assertEqual(result.status, 200)
        self.assertIn("resources:read", result.json()["scopes_supported"])

    def test_metadata_rejects_credentials(self) -> None:
        result = self.client.request(
            "GET",
            WELL_KNOWN_PATH,
            headers={"Accept": "application/json", "Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(result.status, 400)
        self.assertNotIn(self.token.encode(), result.body)

    def test_metadata_rejects_unacceptable_media(self) -> None:
        result = self.client.request("GET", WELL_KNOWN_PATH, headers={"Accept": "text/plain"})
        self.assertEqual(result.status, 406)

    def test_initialize_returns_json_and_secure_visible_session(self) -> None:
        result = self.client.initialize()
        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers["content-type"], "application/json")
        self.assertEqual(result.json()["result"]["protocolVersion"], PROTOCOL_VERSION)
        self.assertTrue(self.client.session_id)
        self.assertTrue(all(0x21 <= ord(char) <= 0x7E for char in self.client.session_id or ""))

    def test_initialize_returns_supported_alternative_protocol_version(self) -> None:
        message = self._initialize_message()
        message["params"]["protocolVersion"] = "2026-07-28"  # type: ignore[index]
        result = self._raw_post(message, token=self.token)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.json()["result"]["protocolVersion"], PROTOCOL_VERSION)
        self.assertIn("mcp-session-id", result.headers)

    def test_initialize_rejects_non_string_protocol_version(self) -> None:
        message = self._initialize_message()
        message["params"]["protocolVersion"] = 20251125  # type: ignore[index]
        result = self._raw_post(message, token=self.token)
        self.assertEqual(result.status, 400)
        self.assertEqual(result.json(), {"error": "invalid_initialize"})

    def test_initialize_rejects_bad_client_info(self) -> None:
        message = self._initialize_message()
        message["params"]["clientInfo"] = {"name": "test"}  # type: ignore[index]
        result = self._raw_post(message, token=self.token)
        self.assertEqual(result.status, 400)

    def test_initialize_rejects_reused_session_header(self) -> None:
        result = self._raw_post(self._initialize_message(), token=self.token, session_id="replay")
        self.assertEqual(result.status, 400)

    def test_initialize_rejects_conflicting_protocol_header(self) -> None:
        result = self._raw_post(
            self._initialize_message(),
            token=self.token,
            protocol_version="2026-07-28",
        )
        self.assertEqual(result.status, 400)

    def test_post_requires_both_accept_media_types(self) -> None:
        result = self._raw_post(
            self._initialize_message(),
            token=self.token,
            accept="application/json",
        )
        self.assertEqual(result.status, 406)
        quality_zero = self._raw_post(
            self._initialize_message(),
            token=self.token,
            accept="application/json, text/event-stream;q=0",
        )
        self.assertEqual(quality_zero.status, 406)

    def test_post_requires_content_type_in_strict_profile(self) -> None:
        result = self._raw_post(
            self._initialize_message(),
            token=self.token,
            content_type="text/plain",
        )
        self.assertEqual(result.status, 415)
        wrong_charset = self._raw_post(
            self._initialize_message(),
            token=self.token,
            content_type="application/json; charset=iso-8859-1",
        )
        self.assertEqual(wrong_charset.status, 415)

    def test_post_rejects_oversized_body_before_decode(self) -> None:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Origin": "https://client.example.test",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        result = self.client.request("POST", MCP_PATH, headers=headers, body=b"x" * (MAX_BODY_BYTES + 1))
        self.assertEqual(result.status, 413)

    def test_post_rejects_duplicate_json_keys(self) -> None:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Origin": "https://client.example.test",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        body = b'{"jsonrpc":"2.0","jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
        result = self.client.request("POST", MCP_PATH, headers=headers, body=body)
        self.assertEqual(result.status, 400)

    def test_invalid_origin_is_403(self) -> None:
        result = self._raw_post(
            self._initialize_message(),
            token=self.token,
            origin="https://attacker.example.test",
        )
        self.assertEqual(result.status, 403)
        self.assertEqual(result.json(), {"error": "invalid_origin"})
        self.assertNotIn("www-authenticate", result.headers)

    def test_absent_origin_is_accepted_for_non_browser_client(self) -> None:
        result = self._raw_post(self._initialize_message(), token=self.token, origin=None)
        self.assertEqual(result.status, 200)

    def test_missing_token_is_401_with_resource_metadata_challenge(self) -> None:
        result = self._raw_post(self._initialize_message())
        self.assertEqual(result.status, 401)
        challenge = result.headers["www-authenticate"]
        self.assertIn("resource_metadata=", challenge)
        self.assertNotIn("invalid_token", challenge)
        self.assertIn('scope="mcp:connect"', challenge)
        self.assertNotIn("insufficient_scope", challenge)

    def test_unknown_token_is_401_without_echo(self) -> None:
        result = self._raw_post(self._initialize_message(), token="unknown-secret")
        self.assertEqual(result.status, 401)
        self.assertNotIn(b"unknown-secret", result.body)

    def test_initialized_notification_returns_empty_202(self) -> None:
        self.assertEqual(self.client.initialize().status, 200)
        result = self.client.initialized()
        self.assertEqual(result.status, 202)
        self.assertEqual(result.body, b"")

    def test_request_before_initialized_is_blocked(self) -> None:
        self.assertEqual(self.client.initialize().status, 200)
        result = self.client.ping()
        self.assertEqual(result.status, 400)
        self.assertEqual(result.json(), {"error": "invalid_lifecycle"})

    def test_ping_returns_application_json(self) -> None:
        self._ready()
        result = self.client.ping()
        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers["content-type"], "application/json")
        self.assertEqual(result.json()["result"], {})

    def test_resources_list_returns_post_sse_for_same_request_id(self) -> None:
        self._ready()
        result = self.client.list_resources(77)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers["content-type"], "text/event-stream")
        events = parse_sse(result.body)
        self.assertEqual(events[0][1]["id"], 77)
        get_event_id = parse_sse(self.client.get_stream().body)[0][0]
        self.assertNotEqual(events[0][0], get_event_id)
        self.assertEqual(self.client.get_stream(events[0][0]).status, 400)

    def test_resources_are_tenant_scoped(self) -> None:
        self._ready()
        events = parse_sse(self.client.list_resources().body)
        uri = events[0][1]["result"]["resources"][0]["uri"]
        self.assertEqual(uri, "kb://tenant/tenant-a/handbook")
        self.running.state.policy.set_allowed_tenants("learner-1", {"tenant-b"})
        denied = self.client.list_resources()
        self.assertEqual(denied.status, 403)
        self.assertEqual(denied.json(), {"error": "forbidden"})
        self.assertNotIn("www-authenticate", denied.headers)

    def test_resource_scope_failure_is_403_with_scope_challenge(self) -> None:
        token = "narrow-token"
        self.running.state.policy.register_token(
            token,
            make_record(
                self.running.state,
                token_id="narrow",
                scopes={"mcp:connect", "mcp:use"},
            ),
        )
        client = self._ready(LoopbackClient(*self.running.address, token))
        result = client.list_resources()
        self.assertEqual(result.status, 403)
        self.assertIn('error="insufficient_scope"', result.headers["www-authenticate"])
        self.assertIn('scope="resources:read"', result.headers["www-authenticate"])

    def test_get_opens_sse_notification_stream(self) -> None:
        self._ready()
        result = self.client.get_stream()
        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers["content-type"], "text/event-stream")
        events = parse_sse(result.body)
        self.assertEqual(events[0][1]["method"], "notifications/resources/list_changed")
        self.assertNotIn("id", events[0][1])

    def test_cursorless_get_does_not_replay_already_delivered_event(self) -> None:
        self._ready()
        first = parse_sse(self.client.get_stream().body)
        self.assertEqual(1, len(first))
        second = self.client.get_stream()
        self.assertEqual(200, second.status)
        self.assertEqual([], parse_sse(second.body))

    def test_get_requires_event_stream_accept(self) -> None:
        self._ready()
        headers = self.client._base_headers(subsequent=True)
        headers["Accept"] = "application/json"
        result = self.client.request("GET", MCP_PATH, headers=headers)
        self.assertEqual(result.status, 406)

    def test_get_resume_does_not_replay_acknowledged_event(self) -> None:
        self._ready()
        first = parse_sse(self.client.get_stream().body)
        resumed = self.client.get_stream(first[-1][0])
        self.assertEqual(resumed.status, 200)
        self.assertEqual(parse_sse(resumed.body), [])

    def test_get_rejects_unknown_last_event_id(self) -> None:
        self._ready()
        result = self.client.get_stream("not-a-known-cursor")
        self.assertEqual(result.status, 400)

    def test_get_rejects_event_id_from_another_session(self) -> None:
        token = "other-token"
        self.running.state.policy.register_token(
            token,
            make_record(self.running.state, token_id="other", subject="learner-2"),
        )
        other = self._ready(LoopbackClient(*self.running.address, token))
        foreign_event_id = parse_sse(other.get_stream().body)[0][0]
        self._ready(self.client)
        result = self.client.get_stream(foreign_event_id)
        self.assertEqual(result.status, 400)

    def test_delete_terminates_session_and_followup_is_404(self) -> None:
        self._ready()
        self.assertEqual(self.client.delete_session().status, 204)
        self.assertEqual(self.client.ping().status, 404)

    def test_subsequent_request_requires_session_header(self) -> None:
        self._ready()
        session_id = self.client.session_id
        self.client.session_id = None
        result = self.client.ping()
        self.client.session_id = session_id
        self.assertEqual(result.status, 400)

    def test_unknown_session_is_404(self) -> None:
        self._ready()
        self.client.session_id = "unknown-visible-session"
        self.assertEqual(self.client.ping().status, 404)

    def test_subsequent_request_requires_stable_protocol_header(self) -> None:
        self._ready()
        headers = self.client._base_headers(subsequent=True)
        headers["MCP-Protocol-Version"] = "2026-07-28"
        headers.update({"Accept": "application/json, text/event-stream", "Content-Type": "application/json"})
        message = {"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}}
        result = self.client.request("POST", MCP_PATH, headers=headers, body=compact_json(message))
        self.assertEqual(result.status, 400)

    def test_session_cannot_move_to_different_subject(self) -> None:
        self._ready()
        stolen_session = self.client.session_id
        token = "different-subject-token"
        self.running.state.policy.register_token(
            token,
            make_record(self.running.state, token_id="different", subject="learner-2"),
        )
        attacker = LoopbackClient(*self.running.address, token)
        attacker.session_id = stolen_session
        result = attacker.ping()
        self.assertEqual(result.status, 404)
        self.assertNotIn((stolen_session or "").encode(), result.body)

    def test_unicode_principal_completes_session_and_resource_round_trip(self) -> None:
        token = "unicode-principal-token"
        self.running.state.policy.register_token(
            token,
            make_record(
                self.running.state,
                token_id="unicode-principal",
                subject="学习者甲",
                tenant="租户/甲?#",
                revision="授权-v1",
            ),
        )
        client = LoopbackClient(*self.running.address, token)
        self.assertEqual(200, client.initialize().status)
        self.assertEqual(202, client.initialized().status)
        self.assertEqual(200, client.ping().status)
        events = parse_sse(client.list_resources().body)
        self.assertEqual(
            "kb://tenant/%E7%A7%9F%E6%88%B7%2F%E7%94%B2%3F%23/handbook",
            events[0][1]["result"]["resources"][0]["uri"],
        )

    def test_expired_session_is_404(self) -> None:
        self._ready()
        self.clock.advance(61)
        self.assertEqual(self.client.ping().status, 404)

    def test_revision_change_invalidates_existing_session(self) -> None:
        self._ready()
        self.running.state.policy.set_revision("learner-1", "tenant-a", "authz-v2")
        self.assertEqual(self.client.ping().status, 401)

    def test_revocation_invalidates_existing_session(self) -> None:
        self._ready()
        self.running.state.policy.revoke("good")
        self.assertEqual(self.client.ping().status, 401)

    def test_concurrent_ping_requests_are_isolated(self) -> None:
        self._ready()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda request_id: self.client.ping(request_id).status, range(10, 42)))
        self.assertEqual(results, [200] * 32)

    def test_session_and_request_capacity_fail_closed(self) -> None:
        running = RunningServer(TeachingState(clock=self.clock, max_sessions=1))
        with running:
            token = "capacity-token"
            running.state.policy.register_token(token, make_record(running.state, token_id="capacity"))
            first = LoopbackClient(*running.address, token)
            second = LoopbackClient(*running.address, token)
            self.assertEqual(first.initialize().status, 200)
            self.assertEqual(second.initialize().status, 503)

        class FakeRequest:
            def __init__(self) -> None:
                self.sent = b""
                self.closed = False

            def sendall(self, payload: bytes) -> None:
                self.sent += payload

            def shutdown(self, how: int) -> None:
                return

            def close(self) -> None:
                self.closed = True

        bounded = RunningServer(TeachingState(clock=self.clock, max_concurrent_requests=1))
        fake = FakeRequest()
        self.assertTrue(bounded.server._request_slots.acquire(blocking=False))
        try:
            bounded.server.process_request(fake, ("127.0.0.1", 1))
        finally:
            bounded.server._request_slots.release()
            bounded.server.server_close()
        self.assertIn(b"503 Service Unavailable", fake.sent)
        self.assertTrue(fake.closed)

    def test_query_string_token_is_rejected_without_echo(self) -> None:
        result = self.client.request(
            "GET",
            f"{MCP_PATH}?access_token=query-secret",
            headers={"Accept": "text/event-stream"},
        )
        self.assertEqual(result.status, 400)
        self.assertNotIn(b"query-secret", result.body)

    def test_unsupported_http_method_returns_405_and_allow(self) -> None:
        result = self.client.request("PUT", MCP_PATH, headers={"Origin": "https://client.example.test"})
        self.assertEqual(result.status, 405)
        self.assertEqual(result.headers["allow"], "POST, GET, DELETE")

    def test_head_is_a_safe_405_not_default_html(self) -> None:
        result = self.client.request("HEAD", MCP_PATH, headers={"Origin": "https://client.example.test"})
        self.assertEqual(result.status, 405)
        self.assertEqual(result.body, b"")

    def test_oversized_header_is_431(self) -> None:
        result = self.client.request(
            "GET",
            WELL_KNOWN_PATH,
            headers={"Accept": "application/json", "X-Filler": "x" * 2_049},
        )
        self.assertEqual(result.status, 431)

    def test_unknown_notification_is_rejected(self) -> None:
        self._ready()
        result = self.client.post(
            {"jsonrpc": "2.0", "method": "notifications/unknown"},
            subsequent=True,
        )
        self.assertEqual(result.status, 400)

    def test_unsolicited_client_response_is_rejected(self) -> None:
        self._ready()
        result = self.client.post(
            {"jsonrpc": "2.0", "id": "server-1", "result": {}},
            subsequent=True,
        )
        self.assertEqual(result.status, 400)
        self.assertEqual(result.json(), {"error": "unexpected_response"})

    def test_duplicate_authorization_header_is_rejected(self) -> None:
        host, port = self.running.address
        connection = http.client.HTTPConnection(host, port, timeout=2)
        try:
            body = compact_json(self._initialize_message())
            connection.putrequest("POST", MCP_PATH)
            connection.putheader("Authorization", f"Bearer {self.token}")
            connection.putheader("Authorization", f"Bearer {self.token}")
            connection.putheader("Origin", "https://client.example.test")
            connection.putheader("Accept", "application/json, text/event-stream")
            connection.putheader("Content-Type", "application/json")
            connection.putheader("Content-Length", str(len(body)))
            connection.endheaders(body)
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 400)
        finally:
            connection.close()

    def test_error_response_never_contains_token_or_session(self) -> None:
        self._ready()
        session_id = self.client.session_id or ""
        self.running.state.policy.revoke("good")
        result = self.client.ping()
        combined = result.body + repr(result.headers).encode()
        self.assertNotIn(self.token.encode(), combined)
        self.assertNotIn(session_id.encode(), combined)


class CLITests(unittest.TestCase):
    @staticmethod
    def _child_env() -> dict[str, str]:
        return {
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        }

    def test_demo_cli_reports_pass(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "demo"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=self._child_env(),
        )
        self.assertEqual(json.loads(completed.stdout)["verdict"], "PASS")

    def test_attack_cli_reports_block(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "attack"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=self._child_env(),
        )
        self.assertEqual(json.loads(completed.stdout)["verdict"], "BLOCK")

    def test_main_function_is_optimization_safe(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["demo"]), 0)
        self.assertEqual(json.loads(output.getvalue())["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
