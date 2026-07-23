---
title: "Representations, coordinates, and norms"
tags: [ ai-agent-engineer, vectors, embedding ]
aliases: [ Vectors and norms ]
source_checked: 2026-07-14
source_baseline:
  - Google Machine Learning Crash Course embeddings
  - MIT OpenCourseWare 18.06 linear algebra
lang: en
translation_key: 向量基础/01-表示坐标与范数.md
translation_source_hash: 1836af9ce4063d9111a9b3743d04460a602964f3ecec56e30628fa9185864830
translation_route: zh-CN/向量基础/01-表示坐标与范数
translation_default_route: zh-CN/向量基础/01-表示坐标与范数
---

# Representations, coordinates, and norms

## Goal of this lesson

Understand a vector both as an ordered collection of numbers and as an arrow in a space. You should be able to distinguish dimensions, components, L1/L2 norms, and unit normalization, and understand their engineering constraints in embeddings and retrieval.

## Two views of a vector

$$x=(x_1,x_2,\ldots,x_d)\in\mathbb R^d$$

- **Data view:** an ordered set of $d$ numbers, such as `[length, price, rating]`.
- **Geometric view:** an arrow from the origin to a point in a space, with a direction and a length.

Two vectors can be compared directly only when they belong to the same space, have the same dimension, and come from the same model and version. A 768-dimensional text vector from one model cannot be mixed with a 768-dimensional vector from another model merely because their dimensions match.

## Coordinates and dimension

The components of the two-dimensional vector $(3,4)$ depend on the coordinate basis. An embedding's axes are learned during training, so an individual dimension normally has no stable human meaning; semantics may be distributed over many dimensions. A higher dimensionality does not automatically mean higher quality—it also increases storage and computation.

“Dense” and “sparse” describe storage and the distribution of nonzero components, not whether a vector has many dimensions. A bag-of-words vector may have one hundred thousand dimensions with almost all components equal to zero, while a neural embedding often has fewer dimensions with most components nonzero. Both must still be compared in the same coordinate space.

## Norms

The L2 norm (Euclidean length) is:

$$\|x\|_2=\sqrt{\sum_i x_i^2}$$

The vector $(3,4)$ has length 5. The L1 norm is:

$$\|x\|_1=\sum_i|x_i|$$

The infinity norm is the largest absolute component. Each norm defines “size” and geometry differently; L1 and L2 regularization in optimization therefore create different preferences too.

## Normalization

For a nonzero vector, unit normalization is:

$$\hat x=\frac{x}{\|x\|_2}$$

It preserves direction and makes the L2 length 1. Applied to $(3,4)$, it yields $(0.6,0.8)$. Normalization discards magnitude information; if a model uses magnitude to encode popularity, confidence, or frequency, normalization changes the ranking.

A zero vector cannot be normalized because the divisor is zero. Engineering code must define an explicit policy—reject it, skip it, or use a special value—and must not continue after producing `NaN` values.

Floating-point computation has rounding error. When checking a normalized result, test whether $|\|\hat{x}\|_2-1|$ is below a tolerance instead of requiring a binary floating-point result to equal 1 exactly.

## Uses in ML, embeddings, and evaluation

- Differences in feature scale can cause distance to be dominated by large-valued features.
- Cosine similarity implicitly compares direction only; pre-normalization can simplify computation.
- Gradient clipping often bounds the size of an update by its overall norm.
- The `dimension` in a vector database must match the output of the embedding model.

## Common misconceptions

- Treating vector components as independently nameable concepts.
- Normalizing every vector unconditionally.
- Equating a zero vector directly with “no semantic meaning”; it can also signal a data or model error.
- Comparing similarity across models or model versions.

## Exercises

1. Calculate the L1/L2 norms of `(1,-2,2)` and normalize it. The result should be L1 = 5, L2 = 3, and unit vector `(1/3,-2/3,2/3)`.
2. Explain why `(0,0,0)` cannot be normalized, then choose and justify one API policy: reject, skip, or special value.
3. Compare a 100,000-dimensional sparse bag-of-words vector with a 768-dimensional dense embedding. What differs about dimension, nonzero components, coordinate semantics, and the conditions for comparability?

## Mastery check

- [ ] I can distinguish dimension, length, and number of samples.
- [ ] I check for a zero norm before normalization.
- [ ] I know normalization can discard useful magnitude information.

## References

- [Google ML Crash Course: Embeddings](https://developers.google.com/machine-learning/crash-course/embeddings)
- [MIT OpenCourseWare 18.06 Linear Algebra](https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/)

Sources verified on 2026-07-14. Next: [[vector-fundamentals/02-dot-products-and-cosine-similarity|Dot products and cosine similarity]].
