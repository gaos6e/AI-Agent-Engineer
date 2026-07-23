---
title: "Instrumentation, Collectors, and Correlation"
tags:
  - observability
  - opentelemetry
  - tracing
aliases:
  - Telemetry Instrumentation
  - Context Propagation and Collectors
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
source_baseline: "OpenTelemetry and W3C Trace Context primary materials checked
  through 2026-07-22; the separate GenAI semantic-convention repository,
  schema-version boundary, and component-stability boundary were reviewed."
lang: en
translation_key: 运行监控/01-可观测性基础/02-仪器化、Collector与关联.md
translation_source_hash: 048a0447bbb5a81245c239ab537af3823e2933c3dde4f276f396e57e3e10c275
translation_route: zh-CN/运行监控/01-可观测性基础/02-仪器化、Collector与关联
translation_default_route: zh-CN/运行监控/01-可观测性基础/02-仪器化、Collector与关联
---

# Instrumentation, Collectors, and Correlation

## Goal

Turn “the application is running” into correlated, governable telemetry: understand the boundary between automatic and manual instrumentation, propagate trace context correctly, design a Collector pipeline, and make explicit sampling, cardinality, cost, and privacy tradeoffs.

## What instrumentation actually does

**Instrumentation** produces telemetry such as logs, metrics, and spans at program boundaries or business steps. It is not complete merely because an agent is installed; it is a three-layer contract:

1. **Generate** — the application, SDK, or automatic probe records data.
2. **Correlate** — a request retains shared context across HTTP, message queues, background jobs, and tool calls.
3. **Process and export** — a Collector receives, transforms, filters, batches, and sends the data to a backend.

Automatic instrumentation is usually good at HTTP, database, and common-framework boundaries. Manual instrumentation adds business semantics that automatic tools do not know, such as `task_type`, a retrieval phase, human-handoff outcome, or a controlled tool name. Do not reproduce code line-by-line with manual spans or treat prompts, national identity numbers, or secrets as convenient attributes.

## Establish a stable resource and field contract first

Every telemetry record should answer “which system, environment, and release produced this?” Start with a finite set of stable resource fields:

| Field | Example | Purpose |
| --- | --- | --- |
| `service.name` | `agent-gateway` | Distinguish services |
| `deployment.environment.name` | `production` | Distinguish environments |
| `service.version` or internal `release_id` | `2026.07.14.1` | Correlate a release |
| `trace_id`, `span_id` | Opaque IDs | Correlate one invocation path |
| Controlled business attribute | `task_type=ticket_triage` | Diagnose a finite category |

Field names, units, enumerations, and missing-value semantics belong in a team **telemetry contract** and should be tested. OpenTelemetry (OTel) semantic-convention stability is declared separately by component and signal; “it belongs to OTel” does not mean all of it is stable. As of 2026-07-21, the core semantic-conventions page was 1.43.0 and GenAI conventions had moved to a separate repository. Pin the actual repository revision or release, record a schema URL or equivalent contract version, and use contract tests to detect field changes for the signals and components you actually use. Do not treat the core-page version as the current GenAI field version or invent fields from memory.

## Propagate correlation with W3C Trace Context

W3C Trace Context defines the `traceparent` and `tracestate` HTTP headers. A common version-`00` `traceparent` has this shape:

```text
00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

In order, it contains the version, a 32-hex-character trace ID, a 16-hex-character parent span ID, and flags. All-zero IDs are invalid. Leave parsing, new-span-ID generation, and sampling-flag processing to a compliant library instead of assembling strings by hand.

Follow four propagation principles:

1. Inject context into HTTP downstream calls and extract it from upstream calls; put it in supported message properties for message systems.
2. When an asynchronous task leaves the original request lifecycle, explicitly decide whether it continues the trace, creates a link, or starts a new trace correlated by a controlled business ID.
3. Structured logs may record the current `trace_id` and `span_id`. Metrics use only finite labels and, when needed, correlate a trace through an exemplar or drill-down link.
4. `traceparent` is a propagation identifier, not an authentication or authorization credential. Context arriving from an untrusted boundary still needs access control, and uncontrolled `tracestate` must not create privacy or resource risks.

## Collector pipeline

An OTel Collector's basic pipeline is:

```text
Application/probe → Receiver → Processor(s) → Exporter → telemetry backend
```

- A **Receiver** accepts OTLP or another protocol.
- A **Processor** batches, limits memory, filters attributes, samples, and performs related work; its order changes the outcome.
- An **Exporter** sends telemetry to the target backend.
- A **Connector** connects one pipeline's output to another pipeline.
- An **Extension** provides health checks, authentication, or other capabilities outside the telemetry data plane.

A Collector may run close to an application as an agent or centrally as a shared gateway. Choose the topology from network boundaries, failure domains, resource cost, and sensitive-data location. Even a minimal design must monitor the Collector itself: accepted, refused, sent, failed, queue length, drops, configuration version, and data freshness. Also keep **Collector export age** distinct from the **age of the latest business event relative to the observation endpoint**. Fresh exports do not show that upstream business traffic is still producing events. Otherwise, a healthy dashboard can simply be exporting a stale stream successfully.

## Sampling, cardinality, and cost

Keeping every trace is usually expensive. Two common approaches are:

- **Head sampling** — decide when a trace begins. Cost is controlled, but the final failure is not yet known.
- **Tail sampling** — decide after observing more spans. It can retain errors or very slow traces more effectively, but requires buffering, state, and capacity planning.

Sampling changes which individual cases are visible. Record a strategy version and estimated coverage; preferentially retain errors, high-risk operations, and very slow calls; and use metrics independent of trace sampling for population rates. Trace sampling also does not solve metric high cardinality: `user_id`, `request_id`, arbitrary URLs, full prompts, a full release-manifest SHA-256, and a full candidate-gate SHA-256 still must not be metric labels. The latter two may live in controlled traces or audit logs for evidence handoff.

Start cost governance with a budget table: event volume per signal, record size, retention period, indexed fields, sampling rate, query need, and owner. Retain a field long term only when it supports a user objective, release decision, or incident response.

## Privacy, security, and retention

Generative-AI content often includes personal data, business information, or over-privileged instructions. Safer defaults are:

- Content capture is off by default or explicitly opt-in; collect only the smallest diagnostic field set.
- Remove, mask, or apply controlled hashes before data crosses a trust boundary, without presenting an irreversible hash as a guarantee of anonymity.
- Apply least privilege, encryption in transit and at rest, audit, retention, and verifiable deletion to telemetry storage.
- Make collection, redaction, and deletion failures observable events rather than silently ignoring them.
- Use synthetic teaching IDs and placeholder content to test the pipeline; never place real credentials in examples.

## Design an Agent request path step by step

Assume one request retrieves information, calls a tool, and produces an answer:

1. The gateway creates a root span with service, release, controlled task type, and technical outcome.
2. Retrieval, reranking, model invocation, tool invocation, and policy checks create child spans.
3. Context propagates to downstream HTTP/message handlers, and logs record the current trace correlation keys.
4. Metrics count request rate, error rate, latency distribution, tool failures, quality coverage, and cost without a per-request ID.
5. The Collector first limits memory and batches, then filters/redacts fields, and finally exports.
6. Collector metrics, propagation completeness, and sample coverage enter a separate health dashboard.

If model spans exist but tool spans frequently become new root traces, first inspect whether context is being lost at a thread, task-queue, or SDK boundary rather than guessing a tool-performance problem.

## Exercises

1. Draw a span tree for “read a ticket → retrieve knowledge → call an inventory tool → produce a human-reviewable draft,” marking resource, span, and log attributes.
2. Design a Collector pipeline and state each component's input, output, failure behavior, and self-monitoring signals. Explain why redaction must occur before export.
3. Decide whether each candidate can be a metric label: `environment`, `request_id`, `release_id`, `user_email`, controlled `task_type`, full prompt. Explain each decision.
4. Design head- and tail-sampling policies. State which failures each can miss and how metrics estimate the coverage gap.

## Self-check

- [ ] I can explain why automatic instrumentation cannot replace business semantics.
- [ ] I can explain that `traceparent` propagation, authentication, and sampling are different things.
- [ ] I can draw a Receiver–Processor–Exporter pipeline and identify its self-monitoring signals.
- [ ] I can distinguish trace-sampling problems from metric-cardinality problems.
- [ ] I can define capture controls, redaction, permissions, and retention for generative-AI content.
- [ ] I can verify the stability of a target semantic convention and control change with version pinning and contract tests.

## Summary and next step

Instrumentation turns code paths into semantic evidence, propagation preserves that evidence across boundaries, and a Collector processes and exports it governably. Continue with [[runtime-monitoring/foundations/03-slis-slos-and-error-budgets|SLIs, SLOs, and Error Budgets]] to decide which user behavior should become an objective rather than alerting on every field you can collect.

## References

- [OpenTelemetry Collector Architecture](https://opentelemetry.io/docs/collector/architecture/) — checked 2026-07-21.
- [OpenTelemetry Collector components](https://opentelemetry.io/docs/collector/components/) — checked 2026-07-21.
- [OpenTelemetry Collector internal telemetry](https://opentelemetry.io/docs/collector/internal-telemetry/) — checked 2026-07-21.
- [OpenTelemetry Sampling](https://opentelemetry.io/docs/concepts/sampling/) — checked 2026-07-21.
- [OpenTelemetry Handling sensitive data](https://opentelemetry.io/docs/security/handling-sensitive-data/) — checked 2026-07-21.
- [OpenTelemetry Versioning and stability](https://opentelemetry.io/docs/specs/otel/versioning-and-stability/) — checked 2026-07-21; recheck stability for the specific component.
- [OpenTelemetry Generative AI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — checked 2026-07-21; the core page notes that the content moved and the prior location is no longer maintained.
- [OpenTelemetry GenAI semantic conventions repository](https://github.com/open-telemetry/semantic-conventions-genai) — checked 2026-07-21; pin the actual revision/schema URL and verify stability for each component in use.
- [W3C Trace Context](https://www.w3.org/TR/trace-context/) — W3C Recommendation, 2021-11-23; checked 2026-07-21.

