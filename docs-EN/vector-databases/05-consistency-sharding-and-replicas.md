---
title: "Consistency, Shards, and Replicas"
tags:
  - ai-agent-engineer
  - vector-database
  - distributed-systems
  - consistency
aliases:
  - Vector Database Consistency
  - Vector-store shards and replicas
source_checked: 2026-07-22
source_baseline: "Qdrant Distributed Deployment and Points current official
  documentation, checked through 2026-07-22; general concepts are not equivalent
  to its product guarantees"
content_origin: original
content_status: dynamic
lang: en
translation_key: 向量数据库/05-一致性分片与副本.md
translation_source_hash: 0a93829c4f1fe5b5da7b890903a9473a25c99b703cd918a456057e57e238165b
translation_route: zh-CN/向量数据库/05-一致性分片与副本
translation_default_route: zh-CN/向量数据库/05-一致性分片与副本
---

# Consistency, Shards, and Replicas

## Learning objectives

Extend a single-node point model to a distributed collection. Understand shards and replicas, write acknowledgements and read consistency, concurrent upsert/delete conflicts, shard keys and fan-out, scaling/rebalancing, and observable tests that define the business semantics actually required.

## A shard is not a replica

### Shard

A collection is divided into non-overlapping data subsets. Each point normally belongs to one logical shard. Sharding supports:

- capacity beyond one machine;
- distribution of queries and writes;
- tenant or partition routing;
- parallel construction and maintenance.

### Replica

A replica is an additional copy of the same shard. Replicas support:

- service during a node failure;
- read distribution;
- upgrade and maintenance;
- lower risk of losing the sole copy of data.

More shards do not automatically add disaster tolerance; more replicas do not automatically add unique capacity. Replication is not backup: every replica can copy an accidental deletion, logical corruption, or malicious write.

## What one query can do

1. An ingress node receives query and filter.
2. It finds relevant shards from the collection topology.
3. Each shard executes a local top-k on one or more replicas.
4. A coordinator merges local candidates.
5. Filtering and ordering semantics are applied.
6. A global top-k is returned.

When a query fans out to every shard, tail latency is determined by the slowest shard. A custom shard key can narrow routing, but a wrong key can omit data or create a hotspot.

Do not assume that a global top-k can be produced from an arbitrary small number of candidates outside each shard's local top-k. Filtering and score distribution affect the oversampling needed for merging.

## Why stale results appear

In a distributed system:

- a write reaches one replica first;
- other replicas apply it later;
- a query reads a replica that has not caught up;
- concurrent upserts arrive in a different order at different replicas;
- a delete interleaves with an older upsert;
- a new index or segment is not searchable yet;
- a shard is transferring or recovering;
- cache still holds old candidates.

“The write API returned success” must map to an explicit acknowledgement level. It does not naturally imply that all later queries immediately see only the new revision.

## State business semantics before selecting a consistency label

Do not start with the terms **quorum**, **strong**, or **eventual**. Answer:

- How many replicas, or which leader, must acknowledge a successful write?
- After the same user writes and immediately searches, is read-your-writes required?
- What is the maximum time before a new revision becomes searchable?
- If two clients write one point concurrently, is the winner defined by source revision, leader order, or last-write-wins?
- When delete and an old upsert arrive out of order, which one wins?
- During node or network failure, should the system prefer availability or reject uncertain reads/writes?
- Must queries read majority or all-consistent results?
- Do collection schema/alias changes have the same guarantee as point writes?
- While index construction is incomplete, is the behavior exact fallback, old index, or rejection?

State the SLO with time, version, and error behavior. For example:

> After source revision r8 is committed, an authorized query must no longer return r7 within 30 seconds. If that deadline is missed, withdraw the document and alert.

This is more testable than “eventual consistency.”

## Write acknowledgements, read consistency, and ordering

Products may provide:

- write acknowledgement count or factor;
- leader or strong ordering;
- reads from one, quorum, majority, or all replicas;
- wait until an operation is applied;
- optimistic row/version conditions;
- transactions scoped to a table, shard, or larger range.

Stronger confirmation normally needs more active nodes and network round trips, and reduces availability during a partition. Check current product documentation and failure-test the exact semantics, including whether a failure can leave partial application.

