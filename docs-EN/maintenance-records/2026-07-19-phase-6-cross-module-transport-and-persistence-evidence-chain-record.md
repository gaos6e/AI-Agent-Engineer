---
title: "2026-07-19 Phase 6 Cross-Module, Transport, and Persistence Evidence
  Chain Record"
aliases:
  - AI Agent Engineer Phase 6 optimization record
tags:
  - AI-Agent-Engineer
  - maintenance
  - rag
  - mcp
  - tool-calling
  - production
content_origin: original
content_status: validated
source_checked: 2026-07-19
lang: en
translation_key: 维护记录/2026-07-19-第六阶段跨模块传输持久化证据链记录.md
translation_source_hash: 6435e0412506b6a75f2f3b6fdefd1b4a11fb8d4d875bf3a60f0cbe141c807d09
translation_route: zh-CN/维护记录/2026-07-19-第六阶段跨模块传输持久化证据链记录
translation_default_route: zh-CN/维护记录/2026-07-19-第六阶段跨模块传输持久化证据链记录
---

# 2026-07-19 Phase 6 Cross-Module, Transport, and Persistence Evidence Chain Record

This phase delivers three Phase 5 Layer B items: a real Parser/Knowledge Store/Chunking adapter, real loopback MCP Streamable HTTP, and SQLite-persistent Tool idempotency/reconciliation. The primary Agent audited native contracts across repositories first, standardized IDs, coordinates, and publication terms, then reviewed directory-isolated specialist changes. Specialists handled MCP HTTP/OAuth boundary, Tool Calling persistence, and independent red team. Every implementation remains offline with repeatable fixtures; mocks are not presented as real OAuth, Provider, distributed database, or exactly-once.

> [!important] Phase conclusion boundary
>
> “Real” names only the boundary actually crossed here: the RAG adapter imports three existing Python modules; MCP makes <code>127.0.0.1</code> HTTP round trips; Tool persistence uses a multi-connection SQLite file. It does not mean RAG Lesson 9 provenance imports external chunks, a token went through a real AS/JWKS/introspection, or SQLite and downstream form an atomic cross-service transaction.

## 1. Cross-module adapter: move from isolated green checks to an explicit wire bridge

The main path read-only ran 151/151 Parser, Knowledge Store, Chunking, and Lesson 9 provenance tests before wiring them, and compared actual preimages, coordinate systems, and release states. Native Parser contracts use raw-byte hash, parse revision, 1-based inclusive normalized line, and content-addressed <code>elm_</code>; Knowledge Store uses SQLite integer revision/source/build hash/outbox/published pointer/ACL/tombstone; Chunking uses element lexical-unit half-open spans, content/retrieval dual representations, and <code>chk_/idx_</code>; provenance v1 uses independent LF+NFC character spans and separate parse/chunk/index/generation IDs. The adapter supplies tenant, logical document, sequence, ACL, control event, protected raw/canonical sidecar, cross-database revision fingerprint, corpus release, output artifact/schema/generation/line crosswalk, and a clear independent-importer status for provenance.

Audit exposed a real counterexample: byte-identical documents in different tenants get the same Parser native element ID. That is valid content address but cannot be a logical resource or authorization identity. The new fixture retains the collision. The adapter derives <code>xsrc_/xel_</code> from tenant, document, KB revision, and native ID and records each ID's scheme.

The Cross-Module Provenance Adapter and Atomic Publication project:

- Freshly calls current <code>inspect_documents.py</code>, <code>knowledge_store.py</code>, and <code>chunking_lab.py</code>. Lesson 9 provides only a bounded canonical-JSON implementation and remains marked as an independent reparse branch.
- Carries tenant/document/sequence, URI/version, connector/upstream event/run, media/root section, and ACL as explicit control binding, never guessed from body/parser manifest.
- Accepts strict UTF-8 Markdown without BOM and preserves caller's absolute materialization root. Before resolving, it rejects existing root/source/parent symlinks, traversal, and unregistered kind. A root-link-outside test confirms zero writes. Python 3.11 guard does not cover NTFS junction/reparse points, hard links, or concurrent path-replacement TOCTOU.
- Keeps headings <code>context_only</code> and body elements <code>projected_as_body</code>; missing Parser section path permits only trusted <code>root_section_path</code>.
- Binds adapter/Parser/KB/Chunking/provenance module bytes and all contract revisions in a pipeline fingerprint. Evidence validation fresh-reparses/rechunks protected raw snapshot and recomputes native IDs.
- Recomputes KB content/source/build hashes, outbox event identity, revision/search body, ACL, and pointer instead of comparing self-reported database digests.
- Binds release manifest to control/crosswalk, raw/parser, SQLite numeric locator, KB content fingerprint, capture/outbox/tombstone, chunk/index set, authorization, and pipeline; old releases become explicitly superseded.
- Runs current-revision preflight then drains native KB outbox. A content-only build failure never switches KB pointer prematurely; old release may still serve while live deny state instantly blocks ACL/delete.
- Fresh-reparses immutable raw before a parser sidecar enters a new pointer. A forged but internally consistent Parser record is rejected and old pointer/generation remains.

Thirty-four red-team tests cover strict fixture, path/symlink, cross-tenant native-ID collision, release lifecycle, authorization noninterference, layer tamper, fault gates, artifacts, and CLI. Artifact self-hash proves internal consistency only—not trusted rerun, MAC, or signature.

Coordinates remain honest: Parser line positions, Chunking lexical spans, and provenance canonical character spans cannot be losslessly exchanged. A public citation retains native line locator, <code>[unit_start, unit_end)</code>, <code>exact/prefix/suffix</code>, and each layer's IDs. Its canonical-char mapping is explicitly unavailable because a Parser projection is not one exact canonical span; release evidence is <code>document-revision-bridge</code> with <code>external_chunk_to_citation_verified: false</code>. The selector vocabulary borrows from W3C Text Quote Selector without emitting W3C JSON-LD or claiming conformance, and the bounded canonical JSON is not RFC 8785 JCS.

Queries apply tenant, KB live state, and ACL before relevance score and omit global generation/filter counts from public response. Same-ACL content updates can serve old release until complete, but no mixed revision appears when KB pointer advances before adapter pointer. ACL/delete blocks immediately through <code>access_blocked/deleted</code>; resurrection needs higher sequence and a new release. Stale capture, layer/manifest tamper, and unknown retrieval outcome fail closed. <code>retrieval_unavailable</code> returns <code>dependency_unavailable</code> and the offline release gate must <code>BLOCK</code>.

## 2. MCP: move from a message state machine to real loopback transport

The Loopback Streamable HTTP and OAuth Resource Boundary project uses the standard library at a random <code>127.0.0.1</code> port for real POST/GET/DELETE, JSON response, POST SSE, GET SSE, and <code>Last-Event-ID</code> recovery. It checks Origin, Accept/Content-Type, header/body/response/concurrency budgets, <code>MCP-Protocol-Version</code>, session owner/TTL/capacity/DELETE, and event-replay scope.

It implements 401/403, <code>WWW-Authenticate</code>, Protected Resource Metadata document/challenge form, and two RFC 8707 resource bindings at authorization/token request. Because the resource URI is HTTP loopback, it does not claim RFC 9728 compliance. An offline token policy rechecks issuer, audience/resource, scope, tenant, authorization revision, expiry, and revocation per request without echoing bearer/session. Unicode-safe exact comparisons support non-ASCII subject/tenant; malformed Unicode issuer/resource/revision returns stable 401, and invalid UTF-8 surrogate fixture fails at registration. Resource URI is fixed ASCII <code>kb://tenant/</code> with tenant percent-encoded only as path segment, preserving RFC 3986 syntax for Unicode and <code>/ ? #</code>.

