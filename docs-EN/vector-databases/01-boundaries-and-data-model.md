---
title: "Boundaries and the Data Model"
tags:
  - ai-agent-engineer
  - vector-database
  - data-modeling
aliases:
  - Vector Record Model
  - Vector Data Model
source_checked: 2026-07-22
source_baseline: "pgvector and the Qdrant Points and Overview documentation,
  checked through 2026-07-22"
lang: en
translation_key: 向量数据库/01-边界与数据模型.md
translation_source_hash: f11bee09462a6b641dd1f665a426540026c80d0ec1187ef57ec9718173b65442
translation_route: zh-CN/向量数据库/01-边界与数据模型
translation_default_route: zh-CN/向量数据库/01-边界与数据模型
---

# Boundaries and the Data Model

## Learning objectives

You will define the responsibility boundaries among a vector database, embeddings, search, and RAG; design a record containing a space contract, stable point ID, vector, provenance, permissions, status, and hash; and decide when to split collections versus use payload fields or partitions.

## Draw the system boundary first

A common data flow is:

```text
canonical document
  -> parse/chunk
  -> embedding adapter
  -> versioned point records
  -> vector database (filter + exact/ANN)
  -> search fusion/rerank
  -> RAG context + citations
```

Each layer has a distinct responsibility:

| Layer | Responsible for | Must not pretend to be responsible for |
| --- | --- | --- |
| Documents and chunking | source, structure, spans, ACLs, content hashes | vector similarity |
| Embeddings | roles, model/revision, dimensions, vectors | database storage and authorization |
| Vector database | schema, persistence, filtering, neighbors, CRUD, operations | deciding whether an answer is factually correct |
| Search and reranking | queries, fusion, candidate order, relevance evaluation | content generation |
| RAG | context, citations, answers, and abstention | repairing data lost upstream |

Copying source text into a payload can make a demo convenient, but it also expands the attack surface for disclosure, backup, and updates. A common security baseline is to store only the minimum retrievable metadata and a controlled text pointer in the vector store, then cite the canonical source. If full text must be stored, explicitly define its encryption, ACL, retention, and deletion scope.

## Define a space contract before creating a collection

Whatever a logical container is called—collection, index, table, or namespace—it should be bound to a contract such as:

```json
{
  "space_id": "ops-rag-v3",
  "model": "provider/model-id",
  "embedding_revision": "immutable-revision",
  "dimension": 1024,
  "metric": "cosine",
  "normalized": true,
  "dtype": "float32"
}
```

This remains valid JSON, so it has no legal trailing comments. `space_id` isolates the index space; `model` and `embedding_revision` fix the generating source; and `dimension`, `metric`, `normalized`, and `dtype` define the mathematical and storage contract for comparable vectors. Replace the placeholder strings and numbers with verified values; do not infer a model specification from this example.

The numbers above are schema examples, not model recommendations. Obtain actual values from the candidate cards in [[embeddings/00-index|Embeddings]].

Different models or revisions are not automatically compatible even when they have the same dimension. When the dimension, metric, normalization, dtype, or role policy changes, create a new `space_id` and migrate rather than mixing writes into the old index.

A contract signature can be the hash of normalized contract fields. Use it to:

- validate a collection at application startup;
- prevent a query vector from searching the wrong space;
- isolate caches and batch jobs;
- check snapshots and restores; and
- verify that a published alias targets the intended version.

## An auditable point

```json
{
  "id": "tenant-a:doc-17:chunk-03",
  "vector": [0.12, -0.08, 0.44],
  "payload": {
    "tenant_id": "tenant-a",
    "document_id": "doc-17",
    "chunk_id": "chunk-03",
    "source_revision": "rev-7",
    "content_sha256": "64-char-lowercase-hex",
    "embedding_revision": "immutable-revision",
    "acl": ["employees", "sre"],
    "status": "published",
    "section_path": ["runbook", "rollback"],
    "language": "zh"
  }
}
```

This is also valid JSON. The top-level `id` supports idempotent writes, deletion, and citation; `vector` must match the dimension in the preceding contract; and the payload's `tenant_id`, provenance/revision/hash, ACL, and `status` are the minimum fields for pre-query security filtering and lifecycle tracking. Presentation fields such as `section_path` and `language` do not replace authorization fields.

The example vector has only three dimensions for readability. A real vector's dimension must equal the collection contract.

Field responsibilities:

| Field | Purpose | Common mistake |
| --- | --- | --- |
| point ID | idempotent upsert, deletion, and citation | using an array position, so inserting earlier text shifts every later ID |
| tenant ID | hard isolation, filtering, shard routing | trusting an arbitrary tenant parameter supplied by the client |
| document/chunk ID | traceability to the canonical source | storing only a vector, making whole-document deletion impossible |
| source revision | prevents old and new text from being mixed | updating the vector while leaving stale payload data |
| content hash | reconciles whether the vector matches its current input | hashing display text rather than the actual embedding input |
| embedding revision | checks the space version | keeping only a dimension, with no model or revision |
| ACL | authorization before retrieval | removing unauthorized results only in the final UI |
| status | draft/published/archived lifecycle | allowing drafts and tombstones to remain searchable |
| section/language | filtering, explanation, and slice evaluation | type drift that destabilizes indexes and filters |

Metadata types must remain stable. If `acl` is sometimes a string and sometimes an array, filter semantics become unpredictable. Standardize time zones and formats for time fields. Whether a high-cardinality field gets a scalar index must follow the query distribution.

## ID design

A stable ID should:

- remain the same across retries and replays;
- not collide across tenants;
- map to its source and chunk;
- avoid exposing unnecessary sensitive information;
- support enumerating all points when a source is deleted; and
- not depend only on an ordinal position.

