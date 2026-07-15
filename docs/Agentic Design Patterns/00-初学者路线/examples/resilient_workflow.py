"""Offline, deterministic demonstration of a recoverable agentic workflow.

This module intentionally uses only the Python standard library.  It teaches
architecture patterns; it is not a production approval or durability system.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Mapping


STATE_VERSION = 2
CHECKPOINT_FORMAT = "resilient-workflow-checkpoint"
BRANCHES = ("input", "policy")
STAGES = {
    "start",
    "awaiting_approval",
    "checks",
    "evaluate",
    "execute",
    "done",
    "failed",
    "canceled",
}
TERMINAL_STAGES = {"done", "failed", "canceled"}
TASK_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")

CheckResult = dict[str, Any]
CheckFunction = Callable[[str, int], CheckResult]


class WorkflowError(RuntimeError):
    """Raised when input, checkpoint, or recovery evidence is unsafe."""


class SimulatedCrash(RuntimeError):
    """Raised only by the teaching switch after the side effect commits."""


def canonical_json(value: Any) -> str:
    """Return a stable JSON representation suitable for local fingerprints."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def action_for(task_id: str) -> dict[str, str]:
    return {
        "kind": "publish_summary",
        "target": f"teaching-outbox/{task_id}.json",
    }


def new_state(task_id: str, risk: str) -> dict[str, Any]:
    if not TASK_ID_PATTERN.fullmatch(task_id):
        raise WorkflowError("task_id 只能使用 1–64 位 ASCII 字母、数字、点、下划线或连字符")
    if risk not in {"low", "high"}:
        raise WorkflowError("risk 必须是 low 或 high")
    return {
        "version": STATE_VERSION,
        "task_id": task_id,
        "risk": risk,
        "stage": "start",
        "revision": 0,
        "action": action_for(task_id),
        "approval": None,
        "checks": {},
        "attempts": {},
        "receipt": None,
        "events": [],
    }


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise WorkflowError(f"{label} 字段不匹配；缺失={missing}，多余={extra}")


def _validate_check(name: str, result: Any) -> None:
    if not isinstance(result, dict):
        raise WorkflowError(f"检查 {name} 必须是 JSON 对象")
    _require_exact_keys(result, {"ok", "category", "evidence"}, f"检查 {name}")
    if not isinstance(result["ok"], bool):
        raise WorkflowError(f"检查 {name}.ok 必须是布尔值")
    if result["category"] not in {"ok", "transient", "permanent"}:
        raise WorkflowError(f"检查 {name}.category 非法")
    if result["ok"] is not (result["category"] == "ok"):
        raise WorkflowError(f"检查 {name} 的 ok 与 category 矛盾")
    if not isinstance(result["evidence"], str) or not result["evidence"]:
        raise WorkflowError(f"检查 {name}.evidence 必须是非空字符串")


