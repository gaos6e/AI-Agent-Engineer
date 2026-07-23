"""Loopback Streamable HTTP + OAuth resource-boundary teaching project.

This module intentionally implements only a small, strict subset of MCP
2025-11-25.  It performs real HTTP round trips on 127.0.0.1, while access
tokens are validated by an in-memory offline policy.  It is not an OAuth
authorization server, a JWT verifier, or an MCP conformance implementation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import http.client
import json
import math
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Iterable
from urllib.parse import quote, urlsplit


PROTOCOL_VERSION = "2025-11-25"
MCP_PATH = "/mcp"
WELL_KNOWN_PATH = "/.well-known/oauth-protected-resource/mcp"
ROOT_WELL_KNOWN_PATH = "/.well-known/oauth-protected-resource"
AUTHORIZATION_SERVER = "https://auth.example.test"
ALLOWED_ORIGINS = frozenset({"https://client.example.test", "http://127.0.0.1"})
ALL_SCOPES = frozenset(
    {"mcp:connect", "mcp:use", "mcp:stream", "mcp:session", "resources:read"}
)
MAX_BODY_BYTES = 16 * 1024
MAX_RESPONSE_BYTES = 64 * 1024
MAX_JSON_DEPTH = 64
MAX_HEADER_COUNT = 32
MAX_HEADER_VALUE_BYTES = 2 * 1024
MAX_HEADER_BYTES = 12 * 1024
MAX_PATH_BYTES = 2 * 1024
MAX_SESSIONS = 8
SESSION_TTL_SECONDS = 60.0
MAX_SSE_EVENTS = 16
MAX_CONCURRENT_REQUESTS = 64
REQUEST_TIMEOUT_SECONDS = 2.0
BEARER_TOKEN_RE = re.compile(r"^[A-Za-z0-9._~+/-]+=*$")


class BoundaryError(Exception):
    """A safe error intended to cross the local HTTP boundary."""

    def __init__(
        self,
        status: int,
        public_code: str,
        *,
        required_scope: str | None = None,
        allow: str | None = None,
    ) -> None:
        super().__init__(public_code)
        self.status = status
        self.public_code = public_code
        self.required_scope = required_scope
        self.allow = allow


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _pairs_to_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_excessive_json_nesting(text: str) -> None:
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
            if depth > MAX_JSON_DEPTH:
                raise BoundaryError(400, "json_depth_exceeded")
        elif character in "]}":
            depth = max(0, depth - 1)


def strict_json_loads(raw: bytes) -> Any:
    """Decode one UTF-8 JSON value while rejecting duplicate keys and NaN."""

    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise BoundaryError(400, "invalid_utf8") from exc
    _reject_excessive_json_nesting(text)
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_to_object,
            parse_constant=_reject_constant,
        )
    except (ValueError, TypeError, RecursionError) as exc:
        raise BoundaryError(400, "invalid_json") from exc


def compact_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _token_digest(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


def _bounded_utf8_text(value: Any, *, maximum: int = MAX_HEADER_VALUE_BYTES) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        return False
    return len(encoded) <= maximum


def _tenant_resource_uri(tenant: str) -> str:
    """Build an RFC 3986 URI without treating a tenant label as authority syntax."""

    return f"kb://tenant/{quote(tenant, safe='')}/handbook"


@dataclass(frozen=True)
class TokenRecord:
    """Claims returned by the teaching policy after offline token lookup."""

    token_id: str
    issuer: str
    audience: str
    resource: str
    authorization_resource: str
    token_resource: str
    subject: str
    tenant: str
    scopes: frozenset[str]
    authorization_revision: str
    expires_at: float
    active: bool = True


class OfflineTokenPolicy:
    """Explicitly non-production token policy for resource-server tests.

    Tokens are stored only as SHA-256 lookup keys.  The class models the
    *result* of signature/introspection work; it does not perform that work.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self.resource_uri = ""
        self.expected_issuer = AUTHORIZATION_SERVER
        self._records: dict[bytes, TokenRecord] = {}
        self._current_revisions: dict[tuple[str, str], str] = {}
        self._allowed_tenants: dict[str, frozenset[str]] = {}
        self._revoked_token_ids: set[str] = set()
        self._lock = threading.RLock()

    def configure_resource(self, resource_uri: str) -> None:
        parsed = urlsplit(resource_uri)
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.path != MCP_PATH:
            raise ValueError("teaching resource must be the exact 127.0.0.1 loopback MCP URI")
        if parsed.query or parsed.fragment:
            raise ValueError("resource URI cannot contain query or fragment")
        with self._lock:
            if self.resource_uri and self.resource_uri != resource_uri:
                raise ValueError("resource URI is already configured")
            self.resource_uri = resource_uri

    def register_token(self, opaque_token: str, record: TokenRecord) -> None:
        """Register fixture claims; malformed claims are allowed for negative tests."""

        if not BEARER_TOKEN_RE.fullmatch(opaque_token) or len(opaque_token) > 512:
            raise ValueError("fixture token must be a 1..512 character RFC 6750 b64token subset")
        string_claims = (
            record.token_id,
            record.issuer,
            record.audience,
            record.resource,
            record.authorization_resource,
            record.token_resource,
            record.subject,
            record.tenant,
            record.authorization_revision,
        )
        if any(not _bounded_utf8_text(value) for value in string_claims):
            raise ValueError("fixture string claims must contain 1..2048 UTF-8 bytes")
        if (
            not isinstance(record.scopes, frozenset)
            or not record.scopes
            or any(not _bounded_utf8_text(scope) for scope in record.scopes)
            or len(record.scopes) > 64
        ):
            raise ValueError("fixture scopes must be a nonempty bounded frozenset of strings")
        if (
            isinstance(record.expires_at, bool)
            or not isinstance(record.expires_at, (int, float))
            or not math.isfinite(record.expires_at)
            or not isinstance(record.active, bool)
        ):
            raise ValueError("fixture expiry and active claims are invalid")
        digest = _token_digest(opaque_token)
        with self._lock:
            if digest in self._records:
                raise ValueError("duplicate fixture token")
            self._records[digest] = copy.deepcopy(record)
            self._current_revisions.setdefault(
                (record.subject, record.tenant), record.authorization_revision
            )
            current = self._allowed_tenants.get(record.subject, frozenset())
            self._allowed_tenants[record.subject] = current | {record.tenant}

    def set_allowed_tenants(self, subject: str, tenants: Iterable[str]) -> None:
        normalized = frozenset(tenants)
        if (
            not _bounded_utf8_text(subject)
            or not normalized
            or any(not _bounded_utf8_text(item) for item in normalized)
        ):
            raise ValueError("subject and at least one nonempty tenant are required")
        with self._lock:
            self._allowed_tenants[subject] = normalized

    def set_revision(self, subject: str, tenant: str, revision: str) -> None:
        if not all(_bounded_utf8_text(value) for value in (subject, tenant, revision)):
            raise ValueError("subject, tenant, and revision are required")
        with self._lock:
            self._current_revisions[(subject, tenant)] = revision

    def revoke(self, token_id: str) -> None:
        if not _bounded_utf8_text(token_id):
            raise ValueError("token_id is required")
        with self._lock:
            self._revoked_token_ids.add(token_id)

    def authenticate(self, authorization: str | None) -> TokenRecord:
        if authorization is None:
            raise BoundaryError(401, "authorization_required")
        if len(authorization) < 8 or authorization[:7].lower() != "bearer ":
            raise BoundaryError(401, "invalid_token")
        token = authorization[7:]
        if not BEARER_TOKEN_RE.fullmatch(token) or len(token) > 512:
            raise BoundaryError(401, "invalid_token")
        digest = _token_digest(token)
        with self._lock:
            record = self._records.get(digest)
            if record is None:
                raise BoundaryError(401, "invalid_token")
            candidate = copy.deepcopy(record)
            expected_revision = self._current_revisions.get(
                (candidate.subject, candidate.tenant)
            )
            revoked = candidate.token_id in self._revoked_token_ids

        # These are already parsed application claims, not secret MACs.
        # Exact Unicode equality is the correct operation; compare_digest on
        # str is ASCII-only and can turn valid non-ASCII identities into 500s.
        binding_ok = bool(self.resource_uri) and all(
            item == self.resource_uri
            for item in (
                candidate.audience,
                candidate.resource,
                candidate.authorization_resource,
                candidate.token_resource,
            )
        )
        if (
            not candidate.active
            or revoked
            or candidate.expires_at <= self.clock()
            or candidate.issuer != self.expected_issuer
            or not binding_ok
            or expected_revision is None
            or candidate.authorization_revision != expected_revision
        ):
            raise BoundaryError(401, "invalid_token")
        return candidate

    def authorize(self, record: TokenRecord, required_scope: str) -> None:
        with self._lock:
            allowed_tenants = self._allowed_tenants.get(record.subject, frozenset())
        if record.tenant not in allowed_tenants:
            raise BoundaryError(403, "forbidden")
        if required_scope not in record.scopes:
            raise BoundaryError(
                403,
                "insufficient_scope",
                required_scope=required_scope,
            )


