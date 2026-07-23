"""A deterministic dependency-aware priority scheduler using only the Python standard library."""

from __future__ import annotations

import heapq
from collections.abc import Mapping
from dataclasses import dataclass


REQUIRED_FIELDS = frozenset({"id", "priority", "depends_on"})


class ScheduleInputError(ValueError):
    """The task collection does not satisfy the scheduler input contract."""


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    priority: int
    depends_on: tuple[str, ...]


def _strict_non_empty_string(value: object, field: str) -> str:
    if type(value) is not str or not value:
        raise ScheduleInputError(f"{field} must be a non-empty built-in str")
    if value != value.strip():
        raise ScheduleInputError(f"{field} must not have leading or trailing whitespace")
    return value


def parse_task(value: object, index: int) -> Task:
    if not isinstance(value, Mapping):
        raise ScheduleInputError(f"item {index} must be a mapping")

    try:
        raw_keys = list(value.keys())
    except Exception as exc:
        raise ScheduleInputError(f"field names for item {index} cannot be read") from exc
    if not all(type(key) is str for key in raw_keys):
        raise ScheduleInputError(f"field names for item {index} must be built-in str values")
    keys = set(raw_keys)
    if len(keys) != len(raw_keys):
        raise ScheduleInputError(f"item {index} contains duplicate field names")
    missing = REQUIRED_FIELDS - keys
    unknown = keys - REQUIRED_FIELDS
    if missing:
        raise ScheduleInputError(f"item {index} is missing fields: {sorted(missing)}")
    if unknown:
        raise ScheduleInputError(f"item {index} has unknown fields: {sorted(unknown)}")

    try:
        fields = {key: value[key] for key in raw_keys}
    except Exception as exc:
        raise ScheduleInputError(f"field values for item {index} cannot be read") from exc

    task_id = _strict_non_empty_string(fields["id"], f"item {index} id")
    priority = fields["priority"]
    if type(priority) is not int:
        raise ScheduleInputError(f"priority for task {task_id} must be an int, not bool")

    raw_dependencies = fields["depends_on"]
    if not isinstance(raw_dependencies, list):
        raise ScheduleInputError(f"depends_on for task {task_id} must be a list")

    dependencies: list[str] = []
    seen_dependencies: set[str] = set()
    for dependency_index, raw_dependency in enumerate(raw_dependencies):
        dependency = _strict_non_empty_string(
            raw_dependency,
            f"dependency {dependency_index} for task {task_id}",
        )
        if dependency == task_id:
            raise ScheduleInputError(f"a task cannot directly depend on itself: {task_id}")
        if dependency in seen_dependencies:
            raise ScheduleInputError(f"task {task_id} contains duplicate dependency: {dependency}")
        seen_dependencies.add(dependency)
        dependencies.append(dependency)

    return Task(
        task_id=task_id,
        priority=priority,
        depends_on=tuple(dependencies),
    )


def _parse_tasks(values: object) -> dict[str, Task]:
    if type(values) not in (list, tuple):
        raise ScheduleInputError(
            "the task collection must be a repeatable built-in list or tuple"
        )

    by_id: dict[str, Task] = {}
    for index, value in enumerate(values):
        task = parse_task(value, index)
        if task.task_id in by_id:
            raise ScheduleInputError(f"duplicate task id: {task.task_id}")
        by_id[task.task_id] = task

    for task in by_id.values():
        missing = set(task.depends_on) - by_id.keys()
        if missing:
            raise ScheduleInputError(
                f"task {task.task_id} depends on missing tasks: {sorted(missing)}"
            )
    return by_id


def schedule(values: object) -> list[str]:
    """Return a valid deterministic order: lower priority values win, then task_id."""
    by_id = _parse_tasks(values)
    remaining = {
        task_id: len(task.depends_on) for task_id, task in by_id.items()
    }
    dependents: dict[str, list[str]] = {task_id: [] for task_id in by_id}
    for task in by_id.values():
        for predecessor in task.depends_on:
            dependents[predecessor].append(task.task_id)

    ready: list[tuple[int, str]] = []
    for task_id, count in remaining.items():
        if count == 0:
            task = by_id[task_id]
            heapq.heappush(ready, (task.priority, task.task_id))

    order: list[str] = []
    while ready:
        _, task_id = heapq.heappop(ready)
        order.append(task_id)
        for dependent in dependents[task_id]:
            remaining[dependent] -= 1
            if remaining[dependent] == 0:
                task = by_id[dependent]
                heapq.heappush(ready, (task.priority, task.task_id))

    if len(order) != len(by_id):
        blocked = sorted(set(by_id) - set(order))
        raise ScheduleInputError(
            "remaining tasks are blocked by one or more dependency cycles: "
            + ", ".join(blocked)
        )
    return order


def run_demo() -> None:
    tasks: list[object] = [
        {"id": "extract", "priority": 2, "depends_on": []},
        {"id": "validate", "priority": 1, "depends_on": ["extract"]},
        {"id": "summarize", "priority": 2, "depends_on": ["validate"]},
        {"id": "review", "priority": 3, "depends_on": ["summarize"]},
    ]
    print("execution order:", " -> ".join(schedule(tasks)))


if __name__ == "__main__":
    run_demo()