Documentation checked on 2026-07-22 distinguishes Qdrant collection-topology consensus from point operations and exposes write consistency, read consistency, and write-ordering options. Points documentation also describes payload-version conditional updates. Defaults and scope are product facts for that version, not a general vector-database model, and conditional updates still cannot interpret business source identity. pgvector inherits PostgreSQL transaction and replication semantics, which are different.

## Use versions to resolve business conflicts

Database ordering chooses execution order, not which source revision is semantically correct. If **source_revision** is opaque, do not compare it lexically or by numeric suffix. The canonical source/workflow determines legal successors, and identity for one point must not be reused across its lifecycle. Record:

- **source_revision**;
- a tombstone's **deleted_source_revision**;
- expected-current source revision;
- delete-event ID or fence;
- published pointer.

Example rules:

- Writer A reads r7 and publishes candidate r8 with **expected=r7**. After it succeeds, every writer that still submits **expected=r7** fails CAS.
- A delete writes a tombstone only when expected current state matches, and persists the deleted source identity and delete event.
- A tombstone rejects later upsert by default. Explicit resurrection matches the old source/delete fence and uses a different new source identity.
- Different vector, payload, or hash under one revision enters a conflict queue.
- ACL revision can change independently but must not regress.
- Queries read only the published revision.

These rules remain meaningful during replica recovery, replay, and shard transfer. But retaining only the current source and current tombstone cannot stop ABA: in **r1 → delete → r2 → delete → r1**, a very old **delete(r1, d1)** can match again. Production needs an unreusable generation, monotonic row/store version, or permanent history fence. An append-only lifecycle/audit log must preserve history even after resurrection removes a current tombstone.

## Read-your-writes

After a user uploads a document, they may need to search it immediately. Options include:

- wait for the required write acknowledgement and searchable state;
- send a minimum revision or fence with the query;
- route a session temporarily to a confirmed replica;
- merge a small recent-write buffer until indexing is visible;
- show “processing” in the UI and open search only after completion.

Do not replace state and timeout behavior with **sleep for five seconds**. Record an operation/event ID and trace it from write acknowledgement to a search canary.

Multiple repository/store instances in one process can also hold different snapshots. “One process” does not mean “one instance.” If a read path cannot prove that a local snapshot revision is current, reload a consistent snapshot or fail closed, as this course's toy project does. After a delete or ACL tightening, a stale instance must not return an old point. Summary and no-op paths must not report a stale cache as current success either.

## Shard-key trade-offs

### Random or hashed point ID

The benefit is even distribution. The cost is that a tenant query may fan out to every shard.

### Tenant ID

Tenant queries route directly and isolation is intuitive. A large tenant can become a hotspot or exceed one shard.

### Tenant group or composite key

Large tenants can be split into buckets and long-tail tenants grouped. Routing and rebalancing become more complex.

Choose from:

- tenant size and growth tail;
- whether queries cross tenants;
- filter combinations;
- hotspots and concurrency;
- one-shard capacity and index construction;
- resharding ability and downtime cost;
- data residency.

A key that is even today may not suit two years of growth. Monitor points, bytes, QPS, P99, writes, and index size by shard, with resharding thresholds.

## Scaling and shard transfer

Scaling is not “add a node and it becomes faster.” Confirm:

- whether a new node receives shards automatically;
- whether rebalancing is manual or automatic;
- whether transfer copies records or snapshots/indexes;
- whether the target rebuilds ANN or quantization;
- how writes queue or replay during transfer;
- cutover ordering;
- peak disk and network use;
- failure rollback;
- whether all unique shards moved before downscaling.

Current Qdrant documentation lists several shard-transfer methods with different index, ordering, and resource characteristics. Recheck the actual version and rehearse it.

## Replica health and degradation

Monitor:

- active, partial, and dead replicas;
- replication lag;
- write-acknowledgement failures;
- under-replicated shards;
- leader or consensus changes;
- partial query failure;
- rebuild/optimization backlog;
- disk high-water mark;
- anomalous top-k result count.

Define failure behavior:

- whether a partial result is allowed;
- whether to fall back to exact, keyword, or cache;
- whether writes are rejected;
- whether data with possibly stale permissions is withdrawn;
- how callers are informed instead of receiving a false complete success.

