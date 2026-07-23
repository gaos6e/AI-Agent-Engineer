"""Run the complete local JSON project without persistent output."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from strict_json import iter_json_lines, write_json_lines_atomic
from validate_agent_config import load_and_validate_config
from validate_tool_calls import process_tool_call_file


def main() -> None:
    base = Path(__file__).resolve().parent
    config = load_and_validate_config(
        base / "agent_config.json",
        base / "agent_config.schema.json",
    )
    reports = process_tool_call_file(
        base / "tool_calls.jsonl",
        base / "tool_call.schema.json",
    )

    with TemporaryDirectory() as directory:
        report_path = Path(directory) / "report.jsonl"
        write_json_lines_atomic(report_path, reports)
        round_trip = [value for _, value in iter_json_lines(report_path)]

    counts = Counter(report["status"] for report in round_trip)
    print(f"validated config: {config['name']}")
    print("report statuses:", dict(sorted(counts.items())))
    print("no tools executed; temporary report removed")


if __name__ == "__main__":
    main()

