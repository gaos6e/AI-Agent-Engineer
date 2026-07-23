"""Regression tests for the SQLite Tool Result v2 persistence project."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import copy
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch


PERSISTENCE_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = PERSISTENCE_DIR.parent
sys.path.insert(0, str(PERSISTENCE_DIR))
sys.path.insert(0, str(EXAMPLES_DIR))

import persistent_tool_runtime as persisted  # noqa: E402
import tool_dispatcher as tool_v2  # noqa: E402


FIXTURE_PATH = PERSISTENCE_DIR / "persistence-case.json"
SCRIPT_PATH = PERSISTENCE_DIR / "persistent_tool_runtime.py"
DEEP_JSON_NESTING = 4_096


def deeply_nested_json() -> str:
    """Stay below the fixture byte cap while exceeding normal decoder recursion."""

    return "[" * DEEP_JSON_NESTING + "0" + "]" * DEEP_JSON_NESTING


def principal(
    subject_id: str = "user-1",
    tenant_id: str = "tenant-a",
    roles: tuple[str, ...] = (),
) -> tool_v2.Principal:
    return tool_v2.Principal(tenant_id, subject_id, roles)


def write_call(
    reason: str = "duplicate",
    *,
    order_ref: str = "ORDER-7",
    key: str | None = "persistent-key-1",
    call_id: str = "call-persistent",
    operation_id: str = "operation-persistent",
    response_id: str = "response-persistent",
    provider: str = "openai",
    api_family: str = "responses",
    adapter_revision: str = "openai-responses-v1",
) -> tool_v2.ToolCall:
    return tool_v2.ToolCall(
        call_id,
        operation_id,
        "create_refund_draft",
        {"order_ref": order_ref, "reason": reason},
        key,
        provider,
        api_family,
        response_id,
        adapter_revision,
    )


def code(package: dict[str, object]) -> str:
    model = package["model_result"]
    if not isinstance(model, dict):
        raise TypeError("model_result must be an object")
    if model["status"] == "succeeded":
        return "OK"
    error = model["error"]
    if not isinstance(error, dict):
        raise TypeError("failed model_result must contain error")
    return str(error["code"])


def delivery(package: dict[str, object]) -> str:
    model = package["model_result"]
    if not isinstance(model, dict) or not isinstance(model["execution"], dict):
        raise TypeError("model_result.execution must be an object")
    return str(model["execution"]["delivery"])


def status_ref(package: dict[str, object]) -> str:
    audit = package["protected_audit"]
    if not isinstance(audit, dict) or not isinstance(audit["downstream"], dict):
        raise TypeError("protected_audit.downstream must be an object")
    value = audit["downstream"]["status_ref"]
    if not isinstance(value, str):
        raise TypeError("result must contain status_ref")
    return value


class FixtureBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = persisted.load_fixture(FIXTURE_PATH)

    def _write(self, directory: str, text: str | bytes) -> Path:
        path = Path(directory) / "case.json"
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text, encoding="utf-8")
        return path

    def test_fixture_loads_exact_contract(self) -> None:
        self.assertEqual([], persisted.validate_fixture(self.fixture))
        self.assertEqual(persisted.FIXTURE_SCHEMA_VERSION, self.fixture["schema_version"])

    def test_fixture_builds_v2_principal_and_call(self) -> None:
        actor, call = persisted.fixture_principal_call(self.fixture)
        self.assertIsInstance(actor, tool_v2.Principal)
        self.assertIsInstance(call, tool_v2.ToolCall)
        self.assertEqual("create_refund_draft", call.name)

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, '{"schema_version":"a","schema_version":"b"}')
            with self.assertRaises(persisted.PersistenceFixtureError):
                persisted.load_fixture(path)

    def test_nonfinite_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, '{"value":NaN}')
            with self.assertRaises(persisted.PersistenceFixtureError):
                persisted.load_fixture(path)

    def test_invalid_utf8_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, b"\xff")
            with self.assertRaises(persisted.PersistenceFixtureError):
                persisted.load_fixture(path)

    def test_oversize_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, b" " * (persisted.MAX_FIXTURE_BYTES + 1))
            with self.assertRaises(persisted.PersistenceFixtureError):
                persisted.load_fixture(path)

    def test_nested_fixture_is_rejected_before_decoder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = deeply_nested_json()
            self.assertLess(len(payload.encode("utf-8")), persisted.MAX_FIXTURE_BYTES)
            path = self._write(
                directory,
                payload,
            )
            with self.assertRaisesRegex(persisted.PersistenceFixtureError, "nesting"):
                persisted.load_fixture(path)

    def test_extra_root_field_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["extra"] = True
        self.assertTrue(any("root fields" in error for error in persisted.validate_fixture(changed)))

    def test_roles_must_be_sorted_and_unique(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["principal"]["roles"] = ["z", "a", "a"]
        self.assertTrue(any("roles" in error for error in persisted.validate_fixture(changed)))

    def test_boolean_now_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["now"] = True
        self.assertTrue(any("now" in error for error in persisted.validate_fixture(changed)))
        changed["now"] = persisted.MAX_PORTABLE_UNIX_SECONDS
        self.assertTrue(any("now" in error for error in persisted.validate_fixture(changed)))

    def test_provider_revision_mismatch_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["execution_context"]["adapter_revision"] = "invented"
        self.assertTrue(any("provider profile" in error for error in persisted.validate_fixture(changed)))

    def test_missing_idempotency_key_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["execution_context"]["idempotency_key"] = None
        self.assertTrue(any("idempotency_key" in error for error in persisted.validate_fixture(changed)))

    def test_non_write_tool_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["proposal"]["name"] = "get_order"
        self.assertTrue(any("create_refund_draft" in error for error in persisted.validate_fixture(changed)))


class RuntimeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary.name) / "runtime.sqlite3"
        self.runtime = persisted.PersistentToolRuntime(self.database)
        self.actor = principal()
        self.call = write_call()
        self.spec = self.runtime.contract.registry[self.call.name]
        self.now = 1_784_419_200

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def approval(
        self,
        call: tool_v2.ToolCall | None = None,
        *,
        mode: str = "valid",
    ) -> tuple[tool_v2.Approval, ...]:
        selected = self.call if call is None else call
        return tool_v2.make_approval(
            self.actor,
            selected,
            self.runtime.contract.registry.get(selected.name),
            mode,
            self.now,
        )

    def dispatch(
        self,
        call: tool_v2.ToolCall | None = None,
        *,
        failure: str = "none",
        approvals: tuple[tool_v2.Approval, ...] | None = None,
    ) -> dict[str, object]:
        selected = self.call if call is None else call
        selected_approvals = self.approval(selected) if approvals is None else approvals
        return self.runtime.dispatch(
            self.actor,
            selected,
            approvals=selected_approvals,
            now=self.now,
            failure=failure,
        )

    def status_call(
        self,
        reference: str,
        call: tool_v2.ToolCall | None = None,
    ) -> tool_v2.ToolCall:
        selected = self.call if call is None else call
        return persisted.status_query_call(selected, reference)


class DatabaseContractTests(RuntimeTestCase):
    def test_database_uses_wal_and_full_synchronous(self) -> None:
        audit = self.runtime.audit_database()
        self.assertEqual("wal", audit["journal_mode"])
        self.assertEqual(2, audit["synchronous"])

    def test_database_integrity_and_foreign_keys_are_clean(self) -> None:
        with patch.object(
            self.runtime, "_connect", wraps=self.runtime._connect
        ) as connect:
            audit = self.runtime.audit_database()
        self.assertEqual(1, connect.call_count)
        self.assertEqual(["ok"], audit["integrity_check"])
        self.assertEqual([], audit["foreign_key_violations"])
        self.assertEqual([], audit["semantic_errors"])
        self.assertTrue(audit["passed"])

    def test_orphan_receipt_audit_uses_opaque_reference(self) -> None:
        secrets = (
            "tenant-audit-secret",
            "subject-audit-secret",
            "tool-audit-secret",
            "idempotency-audit-secret",
        )
        with self.runtime._connect() as connection:
            connection.execute(
                """
                INSERT INTO downstream_receipts (
                    tenant_id, subject_id, tool_name, idempotency_key,
                    request_sha256, receipt_id, downstream_request_id,
                    result_json, producer_revision, resource_revision,
                    observed_at, effect_revision, committed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    *secrets,
                    "0" * 64,
                    "receipt-orphan",
                    "request-orphan",
                    "{}",
                    "producer-orphan",
                    "resource-orphan",
                    "2026-07-19T00:00:00Z",
                    "effect-orphan",
                    1,
                ),
            )
        audit = self.runtime.audit_database()
        rendered = json.dumps(audit, ensure_ascii=False, sort_keys=True)
        self.assertFalse(audit["passed"])
        self.assertRegex(
            audit["semantic_errors"][0],
            r"^AUDIT_ORPHAN_DOWNSTREAM_RECEIPT\[status_[0-9a-f]{32}\]$",
        )
        for secret in secrets:
            self.assertNotIn(secret, rendered)

    def test_all_runtime_tables_are_strict(self) -> None:
        with self.runtime._connect() as connection:
            rows = connection.execute(
                "SELECT name, strict FROM pragma_table_list WHERE name NOT LIKE 'sqlite_%'"
            ).fetchall()
        self.assertEqual(
            {
                "runtime_metadata",
                "call_bindings",
                "operations",
                "outbox",
                "downstream_receipts",
                "local_receipts",
            },
            {row["name"] for row in rows},
        )
        self.assertTrue(all(row["strict"] == 1 for row in rows))

    def test_foreign_keys_are_enabled_on_each_connection(self) -> None:
        with self.runtime._connect() as connection:
            enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(1, enabled)

    def test_memory_database_is_rejected_for_multi_connection_project(self) -> None:
        with self.assertRaises(ValueError):
            persisted.PersistentToolRuntime(Path(":memory:"))

    def test_missing_parent_directory_is_rejected(self) -> None:
        missing = Path(self.temporary.name) / "missing" / "db.sqlite3"
        with self.assertRaises(ValueError):
            persisted.PersistentToolRuntime(missing)

    def test_invalid_busy_timeout_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            persisted.PersistentToolRuntime(self.database, busy_timeout_ms=0)

    def test_schema_version_mismatch_is_rejected_on_reopen(self) -> None:
        with self.runtime._connect() as connection:
            connection.execute(
                "UPDATE runtime_metadata SET metadata_value = 'future' "
                "WHERE metadata_key = 'schema_version'"
            )
        with self.assertRaises(persisted.PersistenceContractError):
            persisted.PersistentToolRuntime(self.database)

    def test_outbox_check_constraint_rejects_invalid_lease_shape(self) -> None:
        package = self.dispatch(failure="after_intent_commit")
        self.assertEqual("OUTCOME_UNKNOWN", code(package))
        with self.runtime._connect() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE outbox SET state = 'processing', lease_owner = NULL, "
                    "lease_until = NULL"
                )

    def test_intent_and_outbox_roll_back_together(self) -> None:
        with self.runtime._connect() as connection:
            connection.execute(
                """
                CREATE TRIGGER fail_outbox_insert
                BEFORE INSERT ON outbox
                BEGIN
                    SELECT RAISE(ABORT, 'injected outbox failure');
                END
                """
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.dispatch(failure="after_intent_commit")
        counts = self.runtime.counts()
        self.assertEqual(0, counts["operations"])
        self.assertEqual(0, counts["outbox"])
        self.assertEqual(0, counts["call_bindings"])

    def test_database_counts_start_at_zero(self) -> None:
        self.assertEqual(
            {
                "call_bindings": 0,
                "operations": 0,
                "outbox": 0,
                "downstream_receipts": 0,
                "local_receipts": 0,
            },
            self.runtime.counts(),
        )


class ToolResultV2CompatibilityTests(RuntimeTestCase):
    def test_request_digest_is_exact_v2_digest(self) -> None:
        package = self.dispatch()
        expected = tool_v2.request_digest(self.actor, self.call, self.spec)
        actual = package["protected_audit"]["binding"]["request_sha256"]
        self.assertEqual(expected, actual)

    def test_request_digest_excludes_idempotency_key(self) -> None:
        other = write_call(key="another-key", call_id="other-call", response_id="other-response")
        self.assertEqual(
            tool_v2.request_digest(self.actor, self.call, self.spec),
            tool_v2.request_digest(self.actor, other, self.spec),
        )

    def test_call_binding_still_binds_idempotency_key(self) -> None:
        package = self.dispatch()
        swapped = write_call(key="another-key")
        errors = tool_v2.validate_result(self.actor, swapped, self.spec, package)
        self.assertTrue(any("call_binding" in error for error in errors))

    def test_success_package_passes_v2_result_validation(self) -> None:
        package = self.dispatch()
        self.assertEqual([], tool_v2.validate_result(self.actor, self.call, self.spec, package))

    def test_unknown_package_passes_v2_result_validation(self) -> None:
        package = self.dispatch(failure="after_intent_commit")
        self.assertEqual([], tool_v2.validate_result(self.actor, self.call, self.spec, package))


class IdempotencyDispatchTests(RuntimeTestCase):
    def test_time_and_lease_overflow_fail_before_reservation(self) -> None:
        with self.assertRaisesRegex(ValueError, "UTC datetime"):
            self.runtime.dispatch(
                self.actor,
                self.call,
                approvals=self.approval(),
                now=persisted.MAX_PORTABLE_UNIX_SECONDS + 1,
            )
        with self.assertRaisesRegex(ValueError, r"now \+ lease_seconds"):
            self.runtime.dispatch(
                self.actor,
                self.call,
                approvals=self.approval(),
                now=persisted.MAX_PORTABLE_UNIX_SECONDS,
                lease_seconds=1,
            )
        self.assertEqual(0, self.runtime.counts()["operations"])
        safe_now = persisted.MAX_PORTABLE_UNIX_SECONDS - max(
            persisted.DEFAULT_LEASE_SECONDS,
            tool_v2.APPROVAL_TTL_SECONDS,
        )
        safe_approval = tool_v2.make_approval(
            self.actor, self.call, self.spec, "valid", safe_now
        )
        package = self.runtime.dispatch(
            self.actor,
            self.call,
            approvals=safe_approval,
            now=safe_now,
        )
        self.assertEqual("OK", code(package))

    def test_first_dispatch_is_fresh_and_durable(self) -> None:
        package = self.dispatch()
        self.assertEqual("OK", code(package))
        self.assertEqual("fresh", delivery(package))
        self.assertEqual(1, self.runtime.counts()["downstream_receipts"])

    def test_same_key_same_intent_replays_without_second_effect(self) -> None:
        first = self.dispatch()
        second = self.dispatch(approvals=())
        self.assertEqual("OK", code(first))
        self.assertEqual("local_replay", delivery(second))
        self.assertEqual(1, self.runtime.counts()["downstream_receipts"])

    def test_same_key_different_intent_conflicts(self) -> None:
        self.dispatch(failure="after_intent_commit")
        changed = write_call(reason="damaged", call_id="changed", response_id="changed-response")
        package = self.dispatch(changed)
        self.assertEqual("IDEMPOTENCY_CONFLICT", code(package))
        self.assertEqual(0, self.runtime.counts()["downstream_receipts"])

    def test_different_key_same_intent_is_a_new_operation(self) -> None:
        first = self.dispatch()
        second_call = write_call(key="persistent-key-2", call_id="call-2", response_id="response-2")
        second = self.dispatch(second_call)
        self.assertEqual("OK", code(first))
        self.assertEqual("OK", code(second))
        self.assertEqual(2, self.runtime.counts()["downstream_receipts"])

    def test_missing_key_is_rejected_before_reservation(self) -> None:
        package = self.dispatch(write_call(key=None), approvals=())
        self.assertEqual("IDEMPOTENCY_KEY_REQUIRED", code(package))
        self.assertEqual(0, self.runtime.counts()["operations"])

    def test_missing_approval_does_not_create_intent(self) -> None:
        package = self.dispatch(approvals=())
        self.assertEqual("APPROVAL_REQUIRED", code(package))
        self.assertEqual(0, self.runtime.counts()["operations"])

    def test_expired_approval_does_not_create_intent(self) -> None:
        package = self.dispatch(approvals=self.approval(mode="expired"))
        self.assertEqual("APPROVAL_INVALID", code(package))
        self.assertEqual(0, self.runtime.counts()["operations"])

    def test_approval_above_portable_time_boundary_does_not_create_intent(self) -> None:
        valid = self.approval()[0]
        overflow = replace(
            valid, expires_at=tool_v2.MAX_PORTABLE_UNIX_SECONDS + 1
        )
        package = self.dispatch(approvals=(overflow,))
        self.assertEqual("APPROVAL_INVALID", code(package))
        self.assertEqual(0, self.runtime.counts()["operations"])
        self.assertEqual(0, self.runtime.counts()["outbox"])

    def test_persisted_approval_records_bound_approver_identity(self) -> None:
        self.dispatch()
        with self.runtime._connect() as connection:
            row = connection.execute(
                "SELECT approver_id, approval_digest, first_provider, "
                "first_api_family, first_adapter_revision FROM operations"
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(tool_v2.DEFAULT_APPROVER_ID, row["approver_id"])
        self.assertEqual("openai", row["first_provider"])
        self.assertEqual("responses", row["first_api_family"])
        self.assertEqual("openai-responses-v1", row["first_adapter_revision"])
        self.assertEqual(
            tool_v2.approval_digest(
                self.actor,
                self.call,
                self.spec,
                approver_id=row["approver_id"],
            ),
            row["approval_digest"],
        )

    def test_approval_cannot_cross_provider_or_idempotency_key(self) -> None:
        approval = self.approval()
        changed_calls = (
            write_call(
                provider="anthropic",
                api_family="messages",
                adapter_revision="anthropic-messages-v1",
            ),
            write_call(key="other-persistent-key"),
        )
        for changed in changed_calls:
            with self.subTest(provider=changed.provider, key=changed.idempotency_key):
                package = self.runtime.dispatch(
                    self.actor,
                    changed,
                    approvals=approval,
                    now=self.now,
                )
                self.assertEqual("APPROVAL_INVALID", code(package))
        self.assertEqual(0, self.runtime.counts()["operations"])

    def test_unauthorized_resource_does_not_create_call_binding(self) -> None:
        package = self.dispatch(write_call(order_ref="ORDER-8"))
        self.assertEqual("NOT_FOUND", code(package))
        self.assertEqual(0, self.runtime.counts()["call_bindings"])

    def test_invalid_arguments_do_not_reach_database(self) -> None:
        invalid = write_call(reason="invented")
        package = self.dispatch(invalid, approvals=())
        self.assertEqual("INVALID_ARGUMENTS", code(package))
        self.assertEqual(0, self.runtime.counts()["operations"])

    def test_invalid_current_business_state_does_not_create_intent(self) -> None:
        self.runtime.contract.orders["ORDER-7"]["status"] = "refunded"
        package = self.dispatch()
        self.assertEqual("BUSINESS_RULE_VIOLATION", code(package))
        self.assertEqual(0, self.runtime.counts()["operations"])

    def test_call_identity_cannot_be_rebound_to_another_key(self) -> None:
        self.dispatch(failure="after_intent_commit")
        changed = write_call(key="other-key")
        package = self.dispatch(changed)
        self.assertEqual("CALL_ID_CONFLICT", code(package))

    def test_replay_survives_process_restart(self) -> None:
        self.dispatch()
        reopened = persisted.PersistentToolRuntime(self.database)
        package = reopened.dispatch(self.actor, self.call, approvals=(), now=self.now + 1)
        self.assertEqual("local_replay", delivery(package))
        self.assertEqual(1, reopened.counts()["downstream_receipts"])

    def test_replay_cannot_cross_the_approved_provider_context(self) -> None:
        self.dispatch()
        changed = replace(
            self.call,
            provider="anthropic",
            api_family="messages",
            response_id="response-persistent-anthropic",
            adapter_revision="anthropic-messages-v1",
        )
        package = self.runtime.dispatch(
            self.actor, changed, approvals=(), now=self.now + 1
        )
        self.assertEqual("IDEMPOTENCY_CONFLICT", code(package))
        self.assertEqual(1, self.runtime.counts()["downstream_receipts"])

    def test_returned_result_is_a_defensive_projection(self) -> None:
        first = self.dispatch()
        first["model_result"]["data"]["reason"] = "tampered"
        replay = self.dispatch(approvals=())
        self.assertEqual("duplicate", replay["model_result"]["data"]["reason"])

    def test_replay_rechecks_current_authorization(self) -> None:
        allowed = {"ORDER-7"}
        runtime = persisted.PersistentToolRuntime(
            self.database,
            authorization_resolver=lambda actor, order_ref: order_ref in allowed,
        )
        first = runtime.dispatch(
            self.actor,
            self.call,
            approvals=self.approval(),
            now=self.now,
        )
        self.assertEqual("OK", code(first))
        allowed.clear()
        replay = runtime.dispatch(self.actor, self.call, approvals=(), now=self.now + 1)
        self.assertEqual("NOT_FOUND", code(replay))


class CrashAndReconciliationTests(RuntimeTestCase):
    def test_worker_uses_persisted_provider_context_for_approval_evidence(self) -> None:
        call = write_call(
            call_id="call-anthropic",
            operation_id="operation-anthropic",
            response_id="response-anthropic",
            provider="anthropic",
            api_family="messages",
            adapter_revision="anthropic-messages-v1",
        )
        spec = self.runtime.contract.registry[call.name]
        blocked = self.runtime.dispatch(
            self.actor,
            call,
            approvals=tool_v2.make_approval(self.actor, call, spec, "valid", self.now),
            now=self.now,
            failure="after_intent_commit",
        )
        self.assertEqual("OUTCOME_UNKNOWN", code(blocked))
        with self.runtime._connect() as connection:
            row = connection.execute(
                "SELECT first_provider, first_api_family, first_adapter_revision "
                "FROM operations"
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(
            ("anthropic", "messages", "anthropic-messages-v1"),
            (
                row["first_provider"],
                row["first_api_family"],
                row["first_adapter_revision"],
            ),
        )
        self.assertEqual(
            "succeeded",
            self.runtime.process_operation(
                status_ref(blocked), worker_id="anthropic-worker", now=self.now + 1
            ),
        )

    def test_default_persistence_policy_does_not_trust_presented_role_snapshot(self) -> None:
        admin = principal("admin-1", roles=("support_admin",))
        call = write_call(
            order_ref="ORDER-8",
            call_id="call-admin-default",
            operation_id="operation-admin-default",
            response_id="response-admin-default",
        )
        spec = self.runtime.contract.registry[call.name]
        package = self.runtime.dispatch(
            admin,
            call,
            approvals=tool_v2.make_approval(admin, call, spec, "valid", self.now),
            now=self.now,
        )
        self.assertEqual("NOT_FOUND", code(package))
        self.assertEqual(0, self.runtime.counts()["operations"])

    def test_current_principal_resolver_allows_admin_write_and_worker_delivery(self) -> None:
        principals = {
            ("tenant-a", "admin-1"): principal("admin-1", roles=("support_admin",))
        }
        runtime = persisted.PersistentToolRuntime(
            self.database,
            principal_resolver=lambda tenant_id, subject_id: principals.get(
                (tenant_id, subject_id)
            ),
        )
        admin = principal("admin-1")
        call = write_call(
            order_ref="ORDER-8",
            call_id="call-admin-current",
            operation_id="operation-admin-current",
            response_id="response-admin-current",
        )
        spec = runtime.contract.registry[call.name]
        package = runtime.dispatch(
            admin,
            call,
            approvals=tool_v2.make_approval(admin, call, spec, "valid", self.now),
            now=self.now,
        )
        self.assertEqual("OK", code(package))
        self.assertEqual(1, runtime.counts()["downstream_receipts"])

    def test_reservation_rechecks_current_principal_before_intent_commit(self) -> None:
        lookups: list[tuple[str, str]] = []

        def resolve(tenant_id: str, subject_id: str) -> tool_v2.Principal:
            lookups.append((tenant_id, subject_id))
            roles = ("support_admin",) if len(lookups) == 1 else ()
            return principal(subject_id, tenant_id, roles)

        runtime = persisted.PersistentToolRuntime(
            self.database, principal_resolver=resolve
        )
        admin = principal("admin-1")
        call = write_call(
            order_ref="ORDER-8",
            call_id="call-admin-reservation-revoked",
            operation_id="operation-admin-reservation-revoked",
            response_id="response-admin-reservation-revoked",
        )
        spec = runtime.contract.registry[call.name]
        package = runtime.dispatch(
            admin,
            call,
            approvals=tool_v2.make_approval(admin, call, spec, "valid", self.now),
            now=self.now,
        )
        self.assertEqual("NOT_FOUND", code(package))
        self.assertEqual(2, len(lookups))
        self.assertEqual(0, runtime.counts()["operations"])

    def test_worker_rechecks_current_principal_roles_before_delivery(self) -> None:
        principals = {
            ("tenant-a", "admin-1"): principal("admin-1", roles=("support_admin",))
        }
        runtime = persisted.PersistentToolRuntime(
            self.database,
            principal_resolver=lambda tenant_id, subject_id: principals.get(
                (tenant_id, subject_id)
            ),
        )
        admin = principal("admin-1")
        call = write_call(
            order_ref="ORDER-8",
            call_id="call-admin-revoked",
            operation_id="operation-admin-revoked",
            response_id="response-admin-revoked",
        )
        spec = runtime.contract.registry[call.name]
        blocked = runtime.dispatch(
            admin,
            call,
            approvals=tool_v2.make_approval(admin, call, spec, "valid", self.now),
            now=self.now,
            failure="after_intent_commit",
        )
        principals[("tenant-a", "admin-1")] = principal("admin-1")
        outcome = runtime.process_operation(
            status_ref(blocked), worker_id="worker-revoked", now=self.now + 1
        )
        self.assertEqual("authorization_denied", outcome)
        self.assertEqual(0, runtime.counts()["downstream_receipts"])

    def test_intent_commit_returns_unknown_without_downstream_effect(self) -> None:
        package = self.dispatch(failure="after_intent_commit")
        self.assertEqual("OUTCOME_UNKNOWN", code(package))
        self.assertEqual(1, self.runtime.counts()["operations"])
        self.assertEqual(0, self.runtime.counts()["downstream_receipts"])

    def test_repeat_dispatch_does_not_implicitly_process_unknown(self) -> None:
        first = self.dispatch(failure="after_intent_commit")
        second = self.dispatch(approvals=())
        self.assertEqual(status_ref(first), status_ref(second))
        self.assertEqual("OUTCOME_UNKNOWN", code(second))
        self.assertEqual(0, self.runtime.counts()["downstream_receipts"])

    def test_status_query_without_receipt_stays_unknown(self) -> None:
        blocked = self.dispatch(failure="after_intent_commit")
        package = self.runtime.query_operation_status(
            self.actor,
            self.status_call(status_ref(blocked)),
            status_ref=status_ref(blocked),
            expected_request_sha256=tool_v2.request_digest(self.actor, self.call, self.spec),
            now=self.now + 1,
        )
        self.assertEqual("OUTCOME_UNKNOWN", code(package))

    def test_status_query_call_identity_cannot_be_reused_for_dispatch(self) -> None:
        blocked = self.dispatch(failure="after_intent_commit")
        reference = status_ref(blocked)
        query_call = self.status_call(reference)
        package = self.runtime.query_operation_status(
            self.actor,
            query_call,
            status_ref=reference,
            expected_request_sha256=tool_v2.request_digest(
                self.actor, query_call, self.spec
            ),
            now=self.now + 1,
        )
        self.assertEqual("OUTCOME_UNKNOWN", code(package))

        approval = tool_v2.make_approval(
            self.actor, query_call, self.spec, "valid", self.now + 1
        )
        reused = self.runtime.dispatch(
            self.actor,
            query_call,
            approvals=approval,
            now=self.now + 2,
        )
        self.assertEqual("CALL_ID_CONFLICT", code(reused))

    def test_worker_can_finish_pending_intent_then_status_query_reconciles(self) -> None:
        blocked = self.dispatch(failure="after_intent_commit")
        outcome = self.runtime.process_operation(
            status_ref(blocked), worker_id="recovery-worker", now=self.now + 1
        )
        self.assertEqual("succeeded", outcome)
        package = self.runtime.query_operation_status(
            self.actor,
            self.status_call(status_ref(blocked)),
            status_ref=status_ref(blocked),
            expected_request_sha256=tool_v2.request_digest(self.actor, self.call, self.spec),
            now=self.now + 2,
        )
        self.assertEqual("receipt_reconciled", delivery(package))

    def test_active_lease_blocks_second_worker(self) -> None:
        blocked = self.dispatch(failure="after_intent_commit")
        first = self.runtime.claim_operation(
            status_ref(blocked), worker_id="worker-a", now=self.now, lease_seconds=10
        )
        second = self.runtime.claim_operation(
            status_ref(blocked), worker_id="worker-b", now=self.now + 9, lease_seconds=10
        )
        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_expired_lease_can_be_reclaimed(self) -> None:
        blocked = self.dispatch(failure="after_intent_commit")
        first = self.runtime.claim_operation(
            status_ref(blocked), worker_id="worker-a", now=self.now, lease_seconds=10
        )
        second = self.runtime.claim_operation(
            status_ref(blocked), worker_id="worker-b", now=self.now + 10, lease_seconds=10
        )
        self.assertEqual(1, first.attempt_count if first is not None else None)
        self.assertEqual(2, second.attempt_count if second is not None else None)

    def test_crash_after_claim_is_recoverable_after_lease_expiry(self) -> None:
        blocked = self.dispatch(failure="after_intent_commit")
        outcome = self.runtime.process_operation(
            status_ref(blocked),
            worker_id="crashing-worker",
            now=self.now,
            lease_seconds=5,
            failure="after_claim",
        )
        self.assertEqual("crashed_after_claim", outcome)
        recovered = self.runtime.process_operation(
            status_ref(blocked), worker_id="recovery-worker", now=self.now + 5
        )
        self.assertEqual("succeeded", recovered)

    def test_worker_rechecks_current_authorization_before_downstream_effect(self) -> None:
        allowed = {"ORDER-7"}
        runtime = persisted.PersistentToolRuntime(
            self.database,
            authorization_resolver=lambda actor, order_ref: order_ref in allowed,
        )
        blocked = runtime.dispatch(
            self.actor,
            self.call,
            approvals=self.approval(),
            now=self.now,
            failure="after_intent_commit",
        )
        allowed.clear()
        denied = runtime.process_operation(
            status_ref(blocked),
            worker_id="worker-denied",
            now=self.now + 1,
            lease_seconds=5,
        )
        self.assertEqual("authorization_denied", denied)
        self.assertEqual(0, runtime.counts()["downstream_receipts"])
        allowed.add("ORDER-7")
        recovered = runtime.process_operation(
            status_ref(blocked), worker_id="worker-restored", now=self.now + 6
        )
        self.assertEqual("succeeded", recovered)
        self.assertEqual(1, runtime.counts()["downstream_receipts"])

    def test_worker_rechecks_current_business_state_before_downstream_effect(self) -> None:
        blocked = self.dispatch(failure="after_intent_commit")
        self.runtime.contract.orders["ORDER-7"]["status"] = "refunded"
        denied = self.runtime.process_operation(
            status_ref(blocked),
            worker_id="worker-business-denied",
            now=self.now + 1,
            lease_seconds=5,
        )
        self.assertEqual("business_rule_denied", denied)
        self.assertEqual(0, self.runtime.counts()["downstream_receipts"])

    def test_worker_rejects_contract_revision_drift_before_effect(self) -> None:
        blocked = self.dispatch(failure="after_intent_commit")
        self.runtime.contract.registry[self.call.name] = replace(
            self.spec, effect_revision="create-refund-draft-v2"
        )
        with self.assertRaises(persisted.PersistenceContractError):
            self.runtime.process_operation(
                status_ref(blocked), worker_id="worker-new-contract", now=self.now + 1
            )
        self.assertEqual(0, self.runtime.counts()["downstream_receipts"])

    def test_downstream_commit_before_local_receipt_stays_unknown(self) -> None:
        blocked = self.dispatch(failure="after_downstream_commit")
        self.assertEqual("OUTCOME_UNKNOWN", code(blocked))
        counts = self.runtime.counts()
        self.assertEqual(1, counts["downstream_receipts"])
        self.assertEqual(0, counts["local_receipts"])
        replay = self.dispatch(approvals=())
        self.assertEqual("OUTCOME_UNKNOWN", code(replay))

    def test_explicit_query_reconciles_downstream_receipt(self) -> None:
        blocked = self.dispatch(failure="after_downstream_commit")
        package = self.runtime.query_operation_status(
            self.actor,
            self.status_call(status_ref(blocked)),
            status_ref=status_ref(blocked),
            expected_request_sha256=tool_v2.request_digest(self.actor, self.call, self.spec),
            now=self.now + 1,
        )
        self.assertEqual("OK", code(package))
        self.assertEqual("receipt_reconciled", delivery(package))
        counts = self.runtime.counts()
        self.assertEqual(1, counts["local_receipts"])
        with self.runtime._connect() as connection:
            outbox_state = connection.execute("SELECT state FROM outbox").fetchone()[0]
        self.assertEqual("delivered", outbox_state)

    def test_receipt_ledger_and_outbox_reconciliation_roll_back_together(self) -> None:
        blocked = self.dispatch(failure="after_downstream_commit")
        with self.runtime._connect() as connection:
            connection.execute(
                """
                CREATE TRIGGER fail_outbox_delivery
                BEFORE UPDATE OF state ON outbox
                WHEN NEW.state = 'delivered'
                BEGIN
                    SELECT RAISE(ABORT, 'injected delivery failure');
                END
                """
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.runtime.query_operation_status(
                self.actor,
                self.status_call(status_ref(blocked)),
                status_ref=status_ref(blocked),
                expected_request_sha256=tool_v2.request_digest(self.actor, self.call, self.spec),
                now=self.now + 1,
            )
        self.assertEqual(0, self.runtime.counts()["local_receipts"])
        with self.runtime._connect() as connection:
            operation_state = connection.execute("SELECT state FROM operations").fetchone()[0]
            outbox_state = connection.execute("SELECT state FROM outbox").fetchone()[0]
        self.assertEqual("processing", operation_state)
        self.assertEqual("processing", outbox_state)

    def test_dispatch_after_explicit_reconciliation_is_local_replay(self) -> None:
        blocked = self.dispatch(failure="after_downstream_commit")
        self.runtime.query_operation_status(
            self.actor,
            self.status_call(status_ref(blocked)),
            status_ref=status_ref(blocked),
            expected_request_sha256=tool_v2.request_digest(self.actor, self.call, self.spec),
            now=self.now + 1,
        )
        replay = self.dispatch(approvals=())
        self.assertEqual("local_replay", delivery(replay))
        self.assertEqual(1, self.runtime.counts()["downstream_receipts"])

    def test_wrong_expected_digest_is_status_conflict(self) -> None:
        blocked = self.dispatch(failure="after_downstream_commit")
        package = self.runtime.query_operation_status(
            self.actor,
            self.status_call(status_ref(blocked)),
            status_ref=status_ref(blocked),
            expected_request_sha256="0" * 64,
            now=self.now + 1,
        )
        self.assertEqual("STATUS_CONFLICT", code(package))

    def test_unknown_status_ref_is_not_found(self) -> None:
        unknown_ref = "status_" + "0" * 32
        package = self.runtime.query_operation_status(
            self.actor,
            self.status_call(unknown_ref),
            status_ref=unknown_ref,
            expected_request_sha256=tool_v2.request_digest(self.actor, self.call, self.spec),
            now=self.now,
        )
        self.assertEqual("NOT_FOUND", code(package))

    def test_changed_key_cannot_query_status(self) -> None:
        blocked = self.dispatch(failure="after_downstream_commit")
        changed = write_call(key="other-key", call_id="other-call", response_id="other-response")
        package = self.runtime.query_operation_status(
            self.actor,
            self.status_call(status_ref(blocked), changed),
            status_ref=status_ref(blocked),
            expected_request_sha256=tool_v2.request_digest(self.actor, changed, self.spec),
            now=self.now + 1,
        )
        self.assertEqual("STATUS_CONFLICT", code(package))

    def test_status_query_cannot_cross_approved_provider_context(self) -> None:
        blocked = self.dispatch(failure="after_downstream_commit")
        changed = replace(
            self.call,
            provider="anthropic",
            api_family="messages",
            response_id="response-status-anthropic",
            adapter_revision="anthropic-messages-v1",
        )
        package = self.runtime.query_operation_status(
            self.actor,
            self.status_call(status_ref(blocked), changed),
            status_ref=status_ref(blocked),
            expected_request_sha256=tool_v2.request_digest(
                self.actor, changed, self.spec
            ),
            now=self.now + 1,
        )
        self.assertEqual("STATUS_CONFLICT", code(package))

    def test_status_query_rechecks_current_authorization(self) -> None:
        allowed = {"ORDER-7"}
        runtime = persisted.PersistentToolRuntime(
            self.database,
            authorization_resolver=lambda actor, order_ref: order_ref in allowed,
        )
        blocked = runtime.dispatch(
            self.actor,
            self.call,
            approvals=self.approval(),
            now=self.now,
            failure="after_downstream_commit",
        )
        allowed.clear()
        package = runtime.query_operation_status(
            self.actor,
            self.status_call(status_ref(blocked)),
            status_ref=status_ref(blocked),
            expected_request_sha256=tool_v2.request_digest(self.actor, self.call, self.spec),
            now=self.now + 1,
        )
        self.assertEqual("NOT_FOUND", code(package))


class StoredStateTamperTests(RuntimeTestCase):
    def test_approval_evidence_is_recomputed_before_worker_effect(self) -> None:
        blocked = self.dispatch(failure="after_intent_commit")
        with self.runtime._connect() as connection:
            connection.execute(
                "UPDATE operations SET approval_digest = ?", ("0" * 64,)
            )
        audit = self.runtime.audit_database()
        self.assertFalse(audit["passed"])
        self.assertTrue(any("approval" in error for error in audit["semantic_errors"]))
        with self.assertRaises(persisted.PersistenceContractError):
            self.runtime.process_operation(
                status_ref(blocked), worker_id="worker", now=self.now + 1
            )
        self.assertEqual(0, self.runtime.counts()["downstream_receipts"])

    def test_persisted_approval_recomputation_binds_provider_api_and_adapter(self) -> None:
        call = write_call(
            call_id="call-anthropic-approval",
            operation_id="operation-anthropic-approval",
            response_id="response-anthropic-approval",
            provider="anthropic",
            api_family="messages",
            adapter_revision="anthropic-messages-v1",
        )
        spec = self.runtime.contract.registry[call.name]
        blocked = self.runtime.dispatch(
            self.actor,
            call,
            approvals=tool_v2.make_approval(self.actor, call, spec, "valid", self.now),
            now=self.now,
            failure="after_intent_commit",
        )
        with self.runtime._connect() as connection:
            connection.execute(
                "UPDATE operations SET first_provider = ?, first_api_family = ?, "
                "first_adapter_revision = ?",
                ("openai", "responses", "openai-responses-v1"),
            )
        audit = self.runtime.audit_database()
        self.assertFalse(audit["passed"])
        self.assertTrue(any("approval" in error for error in audit["semantic_errors"]))
        with self.assertRaises(persisted.PersistenceContractError):
            self.runtime.process_operation(
                status_ref(blocked), worker_id="provider-tamper-worker", now=self.now + 1
            )
        self.assertEqual(0, self.runtime.counts()["downstream_receipts"])

    def test_semantic_audit_detects_valid_shape_digest_tamper(self) -> None:
        self.dispatch(failure="after_intent_commit")
        with self.runtime._connect() as connection:
            connection.execute(
                "UPDATE operations SET request_sha256 = ?", ("0" * 64,)
            )
        audit = self.runtime.audit_database()
        self.assertFalse(audit["passed"])
        self.assertTrue(any("request/contract" in error for error in audit["semantic_errors"]))

    def test_semantic_audit_detects_outbox_binding_tamper(self) -> None:
        self.dispatch(failure="after_intent_commit")
        with self.runtime._connect() as connection:
            payload = json.loads(connection.execute("SELECT payload_json FROM outbox").fetchone()[0])
            payload["tool"] = "other"
            connection.execute(
                "UPDATE outbox SET payload_json = ?",
                (tool_v2._canonical_json(payload),),
            )
        audit = self.runtime.audit_database()
        self.assertFalse(audit["passed"])
        self.assertTrue(any("outbox" in error for error in audit["semantic_errors"]))

    def test_semantic_audit_rejects_nested_stored_json_without_crashing(self) -> None:
        self.dispatch(failure="after_intent_commit")
        nested = deeply_nested_json()
        self.assertLess(len(nested.encode("utf-8")), persisted.MAX_STORED_JSON_BYTES)
        with self.runtime._connect() as connection:
            connection.execute("UPDATE outbox SET payload_json = ?", (nested,))
        audit = self.runtime.audit_database()
        self.assertFalse(audit["passed"])
        self.assertTrue(any("nesting" in error for error in audit["semantic_errors"]))

    def test_noncanonical_outbox_json_is_rejected(self) -> None:
        blocked = self.dispatch(failure="after_intent_commit")
        with self.runtime._connect() as connection:
            payload = connection.execute("SELECT payload_json FROM outbox").fetchone()[0]
            value = json.loads(payload)
            connection.execute(
                "UPDATE outbox SET payload_json = ?",
                (json.dumps(value, ensure_ascii=False, indent=2),),
            )
        with self.assertRaises(persisted.PersistenceContractError):
            self.runtime.claim_operation(
                status_ref(blocked), worker_id="worker", now=self.now
            )

    def test_duplicate_key_in_stored_json_is_rejected(self) -> None:
        blocked = self.dispatch(failure="after_intent_commit")
        with self.runtime._connect() as connection:
            connection.execute(
                "UPDATE outbox SET payload_json = ?",
                (
                    '{"schema_version":"tool-outbox-event-v1",'
                    '"schema_version":"tool-outbox-event-v1",'
                    '"operation_pk":1,"request_sha256":"' + "0" * 64 + '","tool":"x"}',
                ),
            )
        with self.assertRaises(persisted.PersistenceContractError):
            self.runtime.claim_operation(
                status_ref(blocked), worker_id="worker", now=self.now
            )

    def test_tampered_downstream_digest_is_rejected(self) -> None:
        blocked = self.dispatch(failure="after_downstream_commit")
        with self.runtime._connect() as connection:
            connection.execute(
                "UPDATE downstream_receipts SET request_sha256 = ?", ("0" * 64,)
            )
        with self.assertRaises(persisted.PersistenceContractError):
            self.runtime.query_operation_status(
                self.actor,
                self.status_call(status_ref(blocked)),
                status_ref=status_ref(blocked),
                expected_request_sha256=tool_v2.request_digest(self.actor, self.call, self.spec),
                now=self.now + 1,
            )

    def test_tampered_downstream_output_is_rejected(self) -> None:
        blocked = self.dispatch(failure="after_downstream_commit")
        with self.runtime._connect() as connection:
            connection.execute(
                "UPDATE downstream_receipts SET result_json = ?",
                ('{"draft_id":"DRAFT-1","order_ref":"ORDER-7","reason":"damaged"}',),
            )
        with self.assertRaises(persisted.PersistenceContractError):
            self.runtime.query_operation_status(
                self.actor,
                self.status_call(status_ref(blocked)),
                status_ref=status_ref(blocked),
                expected_request_sha256=tool_v2.request_digest(self.actor, self.call, self.spec),
                now=self.now + 1,
            )

    def test_tampered_local_output_is_rejected_on_replay(self) -> None:
        self.dispatch()
        with self.runtime._connect() as connection:
            connection.execute(
                "UPDATE local_receipts SET result_json = ?",
                ('{"draft_id":"DRAFT-1","order_ref":"ORDER-7","reason":"damaged"}',),
            )
        with self.assertRaises(persisted.PersistenceContractError):
            self.dispatch(approvals=())


class ConcurrentConnectionTests(RuntimeTestCase):
    def test_concurrent_same_intent_creates_one_ledger_and_outbox(self) -> None:
        workers = 8
        barrier = threading.Barrier(workers)

        def reserve(index: int) -> str:
            runtime = persisted.PersistentToolRuntime(self.database)
            barrier.wait()
            package = runtime.dispatch(
                self.actor,
                self.call,
                approvals=self.approval(),
                now=self.now + index,
                failure="after_intent_commit",
            )
            return code(package)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(reserve, range(workers)))
        self.assertEqual(["OUTCOME_UNKNOWN"] * workers, results)
        counts = self.runtime.counts()
        self.assertEqual(1, counts["operations"])
        self.assertEqual(1, counts["outbox"])
        self.assertEqual(0, counts["downstream_receipts"])

    def test_concurrent_different_intents_yield_one_conflict(self) -> None:
        barrier = threading.Barrier(2)
        calls = (
            write_call(reason="duplicate", call_id="call-a", response_id="response-a"),
            write_call(reason="damaged", call_id="call-b", response_id="response-b"),
        )

        def reserve(call: tool_v2.ToolCall) -> str:
            runtime = persisted.PersistentToolRuntime(self.database)
            spec = runtime.contract.registry[call.name]
            approvals = tool_v2.make_approval(self.actor, call, spec, "valid", self.now)
            barrier.wait()
            package = runtime.dispatch(
                self.actor,
                call,
                approvals=approvals,
                now=self.now,
                failure="after_intent_commit",
            )
            return code(package)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(reserve, calls))
        self.assertEqual({"OUTCOME_UNKNOWN", "IDEMPOTENCY_CONFLICT"}, set(results))
        self.assertEqual(1, self.runtime.counts()["operations"])

    def test_concurrent_workers_commit_one_downstream_effect(self) -> None:
        blocked = self.dispatch(failure="after_intent_commit")
        reference = status_ref(blocked)
        workers = 8
        barrier = threading.Barrier(workers)

        def process(index: int) -> str:
            runtime = persisted.PersistentToolRuntime(self.database)
            barrier.wait()
            return runtime.process_operation(
                reference,
                worker_id=f"worker-{index}",
                now=self.now + 1,
            )

        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(process, range(workers)))
        self.assertIn("succeeded", results)
        counts = self.runtime.counts()
        self.assertEqual(1, counts["downstream_receipts"])
        self.assertEqual(1, counts["local_receipts"])

    def test_two_connections_observe_persisted_replay(self) -> None:
        first_runtime = persisted.PersistentToolRuntime(self.database)
        second_runtime = persisted.PersistentToolRuntime(self.database)
        first = first_runtime.dispatch(
            self.actor,
            self.call,
            approvals=self.approval(),
            now=self.now,
        )
        second = second_runtime.dispatch(
            self.actor, self.call, approvals=(), now=self.now + 1
        )
        self.assertEqual("fresh", delivery(first))
        self.assertEqual("local_replay", delivery(second))
        self.assertEqual(1, second_runtime.counts()["downstream_receipts"])


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary.name) / "cli.sqlite3"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(
        self,
        *arguments: str,
        database: Path | None = None,
        fixture: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                "-W",
                "error",
                str(SCRIPT_PATH),
                "--db",
                str(self.database if database is None else database),
                "--fixture",
                str(FIXTURE_PATH if fixture is None else fixture),
                *arguments,
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_dispatch_cli_reports_pass(self) -> None:
        result = self.run_cli("dispatch")
        self.assertEqual(0, result.returncode, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual("PASS", summary["gate"])
        self.assertEqual("fresh", summary["delivery"])

    def test_crash_cli_blocks_until_explicit_status_query(self) -> None:
        blocked = self.run_cli("dispatch", "--failure", "after_downstream_commit")
        self.assertEqual(1, blocked.returncode, blocked.stderr)
        blocked_summary = json.loads(blocked.stdout)
        self.assertEqual("BLOCK", blocked_summary["gate"])
        self.assertEqual("OUTCOME_UNKNOWN", blocked_summary["code"])
        reconciled = self.run_cli(
            "status", "--status-ref", blocked_summary["status_ref"]
        )
        self.assertEqual(0, reconciled.returncode, reconciled.stderr)
        self.assertEqual("PASS", json.loads(reconciled.stdout)["gate"])

    def test_audit_cli_reports_pass(self) -> None:
        result = self.run_cli("audit")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("PASS", json.loads(result.stdout)["gate"])

    def test_missing_fixture_cli_uses_path_free_error_code(self) -> None:
        secret_path = Path(self.temporary.name) / "private-account" / "fixture.json"
        result = self.run_cli("dispatch", fixture=secret_path)
        self.assertEqual(2, result.returncode)
        summary = json.loads(result.stderr)
        self.assertEqual("BLOCK", summary["gate"])
        self.assertEqual("FIXTURE_IO_ERROR", summary["error"]["code"])
        self.assertNotIn(str(secret_path), result.stderr)
        self.assertNotIn("private-account", result.stderr)

    def test_nested_fixture_cli_uses_controlled_error(self) -> None:
        fixture = Path(self.temporary.name) / "nested.json"
        payload = deeply_nested_json()
        self.assertLess(len(payload.encode("utf-8")), persisted.MAX_FIXTURE_BYTES)
        fixture.write_text(payload, encoding="utf-8")
        result = self.run_cli("dispatch", fixture=fixture)
        self.assertEqual(2, result.returncode)
        summary = json.loads(result.stderr)
        self.assertEqual("BLOCK", summary["gate"])
        self.assertEqual("FIXTURE_CONTRACT_ERROR", summary["error"]["code"])
        self.assertNotIn("Traceback", result.stderr)

    def test_database_open_cli_uses_path_free_error_code(self) -> None:
        blocking_file = Path(self.temporary.name) / "private-database-parent"
        blocking_file.write_text("not a directory", encoding="utf-8")
        secret_path = blocking_file / "runtime.sqlite3"
        result = self.run_cli("audit", database=secret_path)
        self.assertEqual(2, result.returncode)
        summary = json.loads(result.stderr)
        self.assertEqual("BLOCK", summary["gate"])
        self.assertEqual("SQLITE_ERROR", summary["error"]["code"])
        self.assertNotIn(str(secret_path), result.stderr)
        self.assertNotIn("private-database-parent", result.stderr)


if __name__ == "__main__":
    unittest.main()

