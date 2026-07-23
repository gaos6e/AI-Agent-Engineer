---
title: "Interoperability, Unicode, and Number Boundaries"
tags:
  - ai-agent-engineer
  - JSON
  - interoperability
  - security
aliases:
  - JSON interoperability boundaries
  - Strict JSON profile
source_checked: 2026-07-14
lang: en
translation_key: "JSON/03-互操作性、Unicode与数字边界.md"
translation_source_hash: d43f0febdc3f7f8c5f25277817884657064199f6f1ec56bad60e266ae7a4c8c7
translation_route: zh-CN/JSON/03-互操作性、Unicode与数字边界
translation_default_route: zh-CN/JSON/03-互操作性、Unicode与数字边界
---

# Interoperability, Unicode, and Number Boundaries

## Goals

Understand why “a parser accepts it” does not prove that a value will work reliably across systems; define acceptance policy for duplicate keys, UTF-8, Unicode scalars, numeric ranges, object order, and resource limits; and know the difference between stable formatting and RFC 8785 canonicalization.

## Specification, implementation, and application profile

Engineering decisions have three layers:

1. **RFC 8259 syntax and interoperability guidance** describes JSON text.
2. **Parser implementation behavior** may accept extensions or expose different language types.
3. **An application profile** further restricts top-level types, sizes, numbers, fields, and error policy for a particular interface.

For example, RFC 8259 says object member names `SHOULD` be unique. A duplicate-key text may still be accepted by some parsers, but implementations may keep the first occurrence, the last occurrence, all occurrences, or reject it outright. A security-sensitive interface should promote uniqueness to a hard application constraint.

## Handle duplicate keys during parsing

```text
{"role": "reader", "role": "admin"}
```

If a gateway retains the first occurrence while a backend retains the last, they can make different authorization decisions about the same request. A Schema validates the parsed object; after the first value has been discarded, it cannot restore proof of the conflict. The ordering should therefore be:

```text
byte limit → UTF-8 decode → parse with unique keys and finite numbers → structural resource checks → Schema → business/authorization
```

The project uses `object_pairs_hook` to check duplicate names before constructing a `dict` for every nested object.

## Objects have no business order; arrays do

Python `dict` preserves insertion order, and the `json` module also preserves input and output order by default. That is implementation behavior and must not be mistaken for cross-system business semantics of a JSON object.

- Objects suit independently named fields.
- Arrays suit ordered steps, messages, or sorted results.
- If object-member order matters, use an array instead, for example `[{"name":"a"}, {"name":"b"}]`.
- When testing objects, compare parsed values instead of arbitrary pretty-printed text.

## UTF-8, BOMs, and Unicode scalars

RFC 8259 requires JSON exchanged between open systems to use UTF-8, and network senders must not add a BOM. A parser may choose to ignore a BOM, but an application can reject it to keep one deterministic profile.

Also distinguish:

- a Unicode character (code point) from its UTF-8 byte encoding;
- combining characters from visually identical precomposed characters;
- a valid Unicode scalar from a lone UTF-16 surrogate such as `"\uDEAD"`.

RFC 8259 syntax can permit a lone surrogate to enter text, yet receiver behavior is unpredictable. The project strictly rejects lone values in U+D800–U+DFFF. Do not normalize every string to Unicode on your own: whether usernames, signature material, or external IDs are normalized must be decided by the field contract.

```python
text_a = "é"          # U+00E9
text_b = "e\u0301"   # U+0065 + U+0301

assert text_a != text_b
```

They may render similarly, but they are not the same code-point sequence.

## Numeric syntax does not promise unlimited precision

A JSON `number` has no `int64`, `float32`, or Decimal marker. RFC 8259 notes that integers in `[-(2^53)+1, (2^53)-1]` can be represented exactly across widely used IEEE 754 binary64 implementations; integers outside that range and excessively precise decimals can cause interoperability problems.

| Data | Recommended contract | Reason |
| --- | --- | --- |
| Counts and step totals | bounded integer | Arithmetic is possible and boundaries are explicit. |
| Database or Snowflake IDs | string | Avoid precision loss, leading-zero changes, and accidental arithmetic. |
| Monetary values | smallest-unit integer or normalized decimal string | Make rounding and precision explicit. |
| Time | string with time zone/offset | JSON has no date type. |
| Non-finite computation result | error or explicit status object | `NaN` and `Infinity` are not RFC 8259 numbers. |

