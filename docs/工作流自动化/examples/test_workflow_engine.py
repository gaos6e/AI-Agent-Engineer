"""Offline regression tests for the workflow automation teaching project."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


EXAMPLES = Path(__file__).resolve().parent
ENGINE_PATH = EXAMPLES / "workflow_engine.py"
DEFINITION_PATH = EXAMPLES / "workflow.json"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


engine = load_module("workflow_engine_teaching", ENGINE_PATH)


def definition_data() -> dict[str, Any]:
    return json.loads(DEFINITION_PATH.read_text(encoding="utf-8"))


def load_modified_definition(modify: Callable[[dict[str, Any]], None]) -> Any:
    data = definition_data()
    modify(data)
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "workflow.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return engine.load_definition(path)


class DefinitionValidationTests(unittest.TestCase):
    def test_valid_definition(self) -> None:
        definition = engine.load_definition(DEFINITION_PATH)
        self.assertEqual(definition.name, "offline-order-workflow")
        self.assertEqual(len(definition.steps), 5)

    def assert_invalid(self, modify: Callable[[dict[str, Any]], None], pattern: str) -> None:
        with self.assertRaisesRegex(ValueError, pattern):
            load_modified_definition(modify)

    def test_unknown_top_level_field(self) -> None:
        self.assert_invalid(lambda data: data.update({"unknown": 1}), "top-level")

    def test_missing_top_level_field(self) -> None:
        self.assert_invalid(lambda data: data.pop("version"), "top-level")

    def test_empty_name(self) -> None:
        self.assert_invalid(lambda data: data.update({"name": ""}), "name")

    def test_empty_version(self) -> None:
        self.assert_invalid(lambda data: data.update({"version": ""}), "version")

    def test_boolean_attempt_budget_is_invalid(self) -> None:
        self.assert_invalid(lambda data: data.update({"max_total_attempts": True}), "positive integer")

    def test_attempt_budget_must_cover_steps(self) -> None:
        self.assert_invalid(lambda data: data.update({"max_total_attempts": 4}), "every step")

    def test_steps_must_not_be_empty(self) -> None:
        self.assert_invalid(lambda data: data.update({"steps": []}), "non-empty")

    def test_step_unknown_field(self) -> None:
        self.assert_invalid(lambda data: data["steps"][0].update({"x": 1}), "step 1")

    def test_step_missing_field(self) -> None:
        self.assert_invalid(lambda data: data["steps"][0].pop("handler"), "step 1")

    def test_duplicate_step_name(self) -> None:
        self.assert_invalid(lambda data: data["steps"][1].update({"name": "validate"}), "duplicate step")

    def test_duplicate_dependency(self) -> None:
        self.assert_invalid(
            lambda data: data["steps"][3].update({"needs": ["risk_check", "risk_check"]}),
            "duplicate dependencies",
        )

    def test_unknown_dependency(self) -> None:
        self.assert_invalid(lambda data: data["steps"][1].update({"needs": ["missing"]}), "unknown dependencies")

    def test_self_dependency(self) -> None:
        self.assert_invalid(
            lambda data: data["steps"][1].update({"needs": ["reserve_inventory"]}),
            "depend on itself",
        )

    def test_cycle(self) -> None:
        def modify(data: dict[str, Any]) -> None:
            data["steps"][0]["needs"] = ["notify"]

        self.assert_invalid(modify, "cycle")

    def test_unknown_handler(self) -> None:
        self.assert_invalid(lambda data: data["steps"][0].update({"handler": "shell"}), "unknown handler")

    def test_approval_must_be_boolean(self) -> None:
        self.assert_invalid(lambda data: data["steps"][0].update({"approval": "no"}), "boolean")

    def test_max_attempts_must_be_positive(self) -> None:
        self.assert_invalid(lambda data: data["steps"][1].update({"max_attempts": 0}), "positive integer")

    def test_retryable_errors_must_be_array(self) -> None:
        self.assert_invalid(lambda data: data["steps"][1].update({"retryable_errors": "TRANSIENT"}), "array")

    def test_unknown_retryable_error(self) -> None:
        self.assert_invalid(lambda data: data["steps"][1].update({"retryable_errors": ["MAGIC"]}), "unknown retryable")

    def test_duplicate_retryable_error(self) -> None:
        self.assert_invalid(
            lambda data: data["steps"][1].update({"retryable_errors": ["TRANSIENT", "TRANSIENT"]}),
            "duplicate retryable",
        )

    def test_unknown_compensation(self) -> None:
        self.assert_invalid(lambda data: data["steps"][1].update({"compensate": "erase"}), "unknown compensation")

    def test_duplicate_json_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "workflow.json"
            path.write_text('{"name":"a","name":"b"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                engine.load_definition(path)


class EventValidationTests(unittest.TestCase):
    def valid_event(self) -> dict[str, Any]:
        return engine.make_event("event-1", "order-1", 100)

    def test_valid_event(self) -> None:
        self.assertEqual(engine.validate_event(self.valid_event())["amount_cents"], 100)

    def test_missing_required_field(self) -> None:
        event = self.valid_event()
        event.pop("id")
        with self.assertRaisesRegex(ValueError, "missing required"):
            engine.validate_event(event)

    def test_unknown_event_field(self) -> None:
        event = self.valid_event()
        event["secret"] = "x"
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            engine.validate_event(event)

    def test_wrong_specversion(self) -> None:
        event = self.valid_event()
        event["specversion"] = "0.3"
        with self.assertRaisesRegex(ValueError, "specversion"):
            engine.validate_event(event)

    def test_wrong_event_type(self) -> None:
        event = self.valid_event()
        event["type"] = "other"
        with self.assertRaisesRegex(ValueError, "unsupported event type"):
            engine.validate_event(event)

    def test_data_must_be_object(self) -> None:
        event = self.valid_event()
        event["data"] = []
        with self.assertRaisesRegex(ValueError, "data must be an object"):
            engine.validate_event(event)

    def test_data_unknown_field(self) -> None:
        event = self.valid_event()
        event["data"]["currency"] = "CNY"
        with self.assertRaisesRegex(ValueError, "data has missing or unknown"):
            engine.validate_event(event)

    def test_empty_order_id(self) -> None:
        event = self.valid_event()
        event["data"]["order_id"] = ""
        with self.assertRaisesRegex(ValueError, "order_id"):
            engine.validate_event(event)

    def test_zero_amount(self) -> None:
        event = self.valid_event()
        event["data"]["amount_cents"] = 0
        with self.assertRaisesRegex(ValueError, "positive integer"):
            engine.validate_event(event)

    def test_boolean_amount_is_invalid(self) -> None:
        event = self.valid_event()
        event["data"]["amount_cents"] = True
        with self.assertRaisesRegex(ValueError, "positive integer"):
            engine.validate_event(event)


class EffectStoreTests(unittest.TestCase):
    def test_same_key_and_intent_reuses_result(self) -> None:
        store = engine.EffectStore()
        first = store.perform(key="k", action="charge", intent={"amount": 1})
        second = store.perform(key="k", action="charge", intent={"amount": 1})
        self.assertEqual(first, second)
        self.assertEqual(store.counts["charge"], 1)

    def test_same_key_different_intent_conflicts(self) -> None:
        store = engine.EffectStore()
        store.perform(key="k", action="charge", intent={"amount": 1})
        with self.assertRaisesRegex(ValueError, "idempotency conflict"):
            store.perform(key="k", action="charge", intent={"amount": 2})

    def test_same_key_different_action_conflicts(self) -> None:
        store = engine.EffectStore()
        store.perform(key="k", action="charge", intent={"amount": 1})
        with self.assertRaisesRegex(ValueError, "action conflict"):
            store.perform(key="k", action="refund", intent={"amount": 1})

    def test_unknown_result_commits_once(self) -> None:
        store = engine.EffectStore(unknown_once={"charge"})
        with self.assertRaises(engine.UnknownResultError):
            store.perform(key="k", action="charge", intent={"amount": 1})
        result = store.perform(key="k", action="charge", intent={"amount": 1})
        self.assertIn("receipt", result)
        self.assertEqual(store.counts["charge"], 1)

    def test_transient_failure_does_not_commit(self) -> None:
        store = engine.EffectStore(transient_failures={"charge": 1})
        with self.assertRaises(engine.TransientStepError):
            store.perform(key="k", action="charge", intent={"amount": 1})
        self.assertNotIn("k", store.records)

    def test_permanent_failure_does_not_commit(self) -> None:
        store = engine.EffectStore(permanent_failures={"charge"})
        with self.assertRaises(engine.PermanentStepError):
            store.perform(key="k", action="charge", intent={"amount": 1})
        self.assertNotIn("k", store.records)


class WorkflowExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.definition = engine.load_definition(DEFINITION_PATH)
        self.clock = [1000]

    def coordinator(self, effects: Any | None = None) -> Any:
        return engine.WorkflowCoordinator(
            self.definition,
            effects or engine.EffectStore(),
            now=lambda: self.clock[0],
            approval_ttl=60,
        )

    def pause(self, effects: Any | None = None) -> tuple[Any, Any]:
        coordinator = self.coordinator(effects)
        state = coordinator.start(engine.make_event("event-1", "order-1", 100))
        coordinator.run_until_blocked(state)
        return coordinator, state

    def test_same_event_returns_same_instance(self) -> None:
        coordinator = self.coordinator()
        event = engine.make_event("event-1", "order-1", 100)
        self.assertIs(coordinator.start(event), coordinator.start(event))

    def test_same_event_key_different_payload_conflicts(self) -> None:
        coordinator = self.coordinator()
        coordinator.start(engine.make_event("event-1", "order-1", 100))
        with self.assertRaisesRegex(ValueError, "different payload"):
            coordinator.start(engine.make_event("event-1", "order-1", 101))

    def test_independent_steps_share_ready_batch(self) -> None:
        _, state = self.pause()
        self.assertIn(["reserve_inventory", "risk_check"], state.ready_batches)

    def test_workflow_pauses_before_charge(self) -> None:
        effects = engine.EffectStore()
        _, state = self.pause(effects)
        self.assertEqual(state.status, "waiting_approval")
        self.assertEqual(effects.counts.get("charge", 0), 0)

    def test_valid_approval_completes(self) -> None:
        coordinator, state = self.pause()
        coordinator.approve(state, engine.grant_for(state.approval_request))
        coordinator.run_until_blocked(state)
        self.assertEqual(state.status, "completed")

    def test_approval_is_bound_to_request_id(self) -> None:
        coordinator, state = self.pause()
        values = asdict(engine.grant_for(state.approval_request))
        values["request_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "does not match"):
            coordinator.approve(state, engine.ApprovalGrant(**values))

    def test_approval_is_bound_to_payload(self) -> None:
        coordinator, state = self.pause()
        values = asdict(engine.grant_for(state.approval_request))
        values["payload_fingerprint"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "does not match"):
            coordinator.approve(state, engine.ApprovalGrant(**values))

    def test_approval_is_bound_to_definition_version(self) -> None:
        coordinator, state = self.pause()
        values = asdict(engine.grant_for(state.approval_request))
        values["definition_version"] = "2.0.0"
        with self.assertRaisesRegex(ValueError, "does not match"):
            coordinator.approve(state, engine.ApprovalGrant(**values))

    def test_approval_is_bound_to_state_version(self) -> None:
        coordinator, state = self.pause()
        values = asdict(engine.grant_for(state.approval_request))
        values["state_version"] += 1
        with self.assertRaisesRegex(ValueError, "does not match"):
            coordinator.approve(state, engine.ApprovalGrant(**values))

    def test_expired_approval_fails(self) -> None:
        coordinator, state = self.pause()
        grant = engine.grant_for(state.approval_request)
        self.clock[0] = grant.expires_at + 1
        with self.assertRaisesRegex(ValueError, "expired"):
            coordinator.approve(state, grant)

    def test_rejected_approval_compensates_inventory(self) -> None:
        effects = engine.EffectStore()
        coordinator, state = self.pause(effects)
        coordinator.approve(state, engine.grant_for(state.approval_request, "reject"))
        self.assertEqual(state.status, "business_rejected_compensated")
        self.assertEqual(effects.counts["release_inventory"], 1)

    def test_unknown_result_is_recovered_without_duplicate(self) -> None:
        effects = engine.EffectStore(unknown_once={"reserve_inventory"})
        _, state = self.pause(effects)
        self.assertEqual(state.attempts["reserve_inventory"], 2)
        self.assertEqual(effects.counts["reserve_inventory"], 1)

    def test_transient_charge_retries_then_succeeds(self) -> None:
        effects = engine.EffectStore(transient_failures={"charge": 1})
        coordinator, state = self.pause(effects)
        coordinator.approve(state, engine.grant_for(state.approval_request))
        coordinator.run_until_blocked(state)
        self.assertEqual(state.status, "completed")
        self.assertEqual(state.attempts["charge"], 2)

    def test_permanent_reservation_failure_has_no_compensation(self) -> None:
        effects = engine.EffectStore(permanent_failures={"reserve_inventory"})
        coordinator = self.coordinator(effects)
        state = coordinator.start(engine.make_event("event-1", "order-1", 100))
        coordinator.run_until_blocked(state)
        self.assertEqual(state.status, "failed_uncompensated")

    def test_permanent_notification_failure_compensates_reverse_order(self) -> None:
        effects = engine.EffectStore(permanent_failures={"notify"})
        coordinator, state = self.pause(effects)
        coordinator.approve(state, engine.grant_for(state.approval_request))
        coordinator.run_until_blocked(state)
        self.assertEqual(state.status, "failed_compensated")
        actions = [record.action for record in effects.records.values()]
        self.assertLess(actions.index("refund"), actions.index("release_inventory"))

    def test_retry_exhaustion_compensates(self) -> None:
        effects = engine.EffectStore(transient_failures={"notify": 5})
        coordinator, state = self.pause(effects)
        coordinator.approve(state, engine.grant_for(state.approval_request))
        coordinator.run_until_blocked(state)
        self.assertEqual(state.attempts["notify"], 2)
        self.assertEqual(state.status, "failed_compensated")

    def test_compensation_failure_is_explicit(self) -> None:
        effects = engine.EffectStore(permanent_failures={"notify", "refund"})
        coordinator, state = self.pause(effects)
        coordinator.approve(state, engine.grant_for(state.approval_request))
        coordinator.run_until_blocked(state)
        self.assertEqual(state.status, "compensation_failed")
        self.assertEqual(state.compensations[-1].status, "failed")

    def test_total_attempt_budget_is_terminal(self) -> None:
        definition = load_modified_definition(lambda data: data.update({"max_total_attempts": 5}))
        effects = engine.EffectStore(unknown_once={"reserve_inventory"})
        coordinator = engine.WorkflowCoordinator(definition, effects, now=lambda: self.clock[0])
        state = coordinator.start(engine.make_event("event-1", "order-1", 100))
        coordinator.run_until_blocked(state)
        coordinator.approve(state, engine.grant_for(state.approval_request))
        coordinator.run_until_blocked(state)
        self.assertEqual(state.status, "failed_compensated")
        self.assertTrue(any(event["type"] == "attempt_budget_exhausted" for event in state.events))

    def test_events_do_not_contain_order_payload(self) -> None:
        _, state = self.pause()
        serialized = json.dumps(state.events, ensure_ascii=False)
        self.assertNotIn("order-1", serialized)
        self.assertNotIn("amount_cents", serialized)


class CheckpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.definition = engine.load_definition(DEFINITION_PATH)
        self.coordinator = engine.WorkflowCoordinator(self.definition, engine.EffectStore(), now=lambda: 1000)
        self.state = self.coordinator.start(engine.make_event("event-1", "order-1", 100))
        self.coordinator.run_until_blocked(self.state)

    def test_round_trip_waiting_state(self) -> None:
        restored = engine.decode_checkpoint(engine.encode_checkpoint(self.state), self.definition)
        self.assertEqual(restored.status, "waiting_approval")
        self.assertEqual(restored.approval_request, self.state.approval_request)

    def test_tampered_payload_fails_integrity(self) -> None:
        envelope = json.loads(engine.encode_checkpoint(self.state))
        envelope["payload"]["data"]["amount_cents"] = 999
        with self.assertRaisesRegex(ValueError, "integrity"):
            engine.decode_checkpoint(json.dumps(envelope), self.definition)

    def test_unknown_envelope_field_fails(self) -> None:
        envelope = json.loads(engine.encode_checkpoint(self.state))
        envelope["extra"] = True
        with self.assertRaisesRegex(ValueError, "missing or unknown"):
            engine.decode_checkpoint(json.dumps(envelope), self.definition)

    def test_unknown_payload_field_fails(self) -> None:
        envelope = json.loads(engine.encode_checkpoint(self.state))
        envelope["payload"]["extra"] = True
        envelope["sha256"] = engine.fingerprint(envelope["payload"])
        with self.assertRaisesRegex(ValueError, "payload shape"):
            engine.decode_checkpoint(json.dumps(envelope), self.definition)

    def test_wrong_schema_version_fails(self) -> None:
        envelope = json.loads(engine.encode_checkpoint(self.state))
        envelope["schema_version"] = 2
        with self.assertRaisesRegex(ValueError, "schema_version"):
            engine.decode_checkpoint(json.dumps(envelope), self.definition)

    def test_wrong_definition_fingerprint_fails(self) -> None:
        envelope = json.loads(engine.encode_checkpoint(self.state))
        envelope["definition_fingerprint"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            engine.decode_checkpoint(json.dumps(envelope), self.definition)

    def test_wrong_step_set_fails(self) -> None:
        envelope = json.loads(engine.encode_checkpoint(self.state))
        envelope["payload"]["steps"].pop("notify")
        envelope["sha256"] = engine.fingerprint(envelope["payload"])
        with self.assertRaisesRegex(ValueError, "step set mismatch"):
            engine.decode_checkpoint(json.dumps(envelope), self.definition)

    def test_negative_attempt_fails(self) -> None:
        envelope = json.loads(engine.encode_checkpoint(self.state))
        envelope["payload"]["attempts"]["validate"] = -1
        envelope["sha256"] = engine.fingerprint(envelope["payload"])
        with self.assertRaisesRegex(ValueError, "invalid attempts"):
            engine.decode_checkpoint(json.dumps(envelope), self.definition)

    def test_invalid_status_fails(self) -> None:
        envelope = json.loads(engine.encode_checkpoint(self.state))
        envelope["payload"]["status"] = "magic"
        envelope["sha256"] = engine.fingerprint(envelope["payload"])
        with self.assertRaisesRegex(ValueError, "status is invalid"):
            engine.decode_checkpoint(json.dumps(envelope), self.definition)

    def test_duplicate_checkpoint_key_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            engine.decode_checkpoint('{"schema_version":1,"schema_version":1}', self.definition)


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(ENGINE_PATH), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_validate_cli(self) -> None:
        result = self.run_cli("--validate")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["status"], "ok")

    def test_demo_cli(self) -> None:
        result = self.run_cli()
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(output["success"]["reserve_commits"], 1)
        self.assertEqual(output["failure"]["final_status"], "failed_compensated")

    def test_help_cli(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--validate", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
