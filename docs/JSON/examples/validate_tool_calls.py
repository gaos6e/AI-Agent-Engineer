"""Validate JSONL tool suggestions without executing any tool."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
from typing import Any

from jsonschema import Draft202012Validator

from strict_json import JsonDataError, load_json_file, scan_json_lines
from validate_agent_config import ContractError, build_validator, validate_schema


REQUEST_ID = re.compile(r"^req-[0-9]{4}$")
TRUSTED_TOOL_POLICY = {
    "search_notes": {"requires_approval": False},
    "send_email": {"requires_approval": True},
}


def _safe_request_id(record: Any) -> str | None:
    if type(record) is not dict:
        return None
    value = record.get("request_id")
    if type(value) is str and REQUEST_ID.fullmatch(value):
        return value
    return None


def _base_report(line: int, *, request_id: str | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {"line": line}
    if request_id is not None:
        report["request_id"] = request_id
    return report


def _reject_report(
    line: int,
    code: str,
    *,
    request_id: str | None = None,
    pointer: str = "",
    keyword: str | None = None,
) -> dict[str, Any]:
    report = _base_report(line, request_id=request_id)
    report.update({"status": "rejected", "code": code})
    if pointer:
        report["pointer"] = pointer
    if keyword:
        report["keyword"] = keyword
    return report


def classify_tool_suggestion(
    record: Any,
    validator: Draft202012Validator,
) -> tuple[str, str]:
    """Return a safe status; this function never dispatches a tool."""

    validate_schema(record, validator)
    policy = TRUSTED_TOOL_POLICY.get(record["tool"])
    if policy is None:
        raise ContractError("unknown_tool", "tool is absent from the trusted registry", pointer="/tool")
    if policy["requires_approval"]:
        return "approval_required", "human_approval_required"
    return "validated_not_executed", "validated_only"


def process_tool_call_file(
    input_path: Path,
    schema_path: Path,
) -> list[dict[str, Any]]:
    """Produce redacted reports for every JSONL record and keep parsing errors local."""

    schema = load_json_file(schema_path)
    if type(schema) is not dict:
        raise ContractError("invalid_schema", "tool schema must be an object")
    validator = build_validator(schema)
    reports: list[dict[str, Any]] = []
    seen_request_ids: set[str] = set()

    for result in scan_json_lines(input_path):
        if result.error is not None:
            reports.append(_reject_report(result.line, result.error.code))
            continue

        request_id = _safe_request_id(result.value)
        try:
            status, code = classify_tool_suggestion(result.value, validator)
        except ContractError as error:
            reports.append(
                _reject_report(
                    result.line,
                    error.code,
                    request_id=request_id,
                    pointer=error.pointer,
                    keyword=error.keyword,
                )
            )
            continue

        if request_id is None:
            # The schema should already reject this, but retain a fail-closed guard.
            reports.append(_reject_report(result.line, "unsafe_request_id"))
            continue
        if request_id in seen_request_ids:
            reports.append(
                _reject_report(
                    result.line,
                    "duplicate_request_id",
                    request_id=request_id,
                    pointer="/request_id",
                )
            )
            continue
        seen_request_ids.add(request_id)

        report = _base_report(result.line, request_id=request_id)
        report.update({"status": status, "code": code})
        reports.append(report)
    return reports


def report_counts(reports: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(report["status"]) for report in reports)
    return dict(sorted(counts.items()))


def main() -> int:
    base = Path(__file__).resolve().parent
    try:
        reports = process_tool_call_file(
            base / "tool_calls.jsonl",
            base / "tool_call.schema.json",
        )
    except (JsonDataError, ContractError) as error:
        print(f"pipeline failed: {error.code}")
        return 1
    print("report counts:", report_counts(reports))
    print("no tools executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
