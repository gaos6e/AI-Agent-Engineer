---
title: "Evaluation, Operations, and the Incremental Project"
tags:
  - ai-agent-engineer
  - knowledge-base
  - project
  - evaluation
aliases:
  - Knowledge Base Construction Project
source_checked: 2026-07-22
execution_verified: 2026-07-22
content_origin: original
content_status: validated
source_baseline:
  - Python 3.11 sqlite3 and unittest
  - SQLite transaction and UPSERT documentation
  - JSON Schema draft 2020-12
  - Debezium Outbox Event Router documentation
lang: en
translation_key: 知识库构建/05-评测运营与增量项目.md
translation_source_hash: 18173b32f4e84482ce1f387735b1e994c2f15e73cf900ba54cc06d367c0e628c
translation_route: zh-CN/知识库构建/05-评测运营与增量项目
translation_default_route: zh-CN/知识库构建/05-评测运营与增量项目
---

# Evaluation, Operations, and the Incremental Project

## Goal of this lesson

Run an offline, deterministic knowledge-lifecycle project. Its 41 tests make canonical revisions, source sequences, the outbox, published pointers, query-time ACL and text-integrity gates, tombstones, content purging, non-materialization of stale events, and reconciliation concrete. Then establish layered evaluation and operational metrics for a real knowledge base.

## Four layers of acceptance

1. **Ingestion**: authorized-source coverage, failure rate, cursor progress, freshness, and deletion-discovery latency.
2. **Content**: correctness of parsed structure, schema, provenance, ACLs, versions, and critical fields.
3. **Retrieval**: Recall@k, MRR/nDCG, correct filtering, zero-result cases, and stale candidates.
4. **Answer**: citation support, completeness, no-answer refusal, authorization, and safety.

Testing only the final answer makes it hard to locate an ingestion, parsing, retrieval, or generation failure. Testing only similarity cannot prove that users accomplish their tasks. Layer a query set across languages, proper names, time-sensitive questions, permissions, no-answer cases, long-tail cases, and source conflicts.

## Project structure and capabilities

- [[knowledge-base-construction/examples/knowledge_store.py|knowledge_store.py]]: a standard-library SQLite lifecycle implementation.
- [[knowledge-base-construction/examples/test_knowledge_store.py|test_knowledge_store.py]]: regression tests for normal and failure paths.
- [[knowledge-base-construction/examples/source-record.schema.json|source-record.schema.json]]: the source-ingress contract.

Project tables:

| Table | Role |
| --- | --- |
| `documents` | Current, published, sequence, deleted, and access-blocked state for each tenant/document |
| `revisions` / `revision_acl` | Append-only canonical revisions, state hashes, and ACL snapshots |
| `outbox` | Events awaiting projection and retry state, written with the canonical transaction |
| `search_revisions` / `search_acl` | Rebuildable teaching search projections |
| `tombstones` | Deletion sequence, reason, and application-level purge state |

It implements source/build state hashes, no-ops, checkpoints, stale-event handling, same-sequence conflicts, same-sequence deletion-reason conflicts, pipeline reprocessing, continued service from the prior published version, immediate blocking on ACL changes, deletion/restoration ordering, retry after projection failure, deletion propagation, clearing canonical content at the application layer, input/candidate resource boundaries, outbox-revision identity binding, non-materialization of stale events, and query-time recomputation of canonical/projection integrity.

It explicitly does **not** implement a real connector or identity provider, vector/FTS retrieval, distributed messaging, concurrent workers, timeout/dead-letter scheduling, database encryption, backup/WAL erasure, tamper-resistant audit logs, or compliance proof.

## Run the project

From the project root, which contains `docs-CN/`, `docs-EN/`, and `.website/`, use PowerShell 7:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
py -3.11 -B -W error '.\docs-EN\knowledge-base-construction\examples\knowledge_store.py'
```

The program publishes two documents, updates one, simulates a projection failure while proving that the old revision remains visible, retries publication of the new revision, deletes the document, propagates the deletion and clears canonical `content`, then emits a JSON reconciliation report.

Check that its output includes:

- `before_publish[0].revision_number == 1`;
- `after_publish[0].revision_number == 2`;
- an action of `failed` followed by successful projection (the successful projection is not separately listed in actions);
- zero `pending_events`, unpublished/blocked active documents, cross-identity pointers, hash/ACL mismatches, orphaned ACLs, and residual deletion projections; and
- `purged_revisions == 2`.

This proves only that content fields in application tables were cleared. It does not prove physical erasure of SQLite historical pages, the WAL, system snapshots, or backups.

## Run the regression tests

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location '.\docs-EN\knowledge-base-construction\examples'
try {
    py -3.11 -B -W error -m unittest -v test_knowledge_store.py
    py -3.11 -B -O -W error -m unittest -v test_knowledge_store.py
} finally {
    Pop-Location
}
```

