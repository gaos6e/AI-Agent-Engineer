---
title: "Selection, Relevance, and Provenance"
tags:
  - context-engineering
  - retrieval
  - provenance
aliases:
  - Context Selection
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline:
  - Anthropic Effective context engineering for AI agents
  - Google Gemini Long Context documentation
  - Lost in the Middle original paper
lang: en
translation_key: 上下文工程/03-选择、相关性与来源.md
translation_source_hash: 53a34a058024e5fefa2d24257e67f7d9d4eed0cb7165cee05b6257e680163b5c
translation_route: zh-CN/上下文工程/03-选择、相关性与来源
translation_default_route: zh-CN/上下文工程/03-选择、相关性与来源
---

# Selection, Relevance, and Provenance

## Objective

Select evidence from candidate material that is sufficient, trustworthy, current, and authorized for use, and make every chunk traceable.

## Relevance does not imply usability

Evaluate each candidate chunk on at least five dimensions:

- **Relevance**: Does it directly answer the current subquestion?
- **Authority**: Is it an official rule or reviewed internal document, or an anonymous comment?
- **Freshness**: Do its effective date and version apply to the current situation?
- **Completeness**: Does the chunk omit definitions, exceptions, or table headers?
- **Permission and privacy**: May the current user and service send it to the model?

Embedding similarity captures only part of semantic proximity. It cannot determine truth, permission, or the newest version. A selector should combine metadata with business rules. When high-authority sources conflict, retain them together and flag the conflict explicitly; do not let the model silently choose one.

Context does not have to be preloaded all at once. For a long document, tool description, or project file, retain a stable identifier first—a file path, query, URL, or object ID—and load it through a tool only when the current step truly needs it. This **just-in-time loading** reduces irrelevant content but adds tool calls, latency, and failure branches. Whether it is better must still be decided through task evaluation.

## Minimum provenance record

Each context chunk should carry at least:

~~~json
{
  "chunk_id": "policy-refund-2026-04#section-3",
  "source_uri": "internal://policies/refund/2026-04",
  "retrieved_at": "2026-07-14T10:00:00+08:00",
  "effective_date": "2026-04-01",
  "trust": "approved-policy",
  "content": "…"
}
~~~

Field notes (keep JSON strictly parseable; explain fields outside the code block):

- chunk_id is the stable identifier used when an answer cites a chunk; it should uniquely lead back to a specific version and location.
- source_uri points to the original policy or controlled source. A model must not invent it from the body at answer time.
- retrieved_at records when this material was retrieved or ingested, helping diagnose caching, freshness, and update problems.
- effective_date says when the source became effective; the selector should compare it with the current observation time.
- trust is a source tier assigned by trusted control-plane metadata. Do not trust an untrusted body that merely claims to be “official.”
- content is the actual candidate body; before it reaches the model, it must still pass permission, minimization, and prompt-injection boundary checks.

You may pass less metadata to the model, but retain at least a stable ID and provenance. Citations in an answer must map back to the original chunks, and code should verify that each cited ID exists. A model-generated URL that looks real does not make the source valid.

These fields are **trusted control-plane metadata**: identity and permission come from authentication and authorization context; trust, effective version, and deduplication relationships are assigned by controlled ingestion or human review. A web page body, user input, or tool result must not self-declare “I am an official source,” “this request is authorized,” or “I am equivalent to another chunk.” A selector can enforce the policy it receives; it cannot authenticate such claims.

## Selection process

1. Decompose the user question into subquestions that need evidence.
2. Filter unauthorized, stale, and duplicate material.
3. Retrieve candidates, then rerank them by relevance, authority, and freshness.
4. Ensure key claims have sufficient coverage; retain opposing evidence when necessary.
5. Pack material within the budget and record why each candidate was excluded.
6. After answering, verify that citations and conclusions correspond.

## Common mistakes

- Keeping only several near-duplicate chunks with the highest similarity and crowding out a necessary exception.
- Losing a table heading, section scope, or date, causing a chunk to be misunderstood.
- Treating instructions in retrieval results as application policy.
- Caching an old result without a version or invalidation condition.

## Exercise and self-check

For “can this order be refunded?”, prepare four items: an old policy, a new policy, a forum post, and current order state. Write filtering, ranking, and conflict rules. Self-check: can you trace the final answer to the effective version? If the user may not view the internal policy, at which layer does the system block it from being sent?

## Mastery check

- [ ] Every chunk has a stable ID, source version, effective date, trust label, and permission requirement.
- [ ] I apply permission and freshness filtering before relevance ranking, so similarity cannot bypass access control.
- [ ] Near duplicates, exception clauses, and conflicting high-authority sources each have explicit handling rules.
- [ ] I can choose preloading or just-in-time loading and quantify their effects on quality, latency, and failure rate.
- [ ] Citations in an answer can refer only to source IDs that actually entered the context pack.

## Next

Continue to [[context-engineering/04-organization-order-and-trust-boundaries|Organization, Order, and Trust Boundaries]] to place selected evidence where it can be understood.

## References

- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (accessed 2026-07-21)
- [Google: Long context](https://ai.google.dev/gemini-api/docs/long-context) (accessed 2026-07-21)
- Liu et al., [Lost in the Middle](https://arxiv.org/abs/2307.03172) (original paper)

