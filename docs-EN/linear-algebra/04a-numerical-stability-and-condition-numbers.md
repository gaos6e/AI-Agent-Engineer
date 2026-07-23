---
title: "Linear Algebra: Numerical Stability and Condition Numbers"
tags:
  - ai-agent-engineer
  - linear-algebra
  - numerical-stability
aliases:
  - Introduction to condition numbers
  - Ill-conditioned matrices and stable solving
source_checked: 2026-07-14
source_baseline:
  - NumPy stable linear algebra documentation
  - MIT OpenCourseWare 18.06SC Linear Algebra
related: "[[linear-algebra/00-index]]"
lang: en
translation_key: 线性代数/04A-数值稳定性与条件数.md
translation_source_hash: 9f6fe928faaf89f30ec54eb1b932c32cd55920796d5ae29d9125842f570a249b
translation_route: zh-CN/线性代数/04A-数值稳定性与条件数
translation_default_route: zh-CN/线性代数/04A-数值稳定性与条件数
---

# Linear Algebra: Numerical Stability and Condition Numbers

## Objectives

“Invertible” in mathematics is not the same as “reliable” in computation. Floating-point numbers only approximate real numbers, and nearly linearly dependent features amplify input and rounding error. This lesson helps you distinguish rank deficiency from ill-conditioning, understand the role of a condition number, and choose safer solution paths for regression, embedding transformations, and neural-network calculations.

## Three different things

1. **Singular**: a matrix loses directions, so a square matrix is not invertible and some systems do not have a unique solution.
2. **Ill-conditioned**: a matrix may be invertible in exact mathematics, but a tiny input change can cause a large change in its solution.
3. **Algorithmically unstable**: a particular calculation introduces avoidable extra amplification of rounding error.

These can influence one another, but they are not interchangeable. A better algorithm can reduce avoidable error; it cannot recover independent directions that the data do not contain.

## Why floating point introduces error

Computers usually store numbers as finite-precision binary floating-point values. Many decimal fractions cannot be represented exactly, and a long sequence of operations accumulates rounding. Subtracting two similar-sized numbers can cancel many significant digits; this is **catastrophic cancellation**.

For that reason, floating-point results are usually compared with a tolerance instead of requiring every value that is theoretically 0 to match `0.0` bit for bit. A tolerance must account for numerical scale and problem risk; one absolute threshold must not be hard-coded for every situation.

## Condition number: sensitivity to perturbation

For an invertible square matrix under a selected norm:

$$
\kappa(A)=\|A\|\,\|A^{-1}\|
$$

For the 2-norm, it can also be written as the ratio of the largest to smallest singular value:

$$
\kappa_2(A)=\frac{\sigma_{\max}}{\sigma_{\min}}
$$

A condition number close to 1 means directions are scaled relatively evenly. A large value means some directions are nearly flattened, so small input perturbations can be greatly amplified. A singular matrix is treated as having infinite condition number. A condition number is a sensitivity warning, not a probability that a result is wrong, and there is no single dangerous threshold for every dtype, scale, and task.

## A verifiable sensitivity example

Consider two nearly parallel equations:

$$
x+y=2,\qquad x+(1+\varepsilon)y=2+\varepsilon+\delta
$$

When $\delta=0$, the solution is $(1,1)$. If $\varepsilon$ is small, a tiny perturbation $\delta$ on the right-hand side can substantially change the parameters.

```python
def solve_2x2(matrix: tuple[tuple[float, float], tuple[float, float]],
              target: tuple[float, float]) -> tuple[float, float]:
    (a, b), (c, d) = matrix
    e, f = target
    determinant = a * d - b * c
    if determinant == 0.0:
        raise ValueError("matrix is singular")
    x = (e * d - b * f) / determinant
    y = (a * f - e * c) / determinant
    return x, y


delta = 1e-10
for epsilon in (1e-4, 1e-8, 1e-10):
    solution = solve_2x2(
        ((1.0, 1.0), (1.0, 1.0 + epsilon)),
        (2.0, 2.0 + epsilon + delta),
    )
    print(epsilon, solution)
```

