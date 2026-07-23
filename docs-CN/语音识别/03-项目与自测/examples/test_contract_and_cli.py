from __future__ import annotations

import ast
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from evaluate_transcript import (
    FixtureError,
    NORMALIZATION_NAME,
    edit_distance,
    evaluate,
    load_fixture,
    normalize,
    score_pairs,
    tokens_for_cer,
    tokens_for_wer,
    validate_fixture,
)


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "evaluate_transcript.py"
FIXTURE = HERE / "asr_fixture.json"


def valid_payload() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TemporaryFileCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="asr-test-", dir=HERE)
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "fixture.json"

    def write_text(self, text: str) -> Path:
        self.path.write_text(text, encoding="utf-8")
        return self.path

    def write_payload(self, payload: object) -> Path:
        return self.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False))


class StrictJsonTests(TemporaryFileCase):
    def test_loads_valid_fixture(self) -> None:
        self.assertEqual(load_fixture(FIXTURE)["session_id"], "synthetic-meeting-001")

    def test_rejects_duplicate_key(self) -> None:
        path = self.write_text(
            '{"schema_version":"1.1","session_id":"x",'
            '"normalization":"nfkc-casefold-remove-punctuation-v1",'
            '"segments":[],"segments":[]}'
        )
        with self.assertRaisesRegex(FixtureError, "duplicate JSON key"):
            load_fixture(path)

    def test_rejects_nan(self) -> None:
        raw = FIXTURE.read_text(encoding="utf-8").replace("0.0", "NaN", 1)
        with self.assertRaisesRegex(FixtureError, "non-finite"):
            load_fixture(self.write_text(raw))

    def test_rejects_infinity(self) -> None:
        raw = FIXTURE.read_text(encoding="utf-8").replace("0.0", "Infinity", 1)
        with self.assertRaisesRegex(FixtureError, "non-finite"):
            load_fixture(self.write_text(raw))

    def test_rejects_malformed_json(self) -> None:
        with self.assertRaisesRegex(FixtureError, "invalid JSON"):
            load_fixture(self.write_text("{"))

    def test_rejects_missing_file(self) -> None:
        with self.assertRaisesRegex(FixtureError, "cannot read fixture"):
            load_fixture(self.path)

    def test_rejects_invalid_utf8(self) -> None:
        self.path.write_bytes(b"\xff\xfe")
        with self.assertRaisesRegex(FixtureError, "cannot read fixture"):
            load_fixture(self.path)

    def test_rejects_non_object_root(self) -> None:
        with self.assertRaisesRegex(FixtureError, "fixture must be an object"):
            load_fixture(self.write_text("[]"))


class TopLevelContractTests(unittest.TestCase):
    def assert_invalid(self, payload: object, pattern: str) -> None:
        with self.assertRaisesRegex(FixtureError, pattern):
            validate_fixture(payload)

    def test_accepts_valid_payload(self) -> None:
        self.assertEqual(validate_fixture(valid_payload())["schema_version"], "1.1")

    def test_missing_field(self) -> None:
        payload = valid_payload()
        del payload["session_id"]
        self.assert_invalid(payload, "missing fields")

    def test_unknown_field(self) -> None:
        payload = valid_payload()
        payload["language"] = "mixed"
        self.assert_invalid(payload, "unknown fields")

    def test_wrong_schema_version(self) -> None:
        payload = valid_payload()
        payload["schema_version"] = "2.0"
        self.assert_invalid(payload, "schema_version")

    def test_source_audio_requires_a_stable_asset_and_revision(self) -> None:
        payload = valid_payload()
        payload["source_audio"]["asset_id"] = " "
        self.assert_invalid(payload, "source_audio.asset_id")

    def test_source_audio_requires_asset_start_timebase(self) -> None:
        payload = valid_payload()
        payload["source_audio"]["timestamp_reference"] = "wall_clock"
        self.assert_invalid(payload, "timestamp_reference")

    def test_offline_fixture_rejects_an_audio_claim(self) -> None:
        payload = valid_payload()
        payload["source_audio"]["audio_available"] = True
        self.assert_invalid(payload, "audio_available")

    def test_audio_format_rejects_boolean_sample_rate(self) -> None:
        payload = valid_payload()
        payload["source_audio"]["analysis_format"]["sample_rate_hz"] = True
        self.assert_invalid(payload, "sample_rate_hz")

    def test_transcript_state_must_be_committed(self) -> None:
        payload = valid_payload()
        payload["transcript_state"] = "partial"
        self.assert_invalid(payload, "transcript_state")

    def test_empty_session_id(self) -> None:
        payload = valid_payload()
        payload["session_id"] = "  "
        self.assert_invalid(payload, "session_id")

    def test_non_string_session_id(self) -> None:
        payload = valid_payload()
        payload["session_id"] = 3
        self.assert_invalid(payload, "session_id")

    def test_unknown_normalization(self) -> None:
        payload = valid_payload()
        payload["normalization"] = "none"
        self.assert_invalid(payload, "normalization")

    def test_segments_must_be_array(self) -> None:
        payload = valid_payload()
        payload["segments"] = {}
        self.assert_invalid(payload, "segments must be an array")

    def test_empty_segments_are_valid(self) -> None:
        payload = valid_payload()
        payload["segments"] = []
        self.assertEqual(validate_fixture(payload)["segments"], [])


class SegmentContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = valid_payload()

    @property
    def segment(self) -> dict[str, Any]:
        return self.payload["segments"][0]

    def assert_invalid(self, pattern: str) -> None:
        with self.assertRaisesRegex(FixtureError, pattern):
            validate_fixture(self.payload)

    def test_segment_must_be_object(self) -> None:
        self.payload["segments"][0] = []
        self.assert_invalid("must be an object")

    def test_segment_missing_field(self) -> None:
        del self.segment["hypothesis"]
        self.assert_invalid("missing fields")

    def test_segment_unknown_field(self) -> None:
        self.segment["confidence"] = 0.9
        self.assert_invalid("unknown fields")

    def test_empty_segment_id(self) -> None:
        self.segment["segment_id"] = ""
        self.assert_invalid("segment_id")

    def test_non_string_segment_id(self) -> None:
        self.segment["segment_id"] = 1
        self.assert_invalid("segment_id")

    def test_start_rejects_boolean(self) -> None:
        self.segment["start_seconds"] = False
        self.assert_invalid("start_seconds")

    def test_end_rejects_string(self) -> None:
        self.segment["end_seconds"] = "2.4"
        self.assert_invalid("end_seconds")

    def test_start_rejects_nan(self) -> None:
        self.segment["start_seconds"] = float("nan")
        self.assert_invalid("start_seconds")

    def test_end_rejects_infinity(self) -> None:
        self.segment["end_seconds"] = float("inf")
        self.assert_invalid("end_seconds")

    def test_speaker_accepts_null(self) -> None:
        self.segment["speaker"] = None
        self.assertIsNone(validate_fixture(self.payload)["segments"][0]["speaker"])

    def test_speaker_rejects_empty_string(self) -> None:
        self.segment["speaker"] = " "
        self.assert_invalid("speaker")

    def test_speaker_rejects_number(self) -> None:
        self.segment["speaker"] = 2
        self.assert_invalid("speaker")

    def test_slice_rejects_empty_string(self) -> None:
        self.segment["slice"] = ""
        self.assert_invalid("slice")

    def test_slice_rejects_number(self) -> None:
        self.segment["slice"] = 2
        self.assert_invalid("slice")

    def test_reference_must_be_string(self) -> None:
        self.segment["reference"] = None
        self.assert_invalid("reference")

    def test_hypothesis_must_be_string(self) -> None:
        self.segment["hypothesis"] = []
        self.assert_invalid("hypothesis")


class NormalizationAndMetricTests(unittest.TestCase):
    def test_normalization_casefolds_and_removes_punctuation(self) -> None:
        self.assertEqual(normalize("Hello, WORLD!"), "hello world")

    def test_normalization_applies_nfkc(self) -> None:
        self.assertEqual(normalize("１２８．００"), "12800")

    def test_punctuation_only_token_does_not_leave_extra_space(self) -> None:
        self.assertEqual(normalize("a !!! b"), "a b")

    def test_wer_tokens_use_whitespace(self) -> None:
        self.assertEqual(tokens_for_wer("A, B!"), ["a", "b"])

    def test_cer_tokens_remove_spaces(self) -> None:
        self.assertEqual(tokens_for_cer("A B"), ["a", "b"])

    def test_edit_distance_identity(self) -> None:
        self.assertEqual(edit_distance(["a", "b"], ["a", "b"]), 0)

    def test_edit_distance_substitution_and_insertion(self) -> None:
        self.assertEqual(edit_distance(list("ABC"), list("ADCX")), 2)

    def test_edit_distance_deletion(self) -> None:
        self.assertEqual(edit_distance(["a", "b"], ["a"]), 1)

    def test_score_pairs_micro_averages(self) -> None:
        score = score_pairs([("a b", "a x"), ("c", "c")], tokens_for_wer)
        self.assertEqual(
            score,
            {
                "errors": 1,
                "reference_units": 3,
                "rate": 0.333333,
                "rate_status": "defined",
            },
        )

    def test_score_pairs_empty_reference_is_undefined(self) -> None:
        score = score_pairs([("", "extra")], tokens_for_wer)
        self.assertEqual(score["errors"], 1)
        self.assertIsNone(score["rate"])
        self.assertEqual(score["rate_status"], "undefined_no_reference_units")


