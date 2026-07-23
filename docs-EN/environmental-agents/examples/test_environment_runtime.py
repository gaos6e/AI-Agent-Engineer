"""Regression tests for the deterministic environment-agent teaching runtime."""

from __future__ import annotations

import copy
import hashlib
import hmac
import secrets
import unittest
from pathlib import Path

from environment_runtime import (
    Action,
    ApprovalError,
    CheckpointError,
    CheckpointGenerationStore,
    ContractError,
    EnvironmentRuntime,
    IdempotencyConflict,
    PermissionDenied,
    ReviewRequired,
    Sandbox,
    Scenario,
    SimulatedCrash,
    StaleObservation,
    TerminalStateError,
    VerificationError,
    action,
    canonical_json,
    load_scenario,
    run_demo,
    sha256_json,
    signed_approval,
    signed_reconciliation,
    strict_loads,
)


FIXTURE = Path(__file__).with_name("environment_fixture.json")
APPROVER_ID = "reviewer-1"
APPROVER_KEY = b"approval-authority-key-material-01"


class FakeClock:
    def __init__(self, now_ms: int) -> None:
        self.value = now_ms

    def __call__(self) -> int:
        return self.value


def scenario_with(**changes: object) -> Scenario:
    value = load_scenario(FIXTURE).to_dict()
    value.update(changes)
    return Scenario.from_dict(value)


def current_action(
    runtime: EnvironmentRuntime,
    action_id: str,
    kind: str,
    arguments: dict[str, object],
    idempotency_key: str | None = None,
    **options: object,
) -> dict[str, object]:
    return action(
        action_id,
        kind,
        arguments,
        idempotency_key,
        environment_version=runtime.sandbox.version,
        **options,
    )


def approved_action(
    runtime: EnvironmentRuntime,
    action_id: str = "write-approved",
    *,
    content: str = "print('ready')\n",
    expires_at_proposal: int = 10,
) -> dict[str, object]:
    raw = current_action(
        runtime,
        action_id,
        "write_file",
        {"path": "app.py", "content": content},
        f"key-{action_id}",
    )
    runtime.register_approval(
        approval_for(runtime, raw, expires_at_proposal=expires_at_proposal)
    )
    return raw


def approval_for(
    runtime: EnvironmentRuntime,
    raw_action: dict[str, object],
    *,
    approver_id: str = APPROVER_ID,
    signing_key: bytes = APPROVER_KEY,
    task_id: str | None = None,
    run_id: str | None = None,
    policy_version: str | None = None,
    intent_digest: str | None = None,
    environment_version: int | None = None,
    expires_at_proposal: int = 10,
    expires_at_unix_ms: int | None = None,
    nonce: str = "approval-nonce-1",
) -> dict[str, object]:
    return signed_approval(
        approver_id=approver_id,
        task_id=task_id or runtime.scenario.task_id,
        run_id=run_id or runtime.state.run_id,
        policy_version=policy_version or runtime.scenario.policy_version,
        action_id=str(raw_action["action_id"]),
        idempotency_key=(
            None
            if raw_action["idempotency_key"] is None
            else str(raw_action["idempotency_key"])
        ),
        intent_digest=intent_digest or Action.from_dict(raw_action).intent_digest(),
        environment_version=(
            runtime.sandbox.version
            if environment_version is None
            else environment_version
        ),
        environment_instance_id=runtime.sandbox.instance_id,
        state_fingerprint=runtime.sandbox.state_fingerprint(),
        environment_generation=runtime.sandbox.generation,
        expires_at_proposal=expires_at_proposal,
        expires_at_unix_ms=(
            runtime.now_ms() + 60_000
            if expires_at_unix_ms is None
            else expires_at_unix_ms
        ),
        nonce=nonce,
        signing_key=signing_key,
    )


def reconciliation_for(
    runtime: EnvironmentRuntime,
    action_id: str,
    *,
    decision: str,
    reviewer_id: str = APPROVER_ID,
    signing_key: bytes = APPROVER_KEY,
    nonce: str = "review-nonce-1",
) -> dict[str, object]:
    case = runtime.state.review_cases[action_id]
    pending = case["pending_intent"]
    pending_action = Action.from_dict(pending["action"])
    idempotency_key = pending_action.idempotency_key
    if idempotency_key is None:
        raise AssertionError("test fixture expected a write idempotency key")
    return signed_reconciliation(
        reviewer_id=reviewer_id,
        task_id=runtime.scenario.task_id,
        run_id=runtime.state.run_id,
        policy_version=runtime.scenario.policy_version,
        action_id=action_id,
        idempotency_key=idempotency_key,
        pending_intent_digest=pending["intent_digest"],
        observed_intent_digest=case["observed_receipt"]["intent_digest"],
        observed_receipt_fingerprint=case["observed_receipt_fingerprint"],
        environment_version=runtime.sandbox.version,
        decision=decision,
        nonce=nonce,
        signing_key=signing_key,
    )


def forged_receipt(
    *,
    intent_digest: str = "0" * 64,
    content_sha256: str = "0" * 64,
) -> dict[str, object]:
    return {
        "adapter_namespace": "memory-file-adapter/v1",
        "receipt_version": 1,
        "receipt_id": sha256_json(
            {
                "fixture": "conflicting-receipt",
                "intent_digest": intent_digest,
                "content_sha256": content_sha256,
            }
        ),
        "intent_digest": intent_digest,
        "result": {
            "path": "app.py",
            "version": 1,
            "content_sha256": content_sha256,
        },
    }


def repaired_runtime(**scenario_changes: object) -> EnvironmentRuntime:
    runtime = EnvironmentRuntime(scenario_with(**scenario_changes))
    runtime.apply(
        current_action(
            runtime,
            "write-repair",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "repair-app",
        )
    )
    return runtime


