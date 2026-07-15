"""Tests for the offline synthetic dataset teaching project."""

from __future__ import annotations

import ast
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import build_synthetic_evalset as app


class SyntheticDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = app.validate_spec(app.load_json(app.DEFAULT_SPEC))

    def valid_spec(self) -> dict:
        return copy.deepcopy(self.spec)

    def run_main(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = app.main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def write_temp(self, text: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "fixture.json"
        path.write_text(text, encoding="utf-8")
        return path

    def test_default_spec_loads(self) -> None:
        self.assertEqual(self.spec["dataset_version"], "2.0.0")

    def test_duplicate_json_key_is_rejected(self) -> None:
        path = self.write_temp('{"a": 1, "a": 2}')
        with self.assertRaisesRegex(app.ContractError, "duplicate JSON key"):
            app.load_json(path)

    def test_nonstandard_nan_is_rejected(self) -> None:
        path = self.write_temp('{"a": NaN}')
        with self.assertRaisesRegex(app.ContractError, "non-standard JSON constant"):
            app.load_json(path)

    def test_unknown_top_level_field_is_rejected(self) -> None:
        spec = self.valid_spec()
        spec["unknown"] = True
        with self.assertRaisesRegex(app.ContractError, r"unknown=\['unknown'\]"):
            app.validate_spec(spec)

    def test_missing_top_level_field_is_rejected(self) -> None:
        spec = self.valid_spec()
        del spec["purpose"]
        with self.assertRaisesRegex(app.ContractError, r"missing=\['purpose'\]"):
            app.validate_spec(spec)

    def test_generator_unknown_field_is_rejected(self) -> None:
        spec = self.valid_spec()
        spec["generator"]["model"] = "not-allowed"
        with self.assertRaisesRegex(app.ContractError, "spec.generator fields mismatch"):
            app.validate_spec(spec)

    def test_contains_real_data_must_be_boolean(self) -> None:
        spec = self.valid_spec()
        spec["generator"]["contains_real_data"] = "false"
        with self.assertRaisesRegex(app.ContractError, "must be a boolean"):
            app.validate_spec(spec)

    def test_split_seed_rejects_boolean(self) -> None:
        spec = self.valid_spec()
        spec["split"]["seed"] = True
        with self.assertRaisesRegex(app.ContractError, "must be an integer"):
            app.validate_spec(spec)

    def test_development_count_must_leave_test_family(self) -> None:
        spec = self.valid_spec()
        spec["split"]["development_family_count"] = 6
        with self.assertRaisesRegex(app.ContractError, "leave at least one family"):
            app.validate_spec(spec)

    def test_quality_integer_rejects_boolean(self) -> None:
        spec = self.valid_spec()
        spec["quality_gates"]["min_records_per_cell"] = True
        with self.assertRaisesRegex(app.ContractError, "must be an integer"):
            app.validate_spec(spec)

    def test_nonfinite_programmatic_gate_is_rejected(self) -> None:
        spec = self.valid_spec()
        spec["quality_gates"]["max_duplicate_fraction"] = float("inf")
        with self.assertRaisesRegex(app.ContractError, "finite number"):
            app.validate_spec(spec)

    def test_duplicate_fraction_range_is_validated(self) -> None:
        spec = self.valid_spec()
        spec["quality_gates"]["max_duplicate_fraction"] = 1.1
        with self.assertRaisesRegex(app.ContractError, r"must be in \[0, 1\]"):
            app.validate_spec(spec)

    def test_non_goals_must_not_be_empty(self) -> None:
        spec = self.valid_spec()
        spec["non_goals"] = []
        with self.assertRaisesRegex(app.ContractError, "non-empty list"):
            app.validate_spec(spec)

    def test_condition_templates_must_not_be_empty(self) -> None:
        spec = self.valid_spec()
        spec["conditions"]["en"]["status"]["templates"] = []
        with self.assertRaisesRegex(app.ContractError, "templates must be non-empty"):
            app.validate_spec(spec)

    def test_condition_unknown_field_is_rejected(self) -> None:
        spec = self.valid_spec()
        spec["conditions"]["en"]["status"]["weight"] = 1
        with self.assertRaisesRegex(app.ContractError, "fields mismatch"):
            app.validate_spec(spec)

    def test_normalize_is_case_and_whitespace_stable(self) -> None:
        self.assertEqual(app.normalize("  HELLO   World "), "hello world")

    def test_generation_has_expected_raw_count(self) -> None:
        self.assertEqual(len(app.generate_candidates(self.spec)), 14)

    def test_filter_rejects_one_contract_error_and_one_duplicate(self) -> None:
        accepted, rejected = app.filter_and_deduplicate(
            app.generate_candidates(self.spec), self.spec
        )
        self.assertEqual(len(accepted), 12)
        self.assertEqual(
            [item["stage"] for item in rejected],
            ["deduplication", "contract"],
        )

    def test_candidate_unknown_field_is_rejected(self) -> None:
        candidate = app.generate_candidates(self.spec)[0]
        candidate["unknown"] = True
        self.assertIn("unknown:unknown", app.candidate_errors(candidate, self.spec))

    def test_candidate_expected_action_mismatch_is_rejected(self) -> None:
        candidate = app.generate_candidates(self.spec)[0]
        candidate["expected_action"] = "wrong"
        self.assertIn("expected-action-mismatch", app.candidate_errors(candidate, self.spec))

    def test_candidate_provenance_mismatch_is_rejected(self) -> None:
        candidate = app.generate_candidates(self.spec)[0]
        candidate["provenance"]["contains_real_data"] = True
        self.assertIn("provenance-source-mismatch", app.candidate_errors(candidate, self.spec))

    def test_possible_email_is_rejected(self) -> None:
        candidate = app.generate_candidates(self.spec)[0]
        candidate["input"] = "Email real.person@example.com"
        self.assertIn("possible-personal-data-pattern", app.candidate_errors(candidate, self.spec))

    def test_duplicate_candidate_id_is_rejected(self) -> None:
        first = app.generate_candidates(self.spec)[0]
        second = copy.deepcopy(first)
        second["input"] = "a different fictional prompt"
        _, rejected = app.filter_and_deduplicate([first, second], self.spec)
        self.assertIn("duplicate-candidate-id", rejected[0]["reasons"])

    def test_family_split_is_disjoint(self) -> None:
        report = app.build_dataset(self.spec)
        family_splits: dict[str, set[str]] = {}
        for record in report["records"]:
            family_splits.setdefault(record["family_id"], set()).add(record["split"])
        self.assertTrue(all(len(splits) == 1 for splits in family_splits.values()))

    def test_both_splits_exist(self) -> None:
        report = app.build_dataset(self.spec)
        self.assertEqual(set(report["splits"]), {"development", "test"})

    def test_all_condition_cells_have_two_records(self) -> None:
        report = app.build_dataset(self.spec)
        self.assertEqual(len(report["coverage"]), 6)
        self.assertEqual(set(report["coverage"].values()), {2})

    def test_records_have_stable_ids_and_explicit_provenance(self) -> None:
        report = app.build_dataset(self.spec)
        self.assertTrue(all(item["id"].startswith("syn-") for item in report["records"]))
        self.assertTrue(
            all(set(item["provenance"]) == app.PROVENANCE_FIELDS for item in report["records"])
        )

    def test_default_report_passes(self) -> None:
        report = app.build_dataset(self.spec)
        self.assertEqual(report["action"], "PASS")
        self.assertEqual(
            report["counts"],
            {
                "raw": 14,
                "contract_rejected": 1,
                "duplicate_rejected": 1,
                "released": 12,
            },
        )

    def test_quality_regression_blocks(self) -> None:
        report = app.run_from_path(app.QUALITY_REGRESSION_SPEC)
        self.assertEqual(report["action"], "BLOCK")
        self.assertIn("condition coverage below gate", report["reasons"][0])

    def test_duplicate_fraction_can_trigger_review(self) -> None:
        spec = self.valid_spec()
        spec["quality_gates"]["max_duplicate_fraction"] = 0.01
        report = app.build_dataset(spec)
        self.assertEqual(report["action"], "REVIEW")
        self.assertIn("duplicate fraction", report["reasons"][0])

    def test_real_source_declaration_blocks_automatic_release(self) -> None:
        spec = self.valid_spec()
        spec["generator"]["contains_real_data"] = True
        report = app.build_dataset(spec)
        self.assertEqual(report["action"], "BLOCK")
        self.assertTrue(any("authorization and privacy review" in reason for reason in report["reasons"]))

    def test_fingerprint_is_deterministic(self) -> None:
        first = app.build_dataset(self.spec)
        second = app.build_dataset(self.spec)
        self.assertEqual(first["manifest"]["fingerprint"], second["manifest"]["fingerprint"])

    def test_fingerprint_changes_when_split_seed_changes(self) -> None:
        first = app.build_dataset(self.spec)
        spec = self.valid_spec()
        spec["split"]["seed"] = 99
        second = app.build_dataset(spec)
        self.assertNotEqual(first["manifest"]["fingerprint"], second["manifest"]["fingerprint"])

    def test_limitations_name_utility_and_privacy_boundaries(self) -> None:
        limitations = " ".join(app.build_dataset(self.spec)["limitations"])
        self.assertIn("No differential privacy", limitations)
        self.assertIn("independent real holdout", limitations)

    def test_self_test_uses_explicit_checks(self) -> None:
        app.self_test()

    def test_cli_pass_exit_zero(self) -> None:
        code, output, error = self.run_main("--spec", str(app.DEFAULT_SPEC))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["action"], "PASS")
        self.assertEqual(error, "")

    def test_cli_quality_block_exit_one(self) -> None:
        code, output, _ = self.run_main("--spec", str(app.QUALITY_REGRESSION_SPEC))
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output)["action"], "BLOCK")

    def test_cli_contract_error_exit_two(self) -> None:
        code, output, error = self.run_main("--spec", str(app.CONTRACT_ERROR_SPEC))
        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertIn("contract error", error)

    def test_cli_self_test_exit_zero(self) -> None:
        code, output, error = self.run_main("--self-test")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output), {"self_test": "passed"})
        self.assertEqual(error, "")

    def test_production_code_does_not_use_assert(self) -> None:
        tree = ast.parse(Path(app.__file__).read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))


if __name__ == "__main__":
    unittest.main()
