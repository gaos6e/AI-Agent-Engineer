from __future__ import annotations

import contextlib
import copy
import io
import json
import math
import tempfile
import unittest
from pathlib import Path

import evaluate_agent_outputs as evaluator


class EvaluationPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dataset = evaluator.validate_dataset(evaluator.load_json(evaluator.DEFAULT_DATASET))
        cls.rubric = evaluator.validate_rubric(evaluator.load_json(evaluator.DEFAULT_RUBRIC))
        cls.pass_predictions = evaluator.validate_predictions(
            evaluator.load_json(evaluator.DEFAULT_PREDICTIONS), cls.dataset
        )
        cls.regression_path = evaluator.HERE / "predictions_regression.json"
        cls.regression_predictions = evaluator.validate_predictions(
            evaluator.load_json(cls.regression_path), cls.dataset
        )

    def test_fixtures_validate(self) -> None:
        self.assertEqual(self.dataset["schema_version"], "eval-dataset-v1")
        self.assertEqual(self.rubric["schema_version"], "eval-rubric-v1")
        self.assertEqual(len(self.pass_predictions["releases"]), 2)

    def test_pass_fixture_passes(self) -> None:
        decision = evaluator.evaluate(
            self.dataset, self.rubric, self.pass_predictions, "candidate-pass"
        )
        self.assertEqual(decision.action, "PASS")
        self.assertEqual(decision.candidate_metrics["pass_rate"], 1.0)

    def test_regression_fixture_blocks(self) -> None:
        decision = evaluator.evaluate(
            self.dataset,
            self.rubric,
            self.regression_predictions,
            "candidate-regression",
        )
        self.assertEqual(decision.action, "BLOCK")

    def test_critical_failure_has_first_priority(self) -> None:
        decision = evaluator.evaluate(
            self.dataset,
            self.rubric,
            self.regression_predictions,
            "candidate-regression",
        )
        self.assertTrue(decision.primary_reason.startswith("critical safety/privacy"))
        self.assertIn("test-safety-negative", decision.primary_reason)

    def test_critical_failure_blocks_despite_aggregate_gate_pass(self) -> None:
        decision = evaluator.evaluate(
            self.dataset,
            self.rubric,
            self.regression_predictions,
            "candidate-regression",
        )
        self.assertGreaterEqual(
            decision.candidate_metrics["pass_rate"],
            self.rubric["gates"]["min_overall_pass_rate"],
        )
        self.assertEqual(decision.action, "BLOCK")

    def test_baseline_confusion_matrix(self) -> None:
        decision = evaluator.evaluate(
            self.dataset, self.rubric, self.pass_predictions, "candidate-pass"
        )
        self.assertEqual(
            decision.baseline_metrics["confusion_matrix"],
            {"tp": 2, "fp": 1, "tn": 2, "fn": 1},
        )

    def test_candidate_precision_recall_f1(self) -> None:
        decision = evaluator.evaluate(
            self.dataset, self.rubric, self.pass_predictions, "candidate-pass"
        )
        self.assertEqual(decision.candidate_metrics["precision"], 1.0)
        self.assertEqual(decision.candidate_metrics["recall"], 1.0)
        self.assertEqual(decision.candidate_metrics["f1"], 1.0)

    def test_f1_formula(self) -> None:
        self.assertAlmostEqual(evaluator.f1_or_none(0.5, 1.0), 2.0 / 3.0)

    def test_zero_denominator_is_unknown(self) -> None:
        self.assertIsNone(evaluator.divide_or_none(0, 0))
        self.assertIsNone(evaluator.f1_or_none(None, 1.0))

    def test_nearest_rank_percentile(self) -> None:
        self.assertEqual(evaluator.nearest_rank([1.0, 2.0, 3.0, 100.0], 0.95), 100.0)

    def test_empty_percentile_is_rejected(self) -> None:
        with self.assertRaises(evaluator.ContractError):
            evaluator.nearest_rank([], 0.95)

    def test_bootstrap_is_seeded_and_deterministic(self) -> None:
        first = evaluator.bootstrap_interval([0.0, 1.0, 0.0], 500, 7, 0.95)
        second = evaluator.bootstrap_interval([0.0, 1.0, 0.0], 500, 7, 0.95)
        self.assertEqual(first, second)

    def test_fingerprint_is_stable_and_sensitive(self) -> None:
        first = evaluator.fingerprint(self.dataset, self.rubric, "candidate-pass")
        second = evaluator.fingerprint(self.dataset, self.rubric, "candidate-pass")
        changed = evaluator.fingerprint(self.dataset, self.rubric, "another-candidate")
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)

    def test_duplicate_case_id_is_rejected(self) -> None:
        dataset = copy.deepcopy(self.dataset)
        dataset["cases"][1]["id"] = dataset["cases"][0]["id"]
        with self.assertRaisesRegex(evaluator.ContractError, "unique"):
            evaluator.validate_dataset(dataset)

    def test_split_leakage_is_rejected(self) -> None:
        dataset = copy.deepcopy(self.dataset)
        dataset["cases"][4]["family_id"] = dataset["cases"][0]["family_id"]
        with self.assertRaisesRegex(evaluator.ContractError, "split leakage"):
            evaluator.validate_dataset(dataset)

    def test_missing_split_is_rejected(self) -> None:
        dataset = copy.deepcopy(self.dataset)
        dataset["cases"] = [
            case for case in dataset["cases"] if case["split"] != "development"
        ]
        with self.assertRaisesRegex(evaluator.ContractError, "train/development/test"):
            evaluator.validate_dataset(dataset)

    def test_test_split_must_be_frozen(self) -> None:
        dataset = copy.deepcopy(self.dataset)
        dataset["frozen_test"] = False
        with self.assertRaisesRegex(evaluator.ContractError, "frozen_test"):
            evaluator.validate_dataset(dataset)

    def test_unknown_dataset_field_is_rejected(self) -> None:
        dataset = copy.deepcopy(self.dataset)
        dataset["typo"] = "must not be ignored"
        with self.assertRaisesRegex(evaluator.ContractError, "unknown"):
            evaluator.validate_dataset(dataset)

    def test_boolean_is_not_a_numeric_gate(self) -> None:
        rubric = copy.deepcopy(self.rubric)
        rubric["gates"]["min_f1"] = True
        with self.assertRaisesRegex(evaluator.ContractError, "not boolean"):
            evaluator.validate_rubric(rubric)

    def test_nonfinite_gate_is_rejected(self) -> None:
        rubric = copy.deepcopy(self.rubric)
        rubric["gates"]["max_mean_cost_usd"] = math.inf
        with self.assertRaisesRegex(evaluator.ContractError, "finite"):
            evaluator.validate_rubric(rubric)

    def test_duplicate_release_id_is_rejected(self) -> None:
        predictions = copy.deepcopy(self.pass_predictions)
        predictions["releases"][1]["release_id"] = predictions["releases"][0]["release_id"]
        with self.assertRaisesRegex(evaluator.ContractError, "release IDs"):
            evaluator.validate_predictions(predictions, self.dataset)

    def test_missing_test_prediction_is_rejected(self) -> None:
        predictions = copy.deepcopy(self.pass_predictions)
        predictions["releases"][1]["records"].pop()
        with self.assertRaisesRegex(evaluator.ContractError, "exactly cover"):
            evaluator.validate_predictions(predictions, self.dataset)

    def test_dataset_version_mismatch_is_rejected(self) -> None:
        predictions = copy.deepcopy(self.pass_predictions)
        predictions["dataset_version"] = "wrong-version"
        with self.assertRaisesRegex(evaluator.ContractError, "does not match"):
            evaluator.validate_predictions(predictions, self.dataset)

    def test_duplicate_actions_are_rejected(self) -> None:
        predictions = copy.deepcopy(self.pass_predictions)
        predictions["releases"][1]["records"][0]["actions"] = ["read", "read"]
        with self.assertRaisesRegex(evaluator.ContractError, "duplicates"):
            evaluator.validate_predictions(predictions, self.dataset)

    def test_required_evidence_is_deterministic(self) -> None:
        case = next(case for case in self.dataset["cases"] if case["id"] == "test-zh-positive")
        records = evaluator.release_records(self.pass_predictions, "candidate-pass")
        record = copy.deepcopy(records["test-zh-positive"])
        record["evidence_present"] = False
        result = evaluator.grade_case(case, record)
        self.assertFalse(result["checks"]["evidence_requirement_met"])
        self.assertFalse(result["passed"])

    def test_forbidden_action_is_deterministic(self) -> None:
        case = next(
            case for case in self.dataset["cases"] if case["id"] == "test-safety-negative"
        )
        records = evaluator.release_records(self.pass_predictions, "candidate-pass")
        record = copy.deepcopy(records["test-safety-negative"])
        record["actions"] = ["refund_order"]
        result = evaluator.grade_case(case, record)
        self.assertFalse(result["checks"]["forbidden_actions_absent"])

    def test_regression_exposes_slice_gap(self) -> None:
        decision = evaluator.evaluate(
            self.dataset,
            self.rubric,
            self.regression_predictions,
            "candidate-regression",
        )
        self.assertEqual(decision.candidate_metrics["slice_pass_rate_gap"], 1.0)

    def test_unknown_candidate_is_rejected(self) -> None:
        with self.assertRaisesRegex(evaluator.ContractError, "release not found"):
            evaluator.evaluate(
                self.dataset, self.rubric, self.pass_predictions, "unknown-release"
            )

    def test_candidate_cannot_equal_baseline(self) -> None:
        with self.assertRaisesRegex(evaluator.ContractError, "must differ"):
            evaluator.evaluate(
                self.dataset, self.rubric, self.pass_predictions, "baseline-v1"
            )

    def test_main_pass_exit_code(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = evaluator.main([])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["action"], "PASS")
        self.assertEqual(stderr.getvalue(), "")

    def test_main_regression_exit_code(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = evaluator.main(
                [
                    "--predictions",
                    str(self.regression_path),
                    "--candidate",
                    "candidate-regression",
                ]
            )
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout.getvalue())["action"], "BLOCK")
        self.assertEqual(stderr.getvalue(), "")

    def test_main_contract_error_exit_code(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        invalid_path = evaluator.HERE / "eval_dataset_contract_error.json"
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = evaluator.main(["--dataset", str(invalid_path)])
        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("split leakage", stderr.getvalue())

    def test_nonstandard_json_nan_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(evaluator.ContractError, "non-standard"):
                evaluator.load_json(path)

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"value": 1, "value": 2}', encoding="utf-8")
            with self.assertRaisesRegex(evaluator.ContractError, "duplicate key"):
                evaluator.load_json(path)

    def test_report_contains_fingerprint_and_limitations(self) -> None:
        decision = evaluator.evaluate(
            self.dataset, self.rubric, self.pass_predictions, "candidate-pass"
        )
        report = evaluator.decision_to_dict(decision)
        self.assertEqual(len(report["evidence_fingerprint"]), 16)
        self.assertEqual(len(report["limitations"]), 3)

    def test_predictions_only_cover_frozen_test(self) -> None:
        expected = {
            case["id"] for case in self.dataset["cases"] if case["split"] == "test"
        }
        actual = set(evaluator.release_records(self.pass_predictions, "candidate-pass"))
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
