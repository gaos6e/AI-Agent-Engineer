"""Tests for the deterministic MLOps promotion and operations gate."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

import promotion_gate as gate


class GateTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidates_path = Path(__file__).with_name("candidates.json")
        cls.observations_path = Path(__file__).with_name("observations.json")
        cls.candidates = gate.load_json(cls.candidates_path)
        gate.validate_candidates_fixture(cls.candidates)
        cls.observations = gate.load_json(cls.observations_path)
        gate.validate_observations_fixture(cls.observations, cls.candidates)

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)

    def candidate(self, identifier: str) -> dict[str, object]:
        return copy.deepcopy(
            next(item for item in self.candidates["candidates"] if item["candidate_id"] == identifier)
        )

    def window(self, identifier: str) -> dict[str, object]:
        return copy.deepcopy(
            next(item for item in self.observations["windows"] if item["window_id"] == identifier)
        )


class CandidateFixtureTests(GateTestCase):
    def test_fixture_is_valid(self) -> None:
        gate.validate_candidates_fixture(self.candidates)

    def test_fixture_must_be_object(self) -> None:
        with self.assertRaises(gate.GateError):
            gate.validate_candidates_fixture([])

    def test_unknown_top_level_field_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.candidates)
        fixture["extra"] = True
        with self.assertRaises(gate.GateError):
            gate.validate_candidates_fixture(fixture)

    def test_schema_version_is_strict(self) -> None:
        fixture = copy.deepcopy(self.candidates)
        fixture["schema_version"] = 3
        with self.assertRaises(gate.GateError):
            gate.validate_candidates_fixture(fixture)

    def test_duplicate_candidate_id_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.candidates)
        fixture["candidates"][1]["candidate_id"] = fixture["candidates"][0]["candidate_id"]
        with self.assertRaises(gate.GateError):
            gate.validate_candidates_fixture(fixture)

    def test_mutable_lineage_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.candidates)
        fixture["candidates"][0]["lineage"]["data_snapshot"] = "latest"
        with self.assertRaises(gate.GateError):
            gate.validate_candidates_fixture(fixture)

    def test_bad_digest_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.candidates)
        fixture["candidates"][0]["artifact"]["digest"] = "sha256:not-a-digest"
        with self.assertRaises(gate.GateError):
            gate.validate_candidates_fixture(fixture)

    def test_uppercase_digest_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.candidates)
        fixture["candidates"][0]["artifact"]["digest"] = "sha256:" + "A" * 64
        with self.assertRaises(gate.GateError):
            gate.validate_candidates_fixture(fixture)

    def test_boolean_metric_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.candidates)
        fixture["baseline"]["metrics"]["overall_accuracy"] = True
        with self.assertRaises(gate.GateError):
            gate.validate_candidates_fixture(fixture)

    def test_non_finite_metric_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.candidates)
        fixture["baseline"]["metrics"]["overall_accuracy"] = float("nan")
        with self.assertRaises(gate.GateError):
            gate.validate_candidates_fixture(fixture)

    def test_zero_artifact_size_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.candidates)
        fixture["candidates"][0]["artifact"]["size_bytes"] = 0
        with self.assertRaises(gate.GateError):
            gate.validate_candidates_fixture(fixture)

    def test_missing_required_test_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.candidates)
        del fixture["candidates"][0]["tests"]["data"]
        with self.assertRaises(gate.GateError):
            gate.validate_candidates_fixture(fixture)

    def test_invalid_json_is_reported(self) -> None:
        path = self.root / "bad.json"
        path.write_text("{", encoding="utf-8")
        with self.assertRaises(gate.GateError):
            gate.load_json(path)

    def test_duplicate_json_key_is_rejected(self) -> None:
        path = self.root / "duplicate.json"
        path.write_text('{"schema_version": 2, "schema_version": 2}', encoding="utf-8")
        with self.assertRaisesRegex(gate.GateError, "duplicate JSON key"):
            gate.load_json(path)

    def test_nonstandard_json_constant_is_rejected(self) -> None:
        path = self.root / "nan.json"
        path.write_text('{"value": NaN}', encoding="utf-8")
        with self.assertRaisesRegex(gate.GateError, "non-standard JSON constant"):
            gate.load_json(path)


class PromotionDecisionTests(GateTestCase):
    def decide(self, candidate: dict[str, object]) -> dict[str, object]:
        return gate.evaluate_candidate(
            candidate,
            self.candidates["baseline"],
            self.candidates["policy"],
            self.candidates["policy_version"],
        )

    def test_safe_candidate_is_promoted(self) -> None:
        decision = self.decide(self.candidate("candidate-safe"))
        self.assertTrue(decision["passed"])
        self.assertEqual(decision["decision"], "promote")

    def test_regression_candidate_is_blocked(self) -> None:
        decision = self.decide(self.candidate("candidate-regression"))
        self.assertFalse(decision["passed"])
        self.assertTrue(any("required test failed" in item for item in decision["reasons"]))
        self.assertTrue(any("critical_slice_recall" in item for item in decision["reasons"]))

    def test_overall_regression_is_blocked(self) -> None:
        candidate = self.candidate("candidate-safe")
        candidate["metrics"]["overall_accuracy"] = 0.8
        self.assertFalse(self.decide(candidate)["passed"])

    def test_latency_regression_is_blocked(self) -> None:
        candidate = self.candidate("candidate-safe")
        candidate["metrics"]["p95_latency_ms"] = 121.0
        self.assertFalse(self.decide(candidate)["passed"])

    def test_large_artifact_is_blocked(self) -> None:
        candidate = self.candidate("candidate-safe")
        candidate["artifact"]["size_bytes"] = 1000001
        self.assertFalse(self.decide(candidate)["passed"])

    def test_incompatible_signature_is_blocked(self) -> None:
        candidate = self.candidate("candidate-safe")
        candidate["artifact"]["signature"]["input_schema_version"] = "fraud-features-v4"
        self.assertFalse(self.decide(candidate)["passed"])

    def test_failed_smoke_test_is_blocked(self) -> None:
        candidate = self.candidate("candidate-safe")
        candidate["tests"]["inference_smoke"] = False
        self.assertFalse(self.decide(candidate)["passed"])

    def test_decision_records_policy_version(self) -> None:
        decision = self.decide(self.candidate("candidate-safe"))
        self.assertEqual(decision["policy_version"], "promotion-lab-v3")

    def test_evidence_fingerprint_is_deterministic(self) -> None:
        first = self.decide(self.candidate("candidate-safe"))
        second = self.decide(self.candidate("candidate-safe"))
        self.assertEqual(first["evidence_fingerprint"], second["evidence_fingerprint"])


class ObservationFixtureTests(GateTestCase):
    def test_fixture_is_valid(self) -> None:
        gate.validate_observations_fixture(self.observations, self.candidates)

    def test_policy_mismatch_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.observations)
        fixture["policy_version"] = "other-policy"
        with self.assertRaises(gate.GateError):
            gate.validate_observations_fixture(fixture, self.candidates)

    def test_unknown_deployed_model_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.observations)
        fixture["deployment"]["model_id"] = "missing"
        with self.assertRaises(gate.GateError):
            gate.validate_observations_fixture(fixture, self.candidates)

    def test_deployed_digest_mismatch_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.observations)
        fixture["deployment"]["artifact_digest"] = "sha256:" + "f" * 64
        with self.assertRaises(gate.GateError):
            gate.validate_observations_fixture(fixture, self.candidates)

    def test_stale_promotion_fingerprint_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.observations)
        fixture["deployment"]["promotion_evidence_fingerprint"] = "0" * 64
        with self.assertRaisesRegex(gate.GateError, "stale or mismatched"):
            gate.validate_observations_fixture(fixture, self.candidates)

    def test_blocked_candidate_cannot_be_declared_deployed(self) -> None:
        fixture = copy.deepcopy(self.observations)
        blocked = self.candidate("candidate-regression")
        fixture["deployment"]["model_id"] = blocked["candidate_id"]
        fixture["deployment"]["artifact_digest"] = blocked["artifact"]["digest"]
        with self.assertRaisesRegex(gate.GateError, "did not pass"):
            gate.validate_observations_fixture(fixture, self.candidates)

    def test_reference_must_bind_to_deployed_artifact(self) -> None:
        fixture = copy.deepcopy(self.observations)
        fixture["reference"]["artifact_digest"] = "sha256:" + "f" * 64
        with self.assertRaisesRegex(gate.GateError, "reference artifact"):
            gate.validate_observations_fixture(fixture, self.candidates)

    def test_duplicate_window_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.observations)
        fixture["windows"][1]["window_id"] = fixture["windows"][0]["window_id"]
        with self.assertRaises(gate.GateError):
            gate.validate_observations_fixture(fixture, self.candidates)

    def test_zero_samples_are_rejected(self) -> None:
        fixture = copy.deepcopy(self.observations)
        fixture["windows"][0]["sample_count"] = 0
        with self.assertRaises(gate.GateError):
            gate.validate_observations_fixture(fixture, self.candidates)

    def test_unknown_release_phase_is_rejected(self) -> None:
        fixture = copy.deepcopy(self.observations)
        fixture["windows"][0]["phase"] = "production"
        with self.assertRaisesRegex(gate.GateError, "must be one of"):
            gate.validate_observations_fixture(fixture, self.candidates)

    def test_labeled_count_cannot_exceed_sample_count(self) -> None:
        fixture = copy.deepcopy(self.observations)
        fixture["windows"][0]["labeled_count"] = 2001
        with self.assertRaisesRegex(gate.GateError, "must not exceed sample_count"):
            gate.validate_observations_fixture(fixture, self.candidates)

    def test_critical_count_cannot_exceed_labeled_count(self) -> None:
        fixture = copy.deepcopy(self.observations)
        fixture["windows"][0]["critical_labeled_count"] = 1601
        with self.assertRaisesRegex(gate.GateError, "must not exceed labeled_count"):
            gate.validate_observations_fixture(fixture, self.candidates)


class OperationalDecisionTests(GateTestCase):
    def assess(self, observation: dict[str, object]) -> dict[str, object]:
        return gate.assess_observation(
            observation,
            self.observations["reference"],
            self.candidates["policy"],
            self.candidates["policy_version"],
            self.observations["deployment"],
        )

    def test_healthy_window_continues(self) -> None:
        self.assertEqual(self.assess(self.window("window-healthy"))["action"], "continue")

    def test_drift_without_labels_requires_investigation(self) -> None:
        decision = self.assess(self.window("window-drift-no-label"))
        self.assertEqual(decision["action"], "investigate")
        self.assertTrue(any("label_coverage" in item for item in decision["reasons"]))

    def test_label_backed_regression_rolls_back_and_reviews_retraining(self) -> None:
        decision = self.assess(self.window("window-quality-regression"))
        self.assertEqual(decision["action"], "rollback_and_review_retraining")

    def test_technical_failure_rolls_back(self) -> None:
        decision = self.assess(self.window("window-technical-failure"))
        self.assertEqual(decision["action"], "rollback_and_investigate")

    def test_drift_alone_never_auto_retrains(self) -> None:
        decision = self.assess(self.window("window-drift-no-label"))
        self.assertNotIn("retraining", decision["action"])

    def test_low_label_coverage_prevents_quality_claim(self) -> None:
        observation = self.window("window-drift-no-label")
        observation["signals"]["critical_slice_recall"] = 0.2
        decision = self.assess(observation)
        self.assertEqual(decision["action"], "investigate")

    def test_small_window_cannot_auto_continue(self) -> None:
        observation = self.window("window-healthy")
        observation["sample_count"] = 400
        observation["labeled_count"] = 320
        observation["critical_labeled_count"] = 120
        decision = self.assess(observation)
        self.assertEqual(decision["action"], "investigate")
        self.assertTrue(any("sample_count" in item for item in decision["reasons"]))

    def test_small_critical_slice_cannot_confirm_quality(self) -> None:
        observation = self.window("window-quality-regression")
        observation["critical_labeled_count"] = 10
        decision = self.assess(observation)
        self.assertEqual(decision["action"], "investigate")

    def test_shadow_technical_failure_blocks_rollout(self) -> None:
        decision = self.assess(self.window("window-shadow-technical-failure"))
        self.assertEqual(decision["action"], "block_rollout_and_investigate")
        self.assertEqual(decision["phase"], "shadow")

    def test_quality_regression_without_drift_rolls_back_to_investigate(self) -> None:
        observation = self.window("window-quality-regression")
        observation["signals"]["input_drift_score"] = 0.01
        decision = self.assess(observation)
        self.assertEqual(decision["action"], "rollback_and_investigate")

    def test_operational_fingerprint_is_deterministic(self) -> None:
        first = self.assess(self.window("window-healthy"))
        second = self.assess(self.window("window-healthy"))
        self.assertEqual(first["evidence_fingerprint"], second["evidence_fingerprint"])


class CliTests(GateTestCase):
    def call_main(self, *arguments: str) -> tuple[int, object]:
        stream = io.StringIO()
        prefix = [
            "--candidates",
            str(self.candidates_path),
            "--observations",
            str(self.observations_path),
        ]
        with contextlib.redirect_stdout(stream):
            code = gate.main([*prefix, *arguments])
        return code, json.loads(stream.getvalue())

    def test_candidate_cli_passes(self) -> None:
        code, payload = self.call_main("candidate", "--id", "candidate-safe")
        self.assertEqual(code, 0)
        self.assertEqual(payload["decision"], "promote")

    def test_candidate_cli_blocks(self) -> None:
        code, payload = self.call_main("candidate", "--id", "candidate-regression")
        self.assertEqual(code, 1)
        self.assertEqual(payload["decision"], "block")

    def test_observation_cli_investigates(self) -> None:
        code, payload = self.call_main("observe", "--id", "window-drift-no-label")
        self.assertEqual(code, 1)
        self.assertEqual(payload["action"], "investigate")

    def test_audit_cli_reports_every_scenario(self) -> None:
        code, payload = self.call_main("audit")
        self.assertEqual(code, 0)
        self.assertEqual(len(payload["candidate_decisions"]), 2)
        self.assertEqual(len(payload["operational_decisions"]), 5)

    def test_unknown_candidate_returns_error(self) -> None:
        code, payload = self.call_main("candidate", "--id", "missing")
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "error")


if __name__ == "__main__":
    unittest.main()
