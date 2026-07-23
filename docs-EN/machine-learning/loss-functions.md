---
title: "Loss Functions"
tags:
  - machine-learning
  - deep-learning
  - reference
content_tier: reference
content_status: validated
content_origin: original
source_checked: 2026-07-22
source_baseline:
  - PyTorch stable loss API documentation (retrieved 2026-07-22)
lang: en
translation_key: 机器学习/损失函数.md
translation_source_hash: f30ddf41f997a0d965f0e82e550ec74d918dec51821e750c3dc1f1a3136b2d7b
translation_route: zh-CN/机器学习/损失函数
translation_default_route: zh-CN/机器学习/损失函数
---

# Loss Functions

> [!note] Content and boundary
> This page is an original English summary and formula organization based on the listed primary sources; it does not reproduce third-party tutorial prose. A loss function gives an optimizer a training signal. It is not directly equivalent to accuracy, F1, calibration, business cost, or deployment safety; assess those separately through validation/testing and error analysis.

<!-- graph-links:start -->
## Related notes

- Same-directory notes: [[machine-learning/optimizers|Optimizers]] · [[machine-learning/04-training-validation-and-hyperparameter-tuning|Training, Validation, and Hyperparameter Tuning]] · [[machine-learning/06-metrics-baselines-and-error-analysis|Metrics, Baselines, and Error Analysis]]
- Next learning: [[deep-learning/00-index|Deep Learning]]
<!-- graph-links:end -->

## Choose loss from task and output first

| Task | Model output | Label contract | Common PyTorch interface | Most common misuse |
| --- | --- | --- | --- | --- |
| single-label multiclass classification | one raw `logit` per class, commonly shape `[N, C]` | one class index per example, commonly `long` shape `[N]` | `CrossEntropyLoss` | apply `softmax` first, or treat multi-label data as single-label |
| binary / multilabel classification | one raw `logit` per target | floating labels in `[0, 1]` with the same shape as output | `BCEWithLogitsLoss` | apply `sigmoid` first and then pass it to `BCEWithLogitsLoss` |
| regression | continuous prediction | continuous target aligned with the prediction | `MSELoss`, among others | treat squared error as the only business cost |

A `logit` is the raw score before softmax/sigmoid. First determine how many true labels one example may have and the output shape, then choose loss; do not copy an interface merely because its name contains “cross entropy.”

## Single-label multiclass classification: cross entropy

Let sample $i$ have logits $z_i \in \mathbb{R}^C$ and true class index $y_i \in \{0,\ldots,C-1\}$. Unweighted cross entropy averaged over examples is:

$$
\mathcal{L}_{CE} = -\frac{1}{N}\sum_{i=1}^{N}
\log\frac{\exp(z_{i,y_i})}{\sum_{c=1}^{C}\exp(z_{i,c})}.
$$

In PyTorch, `CrossEntropyLoss` accepts logits and internally corresponds to `LogSoftmax` plus `NLLLoss`; therefore do not normally apply `softmax` to input first. It also accepts soft labels/class-probability targets, but callers must ensure that every row is a valid probability distribution—the framework does not validate every constraint for you. `weight`, `ignore_index`, `label_smoothing`, and `reduction` change the optimization objective or aggregation, so record them when comparing experiments.

```python
import torch.nn as nn

criterion = nn.CrossEntropyLoss()
loss = criterion(logits, class_index_targets)  # logits: [N, C]; targets: [N]
```

## Binary and multilabel classification: BCE with logits

For one raw logit $z$ and label $y \in [0,1]$, binary cross entropy is:

$$
\ell(z, y) = -\big[y\log\sigma(z) + (1-y)\log(1-\sigma(z))\big],
$$

where $\sigma$ is sigmoid. `BCEWithLogitsLoss` combines sigmoid and loss in a numerically stable calculation; do not pass it probabilities that have already gone through sigmoid. In multilabel tasks, this term is computed independently per class, so multiple classes can be positive at once. That differs from single-label multiclass classification, where every row selects one class.

`pos_weight` changes relative training weight for positive examples and can change the precision/recall tradeoff. It does not automatically choose a deployment threshold, calibrate probabilities, or repair label bias. Choose and inspect thresholds, calibration, and per-class metrics inside the validation boundary.

## Regression: MSE is only an explicit starting point

The unweighted mean squared error is:

$$
\mathcal{L}_{MSE}=\frac{1}{N}\sum_{i=1}^{N}(y_i-\hat{y}_i)^2.
$$

Squaring amplifies large errors. That can be appropriate when large deviations cost more, but can also let outliers dominate training. Before choosing MAE, Huber, or another objective, state error cost, target unit, missing-value handling, and reported metric. Training loss can differ from delivery-time MAE, RMSE, or business loss, but the difference needs a reason and validation evidence.

## Contrastive loss is not one universal formula

“Contrastive loss” covers many objectives for metric learning, retrieval, and representation alignment. Papers and libraries differ in definitions of similar/dissimilar labels, distance/similarity, margin, temperature, sampling strategy, and batch aggregation. Do not present any one form as a universal interface. Before use, follow the selected paper and implementation for input shape, label convention, and unit tests; split evaluation by entity/document/time to prevent near-duplicate leakage from creating false retrieval gains.

## Selection and validation checklist

1. State task, model output, label type, `reduction`, and class/example weights first.
2. Fit in the training region; choose loss variants, weights, and threshold in validation; reserve the sealed test set for final estimation.
3. Report decision-relevant metrics, per-class support, calibration/threshold boundaries, and error examples together. Lower training loss does not prove F1, cost, or safety risk improved with it.
4. For affected populations or high-risk operations, review data representativeness, access/privacy boundaries, human review, and appeal/correction process. One loss or one group metric cannot supply a complete fairness conclusion.

## References

Review date: **2026-07-22**. Interface semantics and defaults change with framework versions; follow the documentation for the version actually in use before running.

- [PyTorch: CrossEntropyLoss](https://docs.pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html)
- [PyTorch: BCEWithLogitsLoss](https://docs.pytorch.org/docs/stable/generated/torch.nn.BCEWithLogitsLoss.html)
- [PyTorch: MSELoss](https://docs.pytorch.org/docs/stable/generated/torch.nn.MSELoss.html)
- [scikit-learn: Common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html)
