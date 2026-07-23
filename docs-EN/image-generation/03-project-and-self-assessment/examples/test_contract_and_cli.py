from __future__ import annotations

import ast
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from audit_image_plan import (
    FixtureError,
    audit_plan,
    load_plan,
    normalized_hash,
    validate_contract,
    validate_plan,
)


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "audit_image_plan.py"
FIXTURE = HERE / "image_task_plan.json"


def valid_plan() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def reference_asset(
    role: str = "source_image", asset_id: str = "asset-1"
) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "source_revision": "asset-1-r1",
        "role": role,
        "source_reference": "synthetic://asset-1",
        "content_sha256": "a" * 64,
        "rights_reference": "synthetic-rights-record",
        "acl_reference": "synthetic-acl-record",
    }


class TemporaryFileCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="image-test-", dir=HERE)
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "plan.json"

    def write_text(self, text: str) -> Path:
        self.path.write_text(text, encoding="utf-8")
        return self.path

    def write_plan(self, plan: object) -> Path:
        return self.write_text(json.dumps(plan, ensure_ascii=False, allow_nan=False))


class StrictJsonTests(TemporaryFileCase):
    def test_loads_valid_plan(self) -> None:
        self.assertEqual(load_plan(FIXTURE)["task_id"], "img-course-cover-001")

    def test_rejects_duplicate_key(self) -> None:
        raw = FIXTURE.read_text(encoding="utf-8").replace(
            '"schema_version": "1.0",',
            '"schema_version": "1.0", "schema_version": "1.0",',
            1,
        )
        with self.assertRaisesRegex(FixtureError, "Duplicate JSON key"):
            load_plan(self.write_text(raw))

    def test_rejects_nan(self) -> None:
        raw = FIXTURE.read_text(encoding="utf-8").replace("1080", "NaN", 1)
        with self.assertRaisesRegex(FixtureError, "Non-finite"):
            load_plan(self.write_text(raw))

    def test_rejects_infinity(self) -> None:
        raw = FIXTURE.read_text(encoding="utf-8").replace("1080", "Infinity", 1)
        with self.assertRaisesRegex(FixtureError, "Non-finite"):
            load_plan(self.write_text(raw))

    def test_rejects_malformed_json(self) -> None:
        with self.assertRaisesRegex(FixtureError, "Invalid JSON"):
            load_plan(self.write_text("{"))

    def test_rejects_missing_file(self) -> None:
        with self.assertRaisesRegex(FixtureError, "Unable to read"):
            load_plan(self.path)

    def test_rejects_invalid_utf8(self) -> None:
        self.path.write_bytes(b"\xff\xfe")
        with self.assertRaisesRegex(FixtureError, "Unable to read"):
            load_plan(self.path)

    def test_rejects_non_object_root(self) -> None:
        with self.assertRaisesRegex(FixtureError, "root object"):
            load_plan(self.write_text("[]"))


