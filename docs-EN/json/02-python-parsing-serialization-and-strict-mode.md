---
title: "Python Parsing, Serialization, and Strict Mode"
tags:
  - ai-agent-engineer
  - JSON
  - Python
aliases:
  - Python json standard library
  - Strict JSON parsing
source_checked: 2026-07-22
lang: en
translation_key: "JSON/02-Python解析、序列化与严格模式.md"
translation_source_hash: 82241ed820b50e86a6987a04badab5fb6f1d3222fda756629abc4361933c3f13
translation_route: zh-CN/JSON/02-Python解析、序列化与严格模式
translation_default_route: zh-CN/JSON/02-Python解析、序列化与严格模式
---

# Python Parsing, Serialization, and Strict Mode

## Goals

Choose `load/loads/dump/dumps` correctly, read and write UTF-8 files while preserving parse-error locations, understand that Python's standard-library defaults accept extensions such as duplicate keys and non-standard numbers, and explicitly tighten input and output to an interface contract.

## Prepare a minimal environment

The standard-library `json` module needs no installation. The integrated project additionally uses a JSON Schema validator, so create an isolated environment before installing the pinned dependency. Run these commands from the project root that contains both `docs-EN/` and `.website/`:

```powershell
Push-Location -LiteralPath 'docs-EN\json'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\examples\requirements.txt
Pop-Location
```

Do not add `.venv` to the repository. This knowledge base was verified with Python 3.11.9; the code also supports Python 3.10+ supported by `jsonschema` 4.26.0. Re-run the tests when using other versions.

## The four functions differ by “string or file object”

| Direction | String/bytes | An open file object |
| --- | --- | --- |
| JSON → Python | `json.loads(text)` | `json.load(file)` |
| Python → JSON | `json.dumps(value)` | `json.dump(value, file)` |

Remember `s` as “string.” `load` and `dump` accept file-like objects with `read` or `write`; they do not directly accept a `Path`.

```python
import json

text = '{"name": "agent", "max_steps": 5}'
value = json.loads(text)
round_trip = json.dumps(value, ensure_ascii=False)

assert value["name"] == "agent"
assert json.loads(round_trip) == value
```

The `assert` statements here only illustrate equivalence and should not replace project tests; `python -O` removes bare assertions.

## Catch syntax errors while preserving their location

```python
import json

text = '{\n  "name": "agent",\n}'

try:
    config = json.loads(text)
except json.JSONDecodeError as error:
    print(f"invalid JSON at line {error.lineno}, column {error.colno}")
else:
    print(config)
```

Production logs should not casually print the whole `text`: a payload can contain tokens, personal information, or prompt-injection text. Record stable error codes, safe paths, line/column positions, request IDs, and data sources instead of whole values.

## Read and write UTF-8 files

```python
import json
from pathlib import Path

path = Path("agent_config.json")
data = {"name": "meeting assistant", "enabled": True}

with path.open("w", encoding="utf-8", newline="\n") as file:
    json.dump(
        data,
        file,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    )
    file.write("\n")

with path.open("r", encoding="utf-8") as file:
    loaded = json.load(file)
```

- `encoding="utf-8"` does not depend on the current Windows code page.
- `ensure_ascii=False` keeps non-ASCII text readable without changing the logical string.
- `allow_nan=False` prevents encoding the RFC 8259-forbidden `NaN`/`Infinity` values.
- `indent=2` is for people; compact output can be appropriate for network payloads.
- `sort_keys=True` can stabilize ordinary test output, but is not cryptographic canonicalization.
- A final LF helps diffs and is not part of the JSON value.

## Python defaults are broader than RFC 8259

As documented for Python 3.14.6, the standard library has these compatibility behaviors by default:

```python
import json
import math

duplicate = json.loads('{"role":"reader","role":"admin"}')
non_standard = json.loads("NaN")

assert duplicate == {"role": "admin"}
assert math.isnan(non_standard)
```

This does not make duplicate keys or `NaN` standard JSON. If the parsing layer silently drops the first key, a Schema can no longer discover the conflict; duplicate authorization fields are particularly dangerous.

### Use hooks to reject duplicate keys and non-standard constants

