---
title: "Query Processing and Filtering"
tags:
  - ai-agent-engineer
  - semantic-search
  - query-processing
aliases:
  - Query processing and secure filtering
  - Query Processing
source_checked: 2026-07-22
source_baseline: "Sentence Transformers and Qdrant official documentation, and
  DPR/BEIR papers, through 2026-07-22"
lang: en
translation_key: 语义搜索/05-Query处理与过滤.md
translation_source_hash: 5d84c51654cab9d47b465aa067a220b8ae5e582c74b374528f13f6ff93bc37b4
translation_route: zh-CN/语义搜索/05-Query处理与过滤
translation_default_route: zh-CN/语义搜索/05-Query处理与过滤
---

# Query Processing and Filtering

## Learning objective

Turn a user input containing typos, references, time, and authorization into a replayable retrieval plan, while ensuring no rewrite or fallback can cross tenant/ACL boundaries. Afterward, you can draw a query pipeline, separate hard constraints from optional enhancements, and set versions, timeouts, and fallbacks for each step.

## A secure query flow

```text
authenticated identity + original query + trusted conversation state
        ↓
minimum Unicode/case normalization
        ↓
identify language, intent, entities, time, and exact identifiers
        ↓
construct non-relaxable tenant / ACL / status / effective-time filters
        ↓
optional: alias expansion, rewriting, decomposition, multiple queries
        ↓
parallel BM25 / dense / other-route recall
        ↓
fusion, deduplication, budget, and explainable logging
```

Identity and hard filters must be established before rewriting and passed to every route. Neither an LLM nor user text can override trusted tenant/groups.

## Minimum normalization

Safe starting transformations include:

- Unicode NFKC or a project-defined normalization;
- English case and whitespace normalization;
- retaining the original query;
- recognizing error codes, model numbers, URLs, amounts, dates, and versions;
- tokenizing through the locked analyzer.

Do not blindly delete punctuation, numbers, or stop words. Negation in “do not renew,” the version in “Python 2,” and the value in “1.5%” can change intent. Both pre- and post-normalization text must be replayable.

## Aliases, spelling, and domain expansion

A stable domain dictionary can add synonymous wording such as VPN and virtual private network as extra queries, but it should:

- retain dictionary version and trigger terms;
- distinguish exact replacement from OR expansion;
- prevent candidate explosion when one abbreviation maps to several domains;
- preserve an original-term route for exact identifiers such as error codes, accounts, and order numbers;
- validate with hard negatives that expansion does not spill into neighboring products.

Use spelling correction as an additional candidate or explicit prompt, rather than silently replacing the original query. “Correcting” an error code into an ordinary word is particularly dangerous.

## Conversational references and time

“Is that refund rule from last time still valid?” needs at least:

1. resolving what “that” refers to from trusted conversation state, rather than asking a model to guess;
2. converting now to an explicit time zone and timestamp;
3. making `effective_from`/`effective_to` filters;
4. retaining the original query and completed retrieval query;
5. requesting clarification when context is missing rather than searching every refund document.

When time filtering is a hard condition, high similarity cannot override it. If the index has not synchronized the latest revision, return a “data may be stale” state rather than silently using expired material.

## The boundary of LLM rewriting

An LLM can create paraphrase queries, expand abbreviations, or split complex questions, but it is a dynamic component that can fail:

- it may alter negation, numbers, entities, and authorization;
- it may generate terms absent from the corpus;
- instructions in user text can induce it to change retrieval scope;
- network/model timeouts increase tail latency;
- model upgrades alter rewrite distributions.

Engineering requirements:

- the original query always has an independent route or fallback;
- every rewrite has prompt/model/revision, parent query, duration, and checksum;
- limit total query count, tokens, concurrency, candidates, and timeout;
- treat query text as data and never execute tool/system instructions within it;
- replay original-only and rewritten baselines offline;
- enforce the safety filter as an outer conjunction around every rewrite.

## Multiple queries and decomposition

“VPN will not connect and I am not receiving verification codes” may be split into two subproblems. Each new route adds latency and noise, so record:

- subquery ID and parent query;
- recall channels and contributing documents per route;
- merge/deduplication rules;
- total candidate and per-original limits;
- whether partial results, retry, or whole-request failure occurs when one route fails.

For multi-hop questions, distinguish “requires two pieces of evidence” from “two independent questions.” Qrels can label evidence groups; ordinary Recall@k may be insufficient when it measures only one document.

