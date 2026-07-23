---
title: "Usage, Observability, and Provider Adapters"
tags:
  - llm-api
  - observability
  - adapter
aliases:
  - LLM API Observability
source_checked: 2026-07-21
source_baseline:
  - OpenTelemetry GenAI semantic conventions
  - OpenAI API errors and official Python SDK documentation
  - Anthropic Messages usage and API errors documentation
  - Gemini Interactions v1 usage schema
  - Provider state, storage, and data-retention documentation
content_origin: original
content_status: dynamic
lang: en
translation_key: LLM API集成/06-用量、可观测性与供应商适配.md
translation_source_hash: f0f673d5566a77a3675e5ebdc519d8604e04962486185a306e4ef2ef74054dc5
translation_route: zh-CN/LLM-API集成/06-用量、可观测性与供应商适配
translation_default_route: zh-CN/LLM-API集成/06-用量、可观测性与供应商适配
---

# Usage, Observability, and Provider Adapters

## Objectives

Record enough non-sensitive metadata to reproduce and diagnose problems, isolate provider differences with adapters, and compare replacement options through real task evaluation.

## Minimum data for every call

- application `operation_id`, trace/span ID, and server request ID;
- provider-adapter version, actual model identifier, and prompt/schema/context-selector versions;
- start time, first-event latency, total duration, attempt count, and final state;
- provider `usage` fields for input, output, and cache-related usage;
- normalized error categories for parsing, schema, refusal, truncation, rate limiting, and so on;
- business evaluation results or human corrections, but not raw sensitive text by default.

First retain a structured copy of the provider's raw usage, then derive unified metrics. Different providers may define tokens, cache, reasoning, or tool usage differently. Price tables change, so cost estimates need a price version and currency; the provider's final bill is authoritative.

Raw fields should retain their namespace and adapter version, while unified fields state their conversion formula. Leave missing values as `unknown/not_reported`; do not fill them with `0`. OpenTelemetry GenAI semantic conventions can provide cross-system vocabulary, but the current specification moved to a separate repository and its registry still includes development/deprecated attributes. Do not treat field names on a web page as a permanent API. Record the convention version, stability level, and custom extensions in use, and migration-test dashboards and alerts during upgrades.

For the current Gemini Interactions v1, total-usage fields are optional `total_input_tokens`, `total_output_tokens`, and `total_tokens`. Do not copy names from earlier or other API families directly, and do not treat absence as zero. Anthropic Messages and OpenAI Responses should likewise retain each native structure first, then derive unified metrics through a versioned adapter.

## State, storage, retention, and logs are different things

As of 2026-07-21, current defaults across the three families differ, and all can depend on account, feature, and governance configuration:

| API family | Current server-state/retention fact | Integration action |
| --- | --- | --- |
| OpenAI Responses | A Response is stored for 30 days by default and can be disabled with `store:false`; Conversation objects and their Items are not bound by the same 30-day TTL; earlier input tokens on a previous-response chain remain billed | Record Response storage, Conversation lifecycle, and billing separately; ZDR/manual state must retain every needed output Item |
| Anthropic Messages | API prompts/outputs are generally not retained by default, but covered models Fable 5/Mythos 5 currently have a 30-day exception; some stateful features have separate retention; a structured-output schema can be cached for up to 24 hours | Check retention/ZDR by model and feature; do not place PHI, secrets, or user originals in a schema |
| Gemini Interactions v1 | `store=true` by default; free projects retain data for one day, while paid projects can configure 7/14/28/55 days, with 55 days both default and maximum | Decide `store` explicitly for every call, and put retention into data-classification, deletion, and handle-expiry tests |

These are feature/state facts, not complete DPA, legal-retention, or abuse-monitoring promises. Anthropic also currently states that, even with ZDR/HIPAA arrangements, data legally required or automatically flagged by trust-and-safety systems can remain retained; flagged inputs/outputs can be retained for up to two years. Check other providers separately against account contracts and applicable features. Do not infer “absolute zero retention” from a `store` field.

These provider contracts also do not cover your reverse proxy, APM, queue, object storage, crash dump, SDK debug log, or data warehouse. Even if a request has `store:false`, your logging path may retain its complete payload. Conversely, provider retention cannot replace an application's durable conversation/execution ledger. Before launch, create a data-flow inventory: where every body, schema, tool result, trace, and usage copy goes, who can access it, how long it is retained, and how it is deleted.

