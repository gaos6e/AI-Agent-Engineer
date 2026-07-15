"""离线运行监控审计：校验本地遥测并模拟 SLO/告警决策。"""

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


class ContractError(ValueError):
    """输入 JSON 不符合本项目的严格契约。"""


@dataclass(frozen=True)
class Decision:
    """一次监控审计决定。"""

    scenario_name: str
    action: str
    reasons: tuple[str, ...]
    indicators: dict[str, float | int | None]
    evidence_fingerprint: str

    @property
    def passed(self) -> bool:
        return self.action == "ok"


def load_json(path: Path) -> dict[str, Any]:
    """以 UTF-8 读取严格 JSON 对象。"""

    def reject_nonstandard_number(value: str) -> None:
        raise ContractError(f"{path.name} 含 JSON 标准之外的数值: {value}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle, parse_constant=reject_nonstandard_number)
    if not isinstance(data, dict):
        raise ContractError(f"{path.name} 顶层必须是对象")
    return data


def fingerprint(*values: object) -> str:
    payload = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def require_exact_keys(value: object, required: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{context} 必须是对象")
    missing = required - value.keys()
    extra = value.keys() - required
    if missing:
        raise ContractError(f"{context} 缺少字段: {', '.join(sorted(missing))}")
    if extra:
        raise ContractError(f"{context} 含未知字段: {', '.join(sorted(extra))}")
    return value


def require_string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{context} 必须是非空字符串")
    return value


def require_bool(value: object, context: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(f"{context} 必须是布尔值")
    return value


def require_number(
    value: object,
    context: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{context} 必须是数值")
    number = float(value)
    if not math.isfinite(number):
        raise ContractError(f"{context} 必须是有限数值")
    if minimum is not None and number < minimum:
        raise ContractError(f"{context} 必须大于等于 {minimum}")
    if maximum is not None and number > maximum:
        raise ContractError(f"{context} 必须小于等于 {maximum}")
    return number


def require_integer(value: object, context: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{context} 必须是整数")
    if value < minimum:
        raise ContractError(f"{context} 必须大于等于 {minimum}")
    return value


def require_string_list(value: object, context: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ContractError(f"{context} 必须是非空字符串数组")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(require_string(item, f"{context}[{index}]"))
    if len(set(result)) != len(result):
        raise ContractError(f"{context} 不能包含重复值")
    return result


def parse_timestamp(value: object, context: str) -> datetime:
    text = require_string(value, context)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{context} 必须是 ISO 8601 时间") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{context} 必须包含时区")
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
    "window_minutes",
    "short_window_minutes",
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
        raise ContractError("slo.target 必须小于 1，零容忍风险应使用独立控制")
    require_number(slo["latency_objective_ms"], "slo.latency_objective_ms", minimum=0)
    require_string_list(slo["good_statuses"], "slo.good_statuses")
    return slo


def validate_trace_id(value: object, context: str) -> str:
    text = require_string(value, context)
    if not TRACE_ID_RE.fullmatch(text) or set(text) == {"0"}:
        raise ContractError(f"{context} 必须是 32 位小写十六进制且不能全零")
    return text


def validate_span_id(value: object, context: str) -> str:
    text = require_string(value, context)
    if not SPAN_ID_RE.fullmatch(text) or set(text) == {"0"}:
        raise ContractError(f"{context} 必须是 16 位小写十六进制且不能全零")
    return text


def validate_span(value: object, context: str) -> dict[str, Any]:
    span = require_exact_keys(value, SPAN_KEYS, context)
    validate_span_id(span["span_id"], f"{context}.span_id")
    if span["parent_span_id"] is not None:
        validate_span_id(span["parent_span_id"], f"{context}.parent_span_id")
    for key in ("name", "service"):
        require_string(span[key], f"{context}.{key}")
    if span["status"] not in {"ok", "error"}:
        raise ContractError(f"{context}.status 只能是 ok 或 error")
    require_number(span["duration_ms"], f"{context}.duration_ms", minimum=0)
    attributes = require_exact_keys(
        span["attributes"], {"release", "operation_type"}, f"{context}.attributes"
    )
    require_string(attributes["release"], f"{context}.attributes.release")
    if attributes["operation_type"] not in {"request", "retrieval", "model", "tool", "policy"}:
        raise ContractError(f"{context}.attributes.operation_type 不在允许集合中")
    return span


def validate_trace(value: object, context: str) -> dict[str, Any]:
    trace = require_exact_keys(value, TRACE_KEYS, context)
    trace_id = validate_trace_id(trace["trace_id"], f"{context}.trace_id")
    traceparent = require_string(trace["traceparent"], f"{context}.traceparent")
    match = TRACEPARENT_RE.fullmatch(traceparent)
    if match is None or match.group(1) != trace_id or set(match.group(2)) == {"0"}:
        raise ContractError(
            f"{context}.traceparent 必须是版本 00、匹配 trace_id、非零 parent-id、flags 00/01"
        )

    if not isinstance(trace["spans"], list) or not trace["spans"]:
        raise ContractError(f"{context}.spans 必须是非空数组")
    spans = [validate_span(item, f"{context}.spans[{index}]") for index, item in enumerate(trace["spans"])]
    span_ids = [str(span["span_id"]) for span in spans]
    if len(set(span_ids)) != len(span_ids):
        raise ContractError(f"{context}.spans 含重复 span_id")
    roots = [span for span in spans if span["parent_span_id"] is None]
    if len(roots) != 1:
        raise ContractError(f"{context}.spans 必须恰有一个 root span")
    known_ids = set(span_ids)
    for span in spans:
        parent = span["parent_span_id"]
        if parent is not None and parent not in known_ids:
            raise ContractError(f"{context}: span {span['span_id']} 引用了未知 parent_span_id")

    parents = {str(span["span_id"]): span["parent_span_id"] for span in spans}
    for span_id in span_ids:
        visited: set[str] = set()
        current: str | None = span_id
        while current is not None:
            if current in visited:
                raise ContractError(f"{context}.spans 存在父子环")
            visited.add(current)
            parent = parents[current]
            current = str(parent) if parent is not None else None
    return trace


def validate_event(value: object, context: str) -> dict[str, Any]:
    event = require_exact_keys(value, EVENT_KEYS, context)
    for key in ("request_id", "release", "service", "intent", "status", "model_provider", "model_snapshot"):
        require_string(event[key], f"{context}.{key}")
    parse_timestamp(event["timestamp"], f"{context}.timestamp")
    if event["status"] not in {"ok", "error"}:
        raise ContractError(f"{context}.status 只能是 ok 或 error")
    for key in ("latency_ms", "estimated_cost_usd"):
        require_number(event[key], f"{context}.{key}", minimum=0)
    for key in ("model_calls", "tool_calls", "agent_steps", "input_tokens", "output_tokens"):
        require_integer(event[key], f"{context}.{key}")
    if event["quality_pass"] is not None:
        require_bool(event["quality_pass"], f"{context}.quality_pass")
    for key in ("safety_checked", "safety_violation"):
        require_bool(event[key], f"{context}.{key}")
    if event["safety_violation"] and not event["safety_checked"]:
        raise ContractError(f"{context}: 未检查安全却宣称发现违规")
    if event["trace_id"] is not None:
        validate_trace_id(event["trace_id"], f"{context}.trace_id")
    return event


def validate_scenario(value: object, index: int, policy: dict[str, Any]) -> dict[str, Any]:
    context = f"scenarios[{index}]"
    scenario = require_exact_keys(value, SCENARIO_KEYS, context)
    require_string(scenario["name"], f"{context}.name")
    long_minutes = require_integer(scenario["window_minutes"], f"{context}.window_minutes", minimum=1)
    short_minutes = require_integer(
        scenario["short_window_minutes"], f"{context}.short_window_minutes", minimum=1
    )
    if short_minutes >= long_minutes:
        raise ContractError(f"{context}: short_window_minutes 必须小于 window_minutes")

    label_keys = require_string_list(scenario["metric_label_keys"], f"{context}.metric_label_keys")
    disallowed = set(label_keys) - set(policy["allowed_metric_labels"])
    if disallowed:
        raise ContractError(
            f"{context}.metric_label_keys 含未批准或高基数字段: {', '.join(sorted(disallowed))}"
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
        raise ContractError(f"{context}.collector.queue_size 不能超过 queue_capacity")
    if collector["sent"] + collector["failed_to_send"] > collector["accepted"]:
        raise ContractError(f"{context}.collector 发送与失败数不能超过 accepted")

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
        raise ContractError(f"{context}.events 必须是非空数组")
    events = [validate_event(item, f"{context}.events[{event_index}]") for event_index, item in enumerate(scenario["events"])]
    request_ids = [str(event["request_id"]) for event in events]
    if len(set(request_ids)) != len(request_ids):
        raise ContractError(f"{context}.events 含重复 request_id")
    timestamps = [parse_timestamp(event["timestamp"], f"{context}.events.timestamp") for event in events]
    if timestamps != sorted(timestamps):
        raise ContractError(f"{context}.events 必须按 timestamp 升序")
    if timestamps[-1] - timestamps[0] > timedelta(minutes=long_minutes):
        raise ContractError(f"{context}.events 超出 window_minutes")
    cutoff = timestamps[-1] - timedelta(minutes=short_minutes)
    if not any(timestamp >= cutoff for timestamp in timestamps):
        raise ContractError(f"{context} 短窗口没有事件")

    if not isinstance(scenario["traces"], list):
        raise ContractError(f"{context}.traces 必须是数组")
    traces = [validate_trace(item, f"{context}.traces[{trace_index}]") for trace_index, item in enumerate(scenario["traces"])]
    trace_ids = [str(trace["trace_id"]) for trace in traces]
    if len(set(trace_ids)) != len(trace_ids):
        raise ContractError(f"{context}.traces 含重复 trace_id")
    referenced = {str(event["trace_id"]) for event in events if event["trace_id"] is not None}
    if referenced - set(trace_ids):
        raise ContractError(f"{context}.events 引用了不存在的 trace")
    if set(trace_ids) - referenced:
        raise ContractError(f"{context}.traces 含未被事件引用的 trace")

    event_by_trace = {
        str(event["trace_id"]): event for event in events if event["trace_id"] is not None
    }
    for trace in traces:
        event = event_by_trace[str(trace["trace_id"])]
        root = next(span for span in trace["spans"] if span["parent_span_id"] is None)
        if root["service"] != event["service"]:
            raise ContractError(f"{context}: root span service 与事件不一致")
        if root["attributes"]["release"] != event["release"]:
            raise ContractError(f"{context}: root span release 与事件不一致")
        if root["status"] != event["status"]:
            raise ContractError(f"{context}: root span status 与事件不一致")
        if not math.isclose(float(root["duration_ms"]), float(event["latency_ms"]), abs_tol=1e-9):
            raise ContractError(f"{context}: root span duration 与事件 latency 不一致")
    return scenario


def validate_input(value: object) -> dict[str, Any]:
    data = require_exact_keys(value, {"policy", "slo", "scenarios"}, "input")
    policy = validate_policy(data["policy"])
    validate_slo(data["slo"])
    if not isinstance(data["scenarios"], list) or not data["scenarios"]:
        raise ContractError("scenarios 必须是非空数组")
    scenarios = [validate_scenario(item, index, policy) for index, item in enumerate(data["scenarios"])]
    names = [str(scenario["name"]) for scenario in scenarios]
    if len(set(names)) != len(names):
        raise ContractError("scenarios 含重复 name")
    return data


def nearest_rank_percentile(values: list[float], percentile: float) -> float:
    if not values:
        raise ContractError("分位数输入不能为空")
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def is_good_event(event: dict[str, Any], slo: dict[str, Any]) -> bool:
    return event["status"] in slo["good_statuses"] and float(event["latency_ms"]) <= float(
        slo["latency_objective_ms"]
    )


def burn_rate(events: list[dict[str, Any]], slo: dict[str, Any]) -> float:
    bad_fraction = sum(not is_good_event(event, slo) for event in events) / len(events)
    return bad_fraction / (1 - float(slo["target"]))


def window_events(scenario: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events = list(scenario["events"])
    end = parse_timestamp(events[-1]["timestamp"], "events[-1].timestamp")
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
        "long_burn_rate": burn_rate(events, slo),
        "short_burn_rate": burn_rate(short_events, slo),
        "error_budget_remaining_ratio": 1 - burn_rate(events, slo),
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
        escalate("page", "短/长窗口错误预算同时高速燃烧")
    elif long_burn >= float(policy["ticket_long_burn_rate"]):
        escalate("ticket", "长窗口错误预算消耗需要调查")

    safety_rate = indicators["safety_violation_rate"]
    if safety_rate is None:
        escalate("page", "没有已执行的安全检查，安全状态未知")
    elif float(safety_rate) > float(policy["max_safety_violation_rate"]):
        escalate("page", "安全违规率超过本地策略")

    telemetry_policy = scenario["telemetry_policy"]
    if telemetry_policy["content_capture_enabled"]:
        escalate("page", "本地策略不允许默认采集原始内容")
    if not telemetry_policy["redaction_check_passed"]:
        escalate("page", "遥测脱敏检查未通过")
    if int(telemetry_policy["retention_days"]) > int(policy["max_retention_days"]):
        escalate("page", "遥测保留期超过本地策略")

    collector = scenario["collector"]
    if float(indicators["collector_drop_rate"]) > float(policy["max_collector_drop_rate"]):
        escalate("page", "Collector 拒收或导出失败比例超过本地策略")
    if float(collector["last_export_age_seconds"]) > float(policy["max_export_age_seconds"]):
        escalate("page", "Collector 导出数据过旧，监控可能失明")
    if float(indicators["trace_completeness_rate"]) < float(
        policy["min_trace_completeness_rate"]
    ):
        escalate("page", "Trace 完整率低于本地策略")

    if float(indicators["p95_latency_ms"]) > float(policy["max_p95_latency_ms"]):
        escalate("ticket", "p95 延迟超过本地策略")
    if float(indicators["label_coverage_rate"]) < float(policy["min_label_coverage_rate"]):
        escalate("ticket", "质量标签覆盖率不足")
    quality_rate = indicators["quality_pass_rate"]
    if quality_rate is None:
        escalate("ticket", "没有质量标签，任务质量未知")
    elif float(quality_rate) < float(policy["min_quality_pass_rate"]):
        escalate("ticket", "已标签质量通过率低于本地策略")
    if float(indicators["safety_check_coverage_rate"]) < float(
        policy["min_safety_check_coverage_rate"]
    ):
        escalate("ticket", "安全检查覆盖率不足")
    if float(indicators["average_estimated_cost_usd"]) > float(
        policy["max_average_estimated_cost_usd"]
    ):
        escalate("ticket", "平均每请求估算成本超过本地策略")
    if float(indicators["average_agent_steps"]) > float(policy["max_average_agent_steps"]):
        escalate("ticket", "平均 Agent 步数超过本地策略")
    if float(indicators["average_total_tokens"]) > float(policy["max_average_total_tokens"]):
        escalate("ticket", "平均 token 数超过本地策略")

    resources = scenario["resources"]
    if float(resources["cpu_utilization"]) > float(policy["max_cpu_utilization"]):
        escalate("ticket", "USE: CPU 利用率超过本地调查线")
    if int(resources["queue_depth"]) > int(policy["max_queue_depth"]):
        escalate("ticket", "USE: 资源队列饱和度超过本地调查线")
    if int(resources["resource_error_count"]) > 0:
        escalate("ticket", "USE: 资源错误计数非零")

    return Decision(
        scenario_name=str(scenario["name"]),
        action=action,
        reasons=tuple(reasons),
        indicators=indicators,
        evidence_fingerprint=fingerprint(scenario, policy, slo),
    )


def select_scenarios(
    scenarios: Iterable[dict[str, Any]], wanted: str | None
) -> list[dict[str, Any]]:
    selected = [scenario for scenario in scenarios if wanted is None or scenario["name"] == wanted]
    if wanted is not None and not selected:
        raise ContractError(f"未找到 scenario={wanted}")
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
            f"trace={float(indicators['trace_completeness_rate']):.3f}"
        )
        if decision.reasons:
            for reason in decision.reasons:
                print(f"  - {reason}")
        else:
            print("  - 满足全部本地教学规则")
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
