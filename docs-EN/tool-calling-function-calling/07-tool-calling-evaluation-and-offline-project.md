---
title: "Tool-Calling Evaluation and Offline Project"
tags:
  - ai-agent-engineer
  - tool-calling
  - project
aliases:
  - Tool Calling Project
  - Offline Tool Dispatcher
source_checked: 2026-07-21
execution_verified: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: "Tool Calling（含 Function Calling）/07-工具调用评测与离线项目.md"
translation_source_hash: f249307a157b7d5d0631f72215758897b681a58821fc8e3b9a9bcf16cb4ac525
translation_route: zh-CN/Tool-Calling（含-Function-Calling）/07-工具调用评测与离线项目
translation_default_route: zh-CN/Tool-Calling（含-Function-Calling）/07-工具调用评测与离线项目
---

# Tool-Calling Evaluation and Offline Project

## Project goal

Run a Tool Result v2 trusted-boundary dispatcher that connects to no real model, SDK, network, or business service. It validates the application contract from a model proposal to a provider return:

~~~mermaid
flowchart LR
    P["Model proposal<br/>name + arguments"] --> B["host context binding<br/>provider/call/operation/idempotency"]
    B --> I["registry + exact input"]
    I --> A["principal + tenant/resource authorization"]
    A --> D["idempotency + eligible approval<br/>current business state + deadline"]
    D --> H["mock handler"]
    H --> O["per-tool output schema"]
    O --> M["model_result"]
    O --> U["protected_audit + 3 digests"]
    M --> R["OpenAI / Anthropic / Gemini adapter"]
~~~

It validates the application execution contract. It does not validate whether a real model chooses the correct tool, whether a real SDK is compatible, or distributed exactly-once behavior.

## Project files

| File | Content |
| --- | --- |
| [[tool-calling-function-calling/examples/tool-cases.json\|tool-cases.json]] | 'tool-cases-v2': 18 scenarios, 23 dispatch/query-status steps, and model/audit contract revisions |
| [[tool-calling-function-calling/examples/tool_dispatcher.py\|tool_dispatcher.py]] | Bounded strict fixture, proposal/context binding, registry, authorization, approver eligibility, business-state recheck, idempotency, explicit status query, per-tool outputs, dual projections, digests, and three adapters |
| [[tool-calling-function-calling/examples/test_tool_dispatcher.py\|test_tool_dispatcher.py]] | 120 regression tests for fixture resource bounds, digests, dispatcher behavior, exception recovery, output contamination, result/evidence swaps, provider-profile isolation, adapters, and CLI |

## Environment and execution

- Windows 11 and PowerShell 7;
- verified with Python 3.11;
- standard library only: no API key, network, database, or model;
- use '-B' to avoid creating '__pycache__' and '-W error' to expose warnings.

Run these commands from the repository root:

~~~powershell
$env:PYTHONDONTWRITEBYTECODE = '1' # Do not write Python bytecode caches; keep the example directory clean.
$env:PYTHONIOENCODING = 'utf-8' # Keep terminal encoding stable for JSON and error messages.
$examples = '.\docs-EN\tool-calling-function-calling\examples' # Reuse the dispatcher-example directory below.

python -B -W error "$examples\tool_dispatcher.py" --fixture "$examples\tool-cases.json" # Run the data-driven fixture and confirm the public CLI contract first.
python -B -m unittest discover -s $examples -p 'test_tool_dispatcher.py' # Run dispatcher tests in normal mode.
python -O -B -m unittest discover -s $examples -p 'test_tool_dispatcher.py' # Ensure runtime checks do not depend on bare assert in optimized mode.
python -B -W error -m unittest discover -s $examples -p 'test_tool_dispatcher.py' # Check warning-as-error compatibility.
python -O -B -W error -m unittest discover -s $examples -p 'test_tool_dispatcher.py' # Combine strict modes to cover behavior that is easy to miss.
~~~

The CLI must report 'passed=true', 'case_count=18', and 'step_count=23'; all four test modes must report 120 passing tests.

## Two mock tools

### get_order

- Accepts only 'order_ref'.
- Tenant, subject, and roles come from the trusted principal.
- Another person's order in the same tenant and an order in another tenant both return external 'NOT_FOUND'.
- Its exact output fields are 'order_ref/status', and status is limited to 'paid/pending/refunded'.
- Output binds the input order reference, orders producer revision, and resource revision.
- Successful data is labelled 'trust=untrusted_data'.

### create_refund_draft

