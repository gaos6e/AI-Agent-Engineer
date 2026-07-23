---
title: "Sparse, Dense, and Hybrid Retrieval"
tags:
  - ai-agent-engineer
  - semantic-search
  - hybrid-search
aliases:
  - Hybrid recall
  - Hybrid Retrieval
source_checked: 2026-07-14
source_baseline: "Original BM25/RRF research; DPR/SPLADE papers; Elasticsearch
  and Qdrant official hybrid-retrieval documentation through 2026-07-14"
lang: en
translation_key: 语义搜索/04-稀疏稠密与混合检索.md
translation_source_hash: fd1b6bc633a807677bf0b39099d67afeda4f9e2f96a5be65eac8407092a62e76
translation_route: zh-CN/语义搜索/04-稀疏稠密与混合检索
translation_default_route: zh-CN/语义搜索/04-稀疏稠密与混合检索
---

# Sparse, Dense, and Hybrid Retrieval

## Learning objective

This lesson starts with two failures of one query: a lexical system misses a paraphrase, while a dense system may ignore error codes and numbers. The goal is not to memorize product APIs. It is to create reproducible BM25-only, dense-only, and hybrid baselines, understand why fusion can work, and know when it can worsen results.

## Minimum intuition for BM25

BM25 is a term-based ranking function. For query term t and document d, one common form is:

$$
\operatorname{BM25}(q,d)=
\sum_{t\in q}
\log\left(1+\frac{N-n_t+0.5}{n_t+0.5}\right)
\frac{f(t,d)(k_1+1)}
{f(t,d)+k_1\left(1-b+b\frac{|d|}{\operatorname{avgdl}}\right)}
$$

- $N$: number of documents in the candidate corpus;
- $n_t$: number of documents containing t; rarer terms usually receive higher weight;
- $f(t,d)$: frequency of t in the document;
- $|d|/\operatorname{avgdl}$: document-length normalization;
- $k_1$: term-frequency saturation rate;
- $b$: strength of length normalization.

The intuition is that a rare exact term such as E042 should distinguish more than “system”; repeating the same term 100 times should not create 100 times the gain; and long documents naturally contain more terms and need appropriate correction.

The formula is only one part of ranking. How the analyzer segments Chinese, preserves model numbers, and handles synonyms changes t, $n_t$, and document length beforehand. Search products can differ in field handling, boosts, stop words, and implementation details, so copying $k_1=1.2,b=0.75$ does not establish equivalent reproduction.

## The complementary capability of dense retrieval

A dense bi-encoder turns a query and document into fixed-dimensional vectors, then searches nearest neighbors. It may retrieve “duplicate charge on an order” for “my money was charged twice” even though the two share no Chinese two-character term. It may also:

- mix documents from similar topics;
- distinguish E042, model numbers, amounts, or dates poorly;
- ignore negation or condition order;
- fail when training language/domain does not match;
- miss exact neighbors because of ANN parameters.

Dense retrieval should therefore not replace BM25; evaluate it first as an independent channel. If dense-only already beats hybrid, a weak lexical channel may only add noise, and the reverse is also true.

## Learned sparse is a third category, not another name for BM25

Learned-sparse models still output high-dimensional sparse weights that can use inverted-index structures and may expand related terms. SPLADE is a representative research line. Its model revision, vocabulary, sparsity, index size, and training domain also require evaluation; interpretable terms do not guarantee that every weight matches human intuition.

Keep this basic route first:

1. an interpretable BM25/keyword baseline;
2. a dense baseline with a locked contract;
3. simple rank fusion;
4. learned sparse or multi-vector only when needed.

## Why raw scores cannot be added directly

BM25 scores normally have no fixed upper bound. Cosine is often bounded, yet its distribution changes by model and query. A product may also transform it into distance/relevance. Directly computing:

$$0.5\times\text{BM25}+0.5\times\text{cosine}$$

does not mean that the channels “contribute half each”; the larger scale dominates. Linear fusion needs normalization/calibration, weights, missing-candidate treatment, and stability monitoring defined on a validation set.

## Reciprocal Rank Fusion

RRF uses only ranks from each route:

$$
\operatorname{RRF}(d)=
\sum_{r\in R(d)}
\frac{1}{c+\operatorname{rank}_r(d)}
$$

- $R(d)$: routes that contain document d;
- ranks begin at 1;
- c is the rank constant; a larger c makes differences between lower ranks relatively flatter;
- each route contributes only inside its rank window.

RRF avoids raw-score scale problems and rewards documents that appear near the top of several routes. It is not automatically optimal:

- a weak channel can boost a wrong document;
- an overly small rank window truncates complementary candidates;
- ties and deduplication within a channel change rank;
- equal-weight RRF does not express different channel reliability;
- choose constant and window on local validation data.