def validate_state(state: Any) -> None:
    """Validate the complete checkpoint state without trying to repair it."""

    if not isinstance(state, dict):
        raise WorkflowError("state 必须是 JSON 对象")
    expected = {
        "version",
        "task_id",
        "risk",
        "stage",
        "revision",
        "action",
        "approval",
        "checks",
        "attempts",
        "receipt",
        "events",
    }
    _require_exact_keys(state, expected, "state")

    if state["version"] != STATE_VERSION:
        raise WorkflowError("检查点版本不受支持，拒绝猜测迁移")
    if not isinstance(state["task_id"], str) or not TASK_ID_PATTERN.fullmatch(
        state["task_id"]
    ):
        raise WorkflowError("检查点 task_id 非法")
    if state["risk"] not in {"low", "high"}:
        raise WorkflowError("检查点 risk 非法")
    if state["stage"] not in STAGES:
        raise WorkflowError("检查点 stage 非法")
    if isinstance(state["revision"], bool) or not isinstance(state["revision"], int):
        raise WorkflowError("检查点 revision 必须是整数")
    if state["revision"] < 0:
        raise WorkflowError("检查点 revision 不能为负数")

    if not isinstance(state["action"], dict):
        raise WorkflowError("action 必须是 JSON 对象")
    _require_exact_keys(state["action"], {"kind", "target"}, "action")
    if state["action"] != action_for(state["task_id"]):
        raise WorkflowError("action 与 task_id 不一致，拒绝执行被篡改的动作")

    approval = state["approval"]
    if approval is not None:
        if not isinstance(approval, dict):
            raise WorkflowError("approval 必须是对象或 null")
        _require_exact_keys(
            approval,
            {"decision", "action_fingerprint", "based_on_revision"},
            "approval",
        )
        if approval["decision"] not in {"approved", "rejected"}:
            raise WorkflowError("approval.decision 非法")
        if approval["action_fingerprint"] != fingerprint(state["action"]):
            raise WorkflowError("审批绑定的动作与当前动作不一致")
        if isinstance(approval["based_on_revision"], bool) or not isinstance(
            approval["based_on_revision"], int
        ):
            raise WorkflowError("approval.based_on_revision 必须是整数")
        if not 0 <= approval["based_on_revision"] <= state["revision"]:
            raise WorkflowError("approval.based_on_revision 超出状态历史")
    if state["risk"] == "low" and approval is not None:
        raise WorkflowError("低风险教学路径不应包含审批记录")
    if state["stage"] == "awaiting_approval" and approval is not None:
        raise WorkflowError("等待审批阶段不能预先包含审批决定")
    if state["stage"] == "canceled":
        if approval is None or approval["decision"] != "rejected":
            raise WorkflowError("canceled 终态必须有 rejected 审批")
    elif approval is not None and approval["decision"] == "rejected":
        raise WorkflowError("rejected 审批只能对应 canceled 终态")
    if state["risk"] == "high" and state["stage"] in {
        "checks",
        "evaluate",
        "execute",
        "done",
        "failed",
    }:
        if approval is None or approval["decision"] != "approved":
            raise WorkflowError("高风险路径越过了有效审批")

    if not isinstance(state["checks"], dict):
        raise WorkflowError("checks 必须是对象")
    if not set(state["checks"]).issubset(BRANCHES):
        raise WorkflowError("checks 包含未知分支")
    for name, result in state["checks"].items():
        _validate_check(name, result)

    if not isinstance(state["attempts"], dict):
        raise WorkflowError("attempts 必须是对象")
    if not set(state["attempts"]).issubset(BRANCHES):
        raise WorkflowError("attempts 包含未知分支")
    for name, count in state["attempts"].items():
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise WorkflowError(f"attempts.{name} 必须是正整数")

    receipt = state["receipt"]
    if receipt is not None:
        _validate_receipt(receipt, state)
    if state["stage"] == "done" and receipt is None:
        raise WorkflowError("done 终态必须包含动作回执")
    if state["stage"] != "done" and receipt is not None:
        raise WorkflowError("只有 done 终态可以把动作回执写入检查点")

    if not isinstance(state["events"], list):
        raise WorkflowError("events 必须是数组")
    for expected_revision, event in enumerate(state["events"], start=1):
        if not isinstance(event, dict):
            raise WorkflowError("event 必须是对象")
        _require_exact_keys(event, {"revision", "name"}, "event")
        if event["revision"] != expected_revision:
            raise WorkflowError("事件 revision 必须连续递增")
        if not isinstance(event["name"], str) or not event["name"]:
            raise WorkflowError("事件 name 必须是非空字符串")
    if state["revision"] != len(state["events"]):
        raise WorkflowError("state.revision 必须等于事件数")


def append_event(state: dict[str, Any], name: str) -> None:
    state["revision"] += 1
    state["events"].append({"revision": state["revision"], "name": name})


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"无法读取{label}：{exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowError(f"{label}顶层必须是 JSON 对象")
    return value


def load_state(path: Path, task_id: str, risk: str) -> dict[str, Any]:
    if not path.exists():
        return new_state(task_id, risk)
    envelope = _read_json_object(path, "检查点")
    _require_exact_keys(envelope, {"format", "state", "sha256"}, "检查点封装")
    if envelope["format"] != CHECKPOINT_FORMAT:
        raise WorkflowError("检查点格式标识不受支持")
    if not isinstance(envelope["sha256"], str) or envelope["sha256"] != fingerprint(
        envelope["state"]
    ):
        raise WorkflowError("检查点完整性校验失败")
    state = envelope["state"]
    validate_state(state)
    if state["task_id"] != task_id:
        raise WorkflowError("命令行 task_id 与已有检查点不一致")
    if state["risk"] != risk:
        raise WorkflowError("命令行 risk 与已有检查点不一致")
    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    validate_state(state)
    envelope = {
        "format": CHECKPOINT_FORMAT,
        "state": state,
        "sha256": fingerprint(state),
    }
    temporary = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise WorkflowError(f"无法原子保存检查点：{exc}") from exc


