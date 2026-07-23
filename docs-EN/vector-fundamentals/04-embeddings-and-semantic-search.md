---
title: "Embeddings and semantic search"
tags: [ ai-agent-engineer, vectors, embedding, retrieval ]
aliases: [ Vector semantic search ]
source_checked: 2026-07-14
source_baseline:
  - Google Machine Learning Crash Course embeddings
  - Google Measuring Similarity from Embeddings
lang: en
translation_key: 向量基础/04-Embedding与语义检索.md
translation_source_hash: 3edfbae03b833ad5b1e4896a9ec7a1ca3f43622dc41f16604e5eb8bc718a2f47
translation_route: zh-CN/向量基础/04-Embedding与语义检索
translation_default_route: zh-CN/向量基础/04-Embedding与语义检索
---

# Embeddings and semantic search

## Goal of this lesson

Connect “object → vector → candidates → filtering/reranking → evaluation” into an auditable path, and understand the separate roles of scores, top-*k*, thresholds, model versions, and relevance labels.

## From object to vector

An embedding model $f$ maps text, images, or other objects to a fixed-dimensional vector:

$$v=f(object)\in\mathbb R^d$$

The training objective makes task-similar objects close in its chosen geometry. An embedding is not a compressed copy of the original content, so it cannot reliably reconstruct every detail; it preserves relationships favored by the training objective.

## A minimal retrieval flow

1. Identify the model and version.
2. Preprocess documents as required by the model and create vectors.
3. Store vectors, document IDs, versions, and filterable metadata.
4. Process the query with the same compatible model.
5. Select top-*k* with the matching metric.
6. Apply authorization and business filters.
7. Optionally rerank the candidates.
8. Evaluate with a labeled relevance set.

Queries and documents may require different prefixes or different encoders. Follow the model documentation; “turn everything into vectors” does not imply identical calls.

## Top-*k* and thresholds

Top-*k* fixes the number of candidates, while a threshold fixes the minimum score. Top-*k* still returns results when no document is relevant; a threshold can return none. They are often combined: retrieve a larger candidate *k*, then filter it with a threshold, metadata, and a reranker.

Calibrate a threshold with representative relevant and irrelevant pairs, and re-evaluate it whenever the model, chunking, or corpus changes. A raw cosine value is not a probability.

## Minimal evaluation

For each query, let $R_q$ be the relevant document set and $S_q^k$ the first $k$ returned documents:

$$Recall@k=\frac{|R_q\cap S_q^k|}{|R_q|}$$

If only one answer document is labeled, Recall@*k* reduces to whether it appears in the top-*k*. You can also inspect Precision@*k*, MRR, and nDCG; choose based on whether multiple documents are relevant, whether ranking order matters, and how complete the labels are.

When $R_q$ is empty, the denominator is zero. Do not silently record that query as a perfect or zero score. Decide the evaluation policy in advance: evaluate its abstention/empty-result behavior separately, or exclude it from this Recall aggregation and report its count separately.

## Versions and migration

Changing an embedding model or dimension normally requires re-embedding the corpus and building a new index. Do not mix vectors from different spaces in one index. A migration should dual-write or build a new version, compare retrieval quality offline, shift traffic gradually, and retain rollback capability.

## Risks and common misconceptions

- Semantic similarity does not establish factual correctness, freshness, or authorization.
- Overly large or small chunks both affect how well a vector represents content; this is a joint Chunking/RAG concern.
- A few queries that “look good” are not an evaluation.
- If vector-store metadata omits the model version, future reconstruction and diagnosis become impossible.
- Generating vectors from sensitive source text is not anonymization; privacy and access control still require governance.

## Exercises and self-check

1. Design the minimum metadata for every vector: document/chunk ID, model, version, dimension, generation time, and content hash.
2. Create relevance sets for five queries and calculate Recall@1 and Recall@3 by hand.
3. Explain when returning “no results” is safer than forcing a top-*k* response.

- [ ] I can draw the complete embedding-retrieval path.
- [ ] I know that a model migration requires a new vector space.
- [ ] I use labeled data to choose *k* and thresholds rather than intuition.

## References

- [Google ML Crash Course: Embeddings](https://developers.google.com/machine-learning/crash-course/embeddings)
- [Google: Embedding space](https://developers.google.com/machine-learning/crash-course/embeddings/embedding-space)
- [Google: Measuring Similarity from Embeddings](https://developers.google.com/machine-learning/clustering/dnn-clustering/supervised-similarity)

Sources verified on 2026-07-14. Next: [[vector-fundamentals/05-project-minimal-vector-retriever|Project: a minimal vector retriever]].
