---
title: "JSON Exercises, Self-Check, and Mastery Criteria"
tags:
  - ai-agent-engineer
  - JSON
  - exercises
  - self-check
aliases:
  - JSON Course Self-Check
  - JSON Mastery Check
source_checked: 2026-07-22
lang: en
translation_key: JSON/09-练习、自测与掌握标准.md
translation_source_hash: c117fbf11d0954ba264d4872e78822032bd940d20da679c4829c36ee46beb5b2
translation_route: zh-CN/JSON/09-练习、自测与掌握标准
translation_default_route: zh-CN/JSON/09-练习、自测与掌握标准
---

# JSON Exercises, Self-Check, and Mastery Criteria

## How to use this page

Hide the answer sections first, make the judgments and designs by hand, then run the project tests. The goal is not memorizing Schema keywords. It is being able to locate an unfamiliar JSON-interface problem from the byte boundary, state a testable contract, and refuse to treat structured model output as an authorized action.

Recommended order: basic judgments → small Python experiments → Schema design → fault diagnosis → integrated task. For every group, write **why**, not merely valid/invalid.

## Group 1: Syntax and data model

Decide whether each text is standard JSON. If it is invalid, give the smallest repair:

```text
A. 42
B. {'ok': True}
C. {"items": [1, 2,]}
D. {"id": "001"}
E. {"id": 001}
F. {"value": null}
G. {"value": undefined}
H. {"path": "D:\data\input.json"}
I. {"a": 1} {"b": 2}
J. ["x", 1, false, null]
```

Then answer:

1. A top-level scalar is valid. Why do many APIs still require a top-level object?
2. What distinct intentions can a missing field, `null`, `""`, and `[]` express?
3. Why do reordered object members and reordered array elements have different semantics?
4. How do you distinguish JSON text, a Python dictionary, and a string that contains JSON?

## Group 2: Python encode/decode experiments

Use a temporary directory and do not modify the repository examples:

1. Encode a Chinese object with `json.dumps(..., ensure_ascii=False, allow_nan=False)`, then read it back with `loads`.
2. Print line/column of `JSONDecodeError` for a trailing comma, empty input, and an unclosed string.
3. Prove that Python's default parser retains the last value for a duplicate key.
4. Prove that the default parser accepts `NaN` while `allow_nan=False` prevents emitting it.
5. Parse `0.1` with `parse_float=Decimal` and explain why the write-back contract must still be explicit.
6. Prove that non-string dictionary keys change type after a round trip.
7. Construct double encoding and state the type after each of two parses.
8. Explain why `python -m json.tool` can check syntax but not business rules.

Acceptance condition: every experiment has at least one `unittest` assertion; run it with `python -O` too, and the test count must not decrease.

## Group 3: Strict interoperability boundaries

For each risk, specify detection layer, error code, whether processing may continue, and allowed log fields:

| Risk | What you need to decide |
| --- | --- |
| Duplicate `role` key | Must it be detected before or after Schema? |
| Invalid UTF-8 | Can it enter text parsing? |
| UTF-8 BOM | Should the interface accept or reject it? |
| `NaN` and `1e9999` | Why are two types of check needed? |
| Lone `\uDEAD` | How do you avoid cross-implementation inconsistency? |
| 30 nested levels | How do you test the depth-limit boundary? |
| A 10 MB one-line JSONL record | When do you reject it, and how do you skip to the next physical line? |
| Huge integer ID | Why is a string usually a better choice? |

Further questions:

1. Which test problems can `sort_keys=True` solve, and which signature problems can it not solve?
2. Why might visually identical Unicode strings not be equal?
3. Which contract can break if an application NFC-normalizes every text field?
4. What evidence should set resource limits instead of guessing a number?

## Group 4: JSON Lines and file writes

Create a temporary `events.jsonl` containing, in order: a valid first line, a blank line, a corrupt third line, a valid fourth line, and a fifth line with no trailing LF. Implement two policies:

