---
title: "Similarity, Scores, and Thresholds"
tags:
  - ai-agent-engineer
  - semantic-search
  - relevance
aliases:
  - Interpreting retrieval scores
  - Retrieval Similarity Score
source_checked: 2026-07-22
source_baseline: "pgvector and Qdrant official resources, and the MTEB paper,
  through 2026-07-22"
lang: en
translation_key: 语义搜索/03-相似度分数与阈值.md
translation_source_hash: 087dcce47358091b79b78bc2866b1454342fc9761e5d5917b3d80922c3bca713
translation_route: zh-CN/语义搜索/03-相似度分数与阈值
translation_default_route: zh-CN/语义搜索/03-相似度分数与阈值
---

# Similarity, Scores, and Thresholds

## Learning objective

This lesson addresses three common misconceptions: “a high score means relevant,” “0.8 is a universal threshold,” and “larger top-k is always better.” Afterward, you can confirm score direction and space contracts, choose candidate budgets/thresholds with qrels, and evaluate exact search, ANN, and business relevance separately.

## Three common vector quantities

For vectors x and y:

- **dot product:** $x \cdot y$, normally ranks larger values first and is affected by both direction and magnitude;
- **cosine similarity:** $\frac{x \cdot y}{\lVert x\rVert\lVert y\rVert}$, compares direction and is larger for more similar nonzero vectors;
- **Euclidean/L2 distance:** $\lVert x-y\rVert_2$, where smaller distance is closer.

If x and y are unit vectors, dot product equals cosine, and squared L2 has a monotonic relationship to cosine. A database, however, may return similarity, distance, negative distance, or a transformed relevance score. Verify the field name, operator, and sorting direction against the locked product version.

The [[semantic-search/examples/toy_semantic_search.py|project script]] normalizes all three quantities internally to “larger is better,” using negative distance for Euclidean distance. A real system need not use this design.

## A score is not a relevance probability

Cosine 0.82 describes a geometric relationship in one model space; it does not mean “82% relevant.” Its meaning changes with:

- model, revision, and query/document role;
- corpus domain, language, and text length;
- normalization, quantization, and metric;
- exact/ANN implementation and candidate parameters;
- the candidate distribution after filtering;
- query type and hard-negative density.

Do not compare “higher average cosine” across models or treat a 0.7/0.8 threshold from a public tutorial as a default. When migrating models, compare rankings and business metrics first, then analyze each score distribution.

## Exact search, ANN, and business relevance

Answer these three layers separately:

1. **Exact kNN:** calculates the true nearest neighbors among all authorized candidates by definition.
2. **ANN recall:** assesses whether an approximate index retrieves the exact top-k.
3. **Business relevance:** assesses whether returned documents solve the information need according to qrels.

ANN Recall@k of 1 says only that the approximate index did not miss exact neighbors. If an embedding ranks the wrong topic first, business nDCG can still be poor. Conversely, a small difference between ANN and exact top-k need not harm business metrics.

## Top-k is a candidate budget

First-stage top-k determines what downstream components have a chance to see. Increasing k often increases coverage opportunity, but also increases:

- database, network, and serialization cost;
- reranker/LLM latency and expense;
- near-duplicate documents and noise;
- exposure to authorization, stale-content, and prompt-injection risks.

Define independently the window for each recall route, fusion rank window, number after fusion, reranker input count, and final evidence count. Do not call all of them top-k. Plot Recall@k against latency/cost on a local query set, then choose the budget where benefits flatten.

## A threshold must correspond to a decision

A threshold is not a decorative parameter. It decides “return, search wider, hand off to a human, or no result.” Select it by:

1. defining error cost: is weakly related output or refusal more expensive?
2. collecting scores and labels on independent validation queries/qrels;
3. slicing by language, intent, length, tenant, and time;
4. comparing coverage, precision, recall, and downstream-task success;
5. freezing model/index/threshold versions and evaluating the test set only once;
6. monitoring distribution drift and no-result rate online.

A threshold applies only to a channel compatible with the environment in which it was calibrated. BM25, dense, and reranker raw scores cannot share one cutoff.

## Ranking stability and ties

Equal scores need a stable secondary key such as document ID; otherwise pagination, caching, and regression diffs will fluctuate. Do not rely on exact equality of floating-point values for business decisions, though a deterministic toy fixture can use a stable ID to demonstrate tie-breaking.

RRF operates on rank, so within-channel tie ordering propagates into fusion. Record score, rank, tie-break rule, index revision, and filtering conditions.

## Deduplication and diversity

Adjacent chunks from one original document can fill a candidate list. Optional policies include:

- capping the number of chunks per canonical document;
- exact-hash or near-duplicate clustering;
- keeping the highest-scored result first, then expanding by source or section;
- balancing relevance and repetition with MMR or another diversification rule.

These rules do not guarantee improvement. A multi-hop question can genuinely need several passages from the same document. Evaluate evidence coverage, number of relevant originals, and final task outcome rather than merely whether results “look less duplicated.”

## Fusing incomparable scores

Three safe starting points:

1. **Sort each channel, then apply RRF:** uses only rank and is a strong, easy baseline.
2. **Calibrate/normalize on a validation set, then fuse linearly:** retain the method and parameters.
3. **Train learning to rank:** requires enough non-leaking data that represents online distribution.

Per-query min-max is sensitive to outliers and candidate-window changes, while fixed z-scores drift with distributions. Compare any score treatment with BM25-only, dense-only, and RRF; do not assume it is better because the math is more complex.

## Common failures and diagnosis

- **Distance sorted in the wrong direction:** unit-test with two manually calculated vectors.
- **A zero vector produces NaN:** input gates reject zero/non-finite vectors.
- **An old threshold survives a model change:** recalibrate in the new space.
- **Only average score is measured:** use qrels metrics and sliced errors instead.
- **ACL is applied after top-k:** move hard filtering before scoring.
- **Deduplication loses multi-hop evidence:** report original-document and evidence coverage.
- **ANN quality is treated as business quality:** retain exact ground truth and human qrels together.

## Exercise

1. Calculate dot product, cosine, and L2 for $(1,0)$ and $(0.8,0.6)$, and state each ranking direction.
2. Record dense score, binary relevance, and language for 50 queries, then choose a “return/refuse” threshold.
3. Compare recall, p95, and reranker cost for top-k values 5, 10, 20, and 50.
4. Add a stable tie-break to same-score documents and demonstrate repeated runs are identical.
5. Report ANN Recall@10 and business nDCG@10 separately, explaining why they might move in opposite directions.

## Mastery checklist

- [ ] Metric, direction, normalization, and space revision are explicit for every score.
- [ ] Similarity is not interpreted as a relevance probability.
- [ ] Exact search, ANN recall, and business relevance are validated separately.
- [ ] A threshold maps to a defined action and is calibrated on independent data.
- [ ] Candidate budgets and costs at every stage are named clearly.
- [ ] Deduplication, diversification, and tie-breaking have regression tests.

Next: [[semantic-search/04-sparse-dense-and-hybrid-retrieval|Sparse, Dense, and Hybrid Retrieval]].

## References

- [pgvector: Querying](https://github.com/pgvector/pgvector#querying)
- [Qdrant: Search](https://qdrant.tech/documentation/search/search/)
- Muennighoff et al., [MTEB](https://arxiv.org/abs/2210.07316)

Sources were obtained on 2026-07-22. Return to the [[semantic-search/00-index|Semantic Search index]].

