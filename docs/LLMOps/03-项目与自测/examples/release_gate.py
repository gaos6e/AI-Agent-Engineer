"""离线 LLMOps 发布与在线观察门：只读取本地 JSON，不调用外部 API。"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST = BASE_DIR / "release_candidates.json"
DEFAULT_OBSERVATIONS = BASE_DIR / "online_observations.json"
MUTABLE_MARKERS = {"latest", "current", "production", "champion", "main", "master"}


class ContractError(ValueError):
    """输入 JSON 不符合本项目的严格契约。"""


@dataclass(frozen=True)
class Decision:
    """一次门禁判定；reasons 为空表示可继续。"""

    subject_id: str
    action: str
    reasons: tuple[str, ...]
    evidence_fingerprint: str

    @property
    def passed(self) -> bool:
        return self.action in {"promote", "continue"}


def load_json(path: Path) -> dict[str, Any]:
    """以 UTF-8 读取 JSON 对象。"""
    def reject_nonstandard_number(value: str) -> None:
        raise ContractError(f"{path.name} 含 JSON 标准之外的数值: {value}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle, parse_constant=reject_nonstandard_number)
    if not isinstance(data, dict):
        raise ContractError(f"{path.name} 顶层必须是对象")
    return data


def fingerprint(*values: object) -> str:
    """为参与决策的证据生成稳定短指纹，便于审计复算。"""
    payload = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def require_exact_keys(
    value: object,
    required: set[str],
    context: str,
    optional: set[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{context} 必须是对象")
    optional = optional or set()
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        raise ContractError(f"{context} 缺少字段: {', '.join(sorted(missing))}")
    if extra:
        raise ContractError(f"{context} 含未知字段: {', '.join(sorted(extra))}")
    return value


def require_list(value: object, context: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise ContractError(f"{context} 必须是非空数组")
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


def is_fixed_identifier(value: object) -> bool:
    """教学性检查：拒绝空值和常见浮动别名，不替代供应商合同核验。"""
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value.strip().lower() not in MUTABLE_MARKERS
    )


def require_fixed(value: object, context: str) -> str:
    if not is_fixed_identifier(value):
        raise ContractError(f"{context} 必须是非空且非浮动标识，当前={value!r}")
    return str(value)


POLICY_KEYS = {
    "version",
    "required_tests",
    "min_task_success_delta",
    "min_critical_success_delta",
    "max_safety_violation_rate",
    "min_safety_samples",
    "max_latency_increase_ratio",
    "max_cost_increase_ratio",
    "human_approval_required",
    "online_min_samples",
    "online_max_task_drop",
    "online_max_critical_drop",
    "online_max_provider_error_rate",
    "online_max_provider_shift_score",
    "online_max_latency_increase_ratio",
    "online_max_cost_increase_ratio",
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
    "release_id",
    "window_id",
    "sample_count",
    "task_success_rate",
    "critical_slice_success_rate",
    "safety_violation_rate",
    "p95_latency_ms",
    "actual_cost_usd_per_1k_requests",
    "provider_error_rate",
    "provider_output_shift_score",
    "trace_schema_complete",
    "redaction_check_passed",
    "fallback_ready",
}


def validate_policy(value: object) -> dict[str, Any]:
    policy = require_exact_keys(value, POLICY_KEYS, "policy")
    require_fixed(policy["version"], "policy.version")
    tests = require_list(policy["required_tests"], "policy.required_tests")
    if any(not is_fixed_identifier(item) for item in tests):
        raise ContractError("policy.required_tests 只能包含非空固定名称")
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
        require_number(policy[key], f"policy.{key}", minimum=0)
    for key in ("min_safety_samples", "online_min_samples"):
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


def validate_candidate(value: object, index: int) -> dict[str, Any]:
    context = f"candidates[{index}]"
    candidate = require_exact_keys(value, CANDIDATE_KEYS, context)
    require_fixed(candidate["release_id"], f"{context}.release_id")

    nested_specs: tuple[tuple[str, set[str]], ...] = (
        ("app", {"commit"}),
        ("api", {"contract_version", "sdk_lock_hash"}),
        ("prompt", {"version", "digest"}),
        ("context", {"policy_version"}),
        ("retrieval", {"snapshot", "config_version"}),
        ("model", {"provider", "model_snapshot", "parameters_version"}),
        ("policies", {"guardrail_version", "data_handling_version"}),
        ("evaluation", {"suite_version", "dataset_version", "rubric_version", "grader_version"}),
        ("routing", {"policy_version", "fallback_manifest"}),
        ("pricing", {"policy_version"}),
    )
    for name, keys in nested_specs:
        item = require_exact_keys(candidate[name], keys, f"{context}.{name}")
        for key in keys:
            require_fixed(item[key], f"{context}.{name}.{key}")

    tools = require_list(candidate["tools"], f"{context}.tools")
    for tool_index, tool_value in enumerate(tools):
        tool = require_exact_keys(
            tool_value,
            {"name", "schema_version", "implementation_version"},
            f"{context}.tools[{tool_index}]",
        )
        for key in tool:
            require_fixed(tool[key], f"{context}.tools[{tool_index}].{key}")

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
    validate_policy(manifest["policy"])
    baseline = require_exact_keys(manifest["baseline"], {"release_id", "metrics"}, "baseline")
    require_fixed(baseline["release_id"], "baseline.release_id")
    validate_metrics(baseline["metrics"], "baseline.metrics")
    candidates = require_list(manifest["candidates"], "candidates")
    seen: set[str] = set()
    for index, candidate_value in enumerate(candidates):
        candidate = validate_candidate(candidate_value, index)
        release_id = str(candidate["release_id"])
        if release_id in seen:
            raise ContractError(f"重复 release_id: {release_id}")
        seen.add(release_id)
    return manifest


def validate_observations(value: object) -> dict[str, Any]:
    bundle = require_exact_keys(value, {"schema_version", "observations"}, "observations")
    require_fixed(bundle["schema_version"], "observations.schema_version")
    observations = require_list(bundle["observations"], "observations.observations")
    seen: set[str] = set()
    for index, item_value in enumerate(observations):
        context = f"observations[{index}]"
        item = require_exact_keys(item_value, OBSERVATION_KEYS, context)
        for key in ("observation_id", "release_id", "window_id"):
            require_fixed(item[key], f"{context}.{key}")
        require_integer(item["sample_count"], f"{context}.sample_count")
        for key in (
            "task_success_rate",
            "critical_slice_success_rate",
            "safety_violation_rate",
            "provider_error_rate",
            "provider_output_shift_score",
        ):
            require_number(item[key], f"{context}.{key}", minimum=0, maximum=1)
        for key in (
            "p95_latency_ms",
            "actual_cost_usd_per_1k_requests",
        ):
            require_number(item[key], f"{context}.{key}", minimum=0)
        for key in ("trace_schema_complete", "redaction_check_passed", "fallback_ready"):
            require_bool(item[key], f"{context}.{key}")
        observation_id = str(item["observation_id"])
        if observation_id in seen:
            raise ContractError(f"重复 observation_id: {observation_id}")
        seen.add(observation_id)
    return bundle


def candidate_decision(
    candidate: dict[str, Any], baseline: dict[str, Any], policy: dict[str, Any]
) -> Decision:
    """根据已通过契约校验的证据决定是否允许进入 Canary。"""
    reasons: list[str] = []
    for test_name in policy["required_tests"]:
        if candidate["tests"].get(test_name) is not True:
            reasons.append(f"必需测试未通过: {test_name}")

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
        (float(metrics["task_success_rate"]) < minimum_task, f"任务成功率低于 {minimum_task:.3f}"),
        (
            float(metrics["critical_slice_success_rate"]) < minimum_critical,
            f"高风险切片成功率低于 {minimum_critical:.3f}",
        ),
        (
            float(metrics["safety_violation_rate"]) > float(policy["max_safety_violation_rate"]),
            "安全违规率超过策略上限",
        ),
        (
            int(metrics["safety_sample_count"]) < int(policy["min_safety_samples"]),
            "安全切片样本量不足",
        ),
        (float(metrics["p95_latency_ms"]) > maximum_latency, f"p95 延迟超过 {maximum_latency:.0f}ms"),
        (
            float(metrics["estimated_cost_usd_per_1k_requests"]) > maximum_cost,
            f"估算成本超过每千请求 {maximum_cost:.2f} 美元的本地练习上限",
        ),
    )
    reasons.extend(message for failed, message in checks if failed)

    operations = candidate["operations"]
    operation_messages = {
        "trace_schema_complete": "Trace schema 不完整",
        "redaction_check_passed": "脱敏检查未通过",
        "canary_plan_ready": "Canary 计划未就绪",
        "rollback_manifest_ready": "回滚 manifest 未就绪",
    }
    for key, message in operation_messages.items():
        if operations[key] is not True:
            reasons.append(message)
    if policy["human_approval_required"] and not operations["human_approval_recorded"]:
        reasons.append("高风险发布缺少人工审批记录")

    return Decision(
        subject_id=str(candidate["release_id"]),
        action="block" if reasons else "promote",
        reasons=tuple(reasons),
        evidence_fingerprint=fingerprint(candidate, baseline, policy),
    )


def observation_decision(
    observation: dict[str, Any], baseline: dict[str, Any], policy: dict[str, Any]
) -> Decision:
    """把 Canary 观察转成继续、调查、暂停、降级、回滚或人工复核动作。"""
    metrics = baseline["metrics"]
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

    if int(observation["sample_count"]) < int(policy["online_min_samples"]):
        escalate("investigate", "观察样本量不足，不能自动扩大流量")
    if not observation["trace_schema_complete"]:
        escalate("rollback", "线上 Trace schema 不完整，无法可靠取证")
    if not observation["redaction_check_passed"]:
        escalate("rollback", "线上脱敏检查失败")
    if float(observation["safety_violation_rate"]) > float(policy["max_safety_violation_rate"]):
        escalate("rollback", "线上出现超过策略上限的安全违规")

    minimum_task = float(metrics["task_success_rate"]) - float(policy["online_max_task_drop"])
    minimum_critical = float(metrics["critical_slice_success_rate"]) - float(
        policy["online_max_critical_drop"]
    )
    if float(observation["task_success_rate"]) < minimum_task:
        escalate("rollback", f"线上任务成功率低于 {minimum_task:.3f}")
    if float(observation["critical_slice_success_rate"]) < minimum_critical:
        escalate("rollback", f"线上高风险切片成功率低于 {minimum_critical:.3f}")

    provider_degraded = (
        float(observation["provider_error_rate"])
        > float(policy["online_max_provider_error_rate"])
    )
    provider_shifted = (
        float(observation["provider_output_shift_score"])
        > float(policy["online_max_provider_shift_score"])
    )
    if provider_degraded or provider_shifted:
        provider_reason = "供应商错误率或输出漂移分数超过本地策略上限"
        if observation["fallback_ready"]:
            escalate("fallback", provider_reason + "，切换到已验证的降级路径")
        else:
            escalate("human_review", provider_reason + "，但没有已验证的降级路径")

    maximum_latency = float(metrics["p95_latency_ms"]) * (
        1 + float(policy["online_max_latency_increase_ratio"])
    )
    maximum_cost = float(metrics["estimated_cost_usd_per_1k_requests"]) * (
        1 + float(policy["online_max_cost_increase_ratio"])
    )
    if float(observation["p95_latency_ms"]) > maximum_latency:
        escalate("pause", f"线上 p95 延迟超过 {maximum_latency:.0f}ms")
    if float(observation["actual_cost_usd_per_1k_requests"]) > maximum_cost:
        escalate("pause", f"线上成本超过每千请求 {maximum_cost:.2f} 美元的本地练习上限")

    return Decision(
        subject_id=str(observation["observation_id"]),
        action=action,
        reasons=tuple(reasons),
        evidence_fingerprint=fingerprint(observation, baseline, policy),
    )


def select_by_id(items: Iterable[dict[str, Any]], key: str, wanted: str | None) -> list[dict[str, Any]]:
    selected = [item for item in items if wanted is None or item[key] == wanted]
    if wanted is not None and not selected:
        raise ContractError(f"未找到 {key}={wanted}")
    return selected


def print_decisions(decisions: Iterable[Decision], policy_version: str) -> bool:
    """打印可审计结果，并返回是否全部可继续。"""
    all_passed = True
    for decision in decisions:
        all_passed = all_passed and decision.passed
        print(f"{decision.action.upper()}: {decision.subject_id}")
        print(f"  - policy={policy_version}")
        print(f"  - evidence={decision.evidence_fingerprint}")
        if decision.reasons:
            for reason in decision.reasons:
                print(f"  - {reason}")
        else:
            print("  - 所有本地练习门均满足")
    return all_passed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    candidate = subparsers.add_parser("candidate", help="检查候选发布是否可进入 Canary")
    candidate.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    candidate.add_argument("--release-id")

    observe = subparsers.add_parser("observe", help="根据线上观察决定继续、降级或回滚")
    observe.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    observe.add_argument("--observations", type=Path, default=DEFAULT_OBSERVATIONS)
    observe.add_argument("--observation-id")

    audit = subparsers.add_parser("audit", help="同时复算候选门与线上观察门")
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

    if args.command in {"candidate", "audit"}:
        candidates = select_by_id(manifest["candidates"], "release_id", args.release_id)
        decisions.extend(candidate_decision(item, baseline, policy) for item in candidates)

    if args.command in {"observe", "audit"}:
        bundle = validate_observations(load_json(args.observations))
        observations = select_by_id(
            bundle["observations"], "observation_id", args.observation_id
        )
        release_ids = {item["release_id"] for item in manifest["candidates"]}
        for observation in observations:
            if observation["release_id"] not in release_ids:
                raise ContractError(
                    f"观察 {observation['observation_id']} 引用了未知 release_id="
                    f"{observation['release_id']}"
                )
            decisions.append(observation_decision(observation, baseline, policy))

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
