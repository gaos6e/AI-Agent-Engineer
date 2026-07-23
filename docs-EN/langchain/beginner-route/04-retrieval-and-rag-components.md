---
title: "Retrieval and RAG Components"
aliases:
  - LangChain Retrieval and RAG
tags:
  - langchain
  - retrieval
  - rag
source_checked: 2026-07-20
source_baseline: LangChain Retrieval, langchain-core 1.4.9 source/API and PyPI,
  and NumPy 2.4.6 through 2026-07-20
execution_verified: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: "LangChain/00-初学者路线/04-Retrieval与RAG组件.md"
translation_source_hash: e79684f710d15e3a45aff5b0e7ac5d0215e907f9ca2874535ce6dfa2e111a863
translation_route: zh-CN/LangChain/00-初学者路线/04-Retrieval与RAG组件
translation_default_route: zh-CN/LangChain/00-初学者路线/04-Retrieval与RAG组件
---

# Retrieval and RAG Components

## Objectives

Break RAG into a verifiable data pipeline. Understand how Documents, loaders, splitters, embeddings, vector stores, retrievers, and Agent tools relate in LangChain, and decide when to use 2-step RAG or Agentic RAG.

## What retrieval solves

Knowledge in model parameters is not the same as your latest private material. Retrieval first finds external knowledge fragments for a question, then generation answers from those fragments. LangChain offers unified components and integrations, but a framework does not automatically repair malformed PDFs, bad chunking, missing permissions, or stale indexes.

~~~mermaid
flowchart LR
    subgraph offline["Offline ingestion: untrusted material enters the index"]
        source["source + revision + ACL"] --> parse["parse / clean / scan content"]
        parse --> chunk["split + evidence anchors"]
        chunk --> embedding["embedding"]
        embedding --> index["index + deletable stable IDs"]
    end
    subgraph online["Online query: identity and question enter retrieval"]
        query["query + trusted identity"] --> authorize["authorize / push down ACL filter / process query"]
        authorize --> retrieve["retriever"]
        retrieve --> rerank["authorized candidates: deduplicate / apply business filters / rerank"]
        rerank --> context["controlled context pack"]
        context --> generate["generate or refuse"]
        generate --> citation["citation and evidence validation"]
    end
    index --> retrieve
~~~

Every arrow should be observable and evaluable independently. Start with 5–20 documents that a person can inspect, then increase the data volume.

## LangChain component map

- **Document loader**: reads a file or service into Documents; a successful read does not prove that layout semantics are correct.
- **Text splitter**: partitions content by length, structure, or semantics; chunk size is an experimental parameter, not a fixed answer.
- **Embedding model**: maps text to vectors; version both the model and normalization method.
- **Vector store**: stores vectors and metadata and runs similarity queries; filtering capabilities differ by implementation.
- **Retriever**: returns Documents for a text query. It is a more general read interface than a vector store and is a Runnable callable through `invoke` / `batch`.
- **Authorization filter**: uses the authenticated tenant, scope, and business state to filter before unauthorized fragments leave the data boundary; never trust these fields directly from natural-language user input.
- **Reranker / business filter**: processes only authorized candidates, then performs relevance reranking, deduplication, time policy, or source policy; a reranker must not see unauthorized body text first.
- **Tool**: exposes retrieval to an Agent; the loop becomes more dynamic when the model decides when to call it.

LangChain v1 moved some higher-level imports, including former `langchain.retrievers` and `langchain.indexes` entries, to `langchain-classic`. `BaseRetriever`, vector-store abstractions, and current `langchain_core.indexing` remain in `langchain-core`. When you encounter an old import path, check the migration guide and current API for the specific class; do not summarize all retriever/indexing capabilities as “moved away.”

## Do not guess a score contract across backends

A `score` is not a universal unit. If you change vector stores but keep only a threshold number without its score definition, direction, and version, you can reverse the meaning of “more relevant” and “farther away.”

