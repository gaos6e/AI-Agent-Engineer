"""Validate an Agent configuration in syntax, schema, and business layers."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from strict_json import JsonDataError, load_json_file


class ContractError(ValueError):
    """A redacted contract error with a stable code and JSON Pointer."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        pointer: str = "",
        keyword: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.pointer = pointer
        self.keyword = keyword


def json_pointer(parts: Iterable[str | int]) -> str:
    """Encode a path as RFC 6901 JSON Pointer; the root pointer is empty."""

    encoded: list[str] = []
    for part in parts:
        token = str(part).replace("~", "~0").replace("/", "~1")
        encoded.append(token)
    return "" if not encoded else "/" + "/".join(encoded)


def load_object(path: Path) -> dict[str, Any]:
    value = load_json_file(path)
    if type(value) is not dict:
        raise ContractError("top_level_type", "top-level value must be an object")
    return value


def build_validator(schema: dict[str, Any]) -> Draft202012Validator:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise ContractError("invalid_schema", "schema is not valid Draft 2020-12") from error
    return Draft202012Validator(schema)


def validate_schema(
    instance: Any,
    validator: Draft202012Validator,
) -> None:
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            str(error.validator),
        ),
    )
    if not errors:
        return
    error = errors[0]
    raise ContractError(
        "schema_validation",
        "instance does not satisfy the declared schema",
        pointer=json_pointer(error.absolute_path),
        keyword=str(error.validator),
    ) from error


def validate_agent_config(
    config: dict[str, Any],
    validator: Draft202012Validator,
) -> None:
    """Apply JSON Schema first, then application-specific invariants."""

    validate_schema(config, validator)

    # JSON Schema treats 1.0 as an integer because it is mathematically whole.
    # This file-format contract deliberately requires lexical integers, which
    # Python's decoder represents as type(value) is int.
    for field in ("schema_version", "max_steps", "timeout_seconds"):
        if type(config[field]) is not int:
            raise ContractError(
                "lexical_integer_required",
                "configuration field must use an integer JSON token",
                pointer=f"/{field}",
            )

    seen_names: set[str] = set()
    for index, tool in enumerate(config["tools"]):
        name = tool["name"]
        if name in seen_names:
            raise ContractError(
                "duplicate_tool_name",
                "tool names must be unique",
                pointer=f"/tools/{index}/name",
            )
        seen_names.add(name)
        if tool["mode"] == "write" and tool["requires_approval"] is not True:
            raise ContractError(
                "unsafe_write_policy",
                "write tools must require approval",
                pointer=f"/tools/{index}/requires_approval",
            )


def load_and_validate_config(
    config_path: Path,
    schema_path: Path,
) -> dict[str, Any]:
    schema = load_object(schema_path)
    validator = build_validator(schema)
    config = load_object(config_path)
    validate_agent_config(config, validator)
    return config


def main() -> int:
    base = Path(__file__).resolve().parent
    try:
        config = load_and_validate_config(
            base / "agent_config.json",
            base / "agent_config.schema.json",
        )
    except (JsonDataError, ContractError) as error:
        print(f"configuration rejected: {error.code}")
        return 1
    print(f"validated config: {config['name']}")
    print("syntax, Draft 2020-12 schema, and business checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
