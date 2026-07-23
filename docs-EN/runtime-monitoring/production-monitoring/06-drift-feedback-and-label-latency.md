---
title: "Drift, Feedback, and Label Latency"
tags:
  - observability
  - drift
aliases:
  - Drift Monitoring
source_checked: 2026-07-14
lang: en
translation_key: 运行监控/02-生产监控/06-漂移、反馈与标签延迟.md
translation_source_hash: 4eab9c75b886b831b1521abcf1c9e73cf9c97ecaa1e483377866952593b8b38f
translation_route: zh-CN/运行监控/02-生产监控/06-漂移、反馈与标签延迟
translation_default_route: zh-CN/运行监控/02-生产监控/06-漂移、反馈与标签延迟
---

# Drift, Feedback, and Label Latency

## Goal

Distinguish data-quality failures, input-distribution change, label-distribution change, and concept drift. When ground truth is delayed or covers only part of the population, state honestly what the current evidence can prove.

## Four different problems

Let inputs be $X$ and true outcomes be $Y$:

- **Data-quality / contract failure** — missing fields, changed type/unit, wrong time zone, duplicates, or late data. It can be a pipeline incident requiring immediate repair.
- **Data drift** — $P(X)$ changes, for example the mix of input languages or task types changes.
- **Label drift** — $P(Y)$ changes, for example the true share of high-risk tickets rises.
- **Concept drift** — $P(Y\mid X)$ changes: the relationship between the same input and outcome changes.

Observing only $X$ cannot prove that $P(Y\mid X)$ changed. Data drift may have no quality impact; concept drift may occur even when the input marginal distribution looks stable.

## Reference and current windows

A drift statistic must make clear:

- why the reference window is trusted and which release, data definition, and business season it represents;
- the current window's sample size, data delay, and whether it includes partial days;
- whether time zone, missing values, new categories, sampling, and deduplication rules match;
- whether business cycles, holidays, market activity, or split releases can explain the change.

“Last week versus this week” is not necessarily a valid comparison. Annual seasonality, business growth, and product changes can make a fixed reference snapshot progressively unrepresentative. Updating a reference needs versioning and review; it must not happen automatically just to silence an alert.

## A verifiable categorical-distribution example

For a finite category set, Total Variation Distance (TVD) is an intuitive practice quantity:

$$
TVD(P,Q)=\frac{1}{2}\sum_i |P_i-Q_i|
$$

$TVD=0$ means the two category proportions are identical; the maximum is 1. For example, a reference intent mix of `{query: 0.7, write: 0.3}` and current mix of `{query: 0.4, write: 0.6}` have TVD 0.3.

This proves only a category-distribution difference, not lower task quality. There is no universal TVD threshold; calibrate it against historic normal variation, sample size, multiple comparisons, and business loss.

## Monitoring numeric, text, and embedding data

- For numeric values, compare missingness, percentiles, ranges, histograms, or distance from a reference.
- For categories, inspect new categories, head/tail proportions, and category-merging rules.
- For text, begin with language, length, encoding, duplication, refusal, and controlled task classes; do not store full raw text merely for convenience.
- For embeddings, monitor norms, distance from fixed reference samples, clusters, or downstream retrieval/task metrics.

Embedding drift depends on the embedding model, normalization, text preprocessing, and vector dimension. Vectors produced after a version change must not be compared directly with an old reference. A statistical distance also cannot replace retrieval recall, grounding, or task-success rate.

## Label delay and selection bias

True outcomes may arrive a week later. Preserve the release, prediction/action, task ID, and label-definition version at the original time, then backfill. Also report:

- count/proportion of labels received and their delay distribution;
- coverage differences by release, task, and slice;
- whether only human-handoff, customer-complaint, or policy-selected samples receive labels;
- whether label definitions changed or historical labels were revised.

If you investigate only samples the model marks high risk, you will obtain labels for those samples more easily; quality monitoring is then shaped by the model's own selection. Controlled random sampling or independent audit can add visibility, subject to privacy and business constraints.

## Investigation order after an alert

1. Verify collection, schema, time zone, definition, and version consistency first.
2. Check sample size, missingness, sampling, and label coverage.
3. Compare business cycles, releases, upstream changes, and external events.
4. Inspect task quality, safety, human feedback, and business outcome together.
5. Record the conclusion: data failure, explainable change, quality impact, no impact yet found, or insufficient evidence.
6. Escalate an immediately containable situation into an incident, but do not transform “drift” directly into “automatically deploy a new model.”

## Exercise and self-check

Scenario: the share of “account issue” inputs to a ticket Agent doubles. Overall labeled quality is unchanged, but label coverage falls from 60% to 20%. State what you can prove, what you cannot prove, and what evidence you need next. Answer:

1. Why cannot data drift automatically prove concept drift?
2. Why cannot an old vector reference distribution survive an embedding-model update?
3. Why does a quality curve containing only human-handoff samples fail to represent the whole population?

## Summary and next step

Drift is an investigation signal with assumptions, definitions, and coverage—not a root cause or automatic retraining command. When it combines with user harm, safety consequences, or material quality regression, proceed to [[runtime-monitoring/production-monitoring/07-incident-response-and-postmortems|Incident Response and Postmortems]].

## References

- [Google Rules of Machine Learning](https://developers.google.com/machine-learning/guides/rules-of-ml) — checked 2026-07-14; engineering guidance for production data, train/serve consistency, and feedback loops.
- [Learning from Time-Changing Data with Adaptive Windowing](https://www.cs.upc.edu/~gavalda/papers/adwin06.pdf) — Bifet and Gavaldà, original research source, checked 2026-07-14.
- [NIST AI RMF: Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) — checked 2026-07-14.

