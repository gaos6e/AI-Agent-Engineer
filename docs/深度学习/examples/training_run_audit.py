"""Validate a small, offline training-run record before treating it as evidence.

This is a teaching guardrail, not a model trainer or a production governance system.
It intentionally validates only the metadata supplied by its caller; it cannot prove
that a data revision exists, is authorized, or is representative of production.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any


class TrainingRunContractError(ValueError):
    """Raised when a teaching training-run record violates an evidence boundary."""


MUTABLE_ALIASES = {"current", "head", "latest", "main", "production"}
REQUIRED_LINEAGE_FIELDS = (
    "source_revision",
    "transform_id",
    "split_id",
    "candidate_id",
)
SPLIT_NAMES = ("train", "validation", "test")


SAMPLE_RUN: dict[str, Any] = {
    "source_revision": "support-intents-r2",
    "transform_id": "redact-and-tokenize-v3",
    "split_id": "group-holdout-2026-07-22",
    "candidate_id": "intent-router-candidate-2026-07-22.1",
    "splits": {
        "train": ["ticket-001", "ticket-002", "ticket-003"],
        "validation": ["ticket-004"],
        "test": ["ticket-005", "ticket-006"],
    },
    "selection": {
        "checkpoint_id": "epoch-4",
        "metric": "macro_f1",
        "used_split": "validation",
    },
    "test_report": {
        "evaluated_after_selection": True,
        "metrics": {"macro_f1": 0.78},
        "slice_metrics": {"billing": {"macro_f1": 0.75}},
    },
}


def _require_stable_identifier(record: Mapping[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TrainingRunContractError(f"{key} must be a non-empty string")
    if value.strip().lower() in MUTABLE_ALIASES:
        raise TrainingRunContractError(f"{key} must not use a mutable alias: {value!r}")
    return value


def _require_ids(splits: Mapping[str, Any], name: str) -> set[str]:
    values = splits.get(name)
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or not values:
        raise TrainingRunContractError(f"splits.{name} must be a non-empty list of IDs")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise TrainingRunContractError(f"splits.{name} contains an invalid sample ID")
    identifiers = set(values)
    if len(identifiers) != len(values):
        raise TrainingRunContractError(f"splits.{name} contains duplicate sample IDs")
    return identifiers


def _validate_finite_metric(value: Any, path: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TrainingRunContractError(f"{path} must be a finite numeric metric")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise TrainingRunContractError(f"{path} must be a finite numeric metric")


def validate_training_run(record: Mapping[str, Any]) -> None:
    """Validate explicit leakage and evidence-boundary checks for a demo record."""

    if not isinstance(record, Mapping):
        raise TrainingRunContractError("training run must be an object")

    for field in REQUIRED_LINEAGE_FIELDS:
        _require_stable_identifier(record, field)

    splits = record.get("splits")
    if not isinstance(splits, Mapping):
        raise TrainingRunContractError("splits must be an object")
    split_ids = {name: _require_ids(splits, name) for name in SPLIT_NAMES}
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        overlap = split_ids[left] & split_ids[right]
        if overlap:
            raise TrainingRunContractError(
                f"splits.{left} and splits.{right} overlap: {sorted(overlap)!r}"
            )

    selection = record.get("selection")
    if not isinstance(selection, Mapping):
        raise TrainingRunContractError("selection must be an object")
    if selection.get("used_split") != "validation":
        raise TrainingRunContractError("selection.used_split must be 'validation', never 'test'")
    for field in ("checkpoint_id", "metric"):
        _require_stable_identifier(selection, field)

    report = record.get("test_report")
    if not isinstance(report, Mapping):
        raise TrainingRunContractError("test_report must be an object")
    if report.get("evaluated_after_selection") is not True:
        raise TrainingRunContractError("test_report must be recorded after checkpoint selection")
    metrics = report.get("metrics")
    if not isinstance(metrics, Mapping) or not metrics:
        raise TrainingRunContractError("test_report.metrics must be a non-empty object")
    for name, value in metrics.items():
        _validate_finite_metric(value, f"test_report.metrics.{name}")

    slice_metrics = report.get("slice_metrics")
    if not isinstance(slice_metrics, Mapping) or not slice_metrics:
        raise TrainingRunContractError("test_report.slice_metrics must be a non-empty object")
    for slice_name, slice_report in slice_metrics.items():
        if not isinstance(slice_name, str) or not slice_name.strip() or not isinstance(slice_report, Mapping):
            raise TrainingRunContractError("test_report.slice_metrics must map names to metric objects")
        for name, value in slice_report.items():
            _validate_finite_metric(value, f"test_report.slice_metrics.{slice_name}.{name}")


def evidence_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return a minimal, non-sensitive summary only after the contract validates."""

    validate_training_run(record)
    splits = record["splits"]
    return {
        "source_revision": record["source_revision"],
        "transform_id": record["transform_id"],
        "split_id": record["split_id"],
        "candidate_id": record["candidate_id"],
        "split_sizes": {name: len(splits[name]) for name in SPLIT_NAMES},
        "selection_split": record["selection"]["used_split"],
        "test_metrics": record["test_report"]["metrics"],
    }


def main() -> None:
    print(json.dumps(evidence_summary(SAMPLE_RUN), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
