---
title: "Eigenvalues, SVD, and the Least-Squares Project"
tags: [ ai-agent-engineer, linear-algebra, project ]
aliases: [ SVD and dimensionality reduction ]
source_checked: 2026-07-14
source_baseline:
  - MIT OpenCourseWare 18.06SC Linear Algebra
  - NumPy stable SVD and lstsq documentation
lang: en
translation_key: 线性代数/05-特征值SVD与项目.md
translation_source_hash: 283f48ac50b3ba43c046bbc4bb581fe8c51cf0c5cd4f31f45ee13b4cd7ea8e01
translation_route: zh-CN/线性代数/05-特征值SVD与项目
translation_default_route: zh-CN/线性代数/05-特征值SVD与项目
---

# Eigenvalues, SVD, and the Least-Squares Project

## Objectives

Build intuition for the directions along which a matrix scales using eigenvalues and SVD, then complete a tested least-squares project that has no third-party dependency and defines its input contract. The focus is explaining direction, rank, residuals, and numerical boundaries rather than treating decomposition functions as black boxes.

## Eigenvectors: directions unchanged by a transformation

For nonzero $v$, if:

$$Av=\lambda v$$

then $v$ is an eigenvector and $\lambda$ is an eigenvalue. The transformation only scales or flips the vector along that direction. For example, the coordinate-axis directions are eigenvectors of the diagonal matrix `diag(3, 0.5)`.

Uses include analyzing growth or decay in iterative systems, principal directions of a covariance matrix, and curvature in some optimization problems. Not every matrix has enough real eigenvectors, so eigendecomposition is not a universal tool.

Eigenvalues are defined only for square matrices. A matrix representation of one linear transformation changes under a change of basis, but its eigenvalues do not. A real symmetric matrix has orthogonal real eigenvectors, which is why covariance matrices and PCA are particularly convenient. A general real matrix may have complex eigenvalues or may not be diagonalizable.

## SVD: directional decomposition of any matrix

$$A=U\Sigma V^T$$

The columns of $U,V$ are orthogonal directions, and the nonnegative singular values in $\Sigma$ show how strongly each direction is scaled. SVD applies to non-square matrices; the number of nonzero singular values equals the rank.

For $A$ of shape $m\times n$, the exact shapes in a full or reduced SVD depend on the convention; check library documentation in engineering work. Right singular vectors lie in the input space and left singular vectors lie in the output space. Do not exchange them merely because both are called “directions.”

Keeping the largest $k$ singular values gives a low-rank approximation:

$$A_k=U_k\Sigma_kV_k^T$$

It can be used for compression, denoising, and the computational basis of PCA. Choosing $k$ trades information retention against cost; low-variance directions can still contain rare but critical safety signals.

Under the Frobenius norm or the 2-norm, truncated SVD gives the best rank-$k$ approximation. “Best” applies only to that mathematical error; it does not guarantee the best downstream correctness, safety, or semantic interpretability.

## Uses in ML and embeddings

- PCA finds orthogonal directions of greatest data variance and requires centering first; principal components are not causal factors or necessarily the most valuable business signals.
- A low-rank approximation of a weight matrix can reduce parameters and computation, but its task loss needs real evaluation.
- Dimensionality reduction of retrieval vectors can save memory and speed search, but it changes nearest-neighbor ranking.
- Small singular values mean some directions are close to unidentifiable, making a solution sensitive to noise.

## Project: fit a linear model from scratch

Implementation: [[linear-algebra/examples/least_squares.py|least_squares.py]] · Tests: [[linear-algebra/examples/test_least_squares.py|test_least_squares.py]].

### Input and output contract

- `xs` and `ys` are equal-length sequences with at least two observations.
- Every value must be a finite real number; booleans, strings, `NaN`, and infinity are rejected.
- `x` must contain at least two distinct values, otherwise the slope is not identifiable.
- The output `LineFit` records sample count, slope, intercept, MSE, and two residual-orthogonality diagnostics.
- This project fits only one-variable ordinary least squares with an intercept; it makes no claim about causation or production generalization.

