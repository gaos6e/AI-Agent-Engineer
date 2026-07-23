---
title: "LLM API Integration Learning Path"
tags:
  - ai-agent-engineer
  - llm-api
  - learning-path
aliases:
  - LLM API Integration Index
  - Large Language Model API Integration
source_checked: 2026-07-22
source_baseline:
  - OpenAI Responses API Reference and openai-python 2.46.0
  - OpenAI API Authentication and Workload Identity Federation
  - OpenAI Codex Authentication and OpenClaw agent runtimes
  - Anthropic Messages API and anthropic-python 0.117.0
  - Gemini Interactions v1 and google-genai 2.12.1
  - RFC 9110 HTTP Semantics and WHATWG Server-sent events
content_origin: original
content_status: dynamic
ai_learning_stage: 3. LLM Application Fundamentals
ai_learning_order: 21
ai_learning_schema: 2
ai_learning_id: llm-api
ai_learning_domain: model-and-context
ai_learning_catalog_order: 2100
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 400
ai_learning_track_agent_app_kind: core
ai_learning_track_rag_order: 400
ai_learning_track_rag_kind: core
ai_learning_track_agent_platform_order: 400
ai_learning_track_agent_platform_kind: core
lang: en
translation_key: LLM API集成/00-目录.md
translation_source_hash: a07e8057bf9aaccdf02caa4064cec5952b3837fb17633b3b04496fbb26eeadfe
translation_route: zh-CN/LLM-API集成/00-目录
translation_default_route: zh-CN/LLM-API集成/00-目录
---

# LLM API Integration

> Source review date: 2026-07-22. Endpoints, SDK methods, authentication, default retries, model identifiers, event types, rate limits, storage defaults, and pricing can change. This course teaches stable integration boundaries and fixes an auditable contract baseline for three providers. Real integrations must still follow the pinned official documentation, SDK version, machine schema, and live integration tests.

## Course overview

LLM API integration brings prompts, context, and tool calls into running software. An introductory example often consists of one request, while a production system must also handle authentication, layered timeouts, a single retry budget, rate limits, structured outputs, in-stream failures, usage, logs, privacy, and provider differences. This course practices at two layers: first, a provider-neutral offline client contract teaches reliability responsibilities; then it separately parses the current Reference/SDK event projections and continuation contracts for OpenAI Responses, Anthropic Messages, and Gemini Interactions v1. Canonical events belong only to the first layer. The second layer does not force the providers' identity, terminal-state, storage, or replay semantics into a single abstraction, and it does not present offline fixtures as real SSE bytes or live conformance.

## Place in the overall learning path

This course is the engineering outlet for LLM application fundamentals. [[modern-llm-capabilities-and-model-selection/00-index|Modern LLM Capabilities and Model Selection]] provides candidate and task-level acceptance contracts; [[prompt-engineering/00-index|Prompt Engineering]] provides task and output contracts; [[context-engineering/00-index|Context Engineering]] provides evidence and state. This course owns reliable transport, parsing, observability, and error control. Tool Calling, RAG, agent frameworks, and LLMOps all depend on these foundations.

## Learning goals

- Build a minimal Python environment with `venv + pip` in Windows 11 / PowerShell 7, and read secrets safely.
- Understand the responsibility boundary among HTTP, official SDKs, and application adapters.
- Construct version-traceable messages, model configuration, and request metadata.
- Correctly handle structured outputs, SSE streaming events, refusals, truncation, and mid-stream errors.
- Design bounded, jittered retries for temporary failures such as timeouts, 429s, connection failures, and 5xxs; do not retry permanent errors.
- Record request IDs, prompt versions, usage, latency, and outcome states while protecting sensitive content.
- Use a stable `operation_id` to correlate attempts for one business operation, and separate model generation from external side effects.
- Explicitly reject provider features that cannot be mapped equivalently through a capability check.
- Handle Responses Items/calls, Messages blocks/tool-use, and Interactions steps/interactions separately for identity and terminal state; do not infer associations from array position.
- Distinguish stateful handles, stateless replay, provider storage/retention, owned logs, and durable business state; do not mistake `store=false` for end-to-end non-retention.
- Distinguish Platform API keys, workload short-lived tokens, and ChatGPT/Codex OAuth; do not conflate identically named models, authentication, actual backends, and agent runtimes.
- Understand the respective proof boundaries of fixture contract tests, SDK integration tests, live model evaluation, and production audit.

