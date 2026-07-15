"""Evaluate a synthetic ASR transcript fixture with the standard library."""

from __future__ import annotations

import argparse
import json
import math
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable


NORMALIZATION_NAME = "nfkc-casefold-remove-punctuation-v1"
TOP_FIELDS = {"schema_version", "session_id", "normalization", "segments"}
SEGMENT_FIELDS = {
    "segment_id",
    "start_seconds",
    "end_seconds",
    "speaker",
    "slice",
    "reference",
    "hypothesis",
}


class FixtureError(ValueError):
    """Raised when a fixture violates the documented structural contract."""


def _reject_constant(value: str) -> None:
    raise FixtureError(f"non-finite JSON number is not allowed: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FixtureError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_exact_fields(
    value: Any, required: set[str], *, context: str
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FixtureError(f"{context} must be an object")
    actual = set(value)
    missing = sorted(required - actual)
    unknown = sorted(actual - required)
    if missing:
        raise FixtureError(f"{context} missing fields: {', '.join(missing)}")
    if unknown:
        raise FixtureError(f"{context} has unknown fields: {', '.join(unknown)}")
    return value


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def validate_fixture(payload: Any) -> dict[str, Any]:
    """Validate schema and types; temporal quality checks remain audit findings."""
    root = _require_exact_fields(payload, TOP_FIELDS, context="fixture")
    if root["schema_version"] != "1.0":
        raise FixtureError("schema_version must be '1.0'")
    session_id = root["session_id"]
    if not isinstance(session_id, str) or not session_id.strip():
        raise FixtureError("session_id must be a non-empty string")
    if root["normalization"] != NORMALIZATION_NAME:
        raise FixtureError(f"normalization must be {NORMALIZATION_NAME!r}")
    segments = root["segments"]
    if not isinstance(segments, list):
        raise FixtureError("segments must be an array")

    for index, raw_segment in enumerate(segments):
        context = f"segments[{index}]"
        segment = _require_exact_fields(raw_segment, SEGMENT_FIELDS, context=context)
        segment_id = segment["segment_id"]
        if not isinstance(segment_id, str) or not segment_id.strip():
            raise FixtureError(f"{context}.segment_id must be a non-empty string")
        for field in ("start_seconds", "end_seconds"):
            if not _is_finite_number(segment[field]):
                raise FixtureError(f"{context}.{field} must be a finite number")
        speaker = segment["speaker"]
        if speaker is not None and (not isinstance(speaker, str) or not speaker.strip()):
            raise FixtureError(f"{context}.speaker must be null or a non-empty string")
        slice_name = segment["slice"]
        if not isinstance(slice_name, str) or not slice_name.strip():
            raise FixtureError(f"{context}.slice must be a non-empty string")
        for field in ("reference", "hypothesis"):
            if not isinstance(segment[field], str):
                raise FixtureError(f"{context}.{field} must be a string")
    return root


def load_fixture(path: Path) -> dict[str, Any]:
    """Load UTF-8 strict JSON and validate the full structural contract."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise FixtureError(f"cannot read fixture: {exc}") from exc
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise FixtureError(
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    return validate_fixture(payload)


def normalize(text: str) -> str:
    """Apply the versioned teaching normalization symmetrically."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    cleaned_tokens: list[str] = []
    for token in normalized.split():
        cleaned = "".join(
            char for char in token if not unicodedata.category(char).startswith("P")
        )
        if cleaned:
            cleaned_tokens.append(cleaned)
    return " ".join(cleaned_tokens)


def edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    """Return Levenshtein distance between two token sequences."""
    previous = list(range(len(hypothesis) + 1))
    for row, ref_token in enumerate(reference, start=1):
        current = [row]
        for col, hyp_token in enumerate(hypothesis, start=1):
            current.append(
                min(
                    previous[col] + 1,
                    current[col - 1] + 1,
                    previous[col - 1] + (ref_token != hyp_token),
                )
            )
        previous = current
    return previous[-1]


def tokens_for_wer(text: str) -> list[str]:
    return normalize(text).split()


def tokens_for_cer(text: str) -> list[str]:
    return list(normalize(text).replace(" ", ""))


def score_pairs(
    pairs: list[tuple[str, str]], tokenizer: Callable[[str], list[str]]
) -> dict[str, float | int | None]:
    """Micro-average edit errors over reference units."""
    errors = 0
    reference_units = 0
    for reference, hypothesis in pairs:
        ref_tokens = tokenizer(reference)
        errors += edit_distance(ref_tokens, tokenizer(hypothesis))
        reference_units += len(ref_tokens)
    rate = errors / reference_units if reference_units else None
    return {
        "errors": errors,
        "reference_units": reference_units,
        "rate": round(rate, 6) if rate is not None else None,
    }


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a validated transcript without reading or generating audio."""
    validate_fixture(payload)
    audit_errors: list[str] = []
    timestamp_errors: list[str] = []
    seen_ids: set[str] = set()
    previous_end = 0.0
    all_pairs: list[tuple[str, str]] = []
    slice_pairs: dict[str, list[tuple[str, str]]] = defaultdict(list)
    speaker_count = 0
    segments = payload["segments"]

    for segment in segments:
        segment_id = segment["segment_id"]
        if segment_id in seen_ids:
            audit_errors.append(f"duplicate segment_id: {segment_id}")
        seen_ids.add(segment_id)

        start = segment["start_seconds"]
        end = segment["end_seconds"]
        if start < 0 or end <= start:
            timestamp_errors.append(f"{segment_id}: invalid time range")
        else:
            if start < previous_end:
                timestamp_errors.append(f"{segment_id}: overlaps previous segment")
            previous_end = max(previous_end, end)

        pair = (segment["reference"], segment["hypothesis"])
        all_pairs.append(pair)
        slice_pairs[segment["slice"]].append(pair)
        if segment["speaker"] is not None:
            speaker_count += 1

    by_slice = {
        name: {
            "segments": len(pairs),
            "wer": score_pairs(pairs, tokens_for_wer),
            "cer": score_pairs(pairs, tokens_for_cer),
        }
        for name, pairs in sorted(slice_pairs.items())
    }
    return {
        "session_id": payload["session_id"],
        "normalization": NORMALIZATION_NAME,
        "segments": len(segments),
        "micro_wer": score_pairs(all_pairs, tokens_for_wer),
        "micro_cer": score_pairs(all_pairs, tokens_for_cer),
        "by_slice": by_slice,
        "speaker_coverage": round(speaker_count / len(segments), 6)
        if segments
        else None,
        "timestamp_errors": timestamp_errors,
        "audit_errors": audit_errors,
        "notes": [
            "synthetic transcripts and standard-library scoring only",
            "no audio, VAD, diarization, network, or ASR model was used",
        ],
    }


def run_self_test() -> None:
    """Run smoke checks that remain active under Python optimization."""
    if edit_distance(["abc"], ["adc"]) != 1:
        raise RuntimeError("word-distance self-test failed")
    if edit_distance(list("ABC"), list("ADCX")) != 2:
        raise RuntimeError("character-distance self-test failed")
    if normalize("Hello, WORLD!") != "hello world":
        raise RuntimeError("normalization self-test failed")
    report = evaluate(
        {
            "schema_version": "1.0",
            "session_id": "self-test",
            "normalization": NORMALIZATION_NAME,
            "segments": [],
        }
    )
    if report["audit_errors"] or report["timestamp_errors"]:
        raise RuntimeError("evaluation self-test failed")
    print("self-test: PASS")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", nargs="?", type=Path, help="UTF-8 JSON fixture")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.self_test:
        run_self_test()
        return 0
    if args.fixture is None:
        print("fixture is required unless --self-test is used", file=sys.stderr)
        return 2
    try:
        report = evaluate(load_fixture(args.fixture))
    except FixtureError as exc:
        print(f"fixture error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if report["audit_errors"] or report["timestamp_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
