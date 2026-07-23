---
title: "Reranking"
tags:
  - ai-agent-engineer
  - reranking
  - information-retrieval
aliases:
  - Reranking learning path
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
source_baseline: BERT, monoT5, RankT5, and RankGPT papers, plus Sentence
  Transformers and Elasticsearch documentation, checked through 2026-07-22
ai_learning_stage: 4. RAG and knowledge bases
ai_learning_order: 28
ai_learning_schema: 2
ai_learning_id: reranking
ai_learning_domain: retrieval-and-data
ai_learning_catalog_order: 2800
ai_learning_hard_prerequisites: []
ai_learning_track_rag_order: 1100
ai_learning_track_rag_kind: core
lang: en
translation_key: Reranking/00-目录.md
translation_source_hash: a4db3d9ae501f158288efb92d5229dec912004e21a0f83e5377ceb4ae6297c45
translation_route: zh-CN/Reranking/00-目录
translation_default_route: zh-CN/Reranking/00-目录
---

# Reranking

## Course overview

Reranking takes an already authorized candidate set from a first-stage retriever, then uses a more expensive model that can inspect a query and document together—or an auditable rule set—to reorder it. It is useful for separating documents that share a topic but do not answer the question, documents with conflicting numbers or conditions, and precise evidence from merely broad relevance. Its hard limit is equally important: a reranker cannot recover a document that never entered its candidate window.

A production-ready reranking path needs more than a model:

- independent budgets for the candidate window and the output top-*n*;
- a contract for the query, candidate text, first-stage rank and score, and source revision;
- a deliberate choice and combination of Cross-Encoder, rules, learning-to-rank (LTR), or LLM approaches;
- long-document truncation, chunk aggregation, and canonical-document deduplication;
- pointwise, pairwise, or listwise data together with confirmed hard negatives;
- validation for the model-output schema, complete IDs, finite scores, and duplicate results;
- safe, observable degradation for timeouts, 5xx responses, empty responses, malformed responses, and capacity limits; and
- candidate recall, nDCG/MRR, p95/p99 latency, cost, and fallback quality.

> [!important] Security boundary
> Hard constraints such as tenant scope, ACLs, status, effective time, and deletion must be enforced in [[semantic-search/00-index|Semantic Search]]. A reranker can recheck inputs as defense in depth, but it must not decide whether unauthorized content is “relevant enough” to show. Both the normal and fallback paths may rank only the same safe candidate set.

## Where this course fits

This course belongs to the Retrieval and Data knowledge domain. In the RAG role track, [[semantic-search/00-index|Semantic Search]] first supplies high-recall candidates; this course improves relevance, precision, and diversity near the top of that set; then [[rag/00-index|Retrieval-Augmented Generation (RAG)]] compresses evidence, cites it, and produces an answer. This is a recommended integration order, not a hard prerequisite chain between three whole courses. Approximate-nearest-neighbor (ANN) settings in [[vector-databases/00-index|Vector Databases]] and the reranker’s own model quality still need separate evaluation.

## Learning objectives

After completing this course, you should be able to:

- compute Candidate Recall@window and explain the reachable quality ceiling of a reranker;
- distinguish the retrieval window, reranking window, output top-*n*, and RAG evidence budget;
- explain the interaction, caching, and computation-cost differences between bi-encoders and cross-encoders;
- define query, title, body, and metadata templates together with tokenizer and truncation policies;
- correctly interpret logits, regression scores, probabilities, and thresholds across queries;
- compare rules, Cross-Encoders, LTR, and pointwise, pairwise, or listwise LLM rerankers;
- construct confirmed hard negatives from high-ranked first-stage false positives;
- rerank passages or chunks from long documents and evaluate aggregation and duplicate-source behavior;
- verify that model outputs contain complete, unique IDs from the input window only, with finite scores;
- design deterministic, safe, observable fallbacks for timeouts, errors, and empty or malformed outputs; and
- report relevance, tail latency, throughput, cost, stability, and end-to-end benefit together.

## Prerequisites

- [[semantic-search/00-index|Semantic Search]]: candidates, qrels, Recall/MRR/nDCG, and filtering.
- [[embeddings/00-index|Embeddings]]: bi-encoders and representation contracts.
- [[data-annotation/00-index|Data Annotation]]: relevance levels, adjudication, and bias.
- [[llm-api-integration/00-index|LLM API Integration]]: timeouts, retries, rate limits, and schemas when you use a hosted or LLM reranker.
- [[evaluation-framework/00-index|Evaluation Framework]]: connecting component metrics to end-to-end objectives.

The course project uses only the Python 3 standard library; it has no model, network, or secret dependency.

## Core terms

| Term | Plain-language explanation | Critical boundary |
| --- | --- | --- |
| candidate window | The candidate set actually passed to the reranker | It determines whether a relevant document can be seen at all. |
| candidate recall | The proportion of positive qrels contained in the window | It is a ranking-quality ceiling, not final nDCG. |
| cross-encoder | A model that jointly encodes the query and one candidate to score them | It must run for every query–candidate pair. |
| pointwise | Score each document independently | Easy to batch, but weaker at list-level comparison. |
| pairwise | Compare candidate A with B for the same query | The number of comparisons and calls increases. |
| listwise | Judge a candidate list at once | Sensitive to window size, order, format, and position bias. |
| hard negative | A high-ranked first-stage candidate confirmed to be irrelevant | An unlabeled candidate is not automatically a negative. |
| output contract | Required IDs, scores, reasons, and version data in a model response | Empty, duplicate, unknown, or non-finite values must trigger fallback. |
| fallback | An evaluated safe path when the model is unavailable | It commonly preserves the safe first-stage order. |

## Recommended sequence

