"""Offline tests for collaboration_simulator.py."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from collaboration_simulator import CollaborationSimulator, load_scenario


HERE = Path(__file__).resolve().parent


def scenario_with(
    *,
    step_budget: int = 4,
    capabilities: list[str] | None = None,
    tasks: list[dict] | None = None,
) -> dict:
    return {
        "step_budget": step_budget,
        "roles": {
            "worker": {
                "capabilities": capabilities
                if capabilities is not None
                else ["work"]
            }
        },
        "tasks": tasks
        if tasks is not None
        else [
            {
                "id": "job",
                "owner": "worker",
                "requires": [],
                "capability": "work",
                "max_attempts": 1,
                "outcome_plan": ["success"],
            }
        ],
    }


class CollaborationSimulatorTests(unittest.TestCase):
    def test_fixture_completes_after_bounded_retry(self) -> None:
        report = CollaborationSimulator(load_scenario(HERE / "scenario.json")).run()
        self.assertEqual(report["status"], "succeeded")
        self.assertEqual(report["tasks"]["collect"]["attempts"], 2)
        self.assertEqual(report["steps_used"], 4)

    def test_missing_capability_is_denied_and_dependency_blocked(self) -> None:
        data = scenario_with(
            capabilities=[],
            tasks=[
                {
                    "id": "first",
                    "owner": "worker",
                    "requires": [],
                    "capability": "write",
                    "max_attempts": 1,
                    "outcome_plan": ["success"],
                },
                {
                    "id": "second",
                    "owner": "worker",
                    "requires": ["first"],
                    "capability": "work",
                    "max_attempts": 1,
                    "outcome_plan": ["success"],
                },
            ],
        )
        report = CollaborationSimulator(data).run()
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["tasks"]["first"]["state"], "denied")
        self.assertEqual(report["tasks"]["second"]["state"], "blocked")

    def test_global_budget_stops_retry(self) -> None:
        data = scenario_with(
            step_budget=1,
            tasks=[
                {
                    "id": "job",
                    "owner": "worker",
                    "requires": [],
                    "capability": "work",
                    "max_attempts": 3,
                    "outcome_plan": ["transient_error", "success"],
                }
            ],
        )
        report = CollaborationSimulator(data).run()
        self.assertEqual(report["status"], "budget_exhausted")
        self.assertEqual(report["tasks"]["job"]["attempts"], 1)

    def test_cycle_is_reported_as_deadlock(self) -> None:
        tasks = [
            {
                "id": "a",
                "owner": "worker",
                "requires": ["b"],
                "capability": "work",
                "max_attempts": 1,
                "outcome_plan": ["success"],
            },
            {
                "id": "b",
                "owner": "worker",
                "requires": ["a"],
                "capability": "work",
                "max_attempts": 1,
                "outcome_plan": ["success"],
            },
        ]
        report = CollaborationSimulator(scenario_with(tasks=tasks)).run()
        self.assertEqual(report["status"], "deadlock")
        self.assertEqual(report["steps_used"], 0)

    def test_duplicate_success_is_ignored(self) -> None:
        simulator = CollaborationSimulator(scenario_with())
        first = simulator.accept_result("job", "same-key", {"value": 1})
        second = simulator.accept_result("job", "same-key", {"value": 2})
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(simulator.tasks["job"]["result"], {"value": 1})
        self.assertEqual(simulator.events[-1]["event"], "duplicate_result_ignored")

    def test_utf8_json_round_trip_uses_temp_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "场景.json"
            path.write_text(
                json.dumps(scenario_with(), ensure_ascii=False), encoding="utf-8"
            )
            report = CollaborationSimulator(load_scenario(path)).run()
        self.assertEqual(report["status"], "succeeded")


if __name__ == "__main__":
    unittest.main(verbosity=2)

