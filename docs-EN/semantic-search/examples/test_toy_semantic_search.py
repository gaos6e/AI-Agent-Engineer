"""Tests for the deterministic offline semantic-search teaching lab."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "toy_semantic_search.py"
FIXTURE = HERE / "semantic-search-fixture.json"
SPEC = importlib.util.spec_from_file_location("toy_semantic_search", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load toy_semantic_search.py")
lab = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


def raw_fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TemporaryFixtureMixin:
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "fixture.json"

    def write(self, value: object) -> Path:
        self.path.write_text(
            json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return self.path


class ContractAndMathTests(unittest.TestCase):
    def test_analyzer_normalises_ascii_and_builds_cjk_bigrams(self) -> None:
        tokens = lab.analyze("\uff25\uff10\uff14\uff12 \u9000\u6b3e\u5230\u8d26")
        self.assertEqual(tokens[0], "e042")
        self.assertIn("\u9000\u6b3e", tokens)
        self.assertIn("\u6b3e\u5230", tokens)
        self.assertIn("\u5230\u8d26", tokens)

    def test_analyzer_is_deterministic_for_empty_and_single_cjk(self) -> None:
        self.assertEqual(lab.analyze(""), ())
        self.assertEqual(lab.analyze("\u94b1"), ("\u94b1",))
        self.assertEqual(lab.analyze("VPN vpn"), ("vpn", "vpn"))

    def test_vector_score_supports_three_metrics(self) -> None:
        self.assertAlmostEqual(
            lab.vector_score((1.0, 0.0), (1.0, 0.0), metric="cosine"),
            1.0,
        )
        self.assertAlmostEqual(
            lab.vector_score((1.0, 2.0), (3.0, 4.0), metric="dot"),
            11.0,
        )
        self.assertAlmostEqual(
            lab.vector_score((0.0, 0.0), (3.0, 4.0), metric="euclidean"),
            -5.0,
        )

    def test_vector_score_rejects_bad_inputs(self) -> None:
        calls = [
            ((), (), "cosine"),
            ((1.0,), (1.0, 2.0), "cosine"),
            ((0.0, 0.0), (1.0, 0.0), "cosine"),
            ((math.inf,), (1.0,), "dot"),
            ((10**400,), (1.0,), "dot"),
            ((1.0,), (1.0,), "unknown"),
        ]
        for left, right, metric in calls:
            with self.subTest(metric=metric), self.assertRaises(lab.SemanticSearchError):
                lab.vector_score(left, right, metric=metric)

    def test_ranking_metrics_use_all_relevant_documents(self) -> None:
        metrics = lab.ranking_metrics(
            ["d2", "d3", "d1"],
            {"d1": 3, "d2": 1},
            top_k=2,
        )
        self.assertEqual(metrics["recall"], 0.5)
        self.assertEqual(metrics["mrr"], 1.0)
        self.assertGreater(metrics["ndcg"], 0.0)
        self.assertLess(metrics["ndcg"], 1.0)

    def test_empty_qrels_have_null_metrics(self) -> None:
        self.assertEqual(
            lab.ranking_metrics([], {}, top_k=3),
            {"recall": None, "mrr": None, "ndcg": None},
        )

    def test_ranking_metrics_reject_duplicate_ids_and_invalid_qrels(self) -> None:
        with self.assertRaisesRegex(lab.SemanticSearchError, "duplicate"):
            lab.ranking_metrics(
                ["d1", "d1"], {"d1": 3, "d2": 2}, top_k=2
            )
        for qrels in ({"d1": True}, {"d1": 0}, {"d1": 4}):
            with self.subTest(qrels=qrels), self.assertRaisesRegex(
                lab.SemanticSearchError, "1..3"
            ):
                lab.ranking_metrics(["d1"], qrels, top_k=1)

    def test_rrf_uses_rank_not_raw_channel_score(self) -> None:
        first = [lab.ScoredHit("a", 1000.0), lab.ScoredHit("b", 1.0)]
        second = [lab.ScoredHit("b", -100.0), lab.ScoredHit("a", -200.0)]
        fused = lab.reciprocal_rank_fusion(
            {"first": first, "second": second},
            rank_window=2,
            constant=60,
        )
        self.assertEqual([hit.document_id for hit in fused], ["a", "b"])
        self.assertAlmostEqual(fused[0].score, fused[1].score)

    def test_rrf_rejects_duplicate_or_single_channel(self) -> None:
        duplicate = [lab.ScoredHit("a", 1.0), lab.ScoredHit("a", 0.5)]
        with self.assertRaisesRegex(lab.SemanticSearchError, "at least two"):
            lab.reciprocal_rank_fusion(
                {"only": duplicate}, rank_window=2, constant=60
            )
        with self.assertRaisesRegex(lab.SemanticSearchError, "duplicate"):
            lab.reciprocal_rank_fusion(
                {"one": duplicate, "two": []},
                rank_window=2,
                constant=60,
            )


class FixtureValidationTests(TemporaryFixtureMixin, unittest.TestCase):
    def test_valid_fixture_loads_with_stable_contract(self) -> None:
        fixture = lab.load_fixture(FIXTURE)
        self.assertEqual(len(fixture.documents), 10)
        self.assertEqual(len(fixture.queries), 7)
        self.assertEqual(len(fixture.representation.signature()), 64)
        self.assertEqual(fixture.representation.signature(), fixture.representation.signature())

    def test_duplicate_key_and_nonfinite_number_are_rejected(self) -> None:
        self.path.write_text(
            '{"schema_version":1,"schema_version":1}',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(lab.SemanticSearchError, "duplicate JSON field"):
            lab.load_fixture(self.path)
        self.path.write_text(
            '{"schema_version":NaN}',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(lab.SemanticSearchError, "non-finite"):
            lab.load_fixture(self.path)

    def test_exact_top_fields_and_schema_version_are_checked(self) -> None:
        value = raw_fixture()
        value["extra"] = True
        with self.assertRaisesRegex(lab.SemanticSearchError, "fields must be exactly"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["schema_version"] = 2
        with self.assertRaisesRegex(lab.SemanticSearchError, "schema_version"):
            lab.load_fixture(self.write(value))

    def test_representation_contract_rejects_bad_values(self) -> None:
        cases = [
            ("dimension", True),
            ("dimension", 0),
            ("metric", "unknown"),
            ("normalized", "true"),
        ]
        for field, replacement in cases:
            value = raw_fixture()
            value["representation"][field] = replacement
            with self.subTest(field=field), self.assertRaises(lab.SemanticSearchError):
                lab.load_fixture(self.write(value))

    def test_document_vectors_reject_dimension_bool_zero_and_bad_norm(self) -> None:
        vectors = [
            [1, 0],
            [True, 0, 0, 0, 0, 0, 0],
            [10**400, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [2, 0, 0, 0, 0, 0, 0],
        ]
        for vector in vectors:
            value = raw_fixture()
            value["documents"][0]["vector"] = vector
            with self.subTest(vector=vector), self.assertRaises(lab.SemanticSearchError):
                lab.load_fixture(self.write(value))

    def test_document_status_acl_and_duplicate_id_are_checked(self) -> None:
        value = raw_fixture()
        value["documents"][0]["status"] = "deleted"
        with self.assertRaisesRegex(lab.SemanticSearchError, "status"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["documents"][0]["acl"] = ["guests", "employees"]
        with self.assertRaisesRegex(lab.SemanticSearchError, "lexicographically"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["documents"][1]["id"] = value["documents"][0]["id"]
        with self.assertRaisesRegex(lab.SemanticSearchError, "duplicate document id"):
            lab.load_fixture(self.write(value))

    def test_query_groups_filters_and_relevance_are_checked(self) -> None:
        value = raw_fixture()
        value["queries"][0]["subject_groups"] = ["z", "a"]
        with self.assertRaisesRegex(lab.SemanticSearchError, "lexicographically"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["queries"][0]["filters"] = {"tenant_id": "alpha"}
        with self.assertRaisesRegex(lab.SemanticSearchError, "does not allow field"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["queries"][0]["qrels"] = {"d-03-refund-time": True}
        with self.assertRaisesRegex(lab.SemanticSearchError, "1..3"):
            lab.load_fixture(self.write(value))

    def test_qrels_must_exist_be_eligible_and_not_overlap_denials(self) -> None:
        value = raw_fixture()
        value["queries"][0]["qrels"] = {"unknown": 3}
        with self.assertRaisesRegex(lab.SemanticSearchError, "unknown document"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["queries"][0]["qrels"] = {"d-09-beta-private": 3}
        with self.assertRaisesRegex(lab.SemanticSearchError, "does not satisfy access"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["queries"][1]["qrels"] = {"d-09-beta-private": 3}
        with self.assertRaisesRegex(lab.SemanticSearchError, "overlap"):
            lab.load_fixture(self.write(value))

    def test_denied_documents_must_exist_and_be_ineligible(self) -> None:
        value = raw_fixture()
        value["queries"][0]["must_not_return"] = ["unknown"]
        with self.assertRaisesRegex(lab.SemanticSearchError, "unknown document"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["queries"][0]["must_not_return"] = ["d-04-double-charge"]
        with self.assertRaisesRegex(lab.SemanticSearchError, "still eligible"):
            lab.load_fixture(self.write(value))

    def test_duplicate_query_id_is_rejected(self) -> None:
        value = raw_fixture()
        value["queries"][1]["id"] = value["queries"][0]["id"]
        with self.assertRaisesRegex(lab.SemanticSearchError, "duplicate query id"):
            lab.load_fixture(self.write(value))

    def test_size_limit_is_checked_before_parsing(self) -> None:
        with mock.patch.object(lab, "MAX_FIXTURE_BYTES", 10):
            with self.assertRaisesRegex(lab.SemanticSearchError, "2 MiB"):
                lab.load_fixture(FIXTURE)


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = lab.load_fixture(FIXTURE)
        cls.queries = {query.query_id: query for query in cls.fixture.queries}

    def test_filtering_removes_other_tenant_draft_and_wrong_acl(self) -> None:
        double = lab.eligible_documents(self.fixture, self.queries["q-double-charge"])
        identifiers = {document.document_id for document in double}
        self.assertEqual(identifiers, {"d-03-refund-time", "d-04-double-charge"})
        guest_ops = lab.eligible_documents(self.fixture, self.queries["q-ops-guest"])
        self.assertEqual(guest_ops, ())

    def test_empty_subject_groups_fail_closed(self) -> None:
        query = replace(self.queries["q-refund-time"], subject_groups=())
        self.assertEqual(lab.eligible_documents(self.fixture, query), ())

    def test_bm25_recovers_exact_error_code(self) -> None:
        query = self.queries["q-e042"]
        hits = lab.rank_bm25(
            query,
            lab.eligible_documents(self.fixture, query),
            limit=5,
        )
        self.assertEqual([hit.document_id for hit in hits], ["d-02-e042"])

    def test_bm25_can_miss_a_semantic_paraphrase(self) -> None:
        query = self.queries["q-double-charge"]
        hits = lab.rank_bm25(
            query,
            lab.eligible_documents(self.fixture, query),
            limit=5,
        )
        self.assertEqual(hits, [])

    def test_dense_fixture_recovers_semantic_paraphrase(self) -> None:
        query = self.queries["q-double-charge"]
        hits = lab.rank_dense(
            query,
            lab.eligible_documents(self.fixture, query),
            self.fixture.representation,
            limit=5,
        )
        self.assertEqual(hits[0].document_id, "d-04-double-charge")
        self.assertEqual(hits[0].score, 1.0)

    def test_dense_tie_is_broken_by_stable_id(self) -> None:
        query = self.queries["q-e042"]
        hits = lab.rank_dense(
            query,
            lab.eligible_documents(self.fixture, query),
            self.fixture.representation,
            limit=5,
        )
        self.assertEqual(
            [hit.document_id for hit in hits[:2]],
            ["d-01-format-general", "d-02-e042"],
        )

    def test_hybrid_promotes_exact_code_over_dense_tie(self) -> None:
        query = self.queries["q-e042"]
        documents = lab.eligible_documents(self.fixture, query)
        bm25 = lab.rank_bm25(query, documents, limit=5)
        dense = lab.rank_dense(
            query, documents, self.fixture.representation, limit=5
        )
        fused = lab.reciprocal_rank_fusion(
            {"bm25": bm25, "dense": dense},
            rank_window=5,
            constant=60,
        )
        self.assertEqual(fused[0].document_id, "d-02-e042")

    def test_bm25_and_limits_reject_invalid_parameters(self) -> None:
        query = self.queries["q-refund-time"]
        documents = lab.eligible_documents(self.fixture, query)
        for values in (
            {"limit": 0},
            {"limit": 1, "k1": 0.0},
            {"limit": 1, "b": 2.0},
        ):
            with self.subTest(values=values), self.assertRaises(lab.SemanticSearchError):
                lab.rank_bm25(query, documents, **values)


class EvaluationAndCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = lab.load_fixture(FIXTURE)

    def test_report_has_expected_quality_and_no_security_violation(self) -> None:
        report = lab.evaluate(
            self.fixture, top_k=3, rank_window=5, rrf_constant=60
        )
        self.assertEqual(
            report["report_schema_version"], "semantic-search-offline-audit-v1"
        )
        self.assertEqual(report["visibility"], "protected_audit")
        self.assertEqual(report["fixture"]["document_count"], 10)
        self.assertEqual(report["fixture"]["query_count"], 7)
        self.assertEqual(report["security_violations"], [])
        self.assertEqual(report["macro_metrics"]["hybrid_rrf"]["recall"], 1.0)
        self.assertGreater(
            report["macro_metrics"]["hybrid_rrf"]["ndcg"],
            report["macro_metrics"]["dense"]["ndcg"],
        )

    def test_security_gate_checks_entire_candidate_window(self) -> None:
        original = lab.rank_dense

        def inject_forbidden_candidate(
            query: lab.Query,
            documents: tuple[lab.Document, ...],
            contract: lab.RepresentationContract,
            *,
            limit: int,
        ) -> list[lab.ScoredHit]:
            ranking = original(query, documents, contract, limit=limit)
            if query.query_id != "q-double-charge":
                return ranking
            return (
                ranking[:1]
                + [lab.ScoredHit("d-09-beta-private", -1.0)]
                + ranking[1 : max(1, limit - 1)]
            )

        with mock.patch.object(
            lab, "rank_dense", side_effect=inject_forbidden_candidate
        ):
            report = lab.evaluate(
                self.fixture, top_k=1, rank_window=5, rrf_constant=60
            )

        violation = next(
            item
            for item in report["security_violations"]
            if item["query_id"] == "q-double-charge"
            and item["channel"] == "dense"
            and item["document_id"] == "d-09-beta-private"
        )
        self.assertEqual(violation["rank"], 2)
        self.assertEqual(violation["stage"], "candidate_window")
        self.assertEqual(violation["reason"], "must_not_return")

    def test_report_excludes_no_answer_query_from_macro_and_returns_empty(self) -> None:
        report = lab.evaluate(
            self.fixture, top_k=3, rank_window=5, rrf_constant=60
        )
        row = next(
            item for item in report["queries"] if item["query_id"] == "q-ops-guest"
        )
        self.assertEqual(row["rankings"]["hybrid_rrf"], [])
        self.assertIsNone(row["metrics"]["hybrid_rrf"]["recall"])

    def test_evaluate_rejects_bad_window_and_numbers(self) -> None:
        cases = [
            {"top_k": 0, "rank_window": 5, "rrf_constant": 60},
            {"top_k": 3, "rank_window": 2, "rrf_constant": 60},
            {"top_k": 3, "rank_window": 5, "rrf_constant": 0},
        ]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(lab.SemanticSearchError):
                lab.evaluate(self.fixture, **values)

    def test_cli_output_matches_under_normal_and_optimized_python(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        command = [
            str(SCRIPT),
            "--fixture",
            str(FIXTURE),
            "--top-k",
            "3",
            "--rank-window",
            "5",
        ]
        normal = subprocess.run(
            [sys.executable, "-B", "-W", "error", *command],
            cwd=HERE,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        optimized = subprocess.run(
            [sys.executable, "-B", "-O", "-W", "error", *command],
            cwd=HERE,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(normal.stdout, optimized.stdout)
        self.assertEqual(normal.stderr, b"")
        report = json.loads(normal.stdout.decode("utf-8"))
        self.assertIn("not learned embeddings", report["notice"])

    def test_cli_returns_controlled_error_for_invalid_fixture(self) -> None:
        overflow = raw_fixture()
        overflow["documents"][0]["vector"] = [10**400, 0, 0, 0, 0, 0, 0]
        cases = {
            "missing-fields": "{}\n",
            "overflowing-vector": json.dumps(overflow, ensure_ascii=False),
        }
        for label, content in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "bad.json"
                path.write_text(content, encoding="utf-8")
                process = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(SCRIPT),
                        "--fixture",
                        str(path),
                    ],
                    cwd=HERE,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertEqual(process.returncode, 2)
                self.assertEqual(process.stdout, b"")
                self.assertIn(b"error:", process.stderr)
                self.assertNotIn(b"Traceback", process.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
