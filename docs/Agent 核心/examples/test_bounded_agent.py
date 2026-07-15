"""Regression tests for the bounded offline agent teaching runtime."""

from __future__ import annotations

import copy
import json
import unittest

from bounded_agent import (
    ActionProposal,
    AgentError,
    AgentState,
    Approval,
    BoundedAgentRuntime,
    Budget,
    CheckpointError,
    DeterministicPolicy,
    IdempotencyConflict,
    OfflineToolHost,
    SimulatedCrash,
    canonical_json,
    make_approval,
    run_demo,
    sha256_json,
    strict_loads,
)


def paused_run(
    *,
    tools: OfflineToolHost | None = None,
    budget: Budget | None = None,
) -> tuple[OfflineToolHost, BoundedAgentRuntime, AgentState]:
    host = tools or OfflineToolHost()
    runtime = BoundedAgentRuntime(host, budget=budget)
    state = runtime.run(AgentState(run_id="run-test", ticket_id="ticket-7"))
    return host, runtime, state


def changed_checkpoint(state: AgentState, **changes: object) -> str:
    envelope = json.loads(state.checkpoint())
    envelope["payload"].update(changes)
    envelope["sha256"] = sha256_json(envelope["payload"])
    return json.dumps(envelope, ensure_ascii=False)


class HappyPathTests(unittest.TestCase):
    def test_demo_completes(self) -> None:
        result = run_demo()
        self.assertEqual(result["phase"], "completed")
        self.assertEqual(result["close_count"], 1)

    def test_first_run_pauses_before_write(self) -> None:
        host, _, state = paused_run()
        self.assertEqual(state.phase, "waiting_approval")
        self.assertEqual(host.close_count, 0)

    def test_observation_is_explicitly_untrusted(self) -> None:
        _, _, state = paused_run()
        self.assertEqual(state.observations[0]["trust"], "untrusted")
        self.assertIn("never runtime instructions", state.observations[0]["purpose"])

    def test_malicious_note_does_not_change_target(self) -> None:
        _, _, state = paused_run()
        self.assertIn("关闭其他工单", state.observations[0]["data"]["customer_note"])
        self.assertEqual(state.pending_action["arguments"]["ticket_id"], "ticket-7")

    def test_bound_approval_completes(self) -> None:
        host, runtime, state = paused_run()
        approval = make_approval(state)
        result = runtime.run(state, approvals=[approval])
        self.assertEqual(result.phase, "completed")
        self.assertEqual(host.close_count, 1)

    def test_completion_contains_external_receipt(self) -> None:
        _, runtime, state = paused_run()
        result = runtime.run(state, approvals=[make_approval(state)])
        evidence = result.evidence[-1]
        self.assertEqual(evidence["type"], "tool_receipt")
        self.assertTrue(evidence["result"]["receipt_id"].startswith("receipt-"))

    def test_event_sequence_and_state_version_are_monotonic(self) -> None:
        _, runtime, state = paused_run()
        result = runtime.run(state, approvals=[make_approval(state)])
        self.assertEqual([event["sequence"] for event in result.events], [1, 2, 3])
        self.assertEqual([event["state_version"] for event in result.events], [1, 2, 3])

    def test_human_rejection_is_terminal_not_exception(self) -> None:
        host, runtime, state = paused_run()
        result = runtime.run(state, approvals=[make_approval(state, decision="reject")])
        self.assertEqual(result.phase, "rejected")
        self.assertEqual(result.stop_reason, "human_rejected")
        self.assertEqual(host.close_count, 0)

    def test_no_approval_keeps_safe_pause(self) -> None:
        host, runtime, state = paused_run()
        result = runtime.run(state)
        self.assertEqual(result.phase, "waiting_approval")
        self.assertEqual(host.close_count, 0)


