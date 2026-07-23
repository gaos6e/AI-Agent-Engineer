---
title: "Distance, Exact Search, and ANN Indexes"
tags:
  - ai-agent-engineer
  - vector-database
  - ann
  - hnsw
aliases:
  - ANN Index Basics
  - Vector indexes
source_checked: 2026-07-14
source_baseline: "The original HNSW and Faiss papers plus Faiss and pgvector
  official materials, checked through 2026-07-14"
lang: en
translation_key: 向量数据库/02-距离精确检索与ANN索引.md
translation_source_hash: 8dc7c4cb7ca2d2648362ab22f3a4b4c51ec8f4ac4fbe0909676b52942ba650d3
translation_route: zh-CN/向量数据库/02-距离精确检索与ANN索引
translation_default_route: zh-CN/向量数据库/02-距离精确检索与ANN索引
---

# Distance, Exact Search, and ANN Indexes

## Learning objectives

You will distinguish similarity from distance and exact kNN from ANN; understand the basic mechanisms of HNSW, IVF, and quantization; use exact top-*k* as a baseline for approximation error; and include real filters, writes, and hardware in experiments.

## First agree on whether larger means more similar or smaller means closer

Common metrics include:

### Cosine similarity

$$
\operatorname{cos}(x,y)=
\frac{x\cdot y}{\lVert x\rVert_2\lVert y\rVert_2}
$$

Larger means more similar. It is undefined for a zero vector.

### Dot product

$$
x\cdot y=\sum_i x_i y_i
$$

Larger means more similar. Without normalization, vector magnitude affects the score.

### Euclidean distance

$$
d_2(x,y)=\sqrt{\sum_i(x_i-y_i)^2}
$$

Smaller means closer. An API may return distance, negative distance, or a similarity score. Read the current official documentation; the field name `score` is not enough.

For unit vectors, cosine, dot-product, and Euclidean-distance rankings are equivalent. They need not be equivalent for non-unit vectors. The metric and normalization must match the space contract in [[embeddings/00-index|Embeddings]].

## Exact kNN

Given an authorized candidate set $D$, calculate the query's score against every vector and take the top-*k*. Its advantages are:

- deterministic behavior under a fixed metric, filter, and tie-breaking rule;
- no ANN approximation misses;
- a convenient small-scale unit-test or offline-quality baseline; and
- a way to validate differences caused by quantization, filtering, and index parameters.

It still does not guarantee business relevance: the exact nearest vector may not be a human gold result. Exact search removes only the error layer of index approximation.

As $N$, vector dimension, or QPS grows, per-item CPU and memory-bandwidth cost can exceed the SLO. ANN is then used.

## Do not conflate two kinds of recall

### ANN Recall@k

Freeze the same data snapshot, space, trusted-identity-derived filter, query, and tie-breaking rule. Let $D_{\mathrm{eligible}}$ be the post-filter searchable set and $K=\min(k, |D_{\mathrm{eligible}}|)$:

$$
\operatorname{ANNRecall@k}
=
\frac{|ANN_K\cap Exact_K|}{K}
$$

It asks, “How many exact neighbors did the approximate index retrieve?” When $K=0$, record `empty_eligible` or not-applicable; do not turn a security-correct empty result into zero. If ANN could return $K$ results but returns fewer, the gap remains low recall or a separate service failure.

### Business Recall@k

Let $Relevant_{\mathrm{eligible}}$ be the gold-relevant items that the same test subject, time, and policy revision **should be allowed to access**:

$$
\operatorname{BusinessRecall@k}
=
\frac{|Retrieved_K\cap Relevant_{\mathrm{eligible}}|}{|Relevant_{\mathrm{eligible}}|}
$$

It asks, “How much human- or behavior-judged relevant evidence was retrieved?” When $Relevant_{\mathrm{eligible}}$ is empty, test the safe assertion that the system has no answer or must not return unauthorized content; do not penalize correct filtering with zero recall.

ANN Recall of 1.0 with low business Recall means the representation or gold labels do not match. Adequate business Recall with slightly lower ANN Recall can mean the missed exact neighbors were not relevant. Report both.

## HNSW intuition

Hierarchical Navigable Small World (HNSW) builds a multilayer neighbor graph:

1. Higher layers are sparse and support large navigation steps.
2. A query starts at an entry point and moves toward closer neighbors.
3. It descends layer by layer to a dense base layer.
4. It returns neighbors from a candidate search range.

Common implementations expose settings resembling:

- graph connectivity (often `M`): a higher value commonly increases memory/build cost and opportunities for connectivity;
- build candidate range (often `ef_construction`); and
- query candidate range (often `ef_search`): a larger range commonly improves recall and also increases latency.

“Commonly” is not a monotonic guarantee. Data distribution, filtering, deletes, concurrency, and implementation affect results. Check parameter names, legal ranges, defaults, and whether settings can change online for the pinned product version.

Typical HNSW advantages are query performance and no need to train coarse centroids first. Costs include graph memory, build time, dynamic-update/delete maintenance, and cold starts.

## IVF intuition

An Inverted File Index (IVF) first trains a coarse quantizer and assigns vectors to cells/lists:

1. Train centroids.
2. Assign each document vector to its nearest list.
3. Find nearby centroids for the query.
4. Scan candidates in only some lists.

Typical parameters include:

- the number of lists (commonly `nlist` in Faiss); and
- the number of lists probed per query (`nprobe`).

Probing more lists commonly improves ANN recall and increases work. If the training sample does not represent the production distribution, cells may be unbalanced or recall can degrade. Monitor drift as new data arrives.

