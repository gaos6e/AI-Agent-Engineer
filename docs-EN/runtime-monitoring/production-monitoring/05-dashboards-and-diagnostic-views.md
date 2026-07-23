---
title: "Dashboards and Diagnostic Views"
tags:
  - observability
  - dashboard
aliases:
  - AI Runtime Dashboard
source_checked: 2026-07-14
lang: en
translation_key: 运行监控/02-生产监控/05-Dashboard与诊断视图.md
translation_source_hash: 249672e29eed1bb244a0da53ec8cade73d02e0c9c9c3b46d11899357cba71bb7
translation_route: zh-CN/运行监控/02-生产监控/05-Dashboard与诊断视图
translation_default_route: zh-CN/运行监控/02-生产监控/05-Dashboard与诊断视图
---

# Dashboards and Diagnostic Views

## Goal

Design a dashboard that rapidly answers “are users affected, when did it start, which versions/tasks are affected, and where do I drill down?” without creating false conclusions through dual axes, averages, or incomplete data.

## Define audience and questions first

An incident dashboard for on-call staff should not be identical to a weekly quality/cost dashboard for a product owner. Place these facts at the top of every dashboard:

- audience, purpose, and owner;
- environment, time zone, default window, and data freshness;
- SLI/metric definition version;
- which decisions this dashboard can support and which it cannot;
- entry points for runbooks, release records, alerts, and trace search.

## A four-layer structure

### 1. User-impact overview

- Availability and latency SLIs, SLOs, and error-budget burn.
- Task quality, label coverage/freshness, safety events, and per-task cost.
- Current traffic, change from baseline, and missing-data alerts.

### 2. Scope breakdown

Break down by environment, release, task type, business-meaningful risk slice, provider/model, and outcome type. A breakdown is not unlimited labels: use logs/traces to query user IDs, request IDs, and free text.

### 3. Diagnostic signals

- Latency/errors/saturation for retrieval, model, tool, gateway, queue, and observability pipeline.
- RED (Rate, Errors, Duration) for services and USE (Utilization, Saturation, Errors) for resources.
- Token, cache, retry, Agent-step, and cost breakdowns.
- Label-return delay, trace completeness, and log-drop volume.

### 4. Evidence drill-down

Move from an anomalous point to a filtered trace list, then to an individual span and related structured logs. Preserve the current time window, release, and task filter across the drill-down so an on-call responder does not have to reconstruct conditions on a new page.

## Release and definition annotations

Annotate the timeline with application/model/prompt/retrieval/tool releases, gateway-routing or safety-policy changes, data-definition changes, provider announcements, and business events. An annotation is a correlation clue, not causal proof. “The metric changed after a release” still needs comparison of release slices, traces, and coincident external changes.

## Display incomplete data honestly

Show:

- last successful collection time and end-to-end data delay;
- record volume sent, received, dropped, and sampled;
- label coverage, safety-check coverage, and trace completeness;
- low-sample-size or no-data state;
- definition version and boundaries where historical curves are not comparable.

Do not draw no data as zero. “Safety events = 0” and “safety collection is interrupted” need completely different visual meaning and actions.

## Chart choices and misleading patterns

- Show latency with p50/p95/p99 or a histogram, not an average alone.
- Show numerator/denominator or sample size with a ratio.
- Compare releases over the same window, task mix, and definition.
- Separate cost and traffic: total cost, per-request cost, and per-successful-task cost may all be needed.
- Avoid two independent Y axes that manufacture a visual correlation.
- Use consistent units and an explicit time zone; do not name a metric “score” without semantics.

## Exercise and self-check

Draw a one-page incident-dashboard wireframe for a Tool-Calling Agent. It must include user SLI, quality/safety/cost, release annotations, scope breakdown, observability completeness, and trace drill-down. Answer:

1. Why does p95 reveal tail issues better than average latency alone?
2. Why must data interruption not appear as zero?
3. Why does a release annotation appearing with a metric anomaly not automatically prove the release is the root cause?

## Summary and next step

A good dashboard is a decision and diagnostic path, not a wall of metrics. When a distribution change appears, apply the evidence boundaries in [[runtime-monitoring/production-monitoring/06-drift-feedback-and-label-latency|Drift, Feedback, and Label Latency]].

## References

- [Google SRE: Service Level Objectives](https://sre.google/sre-book/service-level-objectives/) — checked 2026-07-14; percentiles, user perspective, and metric definitions.
- [OpenTelemetry Observability primer](https://opentelemetry.io/docs/concepts/observability-primer/) — checked 2026-07-14.
- [Prometheus Metric and label naming](https://prometheus.io/docs/practices/naming/) — checked 2026-07-14; recheck current conventions if using Prometheus.
- [Prometheus Histograms and summaries](https://prometheus.io/docs/practices/histograms/) — checked 2026-07-14; aggregation and version capability differ among histogram types.

