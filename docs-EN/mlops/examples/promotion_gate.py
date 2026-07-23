"""Deterministic, offline MLOps promotion and operations gate.

The exercise uses only the Python standard library.  It does not train or load
a real model, contact a registry, deploy a service, or access the network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = 2
DEFAULT_CANDIDATES = Path(__file__).with_name("candidates.json")
DEFAULT_OBSERVATIONS = Path(__file__).with_name("observations.json")
DECISION_ACTIONS = {
    "block_rollout_and_investigate",
    "continue",
    "investigate",
    "rollback_and_investigate",
    "rollback_and_review_retraining",
}


class GateError(ValueError):
    """Raised when evidence is invalid or a requested subject does not exist."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object while rejecting duplicate keys."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GateError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_nonstandard_constant(value: str) -> None:
    raise GateError(f"non-standard JSON constant: {value}")


def require_exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise GateError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise GateError(f"{label} fields differ; missing={missing}, extra={extra}")
    return value


def require_text(value: Any, label: str, maximum: int = 200) -> str:
    if not isinstance(value, str):
        raise GateError(f"{label} must be a string")
    normalized = value.strip()
    if not normalized:
        raise GateError(f"{label} must not be empty")
    if len(normalized) > maximum:
        raise GateError(f"{label} exceeds {maximum} characters")
    if normalized.casefold() == "latest":
        raise GateError(f"{label} must be immutable, not 'latest'")
    return normalized


def require_choice(value: Any, label: str, choices: set[str]) -> str:
    text = require_text(value, label)
    if text not in choices:
        raise GateError(f"{label} must be one of {sorted(choices)}")
    return text


def require_fingerprint(value: Any, label: str) -> str:
    digest = require_text(value, label, 64)
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise GateError(f"{label} must use 64 lowercase hexadecimal characters")
    return digest


