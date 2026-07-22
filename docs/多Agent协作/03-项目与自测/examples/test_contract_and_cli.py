"""Contract, state-machine, and CLI tests for collaboration_simulator.py."""

from __future__ import annotations

import ast
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import collaboration_simulator as app


def valid_scenario() -> dict:
    return {
        "step_budget": 4,
        "roles": {"worker": {"capabilities": ["work"]}},
        "tasks": [
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


class ContractAndCliTests(unittest.TestCase):
    @staticmethod
    def make_running(simulator: app.CollaborationSimulator, task_id: str) -> None:
        """Put a task in the same state as an in-flight external result."""
        simulator._transition(task_id, "running", "test_setup")

    def write_text(self, text: str) -> Path:
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        )
        with handle:
            handle.write(text)
        path = Path(handle.name)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def write_scenario(self, scenario: object) -> Path:
        return self.write_text(json.dumps(scenario, ensure_ascii=False))

    def run_main(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = app.main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def expect_error(self, scenario: object) -> None:
        with self.assertRaises(app.ScenarioError):
            app.CollaborationSimulator(scenario)  # type: ignore[arg-type]

    def test_01_duplicate_json_key_rejected(self) -> None:
        path = self.write_text('{"step_budget":1,"step_budget":2}')
        with self.assertRaisesRegex(app.ScenarioError, r"duplicate JSON key"):
            app.load_scenario(path)

    def test_02_nonstandard_json_constant_rejected(self) -> None:
        path = self.write_text('{"step_budget":NaN}')
        with self.assertRaisesRegex(app.ScenarioError, r"non-standard JSON constant"):
            app.load_scenario(path)

    def test_03_invalid_json_rejected(self) -> None:
        path = self.write_text("{")
        with self.assertRaisesRegex(app.ScenarioError, r"invalid JSON"):
            app.load_scenario(path)

    def test_04_missing_file_wrapped_as_scenario_error(self) -> None:
        with self.assertRaisesRegex(app.ScenarioError, r"cannot read"):
            app.load_scenario(Path("definitely-missing-scenario.json"))

    def test_05_json_root_must_be_object(self) -> None:
        path = self.write_text("[]")
        with self.assertRaisesRegex(app.ScenarioError, r"root must be an object"):
            app.load_scenario(path)

    def test_06_top_fields_are_exact(self) -> None:
        scenario = valid_scenario()
        scenario["extra"] = True
        self.expect_error(scenario)

    def test_07_missing_top_field_rejected(self) -> None:
        scenario = valid_scenario()
        del scenario["roles"]
        self.expect_error(scenario)

    def test_08_budget_must_be_positive_integer(self) -> None:
        for invalid in (0, -1, True, "4"):
            scenario = valid_scenario()
            scenario["step_budget"] = invalid
            with self.subTest(invalid=invalid):
                self.expect_error(scenario)

    def test_09_roles_must_be_nonempty_object(self) -> None:
        scenario = valid_scenario()
        scenario["roles"] = {}
        self.expect_error(scenario)

    def test_10_role_name_must_be_nonempty(self) -> None:
        scenario = valid_scenario()
        scenario["roles"] = {"": {"capabilities": []}}
        self.expect_error(scenario)

    def test_11_role_spec_must_be_object(self) -> None:
        scenario = valid_scenario()
        scenario["roles"] = {"worker": []}
        self.expect_error(scenario)

    def test_12_role_fields_are_exact(self) -> None:
        scenario = valid_scenario()
        scenario["roles"]["worker"]["prompt"] = "hidden"
        self.expect_error(scenario)

    def test_13_capabilities_must_be_array(self) -> None:
        scenario = valid_scenario()
        scenario["roles"]["worker"]["capabilities"] = "work"
        self.expect_error(scenario)

    def test_14_capabilities_must_be_nonempty_strings(self) -> None:
        scenario = valid_scenario()
        scenario["roles"]["worker"]["capabilities"] = [""]
        self.expect_error(scenario)

    def test_15_capabilities_must_be_unique(self) -> None:
        scenario = valid_scenario()
        scenario["roles"]["worker"]["capabilities"] = ["work", "work"]
        self.expect_error(scenario)

    def test_16_tasks_must_be_nonempty_array(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"] = []
        self.expect_error(scenario)

    def test_17_each_task_must_be_object(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"] = ["job"]
        self.expect_error(scenario)

    def test_18_missing_task_field_rejected(self) -> None:
        scenario = valid_scenario()
        del scenario["tasks"][0]["capability"]
        self.expect_error(scenario)

    def test_19_unknown_task_field_rejected(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"][0]["secret"] = True
        self.expect_error(scenario)

    def test_20_task_id_must_be_nonempty(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"][0]["id"] = ""
        self.expect_error(scenario)

    def test_21_task_ids_must_be_unique(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"].append(copy.deepcopy(scenario["tasks"][0]))
        self.expect_error(scenario)

    def test_22_task_owner_must_exist(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"][0]["owner"] = "missing"
        self.expect_error(scenario)

    def test_23_requires_must_be_array_of_nonempty_strings(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"][0]["requires"] = [""]
        self.expect_error(scenario)

    def test_24_requires_must_be_unique(self) -> None:
        scenario = valid_scenario()
        second = copy.deepcopy(scenario["tasks"][0])
        second["id"] = "second"
        scenario["tasks"].append(second)
        scenario["tasks"][0]["requires"] = ["second", "second"]
        self.expect_error(scenario)

    def test_25_capability_must_be_nonempty(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"][0]["capability"] = ""
        self.expect_error(scenario)

    def test_26_max_attempts_must_be_positive_integer(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"][0]["max_attempts"] = True
        self.expect_error(scenario)

    def test_27_outcome_plan_must_be_nonempty(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"][0]["outcome_plan"] = []
        self.expect_error(scenario)

    def test_28_unsupported_outcome_rejected_during_validation(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"][0]["outcome_plan"] = ["invented"]
        self.expect_error(scenario)

    def test_29_unknown_dependency_rejected(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"][0]["requires"] = ["missing"]
        self.expect_error(scenario)

    def test_30_self_dependency_rejected(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"][0]["requires"] = ["job"]
        self.expect_error(scenario)

    def test_31_permanent_error_fails_task(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"][0]["outcome_plan"] = ["permanent_error"]
        report = app.CollaborationSimulator(scenario).run()
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["tasks"]["job"]["state"], "failed")

    def test_32_policy_denied_denies_task(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"][0]["outcome_plan"] = ["policy_denied"]
        report = app.CollaborationSimulator(scenario).run()
        self.assertEqual(report["tasks"]["job"]["state"], "denied")

    def test_33_transient_error_exhaustion_fails(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"][0]["max_attempts"] = 2
        scenario["tasks"][0]["outcome_plan"] = ["transient_error"]
        report = app.CollaborationSimulator(scenario).run()
        self.assertEqual(report["tasks"]["job"]["attempts"], 2)
        self.assertEqual(report["tasks"]["job"]["state"], "failed")

    def test_34_failed_dependency_blocks_downstream(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"][0]["outcome_plan"] = ["permanent_error"]
        second = copy.deepcopy(scenario["tasks"][0])
        second.update(id="downstream", requires=["job"], outcome_plan=["success"])
        scenario["tasks"].append(second)
        report = app.CollaborationSimulator(scenario).run()
        self.assertEqual(report["tasks"]["downstream"]["state"], "blocked")

    def test_35_ready_tasks_are_deterministically_sorted(self) -> None:
        scenario = valid_scenario()
        first = scenario["tasks"][0]
        first["id"] = "z-task"
        second = copy.deepcopy(first)
        second["id"] = "a-task"
        scenario["tasks"].append(second)
        report = app.CollaborationSimulator(scenario).run()
        starts = [event["task_id"] for event in report["events"] if event["event"] == "attempt_started"]
        self.assertEqual(starts, ["a-task", "z-task"])

    def test_36_same_idempotency_text_is_scoped_per_task(self) -> None:
        scenario = valid_scenario()
        second = copy.deepcopy(scenario["tasks"][0])
        second["id"] = "other"
        scenario["tasks"].append(second)
        simulator = app.CollaborationSimulator(scenario)
        self.make_running(simulator, "job")
        self.make_running(simulator, "other")
        self.assertTrue(simulator.accept_result("job", "key", {"v": 1}))
        self.assertTrue(simulator.accept_result("other", "key", {"v": 2}))

    def test_37_late_result_with_new_key_is_ignored(self) -> None:
        simulator = app.CollaborationSimulator(valid_scenario())
        self.make_running(simulator, "job")
        self.assertTrue(simulator.accept_result("job", "first", {"v": 1}))
        self.assertFalse(simulator.accept_result("job", "second", {"v": 2}))
        self.assertEqual(simulator.events[-1]["event"], "late_result_ignored")

    def test_38_unknown_result_task_rejected(self) -> None:
        simulator = app.CollaborationSimulator(valid_scenario())
        with self.assertRaises(app.ScenarioError):
            simulator.accept_result("missing", "key", {})

    def test_39_empty_idempotency_key_rejected(self) -> None:
        simulator = app.CollaborationSimulator(valid_scenario())
        with self.assertRaises(app.ScenarioError):
            simulator.accept_result("job", "", {})

    def test_40_result_payload_is_deep_copied(self) -> None:
        simulator = app.CollaborationSimulator(valid_scenario())
        self.make_running(simulator, "job")
        payload = {"nested": [1]}
        simulator.accept_result("job", "key", payload)
        payload["nested"].append(2)
        self.assertEqual(simulator.tasks["job"]["result"], {"nested": [1]})

    def test_51_result_requires_running_state(self) -> None:
        simulator = app.CollaborationSimulator(valid_scenario())
        with self.assertRaisesRegex(app.ScenarioError, r"while pending"):
            simulator.accept_result("job", "key", {"v": 1})

    def test_52_same_key_with_reordered_json_is_a_safe_duplicate(self) -> None:
        simulator = app.CollaborationSimulator(valid_scenario())
        self.make_running(simulator, "job")
        self.assertTrue(simulator.accept_result("job", "key", {"a": 1, "b": 2}))
        self.assertFalse(simulator.accept_result("job", "key", {"b": 2, "a": 1}))
        self.assertEqual(simulator.tasks["job"]["state"], "succeeded")
        self.assertEqual(simulator.events[-1]["event"], "duplicate_result_ignored")

    def test_53_same_key_with_different_payload_freezes_for_review(self) -> None:
        simulator = app.CollaborationSimulator(valid_scenario())
        self.make_running(simulator, "job")
        self.assertTrue(simulator.accept_result("job", "key", {"v": 1}))
        self.assertFalse(simulator.accept_result("job", "key", {"v": 2}))
        self.assertEqual(simulator.tasks["job"]["state"], "needs_review")
        conflict_event = simulator.events[-2]
        self.assertEqual(conflict_event["event"], "result_conflict_detected")
        self.assertNotEqual(
            conflict_event["accepted_result_digest"],
            conflict_event["received_result_digest"],
        )
        self.assertEqual(simulator.events[-1]["to"], "needs_review")
        self.assertEqual(simulator.run()["status"], "needs_review")

    def test_54_conflict_blocks_pending_dependents(self) -> None:
        scenario = valid_scenario()
        downstream = copy.deepcopy(scenario["tasks"][0])
        downstream.update(id="downstream", requires=["job"])
        scenario["tasks"].append(downstream)
        simulator = app.CollaborationSimulator(scenario)
        self.make_running(simulator, "job")
        simulator.accept_result("job", "key", {"v": 1})
        simulator.accept_result("job", "key", {"v": 2})
        report = simulator.run()
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(report["tasks"]["downstream"]["state"], "blocked")

    def test_55_non_json_result_is_rejected_before_state_change(self) -> None:
        simulator = app.CollaborationSimulator(valid_scenario())
        self.make_running(simulator, "job")
        with self.assertRaisesRegex(app.ScenarioError, r"JSON-compatible"):
            simulator.accept_result("job", "key", {"bad": float("nan")})
        self.assertEqual(simulator.tasks["job"]["state"], "running")

    def test_56_reverse_order_failure_blocks_every_descendant(self) -> None:
        scenario = valid_scenario()
        root = scenario["tasks"][0]
        root.update(id="a", outcome_plan=["permanent_error"])
        middle = copy.deepcopy(root)
        middle.update(id="b", requires=["a"], outcome_plan=["success"])
        leaf = copy.deepcopy(root)
        leaf.update(id="c", requires=["b"], outcome_plan=["success"])
        scenario["tasks"] = [leaf, middle, root]

        report = app.CollaborationSimulator(scenario).run()

        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["tasks"]["a"]["state"], "failed")
        self.assertEqual(report["tasks"]["b"]["state"], "blocked")
        self.assertEqual(report["tasks"]["c"]["state"], "blocked")
        self.assertFalse(
            any(task["state"] == "pending" for task in report["tasks"].values())
        )

    def test_57_reverse_order_conflict_blocks_every_descendant(self) -> None:
        scenario = valid_scenario()
        root = scenario["tasks"][0]
        root["id"] = "a"
        middle = copy.deepcopy(root)
        middle.update(id="b", requires=["a"])
        leaf = copy.deepcopy(root)
        leaf.update(id="c", requires=["b"])
        scenario["tasks"] = [leaf, middle, root]
        simulator = app.CollaborationSimulator(scenario)
        self.make_running(simulator, "a")
        simulator.accept_result("a", "key", {"value": 1})
        simulator.accept_result("a", "key", {"value": 2})

        report = simulator.run()

        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(report["tasks"]["b"]["state"], "blocked")
        self.assertEqual(report["tasks"]["c"]["state"], "blocked")

    def test_58_illegal_state_transition_is_rejected_without_mutation(self) -> None:
        simulator = app.CollaborationSimulator(valid_scenario())
        with self.assertRaisesRegex(app.ScenarioError, r"illegal state transition"):
            simulator._transition("job", "failed", "test_setup")
        self.assertEqual(simulator.tasks["job"]["state"], "pending")
        self.assertEqual(simulator.tasks["job"]["state_version"], 0)

    def test_59_success_cannot_return_to_pending(self) -> None:
        simulator = app.CollaborationSimulator(valid_scenario())
        self.make_running(simulator, "job")
        simulator.accept_result("job", "key", {"value": 1})
        with self.assertRaisesRegex(app.ScenarioError, r"illegal state transition"):
            simulator._transition("job", "pending", "bad_retry")
        self.assertEqual(simulator.tasks["job"]["state"], "succeeded")

    def test_60_conflict_withholds_public_result_and_keeps_review_evidence(self) -> None:
        simulator = app.CollaborationSimulator(valid_scenario())
        self.make_running(simulator, "job")
        accepted = {"nested": [1]}
        received = {"nested": [2]}
        simulator.accept_result("job", "key", accepted)
        simulator.accept_result("job", "key", received)
        accepted["nested"].append(99)
        received["nested"].append(99)

        task = simulator.run()["tasks"]["job"]

        self.assertIsNone(task["result"])
        self.assertEqual(task["result_trust"], "conflicted")
        self.assertEqual(task["state_version"], 3)
        self.assertEqual(len(task["result_conflicts"]), 1)
        conflict = task["result_conflicts"][0]
        self.assertEqual(conflict["accepted"]["payload"], {"nested": [1]})
        self.assertEqual(conflict["received"]["payload"], {"nested": [2]})
        self.assertEqual(conflict["state_version"], 3)
        self.assertLess(conflict["detected_event_seq"], len(simulator.events) + 1)

    def test_41_events_have_monotonic_sequence_numbers(self) -> None:
        report = app.CollaborationSimulator(valid_scenario()).run()
        self.assertEqual(
            [event["seq"] for event in report["events"]],
            list(range(1, len(report["events"]) + 1)),
        )

    def test_42_run_does_not_mutate_input_fixture(self) -> None:
        scenario = valid_scenario()
        before = copy.deepcopy(scenario)
        app.CollaborationSimulator(scenario).run()
        self.assertEqual(scenario, before)

    def test_43_steps_never_exceed_global_budget(self) -> None:
        scenario = valid_scenario()
        scenario["step_budget"] = 1
        scenario["tasks"][0]["max_attempts"] = 3
        scenario["tasks"][0]["outcome_plan"] = ["transient_error"]
        report = app.CollaborationSimulator(scenario).run()
        self.assertLessEqual(report["steps_used"], report["step_budget"])

    def test_44_cli_success_returns_zero(self) -> None:
        path = self.write_scenario(valid_scenario())
        code, stdout, stderr = self.run_main(str(path))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["status"], "succeeded")
        self.assertEqual(stderr, "")

    def test_45_cli_workflow_failure_returns_one(self) -> None:
        scenario = valid_scenario()
        scenario["tasks"][0]["outcome_plan"] = ["permanent_error"]
        path = self.write_scenario(scenario)
        code, stdout, stderr = self.run_main(str(path))
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout)["status"], "failed")
        self.assertEqual(stderr, "")

    def test_46_cli_contract_error_returns_two(self) -> None:
        scenario = valid_scenario()
        scenario["extra"] = True
        path = self.write_scenario(scenario)
        code, stdout, stderr = self.run_main(str(path))
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("scenario error", stderr)

    def test_47_cli_output_file_matches_stdout(self) -> None:
        scenario_path = self.write_scenario(valid_scenario())
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.json"
            code, stdout, stderr = self.run_main(
                str(scenario_path), "--output", str(output_path)
            )
            written = output_path.read_text(encoding="utf-8")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(written), json.loads(stdout))
        self.assertEqual(stderr, "")

    def test_48_fixture_succeeds_with_expected_retry(self) -> None:
        here = Path(app.__file__).resolve().parent
        report = app.CollaborationSimulator(app.load_scenario(here / "scenario.json")).run()
        self.assertEqual(report["status"], "succeeded")
        self.assertEqual(report["tasks"]["collect"]["attempts"], 2)

    def test_49_production_code_has_no_assert_statement(self) -> None:
        tree = ast.parse(Path(app.__file__).read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))

    def test_50_reports_are_json_serializable(self) -> None:
        report = app.CollaborationSimulator(valid_scenario()).run()
        self.assertEqual(json.loads(json.dumps(report)), report)


if __name__ == "__main__":
    unittest.main()
