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

from validate_video_job import (
    FixtureError,
    audit_package,
    load_package,
    normalized_hash,
    validate_contract,
    validate_package,
)


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "validate_video_job.py"
FIXTURE = HERE / "video_job_package.json"


def valid_package() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def reference_asset(
    role: str = "first_frame", asset_id: str = "asset-1"
) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "role": role,
        "source_reference": "synthetic://asset-1",
        "content_sha256": "a" * 64,
        "rights_reference": "synthetic-rights-record",
    }


class TemporaryFileCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="video-test-", dir=HERE)
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "package.json"

    def write_text(self, text: str) -> Path:
        self.path.write_text(text, encoding="utf-8")
        return self.path

    def write_package(self, package: object) -> Path:
        return self.write_text(
            json.dumps(package, ensure_ascii=False, allow_nan=False)
        )


class StrictJsonTests(TemporaryFileCase):
    def test_loads_valid_package(self) -> None:
        self.assertEqual(load_package(FIXTURE)["project_id"], "video-task-flow-001")

    def test_rejects_duplicate_key(self) -> None:
        raw = FIXTURE.read_text(encoding="utf-8").replace(
            '"schema_version": "1.0",',
            '"schema_version": "1.0", "schema_version": "1.0",',
            1,
        )
        with self.assertRaisesRegex(FixtureError, "JSON 键重复"):
            load_package(self.write_text(raw))

    def test_rejects_nan(self) -> None:
        raw = FIXTURE.read_text(encoding="utf-8").replace("8.0", "NaN", 1)
        with self.assertRaisesRegex(FixtureError, "非有限"):
            load_package(self.write_text(raw))

    def test_rejects_infinity(self) -> None:
        raw = FIXTURE.read_text(encoding="utf-8").replace("8.0", "Infinity", 1)
        with self.assertRaisesRegex(FixtureError, "非有限"):
            load_package(self.write_text(raw))

    def test_rejects_malformed_json(self) -> None:
        with self.assertRaisesRegex(FixtureError, "JSON 无效"):
            load_package(self.write_text("{"))

    def test_rejects_missing_file(self) -> None:
        with self.assertRaisesRegex(FixtureError, "无法读取"):
            load_package(self.path)

    def test_rejects_invalid_utf8(self) -> None:
        self.path.write_bytes(b"\xff\xfe")
        with self.assertRaisesRegex(FixtureError, "无法读取"):
            load_package(self.path)

    def test_rejects_non_object_root(self) -> None:
        with self.assertRaisesRegex(FixtureError, "根对象"):
            load_package(self.write_text("[]"))


