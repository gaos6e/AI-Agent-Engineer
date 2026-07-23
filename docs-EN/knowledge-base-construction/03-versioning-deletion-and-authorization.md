---
title: "Versioning, Deletion, and Authorization"
tags:
  - ai-agent-engineer
  - knowledge-base
  - governance
  - authorization
aliases:
  - Knowledge Lifecycle and Authorization
source_checked: 2026-07-22
source_baseline:
  - OWASP Authorization Cheat Sheet
  - NIST SP 800-162 update 2
  - SQLite transaction documentation retrieved 2026-07-22
lang: en
translation_key: 知识库构建/03-版本删除与权限.md
translation_source_hash: abdd76b793ea3ae175fc37640916b2cabe99b9c038ebd81dcd542b88cda7907f
translation_route: zh-CN/知识库构建/03-版本删除与权限
translation_default_route: zh-CN/知识库构建/03-版本删除与权限
---

# Versioning, Deletion, and Authorization

## Goal of this lesson

Use a current/published separation to make updates reversible. Make ACL tightening and deletion fail closed. Understand tombstones, soft deletion, content purging, cache and backup propagation, and the boundary of authorization-aware queries.

## Multiple version axes

A knowledge base commonly has all of the following at once:

- source revision/sequence: source content or authorization state;
- canonical revision: the authoritative revision stored by this knowledge base;
- schema/pipeline version: parsing, normalization, and chunking configuration;
- model/index version: the embedding model and retrieval-index structure;
- policy version: authorization, retention, and classification rules; and
- published generation: the combination currently read by online queries.

When content is unchanged but the pipeline is upgraded, recompute the affected derived artifacts; do not invent a source-content change. An ACL change must produce a traceable state change even when the content hash is unchanged.

## Current is not published

`current_revision_id` is the latest accepted canonical state. `published_revision_id` is the revision that online retrieval has projected completely and passed through its gates.

```text
source event → canonical current + outbox (one transaction)
             → build derived projections → accept → atomically switch published pointer
```

For a normal content update, a failed new projection can leave the old published revision serving until a retry succeeds and switches the pointer. Do not delete the old index first and slowly build the new one.

There are security exceptions to “keep serving the old version”:

- **ACL tightening**: the old projection may be visible to too many subjects, so set `access_blocked` immediately and lift it only after the new ACL projection succeeds.
- **Deletion/access revocation**: mark the canonical state deleted immediately, make queries fail closed, and remove projections in the background.
- **First publication/restoration after deletion**: there is no safe old version, so wait for the new projection to be fully published.

The course project uses these rules to distinguish availability from confidentiality, so “eventual consistency will recover” cannot become an excuse for a temporary disclosure.

## Tombstones and deletion propagation

A deletion may originate from a source object disappearing, permission revocation, a user request, retention expiry, a license change, or a governance decision. At a minimum, a tombstone records a document ID, source sequence, event version, reason category, run ID, and the propagation status of every downstream target. It prevents an old batch or full rescan from restoring the object accidentally.

The propagation inventory normally includes:

- canonical/current state and revision content;
- parsed elements, chunks, embeddings, and keyword/vector/graph indexes;
- query, answer, prompt, CDN, and other caches;
- failure queues, exports, and analytical copies; and
- backups, WAL/logs, and vendor-retention policies.

Soft deletion supports short-term rollback and audit, but it does not automatically meet a physical-deletion obligation. Setting a database field to `NULL` cannot prove that old pages, WAL, snapshots, and backups have been erased. This project’s `purge_deleted_canonical_content()` verifies only application-level propagation order. Real erasure needs evidence appropriate to storage media, backup cadence, and legal or organizational policy.

A hash can itself be personal data or a linkable identifier, so it must not be retained forever without conditions simply because it is “irreversible.”

## Authorize before candidate generation

