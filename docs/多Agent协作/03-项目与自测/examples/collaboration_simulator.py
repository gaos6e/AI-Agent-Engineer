"""Deterministic, offline multi-agent coordination simulator.

This module models orchestration semantics only.  It makes no model or network
calls and uses synthetic outcomes supplied by a JSON fixture.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


TERMINAL_TASK_STATES = {"succeeded", "failed", "denied", "blocked"}


class ScenarioError(ValueError):
    """Raised when the fixture does not satisfy the scenario contract."""


def load_scenario(path: Path) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ScenarioError(f"non-standard JSON constant is forbidden: {value}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ScenarioError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ScenarioError(f"cannot read {path}: {exc}") from exc
    try:
        data = json.loads(
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
        self.roles = self._validate_roles(scenario.get("roles"))
        self.step_budget = self._positive_int(
            scenario.get("step_budget"), "step_budget"
        )
        self.tasks = self._validate_tasks(scenario.get("tasks"))
        self.events: list[dict[str, Any]] = []
        self.steps_used = 0
        self.accepted_result_keys: set[tuple[str, str]] = set()

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
            task = deepcopy(original)
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
            task.update(state="pending", attempts=0, result=None)
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
    ) -> None:
        item: dict[str, Any] = {
            "seq": len(self.events) + 1,
            "event": event,
            "task_id": task_id,
            "attempt": self.tasks[task_id]["attempts"],
        }
        if old_state is not None:
            item["from"] = old_state
        if new_state is not None:
            item["to"] = new_state
        if reason is not None:
            item["reason"] = reason
        self.events.append(item)

    def _transition(self, task_id: str, new_state: str, reason: str) -> None:
        task = self.tasks[task_id]
        old_state = task["state"]
        task["state"] = new_state
        self._record(
            "state_transition",
            task_id,
            old_state=old_state,
            new_state=new_state,
            reason=reason,
        )

    def accept_result(
        self, task_id: str, idempotency_key: str, payload: Any
    ) -> bool:
        """Accept a successful result once; return False for a duplicate."""
        if task_id not in self.tasks:
            raise ScenarioError(f"unknown task: {task_id}")
        if not isinstance(idempotency_key, str) or not idempotency_key:
            raise ScenarioError("idempotency_key must be a non-empty string")
        result_key = (task_id, idempotency_key)
        if result_key in self.accepted_result_keys:
            self._record("duplicate_result_ignored", task_id, reason=idempotency_key)
            return False
        task = self.tasks[task_id]
        if task["state"] in TERMINAL_TASK_STATES:
            self._record(
                "late_result_ignored",
                task_id,
                reason=f"task already {task['state']}",
            )
            return False
        self.accepted_result_keys.add(result_key)
        task["result"] = deepcopy(payload)
        self._transition(task_id, "succeeded", "accepted_result")
        return True

    def _block_failed_dependents(self) -> bool:
        changed = False
        for task_id, task in self.tasks.items():
            if task["state"] != "pending":
                continue
            bad = [
                dependency
                for dependency in task["requires"]
                if self.tasks[dependency]["state"] in {"failed", "denied", "blocked"}
            ]
            if bad:
                self._transition(
                    task_id, "blocked", f"dependency_not_successful:{','.join(bad)}"
                )
                changed = True
        return changed

    def _ready_tasks(self) -> list[str]:
        return sorted(
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
        task["attempts"] += 1
        self.steps_used += 1
        self._record("attempt_started", task_id)
        role_capabilities = self.roles[task["owner"]]
        if task["capability"] not in role_capabilities:
            self._transition(task_id, "denied", "owner_missing_capability")
            return
        index = min(task["attempts"] - 1, len(task["outcome_plan"]) - 1)
        outcome = task["outcome_plan"][index]
        if outcome == "success":
            key = f"{task_id}:attempt:{task['attempts']}"
            payload = task.get("result_payload", {"ok": True})
            self.accept_result(task_id, key, payload)
        elif outcome == "transient_error":
            if task["attempts"] < task["max_attempts"]:
                self._record("retry_scheduled", task_id, reason="transient_error")
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
        status = "failed"
        while True:
            self._block_failed_dependents()
            if all(
                task["state"] == "succeeded" for task in self.tasks.values()
            ):
                status = "succeeded"
                break
            if self.steps_used >= self.step_budget:
                status = "budget_exhausted"
                break
            ready = self._ready_tasks()
            if not ready:
                pending = [
                    task_id
                    for task_id, task in self.tasks.items()
                    if task["state"] == "pending"
                ]
                status = "deadlock" if pending else "failed"
                break
            self._execute(ready[0])
        return {
            "status": status,
            "steps_used": self.steps_used,
            "step_budget": self.step_budget,
            "tasks": {
                task_id: {
                    "owner": task["owner"],
                    "state": task["state"],
                    "attempts": task["attempts"],
                    "result": task["result"],
                }
                for task_id, task in sorted(self.tasks.items())
            },
            "events": deepcopy(self.events),
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path, help="UTF-8 JSON scenario")
    parser.add_argument(
        "--output", type=Path, help="optional JSON report path; stdout is always used"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        simulator = CollaborationSimulator(load_scenario(args.scenario))
        report = simulator.run()
        rendered = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
    except ScenarioError as exc:
        print(f"scenario error: {exc}", file=sys.stderr)
        return 2
    print(rendered)
    return 0 if report["status"] == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