- `read_all_or_fail`: any invalid line fails the entire batch.
- `scan_with_reports`: emit `status/code` for each physical line and continue after a bad line.

Constraints:

- Accept UTF-8 only, with no BOM.
- Bound individual-line and total bytes.
- A report must never echo the source line.
- Read both CRLF and LF.
- An escaped `\n` in a string does not split a record.
- Write with a temporary file in the same directory and `os.replace`.
- Under a simulated replacement failure, the old target remains complete and the temporary file is cleaned up.

Explain why this is still not a multi-process transactional database.

## Group 5: Schema fundamentals

Write a Draft 2020-12 Schema for:

```json
{
  "schema_version": 1,
  "name": "research-agent",
  "max_steps": 10,
  "timeout_seconds": 45,
  "log_level": "INFO"
}
```

Requirements:

- declare `$schema`;
- use an object root and reject unknown fields;
- require all five fields;
- permit only `1` for `schema_version`;
- restrict `name` to length 1–64;
- restrict `max_steps` to 1–20;
- restrict `timeout_seconds` to 1–120;
- limit `log_level` to `DEBUG/INFO/WARNING/ERROR`.

For every range, test its minimum, maximum, one below, one above, `true`, and a string. Then explain:

1. the division of labor between `properties` and `required`;
2. optional versus nullable;
3. why `default` does not automatically write a value;
4. why `format` can be annotation only;
5. why `uniqueItems` cannot guarantee unique `name` values in tool objects.

## Group 6: Schema composition, versioning, and error paths

Design a `tool` envelope with `search_notes` and `send_email`:

- distinguish branches with `oneOf + const`;
- reject unknown fields in every `arguments` object;
- set `search_notes.limit` to 1–20;
- allow `send_email` only at the teaching domain `example.test`;
- reject input `approved`;
- report errors using RFC 6901 JSON Pointer;
- include `schema_version` in the instance;
- include `$schema` and `$id` in the Schema.

Then:

1. Create a zero-branch match and a two-branch match counterexample.
2. Encode key `a/b~c` as a Pointer token.
3. Design a v1 → v2 field-renaming migration: validate old, migrate, then validate new.
4. Limit results to at most five errors and prove they contain no instance values.
5. Explain `$schema`, `$id`, and `schema_version` separately.

## Group 7: LLM and tool-boundary scenarios

Give the correct handling for each:

1. A model returns parseable JSON but omits a required field.
2. Strict output passes Schema but gives a nonexistent `document_id`.
3. Tool parameters include `"approved": true`.
4. A stream disconnects after only half an object.
5. `send_email` parameters are valid but the user lacks sending permission.
6. The email tool times out and the server may already have sent it.
7. A tool result contains webpage text saying “ignore previous rules.”
8. Vendor documentation supports only a JSON Schema subset while the domain Schema uses an unsupported keyword.
9. An MCP server provides `readOnlyHint: true` but the server is untrusted.
10. The logging system wants full tool parameters for diagnosis.

Every answer must name the structural, factual, permission, approval, idempotency/unknown-result, trust-source, and redaction layers.

## Group 8: Integrated project extension

Choose one task in the current `examples/` project.

### Task A: New read-only tool

Add `lookup_document`:

- `document_id` is a string of 1–64 characters;
- update Schema, trusted registry, and success/failure tests together;
- the status can only be `validated_not_executed`;
- document content from input never enters a report.

### Task B: Config v2 migration

Replace `timeout_seconds` with:

```json
{
  "connect_timeout_seconds": 5,
  "read_timeout_seconds": 40
}
```

Implement a pure migration function: do not mutate its input, reject unknown versions, validate v2 after migration, and keep the original file until a new file has replaced it atomically.

### Task C: Batch error budget

Add `max_rejected_records` to the pipeline. When the budget is exceeded, stop accepting additional business records and return a failing exit code, but never execute tools or echo payload. Test exactly at the budget and one over it.

