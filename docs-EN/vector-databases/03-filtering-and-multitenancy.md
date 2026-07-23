---
title: "Filtering and Multitenancy"
tags:
  - ai-agent-engineer
  - vector-database
  - filtering
  - multitenancy
  - security
aliases:
  - Vector Search Filtering
  - Vector-store multitenancy
source_checked: 2026-07-22
source_baseline: "Qdrant Filtering/Multitenancy and pgvector official
  documentation, checked through 2026-07-22"
lang: en
translation_key: 向量数据库/03-过滤与多租户.md
translation_source_hash: e11f4fbe1ad9c0e0d37e018deb0cd9a26c74a4be4348e4140269b3b0c21044ba
translation_route: zh-CN/向量数据库/03-过滤与多租户
translation_default_route: zh-CN/向量数据库/03-过滤与多租户
---

# Filtering and Multitenancy

## Learning objectives

Make tenant, ACL, publication status, and business conditions part of the retrieval plan; understand the interaction between filter selectivity and ANN; compare a shared collection, partitions/custom shards, and collection-per-tenant; and write fail-closed authorization-escape tests.

## Why “take top-k, then remove results” is wrong

Suppose the ten globally most similar records all belong to other tenants. If you run global ANN top-10 first and remove them in application code, an authorized user may be left with zero results. Raising **k** to 100 still cannot prove that you found the true top-10 for that tenant.

Worse, an unauthorized record may already have:

- participated in vector scoring;
- appeared in a database response, trace, or debug log;
- influenced cache or reranking;
- been sent to a model and hidden only later in the UI.

An authorization filter must take effect fail-closed before candidate scoring or return. A final application-side check is defense in depth, not a remedy for a database-layer disclosure.

## Build filters from a trusted identity

The request path is:

1. The API verifies the user or service identity.
2. The server resolves tenant, user, groups, roles, and policy version.
3. The authorization module produces a mandatory predicate that cannot be relaxed.
4. A user business filter can only be ANDed with the mandatory predicate.
5. The service queries the database.
6. Parent expansion, cache, and citations are checked again.

Do not directly accept this client payload:

~~~json
{"tenant_id": "someone-else", "acl": ["admin"]}
~~~

It is deliberately a parseable counterexample of untrusted client input. Neither **tenant_id** nor **acl** may be written directly into a mandatory filter after client declaration. The server must derive both constraints from the authenticated principal and authorization policy.

A client may select “only this language,” but may not select its own tenant or elevate an ACL.

## Define ACL semantics explicitly

The simplest group-OR rule is:

$$
authorized(p,u)
=
p.tenant=u.tenant
\land
(p.acl\cap u.groups\ne\varnothing)
$$

A production policy may also include:

- user-specific grants;
- all-of group requirements;
- explicit-deny precedence;
- inheritance from a document or parent;
- time-bounded access;
- classification clearance;
- ABAC attribute conditions.

Write the Boolean semantics and priority order. Do not make separate services guess. An empty ACL, missing tenant, or identity-resolution failure must reject publication or query rather than make a record publicly visible.

When a user's groups change, retrieval must read the current authorization context. At minimum, a cache key contains the tenant and either the authorization-policy version or an invalidatable membership fingerprint. A query-text-only key reuses results across permission contexts.

## Business filters

Common fields are:

- **status = published**;
- language or document type;
- **valid_from / valid_to**;
- source or project;
- region or data residency;
- embedding or source revision;
- tags or department;
- numeric or date range.

Record mandatory security filters separately from user business filters. Logs may include field names, selectivity, and policy ID, but should not emit sensitive values by default.

## Selectivity and cardinality

- **Selectivity** is the fraction of candidates retained by a filter. One percent is stricter than eighty percent.
- **Cardinality** is the number of distinct values for a field. Tenant ID is normally high-cardinality; status is normally low-cardinality.

They affect:

- scalar/payload-index type and memory;
- whether a planner filters first or searches while filtering;
- whether ANN traversal can find enough candidates;
- shard routing and fan-out;
- tail latency.

Do not use a fixed high/low-cardinality threshold across products. Collect the actual distribution and benchmark it against the selected product's current index mechanisms.

## Filter indexes

A scalar or payload index for a frequent predicate can greatly reduce scanning, at the cost of:

- more indexes on writes and updates;
- disk and RAM;
- schema migration;
- waste on infrequent fields;
- no guarantee that multi-field combinations use one plan.

For every indexed field, record type, cardinality, query frequency, selectivity, and delete/update cost. String, keyword, full-text, numeric, datetime, and geographic fields have different semantics. Test casing and tokenization with real data.

## ANN and filter execution strategies

A product may:

- pre-filter and perform exact or ANN search in the subset;
- check a filter during traversal and continue expansion;
- run ANN first and post-filter;
- use iterative scan or oversampling when filtering yields too few results;
- route to a partition or shard, then search locally.

Each strategy behaves differently at low selectivity, under latency pressure, and when returning enough results. With pgvector, approximate indexes plus **WHERE** are governed by the PostgreSQL planner and index scan and currently offer iterative-scan capabilities. Qdrant has its own filtering and indexing strategies. The statement “filters are supported” does not establish quality or performance.

Tests should cover:

- every returned result satisfies the predicate;
- returned count;
- ANN recall relative to filter-exact top-k;
- P95 and P99;
- scan/candidate statistics when the product exposes them;
- filter combinations and missing-field behavior.

