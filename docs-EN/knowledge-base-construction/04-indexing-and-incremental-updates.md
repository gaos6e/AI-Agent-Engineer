---
title: "Indexing and Incremental Updates"
tags:
  - ai-agent-engineer
  - knowledge-base
  - indexing
  - outbox
aliases:
  - Incremental Knowledge-Base Indexing
source_checked: 2026-07-22
source_baseline:
  - Debezium Outbox Event Router documentation retrieved 2026-07-22
  - SQLite UPSERT documentation retrieved 2026-07-22
  - SQLite transaction documentation retrieved 2026-07-22
  - SQLite FTS5 documentation retrieved 2026-07-22
lang: en
translation_key: 知识库构建/04-索引与增量更新.md
translation_source_hash: abd2420c0217189a7cacccde2ce1f5c1da1b8b82e7cccde13d32ab12f4107ad9
translation_route: zh-CN/知识库构建/04-索引与增量更新
translation_default_route: zh-CN/知识库构建/04-索引与增量更新
---

# Indexing and Incremental Updates

## Goal of this lesson

Treat metadata, lexical, vector, and graph indexes as versioned derived projections that can be replayed and reconciled. Use state hashes, an outbox, idempotent consumers, and published pointers to handle creation, update, deletion, reprocessing, and rebuilding safely.

## Canonical store and derived projections

The canonical store keeps explainable revisions, sources, permissions, and processing state. Retrieval projections optimize queries:

- **metadata store**: IDs, versions, tenant, ACLs, state, and time;
- **lexical/full-text**: exact words, code, proper names, and phrases;
- **vector**: semantic neighbors;
- **optional graph**: explicit entities and relationships; and
- **cache**: short-lived copies of frequent queries, candidates, and answers.

Every damaged projection should be rebuildable from canonical revisions plus a versioned pipeline/configuration. Do not infer original text back from a vector, and do not make an ACL that exists only in one index the sole authorization fact.

## The dependency graph determines invalidation scope

```text
source revision
  └─ parsed elements (parser/config)
       └─ chunks (chunker/config)
            ├─ lexical projection (tokenizer/index schema)
            └─ embeddings (model/preprocessing)
                 └─ vector projection (metric/index params)
```

Examples of the decision:

| Change | What to recompute |
| --- | --- |
| Content hash unchanged; ACL unchanged | `noop`, or only advance the source checkpoint |
| Source content or structure changes | Parsing for that document and every downstream artifact |
| Chunker version changes | Chunks, embeddings, and lexical/vector downstream artifacts |
| Embedding model changes | Embeddings and the vector projection |
| Tokenizer/index schema changes | Lexical projection |
| ACL/policy changes | All executable authorization projections and caches; block immediately when necessary |
| Deletion | All online projections, caches, and subsequent retention processes |

Persist the parent ID, algorithm/model/configuration version, and hash at each layer so that only genuinely affected work is recomputed.

## From the canonical transaction to the outbox

Write the canonical revision/current state and outbox event in one transaction so they succeed or fail together. At minimum, an event contains a unique event ID, tenant/document key, within-object event version, kind, and revision pointer. The consumer:

1. processes in object order or recognizes stale events;
2. verifies the event’s tenant/document, revision pointer, and current state first; an event superseded by an update or deletion may be marked consumed, but it must not materialize a search copy;
3. writes projections idempotently using the event/revision ID and unique constraints;
4. atomically switches the published pointer only after the projection is complete;
5. marks the event complete after success, or records a safe error and retries/quarantines it on failure; and
6. periodically reconciles pending events with canonical/published state, recomputing hashes from the actual canonical and projection text rather than comparing only two hash fields that could both be stale or forged.

The fact that a pointer eventually stops pointing at an old revision does not prove correct deletion propagation. If a worker writes an obsolete event into a search table first, it can still remain in physical storage, backups, or erroneous internal queries. The teaching project therefore materializes search projections only for an upsert whose revision is still `current_revision_id`, and fails closed when an outbox revision’s tenant/document identity disagrees. That still does not replace proof of ordering and concurrency in a real message bus.

Debezium’s Outbox Event Router documentation uses a unique event ID for consumer deduplication and an aggregate key as the message key to preserve order within a Kafka partition. A concrete messaging system can still deliver duplicates; application consumers cannot omit idempotency.

