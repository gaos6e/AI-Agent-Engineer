---
title: "Backup, Recovery, and Migration"
tags:
  - ai-agent-engineer
  - vector-database
  - backup
  - disaster-recovery
aliases:
  - Vector Database Backup
  - Vector-store disaster recovery
source_checked: 2026-07-22
source_baseline: "Qdrant Snapshots/Distributed Deployment and PostgreSQL Backup
  official documentation, checked through 2026-07-22"
lang: en
translation_key: 向量数据库/06-备份恢复与迁移.md
translation_source_hash: f1e14d290984a562cab6687de6617fda9992e3f0f22baad728312a69c83d0825
translation_route: zh-CN/向量数据库/06-备份恢复与迁移
translation_default_route: zh-CN/向量数据库/06-备份恢复与迁移
---

# Backup, Recovery, and Migration

## Learning objectives

Work backward from business RPO/RTO to backup scope; distinguish replicas, snapshots, backups, and canonical re-embedding; write encryption, retention, and integrity checklists; recover in isolation; and accept recovery only after IDs, ACLs, deletion, gold queries, and performance pass.

## Define RPO and RTO first

- **RPO (Recovery Point Objective):** the maximum amount of data time that may be lost, for example fifteen minutes.
- **RTO (Recovery Time Objective):** the maximum time from failure to an available service, for example two hours.

Also define:

- whether recovery means “the process starts” or meets query SLOs;
- whether vectors may be recomputed or the index must return quickly;
- whether deletion or ACL events may be lost;
- which tenants or regions have different objectives;
- how reads and writes degrade during recovery;
- whether the upstream canonical source remains available;
- whether model, revision, and SDK artifacts can still be obtained.

“Vectors can be recomputed” solves vector values only. It does not automatically restore stable IDs, payload/ACL, published alias, tombstones, index configuration, or deletion watermark.

## Do not confuse four capabilities

| Capability | Main purpose | Cannot solve alone |
| --- | --- | --- |
| Replica | Availability during node failure | Accidental deletion, logical corruption, ransomware, long-term retention |
| Snapshot | Point-in-time state for a product/scope | Alias/cluster configuration not included, cross-product compatibility |
| Backup | Independent retention and disaster recovery | Recoverability cannot be proven without rehearsal |
| Rebuild from canonical | Regenerate derived indexes | Unavailable model, cost/time, missing ACL or tombstone |

Production commonly combines all four: replicas for short failures, periodic backups/snapshots for disaster, and canonical/outbox records for rebuild and post-restore catch-up.

## Backup checklist

### Data and schema

- collection, table, or namespace;
- space contract: model/revision/dimension/metric/normalization/dtype;
- points and vectors;
- payload, tenant, ACL, and status;
- point/source/chunk mapping;
- tombstones and deletion watermark;
- scalar/payload/ANN-index configuration;
- named and sparse vectors.

### Control plane

- published alias or pointer;
- tenant/shard/partition mapping;
- access policies and service configuration;
- replication/shard topology, if the recovery path needs it;
- application/schema version;
- encryption/key reference;
- outbox/CDC checkpoint;
- restore/runbook version.

### Backup metadata

- backup or snapshot ID, creation time, source cluster/version;
- covered shards, nodes, and collections;
- logical/physical and full/incremental status;
- checksum and manifest;
- size and object count;
- encryption, location, retention, and immutability;
- latest successful restore test.

## Verify product snapshot scope

As of 2026-07-22, Qdrant documentation states that a collection snapshot contains a given node's configuration, points, and payload for that collection. A distributed deployment must handle nodes separately, and collection aliases are not included in that snapshot. Qdrant Cloud backup and self-hosted snapshots are different capabilities.

Therefore, after downloading a snapshot, still ask:

- Which node or shard produced it?
- Is the whole collection covered?
- Are aliases stored separately?
- Are index and quantization included?
- How are incremental writes caught up?
- What version-compatibility range applies?
- Is restore into an existing or new collection?
- How are security credentials and encryption handled?

pgvector relies on PostgreSQL data files, WAL, and logical-backup mechanisms, so its recovery semantics differ. Design only from current official manuals for the selected deployment.

## Establish a consistent backup point

While writes continue, snapshots of multiple shards or collections can represent different times. If the business requires point, ACL, alias, and source revision to be coherent, use:

- an identifiable snapshot watermark;
- a short write pause or staging switch;
- a database transaction or consistent snapshot;
- a WAL or CDC checkpoint;
- outbox replay after recovery;
- final reconciliation.

Do not call independently created files an atomic all-database snapshot unless the product explicitly guarantees it.

## Security and retention

Vectors and payloads can contain sensitive derived information. Backups need:

- encryption in transit and at rest;
- management separation between keys and backups;
- least privilege, audit, and periodic permission review;
- region and data-residency controls;
- immutable or deletion-resistant policy when the threat model requires it;
- explicit retention, expiry, and legal hold;
- network isolation for the restore environment;
- no credentials, document bodies, or full vectors in ordinary logs.

Deletion requests and immutable backup conflict. Record a deletion ledger for deleted IDs/tenants, replay it after recovery and before queries open, and destroy expired old backups under policy. Legal and compliance conclusions require legal/governance review.

## Recovery is more than a process starting

After restoring in isolation, validate by layer.