@dataclass
class Session:
    session_id: str
    subject: str
    tenant: str
    authorization_revision: str
    expires_at: float
    phase: str = "awaiting_initialized"
    event_namespace: str = field(default_factory=lambda: secrets.token_hex(8))
    event_counter: int = 0
    events: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    last_implicit_event_id: str | None = None


class TeachingState:
    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_sessions: int = MAX_SESSIONS,
        session_ttl: float = SESSION_TTL_SECONDS,
        max_concurrent_requests: int = MAX_CONCURRENT_REQUESTS,
    ) -> None:
        if max_sessions < 1 or session_ttl <= 0 or max_concurrent_requests < 1:
            raise ValueError("positive session limits are required")
        self.clock = clock
        self.max_sessions = max_sessions
        self.session_ttl = session_ttl
        self.max_concurrent_requests = max_concurrent_requests
        self.policy = OfflineTokenPolicy(clock)
        self.resource_uri = ""
        self.metadata_uri = ""
        self.sessions: dict[str, Session] = {}
        self.lock = threading.RLock()

    def configure_endpoint(self, host: str, port: int) -> None:
        if host != "127.0.0.1" or not (1 <= port <= 65535):
            raise ValueError("server must bind an allocated 127.0.0.1 port")
        # This HTTP URI is deliberate for a dependency-free loopback exercise.
        # It tests the MCP metadata/challenge *shape*, but is not an RFC 9728
        # protected-resource deployment: RFC 9728 resource identifiers use
        # HTTPS, so production interop needs TLS and a conforming endpoint.
        self.resource_uri = f"http://{host}:{port}{MCP_PATH}"
        self.metadata_uri = f"http://{host}:{port}{WELL_KNOWN_PATH}"
        self.policy.configure_resource(self.resource_uri)

    def create_session(self, principal: TokenRecord) -> Session:
        with self.lock:
            now = self.clock()
            expired = [sid for sid, item in self.sessions.items() if item.expires_at <= now]
            for sid in expired:
                del self.sessions[sid]
            if len(self.sessions) >= self.max_sessions:
                raise BoundaryError(503, "session_capacity_exceeded")
            session_id = secrets.token_urlsafe(32)
            while session_id in self.sessions:
                session_id = secrets.token_urlsafe(32)
            session = Session(
                session_id=session_id,
                subject=principal.subject,
                tenant=principal.tenant,
                authorization_revision=principal.authorization_revision,
                expires_at=now + self.session_ttl,
            )
            self.sessions[session_id] = session
            return copy.deepcopy(session)

    def lookup_session(self, session_id: str | None, principal: TokenRecord) -> Session:
        if not session_id or len(session_id) > 256 or any(
            ord(char) < 0x21 or ord(char) > 0x7E for char in session_id
        ):
            raise BoundaryError(400, "missing_or_invalid_session")
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                raise BoundaryError(404, "session_not_found")
            if session.expires_at <= self.clock():
                del self.sessions[session_id]
                raise BoundaryError(404, "session_not_found")
            if (
                session.subject != principal.subject
                or session.tenant != principal.tenant
                or session.authorization_revision != principal.authorization_revision
            ):
                # Avoid confirming that a session belongs to another principal.
                raise BoundaryError(404, "session_not_found")
            return copy.deepcopy(session)

    def mark_initialized(self, session_id: str) -> None:
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                raise BoundaryError(404, "session_not_found")
            if session.phase != "awaiting_initialized":
                raise BoundaryError(400, "invalid_lifecycle")
            session.phase = "ready"
            event_id = self._allocate_event_id_locked(session, "get")
            session.events.append(
                (
                    event_id,
                    {
                        "jsonrpc": "2.0",
                        "method": "notifications/resources/list_changed",
                    },
                )
            )

    @staticmethod
    def _allocate_event_id_locked(session: Session, stream: str) -> str:
        session.event_counter += 1
        return f"{stream}-{session.event_namespace}:{session.event_counter:08d}"

    def allocate_event_id(self, session_id: str, stream: str) -> str:
        if stream not in {"get", "post"}:
            raise ValueError("unknown teaching stream")
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                raise BoundaryError(404, "session_not_found")
            return self._allocate_event_id_locked(session, stream)

    def require_ready(self, session_id: str) -> Session:
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                raise BoundaryError(404, "session_not_found")
            if session.phase != "ready":
                raise BoundaryError(400, "invalid_lifecycle")
            return copy.deepcopy(session)

    def delete_session(self, session_id: str) -> None:
        with self.lock:
            if session_id not in self.sessions:
                raise BoundaryError(404, "session_not_found")
            del self.sessions[session_id]

    def resumed_events(
        self,
        session_id: str,
        last_event_id: str | None,
    ) -> list[tuple[str, dict[str, Any]]]:
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                raise BoundaryError(404, "session_not_found")
            if len(session.events) > MAX_SSE_EVENTS:
                raise BoundaryError(503, "event_capacity_exceeded")
            if last_event_id is not None:
                positions = [
                    index
                    for index, item in enumerate(session.events)
                    if item[0] == last_event_id
                ]
                if len(positions) != 1:
                    raise BoundaryError(400, "invalid_last_event_id")
                return copy.deepcopy(session.events[positions[0] + 1 :])

            start = 0
            if session.last_implicit_event_id is not None:
                positions = [
                    index
                    for index, item in enumerate(session.events)
                    if item[0] == session.last_implicit_event_id
                ]
                if len(positions) != 1:
                    raise BoundaryError(503, "event_cursor_state_invalid")
                start = positions[0] + 1
            selected = session.events[start:]
            if selected:
                # A cursor-less GET is an at-most-once teaching poll. Clients
                # that need replay must reconnect with an explicit known ID.
                session.last_implicit_event_id = selected[-1][0]
            return copy.deepcopy(selected)