class TopAndTechnicalContractTests(unittest.TestCase):
    def assert_invalid(self, package: object, pattern: str) -> None:
        with self.assertRaisesRegex(FixtureError, pattern):
            validate_contract(package)

    def test_accepts_valid_package(self) -> None:
        self.assertEqual(validate_contract(valid_package())["schema_version"], "1.0")

    def test_missing_top_field(self) -> None:
        package = valid_package()
        del package["purpose"]
        self.assert_invalid(package, "缺少字段")

    def test_unknown_top_field(self) -> None:
        package = valid_package()
        package["provider_request"] = {}
        self.assert_invalid(package, "未知字段")

    def test_wrong_schema_version(self) -> None:
        package = valid_package()
        package["schema_version"] = "2.0"
        self.assert_invalid(package, "schema_version")

    def test_empty_top_text(self) -> None:
        for field in ("project_id", "purpose", "audience"):
            with self.subTest(field=field):
                package = valid_package()
                package[field] = "  "
                self.assert_invalid(package, field)

    def test_technical_must_be_object(self) -> None:
        package = valid_package()
        package["technical"] = []
        self.assert_invalid(package, "technical")

    def test_technical_missing_field(self) -> None:
        package = valid_package()
        del package["technical"]["container"]
        self.assert_invalid(package, "缺少字段")

    def test_technical_unknown_field(self) -> None:
        package = valid_package()
        package["technical"]["codec"] = "h264"
        self.assert_invalid(package, "未知字段")

    def test_duration_rejects_boolean(self) -> None:
        package = valid_package()
        package["technical"]["duration_seconds"] = True
        self.assert_invalid(package, "duration_seconds")

    def test_duration_rejects_nonfinite_direct_value(self) -> None:
        package = valid_package()
        package["technical"]["duration_seconds"] = float("inf")
        self.assert_invalid(package, "有限正数")

    def test_fps_rejects_float(self) -> None:
        package = valid_package()
        package["technical"]["fps"] = 24.0
        self.assert_invalid(package, "fps")

    def test_dimensions_reject_boolean(self) -> None:
        package = valid_package()
        package["technical"]["width"] = True
        self.assert_invalid(package, "width")

    def test_dimensions_reject_zero(self) -> None:
        package = valid_package()
        package["technical"]["height"] = 0
        self.assert_invalid(package, "height")

    def test_ratio_rejects_missing_colon(self) -> None:
        package = valid_package()
        package["technical"]["aspect_ratio"] = "1.777"
        self.assert_invalid(package, "aspect_ratio")

    def test_ratio_rejects_nan_text(self) -> None:
        package = valid_package()
        package["technical"]["aspect_ratio"] = "NaN:1"
        self.assert_invalid(package, "aspect_ratio")

    def test_container_must_be_nonempty(self) -> None:
        package = valid_package()
        package["technical"]["container"] = ""
        self.assert_invalid(package, "container")


class ShotAndAssetContractTests(unittest.TestCase):
    def assert_invalid(self, package: object, pattern: str) -> None:
        with self.assertRaisesRegex(FixtureError, pattern):
            validate_contract(package)

    def test_shots_must_be_nonempty(self) -> None:
        package = valid_package()
        package["shots"] = []
        self.assert_invalid(package, "shots")

    def test_shot_must_be_object(self) -> None:
        package = valid_package()
        package["shots"][0] = []
        self.assert_invalid(package, r"shots\[0\]")

    def test_shot_missing_field(self) -> None:
        package = valid_package()
        del package["shots"][0]["prompt"]
        self.assert_invalid(package, "缺少字段")

    def test_shot_unknown_field(self) -> None:
        package = valid_package()
        package["shots"][0]["seed"] = 42
        self.assert_invalid(package, "未知字段")

    def test_shot_text_fields_must_be_nonempty(self) -> None:
        package = valid_package()
        package["shots"][0]["action"] = ""
        self.assert_invalid(package, "action")

    def test_start_rejects_boolean(self) -> None:
        package = valid_package()
        package["shots"][0]["start_seconds"] = False
        self.assert_invalid(package, "start_seconds")

    def test_start_rejects_negative(self) -> None:
        package = valid_package()
        package["shots"][0]["start_seconds"] = -0.1
        self.assert_invalid(package, "start_seconds")

    def test_end_must_follow_start(self) -> None:
        package = valid_package()
        package["shots"][0]["end_seconds"] = 0.0
        self.assert_invalid(package, "end_seconds")

    def test_end_rejects_nonfinite_direct_value(self) -> None:
        package = valid_package()
        package["shots"][0]["end_seconds"] = float("nan")
        self.assert_invalid(package, "end_seconds")

    def test_anchors_must_be_nonempty(self) -> None:
        package = valid_package()
        package["shots"][0]["continuity_anchors"] = []
        self.assert_invalid(package, "非空列表")

    def test_anchor_items_must_be_strings(self) -> None:
        package = valid_package()
        package["shots"][0]["continuity_anchors"] = [1]
        self.assert_invalid(package, "非空字符串")

    def test_anchors_reject_duplicates(self) -> None:
        package = valid_package()
        package["shots"][0]["continuity_anchors"] = ["灯光一致", "灯光一致"]
        self.assert_invalid(package, "重复项")

    def test_reference_assets_must_be_list(self) -> None:
        package = valid_package()
        package["shots"][0]["reference_assets"] = {}
        self.assert_invalid(package, "reference_assets")

    def test_asset_must_be_object(self) -> None:
        package = valid_package()
        package["shots"][0]["reference_assets"] = [[]]
        self.assert_invalid(package, r"reference_assets\[0\]")

    def test_asset_missing_field(self) -> None:
        package = valid_package()
        asset = reference_asset()
        del asset["rights_reference"]
        package["shots"][0]["reference_assets"] = [asset]
        self.assert_invalid(package, "缺少字段")

    def test_asset_unknown_field(self) -> None:
        package = valid_package()
        asset = reference_asset()
        asset["url"] = "https://example.invalid"
        package["shots"][0]["reference_assets"] = [asset]
        self.assert_invalid(package, "未知字段")

    def test_asset_role_must_be_known(self) -> None:
        package = valid_package()
        package["shots"][0]["reference_assets"] = [reference_asset("unknown")]
        self.assert_invalid(package, "role")

    def test_asset_hash_must_be_lowercase_sha256(self) -> None:
        package = valid_package()
        asset = reference_asset()
        asset["content_sha256"] = "A" * 64
        package["shots"][0]["reference_assets"] = [asset]
        self.assert_invalid(package, "64 位")

    def test_asset_ids_must_be_globally_unique(self) -> None:
        package = valid_package()
        package["shots"][0]["reference_assets"] = [reference_asset()]
        package["shots"][1]["reference_assets"] = [reference_asset("last_frame")]
        self.assert_invalid(package, "asset_id 重复")

    def test_asset_text_must_be_nonempty(self) -> None:
        package = valid_package()
        asset = reference_asset()
        asset["rights_reference"] = ""
        package["shots"][0]["reference_assets"] = [asset]
        self.assert_invalid(package, "rights_reference")


