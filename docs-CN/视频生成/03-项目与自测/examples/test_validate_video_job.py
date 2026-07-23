"""Tests for the offline video generation job package validator."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from validate_video_job import validate_package


FIXTURE = Path(__file__).with_name("video_job_package.json")


class VideoPackageValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.valid_package = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_valid_fixture(self) -> None:
        self.assertEqual(validate_package(copy.deepcopy(self.valid_package)), [])

    def test_rejects_overlapping_shots(self) -> None:
        package = copy.deepcopy(self.valid_package)
        package["shots"][1]["start_seconds"] = 2.0
        self.assertTrue(any("重叠" in error for error in validate_package(package)))

    def test_rejects_caption_outside_duration(self) -> None:
        package = copy.deepcopy(self.valid_package)
        package["captions"]["cues"][1]["end_seconds"] = 9.0
        self.assertTrue(any("字幕" in error or "cues" in error for error in validate_package(package)))

    def test_rejects_missing_continuity_anchors(self) -> None:
        package = copy.deepcopy(self.valid_package)
        package["shots"][0]["continuity_anchors"] = []
        self.assertTrue(any("continuity_anchors" in error for error in validate_package(package)))

    def test_rejects_disabled_human_review(self) -> None:
        package = copy.deepcopy(self.valid_package)
        package["risk"]["human_review_required"] = False
        self.assertTrue(any("human_review_required" in error for error in validate_package(package)))


if __name__ == "__main__":
    unittest.main()

