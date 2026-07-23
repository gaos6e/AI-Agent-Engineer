"""Read and validate task JSON, then produce a deterministic status report."""

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
    """The input does not satisfy the task contract."""


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    title: str
    status: Status


def _non_empty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskValidationError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise TaskValidationError(f"{field} must not have leading or trailing whitespace")
    return value


def parse_task(value: object, index: int) -> Task:
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
    return Task(task_id=task_id, title=title, status=cast(Status, status))


def _read_utf8_limited(path: Path, max_bytes: int) -> str:
    if max_bytes < 1:
        raise ValueError("max_bytes must be at least 1")
    try:
        with path.open("rb") as stream:
            payload = stream.read(max_bytes + 1)
    except FileNotFoundError as exc:
        raise TaskValidationError(f"input file does not exist: {path}") from exc
    except OSError as exc:
        raise TaskValidationError(f"unable to read input file: {path}") from exc

    if len(payload) > max_bytes:
        raise TaskValidationError(f"input file exceeds the {max_bytes}-byte limit")
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TaskValidationError("input file must be valid UTF-8") from exc


def _reject_non_finite(value: str) -> NoReturn:
    raise TaskValidationError(f"JSON does not permit non-finite value: {value}")


def load_tasks(
    path: Path, *, max_bytes: int = DEFAULT_MAX_INPUT_BYTES
) -> list[Task]:
    text = _read_utf8_limited(path, max_bytes)
    try:
        raw = json.loads(text, parse_constant=_reject_non_finite)
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
    """Reject obvious aliases; this is not a security sandbox against concurrent replacement."""
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
    parser.add_argument("input", type=Path, help="UTF-8 task JSON file")
    parser.add_argument("--output", type=Path, help="optional report output path")
    args = parser.parse_args(argv)

    try:
        report = summarize(load_tasks(args.input))
    except TaskValidationError as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output is None:
        print(rendered)
    else:
        if _same_input_and_output(args.input, args.output):
            print("output error: output path must differ from input file", file=sys.stderr)
            return 1
        try:
            write_report(report, args.output)
        except OSError as exc:
            print(f"output error: {exc}", file=sys.stderr)
            return 1
        print(f"report written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