def _media_types(value: str) -> set[str]:
    media: set[str] = set()
    for part in value.split(","):
        segments = [segment.strip() for segment in part.split(";")]
        item = segments[0].lower()
        quality = 1.0
        for parameter in segments[1:]:
            name, separator, raw_value = parameter.partition("=")
            if separator and name.strip().lower() == "q":
                try:
                    quality = float(raw_value.strip())
                except ValueError:
                    quality = 0.0
        if item and 0.0 < quality <= 1.0:
            media.add(item)
    return media


def _validate_jsonrpc_envelope(message: Any) -> str:
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        raise BoundaryError(400, "invalid_jsonrpc")
    has_method = "method" in message
    has_id = "id" in message
    if has_method:
        if not isinstance(message["method"], str) or not message["method"]:
            raise BoundaryError(400, "invalid_jsonrpc")
        allowed = {"jsonrpc", "method", "params", "id"}
        if set(message) - allowed:
            raise BoundaryError(400, "invalid_jsonrpc")
        if "params" in message and not isinstance(message["params"], dict):
            raise BoundaryError(400, "invalid_jsonrpc")
        if has_id and (
            isinstance(message["id"], bool)
            or not isinstance(message["id"], (str, int))
        ):
            raise BoundaryError(400, "invalid_jsonrpc")
        return "request" if has_id else "notification"
    if not has_id or isinstance(message["id"], bool) or not isinstance(message["id"], (str, int)):
        raise BoundaryError(400, "invalid_jsonrpc")
    if ("result" in message) == ("error" in message):
        raise BoundaryError(400, "invalid_jsonrpc")
    allowed = {"jsonrpc", "id", "result" if "result" in message else "error"}
    if set(message) != allowed:
        raise BoundaryError(400, "invalid_jsonrpc")
    return "response"