def require_number(
    value: Any,
    label: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GateError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise GateError(f"{label} must be finite")
    if minimum is not None and number < minimum:
        raise GateError(f"{label} must be >= {minimum}")
    if maximum is not None and number > maximum:
        raise GateError(f"{label} must be <= {maximum}")
    return number


def require_integer(value: Any, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GateError(f"{label} must be an integer")
    if value < minimum:
        raise GateError(f"{label} must be >= {minimum}")
    return value


def require_digest(value: Any, label: str) -> str:
    digest = require_text(value, label, 71)
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise GateError(f"{label} must use sha256:<64 lowercase hex characters>")
    hexadecimal = digest.removeprefix("sha256:")
    if any(character not in "0123456789abcdef" for character in hexadecimal):
        raise GateError(f"{label} must use lowercase hexadecimal")
    return digest


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_pairs,
            parse_constant=reject_nonstandard_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GateError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GateError(f"{path} must contain a JSON object")
    return value


def validate_metrics(value: Any, label: str) -> Mapping[str, Any]:
    metrics = require_exact_keys(
        value,
        {"overall_accuracy", "critical_slice_recall", "p95_latency_ms"},
        label,
    )
    require_number(metrics["overall_accuracy"], f"{label}.overall_accuracy", minimum=0, maximum=1)
    require_number(
        metrics["critical_slice_recall"],
        f"{label}.critical_slice_recall",
        minimum=0,
        maximum=1,
    )
    require_number(metrics["p95_latency_ms"], f"{label}.p95_latency_ms", minimum=0)
    return metrics


def validate_policy(value: Any) -> Mapping[str, Any]:
    policy = require_exact_keys(
        value,
        {
            "required_tests",
            "max_overall_accuracy_drop",
            "max_critical_slice_recall_drop",
            "max_p95_latency_ms",
            "max_artifact_size_bytes",
            "max_error_rate",
            "drift_investigation_threshold",
            "min_observation_samples",
            "min_labeled_samples_for_quality_decision",
            "min_critical_labeled_samples_for_quality_decision",
            "min_label_coverage_for_quality_decision",
        },
        "policy",
    )
    tests = policy["required_tests"]
    if not isinstance(tests, list) or not tests:
        raise GateError("policy.required_tests must be a non-empty list")
    normalized = [require_text(item, "policy.required_tests[]", 80) for item in tests]
    if len(set(normalized)) != len(normalized):
        raise GateError("policy.required_tests must be unique")
    for field in (
        "max_overall_accuracy_drop",
        "max_critical_slice_recall_drop",
        "max_error_rate",
        "drift_investigation_threshold",
        "min_label_coverage_for_quality_decision",
    ):
        require_number(policy[field], f"policy.{field}", minimum=0, maximum=1)
    require_number(policy["max_p95_latency_ms"], "policy.max_p95_latency_ms", minimum=0)
    require_integer(policy["max_artifact_size_bytes"], "policy.max_artifact_size_bytes", 1)
    require_integer(policy["min_observation_samples"], "policy.min_observation_samples", 1)
    require_integer(
        policy["min_labeled_samples_for_quality_decision"],
        "policy.min_labeled_samples_for_quality_decision",
        1,
    )
    require_integer(
        policy["min_critical_labeled_samples_for_quality_decision"],
        "policy.min_critical_labeled_samples_for_quality_decision",
        1,
    )
    return policy


def validate_signature(value: Any, label: str) -> Mapping[str, Any]:
    signature = require_exact_keys(
        value,
        {"input_schema_version", "output_schema_version"},
        label,
    )
    require_text(signature["input_schema_version"], f"{label}.input_schema_version")
    require_text(signature["output_schema_version"], f"{label}.output_schema_version")
    return signature


def validate_baseline(value: Any) -> Mapping[str, Any]:
    baseline = require_exact_keys(
        value,
        {"model_id", "artifact_digest", "signature", "metrics"},
        "baseline",
    )
    require_text(baseline["model_id"], "baseline.model_id")
    require_digest(baseline["artifact_digest"], "baseline.artifact_digest")
    validate_signature(baseline["signature"], "baseline.signature")
    validate_metrics(baseline["metrics"], "baseline.metrics")
    return baseline


def validate_candidate(
    value: Any,
    index: int,
    required_tests: list[str],
) -> Mapping[str, Any]:
    label = f"candidates[{index}]"
    candidate = require_exact_keys(
        value,
        {"candidate_id", "lineage", "artifact", "tests", "metrics"},
        label,
    )
    require_text(candidate["candidate_id"], f"{label}.candidate_id")

    lineage = require_exact_keys(
        candidate["lineage"],
        {
            "data_snapshot",
            "label_version",
            "code_commit",
            "environment_digest",
            "training_config_digest",
        },
        f"{label}.lineage",
    )
    require_text(lineage["data_snapshot"], f"{label}.lineage.data_snapshot")
    require_text(lineage["label_version"], f"{label}.lineage.label_version")
    require_text(lineage["code_commit"], f"{label}.lineage.code_commit")
    require_digest(lineage["environment_digest"], f"{label}.lineage.environment_digest")
    require_digest(
        lineage["training_config_digest"],
        f"{label}.lineage.training_config_digest",
    )

    artifact = require_exact_keys(
        candidate["artifact"],
        {"digest", "format", "size_bytes", "signature"},
        f"{label}.artifact",
    )
    require_digest(artifact["digest"], f"{label}.artifact.digest")
    require_text(artifact["format"], f"{label}.artifact.format")
    require_integer(artifact["size_bytes"], f"{label}.artifact.size_bytes", 1)
    validate_signature(artifact["signature"], f"{label}.artifact.signature")

    tests = require_exact_keys(candidate["tests"], set(required_tests), f"{label}.tests")
    for test_name in required_tests:
        if not isinstance(tests[test_name], bool):
            raise GateError(f"{label}.tests.{test_name} must be boolean")
    validate_metrics(candidate["metrics"], f"{label}.metrics")
    return candidate


def validate_candidates_fixture(value: Any) -> Mapping[str, Any]:
    fixture = require_exact_keys(
        value,
        {"schema_version", "policy_version", "policy", "baseline", "candidates"},
        "candidate fixture",
    )
    if fixture["schema_version"] != SCHEMA_VERSION:
        raise GateError("candidate fixture schema_version is unsupported")
    require_text(fixture["policy_version"], "policy_version")
    policy = validate_policy(fixture["policy"])
    validate_baseline(fixture["baseline"])
    candidates = fixture["candidates"]
    if not isinstance(candidates, list) or not candidates:
        raise GateError("candidates must be a non-empty list")
    identifiers: set[str] = set()
    for index, candidate in enumerate(candidates):
        validated = validate_candidate(candidate, index, policy["required_tests"])
        identifier = validated["candidate_id"]
        if identifier in identifiers:
            raise GateError(f"duplicate candidate_id: {identifier}")
        identifiers.add(identifier)
    return fixture


def evaluate_candidate(
    candidate: Mapping[str, Any],
    baseline: Mapping[str, Any],
    policy: Mapping[str, Any],
    policy_version: str,
) -> dict[str, Any]:
    reasons: list[str] = []
    for test_name in policy["required_tests"]:
        if candidate["tests"][test_name] is not True:
            reasons.append(f"required test failed: {test_name}")

    candidate_metrics = candidate["metrics"]
    baseline_metrics = baseline["metrics"]
    minimum_accuracy = (
        baseline_metrics["overall_accuracy"] - policy["max_overall_accuracy_drop"]
    )
    if candidate_metrics["overall_accuracy"] < minimum_accuracy:
        reasons.append(
            "overall_accuracy below policy: "
            f"candidate={candidate_metrics['overall_accuracy']:.3f}, "
            f"minimum={minimum_accuracy:.3f}"
        )

    minimum_slice = (
        baseline_metrics["critical_slice_recall"]
        - policy["max_critical_slice_recall_drop"]
    )
    if candidate_metrics["critical_slice_recall"] < minimum_slice:
        reasons.append(
            "critical_slice_recall below policy: "
            f"candidate={candidate_metrics['critical_slice_recall']:.3f}, "
            f"minimum={minimum_slice:.3f}"
        )
    if candidate_metrics["p95_latency_ms"] > policy["max_p95_latency_ms"]:
        reasons.append(
            "p95_latency_ms above policy: "
            f"candidate={candidate_metrics['p95_latency_ms']:.1f}, "
            f"maximum={policy['max_p95_latency_ms']:.1f}"
        )
    if candidate["artifact"]["size_bytes"] > policy["max_artifact_size_bytes"]:
        reasons.append(
            "artifact size above policy: "
            f"candidate={candidate['artifact']['size_bytes']}, "
            f"maximum={policy['max_artifact_size_bytes']}"
        )
    if candidate["artifact"]["signature"] != baseline["signature"]:
        reasons.append("artifact signature is incompatible with the baseline")

    passed = not reasons
    if passed:
        reasons.append("all lab promotion checks passed")
    evidence = {
        "candidate": candidate,
        "baseline": baseline,
        "policy": policy,
        "policy_version": policy_version,
    }
    return {
        "subject_id": candidate["candidate_id"],
        "decision": "promote" if passed else "block",
        "passed": passed,
        "policy_version": policy_version,
        "evidence_fingerprint": fingerprint(evidence),
        "reasons": reasons,
    }


def validate_observation(value: Any, index: int) -> Mapping[str, Any]:
    label = f"windows[{index}]"
    observation = require_exact_keys(
        value,
        {
            "window_id",
            "phase",
            "sample_count",
            "labeled_count",
            "critical_labeled_count",
            "signals",
        },
        label,
    )
    require_text(observation["window_id"], f"{label}.window_id")
    require_choice(observation["phase"], f"{label}.phase", {"shadow", "canary"})
    require_integer(observation["sample_count"], f"{label}.sample_count", 1)
    require_integer(observation["labeled_count"], f"{label}.labeled_count")
    require_integer(
        observation["critical_labeled_count"],
        f"{label}.critical_labeled_count",
    )
    if observation["labeled_count"] > observation["sample_count"]:
        raise GateError(f"{label}.labeled_count must not exceed sample_count")
    if observation["critical_labeled_count"] > observation["labeled_count"]:
        raise GateError(f"{label}.critical_labeled_count must not exceed labeled_count")
    signals = require_exact_keys(
        observation["signals"],
        {"error_rate", "p95_latency_ms", "input_drift_score", "critical_slice_recall"},
        f"{label}.signals",
    )
    require_number(signals["error_rate"], f"{label}.signals.error_rate", minimum=0, maximum=1)
    require_number(signals["p95_latency_ms"], f"{label}.signals.p95_latency_ms", minimum=0)
    require_number(
        signals["input_drift_score"],
        f"{label}.signals.input_drift_score",
        minimum=0,
        maximum=1,
    )
    if signals["critical_slice_recall"] is not None:
        require_number(
            signals["critical_slice_recall"],
            f"{label}.signals.critical_slice_recall",
            minimum=0,
            maximum=1,
        )
    return observation


def validate_observations_fixture(
    value: Any,
    candidate_fixture: Mapping[str, Any],
) -> Mapping[str, Any]:
    fixture = require_exact_keys(
        value,
        {"schema_version", "policy_version", "deployment", "reference", "windows"},
        "observations fixture",
    )
    if fixture["schema_version"] != SCHEMA_VERSION:
        raise GateError("observations schema_version is unsupported")
    policy_version = require_text(fixture["policy_version"], "observations.policy_version")
    if policy_version != candidate_fixture["policy_version"]:
        raise GateError("observation and candidate policy versions differ")

    deployment = require_exact_keys(
        fixture["deployment"],
        {
            "release_id",
            "model_id",
            "artifact_digest",
            "baseline_model_id",
            "promotion_evidence_fingerprint",
        },
        "deployment",
    )
    require_text(deployment["release_id"], "deployment.release_id")
    require_text(deployment["model_id"], "deployment.model_id")
    require_digest(deployment["artifact_digest"], "deployment.artifact_digest")
    require_text(deployment["baseline_model_id"], "deployment.baseline_model_id")
    require_fingerprint(
        deployment["promotion_evidence_fingerprint"],
        "deployment.promotion_evidence_fingerprint",
    )
    if deployment["baseline_model_id"] != candidate_fixture["baseline"]["model_id"]:
        raise GateError("deployment baseline_model_id does not match the candidate fixture")
    candidates = {item["candidate_id"]: item for item in candidate_fixture["candidates"]}
    if deployment["model_id"] not in candidates:
        raise GateError("deployment model_id is not a known candidate")
    deployed_candidate = candidates[deployment["model_id"]]
    if deployment["artifact_digest"] != deployed_candidate["artifact"]["digest"]:
        raise GateError("deployment artifact digest does not match the candidate manifest")

    promotion_decision = evaluate_candidate(
        deployed_candidate,
        candidate_fixture["baseline"],
        candidate_fixture["policy"],
        candidate_fixture["policy_version"],
    )
    if promotion_decision["passed"] is not True:
        raise GateError("deployment candidate did not pass the promotion gate")
    if (
        deployment["promotion_evidence_fingerprint"]
        != promotion_decision["evidence_fingerprint"]
    ):
        raise GateError("deployment promotion evidence fingerprint is stale or mismatched")

    reference = require_exact_keys(
        fixture["reference"],
        {
            "model_id",
            "artifact_digest",
            "critical_slice_recall",
            "p95_latency_ms",
            "error_rate",
        },
        "reference",
    )
    require_text(reference["model_id"], "reference.model_id")
    require_digest(reference["artifact_digest"], "reference.artifact_digest")
    if reference["model_id"] != deployment["model_id"]:
        raise GateError("reference model_id does not match the deployed candidate")
    if reference["artifact_digest"] != deployment["artifact_digest"]:
        raise GateError("reference artifact digest does not match the deployed artifact")
    require_number(reference["critical_slice_recall"], "reference.critical_slice_recall", minimum=0, maximum=1)
    require_number(reference["p95_latency_ms"], "reference.p95_latency_ms", minimum=0)
    require_number(reference["error_rate"], "reference.error_rate", minimum=0, maximum=1)

    windows = fixture["windows"]
    if not isinstance(windows, list) or not windows:
        raise GateError("windows must be a non-empty list")
    identifiers: set[str] = set()
    for index, observation in enumerate(windows):
        validated = validate_observation(observation, index)
        identifier = validated["window_id"]
        if identifier in identifiers:
            raise GateError(f"duplicate window_id: {identifier}")
        identifiers.add(identifier)
    return fixture


def assess_observation(
    observation: Mapping[str, Any],
    reference: Mapping[str, Any],
    policy: Mapping[str, Any],
    policy_version: str,
    deployment: Mapping[str, Any],
) -> dict[str, Any]:
    signals = observation["signals"]
    phase = observation["phase"]
    reasons: list[str] = []
    technical_failure = False
    if signals["error_rate"] > policy["max_error_rate"]:
        technical_failure = True
        reasons.append(
            f"error_rate={signals['error_rate']:.3f} exceeds {policy['max_error_rate']:.3f}"
        )
    if signals["p95_latency_ms"] > policy["max_p95_latency_ms"]:
        technical_failure = True
        reasons.append(
            "p95_latency_ms="
            f"{signals['p95_latency_ms']:.1f} exceeds {policy['max_p95_latency_ms']:.1f}"
        )

    drift_detected = signals["input_drift_score"] >= policy["drift_investigation_threshold"]
    sample_count = observation["sample_count"]
    labeled_count = observation["labeled_count"]
    critical_labeled_count = observation["critical_labeled_count"]
    label_coverage = labeled_count / sample_count
    evidence_gaps: list[str] = []
    if sample_count < policy["min_observation_samples"]:
        evidence_gaps.append(
            f"sample_count={sample_count} is below {policy['min_observation_samples']}"
        )
    if labeled_count < policy["min_labeled_samples_for_quality_decision"]:
        evidence_gaps.append(
            "labeled_count="
            f"{labeled_count} is below {policy['min_labeled_samples_for_quality_decision']}"
        )
    if critical_labeled_count < policy["min_critical_labeled_samples_for_quality_decision"]:
        evidence_gaps.append(
            "critical_labeled_count="
            f"{critical_labeled_count} is below "
            f"{policy['min_critical_labeled_samples_for_quality_decision']}"
        )
    if label_coverage < policy["min_label_coverage_for_quality_decision"]:
        evidence_gaps.append(
            f"label_coverage={label_coverage:.3f} is below "
            f"{policy['min_label_coverage_for_quality_decision']:.3f}"
        )
    if signals["critical_slice_recall"] is None:
        evidence_gaps.append("critical_slice_recall is unavailable")
    labels_sufficient = not evidence_gaps
    quality_regression = False
    minimum_slice = (
        reference["critical_slice_recall"]
        - policy["max_critical_slice_recall_drop"]
    )
    if labels_sufficient and signals["critical_slice_recall"] is not None:
        if signals["critical_slice_recall"] < minimum_slice:
            quality_regression = True
            reasons.append(
                "confirmed critical_slice_recall regression: "
                f"observed={signals['critical_slice_recall']:.3f}, minimum={minimum_slice:.3f}"
            )

    if technical_failure:
        action = (
            "block_rollout_and_investigate"
            if phase == "shadow"
            else "rollback_and_investigate"
        )
    elif quality_regression and drift_detected:
        if phase == "shadow":
            action = "block_rollout_and_investigate"
            reasons.append("shadow evidence blocks exposure before user-facing rollout")
        else:
            action = "rollback_and_review_retraining"
            reasons.append("drift accompanies a label-backed quality regression")
    elif quality_regression:
        action = (
            "block_rollout_and_investigate"
            if phase == "shadow"
            else "rollback_and_investigate"
        )
    elif evidence_gaps:
        action = "investigate"
        reasons.extend(f"evidence insufficient: {gap}" for gap in evidence_gaps)
    elif drift_detected:
        action = "investigate"
        reasons.append("drift detected without a confirmed quality regression")
    else:
        action = "continue"
        reasons.append("all operational evidence gates passed")

    if action not in DECISION_ACTIONS:
        raise GateError(f"internal action is unsupported: {action}")
    evidence = {
        "observation": observation,
        "deployment": deployment,
        "reference": reference,
        "policy": policy,
        "policy_version": policy_version,
    }
    return {
        "subject_id": observation["window_id"],
        "release_id": deployment["release_id"],
        "phase": phase,
        "label_coverage": label_coverage,
        "action": action,
        "policy_version": policy_version,
        "evidence_fingerprint": fingerprint(evidence),
        "reasons": reasons,
    }


def find_by_id(items: list[Mapping[str, Any]], field: str, identifier: str) -> Mapping[str, Any]:
    for item in items:
        if item[field] == identifier:
            return item
    raise GateError(f"unknown {field}: {identifier}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--observations", type=Path, default=DEFAULT_OBSERVATIONS)
    subparsers = parser.add_subparsers(dest="command", required=True)
    candidate = subparsers.add_parser("candidate", help="evaluate one candidate manifest")
    candidate.add_argument("--id", required=True)
    observation = subparsers.add_parser("observe", help="assess one production window")
    observation.add_argument("--id", required=True)
    subparsers.add_parser("audit", help="evaluate every included teaching scenario")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        candidate_fixture = load_json(args.candidates)
        validate_candidates_fixture(candidate_fixture)
        policy = candidate_fixture["policy"]
        policy_version = candidate_fixture["policy_version"]

        if args.command == "candidate":
            subject = find_by_id(candidate_fixture["candidates"], "candidate_id", args.id)
            result: Any = evaluate_candidate(
                subject,
                candidate_fixture["baseline"],
                policy,
                policy_version,
            )
            exit_code = 0 if result["passed"] else 1
        else:
            observations_fixture = load_json(args.observations)
            validate_observations_fixture(observations_fixture, candidate_fixture)
            if args.command == "observe":
                subject = find_by_id(observations_fixture["windows"], "window_id", args.id)
                result = assess_observation(
                    subject,
                    observations_fixture["reference"],
                    policy,
                    policy_version,
                    observations_fixture["deployment"],
                )
                exit_code = 0 if result["action"] == "continue" else 1
            else:
                result = {
                    "policy_version": policy_version,
                    "candidate_decisions": [
                        evaluate_candidate(
                            candidate,
                            candidate_fixture["baseline"],
                            policy,
                            policy_version,
                        )
                        for candidate in candidate_fixture["candidates"]
                    ],
                    "operational_decisions": [
                        assess_observation(
                            observation,
                            observations_fixture["reference"],
                            policy,
                            policy_version,
                            observations_fixture["deployment"],
                        )
                        for observation in observations_fixture["windows"]
                    ],
                }
                exit_code = 0
    except GateError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())