Stable <code>2025-11-25</code> remains negotiated. When initialize proposes Draft, the server returns a stable alternative and client chooses whether to disconnect; later headers accept only negotiated stable. The <code>2026-07-28</code> release candidate is migration observation only. This is real HTTP, but tokens are in-process preset claims lookup; authorization server, authorization-code+PKCE, JWKS/signature, introspection, TLS, proxy, HTTP/2, cross-node sessions, and official-SDK conformance remain excluded.

## 3. Tool Calling: move from memory idempotency to SQLite operation ledger

The SQLite Persistent Idempotency and Outbox Recovery project reuses Tool Result v2 request digest, call binding, approval, exact output schema, and dual projection; it does not invent a separate result contract.

- <code>BEGIN IMMEDIATE + UNIQUE(tenant, subject, tool, key)</code> atomically reserves execution scope. Same key/same intent replays; same key/different intent conflicts.
- Operation intent/outbox share one local transaction; local receipt, ledger success, and delivered outbox share one too. Trigger-failure injection verifies rollback.
- A worker uses expiring lease and rechecks current tool-contract revision and resource authorization before effect; drift/revocation does not execute downstream.
- Simulated “downstream committed but no local receipt” stays <code>OUTCOME_UNKNOWN</code>. Repeated dispatch does not replay automatically; only explicit status query reauthorizes, recomputes request/contract/receipt/output, then returns <code>receipt_reconciled</code>.
- Approval ID/digest/expiry/accepted-at persist and recompute. The course distinguishes atomic acceptance of immutable intent within validity and business semantics requiring not-yet-expired approval at downstream commit.
- Database audit emits only irreversible <code>status_*</code> references for orphan downstream receipts, never tenant/subject/tool/idempotency key. Portable UTC upper bounds apply to <code>now</code>/<code>now + lease_seconds</code> before reservation; UTC epoch + <code>timedelta</code> avoids Windows <code>fromtimestamp</code> overflow leaving a half-committed intent.
- <code>now</code> is deterministic test control only. Production needs controlled wall/DB clock, skew monitoring, and fencing; cross-process lease time is not a trust boundary.
- One explicit read transaction audits integrity/FK/operation/outbox/receipt semantics and counts, avoiding a false <code>BLOCK</code> caused by a legitimate reconcile between SELECTs. FULL synchronous enters PASS gate. CLI rc2 exposes a stable path-free <code>error.code</code>; fixture/DB-open failures do not echo raw <code>OSError</code> or paths.

SQLite uses STRICT, WAL, FULL synchronous, foreign keys, and parameterized SQL. WAL reader/writer parallelism still has one writer and depends on same-host wal-index. <code>downstream_receipts</code> is just a separate-transaction stand-in inside the same SQLite file. The course claims local durable ledger and at-least-once-compatible building blocks, no delivery liveness and no cross-service exactly-once.

## 4. Cross-course consistency and learning experience

- RAG09 retains the independent-reference-model warning and links RAG10's real adapter; Parser/Knowledge Store/Chunking now point to their two-phase order.
- RAG10 and three upstream courses use <code>scheme + value</code>, native locator, loss profile, control plane, release pointer, and protected audit consistently.
- MCP distinguishes no-network message validation in Lesson 6 from real HTTP black-box testing in Lesson 8; <code>transport_context</code> is not a wire field.
- Tool Calling 06/07/08 form memory sequential semantics → Tool Result v2 evidence → SQLite durable recovery, always distinguishing business digest from idempotency key/call binding.
- Project commands constrain cwd to current repository. Temporary SQLite files use GUID filenames to avoid reading old ledger on rerun. New courses, fixtures, code, Mermaid, and tests are original; external specifications are fact/boundary checks only.

## Verification actually performed