class LoopbackMCPHandler(BaseHTTPRequestHandler):
    server_version = "MCPTeachingServer/1"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(REQUEST_TIMEOUT_SECONDS)

    @property
    def state(self) -> TeachingState:
        return self.server.state  # type: ignore[attr-defined,no-any-return]

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # The project deliberately avoids raw request/header logging.
        return

    def _single_header(self, name: str, *, required: bool = False) -> str | None:
        values = self.headers.get_all(name, failobj=[])
        if len(values) > 1:
            raise BoundaryError(400, "duplicate_header")
        if not values:
            if required:
                raise BoundaryError(400, "missing_header")
            return None
        value = values[0].strip()
        if not value and required:
            raise BoundaryError(400, "missing_header")
        if len(value.encode("utf-8")) > MAX_HEADER_VALUE_BYTES:
            raise BoundaryError(431, "header_too_large")
        return value

    def _validate_common(self) -> tuple[str, str]:
        if len(self.headers) > MAX_HEADER_COUNT:
            raise BoundaryError(431, "too_many_headers")
        header_bytes = 0
        for name, value in self.headers.items():
            try:
                encoded_name = name.encode("ascii", errors="strict")
                encoded_value = value.encode("utf-8", errors="strict")
            except UnicodeError as exc:
                raise BoundaryError(400, "invalid_header") from exc
            if not encoded_name or len(encoded_name) > 128 or len(encoded_value) > MAX_HEADER_VALUE_BYTES:
                raise BoundaryError(431, "header_too_large")
            header_bytes += len(encoded_name) + len(encoded_value) + 4
        if header_bytes > MAX_HEADER_BYTES:
            raise BoundaryError(431, "headers_too_large")
        if len(self.path.encode("utf-8")) > MAX_PATH_BYTES:
            raise BoundaryError(414, "uri_too_long")
        parsed = urlsplit(self.path)
        if parsed.query or parsed.fragment:
            raise BoundaryError(400, "query_not_allowed")
        origin = self._single_header("Origin")
        if origin is not None and origin not in ALLOWED_ORIGINS:
            raise BoundaryError(403, "invalid_origin")
        return parsed.path, origin or ""

    def _authenticate(self, required_scope: str) -> TokenRecord:
        authorization = self._single_header("Authorization")
        try:
            principal = self.state.policy.authenticate(authorization)
        except BoundaryError as error:
            if error.status == 401:
                raise BoundaryError(
                    401,
                    error.public_code,
                    required_scope=required_scope,
                ) from error
            raise
        self.state.policy.authorize(principal, required_scope)
        return principal

    def _validate_protocol_header(self) -> None:
        version = self._single_header("MCP-Protocol-Version", required=True)
        if version != PROTOCOL_VERSION:
            raise BoundaryError(400, "unsupported_protocol_version")

    def _read_json_body(self) -> Any:
        if self._single_header("Transfer-Encoding") is not None:
            raise BoundaryError(400, "transfer_encoding_not_supported")
        content_type = self._single_header("Content-Type", required=True)
        content_type_parts = [item.strip().lower() for item in (content_type or "").split(";")]
        if (
            not content_type_parts
            or content_type_parts[0] != "application/json"
            or any(item not in {"charset=utf-8"} for item in content_type_parts[1:])
        ):
            raise BoundaryError(415, "unsupported_media_type")
        length_text = self._single_header("Content-Length", required=True)
        try:
            length = int(length_text or "")
        except ValueError as exc:
            raise BoundaryError(400, "invalid_content_length") from exc
        if length < 1:
            raise BoundaryError(400, "empty_body")
        if length > MAX_BODY_BYTES:
            self.close_connection = True
            raise BoundaryError(413, "body_too_large")
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise BoundaryError(400, "truncated_body")
        return strict_json_loads(raw)

    def _send_bytes(
        self,
        status: int,
        body: bytes = b"",
        *,
        content_type: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        if len(body) > MAX_RESPONSE_BYTES:
            raise RuntimeError("response exceeds teaching cap")
        self.send_response(status)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if content_type is not None:
            self.send_header("Content-Type", content_type)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _send_json(
        self,
        status: int,
        value: Any,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._send_bytes(
            status,
            compact_json(value),
            content_type="application/json",
            headers=headers,
        )

    def _challenge(self, error: BoundaryError) -> str:
        params = [f'resource_metadata="{self.state.metadata_uri}"']
        if error.status == 401:
            if error.public_code == "invalid_token":
                params.append('error="invalid_token"')
            if error.required_scope:
                params.append(f'scope="{error.required_scope}"')
        elif error.required_scope:
            params.extend(
                [
                    'error="insufficient_scope"',
                    f'scope="{error.required_scope}"',
                ]
            )
        return "Bearer " + ", ".join(params)

    def _handle_boundary_error(self, error: BoundaryError) -> None:
        # Closing prevents unread request bodies from being interpreted as a
        # second request after an early header/origin/auth failure.
        self.close_connection = True
        headers: dict[str, str] = {}
        if error.status == 401 or error.required_scope is not None:
            headers["WWW-Authenticate"] = self._challenge(error)
        if error.allow:
            headers["Allow"] = error.allow
        self._send_json(error.status, {"error": error.public_code}, headers=headers)

    def do_POST(self) -> None:  # noqa: N802
        try:
            path, _origin = self._validate_common()
            if path != MCP_PATH:
                raise BoundaryError(404, "not_found")
            accept = _media_types(self._single_header("Accept", required=True) or "")
            if not {"application/json", "text/event-stream"} <= accept:
                raise BoundaryError(406, "not_acceptable")
            message = self._read_json_body()
            envelope = _validate_jsonrpc_envelope(message)
            if envelope == "request" and message["method"] == "initialize":
                self._handle_initialize(message)
                return
            self._handle_subsequent_post(message, envelope)
        except BoundaryError as error:
            self._handle_boundary_error(error)

    def _handle_initialize(self, message: dict[str, Any]) -> None:
        if self._single_header("MCP-Session-Id") is not None:
            raise BoundaryError(400, "initialization_must_not_reuse_session")
        supplied_version = self._single_header("MCP-Protocol-Version")
        if supplied_version is not None and supplied_version != PROTOCOL_VERSION:
            raise BoundaryError(400, "unsupported_protocol_version")
        principal = self._authenticate("mcp:connect")
        if set(message) != {"jsonrpc", "id", "method", "params"}:
            raise BoundaryError(400, "invalid_initialize")
        params = message["params"]
        if not isinstance(params, dict) or set(params) != {
            "protocolVersion",
            "capabilities",
            "clientInfo",
        }:
            raise BoundaryError(400, "invalid_initialize")
        requested_version = params["protocolVersion"]
        if (
            not isinstance(requested_version, str)
            or not requested_version
            or len(requested_version) > 64
            or not isinstance(params["capabilities"], dict)
        ):
            raise BoundaryError(400, "invalid_initialize")
        client_info = params["clientInfo"]
        if (
            not isinstance(client_info, dict)
            or set(client_info) != {"name", "version"}
            or not all(isinstance(client_info[key], str) and client_info[key] for key in client_info)
        ):
            raise BoundaryError(400, "invalid_initialize")
        session = self.state.create_session(principal)
        result = {
            "jsonrpc": "2.0",
            "id": message["id"],
            "result": {
                # The client proposes a version in InitializeRequest.  When it
                # is unsupported, stable MCP requires the server to return an
                # alternative it supports; the client then decides whether to
                # continue or disconnect.
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"resources": {"listChanged": True}},
                "serverInfo": {"name": "loopback-teaching-server", "version": "1.0"},
            },
        }
        self._send_json(200, result, headers={"Mcp-Session-Id": session.session_id})

    def _handle_subsequent_post(self, message: dict[str, Any], envelope: str) -> None:
        principal = self._authenticate("mcp:use")
        self._validate_protocol_header()
        session_id = self._single_header("MCP-Session-Id", required=True)
        session = self.state.lookup_session(session_id, principal)
        if envelope == "notification":
            if message["method"] != "notifications/initialized" or set(message) != {
                "jsonrpc",
                "method",
            }:
                raise BoundaryError(400, "unsupported_notification")
            self.state.mark_initialized(session.session_id)
            self._send_bytes(202)
            return
        if envelope == "response":
            # This profile never creates a server request, so no client response
            # can be correlated and accepted.  A server with an outstanding
            # request would acknowledge a matching response with HTTP 202.
            raise BoundaryError(400, "unexpected_response")
        self.state.require_ready(session.session_id)
        method = message["method"]
        if method == "ping":
            if set(message) - {"jsonrpc", "id", "method", "params"}:
                raise BoundaryError(400, "invalid_request")
            if message.get("params", {}) != {}:
                raise BoundaryError(400, "invalid_request")
            self._send_json(
                200,
                {"jsonrpc": "2.0", "id": message["id"], "result": {}},
            )
            return
        if method == "resources/list":
            self.state.policy.authorize(principal, "resources:read")
            if message.get("params", {}) != {}:
                raise BoundaryError(400, "invalid_request")
            response = {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {
                    "resources": [
                        {
                            "uri": _tenant_resource_uri(principal.tenant),
                            "name": "Tenant handbook",
                            "mimeType": "text/plain",
                        }
                    ]
                },
            }
            event_id = self.state.allocate_event_id(session.session_id, "post")
            self._send_sse([(event_id, response)])
            return
        raise BoundaryError(400, "unsupported_method")

    def _send_sse(self, events: list[tuple[str, dict[str, Any]]]) -> None:
        if len(events) > MAX_SSE_EVENTS:
            raise BoundaryError(503, "event_capacity_exceeded")
        parts: list[bytes] = []
        for event_id, message in events:
            if "\n" in event_id or "\r" in event_id:
                raise RuntimeError("unsafe event ID")
            data = compact_json(message).decode("utf-8")
            parts.append(f"id: {event_id}\ndata: {data}\n\n".encode("utf-8"))
        self._send_bytes(200, b"".join(parts), content_type="text/event-stream")

    def do_GET(self) -> None:  # noqa: N802
        try:
            path, _origin = self._validate_common()
            if path in {WELL_KNOWN_PATH, ROOT_WELL_KNOWN_PATH}:
                self._handle_metadata()
                return
            if path != MCP_PATH:
                raise BoundaryError(404, "not_found")
            accept = _media_types(self._single_header("Accept", required=True) or "")
            if "text/event-stream" not in accept:
                raise BoundaryError(406, "not_acceptable")
            principal = self._authenticate("mcp:stream")
            self._validate_protocol_header()
            session_id = self._single_header("MCP-Session-Id", required=True)
            session = self.state.lookup_session(session_id, principal)
            self.state.require_ready(session.session_id)
            last_event_id = self._single_header("Last-Event-ID")
            events = self.state.resumed_events(session.session_id, last_event_id)
            self._send_sse(events)
        except BoundaryError as error:
            self._handle_boundary_error(error)

    def _handle_metadata(self) -> None:
        if self._single_header("Authorization") is not None:
            raise BoundaryError(400, "metadata_does_not_accept_credentials")
        accept = _media_types(self._single_header("Accept") or "application/json")
        if "application/json" not in accept and "*/*" not in accept:
            raise BoundaryError(406, "not_acceptable")
        self._send_json(
            200,
            {
                "resource": self.state.resource_uri,
                "authorization_servers": [AUTHORIZATION_SERVER],
                "scopes_supported": sorted(ALL_SCOPES),
                "resource_name": "Loopback MCP teaching resource",
            },
        )

    def do_DELETE(self) -> None:  # noqa: N802
        try:
            path, _origin = self._validate_common()
            if path != MCP_PATH:
                raise BoundaryError(404, "not_found")
            principal = self._authenticate("mcp:session")
            self._validate_protocol_header()
            session_id = self._single_header("MCP-Session-Id", required=True)
            session = self.state.lookup_session(session_id, principal)
            self.state.delete_session(session.session_id)
            self._send_bytes(204)
        except BoundaryError as error:
            self._handle_boundary_error(error)

    def do_PUT(self) -> None:  # noqa: N802
        try:
            self._validate_common()
            raise BoundaryError(405, "method_not_allowed", allow="POST, GET, DELETE")
        except BoundaryError as error:
            self._handle_boundary_error(error)

    do_PATCH = do_PUT
    do_OPTIONS = do_PUT

    def do_HEAD(self) -> None:  # noqa: N802
        try:
            self._validate_common()
        except BoundaryError as error:
            self._handle_boundary_error(error)
            return
        self.close_connection = True
        self._send_bytes(405, headers={"Allow": "POST, GET, DELETE"})


class LoopbackHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, state: TeachingState) -> None:
        super().__init__(("127.0.0.1", 0), LoopbackMCPHandler)
        self.state = state
        self._request_slots = threading.BoundedSemaphore(state.max_concurrent_requests)
        self._request_count_lock = threading.Lock()
        self._active_requests = 0
        host, port = self.server_address
        state.configure_endpoint(str(host), int(port))

    @property
    def active_requests(self) -> int:
        with self._request_count_lock:
            return self._active_requests

    def process_request(self, request: Any, client_address: Any) -> None:
        if not self._request_slots.acquire(blocking=False):
            try:
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Connection: close\r\n"
                    b"Cache-Control: no-store\r\n"
                    b"Content-Length: 0\r\n\r\n"
                )
            finally:
                self.shutdown_request(request)
            return
        with self._request_count_lock:
            self._active_requests += 1
        try:
            super().process_request(request, client_address)
        except BaseException:
            with self._request_count_lock:
                self._active_requests -= 1
            self._request_slots.release()
            raise

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            with self._request_count_lock:
                self._active_requests -= 1
            self._request_slots.release()

    def handle_error(self, request: Any, client_address: Any) -> None:
        # Do not print raw request context or credentials from unexpected errors.
        return


