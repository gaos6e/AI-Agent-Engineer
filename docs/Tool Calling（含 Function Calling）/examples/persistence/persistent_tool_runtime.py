"""SQLite persistence layer for the sibling Tool Result v2 reference contract.

This standard-library-only project demonstrates a durable idempotency ledger,
transactional outbox, expiring/reclaimable worker lease, downstream receipt
stand-in, and explicit status reconciliation.  It intentionally omits a
continuously scheduled outbox poller and does not claim delivery liveness or
distributed exactly-once execution.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any, Callable


EXAMPLES_DIR = Path(__file__).resolve().parent.parent
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

import tool_dispatcher as tool_v2  # noqa: E402


DATABASE_SCHEMA_VERSION = "persistent-tool-runtime-v3"
FIXTURE_SCHEMA_VERSION = "persistent-tool-case-v1"
OUTBOX_SCHEMA_VERSION = "tool-outbox-event-v1"
MINIMUM_SQLITE = (3, 37, 0)
MAX_PORTABLE_UNIX_SECONDS = 253_402_300_799  # 9999-12-31T23:59:59Z
DEFAULT_LEASE_SECONDS = 30
MAX_FIXTURE_BYTES = 65_536
MAX_STORED_JSON_BYTES = 65_536
UTC_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
VALID_FAILURES = {
    "none",
    "after_intent_commit",
    "after_claim",
    "after_downstream_commit",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
STATUS_REF = re.compile(r"^status_[0-9a-f]{32}$")
FIXTURE_FIELDS = {
    "schema_version",
    "principal",
    "proposal",
    "execution_context",
    "approval_mode",
    "now",
}


class PersistenceContractError(RuntimeError):
    """Raised when stored state violates the persistence contract."""


class PersistenceFixtureError(ValueError):
    """Raised when a CLI fixture is outside its exact JSON contract."""


class PersistenceFixtureIOError(PersistenceFixtureError):
    """Raised when the CLI fixture cannot be read without exposing its path."""


class ClosingConnection(sqlite3.Connection):
    """Preserve sqlite3 transaction context semantics and close on exit."""

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
        try:
            return bool(super().__exit__(exc_type, exc_value, traceback))
        finally:
            self.close()


@dataclass(frozen=True)
class OutboxClaim:
    operation_pk: int
    status_ref: str
    worker_id: str
    request_sha256: str
    tool_name: str
    attempt_count: int


@dataclass(frozen=True)
class Reservation:
    disposition: str
    operation_pk: int | None
    status_ref: str | None


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runtime_metadata (
    metadata_key TEXT PRIMARY KEY,
    metadata_value TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS call_bindings (
    tenant_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    api_family TEXT NOT NULL,
    response_id TEXT NOT NULL,
    call_id TEXT NOT NULL,
    fingerprint_sha256 TEXT NOT NULL
        CHECK(length(fingerprint_sha256) = 64
              AND fingerprint_sha256 NOT GLOB '*[^0-9a-f]*'),
    created_at INTEGER NOT NULL CHECK(created_at >= 0),
    PRIMARY KEY (
        tenant_id, subject_id, provider, api_family, response_id, call_id
    )
) STRICT;

CREATE TABLE IF NOT EXISTS operations (
    operation_pk INTEGER PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    idempotency_key TEXT NOT NULL CHECK(length(idempotency_key) BETWEEN 1 AND 255),
    request_sha256 TEXT NOT NULL
        CHECK(length(request_sha256) = 64
              AND request_sha256 NOT GLOB '*[^0-9a-f]*'),
    arguments_json TEXT NOT NULL,
    input_schema_revision TEXT NOT NULL,
    output_schema_revision TEXT NOT NULL,
    effect_revision TEXT NOT NULL,
    handler_revision TEXT NOT NULL,
    producer_revision TEXT NOT NULL,
    policy_revision TEXT NOT NULL,
    approval_id TEXT NOT NULL,
    approver_id TEXT NOT NULL,
    approval_digest TEXT NOT NULL
        CHECK(length(approval_digest) = 64
              AND approval_digest NOT GLOB '*[^0-9a-f]*'),
    approval_expires_at INTEGER NOT NULL CHECK(approval_expires_at >= 0),
    approved_at INTEGER NOT NULL CHECK(approved_at >= 0),
    first_operation_id TEXT NOT NULL,
    first_call_id TEXT NOT NULL,
    first_response_id TEXT NOT NULL,
    first_provider TEXT NOT NULL,
    first_api_family TEXT NOT NULL,
    first_adapter_revision TEXT NOT NULL,
    status_ref TEXT NOT NULL UNIQUE
        CHECK(length(status_ref) = 39
              AND substr(status_ref, 1, 7) = 'status_'
              AND substr(status_ref, 8) NOT GLOB '*[^0-9a-f]*'),
    state TEXT NOT NULL CHECK(state IN ('pending', 'processing', 'succeeded')),
    created_at INTEGER NOT NULL CHECK(created_at >= 0),
    updated_at INTEGER NOT NULL CHECK(updated_at >= created_at),
    completed_at INTEGER CHECK(completed_at IS NULL OR completed_at >= created_at),
    UNIQUE(tenant_id, subject_id, tool_name, idempotency_key)
) STRICT;

CREATE TABLE IF NOT EXISTS outbox (
    event_id TEXT PRIMARY KEY,
    operation_pk INTEGER NOT NULL UNIQUE
        REFERENCES operations(operation_pk) ON DELETE RESTRICT,
    payload_json TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('pending', 'processing', 'delivered')),
    lease_owner TEXT,
    lease_until INTEGER,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
    created_at INTEGER NOT NULL CHECK(created_at >= 0),
    updated_at INTEGER NOT NULL CHECK(updated_at >= created_at),
    CHECK(
        (state = 'pending' AND lease_owner IS NULL AND lease_until IS NULL)
        OR (state = 'processing' AND lease_owner IS NOT NULL AND lease_until IS NOT NULL)
        OR (state = 'delivered' AND lease_owner IS NULL AND lease_until IS NULL)
    )
) STRICT;

-- This is an offline stand-in for an independently committed downstream
-- system.  Production code must query the real dependency using its supported
-- idempotency/status contract rather than sharing this database.
CREATE TABLE IF NOT EXISTS downstream_receipts (
    downstream_pk INTEGER PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    request_sha256 TEXT NOT NULL
        CHECK(length(request_sha256) = 64
              AND request_sha256 NOT GLOB '*[^0-9a-f]*'),
    receipt_id TEXT NOT NULL UNIQUE,
    downstream_request_id TEXT NOT NULL UNIQUE,
    result_json TEXT NOT NULL,
    producer_revision TEXT NOT NULL,
    resource_revision TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    effect_revision TEXT NOT NULL,
    committed_at INTEGER NOT NULL CHECK(committed_at >= 0),
    UNIQUE(tenant_id, subject_id, tool_name, idempotency_key)
) STRICT;

CREATE TABLE IF NOT EXISTS local_receipts (
    operation_pk INTEGER PRIMARY KEY
        REFERENCES operations(operation_pk) ON DELETE RESTRICT,
    receipt_id TEXT NOT NULL UNIQUE,
    downstream_request_id TEXT NOT NULL UNIQUE,
    request_sha256 TEXT NOT NULL
        CHECK(length(request_sha256) = 64
              AND request_sha256 NOT GLOB '*[^0-9a-f]*'),
    result_json TEXT NOT NULL,
    producer_revision TEXT NOT NULL,
    resource_revision TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    effect_revision TEXT NOT NULL,
    reconciled_at INTEGER NOT NULL CHECK(reconciled_at >= 0)
) STRICT;
"""


