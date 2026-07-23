---
title: "Vectors, Matrices, and Shapes"
tags: [ ai-agent-engineer, linear-algebra ]
aliases: [ Matrix-shape fundamentals ]
source_checked: 2026-07-14
source_baseline:
  - MIT OpenCourseWare 18.06SC Linear Algebra
  - PyTorch official Linear documentation
lang: en
translation_key: 线性代数/01-向量矩阵与形状.md
translation_source_hash: 4ab349cf48035fbfc4d550f881fc22f2173c5b8f169b6f5325d57a3d022b7176
translation_route: zh-CN/线性代数/01-向量矩阵与形状
translation_default_route: zh-CN/线性代数/01-向量矩阵与形状
---

# Vectors, Matrices, and Shapes

## Objectives

This lesson extends the one-dimensional vectors from the previous lesson to matrices and tensors. The focus is not memorizing notation, but assigning a business meaning to every axis, deriving shapes before computing, and distinguishing matrix multiplication, dot products, and elementwise multiplication.

## Why this matters

The features of one sample form a vector; a batch of samples forms a matrix; model weights are often matrices too. Many ML failures begin as shape errors, not as algorithms that are “too difficult.”

## Scalars, vectors, and matrices

- A scalar $a\in\mathbb R$ is one number, such as a learning rate of 0.01.
- A column vector $x\in\mathbb R^d$ has $d$ ordered components.
- A matrix $X\in\mathbb R^{n\times d}$ has $n$ rows and $d$ columns; a common convention is one sample per row and one feature per column.
- A tensor generalizes scalars, vectors, and matrices to higher dimensions. For example, `batch × sequence × hidden` is a three-dimensional tensor; every axis needs an explicit meaning.

$$x=\begin{bmatrix}2\\3\end{bmatrix},\quad X=\begin{bmatrix}1&2\\3&4\\5&6\end{bmatrix}$$

The shape of $x$ may be written `(2,)` or `(2,1)`; the two can behave differently in a concrete library. $X$ is $3\times2$.

## Basic operations

Same-shape vectors can be added and scaled:

$$\begin{bmatrix}1\\2\end{bmatrix}+\begin{bmatrix}3\\4\end{bmatrix}=\begin{bmatrix}4\\6\end{bmatrix},\quad 2x=\begin{bmatrix}4\\6\end{bmatrix}$$

Matrix multiplication $AB$ requires the number of columns in $A$ to equal the number of rows in $B$:

$$A_{m\times n}B_{n\times p}=C_{m\times p}$$

Its elementwise formula is:

$$C_{ij}=\sum_{k=1}^{n}A_{ik}B_{kj}$$

For example:

$$\begin{bmatrix}1&2\\3&4\end{bmatrix}\begin{bmatrix}5\\6\end{bmatrix}=\begin{bmatrix}17\\39\end{bmatrix}$$

The first component is $1\times5+2\times6=17$. This is different from elementwise multiplication.

Elementwise multiplication of matrices with the same shape is the Hadamard product, written $A\odot B$. It preserves the shape; matrix multiplication contracts adjacent inner dimensions. Do not skip a mathematical-semantic check because a library happens to use `*` or `@`.

## Transpose and the batch view

Transposition exchanges rows and columns: $(X^T)_{ij}=X_{ji}$. If every row is a sample, a linear prediction can be written:

$$
\hat y=Xw
$$

Here $X$ is $n\times d$, $w$ is $d\times1$, and the output is $n\times1$: one computation for $n$ samples.

## Shape ledger

Write one ledger row for every operation:

| Name | Shape | Axis semantics |
| --- | --- | --- |
| `X` | `n × d_in` | samples × input features |
| `W` | `d_out × d_in` | output features × input features |
| `X @ W.T` | `n × d_out` | samples × output features |
| `b` | `d_out` | bias for each output feature |
| `Z` | `n × d_out` | output representation for each sample |

With a column-sample convention, the formula changes, but the semantics must remain consistent. A project may choose either convention; it must not switch silently halfway through.

## Runnable matrix-vector multiplication

```python
from math import fsum


def matvec(matrix: list[list[float]], vector: list[float]) -> list[float]:
    if not matrix or not vector:
        raise ValueError("matrix and vector must be non-empty")
    columns = len(matrix[0])
    if columns != len(vector) or any(len(row) != columns for row in matrix):
        raise ValueError("matrix must be rectangular and inner dimensions must match")
    return [fsum(value * weight for value, weight in zip(row, vector))
            for row in matrix]


assert matvec([[1.0, 2.0], [3.0, 4.0]], [5.0, 6.0]) == [17.0, 39.0]
```

This code prioritizes an inner-dimension check. A real tensor library also handles dtype, device, batch axes, sparse layouts, and broadcasting rules.

## Uses in ML and embeddings

- Token representations often form a `batch × sequence × hidden` tensor; a matrix is a two-dimensional special case of a tensor.
- An embedding table can be viewed as a `vocabulary × dimension` matrix, indexed by token ID.
- A retrieval system stacks document vectors into a matrix to score a query against all documents in one batch.
- The input dimension of a weight matrix must equal the final dimension of its input vector.

## Common pitfalls

- Assuming $AB=BA$. Matrix multiplication is generally not commutative, and the reverse order may not even be valid.
- Ignoring row-vector and column-vector conventions and relying on broadcasting to produce a semantically wrong result.
- Confusing number of dimensions with number of samples.
- Mixing up elementwise multiplication, dot products, and matrix multiplication.
- Reshaping merely because the total number of elements matches; a new shape can change the correspondence among samples, tokens, and features.
- Treating successful broadcasting as semantic correctness without checking which axis receives the bias.

## Exercises and self-check

1. If $X$ is `32×768` and $W$ is `768×128`, what is the output shape? It is `32×128`.
2. Calculate the matrix-vector multiplication above by hand and explain how each row combines with $x$.
3. For `batch=4, sequence=128, hidden=768`, write the business meaning of every axis and explain why it cannot be changed to `512×768` without explanation.
4. Modify `matvec` and write a test for each of a ragged matrix, empty input, and an inner-dimension mismatch.

- [ ] I write shapes before computing.
- [ ] I can explain the inner-dimension condition for matrix multiplication.
- [ ] I can write batched prediction as $Xw$.
- [ ] I can distinguish matrix multiplication, dot products, and elementwise multiplication.
- [ ] I write semantics for axes such as batch, sequence, and feature rather than only writing numbers.

## References

Verified on **2026-07-14**.

- [MIT OpenCourseWare: 18.06SC Linear Algebra](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/)
- [PyTorch: shape conventions for `torch.nn.Linear`](https://docs.pytorch.org/docs/main/generated/torch.nn.Linear.html)

Previous: [[linear-algebra/00a-coordinates-dot-products-norms-and-similarity|Coordinates, dot products, norms, and similarity]] · Next: [[linear-algebra/02-linear-combinations-systems-and-rank|Linear combinations, systems, and rank]].
