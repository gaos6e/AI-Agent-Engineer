---
title: "RAG Learning Path"
tags:
  - ai-agent-engineer
  - rag
  - learning-path
aliases:
  - Retrieval-Augmented Generation
  - RAG learning path
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
source_baseline: Original RAG/DPR/BEIR/Self-RAG/RAGAS/ARES/Lost in the Middle
  papers; W3C PROV/Web Annotation; RFC 8785; JSON Schema 2020-12; and official
  NIST AI RMF Playbook and OWASP GenAI/RAG Security resources through 2026-07-22
ai_learning_stage: 4. RAG and Knowledge Bases
ai_learning_order: 29
ai_learning_schema: 2
ai_learning_id: rag
ai_learning_domain: retrieval-and-data
ai_learning_catalog_order: 2900
ai_learning_hard_prerequisites: []
ai_learning_track_rag_order: 1200
ai_learning_track_rag_kind: core
lang: en
translation_key: RAG/00-目录.md
translation_source_hash: 56d57310b6bc354679d33592a8a953a06c91067cefc5f7f0ee5fb222ce6feac3
translation_route: zh-CN/RAG/00-目录
translation_default_route: zh-CN/RAG/00-目录
---

# RAG

## About this knowledge base

RAG (Retrieval-Augmented Generation) is a systems approach that retrieves evidence from an external knowledge source before organizing an answer with a generative model. It connects what is remembered in model parameters to material that can currently be searched, updated, and cited. It suits internal knowledge Q&A, customer explanations, research assistants, and agents that need sources.

Beginners often reduce RAG to “vector retrieval + LLM.” Engineering RAG actually contains two pipelines:

- Offline knowledge pipeline: source connection → parsing → cleaning → chunking → representation → indexing → quality checks.
- Online answer pipeline: identity and routing → hard filters → recall → reranking → context selection → generation → citation validation → monitoring.

> [!important] Three non-guarantees
> RAG does not automatically guarantee source correctness, complete retrieval, or faithful answers. Retrieving a document does not mean it supports the conclusion; a citation marker does not mean the citation is valid; putting a private document in a vector store does not mean authorization is safe. A complete derivation/hash chain establishes traceability or comparability only; by itself it cannot prove that a source is authentic, admitted, or currently accessible.

## Position in the overall curriculum

This knowledge base belongs to the “retrieval and data” domain and is the integration stop in the RAG role path. It connects the following components into an answer chain that can be accepted:

- [[document-parsing/00-index|Document Parsing]] and [[knowledge-base-construction/00-index|Knowledge Base Construction]] provide trusted, versionable knowledge.
- [[chunking-strategies/00-index|Chunking Strategies]] determines evidence granularity.
- [[embeddings/00-index|Embeddings]], [[vector-databases/00-index|Vector Databases]], and [[semantic-search/00-index|Semantic Search]] provide candidate recall.
- [[reranking/00-index|Reranking]] improves the quality of candidates near the top.
- [[prompt-engineering/00-index|Prompt Engineering]], [[context-engineering/00-index|Context Engineering]], and [[api/ai-api-reference/00-index|AI API Reference]] support constrained generation.

After this knowledge base, proceed to Tool Calling, MCP, and agent orchestration: knowledge Q&A uses RAG, while live state and side-effecting actions use controlled tools. They must not be conflated.

## Learning objectives

After completing this knowledge base, you should be able to:

- draw offline indexing and online answer pipelines and explain each layer's inputs, outputs, and responsibility;
- establish version chains for source, parser, chunk, embedding, index, retrieval, reranker, prompt, and model;
- distinguish source admission, derivation provenance, current authorization, and relevance: they need different evidence and cannot be replaced by one similarity score or SHA-256;
- distinguish routes for small talk, knowledge retrieval, live tools, high-risk refusals, and human escalation;
- apply tenant, ACL, status, and validity hard filters before relevance ranking;
- combine sparse/dense recall, fusion, reranking, and measurable fallback paths;
- perform canonical deduplication, source coverage, adjacent-passage selection, and conflict handling within a context budget;
- split an answer into checkable claims and verify citations came from this request's context and support their claims;
- recompute citations from source/span/revision through canonical, parse, chunk, index entry, and published generation;
- establish explicit schemes, crosswalks, and release manifests for incompatible native Parser, KB, and Chunking identity/coordinate/publication contracts;
- apply different strategies for no-answer, insufficient permission, evidence conflict, dependency failure, and live questions;
- evaluate retrieval, context, answers, citations, routing, security, latency, and cost separately;
- use traces and regression samples to locate the wrong layer rather than tuning only a prompt when an answer is wrong.

