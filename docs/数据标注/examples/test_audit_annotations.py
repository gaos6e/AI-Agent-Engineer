"""双人标注一致性审计项目的回归测试。"""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from audit_annotations import (
    AnnotationPair,
    agreement_and_kappa,
    load_batch,
    main,
)


EXAMPLE_DIR = Path(__file__).resolve().parent
SAMPLE_PATH = EXAMPLE_DIR / "sample_annotations.jsonl"


def write_jsonl(path: Path, records: list[object]) -> None:
    path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


def record(
    sample_id: str,
    annotator: str,
    label: str,
    *,
    data_version: str = "v1",
    guideline_version: str = "1.0",
) -> dict[str, str]:
    return {
        "sample_id": sample_id,
        "data_version": data_version,
        "guideline_version": guideline_version,
        "annotator": annotator,
        "label": label,
    }


class AnnotationAuditTests(unittest.TestCase):
    def test_sample_batch_has_fixed_annotators_and_versions(self) -> None:
        batch = load_batch(SAMPLE_PATH)
        self.assertEqual(batch.data_version, "v1")
        self.assertEqual(batch.guideline_version, "1.0")
        self.assertEqual(batch.annotators, ("ann-a", "ann-b"))
        self.assertEqual(len(batch.pairs), 8)

    def test_sample_metrics_match_hand_calculation(self) -> None:
        result = agreement_and_kappa(load_batch(SAMPLE_PATH).pairs)
        self.assertAlmostEqual(result.observed, 0.75)
        self.assertAlmostEqual(result.expected, 22 / 64)
        self.assertIsNotNone(result.kappa)
        self.assertAlmostEqual(result.kappa or 0.0, 13 / 21)

    def test_sample_conflicts_are_auditable(self) -> None:
        result = agreement_and_kappa(load_batch(SAMPLE_PATH).pairs)
        self.assertEqual(
            [pair.sample_id for pair in result.conflicts],
            ["s-003", "s-005"],
        )
        self.assertIn(("unsafe", "not_helpful", 1), result.confusion)
        self.assertIn(("helpful", "not_helpful", 1), result.confusion)

    def test_constant_perfect_agreement_has_undefined_kappa(self) -> None:
        pairs = (
            AnnotationPair("s-1", "helpful", "helpful"),
            AnnotationPair("s-2", "helpful", "helpful"),
        )
        result = agreement_and_kappa(pairs)
        self.assertEqual(result.observed, 1.0)
        self.assertEqual(result.expected, 1.0)
        self.assertIsNone(result.kappa)

    def test_duplicate_annotator_and_missing_pair_are_rejected(self) -> None:
        cases = (
            [record("s-1", "ann-a", "helpful"), record("s-1", "ann-a", "helpful")],
            [record("s-1", "ann-a", "helpful"), record("s-2", "ann-b", "helpful")],
        )
        for records in cases:
            with self.subTest(records=records), TemporaryDirectory() as directory:
                path = Path(directory) / "annotations.jsonl"
                write_jsonl(path, records)
                with self.assertRaises(ValueError):
                    load_batch(path)

    def test_more_than_two_annotators_are_rejected(self) -> None:
        records = [
            record("s-1", "ann-a", "helpful"),
            record("s-1", "ann-b", "helpful"),
            record("s-1", "ann-c", "helpful"),
        ]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "annotations.jsonl"
            write_jsonl(path, records)
            with self.assertRaises(ValueError):
                load_batch(path)

    def test_mixed_versions_and_unknown_labels_are_rejected(self) -> None:
        cases = (
            [record("s-1", "ann-a", "helpful"), record("s-1", "ann-b", "helpful", data_version="v2")],
            [record("s-1", "ann-a", "helpful"), record("s-1", "ann-b", "maybe")],
        )
        for records in cases:
            with self.subTest(records=records), TemporaryDirectory() as directory:
                path = Path(directory) / "annotations.jsonl"
                write_jsonl(path, records)
                with self.assertRaises(ValueError):
                    load_batch(path)

    def test_invalid_json_shape_fields_and_duplicate_keys_are_rejected(self) -> None:
        invalid_lines = (
            "[]\n",
            '{"sample_id":"s-1"}\n',
            '{"sample_id":"s-1","sample_id":"s-2","data_version":"v1","guideline_version":"1.0","annotator":"ann-a","label":"helpful"}\n',
            "\n",
        )
        for content in invalid_lines:
            with self.subTest(content=content), TemporaryDirectory() as directory:
                path = Path(directory) / "annotations.jsonl"
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_batch(path)

    def test_empty_pairs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            agreement_and_kappa(())
        with self.assertRaises(ValueError):
            agreement_and_kappa(
                (AnnotationPair("s-1", "unknown", "helpful"),)
            )
        with self.assertRaises(ValueError):
            agreement_and_kappa(
                (
                    AnnotationPair("s-1", "helpful", "helpful"),
                    AnnotationPair("s-1", "helpful", "helpful"),
                )
            )

    def test_main_returns_success_and_prints_audit_context(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main([str(SAMPLE_PATH)]), 0)
        text = stdout.getvalue()
        self.assertIn("pairs=8 annotators=ann-a,ann-b", text)
        self.assertIn("observed=0.750 expected=0.344 kappa=0.619", text)
        self.assertIn("s-003: unsafe <> not_helpful", text)


if __name__ == "__main__":
    unittest.main()