The 41 tests cover invisibility before first publication; ACL-group order normalization and limits; idempotent no-ops; checkpoint advancement; stale events; conflicts in state or deletion reason at the same sequence; pipeline reprocessing; retaining an old published version after a failed projection; instant blocking after ACL tightening; tenant isolation; multi-group authorization; immediate hiding after deletion; idempotent tombstones; deletion of a missing object; stale deletion; controlled restoration; Unicode/newline normalization; input, size, and query-candidate gates; unauthorized candidates not consuming the limit; multiple pending revisions; unpublished revisions not materializing; pending upserts not materializing after deletion; rejection of a cross-identity tampered outbox revision; no publication path; defense in depth for a cross-tenant pointer corruption during a query; rehashing actual canonical/search text and source/build state; projection-ACL tampering; content clearing after deletion; and deterministic main-program output.

`-O` removes bare `assert` statements. Production gates use explicit exceptions and database constraints; tests use `unittest` assertions.

Reconciliation cannot merely compare a hash field stored in two places. If an attacker or fault changes only `search_revisions.content` but leaves the old `content_hash`, comparing fields falsely reports agreement. The project recomputes and cross-compares `revisions.content`, canonical ACL/source/build state, and `search_revisions.content/search_acl`; any mismatch blocks `require_reconciled()`.

More importantly, online `search_visible()` does not require a caller to remember to run background reconciliation first. It connects the published pointer to both the canonical revision and search projection, uses canonical ACLs as hard candidate and limit filters, then recomputes the canonical hash, projection-text hash, and ACLs of authorized candidates. Altering only a projection ACL to grant guest access does not put the document in the guest candidate window; background `reconcile()` reports the mismatch. Altering an authorized candidate’s projection text or ACL makes the query fail closed. Thus an unauthorized document neither returns nor displaces a public result from the limit.

These unkeyed digests demonstrate internal consistency under the current trusted code; they do not establish database authenticity. If an attacker can jointly change canonical text, ACLs, every declared hash, and query code, protected fact storage, a MAC/signature, remote attestation, or an equivalent control is still needed. The project does not implement those capabilities.

## Key experiments

### 1. Content updates differ from ACL updates

When content changes but the ACL stays the same, canonical current state advances first and the old published revision keeps serving until the new projection succeeds. When the ACL changes, `access_blocked=1` blocks the old projection immediately and it resumes only after the new ACL projection is complete. This difference is the project’s central security conclusion.

Here, `allowed_groups` is an **upstream-resolved flat allow list**. The project does not implement folder/site inheritance, deny precedence, ABAC, `policy_revision`, permission provenance, or evaluation time. It can therefore prove only a flat ACL lifecycle, not that an enterprise permission resolver is correct. A real system should retain a recomputable permission snapshot and authorization-decision version, and test parent-level tightening.

### 2. Sequence and state hash decide together

- Same sequence plus the same source/build state: `noop`.
- Higher sequence plus the same state: advance only the checkpoint.
- Same sequence plus different source state: conflict.
- Same source state plus a new pipeline version: `reprocessed`.
- An older sequence: `stale_ignored`.

A real connector must replace the teaching integer sequence with its protocol-equivalent semantics.

### 3. Deletion and content purging

The deletion transaction first writes the deleted state, access block, tombstone, and outbox; the query becomes invisible immediately. Only after the worker clears the search projection does `purge_deleted_canonical_content()` permit revision content to be cleared. Governance policy must separately determine how hashes, tombstones, and backups are retained.

Old revision projections after content updates or ACL tightening are currently retained in SQLite. The published pointer and access block make them unqueryable, but the project does not clean them at the end of a rollback-retention period or reconcile `stale_projection_rows`. That is not physical removal after revocation. A production implementation needs an explicit old-projection retention window, cleanup worker, cache/replica propagation SLO, and evidence of completion.

