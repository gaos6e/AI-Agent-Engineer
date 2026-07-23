"""Tests for the strict offline RAG teaching pipeline."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


EXAMPLES_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLES_DIR))

import offline_cited_qa as rag  # noqa: E402


FIXTURE_PATH = EXAMPLES_DIR / "rag-fixture.json"
SCRIPT_PATH = EXAMPLES_DIR / "offline_cited_qa.py"


class FixtureContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = rag.load_fixture(FIXTURE_PATH)

    def test_fixture_loads(self) -> None:
        self.assertEqual([], rag.validate_fixture(self.fixture))
        self.assertEqual("2.0", self.fixture["schema_version"])
        self.assertEqual(
            "offline-rag-harness-v3",
            self.fixture["evaluation_policy"]["harness_revision"],
        )

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema_version":"1.0","schema_version":"2.0"}', encoding="utf-8")
            with self.assertRaises(rag.FixtureError):
                rag.load_fixture(path)

    def test_nonfinite_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nan.json"
            path.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaises(rag.FixtureError):
                rag.load_fixture(path)

    def test_surrogate_and_huge_integer_are_fixture_contract_errors(self) -> None:
        with self.assertRaisesRegex(rag.FixtureError, "invalid Unicode"):
            rag.strict_json_loads(r'{"value":"\ud800"}')

        changed = copy.deepcopy(self.fixture)
        changed["evaluation_policy"]["min_case_pass_rate"] = 10**400
        errors = rag.validate_fixture(changed)
        self.assertTrue(any("min_case_pass_rate" in error for error in errors))
        self.assertFalse(rag._finite_number(10**400))

    def test_fixture_size_and_json_depth_are_bounded_before_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized.json"
            path.write_bytes(b" " * (rag.MAX_FIXTURE_BYTES + 1))
            with self.assertRaisesRegex(rag.FixtureError, "must not exceed"):
                rag.load_fixture(path)

        nested = "[" * (rag.MAX_JSON_DEPTH + 1) + "0" + "]" * (
            rag.MAX_JSON_DEPTH + 1
        )
        with self.assertRaisesRegex(rag.FixtureError, "nesting"):
            rag.strict_json_loads(nested)

    def test_fixture_io_error_does_not_echo_local_path(self) -> None:
        missing = Path("do-not-disclose-this-local-path") / "fixture.json"
        with self.assertRaises(rag.FixtureError) as captured:
            rag.load_fixture(missing)
        self.assertNotIn(str(missing), str(captured.exception))

    def test_unknown_root_field_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["unexpected"] = True
        self.assertTrue(any("root" in error for error in rag.validate_fixture(changed)))

    def test_pipeline_limits_must_be_positive_plain_ints(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["pipeline"]["retrieval_limit"] = True
        self.assertTrue(any("retrieval_limit" in error for error in rag.validate_fixture(changed)))

    def test_pipeline_and_fixture_collection_limits_are_bounded(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["pipeline"]["retrieval_limit"] = rag.MAX_STAGE_LIMIT + 1
        self.assertTrue(
            any("retrieval_limit" in error for error in rag.validate_fixture(changed))
        )

        changed = copy.deepcopy(self.fixture)
        changed["documents"] = changed["documents"] * (rag.MAX_DOCUMENTS + 1)
        self.assertTrue(any("documents" in error for error in rag.validate_fixture(changed)))

    def test_fact_statement_must_exist_verbatim(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["documents"][0]["facts"][0]["statement"] = "This sentence does not exist."
        self.assertTrue(any("must occur verbatim" in error for error in rag.validate_fixture(changed)))

    def test_duplicate_fact_id_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["documents"][1]["facts"][0]["fact_id"] = "F-refund-current"
        self.assertTrue(any("duplicate fact id" in error for error in rag.validate_fixture(changed)))

    def test_unknown_expected_fact_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["queries"][0]["expected_fact_ids"] = ["F-does-not-exist"]
        self.assertTrue(any("unknown fact" in error for error in rag.validate_fixture(changed)))

    def test_reversed_effective_window_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["documents"][0]["effective_to"] = "2025-01-01"
        self.assertTrue(any("[effective_from" in error for error in rag.validate_fixture(changed)))

    def test_empty_effective_window_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["documents"][0]["effective_to"] = changed["documents"][0]["effective_from"]
        self.assertTrue(any("[effective_from" in error for error in rag.validate_fixture(changed)))

    def test_acl_must_be_sorted_and_unique(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["documents"][0]["acl"] = ["public", "public"]
        self.assertTrue(any("must be sorted and unique" in error for error in rag.validate_fixture(changed)))

    def test_subject_groups_are_trusted_nonempty_resolved_groups(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["queries"][0]["subject_groups"] = []
        self.assertTrue(any("public access" in error for error in rag.validate_fixture(changed)))

    def test_forbidden_canary_must_come_from_forbidden_document(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["queries"][0]["forbidden_output_substrings"] = ["missing secret"]
        self.assertTrue(any("test canary" in error for error in rag.validate_fixture(changed)))

    def test_evaluation_threshold_rejects_nonfinite_number(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["evaluation_policy"]["min_status_accuracy"] = float("nan")
        self.assertTrue(any("finite number" in error for error in rag.validate_fixture(changed)))

    def test_json_type_errors_are_reported_as_fixture_contract_errors(self) -> None:
        mutations = (
            ("document id", lambda value: value["documents"][0].__setitem__("id", [])),
            ("document status", lambda value: value["documents"][0].__setitem__("status", [])),
            ("query route", lambda value: value["queries"][0].__setitem__("route", {})),
            (
                "query expected status",
                lambda value: value["queries"][0].__setitem__("expected_status", []),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                changed = copy.deepcopy(self.fixture)
                mutate(changed)
                errors = rag.validate_fixture(changed)
                self.assertTrue(errors)


class PipelineComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = rag.load_fixture(FIXTURE_PATH)
        self.documents = self.fixture["documents"]

    def query(self, query_id: str) -> dict[str, object]:
        return next(query for query in self.fixture["queries"] if query["id"] == query_id)

    def test_features_cover_cjk_and_ascii(self) -> None:
        features = rag.text_features("RAG \u9000\u6b3e")
        self.assertIn("a:rag", features)
        self.assertIn("c2:\u9000\u6b3e", features)

    def test_guest_filter_is_fail_closed(self) -> None:
        visible, summary, decisions = rag.filter_documents(
            self.documents, self.query("Q-phone-guest")
        )
        visible_ids = {document["id"] for document in visible}
        self.assertNotIn("S3", visible_ids)
        self.assertNotIn("S4", visible_ids)
        self.assertNotIn("S7", visible_ids)
        self.assertIn("acl_denied", decisions["S3"])
        self.assertGreaterEqual(summary["filtered"], 3)

    def test_oncall_group_unlocks_only_same_tenant_document(self) -> None:
        visible, _, _ = rag.filter_documents(self.documents, self.query("Q-phone-oncall"))
        visible_ids = {document["id"] for document in visible}
        self.assertIn("S3", visible_ids)
        self.assertNotIn("S7", visible_ids)

    def test_resolved_public_group_can_read_public_documents(self) -> None:
        visible, _, _ = rag.filter_documents(self.documents, self.query("Q-refund"))
        visible_ids = {document["id"] for document in visible}
        self.assertIn("S1", visible_ids)
        self.assertIn("S2", visible_ids)

    def test_effective_to_is_exclusive(self) -> None:
        query = copy.deepcopy(self.query("Q-refund"))
        query["as_of"] = "2026-01-01"
        visible, _, decisions = rag.filter_documents(self.documents, query)
        self.assertNotIn("S4", {document["id"] for document in visible})
        self.assertIn("outside_effective_window", decisions["S4"])

    def test_retrieval_uses_only_filtered_documents(self) -> None:
        query = self.query("Q-refund")
        visible, _, _ = rag.filter_documents(self.documents, query)
        candidates = rag.retrieve(query, visible, 20)
        candidate_ids = {candidate["document_id"] for candidate in candidates}
        self.assertIn("S1", candidate_ids)
        self.assertNotIn("S3", candidate_ids)
        self.assertNotIn("S4", candidate_ids)
        self.assertNotIn("S7", candidate_ids)

    def test_topic_reranker_places_matching_fact_first(self) -> None:
        query = self.query("Q-duplicate")
        visible, _, _ = rag.filter_documents(self.documents, query)
        candidates = rag.retrieve(query, visible, 20)
        by_id = {document["id"]: document for document in visible}
        reranked = rag.rerank(query, candidates, by_id, use_fallback=False)
        self.assertEqual("S2", reranked[0]["document_id"])
        self.assertTrue(reranked[0]["topic_match"])

    def test_reranker_fallback_preserves_retrieval_order(self) -> None:
        query = self.query("Q-refund")
        visible, _, _ = rag.filter_documents(self.documents, query)
        candidates = rag.retrieve(query, visible, 20)
        by_id = {document["id"]: document for document in visible}
        reranked = rag.rerank(query, candidates, by_id, use_fallback=True)
        self.assertEqual(
            [candidate["document_id"] for candidate in candidates],
            [candidate["document_id"] for candidate in reranked],
        )

    def test_context_deduplicates_canonical_document(self) -> None:
        by_id = {document["id"]: document for document in self.documents}
        ranked = [
            {"document_id": "S1", "rank": 1, "score": 3.0},
            {"document_id": "S8", "rank": 2, "score": 2.0},
        ]
        selected, dropped, _ = rag.select_context(ranked, by_id, 3, 1000)
        self.assertEqual(["S1"], [item["document_id"] for item in selected])
        self.assertEqual("canonical_duplicate", dropped[0]["reason"])

    def test_context_budget_is_enforced(self) -> None:
        by_id = {document["id"]: document for document in self.documents}
        ranked = [{"document_id": "S1", "rank": 1, "score": 3.0}]
        selected, dropped, chars = rag.select_context(ranked, by_id, 3, 1)
        self.assertEqual([], selected)
        self.assertEqual(0, chars)
        self.assertEqual("character_budget", dropped[0]["reason"])


class EndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = rag.load_fixture(FIXTURE_PATH)

    def query(self, query_id: str) -> dict[str, object]:
        return next(query for query in self.fixture["queries"] if query["id"] == query_id)

    def execution(self, query_id: str, failure: str = "none") -> dict[str, object]:
        return rag.execute_pipeline(self.fixture, query_id, failure=failure)

    def test_refund_answer_is_extractively_cited(self) -> None:
        result = rag.run_pipeline(self.fixture, "Q-refund")
        self.assertEqual("answered", result["status"])
        self.assertEqual(
            "After a refund is approved, it usually returns to the original payment method within one to three business days.",
            result["answer"],
        )
        self.assertEqual("F-refund-current", result["citations"][0]["fact_id"])

    def test_duplicate_charge_answer(self) -> None:
        result = rag.run_pipeline(self.fixture, "Q-duplicate")
        self.assertEqual("answered", result["status"])
        self.assertEqual("F-duplicate-action", result["citations"][0]["fact_id"])

    def test_guest_phone_query_refuses_without_leak(self) -> None:
        result = rag.run_pipeline(self.fixture, "Q-phone-guest")
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertEqual("insufficient_evidence", result["status"])
        self.assertNotIn("S3", serialized)
        self.assertNotIn("010-5550-0100", serialized)

    def test_authorized_phone_query_answers(self) -> None:
        result = rag.run_pipeline(self.fixture, "Q-phone-oncall")
        self.assertEqual("answered", result["status"])
        self.assertIn("010-5550-0100", result["answer"])

    def test_active_conflict_is_surfaced(self) -> None:
        result = rag.run_pipeline(self.fixture, "Q-conflict")
        facts = sorted(citation["fact_id"] for citation in result["citations"])
        self.assertEqual("conflict", result["status"])
        self.assertEqual(["F-lodging-500", "F-lodging-600"], facts)

    def test_no_evidence_query_refuses(self) -> None:
        result = rag.run_pipeline(self.fixture, "Q-mars")
        self.assertEqual("insufficient_evidence", result["status"])
        self.assertEqual([], result["citations"])

    def test_tool_route_short_circuits_retrieval(self) -> None:
        execution = self.execution("Q-order-live")
        self.assertEqual("tool_required", execution["response"]["status"])
        self.assertEqual([], execution["audit_trace"]["retrieved"])
        self.assertEqual([], execution["audit_trace"]["selected"])

    def test_retrieval_error_refuses(self) -> None:
        execution = self.execution("Q-refund", failure="retrieval_error")
        self.assertEqual("dependency_unavailable", execution["response"]["status"])
        self.assertTrue(execution["audit_trace"]["degraded"])
        self.assertEqual([], execution["response"]["claims"])

    def test_reranker_error_uses_retrieval_order(self) -> None:
        execution = self.execution("Q-refund", failure="reranker_error")
        self.assertEqual("answered", execution["response"]["status"])
        self.assertEqual(
            "reranker_error:retrieval_order", execution["audit_trace"]["fallback"]
        )

    def test_generation_error_does_not_emit_evidence_claims(self) -> None:
        execution = self.execution("Q-refund", failure="generation_error")
        self.assertEqual("generation_unavailable", execution["response"]["status"])
        self.assertEqual([], execution["response"]["claims"])
        self.assertGreater(len(execution["audit_trace"]["selected"]), 0)

    def test_unknown_citation_is_detected(self) -> None:
        execution = self.execution("Q-refund")
        changed = copy.deepcopy(execution["response"])
        changed["citations"][0]["fact_id"] = "F-unknown"
        errors = rag.validate_result(
            self.fixture,
            self.query("Q-refund"),
            changed,
            execution["audit_trace"],
        )
        self.assertTrue(any("unknown fact" in error for error in errors))

    def test_unsupported_claim_is_detected(self) -> None:
        execution = self.execution("Q-refund")
        changed = copy.deepcopy(execution["response"])
        changed["claims"][0]["text"] = "A refund is guaranteed to arrive immediately."
        errors = rag.validate_result(
            self.fixture,
            self.query("Q-refund"),
            changed,
            execution["audit_trace"],
        )
        self.assertTrue(any("must support the claim verbatim" in error for error in errors))

    def test_every_claim_citation_must_support_the_claim_verbatim(self) -> None:
        execution = self.execution("Q-refund")
        changed = copy.deepcopy(execution["response"])
        changed["citations"].append(
            {
                "document_id": "S2",
                "fact_id": "F-duplicate-action",
                "source_revision": "payments-v2",
            }
        )
        changed["claims"][0]["citations"].append(
            {"document_id": "S2", "fact_id": "F-duplicate-action"}
        )
        errors = rag.validate_result(
            self.fixture,
            self.query("Q-refund"),
            changed,
            execution["audit_trace"],
        )
        self.assertTrue(any("each citation" in error for error in errors))

    def test_duplicate_citation_within_claim_is_rejected(self) -> None:
        execution = self.execution("Q-refund")
        changed = copy.deepcopy(execution["response"])
        changed["claims"][0]["citations"].append(
            copy.deepcopy(changed["claims"][0]["citations"][0])
        )
        errors = rag.validate_result(
            self.fixture,
            self.query("Q-refund"),
            changed,
            execution["audit_trace"],
        )
        self.assertTrue(any("duplicate claim citation" in error for error in errors))

    def test_revision_tampering_is_detected(self) -> None:
        execution = self.execution("Q-refund")
        changed = copy.deepcopy(execution["response"])
        changed["citations"][0]["source_revision"] = "wrong"
        errors = rag.validate_result(
            self.fixture,
            self.query("Q-refund"),
            changed,
            execution["audit_trace"],
        )
        self.assertTrue(any("source_revision" in error for error in errors))

    def test_answer_text_must_be_rendered_from_validated_claims(self) -> None:
        execution = self.execution("Q-refund")
        changed = copy.deepcopy(execution["response"])
        changed["answer"] = "A refund is guaranteed to arrive today with no fee."
        errors = rag.validate_result(
            self.fixture,
            self.query("Q-refund"),
            changed,
            execution["audit_trace"],
        )
        self.assertTrue(any("deterministically rendered" in error for error in errors))

    def test_private_body_canary_is_detected_without_document_id(self) -> None:
        execution = self.execution("Q-phone-guest")
        changed = copy.deepcopy(execution["response"])
        changed["answer"] = "The internal incident escalation phone is 010-5550-0100 and is for on-call engineers only."
        errors = rag.validate_result(
            self.fixture,
            self.query("Q-phone-guest"),
            changed,
            execution["audit_trace"],
        )
        self.assertTrue(any("canary" in error for error in errors))

    def test_public_response_does_not_contain_privileged_trace(self) -> None:
        response = rag.run_pipeline(self.fixture, "Q-phone-guest")
        self.assertEqual(rag.RESPONSE_FIELDS, set(response))
        self.assertNotIn("filter_summary", response)
        self.assertNotIn("retrieved", response)

    def test_internal_trace_is_explicitly_privileged_and_versioned(self) -> None:
        execution = self.execution("Q-phone-guest")
        trace = execution["audit_trace"]
        self.assertEqual("privileged_audit", trace["visibility"])
        self.assertEqual("auth-policy-v3", trace["authorization_revision"])
        self.assertIn("acl_denied", trace["filter_summary"]["reasons"])

    def test_unauthorized_corpus_change_cannot_change_public_response(self) -> None:
        before = rag.run_pipeline(self.fixture, "Q-phone-guest")
        changed_fixture = copy.deepcopy(self.fixture)
        changed_fixture["documents"].append(
            {
                "id": "S-private-extra",
                "canonical_document_id": "private-extra",
                "title": "Additional private phone",
                "text": "The additional private phone is 010-0000-0000.",
                "tenant_id": "tenant-a",
                "acl": ["finance"],
                "status": "published",
                "effective_from": "2026-01-01",
                "effective_to": None,
                "source_revision": "private-extra-v1",
                "authority": 99,
                "facts": [
                    {
                        "fact_id": "F-private-extra",
                        "topic": "incident_phone",
                        "statement": "The additional private phone is 010-0000-0000.",
                        "value": "010-0000-0000",
                        "unit": "phone",
                    }
                ],
            }
        )
        after = rag.run_pipeline(changed_fixture, "Q-phone-guest")
        self.assertEqual(before, after)

    def test_internal_trace_rejects_unauthorized_selected_document(self) -> None:
        execution = self.execution("Q-phone-guest")
        changed = copy.deepcopy(execution)
        changed["audit_trace"]["selected"].append(
            {"document_id": "S3", "rank": 99, "score": 1.0, "chars": 10}
        )
        errors = rag.validate_execution(
            self.fixture,
            rag._runtime_query(self.query("Q-phone-guest")),
            changed,
        )
        self.assertTrue(any("unauthorized" in error for error in errors))

    def test_response_json_scalar_types_return_contract_errors(self) -> None:
        execution = self.execution("Q-refund")
        mutations = (
            ("status", lambda value: value.__setitem__("status", [])),
            ("citations container", lambda value: value.__setitem__("citations", None)),
            ("claims container", lambda value: value.__setitem__("claims", {})),
            (
                "top citation document id",
                lambda value: value["citations"][0].__setitem__("document_id", []),
            ),
            (
                "top citation fact id",
                lambda value: value["citations"][0].__setitem__("fact_id", {}),
            ),
            (
                "top citation source revision",
                lambda value: value["citations"][0].__setitem__(
                    "source_revision", []
                ),
            ),
            (
                "claim id",
                lambda value: value["claims"][0].__setitem__("claim_id", []),
            ),
            (
                "claim citation document id",
                lambda value: value["claims"][0]["citations"][0].__setitem__(
                    "document_id", []
                ),
            ),
            (
                "claim citation fact id",
                lambda value: value["claims"][0]["citations"][0].__setitem__(
                    "fact_id", {}
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                changed = copy.deepcopy(execution["response"])
                mutate(changed)
                errors = rag.validate_result(
                    self.fixture,
                    self.query("Q-refund"),
                    changed,
                    execution["audit_trace"],
                )
                self.assertTrue(errors)

    def test_trace_json_scalar_types_return_contract_errors(self) -> None:
        execution = self.execution("Q-refund")
        mutations = (
            ("failure", lambda value: value["audit_trace"].__setitem__("failure", [])),
            ("route", lambda value: value["audit_trace"].__setitem__("route", {})),
            (
                "retrieved document id",
                lambda value: value["audit_trace"]["retrieved"][0].__setitem__(
                    "document_id", []
                ),
            ),
            (
                "retrieved rank",
                lambda value: value["audit_trace"]["retrieved"][0].__setitem__(
                    "rank", {}
                ),
            ),
            (
                "selected score",
                lambda value: value["audit_trace"]["selected"][0].__setitem__(
                    "score", []
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                changed = copy.deepcopy(execution)
                mutate(changed)
                errors = rag.validate_execution(
                    self.fixture,
                    rag._runtime_query(self.query("Q-refund")),
                    changed,
                )
                self.assertTrue(errors)

    def test_trace_pipeline_revisions_are_bound_to_fixture(self) -> None:
        execution = self.execution("Q-refund")
        revision_fields = (
            "pipeline_revision",
            "retrieval_revision",
            "rerank_revision",
            "context_policy_revision",
            "answer_policy_revision",
        )
        for field in revision_fields:
            with self.subTest(field=field):
                changed = copy.deepcopy(execution)
                changed["audit_trace"][field] = "tampered-revision"
                errors = rag.validate_execution(
                    self.fixture,
                    rag._runtime_query(self.query("Q-refund")),
                    changed,
                )
                self.assertTrue(any(field in error for error in errors))

    def test_degraded_fallback_and_failure_status_are_bound(self) -> None:
        mutations = (
            (
                "none cannot claim degradation",
                "Q-refund",
                "none",
                lambda value: value["audit_trace"].__setitem__("degraded", True),
            ),
            (
                "retrieval fallback is fixed",
                "Q-refund",
                "retrieval_error",
                lambda value: value["audit_trace"].__setitem__(
                    "fallback", "retrieval_error:free_generate"
                ),
            ),
            (
                "reranker degradation is recorded",
                "Q-refund",
                "reranker_error",
                lambda value: value["audit_trace"].__setitem__("degraded", False),
            ),
            (
                "generation failure cannot masquerade as insufficient evidence",
                "Q-refund",
                "generation_error",
                lambda value: value.__setitem__(
                    "response",
                    rag._response(
                        value["audit_trace"]["trace_id"],
                        "insufficient_evidence",
                        [],
                        [],
                    ),
                ),
            ),
            (
                "tool route ignores retrieval degradation injection",
                "Q-order-live",
                "retrieval_error",
                lambda value: value["audit_trace"].__setitem__("degraded", True),
            ),
        )
        for label, query_id, failure, mutate in mutations:
            with self.subTest(label=label):
                changed = copy.deepcopy(self.execution(query_id, failure=failure))
                mutate(changed)
                errors = rag.validate_execution(
                    self.fixture,
                    rag._runtime_query(self.query(query_id)),
                    changed,
                )
                self.assertTrue(
                    any(
                        "route/failure" in error
                        for error in errors
                    )
                )

    def test_response_and_trace_id_are_bound_to_deterministic_runtime(self) -> None:
        conflict = copy.deepcopy(self.execution("Q-conflict"))
        first_claim = conflict["response"]["claims"][0]
        first_reference = first_claim["citations"][0]
        first_citation = next(
            citation
            for citation in conflict["response"]["citations"]
            if citation["document_id"] == first_reference["document_id"]
            and citation["fact_id"] == first_reference["fact_id"]
        )
        conflict["response"] = rag._response(
            conflict["audit_trace"]["trace_id"],
            "answered",
            [first_claim],
            [first_citation],
        )

        refund = copy.deepcopy(self.execution("Q-refund"))
        refund["response"] = rag._response(
            refund["audit_trace"]["trace_id"],
            "insufficient_evidence",
            [],
            [],
        )

        trace_tampered = copy.deepcopy(self.execution("Q-refund"))
        trace_tampered["audit_trace"]["trace_id"] = "trace-tampered"
        trace_tampered["response"]["trace_id"] = "trace-tampered"

        for label, query_id, changed in (
            ("conflict collapsed", "Q-conflict", conflict),
            ("answer suppressed", "Q-refund", refund),
            ("trace id", "Q-refund", trace_tampered),
        ):
            with self.subTest(label=label):
                errors = rag.validate_execution(
                    self.fixture,
                    rag._runtime_query(self.query(query_id)),
                    changed,
                )
                self.assertTrue(
                    any(
                        "runtime" in error or "pipeline/query" in error
                        for error in errors
                    )
                )

    def test_filter_summary_is_recomputed_from_authorized_corpus(self) -> None:
        execution = self.execution("Q-refund")
        changed = copy.deepcopy(execution)
        changed["audit_trace"]["filter_summary"]["visible"] += 1
        errors = rag.validate_execution(
            self.fixture,
            rag._runtime_query(self.query("Q-refund")),
            changed,
        )
        self.assertTrue(any("filter_summary" in error for error in errors))

    def test_context_chars_and_selected_item_chars_are_recomputed(self) -> None:
        execution = self.execution("Q-refund")
        mutations = (
            (
                "aggregate",
                lambda value: value["audit_trace"].__setitem__(
                    "context_chars", value["audit_trace"]["context_chars"] + 1
                ),
            ),
            (
                "selected item",
                lambda value: value["audit_trace"]["selected"][0].__setitem__(
                    "chars", value["audit_trace"]["selected"][0]["chars"] + 1
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                changed = copy.deepcopy(execution)
                mutate(changed)
                errors = rag.validate_execution(
                    self.fixture,
                    rag._runtime_query(self.query("Q-refund")),
                    changed,
                )
                self.assertTrue(any("chars" in error for error in errors))

    def test_stage_documents_must_be_unique(self) -> None:
        execution = self.execution("Q-refund")
        changed = copy.deepcopy(execution)
        changed["audit_trace"]["retrieved"].append(
            copy.deepcopy(changed["audit_trace"]["retrieved"][0])
        )
        errors = rag.validate_execution(
            self.fixture,
            rag._runtime_query(self.query("Q-refund")),
            changed,
        )
        self.assertTrue(any("retrieved" in error and "duplicate" in error for error in errors))

    def test_stage_ranks_and_scores_are_bound_across_transformations(self) -> None:
        execution = self.execution("Q-refund")
        mutations = (
            (
                "retrieved rank",
                lambda value: value["audit_trace"]["retrieved"][0].__setitem__("rank", 2),
            ),
            (
                "reranked retrieval score",
                lambda value: value["audit_trace"]["reranked"][0].__setitem__(
                    "retrieval_score",
                    value["audit_trace"]["reranked"][0]["retrieval_score"] + 0.1,
                ),
            ),
            (
                "selected rerank score",
                lambda value: value["audit_trace"]["selected"][0].__setitem__(
                    "score", value["audit_trace"]["selected"][0]["score"] + 0.1
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                changed = copy.deepcopy(execution)
                mutate(changed)
                errors = rag.validate_execution(
                    self.fixture,
                    rag._runtime_query(self.query("Q-refund")),
                    changed,
                )
                self.assertTrue(errors)

    def test_reranked_selected_and_dropped_items_must_come_from_prior_stage(self) -> None:
        execution = self.execution("Q-refund")
        mutations = (
            (
                "reranked",
                lambda value: value["audit_trace"]["reranked"].pop(),
            ),
            (
                "selected",
                lambda value: value["audit_trace"]["selected"][0].__setitem__(
                    "document_id", "S10"
                ),
            ),
            (
                "dropped",
                lambda value: value["audit_trace"]["dropped"].append(
                    {"document_id": "S10", "reason": "context_limit"}
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                changed = copy.deepcopy(execution)
                mutate(changed)
                errors = rag.validate_execution(
                    self.fixture,
                    rag._runtime_query(self.query("Q-refund")),
                    changed,
                )
                self.assertTrue(errors)

    def test_runtime_pipeline_does_not_read_offline_oracle(self) -> None:
        expected = rag.run_pipeline(self.fixture, "Q-refund")
        changed_fixture = copy.deepcopy(self.fixture)
        changed_query = next(
            query for query in changed_fixture["queries"] if query["id"] == "Q-refund"
        )
        changed_query["expected_status"] = "conflict"
        actual = rag.run_pipeline(changed_fixture, "Q-refund")
        self.assertEqual(expected, actual)
        self.assertIn("status_mismatch", rag.oracle_failure_codes(changed_query, actual))

    def test_authorized_untrusted_document_cannot_change_control_fields(self) -> None:
        execution = self.execution("Q-untrusted-content")
        self.assertEqual("answered", execution["response"]["status"])
        self.assertEqual("knowledge", execution["audit_trace"]["route"])
        self.assertEqual("tenant-a", self.query("Q-untrusted-content")["tenant_id"])

    def test_layered_evaluation_passes_and_is_fingerprinted(self) -> None:
        report = rag.evaluate_fixture(self.fixture)
        self.assertEqual("PASS", report["action"])
        self.assertEqual(8, report["query_count"])
        self.assertEqual(1.0, report["metrics"]["retrieval_fact_recall"])
        self.assertEqual(64, len(report["evidence_fingerprint"]))

    def test_retrieval_and_context_recall_count_expected_facts_not_documents(self) -> None:
        changed = copy.deepcopy(self.fixture)
        refund_document = next(
            document for document in changed["documents"] if document["id"] == "S1"
        )
        refund_document["facts"].append(
            {
                "fact_id": "F-refund-channel",
                "topic": "refund_channel",
                "statement": "A refund is approved.",
                "value": "original_channel",
                "unit": "route",
            }
        )
        refund_document["text"] += "A refund is approved."
        refund_query = next(
            query for query in changed["queries"] if query["id"] == "Q-refund"
        )
        refund_query["expected_fact_ids"].append("F-refund-channel")
        refund_query["expected_fact_ids"].sort()
        self.assertEqual([], rag.validate_fixture(changed))

        report = rag.evaluate_fixture(changed)

        refund_case = next(
            case for case in report["cases"] if case["query_id"] == "Q-refund"
        )
        self.assertEqual(1.0, refund_case["retrieval_fact_recall"])
        self.assertEqual(1.0, refund_case["context_fact_recall"])
        self.assertEqual(1.0, report["metrics"]["retrieval_fact_recall"])
        self.assertEqual(1.0, report["metrics"]["context_fact_recall"])

    def test_retrieval_failure_blocks_layered_evaluation(self) -> None:
        report = rag.evaluate_fixture(self.fixture, failure="retrieval_error")
        self.assertEqual("BLOCK", report["action"])
        self.assertIn("gate_failed:case_pass_rate", report["reasons"])

    def test_response_extra_field_is_detected(self) -> None:
        execution = self.execution("Q-refund")
        changed = copy.deepcopy(execution["response"])
        changed["debug"] = True
        errors = rag.validate_result(
            self.fixture,
            self.query("Q-refund"),
            changed,
            execution["audit_trace"],
        )
        self.assertTrue(any("response" in error for error in errors))


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [sys.executable, "-B", "-W", "error", str(SCRIPT_PATH), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )

    def test_demo_cli_returns_all_queries(self) -> None:
        completed = self.run_cli("--fixture", str(FIXTURE_PATH), "demo")
        self.assertEqual(0, completed.returncode, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(8, len(payload["results"]))
        self.assertNotIn("audit_trace", json.dumps(payload, ensure_ascii=False))

    def test_ask_cli_accepts_stable_query_id(self) -> None:
        absolute_fixture = str(FIXTURE_PATH.resolve())
        completed = self.run_cli(
            "--fixture", absolute_fixture, "ask", "--query-id", "Q-refund"
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual("answered", payload["result"]["status"])
        self.assertNotIn("filter_summary", payload["result"])
        self.assertNotIn(absolute_fixture, completed.stdout)

    def test_cli_huge_integer_returns_controlled_fixture_error(self) -> None:
        original = FIXTURE_PATH.read_text(encoding="utf-8")
        malformed = original.replace(
            '"min_case_pass_rate": 1.0',
            '"min_case_pass_rate": ' + "1" + "0" * 400,
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "huge-number.json"
            fixture.write_text(malformed, encoding="utf-8")
            completed = self.run_cli("--fixture", str(fixture), "evaluate")
        self.assertEqual(2, completed.returncode)
        self.assertIn("min_case_pass_rate", completed.stderr)
        self.assertNotIn("OverflowError", completed.stderr)

    def test_inspect_requires_explicit_operator_view(self) -> None:
        completed = self.run_cli(
            "--fixture", str(FIXTURE_PATH), "inspect", "--query-id", "Q-refund"
        )
        self.assertEqual(2, completed.returncode)
        self.assertIn("--operator-view", completed.stderr)

    def test_inspect_returns_privileged_audit_envelope(self) -> None:
        completed = self.run_cli(
            "--fixture",
            str(FIXTURE_PATH),
            "inspect",
            "--query-id",
            "Q-refund",
            "--operator-view",
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(
            "privileged_audit",
            payload["execution"]["audit_trace"]["visibility"],
        )

    def test_evaluate_cli_uses_gate_exit_codes(self) -> None:
        passed = self.run_cli("--fixture", str(FIXTURE_PATH), "evaluate")
        blocked = self.run_cli(
            "--fixture",
            str(FIXTURE_PATH),
            "evaluate",
            "--failure",
            "retrieval_error",
        )
        self.assertEqual(0, passed.returncode, passed.stderr)
        self.assertEqual(1, blocked.returncode, blocked.stderr)
        self.assertEqual("BLOCK", json.loads(blocked.stdout)["report"]["action"])

    def test_unknown_query_id_has_nonzero_exit(self) -> None:
        completed = self.run_cli(
            "--fixture", str(FIXTURE_PATH), "ask", "--query-id", "Q-unknown"
        )
        self.assertEqual(2, completed.returncode)
        self.assertIn("unknown query id", completed.stderr)


if __name__ == "__main__":
    unittest.main()
