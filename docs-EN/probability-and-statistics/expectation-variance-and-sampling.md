---
title: "Expectation, Variance, and Sampling"
tags: [ ai-agent-engineer, probability-and-statistics ]
aliases: [ Means, variance, and sampling ]
lang: en
translation_key: 概率统计/03-期望方差与抽样.md
translation_source_hash: 4e00a850d9f02bac9d59f2075b98e289a4b0359893c055e5db9bf1a3a9af28ce
translation_route: zh-CN/概率统计/03-期望方差与抽样
translation_default_route: zh-CN/概率统计/03-期望方差与抽样
---

# Expectation, Variance, and Sampling

## Expectation: a long-run weighted average

For a discrete random variable:

$$E[X]=\sum_x xP(X=x)$$

If a successful tool call yields 10, a failure costs 4, and the success rate is 0.7, then expected utility is $0.7\times10+0.3\times(-4)=5.8$. Expectation does not mean every call returns 5.8; it is a long-run average model for many comparable trials.

## Variance and standard deviation

$$\operatorname{Var}(X)=E[(X-\mu)^2],\quad \sigma=\sqrt{\operatorname{Var}(X)}$$

Variance is in squared units; standard deviation returns to the original unit. Two Agents can have the same average score while one fails severely on occasion, giving it greater variance and tail risk. An engineering choice should not depend only on the mean.

Sample variance commonly uses $n-1$:

$$s^2=\frac{1}{n-1}\sum_{i=1}^{n}(x_i-\bar{x})^2$$

This is a common unbiased estimator of population variance. When describing the complete population currently in hand, a denominator of $n$ can be appropriate; state the context.

## Covariance and correlation

$$\operatorname{Cov}(X,Y)=E[(X-E[X])(Y-E[Y])]$$

The correlation coefficient is normalized to $[-1,1]$:

$$\rho=\frac{\operatorname{Cov}(X,Y)}{\sigma_X\sigma_Y}$$

If two Agents fail together on the same hard tasks, their outcomes are positively correlated. A paired comparison must preserve this correspondence; independently shuffling A and B scores loses information. Correlation does not establish causation, and it directly describes only linear association.

## Sampling and standard error

A population is the complete set of entities of interest, and a sample is the part actually observed. The sample mean is itself a random variable. If observations are independent and identically distributed with finite variance, its standard error is approximately:

$$SE(\bar X)=\frac{s}{\sqrt n}$$

Quadrupling the sample size roughly halves standard error; it does not reduce it by a factor of four. Large numbers of repeated or highly correlated observations do not add information at the rate of independent observations.

## Bias and variance

- **Sampling bias**: an evaluation contains only short English question-answer tasks but is generalized to long Chinese tool-use tasks.
- **Measurement bias**: a grader systematically favors one writing style.
- **Random variation**: a metric naturally varies when you draw another representative task set.

More samples can reduce random error, but they cannot repair systematic bias. Define the target population and sampling frame before discussing sample size.

## Uses in ML, retrieval, and evaluation

- A mini-batch gradient is a noisy estimate of the full gradient; batch size affects variance and cost.
- Comparing two retrievers on the same queries is a paired design and is usually more efficient than using two different query sets.
- Random assignment in an online A/B test helps reduce confounding, but you still must check exposure, missing data, and interference.
- Repeated stochastic-generation evaluations can estimate output variation; do not keep only the best run.

## A verifiable example

```python
from statistics import mean, stdev

scores = [1, 1, 0, 1, 0, 1, 1, 1]
print("mean", mean(scores))
print("sample sd", stdev(scores))
print("SE", stdev(scores) / len(scores) ** 0.5)
```

## Exercises and self-check

1. Construct two sets of 0-to-1 scores with the same mean of 0.8 and different variance.
2. Explain why an A–B difference on the same task is better suited to a paired comparison than two independently sampled group means.

- [ ] I can distinguish standard deviation from standard error.
- [ ] I know that more samples cannot remove selection bias.
- [ ] I preserve the pairing structure.

## References

[NIST Measures of Scale](https://www.itl.nist.gov/div898/handbook/eda/section3/eda356.htm) and Python [`statistics`](https://docs.python.org/3/library/statistics.html), checked on **2026-07-14**. Previous: [[probability-and-statistics/random-variables-and-common-distributions|Random variables and common distributions]] | Next: [[probability-and-statistics/estimation-confidence-intervals-and-hypothesis-testing|Estimation, confidence intervals, and hypothesis testing]].