### 4. Stale outbox events must not leave copies

After a source event enters the outbox but before the worker runs, an update, deletion, or restoration may already have occurred. The project validates the event’s tenant/document and revision identity first, then builds `search_revisions` only for an upsert that still equals `current_revision_id`. An earlier upsert is consumed but not materialized. Therefore, when v1 arrives, then v2 or deletion arrives, and only then the worker begins, no never-published search content remains.

This is not a distributed ordering guarantee. Multiple workers, cross-partition reordering, message acknowledgement, and dead-letter replay still require validation in real infrastructure. The project merely turns an erroneous or tampered cross-identity revision pointer into an explicit fault and reduces the stale event’s retention surface.

## Operational metrics and alerts

- source lag, last successful cursor, and full/incremental coverage;
- throughput, error rate, retries, and quarantine-queue age by stage;
- counts and differences for active/current/published/blocked/tombstone states;
- pending-outbox age, maximum per-object event lag, and failed-attempt count;
- distributions of parser/chunker/model/index/policy versions;
- missing ACLs, cross-tenant candidates, and revocation/deletion propagation latency; and
- zero-result rate, stale citations, gold-query metrics, and user corrections.

Thresholds must follow historic baselines, risk, and SLOs. A global average hides small tenants, long-tail formats, and highly sensitive documents, so slice the metrics by tenant, source, format, language, and permission level.

## Integrated assignment: add a chunk projection

Extend the project without turning chunks into canonical facts:

1. Add `chunker_version` and `chunks(revision_id, chunk_id, order, text, hash)`.
2. The same content plus a new chunker triggers reprocessing without inventing a source revision.
3. When a new revision projection fails, old published chunks continue serving.
4. An ACL change or deletion blocks old chunks immediately.
5. After deletion propagation, the chunk count is zero.
6. Design 20 retrieval queries, 5 no-answer cases, and 10 tenant/ACL unauthorized-access cases.
7. Use reconciliation to prove each published revision has contiguous chunk order, complete ACLs, and a real parent pointer.

Definition of done: normal and `-O` tests pass; duplicate/out-of-order events have no side effects; fault injection is retryable; there are no real credentials or large data; and the unverified distributed and physical-deletion boundaries are explicit.

Then continue to [[rag/09-project-offline-provenance-from-source-to-citation|the source-to-citation evidence-chain project]], which upgrades this document-level search projection to elements, chunks, and index generations and validates a single lineage across old snapshots, tombstones, authorization versions, and final citations.

## Common mistakes and troubleshooting

- **Tests cover only the happy path**: retries, out-of-order events, permissions, and deletion remain unproven.
- **Only comparing equal active counts**: tenant/ACL, versions, or parent pointers can still be wrong.
- **Treating this project’s search results as retrieval evaluation**: `instr()` proves neither Chinese tokenization, relevance, nor performance at scale.
- **Claiming compliant deletion after clearing a column**: storage pages, logs, and backups are ignored.
- **Treating the groups in a test as authentication**: real subject groups must come from a trusted identity/authorization system.

## Mastery check

- [ ] I can explain the fact/projection boundary of every project table.
- [ ] I can choose the action from source sequence, source state, and build state.
- [ ] I can prove a failed publication retains the old version while ACL tightening blocks immediately.
- [ ] I can explain why an authorized query must recheck canonical/projection state online rather than treat background `reconcile()` as its only security gate.
- [ ] I can explain why an event may still be consumed after it becomes stale but must not leave an unpublished search projection.
- [ ] I can define propagation and completion evidence from a tombstone through every downstream system.
- [ ] I evaluate ingestion, content, retrieval, and answers separately.
- [ ] I can state the production risks that the SQLite teaching project does not verify.

## References

- [Python `sqlite3`](https://docs.python.org/3.11/library/sqlite3.html)
- [Python `unittest`](https://docs.python.org/3.11/library/unittest.html)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [SQLite Transactions](https://www.sqlite.org/lang_transaction.html)
- [SQLite UPSERT](https://www.sqlite.org/lang_upsert.html)
- [SQLite Foreign Key Support](https://www.sqlite.org/foreignkeys.html)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [Debezium Outbox Event Router](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html)

Sources were retrieved on 2026-07-22. Return to [[knowledge-base-construction/00-index|Knowledge Base Construction]]; the next course is [[chunking-strategies/00-index|Chunking Strategies]].