## Prerequisites

Complete the first seven knowledge bases in this stage and also consider:

- [[api/00-index|API]]: authentication, timeouts, retries, and error contracts.
- JSON: structured inputs, outputs, and traces.
- [[data-annotation/00-index|Data Annotation]]: qrels, answer rubrics, and hard negatives.
- [[probability-and-statistics/00-index|Probability and Statistics]]: sampling, confidence intervals, and online variation.

You do not need to train a model first. The projects in this knowledge base use only the Python 3 standard library.

## Core terms

| Term | Beginner explanation | Engineering boundary |
| --- | --- | --- |
| source | Original material plus its identity, version, and permissions. | A web-page title is not a stable source ID. |
| source admission | A source revision passed connector, owner, license, classification, and publication rules. | Provenance records how it arrived; it does not mean it was admitted or factually correct. |
| eligibility | The objects the current principal, policy, and time may search/display. | It differs from relevance and needs rechecking in caches and output. |
| chunk | An independently retrievable evidence unit. | It does not necessarily equal answer context. |
| candidate | A first-stage recalled item. | It may not enter the prompt. |
| evidence | Context selected through filtering, reranking, and budget. | It must retain source and version. |
| grounding | Claims in an answer are supported by supplied evidence. | “Sounds plausible” is not support. |
| claim | A statement whose truth can be checked separately. | One long paragraph usually contains several claims. |
| citation | Mapping from claim to source/span/revision. | `[S1]` formatting alone is insufficient. |
| abstention | Do not invent an answer when evidence is insufficient. | Reasons and next actions should be distinct. |
| trace | Records of inputs, versions, candidates, decisions, and failures at each stage. | External results must not disclose filtered material. |
| manifest | A publication digest for a group of objects, versions, and hashes. | A digest may not carry a complete payload independently rebuildable by a consumer. |
| artifact / bundle | Complete protected artifact that can be serialized, versioned, and consumer-validated. | A self-hash proves only self-consistency, not producer or source authenticity. |
| attestation | A verifiable statement by an actor over typed payload. | `attestation.mode: none` must be honestly treated as “no proof.” |

## Recommended learning order

| Order | Course | Learning outcome |
| --- | --- | --- |
| 1 | [[rag/01-system-boundaries-and-the-complete-pipeline\|System Boundaries and the Complete Pipeline]] | Two pipelines, version contracts, and a minimal baseline. |
| 2 | [[rag/02-query-understanding-routing-and-rewriting\|Query Understanding, Routing, and Rewriting]] | Routing table, rewrite boundaries, and trusted filters. |
| 3 | [[rag/03-retrieval-reranking-and-fallback-orchestration\|Retrieval, Reranking, and Fallback Orchestration]] | Safe candidate chains, fusion, timeouts, and fallback. |
| 4 | [[rag/04-context-selection-and-assembly\|Context Selection and Assembly]] | Budget, deduplication, order, conflict, and untrusted-data wrapping. |
| 5 | [[rag/05-citations-generation-and-abstention\|Citations, Generation, and Abstention]] | Claim-level citations, validation, and abstention taxonomy. |
| 6 | [[rag/06-failure-taxonomy-and-system-debugging\|Failure Taxonomy and System Debugging]] | Reproducible diagnostic flow from data to answer. |
| 7 | [[rag/07-end-to-end-evaluation-and-monitoring\|End-to-End Evaluation and Monitoring]] | Layered metrics, test suite, release gates, and online signals. |
| 8 | [[rag/08-project-offline-cited-qa\|Project: Offline Cited Q&A]] | Public/audit dual contracts, bounded fixture, evidence pipeline, layered release report, fault simulation, and 73 tests. |
| 9 | [[rag/09-project-offline-provenance-from-source-to-citation\|Project: Offline Source-to-Citation Provenance]] | Exact source spans, event identity, index generation, revocation/deletion, and 72 lifecycle/resource-boundary/tamper tests. |
| 10 | [[rag/10-project-cross-layer-provenance-adaptation-and-atomic-publication\|Project: Cross-Layer Provenance Adaptation and Atomic Publication]] | Fresh Parser/KB/Chunking calls, ID schemes, coordinate crosswalk, atomic release, and 37 path/sidecar/tamper/lifecycle regressions. |
| 11 | [[rag/11-project-external-provenance-artifact-v2\|Project: External Provenance Artifact v2]] | Complete protected bundle, strict JSON, out-of-band trusted binding, consumer staged/local publish, and route/coverage/live-deny red-team regressions. |