| API / form | Contract | Boundary verified in this round |
| --- | --- | --- |
| `similarity_search_with_score` | Returns the backend’s raw score; it may be similarity or distance, and implementation defines both range and direction | `InMemoryVectorStore` in `langchain-core==1.4.9` uses descending cosine similarity, where larger is more similar; do not extrapolate to FAISS, databases, or managed services |
| `similarity_search_with_relevance_scores` | Intended contract is normalized `[0,1]` with larger values more relevant, but the concrete implementation must provide the mapping | The current `InMemoryVectorStore` does not implement the relevance mapping and raises `NotImplementedError`; the base-class method does not mean a backend supports it |
| `similarity_score_threshold` retriever | Threshold applies to a relevance score, not an arbitrary raw score | Before selecting it, confirm the backend produces a supported, calibrated relevance score; otherwise define and test threshold semantics in your own adapter |
| Retriever `invoke` / `batch` | Returns `Document` and provides a shared Runnable call surface | Default results do not include raw scores; when a score, routing reason, or trace is needed, define an explicit result contract instead of guessing from a `Document` |

`DeterministicFakeEmbedding` is appropriate for verifying wiring and call shape, not semantic-retrieval quality. In the current implementation it also needs NumPy, while `langchain-core` does not install NumPy automatically. Installing `langchain-core` alone therefore does not guarantee this branch runs.

## Metadata comes before vector-store selection

Consider at least these fields for every fragment:

~~~json
{
  "chunk_id": "policy-v3-section-4-chunk-02",
  "document_id": "policy-v3",
  "title": "Refund Policy",
  "section": "4. Special Cases",
  "version": "3",
  "effective_at": "2026-06-01",
  "access_scope": "support-team",
  "source_path": "policies/refund-v3.md"
}
~~~

Read the fields as follows:

- `chunk_id` is the fragment’s stable primary key for citations, revocation, idempotent updates, and issue reproduction.
- `document_id` associates multiple fragments with one original document version.
- `title` and `section` provide source context for people to read and locate.
- `version` and `effective_at` help retrieval exclude superseded or not-yet-effective material.
- `access_scope` must come from trusted authorization context and is used to enforce permission filtering before generation.
- `source_path` is a traceable source location; whether it may be exposed to a model or user still depends on the data-classification policy.

Write `chunk_id` into `Document.id`; metadata may retain the same value for reconciliation with external systems. Without an ID, some implementations generate a random one, making revocation, reproduction, and idempotent updates difficult. Verify duplicate-ID overwrite/upsert semantics for the selected backend as well.

Implement permission filtering in the retrieval execution layer. Do not retrieve unauthorized material first and then ask the model to “ignore” it. Filter values must come from authenticated, authorized trusted context rather than a user-claimed tenant or scope. Remote backends also need verification that the filter is actually pushed down to the service. Document revocation and version updates depend on stable IDs and a deletable index.

## Trust, egress, and side-effect boundaries

- PDFs, web pages, and tickets read by a loader are untrusted data. They do not gain instruction authority merely by entering `Document.page_content`; separate them from system/developer instructions before model input and test indirect prompt injection.
- A remote embedding service receives the text to encode; a remote vector store retains vectors and usually visible metadata. Before launch, decide field by field which body text, identities, paths, and business labels may leave the boundary.
- Apply ACL, tenant, state, and effective-date checks in model-external code before candidates enter the generation context. If a backend lacks the required filter, narrow the authorized index first or add a trusted gateway; do not hand filtering responsibility to the model.
- “Local” examples such as Chroma and Milvus Lite can still create database directories. Remote services, model downloads, and telemetry also have network or persistence side effects. Teaching commands must state where artifacts are generated and how to clean them up.
- LangSmith tracing is optional observability, not a retrieval prerequisite. Traces can contain queries, document fragments, tool results, and user data; configure sampling, redaction, retention, and access control before explicitly enabling it.

## 2-step RAG and Agentic RAG

