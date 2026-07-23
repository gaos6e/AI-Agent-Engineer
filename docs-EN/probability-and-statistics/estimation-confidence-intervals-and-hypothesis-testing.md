---
title: "Estimation, Confidence Intervals, and Hypothesis Testing"
tags: [ ai-agent-engineer, probability-and-statistics ]
aliases: [ Confidence intervals and hypothesis testing ]
source_checked: 2026-07-14
source_baseline:
  - NIST Confidence Intervals
  - ASA Statement on Statistical Significance and P-Values
lang: en
translation_key: 概率统计/04-估计置信区间与假设检验.md
translation_source_hash: 6bc087a2453426c44781f3ee16edb85445e09e8a3ff3b426dfd142bec928bbe1
translation_route: zh-CN/概率统计/04-估计置信区间与假设检验
translation_default_route: zh-CN/概率统计/04-估计置信区间与假设检验
---

# Estimation, Confidence Intervals, and Hypothesis Testing

## A point estimate is not enough

An 80% sample success rate is a point estimate. Its evidential strength is plainly different for 5 tasks and for 8,000 tasks. Interval estimation makes sampling uncertainty explicit.

## Interpreting a confidence interval correctly

Given the sampling process and model assumptions, if you repeatedly sampled and constructed 95% intervals with the same method, about 95% of those intervals would cover the fixed population parameter in the long run. For one already computed frequentist interval, do not say that the parameter has a 95% probability of lying inside it.

With a known population standard deviation and approximately normal data, an interval for a mean has the form:

$$\bar{x}\pm z_{1-\alpha/2}\frac{\sigma}{\sqrt n}$$

In practice $\sigma$ is often unknown, small-sample means use a *t* distribution, and binary proportions need an appropriate method. Do not mechanically apply $\pm1.96SE$ to every metric.

## Bootstrap intuition

Treat the observed sample as an approximate population. Draw same-size samples from it **with replacement** and recompute the statistic; the many resampled statistics approximate its sampling distribution.

If the direction is defined as “B relative to A,” a paired A/B evaluation must resample the per-task differences $d_i=B_i-A_i$, not A and B separately:

$$\bar d=\frac{1}{n}\sum_i d_i$$

This course uses a simple percentile-bootstrap interval. It is not universally optimal for every statistic or small sample. Bootstrap still relies on the original sample being representative and on choosing the correct resampling unit. Repeating 20 same-type questions 10,000 times does not create evidence for the full task space.

## Hypothesis testing

1. Define a null hypothesis $H_0$ and an alternative hypothesis.
2. Select a statistic and significance level $\alpha$ in advance.
3. Under $H_0$ and its assumptions, calculate the probability of data at least as extreme as the observed data: the *p*-value.
4. If the *p*-value is below the threshold, reject $H_0$; otherwise, **fail to reject** it. That is not acceptance of the null or proof of equality.

A *p*-value is neither $P(H_0\mid data)$ nor the probability that the result “was caused by chance.”

A Type I error rejects a true null hypothesis; when the method's assumptions hold, the chosen $\alpha$ controls its long-run probability. A Type II error fails to reject a false null; its complement is power. Sample size, true effect, noise, design, and multiple comparisons all affect these errors. A *p*-value from one experiment is not itself an error-probability guarantee.

## Effect size, interval, and practical value

Moving from 80.0% to 80.2% can be statistically significant with a very large sample while not paying for the added cost. Report at least the absolute difference, relative difference when meaningful, confidence interval, sample size, stratified results, latency or cost, and failure types.

## Multiple comparisons

Trying 20 prompts and reporting only the best one with *p* < 0.05 raises the chance of a chance “discovery.” Pre-register primary metrics and comparisons, or apply a multiple-comparison correction, and keep the full experiment record. Repeatedly peeking at results and stopping as soon as they become significant also invalidates nominal error rates.

## ML and RAG evaluation contexts

- Compare two retrievers on the same query set and preserve per-query metrics for paired analysis.
- For human-scored generated outputs, account for grader differences and the clustered structure of repeated generations for one task.
- Inspect task categories in addition to the overall metric; an aggregate improvement can conceal a regression in a critical subgroup.
- A benchmark repeatedly used for tuning becomes contaminated as a test set; an interval cannot repair that bias.

## Common mistakes, exercises, and self-check

- A narrow interval does not mean an estimate is unbiased; biased sampling can produce a very stable wrong estimate.
- “Not significant” can mean too little data, not equivalence; equivalence requires a pre-specified acceptable difference and an appropriate test or interval.
- Selecting a metric after seeing results inflates the evidence.

Exercise: an A/B difference is 2 percentage points with a 95% interval of `[-1, 5]`. The appropriate conclusion is that the data are compatible with a small regression through a moderate improvement; the present data do not establish the direction. Do not claim a “95% probability of improvement.”

- [ ] I can interpret confidence intervals and *p*-values correctly.
- [ ] I consider effect size and engineering cost together.
- [ ] I understand the risks of multiple comparisons and test-set contamination.

## References

[NIST Confidence Intervals](https://www.itl.nist.gov/div898/handbook/prc/section1/prc14.htm), [Tests/Intervals Relationship](https://www.itl.nist.gov/div898/handbook/prc/section1/prc15.htm), and the [ASA Statement on Statistical Significance and P-Values](https://www.amstat.org/asa/files/pdfs/P-ValueStatement.pdf), checked on **2026-07-14**. Previous: [[probability-and-statistics/expectation-variance-and-sampling|Expectation, variance, and sampling]] | Next: [[probability-and-statistics/evaluation-design-effect-size-and-statistical-pitfalls|Evaluation design, effect sizes, and statistical pitfalls]].