OWASP authorization guidance emphasizes least privilege, deny by default, validating authorization on every request, and authorization testing. NIST SP 800-162 describes ABAC as evaluating policy using attributes of the subject, object, operation, and environment. Applied to retrieval:

1. The identity system authenticates the subject and supplies trustworthy tenant, group, and attribute data.
2. The query service uses those values as authorization context.
3. Tenant and ACL/ABAC filters run at the metadata, lexical, or vector candidate stage.
4. Only authorized candidates may enter reranking, prompts, logs, and caches.
5. A defensive check can run before returning a result, but it cannot replace filtering before candidate generation.

If a secret chunk is retrieved first and an LLM is later told not to reveal it, the unauthorized data has already entered processing, logs, or caches. An unreadable vector is not access control.

## ACL snapshots, inheritance, and caches

Permissions may come from tenant, site, folder, document, or row-level attributes. Store an executable snapshot on the revision while retaining the policy version and source relationship so it can be recomputed. Monitor the propagation SLO for permission changes separately from content freshness.

A snapshot must also answer when the decision was made, under which rule, and against which upstream authorization facts. Production records therefore usually need the observation time, effective period or synchronization watermark of an entitlement/ACL, the policy/connector version, and a decision reason. If upstream scope or parent permissions cannot be confirmed, block publication rather than reuse a stale allow result.

The cache key must include at least tenant, a subject-authorization summary, policy version, query, and retrieval configuration, and must be invalidated on a permission change. Do not give user B a cached candidate or answer for user A.

Even public content should normally use an explicit `public/everyone` policy rather than treating an empty ACL as public. Default-deny for an empty ACL is safer.

## Ordering, conflicts, and restoration

An old source event must not overwrite newer state. If the source supplies a monotonic sequence:

- a sequence below the known value is `stale_ignored`;
- the same sequence with the same state is an idempotent `noop`;
- the same sequence with different state is a conflict and is quarantined; and
- after deletion, only an explicit upsert with a higher sequence may restore the object.

If a real source does not guarantee a monotonic sequence, use conditional ETag writes, change-feed semantics, or a source-specific conflict policy. Do not mechanically transplant this project’s integer model.

## Common mistakes and troubleshooting

- **Only changing the `documents` table**: old chunks and embeddings can still be searched.
- **Equating deletion with `active=false`**: caches, projections, and backups have no propagation evidence.
- **Waiting for the next full scan to apply an ACL update**: the revocation window is too long.
- **Retrieving first and filtering at answer time**: unauthorized processing has already occurred.
- **Cache keys without authorization context**: reuse across subjects leaks results.
- **Treating SQLite `NULL` as physical erasure**: it ignores file pages, WAL, and backups.
- **Letting the latest write win for the same cursor**: source-protocol conflicts are hidden.

## Exercises

1. Draw states and confirmation signals for “becomes unsearchable immediately after an ACL revocation; all online projections propagate within five minutes.”
2. Define a deletion action and evidence of completion for canonical data, chunks, embeddings, the vector index, caches, logs, and backups.
3. Design a test matrix where a failed content update retains the old version but a failed ACL update blocks immediately.
4. Write one ABAC decision using tenant, group, classification, and effective time, then list eight rejection cases.

## Self-check

- [ ] I can distinguish current, published, and the pipeline/model/policy version axes.
- [ ] I know when to retain an old version and when I must fail closed.
- [ ] A deletion has a tombstone, propagation, reconciliation, and retention/purge evidence.
- [ ] Tenant and ACL checks run before candidate generation, and an empty authorization defaults to deny.
- [ ] I will not misrepresent clearing an application field as compliant physical erasure.

## References and next step

- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [NIST SP 800-162: ABAC](https://csrc.nist.gov/pubs/sp/800/162/upd2/final)
- [SQLite Transactions](https://www.sqlite.org/lang_transaction.html)

Sources were retrieved on 2026-07-22. Next: [[knowledge-base-construction/04-indexing-and-incremental-updates|Indexing and Incremental Updates]].
