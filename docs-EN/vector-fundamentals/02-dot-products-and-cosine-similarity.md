---
title: "Dot products and cosine similarity"
tags: [ ai-agent-engineer, vectors, similarity ]
aliases: [ Cosine similarity ]
source_checked: 2026-07-14
source_baseline:
  - Google Measuring Similarity from Embeddings
  - scikit-learn 1.9.0 pairwise metrics documentation
lang: en
translation_key: 向量基础/02-点积与余弦相似度.md
translation_source_hash: 28cfe3550f16c9541994a90e57fa7db9753ea864400a1a17b491b693edaaea01
translation_route: zh-CN/向量基础/02-点积与余弦相似度
translation_default_route: zh-CN/向量基础/02-点积与余弦相似度
---

# Dot products and cosine similarity

## Goal of this lesson

Calculate dot products and cosine similarity by hand, explain why magnitude changes a dot-product ranking, and draw a clear boundary between normalization, a model's training convention, and the product goal.

## Dot product

$$x\cdot y=\sum_i x_iy_i$$

It can also be written as:

$$x\cdot y=\|x\|\|y\|\cos\theta$$

It depends on both direction and the lengths of the two vectors. $(1,2)\cdot(3,4)=11$. A zero dot product means the vectors are orthogonal in Euclidean geometry; a positive or negative result means their angle is less than or greater than 90°, respectively.

## Cosine similarity

$$\operatorname{cos}(x,y)=\frac{x\cdot y}{\|x\|_2\|y\|_2}$$

For nonzero vectors, the value lies in $[-1,1]$. It compares direction and ignores uniform scaling: `(1,2)` and `(10,20)` have cosine similarity 1.

If every vector is L2-normalized:

$$\operatorname{cos}(\hat x,\hat y)=\hat x\cdot\hat y$$

Some systems can therefore use an inner-product index to implement cosine similarity, but only when both query and document vectors are normalized in the same way.

## A worked comparison

For query $q=(1,1)$:

- $a=(2,2)$: same direction; cosine = 1 and dot product = 4.
- $b=(10,0)$: cosine = $1/\sqrt2\approx0.707$ and dot product = 10.

Dot product places the much larger-magnitude vector $b$ first; cosine places the directionally identical vector $a$ first. Which is correct depends on the embedding's training objective and the product semantics.

## Uses in retrieval

- Dual-encoder models often use dot product as their training and retrieval score; vector magnitude may carry information.
- General text embeddings often recommend cosine or an equivalent normalized dot product, but you must check the model card or official documentation.
- Similarity is a candidate-ranking signal, not proof of factual correctness, answerability, or authorization.
- A high-score threshold cannot be copied across corpora, models, and query types. Calibrate it on a representative labeled set.

## Common misconceptions

- Explaining 0.8 as an “80% probability of relevance.” Cosine is not a probability.
- Assuming negative cosine always means “irrelevant”; validate the distribution and task for the model in use.
- Normalizing the query but not documents, then claiming to use cosine.
- Attributing a large dot product to directional similarity while ignoring magnitude.

## Exercises and self-check

1. Calculate the dot product and cosine for $q=(1,0)$ with `(2,0)`, `(1,1)`, and `(-1,0)`.
2. Prove that squared Euclidean distance between unit vectors is $\|x-y\|^2=2-2x\cdot y$, then explain how cosine ranking and Euclidean-distance ranking relate in this case.

- [ ] I can explain how dot product and cosine differ with respect to magnitude.
- [ ] I do not treat cosine as a probability.
- [ ] I know the metric must match the model's training convention.

## References

- [Google: Measuring Similarity from Embeddings](https://developers.google.com/machine-learning/clustering/dnn-clustering/supervised-similarity)
- [scikit-learn 1.9.0: Cosine similarity](https://scikit-learn.org/stable/modules/metrics.html#cosine-similarity)

Sources verified on 2026-07-14. Next: [[vector-fundamentals/03-distance-normalization-and-high-dimensional-spaces|Distance, normalization, and high-dimensional spaces]].
