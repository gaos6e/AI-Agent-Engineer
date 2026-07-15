from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import unittest

import knowledge_store as subject


class KnowledgeStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = subject.connect()
        self.config = subject.BuildConfig("pipeline-v1")

    def tearDown(self) -> None:
        self.connection.close()

    def record(
        self,
        *,
        tenant: str = "tenant-a",
        document: str = "policy:leave",
        sequence: int = 1,
        version: str = "v1",
        content: str = "请假政策要求提前提交。",
        groups: tuple[str, ...] = ("employees",),
        uri: str = "https://kb.example.invalid/policy/leave",
    ) -> subject.SourceRecord:
        return subject.SourceRecord(
            tenant,
            document,
            sequence,
            uri,
            version,
            content,
            groups,
        )

    def search(
        self,
        *,
        tenant: str = "tenant-a",
        groups: tuple[str, ...] = ("employees",),
        term: str = "请假",
    ) -> list[dict]:
        return subject.search_visible(
            self.connection,
            tenant_id=tenant,
            subject_groups=groups,
            term=term,
        )

    def insert_and_publish(self, record: subject.SourceRecord | None = None) -> subject.ChangeResult:
        result = subject.upsert_record(
            self.connection,
            record or self.record(),
            self.config,
            run_id="run-1",
        )
        subject.drain_outbox(self.connection)
        return result

    def test_new_document_is_hidden_until_projection_is_published(self) -> None:
        result = subject.upsert_record(
            self.connection, self.record(), self.config, run_id="run-1"
        )

        self.assertEqual("inserted", result.action)
        self.assertEqual([], self.search())
        projected = subject.project_next_event(self.connection)
        self.assertEqual("projected", projected.action)
        self.assertEqual(1, self.search()[0]["revision_number"])

    def test_same_state_is_noop_even_if_group_order_changes(self) -> None:
        first = self.record(groups=("group-b", "group-a"))
        subject.upsert_record(self.connection, first, self.config, run_id="run-1")
        repeated = self.record(groups=("group-a", "group-b"))

        result = subject.upsert_record(
            self.connection, repeated, self.config, run_id="run-retry"
        )

        self.assertEqual("noop", result.action)
        self.assertEqual(1, self.connection.execute("SELECT count(*) FROM revisions").fetchone()[0])

    def test_higher_source_sequence_with_same_state_only_advances_checkpoint(self) -> None:
        self.insert_and_publish()

        result = subject.upsert_record(
            self.connection,
            self.record(sequence=2),
            self.config,
            run_id="run-2",
        )

        self.assertEqual("checkpoint_advanced", result.action)
        self.assertEqual(1, self.connection.execute("SELECT count(*) FROM revisions").fetchone()[0])
        document = self.connection.execute("SELECT * FROM documents").fetchone()
        self.assertEqual(2, document["last_source_sequence"])

    def test_older_source_event_is_ignored(self) -> None:
        self.insert_and_publish(self.record(sequence=2))

        result = subject.upsert_record(
            self.connection,
            self.record(sequence=1, content="旧事件不应覆盖"),
            self.config,
            run_id="late-run",
        )

        self.assertEqual("stale_ignored", result.action)
        self.assertEqual("请假政策要求提前提交。", self.search()[0]["content"])

    def test_same_sequence_with_different_source_state_is_conflict(self) -> None:
        subject.upsert_record(self.connection, self.record(), self.config, run_id="run-1")

        with self.assertRaisesRegex(subject.StoreError, "相同 source_sequence"):
            subject.upsert_record(
                self.connection,
                self.record(content="冲突内容"),
                self.config,
                run_id="run-conflict",
            )
        self.assertEqual(1, self.connection.execute("SELECT count(*) FROM revisions").fetchone()[0])

    def test_pipeline_change_reprocesses_same_source_sequence(self) -> None:
        self.insert_and_publish()

        result = subject.upsert_record(
            self.connection,
            self.record(),
            subject.BuildConfig("pipeline-v2"),
            run_id="reprocess-1",
        )

        self.assertEqual("reprocessed", result.action)
        self.assertEqual(2, result.revision_number)

    def test_content_update_keeps_old_published_revision_until_success(self) -> None:
        self.insert_and_publish()
        updated = self.record(
            sequence=2,
            version="v2",
            content="请假政策要求提前两天提交。",
        )

        subject.upsert_record(self.connection, updated, self.config, run_id="run-2")

        self.assertEqual(1, self.search()[0]["revision_number"])
        subject.project_next_event(self.connection)
        self.assertEqual(2, self.search()[0]["revision_number"])

    def test_projection_failure_preserves_old_version_and_is_retryable(self) -> None:
        self.insert_and_publish()
        result = subject.upsert_record(
            self.connection,
            self.record(sequence=2, version="v2", content="请假政策第二版"),
            self.config,
            run_id="run-2",
        )

        failed = subject.project_next_event(self.connection, fail_event_id=result.event_id)

        self.assertEqual("failed", failed.action)
        self.assertEqual(1, self.search()[0]["revision_number"])
        event = self.connection.execute(
            "SELECT processed, attempts, last_error FROM outbox WHERE event_id = ?",
            (result.event_id,),
        ).fetchone()
        self.assertEqual((0, 1, "simulated_projection_failure"), tuple(event))
        subject.project_next_event(self.connection)
        self.assertEqual(2, self.search()[0]["revision_number"])

    def test_acl_change_blocks_old_projection_before_new_acl_is_published(self) -> None:
        self.insert_and_publish(self.record(groups=("admins",), content="内部安全策略"))
        changed = self.record(
            sequence=2,
            version="v2",
            groups=("security",),
            content="内部安全策略",
        )

        subject.upsert_record(self.connection, changed, self.config, run_id="acl-change")

        self.assertEqual([], self.search(groups=("admins",), term="安全"))
        self.assertEqual([], self.search(groups=("security",), term="安全"))
        subject.project_next_event(self.connection)
        self.assertEqual([], self.search(groups=("admins",), term="安全"))
        self.assertEqual("policy:leave", self.search(groups=("security",), term="安全")[0]["document_id"])

    def test_tenant_filter_is_applied_in_query(self) -> None:
        self.insert_and_publish()
        other = self.record(tenant="tenant-b", document="policy:other")
        subject.upsert_record(self.connection, other, self.config, run_id="run-b")
        subject.drain_outbox(self.connection)

        self.assertEqual(["policy:leave"], [row["document_id"] for row in self.search()])
        self.assertEqual(
            ["policy:other"],
            [row["document_id"] for row in self.search(tenant="tenant-b")],
        )

    def test_any_matching_subject_group_grants_access(self) -> None:
        self.insert_and_publish(self.record(groups=("engineering", "reviewers")))

        self.assertEqual(1, len(self.search(groups=("other", "reviewers"))))
        self.assertEqual([], self.search(groups=("other",)))
        self.assertEqual([], self.search(groups=()))

    def test_delete_hides_immediately_then_removes_projection(self) -> None:
        self.insert_and_publish()

        result = subject.delete_document(
            self.connection,
            "tenant-a",
            "policy:leave",
            2,
            reason_code="source_deleted",
            run_id="delete-1",
        )

        self.assertEqual("deleted", result.action)
        self.assertEqual([], self.search())
        self.assertEqual(1, subject.reconcile(self.connection)["deleted_projection_rows"])
        subject.project_next_event(self.connection)
        self.assertEqual(0, subject.reconcile(self.connection)["deleted_projection_rows"])

    def test_repeated_delete_is_noop_and_tombstone_is_not_duplicated(self) -> None:
        self.insert_and_publish()
        subject.delete_document(
            self.connection,
            "tenant-a",
            "policy:leave",
            2,
            reason_code="source_deleted",
            run_id="delete-1",
        )

        result = subject.delete_document(
            self.connection,
            "tenant-a",
            "policy:leave",
            2,
            reason_code="source_deleted",
            run_id="delete-retry",
        )

        self.assertEqual("noop", result.action)
        self.assertEqual(1, self.connection.execute("SELECT count(*) FROM tombstones").fetchone()[0])

    def test_delete_for_missing_document_creates_tombstone(self) -> None:
        result = subject.delete_document(
            self.connection,
            "tenant-a",
            "missing",
            7,
            reason_code="source_deleted",
            run_id="delete-missing",
        )

        self.assertEqual("deleted", result.action)
        subject.drain_outbox(self.connection)
        row = self.connection.execute("SELECT * FROM documents").fetchone()
        self.assertEqual((7, 1), (row["last_source_sequence"], row["deleted"]))

    def test_stale_delete_does_not_remove_newer_content(self) -> None:
        self.insert_and_publish(self.record(sequence=3))

        result = subject.delete_document(
            self.connection,
            "tenant-a",
            "policy:leave",
            2,
            reason_code="source_deleted",
            run_id="late-delete",
        )

        self.assertEqual("stale_ignored", result.action)
        self.assertEqual(1, len(self.search()))

    def test_same_sequence_cannot_be_upsert_and_delete(self) -> None:
        self.insert_and_publish()

        with self.assertRaisesRegex(subject.StoreError, "同时表示"):
            subject.delete_document(
                self.connection,
                "tenant-a",
                "policy:leave",
                1,
                reason_code="source_deleted",
                run_id="conflict-delete",
            )

    def test_resurrection_requires_newer_sequence_and_waits_for_projection(self) -> None:
        self.insert_and_publish()
        subject.delete_document(
            self.connection,
            "tenant-a",
            "policy:leave",
            2,
            reason_code="source_deleted",
            run_id="delete-1",
        )
        subject.drain_outbox(self.connection)

        with self.assertRaisesRegex(subject.StoreError, "不能复活"):
            subject.upsert_record(
                self.connection,
                self.record(sequence=2),
                self.config,
                run_id="bad-resurrection",
            )
        result = subject.upsert_record(
            self.connection,
            self.record(sequence=3, version="v3"),
            self.config,
            run_id="resurrection",
        )
        self.assertEqual("resurrected", result.action)
        self.assertEqual([], self.search())
        subject.drain_outbox(self.connection)
        self.assertEqual(1, len(self.search()))

    def test_source_version_or_uri_change_creates_revision(self) -> None:
        self.insert_and_publish()

        result = subject.upsert_record(
            self.connection,
            self.record(sequence=2, version="v2", uri="https://kb.example.invalid/new"),
            self.config,
            run_id="metadata-change",
        )

        self.assertEqual("updated", result.action)
        self.assertEqual(2, result.revision_number)

    def test_newline_and_nfc_normalisation_make_equivalent_retry_noop(self) -> None:
        first = self.record(content="Cafe\u0301\r\n规则")
        subject.upsert_record(self.connection, first, self.config, run_id="run-1")
        second = self.record(content="Café\n规则")

        result = subject.upsert_record(
            self.connection, second, self.config, run_id="run-retry"
        )

        self.assertEqual("noop", result.action)

    def test_invalid_inputs_fail_before_database_mutation(self) -> None:
        invalid_records = [
            self.record(tenant=" tenant-a"),
            self.record(sequence=0),
            self.record(content="   "),
            self.record(groups=()),
            self.record(groups=("duplicate", "duplicate")),
            self.record(groups=("bad\x00group",)),
        ]
        for record in invalid_records:
            with self.subTest(record=record), self.assertRaises(subject.StoreError):
                subject.upsert_record(
                    self.connection, record, self.config, run_id="invalid"
                )
        self.assertEqual(0, self.connection.execute("SELECT count(*) FROM documents").fetchone()[0])

    def test_content_size_limit_is_enforced(self) -> None:
        oversized = self.record(content="a" * (subject.MAX_CONTENT_BYTES + 1))

        with self.assertRaisesRegex(subject.StoreError, "不得超过"):
            subject.upsert_record(
                self.connection, oversized, self.config, run_id="oversized"
            )

    def test_multiple_pending_revisions_publish_only_latest_pointer(self) -> None:
        subject.upsert_record(self.connection, self.record(), self.config, run_id="run-1")
        subject.upsert_record(
            self.connection,
            self.record(sequence=2, version="v2", content="请假政策第二版"),
            self.config,
            run_id="run-2",
        )

        subject.project_next_event(self.connection)
        self.assertEqual([], self.search())
        subject.project_next_event(self.connection)
        self.assertEqual(2, self.search()[0]["revision_number"])

    def test_reconcile_reports_pending_then_passes_after_drain(self) -> None:
        subject.upsert_record(self.connection, self.record(), self.config, run_id="run-1")

        with self.assertRaisesRegex(subject.StoreError, "pending_events"):
            subject.require_reconciled(self.connection)
        subject.drain_outbox(self.connection)
        report = subject.require_reconciled(self.connection)
        self.assertEqual(0, report["pending_events"])
        self.assertEqual(0, report["missing_published_projection"])

    def test_reconcile_rejects_active_document_with_no_publish_path(self) -> None:
        subject.upsert_record(self.connection, self.record(), self.config, run_id="run-1")
        self.connection.execute("UPDATE outbox SET processed = 1")

        with self.assertRaisesRegex(subject.StoreError, "unpublished_active_documents"):
            subject.require_reconciled(self.connection)

    def test_query_defends_against_cross_tenant_pointer_corruption(self) -> None:
        self.insert_and_publish()
        other = self.record(
            tenant="tenant-b",
            document="secret:other",
            content="请假机密",
        )
        subject.upsert_record(self.connection, other, self.config, run_id="run-b")
        subject.drain_outbox(self.connection)
        other_revision = self.connection.execute(
            """
            SELECT revision_id FROM revisions
            WHERE tenant_id = 'tenant-b' AND document_id = 'secret:other'
            """
        ).fetchone()[0]
        self.connection.execute(
            """
            UPDATE documents SET published_revision_id = ?
            WHERE tenant_id = 'tenant-a' AND document_id = 'policy:leave'
            """,
            (other_revision,),
        )

        self.assertEqual([], self.search())
        report = subject.reconcile(self.connection)
        self.assertEqual(1, report["published_cross_identity"])
        with self.assertRaisesRegex(subject.StoreError, "published_cross_identity"):
            subject.require_reconciled(self.connection)

    def test_purge_waits_for_delete_projection_then_nulls_canonical_content(self) -> None:
        self.insert_and_publish()
        subject.delete_document(
            self.connection,
            "tenant-a",
            "policy:leave",
            2,
            reason_code="user_request",
            run_id="delete-1",
        )

        with self.assertRaisesRegex(subject.StoreError, "尚未完成传播"):
            subject.purge_deleted_canonical_content(
                self.connection, tenant_id="tenant-a", document_id="policy:leave"
            )
        subject.drain_outbox(self.connection)
        purged = subject.purge_deleted_canonical_content(
            self.connection, tenant_id="tenant-a", document_id="policy:leave"
        )
        revision = self.connection.execute("SELECT content, content_purged FROM revisions").fetchone()
        tombstone = self.connection.execute(
            "SELECT canonical_content_purged FROM tombstones"
        ).fetchone()
        self.assertEqual(1, purged)
        self.assertEqual((None, 1), tuple(revision))
        self.assertEqual(1, tombstone[0])

    def test_obsolete_delete_event_cannot_purge_newer_resurrection(self) -> None:
        self.insert_and_publish()
        subject.delete_document(
            self.connection,
            "tenant-a",
            "policy:leave",
            2,
            reason_code="source_deleted",
            run_id="delete-1",
        )
        subject.upsert_record(
            self.connection,
            self.record(sequence=3, version="v3"),
            self.config,
            run_id="resurrect",
        )

        subject.project_next_event(self.connection)
        self.assertEqual([], self.search())
        subject.project_next_event(self.connection)
        self.assertEqual(1, len(self.search()))

    def test_source_record_schema_matches_python_contract(self) -> None:
        schema = json.loads(
            Path(__file__).with_name("source-record.schema.json").read_text(encoding="utf-8")
        )

        self.assertEqual("https://json-schema.org/draft/2020-12/schema", schema["$schema"])
        self.assertEqual(
            {
                "tenant_id",
                "document_id",
                "source_sequence",
                "source_uri",
                "source_version",
                "content",
                "allowed_groups",
            },
            set(schema["required"]),
        )
        self.assertEqual(100000, schema["properties"]["content"]["x-maxUtf8Bytes"])

    def test_main_output_is_deterministic_json_with_reconciled_state(self) -> None:
        first = io.StringIO()
        second = io.StringIO()
        with redirect_stdout(first):
            subject.main()
        with redirect_stdout(second):
            subject.main()

        payload = json.loads(first.getvalue())
        self.assertEqual(first.getvalue(), second.getvalue())
        self.assertEqual(0, payload["reconciliation"]["pending_events"])
        self.assertEqual(2, payload["after_publish"][0]["revision_number"])


if __name__ == "__main__":
    unittest.main()
