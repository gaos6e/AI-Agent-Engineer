"""Tests for the single-process teaching vector store."""

from __future__ import annotations

from dataclasses import replace
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import toy_vector_store as lab


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "toy_vector_store.py"


def make_contract(**changes: object) -> lab.StoreContract:
    values = {
        "space_id": "test-space",
        "model": "hand-authored",
        "embedding_revision": "embed-r1",
        "dimension": 2,
        "metric": "cosine",
        "normalized": True,
        "dtype": "float32",
    }
    values.update(changes)
    return lab.StoreContract(**values)


def make_payload(
    *,
    tenant_id: str = "alpha",
    document_id: str = "doc-1",
    source_revision: str = "source-r1",
    text: str = "example text",
    acl: tuple[str, ...] = ("employees",),
    status: str = "published",
    embedding_revision: str = "embed-r1",
) -> lab.Payload:
    return lab.Payload(
        tenant_id=tenant_id,
        document_id=document_id,
        source_revision=source_revision,
        embedding_revision=embedding_revision,
        content_sha256=lab._digest(lab._normalise_text(text)),
        acl=tuple(sorted(acl)),
        status=status,
    )


class TemporaryStoreMixin:
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "store.json"
        self.contract = make_contract()

    def store(self) -> lab.ToyVectorStore:
        return lab.ToyVectorStore(self.path, self.contract)

    def write_raw(self, value: str) -> None:
        self.path.write_text(value, encoding="utf-8", newline="\n")

    def mutate_state(self, mutator: object) -> None:
        value = json.loads(self.path.read_text(encoding="utf-8"))
        mutator(value)
        self.path.write_text(
            json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )


class ContractAndMathTests(unittest.TestCase):
    def test_valid_contract_has_stable_signature(self) -> None:
        first = make_contract()
        second = make_contract()
        first.validate()
        self.assertEqual(first.signature(), second.signature())
        self.assertNotEqual(first.signature(), make_contract(metric="dot").signature())

    def test_contract_rejects_bad_dimension_metric_normalized_and_dtype(self) -> None:
        invalid = [
            make_contract(dimension=0),
            make_contract(dimension=True),
            make_contract(metric="manhattan"),
            make_contract(normalized="yes"),
            make_contract(dtype="int8"),
        ]
        for contract in invalid:
            with self.subTest(contract=contract), self.assertRaises(lab.StoreError):
                contract.validate()

    def test_payload_requires_contract_revision_hash_sorted_acl_and_status(self) -> None:
        contract = make_contract()
        invalid = [
            make_payload(embedding_revision="other"),
            replace(make_payload(), content_sha256="bad"),
            replace(make_payload(), acl=("z", "a")),
            replace(make_payload(), acl=("a", "a")),
            make_payload(status="deleted"),
        ]
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(lab.StoreError):
                payload.validate(contract)

    def test_similarity_metrics(self) -> None:
        self.assertAlmostEqual(
            lab.similarity((2.0, 0.0), (3.0, 0.0), metric="cosine"), 1.0
        )
        self.assertEqual(
            lab.similarity((2.0, 0.0), (3.0, 0.0), metric="dot"), 6.0
        )
        self.assertEqual(
            lab.similarity((1.0, 1.0), (4.0, 5.0), metric="euclidean"), -5.0
        )

    def test_similarity_rejects_bad_metric_dimension_and_nonfinite(self) -> None:
        cases = [
            ((1.0,), (1.0,), "unknown"),
            ((1.0,), (1.0, 2.0), "cosine"),
            ((math.nan, 1.0), (1.0, 2.0), "dot"),
            ((0.0, 0.0), (1.0, 0.0), "cosine"),
        ]
        for left, right, metric in cases:
            with self.subTest(metric=metric), self.assertRaises(lab.StoreError):
                lab.similarity(left, right, metric=metric)


