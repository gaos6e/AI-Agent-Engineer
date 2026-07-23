---
title: "Relationships, Trends, and Time Series"
tags:
  - ai-agent-engineer
  - data-visualization
aliases:
  - Relationship and Trend Charts
source_checked: 2026-07-14
source_baseline:
  - Matplotlib 3.11.0 pairwise-data and date-axis documentation
lang: en
translation_key: 数据可视化/03-关系趋势与时间序列.md
translation_source_hash: 92a10343597b0bc11675a332d891e8a85f209b1c75751a38f891920a9d6168e4
translation_route: zh-CN/数据可视化/03-关系趋势与时间序列
translation_default_route: zh-CN/数据可视化/03-关系趋势与时间序列
---

# Relationships, Trends, and Time Series

## Objectives

Distinguish cross-sectional relationships, genuine temporal trends, and category comparisons. Handle overplotting, aggregation granularity, missing intervals, and release events correctly, and avoid inferring causality from visual correlation.

## Scatter plots show relationships, not causality

Each point represents two numbers for the same unit, such as token count and latency for one task. Color can encode version and shape can encode task, but too many channels make a chart hard to read. For extensive overlap, use transparency, hexbin, or stratified sampling, and report the sampling method.

A relationship can result from a third variable: complex tasks can increase both token count and latency. Stratify by task type or control common factors in a model; do not declare from one scatter plot that “tokens cause failure.”

For many points, report the total first, then use transparency, hexbin, or two-dimensional density to reveal overlap. If sampling, fix a random seed and state the sampling rule. When color encodes categories, add shape or direct labels; when color maps a continuous value, provide a colorbar and units.

## Time series

Line charts suit ordered temporal data. State clearly:

- timestamp and timezone; whether aggregation is hourly, daily, or weekly;
- whether missing time intervals mean zero or were not collected—do not make a connected line imply continuity;
- events such as releases, configuration changes, and incidents;
- the meaning of raw values, moving averages, and confidence bands.

A moving average can reduce noise, but it also lags and hides spikes. Retain a faint raw series or report anomaly events alongside it.

Aggregation granularity is part of the conclusion. A minute-level peak can disappear in a daily mean, and natural-day aggregation can be affected by timezone and daylight saving time. Predefine comparison windows before and after deployment, then inspect traffic, task mix, and monitoring gaps together. One line that “fell after release” is not enough to prove the release caused the decline.

## Category comparisons

Bar lengths are easiest to compare from a common zero baseline. With many categories, use horizontal bars and order them by value or business sequence. Do not connect unordered categories with a line, which implies a continuous trend.

Dual y-axes can create an appearance of synchronization through arbitrary scaling. Prefer two vertically stacked panels with a shared x-axis, standardized indices, or a scatter plot that states the relationship explicitly.

## Exercise

Design a chart for “daily success rate and call volume.” Explain how you show uncertainty on low-volume days, deployment events, and missing data, and give a layout that does not use a dual y-axis.

Suggested answer: use two panels sharing a date axis. The top panel shows success-rate points and confidence intervals with the daily denominator; the lower panel shows call volume. Mark deployment with a vertical event line, break the line on missing dates instead of filling in zero, and let intervals naturally widen on low-volume days. To investigate the relationship between volume and success rate, add a separate volume–success scatter plot stratified by task mix.

## Mastery check

- [ ] I can explain whether every point in a scatter plot is independent and identify potential common causes.
- [ ] I handle overplotting for many points and record the sampling or aggregation method.
- [ ] I distinguish missing values, zero values, and not-collected values, and do not connect a time line through missing data without justification.
- [ ] I use vertically stacked plots with a shared x-axis instead of dual y-axes.
- [ ] I do not connect unordered categories with a line or claim causality directly from visual correlation.

Next: [[data-visualization/04-error-and-uncertainty|Error and Uncertainty]].

## References

Sources were checked on 2026-07-14; example principles were checked against Matplotlib 3.11.0 documentation.

- [Matplotlib: Pairwise data](https://matplotlib.org/stable/plot_types/basic/index.html)
- [Matplotlib: Date tick labels](https://matplotlib.org/stable/gallery/text_labels_and_annotations/date.html)
- [Matplotlib `hexbin`](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.hexbin.html)
