---
title: "Training, Validation, and Hyperparameter Tuning"
tags:
  - ai-agent-engineer
  - machine-learning
aliases:
  - Model Training and Cross-Validation
source_checked: 2026-07-22
lang: en
translation_key: 机器学习/04-训练验证与调参.md
translation_source_hash: 34c027a95892f4e5634a892b5c887e0d8b927d2c93776cd108094762c9ce3773
translation_route: zh-CN/机器学习/04-训练验证与调参
translation_default_route: zh-CN/机器学习/04-训练验证与调参
---

# Training, Validation, and Hyperparameter Tuning

## Three things that can change

- **Parameter**: a weight learned from examples by the training algorithm.
- **Hyperparameter**: a setting selected before training, such as regularization strength, tree depth, or TF-IDF n-gram range.
- **Decision threshold**: a boundary that converts probability to action, such as blocking only when risk probability exceeds 0.8.

The training set learns parameters; validation chooses hyperparameters and thresholds; the test set performs final evaluation only.

## Baselines come before tuning

For classification, retain at least three comparisons:

1. A majority-class or random baseline, to confirm the model actually learned information.
2. An interpretable rule baseline, representing the current business approach.
3. A simple-model baseline, such as TF-IDF plus logistic regression.

If a complex model is only slightly better than a baseline but slower, more expensive, and harder to monitor, it may not be worth deploying.

## The intuition behind cross-validation

K-fold cross-validation partitions the training region into K parts: each part validates once while the remainder trains, then results from K runs are aggregated. It reduces accidental variation from one random split, but cannot repair leakage, duplicate examples, or a wrong grouping unit.

Tune over a **small, justified space**. The more combinations you try, the more likely you are to match validation noise by chance. Record the data snapshot, split rule, code version, dependency version, random seed, parameters, and all metrics.

Without an independent validation set, cross-validate inside the training region and select the solution from that result. Group- or time-dependent data must carry the corresponding constraint into every fold. More rounds of model selection also make cross-validation means subject to selection bias, so the final conclusion still comes from a sealed test set or a new time/source window.

## A threshold is not a natural law fixed at 0.5

Probability models often default to 0.5 as a classification threshold, but a real system should choose based on error cost. For example, a high-risk tool call may prefer more human reviews over missing an unauthorized action; that favors high recall. Choose a threshold only in the validation region, then confirm it on test data.

Calibration and threshold selection are separate questions. Calibration asks, “Among examples given 0.8, are about 80% positive in the long run?” A threshold decides where an action triggers. If a calibrator is used, fit it only on data outside the final test set and close to the deployment population. Small, skewed calibration sets especially produce unstable curves.

## What learning curves can answer

Plot training-example count against training/validation score:

- Both are low: features are insufficient, the model is too simple, or labels contain no learnable signal.
- Training is high and validation low: high variance/overfitting; add data, regularize, or simplify the model.
- Validation keeps improving with more examples: collecting high-quality data may help.

## Exercise

Design no more than eight tuning configurations to compare `ngram_range` and regularization strength. State the primary metric, secondary metric, group-split rule, and stopping condition for further experiments.

## Mastery checklist

- [ ] I can distinguish parameters, hyperparameters, and thresholds.
- [ ] I can explain why cross-validation may happen only inside the training region.
- [ ] I can use a learning curve to propose a next step rather than blindly enlarging a model.

Next: [[machine-learning/05-overfitting-and-generalization|Overfitting and Generalization]].

## References

Review date: **2026-07-22**.

- [scikit-learn: Tuning the hyper-parameters](https://scikit-learn.org/stable/modules/grid_search.html)
- [scikit-learn: Learning curve](https://scikit-learn.org/stable/modules/learning_curve.html)
- [scikit-learn: Tuning the decision threshold](https://scikit-learn.org/stable/modules/classification_threshold.html)
- [scikit-learn: Probability calibration](https://scikit-learn.org/stable/modules/calibration.html)
