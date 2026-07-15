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

from audit_ocr_fixture import (
    FixtureError,
    audit,
    edit_distance,
    error_rate,
    load_fixture,
    validate_fixture,
)


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "audit_ocr_fixture.py"
FIXTURE = HERE / "ocr_fixture.json"


def valid_payload() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TemporaryFileCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="ocr-test-", dir=HERE)
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "fixture.json"

    def write_text(self, text: str) -> Path:
        self.path.write_text(text, encoding="utf-8")
        return self.path

    def write_payload(self, payload: object) -> Path:
        return self.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False))


class StrictJsonTests(TemporaryFileCase):
    def test_loads_valid_fixture(self) -> None:
        self.assertEqual(load_fixture(FIXTURE)["document_id"], "synthetic-invoice-001")

    def test_rejects_duplicate_key(self) -> None:
        path = self.write_text(
            '{"schema_version":"1.0","schema_version":"1.0",'
            '"document_id":"x","review_threshold":0.9,"pages":[]}'
        )
        with self.assertRaisesRegex(FixtureError, "duplicate JSON key"):
            load_fixture(path)

    def test_rejects_nan(self) -> None:
        path = self.write_text(
            '{"schema_version":"1.0","document_id":"x",'
            '"review_threshold":NaN,"pages":[]}'
        )
        with self.assertRaisesRegex(FixtureError, "non-finite"):
            load_fixture(path)

    def test_rejects_infinity(self) -> None:
        path = self.write_text(
            '{"schema_version":"1.0","document_id":"x",'
            '"review_threshold":Infinity,"pages":[]}'
        )
        with self.assertRaisesRegex(FixtureError, "non-finite"):
            load_fixture(path)

    def test_rejects_malformed_json(self) -> None:
        with self.assertRaisesRegex(FixtureError, "invalid JSON"):
            load_fixture(self.write_text("{"))

    def test_rejects_missing_file(self) -> None:
        with self.assertRaisesRegex(FixtureError, "cannot read fixture"):
            load_fixture(self.path)

    def test_rejects_invalid_utf8(self) -> None:
        self.path.write_bytes(b"\xff\xfe")
        with self.assertRaisesRegex(FixtureError, "cannot read fixture"):
            load_fixture(self.path)

    def test_rejects_non_object_root(self) -> None:
        with self.assertRaisesRegex(FixtureError, "fixture must be an object"):
            load_fixture(self.write_text("[]"))


class TopLevelContractTests(unittest.TestCase):
    def assert_invalid(self, payload: object, pattern: str) -> None:
        with self.assertRaisesRegex(FixtureError, pattern):
            validate_fixture(payload)

    def test_accepts_valid_payload(self) -> None:
        self.assertIs(validate_fixture(valid_payload())["pages"].__class__, list)

    def test_missing_field(self) -> None:
        payload = valid_payload()
        del payload["document_id"]
        self.assert_invalid(payload, "missing fields")

    def test_unknown_field(self) -> None:
        payload = valid_payload()
        payload["surprise"] = True
        self.assert_invalid(payload, "unknown fields")

    def test_wrong_schema_version(self) -> None:
        payload = valid_payload()
        payload["schema_version"] = "2.0"
        self.assert_invalid(payload, "schema_version")

    def test_empty_document_id(self) -> None:
        payload = valid_payload()
        payload["document_id"] = "  "
        self.assert_invalid(payload, "document_id")

    def test_non_string_document_id(self) -> None:
        payload = valid_payload()
        payload["document_id"] = 7
        self.assert_invalid(payload, "document_id")

    def test_boolean_threshold(self) -> None:
        payload = valid_payload()
        payload["review_threshold"] = True
        self.assert_invalid(payload, "review_threshold")

    def test_threshold_below_zero(self) -> None:
        payload = valid_payload()
        payload["review_threshold"] = -0.01
        self.assert_invalid(payload, "review_threshold")

    def test_threshold_above_one(self) -> None:
        payload = valid_payload()
        payload["review_threshold"] = 1.01
        self.assert_invalid(payload, "review_threshold")

    def test_direct_nan_threshold(self) -> None:
        payload = valid_payload()
        payload["review_threshold"] = float("nan")
        self.assert_invalid(payload, "review_threshold")

    def test_pages_must_be_array(self) -> None:
        payload = valid_payload()
        payload["pages"] = {}
        self.assert_invalid(payload, "pages must be")

    def test_pages_must_not_be_empty(self) -> None:
        payload = valid_payload()
        payload["pages"] = []
        self.assert_invalid(payload, "non-empty")


