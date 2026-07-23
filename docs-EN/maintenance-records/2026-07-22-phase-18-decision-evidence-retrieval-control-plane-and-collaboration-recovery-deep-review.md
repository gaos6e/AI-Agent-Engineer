---
title: "2026-07-22 Phase 18 Deep Review Record: Decision Evidence, Retrieval
  Control Plane, and Collaboration Recovery"
aliases:
  - Phase 18 optimization record
tags:
  - maintenance
  - model-selection
  - retrieval
  - agent-runtime
  - governance
  - learning-path
source_checked: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: 维护记录/2026-07-22-第十八阶段决策证据检索控制面与协作恢复深审记录.md
translation_source_hash: f57ad1449452db55e534905acda584342fcbfd544aef27141cc87556ced9624e
translation_route: zh-CN/维护记录/2026-07-22-第十八阶段决策证据检索控制面与协作恢复深审记录
translation_default_route: zh-CN/维护记录/2026-07-22-第十八阶段决策证据检索控制面与协作恢复深审记录
---

# 2026-07-22 Phase 18 Deep Review Record: Decision Evidence, Retrieval Control Plane, and Collaboration Recovery

## Phase conclusion

This phase deeply reviewed whether a learner can connect candidate models, retrieval data, a collaborative runtime, and a release decision into reviewable engineering evidence. It covered AI Fundamentals, [[modern-llm-capabilities-and-model-selection/00-index|Modern LLM Capabilities and Model Selection]], the six retrieval-fundamentals courses, [[ai-safety/00-index|AI Safety]], AI Governance, Privacy Computing, Workflow Automation, Multi-Agent Collaboration, and Environment Agents.

It does not present “the API supports it,” one successful demonstration, the same idempotency key, or the existence of a digest as proof of capability, authorization, a transaction, or production reliability. All new explanations, diagrams, and code are labeled original. Third-party material is cited only through links and factual boundaries; no complete reproduction with an unknown license was added.

> [!important] What this phase does not prove
>
> Offline fixtures, single-process JSON files, and a site build prove only the current internal consistency of the teaching contracts and public content. They do not prove production validation of real Provider behavior, model quality, IdP or object-level authorization, policy services, cross-process leases/CAS, database isolation, an actual deletion execution chain, vendor contracts, or regional legal obligations.

## Multi-Agent division of work and primary-Agent review

The primary Agent first fixed cross-course terminology for request and returned-model identity, evidence digest, ACL-before-score, state and lease version, and human reconciliation. It then assigned non-overlapping areas:

1. Safety, governance, and privacy: dynamic MCP/Tool/Agent components, release evidence, RAG deletion, and authorization propagation.
2. Workflows, multi-Agent systems, and environment Agents: message idempotency, conflict freezing, recovery/leases/fencing, and browser actionability.
3. Chunking, vectors, Embedding, vector databases, semantic search, and reranking: input spaces, candidate windows, metrics, deletion/update, and multi-instance stale reads.
4. AI Fundamentals: entry terminology, identity and authorization, offline-to-online evidence handoff, the capstone project, and source status.

The primary Agent then reviewed every shared-worktree change, checked date and terminology consistency, repaired a broken Model Selection directory link, and reran normal and <code>-O</code> regressions for the related code after all specialist work ended. No Agent staged, committed, pushed, or rolled back pre-existing user workspace state.

## Learning entry points and model selection: define a replayable selection object first

The recommended-order table for Modern LLM Capabilities and Model Selection previously placed the alias separators of eight wikilinks inside unescaped Markdown-table column separators, creating a broken-link and malformed-rendering risk. All links are now parseable. The index adds a Mermaid evidence flow of task → gate → multiple trials → Pareto frontier → release gate, and makes clear that an aggregate score cannot compensate for <code>FAIL</code> or <code>BLOCKED</code>.

