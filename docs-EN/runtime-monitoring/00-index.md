---
title: "Runtime Monitoring Learning Path"
tags:
  - ai-agent-engineer
  - observability
  - learning-path
aliases:
  - Runtime Monitoring
  - AI Application Observability
  - Runtime Monitoring from Zero
ai_learning_stage: 7. Production, Evaluation, and Governance
ai_learning_order: 40
ai_learning_schema: 2
ai_learning_id: runtime-monitoring
ai_learning_domain: production-ops
ai_learning_catalog_order: 4000
ai_learning_hard_prerequisites: []
ai_learning_track_agent_platform_order: 1300
ai_learning_track_agent_platform_kind: core
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
source_baseline: "OpenTelemetry, W3C, Google SRE, Prometheus, and NIST primary
  materials checked through 2026-07-22; the GenAI semantic-convention migration,
  schema-version boundary, and component-stability boundary were reviewed."
lang: en
translation_key: 运行监控/00-目录.md
translation_source_hash: 1dca18ba8f4af792fd5facd64ad638df2f25abe6e760f970e64a24a370152306
translation_route: zh-CN/运行监控/00-目录
translation_default_route: zh-CN/运行监控/00-目录
---

# Runtime Monitoring

## Course overview

Runtime monitoring tells a team whether a service meets user expectations and helps it locate, contain, and learn from anomalies in latency, errors, quality, safety, or cost. **Monitoring** usually checks predefined signals and conditions; **observability** emphasizes answering questions that were not enumerated in advance from a system's outputs. Both depend on meaningful instrumentation, semantics, and operational processes.

This course covers logs, metrics, traces, instrumentation and context propagation, SLIs/SLOs, quality/safety/cost signals, alerts, dashboards, drift investigation, and incident response. It does not replace the model lifecycle in [[mlops/00-index|MLOps]], the LLM release unit and evaluation gates in [[llmops/00-index|LLMOps]], or the evaluators defined by [[evaluation-framework/00-index|Evaluation Framework]]. Instead, it monitors the coverage, trends, and action boundaries of those online signals.

## Where this course fits

Runtime monitoring sits between “deployed” and “operated reliably.” Learn APIs, JSON, logging, model/LLM call paths, and basic evaluation first. The resulting operational evidence feeds later work in evaluation, benchmark design, AI safety, and AI governance.

## Learning objectives

After completing this course, you will be able to:

- distinguish the questions suited to logs, metrics, and traces, and correlate them with IDs, resource attributes, and time;
- design automatic and manual instrumentation, W3C Trace Context propagation, and Collector pipelines, including monitoring of the telemetry path itself;
- derive an SLI, SLO, statistical window, and error budget from user expectations;
- organize service and resource symptoms with RED, USE, and the four golden signals, and correctly interpret histograms, percentiles, sampling, and high cardinality;
- combine availability and tail latency with AI task quality, safety, cost, and label coverage in one monitoring surface;
- design actionable alerts with suppression, runbooks, clear owners, and recovery conditions;
- build overview → drill-down → evidence dashboards instead of decorative walls of charts;
- correctly interpret drift, label delay, sampling, and missing signals;
- run a full incident loop: classification, containment, evidence preservation, recovery, and postmortem learning.

## Prerequisites

- Read and write JSON with Python 3, and understand averages, percentiles, ratios, and time windows.
- Understand HTTP status codes, request IDs, timeouts, retries, and batch jobs.
- Have a basic grasp of model versions, RAG, Tool Calling, and LLM token/cost accounting.
- You do not need Prometheus, OpenTelemetry, or a cloud-monitoring platform installed first.

## Recommended sequence

1. [[runtime-monitoring/foundations/01-logs-metrics-and-traces|Logs, Metrics, and Traces]] — understand the tradeoffs and correlation of the three signal types.
2. [[runtime-monitoring/foundations/02-instrumentation-collector-and-correlation|Instrumentation, Collectors, and Correlation]] — keep telemetry correlated and governable across HTTP, asynchronous jobs, and tools.
3. [[runtime-monitoring/foundations/03-slis-slos-and-error-budgets|SLIs, SLOs, and Error Budgets]] — select signals and objectives from user expectations.
4. [[runtime-monitoring/production-monitoring/03-quality-safety-and-cost-signals|Quality, Safety, and Cost Signals]] — make AI failures visible beyond HTTP 200.
5. [[runtime-monitoring/production-monitoring/04-alert-design-and-on-call-operations|Alert Design and On-Call Operations]] — send actionable symptoms to the right people only.
6. [[runtime-monitoring/production-monitoring/05-dashboards-and-diagnostic-views|Dashboards and Diagnostic Views]] — create a drill-down path from user impact to one trace.
7. [[runtime-monitoring/production-monitoring/06-drift-feedback-and-label-latency|Drift, Feedback, and Label Latency]] — treat distribution change as the start of an investigation, not an automatic root cause.
8. [[runtime-monitoring/production-monitoring/07-incident-response-and-postmortems|Incident Response and Postmortems]] — protect users, preserve evidence, and verify recovery under pressure.
9. [[runtime-monitoring/project-and-self-check/08-offline-monitoring-audit-project-and-self-check|Offline Monitoring Audit Project and Self-Check]] — validate structured events, traces, RED/USE, SLOs, error budgets, and multi-window alerts.