| Order | Lesson | Learning outcome |
| --- | --- | --- |
| 1 | [[reranking/01-boundaries-and-candidate-sets\|Boundaries and candidate sets]] | Input/output contracts, candidate recall, and the safe window. |
| 2 | [[reranking/02-cross-encoder-reranking\|Cross-Encoder reranking]] | Joint encoding, truncation, scores, batching, and calibration. |
| 3 | [[reranking/03-llm-rules-and-hybrid-reranking\|LLMs, rules, and hybrid reranking]] | The priority of hard rules, model judgments, and business policy. |
| 4 | [[reranking/04-candidate-windows-long-documents-and-diversity\|Candidate windows, long documents, and diversity]] | Window curves, passage aggregation, and canonical caps. |
| 5 | [[reranking/05-training-data-and-hard-negatives\|Training data and hard negatives]] | Supervision forms, hard-negative mining, and versioned data without leakage. |
| 6 | [[reranking/06-metrics-latency-cost-and-fallbacks\|Metrics, latency, cost, and fallbacks]] | Component and end-to-end metrics, a failure matrix, and release gates. |
| 7 | [[reranking/07-project-fallback-capable-rule-reranker\|Project: a fallback-capable rule reranker]] | Strict fixtures, output contracts, and safe fallback for four failure modes. |

## Hands-on entry point

- [[reranking/examples/reranker-fixture.json|reranker-fixture.json]]: nine candidates, authorized revisions, graded qrels, time/tenant/ACL boundaries, and window settings.
- [[reranking/examples/toy_reranker.py|toy_reranker.py]]: hard filtering, transparent scoring, output validation, a complete input fingerprint, canonical caps, metrics, and fallback.
- [[reranking/examples/test_toy_reranker.py|test_toy_reranker.py]]: 30 tests for contracts, fingerprint binding, half-open validity boundaries, ranking, failures, security, and the CLI. It rejects candidate or model values that would overflow during float conversion.

From the project root (which contains both `docs-CN/`, `docs-EN/`, and `.website/`), run the normal and timeout paths:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Prevent tests or examples from producing __pycache__ files.
$script = '.\docs-EN\reranking\examples\toy_reranker.py'  # Keep the teaching-reranker path for the following commands.
$fixture = '.\docs-EN\reranking\examples\reranker-fixture.json'  # Keep the strict JSON fixture path; do not retype it manually.

python -B -W error $script --fixture $fixture  # Run the normal provider path and print the protected-audit envelope.
python -B -W error $script --fixture $fixture --failure timeout  # Simulate a timeout and verify that only the safe first-stage fallback is used.
```

The transparent rule score is for validating orchestration, not a Cross-Encoder or LLM quality baseline. The CLI JSON contains candidate IDs, filtering reasons, qrels metrics, and an evidence fingerprint. `visibility=protected_audit` means that it is a protected teaching and audit envelope, not a public response for end users; the label itself does not provide access control.

## Mastery checklist

- [ ] Report Candidate Recall@window before evaluating the reranker.
- [ ] Store first-stage, model, and final rank/score separately.
- [ ] Make query/title/body templates, tokenizer, maximum length, and truncation reproducible.
- [ ] Do not treat Cross-Encoder or LLM scores as general relevance probabilities by default.
- [ ] Derive hard negatives from real candidates and confirm them through annotation.
- [ ] Test long-document and duplicate-source policies for evidence coverage.
- [ ] Return only unique IDs from the input window, with finite scores and complete coverage.
- [ ] Bind authorized revisions and all security/scoring inputs into a complete SHA-256 evidence record.
- [ ] Separate public responses from protected audits containing candidates, filter reasons, or metrics.
- [ ] Send timeouts, errors, and empty or malformed outputs through the same safe fallback.
- [ ] Test the fallback itself for relevance, security, latency, and capacity.
- [ ] Make release gates cover key slices, p99, cost, and end-to-end answer quality.

## Relationship to other courses

| Course | Relationship |
| --- | --- |
| [[semantic-search/00-index\|Semantic Search]] | Produces high-recall, authorized candidates and first-stage provenance. |
| [[chunking-strategies/00-index\|Chunking Strategies]] | Determines the passages and truncation risk the reranker can observe. |
| [[vector-databases/00-index\|Vector Databases]] | ANN and filtering are upstream execution layers, not reranking itself. |
| [[rag/00-index\|RAG]] | Consumes top-*n* evidence and is affected by context budget and order. |
| [[evaluation-framework/00-index\|Evaluation Framework]] | Connects candidate recall and ranking to answer or task quality. |
| [[runtime-monitoring/00-index\|Runtime Monitoring]] | Observes inference queues, timeouts, fallbacks, drift, and cost. |
| [[ai-safety/00-index\|AI Safety]] | Covers unauthorized access, prompt injection, third-party models, and audit risk. |

## Primary references

- Nogueira & Cho, [Passage Re-ranking with BERT](https://arxiv.org/abs/1901.04085)
- Nogueira, Jiang & Lin, [monoT5](https://arxiv.org/abs/2003.06713)
- Zhuang et al., [RankT5](https://arxiv.org/abs/2210.10634)
- Sun et al., [RankGPT](https://arxiv.org/abs/2304.09542)
- [Sentence Transformers: Cross-Encoder Applications](https://www.sbert.net/examples/cross_encoder/applications/README.html)
- [Sentence Transformers: Retrieve & Re-Rank](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)
- [Sentence Transformers: Cross-Encoder Training Overview](https://www.sbert.net/docs/cross_encoder/training_overview.html)
- [Elasticsearch: Semantic reranking](https://www.elastic.co/docs/solutions/search/ranking/semantic-reranking)

Sources checked on 2026-07-22. Model behavior, maximum lengths, service APIs, product capabilities, and prices change over time; verify them against the pinned version and local qrels.
