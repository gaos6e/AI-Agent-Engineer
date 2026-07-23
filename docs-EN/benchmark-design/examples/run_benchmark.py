"""Validate and compare a strict offline Agent benchmark result package."""

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
DEFAULT_SPEC = HERE / "benchmark_spec.json"
DEFAULT_CASES = HERE / "benchmark_cases.json"
DEFAULT_RESULTS = HERE / "benchmark_results_pass.json"

SPLITS = {"train", "development", "test"}
STATUSES = {"success", "timeout", "error", "unknown"}
SPEC_KEYS = {
    "schema_version",
    "benchmark_id",
    "benchmark_version",
    "private_test_frozen",
    "claim",
    "target_population",
    "baseline_system_id",
    "primary_metric",
    "protocol",
    "gates",
    "bootstrap",
}
PROTOCOL_KEYS = {
    "protocol_version",
    "environment_id",
    "toolset_id",
    "reset_policy",
    "max_steps",
    "timeout_seconds",
    "retry_limit",
    "trial_count",
}
GATE_KEYS = {
    "task_min_trial_success_rate",
    "min_primary_task_success_rate",
    "critical_task_min_trial_success_rate",
    "min_final_state_trial_rate",
    "min_side_effect_free_trial_rate",
    "min_trial_stability_rate",
    "max_slice_task_success_gap",
    "max_mean_latency_ms",
    "max_p95_latency_ms",
    "max_mean_cost_units",
    "min_paired_delta_ci_low",
}
BOOTSTRAP_KEYS = {"samples", "seed", "confidence"}
CASES_KEYS = {
    "schema_version",
    "benchmark_id",
    "benchmark_version",
    "dataset_version",
    "cases",
}
CASE_KEYS = {
    "id",
    "family_id",
    "split",
    "slice",
    "critical",
    "task_type",
    "is_private",
    "initial_state",
    "expected_final_state",
    "allowed_tools",
    "forbidden_side_effects",
}
RESULTS_KEYS = {
    "schema_version",
    "benchmark_id",
    "benchmark_version",
    "dataset_version",
    "result_set_version",
    "systems",
}
SYSTEM_KEYS = {"system_id", "role", "protocol", "records"}
RECORD_KEYS = {
    "case_id",
    "trial_id",
    "status",
    "final_state",
    "side_effects",
    "tools_used",
    "latency_ms",
    "cost_units",
}


class ContractError(ValueError):
    """Raised when an input package violates the benchmark contract."""


@dataclass(frozen=True)
class Decision:
    action: str
    primary_reason: str
    reasons: tuple[str, ...]
    comparable: bool
    evidence_fingerprint: str
    baseline_system: str
    candidate_system: str
    baseline_metrics: dict[str, Any] | None
    candidate_metrics: dict[str, Any] | None
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


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(
            handle,
            parse_constant=reject_json_constant,
            object_pairs_hook=reject_duplicate_json_keys,
        )


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


def require_nullable_string(value: object, context: str) -> str | None:
    if value is None:
        return None
    return require_string(value, context)


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
    number = float(value)
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


def require_unique_string_list(value: object, context: str) -> list[str]:
    if not isinstance(value, list):
        raise ContractError(f"{context} must be an array")
    result = [
        require_string(item, f"{context}[{index}]")
        for index, item in enumerate(value)
    ]
    if len(result) != len(set(result)):
        raise ContractError(f"{context} contains duplicates")
    return result


def validate_protocol(value: object, context: str) -> dict[str, Any]:
    protocol = require_exact_dict(value, PROTOCOL_KEYS, context)
    for key in (
        "protocol_version",
        "environment_id",
        "toolset_id",
        "reset_policy",
    ):
        require_string(protocol[key], f"{context}.{key}")
    require_integer(protocol["max_steps"], f"{context}.max_steps", minimum=1)
    require_number(protocol["timeout_seconds"], f"{context}.timeout_seconds", minimum=0.001)
    require_integer(protocol["retry_limit"], f"{context}.retry_limit", minimum=0)
    require_integer(
        protocol["trial_count"],
        f"{context}.trial_count",
        minimum=2,
        maximum=100,
    )
    return protocol


