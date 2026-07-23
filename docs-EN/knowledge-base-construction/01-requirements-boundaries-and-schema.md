---
title: "Requirements, Boundaries, and Schema"
tags:
  - ai-agent-engineer
  - knowledge-base
  - schema
aliases:
  - Knowledge Base Schema
source_checked: 2026-07-22
source_baseline:
  - JSON Schema draft 2020-12
  - W3C PROV-DM Recommendation
lang: en
translation_key: 知识库构建/01-需求边界与Schema.md
translation_source_hash: d89432deac82f3cd9819c1dee69a9e1927c9864e6504d4c99ceaf5ad0360d868
translation_route: zh-CN/知识库构建/01-需求边界与Schema
translation_default_route: zh-CN/知识库构建/01-需求边界与Schema
---

# Requirements, Boundaries, and Schema

## Goal of this lesson

Define a knowledge base from user questions and risk boundaries rather than from fields in a particular vector database. Establish stable identities, a canonical/derived separation, version axes, and an evolvable source-record contract.

## Start by writing down who uses it for what

An employee-policy assistant, code search, a research-evidence library, and a customer-support knowledge base may all use RAG, but their standards of correctness differ entirely. At a minimum, answer the following:

| Dimension | Question to ask | Acceptable output |
| --- | --- | --- |
| Users and tenants | Who asks questions? Are tenants isolated? | Subject/tenant model and unauthorized-access cases |
| Questions | Which questions are frequent, long-tail, or unanswerable? | Representative queries and a refusal set |
| Sources | Which systems and directories are authorized? | Source allowlist and owner |
| Timeliness | How quickly must an update become visible? | Freshness/propagation SLO |
| Evidence | Does a citation point to a document, page, or table cell? | Provenance and location contract |
| Authorization | Under what conditions may a candidate enter retrieval? | ACL/ABAC attributes and tests |
| Deletion | How do source deletion, revocation, and expiry propagate? | Tombstones, confirmation, and retention policy |
| Quality | Which failures must block publication? | Layered metrics, thresholds, and a gold set |

“Higher accuracy is better” is not an acceptance criterion. Write an observable objective instead, such as “within five minutes of confirmed source deletion, the item must not appear in any online candidate set.” Concrete values must follow business risk and capability, not be copied in without context.

## Four layers of objects

1. **Raw source**: the original file or API response, source version, license, and acquisition evidence.
2. **Canonical revision**: the authoritative revision under a stable business ID, including permissions and source state.
3. **Derived artifacts**: parsed elements, chunks, embeddings, and keyword or graph-index records.
4. **Published view**: the version pointer and authorization projection that queries can actually see.

Canonical data is the basis for reconstruction; indexes are acceleration projections. A raw source may require stricter storage permissions. “Canonical” does not mean retain it forever: deletion and retention rules still apply.

W3C PROV-DM uses entities, activities, agents, and derivations to express what entity was produced through what activity and by whom. In a knowledge base, source files and revisions can be entities; ingestion, parsing, and chunking can be activities; and a connector or responsible team can be an agent. Chunks and embeddings are derived entities. Adopting these concepts does not require RDF.

## Keep identity and versions separate

- `document_id`: the stable identity of a business object, for example `policy:leave`.
- `source_sequence`: an order supplied by one connector for that object; this course uses integers for teaching.
- `source_version`: an ETag, revision, or business version from the source system.
- `revision_number`: the revision sequence in the canonical store.
- `pipeline_version`: the version of parsing, normalization, chunking, and related configuration.
- `model/index version`: the embedding model and index schema.
- `run_id`: one processing run; it is not a content version.

Titles, paths, and URLs can change, so they are poor permanent IDs on their own. A hash identifies content state, but identical content under different tenants or ACLs must not be merged casually.

## Source-record contract

```json
{
  "tenant_id": "tenant-a",
  "document_id": "policy:leave",
  "source_sequence": 7,
  "source_uri": "https://kb.example.invalid/policy/leave",
  "source_version": "v3",
  "content": "The leave policy requires submission two days in advance.",
  "allowed_groups": ["employees"]
}
```

The corresponding [[knowledge-base-construction/examples/source-record.schema.json|source-record JSON Schema]] defines required fields, types, lengths, uniqueness of groups, and `additionalProperties: false`. A schema is not the whole business rule set, however. JSON Schema’s `maxLength` counts characters, not UTF-8 bytes, so the project uses `x-maxUtf8Bytes` as a descriptive annotation and enforces the actual byte limit in application code. A validator may ignore an unknown custom keyword; writing it in a schema is not proof that it executes.

> [!warning] A flat `allowed_groups` list is not the authorization source of truth
>
> The example’s `allowed_groups` is teaching input that has already been resolved upstream. It can test only whether subsequent revisions and projections remain consistent. A real connector must also retain a recomputable permission snapshot, source scope and owner, authorization decision or policy revision, observation time, and failure state. A successful schema validation does not prove that the caller actually has permission to read the source.

## Schema evolution

Every schema should declare a dialect and version, then define:

- how old consumers handle a newly added optional field;
- the migration window for changes to required fields or enumerations;
- whether unknown fields are rejected, retained, or ignored;
- whether old and new data coexist, and how they are backfilled and rolled back;
- which changes require only local derived artifacts to be recomputed and which require a full rebuild; and
- a compatibility matrix for schemas, transformers, and index readers/writers.

Do not rewrite all historical data in place and only then discover that readers are incompatible. Common approaches are dual-read/dual-write or a new-version projection, followed by validation and a published-pointer switch.

## The minimum fields, driven by requirements

For source and identity: tenant, document ID, source URI/ID, source version/sequence, and owner. For content and language: raw/content hash, title, language, and element relationships. For governance: ACL/attributes, classification, license, effective period, and retention/deletion state. For processing: schema/pipeline/model/index version, run ID, status, and warnings. For publication: current revision, published revision, publication time, and rollback pointer.

“Minimum” does not mean as few fields as possible. It means every field corresponds to a query, governance, replay, or acceptance requirement.

## Common mistakes and troubleshooting

- **Copying vector-store fields first**: storage limitations get mistaken for the business model.
- **One table for facts, task state, and the search index**: a failed update cannot distinguish current from published.
- **Using a path or title as a permanent key**: renames cause duplicates or deletion failures.
- **Storing only a content hash**: the system cannot explain source, ACL, pipeline, or model version.
- **Unversioned schemas**: the meaning of older records cannot be reproduced after an upgrade.
- **Deduplicating identical documents while ignoring tenant/ACL**: restricted content may be projected as public.

## Exercises

1. Write 15 queries, 3 no-answer cases, and 5 unauthorized-access cases for an internal-policy assistant.
2. Draw `document_id → revision → element → chunk → embedding → published projection`.
3. Add `effective_from` to a source schema, then explain how old data, readers, and indexes migrate.
4. Explain why `source_sequence=7` cannot automatically be compared with `7` from another connector.

## Self-check

- [ ] I can work backward from user tasks to source, citation granularity, authorization, and timeliness requirements.
- [ ] I can distinguish a business identity, source order, canonical revision, and run ID.
- [ ] I separate canonical data, derived artifacts, and the published view.
- [ ] I know that a JSON Schema annotation is not necessarily enforced by a validator.
- [ ] I can design compatibility, migration, and rollback for a schema change.

## References and next step

- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [W3C PROV-DM](https://www.w3.org/TR/prov-dm/)

Sources were retrieved on 2026-07-22. Next: [[knowledge-base-construction/02-ingestion-provenance-and-normalization|Ingestion, Provenance, and Normalization]].
