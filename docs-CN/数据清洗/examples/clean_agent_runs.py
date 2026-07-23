"""清洗小型 Agent 运行日志，同时保留源文件与可审计问题报告。"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Sequence


OUTPUT_FIELDS = ("run_id", "started_at", "status", "latency_ms", "query")
REPORT_FIELDS = ("line", "run_id", "reason", "row_sha256")
STATUS_MAP = {
    "ok": "success",
    "success": "success",
    "failed": "error",
    "error": "error",
    "canceled": "cancelled",
    "cancelled": "cancelled",
}
LATENCY_PATTERN = re.compile(r"-?[0-9]+")
MAX_LATENCY_MS = 300_000


@dataclass(frozen=True)
class CleanSummary:
    accepted: int
    rejected: int
    reasons: tuple[tuple[str, int], ...]


def normalize_query(value: str) -> str:
    """只规范换行和首尾空白，不折叠代码或 Markdown 内部空白。"""

    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def parse_timestamp(value: str) -> str:
    """解析含时区的 ISO 8601 时间并统一输出为 UTC。"""

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone_required")
    utc_value = parsed.astimezone(timezone.utc)
    timespec = "microseconds" if utc_value.microsecond else "seconds"
    return utc_value.isoformat(timespec=timespec).replace("+00:00", "Z")


def row_fingerprint(row: dict[str | None, object]) -> str:
    """对原始行计算确定性摘要，报告问题时无需复制敏感正文。"""

    payload = [
        ("<extra>" if key is None else key, value)
        for key, value in row.items()
    ]
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    return sha256(serialized.encode("utf-8")).hexdigest()


def clean_row(
    row: dict[str | None, str | list[str] | None],
    seen_ids: set[str],
) -> tuple[dict[str, str] | None, str]:
    """按确定性契约清洗一行，并返回结果或单一主原因。"""

    run_id = str(row.get("run_id") or "").strip()
    if run_id:
        if run_id in seen_ids:
            return None, "duplicate:run_id"
        # 输入流中首次出现的 ID 占有身份，即使该行随后因其他规则失败。
        seen_ids.add(run_id)

    if None in row:
        return None, "invalid:column_count"

    raw = {
        field: str(row.get(field) or "")
        for field in OUTPUT_FIELDS
    }
    normalized = {
        "run_id": run_id,
        "started_at": raw["started_at"].strip(),
        "status": raw["status"].strip(),
        "latency_ms": raw["latency_ms"].strip(),
        "query": normalize_query(raw["query"]),
    }
    missing = [field for field in OUTPUT_FIELDS if not normalized[field]]
    if missing:
        return None, "missing:" + ",".join(missing)

    status = STATUS_MAP.get(normalized["status"].lower())
    if status is None:
        return None, "invalid:status"

    try:
        timestamp = parse_timestamp(normalized["started_at"])
    except (TypeError, ValueError, OverflowError):
        return None, "invalid:started_at"

    latency_text = normalized["latency_ms"]
    if LATENCY_PATTERN.fullmatch(latency_text) is None:
        return None, "invalid:latency_ms_type"
    latency = int(latency_text)
    if not 0 <= latency <= MAX_LATENCY_MS:
        return None, "invalid:latency_ms_range"

    return {
        "run_id": run_id,
        "started_at": timestamp,
        "status": status,
        "latency_ms": str(latency),
        "query": normalized["query"],
    }, ""


def ensure_safe_paths(
    input_path: Path,
    output_path: Path,
    report_path: Path,
    *,
    overwrite: bool,
) -> None:
    """拒绝源/输出重合、缺失源文件和未授权覆盖。"""

    resolved = [
        path.resolve()
        for path in (input_path, output_path, report_path)
    ]
    if len(set(resolved)) != 3:
        raise ValueError("input, output and report paths must be different")
    if not input_path.is_file():
        raise ValueError("input must be an existing file")
    if output_path.is_dir():
        raise ValueError("output must be a file path, not a directory")
    if report_path.is_dir():
        raise ValueError("report must be a file path, not a directory")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"output already exists: {output_path}")
    if report_path.exists() and not overwrite:
        raise FileExistsError(f"report already exists: {report_path}")


def _stage_csv(
    destination: Path,
    fieldnames: Sequence[str],
    rows: Sequence[dict[str, str]],
) -> Path:
    """在目标目录生成完整临时文件，成功后再由调用方替换目标。"""

    destination.parent.mkdir(parents=True, exist_ok=True)
    handle = NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
        delete=False,
    )
    staged = Path(handle.name)
    try:
        with handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    except BaseException:
        staged.unlink(missing_ok=True)
        raise
    return staged


def _publish_outputs(
    output_path: Path,
    report_path: Path,
    cleaned: Sequence[dict[str, str]],
    issues: Sequence[dict[str, str]],
) -> None:
    """分别以临时文件完整写入，再原子替换两个目标文件。"""

    staged_output: Path | None = None
    staged_report: Path | None = None
    try:
        staged_output = _stage_csv(output_path, OUTPUT_FIELDS, cleaned)
        staged_report = _stage_csv(report_path, REPORT_FIELDS, issues)
        staged_output.replace(output_path)
        staged_output = None
        staged_report.replace(report_path)
        staged_report = None
    finally:
        if staged_output is not None:
            staged_output.unlink(missing_ok=True)
        if staged_report is not None:
            staged_report.unlink(missing_ok=True)


def clean_file(
    input_path: Path,
    output_path: Path,
    report_path: Path,
    *,
    overwrite: bool = False,
) -> CleanSummary:
    """读取、校验、清洗并发布两个确定性 CSV 产物。"""

    ensure_safe_paths(
        input_path,
        output_path,
        report_path,
        overwrite=overwrite,
    )

    cleaned: list[dict[str, str]] = []
    issues: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    reason_counts: Counter[str] = Counter()
    with input_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != OUTPUT_FIELDS:
            raise ValueError(
                "input schema must exactly match: "
                + ",".join(OUTPUT_FIELDS)
            )
        for row in reader:
            result, reason = clean_row(row, seen_ids)
            if result is None:
                reason_counts[reason] += 1
                issues.append(
                    {
                        "line": str(reader.line_num),
                        "run_id": str(row.get("run_id") or "").strip(),
                        "reason": reason,
                        "row_sha256": row_fingerprint(row),
                    }
                )
            else:
                cleaned.append(result)

    _publish_outputs(output_path, report_path, cleaned, issues)
    return CleanSummary(
        accepted=len(cleaned),
        rejected=len(issues),
        reasons=tuple(sorted(reason_counts.items())),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="清洗教学用 Agent 运行日志 CSV",
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="显式允许覆盖既有 output/report；永不允许覆盖 input",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = clean_file(
        args.input,
        args.output,
        args.report,
        overwrite=args.overwrite,
    )
    reason_text = ",".join(
        f"{reason}={count}"
        for reason, count in summary.reasons
    )
    print(
        f"accepted={summary.accepted} rejected={summary.rejected} "
        f"reasons={reason_text or 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
