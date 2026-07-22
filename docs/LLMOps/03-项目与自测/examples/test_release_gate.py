"""离线发布门的最小回归测试；只使用 Python 标准库。"""

from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

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
        bound_candidate = release_gate.bind_observation(self.manifest, observation)
        return release_gate.observation_decision(
            observation,
            self.manifest["policy"],
            self.observation_bundle["schema_version"],
            self.observation_bundle["evidence_digest_format"],
            bound_candidate,
        )

    def test_manifest_and_observation_fixtures_are_valid(self) -> None:
        self.assertEqual("local-llmops-policy-v6", self.manifest["policy"]["version"])
        self.assertEqual(
            "local-online-observation-v6",
            self.observation_bundle["schema_version"],
        )
        self.assertEqual(
            self.observation_bundle["evidence_digest_format"],
            release_gate.EVIDENCE_DIGEST_FORMAT,
        )
        self.assertEqual(len(self.manifest["candidates"]), 2)
        self.assertEqual(len(self.observation_bundle["observations"]), 7)

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

    def test_latest_suffix_and_tag_are_rejected_for_model_snapshot(self) -> None:
        for value in (
            "provider-model-latest",
            "registry.example/model:latest",
            "models/latest",
        ):
            with self.subTest(value=value):
                malformed = copy.deepcopy(self.manifest)
                malformed["candidates"][0]["model"]["model_snapshot"] = value
                with self.assertRaisesRegex(
                    release_gate.ContractError,
                    r"model_snapshot.*非浮动标识",
                ):
                    release_gate.validate_manifest(malformed)

    def test_floating_branch_ref_is_rejected_for_app_commit(self) -> None:
        for value in (
            "HEAD",
            "refs/heads/main",
            "refs/heads/develop",
            "refs/heads/feature/safe-rollout",
            "refs/remotes/origin/master",
            "refs/remotes/upstream/release-v2",
            "origin/main",
            "origin/develop",
        ):
            with self.subTest(value=value):
                malformed = copy.deepcopy(self.manifest)
                malformed["candidates"][0]["app"]["commit"] = value
                with self.assertRaisesRegex(
                    release_gate.ContractError,
                    r"app\.commit.*非浮动标识",
                ):
                    release_gate.validate_manifest(malformed)

    def test_main_substring_in_fixed_version_is_allowed(self) -> None:
        valid = copy.deepcopy(self.manifest)
        valid["candidates"][0]["prompt"]["version"] = "domain-mainframe-v1"
        self.assertIs(valid, release_gate.validate_manifest(valid))

    def test_duplicate_release_id_is_rejected(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        malformed["candidates"][1]["release_id"] = "release-safe"
        malformed["candidates"][1]["evaluation"]["subject_release_id"] = "release-safe"
        with self.assertRaisesRegex(release_gate.ContractError, "重复 release_id"):
            release_gate.validate_manifest(malformed)

    def test_baseline_and_candidate_release_ids_are_globally_unique(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        baseline_release_id = malformed["baseline"]["release_id"]
        malformed["candidates"][0]["release_id"] = baseline_release_id
        malformed["candidates"][0]["evaluation"][
            "subject_release_id"
        ] = baseline_release_id
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

    def test_all_policy_proportions_are_bounded_by_one(self) -> None:
        proportion_fields = (
            "min_task_success_delta",
            "min_critical_success_delta",
            "max_safety_violation_rate",
            "max_latency_increase_ratio",
            "max_cost_increase_ratio",
            "online_min_label_coverage",
            "online_max_task_drop",
            "online_max_critical_drop",
            "online_max_provider_error_rate",
            "online_max_provider_shift_score",
            "online_max_latency_increase_ratio",
            "online_max_cost_increase_ratio",
        )
        for field in proportion_fields:
            with self.subTest(field=field):
                malformed = copy.deepcopy(self.manifest)
                malformed["policy"][field] = 1.01
                with self.assertRaisesRegex(
                    release_gate.ContractError,
                    rf"policy\.{field}.*小于等于 1",
                ):
                    release_gate.validate_manifest(malformed)

    def test_extreme_safety_rate_limit_cannot_disable_gate(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        malformed["policy"]["max_safety_violation_rate"] = 999
        with self.assertRaisesRegex(release_gate.ContractError, "小于等于 1"):
            release_gate.validate_manifest(malformed)

    def test_non_finite_metric_is_rejected(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        malformed["baseline"]["metrics"]["p95_latency_ms"] = float("nan")
        with self.assertRaisesRegex(release_gate.ContractError, "有限数值"):
            release_gate.validate_manifest(malformed)

    def test_overflowing_integer_is_a_contract_error(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        malformed["baseline"]["metrics"]["p95_latency_ms"] = 10**400
        with self.assertRaisesRegex(release_gate.ContractError, "可表示为有限数值"):
            release_gate.validate_manifest(malformed)

    def test_nonstandard_json_nan_is_rejected_during_load(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "nan.json"
            path.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(release_gate.ContractError, "JSON 标准之外"):
                release_gate.load_json(path)

    def test_non_utf8_input_is_a_contract_error_at_load_and_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "surrogate.json"
            path.write_text('{"value": "\\ud800"}', encoding="utf-8")
            with self.assertRaisesRegex(release_gate.ContractError, "Unicode surrogate"):
                release_gate.load_json(path)
            path.write_text('{"\\ud800": 1}', encoding="utf-8")
            with self.assertRaisesRegex(release_gate.ContractError, "Unicode surrogate"):
                release_gate.load_json(path)
            path.write_bytes(b'{"value":"\xff"}')
            with self.assertRaisesRegex(release_gate.ContractError, "有效 UTF-8 JSON"):
                release_gate.load_json(path)
        with self.assertRaisesRegex(release_gate.ContractError, "Unicode surrogate"):
            release_gate.full_evidence_sha256({"value": "\ud800"})

    def test_duplicate_json_key_is_rejected_during_load(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "duplicate.json"
            path.write_text('{"policy": 1, "policy": 2}', encoding="utf-8")
            with self.assertRaisesRegex(release_gate.ContractError, "重复字段"):
                release_gate.load_json(path)

    def test_evaluation_artifact_is_bound_to_release(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        malformed["candidates"][0]["evaluation"]["subject_release_id"] = "other"
        with self.assertRaisesRegex(release_gate.ContractError, "绑定所属 release_id"):
            release_gate.validate_manifest(malformed)

    def test_evaluation_artifact_requires_full_sha256(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        malformed["candidates"][0]["evaluation"]["artifact_sha256"] = "sha256-short"
        with self.assertRaisesRegex(release_gate.ContractError, "64 位"):
            release_gate.validate_manifest(malformed)

    def test_evaluation_artifact_requires_a_supported_digest_format(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        malformed["candidates"][0]["evaluation"]["artifact_digest_format"] = "unknown-v9"
        with self.assertRaisesRegex(release_gate.ContractError, "证据摘要格式"):
            release_gate.validate_manifest(malformed)

    def test_evidence_digest_golden_vector_matches_the_shared_teaching_profile(self) -> None:
        self.assertEqual(
            release_gate.EVIDENCE_DIGEST_FORMAT,
            "python-json-sorted-utf8-v1",
        )
        actual = release_gate.full_evidence_sha256(
            {"z": "\u6c49\u5b57", "a": [1, 2.5], "nested": {"\u03b2": "\u503c"}},
            "release-v1",
        )
        self.assertEqual(
            actual,
            "ee2f7ef27b87716fd2359ee2f42aae77a38d58792636bf959292c885242152d6",
        )

    def test_fallback_manifest_requires_full_sha256_evidence(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        malformed["candidates"][0]["routing"]["fallback_manifest"][
            "manifest_sha256"
        ] = "sha256-short"
        with self.assertRaisesRegex(release_gate.ContractError, "64 位"):
            release_gate.validate_manifest(malformed)

    def test_fallback_manifest_cannot_point_to_candidate_itself(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        candidate = malformed["candidates"][0]
        candidate["routing"]["fallback_manifest"]["release_id"] = candidate[
            "release_id"
        ]
        with self.assertRaisesRegex(release_gate.ContractError, "不得指向自身"):
            release_gate.validate_manifest(malformed)

    def test_duplicate_tool_name_is_rejected(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        duplicate = copy.deepcopy(malformed["candidates"][0]["tools"][0])
        duplicate["schema_version"] = "lookup-ticket-schema-v3"
        malformed["candidates"][0]["tools"].append(duplicate)
        with self.assertRaisesRegex(release_gate.ContractError, "重复 name"):
            release_gate.validate_manifest(malformed)

    def test_known_blocked_candidate_cannot_be_fallback(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        malformed["candidates"][0]["routing"]["fallback_manifest"][
            "release_id"
        ] = "release-regression"
        with self.assertRaisesRegex(release_gate.ContractError, "未通过 candidate gate"):
            release_gate.validate_manifest(malformed)

    def test_known_fallback_candidates_cannot_form_cycle(self) -> None:
        malformed = copy.deepcopy(self.manifest)
        first = malformed["candidates"][0]
        second = copy.deepcopy(first)
        second["release_id"] = "release-safe-b"
        second["evaluation"]["subject_release_id"] = "release-safe-b"
        first["routing"]["fallback_manifest"]["release_id"] = "release-safe-b"
        second["routing"]["fallback_manifest"]["release_id"] = "release-safe"
        malformed["candidates"] = [first, second]
        with self.assertRaisesRegex(release_gate.ContractError, "形成循环"):
            release_gate.validate_manifest(malformed)

    def test_incomparable_evaluation_contract_is_not_promoted(self) -> None:
        candidate = self.candidate("release-safe")
        candidate["evaluation"]["dataset_version"] = "different-dataset"
        decision = self.decide_candidate(candidate)
        self.assertEqual("incomparable", decision.action)
        self.assertIn("dataset_version", "\n".join(decision.reasons))

    def test_online_window_must_be_forward_utc_interval(self) -> None:
        malformed = copy.deepcopy(self.observation_bundle)
        malformed["observations"][0]["window_end"] = malformed["observations"][0][
            "window_start"
        ]
        with self.assertRaisesRegex(release_gate.ContractError, "window_start < window_end"):
            release_gate.validate_observations(malformed)

    def test_online_window_rejects_date_only_naive_and_non_string_values(self) -> None:
        for value in (
            "2026-07-14",
            "2026-07-14Z",
            "2026-07-14T00:00:00",
            None,
        ):
            with self.subTest(value=value):
                malformed = copy.deepcopy(self.observation_bundle)
                malformed["observations"][0]["window_start"] = value
                with self.assertRaisesRegex(
                    release_gate.ContractError,
                    "RFC3339 UTC 日期时间",
                ):
                    release_gate.validate_observations(malformed)

    def test_online_window_requires_utc_offset(self) -> None:
        for value in ("2026-07-14T08:00:00+08:00", "2026-07-14T00:00:00-00:00"):
            with self.subTest(value=value):
                malformed = copy.deepcopy(self.observation_bundle)
                malformed["observations"][0]["window_start"] = value
                with self.assertRaisesRegex(
                    release_gate.ContractError,
                    "RFC3339 UTC 日期时间",
                ):
                    release_gate.validate_observations(malformed)

    def test_online_window_accepts_explicit_zero_offset(self) -> None:
        valid = copy.deepcopy(self.observation_bundle)
        valid["observations"][0]["window_start"] = "2026-07-14T00:00:00+00:00"
        self.assertIs(valid, release_gate.validate_observations(valid))

    def test_candidate_timestamps_are_ordered_within_decision_as_of(self) -> None:
        cases = (
            ("gate_decided_at", "2026-07-14T06:00:01Z", "decision_as_of"),
            ("promoted_at", "2026-07-13T23:49:59Z", "gate_decided_at"),
            ("promoted_at", "2026-07-14T06:00:01Z", "decision_as_of"),
        )
        for field, value, message in cases:
            with self.subTest(field=field, value=value):
                malformed = copy.deepcopy(self.manifest)
                malformed["candidates"][0][field] = value
                with self.assertRaisesRegex(release_gate.ContractError, message):
                    release_gate.validate_manifest(malformed)

    def test_online_arm_counts_must_be_consistent(self) -> None:
        malformed = copy.deepcopy(self.observation_bundle)
        malformed["observations"][0]["candidate"]["labeled_count"] = 999
        with self.assertRaisesRegex(release_gate.ContractError, "不得超过 eligible_count"):
            release_gate.validate_observations(malformed)

    def test_online_arm_outcome_numerators_must_match_denominators(self) -> None:
        malformed = copy.deepcopy(self.observation_bundle)
        malformed["observations"][0]["candidate"]["task_success_count"] = 999
        with self.assertRaisesRegex(release_gate.ContractError, "不得超过 labeled_count"):
            release_gate.validate_observations(malformed)

    def test_online_rates_are_derived_from_count_pairs(self) -> None:
        arm = self.observation("obs-healthy")["candidate"]
        rates = release_gate.online_arm_rates(arm)
        self.assertAlmostEqual(198 / 220, rates["task_success_rate"])
        self.assertAlmostEqual(51 / 60, rates["critical_slice_success_rate"])
        self.assertEqual(0.0, rates["safety_violation_rate"])

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
        first = self.decide_candidate(candidate)
        original = first.evidence_fingerprint
        self.assertEqual(original, self.decide_candidate(copy.deepcopy(candidate)).evidence_fingerprint)
        self.assertEqual(64, len(first.evidence_sha256))
        self.assertTrue(first.evidence_sha256.startswith(first.evidence_fingerprint))
        self.assertEqual(first.evidence_digest_format, release_gate.EVIDENCE_DIGEST_FORMAT)
        candidate["metrics"]["p95_latency_ms"] += 1
        self.assertNotEqual(original, self.decide_candidate(candidate).evidence_fingerprint)

    def test_candidate_gate_evidence_excludes_post_gate_promotion_timestamp(self) -> None:
        candidate = self.candidate("release-safe")
        original = self.decide_candidate(candidate).evidence_sha256
        candidate["promoted_at"] = "2026-07-14T05:59:00Z"
        self.assertEqual(original, self.decide_candidate(candidate).evidence_sha256)

    def test_observation_requires_full_candidate_gate_evidence_sha256(self) -> None:
        malformed = copy.deepcopy(self.observation_bundle)
        malformed["observations"][0]["candidate_gate_evidence_sha256"] = "short"
        with self.assertRaisesRegex(release_gate.ContractError, "64 位"):
            release_gate.validate_observations(malformed)

    def test_observation_requires_a_supported_gate_evidence_format(self) -> None:
        malformed = copy.deepcopy(self.observation_bundle)
        malformed["evidence_digest_format"] = "unknown-v9"
        with self.assertRaisesRegex(release_gate.ContractError, "证据摘要格式"):
            release_gate.validate_observations(malformed)

    def test_observation_evidence_digest_binds_bundle_schema_and_format(self) -> None:
        observation = self.observation("obs-healthy")
        bound_candidate = release_gate.bind_observation(self.manifest, observation)
        original = self.decide_observation(observation)
        with patch.object(
            release_gate,
            "ONLINE_OBSERVATION_SCHEMA_VERSION",
            "local-online-observation-v7",
        ):
            schema_changed = release_gate.observation_decision(
                observation,
                self.manifest["policy"],
                "local-online-observation-v7",
                self.observation_bundle["evidence_digest_format"],
                bound_candidate,
            )
        with patch.object(
            release_gate,
            "EVIDENCE_DIGEST_FORMAT",
            "python-json-sorted-utf8-v2",
        ):
            format_changed = release_gate.observation_decision(
                observation,
                self.manifest["policy"],
                self.observation_bundle["schema_version"],
                "python-json-sorted-utf8-v2",
                bound_candidate,
            )
        self.assertNotEqual(original.evidence_sha256, schema_changed.evidence_sha256)
        self.assertNotEqual(original.evidence_sha256, format_changed.evidence_sha256)
        self.assertEqual(
            format_changed.evidence_digest_format,
            "python-json-sorted-utf8-v2",
        )

    def test_observation_rejects_mismatched_full_candidate_gate_evidence(self) -> None:
        observation = self.observation("obs-healthy")
        observation["candidate_gate_evidence_sha256"] = "0" * 64
        with self.assertRaisesRegex(release_gate.ContractError, "完整证据摘要不匹配"):
            release_gate.bind_observation(self.manifest, observation)

    def test_healthy_observation_continues(self) -> None:
        decision = self.decide_observation(self.observation("obs-healthy"))
        self.assertTrue(decision.passed)
        self.assertEqual(decision.action, "continue")

    def test_low_sample_observation_requires_investigation(self) -> None:
        decision = self.decide_observation(self.observation("obs-low-sample"))
        self.assertEqual(decision.action, "investigate")
        self.assertIn("样本量不足", "\n".join(decision.reasons))

    def test_low_label_coverage_requires_investigation(self) -> None:
        observation = self.observation("obs-healthy")
        observation["candidate"]["labeled_count"] = 1
        observation["candidate"]["critical_labeled_count"] = 1
        decision = self.decide_observation(observation)
        self.assertEqual("investigate", decision.action)
        self.assertIn("标签覆盖率", "\n".join(decision.reasons))

    def test_online_quality_uses_concurrent_control_not_offline_baseline(self) -> None:
        observation = self.observation("obs-healthy")
        observation["control"]["task_success_count"] = observation["control"][
            "labeled_count"
        ]
        decision = self.decide_observation(observation)
        self.assertEqual("rollback", decision.action)
        self.assertIn("同期 control", "\n".join(decision.reasons))

    def test_provider_drift_uses_prevalidated_fallback(self) -> None:
        decision = self.decide_observation(self.observation("obs-provider-drift"))
        self.assertEqual(decision.action, "fallback")
        self.assertIn("降级路径", "\n".join(decision.reasons))

    def test_provider_drift_with_insufficient_candidate_evidence_does_not_fallback(self) -> None:
        decision = self.decide_observation(
            self.observation("obs-provider-insufficient-evidence")
        )
        self.assertEqual("human_review", decision.action)
        self.assertIn("不能自动切换", "\n".join(decision.reasons))

    def test_provider_drift_cannot_trust_unbound_observation_evidence(self) -> None:
        observation = self.observation("obs-provider-drift")
        decision = release_gate.observation_decision(
            observation,
            self.manifest["policy"],
            self.observation_bundle["schema_version"],
            self.observation_bundle["evidence_digest_format"],
        )
        self.assertEqual("human_review", decision.action)
        self.assertIn("candidate gate", "\n".join(decision.reasons))

    def test_provider_drift_with_mismatched_fallback_is_rejected_at_binding(self) -> None:
        observation = self.observation("obs-provider-drift")
        observation["fallback_evidence"]["manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(release_gate.ContractError, "fallback evidence"):
            release_gate.bind_observation(self.manifest, observation)

    def test_unused_mismatched_fallback_is_also_rejected_at_binding(self) -> None:
        observation = self.observation("obs-healthy")
        observation["fallback_evidence"]["manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(release_gate.ContractError, "fallback evidence"):
            release_gate.bind_observation(self.manifest, observation)

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
        observation["candidate"]["safety_violation_count"] = 1
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

    def test_cli_keeps_insufficient_provider_evidence_in_human_review(self) -> None:
        with redirect_stdout(io.StringIO()) as stdout:
            code = release_gate.main(
                [
                    "audit",
                    "--release-id",
                    "release-safe",
                    "--observation-id",
                    "obs-provider-insufficient-evidence",
                ]
            )
        self.assertEqual(code, 1)
        self.assertIn("HUMAN_REVIEW", stdout.getvalue())
        self.assertIn("不能自动切换", stdout.getvalue())

    def test_audit_rejects_cross_release_observation_pair(self) -> None:
        with redirect_stderr(io.StringIO()) as stderr:
            code = release_gate.main(
                [
                    "audit",
                    "--release-id",
                    "release-regression",
                    "--observation-id",
                    "obs-healthy",
                ]
            )
        self.assertEqual(2, code)
        self.assertIn("不匹配", stderr.getvalue())

    def test_audit_release_id_requires_at_least_one_bound_observation(self) -> None:
        with redirect_stderr(io.StringIO()) as stderr:
            code = release_gate.main(
                ["audit", "--release-id", "release-regression"]
            )
        self.assertEqual(2, code)
        self.assertIn("至少必须绑定一个线上观察", stderr.getvalue())

    def test_batch_audit_requires_observation_for_each_promoted_candidate(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        unobserved = copy.deepcopy(manifest["candidates"][0])
        unobserved["release_id"] = "release-safe-unobserved"
        unobserved["evaluation"]["subject_release_id"] = "release-safe-unobserved"
        manifest["candidates"].append(unobserved)
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "manifest.json"
            path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            with redirect_stderr(io.StringIO()) as stderr:
                code = release_gate.main(["audit", "--manifest", str(path)])
        self.assertEqual(2, code)
        self.assertIn("缺少线上观察", stderr.getvalue())

    def test_observation_rejects_stale_candidate_gate_fingerprint(self) -> None:
        malformed = copy.deepcopy(self.observation_bundle)
        malformed["observations"][0]["candidate_gate_fingerprint"] = "0" * 16
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "observations.json"
            path.write_text(json.dumps(malformed, ensure_ascii=False), encoding="utf-8")
            with redirect_stderr(io.StringIO()) as stderr:
                code = release_gate.main(
                    [
                        "observe",
                        "--observations",
                        str(path),
                        "--observation-id",
                        "obs-healthy",
                    ]
                )
        self.assertEqual(2, code)
        self.assertIn("指纹不匹配", stderr.getvalue())

    def test_observation_rejects_window_before_candidate_promotion(self) -> None:
        observation = self.observation("obs-healthy")
        observation["window_start"] = "2026-07-13T23:00:00Z"
        observation["window_end"] = "2026-07-13T23:30:00Z"
        with self.assertRaisesRegex(release_gate.ContractError, "promoted_at"):
            release_gate.bind_observation(self.manifest, observation)

    def test_observation_rejects_window_after_fixed_decision_as_of(self) -> None:
        observation = self.observation("obs-healthy")
        observation["window_start"] = "2026-07-14T06:00:00Z"
        observation["window_end"] = "2026-07-14T07:00:00Z"
        with self.assertRaisesRegex(release_gate.ContractError, "decision_as_of"):
            release_gate.bind_observation(self.manifest, observation)

    def test_observation_requires_recorded_candidate_promotion(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        candidate = manifest["candidates"][0]
        candidate["promoted_at"] = None
        observation = self.observation("obs-healthy")
        gate = release_gate.candidate_decision(
            candidate, manifest["baseline"], manifest["policy"]
        )
        observation["candidate_gate_fingerprint"] = gate.evidence_fingerprint
        with self.assertRaisesRegex(release_gate.ContractError, "尚无 promoted_at"):
            release_gate.bind_observation(manifest, observation)

    def test_observation_rejects_wrong_control_release(self) -> None:
        malformed = copy.deepcopy(self.observation_bundle)
        malformed["observations"][0]["control"]["release_id"] = "other-control"
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "observations.json"
            path.write_text(json.dumps(malformed, ensure_ascii=False), encoding="utf-8")
            with redirect_stderr(io.StringIO()) as stderr:
                code = release_gate.main(
                    [
                        "observe",
                        "--observations",
                        str(path),
                        "--observation-id",
                        "obs-healthy",
                    ]
                )
        self.assertEqual(2, code)
        self.assertIn("control release", stderr.getvalue())

    def test_main_returns_two_for_bad_json_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "bad.json"
            path.write_text(json.dumps({"wrong": True}), encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                code = release_gate.main(["candidate", "--manifest", str(path)])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
