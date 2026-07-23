from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from pathlib import Path

import offline_provenance_pipeline as lab


HERE = Path(__file__).resolve().parent
FIXTURE_PATH = HERE / "provenance-fixture.json"


def event(
    *,
    event_id: str,
    document_id: str,
    sequence: int,
    content: str | None,
    groups: list[str],
    source_version: str,
    tenant_id: str = "tenant-alpha",
    kind: str = "upsert",
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "kind": kind,
        "connector": "test-connector",
        "tenant_id": tenant_id,
        "document_id": document_id,
        "sequence": sequence,
        "source_uri": f"kb://{tenant_id}/{document_id}",
        "source_version": source_version,
        "media_type": "text/markdown",
        "content": content,
        "raw_sha256": lab.digest_text(content) if content is not None else None,
        "allowed_groups": groups,
    }


class FixtureContractTests(unittest.TestCase):
    def test_fixture_loads_and_separates_runtime_from_oracle(self) -> None:
        fixture = lab.load_fixture(FIXTURE_PATH)
        self.assertEqual(4, len(fixture["queries"]))
        self.assertEqual(4, len(fixture["oracle"]))
        self.assertNotIn("expected_status", fixture["queries"][0])

    def test_duplicate_json_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(lab.ContractError, "duplicate keys"):
            lab.strict_json_loads('{"a": 1, "a": 2}')

    def test_nonfinite_json_number_is_rejected(self) -> None:
        with self.assertRaisesRegex(lab.ContractError, "non-finite"):
            lab.strict_json_loads('{"a": NaN}')

    def test_unpaired_surrogate_is_rejected_before_hash_or_source_parse(self) -> None:
        with self.assertRaisesRegex(lab.ContractError, "invalid Unicode"):
            lab.strict_json_loads(r'{"value":"\ud800"}')
        with self.assertRaisesRegex(lab.ContractError, "invalid Unicode"):
            lab.canonical_json({"value": "\ud800"})

    def test_fixture_size_and_json_depth_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized.json"
            path.write_bytes(b" " * (lab.MAX_FIXTURE_BYTES + 1))
            with self.assertRaisesRegex(lab.ContractError, "must not exceed"):
                lab.load_fixture(path)

        nested = "[" * (lab.MAX_JSON_DEPTH + 1) + "0" + "]" * (
            lab.MAX_JSON_DEPTH + 1
        )
        with self.assertRaisesRegex(lab.ContractError, "nesting"):
            lab.strict_json_loads(nested)

    def test_source_and_query_resource_limits_are_enforced(self) -> None:
        oversized = event(
            event_id="oversized-source",
            document_id="large",
            sequence=1,
            content="x" * (lab.MAX_SOURCE_BYTES + 1),
            groups=["public"],
            source_version="v1",
        )
        with self.assertRaisesRegex(lab.ContractError, "content must not exceed"):
            lab.parse_source_event(oversized)

        with self.assertRaisesRegex(lab.ContractError, "top_k"):
            lab.validate_query(
                {
                    "query_id": "q-large",
                    "query": "refund",
                    "tenant_id": "tenant-alpha",
                    "subject_groups": ["public"],
                    "authorization_revision": "authz-2026-07-21",
                    "top_k": lab.MAX_TOP_K + 1,
                }
            )

    def test_canonical_json_rejects_float_domain(self) -> None:
        with self.assertRaisesRegex(lab.ContractError, "float"):
            lab.canonical_json({"score": 0.5})

    def test_source_hash_mismatch_is_rejected(self) -> None:
        value = event(
            event_id="e1",
            document_id="d1",
            sequence=1,
            content="# T\nBody.\n",
            groups=["public"],
            source_version="v1",
        )
        value["raw_sha256"] = "0" * 64
        with self.assertRaisesRegex(lab.ContractError, "does not match"):
            lab.parse_source_event(value)

    def test_bool_sequence_is_rejected(self) -> None:
        value = event(
            event_id="e1",
            document_id="d1",
            sequence=1,
            content="# T\nBody.\n",
            groups=["public"],
            source_version="v1",
        )
        value["sequence"] = True
        with self.assertRaisesRegex(lab.ContractError, "positive integer"):
            lab.parse_source_event(value)

    def test_unsorted_or_duplicate_acl_is_rejected(self) -> None:
        value = event(
            event_id="e1",
            document_id="d1",
            sequence=1,
            content="# T\nBody.\n",
            groups=["public", "admin", "admin"],
            source_version="v1",
        )
        with self.assertRaisesRegex(lab.ContractError, "sorted"):
            lab.parse_source_event(value)

    def test_unknown_fixture_field_is_rejected(self) -> None:
        raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        raw["unexpected"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(lab.ContractError, "extra"):
                lab.load_fixture(path)

    def test_delete_must_not_carry_content_or_acl(self) -> None:
        value = event(
            event_id="delete-1",
            document_id="d1",
            sequence=2,
            content=None,
            groups=["public"],
            source_version="deleted-v2",
            kind="delete",
        )
        with self.assertRaisesRegex(lab.ContractError, "delete must"):
            lab.parse_source_event(value)

    def test_line_endings_and_unicode_are_normalized(self) -> None:
        raw = "# T\r\ne\u0301\r\n"
        self.assertEqual("# T\n\u00e9\n", lab.normalize_text(raw))


class IdentityAndSpanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = lab.load_fixture(FIXTURE_PATH)
        self.contract = self.fixture["contract"]
        self.event = self.fixture["source_events"][0]
        self.revision = lab._canonical_revision(self.event, self.contract)

    def test_all_contract_digests_are_full_sha256(self) -> None:
        self.assertRegex(self.contract.parser_config_sha256, lab.HEX_64)
        self.assertRegex(self.contract.pipeline_fingerprint, lab.HEX_64)
        self.assertEqual(64, len(self.revision.canonical_revision_id.removeprefix("can_")))

    def test_parse_revision_binds_parser_configuration(self) -> None:
        first, _ = lab.parse_elements(self.revision, self.contract)
        changed = replace(
            self.contract,
            parser_revision="markdown-line-parser-v2",
            pipeline_fingerprint="f" * 64,
        )
        second, _ = lab.parse_elements(self.revision, changed)
        self.assertNotEqual(first, second)

    def test_element_identity_binds_parse_revision_span_and_text(self) -> None:
        parse_id, elements = lab.parse_elements(self.revision, self.contract)
        paragraph = next(item for item in elements if item.kind == "paragraph")
        expected = "el_" + lab.digest_object(
            {
                "parse_revision_id": parse_id,
                "kind": paragraph.kind,
                "coordinate_space": paragraph.coordinate_space,
                "char_start": paragraph.char_start,
                "char_end": paragraph.char_end,
                "text_sha256": paragraph.text_sha256,
            }
        )
        self.assertEqual(expected, paragraph.element_id)

    def test_exact_source_span_reconstructs_element(self) -> None:
        _parse_id, elements = lab.parse_elements(self.revision, self.contract)
        for element in elements:
            exact = self.revision.canonical_text[element.char_start : element.char_end]
            self.assertEqual(element.text, exact)
            self.assertEqual(element.text_sha256, lab.digest_text(exact))

    def test_duplicate_sentences_have_distinct_span_ids(self) -> None:
        source = "# T\nSame sentence.\nSame sentence.\n"
        parsed = lab.parse_source_event(
            event(
                event_id="dup",
                document_id="dup",
                sequence=1,
                content=source,
                groups=["public"],
                source_version="v1",
            )
        )
        revision = lab._canonical_revision(parsed, self.contract)
        _parse_id, elements = lab.parse_elements(revision, self.contract)
        paragraphs = [item for item in elements if item.kind == "paragraph"]
        self.assertEqual(paragraphs[0].text, paragraphs[1].text)
        self.assertNotEqual(paragraphs[0].element_id, paragraphs[1].element_id)

    def test_entry_identity_binds_retrieval_representation(self) -> None:
        parse_id, elements = lab.parse_elements(self.revision, self.contract)
        chunks = lab.build_chunks(self.revision, parse_id, elements, self.contract)
        entry = lab.build_entries(self.revision, parse_id, chunks, self.contract)[0]
        changed_hash = lab.digest_text(entry.retrieval_text + "\nchanged")
        changed_id = "idx_" + lab.digest_object(
            {
                "chunk_id": entry.chunk_id,
                "retrieval_sha256": changed_hash,
                "index_revision": entry.index_revision,
                "acl_snapshot_sha256": entry.acl_snapshot_sha256,
            }
        )
        self.assertNotEqual(entry.index_entry_id, changed_id)

    def test_deterministic_build_produces_same_generation(self) -> None:
        first = lab.initialize_fixture(self.fixture)
        second = lab.initialize_fixture(self.fixture)
        self.assertEqual(first.published_generation_id, second.published_generation_id)
        self.assertEqual(
            first._published().manifest_sha256, second._published().manifest_sha256
        )


class LifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = lab.load_fixture(FIXTURE_PATH)
        self.query = next(item for item in self.fixture["queries"] if item["query_id"] == "Q-refund")

    def _engine_with_events_only(self) -> lab.ProvenanceEngine:
        engine = lab.ProvenanceEngine(self.fixture["contract"])
        for item in self.fixture["source_events"]:
            engine.apply_event(item)
        return engine

    def test_first_build_is_not_queryable_before_publish(self) -> None:
        engine = self._engine_with_events_only()
        engine.stage_generation()
        with self.assertRaisesRegex(lab.ContractError, "no published"):
            engine.query(self.query)

    def test_identical_event_replay_is_noop(self) -> None:
        engine = lab.ProvenanceEngine(self.fixture["contract"])
        item = self.fixture["source_events"][0]
        self.assertEqual("upserted", engine.apply_event(item))
        self.assertEqual("noop", engine.apply_event(item))

    def test_event_id_cannot_be_rebound_to_different_event(self) -> None:
        engine = lab.ProvenanceEngine(self.fixture["contract"])
        item = self.fixture["source_events"][0]
        self.assertEqual("upserted", engine.apply_event(item))
        changed = replace(item, source_version="refund-v1-rebound")

        with self.assertRaisesRegex(lab.ContractError, "same event_id"):
            engine.apply_event(changed)

    def test_processed_event_window_fails_closed_when_full(self) -> None:
        engine = lab.ProvenanceEngine(self.fixture["contract"])
        engine.processed_event_sha256 = {
            f"prior-{index}": "0" * 64
            for index in range(lab.MAX_PROCESSED_EVENTS)
        }

        with self.assertRaisesRegex(lab.ContractError, "deduplication window is full"):
            engine.apply_event(self.fixture["source_events"][0])

    def test_higher_sequence_same_state_only_advances_checkpoint(self) -> None:
        engine = lab.ProvenanceEngine(self.fixture["contract"])
        original = self.fixture["source_events"][0]
        engine.apply_event(original)
        value = event(
            event_id="checkpoint-2",
            document_id=original.document_id,
            sequence=2,
            content=original.content,
            groups=list(original.allowed_groups),
            source_version=original.source_version,
        )
        value["connector"] = original.connector
        self.assertEqual("checkpoint_advanced", engine.apply_event(value))
        self.assertEqual(1, len(engine.revisions))

    def test_equal_sequence_different_state_is_conflict(self) -> None:
        engine = lab.ProvenanceEngine(self.fixture["contract"])
        engine.apply_event(self.fixture["source_events"][0])
        value = event(
            event_id="conflict",
            document_id="refund-policy",
            sequence=1,
            content="# Refund policy\nConflicting content.\n",
            groups=["public"],
            source_version="refund-v1-conflict",
        )
        with self.assertRaisesRegex(lab.ContractError, "same source sequence"):
            engine.apply_event(value)

    def test_stale_event_cannot_overwrite_current_state(self) -> None:
        engine = lab.initialize_fixture(self.fixture)
        current = engine.documents[("tenant-alpha", "refund-policy")].canonical_revision_id
        stale = event(
            event_id="stale",
            document_id="refund-policy",
            sequence=0,
            content="# T\nOld content.\n",
            groups=["public"],
            source_version="stale",
        )
        stale["sequence"] = 0
        parsed = lab.parse_source_event({**stale, "sequence": 1})
        stale_object = replace(parsed, sequence=0)
        self.assertEqual("stale_ignored", engine.apply_event(stale_object))
        self.assertEqual(
            current,
            engine.documents[("tenant-alpha", "refund-policy")].canonical_revision_id,
        )

    def test_failed_content_build_keeps_old_published_revision(self) -> None:
        engine = lab.initialize_fixture(self.fixture)
        updated = "# Refund policy\nThe finance team completes refund review within seven business days after a refund request is submitted.\n"
        engine.apply_event(
            event(
                event_id="refund-v2",
                document_id="refund-policy",
                sequence=2,
                content=updated,
                groups=["public"],
                source_version="refund-v2",
            )
        )
        failed = engine.stage_generation(failure="after_n_index_entries")
        self.assertEqual("failed", failed.status)
        public, _audit = engine.query(self.query)
        self.assertIn("within five business days", public["claims"][0]["text"])

    def test_content_cutover_invalidates_old_citation(self) -> None:
        engine = lab.initialize_fixture(self.fixture)
        before, before_audit = engine.query(self.query)
        updated = "# Refund policy\nThe finance team completes refund review within seven business days after a refund request is submitted.\n"
        engine.apply_event(
            event(
                event_id="refund-v2",
                document_id="refund-policy",
                sequence=2,
                content=updated,
                groups=["public"],
                source_version="refund-v2",
            )
        )
        engine.build_and_publish()
        after, _ = engine.query(self.query)
        self.assertIn("within seven business days", after["claims"][0]["text"])
        self.assertNotEqual(
            before["claims"][0]["citations"][0]["canonical_revision_id"],
            after["claims"][0]["citations"][0]["canonical_revision_id"],
        )
        self.assertIn(
            "generation_not_published",
            engine.validate_evidence(self.query, before, before_audit),
        )

    def test_acl_tightening_blocks_old_generation_immediately(self) -> None:
        engine = lab.initialize_fixture(self.fixture)
        original = self.fixture["source_events"][0]
        engine.apply_event(
            event(
                event_id="refund-acl-v2",
                document_id="refund-policy",
                sequence=2,
                content=original.content,
                groups=["finance"],
                source_version="refund-acl-v2",
            )
        )
        public, _audit = engine.query(self.query)
        self.assertEqual("insufficient_evidence", public["status"])

    def test_acl_projection_restores_only_new_group(self) -> None:
        engine = lab.initialize_fixture(self.fixture)
        original = self.fixture["source_events"][0]
        engine.apply_event(
            event(
                event_id="refund-acl-v2",
                document_id="refund-policy",
                sequence=2,
                content=original.content,
                groups=["finance"],
                source_version="refund-acl-v2",
            )
        )
        engine.build_and_publish()
        public, _audit = engine.query(self.query)
        self.assertEqual("insufficient_evidence", public["status"])
        finance_query = {**self.query, "subject_groups": ["finance"]}
        allowed, _audit = engine.query(finance_query)
        self.assertEqual("answered", allowed["status"])

    def test_delete_blocks_old_projection_immediately(self) -> None:
        engine = lab.initialize_fixture(self.fixture)
        engine.apply_event(
            event(
                event_id="refund-delete-v2",
                document_id="refund-policy",
                sequence=2,
                content=None,
                groups=[],
                source_version="deleted-v2",
                kind="delete",
            )
        )
        public, _audit = engine.query(self.query)
        self.assertEqual("insufficient_evidence", public["status"])

    def test_stale_snapshot_with_new_tombstone_is_blocked(self) -> None:
        engine = lab.initialize_fixture(self.fixture)
        stale_snapshot = engine.capture_snapshot()
        engine.apply_event(
            event(
                event_id="refund-delete-v2",
                document_id="refund-policy",
                sequence=2,
                content=None,
                groups=[],
                source_version="deleted-v2",
                kind="delete",
            )
        )
        generation = engine.stage_generation(snapshot=stale_snapshot)
        with self.assertRaisesRegex(lab.ContractError, "stale_snapshot"):
            engine.publish_generation(generation.generation_id)

    def test_resurrection_waits_for_new_publication(self) -> None:
        engine = lab.initialize_fixture(self.fixture)
        engine.apply_event(
            event(
                event_id="refund-delete-v2",
                document_id="refund-policy",
                sequence=2,
                content=None,
                groups=[],
                source_version="deleted-v2",
                kind="delete",
            )
        )
        engine.apply_event(
            event(
                event_id="refund-resurrect-v3",
                document_id="refund-policy",
                sequence=3,
                content="# Refund policy\nThe finance team completes refund review within six business days after a refund request is submitted.\n",
                groups=["public"],
                source_version="refund-v3",
            )
        )
        blocked, _audit = engine.query(self.query)
        self.assertEqual("insufficient_evidence", blocked["status"])
        engine.build_and_publish()
        restored, _audit = engine.query(self.query)
        self.assertEqual("answered", restored["status"])

    def test_partial_generation_cannot_publish(self) -> None:
        engine = self._engine_with_events_only()
        generation = engine.stage_generation(failure="after_n_index_entries")
        with self.assertRaisesRegex(lab.ContractError, "staged"):
            engine.publish_generation(generation.generation_id)

    def test_generation_missing_one_entry_cannot_publish(self) -> None:
        engine = self._engine_with_events_only()
        generation = engine.stage_generation()
        generation.entries = generation.entries[:-1]
        with self.assertRaisesRegex(lab.ContractError, "entry_set_hash_mismatch"):
            engine.publish_generation(generation.generation_id)

    def test_authorization_revision_mismatch_fails_closed(self) -> None:
        engine = lab.initialize_fixture(self.fixture)
        engine.rotate_authorization("auth-v2")
        public, audit = engine.query(self.query)
        self.assertEqual("insufficient_evidence", public["status"])
        self.assertEqual("authorization_snapshot_mismatch", audit["failure"])
        self.assertEqual([], engine.validate_evidence(self.query, public, audit))

    def test_new_authorization_revision_requires_new_generation(self) -> None:
        engine = lab.initialize_fixture(self.fixture)
        engine.rotate_authorization("auth-v2")
        generation = engine.stage_generation(authorization_revision="auth-v2")
        engine.publish_generation(generation.generation_id)
        query = {**self.query, "authorization_revision": "auth-v2"}
        public, _audit = engine.query(query)
        self.assertEqual("answered", public["status"])

    def test_unknown_generation_auth_revision_is_rejected(self) -> None:
        engine = self._engine_with_events_only()
        with self.assertRaisesRegex(lab.ContractError, "unknown authorization"):
            engine.stage_generation(authorization_revision="auth-forged")


class IntegrityAndCitationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = lab.load_fixture(FIXTURE_PATH)
        self.engine = lab.initialize_fixture(self.fixture)
        self.query = next(item for item in self.fixture["queries"] if item["query_id"] == "Q-refund")
        self.public, self.audit = self.engine.query(self.query)

    def test_public_response_excludes_protected_diagnostics(self) -> None:
        rendered = lab.canonical_json(self.public)
        for forbidden in ("filter_summary", "selected_entry_ids", "visibility"):
            self.assertNotIn(forbidden, rendered)

    def test_public_citation_and_protected_generation_reconstruct_chain(self) -> None:
        self.assertEqual([], self.engine.validate_evidence(self.query, self.public, self.audit))
        citation = self.public["claims"][0]["citations"][0]
        self.assertIn(citation["index_entry_id"], self.audit["selected_entry_ids"])
        self.assertRegex(self.audit["index_generation_id"].removeprefix("gen_"), lab.HEX_64)

    def test_tampered_source_span_is_rejected(self) -> None:
        public = copy.deepcopy(self.public)
        public["claims"][0]["citations"][0]["char_end"] -= 1
        errors = self.engine.validate_evidence(self.query, public, self.audit)
        self.assertIn("citation_binding_mismatch", errors)

    def test_tampered_claim_is_rejected_even_with_old_hash(self) -> None:
        public = copy.deepcopy(self.public)
        public["claims"][0]["text"] = "Refund review completes the same day."
        errors = self.engine.validate_evidence(self.query, public, self.audit)
        self.assertIn("citation_does_not_support_claim", errors)

    def test_tampered_raw_source_hash_is_rejected(self) -> None:
        public = copy.deepcopy(self.public)
        public["claims"][0]["citations"][0]["raw_sha256"] = "0" * 64
        errors = self.engine.validate_evidence(self.query, public, self.audit)
        self.assertIn("citation_raw_hash_mismatch", errors)

    def test_unhashable_external_ids_fail_closed_as_errors(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["index_generation_id"] = []
        self.assertIn(
            "index_generation_id_invalid",
            self.engine.validate_evidence(self.query, self.public, audit),
        )

        public = copy.deepcopy(self.public)
        public["claims"][0]["citations"][0]["index_entry_id"] = []
        self.assertIn(
            "citation_string_field_invalid",
            self.engine.validate_evidence(self.query, public, self.audit),
        )

    def test_citation_to_unselected_entry_is_rejected(self) -> None:
        public = copy.deepcopy(self.public)
        selected = set(self.audit["selected_entry_ids"])
        other = next(
            entry
            for entry in self.engine._published().entries
            if entry.index_entry_id not in selected
        )
        public["claims"][0]["citations"][0]["index_entry_id"] = other.index_entry_id
        errors = self.engine.validate_evidence(self.query, public, self.audit)
        self.assertIn("citation_not_selected", errors)

    def test_swapped_audit_generation_is_rejected(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["index_generation_id"] = "gen_" + "0" * 64
        errors = self.engine.validate_evidence(self.query, self.public, audit)
        self.assertIn("generation_not_published", errors)

    def test_trace_id_is_recomputed(self) -> None:
        public = copy.deepcopy(self.public)
        public["trace_id"] = "0" * 64
        audit = copy.deepcopy(self.audit)
        audit["trace_id"] = "0" * 64
        errors = self.engine.validate_evidence(self.query, public, audit)
        self.assertIn("trace_binding_mismatch", errors)

    def test_extra_selected_entry_is_rejected(self) -> None:
        audit = copy.deepcopy(self.audit)
        selected = set(audit["selected_entry_ids"])
        other = next(
            entry.index_entry_id
            for entry in self.engine._published().entries
            if entry.index_entry_id not in selected
        )
        audit["selected_entry_ids"].append(other)
        errors = self.engine.validate_evidence(self.query, self.public, audit)
        self.assertIn("selected_citation_set_mismatch", errors)

    def test_visible_but_low_relevance_entry_cannot_self_attest(self) -> None:
        other_query = next(
            item
            for item in self.fixture["queries"]
            if item["query_id"] == "Q-untrusted-content"
        )
        forged_public, forged_audit = self.engine.query(other_query)
        forged_public["query_id"] = self.query["query_id"]
        forged_public["trace_id"] = lab.digest_object(
            {
                "query": self.query,
                "status": forged_public["status"],
                "claims": forged_public["claims"],
            }
        )
        forged_audit["trace_id"] = forged_public["trace_id"]
        errors = self.engine.validate_evidence(
            self.query, forged_public, forged_audit
        )
        self.assertIn("selected_entries_not_recomputed", errors)

    def test_filter_summary_is_recomputed(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["filter_summary"]["filtered"] += 1
        errors = self.engine.validate_evidence(self.query, self.public, audit)
        self.assertIn("filter_summary_not_recomputed", errors)

    def test_selected_claim_order_must_follow_recomputed_rank(self) -> None:
        content = "# Refund supplement\nThe finance team completes refund review within ten business days after a refund request is submitted.\n"
        self.engine.apply_event(
            event(
                event_id="refund-supplement-v1",
                document_id="refund-supplement",
                sequence=1,
                content=content,
                groups=["public"],
                source_version="supplement-v1",
            )
        )
        self.engine.build_and_publish()
        query = {**self.query, "top_k": 2}
        public, audit = self.engine.query(query)
        self.assertEqual(2, len(public["claims"]))
        public["claims"].reverse()
        public["trace_id"] = lab.digest_object(
            {"query": query, "status": public["status"], "claims": public["claims"]}
        )
        audit["trace_id"] = public["trace_id"]
        errors = self.engine.validate_evidence(query, public, audit)
        self.assertIn("selected_citation_order_mismatch", errors)

    def test_audit_authorization_revision_swap_is_rejected(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["authorization_revision"] = "auth-v2"
        errors = self.engine.validate_evidence(self.query, self.public, audit)
        self.assertIn("audit_authorization_revision_mismatch", errors)

    def test_non_answered_status_cannot_keep_claims(self) -> None:
        public = copy.deepcopy(self.public)
        public["status"] = "insufficient_evidence"
        errors = self.engine.validate_evidence(self.query, public, self.audit)
        self.assertIn("non_answered_with_claims", errors)

    def test_stale_answer_cannot_hide_behind_authorization_failure(self) -> None:
        self.engine.rotate_authorization("auth-v2")
        forged_audit = copy.deepcopy(self.audit)
        forged_audit["failure"] = "authorization_snapshot_mismatch"
        errors = self.engine.validate_evidence(
            self.query, self.public, forged_audit
        )
        self.assertIn("authorization_failure_status_mismatch", errors)
        self.assertIn("authorization_failure_must_not_return_evidence", errors)

    def test_answer_cannot_hide_behind_retrieval_failure(self) -> None:
        forged_audit = copy.deepcopy(self.audit)
        forged_audit["failure"] = "retrieval_unavailable"
        forged_audit["filter_summary"] = {"visible": 0, "filtered": 0}
        errors = self.engine.validate_evidence(
            self.query, self.public, forged_audit
        )
        self.assertIn("retrieval_failure_status_mismatch", errors)
        self.assertIn("retrieval_failure_must_not_return_evidence", errors)

    def test_projection_text_tampering_is_reconciled_from_actual_text(self) -> None:
        generation = self.engine._published()
        first = generation.entries[0]
        generation.entries = (replace(first, retrieval_text=first.retrieval_text + " tampered"),) + generation.entries[1:]
        report = self.engine.reconcile()
        self.assertGreater(report["index_entry_integrity_mismatch"], 0)
        with self.assertRaisesRegex(lab.ContractError, "reconciliation failed"):
            self.engine.require_reconciled()

    def test_cross_tenant_entry_route_swap_is_rejected(self) -> None:
        generation = self.engine._published()
        entries = list(generation.entries)
        alpha_index = next(
            index
            for index, entry in enumerate(entries)
            if (entry.tenant_id, entry.document_id)
            == ("tenant-alpha", "refund-policy")
        )
        beta_index = next(
            index
            for index, entry in enumerate(entries)
            if (entry.tenant_id, entry.document_id)
            == ("tenant-beta", "cross-tenant-refund")
        )
        alpha = entries[alpha_index]
        beta = entries[beta_index]
        entries[alpha_index] = replace(
            alpha,
            tenant_id=beta.tenant_id,
            document_id=beta.document_id,
        )
        entries[beta_index] = replace(
            beta,
            tenant_id=alpha.tenant_id,
            document_id=alpha.document_id,
        )
        generation.entries = tuple(entries)

        with self.assertRaisesRegex(
            lab.ContractError, "entry_document_binding_mismatch"
        ):
            self.engine._published()
        self.assertGreater(
            self.engine.reconcile()["index_entry_integrity_mismatch"], 0
        )

    def test_canonical_text_tampering_is_recomputed(self) -> None:
        revision_id = next(iter(self.engine.revisions))
        revision = self.engine.revisions[revision_id]
        self.engine.revisions[revision_id] = replace(
            revision, canonical_text=revision.canonical_text + "tampered"
        )
        report = self.engine.reconcile()
        self.assertEqual(1, report["canonical_text_hash_mismatch"])

    def test_raw_text_tampering_is_recomputed(self) -> None:
        revision_id = next(iter(self.engine.revisions))
        revision = self.engine.revisions[revision_id]
        self.engine.revisions[revision_id] = replace(
            revision, raw_content=revision.raw_content + "tampered"
        )
        report = self.engine.reconcile()
        self.assertEqual(1, report["canonical_raw_hash_mismatch"])

    def test_unauthorized_document_change_does_not_change_public_response(self) -> None:
        before = copy.deepcopy(self.public)
        secret = "# Private refund\nInternal refund review takes three hundred days.\n"
        self.engine.apply_event(
            event(
                event_id="private-refund-v1",
                document_id="private-refund",
                sequence=1,
                content=secret,
                groups=["secret"],
                source_version="private-v1",
            )
        )
        self.engine.build_and_publish()
        after, _audit = self.engine.query(self.query)
        self.assertEqual(before, after)

    def test_oracle_mutation_cannot_change_runtime_output(self) -> None:
        first_engine = lab.initialize_fixture(self.fixture)
        first, _audit = first_engine.query(self.query)
        raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        raw["oracle"][0]["slice"] = "oracle-mutated-without-runtime-change"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            mutated = lab.load_fixture(path)
            second_engine = lab.initialize_fixture(mutated)
            second_query = next(
                item for item in mutated["queries"] if item["query_id"] == "Q-refund"
            )
            second, _audit = second_engine.query(second_query)
        self.assertEqual(first, second)

    def test_in_memory_fixture_mutation_after_validation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.fixture)
        mutated["oracle"][0]["slice"] = "changed-after-load"
        with self.assertRaisesRegex(lab.ContractError, "changed after strict loading"):
            lab.initialize_fixture(mutated)

    def test_untrusted_source_text_cannot_change_control_metadata(self) -> None:
        query = next(
            item
            for item in self.fixture["queries"]
            if item["query_id"] == "Q-untrusted-content"
        )
        public, audit = self.engine.query(query)
        self.assertIn("ignore system instructions", public["claims"][0]["text"])
        self.assertEqual("auth-v1", audit["authorization_revision"])
        self.assertEqual(self.engine.published_generation_id, audit["index_generation_id"])


class EvaluationAndCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = lab.load_fixture(FIXTURE_PATH)

    def test_evaluation_artifact_binds_all_control_planes(self) -> None:
        artifact = lab.evaluate_fixture(self.fixture)
        self.assertEqual("PASS", artifact["decision"])
        self.assertEqual([], lab.validate_artifact(artifact))
        for field in (
            "fixture_sha256",
            "pipeline_fingerprint",
            "snapshot_state_sha256",
            "tombstone_state_sha256",
            "index_manifest_sha256",
            "artifact_sha256",
        ):
            self.assertRegex(artifact[field], lab.HEX_64)

    def test_artifact_tampering_is_detected(self) -> None:
        artifact = lab.evaluate_fixture(self.fixture)
        artifact["passed_case_count"] = 0
        errors = lab.validate_artifact(artifact)
        self.assertIn("passed_case_count_mismatch", errors)
        self.assertIn("artifact_hash_mismatch", errors)

    def test_self_consistent_malformed_artifact_cases_are_rejected(self) -> None:
        artifact = lab.evaluate_fixture(self.fixture)
        artifact["cases"] = [{"passed": True} for _item in artifact["cases"]]
        unsigned = {
            key: copy.deepcopy(value)
            for key, value in artifact.items()
            if key != "artifact_sha256"
        }
        artifact["artifact_sha256"] = lab.digest_object(unsigned)
        errors = lab.validate_artifact(artifact)
        self.assertTrue(any("schema_mismatch" in error for error in errors))

    def test_retrieval_failure_blocks_evaluation(self) -> None:
        artifact = lab.evaluate_fixture(self.fixture, failure="retrieval_unavailable")
        self.assertEqual("BLOCK", artifact["decision"])
        self.assertEqual(0, artifact["passed_case_count"])

    def test_cli_evaluate_success(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = lab.main(["--fixture", str(FIXTURE_PATH), "evaluate"])
        self.assertEqual(0, code)
        self.assertEqual("PASS", json.loads(output.getvalue())["decision"])

    def test_cli_failure_returns_block_exit_code(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = lab.main(
                [
                    "--fixture",
                    str(FIXTURE_PATH),
                    "evaluate",
                    "--failure",
                    "retrieval_unavailable",
                ]
            )
        self.assertEqual(1, code)
        self.assertEqual("BLOCK", json.loads(output.getvalue())["decision"])

    def test_inspect_requires_explicit_operator_view(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = lab.main(
                [
                    "--fixture",
                    str(FIXTURE_PATH),
                    "inspect",
                    "--query-id",
                    "Q-refund",
                ]
            )
        self.assertEqual(2, code)
        self.assertIn("--operator-view", stderr.getvalue())

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = lab.main(["--fixture", str(FIXTURE_PATH), "manifest"])
        self.assertEqual(2, code)
        self.assertIn("--operator-view", stderr.getvalue())

    def test_manifest_exposes_no_source_content(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = lab.main(
                ["--fixture", str(FIXTURE_PATH), "manifest", "--operator-view"]
            )
        self.assertEqual(0, code)
        manifest = json.loads(output.getvalue())
        self.assertNotIn("content", manifest)
        self.assertNotIn("entries", manifest)


if __name__ == "__main__":
    unittest.main()