def resign(envelope: dict[str, object], signing_key: bytes) -> str:
    payload = envelope["payload"]
    envelope["checksum_sha256"] = sha256_json(payload)
    envelope["hmac_sha256"] = hmac.new(
        signing_key,
        canonical_json(payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return canonical_json(envelope)


class FixtureContractTests(unittest.TestCase):
    def test_fixture_loads_versioned_policy_and_allowlists(self) -> None:
        scenario = load_scenario(FIXTURE)
        self.assertEqual(scenario.task_id, "repair-greeting")
        self.assertEqual(scenario.task_version, "2026-07-18-v1")
        self.assertEqual(scenario.policy_version, "environment-policy-v1")
        self.assertEqual(scenario.allowed_test_targets, frozenset({"unit"}))
        self.assertGreater(scenario.max_proposals, scenario.max_steps)

    def test_duplicate_json_key_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            strict_loads('{"a": 1, "a": 2}')

    def test_non_finite_number_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            strict_loads('{"value": NaN}')

    def test_unknown_fixture_field_is_rejected(self) -> None:
        raw = load_scenario(FIXTURE).to_dict()
        raw["surprise"] = True
        with self.assertRaises(ContractError):
            Scenario.from_dict(raw)

    def test_boolean_is_not_an_integer_budget(self) -> None:
        with self.assertRaises(ContractError):
            scenario_with(max_steps=True)

    def test_traversal_path_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            scenario_with(allowed_paths=["../app.py"])

    def test_noncanonical_path_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            scenario_with(allowed_paths=["folder//app.py"])

    def test_unknown_permission_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            scenario_with(permissions=["workspace.read", "host.admin"])

    def test_proposal_budget_must_cover_step_budget(self) -> None:
        with self.assertRaises(ContractError):
            scenario_with(max_steps=3, max_proposals=2)

    def test_duplicate_test_target_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            scenario_with(allowed_test_targets=["unit", "unit"])

    def test_expected_file_must_be_inside_allowed_paths(self) -> None:
        with self.assertRaises(ContractError):
            scenario_with(allowed_paths=["other.py"])


class ActionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = EnvironmentRuntime(load_scenario(FIXTURE))

    def test_unknown_action_is_rejected_and_traced(self) -> None:
        with self.assertRaises(ContractError):
            self.runtime.propose(action("bad", "teleport", {}))
        self.assertEqual(self.runtime.state.proposal_count, 1)
        self.assertEqual(self.runtime.state.events[-1]["outcome"], "contract_rejected")

    def test_unknown_action_field_is_rejected(self) -> None:
        raw = current_action(self.runtime, "read", "read_file", {"path": "app.py"})
        raw["unexpected"] = 1
        with self.assertRaises(ContractError):
            self.runtime.propose(raw)

    def test_missing_argument_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            self.runtime.propose(current_action(self.runtime, "read", "read_file", {}))

    def test_extra_argument_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            self.runtime.propose(
                current_action(
                    self.runtime,
                    "read",
                    "read_file",
                    {"path": "app.py", "mode": "unsafe"},
                )
            )

    def test_mutation_requires_idempotency_key(self) -> None:
        with self.assertRaises(ContractError):
            self.runtime.propose(
                current_action(
                    self.runtime,
                    "write",
                    "write_file",
                    {"path": "app.py", "content": "x"},
                )
            )

    def test_nonmutation_rejects_idempotency_key(self) -> None:
        with self.assertRaises(ContractError):
            self.runtime.propose(
                current_action(
                    self.runtime,
                    "read",
                    "read_file",
                    {"path": "app.py"},
                    "not-needed",
                )
            )

    def test_path_outside_scope_is_denied_without_side_effect(self) -> None:
        with self.assertRaises(PermissionDenied):
            self.runtime.apply(
                current_action(
                    self.runtime,
                    "write",
                    "write_file",
                    {"path": "secret.py", "content": "x"},
                    "outside",
                )
            )
        self.assertEqual(self.runtime.sandbox.write_count, 0)
        self.assertEqual(self.runtime.state.events[-1]["outcome"], "permission_denied")

    def test_stale_observation_is_rejected_and_traced(self) -> None:
        raw = action(
            "stale",
            "read_file",
            {"path": "app.py"},
            environment_version=1,
        )
        with self.assertRaises(StaleObservation):
            self.runtime.apply(raw)
        self.assertEqual(self.runtime.state.proposal_count, 1)
        self.assertEqual(self.runtime.state.step_count, 0)
        self.assertEqual(self.runtime.state.events[-1]["outcome"], "stale_observation")

    def test_environment_precondition_is_required(self) -> None:
        raw = current_action(self.runtime, "read", "read_file", {"path": "app.py"})
        raw["preconditions"] = []
        with self.assertRaises(ContractError):
            self.runtime.propose(raw)

    def test_declared_risk_must_match_action_kind(self) -> None:
        raw = current_action(self.runtime, "read", "read_file", {"path": "app.py"})
        raw["risk"] = "reversible_write"
        with self.assertRaises(ContractError):
            self.runtime.propose(raw)

    def test_expired_proposal_deadline_is_rejected(self) -> None:
        self.runtime.apply(
            current_action(self.runtime, "read-1", "read_file", {"path": "app.py"})
        )
        with self.assertRaises(ContractError):
            self.runtime.propose(
                current_action(
                    self.runtime,
                    "read-2",
                    "read_file",
                    {"path": "app.py"},
                    deadline_proposal=1,
                )
            )
        self.assertEqual(self.runtime.state.proposal_count, 2)

    def test_action_id_must_be_unique(self) -> None:
        self.runtime.apply(
            current_action(self.runtime, "same", "read_file", {"path": "app.py"})
        )
        with self.assertRaises(ContractError):
            self.runtime.propose(
                current_action(self.runtime, "same", "read_file", {"path": "app.py"})
            )

    def test_pending_intent_must_be_resolved_before_new_proposal(self) -> None:
        proposal = self.runtime.propose(
            current_action(
                self.runtime,
                "pending",
                "write_file",
                {"path": "app.py", "content": "print('ready')\n"},
                "pending-key",
            )
        )
        self.assertEqual(proposal.outcome, "pending")
        with self.assertRaises(ContractError):
            self.runtime.propose(
                current_action(self.runtime, "read", "read_file", {"path": "app.py"})
            )
        self.assertEqual(self.runtime.state.proposal_count, 2)
        self.assertEqual(self.runtime.state.events[-1]["outcome"], "contract_rejected")


class PermissionTests(unittest.TestCase):
    def test_write_permission_is_enforced(self) -> None:
        runtime = EnvironmentRuntime(
            scenario_with(permissions=["workspace.read", "tests.run"])
        )
        with self.assertRaises(PermissionDenied):
            runtime.apply(
                current_action(
                    runtime,
                    "write",
                    "write_file",
                    {"path": "app.py", "content": "x"},
                    "write-key",
                )
            )
        self.assertEqual(runtime.sandbox.write_count, 0)

    def test_read_permission_is_enforced(self) -> None:
        runtime = EnvironmentRuntime(
            scenario_with(permissions=["workspace.write", "tests.run"])
        )
        with self.assertRaises(PermissionDenied):
            runtime.apply(
                current_action(runtime, "read", "read_file", {"path": "app.py"})
            )

    def test_test_permission_is_enforced(self) -> None:
        runtime = EnvironmentRuntime(
            scenario_with(permissions=["workspace.read", "workspace.write"])
        )
        with self.assertRaises(PermissionDenied):
            runtime.apply(
                current_action(runtime, "test", "run_tests", {"target": "unit"})
            )

    def test_test_target_must_be_allowlisted(self) -> None:
        runtime = EnvironmentRuntime(load_scenario(FIXTURE))
        with self.assertRaises(PermissionDenied):
            runtime.apply(
                current_action(runtime, "test", "run_tests", {"target": "host"})
            )
        self.assertEqual(runtime.state.events[-1]["outcome"], "permission_denied")
        self.assertEqual(runtime.state.step_count, 0)

    def test_allowlisted_test_target_is_passed_to_adapter(self) -> None:
        runtime = EnvironmentRuntime(load_scenario(FIXTURE))
        result = runtime.apply(
            current_action(runtime, "test", "run_tests", {"target": "unit"})
        )
        self.assertEqual(result["target"], "unit")
        self.assertFalse(result["passed"])


class ApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = EnvironmentRuntime(
            scenario_with(approval_required_actions=["write_file"]),
            trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
        )

    def approved_pending_runtime(self) -> tuple[EnvironmentRuntime, str]:
        runtime = EnvironmentRuntime(
            scenario_with(approval_required_actions=["write_file"]),
            trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
        )
        raw = approved_action(runtime, action_id="write-approved-pending")
        proposal = runtime.propose(raw)
        self.assertEqual(proposal.outcome, "pending")
        return runtime, str(raw["action_id"])

    def test_required_approval_cannot_be_omitted(self) -> None:
        raw = current_action(
            self.runtime,
            "write",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "approval-key",
        )
        with self.assertRaises(ApprovalError):
            self.runtime.apply(raw)
        self.assertEqual(self.runtime.state.events[-1]["outcome"], "approval_rejected")

    def test_model_cannot_embed_a_self_issued_approval(self) -> None:
        raw = current_action(
            self.runtime,
            "self-approved",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "self-key",
        )
        raw["approval"] = {
            "approver_id": "model-claims-human",
            "intent_digest": Action.from_dict(raw).intent_digest()
            if "approval" not in raw
            else "0" * 64,
        }
        with self.assertRaises(ContractError):
            self.runtime.apply(raw)
        self.assertEqual(self.runtime.sandbox.write_count, 0)

    def test_matching_unexpired_approval_allows_write(self) -> None:
        result = self.runtime.apply(approved_action(self.runtime))
        self.assertEqual(result["version"], 1)
        self.assertEqual(self.runtime.sandbox.write_count, 1)

    def test_approval_is_bound_to_intent_digest(self) -> None:
        raw = current_action(
            self.runtime,
            "write-approved",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "approval-key",
        )
        self.runtime.register_approval(approval_for(self.runtime, raw))
        raw["arguments"]["content"] = "model changed the approved content"
        with self.assertRaises(ApprovalError):
            self.runtime.apply(raw)
        self.assertEqual(self.runtime.sandbox.write_count, 0)

    def test_approval_is_bound_to_environment_version(self) -> None:
        raw = current_action(
            self.runtime,
            "write-approved",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "approval-key",
        )
        self.runtime.register_approval(approval_for(self.runtime, raw))
        self.runtime.sandbox.write_file(
            "app.py", "external change", "external-key", "1" * 64
        )
        raw["environment_version"] = 1
        with self.assertRaises(ApprovalError):
            self.runtime.apply(raw)
        self.assertEqual(self.runtime.sandbox.write_count, 1)

    def test_expired_approval_is_rejected_after_reobservation(self) -> None:
        raw = current_action(
            self.runtime,
            "write-late",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "approval-key",
        )
        self.runtime.register_approval(
            approval_for(self.runtime, raw, expires_at_proposal=1)
        )
        self.runtime.apply(
            current_action(self.runtime, "read", "read_file", {"path": "app.py"})
        )
        with self.assertRaises(ApprovalError):
            self.runtime.apply(raw)
        self.assertEqual(self.runtime.state.proposal_count, 2)
        self.assertEqual(self.runtime.state.events[-1]["outcome"], "approval_rejected")

    def test_unknown_approval_signer_is_rejected(self) -> None:
        raw = current_action(
            self.runtime,
            "write",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "approval-key",
        )
        with self.assertRaises(ApprovalError):
            self.runtime.register_approval(
                approval_for(
                    self.runtime,
                    raw,
                    approver_id="unknown-reviewer",
                    signing_key=b"unknown-reviewer-key-material-01",
                )
            )

    def test_cross_run_approval_replay_is_rejected(self) -> None:
        raw = current_action(
            self.runtime,
            "write",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "approval-key",
        )
        record = approval_for(self.runtime, raw)
        other = EnvironmentRuntime(
            self.runtime.scenario,
            run_id="another-run",
            trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
        )
        with self.assertRaises(ApprovalError):
            other.register_approval(record)

    def test_cross_task_approval_replay_is_rejected(self) -> None:
        raw = current_action(
            self.runtime,
            "write",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "approval-key",
        )
        record = approval_for(self.runtime, raw)
        other = EnvironmentRuntime(
            scenario_with(
                task_id="different-task",
                approval_required_actions=["write_file"],
            ),
            trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
        )
        with self.assertRaises(ApprovalError):
            other.register_approval(record)

    def test_cross_policy_approval_replay_is_rejected(self) -> None:
        raw = current_action(
            self.runtime,
            "write",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "approval-key",
        )
        with self.assertRaises(ApprovalError):
            self.runtime.register_approval(
                approval_for(self.runtime, raw, policy_version="other-policy")
            )

    def test_one_time_approval_cannot_authorize_a_second_action(self) -> None:
        runtime = EnvironmentRuntime(
            scenario_with(approval_required_actions=["read_file"]),
            trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
        )
        first = current_action(runtime, "read-1", "read_file", {"path": "app.py"})
        runtime.register_approval(approval_for(runtime, first))
        runtime.apply(first)
        with self.assertRaises(ApprovalError):
            runtime.apply(
                current_action(runtime, "read-2", "read_file", {"path": "app.py"})
            )

    def test_approval_does_not_cross_idempotency_keys(self) -> None:
        approved = current_action(
            self.runtime,
            "write-1",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "approved-key",
        )
        self.runtime.register_approval(approval_for(self.runtime, approved))
        with self.assertRaises(ApprovalError):
            self.runtime.apply(
                current_action(
                    self.runtime,
                    "write-1",
                    "write_file",
                    {"path": "app.py", "content": "print('ready')\n"},
                    "different-key",
                )
            )

    def test_approval_does_not_cross_action_ids_before_consumption(self) -> None:
        approved = current_action(
            self.runtime,
            "write-1",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "shared-key",
        )
        self.runtime.register_approval(approval_for(self.runtime, approved))
        with self.assertRaises(ApprovalError):
            self.runtime.apply(
                current_action(
                    self.runtime,
                    "write-2",
                    "write_file",
                    {"path": "app.py", "content": "print('ready')\n"},
                    "shared-key",
                )
            )
        self.assertEqual(self.runtime.sandbox.write_count, 0)

    def test_consumed_approval_nonce_cannot_be_registered_again(self) -> None:
        raw = current_action(
            self.runtime,
            "write-once",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "once-key",
        )
        record = approval_for(self.runtime, raw)
        self.runtime.register_approval(record)
        self.runtime.apply(raw)
        with self.assertRaises(ApprovalError):
            self.runtime.register_approval(record)

    def test_tampered_approval_signature_is_rejected(self) -> None:
        raw = current_action(
            self.runtime,
            "write-tampered",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "tampered-key",
        )
        record = approval_for(self.runtime, raw)
        record["payload"]["intent_digest"] = "0" * 64
        with self.assertRaises(ApprovalError):
            self.runtime.register_approval(record)

    def test_registered_approval_survives_authenticated_checkpoint(self) -> None:
        checkpoint_key = secrets.token_bytes(32)
        raw = current_action(
            self.runtime,
            "write-restored",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "restored-key",
        )
        self.runtime.register_approval(approval_for(self.runtime, raw))
        restored = EnvironmentRuntime.restore(
            self.runtime.checkpoint(checkpoint_key),
            self.runtime.scenario,
            checkpoint_key,
            trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
            generation_store=self.runtime.generation_store,
        )
        result = restored.apply(raw)
        self.assertEqual(result["version"], 1)
        self.assertIn("approval-nonce-1", restored.state.consumed_approval_nonces)

    def test_consumed_nonce_remains_unusable_after_restore(self) -> None:
        checkpoint_key = secrets.token_bytes(32)
        raw = current_action(
            self.runtime,
            "write-before-checkpoint",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "before-checkpoint-key",
        )
        record = approval_for(self.runtime, raw)
        self.runtime.register_approval(record)
        self.runtime.apply(raw)
        restored = EnvironmentRuntime.restore(
            self.runtime.checkpoint(checkpoint_key),
            self.runtime.scenario,
            checkpoint_key,
            trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
            generation_store=self.runtime.generation_store,
        )
        with self.assertRaises(ApprovalError):
            restored.register_approval(record)

    def test_approved_pending_checkpoint_keeps_full_signed_evidence(self) -> None:
        checkpoint_key = secrets.token_bytes(32)
        raw = current_action(
            self.runtime,
            "write-pending-evidence",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "pending-evidence-key",
        )
        record = approval_for(self.runtime, raw)
        self.runtime.register_approval(record)
        proposal = self.runtime.propose(raw)
        self.assertEqual(proposal.outcome, "pending")
        envelope = strict_loads(self.runtime.checkpoint(checkpoint_key))
        pending = envelope["payload"]["state"]["pending_intents"][raw["action_id"]]
        self.assertEqual(pending["approval_evidence"], record)
        self.assertEqual(
            pending["environment_instance_id"], self.runtime.sandbox.instance_id
        )
        self.assertEqual(
            pending["state_fingerprint"], self.runtime.sandbox.state_fingerprint()
        )

    def test_signed_approval_binds_environment_identity_and_state(self) -> None:
        raw = current_action(
            self.runtime,
            "write-environment-bound",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "environment-bound-key",
        )
        record = approval_for(self.runtime, raw)
        payload = record["payload"]
        self.assertEqual(
            payload["environment_instance_id"], self.runtime.sandbox.instance_id
        )
        self.assertEqual(
            payload["state_fingerprint"], self.runtime.sandbox.state_fingerprint()
        )
        self.assertEqual(
            payload["environment_generation"], self.runtime.sandbox.generation
        )
        self.assertGreater(payload["expires_at_unix_ms"], self.runtime.now_ms())

    def test_wall_clock_expiry_is_exclusive_even_without_new_proposals(self) -> None:
        clock = FakeClock(1_000)
        runtime = EnvironmentRuntime(
            scenario_with(approval_required_actions=["write_file"]),
            trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
            clock=clock,
        )
        raw = current_action(
            runtime,
            "write-wall-clock-expired",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "wall-clock-key",
        )
        runtime.register_approval(
            approval_for(runtime, raw, expires_at_unix_ms=1_001)
        )
        clock.value = 1_001
        with self.assertRaises(ApprovalError):
            runtime.apply(raw)
        self.assertEqual(runtime.sandbox.write_count, 0)

    def test_expired_pending_restores_frozen_and_accepts_fresh_approval(self) -> None:
        clock = FakeClock(1_000)
        runtime = EnvironmentRuntime(
            scenario_with(approval_required_actions=["write_file"]),
            trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
            clock=clock,
        )
        raw = current_action(
            runtime,
            "write-wall-clock-restore",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "wall-clock-restore-key",
        )
        expired_evidence = approval_for(
            runtime,
            raw,
            expires_at_unix_ms=1_001,
            nonce="approval-expiring",
        )
        runtime.register_approval(expired_evidence)
        self.assertEqual(runtime.propose(raw).outcome, "pending")
        checkpoint_key = secrets.token_bytes(32)
        runtime.checkpoint(checkpoint_key)
        clock.value = 1_001
        checkpoint = runtime.checkpoint(checkpoint_key)
        restored = EnvironmentRuntime.restore(
            checkpoint,
            runtime.scenario,
            checkpoint_key,
            trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
            generation_store=runtime.generation_store,
            clock=clock,
        )
        with self.assertRaises(ApprovalError):
            restored.execute_pending(str(raw["action_id"]))
        self.assertIn(raw["action_id"], restored.state.pending_intents)
        self.assertEqual(restored.sandbox.write_count, 0)

        fresh_evidence = approval_for(
            restored,
            raw,
            expires_at_unix_ms=2_000,
            nonce="approval-refreshed",
        )
        restored.refresh_pending_approval(str(raw["action_id"]), fresh_evidence)
        self.assertEqual(
            restored.state.events[-1]["detail"]["superseded_approval_evidence"],
            expired_evidence,
        )
        restored.execute_pending(str(raw["action_id"]))
        self.assertEqual(restored.sandbox.write_count, 1)
        self.assertFalse(restored.state.pending_intents)

    def test_approved_pending_restore_requires_approval_trust_root(self) -> None:
        runtime, _ = self.approved_pending_runtime()
        checkpoint_key = secrets.token_bytes(32)
        checkpoint = runtime.checkpoint(checkpoint_key)
        with self.assertRaises(CheckpointError):
            EnvironmentRuntime.restore(
                checkpoint,
                runtime.scenario,
                checkpoint_key,
                generation_store=runtime.generation_store,
            )

    def test_resigned_pending_approval_tampering_is_rejected(self) -> None:
        runtime, action_id = self.approved_pending_runtime()
        checkpoint_key = secrets.token_bytes(32)
        envelope = strict_loads(runtime.checkpoint(checkpoint_key))
        pending = envelope["payload"]["state"]["pending_intents"][action_id]
        pending["approval_evidence"]["payload"]["state_fingerprint"] = "0" * 64
        with self.assertRaises(CheckpointError):
            EnvironmentRuntime.restore(
                resign(envelope, checkpoint_key),
                runtime.scenario,
                checkpoint_key,
                trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
                generation_store=runtime.generation_store,
            )

    def test_same_version_different_state_cannot_receive_approved_pending(self) -> None:
        runtime, _ = self.approved_pending_runtime()
        checkpoint_key = secrets.token_bytes(32)
        checkpoint = runtime.checkpoint(checkpoint_key)
        different_state = Sandbox(
            files={"app.py": "different state\n"},
            expected_files=dict(runtime.scenario.expected_files),
            instance_id=runtime.sandbox.instance_id,
        )
        with self.assertRaises(CheckpointError):
            EnvironmentRuntime.restore(
                checkpoint,
                runtime.scenario,
                checkpoint_key,
                external_sandbox=different_state,
                trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
                generation_store=runtime.generation_store,
            )

    def test_same_state_different_instance_cannot_receive_approved_pending(self) -> None:
        runtime, _ = self.approved_pending_runtime()
        checkpoint_key = secrets.token_bytes(32)
        checkpoint = runtime.checkpoint(checkpoint_key)
        different_instance = Sandbox(
            files=dict(runtime.sandbox.files),
            expected_files=dict(runtime.scenario.expected_files),
        )
        self.assertNotEqual(different_instance.instance_id, runtime.sandbox.instance_id)
        with self.assertRaises(CheckpointError):
            EnvironmentRuntime.restore(
                checkpoint,
                runtime.scenario,
                checkpoint_key,
                external_sandbox=different_instance,
                trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
                generation_store=runtime.generation_store,
            )

    def test_approved_pending_rechecks_state_fingerprint_before_execution(self) -> None:
        runtime, action_id = self.approved_pending_runtime()
        runtime.sandbox.files["app.py"] = "same version but changed state\n"
        with self.assertRaises(StaleObservation):
            runtime.execute_pending(action_id)
        self.assertEqual(runtime.sandbox.write_count, 0)
        self.assertNotIn(action_id, runtime.state.pending_intents)


class IdempotencyTests(unittest.TestCase):
    def test_same_intent_is_replayed_without_second_write(self) -> None:
        runtime = EnvironmentRuntime(load_scenario(FIXTURE))
        first = current_action(
            runtime,
            "write-1",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "same-key",
        )
        runtime.apply(first)
        second = current_action(
            runtime,
            "write-2",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "same-key",
        )
        result = runtime.apply(second)
        self.assertTrue(result["replayed"])
        self.assertEqual(runtime.sandbox.write_count, 1)
        self.assertEqual(runtime.state.step_count, 1)
        self.assertEqual(runtime.state.events[-1]["outcome"], "replayed")

    def test_same_key_with_different_intent_conflicts_and_is_traced(self) -> None:
        runtime = EnvironmentRuntime(load_scenario(FIXTURE))
        runtime.apply(
            current_action(
                runtime,
                "write-1",
                "write_file",
                {"path": "app.py", "content": "first"},
                "same-key",
            )
        )
        with self.assertRaises(IdempotencyConflict):
            runtime.apply(
                current_action(
                    runtime,
                    "write-2",
                    "write_file",
                    {"path": "app.py", "content": "second"},
                    "same-key",
                )
            )
        self.assertEqual(runtime.sandbox.write_count, 1)
        self.assertEqual(runtime.state.proposal_count, 2)
        self.assertEqual(runtime.state.events[-1]["outcome"], "idempotency_conflict")

    def test_adapter_receipt_alone_can_prove_replay(self) -> None:
        runtime = EnvironmentRuntime(load_scenario(FIXTURE))
        runtime.apply(
            current_action(
                runtime,
                "write-1",
                "write_file",
                {"path": "app.py", "content": "print('ready')\n"},
                "adapter-key",
            )
        )
        runtime.state.idempotency_receipts.clear()
        result = runtime.apply(
            current_action(
                runtime,
                "write-2",
                "write_file",
                {"path": "app.py", "content": "print('ready')\n"},
                "adapter-key",
            )
        )
        self.assertTrue(result["replayed"])
        self.assertEqual(runtime.sandbox.write_count, 1)

    def test_runtime_cache_cannot_mask_deleted_adapter_receipt(self) -> None:
        runtime = repaired_runtime()
        runtime.sandbox.adapter_receipts.pop("repair-app")
        with self.assertRaises(IdempotencyConflict):
            runtime.apply(
                current_action(
                    runtime,
                    "write-after-receipt-deletion",
                    "write_file",
                    {"path": "app.py", "content": "print('ready')\n"},
                    "repair-app",
                )
            )
        self.assertEqual(runtime.sandbox.write_count, 1)
        self.assertEqual(runtime.state.events[-1]["outcome"], "idempotency_conflict")

    def test_runtime_cache_cannot_mask_drifted_adapter_receipt(self) -> None:
        runtime = repaired_runtime()
        runtime.sandbox.adapter_receipts["repair-app"]["receipt_id"] = "1" * 64
        with self.assertRaises(IdempotencyConflict):
            runtime.apply(
                current_action(
                    runtime,
                    "write-after-receipt-drift",
                    "write_file",
                    {"path": "app.py", "content": "print('ready')\n"},
                    "repair-app",
                )
            )
        self.assertEqual(runtime.sandbox.write_count, 1)

    def test_drifted_runtime_cache_cannot_override_adapter_receipt(self) -> None:
        runtime = repaired_runtime()
        runtime.state.idempotency_receipts["repair-app"]["receipt_id"] = "1" * 64
        with self.assertRaises(IdempotencyConflict):
            runtime.apply(
                current_action(
                    runtime,
                    "write-after-cache-drift",
                    "write_file",
                    {"path": "app.py", "content": "print('ready')\n"},
                    "repair-app",
                )
            )
        self.assertEqual(runtime.sandbox.write_count, 1)

    def test_replay_consumes_proposal_budget(self) -> None:
        runtime = EnvironmentRuntime(
            scenario_with(max_steps=1, max_proposals=2)
        )
        runtime.apply(
            current_action(
                runtime,
                "write-1",
                "write_file",
                {"path": "app.py", "content": "print('ready')\n"},
                "budget-key",
            )
        )
        runtime.apply(
            current_action(
                runtime,
                "write-2",
                "write_file",
                {"path": "app.py", "content": "print('ready')\n"},
                "budget-key",
            )
        )
        self.assertEqual(runtime.state.proposal_count, 2)
        self.assertEqual(runtime.state.phase, "failed")
        self.assertEqual(runtime.state.terminal_reason, "proposal_budget_exhausted")

    def test_policy_required_approval_gates_idempotent_replay(self) -> None:
        runtime = EnvironmentRuntime(
            scenario_with(approval_required_actions=["write_file"]),
            trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
        )
        first = current_action(
            runtime,
            "approved-original",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "approved-replay-key",
        )
        runtime.register_approval(approval_for(runtime, first, nonce="approval-original"))
        runtime.apply(first)
        replay = current_action(
            runtime,
            "approved-replay",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "approved-replay-key",
        )
        with self.assertRaises(ApprovalError):
            runtime.apply(replay)
        self.assertEqual(runtime.sandbox.write_count, 1)
        approved_replay = current_action(
            runtime,
            "approved-replay-after-denial",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "approved-replay-key",
        )
        runtime.register_approval(
            approval_for(runtime, approved_replay, nonce="approval-replay")
        )
        result = runtime.apply(approved_replay)
        self.assertTrue(result["replayed"])
        self.assertEqual(runtime.sandbox.write_count, 1)


class BudgetAndTraceTests(unittest.TestCase):
    def test_schema_rejection_consumes_proposal_budget_and_enters_trace(self) -> None:
        runtime = EnvironmentRuntime(load_scenario(FIXTURE))
        raw = current_action(runtime, "bad", "read_file", {"path": "app.py"})
        raw.pop("risk")
        with self.assertRaises(ContractError):
            runtime.propose(raw)
        self.assertEqual(runtime.state.proposal_count, 1)
        self.assertEqual(runtime.state.events[-1]["outcome"], "contract_rejected")

    def test_permission_rejection_consumes_proposal_budget(self) -> None:
        runtime = EnvironmentRuntime(scenario_with(permissions=[]))
        with self.assertRaises(PermissionDenied):
            runtime.propose(
                current_action(runtime, "read", "read_file", {"path": "app.py"})
            )
        self.assertEqual(runtime.state.proposal_count, 1)
        self.assertEqual(runtime.state.events[-1]["outcome"], "permission_denied")

    def test_proposal_budget_exhaustion_enters_failed_state(self) -> None:
        runtime = EnvironmentRuntime(scenario_with(max_steps=1, max_proposals=2))
        for identifier in ("bad-1", "bad-2"):
            raw = current_action(runtime, identifier, "read_file", {"path": "app.py"})
            raw["risk"] = "wrong"
            with self.assertRaises(ContractError):
                runtime.propose(raw)
        self.assertEqual(runtime.state.phase, "failed")
        self.assertEqual(runtime.state.terminal_reason, "proposal_budget_exhausted")
        self.assertEqual(runtime.state.proposal_count, 2)
        self.assertEqual(runtime.state.events[-1]["outcome"], "proposal_budget_exhausted")

    def test_step_budget_exhaustion_enters_failed_state(self) -> None:
        runtime = EnvironmentRuntime(scenario_with(max_steps=1, max_proposals=3))
        runtime.apply(
            current_action(runtime, "read-1", "read_file", {"path": "app.py"})
        )
        with self.assertRaises(TerminalStateError):
            runtime.propose(
                current_action(runtime, "read-2", "read_file", {"path": "app.py"})
            )
        self.assertEqual(runtime.state.phase, "failed")
        self.assertEqual(runtime.state.terminal_reason, "step_budget_exhausted")
        self.assertEqual(runtime.state.events[-1]["outcome"], "step_budget_exhausted")

    def test_failed_run_rejects_later_proposals(self) -> None:
        runtime = EnvironmentRuntime(scenario_with(max_steps=1, max_proposals=2))
        for identifier in ("bad-1", "bad-2"):
            raw = current_action(runtime, identifier, "read_file", {"path": "app.py"})
            raw["risk"] = "wrong"
            with self.assertRaises(ContractError):
                runtime.propose(raw)
        with self.assertRaises(TerminalStateError):
            runtime.propose(
                current_action(runtime, "later", "read_file", {"path": "app.py"})
            )

    def test_failed_finish_attempt_is_an_execution_error_in_trace(self) -> None:
        runtime = EnvironmentRuntime(load_scenario(FIXTURE))
        with self.assertRaises(VerificationError):
            runtime.apply(current_action(runtime, "finish", "finish", {}))
        self.assertEqual(runtime.state.step_count, 1)
        self.assertEqual(runtime.state.events[-1]["outcome"], "execution_error")


class CheckpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.key = secrets.token_bytes(32)
        self.scenario = load_scenario(FIXTURE)

    def test_restore_preserves_environment_and_receipts(self) -> None:
        runtime = repaired_runtime()
        restored = EnvironmentRuntime.restore(
            runtime.checkpoint(self.key),
            self.scenario,
            self.key,
            generation_store=runtime.generation_store,
        )
        self.assertEqual(restored.sandbox.files, runtime.sandbox.files)
        self.assertEqual(restored.sandbox.adapter_receipts, runtime.sandbox.adapter_receipts)
        self.assertEqual(restored.state.idempotency_receipts, runtime.state.idempotency_receipts)

    def test_wrong_external_key_rejects_checkpoint(self) -> None:
        checkpoint = EnvironmentRuntime(self.scenario).checkpoint(self.key)
        with self.assertRaises(CheckpointError):
            EnvironmentRuntime.restore(
                checkpoint,
                self.scenario,
                secrets.token_bytes(32),
            )

    def test_recomputed_plain_checksum_does_not_authenticate_tampering(self) -> None:
        checkpoint = EnvironmentRuntime(self.scenario).checkpoint(self.key)
        envelope = strict_loads(checkpoint)
        envelope["payload"]["state"]["run_id"] = "tampered"
        envelope["checksum_sha256"] = sha256_json(envelope["payload"])
        with self.assertRaises(CheckpointError):
            EnvironmentRuntime.restore(
                canonical_json(envelope), self.scenario, self.key
            )

    def test_external_task_version_mismatch_is_rejected(self) -> None:
        checkpoint = EnvironmentRuntime(self.scenario).checkpoint(self.key)
        with self.assertRaises(CheckpointError):
            EnvironmentRuntime.restore(
                checkpoint,
                scenario_with(task_version="2026-07-18-v2"),
                self.key,
            )

    def test_external_policy_version_mismatch_is_rejected(self) -> None:
        checkpoint = EnvironmentRuntime(self.scenario).checkpoint(self.key)
        with self.assertRaises(CheckpointError):
            EnvironmentRuntime.restore(
                checkpoint,
                scenario_with(policy_version="environment-policy-v2"),
                self.key,
            )

    def test_resigned_forged_completion_without_verifier_trace_is_rejected(self) -> None:
        runtime = repaired_runtime()
        envelope = strict_loads(runtime.checkpoint(self.key))
        state = envelope["payload"]["state"]
        state["phase"] = "completed"
        state["terminal_reason"] = "verified_outcome"
        state["verified_version"] = 1
        state["events"].append(
            {
                "sequence": len(state["events"]) + 1,
                "proposal_count": state["proposal_count"],
                "action_id": "forged-finish",
                "kind": "finish",
                "outcome": "completed",
                "environment_version": 1,
                "detail": {},
            }
        )
        with self.assertRaises(CheckpointError):
            EnvironmentRuntime.restore(
                resign(envelope, self.key),
                self.scenario,
                self.key,
                generation_store=runtime.generation_store,
            )

    def test_resigned_structural_corruption_is_rejected(self) -> None:
        runtime = EnvironmentRuntime(self.scenario)
        envelope = strict_loads(runtime.checkpoint(self.key))
        del envelope["payload"]["state"]["task_id"]
        with self.assertRaises(CheckpointError):
            EnvironmentRuntime.restore(
                resign(envelope, self.key),
                self.scenario,
                self.key,
                generation_store=runtime.generation_store,
            )

    def test_short_signing_key_is_rejected(self) -> None:
        with self.assertRaises(CheckpointError):
            EnvironmentRuntime(self.scenario).checkpoint(b"short")

    def test_checkpoint_never_contains_signing_key(self) -> None:
        raw = EnvironmentRuntime(self.scenario).checkpoint(self.key)
        envelope = strict_loads(raw)
        self.assertNotIn("signing_key", envelope)
        self.assertNotIn(self.key.hex(), raw)

    def test_external_high_water_mark_rejects_checkpoint_rollback(self) -> None:
        runtime = EnvironmentRuntime(self.scenario)
        first = runtime.checkpoint(self.key)
        runtime.apply(
            current_action(runtime, "read-before-newer-checkpoint", "read_file", {"path": "app.py"})
        )
        second = runtime.checkpoint(self.key)
        with self.assertRaises(CheckpointError):
            EnvironmentRuntime.restore(
                first,
                self.scenario,
                self.key,
                generation_store=runtime.generation_store,
            )
        with self.assertRaises(CheckpointError):
            EnvironmentRuntime.restore(second, self.scenario, self.key)
        restored = EnvironmentRuntime.restore(
            second,
            self.scenario,
            self.key,
            generation_store=runtime.generation_store,
        )
        self.assertEqual(restored.state.checkpoint_generation, 2)

    def test_invalid_state_does_not_advance_checkpoint_high_water(self) -> None:
        runtime = EnvironmentRuntime(self.scenario)
        first = runtime.checkpoint(self.key)
        scope = runtime.generation_store.scope(
            self.scenario.task_id,
            runtime.state.run_id,
            runtime.sandbox.instance_id,
        )
        runtime.state.phase = "completed"
        runtime.state.terminal_reason = "verified_outcome"
        with self.assertRaises(CheckpointError):
            runtime.checkpoint(self.key)
        self.assertEqual(runtime.state.checkpoint_generation, 1)
        self.assertEqual(runtime.generation_store.high_water_marks[scope], 1)
        restored = EnvironmentRuntime.restore(
            first,
            self.scenario,
            self.key,
            generation_store=runtime.generation_store,
        )
        self.assertEqual(restored.state.phase, "running")


class RecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.key = secrets.token_bytes(32)
        self.scenario = load_scenario(FIXTURE)

    def pending_runtime(self) -> tuple[EnvironmentRuntime, str]:
        runtime = EnvironmentRuntime(self.scenario)
        action_id = "uncertain-write"
        proposal = runtime.propose(
            current_action(
                runtime,
                action_id,
                "write_file",
                {"path": "app.py", "content": "print('ready')\n"},
                "uncertain-key",
            )
        )
        self.assertEqual(proposal.outcome, "pending")
        return runtime, action_id

    def conflicted_runtime(self) -> tuple[EnvironmentRuntime, str]:
        runtime = EnvironmentRuntime(
            self.scenario,
            trusted_reviewer_keys={APPROVER_ID: APPROVER_KEY},
        )
        action_id = "uncertain-write"
        proposal = runtime.propose(
            current_action(
                runtime,
                action_id,
                "write_file",
                {"path": "app.py", "content": "print('ready')\n"},
                "uncertain-key",
            )
        )
        self.assertEqual(proposal.outcome, "pending")
        runtime.sandbox.adapter_receipts["uncertain-key"] = forged_receipt()
        runtime.sandbox.version = 1
        runtime.sandbox.write_count = 1
        runtime.sandbox.generation = 1
        with self.assertRaises(IdempotencyConflict):
            runtime.reconcile_pending(action_id)
        return runtime, action_id

    def test_committed_write_is_reconciled_once_after_receipt_loss(self) -> None:
        runtime, action_id = self.pending_runtime()
        precommit_checkpoint = runtime.checkpoint(self.key)
        external_environment = runtime.sandbox
        with self.assertRaises(SimulatedCrash):
            runtime.execute_pending(action_id, crash_after_commit=True)
        self.assertEqual(external_environment.write_count, 1)

        restored = EnvironmentRuntime.restore(
            precommit_checkpoint,
            self.scenario,
            self.key,
            external_sandbox=external_environment,
            generation_store=runtime.generation_store,
        )
        result = restored.reconcile_pending(action_id)
        self.assertTrue(result["replayed"])
        self.assertEqual(restored.sandbox.write_count, 1)
        self.assertEqual(restored.state.events[-1]["outcome"], "reconciled")
        self.assertFalse(restored.state.pending_intents)

    def test_approved_committed_write_recovers_with_signed_evidence(self) -> None:
        runtime = EnvironmentRuntime(
            scenario_with(approval_required_actions=["write_file"]),
            trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
        )
        raw = approved_action(runtime, action_id="approved-crash-window")
        self.assertEqual(runtime.propose(raw).outcome, "pending")
        checkpoint = runtime.checkpoint(self.key)
        external_environment = runtime.sandbox
        with self.assertRaises(SimulatedCrash):
            runtime.execute_pending(str(raw["action_id"]), crash_after_commit=True)

        restored = EnvironmentRuntime.restore(
            checkpoint,
            runtime.scenario,
            self.key,
            external_sandbox=external_environment,
            trusted_approval_keys={APPROVER_ID: APPROVER_KEY},
            generation_store=runtime.generation_store,
        )
        result = restored.reconcile_pending(str(raw["action_id"]))
        self.assertTrue(result["replayed"])
        self.assertEqual(restored.sandbox.write_count, 1)
        self.assertFalse(restored.state.pending_intents)

    def test_uncommitted_pending_intent_executes_once_during_reconciliation(self) -> None:
        runtime, action_id = self.pending_runtime()
        restored = EnvironmentRuntime.restore(
            runtime.checkpoint(self.key),
            self.scenario,
            self.key,
            generation_store=runtime.generation_store,
        )
        result = restored.reconcile_pending(action_id)
        self.assertFalse(result["replayed"])
        self.assertEqual(restored.sandbox.write_count, 1)
        self.assertFalse(restored.state.pending_intents)

    def test_conflicting_adapter_receipt_is_traced_and_not_applied(self) -> None:
        runtime, action_id = self.pending_runtime()
        runtime.sandbox.adapter_receipts["uncertain-key"] = forged_receipt()
        runtime.sandbox.version = 1
        runtime.sandbox.write_count = 1
        runtime.sandbox.generation = 1
        with self.assertRaises(IdempotencyConflict):
            runtime.reconcile_pending(action_id)
        self.assertEqual(runtime.state.events[-1]["outcome"], "idempotency_conflict")
        self.assertIn(action_id, runtime.state.pending_intents)
        self.assertEqual(runtime.state.phase, "needs_review")
        self.assertEqual(runtime.state.review_cases[action_id]["status"], "open")
        self.assertEqual(
            runtime.state.review_cases[action_id]["pending_intent"],
            runtime.state.pending_intents[action_id],
        )

    def test_review_state_blocks_execution_and_new_proposals(self) -> None:
        runtime, action_id = self.conflicted_runtime()
        with self.assertRaises(ReviewRequired):
            runtime.execute_pending(action_id)
        with self.assertRaises(ReviewRequired):
            runtime.apply(
                current_action(runtime, "read-frozen", "read_file", {"path": "app.py"})
            )
        self.assertIn(action_id, runtime.state.pending_intents)

    def test_untrusted_reconciliation_keeps_case_frozen(self) -> None:
        runtime, action_id = self.conflicted_runtime()
        record = reconciliation_for(
            runtime,
            action_id,
            decision="replan",
            reviewer_id="unknown-reviewer",
            signing_key=b"unknown-reviewer-key-material-01",
        )
        with self.assertRaises(ApprovalError):
            runtime.resolve_receipt_conflict(record)
        self.assertEqual(runtime.state.phase, "needs_review")
        self.assertIn(action_id, runtime.state.pending_intents)
        self.assertEqual(runtime.state.review_cases[action_id]["status"], "open")

    def test_state_change_invalidates_signed_reconciliation(self) -> None:
        runtime, action_id = self.conflicted_runtime()
        record = reconciliation_for(runtime, action_id, decision="replan")
        runtime.sandbox.write_file(
            "app.py", "external review race", "external-review-race", "2" * 64
        )
        with self.assertRaises(ApprovalError):
            runtime.resolve_receipt_conflict(record)
        self.assertEqual(runtime.state.phase, "needs_review")
        self.assertIn(action_id, runtime.state.pending_intents)

    def test_receipt_drift_invalidates_signed_reconciliation(self) -> None:
        runtime, action_id = self.conflicted_runtime()
        record = reconciliation_for(runtime, action_id, decision="replan")
        drifted = copy.deepcopy(runtime.sandbox.adapter_receipts["uncertain-key"])
        drifted["intent_digest"] = "1" * 64
        drifted["result"]["content_sha256"] = "1" * 64
        runtime.sandbox.adapter_receipts["uncertain-key"] = drifted
        with self.assertRaises(ApprovalError):
            runtime.resolve_receipt_conflict(record)
        self.assertEqual(runtime.state.phase, "needs_review")
        self.assertIn(action_id, runtime.state.pending_intents)

    def test_trusted_replan_restores_liveness_with_a_new_key(self) -> None:
        runtime, action_id = self.conflicted_runtime()
        result = runtime.resolve_receipt_conflict(
            reconciliation_for(runtime, action_id, decision="replan")
        )
        self.assertEqual(result["phase"], "running")
        self.assertNotIn(action_id, runtime.state.pending_intents)
        self.assertEqual(runtime.state.review_cases[action_id]["status"], "resolved")
        self.assertIn("uncertain-key", runtime.state.quarantined_idempotency_keys)
        runtime.apply(
            current_action(
                runtime,
                "replacement-write",
                "write_file",
                {"path": "app.py", "content": "print('ready')\n"},
                "replacement-key",
            )
        )
        runtime.apply(
            current_action(runtime, "test-after-review", "run_tests", {"target": "unit"})
        )
        runtime.apply(current_action(runtime, "finish-after-review", "finish", {}))
        self.assertEqual(runtime.state.phase, "completed")
        self.assertEqual(runtime.sandbox.write_count, 2)

    def test_trusted_abort_terminates_but_preserves_review_evidence(self) -> None:
        runtime, action_id = self.conflicted_runtime()
        result = runtime.resolve_receipt_conflict(
            reconciliation_for(runtime, action_id, decision="abort")
        )
        self.assertEqual(result["phase"], "failed")
        self.assertEqual(runtime.state.terminal_reason, "receipt_conflict_reviewed")
        self.assertNotIn(action_id, runtime.state.pending_intents)
        case = runtime.state.review_cases[action_id]
        self.assertEqual(case["status"], "resolved")
        self.assertIsNotNone(case["pending_intent"])
        self.assertIsNotNone(case["observed_receipt"])
        self.assertIsNotNone(case["resolution"])
        with self.assertRaises(TerminalStateError):
            runtime.apply(
                current_action(runtime, "after-abort", "read_file", {"path": "app.py"})
            )

    def test_open_review_case_survives_checkpoint_and_can_be_resolved(self) -> None:
        runtime, action_id = self.conflicted_runtime()
        restored = EnvironmentRuntime.restore(
            runtime.checkpoint(self.key),
            self.scenario,
            self.key,
            trusted_reviewer_keys={APPROVER_ID: APPROVER_KEY},
            generation_store=runtime.generation_store,
        )
        self.assertEqual(restored.state.phase, "needs_review")
        self.assertIn(action_id, restored.state.pending_intents)
        result = restored.resolve_receipt_conflict(
            reconciliation_for(restored, action_id, decision="replan")
        )
        self.assertEqual(result["phase"], "running")

    def test_resolved_review_checkpoint_requires_the_reviewer_trust_root(self) -> None:
        runtime, action_id = self.conflicted_runtime()
        runtime.resolve_receipt_conflict(
            reconciliation_for(runtime, action_id, decision="abort")
        )
        checkpoint = runtime.checkpoint(self.key)
        with self.assertRaisesRegex(
            CheckpointError,
            "checkpoint reviewer is not trusted",
        ):
            EnvironmentRuntime.restore(
                checkpoint,
                self.scenario,
                self.key,
                generation_store=runtime.generation_store,
            )
        restored = EnvironmentRuntime.restore(
            checkpoint,
            self.scenario,
            self.key,
            trusted_reviewer_keys={APPROVER_ID: APPROVER_KEY},
            generation_store=runtime.generation_store,
        )
        self.assertEqual(restored.state.phase, "failed")
        self.assertEqual(
            restored.state.review_cases[action_id]["status"], "resolved"
        )

    def test_environment_change_makes_uncommitted_pending_write_stale(self) -> None:
        runtime, action_id = self.pending_runtime()
        runtime.sandbox.write_file(
            "app.py",
            "external change",
            "other-key",
            "1" * 64,
        )
        with self.assertRaises(StaleObservation):
            runtime.execute_pending(action_id)
        self.assertEqual(runtime.state.events[-1]["outcome"], "stale_observation")
        self.assertNotIn(action_id, runtime.state.pending_intents)

    def test_same_version_state_drift_blocks_unapproved_pending_execution(self) -> None:
        runtime, action_id = self.pending_runtime()
        runtime.sandbox.files["app.py"] = "same version bypass\n"
        with self.assertRaises(StaleObservation):
            runtime.execute_pending(action_id)
        self.assertEqual(runtime.sandbox.write_count, 0)
        self.assertNotIn(action_id, runtime.state.pending_intents)

    def test_same_version_state_drift_blocks_pending_reconciliation(self) -> None:
        runtime, action_id = self.pending_runtime()
        runtime.sandbox.files["app.py"] = "same version bypass\n"
        with self.assertRaises(StaleObservation):
            runtime.reconcile_pending(action_id)
        self.assertEqual(runtime.sandbox.write_count, 0)
        self.assertNotIn(action_id, runtime.state.pending_intents)

    def test_recovered_run_can_reverify_and_complete(self) -> None:
        runtime, action_id = self.pending_runtime()
        precommit_checkpoint = runtime.checkpoint(self.key)
        external_environment = runtime.sandbox
        with self.assertRaises(SimulatedCrash):
            runtime.execute_pending(action_id, crash_after_commit=True)
        restored = EnvironmentRuntime.restore(
            precommit_checkpoint,
            self.scenario,
            self.key,
            external_sandbox=external_environment,
            generation_store=runtime.generation_store,
        )
        restored.reconcile_pending(action_id)
        restored.apply(
            current_action(restored, "test", "run_tests", {"target": "unit"})
        )
        restored.apply(current_action(restored, "finish", "finish", {}))
        self.assertEqual(restored.state.phase, "completed")
        self.assertEqual(restored.sandbox.write_count, 1)


class VerificationAndTerminationTests(unittest.TestCase):
    def test_finish_before_verification_fails(self) -> None:
        runtime = EnvironmentRuntime(load_scenario(FIXTURE))
        with self.assertRaises(VerificationError):
            runtime.apply(current_action(runtime, "finish", "finish", {}))
        self.assertEqual(runtime.state.phase, "running")

    def test_failed_test_does_not_authorize_finish(self) -> None:
        runtime = EnvironmentRuntime(load_scenario(FIXTURE))
        result = runtime.apply(
            current_action(runtime, "test", "run_tests", {"target": "unit"})
        )
        self.assertFalse(result["passed"])
        with self.assertRaises(VerificationError):
            runtime.apply(current_action(runtime, "finish", "finish", {}))

    def test_write_after_passing_test_invalidates_evidence(self) -> None:
        runtime = repaired_runtime()
        runtime.apply(
            current_action(runtime, "test", "run_tests", {"target": "unit"})
        )
        runtime.apply(
            current_action(
                runtime,
                "write-again",
                "write_file",
                {"path": "app.py", "content": "broken again"},
                "break-again",
            )
        )
        with self.assertRaises(VerificationError):
            runtime.apply(current_action(runtime, "finish", "finish", {}))

    def test_cancel_is_terminal(self) -> None:
        runtime = EnvironmentRuntime(load_scenario(FIXTURE))
        result = runtime.apply(
            current_action(runtime, "cancel", "cancel", {"reason": "operator_stop"})
        )
        self.assertEqual(result["phase"], "cancelled")
        with self.assertRaises(TerminalStateError):
            runtime.apply(current_action(runtime, "later", "finish", {}))

    def test_completed_run_is_terminal(self) -> None:
        runtime = repaired_runtime()
        runtime.apply(
            current_action(runtime, "test", "run_tests", {"target": "unit"})
        )
        runtime.apply(current_action(runtime, "finish", "finish", {}))
        with self.assertRaises(TerminalStateError):
            runtime.apply(
                current_action(runtime, "later", "read_file", {"path": "app.py"})
            )

    def test_completed_checkpoint_can_be_restored(self) -> None:
        key = secrets.token_bytes(32)
        scenario = load_scenario(FIXTURE)
        runtime = repaired_runtime()
        runtime.apply(
            current_action(runtime, "test", "run_tests", {"target": "unit"})
        )
        runtime.apply(current_action(runtime, "finish", "finish", {}))
        restored = EnvironmentRuntime.restore(
            runtime.checkpoint(key),
            scenario,
            key,
            generation_store=runtime.generation_store,
        )
        self.assertEqual(restored.state.phase, "completed")
        self.assertEqual(restored.state.verified_version, restored.sandbox.version)

    def test_demo_has_verified_single_write_outcome(self) -> None:
        result = run_demo()
        self.assertEqual(result["phase"], "completed")
        self.assertEqual(result["terminal_reason"], "verified_outcome")
        self.assertEqual(result["environment_version"], 1)
        self.assertEqual(result["write_count"], 1)
        self.assertEqual(result["proposal_count"], 4)
        self.assertEqual(result["event_count"], 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
