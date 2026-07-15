"""Tests for the offline embedding-space lab."""

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

import evaluate_embedding_space as lab


HERE = Path(__file__).resolve().parent
FIXTURE_PATH = HERE / "embedding-fixture.json"


class JsonFixtureMixin:
    def setUp(self) -> None:
        self.payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def write_json(self, value: object) -> Path:
        handle = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".json", delete=False
        )
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        with handle:
            json.dump(value, handle, ensure_ascii=False, allow_nan=False)
        return Path(handle.name)

    def write_raw(self, value: str) -> Path:
        handle = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".json", delete=False
        )
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        with handle:
            handle.write(value)
        return Path(handle.name)


class ContractAndMathTests(unittest.TestCase):
    def make_contract(self, **changes: object) -> lab.EmbeddingContract:
        values = {
            "space_id": "space-a",
            "provider": "provider",
            "model": "model",
            "revision": "r1",
            "dimension": 3,
            "metric": "cosine",
            "normalized": False,
            "query_role": "query",
            "document_role": "document",
            "dtype": "float32",
        }
        values.update(changes)
        return lab.EmbeddingContract(**values)

    def test_valid_contract_and_signature_ignore_storage_alias(self) -> None:
        first = self.make_contract(space_id="blue")
        second = self.make_contract(space_id="green")
        first.validate()
        second.validate()
        self.assertEqual(first.signature(), second.signature())

    def test_contract_rejects_bad_dimension_metric_normalization_roles_and_dtype(self) -> None:
        invalid = [
            self.make_contract(dimension=0),
            self.make_contract(dimension=True),
            self.make_contract(metric="manhattan"),
            self.make_contract(normalized="yes"),
            self.make_contract(document_role="query"),
            self.make_contract(dtype="int8"),
        ]
        for contract in invalid:
            with self.subTest(contract=contract), self.assertRaises(lab.EmbeddingError):
                contract.validate()

    def test_normalize_returns_unit_vector(self) -> None:
        vector = lab.normalize((3.0, 4.0))
        self.assertAlmostEqual(vector[0], 0.6)
        self.assertAlmostEqual(vector[1], 0.8)
        self.assertAlmostEqual(math.sqrt(sum(value * value for value in vector)), 1.0)

    def test_normalize_rejects_empty_zero_and_nonfinite(self) -> None:
        for vector in ((), (0.0, 0.0), (math.nan, 1.0), (math.inf, 1.0)):
            with self.subTest(vector=vector), self.assertRaises(lab.EmbeddingError):
                lab.normalize(vector)

    def test_similarity_metrics_have_explicit_semantics(self) -> None:
        self.assertAlmostEqual(
            lab.similarity((2.0, 0.0), (3.0, 0.0), metric="cosine"), 1.0
        )
        self.assertEqual(
            lab.similarity((2.0, 0.0), (3.0, 0.0), metric="dot"), 6.0
        )
        self.assertEqual(
            lab.similarity((1.0, 1.0), (4.0, 5.0), metric="euclidean"), -5.0
        )

    def test_similarity_rejects_dimension_nonfinite_and_metric_errors(self) -> None:
        cases = [
            (((1.0,), (1.0, 2.0)), "cosine"),
            (((1.0, math.inf), (1.0, 2.0)), "dot"),
            (((1.0,), (1.0,)), "unknown"),
        ]
        for vectors, metric in cases:
            with self.subTest(metric=metric), self.assertRaises(lab.EmbeddingError):
                lab.similarity(*vectors, metric=metric)