Permission and deletion paths normally should not return uncertain stale data for availability.

## Failure tests

| Scenario | Verify |
| --- | --- |
| One replica stops | Read/write availability, acknowledgement level, and alerting |
| Network partition | Which side accepts writes and how conflicts resolve after recovery |
| Two writers both update from r7 | The first CAS succeeds; the other write with expected=r7 conflicts explicitly |
| Delete fence and late upsert | Tombstone rejects resurrection by default; only explicit resurrection matching the fence can enter a next version |
| Query from stale store instance after ACL/delete | Check snapshot revision before reading; reload or fail closed rather than returning old ACL/point |
| Source identity reused across lifecycles | A generation/history ledger detects ABA; an old event cannot succeed just because identity becomes equal again |
| Writes during shard transfer | No missing/duplicate points or old ACL |
| New index build | Searchable lag and fallback behavior |
| Disk full | Write failure is explicit and old state remains intact |
| Coordinator timeout | Partial result is not presented as complete |
| Restoring an old snapshot | Deletion log and new revisions replay |

Use test data and isolated environments. Do not casually stop production nodes.

## Common mistakes and diagnosis

- **Treating replicas as backup:** add independent snapshots, recovery, and accidental-deletion protection.
- **Treating defaults as business guarantees:** map write/read/ordering choices to scenario tests.
- **Using last-write-wins for concurrency:** source revision and tombstones establish business recency.
- **Treating opaque identity as reusable:** the canonical source prevents reuse and a generation/history fence prevents ABA.
- **Ignoring stale reads because there is one process:** multiple instances still cache snapshots. Search, summary, and no-op all validate revision.
- **Hot tenants after tenant sharding:** split buckets or use dedicated shard/collection.
- **Adding nodes with no capacity change:** shards were not transferred or rebalanced.
- **Returning 200 after some shards time out:** define partial response and upstream degradation.
- **Sleeping to test visibility:** use operation ID and revision canary.
- **Preferring availability during permission change:** fail closed on uncertain old ACL.

## Practice

1. Write end-to-end acceptance for “searchable within 30 seconds after upload, with latest revision only.”
2. Draw query fan-out and merge for four shards times two replicas.
3. Without comparing revision-string size, design rules for two writers based on r7 plus a delete event bound to current state; add an identity-reuse ABA counterexample.
4. Compare tenant and random shard keys under long-tail tenants for hotspots and fan-out.
5. Write capacity, write, query, and rollback observations for a shard-transfer rehearsal.
6. Define read/write degradation and security boundaries when one replica is unavailable.

## Mastery check

- [ ] I distinguish shard capacity/parallelism from replica availability.
- [ ] Replication does not replace backup.
- [ ] I state business semantics using revision, time, and SLO instead of consistency labels alone.
- [ ] Database ordering and expected-current source CAS jointly prevent out-of-order overwrite; opaque revisions are never ordered by string comparison.
- [ ] Source identity cannot be reused across a lifecycle, and generation/history ledgers protect against ABA caused by current-state-only checks.
- [ ] Read-your-writes uses state or fences, not fixed sleeps.
- [ ] A stale instance validates snapshot revision before search, summary, or no-op; uncertain permission/deletion state fails closed.
- [ ] Shard keys reflect queries, growth, hotspots, residency, and resharding capability.
- [ ] Scaling includes shard-transfer, rebuild, and rebalance verification.
- [ ] Failure behavior never disguises partial or old-permission data as success.

## Summary and next step

Replicas improve availability but replicate logical error too. Real disaster recovery needs independent snapshots, retention, and rehearsal. Next: [[vector-databases/06-backup-recovery-and-migration|Backup, recovery, and migration]].

## References

- [Qdrant: Distributed deployment](https://qdrant.tech/documentation/scaling/distributed_deployment/)
- [Qdrant: Points](https://qdrant.tech/documentation/manage-data/points/)
- [PostgreSQL: High Availability, Load Balancing, and Replication](https://www.postgresql.org/docs/current/high-availability.html)
- [[knowledge-base-construction/00-index|Knowledge Base Construction]]

Sources were retrieved on 2026-07-22. Return to the [[vector-databases/00-index|Vector Databases index]].

