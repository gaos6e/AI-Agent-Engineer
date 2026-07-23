---
title: "Project: Reliable Agent Configuration and Event Pipeline"
tags:
  - ai-agent-engineer
  - JSON
  - integrated-practice
  - agent-engineering
aliases:
  - JSON Integrated Project
  - Agent JSON Pipeline Project
source_checked: 2026-07-22
lang: en
translation_key: JSON/08-实战-可靠Agent配置与事件管道.md
translation_source_hash: c4c02e9d300a03ebd796d25c298b67a77221128ec60341907035402914e96e9a
translation_route: zh-CN/JSON/08-实战-可靠Agent配置与事件管道
translation_default_route: zh-CN/JSON/08-实战-可靠Agent配置与事件管道
---

# Project: Reliable Agent Configuration and Event Pipeline

## Project goal

Complete the following entirely locally, without real credentials or online side effects:

1. Read UTF-8 JSON within bounded limits.
2. Reject BOMs, duplicate keys, `NaN/Infinity`, overflowing floats, lone surrogates, and resource-limit violations.
3. Run a real Draft 2020-12 Schema.
4. Apply business invariants that Schema cannot express.
5. Process JSONL by physical line so one bad line does not contaminate later records.
6. Use trusted tool policy to categorize a proposal as “validate only” or “approval required.”
7. Create redacted reports with no parameter values.
8. Flush, `fsync`, close, and `os.replace` a temporary file in the same directory.
9. Run the same tests in ordinary and `python -O` modes.

The project never calls search, email, calendars, or a model. `send_email` is only a Schema branch name; the pipeline outputs only `approval_required`.

## Environment

Run these commands in order from the project root containing both `docs-EN/` and `.website/`. The last independent check returns to the project root:

```powershell
Push-Location -LiteralPath 'docs-EN\json\examples'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\requirements.txt
```

The dependency file pins `jsonschema==4.26.0`. It was the current official PyPI release and the locally tested version on 2026-07-22. Read the changelog before upgrading, then rerun ordinary and `-O` tests. Do not commit `.venv`.

## Files and responsibility boundaries

| File | Single responsibility |
| --- | --- |
| `strict_json.py` | Strict codec, resource-tree checks, JSONL, and atomic replacement; no Agent business knowledge. |
| `agent_config.json` | Fictional meeting-assistant configuration, with no endpoint or credential. |
| `agent_config.schema.json` | Draft 2020-12 configuration shape, limits, and declaration for write-tool approval. |
| `validate_agent_config.py` | Schema validator, RFC 6901 Pointer, and business invariants. |
| `tool_calls.jsonl` | Two local tool proposals: a read-only query and an approval-required email. |
| `tool_call.schema.json` | `oneOf + const` distinguishes tool parameters. |
| `validate_tool_calls.py` | Per-line validation, request-ID deduplication, trusted-policy classification, and redacted reporting. |
| `demo.py` | Atomic write and readback inside `TemporaryDirectory`; leaves no generated file. |
| `test_strict_json.py` | Codec, Unicode, number, limit, JSONL, and atomic-failure tests. |
| `test_agent_pipeline.py` | Schema, business, approval, continuation, and redaction tests. |

## Step 1: Run the complete demonstration

```powershell
python -B .\demo.py
```

Expected output:

```text
validated config: meeting-assistant
report statuses: {'approval_required': 1, 'validated_not_executed': 1}
no tools executed; temporary report removed
```

The three lines respectively show that configuration passed three validation layers, two records entered different safety states, and no tool executed while the temporary report was removed. They do not prove that the Schema fits your production business or that an external system is available.

## Step 2: Understand the strict-parsing layer

Default limits in `strict_json.py`:

| Limit | Default | Protection goal |
| --- | ---: | --- |
| One JSON text/file | 65,536 bytes | Bound encoded text; a trailing LF also counts toward a written file's total bytes. |
| Maximum depth | 24 | Deep recursion and complex structures. |
| Members per container | 1,000 | Huge arrays/objects. |
| Total value nodes | 10,000 | Amplification through many small nested containers. |
| One string | 16,384 characters | Oversized text and logging risk. |
| Numeric token | 100 characters | Huge integer conversion and exceptional range. |
| One JSONL record body | 16,384 bytes | UTF-8 JSON-text bytes, excluding LF/CRLF. |
| JSONL record count | 1,000 | Unbounded batches. |
| Total JSONL size | 1,048,576 bytes | Batch-input limit. |

The order is “bounded bytes → UTF-8 → strict parsing hooks → iterative structure checks.” `object_pairs_hook` rejects duplicate keys during object construction; `parse_constant` rejects literals such as `NaN`; a custom float parser and structure checks then reject an infinity produced by `1e9999`.

All failures become `JsonDataError(code, line, column)`, and their messages contain no original payload. These limits are teaching choices, not universal recommendations. Production values should follow real payload distribution, load tests, and a rejection policy.

## Step 3: Run Schema and business checks

```powershell
python -B .\validate_agent_config.py
```

The flow:

1. Strictly read the Schema and require an object root.
2. Run `Draft202012Validator.check_schema` on the Schema itself.
3. Strictly read the configuration.
4. Let the Schema check fields, types, ranges, unknown fields, and conditions.
5. Let application code check invariants such as “tokens must be lexical integers” and “tool names must be unique.”