As $\varepsilon$ approaches the perturbation scale, the solution changes from nearly `(1,1)` to visibly different values. The explicit two-by-two formula here only demonstrates sensitivity; it is not a recommended general linear-system solver.

## Why not to invert by default

To solve $Ax=b$, express the engineering operation as “solve a linear system,” not as “first calculate $A^{-1}$ and multiply by $b$.” Explicit inversion usually adds computation and rounding error and can conceal rank and conditioning problems.

The least-squares normal equations are:

$$
A^TA\hat x=A^Tb
$$

They are useful for understanding projection, but in the 2-norm, for full-column-rank $A$, the condition number of $A^TA$ is approximately $\kappa_2(A)^2$, which amplifies ill-conditioning. Production libraries normally use QR or SVD. NumPy's official `linalg.lstsq` solves the least-squares problem directly and returns rank and singular values; its small-singular-value cutoff is controlled by `rcond`, whose semantics may change by version. Record the version and parameters when using it.

## Centering, scaling, and regularization

- **Centering** subtracts the mean. It often makes intercept and slope calculations clearer and reduces cancellation caused by large offsets.
- **Scaling** brings features to similar magnitudes, improving optimization and numerical conditioning; it does not eliminate strict linear dependence.
- **Removing or merging redundant features** directly addresses repeated information.
- **Regularization** changes the objective problem, trading bias for stability; it is not a lossless repair of the original problem.
- **Higher precision** can reduce rounding error but cannot repair erroneous data or unidentifiable parameters.

Any preprocessing must be fitted on training data and applied with the same parameters to validation and production data; otherwise it creates leakage or a training-serving mismatch.

## Linear-algebra API checklist

1. State input shape, dtype, units, and numerical range.
2. Check for `NaN`, infinity, duplicate columns, and near-constant columns.
3. Choose `solve`, `lstsq`, QR, or SVD instead of unconditional `inv`.
4. Record rank-decision thresholds, `rcond`, library version, and hardware dtype.
5. Check residuals, relative error, and sensitivity to small perturbations.
6. Re-evaluate the real task after dimensionality reduction or regularization.
7. Do not treat “the algorithm returned a result” as “the problem is identifiable and the result is trustworthy.”

## Common mistakes

- “The determinant is nonzero, so the system must be stable.”
- “More decimal places can restore a lost feature direction.”
- “Standardization removes every linear dependency.”
- “A large condition number guarantees poor model generalization.” A condition number describes numerical and problem sensitivity; generalization also depends on data, objectives, regularization, and evaluation.
- “SVD automatically discovers semantically meaningful business directions.” SVD finds algebraic directions; interpretation still requires external evidence.

## Exercises and self-check

1. Run the sensitivity code with `delta=0`, `1e-12`, and `1e-8`, and record the parameter changes.
2. Explain why duplicating a feature causes rank deficiency while adding an almost identical feature causes ill-conditioning.
3. Compare the role of normal equations for understanding least squares with the role of QR/SVD for solving it.
4. For a `float16` neural-network inference problem, list shape, scale, overflow, and tolerance checks.
5. Explain why regularization changes the problem instead of merely making the solver “smarter.”

- [ ] I can distinguish singularity, ill-conditioning, and algorithmic instability.
- [ ] I can explain a condition number using singular-value intuition.
- [ ] I know why explicit inversion is not the default.
- [ ] I check rank, residuals, scale, dtype, and perturbation sensitivity.

Previous: [[linear-algebra/04-orthogonality-projection-and-least-squares|Orthogonality, projection, and least squares]] · Next: [[linear-algebra/05-eigenvalues-svd-and-least-squares-project|Eigenvalues, SVD, and the least-squares project]].

## References

Verified on **2026-07-14**.

- [NumPy: `linalg.lstsq`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html)
- [NumPy: conditioning warning for `linalg.inv`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.inv.html)
- [NumPy: Linear algebra routines](https://numpy.org/doc/stable/reference/routines.linalg.html)
- [MIT OpenCourseWare: 18.06SC Linear Algebra](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/)
