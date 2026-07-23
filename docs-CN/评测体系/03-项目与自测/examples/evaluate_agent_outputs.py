"""Validate an offline eval contract and gate a candidate release."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
DEFAULT_DATASET = HERE / "eval_dataset.json"
DEFAULT_RUBRIC = HERE / "eval_rubric.json"
DEFAULT_PREDICTIONS = HERE / "predictions_pass.json"
EVALUATOR_VERSION = "offline-layered-evaluator-v3"
# This names the exact local byte representation, rather than implying that
# Python's JSON encoder implements a cross-language canonical JSON standard.
EVIDENCE_DIGEST_FORMAT = "python-json-sorted-utf8-v1"

SPLITS = {"train", "development", "test"}
LABELS = {"positive", "negative"}
DATASET_KEYS = {"schema_version", "dataset_version", "frozen_test", "cases"}
CASE_KEYS = {
    "id",
    "family_id",
    "split",
    "slice",
    "critical",
    "input",
    "expected_label",
    "expected_tool",
    "forbidden_actions",
    "requires_evidence",
}
RUBRIC_KEYS = {
    "schema_version",
    "rubric_version",
    "positive_label",
    "baseline_release",
    "eval_split",
    "gates",
    "bootstrap",
}
GATE_KEYS = {
    "min_overall_pass_rate",
    "min_precision",
    "min_recall",
    "min_f1",
    "critical_slice_min_pass_rate",
    "max_slice_pass_rate_gap",
    "max_mean_latency_ms",
    "max_p95_latency_ms",
    "max_mean_cost_usd",
    "min_paired_delta_ci_low",
}
BOOTSTRAP_KEYS = {"samples", "seed", "confidence"}
PREDICTIONS_KEYS = {
    "schema_version",
    "prediction_set_version",
    "dataset_version",
    "releases",
}
RELEASE_KEYS = {"release_id", "records"}
RECORD_KEYS = {
    "case_id",
    "predicted_label",
    "tool",
    "actions",
    "evidence_present",
    "latency_ms",
    "estimated_cost_usd",
}


class ContractError(ValueError):
    """Raised when an input violates the teaching contract."""


@dataclass(frozen=True)
class Decision:
    action: str
    primary_reason: str
    reasons: tuple[str, ...]
    evidence_fingerprint: str
    evidence_sha256: str
    baseline_release: str
    candidate_release: str
    baseline_metrics: dict[str, Any]
    candidate_metrics: dict[str, Any]
    comparison: dict[str, Any]


def reject_json_constant(token: str) -> None:
    raise ContractError(f"JSON contains non-standard constant: {token}")


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"JSON contains duplicate key: {key}")
        result[key] = value
    return result


def reject_non_utf8_scalar_strings(value: object, context: str) -> None:
    """Reject decoded strings that cannot join deterministic UTF-8 evidence."""
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ContractError(
                f"{context} contains a Unicode surrogate that cannot encode as UTF-8"
            ) from exc
        return
    if isinstance(value, dict):
        for key, item in value.items():
            reject_non_utf8_scalar_strings(key, f"{context} field name")
            key_context = f"{context}.{key}" if isinstance(key, str) else context
            reject_non_utf8_scalar_strings(item, key_context)
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            reject_non_utf8_scalar_strings(item, f"{context}[{index}]")


def load_json(path: Path) -> object:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(
                handle,
                parse_constant=reject_json_constant,
                object_pairs_hook=reject_duplicate_json_keys,
            )
    except UnicodeDecodeError as exc:
        raise ContractError(f"{path.name} must be valid UTF-8 JSON") from exc
    reject_non_utf8_scalar_strings(data, path.name)
    return data


def require_exact_dict(value: object, keys: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{context} must be an object")
    actual = set(value)
    missing = sorted(keys - actual)
    unknown = sorted(actual - keys)
    if missing or unknown:
        raise ContractError(
            f"{context} fields mismatch; missing={missing}, unknown={unknown}"
        )
    return value


def require_string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{context} must be a non-empty string")
    return value


def require_bool(value: object, context: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(f"{context} must be boolean")
    return value


def require_number(
    value: object,
    context: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{context} must be a number, not boolean")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ContractError(f"{context} must be representable as a finite number") from exc
    if not math.isfinite(number):
        raise ContractError(f"{context} must be finite")
    if minimum is not None and number < minimum:
        raise ContractError(f"{context} must be >= {minimum}")
    if maximum is not None and number > maximum:
        raise ContractError(f"{context} must be <= {maximum}")
    return number


def require_integer(
    value: object,
    context: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{context} must be an integer, not boolean")
    if minimum is not None and value < minimum:
        raise ContractError(f"{context} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ContractError(f"{context} must be <= {maximum}")
    return value


def require_nullable_string(value: object, context: str) -> str | None:
    if value is None:
        return None
    return require_string(value, context)


def require_unique_string_list(value: object, context: str) -> list[str]:
    if not isinstance(value, list):
        raise ContractError(f"{context} must be an array")
    result = [require_string(item, f"{context}[{index}]") for index, item in enumerate(value)]
    if len(result) != len(set(result)):
        raise ContractError(f"{context} contains duplicates")
    return result


def validate_case(value: object, index: int) -> dict[str, Any]:
    context = f"dataset.cases[{index}]"
    case = require_exact_dict(value, CASE_KEYS, context)
    require_string(case["id"], f"{context}.id")
    require_string(case["family_id"], f"{context}.family_id")
    split = require_string(case["split"], f"{context}.split")
    if split not in SPLITS:
        raise ContractError(f"{context}.split must be one of {sorted(SPLITS)}")
    require_string(case["slice"], f"{context}.slice")
    require_bool(case["critical"], f"{context}.critical")
    require_string(case["input"], f"{context}.input")
    label = require_string(case["expected_label"], f"{context}.expected_label")
    if label not in LABELS:
        raise ContractError(f"{context}.expected_label must be one of {sorted(LABELS)}")
    require_nullable_string(case["expected_tool"], f"{context}.expected_tool")
    require_unique_string_list(case["forbidden_actions"], f"{context}.forbidden_actions")
    require_bool(case["requires_evidence"], f"{context}.requires_evidence")
    return case


def validate_dataset(value: object) -> dict[str, Any]:
    dataset = require_exact_dict(value, DATASET_KEYS, "dataset")
    if require_string(dataset["schema_version"], "dataset.schema_version") != "eval-dataset-v1":
        raise ContractError("dataset.schema_version must be eval-dataset-v1")
    require_string(dataset["dataset_version"], "dataset.dataset_version")
    if not require_bool(dataset["frozen_test"], "dataset.frozen_test"):
        raise ContractError("dataset.frozen_test must be true for a release gate")
    if not isinstance(dataset["cases"], list) or not dataset["cases"]:
        raise ContractError("dataset.cases must be a non-empty array")
    cases = [validate_case(item, index) for index, item in enumerate(dataset["cases"])]
    ids = [str(case["id"]) for case in cases]
    if len(ids) != len(set(ids)):
        raise ContractError("dataset case IDs must be unique")
    family_splits: dict[str, str] = {}
    for case in cases:
        family_id = str(case["family_id"])
        split = str(case["split"])
        previous = family_splits.setdefault(family_id, split)
        if previous != split:
            raise ContractError(
                f"split leakage: family_id={family_id} appears in {previous} and {split}"
            )
    present_splits = {str(case["split"]) for case in cases}
    if present_splits != SPLITS:
        raise ContractError(
            f"dataset must contain train/development/test; got {sorted(present_splits)}"
        )
    return dataset


def validate_rubric(value: object) -> dict[str, Any]:
    rubric = require_exact_dict(value, RUBRIC_KEYS, "rubric")
    if require_string(rubric["schema_version"], "rubric.schema_version") != "eval-rubric-v1":
        raise ContractError("rubric.schema_version must be eval-rubric-v1")
    require_string(rubric["rubric_version"], "rubric.rubric_version")
    positive_label = require_string(rubric["positive_label"], "rubric.positive_label")
    if positive_label not in LABELS:
        raise ContractError(f"rubric.positive_label must be one of {sorted(LABELS)}")
    require_string(rubric["baseline_release"], "rubric.baseline_release")
    if require_string(rubric["eval_split"], "rubric.eval_split") != "test":
        raise ContractError("rubric.eval_split must be test for this release gate")
    gates = require_exact_dict(rubric["gates"], GATE_KEYS, "rubric.gates")
    for key in (
        "min_overall_pass_rate",
        "min_precision",
        "min_recall",
        "min_f1",
        "critical_slice_min_pass_rate",
        "max_slice_pass_rate_gap",
    ):
        require_number(gates[key], f"rubric.gates.{key}", minimum=0.0, maximum=1.0)
    for key in ("max_mean_latency_ms", "max_p95_latency_ms", "max_mean_cost_usd"):
        require_number(gates[key], f"rubric.gates.{key}", minimum=0.0)
    require_number(
        gates["min_paired_delta_ci_low"],
        "rubric.gates.min_paired_delta_ci_low",
        minimum=-1.0,
        maximum=1.0,
    )
    bootstrap = require_exact_dict(rubric["bootstrap"], BOOTSTRAP_KEYS, "rubric.bootstrap")
    require_integer(bootstrap["samples"], "rubric.bootstrap.samples", minimum=100, maximum=100_000)
    require_integer(bootstrap["seed"], "rubric.bootstrap.seed")
    require_number(
        bootstrap["confidence"],
        "rubric.bootstrap.confidence",
        minimum=0.5,
        maximum=0.999,
    )
    return rubric


def validate_record(value: object, context: str) -> dict[str, Any]:
    record = require_exact_dict(value, RECORD_KEYS, context)
    require_string(record["case_id"], f"{context}.case_id")
    label = require_string(record["predicted_label"], f"{context}.predicted_label")
    if label not in LABELS:
        raise ContractError(f"{context}.predicted_label must be one of {sorted(LABELS)}")
    require_nullable_string(record["tool"], f"{context}.tool")
    require_unique_string_list(record["actions"], f"{context}.actions")
    require_bool(record["evidence_present"], f"{context}.evidence_present")
    require_number(record["latency_ms"], f"{context}.latency_ms", minimum=0.0)
    require_number(record["estimated_cost_usd"], f"{context}.estimated_cost_usd", minimum=0.0)
    return record


def validate_predictions(value: object, dataset: dict[str, Any]) -> dict[str, Any]:
    predictions = require_exact_dict(value, PREDICTIONS_KEYS, "predictions")
    if (
        require_string(predictions["schema_version"], "predictions.schema_version")
        != "eval-predictions-v1"
    ):
        raise ContractError("predictions.schema_version must be eval-predictions-v1")
    require_string(predictions["prediction_set_version"], "predictions.prediction_set_version")
    if predictions["dataset_version"] != dataset["dataset_version"]:
        raise ContractError("predictions.dataset_version does not match dataset.dataset_version")
    if not isinstance(predictions["releases"], list) or not predictions["releases"]:
        raise ContractError("predictions.releases must be a non-empty array")
    expected_ids = {
        str(case["id"]) for case in dataset["cases"] if case["split"] == "test"
    }
    release_ids: list[str] = []
    for release_index, value_release in enumerate(predictions["releases"]):
        release_context = f"predictions.releases[{release_index}]"
        release = require_exact_dict(value_release, RELEASE_KEYS, release_context)
        release_id = require_string(release["release_id"], f"{release_context}.release_id")
        release_ids.append(release_id)
        if not isinstance(release["records"], list):
            raise ContractError(f"{release_context}.records must be an array")
        records = [
            validate_record(item, f"{release_context}.records[{record_index}]")
            for record_index, item in enumerate(release["records"])
        ]
        actual_ids = [str(record["case_id"]) for record in records]
        if len(actual_ids) != len(set(actual_ids)):
            raise ContractError(f"{release_context}.records contains duplicate case_id")
        if set(actual_ids) != expected_ids:
            missing = sorted(expected_ids - set(actual_ids))
            unknown = sorted(set(actual_ids) - expected_ids)
            raise ContractError(
                f"{release_context}.records must exactly cover frozen test IDs; "
                f"missing={missing}, unknown={unknown}"
            )
    if len(release_ids) != len(set(release_ids)):
        raise ContractError("predictions release IDs must be unique")
    return predictions


def release_records(predictions: dict[str, Any], release_id: str) -> dict[str, dict[str, Any]]:
    for release in predictions["releases"]:
        if release["release_id"] == release_id:
            return {str(record["case_id"]): record for record in release["records"]}
    raise ContractError(f"release not found: {release_id}")


def grade_case(case: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    actions = set(str(item) for item in record["actions"])
    forbidden = set(str(item) for item in case["forbidden_actions"])
    checks = {
        "label_correct": record["predicted_label"] == case["expected_label"],
        "tool_correct": record["tool"] == case["expected_tool"],
        "forbidden_actions_absent": actions.isdisjoint(forbidden),
        "evidence_requirement_met": (
            bool(record["evidence_present"]) if case["requires_evidence"] else True
        ),
    }
    passed = all(checks.values())
    return {
        "case_id": case["id"],
        "slice": case["slice"],
        "critical": case["critical"],
        "passed": passed,
        "score": statistics.mean(float(value) for value in checks.values()),
        "checks": checks,
    }


def divide_or_none(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def f1_or_none(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None or precision + recall == 0:
        return None
    return 2 * precision * recall / (precision + recall)


def nearest_rank(values: Iterable[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ContractError("cannot calculate percentile for an empty sequence")
    if probability <= 0 or probability > 1:
        raise ContractError("percentile probability must be in (0, 1]")
    rank = max(1, math.ceil(probability * len(ordered)))
    return ordered[rank - 1]


def calculate_metrics(
    cases: list[dict[str, Any]], records: dict[str, dict[str, Any]], positive_label: str
) -> dict[str, Any]:
    results = [grade_case(case, records[str(case["id"])]) for case in cases]
    tp = fp = tn = fn = 0
    for case in cases:
        predicted = records[str(case["id"])]["predicted_label"]
        expected_positive = case["expected_label"] == positive_label
        predicted_positive = predicted == positive_label
        if expected_positive and predicted_positive:
            tp += 1
        elif not expected_positive and predicted_positive:
            fp += 1
        elif not expected_positive and not predicted_positive:
            tn += 1
        else:
            fn += 1
    precision = divide_or_none(tp, tp + fp)
    recall = divide_or_none(tp, tp + fn)
    f1 = f1_or_none(precision, recall)
    by_slice_values: dict[str, list[bool]] = {}
    critical_by_slice: dict[str, int] = {}
    for result in results:
        slice_name = str(result["slice"])
        by_slice_values.setdefault(slice_name, []).append(bool(result["passed"]))
        critical_by_slice[slice_name] = critical_by_slice.get(slice_name, 0) + int(
            bool(result["critical"])
        )
    by_slice = {
        name: {
            "count": len(values),
            "pass_rate": statistics.mean(float(value) for value in values),
            "critical_count": critical_by_slice[name],
        }
        for name, values in sorted(by_slice_values.items())
    }
    slice_rates = [float(item["pass_rate"]) for item in by_slice.values()]
    latencies = [float(records[str(case["id"])]["latency_ms"]) for case in cases]
    costs = [float(records[str(case["id"])]["estimated_cost_usd"]) for case in cases]
    return {
        "case_count": len(cases),
        "pass_rate": statistics.mean(float(result["passed"]) for result in results),
        "mean_score": statistics.mean(float(result["score"]) for result in results),
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "mean_latency_ms": statistics.mean(latencies),
        "p95_latency_ms": nearest_rank(latencies, 0.95),
        "mean_estimated_cost_usd": statistics.mean(costs),
        "slice_pass_rate_gap": max(slice_rates) - min(slice_rates),
        "by_slice": by_slice,
        "critical_failures": [
            str(result["case_id"])
            for result in results
            if result["critical"] and not result["passed"]
        ],
        "case_results": results,
    }


def bootstrap_interval(
    differences: list[float], samples: int, seed: int, confidence: float
) -> tuple[float, float]:
    if not differences:
        raise ContractError("paired bootstrap requires at least one difference")
    rng = random.Random(seed)
    estimates = sorted(
        statistics.mean(rng.choice(differences) for _ in differences)
        for _ in range(samples)
    )
    tail = (1.0 - confidence) / 2.0
    return nearest_rank(estimates, tail), nearest_rank(estimates, 1.0 - tail)


def full_evidence_sha256(*values: object) -> str:
    """Return a digest for this evaluator's versioned local evidence encoding.

    ``sort_keys=True`` and UTF-8 make this Python representation reproducible
    for the validated teaching artifacts.  They do *not* implement a
    cross-language canonical JSON standard, so another system must either
    verify these exact bytes or agree on a separately specified canonicalizer.
    The short fingerprint remains display-only; handoffs use the complete
    digest together with :data:`EVIDENCE_DIGEST_FORMAT`. Non-finite values and
    strings that cannot encode as UTF-8 are rejected as contract errors.
    """
    reject_non_utf8_scalar_strings(values, "evidence")
    try:
        payload = json.dumps(
            values,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        encoded = payload.encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise ContractError(
            "evidence payload must be finite JSON values serializable as UTF-8 by this evaluator"
        ) from exc
    return hashlib.sha256(encoded).hexdigest()


def fingerprint(*values: object) -> str:
    """Return a display-only prefix of :func:`full_evidence_sha256`."""
    return full_evidence_sha256(*values)[:16]


def metric_below(value: float | None, threshold: float) -> bool:
    return value is None or value < threshold


def evaluate(
    dataset: dict[str, Any],
    rubric: dict[str, Any],
    predictions: dict[str, Any],
    candidate_release: str,
) -> Decision:
    baseline_release = str(rubric["baseline_release"])
    if candidate_release == baseline_release:
        raise ContractError("candidate release must differ from baseline release")
    test_cases = [case for case in dataset["cases"] if case["split"] == rubric["eval_split"]]
    baseline_records = release_records(predictions, baseline_release)
    candidate_records = release_records(predictions, candidate_release)
    positive_label = str(rubric["positive_label"])
    baseline_metrics = calculate_metrics(test_cases, baseline_records, positive_label)
    candidate_metrics = calculate_metrics(test_cases, candidate_records, positive_label)
    baseline_results = {
        str(item["case_id"]): bool(item["passed"])
        for item in baseline_metrics["case_results"]
    }
    candidate_results = {
        str(item["case_id"]): bool(item["passed"])
        for item in candidate_metrics["case_results"]
    }
    differences = [
        float(candidate_results[str(case["id"])]) - float(baseline_results[str(case["id"])])
        for case in test_cases
    ]
    bootstrap = rubric["bootstrap"]
    low, high = bootstrap_interval(
        differences,
        int(bootstrap["samples"]),
        int(bootstrap["seed"]),
        float(bootstrap["confidence"]),
    )
    comparison = {
        "paired_pass_rate_delta": statistics.mean(differences),
        "paired_bootstrap_interval": [low, high],
        "confidence": bootstrap["confidence"],
        "samples": bootstrap["samples"],
        "seed": bootstrap["seed"],
    }

    gates = rubric["gates"]
    block_reasons: list[str] = []
    review_reasons: list[str] = []

    critical_failures = list(candidate_metrics["critical_failures"])
    if critical_failures:
        block_reasons.append(
            "critical safety/privacy case failure(s): " + ", ".join(critical_failures)
        )
    critical_slices = {
        str(case["slice"]) for case in test_cases if bool(case["critical"])
    }
    for slice_name in sorted(critical_slices):
        pass_rate = float(candidate_metrics["by_slice"][slice_name]["pass_rate"])
        if pass_rate < float(gates["critical_slice_min_pass_rate"]):
            block_reasons.append(
                f"critical slice {slice_name} pass rate {pass_rate:.3f} below gate"
            )
    if float(candidate_metrics["pass_rate"]) < float(gates["min_overall_pass_rate"]):
        block_reasons.append("overall deterministic pass rate below gate")
    for metric_name, gate_name in (
        ("precision", "min_precision"),
        ("recall", "min_recall"),
        ("f1", "min_f1"),
    ):
        value = candidate_metrics[metric_name]
        if metric_below(None if value is None else float(value), float(gates[gate_name])):
            block_reasons.append(f"{metric_name} is undefined or below gate")

    if float(candidate_metrics["slice_pass_rate_gap"]) > float(
        gates["max_slice_pass_rate_gap"]
    ):
        review_reasons.append("slice pass-rate gap exceeds review gate")
    if float(candidate_metrics["mean_latency_ms"]) > float(gates["max_mean_latency_ms"]):
        review_reasons.append("mean latency exceeds review gate")
    if float(candidate_metrics["p95_latency_ms"]) > float(gates["max_p95_latency_ms"]):
        review_reasons.append("p95 latency exceeds review gate")
    if float(candidate_metrics["mean_estimated_cost_usd"]) > float(
        gates["max_mean_cost_usd"]
    ):
        review_reasons.append("mean estimated cost exceeds review gate")
    if low < float(gates["min_paired_delta_ci_low"]):
        review_reasons.append("paired bootstrap lower bound is below review gate")

    if block_reasons:
        action = "BLOCK"
        reasons = block_reasons + review_reasons
    elif review_reasons:
        action = "REVIEW"
        reasons = review_reasons
    else:
        action = "PASS"
        reasons = ["all frozen teaching gates passed"]
    evidence_sha256 = full_evidence_sha256(
        EVALUATOR_VERSION, dataset, rubric, predictions, candidate_release
    )
    return Decision(
        action=action,
        primary_reason=reasons[0],
        reasons=tuple(reasons),
        evidence_fingerprint=evidence_sha256[:16],
        evidence_sha256=evidence_sha256,
        baseline_release=baseline_release,
        candidate_release=candidate_release,
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
        comparison=comparison,
    )


def decision_to_dict(decision: Decision) -> dict[str, Any]:
    return {
        "action": decision.action,
        "primary_reason": decision.primary_reason,
        "reasons": list(decision.reasons),
        "evidence_fingerprint": decision.evidence_fingerprint,
        "evidence_sha256": decision.evidence_sha256,
        "evidence_digest_format": EVIDENCE_DIGEST_FORMAT,
        "evaluator_version": EVALUATOR_VERSION,
        "baseline_release": decision.baseline_release,
        "candidate_release": decision.candidate_release,
        "baseline_metrics": decision.baseline_metrics,
        "candidate_metrics": decision.candidate_metrics,
        "comparison": decision.comparison,
        "limitations": [
            "Synthetic teaching cases are not a production performance estimate.",
            "Slice gaps from tiny samples are investigation signals, not fairness proof.",
            "Estimated cost is not a provider invoice.",
            "Fixture observations are not trusted harness receipts or final environment state.",
            "The local digest encoding is not cross-language canonical JSON or a signature.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--rubric", type=Path, default=DEFAULT_RUBRIC)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--candidate", default="candidate-pass")
    return parser


def run(args: argparse.Namespace) -> int:
    dataset = validate_dataset(load_json(args.dataset))
    rubric = validate_rubric(load_json(args.rubric))
    predictions = validate_predictions(load_json(args.predictions), dataset)
    decision = evaluate(dataset, rubric, predictions, args.candidate)
    print(json.dumps(decision_to_dict(decision), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if decision.action == "PASS" else 1


def main(argv: list[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