class EvaluationTests(unittest.TestCase):
    def test_fixture_has_no_audit_or_timestamp_errors(self) -> None:
        report = evaluate(valid_payload())
        self.assertEqual(report["audit_errors"], [])
        self.assertEqual(report["timestamp_errors"], [])

    def test_report_records_normalization(self) -> None:
        self.assertEqual(evaluate(valid_payload())["normalization"], NORMALIZATION_NAME)

    def test_report_preserves_audio_and_revision_contract(self) -> None:
        report = evaluate(valid_payload())
        self.assertEqual(
            report["source_audio"]["source_revision"], "synthetic-audio-contract-v1"
        )
        self.assertEqual(report["transcript_revision"], "synthetic-transcript-v1")
        self.assertEqual(report["transcript_state"], "committed")

    def test_report_counts_segments(self) -> None:
        self.assertEqual(evaluate(valid_payload())["segments"], 3)

    def test_report_builds_sorted_slices(self) -> None:
        slices = list(evaluate(valid_payload())["by_slice"])
        self.assertEqual(slices, sorted(slices))

    def test_speaker_coverage_counts_non_null_labels(self) -> None:
        payload = valid_payload()
        payload["segments"][0]["speaker"] = None
        self.assertEqual(evaluate(payload)["speaker_coverage"], 0.666667)

    def test_empty_segments_have_null_speaker_coverage(self) -> None:
        payload = valid_payload()
        payload["segments"] = []
        self.assertIsNone(evaluate(payload)["speaker_coverage"])

    def test_duplicate_segment_id_is_audit_error(self) -> None:
        payload = valid_payload()
        payload["segments"][1]["segment_id"] = "s1"
        self.assertIn("duplicate segment_id", " ".join(evaluate(payload)["audit_errors"]))

    def test_negative_start_is_timestamp_error(self) -> None:
        payload = valid_payload()
        payload["segments"][0]["start_seconds"] = -1
        self.assertIn("invalid time range", " ".join(evaluate(payload)["timestamp_errors"]))

    def test_end_equal_to_start_is_timestamp_error(self) -> None:
        payload = valid_payload()
        payload["segments"][0]["end_seconds"] = 0.0
        self.assertIn("invalid time range", " ".join(evaluate(payload)["timestamp_errors"]))

    def test_overlap_is_timestamp_error(self) -> None:
        payload = valid_payload()
        payload["segments"][1]["start_seconds"] = 2.0
        self.assertIn("overlaps previous", " ".join(evaluate(payload)["timestamp_errors"]))

    def test_evaluate_revalidates_direct_payload(self) -> None:
        payload = valid_payload()
        payload["extra"] = True
        with self.assertRaises(FixtureError):
            evaluate(payload)

    def test_notes_disclose_missing_audio_and_model(self) -> None:
        notes = " ".join(evaluate(valid_payload())["notes"])
        self.assertIn("no audio", notes)
        self.assertIn("ASR model", notes)


class CliTests(TemporaryFileCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            check=False,
        )

    def test_valid_fixture_exit_zero(self) -> None:
        result = self.run_cli(str(FIXTURE))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["audit_errors"], [])

    def test_audit_finding_exit_one(self) -> None:
        payload = valid_payload()
        payload["segments"][1]["segment_id"] = "s1"
        result = self.run_cli(str(self.write_payload(payload)))
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_timestamp_finding_exit_one(self) -> None:
        payload = valid_payload()
        payload["segments"][1]["start_seconds"] = 2.0
        result = self.run_cli(str(self.write_payload(payload)))
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_contract_error_exit_two(self) -> None:
        payload = valid_payload()
        payload["extra"] = True
        result = self.run_cli(str(self.write_payload(payload)))
        self.assertEqual(result.returncode, 2)
        self.assertIn("fixture error", result.stderr)

    def test_missing_file_exit_two(self) -> None:
        self.assertEqual(self.run_cli(str(self.path)).returncode, 2)

    def test_missing_argument_exit_two(self) -> None:
        self.assertEqual(self.run_cli().returncode, 2)

    def test_self_test_exit_zero(self) -> None:
        result = self.run_cli("--self-test")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_production_code_has_no_assert_statement(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))


if __name__ == "__main__":
    unittest.main()
