"""A bounded, offline workflow engine for teaching reliability contracts.

The implementation is intentionally single-process. It demonstrates strict
definition and event validation, deduplication, finite retries, idempotent side
effects, approval binding, checkpoint integrity, and compensation. It is not a
production transaction system or an exactly-once guarantee.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable


ALLOWED_DEFINITION_FIELDS = {"name", "version", "max_total_attempts", "steps"}
ALLOWED_STEP_FIELDS = {
    "name",
    "needs",
    "handler",
    "approval",
    "max_attempts",
    "retryable_errors",
    "compensate",
}
HANDLERS = {"validate", "reserve_inventory", "risk_check", "charge", "notify"}
COMPENSATIONS = {"release_inventory", "refund"}
RETRYABLE_ERROR_CODES = {"TRANSIENT", "UNKNOWN_RESULT"}
EVENT_FIELDS = {"id", "source", "specversion", "type", "time", "data"}
CHECKPOINT_FIELDS = {"schema_version", "definition_fingerprint", "payload", "sha256"}
STATE_FIELDS = {
    "instance_id",
    "event_key",
    "event_fingerprint",
    "definition_name",
    "definition_version",
    "definition_fingerprint",
    "status",
    "data",
    "steps",
    "attempts",
    "approved_steps",
    "compensations",
    "approval_request",
    "state_version",
    "ready_batches",
    "events",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )
    require(isinstance(data, dict), f"{path.name} root must be an object")
    return data


@dataclass(frozen=True)
class StepDefinition:
    name: str
    needs: tuple[str, ...]
    handler: str
    approval: bool
    max_attempts: int
    retryable_errors: tuple[str, ...]
    compensate: str | None


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    version: str
    max_total_attempts: int
    steps: tuple[StepDefinition, ...]
    fingerprint: str

    @property
    def registry(self) -> dict[str, StepDefinition]:
        return {step.name: step for step in self.steps}


def load_definition(path: Path) -> WorkflowDefinition:
    raw = read_json_object(path)
    require(set(raw) == ALLOWED_DEFINITION_FIELDS, "definition has missing or unknown top-level fields")
    require(isinstance(raw["name"], str) and raw["name"].strip(), "definition name must be non-empty")
    require(isinstance(raw["version"], str) and raw["version"].strip(), "definition version must be non-empty")
    require(
        isinstance(raw["max_total_attempts"], int)
        and not isinstance(raw["max_total_attempts"], bool)
        and raw["max_total_attempts"] >= 1,
        "max_total_attempts must be a positive integer",
    )
    raw_steps = raw["steps"]
    require(isinstance(raw_steps, list) and raw_steps, "steps must be a non-empty array")

    steps: list[StepDefinition] = []
    names: set[str] = set()
    for index, item in enumerate(raw_steps, start=1):
        require(isinstance(item, dict), f"step {index} must be an object")
        require(set(item) == ALLOWED_STEP_FIELDS, f"step {index} has missing or unknown fields")
        name = item["name"]
        require(isinstance(name, str) and name.strip(), f"step {index} name must be non-empty")
        require(name not in names, f"duplicate step name: {name}")
        names.add(name)
        needs = item["needs"]
        require(
            isinstance(needs, list) and all(isinstance(value, str) and value for value in needs),
            f"step {name} needs must be an array of names",
        )
        require(len(needs) == len(set(needs)), f"step {name} has duplicate dependencies")
        handler = item["handler"]
        require(handler in HANDLERS, f"unknown handler for {name}: {handler}")
        require(isinstance(item["approval"], bool), f"step {name} approval must be boolean")
        max_attempts = item["max_attempts"]
        require(
            isinstance(max_attempts, int) and not isinstance(max_attempts, bool) and max_attempts >= 1,
            f"step {name} max_attempts must be a positive integer",
        )
        retryable = item["retryable_errors"]
        require(
            isinstance(retryable, list) and all(isinstance(value, str) for value in retryable),
            f"step {name} retryable_errors must be an array of strings",
        )
        require(len(retryable) == len(set(retryable)), f"step {name} has duplicate retryable errors")
        unknown_errors = set(retryable) - RETRYABLE_ERROR_CODES
        require(not unknown_errors, f"step {name} has unknown retryable errors: {sorted(unknown_errors)}")
        compensate = item["compensate"]
        require(
            compensate is None or compensate in COMPENSATIONS,
            f"unknown compensation for {name}: {compensate}",
        )
        steps.append(
            StepDefinition(
                name=name,
                needs=tuple(needs),
                handler=handler,
                approval=item["approval"],
                max_attempts=max_attempts,
                retryable_errors=tuple(retryable),
                compensate=compensate,
            )
        )

    registry = {step.name: step for step in steps}
    for step in steps:
        unknown = set(step.needs) - set(registry)
        require(not unknown, f"unknown dependencies for {step.name}: {sorted(unknown)}")
        require(step.name not in step.needs, f"step {step.name} cannot depend on itself")
    _assert_acyclic(registry)
    require(any(not step.needs for step in steps), "definition needs at least one root step")
    require(
        raw["max_total_attempts"] >= sum(1 for _ in steps),
        "max_total_attempts must allow every step one attempt",
    )
    return WorkflowDefinition(
        name=raw["name"],
        version=raw["version"],
        max_total_attempts=raw["max_total_attempts"],
        steps=tuple(steps),
        fingerprint=fingerprint(raw),
    )


def _assert_acyclic(steps: dict[str, StepDefinition]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        require(name not in visiting, "workflow contains a cycle")
        if name in visited:
            return
        visiting.add(name)
        for dependency in steps[name].needs:
            visit(dependency)
        visiting.remove(name)
        visited.add(name)

    for step_name in steps:
        visit(step_name)


class StepError(RuntimeError):
    code = "STEP_ERROR"


class TransientStepError(StepError):
    code = "TRANSIENT"


class UnknownResultError(StepError):
    code = "UNKNOWN_RESULT"


class PermanentStepError(StepError):
    code = "PERMANENT"


@dataclass(frozen=True)
class EffectRecord:
    key: str
    action: str
    intent_fingerprint: str
    result: dict[str, Any]


class EffectStore:
    """In-memory idempotency ledger; deliberately not a production boundary."""

    def __init__(
        self,
        *,
        unknown_once: set[str] | None = None,
        transient_failures: dict[str, int] | None = None,
        permanent_failures: set[str] | None = None,
    ) -> None:
        self.records: dict[str, EffectRecord] = {}
        self.counts: dict[str, int] = {}
        self.unknown_once = set(unknown_once or set())
        self.unknown_emitted: set[str] = set()
        self.transient_failures = dict(transient_failures or {})
        self.permanent_failures = set(permanent_failures or set())

    def perform(self, *, key: str, action: str, intent: dict[str, Any]) -> dict[str, Any]:
        intent_fingerprint = fingerprint(intent)
        existing = self.records.get(key)
        if existing is not None:
            require(existing.intent_fingerprint == intent_fingerprint, f"idempotency conflict for {key}")
            require(existing.action == action, f"idempotency action conflict for {key}")
            return dict(existing.result)

        remaining = self.transient_failures.get(action, 0)
        if remaining > 0:
            self.transient_failures[action] = remaining - 1
            raise TransientStepError(f"{action} temporarily unavailable")
        if action in self.permanent_failures:
            raise PermanentStepError(f"{action} permanently failed")

        result = {"action": action, "receipt": fingerprint({"key": key, "intent": intent})[:16]}
        self.records[key] = EffectRecord(key, action, intent_fingerprint, result)
        self.counts[action] = self.counts.get(action, 0) + 1
        if action in self.unknown_once and action not in self.unknown_emitted:
            self.unknown_emitted.add(action)
            raise UnknownResultError(f"{action} committed but acknowledgement was lost")
        return dict(result)


@dataclass(frozen=True)
class CompensationRecord:
    original_step: str
    action: str
    intent: dict[str, Any]
    status: str = "pending"


@dataclass(frozen=True)
class ApprovalRequest:
    request_id: str
    instance_id: str
    step: str
    payload_fingerprint: str
    definition_version: str
    state_version: int
    expires_at: int


@dataclass(frozen=True)
class ApprovalGrant:
    request_id: str
    instance_id: str
    step: str
    payload_fingerprint: str
    definition_version: str
    state_version: int
    expires_at: int
    decision: str


@dataclass
class WorkflowState:
    instance_id: str
    event_key: str
    event_fingerprint: str
    definition_name: str
    definition_version: str
    definition_fingerprint: str
    status: str
    data: dict[str, Any]
    steps: dict[str, str]
    attempts: dict[str, int]
    approved_steps: list[str] = field(default_factory=list)
    compensations: list[CompensationRecord] = field(default_factory=list)
    approval_request: ApprovalRequest | None = None
    state_version: int = 0
    ready_batches: list[list[str]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)


def validate_event(event: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(event, dict), "event must be an object")
    require(set(event) <= EVENT_FIELDS, "event has unknown fields")
    for field_name in ("id", "source", "specversion", "type", "data"):
        require(field_name in event, f"event missing required field: {field_name}")
    for field_name in ("id", "source", "specversion", "type"):
        require(
            isinstance(event[field_name], str) and event[field_name].strip(),
            f"event {field_name} must be a non-empty string",
        )
    require(event["specversion"] == "1.0", "this example accepts CloudEvents specversion 1.0")
    require(event["type"] == "com.example.order.submitted.v1", "unsupported event type")
    if "time" in event:
        require(isinstance(event["time"], str) and event["time"].strip(), "event time must be a string")
    data = event["data"]
    require(isinstance(data, dict), "event data must be an object")
    require(set(data) == {"order_id", "amount_cents"}, "event data has missing or unknown fields")
    require(isinstance(data["order_id"], str) and data["order_id"].strip(), "order_id must be non-empty")
    require(
        isinstance(data["amount_cents"], int)
        and not isinstance(data["amount_cents"], bool)
        and data["amount_cents"] > 0,
        "amount_cents must be a positive integer",
    )
    return {"order_id": data["order_id"], "amount_cents": data["amount_cents"]}


class WorkflowCoordinator:
    def __init__(
        self,
        definition: WorkflowDefinition,
        effects: EffectStore,
        *,
        now: Callable[[], int] | None = None,
        approval_ttl: int = 3600,
    ) -> None:
        require(approval_ttl > 0, "approval_ttl must be positive")
        self.definition = definition
        self.effects = effects
        self.now = now or (lambda: 0)
        self.approval_ttl = approval_ttl
        self.events: dict[str, tuple[str, WorkflowState]] = {}

    def start(self, event: dict[str, Any]) -> WorkflowState:
        data = validate_event(event)
        event_key = f"{event['source']}::{event['id']}"
        event_fingerprint = fingerprint(event)
        existing = self.events.get(event_key)
        if existing is not None:
            require(existing[0] == event_fingerprint, "same event key has a different payload")
            return existing[1]
        instance_id = "wf-" + fingerprint({"event_key": event_key})[:16]
        state = WorkflowState(
            instance_id=instance_id,
            event_key=event_key,
            event_fingerprint=event_fingerprint,
            definition_name=self.definition.name,
            definition_version=self.definition.version,
            definition_fingerprint=self.definition.fingerprint,
            status="running",
            data=data,
            steps={step.name: "pending" for step in self.definition.steps},
            attempts={step.name: 0 for step in self.definition.steps},
        )
        self._record(state, "instance_started")
        self.events[event_key] = (event_fingerprint, state)
        return state

    def run_until_blocked(self, state: WorkflowState) -> WorkflowState:
        self._validate_state_identity(state)
        require(state.status == "running", f"state must be running, got {state.status}")
        registry = self.definition.registry
        while state.status == "running":
            ready = [
                step.name
                for step in self.definition.steps
                if state.steps[step.name] == "pending"
                and all(state.steps[dependency] == "succeeded" for dependency in step.needs)
            ]
            if not ready:
                if all(value == "succeeded" for value in state.steps.values()):
                    state.status = "completed"
                    self._bump(state, "instance_completed")
                    return state
                raise ValueError("workflow is blocked without a waiting or terminal state")
            state.ready_batches.append(list(ready))
            self._record(state, "ready_batch", count=len(ready))
            for step_name in ready:
                step = registry[step_name]
                if step.approval and step_name not in state.approved_steps:
                    self._wait_for_approval(state, step)
                    return state
                if not self._execute_with_retries(state, step):
                    return state
        return state

    def approve(self, state: WorkflowState, grant: ApprovalGrant) -> WorkflowState:
        self._validate_state_identity(state)
        require(state.status == "waiting_approval", "workflow is not waiting for approval")
        request = state.approval_request
        require(request is not None, "approval request is missing")
        expected = asdict(request)
        actual = {key: value for key, value in asdict(grant).items() if key != "decision"}
        require(actual == expected, "approval grant does not match the bound request")
        require(grant.decision in {"approve", "reject"}, "approval decision must be approve or reject")
        require(self.now() <= grant.expires_at, "approval has expired")
        if grant.decision == "reject":
            state.steps[grant.step] = "rejected"
            state.status = "business_rejected"
            state.approval_request = None
            self._bump(state, "approval_rejected", step=grant.step)
            self._compensate(state)
            return state
        state.approved_steps.append(grant.step)
        state.steps[grant.step] = "pending"
        state.status = "running"
        state.approval_request = None
        self._bump(state, "approval_accepted", step=grant.step)
        return state

    def _execute_with_retries(self, state: WorkflowState, step: StepDefinition) -> bool:
        while state.attempts[step.name] < step.max_attempts:
            if sum(state.attempts.values()) >= self.definition.max_total_attempts:
                state.steps[step.name] = "failed"
                state.status = "failed"
                self._bump(state, "attempt_budget_exhausted", step=step.name)
                self._compensate(state)
                return False
            state.attempts[step.name] += 1
            state.steps[step.name] = "running"
            self._bump(state, "step_started", step=step.name, attempt=state.attempts[step.name])
            try:
                self._execute_step(state, step)
            except StepError as exc:
                self._record(state, "step_error", step=step.name, error_code=exc.code)
                can_retry = exc.code in step.retryable_errors and state.attempts[step.name] < step.max_attempts
                if can_retry:
                    state.steps[step.name] = "pending"
                    self._bump(state, "retry_scheduled", step=step.name, attempt=state.attempts[step.name])
                    continue
                state.steps[step.name] = "failed"
                state.status = "failed"
                self._bump(state, "step_failed", step=step.name, error_code=exc.code)
                self._compensate(state)
                return False
            state.steps[step.name] = "succeeded"
            if step.compensate is not None:
                state.compensations.append(
                    CompensationRecord(
                        original_step=step.name,
                        action=step.compensate,
                        intent=self._effect_intent(state, step.name),
                    )
                )
            self._bump(state, "step_succeeded", step=step.name)
            return True
        return False

    def _execute_step(self, state: WorkflowState, step: StepDefinition) -> None:
        if step.handler in {"validate", "risk_check"}:
            return
        intent = self._effect_intent(state, step.name)
        key = f"{state.instance_id}:{step.name}:v1"
        self.effects.perform(key=key, action=step.handler, intent=intent)

    def _effect_intent(self, state: WorkflowState, step_name: str) -> dict[str, Any]:
        return {
            "instance_id": state.instance_id,
            "step": step_name,
            "order_id": state.data["order_id"],
            "amount_cents": state.data["amount_cents"],
            "intent_version": "v1",
        }

    def _wait_for_approval(self, state: WorkflowState, step: StepDefinition) -> None:
        state.steps[step.name] = "waiting_approval"
        state.status = "waiting_approval"
        state.state_version += 1
        payload_fingerprint = fingerprint(self._effect_intent(state, step.name))
        expires_at = self.now() + self.approval_ttl
        request_id = "approval-" + fingerprint(
            {
                "instance_id": state.instance_id,
                "step": step.name,
                "payload_fingerprint": payload_fingerprint,
                "definition_version": state.definition_version,
                "state_version": state.state_version,
                "expires_at": expires_at,
            }
        )[:16]
        state.approval_request = ApprovalRequest(
            request_id=request_id,
            instance_id=state.instance_id,
            step=step.name,
            payload_fingerprint=payload_fingerprint,
            definition_version=state.definition_version,
            state_version=state.state_version,
            expires_at=expires_at,
        )
        self._record(state, "approval_requested", step=step.name)

    def _compensate(self, state: WorkflowState) -> None:
        rejected = state.status == "business_rejected"
        if not state.compensations:
            if state.status == "failed":
                state.status = "failed_uncompensated"
            return
        state.status = "compensating"
        self._bump(state, "compensation_started")
        updated = list(state.compensations)
        for index in range(len(updated) - 1, -1, -1):
            record = updated[index]
            if record.status == "succeeded":
                continue
            key = f"{state.instance_id}:compensate:{record.original_step}:{record.action}:v1"
            try:
                self.effects.perform(key=key, action=record.action, intent=record.intent)
            except StepError as exc:
                updated[index] = CompensationRecord(
                    record.original_step,
                    record.action,
                    record.intent,
                    "failed",
                )
                state.compensations = updated
                state.status = "compensation_failed"
                self._bump(state, "compensation_failed", step=record.original_step, error_code=exc.code)
                return
            updated[index] = CompensationRecord(
                record.original_step,
                record.action,
                record.intent,
                "succeeded",
            )
            self._bump(state, "compensation_succeeded", step=record.original_step)
        state.compensations = updated
        state.status = "business_rejected_compensated" if rejected else "failed_compensated"
        self._bump(
            state,
            "instance_business_rejected_compensated" if rejected else "instance_failed_compensated",
        )

    def _validate_state_identity(self, state: WorkflowState) -> None:
        require(state.definition_name == self.definition.name, "checkpoint definition name mismatch")
        require(state.definition_version == self.definition.version, "checkpoint definition version mismatch")
        require(
            state.definition_fingerprint == self.definition.fingerprint,
            "checkpoint definition fingerprint mismatch",
        )
        require(set(state.steps) == set(self.definition.registry), "checkpoint step set mismatch")
        require(set(state.attempts) == set(self.definition.registry), "checkpoint attempt set mismatch")

    def _record(self, state: WorkflowState, event_type: str, **fields: Any) -> None:
        event = {"type": event_type, "state_version": state.state_version}
        event.update(fields)
        state.events.append(event)

    def _bump(self, state: WorkflowState, event_type: str, **fields: Any) -> None:
        state.state_version += 1
        self._record(state, event_type, **fields)


def encode_checkpoint(state: WorkflowState) -> str:
    payload = asdict(state)
    envelope = {
        "schema_version": 1,
        "definition_fingerprint": state.definition_fingerprint,
        "payload": payload,
        "sha256": fingerprint(payload),
    }
    return canonical_json(envelope)


def decode_checkpoint(raw: str, definition: WorkflowDefinition) -> WorkflowState:
    envelope = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    require(isinstance(envelope, dict), "checkpoint root must be an object")
    require(set(envelope) == CHECKPOINT_FIELDS, "checkpoint has missing or unknown fields")
    require(envelope["schema_version"] == 1, "unsupported checkpoint schema_version")
    require(
        envelope["definition_fingerprint"] == definition.fingerprint,
        "checkpoint definition fingerprint mismatch",
    )
    payload = envelope["payload"]
    require(isinstance(payload, dict) and set(payload) == STATE_FIELDS, "checkpoint payload shape is invalid")
    require(envelope["sha256"] == fingerprint(payload), "checkpoint integrity check failed")
    require(isinstance(payload["compensations"], list), "checkpoint compensations must be an array")
    require(
        payload["approval_request"] is None or isinstance(payload["approval_request"], dict),
        "checkpoint approval_request is invalid",
    )
    try:
        compensations = [CompensationRecord(**item) for item in payload["compensations"]]
        approval = (
            ApprovalRequest(**payload["approval_request"])
            if payload["approval_request"] is not None
            else None
        )
        state = WorkflowState(
            **{
                **payload,
                "compensations": compensations,
                "approval_request": approval,
            }
        )
    except (TypeError, KeyError) as exc:
        raise ValueError(f"checkpoint payload values are invalid: {exc}") from exc
    validator = WorkflowCoordinator(definition, EffectStore())
    validator._validate_state_identity(state)
    require(state.status in {
        "running",
        "waiting_approval",
        "completed",
        "business_rejected",
        "business_rejected_compensated",
        "failed_uncompensated",
        "failed_compensated",
        "compensation_failed",
    }, "checkpoint status is invalid")
    require(all(isinstance(value, int) and value >= 0 for value in state.attempts.values()), "invalid attempts")
    return state


def make_event(event_id: str, order_id: str, amount_cents: int) -> dict[str, Any]:
    return {
        "id": event_id,
        "source": "/offline-demo/orders",
        "specversion": "1.0",
        "type": "com.example.order.submitted.v1",
        "data": {"order_id": order_id, "amount_cents": amount_cents},
    }


def grant_for(request: ApprovalRequest, decision: str = "approve") -> ApprovalGrant:
    return ApprovalGrant(**asdict(request), decision=decision)


def run_demo(definition: WorkflowDefinition) -> dict[str, Any]:
    clock = [1_000]
    success_effects = EffectStore(unknown_once={"reserve_inventory"})
    first = WorkflowCoordinator(definition, success_effects, now=lambda: clock[0])
    state = first.start(make_event("event-success", "order-7", 2599))
    first.run_until_blocked(state)
    require(state.status == "waiting_approval", "demo should pause for approval")
    require(state.approval_request is not None, "demo approval request missing")
    request = state.approval_request

    with tempfile.TemporaryDirectory() as temp_directory:
        checkpoint_path = Path(temp_directory) / "checkpoint.json"
        checkpoint_path.write_text(encode_checkpoint(state), encoding="utf-8")
        restored = decode_checkpoint(checkpoint_path.read_text(encoding="utf-8"), definition)

    resumed = WorkflowCoordinator(definition, success_effects, now=lambda: clock[0])
    resumed.approve(restored, grant_for(request))
    resumed.run_until_blocked(restored)
    require(restored.status == "completed", "demo success workflow did not complete")
    require(success_effects.counts.get("reserve_inventory") == 1, "reservation was duplicated")

    failure_effects = EffectStore(permanent_failures={"notify"})
    failure = WorkflowCoordinator(definition, failure_effects, now=lambda: clock[0])
    failed_state = failure.start(make_event("event-failure", "order-8", 4999))
    failure.run_until_blocked(failed_state)
    require(failed_state.approval_request is not None, "failure demo approval request missing")
    failure.approve(failed_state, grant_for(failed_state.approval_request))
    failure.run_until_blocked(failed_state)
    require(failed_state.status == "failed_compensated", "failure demo was not compensated")
    require(failure_effects.counts.get("refund") == 1, "charge refund missing")
    require(failure_effects.counts.get("release_inventory") == 1, "inventory release missing")

    return {
        "status": "ok",
        "definition": definition.name,
        "version": definition.version,
        "definition_fingerprint": definition.fingerprint,
        "success": {
            "final_status": restored.status,
            "reserve_commits": success_effects.counts.get("reserve_inventory", 0),
            "charge_commits": success_effects.counts.get("charge", 0),
            "ready_parallel_batch": ["reserve_inventory", "risk_check"] in restored.ready_batches,
        },
        "failure": {
            "final_status": failed_state.status,
            "refund_commits": failure_effects.counts.get("refund", 0),
            "release_commits": failure_effects.counts.get("release_inventory", 0),
        },
        "note": "single-process teaching evidence; not production exactly-once",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or validate the offline workflow teaching project.")
    parser.add_argument("--validate", action="store_true", help="Validate the workflow definition only")
    args = parser.parse_args(argv)
    definition = load_definition(Path(__file__).with_name("workflow.json"))
    if args.validate:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "name": definition.name,
                    "version": definition.version,
                    "steps": len(definition.steps),
                    "fingerprint": definition.fingerprint,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    print(json.dumps(run_demo(definition), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from exc
