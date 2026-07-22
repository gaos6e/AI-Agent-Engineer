"""Tests for the failure-safe deterministic reranker teaching adapter."""

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
SCRIPT = HERE / "toy_reranker.py"
FIXTURE = HERE / "reranker-fixture.json"
SPEC = importlib.util.spec_from_file_location("toy_reranker", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("无法加载 toy_reranker.py")
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


class MathAndContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = lab.load_fixture(FIXTURE)
        cls.candidates = {
            candidate.candidate_id: candidate for candidate in cls.fixture.candidates
        }

    def test_analyzer_normalises_ascii_and_builds_cjk_bigrams(self) -> None:
        tokens = lab.analyze("Ｅ０４２ 退款到账")
        self.assertEqual(tokens[0], "e042")
        self.assertIn("退款", tokens)
        self.assertIn("到账", tokens)

    def test_rule_score_exposes_finite_features(self) -> None:
        result = lab.transparent_rule_score(
            self.fixture.query,
            self.candidates["d-04-refund-time"],
        )
        self.assertEqual(result.candidate_id, "d-04-refund-time")
        self.assertGreater(result.score, 0.0)
        self.assertEqual(
            set(result.feature_map()),
            {"body_coverage", "exact_phrase", "title_coverage"},
        )

    def test_ranking_metrics_use_graded_qrels(self) -> None:
        metrics = lab.ranking_metrics(
            ["low", "high", "none"],
            {"low": 1, "high": 3},
            top_n=3,
        )
        self.assertEqual(metrics["mrr"], 1.0)
        self.assertEqual(metrics["precision"], 0.666667)
        self.assertGreater(metrics["ndcg"], 0.0)
        self.assertLess(metrics["ndcg"], 1.0)

    def test_canonical_cap_preserves_order_and_fills_from_later_items(self) -> None:
        ordered = [
            "d-04-refund-time",
            "d-05-refund-time-faq",
            "d-06-refund-delay",
            "d-02-refund-apply",
        ]
        selected = lab.select_with_canonical_cap(
            ordered,
            self.candidates,
            top_n=3,
            max_per_canonical=1,
        )
        self.assertEqual(
            selected,
            ["d-04-refund-time", "d-06-refund-delay", "d-02-refund-apply"],
        )

    def test_output_contract_accepts_exact_valid_set(self) -> None:
        window = list(self.fixture.candidates[:3])
        raw = [
            lab.transparent_rule_score(self.fixture.query, candidate)
            for candidate in window
        ]
        parsed = lab.validate_model_output(raw, window)
        self.assertEqual(set(parsed), {candidate.candidate_id for candidate in window})

    def test_output_contract_rejects_empty_duplicate_unknown_missing_and_nonfinite(self) -> None:
        window = list(self.fixture.candidates[:2])
        valid = [
            lab.transparent_rule_score(self.fixture.query, candidate)
            for candidate in window
        ]
        cases = [
            [],
            [valid[0], valid[0]],
            [replace(valid[0], candidate_id="unknown"), valid[1]],
            [valid[0]],
            [replace(valid[0], score=math.nan), valid[1]],
            [replace(valid[0], score=10**400), valid[1]],
            [replace(valid[0], features=(("bad", "x"),)), valid[1]],
            [replace(valid[0], features=(("bad", 10**400),)), valid[1]],
        ]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(lab.OutputContractError):
                lab.validate_model_output(value, window)


class FixtureValidationTests(TemporaryFixtureMixin, unittest.TestCase):
    def test_valid_fixture_loads(self) -> None:
        fixture = lab.load_fixture(FIXTURE)
        self.assertEqual(len(fixture.candidates), 9)
        self.assertEqual(len(fixture.qrels), 4)
        self.assertEqual(len(fixture.must_not_return), 3)
        self.assertEqual(fixture.query.authorization_revision, "authz-alpha-r7")

    def test_duplicate_key_and_nonfinite_json_are_rejected(self) -> None:
        self.path.write_text(
            '{"schema_version":1,"schema_version":1}', encoding="utf-8"
        )
        with self.assertRaisesRegex(lab.RerankerError, "重复字段"):
            lab.load_fixture(self.path)
        self.path.write_text('{"schema_version":NaN}', encoding="utf-8")
        with self.assertRaisesRegex(lab.RerankerError, "非有限"):
            lab.load_fixture(self.path)

    def test_top_fields_and_schema_version_are_exact(self) -> None:
        value = raw_fixture()
        value["extra"] = True
        with self.assertRaisesRegex(lab.RerankerError, "字段必须精确"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["schema_version"] = 3
        with self.assertRaisesRegex(lab.RerankerError, "schema_version"):
            lab.load_fixture(self.write(value))

    def test_query_date_groups_and_authorization_revision_are_checked(self) -> None:
        value = raw_fixture()
        value["query"]["as_of"] = "2026-7-14"
        with self.assertRaisesRegex(lab.RerankerError, "YYYY-MM-DD"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["query"]["subject_groups"] = ["z", "a"]
        with self.assertRaisesRegex(lab.RerankerError, "字典序"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["query"]["authorization_revision"] = ""
        with self.assertRaisesRegex(lab.RerankerError, "非空字符串"):
            lab.load_fixture(self.write(value))

    def test_settings_require_positive_values_and_top_not_above_window(self) -> None:
        cases = [
            ("candidate_window", 0),
            ("output_top_n", True),
            ("max_per_canonical", -1),
        ]
        for field, replacement in cases:
            value = raw_fixture()
            value["settings"][field] = replacement
            with self.subTest(field=field), self.assertRaises(lab.RerankerError):
                lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["settings"]["output_top_n"] = 7
        with self.assertRaisesRegex(lab.RerankerError, "不得大于"):
            lab.load_fixture(self.write(value))

    def test_candidate_status_score_acl_and_dates_are_checked(self) -> None:
        mutations = [
            ("status", "deleted"),
            ("first_score", True),
            ("first_score", 10**400),
            ("acl", ["guests", "employees"]),
            ("effective_from", "2026-1-01"),
        ]
        for field, replacement in mutations:
            value = raw_fixture()
            value["candidates"][0][field] = replacement
            with self.subTest(field=field), self.assertRaises(lab.RerankerError):
                lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["candidates"][0]["effective_to"] = "2024-01-01"
        with self.assertRaisesRegex(lab.RerankerError, "from < to"):
            lab.load_fixture(self.write(value))

    def test_candidate_ids_and_ranks_are_unique_and_contiguous(self) -> None:
        value = raw_fixture()
        value["candidates"][1]["id"] = value["candidates"][0]["id"]
        with self.assertRaisesRegex(lab.RerankerError, "candidate id 重复"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["candidates"][1]["first_rank"] = 1
        with self.assertRaisesRegex(lab.RerankerError, "first_rank 重复"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["candidates"][8]["first_rank"] = 10
        with self.assertRaisesRegex(lab.RerankerError, "连续"):
            lab.load_fixture(self.write(value))

    def test_qrels_must_exist_be_eligible_and_use_integer_grades(self) -> None:
        value = raw_fixture()
        value["qrels"] = {"unknown": 3}
        with self.assertRaisesRegex(lab.RerankerError, "未知"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["candidates"][0]["status"] = "draft"
        value["qrels"] = {"d-01-membership": 3}
        with self.assertRaisesRegex(lab.RerankerError, "不满足硬过滤"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["qrels"]["d-02-refund-apply"] = True
        with self.assertRaisesRegex(lab.RerankerError, "1..3"):
            lab.load_fixture(self.write(value))

    def test_denied_candidates_must_exist_be_ineligible_and_not_overlap_qrels(self) -> None:
        value = raw_fixture()
        value["must_not_return"] = ["unknown"]
        with self.assertRaisesRegex(lab.RerankerError, "未知"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["must_not_return"] = ["d-01-membership"]
        with self.assertRaisesRegex(lab.RerankerError, "仍可访问"):
            lab.load_fixture(self.write(value))
        value = raw_fixture()
        value["must_not_return"].append("d-02-refund-apply")
        value["must_not_return"].sort()
        with self.assertRaisesRegex(lab.RerankerError, "不得重叠"):
            lab.load_fixture(self.write(value))

    def test_size_limit_is_enforced_before_parsing(self) -> None:
        with mock.patch.object(lab, "MAX_FIXTURE_BYTES", 10):
            with self.assertRaisesRegex(lab.RerankerError, "2 MiB"):
                lab.load_fixture(FIXTURE)


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = lab.load_fixture(FIXTURE)
        cls.candidates = {
            candidate.candidate_id: candidate for candidate in cls.fixture.candidates
        }

    def test_eligibility_reports_three_distinct_denial_reasons(self) -> None:
        self.assertEqual(
            lab.eligibility_reason(
                self.candidates["d-07-beta-private"], self.fixture.query
            ),
            "wrong_tenant",
        )
        self.assertEqual(
            lab.eligibility_reason(
                self.candidates["d-08-expired-policy"], self.fixture.query
            ),
            "expired",
        )
        self.assertEqual(
            lab.eligibility_reason(
                self.candidates["d-09-internal-runbook"], self.fixture.query
            ),
            "acl_denied",
        )

    def test_effective_interval_is_half_open(self) -> None:
        candidate = self.candidates["d-01-membership"]
        starts_now = replace(candidate, effective_from=self.fixture.query.as_of)
        ends_now = replace(candidate, effective_to=self.fixture.query.as_of)
        self.assertIsNone(lab.eligibility_reason(starts_now, self.fixture.query))
        self.assertEqual("expired", lab.eligibility_reason(ends_now, self.fixture.query))

    def test_normal_pipeline_improves_ranking_and_is_secure(self) -> None:
        report = lab.run_pipeline(self.fixture, failure_mode="none")
        self.assertEqual(report["visibility"], "protected_audit")
        self.assertIn("not a public response", report["notice"])
        self.assertEqual(
            report["evidence"]["authorization_revision"],
            self.fixture.query.authorization_revision,
        )
        self.assertEqual(
            report["evidence"]["fixture_sha256"], report["fixture"]["signature"]
        )
        self.assertRegex(report["evidence"]["fixture_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(report["evidence"]["evidence_sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(report["rerank_applied"])
        self.assertIsNone(report["fallback_reason"])
        self.assertEqual(report["candidate_recall_at_window"], 1.0)
        self.assertEqual(report["first_stage"]["metrics"]["ndcg"], 0.060708)
        self.assertEqual(report["final"]["metrics"]["ndcg"], 1.0)
        self.assertEqual(report["security_violations"], [])
        self.assertEqual(
            [row["candidate_id"] for row in report["final"]["ranking"]],
            [
                "d-04-refund-time",
                "d-05-refund-time-faq",
                "d-06-refund-delay",
            ],
        )

    def test_fingerprints_bind_every_normalized_security_and_scoring_input(self) -> None:
        baseline = lab.run_pipeline(self.fixture, failure_mode="none")

        def change_query_tenant(value: dict[str, object]) -> None:
            value["query"]["tenant_id"] = "alpha-v2"
            for candidate in value["candidates"]:
                if candidate["tenant_id"] == "alpha":
                    candidate["tenant_id"] = "alpha-v2"

        def swap_first_ranks(value: dict[str, object]) -> None:
            value["candidates"][0]["first_rank"] = 2
            value["candidates"][1]["first_rank"] = 1

        mutations = {
            "query_id": lambda value: value["query"].__setitem__("id", "q-refund-time-v2"),
            "query_text": lambda value: value["query"].__setitem__(
                "text", "退款审核通过后多久原路到账"
            ),
            "query_tenant": change_query_tenant,
            "query_groups": lambda value: value["query"].__setitem__(
                "subject_groups", ["guests", "reviewers"]
            ),
            "authorization_revision": lambda value: value["query"].__setitem__(
                "authorization_revision", "authz-alpha-r8"
            ),
            "as_of": lambda value: value["query"].__setitem__("as_of", "2026-07-15"),
            "candidate_id": lambda value: value["candidates"][0].__setitem__(
                "id", "d-01-membership-v2"
            ),
            "canonical_document_id": lambda value: value["candidates"][0].__setitem__(
                "canonical_document_id", "doc-membership-v2"
            ),
            "candidate_title": lambda value: value["candidates"][0].__setitem__(
                "title", "会员续费规则（修订）"
            ),
            "candidate_text": lambda value: value["candidates"][0].__setitem__(
                "text", "会员自动续费可在扣费前关闭。"
            ),
            "candidate_tenant": lambda value: value["candidates"][0].__setitem__(
                "tenant_id", "beta"
            ),
            "candidate_acl": lambda value: value["candidates"][0].__setitem__(
                "acl", ["employees", "guests", "reviewers"]
            ),
            "candidate_status": lambda value: value["candidates"][0].__setitem__(
                "status", "draft"
            ),
            "effective_from": lambda value: value["candidates"][0].__setitem__(
                "effective_from", "2025-01-02"
            ),
            "effective_to": lambda value: value["candidates"][0].__setitem__(
                "effective_to", "2027-01-01"
            ),
            "source_revision": lambda value: value["candidates"][0].__setitem__(
                "source_revision", "r1b"
            ),
            "first_rank": swap_first_ranks,
            "first_score": lambda value: value["candidates"][0].__setitem__(
                "first_score", 0.92
            ),
            "settings": lambda value: value["settings"].__setitem__(
                "candidate_window", 7
            ),
            "qrels": lambda value: value["qrels"].__setitem__(
                "d-02-refund-apply", 2
            ),
            "must_not_return": lambda value: value.__setitem__(
                "must_not_return", ["d-07-beta-private", "d-08-expired-policy"]
            ),
        }
        for label, mutate in mutations.items():
            value = raw_fixture()
            mutate(value)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "fixture.json"
                path.write_text(
                    json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)
                    + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
                changed = lab.run_pipeline(lab.load_fixture(path), failure_mode="none")
            with self.subTest(field=label):
                self.assertNotEqual(
                    baseline["evidence"]["fixture_sha256"],
                    changed["evidence"]["fixture_sha256"],
                )
                self.assertNotEqual(
                    baseline["evidence"]["evidence_sha256"],
                    changed["evidence"]["evidence_sha256"],
                )

    def test_evidence_fingerprint_binds_runtime_overrides(self) -> None:
        baseline = lab.run_pipeline(self.fixture, failure_mode="none")
        changed = lab.run_pipeline(
            self.fixture,
            failure_mode="none",
            candidate_window=5,
        )
        self.assertEqual(
            baseline["evidence"]["fixture_sha256"],
            changed["evidence"]["fixture_sha256"],
        )
        self.assertNotEqual(
            baseline["evidence"]["evidence_sha256"],
            changed["evidence"]["evidence_sha256"],
        )

    def test_small_window_sets_a_lower_candidate_recall_ceiling(self) -> None:
        report = lab.run_pipeline(
            self.fixture,
            failure_mode="none",
            candidate_window=3,
            output_top_n=3,
        )
        self.assertEqual(report["candidate_recall_at_window"], 0.25)
        self.assertNotIn(
            "d-04-refund-time",
            [row["candidate_id"] for row in report["final"]["ranking"]],
        )

    def test_all_failure_modes_fall_back_to_safe_first_stage_order(self) -> None:
        expected = ["d-01-membership", "d-02-refund-apply", "d-03-login"]
        expected_reasons = {
            "timeout": "timeout",
            "error": "provider_error",
            "empty": "invalid_output",
            "malformed": "invalid_output",
        }
        for mode, reason in expected_reasons.items():
            report = lab.run_pipeline(self.fixture, failure_mode=mode)
            with self.subTest(mode=mode):
                self.assertFalse(report["rerank_applied"])
                self.assertEqual(report["fallback_reason"], reason)
                self.assertEqual(
                    [row["candidate_id"] for row in report["final"]["ranking"]],
                    expected,
                )
                self.assertEqual(report["security_violations"], [])
                self.assertEqual(report["final"], report["first_stage"])

    def test_canonical_cap_one_selects_diverse_later_candidate(self) -> None:
        report = lab.run_pipeline(
            self.fixture,
            failure_mode="none",
            max_per_canonical=1,
        )
        self.assertEqual(
            [row["candidate_id"] for row in report["final"]["ranking"]],
            ["d-04-refund-time", "d-06-refund-delay", "d-02-refund-apply"],
        )

    def test_empty_identity_fails_closed_before_model(self) -> None:
        fixture = replace(
            self.fixture,
            query=replace(self.fixture.query, subject_groups=()),
        )
        report = lab.run_pipeline(fixture, failure_mode="none")
        self.assertFalse(report["rerank_applied"])
        self.assertEqual(report["fallback_reason"], "empty_candidate_window")
        self.assertEqual(report["final"]["ranking"], [])
        self.assertEqual(report["security_violations"], [])

    def test_pipeline_rejects_zero_inverted_window_and_unknown_failure(self) -> None:
        calls = [
            {"failure_mode": "none", "candidate_window": 0},
            {"failure_mode": "none", "candidate_window": 2, "output_top_n": 3},
            {"failure_mode": "unknown"},
            {"failure_mode": "none", "max_per_canonical": 0},
        ]
        for values in calls:
            with self.subTest(values=values), self.assertRaises(lab.RerankerError):
                lab.run_pipeline(self.fixture, **values)
        fixture = replace(
            self.fixture,
            query=replace(self.fixture.query, authorization_revision=""),
        )
        with self.assertRaisesRegex(lab.RerankerError, "authorization_revision"):
            lab.run_pipeline(fixture, failure_mode="none")


class CliTests(unittest.TestCase):
    def test_cli_output_matches_under_normal_and_optimized_python(self) -> None:
        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        args = [str(SCRIPT), "--fixture", str(FIXTURE)]
        normal = subprocess.run(
            [sys.executable, "-B", "-W", "error", *args],
            cwd=HERE,
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        optimized = subprocess.run(
            [sys.executable, "-B", "-O", "-W", "error", *args],
            cwd=HERE,
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(
            normal.returncode,
            0,
            normal.stderr.decode("utf-8", errors="replace"),
        )
        self.assertEqual(
            optimized.returncode,
            0,
            optimized.stderr.decode("utf-8", errors="replace"),
        )
        self.assertEqual(normal.stdout, optimized.stdout)
        self.assertEqual(normal.stderr, b"")
        report = json.loads(normal.stdout.decode("utf-8"))
        self.assertIn("not a cross-encoder", report["notice"])

    def test_cli_failure_mode_returns_successful_fallback_report(self) -> None:
        process = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                "--fixture",
                str(FIXTURE),
                "--failure",
                "timeout",
            ],
            cwd=HERE,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        report = json.loads(process.stdout.decode("utf-8"))
        self.assertFalse(report["rerank_applied"])
        self.assertEqual(report["fallback_reason"], "timeout")

    def test_cli_invalid_fixture_returns_controlled_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{}\n", encoding="utf-8")
            process = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "--fixture", str(path)],
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

    def test_cli_overflowing_score_returns_controlled_error(self) -> None:
        value = raw_fixture()
        value["candidates"][0]["first_score"] = 10**400
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "overflow.json"
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            process = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "--fixture", str(path)],
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