| Approach | Data flow | Strength | Main risk |
| --- | --- | --- | --- |
| 2-step RAG | Retrieve once on a fixed path, then generate once | Predictable latency and path; easier to evaluate | Complex questions can need query rewriting or multi-hop retrieval |
| Agentic RAG | The model decides when, how, and how often to retrieve | Flexibly handles open-ended tasks | Loops, cost, missed retrieval, and tool misuse |
| Hybrid | Deterministic retrieval by default, escalating to an Agent when needed | Preserves a baseline while allowing escalation | Routing conditions and two traces need evaluation |

The official Retrieval page lists both a RAG Agent and a 2-step chain as tutorial paths. The engineering recommendation is to establish a 2-step baseline first and introduce a dynamic loop only when data shows fixed retrieval is insufficient.

## Layered evaluation

1. **Parsing**: are headings, tables, page numbers, and paragraphs preserved?
2. **Chunking**: does answer evidence land in usable fragments, or is it truncated?
3. **Retrieval**: what are Recall@k, MRR/nDCG, or manually checked hits, and is permission filtering correct?
4. **Generation**: is the answer evidence-supported, are citations real, and does it refuse when no answer exists?
5. **System**: index version, latency, cost, failure rate, and data freshness.

At minimum, a test set should cover answerable-in-corpus questions, multi-fragment questions, unanswerable-in-corpus questions, stale versions, unauthorized requests, synonymous queries, misspellings, and malicious documents containing prompt injection. Fluent generation cannot compensate for empty retrieval.

Most top-k implementations return the “closest” items even when the question is unrelated, so “unanswerable in the corpus” usually does not mean an empty list. A refusal gate must come from a backend-specific threshold calibrated on a labeled set, an independent sufficiency decision, or both; do not copy another store’s raw-score threshold.

## Common errors and investigation

- Replacing the vector database whenever recall is poor: inspect parsing and chunks first, then compare embeddings and queries.
- Retrieval results lack source IDs: citations, revocation, and error localization are impossible.
- Treating raw similarity as distance, or copying one backend’s threshold direction to another.
- Copying an InMemory callable metadata filter as remote-database syntax without verifying real server-side pushdown.
- Putting fragments into a system message: external text gains inappropriate instruction priority.
- Updating an index without recording the version: production problems cannot be reproduced.
- Evaluating only the final answer: you cannot tell whether failure came from retrieval or generation.

## Practice

### Layer A: establish a framework-independent baseline first

Choose five local Markdown files and manually design 15 questions with expected documents. Do not connect a model yet: implement a keyword baseline, record top-3 hits and errors, then add `chunk_id`, `document_id`, `section`, `version`, and `access_scope` to every fragment. Finally write deterministic responses for “insufficient evidence” and “no result after permission filtering.”

### Layer B: real LangChain Core, offline retrieval contract

`retrieval_layer_b/` corresponds to [[langchain/beginner-route/examples/retrieval_layer_b/in_memory_retrieval.py|in_memory_retrieval.py]], [[langchain/beginner-route/examples/retrieval_layer_b/test_in_memory_retrieval.py|test_in_memory_retrieval.py]], and [[langchain/beginner-route/examples/retrieval_layer_b/requirements.txt|requirements.txt]] in this knowledge base. The example uses transparent three-dimensional keyword teaching embeddings with a real `InMemoryVectorStore`, so it can reliably verify APIs, IDs, metadata, callable filters, raw cosine scores, and Retriever Runnables. It does not prove the semantic quality of real embeddings.

Run the following from the repository root:

~~~powershell
$example = Resolve-Path '.\docs-EN\langchain\beginner-route\examples\retrieval_layer_b'  # Resolve the course example directory to an absolute path.
Push-Location $example  # Enter the example directory temporarily so requirements and script-relative paths remain stable.
try {  # Restore the original working directory even if any command fails.
    uv run --isolated --with-requirements '.\requirements.txt' python -B '.\in_memory_retrieval.py'  # Run the offline retrieval demonstration in a one-off isolated environment.
    uv run --isolated --with-requirements '.\requirements.txt' python -B -m unittest -v '.\test_in_memory_retrieval.py'  # Run the full retrieval-contract test suite in normal mode.
    uv run --isolated --with-requirements '.\requirements.txt' python -B -O -m unittest -v '.\test_in_memory_retrieval.py'  # Verify that validation logic does not depend on bare assert statements removed by optimization.
    uv run --isolated --with-requirements '.\requirements.txt' python -B -W error -m unittest -v '.\test_in_memory_retrieval.py'  # Treat every unhandled warning as a test failure.
    uv run --isolated --with-requirements '.\requirements.txt' python -B -O -W error -m unittest -v '.\test_in_memory_retrieval.py'  # Cover the optimized, strict-warning environment too.
} finally {  # Clean up the directory stack whether execution succeeds or fails.
    Pop-Location  # Return to the location from before entering the example directory.
}
~~~

`requirements.txt` pins the direct dependencies for this round, `langchain-core==1.4.9` and `numpy==2.4.6` compatible with Python 3.11; it is not a complete transitive-dependency lockfile. Only installation accesses a package index. The scripts do not call a model or remote service and disable LangSmith tracing for the invocation scope with `tracing_context(enabled=False)`. The 2026-07-22 acceptance run passed all 17 tests in normal, `-O`, `-W error`, and `-O -W error` modes. CLI output includes dependency versions, the sole authorized hit `alpha:refund:v1`, and stable document IDs corresponding to `invoke` / `batch`.

> [!important] Layer B security boundary
> The InMemory callable filter runs before scoring in this process, so it proves call shape but is not server-side ACL for a remote database. `batch()` can use a thread pool by default, while this example’s store is read-only; do not silently add concurrent writes to the same example. Its `0.5` threshold applies only to the transparent teaching vectors and is not a production threshold.

## Self-check

- [ ] Draw the indexing and query phases and name an evaluable metric for each.
- [ ] Explain why a retriever is more general than a vector store.
- [ ] Explain the engineering advantages of 2-step RAG relative to Agentic RAG.
- [ ] Design a filter placement that never sends unauthorized fragments to the model.
- [ ] Explain why raw-score direction cannot be reused across backends.
- [ ] Use `Document.id` and metadata to look up, revoke, and verify a chunk.

## Next

Continue to [[langchain/beginner-route/05-memory-state-and-persistence|Memory, State, and Persistence]] to distinguish retrieved knowledge, run state, and long-term memory.

## Source baseline

Official API/source baseline checked on 2026-07-20; local execution was verified on 2026-07-22.

- [LangChain Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval)
- [LangChain v1 migration guide](https://docs.langchain.com/oss/python/migrate/langchain-v1)
- [langchain-core Retriever API overview](https://reference.langchain.com/python/langchain-core/langchain_core)
- [InMemoryVectorStore source (1.4.9 pinned commit)](https://github.com/langchain-ai/langchain/blob/1c3a4186cf2ba4f28face59118ac7786de009f91/libs/core/langchain_core/vectorstores/in_memory.py)
- [VectorStore and Retriever source (1.4.9 pinned commit)](https://github.com/langchain-ai/langchain/blob/1c3a4186cf2ba4f28face59118ac7786de009f91/libs/core/langchain_core/vectorstores/base.py)
- [PyPI: langchain-core 1.4.9](https://pypi.org/project/langchain-core/1.4.9/)
- [PyPI: NumPy 2.4.6 (Python ≥3.11)](https://pypi.org/project/numpy/2.4.6/)
- [[langchain/upstream-references/langchain/semantic-search|Frozen reference page: Semantic Search (requires review; not an execution baseline)]]
- [[langchain/upstream-references/langchain/rag-agent|Frozen reference page: RAG Agent (dynamic APIs require renewed verification)]]
- [[rag/00-index|RAG principles and system route]]