The implementation centers $x,y$, computes the closed-form solution with `math.fsum` and `statistics.fmean`, then verifies:

$$
\sum_i r_i=0,\quad \sum_i(x_i-\bar x)r_i=0
$$

### Running and testing

Run from the vault root:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B '.\Knowledge\AI Agent Engineer\docs-EN\linear-algebra\examples\least_squares.py'
python -B -m unittest discover `
    -s '.\Knowledge\AI Agent Engineer\docs-EN\linear-algebra\examples' `
    -p 'test_*.py' `
    -v
```

Expected script output:

```text
observations=5
weight=1.990000 bias=0.090000 mse=0.010200
residual-sum=-0.000000000000
centered-x-dot-residuals=0.000000000000
```

A floating-point zero can display as `-0.000...`; that is not a negative error, only the sign bit after rounding. Test orthogonality with a tolerance rather than requiring printed text to use positive zero.

The eight tests cover an exact line, a two-point line, a noisy fixture and residual orthogonality, row-order invariance, a large coordinate offset, constant $x$, length boundaries, and non-finite, nonnumeric, or boolean input.

> [!success] Verification on 2026-07-14
> Under Python 3.11.9, the program produced the same results in normal mode and `python -O`; all eight `unittest` cases passed, and both Python files passed `py_compile`. The generated `__pycache__` was removed and was not retained as knowledge-base content.

> [!note] NumPy extension layer
> NumPy is not installed locally, so the core project uses only the standard library and was actually run. In a future scientific-computing environment, compare its result with the official `numpy.linalg.lstsq`; it also returns rank and singular values and uses a minimum-$L_2$-norm solution when multiple solutions exist. Record the NumPy version and `rcond` before use; do not copy a one-line call without that context.

## Required extensions

1. Set every $x$ to the same value, observe that the program rejects the fit, and explain it with rank.
2. Add one extreme outlier and compare parameters and MSE.
3. Calculate a small data set by hand to verify that the program is not a black box.
4. Add $10^9$ to every $x$, observe how the centered implementation behaves, then explain why the intercept changes.
5. Construct two nearly identical feature columns and connect them to [[linear-algebra/04a-numerical-stability-and-condition-numbers|Numerical stability and condition numbers]].
6. If you later use NumPy, compare `linalg.lstsq`, do not invert explicitly, and record the library version, `rcond`, rank, and singular values.

## Common mistakes and troubleshooting

- Using `assert` for production input validation; `python -O` removes assertions. This project uses explicit exceptions and an exit status.
- Looking only at MSE rather than checking residuals, a data plot, outliers, and a validation set.
- Calling the non-identifiability caused by all $x$ values being identical “too few samples.” Copying more identical $x$ values still does not increase rank.
- Treating a numerical result as evidence that parameters are stable; an almost-constant $x$ can still be highly sensitive.
- Implementing least squares with an explicit inverse without checking rank, condition number, and the solver contract.

## Mastery check

- [ ] I can explain why eigenvectors and singular vectors are not the same concept.
- [ ] I can use singular values to explain rank and near singularity.
- [ ] I can explain that PCA keeps high variance rather than guaranteeing task optimality.
- [ ] The project has identical output in normal and `-O` modes and all eight tests pass.
- [ ] I can explain the input contract, centering formula, and why residuals are orthogonal.
- [ ] I can distinguish algebraic optimality, numerical stability, and statistical generalization.

## References

Verified on **2026-07-14**.

- [MIT OpenCourseWare: 18.06SC Linear Algebra](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/)
- [MIT 18.06SC: Least Squares, Determinants and Eigenvalues](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/pages/least-squares-determinants-and-eigenvalues/)
- [NumPy: `linalg.svd`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.svd.html)
- [NumPy: `linalg.lstsq`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html)

Return to [[linear-algebra/00-index|Linear Algebra]].