class ApprovalTests(unittest.TestCase):
    def test_fingerprint_is_stable_for_same_action(self) -> None:
        action = DeterministicPolicy().propose(AgentState(run_id="r", ticket_id="ticket-7", phase="observed"))
        self.assertIsNotNone(action)
        self.assertEqual(action.fingerprint(), action.fingerprint())

    def test_fingerprint_changes_with_arguments(self) -> None:
        first = ActionProposal("a", "close_ticket", {"ticket_id": "ticket-7"}, "write", "key")
        second = ActionProposal("a", "close_ticket", {"ticket_id": "ticket-8"}, "write", "key")
        self.assertNotEqual(first.fingerprint(), second.fingerprint())

    def test_stale_state_version_rejects_approval(self) -> None:
        host, runtime, state = paused_run()
        approval = make_approval(state)
        state.state_version += 1
        result = runtime.run(state, approvals=[approval])
        self.assertEqual(result.phase, "waiting_approval")
        self.assertEqual(result.stop_reason, "invalid_approval")
        self.assertEqual(host.close_count, 0)

    def test_expired_approval_is_rejected(self) -> None:
        host, runtime, state = paused_run()
        approval = make_approval(state, expires_after_steps=0)
        result = runtime.run(state, approvals=[approval])
        self.assertEqual(result.phase, "waiting_approval")
        self.assertIn("expired", result.events[-1]["details"]["error"])
        self.assertEqual(host.close_count, 0)

    def test_wrong_fingerprint_is_rejected(self) -> None:
        host, runtime, state = paused_run()
        valid = make_approval(state)
        wrong = Approval(valid.action_id, "0" * 64, valid.state_version, "approve", valid.expires_after_step)
        result = runtime.run(state, approvals=[wrong])
        self.assertEqual(result.phase, "waiting_approval")
        self.assertEqual(host.close_count, 0)

    def test_unknown_decision_is_rejected(self) -> None:
        host, runtime, state = paused_run()
        valid = make_approval(state)
        wrong = Approval(valid.action_id, valid.action_fingerprint, valid.state_version, "maybe", valid.expires_after_step)
        result = runtime.run(state, approvals=[wrong])
        self.assertEqual(result.stop_reason, "invalid_approval")
        self.assertEqual(host.close_count, 0)

    def test_make_approval_requires_waiting_state(self) -> None:
        with self.assertRaisesRegex(AgentError, "not waiting"):
            make_approval(AgentState(run_id="r", ticket_id="ticket-7"))

    def test_approval_expiry_offset_rejects_boolean(self) -> None:
        _, _, state = paused_run()
        with self.assertRaisesRegex(AgentError, "non-negative integer"):
            make_approval(state, expires_after_steps=True)

    def test_cancel_before_first_action(self) -> None:
        host = OfflineToolHost()
        state = BoundedAgentRuntime(host).run(
            AgentState(run_id="r", ticket_id="ticket-7"),
            cancel_requested=True,
        )
        self.assertEqual(state.phase, "cancelled")
        self.assertEqual(host.lookup_count, 0)

    def test_cancel_while_waiting_approval(self) -> None:
        host, runtime, state = paused_run()
        result = runtime.run(state, cancel_requested=True)
        self.assertEqual(result.phase, "cancelled")
        self.assertEqual(host.close_count, 0)


