"""确定性的依赖感知优先级调度示例，仅使用 Python 标准库。"""

from __future__ import annotations

import heapq
from collections.abc import Mapping
from dataclasses import dataclass


REQUIRED_FIELDS = frozenset({"id", "priority", "depends_on"})


class ScheduleInputError(ValueError):
    """任务集合不满足调度器输入契约。"""


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    priority: int
    depends_on: tuple[str, ...]


def _strict_non_empty_string(value: object, field: str) -> str:
    if type(value) is not str or not value:
        raise ScheduleInputError(f"{field} 必须是内建 str 类型的非空字符串")
    if value != value.strip():
        raise ScheduleInputError(f"{field} 不得包含首尾空白")
    return value


def parse_task(value: object, index: int) -> Task:
    if not isinstance(value, Mapping):
        raise ScheduleInputError(f"第 {index} 项必须是映射对象")

    try:
        raw_keys = list(value.keys())
    except Exception as exc:
        raise ScheduleInputError(f"第 {index} 项的字段名无法读取") from exc
    if not all(type(key) is str for key in raw_keys):
        raise ScheduleInputError(f"第 {index} 项的字段名必须是内建 str")
    keys = set(raw_keys)
    if len(keys) != len(raw_keys):
        raise ScheduleInputError(f"第 {index} 项包含重复字段名")
    missing = REQUIRED_FIELDS - keys
    unknown = keys - REQUIRED_FIELDS
    if missing:
        raise ScheduleInputError(f"第 {index} 项缺少字段: {sorted(missing)}")
    if unknown:
        raise ScheduleInputError(f"第 {index} 项包含未知字段: {sorted(unknown)}")

    try:
        fields = {key: value[key] for key in raw_keys}
    except Exception as exc:
        raise ScheduleInputError(f"第 {index} 项的字段值无法读取") from exc

    task_id = _strict_non_empty_string(fields["id"], f"第 {index} 项 id")
    priority = fields["priority"]
    if type(priority) is not int:
        raise ScheduleInputError(f"任务 {task_id} 的 priority 必须是整数且不能是 bool")

    raw_dependencies = fields["depends_on"]
    if not isinstance(raw_dependencies, list):
        raise ScheduleInputError(f"任务 {task_id} 的 depends_on 必须是列表")

    dependencies: list[str] = []
    seen_dependencies: set[str] = set()
    for dependency_index, raw_dependency in enumerate(raw_dependencies):
        dependency = _strict_non_empty_string(
            raw_dependency,
            f"任务 {task_id} 的第 {dependency_index} 个依赖",
        )
        if dependency == task_id:
            raise ScheduleInputError(f"任务不能直接依赖自身: {task_id}")
        if dependency in seen_dependencies:
            raise ScheduleInputError(f"任务 {task_id} 包含重复依赖: {dependency}")
        seen_dependencies.add(dependency)
        dependencies.append(dependency)

    return Task(
        task_id=task_id,
        priority=priority,
        depends_on=tuple(dependencies),
    )


def _parse_tasks(values: object) -> dict[str, Task]:
    if type(values) not in (list, tuple):
        raise ScheduleInputError("任务集合必须是可重复遍历的内建 list 或 tuple")

    by_id: dict[str, Task] = {}
    for index, value in enumerate(values):
        task = parse_task(value, index)
        if task.task_id in by_id:
            raise ScheduleInputError(f"任务 id 重复: {task.task_id}")
        by_id[task.task_id] = task

    for task in by_id.values():
        missing = set(task.depends_on) - by_id.keys()
        if missing:
            raise ScheduleInputError(
                f"任务 {task.task_id} 依赖不存在的任务: {sorted(missing)}"
            )
    return by_id


def schedule(values: object) -> list[str]:
    """返回合法确定性顺序；数值越小优先级越高，同级按 task_id。"""
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
            "剩余任务被一个或多个依赖环阻塞: "
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
