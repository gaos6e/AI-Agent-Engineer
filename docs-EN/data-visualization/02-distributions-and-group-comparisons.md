---
title: "Distributions and Group Comparisons"
tags:
  - ai-agent-engineer
  - data-visualization
aliases:
  - Distribution Visualization
source_checked: 2026-07-14
source_baseline:
  - Matplotlib 3.11.0 statistical-distribution and ECDF documentation
lang: en
translation_key: 数据可视化/02-分布与分组比较.md
translation_source_hash: 844bd60fb825ff57ca9c603893c974778aa328b9d06b2b0274019ceb4bb916ca
translation_route: zh-CN/数据可视化/02-分布与分组比较
translation_default_route: zh-CN/数据可视化/02-分布与分组比较
---

# Distributions and Group Comparisons

## Objectives

Use raw points, histograms, ECDFs, and boxplots to answer “what does the data look like?” and “where does the difference between groups come from?” Avoid plotting only a mean or filtering out failed samples.

## Why a mean is not enough

Two Agent versions can both have mean latency of two seconds. One may cluster at two seconds, while the other has most runs at 0.5 seconds and a few timeouts at 20 seconds. User experience and incident risk are entirely different. At minimum, examine sample count, median, p95/p99, missing/timeout rate, and the raw distribution.

## Common charts

- **Histogram:** shows counts within intervals. Conclusions can change with bin width, so report binning.
- **ECDF:** x-axis is value and y-axis is the fraction of samples no greater than that value. It needs no bins and suits latency comparison.
- **Boxplot:** compactly shows the median, quartiles, and candidate outliers; it does not show multimodal detail.
- **Violin plot:** shows density shape, but is sensitive to small samples and bandwidth selection.
- **Jittered dot plot:** shows every point directly for smaller samples; transparency can reduce overlap.

Choose by sample size and the argument:

| Samples per group | Preferred starting point | Reason |
| --- | --- | --- |
| `n < 3` | List every point | Quantiles and density have almost no stable meaning |
| `3 ≤ n < 10` | dot/strip plot | Lets readers see all evidence directly |
| `10 ≤ n < 30` | box or violin + raw points | Retains both summary and distribution |
| `n ≥ 30` | ECDF, box, violin, or histogram | Still report `n`, missing values, and binning/bandwidth |

These are not theorem-like statistical cutoffs. They are engineering rules meant to prevent small samples from being disguised as stable distributions by smoothed densities or summary charts.

## Group comparisons

State the denominator first: did each version run on the same task set, in the same time window, on the same hardware? An improved overall distribution can hide a decline on safety-related tasks. Split by version, task, language, or tool, but avoid infinite slicing followed by reporting only the most favorable result.

Right-skewed latency/token/cost values can use a logarithmic axis, but label it explicitly; zero and negative values cannot be logged directly. Do not delete timeouts and then claim latency improved. Treat timeouts as a separate state or include them under a stated upper-bound rule.

Before comparing group distributions, also confirm whether observations are paired. When the same task runs on v1 and v2, a per-task difference or paired points is usually more informative than two independent boxplots. If task sets differ, do not fabricate pairing with connecting lines. Similar distributions also do not imply the same business risk: inspect long tails, threshold violations, and critical subgroups separately.

## Exercise

You have 100 runs: 90 take one second and 10 take 30 seconds. Calculate the mean and median, then choose two charts that reveal the long tail. Explain what “only a boxplot” could still hide.

Answer check: the mean is 3.9 seconds and the median is one second. An ECDF directly shows that 90% of runs take no more than one second; a jittered dot plot or a histogram with explicit bins exposes the 10 long-tail points. A boxplot alone may compress all 30-second runs into one category of outlier, hiding their count and business state.

## Mastery check

- [ ] I can explain what the mean, median, p95, and timeout rate each answer.
- [ ] I choose raw points, ECDF, boxplots, or violins by sample size and can state their limits.
- [ ] I distinguish paired comparisons from independent groups and do not connect unmatched observations.
- [ ] I do not delete failures/timeouts and then plot a polished distribution of only completed runs.
- [ ] I can report histogram bins, log-axis handling, sample count, and filtering rules.

Next: [[data-visualization/03-relationships-trends-and-time-series|Relationships, Trends, and Time Series]].

## References

Sources were checked on 2026-07-14; `Axes.ecdf` usage was checked against Matplotlib 3.11.0 documentation.

- [Matplotlib: Statistical distributions](https://matplotlib.org/stable/plot_types/stats/index.html)
- [Matplotlib `Axes.ecdf`](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.ecdf.html)
