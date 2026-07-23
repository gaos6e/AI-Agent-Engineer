---
title: "Probability and Statistics: Descriptive Statistics and Data Quality"
tags:
  - ai-agent-engineer
  - probability-and-statistics
  - descriptive-statistics
aliases:
  - Agent evaluation data health check
  - Introduction to descriptive statistics
source_checked: 2026-07-14
source_baseline:
  - NIST Exploratory Data Analysis
  - Python 3.14.6 statistics documentation
related: "[[probability-and-statistics/00-index]]"
lang: en
translation_key: 概率统计/00A-描述统计与数据质量.md
translation_source_hash: 117c15dcb06277fb9cfdb29fa85dcb25935331037a61bd87418ab6b47a0d51ec
translation_route: zh-CN/概率统计/00A-描述统计与数据质量
translation_default_route: zh-CN/概率统计/00A-描述统计与数据质量
---

# Probability and Statistics: Descriptive Statistics and Data Quality

## Objective

Statistical inference cannot repair a flawed table. Before calculating a mean or confidence interval, establish what a row represents, who belongs in the denominator, which values are missing, which records are duplicated, and whether the data are grouped by time or task. This lesson provides a repeatable data health-check workflow for Agent evaluation.

## Define the unit of analysis first

The **unit of analysis** is the basic entity that can be treated as one observation. It might be:

- one unique task;
- one model generation for the same task;
- one user session;
- one tool call; or
- one daily service aggregate.

These units are not interchangeable. If every task produces 20 generations, treating all 20 outputs as 20 independent tasks mistakes within-task correlation for extra information. Retain at least these identifiers:

| Field | Purpose |
| --- | --- |
| `task_id` | Identifies a task and supports A/B pairing. |
| `run_id` / `sample_id` | Distinguishes repeated generations for the same task. |
| `model_version` | Records the version under evaluation. |
| `task_type` | Supports pre-specified strata. |
| `score` | Specifies the scale, direction, and allowed range. |
| `latency_ms`, `cost` | Retains engineering metrics beyond quality. |
| `timestamp` | Detects temporal drift, incident windows, and stopping-rule problems. |
| `grader_id` | Identifies grader structure when a person or model assigns scores. |

Document each field's unit, allowed values, missingness meaning, and generation process in a data dictionary. A score of zero and an unscored task are not the same thing.

## The denominator matters more than the percentage

The success rate is:

$$\hat p=\frac{\text{number of successful tasks}}{\text{number of tasks included in analysis}}$$

Before reporting `80%`, state:

- which event is counted in the numerator;
- which tasks the denominator includes or excludes;
- how failures, timeouts, refusals, and parsing errors are scored;
- whether system errors caused tasks to be removed; and
- whether every task has equal weight.

For example, suppose 70 of 100 tasks succeed, 10 time out, and 20 fail. Removing timeouts from the denominator gives `70/90≈77.8%`; scoring timeouts as failures gives `70/100=70%`. Those metrics answer different questions. You cannot report only the more flattering number.

## Location: mean, median, and quantiles

- **Mean**: the sum of all values divided by their count. It suits additive objectives but is sensitive to long tails and outliers.
- **Median**: the middle value after sorting. It is more robust to extreme values.
- **Quantile**: a cut point that divides an ordered distribution at a specified proportion. P95 latency means roughly 95% of observations do not exceed that value; it is not “the average of the slowest 5%.”

For `[100, 110, 120, 130, 2000]`, the last value pulls the mean up substantially while the median remains 120. Neither answer is wrong; they describe different aspects of the distribution. A latency report commonly includes sample size, median, P95/P99, and timeout rate.

> [!warning] Quantile algorithms are not unique
> With small samples, different interpolation definitions return different values. Record the tool, method, and sample size; do not use a P99 calculated from very few observations as precise SLA evidence. Python `statistics.quantiles` offers `exclusive` and `inclusive` methods because they answer different modeling assumptions.

## Dispersion: range, IQR, and standard deviation

- **Range**: maximum minus minimum. It is extremely sensitive to one extreme observation.
- **Interquartile range (IQR)**: $Q_3-Q_1$, the spread of the middle 50% of observations.
- **Standard deviation**: take the average squared deviation from the mean, then the square root; it has the same unit as the original metric.

The same mean does not imply the same experience. Two Agents can both average 80% success, while one is stable across task types and the other nearly always fails on critical tool tasks. Dispersion also does not replace stratification: inspect the distribution and task structure before interpreting one summary statistic.