## Prerequisites

- Basic Python functions, classes, exceptions, and JSON.
- Basic HTTP request/response, status-code, and environment-variable concepts.
- Prompt and context engineering are helpful prerequisites, but can be filled in while learning.

## Recommended order

1. [[llm-api-integration/01-environment-dependencies-and-secret-management|Environment, Dependencies, and Secret Management]]: build a reproducible local environment without exposing secrets.
2. [[llm-api-integration/02-http-sdks-and-request-lifecycle|HTTP, SDKs, and the Request Lifecycle]]: understand the layers a call actually passes through.
3. [[llm-api-integration/03-messages-configuration-and-version-awareness|Messages, Configuration, and Version Awareness]]: design a provider-neutral request contract.
4. [[llm-api-integration/04-structured-output-and-streaming-responses|Structured Output and Streaming Responses]]: parse complete and incremental results correctly.
5. [[llm-api-integration/05-timeouts-errors-rate-limiting-and-retries|Timeouts, Errors, Rate Limits, and Retries]]: apply controlled retries only to recoverable errors.
6. [[llm-api-integration/06-usage-observability-and-provider-adapters|Usage, Observability, and Provider Adapters]]: make requests traceable, comparable, and replaceable.
7. [[llm-api-integration/07-project-reliable-client-and-self-tests|Reliable Client Project and Self-Tests]]: run unit tests with a mock transport.
8. [[llm-api-integration/08-project-provider-contract-tests|Provider Contract Tests]]: parse the current streaming tool-call contracts of three providers and construct correct continuations.
9. [[llm-api-integration/09-common-openai-responses-api-patterns|Common OpenAI Responses API Patterns]]: move from a minimal request to multi-turn state, streaming, structured output, tools, retrieval, and image input.
10. [[llm-api-integration/10-openai-platform-api-keys-and-codex-oauth-authentication-routing-and-runtime|OpenAI Platform API Keys and Codex OAuth: Authentication, Routing, and Runtime]]: distinguish Platform, WIF, and Codex OAuth, and understand OpenClaw authentication, model routing, and runtime selection.

## Hands-on projects

First complete the [[llm-api-integration/07-project-reliable-client-and-self-tests|reliable client project]]: [[llm-api-integration/examples/reliable_client.py|reliable_client.py]] defines strict request/response contracts, error classification, `Retry-After`, exponential backoff, jitter, dual attempt/deadline limits, and a canonical streaming state machine with event/text resource boundaries. Twenty-two offline tests validate success and failure paths.

Then complete the [[llm-api-integration/08-project-provider-contract-tests|provider contract tests]]: a standard-library implementation separately consumes OpenAI/Gemini typed SSE projections and an Anthropic wire-SSE envelope projection, and releases calls only after a provider terminal state. Five constructors validate stateful/stateless continuation, **caller-validated canonical history**, caller controls, complete result sets, and prior/current storage boundaries. The constructors perform bounded JSON, identity, and required-field checks, but do not turn arbitrary caller history into a provider-authenticated session. Ninety-nine tests cover event drift, interleaving, truncation, errors, replay, official-source host/path attacks, Anthropic fallback-beta fail-closed behavior, and resource limits. The two layers total 121 tests, but still do not replace real SDK/API integration tests.

## Mastery standard

