"""Red-team tests for the cross-layer parser/KB/chunk/citation adapter."""

from __future__ import annotations

import copy
from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cross_layer_adapter as lab


HERE = Path(__file__).resolve().parent
FIXTURE_PATH = HERE / "cross-layer-fixture.json"
SCHEMA_PATH = HERE / "cross-layer-eval-artifact.schema.json"


def raw_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def runtime_query(fixture: dict[str, object], query_id: str) -> dict[str, object]:
    queries = fixture["queries"]
    if not isinstance(queries, list):
        raise RuntimeError("fixture queries contract drift")
    value = next(item for item in queries if item["query_id"] == query_id)
    return lab._runtime_query(value)


def rehash_public(public: dict[str, object]) -> None:
    claims = public["claims"]
    if not isinstance(claims, list):
        raise RuntimeError("claims contract drift")
    for claim in claims:
        citations = claim["citations"]
        for citation in citations:
            body = {key: copy.deepcopy(value) for key, value in citation.items() if key != "citation_id"}
            citation["citation_id"] = "xcit_" + lab.digest_object(body)
        claim_body = {"citations": citations, "text": claim["text"]}
        claim["claim_id"] = "xclm_" + lab.digest_object(
            {"query_id": public["query_id"], **claim_body}
        )
    public["trace_id"] = "xtr_" + lab.digest_object(
        {
            "claims": claims,
            "query_id": public["query_id"],
            "status": public["status"],
        }
    )


def rehash_artifact(artifact: dict[str, object]) -> None:
    body = {key: copy.deepcopy(value) for key, value in artifact.items() if key != "artifact_sha256"}
    artifact["artifact_sha256"] = lab.digest_object(body)


