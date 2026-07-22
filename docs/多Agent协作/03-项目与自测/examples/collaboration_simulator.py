"""Deterministic, offline multi-agent coordination simulator.

This module models orchestration semantics only.  It makes no model or network
calls and uses synthetic outcomes supplied by a JSON fixture.
"""

from __future__ import annotations  # 允许在运行时延后解析类型注解。

import argparse  # 提供可复现实验的命令行入口。
import hashlib  # 为结果载荷生成稳定摘要，判断重试是否真正等价。
import json  # 读取场景 fixture，并输出可检查的执行报告。
import sys  # 将不可恢复的场景错误写入标准错误流。
from copy import deepcopy  # 隔离外部载荷，避免调用方事后篡改已接受结果。
from pathlib import Path  # 用跨平台路径对象承载 fixture 和报告文件。
from typing import Any  # 场景载荷来自 JSON，需在运行时逐层收窄类型。


TERMINAL_TASK_STATES = {  # 终态不能再被正常调度；冲突只会升级为人工复核。
    "succeeded",
    "failed",
    "denied",
    "blocked",
    "needs_review",
}
TASK_STATES = {"pending", "running"} | TERMINAL_TASK_STATES  # 合同允许出现的全部状态。
_ALLOWED_TASK_TRANSITIONS = {  # 显式状态机，拒绝“看似方便”的任意跳转。
    "pending": {"running", "blocked"},
    "running": {"pending", "succeeded", "failed", "denied", "needs_review"},
    # A result that was initially accepted can later conflict with a retry or
    # delayed receipt for the same idempotency key.  Escalating to review is
    # deliberately the only transition out of a successful teaching task.
    "succeeded": {"needs_review"},
    "failed": set(),
    "denied": set(),
    "blocked": set(),
    "needs_review": set(),
}


class ScenarioError(ValueError):
    """Raised when the fixture does not satisfy the scenario contract."""


