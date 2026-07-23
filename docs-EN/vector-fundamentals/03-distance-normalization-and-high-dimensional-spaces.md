---
title: "Distance, normalization, and high-dimensional spaces"
tags: [ ai-agent-engineer, vectors, distance ]
aliases: [ Vector distance ]
source_checked: 2026-07-14
source_baseline:
  - Google Measuring Similarity from Embeddings
  - scikit-learn 1.9.0 pairwise metrics documentation
  - HNSW original paper
lang: en
translation_key: 向量基础/03-距离归一化与高维空间.md
translation_source_hash: 04dca29d8febb9619bd10969760f7e1f753118947ac5cf78da9dc55e6e7c6d50
translation_route: zh-CN/向量基础/03-距离归一化与高维空间
translation_default_route: zh-CN/向量基础/03-距离归一化与高维空间
---

# Distance, normalization, and high-dimensional spaces

## Goal of this lesson

Distinguish the direction in which similarity and distance rank results, distinguish sample-level normalization from feature standardization, and understand why high-dimensional retrieval needs both an exact baseline and joint quality/performance evaluation for ANN.

## Euclidean and Manhattan distance

Euclidean distance:

$$d_2(x,y)=\sqrt{\sum_i(x_i-y_i)^2}$$

Manhattan distance:

$$d_1(x,y)=\sum_i|x_i-y_i|$$

The first is straight-line distance; the second is like moving only along coordinate axes. Both depend on scale: if annual income is thousands of times larger numerically than age, unscaled distance is almost entirely determined by income.

## Similarity and distance

Similarity normally ranks larger values closer, while distance ranks smaller values closer. For unit vectors:

$$\|x-y\|_2^2=2-2\cos(x,y)$$

Cosine, dot product, and Euclidean distance can therefore induce equivalent rankings on normalized data (while their numeric direction differs). That does not hold for unnormalized vectors.

## Standardization is not vector normalization

- **Feature standardization:** subtract the mean and divide by the standard deviation for each dataset column so differently scaled features are comparable.
- **Vector normalization:** divide each individual sample vector by its own norm so that its length is 1.

They operate along different axes and serve different purposes. For embeddings, follow the model documentation; for manually engineered structured features, use the distribution, units, and task to decide.

## High-dimensional intuition

High-dimensional spaces resist two-dimensional intuition. Under some distributions, random vectors tend to be nearly orthogonal, the relative gap between nearest and farthest distances can shrink, and data can appear sparse. Adding irrelevant dimensions adds noise to a distance; higher dimension does not guarantee better retrieval. These effects depend on the distribution and metric, so “all high-dimensional distances inevitably become equal” is not an unconditional law.

The “curse of dimensionality” does not mean high dimensions are unusable. It means that the data needed to cover a space grows quickly, and indexes and measures must exploit the structure learned by the model.

## Exact search and ANN

- **Exact search:** calculate the score against every vector. The result is exact, but cost grows with corpus size.
- **Approximate Nearest Neighbor (ANN):** use an index to inspect fewer candidates, trading the possibility of missing true neighbors for speed and memory.

Measure ANN “accuracy” against exact top-*k* by calculating Recall@*k*, alongside latency, throughput, memory, and filtering conditions. Tune index parameters on your own vector distribution.

If exact search and ANN each return $k$ unique results, $|ANN@k\cap Exact@k|/k$ measures ANN recall of exact neighbors. It measures index approximation error, not business relevance Recall@*k*. Business evaluation still requires human or authoritative relevance sets.

## Common misconceptions

- Comparing only average latency without ANN recall.
- Replacing original-space evaluation with a t-SNE or two-dimensional plot's apparent neighbors on a small sample.
- Mixing a cosine index with vectors that were not normalized as required.
- Looking only at aggregate Recall@*k* and ignoring language, length, or domain subgroups.

## Exercises and self-check

1. Calculate the L1/L2 distance from `(0,0)` to `(3,4)`.
2. Expand the squared expression for the unit-vector identity and verify it.
3. Design an ANN experiment: hold queries and exact ground truth fixed, then report Recall@10 and P95 latency.

- [ ] I can distinguish standardization from unit normalization.
- [ ] I know the relationship among the three measures for unit vectors.
- [ ] I can describe ANN's quality/speed trade-off.

## References

- [Google: Measuring Similarity from Embeddings](https://developers.google.com/machine-learning/clustering/dnn-clustering/supervised-similarity)
- [scikit-learn 1.9.0: Pairwise metrics, affinities and kernels](https://scikit-learn.org/stable/modules/metrics.html)
- [Malkov and Yashunin: Efficient and robust approximate nearest neighbor search using HNSW](https://arxiv.org/abs/1603.09320)

Sources verified on 2026-07-14. Next: [[vector-fundamentals/04-embeddings-and-semantic-search|Embeddings and semantic search]].