def validate_spec(value: object) -> dict[str, Any]:
    spec = require_exact_dict(value, SPEC_KEYS, "spec")
    if require_string(spec["schema_version"], "spec.schema_version") != "agent-benchmark-spec-v1":
        raise ContractError("spec.schema_version must be agent-benchmark-spec-v1")
    for key in (
        "benchmark_id",
        "benchmark_version",
        "claim",
        "target_population",
        "baseline_system_id",
    ):
        require_string(spec[key], f"spec.{key}")
    if not require_bool(spec["private_test_frozen"], "spec.private_test_frozen"):
        raise ContractError("spec.private_test_frozen must be true")
    if require_string(spec["primary_metric"], "spec.primary_metric") != "task_success_rate":
        raise ContractError("spec.primary_metric must be task_success_rate")
    validate_protocol(spec["protocol"], "spec.protocol")
    gates = require_exact_dict(spec["gates"], GATE_KEYS, "spec.gates")
    for key in (
        "task_min_trial_success_rate",
        "min_primary_task_success_rate",
        "critical_task_min_trial_success_rate",
        "min_final_state_trial_rate",
        "min_side_effect_free_trial_rate",
        "min_trial_stability_rate",
        "max_slice_task_success_gap",
    ):
        require_number(gates[key], f"spec.gates.{key}", minimum=0.0, maximum=1.0)
    if float(gates["critical_task_min_trial_success_rate"]) < float(
        gates["task_min_trial_success_rate"]
    ):
        raise ContractError(
            "spec.gates.critical_task_min_trial_success_rate must be >= "
            "task_min_trial_success_rate"
        )
    for key in ("max_mean_latency_ms", "max_p95_latency_ms", "max_mean_cost_units"):
        require_number(gates[key], f"spec.gates.{key}", minimum=0.0)
    require_number(
        gates["min_paired_delta_ci_low"],
        "spec.gates.min_paired_delta_ci_low",
        minimum=-1.0,
        maximum=1.0,
    )
    bootstrap = require_exact_dict(spec["bootstrap"], BOOTSTRAP_KEYS, "spec.bootstrap")
    require_integer(bootstrap["samples"], "spec.bootstrap.samples", minimum=100, maximum=100_000)
    require_integer(bootstrap["seed"], "spec.bootstrap.seed")
    require_number(
        bootstrap["confidence"],
        "spec.bootstrap.confidence",
        minimum=0.5,
        maximum=0.999,
    )
    return spec


def validate_case(value: object, index: int) -> dict[str, Any]:
    context = f"cases.cases[{index}]"
    case = require_exact_dict(value, CASE_KEYS, context)
    for key in (
        "id",
        "family_id",
        "slice",
        "task_type",
        "initial_state",
        "expected_final_state",
    ):
        require_string(case[key], f"{context}.{key}")
    split = require_string(case["split"], f"{context}.split")
    if split not in SPLITS:
        raise ContractError(f"{context}.split must be one of {sorted(SPLITS)}")
    require_bool(case["critical"], f"{context}.critical")
    is_private = require_bool(case["is_private"], f"{context}.is_private")
    if is_private != (split == "test"):
        raise ContractError(f"{context}.is_private must be true only for test cases")
    require_unique_string_list(case["allowed_tools"], f"{context}.allowed_tools")
    require_unique_string_list(
        case["forbidden_side_effects"], f"{context}.forbidden_side_effects"
    )
    return case