class PersistenceTests(TemporaryStoreMixin, unittest.TestCase):
    def test_new_store_starts_empty_without_creating_file(self) -> None:
        store = self.store()
        self.assertEqual(store.store_revision, 0)
        self.assertEqual(store.points, {})
        self.assertFalse(self.path.exists())

    def test_upsert_persists_and_round_trips_strict_state(self) -> None:
        store = self.store()
        self.assertEqual(
            store.upsert("p1", (1.0, 0.0), make_payload()), "created"
        )
        loaded = self.store()
        self.assertEqual(loaded.store_revision, 1)
        self.assertEqual(list(loaded.points), ["p1"])
        self.assertEqual(loaded.points["p1"].payload.document_id, "doc-1")
        self.assertEqual(loaded.contract, self.contract)

    def test_duplicate_json_key_and_nonfinite_number_are_rejected(self) -> None:
        self.write_raw('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(lab.StoreError, "duplicate JSON field"):
            self.store()
        self.write_raw('{"schema_version":NaN}')
        with self.assertRaisesRegex(lab.StoreError, "non-finite JSON number"):
            self.store()

    def test_exact_fields_schema_version_and_revision_are_checked(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload())
        mutations = [
            (lambda value: value.__setitem__("extra", True), "fields must match exactly"),
            (lambda value: value.__setitem__("schema_version", 99), "schema_version"),
            (lambda value: value.__setitem__("store_revision", True), "store_revision"),
        ]
        original = self.path.read_text(encoding="utf-8")
        for mutator, message in mutations:
            self.path.write_text(original, encoding="utf-8", newline="\n")
            self.mutate_state(mutator)
            with self.subTest(message=message), self.assertRaisesRegex(
                lab.StoreError, message
            ):
                self.store()

    def test_schema_v1_without_delete_fence_is_not_silently_migrated(self) -> None:
        legacy = {
            "schema_version": 1,
            "store_revision": 2,
            "contract": {
                "space_id": "test-space",
                "model": "hand-authored",
                "embedding_revision": "embed-r1",
                "dimension": 2,
                "metric": "cosine",
                "normalized": True,
                "dtype": "float32",
            },
            "points": [],
            "tombstones": [
                {
                    "point_id": "p1",
                    "tenant_id": "alpha",
                    "deleted_at_revision": 2,
                }
            ],
        }
        self.write_raw(
            json.dumps(legacy, ensure_ascii=False, allow_nan=False) + "\n"
        )
        with self.assertRaisesRegex(lab.StoreError, "schema_version 1.*automatic migration"):
            self.store()

    def test_contract_mismatch_is_rejected_when_opening_existing_store(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload())
        with self.assertRaisesRegex(lab.StoreError, "contract"):
            lab.ToyVectorStore(self.path, make_contract(space_id="other"))

    def test_persisted_vector_dimension_bool_zero_and_normalization_are_checked(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload())
        mutations = [
            (lambda value: value["points"][0].__setitem__("vector", [1.0]), "dimension must be"),
            (lambda value: value["points"][0].__setitem__("vector", [True, 0.0]), "must be finite"),
            (lambda value: value["points"][0].__setitem__("vector", [0.0, 0.0]), "zero vector"),
            (lambda value: value["points"][0].__setitem__("vector", [2.0, 0.0]), "normalized=true"),
        ]
        original = self.path.read_text(encoding="utf-8")
        for mutator, message in mutations:
            self.path.write_text(original, encoding="utf-8", newline="\n")
            self.mutate_state(mutator)
            with self.subTest(message=message), self.assertRaisesRegex(
                lab.StoreError, message
            ):
                self.store()

    def test_duplicate_point_and_point_tombstone_overlap_are_rejected(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload())
        original = self.path.read_text(encoding="utf-8")
        self.mutate_state(lambda value: value["points"].append(value["points"][0]))
        with self.assertRaisesRegex(lab.StoreError, "duplicate point_id"):
            self.store()
        self.path.write_text(original, encoding="utf-8", newline="\n")

        def overlap(value: dict[str, object]) -> None:
            value["tombstones"] = [
                {
                    "point_id": "p1",
                    "tenant_id": "alpha",
                    "deleted_source_revision": "source-r1",
                    "delete_event_id": "delete-p1-r1",
                    "deleted_at_store_revision": 1,
                }
            ]

        self.mutate_state(overlap)
        with self.assertRaisesRegex(lab.StoreError, "must not coexist"):
            self.store()

    def test_size_limit_is_enforced_before_json_parsing(self) -> None:
        self.write_raw("12345678901")
        with patch.object(lab, "MAX_STORE_BYTES", 10):
            with self.assertRaisesRegex(lab.StoreError, "exceeds"):
                self.store()

    def test_record_limit_counts_tombstones_on_commit_and_load(self) -> None:
        store = self.store()
        with patch.object(lab, "MAX_RECORDS", 1):
            self.assertTrue(
                store.delete(
                    "p1",
                    tenant_id="alpha",
                    expected_source_revision="r1",
                    delete_event_id="delete-p1-r1",
                )
            )
            with self.assertRaisesRegex(lab.StoreError, "records exceed"):
                store.delete(
                    "p2",
                    tenant_id="alpha",
                    expected_source_revision="r1",
                    delete_event_id="delete-p2-r1",
                )
        self.assertEqual(store.snapshot_summary()["tombstone_ids"], ["p1"])
        self.assertTrue(
            store.delete(
                "p2",
                tenant_id="alpha",
                expected_source_revision="r1",
                delete_event_id="delete-p2-r1",
            )
        )
        with patch.object(lab, "MAX_RECORDS", 1):
            with self.assertRaisesRegex(lab.StoreError, "records exceed"):
                self.store()

    def test_commit_limits_encoded_utf8_bytes_before_replace(self) -> None:
        control_path = Path(self.temporary.name) / "control.json"
        payload = make_payload(
            tenant_id="tenant",
            document_id="café-" * 50,
            acl=("staff",),
        )
        control = lab.ToyVectorStore(control_path, self.contract)
        control.upsert("point", (1.0, 0.0), payload)
        character_count = len(control_path.read_text(encoding="utf-8"))
        byte_count = len(control_path.read_bytes())
        self.assertGreater(byte_count, character_count)

        guarded = self.store()
        with patch.object(lab, "MAX_STORE_BYTES", character_count):
            with self.assertRaisesRegex(lab.StoreError, "UTF-8 bytes exceed"):
                guarded.upsert("point", (1.0, 0.0), payload)
        self.assertFalse(self.path.exists())
        self.assertEqual(guarded.store_revision, 0)
        self.assertEqual(guarded.points, {})
        self.assertEqual(guarded.tombstones, {})

    def test_atomic_save_leaves_no_temp_file_and_valid_lf_json(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload())
        self.assertEqual(list(self.path.parent.glob("store.json.*.tmp")), [])
        raw = self.path.read_bytes()
        self.assertNotIn(b"\r", raw)
        self.assertTrue(raw.endswith(b"\n"))
        json.loads(raw.decode("utf-8"))


class OperationTests(TemporaryStoreMixin, unittest.TestCase):
    def test_identical_upsert_is_noop_without_revision_growth(self) -> None:
        store = self.store()
        payload = make_payload()
        self.assertEqual(store.upsert("p1", (1.0, 0.0), payload), "created")
        revision = store.store_revision
        self.assertEqual(store.upsert("p1", (1.0, 0.0), payload), "unchanged")
        self.assertEqual(store.store_revision, revision)
        self.assertEqual(len(store.points), 1)

    def test_update_replaces_same_id_and_increments_revision(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload(source_revision="r1"))
        outcome = store.upsert(
            "p1",
            (0.0, 1.0),
            make_payload(source_revision="r2", text="changed"),
            expected_source_revision="r1",
        )
        self.assertEqual(outcome, "updated")
        self.assertEqual(store.store_revision, 2)
        self.assertEqual(len(store.points), 1)
        self.assertEqual(store.points["p1"].payload.source_revision, "r2")
        self.assertEqual(
            store.upsert(
                "p1",
                (0.0, 1.0),
                make_payload(source_revision="r2", text="changed"),
                expected_source_revision="r1",
            ),
            "unchanged",
        )
        self.assertEqual(store.store_revision, 2)

    def test_stale_upsert_requires_expected_current_revision(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload(source_revision="r1"))
        with self.assertRaisesRegex(lab.WriteConflictError, "source revision"):
            store.upsert(
                "p1",
                (0.0, 1.0),
                make_payload(source_revision="r2", text="missing CAS"),
            )
        store.upsert(
            "p1",
            (0.0, 1.0),
            make_payload(source_revision="r2", text="current"),
            expected_source_revision="r1",
        )

        with self.assertRaisesRegex(lab.WriteConflictError, "source revision"):
            store.upsert(
                "p1",
                (0.6, 0.8),
                make_payload(source_revision="r3", text="stale writer"),
                expected_source_revision="r1",
            )

        result = store.search(
            (0.0, 1.0),
            top_k=1,
            tenant_id="alpha",
            subject_groups=("employees",),
        )
        self.assertEqual(result[0].source_revision, "r2")

    def test_source_revision_is_opaque_and_only_compared_by_identity(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload(source_revision="r10"))
        self.assertEqual(
            store.upsert(
                "p1",
                (0.0, 1.0),
                make_payload(source_revision="r2", text="opaque successor"),
                expected_source_revision="r10",
            ),
            "updated",
        )
        self.assertEqual(store.points["p1"].payload.source_revision, "r2")

    def test_same_source_revision_cannot_change_vector_payload_or_hash(self) -> None:
        store = self.store()
        original = make_payload(source_revision="r1")
        store.upsert("p1", (1.0, 0.0), original)
        revision = store.store_revision
        conflicts = [
            ((0.0, 1.0), original),
            (
                (1.0, 0.0),
                make_payload(source_revision="r1", text="different hash"),
            ),
            (
                (1.0, 0.0),
                make_payload(source_revision="r1", acl=("platform",)),
            ),
        ]
        for vector, payload in conflicts:
            with self.subTest(payload=payload, vector=vector), self.assertRaisesRegex(
                lab.WriteConflictError,
                "same source revision",
            ):
                store.upsert(
                    "p1",
                    vector,
                    payload,
                    expected_source_revision="r1",
                )
        self.assertEqual(store.store_revision, revision)

    def test_same_point_id_cannot_move_between_tenants(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload(tenant_id="alpha"))
        with self.assertRaisesRegex(lab.StoreError, "across tenants"):
            store.upsert(
                "p1",
                (1.0, 0.0),
                make_payload(tenant_id="beta"),
            )

    def test_upsert_rejects_bad_payload_and_vectors(self) -> None:
        store = self.store()
        with self.assertRaisesRegex(lab.StoreError, "Payload"):
            store.upsert("p1", (1.0, 0.0), {"tenant_id": "alpha"})
        vectors = [
            ((1.0,), "dimension must be"),
            ((True, 0.0), "must be finite"),
            ((0.0, 0.0), "zero vector"),
            ((2.0, 0.0), "normalized=true"),
        ]
        for vector, message in vectors:
            with self.subTest(vector=vector), self.assertRaisesRegex(
                lab.StoreError, message
            ):
                store.upsert("p1", vector, make_payload())

    def test_delete_requires_matching_current_source_revision(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload(source_revision="r1"))
        store.upsert(
            "p1",
            (0.0, 1.0),
            make_payload(source_revision="r2", text="current"),
            expected_source_revision="r1",
        )
        with self.assertRaisesRegex(lab.WriteConflictError, "source revision"):
            store.delete(
                "p1",
                tenant_id="alpha",
                expected_source_revision="r1",
                delete_event_id="delete-p1-r1",
            )
        self.assertIn("p1", store.points)
        self.assertNotIn("p1", store.tombstones)

    def test_delete_event_is_idempotent_only_for_identical_fence(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload(source_revision="r1"))
        self.assertTrue(
            store.delete(
                "p1",
                tenant_id="alpha",
                expected_source_revision="r1",
                delete_event_id="delete-p1-r1",
            )
        )
        revision = store.store_revision
        self.assertFalse(
            store.delete(
                "p1",
                tenant_id="alpha",
                expected_source_revision="r1",
                delete_event_id="delete-p1-r1",
            )
        )
        conflicts = [
            ("alpha", "r0", "delete-p1-r1"),
            ("alpha", "r1", "delete-p1-other"),
            ("beta", "r1", "delete-p1-r1"),
        ]
        for tenant_id, source_revision, event_id in conflicts:
            with self.subTest(
                tenant_id=tenant_id,
                source_revision=source_revision,
                event_id=event_id,
            ), self.assertRaises(lab.WriteConflictError):
                store.delete(
                    "p1",
                    tenant_id=tenant_id,
                    expected_source_revision=source_revision,
                    delete_event_id=event_id,
                )
        self.assertNotIn("p1", store.points)
        self.assertEqual(store.tombstones["p1"].tenant_id, "alpha")
        self.assertEqual(store.tombstones["p1"].deleted_at_store_revision, 2)
        self.assertEqual(store.store_revision, revision)

    def test_delete_before_create_records_fence_and_blocks_late_upsert(self) -> None:
        store = self.store()
        self.assertTrue(
            store.delete(
                "p1",
                tenant_id="alpha",
                expected_source_revision="r1",
                delete_event_id="delete-p1-r1",
            )
        )
        self.assertEqual(store.snapshot_summary()["tombstone_ids"], ["p1"])
        self.assertFalse(
            store.delete(
                "p1",
                tenant_id="alpha",
                expected_source_revision="r1",
                delete_event_id="delete-p1-r1",
            )
        )
        conflicts = [
            ("alpha", "r0", "delete-p1-r1"),
            ("alpha", "r1", "delete-p1-other"),
            ("beta", "r1", "delete-p1-r1"),
        ]
        for tenant_id, source_revision, event_id in conflicts:
            with self.subTest(
                tenant_id=tenant_id,
                source_revision=source_revision,
                event_id=event_id,
            ), self.assertRaises(lab.WriteConflictError):
                store.delete(
                    "p1",
                    tenant_id=tenant_id,
                    expected_source_revision=source_revision,
                    delete_event_id=event_id,
                )

        reopened = self.store()
        with self.assertRaisesRegex(lab.WriteConflictError, "resurrection token"):
            reopened.upsert(
                "p1",
                (1.0, 0.0),
                make_payload(source_revision="r1"),
            )
        with self.assertRaisesRegex(lab.WriteConflictError, "new source revision"):
            reopened.upsert(
                "p1",
                (1.0, 0.0),
                make_payload(source_revision="r1"),
                resurrect_from=lab.ResurrectionToken("r1", "delete-p1-r1"),
            )
        self.assertEqual(
            reopened.upsert(
                "p1",
                (0.0, 1.0),
                make_payload(source_revision="r2", text="new"),
                resurrect_from=lab.ResurrectionToken("r1", "delete-p1-r1"),
            ),
            "resurrected",
        )

    def test_tombstone_requires_explicit_matching_resurrection_token(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload(source_revision="r1"))
        store.delete(
            "p1",
            tenant_id="alpha",
            expected_source_revision="r1",
            delete_event_id="delete-p1-r1",
        )
        with self.assertRaisesRegex(lab.StoreError, "across tenants"):
            store.upsert(
                "p1",
                (1.0, 0.0),
                make_payload(tenant_id="beta", source_revision="r2"),
                resurrect_from=lab.ResurrectionToken("r1", "delete-p1-r1"),
            )
        with self.assertRaisesRegex(lab.WriteConflictError, "resurrection token"):
            store.upsert(
                "p1",
                (0.0, 1.0),
                make_payload(source_revision="r2", text="new"),
            )
        invalid_tokens = [
            lab.ResurrectionToken("r0", "delete-p1-r1"),
            lab.ResurrectionToken("r1", "delete-p1-other"),
        ]
        for token in invalid_tokens:
            with self.subTest(token=token), self.assertRaisesRegex(
                lab.WriteConflictError,
                "resurrection token",
            ):
                store.upsert(
                    "p1",
                    (0.0, 1.0),
                    make_payload(source_revision="r2", text="new"),
                    resurrect_from=token,
                )
        with self.assertRaisesRegex(lab.WriteConflictError, "new source revision"):
            store.upsert(
                "p1",
                (1.0, 0.0),
                make_payload(source_revision="r1"),
                resurrect_from=lab.ResurrectionToken("r1", "delete-p1-r1"),
            )
        self.assertEqual(
            store.upsert(
                "p1",
                (0.0, 1.0),
                make_payload(source_revision="r2", text="new"),
                resurrect_from=lab.ResurrectionToken("r1", "delete-p1-r1"),
            ),
            "resurrected",
        )
        self.assertNotIn("p1", store.tombstones)

    def test_resurrection_fence_survives_restart(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload(source_revision="r1"))
        store.delete(
            "p1",
            tenant_id="alpha",
            expected_source_revision="r1",
            delete_event_id="delete-p1-r1",
        )

        reopened = self.store()
        tombstone = reopened.tombstones["p1"]
        self.assertEqual(tombstone.deleted_source_revision, "r1")
        self.assertEqual(tombstone.delete_event_id, "delete-p1-r1")
        self.assertEqual(tombstone.deleted_at_store_revision, 2)
        with self.assertRaisesRegex(lab.WriteConflictError, "resurrection token"):
            reopened.upsert(
                "p1",
                (0.0, 1.0),
                make_payload(source_revision="r2", text="new"),
                resurrect_from=lab.ResurrectionToken("r1", "wrong-event"),
            )
        self.assertEqual(
            reopened.upsert(
                "p1",
                (0.0, 1.0),
                make_payload(source_revision="r2", text="new"),
                resurrect_from=lab.ResurrectionToken("r1", "delete-p1-r1"),
            ),
            "resurrected",
        )

    def test_search_filters_tenant_and_acl_before_scoring(self) -> None:
        store = self.store()
        store.upsert(
            "authorized",
            (0.8, 0.6),
            make_payload(tenant_id="alpha", acl=("employees",)),
        )
        store.upsert(
            "wrong-group",
            (1.0, 0.0),
            make_payload(
                tenant_id="alpha",
                document_id="secret",
                acl=("platform",),
                text="secret",
            ),
        )
        store.upsert(
            "wrong-tenant",
            (1.0, 0.0),
            make_payload(
                tenant_id="beta",
                document_id="private",
                acl=("employees",),
                text="private",
            ),
        )
        results = store.search(
            (1.0, 0.0),
            top_k=10,
            tenant_id="alpha",
            subject_groups=("employees",),
        )
        self.assertEqual([result.point_id for result in results], ["authorized"])

    def test_draft_is_hidden_and_safe_filters_work(self) -> None:
        store = self.store()
        store.upsert(
            "published",
            (1.0, 0.0),
            make_payload(document_id="doc-a", status="published"),
        )
        store.upsert(
            "draft",
            (1.0, 0.0),
            make_payload(document_id="doc-b", status="draft", text="draft"),
        )
        results = store.search(
            (1.0, 0.0),
            top_k=10,
            tenant_id="alpha",
            subject_groups=("employees",),
            filters={"document_id": "doc-a"},
        )
        self.assertEqual([result.point_id for result in results], ["published"])
        hidden = store.search(
            (1.0, 0.0),
            top_k=10,
            tenant_id="alpha",
            subject_groups=("employees",),
            filters={"status": "draft"},
        )
        self.assertEqual(hidden, [])

    def test_search_rejects_unsafe_filter_bad_k_and_bad_query(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload())
        calls = [
            {"query": (1.0, 0.0), "top_k": 0, "tenant_id": "alpha", "subject_groups": ("employees",)},
            {"query": (1.0,), "top_k": 1, "tenant_id": "alpha", "subject_groups": ("employees",)},
            {"query": (1.0, 0.0), "top_k": 1, "tenant_id": "alpha", "subject_groups": ("employees",), "filters": {"tenant_id": "alpha"}},
        ]
        for values in calls:
            with self.subTest(values=values), self.assertRaises(lab.StoreError):
                store.search(**values)

    def test_empty_subject_groups_fail_closed(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload())
        self.assertEqual(
            store.search(
                (1.0, 0.0),
                top_k=1,
                tenant_id="alpha",
                subject_groups=(),
            ),
            [],
        )

    def test_stale_writer_is_rejected(self) -> None:
        first = self.store()
        second = self.store()
        first.upsert("p1", (1.0, 0.0), make_payload())
        with self.assertRaises(lab.WriteConflictError):
            second.upsert(
                "p2",
                (0.0, 1.0),
                make_payload(document_id="doc-2", text="second"),
            )

    def test_stale_instance_cannot_report_identical_upsert_as_unchanged(self) -> None:
        initial = self.store()
        initial.upsert("p1", (1.0, 0.0), make_payload(source_revision="r1"))
        stale = self.store()
        current = self.store()
        current.upsert(
            "p1",
            (0.0, 1.0),
            make_payload(source_revision="r2", text="current"),
            expected_source_revision="r1",
        )

        with self.assertRaises(lab.WriteConflictError):
            stale.upsert(
                "p1",
                (1.0, 0.0),
                make_payload(source_revision="r1"),
            )

    def test_stale_instance_cannot_accept_delete_replay_after_resurrection(self) -> None:
        initial = self.store()
        initial.upsert("p1", (1.0, 0.0), make_payload(source_revision="r1"))
        initial.delete(
            "p1",
            tenant_id="alpha",
            expected_source_revision="r1",
            delete_event_id="delete-p1-r1",
        )
        stale = self.store()
        current = self.store()
        current.upsert(
            "p1",
            (0.0, 1.0),
            make_payload(source_revision="r2", text="resurrected"),
            resurrect_from=lab.ResurrectionToken("r1", "delete-p1-r1"),
        )

        with self.assertRaises(lab.WriteConflictError):
            stale.delete(
                "p1",
                tenant_id="alpha",
                expected_source_revision="r1",
                delete_event_id="delete-p1-r1",
            )

    def test_stale_instance_search_fails_closed_after_acl_update(self) -> None:
        initial = self.store()
        initial.upsert("p1", (1.0, 0.0), make_payload(source_revision="r1"))
        stale = self.store()
        current = self.store()
        current.upsert(
            "p1",
            (1.0, 0.0),
            make_payload(
                source_revision="r2",
                acl=("platform",),
                text="acl tightened",
            ),
            expected_source_revision="r1",
        )

        with self.assertRaises(lab.WriteConflictError):
            stale.search(
                (1.0, 0.0),
                top_k=1,
                tenant_id="alpha",
                subject_groups=("employees",),
            )

    def test_stale_instance_snapshot_summary_fails_closed_after_delete(self) -> None:
        initial = self.store()
        initial.upsert("p1", (1.0, 0.0), make_payload(source_revision="r1"))
        stale = self.store()
        current = self.store()
        current.delete(
            "p1",
            tenant_id="alpha",
            expected_source_revision="r1",
            delete_event_id="delete-p1-r1",
        )

        with self.assertRaises(lab.WriteConflictError):
            stale.snapshot_summary()

    def test_snapshot_summary_contains_ids_not_vectors(self) -> None:
        store = self.store()
        store.upsert("p1", (1.0, 0.0), make_payload())
        store.upsert(
            "p2",
            (0.0, 1.0),
            make_payload(document_id="doc-2", text="second"),
        )
        store.delete(
            "p1",
            tenant_id="alpha",
            expected_source_revision="source-r1",
            delete_event_id="delete-p1-source-r1",
        )
        summary = store.snapshot_summary()
        self.assertEqual(summary["point_ids"], ["p2"])
        self.assertEqual(summary["tombstone_ids"], ["p1"])
        self.assertNotIn("vector", json.dumps(summary))


class CliTests(unittest.TestCase):
    def test_demo_has_expected_security_and_lifecycle_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = lab.demo(Path(directory) / "store.json")
        self.assertEqual(report["outcomes"]["a-2-update"], "updated")
        self.assertEqual(report["outcomes"]["a-2-repeat"], "unchanged")
        self.assertEqual(
            [item["point_id"] for item in report["alpha_before_delete"]],
            ["a-1", "a-2"],
        )
        self.assertEqual(
            [item["point_id"] for item in report["alpha_after_delete"]],
            ["a-2"],
        )
        self.assertEqual(report["summary"]["store_revision"], 5)
        self.assertEqual(report["summary"]["tombstone_ids"], ["a-1"])

    def test_cli_output_matches_under_normal_and_optimized_python(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "normal.json"
            second_path = Path(directory) / "optimized.json"
            normal = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-W",
                    "error",
                    str(SCRIPT),
                    "--db",
                    str(first_path),
                    "demo",
                ],
                cwd=HERE,
                env=environment,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            optimized = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-O",
                    "-W",
                    "error",
                    str(SCRIPT),
                    "--db",
                    str(second_path),
                    "demo",
                ],
                cwd=HERE,
                env=environment,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        self.assertEqual(normal.stdout, optimized.stdout)
        parsed = json.loads(normal.stdout.decode("utf-8"))
        self.assertIn("single-process teaching store", parsed["notice"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