class TopAndPromptContractTests(unittest.TestCase):
    def assert_invalid(self, plan: object, pattern: str) -> None:
        with self.assertRaisesRegex(FixtureError, pattern):
            validate_contract(plan)

    def test_accepts_valid_plan(self) -> None:
        self.assertEqual(validate_contract(valid_plan())["schema_version"], "1.0")

    def test_missing_top_field(self) -> None:
        plan = valid_plan()
        del plan["purpose"]
        self.assert_invalid(plan, "missing fields")

    def test_unknown_top_field(self) -> None:
        plan = valid_plan()
        plan["provider_request"] = {}
        self.assert_invalid(plan, "unknown fields")

    def test_wrong_schema_version(self) -> None:
        plan = valid_plan()
        plan["schema_version"] = "2.0"
        self.assert_invalid(plan, "schema_version")

    def test_empty_top_text(self) -> None:
        for field in ("task_id", "purpose", "audience"):
            with self.subTest(field=field):
                plan = valid_plan()
                plan[field] = "  "
                self.assert_invalid(plan, field)

    def test_invalid_task_type(self) -> None:
        plan = valid_plan()
        plan["task_type"] = "upscale"
        self.assert_invalid(plan, "task_type")

    def test_prompt_must_be_object(self) -> None:
        plan = valid_plan()
        plan["prompt"] = []
        self.assert_invalid(plan, "prompt")

    def test_prompt_missing_field(self) -> None:
        plan = valid_plan()
        del plan["prompt"]["lighting"]
        self.assert_invalid(plan, "missing fields")

    def test_prompt_unknown_field(self) -> None:
        plan = valid_plan()
        plan["prompt"]["negative_prompt"] = "demo"
        self.assert_invalid(plan, "unknown fields")

    def test_prompt_text_fields_must_be_nonempty(self) -> None:
        plan = valid_plan()
        plan["prompt"]["subject"] = ""
        self.assert_invalid(plan, "prompt.subject")

    def test_prompt_lists_must_be_nonempty(self) -> None:
        plan = valid_plan()
        plan["prompt"]["must_include"] = []
        self.assert_invalid(plan, "non-empty list")

    def test_prompt_list_items_must_be_strings(self) -> None:
        plan = valid_plan()
        plan["prompt"]["must_avoid"] = [1]
        self.assert_invalid(plan, "non-empty string")

    def test_prompt_lists_reject_duplicates(self) -> None:
        plan = valid_plan()
        plan["prompt"]["must_include"] = ["robot", "robot"]
        self.assert_invalid(plan, "duplicate items")


class OutputAndAssetContractTests(unittest.TestCase):
    def assert_invalid(self, plan: object, pattern: str) -> None:
        with self.assertRaisesRegex(FixtureError, pattern):
            validate_contract(plan)

    def test_output_missing_field(self) -> None:
        plan = valid_plan()
        del plan["output"]["format"]
        self.assert_invalid(plan, "missing fields")

    def test_output_unknown_field(self) -> None:
        plan = valid_plan()
        plan["output"]["quality"] = "high"
        self.assert_invalid(plan, "unknown fields")

    def test_ratio_rejects_missing_colon(self) -> None:
        plan = valid_plan()
        plan["output"]["aspect_ratio"] = "0.8"
        self.assert_invalid(plan, "aspect_ratio")

    def test_ratio_rejects_zero(self) -> None:
        plan = valid_plan()
        plan["output"]["aspect_ratio"] = "0:5"
        self.assert_invalid(plan, "aspect_ratio")

    def test_ratio_rejects_nan_text(self) -> None:
        plan = valid_plan()
        plan["output"]["aspect_ratio"] = "NaN:1"
        self.assert_invalid(plan, "aspect_ratio")

    def test_dimensions_reject_boolean(self) -> None:
        plan = valid_plan()
        plan["output"]["width"] = True
        self.assert_invalid(plan, "width")

    def test_dimensions_reject_zero(self) -> None:
        plan = valid_plan()
        plan["output"]["height"] = 0
        self.assert_invalid(plan, "height")

    def test_candidate_count_rejects_float(self) -> None:
        plan = valid_plan()
        plan["output"]["candidate_count"] = 1.5
        self.assert_invalid(plan, "candidate_count")

    def test_format_must_be_string(self) -> None:
        plan = valid_plan()
        plan["output"]["format"] = 1
        self.assert_invalid(plan, "format")

    def test_reference_assets_must_be_list(self) -> None:
        plan = valid_plan()
        plan["reference_assets"] = {}
        self.assert_invalid(plan, "reference_assets")

    def test_asset_must_be_object(self) -> None:
        plan = valid_plan()
        plan["reference_assets"] = [[]]
        self.assert_invalid(plan, r"reference_assets\[0\]")

    def test_asset_missing_field(self) -> None:
        plan = valid_plan()
        asset = reference_asset()
        del asset["rights_reference"]
        plan["reference_assets"] = [asset]
        self.assert_invalid(plan, "missing fields")

    def test_asset_source_revision_must_be_nonempty(self) -> None:
        plan = valid_plan()
        asset = reference_asset()
        asset["source_revision"] = ""
        plan["reference_assets"] = [asset]
        self.assert_invalid(plan, "source_revision")

    def test_asset_acl_reference_must_be_nonempty(self) -> None:
        plan = valid_plan()
        asset = reference_asset()
        asset["acl_reference"] = ""
        plan["reference_assets"] = [asset]
        self.assert_invalid(plan, "acl_reference")

    def test_asset_unknown_field(self) -> None:
        plan = valid_plan()
        asset = reference_asset()
        asset["url"] = "https://example.invalid"
        plan["reference_assets"] = [asset]
        self.assert_invalid(plan, "unknown fields")

    def test_asset_role_must_be_known(self) -> None:
        plan = valid_plan()
        plan["reference_assets"] = [reference_asset("unknown")]
        self.assert_invalid(plan, "role")

    def test_asset_hash_must_be_lowercase_sha256(self) -> None:
        plan = valid_plan()
        asset = reference_asset()
        asset["content_sha256"] = "A" * 64
        plan["reference_assets"] = [asset]
        self.assert_invalid(plan, "64 lowercase")

    def test_asset_ids_must_be_unique(self) -> None:
        plan = valid_plan()
        plan["reference_assets"] = [reference_asset(), reference_asset("mask")]
        self.assert_invalid(plan, "Duplicate asset_id")


