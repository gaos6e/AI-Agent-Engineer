---
title: "Duplicates and Entity Identity"
tags:
  - ai-agent-engineer
  - data-quality
aliases:
  - Deduplication
  - Data deduplication
source_checked: 2026-07-22
source_baseline:
  - pandas 3.0 duplicate-data documentation
lang: en
translation_key: 数据清洗/03-重复数据与实体身份.md
translation_source_hash: f6bb33a246158b1e8e91e293698056b3df921c19e4255923cdc6bce0f91d5e3c
translation_route: zh-CN/数据清洗/03-重复数据与实体身份
translation_default_route: zh-CN/数据清洗/03-重复数据与实体身份
---

# Duplicates and Entity Identity

## Objective

Distinguish duplicate imports, conflicting records for one entity, genuine retries, and semantic near-duplicates. Ensure that deduplication rules retain identity, provenance, authorization, and traceable relationships.

## Three kinds of duplicates

- **Exact duplicates**: every field is the same, often because of a duplicate import.
- **Conflicting records for one entity**: the primary key is the same but fields differ, possibly because of an update, retry, or corruption.
- **Semantic near-duplicates**: lightly edited text, cropped screenshots, or different versions of one document; whole-row equality cannot find these.

Define the entity and event before deduplicating. Two identical requests may be a real user retry or a collector replay. Deleting them blindly changes failure-rate and traffic statistics.

## Keys and idempotency

A stable primary key identifies the same entity; an event ID identifies the same occurrence. When an external API retries, the write side should use an idempotency key, then the cleaning side can use the event ID to identify replay.

When a primary-key conflict appears, do not stop at “keep the last one.” First establish that the ordering field is reliable and time-zone-aware, then record the replaced version, selection rule, and number of conflicts.

Also define in advance whether an ID that first appears in an invalid row occupies that identity. This course's project chooses that it does: a later row with the same ID enters the duplicate report even if its own fields are valid. That avoids silently rewriting history with later-arriving data. Other systems can choose differently, but must put the choice in their contract and tests.

## Text and RAG deduplication

Content hashes can detect exact duplicate documents. Near-duplicates can use n-gram/Jaccard or embedding candidates, followed by human review. Document deduplication must retain provenance and authorization: identical content under different access controls cannot be replaced with a single public copy.

Split data by original document or entity; otherwise chunks from the same content can cross train and test boundaries and leak.

## Same-source relationships, authorization, and revocation

“Content can be merged” does not mean “provenance can disappear.” Even if one normalized content object saves storage, retain every **source_id**, version, **access_scope**, retention status, and merge mapping. Without them, you cannot answer who authorized a passage, who can see it, or which version produced it. For a frozen evaluation, **group_id** should come from an explainable source entity such as a document, session, incident, code repository, or time window, and must be fixed before labels, model scores, or future outcomes are observed.

If cleaned samples enter an evaluation or benchmark, freeze an explicit **group_id → family_id** mapping. **group_id** marks the upstream entity or same-source boundary; **family_id** marks the evaluation case's anti-leakage group. They can map one-to-one or many-to-one, but must not be generated ad hoc from labels, model output, or random row numbers. Follow the terminology and split rules in [[evaluation-framework/foundations-and-design/02-cases-datasets-and-stratification|Cases, datasets, and stratification]] and [[benchmark-design/foundations-and-design/03-data-splits-leakage-and-contamination|Data splits, leakage, and contamination]].

When a source correction, deletion, or authorization revocation arrives, deleting one row from the current table is not enough. Use lineage to find derivative normalized records, chunks, indexes or embeddings, caches, training or evaluation splits, quality reports, and public downloads. Stop new consumption first, then rebuild, withdraw, or mark outputs invalid under the release policy. A hash can locate byte content; it cannot replace the source-to-derivative artifact mapping.

## Validation questions

- How do row count, entity count, and label distribution change before and after deduplication?
- Can each removed record be traced to its retained record?
- Are same-ID conflicts reported separately?
- Does a sudden duplicate-rate increase reveal an upstream retry storm?

## Exercise

Design **run_id**, **call_id**, **attempt**, and **idempotency_key** for tool-call logs. Explain how a second attempt at one call is counted in task-success, call-volume, and cost statistics.

## Mastery check

- [ ] I can define the distinct responsibilities of an entity key, event key, attempt number, and idempotency key.
- [ ] I do not merge documents with different authorization, provenance, or versions merely because their content hashes match.
- [ ] I can report before/after row count, entity count, label distribution, and the retained-to-removed mapping.
- [ ] I split by entity or original document to prevent near-duplicates from crossing training and test data.
- [ ] I can list every derivative artifact that needs review for a source revocation rather than deleting only one row from the final table.

Next: [[data-cleaning/04-outliers-and-range-rules|Outliers and range rules]].

## References

Sources were checked on 2026-07-22.

- [pandas DataFrame.duplicated](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.duplicated.html)
- [pandas: Duplicate Labels](https://pandas.pydata.org/docs/user_guide/duplicates.html)