def load_scenario(path: Path) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        # JSON 的 NaN/Infinity 没有跨实现的一致语义，不能作为协调协议输入。
        raise ScenarioError(f"non-standard JSON constant is forbidden: {value}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        # 普通 json.loads 会静默保留最后一个同名键；这里将歧义提升为输入错误。
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ScenarioError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        text = path.read_text(encoding="utf-8")  # fixture 一律按 UTF-8 解码，避免平台默认编码漂移。
    except OSError as exc:
        raise ScenarioError(f"cannot read {path}: {exc}") from exc
    try:
        data = json.loads(  # 在解析边界同时禁止非常量与重复键。
            text,
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicate_keys,
        )
    except ScenarioError:
        raise
    except json.JSONDecodeError as exc:
        raise ScenarioError(f"invalid JSON in {path}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ScenarioError("scenario root must be an object")
    return data


class CollaborationSimulator:
    """Run a small task graph with permissions, retries and a global budget."""

    def __init__(self, scenario: dict[str, Any]) -> None:
        if not isinstance(scenario, dict) or set(scenario) != {
            "roles", "step_budget", "tasks"
        }:
            raise ScenarioError(
                "scenario fields must be exactly: roles, step_budget, tasks"
            )
        self.roles = self._validate_roles(scenario.get("roles"))  # 先建立角色—能力边界。
        self.step_budget = self._positive_int(
            scenario.get("step_budget"), "step_budget"
        )
        self.tasks = self._validate_tasks(scenario.get("tasks"))  # 再解析带依赖的任务图。
        self.events: list[dict[str, Any]] = []  # 追加式事件日志是调试和评测的证据。
        self.steps_used = 0  # 全局预算，而不是每个 Agent 独立无限重试。
        # A key alone is not an intent.  Keep the example's explicitly local,
        # sorted-key JSON digest so a repeated delivery can be distinguished
        # from a conflicting delivery.
        self.accepted_result_digests: dict[tuple[str, str], str] = {}
        self._accepted_result_payloads: dict[tuple[str, str], Any] = {}

    @staticmethod
    def _positive_int(value: Any, field: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ScenarioError(f"{field} must be a positive integer")
        return value

    @staticmethod
    def _validate_roles(raw: Any) -> dict[str, set[str]]:
        if not isinstance(raw, dict) or not raw:
            raise ScenarioError("roles must be a non-empty object")
        roles: dict[str, set[str]] = {}
        for name, spec in raw.items():
            if not isinstance(name, str) or not name:
                raise ScenarioError("role names must be non-empty strings")
            if not isinstance(spec, dict):
                raise ScenarioError(f"role {name!r} must be an object")
            if set(spec) != {"capabilities"}:
                raise ScenarioError(
                    f"role {name!r} fields must be exactly: capabilities"
                )
            capabilities = spec.get("capabilities")
            if (
                not isinstance(capabilities, list)
                or not all(isinstance(item, str) and item for item in capabilities)
            ):
                raise ScenarioError(f"role {name!r} capabilities must be strings")
            if len(capabilities) != len(set(capabilities)):
                raise ScenarioError(f"role {name!r} capabilities must be unique")
            roles[name] = set(capabilities)
        return roles

    def _validate_tasks(self, raw: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(raw, list) or not raw:
            raise ScenarioError("tasks must be a non-empty array")
        tasks: dict[str, dict[str, Any]] = {}
        required_fields = {
            "id",
            "owner",
            "requires",
            "capability",
            "max_attempts",
            "outcome_plan",
        }
        allowed_fields = required_fields | {"result_payload"}
        for original in raw:
            if not isinstance(original, dict):
                raise ScenarioError("every task must be an object")
            missing = required_fields - original.keys()
            if missing:
                raise ScenarioError(f"task is missing fields: {sorted(missing)}")
            unknown = set(original) - allowed_fields
            if unknown:
                raise ScenarioError(f"task has unknown fields: {sorted(unknown)}")
            task = deepcopy(original)  # 不在原始 fixture 对象上写入运行时状态。
            task_id = task["id"]
            if not isinstance(task_id, str) or not task_id:
                raise ScenarioError("task id must be a non-empty string")
            if task_id in tasks:
                raise ScenarioError(f"duplicate task id: {task_id}")
            if task["owner"] not in self.roles:
                raise ScenarioError(f"unknown owner for task {task_id}")
            if (
                not isinstance(task["requires"], list)
                or not all(isinstance(item, str) and item for item in task["requires"])
            ):
                raise ScenarioError(f"requires must be an array for task {task_id}")
            if len(task["requires"]) != len(set(task["requires"])):
                raise ScenarioError(f"requires must be unique for task {task_id}")
            if not isinstance(task["capability"], str) or not task["capability"]:
                raise ScenarioError(f"capability must be a string for task {task_id}")
            task["max_attempts"] = self._positive_int(
                task["max_attempts"], f"{task_id}.max_attempts"
            )
            if (
                not isinstance(task["outcome_plan"], list)
                or not task["outcome_plan"]
                or not all(isinstance(item, str) and item for item in task["outcome_plan"])
            ):
                raise ScenarioError(f"outcome_plan must be non-empty for {task_id}")
            unsupported = sorted(
                set(task["outcome_plan"])
                - {"success", "transient_error", "policy_denied", "permanent_error"}
            )
            if unsupported:
                raise ScenarioError(
                    f"unsupported outcomes for {task_id}: {unsupported}"
                )
            task.update(  # 为每个任务补齐运行时字段，统一从 pending 开始。
                state="pending",
                state_version=0,
                attempts=0,
                result=None,
                result_trust="none",
                result_conflicts=[],
            )
            tasks[task_id] = task
        for task_id, task in tasks.items():
            for dependency in task["requires"]:
                if dependency not in tasks:
                    raise ScenarioError(
                        f"task {task_id} has unknown dependency {dependency}"
                    )
                if dependency == task_id:
                    raise ScenarioError(f"task {task_id} cannot depend on itself")
        return tasks

    def _record(
        self,
        event: str,
        task_id: str,
        *,
        old_state: str | None = None,
        new_state: str | None = None,
        reason: str | None = None,
        accepted_result_digest: str | None = None,
        received_result_digest: str | None = None,
    ) -> None:
        item: dict[str, Any] = {  # 每条证据记录都带单调序号和当前状态版本。
            "seq": len(self.events) + 1,
            "event": event,
            "task_id": task_id,
            "attempt": self.tasks[task_id]["attempts"],
            "state_version": self.tasks[task_id]["state_version"],
        }
        if old_state is not None:
            item["from"] = old_state
        if new_state is not None:
            item["to"] = new_state
        if reason is not None:
            item["reason"] = reason
        if accepted_result_digest is not None:
            item["accepted_result_digest"] = accepted_result_digest
        if received_result_digest is not None:
            item["received_result_digest"] = received_result_digest
        self.events.append(item)

    def _transition(self, task_id: str, new_state: str, reason: str) -> None:
        task = self.tasks[task_id]
        old_state = task["state"]
        if new_state not in TASK_STATES:
            raise ScenarioError(f"unknown task state: {new_state!r}")
        if new_state not in _ALLOWED_TASK_TRANSITIONS[old_state]:
            raise ScenarioError(
                f"illegal state transition for task {task_id!r}: "
                f"{old_state} -> {new_state}"
            )
        task["state"] = new_state  # 仅通过此函数改变状态，确保每次变化可审计。
        task["state_version"] += 1  # 版本号帮助识别延迟结果对应的旧状态。
        self._record(
            "state_transition",
            task_id,
            old_state=old_state,
            new_state=new_state,
            reason=reason,
        )

    @staticmethod
    def _result_digest(payload: Any) -> str:
        """Return a stable digest for a JSON-compatible result payload.

        The simulator deliberately rejects values that cannot appear in the
        fixture/protocol boundary.  In particular, ``NaN`` must not acquire a
        second, implementation-defined spelling in an idempotency comparison.
        """
        try:  # 固定排序、分隔符与 UTF-8 编码，保证同一 JSON 载荷得出同一摘要。
            rendered = json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise ScenarioError("result payload must be JSON-compatible") from exc
        return hashlib.sha256(rendered.encode("utf-8")).hexdigest()

    def accept_result(
        self, task_id: str, idempotency_key: str, payload: Any
    ) -> bool:
        """Accept a running task's result once; freeze conflicting duplicates.

        A duplicate delivery is harmless only when the task, idempotency key,
        and this simulator's sorted-key JSON result payload all match.  Reusing
        a key with a different
        payload is evidence that the coordinator cannot safely reconcile, so
        the task enters ``needs_review`` instead of silently retaining either
        answer.
        """
        if task_id not in self.tasks:
            raise ScenarioError(f"unknown task: {task_id}")
        if not isinstance(idempotency_key, str) or not idempotency_key:
            raise ScenarioError("idempotency_key must be a non-empty string")
        result_key = (task_id, idempotency_key)  # 幂等范围是“任务 + 意图键”，不是键字符串本身。
        digest = self._result_digest(payload)  # 比较摘要，而非依赖 Python 对复杂对象的相等语义。
        if result_key in self.accepted_result_digests:
            task = self.tasks[task_id]
            if self.accepted_result_digests[result_key] != digest:
                conflict_event_seq = len(self.events) + 1
                self._record(
                    "result_conflict_detected",
                    task_id,
                    reason="idempotency_key_reused_with_different_payload",
                    accepted_result_digest=self.accepted_result_digests[result_key],
                    received_result_digest=digest,
                )
                task["result_conflicts"].append(  # 保留双方载荷，供人工复核而非静默覆盖。
                    {
                        "idempotency_key": idempotency_key,
                        "accepted": {
                            "digest": self.accepted_result_digests[result_key],
                            "payload": deepcopy(
                                self._accepted_result_payloads[result_key]
                            ),
                        },
                        "received": {
                            "digest": digest,
                            "payload": deepcopy(payload),
                        },
                        "detected_event_seq": conflict_event_seq,
                        "state_version": task["state_version"],
                    }
                )
                # Do not expose the first result as an accepted answer after a
                # later receipt proves that the same intent is ambiguous.
                task["result"] = None  # 冲突后不能继续把先到结果展示为可信答案。
                task["result_trust"] = "conflicted"  # 信任状态与业务成功状态分开表达。
                if task["state"] != "needs_review":
                    self._transition(
                        task_id,
                        "needs_review",
                        "idempotency_payload_conflict",
                    )
                task["result_conflicts"][-1]["state_version"] = task[
                    "state_version"
                ]
                return False
            self._record("duplicate_result_ignored", task_id, reason=idempotency_key)  # 同载荷重放是安全的空操作。
            return False
        task = self.tasks[task_id]
        if task["state"] in TERMINAL_TASK_STATES:
            self._record(
                "late_result_ignored",
                task_id,
                reason=f"task already {task['state']}",
            )
            return False
        if task["state"] != "running":
            raise ScenarioError(
                f"cannot accept a result for task {task_id!r} while {task['state']}"
            )
        self.accepted_result_digests[result_key] = digest  # 先记住已接受的语义摘要。
        self._accepted_result_payloads[result_key] = deepcopy(payload)  # 保存副本以便后续冲突举证。
        task["result"] = deepcopy(payload)  # 报告使用隔离后的结果，防止外部可变引用。
        task["result_trust"] = "accepted"
        self._transition(task_id, "succeeded", "accepted_result")
        return True

    def _block_failed_dependents(self) -> bool:
        """Block every pending descendant before classifying a deadlock.

        Task fixtures need not be topologically ordered.  Repeating the pass to
        a fixed point prevents a one-hop block from leaving its later ancestor
        pending and being misreported as a dependency cycle.
        """
        changed = False
        while True:  # 反复传播失败，直到所有下游阻塞状态稳定下来。
            changed_this_pass = False
            for task_id, task in self.tasks.items():
                if task["state"] != "pending":
                    continue
                bad = [
                    dependency
                    for dependency in task["requires"]
                    if self.tasks[dependency]["state"]
                    in {"failed", "denied", "blocked", "needs_review"}
                ]
                if bad:
                    self._transition(
                        task_id,
                        "blocked",
                        f"dependency_not_successful:{','.join(bad)}",
                    )
                    changed = True
                    changed_this_pass = True
            if not changed_this_pass:
                return changed

    def _ready_tasks(self) -> list[str]:
        return sorted(  # 固定调度次序，让 fixture、测试与课堂复盘均可复现。
            task_id
            for task_id, task in self.tasks.items()
            if task["state"] == "pending"
            and all(
                self.tasks[dependency]["state"] == "succeeded"
                for dependency in task["requires"]
            )
        )

    def _execute(self, task_id: str) -> None:
        task = self.tasks[task_id]
        if task["state"] != "pending":
            raise ScenarioError(f"task {task_id!r} is not pending")
        task["attempts"] += 1  # 每次真正开始调度才计入该任务的尝试数。
        self.steps_used += 1  # 全局预算同时限制重试风暴和任务图规模。
        self._transition(task_id, "running", "scheduled")
        self._record("attempt_started", task_id)
        role_capabilities = self.roles[task["owner"]]  # 运行时再次执行最小权限检查。
        if task["capability"] not in role_capabilities:
            self._transition(task_id, "denied", "owner_missing_capability")
            return
        index = min(task["attempts"] - 1, len(task["outcome_plan"]) - 1)  # 计划耗尽后保持最后一个结果。
        outcome = task["outcome_plan"][index]  # fixture 驱动结果，示例不调用真实模型或网络。
        if outcome == "success":
            key = f"{task_id}:attempt:{task['attempts']}"
            payload = task.get("result_payload", {"ok": True})
            self.accept_result(task_id, key, payload)
        elif outcome == "transient_error":
            if task["attempts"] < task["max_attempts"]:
                self._record("retry_scheduled", task_id, reason="transient_error")
                self._transition(task_id, "pending", "transient_error")
            else:
                self._transition(
                    task_id, "failed", "transient_error_attempts_exhausted"
                )
        elif outcome == "policy_denied":
            self._transition(task_id, "denied", "fixture_policy_denied")
        elif outcome == "permanent_error":
            self._transition(task_id, "failed", "permanent_error")
        else:
            raise ScenarioError(f"unsupported outcome {outcome!r} for {task_id}")

    def run(self) -> dict[str, Any]:
        status = "failed"  # 保守默认值，只有明确满足完成条件才报告成功。
        while True:
            self._block_failed_dependents()  # 先传播依赖失败，避免把下游误判为死锁。
            if any(
                task["state"] == "needs_review" for task in self.tasks.values()
            ):
                status = "needs_review"
                break
            if all(
                task["state"] == "succeeded" for task in self.tasks.values()
            ):
                status = "succeeded"
                break
            if self.steps_used >= self.step_budget:
                status = "budget_exhausted"
                break
            ready = self._ready_tasks()  # 仅依赖全部成功的 pending 任务可以进入调度。
            if not ready:
                pending = [
                    task_id
                    for task_id, task in self.tasks.items()
                    if task["state"] == "pending"
                ]
                status = "deadlock" if pending else "failed"
                break
            self._execute(ready[0])  # 每轮只执行一个确定任务，使状态轨迹容易验证。
        return {
            "status": status,
            "steps_used": self.steps_used,
            "step_budget": self.step_budget,
            "tasks": {
                task_id: {
                    "owner": task["owner"],
                    "state": task["state"],
                    "state_version": task["state_version"],
                    "attempts": task["attempts"],
                    "result": task["result"],
                    "result_trust": task["result_trust"],
                    "result_conflicts": deepcopy(task["result_conflicts"]),
                }
                for task_id, task in sorted(self.tasks.items())
            },
            "events": deepcopy(self.events),
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)  # CLI 与测试共用同一场景合同。
    parser.add_argument("scenario", type=Path, help="UTF-8 JSON scenario")
    parser.add_argument(
        "--output", type=Path, help="optional JSON report path; stdout is always used"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)  # 允许测试传入 argv，同时保留真实命令行入口。
    try:
        simulator = CollaborationSimulator(load_scenario(args.scenario))  # 先严格加载，再创建隔离运行时。
        report = simulator.run()  # 运行结束后输出状态、任务快照和事件证据。
        rendered = json.dumps(report, ensure_ascii=False, indent=2)  # 保留中文，便于人工审阅。
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")  # 文件与 stdout 共享同一可复现报告。
    except ScenarioError as exc:
        print(f"scenario error: {exc}", file=sys.stderr)
        return 2
    print(rendered)
    return 0 if report["status"] == "succeeded" else 1  # 非成功执行也要让自动化调用方感知失败。


if __name__ == "__main__":
    raise SystemExit(main())
