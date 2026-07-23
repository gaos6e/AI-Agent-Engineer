from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from strict_json import (
    DEFAULT_LIMITS,
    JsonDataError,
    dumps_strict,
    iter_json_lines,
    load_json_file,
    loads_strict,
    scan_json_lines,
    write_json_atomic,
    write_json_lines_atomic,
)


class StrictJsonTests(unittest.TestCase):
    def test_six_json_value_kinds_keep_exact_python_types(self) -> None:
        value = loads_strict(
            '{"object":{},"array":[],"string":"x","integer":1,'
            '"real":1.5,"true":true,"false":false,"null":null}'
        )
        self.assertIs(type(value["object"]), dict)
        self.assertIs(type(value["array"]), list)
        self.assertIs(type(value["string"]), str)
        self.assertIs(type(value["integer"]), int)
        self.assertIs(type(value["real"]), float)
        self.assertIs(type(value["true"]), bool)
        self.assertIs(type(value["false"]), bool)
        self.assertIsNone(value["null"])

    def test_chinese_escapes_and_windows_path_round_trip(self) -> None:
        value = {"title": "会议", "path": "D:\\data\\input.json", "line": "a\nb"}
        self.assertEqual(loads_strict(dumps_strict(value)), value)

    def test_duplicate_members_are_rejected_at_any_depth(self) -> None:
        for text in ('{"x":1,"x":2}', '{"nested":{"x":1,"x":2}}'):
            with self.subTest(text=text), self.assertRaises(JsonDataError) as caught:
                loads_strict(text)
            self.assertEqual(caught.exception.code, "duplicate_key")

    def test_non_standard_and_overflowed_numbers_are_rejected(self) -> None:
        for text in ("NaN", "Infinity", "-Infinity", "1e9999"):
            with self.subTest(text=text), self.assertRaises(JsonDataError) as caught:
                loads_strict(text)
            self.assertEqual(caught.exception.code, "non_finite_number")

    def test_excessively_long_integer_token_is_rejected(self) -> None:
        with self.assertRaises(JsonDataError) as caught:
            loads_strict("1" * (DEFAULT_LIMITS.max_number_chars + 1))
        self.assertEqual(caught.exception.code, "number_too_long")

    def test_unpaired_surrogate_is_rejected(self) -> None:
        with self.assertRaises(JsonDataError) as caught:
            loads_strict('"\\ud800"')
        self.assertEqual(caught.exception.code, "invalid_unicode")

    def test_syntax_error_keeps_line_and_column_without_payload(self) -> None:
        secret = "TOP_SECRET_SENTINEL"
        payload = '{\n  "value": "' + secret + '",\n}'
        try:
            json.loads(payload)
        except json.JSONDecodeError as parser_error:
            expected_line = parser_error.lineno
            expected_column = parser_error.colno
        else:
            self.fail("test payload must be invalid JSON")
        with self.assertRaises(JsonDataError) as caught:
            loads_strict(payload)
        error = caught.exception
        self.assertEqual(error.code, "invalid_json")
        self.assertEqual(error.line, expected_line)
        self.assertEqual(error.column, expected_column)
        self.assertNotIn(secret, str(error))

    def test_document_depth_container_string_and_total_limits(self) -> None:
        cases = [
            ("[[[0]]]", replace(DEFAULT_LIMITS, max_depth=3)),
            ('[1,2,3]', replace(DEFAULT_LIMITS, max_container_items=2)),
            ('"abcd"', replace(DEFAULT_LIMITS, max_string_chars=3)),
            ('[1,2]', replace(DEFAULT_LIMITS, max_total_values=2)),
        ]
        for text, limits in cases:
            with self.subTest(text=text), self.assertRaises(JsonDataError) as caught:
                loads_strict(text, limits=limits)
            self.assertEqual(caught.exception.code, "resource_limit")

    def test_invalid_limits_are_rejected_before_work(self) -> None:
        with self.assertRaises(ValueError):
            loads_strict("{}", limits=replace(DEFAULT_LIMITS, max_depth=0))

    def test_file_loader_rejects_invalid_utf8_bom_and_oversize(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            cases = [
                (b'{"x":"\xff"}', DEFAULT_LIMITS, "invalid_utf8"),
                (b"\xef\xbb\xbf{}", DEFAULT_LIMITS, "bom_forbidden"),
                (b"12345", replace(DEFAULT_LIMITS, max_document_bytes=4), "resource_limit"),
            ]
            for payload, limits, code in cases:
                with self.subTest(code=code):
                    path.write_bytes(payload)
                    with self.assertRaises(JsonDataError) as caught:
                        load_json_file(path, limits=limits)
                    self.assertEqual(caught.exception.code, code)

    def test_missing_file_is_normalized(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaises(JsonDataError) as caught:
                load_json_file(Path(directory) / "missing.json")
        self.assertEqual(caught.exception.code, "io_error")

    def test_encoder_rejects_non_json_types_keys_numbers_and_surrogates(self) -> None:
        cases = [
            {1: "coerced-key"},
            (1, 2),
            {"value": math.nan},
            {"value": math.inf},
            {"value": "\ud800"},
        ]
        for value in cases:
            with self.subTest(value=type(value).__name__), self.assertRaises(JsonDataError):
                dumps_strict(value)

    def test_atomic_json_write_replaces_complete_document(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text('{"old":true}\n', encoding="utf-8")
            write_json_atomic(path, {"name": "会议助理", "ok": True})
            payload = path.read_bytes()
            self.assertFalse(payload.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(payload.endswith(b"\n"))
            self.assertEqual(load_json_file(path), {"name": "会议助理", "ok": True})

    def test_encoded_document_and_final_newline_share_the_byte_contract(self) -> None:
        value = {"x": 1}
        document = dumps_strict(value)
        document_bytes = len(document.encode("utf-8"))
        self.assertEqual(
            dumps_strict(
                value,
                limits=replace(DEFAULT_LIMITS, max_document_bytes=document_bytes),
            ),
            document,
        )
        with self.assertRaises(JsonDataError):
            dumps_strict(
                value,
                limits=replace(DEFAULT_LIMITS, max_document_bytes=document_bytes - 1),
            )

        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            exact_file_limits = replace(
                DEFAULT_LIMITS,
                max_document_bytes=document_bytes + 1,
            )
            write_json_atomic(path, value, limits=exact_file_limits)
            self.assertEqual(load_json_file(path, limits=exact_file_limits), value)

            path.write_text('{"old":true}\n', encoding="utf-8", newline="\n")
            original = path.read_bytes()
            with self.assertRaises(JsonDataError):
                write_json_atomic(
                    path,
                    value,
                    limits=replace(DEFAULT_LIMITS, max_document_bytes=document_bytes),
                )
            self.assertEqual(path.read_bytes(), original)

    def test_atomic_replace_failure_preserves_old_file_and_cleans_temp(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            original = b'{"old":true}\n'
            path.write_bytes(original)
            with patch("strict_json.os.replace", side_effect=OSError("simulated")):
                with self.assertRaises(JsonDataError) as caught:
                    write_json_atomic(path, {"new": True})
            self.assertEqual(caught.exception.code, "io_error")
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])

    def test_json_lines_supports_lf_crlf_and_final_line_without_newline(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_bytes(b'{"n":1}\r\n{"n":2}\n{"n":3}')
            self.assertEqual(
                list(iter_json_lines(path)),
                [(1, {"n": 1}), (2, {"n": 2}), (3, {"n": 3})],
            )

    def test_json_lines_content_limit_excludes_lf_and_crlf_symmetrically(self) -> None:
        record = {"x": 1}
        encoded = dumps_strict(record, indent=None).encode("utf-8")
        limits = replace(
            DEFAULT_LIMITS,
            max_document_bytes=1,
            max_jsonl_line_bytes=len(encoded),
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            write_json_lines_atomic(path, [record], limits=limits)
            self.assertEqual(path.read_bytes(), encoded + b"\n")
            self.assertEqual(list(iter_json_lines(path, limits=limits)), [(1, record)])

            for suffix in (b"\n", b"\r\n", b""):
                with self.subTest(suffix=suffix):
                    path.write_bytes(encoded + suffix)
                    self.assertEqual(list(iter_json_lines(path, limits=limits)), [(1, record)])

            too_small = replace(limits, max_jsonl_line_bytes=len(encoded) - 1)
            for suffix in (b"\n", b"\r\n", b""):
                with self.subTest(too_small_suffix=suffix):
                    path.write_bytes(encoded + suffix)
                    result = list(scan_json_lines(path, limits=too_small))[0]
                    self.assertEqual(result.error.code, "line_too_large")
            with self.assertRaises(JsonDataError):
                write_json_lines_atomic(path, [record], limits=too_small)

    def test_json_lines_reports_blank_bad_and_later_valid_lines(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_bytes(b"\n{bad}\n{\"ok\":true}\n")
            results = list(scan_json_lines(path))
        self.assertEqual([result.line for result in results], [1, 2, 3])
        self.assertEqual(results[0].error.code, "blank_line")
        self.assertEqual(results[1].error.code, "invalid_json")
        self.assertEqual(results[2].value, {"ok": True})

    def test_json_lines_rejects_duplicate_nonfinite_utf8_bom_and_long_line(self) -> None:
        limits = replace(DEFAULT_LIMITS, max_jsonl_line_bytes=20)
        payloads = [
            (b'{"x":1,"x":2}\n', "duplicate_key"),
            (b'{"x":NaN}\n', "non_finite_number"),
            (b'{"x":"\xff"}\n', "invalid_utf8"),
            (b"\xef\xbb\xbf{}\n", "bom_forbidden"),
            (b'{"long":"12345678901234567890"}\n', "line_too_large"),
        ]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            for payload, code in payloads:
                with self.subTest(code=code):
                    path.write_bytes(payload)
                    result = list(scan_json_lines(path, limits=limits))[0]
                    self.assertEqual(result.error.code, code)

    def test_json_lines_record_and_total_byte_limits_are_fatal(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_bytes(b"1\n2\n")
            with self.assertRaises(JsonDataError):
                list(scan_json_lines(path, limits=replace(DEFAULT_LIMITS, max_jsonl_records=1)))
            with self.assertRaises(JsonDataError):
                list(scan_json_lines(path, limits=replace(DEFAULT_LIMITS, max_jsonl_total_bytes=2)))

    def test_atomic_json_lines_round_trip_and_failure_cleanup(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "report.jsonl"
            write_json_lines_atomic(path, [{"line": 1}, {"line": 2}])
            self.assertEqual(
                [value for _, value in iter_json_lines(path)],
                [{"line": 1}, {"line": 2}],
            )
            original = path.read_bytes()
            with self.assertRaises(JsonDataError):
                write_json_lines_atomic(path, [{"ok": True}, {"bad": object()}])
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])

    def test_empty_json_lines_output_still_validates_limits(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "report.jsonl"
            path.write_text("old\n", encoding="utf-8", newline="\n")
            with self.assertRaises(ValueError):
                write_json_lines_atomic(
                    path,
                    [],
                    limits=replace(DEFAULT_LIMITS, max_jsonl_records=0),
                )
            self.assertEqual(path.read_text(encoding="utf-8"), "old\n")


if __name__ == "__main__":
    unittest.main()
