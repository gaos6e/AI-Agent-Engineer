"""Audit a provider-neutral video generation job package offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


REQUIRED_ACCEPTANCE = {
    "prompt_adherence",
    "visual_quality",
    "motion",
    "identity",
    "continuity",
    "audio_captions",
    "safety",
    "rights",
}
ALLOWED_CONTAINERS = {"mp4", "mov", "webm", "mkv"}
REFERENCE_ROLES = {
    "first_frame",
    "last_frame",
    "identity_reference",
    "style_reference",
    "source_video",
    "mask",
}
TOP_FIELDS = {
    "schema_version",
    "project_id",
    "purpose",
    "audience",
    "technical",
    "shots",
    "audio",
    "captions",
    "risk",
    "acceptance",
    "recovery",
    "budget",
    "adapter",
}
TECHNICAL_FIELDS = {
    "duration_seconds",
    "fps",
    "width",
    "height",
    "aspect_ratio",
    "container",
}
SHOT_FIELDS = {
    "shot_id",
    "start_seconds",
    "end_seconds",
    "shot_size",
    "camera_motion",
    "subject",
    "action",
    "setting",
    "continuity_anchors",
    "prompt",
    "reference_assets",
}
ASSET_FIELDS = {
    "asset_id",
    "role",
    "source_reference",
    "content_sha256",
    "rights_reference",
}
AUDIO_FIELDS = {
    "mode",
    "narration",
    "music_rights_confirmed",
    "voice_subject_consent",
    "sync_review_required",
}
CAPTION_FIELDS = {"format", "language", "cues"}
CUE_FIELDS = {"start_seconds", "end_seconds", "text"}
RISK_FIELDS = {
    "reference_rights_confirmed",
    "real_person",
    "person_consent",
    "human_review_required",
    "provenance_plan",
    "disclosure_plan",
}
ACCEPTANCE_FIELDS = {"dimension", "criterion", "hard_failure"}
RECOVERY_FIELDS = {
    "max_attempts_per_shot",
    "checkpoint_between_shots",
    "retry_policy",
    "fallback",
    "manual_escalation_required",
}
BUDGET_FIELDS = {
    "max_total_attempts",
    "max_generated_seconds",
    "pricing_source_required_at_run",
    "manual_approval_before_budget_increase",
}
ADAPTER_FIELDS = {"provider", "model", "version", "documentation_checked_on"}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SECRET_PATTERN = re.compile(
    r"(?:\bsk-[A-Za-z0-9_-]{20,}\b|\bbearer\s+[A-Za-z0-9._-]{20,}\b)",
    re.IGNORECASE,
)
INCOMPLETE_VALUE_PATTERN = re.compile(
    r"(?:to[_ -]?be[_ -]?filled|not[_ -]?set)", re.IGNORECASE
)
EPSILON = 1e-6


class FixtureError(ValueError):
    """Raised when a package violates the documented structural contract."""


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _positive_number(value: Any) -> bool:
    return _finite_number(value) and value > 0


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _reject_constant(value: str) -> None:
    raise FixtureError(f"不允许非有限 JSON 数字：{value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FixtureError(f"JSON 键重复：{key}")
        result[key] = value
    return result


def _require_exact_fields(
    value: Any, required: set[str], *, context: str
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FixtureError(f"{context} 必须是 object")
    actual = set(value)
    missing = sorted(required - actual)
    unknown = sorted(actual - required)
    if missing:
        raise FixtureError(f"{context} 缺少字段：{', '.join(missing)}")
    if unknown:
        raise FixtureError(f"{context} 包含未知字段：{', '.join(unknown)}")
    return value


def _validate_string_list(value: Any, *, context: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise FixtureError(f"{context} 必须是非空列表")
    if any(not _nonempty_text(item) for item in value):
        raise FixtureError(f"{context} 的每项必须是非空字符串")
    if len(value) != len(set(value)):
        raise FixtureError(f"{context} 不允许重复项")
    return value


def _parse_ratio(value: Any) -> float | None:
    if not _nonempty_text(value) or value.count(":") != 1:
        return None
    left, right = value.split(":")
    try:
        numerator = float(left)
        denominator = float(right)
    except ValueError:
        return None
    if (
        not math.isfinite(numerator)
        or not math.isfinite(denominator)
        or numerator <= 0
        or denominator <= 0
    ):
        return None
    return numerator / denominator


def validate_contract(package: Any) -> dict[str, Any]:
    """Validate exact fields and types without making policy decisions."""
    root = _require_exact_fields(package, TOP_FIELDS, context="根对象")
    if root["schema_version"] != "1.0":
        raise FixtureError("schema_version 必须是 '1.0'")
    for field in ("project_id", "purpose", "audience"):
        if not _nonempty_text(root[field]):
            raise FixtureError(f"{field} 必须是非空字符串")

    technical = _require_exact_fields(
        root["technical"], TECHNICAL_FIELDS, context="technical"
    )
    if not _positive_number(technical["duration_seconds"]):
        raise FixtureError("technical.duration_seconds 必须是有限正数")
    for field in ("fps", "width", "height"):
        if not _positive_int(technical[field]):
            raise FixtureError(f"technical.{field} 必须是正整数")
    if _parse_ratio(technical["aspect_ratio"]) is None:
        raise FixtureError("technical.aspect_ratio 必须是有限正数比例，例如 16:9")
    if not _nonempty_text(technical["container"]):
        raise FixtureError("technical.container 必须是非空字符串")

    shots = root["shots"]
    if not isinstance(shots, list) or not shots:
        raise FixtureError("shots 必须是非空列表")
    seen_asset_ids: set[str] = set()
    for shot_index, raw_shot in enumerate(shots):
        context = f"shots[{shot_index}]"
        shot = _require_exact_fields(raw_shot, SHOT_FIELDS, context=context)
        for field in (
            "shot_id",
            "shot_size",
            "camera_motion",
            "subject",
            "action",
            "setting",
            "prompt",
        ):
            if not _nonempty_text(shot[field]):
                raise FixtureError(f"{context}.{field} 必须是非空字符串")
        start = shot["start_seconds"]
        end = shot["end_seconds"]
        if not _finite_number(start) or start < 0:
            raise FixtureError(f"{context}.start_seconds 必须是有限非负数")
        if not _finite_number(end) or end <= start:
            raise FixtureError(f"{context}.end_seconds 必须是大于起点的有限数")
        _validate_string_list(
            shot["continuity_anchors"], context=f"{context}.continuity_anchors"
        )
        assets = shot["reference_assets"]
        if not isinstance(assets, list):
            raise FixtureError(f"{context}.reference_assets 必须是列表")
        for asset_index, raw_asset in enumerate(assets):
            asset_context = f"{context}.reference_assets[{asset_index}]"
            asset = _require_exact_fields(
                raw_asset, ASSET_FIELDS, context=asset_context
            )
            for field in ASSET_FIELDS - {"role", "content_sha256"}:
                if not _nonempty_text(asset[field]):
                    raise FixtureError(f"{asset_context}.{field} 必须是非空字符串")
            if asset["role"] not in REFERENCE_ROLES:
                raise FixtureError(
                    f"{asset_context}.role 必须是 {sorted(REFERENCE_ROLES)} 之一"
                )
            if not isinstance(
                asset["content_sha256"], str
            ) or not SHA256_PATTERN.fullmatch(asset["content_sha256"]):
                raise FixtureError(
                    f"{asset_context}.content_sha256 必须是 64 位小写十六进制"
                )
            if asset["asset_id"] in seen_asset_ids:
                raise FixtureError(f"reference asset_id 重复：{asset['asset_id']}")
            seen_asset_ids.add(asset["asset_id"])

    audio = _require_exact_fields(root["audio"], AUDIO_FIELDS, context="audio")
    for field in ("mode", "narration", "voice_subject_consent"):
        if not _nonempty_text(audio[field]):
            raise FixtureError(f"audio.{field} 必须是非空字符串")
    for field in ("music_rights_confirmed", "sync_review_required"):
        if not isinstance(audio[field], bool):
            raise FixtureError(f"audio.{field} 必须是布尔值")

    captions = _require_exact_fields(
        root["captions"], CAPTION_FIELDS, context="captions"
    )
    for field in ("format", "language"):
        if not _nonempty_text(captions[field]):
            raise FixtureError(f"captions.{field} 必须是非空字符串")
    cues = captions["cues"]
    if not isinstance(cues, list) or not cues:
        raise FixtureError("captions.cues 必须是非空列表")
    for cue_index, raw_cue in enumerate(cues):
        context = f"captions.cues[{cue_index}]"
        cue = _require_exact_fields(raw_cue, CUE_FIELDS, context=context)
        start = cue["start_seconds"]
        end = cue["end_seconds"]
        if not _finite_number(start) or start < 0:
            raise FixtureError(f"{context}.start_seconds 必须是有限非负数")
        if not _finite_number(end) or end <= start:
            raise FixtureError(f"{context}.end_seconds 必须是大于起点的有限数")
        if not _nonempty_text(cue["text"]):
            raise FixtureError(f"{context}.text 必须是非空字符串")

    risk = _require_exact_fields(root["risk"], RISK_FIELDS, context="risk")
    for field in (
        "reference_rights_confirmed",
        "real_person",
        "human_review_required",
    ):
        if not isinstance(risk[field], bool):
            raise FixtureError(f"risk.{field} 必须是布尔值")
    for field in ("person_consent", "provenance_plan", "disclosure_plan"):
        if not _nonempty_text(risk[field]):
            raise FixtureError(f"risk.{field} 必须是非空字符串")

    acceptance = root["acceptance"]
    if not isinstance(acceptance, list) or not acceptance:
        raise FixtureError("acceptance 必须是非空列表")
    for index, raw_item in enumerate(acceptance):
        context = f"acceptance[{index}]"
        item = _require_exact_fields(raw_item, ACCEPTANCE_FIELDS, context=context)
        for field in ("dimension", "criterion"):
            if not _nonempty_text(item[field]):
                raise FixtureError(f"{context}.{field} 必须是非空字符串")
        if not isinstance(item["hard_failure"], bool):
            raise FixtureError(f"{context}.hard_failure 必须是布尔值")

    recovery = _require_exact_fields(
        root["recovery"], RECOVERY_FIELDS, context="recovery"
    )
    if not _positive_int(recovery["max_attempts_per_shot"]):
        raise FixtureError("recovery.max_attempts_per_shot 必须是正整数")
    for field in ("checkpoint_between_shots", "manual_escalation_required"):
        if not isinstance(recovery[field], bool):
            raise FixtureError(f"recovery.{field} 必须是布尔值")
    for field in ("retry_policy", "fallback"):
        if not _nonempty_text(recovery[field]):
            raise FixtureError(f"recovery.{field} 必须是非空字符串")

    budget = _require_exact_fields(root["budget"], BUDGET_FIELDS, context="budget")
    if not _positive_int(budget["max_total_attempts"]):
        raise FixtureError("budget.max_total_attempts 必须是正整数")
    if not _positive_number(budget["max_generated_seconds"]):
        raise FixtureError("budget.max_generated_seconds 必须是有限正数")
    for field in (
        "pricing_source_required_at_run",
        "manual_approval_before_budget_increase",
    ):
        if not isinstance(budget[field], bool):
            raise FixtureError(f"budget.{field} 必须是布尔值")

    adapter = _require_exact_fields(root["adapter"], ADAPTER_FIELDS, context="adapter")
    for field in ADAPTER_FIELDS:
        if not _nonempty_text(adapter[field]):
            raise FixtureError(f"adapter.{field} 必须是非空字符串")
    return root


def audit_package(package: dict[str, Any]) -> list[str]:
    """Return policy and cross-field findings for a contract-valid package."""
    validate_contract(package)
    errors: list[str] = []
    technical = package["technical"]
    duration = float(technical["duration_seconds"])
    ratio = _parse_ratio(technical["aspect_ratio"])
    if ratio is not None and abs(technical["width"] / technical["height"] - ratio) > 0.01:
        errors.append("technical 宽高与 aspect_ratio 不一致。")
    if technical["container"].lower() not in ALLOWED_CONTAINERS:
        errors.append(f"technical.container 必须是 {sorted(ALLOWED_CONTAINERS)} 之一。")

    seen_shot_ids: set[str] = set()
    previous_end = 0.0
    for index, shot in enumerate(package["shots"]):
        shot_id = shot["shot_id"]
        if shot_id in seen_shot_ids:
            errors.append(f"shot_id 重复：{shot_id}。")
        seen_shot_ids.add(shot_id)
        start = float(shot["start_seconds"])
        end = float(shot["end_seconds"])
        if index == 0 and abs(start) > EPSILON:
            errors.append("第一个镜头必须从 0 秒开始。")
        if index > 0:
            if start < previous_end - EPSILON:
                errors.append(f"shots[{index}] 与前一镜头重叠。")
            elif start > previous_end + EPSILON:
                errors.append(f"shots[{index}] 与前一镜头之间有空隙。")
        if end > duration + EPSILON:
            errors.append(f"shots[{index}] 超出总时长。")
        previous_end = end
        for asset in shot["reference_assets"]:
            if INCOMPLETE_VALUE_PATTERN.search(asset["source_reference"]):
                errors.append(f"素材 {asset['asset_id']} 的 source_reference 不能保留占位值。")
            if INCOMPLETE_VALUE_PATTERN.search(asset["rights_reference"]):
                errors.append(f"素材 {asset['asset_id']} 的 rights_reference 不能保留占位值。")
    if abs(previous_end - duration) > EPSILON:
        errors.append("镜头时间线没有完整覆盖 technical.duration_seconds。")

    audio = package["audio"]
    if audio["music_rights_confirmed"] is not True:
        errors.append("audio.music_rights_confirmed 必须显式为 true。")
    if audio["sync_review_required"] is not True:
        errors.append("audio.sync_review_required 必须显式为 true。")

    captions = package["captions"]
    if captions["format"].lower() != "webvtt":
        errors.append("captions.format 必须是 webvtt。")
    previous_cue_end = 0.0
    for index, cue in enumerate(captions["cues"]):
        start = float(cue["start_seconds"])
        end = float(cue["end_seconds"])
        if start < previous_cue_end - EPSILON:
            errors.append(f"captions.cues[{index}] 与前一条字幕重叠。")
        if end > duration + EPSILON:
            errors.append(f"captions.cues[{index}] 超出总时长。")
        previous_cue_end = end

    risk = package["risk"]
    if risk["reference_rights_confirmed"] is not True:
        errors.append("risk.reference_rights_confirmed 必须显式为 true。")
    if risk["human_review_required"] is not True:
        errors.append("risk.human_review_required 必须显式为 true。")
    if risk["real_person"] and risk["person_consent"].casefold() in {
        "not_applicable",
        "not_required",
    }:
        errors.append("包含真人时必须记录有效的人物同意依据。")

    dimensions: set[str] = set()
    for item in package["acceptance"]:
        dimension = item["dimension"]
        if dimension in dimensions:
            errors.append(f"acceptance dimension 重复：{dimension}。")
        dimensions.add(dimension)
    missing_dimensions = sorted(REQUIRED_ACCEPTANCE - dimensions)
    if missing_dimensions:
        errors.append(f"acceptance 缺少维度：{missing_dimensions}。")

    recovery = package["recovery"]
    if recovery["checkpoint_between_shots"] is not True:
        errors.append("recovery.checkpoint_between_shots 必须显式为 true。")
    if recovery["manual_escalation_required"] is not True:
        errors.append("recovery.manual_escalation_required 必须显式为 true。")

    budget = package["budget"]
    shot_count = len(package["shots"])
    if budget["max_total_attempts"] < shot_count:
        errors.append("budget.max_total_attempts 至少应允许每个镜头尝试一次。")
    maximum_attempt_envelope = shot_count * recovery["max_attempts_per_shot"]
    if budget["max_total_attempts"] > maximum_attempt_envelope:
        errors.append("budget.max_total_attempts 超过逐镜头重试上限形成的总包络。")
    if budget["max_generated_seconds"] + EPSILON < duration:
        errors.append("budget.max_generated_seconds 不能小于成片总时长。")
    if budget["pricing_source_required_at_run"] is not True:
        errors.append("budget 必须要求运行时核对定价来源。")
    if budget["manual_approval_before_budget_increase"] is not True:
        errors.append("预算上调前必须要求人工批准。")

    adapter = package["adapter"]
    for field in ("provider", "model", "version"):
        if INCOMPLETE_VALUE_PATTERN.search(adapter[field]):
            errors.append(f"adapter.{field} 不能保留占位值。")
    try:
        date.fromisoformat(adapter["documentation_checked_on"])
    except ValueError:
        errors.append("adapter.documentation_checked_on 必须是 YYYY-MM-DD。")

    serialized = json.dumps(package, ensure_ascii=False, allow_nan=False)
    if SECRET_PATTERN.search(serialized):
        errors.append("任务包疑似包含真实密钥或 Bearer 凭据。")
    return errors


def validate_package(package: Any) -> list[str]:
    """Compatibility helper returning contract and audit errors as strings."""
    try:
        validated = validate_contract(package)
    except FixtureError as exc:
        return [f"输入合同错误：{exc}"]
    return audit_package(validated)


def normalized_hash(package: dict[str, Any]) -> str:
    payload = json.dumps(
        package,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_package(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise FixtureError(f"无法读取任务包：{exc}") from exc
    try:
        package = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise FixtureError(
            f"JSON 无效（第 {exc.lineno} 行，第 {exc.colno} 列）：{exc.msg}"
        ) from exc
    return validate_contract(package)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", nargs="?", type=Path, help="UTF-8 JSON video job package")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.package is None:
        print("package is required", file=sys.stderr)
        return 2
    try:
        package = load_package(args.package)
    except FixtureError as exc:
        print(f"输入合同错误：{exc}", file=sys.stderr)
        return 2

    errors = audit_package(package)
    if errors:
        print("审计失败：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "审计通过："
        f"project_id={package['project_id']}, "
        f"shots={len(package['shots'])}, "
        f"duration={package['technical']['duration_seconds']}s, "
        f"package_sha256={normalized_hash(package)[:16]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