def route(state: Mapping[str, Any]) -> str:
    return "approval" if state["risk"] == "high" else "parallel_checks"


def default_check(name: str, attempt: int) -> CheckResult:
    evidence = {
        "input": "required fields present",
        "policy": "policy rule matched",
    }
    return {"ok": True, "category": "ok", "evidence": evidence[name]}


def _run_one_check(
    name: str,
    starting_attempts: int,
    check: CheckFunction,
    max_attempts: int,
) -> tuple[CheckResult, int]:
    attempts = starting_attempts
    if attempts >= max_attempts:
        raise WorkflowError(f"检查 {name} 的重试预算已经耗尽")
    while attempts < max_attempts:
        attempts += 1
        try:
            result = check(name, attempts)
        except WorkflowError:
            raise
        except Exception as exc:
            raise WorkflowError(
                f"检查 {name} 未按契约返回结果：{type(exc).__name__}"
            ) from exc
        _validate_check(name, result)
        if result["ok"] or result["category"] != "transient":
            return result, attempts
    return result, attempts


def run_parallel_checks(
    state: Mapping[str, Any],
    check: CheckFunction = default_check,
    max_attempts: int = 2,
) -> tuple[dict[str, CheckResult], dict[str, int]]:
    """Fan out read-only checks, then join without shared worker mutation."""

    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
        raise WorkflowError("max_attempts 必须是正整数")
    if max_attempts < 1:
        raise WorkflowError("max_attempts 必须是正整数")
    starting = {name: int(state["attempts"].get(name, 0)) for name in BRANCHES}
    with ThreadPoolExecutor(max_workers=len(BRANCHES)) as pool:
        futures = {
            name: pool.submit(_run_one_check, name, starting[name], check, max_attempts)
            for name in BRANCHES
        }
        completed = {name: future.result() for name, future in futures.items()}
    results = {name: completed[name][0] for name in BRANCHES}
    attempts = {name: completed[name][1] for name in BRANCHES}
    return results, attempts


def evaluate(state: Mapping[str, Any]) -> bool:
    return set(state["checks"]) == set(BRANCHES) and all(
        result["ok"] is True for result in state["checks"].values()
    )


def action_id_for(state: Mapping[str, Any]) -> str:
    return fingerprint({"task_id": state["task_id"], "action": state["action"]})


def _validate_receipt(receipt: Any, state: Mapping[str, Any]) -> None:
    if not isinstance(receipt, dict):
        raise WorkflowError("receipt 必须是对象或 null")
    _require_exact_keys(
        receipt,
        {"action_id", "task_id", "action_fingerprint", "outcome"},
        "receipt",
    )
    expected = {
        "action_id": action_id_for(state),
        "task_id": state["task_id"],
        "action_fingerprint": fingerprint(state["action"]),
        "outcome": "published",
    }
    if receipt != expected:
        raise WorkflowError("动作回执与当前任务不一致")


