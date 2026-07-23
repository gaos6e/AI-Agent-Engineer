---
title: "Embeddings"
tags:
  - ai-agent-engineer
  - embedding
  - rag
aliases:
  - Embeddings learning path
  - Text vectorization
source_checked: 2026-07-22
source_baseline: Google MLCC, Sentence Transformers, MTEB, and leading provider
  documentation checked through 2026-07-22; this project uses hand-authored
  vectors from the Python 3.11 standard library
content_origin: original
content_status: dynamic
ai_learning_stage: 4. RAG and knowledge bases
ai_learning_order: 25
ai_learning_schema: 2
ai_learning_id: embedding
ai_learning_domain: retrieval-and-data
ai_learning_catalog_order: 2500
ai_learning_hard_prerequisites: []
ai_learning_track_rag_order: 800
ai_learning_track_rag_kind: core
lang: en
translation_key: Embedding/00-目录.md
translation_source_hash: bbdd541a3321e7895ec86abe872269cae6db819c8c7aab31f9e6cac1f9846254
translation_route: zh-CN/Embedding/00-目录
translation_default_route: zh-CN/Embedding/00-目录
---

# Embeddings

## Course overview

Embeddings map text, images, or other objects to fixed-length numerical vectors, making objects that are related under a model's training objective easier to find in vector space. For an AI Agent Engineer, the important outcome is not a list of floating-point values but a complete space contract:

- the model, revision, and input-role encoding in use;
- the output dimension, normalization behavior, and distance metric;
- whether input was truncated and which revision of the source text a vector represents;
- how batches are reconciled, retried, cached, and billed; and
- how old and new spaces are isolated, evaluated, switched, and rolled back.

Vector proximity is only a candidate-retrieval signal. It does not establish factual correctness, source trustworthiness, user authorization, or answer completeness. Reliable RAG still needs metadata filtering, keyword or hybrid retrieval, reranking, citations, and end-to-end evaluation.

> [!important] Dynamic-fact boundary
> Model names, input limits, dimension options, role parameters, normalization behavior, prices, and SDK APIs change. This course records principles and examples checked through 2026-07-22 only. When implementing, return to the current official documentation or model card for the selected model.

## Where this course fits

[[vector-fundamentals/00-index|Vector Fundamentals]] provides the intuition for dot products, norms, and cosine similarity. [[chunking-strategies/00-index|Chunking Strategies]] defines the evidence text to encode. This course turns queries and documents into comparable representations. [[vector-databases/00-index|Vector Databases]], [[semantic-search/00-index|Semantic Search]], [[reranking/00-index|Reranking]], and [[rag/00-index|Retrieval-Augmented Generation (RAG)]] then use those representations for retrieval and answering.

## Learning objectives

After completing this course, you should be able to:

- explain the progression from one-hot vectors and static word vectors to contextual and sentence/document embeddings;
- explain why similarity depends on training data, objective, input role, and metric;
- select models according to language, domain, task, license, privacy, limits, latency, cost, and a business gold set;
- distinguish query/document encoding, symmetric and asymmetric retrieval, and bi-encoders from rerankers;
- use cosine similarity, dot product, Euclidean distance, and L2 normalization correctly;
- build reconcilable batch jobs, cache keys, failure classes, and quality checks;
- prevent zero vectors, NaN/Inf, dimension errors, silent truncation, and cross-space mixing;
- evaluate candidates with Recall@k, MRR, nDCG, subgroups, latency, and cost; and
- migrate models with dual-index rebuilding, shadow evaluation, atomic switching, and rollback.

## Prerequisites

- [[vector-fundamentals/00-index|Vector Fundamentals]]: vectors, dot products, norms, and cosine similarity.
- [[api/00-index|APIs]]: timeouts, rate limits, retries, and error classification.
- [[chunking-strategies/00-index|Chunking Strategies]]: input boundaries, source hashes, and ACLs.
- Basic Python functions, dataclasses, JSON, and PowerShell.

You can start without training machine-learning models. This course focuses on using and evaluating embeddings; training details go only as far as is necessary to understand the meaning of a space.

## Core terms

| Term | Plain-language explanation | Engineering constraint |
| --- | --- | --- |
| embedding vector | A fixed-length floating-point array a model produces for one input | It must be bound to the model, revision, role, dimension, and preprocessing. |
| embedding space | A coordinate space created by one encoding contract and comparable with its designated metric | Equal dimensions do not make spaces compatible. |
| bi-encoder | Encodes queries and documents separately, then compares vectors quickly | Suitable for large-scale candidate retrieval. |
| query/document role | Distinct task instructions or encoding paths a model defines for queries and corpus text | Call the model according to its official contract. |
| metric | A ranking rule such as cosine, dot product, or distance | It must agree with training, normalization, and index configuration. |
| normalization | Dividing a vector by its L2 norm to make it a unit vector | Do not apply it blindly to every model. |
| exact search | Scores every candidate individually | Useful for small gold sets and ANN ground truth. |
| ANN | Approximate nearest neighbor search | Trades a small amount of recall for speed and memory. |
| space migration | Rebuilding from an old model or contract into a new space | Use isolated dual indexes; never mix writes or searches. |

## Recommended sequence

