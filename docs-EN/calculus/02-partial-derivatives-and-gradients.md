---
title: "Partial Derivatives and Gradients"
tags: [ ai-agent-engineer, calculus ]
aliases: [ Gradient fundamentals ]
source_checked: 2026-07-14
source_baseline:
  - MIT OpenCourseWare 18.02SC Partial Derivatives
lang: en
translation_key: 微积分基础/02-偏导数与梯度.md
translation_source_hash: 46ab6ff88c9578740fb63e03cb1f6fd536fff422aa87fe7b5e4dedac5e3b8661
translation_route: zh-CN/微积分基础/02-偏导数与梯度
translation_default_route: zh-CN/微积分基础/02-偏导数与梯度
---

# Partial Derivatives and Gradients

## Objective

Understand partial derivatives as changing one coordinate at a time, arrange them into a gradient, and use directional derivatives and multivariable local linear approximation to determine how a small step changes loss. Recognize the shape and boundary of use for Jacobians and Hessians.

## Multiparameter functions

Model loss often depends on thousands of parameters: $L(w_1,w_2,\ldots)$. A partial derivative is the local rate when all other variables are temporarily held fixed.

If:

$$
f(x,y)=x^2+3xy+y^2
$$

then:

$$
\frac{\partial f}{\partial x}=2x+3y,\qquad \frac{\partial f}{\partial y}=3x+2y
$$

At $(1,2)$, the partial derivatives are 8 and 7.

Holding other variables fixed is a mathematical operation, not a claim that real variables can be changed independently. If parameters are constrained or generated from one source variable, first express the actual parameterization and use the chain rule for change in a feasible direction.

## Gradient

Arrange all partial derivatives into a vector:

$$
\nabla f=\begin{bmatrix}\partial f/\partial x\\\partial f/\partial y\end{bmatrix}
$$

The gradient points toward locally fastest increase; the negative gradient points toward locally fastest decrease under Euclidean length. The directional derivative in unit direction $u$ is:

$$
D_uf=\nabla f^Tu,\qquad \|u\|=1
$$

This connects calculus with a dot product.

For a small perturbation $\Delta x$, multivariable local linear approximation is:

$$
f(x+\Delta x)\approx f(x)+\nabla f(x)^T\Delta x
$$

Under $\|u\|_2=1$, the directional derivative is maximized in the gradient direction at $\|\nabla f\|_2$ and minimized in the negative-gradient direction. This “steepest” statement depends on the Euclidean metric and coordinate scale; reparameterization changes directions.

## Contour intuition

Contour lines join points with equal function value. A gradient is perpendicular to a smooth contour because moving along it has no first-order change. In a loss landscape, negative gradient crosses contours toward lower values.

## Minimum knowledge of Jacobian and Hessian

- First derivatives of vector output with respect to vector input form a Jacobian.
- Second partial derivatives of a scalar function form a Hessian $H$, which describes local curvature.

For $f:\mathbb R^n\to\mathbb R^m$, Jacobian shape is $m\times n$. For $L:\mathbb R^n\to\mathbb R$, Hessian shape is $n\times n$. Engineering usually computes a Jacobian-vector product or vector-Jacobian product rather than materializing a huge matrix.

You do not need to calculate large matrices by hand initially, but should know that backpropagation computes one class of Jacobian products efficiently and that curvature affects learning rate and optimization difficulty.

## Uses in ML and embeddings

- Gradients determine how weights and relevant rows in an embedding table update.
- A gradient with respect to a query embedding can show which directions affect similarity, but “large gradient” is not automatically causal importance.
- Adversarial perturbations use input gradients to find small changes with large output effects, demonstrating local sensitivity.
- Evaluation metrics such as accuracy are nondifferentiable, so training often uses a differentiable surrogate loss.

## Verifiable example

At $(1,2)$, the directional derivative in unit direction $u=(1,0)$ is 8; in $u=(0,1)$ it is 7. A very small step along the negative normalized gradient should lower $f$. Substitute $\epsilon=0.001$ directly to check.

## Common misconceptions

- Existing partial derivatives do not necessarily imply a function is differentiable everywhere; common smooth engineering functions have fewer issues.
- Gradient magnitude depends on parameter scale, so different units are not directly comparable.
- A gradient is local information and does not guarantee a one-step global optimum.
- A zero gradient can be a saddle point.

## Exercises and self-check

1. Find the gradient and minimum of $f(x,y)=(x-2)^2+2(y+1)^2$.
2. Explain why feature scaling changes loss-contour shape and optimization speed.
3. Normalize the gradient at $(1,2)$ and verify that first-order increase in that unit direction equals gradient norm.
4. State the Jacobian shape for $f:\mathbb R^3\to\mathbb R^2$ and gradient shape for a scalar loss over three parameters.
5. Give a constrained-parameter example where “hold every other coordinate fixed” is not an executable intervention.

- [ ] I can calculate a simple gradient.
- [ ] I can explain a directional derivative as a gradient dot product.
- [ ] I know gradients depend on parameter scale.
- [ ] I can write multivariable local linear approximation and Jacobian/Hessian shapes.
- [ ] I know gradient information is local and depends on coordinates and metric.

## References

Sources were checked on **2026-07-14**.

- [MIT OpenCourseWare: 18.02SC Partial Derivatives](https://ocw.mit.edu/courses/18-02sc-multivariable-calculus-fall-2010/pages/2.-partial-derivatives/)

Previous: [[calculus/01-functions-limits-and-derivatives|Functions, limits, and derivatives]] · Next: [[calculus/03-chain-rule-and-backpropagation|Chain rule and backpropagation]].