class RunningServer:
    def __init__(self, state: TeachingState | None = None) -> None:
        self.state = state or TeachingState()
        self.server = LoopbackHTTPServer(self.state)
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": 0.01},
            name="loopback-mcp-http",
            daemon=True,
        )

    @property
    def address(self) -> tuple[str, int]:
        host, port = self.server.server_address
        return str(host), int(port)

    def __enter__(self) -> "RunningServer":
        self.thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


@dataclass(frozen=True)
class HTTPResult:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return strict_json_loads(self.body)


class LoopbackClient:
    """Small non-redirecting client used by the project and its tests."""

    def __init__(
        self,
        host: str,
        port: int,
        token: str,
        *,
        origin: str = "https://client.example.test",
        timeout: float = 2.0,
    ) -> None:
        if host != "127.0.0.1":
            raise ValueError("client only connects to 127.0.0.1")
        self.host = host
        self.port = port
        self.token = token
        self.origin = origin
        self.timeout = timeout
        self.session_id: str | None = None

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> HTTPResult:
        connection = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise RuntimeError("response exceeded client cap")
            result_headers = {name.lower(): value for name, value in response.getheaders()}
            return HTTPResult(response.status, result_headers, raw)
        finally:
            connection.close()

    def _base_headers(self, *, subsequent: bool = False) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Origin": self.origin,
        }
        if subsequent:
            headers["MCP-Protocol-Version"] = PROTOCOL_VERSION
            if self.session_id:
                headers["Mcp-Session-Id"] = self.session_id
        return headers

    def post(self, message: dict[str, Any], *, subsequent: bool = False) -> HTTPResult:
        headers = self._base_headers(subsequent=subsequent)
        headers.update(
            {
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            }
        )
        return self.request("POST", MCP_PATH, headers=headers, body=compact_json(message))

    def initialize(self) -> HTTPResult:
        result = self.post(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "loopback-client", "version": "1.0"},
                },
            }
        )
        if result.status == 200:
            session_id = result.headers.get("mcp-session-id")
            if not session_id:
                raise RuntimeError("initialize response omitted Mcp-Session-Id")
            self.session_id = session_id
        return result

    def initialized(self) -> HTTPResult:
        return self.post(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            subsequent=True,
        )

    def ping(self, request_id: int = 2) -> HTTPResult:
        return self.post(
            {"jsonrpc": "2.0", "id": request_id, "method": "ping", "params": {}},
            subsequent=True,
        )

    def list_resources(self, request_id: int = 3) -> HTTPResult:
        return self.post(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "resources/list",
                "params": {},
            },
            subsequent=True,
        )

    def get_stream(self, last_event_id: str | None = None) -> HTTPResult:
        headers = self._base_headers(subsequent=True)
        headers["Accept"] = "text/event-stream"
        if last_event_id is not None:
            headers["Last-Event-ID"] = last_event_id
        return self.request("GET", MCP_PATH, headers=headers)

    def delete_session(self) -> HTTPResult:
        headers = self._base_headers(subsequent=True)
        return self.request("DELETE", MCP_PATH, headers=headers)