SQLite `UPSERT` performs `DO UPDATE` or `DO NOTHING` only when a unique constraint conflicts; it is not automatic business idempotency. Choose the right conflict target and validate the state/event version. Foreign keys must also be explicitly enabled on a SQLite connection.

## Publication, rollback, and concurrency windows

For small updates, maintain a published revision per document. For a whole-index migration, build a new generation/alias, then switch the read alias after validating counts, ACLs, deletions, and query samples. Retain the old generation for a short rollback window and delete it later under the retention policy.

Do not use “the worker returned success” as the publication condition. At a minimum, validate:

- whether all active canonical objects have an acceptable published projection;
- whether each published pointer reaches a real projection under the correct tenant;
- whether chunk/embedding counts are within the expected range;
- whether missing ACLs, empty authorization, unpropagated tombstones, and stale-version candidates are all zero;
- whether representative queries, citations, and unauthorized-access tests pass; and
- whether differences between old and new generations are explainable.

When multiple workers run concurrently, define object partitioning, locking or optimistic versions, retries, and transaction isolation. SQLite permits only one writer at a time; this course’s single-connection demonstration cannot prove distributed concurrency is correct.

## Deletion and rebuilding

A deletion event first makes queries fail closed, then removes individual projections asynchronously. A rebuild must read the current active canonical set and tombstone/retention state; it must not republish every historical revision.

For incremental events that arrive during a full rebuild, use a fixed snapshot followed by catch-up from a recorded watermark, dual-write to old and new generations, or replay the change log from the snapshot position. In every case, prove that the switch neither misses updates nor restores deleted objects.

## The teaching boundary of SQLite FTS5

FTS5 is SQLite’s full-text-search virtual table. It supports tokenizers, BM25, and external-content/contentless modes. Its documentation specifically describes consistency pitfalls for external content: the application must keep the content table and FTS index in sync.

This project does not enable FTS5. It uses `instr()` only to simulate a visibility projection so versions, ACLs, and transactions are easy to verify. It does not represent performance, Chinese tokenization, ranking quality, or a production selection. Retrieval implementations are evaluated later in [[semantic-search/00-index|Semantic Search]] and [[vector-databases/00-index|Vector Databases]].

## Common mistakes and troubleshooting

- **Only adding chunks on update**: the old revision remains searchable, creating duplicates or incorrect citations.
- **Reconciling only task success rates**: successful tasks can still write the wrong tenant/ACL or omit objects.
- **An unversioned index schema**: rolling upgrades leave readers and writers incompatible.
- **Committing a message offset before downstream success**: failed records can disappear permanently.
- **Claiming exactly once**: producer, broker, consumer, and business-write boundaries differ.
- **Rebuilding from every historical revision**: deleted or expired content is restored.
- **Generalizing a SQLite demonstration to distributed concurrency**: real locking, isolation, and fault testing are absent.

## Exercises

1. Write a local-invalidation matrix for source, parser, chunker, model, and ACL changes.
2. Draw the two commit boundaries: “canonical plus outbox in one transaction” and “projection plus published pointer in one transaction.”
3. Simulate a worker failing after writing half its chunks; design idempotent retry and reconciliation.
4. Choose a snapshot/watermark strategy for a full-index rebuild and explain how it prevents missed increments and tombstone restoration.

## Self-check

- [ ] I can distinguish canonical facts from metadata/lexical/vector/cache projections.
- [ ] I can choose the smallest recomputation scope from dependency versions.
- [ ] An outbox consumer has unique events, within-object ordering, idempotency, and failure replay.
- [ ] Publication has count, ACL, deletion, and query reconciliation before and after switching.
- [ ] I know that a SQLite/FTS5 example cannot prove production scale or Chinese retrieval quality.

## References and next step

- [Debezium Outbox Event Router](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html)
- [SQLite UPSERT](https://www.sqlite.org/lang_upsert.html)
- [SQLite Transactions](https://www.sqlite.org/lang_transaction.html)
- [SQLite Foreign Key Support](https://www.sqlite.org/foreignkeys.html)
- [SQLite FTS5](https://www.sqlite.org/fts5.html)

Sources were retrieved on 2026-07-22. Next: [[knowledge-base-construction/05-evaluation-operations-and-incremental-project|Evaluation, Operations, and the Incremental Project]].
