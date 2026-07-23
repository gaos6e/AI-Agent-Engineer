---
title: "Tool Calling (including Function Calling)"
tags:
  - ai-agent-engineer
  - tool-calling
  - function-calling
aliases:
  - Tool Calling course index
  - Function Calling course index
  - Tool use
source_checked: 2026-07-21
source_baseline: "Official OpenAI, Anthropic, and Google tool-calling
  documentation; JSON Schema 2020-12; RFC 9110; OWASP GenAI; SQLite
  Transaction/WAL/UPSERT/STRICT; and Stripe/AWS idempotency material, checked
  through 2026-07-21"
content_origin: original
content_status: dynamic
ai_learning_stage: 5. Single agents and tools
ai_learning_order: 30
ai_learning_schema: 2
ai_learning_id: tool-calling
ai_learning_domain: agent-runtime
ai_learning_catalog_order: 3000
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 500
ai_learning_track_agent_app_kind: core
ai_learning_track_agent_platform_order: 500
ai_learning_track_agent_platform_kind: core
ai_learning_track_multimodal_realtime_order: 500
ai_learning_track_multimodal_realtime_kind: core
lang: en
translation_key: "Tool Calling（含 Function Calling）/00-目录.md"
translation_source_hash: fda1095027f0dc97b41005d2e74377066c17a29fd00767a9880b6aafac2600ac
translation_route: zh-CN/Tool-Calling（含-Function-Calling）/00-目录
translation_default_route: zh-CN/Tool-Calling（含-Function-Calling）/00-目录
---

# Tool Calling (including Function Calling)

## Course overview

Tool Calling lets a model express, in a structured form, which capability it wants to use and with which arguments. Function Calling usually means a function tool that the application declares with JSON Schema. It connects natural-language understanding to databases, APIs, files, search, and business actions: the interface that moves an agent from “can talk” to “can look things up and do work.”

> [!important] A call proposal is not execution
> For client-side function tools, the model produces only a candidate call. Your trusted application must parse it, enforce an allowlist and schema, validate business rules, authenticate and authorize, obtain approval when required, apply idempotency and timeouts, execute, audit, and return a result. Schema conformance grants no permission, and a prompt cannot replace any of those controls.

## Stable concepts and provider adaptation

As checked on 2026-07-21, OpenAI uses “tool calling” for function calling and distinguishes JSON-Schema functions, free-form custom tools, and platform-built-in tools. Anthropic distinguishes client-side from server-side tools, and Gemini likewise states that client functions are executed by the application. Message blocks, finish reasons, strict-mode behavior, parallelism, and built-in tools vary, but the stable flow does not:

~~~text
application declares capabilities → model proposes a call → application validates, authorizes, and executes
                                → application correlates and returns the result → model continues or stops
~~~

Learn the provider-neutral execution contract first, then map OpenAI function_call/function_call_output, Anthropic tool_use/tool_result, and equivalent provider objects through an adapter. Provider field shapes must not leak into business handlers.

One current OpenAI nuance deserves explicit treatment: in Chat Completions, function tools are non-strict by default. In Responses, omitting strict causes an attempt to normalize the schema as strict; if that is incompatible, the behavior falls back to best effort and the parsed tool reports strict: false. Production integrations must configure and verify the target behavior explicitly; “Responses tries strict by default” is not an unconditional guarantee.

## Trusted execution boundary

~~~mermaid
flowchart LR
    U["User and external content"] --> M["Model"]
    subgraph Untrusted["Untrusted proposal plane"]
        M --> P["tool proposal<br/>name + arguments"]
    end
    subgraph Trusted["Trusted execution plane (application)"]
        B["adapter binds execution context<br/>call / operation / idempotency"] --> V["registry + schema"]
        V --> A["business validation + AuthN/AuthZ"]
        A --> I["idempotency state / receipt lookup"]
        I --> H{"Does first execution require approval?"}
        H -->|yes| W["durably wait<br/>bind arguments and expiry"]
        H -->|no| X["recheck before execution"]
        W --> X
        X --> D["deadline + scheduling"]
        D --> T["tool handler"]
    end
    P --> B
    T --> S["external system"]
    S --> R["per-tool output validation<br/>content remains untrusted"]
    R --> MR["model_result<br/>returned to model"]
    R --> PA["protected_audit<br/>protected storage"]
    MR --> M