class AudioCaptionRiskContractTests(unittest.TestCase):
    def assert_invalid(self, package: object, pattern: str) -> None:
        with self.assertRaisesRegex(FixtureError, pattern):
            validate_contract(package)

    def test_audio_must_be_object(self) -> None:
        package = valid_package()
        package["audio"] = []
        self.assert_invalid(package, "audio")

    def test_audio_missing_field(self) -> None:
        package = valid_package()
        del package["audio"]["mode"]
        self.assert_invalid(package, "缺少字段")

    def test_audio_unknown_field(self) -> None:
        package = valid_package()
        package["audio"]["sample_rate"] = 48000
        self.assert_invalid(package, "未知字段")

    def test_audio_text_must_be_nonempty(self) -> None:
        package = valid_package()
        package["audio"]["narration"] = ""
        self.assert_invalid(package, "narration")

    def test_audio_flags_must_be_boolean(self) -> None:
        package = valid_package()
        package["audio"]["music_rights_confirmed"] = 1
        self.assert_invalid(package, "music_rights_confirmed")

    def test_captions_must_be_object(self) -> None:
        package = valid_package()
        package["captions"] = []
        self.assert_invalid(package, "captions")

    def test_captions_unknown_field(self) -> None:
        package = valid_package()
        package["captions"]["style"] = "default"
        self.assert_invalid(package, "未知字段")

    def test_caption_metadata_must_be_nonempty(self) -> None:
        package = valid_package()
        package["captions"]["language"] = ""
        self.assert_invalid(package, "language")

    def test_cues_must_be_nonempty(self) -> None:
        package = valid_package()
        package["captions"]["cues"] = []
        self.assert_invalid(package, "非空列表")

    def test_cue_must_be_object(self) -> None:
        package = valid_package()
        package["captions"]["cues"][0] = []
        self.assert_invalid(package, r"cues\[0\]")

    def test_cue_unknown_field(self) -> None:
        package = valid_package()
        package["captions"]["cues"][0]["position"] = "bottom"
        self.assert_invalid(package, "未知字段")

    def test_cue_times_must_be_finite(self) -> None:
        package = valid_package()
        package["captions"]["cues"][0]["start_seconds"] = float("nan")
        self.assert_invalid(package, "start_seconds")

    def test_cue_end_must_follow_start(self) -> None:
        package = valid_package()
        package["captions"]["cues"][0]["end_seconds"] = 0.2
        self.assert_invalid(package, "end_seconds")

    def test_cue_text_must_be_nonempty(self) -> None:
        package = valid_package()
        package["captions"]["cues"][0]["text"] = ""
        self.assert_invalid(package, "text")

    def test_risk_must_be_object(self) -> None:
        package = valid_package()
        package["risk"] = []
        self.assert_invalid(package, "risk")

    def test_risk_missing_field(self) -> None:
        package = valid_package()
        del package["risk"]["provenance_plan"]
        self.assert_invalid(package, "缺少字段")

    def test_risk_boolean_type(self) -> None:
        package = valid_package()
        package["risk"]["real_person"] = 0
        self.assert_invalid(package, "real_person")

    def test_risk_text_must_be_nonempty(self) -> None:
        package = valid_package()
        package["risk"]["disclosure_plan"] = ""
        self.assert_invalid(package, "disclosure_plan")