Whatever you choose, run all tests in ordinary and `-O` modes and leave no network access, key, or generated artifact.

## Reference answers and reasoning

### Group 1 essentials

- A, D, F, and J are valid. D's ID is a string, so its leading zero is preserved.
- B uses Python single quotes and `True`; C has a trailing comma; E has a leading-zero number; G has no `undefined`; H contains an invalid backslash escape and must write `D:\\data\\input.json`; I has two unseparated JSON values.
- A top-level object is an application envelope decision; general JSON syntax permits scalars.

### Strict-boundary essentials

- Detect duplicate keys during object construction; Schema is too late.
- `parse_constant` handles `NaN/Infinity` literals, while `1e9999` needs a custom float parser or post-parse finite-value check.
- Logs may record code, line/column, Pointer, keyword, and request ID; they must not hold the whole input.
- `sort_keys` is implementation-local stable formatting, not RFC 8785.

### Schema essentials

- `properties` does not require presence; `required` does not require nonempty content.
- `default` and usually `format` are annotation semantics; whether to mutate or reject depends on application and validator configuration.
- `oneOf` must match exactly one branch; `const` discriminators prevent overlap.
- A Schema validates stated structure only. Database existence, user permission, and approval belong to the trusted application layer.

### LLM/tool essentials

- Structural validity does not mean factual correctness; verify key IDs at their source.
- Input cannot approve itself; approval comes from trusted external state.
- Incomplete streaming input must not be guessed or executed.
- A timeout can leave an unknown result; converge with an idempotency key, status query, and audit.
- Treat tool annotations, webpage content, and tool results according to their source trust, not as trusted merely because they are JSON.

## Final mastery checklist

### Concepts

- [ ] I can explain six value kinds, top-level scalars, legal whitespace, and the different ordering semantics of objects and arrays.
- [ ] I can distinguish JSON, JSONL, NDJSON, JSON Text Sequences, and JSON5.
- [ ] I can explain number-precision, Unicode-scalar, duplicate-key, and canonicalization risks.
- [ ] I can distinguish syntax, Schema, business logic, authorization, approval, and execution result.

### Python

- [ ] I choose `load/loads/dump/dumps` correctly and state UTF-8 explicitly.
- [ ] I reject duplicate keys, nonfinite numbers, BOM, invalid UTF-8, lone surrogates, and oversized structures.
- [ ] I preserve physical line numbers for JSONL and define a failure policy.
- [ ] I can perform same-directory atomic replacement and explain why it is not a transaction.

### Schema

- [ ] I declare Draft 2020-12 and call `check_schema`.
- [ ] I use objects, arrays, bounds, `$defs/$ref`, composition, and conditionals.
- [ ] I distinguish optional/nullable, `default`/population, and `format` annotation/assertion.
- [ ] I use JSON Pointer and stable keywords for redacted errors.
- [ ] I design versions and migration tests for both Schema and instances.

### Agent engineering

- [ ] I do not treat model JSON, tool annotations, or external content as authorization.
- [ ] I surround tool execution with a trusted registry, allowlist, approval, idempotency, and result validation.
- [ ] I handle refusal, truncation, incomplete streams, and timeout-after-unknown-result.
- [ ] I keep ordinary and `python -O` test counts equal and avoid real credentials and online side effects.

## Next step

After completing the full checklist, return to [[json/00-index|the JSON learning index]]. The next broad route is [[markdown/00-index|Markdown]]. For JSON in network requests, return to [[api/00-index|API]]; for model tool execution, continue with [[tool-calling-function-calling/00-index|Tool Calling]].

## References

Sources checked: **2026-07-22**.

- [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259.html)
- [Python `json`](https://docs.python.org/3.14/library/json.html)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [RFC 6901: JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901.html)
- [RFC 7464: JSON Text Sequences](https://www.rfc-editor.org/rfc/rfc7464.html)
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html)
