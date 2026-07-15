"""Strict, bounded JSON helpers for the JSON learning project.

The standard library intentionally accepts a few extensions.  These helpers
choose a narrower, interoperable profile for untrusted teaching inputs:
UTF-8 without BOM, unique object names, finite numbers, and explicit resource
limits.  They are not a streaming parser or an RFC 8785 canonicalizer.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Iterator


@dataclass(frozen=True)
class JsonLimits:
    """Resource limits applied before and after decoding.

    ``max_document_bytes`` counts every file byte, including trailing JSON
    whitespace. ``max_jsonl_line_bytes`` counts one record's JSON text only;
    LF or CRLF delimiters are excluded, while the total-file limit includes
    them.
    """

    max_document_bytes: int = 65_536
    max_depth: int = 24
    max_container_items: int = 1_000
    max_total_values: int = 10_000
    max_string_chars: int = 16_384
    max_number_chars: int = 100
    max_jsonl_line_bytes: int = 16_384
    max_jsonl_records: int = 1_000
    max_jsonl_total_bytes: int = 1_048_576


DEFAULT_LIMITS = JsonLimits()


class JsonDataError(ValueError):
    """Normalized input error that never embeds the original payload."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.line = line
        self.column = column


@dataclass(frozen=True)
class JsonLineResult:
    """One physical JSON Lines record or its bounded parse error."""

    line: int
    value: Any | None = None
    error: JsonDataError | None = None


def _validate_limits(limits: JsonLimits) -> None:
    for name, value in vars(limits).items():
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive integer")


def _reject_constant(_: str) -> None:
    raise JsonDataError("non_finite_number", "non-standard numeric literal is forbidden")


def _parse_int(token: str, *, max_chars: int) -> int:
    digits = token[1:] if token.startswith("-") else token
    if len(digits) > max_chars:
        raise JsonDataError("number_too_long", "integer token exceeds the configured limit")
    return int(token)


def _parse_float(token: str, *, max_chars: int) -> float:
    if len(token) > max_chars:
        raise JsonDataError("number_too_long", "number token exceeds the configured limit")
    value = float(token)
    if not math.isfinite(value):
        raise JsonDataError("non_finite_number", "number is outside the finite float range")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise JsonDataError("duplicate_key", "object contains a duplicate member name")
        result[key] = value
    return result


def _contains_surrogate(text: str) -> bool:
    return any(0xD800 <= ord(character) <= 0xDFFF for character in text)


def _validate_tree(value: Any, limits: JsonLimits) -> None:
    """Validate decoded data iteratively so malformed depth is normalized."""

    max_integer = 10**limits.max_number_chars - 1
    stack: list[tuple[Any, int]] = [(value, 1)]
    total_values = 0

    while stack:
        current, depth = stack.pop()
        total_values += 1
        if total_values > limits.max_total_values:
            raise JsonDataError("resource_limit", "JSON contains too many values")
        if depth > limits.max_depth:
            raise JsonDataError("resource_limit", "JSON nesting exceeds the configured limit")

        if current is None or type(current) is bool:
            continue
        if type(current) is int:
            if abs(current) > max_integer:
                raise JsonDataError("number_too_long", "integer exceeds the configured limit")
            continue
        if type(current) is float:
            if not math.isfinite(current):
                raise JsonDataError("non_finite_number", "non-finite numbers are forbidden")
            continue
        if type(current) is str:
            if len(current) > limits.max_string_chars:
                raise JsonDataError("resource_limit", "string exceeds the configured limit")
            if _contains_surrogate(current):
                raise JsonDataError("invalid_unicode", "string contains an unpaired surrogate")
            continue
        if type(current) is list:
            if len(current) > limits.max_container_items:
                raise JsonDataError("resource_limit", "array exceeds the configured item limit")
            stack.extend((item, depth + 1) for item in current)
            continue
        if type(current) is dict:
            if len(current) > limits.max_container_items:
                raise JsonDataError("resource_limit", "object exceeds the configured member limit")
            for key, item in current.items():
                if type(key) is not str:
                    raise JsonDataError("invalid_type", "object member names must be strings")
                if len(key) > limits.max_string_chars or _contains_surrogate(key):
                    raise JsonDataError("invalid_unicode", "object member name is not interoperable")
                stack.append((item, depth + 1))
            continue
        raise JsonDataError("invalid_type", "value contains a non-JSON Python type")