class LoadingTests(JsonFixtureMixin, unittest.TestCase):
    def test_checked_fixture_loads_expected_inventory(self) -> None:
        fixture = lab.load_fixture(FIXTURE_PATH)
        self.assertEqual([contract.space_id for contract in fixture.contracts], ["toy-v1", "toy-v2"])
        self.assertEqual(len(fixture.items), 20)
        self.assertEqual(len(fixture.queries), 4)

    def test_duplicate_json_key_and_nonfinite_number_are_rejected(self) -> None:
        duplicate = self.write_raw('{"contracts":[],"contracts":[],"items":[],"queries":[]}')
        with self.assertRaisesRegex(lab.EmbeddingError, "重复字段"):
            lab.load_fixture(duplicate)
        nonfinite = self.write_raw('{"contracts":NaN,"items":[],"queries":[]}')
        with self.assertRaisesRegex(lab.EmbeddingError, "非有限"):
            lab.load_fixture(nonfinite)

    def test_top_level_and_contract_fields_are_exact(self) -> None:
        payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
        payload["extra"] = True
        with self.assertRaisesRegex(lab.EmbeddingError, "字段必须精确"):
            lab.load_fixture(self.write_json(payload))
        payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
        del payload["contracts"][0]["dtype"]
        with self.assertRaisesRegex(lab.EmbeddingError, "字段必须精确"):
            lab.load_fixture(self.write_json(payload))

    def test_duplicate_space_and_item_are_rejected(self) -> None:
        payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
        payload["contracts"][1]["space_id"] = "toy-v1"
        with self.assertRaisesRegex(lab.EmbeddingError, "space_id 重复"):
            lab.load_fixture(self.write_json(payload))
        payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
        payload["items"].append(payload["items"][0])
        with self.assertRaisesRegex(lab.EmbeddingError, "item 重复"):
            lab.load_fixture(self.write_json(payload))

    def test_item_rejects_missing_space_and_wrong_role(self) -> None:
        for field, value, message in [
            ("space_id", "missing", "不存在空间"),
            ("role", "classification", "role 不符合"),
        ]:
            payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
            payload["items"][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                lab.EmbeddingError, message
            ):
                lab.load_fixture(self.write_json(payload))

    def test_vector_rejects_dimension_bool_zero_and_bad_normalization(self) -> None:
        mutations = [
            ([1.0], "维度必须"),
            ([True, 0.0, 0.0, 0.0], "有限数值"),
            ([0.0, 0.0, 0.0, 0.0], "零向量"),
        ]
        for vector, message in mutations:
            payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
            payload["items"][0]["vector"] = vector
            with self.subTest(vector=vector), self.assertRaisesRegex(
                lab.EmbeddingError, message
            ):
                lab.load_fixture(self.write_json(payload))
        payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
        first_v2 = next(
            item for item in payload["items"] if item["space_id"] == "toy-v2"
        )
        first_v2["vector"] = [2.0, 0.0, 0.0, 0.0, 0.0]
        with self.assertRaisesRegex(lab.EmbeddingError, "normalized=True"):
            lab.load_fixture(self.write_json(payload))

    def test_acl_duplicates_and_bad_text_are_rejected(self) -> None:
        payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
        payload["items"][0]["acl"] = ["employees", "employees"]
        with self.assertRaisesRegex(lab.EmbeddingError, "acl 不得重复"):
            lab.load_fixture(self.write_json(payload))
        payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
        payload["items"][0]["text"] = "   "
        with self.assertRaisesRegex(lab.EmbeddingError, "非空文本"):
            lab.load_fixture(self.write_json(payload))

    def test_crlf_text_is_normalized_before_hashing(self) -> None:
        payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
        for item in payload["items"]:
            if item["item_id"] == "doc-timeout":
                item["text"] = "第一行\r\n第二行"
        fixture = lab.load_fixture(self.write_json(payload))
        changed = [
            item for item in fixture.items if item.item_id == "doc-timeout"
        ]
        self.assertEqual({item.text for item in changed}, {"第一行\n第二行"})
        self.assertEqual(len({item.content_sha256 for item in changed}), 1)

    def test_query_rejects_duplicate_id_bad_grade_and_missing_item(self) -> None:
        payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
        payload["queries"].append(payload["queries"][0])
        with self.assertRaisesRegex(lab.EmbeddingError, "case_id 重复"):
            lab.load_fixture(self.write_json(payload))
        payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
        payload["queries"][0]["relevance"]["doc-deploy"] = True
        with self.assertRaisesRegex(lab.EmbeddingError, "grade"):
            lab.load_fixture(self.write_json(payload))
        payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
        payload["queries"][0]["query_item_id"] = "missing"
        with self.assertRaisesRegex(lab.EmbeddingError, "缺少 query item"):
            lab.load_fixture(self.write_json(payload))

    def test_query_gold_must_exist_be_document_and_be_authorized(self) -> None:
        payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
        payload["queries"][0]["relevance"] = {"missing": 3}
        with self.assertRaisesRegex(lab.EmbeddingError, "缺少 relevant document"):
            lab.load_fixture(self.write_json(payload))
        payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
        payload["queries"][0]["relevance"] = {"q-deploy": 3}
        with self.assertRaisesRegex(lab.EmbeddingError, "不是 document role"):
            lab.load_fixture(self.write_json(payload))
        payload = json.loads(json.dumps(self.payload, ensure_ascii=False))
        payload["queries"][0]["subject_groups"] = ["employees"]
        with self.assertRaisesRegex(lab.EmbeddingError, "无权读取"):
            lab.load_fixture(self.write_json(payload))


class SearchAndMetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = lab.load_fixture(FIXTURE_PATH)

    def test_exact_search_returns_expected_rankings_in_both_spaces(self) -> None:
        expected = ["doc-retry", "doc-credentials", "doc-timeout"]
        for space_id in ("toy-v1", "toy-v2"):
            ranked = lab.search(
                self.fixture,
                space_id=space_id,
                query_item_id="q-retry",
                subject_groups=["employees"],
                k=3,
            )
            self.assertEqual([item.item_id for item in ranked], expected)

    def test_acl_filter_prevents_cross_group_document_from_being_scored(self) -> None:
        employees = lab.search(
            self.fixture,
            space_id="toy-v1",
            query_item_id="q-deploy",
            subject_groups=["employees"],
            k=10,
        )
        platform = lab.search(
            self.fixture,
            space_id="toy-v1",
            query_item_id="q-deploy",
            subject_groups=["platform"],
            k=10,
        )
        self.assertNotIn("doc-deploy", [item.item_id for item in employees])
        self.assertEqual([item.item_id for item in platform], ["doc-deploy"])

    def test_empty_groups_fail_closed_and_ties_are_deterministic(self) -> None:
        self.assertEqual(
            lab.search(
                self.fixture,
                space_id="toy-v1",
                query_item_id="q-timeout",
                subject_groups=[],
                k=3,
            ),
            [],
        )
        first = lab.search(
            self.fixture,
            space_id="toy-v1",
            query_item_id="q-image",
            subject_groups=["employees"],
            k=5,
        )
        second = lab.search(
            self.fixture,
            space_id="toy-v1",
            query_item_id="q-image",
            subject_groups=["employees"],
            k=5,
        )
        self.assertEqual(first, second)

    def test_search_rejects_invalid_k_space_query_and_role(self) -> None:
        calls = [
            {"space_id": "toy-v1", "query_item_id": "q-timeout", "subject_groups": ["employees"], "k": 0},
            {"space_id": "missing", "query_item_id": "q-timeout", "subject_groups": ["employees"], "k": 1},
            {"space_id": "toy-v1", "query_item_id": "missing", "subject_groups": ["employees"], "k": 1},
            {"space_id": "toy-v1", "query_item_id": "doc-timeout", "subject_groups": ["employees"], "k": 1},
        ]
        for values in calls:
            with self.subTest(values=values), self.assertRaises(lab.EmbeddingError):
                lab.search(self.fixture, **values)

    def test_recall_reciprocal_rank_and_ndcg_known_cases(self) -> None:
        relevance = {"a": 3, "b": 1}
        self.assertEqual(lab.recall_at_k(["a"], relevance), 0.5)
        self.assertEqual(lab.reciprocal_rank(["x", "b"], relevance), 0.5)
        perfect = lab.ndcg_at_k(["a", "b"], relevance, 2)
        reversed_score = lab.ndcg_at_k(["b", "a"], relevance, 2)
        self.assertAlmostEqual(perfect, 1.0)
        self.assertLess(reversed_score, perfect)

    def test_metrics_reject_empty_gold_and_bad_k(self) -> None:
        with self.assertRaises(lab.EmbeddingError):
            lab.recall_at_k(["a"], {})
        with self.assertRaises(lab.EmbeddingError):
            lab.reciprocal_rank(["a"], {})
        with self.assertRaises(lab.EmbeddingError):
            lab.ndcg_at_k(["a"], {"a": 1}, 0)

    def test_evaluation_reports_per_query_and_subgroups(self) -> None:
        report = lab.evaluate_space(self.fixture, space_id="toy-v1", k=3)
        self.assertEqual(report["query_count"], 4)
        self.assertEqual(report["mean_recall_at_k"], 1.0)
        self.assertEqual(report["mrr"], 1.0)
        self.assertEqual(report["mean_ndcg_at_k"], 1.0)
        self.assertIn("multi-evidence", report["subgroups"])
        self.assertEqual(len(report["details"]), 4)

    def test_inventory_exposes_space_cost_and_norm_contract(self) -> None:
        v1 = lab.inventory_report(self.fixture, space_id="toy-v1")
        v2 = lab.inventory_report(self.fixture, space_id="toy-v2")
        self.assertEqual(v1["estimated_raw_vector_bytes"], 160)
        self.assertEqual(v2["estimated_raw_vector_bytes"], 200)
        self.assertEqual(v1["norm_max"], 2.0)
        self.assertEqual(v2["norm_min"], 1.0)
        self.assertNotEqual(v1["contract_signature"], v2["contract_signature"])


class MigrationAndCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = lab.load_fixture(FIXTURE_PATH)

    def test_migration_audit_separates_mechanical_and_quality_gates(self) -> None:
        report = lab.migration_audit(
            self.fixture, old_space_id="toy-v1", new_space_id="toy-v2", k=3
        )
        self.assertFalse(report["vectors_directly_comparable"])
        self.assertTrue(report["inventory_match"])
        self.assertTrue(report["canonical_match"])
        self.assertTrue(report["mechanical_gates_pass"])
        self.assertEqual(report["quality_delta_new_minus_old"]["mean_recall_at_k"], 0.0)
        self.assertEqual(report["mean_top_k_jaccard"], 0.875)
        self.assertTrue(report["quality_decision_required"])

    def test_migration_audit_detects_inventory_and_canonical_drift(self) -> None:
        changed_items = list(self.fixture.items)
        target_index = next(
            index
            for index, item in enumerate(changed_items)
            if item.space_id == "toy-v2" and item.item_id == "doc-timeout"
        )
        changed_items[target_index] = replace(
            changed_items[target_index],
            text="已漂移正文",
            content_sha256=lab._digest("已漂移正文"),
        )
        canonical_fixture = replace(self.fixture, items=tuple(changed_items))
        canonical = lab.migration_audit(
            canonical_fixture,
            old_space_id="toy-v1",
            new_space_id="toy-v2",
            k=3,
        )
        self.assertFalse(canonical["canonical_match"])
        self.assertIn("doc-timeout", canonical["canonical_mismatches"])

        missing_items = tuple(
            item
            for item in self.fixture.items
            if not (item.space_id == "toy-v2" and item.item_id == "doc-noise")
        )
        inventory_fixture = replace(self.fixture, items=missing_items)
        inventory = lab.migration_audit(
            inventory_fixture,
            old_space_id="toy-v1",
            new_space_id="toy-v2",
            k=3,
        )
        self.assertFalse(inventory["inventory_match"])
        self.assertEqual(inventory["only_old"], ["doc-noise"])
        self.assertFalse(inventory["mechanical_gates_pass"])

    def test_migration_rejects_same_space(self) -> None:
        with self.assertRaises(lab.EmbeddingError):
            lab.migration_audit(
                self.fixture,
                old_space_id="toy-v1",
                new_space_id="toy-v1",
                k=3,
            )

    def test_experiment_is_deterministic_in_process(self) -> None:
        first = lab.run_experiment(self.fixture, k=3)
        second = lab.run_experiment(self.fixture, k=3)
        self.assertEqual(first, second)
        self.assertIn("hand-authored vectors", first["fixture_notice"])

    def test_cli_output_is_identical_under_normal_and_optimized_python(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        script = str(HERE / "evaluate_embedding_space.py")
        normal = subprocess.run(
            [sys.executable, "-B", "-W", "error", script],
            cwd=HERE,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        optimized = subprocess.run(
            [sys.executable, "-B", "-O", "-W", "error", script],
            cwd=HERE,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(normal.stdout, optimized.stdout)
        parsed = json.loads(normal.stdout.decode("utf-8"))
        self.assertEqual(parsed["k"], 3)

    def test_cli_rejects_nonpositive_k(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-W",
                "error",
                str(HERE / "evaluate_embedding_space.py"),
                "--k",
                "0",
            ],
            cwd=HERE,
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("k", result.stderr.decode("utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

