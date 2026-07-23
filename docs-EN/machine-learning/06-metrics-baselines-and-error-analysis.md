---
title: "Metrics, Baselines, and Error Analysis"
tags:
  - ai-agent-engineer
  - machine-learning
aliases:
  - Machine Learning Evaluation Metrics
  - Error Analysis
source_checked: 2026-07-22
lang: en
translation_key: 机器学习/06-指标基线与误差分析.md
translation_source_hash: b9189107bb1c9f659a9d3c347e07a8f85874184e20b30bf4e2d240d368bcb0b4
translation_route: zh-CN/机器学习/06-指标基线与误差分析
translation_default_route: zh-CN/机器学习/06-指标基线与误差分析
---

# Metrics, Baselines, and Error Analysis

## Objectives

Derive classification metrics from a confusion matrix, distinguish macro/micro/weighted aggregation, choose majority-class and rule baselines, and split metrics by class, scenario, and error cost. The deliverable is not a pretty aggregate score; it is decision material containing sample size, baselines, interval boundaries, and an error list.

## Understand classification through the confusion matrix

Define “must block” as the positive class:

- TP: should block and did block.
- FP: should not block but did block.
- FN: should block but did not.
- TN: should not block and correctly passed.

$$Precision=\frac{TP}{TP+FP}$$

$$Recall=\frac{TP}{TP+FN}$$

$$F1=2\cdot\frac{Precision\cdot Recall}{Precision+Recall}$$

Precision answers, “Of actions blocked, how many were truly dangerous?” Recall answers, “Of dangerous actions, how many were blocked?” F1 is their harmonic mean, but does not directly include business cost.

## How to aggregate multiclass results

- **macro average**: compute by class first, then average with equal class weight; minority classes have equal voice.
- **weighted average**: weight by support per class; large classes can dominate.
- **micro average**: aggregate TP/FP/FN over classes first, then compute; in single-label multiclass classification, micro precision/recall/F1 equals accuracy.

Always report support for every class. A class with only two examples and F1 of 1.0 is not evidence of stability. The project uses macro F1 so one of three classes cannot be hidden by total sample count, but six test examples are still extremely few.

## Do not inspect accuracy alone

If 1% of examples carry risk, always predicting “safe” reaches 99% accuracy while providing no value. For class imbalance, report at least per-class precision/recall/F1, confusion matrix, sample count, and one simple baseline.

When ranking or choosing a threshold, inspect PR curves, ROC curves, and cost at a threshold. When probabilities guide risk decisions, inspect calibration as well: are examples predicted at 0.8 about 80% positive?

Calibration differs from discrimination. A model can rank well but be overconfident, or be globally calibrated but unable to distinguish individuals effectively. A reliability plot should report sample count and uncertainty for each bin. Brier loss reflects calibration, discrimination, and data uncertainty together; it cannot alone prove “probabilities are calibrated.” Select a threshold only in the validation region. Choosing the prettiest test-set threshold turns the test set into tuning data.

## Baselines answer “did it learn anything?”

Compare at least:

1. a majority-class or prior-proportional random dummy baseline;
2. the current human/rule workflow;
3. a simple reproducible model;
4. a more complex option only when justified.

For balanced three-class classification, the majority-class baseline is about one-third accuracy. If a complex model obtains two-thirds on one six-example test, do not deploy because it “doubled” the baseline. Inspect intervals, error types, cost, and a new time window too.

## Regression metrics

- MAE: mean absolute error, in the target's unit and relatively interpretable.
- MSE/RMSE: penalize large errors more heavily; RMSE returns to the original unit.
- $R^2$: variation explained relative to predicting the training mean. It can be negative and is not accuracy.

## Agent and RAG also need end-to-end metrics

An F1 for a routing classifier is only a component metric. A system should also inspect task-success rate, human-escalation rate, per-task cost, latency, tool errors, safety incidents, and scenario-sliced failure rate. One aggregate score cannot hide failure in critical subgroups.

## Fairness and privacy are evaluation boundaries, not one aggregate score

When a model affects people, regions, languages, devices, or business channels differently, report sample size, error rate, calibration, and human-escalation rate by relevant slice only within legal, necessary, access-controlled data boundaries. Prioritize harmful differences and their data/workflow causes. Slice definitions, threshold tradeoffs, and acceptable risk remain constrained by business, law, privacy, and affected parties in the concrete setting; equal metrics across groups alone cannot prove fairness.

Do not collect or retain sensitive attributes indefinitely merely to obtain a fairness number. If an attribute is truly necessary for risk review, minimize scope, record purpose and access rights, and review results together with data quality, representativeness, human review, and appeal/correction mechanisms. NIST AI RMF can serve as a voluntary risk-management framework, not a conclusion that an implementation complies with law in any jurisdiction.

## Error-analysis template

For every error, record:

```text
Example ID:
True label / predicted label:
Error type: FP / FN / label dispute / corrupted data
Possible cause: insufficient coverage / feature shortcut / ambiguous rule / drift
Actionable improvement: add examples, change guidance, change features, adjust threshold, or add human fallback
```

Aggregate error categories and counts first, then decide whether data, model, or workflow should change. Selecting only two “interesting cases” easily causes survivorship bias.

For repeated experiments or sampled tests, report uncertainty with [[probability-and-statistics/00-index|Probability and Statistics]]. A fixed random seed reproduces the current split; it does not make a small sample larger or cover distribution shift.

## Exercise

A risk classifier has TP=30, FP=10, FN=20, TN=940. Compute precision and recall by hand, then explain which metric should improve first when a missed block costs far more than an erroneous block.

Then complete:

1. With three-class supports of 90, 9, and 1, explain how macro and weighted F1 can tell different stories.
2. Write a majority-class baseline and a rule baseline for ticket routing, and explain the failure mode of each.
3. Write a conclusion for `accuracy=0.667, n=6` that does not overstate evidence.

## Mastery checklist

- [ ] I can compute and explain precision/recall from a confusion matrix.
- [ ] I can explain why high accuracy may be meaningless.
- [ ] I can connect component metrics to task success, cost, and safety metrics.
- [ ] I can distinguish macro, micro, weighted, and support.
- [ ] I report baselines, sample size, error examples, and uncertainty boundaries together.

Next: [[machine-learning/07-introduction-to-unsupervised-learning|Introduction to Unsupervised Learning]].

## References

Review date: **2026-07-22**.

- [scikit-learn: Metrics and scoring](https://scikit-learn.org/stable/modules/model_evaluation.html)
- [scikit-learn: Classification metrics](https://scikit-learn.org/stable/modules/model_evaluation.html#classification-metrics)
- [scikit-learn: Probability calibration](https://scikit-learn.org/stable/modules/calibration.html)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
