"""Tests for the deterministic offline Agent threat review example."""

from __future__ import annotations

import ast
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import threat_review as app


class ThreatReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vulnerable = app.load_json(app.DEFAULT_SCENARIO)
        cls.hardened = app.load_json(app.HARDENED_SCENARIO)

    def valid(self) -> dict:
        return copy.deepcopy(self.hardened)

    def write_json(self, value: object) -> Path:
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        )
        with handle:
            json.dump(value, handle, ensure_ascii=False)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return Path(handle.name)

    def run_main(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = app.main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def expect_contract_error(self, value: object) -> None:
        with self.assertRaises(app.ContractError):
            app.validate_scenario(value)

    def test_01_load_vulnerable_json(self) -> None:
        self.assertEqual(self.vulnerable["scenario_id"], "mail-draft-assistant-vulnerable")

    def test_02_load_hardened_json(self) -> None:
        self.assertEqual(self.hardened["scenario_id"], "mail-draft-assistant-hardened")

    def test_03_valid_contract_returns_copy(self) -> None:
        source = self.valid()
        result = app.validate_scenario(source)
        self.assertEqual(result, source)
        self.assertIsNot(result, source)

    def test_04_duplicate_json_key_rejected(self) -> None:
        path = self.write_json({"ok": 1})
        path.write_text('{"scenario_id":"a","scenario_id":"b"}', encoding="utf-8")
        with self.assertRaisesRegex(app.ContractError, r"duplicate JSON key"):
            app.load_json(path)

    def test_05_nonstandard_json_constant_rejected(self) -> None:
        path = self.write_json({"ok": 1})
        path.write_text('{"value":NaN}', encoding="utf-8")
        with self.assertRaisesRegex(app.ContractError, r"non-standard JSON constant"):
            app.load_json(path)

    def test_06_invalid_json_rejected(self) -> None:
        path = self.write_json({"ok": 1})
        path.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(app.ContractError, r"invalid JSON"):
            app.load_json(path)

    def test_07_unknown_top_field_rejected(self) -> None:
        value = self.valid()
        value["surprise"] = True
        self.expect_contract_error(value)

    def test_08_missing_top_field_rejected(self) -> None:
        value = self.valid()
        del value["purpose"]
        self.expect_contract_error(value)

    def test_09_empty_purpose_rejected(self) -> None:
        value = self.valid()
        value["purpose"] = " "
        self.expect_contract_error(value)

    def test_10_empty_non_goals_rejected(self) -> None:
        value = self.valid()
        value["non_goals"] = []
        self.expect_contract_error(value)

    def test_11_invalid_asset_classification_rejected(self) -> None:
        value = self.valid()
        value["assets"][0]["classification"] = "secret-ish"
        self.expect_contract_error(value)

    def test_12_duplicate_asset_id_rejected(self) -> None:
        value = self.valid()
        value["assets"][1]["id"] = value["assets"][0]["id"]
        self.expect_contract_error(value)

    def test_13_boundary_unknown_asset_rejected(self) -> None:
        value = self.valid()
        value["trust_boundaries"][0]["data_assets"] = ["missing"]
        self.expect_contract_error(value)

    def test_14_duplicate_boundary_id_rejected(self) -> None:
        value = self.valid()
        value["trust_boundaries"][1]["id"] = value["trust_boundaries"][0]["id"]
        self.expect_contract_error(value)

    def test_15_invalid_source_trust_rejected(self) -> None:
        value = self.valid()
        value["untrusted_sources"][0]["trust_level"] = "maybe"
        self.expect_contract_error(value)

    def test_16_duplicate_source_id_rejected(self) -> None:
        value = self.valid()
        value["untrusted_sources"][1]["id"] = value["untrusted_sources"][0]["id"]
        self.expect_contract_error(value)

    def test_17_identity_boolean_must_be_bool(self) -> None:
        value = self.valid()
        value["identities"][0]["shared"] = 0
        self.expect_contract_error(value)

    def test_18_identity_ttl_must_be_positive_integer(self) -> None:
        value = self.valid()
        value["identities"][0]["ttl_minutes"] = 0
        self.expect_contract_error(value)

    def test_19_duplicate_identity_id_rejected(self) -> None:
        value = self.valid()
        value["identities"].append(copy.deepcopy(value["identities"][0]))
        self.expect_contract_error(value)

    def test_20_duplicate_scope_rejected(self) -> None:
        value = self.valid()
        value["identities"][0]["scopes"] = ["mail.read", "mail.read"]
        self.expect_contract_error(value)

    def test_21_invalid_tool_mode_rejected(self) -> None:
        value = self.valid()
        value["tools"][0]["mode"] = "think"
        self.expect_contract_error(value)

    def test_22_invalid_tool_destination_rejected(self) -> None:
        value = self.valid()
        value["tools"][0]["destination"] = "internet-ish"
        self.expect_contract_error(value)

    def test_23_tool_boolean_must_be_bool(self) -> None:
        value = self.valid()
        value["tools"][0]["side_effect"] = 1
        self.expect_contract_error(value)

    def test_24_unavailable_tool_scope_rejected(self) -> None:
        value = self.valid()
        value["tools"][0]["required_scopes"] = ["mail.admin"]
        self.expect_contract_error(value)

    def test_25_duplicate_tool_name_rejected(self) -> None:
        value = self.valid()
        value["tools"].append(copy.deepcopy(value["tools"][0]))
        self.expect_contract_error(value)

    def test_26_unknown_allowlisted_tool_rejected(self) -> None:
        value = self.valid()
        value["controls"]["tool_allowlist"] = ["missing"]
        self.expect_contract_error(value)

    def test_27_invalid_destination_allowlist_rejected(self) -> None:
        value = self.valid()
        value["controls"]["destination_allowlist"] = ["partner"]
        self.expect_contract_error(value)

    def test_28_unknown_approval_tool_rejected(self) -> None:
        value = self.valid()
        value["controls"]["approval"]["required_for_tools"] = ["missing"]
        self.expect_contract_error(value)

    def test_29_approval_binding_must_be_bool(self) -> None:
        value = self.valid()
        value["controls"]["approval"]["binds_parameters"] = "yes"
        self.expect_contract_error(value)

    def test_30_approval_expiry_must_be_positive(self) -> None:
        value = self.valid()
        value["controls"]["approval"]["expires_minutes"] = 0
        self.expect_contract_error(value)

    def test_31_sandbox_flag_must_be_bool(self) -> None:
        value = self.valid()
        value["controls"]["sandbox"]["enabled"] = "true"
        self.expect_contract_error(value)

    def test_32_dependency_boolean_must_be_bool(self) -> None:
        value = self.valid()
        value["dependencies"][0]["pinned"] = 1
        self.expect_contract_error(value)

    def test_33_duplicate_dependency_name_rejected(self) -> None:
        value = self.valid()
        value["dependencies"].append(copy.deepcopy(value["dependencies"][0]))
        self.expect_contract_error(value)

    def test_34_invalid_risk_severity_rejected(self) -> None:
        value = self.valid()
        value["risk_policy"]["block_severities"] = ["urgent"]
        self.expect_contract_error(value)

    def test_35_overlapping_risk_severity_rejected(self) -> None:
        value = self.valid()
        value["risk_policy"]["review_severities"] = ["high"]
        self.expect_contract_error(value)

    def test_36_vulnerable_scenario_has_all_teaching_findings(self) -> None:
        report = app.run_from_path(app.DEFAULT_SCENARIO)
        expected = {f"AS-{number:03d}" for number in range(1, 12)}
        self.assertEqual({item["id"] for item in report["findings"]}, expected)
        self.assertEqual(report["action"], "BLOCK")

    def test_37_findings_are_severity_then_id_sorted(self) -> None:
        report = app.run_from_path(app.DEFAULT_SCENARIO)
        keys = [
            (app.SEVERITY_ORDER[item["severity"]], item["id"])
            for item in report["findings"]
        ]
        self.assertEqual(keys, sorted(keys))

    def test_38_critical_findings_are_first(self) -> None:
        report = app.run_from_path(app.DEFAULT_SCENARIO)
        self.assertEqual([item["id"] for item in report["findings"][:2]], ["AS-001", "AS-006"])

    def test_39_hardened_scenario_passes_without_findings(self) -> None:
        report = app.run_from_path(app.HARDENED_SCENARIO)
        self.assertEqual(report["action"], "PASS")
        self.assertEqual(report["finding_count"], 0)

    def test_40_medium_only_scenario_requires_review(self) -> None:
        value = self.valid()
        value["dependencies"][0]["pinned"] = False
        report = app.build_report(app.validate_scenario(value))
        self.assertEqual(report["action"], "REVIEW")
        self.assertEqual([item["id"] for item in report["findings"]], ["AS-007"])

    def test_41_each_finding_has_actionable_evidence_fields(self) -> None:
        findings = app.run_from_path(app.DEFAULT_SCENARIO)["findings"]
        required = {
            "id", "title", "severity", "asset", "attack_path", "impact",
            "recommended_controls", "owner", "verification",
        }
        self.assertTrue(findings)
        self.assertTrue(all(set(item) == required for item in findings))
        self.assertEqual(len({item["id"] for item in findings}), len(findings))

    def test_42_fingerprint_is_stable(self) -> None:
        first = app.run_from_path(app.HARDENED_SCENARIO)["evidence_fingerprint"]
        second = app.run_from_path(app.HARDENED_SCENARIO)["evidence_fingerprint"]
        self.assertEqual(first, second)
        self.assertRegex(first, r"^sha256:[0-9a-f]{64}$")

    def test_43_fingerprint_changes_with_scenario(self) -> None:
        value = self.valid()
        original = app.build_report(app.validate_scenario(value))["evidence_fingerprint"]
        value["scenario_id"] = "changed"
        changed = app.build_report(app.validate_scenario(value))["evidence_fingerprint"]
        self.assertNotEqual(original, changed)

    def test_44_limitations_prevent_overclaiming(self) -> None:
        limitations = " ".join(app.run_from_path(app.HARDENED_SCENARIO)["limitations"])
        self.assertIn("not a penetration test", limitations)
        self.assertIn("No model", limitations)
        self.assertIn("not a legal", limitations)

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

    def test_50_declared_non_goals_survive_report(self) -> None:
        validated = app.validate_scenario(self.valid())
        self.assertIn("send messages", validated["non_goals"])


if __name__ == "__main__":
    unittest.main()
