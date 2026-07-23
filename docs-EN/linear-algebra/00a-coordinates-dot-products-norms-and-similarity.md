---
title: "Linear Algebra: Coordinates, Dot Products, Norms, and Similarity"
tags:
  - ai-agent-engineer
  - linear-algebra
  - vector-geometry
aliases:
  - Introduction to vector geometry
  - Dot products and norms
source_checked: 2026-07-14
source_baseline:
  - MIT OpenCourseWare 18.06SC Linear Algebra
  - NumPy stable linear algebra documentation
related: "[[linear-algebra/00-index]]"
lang: en
translation_key: 线性代数/00A-坐标点积范数与相似度.md
translation_source_hash: bf0df02ed943088b4cccb7c3f610c1fc45ec86e54c707e57c16eb64e80bec89b
translation_route: zh-CN/线性代数/00A-坐标点积范数与相似度
translation_default_route: zh-CN/线性代数/00A-坐标点积范数与相似度
---

# Linear Algebra: Coordinates, Dot Products, Norms, and Similarity

## Objectives

A vector is not a sequence of numbers without meaning. It normally represents the components of one object along several axes: the features of a sample, quality metrics for a request, or a text embedding. By the end of this lesson, you should be able to distinguish coordinates from the object they represent, calculate dot products, length, distance, and cosine similarity by hand, and know when those quantities can mislead.

## Coordinate-dependent conventions

The two-dimensional vector $x=(3,4)$ says that its first coordinate is 3 and its second is 4. To give it engineering meaning, you must also know:

- what each dimension represents;
- the unit for each dimension;
- whether dimension order is consistent;
- whether centering, scaling, or normalization has been applied; and
- how missing values and outliers are handled.

If you put latency in milliseconds and success rate directly into one vector and compute distance, the numerically larger latency dimension may dominate the result. Linear-algebra formulas do not automatically fix units or data semantics.

## Vector addition and scalar scaling

Vectors of the same dimension are added coordinate by coordinate:

$$
(1,2)+(3,-1)=(4,1)
$$

Scalar scaling multiplies every coordinate by the same number:

$$
2(1,2)=(2,4)
$$

A linear combination $a u+b v$ means “scale first, then add.” Column spaces, linear layers, and low-rank decompositions all build on this operation.

## Dot product: alignment and weighted sum

For two real vectors of the same dimension, the dot product is:

$$
x^Ty=x\cdot y=\sum_{i=1}^{d}x_i y_i
$$

For example, $(1,2)\cdot(3,4)=1\times3+2\times4=11$. The dot product has two complementary intuitions:

1. **Algebraic view**: multiply corresponding components and sum them; this is the weighted sum in a linear model.
2. **Geometric view**: $x\cdot y=\|x\|_2\|y\|_2\cos\theta$, so it depends on both length and angle.

Nonzero vectors with dot product 0 are orthogonal. In two dimensions, that can be understood as perpendicular; in a higher-dimensional space, it still means neither vector has a projection component along the other.

## Norms, distance, and normalization

Euclidean length (the $L_2$ norm) is:

$$
\|x\|_2=\sqrt{\sum_i x_i^2}
$$

The Euclidean distance between two points is the length of their difference vector:

$$
d(x,y)=\|x-y\|_2
$$

A nonzero vector can be normalized to unit length:

$$
\hat x=\frac{x}{\|x\|_2}
$$

Normalization preserves direction and removes length. A zero vector has length 0 and cannot be divided by its own length; an implementation must reject it explicitly or handle it separately.

There are also the $L_1$ norm $\|x\|_1=\sum_i|x_i|$ and the maximum norm $\|x\|_\infty=\max_i|x_i|$. Different norms define different notions of “near,” changing the semantics of regularization, nearest-neighbor search, and robustness.

## Cosine similarity

For two nonzero vectors:

$$
\operatorname{cosine}(x,y)=\frac{x\cdot y}{\|x\|_2\|y\|_2}
$$

In a real vector space it lies in $[-1,1]$: 1 means the same direction, 0 means orthogonal, and -1 means opposite directions. When both vectors are $L_2$-normalized, cosine similarity equals their dot product, and squared Euclidean distance is:

$$
\|\hat x-\hat y\|_2^2=2-2\hat x\cdot\hat y
$$

That does not make a cosine score a “probability of correlation.” Change the embedding model, text domain, language, or preprocessing and both the score distribution and a usable threshold can change. Calibrate thresholds with representative data.

## Runnable standard-library example

```python
from math import fsum, sqrt
from typing import Sequence


def dot(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("vectors must be non-empty and have equal length")
    return fsum(a * b for a, b in zip(left, right))


def norm(vector: Sequence[float]) -> float:
    return sqrt(dot(vector, vector))


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    denominator = norm(left) * norm(right)
    if denominator == 0.0:
        raise ValueError("cosine is undefined for a zero vector")
    return dot(left, right) / denominator


x = (3.0, 4.0)
y = (4.0, -3.0)
assert dot(x, y) == 0.0
assert norm(x) == 5.0
assert abs(cosine(x, y)) < 1e-12
assert abs(norm((x[0] - y[0], x[1] - y[1])) - sqrt(50.0)) < 1e-12
```

This example verifies the formulas; it is not a high-performance vector library. Production code must also check non-finite values, data types, batch shapes, and numerical precision.

## Uses in agent engineering

- Linear models score a feature vector by taking its dot product with weights.
- Embedding retrieval commonly compares normalized vectors with dot product or cosine similarity.
- Attention uses the dot product of a query and key as a relative score, then applies scaling and softmax; the dot product itself is not a final probability.
- Gradients, residuals, and parameter updates can all be viewed as high-dimensional vectors.
- A distance in multi-metric evaluation is trustworthy only when units, scaling, and weights have explicit meaning.

## Common mistakes

- Taking a dot product between vectors with different dimensions or incompatible coordinate semantics.
- Interpreting cosine similarity directly as accuracy, confidence, or causation.
- Forgetting to handle zero vectors, `NaN`, and infinity.
- Claiming that normalization retains the original vector's length information.
- Setting a high-dimensional similarity threshold by intuition without evaluating target data.

## Exercises and self-check

1. Calculate the $L_1$, $L_2$, and $L_\infty$ norms of $(1,2,2)$ by hand.
2. Prove that the squared Euclidean distance between two unit vectors is $2-2\cos\theta$.
3. Construct two vectors with a large dot product but low cosine similarity, and explain the effect of length.
4. Add tests for unequal dimensions, empty vectors, and zero vectors to the standard-library example.
5. Explain why an old similarity threshold cannot be carried over after changing the embedding model.

- [ ] I can explain a vector from its coordinate semantics.
- [ ] I can calculate dot products, norms, distance, and cosine similarity by hand.
- [ ] I know what information normalization removes.
- [ ] I do not treat a similarity score as a probability.

Next: [[linear-algebra/01-vectors-matrices-and-shapes|Vectors, matrices, and shapes]].

## References

Verified on **2026-07-14**.

- [MIT OpenCourseWare: 18.06SC Linear Algebra](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/)
- [NumPy: Linear algebra routines](https://numpy.org/doc/stable/reference/routines.linalg.html)
