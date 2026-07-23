"""Offline runtime-monitoring audit: validate local telemetry and simulate SLO/alert decisions."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "telemetry_windows.json"
TRACE_ID_RE = re.compile(r"^[0-9a-f]{32}$")
SPAN_ID_RE = re.compile(r"^[0-9a-f]{16}$")
TRACEPARENT_RE = re.compile(
    r"^00-([0-9a-f]{32})-([0-9a-f]{16})-(00|01)$"
)
EVENT_STATUSES = frozenset({"ok", "error"})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_REGRESSION_HANDOFF_TRACE_REFS = 20
# This names the exact local byte representation, rather than implying that
# Python's JSON encoder implements a cross-language canonical JSON standard.
EVIDENCE_DIGEST_FORMAT = "python-json-sorted-utf8-v1"


class ContractError(ValueError):
    """Input JSON violates this project's strict contract."""


def reject_non_utf8_scalar_strings(value: object, context: str) -> None:
    """Reject strings that cannot participate in deterministic UTF-8 evidence bytes."""
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ContractError(
                f"{context} contains a Unicode surrogate that cannot be encoded as normalized UTF-8 input"
            ) from exc
        return
    if isinstance(value, dict):
        for key, item in value.items():
            reject_non_utf8_scalar_strings(key, f"{context}  field name")
            key_context = f"{context}.{key}" if isinstance(key, str) else context
            reject_non_utf8_scalar_strings(item, key_context)
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            reject_non_utf8_scalar_strings(item, f"{context}[{index}]")


@dataclass(frozen=True)
class Decision:
    """A monitoring-audit decision."""

    scenario_name: str
    action: str
    reasons: tuple[str, ...]
    indicators: dict[str, float | int | None]
    evidence_fingerprint: str
    evidence_sha256: str
    regression_handoff: dict[str, object] | None
    evidence_digest_format: str = EVIDENCE_DIGEST_FORMAT

    @property
    def passed(self) -> bool:
        return self.action == "ok"