class GovernanceContractTests(unittest.TestCase):
    def assert_invalid(self, package: object, pattern: str) -> None:
        with self.assertRaisesRegex(FixtureError, pattern):
            validate_contract(package)

    def test_acceptance_must_be_nonempty(self) -> None:
        package = valid_package()
        package["acceptance"] = []
        self.assert_invalid(package, "acceptance")

    def test_acceptance_item_exact_fields(self) -> None:
        package = valid_package()
        package["acceptance"][0]["weight"] = 1
        self.assert_invalid(package, "未知字段")

    def test_acceptance_text_must_be_nonempty(self) -> None:
        package = valid_package()
        package["acceptance"][0]["criterion"] = ""
        self.assert_invalid(package, "criterion")

    def test_acceptance_hard_failure_boolean(self) -> None:
        package = valid_package()
        package["acceptance"][0]["hard_failure"] = 1
        self.assert_invalid(package, "hard_failure")

    def test_recovery_missing_field(self) -> None:
        package = valid_package()
        del package["recovery"]["fallback"]
        self.assert_invalid(package, "缺少字段")

    def test_recovery_attempts_positive_int(self) -> None:
        package = valid_package()
        package["recovery"]["max_attempts_per_shot"] = 1.5
        self.assert_invalid(package, "max_attempts_per_shot")

    def test_recovery_flags_boolean(self) -> None:
        package = valid_package()
        package["recovery"]["checkpoint_between_shots"] = "yes"
        self.assert_invalid(package, "checkpoint_between_shots")

    def test_recovery_text_nonempty(self) -> None:
        package = valid_package()
        package["recovery"]["retry_policy"] = ""
        self.assert_invalid(package, "retry_policy")

    def test_budget_missing_field(self) -> None:
        package = valid_package()
        del package["budget"]["max_generated_seconds"]
        self.assert_invalid(package, "缺少字段")

    def test_budget_attempts_positive_int(self) -> None:
        package = valid_package()
        package["budget"]["max_total_attempts"] = True
        self.assert_invalid(package, "max_total_attempts")

    def test_budget_seconds_finite_positive(self) -> None:
        package = valid_package()
        package["budget"]["max_generated_seconds"] = float("inf")
        self.assert_invalid(package, "max_generated_seconds")

    def test_budget_flags_boolean(self) -> None:
        package = valid_package()
        package["budget"]["pricing_source_required_at_run"] = "yes"
        self.assert_invalid(package, "pricing_source")

    def test_adapter_missing_field(self) -> None:
        package = valid_package()
        del package["adapter"]["version"]
        self.assert_invalid(package, "缺少字段")

    def test_adapter_unknown_field(self) -> None:
        package = valid_package()
        package["adapter"]["endpoint"] = "offline"
        self.assert_invalid(package, "未知字段")

    def test_adapter_text_nonempty(self) -> None:
        package = valid_package()
        package["adapter"]["provider"] = ""
        self.assert_invalid(package, "provider")