- Explain why an SDK's default retry plus a second wrapping retry can multiply attempts.
- Set boundaries for connection, first byte, whole request, and business deadline rather than waiting indefinitely.
- Distinguish parseable JSON, schema compliance, semantic correctness, and an authorized action.
- Continue handling error events and incomplete termination after streaming HTTP has returned a success status.
- Isolate provider differences behind a stable application interface without pretending that all parameter semantics are identical.
- Locate the configuration and failure reason for a request without recording raw sensitive content.
- Run the 22 reliable-client tests and 99 provider-contract tests, and demonstrate that unknown exceptions, permanent errors, in-stream failures, error association, resource-limit violations, and missing terminal events are never misclassified as success.
- Explain why SDK automatic retries, provider call IDs, business idempotency keys, and exactly-once are different mechanisms.

## Relationship to other knowledge bases

- [[modern-llm-capabilities-and-model-selection/00-index|Modern LLM Capabilities and Model Selection]] defines candidate hard gates, multi-trial evaluation, and Pareto decisions; this course provides replaceable, observable adapters and real probe evidence for each candidate.
- Template versions and schemas from [[prompt-engineering/00-index|Prompt Engineering]] should enter request metadata.
- Budgets, sources, and state from [[context-engineering/00-index|Context Engineering]] should be validated before sending.
- [[tool-calling-function-calling/00-index|Tool Calling (including Function Calling)]] must keep incomplete streams and retries separate from real side effects.
- LLMOps manages cross-environment releases and costs, while monitoring manages production alerts; [[ai-safety/00-index|AI Safety]], [[privacy-computing/00-index|Privacy-Preserving Computation]], and [[ai-governance/00-index|AI Governance]] constrain logging, data residency, permissions, and audit.

## Primary references

- [OpenAI: API errors](https://developers.openai.com/api/docs/guides/error-codes) (accessed 2026-07-21)
- [OpenAI: Rate limits](https://developers.openai.com/api/docs/guides/rate-limits) (accessed 2026-07-21)
- [OpenAI: Streaming API responses](https://developers.openai.com/api/docs/guides/streaming-responses) (accessed 2026-07-21)
- [OpenAI: Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) (accessed 2026-07-21)
- [OpenAI: Conversation state](https://developers.openai.com/api/docs/guides/conversation-state) (accessed 2026-07-21)
- [OpenAI: official Python SDK](https://github.com/openai/openai-python) (accessed 2026-07-21)
- [OpenAI: Function calling](https://developers.openai.com/api/docs/guides/function-calling) (accessed 2026-07-21)
- [OpenAI: Responses streaming events](https://developers.openai.com/api/reference/resources/responses/streaming-events) (accessed 2026-07-21; event fields cross-checked against the current API Reference and SDK types)
- [Anthropic: API errors](https://platform.claude.com/docs/en/api/errors) (accessed 2026-07-21)
- [Anthropic: Rate limits](https://platform.claude.com/docs/en/api/rate-limits) (accessed 2026-07-21)
- [Anthropic: Streaming Messages](https://platform.claude.com/docs/en/build-with-claude/streaming) (accessed 2026-07-21)
- [Anthropic: Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls) (accessed 2026-07-21)
- [Anthropic: Fine-grained tool streaming](https://platform.claude.com/docs/en/agents-and-tools/tool-use/fine-grained-tool-streaming) (accessed 2026-07-21)
- [Anthropic: Mid-conversation system messages](https://platform.claude.com/docs/en/build-with-claude/mid-conversation-system-messages) (accessed 2026-07-21)
- [Anthropic: Refusals and fallback](https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback) (accessed 2026-07-21)
- [Anthropic: API and data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention) (accessed 2026-07-21)
- [Google: Troubleshooting guide](https://ai.google.dev/gemini-api/docs/troubleshooting) (accessed 2026-07-21)
- [Google: Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) (accessed 2026-07-21)
- [Google: Gemini Interactions overview](https://ai.google.dev/gemini-api/docs/interactions-overview) (accessed 2026-07-21)
- [Google: Interactions API v1 reference](https://ai.google.dev/api/interactions-api-v1) (accessed 2026-07-21)
- [Google: Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling) (accessed 2026-07-21)
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110)
- [WHATWG: Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
