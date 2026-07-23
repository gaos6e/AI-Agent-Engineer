"""Validate the strict teaching profile used by the bundled Agent Skill.

This standard-library validator deliberately supports only the YAML subset used
by this example. It is not an Agent Skills conformance test and does not replace
the official ``skills-ref validate`` command.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESOURCE_PATTERN = re.compile(
    r"(?:`|\]\()((?:scripts|references|assets)/[^`\s)]+)(?=[`\s)])"
)
ALLOWED_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
    # Repository-level bilingual publication metadata. It is accepted by this
    # teaching validator so the English course copy can retain its required
    # source mapping without weakening validation of unknown Skill fields.
    "lang",
    "translation_key",
    "translation_source_hash",
}
MIN_TRIGGER_CASES_PER_CLASS = 8


def require(condition: bool, message: str) -> None:
    """Raise a stable, user-facing validation error."""
    if not condition:
        raise ValueError(message)


def _parse_scalar(raw: str, *, line_number: int) -> str:
    value = raw.strip()
    require(value != "", f"frontmatter line {line_number} needs a scalar value")
    if value[0] in {"'", '"'}:
        require(
            len(value) >= 2 and value[-1] == value[0],
            f"frontmatter line {line_number} has an unterminated quoted scalar",
        )
        value = value[1:-1]
    require("\n" not in value and "\r" not in value, "scalar values cannot contain newlines")
    return value


def parse_frontmatter_subset(text: str) -> tuple[dict[str, Any], str]:
    """Parse flat scalars plus a one-level string-to-string metadata mapping."""
    lines = text.splitlines()
    require(lines and lines[0] == "---", "SKILL.md must start with ---")
    try:
        closing = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("SKILL.md frontmatter has no closing ---") from exc

    fields: dict[str, Any] = {}
    index = 1
    while index < closing:
        line_number = index + 1
        line = lines[index]
        require(line and not line[0].isspace(), f"unexpected indentation on line {line_number}")
        require(":" in line, f"frontmatter line {line_number} must contain ':'")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        require(key in ALLOWED_FIELDS, f"unsupported top-level field in teaching profile: {key}")
        require(key not in fields, f"duplicate frontmatter field: {key}")

        if key != "metadata":
            fields[key] = _parse_scalar(raw_value, line_number=line_number)
            index += 1
            continue

        require(raw_value.strip() == "", "metadata must be a one-level mapping in this teaching profile")
        metadata: dict[str, str] = {}
        index += 1
        while index < closing and lines[index].startswith("  "):
            nested_number = index + 1
            nested = lines[index][2:]
            require(nested and not nested[0].isspace(), f"metadata line {nested_number} is too deeply nested")
            require(":" in nested, f"metadata line {nested_number} must contain ':'")
            nested_key, nested_raw = nested.split(":", 1)
            nested_key = nested_key.strip()
            require(nested_key != "", f"metadata line {nested_number} needs a key")
            require(nested_key not in metadata, f"duplicate metadata key: {nested_key}")
            metadata[nested_key] = _parse_scalar(nested_raw, line_number=nested_number)
            index += 1
        require(metadata, "metadata mapping must not be empty")
        fields[key] = metadata

    return fields, "\n".join(lines[closing + 1 :]).strip()


def require_canonical_resource_relative(relative: str) -> None:
    """Reject ambiguous resource spellings before resolving them on the host OS."""
    path = PurePosixPath(relative)
    parts = path.parts
    require(
        not path.is_absolute()
        and "\\" not in relative
        and str(path) == relative
        and len(parts) >= 2
        and parts[0] in {"scripts", "references", "assets"}
        and all(part not in {".", ".."} for part in parts),
        f"resource reference must be a canonical relative POSIX path: {relative}",
    )


def resolve_within(root: Path, relative: str) -> Path:
    """Resolve a canonical resource reference without allowing Skill-root escape."""
    require_canonical_resource_relative(relative)
    target = (root / relative).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"resource escapes skill root: {relative}") from exc
    return target


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_json_keys,
    )
    require(isinstance(data, dict), f"{path.name} root must be an object")
    return data


def validate_evals(skill_root: Path, skill_name: str) -> dict[str, int]:
    """Validate the local trigger-corpus profile, not a universal eval schema."""
    eval_path = skill_root / "evals" / "evals.json"
    if not eval_path.exists():
        return {"total": 0, "positive": 0, "negative": 0}

    data = load_json_object(eval_path)
    require(data.get("skill_name") == skill_name, "eval skill_name must match name")
    cases = data.get("evals")
    require(isinstance(cases, list) and cases, "evals must be a non-empty array")

    ids: set[str] = set()
    positives = 0
    negatives = 0
    for index, case in enumerate(cases, start=1):
        require(isinstance(case, dict), f"eval {index} must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and case_id.strip(), f"eval {index} needs a string id")
        require(case_id not in ids, f"duplicate eval id: {case_id}")
        ids.add(case_id)
        require(
            isinstance(case.get("prompt"), str) and case["prompt"].strip(),
            f"eval {index} needs a non-empty prompt",
        )
        trigger = case.get("should_trigger")
        require(isinstance(trigger, bool), f"eval {index} needs boolean should_trigger")
        require(
            isinstance(case.get("reason"), str) and case["reason"].strip(),
            f"eval {index} needs a non-empty reason",
        )
        require(
            isinstance(case.get("expected_output"), str) and case["expected_output"].strip(),
            f"eval {index} needs a non-empty expected_output",
        )
        positives += int(trigger)
        negatives += int(not trigger)

    require(
        positives >= MIN_TRIGGER_CASES_PER_CLASS,
        f"teaching profile needs at least {MIN_TRIGGER_CASES_PER_CLASS} positive trigger cases",
    )
    require(
        negatives >= MIN_TRIGGER_CASES_PER_CLASS,
        f"teaching profile needs at least {MIN_TRIGGER_CASES_PER_CLASS} negative trigger cases",
    )
    return {"total": len(cases), "positive": positives, "negative": negatives}


def validate_python_scripts(skill_root: Path) -> list[str]:
    """Compile Python source in memory so validation creates no bytecode cache."""
    scripts_root = skill_root / "scripts"
    if not scripts_root.exists():
        return []
    require(scripts_root.is_dir(), "scripts must be a directory")
    checked: list[str] = []
    for path in sorted(scripts_root.rglob("*.py")):
        relative = path.relative_to(skill_root).as_posix()
        try:
            compile(path.read_text(encoding="utf-8"), relative, "exec")
        except (SyntaxError, UnicodeError) as exc:
            raise ValueError(f"invalid Python script {relative}: {exc}") from exc
        checked.append(relative)
    return checked


def validate_skill(skill_root: Path) -> dict[str, Any]:
    require(skill_root.is_dir(), f"skill directory not found: {skill_root}")
    skill_file = skill_root / "SKILL.md"
    require(skill_file.is_file(), "SKILL.md not found")
    skill_text = skill_file.read_text(encoding="utf-8")
    fields, body = parse_frontmatter_subset(skill_text)

    name = fields.get("name", "")
    description = fields.get("description", "")
    require(isinstance(name, str) and 1 <= len(name) <= 64, "name must contain 1-64 characters")
    require(bool(NAME_PATTERN.fullmatch(name)), "name must use lowercase letters, digits, and single hyphens")
    require(name == skill_root.name, "name must match the parent directory")
    require(
        isinstance(description, str) and 1 <= len(description) <= 1024,
        "description must contain 1-1024 characters",
    )
    require(body, "SKILL.md body must not be empty")
    compatibility = fields.get("compatibility")
    if compatibility is not None:
        require(
            isinstance(compatibility, str) and 1 <= len(compatibility) <= 500,
            "compatibility must contain 1-500 characters",
        )
    metadata = fields.get("metadata")
    if metadata is not None:
        require(
            isinstance(metadata, dict)
            and all(isinstance(key, str) and isinstance(value, str) for key, value in metadata.items()),
            "metadata must be a string-to-string mapping",
        )
    allowed_tools = fields.get("allowed-tools")
    if allowed_tools is not None:
        require(isinstance(allowed_tools, str) and bool(allowed_tools.strip()), "allowed-tools must be a string")

    references = sorted(set(RESOURCE_PATTERN.findall(body)))
    for relative in references:
        require(resolve_within(skill_root, relative).is_file(), f"missing resource: {relative}")

    warnings: list[str] = []
    if len(skill_text.splitlines()) >= 500:
        warnings.append("official guidance recommends keeping SKILL.md under 500 lines")
    for relative in references:
        if len(Path(relative).parts) > 2:
            warnings.append(f"deep resource reference may be harder to discover: {relative}")

    eval_summary = validate_evals(skill_root, name)
    scripts = validate_python_scripts(skill_root)
    return {
        "status": "ok",
        "profile": "strict-offline-teaching-profile-v1",
        "name": name,
        "referenced_files": references,
        "python_scripts": scripts,
        "trigger_cases": eval_summary,
        "warnings": sorted(set(warnings)),
        "note": "not an official conformance result; use skills-ref for official validation",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the offline teaching Agent Skill profile.")
    parser.add_argument("skill_directory", type=Path, help="Path containing SKILL.md")
    args = parser.parse_args()
    result = validate_skill(args.skill_directory.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1) from exc

