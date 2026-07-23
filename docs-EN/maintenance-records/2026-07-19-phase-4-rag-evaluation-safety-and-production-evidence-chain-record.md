---
title: "2026-07-19 Phase 4 RAG, Evaluation, Safety, and Production Evidence
  Chain Record"
aliases:
  - AI Agent Engineer Phase 4 optimization record
tags:
  - AI-Agent-Engineer
  - maintenance
  - rag
  - evaluation
  - security
  - production
content_origin: original
content_status: validated
source_checked: 2026-07-19
lang: en
translation_key: 维护记录/2026-07-19-第四阶段RAG评测安全生产证据链记录.md
translation_source_hash: a9072244b084e47588c8c837a219104ac46dfeb8e1e12f9094a408c2f30cab61
translation_route: zh-CN/维护记录/2026-07-19-第四阶段RAG评测安全生产证据链记录
translation_default_route: zh-CN/维护记录/2026-07-19-第四阶段RAG评测安全生产证据链记录
---

# 2026-07-19 Phase 4 RAG, Evaluation, Safety, and Production Evidence Chain Record

This phase turns the Phase 3 queue's “vertical review of RAG, evaluation, safety, and productionization” into an executable, fault-injectable, auditable evidence chain. The primary Agent standardized public/internal-data boundaries, terminology, versions, cross-links, and final verification. Specialist Agents separately reviewed RAG, LLMOps, Reranking, source links, document consistency, and code-bypass risks, with isolated scopes; the primary Agent reviewed and merged semantics.

> [!important] Conclusion boundary
>
> This phase deeply reviews offline teaching projects and high-priority main-path pages. It does not mean historical RAG, evaluation, safety, or production material is all page-by-page verified. Deterministic fixtures prove that local contracts can fail closed; they do not prove real vector retrieval, real LLMs, production identity, online telemetry, signed artifacts, or physical deletion.

## 1. RAG: from “has citations” to layer-by-layer recomputable evidence

- The offline citable-Q&A project now returns only stable status, answers rendered from verified claims, post-authorization citations, and a teaching <code>trace_id</code>. Candidates, filtering reasons, stage scores, internal versions, and failure details enter only <code>privileged_audit</code>.
- <code>inspect --operator-view</code> prevents mistaken disclosure of an internal teaching envelope; it does not authenticate an operator. Public access uses explicit <code>public</code> group rather than an empty group or magic ACL bypass.
- Fixture schema 2.0 includes 10 versioned documents, 8 query types, authorized revision, risk slices, critical cases, a private canary, and untrusted documents with pseudo-instructions. Validity uses half-open <code>[effective_from, effective_to)</code>.
- Runtime queries are whitelist-projected and separated from offline oracles such as <code>expected_*</code>, forbidden IDs, and private canary. The runtime validator does not read the oracle to decide an answer.
- Retrieval, reranking, context selection, claims, citations, degraded/fallback state, public response, and teaching trace are recomputed from trusted inputs and stage results. Every citation for every claim must support that claim verbatim; duplicate citations and “one valid citation hides another invalid citation” are rejected.
- Evaluation output is fixed as <code>rag-evaluation-report-v1</code>, reporting case/slice/critical/status accuracy, retrieval/context/citation fact recall, and non-disclosure violations. Fixture/evidence use complete SHA-256. Fact-level counting and strict audit semantics are bound by <code>offline-rag-harness-v3</code>; normal run is <code>PASS</code>, fault injection is <code>BLOCK</code>.
- The main path adds an original layered-evidence Mermaid plus text alternative: ingestion, retrieval, context, generation, and system must not be collapsed into one “accuracy.”

## 2. LLMOps: bind offline score, release decision, and online window

