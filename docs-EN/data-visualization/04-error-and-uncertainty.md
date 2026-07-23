---
title: "Error and Uncertainty"
tags:
  - ai-agent-engineer
  - data-visualization
aliases:
  - Uncertainty Visualization
source_checked: 2026-07-14
source_baseline:
  - NIST SEMATECH binomial-proportion confidence-interval guidance
  - Matplotlib 3.11.0 errorbar and fill-between documentation
lang: en
translation_key: 数据可视化/04-误差与不确定性.md
translation_source_hash: 93c36a523385b25eb2fa533d93435ec0d1cd64a614a108369e3aee7c1eda6927
translation_route: zh-CN/数据可视化/04-误差与不确定性
translation_default_route: zh-CN/数据可视化/04-误差与不确定性
---

# Error and Uncertainty

## Objectives

Distinguish observational spread, mean estimation, binomial proportions, and variation across runs. Be able to write the denominator, unit of repetition, and calculation method for an error bar, and recognize pseudoreplication and removed failures.

## State what an error bar represents

An error bar can represent standard deviation, standard error, a confidence interval, min–max, or a range across random seeds; these have different meanings. A caption must state the statistic, sample count, repetition unit, and calculation method.

- Standard deviation describes the spread of individual observations.
- Standard error describes uncertainty in a sample-mean estimate and depends on an independence assumption.
- A confidence interval comes from a stated statistical model or resampling method. In a frequentist interpretation, it does not mean “the true parameter has a 95% probability of lying in this particular interval.”
- A range from repeated model runs includes both training randomness and evaluation-sampling uncertainty; state the experimental design.

One error bar cannot automatically cover every uncertainty source. Agent evaluation commonly involves task sampling, model/temperature randomness, infrastructure variability, annotator disagreement, and data drift. First choose whether the inferential unit is a task, user, day, or random seed; then choose an interval. Treating multiple conversations from the same user as completely independent samples creates pseudoreplication and makes an interval falsely narrow.

## Binomial proportions: avoid boundary errors from symmetric normal intervals

The simple approximation `p ± 1.96*sqrt(p(1-p)/n)` for a success/failure proportion can be unreasonable with small samples or values near 0/1. It can even produce a zero-width interval for `0/n` or `n/n`. This knowledge base uses the Wilson score interval. Let $\hat p=x/n$ and use $z\approx1.96$ for a 95% interval:

$$
c=\frac{\hat p+z^2/(2n)}{1+z^2/n},\qquad
h=\frac{z\sqrt{\hat p(1-\hat p)/n+z^2/(4n^2)}}{1+z^2/n}
$$

The interval is $[c-h,c+h]$, clipped to $[0,1]$. For example, the Wilson 95% upper bound for `0/10` is about 27.8%, not 0%. It reminds readers that “no failures were observed” does not mean “the failure rate has been proven to be 0.” The interval still relies on assumptions such as binomial outcomes and independence; it does not substitute for task stratification or experiment design.

## Paired comparisons are better than two independent means

If v1 and v2 are evaluated on the same tasks, plot each task's difference or paired line. That directly shows which tasks improved or regressed, and reduces interference from differences in task difficulty.

## Sample size for proportions

A 100% success rate has different evidence strength for `1/1` and `1000/1000`. Show `successes / total` or an interval so a small-sample point does not appear as certain as a large-sample point. Guard against very small denominators especially after stratifying by category.

## Missingness and censoring

A timeout is not ordinary missing data. Removing timed-out runs from a latency chart systematically beautifies the result. You can plot timeout rate separately and show latency distribution for completed runs, interpreting both together.

## Exercise

Design a caption for a model comparison with “five random seeds × a fixed set of 200 tasks.” State what the points, error bars, and sample units are. Then explain why treating 1,000 results as fully independent may be unreasonable.

Suggested caption: “Points are mean end-to-end success rate across five random seeds; error bars show the between-seed range (or prespecified SD/CI); every seed is evaluated on the same frozen set of 200 tasks.” The same 200 tasks repeat for each seed and may cluster by user/topic, so 1,000 results are not 1,000 independent tasks. Show each seed's result and task-paired differences as well.

## Mastery check

- [ ] I can distinguish SD, SEM, confidence intervals, random-seed range, and quantiles.
- [ ] In a caption I state the statistic, `n`, repetition unit, pairing relationship, and calculation method.
- [ ] I can calculate/check a Wilson interval and explain why `0/10` does not mean zero uncertainty.
- [ ] I explain task sampling, model randomness, infrastructure, and annotation disagreement in layers.
- [ ] I do not remove timeouts and then draw error bars only for completed runs.

Next: [[data-visualization/05-machine-learning-rag-and-agent-evaluation-charts|Machine Learning, RAG, and Agent Evaluation Charts]].

## References

Sources were checked on 2026-07-14. Wilson formulas and terminology were checked against the NIST/SEMATECH handbook; Matplotlib APIs were checked against 3.11.0 documentation.

- [NIST: Confidence intervals for a binomial proportion](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm)
- [Matplotlib `errorbar`](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.errorbar.html)
- [Matplotlib `fill_between`](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.fill_between.html)