class EngineCase(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = lab.load_fixture(FIXTURE_PATH)
        self.temporary = tempfile.TemporaryDirectory(prefix="adapter-redteam-")
        self.addCleanup(self.temporary.cleanup)
        self.engine = lab.initialize_fixture(
            self.fixture, Path(self.temporary.name) / "sources"
        )
        self.addCleanup(self.engine.close)

    def query(self, query_id: str, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        return self.engine.query(runtime_query(self.fixture, query_id), **kwargs)


class FixtureContractTests(unittest.TestCase):
    def test_fixture_loads_and_runtime_query_excludes_oracle(self) -> None:
        fixture = lab.load_fixture(FIXTURE_PATH)
        query = runtime_query(fixture, "q-tenant-a-refund")
        self.assertEqual(3, len(fixture["documents"]))
        self.assertNotIn("expected_claim_texts", query)
        self.assertNotIn("forbidden_document_ids", query)
        lab.require_fixture_integrity(fixture)

    def test_strict_json_rejects_duplicate_keys_nonfinite_and_float_domain(self) -> None:
        with self.assertRaisesRegex(lab.IntegrationError, "duplicate"):
            lab.strict_json_loads('{"a":1,"a":2}')
        with self.assertRaisesRegex(lab.IntegrationError, "non-finite"):
            lab.strict_json_loads('{"a":NaN}')
        with self.assertRaisesRegex(lab.IntegrationError, "floating-point"):
            lab.strict_json_loads('{"a":0.5}')
        with self.assertRaises(lab.IntegrationError):
            lab.canonical_json({"a": 0.5})

    def test_fixture_json_resource_and_unicode_boundaries_fail_closed(self) -> None:
        nested = "[" * (lab.MAX_JSON_DEPTH + 1) + "0" + "]" * (
            lab.MAX_JSON_DEPTH + 1
        )
        with self.assertRaisesRegex(lab.IntegrationError, "nesting"):
            lab.strict_json_loads(nested)
        with self.assertRaisesRegex(lab.IntegrationError, "invalid Unicode"):
            lab.strict_json_loads(r'{"value":"\ud800"}')
        with self.assertRaisesRegex(lab.IntegrationError, "must not exceed"):
            lab.strict_json_loads(" " * (lab.MAX_FIXTURE_BYTES + 1))

        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "invalid-utf8.json"
            fixture.write_bytes(b"\xff")
            with self.assertRaisesRegex(lab.IntegrationError, "UnicodeDecodeError") as caught:
                lab.load_fixture(fixture)
        self.assertNotIn("invalid-utf8.json", str(caught.exception))

    def test_fixture_requires_exact_root_and_document_fields(self) -> None:
        unexpected = raw_fixture()
        unexpected["unexpected"] = True
        with self.assertRaisesRegex(lab.IntegrationError, "fields must match exactly"):
            lab.validate_fixture(unexpected)
        missing = raw_fixture()
        del missing["documents"][0]["source_uri"]
        with self.assertRaisesRegex(lab.IntegrationError, "fields must match exactly"):
            lab.validate_fixture(missing)

    def test_bool_and_invalid_overlap_are_rejected_as_numbers(self) -> None:
        value = raw_fixture()
        value["documents"][0]["source_sequence"] = True
        with self.assertRaisesRegex(lab.IntegrationError, "integer"):
            lab.validate_fixture(value)
        value = raw_fixture()
        value["contract"]["chunk_config"]["overlap_units"] = True
        with self.assertRaisesRegex(lab.IntegrationError, "overlap"):
            lab.validate_fixture(value)

    def test_acl_sorting_and_relative_path_boundary_are_enforced(self) -> None:
        value = raw_fixture()
        value["documents"][0]["allowed_groups"] = ["z", "a", "a"]
        with self.assertRaisesRegex(lab.IntegrationError, "sorted"):
            lab.validate_fixture(value)
        for bad_path in ("../escape.md", "C:\\escape.md", "plain.txt"):
            with self.subTest(path=bad_path):
                value = raw_fixture()
                value["documents"][0]["relative_path"] = bad_path
                with self.assertRaises(lab.IntegrationError):
                    lab.validate_fixture(value)

    def test_safe_output_path_rejects_in_root_outside_and_parent_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            root = temporary / "root"
            root.mkdir()
            real_file = root / "real.md"
            real_file.write_text("inside", encoding="utf-8")
            outside_file = temporary / "outside.md"
            outside_file.write_text("outside", encoding="utf-8")
            real_directory = root / "real-directory"
            real_directory.mkdir()
            (real_directory / "document.md").write_text("nested", encoding="utf-8")
            try:
                (root / "inside-link.md").symlink_to(real_file)
                (root / "outside-link.md").symlink_to(outside_file)
                (root / "parent-link").symlink_to(
                    real_directory, target_is_directory=True
                )
            except OSError as exc:
                self.skipTest(f"The current platform does not permit test symlinks: {exc}")

            for relative_path in (
                "inside-link.md",
                "outside-link.md",
                "parent-link/document.md",
            ):
                with self.subTest(relative_path=relative_path):
                    with self.assertRaisesRegex(lab.IntegrationError, "symlink"):
                        lab._safe_output_path(root, relative_path)

            outside_root = temporary / "outside-root"
            outside_root.mkdir()
            logical_root = temporary / "logical-root"
            logical_root.symlink_to(outside_root, target_is_directory=True)
            unexpected_engine = None
            try:
                with self.assertRaisesRegex(lab.IntegrationError, "symlink"):
                    unexpected_engine = lab.CrossLayerEngine(
                        lab.load_fixture(FIXTURE_PATH), logical_root
                    )
            finally:
                if unexpected_engine is not None:
                    unexpected_engine.close()
            self.assertEqual([], list(outside_root.iterdir()))

    def test_native_contract_version_drift_is_rejected(self) -> None:
        for field, value in (
            ("parser_schema_version", "999"),
            ("knowledge_store_schema_version", "999"),
            ("index_revision", "stale-index"),
        ):
            with self.subTest(field=field):
                fixture = raw_fixture()
                fixture["contract"][field] = value
                with self.assertRaises(lab.IntegrationError):
                    lab.validate_fixture(fixture)

    def test_duplicate_document_path_event_and_query_identity_are_rejected(self) -> None:
        mutations = (
            ("documents", 1, "document_id", "refund-policy"),
            ("documents", 1, "relative_path", "tenant-a/refund.md"),
            ("documents", 1, "upstream_event_id", "event-tenant-a-refund-v1"),
            ("queries", 1, "query_id", "q-tenant-a-refund"),
        )
        for collection, index, field, value in mutations:
            with self.subTest(field=field):
                fixture = raw_fixture()
                fixture[collection][index][field] = value
                with self.assertRaises(lab.IntegrationError):
                    lab.validate_fixture(fixture)

    def test_runtime_query_is_exact_sorted_and_bounded(self) -> None:
        query = runtime_query(lab.load_fixture(FIXTURE_PATH), "q-tenant-a-refund")
        query["unexpected"] = True
        with self.assertRaisesRegex(lab.IntegrationError, "fields must match exactly"):
            lab.validate_runtime_query(query)
        query = runtime_query(lab.load_fixture(FIXTURE_PATH), "q-tenant-a-refund")
        query["subject_groups"] = ["z", "a"]
        with self.assertRaisesRegex(lab.IntegrationError, "sorted"):
            lab.validate_runtime_query(query)
        query = runtime_query(lab.load_fixture(FIXTURE_PATH), "q-tenant-a-refund")
        query["top_k"] = True
        with self.assertRaisesRegex(lab.IntegrationError, "integer"):
            lab.validate_runtime_query(query)


class IdentityAndProjectionTests(EngineCase):
    def test_identical_cross_tenant_bytes_collide_natively_but_are_namespaced(self) -> None:
        generation = self.engine._published_generation()
        first = generation.documents[("tenant-a", "refund-policy")]
        second = generation.documents[("tenant-b", "refund-policy-copy")]
        first_native = [item["native_element_id"]["value"] for item in first.crosswalk]
        second_native = [item["native_element_id"]["value"] for item in second.crosswalk]
        self.assertEqual(first_native, second_native)
        self.assertNotEqual(first.source_id, second.source_id)
        self.assertTrue(set(first.element_context).isdisjoint(second.element_context))

    def test_namespacing_propagates_to_chunk_and_index_entry_ids(self) -> None:
        generation = self.engine._published_generation()
        by_document: dict[tuple[str, str], list[object]] = {}
        for chunk in generation.chunks:
            by_document.setdefault(generation.chunk_documents[chunk.chunk_id], []).append(chunk)
        left = by_document[("tenant-a", "refund-policy")][0]
        right = by_document[("tenant-b", "refund-policy-copy")][0]
        self.assertNotEqual(left.chunk_id, right.chunk_id)
        self.assertNotEqual(
            lab.CHUNK.index_entry_id(left, index_revision=self.engine.contract.index_revision),
            lab.CHUNK.index_entry_id(right, index_revision=self.engine.contract.index_revision),
        )

    def test_fresh_build_is_deterministic_and_manifest_binds_capture(self) -> None:
        second_temp = tempfile.TemporaryDirectory(prefix="adapter-second-")
        self.addCleanup(second_temp.cleanup)
        second = lab.initialize_fixture(self.fixture, Path(second_temp.name) / "sources")
        self.addCleanup(second.close)
        first_generation = self.engine._published_generation()
        second_generation = second._published_generation()
        self.assertEqual(first_generation.generation_id, second_generation.generation_id)
        self.assertEqual(first_generation.manifest_sha256, second_generation.manifest_sha256)
        self.assertEqual(
            first_generation.capture_artifact_sha256,
            lab.digest_object(first_generation.capture),
        )
        self.assertRegex(self.engine.pipeline_fingerprint, lab.HEX64)

    def test_crosswalk_and_citation_are_honest_about_coordinates(self) -> None:
        generation = self.engine._published_generation()
        document = generation.documents[("tenant-a", "refund-policy")]
        heading = next(item for item in document.crosswalk if item["projection_relation"] == "context_only")
        self.assertIsNone(heading["adapter_element_id"])
        public, _audit = self.query("q-tenant-a-refund")
        citation = public["claims"][0]["citations"][0]
        self.assertEqual("unavailable", citation["canonical_char_mapping"]["mapping_status"])
        self.assertEqual(lab.PARSER.LINE_COORDINATE_SPACE, citation["native_location"]["coordinate_space"])
        element_id = citation["adapter_element_id"]["value"]
        element = next(item for item in document.elements if item.element_id == element_id)
        lexical = citation["lexical_coordinate"]
        units = lab.CHUNK.lexical_units(element.text)
        exact = element.text[
            units[lexical["unit_start"]].char_start : units[lexical["unit_end"] - 1].char_end
        ]
        self.assertEqual(citation["exact"], exact)

    def test_public_and_protected_audit_validate_without_cross_projection_leakage(self) -> None:
        query = runtime_query(self.fixture, "q-tenant-a-refund")
        public, audit = self.engine.query(query)
        self.assertEqual([], self.engine.validate_evidence(query, public, audit))
        self.assertNotIn("authorization_revision", public)
        self.assertNotIn("index_generation_id", public)
        self.assertNotIn("subject_groups", public)
        self.assertEqual("protected", audit["visibility"])
        self.assertEqual(public["trace_id"], audit["trace_id"])

    def test_tenant_and_acl_filtering_happens_before_retrieval(self) -> None:
        query = runtime_query(self.fixture, "q-tenant-a-refund")
        observed: list[object] = []
        original = lab.CHUNK.retrieve

        def spy(text: str, chunks: object, **kwargs: object) -> object:
            observed.extend(chunks)
            return original(text, chunks, **kwargs)

        with patch.object(lab.CHUNK, "retrieve", side_effect=spy):
            self.engine.query(query)
        generation = self.engine._published_generation()
        keys = {generation.chunk_documents[chunk.chunk_id] for chunk in observed}
        self.assertEqual({("tenant-a", "refund-policy")}, keys)

    def test_hidden_document_update_does_not_change_denied_public_projection(self) -> None:
        before_public, before_audit = self.query("q-tenant-a-phone-denied")
        self.engine.stage_update(
            tenant_id="tenant-a",
            document_id="oncall-secret",
            source_sequence=2,
            source_version="v2",
            content="# On-call runbook\n\nThe internal on-call phone has changed to 010-5555-0199.\n",
            allowed_groups=["oncall"],
        )
        self.engine.project_and_publish()
        after_public, after_audit = self.query("q-tenant-a-phone-denied")
        self.assertEqual(before_public, after_public)
        self.assertNotEqual(before_audit["index_generation_id"], after_audit["index_generation_id"])


class IntegrityTamperTests(EngineCase):
    def test_self_consistent_parser_record_forgery_is_rejected_by_fresh_parse(self) -> None:
        old_generation_id = self.engine.published_generation_id
        old_generation_keys = set(self.engine.generations)
        key = next(key for key in self.engine.revision_inputs if key[:2] == ("tenant-a", "refund-policy"))
        original = self.engine.revision_inputs[key]
        record = copy.deepcopy(original.parser_record)
        paragraph = next(item for item in record["elements"] if item["kind"] == "paragraph")
        paragraph["text"] = "A forged refund policy with an internally consistent hash."
        paragraph["text_sha256"] = lab.digest_text(paragraph["text"])
        paragraph["element_id"] = lab._parser_element_identity(record, paragraph)
        forged = replace(
            original,
            parser_record=record,
            parser_record_sha256=lab.digest_object(record),
        )
        self.engine.revision_inputs[key] = forged
        with self.assertRaisesRegex(lab.IntegrationError, "freshly rebuilt"):
            self.engine.publish_capture(self.engine.capture_published_state())
        self.assertEqual(old_generation_id, self.engine.published_generation_id)
        self.assertEqual(old_generation_keys, set(self.engine.generations))
        self.assertEqual(
            "published", self.engine.generations[old_generation_id].status
        )

    def test_chunk_tamper_is_rejected_by_fresh_rebuild(self) -> None:
        generation = self.engine._published_generation()
        generation.chunks = (replace(generation.chunks[0], text="tampered"), *generation.chunks[1:])
        with self.assertRaisesRegex(lab.IntegrationError, "chunks cannot be freshly rebuilt"):
            self.engine._published_generation()

    def test_kb_canonical_revision_tamper_is_rejected(self) -> None:
        generation = self.engine._published_generation()
        revision_id = generation.documents[("tenant-a", "refund-policy")].kb_revision_id
        self.engine.connection.execute(
            "UPDATE revisions SET content = ? WHERE revision_id = ?",
            ("tampered", revision_id),
        )
        with self.assertRaisesRegex(lab.IntegrationError, "content hash"):
            self.query("q-tenant-a-refund")

    def test_search_projection_content_and_acl_tamper_are_rejected(self) -> None:
        generation = self.engine._published_generation()
        revision_id = generation.documents[("tenant-a", "refund-policy")].kb_revision_id
        self.engine.connection.execute(
            "UPDATE search_revisions SET content = ? WHERE revision_id = ?",
            ("tampered", revision_id),
        )
        with self.assertRaisesRegex(lab.IntegrationError, "search content hash"):
            self.query("q-tenant-a-refund")

    def test_generation_manifest_capture_and_crosswalk_tamper_are_rejected(self) -> None:
        generation = self.engine._published_generation()
        generation.manifest["publication_mode"] = "tampered"
        with self.assertRaises(lab.IntegrationError):
            self.engine._published_generation()

    def test_rehashed_public_citation_swap_still_fails_trusted_recompute(self) -> None:
        query = runtime_query(self.fixture, "q-tenant-a-refund")
        public, audit = self.engine.query(query)
        forged = copy.deepcopy(public)
        forged["claims"][0]["citations"][0]["document_id"] = "oncall-secret"
        rehash_public(forged)
        self.assertEqual(forged, lab.validate_public_projection(forged))
        self.assertIn("public_projection_mismatch", self.engine.validate_evidence(query, forged, audit))

    def test_trace_and_protected_audit_tamper_are_rejected(self) -> None:
        query = runtime_query(self.fixture, "q-tenant-a-refund")
        public, audit = self.engine.query(query)
        bad_public = copy.deepcopy(public)
        bad_public["trace_id"] = "xtr_" + "0" * 64
        self.assertTrue(any(item.startswith("public_shape:") for item in self.engine.validate_evidence(query, bad_public, audit)))
        bad_audit = copy.deepcopy(audit)
        bad_audit["query_binding_sha256"] = "0" * 64
        self.assertIn("protected_audit_mismatch", self.engine.validate_evidence(query, public, bad_audit))


class LifecycleTests(EngineCase):
    def test_checkpoint_advance_preserves_old_release_sidecar(self) -> None:
        key = ("tenant-a", "refund-policy")
        original = copy.deepcopy(self.engine.source_specs[key])
        before, _audit = self.query("q-tenant-a-refund")
        generation_id = self.engine.published_generation_id
        result = self.engine.stage_update(
            tenant_id=key[0],
            document_id=key[1],
            source_sequence=2,
            source_version=original["source_version"],
            content=original["content"],
            allowed_groups=original["allowed_groups"],
        )
        after, _audit = self.query("q-tenant-a-refund")
        self.assertEqual("checkpoint_advanced", result.action)
        self.assertEqual(before, after)
        self.assertEqual(generation_id, self.engine.published_generation_id)

    def test_stale_replay_after_pending_update_preserves_old_release_sidecar(self) -> None:
        key = ("tenant-a", "refund-policy")
        original = copy.deepcopy(self.engine.source_specs[key])
        before, _audit = self.query("q-tenant-a-refund")
        generation_id = self.engine.published_generation_id
        updated_content = "# Refund policy\n\nApproved refunds usually return to the original payment method within five business days.\n"
        updated = self.engine.stage_update(
            tenant_id=key[0],
            document_id=key[1],
            source_sequence=2,
            source_version="v2",
            content=updated_content,
            allowed_groups=original["allowed_groups"],
        )
        stale = self.engine.stage_update(
            tenant_id=key[0],
            document_id=key[1],
            source_sequence=1,
            source_version=original["source_version"],
            content=original["content"],
            allowed_groups=original["allowed_groups"],
        )
        after, _audit = self.query("q-tenant-a-refund")
        self.assertEqual("updated", updated.action)
        self.assertEqual("stale_ignored", stale.action)
        self.assertEqual(before, after)
        self.assertEqual("v2", self.engine.source_specs[key]["source_version"])
        self.assertEqual(generation_id, self.engine.published_generation_id)

    def test_same_acl_pending_update_keeps_old_release_visible(self) -> None:
        before, _audit = self.query("q-tenant-a-refund")
        generation_id = self.engine.published_generation_id
        result = self.engine.stage_update(
            tenant_id="tenant-a",
            document_id="refund-policy",
            source_sequence=2,
            source_version="v2",
            content="# Refund policy\n\nApproved refunds usually return to the original payment method within five business days.\n",
            allowed_groups=["employees"],
        )
        after, _audit = self.query("q-tenant-a-refund")
        self.assertEqual("updated", result.action)
        self.assertEqual(before, after)
        self.assertEqual(generation_id, self.engine.published_generation_id)

    def test_acl_tightening_denies_immediately_before_projection(self) -> None:
        self.engine.stage_update(
            tenant_id="tenant-a",
            document_id="refund-policy",
            source_sequence=2,
            source_version="v2",
            content="# Refund policy\n\nApproved refunds usually return to the original payment method within one to three business days.\n",
            allowed_groups=["managers"],
        )
        public, _audit = self.query("q-tenant-a-refund")
        self.assertEqual("insufficient_evidence", public["status"])
        self.assertEqual([], public["claims"])

    def test_delete_denies_immediately_and_new_generation_excludes_document(self) -> None:
        result = self.engine.delete_document(
            tenant_id="tenant-a", document_id="refund-policy", source_sequence=2
        )
        public, _audit = self.query("q-tenant-a-refund")
        self.assertEqual("deleted", result.action)
        self.assertEqual("insufficient_evidence", public["status"])
        generation = self.engine.project_and_publish()
        self.assertNotIn(("tenant-a", "refund-policy"), generation.documents)

    def test_stale_capture_cannot_publish_after_state_changes(self) -> None:
        capture = self.engine.capture_published_state()
        self.engine.stage_update(
            tenant_id="tenant-a",
            document_id="refund-policy",
            source_sequence=2,
            source_version="v2",
            content="# Refund policy\n\nApproved refunds usually return to the original payment method within five business days.\n",
            allowed_groups=["employees"],
        )
        with self.assertRaises((lab.IntegrationError, lab.KB.StoreError)):
            self.engine.publish_capture(capture)

    def test_resurrection_waits_for_projection_and_adapter_publication(self) -> None:
        self.engine.delete_document(
            tenant_id="tenant-a", document_id="refund-policy", source_sequence=2
        )
        self.engine.project_and_publish()
        result = self.engine.stage_update(
            tenant_id="tenant-a",
            document_id="refund-policy",
            source_sequence=3,
            source_version="v3",
            content="# Refund policy\n\nApproved refunds usually return to the original payment method within two business days.\n",
            allowed_groups=["employees"],
        )
        pending, _audit = self.query("q-tenant-a-refund")
        self.assertEqual("resurrected", result.action)
        self.assertEqual("insufficient_evidence", pending["status"])
        self.engine.project_and_publish()
        published, _audit = self.query("q-tenant-a-refund")
        self.assertEqual("answered", published["status"])
        self.assertIn("within two business days", published["claims"][0]["text"])

    def test_kb_cutover_before_adapter_publication_blocks_old_generation(self) -> None:
        old_generation = self.engine._published_generation()
        self.engine.stage_update(
            tenant_id="tenant-a",
            document_id="refund-policy",
            source_sequence=2,
            source_version="v2",
            content="# Refund policy\n\nApproved refunds usually return to the original payment method within five business days.\n",
            allowed_groups=["employees"],
        )
        lab.KB.drain_outbox(self.engine.connection)
        blocked, _audit = self.query("q-tenant-a-refund")
        self.assertEqual("insufficient_evidence", blocked["status"])
        new_generation = self.engine.project_and_publish()
        self.assertEqual("superseded", old_generation.status)
        self.assertNotEqual(old_generation.generation_id, new_generation.generation_id)


class EvaluationArtifactAndCliTests(EngineCase):
    def test_normal_and_failure_injected_release_gates(self) -> None:
        normal = lab.evaluate_fixture(self.engine, self.fixture)
        self.assertEqual("PASS", normal["summary"]["decision"])
        self.assertEqual([], lab.validate_artifact(normal))
        failure = lab.evaluate_fixture(
            self.engine, self.fixture, observed_failure="retrieval_unavailable"
        )
        self.assertEqual("BLOCK", failure["summary"]["decision"])
        self.assertEqual(len(failure["cases"]), failure["summary"]["failed"])
        self.assertEqual([], lab.validate_artifact(failure))

    def test_artifact_hash_counter_and_duplicate_query_tamper_are_rejected(self) -> None:
        artifact = lab.evaluate_fixture(self.engine, self.fixture)
        bad_hash = copy.deepcopy(artifact)
        bad_hash["cases"][0]["actual_status"] = "insufficient_evidence"
        self.assertTrue(lab.validate_artifact(bad_hash))
        bad_count = copy.deepcopy(artifact)
        bad_count["summary"]["passed"] = 0
        rehash_artifact(bad_count)
        self.assertTrue(lab.validate_artifact(bad_count))
        duplicate = copy.deepcopy(artifact)
        duplicate["cases"][1]["query_id"] = duplicate["cases"][0]["query_id"]
        rehash_artifact(duplicate)
        self.assertTrue(lab.validate_artifact(duplicate))

    def test_schema_is_draft_2020_12_strict_and_marks_python_recompute_boundary(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual("https://json-schema.org/draft/2020-12/schema", schema["$schema"])
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(schema["$defs"]["case"]["additionalProperties"])
        self.assertFalse(schema["$defs"]["summary"]["additionalProperties"])
        self.assertIn("capture_artifact_sha256", schema["required"])
        self.assertNotIn("uniqueItems", schema["$defs"]["stringArray"])
        self.assertIn("trusted recomputation", schema["description"])

    def test_cli_ask_outputs_only_public_projection(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = lab.main(["--fixture", str(FIXTURE_PATH), "ask", "--query-id", "q-tenant-a-refund"])
        value = json.loads(output.getvalue())
        self.assertEqual(0, code)
        self.assertEqual(set(value), {"schema_version", "query_id", "status", "claims", "trace_id"})

    def test_cli_requires_operator_view_and_returns_one_for_failure_gate(self) -> None:
        with self.assertRaisesRegex(lab.IntegrationError, "operator-view"):
            lab.main(["--fixture", str(FIXTURE_PATH), "inspect", "--query-id", "q-tenant-a-refund"])
        with self.assertRaisesRegex(lab.IntegrationError, "operator-view"):
            lab.main(["--fixture", str(FIXTURE_PATH), "manifest"])
        with self.assertRaisesRegex(lab.IntegrationError, "operator-view"):
            lab.main(["--fixture", str(FIXTURE_PATH), "evaluate"])
        output = io.StringIO()
        with redirect_stdout(output):
            code = lab.main(
                [
                    "--fixture",
                    str(FIXTURE_PATH),
                    "evaluate",
                    "--operator-view",
                    "--failure",
                    "retrieval_unavailable",
                ]
            )
        self.assertEqual(1, code)
        self.assertEqual("BLOCK", json.loads(output.getvalue())["summary"]["decision"])


if __name__ == "__main__":
    unittest.main()