- Creates a draft; it does not submit a real refund.
- 'reason' is limited to 'duplicate/damaged/other'.
- A first execution needs an idempotency key and an eligible approval bound to the current principal, provider/API family/adapter revision, call/operation, arguments, and contract revisions.
- The approver must be in a trusted allowlist and the order must still be 'paid' at execution; an old approval cannot cover changed business state.
- The idempotency namespace is tenant + subject + tool + key.
- Its exact output fields are 'draft_id/order_ref/reason'; additional 'status', token, or control fields fail.
- The same key and intent return 'delivery=local_replay'; the same key with a different intent conflicts.

## Why fixture v2 separates proposal from context

Every step limits model-controllable fields to:

~~~json
{"name": "get_order", "arguments": {"order_ref": "ORDER-7"}}
~~~

Trusted adapter/context data separately supplies provider, API family, response ID, call ID, operation ID, idempotency key, and adapter revision. The fixture accepts only three registered profiles:

| provider | API family | adapter revision |
| --- | --- | --- |
| OpenAI | Responses | 'openai-responses-v1' |
| Anthropic | Messages | 'anthropic-messages-v1' |
| Google | Interactions | 'gemini-interactions-v1' |

Arguments cannot declare their own principal, approval, call ID, or idempotency key. Before parsing, the fixture limits input to 65,536 UTF-8 bytes and uses a nonrecursive scan to limit JSON-container nesting to 32 levels before entering Python's JSON decoder. Thus even deeply nested input that stays below the byte limit receives a controlled fixture-contract error rather than a 'RecursionError' or traceback. It then bounds cases/steps/roles, identifiers, times, and the portable JSON domain, and rejects duplicate JSON keys, NaN/Infinity, extra fields, unsorted roles, boolean or out-of-range times, self-referential query status, and unregistered provider profiles. File-read errors do not echo local paths. These offline bounds are not a complete production denial-of-service gateway.

## Eighteen scenarios and twenty-three steps

| Category | Scenarios |
| --- | --- |
| Normal read | The caller's own order |
| Resource authorization | Another person's same-tenant order and cross-tenant order both fail closed |
| Registry | An unknown dangerous tool |
| Input schema | Missing field, extra 'is_admin', wrong type, invalid enum/injection text |
| Write | No approval, valid approval, expired/mismatched approval |
| Idempotency | Same-key/same-intent local replay; same-key/different-intent conflict |
| Call correlation | Changing a request under the same provider response/call |
| Failure | Timeout before execution, unknown outcome after commit, explicit receipt query, unavailable receipt, and 429 |

Each case receives a new dispatcher. A case that needs sequential semantics contains several steps in the same instance.

## Three delivery types are evidence, not UI labels

### fresh

The handler really executed this time and passed its output contract. For a write tool, the side-effect counter increases once.

### local_replay

The same tenant/subject/tool/key, request digest, and output/effect/handler/producer revisions hit a local record. It does not execute again and returns a defensive deep copy, so a caller mutating the first result cannot contaminate the record.

### receipt_reconciled

'timeout_after_commit' first returns:

~~~text
status=unknown
outcome=unknown
recovery=query_status
opaque status_ref in protected_audit
~~~

A second 'dispatch' remains 'OUTCOME_UNKNOWN'. Only an explicit 'query_operation_status' will:

1. recheck current resource authorization;
2. recompute the request digest;
3. bind tenant/subject/tool/key, effect and producer revisions;
4. validate the downstream receipt and 'status_ref';
5. confirm that provider/API family/adapter revision is still the approved operation context, then bind provider call identity to the 'query_status' purpose so it cannot become a new dispatch;
6. backfill the local record and return 'receipt_reconciled'.

When the receipt is unavailable, the query continues to return unknown and the side effect remains only once. Changing arguments, key, principal, or contract revision returns 'STATUS_CONFLICT/NOT_FOUND'; it does not “guess a success state.”

## Dual projections and triple SHA-256

### model_result

It contains only:

- 'status';
- per-tool 'data' or a fixed-catalog 'error';
- 'outcome/delivery/complete/truncated';
- minimal provenance and 'trust'.

### protected_audit

It stores a principal reference, provider context, tool contract, downstream receipt/status reference, redactions, and:

- 'request_sha256': principal + tool + arguments + input/output/effect revisions;
- 'result_sha256': complete model_result;
- 'call_binding_sha256': provider turn + call/operation + idempotency key + adapter/tool contract + the first two digests + downstream request/receipt/status reference.

The request digest deliberately still excludes the idempotency key to preserve the semantics of “same business intent.” The key belongs to call-level execution identity and must therefore enter the call binding.

All three fields must be complete 64-character lowercase hexadecimal values and the validator recomputes them. 'protected_audit' appears in no provider payload.

