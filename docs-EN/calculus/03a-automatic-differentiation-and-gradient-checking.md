---
title: "Calculus Fundamentals: Automatic Differentiation and Gradient Checking"
tags:
  - ai-agent-engineer
  - calculus
  - automatic-differentiation
aliases:
  - Autodiff and gradcheck
  - Numerical gradient checking
source_checked: 2026-07-14
source_baseline:
  - PyTorch 2.13 autograd and gradcheck documentation
  - MIT OpenCourseWare multivariable calculus
related: "[[calculus/00-index]]"
lang: en
translation_key: 微积分基础/03A-自动微分与梯度检查.md
translation_source_hash: 12ed8fd49dd22d06acc88cb8bc1cf053f3f23fa6927f5a93b90f16255da6ddb8
translation_route: zh-CN/微积分基础/03A-自动微分与梯度检查
translation_default_route: zh-CN/微积分基础/03A-自动微分与梯度检查
---

# Calculus Fundamentals: Automatic Differentiation and Gradient Checking

## Objective

Backpropagation organizes the chain rule; automatic differentiation (AD) lets a program execute local rules over its actual computation graph. Distinguish symbolic differentiation, finite differences, and AD; understand JVP/VJP shapes; and use a workflow that locates gradient errors.

## Three kinds of “differentiation” are not interchangeable

| Method | What it does | Primary use | Primary limit |
| --- | --- | --- | --- |
| Symbolic differentiation | Manipulates formula expressions | Derivation and simplification of small formulas | Expressions can explode and arbitrary program branches are difficult |
| Numerical difference | Perturbs input and compares function values | Small independent verification | Truncation/rounding error; cost grows with input dimension |
| Automatic differentiation | Applies chain rule to actual primitive operations | Training and differentiable programs | Depends on correct graph, dtype, operator derivatives, and state semantics |

AD is not choosing an extremely small $h$; it normally applies analytical local derivative rules at machine precision. Finite differences make an independent reference, not a replacement for large-model backpropagation.

## Jacobian, JVP, and VJP

For $f:\mathbb R^n\to\mathbb R^m$, Jacobian $J$ has shape $m\times n$. Storing it can be expensive, so AD commonly computes products directly:

- Forward mode computes a Jacobian-vector product: $Ju$.
- Reverse mode computes a vector-Jacobian product: $v^TJ$.

Scalar loss has $m=1$ and many parameters. Propagating one upstream scalar from output to input yields all parameter gradients, so reverse mode is especially appropriate. PyTorch's autograd documentation describes a reverse automatic-differentiation system based on computation history; its APIs and stability status can change across versions.

## State in a computation graph

When debugging framework code, distinguish:

- which tensors require gradients and which are constants;
- which are leaf nodes and where their gradients are retained;
- whether repeated backward calls accumulate old gradients;
- whether **detach**, no-grad context, or conversion to a plain number cuts the graph;
- whether an in-place mutation destroys intermediates needed by backward;
- whether mixed precision, stochastic operators, or parallel reductions introduce extra differences.

These are framework semantics, not calculus formulas. Follow current official documentation and a minimal reproduction.

## Centered finite difference

For one variable:

$$
f'(x)\approx\frac{f(x+h)-f(x-h)}{2h}
$$

For several parameters, perturb one coordinate per evaluation to rebuild a numerical gradient or Jacobian. Centered differences usually have lower truncation error than one-sided differences, but too-small $h$ suffers cancellation. Compare both absolute and relative tolerances:

$$
|g_a-g_n|\le \text{atol}+\text{rtol}|g_n|
$$

Here $g_a$ is the analytical/AD gradient and $g_n$ the numerical estimate. Absolute tolerance matters near zero; relative tolerance matters for large values.

## Runnable step scan

~~~python
def function(value: float) -> float:
    return value ** 3 - 2.0 * value


