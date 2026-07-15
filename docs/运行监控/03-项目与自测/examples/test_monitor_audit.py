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

    def test_stable_scenario_is_ok(self) -> None:
        decision = self.decide(self.scenario("stable-window"))
        self.assertTrue(decision.passed)
        self.assertEqual(decision.action, "ok")
        self.assertEqual(decision.reasons, ())

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

    def test_boolean_is_not_a_number(self) -> None:
        malformed = copy.deepcopy(self.data)
        malformed["policy"]["max_p95_latency_ms"] = True
        with self.assertRaisesRegex(monitor_audit.ContractError, "必须是数值"):
            monitor_audit.validate_input(malformed)

    def test_non_finite_number_is_rejected(self) -> None:
        malformed = copy.deepcopy(self.data)
        malformed["policy"]["max_p95_latency_ms"] = float("inf")
        with self.assertRaisesRegex(monitor_audit.ContractError, "有限数值"):
            monitor_audit.validate_input(malformed)

    def test_nonstandard_json_nan_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "nan.json"
            path.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(monitor_audit.ContractError, "JSON 标准之外"):
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
        original = self.decide(scenario).evidence_fingerprint
        self.assertEqual(original, self.decide(copy.deepcopy(scenario)).evidence_fingerprint)
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
