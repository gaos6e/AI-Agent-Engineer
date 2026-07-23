---
title: "2026-07-19 Phase 5 Provenance, MCP, and Tool Result Evidence Chain Record"
aliases:
  - AI Agent Engineer Phase 5 optimization record
tags:
  - AI-Agent-Engineer
  - maintenance
  - provenance
  - mcp
  - tool-calling
  - security
content_origin: original
content_status: validated
source_checked: 2026-07-19
lang: en
translation_key: 维护记录/2026-07-19-第五阶段来源MCP工具结果证据链记录.md
translation_source_hash: af77cafba84d27eb5928e440861ceadcaa1e693bfc9253c6b82bf4a26d291485
translation_route: zh-CN/维护记录/2026-07-19-第五阶段来源MCP工具结果证据链记录
translation_default_route: zh-CN/维护记录/2026-07-19-第五阶段来源MCP工具结果证据链记录
---

# 2026-07-19 Phase 5 Provenance, MCP, and Tool Result Evidence Chain Record

This phase delivers three Layer B items from Phase 4: source-to-citation provenance, MCP Resources/subscription safety, and Tool Result dual projections with unknown-outcome reconciliation. The primary Agent unified provenance baseline, identity semantics, public/protected boundary, cross-course terms, and final regression. Specialist Agents reviewed MCP, Tool Result, and document consistency in directory-isolated changes; the primary Agent replayed counterexamples and repaired residual gaps.

> [!important] Conclusion boundary
>
> This is a standard-library offline reference implementation, a stable-specification subset, and deep review of high-priority courses. It does not prove the vault as a whole has page-level validation, nor that real OAuth, SDKs, network transport, vector databases, LLMs, distributed exactly-once, signed artifacts, or physical deletion are implemented. Digest fields show consistency within one trusted pipeline, not cross-service authentication or third-party attestation.

## 1. Source to citation: a recomputable Layer B

- Added an offline source-to-citation evidence-chain project using UTF-8 Markdown fixtures linking source event, canonical revision, parse revision, element, chunk, index entry, published generation, ACL-before-score, extractive claim, and citation.
- <code>canonical_revision_id</code>, <code>parse_revision_id</code>, <code>element_id</code>, <code>chunk_id</code>, <code>index_entry_id</code>, and <code>index_generation_id</code> use a bounded canonical-JSON domain plus complete SHA-256. Original/retrieval text respectively stores <code>content_sha256</code>/<code>retrieval_sha256</code>.
- A public citation retains source URI/version; raw/canonical/parse/element/chunk/index identity; and exact half-open character span. Global generation, selected-entry IDs, aggregate filtering summary, and authorization version are protected audit only, preventing private-corpus change from affecting public response. The teaching trace hashes full runtime query only for tamper recomputation; production public request IDs must be random and not derivable from authorization context.
- The validator does not trust audit-reported selection. It recomputes candidate set, rank, top-k, filter summary, claim, span, and trace from trusted query, current ACL, index generation, and lexical rules.
- A generation binds source snapshot, tombstone, authorization revision, pipeline fingerprint, and full entry set. Once a new generation publishes, old one becomes <code>superseded</code>; ACL tightening, revocation, deletion, and stale snapshot fail closed.
- Fixture binding includes raw JSON SHA-256 and strict-load typed-model SHA-256; in-memory mutation after load requires revalidation. The evaluation artifact separately binds fixture, pipeline, snapshot, tombstone, authorization, index manifest, and harness revision.

Upstream contracts were tightened too: Document Parsing binds parse revision to raw hash, parser name/version, and config hash, then element identity to parse revision/type/coordinate space/line span/body hash; Knowledge Base reconciliation recomputes canonical/search body hashes rather than trusting two database digest fields; Chunking binds index entry to chunk, actual retrieval hash, index revision, and ACL snapshot so title-path/table-header changes invalidate an old index record. RAG09 remains an independent reference model, not wire integration: line coordinates, lexical-unit spans, SQLite integer revisions, and canonical character spans still need versioned adapters and migration tests to connect in production.

## 2. MCP: Resources, subscriptions, and authorization snapshot

