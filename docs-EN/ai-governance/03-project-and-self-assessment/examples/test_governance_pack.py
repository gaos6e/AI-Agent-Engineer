"""Tests for the deterministic offline AI-governance pack example."""

from __future__ import annotations

import ast
import copy
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import governance_pack as app


class GovernancePackTests(unittest.TestCase):
    def scenario(self) -> dict:
        return copy.deepcopy(app.SCENARIO)

    def pack(self) -> dict:
        return app.build_pack(self.scenario())

    def risk_facts(self, **updates: object) -> dict:
        facts = copy.deepcopy(app.SCENARIO["risk_facts"])
        facts.update(updates)
        return facts

    def run_main(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = app.main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def expect_scenario_error(self, value: object) -> None:
        with self.assertRaises(app.GovernanceError):
            app.validate_scenario(value)

    def test_01_valid_scenario_returns_deep_copy(self) -> None:
        value = self.scenario()
        result = app.validate_scenario(value)
        self.assertEqual(result, value)
        self.assertIsNot(result, value)

    def test_02_scenario_must_be_object(self) -> None:
        self.expect_scenario_error([])

    def test_03_unknown_top_field_rejected(self) -> None:
        value = self.scenario()
        value["unknown"] = True
        self.expect_scenario_error(value)

    def test_04_missing_top_field_rejected(self) -> None:
        value = self.scenario()
        del value["purpose"]
        self.expect_scenario_error(value)

    def test_05_empty_system_id_rejected(self) -> None:
        value = self.scenario()
        value["system_id"] = " "
        self.expect_scenario_error(value)

    def test_06_prohibited_uses_must_be_nonempty(self) -> None:
        value = self.scenario()
        value["prohibited_uses"] = []
        self.expect_scenario_error(value)

    def test_07_duplicate_prohibited_use_rejected(self) -> None:
        value = self.scenario()
        value["prohibited_uses"].append(value["prohibited_uses"][0])
        self.expect_scenario_error(value)

    def test_08_users_must_be_text_list(self) -> None:
        value = self.scenario()
        value["users"] = [1]
        self.expect_scenario_error(value)

    def test_09_data_must_be_nonempty(self) -> None:
        value = self.scenario()
        value["data"] = []
        self.expect_scenario_error(value)

    def test_10_data_unknown_field_rejected(self) -> None:
        value = self.scenario()
        value["data"][0]["extra"] = "x"
        self.expect_scenario_error(value)

    def test_11_personal_data_must_be_bool(self) -> None:
        value = self.scenario()
        value["data"][0]["personal_data"] = 0
        self.expect_scenario_error(value)

    def test_12_duplicate_data_id_rejected(self) -> None:
        value = self.scenario()
        value["data"].append(copy.deepcopy(value["data"][0]))
        self.expect_scenario_error(value)

    def test_13_components_must_be_nonempty(self) -> None:
        value = self.scenario()
        value["components"] = []
        self.expect_scenario_error(value)

    def test_14_invalid_component_type_rejected(self) -> None:
        value = self.scenario()
        value["components"][0]["type"] = "agent"
        self.expect_scenario_error(value)

    def test_15_component_version_must_be_nonempty(self) -> None:
        value = self.scenario()
        value["components"][0]["version"] = ""
        self.expect_scenario_error(value)

    def test_16_duplicate_component_id_rejected(self) -> None:
        value = self.scenario()
        value["components"][1]["id"] = value["components"][0]["id"]
        self.expect_scenario_error(value)

    def test_17_vendor_fields_are_exact(self) -> None:
        value = self.scenario()
        del value["vendor"]["exit_plan"]
        self.expect_scenario_error(value)

    def test_18_vendor_training_flag_must_be_bool(self) -> None:
        value = self.scenario()
        value["vendor"]["training_on_inputs"] = "false"
        self.expect_scenario_error(value)

    def test_19_risk_facts_are_exact(self) -> None:
        value = self.scenario()
        value["risk_facts"]["legal_class"] = "high"
        self.expect_scenario_error(value)

    def test_20_severity_must_be_integer_one_to_five(self) -> None:
        for invalid in (0, 6, True, "4"):
            value = self.scenario()
            value["risk_facts"]["severity"] = invalid
            with self.subTest(invalid=invalid):
                self.expect_scenario_error(value)

    def test_21_likelihood_must_be_integer_one_to_five(self) -> None:
        value = self.scenario()
        value["risk_facts"]["likelihood"] = 0
        self.expect_scenario_error(value)

    def test_22_risk_flags_must_be_bool(self) -> None:
        value = self.scenario()
        value["risk_facts"]["autonomous_action"] = 1
        self.expect_scenario_error(value)

    def test_23_uncertainty_must_be_recorded(self) -> None:
        value = self.scenario()
        value["risk_facts"]["uncertainty"] = ""
        self.expect_scenario_error(value)

    def test_24_low_risk_matrix_case(self) -> None:
        facts = self.risk_facts(
            severity=2,
            likelihood=2,
            consequential_context=False,
            uncertainty="bounded",
        )
        result = app.tier_risk(facts)
        self.assertEqual(result["internal_tier"], "low")
        self.assertEqual(result["score"], 4)

    def test_25_medium_risk_matrix_case(self) -> None:
        facts = self.risk_facts(
            severity=3,
            likelihood=2,
            consequential_context=False,
            uncertainty="bounded",
        )
        self.assertEqual(app.tier_risk(facts)["internal_tier"], "medium")

    def test_26_high_risk_matrix_case(self) -> None:
        facts = self.risk_facts(severity=5, likelihood=2, uncertainty="bounded")
        self.assertEqual(app.tier_risk(facts)["internal_tier"], "high")

    def test_27_consequential_context_forces_high(self) -> None:
        facts = self.risk_facts(severity=1, likelihood=1, consequential_context=True, uncertainty="bounded")
        result = app.tier_risk(facts)
        self.assertEqual(result["internal_tier"], "high")
        self.assertTrue(any("consequential" in reason for reason in result["reasons"]))

    def test_28_autonomous_action_forces_high(self) -> None:
        facts = self.risk_facts(
            severity=1,
            likelihood=1,
            consequential_context=False,
            autonomous_action=True,
            uncertainty="bounded",
        )
        self.assertEqual(app.tier_risk(facts)["internal_tier"], "high")

    def test_29_risk_boundary_disclaims_legal_classification(self) -> None:
        facts = self.risk_facts(severity=1, likelihood=1, consequential_context=False)
        self.assertIn("not a statutory", app.tier_risk(facts)["boundary"])

    def test_30_pack_contains_exact_sections(self) -> None:
        pack = self.pack()
        app.validate_pack(pack)
        self.assertEqual(len(pack), 13)

    def test_31_pack_is_high_internal_review(self) -> None:
        self.assertEqual(self.pack()["risk_assessment"]["internal_tier"], "high")

    def test_32_approval_is_sandbox_only(self) -> None:
        approval = self.pack()["approval"]
        self.assertEqual(approval["decision"], "conditional_synthetic_sandbox_only")
        self.assertFalse(approval["production_approved"])

    def test_33_approval_is_bound_to_versions(self) -> None:
        pack = self.pack()
        self.assertEqual(
            pack["approval"]["approved_version_set"],
            pack["component_register"]["approved_version_set"],
        )

    def test_34_monitoring_has_threshold_action_owner(self) -> None:
        self.assertTrue(
            all(
                item["metric"] and item["threshold"] and item["action"] and item["owner"]
                for item in self.pack()["monitoring_plan"]
            )
        )

    def test_35_change_triggers_cover_material_versions(self) -> None:
        text = " ".join(self.pack()["change_triggers"])
        self.assertIn("model", text)
        self.assertIn("real data", text)

    def test_36_retirement_revokes_identity_and_keeps_manual_path(self) -> None:
        text = " ".join(self.pack()["retirement_plan"])
        self.assertIn("revoke service identity", text)
        self.assertIn("manual checklist", text)

    def test_37_source_status_is_current_and_bounded(self) -> None:
        status = self.pack()["source_status"]
        self.assertEqual(status["as_of"], "2026-07-22")
        self.assertIn("revision in progress", status["nist_ai_rmf"]["version_status"])
        self.assertIn("not performed", status["legal_review"])

    def test_38_missing_pack_section_rejected(self) -> None:
        pack = self.pack()
        del pack["retirement_plan"]
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_39_modified_system_id_rejected(self) -> None:
        pack = self.pack()
        pack["system_register"]["system_id"] = "other"
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_40_production_approval_rejected(self) -> None:
        pack = self.pack()
        pack["approval"]["production_approved"] = True
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_41_version_binding_mismatch_rejected(self) -> None:
        pack = self.pack()
        pack["approval"]["approved_version_set"]["MODEL-001"] = "other"
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_42_incomplete_monitoring_rejected(self) -> None:
        pack = self.pack()
        pack["monitoring_plan"][0]["owner"] = ""
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_43_short_retirement_plan_rejected(self) -> None:
        pack = self.pack()
        pack["retirement_plan"] = ["stop"]
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_44_missing_legal_boundary_rejected(self) -> None:
        pack = self.pack()
        pack["disclaimer"] = "teaching only"
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_45_self_test_passes(self) -> None:
        app.self_test()

    def test_46_cli_default_outputs_valid_pack(self) -> None:
        code, stdout, stderr = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["approval"]["production_approved"], False)
        self.assertEqual(stderr, "")

    def test_47_cli_self_test_outputs_json(self) -> None:
        code, stdout, stderr = self.run_main("--self-test")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout), {"self_test": "passed"})
        self.assertEqual(stderr, "")

    def test_48_cli_contract_failure_returns_two(self) -> None:
        invalid = self.scenario()
        invalid["unknown"] = True
        with patch.object(app, "SCENARIO", invalid):
            code, stdout, stderr = self.run_main()
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("governance contract error", stderr)

    def test_49_production_code_has_no_assert_statement(self) -> None:
        tree = ast.parse(Path(app.__file__).read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))

    def test_50_rendered_pack_contains_no_credential_marker(self) -> None:
        rendered = json.dumps(self.pack(), ensure_ascii=False).lower()
        self.assertFalse(any(marker in rendered for marker in ("api_key", "access_token", "bearer ", "password")))

    def test_51_production_status_is_rejected_at_input(self) -> None:
        value = self.scenario()
        value["status"] = "production"
        self.expect_scenario_error(value)

    def test_52_autonomous_decision_role_is_rejected_at_input(self) -> None:
        value = self.scenario()
        value["decision_role"] = "autonomous_final_decision"
        self.expect_scenario_error(value)

    def test_53_personal_data_must_match_risk_fact(self) -> None:
        value = self.scenario()
        value["data"][0]["personal_data"] = True
        self.expect_scenario_error(value)

    def test_54_sensitive_data_must_match_risk_fact(self) -> None:
        value = self.scenario()
        value["data"][0]["sensitive_data"] = True
        self.expect_scenario_error(value)

    def test_55_tier_risk_rejects_partial_facts(self) -> None:
        with self.assertRaises(app.GovernanceError):
            app.tier_risk({"severity": 1, "likelihood": 1})

    def test_56_tier_risk_rejects_truthy_string_flag(self) -> None:
        facts = self.risk_facts(autonomous_action="false")
        with self.assertRaises(app.GovernanceError):
            app.tier_risk(facts)

    def test_57_sensitive_data_requires_privacy_review(self) -> None:
        facts = self.risk_facts(
            severity=1,
            likelihood=1,
            consequential_context=False,
            sensitive_or_personal_data=True,
        )
        result = app.tier_risk(facts)
        self.assertEqual(result["internal_tier"], "low")
        self.assertIn("privacy", result["required_reviews"])

    def test_58_empty_impact_assessment_is_rejected(self) -> None:
        pack = self.pack()
        pack["impact_assessment"] = {}
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_59_missing_incident_plan_is_rejected(self) -> None:
        pack = self.pack()
        pack["incident_and_hazard_plan"] = None
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_60_source_status_requires_official_url(self) -> None:
        pack = self.pack()
        del pack["source_status"]["nist_ai_rmf"]["official_url"]
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_61_mutating_both_version_copies_cannot_bypass_binding(self) -> None:
        pack = self.pack()
        pack["component_register"]["approved_version_set"]["MODEL-001"] = "other"
        pack["approval"]["approved_version_set"]["MODEL-001"] = "other"
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_62_scenario_fingerprint_changes_with_material_fact(self) -> None:
        original = app.validate_scenario(self.scenario())
        changed = self.scenario()
        changed["components"][0]["version"] = "snapshot-v2"
        changed = app.validate_scenario(changed)
        self.assertNotEqual(app.scenario_fingerprint(original), app.scenario_fingerprint(changed))

    def test_63_invalid_review_date_is_rejected(self) -> None:
        pack = self.pack()
        pack["system_register"]["next_review"] = "21-08-2026"
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_64_expired_approval_date_is_rejected(self) -> None:
        pack = self.pack()
        pack["approval"]["expires"] = "2026-07-20"
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_65_monitoring_unknown_field_is_rejected(self) -> None:
        pack = self.pack()
        pack["monitoring_plan"][0]["extra"] = "x"
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_66_role_section_missing_nested_field_is_rejected(self) -> None:
        pack = self.pack()
        del pack["role_assignment"]["decision_rights"]["emergency_stop"]
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_67_data_register_mutation_is_rejected(self) -> None:
        pack = self.pack()
        pack["component_register"]["data"][0]["retention"] = "forever"
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_68_custom_scenario_pack_requires_same_scenario_for_validation(self) -> None:
        scenario = self.scenario()
        scenario["components"][0]["version"] = "snapshot-v2"
        pack = app.build_pack(scenario)
        app.validate_pack(pack, scenario)
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_69_approval_fingerprint_mutation_is_rejected(self) -> None:
        pack = self.pack()
        pack["approval"]["scenario_sha256"] = "0" * 64
        with self.assertRaises(app.GovernanceError):
            app.validate_pack(pack)

    def test_70_data_version_must_be_nonempty(self) -> None:
        value = self.scenario()
        value["data"][0]["version"] = ""
        self.expect_scenario_error(value)

    def test_71_data_owner_must_be_nonempty(self) -> None:
        value = self.scenario()
        value["data"][0]["owner"] = ""
        self.expect_scenario_error(value)

    def test_72_vendor_profile_snapshot_must_be_nonempty(self) -> None:
        value = self.scenario()
        value["vendor"]["profile_snapshot"] = ""
        self.expect_scenario_error(value)

    def test_73_vendor_owner_must_be_nonempty(self) -> None:
        value = self.scenario()
        value["vendor"]["owner"] = ""
        self.expect_scenario_error(value)


if __name__ == "__main__":
    unittest.main()
