---
title: "Calculus Fundamentals: Variables, Functions, Graphs, and Scales"
tags:
  - ai-agent-engineer
  - calculus
  - functions
aliases:
  - Modeling change problems
  - Introduction to function graphs
source_checked: 2026-07-14
source_baseline:
  - MIT OpenCourseWare 18.01SC Single Variable Calculus
related: "[[calculus/00-index]]"
lang: en
translation_key: 微积分基础/00A-变量函数图像与变化尺度.md
translation_source_hash: 357c22fad4931bfabd2f97d2493a7f2f013b3e9259ad77ceae398021ecbe545a
translation_route: zh-CN/微积分基础/00A-变量函数图像与变化尺度
translation_default_route: zh-CN/微积分基础/00A-变量函数图像与变化尺度
---

# Calculus Fundamentals: Variables, Functions, Graphs, and Scales

## Objective

Before differentiating, state what changes, what changes with it, the domain under discussion, and the units. This lesson uses tables, graphs, and small numerical experiments to build function intuition, distinguish continuous change from discrete jumps, and explain why scale and units affect gradients.

## Define variables from an engineering problem

A function contains at least:

- **Input variable**: a quantity changed deliberately or observed.
- **Output variable**: a quantity determined by the input.
- **Domain**: the allowed input set.
- **Range**: possible output values.
- **Units and conventions**: milliseconds, seconds, proportions, percentage points, log scale, or normalization.
- **Other fixed conditions**: data version, model, traffic, random seed, and so on.

For example, **L(w)** means how model loss changes with parameter $w$ while other conditions are fixed. If training data, batch, or random sampling also changes, an observed difference is no longer caused by $w$ alone.

## A function is not synonymous with a formula

A function is a rule that maps each allowed input to one output. It can be a formula, program, lookup table, or piecewise rule:

$$
f(x)=\begin{cases}
0,&x<0\\
x,&x\ge0
\end{cases}
$$

This is a simple ReLU form. Whether an API times out, whether a retrieved result enters top-k, or which branch tool routing selects can also be rule-governed, but these rules often jump and may not accept an ordinary derivative directly.

## Use tables and graphs to inspect the whole shape first

For $f(x)=(x-2)^2+1$:

| $x$ | $f(x)$ |
| ---: | ---: |
| 0 | 5 |
| 1 | 2 |
| 2 | 1 |
| 3 | 2 |
| 4 | 5 |

The table shows decrease followed by increase, with a minimum near 2. A graph can also reveal:

- intervals of increase or decrease;
- flat, steep, turning, and discontinuous positions;
- outliers, noise, and observation range;
- whether a local trend represents the whole function.

One derivative value loses this global structure. In optimization, inspect local gradients together with training curves, parameter ranges, and validation metrics.

## Average rate of change and scale

The average rate from $x=a$ to $x=b$ is:

$$
\frac{f(b)-f(a)}{b-a}
$$

The numerator has output units and the denominator has input units. Changing latency from milliseconds to seconds rescales a numeric derivative by 1000 even though the physical relationship is unchanged. Gradient magnitudes for different parameters are not directly comparable when units and parameterization are ignored.

Log scale is common for positive quantities spanning orders of magnitude; probabilities sometimes use logits. Transforming coordinates changes derivative expressions and the optimization landscape, so record the parameterization actually used for training—not merely a business display value.

## Continuous, discrete, and noisy observations

- A continuously differentiable function has a local slope for small changes.
- A piecewise function can be nondifferentiable at some points.
- Discrete metrics such as top-k membership, Boolean success, and string match usually form steps.
- Repeated runs with one parameter producing different outputs are a noisy function or random variable.

Training often uses a differentiable surrogate loss instead of a discrete business metric, but a lower surrogate does not guarantee that the final metric improves at the same time. Evaluate their relationship separately.

## Runnable numerical observation

~~~python
def objective(value: float) -> float:
    return (value - 2.0) ** 2 + 1.0


x = 3.0
for step in (1.0, 0.1, 0.01, 0.001):
    forward_slope = (objective(x + step) - objective(x)) / step
    print(f"step={step:g} forward-slope={forward_slope:.6f}")

assert objective(2.0) == 1.0
~~~

At $x=3$, the true derivative is 2. The forward difference quotient approaches 2 as the step shrinks. With floating-point computation, a step that is too small causes cancellation, so “smaller is always more accurate” is false.

## Function composition

Agent and model paths are often composite functions:

$$
x\xrightarrow{g}u\xrightarrow{f}y,\qquad y=f(g(x))
$$

For example, parameters produce logits and logits produce loss. The chain rule later multiplies each local rate of change; if a variable travels through several paths, their contributions are added.

## Common errors

- Omitting a domain and passing invalid input to a probability, logarithm, or division.
- Mistaking numeric rescaling caused by changed units for system-behavior change.
- Forcing an ordinary derivative at a discrete threshold.
- Looking at one local slope and claiming global monotonicity or a global optimum.
- Comparing two random runs without controlling data, seed, or batch.

## Exercises and self-check

1. For “concurrency → P95 latency,” write input, output, units, domain, and fixed conditions.
2. Sketch $|x|$, ReLU, and a step function, marking continuity and nondifferentiable positions.
3. Reduce the code's step to **1e-8** and **1e-12**; record whether error decreases monotonically.
4. Give one example where a differentiable surrogate and final discrete business metric do not fully agree.
5. Explain why changing a parameter from seconds to milliseconds changes its numeric derivative.

- [ ] I can state a function's input, output, domain, units, and fixed conditions.
- [ ] I inspect a table or graph before explaining a local derivative.
- [ ] I can distinguish continuous, nondifferentiable, discrete, and random observations.
- [ ] I know that rescaling a variable changes numeric derivative values.

Next: [[calculus/01-functions-limits-and-derivatives|Functions, limits, and derivatives]].

## References

Sources were checked on **2026-07-14**.

- [MIT OpenCourseWare: 18.01SC Single Variable Calculus](https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/)
