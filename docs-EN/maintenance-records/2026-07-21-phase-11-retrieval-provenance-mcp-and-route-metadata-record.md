---
title: "2026-07-21 Phase 11 Retrieval, Provenance, MCP, and Route Metadata Record"
aliases:
  - Phase 11 optimization record
tags:
  - maintenance
  - retrieval
  - langchain
  - mcp
  - provenance
  - licensing
  - learning-roadmap
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: 维护记录/2026-07-21-第十一阶段检索来源MCP与路线元数据记录.md
translation_source_hash: dde11712ece4228d8debc6d9cc0c30ba8887c2ecd4ea74f98e6a23f3e30bac7e
translation_route: zh-CN/维护记录/2026-07-21-第十一阶段检索来源MCP与路线元数据记录
translation_default_route: zh-CN/维护记录/2026-07-21-第十一阶段检索来源MCP与路线元数据记录
---

# 2026-07-21 Phase 11 Retrieval, Provenance, MCP, and Route Metadata Record

This phase reviewed whether RAG components, AI Safety, and AI Governance are course-level hard prerequisites or role-track recommendations; independently re-reviewed frozen LangChain Semantic Search for source/license/39 Python fences/current API; added original pinned, offline Retrieval Layer B; traced all 18 historic MCP reference pages through repository-path/license change; and confirmed metadata relabeling cannot bypass fail-closed publication.

Seven courses enter v2 metadata: Chunking, Embedding, Vector Database, Semantic Search, Reranking, AI Safety, and AI Governance. The five RAG components are core in RAG order 700–1100 with no universal hard prerequisite; AI Safety is core in all four tracks and Governance is Agent-Platform core. This records actual page-level evidence, not a claim that recommendation order is a hard DAG.

Semantic Search stays frozen after strict review. Strong source trace is the listed LangChain blobs and MIT blob, but 39 parseable fences are not one runnable program: flattened embedding/vector-store tabs overwrite mutually exclusive variables; PDF/dependencies/credentials are absent; model dimension assumptions conflict; fake embeddings lack semantic capability; raw/relevance score semantics differ by backend; and copied NIKE 10-K output is not covered by repository MIT. The page remains a public stub despite facts/terminology corrections.

The original Retrieval Layer B separates offline ingestion from online query, applies trusted identity/ACL/filter before candidate leaves the data boundary, and gives reranker authorized candidates only. It distinguishes raw similarity/distance, calibrated relevance, threshold retrieval, and document-only retrievers; top-k without an abstention gate is not a no-answer proof. The pinned <code>langchain-core==1.4.9</code>/<code>numpy==2.4.6</code> example has transparent 3D embeddings, full metadata/filter, stable IDs, raw scores, Retriever, JSON CLI, and 17 positive/negative tests.

For MCP, content/license audit identifies two pre-switch MIT candidates, two post-switch CC BY 4.0 candidates, and 14 mixed-history pages that remain stubs. Corrections cover Elicitation form/URL and credential prohibition; Roots as coordination rather than sandbox/ACL; host-specific confirmation UI; vendor-context Custom Connectors; optional Streamable HTTP sessions; actual composite Skills names; separate session-hijacking/prompt-injection chains; and Example Clients as historical fixed snapshot after upstream removal.

Verification: Retrieval 17/17 in four modes; 65 base Python files 2,491/2,491 in four modes, plus locked LangGraph/CrewAI/Retrieval environments; 45/45 website tests and 39/39 route-policy tests; full build produced 896 staged Markdown, 2,394 HTML, 2,735 public files with every publication gate 0. Five optional files were not falsely treated as passed. Dynamic facts are supported by [LangChain Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval), pinned [InMemoryVectorStore](https://github.com/langchain-ai/langchain/blob/1c3a4186cf2ba4f28face59118ac7786de009f91/libs/core/langchain_core/vectorstores/in_memory.py), [MCP 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25), [Elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation), and [Security Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices).

Next: page-bound source/attribution HTML gates before restoring MCP candidates; rebuild Semantic Search as original layered route; migrate remaining legacy courses without inferring hard dependencies; share v2 tracks across Homepage/CourseNavigator/Dataview; add credential-gated real retrieval tests; and inspect Obsidian rendering.
