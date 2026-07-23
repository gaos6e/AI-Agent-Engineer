---
title: "Structured Output and Streaming Responses"
tags:
  - llm-api
  - streaming
  - structured-output
aliases:
  - LLM Streaming Responses
source_checked: 2026-07-21
source_baseline:
  - OpenAI Structured Outputs and streaming Responses documentation
  - Anthropic Streaming Messages and API errors documentation
  - Gemini Interactions v1 reference and streaming documentation
  - WHATWG Server-sent events standard
content_origin: original
content_status: dynamic
lang: en
translation_key: LLM API集成/04-结构化输出与流式响应.md
translation_source_hash: f73448b0aa0530c52db49662bf0ddc346a89fdea979a102a85dcb8fdd0d78c11
translation_route: zh-CN/LLM-API集成/04-结构化输出与流式响应
translation_default_route: zh-CN/LLM-API集成/04-结构化输出与流式响应
---

# Structured Output and Streaming Responses

## Objectives

Safely handle schema-constrained output and SSE incremental events, and understand the difference between “HTTP succeeded” and “the business result is complete.”

## The structured-output pipeline

1. Select the schema subset currently supported by the provider.
2. Validate the schema itself locally before sending a request.
3. Handle normal completion, refusal, safety blocking, output truncation, and API errors.
4. Parse and validate the schema of completed content again.
5. Perform business-semantic validation and authorization decisions.

JSON that guarantees only “valid JSON” cannot replace a schema. Even schema-compliant content can contain an amount from the wrong row, a citation that does not exist, or an unauthorized action.

## Tool parameters and a final structured answer are two contracts

| API family | Final structured answer | Tool/function parameters | Key difference |
| --- | --- | --- | --- |
| OpenAI Responses | `text.format` | a function tool's `parameters` plus `strict` | Omitting `strict` behaves differently for Responses and Chat Completions |
| Anthropic Messages | The native request uses `output_config.format`; SDK `messages.parse(output_format=...)` is a convenience layer | `input_schema`; strict tools additionally set `strict: true` | An SDK helper can transform the original schema, so record both original and actually-sent versions |
| Gemini Interactions v1 | `response_format`; JSON uses `type=text`, `mime_type=application/json`, and `schema` | a function's `parameters` | It has no OpenAI function-tool `strict` field |

As of 2026-07-21, when an OpenAI Responses function tool omits `strict`, the server first attempts to normalize its schema to strict mode. Only if normalization cannot succeed does it fall back to non-strict mode and show `strict:false` on the response tool. Chat Completions still treat omission as non-strict. A production contract should not rely on this implicit branch: set `strict` explicitly. When it is `true`, follow the current requirement that an object sets `additionalProperties:false` and every property appears in `required`, then perform local schema and semantic validation.

Anthropic's structured-output SDK helper can transform some SDK type/schema features into an API-accepted shape. During audit, do not save only the caller's original schema; also retain the adapter/SDK version and schema actually sent. With all three providers, a refusal, `max_tokens`/truncation, safety block, or API error can mean that there is no business answer satisfying the final schema. A parser must inspect terminal state before structure.

## What a streaming response is

Many LLM APIs use Server-Sent Events (SSE) to send typed events. A client does not keep concatenating arbitrary HTTP characters. First, an SSE decoder processes UTF-8, lines, and `event`/`data`/`id` framing; then provider protocol code processes start, content delta, tool-parameter delta, completion, and error events. Event types can expand, so record unknown types and handle them under a compatibility policy.

A robust state machine has at least:

```text
INIT -> STARTED -> STREAMING -> COMPLETED
                         \-> FAILED
```

Only a valid terminal event followed by validation is success. A broken connection, timeout, or in-stream error cannot turn partially displayed text into a complete answer. Tool-parameter JSON is often split across several deltas as well; wait for the corresponding content block to end before parsing it, and never execute a tool with partial JSON.

This course uses `response.started`, `response.text.delta`, `response.finished`, and `response.failed` as **canonical internal events**. They are not raw event names from OpenAI, Anthropic, or Google. A real adapter must map raw events according to the API version in use. When a new unknown event appears, log it explicitly and fail or handle it under a compatibility policy; do not guess its meaning.