## Adapter responsibilities

```text
ApplicationRequest
  -> Capability check
  -> ProviderAdapter.map_request()
  -> Official SDK / HTTP
  -> ProviderAdapter.map_events_or_response()
  -> ApplicationResponse
```

An adapter should declare capabilities explicitly: schema, streaming, tools, images, and so forth. If it cannot map one equivalently, return `unsupported_capability` rather than delete a field and continue. Retain raw errors and completion reasons for troubleshooting, while exposing a bounded, stable internal enumeration to higher layers.

## Observability without disclosure

Use an allowlist for logs: record length, hashes, versions, and categories by default rather than full prompts, context, tool arguments, or authentication headers. Choose sampling and retention by risk, and limit access. Aggregated metrics must not contain high-cardinality fields such as complete user IDs; use controlled irreversible identifiers for necessary correlation.

Trace, log, and metric have different responsibilities: traces correlate one business operation and its attempts, logs capture discrete states and structured errors, and metrics aggregate latency, usage, and failure rate. A server request ID belongs in controlled logs or span attributes, not a low-cardinality metric label.

Logs should distinguish “requested settings” from “actual results”: requested model/configuration versus response-reported model, requested `store` versus whether prior state was retrievable, planned retry versus actual attempts, and estimated cost versus final bill must all be saved separately. That makes routing, fallback, alias drift, and handle expiry explainable rather than leaving one seemingly unified `model` field.

## Comparing providers or models

Fix the task evaluation set, prompt contract, and context. Compare quality slices, parse rate, refusal, latency percentiles, usage, cost, and failure rate. A feature table can tell you only what a provider claims to support; it cannot prove business equivalence. Validate through shadow or low-volume traffic before switching production.

## Exercise and self-check

Design a log schema for one call and mark each field “required,” “optional,” or “prohibited.” Design a capability matrix for two adapters. Self-check: can average latency and unit price per token alone decide a migration? What task-level evidence is still missing?

## Mastery checklist

- [ ] All attempts for one operation can be correlated through operation/trace ID, while each server request ID is retained separately.
- [ ] Raw usage, unified metrics, conversion formulas, adapter version, and price version are traceable.
- [ ] Missing fields remain unknown; unreported usage, cache, or cost is never written as zero.
- [ ] Logs use an allowlist and do not retain prompts, context, tool arguments, authentication headers, or personal information by default.
- [ ] An adapter capability mismatch fails explicitly, and unknown errors/terminal states retain their raw type.
- [ ] Provider storage, product retention, owned-log retention, and durable business state are modeled separately; `store=false` is not treated as “no retention anywhere.”
- [ ] The OTel GenAI convention has a pinned version and stability level; upgrades validate attribute migration rather than copying a volatile registry.
- [ ] Provider comparison uses the same task set and quality/safety gates, and observes latency percentiles and failure rate.

## Next step

First continue to [[llm-api-integration/07-project-reliable-client-and-self-tests|Reliable Client Project and Self-Tests]], then complete [[llm-api-integration/08-project-provider-contract-tests|Provider Contract Tests]]. The latter turns the capability matrix into separate state machines and continuation contracts for OpenAI Responses, Anthropic Messages, and Gemini Interactions v1 rather than merely comparing field names.

## References

- [OpenTelemetry: GenAI semantic-convention attribute registry](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/) (accessed 2026-07-21; fields include development/deprecated states)
- [OpenAI: API errors](https://developers.openai.com/api/docs/guides/error-codes) (accessed 2026-07-21)
- [OpenAI: official Python SDK—Request IDs](https://github.com/openai/openai-python#request-ids) (accessed 2026-07-21)
- [OpenAI: Conversation state](https://developers.openai.com/api/docs/guides/conversation-state) (storage, Conversation, and chain billing; accessed 2026-07-21)
- [Anthropic: API errors](https://platform.claude.com/docs/en/api/errors) (accessed 2026-07-21)
- [Anthropic: Messages API reference](https://platform.claude.com/docs/en/api/messages) (accessed 2026-07-21)
- [Anthropic: API and data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention) (model/feature retention and schema cache; accessed 2026-07-21)
- [Google: Gemini Interactions overview](https://ai.google.dev/gemini-api/docs/interactions-overview) (default storage and retention; accessed 2026-07-21)
- [Google: Interactions API v1 reference](https://ai.google.dev/api/interactions-api-v1) (usage schema; accessed 2026-07-21)
