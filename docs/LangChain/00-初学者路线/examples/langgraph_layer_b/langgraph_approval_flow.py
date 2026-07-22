"""A key-free LangGraph approval flow with durable SQLite checkpoints.

The example deliberately performs only a deterministic dry-run action.  It
demonstrates runtime persistence and interrupt semantics without pretending
that a checkpoint makes an external side effect exactly-once.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator
from contextlib import contextmanager
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Literal, TypedDict


# Restrict msgpack deserialization to LangGraph's built-in safe-type allowlist.
# JsonPlusSerializer's separate pickle fallback remains disabled by default.
os.environ["LANGGRAPH_STRICT_MSGPACK"] = "true"

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Command, interrupt
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by the CLI
    raise SystemExit(
        "dependency_missing: install the versions in langgraph_layer_b/requirements.txt"
    ) from exc


SCHEMA_VERSION = 1
GRAPH_VERSION = "approval-flow-v1"
POLICY_VERSION = "approval-policy-v1"
MAX_TEXT_LENGTH = 500


class ApprovalState(TypedDict, total=False):
    schema_version: int
    graph_version: str
    policy_version: str
    workflow_id: str
    owner_id: str
    action: str
    requested_text: str
    normalized_text: str
    action_fingerprint: str
    approval_request_id: str
    status: Literal[
        "new",
        "awaiting_approval",
        "approved",
        "rejected",
        "completed",
    ]
    reviewer: str
    dry_run_result: str
    dry_run_receipt: str


def _require_text(value: object, field: str, *, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field} must not be empty")
    if len(normalized) > maximum:
        raise ValueError(f"{field} exceeds {maximum} characters")
    return normalized


def action_fingerprint(
    workflow_id: str,
    owner_id: str,
    normalized_text: str,
) -> str:
    canonical = json.dumps(
        {
            "action": "normalize_text",
            "graph_version": GRAPH_VERSION,
            "policy_version": POLICY_VERSION,
            "schema_version": SCHEMA_VERSION,
            "text": normalized_text,
            "owner_id": owner_id,
            "workflow_id": workflow_id,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def prepare_action(state: ApprovalState) -> dict[str, object]:
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {state.get('schema_version')!r}")
    workflow_id = _require_text(state.get("workflow_id"), "workflow_id", maximum=128)
    owner_id = _require_text(state.get("owner_id"), "owner_id", maximum=128)
    if state.get("action") != "normalize_text":
        raise ValueError("action must be normalize_text")
    normalized = _require_text(
        state.get("requested_text"),
        "requested_text",
        maximum=MAX_TEXT_LENGTH,
    )
    fingerprint = action_fingerprint(workflow_id, owner_id, normalized)
    return {
        "workflow_id": workflow_id,
        "owner_id": owner_id,
        "normalized_text": normalized,
        "graph_version": GRAPH_VERSION,
        "policy_version": POLICY_VERSION,
        "action_fingerprint": fingerprint,
        "approval_request_id": f"approval-{fingerprint[:20]}",
        "status": "awaiting_approval",
    }


def _validate_decision(
    raw: object,
    state: ApprovalState,
) -> tuple[bool, str]:
    if not isinstance(raw, dict):
        raise ValueError("resume value must be an approval object")
    required = {
        "approval_request_id",
        "action_fingerprint",
        "approved",
        "reviewer",
    }
    if set(raw) != required:
        raise ValueError("approval object has an unexpected shape")
    if raw["approval_request_id"] != state["approval_request_id"]:
        raise ValueError("approval_request_id does not match the pending action")
    if raw["action_fingerprint"] != state["action_fingerprint"]:
        raise ValueError("action_fingerprint does not match the pending action")
    if type(raw["approved"]) is not bool:
        raise ValueError("approved must be a boolean")
    reviewer = _require_text(raw["reviewer"], "reviewer", maximum=80)
    return raw["approved"], reviewer


def make_review_node(
    on_enter: Callable[[], None] | None,
) -> Callable[[ApprovalState], dict[str, object]]:
    def review_action(state: ApprovalState) -> dict[str, object]:
        _validate_checkpoint_contract(state, require_pending=True)
        # Test instrumentation makes the documented node replay observable.
        # Production work must not place a non-idempotent side effect here.
        if on_enter is not None:
            on_enter()
        decision = interrupt(
            {
                "kind": "approval",
                "approval_request_id": state["approval_request_id"],
                "action": state["action"],
                "action_fingerprint": state["action_fingerprint"],
                "preview": state["normalized_text"],
            }
        )
        approved, reviewer = _validate_decision(decision, state)
        return {
            "reviewer": reviewer,
            "status": "approved" if approved else "rejected",
        }

    return review_action


def route_after_review(state: ApprovalState) -> Literal["execute", "__end__"]:
    if state.get("status") == "approved":
        return "execute"
    if state.get("status") == "rejected":
        return END
    raise ValueError("review node did not produce a terminal decision")


def execute_dry_run(state: ApprovalState) -> dict[str, str]:
    _validate_checkpoint_contract(state)
    if state.get("status") != "approved":
        raise ValueError("dry-run execution requires an approved state")
    result = state["normalized_text"].upper()
    receipt_material = f"dry-run\0{state['action_fingerprint']}\0{result}"
    receipt = hashlib.sha256(receipt_material.encode("utf-8")).hexdigest()
    return {
        "dry_run_result": result,
        "dry_run_receipt": f"sha256:{receipt}",
        "status": "completed",
    }


def build_graph(
    checkpointer: SqliteSaver,
    *,
    on_review_enter: Callable[[], None] | None = None,
) -> Any:
    builder = StateGraph(ApprovalState)
    builder.add_node("prepare", prepare_action)
    builder.add_node("review", make_review_node(on_review_enter))
    builder.add_node("execute", execute_dry_run)
    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "review")
    builder.add_conditional_edges(
        "review",
        route_after_review,
        {"execute": "execute", END: END},
    )
    builder.add_edge("execute", END)
    return builder.compile(checkpointer=checkpointer)


@contextmanager
def open_graph(
    database: str | Path,
    *,
    on_review_enter: Callable[[], None] | None = None,
) -> Iterator[Any]:
    path = Path(database).resolve()
    if not path.parent.is_dir():
        raise ValueError(f"database parent does not exist: {path.parent}")
    connection = sqlite3.connect(str(path), check_same_thread=False)
    try:
        yield build_graph(
            SqliteSaver(connection),
            on_review_enter=on_review_enter,
        )
    finally:
        connection.close()


def thread_config(thread_id: str) -> dict[str, dict[str, str]]:
    normalized = _require_text(thread_id, "thread_id", maximum=128)
    return {"configurable": {"thread_id": normalized}}


def _normalized_thread_id(thread_id: str) -> str:
    """Normalize the durable key once so storage, state, and responses agree."""

    return _require_text(thread_id, "thread_id", maximum=128)


def _pending_interrupts(snapshot: Any) -> list[Any]:
    return [item for task in snapshot.tasks for item in task.interrupts]


def _validate_checkpoint_contract(
    values: ApprovalState,
    *,
    expected_thread_id: str | None = None,
    expected_owner_id: str | None = None,
    require_pending: bool = False,
) -> None:
    """Reject incompatible or internally inconsistent saved state before reuse.

    This is a migration/contract guard, not a substitute for access control or
    cryptographic integrity of a database controlled by an attacker.
    """

    if values.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("checkpoint schema_version is not supported")
    if values.get("graph_version") != GRAPH_VERSION:
        raise ValueError("checkpoint graph_version is not supported")
    if values.get("policy_version") != POLICY_VERSION:
        raise ValueError("checkpoint policy_version is not supported")
    workflow_id = _require_text(values.get("workflow_id"), "workflow_id", maximum=128)
    owner_id = _require_text(values.get("owner_id"), "owner_id", maximum=128)
    if expected_thread_id is not None and workflow_id != expected_thread_id:
        raise ValueError("thread binding does not match workflow state")
    if expected_owner_id is not None and owner_id != expected_owner_id:
        raise ValueError("thread owner does not match workflow state")
    if values.get("action") != "normalize_text":
        raise ValueError("checkpoint action is not supported")
    requested_text = _require_text(
        values.get("requested_text"),
        "requested_text",
        maximum=MAX_TEXT_LENGTH,
    )
    normalized_text = _require_text(
        values.get("normalized_text"),
        "normalized_text",
        maximum=MAX_TEXT_LENGTH,
    )
    if normalized_text != requested_text:
        raise ValueError("checkpoint normalized_text does not match requested_text")
    expected_fingerprint = action_fingerprint(workflow_id, owner_id, normalized_text)
    if values.get("action_fingerprint") != expected_fingerprint:
        raise ValueError("checkpoint action_fingerprint is inconsistent")
    expected_request_id = f"approval-{expected_fingerprint[:20]}"
    if values.get("approval_request_id") != expected_request_id:
        raise ValueError("checkpoint approval_request_id is inconsistent")
    if require_pending and values.get("status") != "awaiting_approval":
        raise ValueError("checkpoint is not awaiting approval")


def inspect_workflow(
    graph: Any,
    thread_id: str,
    *,
    owner_id: str,
) -> dict[str, object]:
    normalized_thread_id = _normalized_thread_id(thread_id)
    config = thread_config(normalized_thread_id)
    snapshot = graph.get_state(config)
    values = dict(snapshot.values)
    normalized_owner = _require_text(owner_id, "owner_id", maximum=128)
    if values and values.get("owner_id") != normalized_owner:
        raise ValueError("thread owner does not match workflow state")
    pending = _pending_interrupts(snapshot)
    return {
        "thread_id": normalized_thread_id,
        "exists": bool(values or snapshot.next or snapshot.tasks),
        "workflow_id": values.get("workflow_id"),
        "status": values.get("status"),
        "next": list(snapshot.next),
        "action_fingerprint": values.get("action_fingerprint"),
        "approval_request_id": values.get("approval_request_id"),
        "pending_interrupts": [item.value for item in pending],
    }


def start_workflow(
    graph: Any,
    *,
    thread_id: str,
    owner_id: str,
    text: str,
) -> dict[str, object]:
    normalized_thread_id = _normalized_thread_id(thread_id)
    config = thread_config(normalized_thread_id)
    existing = graph.get_state(config)
    if existing.values or existing.next or existing.tasks:
        raise ValueError("thread_id already has checkpoint state; choose a new thread")
    graph.invoke(
        {
            "schema_version": SCHEMA_VERSION,
            "workflow_id": normalized_thread_id,
            "owner_id": _require_text(owner_id, "owner_id", maximum=128),
            "action": "normalize_text",
            "requested_text": text,
            "status": "new",
        },
        config,
        durability="sync",
    )
    summary = inspect_workflow(graph, normalized_thread_id, owner_id=owner_id)
    if summary["next"] != ["review"] or len(summary["pending_interrupts"]) != 1:
        raise RuntimeError("workflow did not reach the expected review interrupt")
    return summary


def resume_workflow(
    graph: Any,
    *,
    thread_id: str,
    owner_id: str,
    approved: bool,
    reviewer: str,
    approval_request_id: str | None = None,
    fingerprint: str | None = None,
) -> dict[str, object]:
    normalized_thread_id = _normalized_thread_id(thread_id)
    config = thread_config(normalized_thread_id)
    snapshot = graph.get_state(config)
    values = dict(snapshot.values)
    pending = _pending_interrupts(snapshot)
    if not values:
        raise ValueError("cannot resume a thread with no checkpoint state")
    if values.get("workflow_id") != normalized_thread_id:
        raise ValueError("thread binding does not match workflow state")
    normalized_owner = _require_text(owner_id, "owner_id", maximum=128)
    if values.get("owner_id") != normalized_owner:
        raise ValueError("thread owner does not match workflow state")
    if tuple(snapshot.next) != ("review",) or len(pending) != 1:
        raise ValueError("thread is not paused at the review interrupt")
    _validate_checkpoint_contract(
        values,
        expected_thread_id=normalized_thread_id,
        expected_owner_id=normalized_owner,
        require_pending=True,
    )
    decision = {
        "approval_request_id": approval_request_id
        if approval_request_id is not None
        else values["approval_request_id"],
        "action_fingerprint": fingerprint
        if fingerprint is not None
        else values["action_fingerprint"],
        "approved": approved,
        "reviewer": reviewer,
    }
    # Validate at the application boundary before consuming the pending
    # interrupt.  The node repeats the check after resume as defense in depth.
    _validate_decision(decision, values)
    graph.invoke(Command(resume=decision), config, durability="sync")
    return inspect_workflow(graph, normalized_thread_id, owner_id=normalized_owner)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="SQLite checkpoint file")
    parser.add_argument("--thread-id", required=True)
    parser.add_argument(
        "--owner-id",
        required=True,
        help="Trusted caller identity supplied by the application boundary",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--text", required=True)

    subparsers.add_parser("inspect")

    resume_parser = subparsers.add_parser("resume")
    resume_parser.add_argument(
        "--decision",
        required=True,
        choices=("approve", "reject"),
    )
    resume_parser.add_argument("--reviewer", required=True)
    resume_parser.add_argument("--approval-request-id")
    resume_parser.add_argument("--fingerprint")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        with open_graph(args.db) as graph:
            if args.command == "start":
                result = start_workflow(
                    graph,
                    thread_id=args.thread_id,
                    owner_id=args.owner_id,
                    text=args.text,
                )
            elif args.command == "inspect":
                result = inspect_workflow(
                    graph,
                    args.thread_id,
                    owner_id=args.owner_id,
                )
            else:
                result = resume_workflow(
                    graph,
                    thread_id=args.thread_id,
                    owner_id=args.owner_id,
                    approved=args.decision == "approve",
                    reviewer=args.reviewer,
                    approval_request_id=args.approval_request_id,
                    fingerprint=args.fingerprint,
                )
        result["runtime"] = {
            "langgraph": version("langgraph"),
            "langgraph-checkpoint-sqlite": version(
                "langgraph-checkpoint-sqlite"
            ),
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {"error": type(exc).__name__, "message": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