def _reject_constant(value: str) -> None:
    raise PersistenceFixtureError(f"JSON 不允许非有限常量：{value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PersistenceFixtureError(f"JSON 对象包含重复键：{key}")
        result[key] = value
    return result


def _strict_json_loads(text: str, *, label: str) -> Any:
    if not isinstance(text, str):
        raise PersistenceContractError(f"{label} 必须是 TEXT")
    try:
        raw = text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise PersistenceContractError(f"{label} 不是有效 UTF-8 文本") from exc
    if len(raw) > MAX_STORED_JSON_BYTES:
        raise PersistenceContractError(
            f"{label} 超过 {MAX_STORED_JSON_BYTES} UTF-8 字节上限"
        )
    try:
        tool_v2._reject_excessive_json_nesting(text)
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        tool_v2._validate_json_domain(value)
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError, UnicodeError) as exc:
        raise PersistenceContractError(f"{label} 不是严格 JSON：{exc}") from exc
    return value


def _canonical_json(value: Any) -> str:
    return tool_v2._canonical_json(value)


def _decode_canonical_object(text: Any, *, label: str, fields: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(text, str):
        raise PersistenceContractError(f"{label} 必须是 TEXT")
    value = _strict_json_loads(text, label=label)
    if not isinstance(value, dict):
        raise PersistenceContractError(f"{label} 必须解析为对象")
    if _canonical_json(value) != text:
        raise PersistenceContractError(f"{label} 不是当前规范 JSON 编码")
    if fields is not None and set(value) != fields:
        raise PersistenceContractError(f"{label} 字段不精确")
    return value


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_fixture(value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["fixture 根必须是对象"]
    if set(value) != FIXTURE_FIELDS:
        errors.append(
            f"fixture 根字段不匹配：missing={sorted(FIXTURE_FIELDS - set(value))}, "
            f"extra={sorted(set(value) - FIXTURE_FIELDS)}"
        )
        return errors
    if value["schema_version"] != FIXTURE_SCHEMA_VERSION:
        errors.append("schema_version 不匹配")
    principal = value["principal"]
    if not isinstance(principal, dict) or set(principal) != tool_v2.PRINCIPAL_FIELDS:
        errors.append("principal 字段不精确")
    else:
        if not _nonempty(principal["tenant_id"]) or not _nonempty(principal["subject_id"]):
            errors.append("principal tenant/subject 必须是非空字符串")
        roles = principal["roles"]
        if not isinstance(roles, list) or not all(_nonempty(role) for role in roles):
            errors.append("principal.roles 必须是非空字符串数组")
        elif roles != sorted(set(roles)):
            errors.append("principal.roles 必须已排序且无重复")
    proposal = value["proposal"]
    if not isinstance(proposal, dict) or set(proposal) != tool_v2.PROPOSAL_FIELDS:
        errors.append("proposal 字段不精确")
    else:
        if proposal["name"] != "create_refund_draft":
            errors.append("persistence 项目只接受 create_refund_draft")
        if not isinstance(proposal["arguments"], dict):
            errors.append("proposal.arguments 必须是对象")
        else:
            try:
                tool_v2._validate_json_domain(proposal["arguments"])
            except (TypeError, ValueError, UnicodeError) as exc:
                errors.append(f"proposal.arguments 超出 JSON 域：{exc}")
    context = value["execution_context"]
    if not isinstance(context, dict) or set(context) != tool_v2.CONTEXT_FIELDS:
        errors.append("execution_context 字段不精确")
    else:
        string_fields = set(tool_v2.CONTEXT_FIELDS) - {"idempotency_key"}
        if not all(_nonempty(context[field]) for field in string_fields):
            errors.append("execution_context 关联字段必须是非空字符串")
        key = context["idempotency_key"]
        if not isinstance(key, str) or not 1 <= len(key) <= 255:
            errors.append("idempotency_key 必须是 1..255 字符")
        profile = (context.get("provider"), context.get("api_family"))
        if tool_v2.PROVIDER_PROFILES.get(profile) != context.get("adapter_revision"):
            errors.append("provider profile/adapter revision 未登记")
    if value["approval_mode"] not in tool_v2.VALID_APPROVAL_MODES:
        errors.append("approval_mode 非法")
    if (
        type(value["now"]) is not int
        or value["now"] < 0
        or value["now"] > MAX_PORTABLE_UNIX_SECONDS - DEFAULT_LEASE_SECONDS
    ):
        errors.append("now 必须是可移植 UTC datetime 与默认 lease 可表示的非负整数时间戳")
    return errors


def load_fixture(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_FIXTURE_BYTES + 1)
    except OSError as exc:
        raise PersistenceFixtureIOError("无法读取 fixture") from exc
    if len(raw) > MAX_FIXTURE_BYTES:
        raise PersistenceFixtureError(f"fixture 超过 {MAX_FIXTURE_BYTES} 字节")
    try:
        text = raw.decode("utf-8")
        tool_v2._reject_excessive_json_nesting(text)
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        tool_v2._validate_json_domain(value)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
        TypeError,
        ValueError,
    ) as exc:
        raise PersistenceFixtureError(f"fixture 不是严格 UTF-8 JSON：{exc}") from exc
    errors = validate_fixture(value)
    if errors:
        raise PersistenceFixtureError("fixture 校验失败：" + "; ".join(errors))
    return value


def fixture_principal_call(fixture: dict[str, Any]) -> tuple[tool_v2.Principal, tool_v2.ToolCall]:
    principal_value = fixture["principal"]
    context = fixture["execution_context"]
    principal = tool_v2.Principal(
        principal_value["tenant_id"],
        principal_value["subject_id"],
        tuple(principal_value["roles"]),
    )
    call = tool_v2.bind_tool_call(
        tool_v2.ModelProposal(
            fixture["proposal"]["name"],
            copy.deepcopy(fixture["proposal"]["arguments"]),
        ),
        tool_v2.ExecutionContext(
            call_id=context["call_id"],
            operation_id=context["operation_id"],
            idempotency_key=context["idempotency_key"],
            provider=context["provider"],
            api_family=context["api_family"],
            response_id=context["response_id"],
            adapter_revision=context["adapter_revision"],
        ),
    )
    return principal, call


def status_query_call(
    original_call: tool_v2.ToolCall, status_ref: str
) -> tool_v2.ToolCall:
    """Derive a separate host-owned provider identity for explicit status lookup."""

    if not isinstance(status_ref, str) or STATUS_REF.fullmatch(status_ref) is None:
        raise ValueError("status_ref 格式非法")
    suffix = tool_v2._digest(
        {
            "provider": original_call.provider,
            "api_family": original_call.api_family,
            "response_id": original_call.response_id,
            "call_id": original_call.call_id,
            "status_ref": status_ref,
        }
    )[:24]
    return tool_v2.ToolCall(
        call_id=f"status-call-{suffix}",
        operation_id=original_call.operation_id,
        name=original_call.name,
        arguments=copy.deepcopy(original_call.arguments),
        idempotency_key=original_call.idempotency_key,
        provider=original_call.provider,
        api_family=original_call.api_family,
        response_id=f"status-response-{suffix}",
        adapter_revision=original_call.adapter_revision,
    )


class PersistentToolRuntime:
    """Durable adapter around the existing Tool Result v2 write contract."""

    def __init__(
        self,
        database: Path,
        *,
        authorization_resolver: Callable[[tool_v2.Principal, str], bool] | None = None,
        principal_resolver: Callable[[str, str], tool_v2.Principal | None] | None = None,
        busy_timeout_ms: int = 5_000,
    ) -> None:
        self.database = Path(database)
        if str(self.database) == ":memory:":
            raise ValueError("multi-connection 项目不接受 :memory: 数据库")
        if not self.database.parent.exists():
            raise ValueError("数据库父目录不存在")
        if type(busy_timeout_ms) is not int or busy_timeout_ms < 1:
            raise ValueError("busy_timeout_ms 必须是正整数")
        self.busy_timeout_ms = busy_timeout_ms
        self.contract = tool_v2.Dispatcher()
        self.authorization_resolver = authorization_resolver
        self.principal_resolver = principal_resolver
        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database,
            timeout=self.busy_timeout_ms / 1000,
            isolation_level=None,
            factory=ClosingConnection,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @staticmethod
    def _begin_immediate(connection: sqlite3.Connection) -> None:
        connection.execute("BEGIN IMMEDIATE")

    def _initialize_database(self) -> None:
        if sqlite3.sqlite_version_info < MINIMUM_SQLITE:
            minimum = ".".join(str(item) for item in MINIMUM_SQLITE)
            raise PersistenceContractError(f"SQLite {minimum}+ 才支持本项目 STRICT 表")
        with self._connect() as connection:
            mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            if str(mode).lower() != "wal":
                raise PersistenceContractError("SQLite 未进入 WAL 模式")
            connection.executescript(SCHEMA_SQL)
            connection.execute(
                """
                INSERT INTO runtime_metadata(metadata_key, metadata_value)
                VALUES ('schema_version', ?)
                ON CONFLICT(metadata_key) DO NOTHING
                """,
                (DATABASE_SCHEMA_VERSION,),
            )
            stored = connection.execute(
                "SELECT metadata_value FROM runtime_metadata WHERE metadata_key = 'schema_version'"
            ).fetchone()
            if stored is None or stored["metadata_value"] != DATABASE_SCHEMA_VERSION:
                raise PersistenceContractError("数据库 schema_version 不匹配")

    def _authorized(self, principal: tool_v2.Principal, order_ref: str) -> bool:
        if self.authorization_resolver is not None:
            return self.authorization_resolver(principal, order_ref)
        return self.contract._authorized_order(principal, order_ref)

    def _resolve_current_principal(
        self, tenant_id: str, subject_id: str
    ) -> tool_v2.Principal | None:
        """Resolve current claims; durable intents never retain a roles snapshot."""

        if self.principal_resolver is None:
            # The teaching default is deliberately owner-only.  A deployment
            # with role-based policy must inject current claims from IAM rather
            # than trusting the roles present when the intent was created.
            return tool_v2.Principal(tenant_id, subject_id, ())
        try:
            principal = self.principal_resolver(tenant_id, subject_id)
        except Exception as exc:
            raise PersistenceContractError("current principal resolver 失败") from exc
        if principal is None:
            return None
        if not isinstance(principal, tool_v2.Principal):
            raise PersistenceContractError("current principal resolver 返回类型非法")
        if (principal.tenant_id, principal.subject_id) != (tenant_id, subject_id):
            raise PersistenceContractError("current principal resolver 改变了 tenant/subject")
        if (
            not isinstance(principal.roles, tuple)
            or len(principal.roles) > tool_v2.MAX_ROLES
            or any(
                not tool_v2._bounded_identifier(role) for role in principal.roles
            )
            or tuple(sorted(set(principal.roles))) != principal.roles
        ):
            raise PersistenceContractError("current principal resolver 返回了非法 roles")
        return principal

    def _current_authorized_principal(
        self, principal: tool_v2.Principal, order_ref: str
    ) -> tool_v2.Principal | None:
        """Resolve current claims and check the resource with those claims only.

        The presented ``Principal`` establishes the immutable tenant/subject
        scope of this request.  It is deliberately not a durable role snapshot:
        both reservation and worker delivery obtain fresh roles through the
        same resolver.  The owner-only default is therefore fail closed when a
        deployment has not installed a current-claims resolver.
        """

        current = self._resolve_current_principal(
            principal.tenant_id, principal.subject_id
        )
        if current is None or not self._authorized(current, order_ref):
            return None
        return current

    def _preflight(
        self,
        principal: tool_v2.Principal,
        call: tool_v2.ToolCall,
        *,
        now: int,
    ) -> tuple[tool_v2.ToolSpec | None, str, dict[str, Any] | None]:
        tool_v2.validate_host_context(principal, call, now=now)
        spec = self.contract.registry.get(call.name)
        if spec is None or call.name != "create_refund_draft":
            digest = tool_v2.request_digest(principal, call, spec)
            return spec, digest, tool_v2._error_package(
                principal, call, spec, "UNKNOWN_TOOL", digest, now=now
            )
        if not self.contract._validate_arguments(spec, call.arguments):
            digest = tool_v2.request_digest(principal, call, spec)
            return spec, digest, tool_v2._error_package(
                principal, call, spec, "INVALID_ARGUMENTS", digest, now=now
            )
        digest = tool_v2.request_digest(principal, call, spec)
        current_principal = self._current_authorized_principal(
            principal, call.arguments["order_ref"]
        )
        if current_principal is None:
            return spec, digest, tool_v2._error_package(
                principal, call, spec, "NOT_FOUND", digest, now=now
            )
        if not call.idempotency_key or len(call.idempotency_key) > 255:
            return spec, digest, tool_v2._error_package(
                principal, call, spec, "IDEMPOTENCY_KEY_REQUIRED", digest, now=now
            )
        return spec, digest, None

    @staticmethod
    def _validate_timepoint(now: int) -> None:
        if (
            type(now) is not int
            or now < 0
            or now > MAX_PORTABLE_UNIX_SECONDS
        ):
            raise ValueError("now 超出可移植 UTC datetime 范围")

    @classmethod
    def _validate_lease_window(cls, now: int, lease_seconds: int) -> None:
        cls._validate_timepoint(now)
        if type(lease_seconds) is not int or lease_seconds < 1:
            raise ValueError("lease_seconds 必须是正整数")
        if lease_seconds > MAX_PORTABLE_UNIX_SECONDS - now:
            raise ValueError("now + lease_seconds 超出可移植 UTC datetime 范围")

    @staticmethod
    def _scope(principal: tool_v2.Principal, call: tool_v2.ToolCall) -> tuple[str, str, str, str]:
        if not call.idempotency_key:
            raise ValueError("写操作缺少 idempotency key")
        return principal.tenant_id, principal.subject_id, call.name, call.idempotency_key

    @staticmethod
    def _status_ref(scope: tuple[str, str, str, str], request_sha256: str) -> str:
        return "status_" + tool_v2._digest(
            {"scope": list(scope), "request_sha256": request_sha256}
        )[:32]

    @staticmethod
    def _event_payload(operation_pk: int, request_sha256: str, tool_name: str) -> dict[str, Any]:
        return {
            "schema_version": OUTBOX_SCHEMA_VERSION,
            "operation_pk": operation_pk,
            "request_sha256": request_sha256,
            "tool": tool_name,
        }

    @staticmethod
    def _contract_matches(row: sqlite3.Row, spec: tool_v2.ToolSpec, digest: str) -> bool:
        return (
            row["request_sha256"] == digest
            and row["input_schema_revision"] == spec.schema_version
            and row["output_schema_revision"] == spec.output_schema_revision
            and row["effect_revision"] == spec.effect_revision
            and row["handler_revision"] == spec.handler_revision
            and row["producer_revision"] == spec.producer_revision
            and row["policy_revision"] == spec.approval_revision
        )

    @staticmethod
    def _approval_provider_context_matches(
        row: sqlite3.Row, call: tool_v2.ToolCall
    ) -> bool:
        """Keep an accepted approval inside its provider/API/adapter context."""

        return (
            row["first_provider"],
            row["first_api_family"],
            row["first_adapter_revision"],
        ) == (call.provider, call.api_family, call.adapter_revision)

    @staticmethod
    def _call_key(
        principal: tool_v2.Principal, call: tool_v2.ToolCall
    ) -> tuple[str, str, str, str, str, str]:
        return (
            principal.tenant_id,
            principal.subject_id,
            call.provider,
            call.api_family,
            call.response_id,
            call.call_id,
        )

    def _bind_call_identity(
        self,
        connection: sqlite3.Connection,
        principal: tool_v2.Principal,
        call: tool_v2.ToolCall,
        spec: tool_v2.ToolSpec,
        *,
        purpose: str,
        now: int,
    ) -> bool:
        fingerprint = tool_v2.call_fingerprint(
            principal, call, spec, purpose=purpose
        )
        call_key = self._call_key(principal, call)
        connection.execute(
            """
            INSERT INTO call_bindings(
                tenant_id, subject_id, provider, api_family,
                response_id, call_id, fingerprint_sha256, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(
                tenant_id, subject_id, provider, api_family, response_id, call_id
            ) DO NOTHING
            """,
            (*call_key, fingerprint, now),
        )
        call_row = connection.execute(
            """
            SELECT fingerprint_sha256 FROM call_bindings
            WHERE tenant_id = ? AND subject_id = ? AND provider = ?
              AND api_family = ? AND response_id = ? AND call_id = ?
            """,
            call_key,
        ).fetchone()
        if call_row is None:
            raise PersistenceContractError("call binding 写入后不可见")
        return call_row["fingerprint_sha256"] == fingerprint

    def _validate_operation_row(
        self,
        row: sqlite3.Row,
        principal: tool_v2.Principal,
        call: tool_v2.ToolCall,
        spec: tool_v2.ToolSpec,
        digest: str,
    ) -> dict[str, Any]:
        scope = self._scope(principal, call)
        if tuple(row[field] for field in ("tenant_id", "subject_id", "tool_name", "idempotency_key")) != scope:
            raise PersistenceContractError("operation scope 与当前请求不一致")
        if not self._contract_matches(row, spec, digest):
            raise PersistenceContractError("operation digest/合同版本与当前请求不一致")
        arguments = _decode_canonical_object(
            row["arguments_json"], label="operations.arguments_json"
        )
        if arguments != call.arguments:
            raise PersistenceContractError("operation arguments 与当前请求不一致")
        expected_status_ref = self._status_ref(scope, digest)
        if row["status_ref"] != expected_status_ref or STATUS_REF.fullmatch(row["status_ref"]) is None:
            raise PersistenceContractError("operation status_ref 绑定无效")
        approval_context_fields = (
            "first_operation_id",
            "first_call_id",
            "first_response_id",
            "first_provider",
            "first_api_family",
            "first_adapter_revision",
        )
        if any(not tool_v2._bounded_identifier(row[field]) for field in approval_context_fields):
            raise PersistenceContractError("operation provider/call 证据字段无效")
        approval_call = tool_v2.ToolCall(
            row["first_call_id"],
            row["first_operation_id"],
            row["tool_name"],
            arguments,
            row["idempotency_key"],
            provider=row["first_provider"],
            api_family=row["first_api_family"],
            response_id=row["first_response_id"],
            adapter_revision=row["first_adapter_revision"],
        )
        if (
            tool_v2.PROVIDER_PROFILES.get(
                (approval_call.provider, approval_call.api_family)
            )
            != approval_call.adapter_revision
        ):
            raise PersistenceContractError("operation provider profile evidence 无效")
        approver_id = row["approver_id"]
        if (
            not tool_v2._bounded_identifier(approver_id)
            or approver_id not in tool_v2.AUTHORIZED_APPROVER_IDS
        ):
            raise PersistenceContractError("operation approver 证据无效")
        expected_approval = tool_v2.approval_digest(
            principal, approval_call, spec, approver_id=approver_id
        )
        if (
            not _nonempty(row["approval_id"])
            or row["approval_digest"] != expected_approval
            or type(row["approved_at"]) is not int
            or type(row["approval_expires_at"]) is not int
            or row["approved_at"] != row["created_at"]
            or row["approval_expires_at"] <= row["approved_at"]
            or row["approval_expires_at"] > tool_v2.MAX_PORTABLE_UNIX_SECONDS
        ):
            raise PersistenceContractError("operation approval 证据绑定无效")
        return arguments

    def _reserve(
        self,
        principal: tool_v2.Principal,
        call: tool_v2.ToolCall,
        spec: tool_v2.ToolSpec,
        digest: str,
        approvals: tuple[tool_v2.Approval, ...],
        now: int,
    ) -> Reservation:
        # Re-resolve immediately before the durable intent transaction.  The
        # earlier preflight gives a cheap reject path; this second lookup closes
        # the gap in which a role or resource grant may have changed.
        current_principal = self._current_authorized_principal(
            principal, call.arguments["order_ref"]
        )
        if current_principal is None:
            return Reservation("authorization_denied", None, None)
        scope = self._scope(current_principal, call)
        status_ref = self._status_ref(scope, digest)
        connection = self._connect()
        try:
            self._begin_immediate(connection)
            if not self._bind_call_identity(
                connection,
                current_principal,
                call,
                spec,
                purpose="dispatch",
                now=now,
            ):
                connection.commit()
                return Reservation("call_conflict", None, None)

            row = connection.execute(
                """
                SELECT * FROM operations
                WHERE tenant_id = ? AND subject_id = ?
                  AND tool_name = ? AND idempotency_key = ?
                """,
                scope,
            ).fetchone()
            if row is not None:
                if (
                    not self._contract_matches(row, spec, digest)
                    or not self._approval_provider_context_matches(row, call)
                ):
                    connection.commit()
                    return Reservation("idempotency_conflict", row["operation_pk"], row["status_ref"])
                self._validate_operation_row(
                    row, current_principal, call, spec, digest
                )
                disposition = "succeeded" if row["state"] == "succeeded" else "unknown"
                connection.commit()
                return Reservation(disposition, row["operation_pk"], row["status_ref"])

            if not spec.business_validator(current_principal, call.arguments):
                connection.commit()
                return Reservation("business_rule_violation", None, None)

            if not approvals:
                connection.commit()
                return Reservation("approval_required", None, None)
            if not self.contract._approval_valid(
                approvals, current_principal, call, spec, now
            ):
                connection.commit()
                return Reservation("approval_invalid", None, None)
            matching_approvals = [
                approval
                for approval in approvals
                if isinstance(approval, tool_v2.Approval)
                and tool_v2._bounded_identifier(approval.approver_id)
                and approval.approver_id in tool_v2.AUTHORIZED_APPROVER_IDS
                and approval.operation_id == call.operation_id
                and approval.call_id == call.call_id
                and approval.provider == call.provider
                and approval.api_family == call.api_family
                and approval.adapter_revision == call.adapter_revision
                and approval.idempotency_key == call.idempotency_key
                and approval.tool_name == call.name
                and approval.subject_id == current_principal.subject_id
                and approval.schema_version == spec.schema_version
                and approval.approval_revision == spec.approval_revision
                and approval.approval_digest
                == tool_v2.approval_digest(
                    current_principal,
                    call,
                    spec,
                    approver_id=approval.approver_id,
                )
                and type(approval.expires_at) is int
                and approval.expires_at > now
                and approval.expires_at <= tool_v2.MAX_PORTABLE_UNIX_SECONDS
            ]
            if not matching_approvals:
                raise PersistenceContractError("审批校验与持久化选择不一致")
            selected_approval = sorted(
                matching_approvals, key=lambda item: (item.approval_id, item.expires_at)
            )[0]

            contract = tool_v2._tool_contract(spec, call.name)
            cursor = connection.execute(
                """
                INSERT INTO operations(
                    tenant_id, subject_id, tool_name, idempotency_key,
                    request_sha256, arguments_json,
                    input_schema_revision, output_schema_revision,
                    effect_revision, handler_revision, producer_revision,
                    policy_revision, approval_id, approver_id, approval_digest,
                    approval_expires_at, approved_at,
                    first_operation_id, first_call_id, first_response_id,
                    first_provider, first_api_family, first_adapter_revision,
                    status_ref, state, created_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, NULL)
                ON CONFLICT(tenant_id, subject_id, tool_name, idempotency_key) DO NOTHING
                """,
                (
                    *scope,
                    digest,
                    _canonical_json(call.arguments),
                    contract["input_schema_revision"],
                    contract["output_schema_revision"],
                    contract["effect_revision"],
                    contract["handler_revision"],
                    contract["producer_revision"],
                    contract["policy_revision"],
                    selected_approval.approval_id,
                    selected_approval.approver_id,
                    selected_approval.approval_digest,
                    selected_approval.expires_at,
                    now,
                    call.operation_id,
                    call.call_id,
                    call.response_id,
                    call.provider,
                    call.api_family,
                    call.adapter_revision,
                    status_ref,
                    now,
                    now,
                ),
            )
            if cursor.rowcount != 1:
                raise PersistenceContractError("BEGIN IMMEDIATE 中出现未预期的 operation 竞争")
            operation_pk = int(cursor.lastrowid)
            payload = self._event_payload(operation_pk, digest, call.name)
            event_id = "outbox_" + tool_v2._digest(payload)[:32]
            connection.execute(
                """
                INSERT INTO outbox(
                    event_id, operation_pk, payload_json, state,
                    lease_owner, lease_until, attempt_count, created_at, updated_at
                ) VALUES (?, ?, ?, 'pending', NULL, NULL, 0, ?, ?)
                """,
                (event_id, operation_pk, _canonical_json(payload), now, now),
            )
            connection.commit()
            return Reservation("new", operation_pk, status_ref)
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _read_operation_by_status(self, status_ref: str) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM operations WHERE status_ref = ?", (status_ref,)
            ).fetchone()

    def _unknown_package(
        self,
        principal: tool_v2.Principal,
        call: tool_v2.ToolCall,
        spec: tool_v2.ToolSpec,
        digest: str,
        *,
        now: int,
        status_ref: str,
    ) -> dict[str, Any]:
        return tool_v2._error_package(
            principal,
            call,
            spec,
            "OUTCOME_UNKNOWN",
            digest,
            now=now,
            status_ref=status_ref,
        )

    def _load_local_record(
        self,
        operation_pk: int,
        principal: tool_v2.Principal,
        call: tool_v2.ToolCall,
        spec: tool_v2.ToolSpec,
        digest: str,
    ) -> tool_v2.IdempotencyRecord:
        with self._connect() as connection:
            operation = connection.execute(
                "SELECT * FROM operations WHERE operation_pk = ?", (operation_pk,)
            ).fetchone()
            receipt = connection.execute(
                "SELECT * FROM local_receipts WHERE operation_pk = ?", (operation_pk,)
            ).fetchone()
        if operation is None or receipt is None or operation["state"] != "succeeded":
            raise PersistenceContractError("succeeded operation 缺少本地 receipt")
        self._validate_operation_row(operation, principal, call, spec, digest)
        if (
            receipt["request_sha256"] != digest
            or receipt["producer_revision"] != spec.producer_revision
            or receipt["effect_revision"] != spec.effect_revision
        ):
            raise PersistenceContractError("local receipt 与 operation/当前合同不一致")
        data = _decode_canonical_object(receipt["result_json"], label="local_receipts.result_json")
        raw = tool_v2.HandlerResult(
            data=data,
            producer_revision=receipt["producer_revision"],
            resource_revision=receipt["resource_revision"],
            observed_at=receipt["observed_at"],
            downstream_request_id=receipt["downstream_request_id"],
            receipt_id=receipt["receipt_id"],
        )
        errors = tool_v2.validate_handler_result(spec, call, raw)
        if errors:
            raise PersistenceContractError("local receipt 输出合同失败：" + "; ".join(errors))
        return tool_v2.IdempotencyRecord(
            request_sha256=digest,
            provider=operation["first_provider"],
            api_family=operation["first_api_family"],
            adapter_revision=operation["first_adapter_revision"],
            data=copy.deepcopy(data),
            source_label=spec.producer_label,
            producer_revision=receipt["producer_revision"],
            resource_revision=receipt["resource_revision"],
            observed_at=receipt["observed_at"],
            output_schema_revision=spec.output_schema_revision,
            effect_revision=receipt["effect_revision"],
            handler_revision=spec.handler_revision,
            downstream_request_id=receipt["downstream_request_id"],
            receipt_id=receipt["receipt_id"],
            status_ref=operation["status_ref"],
        )

    def dispatch(
        self,
        principal: tool_v2.Principal,
        call: tool_v2.ToolCall,
        *,
        approvals: tuple[tool_v2.Approval, ...] = (),
        now: int,
        failure: str = "none",
        worker_id: str = "inline-worker",
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> dict[str, Any]:
        """Reserve intent atomically, then optionally run the outbox worker."""

        if failure not in VALID_FAILURES:
            raise ValueError(f"未知 failure：{failure}")
        spec, digest, preflight_error = self._preflight(principal, call, now=now)
        if preflight_error is not None:
            return preflight_error
        if spec is None:
            raise PersistenceContractError("内部错误：preflight 未返回 spec")
        # Validate all worker controls before the intent/outbox transaction.
        # Otherwise an invalid lease could strand a newly reserved operation.
        if failure != "after_intent_commit":
            if not _nonempty(worker_id) or len(worker_id) > 128:
                raise ValueError("worker_id 必须是 1..128 字符")
            self._validate_lease_window(now, lease_seconds)
        reservation = self._reserve(principal, call, spec, digest, approvals, now)
        code_for_disposition = {
            "call_conflict": "CALL_ID_CONFLICT",
            "idempotency_conflict": "IDEMPOTENCY_CONFLICT",
            "authorization_denied": "NOT_FOUND",
            "business_rule_violation": "BUSINESS_RULE_VIOLATION",
            "approval_required": "APPROVAL_REQUIRED",
            "approval_invalid": "APPROVAL_INVALID",
        }
        if reservation.disposition in code_for_disposition:
            return tool_v2._error_package(
                principal,
                call,
                spec,
                code_for_disposition[reservation.disposition],
                digest,
                now=now,
            )
        if reservation.operation_pk is None or reservation.status_ref is None:
            raise PersistenceContractError("operation reservation 缺少身份")
        if reservation.disposition == "succeeded":
            record = self._load_local_record(
                reservation.operation_pk, principal, call, spec, digest
            )
            return tool_v2._success_package(
                principal, call, spec, record, delivery="local_replay"
            )
        if reservation.disposition == "unknown":
            return self._unknown_package(
                principal,
                call,
                spec,
                digest,
                now=now,
                status_ref=reservation.status_ref,
            )
        if failure == "after_intent_commit":
            return self._unknown_package(
                principal,
                call,
                spec,
                digest,
                now=now,
                status_ref=reservation.status_ref,
            )

        outcome = self.process_operation(
            reservation.status_ref,
            worker_id=worker_id,
            now=now,
            lease_seconds=lease_seconds,
            failure=failure,
        )
        if outcome != "succeeded":
            return self._unknown_package(
                principal,
                call,
                spec,
                digest,
                now=now,
                status_ref=reservation.status_ref,
            )
        record = self._load_local_record(
            reservation.operation_pk, principal, call, spec, digest
        )
        return tool_v2._success_package(
            principal, call, spec, record, delivery="fresh"
        )

    def claim_operation(
        self,
        status_ref: str,
        *,
        worker_id: str,
        now: int,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> OutboxClaim | None:
        """Claim one pending or expired outbox row using a write transaction."""

        if STATUS_REF.fullmatch(status_ref) is None:
            raise ValueError("status_ref 格式无效")
        if not _nonempty(worker_id) or len(worker_id) > 128:
            raise ValueError("worker_id 必须是 1..128 字符")
        self._validate_lease_window(now, lease_seconds)
        connection = self._connect()
        try:
            self._begin_immediate(connection)
            row = connection.execute(
                """
                SELECT o.operation_pk, o.status_ref, o.request_sha256, o.tool_name,
                       b.payload_json, b.state AS outbox_state,
                       b.lease_until, b.attempt_count
                FROM operations AS o
                JOIN outbox AS b ON b.operation_pk = o.operation_pk
                WHERE o.status_ref = ?
                """,
                (status_ref,),
            ).fetchone()
            if row is None or row["outbox_state"] == "delivered":
                connection.commit()
                return None
            claimable = row["outbox_state"] == "pending" or (
                row["outbox_state"] == "processing"
                and isinstance(row["lease_until"], int)
                and row["lease_until"] <= now
            )
            if not claimable:
                connection.commit()
                return None
            payload = _decode_canonical_object(
                row["payload_json"],
                label="outbox.payload_json",
                fields={"schema_version", "operation_pk", "request_sha256", "tool"},
            )
            expected = self._event_payload(
                row["operation_pk"], row["request_sha256"], row["tool_name"]
            )
            if payload != expected:
                raise PersistenceContractError("outbox payload 与 operation 不一致")
            changed = connection.execute(
                """
                UPDATE outbox
                SET state = 'processing', lease_owner = ?, lease_until = ?,
                    attempt_count = attempt_count + 1, updated_at = ?
                WHERE operation_pk = ?
                  AND (state = 'pending'
                       OR (state = 'processing' AND lease_until <= ?))
                """,
                (worker_id, now + lease_seconds, now, row["operation_pk"], now),
            ).rowcount
            if changed != 1:
                connection.commit()
                return None
            connection.execute(
                """
                UPDATE operations SET state = 'processing', updated_at = ?
                WHERE operation_pk = ? AND state != 'succeeded'
                """,
                (now, row["operation_pk"]),
            )
            connection.commit()
            return OutboxClaim(
                operation_pk=row["operation_pk"],
                status_ref=row["status_ref"],
                worker_id=worker_id,
                request_sha256=row["request_sha256"],
                tool_name=row["tool_name"],
                attempt_count=row["attempt_count"] + 1,
            )
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _commit_downstream(self, claim: OutboxClaim, *, now: int) -> None:
        """Commit a deterministic downstream receipt with its own unique key."""

        with self._connect() as connection:
            operation = connection.execute(
                "SELECT * FROM operations WHERE operation_pk = ?", (claim.operation_pk,)
            ).fetchone()
        if operation is None or operation["status_ref"] != claim.status_ref:
            raise PersistenceContractError("claim 引用的 operation 不存在")
        if operation["request_sha256"] != claim.request_sha256:
            raise PersistenceContractError("claim request digest 不匹配")
        arguments = _decode_canonical_object(
            operation["arguments_json"], label="operations.arguments_json"
        )
        scope = tuple(
            operation[field]
            for field in ("tenant_id", "subject_id", "tool_name", "idempotency_key")
        )
        effect_identity = tool_v2._digest(
            {"scope": list(scope), "request_sha256": claim.request_sha256}
        )
        draft_number = int(effect_identity[:12], 16) + 1
        data = {
            "draft_id": f"DRAFT-{draft_number}",
            "order_ref": arguments.get("order_ref"),
            "reason": arguments.get("reason"),
        }
        result_json = _canonical_json(data)
        receipt_id = "refund-receipt-" + effect_identity[:24]
        downstream_request_id = "refund-request-" + effect_identity[24:48]
        # Avoid the platform C runtime range used by datetime.fromtimestamp().
        # The validated arithmetic is deterministic on Windows and POSIX.
        observed_at = (UTC_EPOCH + timedelta(seconds=now)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        connection = self._connect()
        try:
            self._begin_immediate(connection)
            connection.execute(
                """
                INSERT INTO downstream_receipts(
                    tenant_id, subject_id, tool_name, idempotency_key,
                    request_sha256, receipt_id, downstream_request_id,
                    result_json, producer_revision, resource_revision,
                    observed_at, effect_revision, committed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, subject_id, tool_name, idempotency_key) DO NOTHING
                """,
                (
                    *scope,
                    claim.request_sha256,
                    receipt_id,
                    downstream_request_id,
                    result_json,
                    operation["producer_revision"],
                    f"{data['draft_id'].lower()}-r1",
                    observed_at,
                    operation["effect_revision"],
                    now,
                ),
            )
            receipt = connection.execute(
                """
                SELECT * FROM downstream_receipts
                WHERE tenant_id = ? AND subject_id = ?
                  AND tool_name = ? AND idempotency_key = ?
                """,
                scope,
            ).fetchone()
            if receipt is None:
                raise PersistenceContractError("downstream UPSERT 后缺少 receipt")
            expected = {
                "request_sha256": claim.request_sha256,
                "result_json": result_json,
                "producer_revision": operation["producer_revision"],
                "effect_revision": operation["effect_revision"],
            }
            if any(receipt[field] != value for field, value in expected.items()):
                raise PersistenceContractError("downstream 同 key 出现异意图或回执漂移")
            connection.commit()
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _reconcile(
        self,
        operation_pk: int,
        principal: tool_v2.Principal,
        call: tool_v2.ToolCall,
        spec: tool_v2.ToolSpec,
        digest: str,
        *,
        now: int,
    ) -> tool_v2.IdempotencyRecord | None:
        connection = self._connect()
        try:
            self._begin_immediate(connection)
            operation = connection.execute(
                "SELECT * FROM operations WHERE operation_pk = ?", (operation_pk,)
            ).fetchone()
            if operation is None:
                connection.commit()
                return None
            self._validate_operation_row(operation, principal, call, spec, digest)
            downstream = connection.execute(
                """
                SELECT * FROM downstream_receipts
                WHERE tenant_id = ? AND subject_id = ?
                  AND tool_name = ? AND idempotency_key = ?
                """,
                self._scope(principal, call),
            ).fetchone()
            if downstream is None:
                connection.commit()
                return None
            if (
                downstream["request_sha256"] != digest
                or downstream["producer_revision"] != spec.producer_revision
                or downstream["effect_revision"] != spec.effect_revision
            ):
                raise PersistenceContractError("downstream receipt 与 operation/合同不一致")
            data = _decode_canonical_object(
                downstream["result_json"], label="downstream_receipts.result_json"
            )
            raw = tool_v2.HandlerResult(
                data=data,
                producer_revision=downstream["producer_revision"],
                resource_revision=downstream["resource_revision"],
                observed_at=downstream["observed_at"],
                downstream_request_id=downstream["downstream_request_id"],
                receipt_id=downstream["receipt_id"],
            )
            errors = tool_v2.validate_handler_result(spec, call, raw)
            if errors:
                raise PersistenceContractError("downstream receipt 输出合同失败：" + "; ".join(errors))
            connection.execute(
                """
                INSERT INTO local_receipts(
                    operation_pk, receipt_id, downstream_request_id,
                    request_sha256, result_json, producer_revision,
                    resource_revision, observed_at, effect_revision, reconciled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(operation_pk) DO NOTHING
                """,
                (
                    operation_pk,
                    downstream["receipt_id"],
                    downstream["downstream_request_id"],
                    digest,
                    downstream["result_json"],
                    downstream["producer_revision"],
                    downstream["resource_revision"],
                    downstream["observed_at"],
                    downstream["effect_revision"],
                    now,
                ),
            )
            local = connection.execute(
                "SELECT * FROM local_receipts WHERE operation_pk = ?", (operation_pk,)
            ).fetchone()
            if local is None:
                raise PersistenceContractError("local receipt UPSERT 后不可见")
            for field in (
                "receipt_id",
                "downstream_request_id",
                "request_sha256",
                "result_json",
                "producer_revision",
                "resource_revision",
                "observed_at",
                "effect_revision",
            ):
                if local[field] != downstream[field]:
                    raise PersistenceContractError("local/downstream receipt 不一致")
            connection.execute(
                """
                UPDATE operations
                SET state = 'succeeded', updated_at = ?, completed_at = ?
                WHERE operation_pk = ?
                """,
                (now, now, operation_pk),
            )
            connection.execute(
                """
                UPDATE outbox
                SET state = 'delivered', lease_owner = NULL, lease_until = NULL,
                    updated_at = ?
                WHERE operation_pk = ?
                """,
                (now, operation_pk),
            )
            connection.commit()
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()
        return self._load_local_record(operation_pk, principal, call, spec, digest)

    def process_operation(
        self,
        status_ref: str,
        *,
        worker_id: str,
        now: int,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
        failure: str = "none",
    ) -> str:
        """Claim, perform the downstream stand-in, and reconcile the receipt."""

        if failure not in {"none", "after_claim", "after_downstream_commit"}:
            raise ValueError("worker failure 非法")
        claim = self.claim_operation(
            status_ref,
            worker_id=worker_id,
            now=now,
            lease_seconds=lease_seconds,
        )
        if claim is None:
            row = self._read_operation_by_status(status_ref)
            if row is not None and row["state"] == "succeeded":
                return "succeeded"
            return "not_claimed"
        if failure == "after_claim":
            return "crashed_after_claim"
        with self._connect() as connection:
            operation = connection.execute(
                "SELECT * FROM operations WHERE operation_pk = ?", (claim.operation_pk,)
            ).fetchone()
        if operation is None:
            raise PersistenceContractError("worker 丢失 operation")
        arguments = _decode_canonical_object(
            operation["arguments_json"], label="operations.arguments_json"
        )
        order_ref = arguments.get("order_ref")
        if not isinstance(order_ref, str):
            raise PersistenceContractError("operation arguments 缺少 order_ref")
        principal = self._current_authorized_principal(
            tool_v2.Principal(operation["tenant_id"], operation["subject_id"], ()),
            order_ref,
        )
        if principal is None:
            return "authorization_denied"
        spec = self.contract.registry[operation["tool_name"]]
        call = tool_v2.ToolCall(
            operation["first_call_id"],
            operation["first_operation_id"],
            operation["tool_name"],
            arguments,
            operation["idempotency_key"],
            provider=operation["first_provider"],
            api_family=operation["first_api_family"],
            response_id=operation["first_response_id"],
            adapter_revision=operation["first_adapter_revision"],
        )
        current_digest = tool_v2.request_digest(principal, call, spec)
        self._validate_operation_row(
            operation, principal, call, spec, current_digest
        )
        if not spec.business_validator(principal, arguments):
            # The approved intent is durable, but a current business-state change
            # must fail closed before the downstream effect.
            return "business_rule_denied"
        self._commit_downstream(claim, now=now)
        if failure == "after_downstream_commit":
            return "outcome_unknown"
        record = self._reconcile(
            claim.operation_pk,
            principal,
            call,
            spec,
            current_digest,
            now=now,
        )
        if record is None:
            raise PersistenceContractError("downstream commit 后未能对账")
        return "succeeded"

    def query_operation_status(
        self,
        principal: tool_v2.Principal,
        call: tool_v2.ToolCall,
        *,
        status_ref: str,
        expected_request_sha256: str,
        now: int,
    ) -> dict[str, Any]:
        """Reauthorize and reconcile one opaque status reference explicitly."""

        spec, digest, preflight_error = self._preflight(principal, call, now=now)
        if preflight_error is not None:
            return preflight_error
        if spec is None:
            raise PersistenceContractError("内部错误：status query 缺少 spec")
        if STATUS_REF.fullmatch(status_ref) is None:
            return tool_v2._error_package(
                principal, call, spec, "NOT_FOUND", digest, now=now
            )
        operation = self._read_operation_by_status(status_ref)
        if operation is None or (
            operation["tenant_id"], operation["subject_id"]
        ) != (principal.tenant_id, principal.subject_id):
            return tool_v2._error_package(
                principal, call, spec, "NOT_FOUND", digest, now=now
            )
        connection = self._connect()
        try:
            self._begin_immediate(connection)
            call_bound = self._bind_call_identity(
                connection,
                principal,
                call,
                spec,
                purpose="query_status",
                now=now,
            )
            connection.commit()
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()
        if not call_bound:
            return tool_v2._error_package(
                principal, call, spec, "CALL_ID_CONFLICT", digest, now=now
            )
        if (
            not isinstance(expected_request_sha256, str)
            or HEX64.fullmatch(expected_request_sha256) is None
            or expected_request_sha256 != digest
            or operation["status_ref"] != status_ref
            or tuple(
                operation[field]
                for field in ("tenant_id", "subject_id", "tool_name", "idempotency_key")
            )
            != self._scope(principal, call)
            or not self._contract_matches(operation, spec, digest)
            or not self._approval_provider_context_matches(operation, call)
        ):
            return tool_v2._error_package(
                principal,
                call,
                spec,
                "STATUS_CONFLICT",
                digest,
                now=now,
                status_ref=status_ref,
            )
        self._validate_operation_row(operation, principal, call, spec, digest)
        if operation["state"] == "succeeded":
            record = self._load_local_record(
                operation["operation_pk"], principal, call, spec, digest
            )
            return tool_v2._success_package(
                principal, call, spec, record, delivery="receipt_reconciled"
            )
        record = self._reconcile(
            operation["operation_pk"], principal, call, spec, digest, now=now
        )
        if record is None:
            return self._unknown_package(
                principal,
                call,
                spec,
                digest,
                now=now,
                status_ref=status_ref,
            )
        return tool_v2._success_package(
            principal, call, spec, record, delivery="receipt_reconciled"
        )

    @staticmethod
    def _counts_from_connection(connection: sqlite3.Connection) -> dict[str, int]:
        tables = (
            "call_bindings",
            "operations",
            "outbox",
            "downstream_receipts",
            "local_receipts",
        )
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }

    def counts(self) -> dict[str, int]:
        with self._connect() as connection:
            connection.execute("BEGIN")
            result = self._counts_from_connection(connection)
            connection.commit()
            return result

    @staticmethod
    def _semantic_rows(
        connection: sqlite3.Connection,
    ) -> tuple[
        list[sqlite3.Row],
        list[sqlite3.Row],
        list[sqlite3.Row],
        list[sqlite3.Row],
    ]:
        return (
            list(connection.execute("SELECT * FROM operations ORDER BY operation_pk")),
            list(connection.execute("SELECT * FROM outbox ORDER BY operation_pk")),
            list(
                connection.execute(
                    """
                    SELECT * FROM downstream_receipts
                    ORDER BY tenant_id, subject_id, tool_name, idempotency_key
                    """
                )
            ),
            list(connection.execute("SELECT * FROM local_receipts ORDER BY operation_pk")),
        )

    def _semantic_audit(
        self, connection: sqlite3.Connection | None = None
    ) -> list[str]:
        """Recompute stored identities and receipt bindings, not just page health."""

        if connection is None:
            with self._connect() as owned_connection:
                owned_connection.execute("BEGIN")
                rows = self._semantic_rows(owned_connection)
                owned_connection.commit()
        else:
            rows = self._semantic_rows(connection)
        operations, outbox_rows, downstream_rows, local_rows = rows
        errors: list[str] = []
        outbox_by_operation = {row["operation_pk"]: row for row in outbox_rows}
        local_by_operation = {row["operation_pk"]: row for row in local_rows}
        downstream_by_scope = {
            tuple(
                row[field]
                for field in ("tenant_id", "subject_id", "tool_name", "idempotency_key")
            ): row
            for row in downstream_rows
        }
        operation_ids = {row["operation_pk"] for row in operations}
        operation_scopes: set[tuple[str, str, str, str]] = set()
        for operation in operations:
            operation_pk = operation["operation_pk"]
            label = f"operation[{operation_pk}]"
            scope = tuple(
                operation[field]
                for field in ("tenant_id", "subject_id", "tool_name", "idempotency_key")
            )
            operation_scopes.add(scope)
            try:
                arguments = _decode_canonical_object(
                    operation["arguments_json"], label=f"{label}.arguments_json"
                )
                spec = self.contract.registry.get(operation["tool_name"])
                if spec is None or operation["tool_name"] != "create_refund_draft":
                    raise PersistenceContractError(f"{label} 工具未登记")
                actor = tool_v2.Principal(operation["tenant_id"], operation["subject_id"], ())
                call = tool_v2.ToolCall(
                    operation["first_call_id"],
                    operation["first_operation_id"],
                    operation["tool_name"],
                    arguments,
                    operation["idempotency_key"],
                    provider=operation["first_provider"],
                    api_family=operation["first_api_family"],
                    response_id=operation["first_response_id"],
                    adapter_revision=operation["first_adapter_revision"],
                )
                digest = tool_v2.request_digest(actor, call, spec)
                if not self._contract_matches(operation, spec, digest):
                    raise PersistenceContractError(f"{label} request/合同绑定不匹配")
                if operation["status_ref"] != self._status_ref(scope, digest):
                    raise PersistenceContractError(f"{label} status_ref 不匹配")
                self._validate_operation_row(operation, actor, call, spec, digest)
                outbox = outbox_by_operation.get(operation_pk)
                if outbox is None:
                    raise PersistenceContractError(f"{label} 缺少 outbox")
                payload = _decode_canonical_object(
                    outbox["payload_json"],
                    label=f"outbox[{operation_pk}].payload_json",
                    fields={"schema_version", "operation_pk", "request_sha256", "tool"},
                )
                if payload != self._event_payload(operation_pk, digest, operation["tool_name"]):
                    raise PersistenceContractError(f"outbox[{operation_pk}] 与 operation 不一致")
                local = local_by_operation.get(operation_pk)
                downstream = downstream_by_scope.get(scope)
                if operation["state"] == "succeeded":
                    if outbox["state"] != "delivered" or local is None or downstream is None:
                        raise PersistenceContractError(f"{label} succeeded 状态证据不完整")
                elif local is not None or outbox["state"] == "delivered":
                    raise PersistenceContractError(f"{label} 未成功却存在 delivered/local receipt")
                if downstream is not None:
                    if (
                        downstream["request_sha256"] != digest
                        or downstream["producer_revision"] != spec.producer_revision
                        or downstream["effect_revision"] != spec.effect_revision
                    ):
                        raise PersistenceContractError(f"{label} downstream receipt 绑定不匹配")
                    downstream_data = _decode_canonical_object(
                        downstream["result_json"],
                        label=f"downstream_receipt[{operation_pk}].result_json",
                    )
                    raw = tool_v2.HandlerResult(
                        data=downstream_data,
                        producer_revision=downstream["producer_revision"],
                        resource_revision=downstream["resource_revision"],
                        observed_at=downstream["observed_at"],
                        downstream_request_id=downstream["downstream_request_id"],
                        receipt_id=downstream["receipt_id"],
                    )
                    output_errors = tool_v2.validate_handler_result(spec, call, raw)
                    if output_errors:
                        raise PersistenceContractError(
                            f"{label} downstream 输出合同失败：" + "; ".join(output_errors)
                        )
                if local is not None:
                    if downstream is None:
                        raise PersistenceContractError(f"{label} local receipt 缺少 downstream 依据")
                    for field in (
                        "receipt_id",
                        "downstream_request_id",
                        "request_sha256",
                        "result_json",
                        "producer_revision",
                        "resource_revision",
                        "observed_at",
                        "effect_revision",
                    ):
                        if local[field] != downstream[field]:
                            raise PersistenceContractError(f"{label} local/downstream receipt 不一致")
            except (KeyError, TypeError, ValueError, PersistenceContractError) as exc:
                errors.append(str(exc))
        for operation_pk in sorted(set(outbox_by_operation) - operation_ids):
            errors.append(f"outbox[{operation_pk}] 没有 operation")
        for operation_pk in sorted(set(local_by_operation) - operation_ids):
            errors.append(f"local_receipt[{operation_pk}] 没有 operation")
        for scope in sorted(set(downstream_by_scope) - operation_scopes):
            # Audit output can cross an operator/CLI boundary.  Keep the
            # orphan diagnosable without exposing tenant, subject, tool or the
            # idempotency key stored in the downstream scope.
            receipt = downstream_by_scope[scope]
            audit_ref = self._status_ref(scope, receipt["request_sha256"])
            errors.append(f"AUDIT_ORPHAN_DOWNSTREAM_RECEIPT[{audit_ref}]")
        return errors

    def audit_database(self) -> dict[str, Any]:
        with self._connect() as connection:
            # One explicit read transaction gives integrity/FK, semantic rows,
            # and counts the same SQLite snapshot.  Without it, a legal
            # reconcile commit between SELECTs could look like corruption.
            connection.execute("BEGIN")
            integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
            foreign_keys = [list(row) for row in connection.execute("PRAGMA foreign_key_check")]
            journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            synchronous = int(connection.execute("PRAGMA synchronous").fetchone()[0])
            semantic_errors = self._semantic_audit(connection)
            counts = self._counts_from_connection(connection)
            connection.commit()
        return {
            "schema_version": DATABASE_SCHEMA_VERSION,
            "sqlite_version": sqlite3.sqlite_version,
            "journal_mode": journal_mode,
            "synchronous": synchronous,
            "integrity_check": integrity,
            "foreign_key_violations": foreign_keys,
            "semantic_errors": semantic_errors,
            "counts": counts,
            "passed": (
                integrity == ["ok"]
                and not foreign_keys
                and not semantic_errors
                and journal_mode == "wal"
                and synchronous == 2
            ),
        }


def _result_code(package: dict[str, Any]) -> str:
    model = package["model_result"]
    if model["status"] == "succeeded":
        return "OK"
    return model["error"]["code"]


def _cli_package_summary(
    package: dict[str, Any],
    principal: tool_v2.Principal,
    call: tool_v2.ToolCall,
    spec: tool_v2.ToolSpec,
    runtime: PersistentToolRuntime,
) -> dict[str, Any]:
    errors = tool_v2.validate_result(principal, call, spec, package)
    model = package["model_result"]
    status_ref = package["protected_audit"]["downstream"]["status_ref"]
    gate = "PASS" if model["status"] == "succeeded" and not errors else "BLOCK"
    return {
        "gate": gate,
        "code": _result_code(package),
        "status": model["status"],
        "delivery": model["execution"]["delivery"],
        "status_ref": status_ref,
        "validation_errors": errors,
        "database": runtime.audit_database(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True, help="SQLite 数据库路径")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path(__file__).with_name("persistence-case.json"),
        help="严格 JSON 教学场景",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    dispatch = subparsers.add_parser("dispatch", help="预占 intent 并可选处理 outbox")
    dispatch.add_argument("--failure", choices=sorted(VALID_FAILURES), default="none")
    dispatch.add_argument("--worker-id", default="cli-worker")
    status = subparsers.add_parser("status", help="显式查询/对账 unknown operation")
    status.add_argument("--status-ref", required=True)
    subparsers.add_parser("audit", help="运行 SQLite 完整性/外键检查")
    return parser


def _cli_error_code(exc: BaseException) -> str:
    """Map expected local failures to stable, path-free CLI diagnostics."""

    if isinstance(exc, PersistenceFixtureIOError):
        return "FIXTURE_IO_ERROR"
    if isinstance(exc, PersistenceFixtureError):
        return "FIXTURE_CONTRACT_ERROR"
    if isinstance(exc, sqlite3.Error):
        return "SQLITE_ERROR"
    if isinstance(exc, PersistenceContractError):
        return "PERSISTENCE_CONTRACT_ERROR"
    if isinstance(exc, OSError):
        return "LOCAL_IO_ERROR"
    return "INVALID_VALUE"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        runtime = PersistentToolRuntime(args.db)
        if args.command == "audit":
            summary = runtime.audit_database()
            summary["gate"] = "PASS" if summary["passed"] else "BLOCK"
            print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
            return 0 if summary["passed"] else 1
        fixture = load_fixture(args.fixture)
        principal, call = fixture_principal_call(fixture)
        spec = runtime.contract.registry[call.name]
        now = fixture["now"]
        if args.command == "dispatch":
            approvals = tool_v2.make_approval(
                principal, call, spec, fixture["approval_mode"], now
            )
            package = runtime.dispatch(
                principal,
                call,
                approvals=approvals,
                now=now,
                failure=args.failure,
                worker_id=args.worker_id,
            )
        else:
            call = status_query_call(call, args.status_ref)
            package = runtime.query_operation_status(
                principal,
                call,
                status_ref=args.status_ref,
                expected_request_sha256=tool_v2.request_digest(principal, call, spec),
                now=now + 1,
            )
        summary = _cli_package_summary(package, principal, call, spec, runtime)
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if summary["gate"] == "PASS" else 1
    except (
        OSError,
        sqlite3.Error,
        PersistenceContractError,
        PersistenceFixtureError,
        ValueError,
    ) as exc:
        print(
            json.dumps(
                {"gate": "BLOCK", "error": {"code": _cli_error_code(exc)}},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
