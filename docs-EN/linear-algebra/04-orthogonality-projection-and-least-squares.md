---
title: "Orthogonality, Projection, and Least Squares"
tags: [ ai-agent-engineer, linear-algebra ]
aliases: [ Least-squares geometry ]
source_checked: 2026-07-14
source_baseline:
  - MIT OpenCourseWare 18.06SC Linear Algebra
  - NumPy stable lstsq documentation
lang: en
translation_key: 线性代数/04-正交投影与最小二乘.md
translation_source_hash: 3666891dbdaacf6db901158bd6b9d67806b5501539c96e68542266ac81bbbd74
translation_route: zh-CN/线性代数/04-正交投影与最小二乘
translation_default_route: zh-CN/线性代数/04-正交投影与最小二乘
---

# Orthogonality, Projection, and Least Squares

## Objectives

You will understand orthogonal projection and least squares as finding the nearest point in a subspace, derive the residual-orthogonality condition, distinguish uniqueness of a fitted value from uniqueness of parameters, and know that normal equations are useful for explanation but should not be mechanically implemented through an explicit inverse.

## Orthogonality and projection

If $u^Tv=0$, the two vectors are orthogonal. Project $b$ onto the direction of a nonzero vector $a$ as:

$$\operatorname{proj}_a(b)=\frac{a^Tb}{a^Ta}a$$

For example, if $a=(1,0)$ and $b=(3,2)$, the projection is $(3,0)$, and the residual $(0,2)$ is orthogonal to $a$.

If $q_1,\ldots,q_k$ are pairwise orthogonal unit basis vectors and are collected as $Q$, then projection onto their column space is:

$$
\hat b=QQ^Tb
$$

An orthogonal basis makes coordinates clear and prevents repeated directions from interfering with one another. Gram–Schmidt constructs an orthogonal basis from independent columns; numerical libraries normally use a more stable QR implementation instead of copying the most naive hand-calculation procedure.

## Why least squares is projection

When $Ax=b$ has no exact solution, find $\hat x$ that minimizes squared residual length:

$$\hat x=\arg\min_x\|Ax-b\|_2^2$$

$A\hat x$ is the point in the column space of $A$ nearest to $b$, and the residual $r=b-A\hat x$ is orthogonal to that column space:

$$A^T(b-A\hat x)=0$$

This gives the normal equations:

$$A^TA\hat x=A^Tb$$

That explains linear regression: predictions lie in the space spanned by feature columns, while the remaining error is orthogonal to every feature column.

If $A$ has full column rank, the parameter solution is unique. If columns are dependent, the closest fitted vector $A\hat x$ may still be unique even though multiple parameter vectors produce it. SVD-based least-squares solvers usually choose one minimum-norm solution; consult the particular API contract.

When $A$ has full column rank, the theoretical projection matrix is:

$$
P=A(A^TA)^{-1}A^T
$$

This identity is for understanding, not a default implementation recommendation. Explicitly forming an inverse adds computational and numerical risk, and the inverse does not exist when rank is deficient. The next lesson uses condition numbers to explain why QR- and SVD-based paths are safer.

## One-variable linear regression

For the model $\hat y=wx+b$, minimize:

$$\sum_i(y_i-(wx_i+b))^2$$

Adding a column of ones to the design matrix incorporates the bias into the parameter vector. The project program uses equivalent closed-form formulas for $w,b$ and checks that the residual sum and the dot product of residuals with centered $x$ are close to 0.

After centering $x_i-\bar x$, slope and intercept are:

$$
\hat w=\frac{\sum_i(x_i-\bar x)(y_i-\bar y)}{\sum_i(x_i-\bar x)^2},\qquad
\hat b=\bar y-\hat w\bar x
$$

A zero denominator means all $x$ values are identical, so the slope cannot be identified from the data. A very small denominator signals an almost-constant feature and a sensitivity risk.

## Numerical and statistical boundaries

- Normal equations are convenient for explanation, but explicitly calculating $(A^TA)^{-1}$ can amplify numerical problems; production libraries normally use QR, SVD, or a dedicated least-squares solver.
- Least squares produces an algebraically optimal fit; it does not automatically satisfy statistical assumptions such as causal interpretation, independent and identically distributed data, or homoscedasticity.
- Outliers are amplified by squared loss. Whether to use a robust loss depends on the data-generating mechanism, not on making a score look better.
- Minimizing training residuals does not imply best generalization. Data splits, noise, overfitting, and uncertainty must be assessed with [[probability-and-statistics/00-index|Probability and Statistics]] and [[machine-learning/00-index|Machine Learning]].

## Connection to embeddings and retrieval

- Projection decomposes a high-dimensional vector into a component in a subspace plus an orthogonal residual.
- Dimensionality reduction preserves major structure in a lower-dimensional subspace.
- Mapping a query into a domain subspace may strengthen relevant directions but can also discard crucial information.
- The dot product and orthogonality used in cosine similarity arise from the same geometry.

## Common pitfalls, exercises, and self-check

1. Calculate by hand the projection of $b=(2,3)$ onto $a=(1,1)$. The coefficient is $5/2$ and the projection is $(2.5,2.5)$.
2. Verify that the residual $(-0.5,0.5)$ has dot product 0 with $a$.
3. Use the three points `(0,1)`, `(1,3)`, and `(2,5)` to calculate slope and intercept by hand.
4. Explain why “the fitted vector may be unique” and “the parameters are not unique” can both be true for dependent columns.
5. Give an outlier scenario that is unsuitable for squared loss, and describe the data mechanism that needs checking.

Pitfalls: the nearest point depends on the selected norm; an $L_2$ nearest point is not optimal under every loss; feature scaling affects regularization and numerical conditioning; and a non-invertible matrix should not be forcibly inverted.

- [ ] I can explain normal equations through projection.
- [ ] I know that engineering code should not default to explicit inversion.
- [ ] I can distinguish algebraic fitting from a statistical causal conclusion.
- [ ] I can write the one-variable closed form and recognize the rank issue caused by a zero denominator.
- [ ] I know that parameter uniqueness depends on column rank.

## References

Verified on **2026-07-14**.

- [MIT OpenCourseWare: Least Squares, Determinants and Eigenvalues](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/pages/least-squares-determinants-and-eigenvalues/)
- [NumPy: `linalg.lstsq`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html)

Previous: [[linear-algebra/03-linear-transformations-and-neural-networks|Linear transformations and neural networks]] · Next: [[linear-algebra/04a-numerical-stability-and-condition-numbers|Numerical stability and condition numbers]].
