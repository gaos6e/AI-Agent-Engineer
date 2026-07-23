---
title: "Probability, Conditional Probability, and Bayes' Rule"
tags: [ ai-agent-engineer, probability-and-statistics ]
aliases: [ Conditional probability and Bayes' rule ]
lang: en
translation_key: 概率统计/01-概率条件概率与贝叶斯.md
translation_source_hash: 65b1fd7eb5b6cb5ebabcb9c1a176ac8f2b8aba7f51c0349791f56f19a2b0a799
translation_route: zh-CN/概率统计/01-概率条件概率与贝叶斯
translation_default_route: zh-CN/概率统计/01-概率条件概率与贝叶斯
---

# Probability, Conditional Probability, and Bayes' Rule

## Why it matters

An Agent tool can fail, a classifier can raise a false alert, and a retrieved result can be relevant. Probability is not merely subjective vagueness; it is a model that assigns a number from 0 to 1 to an uncertain event.

## Events and basic rules

The sample space $\Omega$ contains every possible outcome, and an event $A$ is a subset of it. Probability obeys $0\le P(A)\le1$ and $P(\Omega)=1$. The complement rule is:

$$P(\neg A)=1-P(A)$$

If two events are mutually exclusive, $P(A\cup B)=P(A)+P(B)$. In general, subtract the overlap:

$$P(A\cup B)=P(A)+P(B)-P(A\cap B)$$

For example, 12 out of 100 tool calls time out, so the observed timeout rate is $12/100=0.12$. That is a sample estimate, not an eternal truth.

## Conditional probability and independence

Once you know that $B$ occurred, the probability of $A$ is:

$$P(A\mid B)=\frac{P(A\cap B)}{P(B)},\quad P(B)>0$$

Only when $P(A\mid B)=P(A)$ are $A$ and $B$ independent. Requests from the same user, service-incident window, or document are often not independent. Treating them as independent samples understates uncertainty.

For example, monitoring shows a 5% overall failure rate and a 15% failure rate during peak hours. Once you know it is a peak-hour request, use 15%, not the overall 5%.

## Bayes' rule

$$P(H\mid E)=\frac{P(E\mid H)P(H)}{P(E)}$$

Here $H$ is a hypothesis and $E$ is evidence. $P(H)$ is the prior, $P(E\mid H)$ is the probability of the evidence if the hypothesis is true, and $P(H\mid E)$ is the updated posterior.

Suppose only 1% of production requests are truly anomalous. An alert has 90% recall for anomalies and a 5% false-positive rate for normal requests. Given an alert, the probability that the request is truly anomalous is:

$$\frac{0.90\times0.01}{0.90\times0.01+0.05\times0.99}\approx0.154$$

That is about 15.4%, not 90%. A low base rate means most alerts can be false positives. This matters in security detection, hallucination alerts, and anomaly monitoring.

## Uses in ML, retrieval, and evaluation

- A classification model's reported “probability” needs calibration before it can be interpreted as a frequency; a softmax value is not automatically trustworthy.
- In RAG, “a relevant document was retrieved” changes the conditional probability of a correct answer, but the two are not the same event.
- Stratifying an offline evaluation by task category compares success rates under different conditions.
- Do not blindly multiply success rates across a multi-step Agent unless step failures are approximately independent.

## Common mistakes

- Treating $P(A\mid B)$ as $P(B\mid A)$.
- Treating uncorrelated variables as independent; zero covariance does not always imply independence.
- Using a training-set frequency as a production probability while ignoring distribution shift.
- Seeing a correlation and claiming causation.

## Exercises and self-check

1. A tool succeeds with probability 0.8 on one call. If two calls are independent, what is the probability that at least one succeeds? Answer: $1-0.2^2=0.96$. Explain when the independence assumption fails.
2. Draw a 2×2 table for 1,000 requests—truly anomalous/normal by alerted/not alerted—and recompute the Bayes example.

- [ ] I can explain conditional probability with frequencies.
- [ ] I check an independence assumption rather than assuming it.
- [ ] I can explain how base rates affect alert reliability.

## References

[NIST Probability Distributions](https://www.itl.nist.gov/div898/handbook/eda/section3/eda36.htm), checked on **2026-07-14**. Previous: [[probability-and-statistics/descriptive-statistics-and-data-quality|Descriptive statistics and data quality]] | Next: [[probability-and-statistics/random-variables-and-common-distributions|Random variables and common distributions]].

