"""Audit a synthetic structured OCR fixture using only the standard library."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable


class FixtureError(ValueError):
    """Raised when the fixture cannot satisfy the documented input contract."""


TOP_FIELDS = {"schema_version", "document_id", "review_threshold", "pages"}
PAGE_FIELDS = {"page", "width", "height", "blocks"}
BLOCK_FIELDS = {
    "block_id",
    "type",
    "bbox",
    "order",
    "reference_text",
    "predicted_text",
    "confidence",
    "critical",
}
TABLE_FIELDS = {"reference_shape", "predicted_shape"}
BLOCK_TYPES = {"title", "text", "field", "table"}


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
    value: Any,
    required: set[str],
    *,
    optional: set[str] | None = None,
    context: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FixtureError(f"{context} must be an object")
    optional = optional or set()
    actual = set(value)
    missing = sorted(required - actual)
    unknown = sorted(actual - required - optional)
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


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _validate_shape(value: Any, context: str) -> None:
    if not (
        isinstance(value, list)
        and len(value) == 2
        and all(_is_positive_int(item) for item in value)
    ):
        raise FixtureError(f"{context} must be [positive_rows, positive_columns]")


def validate_fixture(payload: Any) -> dict[str, Any]:
    """Validate the complete teaching contract and return the typed object."""
    root = _require_exact_fields(payload, TOP_FIELDS, context="fixture")
    if root["schema_version"] != "1.0":
        raise FixtureError("schema_version must be '1.0'")
    document_id = root["document_id"]
    if not isinstance(document_id, str) or not document_id.strip():
        raise FixtureError("document_id must be a non-empty string")
    threshold = root["review_threshold"]
    if not _is_finite_number(threshold) or not 0 <= threshold <= 1:
        raise FixtureError("review_threshold must be a finite number between 0 and 1")
    pages = root["pages"]
    if not isinstance(pages, list) or not pages:
        raise FixtureError("pages must be a non-empty array")

    page_numbers: list[int] = []
    for page_index, raw_page in enumerate(pages):
        context = f"pages[{page_index}]"
        page = _require_exact_fields(raw_page, PAGE_FIELDS, context=context)
        page_number = page["page"]
        if not _is_positive_int(page_number):
            raise FixtureError(f"{context}.page must be a positive integer")
        if not _is_positive_int(page["width"]) or not _is_positive_int(page["height"]):
            raise FixtureError(f"{context} width and height must be positive integers")
        blocks = page["blocks"]
        if not isinstance(blocks, list):
            raise FixtureError(f"{context}.blocks must be an array")
        page_numbers.append(page_number)

        for block_index, raw_block in enumerate(blocks):
            block_context = f"{context}.blocks[{block_index}]"
            if not isinstance(raw_block, dict):
                raise FixtureError(f"{block_context} must be an object")
            block_type = raw_block.get("type")
            required = BLOCK_FIELDS | ({"table"} if block_type == "table" else set())
            optional = {"table"} if block_type != "table" else set()
            block = _require_exact_fields(
                raw_block,
                required,
                optional=optional,
                context=block_context,
            )
            block_id = block["block_id"]
            if not isinstance(block_id, str) or not block_id.strip():
                raise FixtureError(f"{block_context}.block_id must be a non-empty string")
            if block_type not in BLOCK_TYPES:
                raise FixtureError(
                    f"{block_context}.type must be one of {sorted(BLOCK_TYPES)}"
                )
            if block_type != "table" and "table" in block:
                raise FixtureError(f"{block_context}.table is only valid for table blocks")
            bbox = block["bbox"]
            if not (
                isinstance(bbox, list)
                and len(bbox) == 4
                and all(_is_finite_number(item) for item in bbox)
            ):
                raise FixtureError(f"{block_context}.bbox must contain four finite numbers")
            left, top, right, bottom = bbox
            if not (
                0 <= left < right <= page["width"]
                and 0 <= top < bottom <= page["height"]
            ):
                raise FixtureError(f"{block_context}.bbox must stay inside the page")
            if not _is_positive_int(block["order"]):
                raise FixtureError(f"{block_context}.order must be a positive integer")
            for field in ("reference_text", "predicted_text"):
                if not isinstance(block[field], str):
                    raise FixtureError(f"{block_context}.{field} must be a string")
            confidence = block["confidence"]
            if not _is_finite_number(confidence) or not 0 <= confidence <= 1:
                raise FixtureError(
                    f"{block_context}.confidence must be a finite number between 0 and 1"
                )
            if not isinstance(block["critical"], bool):
                raise FixtureError(f"{block_context}.critical must be a boolean")
            if block_type == "table":
                table = _require_exact_fields(
                    block["table"], TABLE_FIELDS, context=f"{block_context}.table"
                )
                _validate_shape(table["reference_shape"], f"{block_context}.reference_shape")
                _validate_shape(table["predicted_shape"], f"{block_context}.predicted_shape")

    if len(page_numbers) != len(set(page_numbers)):
        raise FixtureError("page numbers must be unique")
    if page_numbers != sorted(page_numbers):
        raise FixtureError("pages must be ordered by page number")
    return root


def load_fixture(path: Path) -> dict[str, Any]:
    """Load UTF-8 JSON while rejecting duplicate keys and non-finite numbers."""
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


def edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    """Return the Levenshtein distance between two token sequences."""
    previous = list(range(len(hypothesis) + 1))
    for row, ref_token in enumerate(reference, start=1):
        current = [row]
        for col, hyp_token in enumerate(hypothesis, start=1):
            substitution = previous[col - 1] + (ref_token != hyp_token)
            current.append(min(previous[col] + 1, current[col - 1] + 1, substitution))
        previous = current
    return previous[-1]


def error_rate(reference: Iterable[str], hypothesis: Iterable[str]) -> float:
    """Calculate edit errors divided by reference length."""
    ref = list(reference)
    hyp = list(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return edit_distance(ref, hyp) / len(ref)


def audit(payload: dict[str, Any]) -> dict[str, Any]:
    """Audit validated OCR output without opening images or calling a model."""
    validate_fixture(payload)
    errors: list[str] = []
    reviews: list[dict[str, Any]] = []
    references: list[str] = []
    predictions: list[str] = []
    seen_ids: set[str] = set()
    order_valid = True
    table_checks: list[bool] = []
    threshold = payload["review_threshold"]
    block_count = 0

    for page in payload["pages"]:
        blocks = page["blocks"]
        orders = [block["order"] for block in blocks]
        if len(set(orders)) != len(orders) or orders != sorted(orders):
            order_valid = False
            errors.append(f"page {page['page']}: order must be unique and increasing")

        for block in blocks:
            block_count += 1
            block_id = block["block_id"]
            if block_id in seen_ids:
                errors.append(f"duplicate block_id: {block_id}")
            seen_ids.add(block_id)
            reference = block["reference_text"]
            prediction = block["predicted_text"]
            references.append(reference)
            predictions.append(prediction)

            reasons: list[str] = []
            if block["confidence"] < threshold:
                reasons.append("low_confidence")
            if block["critical"] and reference != prediction:
                reasons.append("critical_text_mismatch")
            if block["type"] == "table":
                table = block["table"]
                shape_matches = table["reference_shape"] == table["predicted_shape"]
                table_checks.append(shape_matches)
                if not shape_matches:
                    reasons.append("table_shape_mismatch")
            if reasons:
                reviews.append({"block_id": block_id, "reasons": reasons})

    reference_text = "\n".join(references)
    predicted_text = "\n".join(predictions)
    return {
        "document_id": payload["document_id"],
        "block_count": block_count,
        "cer": round(error_rate(reference_text, predicted_text), 6),
        "wer": round(error_rate(reference_text.split(), predicted_text.split()), 6),
        "order_valid": order_valid,
        "table_structure_match": all(table_checks) if table_checks else None,
        "review_queue": reviews,
        "errors": errors,
        "notes": [
            "fixture and cost-free standard-library audit only",
            "no image, OCR engine, network, or model was used",
        ],
    }


def run_self_test() -> None:
    """Run a tiny smoke check without relying on removable assert statements."""
    if edit_distance(list("ABC"), list("ADCX")) != 2:
        raise RuntimeError("edit-distance self-test failed")
    if error_rate([], []) != 0.0 or error_rate([], ["extra"]) != 1.0:
        raise RuntimeError("error-rate self-test failed")
    fixture = {
        "schema_version": "1.0",
        "document_id": "self-test",
        "review_threshold": 0.9,
        "pages": [{"page": 1, "width": 10, "height": 10, "blocks": []}],
    }
    if audit(fixture)["errors"]:
        raise RuntimeError("audit self-test failed")
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
        payload = load_fixture(args.fixture)
        report = audit(payload)
    except FixtureError as exc:
        print(f"fixture error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
