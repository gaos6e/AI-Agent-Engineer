---
title: "Ingestion, Provenance, and Normalization"
tags:
  - ai-agent-engineer
  - knowledge-base
  - ingestion
  - provenance
aliases:
  - Knowledge Ingestion Pipeline
source_checked: 2026-07-22
source_baseline:
  - Microsoft Graph delta query documentation
  - W3C PROV-DM Recommendation
  - Debezium Outbox Event Router documentation retrieved 2026-07-22
lang: en
translation_key: 知识库构建/02-采集来源与规范化.md
translation_source_hash: 42868a1683254d2ec4474d99be166dcd19faefc283d793f845de134e243a5ad1
translation_route: zh-CN/知识库构建/02-采集来源与规范化
translation_default_route: zh-CN/知识库构建/02-采集来源与规范化
---

# Ingestion, Provenance, and Normalization

## Goal of this lesson

Design a connector pipeline that can initialize from a full scan, track incrementally, replay idempotently, propagate deletion, and preserve lineage. Understand that cursors have meaning only within a specific source protocol and that failures must never disappear silently.

## A connector is not a “download function”

Every source connector should record at least:

- the source, tenant, owner, and evidence of authorization;
- permitted containers, folders, sites, or API scopes;
- full-enumeration method, incremental signal, and cursor semantics;
- pagination, rate limits, timeouts, retries, and maximum object limits;
- a stable external ID, version/ETag, permissions, and deletion representation;
- sensitivity classification, license, retention, and accountable owner; and
- connector/schema versions and test fixtures.

Being technically able to fetch something does not mean it is authorized for ingestion. Credentials belong only in a controlled secrets system, never in source records, logs, or example files.

## Full ingestion, increments, and cursors

The first synchronization usually requires a paginated full enumeration. Later runs may use a change feed, delta token, modification sequence, event log, or controlled time watermark. A cursor is part of the source protocol; do not assume it is a timestamp or a comparable string.

The official Microsoft Graph delta-query flow returns `@odata.nextLink` or `@odata.deltaLink`; callers should store and use the URL it returns. Its token is opaque state. Supported scope and limitations differ by resource, and deletion is represented according to the resource protocol. In engineering terms:

- persist the cursor for the last successfully completed batch, rather than overwriting it when a request starts;
- do not parse or concatenate opaque tokens;
- recover a failed page from a position allowed by the protocol;
- have a controlled full-resynchronization strategy for token expiry or permission changes; and
- state whether the source guarantees ordering, may repeat events, or may omit historical deletions.

This course uses an increasing integer `source_sequence` per document for teaching. If a real API supplies only an ETag or does not guarantee monotonic order, rebuild conflict rules from its protocol rather than copying integer comparison.

A change cursor proves only the synchronization position for one resource query; it is not evidence that authorization remains valid. A connector must separately define which scope changes, site/folder inheritance changes, group changes, or policy updates trigger recomputation of a permission snapshot. If a content delta does not report a permission change, an old ACL cannot simply be presumed valid.

## State machine and batch boundaries

```text
discovered → fetched → parsed → normalized → validated → staged → published
      ↘ retryable_failed / quarantined / permanently_rejected
```

At every stage, retain a run ID, input/output versions, error classification, and replay pointer. Network timeouts and rate limits can be retried according to the [[api/00-index|API]] strategy; unauthorized access, permanently corrupt formats, and schema conflicts must not be retried forever.

Batch gates may check expected versus actual object counts, empty content, parse failures, missing source or ACL data, abnormal size, duplicate rate, sudden deletion growth, and version distribution. If a risk threshold is exceeded, keep the old published view and isolate the new batch. Do not expose a mixture of old and new content.

## Provenance and lineage

For every canonical revision, retain the external/source ID, source URI, source version/sequence, raw/normalized hash, connector/schema/pipeline versions, run ID, permissions/license, and parent-entity location. For every derived artifact, retain its parent revision, transformation activity, and configuration/model version.

This corresponds to W3C PROV-DM’s entity/activity/agent/derivation model, but the implementation may be relational tables or JSON rather than a full copy of the standard. The important questions are:

- Which element of which source-document revision produced this chunk?
- Which connector and pipeline produced it?
- Why can the current user see it?
- Which downstream artifacts must become invalid when the source is deleted or a rule changes?

## Normalization and deduplication

Normalization may standardize newlines, Unicode, language tags, time formats, enumerations, and field names, but must retain original values or parent versions and the transformer version. Title inference, converting table rows to sentences, and search text are derived artifacts; they must not impersonate quoted source text.

Hashes work for exact content comparison. Near duplicates, template headers/footers, and merging multiple versions need separate rules. Content that is identical under different tenants, licenses, or ACLs must not share a public projection merely because its hashes match. Define the deduplication unit together with its authorization boundary.

## Idempotency, out-of-order events, and the outbox

At-least-once delivery is common in production, so writes must be idempotent. Use unique constraints, state hashes, and event IDs together to distinguish a `noop`, a new revision, a stale event, and a conflict. The same source sequence carrying different state must raise an alert rather than use last-writer-wins behavior.

If the canonical transaction commits but message publication fails, the index can fall permanently behind. If the message succeeds but the transaction rolls back, a nonexistent revision can be projected. A transactional outbox writes the canonical change and the event awaiting projection in the same database transaction, then lets an independent worker retry. Current Debezium Outbox Event Router documentation presents this pattern to avoid inconsistent service-internal and consumer state and explains that a unique event ID can deduplicate at the consumer.

An outbox still does not automatically provide business-level exactly-once behavior. Consumers must be idempotent, events must be ordered within an object, failures and dead letters must be replayable, and reconciliation must find events left unprocessed for too long.

## Common mistakes and troubleshooting

- **Treating `mtime` as the only change signal**: copies, time zones, and source behavior can mislead it.
- **Saving a new cursor before processing a page**: a mid-page failure can skip data permanently.
- **Calling a connector fresh because it returned 200**: it may have synchronized only part of the scope or permissions may have changed.
- **Overwriting original values during normalization**: the result cannot be explained or reprocessed.
- **Deduplicating identical content across ACLs**: permissions may leak.
- **Only logging a failed task**: without a quarantine queue, replay, and owner, hidden operational debt accumulates.

## Exercises

1. Write a connector manifest for a folder source and another for an API source, including full ingestion, increments, deletion, and cursor-expiry flows.
2. Simulate 100 objects, 3 parse failures, and a sudden increase of 50 deletions; define the publication/isolation decision and its evidence.
3. Draw the commit boundary between the canonical transaction and outbox worker, then design the consumer deduplication key.
4. Map a source revision, parsed element, and chunk to a simplified entity/activity/derivation table.

## Self-check

- [ ] I know that whether a cursor is comparable depends on the source protocol.
- [ ] I advance a persistent cursor only after complete success.
- [ ] Every record can be traced back to its source, run, connector, and pipeline version.
- [ ] Identical input is replayable, while stale events and same-sequence conflicts have different states.
- [ ] I can explain what an outbox solves and what it does not.

## References and next step

- [Microsoft Graph delta query overview](https://learn.microsoft.com/en-us/graph/delta-query-overview)
- [W3C PROV-DM](https://www.w3.org/TR/prov-dm/)
- [Debezium Outbox Event Router](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html)

Sources were retrieved on 2026-07-22. Next: [[knowledge-base-construction/03-versioning-deletion-and-authorization|Versioning, Deletion, and Authorization]].
