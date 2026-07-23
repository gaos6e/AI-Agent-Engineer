"""Regression tests for the fixed-format Agent log parser."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from log_parser import parse_file, parse_line


VALID_LINE = (
    '2026-07-13T10:00:01Z level=INFO run_id=r1 '
    'latency_ms=120 message="completed"'
)


class ParseLineTests(unittest.TestCase):
    def test_valid_line_returns_typed_record(self) -> None:
        self.assertEqual(
            parse_line(VALID_LINE, 7),
            {
                "timestamp": "2026-07-13T10:00:01Z",
                "level": "INFO",
                "run_id": "r1",
                "latency_ms": 120,
                "message": "completed",
            },
        )

    def test_prefix_and_suffix_are_rejected(self) -> None:
        for line in (f"prefix {VALID_LINE}", f"{VALID_LINE} suffix"):
            with self.subTest(line=line):
                with self.assertRaisesRegex(ValueError, r"line 2: invalid log format"):
                    parse_line(line, 2)

    def test_unicode_digits_are_rejected_by_ascii_contract(self) -> None:
        cases = (
            VALID_LINE.replace("2026", "２０２６", 1),
            VALID_LINE.replace("latency_ms=120", "latency_ms=１２０"),
        )
        for line in cases:
            with self.subTest(line=line):
                with self.assertRaisesRegex(ValueError, r"invalid log format"):
                    parse_line(line, 3)

    def test_latency_limit_has_an_inclusive_boundary(self) -> None:
        allowed = VALID_LINE.replace("latency_ms=120", "latency_ms=300000")
        rejected = VALID_LINE.replace("latency_ms=120", "latency_ms=300001")
        self.assertEqual(parse_line(allowed, 1)["latency_ms"], 300_000)
        with self.assertRaisesRegex(ValueError, r"latency_ms exceeds limit"):
            parse_line(rejected, 1)

    def test_run_id_length_limit(self) -> None:
        allowed = VALID_LINE.replace("run_id=r1", f"run_id={'a' * 64}")
        rejected = VALID_LINE.replace("run_id=r1", f"run_id={'a' * 65}")
        self.assertEqual(parse_line(allowed, 1)["run_id"], "a" * 64)
        with self.assertRaisesRegex(ValueError, r"invalid log format"):
            parse_line(rejected, 1)

    def test_long_message_shape_remains_valid(self) -> None:
        long_message = "a" * 50_000
        line = VALID_LINE.replace("completed", long_message)
        self.assertEqual(parse_line(line, 1)["message"], long_message)


class ParseFileTests(unittest.TestCase):
    def test_sample_fixture_reports_one_specific_error(self) -> None:
        path = Path(__file__).with_name("sample.txt")
        records, errors = parse_file(path)
        self.assertEqual(len(records), 3)
        self.assertEqual(errors, ["line 3: invalid log format"])

    def test_file_keeps_successes_and_line_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.log"
            path.write_text(f"{VALID_LINE}\ninvalid\n", encoding="utf-8")
            records, errors = parse_file(path)

        self.assertEqual(len(records), 1)
        self.assertEqual(errors, ["line 2: invalid log format"])


class LiteralEscapingTests(unittest.TestCase):
    def test_user_literal_is_escaped_before_search(self) -> None:
        literal = "agent.v2+beta"
        pattern = re.compile(re.escape(literal))
        self.assertIsNotNone(pattern.search(f"use {literal} now"))
        self.assertIsNone(pattern.search("use agentXv22beta now"))


if __name__ == "__main__":
    unittest.main()
