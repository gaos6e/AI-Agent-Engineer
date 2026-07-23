---
title: "Writes, Updates, Deletes, and Versions"
tags:
  - ai-agent-engineer
  - vector-database
  - data-lifecycle
  - deletion
aliases:
  - Vector Data Lifecycle
  - Vector-store data lifecycle
source_checked: 2026-07-22
source_baseline: "Qdrant Points, pgvector, and PostgreSQL Transactions official
  material, checked through 2026-07-22"
content_origin: original
content_status: dynamic
lang: en
translation_key: 向量数据库/04-写入更新删除与版本.md
translation_source_hash: d12e4279734693bcc5dc986f91e471cf619ffbf67c425204a081d6f7c5a958ce
translation_route: zh-CN/向量数据库/04-写入更新删除与版本
translation_default_route: zh-CN/向量数据库/04-写入更新删除与版本
---

# Writes, Updates, Deletes, and Versions

## Learning objectives

Design a replayable, reconcilable data lifecycle: idempotent upserts with stable IDs; coherent source, permission, and vector updates; partial-failure recovery; deletion tombstones and physical cleanup; and dual-version releases for models and indexes.

## Write from a canonical revision

A point should not be defined by “a vector calculated temporarily by one script.” Bind it to:

~~~text
tenant + point_id
source_id + source_revision
chunk_id/span + actual input hash
embedding space + revision
payload/ACL revision
ingestion job + attempt
~~~

[[knowledge-base-construction/00-index|Knowledge Base Construction]] can use a canonical revision plus an outbox to produce events. An embedding worker processes only an explicit revision, then reports state after the vector-store write. This permits reconstruction from the system of record rather than from a one-time, non-replayable call.

## Stable IDs and idempotent upserts

Retries for the same logical point use the same ID. If **source_revision** is an upstream-generated opaque identity, the vector store neither knows its business ordering nor may infer it from a string relation such as **r10 > r9**. A safe single-point state machine is:

- If the ID does not exist and the caller asserts it is currently absent: create it.
- A retry of an entirely identical point is a no-op. If the first successful response was lost, this does not increase versions again.
- If the ID exists and content differs, the caller supplies an **expected_source_revision** representing the expected current value. Update only when it exactly matches the current value.
- Different vector, payload, or content hash under the same **source_revision** is a conflict, not an update.
- After a successful update, any concurrent or late write that still carries the old expected current value fails CAS and cannot overwrite current state.

Thus, a “new revision” is an upstream workflow identity published after successful CAS. It is not a conclusion drawn from the lexical size of a revision string. Opaque also does not mean reusable: the canonical source must prevent reuse of an old **source_revision** for one point across its full lifecycle. Otherwise an ABA cycle such as **r1 → delete → r2 → delete → r1** can cause a stale **delete(r1, d1)** to match again. Stronger systems incorporate an unreusable generation, monotonic row version, or permanent history fence into CAS.

A request can carry:

- event or job ID;
- expected source revision;
- content or input hash;
- expected store or row version;
- embedding-contract signature.

Products differ in compare-and-set, transaction, and write-ordering support. Without them, the application still keeps versions and reconciles before and after writes. Do not interpret “upsert” as automatic resolution of out-of-order concurrency. As of 2026-07-22, Qdrant Points documentation describes payload-version conditional updates and **insert_only** and **update_only** modes. These are product-level concurrency primitives; they do not understand business order among source revisions or deletion policy.

## Partial success

A batch write can:

- fully succeed;
- succeed for only some points;
- time out at the client although the server completed;
- succeed on one shard or replica while another is recovering;
- mix valid records with bad dimensions or payloads.

A reliable flow:

1. Give each item a stable ID and input hash.
2. Persist the provider or database request ID.
3. Parse per-item or per-batch results.
4. Read back or confirm successful items, according to risk.
5. Retry only unknown or temporary failures.
6. Quarantine permanently bad data.
7. Close the set difference **expected IDs − published IDs**.
8. Record a total retry budget.

An HTTP 200 does not prove an entire batch is complete, and one timeout does not justify rewriting every item under new IDs.

## Updates are a multi-field consistency problem

When body text or a chunk changes, synchronize at least:

- vector;
- source revision;
- content/input hash;
- document/chunk mapping;
- ACL/status;
- embedding revision;
- indexed/published revision.

The most dangerous states are “new vector plus old ACL” and “old vector plus new body.” The remedy depends on the product.

### One database transaction

When pgvector is in a PostgreSQL table, a database transaction can commit the vector, relational fields, and business state together. Embedding API work still occurs outside the transaction; normally compute the derived result first, then perform a short write transaction.

