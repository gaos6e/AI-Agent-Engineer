"""Reliable-client integration tests using a real loopback HTTP server."""

from __future__ import annotations

from threading import Thread
import unittest

from mock_api_server import create_server
from reliable_client import ApiHttpError, ApiResponseError, ReliableApiClient


class ReliableApiClientIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = create_server(port=0)
        self.thread = Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": 0.01},
            daemon=True,
        )
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"
        self.client = self._new_client()

    def tearDown(self) -> None:
        self.client.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.assertFalse(self.thread.is_alive(), "teaching-server thread did not stop in time")

    def _new_client(self, **overrides: object) -> ReliableApiClient:
        options: dict[str, object] = {
            "backoff_base": 0,
            "backoff_cap": 0,
            "jitter_ratio": 0,
            "sleep": lambda _: None,
        }
        options.update(overrides)
        return ReliableApiClient(self.base_url, **options)

    def _replace_client(self, **overrides: object) -> None:
        self.client.close()
        self.client = self._new_client(**overrides)

    def test_cursor_pagination_returns_every_item(self) -> None:
        ids = [item["id"] for item in self.client.iter_items()]
        self.assertEqual(ids, ["item-1", "item-2", "item-3"])

    def test_repeated_cursor_is_rejected(self) -> None:
        with self.assertRaisesRegex(ApiResponseError, "repeated next_cursor"):
            list(self.client.iter_items(endpoint="/looping-items"))

    def test_max_pages_stops_endless_pagination(self) -> None:
        iterator = self.client.iter_items(max_pages=2, endpoint="/endless-items")
        self.assertEqual(next(iterator)["id"], "endless-0")
        self.assertEqual(next(iterator)["id"], "endless-1")
        with self.assertRaisesRegex(ApiResponseError, "maximum of 2 pages"):
            next(iterator)

    def test_items_schema_is_validated(self) -> None:
        with self.assertRaisesRegex(ApiResponseError, "items array"):
            list(self.client.iter_items(endpoint="/bad-items"))

    def test_cursor_schema_is_validated(self) -> None:
        with self.assertRaisesRegex(ApiResponseError, "next_cursor has an invalid format"):
            list(self.client.iter_items(endpoint="/bad-cursor"))

    def test_retry_recovers_from_two_temporary_failures(self) -> None:
        result = self.client.get_flaky_status()
        self.assertEqual(result, {"ok": True, "attempt": 3})
        self.assertEqual(self.server.state["flaky_attempts"], 3)

    def test_retry_exhaustion_preserves_attempt_count(self) -> None:
        self._replace_client(max_attempts=2)
        with self.assertRaises(ApiHttpError) as raised:
            self.client.get_flaky_status()
        self.assertEqual(raised.exception.status, 503)
        self.assertEqual(raised.exception.attempts, 2)
        self.assertEqual(self.server.state["flaky_attempts"], 2)

    def test_long_retry_after_is_not_retried_early(self) -> None:
        with self.assertRaises(ApiHttpError) as raised:
            self.client._request_json("GET", "/retry-later", retry_authorized=True)
        self.assertEqual(raised.exception.status, 503)
        self.assertEqual(raised.exception.retry_after, 120.0)
        self.assertEqual(raised.exception.attempts, 1)
        self.assertEqual(self.server.state["retry_later_attempts"], 1)

    def test_same_idempotency_key_returns_same_job(self) -> None:
        payload = {"task": "index", "document_id": "doc-1"}
        first = self.client.create_job(payload, idempotency_key="operation-1")
        second = self.client.create_job(payload, idempotency_key="operation-1")
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.server.state["jobs"]), 1)

    def test_same_key_with_different_payload_is_conflict(self) -> None:
        self.client.create_job({"value": 1}, idempotency_key="operation-2")
        with self.assertRaises(ApiHttpError) as raised:
            self.client.create_job({"value": 2}, idempotency_key="operation-2")
        self.assertEqual(raised.exception.status, 409)
        self.assertEqual(raised.exception.code, "idempotency_conflict")
        self.assertEqual(raised.exception.attempts, 1)

    def test_lost_create_response_reuses_key_without_duplicate(self) -> None:
        self.server.state["fail_first_job_response"] = True
        result = self.client.create_job(
            {"task": "index", "document_id": "doc-2"},
            idempotency_key="operation-3",
        )
        self.assertEqual(result["id"], "job-1")
        self.assertEqual(len(self.server.state["jobs"]), 1)
        self.assertEqual(self.server.state["job_requests"], 2)

    def test_invalid_json_has_distinct_error(self) -> None:
        with self.assertRaisesRegex(ApiResponseError, "cannot be parsed"):
            self.client._request_json("GET", "/bad-json")

    def test_wrong_content_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(ApiResponseError, "Content-Type='text/plain'"):
            self.client._request_json("GET", "/text-json")

    def test_no_content_returns_none(self) -> None:
        self.assertIsNone(self.client._request_json("GET", "/no-content"))

    def test_redirect_is_not_followed(self) -> None:
        with self.assertRaises(ApiHttpError) as raised:
            self.client._request_json("GET", "/redirect")
        self.assertEqual(raised.exception.status, 302)

    def test_not_found_preserves_machine_error(self) -> None:
        with self.assertRaises(ApiHttpError) as raised:
            self.client._request_json("GET", "/missing")
        self.assertEqual(raised.exception.status, 404)
        self.assertEqual(raised.exception.code, "not_found")
        self.assertRegex(raised.exception.request_id or "", r"^req-\d{4}$")


if __name__ == "__main__":
    unittest.main()
