---
title: "JSON Learning Index"
tags:
  - ai-agent-engineer
  - engineering-foundations
  - json
aliases:
  - JSON
  - Introduction to JSON
  - JSON learning path
source_checked: 2026-07-22
ai_learning_stage: 1. Engineering foundations
ai_learning_order: 4
ai_learning_schema: 2
ai_learning_id: json
ai_learning_domain: foundations
ai_learning_catalog_order: 400
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 20
ai_learning_track_agent_app_kind: recommended
ai_learning_track_rag_order: 20
ai_learning_track_rag_kind: core
ai_learning_track_agent_platform_order: 20
ai_learning_track_agent_platform_kind: recommended
ai_learning_track_multimodal_realtime_order: 20
ai_learning_track_multimodal_realtime_kind: recommended
lang: en
translation_key: "JSON/00-目录.md"
translation_source_hash: d387399c39d3e7f0ccedf50c628d89e8a6ca658da9c2057382e6623ccc31716d
translation_route: zh-CN/JSON/00-目录
translation_default_route: zh-CN/JSON/00-目录
---

# JSON Learning Index

## About this knowledge base

JSON (JavaScript Object Notation) is a text data-interchange format. API requests and responses, configuration files, LLM structured output, Tool Calling arguments, MCP messages, and Agent state commonly use it. Recognizing curly braces is only the beginning. Engineering systems must also handle UTF-8, duplicate keys, numeric ranges, parser resource limits, Schema dialects, version migrations, redacted errors, and the boundary between “structurally correct” and “authorized to act.”

This knowledge base uses three progressively stricter views:

1. **JSON syntax** answers “can this text represent a value?”
2. **Data contract** answers “does this value meet the agreement between caller and callee?”
3. **Business and authorization** answers “is this value real, usable, and allowed to trigger an action?”

The capstone handles only local teaching data. It does not access a network, use keys, or execute tools. It strictly parses with Python first, validates with Draft 2020-12 Schema next, then lets trusted code determine whether a tool proposal is “validation only” or “approval required.”

## Place in the overall path

This knowledge base belongs to the Engineering Foundations domain of the AI Agent Engineer path and enters all four role tracks. It first establishes the data representation and contracts for request bodies, response bodies, and configuration; then it can move to [[api/00-index|API]], Markdown, and gradually into LLMs, Tool Calling, and MCP.

## Learning objectives

- Write and judge the six JSON value types, distinguishing JSON text, Python objects, and “a string containing JSON.”
- Use `load/loads/dump/dumps` and correctly handle UTF-8, Chinese text, error line/column numbers, and serialization policy.
- Explain the interoperability boundary between Python's default `json` behavior and RFC 8259 strictness, rejecting duplicate keys, non-finite numbers, lone surrogates, and oversized input.
- Distinguish one JSON document, JSON Lines, NDJSON, and RFC 7464 JSON Text Sequences.
- Use Draft 2020-12 core keywords and understand the real semantics of `$schema`, `$defs/$ref`, composition, conditions, `default`, and `format`.
- Design versioned contracts, stable error paths, and redacted reporting for Agent configuration and tool arguments.
- Explain why structured output still cannot prove facts, permission, approval, or successful tool execution.
- Run independent tests in ordinary and `python -O` modes, verifying failure paths instead of relying on bare `assert`.

## Prerequisites

- Python strings, dictionaries, lists, exceptions, files, and virtual environments are recommended first.
- Basic data structures help explain objects, arrays, and traversal cost.
- You need only run `python` in Windows 11 and PowerShell 7; JavaScript, web services, and real APIs are not required.

## Recommended order

1. [[json/01-json-syntax-and-data-model|Syntax and data model]]: move from JSON text to six value types, null semantics, and validity checks.
2. [[json/02-python-parsing-serialization-and-strict-mode|Python parsing, serialization, and strict mode]]: master the standard library and learn why defaults are not a strict RFC profile.
3. [[json/03-interoperability-unicode-and-number-boundaries|Interoperability, Unicode, and number boundaries]]: handle duplicate keys, object order, Unicode, numeric precision, and canonicalization.
4. [[json/04-files-json-lines-and-stream-processing|Files, JSON Lines, and stream processing]]: read and write files safely, process records line by line, and understand the limits of atomic replacement.
5. [[json/05-json-schema-core-contracts|JSON Schema core contracts]]: express objects, arrays, required fields, ranges, and unknown-field policy with Draft 2020-12.
6. [[json/06-schema-design-versioning-and-error-localization|Schema design, versioning, and error location]]: learn reuse, composition, conditions, version migration, and RFC 6901 error paths.
7. [[json/07-json-in-api-llm-and-tool-calling|JSON in APIs, LLMs, and Tool Calling]]: layer format, Schema, facts, authorization, and execution results.
8. [[json/08-project-reliable-agent-configuration-and-event-pipeline|Project: reliable Agent configuration and event pipeline]]: run the real Schema, strict JSONL pipeline, approval routing, and redacted reports.
9. [[json/09-exercises-self-check-and-mastery-criteria|Exercises, self-test, and mastery criteria]]: complete fault fixes, Schema design, and project extensions, then accept the work with a checklist.

## Hands-on entry point

The project lives in `examples/`:

| File | Purpose |
| --- | --- |
| `strict_json.py` | strict UTF-8 parsing, unique keys, finite numbers, resource limits, JSONL, and atomic replacement |
| `agent_config.schema.json` | Draft 2020-12 Agent-configuration contract |
| `validate_agent_config.py` | executes syntax, Schema, and business-invariant checks in sequence |
| `tool_call.schema.json` | a union Schema for two local tool proposals |
| `tool_calls.jsonl` | fictional records for read-only search and approval-required write operations |
| `validate_tool_calls.py` | produces redacted status and never dynamically dispatches or executes a tool |
| `demo.py` | completes a read, validate, atomic-write, and read-back loop in a temporary directory |
| `test_*.py` | `unittest` tests valid in ordinary and `-O` modes |

Read [[json/08-project-reliable-agent-configuration-and-event-pipeline|the project overview]] first. Do not copy complex helpers before deriving contracts in the first seven lessons.

## Mastery criteria

- [ ] I can identify common JSON syntax errors without running code and explain why a top-level scalar is valid.
- [ ] I can distinguish an absent field, a field set to `null`, an empty string, and an empty array in business terms.
- [ ] I can write UTF-8 read/write code and explain `ensure_ascii=False`, `allow_nan=False`, and double encoding.
- [ ] I can show which non-standard extensions Python's default parser accepts and tighten it to the contract.
- [ ] I can design failure tests for duplicate keys, oversized input, deep nesting, and damaged JSONL lines.
- [ ] I can read and modify a Draft 2020-12 Schema, knowing that validator dialects and supported subsets must be checked.
- [ ] I can use JSON Pointer to locate errors without writing whole payloads or sensitive values to logs.
- [ ] I can explain why a passing Schema still needs business validation, trusted tool registration, authorization, approval, idempotency, and result confirmation.
- [ ] I can run the project and all tests, then independently add a field, a failure case, and a migration rule.

## Relationship to other knowledge bases

| Knowledge base | Boundary and connection |
| --- | --- |
| Python fundamentals | Provides strings, containers, exceptions, files, and tests; this course focuses only on JSON contracts. |
| [[api/00-index\|API]] | Explains HTTP methods, media types, timeouts, and retries; this course explains payload structure and validation. |
| LLM API integration | Vendor endpoints, SDK fields, and response lifecycles change and belong there for verification. |
| [[tool-calling-function-calling/00-index\|Tool Calling (including Function Calling)]] | Schema constrains argument shape; tool selection, execution loops, and side-effect control are elaborated there. |
| MCP | MCP uses JSON-RPC and JSON Schema; protocol versions and lifecycle belong in MCP materials. |
| [[agent-core/00-index\|Agent Core]] | Agent state can serialize to JSON, but memory, planning, and control loops are not data formats. |
| Workflow automation | JSON can carry step inputs and outputs; concurrency, transactions, compensation, and recovery need workflow-layer design. |

## Acceptance record for this revision

Acceptance date: **2026-07-22**.

- Structure: ten Markdown pages (one index plus nine lessons), eleven files in `examples/`, and 21 files total; no public full-text reproduction material.
- Navigation: 44 internal wikilinks use fully qualified paths; zero short paths, broken links, or legacy-course paths remain.
- Documentation code: 16 Python fenced blocks pass AST parsing and 28 JSON fenced blocks parse successfully.
- Project files: six Python files pass AST; three one-document JSON/Schema files pass `python -m json.tool`; the JSONL fixture parses line by line.
- Runs: all 42 `unittest` cases pass in ordinary and `python -O` modes, with `ResourceWarning` treated as an error.
- Closed loop: `demo.py` produces one `validated_not_executed` and one `approval_required` record, executes no tool, and automatically cleans its temporary report.
- Boundaries: tests cover exact-limit/limit+1 reads and writes, LF/CRLF/EOF, duplicate keys, non-finite numbers, Unicode, resource limits, atomic-replacement failure, and report redaction.
- Hygiene: no `.venv`, cache, model file, large file, real credential, or persistent generated report; `git diff --check` passes.
- Review: independent read-only reviews of content structure, dynamic facts/sources, and code/safety all passed.

Obsidian Reading View was not opened manually in this automated environment. Frontmatter, Markdown structure, wikilink targets, and code fences were statically validated.

## Primary references

Source review date: **2026-07-22**.

- [RFC 8259: The JavaScript Object Notation Data Interchange Format](https://www.rfc-editor.org/rfc/rfc8259.html)
- [ECMA-404: The JSON Data Interchange Syntax](https://ecma-international.org/publications-and-standards/standards/ecma-404/)
- [Python 3.14 `json` documentation](https://docs.python.org/3.14/library/json.html)
- [JSON Schema Specification](https://json-schema.org/specification)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [Official `jsonschema` 4.26.0 documentation](https://python-jsonschema.readthedocs.io/en/stable/)
- [RFC 7464: JSON Text Sequences](https://www.rfc-editor.org/rfc/rfc7464.html)
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html)

As of the review date, the JSON Schema site still identifies Draft 2020-12 as the current formally released dialect. This local project uses Python 3.11.9 and `jsonschema` 4.26.0. When vendor structured output supports only a profile or subset of the complete specification, use that vendor's official documentation for the day; do not write an implementation limit as a general JSON Schema rule.
