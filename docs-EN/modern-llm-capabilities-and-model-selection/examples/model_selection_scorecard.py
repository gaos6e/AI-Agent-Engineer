"""Evaluate fictional model candidates with gates before weighted scoring."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Sequence, TextIO
from urllib.parse import urlparse


DEFAULT_FIXTURE = Path(__file__).with_name("model_candidates.json")
METRIC_NAMES = (
    "task_success",
    "structured_output",
    "tool_success",
    "latency_headroom",
    "cost_headroom",
)
ROOT_FIELDS = frozenset({"version", "decision", "candidates"})
DECISION_FIELDS = frozenset(
    {
        "task",
        "as_of",
        "required_capabilities",
        "allowed_deployments",
        "require_no_training",
        "max_retention_days",
        "max_p95_latency_ms",
        "max_avg_cost_usd",
        "min_trials_per_case",
        "min_task_success_rate",
        "min_structured_output_rate",
        "min_tool_success_rate",
        "weights",
        "sensitivity_weights",
    }
)
CANDIDATE_FIELDS = frozenset(
    {
        "id",
        "evidence",
        "deployment",
        "capabilities",
        "data_policy",
        "trials",
    }
)
EVIDENCE_FIELDS = frozenset(
    {"status", "uri", "checked_on", "owner", "expires_on", "missing_items"}
)
DATA_POLICY_FIELDS = frozenset({"training_use", "retention_days"})
TRIAL_FIELDS = frozenset(
    {
        "trial_id",
        "case_id",
        "task_success",
        "structured_output_valid",
        "tool_success",
        "latency_ms",
        "cost_usd",
    }
)
SENSITIVITY_FIELDS = frozenset({"name", "weights"})
IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,63}$")


class ScorecardError(ValueError):
    """Raised when the evidence contract or decision is invalid."""


@dataclass(frozen=True)
class WeightSet:
    name: str
    values: dict[str, float]


@dataclass(frozen=True)
class Decision:
    task: str
    as_of: date
    required_capabilities: frozenset[str]
    allowed_deployments: frozenset[str]
    require_no_training: bool
    max_retention_days: int
    max_p95_latency_ms: int
    max_avg_cost_usd: float
    min_trials_per_case: int
    min_task_success_rate: float
    min_structured_output_rate: float
    min_tool_success_rate: float
    baseline_weights: WeightSet
    sensitivity_weights: tuple[WeightSet, ...]


@dataclass(frozen=True)
class DataPolicy:
    training_use: bool
    retention_days: int


@dataclass(frozen=True)
class Evidence:
    status: str
    uri: str | None
    checked_on: date
    owner: str
    expires_on: date | None
    missing_items: tuple[str, ...]


@dataclass(frozen=True)
class Trial:
    trial_id: str
    case_id: str
    task_success: bool
    structured_output_valid: bool
    tool_success: float
    latency_ms: int
    cost_usd: float


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    evidence: Evidence
    deployment: str
    capabilities: frozenset[str]
    data_policy: DataPolicy
    trials: tuple[Trial, ...]


@dataclass(frozen=True)
class Fixture:
    version: str
    decision: Decision
    candidates: tuple[Candidate, ...]


@dataclass(frozen=True)
class Metrics:
    trial_count: int
    case_count: int
    min_trials_per_case: int
    task_success: float
    structured_output: float
    tool_success: float
    p95_latency_ms: int
    avg_cost_usd: float
    latency_headroom: float
    cost_headroom: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "trial_count": self.trial_count,
            "case_count": self.case_count,
            "min_trials_per_case": self.min_trials_per_case,
            "task_success": round(self.task_success, 6),
            "structured_output": round(self.structured_output, 6),
            "tool_success": round(self.tool_success, 6),
            "p95_latency_ms": self.p95_latency_ms,
            "avg_cost_usd": round(self.avg_cost_usd, 6),
            "latency_headroom": round(self.latency_headroom, 6),
            "cost_headroom": round(self.cost_headroom, 6),
        }


def _reject_constant(value: str) -> None:
    raise ScorecardError(f"non-finite JSON number is not allowed: {value}")


def _object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ScorecardError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json_strict(text: str, context: str) -> Any:
    if not isinstance(text, str) or not text.strip():
        raise ScorecardError(f"{context} must be non-blank JSON text")
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ScorecardError(
            f"{context} is invalid JSON at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScorecardError(f"{context} must be a JSON object")
    return value


def _require_exact_fields(
    value: dict[str, Any], expected: frozenset[str], context: str
) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing={sorted(missing)}")
        if unknown:
            details.append(f"unknown={sorted(unknown)}")
        raise ScorecardError(f"{context} has invalid fields: {', '.join(details)}")


def _require_text(value: Any, context: str, *, maximum: int = 200) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScorecardError(f"{context} must be a non-blank string")
    text = value.strip()
    if len(text) > maximum:
        raise ScorecardError(f"{context} exceeds {maximum} characters")
    return text


def _require_identifier(value: Any, context: str) -> str:
    text = _require_text(value, context, maximum=64)
    if not IDENTIFIER_PATTERN.fullmatch(text):
        raise ScorecardError(f"{context} must match {IDENTIFIER_PATTERN.pattern}")
    return text


def _require_integer(
    value: Any,
    context: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ScorecardError(f"{context} must be an integer")
    if not minimum <= value <= maximum:
        raise ScorecardError(f"{context} must be between {minimum} and {maximum}")
    return value


def _require_number(
    value: Any,
    context: str,
    *,
    minimum: float,
    maximum: float,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScorecardError(f"{context} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ScorecardError(f"{context} must be finite")
    if not minimum <= result <= maximum:
        raise ScorecardError(f"{context} must be between {minimum} and {maximum}")
    return result


def _require_boolean(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        raise ScorecardError(f"{context} must be a boolean")
    return value


def _require_date(value: Any, context: str) -> date:
    text = _require_text(value, context, maximum=10)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ScorecardError(f"{context} must use YYYY-MM-DD") from exc
    if parsed.isoformat() != text:
        raise ScorecardError(f"{context} must use YYYY-MM-DD")
    return parsed


def _require_uri(value: Any, context: str) -> str:
    text = _require_text(value, context, maximum=500)
    if not urlparse(text).scheme:
        raise ScorecardError(f"{context} must be an absolute URI")
    return text


def _require_identifier_list(value: Any, context: str) -> frozenset[str]:
    if not isinstance(value, list) or not value:
        raise ScorecardError(f"{context} must be a non-empty array")
    items = [
        _require_identifier(item, f"{context}[{index}]")
        for index, item in enumerate(value)
    ]
    if len(set(items)) != len(items):
        raise ScorecardError(f"{context} values must be unique")
    return frozenset(items)


def _parse_weights(raw: Any, context: str, name: str) -> WeightSet:
    value = _require_object(raw, context)
    _require_exact_fields(value, frozenset(METRIC_NAMES), context)
    weights = {
        metric: _require_number(
            value[metric], f"{context}.{metric}", minimum=0.0, maximum=1.0
        )
        for metric in METRIC_NAMES
    }
    if not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-9):
        raise ScorecardError(f"{context} values must sum to 1")
    return WeightSet(name=name, values=weights)


def _parse_decision(raw: Any) -> Decision:
    value = _require_object(raw, "decision")
    _require_exact_fields(value, DECISION_FIELDS, "decision")
    as_of = _require_date(value["as_of"], "decision.as_of")
    sensitivity_raw = value["sensitivity_weights"]
    if not isinstance(sensitivity_raw, list) or not 1 <= len(sensitivity_raw) <= 10:
        raise ScorecardError("decision.sensitivity_weights must contain 1 to 10 entries")
    sensitivity: list[WeightSet] = []
    for index, raw_entry in enumerate(sensitivity_raw):
        context = f"decision.sensitivity_weights[{index}]"
        entry = _require_object(raw_entry, context)
        _require_exact_fields(entry, SENSITIVITY_FIELDS, context)
        name = _require_identifier(entry["name"], f"{context}.name")
        sensitivity.append(
            _parse_weights(entry["weights"], f"{context}.weights", name)
        )
    names = [item.name for item in sensitivity]
    if len(set(names)) != len(names) or "baseline" in names:
        raise ScorecardError("sensitivity weight names must be unique and not baseline")
    return Decision(
        task=_require_text(value["task"], "decision.task"),
        as_of=as_of,
        required_capabilities=_require_identifier_list(
            value["required_capabilities"], "decision.required_capabilities"
        ),
        allowed_deployments=_require_identifier_list(
            value["allowed_deployments"], "decision.allowed_deployments"
        ),
        require_no_training=_require_boolean(
            value["require_no_training"], "decision.require_no_training"
        ),
        max_retention_days=_require_integer(
            value["max_retention_days"],
            "decision.max_retention_days",
            minimum=0,
            maximum=36500,
        ),
        max_p95_latency_ms=_require_integer(
            value["max_p95_latency_ms"],
            "decision.max_p95_latency_ms",
            minimum=1,
            maximum=86_400_000,
        ),
        max_avg_cost_usd=_require_number(
            value["max_avg_cost_usd"],
            "decision.max_avg_cost_usd",
            minimum=0.000001,
            maximum=1_000_000.0,
        ),
        min_trials_per_case=_require_integer(
            value["min_trials_per_case"],
            "decision.min_trials_per_case",
            minimum=2,
            maximum=1000,
        ),
        min_task_success_rate=_require_number(
            value["min_task_success_rate"],
            "decision.min_task_success_rate",
            minimum=0.0,
            maximum=1.0,
        ),
        min_structured_output_rate=_require_number(
            value["min_structured_output_rate"],
            "decision.min_structured_output_rate",
            minimum=0.000001,
            maximum=1.0,
        ),
        min_tool_success_rate=_require_number(
            value["min_tool_success_rate"],
            "decision.min_tool_success_rate",
            minimum=0.000001,
            maximum=1.0,
        ),
        baseline_weights=_parse_weights(
            value["weights"], "decision.weights", "baseline"
        ),
        sensitivity_weights=tuple(sensitivity),
    )


def _parse_trial(raw: Any, context: str) -> Trial:
    value = _require_object(raw, context)
    _require_exact_fields(value, TRIAL_FIELDS, context)
    return Trial(
        trial_id=_require_identifier(value["trial_id"], f"{context}.trial_id"),
        case_id=_require_identifier(value["case_id"], f"{context}.case_id"),
        task_success=_require_boolean(
            value["task_success"], f"{context}.task_success"
        ),
        structured_output_valid=_require_boolean(
            value["structured_output_valid"],
            f"{context}.structured_output_valid",
        ),
        tool_success=_require_number(
            value["tool_success"],
            f"{context}.tool_success",
            minimum=0.0,
            maximum=1.0,
        ),
        latency_ms=_require_integer(
            value["latency_ms"],
            f"{context}.latency_ms",
            minimum=1,
            maximum=86_400_000,
        ),
        cost_usd=_require_number(
            value["cost_usd"],
            f"{context}.cost_usd",
            minimum=0.0,
            maximum=1_000_000.0,
        ),
    )


def _parse_evidence(raw: Any, context: str, decision: Decision) -> Evidence:
    value = _require_object(raw, context)
    _require_exact_fields(value, EVIDENCE_FIELDS, context)
    status = _require_text(value["status"], f"{context}.status", maximum=16)
    if status not in {"verified", "blocked"}:
        raise ScorecardError(f"{context}.status must be verified or blocked")
    owner = _require_identifier(value["owner"], f"{context}.owner")
    checked_on = _require_date(value["checked_on"], f"{context}.checked_on")
    if checked_on > decision.as_of:
        raise ScorecardError(f"{context}.checked_on cannot be after decision.as_of")

    missing_raw = value["missing_items"]
    if not isinstance(missing_raw, list):
        raise ScorecardError(f"{context}.missing_items must be an array")
    missing_items = tuple(
        _require_identifier(item, f"{context}.missing_items[{index}]")
        for index, item in enumerate(missing_raw)
    )
    if len(set(missing_items)) != len(missing_items):
        raise ScorecardError(f"{context}.missing_items must be unique")

    if status == "verified":
        uri = _require_uri(value["uri"], f"{context}.uri")
        expires_on = _require_date(value["expires_on"], f"{context}.expires_on")
        if expires_on < checked_on:
            raise ScorecardError(f"{context}.expires_on cannot be before checked_on")
        if missing_items:
            raise ScorecardError(
                f"{context}.verified evidence cannot contain missing_items"
            )
    else:
        if value["uri"] is not None:
            raise ScorecardError(f"{context}.blocked evidence uri must be null")
        if value["expires_on"] is not None:
            raise ScorecardError(f"{context}.blocked evidence expires_on must be null")
        if not missing_items:
            raise ScorecardError(
                f"{context}.blocked evidence requires missing_items"
            )
        uri = None
        expires_on = None

    return Evidence(
        status=status,
        uri=uri,
        checked_on=checked_on,
        owner=owner,
        expires_on=expires_on,
        missing_items=missing_items,
    )


def _parse_candidate(raw: Any, index: int, decision: Decision) -> Candidate:
    context = f"candidates[{index}]"
    value = _require_object(raw, context)
    _require_exact_fields(value, CANDIDATE_FIELDS, context)
    policy_raw = _require_object(value["data_policy"], f"{context}.data_policy")
    _require_exact_fields(policy_raw, DATA_POLICY_FIELDS, f"{context}.data_policy")
    trials_raw = value["trials"]
    if not isinstance(trials_raw, list) or not 1 <= len(trials_raw) <= 10000:
        raise ScorecardError(f"{context}.trials must contain 1 to 10000 entries")
    trials = tuple(
        _parse_trial(raw_trial, f"{context}.trials[{trial_index}]")
        for trial_index, raw_trial in enumerate(trials_raw)
    )
    trial_ids = [trial.trial_id for trial in trials]
    if len(set(trial_ids)) != len(trial_ids):
        raise ScorecardError(f"{context}.trials trial_id values must be unique")
    if "structured-output" in decision.required_capabilities:
        contradictory = [
            trial.trial_id
            for trial in trials
            if trial.task_success and not trial.structured_output_valid
        ]
        if contradictory:
            raise ScorecardError(
                f"{context}.trials cannot mark task_success=true when required "
                f"structured output is invalid: {contradictory}"
            )
    return Candidate(
        candidate_id=_require_identifier(value["id"], f"{context}.id"),
        evidence=_parse_evidence(value["evidence"], f"{context}.evidence", decision),
        deployment=_require_identifier(value["deployment"], f"{context}.deployment"),
        capabilities=_require_identifier_list(
            value["capabilities"], f"{context}.capabilities"
        ),
        data_policy=DataPolicy(
            training_use=_require_boolean(
                policy_raw["training_use"],
                f"{context}.data_policy.training_use",
            ),
            retention_days=_require_integer(
                policy_raw["retention_days"],
                f"{context}.data_policy.retention_days",
                minimum=0,
                maximum=36500,
            ),
        ),
        trials=trials,
    )


def load_fixture(path: Path) -> Fixture:
    if not path.is_file():
        raise ScorecardError(f"fixture does not exist: {path}")
    root = _require_object(
        parse_json_strict(path.read_text(encoding="utf-8"), str(path)), "root"
    )
    _require_exact_fields(root, ROOT_FIELDS, "root")
    version = _require_identifier(root["version"], "version")
    decision = _parse_decision(root["decision"])
    candidates_raw = root["candidates"]
    if not isinstance(candidates_raw, list) or not 2 <= len(candidates_raw) <= 50:
        raise ScorecardError("candidates must contain 2 to 50 entries")
    candidates = tuple(
        _parse_candidate(raw, index, decision)
        for index, raw in enumerate(candidates_raw)
    )
    candidate_ids = [candidate.candidate_id for candidate in candidates]
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ScorecardError("candidate ids must be unique")
    all_trial_ids = [
        trial.trial_id for candidate in candidates for trial in candidate.trials
    ]
    if len(set(all_trial_ids)) != len(all_trial_ids):
        raise ScorecardError("trial_id values must be globally unique")
    expected_case_counts = Counter(
        trial.case_id for trial in candidates[0].trials
    )
    for candidate in candidates[1:]:
        actual_case_counts = Counter(trial.case_id for trial in candidate.trials)
        if actual_case_counts != expected_case_counts:
            raise ScorecardError(
                "all candidates must use the same case_id multiplicities; "
                f"{candidate.candidate_id} differs"
            )
    return Fixture(version=version, decision=decision, candidates=candidates)


def _nearest_rank_p95(values: Sequence[int]) -> int:
    if not values:
        raise ScorecardError("cannot compute p95 from no values")
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def aggregate_metrics(candidate: Candidate, decision: Decision) -> Metrics:
    count = len(candidate.trials)
    case_counts = Counter(trial.case_id for trial in candidate.trials)
    task_success = sum(trial.task_success for trial in candidate.trials) / count
    structured_output = (
        sum(trial.structured_output_valid for trial in candidate.trials) / count
    )
    tool_success = sum(trial.tool_success for trial in candidate.trials) / count
    p95_latency_ms = _nearest_rank_p95(
        [trial.latency_ms for trial in candidate.trials]
    )
    avg_cost_usd = sum(trial.cost_usd for trial in candidate.trials) / count
    return Metrics(
        trial_count=count,
        case_count=len(case_counts),
        min_trials_per_case=min(case_counts.values()),
        task_success=task_success,
        structured_output=structured_output,
        tool_success=tool_success,
        p95_latency_ms=p95_latency_ms,
        avg_cost_usd=avg_cost_usd,
        latency_headroom=max(
            0.0, 1.0 - p95_latency_ms / decision.max_p95_latency_ms
        ),
        cost_headroom=max(
            0.0, 1.0 - avg_cost_usd / decision.max_avg_cost_usd
        ),
    )


def gate_failures(
    candidate: Candidate, metrics: Metrics, decision: Decision
) -> tuple[str, ...]:
    failures: list[str] = []
    if candidate.evidence.status == "blocked":
        failures.append("evidence_status_blocked")
        failures.extend(
            f"evidence_missing:{item}"
            for item in sorted(candidate.evidence.missing_items)
        )
    elif (
        candidate.evidence.expires_on is not None
        and candidate.evidence.expires_on < decision.as_of
    ):
        failures.append("evidence_expired")
    for capability in sorted(decision.required_capabilities - candidate.capabilities):
        failures.append(f"missing_capability:{capability}")
    if candidate.deployment not in decision.allowed_deployments:
        failures.append("deployment_not_allowed")
    if decision.require_no_training and candidate.data_policy.training_use:
        failures.append("training_use_not_allowed")
    if candidate.data_policy.retention_days > decision.max_retention_days:
        failures.append("retention_exceeds_limit")
    case_counts = Counter(trial.case_id for trial in candidate.trials)
    for case_id in sorted(case_counts):
        if case_counts[case_id] < decision.min_trials_per_case:
            failures.append(f"insufficient_trials_per_case:{case_id}")
    if metrics.task_success < decision.min_task_success_rate:
        failures.append("task_success_below_minimum")
    if (
        "structured-output" in decision.required_capabilities
        and metrics.structured_output < decision.min_structured_output_rate
    ):
        failures.append("structured_output_below_minimum")
    if (
        "tool-calling" in decision.required_capabilities
        and metrics.tool_success < decision.min_tool_success_rate
    ):
        failures.append("tool_success_below_minimum")
    if metrics.p95_latency_ms > decision.max_p95_latency_ms:
        failures.append("p95_latency_exceeds_limit")
    if metrics.avg_cost_usd > decision.max_avg_cost_usd:
        failures.append("average_cost_exceeds_limit")
    return tuple(failures)


def weighted_score(metrics: Metrics, weights: WeightSet) -> float:
    utility = {
        "task_success": metrics.task_success,
        "structured_output": metrics.structured_output,
        "tool_success": metrics.tool_success,
        "latency_headroom": metrics.latency_headroom,
        "cost_headroom": metrics.cost_headroom,
    }
    return sum(utility[name] * weights.values[name] for name in METRIC_NAMES)


def _dominates(left: Metrics, right: Metrics) -> bool:
    comparisons = (
        left.task_success >= right.task_success,
        left.structured_output >= right.structured_output,
        left.tool_success >= right.tool_success,
        left.p95_latency_ms <= right.p95_latency_ms,
        left.avg_cost_usd <= right.avg_cost_usd,
    )
    strict = (
        left.task_success > right.task_success
        or left.structured_output > right.structured_output
        or left.tool_success > right.tool_success
        or left.p95_latency_ms < right.p95_latency_ms
        or left.avg_cost_usd < right.avg_cost_usd
    )
    return all(comparisons) and strict


def pareto_frontier(metrics_by_id: dict[str, Metrics]) -> list[str]:
    frontier: list[str] = []
    for candidate_id in sorted(metrics_by_id):
        dominated = any(
            other_id != candidate_id
            and _dominates(other_metrics, metrics_by_id[candidate_id])
            for other_id, other_metrics in metrics_by_id.items()
        )
        if not dominated:
            frontier.append(candidate_id)
    return frontier


def evaluate(fixture: Fixture) -> dict[str, Any]:
    decision = fixture.decision
    all_metrics = {
        candidate.candidate_id: aggregate_metrics(candidate, decision)
        for candidate in fixture.candidates
    }
    ineligible: list[dict[str, Any]] = []
    eligible_metrics: dict[str, Metrics] = {}
    for candidate in sorted(fixture.candidates, key=lambda item: item.candidate_id):
        metrics = all_metrics[candidate.candidate_id]
        failures = gate_failures(candidate, metrics, decision)
        if failures:
            ineligible.append(
                {
                    "id": candidate.candidate_id,
                    "gate_failures": list(failures),
                    "metrics": metrics.as_dict(),
                }
            )
        else:
            eligible_metrics[candidate.candidate_id] = metrics

    weight_sets = (decision.baseline_weights,) + decision.sensitivity_weights
    rankings: list[dict[str, Any]] = []
    for weights in weight_sets:
        scored = [
            {
                "id": candidate_id,
                "score": round(weighted_score(metrics, weights), 6),
            }
            for candidate_id, metrics in eligible_metrics.items()
        ]
        scored.sort(key=lambda item: (-item["score"], item["id"]))
        rankings.append(
            {
                "name": weights.name,
                "weights": dict(weights.values),
                "ranking": scored,
            }
        )

    baseline_scores = {
        item["id"]: item["score"] for item in rankings[0]["ranking"]
    }
    frontier = set(pareto_frontier(eligible_metrics))
    eligible = [
        {
            "id": candidate_id,
            "score": baseline_scores[candidate_id],
            "pareto": candidate_id in frontier,
            "metrics": eligible_metrics[candidate_id].as_dict(),
        }
        for candidate_id in sorted(eligible_metrics)
    ]
    winners = [
        ranking["ranking"][0]["id"]
        for ranking in rankings
        if ranking["ranking"]
    ]
    winner_stable = bool(winners) and len(winners) == len(rankings) and len(set(winners)) == 1
    return {
        "fixture_version": fixture.version,
        "task": decision.task,
        "as_of": decision.as_of.isoformat(),
        "decision_order": [
            "strict_input",
            "hard_gates",
            "eligible_only_weighted_score",
            "pareto_frontier",
            "declared_weight_scenarios",
        ],
        "eligible": eligible,
        "ineligible": ineligible,
        "pareto_frontier": sorted(frontier),
        "sensitivity": rankings,
        "sensitivity_scope": "declared_weight_sets_only",
        "winner_stable_across_declared_weights": winner_stable,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply hard gates before scoring fictional model candidates."
    )
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--json-output", type=Path)
    return parser


def run(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = evaluate(load_fixture(args.fixture))
        rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        print(rendered, file=stdout)
        if args.json_output is not None:
            args.json_output.parent.mkdir(parents=True, exist_ok=True)
            args.json_output.write_text(rendered + "\n", encoding="utf-8")
        return 0
    except (OSError, ScorecardError) as exc:
        print(f"scorecard error: {exc}", file=stderr)
        return 2


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