~~~

The model supplies only the tool name and arguments. The adapter extracts a provider call ID from provider events and records it in principal scope; the application or orchestrator generates the operation ID and idempotency key. The model cannot inject that trusted metadata into arguments and decide it for itself. Permissions, approval, idempotency, and real execution stay outside the model. Even structured external-system output can be stale, wrong, or contain prompt injection.

## Source and maintenance status

The teaching structure, threat model, offline dispatcher, fixtures, and tests in this course are original to this project. Official documentation, specifications, and OWASP material are used to verify product behavior and engineering boundaries; this course does not reproduce third-party prose or images. Provider APIs and model capabilities evolve, so the course is marked dynamic. See [[maintenance-records/content-quality-and-source-labeling-standard|Content quality and source-labeling standard]] for the meaning of source and status labels.

## Place in the overall learning path

This course belongs to the Agent Runtime domain and is a core entry point for the Agent Application, Agent Platform, and Multimodal Real-Time tracks.

- JSON and [[api/00-index|API]] provide structure, error, and network foundations.
- The API material handles provider requests, streaming events, and error adaptation.
- [[rag/01-system-boundaries-and-the-complete-pipeline|RAG]] supplies external knowledge evidence; controlled tools are better for live state and side effects.
- This course establishes the trusted execution boundary for one or more calls.
- [[agent-core/00-index|Agent Core]] places calls inside a stateful loop with budgets and termination conditions.
- MCP standardizes capability discovery and invocation protocols; it does not replace business authorization or idempotency.

## Learning objectives

After completing this course, you can:

- distinguish tools, function tools, custom tools, built-in tools, and client/server execution;
- design complete input contracts with clear names, descriptions, and supported JSON Schema;
- explain why strict/schema constrains shape but cannot prove business correctness, ownership, or permission;
- source tenant, subject, roles, and service credentials from a trusted session rather than model arguments;
- implement the allowlist → schema → business → AuthN/AuthZ → idempotency-state → approval-for-first-execution → execute pipeline;
- bind an approval to the precise principal, tool, argument digest, operation/call, schema/policy revision, and expiry;
- use a call ID to correlate a result, an operation ID to trace a business task, and an idempotency key to suppress duplicate side effects;
- handle zero, one, many, parallel, dependent, and partially failed calls;
- treat tool results as untrusted data and bound their size, type, provenance, and authority for the next step;
- separate model-visible results from protected audit records and recompute request/result/call triple bindings;
- handle the uncertainty of a timeout after an action may already have run;
- persist idempotency and recovery state with SQLite uniqueness, an operation ledger, a transactional outbox, leases, and receipt reconciliation;
- explain why those measures still do not prove distributed exactly-once delivery; and
- evaluate routing, arguments, authorization, execution, recovery, security, and end-to-end outcomes.

## Prerequisites

- JSON: types, strict parsing, and schemas.
- [[api/00-index|API]]: authentication, HTTP, rate limits, timeouts, and retries.
- [[prompt-engineering/00-index|Prompt Engineering]]: instruction boundaries.
- [[context-engineering/00-index|Context Engineering]]: external data and state management.
- Basic Python dataclasses, exceptions, and unit tests.

The project uses only the Python 3 standard library. It does not contact a real model, network, or business service.

## Core terms

| Term | Plain-language explanation | What it does not solve |
| --- | --- | --- |
| tool definition | Name, description, and input shape shown to the model | It does not implement a function. |
| tool call | Tool name and arguments proposed by the model | It does not mean the tool executed. |
| tool result | Structured output from the application or service | It is not automatically trustworthy. |
| handler | Code that performs the real action in the trusted application | The model must not choose it dynamically. |
| registry / allowlist | Explicit mapping from tool name to schema, risk, and handler | It is not resource authorization. |
| call ID | Correlates a call in one turn with its result | It does not prevent duplicate business actions. |
| operation ID | Traces a business task across turns or services | It does not provide idempotency. |
| idempotency key | Recognizes the same business intent on retry | The same key with different arguments must conflict. |
| approval | A human authorization record for one precise high-risk action | It is not a permanent pass. |
| adapter | Converts provider messages to internal finite states | It does not contain business rules. |