The course also adds a commonly missed identity boundary in the model lifecycle. <code>latest</code>, preview aliases, and fixed versions have different change semantics; even with fixed weights, routing, safety layers, or service infrastructure can change observable behavior. Selection and each trial must therefore record the requested model identifier, the actual model/version returned by the interface when available, endpoint/region, adapter version, date, and sampling configuration. A new evaluation version is required when version resolution or the control plane changes. The Model Selection project now leads directly into the Offline-to-Online Evidence Handoff and Regression Loop lesson in Evaluation Systems.

All 13 AI Fundamentals pages completed page-by-page metadata and source-status checks. Learner completion status was retained rather than confused with content status. The course adds a minimal chain for “a model is not an authorized principal”: identity, delegation, object permission, and expiry facts. It explicitly hands offline evaluation to a trial run. Its capstone adds a no-side-effect trust-boundary Mermaid diagram and raises acceptance to at least 10 independent tests, including an error contract for rejection paths.

## Retrieval foundations: move from mathematical demonstrations to identity, version, and complete-window contracts

The retrieval courses no longer treat a top-k result alone as evidence of safety or quality:

- Chunking states that default recursive character splitting is better aligned with space-tokenized languages. Corpora such as CJK and Thai require appropriate separators and fixture-based acceptance; a token-length function cannot replace boundary design.
- Embedding states that query/document roles, task instructions, and automatic truncation for different models cannot be copied across models. A migration from an old vector space requires full re-encoding, dual-space isolation, and threshold revalidation. The teaching evaluator rejects duplicate ranked IDs and invalid relevance grades so that nDCG cannot be fabricated above 1.
- The Vector Database project replaces “upsert solves concurrency” with explicit <code>expected_source_revision</code> CAS, same-revision/different-content conflict handling, a delete-before-create fence, resurrection tokens, tombstones, and fail-closed stale reads. It also states that the current tombstone is not a permanent audit ledger, that reusing source identity can cause ABA, and that a JSON file still has TOCTOU between check and replacement; it does not claim snapshot isolation.
- The Semantic Search security audit now covers the full candidate/rank window of every retrieval channel, rather than only the displayed top-k. An unauthorized candidate can contaminate fusion, cache, or trace even if it is ultimately truncated.
- The Reranking course adds the upper-bound boundary for candidate recall: some evaluators inject positive items, which is useful for diagnosing the ranking ceiling but is not an end-to-end release result. A release must freeze the actual first-stage candidate IDs and window.

These courses now use consistent <code>content_origin</code>, <code>content_status</code>, review-date, test-count, and “teaching implementation is not a production system” boundaries in their indexes, projects, and body text.

## Safety, governance, collaboration, and recovery: stop conflicts and make evidence discoverable

The Safety course now requires dynamically discovered MCP/Tool/Agent components to be stored as reviewable snapshots. Identity and release channel, protocol and transport, schema digest, execution identity/scope, Roots/data scope, and outbound destinations become change triggers, while secrets such as bearer tokens must never enter a snapshot. Snapshots, regression results, and approval conditions are passed to release through <code>release_id</code> and a full gate digest. The digest supports change detection only; it is not proof of signature, authorization, or source authenticity.

The Governance course adds a minimum handoff table for offline evaluation, release gate, operational evidence, and human-triage regressions. The Privacy course adds boundaries for ACL, revocation, deletion propagation, and Tool Calling reauthorization across RAG/Agent chunks, Embedding, index generations, caches, citations, and memory references. Neither course accepts “a source hash,” “from the internal knowledge base,” or “one vector was deleted” as proof of current object-level authorization or completed deletion.

The Multi-Agent offline simulator fixes a genuinely reproducible defect. The old implementation silently treated different payloads under the same <code>(task_id, idempotency_key)</code> as duplicates and allowed pending tasks to accept external results directly. Results are now accepted only in <code>running</code>; a canonical JSON digest separates safe replay from conflict. The same key with a different digest records both digests, escalates to <code>needs_review</code>, and blocks downstream tasks that have not started. The course clearly labels <code>needs_review</code> as an internal coordination state of this repository, not an A2A standard state.

Workflow Automation and Environment Agents now consistently use <code>owner_worker</code>, <code>lease_version</code>, <code>expires_at</code>, <code>state_version</code>, CAS, and external fencing. These distinguish runtime ownership, state commit, and external side effects. The browser course adds the waiting boundary for Playwright dynamic locators and <code>locator.all()</code>, and stresses that fresh DOM state does not mean authorization is still valid.