def validate_cases(value: object, spec: dict[str, Any]) -> dict[str, Any]:
    case_file = require_exact_dict(value, CASES_KEYS, "cases")
    if require_string(case_file["schema_version"], "cases.schema_version") != "agent-benchmark-cases-v1":
        raise ContractError("cases.schema_version must be agent-benchmark-cases-v1")
    for key in ("benchmark_id", "benchmark_version", "dataset_version"):
        require_string(case_file[key], f"cases.{key}")
    if case_file["benchmark_id"] != spec["benchmark_id"]:
        raise ContractError("cases.benchmark_id does not match spec")
    if case_file["benchmark_version"] != spec["benchmark_version"]:
        raise ContractError("cases.benchmark_version does not match spec")
    if not isinstance(case_file["cases"], list) or not case_file["cases"]:
        raise ContractError("cases.cases must be a non-empty array")
    cases = [validate_case(item, index) for index, item in enumerate(case_file["cases"])]
    ids = [str(case["id"]) for case in cases]
    if len(ids) != len(set(ids)):
        raise ContractError("case IDs must be unique")
    family_splits: dict[str, str] = {}
    for case in cases:
        family_id = str(case["family_id"])
        split = str(case["split"])
        previous = family_splits.setdefault(family_id, split)
        if previous != split:
            raise ContractError(
                f"split contamination: family_id={family_id} appears in {previous} and {split}"
            )
    present_splits = {str(case["split"]) for case in cases}
    if present_splits != SPLITS:
        raise ContractError(
            f"cases must contain train/development/test; got {sorted(present_splits)}"
        )
    return case_file


def validate_record(value: object, context: str) -> dict[str, Any]:
    record = require_exact_dict(value, RECORD_KEYS, context)
    require_string(record["case_id"], f"{context}.case_id")
    require_integer(record["trial_id"], f"{context}.trial_id", minimum=1)
    status = require_string(record["status"], f"{context}.status")
    if status not in STATUSES:
        raise ContractError(f"{context}.status must be one of {sorted(STATUSES)}")
    require_nullable_string(record["final_state"], f"{context}.final_state")
    require_unique_string_list(record["side_effects"], f"{context}.side_effects")
    require_unique_string_list(record["tools_used"], f"{context}.tools_used")
    require_number(record["latency_ms"], f"{context}.latency_ms", minimum=0.0)
    require_number(record["cost_units"], f"{context}.cost_units", minimum=0.0)
    return record


def validate_results(
    value: object, spec: dict[str, Any], case_file: dict[str, Any]
) -> dict[str, Any]:
    results = require_exact_dict(value, RESULTS_KEYS, "results")
    if require_string(results["schema_version"], "results.schema_version") != "agent-benchmark-results-v1":
        raise ContractError("results.schema_version must be agent-benchmark-results-v1")
    for key in (
        "benchmark_id",
        "benchmark_version",
        "dataset_version",
        "result_set_version",
    ):
        require_string(results[key], f"results.{key}")
    for key in ("benchmark_id", "benchmark_version"):
        if results[key] != spec[key]:
            raise ContractError(f"results.{key} does not match spec")
    if results["dataset_version"] != case_file["dataset_version"]:
        raise ContractError("results.dataset_version does not match cases.dataset_version")
    if not isinstance(results["systems"], list) or not results["systems"]:
        raise ContractError("results.systems must be a non-empty array")
    trial_count = int(spec["protocol"]["trial_count"])
    test_ids = {
        str(case["id"]) for case in case_file["cases"] if case["split"] == "test"
    }
    expected_pairs = {
        (case_id, trial_id)
        for case_id in test_ids
        for trial_id in range(1, trial_count + 1)
    }
    system_ids: list[str] = []
    roles: list[str] = []
    for system_index, system_value in enumerate(results["systems"]):
        context = f"results.systems[{system_index}]"
        system = require_exact_dict(system_value, SYSTEM_KEYS, context)
        system_ids.append(require_string(system["system_id"], f"{context}.system_id"))
        role = require_string(system["role"], f"{context}.role")
        if role not in {"baseline", "candidate"}:
            raise ContractError(f"{context}.role must be baseline or candidate")
        roles.append(role)
        validate_protocol(system["protocol"], f"{context}.protocol")
        if not isinstance(system["records"], list):
            raise ContractError(f"{context}.records must be an array")
        records = [
            validate_record(record, f"{context}.records[{record_index}]")
            for record_index, record in enumerate(system["records"])
        ]
        actual_pairs = [
            (str(record["case_id"]), int(record["trial_id"])) for record in records
        ]
        if len(actual_pairs) != len(set(actual_pairs)):
            raise ContractError(f"{context}.records contains duplicate case/trial")
        actual_set = set(actual_pairs)
        if actual_set != expected_pairs:
            missing = sorted(expected_pairs - actual_set)
            unknown = sorted(actual_set - expected_pairs)
            raise ContractError(
                f"{context}.records must exactly cover frozen private test trials; "
                f"missing={missing}, unknown={unknown}"
            )
    if len(system_ids) != len(set(system_ids)):
        raise ContractError("system IDs must be unique")
    if roles.count("baseline") != 1 or roles.count("candidate") != 1:
        raise ContractError("results must contain exactly one baseline and one candidate")
    baseline = next(system for system in results["systems"] if system["role"] == "baseline")
    if baseline["system_id"] != spec["baseline_system_id"]:
        raise ContractError("baseline system does not match spec.baseline_system_id")
    return results


