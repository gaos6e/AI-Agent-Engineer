---
title: "Traces and Privacy Boundaries"
tags:
  - llmops
  - tracing
aliases:
  - LLM Trace
  - LLM Distributed Tracing
source_checked: 2026-07-21
lang: en
translation_key: LLMOps/02-生产工程/04-Trace与隐私边界.md
translation_source_hash: 429ac646c6bacb4528a6d9074599bbf1f1c7792aad96597cec2d7addfca5301e
translation_route: zh-CN/LLMOps/02-生产工程/04-Trace与隐私边界
translation_default_route: zh-CN/LLMOps/02-生产工程/04-Trace与隐私边界
---

# Traces and Privacy Boundaries

## Goal

Split one LLM or agent request into correlated spans to locate latency, retry, tool error, and version regression, while designing content collection, redaction, and retention boundaries.

## Trace, span, and event

- **Trace** — causal chain of an end-to-end task, joined by shared `trace_id`.
- **Span** — one unit of work with start/end, status, attributes, and parent/child relation.
- **Event** — a discrete occurrence in a span, such as “retry attempt two started” or “output policy denied.”

One support-agent Trace can be:

```text
request
├─ assemble_context
│  └─ retrieve_documents
│     └─ rerank
├─ model_call attempt=1
├─ tool_call lookup_ticket
├─ model_call attempt=2
└─ output_policy
```

One 30-second total request record cannot identify whether retrieval, model, tool, or a loop caused the time.

## What each span records

Prefer searchable metadata:

| Span | Suggested metadata | Content not recorded by default |
| --- | --- | --- |
| Request | Release ID, controlled tenant/task-type tag, outcome status | Authorization header, complete user input |
| Retrieval | Snapshot, configuration, hit count, duration | Unredacted full document |
| Model | Provider/model version, parameters, token/cache statistics, request ID | Key, default full prompt/output |
| Tool | Tool/schema version, status, duration, idempotency-key digest | Full parameter, password, returned personal data |
| Policy | Policy version, pass/deny, reason code | Repeating raw content “for convenience” |

Content and metadata need separate switches and retention policy. Debug-content sampling must bound environment, tenant, percentage, access role, and expiry rather than leaving “record everything” on indefinitely.

To join an offline gate and online window, a Trace or controlled audit log can record `release_id`, release-manifest SHA-256, and the candidate gate's **full** SHA-256. A short fingerprint is only human-readable comparison. Full digest, Trace ID, request ID, and user ID must not be Metric labels: they create high cardinality, and the latter two enlarge privacy risk. A digest also must not excuse content collection; raw text still obeys minimization, authorization, and retention boundaries.

## Context propagation

Distributed systems pass Trace context from gateway to retrieval, model proxy, and tool service. W3C Trace Context defines an HTTP propagation format; use mature libraries to generate and validate it, never manually splice IDs.

An externally supplied Trace field is not a trusted business identity. A `trace_id` cannot replace user authentication, and a requester must not force sensitive recording by forging sampling flags.

## Sampling and cardinality

Full tracing can be too expensive. Common strategies include probability sampling, tail sampling that retains errors/slow requests, and higher sampling for high-risk tasks. Sampling must be visible; otherwise “not sampled” can be confused with “did not happen.”

Do not make `user_id`, a full prompt, or document ID a Metric label. Investigate concrete requests with a Trace and population trends with controlled low-cardinality Metrics.

## Decision order for sensitive content

1. **Necessity** — can the problem be diagnosed without raw content? If yes, do not collect it.
2. **Minimization** — collect only necessary fields, length, or summary.
3. **Redaction** — process before it leaves the application trust boundary, and test redaction-failure paths.
4. **Isolation** — apply access control by environment and tenant.
5. **Retention and deletion** — set expiry, deletion, and audit evidence.

Provider retention and region capabilities vary by endpoint, feature, and customer configuration. State only what the current contract and official control surface supports; one overview cannot mean every API has zero retention.

## Exercise and self-check

For an agent calling tools to read customer records and create tickets, draw a span tree and list span metadata, content not to record, and retention. Why does one `request_id` not replace parent/child Trace structure? Why must a Metric label not contain user ID? If sampling retains only errors, can it estimate latency distribution for all successful requests?

## Next step

Trace connects diagnosis and lineage; it is not “store all content.” In [[llmops/foundations-and-lifecycle/05-offline-evaluation-gates-and-regression-suites|Offline Evaluation Gates and Regression Suites]], turn real Trace failures into candidates for human triage before a regression-suite update. Use the Evaluation Framework's offline-to-online evidence handoff only after that course exists.

## References

- [OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/) — accessed 2026-07-21.
- [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai) — accessed 2026-07-21; pin actual revision/schema URL during integration.
- [W3C Trace Context](https://www.w3.org/TR/trace-context/) — W3C Recommendation; accessed 2026-07-21.
- [OpenAI Data controls](https://developers.openai.com/api/docs/guides/your-data) — accessed 2026-07-21; retention varies by endpoint, feature, and account eligibility.
