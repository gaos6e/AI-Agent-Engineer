"""SQLite 教学知识库：版本、outbox、发布指针、ACL 与删除传播。

该实现用于离线学习生命周期契约，不包含向量检索、身份提供方、
分布式并发控制、备份清除或合规级物理擦除。
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import sqlite3
import sys
from typing import Any, Iterator, Sequence
import unicodedata


SCHEMA_VERSION = "1.0"
MAX_CONTENT_BYTES = 100_000
MAX_ACL_GROUPS = 128
MAX_SUBJECT_GROUPS = 128
MAX_SEARCH_RESULTS = 100
DELETE_REASONS = {
    "access_revoked",
    "retention_expired",
    "source_deleted",
    "user_request",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    tenant_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    last_source_sequence INTEGER NOT NULL CHECK (last_source_sequence >= 0),
    current_revision_id INTEGER,
    published_revision_id INTEGER,
    current_event_version INTEGER NOT NULL CHECK (current_event_version >= 0),
    deleted INTEGER NOT NULL DEFAULT 0 CHECK (deleted IN (0, 1)),
    access_blocked INTEGER NOT NULL DEFAULT 1 CHECK (access_blocked IN (0, 1)),
    PRIMARY KEY (tenant_id, document_id)
);

CREATE TABLE IF NOT EXISTS revisions (
    revision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    revision_number INTEGER NOT NULL CHECK (revision_number > 0),
    source_sequence INTEGER NOT NULL CHECK (source_sequence > 0),
    source_uri TEXT NOT NULL,
    source_version TEXT NOT NULL,
    pipeline_version TEXT NOT NULL,
    content TEXT,
    content_hash TEXT NOT NULL,
    source_state_hash TEXT NOT NULL,
    build_state_hash TEXT NOT NULL,
    run_id TEXT NOT NULL,
    content_purged INTEGER NOT NULL DEFAULT 0 CHECK (content_purged IN (0, 1)),
    UNIQUE (tenant_id, document_id, revision_number),
    FOREIGN KEY (tenant_id, document_id)
        REFERENCES documents(tenant_id, document_id)
);

CREATE TABLE IF NOT EXISTS revision_acl (
    revision_id INTEGER NOT NULL,
    group_id TEXT NOT NULL,
    PRIMARY KEY (revision_id, group_id),
    FOREIGN KEY (revision_id) REFERENCES revisions(revision_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS outbox (
    outbox_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    tenant_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    event_version INTEGER NOT NULL CHECK (event_version > 0),
    event_kind TEXT NOT NULL CHECK (event_kind IN ('document.upserted', 'document.deleted')),
    revision_id INTEGER,
    processed INTEGER NOT NULL DEFAULT 0 CHECK (processed IN (0, 1)),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_error TEXT,
    UNIQUE (tenant_id, document_id, event_version),
    FOREIGN KEY (revision_id) REFERENCES revisions(revision_id)
);

CREATE TABLE IF NOT EXISTS tombstones (
    tenant_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    event_version INTEGER NOT NULL,
    source_sequence INTEGER NOT NULL,
    reason_code TEXT NOT NULL,
    run_id TEXT NOT NULL,
    canonical_content_purged INTEGER NOT NULL DEFAULT 0
        CHECK (canonical_content_purged IN (0, 1)),
    PRIMARY KEY (tenant_id, document_id, event_version)
);

CREATE TABLE IF NOT EXISTS search_revisions (
    revision_id INTEGER PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    revision_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    FOREIGN KEY (revision_id) REFERENCES revisions(revision_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS search_acl (
    revision_id INTEGER NOT NULL,
    group_id TEXT NOT NULL,
    PRIMARY KEY (revision_id, group_id),
    FOREIGN KEY (revision_id) REFERENCES search_revisions(revision_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_outbox_pending ON outbox(processed, outbox_id);
CREATE INDEX IF NOT EXISTS idx_search_document
    ON search_revisions(tenant_id, document_id);
"""


class StoreError(ValueError):
    """知识库输入、顺序或状态冲突。"""


@dataclass(frozen=True)
class SourceRecord:
    tenant_id: str
    document_id: str
    source_sequence: int
    source_uri: str
    source_version: str
    content: str
    allowed_groups: tuple[str, ...]


@dataclass(frozen=True)
class BuildConfig:
    pipeline_version: str


