"""Audit agreement, Cohen's kappa, and conflicts in fixed two-annotator nominal labels.

This offline teaching contract checker audits a batch of initial-annotation
records already assigned to two annotators. It does not replace adjudication,
gold review, sampling-representativeness, or privacy and licensing review.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any, Sequence


LABELS = (
    "helpful",
    "not_helpful",
    "unsafe",
    "cannot_judge",
    "exclude",
)
REQUIRED_FIELDS = {
    "annotation_id",
    "sample_id",
    "source_revision",
    "data_version",
    "guideline_version",
    "label_set_version",
    "task_config_version",
    "annotator",
    "label",
    "evidence",
    "created_at",
}
UTC_SECOND_TIMESTAMP = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)


@dataclass(frozen=True)
class AnnotationPair:
    sample_id: str
    label_a: str
    label_b: str
    source_revision: str = "manual"


@dataclass(frozen=True)
class AnnotationBatch:
    data_version: str
    guideline_version: str
    label_set_version: str
    task_config_version: str
    annotators: tuple[str, str]
    pairs: tuple[AnnotationPair, ...]


@dataclass(frozen=True)
class AgreementResult:
    observed: float
    expected: float
    kappa: float | None
    confusion: tuple[tuple[str, str, int], ...]
    conflicts: tuple[AnnotationPair, ...]


def _object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    record: dict[str, Any] = {}
    for key, value in pairs:
        if key in record:
            raise ValueError(f"duplicate JSON key: {key}")
        record[key] = value
    return record


def _reject_non_standard_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _validate_timestamp(value: str, line_number: int) -> None:
    """Accept only the UTC, second-level time format declared by this teaching contract."""

    if not UTC_SECOND_TIMESTAMP.fullmatch(value):
        raise ValueError(
            f"line {line_number}: created_at must use YYYY-MM-DDTHH:MM:SSZ"
        )
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError(
            f"line {line_number}: created_at is not a calendar timestamp"
        ) from exc


def _read_record(line: str, line_number: int) -> dict[str, str]:
    if not line.strip():
        raise ValueError(f"line {line_number}: blank JSONL record")
    try:
        parsed = json.loads(
            line,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_non_standard_constant,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"line {line_number}: invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"line {line_number}: record must be a JSON object")

    missing = sorted(REQUIRED_FIELDS - parsed.keys())
    if missing:
        raise ValueError(
            f"line {line_number}: missing fields: {','.join(missing)}"
        )
    unknown = sorted(parsed.keys() - REQUIRED_FIELDS)
    if unknown:
        raise ValueError(
            f"line {line_number}: unknown fields: {','.join(unknown)}"
        )

    record: dict[str, str] = {}
    for field in REQUIRED_FIELDS:
        value = parsed[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"line {line_number}: {field} must be a non-empty string"
            )
        record[field] = value.strip()
    if record["label"] not in LABELS:
        raise ValueError(
            f"line {line_number}: unsupported label {record['label']!r}"
        )
    _validate_timestamp(record["created_at"], line_number)
    return record


def _single_batch_value(values: set[str], field: str) -> str:
    if len(values) != 1:
        raise ValueError(f"batch mixes multiple {field} values")
    return next(iter(values))


def load_batch(path: Path) -> AnnotationBatch:
    """Load strict JSONL requiring two fixed annotators, one contract version, and one input snapshot."""

    if not path.is_file():
        raise ValueError("annotation path must be an existing file")

    grouped: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    annotation_ids: set[str] = set()
    annotators: set[str] = set()
    data_versions: set[str] = set()
    guideline_versions: set[str] = set()
    label_set_versions: set[str] = set()
    task_config_versions: set[str] = set()
    with path.open("r", encoding="utf-8-sig") as source:
        for line_number, line in enumerate(source, start=1):
            record = _read_record(line, line_number)
            annotation_id = record["annotation_id"]
            if annotation_id in annotation_ids:
                raise ValueError(
                    f"line {line_number}: duplicate annotation_id {annotation_id!r}"
                )
            annotation_ids.add(annotation_id)

            sample_id = record["sample_id"]
            annotator = record["annotator"]
            if annotator in grouped[sample_id]:
                raise ValueError(
                    f"line {line_number}: duplicate annotation for "
                    f"{sample_id!r} by {annotator!r}"
                )
            grouped[sample_id][annotator] = record
            annotators.add(annotator)
            data_versions.add(record["data_version"])
            guideline_versions.add(record["guideline_version"])
            label_set_versions.add(record["label_set_version"])
            task_config_versions.add(record["task_config_version"])

    if not grouped:
        raise ValueError("annotation file contains no records")
    if len(annotators) != 2:
        raise ValueError(
            f"batch must contain exactly two annotators, found {len(annotators)}"
        )

    ordered_annotators = tuple(sorted(annotators))
    annotator_a, annotator_b = ordered_annotators
    pairs: list[AnnotationPair] = []
    for sample_id, annotations in sorted(grouped.items()):
        if set(annotations) != annotators:
            missing = sorted(annotators - set(annotations))
            raise ValueError(
                f"{sample_id}: missing annotations from {','.join(missing)}"
            )
        source_revisions = {
            record["source_revision"] for record in annotations.values()
        }
        if len(source_revisions) != 1:
            raise ValueError(
                f"{sample_id}: annotators did not use the same source_revision"
            )
        pairs.append(
            AnnotationPair(
                sample_id=sample_id,
                label_a=annotations[annotator_a]["label"],
                label_b=annotations[annotator_b]["label"],
                source_revision=next(iter(source_revisions)),
            )
        )

    return AnnotationBatch(
        data_version=_single_batch_value(data_versions, "data_version"),
        guideline_version=_single_batch_value(
            guideline_versions, "guideline_version"
        ),
        label_set_version=_single_batch_value(
            label_set_versions, "label_set_version"
        ),
        task_config_version=_single_batch_value(
            task_config_versions, "task_config_version"
        ),
        annotators=(annotator_a, annotator_b),
        pairs=tuple(pairs),
    )


def agreement_and_kappa(
    pairs: Sequence[AnnotationPair],
) -> AgreementResult:
    """Calculate nominal-label observed agreement, expected agreement, kappa, and confusion counts."""

    if not pairs:
        raise ValueError("no annotation pairs")
    seen_samples: set[str] = set()
    for pair in pairs:
        if (
            not pair.sample_id
            or not pair.source_revision
            or pair.sample_id in seen_samples
        ):
            raise ValueError(
                "pairs must contain unique non-empty sample_id and source_revision"
            )
        if pair.label_a not in LABELS or pair.label_b not in LABELS:
            raise ValueError("pair contains an unsupported label")
        seen_samples.add(pair.sample_id)
    labels_a = Counter(pair.label_a for pair in pairs)
    labels_b = Counter(pair.label_b for pair in pairs)
    labels = set(labels_a) | set(labels_b)
    count = len(pairs)
    observed = sum(pair.label_a == pair.label_b for pair in pairs) / count
    expected = sum(
        (labels_a[label] / count) * (labels_b[label] / count)
        for label in labels
    )
    denominator = 1.0 - expected
    kappa = (
        None
        if abs(denominator) < 1e-15
        else (observed - expected) / denominator
    )

    confusion_counter = Counter(
        (pair.label_a, pair.label_b)
        for pair in pairs
    )
    confusion = tuple(
        (label_a, label_b, confusion_counter[(label_a, label_b)])
        for label_a in LABELS
        for label_b in LABELS
        if confusion_counter[(label_a, label_b)]
    )
    conflicts = tuple(pair for pair in pairs if pair.label_a != pair.label_b)
    return AgreementResult(
        observed=observed,
        expected=expected,
        kappa=kappa,
        confusion=confusion,
        conflicts=conflicts,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit nominal-label JSONL from exactly two annotators",
    )
    parser.add_argument("path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    batch = load_batch(args.path)
    result = agreement_and_kappa(batch.pairs)
    annotator_a, annotator_b = batch.annotators
    kappa_text = "undefined" if result.kappa is None else f"{result.kappa:.3f}"
    print(
        f"pairs={len(batch.pairs)} annotators={annotator_a},{annotator_b} "
        f"data_version={batch.data_version} "
        f"guideline_version={batch.guideline_version} "
        f"label_set_version={batch.label_set_version} "
        f"task_config_version={batch.task_config_version}"
    )
    print(
        f"observed={result.observed:.3f} "
        f"expected={result.expected:.3f} kappa={kappa_text}"
    )
    print(f"confusion rows={annotator_a} columns={annotator_b}:")
    for label_a, label_b, count in result.confusion:
        print(f"- {label_a} -> {label_b}: {count}")
    print("conflicts:")
    if not result.conflicts:
        print("- none")
    for pair in result.conflicts:
        print(
            f"- {pair.sample_id} ({pair.source_revision}): "
            f"{pair.label_a} <> {pair.label_b}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
