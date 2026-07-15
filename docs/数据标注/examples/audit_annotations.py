"""审计固定双人名义分类标注的一致率、Cohen's kappa 与冲突。"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Sequence


LABELS = (
    "helpful",
    "not_helpful",
    "unsafe",
    "cannot_judge",
    "exclude",
)
REQUIRED_FIELDS = {
    "sample_id",
    "data_version",
    "guideline_version",
    "annotator",
    "label",
}
OPTIONAL_FIELDS = {"evidence", "created_at"}


@dataclass(frozen=True)
class AnnotationPair:
    sample_id: str
    label_a: str
    label_b: str


@dataclass(frozen=True)
class AnnotationBatch:
    data_version: str
    guideline_version: str
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


def _read_record(line: str, line_number: int) -> dict[str, Any]:
    if not line.strip():
        raise ValueError(f"line {line_number}: blank JSONL record")
    try:
        record = json.loads(
            line,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_non_standard_constant,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"line {line_number}: invalid JSON: {exc}") from exc
    if not isinstance(record, dict):
        raise ValueError(f"line {line_number}: record must be a JSON object")

    missing = sorted(REQUIRED_FIELDS - record.keys())
    if missing:
        raise ValueError(
            f"line {line_number}: missing fields: {','.join(missing)}"
        )
    unknown = sorted(record.keys() - REQUIRED_FIELDS - OPTIONAL_FIELDS)
    if unknown:
        raise ValueError(
            f"line {line_number}: unknown fields: {','.join(unknown)}"
        )
    for field in REQUIRED_FIELDS:
        value = record[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"line {line_number}: {field} must be a non-empty string"
            )
        record[field] = value.strip()
    for field in OPTIONAL_FIELDS & record.keys():
        if not isinstance(record[field], str):
            raise ValueError(
                f"line {line_number}: {field} must be a string when present"
            )
    if record["label"] not in LABELS:
        raise ValueError(
            f"line {line_number}: unsupported label {record['label']!r}"
        )
    return record


def load_batch(path: Path) -> AnnotationBatch:
    """加载严格 JSONL，并要求整批恰有两名固定标注者和统一版本。"""

    if not path.is_file():
        raise ValueError("annotation path must be an existing file")

    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    annotators: set[str] = set()
    data_versions: set[str] = set()
    guideline_versions: set[str] = set()
    with path.open("r", encoding="utf-8-sig") as source:
        for line_number, line in enumerate(source, start=1):
            record = _read_record(line, line_number)
            sample_id = record["sample_id"]
            annotator = record["annotator"]
            if annotator in grouped[sample_id]:
                raise ValueError(
                    f"line {line_number}: duplicate annotation for "
                    f"{sample_id!r} by {annotator!r}"
                )
            grouped[sample_id][annotator] = record["label"]
            annotators.add(annotator)
            data_versions.add(record["data_version"])
            guideline_versions.add(record["guideline_version"])

    if not grouped:
        raise ValueError("annotation file contains no records")
    if len(annotators) != 2:
        raise ValueError(
            f"batch must contain exactly two annotators, found {len(annotators)}"
        )
    if len(data_versions) != 1:
        raise ValueError("batch mixes multiple data_version values")
    if len(guideline_versions) != 1:
        raise ValueError("batch mixes multiple guideline_version values")

    ordered_annotators = tuple(sorted(annotators))
    annotator_a, annotator_b = ordered_annotators
    pairs: list[AnnotationPair] = []
    for sample_id, annotations in sorted(grouped.items()):
        if set(annotations) != annotators:
            missing = sorted(annotators - set(annotations))
            raise ValueError(
                f"{sample_id}: missing annotations from {','.join(missing)}"
            )
        pairs.append(
            AnnotationPair(
                sample_id=sample_id,
                label_a=annotations[annotator_a],
                label_b=annotations[annotator_b],
            )
        )
    return AnnotationBatch(
        data_version=next(iter(data_versions)),
        guideline_version=next(iter(guideline_versions)),
        annotators=(annotator_a, annotator_b),
        pairs=tuple(pairs),
    )


def agreement_and_kappa(
    pairs: Sequence[AnnotationPair],
) -> AgreementResult:
    """计算名义标签的一致率、期望一致率、kappa 和混淆计数。"""

    if not pairs:
        raise ValueError("no annotation pairs")
    seen_samples: set[str] = set()
    for pair in pairs:
        if not pair.sample_id or pair.sample_id in seen_samples:
            raise ValueError("pairs must contain unique non-empty sample_id values")
        if pair.label_a not in LABELS or pair.label_b not in LABELS:
            raise ValueError("pair contains an unsupported label")
        seen_samples.add(pair.sample_id)
    labels_a = Counter(pair.label_a for pair in pairs)
    labels_b = Counter(pair.label_b for pair in pairs)
    labels = set(labels_a) | set(labels_b)
    count = len(pairs)
    observed = sum(
        pair.label_a == pair.label_b
        for pair in pairs
    ) / count
    expected = sum(
        (labels_a[label] / count) * (labels_b[label] / count)
        for label in labels
    )
    denominator = 1.0 - expected
    kappa = None if abs(denominator) < 1e-15 else (
        observed - expected
    ) / denominator

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
    conflicts = tuple(
        pair
        for pair in pairs
        if pair.label_a != pair.label_b
    )
    return AgreementResult(
        observed=observed,
        expected=expected,
        kappa=kappa,
        confusion=confusion,
        conflicts=conflicts,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="审计恰好两名标注者的名义分类 JSONL",
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
        f"guideline_version={batch.guideline_version}"
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
        print(f"- {pair.sample_id}: {pair.label_a} <> {pair.label_b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
