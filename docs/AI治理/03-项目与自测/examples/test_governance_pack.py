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
        facts = {"severity": 2, "likelihood": 2, "uncertainty": "bounded"}
        result = app.tier_risk(facts)
        self.assertEqual(result["internal_tier"], "low")
        self.assertEqual(result["score"], 4)

    def test_25_medium_risk_matrix_case(self) -> None:
        facts = {"severity": 3, "likelihood": 2, "uncertainty": "bounded"}
        self.assertEqual(app.tier_risk(facts)["internal_tier"], "medium")

    def test_26_high_risk_matrix_case(self) -> None:
        facts = {"severity": 5, "likelihood": 2, "uncertainty": "bounded"}
        self.assertEqual(app.tier_risk(facts)["internal_tier"], "high")

    def test_27_consequential_context_forces_high(self) -> None:
        facts = {
            "severity": 1, "likelihood": 1, "consequential_context": True,
            "uncertainty": "bounded",
        }
        result = app.tier_risk(facts)
        self.assertEqual(result["internal_tier"], "high")
        self.assertTrue(any("consequential" in reason for reason in result["reasons"]))

    def test_28_autonomous_action_forces_high(self) -> None:
        facts = {
            "severity": 1, "likelihood": 1, "autonomous_action": True,
            "uncertainty": "bounded",
        }
        self.assertEqual(app.tier_risk(facts)["internal_tier"], "high")

    def test_29_risk_boundary_disclaims_legal_classification(self) -> None:
        self.assertIn("not a statutory", app.tier_risk({"severity": 1, "likelihood": 1})["boundary"])

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
        self.assertEqual(status["as_of"], "2026-07-14")
        self.assertIn("revision in progress", status["nist_ai_rmf"])
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


if __name__ == "__main__":
    unittest.main()
