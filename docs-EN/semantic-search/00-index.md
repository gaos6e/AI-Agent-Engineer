---
title: "Semantic Search Learning Path"
tags:
  - ai-agent-engineer
  - semantic-search
  - information-retrieval
aliases:
  - Semantic Search index
  - Semantic Search learning path
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
source_baseline: Original BM25/RRF research; DPR/BEIR/MTEB papers; Sentence
  Transformers, Elasticsearch, and Qdrant official resources through 2026-07-22
ai_learning_stage: 4. RAG and knowledge bases
ai_learning_order: 27
ai_learning_schema: 2
ai_learning_id: semantic-search
ai_learning_domain: retrieval-and-data
ai_learning_catalog_order: 2700
ai_learning_hard_prerequisites: []
ai_learning_track_rag_order: 1000
ai_learning_track_rag_kind: core
lang: en
translation_key: 语义搜索/00-目录.md
translation_source_hash: 792ead9b0f7b009998b02f77c451f8dd29dbfcece0f5b2c6fcb9b8ca7c3894d8
translation_route: zh-CN/语义搜索/00-目录
translation_default_route: zh-CN/语义搜索/00-目录
---

# Semantic Search

## About this knowledge base

The input to semantic search is not “a string,” but an information need with identity, time, and business conditions. Its output is not a final answer, but a set of traceable, authorized evidence candidates with sufficient recall. A complete first-stage retrieval system commonly combines:

- lexical signals such as keywords/BM25;
- dense-vector signals produced by embeddings;
- optional learned sparse representations;
- hard filters for tenant, ACL, status, language, product, and validity period;
- Reciprocal Rank Fusion (RRF) or calibrated score fusion;
- query-document relevance judgments and offline/online evaluation.

Semantic search is not synonymous with vector similarity: error codes, model numbers, numbers, negation, and proper nouns often need a lexical channel. Nor is “semantically similar” synonymous with “answers the question.” A retrieval system must explain which route produced each candidate, which authorization it satisfies, which representation version it used, and whether it improves business relevance on a local query set.

> [!important] Capability boundary
> [[vector-databases/00-index|Vector Databases]] handles storage, ANN, filter execution, and lifecycle. This course handles queries, recall, fusion, and relevance evaluation. [[reranking/00-index|Reranking]] uses a more expensive joint model to reorder candidates. [[rag/00-index|RAG]] organizes evidence, citations, and answers. Neither a reranker nor a generative model can recover a document completely missed at first stage.

## Where this course fits in the overall route

This knowledge base belongs to the Retrieval and Data domain. In the RAG role track, [[document-parsing/00-index|Document Parsing]], [[chunking-strategies/00-index|Chunking Strategies]], and [[knowledge-base-construction/00-index|Knowledge Base Construction]] create traceable retrieval units; [[embeddings/00-index|Embeddings]] and [[vector-databases/00-index|Vector Databases]] provide dense representations and execution foundations. This course combines them into an evaluable recall system before Reranking. The sequence describes integration order; it does not add entire courses as hard prerequisites.

## Learning objectives

After completing this knowledge base, you can:

- distinguish a user’s words, an information need, a query, a document/chunk, qrels, and a final answer;
- define query/document encoding, text concatenation, truncation, and version contracts for asymmetric retrieval;
- explain the intuition behind BM25 term frequency, document frequency, and length normalization;
- use cosine, dot product, and L2 correctly, rejecting direct comparison of raw scores across models;
- compare independent sparse/keyword, dense, and hybrid baselines;
- use RRF to fuse incomparable channel rankings, and understand the rank window and candidate budget;
- build tenant/ACL filters from a trusted identity, failing closed for an empty identity or abnormal state;
- design a query set that includes paraphrases, error codes, numbers, negation, multilingual queries, no-answer cases, and authorization boundaries;
- distinguish ANN recall, business Recall@k/Hit@k, MRR, nDCG, and safety gates;
- use reproducible experiments to decide whether query rewriting, filtering, fusion, or a model upgrade truly improves the system.

## Prerequisites

- [[vector-fundamentals/00-index|Vector Fundamentals]]: cosine, dot product, distance, and top-k.
- [[embeddings/00-index|Embeddings]]: model roles, space contracts, and migration.
- [[vector-databases/00-index|Vector Databases]]: exact/ANN search, payload filters, and indexes.
- [[data-annotation/00-index|Data Annotation]]: annotation specifications, agreement, and adjudication.
- [[evaluation-framework/00-index|Evaluation Framework]]: later incorporates offline retrieval metrics into system-level evaluation.

You only need to run a Python 3 standard-library script. This course requires no real model, database, or API key.

## Core terminology

| Term | Beginner explanation | Do not confuse it with |
| --- | --- | --- |
| information need | The problem the user actually wants solved | The raw string |
| query | A replayable retrieval request with text, identity, filters, and version | A rewritten form must retain the original query |
| document / passage | A retrieval unit that can be returned, judged, and traced to a source | It should match the unit returned online |
| qrels | Relevance annotations for query-document pairs | A database authorization table |
| sparse / lexical | A term-and-weight representation suited to an inverted index | BM25 and learned sparse retrieval are not the same algorithm |
| dense | Fixed-dimensional nearest-neighbor vector retrieval | Similarity is not a relevance probability |
| first-stage retrieval | Inexpensively produces a larger candidate set | It does not seek perfect final ranking |
| fusion | Combines candidates from multiple routes | Raw scores cannot be assumed to add directly |
| rank window | Maximum candidates per route entering fusion | Final top-k |
| hard filter | Non-negotiable constraints such as tenant, ACL, status, and expiry | Something generation can repair afterward |

