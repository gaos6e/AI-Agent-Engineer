import copy
import unittest
from collections.abc import Mapping

from task_scheduler import ScheduleInputError, schedule


class UnhashableString(str):
    __hash__ = None


class InvalidKeyMapping(Mapping[object, object]):
    def __getitem__(self, key: object) -> object:
        if str(key) == "id":
            return "a"
        if key == "priority":
            return 1
        if key == "depends_on":
            return []
        raise KeyError(key)

    def __iter__(self):
        yield UnhashableString("id")
        yield "priority"
        yield "depends_on"

    def __len__(self) -> int:
        return 3


class TaskSchedulerTests(unittest.TestCase):
    def test_task_collection_type_is_validated(self) -> None:
        invalid_values = (None, "text", b"bytes", {"id": "single-mapping"}, {1, 2})
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ScheduleInputError, "task collection must"):
                    schedule(value)

    def test_one_shot_iterator_is_rejected_without_consumption(self) -> None:
        tasks = [{"id": "a", "priority": 1, "depends_on": []}]
        one_shot = (task for task in tasks)
        with self.assertRaisesRegex(ScheduleInputError, "list or tuple"):
            schedule(one_shot)
        self.assertEqual(list(one_shot), tasks)

    def test_empty_input_returns_empty_order(self) -> None:
        self.assertEqual(schedule([]), [])

    def test_single_task(self) -> None:
        tasks = [{"id": "only", "priority": 1, "depends_on": []}]
        self.assertEqual(schedule(tasks), ["only"])

    def test_same_priority_uses_task_id_not_input_order(self) -> None:
        tasks = [
            {"id": "z", "priority": 1, "depends_on": []},
            {"id": "a", "priority": 1, "depends_on": []},
        ]
        self.assertEqual(schedule(tasks), ["a", "z"])

    def test_priority_applies_only_among_ready_tasks(self) -> None:
        tasks = [
            {"id": "prerequisite", "priority": 9, "depends_on": []},
            {"id": "urgent", "priority": 0, "depends_on": ["prerequisite"]},
            {"id": "normal", "priority": 5, "depends_on": []},
        ]
        self.assertEqual(schedule(tasks), ["normal", "prerequisite", "urgent"])

    def test_chain(self) -> None:
        tasks = [
            {"id": "c", "priority": 1, "depends_on": ["b"]},
            {"id": "a", "priority": 3, "depends_on": []},
            {"id": "b", "priority": 2, "depends_on": ["a"]},
        ]
        self.assertEqual(schedule(tasks), ["a", "b", "c"])

    def test_diamond(self) -> None:
        tasks = [
            {"id": "start", "priority": 5, "depends_on": []},
            {"id": "left", "priority": 2, "depends_on": ["start"]},
            {"id": "right", "priority": 1, "depends_on": ["start"]},
            {"id": "end", "priority": 0, "depends_on": ["left", "right"]},
        ]
        self.assertEqual(schedule(tasks), ["start", "right", "left", "end"])

    def test_disconnected_components(self) -> None:
        tasks = [
            {"id": "a1", "priority": 2, "depends_on": []},
            {"id": "a2", "priority": 1, "depends_on": ["a1"]},
            {"id": "b1", "priority": 0, "depends_on": []},
        ]
        self.assertEqual(schedule(tasks), ["b1", "a1", "a2"])

    def test_duplicate_id_is_rejected(self) -> None:
        tasks = [
            {"id": "same", "priority": 1, "depends_on": []},
            {"id": "same", "priority": 2, "depends_on": []},
        ]
        with self.assertRaisesRegex(ScheduleInputError, "duplicate task id"):
            schedule(tasks)

    def test_missing_dependency_is_rejected(self) -> None:
        tasks = [{"id": "a", "priority": 1, "depends_on": ["missing"]}]
        with self.assertRaisesRegex(ScheduleInputError, "depends on missing tasks"):
            schedule(tasks)

    def test_duplicate_dependency_is_rejected(self) -> None:
        tasks = [
            {"id": "a", "priority": 1, "depends_on": []},
            {"id": "b", "priority": 1, "depends_on": ["a", "a"]},
        ]
        with self.assertRaisesRegex(ScheduleInputError, "duplicate dependency"):
            schedule(tasks)

    def test_direct_self_dependency_is_rejected(self) -> None:
        tasks = [{"id": "a", "priority": 1, "depends_on": ["a"]}]
        with self.assertRaisesRegex(ScheduleInputError, "directly depend on itself"):
            schedule(tasks)

    def test_cycle_reports_blocked_not_cycle_members(self) -> None:
        tasks = [
            {"id": "a", "priority": 1, "depends_on": ["b"]},
            {"id": "b", "priority": 1, "depends_on": ["a"]},
            {"id": "downstream", "priority": 1, "depends_on": ["a"]},
            {"id": "independent", "priority": 1, "depends_on": []},
        ]
        with self.assertRaisesRegex(
            ScheduleInputError,
            "remaining tasks are blocked by one or more dependency cycles: a, b, downstream",
        ):
            schedule(tasks)

    def test_non_mapping_task_is_rejected(self) -> None:
        with self.assertRaisesRegex(ScheduleInputError, "item 0 must be a mapping"):
            schedule(["not-a-task"])

    def test_missing_and_unknown_fields_are_rejected(self) -> None:
        cases = [
            ({"id": "a", "priority": 1}, "missing fields"),
            (
                {"id": "a", "priority": 1, "depends_on": [], "extra": 1},
                "unknown fields",
            ),
        ]
        for value, message in cases:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ScheduleInputError, message):
                    schedule([value])

    def test_field_names_must_be_strings(self) -> None:
        task = {
            "id": "a",
            "priority": 1,
            "depends_on": [],
            3: "invalid-key",
        }
        with self.assertRaisesRegex(ScheduleInputError, "field names.*built-in str"):
            schedule([task])

    def test_unhashable_field_name_is_normalized(self) -> None:
        with self.assertRaisesRegex(ScheduleInputError, "field names.*built-in str"):
            schedule([InvalidKeyMapping()])

    def test_unhashable_string_subclasses_are_normalized(self) -> None:
        invalid_cases = [
            [{"id": UnhashableString("a"), "priority": 1, "depends_on": []}],
            [
                {"id": "a", "priority": 1, "depends_on": []},
                {
                    "id": "b",
                    "priority": 1,
                    "depends_on": [UnhashableString("a")],
                },
            ],
        ]
        for tasks in invalid_cases:
            with self.subTest(tasks=tasks):
                with self.assertRaises(ScheduleInputError):
                    schedule(tasks)

    def test_invalid_ids_are_rejected(self) -> None:
        for task_id in ("", " a", "a ", 3, None, UnhashableString("a")):
            with self.subTest(task_id=task_id):
                task = {"id": task_id, "priority": 1, "depends_on": []}
                with self.assertRaises(ScheduleInputError):
                    schedule([task])

    def test_priority_rejects_bool_and_non_int(self) -> None:
        for priority in (True, False, 1.0, "1", None):
            with self.subTest(priority=priority):
                task = {"id": "a", "priority": priority, "depends_on": []}
                with self.assertRaisesRegex(ScheduleInputError, "priority"):
                    schedule([task])

    def test_dependencies_must_be_list_of_strict_strings(self) -> None:
        invalid_dependencies = (
            "a",
            [1],
            [""],
            [" a"],
            [None],
            [UnhashableString("a")],
        )
        for dependencies in invalid_dependencies:
            with self.subTest(dependencies=dependencies):
                task = {
                    "id": "b",
                    "priority": 1,
                    "depends_on": dependencies,
                }
                with self.assertRaises(ScheduleInputError):
                    schedule([task])

    def test_input_is_not_modified(self) -> None:
        tasks = [
            {"id": "a", "priority": 1, "depends_on": []},
            {"id": "b", "priority": 0, "depends_on": ["a"]},
        ]
        before = copy.deepcopy(tasks)
        schedule(tasks)
        self.assertEqual(tasks, before)

    def test_repeated_runs_are_deterministic(self) -> None:
        tasks = [
            {"id": "z", "priority": 1, "depends_on": []},
            {"id": "a", "priority": 1, "depends_on": []},
            {"id": "end", "priority": 0, "depends_on": ["a", "z"]},
        ]
        outputs = [schedule(tasks) for _ in range(5)]
        self.assertTrue(all(output == outputs[0] for output in outputs))


if __name__ == "__main__":
    unittest.main()