class GovernanceContractTests(unittest.TestCase):
    def assert_invalid(self, plan: object, pattern: str) -> None:
        with self.assertRaisesRegex(FixtureError, pattern):
            validate_contract(plan)

    def test_risk_missing_field(self) -> None:
        plan = valid_plan()
        del plan["risk"]["minor"]
        self.assert_invalid(plan, "missing fields")

    def test_risk_boolean_type(self) -> None:
        plan = valid_plan()
        plan["risk"]["real_person"] = 0
        self.assert_invalid(plan, "real_person")

    def test_risk_plan_text_nonempty(self) -> None:
        plan = valid_plan()
        plan["risk"]["provenance_plan"] = ""
        self.assert_invalid(plan, "provenance_plan")

    def test_lineage_text_must_be_nonempty(self) -> None:
        plan = valid_plan()
        plan["lineage"]["transform_id"] = ""
        self.assert_invalid(plan, "transform_id")

    def test_governance_fields_have_the_declared_types(self) -> None:
        plan = valid_plan()
        plan["governance"]["object_acl_required"] = "yes"
        self.assert_invalid(plan, "object_acl_required")

    def test_acceptance_must_be_nonempty(self) -> None:
        plan = valid_plan()
        plan["acceptance"] = []
        self.assert_invalid(plan, "acceptance")

    def test_acceptance_item_exact_fields(self) -> None:
        plan = valid_plan()
        plan["acceptance"][0]["weight"] = 1
        self.assert_invalid(plan, "unknown fields")

    def test_acceptance_hard_failure_boolean(self) -> None:
        plan = valid_plan()
        plan["acceptance"][0]["hard_failure"] = 1
        self.assert_invalid(plan, "hard_failure")

    def test_budget_positive_ints(self) -> None:
        plan = valid_plan()
        plan["budget"]["max_attempts"] = False
        self.assert_invalid(plan, "max_attempts")

    def test_budget_flags_boolean(self) -> None:
        plan = valid_plan()
        plan["budget"]["pricing_source_required_at_run"] = "yes"
        self.assert_invalid(plan, "pricing_source")

    def test_reproducibility_missing_field(self) -> None:
        plan = valid_plan()
        del plan["reproducibility"]["adapter_version"]
        self.assert_invalid(plan, "missing fields")

    def test_reproducibility_text_nonempty(self) -> None:
        plan = valid_plan()
        plan["reproducibility"]["provider"] = ""
        self.assert_invalid(plan, "provider")

    def test_reproducibility_hash_flag_boolean(self) -> None:
        plan = valid_plan()
        plan["reproducibility"]["save_normalized_request_hash"] = 1
        self.assert_invalid(plan, "save_normalized_request_hash")