- The teaching profile is fixed to official latest <code>2025-11-25</code>; <code>2026-07-28</code> appears only as a release candidate under <code>/specification/draft</code>, not in the stable contract.
- The offline fixture grows to 54 cases: Resource list/templates/read/subscribe/unsubscribe; list-changed/updated; failed subscribe/cancel; child resources; paging; URI; RFC 6570 templates; canonical Base64; aggregate-size gates.
- One page allows at most 256 items; read allows at most 64 content items totaling 64 KiB. Exact request/response fields, cursor, URI, MIME, text/blob exclusivity, and duplicate content are all validated.
- An active subscription is created only after successful subscribe. Failed subscribe never authorizes <code>updated</code>; failed unsubscribe preserves the old subscription; duplicate pending operations are rejected. Authorization-revision changes clear old subscriptions and block stale reread/update.
- Course-added <code>transport_context</code> is explicitly not an MCP wire field. It binds active token, audience, RFC 8707 resource indicator, tenant, scope, authorization revision, and revocation policy to a resource operation. Roots remain client-coordination hints, not token, ACL, or sandbox.

## 3. Tool Result v2: model projection, audit projection, and unknown outcome

- Fixture becomes <code>tool-cases-v2</code>: 18 cases and 23 <code>dispatch/query_status</code> steps for read/write authorization, approval, idempotency, call conflict, rate limit, pre-execution timeout, lost post-submit response, receipt reconciliation, and persistent unknown.
- Every tool has exact output schema. Business data is always <code>untrusted_data</code>; error state, recovery action, and <code>OUTCOME_UNKNOWN</code> originate only from the dispatcher's fixed error catalog, so a handler cannot inject top-level status/recovery/sensitive/control fields.
- <code>model_result</code> is the sole projection allowed back to model/Provider. Subject references, Provider context, full tool contract, downstream request/receipt/status reference, redactions, and digests exist only in <code>protected_audit</code>.
- <code>request_sha256</code> binds subject/tool/arguments and input/output/effect revision; <code>result_sha256</code> binds full model projection; <code>call_binding_sha256</code> binds Provider/API family, response/call/operation, adapter, full tool contract, idempotency key, and both earlier digests. All use full 64-character lowercase hex and are recomputed.
- A counterexample showed that replacing only <code>idempotency_key</code> could reuse a package. The repair places it in call-level binding while excluding it from business request digest: the same intent can retry under a new call, but its result remains bound to the execution key.
- Cross-call package/model-result swaps, forged digests, forged source labels, missing/duplicate/unknown result sets, and protected-audit leakage into Provider payload are rejected. <code>query_operation_status</code> rechecks current subject/resource authorization; without trusted receipt, status stays <code>OUTCOME_UNKNOWN</code> and a non-idempotent write is not guessed successful or replayed.
- OpenAI Responses, Anthropic Messages, and Gemini Interactions adapters serialize verified model projection only. They are schema-only teaching adapters, not live SDK or streaming-continuation integration tests.

## 4. Cross-course consistency repairs

- Document Parsing, Knowledge Base, Chunking, and RAG project commands use current project root as cwd so public-repository users do not mistakenly invoke a path outside the vault.
- Route 22→29 now explicitly passes Chunking, Embedding, Vector Database, Semantic Search, and Reranking before RAG.
- Deep-reviewed indexes/project pages fill <code>content_origin</code>, <code>content_status</code>, and <code>execution_verified</code>. Dynamic official-material pages stay <code>dynamic</code>; local test success does not make a dynamic external fact static/validated.
- RAG uses “public response”/“protected audit” consistently. Lesson 8's fixed enum <code>privileged_audit</code> and Lesson 9's <code>protected_audit</code> are explicitly different schemas. Citation/Generation/Refusal distinguishes Lesson 8 fixture fact/revision schema from Lesson 9 full source/span citation.
- AI Safety now cross-links untrusted tool result, per-tool exact output schema, dual projection, explicit status query, complete-digest binding, MCP, and RAG.

## Verification actually performed