## Hands-on entry points

| File | Use |
| --- | --- |
| [[rag/examples/rag-fixture.json\|rag-fixture.json]] | 10 documents, 8 query classes, trusted authorization revisions, risk slices, and offline oracles. |
| [[rag/examples/offline_cited_qa.py\|offline_cited_qa.py]] | Hard filters, public-response/protected-audit separation, claim rendering, layered evaluation report, and CLI. |
| [[rag/examples/test_offline_cited_qa.py\|test_offline_cited_qa.py]] | 73 schema/file/depth/set resource-boundary, type-robustness, noninterference, security, audit-binding, failure, grounding, evaluation, and CLI tests. |
| [[rag/examples/provenance/provenance-fixture.json\|provenance-fixture.json]] | UTF-8 Markdown source events, two-tenant ACLs, malicious strings, runtime queries, and independent oracles. |
| [[rag/examples/provenance/offline_provenance_pipeline.py\|offline_provenance_pipeline.py]] | Source normalization, parse/chunk/index identity, generation publication, retrieval, and citation recomputation. |
| [[rag/examples/provenance/provenance-artifact.schema.json\|provenance-artifact.schema.json]] | JSON Schema 2020-12 structural contract for evaluation artifact v2; self-hash is not authenticity. |
| [[rag/examples/provenance/test_offline_provenance_pipeline.py\|test_offline_provenance_pipeline.py]] | 72 tests for input limits, event identity, spans, lifecycle, integrity, external type/route/failure/artifact tampering, non-disclosure, reports, and CLI. |
| [[rag/examples/integration/cross-layer-fixture.json\|cross-layer-fixture.json]] | Adapter fixture for two tenants, byte-identical sources, ACLs, and independent runtime/oracle. |
| [[rag/examples/integration/cross_layer_adapter.py\|cross_layer_adapter.py]] | Real three-module import, protected crosswalk, fresh rebuild, release, citation, and evaluation CLI. |
| [[rag/examples/integration/cross-layer-eval-artifact.schema.json\|cross-layer-eval-artifact.schema.json]] | Structural contract for this lesson's local evaluation artifact; it is not the current LLMOps example's wire input and does not verify authenticity. |
| [[rag/examples/integration/test_cross_layer_adapter.py\|test_cross_layer_adapter.py]] | 37 strict-contract, path/symlink, identity-conflict, authorization, sidecar replay/checkpoint, tamper, lifecycle, failure, and CLI red-team tests. |
| [[rag/examples/provenance/external_provenance_v2.py\|external_provenance_v2.py]] | v2 strict importer, trusted policy, fresh semantic rebuild, consumer publication state machine, and query dual projections. |
| [[rag/examples/provenance/external-provenance-bundle-v2.schema.json\|external-provenance-bundle-v2.schema.json]] | JSON Schema 2020-12 structural contract for a protected bundle; self-hash, trusted binding, semantic validation, and live gate are handled separately. |
| [[rag/examples/provenance/test_external_provenance_v2.py\|test_external_provenance_v2.py]] | 42 trust/identity/route/path/order/coordinate/coverage/host-auth/trace/publication/audit-delivery/non-leakage regressions across a JSON boundary. |

From the project root (which contains `docs-EN/` and `.website/`), run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Do not create __pycache__ in the course directory while running the project.
$env:PYTHONIOENCODING = 'utf-8'  # Force UTF-8 for CLI stdout/stderr.
$script = '.\docs-EN\rag\examples\offline_cited_qa.py'  # Store the Lesson 8 offline-Q&A script path.
$fixture = '.\docs-EN\rag\examples\rag-fixture.json'  # Store the strict teaching fixture path shared by all commands.