def perform_action(
    receipt_path: Path,
    state: Mapping[str, Any],
    crash_after_commit: bool = False,
) -> tuple[dict[str, str], bool]:
    """Commit one local side effect and recover it by deterministic action ID."""

    expected: dict[str, str] = {
        "action_id": action_id_for(state),
        "task_id": state["task_id"],
        "action_fingerprint": fingerprint(state["action"]),
        "outcome": "published",
    }
    if receipt_path.exists():
        existing = _read_json_object(receipt_path, "动作回执")
        if existing != expected:
            raise WorkflowError("已有动作回执属于另一个任务，拒绝覆盖")
        return expected, True

    temporary = receipt_path.with_name(receipt_path.name + ".tmp")
    try:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            json.dumps(expected, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, receipt_path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise WorkflowError(f"无法提交动作回执：{exc}") from exc
    if crash_after_commit:
        raise SimulatedCrash("模拟：动作已提交，但检查点尚未更新")
    return expected, False


def make_demo_check(transient_once: bool, permanent_policy_failure: bool) -> CheckFunction:
    def check(name: str, attempt: int) -> CheckResult:
        if name == "policy" and permanent_policy_failure:
            return {
                "ok": False,
                "category": "permanent",
                "evidence": "policy explicitly denied the action",
            }
        if name == "policy" and transient_once and attempt == 1:
            return {
                "ok": False,
                "category": "transient",
                "evidence": "simulated dependency timeout",
            }
        return default_check(name, attempt)

    return check


def run(
    checkpoint_path: Path,
    receipt_path: Path,
    task_id: str,
    risk: str,
    decision: str | None = None,
    check: CheckFunction = default_check,
    max_attempts: int = 2,
    crash_after_commit: bool = False,
) -> dict[str, Any]:
    if decision not in {None, "approve", "reject"}:
        raise WorkflowError("decision 必须是 approve、reject 或留空")
    if risk == "low" and decision is not None:
        raise WorkflowError("低风险路径不接受审批决定")
    state = load_state(checkpoint_path, task_id, risk)
    if state["stage"] in TERMINAL_STAGES:
        return state

    if state["stage"] == "start":
        selected = route(state)
        state["stage"] = "awaiting_approval" if selected == "approval" else "checks"
        append_event(state, f"routed:{selected}")
        save_state(checkpoint_path, state)

    if state["stage"] == "awaiting_approval":
        if decision is None:
            if not state["events"] or state["events"][-1]["name"] != "paused_for_approval":
                append_event(state, "paused_for_approval")
                save_state(checkpoint_path, state)
            return state
        state["approval"] = {
            "decision": "approved" if decision == "approve" else "rejected",
            "action_fingerprint": fingerprint(state["action"]),
            "based_on_revision": state["revision"],
        }
        if decision == "reject":
            state["stage"] = "canceled"
            append_event(state, "approval:rejected")
            save_state(checkpoint_path, state)
            return state
        state["stage"] = "checks"
        append_event(state, "approval:approved")
        save_state(checkpoint_path, state)

    if state["stage"] == "checks":
        results, attempts = run_parallel_checks(state, check, max_attempts)
        state["checks"] = results
        state["attempts"] = attempts
        state["stage"] = "evaluate"
        append_event(state, "parallel_checks:joined")
        save_state(checkpoint_path, state)

    if state["stage"] == "evaluate":
        if not evaluate(state):
            state["stage"] = "failed"
            append_event(state, "evaluation:failed")
            save_state(checkpoint_path, state)
            return state
        if state["risk"] == "high":
            approval = state["approval"]
            if approval is None or approval["decision"] != "approved":
                raise WorkflowError("高风险动作缺少有效批准")
            if approval["action_fingerprint"] != fingerprint(state["action"]):
                raise WorkflowError("动作在批准后发生变化，原批准已失效")
        state["stage"] = "execute"
        append_event(state, "evaluation:passed")
        save_state(checkpoint_path, state)

    if state["stage"] == "execute":
        receipt, recovered = perform_action(
            receipt_path,
            state,
            crash_after_commit=crash_after_commit,
        )
        state["receipt"] = receipt
        state["stage"] = "done"
        append_event(
            state,
            "action:recovered_existing_receipt" if recovered else "action:committed",
        )
        save_state(checkpoint_path, state)

    return state


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--task-id", default="demo-001")
    parser.add_argument("--risk", choices=("low", "high"), required=True)
    parser.add_argument("--decision", choices=("approve", "reject"))
    parser.add_argument("--simulate-transient-once", action="store_true")
    parser.add_argument("--simulate-permanent-policy-failure", action="store_true")
    parser.add_argument("--crash-after-commit", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    check = make_demo_check(
        transient_once=args.simulate_transient_once,
        permanent_policy_failure=args.simulate_permanent_policy_failure,
    )
    try:
        state = run(
            checkpoint_path=args.checkpoint,
            receipt_path=args.receipt,
            task_id=args.task_id,
            risk=args.risk,
            decision=args.decision,
            check=check,
            crash_after_commit=args.crash_after_commit,
        )
    except SimulatedCrash as exc:
        print(json.dumps({"stage": "simulated_crash", "message": str(exc)}, ensure_ascii=False))
        return 5
    except WorkflowError as exc:
        print(json.dumps({"stage": "error", "message": str(exc)}, ensure_ascii=False))
        return 2

    print(json.dumps(state, ensure_ascii=False, indent=2))
    return {
        "done": 0,
        "awaiting_approval": 3,
        "canceled": 4,
        "failed": 1,
    }.get(state["stage"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