pgvector currently offers HNSW and IVFFlat, and documents their differences in build, query, memory, and training behavior. Treat its repository documentation as authoritative for the concrete operator classes, parameters, and version capabilities.

## Product Quantization and compression

Product Quantization (PQ) divides a vector into subspaces and approximates each part with a codebook, reducing memory and distance-computation bandwidth. Other systems may support scalar, binary, or float16/half-precision representations.

Compression introduces another error layer:

```text
business relevance
  <- embedding representation
  <- dimension reduction
  <- dtype / quantization
  <- ANN traversal
  <- filtering / top-k
```

Save a full-precision exact baseline first, then add dimension reduction, quantization, and ANN one layer at a time. Otherwise, changing the model, PQ, index, and filter parameters at once leaves one uninformative aggregate score.

## Filters change the ANN workload

If you obtain a global ANN top-*k* first and post-filter it, authorized results may be insufficient. If filtering is integrated into graph traversal, selectivity and graph connectivity affect search. If you construct filtered candidates first, a very small set may be better served by exact search.

Current pgvector documentation explains that filtering in an approximate-index query interacts with the PostgreSQL planner/scan and provides iterative-scan capabilities. Dedicated systems such as Qdrant have their own filter-aware mechanisms. Product strategies differ, so build a comparable candidate set for exact and ANN paths using the same filter.

## Index lifecycle

An index is more than its query path:

- CPU, memory, disk, and write impact while the index is built;
- when a new write becomes searchable;
- whether bulk import writes first and builds later or builds while writing;
- whether deletion leaves a tombstone and when it is reclaimed;
- whether updates fragment graphs or lists;
- whether crash recovery rebuilds it;
- whether scaling or migration transfers the index or rebuilds it at the target; and
- whether a parameter change applies online.

A benchmark that measures only steady-state read QPS misses most production cost.

## Reproducible ANN experiments

### Data

- Real document and query vectors.
- A fixed space contract and snapshot/hash.
- Query/gold-label slices.
- Common and low-selectivity filters.
- A realistic update/delete ratio.

Random Gaussian vectors are useful for functional or load sanity checks; they do not substitute for production geometry.

### Exact ground truth

For every query and filter, run exact top-*k* first and save IDs, metric, and tie rules. If the corpus is too large, use a representative subset or offline shard-and-merge process, but document the method.

### Fixed environment

- Product/library and configuration versions.
- CPU/GPU, RAM, disk, and filesystem.
- Single/multithreading, concurrency, and connection pooling.
- Cold-start and warm-up procedure.
- Index-build and query parameters.
- Data volume, dimension, and filter distribution.
- Repeat counts and time windows.

### Report

| Quality | Query | Build/writes | Resources |
| --- | --- | --- | --- |
| ANN Recall@*k*, business Recall/MRR/nDCG | P50/P95/P99, QPS, timeouts | build time, upsert/delete latency, searchable lag | RAM, disk, CPU/GPU, network |
| slices and filter selectivity | cold/warm, concurrency curves | read degradation during writes, rebuild | peaks, not averages alone |

For latency charts, state whether they include network, serialization, filtering, and reranking. Otherwise, reports are not comparable.

## Common failures and investigation

- **High QPS but wrong results:** inspect ANN/business recall and gold labels first.
- **Exact and ANN use different filters:** the ground truth is not comparable.
- **Only query parameters are recorded:** index-build parameters and the data snapshot also determine results.
- **Random vectors support a product conclusion:** switch to real corpus, query, and filter distributions.
- **Writes slow after index construction:** add a mixed read/write workload.
- **Memory does not drop after deletes:** inspect tombstone, compaction, and rebuild semantics.
- **Copying another product's `ef`/`nprobe`:** return to current implementation documentation.
- **An old threshold is kept for a new model:** score scale and vector space have changed.

## Exercises

1. Hand-write exact cosine top-5 over 100 small vectors and use it as an ANN fixture.
2. Design three HNSW query-candidate-range experiments, holding all other parameters fixed, and plot Recall@10 against P95.
3. Specify IVF training-set selection, list count, probe count, and distribution-drift checks.
4. Construct filters with 1%, 10%, and 80% selectivity, then compare exact/ANN result counts and latency.
5. Design a layered experiment: full float → reduced dimension → quantized → ANN.
6. Explain what “ANN Recall fell while business nDCG did not” could mean.

## Mastery check

- [ ] I know the score/distance direction and metric contract.
- [ ] Exact top-*k* removes index approximation only; it is not business truth.
- [ ] I distinguish ANN Recall from business Recall.
- [ ] I can explain HNSW graph search, IVF coarse lists, and PQ compression.
- [ ] Parameter names and defaults are cited only for a pinned product version.
- [ ] Filters, writes, deletes, build, and recovery are part of the benchmark.
- [ ] Model, dimension, quantization, and ANN are tested in layers, so results are attributable.

## Summary and next step

ANN answers “how can we find neighbors faster?” but its output is usable only when tenant, ACL, and business filters are correct. Next: [[vector-databases/03-filtering-and-multitenancy|Filtering and multitenancy]].

## References

- [Malkov & Yashunin, HNSW](https://arxiv.org/abs/1603.09320)
- [Johnson, Douze & Jégou, Billion-scale similarity search with GPUs](https://arxiv.org/abs/1702.08734)
- [Faiss official repository](https://github.com/facebookresearch/faiss)
- [pgvector official repository](https://github.com/pgvector/pgvector)

Sources checked on 2026-07-14. Return to [[vector-databases/00-index|Vector Databases]].