## Recommended order

| Order | Lesson | Learning output |
| --- | --- | --- |
| 1 | [[tool-calling-function-calling/01-tool-contracts-and-schema-design\|Tool contracts and schema design]] | Tool categories; input/output contracts; versioning policy |
| 2 | [[tool-calling-function-calling/02-call-proposals-validation-and-authorization\|Call proposals, validation, and authorization]] | Trust boundary, identity injection, resource authorization, and approval binding |
| 3 | [[tool-calling-function-calling/03-execution-loop-and-call-correlation\|Execution loop and call correlation]] | Provider-neutral state machine, ID correlation, and loop limits |
| 4 | [[tool-calling-function-calling/04-multiple-calls-parallelism-and-dependencies\|Multiple calls, parallelism, and dependencies]] | DAGs, join strategies, partial success, and compensation |
| 5 | [[tool-calling-function-calling/05-results-errors-and-untrusted-data\|Results, errors, and untrusted data]] | Dual projections, per-tool output schemas, triple digest binding, error catalog, and provider adapters |
| 6 | [[tool-calling-function-calling/06-idempotency-timeouts-and-observability\|Idempotency, timeouts, and observability]] | Duplicate suppression, timeout ambiguity, audit, and SLOs |
| 7 | [[tool-calling-function-calling/07-tool-calling-evaluation-and-offline-project\|Tool-calling evaluation and offline project]] | An 18-scenario, 23-step Tool Result v2 fixture and 120 regression tests for resource limits, approvals, and adapters |
| 8 | [[tool-calling-function-calling/08-project-sqlite-persistent-idempotency-and-outbox-recovery\|SQLite persistence, idempotency, and outbox recovery]] | A ledger/outbox/lease/receipt adapter above v2, with 94 regressions for current claims, approval context, multi-connection, and crashes |

## Hands-on entry point

| File | Purpose |
| --- | --- |
| [[tool-calling-function-calling/examples/tool-cases.json\|tool-cases.json]] | tool-cases-v2: 18 scenarios, 23 dispatch/query-status steps, and expected dual projections |
| [[tool-calling-function-calling/examples/tool_dispatcher.py\|tool_dispatcher.py]] | Proposal/context separation, per-tool input/output contracts, authorization/approval/idempotency, explicit status reconciliation, dual projections, triple bindings, and three provider adapters |
| [[tool-calling-function-calling/examples/test_tool_dispatcher.py\|test_tool_dispatcher.py]] | 120 tests for fixture limits, approver binding, current-business-state checks, failure recovery, output contamination, swap attacks, digest recomputation, provider-profile isolation, adapters, and CLI |
| [[tool-calling-function-calling/examples/persistence/persistence-case.json\|persistence-case.json]] | Strict JSON scenario for a persistent write action |
| [[tool-calling-function-calling/examples/persistence/persistent_tool_runtime.py\|persistent_tool_runtime.py]] | SQLite operation ledger, transactional outbox, leases, receipt reconciliation, and PASS/BLOCK CLI |
| [[tool-calling-function-calling/examples/persistence/test_persistent_tool_runtime.py\|test_persistent_tool_runtime.py]] | 94 tests for JSON/database boundaries, current-principal resolution, approver and provider-context evidence, business state, call purpose, idempotency, crashes, authorization/contract drift, CLI/audit redaction, tampering, and multi-connection behavior |

Run from the repository root:

~~~powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONIOENCODING = 'utf-8'
$examples = '.\docs-EN\tool-calling-function-calling\examples'

python -B -W error "$examples\tool_dispatcher.py" --fixture "$examples\tool-cases.json"
python -B -W error -m unittest discover -s $examples -p 'test_tool_dispatcher.py' -v

