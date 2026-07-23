---
title: "Overlap, Metadata, and Context"
tags:
  - ai-agent-engineer
  - chunking
  - metadata
  - security
aliases:
  - Chunk Overlap
  - Chunk Metadata
source_checked: 2026-07-14
source_baseline: Unstructured, Azure AI Search, and Anthropic official material
  checked through 2026-07-14
lang: en
translation_key: Chunking策略/04-Overlap元数据与上下文.md
translation_source_hash: 718b054fb882d2990801472d742207113bcdcdd0231193b8b64e1a5f39a7c952
translation_route: zh-CN/Chunking策略/04-Overlap元数据与上下文
translation_default_route: zh-CN/Chunking策略/04-Overlap元数据与上下文
---

# Overlap, Metadata, and Context

## Learning objectives

You will understand that overlap solves only one class of problem near a boundary and be able to calculate its duplication cost. You will then establish a chunk contract that keeps source text, retrieval context, provenance positions, permissions, and versions separate.

## Overlap addresses boundary risk

Suppose a conditional sentence is cut exactly at a fixed-window boundary. Both chunks may lack complete evidence. Repeating the tail of the prior window in the next one increases the chance that at least one chunk covers the full condition.

It does not solve:

- a source that contains no answer;
- incorrect parsing order;
- a missing heading or table header;
- an embedding that does not fit the query;
- incorrect ACL filtering;
- a query that needs synthesis across distant sections.

When structural boundaries are clean, overlap can even carry the prior topic into the next topic. Unstructured currently applies overlap by default only to oversized elements that were hard-split; it also allows overlap on all chunks, while its documentation explicitly warns that this may have unexpected behavior. Treat that default as an implementation fact, not a universally optimal conclusion.

## Calculating duplication cost

For source length $L$, window size $S$, and overlap $O$, the stride is $S-O$. The most reliable calculation of actually duplicated units is:

$$
D=\sum_{i=1}^{N}\operatorname{units}(chunk_i)-L
$$

The duplication ratio is:

$$
R_{\text{dup}}=\frac{D}{L}
$$

Do not use `overlap / size` as a substitute for the actual duplication ratio: the last chunk can be short, and a structural strategy may overlap only a few oversized elements.

With the current default configuration, this course’s fixture has:

- a structure-aware strategy that uses overlap only for oversized elements, with a body duplication ratio of about 0.0319;
- fixed windows over continuous source content, with a body duplication ratio of about 0.0956.

These values describe only the local example. They do not prove that structural chunking is always cheaper or more accurate on other data.

## Duplicate retrieval and context deduplication

Highly similar neighboring chunks can fill top-*k*. A common processing order is:

1. filter by permissions and metadata;
2. retrieve candidates;
3. rerank;
4. merge or deduplicate by source, parent, or overlapping spans;
5. pack context within the model budget.

Do not deduplicate only by string similarity. Two chunks can have similar text but different sources, versions, or ACLs and must not be merged; neighboring spans from the same source can be joined, but each segment’s provenance and match score must remain. When several children point to one parent, usually expand that parent only once.

## Source text and retrieval text must be separate

At minimum, distinguish:

- `text`: citable body text obtained from canonical source spans;
- `retrieval_text`: text used for lexical retrieval or embedding, which can add a heading path, table header, entity names, or controlled context;
- `display/citation`: content reconstructed from source and spans for final display;
- `generated context`: model-generated derived explanation, recorded separately with its generation method and version.

For example:

```text
text:
production | 4 | SRE

retrieval_text:
Heading path: Deployment Guide > Environment Matrix
Table header: Environment | Replica count | Approval
production | 4 | SRE
```

Only the first portion may be treated as the original table row in a citation; the heading and table header should be presented using their own source spans. Store `content_sha256` and `retrieval_sha256` separately so you can tell which input version a vector represents.

Anthropic’s Contextual Retrieval is one approach that generates chunk-specific context. It may improve particular retrieval tasks, but generated content is still derived data; retain the original text, model and prompt versions, failure policy, and rebuild capability.

## Minimum metadata set

| Category | Recommended fields | Purpose |
| --- | --- | --- |
| Identity | `chunk_id`, `strategy_version`, `ordinal` | Deduplication, ordering, migration |
| Source | `source_id`, `source_revision`, `element_spans` | Citation, update, deletion |
| Structure | `section_path`, `family`, `language` | Explanation, filtering, specialized strategy |
| Security | `tenant_id`, `acl`, `classification` | Authorization before retrieval |
| Integrity | `content_sha256`, `retrieval_sha256` | Detect stale vectors and content drift |
| Vectors | `embedding_model`, `embedding_version`, `dimensions` | Compatibility checks and rebuilding |
| Lifecycle | `created_at`, `published_revision`, `tombstone` | Audit, cutover, deletion |

More fields are not automatically better. Each needs a type, source, and update rule; filter fields in particular must not sometimes be strings and sometimes arrays.

## ACLs must take effect before retrieval

If you retrieve first and remove unauthorized chunks only at display time, vector scores, logs, or model context may already have leaked information. A safe baseline is:

1. the query carries a tenant and subject groups;
2. the database or retrieval layer applies fail-closed filtering first;
3. only authorized candidates are scored or returned;
4. parent expansion and neighboring-chunk merging validate again;
5. a chunk with a missing ACL never enters the published index.

The course project filters by ACL before term-overlap scoring and includes a test that an employee query for the `production` table returns nothing. It demonstrates only OR-group semantics; a real authorization model needs separate definitions for users, groups, tenants, inheritance, and deny rules.

## Stable IDs and versions

Using only `source_id + ordinal` makes all later IDs change when a paragraph is inserted near the start of a document. A content-derived ID can include:

- source ID and source revision;
- strategy version;
- element IDs and half-open unit intervals;
- content hash;
- ACL or tenant boundary.

Whether a retrieval-context hash belongs in a chunk ID depends on the identity definition. If the body is unchanged but a heading prefix changes and vectors must be regenerated, you may retain the chunk ID while updating `retrieval_sha256` and the embedding revision; alternatively, you may create a new ID. Both choices are valid, but the indexing layer needs one non-optional invalidation rule:

```text
index_entry_id = H(chunk_id + retrieval_sha256
                   + index_revision + acl_snapshot_sha256)
```

Therefore, even if the application keeps `chunk_id`, a changed heading path, table header, or generative retrieval context creates a new `index_entry_id`. A changed index version or ACL snapshot likewise cannot reuse an old record. Separating the identity of the body from the identity of an index record supports both stable citations and deterministic rebuilding. The course project tests all four bindings as well as heading and table-header changes; [[rag/09-project-offline-provenance-from-source-to-citation|the RAG source-to-citation evidence chain]] continues from this identity into publication generations and citations.

`ordinal` must still be stored to recover reading order, but it does not participate in this course example’s ID identity. The tests insert an unrelated source before the existing one and verify that old chunk IDs remain unchanged.

## Incremental updates and deletion

When a source revision changes:

1. parse the new revision and generate candidate chunks;
2. validate coverage, ACLs, hard maxima, and hashes;
3. recompute vectors only for chunks with a changed `retrieval_sha256`;
4. finish retrieval evaluation in a shadow or pending-publication version;
5. atomically switch the published pointer;
6. retain the old version for a short rollback window;
7. propagate deletion requests through tombstones or purge jobs to chunks, vectors, caches, and backup policy.

Do not delete the old index first and slowly build the new one: the intermediate state will be missing content. The revision/outbox/published-pointer pattern in [[knowledge-base-construction/00-index|Knowledge Base Construction]] can support this lifecycle.

## Common mistakes and diagnosis

- **Defaulting to 20% overlap**: there is no stated boundary assumption or comparison with `O=0`.
- **Retrieved results are nearly identical**: inspect neighboring-span overlap and top-*k* diversity.
- **Writing a heading into the body**: the citation represents derived context as original text.
- **Only the parent has an ACL**: child vectors can already match an unauthorized query.
- **Content changed but the vector did not**: retrieval hash and model-version reconciliation are missing.
- **The strategy name was not upgraded**: one name produces different boundaries, so the experiment cannot be replayed.
- **Old chunks remain searchable after source deletion**: the lifecycle does not cover the index, cache, or published pointer.

## Exercises

1. With $L=10{,}000,S=1{,}000$, calculate the window intervals, total body units, and actual duplication ratio for `O=0` and `O=200`.
2. Design `text` and `retrieval_text` for a table row, listing the source span for every line.
3. Design the ID and vector-update rule for “the heading is renamed, the body is unchanged,” and explain the choice.
4. Write three fail-closed tests: a missing ACL, a changed ACL, and different parent/child ACLs.
5. Give a stopping condition for overlap, for example, “evidence completeness improves too little while context duplication rises.”

## Mastery checklist

- [ ] I can calculate actual duplicated units and duplication ratio.
- [ ] I know overlap targets boundary evidence only; it is not a universal quality switch.
- [ ] I store source text, retrieval text, derived context, and their hashes separately.
- [ ] ACLs run before retrieval or scoring and are rechecked during parent expansion.
- [ ] Chunk ID, ordinal, revision, and embedding revision have distinct responsibilities.
- [ ] Index-entry identity binds the retrieval representation, index version, and ACL; a heading or table-header change alone invalidates the old index record.
- [ ] A strategy upgrade supports shadow rebuilding, reconciliation, atomic cutover, and rollback.

## Summary and next step

Chunking’s engineering quality is not determined by boundaries alone; it also depends on duplication cost, source traceability, permissions, and lifecycle. Next, put these contracts into a runnable experiment: [[chunking-strategies/05-retrieval-evaluation-and-chunking-project|Retrieval Evaluation and the Chunking Project]].

## References

- [Unstructured: Chunking](https://docs.unstructured.io/open-source/core-functionality/chunking)
- [Azure AI Search: Chunk documents](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-chunk-documents)
- [Anthropic: Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)

Sources checked on 2026-07-14. Return to [[chunking-strategies/00-index|the Chunking Strategies course index]].