Separate the original RRF paper from product implementations. The current Elasticsearch RRF retriever exposes `rank_constant`/`rank_window_size`; the current Qdrant Hybrid Queries documentation describes RRF, weighted variants, and other fusion methods. These are product facts as of the source date; defaults and APIs cannot be generalized to every system.

## How the candidate budget flows

If the reranker ultimately receives 20 items, you might first test:

| Stage | Example parameter | What to measure |
| --- | --- | --- |
| BM25 | top 50 | Recall of error codes/proper names; latency |
| Dense | top 50; record ANN candidates separately | Recall of semantic paraphrases; ANN recall |
| RRF | 50-window per route; output 40 | Channel contribution; fused Recall/nDCG |
| Deduplication | At most three chunks per original | Evidence coverage |
| Reranker | Input 40; output 10 | Ranking quality; cost |

The numbers are experimental starting points only. Select windows from your own qrels, tail latency, and downstream budget.

## An explainable example

For q-e042 in the project:

- BM25 returns only error-code document d-02-e042.
- Toy dense gives the general-format document d-01 and the error-code document the same score, then puts d-01 first by ID.
- RRF raises d-02 to first because it appears in both BM25 and dense.
- Graded qrels label d-02 as 3 and d-01 as 1, so hybrid nDCG exceeds dense nDCG.

For q-double-charge, the colloquial phrase “my money was charged twice” misses “duplicate charge” in the BM25 two-character channel, while toy dense retrieves the right document. The examples show complementarity between exact lexical terms and semantic paraphrases; the hand-authored vectors do not prove that a real model will succeed.

## Experiment matrix

Change only one main factor per experiment:

| Experiment | Control | At minimum report |
| --- | --- | --- |
| Analyzer | Words/characters/n-grams, synonyms | Sliced recall; index size |
| Dense model | Same corpus/query/filter | Recall/MRR/nDCG; latency; cost |
| Fusion | BM25, dense, RRF, calibrated linear | Channel contribution; error classification |
| Window | 10/20/50/100 per route | Quality-latency curve |
| Deduplication | None; cap per original | Chunk and original evidence coverage |
| ANN | Exact and parameter combinations | ANN recall and business metrics |

Save data checksums, qrels version, model/index revision, parameters, and random seed; otherwise tables cannot be reproduced.

## Common failures and diagnosis

- **Compare hybrid only to the old system:** add BM25-only and dense-only.
- **Average raw scores directly:** use RRF first, or calibrate explicitly on validation data.
- **Lexical channel lacks an analyzer version:** lock it and rebuild the index.
- **Dense channel forgets the exact/ANN distinction:** use exact top-k as ANN ground truth.
- **Too few candidates survive filters:** slice by filter selectivity and expand candidates or change the execution plan.
- **Fusion cannot be explained:** retain each route’s rank, score, window, and contribution.
- **Only overall means are examined:** report error codes, paraphrases, numbers, negation, and authorization separately.

## Exercise

1. Write three queries each for E042, RTX-5090, refund arrival, and duplicate charges.
2. Predict which sample type BM25 and dense retrieval are most likely to miss.
3. Hand-calculate RRF for two rankings of length three when c=10.
4. Design window experiments with 10, 50, and 100 candidates per route.
5. If dense-only nDCG exceeds hybrid, list at least four diagnostic steps.
6. State calibration data and rollback conditions that linear fusion must retain.

## Mastery checklist

- [ ] Can explain BM25’s IDF, term-frequency saturation, and length normalization.
- [ ] Evaluate both dense paraphrase-recall strengths and number/negation risks.
- [ ] Do not call learned sparse ordinary BM25.
- [ ] Do not add incomparable raw scores directly.
- [ ] Understand RRF constant, rank window, ties, and weak-channel risks.
- [ ] Every fusion experiment has three independent baselines and sliced error analysis.

Next: [[semantic-search/05-query-processing-and-filtering|Query Processing and Filtering]].

## References

- Robertson & Zaragoza, [The Probabilistic Relevance Framework: BM25 and Beyond](https://ir.webis.de/anthology/2009.ftir_journal-ir0anthology0volumeA3A4.0/)
- Karpukhin et al., [Dense Passage Retrieval](https://arxiv.org/abs/2004.04906)
- Formal et al., [SPLADE v2](https://arxiv.org/abs/2109.10086)
- Cormack, Clarke & Buettcher, [Reciprocal Rank Fusion](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf)
- [Elasticsearch: Reciprocal rank fusion](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion)
- [Qdrant: Hybrid and Multi-Stage Queries](https://qdrant.tech/documentation/search/hybrid-queries/)

Sources were obtained on 2026-07-14. Return to the [[semantic-search/00-index|Semantic Search index]].

