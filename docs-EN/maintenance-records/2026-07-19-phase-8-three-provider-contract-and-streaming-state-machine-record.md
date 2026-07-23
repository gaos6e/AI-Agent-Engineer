---
title: "2026-07-19 Phase 8 Three-Provider Contract and Streaming State-Machine Record"
aliases:
  - AI Agent Engineer Phase 8 optimization record
tags:
  - AI-Agent-Engineer
  - maintenance
  - llm-api
  - provider-contract
  - streaming
  - tool-calling
  - red-team
content_origin: original
content_status: validated
source_checked: 2026-07-19
lang: en
translation_key: 维护记录/2026-07-19-第八阶段三家Provider合同与流式状态机记录.md
translation_source_hash: 8e527b856101f9d36f055974f8c5ffaad606604cccf80684b3b9f7008af34c46
translation_route: zh-CN/维护记录/2026-07-19-第八阶段三家Provider合同与流式状态机记录
translation_default_route: zh-CN/维护记录/2026-07-19-第八阶段三家Provider合同与流式状态机记录
---

# 2026-07-19 Phase 8 Three-Provider Contract and Streaming State-Machine Record

This phase turns the Provider-contract gap identified in Phase 7 into a fully offline, auditable course project. The primary Agent unified version boundaries, terminology, continuation semantics, documentation counts, and final verification for three APIs. Specialists performed document-consistency, code-red-team, and official-fact checks. Every high-risk finding was first reproduced, then fixed with a regression; no P0/P1 is currently known.

> [!important] Evidence boundary
>
> <code>docs/LLM API integration/examples/provider_contracts/</code> reads no keys, imports no Provider SDK, and accesses no network. Under the official API Reference/SDK-type baseline on a fixed date, it proves contracts for local projection parser, identity association, terminal gate, resource limits, and continuation builder. OpenAI/Gemini fixture is <code>typed-sse-projection</code>, Anthropic is <code>wire-sse-envelope-projection</code>; neither is raw SSE bytes, an SDK instance, live conformance, server exactly-once, or model-quality evaluation.

## 1. Current baseline and version boundary

- OpenAI Responses with <code>openai-python 2.46.0</code> (2026-07-17): ordinary HTTP <code>previous_response_id</code> continuation is recorded separately from WebSocket current-connection cache.
- Anthropic Messages with <code>anthropic-python 0.117.0</code> (2026-07-16): top-level <code>system</code> remains broadly compatible default; mid-conversation system is allowed only for checked model/placement constraints. Invalid JSON in eager/fine-grained tool input enters recovery.
- Gemini Interactions stable <code>v1</code> with <code>google-genai 2.12.1</code> (2026-07-16): its Step discriminator is fixed to 15 types from official Reference. An MCP-server step in current v1beta OpenAPI is not part of the stable contract and fails closed in local parser.
- Gemini <code>status_update</code> is optional intermediate notification; terminal Interaction status is authoritative. <code>last_event_id</code> supports recovery only for still-retrievable stored-Interaction GET stream.
- Every fixture binds Provider, API family/version, contract revision, SDK baseline, checked date, and HTTPS source URL. Example IDs/model values are synthetic opaque values.

## 2. Implementation and teaching structure

The Three-Provider Contract Tests project adds three versioned fixtures, <code>provider_contracts.py</code>, and <code>test_provider_contracts.py</code>. It retains Provider differences rather than building an event-renaming table:

- **OpenAI:** correlates by <code>sequence_number + output_index + item_id</code>; preserves complete Item lifecycle, non-function terminal binding, direct caller retention, and HTTP storage proof. Stateless replay uses caller-validated input Items plus complete raw output Items.
- **Anthropic:** retains named SSE envelope; thinking/redacted thinking; signatures; citations; and mixed server/client tools. <code>calls</code> exposes only executable client calls; illegal input or a truncated sibling call enters a separate <code>recovery_calls</code>. Continuation requires <code>is_error</code>.
- **Gemini:** deduplicates by <code>event_id</code> and correlates stream by Step index; separates optional <code>status_update</code> from terminal; keeps current usage fields unchanged; separates create/GET complete-steps input-history source; fails closed when opaque model/hosted steps are not provable.

All three turns retain a local canonical snapshot digest. Builders recheck digest before copying history/call/block, detecting post-parse nested-object mutation; it is not a signature or cross-process truth proof. Five builders require explicit re-send of caller controls and verify every observed function name appears in that Provider's tool declaration.

## 3. Red-team closure

| Finding | Repair and regression |
| --- | --- |
| Nonfunction OpenAI Items such as reasoning/message could be replaced in terminal | Preserve <code>output_item.done</code> by output index; terminal validates complete Item consistency; add tamper fixture. |
| Nested dict in frozen dataclasses could mutate after parse, misbinding call/result | Add Provider-specific snapshot digest and fail-closed builder entry; mutation regression for each Provider. |
| An Anthropic truncated turn might let naive caller execute a complete sibling tool call | Put all <code>max_tokens</code> calls in <code>recovery_calls</code>; only explicit <code>stop_reason=tool_use</code> with parseable input enters <code>calls</code>. |
| Deep tool JSON leaked bare <code>RecursionError</code> before <code>json.loads</code> | Add string-scan nesting guard; map parser/load-fixture recursion errors to stable contract error. |
| Malformed HTTPS source URL leaked <code>urlsplit</code> <code>ValueError</code> | Catch and return structured validation error. |
| Gemini v1 included a v1beta MCP Step in stable union | Stable v1 keeps 15 types; forward MCP type receives unknown-Step negative test. |
| Continuation could declare a same-shaped tool with no observed call name | All three builders check observed function name against declaration set. |
| Gemini prior history accepted nonfirst <code>user_input</code>, orphan/duplicate function result | Require initial <code>user_input</code>, paired function call/result, matching names, and complete results. |
| Result iterable could grow forever | <code>_bind_results</code> fails immediately after expected count. |

