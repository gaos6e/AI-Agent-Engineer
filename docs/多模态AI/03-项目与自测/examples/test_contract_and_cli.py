"""Strict-contract, routing, privacy, and CLI tests for multimodal_router.py."""

from __future__ import annotations

import ast
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import multimodal_router as app


HERE = Path(app.__file__).resolve().parent


class ContractAndCliTests(unittest.TestCase):
    def manifest(self) -> dict:
        return app.load_manifest(HERE / "media_manifest.json")

    def write_text(self, text: str) -> Path:
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        )
        with handle:
            handle.write(text)
        path = Path(handle.name)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def write_manifest(self, value: object) -> Path:
        return self.write_text(json.dumps(value, ensure_ascii=False))

    def run_main(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = app.main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def expect_error(self, value: object) -> None:
        with self.assertRaises(app.ManifestError):
            app.MultimodalRouter(value)  # type: ignore[arg-type]

    def test_01_duplicate_json_key_rejected(self) -> None:
        path = self.write_text('{"policy":{},"policy":{}}')
        with self.assertRaisesRegex(app.ManifestError, r"duplicate JSON key"):
            app.load_manifest(path)

    def test_02_nonstandard_json_constant_rejected(self) -> None:
        path = self.write_text('{"value":NaN}')
        with self.assertRaisesRegex(app.ManifestError, r"non-standard JSON constant"):
            app.load_manifest(path)

    def test_03_invalid_json_rejected(self) -> None:
        path = self.write_text("{")
        with self.assertRaisesRegex(app.ManifestError, r"invalid JSON"):
            app.load_manifest(path)

    def test_04_missing_file_wrapped(self) -> None:
        with self.assertRaisesRegex(app.ManifestError, r"cannot read"):
            app.load_manifest(Path("definitely-missing-media-manifest.json"))

    def test_05_json_root_must_be_object(self) -> None:
        path = self.write_text("[]")
        with self.assertRaisesRegex(app.ManifestError, r"root must be an object"):
            app.load_manifest(path)

    def test_06_manifest_top_fields_are_exact(self) -> None:
        value = self.manifest()
        value["model"] = "not-part-of-contract"
        self.expect_error(value)

    def test_07_manifest_missing_top_field_rejected(self) -> None:
        value = self.manifest()
        del value["query"]
        self.expect_error(value)

    def test_08_policy_must_be_object(self) -> None:
        value = self.manifest()
        value["policy"] = []
        self.expect_error(value)

    def test_09_policy_fields_are_exact(self) -> None:
        value = self.manifest()
        value["policy"]["vendor"] = "x"
        self.expect_error(value)

    def test_10_allowed_mime_must_be_nonempty_list(self) -> None:
        value = self.manifest()
        value["policy"]["allowed_mime"] = []
        self.expect_error(value)

    def test_11_allowed_mime_values_must_be_text(self) -> None:
        value = self.manifest()
        value["policy"]["allowed_mime"] = [1]
        self.expect_error(value)

    def test_12_allowed_mime_must_be_unique(self) -> None:
        value = self.manifest()
        value["policy"]["allowed_mime"].append("image/png")
        self.expect_error(value)

    def test_13_external_privacy_class_must_be_known(self) -> None:
        value = self.manifest()
        value["policy"]["external_processing_allowed_for"] = ["secret-ish"]
        self.expect_error(value)

    def test_14_external_privacy_classes_must_be_unique(self) -> None:
        value = self.manifest()
        value["policy"]["external_processing_allowed_for"] = ["public", "public"]
        self.expect_error(value)

    def test_15_policy_integers_reject_bool_and_zero(self) -> None:
        for field, invalid in (("max_bytes_per_asset", True), ("budget_units", 0)):
            value = self.manifest()
            value["policy"][field] = invalid
            with self.subTest(field=field):
                self.expect_error(value)

    def test_16_query_must_be_object(self) -> None:
        value = self.manifest()
        value["query"] = []
        self.expect_error(value)

    def test_17_query_fields_are_exact(self) -> None:
        value = self.manifest()
        value["query"]["prompt"] = "x"
        self.expect_error(value)

    def test_18_required_modalities_must_be_nonempty(self) -> None:
        value = self.manifest()
        value["query"]["required_modalities"] = []
        self.expect_error(value)

    def test_19_required_modality_must_be_supported(self) -> None:
        value = self.manifest()
        value["query"]["required_modalities"] = ["depth"]
        self.expect_error(value)

    def test_20_required_modalities_must_be_unique(self) -> None:
        value = self.manifest()
        value["query"]["required_modalities"] = ["image", "image"]
        self.expect_error(value)

    def test_21_assets_must_be_nonempty_array(self) -> None:
        value = self.manifest()
        value["assets"] = []
        self.expect_error(value)

    def test_22_each_asset_must_be_object(self) -> None:
        value = self.manifest()
        value["assets"] = ["file"]
        self.expect_error(value)

    def test_23_missing_required_asset_field_rejected(self) -> None:
        value = self.manifest()
        del value["assets"][0]["detected_mime"]
        self.expect_error(value)

    def test_24_unknown_asset_field_rejected(self) -> None:
        value = self.manifest()
        value["assets"][0]["caption"] = "untrusted"
        self.expect_error(value)

    def test_25_asset_id_must_be_nonempty(self) -> None:
        value = self.manifest()
        value["assets"][0]["asset_id"] = ""
        self.expect_error(value)

    def test_26_asset_ids_must_be_unique(self) -> None:
        value = self.manifest()
        value["assets"].append(copy.deepcopy(value["assets"][0]))
        self.expect_error(value)

    def test_27_asset_text_fields_must_be_nonempty(self) -> None:
        value = self.manifest()
        value["assets"][0]["file_name"] = ""
        self.expect_error(value)

    def test_28_asset_bytes_must_be_positive_integer(self) -> None:
        value = self.manifest()
        value["assets"][0]["bytes"] = True
        self.expect_error(value)

    def test_29_asset_privacy_class_must_be_known(self) -> None:
        value = self.manifest()
        value["assets"][0]["privacy"] = "classified"
        self.expect_error(value)

    def test_30_optional_media_metadata_must_be_positive(self) -> None:
        value = self.manifest()
        value["assets"][0]["width"] = 0
        self.expect_error(value)

    def test_31_modality_mapping(self) -> None:
        cases = {
            "application/pdf": "document", "image/png": "image",
            "audio/wav": "audio", "video/mp4": "video",
            "text/plain": "text", "application/octet-stream": None,
        }
        for mime, expected in cases.items():
            with self.subTest(mime=mime):
                self.assertEqual(app.modality_for(mime), expected)

    def test_32_fixture_builds_ready_plan(self) -> None:
        report = app.MultimodalRouter(self.manifest()).build_plan()
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["total_cost_units"], 13)

    def test_33_disallowed_mime_blocks_asset(self) -> None:
        value = self.manifest()
        value["policy"]["allowed_mime"].remove("image/png")
        report = app.MultimodalRouter(value).build_plan()
        self.assertIn("mime_not_allowed:IMG-1:image/png", report["errors"])

    def test_34_oversize_asset_is_blocked(self) -> None:
        value = self.manifest()
        value["policy"]["max_bytes_per_asset"] = 100
        report = app.MultimodalRouter(value).build_plan()
        self.assertIn("asset_too_large:IMG-1", report["errors"])

    def test_35_allowed_but_unsupported_mime_is_blocked(self) -> None:
        value = self.manifest()
        value["policy"]["allowed_mime"].append("application/octet-stream")
        asset = value["assets"][0]
        asset["declared_mime"] = "application/octet-stream"
        asset["detected_mime"] = "application/octet-stream"
        report = app.MultimodalRouter(value).build_plan()
        self.assertIn("unsupported_modality:IMG-1:application/octet-stream", report["errors"])

    def test_36_missing_audio_duration_is_reported_not_crash(self) -> None:
        value = self.manifest()
        del value["assets"][1]["duration_ms"]
        report = app.MultimodalRouter(value).build_plan()
        self.assertTrue(any(item.startswith("invalid_media_metadata:AUD-1:") for item in report["errors"]))

    def test_37_missing_image_dimensions_are_reported(self) -> None:
        value = self.manifest()
        del value["assets"][0]["width"]
        report = app.MultimodalRouter(value).build_plan()
        self.assertTrue(any(item.startswith("invalid_media_metadata:IMG-1:") for item in report["errors"]))

    def test_38_missing_document_pages_are_reported(self) -> None:
        value = self.manifest()
        del value["assets"][3]["pages"]
        report = app.MultimodalRouter(value).build_plan()
        self.assertTrue(any(item.startswith("invalid_media_metadata:DOC-1:") for item in report["errors"]))

    def test_39_personal_external_processing_requires_redaction(self) -> None:
        value = self.manifest()
        value["policy"]["external_processing_allowed_for"].append("personal")
        report = app.MultimodalRouter(value).build_plan()
        audio = next(item for item in report["assets"] if item["asset_id"] == "AUD-1")
        self.assertEqual(audio["privacy_action"], "redact_then_external")

    def test_40_restricted_remains_local_even_if_policy_lists_it(self) -> None:
        value = self.manifest()
        value["assets"][0]["privacy"] = "restricted"
        value["policy"]["external_processing_allowed_for"].append("restricted")
        report = app.MultimodalRouter(value).build_plan()
        image = next(item for item in report["assets"] if item["asset_id"] == "IMG-1")
        self.assertEqual(image["privacy_action"], "local_only")

    def test_41_missing_required_modality_is_blocked(self) -> None:
        value = self.manifest()
        value["assets"] = [item for item in value["assets"] if item["asset_id"] != "VID-1"]
        report = app.MultimodalRouter(value).build_plan()
        self.assertIn("missing_required_modality:video", report["errors"])

    def test_42_budget_is_global_and_never_silently_reduced(self) -> None:
        value = self.manifest()
        value["policy"]["budget_units"] = 12
        report = app.MultimodalRouter(value).build_plan()
        self.assertEqual(report["total_cost_units"], 13)
        self.assertIn("budget_exceeded:13>12", report["errors"])

    def test_43_router_does_not_mutate_manifest(self) -> None:
        value = self.manifest()
        before = copy.deepcopy(value)
        app.MultimodalRouter(value).build_plan()
        self.assertEqual(value, before)

    def test_44_report_disclaims_real_media_and_vendor_cost(self) -> None:
        notes = " ".join(app.MultimodalRouter(self.manifest()).build_plan()["notes"])
        self.assertIn("synthetic", notes)
        self.assertIn("no media file", notes)
        self.assertIn("no network", notes)

    def test_45_cli_ready_returns_zero(self) -> None:
        path = self.write_manifest(self.manifest())
        code, stdout, stderr = self.run_main(str(path))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["status"], "ready")
        self.assertEqual(stderr, "")

    def test_46_cli_blocked_returns_one(self) -> None:
        value = self.manifest()
        value["policy"]["budget_units"] = 1
        path = self.write_manifest(value)
        code, stdout, stderr = self.run_main(str(path))
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout)["status"], "blocked")
        self.assertEqual(stderr, "")

    def test_47_cli_contract_error_returns_two(self) -> None:
        value = self.manifest()
        value["extra"] = True
        path = self.write_manifest(value)
        code, stdout, stderr = self.run_main(str(path))
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("manifest error", stderr)

    def test_48_cli_output_file_matches_stdout(self) -> None:
        manifest_path = self.write_manifest(self.manifest())
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "plan.json"
            code, stdout, stderr = self.run_main(
                str(manifest_path), "--output", str(output)
            )
            written = output.read_text(encoding="utf-8")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(written), json.loads(stdout))
        self.assertEqual(stderr, "")

    def test_49_production_code_has_no_assert_statement(self) -> None:
        tree = ast.parse(Path(app.__file__).read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))

    def test_50_report_is_json_serializable(self) -> None:
        report = app.MultimodalRouter(self.manifest()).build_plan()
        self.assertEqual(json.loads(json.dumps(report)), report)


if __name__ == "__main__":
    unittest.main()
