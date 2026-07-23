---
title: "Linear Combinations, Systems, and Rank"
tags: [ ai-agent-engineer, linear-algebra ]
aliases: [ Linear combinations and rank ]
source_checked: 2026-07-14
source_baseline:
  - MIT OpenCourseWare 18.06SC Linear Algebra
lang: en
translation_key: 线性代数/02-线性组合方程组与秩.md
translation_source_hash: 8b79c196c36603d835709b69b940e70a6ded768ec0ceb311baef8ac9b3003ae8
translation_route: zh-CN/线性代数/02-线性组合方程组与秩
translation_default_route: zh-CN/线性代数/02-线性组合方程组与秩
---

# Linear Combinations, Systems, and Rank

## Objectives

You will understand matrix multiplication as making linear combinations of column vectors, then use span, bases, column spaces, null spaces, and rank to determine whether a system has a solution, whether that solution is unique, and whether a feature set contains redundant directions.

## Linear combinations and span

Given vectors $v_1,v_2$, every $c_1v_1+c_2v_2$ is a linear combination. All possible combinations form their span. The column space of a matrix $A$ is the set of every possible $Ax$.

$$A=\begin{bmatrix}1&0\\0&1\end{bmatrix},\quad Ax=x_1\begin{bmatrix}1\\0\end{bmatrix}+x_2\begin{bmatrix}0\\1\end{bmatrix}$$

Those two columns span the entire two-dimensional plane. If the second column is twice the first, they can span only a line.

A **subspace** is a set closed under vector addition and scalar scaling. A smallest generating set of linearly independent vectors is a **basis**, and its number of vectors is the space's **dimension**. Coordinates depend on the chosen basis; the space itself does not depend on one particular coordinate representation.

## Linear independence and rank

A set of vectors is linearly independent if only setting every coefficient to 0 can make $c_1v_1+\cdots+c_kv_k=0$. Rank is the number of independent row or column directions in a matrix.

$$A=\begin{bmatrix}1&2\\2&4\end{bmatrix}$$

The second column is twice the first, so the rank is 1. It appears to have two features, but it supplies information in only one linear direction.

The row rank of a matrix equals its column rank, so both are simply called rank. For $A\in\mathbb R^{m\times n}$:

$$
0\le \operatorname{rank}(A)\le\min(m,n)
$$

“Full rank” must be interpreted with the shape: a tall matrix can have full column rank, and a wide matrix can have full row rank. Neither statement automatically means a square matrix is invertible.

## The system $Ax=b$

The question $Ax=b$ asks whether $b$ is in the column space of $A$.

- If it is not, there is no exact solution.
- If it is and the columns are independent, there may be a unique solution.
- If it is but redundant directions exist, there may be infinitely many solutions.

Gaussian elimination simplifies a system through valid row operations. The learning goal is not hand-eliminating huge matrices, but understanding pivots, free variables, and rank.

## Null space and uniqueness

The null space contains all $x$ satisfying $Ax=0$. If a nonzero $z$ satisfies $Az=0$, then once $x_0$ solves $Ax=b$, $x_0+tz$ yields the same $b$ for every scalar $t$:

$$
A(x_0+tz)=Ax_0+tAz=b
$$

Thus, full column rank means the null space contains only the zero vector, so parameters cannot drift freely along a hidden direction. A wide matrix has more unknowns than independent constraints and normally has free variables; an algorithm returning one solution does not mean the data uniquely identifies that solution.

## What to record during elimination

Consider the system:

$$
x+2y=3,\qquad 2x+4y=6
$$

Subtracting twice the first row from the second gives a zero row. The first column has a pivot; the second variable is free, so the rank is 1 and the solution has one degree of freedom. Row swapping, nonzero scaling, and adding a multiple of one row to another do not change the solution set. In real floating-point computation, pivot choice and numerical stability matter too: near dependence cannot be classified only by whether something is exactly 0.

## Uses in ML

- Exactly duplicated or linearly dependent features make parameters non-identifiable and numerical solves unstable.
- When $d$ is much larger than the sample count $n$, many parameter vectors can fit the training set equally well, requiring regularization or prior assumptions.
- Low-rank approximations are used to compress weights, reduce dimensionality, and denoise.
- Attention's query, key, and value pass through linear mappings whose effective information is also limited by projection dimension and rank.

## A verifiable example

For the system:

$$x+2y=3,\quad 2x+4y=6$$

the second equation is just twice the first, so it cannot uniquely determine $x,y$; both $(3,0)$ and $(1,1)$ satisfy it. Adding $x-y=0$ provides an independent constraint and gives the unique solution $(1,1)$.

## Common mistakes

- A determinant of 0 is only a signal that a square matrix is not invertible; it does not mean the data are “useless.”
- More features do not imply higher rank; copying a feature adds no information direction.
- Full rank does not guarantee numerical stability; near-linear dependence can yield a large condition number.
- A solvable equation does not mean the solution is reasonable for the domain; noise, units, and constraints still need checking.

## Exercises and self-check

1. Identify redundant directions among `(1,2)`, `(2,4)`, and `(0,1)`.
2. Explain why a regression with few samples and many features may have many solutions.
3. Write the general solution to the system above and give one basis for its null space.
4. Give one `3×2` matrix with full column rank and one `2×3` matrix with full row rank, then explain what “full rank” means in each case.
5. Explain why a solver returning concrete parameters is insufficient evidence that the parameters are uniquely identifiable.

- [ ] I can explain $Ax=b$ from the column space.
- [ ] I can use rank to identify redundant directions.
- [ ] I know that near dependence and exact dependence are different.
- [ ] I can use the null space to explain multiple solutions and distinguish full row rank from full column rank.

## References

Verified on **2026-07-14**.

- [MIT OpenCourseWare: 18.06SC Linear Algebra](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/)
- [MIT 18.06SC Syllabus: column space, null space, bases, and dimension](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/pages/syllabus/)

Previous: [[linear-algebra/01-vectors-matrices-and-shapes|Vectors, matrices, and shapes]] · Next: [[linear-algebra/03-linear-transformations-and-neural-networks|Linear transformations and neural networks]].