You can use a readable composite ID, or a content-derived/random ID with an explicit mapping. If a content hash is part of the ID, a text change creates a new ID and the process that removes the old ID must be reliable. If a stable chunk ID does not change with its text, the upsert path needs a source revision to prevent an out-of-order write from overwriting newer content.

Do not let a client assert that it may overwrite a particular point ID. The server should construct IDs and authorization from a trusted tenant/source mapping.

## A payload is a query schema, not a junk drawer

Before adding a field, answer:

1. Will it be used for filtering, sorting, presentation, audit, or deletion?
2. What are its type and allowed values?
3. Who produces it, and when is it updated?
4. Does it contain sensitive information?
5. Does it need a scalar index?
6. If old records lack the field, should behavior fail open or fail closed?
7. Is it included in migration and backup?

Frequently filtered fields may need a payload or scalar index. Infrequent, high-cardinality, or presentation-only fields may not. Every index increases write, disk, and maintenance cost.

## Choosing collections and partitions

### Cases that usually deserve separation

- Different dimensions, metrics, or embedding spaces.
- Regulatory hard isolation for tenants or regions.
- Completely different backup, retention, encryption, or access-control requirements.
- Independent scaling, SLOs, or lifecycles.
- High-risk experiments versus production releases.

### Cases that usually do not need one collection each

- Language, document type, or small-department labels.
- A large number of tiny tenants.
- A single filterable field.
- Using multiple collections to hide a confused schema.

Collection-per-tenant isolation is intuitive, but many small collections increase control-plane, backup, and operational cost. A shared collection with a tenant payload centralizes operations, but requires strict filtering and shard design. Dedicated vector stores may also offer partitions or custom sharding. The correct choice depends on the product version and tenant distribution; there is no universal numeric threshold.

## Multiple and sparse vectors

Some products support named dense vectors, sparse vectors, or multivectors on one point. They can represent:

- text and images for the same object;
- dense-plus-sparse hybrid retrieval;
- titles and bodies encoded separately; or
- multiple granularities of representation.

Sharing a point does not mean vectors from different spaces can be dotted together. Each vector field still needs its own contract, dimension, metric, and query path. Keep deletion, ACLs, and source revision coherent across representations so that one representation is not updated alone.

## Source of truth and derived indexes

Treat the canonical source and chunk registry as reconstructible facts, and the vector index as versioned derived data:

- a source update emits an outbox event;
- an embedding job encodes a fixed revision;
- the vector write includes the source/input hash;
- the completed index is reconciled;
- the published alias switches; and
- deletion events propagate to every active space.

If the vector database is the only place that stores payload, ACL, or deletion mappings, disaster recovery and migration become harder. The revision/outbox pattern in [[knowledge-base-construction/00-index|Knowledge Base Construction]] can provide the upstream chain of facts.

## Schema gates

Before a write, verify:

- an exact contract-signature match;
- a valid point ID that cannot move across tenants;
- compliant vector dimension, finite values, and nonzero/normalized state;
- all required payload fields with stable types;
- source and embedding revisions consistent with the job;
- a nonempty ACL and an allowed status;
- a content hash of the actual embedding input; and
- no simultaneous point and tombstone.

Before a query, check again that the query vector belongs to the same space.

## Common failures and investigation

- **One collection contains every model:** inventory contracts and create isolated spaces.
- **Only vectors and text are stored:** tenant/filter/version/deletion operations become impossible.
- **Payload accepts arbitrary JSON:** field types drift and filtering/indexing becomes unstable.
- **IDs are chunk ordinals:** inserting source text causes widespread meaningless rewrites.
- **Full text is copied into logs or snapshots:** the sensitive surface expands; return to minimum metadata plus a source pointer.
- **Drafts are searchable:** the status filter is absent or fails open.
- **Named vectors update out of sync:** add a source revision and representation-integrity reconciliation.

## Exercises

1. Design a contract and point schema for a multi-tenant internal FAQ. List required and optional fields.
2. Compare a composite ID with a random ID plus mapping for deletion, migration, and privacy.
3. Decide which fields need scalar indexes: tenant, ACL, language, content hash, title, and creation time.
4. Write separate space contracts for text and image named vectors, and state which payload fields they must share.
5. Design a bad record whose vector belongs to a new model while the payload still names an old embedding revision. Write the gate that rejects it.
6. Choose a fail-closed migration strategy for historical records without an ACL.

## Mastery check

- [ ] I can explain the boundaries among a vector store, embeddings, search, and RAG.
- [ ] A collection has a complete, hashable space contract.
- [ ] A point traces to source/chunk/revision/hash and carries tenant/ACL/status.
- [ ] Metadata fields have stable types, origins, update rules, and indexing rules.
- [ ] Different spaces or hard-isolation domains do not share one query path.
- [ ] Named or multivectors are versioned independently; coexistence does not imply compatibility.
- [ ] A canonical source can rebuild the index, so the vector database is not an isolated source of truth.

## Summary and next step

The data model first guarantees that comparisons occur in the right space and that records are authorized and traceable. Next, decide how to find neighbors faster: [[vector-databases/02-distance-exact-search-and-ann-indexes|Distance, exact search, and ANN indexes]].

## References

- [Qdrant: Overview](https://qdrant.tech/documentation/overview/)
- [Qdrant: Points](https://qdrant.tech/documentation/manage-data/points/)
- [pgvector official repository](https://github.com/pgvector/pgvector)
- [[embeddings/00-index|Embeddings]]

Sources checked on 2026-07-22. Return to [[vector-databases/00-index|Vector Databases]].
