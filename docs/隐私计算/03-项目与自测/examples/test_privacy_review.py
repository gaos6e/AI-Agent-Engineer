"""Tests for the deterministic offline privacy-design review example."""

from __future__ import annotations

import ast
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from pathlib import Path

import privacy_review as app


class PrivacyReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vulnerable = app.load_json(app.DEFAULT_SCENARIO)
        cls.hardened = app.load_json(app.HARDENED_SCENARIO)

    def valid(self) -> dict:
        return copy.deepcopy(self.hardened)

    def write_text(self, text: str) -> Path:
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        )
        with handle:
            handle.write(text)
        path = Path(handle.name)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def run_main(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = app.main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def expect_contract_error(self, value: object) -> None:
        with self.assertRaises(app.ContractError):
            app.validate_scenario(value)

    def test_01_load_vulnerable(self) -> None:
        self.assertEqual(self.vulnerable["scenario_id"], "regional-statistics-vulnerable")

    def test_02_load_hardened(self) -> None:
        self.assertEqual(self.hardened["scenario_id"], "regional-statistics-hardened")

    def test_03_validation_returns_deep_copy(self) -> None:
        value = self.valid()
        result = app.validate_scenario(value)
        self.assertEqual(result, value)
        self.assertIsNot(result, value)

    def test_04_duplicate_json_key_rejected(self) -> None:
        path = self.write_text('{"purpose":"a","purpose":"b"}')
        with self.assertRaisesRegex(app.ContractError, r"duplicate JSON key"):
            app.load_json(path)

    def test_05_nan_json_rejected(self) -> None:
        path = self.write_text('{"value":NaN}')
        with self.assertRaisesRegex(app.ContractError, r"non-standard JSON constant"):
            app.load_json(path)

    def test_06_invalid_json_rejected(self) -> None:
        path = self.write_text("{")
        with self.assertRaisesRegex(app.ContractError, r"invalid JSON"):
            app.load_json(path)

    def test_07_unknown_top_field_rejected(self) -> None:
        value = self.valid()
        value["unknown"] = True
        self.expect_contract_error(value)

    def test_08_missing_top_field_rejected(self) -> None:
        value = self.valid()
        del value["subject_scope"]
        self.expect_contract_error(value)

    def test_09_empty_non_goals_rejected(self) -> None:
        value = self.valid()
        value["non_goals"] = []
        self.expect_contract_error(value)

    def test_10_invalid_field_classification_rejected(self) -> None:
        value = self.valid()
        value["data_fields"][0]["classification"] = "anonymous"
        self.expect_contract_error(value)

    def test_11_field_boolean_must_be_bool(self) -> None:
        value = self.valid()
        value["data_fields"][0]["necessary"] = 1
        self.expect_contract_error(value)

    def test_12_contribution_bound_must_be_positive(self) -> None:
        value = self.valid()
        value["data_fields"][0]["contribution_bound"] = 0
        self.expect_contract_error(value)

    def test_13_duplicate_field_name_rejected(self) -> None:
        value = self.valid()
        value["data_fields"][1]["name"] = value["data_fields"][0]["name"]
        self.expect_contract_error(value)

    def test_14_invalid_participant_role_rejected(self) -> None:
        value = self.valid()
        value["participants"][0]["role"] = "model"
        self.expect_contract_error(value)

    def test_15_participant_trust_must_be_bool(self) -> None:
        value = self.valid()
        value["participants"][0]["trusted"] = "yes"
        self.expect_contract_error(value)

    def test_16_duplicate_participant_id_rejected(self) -> None:
        value = self.valid()
        value["participants"][1]["id"] = value["participants"][0]["id"]
        self.expect_contract_error(value)

    def test_17_flow_unknown_endpoint_rejected(self) -> None:
        value = self.valid()
        value["data_flows"][0]["to"] = "missing"
        self.expect_contract_error(value)

    def test_18_flow_unknown_field_rejected(self) -> None:
        value = self.valid()
        value["data_flows"][0]["fields"] = ["missing"]
        self.expect_contract_error(value)

    def test_19_flow_raw_must_be_bool(self) -> None:
        value = self.valid()
        value["data_flows"][0]["raw"] = 0
        self.expect_contract_error(value)

    def test_20_duplicate_flow_id_rejected(self) -> None:
        value = self.valid()
        value["data_flows"][1]["id"] = value["data_flows"][0]["id"]
        self.expect_contract_error(value)

    def test_21_processing_flags_must_be_bool(self) -> None:
        value = self.valid()
        value["processing"]["mpc"] = 1
        self.expect_contract_error(value)

    def test_22_group_size_must_be_positive_integer(self) -> None:
        value = self.valid()
        value["release"]["minimum_group_size"] = 0
        self.expect_contract_error(value)

    def test_23_decimal_values_must_be_strings(self) -> None:
        value = self.valid()
        value["release"]["epsilon_limit"] = 1.0
        self.expect_contract_error(value)

    def test_24_decimal_values_must_be_finite(self) -> None:
        value = self.valid()
        value["release"]["epsilon_limit"] = "NaN"
        self.expect_contract_error(value)

    def test_25_delta_limit_must_be_less_than_one(self) -> None:
        value = self.valid()
        value["release"]["delta_limit"] = "1"
        self.expect_contract_error(value)

    def test_26_mechanism_delta_must_be_less_than_one(self) -> None:
        value = self.valid()
        value["release"]["mechanisms"][0]["delta"] = "1"
        self.expect_contract_error(value)

    def test_27_duplicate_mechanism_id_rejected(self) -> None:
        value = self.valid()
        value["release"]["mechanisms"][1]["id"] = value["release"]["mechanisms"][0]["id"]
        self.expect_contract_error(value)

    def test_28_mechanism_approved_must_be_bool(self) -> None:
        value = self.valid()
        value["release"]["mechanisms"][0]["approved"] = "yes"
        self.expect_contract_error(value)

    def test_29_retention_days_must_be_positive(self) -> None:
        value = self.valid()
        value["retention"]["days"] = 0
        self.expect_contract_error(value)

    def test_30_control_flags_must_be_bool(self) -> None:
        value = self.valid()
        value["controls"]["access_control"] = 1
        self.expect_contract_error(value)

    def test_31_collusion_threshold_must_be_positive(self) -> None:
        value = self.valid()
        value["threat_model"]["collusion_threshold"] = 0
        self.expect_contract_error(value)

    def test_32_invalid_risk_severity_rejected(self) -> None:
        value = self.valid()
        value["risk_policy"]["block_severities"] = ["urgent"]
        self.expect_contract_error(value)

    def test_33_overlapping_risk_severity_rejected(self) -> None:
        value = self.valid()
        value["risk_policy"]["review_severities"] = ["high"]
        self.expect_contract_error(value)

    def test_34_vulnerable_scenario_has_all_findings(self) -> None:
        report = app.run_from_path(app.DEFAULT_SCENARIO)
        expected = {f"PR-{number:03d}" for number in range(1, 13)}
        self.assertEqual({item["id"] for item in report["findings"]}, expected)
        self.assertEqual(report["action"], "BLOCK")

    def test_35_hardened_scenario_passes(self) -> None:
        report = app.run_from_path(app.HARDENED_SCENARIO)
        self.assertEqual(report["action"], "PASS")
        self.assertEqual(report["finding_count"], 0)

    def test_36_medium_only_scenario_requires_review(self) -> None:
        value = self.valid()
        value["retention"]["days"] = 365
        report = app.build_report(app.validate_scenario(value))
        self.assertEqual(report["action"], "REVIEW")
        self.assertEqual([item["id"] for item in report["findings"]], ["PR-008"])

    def test_37_budget_uses_exact_decimal_arithmetic(self) -> None:
        epsilon, delta = app.budget_totals(app.validate_scenario(self.valid()))
        self.assertEqual(epsilon, Decimal("0.8"))
        self.assertEqual(delta, Decimal("0.0000002"))

    def test_38_vulnerable_budget_exceeds_both_limits(self) -> None:
        report = app.run_from_path(app.DEFAULT_SCENARIO)
        self.assertEqual(report["budget_ledger"]["epsilon_used"], "1.5")
        self.assertEqual(report["budget_ledger"]["delta_used"], "0.0000016")

    def test_39_findings_sorted_by_severity_then_id(self) -> None:
        findings = app.run_from_path(app.DEFAULT_SCENARIO)["findings"]
        keys = [(app.SEVERITY_ORDER[item["severity"]], item["id"]) for item in findings]
        self.assertEqual(keys, sorted(keys))

    def test_40_findings_have_evidence_fields(self) -> None:
        findings = app.run_from_path(app.DEFAULT_SCENARIO)["findings"]
        expected = {
            "id", "title", "severity", "privacy_problem", "recommended_controls",
            "verification", "owner",
        }
        self.assertTrue(all(set(item) == expected for item in findings))
        self.assertEqual(len({item["id"] for item in findings}), len(findings))

    def test_41_candidate_controls_expose_boundaries(self) -> None:
        controls = app.run_from_path(app.HARDENED_SCENARIO)["candidate_controls"]
        self.assertEqual(len(controls), 3)
        self.assertTrue(all(item["fit"] and item["boundary"] for item in controls))

    def test_42_fingerprint_is_stable_and_formatted(self) -> None:
        first = app.run_from_path(app.HARDENED_SCENARIO)["evidence_fingerprint"]
        second = app.run_from_path(app.HARDENED_SCENARIO)["evidence_fingerprint"]
        self.assertEqual(first, second)
        self.assertRegex(first, r"^sha256:[0-9a-f]{64}$")

    def test_43_fingerprint_changes_with_input(self) -> None:
        value = self.valid()
        first = app.build_report(app.validate_scenario(value))["evidence_fingerprint"]
        value["scenario_id"] = "changed"
        second = app.build_report(app.validate_scenario(value))["evidence_fingerprint"]
        self.assertNotEqual(first, second)

    def test_44_limitations_prevent_overclaiming(self) -> None:
        text = " ".join(app.run_from_path(app.HARDENED_SCENARIO)["limitations"])
        self.assertIn("No personal data", text)
        self.assertIn("basic illustrative", text)
        self.assertIn("not legal advice", text)

    def test_45_cli_vulnerable_returns_one(self) -> None:
        code, stdout, stderr = self.run_main("--scenario", str(app.DEFAULT_SCENARIO))
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout)["action"], "BLOCK")
        self.assertEqual(stderr, "")

    def test_46_cli_hardened_returns_zero(self) -> None:
        code, stdout, stderr = self.run_main("--scenario", str(app.HARDENED_SCENARIO))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["action"], "PASS")
        self.assertEqual(stderr, "")

    def test_47_cli_contract_error_returns_two(self) -> None:
        code, stdout, stderr = self.run_main("--scenario", str(app.CONTRACT_ERROR_SCENARIO))
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("contract error", stderr)

    def test_48_cli_self_test_returns_zero(self) -> None:
        code, stdout, stderr = self.run_main("--self-test")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout), {"self_test": "passed"})
        self.assertEqual(stderr, "")

    def test_49_production_code_has_no_assert_statement(self) -> None:
        tree = ast.parse(Path(app.__file__).read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))

    def test_50_report_does_not_echo_record_level_data(self) -> None:
        report = app.run_from_path(app.DEFAULT_SCENARIO)
        self.assertNotIn("person_name", json.dumps(report["findings"]))


if __name__ == "__main__":
    unittest.main()