## Key sources

Dynamic conclusions prioritize current primary material, with dates recorded on the relevant pages through <code>source_checked</code>:

- [Gemini API models](https://ai.google.dev/gemini-api/docs/models) and [Claude model IDs and versions](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions): boundaries for model versions, aliases, and service behavior.
- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/), [NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1), and [NIST's concept paper on identity and authority for software agents](https://www.nist.gov/news-events/news/2026/02/new-concept-paper-identity-and-authority-software-agents): risk, identity, and authorization boundaries.
- [A2A specification](https://a2a-protocol.org/latest/specification/), [Temporal workflow execution](https://docs.temporal.io/workflow-execution), and [Playwright locators](https://playwright.dev/docs/locators): interoperability, durable workflows, and browser-action boundaries.
- [Qdrant Points](https://qdrant.tech/documentation/manage-data/points/), [Qdrant filtering](https://qdrant.tech/documentation/search/filtering/), and [Sentence Transformers Cross-Encoder training](https://www.sbert.net/docs/cross_encoder/training_overview.html): boundaries for vector data, filtering, and reranking evaluation.
- [OECD's updated AI-system definition](https://oecd.ai/en/ai-publications/explanatory-memorandum-on-the-updated-oecd-definition-of-an-ai-system) and the [Stanford HAI 2026 AI Index](https://hai.stanford.edu/ai-index/2026-ai-index-report): limited use for foundational concepts and annual trends.

## Verification evidence

| Check | Phase result |
| --- | --- |
| Model-selection scorecard | 20 tests; normal and <code>-O</code> passed under <code>-B -W error</code>. |
| AI Safety / Governance / Privacy | 80 / 69 / 76 tests; normal and <code>-O</code> passed under <code>-B -W error</code>. |
| Workflow / Multi-Agent / Environment Agent | 71 / 61 / 103 tests; normal and <code>-O</code> passed under <code>-B -W error</code>. |
| Chunking / Vector Fundamentals / Embedding | 32 / 9 / 31 tests; normal and <code>-O</code> passed under <code>-B -W error</code>. |
| Vector Database / Semantic Search / Reranking | 41 / 34 / 29 tests; normal and <code>-O</code> passed under <code>-B -W error</code>. |
| AI Fundamentals internal links | 112 wikilinks; specialist check found 0 missing. |
| Final website unit tests | <code>.website npm test</code>: 47/47 passed. |
| Final public build | 911 source Markdown pages, 571 full pages, 340 fail-closed stubs, and 229 assets; 914 staged Markdown pages, 2,456 HTML pages, and 2,809 public files. Broken local links, sensitive leaks, table-wikilink leaks, interactive checkboxes, and KaTeX errors were all 0. |
| Text and change hygiene | Relevant scope and global <code>git diff --check</code> passed. Two Chunking <code>.pyc</code> files created during verification were removed; a scope recheck found 0. No files were staged. |

The website tests and build above were rerun after this phase record and the overall-route entry point were updated. A specialist Agent's earlier build is not treated as final post-merge gate evidence.

## Follow-up queue

1. Use real, controlled identity, policy, vector-database, and adapter components for end-to-end ACL, deletion propagation, lease/fencing, receipt reconciliation, and multi-worker load tests. Do not elevate the current single-process fixtures into a production guarantee.
2. Add isolated Provider smoke tests with a cost cap, redacted traces, and change detection; rerun capability contracts when model catalogs, aliases, or regions change.
3. Inspect this phase's new Mermaid diagrams, tables, callouts, and mobile layout in Obsidian desktop. A Quartz build is not verification of Obsidian Reading View.
4. Continue course-by-course review of pages with early <code>source_checked</code> dates. Prioritize dynamic chapters tied to live services, law, frameworks, or runtime behavior; do not replace review with bulk date updates.

This record covers only Phase 18. It does not mean the long-running <code>/goal</code> is complete.