### Staging plus publish

In a dedicated vector store or cross-system pipeline, write a staging space or version. Reconcile counts, hashes, ACLs, and quality, then atomically switch the published alias or pointer.

### Versioned records

Keep **point_id + source_revision** in parallel, and let queries read only the published revision. Clean up the older version after switching. This adds storage but gives a clear rollback.

Do not let each application instance switch configuration independently. Use one shared read pointer.

## Permission updates have priority

An ACL change does not necessarily require a new vector, but it must update every readable path immediately:

- payload in the active collection;
- old and shadow spaces;
- sparse or inverted indexes;
- query, result, and parent caches;
- replicated copies;
- revocation logs replayed after export or backup recovery.

If vector and payload cannot be updated atomically, the security baseline is to make **status** unsearchable first, update ACL/vector, validate, then republish. Do not retain a temporarily broad permission state.

## Three layers of deletion

### Logical invisibility

Exclude the point from query immediately, often through a tombstone, **status=deleted**, or point deletion. Record the deletion event, tenant, source revision, and time or sequence. A delete can arrive before the index write: even if the vector store has never seen the point, persist a deletion-intent fence for the intended tenant, source, and event. Treating “not found” as success without state lets a late create republish deleted content.

### Index and storage reclamation

ANN graphs, segments, WAL, and compaction can reclaim storage later. A successful delete API call does not imply immediate disk reduction or absence of old segments from backups.

### Retention and compliance

Synchronize:

- the canonical source;
- all chunks, points, and named vectors;
- every embedding space;
- sparse and keyword indexes;
- caches, exports, and debug artifacts;
- retention and expiry of snapshots and backups;
- audit evidence.

Whether immutable backups can be physically deleted immediately depends on governance, law, and system design. Record quarantine, expiry, and deletion replay after recovery; do not falsely promise that every replica has been physically erased.

## Tombstone purpose and risks

A tombstone prevents old events from unexpectedly resurrecting a deleted point and helps replay deletions after recovery or migration. It includes at least:

- point/source ID;
- tenant or security domain;
- **deleted_source_revision**, the source identity actually bound at deletion;
- a current, unique, traceable **delete_event_id** or delete fence;
- store/row revision or time at deletion;
- retention and physical-purge state.

Risks include:

- unbounded tombstone growth;
- reuse of an ID by another tenant;
- an unauthenticated caller squatting on another point ID with delete-before-create;
- resurrection because recovery lacks tombstones;
- undefined order of concurrent upsert and delete;
- ABA from source-identity reuse across lifecycles.

Define a resurrection policy: whether it is allowed in a tenant and which source revision or approval it requires. Reject cross-tenant ID reuse by default. While a tombstone is current, a delete retry is idempotent only if tenant, **deleted_source_revision**, and **delete_event_id** all match. Any partial mismatch is a conflict. Delete-before-create writes a tombstone for a nonexistent ID, so the delete API must derive tenant and source from trusted identity and canonical mapping. Otherwise it enables ID squatting.

This course's toy project schema v2 retains **point_id + tenant_id + deleted_source_revision + delete_event_id + deleted_at_store_revision**. A delete for an unknown or unindexed point writes the same fence. A tombstone rejects upsert by default. In the same tenant, explicit resurrection requires a **ResurrectionToken** matching the old source and delete event and a different new source identity. The token is a concurrency/replay fence, not an authorization credential. Identity, authorization, and business approval still occur before the call. Cross-tenant resurrection is always rejected.

After successful resurrection, the toy store removes the current tombstone. Consequently, **delete_event_id** fences only the current deletion state; it is not permanent audit history. A production system writes create/update/delete/resurrection events to an external append-only lifecycle or audit log and uses a generation/history ledger to prevent revision ABA. This example lacks both, so it cannot claim to block every historical stale event.

Schema v1 tombstones lack source and delete fences. The script explicitly refuses automatic migration and requires rebuilding from the canonical source. Inventing a fence would create historical state that cannot be proven.

## Embedding and index-version migration

Follow the complete process in [[embeddings/04-similarity-indexing-and-space-migration|Similarity Indexing and Space Migration]]:

1. Freeze the old space contract and alias.
2. Create a new collection or index.
3. Recompute from canonical chunks, not from old vectors.
4. Reconcile IDs, source/hash, ACL, tombstones, dimension, and norm.
5. Evaluate old-query-to-old-index and new-query-to-new-index independently.
6. Use shadow traffic or a canary.
7. Atomically switch reads.
8. Stop old writes.
9. Keep a rollback window.
10. Reclaim the old space according to deletion and retention policy.