class AuditTests(unittest.TestCase):
    def test_valid_fixture_passes(self) -> None:
        self.assertEqual(audit_plan(valid_plan()), [])

    def test_validate_plan_compatibility_helper(self) -> None:
        self.assertEqual(validate_plan(valid_plan()), [])
        self.assertIn("Input contract error", validate_plan([])[0])

    def test_ratio_mismatch(self) -> None:
        plan = valid_plan()
        plan["output"]["width"] = 1000
        self.assertIn("aspect_ratio", " ".join(audit_plan(plan)))

    def test_unsupported_output_format(self) -> None:
        plan = valid_plan()
        plan["output"]["format"] = "gif"
        self.assertIn("output.format", " ".join(audit_plan(plan)))

    def test_include_avoid_conflict(self) -> None:
        plan = valid_plan()
        plan["prompt"]["must_avoid"].append(plan["prompt"]["must_include"][0])
        self.assertIn("conflicts", " ".join(audit_plan(plan)))

    def test_image_to_image_requires_source(self) -> None:
        plan = valid_plan()
        plan["task_type"] = "image_to_image"
        self.assertIn("source_image", " ".join(audit_plan(plan)))

    def test_inpainting_requires_source_and_mask(self) -> None:
        plan = valid_plan()
        plan["task_type"] = "inpainting"
        plan["reference_assets"] = [reference_asset("source_image")]
        self.assertIn("mask", " ".join(audit_plan(plan)))

    def test_inpainting_with_both_roles_passes_asset_gate(self) -> None:
        plan = valid_plan()
        plan["task_type"] = "inpainting"
        plan["reference_assets"] = [
            reference_asset("source_image", "source"),
            reference_asset("mask", "mask"),
        ]
        self.assertNotIn(
            "required reference asset roles", " ".join(audit_plan(plan))
        )

    def test_asset_source_revision_cannot_be_incomplete(self) -> None:
        plan = valid_plan()
        asset = reference_asset()
        asset["source_revision"] = "TO_BE_FILLED"
        plan["reference_assets"] = [asset]
        self.assertIn("source_revision", " ".join(audit_plan(plan)))

    def test_asset_acl_reference_cannot_be_incomplete(self) -> None:
        plan = valid_plan()
        asset = reference_asset()
        asset["acl_reference"] = "ACL_NOT_SET"
        plan["reference_assets"] = [asset]
        self.assertIn("acl_reference", " ".join(audit_plan(plan)))

    def test_rights_confirmation_is_hard_gate(self) -> None:
        plan = valid_plan()
        plan["risk"]["rights_confirmed"] = False
        self.assertIn("rights_confirmed", " ".join(audit_plan(plan)))

    def test_human_review_is_hard_gate(self) -> None:
        plan = valid_plan()
        plan["risk"]["human_review_required"] = False
        self.assertIn("human_review_required", " ".join(audit_plan(plan)))

    def test_lineage_cannot_contain_placeholder(self) -> None:
        plan = valid_plan()
        plan["lineage"]["release_id"] = "RELEASE_NOT_SET"
        self.assertIn("release_id", " ".join(audit_plan(plan)))

    def test_object_acl_is_a_hard_gate_before_scoring(self) -> None:
        plan = valid_plan()
        plan["governance"]["object_acl_required"] = False
        self.assertIn(
            "object-level authorization/ACL", " ".join(audit_plan(plan))
        )

    def test_deletion_propagation_plan_cannot_be_incomplete(self) -> None:
        plan = valid_plan()
        plan["governance"]["deletion_propagation_plan"] = "NOT_SET"
        self.assertIn("deletion_propagation_plan", " ".join(audit_plan(plan)))

    def test_evidence_policy_is_a_hard_gate(self) -> None:
        plan = valid_plan()
        plan["governance"]["evidence_policy"] = "unbounded"
        self.assertIn("evidence_supported", " ".join(audit_plan(plan)))

    def test_duplicate_acceptance_dimension(self) -> None:
        plan = valid_plan()
        plan["acceptance"].append(copy.deepcopy(plan["acceptance"][0]))
        self.assertIn("Duplicate acceptance", " ".join(audit_plan(plan)))

    def test_missing_acceptance_dimension(self) -> None:
        plan = valid_plan()
        plan["acceptance"] = [
            item for item in plan["acceptance"] if item["dimension"] != "safety"
        ]
        self.assertIn("safety", " ".join(audit_plan(plan)))

    def test_candidate_count_respects_budget(self) -> None:
        plan = valid_plan()
        plan["budget"]["max_outputs"] = 2
        self.assertIn("candidate_count", " ".join(audit_plan(plan)))

    def test_runtime_pricing_gate(self) -> None:
        plan = valid_plan()
        plan["budget"]["pricing_source_required_at_run"] = False
        self.assertIn("pricing-source", " ".join(audit_plan(plan)))

    def test_budget_increase_approval_gate(self) -> None:
        plan = valid_plan()
        plan["budget"]["manual_approval_before_budget_increase"] = False
        self.assertIn("manual approval", " ".join(audit_plan(plan)))

    def test_request_hash_gate(self) -> None:
        plan = valid_plan()
        plan["reproducibility"]["save_normalized_request_hash"] = False
        self.assertIn("normalized request hash", " ".join(audit_plan(plan)))

    def test_placeholder_reproducibility_value(self) -> None:
        plan = valid_plan()
        plan["reproducibility"]["provider"] = "PROVIDER_TO_BE_FILLED"
        self.assertIn("placeholder value", " ".join(audit_plan(plan)))

    def test_bad_documentation_date(self) -> None:
        plan = valid_plan()
        plan["reproducibility"]["documentation_checked_on"] = "2026/07/14"
        self.assertIn("YYYY-MM-DD", " ".join(audit_plan(plan)))

    def test_secret_like_value_is_rejected(self) -> None:
        plan = valid_plan()
        plan["purpose"] = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
        self.assertIn("real key", " ".join(audit_plan(plan)))

    def test_normalized_hash_ignores_key_order(self) -> None:
        plan = valid_plan()
        reordered = dict(reversed(list(plan.items())))
        self.assertEqual(normalized_hash(plan), normalized_hash(reordered))

    def test_normalized_hash_changes_with_task(self) -> None:
        plan = valid_plan()
        changed = copy.deepcopy(plan)
        changed["purpose"] += " v2"
        self.assertNotEqual(normalized_hash(plan), normalized_hash(changed))