## Missing values, NaN, duplicates, and invalid values

Check in this order:

1. Total row count and count of unique `task_id` values.
2. Whether A and B contain exactly the same task set.
3. Missing-value counts and causes for each column.
4. Whether numeric values obey the contract and use consistent units.
5. Whether repeated rows are genuine repeated generations or accidental copies.
6. Whether `NaN`, infinity, and parsing failures have silently entered the calculation.
7. Whether exclusion rules were fixed before results were observed.

The Python documentation notes that `NaN` comparison behavior can produce surprising results in functions that sort or count, including `median`, `mode`, and `quantiles`. Do not mechanically replace `NaN` with zero. First determine whether it means missing data, not applicable, or a calculation failure, then apply a pre-specified rule.

## Stratification, time, and Simpson's paradox

An overall average depends on the mix of cases. In the following data, B outperforms A at each difficulty level:

| Difficulty | A | B |
| --- | ---: | ---: |
| Easy | 90/100 = 90% | 19/20 = 95% |
| Hard | 1/10 = 10% | 40/100 = 40% |

Yet A is `91/110≈82.7%` overall and B is `59/120≈49.2%`, reversing the direction because A was evaluated on more easy tasks and B on more hard tasks. This reversal from differing composition is often called **Simpson's paradox**. The remedy is not to reject all aggregate metrics; it is to pair on the same task set, predefine important strata, and report the sample size for each stratum.

Time can create structure too. Requests from the same incident window are correlated, and repeatedly inspecting a metric until you select its best moment introduces selection bias. Keep timestamps and plot a time series instead of indiscriminately shuffling every row together.

## A runnable minimum health check

```python
from math import isfinite
from statistics import mean, median, quantiles, stdev

latencies = [120.0, 125.0, 130.0, 140.0, 900.0]
scores = [1, 1, 0, 1, 0]

if not latencies or not all(isfinite(value) and value >= 0 for value in latencies):
    raise ValueError("latency must be finite and non-negative")
if len(scores) != len(latencies) or any(score not in (0, 1) for score in scores):
    raise ValueError("scores and latencies must align with the binary contract")

p95 = quantiles(latencies, n=100, method="inclusive")[94]
summary = {
    "n": len(scores),
    "success_rate": mean(scores),
    "latency_mean": mean(latencies),
    "latency_median": median(latencies),
    "latency_sample_sd": stdev(latencies),
    "latency_p95_inclusive": p95,
}

assert summary["n"] == 5
assert summary["success_rate"] == 0.6
assert summary["latency_median"] == 130.0
```

This verifies only the contract of a small list; it does not establish that the sample represents production. A real analysis must also check unique IDs, missingness causes, complete pairing, strata, and temporal structure.

## Data health-check delivery template

```text
Target population:
Unit of analysis:
Time window:
Data source and version:
Total rows / unique tasks:
Numerator / denominator definition:
Handling of missing values, timeouts, and parsing failures:
Duplicate and repeated-generation structure:
A/B pairing completeness:
Primary metric and direction:
Pre-specified strata:
Known selection bias and uncovered scenarios:
```

## Exercises and self-check

1. Calculate the mean and median of `[100, 110, 120, 130, 2000]` by hand, and explain the question each best answers.
2. Design a minimum table header containing `task_id`, `run_id`, version, stratum, score, latency, and grader.
3. Calculate the same data once with timeouts scored as failures and once with timeouts excluded; write the distinct meaning of each metric.
4. Explain why copying each task 20 times does not create 20 times as much independent information.
5. In the Simpson's-paradox example, how would you change the evaluation design to compare A and B fairly?

- [ ] I define the unit of analysis and target population before calculating statistics.
- [ ] I report the numerator, denominator, sample size, missingness, and exclusion rules.
- [ ] I can choose means, medians, quantiles, and dispersion based on the distribution.
- [ ] I check pairing, duplicates, strata, and time structure.

Next: [[probability-and-statistics/probability-conditional-probability-and-bayes|Probability, conditional probability, and Bayes' rule]].

## References

Sources checked on **2026-07-14**.

- [NIST: Exploratory Data Analysis](https://www.itl.nist.gov/div898/handbook/eda/eda.htm)
- [NIST: Quantitative Techniques](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35.htm)
- [NIST: Percentiles](https://www.itl.nist.gov/div898/handbook/prc/section2/prc262.htm)
- [Python `statistics`](https://docs.python.org/3/library/statistics.html)
