"""读取并校验任务 JSON，生成确定性的状态报告。"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NoReturn, cast


ALLOWED_STATUSES = frozenset({"pending", "running", "done", "failed"})
REQUIRED_FIELDS = frozenset({"id", "title", "status"})
DEFAULT_MAX_INPUT_BYTES = 1_000_000
Status = Literal["pending", "running", "done", "failed"]


class TaskValidationError(ValueError):
    """输入不满足任务契约。"""


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    title: str
    status: Status


def _non_empty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskValidationError(f"{field} 必须是非空字符串")
    if value != value.strip():
        raise TaskValidationError(f"{field} 不得包含首尾空白")
    return value


def parse_task(value: object, index: int) -> Task:
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
    return Task(task_id=task_id, title=title, status=cast(Status, status))


def _read_utf8_limited(path: Path, max_bytes: int) -> str:
    if max_bytes < 1:
        raise ValueError("max_bytes 必须至少为 1")
    try:
        with path.open("rb") as stream:
            payload = stream.read(max_bytes + 1)
    except FileNotFoundError as exc:
        raise TaskValidationError(f"输入文件不存在: {path}") from exc
    except OSError as exc:
        raise TaskValidationError(f"无法读取输入文件: {path}") from exc

    if len(payload) > max_bytes:
        raise TaskValidationError(f"输入文件超过 {max_bytes} 字节上限")
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TaskValidationError("输入文件必须是有效 UTF-8") from exc


def _reject_non_finite(value: str) -> NoReturn:
    raise TaskValidationError(f"JSON 不允许非有限数值: {value}")


def load_tasks(
    path: Path, *, max_bytes: int = DEFAULT_MAX_INPUT_BYTES
) -> list[Task]:
    text = _read_utf8_limited(path, max_bytes)
    try:
        raw = json.loads(text, parse_constant=_reject_non_finite)
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


def summarize(tasks: list[Task]) -> dict[str, object]:
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


def write_report(report: dict[str, object], path: Path) -> None:
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _same_input_and_output(input_path: Path, output_path: Path) -> bool:
    """拒绝显然相同的路径；这不是抵御并发替换的安全沙箱。"""
    try:
        if input_path.resolve(strict=True) == output_path.resolve(strict=False):
            return True
    except OSError:
        pass

    try:
        return output_path.exists() and input_path.samefile(output_path)
    except OSError:
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 任务 JSON 文件")
    parser.add_argument("--output", type=Path, help="可选报告输出路径")
    args = parser.parse_args(argv)

    try:
        report = summarize(load_tasks(args.input))
    except TaskValidationError as exc:
        print(f"输入错误: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output is None:
        print(rendered)
    else:
        if _same_input_and_output(args.input, args.output):
            print("输出错误: 输出路径不能与输入文件相同", file=sys.stderr)
            return 1
        try:
            write_report(report, args.output)
        except OSError as exc:
            print(f"输出错误: {exc}", file=sys.stderr)
            return 1
        print(f"报告已写入: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