Do not merge three testing layers into one: raw SSE fixtures validate framing, SDK-object fixtures validate pinned-SDK decoding, and application projections validate the adapter and business state machine. The course's OpenAI/Gemini provider fixtures are hand-authored `typed-sse-projection` data, while the Anthropic fixture is a `wire-sse-envelope-projection`; neither is captured live network bytes.

## Bounded assembly and explicit termination

A stream consumer must limit event count, one delta, cumulative text/parameters, JSON depth, and collection size. Otherwise, a stream that never terminates or keeps sending small fragments can grow memory without bound. Hitting a limit is an auditable protocol failure: retain request/operation ID, consumed count, and controlled partial metadata; close the stream; do not present it as success; and never execute any provisional tool call.

Define terminal authority separately for each API family. HTTP 200, the first event, the end of a content block, or even “one function's parameters are assembled” does not mean a whole turn is complete. A call may enter the host execution ledger only after a valid provider terminal and local validation both pass. On consumer cancellation or deadline expiry, explicitly close the stream context as well; stopping reads does not guarantee that the socket or billing has stopped.

Retrying after a broken stream usually begins a new generation with possibly different text. Do not concatenate “the old partial” and “the new-request partial” into one answer. Implement a provider's explicit recovery identifier and protocol only when current documentation supports it; otherwise discard or mark the old partial, and place external tool side effects after complete termination and validation.

## UI and safety

Streaming can reduce perceived first-byte delay, but adds difficulty for content moderation, retraction, ordering, and disconnect recovery. Buffer and review high-risk output on the server first. If you display it in real time, the UI should clearly state “generating/incomplete,” and retain failure state rather than disguising an error as success.

## Exercise and self-check

Write an assembly state machine for `start, delta("hel"), delta("lo"), completed`, then test `start, delta, error` and a stream missing `completed`. Self-check: why does checking only the status code misclassify a stream that receives an in-stream error after HTTP 200?

## Mastery checklist

- [ ] JSON syntax, schema, business semantics, and action authorization are validated in order; refusal and truncation are independent states.
- [ ] I process streams through typed events and a state machine; I do not operate on raw bytes or partial tool parameters.
- [ ] HTTP 200, the first delta, and text already rendered in the UI do not prove business completion.
- [ ] A broken stream's partial is marked failed; regeneration never silently concatenates it with an old partial.
- [ ] Canonical events remain separate from provider raw events, and unknown events are never treated as ignorable success by default.
- [ ] Raw SSE, SDK typed objects, and application projections each have tests; fixture parity is not presented as live conformance.
- [ ] Events, a single delta, cumulative buffers, and JSON resources all have bounds; a violation closes the stream and leaves failure evidence.

## Next step

Continue to [[llm-api-integration/05-timeouts-errors-rate-limiting-and-retries|Timeouts, Errors, Rate Limits, and Retries]]. After completing the reliable-client core, use [[llm-api-integration/08-project-provider-contract-tests|Provider Contract Tests]] to compare the current Reference/SDK event projections, identity association, and terminal gates of the three providers. Do not treat this chapter's canonical events or offline projections as a provider wire protocol.

## References

- [OpenAI: Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) (accessed 2026-07-21)
- [OpenAI: Function calling](https://developers.openai.com/api/docs/guides/function-calling) (the Responses/Chat Completions `strict` default difference; accessed 2026-07-21)
- [OpenAI: Migrate to Responses—Update streaming consumers](https://developers.openai.com/api/docs/guides/migrate-to-responses#7-update-streaming-consumers) (accessed 2026-07-21)
- [OpenAI: Streaming API responses](https://developers.openai.com/api/docs/guides/streaming-responses) (accessed 2026-07-21)
- [Anthropic: Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) (accessed 2026-07-21)
- [Anthropic: Streaming Messages](https://platform.claude.com/docs/en/build-with-claude/streaming) (accessed 2026-07-21)
- [Anthropic: API errors](https://platform.claude.com/docs/en/api/errors) (a stream can still fail after HTTP 200; accessed 2026-07-21)
- [Google: Structured output](https://ai.google.dev/gemini-api/docs/structured-output) (accessed 2026-07-21)
- [Google: Interactions API v1 reference](https://ai.google.dev/api/interactions-api-v1) (accessed 2026-07-21)
- [Google: Interactions streaming](https://ai.google.dev/gemini-api/docs/streaming) (accessed 2026-07-21)
- [WHATWG: Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