def loads_strict(text: str, *, limits: JsonLimits = DEFAULT_LIMITS) -> Any:
    """Decode one RFC 8259-oriented JSON text with explicit safety limits."""

    _validate_limits(limits)
    if type(text) is not str:
        raise TypeError("text must be str")
    try:
        encoded = text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise JsonDataError("invalid_unicode", "text is not valid Unicode scalar data") from error
    if len(encoded) > limits.max_document_bytes:
        raise JsonDataError("resource_limit", "JSON document exceeds the byte limit")
    if encoded.startswith(b"\xef\xbb\xbf"):
        raise JsonDataError("bom_forbidden", "UTF-8 BOM is forbidden by this contract")

    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_int=lambda token: _parse_int(token, max_chars=limits.max_number_chars),
            parse_float=lambda token: _parse_float(token, max_chars=limits.max_number_chars),
        )
    except json.JSONDecodeError as error:
        raise JsonDataError(
            "invalid_json",
            "invalid JSON syntax",
            line=error.lineno,
            column=error.colno,
        ) from error
    except RecursionError as error:
        raise JsonDataError("resource_limit", "JSON nesting exceeds the parser limit") from error
    _validate_tree(value, limits)
    return value


def load_json_file(path: Path, *, limits: JsonLimits = DEFAULT_LIMITS) -> Any:
    """Read at most max_document_bytes + 1 bytes and decode UTF-8 strictly."""

    _validate_limits(limits)
    try:
        with path.open("rb") as handle:
            payload = handle.read(limits.max_document_bytes + 1)
    except OSError as error:
        raise JsonDataError("io_error", "unable to read JSON file") from error
    if len(payload) > limits.max_document_bytes:
        raise JsonDataError("resource_limit", "JSON document exceeds the byte limit")
    if payload.startswith(b"\xef\xbb\xbf"):
        raise JsonDataError("bom_forbidden", "UTF-8 BOM is forbidden by this contract")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise JsonDataError("invalid_utf8", "JSON file must be UTF-8") from error
    return loads_strict(text, limits=limits)


def dumps_strict(
    value: Any,
    *,
    limits: JsonLimits = DEFAULT_LIMITS,
    indent: int | None = 2,
    sort_keys: bool = True,
) -> str:
    """Encode JSON without NaN, implicit key coercion, or invalid Unicode."""

    _validate_limits(limits)
    _validate_tree(value, limits)
    try:
        document = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            indent=indent,
            sort_keys=sort_keys,
            separators=(",", ":") if indent is None else None,
        )
    except (TypeError, ValueError, RecursionError) as error:
        raise JsonDataError("encode_error", "value cannot be encoded as strict JSON") from error
    if len(document.encode("utf-8")) > limits.max_document_bytes:
        raise JsonDataError("resource_limit", "encoded JSON document exceeds the byte limit")
    return document


def _atomic_replace_text(path: Path, chunks: Iterable[str]) -> None:
    """Replace one file from a closed same-directory temporary file."""

    parent = path.parent
    if not parent.is_dir():
        raise JsonDataError("io_error", "target directory does not exist")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            for chunk in chunks:
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    except JsonDataError:
        raise
    except OSError as error:
        raise JsonDataError("io_error", "unable to atomically replace target file") from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def write_json_atomic(
    path: Path,
    value: Any,
    *,
    limits: JsonLimits = DEFAULT_LIMITS,
) -> None:
    """Write one pretty JSON document with LF and a final newline."""

    document = dumps_strict(value, limits=limits)
    if len(document.encode("utf-8")) + 1 > limits.max_document_bytes:
        raise JsonDataError(
            "resource_limit",
            "encoded JSON file plus final newline exceeds the byte limit",
        )
    _atomic_replace_text(path, (document, "\n"))