class PageContractTests(unittest.TestCase):
    def assert_invalid(self, payload: object, pattern: str) -> None:
        with self.assertRaisesRegex(FixtureError, pattern):
            validate_fixture(payload)

    def test_page_missing_field(self) -> None:
        payload = valid_payload()
        del payload["pages"][0]["width"]
        self.assert_invalid(payload, "missing fields")

    def test_page_unknown_field(self) -> None:
        payload = valid_payload()
        payload["pages"][0]["rotation"] = 0
        self.assert_invalid(payload, "unknown fields")

    def test_page_number_rejects_boolean(self) -> None:
        payload = valid_payload()
        payload["pages"][0]["page"] = True
        self.assert_invalid(payload, "positive integer")

    def test_page_number_rejects_zero(self) -> None:
        payload = valid_payload()
        payload["pages"][0]["page"] = 0
        self.assert_invalid(payload, "positive integer")

    def test_width_rejects_zero(self) -> None:
        payload = valid_payload()
        payload["pages"][0]["width"] = 0
        self.assert_invalid(payload, "width and height")

    def test_height_rejects_float(self) -> None:
        payload = valid_payload()
        payload["pages"][0]["height"] = 2.5
        self.assert_invalid(payload, "width and height")

    def test_blocks_must_be_array(self) -> None:
        payload = valid_payload()
        payload["pages"][0]["blocks"] = {}
        self.assert_invalid(payload, "blocks must be an array")

    def test_duplicate_page_number(self) -> None:
        payload = valid_payload()
        payload["pages"].append(copy.deepcopy(payload["pages"][0]))
        self.assert_invalid(payload, "page numbers must be unique")

    def test_pages_must_be_ordered(self) -> None:
        payload = valid_payload()
        second = copy.deepcopy(payload["pages"][0])
        second["page"] = 2
        payload["pages"] = [second, payload["pages"][0]]
        self.assert_invalid(payload, "pages must be ordered")


class BlockContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = valid_payload()

    @property
    def block(self) -> dict[str, object]:
        return self.payload["pages"][0]["blocks"][0]

    def assert_invalid(self, pattern: str) -> None:
        with self.assertRaisesRegex(FixtureError, pattern):
            validate_fixture(self.payload)

    def test_block_must_be_object(self) -> None:
        self.payload["pages"][0]["blocks"][0] = []
        self.assert_invalid("must be an object")

    def test_block_missing_field(self) -> None:
        del self.block["bbox"]
        self.assert_invalid("missing fields")

    def test_block_unknown_field(self) -> None:
        self.block["language"] = "zh"
        self.assert_invalid("unknown fields")

    def test_empty_block_id(self) -> None:
        self.block["block_id"] = ""
        self.assert_invalid("block_id")

    def test_unknown_block_type(self) -> None:
        self.block["type"] = "figure"
        self.assert_invalid("type must be")

    def test_bbox_must_be_array(self) -> None:
        self.block["bbox"] = "0,0,1,1"
        self.assert_invalid("four finite numbers")

    def test_bbox_must_have_four_values(self) -> None:
        self.block["bbox"] = [0, 0, 1]
        self.assert_invalid("four finite numbers")

    def test_bbox_rejects_boolean(self) -> None:
        self.block["bbox"] = [True, 0, 1, 1]
        self.assert_invalid("four finite numbers")

    def test_bbox_rejects_non_finite_value(self) -> None:
        self.block["bbox"] = [0, 0, float("inf"), 1]
        self.assert_invalid("four finite numbers")

    def test_bbox_requires_positive_area(self) -> None:
        self.block["bbox"] = [2, 0, 1, 1]
        self.assert_invalid("inside the page")

    def test_bbox_must_stay_inside_page(self) -> None:
        self.block["bbox"] = [0, 0, 1001, 1]
        self.assert_invalid("inside the page")

    def test_order_rejects_boolean(self) -> None:
        self.block["order"] = True
        self.assert_invalid("positive integer")

    def test_order_rejects_zero(self) -> None:
        self.block["order"] = 0
        self.assert_invalid("positive integer")

    def test_reference_text_must_be_string(self) -> None:
        self.block["reference_text"] = None
        self.assert_invalid("reference_text")

    def test_predicted_text_must_be_string(self) -> None:
        self.block["predicted_text"] = 1
        self.assert_invalid("predicted_text")

    def test_confidence_rejects_boolean(self) -> None:
        self.block["confidence"] = False
        self.assert_invalid("confidence")

    def test_confidence_rejects_out_of_range(self) -> None:
        self.block["confidence"] = 1.1
        self.assert_invalid("confidence")

    def test_critical_must_be_boolean(self) -> None:
        self.block["critical"] = 1
        self.assert_invalid("critical")

    def test_table_block_requires_table(self) -> None:
        self.block["type"] = "table"
        self.assert_invalid("missing fields")

    def test_non_table_rejects_table(self) -> None:
        self.block["table"] = {
            "reference_shape": [1, 1],
            "predicted_shape": [1, 1],
        }
        self.assert_invalid("only valid for table")

    def test_table_rejects_unknown_field(self) -> None:
        table = self.payload["pages"][0]["blocks"][2]["table"]
        table["cells"] = []
        self.assert_invalid("unknown fields")

    def test_table_shape_requires_two_positive_ints(self) -> None:
        table = self.payload["pages"][0]["blocks"][2]["table"]
        table["reference_shape"] = [2, 0]
        self.assert_invalid("positive_rows")


