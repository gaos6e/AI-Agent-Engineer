"""Offline tests for multimodal_router.py."""

from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from multimodal_router import ManifestError, MultimodalRouter, load_manifest


HERE = Path(__file__).resolve().parent


def base_manifest() -> dict:
    return load_manifest(HERE / "media_manifest.json")


class MultimodalRouterTests(unittest.TestCase):
    def test_fixture_builds_ready_plan(self) -> None:
        report = MultimodalRouter(base_manifest()).build_plan()
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["total_cost_units"], 13)
        video = next(
            item for item in report["assets"] if item["asset_id"] == "VID-1"
        )
        self.assertIn("video_interval", video["evidence_kinds"])
        self.assertIn("frame_region", video["evidence_kinds"])

    def test_mime_mismatch_blocks_plan(self) -> None:
        manifest = base_manifest()
        manifest["assets"][0]["detected_mime"] = "image/jpeg"
        report = MultimodalRouter(manifest).build_plan()
        self.assertEqual(report["status"], "blocked")
        self.assertIn("mime_mismatch:IMG-1", report["errors"])

    def test_missing_required_modality_is_reported(self) -> None:
        manifest = base_manifest()
        manifest["assets"] = [
            asset for asset in manifest["assets"] if asset["asset_id"] != "AUD-1"
        ]
        report = MultimodalRouter(manifest).build_plan()
        self.assertIn("missing_required_modality:audio", report["errors"])

    def test_budget_is_global(self) -> None:
        manifest = base_manifest()
        manifest["policy"]["budget_units"] = 3
        report = MultimodalRouter(manifest).build_plan()
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(
            any(error.startswith("budget_exceeded:") for error in report["errors"])
        )

    def test_restricted_asset_is_local_only(self) -> None:
        manifest = base_manifest()
        manifest["assets"][0]["privacy"] = "restricted"
        report = MultimodalRouter(manifest).build_plan()
        image = next(
            item for item in report["assets"] if item["asset_id"] == "IMG-1"
        )
        self.assertEqual(image["privacy_action"], "local_only")
        audio = next(
            item for item in report["assets"] if item["asset_id"] == "AUD-1"
        )
        self.assertEqual(audio["privacy_action"], "local_only")

    def test_duplicate_asset_id_is_invalid(self) -> None:
        manifest = base_manifest()
        manifest["assets"].append(deepcopy(manifest["assets"][0]))
        with self.assertRaises(ManifestError):
            MultimodalRouter(manifest)

    def test_utf8_manifest_in_temporary_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "synthetic-manifest.json"
            path.write_text(
                json.dumps(base_manifest(), ensure_ascii=False), encoding="utf-8"
            )
            report = MultimodalRouter(load_manifest(path)).build_plan()
        self.assertEqual(report["status"], "ready")


if __name__ == "__main__":
    unittest.main(verbosity=2)
