---
title: "JSON Syntax and Data Model"
tags:
  - ai-agent-engineer
  - JSON
  - data-format
aliases:
  - Introduction to JSON syntax
  - The six JSON value types
source_checked: 2026-07-14
lang: en
translation_key: "JSON/01-语法与数据模型.md"
translation_source_hash: 90921d5f2301b6f3446e37bbe06df7b8531be386cc8a9638bf587397381697e1
translation_route: zh-CN/JSON/01-语法与数据模型
translation_default_route: zh-CN/JSON/01-语法与数据模型
---

# JSON Syntax and Data Model

## Goals

After this lesson, you can distinguish “text that looks like JSON” from valid JSON; identify the six value types, object members, and array elements; and explain why a top-level scalar, permitted whitespace, escaping, and the difference between an absent value, `null`, and an empty value all matter.

## First, distinguish three layers

Beginners often mix up these three things:

```python
python_value = {"enabled": True, "fallback": None}
json_text = '{"enabled": true, "fallback": null}'
json_string_value = '"{\\"enabled\\": true}"'
```

- `python_value` is a Python `dict` in memory.
- `json_text` is a Python string whose contents happen to be one JSON text.
- After parsing, `json_string_value` is still a string whose contents merely look like an object. This is usually an accidental second serialization.

An interface transmits bytes. A parser decodes the bytes into text, then converts the text into language-level objects. Schema validation and business logic operate on the parsed value, not on the braces themselves.

## One JSON text represents one value

The core form in RFC 8259 can be read as: permitted whitespace + one value + permitted whitespace. A top-level value need not be an object or array; all of these are valid standalone JSON texts:

```json
{"name":"agent"}
```

```json
["search", "read"]
```

```json
42
```

```json
null
```

Some APIs additionally require the top-level value to be an object. That is an interface contract, not a general JSON syntax rule. Parse the data first, then explicitly check the top-level type.

## The six value types and their Python mappings

```json
{
  "name": "meeting-assistant",
  "enabled": true,
  "max_steps": 8,
  "temperature": 0.2,
  "tools": ["search_notes", "read_calendar"],
  "fallback": null,
  "limits": {
    "timeout_seconds": 30
  }
}
```

| JSON type | Example | Default Python result | Key boundary |
| --- | --- | --- | --- |
| object | `{"a": 1}` | `dict` | Member names must be strings; object meaning does not depend on order. |
| array | `[1, "x", null]` | `list` | Elements are ordered and may be heterogeneous. |
| string | `"agent"` | `str` | Uses double quotes; control characters must be escaped. |
| number | `8`, `0.2`, `1e3` | `int`, `float` | JSON does not declare bit width, Decimal, or date types. |
| boolean | `true`, `false` | `True`, `False` | JSON literals are lowercase. |
| null | `null` | `None` | Represents an explicit empty value; the contract defines its business meaning. |

An object member is written as `"name": value`, with commas between members; array elements are also separated by commas. A trailing comma is not allowed after the last item.

## Permitted whitespace is very limited

JSON grammar recognizes only four characters as whitespace outside structures: space, tab, LF, and CR. A full-width space, arbitrary invisible Unicode whitespace, or a special character copied from elsewhere may not be valid. When debugging, inspect the parser's line and column and the source bytes; do not hide a data problem by deleting every invisible character.

## The most common invalid forms

None of these lines is standard JSON:

```text
{'name': 'agent'}           # single quotes
{name: "agent"}             # key is not double-quoted
{"enabled": True}           # Python Boolean
{"fallback": None}          # Python null
{"items": [1, 2,]}          # trailing comma
{"value": undefined}       # JSON has no undefined
{"id": 001}                # meaningless leading zero in an integer
{"score": NaN}             # RFC 8259 disallows non-finite numbers
{"hex": 0x10}              # hexadecimal numbers are unsupported
{"a": 1} {"b": 2}         # two values without framing
```

The `#` text after each example is teaching commentary, not part of the value being judged. Standard JSON does not support comments. Extended formats such as JSON5 may allow some of these forms, but never silently send extension syntax to a strict JSON API.

## Strings, escaping, and Windows paths

Double quotes, backslashes, and U+0000–U+001F control characters inside strings must be escaped:

```json
{
  "quote": "They said: \\"stop the task.\\"",
  "path": "D:\\\\data\\\\input.json",
  "two_lines": "first\nsecond",
  "tab": "left\tright",
  "text": "Unicode text can be written directly as UTF-8"
}
```

Do not confuse JSON escaping with Python source-string escaping. When you handwrite the same text in Python source, a backslash may first be interpreted by the Python string parser. A safer approach is to construct a Python object and let `json.dumps` encode it.

## Absent fields, `null`, empty strings, and empty containers

```json
{}
```

```json
{"deadline": null}
```

```json
{"deadline": ""}
```

```json
{"reviewers": []}
```

They can respectively mean:

- an absent field: it was not supplied, an old value remains, or a default applies;
- `null`: explicitly clear the value, or its value is unknown;
- an empty string: a string was supplied, but it contains no characters;
- an empty array: a collection was supplied, and it currently contains no elements.

A parser preserves only the data shape; it cannot know whether “clear” or “retain” is the business intent. The contract must say so for every field.

## Same text, same value, and same business meaning

These texts have different bytes, but their parsed objects can represent the same name/value mapping:

```json
{"a":1,"b":2}
```

```json
{
  "b": 2,
  "a": 1
}
```

Object-member order should not be business semantics across systems; array order does have semantics. The string `"1"` and the number `1` are not equal, and `null` is not the same as an absent field. For signatures, hashes, or cache keys, do not assume arbitrary serialized text is stable; canonicalization comes later.

## Common errors and troubleshooting

- Copying a Python `repr` as JSON: generate it with `json.dumps`, then validate it with a parser.
- Hand-concatenating JSON: quotes, backslashes, and control characters easily break boundaries; construct an object and serialize it.
- Editing a Schema when you see `JSONDecodeError`: syntax parsing occurs before Schema validation, so fix the text first.
- Assuming all JSON is an object: a top-level scalar is valid, though an application may explicitly reject it.
- Writing comments into a production payload: use a separate documentation field or a configuration format that explicitly supports comments.

## Exercises

1. Convert the Python literal `{'ok': True, 'value': None}` into valid JSON.
2. Write valid JSON strings for the path `D:\agent\config.json` and for a sentence containing double quotes.
3. Decide whether `42`, `[true]`, `{"x": 1,}`, and `{"x": +1}` are valid, and explain why.
4. Define the three meanings of absent, `null`, and empty-string `display_name` in a PATCH request.
5. Explain why reordering object fields normally should not change business behavior, while reordering array elements can.

## Self-test

1. Can a JSON object key be an unquoted number?
2. Is top-level `false` a valid JSON text?
3. Does JSON natively support dates, comments, and `undefined`?
4. Why must a Windows path in a JSON string use doubled backslashes?
5. Must different text represent different parsed values?

## Summary and next step

JSON is syntax for “one serialized value,” not a permission system, database, or business model. The next lesson hands text to Python and examines compatibility-oriented defaults in the standard library: [[json/02-python-parsing-serialization-and-strict-mode|Python Parsing, Serialization, and Strict Mode]]. Return to the [[json/00-index|JSON Learning Index]].

## References

Source review date: **2026-07-14**.

- [RFC 8259: JSON Grammar, Objects, Arrays, Numbers, and Strings](https://www.rfc-editor.org/rfc/rfc8259.html)
- [ECMA-404: The JSON Data Interchange Syntax](https://ecma-international.org/publications-and-standards/standards/ecma-404/)