def parse_sse(body: bytes) -> list[tuple[str, Any]]:
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("SSE body exceeds cap")
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("SSE must be UTF-8") from exc
    if not text:
        return []
    events: list[tuple[str, Any]] = []
    for block in text.split("\n\n"):
        if not block:
            continue
        event_id: str | None = None
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("id: "):
                if event_id is not None:
                    raise ValueError("duplicate SSE id")
                event_id = line[4:]
            elif line.startswith("data: "):
                data_lines.append(line[6:])
            else:
                raise ValueError("unsupported SSE field")
        if not event_id or len(data_lines) != 1:
            raise ValueError("teaching SSE event requires one id and one data field")
        events.append((event_id, strict_json_loads(data_lines[0].encode("utf-8"))))
    return events


def make_record(
    state: TeachingState,
    *,
    token_id: str = "token-good",
    subject: str = "learner-1",
    tenant: str = "tenant-a",
    scopes: Iterable[str] = ALL_SCOPES,
    expires_in: float = 300.0,
    issuer: str = AUTHORIZATION_SERVER,
    audience: str | None = None,
    resource: str | None = None,
    authorization_resource: str | None = None,
    token_resource: str | None = None,
    revision: str = "authz-v1",
    active: bool = True,
) -> TokenRecord:
    """Build explicit fixture claims after the random loopback port is known."""

    expected = state.resource_uri
    return TokenRecord(
        token_id=token_id,
        issuer=issuer,
        audience=audience or expected,
        resource=resource or expected,
        authorization_resource=authorization_resource or expected,
        token_resource=token_resource or expected,
        subject=subject,
        tenant=tenant,
        scopes=frozenset(scopes),
        authorization_revision=revision,
        expires_at=state.clock() + expires_in,
        active=active,
    )