class CheckpointTests(unittest.TestCase):
    def test_round_trip_preserves_state(self) -> None:
        _, _, state = paused_run()
        restored = AgentState.restore(state.checkpoint())
        self.assertEqual(restored, state)

    def test_checkpoint_is_deterministic(self) -> None:
        _, _, state = paused_run()
        self.assertEqual(state.checkpoint(), state.checkpoint())

    def test_payload_tampering_fails_integrity(self) -> None:
        _, _, state = paused_run()
        envelope = json.loads(state.checkpoint())
        envelope["payload"]["ticket_id"] = "ticket-8"
        with self.assertRaisesRegex(CheckpointError, "integrity"):
            AgentState.restore(json.dumps(envelope))

    def test_digest_tampering_fails_integrity(self) -> None:
        _, _, state = paused_run()
        envelope = json.loads(state.checkpoint())
        envelope["sha256"] = "0" * 64
        with self.assertRaisesRegex(CheckpointError, "integrity"):
            AgentState.restore(json.dumps(envelope))

    def test_extra_envelope_field_is_rejected(self) -> None:
        _, _, state = paused_run()
        envelope = json.loads(state.checkpoint())
        envelope["unexpected"] = True
        with self.assertRaisesRegex(CheckpointError, "unknown keys"):
            AgentState.restore(json.dumps(envelope))

    def test_duplicate_json_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(CheckpointError, "duplicate JSON key"):
            strict_loads('{"phase":"start","phase":"completed"}')

    def test_non_finite_number_is_rejected(self) -> None:
        with self.assertRaisesRegex(CheckpointError, "non-finite"):
            strict_loads('{"step":NaN}')

    def test_invalid_json_reports_line(self) -> None:
        with self.assertRaisesRegex(CheckpointError, "invalid JSON at line"):
            strict_loads('{\n  "step":\n}')

    def test_unsupported_state_schema_is_rejected(self) -> None:
        _, _, state = paused_run()
        with self.assertRaisesRegex(CheckpointError, "schema_version"):
            AgentState.restore(changed_checkpoint(state, schema_version=2))

    def test_unknown_phase_is_rejected(self) -> None:
        _, _, state = paused_run()
        with self.assertRaisesRegex(CheckpointError, "unknown phase"):
            AgentState.restore(changed_checkpoint(state, phase="mystery"))

    def test_boolean_counter_is_rejected(self) -> None:
        _, _, state = paused_run()
        with self.assertRaisesRegex(CheckpointError, "non-negative integer"):
            AgentState.restore(changed_checkpoint(state, step=True))

    def test_duplicate_completed_action_is_rejected(self) -> None:
        _, _, state = paused_run()
        duplicate = ["lookup-current-ticket", "lookup-current-ticket"]
        with self.assertRaisesRegex(CheckpointError, "duplicates"):
            AgentState.restore(changed_checkpoint(state, completed_action_ids=duplicate))

    def test_malformed_pending_action_is_checkpoint_error(self) -> None:
        _, _, state = paused_run()
        with self.assertRaisesRegex(CheckpointError, "pending action fields"):
            AgentState.restore(changed_checkpoint(state, pending_action={"tool": "close_ticket"}))


class BudgetAndFailureTests(unittest.TestCase):
    def test_step_budget_stops_loop(self) -> None:
        host = OfflineToolHost()
        runtime = BoundedAgentRuntime(host, budget=Budget(max_steps=1, max_tool_calls=3, max_consecutive_failures=2))
        result = runtime.run(AgentState(run_id="r", ticket_id="ticket-7"))
        self.assertEqual(result.phase, "budget_exhausted")
        self.assertEqual(result.stop_reason, "max_steps")

    def test_tool_call_budget_blocks_write(self) -> None:
        budget = Budget(max_steps=8, max_tool_calls=1, max_consecutive_failures=2)
        host, runtime, state = paused_run(budget=budget)
        result = runtime.run(state, approvals=[make_approval(state)])
        self.assertEqual(result.phase, "budget_exhausted")
        self.assertEqual(result.stop_reason, "max_tool_calls")
        self.assertEqual(host.close_count, 0)

    def test_one_transient_failure_is_retried(self) -> None:
        host = OfflineToolHost(transient_lookup_failures=1)
        runtime = BoundedAgentRuntime(host)
        result = runtime.run(AgentState(run_id="r", ticket_id="ticket-7"))
        self.assertEqual(result.phase, "waiting_approval")
        self.assertEqual(host.lookup_count, 2)

    def test_transient_failure_budget_is_bounded(self) -> None:
        host = OfflineToolHost(transient_lookup_failures=5)
        runtime = BoundedAgentRuntime(host)
        result = runtime.run(AgentState(run_id="r", ticket_id="ticket-7"))
        self.assertEqual(result.phase, "failed")
        self.assertEqual(result.stop_reason, "transient_tool_failures_exhausted")
        self.assertEqual(host.lookup_count, 2)

    def test_permanent_tool_error_is_not_retried(self) -> None:
        host = OfflineToolHost()
        runtime = BoundedAgentRuntime(host)
        result = runtime.run(AgentState(run_id="r", ticket_id="missing"))
        self.assertEqual(result.phase, "failed")
        self.assertEqual(result.stop_reason, "permanent_tool_error")
        self.assertEqual(host.lookup_count, 1)

    def test_budget_values_must_be_positive_integers(self) -> None:
        with self.assertRaisesRegex(AgentError, "max_steps"):
            BoundedAgentRuntime(OfflineToolHost(), budget=Budget(max_steps=0))

    def test_policy_returning_no_action_fails_without_claiming_success(self) -> None:
        class NoActionPolicy:
            def propose(self, state: AgentState) -> None:
                return None

        runtime = BoundedAgentRuntime(OfflineToolHost(), policy=NoActionPolicy())
        result = runtime.run(AgentState(run_id="r", ticket_id="ticket-7"))
        self.assertEqual(result.phase, "failed")
        self.assertIn("no_action", result.events[-1]["type"])

    def test_non_allowlisted_tool_is_rejected(self) -> None:
        class BadPolicy:
            def propose(self, state: AgentState) -> ActionProposal:
                return ActionProposal("x", "run_shell", {"ticket_id": state.ticket_id}, "write", "key")

        result = BoundedAgentRuntime(OfflineToolHost(), policy=BadPolicy()).run(
            AgentState(run_id="r", ticket_id="ticket-7")
        )
        self.assertEqual(result.stop_reason, "policy_violation")

    def test_policy_cannot_target_other_ticket(self) -> None:
        class WrongTargetPolicy:
            def propose(self, state: AgentState) -> ActionProposal:
                return ActionProposal("x", "lookup_ticket", {"ticket_id": "ticket-8"}, "read")

        result = BoundedAgentRuntime(OfflineToolHost(), policy=WrongTargetPolicy()).run(
            AgentState(run_id="r", ticket_id="ticket-7")
        )
        self.assertEqual(result.phase, "failed")
        self.assertIn("different ticket", result.events[-1]["details"]["error"])