| Check | Result | Evidence boundary |
| --- | --- | --- |
| 7 related offline projects, three modes | 1,239/1,239 passed | 413 each in normal, <code>python -O</code>, warnings-as-errors: Document Parsing 26; Knowledge Base 31; Chunking 32; RAG Lesson 8 68; RAG provenance 62; MCP 94; Tool Result 100. |
| Combined optimization/warning regressions | 194/194 passed | MCP 94 and Tool Result 100 also pass <code>-O -W error</code>. |
| CLI and fault injection | Passed | Provenance normal <code>PASS</code>/retrieval fault <code>BLOCK</code>; MCP 54 cases has 16 positive passes and 38 expected negative rejections; all Tool Result cases/steps report <code>passed=true</code>. |
| Specialist attack review | Passed | Parser/config reuse; joint body/digest tamper; stale title/header index; stale generation; citation/audit tamper; MCP URI/token/subscription bypass; Tool Result swap/forged digest/status injection/idempotency-key replacement all fail closed. |
| Website tests/full build | Passed | Unified site gate reran publication policy, source gate, route metadata, resources, and links. |
| Supplemental checks | Passed | <code>git diff --check</code>, scoped wikilink/JSON parsing, and project <code>__pycache__</code>/<code>.pyc</code> scan; three known outer local/submodule states untouched. |

## Key sources

This record's <code>source_checked</code> means its sources and changes were summarized on 2026-07-19. Dynamic SDKs, candidate specifications, and product message shapes must be version-pinned and contract-tested again on implementation day.

- [W3C PROV Overview](https://www.w3.org/TR/prov-overview/) and [PROV-O](https://www.w3.org/TR/prov-o/): entity/activity/agent/derivation vocabulary.
- OWASP [LLM01](https://genai.owasp.org/llmrisk/llm01-prompt-injection/), [LLM02](https://genai.owasp.org/llmrisk/llm02-sensitive-information-disclosure/), [LLM05](https://genai.owasp.org/llmrisk/llm05-improper-output-handling/), [LLM06](https://genai.owasp.org/llmrisk/llm06-excessive-agency/), and [LLM08](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/).
- [MCP 2025-11-25 Resources](https://modelcontextprotocol.io/specification/2025-11-25/server/resources), [Schema](https://modelcontextprotocol.io/specification/2025-11-25/schema), and [Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization).
- [OpenAI Function calling](https://developers.openai.com/api/docs/guides/function-calling), [Anthropic Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls), [Gemini Function calling](https://ai.google.dev/gemini-api/docs/function-calling), and [RFC 9110 §9.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2).
- [SLSA Build Provenance v1.2](https://slsa.dev/spec/v1.2/build-provenance/) and [OpenTelemetry Signals](https://opentelemetry.io/docs/concepts/signals/): supply-chain analogy and trace/metric/log boundaries. Document hashes are not claimed as SLSA attestation.

## Follow-up queue

1. Wire Document Parsing, canonical store, Chunking, real index, and RAG citation into one versioned artifact schema, with migration/round-trip tests for line/character/page/bbox/DOM/JSON-Pointer coordinate spaces.
2. Use official SDKs for real MCP Streamable HTTP/SSE, token signature, issuer/audience/resource/expiry, 401/403, introspection, reconnect, and distributed-subscription recovery.
3. Add real Provider contract tests pinned to OpenAI/Anthropic/Gemini SDK/API versions, covering streaming tool call, parallel result order, continuation token/interaction, thinking-item continuation, and Provider errors.
4. Upgrade mocks to atomic database transactions, unique constraints, outbox, receipt/status query, concurrent/crash recovery; do not claim exactly-once.
5. Add controlled signature/MAC, key rotation, immutable storage, approval principal, and verification policy to artifact manifest, rather than merely comparing self-reported SHA-256.
6. Test real retrieval with Embedding, vector database, reranker, LLM, indirect prompt injection, data poisoning, over-authorization, and post-revocation cache/index invalidation.
7. Implement hierarchy, explicit deny, ABAC/provenance, retention, backup erasure, and auditable-purge evidence.
8. Manually inspect new Mermaid diagrams, Callouts, wide tables, and cross-course navigation in Obsidian/public site.

See the preceding [[maintenance-records/2026-07-19-phase-4-rag-evaluation-safety-and-production-evidence-chain-record|Phase 4 record]]. Source/license policy continues through the [[maintenance-records/content-quality-and-source-labeling-standard|Content Quality and Source Labeling Standard]].