| Order | Lesson | Learning outcome |
| --- | --- | --- |
| 1 | [[embeddings/01-representation-learning-and-vector-intuition\|Representation learning and vector intuition]] | Explain where vector proximity comes from and where it stops. |
| 2 | [[embeddings/02-model-dimension-and-normalization\|Model, dimension, and normalization selection]] | An auditable model candidate card and comparison experiment. |
| 3 | [[embeddings/03-batching-caching-and-reliability\|Batching, caching, and reliability]] | A recoverable, reconcilable encoding pipeline that does not leak source text. |
| 4 | [[embeddings/04-similarity-indexing-and-space-migration\|Similarity, indexing, and space migration]] | A space contract, dual-index migration, and rollback gates. |
| 5 | [[embeddings/05-evaluation-and-migration-project\|Evaluation and migration project]] | Exact retrieval, metrics, and migration audit for two isolated spaces. |

Complete the lessons in order. Understand representation meaning before choosing a model; define the space contract before calling an API; and freeze business queries plus mechanical reconciliation gates before migration.

## Hands-on entry point

- [[embeddings/examples/evaluate_embedding_space.py|evaluate_embedding_space.py]]: strict loading, vector validation, exact search, ACLs, Recall/MRR/nDCG, subgroups, and migration audit.
- [[embeddings/examples/embedding-fixture.json|embedding-fixture.json]]: two hand-authored teaching spaces with different dimensions and metrics that remain isolated.
- [[embeddings/examples/test_evaluate_embedding_space.py|test_evaluate_embedding_space.py]]: 32 tests for inputs, mathematics, authorization, evaluation, migration, and the CLI. The metric entry points reject duplicate ranked IDs, invalid relevance grades, and fixture values that overflow during float conversion.

From the project root (which contains `docs-CN/`, `docs-EN/`, and `.website/`), run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Prevent __pycache__ files so running the exercise does not pollute the knowledge-base directory.
python -B -W error '.\docs-EN\embeddings\examples\evaluate_embedding_space.py'  # Run retrieval and migration audits for the two offline vector spaces.
python -B -W error -m unittest discover -s '.\docs-EN\embeddings\examples' -p 'test_evaluate_embedding_space.py' -v  # Discover and run the Embeddings example tests verbosely.
```

The project is entirely offline: it downloads no model and requires no API key. Hand-authored vectors can validate contract and metric code, but cannot establish the quality of a real model.

## Mastery checklist

- [ ] I can distinguish one-hot, static-token, contextual-token, sentence/document, and multimodal embeddings.
- [ ] I can explain the distinct responsibilities of bi-encoder retrieval and cross-encoder reranking.
- [ ] My model record includes provider/model/revision, roles or instructions, dimension, dtype, metric, normalization, and input limits.
- [ ] I use variable dimensions or vector compression only when a model explicitly supports them, then reevaluate on business data.
- [ ] My batch job reconciles each item and rejects empty, zero, non-finite, wrong-dimension vectors and silent truncation.
- [ ] My cache key includes the complete space contract and input hash, and vectors inherit the security level of their source text.
- [ ] Queries and documents always come from compatible spaces, and ACLs take effect before scoring.
- [ ] Old and new spaces are physically or logically isolated; queries are encoded and retrieved independently in each.
- [ ] I report per-query results, subgroups, Recall/MRR/nDCG, latency, throughput, storage, and cost.
- [ ] Public leaderboards only narrow candidates; the final decision comes from target corpus and queries.

## Relationship to other courses

| Course | Relationship |
| --- | --- |
| [[vector-fundamentals/00-index\|Vector Fundamentals]] | Explains dot products, norms, distance, and high-dimensional geometry. |
| [[chunking-strategies/00-index\|Chunking Strategies]] | Determines document-embedding input and its hash. |
| [[llm-api-integration/00-index\|LLM API Integration]] | Provides patterns for client timeouts, retries, rate limits, and observability. |
| [[vector-databases/00-index\|Vector Databases]] | Stores vectors, metadata, filter fields, and ANN indexes. |
| [[semantic-search/00-index\|Semantic Search]] | Combines query encoding, filtering, recall, and hybrid retrieval. |
| [[reranking/00-index\|Reranking]] | Applies more detailed query-document interaction to bi-encoder candidates. |
| [[evaluation-framework/00-index\|Evaluation Framework]] | Manages data splits, statistical uncertainty, and release gates. |
| [[rag/00-index\|RAG]] | Tests citation support, answer correctness, and abstention when no answer is available. |

## Primary references

- [Google Machine Learning Crash Course: Embeddings](https://developers.google.com/machine-learning/crash-course/embeddings)
- [Mikolov et al., Efficient Estimation of Word Representations in Vector Space](https://arxiv.org/abs/1301.3781)
- [Reimers & Gurevych, Sentence-BERT](https://arxiv.org/abs/1908.10084)
- [Sentence Transformers Usage](https://www.sbert.net/docs/sentence_transformer/usage/usage.html)
- [MTEB Overview](https://docs.mteb.org/overview/)
- [MTEB original paper](https://arxiv.org/abs/2210.07316)
- [OpenAI: Vector embeddings](https://developers.openai.com/api/docs/guides/embeddings)
- [Gemini API: Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
- [Cohere: Introduction to Embeddings](https://docs.cohere.com/docs/embeddings)

Sources were obtained or checked on 2026-07-22. Provider documentation describes dynamic facts; verify specific APIs and limits again on the implementation date.
