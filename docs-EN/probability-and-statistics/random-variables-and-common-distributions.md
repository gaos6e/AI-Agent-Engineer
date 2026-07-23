---
title: "Random Variables and Common Distributions"
tags: [ ai-agent-engineer, probability-and-statistics ]
aliases: [ Probability-distribution fundamentals ]
lang: en
translation_key: 概率统计/02-随机变量与常见分布.md
translation_source_hash: 994f5c5e9fe9530d32f83b44a966298af0129368fe8582e919f4e3025891b27d
translation_route: zh-CN/概率统计/02-随机变量与常见分布
translation_default_route: zh-CN/概率统计/02-随机变量与常见分布
---

# Random Variables and Common Distributions

## What a random variable is

A random variable maps a random outcome to a number. For example, $X=1$ can mean that an Agent succeeds and $X=0$ that it fails; latency $T$ can take any non-negative real value. A discrete variable lists probabilities, while a continuous variable uses a density to describe the probability of an interval.

## PMF, PDF, and CDF

- A discrete variable's **probability mass function (PMF)** is $p(x)=P(X=x)$; the probabilities over all possible values sum to 1.
- A continuous variable's **probability density function (PDF)**, $f(x)$, is not itself a point probability; an interval probability is an area.
- The **cumulative distribution function (CDF)** applies to either kind: $F(x)=P(X\le x)$.

Latency P95 is the smallest $t$ for which $F(t)\ge0.95$. About 95% of observations do not exceed it; it is neither the maximum nor “the average latency of 95% of requests.”

## Five common distribution models

### Bernoulli

For $X\in\{0,1\}$ with success probability $p$:

$$P(X=1)=p,\quad P(X=0)=1-p$$

This model suits whether a single task succeeds or whether a single answer passes a human judgment.

### Binomial

If $n$ Bernoulli trials are independent and share one success rate, the number of successes $K$ has:

$$P(K=k)=\binom{n}{k}p^k(1-p)^{n-k}$$

In a real evaluation, tasks can have different difficulty and outputs can be correlated, so the independent-and-identically-distributed assumption may fail. In that case, stratify, pair, or bootstrap by task.

### Categorical and multinomial

A categorical random variable takes one of $K$ mutually exclusive categories, such as a tool-routing outcome of `search`, `calculator`, or `none`; category probabilities $p_k$ satisfy $\sum_k p_k=1$. Under a fixed number of independent, identically distributed trials, the counts of each category can be described by a multinomial model.

An LLM softmax vector is often treated as a categorical distribution, but whether its values can be interpreted as actual frequencies still requires calibration. Real tool-call frequencies also depend on the prompt, sampling, constrained decoding, and runtime rules.

### Poisson

The Poisson distribution is often used for counts in a fixed exposure, such as tool timeouts per hour. Its parameter $\lambda$ is both the expectation and variance in the idealized model. It assumes events are approximately independent at a stable rate. Production data frequently has peaks, incident clusters, and user differences that make its variance exceed its mean. A count is not automatically Poisson just because it is a count.

### Normal

A normal distribution is symmetric and is described by mean $\mu$ and standard deviation $\sigma$. Many sample means are approximately normal under suitable conditions, but one-off latencies and token use can be skewed or long-tailed. Do not assume normality merely because a mean and variance exist.

Standardization is:

$$z=\frac{x-\mu}{\sigma}$$

It states how many standard deviations $x$ lies from the mean. In anomaly detection, a threshold relies on a stable distribution; after distribution drift, an old *z*-score can mislead.

## Empirical distributions

Engineering work need not begin by fitting a theoretical distribution. Ordered observations form an empirical CDF, from which you can directly calculate median, P90, P95, and P99. For long-tailed API latency, quantiles often reveal tail experience more clearly than a mean.

With the Python standard library:

```python
from statistics import mean, median, quantiles

latencies = [120, 125, 130, 140, 900]
print(mean(latencies), median(latencies))
print(quantiles(latencies, n=100, method="inclusive")[94])
```

A high quantile from a small sample is extremely unstable. Do not treat P99 computed from five values as precise SLA evidence.

## Uses and pitfalls

- Sampling in a generative model produces an output distribution. Temperature changes its shape; it is not a “correctness knob.”
- Benchmark pass counts can resemble Bernoulli or binomial observations, but task heterogeneity needs additional treatment.
- Retrieval-similarity score distributions change with the model, corpus, and query type, so thresholds are not directly comparable across systems.

Common misconceptions: a density can exceed 1 while its total area remains 1; a normal distribution supports negative values and therefore should not be fitted uncritically to non-negative, long-tailed latency; and “random” does not mean “patternless.”

## Exercises and self-check

1. Choose a variable type and a presentation for success rate, latency, and tokens per request.
2. Compare the mean and median of `[10, 11, 12, 13, 100]`, and explain the outlier's effect.

- [ ] I can distinguish probability, density, and cumulative probability.
- [ ] I know the assumptions behind Bernoulli and binomial models.
- [ ] I do not overinterpret P99 from a small sample.

## References

[NIST Distribution Gallery](https://www.itl.nist.gov/div898/handbook/eda/section3/eda366.htm), checked on **2026-07-14**. Previous: [[probability-and-statistics/probability-conditional-probability-and-bayes|Probability, conditional probability, and Bayes' rule]] | Next: [[probability-and-statistics/expectation-variance-and-sampling|Expectation, variance, and sampling]].

