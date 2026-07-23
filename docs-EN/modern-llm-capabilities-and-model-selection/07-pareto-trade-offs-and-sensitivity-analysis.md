---
title: "Pareto Trade-offs and Sensitivity Analysis"
tags:
  - llm
  - pareto
  - decision-analysis
aliases:
  - Multi-objective model-selection decisions
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
lang: en
translation_key: 现代LLM能力与模型选择/07-Pareto权衡与敏感性分析.md
translation_source_hash: 3ea4629e7012922b7d95622975839678d1a95c36dc31d63d430e57cf1a2646b6
translation_route: zh-CN/现代LLM能力与模型选择/07-Pareto权衡与敏感性分析
translation_default_route: zh-CN/现代LLM能力与模型选择/07-Pareto权衡与敏感性分析
---

# Pareto Trade-offs and Sensitivity Analysis

## Goal

Within the candidates that pass hard gates, identify options that cannot be comprehensively outperformed and test whether a conclusion depends on fragile weights.

## Core concepts

If candidate A is no worse than B on every metric that matters and is better on at least one, A **dominates** B. The candidates that no other candidate dominates form the **Pareto frontier**.

A weighted score can assist ranking, but only under three conditions:

1. Compute it only for candidates that pass gates.
2. Make every metric’s direction, unit, and normalization public.
3. Keep the source, changes, and sensitivity of weights traceable.

A total score is not a natural truth. It compresses distinct value judgments into a number and cannot replace raw metrics and failed samples.

## Why this matters

High quality, low latency, and low cost usually cannot all be optimal at once. Averaging every dimension directly hides the actual choice: one candidate may be more reliable but slower, while another is cheaper but weaker on a critical slice. The Pareto frontier first removes candidates that are comprehensively worse, then lets accountable people decide among the real trade-offs.

## How to implement it

### Normalize direction, but retain raw values

Quality is better when larger; latency, cost, and failure rate are better when smaller. You can convert budget headroom to 0–1 utility, for example:

```text
latency_headroom = max(0, 1 - p95_latency / latency_gate)
cost_headroom = max(0, 1 - avg_cost / cost_gate)
```

At the same time, display the raw `p95_ms` and `avg_cost` values so utility does not hide units.

### Run sensitivity analysis

Prepare at least three preregistered sets of weights: baseline, quality-priority, and efficiency-priority. Record the full ranking for each set, whether the winner changes, and whether score differences are close to measurement noise. If a small weight change changes the winner, label the conclusion “preference-sensitive” rather than declaring an absolute best.

The offline project makes only a discrete comparison of these three **declared weight scenarios** and outputs `sensitivity_scope: declared_weight_sets_only`. `winner_stable_across_declared_weights=true` means only that the winner is the same at those points; it does not mean the winner is locally stable across every reasonable weight, nor does it include statistical uncertainty from trials. A production decision may additionally scan a weight range, apply local perturbations, and propagate measurement error, but it must state the method and scope.

### Produce a decision record

State the selection, reasons for rejection, residual risks, owner, validity period, model version, and reevaluation triggers. Changes to the model catalog, price, policy, or task distribution can all trigger reevaluation.

## Common failures

- Calculating total scores before gates, leaving a noncompliant candidate ranked first.
- Applying min–max normalization dynamically to the current candidates, so adding a weak candidate changes every score.
- Giving only the final score, not raw values, formulas, and weights.
- Adjusting weights after viewing results until a preferred candidate wins.
- Making a deterministic rank claim when score differences are smaller than trial variation.

## How to validate

Manually construct a candidate that is worse than another on every metric; the program must mark it dominated. Then exchange quality and efficiency weights. If the winner changes, the report must show the instability explicitly rather than outputting only the baseline rank.

## Practice task

Have three stakeholders assign weights independently, then discuss the differences. Before viewing candidate names, inspect only anonymized raw metrics, gates, and the Pareto frontier. Record the final trade-off and what new evidence would change the decision.

## References

- [HELM: multiple scenarios, metrics, and transparent evaluation](https://crfm.stanford.edu/helm/index.html)
- NIST, [AI 600-1](https://doi.org/10.6028/NIST.AI.600-1)
- Mitchell et al., [Model Cards for Model Reporting](https://doi.org/10.1145/3287560.3287596)