$persistence = Join-Path $examples 'persistence'
$db = Join-Path ([IO.Path]::GetTempPath()) ("tool-persistence-learning-{0}.sqlite3" -f [guid]::NewGuid().ToString('N'))
python -B -W error "$persistence\persistent_tool_runtime.py" --db $db --fixture "$persistence\persistence-case.json" dispatch
python -B -W error -m unittest discover -s $persistence -p 'test_persistent_tool_runtime.py' -v
~~~

The temporary database is created in the system temporary directory rather than the repository. The random GUID avoids collisions between concurrent runs.

## Mastery criteria

- [ ] I can state the responsibilities of the model, adapter, dispatcher, handler, and business service.
- [ ] Tools resolve only from an explicit registry; unknown names never trigger dynamic import or eval.
- [ ] The schema rejects missing, extra, wrong-type, and invalid-enum arguments.
- [ ] Tenant, subject, roles, and service credentials do not come from the model.
- [ ] Unauthorized resources return consistent, non-enumerating errors.
- [ ] A write does not run without approval, after expiry, or after an argument, provider/API/adapter context, schema, or policy revision changes.
- [ ] The same idempotency key and intent can replay across SQLite connections/runtime restarts; the same key with a different intent conflicts, and ledger/outbox writes share one local transaction.
- [ ] I can explain why an expired outbox-worker lease may redeliver and why downstream idempotency is still mandatory; I do not claim exactly once.
- [ ] I distinguish a confirmed pre-execution timeout from an unknown post-commit outcome; the latter is reconciled before any retry.
- [ ] Idempotency keys have tenant/subject/tool scope and cannot let another tenant occupy the namespace.
- [ ] Multiple calls run concurrently only when they are independent, conflict-free, and have explicit failure semantics.
- [ ] Tool results remain untrusted data and cannot expand authority for the next action.
- [ ] Per-tool output schemas reject extra control fields, sensitive fields, forged error origins, and input/output mismatches.
- [ ] model_result and protected_audit are separate; provider payloads never expose the audit projection.
- [ ] I can recompute full request/result/call SHA-256 values; call binding covers downstream request/receipt/status reference and rejects cross-call, cross-response, or evidence swaps.
- [ ] I distinguish fresh, local_replay, and receipt_reconciled; unknown recovery happens only through explicit status query.
- [ ] The loop has limits for turns, calls, time, cost, and repeated progress.
- [ ] I can run and explain the 120 v2 tests and 94 persistent-layer tests, including their boundaries for offline execution contracts, SQLite-local races, at-least-once-compatible primitives, and real provider/distributed delivery.

## Related knowledge bases

| Knowledge base | Relationship |
| --- | --- |
| [[api/00-index\|API]] | Parses provider output, streaming events, and API failures |
| [[rag/01-system-boundaries-and-the-complete-pipeline\|RAG]] | Supplies sourced knowledge; tools handle live state and actions |
| MCP | Supplies standardized capability catalogs and transport, not business control |
| [[agent-core/00-index\|Agent Core]] | Places calls in an observe–decide–act loop |
| [[workflow-automation/00-index\|Workflow Automation]] | Uses reliable orchestration, retries, and compensation for fixed-path tasks |
| Evaluation systems | Evaluate routing, arguments, execution, recovery, and task success |
| [[ai-safety/00-index\|AI Safety]] | Covers prompt injection, privilege escalation, data disclosure, and tool misuse |

## Primary references

- [OpenAI: Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [Anthropic: How tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works)
- [Anthropic: Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)
- [Google AI: Function calling with the Gemini API](https://ai.google.dev/gemini-api/docs/function-calling)
- [JSON Schema 2020-12 Core](https://json-schema.org/draft/2020-12/json-schema-core)
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
- [OWASP GenAI: LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
- [SQLite: Transactions](https://www.sqlite.org/lang_transaction.html)
- [SQLite: Write-Ahead Logging](https://www.sqlite.org/wal.html)
- [SQLite: UPSERT](https://www.sqlite.org/lang_upsert.html)
- [Stripe API: Idempotent requests](https://docs.stripe.com/api/idempotent_requests)

Sources were retrieved on 2026-07-21. Tool fields, strict mode, parallelism limits, server-side tools, and model compatibility can change; lock the API/SDK/model version and recheck official documentation during integration.
