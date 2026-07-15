"""离线发布门的最小回归测试；只使用 Python 标准库。"""

from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import release_gate


class ReleaseGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = release_gate.validate_manifest(
            release_gate.load_json(release_gate.DEFAULT_MANIFEST)
        )
        cls.observation_bundle = release_gate.validate_observations(
            release_gate.load_json(release_gate.DEFAULT_OBSERVATIONS)
        )

    def candidate(self, release_id: str) -> dict[str, object]:
        return copy.deepcopy(
            next(
                item
                for item in self.manifest["candidates"]
                if item["release_id"] == release_id
            )
        )

    def observation(self, observation_id: str) -> dict[str, object]:
        return copy.deepcopy(
            next(
                item
                for item in self.observation_bundle["observations"]
                if item["observation_id"] == observation_id
            )
        )

    def decide_candidate(self, candidate: dict[str, object]) -> release_gate.Decision:
        return release_gate.candidate_decision(
            candidate, self.manifest["baseline"], self.manifest["policy"]
        )

    def decide_observation(self, observation: dict[str, object]) -> release_gate.Decision:
        return release_gate.observation_decision(
            observation, self.manifest["baseline"], self.manifest["policy"]
        )

    def test_manifest_and_observation_fixtures_are_valid(self) -> None:
        self.assertEqual(len(self.manifest["candidates"]), 2)
        self.assertEqual(len(self.observation_bundle["observations"]), 6)

    def test_unknown_manifest_field_is_rejected(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        malformed["surprise"] = True
        with self.assertRaisesRegex(release_gate.ContractError, "未知字段"):
            release_gate.validate_manifest(malformed)

    def test_missing_component_is_rejected(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        del malformed["candidates"][0]["pricing"]
        with self.assertRaisesRegex(release_gate.ContractError, "缺少字段: pricing"):
            release_gate.validate_manifest(malformed)

    def test_mutable_model_alias_is_rejected(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        malformed["candidates"][0]["model"]["model_snapshot"] = "latest"
        with self.assertRaisesRegex(release_gate.ContractError, "非浮动标识"):
            release_gate.validate_manifest(malformed)

    def test_duplicate_release_id_is_rejected(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        malformed["candidates"][1]["release_id"] = "release-safe"
        with self.assertRaisesRegex(release_gate.ContractError, "重复 release_id"):
            release_gate.validate_manifest(malformed)

    def test_boolean_is_not_accepted_as_number(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        malformed["baseline"]["metrics"]["p95_latency_ms"] = True
        with self.assertRaisesRegex(release_gate.ContractError, "必须是数值"):
            release_gate.validate_manifest(malformed)

    def test_fractional_sample_count_is_rejected(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        malformed["candidates"][0]["metrics"]["safety_sample_count"] = 50.5
        with self.assertRaisesRegex(release_gate.ContractError, "必须是整数"):
            release_gate.validate_manifest(malformed)

    def test_rate_above_one_is_rejected(self) -> None:
        malformed = copy.deepcopy(self.observation_bundle)
        malformed["observations"][0]["provider_error_rate"] = 1.1
        with self.assertRaisesRegex(release_gate.ContractError, "小于等于 1"):
            release_gate.validate_observations(malformed)

    def test_non_finite_metric_is_rejected(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        malformed["baseline"]["metrics"]["p95_latency_ms"] = float("nan")
        with self.assertRaisesRegex(release_gate.ContractError, "有限数值"):
            release_gate.validate_manifest(malformed)

    def test_nonstandard_json_nan_is_rejected_during_load(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "nan.json"
            path.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(release_gate.ContractError, "JSON 标准之外"):
                release_gate.load_json(path)

    def test_safe_candidate_is_promoted(self) -> None:
        decision = self.decide_candidate(self.candidate("release-safe"))
        self.assertTrue(decision.passed)
        self.assertEqual(decision.action, "promote")
        self.assertEqual(decision.reasons, ())

    def test_regression_candidate_is_blocked_for_multiple_independent_reasons(self) -> None:
        decision = self.decide_candidate(self.candidate("release-regression"))
        joined = "\n".join(decision.reasons)
        self.assertEqual(decision.action, "block")
        self.assertIn("tool_contract", joined)
        self.assertIn("高风险切片成功率", joined)
        self.assertIn("安全切片样本量", joined)
        self.assertIn("估算成本", joined)
        self.assertIn("人工审批", joined)

    def test_trace_failure_blocks_candidate(self) -> None:
        candidate = self.candidate("release-safe")
        candidate["operations"]["trace_schema_complete"] = False
        self.assertIn("Trace schema", "\n".join(self.decide_candidate(candidate).reasons))

    def test_safety_sample_floor_is_enforced_even_with_zero_observed_violations(self) -> None:
        candidate = self.candidate("release-safe")
        candidate["metrics"]["safety_sample_count"] = 1
        decision = self.decide_candidate(candidate)
        self.assertEqual(decision.action, "block")
        self.assertIn("样本量不足", "\n".join(decision.reasons))

    def test_evidence_fingerprint_is_stable_and_sensitive_to_change(self) -> None:
        candidate = self.candidate("release-safe")
        original = self.decide_candidate(candidate).evidence_fingerprint
        self.assertEqual(original, self.decide_candidate(copy.deepcopy(candidate)).evidence_fingerprint)
        candidate["metrics"]["p95_latency_ms"] += 1
        self.assertNotEqual(original, self.decide_candidate(candidate).evidence_fingerprint)

    def test_healthy_observation_continues(self) -> None:
        decision = self.decide_observation(self.observation("obs-healthy"))
        self.assertTrue(decision.passed)
        self.assertEqual(decision.action, "continue")

    def test_low_sample_observation_requires_investigation(self) -> None:
        decision = self.decide_observation(self.observation("obs-low-sample"))
        self.assertEqual(decision.action, "investigate")
        self.assertIn("样本量不足", "\n".join(decision.reasons))

    def test_provider_drift_uses_prevalidated_fallback(self) -> None:
        decision = self.decide_observation(self.observation("obs-provider-drift"))
        self.assertEqual(decision.action, "fallback")
        self.assertIn("降级路径", "\n".join(decision.reasons))

    def test_provider_drift_without_fallback_requires_human_review(self) -> None:
        decision = self.decide_observation(self.observation("obs-no-fallback"))
        self.assertEqual(decision.action, "human_review")
        self.assertIn("没有已验证", "\n".join(decision.reasons))

    def test_quality_or_safety_regression_rolls_back(self) -> None:
        decision = self.decide_observation(self.observation("obs-quality-regression"))
        self.assertEqual(decision.action, "rollback")
        joined = "\n".join(decision.reasons)
        self.assertIn("任务成功率", joined)
        self.assertIn("安全违规", joined)

    def test_capacity_or_cost_regression_pauses_expansion(self) -> None:
        decision = self.decide_observation(self.observation("obs-capacity-cost"))
        self.assertEqual(decision.action, "pause")
        joined = "\n".join(decision.reasons)
        self.assertIn("p95", joined)
        self.assertIn("成本", joined)

    def test_redaction_failure_has_rollback_priority_over_cost_pause(self) -> None:
        observation = self.observation("obs-capacity-cost")
        observation["redaction_check_passed"] = False
        decision = self.decide_observation(observation)
        self.assertEqual(decision.action, "rollback")

    def test_safety_rollback_has_priority_over_missing_fallback_review(self) -> None:
        observation = self.observation("obs-no-fallback")
        observation["safety_violation_rate"] = 0.01
        decision = self.decide_observation(observation)
        self.assertEqual(decision.action, "rollback")

    def test_main_returns_zero_for_safe_candidate(self) -> None:
        with redirect_stdout(io.StringIO()):
            code = release_gate.main(["candidate", "--release-id", "release-safe"])
        self.assertEqual(code, 0)

    def test_main_returns_one_for_blocked_candidate(self) -> None:
        with redirect_stdout(io.StringIO()):
            code = release_gate.main(["candidate", "--release-id", "release-regression"])
        self.assertEqual(code, 1)

    def test_main_returns_zero_for_healthy_audit_pair(self) -> None:
        with redirect_stdout(io.StringIO()):
            code = release_gate.main(
                [
                    "audit",
                    "--release-id",
                    "release-safe",
                    "--observation-id",
                    "obs-healthy",
                ]
            )
        self.assertEqual(code, 0)

    def test_main_returns_two_for_bad_json_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "bad.json"
            path.write_text(json.dumps({"wrong": True}), encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                code = release_gate.main(["candidate", "--manifest", str(path)])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
