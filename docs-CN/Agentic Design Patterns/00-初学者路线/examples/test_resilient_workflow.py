"""Tests for resilient_workflow.py that remain meaningful under python -O."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import resilient_workflow as workflow


class WorkflowTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.checkpoint = self.root / "state.json"
        self.receipt = self.root / "receipt.json"

    def run_workflow(self, **overrides: object) -> dict[str, object]:
        arguments: dict[str, object] = {
            "checkpoint_path": self.checkpoint,
            "receipt_path": self.receipt,
            "task_id": "case-001",
            "risk": "low",
        }
        arguments.update(overrides)
        return workflow.run(**arguments)  # type: ignore[arg-type]


class StateValidationTests(WorkflowTestCase):
    def test_new_state_is_valid(self) -> None:
        state = workflow.new_state("task-1", "low")
        workflow.validate_state(state)
        self.assertEqual(state["stage"], "start")

    def test_invalid_task_id_is_rejected(self) -> None:
        with self.assertRaises(workflow.WorkflowError):
            workflow.new_state("含中文", "low")

    def test_empty_task_id_is_rejected(self) -> None:
        with self.assertRaises(workflow.WorkflowError):
            workflow.new_state("", "low")

    def test_invalid_risk_is_rejected(self) -> None:
        with self.assertRaises(workflow.WorkflowError):
            workflow.new_state("task-1", "medium")

    def test_unknown_state_field_is_rejected(self) -> None:
        state = workflow.new_state("task-1", "low")
        state["surprise"] = True
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_state(state)

    def test_boolean_revision_is_rejected(self) -> None:
        state = workflow.new_state("task-1", "low")
        state["revision"] = True
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_state(state)

    def test_tampered_action_is_rejected(self) -> None:
        state = workflow.new_state("task-1", "low")
        state["action"]["target"] = "other-target"
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_state(state)

    def test_non_contiguous_event_revision_is_rejected(self) -> None:
        state = workflow.new_state("task-1", "low")
        state["revision"] = 1
        state["events"] = [{"revision": 2, "name": "bad"}]
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_state(state)

    def test_unknown_check_branch_is_rejected(self) -> None:
        state = workflow.new_state("task-1", "low")
        state["checks"] = {
            "mystery": {"ok": True, "category": "ok", "evidence": "x"}
        }
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_state(state)

    def test_check_result_contradiction_is_rejected(self) -> None:
        state = workflow.new_state("task-1", "low")
        state["checks"] = {
            "input": {"ok": False, "category": "ok", "evidence": "x"}
        }
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_state(state)

    def test_approval_must_match_checked_action_context(self) -> None:
        state = self.run_workflow(risk="high")
        state["approval"] = {
            "decision": "approved",
            "approval_fingerprint": "0" * 64,
            "based_on_revision": state["revision"],
        }
        state["stage"] = "execute"
        workflow.append_event(state, "approval:approved")
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_state(state)

    def test_approved_context_rejects_changed_check_evidence(self) -> None:
        state = self.run_workflow(risk="high")
        state["approval"] = {
            "decision": "approved",
            "approval_fingerprint": workflow.approval_fingerprint_for(state),
            "based_on_revision": state["revision"],
        }
        state["stage"] = "execute"
        workflow.append_event(state, "approval:approved")
        workflow.validate_state(state)
        state["checks"]["policy"]["evidence"] = "different policy evidence"
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_state(state)

    def test_awaiting_approval_requires_passed_checks(self) -> None:
        state = workflow.new_state("task-1", "high")
        state["stage"] = "awaiting_approval"
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_state(state)

    def test_approval_cannot_appear_before_execute(self) -> None:
        state = self.run_workflow(risk="high")
        state["approval"] = {
            "decision": "approved",
            "approval_fingerprint": workflow.approval_fingerprint_for(state),
            "based_on_revision": state["revision"],
        }
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_state(state)

    def test_unknown_policy_revision_is_rejected(self) -> None:
        state = workflow.new_state("task-1", "low")
        state["policy_revision"] = "old-policy"
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_state(state)

    def test_high_risk_execute_without_approval_is_rejected(self) -> None:
        state = workflow.new_state("task-1", "high")
        state["stage"] = "execute"
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_state(state)

    def test_done_without_receipt_is_rejected(self) -> None:
        state = workflow.new_state("task-1", "low")
        state["stage"] = "done"
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_state(state)

    def test_low_risk_approval_is_rejected(self) -> None:
        state = workflow.new_state("task-1", "low")
        state["approval"] = {
            "decision": "approved",
            "approval_fingerprint": workflow.approval_fingerprint_for(state),
            "based_on_revision": 0,
        }
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_state(state)


class CheckpointTests(WorkflowTestCase):
    def test_checkpoint_round_trip(self) -> None:
        state = workflow.new_state("task-1", "low")
        workflow.save_state(self.checkpoint, state)
        loaded = workflow.load_state(self.checkpoint, "task-1", "low")
        self.assertEqual(loaded, state)

    def test_checkpoint_integrity_detects_tampering(self) -> None:
        state = workflow.new_state("task-1", "low")
        workflow.save_state(self.checkpoint, state)
        envelope = json.loads(self.checkpoint.read_text(encoding="utf-8"))
        envelope["state"]["risk"] = "high"
        self.checkpoint.write_text(json.dumps(envelope), encoding="utf-8")
        with self.assertRaises(workflow.WorkflowError):
            workflow.load_state(self.checkpoint, "task-1", "low")

    def test_invalid_json_is_rejected(self) -> None:
        self.checkpoint.write_text("{", encoding="utf-8")
        with self.assertRaises(workflow.WorkflowError):
            workflow.load_state(self.checkpoint, "task-1", "low")

    def test_duplicate_checkpoint_key_is_rejected(self) -> None:
        self.checkpoint.write_text(
            '{"format":"first","format":"second","state":{},"sha256":"x"}',
            encoding="utf-8",
        )
        with self.assertRaises(workflow.WorkflowError):
            workflow.load_state(self.checkpoint, "task-1", "low")

    def test_checkpoint_array_is_rejected(self) -> None:
        self.checkpoint.write_text("[]", encoding="utf-8")
        with self.assertRaises(workflow.WorkflowError):
            workflow.load_state(self.checkpoint, "task-1", "low")

    def test_wrong_format_is_rejected(self) -> None:
        state = workflow.new_state("task-1", "low")
        envelope = {"format": "other", "state": state, "sha256": workflow.fingerprint(state)}
        self.checkpoint.write_text(json.dumps(envelope), encoding="utf-8")
        with self.assertRaises(workflow.WorkflowError):
            workflow.load_state(self.checkpoint, "task-1", "low")

    def test_task_mismatch_is_rejected(self) -> None:
        workflow.save_state(self.checkpoint, workflow.new_state("task-1", "low"))
        with self.assertRaises(workflow.WorkflowError):
            workflow.load_state(self.checkpoint, "task-2", "low")

    def test_risk_mismatch_is_rejected(self) -> None:
        workflow.save_state(self.checkpoint, workflow.new_state("task-1", "low"))
        with self.assertRaises(workflow.WorkflowError):
            workflow.load_state(self.checkpoint, "task-1", "high")

    def test_atomic_temporary_file_is_removed(self) -> None:
        workflow.save_state(self.checkpoint, workflow.new_state("task-1", "low"))
        self.assertFalse(self.checkpoint.with_name("state.json.tmp").exists())


class PatternTests(WorkflowTestCase):
    def test_low_risk_routes_to_checks(self) -> None:
        self.assertEqual(workflow.route(workflow.new_state("task-1", "low")), "parallel_checks")

    def test_high_risk_routes_to_approval(self) -> None:
        self.assertEqual(workflow.route(workflow.new_state("task-1", "high")), "approval")

    def test_parallel_checks_return_complete_join(self) -> None:
        state = workflow.new_state("task-1", "low")
        checks, attempts = workflow.run_parallel_checks(state)
        self.assertEqual(set(checks), {"input", "policy"})
        self.assertEqual(attempts, {"input": 1, "policy": 1})

    def test_transient_check_is_retried(self) -> None:
        state = workflow.new_state("task-1", "low")
        check = workflow.make_demo_check(True, False)
        checks, attempts = workflow.run_parallel_checks(state, check, max_attempts=2)
        self.assertTrue(checks["policy"]["ok"])
        self.assertEqual(attempts["policy"], 2)

    def test_permanent_check_is_not_retried(self) -> None:
        state = workflow.new_state("task-1", "low")
        check = workflow.make_demo_check(False, True)
        checks, attempts = workflow.run_parallel_checks(state, check, max_attempts=3)
        self.assertFalse(checks["policy"]["ok"])
        self.assertEqual(attempts["policy"], 1)

    def test_zero_retry_budget_is_rejected(self) -> None:
        with self.assertRaises(workflow.WorkflowError):
            workflow.run_parallel_checks(workflow.new_state("task-1", "low"), max_attempts=0)

    def test_boolean_attempt_count_is_rejected(self) -> None:
        state = workflow.new_state("task-1", "low")
        state["attempts"] = {"policy": True}
        with self.assertRaises(workflow.WorkflowError):
            workflow.run_parallel_checks(state)

    def test_evaluate_requires_all_branches(self) -> None:
        state = workflow.new_state("task-1", "low")
        state["checks"] = {
            "input": {"ok": True, "category": "ok", "evidence": "present"}
        }
        self.assertFalse(workflow.evaluate(state))

    def test_action_id_is_deterministic(self) -> None:
        state = workflow.new_state("task-1", "low")
        self.assertEqual(workflow.action_id_for(state), workflow.action_id_for(state))


class EndToEndTests(WorkflowTestCase):
    def test_low_risk_workflow_completes(self) -> None:
        state = self.run_workflow()
        self.assertEqual(state["stage"], "done")
        self.assertTrue(self.receipt.exists())

    def test_high_risk_workflow_pauses(self) -> None:
        state = self.run_workflow(risk="high")
        self.assertEqual(state["stage"], "awaiting_approval")
        self.assertEqual(set(state["checks"]), {"input", "policy"})
        self.assertTrue(all(result["ok"] for result in state["checks"].values()))
        self.assertLess(
            [event["name"] for event in state["events"]].index("parallel_checks:joined"),
            [event["name"] for event in state["events"]].index("approval:requested_after_checks"),
        )
        self.assertFalse(self.receipt.exists())

    def test_repeated_pause_is_stable(self) -> None:
        first = self.run_workflow(risk="high")
        second = self.run_workflow(risk="high")
        self.assertEqual(second, first)

    def test_high_risk_approval_completes(self) -> None:
        self.run_workflow(risk="high")
        state = self.run_workflow(risk="high", decision="approve")
        self.assertEqual(state["stage"], "done")
        self.assertEqual(state["approval"]["decision"], "approved")
        self.assertEqual(
            state["approval"]["approval_fingerprint"],
            workflow.approval_fingerprint_for(state),
        )

    def test_initial_decision_cannot_bypass_persisted_pause(self) -> None:
        with self.assertRaises(workflow.WorkflowError):
            self.run_workflow(risk="high", decision="approve")
        self.assertFalse(self.checkpoint.exists())
        self.assertFalse(self.receipt.exists())

    def test_rejection_is_terminal_without_receipt(self) -> None:
        self.run_workflow(risk="high")
        state = self.run_workflow(risk="high", decision="reject")
        self.assertEqual(state["stage"], "canceled")
        self.assertFalse(self.receipt.exists())

    def test_permanent_policy_failure_fails_closed(self) -> None:
        check = workflow.make_demo_check(False, True)
        state = self.run_workflow(check=check)
        self.assertEqual(state["stage"], "failed")
        self.assertFalse(self.receipt.exists())

    def test_high_risk_policy_failure_stops_before_approval(self) -> None:
        check = workflow.make_demo_check(False, True)
        state = self.run_workflow(risk="high", check=check)
        self.assertEqual(state["stage"], "failed")
        self.assertIsNone(state["approval"])
        self.assertNotIn("paused_for_approval", [event["name"] for event in state["events"]])
        self.assertFalse(self.receipt.exists())

    def test_transient_policy_failure_recovers(self) -> None:
        check = workflow.make_demo_check(True, False)
        state = self.run_workflow(check=check)
        self.assertEqual(state["stage"], "done")
        self.assertEqual(state["attempts"]["policy"], 2)

    def test_terminal_resume_does_not_duplicate_action(self) -> None:
        first = self.run_workflow()
        receipt_text = self.receipt.read_text(encoding="utf-8")
        second = self.run_workflow()
        self.assertEqual(second, first)
        self.assertEqual(self.receipt.read_text(encoding="utf-8"), receipt_text)

    def test_crash_after_commit_recovers_receipt(self) -> None:
        with self.assertRaises(workflow.SimulatedCrash):
            self.run_workflow(crash_after_commit=True)
        committed = self.receipt.read_text(encoding="utf-8")
        state = self.run_workflow()
        self.assertEqual(state["stage"], "done")
        self.assertEqual(self.receipt.read_text(encoding="utf-8"), committed)
        self.assertEqual(state["events"][-1]["name"], "action:recovered_existing_receipt")

    def test_existing_receipt_for_other_task_is_rejected(self) -> None:
        self.receipt.write_text("{}", encoding="utf-8")
        with self.assertRaises(workflow.WorkflowError):
            self.run_workflow()

    def test_duplicate_receipt_key_is_rejected(self) -> None:
        self.receipt.write_text(
            '{"action_id":"first","action_id":"second"}',
            encoding="utf-8",
        )
        with self.assertRaises(workflow.WorkflowError):
            self.run_workflow()

    def test_invalid_decision_is_rejected(self) -> None:
        with self.assertRaises(workflow.WorkflowError):
            self.run_workflow(decision="maybe")

    def test_low_risk_approval_argument_is_rejected(self) -> None:
        with self.assertRaises(workflow.WorkflowError):
            self.run_workflow(decision="approve")


class CliTests(WorkflowTestCase):
    def call_main(self, *extra: str) -> tuple[int, dict[str, object]]:
        arguments = [
            "--checkpoint",
            str(self.checkpoint),
            "--receipt",
            str(self.receipt),
            "--task-id",
            "case-001",
            *extra,
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = workflow.main(arguments)
        return code, json.loads(output.getvalue())

    def test_cli_low_risk_exit_code(self) -> None:
        code, payload = self.call_main("--risk", "low")
        self.assertEqual(code, 0)
        self.assertEqual(payload["stage"], "done")

    def test_cli_waiting_exit_code(self) -> None:
        code, payload = self.call_main("--risk", "high")
        self.assertEqual(code, 3)
        self.assertEqual(payload["stage"], "awaiting_approval")

    def test_cli_initial_approval_is_rejected(self) -> None:
        code, payload = self.call_main("--risk", "high", "--decision", "approve")
        self.assertEqual(code, 2)
        self.assertEqual(payload["stage"], "error")

    def test_cli_rejection_exit_code(self) -> None:
        self.call_main("--risk", "high")
        code, payload = self.call_main("--risk", "high", "--decision", "reject")
        self.assertEqual(code, 4)
        self.assertEqual(payload["stage"], "canceled")

    def test_cli_permanent_failure_exit_code(self) -> None:
        code, payload = self.call_main(
            "--risk",
            "low",
            "--simulate-permanent-policy-failure",
        )
        self.assertEqual(code, 1)
        self.assertEqual(payload["stage"], "failed")

    def test_cli_simulated_crash_exit_code(self) -> None:
        code, payload = self.call_main("--risk", "low", "--crash-after-commit")
        self.assertEqual(code, 5)
        self.assertEqual(payload["stage"], "simulated_crash")


if __name__ == "__main__":
    unittest.main()