JSON Schema considers a mathematically integral `1.0` to be an integer. This configuration additionally requires a lexical integer, so code checks that the decoded Python type is exactly `int`. That is an application profile: document and test it, but do not present it as universal JSON Schema semantics.

## Step 4: Understand the tool-proposal pipeline

`tool_calls.jsonl` has two branches:

```json
{"schema_version":1,"request_id":"req-0001","tool":"search_notes","arguments":{"query":"strict JSON parsing","limit":5}}
```

```json
{"schema_version":1,"request_id":"req-0002","tool":"send_email","arguments":{"recipient":"team@example.test","subject":"Teaching demonstration","body":"This is a local validation sample and will not be sent."}}
```

`tool_call.schema.json` permits only `search_notes` and `send_email` and sets `additionalProperties: false` separately for their arguments. A trusted code registry then decides that `send_email` requires approval.

A report contains at most:

```json
{
  "line": 2,
  "request_id": "req-0002",
  "status": "approval_required",
  "code": "human_approval_required"
}
```

It never copies `arguments`, query, recipient, body, or the original `ValidationError.message`. Regardless of state, this project has neither `executed` nor `succeeded`.

## Step 5: Run tests

```powershell
python -B -W error::ResourceWarning -m unittest discover `
  -s '.' `
  -p 'test_*.py' `
  -v
```

Then verify that optimization does not remove tests:

```powershell
python -B -O -W error::ResourceWarning -m unittest discover `
  -s '.' `
  -p 'test_*.py' `
  -v
```

At the source check, both modes ran **42 tests** and all passed. `-B` prevents `.pyc` generation; `ResourceWarning` is an error; the tests use `unittest` assertions rather than bare `assert` statements removed by `-O`.

Coverage includes:

- six JSON value kinds and exact Python types;
- Chinese text, Windows paths, escaping, and LF;
- top-level and nested duplicate keys;
- `NaN`, positive/negative Infinity, `1e9999`, and long integers;
- invalid UTF-8, BOM, and lone surrogates;
- document, depth, container, string, total-node, and JSONL limits;
- LF, CRLF, no trailing newline, blank lines, and continuation after a corrupt line;
- successful atomic replacement and preservation of the old file under simulated failure;
- Schema self-check, required fields, unknown fields, types, ranges, conditions, and business invariants;
- read-only proposals, approval-required proposals, duplicate request IDs, and prompt injection treated as ordinary data;
- sensitive sentinels excluded from reports.

## Step 6: Independently check JSON files

```powershell
python -B -m json.tool .\agent_config.json *> $null
python -B -m json.tool .\agent_config.schema.json *> $null
python -B -m json.tool .\tool_call.schema.json *> $null
Pop-Location
```

`tool_calls.jsonl` must not be passed as a whole to `json.tool`; the project parses it line by line. A syntax tool cannot replace Draft validation.

## Security and capability boundaries

- There is no real API key, token, cookie, personal email address, online endpoint, or customer data.
- `.invalid` and `example.test` are reserved example domains, not real services.
- The project uses no `eval`, `exec`, dynamic `getattr`, or model-controlled output path.
- Tool risk comes from the trusted registry, not an input field.
- Atomic writes provide limited single-file replacement semantics, not transactions or concurrency consistency.
- `jsonschema` is a third-party dependency requiring supply-chain management, version pinning, and upgrade tests.
- Passing parsing, Schema, and business checks still does not prove external facts are correct or that an action is authorized.

## Extension tasks

Write a failing test before every implementation:

1. Add a read-only `lookup_document` tool with a bounded string contract for `document_id`.
2. Add config v2, split `timeout_seconds` into connection/read timeouts, and implement pure v1 → v2 migration.
3. Add a bounded aggregate error array to JSONL processing while retaining payload redaction.
4. Add a trusted approval input parameter supplied by the caller, not the model JSON, and prove that an unapproved action never executes.
5. Write reports to a user-selected temporary output directory, simulate `os.replace` failure, and verify the exit code.
6. Compare `sort_keys=True` output with RFC 8785 canonicalization and forbid using the former for signatures.

## Project acceptance

- [ ] I can explain each file's single responsibility.
- [ ] I can trace one valid and one invalid JSONL record by hand.
- [ ] I can distinguish strict parsing, Schema, business registry, and approval.
- [ ] I can explain which risks at least 10 of the 42 test boundaries protect.
- [ ] I can reproduce all tests passing in ordinary and `-O` modes.
- [ ] When extending a field or tool, I update Schema, code, success/failure tests, and documentation together.
- [ ] I can show that the project has no persistent generated artifact, real credential, or tool side effect.

## Summary and next step

The project moves from “format is valid” to “boundaries are demonstrable,” while deliberately stopping before execution. Complete [[json/09-exercises-self-check-and-mastery-criteria|Exercises, Self-Check, and Mastery Criteria]], then return to [[json/00-index|the JSON learning index]] to review the course checklist.

## References

Sources and dependency checked: **2026-07-22**.

- [Python `json`](https://docs.python.org/3.14/library/json.html)
- [Python `os.replace`](https://docs.python.org/3/library/os.html#os.replace)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [`jsonschema` 4.26.0](https://python-jsonschema.readthedocs.io/en/stable/)
- [RFC 6901: JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901.html)
