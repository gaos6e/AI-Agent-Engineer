---
title: "Optimization and Gradient Descent"
tags: [ ai-agent-engineer, calculus ]
aliases: [ Gradient descent fundamentals ]
source_checked: 2026-07-14
source_baseline:
  - Google Machine Learning Crash Course gradient descent and hyperparameters
  - MIT OpenCourseWare calculus
lang: en
translation_key: 微积分基础/04-优化与梯度下降.md
translation_source_hash: e144cca3c23f8223657806c9d48bccb823fad8078bcc905ab536c219b0a29bc7
translation_route: zh-CN/微积分基础/04-优化与梯度下降
translation_default_route: zh-CN/微积分基础/04-优化与梯度下降
---

# Optimization and Gradient Descent

## Objective

Connect negative-gradient updates with local linear approximation. Derive when a learning rate converges on a quadratic function, and establish a training-diagnosis checklist that separately examines data, gradients, loss, validation metrics, numerical anomalies, and stopping rules.

## Optimization problem

Training is often written:

$$
\theta^*=\arg\min_\theta L(\theta)
$$

$\theta$ is the parameter and $L$ the loss. Loss is a training proxy objective, not user value. For example, lower cross-entropy does not automatically guarantee factuality, latency, or safety.

## Gradient-descent update

$$
\theta_{t+1}=\theta_t-\eta\nabla L(\theta_t)
$$

$\eta$ is learning rate. The negative sign takes a local descent direction. For $L(w)=(w-3)^2$, the gradient is $2(w-3)$. From $w=0$ with $\eta=0.1$, $w_1=0.6$ and later steps approach 3.

Let $e_t=w_t-3$. Then:

$$
e_{t+1}=(1-2\eta)e_t
$$

For error magnitude to decrease on this specific function, $|1-2\eta|<1$, or $0<\eta<1$. $\eta=0.5$ reaches the minimum in one step, $\eta=0.9$ alternates while converging, $\eta=1$ does not decay, and $\eta>1$ diverges. This is an exact result for one quadratic, not a universal threshold for every model.

## Learning rate

- Too small: stable decline but very slow.
- Suitable: faster convergence.
- Too large: crosses the valley, oscillates, or diverges.

Learning rate depends on feature scale, curvature, and batch noise; do not copy it mechanically from another model. Inspect loss, validation metric, gradient norm, and numerical anomalies together.

Feature scaling changes curvature across directions. When one direction is steep and another flat, one learning rate can oscillate across the steep direction and move slowly along the flat one. Standardization, preconditioning, adaptive optimizers, or better parameterization can improve the path, but all need validation data and real-task checks.

## Batch and stochastic gradients

A full gradient uses all examples. SGD uses one example at a time; mini-batch uses a small batch. A mini-batch gradient is noisy but computationally efficient. Larger batches usually lower variance but need more memory, and learning-rate and related settings need adjustment with them.

An epoch is one defined traversal of training data; a step is one parameter update. If the last batch has a different size, a sampler is used, or data streams continuously, specify actual sample exposure rather than assuming an epoch has one fixed meaning.

## Curvature, convexity, and local optima

For a convex function, every local minimum is global; squared loss in linear regression is a typical case. Deep networks are usually nonconvex and have saddle points and flat regions. A Hessian describes second-order curvature. Strongly different curvature by direction causes fixed learning rates to oscillate in steep directions and progress slowly in flat ones.

## Minimum knowledge of common optimizers

- Momentum accumulates prior direction to reduce oscillation.
- Adam maintains first- and second-moment estimates per parameter and rescales adaptively.
- Weight decay/regularization changes an objective or update and is not merely an “overfitting switch.”

This course does not expand APIs. First understand that every optimizer still requires reliable gradients, suitable learning rate, a validation set, and stopping conditions.

## Stopping and diagnosis

Define stopping conditions before training, for example:

- maximum step or epoch;
- no validation improvement during predefined patience;
- non-finite gradient or parameter;
- loss rises sharply relative to baseline;
- computation, cost, or time budget is reached.

Diagnose in order: first see whether a small batch can overfit; then inspect gradient, reduction, learning rate, and scale; only then expand data and model. A nondecreasing loss alone cannot distinguish label errors, gradient bugs, learning-rate problems, insufficient model capacity, or an objective mismatch.

## Boundary in Agent engineering

Most Agent applications do not train a foundation model, but may tune a reranker, embedding model, classifier, or prompt/policy parameter. Discrete prompt selection is not necessarily differentiable and may call for search or a bandit. Do not force gradient descent on every problem.

## Common misconceptions, exercises, and self-check

- Training loss falling does not prove validation or online metrics improve.
- Continuing training after a gradient becomes NaN and waiting for recovery.
- Tuning epochs without recording data version and random seed.
- Treating optimization failure as identical to insufficient model expressiveness.

Exercises:

1. Calculate the first three steps of $L(w)=(w-3)^2$ for $\eta=0.1$ and $\eta=1.1$, then compare convergence and divergence.
2. Use $e_{t+1}=(1-2\eta)e_t$ to explain $\eta=0.5,0.9,1.0$.
3. State step, epoch, batch size, and actual sample exposure for one training run.
4. Give a diagnosis path for loss decreasing while validation metric worsens.
5. Design a stop-and-record rule for **NaN** that does not allow “wait for it to recover.”

- [ ] I can write the update and explain every term.
- [ ] I can use a loss curve to diagnose learning-rate candidates.
- [ ] I know training objective and business metric differ.
- [ ] I can distinguish step, epoch, batch, and sample exposure.
- [ ] I define stopping conditions in advance and treat divergence as an explicit error.

## References

Sources were checked on **2026-07-14**. Training APIs and optimizer defaults change; this lesson uses stable principles only. Follow current framework documentation for concrete implementation.

- [Google ML Crash Course: Gradient Descent](https://developers.google.com/machine-learning/crash-course/linear-regression/gradient-descent)
- [Google ML Crash Course: Hyperparameters](https://developers.google.com/machine-learning/crash-course/linear-regression/hyperparameters)
- [MIT OpenCourseWare: 18.01SC Single Variable Calculus](https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/)

Previous: [[calculus/03a-automatic-differentiation-and-gradient-checking|Automatic differentiation and gradient checking]] · Next: [[calculus/05-integrals-probability-and-gradient-descent-project|Integrals, probability, and the gradient-descent project]].