```python
import json
from typing import Any


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate object member")
        result[key] = value
    return result


def reject_constant(_: str) -> None:
    raise ValueError("non-standard numeric literal")


value = json.loads(
    '{"enabled": true}',
    object_pairs_hook=unique_object,
    parse_constant=reject_constant,
)
```

This is still not a complete security boundary: the default `float` can turn `1e9999` into positive infinity; lone UTF-16 surrogates, excessively deep nesting, huge arrays, and large files also need extra checks. The project’s `strict_json.py` centralizes these rules behind a testable entry point.

## Numeric precision and `Decimal`

```python
import json
from decimal import Decimal

data = json.loads('{"price": 0.1}', parse_float=Decimal)
assert data["price"] == Decimal("0.1")
```

`Decimal` changes only the local parsing result. It is not a JSON-native type; an output contract still needs to specify a string, an integer number of smallest currency units, or another explicit structure. Very large integer IDs crossing JavaScript systems should usually be strings as well.

## Encode non-native Python types explicitly

`datetime`, `Decimal`, UUID, `Path`, `set`, and custom classes are not JSON-native values. Do not write a fallback encoder that applies `str(obj)` to every unknown object, because type errors will silently become strings. Define the field contract first, then use a narrow conversion:

```python
from datetime import datetime, timezone
import json

payload = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "tags": sorted({"json", "agent"}),
}
text = json.dumps(payload, ensure_ascii=False, allow_nan=False)
```

Time strings also need an agreed time zone, precision, and parsing rule; “serializable” does not mean both sides understand the same thing.

## Double encoding

```python
import json

payload = {"name": "agent"}
once = json.dumps(payload)
twice = json.dumps(once)

print(once)   # {"name": "agent"}
print(twice)  # "{\"name\": \"agent\"}"
```

The second result is a JSON string value, not an object. If an HTTP client provides `json=payload`, normally pass it a Python object; when using `data=`, you must handle encoding and media type yourself, subject to the client documentation.

## Quick command-line check

Python 3.11 can use:

```powershell
Push-Location -LiteralPath 'docs-EN\json'
python -m json.tool .\examples\agent_config.json
Pop-Location
```

Python 3.14 adds the `python -m json` entry point, but the course continues to use `json.tool` for compatibility with this project environment. It checks syntax and formats output; it does not replace Schema or business validation.

## Common errors and troubleshooting

- Parsing JSON with `eval`: untrusted text crosses into code execution; use a data parser only.
- Setting `allow_nan=False` only at output: input also needs `parse_constant` and a post-parse finite-number check.
- Using `skipkeys=True` to hide non-string keys: it loses data; the contract should explicitly reject them.
- Calling `json.dump` repeatedly on the same file: JSON has no record framing, so the result is not a valid single document.
- Catching `Exception` and printing only “parsing failed”: preserve safe error type, position, and handling action.

## Exercises

1. Parse text with `loads`, read a file containing the same text with `load`, and assert that their results match.
2. Input a trailing comma, empty text, and an unterminated string separately, then record `lineno` and `colno`.
3. Encode `float("nan")` with `allow_nan=False` and explain which layer raises the exception.
4. Implement the duplicate-key hook above and write one failing test each for a top-level and nested object.
5. Explain why `json.loads(json.dumps({1: "x"}))` does not equal the original dictionary.

## Self-test

1. What is the input difference between `load` and `loads`?
2. Does `ensure_ascii=False` change a string’s logical content?
3. Is `sort_keys=True` enough to support a digital signature?
4. Why cannot a Schema repair duplicate keys already lost during parsing?
5. Can `parse_constant` alone reject the infinity produced by `1e9999`?

## Summary and next step

The standard library provides mechanisms; the application chooses a profile. The next lesson extends strict boundaries to Unicode, numeric ranges, object order, and resource exhaustion: [[json/03-interoperability-unicode-and-number-boundaries|Interoperability, Unicode, and Number Boundaries]]. Return to the [[json/00-index|JSON Learning Index]].

## References

Source review date: **2026-07-22**.

- [Python 3.14 `json`: Encoder and Decoder; Standard Compliance](https://docs.python.org/3.14/library/json.html)
- [Python `decimal`](https://docs.python.org/3/library/decimal.html)
- [RFC 8259: Parsers, Generators, and Security Considerations](https://www.rfc-editor.org/rfc/rfc8259.html)