- The Offline Release Gate evaluation artifact binds subject release, suite, dataset, rubric, grader, harness version, and complete SHA-256. Contract mismatch returns <code>INCOMPARABLE</code>, not a false improvement/regression.
- JSON input rejects duplicate keys; policy fields such as ratios, drop rate, safety ceiling, latency, and cost have explicit type/numeric limits.
- Online observation uses strict UTC RFC 3339 window; assignment/population revision; candidate/control arms; coverage, sample count, label age, quality, safety, latency, and cost; and binds candidate gate fingerprint plus control release. A candidate records <code>gate_decided_at</code>/<code>promoted_at</code>, with <code>promoted_at &lt;= window_start &lt; window_end &lt;= decision_as_of</code>.
- Online judgment compares simultaneous controls in the same window, not historical offline baseline. <code>audit --release-id</code> requires observation; bulk audit requires every promoted candidate to have it but does not require online data from an offline-blocked candidate.
- Release IDs are globally unique. Floating refs such as <code>latest</code>, <code>HEAD</code>, branch/ref/remote forms fail closed. Time accepts only <code>Z</code> or <code>+00:00</code>; <code>-00:00</code>, no timezone, and non-UTC offsets are rejected.
- Automated <code>FALLBACK</code> cannot be triggered by an observation boolean. Online evidence must match the candidate gate's bound fallback release ID, manifest SHA-256, and gate-evidence SHA-256 field by field. Missing evidence requires human review; nonempty mismatched evidence is rejected. External fallback artifacts are neither loaded nor signature-verified and remain Layer B.
- Binding unconditionally rejects nonempty mismatched fallback evidence. The manifest rejects self, known cycle, known blocked, or unpublished targets for automatic fallback. Policy moved to <code>local-llmops-policy-v6</code>, observation schema to v3, and all observations were rebound to candidate fingerprint. The short decision fingerprint is local correlation only, not a signature, provenance proof, or approval record.

## 3. Reranking and monitoring: expose hidden input and honest limits

- The Reranking fixture moves to schema 2 and adds <code>authorization_revision</code>. Its normalized SHA-256 covers query, tenant, groups, authorization version, as-of, candidate body/ACL/state/validity/source revision/rank/score, settings, qrels, and must-not-return. Evidence SHA-256 separately binds runtime overrides, faults, model version, and decision.
- Reranking output explicitly uses <code>visibility=protected_audit</code>. This label is neither public response nor real authorization; authorization/validity still precede scoring, with half-open end-time semantics.
- The Offline Monitoring Audit JSON loader rejects duplicate keys and corrects the teaching RED error-rate formula. Its Layer A verifies only local thresholds and incident classification; it does not bind full SLO population, exclusion rules, compliance window, data-source version, or change approval.

## 4. Cross-course consistency of facts, sources, and links

- Corrected MCP Roots: they coordinate suggested filesystem focus ranges from client to server; they are not authorization, ACL, sandbox, or least-privilege boundary. Client and route pages use the same wording.
- The frozen MCP reference layer received only narrow factual correction; later page-level <code>curated</code>/<code>third-party</code> and license decisions remain required.
- Knowledge Base examples are stated to have only a flat allow-list, not hierarchical permission, explicit deny, ABAC, or permission-source propagation. <code>archived</code>/tombstone is not physical deletion, retention compliance, or proof that old snapshots cannot revive.
- RAG troubleshooting uses protected <code>inspect --operator-view</code>, not public <code>ask</code> to imply internal-trace access. Future Provider sunset dates remain “officially planned at time of check” and require rechecking before implementation.
- The overall route's nonexistent path was repaired. A specialist link audit found 0 missing/ambiguous wikilinks and 0 bad heading anchors for this phase's core pages.
- Deep-reviewed pages fill <code>content_origin</code>/<code>content_status</code>; rerunning only local code uses <code>execution_verified: 2026-07-19</code> without mechanically refreshing external <code>source_checked</code>.

## Verification actually performed

