---
title: "Calculus Fundamentals"
tags:
  - ai-agent-engineer
  - calculus
aliases:
  - Calculus fundamentals
  - Calculus for machine learning
source_checked: 2026-07-14
source_baseline:
  - MIT OpenCourseWare 18.01SC and 18.02SC
  - Google Machine Learning Crash Course
  - PyTorch 2.13 autograd and gradcheck documentation
ai_learning_stage: "2. Mathematical and data foundations"
ai_learning_order: 12
ai_learning_schema: 2
ai_learning_id: calculus
ai_learning_domain: foundations
ai_learning_catalog_order: 1200
ai_learning_hard_prerequisites: []
lang: en
translation_key: 微积分基础/00-目录.md
translation_source_hash: 2632c300ad2bdefcec04acd64bd70283ead8ffc38e18890e0d04d7337f9c711d
translation_route: zh-CN/微积分基础/00-目录
translation_default_route: zh-CN/微积分基础/00-目录
---

# Calculus Fundamentals

## Course overview

Calculus studies rates of change and accumulation. Training a model means observing how loss changes with parameters and updating in a descending direction; interval probability under a density is accumulated area. This course starts with variables, function graphs, and units, then moves through derivatives, gradients, the chain rule, automatic differentiation, optimization, and integrals. A tested standard-library project verifies gradients. The goal is to read training behavior and diagnose errors, not to become a complete mathematics major curriculum.

## Where this fits in the overall path

Calculus Fundamentals belongs to the Mathematical and data foundations stage. After functions and linear algebra, it connects to machine learning and deep learning. It explains how loss changes with parameters, why gradients can guide training, and how a probability density accumulates into probability.

## Learning objectives

- Express an engineering problem as a function with domain, units, and fixed conditions.
- Understand derivatives and local linear approximation from difference quotients.
- Calculate simple partial derivatives and gradients, and explain directional derivatives.
- Read backpropagation through the chain rule.
- Distinguish symbolic differentiation, finite differences, and automatic differentiation, then complete a gradient check.
- Understand gradient descent, learning rate, curvature, divergence, and stopping conditions.
- Recognize how integration is used in probability and expectation.

## Prerequisites

Function substitution, powers, and the slope of a line are enough to begin. Complete [[python-fundamentals/00-index|Python Fundamentals]] and [[linear-algebra/00-index|Linear Algebra]] first if possible. Gradients are vectors, and dot products and shapes recur throughout. The course does not require formal limit proofs first.

## Recommended order

1. [[calculus/00a-variables-functions-graphs-and-scales|Variables, functions, graphs, and scales]]: define input, output, units, and observable change.
2. [[calculus/01-functions-limits-and-derivatives|Functions, limits, and derivatives]]: understand a derivative as local rate and linear approximation.
3. [[calculus/02-partial-derivatives-and-gradients|Partial derivatives and gradients]]: handle multiparameter loss, directional derivatives, and curvature.
4. [[calculus/03-chain-rule-and-backpropagation|Chain rule and backpropagation]]: propagate influence through a computation graph and sum branch contributions.
5. [[calculus/03a-automatic-differentiation-and-gradient-checking|Automatic differentiation and gradient checking]]: distinguish AD from finite differences and identify dtype, nondifferentiable-point, and state risks.
6. [[calculus/04-optimization-and-gradient-descent|Optimization and gradient descent]]: understand learning rate, curvature, batches, divergence, and stopping.
7. [[calculus/05-integrals-probability-and-gradient-descent-project|Integrals, probability, and the gradient-descent project]]: understand accumulation and complete a verifiable training exercise with nine tests.

## Hands-on entry point

- In [[calculus/00a-variables-functions-graphs-and-scales|Variables, functions, graphs, and scales]], scan difference steps to observe a function before explaining its derivative.
- In [[calculus/03a-automatic-differentiation-and-gradient-checking|Automatic differentiation and gradient checking]], calculate a two-dimensional gradient by hand and verify it with absolute and relative tolerances.
- In [[calculus/05-integrals-probability-and-gradient-descent-project|Integrals, probability, and the gradient-descent project]], run analytical-gradient and centered-difference checks, normal and **-O** modes, and nine tests. Then change learning rate and feature scale to observe convergence or explicit divergence.

## Mastery criteria

- [ ] I can explain a derivative with a difference quotient rather than only reciting rules.
- [ ] I can calculate simple partial derivatives and explain gradient direction.
- [ ] I can apply the chain rule along a computation graph.
- [ ] I can write a gradient-descent update and diagnose a learning rate that is too large or too small.
- [ ] I can use finite differences to check an analytical gradient.
- [ ] I can distinguish backpropagation, automatic differentiation, an optimizer update, and business evaluation.
- [ ] I can explain integration in probability and expectation.

## Connections to other knowledge bases

| Knowledge base | Connection |
| --- | --- |
| [[linear-algebra/00-index\|Linear Algebra]] | Gradients, Jacobians, Hessians, JVPs, and VJPs depend on vector and matrix shape. |
| [[probability-and-statistics/00-index\|Probability and Statistics]] | Continuous densities, expectation, and cumulative distributions use integrals; stochastic gradients require understanding sampling variability. |
| [[machine-learning/00-index\|Machine Learning]] | Loss, regularization, gradient descent, and validation form the training process. |
| [[deep-learning/00-index\|Deep Learning]] | Automatic differentiation, backpropagation, vanishing/exploding gradients, and optimizers are central. |
| [[embeddings/00-index\|Embeddings]] and [[reranking/00-index\|Reranking]] | Fine-tuning or training representation/ranking models uses gradients, while online thresholds and metrics may be discrete. |

## Primary references

- [MIT OCW 18.01SC Single Variable Calculus](https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/)
- [MIT OCW 18.02SC Partial Derivatives](https://ocw.mit.edu/courses/18-02sc-multivariable-calculus-fall-2010/pages/2.-partial-derivatives/)
- [Google ML Crash Course: Gradient Descent](https://developers.google.com/machine-learning/crash-course/linear-regression/gradient-descent)
- [Google ML Crash Course: Hyperparameters](https://developers.google.com/machine-learning/crash-course/linear-regression/hyperparameters)
- [PyTorch: Autograd mechanics](https://docs.pytorch.org/docs/stable/notes/autograd.html)
- [PyTorch: Gradcheck mechanics](https://docs.pytorch.org/docs/stable/notes/gradcheck.html)

Sources were checked on **2026-07-14**. MIT supports stable mathematical concepts. Google and PyTorch pages are changing engineering material; this course records their current semantic content and check date, but recheck the version before using a framework. The local project uses only the Python 3.11.9 standard library and does not require PyTorch.
