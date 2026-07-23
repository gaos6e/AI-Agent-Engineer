"""Agent 运行日志清洗项目的回归测试。"""

from __future__ import annotations

import csv
from hashlib import sha256
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from contextlib import redirect_stdout

from clean_agent_runs import (
    clean_file,
    clean_row,
    main,
    normalize_query,
    parse_timestamp,
)


EXAMPLE_DIR = Path(__file__).resolve().parent
SAMPLE_INPUT = EXAMPLE_DIR / "dirty_agent_runs.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


class CleanAgentRunsTests(unittest.TestCase):
    def test_timestamp_is_normalized_to_utc(self) -> None:
        self.assertEqual(
            parse_timestamp("2026-07-13T09:02:00+08:00"),
            "2026-07-13T01:02:00Z",
        )
        self.assertEqual(
            parse_timestamp("2026-07-13T01:02:00Z"),
            "2026-07-13T01:02:00Z",
        )
        self.assertEqual(
            parse_timestamp("2026-07-13T09:02:00.123456+08:00"),
            "2026-07-13T01:02:00.123456Z",
        )
        with self.assertRaises(ValueError):
            parse_timestamp("2026-07-13T01:02:00")

    def test_query_keeps_internal_whitespace_and_normalizes_newlines(self) -> None:
        self.assertEqual(
            normalize_query("  line  1\r\n  code  block  \r"),
            "line  1\n  code  block",
        )

    def test_clean_row_maps_status_and_rejects_duplicate_identity(self) -> None:
        seen: set[str] = set()
        valid = {
            "run_id": " run-1 ",
            "started_at": "2026-07-13T09:02:00+08:00",
            "status": " OK ",
            "latency_ms": " 120 ",
            "query": " hello  world ",
        }
        cleaned, reason = clean_row(valid, seen)
        self.assertEqual(reason, "")
        self.assertEqual(
            cleaned,
            {
                "run_id": "run-1",
                "started_at": "2026-07-13T01:02:00Z",
                "status": "success",
                "latency_ms": "120",
                "query": "hello  world",
            },
        )
        duplicate, reason = clean_row(valid, seen)
        self.assertIsNone(duplicate)
        self.assertEqual(reason, "duplicate:run_id")

    def test_first_invalid_occurrence_still_reserves_run_id(self) -> None:
        seen: set[str] = set()
        invalid = {
            "run_id": "run-1",
            "started_at": "bad-time",
            "status": "success",
            "latency_ms": "10",
            "query": "q",
        }
        valid = dict(invalid, started_at="2026-07-13T00:00:00Z")
        self.assertEqual(clean_row(invalid, seen)[1], "invalid:started_at")
        self.assertEqual(clean_row(valid, seen)[1], "duplicate:run_id")

    def test_missing_and_invalid_values_have_stable_reason_codes(self) -> None:
        base = {
            "run_id": "run-1",
            "started_at": "2026-07-13T00:00:00Z",
            "status": "success",
            "latency_ms": "10",
            "query": "q",
        }
        cases = (
            (dict(base, run_id=""), "missing:run_id"),
            (dict(base, status="unknown"), "invalid:status"),
            (dict(base, started_at="not-a-time"), "invalid:started_at"),
            (dict(base, latency_ms="-1"), "invalid:latency_ms_range"),
            (dict(base, latency_ms="1_000"), "invalid:latency_ms_type"),
            (dict(base, latency_ms="300001"), "invalid:latency_ms_range"),
        )
        for row, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(clean_row(row, set())[1], expected)

    def test_sample_file_produces_three_clean_and_five_issue_rows(self) -> None:
        before = sha256(SAMPLE_INPUT.read_bytes()).hexdigest()
        with TemporaryDirectory() as directory:
            output = Path(directory) / "clean.csv"
            report = Path(directory) / "issues.csv"
            summary = clean_file(SAMPLE_INPUT, output, report)
            cleaned = read_csv(output)
            issues = read_csv(report)
        self.assertEqual(summary.accepted, 3)
        self.assertEqual(summary.rejected, 5)
        self.assertEqual([row["run_id"] for row in cleaned], ["run-001", "run-002", "run-003"])
        self.assertEqual(cleaned[2]["started_at"], "2026-07-13T01:02:00Z")
        self.assertEqual(len(issues), 5)
        self.assertTrue(all(len(row["row_sha256"]) == 64 for row in issues))
        self.assertEqual(sha256(SAMPLE_INPUT.read_bytes()).hexdigest(), before)

    def test_repeated_run_is_byte_deterministic_with_explicit_overwrite(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "clean.csv"
            report = Path(directory) / "issues.csv"
            first = clean_file(SAMPLE_INPUT, output, report)
            first_bytes = (output.read_bytes(), report.read_bytes())
            second = clean_file(
                SAMPLE_INPUT,
                output,
                report,
                overwrite=True,
            )
            second_bytes = (output.read_bytes(), report.read_bytes())
        self.assertEqual(first, second)
        self.assertEqual(first_bytes, second_bytes)

    def test_existing_outputs_and_overlapping_paths_are_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "clean.csv"
            report = root / "issues.csv"
            output.write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                clean_file(SAMPLE_INPUT, output, report)
            with self.assertRaises(ValueError):
                clean_file(SAMPLE_INPUT, SAMPLE_INPUT, report)
            directory_target = root / "directory-target"
            directory_target.mkdir()
            with self.assertRaises(ValueError):
                clean_file(
                    SAMPLE_INPUT,
                    directory_target,
                    report,
                    overwrite=True,
                )

    def test_schema_must_match_exactly(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            bad = root / "bad.csv"
            bad.write_text("run_id,status\n1,ok\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                clean_file(bad, root / "out.csv", root / "report.csv")

    def test_main_reports_counts_and_returns_success(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "clean.csv"
            report = Path(directory) / "issues.csv"
            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "--input",
                        str(SAMPLE_INPUT),
                        "--output",
                        str(output),
                        "--report",
                        str(report),
                    ]
                )
        self.assertEqual(result, 0)
        self.assertIn("accepted=3 rejected=5", stdout.getvalue())
        self.assertIn("duplicate:run_id=1", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
