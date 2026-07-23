from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import run_benchmark as benchmark


class BenchmarkContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec_path = benchmark.HERE / "benchmark_spec.json"
        cls.protocol_mismatch_path = (
            benchmark.HERE / "benchmark_spec_protocol_mismatch.json"
        )
        cls.cases_path = benchmark.HERE / "benchmark_cases.json"
        cls.contract_error_path = (
            benchmark.HERE / "benchmark_cases_contract_error.json"
        )
        cls.pass_path = benchmark.HERE / "benchmark_results_pass.json"
        cls.regression_path = benchmark.HERE / "benchmark_results_regression.json"

    def load_valid(self) -> tuple[dict, dict, dict]:
        spec = benchmark.validate_spec(benchmark.load_json(self.spec_path))
        cases = benchmark.validate_cases(benchmark.load_json(self.cases_path), spec)
        results = benchmark.validate_results(
            benchmark.load_json(self.pass_path), spec, cases
        )
        return spec, cases, results

    def test_valid_package_loads(self) -> None:
        spec, cases, results = self.load_valid()
        self.assertEqual(spec["benchmark_id"], "readonly-order-agent")
        self.assertEqual(len(cases["cases"]), 7)
        self.assertEqual(len(results["systems"]), 2)

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"x": 1, "x": 2}', encoding="utf-8")
            with self.assertRaisesRegex(benchmark.ContractError, "duplicate key"):
                benchmark.load_json(path)

    def test_nonstandard_nan_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nan.json"
            path.write_text('{"x": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(benchmark.ContractError, "non-standard"):
                benchmark.load_json(path)

    def test_unknown_spec_field_is_rejected(self) -> None:
        spec = copy.deepcopy(benchmark.load_json(self.spec_path))
        spec["surprise"] = True
        with self.assertRaisesRegex(benchmark.ContractError, "unknown"):
            benchmark.validate_spec(spec)

    def test_private_test_must_be_frozen(self) -> None:
        spec = copy.deepcopy(benchmark.load_json(self.spec_path))
        spec["private_test_frozen"] = False
        with self.assertRaisesRegex(benchmark.ContractError, "must be true"):
            benchmark.validate_spec(spec)

    def test_bool_is_not_a_number(self) -> None:
        spec = copy.deepcopy(benchmark.load_json(self.spec_path))
        spec["gates"]["max_mean_cost_units"] = True
        with self.assertRaisesRegex(benchmark.ContractError, "not boolean"):
            benchmark.validate_spec(spec)

    def test_protocol_integer_rejects_bool(self) -> None:
        spec = copy.deepcopy(benchmark.load_json(self.spec_path))
        spec["protocol"]["max_steps"] = True
        with self.assertRaisesRegex(benchmark.ContractError, "not boolean"):
            benchmark.validate_spec(spec)

    def test_trial_count_requires_multiple_trials(self) -> None:
        spec = copy.deepcopy(benchmark.load_json(self.spec_path))
        spec["protocol"]["trial_count"] = 1
        with self.assertRaisesRegex(benchmark.ContractError, ">= 2"):
            benchmark.validate_spec(spec)

    def test_critical_trial_gate_cannot_be_weaker(self) -> None:
        spec = copy.deepcopy(benchmark.load_json(self.spec_path))
        spec["gates"]["critical_task_min_trial_success_rate"] = 0.5
        with self.assertRaisesRegex(benchmark.ContractError, "must be >="):
            benchmark.validate_spec(spec)

    def test_invalid_split_is_rejected(self) -> None:
        spec = benchmark.validate_spec(benchmark.load_json(self.spec_path))
        cases = copy.deepcopy(benchmark.load_json(self.cases_path))
        cases["cases"][0]["split"] = "validation"
        with self.assertRaisesRegex(benchmark.ContractError, "must be one of"):
            benchmark.validate_cases(cases, spec)

    def test_private_flag_must_match_split(self) -> None:
        spec = benchmark.validate_spec(benchmark.load_json(self.spec_path))
        cases = copy.deepcopy(benchmark.load_json(self.cases_path))
        cases["cases"][0]["is_private"] = True
        with self.assertRaisesRegex(benchmark.ContractError, "true only for test"):
            benchmark.validate_cases(cases, spec)

    def test_duplicate_case_id_is_rejected(self) -> None:
        spec = benchmark.validate_spec(benchmark.load_json(self.spec_path))
        cases = copy.deepcopy(benchmark.load_json(self.cases_path))
        cases["cases"][1]["id"] = cases["cases"][0]["id"]
        with self.assertRaisesRegex(benchmark.ContractError, "IDs must be unique"):
            benchmark.validate_cases(cases, spec)

    def test_family_cross_split_contamination_is_rejected(self) -> None:
        spec = benchmark.validate_spec(benchmark.load_json(self.spec_path))
        with self.assertRaisesRegex(benchmark.ContractError, "split contamination"):
            benchmark.validate_cases(
                benchmark.load_json(self.contract_error_path), spec
            )

    def test_all_three_splits_are_required(self) -> None:
        spec = benchmark.validate_spec(benchmark.load_json(self.spec_path))
        cases = copy.deepcopy(benchmark.load_json(self.cases_path))
        cases["cases"] = [case for case in cases["cases"] if case["split"] != "train"]
        with self.assertRaisesRegex(benchmark.ContractError, "train/development/test"):
            benchmark.validate_cases(cases, spec)

    def test_results_benchmark_mismatch_is_rejected(self) -> None:
        spec, cases, results = self.load_valid()
        changed = copy.deepcopy(results)
        changed["benchmark_id"] = "other"
        with self.assertRaisesRegex(benchmark.ContractError, "does not match spec"):
            benchmark.validate_results(changed, spec, cases)

    def test_results_dataset_mismatch_is_rejected(self) -> None:
        spec, cases, results = self.load_valid()
        changed = copy.deepcopy(results)
        changed["dataset_version"] = "other"
        with self.assertRaisesRegex(benchmark.ContractError, "does not match cases"):
            benchmark.validate_results(changed, spec, cases)

    def test_duplicate_system_ids_are_rejected(self) -> None:
        spec, cases, results = self.load_valid()
        changed = copy.deepcopy(results)
        changed["systems"][1]["system_id"] = "baseline-v1"
        with self.assertRaisesRegex(benchmark.ContractError, "system IDs"):
            benchmark.validate_results(changed, spec, cases)

    def test_exactly_one_baseline_and_candidate_are_required(self) -> None:
        spec, cases, results = self.load_valid()
        changed = copy.deepcopy(results)
        changed["systems"][1]["role"] = "baseline"
        with self.assertRaisesRegex(benchmark.ContractError, "exactly one"):
            benchmark.validate_results(changed, spec, cases)

    def test_baseline_id_must_match_spec(self) -> None:
        spec, cases, results = self.load_valid()
        changed = copy.deepcopy(results)
        changed["systems"][0]["system_id"] = "wrong-baseline"
        with self.assertRaisesRegex(benchmark.ContractError, "baseline system"):
            benchmark.validate_results(changed, spec, cases)

    def test_unknown_record_field_is_rejected(self) -> None:
        spec, cases, results = self.load_valid()
        changed = copy.deepcopy(results)
        changed["systems"][0]["records"][0]["extra"] = 1
        with self.assertRaisesRegex(benchmark.ContractError, "unknown"):
            benchmark.validate_results(changed, spec, cases)

    def test_duplicate_case_trial_is_rejected(self) -> None:
        spec, cases, results = self.load_valid()
        changed = copy.deepcopy(results)
        changed["systems"][0]["records"][1] = copy.deepcopy(
            changed["systems"][0]["records"][0]
        )
        with self.assertRaisesRegex(benchmark.ContractError, "duplicate case/trial"):
            benchmark.validate_results(changed, spec, cases)

    def test_missing_case_trial_is_not_silently_ignored(self) -> None:
        spec, cases, results = self.load_valid()
        changed = copy.deepcopy(results)
        changed["systems"][1]["records"].pop()
        with self.assertRaisesRegex(benchmark.ContractError, "exactly cover"):
            benchmark.validate_results(changed, spec, cases)

    def test_unknown_case_is_rejected(self) -> None:
        spec, cases, results = self.load_valid()
        changed = copy.deepcopy(results)
        changed["systems"][1]["records"][0]["case_id"] = "unknown-case"
        with self.assertRaisesRegex(benchmark.ContractError, "unknown="):
            benchmark.validate_results(changed, spec, cases)

    def test_trial_zero_is_rejected(self) -> None:
        spec, cases, results = self.load_valid()
        changed = copy.deepcopy(results)
        changed["systems"][1]["records"][0]["trial_id"] = 0
        with self.assertRaisesRegex(benchmark.ContractError, ">= 1"):
            benchmark.validate_results(changed, spec, cases)

    def test_latency_rejects_bool(self) -> None:
        spec, cases, results = self.load_valid()
        changed = copy.deepcopy(results)
        changed["systems"][1]["records"][0]["latency_ms"] = False
        with self.assertRaisesRegex(benchmark.ContractError, "not boolean"):
            benchmark.validate_results(changed, spec, cases)

    def test_nonfinite_programmatic_number_is_rejected(self) -> None:
        spec, cases, results = self.load_valid()
        changed = copy.deepcopy(results)
        changed["systems"][1]["records"][0]["cost_units"] = float("inf")
        with self.assertRaisesRegex(benchmark.ContractError, "finite"):
            benchmark.validate_results(changed, spec, cases)

    def test_unknown_status_name_is_rejected(self) -> None:
        spec, cases, results = self.load_valid()
        changed = copy.deepcopy(results)
        changed["systems"][1]["records"][0]["status"] = "missing"
        with self.assertRaisesRegex(benchmark.ContractError, "must be one of"):
            benchmark.validate_results(changed, spec, cases)

    def test_unknown_status_is_counted_as_failure(self) -> None:
        spec, cases, results = self.load_valid()
        baseline = benchmark.system_by_id(results, "baseline-v1")
        test_cases = [case for case in cases["cases"] if case["split"] == "test"]
        metrics = benchmark.calculate_metrics(spec, test_cases, baseline)
        self.assertEqual(metrics["unknown_trial_count"], 1)
        missing = next(
            item for item in metrics["task_results"] if item["case_id"] == "test-missing-id"
        )
        self.assertFalse(missing["task_pass"])

    def test_wrong_final_state_fails_trial(self) -> None:
        spec, cases, results = self.load_valid()
        case = next(case for case in cases["cases"] if case["id"] == "test-status")
        record = copy.deepcopy(results["systems"][1]["records"][0])
        record["final_state"] = "wrong"
        self.assertFalse(benchmark.grade_trial(case, record)["passed"])

    def test_forbidden_side_effect_fails_trial(self) -> None:
        spec, cases, results = self.load_valid()
        case = next(case for case in cases["cases"] if case["id"] == "test-safety")
        record = next(
            record
            for record in results["systems"][1]["records"]
            if record["case_id"] == "test-safety"
        )
        changed = copy.deepcopy(record)
        changed["side_effects"] = ["refund_order"]
        self.assertFalse(benchmark.grade_trial(case, changed)["passed"])

    def test_disallowed_tool_fails_trial(self) -> None:
        spec, cases, results = self.load_valid()
        case = next(case for case in cases["cases"] if case["id"] == "test-privacy")
        record = next(
            record
            for record in results["systems"][1]["records"]
            if record["case_id"] == "test-privacy"
        )
        changed = copy.deepcopy(record)
        changed["tools_used"] = ["admin_lookup"]
        self.assertFalse(benchmark.grade_trial(case, changed)["passed"])

    def test_pass_fixture_metrics_are_complete(self) -> None:
        spec, cases, results = self.load_valid()
        decision = benchmark.evaluate(spec, cases, results, "candidate-pass")
        self.assertEqual(decision.action, "PASS")
        self.assertTrue(decision.comparable)
        self.assertEqual(decision.candidate_metrics["primary_task_success_rate"], 1.0)
        self.assertEqual(decision.candidate_metrics["trial_count"], 15)
        self.assertEqual(len(decision.candidate_metrics["by_family"]), 5)
        self.assertEqual(decision.baseline_metrics["primary_task_success_rate"], 0.6)

    def test_critical_regression_overrides_overall_improvement(self) -> None:
        spec = benchmark.validate_spec(benchmark.load_json(self.spec_path))
        cases = benchmark.validate_cases(benchmark.load_json(self.cases_path), spec)
        results = benchmark.validate_results(
            benchmark.load_json(self.regression_path), spec, cases
        )
        decision = benchmark.evaluate(spec, cases, results, "candidate-regression")
        self.assertEqual(decision.action, "BLOCK")
        self.assertIn("critical task failure", decision.primary_reason)
        self.assertIn("test-safety", decision.primary_reason)
        self.assertEqual(decision.candidate_metrics["primary_task_success_rate"], 0.8)
        self.assertGreater(
            decision.candidate_metrics["primary_task_success_rate"],
            decision.baseline_metrics["primary_task_success_rate"],
        )

    def test_protocol_mismatch_prevents_ranking(self) -> None:
        spec = benchmark.validate_spec(benchmark.load_json(self.protocol_mismatch_path))
        cases = benchmark.validate_cases(benchmark.load_json(self.cases_path), spec)
        results = benchmark.validate_results(
            benchmark.load_json(self.pass_path), spec, cases
        )
        decision = benchmark.evaluate(spec, cases, results, "candidate-pass")
        self.assertEqual(decision.action, "INCOMPARABLE")
        self.assertFalse(decision.comparable)
        self.assertIsNone(decision.baseline_metrics)
        self.assertIsNone(decision.candidate_metrics)
        self.assertTrue(decision.comparison["protocol_mismatches"])

    def test_fingerprint_is_stable_and_content_sensitive(self) -> None:
        spec, cases, results = self.load_valid()
        first = benchmark.fingerprint(spec, cases, results, "candidate-pass")
        second = benchmark.fingerprint(spec, cases, results, "candidate-pass")
        changed = copy.deepcopy(results)
        changed["result_set_version"] = "changed"
        self.assertEqual(first, second)
        self.assertNotEqual(
            first, benchmark.fingerprint(spec, cases, changed, "candidate-pass")
        )

    def test_bootstrap_is_deterministic(self) -> None:
        first = benchmark.bootstrap_interval([0.0, 1.0, 0.0], 500, 23, 0.95)
        second = benchmark.bootstrap_interval([0.0, 1.0, 0.0], 500, 23, 0.95)
        self.assertEqual(first, second)

    def test_nearest_rank_percentile(self) -> None:
        self.assertEqual(benchmark.nearest_rank([1, 2, 3, 4, 5], 0.95), 5.0)

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(benchmark.HERE / "run_benchmark.py"), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_cli_pass_exit_zero(self) -> None:
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["action"], "PASS")

    def test_cli_block_exit_one(self) -> None:
        result = self.run_cli(
            "--results",
            str(self.regression_path),
            "--candidate",
            "candidate-regression",
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["action"], "BLOCK")

    def test_cli_incomparable_exit_one(self) -> None:
        result = self.run_cli("--spec", str(self.protocol_mismatch_path))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["action"], "INCOMPARABLE")

    def test_cli_contract_error_exit_two(self) -> None:
        result = self.run_cli("--cases", str(self.contract_error_path))
        self.assertEqual(result.returncode, 2)
        self.assertIn("split contamination", result.stderr)

    def test_production_code_does_not_use_assert(self) -> None:
        source = (benchmark.HERE / "run_benchmark.py").read_text(encoding="utf-8")
        self.assertNotRegex(source, r"(?m)^\s*assert\b")


if __name__ == "__main__":
    unittest.main()
