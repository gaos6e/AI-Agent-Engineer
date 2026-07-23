"""Tests for the offline image task plan auditor."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from audit_image_plan import validate_plan


FIXTURE = Path(__file__).with_name("image_task_plan.json")


class ImagePlanValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.valid_plan = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_valid_fixture(self) -> None:
        self.assertEqual(validate_plan(copy.deepcopy(self.valid_plan)), [])

    def test_rejects_missing_rights_confirmation(self) -> None:
        plan = copy.deepcopy(self.valid_plan)
        plan["risk"]["rights_confirmed"] = False
        self.assertTrue(any("rights_confirmed" in error for error in validate_plan(plan)))

    def test_rejects_inconsistent_ratio(self) -> None:
        plan = copy.deepcopy(self.valid_plan)
        plan["output"]["width"] = 1000
        self.assertTrue(any("aspect_ratio" in error for error in validate_plan(plan)))

    def test_rejects_missing_acceptance_dimension(self) -> None:
        plan = copy.deepcopy(self.valid_plan)
        plan["acceptance"] = [
            item for item in plan["acceptance"] if item["dimension"] != "safety"
        ]
        self.assertTrue(any("safety" in error for error in validate_plan(plan)))


if __name__ == "__main__":
    unittest.main()
