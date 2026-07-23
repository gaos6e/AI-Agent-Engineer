"""A key-free CrewAI Flow with state persistence and an idempotent receipt ledger."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from dataclasses import dataclass
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Literal


# These must be set before importing CrewAI.  CREWAI_TESTING is an internal
# isolation switch used only by this locked-version teaching fixture.  AMP
# tracing is disabled separately on every Flow with tracing=False.
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["CREWAI_TESTING"] = "true"

try:
    from crewai.flow.flow import Flow, FlowState, listen, router, start
    from crewai.flow.persistence import persist
    from crewai.flow.persistence.sqlite import SQLiteFlowPersistence
    from pydantic import ConfigDict, Field
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by the CLI
    raise SystemExit(
        "dependency_missing: install the version in crewai_layer_b/requirements.txt"
    ) from exc


SCHEMA_VERSION = 1
NAMESPACE = "brief-publisher-v1"
ROUTE_EXECUTE = "route_execute"
ROUTE_DONE = "route_done"
MAX_TOPIC_LENGTH = 200


class PersistentBriefState(FlowState):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    stage: Literal["new", "prepared", "done"] = "new"
    topic: str = ""
    normalized_topic: str = ""
    operation_id: str = ""
    payload_hash: str = ""
    attempt: int = 0
    receipt_id: str = ""
    result: str = ""
    recovered_receipt: bool = False
    steps: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    result: str
    recovered: bool


class InjectedCrash(RuntimeError):
    def __init__(self, flow_id: str) -> None:
        super().__init__("injected crash after receipt commit")
        self.flow_id = flow_id


def _normalize(value: object, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field} must not be empty")
    if len(normalized) > maximum:
        raise ValueError(f"{field} exceeds {maximum} characters")
    return normalized


def payload_hash(operation_id: str, topic: str) -> str:
    canonical = json.dumps(
        {
            "namespace": NAMESPACE,
            "operation_id": operation_id,
            "schema_version": SCHEMA_VERSION,
            "topic": topic,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ReceiptStore:
    """A separate business receipt ledger; it is not a Flow checkpoint."""

    def __init__(self, database: str | Path) -> None:
        self.database = Path(database).resolve()
        if not self.database.parent.is_dir():
            raise ValueError(
                f"receipt database parent does not exist: {self.database.parent}"
            )
        with sqlite3.connect(str(self.database), timeout=30) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS receipts (
                    namespace TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    receipt_id TEXT NOT NULL,
                    result TEXT NOT NULL,
                    effect_count INTEGER NOT NULL,
                    PRIMARY KEY (namespace, operation_id)
                )
                """
            )

    def apply_once(
        self,
        *,
        operation_id: str,
        fingerprint: str,
        topic: str,
    ) -> Receipt:
        connection = sqlite3.connect(str(self.database), timeout=30)
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT payload_hash, receipt_id, result
                FROM receipts
                WHERE namespace = ? AND operation_id = ?
                """,
                (NAMESPACE, operation_id),
            ).fetchone()
            if row is not None:
                stored_hash, receipt_id, result = row
                if stored_hash != fingerprint:
                    raise ValueError(
                        "operation_id already belongs to a different payload"
                    )
                connection.commit()
                return Receipt(receipt_id, result, True)

            result = f"PUBLISHED:{topic.upper()}"
            receipt_digest = hashlib.sha256(
                f"{NAMESPACE}\0{operation_id}\0{fingerprint}".encode("utf-8")
            ).hexdigest()
            receipt_id = f"receipt-{receipt_digest[:24]}"
            connection.execute(
                """
                INSERT INTO receipts (
                    namespace,
                    operation_id,
                    payload_hash,
                    receipt_id,
                    result,
                    effect_count
                ) VALUES (?, ?, ?, ?, ?, 1)
                """,
                (
                    NAMESPACE,
                    operation_id,
                    fingerprint,
                    receipt_id,
                    result,
                ),
            )
            connection.commit()
            return Receipt(receipt_id, result, False)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def effect_count(self, operation_id: str) -> int:
        with sqlite3.connect(str(self.database), timeout=30) as connection:
            row = connection.execute(
                """
                SELECT effect_count
                FROM receipts
                WHERE namespace = ? AND operation_id = ?
                """,
                (NAMESPACE, operation_id),
            ).fetchone()
        return 0 if row is None else int(row[0])


def build_flow_class(
    persistence: SQLiteFlowPersistence,
    receipts: ReceiptStore,
    *,
    crash_after_receipt: bool = False,
) -> type[Flow[PersistentBriefState]]:
    @persist(persistence)
    class PersistentBriefFlow(Flow[PersistentBriefState]):
        @start()
        def prepare(self) -> str:
            if self.state.schema_version != SCHEMA_VERSION:
                raise ValueError(
                    f"unsupported schema_version: {self.state.schema_version}"
                )
            if self.state.stage == "done":
                self.state.steps.append("prepare:already_done")
                return ROUTE_DONE
            if self.state.stage not in {"new", "prepared"}:
                raise ValueError(f"unsupported stage: {self.state.stage}")

            topic = _normalize(self.state.topic, "topic", MAX_TOPIC_LENGTH)
            operation_id = _normalize(
                self.state.operation_id,
                "operation_id",
                128,
            )
            self.state.normalized_topic = topic
            self.state.operation_id = operation_id
            self.state.payload_hash = payload_hash(operation_id, topic)
            self.state.stage = "prepared"
            self.state.attempt += 1
            self.state.steps.append("prepare")
            return ROUTE_EXECUTE

        @router(prepare)
        def select_route(self, prepared_route: str) -> str:
            if prepared_route not in {ROUTE_EXECUTE, ROUTE_DONE}:
                raise ValueError(f"unexpected route: {prepared_route}")
            self.state.steps.append(f"router:{prepared_route}")
            return prepared_route

        @listen(ROUTE_EXECUTE)
        def apply_effect(self) -> str:
            receipt = receipts.apply_once(
                operation_id=self.state.operation_id,
                fingerprint=self.state.payload_hash,
                topic=self.state.normalized_topic,
            )
            if crash_after_receipt and not receipt.recovered:
                raise InjectedCrash(self.state.id)
            self.state.receipt_id = receipt.receipt_id
            self.state.result = receipt.result
            self.state.recovered_receipt = receipt.recovered
            self.state.stage = "done"
            self.state.steps.append(
                "effect:recovered" if receipt.recovered else "effect:created"
            )
            return receipt.result

        @listen(ROUTE_DONE)
        def return_completed(self) -> str:
            self.state.steps.append("return:done")
            return self.state.result

    return PersistentBriefFlow


def _paths(state_database: str | Path, effect_database: str | Path) -> tuple[Path, Path]:
    state_path = Path(state_database).resolve()
    effect_path = Path(effect_database).resolve()
    for label, path in (("state", state_path), ("effect", effect_path)):
        if not path.parent.is_dir():
            raise ValueError(f"{label} database parent does not exist: {path.parent}")
    if state_path == effect_path:
        raise ValueError("state and effect databases must be different files")
    return state_path, effect_path


def _kickoff(flow: Flow[PersistentBriefState], **kwargs: Any) -> Any:
    # Keep stdout machine-readable while preserving framework diagnostics on stderr.
    with redirect_stdout(sys.stderr):
        return flow.kickoff(**kwargs)


def _summary(flow: Flow[PersistentBriefState], receipts: ReceiptStore) -> dict[str, object]:
    state = flow.state
    return {
        "flow_id": state.id,
        "schema_version": state.schema_version,
        "stage": state.stage,
        "topic": state.normalized_topic,
        "operation_id": state.operation_id,
        "attempt": state.attempt,
        "receipt_id": state.receipt_id,
        "result": state.result,
        "recovered_receipt": state.recovered_receipt,
        "effect_count": receipts.effect_count(state.operation_id)
        if state.operation_id
        else 0,
        "steps": list(state.steps),
    }


def start_flow(
    *,
    state_database: str | Path,
    effect_database: str | Path,
    topic: str,
    operation_id: str,
    schema_version: int = SCHEMA_VERSION,
    crash_after_receipt: bool = False,
) -> dict[str, object]:
    state_path, effect_path = _paths(state_database, effect_database)
    persistence = SQLiteFlowPersistence(str(state_path))
    receipts = ReceiptStore(effect_path)
    flow_class = build_flow_class(
        persistence,
        receipts,
        crash_after_receipt=crash_after_receipt,
    )
    flow = flow_class(suppress_flow_events=True, tracing=False)
    try:
        _kickoff(
            flow,
            inputs={
                "schema_version": schema_version,
                "topic": topic,
                "operation_id": operation_id,
            },
        )
    except InjectedCrash:
        raise
    return _summary(flow, receipts)


def _require_persisted_state(
    persistence: SQLiteFlowPersistence,
    flow_id: str,
) -> dict[str, Any]:
    normalized = _normalize(flow_id, "flow_id", 128)
    stored = persistence.load_state(normalized)
    if stored is None:
        raise ValueError("unknown flow_id; refusing implicit creation")
    return stored


def _normalized_flow_id(flow_id: str) -> str:
    """Use the same canonical flow key for lookup, kickoff, and reporting."""

    return _normalize(flow_id, "flow_id", 128)


def resume_flow(
    *,
    state_database: str | Path,
    effect_database: str | Path,
    flow_id: str,
) -> dict[str, object]:
    state_path, effect_path = _paths(state_database, effect_database)
    persistence = SQLiteFlowPersistence(str(state_path))
    normalized_flow_id = _normalized_flow_id(flow_id)
    _require_persisted_state(persistence, normalized_flow_id)
    receipts = ReceiptStore(effect_path)
    flow_class = build_flow_class(persistence, receipts)
    flow = flow_class(suppress_flow_events=True, tracing=False)
    _kickoff(flow, inputs={"id": normalized_flow_id})
    return _summary(flow, receipts)


def fork_flow(
    *,
    state_database: str | Path,
    effect_database: str | Path,
    flow_id: str,
) -> dict[str, object]:
    state_path, effect_path = _paths(state_database, effect_database)
    persistence = SQLiteFlowPersistence(str(state_path))
    normalized_flow_id = _normalized_flow_id(flow_id)
    _require_persisted_state(persistence, normalized_flow_id)
    receipts = ReceiptStore(effect_path)
    flow_class = build_flow_class(persistence, receipts)
    flow = flow_class(suppress_flow_events=True, tracing=False)
    _kickoff(flow, restore_from_state_id=normalized_flow_id)
    result = _summary(flow, receipts)
    result["forked_from"] = normalized_flow_id
    return result


def inspect_flow(
    *,
    state_database: str | Path,
    effect_database: str | Path,
    flow_id: str,
) -> dict[str, object]:
    state_path, effect_path = _paths(state_database, effect_database)
    persistence = SQLiteFlowPersistence(str(state_path))
    normalized_flow_id = _normalized_flow_id(flow_id)
    stored = _require_persisted_state(persistence, normalized_flow_id)
    receipts = ReceiptStore(effect_path)
    operation_id = str(stored.get("operation_id", ""))
    return {
        "flow_id": normalized_flow_id,
        "stage": stored.get("stage"),
        "operation_id": operation_id,
        "attempt": stored.get("attempt"),
        "receipt_id": stored.get("receipt_id"),
        "effect_count": receipts.effect_count(operation_id) if operation_id else 0,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-db", required=True)
    parser.add_argument("--effect-db", required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--topic", required=True)
    start_parser.add_argument("--operation-id", required=True)
    start_parser.add_argument("--crash-after-receipt", action="store_true")

    for name in ("resume", "fork", "inspect"):
        command_parser = subparsers.add_parser(name)
        command_parser.add_argument("--flow-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    common = {
        "state_database": args.state_db,
        "effect_database": args.effect_db,
    }
    try:
        if args.command == "start":
            result = start_flow(
                **common,
                topic=args.topic,
                operation_id=args.operation_id,
                crash_after_receipt=args.crash_after_receipt,
            )
        elif args.command == "resume":
            result = resume_flow(**common, flow_id=args.flow_id)
        elif args.command == "fork":
            result = fork_flow(**common, flow_id=args.flow_id)
        else:
            result = inspect_flow(**common, flow_id=args.flow_id)
        result["runtime"] = {"crewai": version("crewai")}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except InjectedCrash as exc:
        print(
            json.dumps(
                {
                    "error": type(exc).__name__,
                    "message": str(exc),
                    "flow_id": exc.flow_id,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 3
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