class MetricAndAuditTests(unittest.TestCase):
    def test_edit_distance_identity(self) -> None:
        self.assertEqual(edit_distance(list("abc"), list("abc")), 0)

    def test_edit_distance_substitution_and_insertion(self) -> None:
        self.assertEqual(edit_distance(list("ABC"), list("ADCX")), 2)

    def test_edit_distance_deletion(self) -> None:
        self.assertEqual(edit_distance(list("abcd"), list("acd")), 1)

    def test_empty_reference_and_hypothesis(self) -> None:
        self.assertEqual(error_rate([], []), 0.0)

    def test_empty_reference_with_hypothesis(self) -> None:
        self.assertEqual(error_rate([], ["extra"]), 1.0)

    def test_error_rate_can_exceed_one(self) -> None:
        self.assertEqual(error_rate(["a"], ["a", "b", "c"]), 2.0)

    def test_fixture_report_is_successful(self) -> None:
        report = audit(valid_payload())
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["order_valid"])
        self.assertTrue(report["table_structure_match"])
        self.assertEqual(report["block_count"], 3)

    def test_low_confidence_enters_review(self) -> None:
        report = audit(valid_payload())
        review = next(item for item in report["review_queue"] if item["block_id"] == "p1-number")
        self.assertIn("low_confidence", review["reasons"])

    def test_critical_mismatch_enters_review(self) -> None:
        report = audit(valid_payload())
        review = next(item for item in report["review_queue"] if item["block_id"] == "p1-number")
        self.assertIn("critical_text_mismatch", review["reasons"])

    def test_duplicate_block_id_is_audit_error(self) -> None:
        payload = valid_payload()
        payload["pages"][0]["blocks"][1]["block_id"] = "p1-title"
        self.assertIn("duplicate block_id", " ".join(audit(payload)["errors"]))

    def test_duplicate_order_is_audit_error(self) -> None:
        payload = valid_payload()
        payload["pages"][0]["blocks"][1]["order"] = 1
        report = audit(payload)
        self.assertFalse(report["order_valid"])
        self.assertIn("order must be unique", " ".join(report["errors"]))

    def test_decreasing_order_is_audit_error(self) -> None:
        payload = valid_payload()
        payload["pages"][0]["blocks"][0]["order"] = 2
        payload["pages"][0]["blocks"][1]["order"] = 1
        self.assertFalse(audit(payload)["order_valid"])

    def test_table_shape_mismatch_enters_one_review(self) -> None:
        payload = valid_payload()
        payload["pages"][0]["blocks"][2]["table"]["predicted_shape"] = [3, 2]
        report = audit(payload)
        self.assertFalse(report["table_structure_match"])
        reviews = [item for item in report["review_queue"] if item["block_id"] == "p1-table"]
        self.assertEqual(len(reviews), 1)
        self.assertIn("table_shape_mismatch", reviews[0]["reasons"])

    def test_no_table_yields_null_table_metric(self) -> None:
        payload = valid_payload()
        payload["pages"][0]["blocks"] = payload["pages"][0]["blocks"][:2]
        self.assertIsNone(audit(payload)["table_structure_match"])

    def test_audit_revalidates_direct_input(self) -> None:
        payload = valid_payload()
        payload["review_threshold"] = True
        with self.assertRaises(FixtureError):
            audit(payload)


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

    def test_valid_fixture_exit_zero(self) -> None:
        result = self.run_cli(str(FIXTURE))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["errors"], [])

    def test_audit_finding_exit_one(self) -> None:
        payload = valid_payload()
        payload["pages"][0]["blocks"][1]["order"] = 1
        result = self.run_cli(str(self.write_payload(payload)))
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_contract_error_exit_two(self) -> None:
        payload = valid_payload()
        payload["extra"] = True
        result = self.run_cli(str(self.write_payload(payload)))
        self.assertEqual(result.returncode, 2)
        self.assertIn("fixture error", result.stderr)

    def test_missing_file_exit_two(self) -> None:
        result = self.run_cli(str(self.path))
        self.assertEqual(result.returncode, 2)

    def test_missing_argument_exit_two(self) -> None:
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)

    def test_self_test_exit_zero(self) -> None:
        result = self.run_cli("--self-test")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_production_code_has_no_assert_statement(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))


if __name__ == "__main__":
    unittest.main()
