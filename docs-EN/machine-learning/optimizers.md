---
title: "Optimizers"
tags:
  - machine-learning
  - deep-learning
  - reference
content_tier: reference
content_status: validated
content_origin: original
source_checked: 2026-07-22
source_baseline:
  - PyTorch stable optimizer API documentation (retrieved 2026-07-22)
lang: en
translation_key: 机器学习/优化器.md
translation_source_hash: bec4367dccd07c874c384bc3876f7437593ee0e6ac8149384d7a0a4e4795ca11
translation_route: zh-CN/机器学习/优化器
translation_default_route: zh-CN/机器学习/优化器
---

# Optimizers

> [!note] Content and boundary
> This page is an original English summary of primary API documentation and original papers. An optimizer defines how parameters update after gradients are given; it cannot repair leakage, incorrect labels, unavailable features, or an inappropriate evaluation split, and no task-independent best default exists.

<!-- graph-links:start -->
## Related notes

- Same-directory notes: [[machine-learning/loss-functions|Loss Functions]] · [[machine-learning/04-training-validation-and-hyperparameter-tuning|Training, Validation, and Hyperparameter Tuning]] · [[machine-learning/05-overfitting-and-generalization|Overfitting and Generalization]]
- Next learning: [[deep-learning/00-index|Deep Learning]]
<!-- graph-links:end -->

## Establish shared vocabulary first

For an objective $L(\theta)$, the simplest gradient-descent update is:

$$
\theta_{t+1}=\theta_t-\eta\nabla_\theta L(\theta_t),
$$

where $\theta$ denotes parameters and $\eta$ the learning rate. Different optimizers chiefly change how gradients are smoothed, scaled, or combined with regularization. All still depend on data, loss, batch, numeric precision, and training budget.

## Common categories and questions they suit

| Category | Core idea | Tradeoff to validate |
| --- | --- | --- |
| SGD | update directly from the current gradient | learning rate, batch, data scale, and convergence speed |
| SGD + momentum / Nesterov | accumulate historical update direction to reduce local oscillation | momentum, learning-rate schedule, instability/divergence risk |
| Adam | exponentially estimate first- and second-gradient moments with bias correction | learning rate, `betas`, numeric-stability term, and generalization |
| AdamW | decouple weight decay from Adam's moment estimates | which parameters decay, learning-rate schedule, and validation benefit |
| AdaGrad / RMSprop | adaptively scale by historical squared gradients | sparsity, non-stationary training, and concrete framework implementation |

This table is a starting point for diagnosis and experiments, not a selection recipe. For the same task, data volume, pretraining starting point, architecture, mixed precision, batch size, and scheduler can all change results.

## Do not conflate Adam, AdamW, and `weight_decay`

Adam maintains exponential moving estimates of gradients and their squares, commonly abbreviated $m_t$ and $v_t$, then scales updates with bias-corrected quantities. AdamW applies parameter decay separately from these moment estimates; PyTorch `AdamW` documentation explicitly describes weight decay as not accumulating into momentum or variance.

Therefore, do not indiscriminately call `weight_decay` “L2 regularization” across every optimizer and framework. Inspect formulas, parameter groups, and defaults in the current implementation, especially when migrating checkpoints or changing frameworks. Whether to decay bias, normalization-layer, or embedding parameters is also a model/task design choice that needs validation evidence rather than copied parameter groups.

```python
import torch

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=learning_rate,
    weight_decay=weight_decay,
)
```

These variables are experiment configuration to validate, not recommended constants. A checkpoint should also retain `optimizer.state_dict()`; it contains optimization state for every parameter, and without it “resume training” is not equivalent to continuing from the interruption.

## A reproducible optimization experiment protocol

1. Fix data version, split unit, baseline, loss, primary metric, and training budget first. Do not choose an optimizer from final-test results.
2. Change only a few justified variables per round, such as optimizer, learning rate, or scheduler, rather than model, augmentation, and batch all together.
3. Record Python/framework versions, hardware, randomness settings, precision mode, batch, gradient clipping, loss, learning-rate curve, and validation metrics.
4. Inspect training loss, validation metrics, error examples, and failure modes together. When training loss falls while validation does not improve, first investigate data, labels, leakage, overfitting, and metric alignment before enlarging the search.
5. After locking a solution, report results on a sealed test set or new time window. Save model, optimizer, scheduler, random state, and configuration before discussing resumed training or reproducibility.

## Common misconceptions

- **Treat learning rate as everything**: it matters, but does not replace correct data boundaries or loss/metric alignment.
- **Treat defaults as recommendations**: API defaults aim for usability, not an empirical conclusion about your model or business.
- **Look only at final loss**: different reduction, batch, and data ranges make loss magnitudes not directly comparable.
- **Save only model weights**: inference may resume, but training trajectory, scheduler, and optimizer state can be lost.
- **Judge which optimizer is better on training data**: select through validation inside the training region and retain a final test boundary.

## References

Review date: **2026-07-22**. Interfaces, defaults, and accelerated implementations evolve with framework versions; follow the documentation for the version actually in use before running.

- [PyTorch: SGD](https://docs.pytorch.org/docs/stable/generated/torch.optim.SGD.html)
- [PyTorch: Adam](https://docs.pytorch.org/docs/stable/generated/torch.optim.Adam.html)
- [PyTorch: AdamW](https://docs.pytorch.org/docs/stable/generated/torch.optim.AdamW.html)
- [PyTorch: RMSprop](https://docs.pytorch.org/docs/stable/generated/torch.optim.RMSprop.html)
- [Decoupled Weight Decay Regularization](https://arxiv.org/abs/1711.05101)
