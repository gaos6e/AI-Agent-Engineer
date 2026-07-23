---
title: "Chain Rule and Backpropagation"
tags: [ ai-agent-engineer, calculus ]
aliases: [ Backpropagation intuition ]
source_checked: 2026-07-14
source_baseline:
  - MIT OpenCourseWare 18.02SC Partial Derivatives
  - PyTorch 2.13 autograd documentation
lang: en
translation_key: 微积分基础/03-链式法则与反向传播.md
translation_source_hash: 7879f2db41560efabdb9e9186e6f1c232dfe1054cc31e340d9b8c7accc97c090
translation_route: zh-CN/微积分基础/03-链式法则与反向传播
translation_default_route: zh-CN/微积分基础/03-链式法则与反向传播
---

# Chain Rule and Backpropagation

## Objective

Apply the chain rule to scalar composite functions and simple computation graphs. Understand why branch gradients add, why batch averaging rescales gradients, and how “calculate a gradient,” “automatically record a graph,” and “update with an optimizer” are three distinct steps.

## Composite functions and responsibility propagation

If $y=f(u)$ and $u=g(x)$:

$$
\frac{dy}{dx}=\frac{dy}{du}\frac{du}{dx}
$$

The effect of $x$ on $y$ equals “the effect of $x$ on the intermediate quantity × the effect of the intermediate quantity on output.”

For $u=3x+1$ and $y=u^2$:

$$
\frac{dy}{dx}=2u\times3=6(3x+1)
$$

At $x=1$, the derivative is 24. Expanding $y=(3x+1)^2$ verifies it.

The multivariable version also follows shape. If $x\in\mathbb R^n$, $u=g(x)\in\mathbb R^m$, and scalar $L=f(u)$:

$$
\nabla_x L=J_g(x)^T\nabla_u L
$$

Backpropagation takes an upstream vector and a local Jacobian as a vector-Jacobian product, so it need not store the complete Jacobian.

## Computation graph

For one linear-regression example:

$$
z=wx+b,\qquad e=z-y,\qquad L=e^2
$$

Backward through the graph:

$$
\frac{\partial L}{\partial e}=2e,\qquad \frac{\partial e}{\partial z}=1,\qquad \frac{\partial z}{\partial w}=x
$$

Therefore:

$$
\frac{\partial L}{\partial w}=2ex
$$

The gradient for $b$ is $2e$. Each local node needs only its own input and upstream gradient.

If batch loss is mean MSE:

$$
L=\frac1n\sum_{i=1}^n(w x_i+b-y_i)^2
$$

then $\partial L/\partial w=\frac2n\sum_i e_i x_i$ and $\partial L/\partial b=\frac2n\sum_i e_i$. Replacing **sum** with **mean** changes gradient scale; implementation, hand calculation, and tests must use the same reduction convention.

## Branches add gradients

When variable $x$ affects $L$ through two paths, the total derivative is the sum of each path's contribution. This is why gradients accumulate for shared parameters, residual connections, and repeated use of one token embedding.

For $y=x^2+x$ and $L=y^2$, one path enters the square and another adds directly:

$$
\frac{dL}{dx}=2y(2x+1)
$$

Omitting either path produces a wrong gradient. Broadcasting, repeated indices, and shared weights can create less obvious multiple paths in code.

## Reverse-mode automatic differentiation

For scalar loss and many parameters, reverse mode obtains all parameter gradients at a cost comparable to forward computation. Backpropagation is an efficient organization of the chain rule on a computation graph, not a separate mysterious formula.

Intermediate values must be saved for backward computation, contributing to training-memory use. Gradient checkpointing exchanges extra recomputation for memory. Inference normally does not retain a complete gradient graph.

## Vanishing and exploding gradients

A long chain multiplies derivatives. Many factors below 1 drive a gradient toward zero; many large factors make it explode. Initialization, normalization, residual connections, activation functions, and gradient clipping all relate to this. Clipping can alleviate a numerical symptom but does not guarantee the root cause is solved.

## Common misconceptions

- Forgetting to add multiple path contributions for a shared variable.
- Confusing backpropagation with parameter updating: the first calculates gradients; the optimizer updates later.
- Checking only that training runs rather than checking gradient direction.
- Changing learning rate whenever numerical and analytical gradients disagree rather than inspecting implementation.

## Exercises and self-check

1. Calculate derivatives for $w$, $b$, and $x$ in $L=(wx+b-y)^2$.
2. Draw **x → u=x² → y=u+x → L=y²**, list both paths from x to L, and add them.
3. Derive $w,b$ gradients for batch-mean MSE and identify where **2/n** originates.
4. State Jacobian/gradient shapes for $x\to u\in\mathbb R^m\to L$ and check transpose direction.
5. Explain the responsibilities of backpropagation, automatic differentiation, and an optimizer update.

- [ ] I can differentiate backward through a simple computation graph.
- [ ] I know branch gradients add.
- [ ] I can distinguish gradient calculation from parameter updates.
- [ ] I check **sum/mean** reduction and batch dimensions.
- [ ] I can use VJP intuition to explain why a full Jacobian is unnecessary.

## References

Sources were checked on **2026-07-14**. Framework automatic-differentiation behavior can change by version; recheck current official documentation before use.

- [MIT OpenCourseWare: 18.02SC Partial Derivatives](https://ocw.mit.edu/courses/18-02sc-multivariable-calculus-fall-2010/pages/2.-partial-derivatives/)
- [PyTorch: Autograd mechanics](https://docs.pytorch.org/docs/stable/notes/autograd.html)
- [Google ML Crash Course: Backpropagation](https://developers.google.com/machine-learning/crash-course/neural-networks/backpropagation)

Previous: [[calculus/02-partial-derivatives-and-gradients|Partial derivatives and gradients]] · Next: [[calculus/03a-automatic-differentiation-and-gradient-checking|Automatic differentiation and gradient checking]].