`1e400` can be a syntactically valid JSON number, but it may overflow when a receiver uses binary64. The project limits token length and checks `math.isfinite` after parsing; a real business contract should also set `minimum`, `maximum`, or a string format per field.

## Resource limits for untrusted input

“Only data” does not mean no denial-of-service risk. One small entry point can trigger large allocations, deep recursion, or expensive validation. At minimum, consider:

- total byte size before parsing;
- UTF-8 decode errors;
- maximum nesting depth;
- elements per array and members per object;
- total node count;
- characters in one string;
- numeric-token length;
- JSONL line size, record count, and total file size;
- read timeouts and decompression limits at the request layer.

Limits are not “smaller is always better.” Set them from real use cases, load tests, and failure policy. Normalize errors instead of exposing `RecursionError` or a raw exception that contains payload content directly to a caller.

## Stable text is not canonicalization

```python
import json

stable_for_tests = json.dumps(
    {"b": 2, "a": 1},
    ensure_ascii=False,
    allow_nan=False,
    sort_keys=True,
    separators=(",", ":"),
)
```

This is useful for this project’s snapshot tests, but it does not automatically meet RFC 8785 JSON Canonicalization Scheme (JCS). Signatures and hashes also involve:

- numeric serialization rules;
- string escaping;
- Unicode handling;
- property sorting;
- duplicate keys and I-JSON restrictions.

For a digital signature, use a verified JCS implementation and an explicit protocol. Do not compose JSON strings yourself.

## JSON-value equality and business equivalence

- Text with different whitespace or object-field order can still parse to equal values.
- The number `1` and `1.0` can both satisfy `integer` in JSON Schema as mathematical values, while Python decodes them as `int` and `float` respectively.
- Visually identical Unicode does not guarantee identical code points.
- Schema equality is not the same as business-state equality.
- Repeated parsing and serialization can change whitespace, escaping, number text, and field order.

If a business rule requires an integer token, add an application rule after Schema validation like `type(value) is int`, as this project does, and write that requirement into the contract.

## Common errors and troubleshooting

- Checking duplicate keys only with a WAF or Schema: if a parser already overwrote the old value, the evidence is gone.
- Treating Python dictionary order as protocol order: use an array or an explicit `order` field.
- Calling UTF-16/UTF-32 input a “UTF-8 interface”: decode strictly at the byte boundary and test the BOM.
- Rejecting only literal `NaN`: also reject the non-finite result of `1e9999`.
- Copying a whole payload into an error log: use an error code, line/column, JSON Pointer, and request ID.
- Claiming `sort_keys=True` is a signable canonical form: cite and implement an explicit standard.

## Exercises

1. Parse a duplicate `role` with Python’s default `json.loads` and record the result; then replace it with a rejecting hook.
2. Choose JSON representations for an ID, money, time, and probability field, explaining the trade-offs.
3. Design four resource limits and their boundary tests, including exactly at the limit and one over.
4. Compare the text, parsed value, and hash of `{"a":1,"b":2}` and `{"b":2,"a":1}`.
5. Explain why arbitrary Unicode normalization of signature material can break verification.

## Self-test

1. Does RFC 8259 require every parser to reject duplicate keys?
2. Why can a Schema not discover a duplicate value already overwritten by a parser?
3. How do JSON objects and arrays differ in ordering semantics?
4. Why can `1e400` be syntactically valid but not interoperable?
5. Why is `sort_keys=True` not RFC 8785?

## Summary and next step

A strict profile is an explicit contract choice, not a default label from a library. The next lesson applies these boundaries to files, line-oriented records, and atomic replacement: [[json/04-files-json-lines-and-stream-processing|Files, JSON Lines, and Stream Processing]]. Return to the [[json/00-index|JSON Learning Index]].

## References

Source review date: **2026-07-14**.

- [RFC 8259: Objects, Numbers, Character Encoding, and Security](https://www.rfc-editor.org/rfc/rfc8259.html)
- [RFC 7493: The I-JSON Message Format](https://www.rfc-editor.org/rfc/rfc7493.html)
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html)
- [Python `json`: Standard Compliance and Interoperability](https://docs.python.org/3.14/library/json.html#standard-compliance-and-interoperability)
