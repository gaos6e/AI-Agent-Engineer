---
title: "Introduction to Unsupervised Learning"
tags:
  - ai-agent-engineer
  - machine-learning
aliases:
  - Introduction to Clustering and Dimensionality Reduction
source_checked: 2026-07-22
lang: en
translation_key: 机器学习/07-无监督学习入门.md
translation_source_hash: b7a77acbe7181d6d46b3734f32cb2d5a247f2c9a2be45f75106cf3571e2de5f1
translation_route: zh-CN/机器学习/07-无监督学习入门
translation_default_route: zh-CN/机器学习/07-无监督学习入门
---

# Introduction to Unsupervised Learning

## Objectives

Understand that unsupervised learning still assumes a distance, scale, cluster shape, and dimensionality. Use clustering/dimensionality reduction to propose exploratory candidates, then validate them through stability, human spot checks, and downstream value rather than treating algorithmic groups as true labels.

## No labels does not mean no assumptions

Unsupervised learning does not use target labels, but relies on assumptions about distance, density, cluster shape, or low-dimensional structure. Its results are suitable for exploration and candidate generation, not automatic business truth.

## Clustering

K-means finds K centers that make the squared distance from examples to their assigned center as small as possible. It suits approximately spherical, similarly scaled clusters; K must be selected in advance, and it is sensitive to feature scaling and outliers.

In Agent engineering, it can group failure logs or user queries into topic candidates. The correct process is: cluster -> sample-read each cluster -> name/merge them with human judgment -> validate stability on new data. Cluster IDs `0/1/2` have no inherent meaning.

When cluster outcomes affect routing, risk control, or personnel handling, also validate each cluster's coverage, misclassification cost, and possible sensitive-attribute proxy variables. “Unsupervised” does not permit bypassing data minimization, access control, or human review.

## Dimensionality reduction

PCA finds directions retaining the greatest linear variance and is often used for compression, decorrelation, and preliminary visualization. A two-dimensional projection necessarily loses information; proximity in a plot does not guarantee equal proximity in original space.

Be especially cautious with t-SNE/UMAP over embeddings: local structure, random seeds, and hyperparameters affect the picture, and attractive “islands” alone cannot prove that real categories exist.

When an unsupervised transform becomes part of a later supervised model, PCA, vocabulary, scalers, and cluster centers must likewise `fit` only on the training region and then apply to validation/test. Lacking labels does not permit peeking at test distribution; the evaluation boundary depends on the final decision problem.

## How to evaluate

- Internal metrics such as silhouette measure compactness and separation under the current distance definition, not business usefulness.
- Stability: do clusters change substantially with random seed, resampling, or time window?
- Human interpretation: do examples in each cluster have a consistent, actionable theme?
- Downstream value: does clustering help add labels, repair workflow, or improve retrieval?

## Mini exercise

Take 30 Agent failure messages, remove shortcuts such as IDs and timestamps, then use TF-IDF plus K-means to form 3–5 clusters. Sample five from each cluster and record theme, mixed examples, and whether a new error label is worthwhile.

## Common misconceptions

- Set K equal to the number of existing departments and assume the algorithm will recover department boundaries.
- Do not scale numeric features, allowing large-unit fields to dominate Euclidean distance.
- Show only a two-dimensional plot and never inspect original examples.
- Train a classifier on cluster output and call it “human ground truth.”

## Mastery checklist

- [ ] I can state K-means assumptions about distance, scale, cluster shape, and K.
- [ ] I do not treat cluster IDs or two-dimensional “islands” as business truth.
- [ ] I vary random seed, resampling, and time window to inspect stability.
- [ ] I inspect raw examples and use downstream value to decide whether to retain a cluster.
- [ ] I know that unsupervised preprocessing must also respect training/test `fit` boundaries.

Next: [[machine-learning/08-project-ticket-intent-routing|Project: Ticket Intent Routing]].

## References

Review date: **2026-07-22**.

- [scikit-learn: Clustering](https://scikit-learn.org/stable/modules/clustering.html)
- [scikit-learn: Decomposing signals in components](https://scikit-learn.org/stable/modules/decomposition.html)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
