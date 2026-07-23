---
title: "Model Monitoring, Drift, and Feedback"
tags:
  - mlops
  - model-monitoring
aliases:
  - ML Model Monitoring
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
lang: en
translation_key: MLOps/02-生产工程/06-模型监控、漂移与反馈.md
translation_source_hash: f3029f49cdb80c5adf561315726590d1854c7fd2a87ce9133ce6a45f59f7d695
translation_route: zh-CN/MLOps/02-生产工程/06-模型监控、漂移与反馈
translation_default_route: zh-CN/MLOps/02-生产工程/06-模型监控、漂移与反馈
---

# Model Monitoring, Drift, and Feedback

## Goal

Establish layered monitoring from service health to real model effect, and interpret drift signals correctly.

## Four observation layers

1. **System** — availability, error, latency, throughput, CPU/memory, and queue backlog.
2. **Data** — schema, missingness, range, categories, duplicates, freshness, and feature-computation failure.
3. **Model** — prediction distribution, confidence, abstention rate, critical slices, and version differences.
4. **Outcome** — labeled performance, business cost, human review, and user feedback.

Healthy service and wrong model is a common failure. A service can return 200 consistently while an upstream field is filled with a default and predictions are stable but wrong.

## Three concepts often confused

For input $X$ and label $Y$:

- **Data drift** — $P(X)$ changes.
- **Label drift** — $P(Y)$ changes.
- **Concept drift** — the relation $P(Y \mid X)$ changes.

Observing input alone cannot prove concept drift. Data drift can occur without quality loss; conditional relations can change even when marginal input distribution appears stable. Treat drift as an investigation signal, not a sufficient reason to retrain automatically.

## When labels are delayed

Many true labels arrive days or months later. Use two paths:

- **Fast proxy signals** — data quality, prediction distribution, human review, user reversal, and rule conflict.
- **Delayed ground-truth backfill** — use a stable entity ID to link a later label to the model, feature, and prediction at the time, then calculate real slice metrics.

Proxy signals discover anomalies early but must be labeled as not final quality. During backfill, avoid collecting only easy-to-obtain labels; otherwise the monitoring sample itself is biased.

## Slices before averages

An overall metric can hide:

- degradation in a new region or device;
- a low-traffic but high-risk group averaged away;
- upstream data affecting only part of requests in one version;
- unequal label coverage across groups.

Choose slices tied to business risk and bound their number. Infinite dimension combinations create statistical instability and high-cardinality cost. Define critical slices first and retain redacted raw offline evidence for exploratory work.

## A release action needs its full denominator

An online gate must not retain only a ratio. `Critical-slice recall=0.80` from five labeled examples is not equivalent evidence to the same ratio from 500; `label coverage=80%` can also come from a window that is too small. A reviewable expansion or rollback decision binds fixed release/artifact, candidate-gate evidence, shadow or Canary stage, total sample count, labeled count, critical-slice count, label age, collection completeness, and policy version.

With insufficient evidence, hold scope or investigate; never call “no failure observed yet” success. A fixed historical reference can reveal a clear change but cannot rule out time, traffic mix, or external environment confounding. Claiming candidate-caused improvement needs concurrent control, stable allocation, or another design suitable for the problem. See the runnable simplified boundary in [[mlops/project-and-self-check/08-offline-model-promotion-project-and-self-check|Offline Model Promotion Project and Self-Check]] and the stricter composite-release example with concurrent control in [[llmops/project-and-self-check/08-offline-release-gate-project-and-self-check|LLMOps Offline Release Gate Project]].

## Applying drift detection

1. Choose a trustworthy reference and current window.
2. Check collection, schema, timezone, and version consistency.
3. Choose an appropriate statistic for numeric, categorical, or embedding data.
4. Calibrate thresholds from historical normal variation.
5. Interpret results with sample size and multiple comparisons.
6. After alert, inspect quality, business activity, and data pipeline.
7. Record a conclusion: data problem, real change, harmless change, or insufficient evidence.

Methods such as ADWIN can detect change over time, but every detector has false positives, detection latency, and assumptions. An algorithm name is not a conclusion.

## Feedback-loop risk

Once a model influences decisions, later data can be changed by the model. If only high-scoring samples are investigated, labels are more likely for those samples. Retraining data then carries selection bias. Record why a label was obtained, preserve random sampling or controlled exploration, and give human feedback a clear definition.

## Exercise and self-check

For a ticket-priority model, list two signals in each of the four layers. Does a sudden increase in input length prove quality decline? What bias occurs when only human-taken-over tickets have ground truth? Why calibrate drift thresholds from this system's history and risk rather than copying a fixed number?

## Next step

Monitoring supplies evidence; it does not make a causal decision for you. When an anomaly appears, choose rollback, data repair, rule adjustment, or retraining in [[mlops/production-engineering/07-incidents-rollback-and-retraining-decisions|Incidents, Rollback, and Retraining Decisions]]. For the system practice of collecting signals, SLOs, and alerts, see [[runtime-monitoring/00-index|Runtime Monitoring]].

## References

- [Google SRE: Service Level Objectives](https://sre.google/sre-book/service-level-objectives/) — checked 2026-07-14.
- Bifet and Gavaldà, [Learning from Time-Changing Data with Adaptive Windowing](https://www.cs.upc.edu/~gavalda/papers/adwin06.pdf) — original paper; checked 2026-07-14.
