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
    annotation_id: str | None = None,
    source_revision: str | None = None,
    data_version: str = "v1",
    guideline_version: str = "1.0",
    label_set_version: str = "1.0",
    task_config_version: str = "agent-answer-v1",
    evidence: str = "fixture evidence",
    created_at: str = "2026-07-22T00:00:00Z",
) -> dict[str, str]:
    return {
        "annotation_id": annotation_id or f"a-{sample_id}-{annotator}",
        "sample_id": sample_id,
        "source_revision": source_revision or f"demo-{sample_id}-r1",
        "data_version": data_version,
        "guideline_version": guideline_version,
        "label_set_version": label_set_version,
        "task_config_version": task_config_version,
        "annotator": annotator,
        "label": label,
        "evidence": evidence,
        "created_at": created_at,
    }


class AnnotationAuditTests(unittest.TestCase):
    def test_sample_batch_has_fixed_annotators_and_contract_versions(self) -> None:
        batch = load_batch(SAMPLE_PATH)
        self.assertEqual(batch.data_version, "v1")
        self.assertEqual(batch.guideline_version, "1.0")
        self.assertEqual(batch.label_set_version, "1.0")
        self.assertEqual(batch.task_config_version, "agent-answer-v1")
        self.assertEqual(batch.annotators, ("ann-a", "ann-b"))
        self.assertEqual(len(batch.pairs), 8)
        self.assertEqual(batch.pairs[0].source_revision, "demo-s-001-r1")

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
        self.assertEqual(result.conflicts[0].source_revision, "demo-s-003-r1")
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
            [
                record("s-1", "ann-a", "helpful"),
                record(
                    "s-1",
                    "ann-a",
                    "helpful",
                    annotation_id="a-s-1-ann-a-again",
                ),
            ],
            [
                record("s-1", "ann-a", "helpful"),
                record("s-2", "ann-b", "helpful"),
            ],
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

    def test_mixed_contract_versions_and_unknown_labels_are_rejected(self) -> None:
        cases = (
            [
                record("s-1", "ann-a", "helpful"),
                record("s-1", "ann-b", "helpful", data_version="v2"),
            ],
            [
                record("s-1", "ann-a", "helpful"),
                record("s-1", "ann-b", "helpful", label_set_version="2.0"),
            ],
            [
                record("s-1", "ann-a", "helpful"),
                record(
                    "s-1",
                    "ann-b",
                    "helpful",
                    task_config_version="agent-answer-v2",
                ),
            ],
            [
                record("s-1", "ann-a", "helpful"),
                record("s-1", "ann-b", "maybe"),
            ],
        )
        for records in cases:
            with self.subTest(records=records), TemporaryDirectory() as directory:
                path = Path(directory) / "annotations.jsonl"
                write_jsonl(path, records)
                with self.assertRaises(ValueError):
                    load_batch(path)

    def test_traceability_fields_and_source_revision_are_checked(self) -> None:
        missing_source = record("s-1", "ann-a", "helpful")
        del missing_source["source_revision"]
        duplicate_id = [
            record("s-1", "ann-a", "helpful", annotation_id="same-id"),
            record("s-1", "ann-b", "helpful", annotation_id="same-id"),
        ]
        source_mismatch = [
            record("s-1", "ann-a", "helpful", source_revision="r1"),
            record("s-1", "ann-b", "helpful", source_revision="r2"),
        ]
        cases = ([missing_source], duplicate_id, source_mismatch)
        for records in cases:
            with self.subTest(records=records), TemporaryDirectory() as directory:
                path = Path(directory) / "annotations.jsonl"
                write_jsonl(path, records)
                with self.assertRaises(ValueError):
                    load_batch(path)

    def test_evidence_timestamp_and_unknown_fields_are_rejected(self) -> None:
        empty_evidence = record("s-1", "ann-a", "helpful", evidence=" ")
        invalid_timestamp = record(
            "s-1",
            "ann-a",
            "helpful",
            created_at="2026-07-22T08:00:00+08:00",
        )
        unknown_field = record("s-1", "ann-a", "helpful")
        unknown_field["model_suggestion"] = "helpful"
        cases = ([empty_evidence], [invalid_timestamp], [unknown_field])
        for records in cases:
            with self.subTest(records=records), TemporaryDirectory() as directory:
                path = Path(directory) / "annotations.jsonl"
                write_jsonl(path, records)
                with self.assertRaises(ValueError):
                    load_batch(path)

    def test_invalid_json_shape_constants_and_duplicate_keys_are_rejected(self) -> None:
        invalid_lines = (
            "[]\n",
            '{"sample_id":"s-1"}\n',
            '{"sample_id":"s-1","sample_id":"s-2"}\n',
            '{"score":NaN}\n',
            '{"score":Infinity}\n',
            "\n",
        )
        for content in invalid_lines:
            with self.subTest(content=content), TemporaryDirectory() as directory:
                path = Path(directory) / "annotations.jsonl"
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_batch(path)

    def test_empty_pairs_and_missing_pair_source_revision_are_rejected(self) -> None:
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
        with self.assertRaises(ValueError):
            agreement_and_kappa(
                (AnnotationPair("s-1", "helpful", "helpful", ""),)
            )

    def test_main_returns_success_and_prints_audit_context(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main([str(SAMPLE_PATH)]), 0)
        text = stdout.getvalue()
        self.assertIn("pairs=8 annotators=ann-a,ann-b", text)
        self.assertIn("label_set_version=1.0", text)
        self.assertIn("task_config_version=agent-answer-v1", text)
        self.assertIn("observed=0.750 expected=0.344 kappa=0.619", text)
        self.assertIn("s-003 (demo-s-003-r1): unsafe <> not_helpful", text)


if __name__ == "__main__":
    unittest.main()
