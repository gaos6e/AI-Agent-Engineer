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

    def test_22_invalid_tool_destination_class_rejected(self) -> None:
        value = self.valid()
        value["tools"][0]["destination_class"] = "internet-ish"
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

    def test_27_unknown_endpoint_allowlist_entry_rejected(self) -> None:
        value = self.valid()
        value["controls"]["endpoint_allowlist"] = ["partner-api"]
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

    def test_32_dependency_provenance_must_be_bool(self) -> None:
        value = self.valid()
        value["dependencies"][0]["provenance_verified"] = 1
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
        value["dependencies"][0]["artifact_digest"] = None
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
        report = app.build_report(app.validate_scenario(self.valid()))
        self.assertEqual(
            report["non_goals"],
            ["send messages", "modify mailbox state", "persist email content to memory"],
        )

    def test_51_unsupported_schema_version_rejected(self) -> None:
        value = self.valid()
        value["schema_version"] = "999"
        self.expect_contract_error(value)

    def test_52_write_mode_cannot_deny_side_effect(self) -> None:
        value = self.valid()
        value["tools"][0]["mode"] = "write"
        value["tools"][0]["side_effect"] = False
        self.expect_contract_error(value)

    def test_53_read_mode_cannot_claim_side_effect(self) -> None:
        value = self.valid()
        value["tools"][0]["side_effect"] = True
        self.expect_contract_error(value)

    def test_54_tool_identity_must_exist(self) -> None:
        value = self.valid()
        value["tools"][0]["identity_id"] = "missing"
        self.expect_contract_error(value)

    def test_55_tool_scope_is_bound_to_its_identity(self) -> None:
        value = self.valid()
        value["identities"].append(
            {
                "id": "unrelated-admin",
                "shared": False,
                "ttl_minutes": 5,
                "scopes": ["mail.admin"],
            }
        )
        value["tools"][0]["required_scopes"] = ["mail.admin"]
        self.expect_contract_error(value)

    def test_56_unknown_egress_asset_rejected(self) -> None:
        value = self.valid()
        value["tools"][0]["egress_assets"] = ["missing"]
        self.expect_contract_error(value)

    def test_57_required_tool_must_be_allowlisted(self) -> None:
        value = self.valid()
        value["controls"]["tool_allowlist"] = []
        self.expect_contract_error(value)

    def test_58_unknown_resource_allowlist_entry_rejected(self) -> None:
        value = self.valid()
        value["controls"]["resource_allowlist"] = ["mailbox:other"]
        self.expect_contract_error(value)

    def test_59_approval_cannot_reference_disabled_tool(self) -> None:
        value = self.valid()
        optional = copy.deepcopy(value["tools"][0])
        optional["name"] = "optional_mail_read"
        optional["required_for_purpose"] = False
        value["tools"].append(optional)
        value["controls"]["approval"]["required_for_tools"] = [
            "optional_mail_read"
        ]
        self.expect_contract_error(value)

    def test_60_disabled_memory_cannot_declare_write_source(self) -> None:
        value = self.valid()
        value["memory"]["write_sources"] = ["email_body"]
        self.expect_contract_error(value)

    def test_61_disabled_memory_marks_validation_not_applicable(self) -> None:
        value = self.valid()
        value["controls"]["memory_write_validation"] = True
        self.expect_contract_error(value)

    def test_62_enabled_memory_requires_declared_flow(self) -> None:
        value = self.valid()
        value["memory"]["enabled"] = True
        self.expect_contract_error(value)

    def test_63_memory_source_must_exist(self) -> None:
        value = self.valid()
        value["memory"] = {
            "enabled": True,
            "write_sources": ["missing"],
            "write_assets": [],
        }
        self.expect_contract_error(value)

    def test_64_memory_asset_must_exist(self) -> None:
        value = self.valid()
        value["memory"] = {
            "enabled": True,
            "write_sources": [],
            "write_assets": ["missing"],
        }
        self.expect_contract_error(value)

    def test_65_conditional_sources_remain_non_authoritative(self) -> None:
        value = copy.deepcopy(self.vulnerable)
        for source in value["untrusted_sources"]:
            source["trust_level"] = "conditional"
        report = app.build_report(app.validate_scenario(value))
        ids = {item["id"] for item in report["findings"]}
        self.assertIn("AS-001", ids)
        self.assertIn("AS-010", ids)

    def test_66_external_read_with_sensitive_egress_is_checked(self) -> None:
        value = self.valid()
        value["tools"][0]["destination_class"] = "external"
        value["tools"][0]["egress_assets"] = ["private_mail"]
        report = app.build_report(app.validate_scenario(value))
        self.assertEqual([item["id"] for item in report["findings"]], ["AS-006"])
        self.assertEqual(report["action"], "BLOCK")

    def test_67_weak_internal_write_approval_is_checked(self) -> None:
        value = self.valid()
        value["tools"][0]["mode"] = "write"
        value["tools"][0]["side_effect"] = True
        value["controls"]["approval"] = {
            "required_for_tools": ["read_mail"],
            "binds_parameters": False,
            "expires_minutes": 60,
        }
        report = app.build_report(app.validate_scenario(value))
        self.assertEqual([item["id"] for item in report["findings"]], ["AS-004"])

    def test_68_missing_endpoint_policy_is_a_finding(self) -> None:
        value = self.valid()
        value["controls"]["endpoint_allowlist"] = []
        report = app.build_report(app.validate_scenario(value))
        self.assertEqual([item["id"] for item in report["findings"]], ["AS-005"])

    def test_69_missing_resource_policy_is_a_finding(self) -> None:
        value = self.valid()
        value["controls"]["resource_allowlist"] = []
        report = app.build_report(app.validate_scenario(value))
        self.assertEqual([item["id"] for item in report["findings"]], ["AS-005"])

    def test_70_mutable_version_is_a_supply_chain_finding(self) -> None:
        value = self.valid()
        value["dependencies"][0]["version"] = "latest"
        report = app.build_report(app.validate_scenario(value))
        self.assertEqual([item["id"] for item in report["findings"]], ["AS-007"])
        self.assertEqual(report["action"], "REVIEW")

    def test_71_invalid_artifact_digest_rejected(self) -> None:
        value = self.valid()
        value["dependencies"][0]["artifact_digest"] = "sha256:not-a-digest"
        self.expect_contract_error(value)

    def test_72_risk_policy_must_cover_every_severity(self) -> None:
        value = self.valid()
        value["risk_policy"]["accept_severities"] = []
        self.expect_contract_error(value)

    def test_73_risk_policy_must_block_critical(self) -> None:
        value = self.valid()
        value["risk_policy"] = {
            "block_severities": ["high"],
            "review_severities": ["critical", "medium"],
            "accept_severities": ["low"],
        }
        self.expect_contract_error(value)

    def test_74_risk_policy_cannot_accept_high(self) -> None:
        value = self.valid()
        value["risk_policy"] = {
            "block_severities": ["critical"],
            "review_severities": ["medium"],
            "accept_severities": ["high", "low"],
        }
        self.expect_contract_error(value)

    def test_75_original_fail_open_policy_is_rejected(self) -> None:
        value = copy.deepcopy(self.vulnerable)
        value["risk_policy"] = {
            "block_severities": ["low"],
            "review_severities": [],
            "accept_severities": ["critical", "high", "medium"],
        }
        self.expect_contract_error(value)

    def test_76_decision_fails_closed_on_unhandled_severity(self) -> None:
        action, reasons = app.decision(
            self.valid(), [{"id": "AS-X", "severity": "unexpected"}]
        )
        self.assertEqual(action, "BLOCK")
        self.assertIn("unhandled", reasons[0])

    def test_77_explicit_low_acceptance_is_visible(self) -> None:
        action, reasons = app.decision(
            self.valid(), [{"id": "AS-LOW", "severity": "low"}]
        )
        self.assertEqual(action, "PASS")
        self.assertIn("explicitly accepted", reasons[0])

    def test_78_no_memory_does_not_require_memory_validation(self) -> None:
        value = self.valid()
        self.assertFalse(value["memory"]["enabled"])
        self.assertFalse(value["controls"]["memory_write_validation"])
        self.assertEqual(app.build_report(app.validate_scenario(value))["action"], "PASS")

    def test_79_wildcard_resource_is_not_a_concrete_policy_target(self) -> None:
        value = self.valid()
        value["tools"][0]["resources"] = ["mailbox:*"]
        value["controls"]["resource_allowlist"] = ["mailbox:*"]
        self.expect_contract_error(value)

    def test_80_report_identifies_contract_version(self) -> None:
        report = app.build_report(app.validate_scenario(self.valid()))
        self.assertEqual(report["schema_version"], app.SUPPORTED_SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
