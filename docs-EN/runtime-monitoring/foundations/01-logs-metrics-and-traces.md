---
title: "Logs, Metrics, and Traces"
tags:
  - observability
  - telemetry
aliases:
  - The Three Signals of Observability
source_checked: 2026-07-14
lang: en
translation_key: 运行监控/01-可观测性基础/01-Logs、Metrics与Traces.md
translation_source_hash: c472e331ec16fcbfeb7e2ca86ae9362534c003bd54fcef2aacd07beb5f174fcb
translation_route: zh-CN/运行监控/01-可观测性基础/01-Logs、Metrics与Traces
translation_default_route: zh-CN/运行监控/01-可观测性基础/01-Logs、Metrics与Traces
---

# Logs, Metrics, and Traces

## Goal

Understand the shape of logs, metrics, and traces; the questions each answers; their cost tradeoffs; and the correlation keys that let you drill from an aggregate trend into one request.

## Intuition for the three signals

| Signal | Data shape | Questions it answers well | Main risk |
| --- | --- | --- | --- |
| Log | Discrete record with time and metadata | “What happened then? What was the concrete error?” | Volume, sensitive content, and free text that is hard to aggregate |
| Metric | Numeric series aggregated over time | “How are error rate, p95 latency, or cost changing?” | Aggregation loses detail; high-cardinality labels cost money |
| Trace | End-to-end path made of parent/child spans | “Where did time go? Which retry or tool failed?” | Sampling bias, broken propagation, and content exposure |

They are not three isolated data silos. A request's structured log can carry `trace_id` and `span_id`; a metric exemplar or dashboard drill-down can point to a related trace; and all three should share stable resource semantics such as service, environment, and release.

## From free text to structured logs

A log that is difficult to query:

```text
something went wrong for user 93827
```

A more actionable structure:

```json
{
  "timestamp": "2026-07-13T08:30:10Z",
  "severity": "ERROR",
  "service": "agent-gateway",
  "environment": "production",
  "release_id": "agent-2026-07-13.1",
  "trace_id": "opaque-trace-id",
  "event_name": "tool_timeout",
  "tool_name": "lookup_ticket",
  "error_type": "deadline_exceeded"
}
```

This is still strict JSON. `timestamp`, `service`, `environment`, and `release_id` establish where and which version produced the event; `trace_id` only correlates signals; `event_name`, `tool_name`, and `error_type` let alerts and investigations aggregate by structure; and `severity` describes event severity only. It cannot replace an SLO or a judgment about business quality.

This is a teaching example. Production logs should use the platform's time and trace-ID formats and must not record secrets, Authorization headers, complete personal profiles, or unnecessary prompts. If user correlation is necessary, use a controlled surrogate identifier with a retention period that cannot serve as an authentication credential.

## Metric types and units

Start with:

- **Counter** — an event total that only increases, such as requests, errors, or tokens; normally query a rate or interval increase.
- **Gauge** — a current value that can rise and fall, such as queue length, in-flight requests, or snapshot age.
- **Histogram** — bucketed observations of a distribution, useful for latency, output length, or cost; choose bucket boundaries around SLOs and diagnostic needs.

A metric name should include its unit or the data model should make the unit unambiguous. `latency=4` is unsafe because it might mean seconds, milliseconds, or minutes.

## Start investigations with RED, USE, and the golden signals

These three methods help beginners avoid overlooking important symptoms, but they are inspection frameworks—not SLIs or root-cause engines:

- **RED** applies to service requests: Rate, Errors, Duration.
- **USE** applies to each resource: Utilization, Saturation/queueing, Errors.
- Google SRE's **four golden signals** are Latency, Traffic, Errors, and Saturation, a useful organization around user impact and capacity symptoms.

For example, start an Agent API investigation with request rate, error rate, and latency distribution. If latency rises, use USE to inspect CPU utilization, thread/queue saturation, and resource errors. High CPU is only a candidate explanation; validate it with traces and change evidence.

## Histograms and percentiles

p95 means about 95% of observations do not exceed that value. It is not the average of the slowest 5%, and an overall p95 cannot be obtained by averaging per-instance p95 values. Tail latency requires enough distribution information: a histogram accumulates counts in preselected buckets, whose boundaries should fit the SLO threshold and diagnostic scale. Coarse buckets can make the estimate misleading.

Prometheus documentation distinguishes classic Histograms, native Histograms, and Summaries: classic Histograms can aggregate buckets server-side, while Summaries precompute quantiles client-side and have limited cross-instance aggregation. Prometheus currently recommends considering native Histograms where feasible. That is current Prometheus guidance, not a universal monitoring API. Recheck support, migration cost, and storage cost for the deployed version before choosing.

## Labels and cardinality

Metric labels group a finite set of categories, such as `environment`, `release`, `result`, and a controlled `task_type`. Each unique combination can create a new time series, so do not put user IDs, request IDs, full prompts, or unbounded URLs in labels. Keep those high-cardinality details in controlled traces or logs and drill down through an ID.

## Trace completeness

A span should capture its operation name, start/end, status, parent span, important version, and controlled business attributes. Standard propagation is needed when context crosses HTTP, message queues, or background jobs. An LLM/Agent path should at least distinguish retrieval, model, tool, retry, and output-policy spans.

After sampling, a missing trace can mean it was not collected—not that the request did not occur. Monitor the sampling strategy, sampling rate, and propagation-loss rate as well.

## A practical diagnostic path

1. A dashboard shows p95 latency rising for one release.
2. Filter by release, task type, and time window; rule out a changed aggregation definition.
3. Choose slow traces from the latency distribution.
4. Compare retrieval, model, tool, and retry spans.
5. Use `trace_id` to find related structured logs and their concrete error type.
6. Form a testable hypothesis rather than declaring the correlated component the root cause.

## Exercise and self-check

Break “the Agent answered too slowly” into at least five spans. Give each span two metadata fields, then list two metrics and two logs. Answer:

1. Why are metrics excellent for trends but insufficient to explain one request?
2. Why must a request ID not be a metric label?
3. Why is business semantics and version data still needed after automatic instrumentation?

## Summary and next step

The three signals work together to answer “is there a problem, who is affected, and why?” Continue with [[runtime-monitoring/foundations/02-instrumentation-collector-and-correlation|Instrumentation, Collectors, and Correlation]] to connect them reliably across processes and govern their use.

## References

- [OpenTelemetry Logs](https://opentelemetry.io/docs/concepts/signals/logs/) — checked 2026-07-14; language-SDK support changes over time.
- [OpenTelemetry Metrics](https://opentelemetry.io/docs/concepts/signals/metrics/) — checked 2026-07-14.
- [OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/) — checked 2026-07-14.
- [Prometheus Histograms and summaries](https://prometheus.io/docs/practices/histograms/) — checked 2026-07-14; recheck native-Histogram support for the deployed version.
- [Tom Wilkie: The RED Method](https://grafana.com/blog/2018/08/02/the-red-method-how-to-instrument-your-services/) — original method explanation, checked 2026-07-14.
- [Brendan Gregg: The USE Method](https://www.brendangregg.com/usemethod.html) — original method explanation, checked 2026-07-14.
- [Google SRE: Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) — checked 2026-07-14.
- [W3C Trace Context](https://www.w3.org/TR/trace-context/) — W3C Recommendation, checked 2026-07-14.