x = 1.5
analytical = 3.0 * x ** 2 - 2.0
errors = []
for step in (1e-1, 1e-3, 1e-5, 1e-7, 1e-9, 1e-11):
    numerical = (function(x + step) - function(x - step)) / (2.0 * step)
    error = abs(analytical - numerical)
    errors.append(error)
    print(f"step={step:.0e} error={error:.3e}")

assert min(errors) < 1e-8
~~~

Error typically falls as the step shrinks and then rises because of floating-point rounding. One accidental pass does not prove a whole implementation correct; check multiple inputs, directions, and boundaries.

## Points unsuitable for direct gradcheck

- Nondifferentiable points such as ReLU at 0 and absolute value at 0; a framework's chosen subgradient can differ from symmetric difference.
- Random dropout, sampling, or data augmentation without fixed random state.
- Batch-normalization-like operations whose batch state changes.
- Overlapping input memory, where perturbing one coordinate changes several logical elements.
- Low-precision inputs whose default difference step and tolerance are unsuitable.

PyTorch 2.13 gradcheck documentation explicitly notes that default parameters target double precision; low precision, nondifferentiable points, and overlapping memory can fail a check. Do not hide failure by unconditionally loosening tolerances.

## Gradient-check workflow

1. Reduce to a small tensor and deterministic scalar output.
2. Use high precision and fix random seed and model state.
3. Avoid known nondifferentiable points, or state the framework convention.
4. Compare analytical/AD gradients with centered differences over several steps.
5. Record absolute error, relative error, inputs, and gradient shape together.
6. If it fails, shrink the computation graph layer by layer and inspect broadcasting, reduction factors, signs, and shared-path accumulation.
7. Keep a regression test after repair instead of only checking once in a notebook.

## Common errors

- Omitting the averaging denominator or factor 2 when differentiating MSE.
- Forgetting the reduction that accumulates a broadcast gradient across elements.
- Overwriting rather than adding gradient for shared parameters on several paths.
- Comparing two reasonable but different subgradient conventions at a nondifferentiable point.
- Using one step only, then increasing tolerances until failure disappears.
- Treating eventual training-loss decrease as proof that every local gradient is correct.

## Exercises and self-check

1. Run the step scan, find the order of magnitude with least error, and explain both sides of the curve.
2. Calculate the gradient of $f(x,y)=x^2+xy$ by hand, then apply centered difference to each coordinate.
3. Draw a **broadcast → sum** graph and explain why backward sums over broadcast axes.
4. Write a non-misleading diagnosis note for gradcheck failure at ReLU **x=0**.
5. List the state that must be fixed before gradient-checking a random model.

- [ ] I can distinguish symbolic differentiation, finite differences, and AD.
- [ ] I can state JVP/VJP shape and appropriate use.
- [ ] I use several steps plus absolute/relative tolerance to check gradients.
- [ ] I know the risks of nondifferentiable points, low precision, random state, and overlapping memory.

Previous: [[calculus/03-chain-rule-and-backpropagation|Chain rule and backpropagation]] · Next: [[calculus/04-optimization-and-gradient-descent|Optimization and gradient descent]].

## References

Sources were checked on **2026-07-14**. The PyTorch pages correspond to the 2.13 documentation found for this review; framework interfaces and stability markers may change, so recheck current official documentation before use.

- [PyTorch: Autograd mechanics](https://docs.pytorch.org/docs/stable/notes/autograd.html)
- [PyTorch: Gradcheck mechanics](https://docs.pytorch.org/docs/stable/notes/gradcheck.html)
- [PyTorch: torch.autograd.gradcheck](https://docs.pytorch.org/docs/stable/generated/torch.autograd.gradcheck.gradcheck.html)
- [MIT OpenCourseWare: 18.02SC Partial Derivatives](https://ocw.mit.edu/courses/18-02sc-multivariable-calculus-fall-2010/pages/2.-partial-derivatives/)
