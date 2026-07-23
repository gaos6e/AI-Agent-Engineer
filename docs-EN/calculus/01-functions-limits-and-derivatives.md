---
title: "Functions, Limits, and Derivatives"
tags: [ ai-agent-engineer, calculus ]
aliases: [ Derivative intuition ]
source_checked: 2026-07-14
source_baseline:
  - MIT OpenCourseWare 18.01SC Single Variable Calculus
lang: en
translation_key: 微积分基础/01-函数极限与导数.md
translation_source_hash: 6800b8398f81c10526634b1f3569398ab76c0ff68871793bd6f376d7c09bf6f4
translation_route: zh-CN/微积分基础/01-函数极限与导数
translation_default_route: zh-CN/微积分基础/01-函数极限与导数
---

# Functions, Limits, and Derivatives

## Objective

Start from average slope over an interval to understand limits and derivatives. Use a derivative for local linear approximation, recognize continuous-but-nondifferentiable points, unequal left/right derivatives, and discrete jumps, and understand why numerical differences need an appropriate step.

## A function maps input to output

$y=f(x)$ means input $x$ produces output $y$. In ML, $x$ can be a parameter and $f$ a loss; in retrieval, changing a threshold changes recall. Define input, output, and domain before discussing change.

## From average rate to instantaneous rate

The average rate over $[x,x+h]$ is:

$$
\frac{f(x+h)-f(x)}{h}
$$

If the limit exists as $h$ approaches zero, it is the derivative:

$$
f'(x)=\lim_{h\to0}\frac{f(x+h)-f(x)}{h}
$$

It is the local slope near one point. If $f(x)=x^2$:

$$
\frac{(x+h)^2-x^2}{h}=2x+h\to2x
$$

so $f'(x)=2x$. At $x=3$, increasing input by about 0.01 increases output by about $6\times0.01=0.06$.

A limit is about approaching, not necessarily taking, a value. Differentiability at a point implies continuity there, but continuity does not imply differentiability: $|x|$ is continuous at 0 but has different left and right slopes. A function can be undefined at a point while still having a limit as it approaches it.

## Local linear approximation

$$
f(x+\Delta x)\approx f(x)+f'(x)\Delta x
$$

This is the central intuition of gradient descent: when the derivative is positive, a small move in the negative direction usually lowers the function. The approximation works only in a sufficiently small neighborhood; with a large step, higher-order curvature matters.

## Minimum derivative rules

$$
\frac{d}{dx}c=0,\qquad \frac{d}{dx}x^n=nx^{n-1}
$$

$$
\frac{d}{dx}(f+g)=f'+g',\qquad \frac{d}{dx}(cf)=cf'
$$

Learn product, quotient, and chain rules when needed rather than memorizing them without context; difference quotients can check results.

ML also often uses:

$$
\frac{d}{dx}e^x=e^x,\qquad \frac{d}{dx}\ln x=\frac1x\;(x>0)
$$

The logarithm's domain and numerical stability need explicit handling. In cross-entropy implementations, use a framework's stable composite operator rather than calculate an extremely small probability and then take a separate logarithm.

## Nondifferentiability and subgradients

At 0, $|x|$ has left slope -1 and right slope 1, so the ordinary derivative does not exist. ReLU and L1 loss in ML also have nondifferentiable points. Implementations choose a specified subgradient or other handling. A few nondifferentiable points do not make training impossible, but the framework definition must be known.

## Uses and misconceptions

- A loss derivative with respect to parameters describes the impact of a small parameter change on loss.
- A local slope on a latency-concurrency curve can indicate approaching saturation, but noisy observations need statistical treatment.
- Threshold metrics can be step functions and cannot simply inherit smooth derivatives.
- A derivative carries units: if $x$ is seconds and $f$ is cost, $f'(x)$ is cost/second. Milliseconds rescale the numerical value.

Misconceptions: a zero derivative can be a maximum, saddle point, or flat region rather than a minimum. A derivative's existence does not imply global linearity. A finite-difference $h$ that is too large has truncation error, while one that is too small has floating-point cancellation error.

## Exercises and self-check

1. Derive the derivative of $f(x)=3x^2+2$ with a difference quotient.
2. At $x=2$, approximate the $x^2$ derivative with $h=0.1,0.01,0.001$ and observe convergence to 4.
3. Calculate left and right difference quotients of $|x|$ at 0 and explain why it is continuous but not differentiable.
4. State the domain of $f(x)=\ln x$ and describe gradient/numerical risk near 0.
5. Derive how a derivative changes when input units change from seconds to milliseconds.

- [ ] I can explain a derivative from a difference quotient.
- [ ] I know local approximation requires small steps.
- [ ] I do not automatically treat a stationary point as a minimum.
- [ ] I can distinguish limit, continuity, and differentiability.
- [ ] I check derivative units, domain, and numerical step.

## References

Sources were checked on **2026-07-14**.

- [MIT OpenCourseWare: 18.01SC Single Variable Calculus](https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/)

Previous: [[calculus/00a-variables-functions-graphs-and-scales|Variables, functions, graphs, and scales]] · Next: [[calculus/02-partial-derivatives-and-gradients|Partial derivatives and gradients]].