@dataclass(frozen=True)
class ChangeResult:
    action: str
    event_id: str | None
    revision_number: int | None


@dataclass(frozen=True)
class ProjectionResult:
    action: str
    event_id: str | None


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _normalise_content(value: str) -> str:
    return unicodedata.normalize(
        "NFC", value.replace("\r\n", "\n").replace("\r", "\n")
    )


def _validate_token(name: str, value: str, *, maximum: int = 200) -> str:
    if not isinstance(value, str):
        raise StoreError(f"{name} 必须是字符串")
    if not value or value != value.strip():
        raise StoreError(f"{name} 不得为空或带首尾空白")
    if len(value) > maximum:
        raise StoreError(f"{name} 长度不得超过 {maximum}")
    if any(ord(character) < 32 for character in value):
        raise StoreError(f"{name} 不得包含控制字符")
    return value


def _validate_sequence(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise StoreError("source_sequence 必须是正整数")
    return value


def _normalise_record(record: SourceRecord) -> SourceRecord:
    tenant_id = _validate_token("tenant_id", record.tenant_id)
    document_id = _validate_token("document_id", record.document_id)
    source_uri = _validate_token("source_uri", record.source_uri, maximum=2_000)
    source_version = _validate_token("source_version", record.source_version)
    source_sequence = _validate_sequence(record.source_sequence)
    if not isinstance(record.content, str):
        raise StoreError("content 必须是字符串")
    content = _normalise_content(record.content)
    if not content.strip():
        raise StoreError("content 不得为空")
    if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
        raise StoreError(f"content 不得超过 {MAX_CONTENT_BYTES} UTF-8 bytes")
    if not isinstance(record.allowed_groups, tuple) or not record.allowed_groups:
        raise StoreError("allowed_groups 必须是非空 tuple；公开内容也要使用显式组")
    if len(record.allowed_groups) > MAX_ACL_GROUPS:
        raise StoreError(f"allowed_groups 不得超过 {MAX_ACL_GROUPS} 项")
    validated_groups = tuple(
        _validate_token("group_id", group) for group in record.allowed_groups
    )
    if len(set(validated_groups)) != len(validated_groups):
        raise StoreError("allowed_groups 不得包含重复值")
    groups = tuple(sorted(validated_groups))
    return SourceRecord(
        tenant_id,
        document_id,
        source_sequence,
        source_uri,
        source_version,
        content,
        groups,
    )


def _validate_config(config: BuildConfig) -> BuildConfig:
    return BuildConfig(_validate_token("pipeline_version", config.pipeline_version))


def _source_state(record: SourceRecord) -> dict[str, Any]:
    return {
        "allowed_groups": list(record.allowed_groups),
        "content": record.content,
        "source_uri": record.source_uri,
        "source_version": record.source_version,
    }


def _state_hashes(record: SourceRecord, config: BuildConfig) -> tuple[str, str, str]:
    content_hash = _digest_text(record.content)
    source_state_hash = _digest_text(_canonical_json(_source_state(record)))
    build_state_hash = _digest_text(
        _canonical_json(
            {
                "pipeline_version": config.pipeline_version,
                "source_state_hash": source_state_hash,
            }
        )
    )
    return content_hash, source_state_hash, build_state_hash


def _persisted_revision_hash_errors(
    revision: sqlite3.Row, groups: tuple[str, ...]
) -> tuple[str, ...]:
    """Recompute canonical hashes from persisted values instead of trusting labels."""

    content = revision["content"]
    if not isinstance(content, str):
        return ("canonical_content_missing",)
    content_hash = _digest_text(content)
    source_state_hash = _digest_text(
        _canonical_json(
            {
                "allowed_groups": list(groups),
                "content": content,
                "source_uri": revision["source_uri"],
                "source_version": revision["source_version"],
            }
        )
    )
    build_state_hash = _digest_text(
        _canonical_json(
            {
                "pipeline_version": revision["pipeline_version"],
                "source_state_hash": source_state_hash,
            }
        )
    )
    errors: list[str] = []
    if revision["content_hash"] != content_hash:
        errors.append("canonical_content_hash_mismatch")
    if revision["source_state_hash"] != source_state_hash:
        errors.append("canonical_source_state_hash_mismatch")
    if revision["build_state_hash"] != build_state_hash:
        errors.append("canonical_build_state_hash_mismatch")
    return tuple(errors)


def connect(path: str = ":memory:") -> sqlite3.Connection:
    connection = sqlite3.connect(path, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    return connection


@contextmanager
def _transaction(connection: sqlite3.Connection) -> Iterator[None]:
    if connection.in_transaction:
        raise RuntimeError("教学事务不允许嵌套；生产实现应明确 savepoint 策略")
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        connection.rollback()
        raise
    else:
        connection.commit()


def _document(
    connection: sqlite3.Connection, tenant_id: str, document_id: str
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT * FROM documents
        WHERE tenant_id = ? AND document_id = ?
        """,
        (tenant_id, document_id),
    ).fetchone()


def _revision(
    connection: sqlite3.Connection, revision_id: int | None
) -> sqlite3.Row | None:
    if revision_id is None:
        return None
    return connection.execute(
        "SELECT * FROM revisions WHERE revision_id = ?", (revision_id,)
    ).fetchone()


def _revision_groups(connection: sqlite3.Connection, revision_id: int) -> tuple[str, ...]:
    rows = connection.execute(
        "SELECT group_id FROM revision_acl WHERE revision_id = ? ORDER BY group_id",
        (revision_id,),
    ).fetchall()
    return tuple(row["group_id"] for row in rows)


def _event_id(
    tenant_id: str, document_id: str, event_version: int, event_kind: str
) -> str:
    payload = _canonical_json(
        {
            "document_id": document_id,
            "event_kind": event_kind,
            "event_version": event_version,
            "tenant_id": tenant_id,
        }
    )
    return f"evt_{_digest_text(payload)}"


def upsert_record(
    connection: sqlite3.Connection,
    record: SourceRecord,
    config: BuildConfig,
    *,
    run_id: str,
) -> ChangeResult:
    record = _normalise_record(record)
    config = _validate_config(config)
    run_id = _validate_token("run_id", run_id)
    content_hash, source_state_hash, build_state_hash = _state_hashes(record, config)

    with _transaction(connection):
        document = _document(connection, record.tenant_id, record.document_id)
        if document is None:
            connection.execute(
                """
                INSERT INTO documents(
                    tenant_id, document_id, last_source_sequence,
                    current_event_version, deleted, access_blocked
                ) VALUES (?, ?, 0, 0, 0, 1)
                """,
                (record.tenant_id, record.document_id),
            )
            document = _document(connection, record.tenant_id, record.document_id)
        if document is None:
            raise RuntimeError("创建 documents 行后读取失败")

        last_sequence = int(document["last_source_sequence"])
        current = _revision(connection, document["current_revision_id"])
        if record.source_sequence < last_sequence:
            return ChangeResult("stale_ignored", None, None)

        if record.source_sequence == last_sequence:
            if bool(document["deleted"]):
                raise StoreError("相同 source_sequence 不能复活已删除文档")
            if current is None:
                raise StoreError("当前文档缺少 revision，无法判定同序列事件")
            if current["source_state_hash"] != source_state_hash:
                raise StoreError("相同 source_sequence 携带不同来源状态")
            if current["build_state_hash"] == build_state_hash:
                return ChangeResult("noop", None, int(current["revision_number"]))
            action = "reprocessed"
        else:
            if (
                current is not None
                and not bool(document["deleted"])
                and current["source_state_hash"] == source_state_hash
                and current["build_state_hash"] == build_state_hash
            ):
                connection.execute(
                    """
                    UPDATE documents SET last_source_sequence = ?
                    WHERE tenant_id = ? AND document_id = ?
                    """,
                    (record.source_sequence, record.tenant_id, record.document_id),
                )
                return ChangeResult(
                    "checkpoint_advanced", None, int(current["revision_number"])
                )
            if current is None:
                action = "inserted"
            elif bool(document["deleted"]):
                action = "resurrected"
            else:
                action = "updated"

        previous_groups = () if current is None else _revision_groups(
            connection, int(current["revision_id"])
        )
        acl_changed = previous_groups != record.allowed_groups
        revision_number = 1 if current is None else int(current["revision_number"]) + 1
        cursor = connection.execute(
            """
            INSERT INTO revisions(
                tenant_id, document_id, revision_number, source_sequence,
                source_uri, source_version, pipeline_version, content,
                content_hash, source_state_hash, build_state_hash, run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.tenant_id,
                record.document_id,
                revision_number,
                record.source_sequence,
                record.source_uri,
                record.source_version,
                config.pipeline_version,
                record.content,
                content_hash,
                source_state_hash,
                build_state_hash,
                run_id,
            ),
        )
        revision_id = int(cursor.lastrowid)
        connection.executemany(
            "INSERT INTO revision_acl(revision_id, group_id) VALUES (?, ?)",
            [(revision_id, group) for group in record.allowed_groups],
        )

        event_version = int(document["current_event_version"]) + 1
        event_kind = "document.upserted"
        event_id = _event_id(
            record.tenant_id, record.document_id, event_version, event_kind
        )
        must_block = (
            bool(document["deleted"])
            or acl_changed
            or document["published_revision_id"] is None
            or bool(document["access_blocked"])
        )
        connection.execute(
            """
            UPDATE documents SET
                last_source_sequence = ?,
                current_revision_id = ?,
                current_event_version = ?,
                deleted = 0,
                access_blocked = ?
            WHERE tenant_id = ? AND document_id = ?
            """,
            (
                record.source_sequence,
                revision_id,
                event_version,
                int(must_block),
                record.tenant_id,
                record.document_id,
            ),
        )
        connection.execute(
            """
            INSERT INTO outbox(
                event_id, tenant_id, document_id, event_version,
                event_kind, revision_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                record.tenant_id,
                record.document_id,
                event_version,
                event_kind,
                revision_id,
            ),
        )
        return ChangeResult(action, event_id, revision_number)


def delete_document(
    connection: sqlite3.Connection,
    tenant_id: str,
    document_id: str,
    source_sequence: int,
    *,
    reason_code: str,
    run_id: str,
) -> ChangeResult:
    tenant_id = _validate_token("tenant_id", tenant_id)
    document_id = _validate_token("document_id", document_id)
    source_sequence = _validate_sequence(source_sequence)
    run_id = _validate_token("run_id", run_id)
    if reason_code not in DELETE_REASONS:
        raise StoreError(f"reason_code 必须是：{', '.join(sorted(DELETE_REASONS))}")

    with _transaction(connection):
        document = _document(connection, tenant_id, document_id)
        if document is None:
            connection.execute(
                """
                INSERT INTO documents(
                    tenant_id, document_id, last_source_sequence,
                    current_event_version, deleted, access_blocked
                ) VALUES (?, ?, 0, 0, 0, 1)
                """,
                (tenant_id, document_id),
            )
            document = _document(connection, tenant_id, document_id)
        if document is None:
            raise RuntimeError("创建 documents 行后读取失败")

        last_sequence = int(document["last_source_sequence"])
        if source_sequence < last_sequence:
            return ChangeResult("stale_ignored", None, None)
        if source_sequence == last_sequence:
            if bool(document["deleted"]):
                tombstone = connection.execute(
                    """
                    SELECT reason_code FROM tombstones
                    WHERE tenant_id = ? AND document_id = ? AND event_version = ?
                    """,
                    (tenant_id, document_id, document["current_event_version"]),
                ).fetchone()
                if tombstone is None:
                    raise StoreError("删除状态缺少当前墓碑，不能确认幂等重放")
                if tombstone["reason_code"] != reason_code:
                    raise StoreError("相同 source_sequence 的删除原因冲突")
                return ChangeResult("noop", None, None)
            raise StoreError("相同 source_sequence 不能同时表示 upsert 与 delete")

        event_version = int(document["current_event_version"]) + 1
        event_kind = "document.deleted"
        event_id = _event_id(tenant_id, document_id, event_version, event_kind)
        connection.execute(
            """
            UPDATE documents SET
                last_source_sequence = ?,
                current_event_version = ?,
                deleted = 1,
                access_blocked = 1
            WHERE tenant_id = ? AND document_id = ?
            """,
            (source_sequence, event_version, tenant_id, document_id),
        )
        connection.execute(
            """
            INSERT INTO tombstones(
                tenant_id, document_id, event_version, source_sequence,
                reason_code, run_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                document_id,
                event_version,
                source_sequence,
                reason_code,
                run_id,
            ),
        )
        connection.execute(
            """
            INSERT INTO outbox(
                event_id, tenant_id, document_id, event_version, event_kind
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (event_id, tenant_id, document_id, event_version, event_kind),
        )
        return ChangeResult("deleted", event_id, None)


def next_pending_event(connection: sqlite3.Connection) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT * FROM outbox
        WHERE processed = 0
        ORDER BY outbox_id
        LIMIT 1
        """
    ).fetchone()


def project_next_event(
    connection: sqlite3.Connection, *, fail_event_id: str | None = None
) -> ProjectionResult:
    event = next_pending_event(connection)
    if event is None:
        return ProjectionResult("empty", None)
    event_id = str(event["event_id"])
    if fail_event_id == event_id:
        with _transaction(connection):
            connection.execute(
                """
                UPDATE outbox SET attempts = attempts + 1, last_error = ?
                WHERE event_id = ? AND processed = 0
                """,
                ("simulated_projection_failure", event_id),
            )
        return ProjectionResult("failed", event_id)

    with _transaction(connection):
        event = connection.execute(
            "SELECT * FROM outbox WHERE event_id = ? AND processed = 0",
            (event_id,),
        ).fetchone()
        if event is None:
            return ProjectionResult("already_processed", event_id)
        document = _document(
            connection, str(event["tenant_id"]), str(event["document_id"])
        )
        if document is None:
            raise RuntimeError("outbox 指向不存在的 documents 行")

        if event["event_kind"] == "document.upserted":
            if event["revision_id"] is None:
                raise RuntimeError("upsert 事件缺少 revision 指针")
            revision = _revision(connection, int(event["revision_id"]))
            if revision is None or revision["content"] is None:
                raise RuntimeError("upsert 事件缺少可投影 revision 内容")
            if (
                revision["tenant_id"] != event["tenant_id"]
                or revision["document_id"] != event["document_id"]
            ):
                raise RuntimeError("outbox upsert revision 与事件身份不一致")
            is_current = (
                not bool(document["deleted"])
                and int(document["current_event_version"]) == int(event["event_version"])
                and document["current_revision_id"] is not None
                and int(document["current_revision_id"]) == int(revision["revision_id"])
            )
            # 过期 revision 不得物化；否则会在后续删除后残留，或保留从未具备发布资格的内容。
            if is_current:
                connection.execute(
                    """
                    INSERT INTO search_revisions(
                        revision_id, tenant_id, document_id, revision_number,
                        content, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(revision_id) DO UPDATE SET
                        content = excluded.content,
                        content_hash = excluded.content_hash
                    """,
                    (
                        revision["revision_id"],
                        revision["tenant_id"],
                        revision["document_id"],
                        revision["revision_number"],
                        revision["content"],
                        revision["content_hash"],
                    ),
                )
                connection.execute(
                    "DELETE FROM search_acl WHERE revision_id = ?",
                    (revision["revision_id"],),
                )
                groups = _revision_groups(connection, int(revision["revision_id"]))
                connection.executemany(
                    "INSERT INTO search_acl(revision_id, group_id) VALUES (?, ?)",
                    [(revision["revision_id"], group) for group in groups],
                )
                connection.execute(
                    """
                    UPDATE documents SET
                        published_revision_id = ?, access_blocked = 0
                    WHERE tenant_id = ? AND document_id = ?
                    """,
                    (
                        revision["revision_id"],
                        event["tenant_id"],
                        event["document_id"],
                    ),
                )
        else:
            is_current_delete = (
                bool(document["deleted"])
                and int(document["current_event_version"]) == int(event["event_version"])
            )
            if is_current_delete:
                revision_ids = connection.execute(
                    """
                    SELECT revision_id FROM search_revisions
                    WHERE tenant_id = ? AND document_id = ?
                    """,
                    (event["tenant_id"], event["document_id"]),
                ).fetchall()
                connection.executemany(
                    "DELETE FROM search_revisions WHERE revision_id = ?",
                    [(row["revision_id"],) for row in revision_ids],
                )
                connection.execute(
                    """
                    UPDATE documents SET published_revision_id = NULL
                    WHERE tenant_id = ? AND document_id = ?
                    """,
                    (event["tenant_id"], event["document_id"]),
                )

        connection.execute(
            """
            UPDATE outbox SET
                processed = 1, attempts = attempts + 1, last_error = NULL
            WHERE event_id = ?
            """,
            (event_id,),
        )
    return ProjectionResult("projected", event_id)


def drain_outbox(connection: sqlite3.Connection) -> list[str]:
    event_ids: list[str] = []
    while True:
        result = project_next_event(connection)
        if result.action == "empty":
            return event_ids
        if result.action != "projected" or result.event_id is None:
            raise RuntimeError(f"无法排空 outbox：{result.action}")
        event_ids.append(result.event_id)


def search_visible(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    subject_groups: Sequence[str],
    term: str,
    limit: int = MAX_SEARCH_RESULTS,
) -> list[dict[str, Any]]:
    tenant_id = _validate_token("tenant_id", tenant_id)
    term = _validate_token("term", term, maximum=500)
    if isinstance(subject_groups, (str, bytes)) or not isinstance(
        subject_groups, Sequence
    ):
        raise StoreError("subject_groups 必须是字符串序列")
    if len(subject_groups) > MAX_SUBJECT_GROUPS:
        raise StoreError(f"subject_groups 不得超过 {MAX_SUBJECT_GROUPS} 项")
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 1 <= limit <= MAX_SEARCH_RESULTS
    ):
        raise StoreError(f"limit 必须是 1..{MAX_SEARCH_RESULTS} 的整数")
    groups = tuple(
        sorted({_validate_token("group_id", group) for group in subject_groups})
    )
    if not groups:
        return []
    placeholders = ",".join("?" for _ in groups)
    rows = connection.execute(
        f"""
        SELECT
            d.document_id,
            s.revision_number,
            s.revision_id,
            s.content AS search_content,
            s.content_hash AS search_content_hash,
            r.content,
            r.content_hash,
            r.source_uri,
            r.source_version,
            r.pipeline_version,
            r.source_state_hash,
            r.build_state_hash
        FROM documents AS d
        JOIN search_revisions AS s
          ON s.revision_id = d.published_revision_id
         AND s.tenant_id = d.tenant_id
         AND s.document_id = d.document_id
        JOIN revisions AS r
          ON r.revision_id = d.published_revision_id
         AND r.tenant_id = d.tenant_id
         AND r.document_id = d.document_id
        WHERE d.tenant_id = ?
          AND d.deleted = 0
          AND d.access_blocked = 0
          AND EXISTS (
              SELECT 1 FROM revision_acl AS a
              WHERE a.revision_id = r.revision_id
                AND a.group_id IN ({placeholders})
          )
          AND instr(lower(s.content), lower(?)) > 0
        ORDER BY d.document_id
        LIMIT ?
        """,
        (tenant_id, *groups, term, limit + 1),
    ).fetchall()
    if len(rows) > limit:
        raise StoreError("候选窗口超过 limit；必须收窄查询或显式分页")
    result: list[dict[str, Any]] = []
    requested_groups = set(groups)
    for row in rows:
        revision_id = int(row["revision_id"])
        canonical_groups = _revision_groups(connection, revision_id)
        search_groups = tuple(
            item["group_id"]
            for item in connection.execute(
                "SELECT group_id FROM search_acl WHERE revision_id = ? ORDER BY group_id",
                (revision_id,),
            ).fetchall()
        )
        integrity_errors = list(
            _persisted_revision_hash_errors(row, canonical_groups)
        )
        search_content = row["search_content"]
        if (
            not isinstance(search_content, str)
            or _digest_text(search_content) != row["search_content_hash"]
            or row["search_content_hash"] != row["content_hash"]
        ):
            integrity_errors.append("search_content_hash_mismatch")
        if search_groups != canonical_groups:
            integrity_errors.append("published_acl_mismatch")
        if integrity_errors:
            raise StoreError(
                "查询候选完整性失败："
                + ",".join(sorted(set(integrity_errors)))
            )
        if not requested_groups.intersection(canonical_groups):
            continue
        result.append(
            {
                "document_id": row["document_id"],
                "revision_number": row["revision_number"],
                "content": search_content,
            }
        )
    return result


def reconcile(connection: sqlite3.Connection) -> dict[str, int]:
    scalar_queries = {
        "active_documents": "SELECT count(*) FROM documents WHERE deleted = 0",
        "blocked_active_documents": (
            "SELECT count(*) FROM documents WHERE deleted = 0 AND access_blocked = 1"
        ),
        "pending_events": "SELECT count(*) FROM outbox WHERE processed = 0",
        "revisions": "SELECT count(*) FROM revisions",
        "search_revisions": "SELECT count(*) FROM search_revisions",
        "tombstones": "SELECT count(*) FROM tombstones",
        "unpublished_active_documents": """
            SELECT count(*) FROM documents
            WHERE deleted = 0 AND published_revision_id IS NULL
        """,
        "published_not_current_documents": """
            SELECT count(*) FROM documents
            WHERE deleted = 0
              AND published_revision_id IS NOT NULL
              AND published_revision_id <> current_revision_id
        """,
        "missing_published_projection": """
            SELECT count(*) FROM documents AS d
            WHERE d.published_revision_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM search_revisions AS s
                  WHERE s.revision_id = d.published_revision_id
              )
        """,
        "orphan_search_acl": """
            SELECT count(*) FROM search_acl AS a
            WHERE NOT EXISTS (
                SELECT 1 FROM search_revisions AS s
                WHERE s.revision_id = a.revision_id
            )
        """,
        "deleted_projection_rows": """
            SELECT count(*) FROM search_revisions AS s
            JOIN documents AS d
              ON d.tenant_id = s.tenant_id AND d.document_id = s.document_id
            WHERE d.deleted = 1
        """,
        "published_cross_identity": """
            SELECT count(*) FROM documents AS d
            JOIN search_revisions AS s
              ON s.revision_id = d.published_revision_id
            WHERE s.tenant_id <> d.tenant_id
               OR s.document_id <> d.document_id
        """,
        "published_hash_mismatch": """
            SELECT count(*) FROM documents AS d
            JOIN search_revisions AS s
              ON s.revision_id = d.published_revision_id
            JOIN revisions AS r
              ON r.revision_id = d.published_revision_id
            WHERE s.content_hash <> r.content_hash
        """,
        "published_acl_mismatch": """
            SELECT count(*) FROM documents AS d
            WHERE d.published_revision_id IS NOT NULL
              AND (
                EXISTS (
                    SELECT 1 FROM revision_acl AS r
                    WHERE r.revision_id = d.published_revision_id
                      AND NOT EXISTS (
                          SELECT 1 FROM search_acl AS s
                          WHERE s.revision_id = r.revision_id
                            AND s.group_id = r.group_id
                      )
                )
                OR EXISTS (
                    SELECT 1 FROM search_acl AS s
                    WHERE s.revision_id = d.published_revision_id
                      AND NOT EXISTS (
                          SELECT 1 FROM revision_acl AS r
                          WHERE r.revision_id = s.revision_id
                            AND r.group_id = s.group_id
                      )
                )
              )
        """,
    }
    result: dict[str, int] = {}
    for name, query in scalar_queries.items():
        row = connection.execute(query).fetchone()
        result[name] = int(row[0])
    body_hash_tables = {
        "canonical_content_hash_mismatch": "revisions",
        "search_content_hash_mismatch": "search_revisions",
    }
    for name, table_name in body_hash_tables.items():
        rows = connection.execute(
            f"SELECT content, content_hash FROM {table_name} WHERE content IS NOT NULL"
        ).fetchall()
        result[name] = sum(
            1
            for row in rows
            if not isinstance(row["content"], str)
            or _digest_text(row["content"]) != row["content_hash"]
        )
    canonical_rows = connection.execute(
        "SELECT * FROM revisions WHERE content IS NOT NULL"
    ).fetchall()
    canonical_hash_errors = {
        "canonical_source_state_hash_mismatch": 0,
        "canonical_build_state_hash_mismatch": 0,
    }
    for row in canonical_rows:
        errors = _persisted_revision_hash_errors(
            row, _revision_groups(connection, int(row["revision_id"]))
        )
        for name in canonical_hash_errors:
            canonical_hash_errors[name] += int(name in errors)
    result.update(canonical_hash_errors)
    return result


def require_reconciled(
    connection: sqlite3.Connection, *, require_empty_outbox: bool = True
) -> dict[str, int]:
    report = reconcile(connection)
    failures = {
        name: report[name]
        for name in (
            "missing_published_projection",
            "orphan_search_acl",
            "deleted_projection_rows",
            "published_cross_identity",
            "published_hash_mismatch",
            "canonical_content_hash_mismatch",
            "canonical_source_state_hash_mismatch",
            "canonical_build_state_hash_mismatch",
            "search_content_hash_mismatch",
            "published_acl_mismatch",
        )
        if report[name]
    }
    if require_empty_outbox and report["pending_events"]:
        failures["pending_events"] = report["pending_events"]
    if require_empty_outbox:
        for name in (
            "unpublished_active_documents",
            "published_not_current_documents",
            "blocked_active_documents",
        ):
            if report[name]:
                failures[name] = report[name]
    if failures:
        raise StoreError(f"对账失败：{_canonical_json(failures)}")
    return report


def purge_deleted_canonical_content(
    connection: sqlite3.Connection, *, tenant_id: str, document_id: str
) -> int:
    tenant_id = _validate_token("tenant_id", tenant_id)
    document_id = _validate_token("document_id", document_id)
    with _transaction(connection):
        document = _document(connection, tenant_id, document_id)
        if document is None or not bool(document["deleted"]):
            raise StoreError("只有已删除文档才能执行 canonical content purge")
        pending = connection.execute(
            """
            SELECT count(*) FROM outbox
            WHERE tenant_id = ? AND document_id = ? AND processed = 0
            """,
            (tenant_id, document_id),
        ).fetchone()[0]
        projected = connection.execute(
            """
            SELECT count(*) FROM search_revisions
            WHERE tenant_id = ? AND document_id = ?
            """,
            (tenant_id, document_id),
        ).fetchone()[0]
        if pending or projected:
            raise StoreError("删除事件尚未完成传播，不能清除 canonical content")
        cursor = connection.execute(
            """
            UPDATE revisions SET content = NULL, content_purged = 1
            WHERE tenant_id = ? AND document_id = ? AND content_purged = 0
            """,
            (tenant_id, document_id),
        )
        connection.execute(
            """
            UPDATE tombstones SET canonical_content_purged = 1
            WHERE tenant_id = ? AND document_id = ?
            """,
            (tenant_id, document_id),
        )
        return int(cursor.rowcount)


def main() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", newline="\n")
    connection = connect()
    config = BuildConfig("pipeline-v1")
    actions: list[dict[str, Any]] = []
    public = SourceRecord(
        "tenant-a",
        "policy:leave",
        1,
        "https://kb.example.invalid/policy/leave",
        "v1",
        "请假政策要求提前提交。",
        ("employees",),
    )
    secret = SourceRecord(
        "tenant-a",
        "policy:security",
        1,
        "https://kb.example.invalid/policy/security",
        "v1",
        "安全策略要求管理员复核。",
        ("admins",),
    )
    actions.append(asdict(upsert_record(connection, public, config, run_id="run-1")))
    actions.append(asdict(upsert_record(connection, secret, config, run_id="run-1")))
    drain_outbox(connection)

    updated = SourceRecord(
        "tenant-a",
        "policy:leave",
        2,
        public.source_uri,
        "v2",
        "请假政策要求提前两天提交。",
        public.allowed_groups,
    )
    update_result = upsert_record(connection, updated, config, run_id="run-2")
    actions.append(asdict(update_result))
    before_publish = search_visible(
        connection,
        tenant_id="tenant-a",
        subject_groups=("employees",),
        term="请假",
    )
    failed = project_next_event(connection, fail_event_id=update_result.event_id)
    actions.append(asdict(failed))
    project_next_event(connection)
    after_publish = search_visible(
        connection,
        tenant_id="tenant-a",
        subject_groups=("employees",),
        term="请假",
    )

    deletion = delete_document(
        connection,
        "tenant-a",
        "policy:leave",
        3,
        reason_code="source_deleted",
        run_id="run-3",
    )
    actions.append(asdict(deletion))
    drain_outbox(connection)
    purged_revisions = purge_deleted_canonical_content(
        connection, tenant_id="tenant-a", document_id="policy:leave"
    )
    report = require_reconciled(connection)
    output = {
        "schema_version": SCHEMA_VERSION,
        "actions": actions,
        "before_publish": before_publish,
        "after_publish": after_publish,
        "purged_revisions": purged_revisions,
        "reconciliation": report,
    }
    print(json.dumps(output, ensure_ascii=False, allow_nan=False, indent=2))
    connection.close()


if __name__ == "__main__":
    main()