def load_json(path: Path) -> dict[str, Any]:
    """Read a strict JSON object as UTF-8."""

    def reject_nonstandard_number(value: str) -> None:
        raise ContractError(f"{path.name} contains a number outside the JSON standard: {value}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            reject_non_utf8_scalar_strings(key, "JSON field name")
            if key in result:
                raise ContractError(f"{path.name} contains a duplicate JSON field: {key}")
            result[key] = value
        return result

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(
                handle,
                parse_constant=reject_nonstandard_number,
                object_pairs_hook=reject_duplicate_keys,
            )
    except UnicodeDecodeError as exc:
        raise ContractError(f"{path.name} must be valid UTF-8 JSON") from exc
    if not isinstance(data, dict):
        raise ContractError(f"{path.name} top level must be an object")
    reject_non_utf8_scalar_strings(data, path.name)
    return data


def full_evidence_sha256(*values: object) -> str:
    """Return this project's versioned, local evidence identifier.

    The label fixes a Python byte profile for the teaching artifacts. It is
    neither cross-language canonical JSON nor an authenticity mechanism.
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
    """Return a display-only prefix of a durable monitoring evidence digest."""
    return full_evidence_sha256(*values)[:16]


def require_exact_keys(value: object, required: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{context} must be an object")
    missing = required - value.keys()
    extra = value.keys() - required
    if missing:
        raise ContractError(f"{context} is missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise ContractError(f"{context} contains unknown fields: {', '.join(sorted(extra))}")
    return value


def require_string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{context} must be a non-empty string")
    return value


def require_bool(value: object, context: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(f"{context} must be a Boolean")
    return value


def require_sha256(value: object, context: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ContractError(f"{context} must be a 64-character lowercase hexadecimal SHA-256")
    return value


def require_evidence_digest_format(value: object, context: str) -> str:
    if value != EVIDENCE_DIGEST_FORMAT:
        raise ContractError(
            f"{context} must use a supported evidence digest format "
            f"{EVIDENCE_DIGEST_FORMAT!r}"
        )
    return EVIDENCE_DIGEST_FORMAT


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
        raise ContractError(f"{context} must be greater than or equal to {minimum}")
    if maximum is not None and number > maximum:
        raise ContractError(f"{context} must be less than or equal to {maximum}")
    return number


def require_integer(value: object, context: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{context} must be an integer")
    if value < minimum:
        raise ContractError(f"{context} must be greater than or equal to {minimum}")
    return value


def require_string_list(value: object, context: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ContractError(f"{context} must be a non-empty array of strings")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(require_string(item, f"{context}[{index}]"))
    if len(set(result)) != len(result):
        raise ContractError(f"{context} must not contain duplicates")
    return result


def parse_timestamp(value: object, context: str) -> datetime:
    text = require_string(value, context)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{context} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{context} must include a time zone")
    return parsed


POLICY_KEYS = {
    "version",
    "allowed_metric_labels",
    "max_p95_latency_ms",
    "min_quality_pass_rate",
    "min_label_coverage_rate",
    "max_safety_violation_rate",
    "min_safety_check_coverage_rate",
    "max_average_estimated_cost_usd",
    "min_trace_completeness_rate",
    "max_collector_drop_rate",
    "max_export_age_seconds",
    "max_event_age_seconds",
    "max_retention_days",
    "page_short_burn_rate",
    "page_long_burn_rate",
    "ticket_long_burn_rate",
    "max_cpu_utilization",
    "max_queue_depth",
    "max_average_agent_steps",
    "max_average_total_tokens",
}
SLO_KEYS = {"version", "target", "latency_objective_ms", "good_statuses"}
SCENARIO_KEYS = {
    "name",
    "release_evidence",
    "window_minutes",
    "short_window_minutes",
    "window_end",
    "metric_label_keys",
    "telemetry_policy",
    "collector",
    "resources",
    "events",
    "traces",
}
EVENT_KEYS = {
    "request_id",
    "timestamp",
    "release",
    "service",
    "intent",
    "status",
    "latency_ms",
    "quality_pass",
    "safety_checked",
    "safety_violation",
    "estimated_cost_usd",
    "model_provider",
    "model_snapshot",
    "model_calls",
    "tool_calls",
    "agent_steps",
    "input_tokens",
    "output_tokens",
    "trace_id",
}
TRACE_KEYS = {"trace_id", "traceparent", "spans"}
SPAN_KEYS = {
    "span_id",
    "parent_span_id",
    "name",
    "service",
    "status",
    "duration_ms",
    "attributes",
}
RELEASE_EVIDENCE_KEYS = {
    "release_id",
    "release_manifest_sha256",
    "candidate_gate_evidence_sha256",
    "candidate_gate_evidence_digest_format",
}


def validate_release_evidence(value: object, context: str) -> dict[str, Any]:
    evidence = require_exact_keys(value, RELEASE_EVIDENCE_KEYS, context)
    require_string(evidence["release_id"], f"{context}.release_id")
    require_sha256(evidence["release_manifest_sha256"], f"{context}.release_manifest_sha256")
    require_sha256(
        evidence["candidate_gate_evidence_sha256"],
        f"{context}.candidate_gate_evidence_sha256",
    )
    require_evidence_digest_format(
        evidence["candidate_gate_evidence_digest_format"],
        f"{context}.candidate_gate_evidence_digest_format",
    )
    return evidence


def validate_policy(value: object) -> dict[str, Any]:
    policy = require_exact_keys(value, POLICY_KEYS, "policy")
    require_string(policy["version"], "policy.version")
    require_string_list(policy["allowed_metric_labels"], "policy.allowed_metric_labels")
    for key in (
        "min_label_coverage_rate",
        "min_quality_pass_rate",
        "max_safety_violation_rate",
        "min_safety_check_coverage_rate",
        "min_trace_completeness_rate",
        "max_collector_drop_rate",
        "max_cpu_utilization",
    ):
        require_number(policy[key], f"policy.{key}", minimum=0, maximum=1)
    for key in (
        "max_p95_latency_ms",
        "max_average_estimated_cost_usd",
        "max_export_age_seconds",
        "max_event_age_seconds",
        "page_short_burn_rate",
        "page_long_burn_rate",
        "ticket_long_burn_rate",
        "max_average_agent_steps",
        "max_average_total_tokens",
    ):
        require_number(policy[key], f"policy.{key}", minimum=0)
    for key in ("max_retention_days", "max_queue_depth"):
        require_integer(policy[key], f"policy.{key}")
    return policy


def validate_slo(value: object) -> dict[str, Any]:
    slo = require_exact_keys(value, SLO_KEYS, "slo")
    require_string(slo["version"], "slo.version")
    target = require_number(slo["target"], "slo.target", minimum=0, maximum=1)
    if target >= 1:
        raise ContractError("slo.target must be less than 1; use a separate control for zero-tolerance risk")
    require_number(slo["latency_objective_ms"], "slo.latency_objective_ms", minimum=0)
    good_statuses = require_string_list(slo["good_statuses"], "slo.good_statuses")
    unknown_statuses = set(good_statuses) - EVENT_STATUSES
    if unknown_statuses:
        raise ContractError(
            "slo.good_statuses contains a status outside the event contract: "
            + ", ".join(sorted(unknown_statuses))
        )
    return slo


def validate_trace_id(value: object, context: str) -> str:
    text = require_string(value, context)
    if not TRACE_ID_RE.fullmatch(text) or set(text) == {"0"}:
        raise ContractError(f"{context} must be 32 lowercase hexadecimal characters and not all zero")
    return text


def validate_span_id(value: object, context: str) -> str:
    text = require_string(value, context)
    if not SPAN_ID_RE.fullmatch(text) or set(text) == {"0"}:
        raise ContractError(f"{context} must be 16 lowercase hexadecimal characters and not all zero")
    return text


def validate_span(value: object, context: str) -> dict[str, Any]:
    span = require_exact_keys(value, SPAN_KEYS, context)
    validate_span_id(span["span_id"], f"{context}.span_id")
    if span["parent_span_id"] is not None:
        validate_span_id(span["parent_span_id"], f"{context}.parent_span_id")
    for key in ("name", "service"):
        require_string(span[key], f"{context}.{key}")
    if span["status"] not in {"ok", "error"}:
        raise ContractError(f"{context}.status must be ok or error")
    require_number(span["duration_ms"], f"{context}.duration_ms", minimum=0)
    attributes = require_exact_keys(
        span["attributes"], {"release", "operation_type"}, f"{context}.attributes"
    )
    require_string(attributes["release"], f"{context}.attributes.release")
    if attributes["operation_type"] not in {"request", "retrieval", "model", "tool", "policy"}:
        raise ContractError(f"{context}.attributes.operation_type is not in the allowed set")
    return span


def validate_trace(value: object, context: str) -> dict[str, Any]:
    trace = require_exact_keys(value, TRACE_KEYS, context)
    trace_id = validate_trace_id(trace["trace_id"], f"{context}.trace_id")
    traceparent = require_string(trace["traceparent"], f"{context}.traceparent")
    match = TRACEPARENT_RE.fullmatch(traceparent)
    if match is None or match.group(1) != trace_id or set(match.group(2)) == {"0"}:
        raise ContractError(
            f"{context}.traceparent must use version 00, match trace_id, have a nonzero parent ID, and use flags 00/01"
        )

    if not isinstance(trace["spans"], list) or not trace["spans"]:
        raise ContractError(f"{context}.spans must be a non-empty array")
    spans = [validate_span(item, f"{context}.spans[{index}]") for index, item in enumerate(trace["spans"])]
    span_ids = [str(span["span_id"]) for span in spans]
    if len(set(span_ids)) != len(span_ids):
        raise ContractError(f"{context}.spans contains duplicate span_id")
    roots = [span for span in spans if span["parent_span_id"] is None]
    if len(roots) != 1:
        raise ContractError(f"{context}.spans must have exactly one root span")
    known_ids = set(span_ids)
    for span in spans:
        parent = span["parent_span_id"]
        if parent is not None and parent not in known_ids:
            raise ContractError(f"{context}: span {span['span_id']} references an unknown parent_span_id")

    parents = {str(span["span_id"]): span["parent_span_id"] for span in spans}
    for span_id in span_ids:
        visited: set[str] = set()
        current: str | None = span_id
        while current is not None:
            if current in visited:
                raise ContractError(f"{context}.spans contains a parent-child cycle")
            visited.add(current)
            parent = parents[current]
            current = str(parent) if parent is not None else None
    return trace


def validate_event(value: object, context: str) -> dict[str, Any]:
    event = require_exact_keys(value, EVENT_KEYS, context)
    for key in ("request_id", "release", "service", "intent", "status", "model_provider", "model_snapshot"):
        require_string(event[key], f"{context}.{key}")
    parse_timestamp(event["timestamp"], f"{context}.timestamp")
    if event["status"] not in EVENT_STATUSES:
        raise ContractError(f"{context}.status must be ok or error")
    for key in ("latency_ms", "estimated_cost_usd"):
        require_number(event[key], f"{context}.{key}", minimum=0)
    for key in ("model_calls", "tool_calls", "agent_steps", "input_tokens", "output_tokens"):
        require_integer(event[key], f"{context}.{key}")
    if event["quality_pass"] is not None:
        require_bool(event["quality_pass"], f"{context}.quality_pass")
    for key in ("safety_checked", "safety_violation"):
        require_bool(event[key], f"{context}.{key}")
    if event["safety_violation"] and not event["safety_checked"]:
        raise ContractError(f"{context}: claims a violation although safety was not checked")
    if event["trace_id"] is not None:
        validate_trace_id(event["trace_id"], f"{context}.trace_id")
    return event


def validate_scenario(value: object, index: int, policy: dict[str, Any]) -> dict[str, Any]:
    context = f"scenarios[{index}]"
    scenario = require_exact_keys(value, SCENARIO_KEYS, context)
    require_string(scenario["name"], f"{context}.name")
    release_evidence = validate_release_evidence(
        scenario["release_evidence"], f"{context}.release_evidence"
    )
    long_minutes = require_integer(scenario["window_minutes"], f"{context}.window_minutes", minimum=1)
    short_minutes = require_integer(
        scenario["short_window_minutes"], f"{context}.short_window_minutes", minimum=1
    )
    if short_minutes >= long_minutes:
        raise ContractError(f"{context}: short_window_minutes must be less than window_minutes")
    window_end = parse_timestamp(scenario["window_end"], f"{context}.window_end")
    window_start = window_end - timedelta(minutes=long_minutes)

    label_keys = require_string_list(scenario["metric_label_keys"], f"{context}.metric_label_keys")
    disallowed = set(label_keys) - set(policy["allowed_metric_labels"])
    if disallowed:
        raise ContractError(
            f"{context}.metric_label_keys contains an unapproved or high-cardinality field: {', '.join(sorted(disallowed))}"
        )

    telemetry_policy = require_exact_keys(
        scenario["telemetry_policy"],
        {"content_capture_enabled", "redaction_check_passed", "retention_days"},
        f"{context}.telemetry_policy",
    )
    require_bool(
        telemetry_policy["content_capture_enabled"],
        f"{context}.telemetry_policy.content_capture_enabled",
    )
    require_bool(
        telemetry_policy["redaction_check_passed"],
        f"{context}.telemetry_policy.redaction_check_passed",
    )
    require_integer(
        telemetry_policy["retention_days"], f"{context}.telemetry_policy.retention_days"
    )

    collector = require_exact_keys(
        scenario["collector"],
        {
            "accepted",
            "refused",
            "sent",
            "failed_to_send",
            "queue_size",
            "queue_capacity",
            "last_export_age_seconds",
        },
        f"{context}.collector",
    )
    for key in ("accepted", "refused", "sent", "failed_to_send", "queue_size", "queue_capacity"):
        require_integer(collector[key], f"{context}.collector.{key}")
    require_number(
        collector["last_export_age_seconds"],
        f"{context}.collector.last_export_age_seconds",
        minimum=0,
    )
    if collector["queue_size"] > collector["queue_capacity"]:
        raise ContractError(f"{context}.collector.queue_size must not exceed queue_capacity")
    if collector["sent"] + collector["failed_to_send"] > collector["accepted"]:
        raise ContractError(f"{context}.collector sent and failed counts must not exceed accepted")

    resources = require_exact_keys(
        scenario["resources"],
        {"cpu_utilization", "queue_depth", "resource_error_count"},
        f"{context}.resources",
    )
    require_number(
        resources["cpu_utilization"], f"{context}.resources.cpu_utilization", minimum=0, maximum=1
    )
    for key in ("queue_depth", "resource_error_count"):
        require_integer(resources[key], f"{context}.resources.{key}")

    if not isinstance(scenario["events"], list) or not scenario["events"]:
        raise ContractError(f"{context}.events must be a non-empty array")
    events = [validate_event(item, f"{context}.events[{event_index}]") for event_index, item in enumerate(scenario["events"])]
    request_ids = [str(event["request_id"]) for event in events]
    if len(set(request_ids)) != len(request_ids):
        raise ContractError(f"{context}.events contain duplicate request_id")
    timestamps = [parse_timestamp(event["timestamp"], f"{context}.events.timestamp") for event in events]
    if timestamps != sorted(timestamps):
        raise ContractError(f"{context}.events must be sorted ascending by timestamp")
    event_releases = {str(event["release"]) for event in events}
    if event_releases != {str(release_evidence["release_id"])}:
        raise ContractError(f"{context}.release_evidence must bind the release of every event")
    if timestamps[0] < window_start or timestamps[-1] > window_end:
        raise ContractError(
            f"{context}.events must fall within the window_minutes window ending at window_end"
        )
    cutoff = window_end - timedelta(minutes=short_minutes)
    if not any(timestamp >= cutoff for timestamp in timestamps):
        raise ContractError(f"{context} short window contains no events")

    if not isinstance(scenario["traces"], list):
        raise ContractError(f"{context}.traces must be an array")
    traces = [validate_trace(item, f"{context}.traces[{trace_index}]") for trace_index, item in enumerate(scenario["traces"])]
    trace_ids = [str(trace["trace_id"]) for trace in traces]
    if len(set(trace_ids)) != len(trace_ids):
        raise ContractError(f"{context}.traces contain duplicate trace_id")
    referenced = {str(event["trace_id"]) for event in events if event["trace_id"] is not None}
    if referenced - set(trace_ids):
        raise ContractError(f"{context}.events reference a missing trace")
    if set(trace_ids) - referenced:
        raise ContractError(f"{context}.traces contain a trace not referenced by an event")

    event_by_trace = {
        str(event["trace_id"]): event for event in events if event["trace_id"] is not None
    }
    for trace in traces:
        event = event_by_trace[str(trace["trace_id"])]
        root = next(span for span in trace["spans"] if span["parent_span_id"] is None)
        if root["service"] != event["service"]:
            raise ContractError(f"{context}: root span service does not match the event")
        if root["attributes"]["release"] != event["release"]:
            raise ContractError(f"{context}: root span release does not match the event")
        if root["status"] != event["status"]:
            raise ContractError(f"{context}: root span status does not match the event")
        if not math.isclose(float(root["duration_ms"]), float(event["latency_ms"]), abs_tol=1e-9):
            raise ContractError(f"{context}: root span duration does not match the event latency")
    return scenario


def validate_input(value: object) -> dict[str, Any]:
    data = require_exact_keys(value, {"policy", "slo", "scenarios"}, "input")
    policy = validate_policy(data["policy"])
    validate_slo(data["slo"])
    if not isinstance(data["scenarios"], list) or not data["scenarios"]:
        raise ContractError("scenarios must be a non-empty array")
    scenarios = [validate_scenario(item, index, policy) for index, item in enumerate(data["scenarios"])]
    names = [str(scenario["name"]) for scenario in scenarios]
    if len(set(names)) != len(names):
        raise ContractError("scenarios contain duplicate name")
    return data


def nearest_rank_percentile(values: list[float], percentile: float) -> float:
    if not values:
        raise ContractError("percentile input must not be empty")
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def is_good_event(event: dict[str, Any], slo: dict[str, Any]) -> bool:
    return event["status"] in slo["good_statuses"] and float(event["latency_ms"]) <= float(
        slo["latency_objective_ms"]
    )


def bad_event_fraction(events: list[dict[str, Any]], slo: dict[str, Any]) -> float:
    return sum(not is_good_event(event, slo) for event in events) / len(events)


def burn_rate(events: list[dict[str, Any]], slo: dict[str, Any]) -> float:
    bad_fraction = bad_event_fraction(events, slo)
    return bad_fraction / (1 - float(slo["target"]))


def window_events(scenario: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events = list(scenario["events"])
    end = parse_timestamp(scenario["window_end"], "scenario.window_end")
    cutoff = end - timedelta(minutes=int(scenario["short_window_minutes"]))
    short = [
        event
        for event in events
        if parse_timestamp(event["timestamp"], "event.timestamp") >= cutoff
    ]
    return events, short


def calculate_indicators(
    scenario: dict[str, Any], slo: dict[str, Any]
) -> dict[str, float | int | None]:
    events, short_events = window_events(scenario)
    window_end = parse_timestamp(scenario["window_end"], "scenario.window_end")
    newest_event = parse_timestamp(events[-1]["timestamp"], "events[-1].timestamp")
    labeled = [event for event in events if event["quality_pass"] is not None]
    safety_checked = [event for event in events if event["safety_checked"]]
    traces_present = [event for event in events if event["trace_id"] is not None]
    collector = scenario["collector"]
    accepted_or_refused = int(collector["accepted"]) + int(collector["refused"])
    collector_drop_rate = (
        (int(collector["refused"]) + int(collector["failed_to_send"]))
        / accepted_or_refused
        if accepted_or_refused
        else 0.0
    )

    quality_rate: float | None = None
    if labeled:
        quality_rate = sum(event["quality_pass"] is True for event in labeled) / len(labeled)
    safety_rate: float | None = None
    if safety_checked:
        safety_rate = sum(event["safety_violation"] for event in safety_checked) / len(
            safety_checked
        )

    status_counts = Counter(str(event["status"]) for event in events)
    return {
        "event_count": len(events),
        "request_rate_per_minute": len(events) / int(scenario["window_minutes"]),
        "technical_error_rate": status_counts.get("error", 0) / len(events),
        "p95_latency_ms": nearest_rank_percentile(
            [float(event["latency_ms"]) for event in events], 0.95
        ),
        "sli_good_event_rate": sum(is_good_event(event, slo) for event in events)
        / len(events),
        "slo_bad_event_fraction": bad_event_fraction(events, slo),
        "long_burn_rate": burn_rate(events, slo),
        "short_burn_rate": burn_rate(short_events, slo),
        "event_data_age_seconds": (window_end - newest_event).total_seconds(),
        "quality_pass_rate": quality_rate,
        "label_coverage_rate": len(labeled) / len(events),
        "safety_violation_rate": safety_rate,
        "safety_check_coverage_rate": len(safety_checked) / len(events),
        "average_estimated_cost_usd": sum(
            float(event["estimated_cost_usd"]) for event in events
        )
        / len(events),
        "trace_completeness_rate": len(traces_present) / len(events),
        "collector_drop_rate": collector_drop_rate,
        "collector_queue_utilization": (
            int(collector["queue_size"]) / int(collector["queue_capacity"])
            if int(collector["queue_capacity"])
            else 0.0
        ),
        "average_model_calls": sum(int(event["model_calls"]) for event in events)
        / len(events),
        "average_tool_calls": sum(int(event["tool_calls"]) for event in events)
        / len(events),
        "average_agent_steps": sum(int(event["agent_steps"]) for event in events)
        / len(events),
        "average_total_tokens": sum(
            int(event["input_tokens"]) + int(event["output_tokens"]) for event in events
        )
        / len(events),
    }


def regression_handoff(
    scenario: dict[str, Any],
    action: str,
    monitor_evidence_sha256: str,
) -> dict[str, object] | None:
    """Create a bounded, content-free candidate for human regression triage.

    A monitoring alert is evidence of a production condition, not an automatic
    change to a frozen suite. The returned references therefore remain a
    restricted audit artifact and explicitly require human review.
    """
    if action == "ok":
        return None
    release_evidence = scenario["release_evidence"]
    trace_ids = sorted(
        {
            str(event["trace_id"])
            for event in scenario["events"]
            if event["trace_id"] is not None
        }
    )[:MAX_REGRESSION_HANDOFF_TRACE_REFS]
    return {
        "status": "needs_human_triage",
        "release_id": release_evidence["release_id"],
        "release_manifest_sha256": release_evidence["release_manifest_sha256"],
        "candidate_gate_evidence_sha256": release_evidence[
            "candidate_gate_evidence_sha256"
        ],
        "candidate_gate_evidence_digest_format": release_evidence[
            "candidate_gate_evidence_digest_format"
        ],
        "monitor_evidence_sha256": monitor_evidence_sha256,
        "monitor_evidence_digest_format": EVIDENCE_DIGEST_FORMAT,
        "source_trace_ids": trace_ids,
        "raw_content_included": False,
        "dedupe_key": full_evidence_sha256(
            "regression-candidate-v1", release_evidence, action, trace_ids
        ),
    }


def evaluate_scenario(
    scenario: dict[str, Any], policy: dict[str, Any], slo: dict[str, Any]
) -> Decision:
    indicators = calculate_indicators(scenario, slo)
    reasons: list[str] = []
    action = "ok"

    def escalate(next_action: str, reason: str) -> None:
        nonlocal action
        priority = {"ok": 0, "ticket": 1, "page": 2}
        if priority[next_action] > priority[action]:
            action = next_action
        reasons.append(reason)

    short_burn = float(indicators["short_burn_rate"])
    long_burn = float(indicators["long_burn_rate"])
    if short_burn >= float(policy["page_short_burn_rate"]) and long_burn >= float(
        policy["page_long_burn_rate"]
    ):
        escalate("page", "short and long window error budgets are both burning rapidly")
    elif long_burn >= float(policy["ticket_long_burn_rate"]):
        escalate("ticket", "long-window error-budget consumption requires investigation")

    safety_rate = indicators["safety_violation_rate"]
    if safety_rate is None:
        escalate("page", "no safety check was performed; safety state is unknown")
    elif float(safety_rate) > float(policy["max_safety_violation_rate"]):
        escalate("page", "safety-violation rate exceeds local policy")

    telemetry_policy = scenario["telemetry_policy"]
    if telemetry_policy["content_capture_enabled"]:
        escalate("page", "local policy does not permit raw-content capture by default")
    if not telemetry_policy["redaction_check_passed"]:
        escalate("page", "telemetry redaction check failed")
    if int(telemetry_policy["retention_days"]) > int(policy["max_retention_days"]):
        escalate("page", "telemetry retention exceeds local policy")

    collector = scenario["collector"]
    if float(indicators["collector_drop_rate"]) > float(policy["max_collector_drop_rate"]):
        escalate("page", "Collector refusal or export-failure rate exceeds local policy")
    if float(collector["last_export_age_seconds"]) > float(policy["max_export_age_seconds"]):
        escalate("page", "Collector export data is too old; monitoring may be blind")
    if float(indicators["event_data_age_seconds"]) > float(
        policy["max_event_age_seconds"]
    ):
        escalate("page", "latest business event is too old relative to observation-window end; monitoring may be stale")
    if float(indicators["trace_completeness_rate"]) < float(
        policy["min_trace_completeness_rate"]
    ):
        escalate("page", "Trace completeness is below local policy")

    if float(indicators["p95_latency_ms"]) > float(policy["max_p95_latency_ms"]):
        escalate("ticket", "p95 latency exceeds local policy")
    if float(indicators["label_coverage_rate"]) < float(policy["min_label_coverage_rate"]):
        escalate("ticket", "quality-label coverage is insufficient")
    quality_rate = indicators["quality_pass_rate"]
    if quality_rate is None:
        escalate("ticket", "no quality labels; task quality is unknown")
    elif float(quality_rate) < float(policy["min_quality_pass_rate"]):
        escalate("ticket", "labeled quality-pass rate is below local policy")
    if float(indicators["safety_check_coverage_rate"]) < float(
        policy["min_safety_check_coverage_rate"]
    ):
        escalate("ticket", "safety-check coverage is insufficient")
    if float(indicators["average_estimated_cost_usd"]) > float(
        policy["max_average_estimated_cost_usd"]
    ):
        escalate("ticket", "mean estimated cost per request exceeds local policy")
    if float(indicators["average_agent_steps"]) > float(policy["max_average_agent_steps"]):
        escalate("ticket", "mean Agent steps exceed local policy")
    if float(indicators["average_total_tokens"]) > float(policy["max_average_total_tokens"]):
        escalate("ticket", "mean token count exceeds local policy")

    resources = scenario["resources"]
    if float(resources["cpu_utilization"]) > float(policy["max_cpu_utilization"]):
        escalate("ticket", "USE: CPU utilization exceeds local investigation line")
    if int(resources["queue_depth"]) > int(policy["max_queue_depth"]):
        escalate("ticket", "USE: resource-queue saturation exceeds local investigation line")
    if int(resources["resource_error_count"]) > 0:
        escalate("ticket", "USE: resource error count is nonzero")

    evidence_sha256 = full_evidence_sha256("monitor-audit-v3", scenario, policy, slo)
    return Decision(
        scenario_name=str(scenario["name"]),
        action=action,
        reasons=tuple(reasons),
        indicators=indicators,
        evidence_fingerprint=evidence_sha256[:16],
        evidence_sha256=evidence_sha256,
        regression_handoff=regression_handoff(scenario, action, evidence_sha256),
    )


def select_scenarios(
    scenarios: Iterable[dict[str, Any]], wanted: str | None
) -> list[dict[str, Any]]:
    selected = [scenario for scenario in scenarios if wanted is None or scenario["name"] == wanted]
    if wanted is not None and not selected:
        raise ContractError(f"scenario not found={wanted}")
    return selected


def print_decisions(decisions: Iterable[Decision], policy_version: str, slo_version: str) -> bool:
    all_passed = True
    for decision in decisions:
        all_passed = all_passed and decision.passed
        indicators = decision.indicators
        print(f"{decision.action.upper()}: {decision.scenario_name}")
        print(
            "  - "
            f"policy={policy_version}, slo={slo_version}, evidence={decision.evidence_fingerprint}"
        )
        print(f"  - evidence_digest_format={decision.evidence_digest_format}")
        print(
            "  - "
            f"RED rate={float(indicators['request_rate_per_minute']):.3f}/min, "
            f"errors={float(indicators['technical_error_rate']):.3f}, "
            f"p95={float(indicators['p95_latency_ms']):.0f}ms"
        )
        print(
            "  - "
            f"SLI={float(indicators['sli_good_event_rate']):.3f}, "
            f"burn(short/long)={float(indicators['short_burn_rate']):.2f}/"
            f"{float(indicators['long_burn_rate']):.2f}, "
            f"trace={float(indicators['trace_completeness_rate']):.3f}, "
            f"event_age={float(indicators['event_data_age_seconds']):.0f}s"
        )
        if decision.reasons:
            for reason in decision.reasons:
                print(f"  - {reason}")
        else:
            print("  - meets every local teaching rule")
        if decision.regression_handoff is not None:
            trace_refs = decision.regression_handoff["source_trace_ids"]
            print(
                "  - regression_candidate=needs_human_triage; "
                f"trace_refs={len(trace_refs)}; raw_content_included=false"
            )
    return all_passed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--scenario")
    return parser


def run(args: argparse.Namespace) -> int:
    data = validate_input(load_json(args.input))
    scenarios = select_scenarios(data["scenarios"], args.scenario)
    decisions = [evaluate_scenario(scenario, data["policy"], data["slo"]) for scenario in scenarios]
    passed = print_decisions(decisions, str(data["policy"]["version"]), str(data["slo"]["version"]))
    return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

