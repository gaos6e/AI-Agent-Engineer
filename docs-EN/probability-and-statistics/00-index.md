---
title: "Probability and Statistics"
tags:
  - ai-agent-engineer
  - mathematical-and-data-foundations
  - probability-and-statistics
aliases:
  - Probability and Statistics
  - Probability and Statistics learning path
source_checked: 2026-07-14
source_baseline:
  - NIST/SEMATECH e-Handbook of Statistical Methods
  - Python 3.14.6 statistics and random documentation
  - ASA Statement on Statistical Significance and P-Values
ai_learning_stage: "2. Mathematical and data foundations"
ai_learning_order: 10
ai_learning_schema: 2
ai_learning_id: probability-statistics
ai_learning_domain: foundations
ai_learning_catalog_order: 1000
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 80
ai_learning_track_agent_app_kind: recommended
ai_learning_track_rag_order: 80
ai_learning_track_rag_kind: recommended
ai_learning_track_agent_platform_order: 80
ai_learning_track_agent_platform_kind: recommended
ai_learning_track_multimodal_realtime_order: 80
ai_learning_track_multimodal_realtime_kind: recommended
lang: en
translation_key: 概率统计/00-目录.md
translation_source_hash: 710fdd1c49f79a081e65ebaec97f0e8a8078c9e02e8af462093dd2cecbdb6dcf
translation_route: zh-CN/概率统计/00-目录
translation_default_route: zh-CN/概率统计/00-目录
---

# Probability and Statistics

## Course overview

Model outputs, sampled evaluations, production success rates, and retrieval metrics are all random to some degree. Probability gives you a language for describing uncertainty; statistics lets you infer properties of a population from limited data. This course begins with units of analysis, denominators, and descriptive statistics, then develops probability models, sampling, and inference before applying them to Agent A/B evaluation. The goal is not to memorize formulas. It is to avoid mistaking one run, one average, or one *p*-value for a certain conclusion.

## Where this course fits

Probability and Statistics belongs to the Mathematical and data foundations stage. It supplies the language of uncertainty used throughout machine learning, evaluation systems, benchmark design, and runtime monitoring. You can begin after the engineering foundations; the same ideas recur whenever you compare models, retrievers, or Agent versions.

## Learning objectives

- Update judgments with events, conditional probability, and Bayes' rule.
- Describe data with means, medians, quantiles, standard deviations, and stratified tables while checking denominators, missingness, and duplicates.
- Recognize random variables, distributions, expectation, variance, and sampling variation.
- Express uncertainty in a metric with a confidence interval.
- Interpret hypothesis tests, *p*-values, multiple comparisons, and effect sizes correctly.
- Define a target population, unit of analysis, pairing structure, primary metric, and minimum practically important difference for Agent evaluation.
- Compare two Agent versions with a standard-library bootstrap and state the evidence boundary honestly.

## Prerequisites

Basic arithmetic, square roots, Python lists, and functions are enough. The summation symbol $\sum$ means “add a collection of numbers.” Complete [[python-fundamentals/00-index|Python Fundamentals]] first if possible. This course does not require calculus or a third-party statistics package.

## Recommended sequence

1. [[probability-and-statistics/descriptive-statistics-and-data-quality|Descriptive statistics and data quality]]: first establish what a row represents, what the denominator is, and whether data are missing or duplicated.
2. [[probability-and-statistics/probability-conditional-probability-and-bayes|Probability, conditional probability, and Bayes' rule]]: begin with uncertain events and base rates.
3. [[probability-and-statistics/random-variables-and-common-distributions|Random variables and common distributions]]: map success, categories, counts, and latency to probability models.
4. [[probability-and-statistics/expectation-variance-and-sampling|Expectation, variance, and sampling]]: understand why average metrics vary and why correlated observations do not equal more information.
5. [[probability-and-statistics/estimation-confidence-intervals-and-hypothesis-testing|Estimation, confidence intervals, and hypothesis testing]]: draw appropriately limited conclusions from a sample.
6. [[probability-and-statistics/evaluation-design-effect-size-and-statistical-pitfalls|Evaluation design, effect sizes, and statistical pitfalls]]: fix the population, unit, pairing, primary metric, and decision threshold before calculating.
7. [[probability-and-statistics/project-agent-evaluation-uncertainty|Project: Agent evaluation uncertainty]]: complete a tested paired percentile-bootstrap comparison.

## Hands-on entry points

- Start with an Agent-evaluation data health check in [[probability-and-statistics/descriptive-statistics-and-data-quality|Descriptive statistics and data quality]].
- Continue to [[probability-and-statistics/project-agent-evaluation-uncertainty|Project: Agent evaluation uncertainty]] to implement a paired percentile bootstrap with the standard library, then use replicated samples and stratified reporting to recognize false certainty.

## Mastery checklist

- [ ] Distinguish populations, samples, parameters, statistics, and random variables.
- [ ] Explain why $P(A\mid B)$ and $P(B\mid A)$ are not interchangeable.
- [ ] Report sample size and dispersion or an interval alongside a mean.
- [ ] Explain why “fail to reject the null hypothesis” does not prove two systems are the same.
- [ ] Choose a paired evaluation and report an interval for the difference with bootstrap.
- [ ] Identify whether independence, representativeness, and distributional assumptions hold.
- [ ] Specify the primary metric, minimum practically important difference, and stopping rule before looking at results.

## Relationship to other courses

| Course | Connection |
| --- | --- |
| [[machine-learning/00-index\|Machine Learning]] | Probability describes prediction, loss, noise, and generalization uncertainty. |
| [[evaluation-framework/00-index\|Evaluation Framework]] and [[benchmark-design/00-index\|Benchmark Design]] | Populations, sampling, pairing, intervals, effect sizes, and multiple comparisons set the boundary of a conclusion. |
| [[embeddings/00-index\|Embeddings]] and [[semantic-search/00-index\|Semantic Search]] | Retrieval metrics are random variables; thresholds and distributions depend on queries and corpora. |
| [[runtime-monitoring/00-index\|Runtime Monitoring]] | Success rates, latency quantiles, and alerts require stable baselines and time-dependence analysis. |
| [[data-visualization/00-index\|Data Visualization]] | Plots reveal distributions, strata, outliers, and temporal structure; a summary number is not enough. |

## Primary references

- [NIST/SEMATECH e-Handbook of Statistical Methods](https://www.itl.nist.gov/div898/handbook/)
- [NIST Exploratory Data Analysis](https://www.itl.nist.gov/div898/handbook/eda/eda.htm)
- [NIST Probability Distributions](https://www.itl.nist.gov/div898/handbook/eda/section3/eda36.htm)
- [NIST Hypothesis Tests and Confidence Intervals](https://www.itl.nist.gov/div898/handbook/prc/section1/prc1.htm)
- [NIST Randomized Block Designs](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm)
- [ASA Statement on Statistical Significance and P-Values](https://www.amstat.org/asa/files/pdfs/P-ValueStatement.pdf)
- Python [`statistics`](https://docs.python.org/3/library/statistics.html) and [`random`](https://docs.python.org/3/library/random.html)

Sources checked on **2026-07-14**. This course uses NIST, ASA, and the Python 3.14.6 documentation as its external baseline; the local examples were verified with Python 3.11.9. A source list cannot replace review of the current sampling process and data structure: statistical-method validity depends on both.
