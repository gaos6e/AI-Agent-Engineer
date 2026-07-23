---
title: "Files, JSON, and Input Validation"
tags: [ ai-agent-engineer, Python, JSON, I-O ]
aliases: [ Python file boundaries, Python JSON validation ]
lang: en
translation_key: "Python基础/Agent工程路线/01-基础与边界/04-文件JSON与输入校验.md"
translation_source_hash: 5f596347eeeb69db1f2f56986a9e54dcb9544a542fced7d21277bb80c97bc419
translation_route: zh-CN/Python基础/Agent工程路线/01-基础与边界/04-文件JSON与输入校验
translation_default_route: zh-CN/Python基础/Agent工程路线/01-基础与边界/04-文件JSON与输入校验
---

# Files, JSON, and Input Validation

## Objective

By the end of this lesson, you should be able to read and write files with `pathlib` and explicit UTF-8, distinguish JSON syntax, data-type, and business-contract errors, and turn an untrusted `object` into a validated object.

## File paths are not ordinary strings

`pathlib.Path` provides cross-platform path composition and file operations:

```python
from pathlib import Path

base = Path("examples")
input_path = base / "tasks.json"
text = input_path.read_text(encoding="utf-8")
```

Do not concatenate paths as strings such as `"examples/" + name`. An externally supplied path can also contain an absolute path or `..`. If an application permits only one working directory, resolve and verify that the target remains under the permitted root, and reject escape through symbolic links or reparse points; checking a string prefix is not enough.

## Text needs an explicit encoding

```python
text = path.read_text(encoding="utf-8")
path.write_text(rendered + "\n", encoding="utf-8")
```

Depending on the operating system default encoding leads to “it works here but server output is garbled.” When terminal text is garbled, first distinguish file encoding, terminal-output encoding, and font issues instead of rewriting the file immediately.

## Separate three error layers

```text
File layer: does not exist, no permission, too large, interrupted read
JSON syntax layer: invalid brackets, commas, quotes, or decoded text
Business-contract layer: wrong root, missing fields, invalid types, forbidden states
```

```python
import json


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InputError(f"file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(
            f"invalid JSON: line={exc.lineno}, column={exc.colno}"
        ) from exc
```

Translate only exceptions you can explain. If you have no appropriate policy for a permissions error or disk failure, let it propagate or map it to a different error; do not disguise every failure as “file not found.”

## JSON types and Python types

| JSON | Python from `json.loads` |
| --- | --- |
| object | `dict` |
| array | `list` |
| string | `str` |
| number | `int` or `float` |
| true/false | `True`/`False` |
| null | `None` |

In Python, Boolean values are subclasses of integers. When a field must be an integer and Booleans are not allowed, explicitly exclude `bool`. JSON numbers also do not automatically guarantee monetary precision, range, or units.

## Allowlist validation

```python
REQUIRED = {"id", "title", "status"}


def parse_task(value: object, index: int) -> Task:
    if not isinstance(value, dict):
        raise TaskValidationError(f"item {index} must be an object")

    keys = set(value)
    missing = REQUIRED - keys
    unknown = keys - REQUIRED
    if missing:
        raise TaskValidationError(f"item {index} is missing fields: {sorted(missing)}")
    if unknown:
        raise TaskValidationError(f"item {index} has unknown fields: {sorted(unknown)}")
    ...
```

Whether unknown fields are rejected, ignored, or retained is a compatibility decision. Strict allowlists often suit tool write operations; a read API intended for long-term compatibility may permit unknown fields. Whatever the choice, put it in the contract and tests.

Do not silently turn the string `"3"` into an integer or an empty string into `None` unless a business rule explicitly allows it and the conversion is traceable. Autocorrection hides upstream data-quality problems.

## Size, depth, and resource limits

Even valid JSON can be large or deeply nested. Check as appropriate before or after reading:

- file-size limits;
- record counts and string lengths;
- allowed nesting depth;
- ranges for each record's fields; and
- total processing time and memory budget.

The standard-library `json.load` does not promise streaming large-data processing. This course handles only small teaching files; choose an appropriate streaming format or parser for large files and design it in the data-engineering course.

## Deterministic output and atomic writes

A teaching report can use stable key order, indentation, and a final newline:

```python
rendered = json.dumps(
    report,
    ensure_ascii=False,
    indent=2,
    sort_keys=True,
    allow_nan=False,
)
path.write_text(rendered + "\n", encoding="utf-8")
```

The standard library normally allows `NaN` and `Infinity`, which are not strict JSON constants. A cross-system contract can use `allow_nan=False` to fail immediately on those values. Repeated `json.dump()` calls to the same file also do not automatically create valid multi-record JSON; use an array, JSON Lines, or another explicit framing format.

If a partial file is unacceptable after a write failure, write a temporary file on the same file system, flush it, then atomically replace the destination. Decide overwrite policy, permissions, backups, and crash recovery too; do not assume all file systems offer identical atomic semantics.

## Common mistakes

- Returning an empty object after `except Exception`.
- Checking only that JSON parses, not its business fields.
- Treating an absent field, `null`, and an empty string as the same thing.
- Putting a complete sensitive input in an error message.
- Reading or writing arbitrary locations directly from a user-provided path.
- Writing a file without specifying overwrite, repeat-run, and interruption behavior.

## Exercise

Add tests for a task list with an empty file, invalid JSON, an object root, an unknown field, duplicate IDs, a forbidden status, an overlong title, and 1,001 records. Define a stable error type and safely displayable information for every error class.

## Self-check

1. Why separate file, JSON-syntax, and business errors?
2. Can type hints replace parsing-time `isinstance` checks?
3. How do a missing field, `null`, and an empty string differ?
4. Why is a string-prefix check insufficient for path safety?
5. Why can valid JSON still consume too many resources?

## Related concepts and next step

- JSON semantics and schemas belong to the JSON course; data batching belongs to [[data-cleaning/00-index|Data Cleaning]].
- Next, [[python-fundamentals/engineering-route/02-reliability-and-testing/05-exceptions-timeouts-retries-and-resource-management|Exceptions, Timeouts, Retries, and Resource Management]] handles control flow after a boundary failure.

## References

Retrieved on **2026-07-14**.

- [Python `pathlib`](https://docs.python.org/3.14/library/pathlib.html)
- [Python `json`](https://docs.python.org/3.14/library/json.html)
- [Python exceptions](https://docs.python.org/3.14/tutorial/errors.html)