## Construct hard filters from trusted context

Common hard filters:

- `tenant_id` / `organization_id`;
- ACL groups or subject IDs;
- `status=published`;
- effective time;
- data-residency, legal-retention, and deletion state.

Common business filters:

- language, product, and `document_type`;
- region, version, and price range;
- a category expressly chosen by the user.

A client can propose business preferences, but the server must derive tenant/ACL from an authenticated session and schema-validate allowed fields, types, ranges, and combinations. Empty groups, unknown fields, or parsing failures must fail closed.

## Filters must constrain candidates before scoring

Taking global top-k and removing unauthorized documents afterward causes:

- unauthorized content may already enter cache, traces, or downstream models;
- fewer than k items remain afterward, while authorized documents cannot fill the gap;
- scores/ranks can leak that another tenant has content;
- recall collapses under high-selectivity filters.

Whether a database uses pre-filtering, filter-aware ANN, expanded candidates, or exact fallback depends on product and parameters. Regardless of execution plan, the final candidate set must not exceed authorization. The current Qdrant filtering/hybrid API is a verifiable example, not universal database semantics.

## Failure states and fallbacks

| Failure | Example correct action | Prohibited action |
| --- | --- | --- |
| Rewrite timeout | Retrieve with the original query | Relax ACL |
| No subject groups | Return empty/authorization error | Treat as a public user |
| Filter-schema error | Reject and record the request | Ignore unknown fields |
| Dense service failure | Mark fallback to BM25 | Pretend a dense empty result is normal |
| Index revision lags | Return freshness state / clearly mark old version | Claim it is current |
| Partial multi-query failure | Mark partial and retain successful routes | Retry endlessly |

## Observability and privacy

For replay, record query ID, version, filter field names/summaries, channel, duration, candidate ID/rank, fallback reason, and trace ID. Do not put complete private queries, raw text, identity tokens, or entire ACLs in ordinary logs; use minimization, de-identification, access control, and retention periods.

At a minimum, monitor by slice:

- gain/fallback rate of original-only versus rewriting;
- analyzer/dictionary/model revision;
- query type, language, tenant size, and filter selectivity;
- no-result, partial, timeout, and unauthorized gates;
- candidate contribution per route and p95/p99.

## Common failures and diagnosis

- **A rewrite replaces the original query:** retain an independent original route.
- **An LLM changes a number or negation:** extract structured invariants and validate them.
- **The user may send `tenant_id`:** override from authenticated identity server-side.
- **Overly strict filters are cancelled automatically:** return the explicit no-result reason and never relax safety conditions.
- **Synonym expansion explodes candidates:** limit mappings, query count, and total budget.
- **A cache key omits ACL/revision:** include an identity-authorization summary and version.
- **Logs contain sensitive queries/credentials:** minimize, de-identify, and restrict access.

## Exercise

Turn “Is that refund rule from last time still valid?” into a retrieval plan:

1. List fields that must come from the conversation.
2. Write the original query, completed query, and possible clarification question.
3. Define tenant/ACL/status/effective-time filters.
4. Explain fallbacks for rewrite timeout, time-parsing failure, and an outdated index.
5. Design a cache key without recording real credentials.
6. Construct five negation/number hard negatives and three authorization tests.

## Mastery checklist

- [ ] The original query and every rewrite are traceable.
- [ ] Tenant/ACL comes from a trusted identity, not user or model text.
- [ ] Numbers, time, negation, and identifiers have invariant checks.
- [ ] Every dynamic step has a version, timeout, budget, and fallback.
- [ ] Empty authorization, unknown filters, and parsing anomalies fail closed.
- [ ] Logs are sufficient for replay without exposing complete sensitive data.

Next: [[semantic-search/06-recall-and-offline-evaluation|Recall and Offline Evaluation]].

## References

- Karpukhin et al., [Dense Passage Retrieval](https://arxiv.org/abs/2004.04906)
- Thakur et al., [BEIR](https://arxiv.org/abs/2104.08663)
- [Sentence Transformers: Semantic Search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)
- [Qdrant: Filtering](https://qdrant.tech/documentation/search/filtering/)
- [Qdrant: Hybrid and Multi-Stage Queries](https://qdrant.tech/documentation/search/hybrid-queries/)

Sources were obtained on 2026-07-22. Return to the [[semantic-search/00-index|Semantic Search index]].

