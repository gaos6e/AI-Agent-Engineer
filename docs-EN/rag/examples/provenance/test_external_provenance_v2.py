"""Adversarial, offline tests for the external provenance v2 consumer."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import external_provenance_v2 as consumer


HERE = Path(__file__).resolve().parent
INTEGRATION_ROOT = HERE.parent / "integration"
PRODUCER_PATH = INTEGRATION_ROOT / "cross_layer_adapter.py"
FIXTURE_PATH = INTEGRATION_ROOT / "cross-layer-fixture.json"


def load_producer() -> object:
    spec = importlib.util.spec_from_file_location(
        "external_provenance_v2_test_producer", PRODUCER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the local cross-layer producer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


producer = load_producer()


def rehash_embedded_payload(bundle: dict[str, object]) -> None:
    payload = {
        key: copy.deepcopy(value)
        for key, value in bundle.items()
        if key != "integrity"
    }
    integrity = bundle["integrity"]
    if not isinstance(integrity, dict):
        raise RuntimeError("test bundle integrity contract drift")
    integrity["payload_sha256"] = consumer.digest_object(payload)


def policy_for(
    bundle: dict[str, object],
    *,
    bundle_sha256: str | None = None,
    generation_id: str | None = None,
    pipeline_fingerprint: str | None = None,
    authorization_revision: str | None = None,
) -> consumer.TrustedImportPolicy:
    release = bundle["release"]
    if not isinstance(release, dict):
        raise RuntimeError("test bundle release contract drift")
    typed_generation = release["generation_id"]
    if not isinstance(typed_generation, dict):
        raise RuntimeError("test generation contract drift")
    return consumer.TrustedImportPolicy(
        expected_bundle_sha256=(
            bundle_sha256
            if bundle_sha256 is not None
            else consumer.trusted_bundle_sha256(bundle)
        ),
        expected_generation_id=(
            generation_id
            if generation_id is not None
            else typed_generation["value"]
        ),
        expected_pipeline_fingerprint=(
            pipeline_fingerprint
            if pipeline_fingerprint is not None
            else release["pipeline_fingerprint"]
        ),
        expected_authorization_revision=(
            authorization_revision
            if authorization_revision is not None
            else release["authorization_revision"]
        ),
    )


class ExternalProvenanceV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = producer.load_fixture(FIXTURE_PATH)
        with tempfile.TemporaryDirectory(prefix="external-v2-producer-") as directory:
            engine = producer.initialize_fixture(
                cls.fixture, Path(directory) / "sources"
            )
            try:
                cls.bundle = copy.deepcopy(
                    engine.export_external_provenance_bundle()
                )
            finally:
                engine.close()
        cls.serialized = consumer.serialize_external_bundle(cls.bundle)
        cls.policy = policy_for(cls.bundle)

    def mutate_and_stage(
        self, mutation: object, *, rehash: bool = True
    ) -> consumer.StagedExternalBundle:
        bundle = copy.deepcopy(self.bundle)
        mutation(bundle)
        if rehash:
            rehash_embedded_payload(bundle)
        return consumer.stage_external_bundle(
            consumer.serialize_external_bundle(bundle), policy_for(bundle)
        )

    def assert_mutation_rejected(
        self, code: str, mutation: object, *, rehash: bool = True
    ) -> consumer.ExternalProvenanceError:
        with self.assertRaises(consumer.ExternalProvenanceError) as caught:
            self.mutate_and_stage(mutation, rehash=rehash)
        self.assertEqual(code, caught.exception.code)
        self.assertIsInstance(caught.exception.path, str)
        self.assertTrue(caught.exception.path)
        return caught.exception

    def live_state(
        self,
        staged: consumer.StagedExternalBundle,
        *,
        authorization_revision: str | None = None,
        tombstone_state_sha256: str | None = None,
        blocked_documents: frozenset[tuple[str, str]] = frozenset(),
        audit_sink: consumer.ProtectedAuditSink | None = None,
    ) -> consumer.ConsumerLiveState:
        return consumer.ConsumerLiveState(
            authorization_revision or staged.authorization_revision,
            tombstone_state_sha256 or staged.tombstone_state_sha256,
            audit_sink or consumer.InMemoryProtectedAuditSink(),
            blocked_documents,
            {
                "employee-a": consumer.HostPrincipalGrant(
                    "tenant-a", ("employees",)
                ),
                "employee-a-2": consumer.HostPrincipalGrant(
                    "tenant-a", ("employees",)
                ),
                "employee-b": consumer.HostPrincipalGrant(
                    "tenant-b", ("employees",)
                ),
                "oncall-a": consumer.HostPrincipalGrant("tenant-a", ("oncall",)),
            },
        )

    def query(self, query_id: str) -> dict[str, object]:
        raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        item = next(
            query for query in raw["queries"] if query["query_id"] == query_id
        )
        return {
            key: copy.deepcopy(item[key])
            for key in (
                "query_id",
                "query",
                "top_k",
            )
        }

    def request_context(
        self, live: consumer.ConsumerLiveState, query_id: str
    ) -> consumer.TrustedRequestContext:
        principals = {
            "q-tenant-a-refund": "employee-a",
            "q-tenant-a-phone-denied": "employee-a",
            "q-tenant-a-phone-oncall": "oncall-a",
            "q-tenant-b-refund": "employee-b",
        }
        return live.issue_request_context(principals[query_id])

    def protected_audit(
        self, live: consumer.ConsumerLiveState, public: dict[str, object]
    ) -> dict[str, object]:
        sink = live.audit_sink
        if not isinstance(sink, consumer.InMemoryProtectedAuditSink):
            raise RuntimeError("test live state must use the in-memory protected sink")
        return sink.read(public["trace_id"])

    def test_01_trusted_roundtrip_is_staged_without_live_producer_state(self) -> None:
        staged = consumer.stage_external_bundle(self.serialized, self.policy)
        self.assertEqual("staged", staged.status)
        self.assertEqual(3, len(staged.documents))
        self.assertEqual(len(staged.chunks), len(staged.index_entries))
        self.assertEqual("document-revision-bridge", staged.evidence_level)

    def test_02_roundtrip_is_deterministic(self) -> None:
        first = consumer.stage_external_bundle(self.serialized, self.policy)
        second = consumer.stage_external_bundle(self.serialized, self.policy)
        self.assertEqual(first.bundle_sha256, second.bundle_sha256)
        self.assertEqual(first.generation_id, second.generation_id)
        self.assertEqual(first.chunks, second.chunks)

    def test_03_producer_published_bundle_cannot_skip_local_publish(self) -> None:
        staged = consumer.stage_external_bundle(self.serialized, self.policy)
        with self.assertRaises(consumer.ExternalProvenanceError) as caught:
            staged.query(self.query("q-tenant-a-refund"), self.live_state(staged))
        self.assertEqual("consumer_not_published", caught.exception.code)

    def test_04_local_publish_and_authorized_query_succeed(self) -> None:
        staged = consumer.stage_external_bundle(self.serialized, self.policy)
        live = self.live_state(staged)
        published = consumer.publish_staged_bundle(staged, live)
        public = published.query(
            self.query("q-tenant-a-refund"),
            self.request_context(live, "q-tenant-a-refund"),
            live,
        )
        audit = self.protected_audit(live, public)
        self.assertEqual("answered", public["status"])
        self.assertEqual(1, len(public["claims"]))
        self.assertEqual(1, audit["filter_summary"]["selected_chunks"])

    def test_05_public_and_protected_audit_outputs_are_separate(self) -> None:
        staged = consumer.stage_external_bundle(self.serialized, self.policy)
        live = self.live_state(staged)
        public = consumer.publish_staged_bundle(staged, live).query(
            self.query("q-tenant-a-refund"),
            self.request_context(live, "q-tenant-a-refund"),
            live,
        )
        audit = self.protected_audit(live, public)
        public_text = consumer.canonical_json(public)
        self.assertNotIn("authorization_revision", public)
        self.assertNotIn("filter_summary", public)
        self.assertNotIn("index_generation_id", public)
        self.assertNotIn("010-5555-0188", public_text)
        self.assertNotIn("kb://", public_text)
        self.assertEqual("protected", audit["visibility"])
        self.assertTrue(audit["source_bindings"][0]["source_uri"].startswith("kb://"))
        citation = public["claims"][0]["citations"][0]
        self.assertEqual("unavailable", citation["canonical_mapping"]["status"])

    def test_06_tenant_acl_and_live_filters_run_before_scoring(self) -> None:
        staged = consumer.stage_external_bundle(self.serialized, self.policy)
        live = self.live_state(staged)
        published = consumer.publish_staged_bundle(staged, live)
        with patch.object(
            consumer.CHUNK, "retrieve", wraps=consumer.CHUNK.retrieve
        ) as retrieve:
            public = published.query(
                self.query("q-tenant-a-refund"),
                self.request_context(live, "q-tenant-a-refund"),
                live,
            )
        audit = self.protected_audit(live, public)
        candidate_chunks = retrieve.call_args.args[1]
        self.assertEqual(1, len(candidate_chunks))
        self.assertEqual(("employees",), candidate_chunks[0].acl)
        self.assertEqual("answered", public["status"])
        self.assertEqual(
            {
                "all_chunks": 3,
                "tenant_chunks": 2,
                "live_chunks": 2,
                "acl_chunks": 1,
                "selected_chunks": 1,
            },
            audit["filter_summary"],
        )

    def test_07_self_rehashed_tamper_fails_original_out_of_band_pin(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        bundle["documents"][0]["document_id"] = "tampered-document"
        rehash_embedded_payload(bundle)
        with self.assertRaises(consumer.ExternalProvenanceError) as caught:
            consumer.stage_external_bundle(
                consumer.serialize_external_bundle(bundle), self.policy
            )
        self.assertEqual("trusted_bundle_digest_mismatch", caught.exception.code)

    def test_08_embedded_self_hash_is_only_a_consistency_check(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        bundle["documents"][0]["document_id"] = "tampered-document"
        with self.assertRaises(consumer.ExternalProvenanceError) as caught:
            consumer.stage_external_bundle(
                consumer.serialize_external_bundle(bundle), policy_for(bundle)
            )
        self.assertEqual("payload_hash_mismatch", caught.exception.code)

    def test_09_generation_pipeline_and_authorization_are_independently_pinned(self) -> None:
        cases = (
            (
                {"generation_id": "xgen_" + "0" * 64},
                "trusted_generation_mismatch",
            ),
            ({"pipeline_fingerprint": "0" * 64}, "trusted_pipeline_mismatch"),
            ({"authorization_revision": "authz-v999"}, "trusted_authorization_mismatch"),
        )
        for override, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaises(consumer.ExternalProvenanceError) as caught:
                    consumer.stage_external_bundle(
                        self.serialized, policy_for(self.bundle, **override)
                    )
                self.assertEqual(expected, caught.exception.code)

    def test_10_json_boundary_rejects_in_memory_objects(self) -> None:
        with self.assertRaises(consumer.ExternalProvenanceError) as caught:
            consumer.stage_external_bundle(self.bundle, self.policy)
        self.assertEqual("json_boundary_required", caught.exception.code)

    def test_11_duplicate_and_truncated_json_are_structured_failures(self) -> None:
        malformed = (
            ('{"a":1,"a":2}', "duplicate_json_key"),
            (self.serialized[:-1], "invalid_json"),
        )
        for raw, expected in malformed:
            with self.subTest(expected=expected):
                with self.assertRaises(consumer.ExternalProvenanceError) as caught:
                    consumer.stage_external_bundle(raw, self.policy)
                self.assertEqual(expected, caught.exception.code)

    def test_12_non_standard_and_float_numbers_are_rejected(self) -> None:
        malformed = (
            ("{\"value\":NaN}", "non_standard_number"),
            ("{\"value\":1.5}", "float_not_supported"),
            (r'{"value":"\ud800"}', "invalid_unicode"),
            (r'{"\ud800":1}', "invalid_unicode"),
        )
        for raw, expected in malformed:
            with self.subTest(expected=expected):
                with self.assertRaises(consumer.ExternalProvenanceError) as caught:
                    consumer.stage_external_bundle(raw, self.policy)
                self.assertEqual(expected, caught.exception.code)

    def test_13_unknown_fields_fail_closed(self) -> None:
        self.assert_mutation_rejected(
            "fields_mismatch", lambda bundle: bundle.update({"unexpected": True})
        )

    def test_14_wrong_and_oversize_external_ids_never_raise_type_error(self) -> None:
        mutations = (
            lambda bundle: bundle["documents"][0]["logical_source_id"].update(
                {"value": []}
            ),
            lambda bundle: bundle["documents"][0]["logical_source_id"].update(
                {"value": "xsrc_" + "a" * 4_000}
            ),
        )
        expected = ("id_type_invalid", "id_value_invalid")
        for mutation, code in zip(mutations, expected, strict=True):
            with self.subTest(code=code):
                self.assert_mutation_rejected(code, mutation)

    def test_15_typed_identity_scheme_mismatch_is_rejected(self) -> None:
        self.assert_mutation_rejected(
            "id_scheme_mismatch",
            lambda bundle: bundle["documents"][0]["logical_source_id"].update(
                {"scheme": consumer.CHUNK_ID_SCHEME}
            ),
        )

    def test_16_cross_tenant_index_route_swap_is_rejected(self) -> None:
        def swap_routes(bundle: dict[str, object]) -> None:
            entries = bundle["index_entries"]
            first = next(item for item in entries if item["tenant_id"] == "tenant-a")
            second = next(item for item in entries if item["tenant_id"] == "tenant-b")
            first["tenant_id"], second["tenant_id"] = (
                second["tenant_id"],
                first["tenant_id"],
            )
            first["document_id"], second["document_id"] = (
                second["document_id"],
                first["document_id"],
            )

        self.assert_mutation_rejected("entry_route_mismatch", swap_routes)

    def test_17_canonical_mapping_overclaim_is_rejected(self) -> None:
        self.assert_mutation_rejected(
            "evidence_level_overclaim",
            lambda bundle: bundle["documents"][0]["crosswalk"][0][
                "canonical_mapping"
            ].update({"status": "available"}),
        )

    def test_18_adapter_quote_must_equal_fresh_parser_element(self) -> None:
        self.assert_mutation_rejected(
            "element_text_mismatch",
            lambda bundle: bundle["documents"][0]["adapter_elements"][0].update(
                {"text": "Forged exact citation."}
            ),
        )

    def test_19_lexical_coordinates_must_be_in_element_bounds(self) -> None:
        self.assert_mutation_rejected(
            "chunk_validation_failed",
            lambda bundle: bundle["chunks"][0]["element_spans"][0].update(
                {"unit_end": 99_999}
            ),
        )

    def test_20_orphan_and_duplicate_crosswalk_rows_are_rejected(self) -> None:
        def orphan(bundle: dict[str, object]) -> None:
            bundle["documents"][0]["crosswalk"][0]["native_element_id"][
                "value"
            ] = "elm_" + "0" * 64

        def duplicate(bundle: dict[str, object]) -> None:
            rows = bundle["documents"][0]["crosswalk"]
            rows.append(copy.deepcopy(rows[0]))

        for mutation, code in (
            (orphan, "orphan_crosswalk"),
            (duplicate, "duplicate_crosswalk"),
        ):
            with self.subTest(code=code):
                self.assert_mutation_rejected(code, mutation)

    def test_21_chunk_acl_and_access_bindings_are_rejected(self) -> None:
        mutations = (
            (
                "chunk_acl_mismatch",
                lambda bundle: bundle["chunks"][0].update(
                    {"allowed_groups": ["employees", "unexpected"]}
                ),
            ),
            (
                "chunk_access_binding_mismatch",
                lambda bundle: bundle["chunks"][0].update(
                    {"access_snapshot_sha256": "0" * 64}
                ),
            ),
        )
        for code, mutation in mutations:
            with self.subTest(code=code):
                self.assert_mutation_rejected(code, mutation)

    def test_22_entry_retrieval_and_identity_bindings_are_rejected(self) -> None:
        mutations = (
            (
                "entry_retrieval_binding_mismatch",
                lambda bundle: bundle["index_entries"][0].update(
                    {"retrieval_sha256": "0" * 64}
                ),
            ),
            (
                "entry_identity_mismatch",
                lambda bundle: bundle["index_entries"][0]["index_entry_id"].update(
                    {"value": "idx_" + "0" * 64}
                ),
            ),
        )
        for code, mutation in mutations:
            with self.subTest(code=code):
                self.assert_mutation_rejected(code, mutation)

    def test_23_chunk_and_entry_coverage_must_be_exact(self) -> None:
        self.assert_mutation_rejected(
            "generation_coverage_mismatch",
            lambda bundle: bundle["index_entries"].pop(),
        )

    def test_24_generation_document_and_entry_refs_must_cover_release(self) -> None:
        mutations = (
            lambda bundle: bundle["release"]["document_refs"].pop(),
            lambda bundle: bundle["release"]["entry_refs"].pop(),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assert_mutation_rejected(
                    "generation_coverage_mismatch", mutation
                )

    def test_25_raw_and_canonical_representations_are_rebuilt(self) -> None:
        def tamper_raw(bundle: dict[str, object]) -> None:
            document = next(
                item
                for item in bundle["documents"]
                if "refund" in item["raw_representation"]["text"]
            )
            document["raw_representation"]["text"] = document[
                "raw_representation"
            ]["text"].replace("refund", "return", 1)

        self.assert_mutation_rejected(
            "raw_hash_mismatch",
            tamper_raw,
        )

    def test_26_parser_record_tamper_is_rejected(self) -> None:
        self.assert_mutation_rejected(
            "parser_record_hash_mismatch",
            lambda bundle: bundle["documents"][0]["parser_artifact"][
                "record"
            ].update({"source_id": "tampered-source"}),
        )

    def test_27_publish_requires_current_authorization(self) -> None:
        staged = consumer.stage_external_bundle(self.serialized, self.policy)
        with self.assertRaises(consumer.ExternalProvenanceError) as caught:
            consumer.publish_staged_bundle(
                staged,
                self.live_state(staged, authorization_revision="authz-v999"),
            )
        self.assertEqual("live_authorization_mismatch", caught.exception.code)

    def test_28_publish_requires_current_tombstone_state(self) -> None:
        staged = consumer.stage_external_bundle(self.serialized, self.policy)
        with self.assertRaises(consumer.ExternalProvenanceError) as caught:
            consumer.publish_staged_bundle(
                staged, self.live_state(staged, tombstone_state_sha256="0" * 64)
            )
        self.assertEqual("live_tombstone_mismatch", caught.exception.code)

    def test_29_publish_rejects_any_blocked_release_document(self) -> None:
        staged = consumer.stage_external_bundle(self.serialized, self.policy)
        blocked = frozenset({("tenant-a", "refund-policy")})
        with self.assertRaises(consumer.ExternalProvenanceError) as caught:
            consumer.publish_staged_bundle(
                staged, self.live_state(staged, blocked_documents=blocked)
            )
        self.assertEqual("live_document_blocked", caught.exception.code)

    def test_30_query_rechecks_live_deny_after_publication(self) -> None:
        staged = consumer.stage_external_bundle(self.serialized, self.policy)
        clean = self.live_state(staged)
        published = consumer.publish_staged_bundle(staged, clean)
        denied = self.live_state(
            staged,
            blocked_documents=frozenset({("tenant-a", "refund-policy")}),
        )
        public = published.query(
            self.query("q-tenant-a-refund"),
            self.request_context(denied, "q-tenant-a-refund"),
            denied,
        )
        audit = self.protected_audit(denied, public)
        self.assertEqual("insufficient_evidence", public["status"])
        self.assertEqual([], public["claims"])
        self.assertEqual(0, audit["filter_summary"]["selected_chunks"])

    def test_31_query_fails_closed_on_live_contract_drift(self) -> None:
        staged = consumer.stage_external_bundle(self.serialized, self.policy)
        clean = self.live_state(staged)
        published = consumer.publish_staged_bundle(staged, clean)
        drifted = self.live_state(staged, authorization_revision="authz-v999")
        public = published.query(
            self.query("q-tenant-a-refund"),
            self.request_context(drifted, "q-tenant-a-refund"),
            drifted,
        )
        audit = self.protected_audit(drifted, public)
        self.assertEqual("insufficient_evidence", public["status"])
        self.assertEqual([], public["claims"])
        self.assertEqual(
            "consumer_live_state_mismatch", audit["failure"]["code"]
        )

    def test_32_knowledge_source_and_build_state_are_rebuilt(self) -> None:
        mutations = (
            (
                "knowledge_source_state_mismatch",
                lambda bundle: bundle["documents"][0]["knowledge_revision"][
                    "identity_inputs"
                ].update({"source_state_hash": "0" * 64}),
            ),
            (
                "knowledge_build_state_mismatch",
                lambda bundle: bundle["documents"][0]["knowledge_revision"][
                    "identity_inputs"
                ].update({"build_state_hash": "0" * 64}),
            ),
        )
        for code, mutation in mutations:
            with self.subTest(code=code):
                # mutate_and_stage recomputes the embedded payload hash and the
                # test's out-of-band whole-bundle policy.  The semantic rebuild
                # must still reject forged KB state inputs.
                self.assert_mutation_rejected(code, mutation)

    def test_33_knowledge_state_algorithm_is_versioned(self) -> None:
        self.assert_mutation_rejected(
            "contract_revision_mismatch",
            lambda bundle: bundle["producer_contract"].update(
                {"knowledge_state_revision": "knowledge-store/source-build-state/v999"}
            ),
        )

    def test_34_excessive_json_depth_is_a_structured_failure(self) -> None:
        deeply_nested = "[" * 1_200 + "0" + "]" * 1_200
        with self.assertRaises(consumer.ExternalProvenanceError) as caught:
            consumer.strict_json_loads(deeply_nested)
        self.assertEqual("json_depth_exceeded", caught.exception.code)

    def test_35_stage_publication_and_context_constructors_are_not_public(self) -> None:
        constructors = (
            (
                lambda: consumer.StagedExternalBundle(status="staged"),
                "validated_stage_factory_required",
            ),
            (
                lambda: consumer.PublishedExternalBundle(bundle=None),
                "local_publication_factory_required",
            ),
            (
                lambda: consumer.TrustedRequestContext(
                    principal_id="attacker",
                    tenant_id="tenant-a",
                    subject_groups=("oncall",),
                    authorization_revision="authz-v1",
                ),
                "trusted_request_context_factory_required",
            ),
        )
        for constructor, code in constructors:
            with self.subTest(code=code):
                with self.assertRaises(consumer.ExternalProvenanceError) as caught:
                    constructor()
                self.assertEqual(code, caught.exception.code)

        forged = object.__new__(consumer.StagedExternalBundle)
        object.__setattr__(forged, "status", "staged")
        with self.assertRaises(consumer.ExternalProvenanceError) as caught:
            consumer.publish_staged_bundle(
                forged,
                consumer.ConsumerLiveState(
                    "authz-v1", "0" * 64, consumer.InMemoryProtectedAuditSink()
                ),
            )
        self.assertEqual("staged_bundle_required", caught.exception.code)

    def test_36_query_identity_is_host_resolved_not_self_claimed(self) -> None:
        staged = consumer.stage_external_bundle(self.serialized, self.policy)
        live = self.live_state(staged)
        published = consumer.publish_staged_bundle(staged, live)
        request = self.query("q-tenant-a-phone-oncall")
        employee_context = live.issue_request_context("employee-a")
        public = published.query(request, employee_context, live)
        self.assertEqual("insufficient_evidence", public["status"])

        self_claimed = {
            **request,
            "tenant_id": "tenant-a",
            "subject_groups": ["oncall"],
            "authorization_revision": staged.authorization_revision,
        }
        with self.assertRaises(consumer.ExternalProvenanceError) as caught:
            published.query(self_claimed, employee_context, live)
        self.assertEqual("fields_mismatch", caught.exception.code)

        with self.assertRaises(consumer.ExternalProvenanceError) as caught:
            published.query(request, {"subject_groups": ["oncall"]}, live)
        self.assertEqual("trusted_request_context_required", caught.exception.code)

        other_snapshot = self.live_state(staged)
        with self.assertRaises(consumer.ExternalProvenanceError) as caught:
            published.query(
                request,
                other_snapshot.issue_request_context("oncall-a"),
                live,
            )
        self.assertEqual("trusted_request_context_required", caught.exception.code)

    def test_37_long_sensitive_source_uri_is_protected_and_schema_aligned(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        sensitive_uri = "https://example.invalid/kb?private_locator=" + "s" * 340
        fixture["documents"][0]["source_uri"] = sensitive_uri
        fixture["fixture_model_sha256"] = producer.fixture_model_sha256(fixture)
        with tempfile.TemporaryDirectory(prefix="external-v2-uri-") as directory:
            engine = producer.initialize_fixture(fixture, Path(directory) / "sources")
            try:
                bundle = engine.export_external_provenance_bundle()
            finally:
                engine.close()
        staged = consumer.stage_external_bundle(
            consumer.serialize_external_bundle(bundle), policy_for(bundle)
        )
        live = self.live_state(staged)
        public = consumer.publish_staged_bundle(staged, live).query(
            self.query("q-tenant-a-refund"),
            self.request_context(live, "q-tenant-a-refund"),
            live,
        )
        audit = self.protected_audit(live, public)
        self.assertNotIn(sensitive_uri, consumer.canonical_json(public))
        self.assertEqual(sensitive_uri, audit["source_bindings"][0]["source_uri"])

        schema = json.loads(
            (HERE / "external-provenance-bundle-v2.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(1000, schema["$defs"]["sourceUri"]["maxLength"])
        self.assertEqual(
            {"$ref": "#/$defs/sourceUri"},
            schema["$defs"]["sourceEvent"]["properties"]["source_uri"],
        )
        self.assertEqual(
            {"$ref": "#/$defs/sourceUri"},
            schema["$defs"]["identityInputs"]["properties"]["source_uri"],
        )

    def test_38_portable_paths_and_materialization_fail_closed(self) -> None:
        invalid_paths = (
            "D:/escape.md",
            "folder/a:b.md",
            "CON.md",
            "folder/" + "a" * 121 + ".md",
        )
        for value in invalid_paths:
            with self.subTest(value=value):
                with self.assertRaises(consumer.ExternalProvenanceError) as caught:
                    consumer._relative_markdown_path(value, "relative_path")
                self.assertEqual("relative_path_invalid", caught.exception.code)

        with patch.object(Path, "open", side_effect=OSError("synthetic I/O denial")):
            with self.assertRaises(consumer.ExternalProvenanceError) as caught:
                consumer.stage_external_bundle(self.serialized, self.policy)
        self.assertEqual("fresh_parser_materialization_failed", caught.exception.code)

    def test_39_crosswalk_and_adapter_order_are_semantic(self) -> None:
        self.assert_mutation_rejected(
            "crosswalk_order_mismatch",
            lambda bundle: bundle["documents"][0]["crosswalk"].reverse(),
        )

        fixture = copy.deepcopy(self.fixture)
        fixture["documents"][0]["content"] = (
            "# Refund policy\n\nThe first paragraph explains review requirements.\n\nThe second paragraph explains refund timing.\n"
        )
        fixture["fixture_model_sha256"] = producer.fixture_model_sha256(fixture)
        with tempfile.TemporaryDirectory(prefix="external-v2-order-") as directory:
            engine = producer.initialize_fixture(fixture, Path(directory) / "sources")
            try:
                bundle = engine.export_external_provenance_bundle()
            finally:
                engine.close()
        document = next(
            item for item in bundle["documents"] if item["document_id"] == "refund-policy"
        )
        self.assertGreaterEqual(len(document["adapter_elements"]), 2)
        document["adapter_elements"].reverse()
        rehash_embedded_payload(bundle)
        with self.assertRaises(consumer.ExternalProvenanceError) as caught:
            consumer.stage_external_bundle(
                consumer.serialize_external_bundle(bundle), policy_for(bundle)
            )
        self.assertEqual("adapter_element_order_mismatch", caught.exception.code)

    def test_40_producer_snapshot_is_rebuilt_and_manifest_ref_is_explicitly_opaque(self) -> None:
        self.assert_mutation_rejected(
            "producer_snapshot_hash_mismatch",
            lambda bundle: bundle["documents"][0]["knowledge_revision"].update(
                {"producer_snapshot_sha256": "0" * 64}
            ),
        )
        self.assert_mutation_rejected(
            "producer_reference_contract_mismatch",
            lambda bundle: bundle["release"][
                "producer_release_manifest_reference"
            ].update({"verification": "verified"}),
        )

    def test_41_public_query_requires_protected_audit_delivery(self) -> None:
        class FailingSink(consumer.ProtectedAuditSink):
            def write(self, audit: object) -> None:
                raise OSError("synthetic protected-store outage")

        staged = consumer.stage_external_bundle(self.serialized, self.policy)
        live = self.live_state(staged, audit_sink=FailingSink())
        published = consumer.publish_staged_bundle(staged, live)
        with self.assertRaises(consumer.ExternalProvenanceError) as caught:
            published.query(
                self.query("q-tenant-a-refund"),
                self.request_context(live, "q-tenant-a-refund"),
                live,
            )
        self.assertEqual("protected_audit_write_failed", caught.exception.code)

    def test_42_trace_identity_is_unique_per_host_issued_request(self) -> None:
        staged = consumer.stage_external_bundle(self.serialized, self.policy)
        live = self.live_state(staged)
        published = consumer.publish_staged_bundle(staged, live)
        request = self.query("q-tenant-a-refund")
        first = published.query(
            request, live.issue_request_context("employee-a"), live
        )
        second = published.query(
            request, live.issue_request_context("employee-a-2"), live
        )
        self.assertEqual(first["claims"], second["claims"])
        self.assertNotEqual(first["trace_id"], second["trace_id"])
        first_audit = self.protected_audit(live, first)
        second_audit = self.protected_audit(live, second)
        self.assertNotEqual(
            first_audit["request_context_id"], second_audit["request_context_id"]
        )
        self.assertEqual("employee-a", first_audit["principal_id"])
        self.assertEqual("employee-a-2", second_audit["principal_id"])


if __name__ == "__main__":
    unittest.main()
