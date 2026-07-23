"""Audit a provider-neutral image generation plan without generating media."""

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


ALLOWED_TASK_TYPES = {
    "text_to_image",
    "image_to_image",
    "inpainting",
    "outpainting",
    "variation",
}
ALLOWED_FORMATS = {"png", "jpeg", "webp"}
REFERENCE_ROLES = {
    "source_image",
    "mask",
    "style_reference",
    "identity_reference",
    "layout_reference",
}
REQUIRED_ACCEPTANCE = {
    "prompt_adherence",
    "composition",
    "text",
    "visual_quality",
    "safety",
    "rights",
}
TOP_FIELDS = {
    "schema_version",
    "task_id",
    "purpose",
    "audience",
    "task_type",
    "prompt",
    "output",
    "reference_assets",
    "lineage",
    "governance",
    "risk",
    "acceptance",
    "budget",
    "reproducibility",
}
PROMPT_FIELDS = {
    "subject",
    "action",
    "setting",
    "composition",
    "lighting",
    "style",
    "text_rendering",
    "must_include",
    "must_avoid",
}
OUTPUT_FIELDS = {"aspect_ratio", "width", "height", "format", "candidate_count"}
ASSET_FIELDS = {
    "asset_id",
    "source_revision",
    "role",
    "source_reference",
    "content_sha256",
    "rights_reference",
    "acl_reference",
}
LINEAGE_FIELDS = {"source_revision", "transform_id", "release_id"}
GOVERNANCE_FIELDS = {
    "object_acl_required",
    "deletion_propagation_plan",
    "evidence_policy",
}
RISK_FIELDS = {
    "rights_confirmed",
    "real_person",
    "minor",
    "sensitive_context",
    "human_review_required",
    "provenance_plan",
    "disclosure_plan",
}
ACCEPTANCE_FIELDS = {"dimension", "criterion", "hard_failure"}
BUDGET_FIELDS = {
    "max_attempts",
    "max_outputs",
    "pricing_source_required_at_run",
    "manual_approval_before_budget_increase",
}
REPRODUCIBILITY_FIELDS = {
    "provider",
    "model",
    "adapter_version",
    "seed_policy",
    "save_normalized_request_hash",
    "documentation_checked_on",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SECRET_PATTERN = re.compile(
    r"(?:\bsk-[A-Za-z0-9_-]{20,}\b|\bbearer\s+[A-Za-z0-9._-]{20,}\b)",
    re.IGNORECASE,
)
INCOMPLETE_VALUE_PATTERN = re.compile(
    r"(?:to[_ -]?be[_ -]?filled|not[_ -]?set)", re.IGNORECASE
)


class FixtureError(ValueError):
    """Raised when a plan violates the documented structural contract."""


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


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


def validate_contract(plan: Any) -> dict[str, Any]:
    """Validate exact fields and types without making policy decisions."""
    root = _require_exact_fields(plan, TOP_FIELDS, context="根对象")
    if root["schema_version"] != "1.0":
        raise FixtureError("schema_version 必须是 '1.0'")
    for field in ("task_id", "purpose", "audience"):
        if not _nonempty_text(root[field]):
            raise FixtureError(f"{field} 必须是非空字符串")
    if root["task_type"] not in ALLOWED_TASK_TYPES:
        raise FixtureError(f"task_type 必须是 {sorted(ALLOWED_TASK_TYPES)} 之一")

    lineage = _require_exact_fields(root["lineage"], LINEAGE_FIELDS, context="lineage")
    for field in LINEAGE_FIELDS:
        if not _nonempty_text(lineage[field]):
            raise FixtureError(f"lineage.{field} 必须是非空字符串")

    governance = _require_exact_fields(
        root["governance"], GOVERNANCE_FIELDS, context="governance"
    )
    if not isinstance(governance["object_acl_required"], bool):
        raise FixtureError("governance.object_acl_required 必须是布尔值")
    for field in ("deletion_propagation_plan", "evidence_policy"):
        if not _nonempty_text(governance[field]):
            raise FixtureError(f"governance.{field} 必须是非空字符串")

    prompt = _require_exact_fields(root["prompt"], PROMPT_FIELDS, context="prompt")
    for field in PROMPT_FIELDS - {"must_include", "must_avoid"}:
        if not _nonempty_text(prompt[field]):
            raise FixtureError(f"prompt.{field} 必须是非空字符串")
    _validate_string_list(prompt["must_include"], context="prompt.must_include")
    _validate_string_list(prompt["must_avoid"], context="prompt.must_avoid")

    output = _require_exact_fields(root["output"], OUTPUT_FIELDS, context="output")
    if _parse_ratio(output["aspect_ratio"]) is None:
        raise FixtureError("output.aspect_ratio 必须是有限正数比例，例如 4:5")
    for field in ("width", "height", "candidate_count"):
        if not _positive_int(output[field]):
            raise FixtureError(f"output.{field} 必须是正整数")
    if not _nonempty_text(output["format"]):
        raise FixtureError("output.format 必须是非空字符串")

    assets = root["reference_assets"]
    if not isinstance(assets, list):
        raise FixtureError("reference_assets 必须是列表")
    seen_asset_ids: set[str] = set()
    for index, raw_asset in enumerate(assets):
        context = f"reference_assets[{index}]"
        asset = _require_exact_fields(raw_asset, ASSET_FIELDS, context=context)
        for field in ASSET_FIELDS - {"role", "content_sha256"}:
            if not _nonempty_text(asset[field]):
                raise FixtureError(f"{context}.{field} 必须是非空字符串")
        if asset["role"] not in REFERENCE_ROLES:
            raise FixtureError(f"{context}.role 必须是 {sorted(REFERENCE_ROLES)} 之一")
        if not isinstance(asset["content_sha256"], str) or not SHA256_PATTERN.fullmatch(
            asset["content_sha256"]
        ):
            raise FixtureError(f"{context}.content_sha256 必须是 64 位小写十六进制")
        if asset["asset_id"] in seen_asset_ids:
            raise FixtureError(f"reference_assets 的 asset_id 重复：{asset['asset_id']}")
        seen_asset_ids.add(asset["asset_id"])

    risk = _require_exact_fields(root["risk"], RISK_FIELDS, context="risk")
    for field in (
        "rights_confirmed",
        "real_person",
        "minor",
        "sensitive_context",
        "human_review_required",
    ):
        if not isinstance(risk[field], bool):
            raise FixtureError(f"risk.{field} 必须是布尔值")
    for field in ("provenance_plan", "disclosure_plan"):
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

    budget = _require_exact_fields(root["budget"], BUDGET_FIELDS, context="budget")
    for field in ("max_attempts", "max_outputs"):
        if not _positive_int(budget[field]):
            raise FixtureError(f"budget.{field} 必须是正整数")
    for field in (
        "pricing_source_required_at_run",
        "manual_approval_before_budget_increase",
    ):
        if not isinstance(budget[field], bool):
            raise FixtureError(f"budget.{field} 必须是布尔值")

    reproducibility = _require_exact_fields(
        root["reproducibility"], REPRODUCIBILITY_FIELDS, context="reproducibility"
    )
    for field in REPRODUCIBILITY_FIELDS - {"save_normalized_request_hash"}:
        if not _nonempty_text(reproducibility[field]):
            raise FixtureError(f"reproducibility.{field} 必须是非空字符串")
    if not isinstance(reproducibility["save_normalized_request_hash"], bool):
        raise FixtureError("reproducibility.save_normalized_request_hash 必须是布尔值")
    return root


def audit_plan(plan: dict[str, Any]) -> list[str]:
    """Return policy and cross-field findings for a contract-valid plan."""
    validate_contract(plan)
    errors: list[str] = []
    output = plan["output"]
    ratio = _parse_ratio(output["aspect_ratio"])
    if ratio is not None and abs(output["width"] / output["height"] - ratio) > 0.01:
        errors.append("output 的宽高与 aspect_ratio 不一致。")
    if output["format"].lower() not in ALLOWED_FORMATS:
        errors.append(f"output.format 必须是 {sorted(ALLOWED_FORMATS)} 之一。")

    include = {item.casefold() for item in plan["prompt"]["must_include"]}
    avoid = {item.casefold() for item in plan["prompt"]["must_avoid"]}
    conflicts = sorted(include & avoid)
    if conflicts:
        errors.append(f"prompt.must_include 与 must_avoid 冲突：{conflicts}。")

    roles = {asset["role"] for asset in plan["reference_assets"]}
    for asset in plan["reference_assets"]:
        for field in (
            "source_reference",
            "source_revision",
            "rights_reference",
            "acl_reference",
        ):
            if INCOMPLETE_VALUE_PATTERN.search(asset[field]):
                errors.append(f"素材 {asset['asset_id']} 的 {field} 不能保留占位值。")
    required_roles = {
        "image_to_image": {"source_image"},
        "variation": {"source_image"},
        "outpainting": {"source_image"},
        "inpainting": {"source_image", "mask"},
    }.get(plan["task_type"], set())
    missing_roles = sorted(required_roles - roles)
    if missing_roles:
        errors.append(f"{plan['task_type']} 缺少参考素材角色：{missing_roles}。")

    risk = plan["risk"]
    if risk["rights_confirmed"] is not True:
        errors.append("risk.rights_confirmed 必须显式为 true。")
    if risk["human_review_required"] is not True:
        errors.append("risk.human_review_required 必须显式为 true。")

    lineage = plan["lineage"]
    for field in LINEAGE_FIELDS:
        if INCOMPLETE_VALUE_PATTERN.search(lineage[field]):
            errors.append(f"lineage.{field} 不能保留占位值。")

    governance = plan["governance"]
    if governance["object_acl_required"] is not True:
        errors.append("governance.object_acl_required 必须在评分前启用对象级授权/ACL。")
    if INCOMPLETE_VALUE_PATTERN.search(governance["deletion_propagation_plan"]):
        errors.append("governance.deletion_propagation_plan 不能保留占位值。")
    if governance["evidence_policy"] != "evidence_supported":
        errors.append(
            "governance.evidence_policy 必须为 'evidence_supported'，不得把生成图单独当作事实证据。"
        )

    dimensions: set[str] = set()
    for item in plan["acceptance"]:
        dimension = item["dimension"]
        if dimension in dimensions:
            errors.append(f"acceptance dimension 重复：{dimension}。")
        dimensions.add(dimension)
    missing_dimensions = sorted(REQUIRED_ACCEPTANCE - dimensions)
    if missing_dimensions:
        errors.append(f"acceptance 缺少维度：{missing_dimensions}。")

    budget = plan["budget"]
    if output["candidate_count"] > budget["max_outputs"]:
        errors.append("output.candidate_count 不能超过 budget.max_outputs。")
    if budget["pricing_source_required_at_run"] is not True:
        errors.append("budget 必须要求运行时核对定价来源。")
    if budget["manual_approval_before_budget_increase"] is not True:
        errors.append("预算上调前必须要求人工批准。")

    reproducibility = plan["reproducibility"]
    if reproducibility["save_normalized_request_hash"] is not True:
        errors.append("必须保存规范化请求哈希。")
    for field in ("provider", "model", "adapter_version"):
        if INCOMPLETE_VALUE_PATTERN.search(reproducibility[field]):
            errors.append(f"reproducibility.{field} 不能保留占位值。")
    try:
        date.fromisoformat(reproducibility["documentation_checked_on"])
    except ValueError:
        errors.append("reproducibility.documentation_checked_on 必须是 YYYY-MM-DD。")

    serialized = json.dumps(plan, ensure_ascii=False, allow_nan=False)
    if SECRET_PATTERN.search(serialized):
        errors.append("任务清单疑似包含真实密钥或 Bearer 凭据。")
    return errors


def validate_plan(plan: Any) -> list[str]:
    """Compatibility helper returning contract and audit errors as strings."""
    try:
        validated = validate_contract(plan)
    except FixtureError as exc:
        return [f"输入合同错误：{exc}"]
    return audit_plan(validated)


def normalized_hash(plan: dict[str, Any]) -> str:
    payload = json.dumps(
        plan,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_plan(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise FixtureError(f"无法读取任务清单：{exc}") from exc
    try:
        plan = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise FixtureError(
            f"JSON 无效（第 {exc.lineno} 行，第 {exc.colno} 列）：{exc.msg}"
        ) from exc
    return validate_contract(plan)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", nargs="?", type=Path, help="UTF-8 JSON task plan")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.plan is None:
        print("plan is required", file=sys.stderr)
        return 2
    try:
        plan = load_plan(args.plan)
    except FixtureError as exc:
        print(f"输入合同错误：{exc}", file=sys.stderr)
        return 2

    errors = audit_plan(plan)
    if errors:
        print("审计失败：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "审计通过："
        f"task_id={plan['task_id']}, "
        f"type={plan['task_type']}, "
        f"candidates={plan['output']['candidate_count']}, "
        f"request_sha256={normalized_hash(plan)[:16]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