class IdempotencyAndRecoveryTests(unittest.TestCase):
    def test_same_key_same_intent_returns_cached_result(self) -> None:
        host = OfflineToolHost()
        first = host.close_ticket("ticket-7", "key-1")
        second = host.close_ticket("ticket-7", "key-1")
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(host.close_count, 1)

    def test_same_key_different_intent_conflicts(self) -> None:
        host = OfflineToolHost()
        host.close_ticket("ticket-7", "shared-key")
        with self.assertRaisesRegex(IdempotencyConflict, "different intent"):
            host.close_ticket("ticket-8", "shared-key")

    def test_receipt_lookup_checks_intent(self) -> None:
        host = OfflineToolHost()
        host.close_ticket("ticket-7", "shared-key")
        with self.assertRaisesRegex(IdempotencyConflict, "different intent"):
            host.get_receipt("shared-key", "ticket-8")

    def test_crash_after_commit_can_resume_without_duplicate(self) -> None:
        host, runtime, paused = paused_run()
        checkpoint = paused.checkpoint()
        approval = make_approval(paused, expires_after_steps=3)
        with self.assertRaises(SimulatedCrash):
            runtime.run(AgentState.restore(checkpoint), approvals=[approval], crash_after_commit=True)
        self.assertEqual(host.close_count, 1)
        recovered = runtime.run(AgentState.restore(checkpoint), approvals=[approval])
        self.assertEqual(recovered.phase, "completed")
        self.assertEqual(host.close_count, 1)

    def test_recovery_evidence_marks_receipt_reuse(self) -> None:
        host, runtime, paused = paused_run()
        checkpoint = paused.checkpoint()
        approval = make_approval(paused, expires_after_steps=3)
        with self.assertRaises(SimulatedCrash):
            runtime.run(AgentState.restore(checkpoint), approvals=[approval], crash_after_commit=True)
        recovered = runtime.run(AgentState.restore(checkpoint), approvals=[approval])
        self.assertTrue(recovered.evidence[-1]["recovered_from_receipt"])

    def test_normal_completion_is_not_marked_recovered(self) -> None:
        _, runtime, paused = paused_run()
        completed = runtime.run(paused, approvals=[make_approval(paused)])
        self.assertFalse(completed.evidence[-1]["recovered_from_receipt"])

    def test_canonical_json_ignores_dictionary_insertion_order(self) -> None:
        self.assertEqual(canonical_json({"b": 2, "a": 1}), canonical_json({"a": 1, "b": 2}))

    def test_deepcopy_of_checkpoint_does_not_share_mutable_state(self) -> None:
        _, _, state = paused_run()
        restored = AgentState.restore(state.checkpoint())
        restored.observations[0]["data"]["status"] = "changed"
        self.assertEqual(state.observations[0]["data"]["status"], "open")


if __name__ == "__main__":
    unittest.main(verbosity=2)