def system_by_id(results: dict[str, Any], system_id: str) -> dict[str, Any]:
    for system in results["systems"]:
        if system["system_id"] == system_id:
            return system
    raise ContractError(f"system not found: {system_id}")


def normalize(text: str | None) -> str:
    return "" if text is None else " ".join(text.casefold().split())


def grade_trial(case: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    side_effects = set(str(item) for item in record["side_effects"])
    forbidden = set(str(item) for item in case["forbidden_side_effects"])
    tools_used = set(str(item) for item in record["tools_used"])
    allowed_tools = set(str(item) for item in case["allowed_tools"])
    checks = {
        "status_success": record["status"] == "success",
        "final_state_correct": normalize(record["final_state"])
        == normalize(str(case["expected_final_state"])),
        "side_effects_safe": side_effects.isdisjoint(forbidden),
        "tools_allowed": tools_used.issubset(allowed_tools),
    }
    return {
        "case_id": case["id"],
        "trial_id": record["trial_id"],
        "passed": all(checks.values()),
        "status": record["status"],
        "checks": checks,
    }


def nearest_rank(values: Iterable[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ContractError("cannot calculate a percentile for an empty sequence")
    if probability <= 0 or probability > 1:
        raise ContractError("percentile probability must be in (0, 1]")
    rank = max(1, math.ceil(probability * len(ordered)))
    return ordered[rank - 1]


def calculate_metrics(
    spec: dict[str, Any], test_cases: list[dict[str, Any]], system: dict[str, Any]
) -> dict[str, Any]:
    records = {
        (str(record["case_id"]), int(record["trial_id"])): record
        for record in system["records"]
    }
    trial_count = int(spec["protocol"]["trial_count"])
    gates = spec["gates"]
    trial_results: list[dict[str, Any]] = []
    task_results: list[dict[str, Any]] = []
    by_slice_values: dict[str, list[bool]] = {}
    by_family_values: dict[str, list[bool]] = {}
    critical_failures: list[str] = []
    for case in test_cases:
        results = [
            grade_trial(case, records[(str(case["id"]), trial_id)])
            for trial_id in range(1, trial_count + 1)
        ]
        trial_results.extend(results)
        passed_values = [bool(result["passed"]) for result in results]
        success_rate = statistics.mean(float(value) for value in passed_values)
        task_pass = success_rate >= float(gates["task_min_trial_success_rate"])
        stable = len(set(passed_values)) == 1
        task_result = {
            "case_id": case["id"],
            "family_id": case["family_id"],
            "slice": case["slice"],
            "critical": case["critical"],
            "trial_success_rate": success_rate,
            "task_pass": task_pass,
            "stable_across_trials": stable,
        }
        task_results.append(task_result)
        by_slice_values.setdefault(str(case["slice"]), []).append(task_pass)
        by_family_values.setdefault(str(case["family_id"]), []).append(task_pass)
        if case["critical"] and success_rate < float(
            gates["critical_task_min_trial_success_rate"]
        ):
            critical_failures.append(str(case["id"]))
    by_slice = {
        name: {
            "task_count": len(values),
            "task_success_rate": statistics.mean(float(value) for value in values),
        }
        for name, values in sorted(by_slice_values.items())
    }
    by_family = {
        name: {
            "task_count": len(values),
            "task_success_rate": statistics.mean(float(value) for value in values),
        }
        for name, values in sorted(by_family_values.items())
    }
    slice_rates = [float(item["task_success_rate"]) for item in by_slice.values()]
    all_records = list(records.values())
    final_state_values = [
        bool(result["checks"]["final_state_correct"]) for result in trial_results
    ]
    side_effect_values = [
        bool(result["checks"]["side_effects_safe"]) for result in trial_results
    ]
    return {
        "task_count": len(test_cases),
        "trial_count": len(trial_results),
        "primary_task_success_rate": statistics.mean(
            float(result["task_pass"]) for result in task_results
        ),
        "final_state_trial_rate": statistics.mean(float(value) for value in final_state_values),
        "side_effect_free_trial_rate": statistics.mean(
            float(value) for value in side_effect_values
        ),
        "trial_stability_rate": statistics.mean(
            float(result["stable_across_trials"]) for result in task_results
        ),
        "unknown_trial_count": sum(result["status"] == "unknown" for result in trial_results),
        "mean_latency_ms": statistics.mean(float(record["latency_ms"]) for record in all_records),
        "p95_latency_ms": nearest_rank(
            (float(record["latency_ms"]) for record in all_records), 0.95
        ),
        "mean_cost_units": statistics.mean(float(record["cost_units"]) for record in all_records),
        "slice_task_success_gap": max(slice_rates) - min(slice_rates),
        "by_slice": by_slice,
        "by_family": by_family,
        "critical_failures": critical_failures,
        "task_results": task_results,
        "trial_results": trial_results,
    }


def bootstrap_interval(
    differences: list[float], samples: int, seed: int, confidence: float
) -> tuple[float, float]:
    if not differences:
        raise ContractError("paired bootstrap requires at least one task")
    rng = random.Random(seed)
    estimates = sorted(
        statistics.mean(rng.choice(differences) for _ in differences)
        for _ in range(samples)
    )
    tail = (1.0 - confidence) / 2.0
    return nearest_rank(estimates, tail), nearest_rank(estimates, 1.0 - tail)


def fingerprint(*values: object) -> str:
    payload = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def protocol_mismatches(
    expected: dict[str, Any], actual: dict[str, Any], system_id: str
) -> list[str]:
    return [
        f"{system_id}.{key}: expected={expected[key]!r}, actual={actual[key]!r}"
        for key in sorted(PROTOCOL_KEYS)
        if actual[key] != expected[key]
    ]


def evaluate(
    spec: dict[str, Any],
    case_file: dict[str, Any],
    results: dict[str, Any],
    candidate_system_id: str,
) -> Decision:
    baseline_id = str(spec["baseline_system_id"])
    if candidate_system_id == baseline_id:
        raise ContractError("candidate system must differ from baseline")
    baseline = system_by_id(results, baseline_id)
    candidate = system_by_id(results, candidate_system_id)
    if candidate["role"] != "candidate":
        raise ContractError("selected candidate system does not have candidate role")
    evidence = fingerprint(spec, case_file, results, candidate_system_id)
    mismatches = protocol_mismatches(spec["protocol"], baseline["protocol"], baseline_id)
    mismatches.extend(
        protocol_mismatches(spec["protocol"], candidate["protocol"], candidate_system_id)
    )
    if mismatches:
        return Decision(
            action="INCOMPARABLE",
            primary_reason="run protocol does not match frozen benchmark protocol",
            reasons=tuple(mismatches),
            comparable=False,
            evidence_fingerprint=evidence,
            baseline_system=baseline_id,
            candidate_system=candidate_system_id,
            baseline_metrics=None,
            candidate_metrics=None,
            comparison={"protocol_mismatches": mismatches},
        )

    test_cases = [case for case in case_file["cases"] if case["split"] == "test"]
    baseline_metrics = calculate_metrics(spec, test_cases, baseline)
    candidate_metrics = calculate_metrics(spec, test_cases, candidate)
    baseline_tasks = {
        str(item["case_id"]): bool(item["task_pass"])
        for item in baseline_metrics["task_results"]
    }
    candidate_tasks = {
        str(item["case_id"]): bool(item["task_pass"])
        for item in candidate_metrics["task_results"]
    }
    differences = [
        float(candidate_tasks[str(case["id"])])
        - float(baseline_tasks[str(case["id"])])
        for case in test_cases
    ]
    bootstrap = spec["bootstrap"]
    low, high = bootstrap_interval(
        differences,
        int(bootstrap["samples"]),
        int(bootstrap["seed"]),
        float(bootstrap["confidence"]),
    )
    comparison = {
        "paired_task_success_delta": statistics.mean(differences),
        "paired_bootstrap_interval": [low, high],
        "confidence": bootstrap["confidence"],
        "samples": bootstrap["samples"],
        "seed": bootstrap["seed"],
        "protocol_mismatches": [],
    }

    gates = spec["gates"]
    block_reasons: list[str] = []
    review_reasons: list[str] = []
    critical_failures = list(candidate_metrics["critical_failures"])
    if critical_failures:
        block_reasons.append(
            "critical task failure(s): " + ", ".join(critical_failures)
        )
    if float(candidate_metrics["primary_task_success_rate"]) < float(
        gates["min_primary_task_success_rate"]
    ):
        block_reasons.append("primary task success rate below gate")
    if float(candidate_metrics["final_state_trial_rate"]) < float(
        gates["min_final_state_trial_rate"]
    ):
        block_reasons.append("final-state trial rate below gate")
    if float(candidate_metrics["side_effect_free_trial_rate"]) < float(
        gates["min_side_effect_free_trial_rate"]
    ):
        block_reasons.append("side-effect-free trial rate below gate")
    if float(candidate_metrics["trial_stability_rate"]) < float(
        gates["min_trial_stability_rate"]
    ):
        block_reasons.append("multi-trial stability below gate")
    if float(candidate_metrics["slice_task_success_gap"]) > float(
        gates["max_slice_task_success_gap"]
    ):
        review_reasons.append("slice task-success gap exceeds review gate")
    if float(candidate_metrics["mean_latency_ms"]) > float(
        gates["max_mean_latency_ms"]
    ):
        review_reasons.append("mean latency exceeds review gate")
    if float(candidate_metrics["p95_latency_ms"]) > float(
        gates["max_p95_latency_ms"]
    ):
        review_reasons.append("p95 latency exceeds review gate")
    if float(candidate_metrics["mean_cost_units"]) > float(
        gates["max_mean_cost_units"]
    ):
        review_reasons.append("mean cost exceeds review gate")
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
        reasons = ["all frozen benchmark gates passed"]
    return Decision(
        action=action,
        primary_reason=reasons[0],
        reasons=tuple(reasons),
        comparable=True,
        evidence_fingerprint=evidence,
        baseline_system=baseline_id,
        candidate_system=candidate_system_id,
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
        comparison=comparison,
    )


def decision_to_dict(
    decision: Decision, spec: dict[str, Any], case_file: dict[str, Any]
) -> dict[str, Any]:
    return {
        "action": decision.action,
        "primary_reason": decision.primary_reason,
        "reasons": list(decision.reasons),
        "comparable": decision.comparable,
        "evidence_fingerprint": decision.evidence_fingerprint,
        "benchmark_id": spec["benchmark_id"],
        "benchmark_version": spec["benchmark_version"],
        "dataset_version": case_file["dataset_version"],
        "baseline_system": decision.baseline_system,
        "candidate_system": decision.candidate_system,
        "baseline_metrics": decision.baseline_metrics,
        "candidate_metrics": decision.candidate_metrics,
        "comparison": decision.comparison,
        "limitations": [
            "Synthetic teaching cases do not estimate production performance.",
            "Private-test flags demonstrate a contract; these local fixtures are visible.",
            "Cost units are synthetic and are not a provider invoice.",
            "Five test tasks are too few for broad population claims.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--candidate", default="candidate-pass")
    return parser


def run(args: argparse.Namespace) -> int:
    spec = validate_spec(load_json(args.spec))
    case_file = validate_cases(load_json(args.cases), spec)
    results = validate_results(load_json(args.results), spec, case_file)
    decision = evaluate(spec, case_file, results, args.candidate)
    print(
        json.dumps(
            decision_to_dict(decision, spec, case_file),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if decision.action == "PASS" else 1


def main(argv: list[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except (OSError, UnicodeError, json.JSONDecodeError, ContractError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
