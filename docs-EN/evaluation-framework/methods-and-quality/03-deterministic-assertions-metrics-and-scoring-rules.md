---
title: "Deterministic Assertions, Metrics, and Scoring Rules"
aliases:
  - Deterministic Graders and Rubrics
tags:
  - evaluation
  - metrics
source_checked: 2026-07-14
lang: en
translation_key: 评测体系/02-方法与质量/03-确定性断言指标与评分规则.md
translation_source_hash: 15d42634664d14c87782217fc2a73d0d5e7351dc555c22dbd72ae44228b7f8b6
translation_route: zh-CN/评测体系/02-方法与质量/03-确定性断言指标与评分规则
translation_default_route: zh-CN/评测体系/02-方法与质量/03-确定性断言指标与评分规则
---

# Deterministic Assertions, Metrics, and Scoring Rules

## Goal

Write deterministic graders for objective conditions, clear rubrics for subjective quality, and prevent a total score from concealing a critical failure.

## Intuition

Let programs verify facts that are decidable, then let people or models assess qualities that need interpretation. Sending every question to one subjective judge increases cost, variation, and debugging difficulty.

## Check decidable facts first

Code can reliably determine whether JSON parses, required fields exist, tool names and parameters are correct, database state changed, cited URLs belong to an allowed set, output exceeds a limit, or a sensitive string appears. Deterministic checks are inexpensive, reproducible, and easy to localize, so they should precede model grading.

Do not overfit to exact-string matching. Amounts such as `96.12` and `96.120`, valid JSON with a different key order, and multiple correct solution paths need normalization or a semantically appropriate assertion.

## Applicability boundaries for scoring methods

| Method | Well suited to | Main boundary |
| --- | --- | --- |
| Deterministic code or tests | Schema, tool parameters, state, permissions, numeric constraints | Can hard-code legitimate variants |
| Rules and heuristics | Format, length, keywords, known risk patterns | Easily bypassed; a proxy signal is not the objective |
| Human review | Domain correctness, real utility, high-risk adjudication | Slow, costly, subject to disagreement and fatigue |
| Model grader | Large-scale classification or pairwise comparison with a clear rubric | Nondeterministic and biased; needs human calibration |
| Trace grading | Tool choice, parameters, loops, evidence use, policy adherence | Missing or sampled traces limit conclusions; cannot replace outcomes |

Choose the method closest to the real success condition, most reproducible, and affordable enough; combine methods when needed. Trace grading explains process, while environment state verifies result. Neither substitutes for the other.

## Minimal intuition for common metrics

For binary classification:

$$
Precision=\frac{TP}{TP+FP},\qquad Recall=\frac{TP}{TP+FN}
$$

TP, FP, TN, and FN are true positives, false positives, true negatives, and false negatives. Together, the four cells form the **confusion matrix**. F1 is the harmonic mean of precision and recall:

$$
F1=2\frac{Precision\times Recall}{Precision+Recall}
$$

Prioritize precision when false positives are expensive and recall when false negatives are expensive. F1 does not automatically express their different business costs. Accuracy can look inflated under severe class imbalance. When a denominator is zero, report the metric as undefined rather than silently filling in 0 or 1.

For continuous quantities, distinguish the mean from the distribution. Average latency can be pulled by very slow values while hiding tail-user experience; p95 means approximately 95% of observations do not exceed that value, not “the average of the slowest 5%.” Report mean, p50/p95, sample count, and the outlier rule together. String similarity can assist generation regression checks, but alone does not prove factual correctness or user utility.

## Writing a rubric

Break “answer quality from 1 to 5” into independent dimensions with anchors:

| Dimension | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Factual support | Contradicts evidence | Partially supported but misses a critical item | Every critical conclusion is supported |
| Completeness | Does not answer | Completes part of the objective | Completes every explicit objective |
| Risk | Performs a prohibited action | Has uncertain risk | No prohibited action and boundaries are clear |

Have the grader return each dimension's score, evidence, and `Unknown`, rather than one overall impression.

## Aggregation and gates

Define critical assertions first: unauthorized action, disclosure, and destructive error make a trial fail when any one occurs. Other dimensions can be weighted by business cost or receive partial credit, but weights must be frozen before candidate results are viewed. Report both the total score and each distribution, failure case, and sample count.

One reasonable structure is:

```text
pass = critical_assertions_all_pass
quality = 0.5 * correctness + 0.3 * completeness + 0.2 * style
ship = pass AND quality >= frozen_threshold
```

## Prevent scorers from being gamed

If a check only looks for the phrase “completed,” an Agent can score without operating the environment. If it only rewards short latency, it can skip a necessary check. A grader must inspect the real outcome and include adversarial cases that try to bypass the rule. Anthropic's guidance specifically warns that grader bugs, ambiguous tasks, and reward hacking can distort scores.

As of 2026-07-14, OpenAI's Graders page still listed string checks, text similarity, score models, and Python execution, but the same page explicitly says graders are in a deprecation transition with the Evals/fine-tuning workflow; the Evals dashboard and API are planned to close on 2026-11-30. This section uses those categories to explain methods, not their JSON configuration as a production entry point to create.

## Common mistakes and diagnostics

- Exact matching rejects equivalent answers: parse types first and normalize.
- A rubric only says “poor / fair / good”: give observable anchors and counterexamples for every level.
- Risk and style are averaged together: make unacceptable risk a gate.

## Exercises

1. Write three deterministic assertions for “create a ticket”: fields, target project, and final existence state.
2. Split “the answer is professional” into three observable dimensions and anchors.

## Self-check

When should metrics not be averaged? When a risk is a hard threshold or units and business losses are not exchangeable.

## Summary and next step

Continue to [[evaluation-framework/methods-and-quality/04-human-review-and-model-based-evaluation|Human Review and Model-Based Evaluation]].

## References

- [OpenAI Evaluation best practices: evaluator types](https://developers.openai.com/api/docs/guides/evaluation-best-practices) — checked 2026-07-14.
- [OpenAI Graders](https://developers.openai.com/api/docs/guides/graders) — checked 2026-07-14; the page explicitly sits in a deprecation transition.
- [OpenAI API Deprecations](https://developers.openai.com/api/docs/deprecations) — checked 2026-07-14; Evals retirement timeline.
- [Anthropic: Design graders thoughtfully](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — published 2026-01-09; checked 2026-07-14.
- [NIST/SEMATECH: Confidence intervals](https://www.itl.nist.gov/div898/handbook/prc/section1/prc14.htm) — checked 2026-07-14.
