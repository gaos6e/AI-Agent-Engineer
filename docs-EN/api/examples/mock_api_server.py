"""A loopback-only teaching HTTP API with reproducible failures and contracts."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Lock
from typing import Any
from urllib.parse import parse_qs, urlsplit


class LearningApiServer(ThreadingHTTPServer):
    state: dict[str, Any]
    state_lock: Lock


class LearningApiHandler(BaseHTTPRequestHandler):
    server: LearningApiServer

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/items":
            cursor = query.get("cursor", [None])[0]
            if cursor is None:
                self._send_json(
                    200,
                    {
                        "items": [
                            {"id": "item-1", "name": "HTTP"},
                            {"id": "item-2", "name": "pagination"},
                        ],
                        "next_cursor": "page-2",
                    },
                )
            elif cursor == "page-2":
                self._send_json(
                    200,
                    {"items": [{"id": "item-3", "name": "retry"}], "next_cursor": None},
                )
            else:
                self._send_problem(400, "invalid_cursor", "the cursor is not recognized")
            return

        if parsed.path == "/looping-items":
            self._send_json(
                200,
                {
                    "items": [{"id": "loop-item", "name": "repeated cursor"}],
                    "next_cursor": "loop",
                },
            )
            return

        if parsed.path == "/endless-items":
            cursor = query.get("cursor", ["page-0"])[0]
            try:
                current = int(cursor.removeprefix("page-"))
            except ValueError:
                self._send_problem(400, "invalid_cursor", "the cursor is not recognized")
                return
            self._send_json(
                200,
                {
                    "items": [{"id": f"endless-{current}", "name": "bounded pagination"}],
                    "next_cursor": f"page-{current + 1}",
                },
            )
            return

        if parsed.path == "/bad-items":
            self._send_json(200, {"items": "not-an-array", "next_cursor": None})
            return

        if parsed.path == "/bad-cursor":
            self._send_json(200, {"items": [], "next_cursor": 42})
            return

        if parsed.path == "/flaky":
            with self.server.state_lock:
                self.server.state["flaky_attempts"] += 1
                attempt = self.server.state["flaky_attempts"]
            if attempt <= 2:
                self._send_problem(
                    503,
                    "temporarily_unavailable",
                    "the teaching service deliberately fails twice",
                    headers={"Retry-After": "0"},
                )
            else:
                self._send_json(200, {"ok": True, "attempt": attempt})
            return

        if parsed.path == "/retry-later":
            with self.server.state_lock:
                self.server.state["retry_later_attempts"] += 1
            self._send_problem(
                503,
                "retry_later",
                "an outer scheduler must defer this request rather than retrying early",
                headers={"Retry-After": "120"},
            )
            return

        if parsed.path == "/bad-json":
            self._send_bytes(200, b'{"broken": ', content_type="application/json")
            return

        if parsed.path == "/text-json":
            self._send_json(200, {"looks": "json"}, content_type="text/plain")
            return

        if parsed.path == "/no-content":
            self._send_empty(204)
            return

        if parsed.path == "/redirect":
            self._send_empty(302, headers={"Location": "/items"})
            return

        self._send_problem(404, "not_found", "the resource does not exist")

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/jobs":
            self._send_problem(404, "not_found", "the resource does not exist")
            return

        idempotency_key = self.headers.get("Idempotency-Key")
        if not idempotency_key:
            self._send_problem(400, "missing_idempotency_key", "Idempotency-Key is required")
            return

        raw_length = self.headers.get("Content-Length", "0")
        try:
            content_length = int(raw_length)
        except ValueError:
            self._send_problem(400, "invalid_content_length", "Content-Length is invalid")
            return
        if not 0 <= content_length <= 1_000_000:
            self._send_problem(413, "payload_too_large", "the teaching service accepts at most 1 MB")
            return

        try:
            payload = json.loads(self.rfile.read(content_length))
        except (ValueError, json.JSONDecodeError):
            self._send_problem(400, "invalid_json", "the request body is not valid JSON")
            return
        if not isinstance(payload, dict):
            self._send_problem(422, "invalid_payload", "the request body must be a JSON object")
            return

        with self.server.state_lock:
            self.server.state["job_requests"] += 1
            existing = self.server.state["jobs"].get(idempotency_key)
            fail_after_create = False
            if existing is not None:
                if existing["payload"] != payload:
                    conflict = True
                    job = None
                else:
                    conflict = False
                    job = existing["job"]
            else:
                conflict = False
                job = {
                    "id": f"job-{len(self.server.state['jobs']) + 1}",
                    "status": "created",
                    "payload": payload,
                }
                self.server.state["jobs"][idempotency_key] = {
                    "payload": payload,
                    "job": job,
                }
                if (
                    self.server.state["fail_first_job_response"]
                    and not self.server.state["job_failure_sent"]
                ):
                    self.server.state["job_failure_sent"] = True
                    fail_after_create = True

        if fail_after_create:
            self._send_problem(
                503,
                "response_lost_after_create",
                "the job was saved but the teaching service deliberately returned a temporary failure",
                headers={"Retry-After": "0"},
            )
        elif conflict:
            self._send_problem(409, "idempotency_conflict", "the same key was used for a different payload")
        elif existing is not None:
            self._send_json(200, job)
        else:
            self._send_json(201, job)

    def _next_request_id(self) -> str:
        with self.server.state_lock:
            self.server.state["request_counter"] += 1
            value = self.server.state["request_counter"]
        return f"req-{value:04d}"

    def _send_problem(
        self,
        status: int,
        code: str,
        detail: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._send_json(
            status,
            {
                "type": f"https://example.invalid/problems/{code}",
                "title": code.replace("_", " "),
                "status": status,
                "code": code,
                "detail": detail,
            },
            content_type="application/problem+json",
            headers=headers,
        )

    def _send_json(
        self,
        status: int,
        payload: Any,
        *,
        content_type: str = "application/json",
        headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, body, content_type=content_type, headers=headers)

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        *,
        content_type: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Request-ID", self._next_request_id())
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_empty(
        self, status: int, *, headers: dict[str, str] | None = None
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.send_header("X-Request-ID", self._next_request_id())
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()

    def log_message(self, *_: object) -> None:
        """Suppress default access logs so practice output stays readable."""


def create_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    fail_first_job_response: bool = False,
) -> LearningApiServer:
    """Create a fresh, loopback-friendly teaching API server."""

    server = LearningApiServer((host, port), LearningApiHandler)
    server.state = {
        "flaky_attempts": 0,
        "retry_later_attempts": 0,
        "jobs": {},
        "job_requests": 0,
        "fail_first_job_response": fail_first_job_response,
        "job_failure_sent": False,
        "request_counter": 0,
    }
    server.state_lock = Lock()
    return server


def main() -> None:
    server = create_server()
    print("Teaching API started at http://127.0.0.1:8765")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