def scan_json_lines(
    path: Path,
    *,
    limits: JsonLimits = DEFAULT_LIMITS,
) -> Iterator[JsonLineResult]:
    """Scan JSON Lines by physical line and keep per-record failures local."""

    _validate_limits(limits)
    try:
        handle = path.open("rb")
    except OSError as error:
        raise JsonDataError("io_error", "unable to read JSON Lines file") from error

    total_bytes = 0
    record_count = 0
    line_number = 0
    with handle:
        while True:
            raw = handle.readline(limits.max_jsonl_line_bytes + 2)
            if not raw:
                break
            line_number += 1
            total_bytes += len(raw)
            if total_bytes > limits.max_jsonl_total_bytes:
                raise JsonDataError("resource_limit", "JSON Lines file exceeds the byte limit")

            partial_overlong_line = (
                len(raw) == limits.max_jsonl_line_bytes + 2
                and not raw.endswith(b"\n")
            )
            if partial_overlong_line:
                while raw and not raw.endswith(b"\n"):
                    raw = handle.readline(limits.max_jsonl_line_bytes + 2)
                    total_bytes += len(raw)
                    if total_bytes > limits.max_jsonl_total_bytes:
                        raise JsonDataError("resource_limit", "JSON Lines file exceeds the byte limit")
                yield JsonLineResult(
                    line_number,
                    error=JsonDataError("line_too_large", "JSON Lines record exceeds the line limit"),
                )
                continue

            if raw.endswith(b"\n"):
                raw = raw[:-1]
                if raw.endswith(b"\r"):
                    raw = raw[:-1]
            if len(raw) > limits.max_jsonl_line_bytes:
                yield JsonLineResult(
                    line_number,
                    error=JsonDataError("line_too_large", "JSON Lines record exceeds the line limit"),
                )
                continue
            if not raw.strip():
                yield JsonLineResult(
                    line_number,
                    error=JsonDataError("blank_line", "blank JSON Lines records are forbidden"),
                )
                continue
            record_count += 1
            if record_count > limits.max_jsonl_records:
                raise JsonDataError("resource_limit", "JSON Lines record count exceeds the limit")
            if line_number == 1 and raw.startswith(b"\xef\xbb\xbf"):
                yield JsonLineResult(
                    line_number,
                    error=JsonDataError("bom_forbidden", "UTF-8 BOM is forbidden by this contract"),
                )
                continue
            try:
                text = raw.decode("utf-8", errors="strict")
                line_limits = JsonLimits(
                    **{
                        **vars(limits),
                        "max_document_bytes": limits.max_jsonl_line_bytes,
                    }
                )
                value = loads_strict(text, limits=line_limits)
            except UnicodeDecodeError:
                yield JsonLineResult(
                    line_number,
                    error=JsonDataError("invalid_utf8", "JSON Lines record must be UTF-8"),
                )
            except JsonDataError as error:
                yield JsonLineResult(line_number, error=error)
            else:
                yield JsonLineResult(line_number, value=value)


def iter_json_lines(
    path: Path,
    *,
    limits: JsonLimits = DEFAULT_LIMITS,
) -> Iterator[tuple[int, Any]]:
    """Fail-fast wrapper for callers that require every record to be valid."""

    for result in scan_json_lines(path, limits=limits):
        if result.error is not None:
            raise JsonDataError(
                result.error.code,
                "invalid JSON Lines record",
                line=result.line,
                column=result.error.column,
            ) from result.error
        yield result.line, result.value


def write_json_lines_atomic(
    path: Path,
    records: Iterable[Any],
    *,
    limits: JsonLimits = DEFAULT_LIMITS,
) -> None:
    """Validate every record and atomically replace a UTF-8 JSON Lines file."""

    _validate_limits(limits)
    line_limits = JsonLimits(
        **{
            **vars(limits),
            "max_document_bytes": limits.max_jsonl_line_bytes,
        }
    )

    def chunks() -> Iterator[str]:
        count = 0
        total_bytes = 0
        for record in records:
            count += 1
            if count > limits.max_jsonl_records:
                raise JsonDataError("resource_limit", "JSON Lines record count exceeds the limit")
            line = dumps_strict(record, limits=line_limits, indent=None)
            line_bytes = len(line.encode("utf-8"))
            if line_bytes > limits.max_jsonl_line_bytes:
                raise JsonDataError("line_too_large", "JSON Lines record exceeds the line limit")
            total_bytes += line_bytes + 1
            if total_bytes > limits.max_jsonl_total_bytes:
                raise JsonDataError("resource_limit", "JSON Lines output exceeds the byte limit")
            yield line
            yield "\n"

    _atomic_replace_text(path, chunks())