python -B -W error $script --fixture $fixture demo  # Run the built-in demonstration for the main cited-answer path.
python -B -W error $script --fixture $fixture ask --query-id Q-conflict  # View the public response for conflicting evidence without audit candidates.
python -B -W error $script --fixture $fixture evaluate  # Produce offline quality and security evaluation on pinned oracles.
python -B -W error $script --fixture $fixture inspect --query-id Q-refund --operator-view  # Request protected audit view only in local teaching.
```

`ask/demo` output only public responses; only `inspect` exposes the protected teaching trace containing filter statistics and candidates. `--operator-view` is explicit confirmation, not a real authorization mechanism. The project intentionally has no embeddings, ANN, LLM, or tool execution. Its malicious-document sample can prove only that control fields are not read from document text; it cannot show that a real model resists indirect prompt injection.

Continue with Lesson 9's source-to-citation project:

```powershell
$provenance = '.\docs-EN\rag\examples\provenance\offline_provenance_pipeline.py'  # Store the Lesson 9 source-to-citation pipeline script path.
$provenanceFixture = '.\docs-EN\rag\examples\provenance\provenance-fixture.json'  # Store this project's independent strict fixture path.

python -B -W error $provenance --fixture $provenanceFixture manifest --operator-view  # View protected provenance manifest with generation.
python -B -W error $provenance --fixture $provenanceFixture ask --query-id Q-refund  # Generate an answer with public citation projection only.
python -B -W error $provenance --fixture $provenanceFixture evaluate  # Rebuild provenance chain and calculate the pinned evaluation-suite result.
```

This project claims recomputable spans only for LF + NFC normalized characters in UTF-8 Markdown. Public citations do not reveal global generation or filter counts; protected audit alone binds selected entries to generation, authorization, and snapshot/tombstone state. Lesson 8 fixes enum `privileged_audit`, while Lesson 9 fixes `protected_audit`; they belong to different schemas but both describe protected audit conceptually.

Finally, run Lesson 10's real-module adapter:

```powershell
$adapter = '.\docs-EN\rag\examples\integration\cross_layer_adapter.py'  # Store the Lesson 10 cross-module adapter's local script path.