## Attack counterexamples that must be replayed

The 120 tests do not only exercise the happy path. They directly replay:

| Counterexample | Expected rejection point |
| --- | --- |
| Give a legal A package to B's call | Provider context, operation, and call binding mismatch |
| Change only a write call's idempotency key | Call binding mismatch; provider adapter rejects |
| Replace only downstream request/receipt/status reference | Recomputed call binding mismatch |
| Swap two model_result values | Result SHA-256 mismatch |
| Replace request digest with 64 well-formed '0' characters | Trusted-context recomputation fails |
| Inject an extra 'status' into refund output | Per-tool exact output schema |
| Nest 'authorization: Bearer ...' | Recursive sensitive-field control |
| Change source/producer or fixed error message | Registry/provenance or error catalog |
| Inject 'status' at package top level | Exact package fields |
| Replace 'execution' with a string | Returns a validation error; it cannot throw past the adapter |
| Attempt to send protected audit to all three payloads | Adapter projection tests |
| Use an unauthorized or malformed approver, or execute exactly at expiry | Approval fails closed |
| A JSON fixture below 65,536 UTF-8 bytes but 4,096 levels deep | Pre-decoder resource limit; CLI has no traceback |
| Order changes from 'paid' to a nonrefundable state after approval | Business-state recheck before first write |
| Write handler raises or returns invalid output | Enter unknown and block blind replay |
| Use a status-query call identity for a new dispatch | Purpose-bound call-fingerprint conflict |

Tests should hit real attack seams, not merely assert that “the program did not crash.”

## Three provider adapters

Adapters perform only final message mapping; business rules stay in the dispatcher:

| Function | Output |
| --- | --- |
| 'to_openai_responses' | 'function_call_output', original call ID, JSON-string 'output' |
| 'to_anthropic_messages' | 'tool_result', original tool-use ID, text 'content', 'is_error' |
| 'to_gemini_interactions' | 'previous_interaction_id' and 'function_result', with model result in a 'result' text block |

Every function first validates the provider profile and complete package. These are schema-only teaching adapters; they do not validate SDK types, real streamed events, reasoning/thinking continuation, every message-order constraint, or API-version compatibility.

The next layer is the companion [[api/00-index|API]] material: it separately parses the current streaming contracts for all three providers and constructs continuation payloads, but still reads no credentials, imports no provider SDK, and does not replace this project's trusted-boundary or persistence semantics.

## Layers of the 120 tests

| Layer | Main coverage |
| --- | --- |
| Fixture | Exact fields, revisions, reference order, provider profiles, and file/collection/time/JSON resource limits |
| Digest | Canonical arguments, principal, semantic contract, approver, provider turn, and downstream-evidence binding |
| Dispatcher | Registry, authorization, business-state recheck, approval, same-profile idempotency, cross-profile conflict, handler exception, timeout, and explicit status query |
| Handler output | Fields/types/enums/input binding, provenance, size, depth, sensitive fields, and controlled rejection of overly deep output |
| Result contract | Dual projections, error catalog, 64-hex recomputation, swapped/fabricated/malformed results |
| Result set | Order independence; missing, duplicate, unknown, and cross-call swaps |
| Provider adapter | OpenAI, Anthropic, and Gemini shapes plus protected-audit isolation |
| CLI | Fixture success in normal and '-O' modes, plus controlled no-traceback rejection of a deeply nested fixture |

'-O' removes bare 'assert'. Passing both normal and '-O' modes can prove only that key project validation does not depend on bare asserts; it cannot prove that a real service has no defect.

## What real-model evaluation still needs

With a real model, lock provider, API, model, prompt, tool schema, and adapter revision, then build a separate evaluation:

| Layer | Metrics / samples |
| --- | --- |
| Whether to call | Should call, no tool needed, clarification, refusal |
| Tool choice | Correct tool, synonym confusion, unknown tool |
| Arguments | Exact/schema, business values, invented IDs, negation, units |
| Safety | Overreach, indirect prompt injection, recipient/path/URL |
| Execution | Success, timeout stage, 429, partial failure, duplicate side effect |
| Recovery | Approval pause/resume, explicit status query, fallback, stop |
| Multiple calls | DAG, correlation, parallelism, join, compensation |
| End to end | Task success, human correction, latency, tokens, and cost |

A strict schema can improve structural conformance, but it cannot replace evaluation of business correctness, safety, and result binding.

## Explicit boundaries not proven by this project

