"""离线运行监控审计的标准库回归测试。"""

from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import monitor_audit


class MonitorAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = monitor_audit.validate_input(
            monitor_audit.load_json(monitor_audit.DEFAULT_INPUT)
        )

    def scenario(self, name: str) -> dict[str, object]:
        return copy.deepcopy(
            next(item for item in self.data["scenarios"] if item["name"] == name)
        )

    def decide(self, scenario: dict[str, object]) -> monitor_audit.Decision:
        return monitor_audit.evaluate_scenario(
            scenario, self.data["policy"], self.data["slo"]
        )

    def validate_changed_scenario(self, scenario: dict[str, object]) -> dict[str, object]:
        data = copy.deepcopy(self.data)
        data["scenarios"] = [scenario]
        return monitor_audit.validate_input(data)["scenarios"][0]

    def test_fixtures_validate(self) -> None:
        self.assertEqual([item["name"] for item in self.data["scenarios"]], ["stable-window", "incident-window"])
        self.assertEqual("local-monitor-policy-v3", self.data["policy"]["version"])

    def test_stable_scenario_is_ok(self) -> None:
        decision = self.decide(self.scenario("stable-window"))
        self.assertTrue(decision.passed)
        self.assertEqual(decision.action, "ok")
        self.assertEqual(decision.reasons, ())
        self.assertIsNone(decision.regression_handoff)

    def test_incident_scenario_pages(self) -> None:
        decision = self.decide(self.scenario("incident-window"))
        self.assertEqual(decision.action, "page")
        joined = "\n".join(decision.reasons)
        self.assertIn("错误预算", joined)
        self.assertIn("Collector", joined)
        self.assertIn("Trace", joined)
        self.assertIn("USE", joined)

    def test_burn_rate_uses_slo_allowed_bad_fraction(self) -> None:
        scenario = self.scenario("incident-window")
        indicators = monitor_audit.calculate_indicators(scenario, self.data["slo"])
        self.assertAlmostEqual(float(indicators["short_burn_rate"]), 5.0)
        self.assertAlmostEqual(float(indicators["long_burn_rate"]), 2.5)
        self.assertAlmostEqual(float(indicators["slo_bad_event_fraction"]), 0.5)
        self.assertNotIn("error_budget_remaining_ratio", indicators)

    def test_event_data_age_is_explicit_and_uses_declared_window_end(self) -> None:
        scenario = self.scenario("stable-window")
        indicators = monitor_audit.calculate_indicators(scenario, self.data["slo"])
        self.assertEqual(60.0, indicators["event_data_age_seconds"])

    def test_stale_event_data_pages_even_when_collector_is_fresh(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["events"][-1]["timestamp"] = "2026-07-14T08:58:00Z"
        scenario["collector"]["last_export_age_seconds"] = 1
        decision = self.decide(scenario)
        self.assertEqual("page", decision.action)
        self.assertIn("最新业务事件", "\n".join(decision.reasons))

    def test_incident_creates_content_free_regression_handoff(self) -> None:
        decision = self.decide(self.scenario("incident-window"))
        handoff = decision.regression_handoff
        self.assertIsNotNone(handoff)
        if handoff is None:
            self.fail("incident 必须产生待人工分诊的回归候选")
        self.assertEqual(handoff["status"], "needs_human_triage")
        self.assertEqual(handoff["release_id"], "agent-release-v4")
        self.assertEqual(len(str(handoff["monitor_evidence_sha256"])), 64)
        self.assertEqual(
            handoff["monitor_evidence_digest_format"],
            monitor_audit.EVIDENCE_DIGEST_FORMAT,
        )
        self.assertEqual(
            handoff["candidate_gate_evidence_digest_format"],
            monitor_audit.EVIDENCE_DIGEST_FORMAT,
        )
        self.assertFalse(bool(handoff["raw_content_included"]))
        self.assertEqual(len(handoff["source_trace_ids"]), 2)

    def test_nearest_rank_percentile(self) -> None:
        self.assertEqual(monitor_audit.nearest_rank_percentile([1, 3, 2, 4], 0.75), 3)

    def test_empty_percentile_input_is_rejected(self) -> None:
        with self.assertRaisesRegex(monitor_audit.ContractError, "不能为空"):
            monitor_audit.nearest_rank_percentile([], 0.95)

    def test_unknown_top_level_field_is_rejected(self) -> None:
        malformed = copy.deepcopy(self.data)
        malformed["unexpected"] = True
        with self.assertRaisesRegex(monitor_audit.ContractError, "未知字段"):
            monitor_audit.validate_input(malformed)

    def test_disallowed_high_cardinality_metric_label_is_rejected(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["metric_label_keys"].append("request_id")
        with self.assertRaisesRegex(monitor_audit.ContractError, "高基数字段"):
            self.validate_changed_scenario(scenario)

    def test_release_evidence_cannot_be_used_as_metric_label(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["metric_label_keys"].append("candidate_gate_evidence_sha256")
        with self.assertRaisesRegex(monitor_audit.ContractError, "高基数字段"):
            self.validate_changed_scenario(scenario)

    def test_release_evidence_must_bind_every_event(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["release_evidence"]["release_id"] = "different-release"
        with self.assertRaisesRegex(monitor_audit.ContractError, "绑定全部事件"):
            self.validate_changed_scenario(scenario)

    def test_release_evidence_requires_full_sha256(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["release_evidence"]["candidate_gate_evidence_sha256"] = "short"
        with self.assertRaisesRegex(monitor_audit.ContractError, "64 位"):
            self.validate_changed_scenario(scenario)

    def test_release_evidence_requires_a_supported_digest_format(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["release_evidence"]["candidate_gate_evidence_digest_format"] = "unknown-v9"
        with self.assertRaisesRegex(monitor_audit.ContractError, "证据摘要格式"):
            self.validate_changed_scenario(scenario)

    def test_evidence_digest_golden_vector_matches_the_shared_teaching_profile(self) -> None:
        self.assertEqual(
            monitor_audit.EVIDENCE_DIGEST_FORMAT,
            "python-json-sorted-utf8-v1",
        )
        actual = monitor_audit.full_evidence_sha256(
            {"z": "\u6c49\u5b57", "a": [1, 2.5], "nested": {"\u03b2": "\u503c"}},
            "release-v1",
        )
        self.assertEqual(
            actual,
            "ee2f7ef27b87716fd2359ee2f42aae77a38d58792636bf959292c885242152d6",
        )

    def test_duplicate_request_id_is_rejected(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["events"][1]["request_id"] = scenario["events"][0]["request_id"]
        with self.assertRaisesRegex(monitor_audit.ContractError, "重复 request_id"):
            self.validate_changed_scenario(scenario)

    def test_timestamp_without_timezone_is_rejected(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["events"][0]["timestamp"] = "2026-07-14T08:00:00"
        with self.assertRaisesRegex(monitor_audit.ContractError, "包含时区"):
            self.validate_changed_scenario(scenario)

    def test_unsorted_events_are_rejected(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["events"][0], scenario["events"][1] = scenario["events"][1], scenario["events"][0]
        with self.assertRaisesRegex(monitor_audit.ContractError, "升序"):
            self.validate_changed_scenario(scenario)

    def test_short_window_must_be_shorter(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["short_window_minutes"] = scenario["window_minutes"]
        with self.assertRaisesRegex(monitor_audit.ContractError, "必须小于"):
            self.validate_changed_scenario(scenario)

    def test_window_end_is_required_and_bounds_events(self) -> None:
        missing = self.scenario("stable-window")
        del missing["window_end"]
        with self.assertRaisesRegex(monitor_audit.ContractError, "缺少字段: window_end"):
            self.validate_changed_scenario(missing)

        outside = self.scenario("stable-window")
        outside["events"][0]["timestamp"] = "2026-07-14T07:59:00Z"
        with self.assertRaisesRegex(monitor_audit.ContractError, "window_end"):
            self.validate_changed_scenario(outside)

    def test_boolean_is_not_a_number(self) -> None:
        malformed = copy.deepcopy(self.data)
        malformed["policy"]["max_p95_latency_ms"] = True
        with self.assertRaisesRegex(monitor_audit.ContractError, "必须是数值"):
            monitor_audit.validate_input(malformed)

    def test_slo_good_statuses_must_match_event_status_enum(self) -> None:
        malformed = copy.deepcopy(self.data)
        malformed["slo"]["good_statuses"] = ["accepted"]
        with self.assertRaisesRegex(monitor_audit.ContractError, "事件契约之外"):
            monitor_audit.validate_input(malformed)

    def test_non_finite_number_is_rejected(self) -> None:
        malformed = copy.deepcopy(self.data)
        malformed["policy"]["max_p95_latency_ms"] = float("inf")
        with self.assertRaisesRegex(monitor_audit.ContractError, "有限数值"):
            monitor_audit.validate_input(malformed)

    def test_overflowing_integer_is_a_contract_error(self) -> None:
        malformed = copy.deepcopy(self.data)
        malformed["policy"]["max_p95_latency_ms"] = 10**400
        with self.assertRaisesRegex(monitor_audit.ContractError, "可表示为有限数值"):
            monitor_audit.validate_input(malformed)

    def test_nonstandard_json_nan_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "nan.json"
            path.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(monitor_audit.ContractError, "JSON 标准之外"):
                monitor_audit.load_json(path)

    def test_non_utf8_input_is_a_contract_error_at_load_and_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "surrogate.json"
            path.write_text('{"value": "\\ud800"}', encoding="utf-8")
            with self.assertRaisesRegex(monitor_audit.ContractError, "Unicode surrogate"):
                monitor_audit.load_json(path)
            path.write_text('{"\\ud800": 1}', encoding="utf-8")
            with self.assertRaisesRegex(monitor_audit.ContractError, "Unicode surrogate"):
                monitor_audit.load_json(path)
            path.write_bytes(b'{"value":"\xff"}')
            with self.assertRaisesRegex(monitor_audit.ContractError, "有效 UTF-8 JSON"):
                monitor_audit.load_json(path)
        with self.assertRaisesRegex(monitor_audit.ContractError, "Unicode surrogate"):
            monitor_audit.full_evidence_sha256({"value": "\ud800"})

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "duplicate.json"
            path.write_text(
                '{"policy": {}, "policy": {}, "slo": {}, "scenarios": []}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                monitor_audit.ContractError, "重复 JSON 字段: policy"
            ):
                monitor_audit.load_json(path)

    def test_invalid_traceparent_is_rejected(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["traces"][0]["traceparent"] = scenario["traces"][0]["traceparent"].upper()
        with self.assertRaisesRegex(monitor_audit.ContractError, "traceparent"):
            self.validate_changed_scenario(scenario)

    def test_traceparent_trace_id_must_match(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["traces"][0]["traceparent"] = (
            "00-90000000000000000000000000000009-a000000000000001-01"
        )
        with self.assertRaisesRegex(monitor_audit.ContractError, "匹配 trace_id"):
            self.validate_changed_scenario(scenario)

    def test_trace_with_unknown_parent_is_rejected(self) -> None:
        scenario = self.scenario("stable-window")
        child = copy.deepcopy(scenario["traces"][0]["spans"][0])
        child["span_id"] = "3000000000000001"
        child["parent_span_id"] = "9000000000000009"
        child["attributes"]["operation_type"] = "model"
        scenario["traces"][0]["spans"].append(child)
        with self.assertRaisesRegex(monitor_audit.ContractError, "未知 parent_span_id"):
            self.validate_changed_scenario(scenario)

    def test_trace_parent_cycle_is_rejected(self) -> None:
        scenario = self.scenario("stable-window")
        first = copy.deepcopy(scenario["traces"][0]["spans"][0])
        first["span_id"] = "3000000000000001"
        first["parent_span_id"] = "3000000000000002"
        first["attributes"]["operation_type"] = "model"
        second = copy.deepcopy(first)
        second["span_id"] = "3000000000000002"
        second["parent_span_id"] = "3000000000000001"
        scenario["traces"][0]["spans"].extend([first, second])
        with self.assertRaisesRegex(monitor_audit.ContractError, "父子环"):
            self.validate_changed_scenario(scenario)

    def test_root_span_status_must_match_event(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["traces"][0]["spans"][0]["status"] = "error"
        with self.assertRaisesRegex(monitor_audit.ContractError, "status 与事件不一致"):
            self.validate_changed_scenario(scenario)

    def test_event_cannot_reference_missing_trace(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["traces"].pop()
        with self.assertRaisesRegex(monitor_audit.ContractError, "不存在的 trace"):
            self.validate_changed_scenario(scenario)

    def test_unreferenced_trace_is_rejected(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["events"][0]["trace_id"] = None
        with self.assertRaisesRegex(monitor_audit.ContractError, "未被事件引用"):
            self.validate_changed_scenario(scenario)

    def test_collector_queue_cannot_exceed_capacity(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["collector"]["queue_size"] = 51
        with self.assertRaisesRegex(monitor_audit.ContractError, "不能超过"):
            self.validate_changed_scenario(scenario)

    def test_safety_contradiction_is_rejected(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["events"][0]["safety_checked"] = False
        scenario["events"][0]["safety_violation"] = True
        with self.assertRaisesRegex(monitor_audit.ContractError, "未检查安全"):
            self.validate_changed_scenario(scenario)

    def test_content_capture_policy_pages_even_when_sli_is_healthy(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["telemetry_policy"]["content_capture_enabled"] = True
        decision = self.decide(scenario)
        self.assertEqual(decision.action, "page")
        self.assertIn("原始内容", "\n".join(decision.reasons))

    def test_low_label_coverage_creates_ticket(self) -> None:
        scenario = self.scenario("stable-window")
        for event in scenario["events"]:
            event["quality_pass"] = None
        decision = self.decide(scenario)
        self.assertEqual(decision.action, "ticket")
        self.assertIn("质量", "\n".join(decision.reasons))

    def test_safety_unknown_pages(self) -> None:
        scenario = self.scenario("stable-window")
        for event in scenario["events"]:
            event["safety_checked"] = False
        decision = self.decide(scenario)
        self.assertEqual(decision.action, "page")
        self.assertIn("安全状态未知", "\n".join(decision.reasons))

    def test_page_has_priority_over_ticket(self) -> None:
        scenario = self.scenario("stable-window")
        scenario["telemetry_policy"]["redaction_check_passed"] = False
        scenario["resources"]["queue_depth"] = 99
        self.assertEqual(self.decide(scenario).action, "page")

    def test_evidence_fingerprint_is_stable_and_sensitive(self) -> None:
        scenario = self.scenario("stable-window")
        first = self.decide(scenario)
        original = first.evidence_fingerprint
        self.assertEqual(original, self.decide(copy.deepcopy(scenario)).evidence_fingerprint)
        self.assertEqual(64, len(first.evidence_sha256))
        self.assertTrue(first.evidence_sha256.startswith(first.evidence_fingerprint))
        self.assertEqual(first.evidence_digest_format, monitor_audit.EVIDENCE_DIGEST_FORMAT)
        scenario["resources"]["queue_depth"] += 1
        self.assertNotEqual(original, self.decide(scenario).evidence_fingerprint)

    def test_main_exit_codes(self) -> None:
        with redirect_stdout(io.StringIO()):
            ok_code = monitor_audit.main(["--scenario", "stable-window"])
            incident_code = monitor_audit.main(["--scenario", "incident-window"])
        self.assertEqual(ok_code, 0)
        self.assertEqual(incident_code, 1)

    def test_main_returns_two_for_bad_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "bad.json"
            path.write_text(json.dumps({"wrong": True}), encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                code = monitor_audit.main(["--input", str(path)])
        self.assertEqual(code, 2)

    def test_main_returns_two_for_unknown_scenario(self) -> None:
        with redirect_stderr(io.StringIO()):
            code = monitor_audit.main(["--scenario", "missing-window"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
