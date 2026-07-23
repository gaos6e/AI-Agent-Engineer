---
title: "Integrals, Probability, and the Gradient-Descent Project"
tags: [ ai-agent-engineer, calculus, project ]
aliases: [ Gradient-checking project ]
source_checked: 2026-07-14
source_baseline:
  - MIT OpenCourseWare 18.01SC Single Variable Calculus
  - Google Machine Learning Crash Course gradient descent
  - PyTorch 2.13 gradcheck mechanics
lang: en
translation_key: 微积分基础/05-积分概率与梯度下降项目.md
translation_source_hash: 924738ca7caa9538c989d733ab73d2a7d7cea155ca53ace4127bfc3142e19dc7
translation_route: zh-CN/微积分基础/05-积分概率与梯度下降项目
translation_default_route: zh-CN/微积分基础/05-积分概率与梯度下降项目
---

# Integrals, Probability, and the Gradient-Descent Project

## Objective

Understand integration first as accumulation and area, connecting continuous probability, CDF, and expectation. Then use a standard-library linear-regression project to make MSE gradients, centered finite differences, gradient descent, divergence detection, and input boundaries into one runnable, tested loop.

## Minimum intuition for integrals

A definite integral divides an interval into many small pieces and adds them:

$$
\int_a^b f(x)\,dx=\lim_{n\to\infty}\sum_i f(x_i)\Delta x
$$

If $f$ is velocity, the integral is displacement. If $f$ is a probability density, it is interval probability:

$$
P(a\le X\le b)=\int_a^b f(x)\,dx
$$

For a continuous distribution:

$$
E[X]=\int_{-\infty}^{\infty}xf(x)\,dx
$$

The height of a density at one point is not probability at that point. Numerical integration and Monte Carlo sampling are common ways to estimate expectation for complex models, but sample error still needs probabilistic description.

A valid density has $f(x)\ge0$ and integrates to 1 over its domain. The cumulative distribution function is:

$$
F(x)=P(X\le x)=\int_{-\infty}^{x}f(t)\,dt
$$

Under suitable conditions such as continuous density, $F'(x)=f(x)$. Expectation is an average weighted by density, not “the most likely value”; long-tailed distributions can even have no finite expectation.

The fundamental theorem of calculus links accumulation and rate of change: if $F(x)=\int_a^x f(t)dt$, then $F'(x)=f(x)$ under suitable conditions.

Numerical integration substitutes a finite grid for infinite subdivision and has discretization error. Monte Carlo uses random samples to approximate expectation and has sampling error. More grid points or samples can reduce the corresponding error; neither repairs a wrong density, biased sampling, or a wrong objective.

## Project: fit $y=2x+1$

Implementation: [[calculus/examples/gradient_descent.py|gradient_descent.py]] · Tests: [[calculus/examples/test_gradient_descent.py|test_gradient_descent.py]].

### Model and gradient

For $n$ points, fit $\hat y_i=wx_i+b$ with mean squared error:

$$
L(w,b)=\frac1n\sum_{i=1}^n(wx_i+b-y_i)^2
$$

The analytical gradients are:

$$
\frac{\partial L}{\partial w}=\frac2n\sum_i(wx_i+b-y_i)x_i,
\qquad
\frac{\partial L}{\partial b}=\frac2n\sum_i(wx_i+b-y_i)
$$

### Input and training contract

- **xs** and **ys** have equal length, at least two observations, and finite real values.
- Booleans, strings, **NaN**, infinite values, and the unidentifiable case where every $x$ is the same are rejected.
- Learning rate, difference step, and gradient tolerance are positive finite numbers; training steps are positive integers.
- Before updates, compare analytical gradients and centered finite differences at the initial parameters.
- During training, non-finite values or loss that rises sharply relative to initial loss cause explicit divergence.
- Output includes data count, steps, learning rate, initial/final loss, parameters, and maximum gradient-check error.

### Run and test

Run from the repository root:

~~~powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B '.\docs-EN\calculus\examples\gradient_descent.py'
python -B -m unittest discover -s '.\docs-EN\calculus\examples' -p 'test_*.py' -v
~~~

Centered difference is:

$$
f'(x)\approx\frac{f(x+h)-f(x-h)}{2h}
$$

It is an independent small-scale check, not a substitute for large-model backpropagation. Expected script output:

~~~text
observations=5 steps=2000 learning_rate=0.050000
initial-loss=9.000000000000 final-loss=0.000000000000
weight=2.000000 bias=1.000000
gradient-check-max-abs-error=1.118e-09
~~~

Nine tests cover analytical gradient, centered difference, exact convergence, row-order invariance, constant $x$, length boundaries, invalid data, invalid control parameters, and divergence under an excessive learning rate. The project uses explicit exceptions and exit status; it does not use assertions that **python -O** can remove for critical validation.

> [!success] Verified on 2026-07-14
> Under Python 3.11.9, normal and **python -O** script runs matched; all nine **unittest** cases passed, and both Python files passed **py_compile** syntax checks. Generated **__pycache__** was removed and is not retained as knowledge-base content.

## Required experiments

1. Change learning rate from 0.05 to 1.0 and record whether loss diverges.
2. Deliberately remove factor 2 from the gradient and confirm the gradient check fails.
3. Scale features by 100 and observe why the same learning rate is no longer appropriate.
4. After adding noise, distinguish “cannot fit exactly” from “optimizer did not converge.”
5. Scan **difference_step** from **1e-2** to **1e-12**, graph maximum gradient error, and explain why smaller is not always better.
6. Change MSE from **mean** to **sum**, derive the new gradient, and explain why learning rate needs reselection.
7. Write a stop and audit record for loss falling while validation metric worsens.

## Common errors and troubleshooting

- Finite difference and analytical gradient use different data, reduction, or parameter point.
- Difference step is too large for truncation error or too small for floating-point cancellation.
- Checking only that final parameters approach an answer, rather than initial gradient direction.
- Leaving divergence as huge values running instead of stopping after recording learning rate, step, and first anomalous location.
- Claiming exact training fit proves model generalization or causal explanation.
- Keeping an old learning rate after input scaling without checking curvature and gradient scale.

## Mastery check

- [ ] I can explain integration as accumulation and derivatives as local change.
- [ ] I can derive MSE gradients for $w,b$ by hand.
- [ ] I verify with finite differences instead of only observing final loss.
- [ ] I can explain the relationship between learning rate and scale.
- [ ] I know passing training loss does not prove online effectiveness.
- [ ] I can explain what the nine tests each prevent.
- [ ] I treat non-finite values and sharply growing loss as explicit failure.

## References

Sources were checked on **2026-07-14**.

- [MIT OpenCourseWare: 18.01SC Single Variable Calculus](https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/)
- [Google ML Crash Course: Gradient Descent](https://developers.google.com/machine-learning/crash-course/linear-regression/gradient-descent)
- [Google ML Crash Course: Hyperparameters](https://developers.google.com/machine-learning/crash-course/linear-regression/hyperparameters)
- [PyTorch: Gradcheck mechanics](https://docs.pytorch.org/docs/stable/notes/gradcheck.html)

Return to [[calculus/00-index|Calculus Fundamentals]].