| Check | Result | Evidence boundary |
| --- | --- | --- |
| 11 vertical project test suites | 1,191/1,191 passed | 397 in each of normal, <code>python -O</code>, and warnings-as-errors: Document Parsing 23; Knowledge Base 29; Chunking 29; Embedding 30; Vector Database 28; Semantic Search 32; Reranking 29; RAG 68; Evaluation 36; LLMOps 60; Monitoring 33. |
| 8 Python syntax checks | Passed | Built-in <code>compile()</code> after UTF-8 read; no bytecode. |
| Specialist red-team review | Passed | Rechecked citation/fact recall/trace-stage/public response/release fingerprint/time window/floating ref/duplicate ID/bulk audit/duplicate JSON key, and fallback misbinding/self-reference/blocked-unpromoted/cycle bypass. No residual high/medium finding. |
| CLI evidence recomputation | Passed | RAG normal <code>PASS</code>/fault <code>BLOCK</code>; protected Reranking envelope; LLMOps v6 promote/healthy audit 0 and cross-bind/no-window 2; Monitoring stable 0 and incident 1. |
| Document/local-link review | Passed | Consistent test counts, public/audit boundary, date fields, and terminology; missing/ambiguous wikilinks 0. |
| <code>.website</code> unit tests | 33/33 passed | Publication policy, source gates, route metadata, path redaction, resource allowlist, repository scan. |
| Full <code>.website</code> build | Passed | 880 source Markdown, 723 full pages, 157 stubs, 204 assets, 883 staged Markdown, 2,400 HTML pages. |
| Supplemental checks | Passed | <code>git diff --check</code> clean; tracked <code>__pycache__</code>/<code>.pyc</code> under projects 0; three outer local/submodule states untouched. |

## Key sources

This record's <code>source_checked</code> summarizes Phase 4 review on 2026-07-19. Course-level external-source dates remain those stated in each page.

- Lewis et al., [Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401), [RAGAS](https://arxiv.org/abs/2309.15217), [ARES](https://arxiv.org/abs/2311.09476), and [BEIR](https://arxiv.org/abs/2104.08663): RAG baselines and heterogeneous-retrieval/evaluation limits.
- [OWASP LLM08:2025 Vector and Embedding Weaknesses](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/), [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/), [MCP Client Concepts](https://modelcontextprotocol.io/docs/learn/client-concepts), and [NIST AI 600-1](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf).
- Google SRE, [Implementing SLOs](https://sre.google/workbook/implementing-slos/) and [Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/): SLI population, window, error-budget, and alert boundaries.

## Follow-up queue

1. Create an end-to-end Layer B ingestion project connecting source → canonical document → chunk/span → index → RAG citation, and verify version migration, deletion propagation, and no revival of old snapshots.
2. Add strict MCP Resource/subscription validation, real AuthN/AuthZ, cancellation, and revocation propagation; Roots remain a coordination hint only.
3. Add a Tool Calling result envelope for untrusted-result schema/provenance/sensitive fields/status query/<code>OUTCOME_UNKNOWN</code> reconciliation.
4. Implement permission/deletion deep water: hierarchy, explicit deny, ABAC/provenance, index/cache invalidation, retention policy, and physical-purge evidence.
5. Bind complete SLO contract for Monitoring Layer B: population, exclusion rules, compliance window, data-source/query version, change approval, and missing-data policy.
6. Move from fixture digests to external artifact loading, signatures, attestations, approval principals, and immutable storage.
7. Continue route-metadata migration and add genuine RAG/evaluation/safety/LLMOps/monitoring hard prerequisites rather than inferring them from display order.
8. Add controlled tests with real vector databases, rerankers/LLMs, prompt injection/data poisoning, latency/cost, and Provider failures.
9. Replace teaching flags/deterministic IDs with real operator auth, random opaque trace IDs, redacted logs, and controlled audit store.
10. Manually inspect Mermaid, Callouts, long tables, and cross-course navigation in Obsidian/public site.

See the preceding [[maintenance-records/2026-07-19-phase-3-framework-recovery-and-learning-route-metadata-record|Phase 3 record]]. Source/license policy continues to follow the [[maintenance-records/content-quality-and-source-labeling-standard|Content Quality and Source Labeling Standard]].