def _exercise_pass() -> dict[str, Any]:
    token = "demo-good-token"
    with RunningServer() as running:
        running.state.policy.register_token(token, make_record(running.state))
        client = LoopbackClient(*running.address, token)
        initialize = client.initialize()
        if initialize.status != 200 or initialize.json()["result"]["protocolVersion"] != PROTOCOL_VERSION:
            raise RuntimeError("initialize failed")
        if client.initialized().status != 202:
            raise RuntimeError("initialized notification failed")
        ping = client.ping()
        if ping.status != 200 or ping.json()["result"] != {}:
            raise RuntimeError("JSON response failed")
        resources = client.list_resources()
        resource_events = parse_sse(resources.body)
        if resources.status != 200 or len(resource_events) != 1:
            raise RuntimeError("POST SSE response failed")
        stream = client.get_stream()
        stream_events = parse_sse(stream.body)
        if stream.status != 200 or len(stream_events) != 1:
            raise RuntimeError("GET SSE stream failed")
        resumed = client.get_stream(stream_events[-1][0])
        if resumed.status != 200 or parse_sse(resumed.body):
            raise RuntimeError("SSE resume cursor replayed an event")
        if client.delete_session().status != 204:
            raise RuntimeError("session deletion failed")
        if client.ping().status != 404:
            raise RuntimeError("terminated session remained usable")
    return {
        "verdict": "PASS",
        "profile": "loopback-streamable-http-teaching-profile-v1",
        "protocol_version": PROTOCOL_VERSION,
        "http_round_trips": 8,
    }