- An in-memory mapping is not cross-process idempotency storage and has no atomic 'in_progress' unique constraint.
- A digest is not a signature, and deterministic JSON makes no RFC 8785 claim.
- A mock receipt is not a real third-party API status query.
- There are no real credentials, auth tokens, network, stream events, SDK, or concurrent contention.
- The output project covers only two shallow JSON tools, not paging, artifacts, multimodal data, or large objects.
- The teaching hash in 'principal_ref' does not replace production privacy design or keyed pseudonymization.
- Unknown after a write-handler exception is only a conservative state; the in-memory example has no real downstream query, persistence, or crash-recovery evidence.
- A schema-only provider adapter is not a provider integration test.

## Extension tasks

### A. Persistent idempotency and crash recovery

Implemented as the separate Layer B project: [[tool-calling-function-calling/08-project-sqlite-persistent-idempotency-and-outbox-recovery|SQLite persistence, idempotency, and outbox recovery]]. It reuses this project's request digest, call binding, input/output contracts, and result package, then adds tenant/subject/tool/key unique constraints, an operation ledger, transactional outbox, leases, process restart, receipt reconciliation, and multi-connection contention tests while explicitly not claiming exactly once.

### B. Signatures or trusted event storage

Lock a cross-language canonicalization algorithm and compare threat models for ordinary SHA-256, HMAC, digital signatures, and an append-only audit log. Do not merely make the digest longer.

### C. File, URL, and artifact output

Add path-root restrictions, URL redirect/DNS validation, MIME and size controls, short-lived authorized references, and malicious-attachment fixtures. Do not put binary data or secrets directly into the model projection.

### D. Provider streaming contracts and live integration

Offline provider stream/continuation fixtures belong in the companion [[api/00-index|API]] material. The next step is to use a separate credentialed environment with no committed outputs to verify three locked SDKs: zero/one/many calls, real chunks, stream interruption, correlation IDs, error results, continuation state, and payload limits, recording exact SDK/model/API revisions.

## Project acceptance

- [ ] All 18 cases and 23 steps pass.
- [ ] An unknown tool cannot be dynamically imported or executed.
- [ ] Inputs and per-tool outputs reject extra/missing/type/enum errors.
- [ ] Same-tenant-other-person and cross-tenant resources are both nonenumerable.
- [ ] Approval binds principal, provider/API family/adapter revision, call/operation, arguments, and semantic contract revisions.
- [ ] Approver eligibility, half-open expiry, and business state before execution are revalidated; malformed approval fails closed.
- [ ] Same-key/same-intent local replay executes once; same-key/different-intent has an explicit conflict.
- [ ] Dispatch does not resolve unknown implicitly; an explicit status query reauthorizes and validates the receipt.
- [ ] Model/audit dual projections are isolated and all three provider payloads omit protected audit.
- [ ] Request/result/call complete SHA-256 values are recomputed rather than only format-checked.
- [ ] Cross-call/result swaps, fabricated digests, injected status, sensitive fields, and error-catalog tampering all fail.
- [ ] All 120 tests pass under normal, '-O', '-W error', and '-O -W error'.
- [ ] You can explain the remaining boundaries of in-memory idempotency, teaching digests, and schema-only adapters.

## Self-check

1. Why cannot dispatching again replace 'query_operation_status'?
2. What do 'request_sha256', 'result_sha256', and 'call_binding_sha256' each bind?
3. Why cannot business 'data.status' overwrite control-plane top-level 'status'?
4. What different evidence supports 'local_replay' and 'receipt_reconciled'?
5. Why do 120 green tests still not prove real-model routing or provider-SDK integration is correct?

Return to [[tool-calling-function-calling/00-index|the Tool Calling index]]; next complete [[tool-calling-function-calling/08-project-sqlite-persistent-idempotency-and-outbox-recovery|SQLite persistence, idempotency, and outbox recovery]], then move to [[agent-core/00-index|Agent Core]]. For a standard protocol that connects external capabilities, continue with MCP.

## References

- [OpenAI API: Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [Anthropic: Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)
- [Google AI: Function calling with the Gemini API](https://ai.google.dev/gemini-api/docs/function-calling)
- [Python 3.11: json — JSON encoder and decoder](https://docs.python.org/3.11/library/json.html)
- [RFC 9110: Idempotent Methods](https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods)
- [OWASP GenAI: LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)

Sources accessed: 2026-07-21. The three provider shapes came from official documentation on that date. Python's 'json' documentation notes that untrusted JSON can consume substantial CPU and memory, so the example sets byte and nesting limits before decoding. '65,536 bytes' and 32 levels are regression-testable teaching limits, not universal production thresholds. The adapter remains an offline teaching implementation; before release, recheck it against live SDK/API versions that are locked for the deployment.
