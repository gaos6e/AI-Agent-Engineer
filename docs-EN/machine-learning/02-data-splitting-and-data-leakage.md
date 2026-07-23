---
title: "Data Splitting and Data Leakage"
tags:
  - ai-agent-engineer
  - machine-learning
aliases:
  - Train Validation Test
  - Data Leakage
source_checked: 2026-07-22
lang: en
translation_key: 机器学习/02-数据划分与数据泄漏.md
translation_source_hash: d3d67d63e367004ebf2e4cfcbfc2a375232ab2fe4733ef40541bb048eed57259
translation_route: zh-CN/机器学习/02-数据划分与数据泄漏
translation_default_route: zh-CN/机器学习/02-数据划分与数据泄漏
---

# Data Splitting and Data Leakage

## Why split data?

Training error answers, “How well did the model fit data it already saw?” What actually matters is **generalization**: whether it still works on future, unseen examples. That requires mutually isolated data:

- **Training set**: fit model parameters and every preprocessor that learns from data.
- **Validation set**: choose features, model, hyperparameters, and decision threshold.
- **Test set**: make one final estimate after the solution is locked; it does not participate in selection.

When examples are scarce, use cross-validation inside the training region. The test set remains sealed.

## What data leakage is

Whenever training sees information unavailable in real deployment, offline scores become artificially high. Typical leakage includes:

- Imputing missing values from the mean of the full dataset, then splitting it.
- Letting near-duplicate slices of the same user or document enter both training and test.
- Using fields such as “handling result” or “final state” that arise after the prediction time.
- Repeatedly viewing test results and changing features accordingly; the test set has then become a validation set.
- In RAG evaluation, mechanically generating questions from the same corpus passage so answer phrasing directly reveals the source.

The key rule is: `fit` may happen only on training data; validation/test may only call `transform` and `predict`.

## A random split is not always correct

| Data relationship | Recommended split | Why |
| --- | --- | --- |
| independent and identically distributed data, stable classes | stratified random split | preserves class proportions |
| multiple records for one user | group by user | prevents identity features leaking across sets |
| time series or future production data | split earlier versus later time | simulates the real future |
| a document split into chunks | group by original document | prevents near-duplicate passages from leaking |

`random_state` reproduces an experiment, but fixed randomness cannot repair faulty split logic.

When groups exist and class proportions should remain as stable as possible, use `StratifiedGroupKFold` in the training region. It prioritizes non-overlapping groups and only **tries** to preserve class proportions under that constraint; with too few groups or very skewed distributions, both are impossible simultaneously. For time data, `TimeSeriesSplit` prevents “train on the future, evaluate on the past,” but comparability still depends on sample interval and business-window definitions. No splitter can automatically determine whether same-origin copies, delayed labels, or permission changes have already leaked.

## Minimal code shape

```python
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    texts,
    labels,
    test_size=0.25,
    stratify=labels,
    random_state=42,
)
```

This is a starting point for independent-example classification. Use group/time-aware strategies when users, documents, or time introduce relationships.

## Exercise

Determine whether each case leaks and explain the repair:

1. Run TF-IDF over 100,000 logs, then randomly split the vectors into train/test.
2. Randomly split multiple chunks from the same FAQ document.
3. Predict whether a ticket escalates while using its “escalation operator” field.
4. View test-set F1 after every model change until it looks satisfactory.

## Mastery checklist

- [ ] I can explain why validation and test sets are not interchangeable.
- [ ] I can choose the correct split unit for user-, document-, and time-related data.
- [ ] I can make preprocessing fit only training data through a Pipeline.

Next: [[machine-learning/03-features-and-preprocessing-pipelines|Features and Preprocessing Pipelines]].

## References

Review date: **2026-07-22**.

- [scikit-learn: Common pitfalls and recommended practices](https://scikit-learn.org/stable/common_pitfalls.html)
- [scikit-learn: Cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html)
- [scikit-learn: StratifiedGroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html)
- [scikit-learn: TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