## 4. Documentation and route synchronization

- LLM API directory moves from 20 reliable-client and 82 legacy Provider tests to 20 + 96, 116 offline tests total, explicitly distinguishing projection, SDK integration, live evaluation, and production audit evidence.
- Lesson 08 adds three Mermaid state machines; OpenAI HTTP/WebSocket storage difference; Anthropic system capability gate/recovery calls; Gemini v1/v1beta boundary/15 Steps/retention/GET-create history/usage/native tool and response-format shape.
- Anthropic introduction narrows absolute claims about <code>system</code> role and adds tool-terminal gate, schema/semantic/permission validation, stable <code>is_error</code> error result, fine-grained-input risk, and one-turn loop limit.
- Dates, Gemini Interactions references, missing-usage semantics, and projection boundary in lessons 04/06/07 are synchronized; the overall route links this phase record.

## 5. Verification actually performed

- Provider contract: 96 tests all passed under normal, <code>-O</code>, warnings-as-errors, and <code>-O + warnings-as-errors</code>.
- Python repository: Python 3.11.9 discovered 68 <code>test_*.py</code>; five files with declared CrewAI/LangGraph/Matplotlib/scikit-learn optional dependencies were left out. The remaining 63 base-environment files passed 2,483/2,483 in each of normal, <code>-W error</code>, <code>-O</code>, and <code>-O -W error</code>—9,932 test executions total. Missing dependencies were not recorded as passed.
- Provider two-file script checks: <code>py_compile</code> plus normal/<code>-O</code> warnings-as-errors regression; no network/key access.
- Site: <code>.website npm test</code> 35/35. Build staged 893 Markdown, emitted 2,432 HTML and 2,676 public files; <code>brokenLocalLinks</code>, <code>forbiddenFiles</code>, <code>progressMetadataLeaks</code>, <code>sensitiveLeaks</code>, <code>selfRedirects</code>, <code>tableWikilinkLeaks</code>, <code>checkboxProgressRuntimeLeaks</code>, <code>interactiveCheckboxes</code>, and <code>katexErrors</code> all 0. It reports 56 course indexes, 225 assets, 8 stage navigation, 56 course navigation, 106 folder navigation.
- Worktree: <code>git diff --check</code> passed; generated cache/bytecode was cleaned in final check.

## Key sources

- [OpenAI Responses function calling](https://developers.openai.com/api/docs/guides/function-calling), [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state), [Programmatic tool calling](https://developers.openai.com/api/docs/guides/tools-programmatic-tool-calling), and [Responses streaming events](https://developers.openai.com/api/reference/resources/responses/streaming-events).
- [Anthropic Streaming Messages](https://platform.claude.com/docs/en/build-with-claude/streaming), [Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls), [Fine-grained tool streaming](https://platform.claude.com/docs/en/agents-and-tools/tool-use/fine-grained-tool-streaming), and [Mid-conversation system messages](https://platform.claude.com/docs/en/build-with-claude/mid-conversation-system-messages).
- [Gemini Interactions overview](https://ai.google.dev/gemini-api/docs/interactions-overview), [Interactions API v1 reference](https://ai.google.dev/api/interactions-api-v1), [Interactions streaming](https://ai.google.dev/gemini-api/docs/streaming), [Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling), and v1beta [OpenAPI](https://ai.google.dev/static/api/interactions.openapi.json) as a forward-drift control only.
- SDK snapshots: [openai-python 2.46.0](https://github.com/openai/openai-python/releases/tag/v2.46.0), [anthropic-python 0.117.0](https://github.com/anthropics/anthropic-sdk-python/releases/tag/v0.117.0), and [google-genai 2.12.1](https://github.com/googleapis/python-genai/releases/tag/v2.12.1).

## Follow-up queue

1. Outside the vault, build a credential-gated, low-cost, no-side-effect live-contract suite for real SSE framing, SDK typed-object decoding, HTTP/WebSocket, timeout, 429, recovery cursor, and default retry.
2. Capture de-identified real wire/SDK fixtures with API version, SDK, model, date, and schema hash, and compare local projections by golden diff.
3. Connect Provider turn with request/execution ledger, approval, business idempotency key, and SQLite persistent idempotency/outbox recovery. Offline parser does not prove exactly-once.
4. Build separate capability/evidence layers for OpenAI built-in/programmatic tools, Anthropic server tools, Gemini hosted/opaque Steps, GenerateContent, and multimodal tool result rather than forcing them into stable-v1 function projection.
5. Manually inspect Mermaid, wide tables, Callouts, and mobile layouts in Obsidian/Quartz, then continue reviewing dynamic SDK/protocol pages elsewhere.

See the preceding [[maintenance-records/2026-07-19-phase-7-external-provenance-artifact-and-route-portability-record|Phase 7 record]]. Source, license, and original/curated/third-party labels continue through the [[maintenance-records/content-quality-and-source-labeling-standard|Content Quality and Source Labeling Standard]].