### Mechanical integrity

- manifest and checksum;
- collection/schema/contract signature;
- point ID set, or partition count plus hash;
- required payload fields;
- sampled or full dimension, finiteness, and norm;
- aliases and routing;
- tombstones and deletion watermark;
- scalar and ANN index readiness.

### Security

- an other-tenant vector identical to the query is not returned;
- empty ACL/groups fail closed;
- group-revoked and deleted points do not resurrect;
- service credentials are least privilege;
- the restore environment has no public exposure.

### Quality

- exact and ANN canaries;
- gold-query Recall, MRR, and nDCG;
- filter-selectivity slices;
- new/old revision shows published only;
- score and tie rules match.

### Performance and operations

- cold start and index load/rebuild;
- P95/P99 and QPS;
- writes and deletion;
- replication/shard health;
- actual RPO loss;
- total RTO from incident start to accepted verification.

Restore traffic only after every gate passes.

## Catch up after recovery

Events exist after snapshot time **T**. The flow is:

1. Restore state at T.
2. Validate contract and watermark.
3. Replay upsert, delete, and ACL events from outbox/WAL/CDC checkpoint.
4. Reject stale out-of-order events by source revision.
5. Reconcile canonical IDs, hashes, and ACLs.
6. Replay the deletion ledger.
7. Build or await indexes.
8. Run security and quality canaries.
9. Atomically switch traffic.

Without a reliable event log, perform full canonical reconciliation/rebuild and include it in RTO.

## Cross-product migration

Internal ANN graphs, segments, and WAL are normally incompatible. A safer process:

1. Freeze source contract and logical schema.
2. Export canonical logical records—ID, vector, payload, revision—or recompute from canonical.
3. Create a new target schema/index.
4. Validate type, dimension, metric, and filters.
5. Import and reconcile.
6. Run the same queries against source and target.
7. Compare exact/ANN, filtering, security, and latency.
8. Shadow or dual-read.
9. Atomically switch alias/configuration.
10. Reclaim only after a rollback window.

If metric or API score direction differs, verify ranking on a small fixture first. Do not copy internal index files and assume compatibility.

## Recovery rehearsal

Rehearse on a risk-appropriate schedule rather than for the first time during an incident:

| Stage | Record |
| --- | --- |
| Trigger | Assumed failure, owner, start time |
| Acquire | Backup ID, checksum, permissions, version |
| Restore | Isolated environment, commands, duration, errors |
| Catch up | Watermark, event count, deletion ledger |
| Validate | Inventory, security, gold queries, performance |
| Decide | RPO/RTO satisfaction and blockers |
| Improve | Runbook, automation, next date |

Use de-identified or controlled data. If a production backup is used, the recovery environment must meet equivalent security requirements.

## Common mistakes and diagnosis

- **Replicas mean no backup is needed:** accidental deletion replicates too.
- **A snapshot file exists, so recovery succeeded:** execute isolated restore and gates.
- **Only vectors are backed up:** ACL, ID, alias, tombstone, and configuration are lost.
- **Only one distributed node is snapshotted:** check shard/node coverage.
- **Deleted data returns after recovery:** deletion watermark/ledger was not replayed.
- **Index files are copied across products:** use logical export or canonical rebuild.
- **RTO counts decompression only:** include index readiness, catch-up, validation, and traffic cutover.
- **Backup access is broad:** separate least-privilege access, encryption, audit, and restore isolation.
- **A model was retired and cannot re-embed:** retain a licensing/model-artifact/revision plan or accept migration.

## Practice

1. Design replicas plus backup plus outbox for an internal RAG system with 15-minute RPO and two-hour RTO.
2. Using Qdrant's current snapshot scope, state how aliases, other nodes/shards, and catch-up events are covered.
3. Write a restore checklist with at least five security gates and five quality gates.
4. Simulate replay order after restoring an old snapshot containing delete-r9 and upsert-r8.
5. Design logical migration and rollback from pgvector to a dedicated vector database.
6. Explain why “vectors can be recomputed from original text” can still fail RTO.

## Mastery check

- [ ] I can define and measure RPO/RTO.
- [ ] I distinguish replica, snapshot, backup, and canonical rebuild.
- [ ] A backup includes data, schema, ACL, alias, tombstone, watermark, and configuration.
- [ ] I verify a product snapshot's version-specific scope instead of guessing from its name.
- [ ] Recovery validates inventory, security, quality, and performance in isolation.
- [ ] Events and deletion ledger replay before queries reopen.
- [ ] Cross-product migration uses logical records or recomputation, not assumed internal-index compatibility.
- [ ] Backups have encryption, access controls, retention, and regular rehearsal.

## Summary and next step

Only after understanding failure and recovery do you have enough evidence for product selection. Next, compare candidates using target data, SLOs, filtering, and operating capability: [[vector-databases/07-selection-and-benchmarking|Selection and benchmarking]].

## References

- [Qdrant: Snapshots](https://qdrant.tech/documentation/snapshots/)
- [Qdrant: Distributed deployment](https://qdrant.tech/documentation/scaling/distributed_deployment/)
- [PostgreSQL: Backup and Restore](https://www.postgresql.org/docs/current/backup.html)

Sources were retrieved on 2026-07-22. Return to the [[vector-databases/00-index|Vector Databases index]].

