"""Tests for the offline model-selection scorecard."""

from __future__ import annotations

from collections import Counter
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

import model_selection_scorecard as scorecard


class ModelSelectionScorecardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_path = Path(__file__).with_name("model_candidates.json")
        cls.raw = json.loads(cls.fixture_path.read_text(encoding="utf-8"))

    def write_fixture(self, root: Path, raw: dict[str, object]) -> Path:
        path = root / "fixture.json"
        path.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def load_raw(self, raw: dict[str, object]) -> scorecard.Fixture:
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write_fixture(Path(temporary), raw)
            return scorecard.load_fixture(path)

    def evaluate_raw(self, raw: dict[str, object]) -> dict[str, object]:
        return scorecard.evaluate(self.load_raw(raw))

    def test_fixture_produces_expected_gates_and_frontier(self) -> None:
        result = scorecard.evaluate(scorecard.load_fixture(self.fixture_path))
        self.assertEqual(
            [item["id"] for item in result["eligible"]],
            ["candidate-a", "candidate-b", "candidate-c"],
        )
        self.assertEqual(
            [item["id"] for item in result["ineligible"]],
            ["candidate-d", "candidate-e"],
        )
        self.assertEqual(
            result["pareto_frontier"], ["candidate-a", "candidate-b"]
        )
        pareto_by_id = {
            item["id"]: item["pareto"] for item in result["eligible"]
        }
        self.assertFalse(pareto_by_id["candidate-c"])

    def test_fixture_repeats_each_case_with_global_trial_ids(self) -> None:
        fixture = scorecard.load_fixture(self.fixture_path)
        all_trial_ids: list[str] = []
        for candidate in fixture.candidates:
            counts = Counter(trial.case_id for trial in candidate.trials)
            self.assertEqual(counts, {"case-01": 3, "case-02": 3})
            all_trial_ids.extend(trial.trial_id for trial in candidate.trials)
        self.assertEqual(len(all_trial_ids), len(set(all_trial_ids)))
        metrics = scorecard.aggregate_metrics(
            fixture.candidates[0], fixture.decision
        )
        self.assertEqual(metrics.trial_count, 6)
        self.assertEqual(metrics.case_count, 2)
        self.assertEqual(metrics.min_trials_per_case, 3)

    def test_behavior_gates_prevent_fast_cheap_candidate_from_scoring(self) -> None:
        result = scorecard.evaluate(scorecard.load_fixture(self.fixture_path))
        rejected = next(
            item for item in result["ineligible"] if item["id"] == "candidate-d"
        )
        self.assertNotIn("score", rejected)
        self.assertEqual(
            rejected["gate_failures"],
            [
                "structured_output_below_minimum",
                "tool_success_below_minimum",
            ],
        )
        self.assertLess(rejected["metrics"]["avg_cost_usd"], 0.005)

    def test_measured_structure_gate_is_independent_of_capability_label(self) -> None:
        raw = copy.deepcopy(self.raw)
        trial = raw["candidates"][0]["trials"][0]
        trial["structured_output_valid"] = False
        trial["task_success"] = False
        result = self.evaluate_raw(raw)
        rejected = next(
            item for item in result["ineligible"] if item["id"] == "candidate-a"
        )
        self.assertEqual(
            rejected["gate_failures"], ["structured_output_below_minimum"]
        )
        self.assertNotIn("score", rejected)

    def test_behavior_threshold_only_applies_when_capability_is_required(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["decision"]["required_capabilities"] = ["tool-calling"]
        trial = raw["candidates"][0]["trials"][0]
        trial["structured_output_valid"] = False
        trial["task_success"] = False
        result = self.evaluate_raw(raw)
        eligible_ids = {item["id"] for item in result["eligible"]}
        self.assertIn("candidate-a", eligible_ids)

    def test_blocked_evidence_is_a_candidate_gate_not_fixture_failure(self) -> None:
        result = scorecard.evaluate(scorecard.load_fixture(self.fixture_path))
        rejected = next(
            item for item in result["ineligible"] if item["id"] == "candidate-e"
        )
        self.assertEqual(
            rejected["gate_failures"],
            [
                "evidence_status_blocked",
                "evidence_missing:data-retention-contract",
                "evidence_missing:regional-processing-proof",
            ],
        )
        self.assertEqual(rejected["metrics"]["task_success"], 1.0)
        self.assertNotIn("score", rejected)

    def test_expired_evidence_is_a_candidate_gate(self) -> None:
        raw = copy.deepcopy(self.raw)
        evidence = raw["candidates"][4]["evidence"]
        evidence.update(
            {
                "status": "verified",
                "uri": "urn:fixture:model-card:candidate-e",
                "checked_on": "2026-07-16",
                "expires_on": "2026-07-17",
                "missing_items": [],
            }
        )
        result = self.evaluate_raw(raw)
        rejected = next(
            item for item in result["ineligible"] if item["id"] == "candidate-e"
        )
        self.assertEqual(rejected["gate_failures"], ["evidence_expired"])

    def test_declared_weight_scenarios_change_the_winner(self) -> None:
        result = scorecard.evaluate(scorecard.load_fixture(self.fixture_path))
        winners = {
            entry["name"]: entry["ranking"][0]["id"]
            for entry in result["sensitivity"]
        }
        self.assertEqual(winners["baseline"], "candidate-b")
        self.assertEqual(winners["quality-priority"], "candidate-a")
        self.assertEqual(winners["efficiency-priority"], "candidate-b")
        self.assertEqual(
            result["sensitivity_scope"], "declared_weight_sets_only"
        )
        self.assertFalse(result["winner_stable_across_declared_weights"])

    def test_p95_uses_nearest_rank_over_recorded_trials(self) -> None:
        fixture = scorecard.load_fixture(self.fixture_path)
        metrics = scorecard.aggregate_metrics(
            fixture.candidates[0], fixture.decision
        )
        self.assertEqual(metrics.p95_latency_ms, 1300)

    def test_unknown_field_is_rejected(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["candidates"][0]["marketing_rank"] = 1
        with self.assertRaisesRegex(scorecard.ScorecardError, "unknown"):
            self.load_raw(raw)

    def test_malformed_evidence_schema_is_rejected(self) -> None:
        raw = copy.deepcopy(self.raw)
        del raw["candidates"][0]["evidence"]["owner"]
        with self.assertRaisesRegex(scorecard.ScorecardError, "missing"):
            self.load_raw(raw)

    def test_verified_evidence_cannot_claim_missing_items(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["candidates"][0]["evidence"]["missing_items"] = ["contract"]
        with self.assertRaisesRegex(scorecard.ScorecardError, "cannot contain"):
            self.load_raw(raw)

    def test_duplicate_json_key_and_non_finite_number_are_rejected(self) -> None:
        with self.assertRaisesRegex(scorecard.ScorecardError, "duplicate JSON key"):
            scorecard.parse_json_strict('{"a": 1, "a": 2}', "inline")
        with self.assertRaisesRegex(scorecard.ScorecardError, "non-finite"):
            scorecard.parse_json_strict('{"a": NaN}', "inline")

    def test_global_duplicate_trial_id_is_rejected(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["candidates"][1]["trials"][0]["trial_id"] = (
            raw["candidates"][0]["trials"][0]["trial_id"]
        )
        with self.assertRaisesRegex(scorecard.ScorecardError, "globally unique"):
            self.load_raw(raw)

    def test_inconsistent_case_multiplicities_are_rejected(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["candidates"][1]["trials"].pop()
        with self.assertRaisesRegex(scorecard.ScorecardError, "multiplicities"):
            self.load_raw(raw)

    def test_minimum_trials_is_enforced_per_case(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["decision"]["min_trials_per_case"] = 4
        result = self.evaluate_raw(raw)
        rejected = next(
            item for item in result["ineligible"] if item["id"] == "candidate-a"
        )
        self.assertEqual(
            rejected["gate_failures"],
            [
                "insufficient_trials_per_case:case-01",
                "insufficient_trials_per_case:case-02",
            ],
        )

    def test_required_invalid_structure_cannot_be_success(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["candidates"][0]["trials"][0]["structured_output_valid"] = False
        with self.assertRaisesRegex(scorecard.ScorecardError, "task_success=true"):
            self.load_raw(raw)

    def test_invalid_weights_are_rejected(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["decision"]["weights"]["task_success"] = 0.2
        with self.assertRaisesRegex(scorecard.ScorecardError, "sum to 1"):
            self.load_raw(raw)

    def test_cli_success_emits_decision_order_and_scope(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = scorecard.run(
            ["--fixture", str(self.fixture_path)],
            stdout=stdout,
            stderr=stderr,
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["decision_order"][1], "hard_gates")
        self.assertEqual(
            result["sensitivity_scope"], "declared_weight_sets_only"
        )

    def test_cli_expected_failure_returns_two_without_traceback(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["decision"]["weights"]["unknown-metric"] = 0.0
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write_fixture(Path(temporary), raw)
            stdout = io.StringIO()
            stderr = io.StringIO()
            exit_code = scorecard.run(
                ["--fixture", str(path)], stdout=stdout, stderr=stderr
            )
        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("scorecard error", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
