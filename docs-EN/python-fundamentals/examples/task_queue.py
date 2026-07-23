"""Read and validate task JSON, then produce a deterministic status report."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALLOWED_STATUSES = frozenset({"pending", "running", "done", "failed"})
REQUIRED_FIELDS = frozenset({"id", "title", "status"})


class TaskValidationError(ValueError):
    """The input does not satisfy the task contract."""


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    title: str
    status: str


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskValidationError(f"{field} must be a non-empty string")
    return value.strip()


def parse_task(value: Any, index: int) -> Task:
    if not isinstance(value, dict):
        raise TaskValidationError(f"item {index} must be a JSON object")

    keys = frozenset(value)
    missing = REQUIRED_FIELDS - keys
    unknown = keys - REQUIRED_FIELDS
    if missing:
        raise TaskValidationError(f"item {index} is missing fields: {sorted(missing)}")
    if unknown:
        raise TaskValidationError(f"item {index} has unknown fields: {sorted(unknown)}")

    task_id = _non_empty_string(value["id"], "id")
    title = _non_empty_string(value["title"], "title")
    status = _non_empty_string(value["status"], "status")
    if status not in ALLOWED_STATUSES:
        raise TaskValidationError(
            f"status={status!r} is invalid; allowed values are {sorted(ALLOWED_STATUSES)}"
        )
    return Task(task_id=task_id, title=title, status=status)


def load_tasks(path: Path) -> list[Task]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TaskValidationError(f"input file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TaskValidationError(
            f"invalid JSON: line={exc.lineno}, column={exc.colno}"
        ) from exc

    if not isinstance(raw, list):
        raise TaskValidationError("JSON root must be an array")

    tasks = [parse_task(value, index) for index, value in enumerate(raw)]
    seen: set[str] = set()
    for task in tasks:
        if task.task_id in seen:
            raise TaskValidationError(f"duplicate task id: {task.task_id}")
        seen.add(task.task_id)
    return tasks


def summarize(tasks: list[Task]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    unfinished_ids: list[str] = []
    for task in tasks:
        by_status[task.status] = by_status.get(task.status, 0) + 1
        if task.status != "done":
            unfinished_ids.append(task.task_id)
    return {
        "total": len(tasks),
        "by_status": dict(sorted(by_status.items())),
        "unfinished_ids": unfinished_ids,
    }


def write_report(report: dict[str, Any], path: Path) -> None:
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 task JSON file")
    parser.add_argument("--output", type=Path, help="optional report output path")
    args = parser.parse_args()

    report = summarize(load_tasks(args.input))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output is None:
        print(rendered)
    else:
        write_report(report, args.output)
        print(f"report written: {args.output}")


if __name__ == "__main__":
    main()
