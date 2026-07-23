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


STATE_VERSION = 3
CHECKPOINT_FORMAT = "resilient-workflow-checkpoint"
POLICY_REVISION = "teaching-policy-v1"
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


class DuplicateJsonKeyError(ValueError):
    """Raised when a persisted JSON object tries to define one key twice."""


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


def approval_fingerprint_for(state: Mapping[str, Any]) -> str:
    """Bind a high-risk decision to its action and already verified evidence."""

    return fingerprint(
        {
            "action": state["action"],
            "checks": state["checks"],
            "policy_revision": state["policy_revision"],
            "risk": state["risk"],
        }
    )


def new_state(task_id: str, risk: str) -> dict[str, Any]:
    if not TASK_ID_PATTERN.fullmatch(task_id):
        raise WorkflowError("task_id must use 1–64 ASCII letters, digits, dots, underscores, or hyphens")
    if risk not in {"low", "high"}:
        raise WorkflowError("risk must be low or high")
    return {
        "version": STATE_VERSION,
        "policy_revision": POLICY_REVISION,
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
        raise WorkflowError(f"{label} fields do not match; missing={missing}, extra={extra}")


def _validate_check(name: str, result: Any) -> None:
    if not isinstance(result, dict):
        raise WorkflowError(f"check {name} must be a JSON object")
    _require_exact_keys(result, {"ok", "category", "evidence"}, f"check {name}")
    if not isinstance(result["ok"], bool):
        raise WorkflowError(f"check {name}.ok must be Boolean")
    if result["category"] not in {"ok", "transient", "permanent"}:
        raise WorkflowError(f"check {name}.category is invalid")
    if result["ok"] is not (result["category"] == "ok"):
        raise WorkflowError(f"check {name} has contradictory ok and category")
    if not isinstance(result["evidence"], str) or not result["evidence"]:
        raise WorkflowError(f"check {name}.evidence must be a non-empty string")


def validate_state(state: Any) -> None:
    """Validate the complete checkpoint state without trying to repair it."""

    if not isinstance(state, dict):
        raise WorkflowError("state must be a JSON object")
    expected = {
        "version",
        "policy_revision",
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
        raise WorkflowError("checkpoint version is unsupported; refusing to guess a migration")
    if state["policy_revision"] != POLICY_REVISION:
        raise WorkflowError("checkpoint policy_revision is unsupported; refusing to guess a policy migration")
    if not isinstance(state["task_id"], str) or not TASK_ID_PATTERN.fullmatch(
        state["task_id"]
    ):
        raise WorkflowError("checkpoint task_id is invalid")
    if state["risk"] not in {"low", "high"}:
        raise WorkflowError("checkpoint risk is invalid")
    if state["stage"] not in STAGES:
        raise WorkflowError("checkpoint stage is invalid")
    if isinstance(state["revision"], bool) or not isinstance(state["revision"], int):
        raise WorkflowError("checkpoint revision must be an integer")
    if state["revision"] < 0:
        raise WorkflowError("checkpoint revision must not be negative")

    if not isinstance(state["action"], dict):
        raise WorkflowError("action must be a JSON object")
    _require_exact_keys(state["action"], {"kind", "target"}, "action")
    if state["action"] != action_for(state["task_id"]):
        raise WorkflowError("action does not match task_id; refusing to execute a tampered action")

    if not isinstance(state["checks"], dict):
        raise WorkflowError("checks must be an object")
    if not set(state["checks"]).issubset(BRANCHES):
        raise WorkflowError("checks contains unknown branches")
    for name, result in state["checks"].items():
        _validate_check(name, result)

    if not isinstance(state["attempts"], dict):
        raise WorkflowError("attempts must be an object")
    if not set(state["attempts"]).issubset(BRANCHES):
        raise WorkflowError("attempts contains unknown branches")
    for name, count in state["attempts"].items():
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise WorkflowError(f"attempts.{name} must be a positive integer")

    checks_complete = set(state["checks"]) == set(BRANCHES)
    checks_passed = checks_complete and all(
        result["ok"] is True for result in state["checks"].values()
    )
    approval = state["approval"]
    if approval is not None:
        if not isinstance(approval, dict):
            raise WorkflowError("approval must be an object or null")
        _require_exact_keys(
            approval,
            {"decision", "approval_fingerprint", "based_on_revision"},
            "approval",
        )
        if state["risk"] != "high":
            raise WorkflowError("low-risk teaching paths must not contain an approval record")
        if state["stage"] not in {"execute", "done", "canceled"}:
            raise WorkflowError("an approval decision may appear only in execute or terminal checkpoints")
        if approval["decision"] not in {"approved", "rejected"}:
            raise WorkflowError("approval.decision is invalid")
        if not checks_passed:
            raise WorkflowError("approval may bind only complete, passed read-only check results")
        if approval["approval_fingerprint"] != approval_fingerprint_for(state):
            raise WorkflowError("the approval-bound action, evidence, or policy version does not match current state")
        if isinstance(approval["based_on_revision"], bool) or not isinstance(
            approval["based_on_revision"], int
        ):
            raise WorkflowError("approval.based_on_revision must be an integer")
        if not 0 <= approval["based_on_revision"] <= state["revision"]:
            raise WorkflowError("approval.based_on_revision is outside state history")

    if state["stage"] == "awaiting_approval":
        if state["risk"] != "high" or approval is not None:
            raise WorkflowError("awaiting_approval must be an undecided high-risk path")
        if not checks_passed:
            raise WorkflowError("read-only checks must complete and pass before awaiting approval")
    if state["stage"] == "canceled":
        if approval is None or approval["decision"] != "rejected":
            raise WorkflowError("the canceled terminal state must have rejected approval")
    elif approval is not None and approval["decision"] == "rejected":
        raise WorkflowError("rejected approval may correspond only to the canceled terminal state")
    if state["risk"] == "high" and state["stage"] in {"execute", "done"}:
        if approval is None or approval["decision"] != "approved":
            raise WorkflowError("a high-risk action bypassed valid approval")

    receipt = state["receipt"]
    if receipt is not None:
        _validate_receipt(receipt, state)
    if state["stage"] == "done" and receipt is None:
        raise WorkflowError("the done terminal state must contain an action receipt")
    if state["stage"] != "done" and receipt is not None:
        raise WorkflowError("only the done terminal state may write an action receipt into the checkpoint")

    if not isinstance(state["events"], list):
        raise WorkflowError("events must be an array")
    for expected_revision, event in enumerate(state["events"], start=1):
        if not isinstance(event, dict):
            raise WorkflowError("event must be an object")
        _require_exact_keys(event, {"revision", "name"}, "event")
        if event["revision"] != expected_revision:
            raise WorkflowError("event revisions must increase contiguously")
        if not isinstance(event["name"], str) or not event["name"]:
            raise WorkflowError("event name must be a non-empty string")
    if state["revision"] != len(state["events"]):
        raise WorkflowError("state.revision must equal the event count")


def append_event(state: dict[str, Any], name: str) -> None:
    state["revision"] += 1
    state["events"].append({"revision": state["revision"], "name": name})


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateJsonKeyError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateJsonKeyError) as exc:
        raise WorkflowError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowError(f"{label}top level must be a JSON object")
    return value


def load_state(path: Path, task_id: str, risk: str) -> dict[str, Any]:
    if not path.exists():
        return new_state(task_id, risk)
    envelope = _read_json_object(path, "checkpoint")
    _require_exact_keys(envelope, {"format", "state", "sha256"}, "checkpoint envelope")
    if envelope["format"] != CHECKPOINT_FORMAT:
        raise WorkflowError("checkpoint format identifier is unsupported")
    if not isinstance(envelope["sha256"], str) or envelope["sha256"] != fingerprint(
        envelope["state"]
    ):
        raise WorkflowError("checkpoint integrity validation failed")
    state = envelope["state"]
    validate_state(state)
    if state["task_id"] != task_id:
        raise WorkflowError("command-line task_id does not match the existing checkpoint")
    if state["risk"] != risk:
        raise WorkflowError("command-line risk does not match the existing checkpoint")
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
        raise WorkflowError(f"cannot save checkpoint atomically: {exc}") from exc


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
        raise WorkflowError(f"check {name} retry budget is exhausted")
    while attempts < max_attempts:
        attempts += 1
        try:
            result = check(name, attempts)
        except WorkflowError:
            raise
        except Exception as exc:
            raise WorkflowError(
                f"check {name} did not return a contract result: {type(exc).__name__}"
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
        raise WorkflowError("max_attempts must be a positive integer")
    if max_attempts < 1:
        raise WorkflowError("max_attempts must be a positive integer")
    raw_attempts = state.get("attempts")
    if not isinstance(raw_attempts, Mapping):
        raise WorkflowError("checks input must contain an attempts object")
    if not set(raw_attempts).issubset(BRANCHES):
        raise WorkflowError("checks input contains unknown attempts branches")
    starting: dict[str, int] = {}
    for name in BRANCHES:
        if name not in raw_attempts:
            starting[name] = 0
            continue
        count = raw_attempts[name]
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise WorkflowError(f"checks input attempts.{name} must be a positive integer")
        starting[name] = count
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
        raise WorkflowError("receipt must be an object or null")
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
        raise WorkflowError("action receipt does not match the current task")


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
        existing = _read_json_object(receipt_path, "action receipt")
        if existing != expected:
            raise WorkflowError("the existing action receipt belongs to another task; refusing to overwrite it")
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
        raise WorkflowError(f"cannot commit action receipt: {exc}") from exc
    if crash_after_commit:
        raise SimulatedCrash("simulated: action committed but checkpoint is not yet updated")
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
        raise WorkflowError("decision must be approve, reject, or omitted")
    if risk == "low" and decision is not None:
        raise WorkflowError("the low-risk path does not accept an approval decision")
    state = load_state(checkpoint_path, task_id, risk)
    if state["stage"] in TERMINAL_STAGES:
        return state
    if decision is not None and state["stage"] != "awaiting_approval":
        raise WorkflowError("an approval decision may be submitted only to a persisted awaiting_approval checkpoint")

    if state["stage"] == "start":
        selected = route(state)
        state["stage"] = "checks"
        append_event(state, f"routed:{selected}")
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
            state["stage"] = "awaiting_approval"
            append_event(state, "approval:requested_after_checks")
        else:
            state["stage"] = "execute"
            append_event(state, "evaluation:passed")
        save_state(checkpoint_path, state)

    if state["stage"] == "awaiting_approval":
        if decision is None:
            if not state["events"] or state["events"][-1]["name"] != "paused_for_approval":
                append_event(state, "paused_for_approval")
                save_state(checkpoint_path, state)
            return state
        state["approval"] = {
            "decision": "approved" if decision == "approve" else "rejected",
            "approval_fingerprint": approval_fingerprint_for(state),
            "based_on_revision": state["revision"],
        }
        if decision == "reject":
            state["stage"] = "canceled"
            append_event(state, "approval:rejected")
            save_state(checkpoint_path, state)
            return state
        state["stage"] = "execute"
        append_event(state, "approval:approved")
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
