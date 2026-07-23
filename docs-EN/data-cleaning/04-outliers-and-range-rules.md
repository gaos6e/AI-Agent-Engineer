---
title: "Outliers and Range Rules"
tags:
  - ai-agent-engineer
  - data-quality
aliases:
  - Outlier handling
source_checked: 2026-07-14
source_baseline:
  - pandas 3.0 descriptive-statistics guide
  - scikit-learn 1.9.0 outlier-detection guide
lang: en
translation_key: 数据清洗/04-异常值与范围规则.md
translation_source_hash: 35e28cfd54e4e56c564afae2473ea58a583f832bf8c678ac33fe5eed2f23223b
translation_route: zh-CN/数据清洗/04-异常值与范围规则
translation_default_route: zh-CN/数据清洗/04-异常值与范围规则
---

# Outliers and Range Rules

## Objective

Use types, hard ranges, and cross-field contracts to identify invalid values before treating statistical tails as investigation candidates. Avoid using deletion or clipping to hide real failures and distribution shifts.

## Invalid values and statistical outliers differ

A latency of **-12 ms** violates a physical or contractual constraint and is invalid. A latency of **120000 ms** is rare but may be a real timeout. The first can be rejected by rule; the second should be investigated rather than deleted automatically.

## Checking order

1. Type and parseability: **"fast"** cannot parse as a latency.
2. Hard range: a ratio belongs in **[0, 1]** and a count should not be negative.
3. Cross-field consistency: an end time cannot precede its start time.
4. Distribution inspection: quantiles, box plots, logarithmic scale, and groups by version or source.
5. Domain investigation: is a rare value a failure, attack, long-tail case, or unit error?

## Common statistical rules and their limits

A Z-score assumes that a mean and standard deviation are meaningful; heavy-tailed data can distort the threshold. An IQR rule uses interquartile range to identify values far from the bulk, but it is not a “true anomaly detector,” including for skewed data. These methods generate investigation candidates rather than authorize automatic deletion of facts.

For right-skewed fields such as latency, token count, and cost, inspect logarithmic scale and p50/p95/p99 first. A mean can be dominated by a few extremely large values, while a high percentile can represent the tail latency users feel most acutely.

## Distribution drift

Every historical row can be valid while the overall distribution has changed. For example, a new model version can double token counts across the board. Cleaning should report drift and provenance, not clip the change away.

## Treatment record

Each rule should emit the raw value, normalized value, action (**accepted/repaired/quarantined**), reason code, and rule version. Clipping, winsorization, and logarithmic transformation are modeling choices; perform them in the training Pipeline and evaluate them with validation data.

## Exercise

For **latency_ms=[120, 140, 150, 180, 90000, -1]**, identify invalid values and investigation candidates. State which additional fields you need to explain **90000**.

## Mastery check

- [ ] I can distinguish “unparseable,” “violates a hard range,” “statistically rare,” and “overall drift.”
- [ ] I do not delete Z-score or IQR candidates as if they were established errors.
- [ ] I report p50, p95/p99, sample count, and time window for right-skewed latency.
- [ ] I retain raw value, normalized value, action, reason code, and rule version.

Next: [[data-cleaning/05-text-json-and-time-normalization|Text, JSON, and time normalization]].

## References

Sources were checked on 2026-07-14.

- [pandas: Descriptive statistics](https://pandas.pydata.org/docs/user_guide/basics.html#descriptive-statistics)
- [scikit-learn: Novelty and Outlier Detection](https://scikit-learn.org/stable/modules/outlier_detection.html)
