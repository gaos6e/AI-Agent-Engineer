---
title: "Alert Design and On-Call Operations"
tags:
  - observability
  - alerting
aliases:
  - Alerts for AI Systems
source_checked: 2026-07-14
lang: en
translation_key: 运行监控/02-生产监控/04-告警设计与值班运行.md
translation_source_hash: e1616e038f53bd3ccfa277f4e21b63d0da6feed1ddf98cfcbcb6c96888dfd024
translation_route: zh-CN/运行监控/02-生产监控/04-告警设计与值班运行
translation_default_route: zh-CN/运行监控/02-生产监控/04-告警设计与值班运行
---

# Alert Design and On-Call Operations

## Goal

Turn runtime signals into a small set of actionable alerts. For each alert, define user impact, urgency, owner, runbook, suppression, recovery, and audit process.

## An alert is not every anomaly-detector output

A good real-time page meets all four conditions:

1. User or business impact is occurring or imminent.
2. Someone can take action now.
3. Waiting until business hours would materially increase the loss.
4. There is a clear owner and an initial runbook.

Capacity trends, slow quality decline, and cost-optimization opportunities that do not need immediate response can become tickets or scheduled reviews. They should not wake someone at night.

## Prefer symptom alerts

A symptom alert answers “what impact are users experiencing?” A root-cause signal helps diagnose “why might it be happening?” For example:

- Page: the interactive-request error budget is burning rapidly.
- Diagnostic panel: provider throttling, a tool timeout, or queue saturation.

If top-level user latency remains normal, a briefly slow internal component generally should not wake another team too. Serious but non-user-visible consequences—data leakage, security overreach, or uncontrolled cost—can still need urgent alerts; govern those under separate risk policy.

## The full contract for one alert

| Field | Question it must answer |
| --- | --- |
| Name and meaning | What user symptom is occurring? |
| Severity | When must it be addressed, and should it wake someone? |
| Condition and duration | How are transient spikes suppressed, and which definition version applies? |
| Scope | Which environment, release, task, or slice is affected? |
| Owner | Who responds first and how is it escalated? |
| Runbook | What should the first five minutes inspect, and what is safe to do? |
| Dashboard/trace | Which view and example trace support drill-down? |
| Suppression/aggregation | Which downstream alerts should the root event suppress? |
| Recovery condition | When is it over, and is a human check required? |
| Verification | How are the rule and notification path tested or exercised? |

An alert message should show current observation, objective/budget, window, impact scope, and direct links—not “metric abnormal, please handle.”

## Debouncing, grouping, inhibition, and silences

- **Duration/debouncing** — trigger only after a signal persists long enough to avoid brief spikes; a severe safety event may not be able to wait.
- **Grouping** — combine multiple instances of one incident while retaining scope information.
- **Inhibition** — when a known root event fires, temporarily avoid notifying expected downstream symptoms.
- **Silence** — suppress notifications for a controlled maintenance window; it needs scope, reason, owner, and expiry.

Do not “solve” noise by permanently broadening a silence. Repair noisy alerts, downgrade them to tickets, or delete them. Do not train on-call staff to ignore alerts.

When using Prometheus Alertmanager, keep its product semantics distinct: **grouping** combines related alerts into one notification; **routing** distributes by labels and receiver policy; **deduplication** avoids repeated notifications; **inhibition** suppresses matching alerts while another alert is active; and **silence** blocks notifications by matchers and time range. These concepts help design an alerting system, but configuration fields, defaults, and version support must be checked for the deployed version. This lesson is not copy-paste configuration.

## AI-system-specific alert tradeoffs

- With delayed quality labels, use fast proxies for early warning but state that they are not ground truth.
- A low-traffic, high-risk task cannot rely only on an overall rate; a single high-loss event may escalate directly.
- Drift usually creates an investigation or ticket first. It should not automatically trigger retraining or release.
- Cost alerts examine total spend, per-task spend, retries/loops, and quality together, preventing “cost optimization by stopping service” from being accepted as an improvement.

## Monitor the monitoring system too

Notification paths, Collectors, query backends, and rule evaluators can fail. Build end-to-end synthetic heartbeats, collection freshness, drop counters, and notification exercises. Monitoring only whether every process is running can miss “all components are alive, but no alert reaches a person.”

## Exercise and self-check

For an online RAG Agent, write three alerts: fast error-budget burn, high-risk unauthorized tool invocation, and a sharp rise in cost per successful task. Complete the contract table for each. Answer:

1. Why may a rise in internal model latency not require a page while the user SLI is healthy?
2. Why must a drift alert not connect directly to “retrain and deploy automatically”?
3. How do you prove the chain from rule evaluation to an on-call person works?

## Summary and next step

An alert is a human–system interface that needs versioning, tests, and operations. [[runtime-monitoring/production-monitoring/05-dashboards-and-diagnostic-views|Dashboards and Diagnostic Views]] gives on-call staff a path from symptom to evidence.

## References

- [Prometheus Alerting practices](https://prometheus.io/docs/practices/alerting/) — checked 2026-07-14; symptom orientation, actionability, and monitoring the monitoring system.
- [Prometheus Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/) — checked 2026-07-14; grouping, routing, deduplication, inhibition, and silences.
- [Prometheus Alerting overview](https://prometheus.io/docs/alerting/latest/overview/) — checked 2026-07-14; recheck configuration syntax and version capability for the deployed system.
- [Google SRE: Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) — checked 2026-07-14.