A change in index parameters with unchanged embeddings can use similar blue/green treatment, separating index-build failure from model-quality change.

## Synchronization modes

### Dual write

The application writes the source database and vector database together. This is simple, but one side can succeed while the other fails, so it needs an outbox, retries, and reconciliation.

### Change Data Capture or outbox

The source transaction commits business state and an outbox event. A worker updates the vector store asynchronously. Visibility is delayed, but events can be replayed and the system of record is clear. Handle duplicates, reordering, and poison events.

### Periodic reconciliation

Periodically compare canonical ID/revision/hash with the vector store to find missing, stale, orphaned, and tombstone-inconsistent data. This does not replace real-time synchronization; it is the final integrity net.

These modes combine well: an outbox for real time plus nightly reconciliation.

## Publish reconciliation

For every batch or revision:

| Dimension | Check |
| --- | --- |
| Inventory | expected, published, missing, and extra IDs |
| Version | source, embedding, schema, and index-build revision |
| Integrity | content/input/vector hashes, dimension, finiteness, and norm |
| Security | tenant, ACL, status, and authorization-escape tests |
| Lifecycle | deletes, tombstones, and purge queue |
| Quality | canary/gold top-k and critical slices |
| Operations | errors/retries, searchable lag, and index readiness |

Extra or orphaned points are as dangerous as missing points. Do not compare counts only: one missing and one extra point can leave the count unchanged.

## Common mistakes and diagnosis

- **Retries create new IDs:** use stable IDs plus event/input hashes.
- **An old event overwrites new content:** compare source revision through CAS.
- **A missing point discards the delete:** still write a deletion-intent fence to block late create.
- **Source identity is reused across lifecycles:** use an unreusable generation/row version or permanent history ledger to avoid ABA.
- **Vector and ACL update in separate, searchable steps:** withdraw status first or use a transaction/staging.
- **HTTP 200 means the batch succeeded:** reconcile items and set differences.
- **Deleted content returns:** recovery or out-of-order upsert lacks a tombstone/version.
- **Only the current collection is deleted:** old spaces, cache, sparse indexes, and backups are missed.
- **Model vectors overwrite in place:** old and new spaces mix; use dual indexes.
- **Only point count is compared:** add ID-set, hash, and ACL reconciliation.

## Practice

1. Treat source revision as opaque and unreusable. Write accept/reject rules for two concurrent writers using expected-current CAS, and explain ABA.
2. Design a recovery state machine for a 100-item batch with 97 successes, two temporary failures, and one bad dimension.
3. Draw the safe publication order when ACL tightening and vector update cannot be atomic.
4. Map a document deletion to 12 chunks, two spaces, a keyword index, two caches, and backup retention.
5. Compare dual-write and outbox failure paths and reconciliation.
6. Design delete-before-create, same-tenant resurrection token, actual authorization check, and cross-tenant ID-reuse policy. Explain why a fence, authorization, and permanent audit log cannot replace one another.

## Mastery check

- [ ] Point writes bind canonical, source, input, and embedding revisions.
- [ ] A completely identical upsert is idempotent; non-identical updates explicitly match expected current state, and different content under the same revision conflicts.
- [ ] Partial or unknown success is reconciled item by item rather than blindly retried as a batch.
- [ ] Vector, payload, ACL, and status are coherent in a visible version.
- [ ] Deletion covers logical invisibility, physical reclamation, and retention governance.
- [ ] A delete records a current fence even before create; unknown-ID deletion, authorization, resurrection, and permanent audit history have clear boundaries.
- [ ] The canonical source does not reuse a point's source identity; stronger systems use a generation/history ledger against ABA.
- [ ] Model/index migration uses a new space, evaluation, atomic switch, and rollback.
- [ ] Periodic reconciliation checks ID sets, hashes, ACLs, and deletion.

## Summary and next step

After the single-node lifecycle is correct, sharding, replicas, and concurrency add stale reads, reordering, and partial availability. Next: [[vector-databases/05-consistency-sharding-and-replicas|Consistency, shards, and replicas]].

## References

- [Qdrant: Points](https://qdrant.tech/documentation/manage-data/points/)
- [Qdrant API: Upsert points](https://api.qdrant.tech/api-reference/points/upsert-points)
- [pgvector official repository](https://github.com/pgvector/pgvector)
- [PostgreSQL: Transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html)
- [[knowledge-base-construction/00-index|Knowledge Base Construction]]

Sources were retrieved on 2026-07-22. Return to the [[vector-databases/00-index|Vector Databases index]].