## Hands-on entry point

The main project is [[runtime-monitoring/project-and-self-check/08-offline-monitoring-audit-project-and-self-check|Offline Monitoring Audit Project and Self-Check]]. It uses only Python's standard library. It strictly validates a small JSON event, trace, and release-evidence contract; turns raw invalid UTF-8, Unicode surrogates that cannot be stably encoded as UTF-8 scalar sequences, and numbers that cannot be represented as finite `float` values into controlled errors; calculates RED/USE, SLIs, p95, bad-event ratios, and error-budget burn rates from an explicit `window_end`; and never calls a burn rate remaining budget. It separately checks the age of business events and Collector exports. Release evidence explicitly declares the instructional format of the candidate-gate summary it accepts. Anomalous windows produce only a no-raw-content regression candidate for human triage; they never rewrite a frozen evaluation set automatically. Forty-five tests cover these boundaries. All IDs and thresholds are offline teaching data: no network, third-party package, or key is needed.

## Mastery checklist

- [ ] I can drill from a slow request metric to its trace and structured logs.
- [ ] I can explain W3C Trace Context, a Collector pipeline, semantic-convention stability, sampling, and cardinality boundaries.
- [ ] I can write an SLI with an event definition, good-event condition, window, and data source.
- [ ] I can distinguish technical success, task quality, safety outcome, cost, and observability completeness.
- [ ] I can give an alert user impact, severity, owner, runbook, suppression, and recovery conditions.
- [ ] I can explain the evidence limits introduced by sampling, high cardinality, label delay, and proxy metrics.
- [ ] I can turn an incident postmortem into a new alert, regression sample, runbook, and exercise.
- [ ] I can run the offline project and its 45 tests on Windows 11/PowerShell 7, and explain why every threshold is a local teaching policy.

## Relationships to other courses

- [[mlops/00-index|MLOps]] uses runtime signals to assess model drift, release, and retraining; this course owns signal semantics, SLOs, alerts, and incident processes.
- [[llmops/00-index|LLMOps]] defines LLM release units, trace metadata, and Canary decisions; this course supplies the general observability and response method.
- [[evaluation-framework/00-index|Evaluation Framework]] defines task quality and evaluators. Runtime monitoring tracks online coverage, trends, and failure samples, then outputs only human-triage candidates rather than writing a frozen evaluation set automatically. The full cross-stage handoff fields, summary, and human-triage boundary are specified in [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and Regression Loop]].
- [[ai-safety/00-index|AI Safety]] defines threats and controls; runtime monitoring operationalizes only observable safety symptoms, coverage, and response.

## Primary references

All official or primary sources below were checked on 2026-07-22. Standard stability, tool syntax, and support status can change, so implementation must pin a version and recheck it. The OpenTelemetry core semantic-conventions page was at 1.43.0 when checked, while GenAI conventions have moved to a separate repository. A production contract must pin the repository revision, schema URL, or equivalent contract version in use, determine stability from the actual signal and component, and run compatibility tests. Do not mistake the core-page version for a current GenAI field version.

- [OpenTelemetry Observability primer](https://opentelemetry.io/docs/concepts/observability-primer/) — observability, reliability, and signal fundamentals.
- [OpenTelemetry Signals](https://opentelemetry.io/docs/concepts/signals/) — official entry point for logs, metrics, and traces.
- [OpenTelemetry Collector Architecture](https://opentelemetry.io/docs/collector/architecture/) — Receiver, Processor, and Exporter pipelines.
- [OpenTelemetry Versioning and stability](https://opentelemetry.io/docs/specs/otel/versioning-and-stability/) — stability must be assessed by component.
- [OpenTelemetry Generative AI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — migration note on the core site.
- [OpenTelemetry GenAI semantic conventions repository](https://github.com/open-telemetry/semantic-conventions-genai) — current separate specification repository; pin a specific revision in implementation.
- [W3C Trace Context](https://www.w3.org/TR/trace-context/) — standard for propagating trace context across services.
- [Google SRE: Service Level Objectives](https://sre.google/sre-book/service-level-objectives/) — choosing SLIs/SLOs and error budgets from user behavior.
- [Google SRE: Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) — latency, traffic, errors, saturation, and related fundamentals.
- [Google SRE Workbook: Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/) — error-budget burn rates and multi-window alerts.
- [Prometheus Alerting practices](https://prometheus.io/docs/practices/alerting/) — symptom orientation, actionability, and monitoring the monitoring system.
- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) — current NIST resource for incident response and risk management.