class CliTests(TemporaryFileCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            check=False,
        )

    def test_valid_plan_exit_zero(self) -> None:
        result = self.run_cli(str(FIXTURE))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Audit passed", result.stdout)

    def test_audit_finding_exit_one(self) -> None:
        plan = valid_plan()
        plan["risk"]["rights_confirmed"] = False
        result = self.run_cli(str(self.write_plan(plan)))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Audit failed", result.stderr)

    def test_contract_error_exit_two(self) -> None:
        plan = valid_plan()
        plan["extra"] = True
        result = self.run_cli(str(self.write_plan(plan)))
        self.assertEqual(result.returncode, 2)
        self.assertIn("Input contract error", result.stderr)

    def test_missing_file_exit_two(self) -> None:
        self.assertEqual(self.run_cli(str(self.path)).returncode, 2)

    def test_missing_argument_exit_two(self) -> None:
        self.assertEqual(self.run_cli().returncode, 2)

    def test_no_media_or_report_is_written(self) -> None:
        before = {path.name for path in HERE.iterdir()}
        result = self.run_cli(str(FIXTURE))
        after = {path.name for path in HERE.iterdir()}
        self.assertEqual(result.returncode, 0)
        self.assertEqual(before, after)

    def test_production_code_has_no_assert_statement(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))


if __name__ == "__main__":
    unittest.main()
