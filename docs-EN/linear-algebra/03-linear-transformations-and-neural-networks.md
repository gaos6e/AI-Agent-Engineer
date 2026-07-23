---
title: "Linear Transformations and Neural Networks"
tags: [ ai-agent-engineer, linear-algebra ]
aliases: [ Matrix transformations and neural networks ]
source_checked: 2026-07-14
source_baseline:
  - MIT OpenCourseWare 18.06SC Linear Algebra
  - PyTorch official Linear documentation
lang: en
translation_key: 线性代数/03-线性变换与神经网络.md
translation_source_hash: 008b5fb587c0b7709ff7072bed40a0ae0c7037ba14ce8948f8438d449f8da8ed
translation_route: zh-CN/线性代数/03-线性变换与神经网络
translation_default_route: zh-CN/线性代数/03-线性变换与神经网络
---

# Linear Transformations and Neural Networks

## Objectives

This lesson promotes a matrix from a “table of numbers” to a map from an input space to an output space. You will understand why transformed basis vectors determine matrix columns, distinguish a strictly linear transformation from an affine one, relate row-sample and column-vector formulas, and explain why neural networks need nonlinearity.

## Intuition for a linear transformation

A linear transformation $T$ preserves addition and scaling:

$$T(u+v)=T(u)+T(v),\quad T(cu)=cT(u)$$

In finite dimensions, it can be written as $T(x)=Wx$. Each matrix column is the transformed result of the corresponding basis vector, so a matrix is not an isolated table of numbers but a transformation of a space.

If $W$ is $m\times n$, it maps $\mathbb R^n$ to $\mathbb R^m$. Its column space is the set of possible outputs, and its null space contains input directions mapped to zero. Mapping into a higher-dimensional space does not automatically create new independent information, because $\operatorname{rank}(W)\le\min(m,n)$.

## Scaling, rotation, and projection

For two-dimensional scaling:

$$W=\begin{bmatrix}2&0\\0&0.5\end{bmatrix}$$

the first axis is enlarged twofold and the second is halved. A projection can discard dimensions and is therefore usually not invertible. Neural-network linear layers can likewise mix, expand, or compress feature directions.

## The affine transformation $Wx+b$

Strictly speaking, $Wx+b$ is an affine transformation when $b\ne0$, because it does not preserve the origin. ML still commonly calls it a “linear layer”:

$$z=Wx+b$$

If $x\in\mathbb R^{d_{in}}$, $W\in\mathbb R^{d_{out}\times d_{in}}$, and $b\in\mathbb R^{d_{out}}$, then $z\in\mathbb R^{d_{out}}$.

Each output component is a weighted sum of input features plus a bias. Embedding projections, classification heads, and attention's Q/K/V mappings use this structure.

PyTorch's official `torch.nn.Linear` uses a row-sample / final-feature-dimension convention, written $y=xA^T+b$. Its weight shape is `out_features × in_features`, and every input axis except the final one is preserved. Other libraries or papers may use the column-vector form $Wx+b$; match shapes rather than merely matching letters before implementation.

## Why nonlinearity is necessary

Two unbiased linear layers composed together are still one linear layer:

$$W_2(W_1x)=(W_2W_1)x$$

Even with biases, multiple affine layers can be merged into one affine layer. Activation functions allow a model to represent curved and piecewise relationships. Linear algebra efficiently mixes features; nonlinearity breaks the boundary of a single linear mapping.

Two biased layers combine as:

$$
W_2(W_1x+b_1)+b_2=(W_2W_1)x+(W_2b_1+b_2)
$$

Therefore, stacking `Linear` layers without activations, gates, or another nonlinearity does not expand the class of mappings represented by that portion of the network. The training process and parameterization can differ, but the final result is still an affine mapping.

## Bases and coordinates

The coordinates of one vector change with the basis. An individual embedding dimension rarely has a stable human-readable name; meaning is often distributed across several directions. If a model is rotated and relative geometry and downstream weights are changed consistently, its function may be unchanged. Do not casually interpret “dimension 137” as one standalone concept.

## Batched computation

If samples are stacked by rows as $X\in\mathbb R^{n\times d_{in}}$, write:

$$Z=XW^T+\mathbf{1}b^T$$

An implementation library broadcasts $b$ onto every row. Broadcasting is convenient but can conceal shape errors, so always write expected dimensions first.

For example, with `X: 32×768` and `W: 128×768`, `X @ W.T` is `32×128`, and a bias `b: 128` is replicated along the batch axis. Misusing `W @ X.T` may still be computable, but it chooses a different axis order; the next interface must explicitly transpose it back.

## Common pitfalls, exercises, and self-check

- Treating bias as “statistical bias.” Here it is a trainable intercept, with different semantics.
- Assuming that an increase in dimensions must add information; the effective rank of a linear mapping is still limited.
- Assuming every invertible transformation is beneficial; a model may deliberately compress noise.
- Equating many linear-layer parameters with the ability to express arbitrary nonlinearity.
- Calling attention as a whole a linear transformation. Its Q/K/V projections are affine, but dot products, scaling, softmax, and weighted aggregation form a larger computation.

Exercises:

1. For $W$ of shape `128×768` and an input batch `32×768`, write the matrix expression and output shape under the row-sample convention. Explain why $W^T$ is required.
2. Given two layers `(W1,b1)` and `(W2,b2)`, write the combined weight and bias.
3. Construct a two-dimensional projection matrix and identify its column space, null space, and rank.
4. Explain why mapping two dimensions linearly to 100 dimensions does not create 100 independent information directions.

- [ ] I can distinguish linear from affine transformations.
- [ ] I can explain why multiple linear transformations can be merged.
- [ ] I can map shapes to $Wx+b$.
- [ ] I can use column and null spaces to explain which directions a linear layer preserves or loses.
- [ ] I can translate between paper formulas and a framework's row-sample convention.

## References

Verified on **2026-07-14**. Framework shapes and interfaces can change by version; check the current official page before implementation.

- [MIT OpenCourseWare: 18.06SC Linear Algebra](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/)
- [PyTorch: `torch.nn.Linear`](https://docs.pytorch.org/docs/main/generated/torch.nn.Linear.html)

Previous: [[linear-algebra/02-linear-combinations-systems-and-rank|Linear combinations, systems, and rank]] · Next: [[linear-algebra/04-orthogonality-projection-and-least-squares|Orthogonality, projection, and least squares]].
