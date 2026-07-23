"""Offline LLMOps release and online-observation gate: reads local JSON only and calls no external API."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST = BASE_DIR / "release_candidates.json"
DEFAULT_OBSERVATIONS = BASE_DIR / "online_observations.json"
EVIDENCE_DIGEST_FORMAT = "python-json-sorted-utf8-v1"
ONLINE_OBSERVATION_SCHEMA_VERSION = "local-online-observation-v6"
ONLINE_OBSERVATION_GATE_VERSION = "online-observation-gate-v4"
MUTABLE_MARKERS = {
    "latest",
    "current",
    "production",
    "champion",
    "main",
    "master",
    "head",
}
FLOATING_LATEST_PATTERN = re.compile(r"(?:^|[:/@._-])latest$", re.IGNORECASE)
FLOATING_BRANCH_PATTERN = re.compile(
    r"^(?:refs/heads/.+|refs/remotes/[^/]+/.+|(?:origin|upstream)/.+)$",
    re.IGNORECASE,
)


class ContractError(ValueError):
    """Input JSON does not satisfy this project's strict contract."""


def reject_non_utf8_scalar_strings(value: object, context: str) -> None:
    """Reject strings that cannot participate in deterministic UTF-8 evidence bytes."""
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ContractError(
                f"{context} contains a Unicode surrogate that cannot serve as normalized UTF-8 input"
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


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        reject_non_utf8_scalar_strings(key, "JSON field name")
        if key in result:
            raise ContractError(f"JSON contains duplicate field: {key}")
        result[key] = value
    return result


@dataclass(frozen=True)
class Decision:
    """One gate decision; empty reasons mean it may continue."""

    subject_id: str
    action: str
    reasons: tuple[str, ...]
    evidence_fingerprint: str
    evidence_sha256: str
    evidence_digest_format: str = EVIDENCE_DIGEST_FORMAT

    @property
    def passed(self) -> bool:
        return self.action in {"promote", "continue"}


def load_json(path: Path) -> dict[str, Any]:
    """Read a JSON object as UTF-8."""
    def reject_nonstandard_number(value: str) -> None:
        raise ContractError(f"{path.name} contains a number outside the JSON standard: {value}")

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(
                handle,
                object_pairs_hook=reject_duplicate_keys,
                parse_constant=reject_nonstandard_number,
            )
    except UnicodeDecodeError as exc:
        raise ContractError(f"{path.name} must be valid UTF-8 JSON") from exc
    if not isinstance(data, dict):
        raise ContractError(f"{path.name} top level must be an object")
    reject_non_utf8_scalar_strings(data, path.name)
    return data


def full_evidence_sha256(*values: object) -> str:
    """Generate this project's versioned, local evidence identifier.

    The format label names the exact Python byte representation; it is not a
    cross-language canonical JSON or authenticity mechanism.
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
            "evidence must be a finite JSON value serializable in this project's UTF-8 format"
        ) from exc
    return hashlib.sha256(encoded).hexdigest()


def fingerprint(*values: object) -> str:
    """Return a display-only prefix of the durable evidence identifier."""
    return full_evidence_sha256(*values)[:16]


def require_exact_keys(
    value: object,
    required: set[str],
    context: str,
    optional: set[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{context} must be an object")
    optional = optional or set()
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        raise ContractError(f"{context} is missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise ContractError(f"{context} contains unknown fields: {', '.join(sorted(extra))}")
    return value


def require_list(value: object, context: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise ContractError(f"{context} must be a non-empty array")
    return value


def require_bool(value: object, context: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(f"{context} must be a Boolean")
    return value


def require_number(
    value: object,
    context: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{context} must be numeric")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ContractError(f"{context} must be representable as a finite number") from exc
    if not math.isfinite(number):
        raise ContractError(f"{context} must be finite")
    if minimum is not None and number < minimum:
        raise ContractError(f"{context} must be at least {minimum}")
    if maximum is not None and number > maximum:
        raise ContractError(f"{context} must be at most {maximum}")
    return number


def require_integer(value: object, context: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{context} must be an integer")
    if value < minimum:
        raise ContractError(f"{context} must be at least {minimum}")
    return value


def is_fixed_identifier(value: object) -> bool:
    """Teaching check: rejects empty values and common floating aliases; it does not replace provider-contract verification."""
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    if not normalized or normalized.lower() in MUTABLE_MARKERS:
        return False
    if FLOATING_LATEST_PATTERN.search(normalized) is not None:
        return False
    return FLOATING_BRANCH_PATTERN.fullmatch(normalized) is None


def require_fixed(value: object, context: str) -> str:
    if not is_fixed_identifier(value):
        raise ContractError(f"{context} must be a non-empty, non-floating identifier; got={value!r}")
    return str(value)


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SHORT_FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{16}$")
RFC3339_DATETIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$"
)


def require_sha256(value: object, context: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise ContractError(f"{context} must be a 64-character lowercase hexadecimal SHA-256")
    return value


def require_evidence_digest_format(value: object, context: str) -> str:
    if value != EVIDENCE_DIGEST_FORMAT:
        raise ContractError(
            f"{context} must use supported evidence digest format "
            f"{EVIDENCE_DIGEST_FORMAT!r}"
        )
    return EVIDENCE_DIGEST_FORMAT


def require_short_fingerprint(value: object, context: str) -> str:
    if not isinstance(value, str) or SHORT_FINGERPRINT_PATTERN.fullmatch(value) is None:
        raise ContractError(f"{context} must be a 16-character lowercase hexadecimal evidence fingerprint")
    return value


def require_utc_timestamp(value: object, context: str) -> datetime:
    if not isinstance(value, str) or RFC3339_DATETIME_PATTERN.fullmatch(value) is None:
        raise ContractError(
            f"{context} must be an RFC 3339 UTC datetime (Z or +00:00)"
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{context} is not a valid RFC 3339 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ContractError(f"{context} must use UTC timezone (Z or +00:00)")
    return parsed


POLICY_KEYS = {
    "version",
    "decision_as_of",
    "required_tests",
    "min_task_success_delta",
    "min_critical_success_delta",
    "max_safety_violation_rate",
    "min_safety_samples",
    "max_latency_increase_ratio",
    "max_cost_increase_ratio",
    "human_approval_required",
    "online_min_eligible_samples",
    "online_min_label_coverage",
    "online_min_critical_labeled_samples",
    "online_min_safety_checked_samples",
    "online_max_label_age_hours",
    "online_max_task_drop",
    "online_max_critical_drop",
    "online_max_provider_error_rate",
    "online_max_provider_shift_score",
    "online_max_latency_increase_ratio",
    "online_max_cost_increase_ratio",
}
EVALUATION_KEYS = {
    "subject_release_id",
    "suite_version",
    "dataset_version",
    "rubric_version",
    "grader_version",
    "harness_version",
    "artifact_sha256",
    "artifact_digest_format",
}
EVALUATION_COMPARISON_KEYS = {
    "suite_version",
    "dataset_version",
    "rubric_version",
    "grader_version",
    "harness_version",
}
METRIC_KEYS = {
    "task_success_rate",
    "critical_slice_success_rate",
    "safety_violation_rate",
    "safety_sample_count",
    "p95_latency_ms",
    "estimated_cost_usd_per_1k_requests",
}
CANDIDATE_KEYS = {
    "release_id",
    "gate_decided_at",
    "promoted_at",
    "app",
    "api",
    "prompt",
    "context",
    "retrieval",
    "model",
    "tools",
    "policies",
    "evaluation",
    "routing",
    "pricing",
    "tests",
    "metrics",
    "operations",
}
OBSERVATION_KEYS = {
    "observation_id",
    "candidate_gate_fingerprint",
    "candidate_gate_evidence_sha256",
    "window_id",
    "window_start",
    "window_end",
    "assignment_revision",
    "population_revision",
    "candidate",
    "control",
    "provider_error_rate",
    "provider_output_shift_score",
    "trace_schema_complete",
    "redaction_check_passed",
    "fallback_evidence",
}
FALLBACK_MANIFEST_KEYS = {
    "release_id",
    "manifest_sha256",
    "gate_evidence_sha256",
}
ONLINE_ARM_KEYS = {
    "release_id",
    "eligible_count",
    "labeled_count",
    "critical_labeled_count",
    "safety_checked_count",
    "task_success_count",
    "critical_slice_success_count",
    "safety_violation_count",
    "max_label_age_hours",
    "p95_latency_ms",
    "actual_cost_usd_per_1k_requests",
}


def validate_policy(value: object) -> dict[str, Any]:
    policy = require_exact_keys(value, POLICY_KEYS, "policy")
    require_fixed(policy["version"], "policy.version")
    require_utc_timestamp(policy["decision_as_of"], "policy.decision_as_of")
    tests = require_list(policy["required_tests"], "policy.required_tests")
    if any(not is_fixed_identifier(item) for item in tests):
        raise ContractError("policy.required_tests may contain only non-empty fixed names")
    for key in ("min_task_success_delta", "min_critical_success_delta"):
        require_number(policy[key], f"policy.{key}", minimum=-1, maximum=1)
    for key in (
        "max_safety_violation_rate",
        "max_latency_increase_ratio",
        "max_cost_increase_ratio",
        "online_max_task_drop",
        "online_max_critical_drop",
        "online_max_provider_error_rate",
        "online_max_provider_shift_score",
        "online_max_latency_increase_ratio",
        "online_max_cost_increase_ratio",
    ):
        require_number(policy[key], f"policy.{key}", minimum=0, maximum=1)
    require_number(
        policy["online_max_label_age_hours"],
        "policy.online_max_label_age_hours",
        minimum=0,
    )
    require_number(
        policy["online_min_label_coverage"],
        "policy.online_min_label_coverage",
        minimum=0,
        maximum=1,
    )
    for key in (
        "min_safety_samples",
        "online_min_eligible_samples",
        "online_min_critical_labeled_samples",
        "online_min_safety_checked_samples",
    ):
        require_integer(policy[key], f"policy.{key}", minimum=1)
    require_bool(policy["human_approval_required"], "policy.human_approval_required")
    return policy


def validate_metrics(value: object, context: str) -> dict[str, Any]:
    metrics = require_exact_keys(value, METRIC_KEYS, context)
    for key in (
        "task_success_rate",
        "critical_slice_success_rate",
        "safety_violation_rate",
    ):
        require_number(metrics[key], f"{context}.{key}", minimum=0, maximum=1)
    for key in (
        "p95_latency_ms",
        "estimated_cost_usd_per_1k_requests",
    ):
        require_number(metrics[key], f"{context}.{key}", minimum=0)
    require_integer(metrics["safety_sample_count"], f"{context}.safety_sample_count")
    return metrics


def validate_evaluation(
    value: object, context: str, expected_release_id: str
) -> dict[str, Any]:
    evaluation = require_exact_keys(value, EVALUATION_KEYS, context)
    for key in EVALUATION_COMPARISON_KEYS | {"subject_release_id"}:
        require_fixed(evaluation[key], f"{context}.{key}")
    if evaluation["subject_release_id"] != expected_release_id:
        raise ContractError(
            f"{context}.subject_release_id must bind its owning release_id={expected_release_id}"
        )
    require_sha256(evaluation["artifact_sha256"], f"{context}.artifact_sha256")
    require_evidence_digest_format(
        evaluation["artifact_digest_format"], f"{context}.artifact_digest_format"
    )
    return evaluation


def validate_fallback_manifest(value: object, context: str) -> dict[str, Any]:
    """Validate the immutable identity declared for a pre-gated fallback release."""
    fallback = require_exact_keys(value, FALLBACK_MANIFEST_KEYS, context)
    require_fixed(fallback["release_id"], f"{context}.release_id")
    require_sha256(fallback["manifest_sha256"], f"{context}.manifest_sha256")
    require_sha256(
        fallback["gate_evidence_sha256"],
        f"{context}.gate_evidence_sha256",
    )
    return fallback


def validate_candidate(
    value: object, index: int, decision_as_of: datetime
) -> dict[str, Any]:
    context = f"candidates[{index}]"
    candidate = require_exact_keys(value, CANDIDATE_KEYS, context)
    require_fixed(candidate["release_id"], f"{context}.release_id")
    gate_decided_at = require_utc_timestamp(
        candidate["gate_decided_at"], f"{context}.gate_decided_at"
    )
    if gate_decided_at > decision_as_of:
        raise ContractError(
            f"{context}.gate_decided_at must not be later than policy.decision_as_of"
        )
    promoted_at_value = candidate["promoted_at"]
    if promoted_at_value is not None:
        promoted_at = require_utc_timestamp(
            promoted_at_value, f"{context}.promoted_at"
        )
        if promoted_at < gate_decided_at:
            raise ContractError(
                f"{context}.promoted_at must not be earlier than gate_decided_at"
            )
        if promoted_at > decision_as_of:
            raise ContractError(
                f"{context}.promoted_at must not be later than policy.decision_as_of"
            )

    nested_specs: tuple[tuple[str, set[str]], ...] = (
        ("app", {"commit"}),
        ("api", {"contract_version", "sdk_lock_hash"}),
        ("prompt", {"version", "digest"}),
        ("context", {"policy_version"}),
        ("retrieval", {"snapshot", "config_version"}),
        ("model", {"provider", "model_snapshot", "parameters_version"}),
        ("policies", {"guardrail_version", "data_handling_version"}),
        ("pricing", {"policy_version"}),
    )
    for name, keys in nested_specs:
        item = require_exact_keys(candidate[name], keys, f"{context}.{name}")
        for key in keys:
            require_fixed(item[key], f"{context}.{name}.{key}")

    routing = require_exact_keys(
        candidate["routing"],
        {"policy_version", "fallback_manifest"},
        f"{context}.routing",
    )
    require_fixed(routing["policy_version"], f"{context}.routing.policy_version")
    validate_fallback_manifest(
        routing["fallback_manifest"], f"{context}.routing.fallback_manifest"
    )

    validate_evaluation(
        candidate["evaluation"],
        f"{context}.evaluation",
        str(candidate["release_id"]),
    )

    tools = require_list(candidate["tools"], f"{context}.tools")
    tool_names: set[str] = set()
    for tool_index, tool_value in enumerate(tools):
        tool = require_exact_keys(
            tool_value,
            {"name", "schema_version", "implementation_version"},
            f"{context}.tools[{tool_index}]",
        )
        for key in tool:
            require_fixed(tool[key], f"{context}.tools[{tool_index}].{key}")
        tool_name = str(tool["name"])
        if tool_name in tool_names:
            raise ContractError(f"{context}.tools contains duplicate name: {tool_name}")
        tool_names.add(tool_name)

    tests = require_exact_keys(
        candidate["tests"],
        {"schema_contract", "retrieval_regression", "tool_contract", "output_policy"},
        f"{context}.tests",
    )
    for name, result in tests.items():
        require_bool(result, f"{context}.tests.{name}")

    validate_metrics(candidate["metrics"], f"{context}.metrics")
    operations = require_exact_keys(
        candidate["operations"],
        {
            "trace_schema_complete",
            "redaction_check_passed",
            "canary_plan_ready",
            "rollback_manifest_ready",
            "human_approval_recorded",
        },
        f"{context}.operations",
    )
    for name, result in operations.items():
        require_bool(result, f"{context}.operations.{name}")
    return candidate


def validate_manifest(value: object) -> dict[str, Any]:
    manifest = require_exact_keys(value, {"policy", "baseline", "candidates"}, "manifest")
    policy = validate_policy(manifest["policy"])
    decision_as_of = require_utc_timestamp(
        policy["decision_as_of"], "policy.decision_as_of"
    )
    baseline = require_exact_keys(
        manifest["baseline"], {"release_id", "evaluation", "metrics"}, "baseline"
    )
    require_fixed(baseline["release_id"], "baseline.release_id")
    validate_evaluation(
        baseline["evaluation"], "baseline.evaluation", str(baseline["release_id"])
    )
    validate_metrics(baseline["metrics"], "baseline.metrics")
    candidates = require_list(manifest["candidates"], "candidates")
    seen: set[str] = {str(baseline["release_id"])}
    candidates_by_id: dict[str, dict[str, Any]] = {}
    for index, candidate_value in enumerate(candidates):
        candidate = validate_candidate(candidate_value, index, decision_as_of)
        release_id = str(candidate["release_id"])
        if release_id in seen:
            raise ContractError(f"duplicate release_id: {release_id}")
        seen.add(release_id)
        candidates_by_id[release_id] = candidate

    for candidate in candidates:
        release_id = str(candidate["release_id"])
        fallback_release_id = str(
            candidate["routing"]["fallback_manifest"]["release_id"]
        )
        if fallback_release_id == release_id:
            raise ContractError(
                f"candidate {release_id} fallback release must not point to itself"
            )
        known_fallback = candidates_by_id.get(fallback_release_id)
        if known_fallback is None:
            continue
        fallback_gate = candidate_decision(known_fallback, baseline, policy)
        if not fallback_gate.passed:
            raise ContractError(
                f"candidate {release_id} known fallback release "
                f"{fallback_release_id} did not pass the candidate gate"
            )
        fallback_promoted_at = known_fallback["promoted_at"]
        if fallback_promoted_at is None:
            raise ContractError(
                f"candidate {release_id} known fallback release "
                f"{fallback_release_id} is not yet promoted"
            )
        candidate_promoted_at = candidate["promoted_at"]
        if candidate_promoted_at is not None and require_utc_timestamp(
            fallback_promoted_at,
            f"candidate {fallback_release_id}.promoted_at",
        ) > require_utc_timestamp(
            candidate_promoted_at,
            f"candidate {release_id}.promoted_at",
        ):
            raise ContractError(
                f"candidate {release_id} known fallback release "
                f"{fallback_release_id} must be promoted first"
            )

    for candidate in candidates:
        origin = str(candidate["release_id"])
        visited: set[str] = set()
        current = origin
        while current in candidates_by_id:
            if current in visited:
                raise ContractError(
                    f"candidate {origin} known fallback release chain forms a cycle"
                )
            visited.add(current)
            current = str(
                candidates_by_id[current]["routing"]["fallback_manifest"][
                    "release_id"
                ]
            )
    return manifest


def validate_online_arm(value: object, context: str) -> dict[str, Any]:
    arm = require_exact_keys(value, ONLINE_ARM_KEYS, context)
    require_fixed(arm["release_id"], f"{context}.release_id")
    for key in (
        "eligible_count",
        "labeled_count",
        "critical_labeled_count",
        "safety_checked_count",
        "task_success_count",
        "critical_slice_success_count",
        "safety_violation_count",
    ):
        require_integer(arm[key], f"{context}.{key}")
    if arm["labeled_count"] > arm["eligible_count"]:
        raise ContractError(f"{context}.labeled_count must not exceed eligible_count")
    if arm["critical_labeled_count"] > arm["labeled_count"]:
        raise ContractError(f"{context}.critical_labeled_count must not exceed labeled_count")
    if arm["safety_checked_count"] > arm["eligible_count"]:
        raise ContractError(f"{context}.safety_checked_count must not exceed eligible_count")
    if arm["task_success_count"] > arm["labeled_count"]:
        raise ContractError(f"{context}.task_success_count must not exceed labeled_count")
    if arm["critical_slice_success_count"] > arm["critical_labeled_count"]:
        raise ContractError(
            f"{context}.critical_slice_success_count must not exceed critical_labeled_count"
        )
    if arm["safety_violation_count"] > arm["safety_checked_count"]:
        raise ContractError(
            f"{context}.safety_violation_count must not exceed safety_checked_count"
        )
    for key in (
        "max_label_age_hours",
        "p95_latency_ms",
        "actual_cost_usd_per_1k_requests",
    ):
        require_number(arm[key], f"{context}.{key}", minimum=0)
    return arm


def online_arm_rates(arm: dict[str, Any]) -> dict[str, float | None]:
    """Derive comparable rates from auditable numerator/denominator pairs.

    A zero denominator means the corresponding state is unknown, not a zero
    failure rate.  The caller must keep its coverage gate separate from the
    rate comparison.
    """

    def rate(numerator: str, denominator: str) -> float | None:
        total = int(arm[denominator])
        return int(arm[numerator]) / total if total else None

    return {
        "task_success_rate": rate("task_success_count", "labeled_count"),
        "critical_slice_success_rate": rate(
            "critical_slice_success_count", "critical_labeled_count"
        ),
        "safety_violation_rate": rate(
            "safety_violation_count", "safety_checked_count"
        ),
    }


def validate_observation_bundle_metadata(
    schema_version: object, evidence_digest_format: object
) -> dict[str, str]:
    if schema_version != ONLINE_OBSERVATION_SCHEMA_VERSION:
        raise ContractError(
            "observations.schema_version must be "
            f"{ONLINE_OBSERVATION_SCHEMA_VERSION}"
        )
    return {
        "schema_version": ONLINE_OBSERVATION_SCHEMA_VERSION,
        "evidence_digest_format": require_evidence_digest_format(
            evidence_digest_format, "observations.evidence_digest_format"
        ),
    }


def validate_observations(value: object) -> dict[str, Any]:
    bundle = require_exact_keys(
        value,
        {"schema_version", "evidence_digest_format", "observations"},
        "observations",
    )
    validate_observation_bundle_metadata(
        bundle["schema_version"], bundle["evidence_digest_format"]
    )
    observations = require_list(bundle["observations"], "observations.observations")
    seen: set[str] = set()
    for index, item_value in enumerate(observations):
        context = f"observations[{index}]"
        item = require_exact_keys(item_value, OBSERVATION_KEYS, context)
        for key in (
            "observation_id",
            "window_id",
            "assignment_revision",
            "population_revision",
        ):
            require_fixed(item[key], f"{context}.{key}")
        require_short_fingerprint(
            item["candidate_gate_fingerprint"],
            f"{context}.candidate_gate_fingerprint",
        )
        require_sha256(
            item["candidate_gate_evidence_sha256"],
            f"{context}.candidate_gate_evidence_sha256",
        )
        window_start = require_utc_timestamp(item["window_start"], f"{context}.window_start")
        window_end = require_utc_timestamp(item["window_end"], f"{context}.window_end")
        if window_end <= window_start:
            raise ContractError(f"{context} must satisfy window_start < window_end")
        candidate = validate_online_arm(item["candidate"], f"{context}.candidate")
        control = validate_online_arm(item["control"], f"{context}.control")
        if candidate["release_id"] == control["release_id"]:
            raise ContractError(f"{context} candidate/control releases must differ")
        for key in (
            "provider_error_rate",
            "provider_output_shift_score",
        ):
            require_number(item[key], f"{context}.{key}", minimum=0, maximum=1)
        for key in ("trace_schema_complete", "redaction_check_passed"):
            require_bool(item[key], f"{context}.{key}")
        fallback_evidence = item["fallback_evidence"]
        if fallback_evidence is not None:
            validate_fallback_manifest(
                fallback_evidence, f"{context}.fallback_evidence"
            )
        observation_id = str(item["observation_id"])
        if observation_id in seen:
            raise ContractError(f"duplicate observation_id: {observation_id}")
        seen.add(observation_id)
    return bundle


def candidate_gate_material(candidate: dict[str, Any]) -> dict[str, Any]:
    """Project a candidate onto the material available when its gate is decided.

    ``promoted_at`` is control-plane history written only after a successful
    decision.  Including it in a gate digest would make the already approved
    evidence change merely because rollout state advanced, and would break
    valid observation binding.  It remains independently validated before an
    observation window is accepted.
    """
    return {
        key: value
        for key, value in candidate.items()
        if key != "promoted_at"
    }


def candidate_decision(
    candidate: dict[str, Any], baseline: dict[str, Any], policy: dict[str, Any]
) -> Decision:
    """Decide whether a candidate may enter Canary using contract-validated evidence."""
    evidence_sha256 = full_evidence_sha256(
        "candidate-gate-v2", candidate_gate_material(candidate), baseline, policy
    )
    comparison_mismatches = sorted(
        key
        for key in EVALUATION_COMPARISON_KEYS
        if candidate["evaluation"][key] != baseline["evaluation"][key]
    )
    if comparison_mismatches:
        return Decision(
            subject_id=str(candidate["release_id"]),
            action="incomparable",
            reasons=tuple(
                f"evaluation comparison contract differs: {key}" for key in comparison_mismatches
            ),
            evidence_fingerprint=evidence_sha256[:16],
            evidence_sha256=evidence_sha256,
        )

    reasons: list[str] = []
    for test_name in policy["required_tests"]:
        if candidate["tests"].get(test_name) is not True:
            reasons.append(f"required test failed: {test_name}")

    metrics = candidate["metrics"]
    baseline_metrics = baseline["metrics"]
    minimum_task = float(baseline_metrics["task_success_rate"]) + float(
        policy["min_task_success_delta"]
    )
    minimum_critical = float(baseline_metrics["critical_slice_success_rate"]) + float(
        policy["min_critical_success_delta"]
    )
    maximum_latency = float(baseline_metrics["p95_latency_ms"]) * (
        1 + float(policy["max_latency_increase_ratio"])
    )
    maximum_cost = float(baseline_metrics["estimated_cost_usd_per_1k_requests"]) * (
        1 + float(policy["max_cost_increase_ratio"])
    )

    checks = (
        (float(metrics["task_success_rate"]) < minimum_task, f"task-success rate is below {minimum_task:.3f}"),
        (
            float(metrics["critical_slice_success_rate"]) < minimum_critical,
            f"critical-slice success rate is below {minimum_critical:.3f}",
        ),
        (
            float(metrics["safety_violation_rate"]) > float(policy["max_safety_violation_rate"]),
            "safety-violation rate exceeds the policy limit",
        ),
        (
            int(metrics["safety_sample_count"]) < int(policy["min_safety_samples"]),
            "insufficient safety-slice sample count",
        ),
        (float(metrics["p95_latency_ms"]) > maximum_latency, f"P95 latency exceeds {maximum_latency:.0f}ms"),
        (
            float(metrics["estimated_cost_usd_per_1k_requests"]) > maximum_cost,
            f"estimated cost exceeds the local practice limit of {maximum_cost:.2f} USD per 1,000 requests",
        ),
    )
    reasons.extend(message for failed, message in checks if failed)

    operations = candidate["operations"]
    operation_messages = {
        "trace_schema_complete": "Trace schema is incomplete",
        "redaction_check_passed": "redaction check failed",
        "canary_plan_ready": "Canary plan is not ready",
        "rollback_manifest_ready": "rollback manifest is not ready",
    }
    for key, message in operation_messages.items():
        if operations[key] is not True:
            reasons.append(message)
    if policy["human_approval_required"] and not operations["human_approval_recorded"]:
        reasons.append("high-risk release lacks a human-approval record")

    return Decision(
        subject_id=str(candidate["release_id"]),
        action="block" if reasons else "promote",
        reasons=tuple(reasons),
        evidence_fingerprint=evidence_sha256[:16],
        evidence_sha256=evidence_sha256,
    )


def observation_decision(
    observation: dict[str, Any],
    policy: dict[str, Any],
    bundle_schema_version: object,
    bundle_evidence_digest_format: object,
    bound_candidate: dict[str, Any] | None = None,
) -> Decision:
    """Compare a candidate arm with its concurrent control under one bound window."""
    bundle_metadata = validate_observation_bundle_metadata(
        bundle_schema_version, bundle_evidence_digest_format
    )
    evidence_sha256 = full_evidence_sha256(
        ONLINE_OBSERVATION_GATE_VERSION,
        bundle_metadata,
        observation,
        policy,
        bound_candidate,
    )
    candidate = observation["candidate"]
    control = observation["control"]
    candidate_rates = online_arm_rates(candidate)
    control_rates = online_arm_rates(control)
    reasons: list[str] = []
    action = "continue"

    def escalate(next_action: str, reason: str) -> None:
        nonlocal action
        priority = {
            "continue": 0,
            "investigate": 1,
            "pause": 2,
            "fallback": 3,
            "human_review": 4,
            "rollback": 5,
        }
        if priority[next_action] > priority[action]:
            action = next_action
        reasons.append(reason)

    arm_evidence_complete: dict[str, bool] = {}
    for label, arm in (("candidate", candidate), ("control", control)):
        evidence_complete = True
        eligible = int(arm["eligible_count"])
        labeled = int(arm["labeled_count"])
        label_coverage = labeled / eligible if eligible else 0.0
        if eligible < int(policy["online_min_eligible_samples"]):
            escalate("investigate", f"{label} has insufficient eligible samples; traffic cannot expand automatically")
            evidence_complete = False
        if label_coverage < float(policy["online_min_label_coverage"]):
            escalate("investigate", f"{label} has insufficient label coverage")
            evidence_complete = False
        if int(arm["critical_labeled_count"]) < int(
            policy["online_min_critical_labeled_samples"]
        ):
            escalate("investigate", f"{label} has insufficient labeled critical-slice samples")
            evidence_complete = False
        if int(arm["safety_checked_count"]) < int(
            policy["online_min_safety_checked_samples"]
        ):
            escalate("investigate", f"{label} has insufficient safety-check samples")
            evidence_complete = False
        if float(arm["max_label_age_hours"]) > float(
            policy["online_max_label_age_hours"]
        ):
            escalate("investigate", f"{label} has insufficient label freshness")
            evidence_complete = False
        arm_evidence_complete[label] = evidence_complete
    if not observation["trace_schema_complete"]:
        escalate("rollback", "online Trace schema is incomplete; reliable evidence cannot be collected")
    if not observation["redaction_check_passed"]:
        escalate("rollback", "online redaction check failed")
    candidate_safety_rate = candidate_rates["safety_violation_rate"]
    if candidate_safety_rate is not None and candidate_safety_rate > float(
        policy["max_safety_violation_rate"]
    ):
        escalate("rollback", "online safety violations exceed the policy limit")

    if arm_evidence_complete["candidate"] and arm_evidence_complete["control"]:
        candidate_task_rate = candidate_rates["task_success_rate"]
        control_task_rate = control_rates["task_success_rate"]
        candidate_critical_rate = candidate_rates["critical_slice_success_rate"]
        control_critical_rate = control_rates["critical_slice_success_rate"]
        if candidate_task_rate is not None and control_task_rate is not None:
            minimum_task = control_task_rate - float(policy["online_max_task_drop"])
            if candidate_task_rate < minimum_task:
                escalate(
                    "rollback",
                    f"candidate task-success rate is below the concurrent-control limit {minimum_task:.3f}",
                )
        if candidate_critical_rate is not None and control_critical_rate is not None:
            minimum_critical = control_critical_rate - float(
                policy["online_max_critical_drop"]
            )
            if candidate_critical_rate < minimum_critical:
                escalate(
                    "rollback",
                    f"candidate critical-slice success rate is below the concurrent-control limit {minimum_critical:.3f}",
                )

    provider_degraded = (
        float(observation["provider_error_rate"])
        > float(policy["online_max_provider_error_rate"])
    )
    provider_shifted = (
        float(observation["provider_output_shift_score"])
        > float(policy["online_max_provider_shift_score"])
    )
    if provider_degraded or provider_shifted:
        provider_reason = "provider error rate or output-shift score exceeds the local policy limit"
        expected_fallback = (
            bound_candidate["routing"]["fallback_manifest"]
            if bound_candidate is not None
            else None
        )
        observed_fallback = observation["fallback_evidence"]
        if not arm_evidence_complete["candidate"]:
            escalate(
                "human_review",
                provider_reason
                + ", but the candidate's current-window sample, label, critical-slice, or safety-check evidence is insufficient,"
                + "so it cannot switch automatically and needs human review"
            )
        elif expected_fallback is not None and observed_fallback == expected_fallback:
            escalate(
                "fallback",
                provider_reason + "; switch to the fallback-path release bound by the candidate gate",
            )
        elif observed_fallback is None:
            escalate(
                "human_review",
                provider_reason + ", but no validated and bound fallback evidence exists",
            )
        else:
            escalate(
                "human_review",
                provider_reason + "; fallback evidence does not match the candidate gate",
            )

    maximum_latency = float(control["p95_latency_ms"]) * (
        1 + float(policy["online_max_latency_increase_ratio"])
    )
    maximum_cost = float(control["actual_cost_usd_per_1k_requests"]) * (
        1 + float(policy["online_max_cost_increase_ratio"])
    )
    if float(candidate["p95_latency_ms"]) > maximum_latency:
        escalate("pause", f"candidate p95 latency exceeds the concurrent-control limit {maximum_latency:.0f}ms")
    if float(candidate["actual_cost_usd_per_1k_requests"]) > maximum_cost:
        escalate("pause", f"candidate cost exceeds the concurrent-control limit {maximum_cost:.2f} USD per 1,000 requests")

    return Decision(
        subject_id=str(observation["observation_id"]),
        action=action,
        reasons=tuple(reasons),
        evidence_fingerprint=evidence_sha256[:16],
        evidence_sha256=evidence_sha256,
        evidence_digest_format=bundle_metadata["evidence_digest_format"],
    )


def select_by_id(items: Iterable[dict[str, Any]], key: str, wanted: str | None) -> list[dict[str, Any]]:
    selected = [item for item in items if wanted is None or item[key] == wanted]
    if wanted is not None and not selected:
        raise ContractError(f"not found {key}={wanted}")
    return selected


def bind_observation(
    manifest: dict[str, Any], observation: dict[str, Any]
) -> dict[str, Any]:
    """Bind one online window to the promoted candidate gate and declared control release."""

    candidate_release_id = str(observation["candidate"]["release_id"])
    matches = [
        item
        for item in manifest["candidates"]
        if item["release_id"] == candidate_release_id
    ]
    if len(matches) != 1:
        raise ContractError(
            f"observation {observation['observation_id']} references unknown candidate release_id="
            f"{candidate_release_id}"
        )
    baseline_release_id = str(manifest["baseline"]["release_id"])
    if observation["control"]["release_id"] != baseline_release_id:
        raise ContractError(
            f"observation {observation['observation_id']} control release must bind "
            f"baseline={baseline_release_id}"
        )
    candidate = matches[0]
    gate = candidate_decision(candidate, manifest["baseline"], manifest["policy"])
    if not gate.passed:
        raise ContractError(
            f"observation {observation['observation_id']} has no passed candidate gate that can be bound"
        )
    if observation["candidate_gate_fingerprint"] != gate.evidence_fingerprint:
        raise ContractError(
            f"observation {observation['observation_id']} candidate-gate fingerprint does not match"
        )
    if observation["candidate_gate_evidence_sha256"] != gate.evidence_sha256:
        raise ContractError(
            f"observation {observation['observation_id']} full candidate-gate evidence digest does not match"
        )
    fallback_evidence = observation["fallback_evidence"]
    expected_fallback = candidate["routing"]["fallback_manifest"]
    if fallback_evidence is not None and fallback_evidence != expected_fallback:
        raise ContractError(
            f"observation {observation['observation_id']} fallback evidence "
            "does not match the candidate gate"
        )
    promoted_at_value = candidate["promoted_at"]
    if promoted_at_value is None:
        raise ContractError(
            f"observation {observation['observation_id']} references a candidate with no promoted_at"
        )
    promoted_at = require_utc_timestamp(
        promoted_at_value,
        f"candidate {candidate_release_id}.promoted_at",
    )
    window_start = require_utc_timestamp(
        observation["window_start"],
        f"observation {observation['observation_id']}.window_start",
    )
    window_end = require_utc_timestamp(
        observation["window_end"],
        f"observation {observation['observation_id']}.window_end",
    )
    decision_as_of = require_utc_timestamp(
        manifest["policy"]["decision_as_of"],
        "policy.decision_as_of",
    )
    if window_start < promoted_at:
        raise ContractError(
            f"observation {observation['observation_id']} window_start must not be earlier than "
            f"candidate promoted_at"
        )
    if window_end > decision_as_of:
        raise ContractError(
            f"observation {observation['observation_id']} window_end must not be later than "
            f"policy.decision_as_of"
        )
    return candidate


def print_decisions(decisions: Iterable[Decision], policy_version: str) -> bool:
    """Print auditable results and return whether every decision may continue."""
    all_passed = True
    for decision in decisions:
        all_passed = all_passed and decision.passed
        print(f"{decision.action.upper()}: {decision.subject_id}")
        print(f"  - policy={policy_version}")
        print(
            "  - "
            f"evidence={decision.evidence_fingerprint} "
            f"(full_sha256={decision.evidence_sha256}; "
            f"format={decision.evidence_digest_format})"
        )
        if decision.reasons:
            for reason in decision.reasons:
                print(f"  - {reason}")
        else:
            print("  - All local practice gates are satisfied")
    return all_passed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    candidate = subparsers.add_parser("candidate", help="check whether a candidate release may enter Canary")
    candidate.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    candidate.add_argument("--release-id")

    observe = subparsers.add_parser("observe", help="decide whether to continue, fallback, or roll back from an online observation")
    observe.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    observe.add_argument("--observations", type=Path, default=DEFAULT_OBSERVATIONS)
    observe.add_argument("--observation-id")

    audit = subparsers.add_parser("audit", help="recompute the candidate and online-observation gates together")
    audit.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    audit.add_argument("--observations", type=Path, default=DEFAULT_OBSERVATIONS)
    audit.add_argument("--release-id")
    audit.add_argument("--observation-id")
    return parser


def run(args: argparse.Namespace) -> int:
    manifest = validate_manifest(load_json(args.manifest))
    policy = manifest["policy"]
    baseline = manifest["baseline"]
    decisions: list[Decision] = []

    if args.command == "candidate":
        candidates = select_by_id(manifest["candidates"], "release_id", args.release_id)
        decisions.extend(candidate_decision(item, baseline, policy) for item in candidates)

    elif args.command == "observe":
        bundle = validate_observations(load_json(args.observations))
        observations = select_by_id(
            bundle["observations"], "observation_id", args.observation_id
        )
        for observation in observations:
            bound_candidate = bind_observation(manifest, observation)
            decisions.append(
                observation_decision(
                    observation,
                    policy,
                    bundle["schema_version"],
                    bundle["evidence_digest_format"],
                    bound_candidate,
                )
            )

    else:
        bundle = validate_observations(load_json(args.observations))
        observations = select_by_id(
            bundle["observations"], "observation_id", args.observation_id
        )
        if args.release_id is not None:
            mismatched = [
                observation["observation_id"]
                for observation in observations
                if observation["candidate"]["release_id"] != args.release_id
            ]
            if args.observation_id is not None and mismatched:
                raise ContractError(
                    "joint audit release/observation mismatch: "
                    + ", ".join(mismatched)
                )
            observations = [
                observation
                for observation in observations
                if observation["candidate"]["release_id"] == args.release_id
            ]
            candidates = select_by_id(
                manifest["candidates"], "release_id", args.release_id
            )
            if not observations:
                raise ContractError(
                    f"joint audit release_id={args.release_id} must bind at least one online observation"
                )
        elif args.observation_id is not None:
            release_id = str(observations[0]["candidate"]["release_id"])
            candidates = select_by_id(
                manifest["candidates"], "release_id", release_id
            )
        else:
            candidates = list(manifest["candidates"])
        candidate_decisions = [
            candidate_decision(item, baseline, policy) for item in candidates
        ]
        if args.release_id is None and args.observation_id is None:
            observed_release_ids = {
                str(observation["candidate"]["release_id"])
                for observation in observations
            }
            missing_observations = sorted(
                decision.subject_id
                for decision in candidate_decisions
                if decision.passed
                and decision.subject_id not in observed_release_ids
            )
            if missing_observations:
                raise ContractError(
                    "batch joint audit: release that passed the candidate gate lacks an online observation: "
                    + ", ".join(missing_observations)
                )
        decisions.extend(candidate_decisions)
        for observation in observations:
            bound_candidate = bind_observation(manifest, observation)
            decisions.append(
                observation_decision(
                    observation,
                    policy,
                    bundle["schema_version"],
                    bundle["evidence_digest_format"],
                    bound_candidate,
                )
            )

    return 0 if print_decisions(decisions, str(policy["version"])) else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        return run(parser.parse_args(argv))
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