python -B -W error $adapter manifest --operator-view  # Explicitly request protected crosswalk/manifest inspection.
python -B -W error $adapter ask --query-id q-tenant-a-refund  # Run tenant-a's public answer path.
python -B -W error $adapter evaluate --operator-view  # Run trusted local cross-layer pre-publication replay.
python -B -W error $adapter evaluate --operator-view --failure retrieval_unavailable  # Simulate unavailable retrieval and verify fail-closed publication/answer behavior.
```

It imports the existing Parser, SQLite Knowledge Store, and Chunking implementation but does not force their three coordinate systems into one. Public citations retain parser line locator, element lexical span, and exact quote, and label unverified canonical-character mapping `unavailable`. The release also explicitly declares that external chunks have not yet been imported into Lesson 9's provenance engine.

The 37 adapter tests cover symlink/path behavior, sidecar replay/checkpoint, and publish-before-pointer fresh validation. A keyless artifact self-hash proves only internal consistency and must be accompanied by a trusted `evaluate()` rerun of the oracle/pipeline; it is not a signature or independent authenticity proof.

Lesson 11 serializes Lesson 10's complete raw/parser/crosswalk/chunk/entry payload as `external-provenance-bundle-v2`. A producer's `published` state does not automatically authorize a consumer: canonical bundle value must first match an out-of-band trusted digest/generation/pipeline/auth policy, undergo fresh semantic rebuild in staged state, and then pass the consumer's current auth, tombstone, and deny gate before local publication. A query body carries only question payload; tenant/groups/auth arrive through snapshot-bound context issued from host-owned live state. Raw source locators go only to a host-owned protected audit sink. This path remains `document-revision-bridge` and does not misrepresent transportability as canonical spans, source authenticity, or verified signatures.

## Mastery checklist

- [ ] Distinguish source, chunk, candidate, selected context, claim, and citation.
- [ ] Complete every hard authorization filter before relevance scoring; fallbacks cannot bypass it either.
- [ ] Trace every answer to source/chunk/revision, stage rank, and version.
- [ ] Explain at least three reasons why high candidate recall can still yield a wrong answer.
- [ ] Define different states for no-answer, conflict, live status, insufficient permission, and dependency failure.
- [ ] Give every checkable claim supporting evidence from this request's context.
- [ ] Reconstruct original text from a citation's source locator and half-open span, and explain how parser/chunker/index/auth revisions invalidate old derived artifacts.
- [ ] Explain why byte-identical cross-tenant documents may share native content IDs but need different authorization-namespaced IDs, and interpret the crosswalk's scheme and loss profile.
- [ ] Distinguish JSON Schema, self-hash, out-of-band trusted binding, semantic rebuild, and live authorization as five kinds of evidence, and explain why producer-published does not equal consumer-published.
- [ ] Retain old versions after failed content updates, but immediately block after ACL tightening, authorization-revision mismatch, and deletion; stale snapshots cannot resurrect tombstoned objects.
- [ ] Use distinct schemas for public response and protected audit trace; unauthorized-corpus changes do not change public response.
- [ ] Render final answers from validated status/claims only; no facts outside claims may appear.
- [ ] Cover common, long-tail, freshness, authorization, conflict, attack, and no-answer slices in offline suites.
- [ ] Cover quality, security, p95/p99, cost, and fallback together in release gates.
- [ ] Run the projects/tests and explain why they do not validate real-model quality.

## Relationship to other knowledge bases

| Knowledge base | Relationship |
| --- | --- |
| [[knowledge-base-construction/00-index\|Knowledge Base Construction]] | Manage sources, incremental synchronization, deletion propagation, and versions. |
| [[semantic-search/00-index\|Semantic Search]] | Provides high-recall, authorized first-stage candidates. |
| [[reranking/00-index\|Reranking]] | Improves leading evidence quality within the candidate window. |
| [[context-engineering/00-index\|Context Engineering]] | Manages total window, evidence layout, and state. |
| [[api/ai-api-reference/00-index\|AI API Reference]] | Provides generation calls, schemas, timeouts, and observability. |
| [[tool-calling-function-calling/00-index\|Tool Calling (including Function Calling)]] | Handles live queries and side-effecting actions; routing still requires allowlists, object-level authorization, and confirmation. |
| MCP | Provides cross-service resource/tool protocols; RAG citations or resource URIs cannot replace this system's identity, ACL, and source validation. |
| [[agent-core/00-index\|Agent Core]] | Decides when to retrieve, use tools, and stop. |
| Evaluation systems | Connect component metrics to real task goals. |
| [[ai-safety/00-index\|AI Safety]] | Covers indirect prompt injection, data poisoning, disclosure, and authorization violations. |

## Main references

- Lewis et al. (2020), [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)
- Karpukhin et al. (2020), [Dense Passage Retrieval for Open-Domain Question Answering](https://arxiv.org/abs/2004.04906)
- Thakur et al. (2021), [BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models](https://arxiv.org/abs/2104.08663)
- Liu et al. (2023), [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172)
- Asai et al. (2023), [Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection](https://arxiv.org/abs/2310.11511)
- Es et al. (2023), [RAGAS: Automated Evaluation of Retrieval Augmented Generation](https://arxiv.org/abs/2309.15217)
- Saad-Falcon et al. (2023), [ARES: An Automated Evaluation Framework for RAG Systems](https://arxiv.org/abs/2311.09476)
- [OWASP GenAI Security Project: LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
- [OWASP GenAI Security Project: LLM08:2025 Vector and Embedding Weaknesses](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/)
- [OWASP RAG Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html)
- [NIST AI RMF Playbook](https://airc.nist.gov/airmf-resources/playbook/): organizes continual risk management as Govern, Map, Measure, and Manage. AI RMF 1.0 is being revised; lock the cited version.
- [W3C PROV Overview](https://www.w3.org/TR/prov-overview/)
- [W3C PROV-O](https://www.w3.org/TR/prov-o/)
- [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/)
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)

Sources accessed: 2026-07-22. Paper conclusions apply to their specific datasets and experimental settings; service APIs, model windows, product capabilities, prices, and OWASP/NIST pages can change. Pin versions and validate again with local corpora during implementation.