def _exercise_block() -> dict[str, Any]:
    good = "attack-good-token"
    narrow = "attack-narrow-token"
    revoked = "attack-revoked-token"
    with RunningServer() as running:
        state = running.state
        state.policy.register_token(good, make_record(state, token_id="good"))
        state.policy.register_token(
            narrow,
            make_record(state, token_id="narrow", scopes={"mcp:connect", "mcp:use"}),
        )
        state.policy.register_token(revoked, make_record(state, token_id="revoked"))
        state.policy.revoke("revoked")
        invalid_origin = LoopbackClient(
            *running.address,
            good,
            origin="https://attacker.example.test",
        ).initialize()
        invalid_token = LoopbackClient(*running.address, "unknown-token").initialize()
        narrow_client = LoopbackClient(*running.address, narrow)
        if narrow_client.initialize().status != 200 or narrow_client.initialized().status != 202:
            raise RuntimeError("narrow setup failed")
        insufficient_scope = narrow_client.list_resources()
        revoked_token = LoopbackClient(*running.address, revoked).initialize()
        observed = [
            invalid_origin.status,
            invalid_token.status,
            insufficient_scope.status,
            revoked_token.status,
        ]
        if observed != [403, 401, 403, 401]:
            raise RuntimeError(f"attack was not blocked: {observed}")
        combined = b"\n".join(
            [invalid_origin.body, invalid_token.body, insufficient_scope.body, revoked_token.body]
        )
        for secret in (good, narrow, revoked, "unknown-token"):
            if secret.encode("utf-8") in combined:
                raise RuntimeError("error response leaked a token")
    return {
        "verdict": "BLOCK",
        "profile": "loopback-streamable-http-teaching-profile-v1",
        "protocol_version": PROTOCOL_VERSION,
        "blocked_attacks": 4,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("demo", "attack"), nargs="?", default="demo")
    args = parser.parse_args(argv)
    result = _exercise_pass() if args.command == "demo" else _exercise_block()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