## Three multitenant layouts

### Shared collection plus tenant payload

Advantages:

- few collections;
- common indexes and backups;
- small tenants share resources;
- aggregation across an authorized scope is relatively direct.

Risks:

- every query must carry the correct tenant filter;
- large and small tenants compete for resources;
- filter-aware ANN and high-cardinality fields are pressured;
- a configuration error has a large blast radius.

### Collection per tenant

Advantages:

- hard logical isolation;
- independent lifecycle, backup, and SLO;
- a query cannot cross collections by construction.

Risks:

- control-plane, memory, snapshot, and upgrade cost for many small collections;
- complex cross-tenant administration;
- product-specific collection quotas or overhead;
- capacity fragmentation.

### Partition, custom shard, or routing

Route a tenant or tenant group to a specific partition or shard to reduce fan-out and provide resource isolation. The risks are hot or large tenant skew, difficult resharding, and product coupling.

A hybrid is common:

- isolate large or high-risk tenants;
- share long-tail small tenants;
- use a tenant group as the shard key;
- split hard residency domains across clusters.

Qdrant currently supplies multitenancy and custom-sharding guidance. Its capabilities, limits, and recommendations change by version and must not be copied as another product's architecture.

## Same content under different permissions

The same public template may occur in two tenants. If you retain one “shared vector,” authorization and source mapping must be explicit. Otherwise:

- deletion in one tenant can affect the other;
- a payload can express only one ACL;
- different source revisions can be deduplicated incorrectly;
- cache and results can leak.

The security baseline is for point identity to include a tenant or security domain, or to use a governed shared-content domain with explicit authorization. Do not deduplicate across tenants by content hash alone.

## Deletion and permission revocation

Permission revocation is more urgent than body-text updates:

1. Update the canonical ACL revision.
2. Update vector-store payload/filter or withdraw the point.
3. Make the read path fail closed.
4. Invalidate query, parent, and rerank caches.
5. Synchronize old embedding spaces.
6. Replay revocations after backup retention and recovery.
7. Audit and reconcile.

A database's successful update response does not mean every replica, cache, or old space becomes invisible immediately. The next three lessons cover lifecycle, consistency, and recovery.

## Authorization-escape test matrix

| Scenario | Fixture | Expected result |
| --- | --- | --- |
| Another tenant is more similar | unauthorized vector equals query | Never returned and never enters a visible score |
| Same tenant, wrong group | ACL=platform; user=employees | Not returned |
| Empty groups | identity resolution fails or returns an empty set | Empty result or request rejection |
| Missing ACL | historical bad record | Not published and not returned |
| Draft | status=draft | Not returned |
| Cache | same query, different groups | A more permissive result is not reused |
| Parent | visible child, parent contains invisible spans | Reject or trim, retaining provenance |
| Group revocation | membership changes before and after a query | Invisible after revocation |

Test the final UI, database response, trace, and downstream context, not a single layer alone.

## Common mistakes and diagnosis

- **Too few results after filtering:** inspect execution strategy, selectivity, oversampling or iterative scan, and the filter-exact baseline.
- **Occasional cross-tenant results:** the mandatory filter came from a client, the cache lacks authorization context, or parent expansion was not rechecked.
- **P99 spikes after a new filter:** a scalar index is missing, a combined plan changed, or fan-out increased.
- **Indexing every field:** writes and memory rise; return to query frequency and selectivity.
- **Deduplicating across tenants by content hash:** permission and deletion semantics disappear.
- **Treating an empty ACL as public:** fail closed during both ingestion and query.
- **Hotspots in a shared collection:** analyze tenant size and shard routing instead of only enlarging global resources.

## Practice

1. Write the Boolean predicate **tenant AND published AND (ACL intersects groups) AND valid-time**.
2. Design an authorization-escape test where an other-tenant vector exactly equals the query, and list every output layer to inspect.
3. Establish exact/ANN comparisons at 1%, 10%, and 80% selectivity.
4. Compare the three layouts for ten large tenants and 100,000 small tenants, then propose a hybrid.
5. Design a cache-key and invalidation strategy for group revocation.
6. Decide whether title, tenant, ACL, status, content hash, and timestamp deserve filter indexes, and state the evidence.

## Mastery check

- [ ] Tenant and ACL are derived from a trusted identity; a client cannot relax them.
- [ ] The mandatory security filter runs before scoring, and the application checks again.
- [ ] Missing ACL, empty groups, and identity failure all fail closed.
- [ ] I can explain the relationship among selectivity, cardinality, filter indexes, and ANN.
- [ ] A filter benchmark uses filter-exact ground truth.
- [ ] I choose multitenant layout using tenant distribution, isolation, backup, and operations.
- [ ] Cache, parents, old spaces, and recovery cannot bypass revocation.

## Summary and next step

Filtering makes candidates both visible and eligible. Data still arrives, changes, and disappears. Next, build a replayable lifecycle: [[vector-databases/04-writes-updates-deletes-and-versioning|Writes, updates, deletes, and versions]].

## References

- [Qdrant: Filtering](https://qdrant.tech/documentation/search/filtering/)
- [Qdrant: Multitenancy](https://qdrant.tech/documentation/manage-data/multitenancy/)
- [pgvector official repository](https://github.com/pgvector/pgvector)

Sources were retrieved on 2026-07-22. Return to the [[vector-databases/00-index|Vector Databases index]].
