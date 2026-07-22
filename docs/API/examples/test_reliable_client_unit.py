"""使用脚本化 Session 精确验证等待、超时和错误边界。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import json
from typing import Any
import unittest

import requests

from reliable_client import ApiHttpError, ApiTransportError, ReliableApiClient


class ScriptedSession:
    def __init__(self, *outcomes: requests.Response | BaseException) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []
        self.closed = False

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        self.calls.append({"method": method, "url": url, **kwargs})
        if not self.outcomes:
            raise AssertionError("ScriptedSession 没有剩余响应")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def close(self) -> None:
        self.closed = True


def json_response(
    status: int,
    payload: object,
    *,
    headers: dict[str, str] | None = None,
    content_type: str = "application/json",
) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.headers["Content-Type"] = content_type
    response.headers.update(headers or {})
    response.encoding = "utf-8"
    response._content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    response._content_consumed = True
    return response


class ReliableApiClientUnitTests(unittest.TestCase):
    def test_timeout_tuple_and_redirect_policy_reach_session(self) -> None:
        session = ScriptedSession(json_response(200, {"ok": True}))
        client = ReliableApiClient(
            "https://api.example.test",
            connect_timeout=1.25,
            read_timeout=4.5,
            session=session,
        )
        result = client._request_json("GET", "/status")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(session.calls[0]["timeout"], (1.25, 4.5))
        self.assertIs(session.calls[0]["allow_redirects"], False)

    def test_retryable_transport_error_uses_finite_backoff(self) -> None:
        session = ScriptedSession(
            requests.exceptions.ReadTimeout("slow"),
            json_response(200, {"ok": True}),
        )
        waits: list[float] = []
        client = ReliableApiClient(
            "https://api.example.test",
            backoff_base=0.25,
            backoff_cap=1,
            jitter_ratio=0,
            sleep=waits.append,
            session=session,
        )
        result = client._request_json("GET", "/status", retry_authorized=True)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(waits, [0.25])
        self.assertEqual(len(session.calls), 2)

    def test_idempotency_header_alone_does_not_authorize_post_retry(self) -> None:
        session = ScriptedSession(
            json_response(503, {"code": "temporary"}),
            json_response(200, {"id": "unexpected"}),
        )
        client = ReliableApiClient("https://api.example.test", session=session)
        with self.assertRaises(ApiHttpError) as raised:
            client._request_json(
                "POST",
                "/jobs",
                json_body={"task": "index"},
                idempotency_key="operation-1",
                retry_authorized=False,
            )
        self.assertEqual(raised.exception.attempts, 1)
        self.assertEqual(len(session.calls), 1)

    def test_retry_after_seconds_are_not_clamped_to_backoff_cap(self) -> None:
        session = ScriptedSession(
            json_response(503, {"code": "busy"}, headers={"Retry-After": "2"}),
            json_response(200, {"ok": True}),
        )
        waits: list[float] = []
        client = ReliableApiClient(
            "https://api.example.test",
            backoff_cap=0.1,
            max_retry_after=5,
            sleep=waits.append,
            session=session,
        )
        result = client._request_json("GET", "/status", retry_authorized=True)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(waits, [2.0])

    def test_retry_after_over_budget_stops_without_early_retry(self) -> None:
        for raw_value in ("2", "9" * 5000):
            with self.subTest(length=len(raw_value)):
                session = ScriptedSession(
                    json_response(
                        503,
                        {"code": "busy"},
                        headers={"Retry-After": raw_value},
                    ),
                    json_response(200, {"ok": True}),
                )
                waits: list[float] = []
                client = ReliableApiClient(
                    "https://api.example.test",
                    max_retry_after=1,
                    sleep=waits.append,
                    session=session,
                )
                with self.assertRaises(ApiHttpError) as raised:
                    client._request_json("GET", "/status", retry_authorized=True)
                self.assertGreater(raised.exception.retry_after or 0, 1)
                self.assertEqual(raised.exception.attempts, 1)
                self.assertEqual(waits, [])
                self.assertEqual(len(session.calls), 1)

    def test_invalid_retry_after_values_fall_back_to_local_delay(self) -> None:
        for raw_value in ("-1", "nonsense", "²", ""):
            with self.subTest(raw_value=raw_value):
                session = ScriptedSession(
                    json_response(
                        503,
                        {"code": "busy"},
                        headers={"Retry-After": raw_value},
                    ),
                    json_response(200, {"ok": True}),
                )
                waits: list[float] = []
                client = ReliableApiClient(
                    "https://api.example.test",
                    backoff_base=0.4,
                    backoff_cap=1,
                    jitter_ratio=0,
                    sleep=waits.append,
                    session=session,
                )
                client._request_json("GET", "/status", retry_authorized=True)
                self.assertEqual(waits, [0.4])

    def test_http_date_retry_after_uses_injected_reference_time(self) -> None:
        now = datetime(2026, 7, 14, 8, 0, tzinfo=timezone.utc)
        future = format_datetime(now + timedelta(seconds=12), usegmt=True)
        past = format_datetime(now - timedelta(seconds=1), usegmt=True)
        self.assertEqual(
            ReliableApiClient._parse_retry_after(future, now=now),
            12.0,
        )
        self.assertEqual(
            ReliableApiClient._parse_retry_after(past, now=now),
            0.0,
        )
        self.assertIsNone(ReliableApiClient._parse_retry_after("14 Jul 2026", now=now))

    def test_other_request_exception_is_normalized_without_retry(self) -> None:
        session = ScriptedSession(requests.exceptions.TooManyRedirects("loop"))
        client = ReliableApiClient("https://api.example.test", session=session)
        with self.assertRaises(ApiTransportError) as raised:
            client._request_json("GET", "/status", retry_authorized=True)
        self.assertEqual(raised.exception.attempts, 1)
        self.assertEqual(len(session.calls), 1)

    def test_tls_error_is_normalized_without_retry(self) -> None:
        """SSLError 继承 ConnectionError，不能误入可重试传输分支。"""

        session = ScriptedSession(requests.exceptions.SSLError("untrusted certificate"))
        client = ReliableApiClient("https://api.example.test", session=session)
        with self.assertRaises(ApiTransportError) as raised:
            client._request_json("GET", "/status", retry_authorized=True)
        self.assertEqual(raised.exception.attempts, 1)
        self.assertIn("TLS", str(raised.exception))
        self.assertEqual(len(session.calls), 1)

    def test_injected_session_remains_caller_owned(self) -> None:
        session = ScriptedSession(json_response(200, {"ok": True}))
        with ReliableApiClient("https://api.example.test", session=session) as client:
            client._request_json("GET", "/status")
        self.assertFalse(session.closed)

    def test_owned_session_ignores_environment_proxy_and_netrc(self) -> None:
        client = ReliableApiClient("http://127.0.0.1:8765")
        try:
            self.assertIsInstance(client.session, requests.Session)
            self.assertFalse(client.session.trust_env)
        finally:
            client.close()

    def test_constructor_rejects_invalid_configuration(self) -> None:
        invalid_cases = [
            ({"base_url": "api.example.test"}, "base_url"),
            ({"base_url": "https://user:secret@example.test"}, "凭据"),
            ({"base_url": "https://example.test?token=x"}, "query"),
            ({"base_url": "https://example.test", "max_attempts": True}, "max_attempts"),
            ({"base_url": "https://example.test", "connect_timeout": 0}, "正数"),
            ({"base_url": "https://example.test", "read_timeout": float("inf")}, "有限"),
            ({"base_url": "https://example.test", "jitter_ratio": 1.1}, "0 到 1"),
        ]
        for kwargs, message in invalid_cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(ValueError, message):
                    ReliableApiClient(**kwargs)

    def test_idempotency_key_and_pagination_bounds_are_validated(self) -> None:
        session = ScriptedSession()
        client = ReliableApiClient("https://api.example.test", session=session)
        for key in (
            "",
            " key",
            "key ",
            "two words",
            "line\nbreak",
            "操作-一",
            3,
            None,
        ):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    client.create_job({}, idempotency_key=key)  # type: ignore[arg-type]
        for kwargs in ({"page_size": True}, {"max_pages": 0}, {"endpoint": "items"}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    list(client.iter_items(**kwargs))


if __name__ == "__main__":
    unittest.main()