## Recommended order

| Order | Lesson | Learning outcome |
| --- | --- | --- |
| 1 | [[semantic-search/01-retrieval-boundaries-and-units\|Retrieval boundaries and units]] | Queries/documents/qrels, relevance grades, and no-answer rules |
| 2 | [[semantic-search/02-query-and-document-representations\|Query and document representations]] | Sparse/dense input, encoding, and version contracts |
| 3 | [[semantic-search/03-similarity-scores-and-thresholds\|Similarity, scores, and thresholds]] | Score direction, candidate budget, thresholds, and deduplication experiments |
| 4 | [[semantic-search/04-sparse-dense-and-hybrid-retrieval\|Sparse, dense, and hybrid retrieval]] | Comparable BM25, dense, and RRF baselines |
| 5 | [[semantic-search/05-query-processing-and-filtering\|Query processing and filtering]] | A degradable query pipeline and fail-closed filters |
| 6 | [[semantic-search/06-recall-and-offline-evaluation\|Recall and offline evaluation]] | Stratified queries/qrels, metrics, error classification, and release gates |
| 7 | [[semantic-search/07-project-offline-hybrid-retrieval\|Project: Offline Hybrid Retrieval]] | A BM25 + toy dense + RRF experiment on a strict fixture |

The first two lessons define what to search and how to represent it. Lessons 3–5 build a safe recall pipeline, lesson 6 establishes evidence, and the project reproduces the results.

## Hands-on project

- [[semantic-search/examples/semantic-search-fixture.json|semantic-search-fixture.json]]: 10 documents, 7 queries, graded qrels, tenant/ACL/status fields, and hand-authored unit vectors.
- [[semantic-search/examples/toy_semantic_search.py|toy_semantic_search.py]]: strict loading, Chinese two-character/BM25 tokenization, exact dense retrieval, RRF, metrics, and a `protected_audit` safety report.
- [[semantic-search/examples/test_toy_semantic_search.py|test_toy_semantic_search.py]]: 34 contract, math, retrieval, authorization, evaluation, and CLI tests, including rejection of duplicate rankings and safety audit across the full candidate window.

From the project root (containing `docs-CN/`, `docs-EN/`, and `.website/`), run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B -W error '.\docs-EN\semantic-search\examples\toy_semantic_search.py' `
    --fixture '.\docs-EN\semantic-search\examples\semantic-search-fixture.json' `
    --top-k 3 `
    --rank-window 5 `
    --rrf-constant 60
```

The fixture’s dense vectors are hand-authored one-hot vectors for testing pipeline causality only. They are not an embedding model and cannot demonstrate Chinese semantic quality. Its tenant/ACL fields are teaching data; a real system must separately implement real identities, authorization, revocation, cache invalidation, and audit access control. The project’s `protected_audit` envelope includes qrels, forbidden-return sets, and the full candidate window, and must not be projected directly to a user.

## Mastery checklist

- [ ] Can write the online query/document unit, relevance grades, and no-answer rules.
- [ ] Query/document representations have model, revision, prefix, truncation, normalization, and metric contracts.
- [ ] Can explain why BM25 favors rare matches and reduces excessive term-frequency gain in long documents.
- [ ] Sparse, dense, and hybrid retrieval are evaluated separately, and fusion records each route’s rank/score.
- [ ] Tenant, ACL, status, and validity take effect before scoring, and an empty identity fails closed.
- [ ] Do not treat a cosine threshold, RRF constant, or vendor default as a universal truth.
- [ ] The query set covers real frequency, high-risk long tails, hard negatives, and authorization boundaries.
- [ ] Report Recall/MRR/nDCG, p95/p99, no-result rate, safety errors, and index freshness.
- [ ] A model or query-pipeline upgrade can replay old requests, compare slices, and roll back.

## Relationship to other knowledge bases

| Knowledge base | Relationship |
| --- | --- |
| [[chunking-strategies/00-index\|Chunking Strategies]] | Determines document/passage boundaries, context, and deduplication units |
| [[embeddings/00-index\|Embeddings]] | Provides dense query/document representations and compatibility contracts |
| [[vector-databases/00-index\|Vector Databases]] | Executes exact/ANN search, payload filters, sharding, and lifecycle |
| [[reranking/00-index\|Reranking]] | Jointly judges query-document relevance on recalled candidates |
| [[rag/00-index\|RAG]] | Consumes authorized candidates and organizes citations and generation |
| [[evaluation-framework/00-index\|Evaluation Framework]] | Connects retrieval metrics and safety gates to end-to-end task quality |
| [[runtime-monitoring/00-index\|Runtime Monitoring]] | Monitors latency, no-results, channel contribution, drift, and freshness |

## Primary references

- Robertson & Zaragoza, [The Probabilistic Relevance Framework: BM25 and Beyond](https://ir.webis.de/anthology/2009.ftir_journal-ir0anthology0volumeA3A4.0/)
- Karpukhin et al., [Dense Passage Retrieval](https://arxiv.org/abs/2004.04906)
- Cormack, Clarke & Buettcher, [Reciprocal Rank Fusion](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf)
- Thakur et al., [BEIR](https://arxiv.org/abs/2104.08663)
- Muennighoff et al., [MTEB](https://arxiv.org/abs/2210.07316)
- [Sentence Transformers: Semantic Search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)
- [Elasticsearch: Reciprocal rank fusion](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion)
- [Qdrant: Hybrid and Multi-Stage Queries](https://qdrant.tech/documentation/search/hybrid-queries/)

Sources were obtained/checked on 2026-07-22. Models, SDKs, product APIs, fusion parameters, and defaults change; after locking versions, validate again with local queries and qrels.
