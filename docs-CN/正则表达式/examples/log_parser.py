"""Parse a deliberately small, fixed Agent log format with regex."""

from __future__ import annotations

import re
from pathlib import Path


LOG_PATTERN = re.compile(
    r"""
    (?P<timestamp>[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z)
    \s+level=(?P<level>INFO|WARNING|ERROR)
    \s+run_id=(?P<run_id>[A-Za-z0-9_-]{1,64})
    \s+latency_ms=(?P<latency_ms>[0-9]{1,6})
    \s+message="(?P<message>[^"\r\n]*)"
    """,
    re.VERBOSE,
)


def parse_line(line: str, line_number: int) -> dict[str, str | int]:
    match = LOG_PATTERN.fullmatch(line)
    if match is None:
        raise ValueError(f"line {line_number}: invalid log format")

    latency_ms = int(match.group("latency_ms"))
    if latency_ms > 300_000:
        raise ValueError(f"line {line_number}: latency_ms exceeds limit")

    return {
        "timestamp": match.group("timestamp"),
        "level": match.group("level"),
        "run_id": match.group("run_id"),
        "latency_ms": latency_ms,
        "message": match.group("message"),
    }


def parse_file(path: Path) -> tuple[list[dict[str, str | int]], list[str]]:
    records: list[dict[str, str | int]] = []
    errors: list[str] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        try:
            records.append(parse_line(line, line_number))
        except ValueError as error:
            errors.append(str(error))
    return records, errors


def main() -> int:
    path = Path(__file__).with_name("sample.txt")
    records, errors = parse_file(path)

    error_records = sum(record["level"] == "ERROR" for record in records)
    max_latency = max(
        (int(record["latency_ms"]) for record in records),
        default=-1,
    )

    print(f"parsed={len(records)} errors={len(errors)} max_latency_ms={max_latency}")
    for error in errors:
        print(error)

    expected = (
        len(records) == 3
        and errors == ["line 3: invalid log format"]
        and error_records == 1
        and max_latency == 2200
    )
    if not expected:
        raise RuntimeError("sample fixture produced unexpected results")

    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