- Specialist projects: RAG adapter 34/34, MCP loopback 78/78, Tool SQLite 77/77; each passed four-mode unified regression and independent final review under normal and <code>-O -W error</code>.
- Unified Python regression found 66 <code>test_*.py</code>; 61 ran in normal, <code>-O</code>, <code>-W error</code>, and <code>-O -W error</code>, with all four runs 2,338/2,338 passing.
- Five files stayed out of base regression because declared optional CrewAI, LangGraph, Matplotlib, or scikit-learn dependencies were absent. No skip was presented as execution.
- CLI contracts: MCP demo rc0/PASS and attack rc0/BLOCK (four expected attacks rejected); Tool dispatch rc0/PASS/fresh, after-downstream-commit rc1/BLOCK/<code>OUTCOME_UNKNOWN</code>, explicit status rc0/PASS/<code>receipt_reconciled</code>, audit rc0/PASS, missing fixture rc2/<code>FIXTURE_IO_ERROR</code> with no path echo.
- Structure/security: three new JSON/schema files passed strict UTF-8/duplicate-key/nonfinite checks; 160 scoped wikilinks had 0 missing; no real credentials or absolute user paths; <code>git diff --check</code> passed; no new cache/bytecode/SQLite WAL test artifact.
- Website: <code>.website npm test</code> 33/33. <code>npm run build</code> published 889 Markdown pages, 217 assets, 2,655 public files, with broken local links, forbidden files, progress metadata leaks, sensitive leaks, self redirects, table-wikilink leaks, checkbox leaks, and KaTeX errors all 0.

## Key sources

Primary material checked on 2026-07-19 includes [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/), [PROV-O](https://www.w3.org/TR/prov-o/), [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html), and [JSON Schema 2020-12](https://json-schema.org/draft/2020-12); MCP [Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports), [Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization), [Resources](https://modelcontextprotocol.io/specification/2025-11-25/server/resources), and [Schema](https://modelcontextprotocol.io/specification/2025-11-25/schema); [RFC 8707](https://www.rfc-editor.org/rfc/rfc8707.html), [RFC 9728](https://www.rfc-editor.org/rfc/rfc9728.html), [RFC 6750](https://www.rfc-editor.org/rfc/rfc6750.html), [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html); SQLite [Transaction](https://www.sqlite.org/lang_transaction.html), [WAL](https://www.sqlite.org/wal.html), [UPSERT](https://www.sqlite.org/lang_upsert.html), [STRICT Tables](https://www.sqlite.org/stricttables.html); [Python sqlite3](https://docs.python.org/3.11/library/sqlite3.html), [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests), and [AWS ECS idempotency](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html). Dynamic specifications/SDKs still require version pinning on implementation day.

## Follow-up queue

1. Define persistent protected document/chunk external-artifact schema and locator union, letting Lesson 9 actually import Lesson 10 parser/chunk rather than independently reparse.
2. Test real OAuth/SDK interoperability: PKCE, PRM/discovery, resource, JWKS/introspection, step-up, proxy, TLS, revocation latency.
3. Pin actual OpenAI/Anthropic/Gemini SDKs and test streaming/parallel Tool Calling, continuation, and Provider errors.
4. Replace SQLite stand-in with independent ledger/queue/real downstream and add fencing/heartbeat/DLQ, process kill, network partition, receipt/status tests.
5. Upgrade Python-memory published pointer to immutable artifact store + transactional outbox + CAS, testing reader/build/delete/ACL races.
6. Add real retrieval/LLM evidence tests; introduce MAC/signature, rotation, transparency log, retention, backup erasure, purge audit; and manually inspect Mermaid, wide tables, Callouts, navigation, and schema-major migration round trips.

See the preceding [[maintenance-records/2026-07-19-phase-5-provenance-mcp-and-tool-result-evidence-chain-record|Phase 5 record]]. Source/license policy continues through the [[maintenance-records/content-quality-and-source-labeling-standard|Content Quality and Source Labeling Standard]].