class AuditTests(unittest.TestCase):
    def test_valid_fixture_passes(self) -> None:
        self.assertEqual(audit_package(valid_package()), [])

    def test_validate_package_compatibility_helper(self) -> None:
        self.assertEqual(validate_package(valid_package()), [])
        self.assertIn("输入合同错误", validate_package([])[0])

    def test_ratio_mismatch(self) -> None:
        package = valid_package()
        package["technical"]["width"] = 1000
        self.assertIn("aspect_ratio", " ".join(audit_package(package)))

    def test_unsupported_container(self) -> None:
        package = valid_package()
        package["technical"]["container"] = "avi"
        self.assertIn("container", " ".join(audit_package(package)))

    def test_first_shot_starts_at_zero(self) -> None:
        package = valid_package()
        package["shots"][0]["start_seconds"] = 0.2
        self.assertIn("0 秒", " ".join(audit_package(package)))

    def test_duplicate_shot_id(self) -> None:
        package = valid_package()
        package["shots"][1]["shot_id"] = package["shots"][0]["shot_id"]
        self.assertIn("shot_id 重复", " ".join(audit_package(package)))

    def test_overlapping_shots(self) -> None:
        package = valid_package()
        package["shots"][1]["start_seconds"] = 2.0
        self.assertIn("重叠", " ".join(audit_package(package)))

    def test_gap_between_shots(self) -> None:
        package = valid_package()
        package["shots"][1]["start_seconds"] = 3.0
        self.assertIn("空隙", " ".join(audit_package(package)))

    def test_shot_outside_duration(self) -> None:
        package = valid_package()
        package["shots"][-1]["end_seconds"] = 9.0
        self.assertIn("超出总时长", " ".join(audit_package(package)))

    def test_timeline_must_cover_duration(self) -> None:
        package = valid_package()
        package["shots"][-1]["end_seconds"] = 7.8
        self.assertIn("完整覆盖", " ".join(audit_package(package)))

    def test_asset_source_cannot_be_incomplete(self) -> None:
        package = valid_package()
        asset = reference_asset()
        asset["source_reference"] = "TO_BE_FILLED"
        package["shots"][0]["reference_assets"] = [asset]
        self.assertIn("source_reference", " ".join(audit_package(package)))

    def test_audio_rights_gate(self) -> None:
        package = valid_package()
        package["audio"]["music_rights_confirmed"] = False
        self.assertIn("music_rights_confirmed", " ".join(audit_package(package)))

    def test_audio_sync_review_gate(self) -> None:
        package = valid_package()
        package["audio"]["sync_review_required"] = False
        self.assertIn("sync_review_required", " ".join(audit_package(package)))

    def test_caption_format_gate(self) -> None:
        package = valid_package()
        package["captions"]["format"] = "srt"
        self.assertIn("webvtt", " ".join(audit_package(package)))

    def test_overlapping_captions(self) -> None:
        package = valid_package()
        package["captions"]["cues"][1]["start_seconds"] = 2.8
        self.assertIn("字幕重叠", "字幕" + " ".join(audit_package(package)))

    def test_caption_outside_duration(self) -> None:
        package = valid_package()
        package["captions"]["cues"][1]["end_seconds"] = 8.5
        self.assertIn("超出总时长", " ".join(audit_package(package)))

    def test_reference_rights_gate(self) -> None:
        package = valid_package()
        package["risk"]["reference_rights_confirmed"] = False
        self.assertIn("reference_rights_confirmed", " ".join(audit_package(package)))

    def test_human_review_gate(self) -> None:
        package = valid_package()
        package["risk"]["human_review_required"] = False
        self.assertIn("human_review_required", " ".join(audit_package(package)))

    def test_real_person_requires_consent_record(self) -> None:
        package = valid_package()
        package["risk"]["real_person"] = True
        self.assertIn("人物同意", " ".join(audit_package(package)))

    def test_duplicate_acceptance_dimension(self) -> None:
        package = valid_package()
        package["acceptance"].append(copy.deepcopy(package["acceptance"][0]))
        self.assertIn("重复", " ".join(audit_package(package)))

    def test_missing_acceptance_dimension(self) -> None:
        package = valid_package()
        package["acceptance"] = [
            item for item in package["acceptance"] if item["dimension"] != "safety"
        ]
        self.assertIn("safety", " ".join(audit_package(package)))

    def test_checkpoint_gate(self) -> None:
        package = valid_package()
        package["recovery"]["checkpoint_between_shots"] = False
        self.assertIn("checkpoint_between_shots", " ".join(audit_package(package)))

    def test_manual_escalation_gate(self) -> None:
        package = valid_package()
        package["recovery"]["manual_escalation_required"] = False
        self.assertIn("manual_escalation_required", " ".join(audit_package(package)))

    def test_total_attempts_must_cover_each_shot(self) -> None:
        package = valid_package()
        package["budget"]["max_total_attempts"] = 2
        self.assertIn("每个镜头", " ".join(audit_package(package)))

    def test_total_attempts_respects_per_shot_envelope(self) -> None:
        package = valid_package()
        package["budget"]["max_total_attempts"] = 10
        self.assertIn("总包络", " ".join(audit_package(package)))

    def test_generated_seconds_cover_delivery(self) -> None:
        package = valid_package()
        package["budget"]["max_generated_seconds"] = 7.0
        self.assertIn("成片总时长", " ".join(audit_package(package)))

    def test_runtime_pricing_gate(self) -> None:
        package = valid_package()
        package["budget"]["pricing_source_required_at_run"] = False
        self.assertIn("定价来源", " ".join(audit_package(package)))

    def test_budget_increase_approval_gate(self) -> None:
        package = valid_package()
        package["budget"]["manual_approval_before_budget_increase"] = False
        self.assertIn("人工批准", " ".join(audit_package(package)))

    def test_adapter_incomplete_value(self) -> None:
        package = valid_package()
        package["adapter"]["provider"] = "PROVIDER_NOT_SET"
        self.assertIn("占位值", " ".join(audit_package(package)))

    def test_bad_documentation_date(self) -> None:
        package = valid_package()
        package["adapter"]["documentation_checked_on"] = "2026/07/14"
        self.assertIn("YYYY-MM-DD", " ".join(audit_package(package)))

    def test_secret_like_value_is_rejected(self) -> None:
        package = valid_package()
        package["purpose"] = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
        self.assertIn("密钥", " ".join(audit_package(package)))

    def test_normalized_hash_ignores_key_order(self) -> None:
        package = valid_package()
        reordered = dict(reversed(list(package.items())))
        self.assertEqual(normalized_hash(package), normalized_hash(reordered))

    def test_normalized_hash_changes_with_package(self) -> None:
        package = valid_package()
        changed = copy.deepcopy(package)
        changed["purpose"] += " v2"
        self.assertNotEqual(normalized_hash(package), normalized_hash(changed))


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

    def test_valid_package_exit_zero(self) -> None:
        result = self.run_cli(str(FIXTURE))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("审计通过", result.stdout)

    def test_audit_finding_exit_one(self) -> None:
        package = valid_package()
        package["risk"]["reference_rights_confirmed"] = False
        result = self.run_cli(str(self.write_package(package)))
        self.assertEqual(result.returncode, 1)
        self.assertIn("审计失败", result.stderr)

    def test_contract_error_exit_two(self) -> None:
        package = valid_package()
        package["extra"] = True
        result = self.run_cli(str(self.write_package(package)))
        self.assertEqual(result.returncode, 2)
        self.assertIn("输入合同错误", result.stderr)

    def test_invalid_json_exit_two(self) -> None:
        result = self.run_cli(str(self.write_text("{")))
        self.assertEqual(result.returncode, 2)

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
