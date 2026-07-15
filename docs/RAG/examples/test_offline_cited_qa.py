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
        self.assertEqual("1.0", self.fixture["schema_version"])

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

    def test_unknown_root_field_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["unexpected"] = True
        self.assertTrue(any("root" in error for error in rag.validate_fixture(changed)))

    def test_pipeline_limits_must_be_positive_plain_ints(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["pipeline"]["retrieval_limit"] = True
        self.assertTrue(any("retrieval_limit" in error for error in rag.validate_fixture(changed)))

    def test_fact_statement_must_exist_verbatim(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["documents"][0]["facts"][0]["statement"] = "并不存在的句子。"
        self.assertTrue(any("逐字存在" in error for error in rag.validate_fixture(changed)))

    def test_duplicate_fact_id_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["documents"][1]["facts"][0]["fact_id"] = "F-refund-current"
        self.assertTrue(any("fact id 重复" in error for error in rag.validate_fixture(changed)))

    def test_unknown_expected_fact_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["queries"][0]["expected_fact_ids"] = ["F-does-not-exist"]
        self.assertTrue(any("未知 fact" in error for error in rag.validate_fixture(changed)))

    def test_reversed_effective_window_is_rejected(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["documents"][0]["effective_to"] = "2025-01-01"
        self.assertTrue(any("早于" in error for error in rag.validate_fixture(changed)))

    def test_acl_must_be_sorted_and_unique(self) -> None:
        changed = copy.deepcopy(self.fixture)
        changed["documents"][0]["acl"] = ["public", "public"]
        self.assertTrue(any("已排序且无重复" in error for error in rag.validate_fixture(changed)))


class PipelineComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = rag.load_fixture(FIXTURE_PATH)
        self.documents = self.fixture["documents"]

    def query(self, query_id: str) -> dict[str, object]:
        return next(query for query in self.fixture["queries"] if query["id"] == query_id)

    def test_features_cover_cjk_and_ascii(self) -> None:
        features = rag.text_features("RAG 退款")
        self.assertIn("a:rag", features)
        self.assertIn("c2:退款", features)

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

    def test_public_documents_are_visible_without_groups(self) -> None:
        visible, _, _ = rag.filter_documents(self.documents, self.query("Q-refund"))
        visible_ids = {document["id"] for document in visible}
        self.assertIn("S1", visible_ids)
        self.assertIn("S2", visible_ids)

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

    def test_refund_answer_is_extractively_cited(self) -> None:
        result = rag.run_pipeline(self.fixture, "Q-refund")
        self.assertEqual("answered", result["status"])
        self.assertEqual("退款审核通过后通常在一至三个工作日原路返回。", result["answer"])
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
        result = rag.run_pipeline(self.fixture, "Q-order-live")
        self.assertEqual("tool_required", result["status"])
        self.assertEqual([], result["trace"]["retrieved"])
        self.assertEqual([], result["trace"]["selected"])

    def test_retrieval_error_refuses(self) -> None:
        result = rag.run_pipeline(self.fixture, "Q-refund", failure="retrieval_error")
        self.assertEqual("dependency_unavailable", result["status"])
        self.assertTrue(result["trace"]["degraded"])
        self.assertEqual([], result["claims"])

    def test_reranker_error_uses_retrieval_order(self) -> None:
        result = rag.run_pipeline(self.fixture, "Q-refund", failure="reranker_error")
        self.assertEqual("answered", result["status"])
        self.assertEqual("reranker_error:retrieval_order", result["trace"]["fallback"])

    def test_generation_error_does_not_emit_evidence_claims(self) -> None:
        result = rag.run_pipeline(self.fixture, "Q-refund", failure="generation_error")
        self.assertEqual("generation_unavailable", result["status"])
        self.assertEqual([], result["claims"])
        self.assertGreater(len(result["trace"]["selected"]), 0)

    def test_unknown_citation_is_detected(self) -> None:
        result = rag.run_pipeline(self.fixture, "Q-refund")
        changed = copy.deepcopy(result)
        changed["citations"][0]["fact_id"] = "F-unknown"
        errors = rag.validate_result(self.fixture, self.query("Q-refund"), changed)
        self.assertTrue(any("未知 fact" in error for error in errors))

    def test_unsupported_claim_is_detected(self) -> None:
        result = rag.run_pipeline(self.fixture, "Q-refund")
        changed = copy.deepcopy(result)
        changed["claims"][0]["text"] = "退款保证立即到账。"
        errors = rag.validate_result(self.fixture, self.query("Q-refund"), changed)
        self.assertTrue(any("逐字支持" in error for error in errors))

    def test_revision_tampering_is_detected(self) -> None:
        result = rag.run_pipeline(self.fixture, "Q-refund")
        changed = copy.deepcopy(result)
        changed["citations"][0]["source_revision"] = "wrong"
        errors = rag.validate_result(self.fixture, self.query("Q-refund"), changed)
        self.assertTrue(any("source_revision" in error for error in errors))

    def test_forbidden_document_id_in_trace_is_detected(self) -> None:
        result = rag.run_pipeline(self.fixture, "Q-phone-guest")
        changed = copy.deepcopy(result)
        changed["trace"]["fallback"] = "debug:S3"
        errors = rag.validate_result(self.fixture, self.query("Q-phone-guest"), changed)
        self.assertTrue(any("泄露" in error for error in errors))

    def test_result_extra_field_is_detected(self) -> None:
        result = rag.run_pipeline(self.fixture, "Q-refund")
        changed = copy.deepcopy(result)
        changed["debug"] = True
        errors = rag.validate_result(self.fixture, self.query("Q-refund"), changed)
        self.assertTrue(any("result" in error for error in errors))


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
        self.assertEqual(7, len(payload["results"]))

    def test_ask_cli_accepts_stable_query_id(self) -> None:
        completed = self.run_cli(
            "--fixture", str(FIXTURE_PATH), "ask", "--query-id", "Q-refund"
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual("answered", payload["result"]["status"])

    def test_unknown_query_id_has_nonzero_exit(self) -> None:
        completed = self.run_cli(
            "--fixture", str(FIXTURE_PATH), "ask", "--query-id", "Q-unknown"
        )
        self.assertEqual(2, completed.returncode)
        self.assertIn("未知 query id", completed.stderr)


if __name__ == "__main__":
    unittest.main()
