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
    raise FixtureError(f"Non-finite JSON numbers are not allowed: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FixtureError(f"Duplicate JSON key: {key}")
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
        raise FixtureError(f"{context} is missing fields: {', '.join(missing)}")
    if unknown:
        raise FixtureError(f"{context} contains unknown fields: {', '.join(unknown)}")
    return value


def _validate_string_list(value: Any, *, context: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise FixtureError(f"{context} must be a non-empty list")
    if any(not _nonempty_text(item) for item in value):
        raise FixtureError(f"Every item in {context} must be a non-empty string")
    if len(value) != len(set(value)):
        raise FixtureError(f"{context} must not contain duplicate items")
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
    root = _require_exact_fields(plan, TOP_FIELDS, context="root object")
    if root["schema_version"] != "1.0":
        raise FixtureError("schema_version must be '1.0'")
    for field in ("task_id", "purpose", "audience"):
        if not _nonempty_text(root[field]):
            raise FixtureError(f"{field} must be a non-empty string")
    if root["task_type"] not in ALLOWED_TASK_TYPES:
        raise FixtureError(f"task_type must be one of {sorted(ALLOWED_TASK_TYPES)}")

    lineage = _require_exact_fields(root["lineage"], LINEAGE_FIELDS, context="lineage")
    for field in LINEAGE_FIELDS:
        if not _nonempty_text(lineage[field]):
            raise FixtureError(f"lineage.{field} must be a non-empty string")

    governance = _require_exact_fields(
        root["governance"], GOVERNANCE_FIELDS, context="governance"
    )
    if not isinstance(governance["object_acl_required"], bool):
        raise FixtureError("governance.object_acl_required must be a Boolean")
    for field in ("deletion_propagation_plan", "evidence_policy"):
        if not _nonempty_text(governance[field]):
            raise FixtureError(f"governance.{field} must be a non-empty string")

    prompt = _require_exact_fields(root["prompt"], PROMPT_FIELDS, context="prompt")
    for field in PROMPT_FIELDS - {"must_include", "must_avoid"}:
        if not _nonempty_text(prompt[field]):
            raise FixtureError(f"prompt.{field} must be a non-empty string")
    _validate_string_list(prompt["must_include"], context="prompt.must_include")
    _validate_string_list(prompt["must_avoid"], context="prompt.must_avoid")

    output = _require_exact_fields(root["output"], OUTPUT_FIELDS, context="output")
    if _parse_ratio(output["aspect_ratio"]) is None:
        raise FixtureError(
            "output.aspect_ratio must be a finite positive ratio, such as 4:5"
        )
    for field in ("width", "height", "candidate_count"):
        if not _positive_int(output[field]):
            raise FixtureError(f"output.{field} must be a positive integer")
    if not _nonempty_text(output["format"]):
        raise FixtureError("output.format must be a non-empty string")

    assets = root["reference_assets"]
    if not isinstance(assets, list):
        raise FixtureError("reference_assets must be a list")
    seen_asset_ids: set[str] = set()
    for index, raw_asset in enumerate(assets):
        context = f"reference_assets[{index}]"
        asset = _require_exact_fields(raw_asset, ASSET_FIELDS, context=context)
        for field in ASSET_FIELDS - {"role", "content_sha256"}:
            if not _nonempty_text(asset[field]):
                raise FixtureError(f"{context}.{field} must be a non-empty string")
        if asset["role"] not in REFERENCE_ROLES:
            raise FixtureError(
                f"{context}.role must be one of {sorted(REFERENCE_ROLES)}"
            )
        if not isinstance(asset["content_sha256"], str) or not SHA256_PATTERN.fullmatch(
            asset["content_sha256"]
        ):
            raise FixtureError(
                f"{context}.content_sha256 must be 64 lowercase hexadecimal characters"
            )
        if asset["asset_id"] in seen_asset_ids:
            raise FixtureError(
                f"Duplicate asset_id in reference_assets: {asset['asset_id']}"
            )
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
            raise FixtureError(f"risk.{field} must be a Boolean")
    for field in ("provenance_plan", "disclosure_plan"):
        if not _nonempty_text(risk[field]):
            raise FixtureError(f"risk.{field} must be a non-empty string")

    acceptance = root["acceptance"]
    if not isinstance(acceptance, list) or not acceptance:
        raise FixtureError("acceptance must be a non-empty list")
    for index, raw_item in enumerate(acceptance):
        context = f"acceptance[{index}]"
        item = _require_exact_fields(raw_item, ACCEPTANCE_FIELDS, context=context)
        for field in ("dimension", "criterion"):
            if not _nonempty_text(item[field]):
                raise FixtureError(f"{context}.{field} must be a non-empty string")
        if not isinstance(item["hard_failure"], bool):
            raise FixtureError(f"{context}.hard_failure must be a Boolean")

    budget = _require_exact_fields(root["budget"], BUDGET_FIELDS, context="budget")
    for field in ("max_attempts", "max_outputs"):
        if not _positive_int(budget[field]):
            raise FixtureError(f"budget.{field} must be a positive integer")
    for field in (
        "pricing_source_required_at_run",
        "manual_approval_before_budget_increase",
    ):
        if not isinstance(budget[field], bool):
            raise FixtureError(f"budget.{field} must be a Boolean")

    reproducibility = _require_exact_fields(
        root["reproducibility"], REPRODUCIBILITY_FIELDS, context="reproducibility"
    )
    for field in REPRODUCIBILITY_FIELDS - {"save_normalized_request_hash"}:
        if not _nonempty_text(reproducibility[field]):
            raise FixtureError(f"reproducibility.{field} must be a non-empty string")
    if not isinstance(reproducibility["save_normalized_request_hash"], bool):
        raise FixtureError(
            "reproducibility.save_normalized_request_hash must be a Boolean"
        )
    return root


def audit_plan(plan: dict[str, Any]) -> list[str]:
    """Return policy and cross-field findings for a contract-valid plan."""
    validate_contract(plan)
    errors: list[str] = []
    output = plan["output"]
    ratio = _parse_ratio(output["aspect_ratio"])
    if ratio is not None and abs(output["width"] / output["height"] - ratio) > 0.01:
        errors.append("output width and height do not match aspect_ratio.")
    if output["format"].lower() not in ALLOWED_FORMATS:
        errors.append(f"output.format must be one of {sorted(ALLOWED_FORMATS)}.")

    include = {item.casefold() for item in plan["prompt"]["must_include"]}
    avoid = {item.casefold() for item in plan["prompt"]["must_avoid"]}
    conflicts = sorted(include & avoid)
    if conflicts:
        errors.append(f"prompt.must_include conflicts with must_avoid: {conflicts}.")

    roles = {asset["role"] for asset in plan["reference_assets"]}
    for asset in plan["reference_assets"]:
        for field in (
            "source_reference",
            "source_revision",
            "rights_reference",
            "acl_reference",
        ):
            if INCOMPLETE_VALUE_PATTERN.search(asset[field]):
                errors.append(
                    f"Asset {asset['asset_id']} field {field} cannot retain a placeholder value."
                )
    required_roles = {
        "image_to_image": {"source_image"},
        "variation": {"source_image"},
        "outpainting": {"source_image"},
        "inpainting": {"source_image", "mask"},
    }.get(plan["task_type"], set())
    missing_roles = sorted(required_roles - roles)
    if missing_roles:
        errors.append(
            f"{plan['task_type']} is missing required reference asset roles: {missing_roles}."
        )

    risk = plan["risk"]
    if risk["rights_confirmed"] is not True:
        errors.append("risk.rights_confirmed must be explicitly true.")
    if risk["human_review_required"] is not True:
        errors.append("risk.human_review_required must be explicitly true.")

    lineage = plan["lineage"]
    for field in LINEAGE_FIELDS:
        if INCOMPLETE_VALUE_PATTERN.search(lineage[field]):
            errors.append(f"lineage.{field} cannot retain a placeholder value.")

    governance = plan["governance"]
    if governance["object_acl_required"] is not True:
        errors.append(
            "governance.object_acl_required must enable object-level authorization/ACL before evaluation."
        )
    if INCOMPLETE_VALUE_PATTERN.search(governance["deletion_propagation_plan"]):
        errors.append(
            "governance.deletion_propagation_plan cannot retain a placeholder value."
        )
    if governance["evidence_policy"] != "evidence_supported":
        errors.append(
            "governance.evidence_policy must be 'evidence_supported'; a generated image cannot serve as standalone evidence of fact."
        )

    dimensions: set[str] = set()
    for item in plan["acceptance"]:
        dimension = item["dimension"]
        if dimension in dimensions:
            errors.append(f"Duplicate acceptance dimension: {dimension}.")
        dimensions.add(dimension)
    missing_dimensions = sorted(REQUIRED_ACCEPTANCE - dimensions)
    if missing_dimensions:
        errors.append(f"acceptance is missing dimensions: {missing_dimensions}.")

    budget = plan["budget"]
    if output["candidate_count"] > budget["max_outputs"]:
        errors.append("output.candidate_count must not exceed budget.max_outputs.")
    if budget["pricing_source_required_at_run"] is not True:
        errors.append(
            "budget must require pricing-source verification at execution time."
        )
    if budget["manual_approval_before_budget_increase"] is not True:
        errors.append("A budget increase must require manual approval first.")

    reproducibility = plan["reproducibility"]
    if reproducibility["save_normalized_request_hash"] is not True:
        errors.append("A normalized request hash must be retained.")
    for field in ("provider", "model", "adapter_version"):
        if INCOMPLETE_VALUE_PATTERN.search(reproducibility[field]):
            errors.append(
                f"reproducibility.{field} cannot retain a placeholder value."
            )
    try:
        date.fromisoformat(reproducibility["documentation_checked_on"])
    except ValueError:
        errors.append(
            "reproducibility.documentation_checked_on must use YYYY-MM-DD."
        )

    serialized = json.dumps(plan, ensure_ascii=False, allow_nan=False)
    if SECRET_PATTERN.search(serialized):
        errors.append(
            "The task plan appears to contain a real key or Bearer credential."
        )
    return errors


def validate_plan(plan: Any) -> list[str]:
    """Compatibility helper returning contract and audit errors as strings."""
    try:
        validated = validate_contract(plan)
    except FixtureError as exc:
        return [f"Input contract error: {exc}"]
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
        raise FixtureError(f"Unable to read task plan: {exc}") from exc
    try:
        plan = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise FixtureError(
            f"Invalid JSON (line {exc.lineno}, column {exc.colno}): {exc.msg}"
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
        print(f"Input contract error: {exc}", file=sys.stderr)
        return 2

    errors = audit_plan(plan)
    if errors:
        print("Audit failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "Audit passed: "
        f"task_id={plan['task_id']}, "
        f"type={plan['task_type']}, "
        f"candidates={plan['output']['candidate_count']}, "
        f"request_sha256={normalized_hash(plan)[:16]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
