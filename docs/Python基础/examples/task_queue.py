"""读取并校验任务 JSON，生成确定性的状态报告。"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALLOWED_STATUSES = frozenset({"pending", "running", "done", "failed"})
REQUIRED_FIELDS = frozenset({"id", "title", "status"})


class TaskValidationError(ValueError):
    """输入不满足任务契约。"""


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    title: str
    status: str


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskValidationError(f"{field} 必须是非空字符串")
    return value.strip()


def parse_task(value: Any, index: int) -> Task:
    if not isinstance(value, dict):
        raise TaskValidationError(f"第 {index} 项必须是 JSON 对象")

    keys = frozenset(value)
    missing = REQUIRED_FIELDS - keys
    unknown = keys - REQUIRED_FIELDS
    if missing:
        raise TaskValidationError(f"第 {index} 项缺少字段: {sorted(missing)}")
    if unknown:
        raise TaskValidationError(f"第 {index} 项包含未知字段: {sorted(unknown)}")

    task_id = _non_empty_string(value["id"], "id")
    title = _non_empty_string(value["title"], "title")
    status = _non_empty_string(value["status"], "status")
    if status not in ALLOWED_STATUSES:
        raise TaskValidationError(
            f"status={status!r} 非法；允许值为 {sorted(ALLOWED_STATUSES)}"
        )
    return Task(task_id=task_id, title=title, status=status)


def load_tasks(path: Path) -> list[Task]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TaskValidationError(f"输入文件不存在: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TaskValidationError(
            f"JSON 格式错误: line={exc.lineno}, column={exc.colno}"
        ) from exc

    if not isinstance(raw, list):
        raise TaskValidationError("JSON 根节点必须是数组")

    tasks = [parse_task(value, index) for index, value in enumerate(raw)]
    seen: set[str] = set()
    for task in tasks:
        if task.task_id in seen:
            raise TaskValidationError(f"任务 id 重复: {task.task_id}")
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
    parser.add_argument("input", type=Path, help="UTF-8 任务 JSON 文件")
    parser.add_argument("--output", type=Path, help="可选报告输出路径")
    args = parser.parse_args()

    report = summarize(load_tasks(args.input))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output is None:
        print(rendered)
    else:
        write_report(report, args.output)
        print(f"报告已写入: {args.output}")


if __name__ == "__main__":
    main()

