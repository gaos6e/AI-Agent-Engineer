---
title: "Vector Fundamentals"
tags:
  - ai-agent-engineer
  - vectors
  - embedding
aliases:
  - Vector fundamentals learning path
  - Mathematical foundations for vector retrieval
source_checked: 2026-07-22
source_baseline:
  - Google Machine Learning similarity and embeddings guides
  - scikit-learn 1.9.0 pairwise metrics documentation
  - HNSW original paper
ai_learning_stage: "2. Mathematics and data foundations"
ai_learning_order: 15
ai_learning_schema: 2
ai_learning_id: vector-fundamentals
ai_learning_domain: retrieval-and-data
ai_learning_catalog_order: 1500
ai_learning_hard_prerequisites: []
ai_learning_track_rag_order: 750
ai_learning_track_rag_kind: recommended
lang: en
translation_key: 向量基础/00-目录.md
translation_source_hash: b9ff9594ca79b614002d704fd714243010875ff83aee8b47ec8e96fb93faabfc
translation_route: zh-CN/向量基础/00-目录
translation_default_route: zh-CN/向量基础/00-目录
---

# Vector Fundamentals

## Course overview

A vector is both an ordered list of numbers and a geometric object with a direction and a length. Embeddings map text, images, and other objects to vectors; retrieval then uses a similarity measure to find neighbors. This path connects linear algebra with practical semantic search. Its central concern is choosing and evaluating a metric, rather than treating a similarity score as mysterious.

## Where this fits in the overall path

Vector fundamentals belongs to the Mathematics and data foundations stage. After linear algebra, it leads into embeddings, vector databases, semantic search, and RAG. It focuses on how to compare representations, choose a measure, and verify the quality of nearest-neighbor retrieval.

## Learning objectives

- Calculate and explain vector norms, normalization, dot products, and cosine similarity.
- Compare when cosine, dot product, and Euclidean distance are appropriate.
- Understand the basic trade-offs of high-dimensional spaces and approximate nearest-neighbor retrieval.
- Build an embedding-retrieval path and evaluate top-*k* with labeled relevance sets.

## Prerequisites

You should be comfortable with squares, square roots, and loops over lists. [[python-fundamentals/00-index|Python Fundamentals]] is a useful starting point. [[linear-algebra/00-index|Linear Algebra]] helps with coordinates, dot products, norms, and batched matrix computation, but it is not a hard prerequisite for this path.

## Recommended order

1. [[vector-fundamentals/01-representations-coordinates-and-norms|Representations, coordinates, and norms]]: understand components, dimensions, length, and normalization.
2. [[vector-fundamentals/02-dot-products-and-cosine-similarity|Dot products and cosine similarity]]: understand directional similarity and the effect of magnitude.
3. [[vector-fundamentals/03-distance-normalization-and-high-dimensional-spaces|Distance, normalization, and high-dimensional spaces]]: compare Euclidean distance, cosine, and dot product.
4. [[vector-fundamentals/04-embeddings-and-semantic-search|Embeddings and semantic search]]: go from objects to vectors to candidate results.
5. [[vector-fundamentals/05-project-minimal-vector-retriever|Project: a minimal vector retriever]]: implement top-*k* and Recall@*k* with the standard library.

## Hands-on entry point

Start with [[vector-fundamentals/05-project-minimal-vector-retriever|Project: a minimal vector retriever]], then run [[vector-fundamentals/examples/vector_search.py|vector_search.py]] and [[vector-fundamentals/examples/test_vector_search.py|test_vector_search.py]]. The example uses only the Python standard library to implement dot products, norms, unit normalization, cosine, Euclidean distance, top-*k*, and Recall@*k* from first principles. It also shows how vector magnitude, normalization, and metric choice change a ranking.

## Mastery criteria

- [ ] I can calculate L1/L2 norms, a dot product, cosine similarity, and Euclidean distance.
- [ ] I can explain the relationship between dot product and cosine after normalization.
- [ ] I can explain why vector dimension is not an interpretable count of “topics.”
- [ ] I can choose a metric from the model documentation and avoid comparing raw scores across models.
- [ ] I can implement top-*k*, handle zero vectors, and calculate Recall@*k* from labeled relevance data.
- [ ] I can distinguish the speed/recall trade-off between exact search and ANN.
- [ ] I can run the example and its nine tests in both normal mode and `python -O`, and explain why `assert` is not production validation.

## Connections to other knowledge bases

- [[linear-algebra/00-index|Linear Algebra]] supplies the ideas of space, projection, and matrix operations.
- [[embeddings/00-index|Embeddings]] explains how models create vectors; [[vector-databases/00-index|Vector Databases]] covers indexing, filtering, and persistence.
- [[semantic-search/00-index|Semantic Search]], [[reranking/00-index|Reranking]], and [[rag/00-index|RAG]] connect candidate retrieval to a complete answer path.
- [[evaluation-framework/00-index|Evaluation Framework]] and [[benchmark-design/00-index|Benchmark Design]] cover representative query sets, relevance labels, and regression gates.

## Primary references

- [Google ML Crash Course: Embeddings](https://developers.google.com/machine-learning/crash-course/embeddings)
- [Google: Measuring Similarity from Embeddings](https://developers.google.com/machine-learning/clustering/dnn-clustering/supervised-similarity)
- [scikit-learn 1.9.0: Pairwise metrics, affinities and kernels](https://scikit-learn.org/stable/modules/metrics.html)
- [Malkov and Yashunin: HNSW](https://arxiv.org/abs/1603.09320)
- [MIT OCW 18.06 Linear Algebra](https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/)

Verified on 2026-07-14. The mathematical relationships are stable; the `stable` API, ANN implementation, and a model's metric convention can change. Check the version and model card you actually use.
