---
title: "Project: Agent Evaluation Uncertainty"
tags:
  - ai-agent-engineer
  - probability-and-statistics
  - integrated-practice
aliases:
  - Paired bootstrap project
source_checked: 2026-07-14
source_baseline:
  - NIST Bootstrap Plot and Percentiles
  - Efron 1979 bootstrap paper
  - Python 3.14.6 statistics and random documentation
lang: en
translation_key: 概率统计/05-项目-Agent评测不确定性.md
translation_source_hash: c834f6cce94ed1e900876490953990ca7ff9cc57bc8143ce45a6a5b60be82019
translation_route: zh-CN/概率统计/05-项目-Agent评测不确定性
translation_default_route: zh-CN/概率统计/05-项目-Agent评测不确定性
---

# Project: Agent Evaluation Uncertainty

## Project objective

Compare paired binary A/B scores for the same 12 tasks. Report the mean difference $B-A$ and a 95% percentile-bootstrap interval. Verify the direction, pairing, input boundaries, quantile method, and reproducibility, then explain the result with its evidence boundary.

Implementation: [[probability-and-statistics/examples/bootstrap_eval.py|bootstrap_eval.py]] | Tests: [[probability-and-statistics/examples/test_bootstrap_eval.py|test_bootstrap_eval.py]].

## Input contract

- Each $(A_i, B_i)$ pair belongs to the same unique task; do not scramble its order.
- Scores can only be `0` or `1`; 1 means that the output passes a pre-frozen grading rule.
- Twelve tasks are a teaching sample, not a claim to represent all Agent traffic.
- The difference direction is fixed as $d_i=B_i-A_i$; a positive value favors B.
- The bootstrap resampling unit is a **task difference**, not an individual A/B score or a row produced by a previous bootstrap draw.

## Method, step by step

1. Calculate the per-task difference $d_i=B_i-A_i$.
2. Draw 12 of those differences with replacement and calculate their mean.
3. Repeat this 10,000 times to form an empirical distribution of bootstrap statistics.
4. Use R7-style linear interpolation for the 2.5% and 97.5% quantiles.
5. Report the observed mean difference, interval, task count, repeat count, random seed, and method name.

This is a simple **paired percentile bootstrap**. Quantile conventions differ, and a percentile interval is not optimally suited to every statistic or small sample. The project builds resampling intuition; it does not present the method as a general statistical conclusion.

A fixed random seed only makes the Monte Carlo resampling reproducible. It does not increase task representativeness, grading reliability, or causal evidence. Raising `repeats` reduces simulation error only; it does not turn 12 tasks into a larger real sample.

## Run and test

From the project root:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B -W error '.\docs-EN\probability-and-statistics\examples\bootstrap_eval.py'
python -B -W error -m unittest discover `
    -s '.\docs-EN\probability-and-statistics\examples' `
    -p 'test_*.py' `
    -v
```

The script is expected to print:

```text
method=paired-percentile-bootstrap
tasks=12 repeats=10000 seed=20260714
A mean=0.583
B mean=0.833
B-A=0.250
confidence=0.950 interval=[-0.083, 0.583]
```

The test suite should pass eight tests covering:

- quantile endpoints, interpolation, and invalid inputs;
- degenerate cases where all pairs tie or B wins all pairs;
- reproducibility of fixed data, direction, and seed; and
- invalid scores, empty samples, repeat counts, confidence levels, and seeds.

> [!success] Verified on 2026-07-14
> With Python 3.11.9, the script produced the same result in normal mode and with `python -O`; all eight `unittest` tests passed. Both Python files also passed `py_compile`. The verification cache was removed afterward and is not kept as course content.

## Reading the code step by step

1. `PAIRED_SCORES` preserves A/B correspondence for each task.
2. `linear_quantile` sorts values and linearly interpolates at position $(n-1)p$; it rejects empty values, out-of-range probabilities, and non-finite values.
3. `_validate_pairs` explicitly rejects non-binary scores and malformed pairs.
4. `paired_bootstrap` computes observed differences first, then samples those differences with replacement.
5. `BootstrapResult` keeps method parameters and results together in one immutable record.
6. The tests cover edge cases rather than only checking that the script prints.

## Interpreting the result

The example observes B ahead of A by `0.25`, or 25 percentage points, but its interval is approximately `[-0.083, 0.583]`, which crosses zero. For this design, a faithful statement is:

> On these 12 preselected tasks, B's mean binary-score difference relative to A is +0.25; the paired percentile-bootstrap 95% interval is approximately [-0.083, 0.583]. The interval permits both a small regression and a large improvement, so this sample does not establish the direction. It approximates only uncertainty from sampling the current tasks; task representativeness, grading error, and generation stochasticity are not covered.

Do not write that “B has a 95% probability of being better,” and do not recommend release merely because the point estimate is positive. Even when an interval does not cross zero, compare it with the pre-specified minimum practically important difference, latency, cost, and safety guardrails.

## Required extensions

1. **The repeated-sample trap**: mechanically copy each task 20 times, observe the falsely narrower interval, and explain why more rows do not mean more independent information.
2. **Stratified reporting**: add `retrieval` and `tool-use` labels to tasks and report sample size, point estimate, and interval for each; do not select only the strongest stratum.
3. **Real sample size**: add new unique tasks that represent the target population rather than only increasing bootstrap repeats.
4. **Generation hierarchy**: generate five outputs for A and B for each task, define the estimand first, then choose task-level aggregation or hierarchical resampling.
5. **Engineering decision**: report latency and cost as well, and define the minimum practical improvement and guardrail thresholds needed for release.
6. **Method sensitivity**: when comparing quantile conventions or interval methods, document the implementation and difference instead of selecting only the narrowest interval.

## Common errors

- Resampling A and B separately, which destroys same-task pairing.
- Ignoring a wide interval because B–A is positive.
- Treating `repeats=100000` as 100,000 real tasks.
- Treating copied tasks, repeated generations, or grader scores as independent samples.
- Changing the random seed until the interval looks more favorable.
- Removing timeouts, failures, or “outlier tasks” after the fact without reporting the exclusion rule.
- Calling a percentile interval an assumption-free, universally accurate 95% guarantee.

## Self-check and mastery standard

- [ ] I can explain sampling with replacement and why every draw still contains 12 differences.
- [ ] I did not shuffle A and B separately, and I can state the difference direction.
- [ ] I report the point estimate, interval, sample size, method, repeat count, and seed.
- [ ] I know that quantile algorithms differ and that percentile bootstrap has applicability limits.
- [ ] I do not use bootstrap as a repair for selection bias or correlated samples.
- [ ] I can list four uncovered uncertainties: task sampling, generation, grading, and the production distribution.
- [ ] I connect the statistical result to the minimum practically important difference, latency, cost, and safety guardrails.

Previous: [[probability-and-statistics/evaluation-design-effect-size-and-statistical-pitfalls|Evaluation design, effect sizes, and statistical pitfalls]] | After completing the project, return to [[probability-and-statistics/00-index|Probability and Statistics]].

## References

Sources checked on **2026-07-14**.

- [NIST: Bootstrap Plot](https://www.itl.nist.gov/div898/handbook/eda/section3/bootplot.htm)
- [NIST: Percentiles](https://www.itl.nist.gov/div898/handbook/prc/section2/prc262.htm)
- [Efron (1979), Bootstrap Methods: Another Look at the Jackknife](https://doi.org/10.1214/aos/1176344552)
- Python [`statistics`](https://docs.python.org/3/library/statistics.html)
- Python [`random`](https://docs.python.org/3/library/random.html)
