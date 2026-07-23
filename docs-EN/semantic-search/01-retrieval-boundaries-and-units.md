---
title: "Retrieval Boundaries and Units"
tags:
  - ai-agent-engineer
  - semantic-search
  - information-retrieval
aliases:
  - Retrieval task definition
  - Retrieval Unit
source_checked: 2026-07-14
source_baseline: "MS MARCO, DPR, and BEIR original papers through 2026-07-14"
lang: en
translation_key: 语义搜索/01-边界与检索单元.md
translation_source_hash: 4e1a49087f516d282161009befced01ba2622663ca0b9b2ed3516a9d985b4877
translation_route: zh-CN/语义搜索/01-边界与检索单元
translation_default_route: zh-CN/语义搜索/01-边界与检索单元
---

# Retrieval Boundaries and Units

## Learning objective

Before selecting an embedding, database, or framework, define the basic objects of a retrieval experiment: the user’s information need, query, documents/passages, relevance judgments, visibility, and first-stage candidates. After this lesson, you should be able to write a one-page retrieval-task specification that does not depend on a particular product.

## A user’s words are not the information need

The user input “why has my refund not arrived?” may require all of the following:

1. Recognizing that the user asks about refund-arrival time rather than how to request a refund.
2. Knowing when the order was approved, its payment channel, and the current time.
3. Retrieving general timing guidance, the status-check entry point, and exceptional-escalation conditions.
4. Reading only orders and knowledge documents that this user is authorized to access.

The raw string is the original query. Context completion, alias expansion, or decomposition may create one or more retrieval queries. Every rewrite must retain its relationship to the original input, conversation state, version, and time; otherwise the system cannot replay why it searched those words.

## Five basic objects

| Object | Definition | Minimum metadata |
| --- | --- | --- |
| information need | The task the user truly wants to complete | Intent, time point, cost of error |
| query | One executable, replayable retrieval request | ID, original/rewrite, identity, filters, version |
| document/passages | Retrieval units that can be returned and judged | Stable ID, source span/revision, authorization, status |
| qrels | Query-document relevance judgments | Grade, annotation guideline, annotator/adjudication version |
| ranking | Candidates arranged by a channel under rules | Channel, rank, score, parameters, time |

Qrels are relevance judgments, not an access-control table. An internal runbook may be highly relevant to a question but unavailable to a visitor. It can appear in qrels for controlled audit or a platform-employee query, but cannot be an online candidate for a visitor. An evaluation fixture should ensure that every positive document satisfies the query’s tenant, ACL, status, and business filters. Validate security boundaries separately with `must_not_return` or equivalent gates.

## The document unit must match production

If production returns chunks, qrels should judge chunks rather than only an entire PDF. Otherwise, “the paper is relevant overall, but the returned passage lacks the answer” becomes a false positive. A retrieval unit needs at least:

- a stable `document_id`/`chunk_id`;
- original path, page/paragraph or character span;
- source revision and content hash;
- title, hierarchy, and necessary local context;
- tenant, ACL, status, language, product, and validity period;
- representation revision.

An overly long document dilutes answers and increases downstream cost. An overly short one loses subjects and conditions. Boundary design belongs to [[chunking-strategies/00-index|Chunking Strategies]]; this course uses qrels to verify whether those units are retrievable.

## Relevance is not “contains the keyword”

Define grades 0–3 from the task:

| Grade | Meaning | Example |
| --- | --- | --- |
| 3 | Directly answers the primary need with correct conditions and version | States the current refund-arrival time explicitly |
| 2 | Supplies necessary evidence but must be combined with another passage | Explains approval-completion time but not channel differences |
| 1 | Topically related but cannot solve the need independently | Only explains how to initiate a refund |
| 0 | Irrelevant, outdated, contradictory, or for the wrong object | Return-shipping rules |

The rules must say whether time, version, language, source trustworthiness, and mere mention count as relevance. Resolve annotator conflicts through adjudication and retain the guideline version; do not quietly rewrite disagreement as agreement.

## Unjudged does not mean irrelevant

Large corpora cannot be judged exhaustively. If you judge only the old system’s top-k, useful documents discovered by a new system will be falsely counted as negatives. A common approach is pooling: collect the first several results from several candidate systems, randomize system origin, annotate together, then add hard negatives and online-failure samples.

Report qrels coverage and the composition of the judgment pool with metrics. External benchmark qrels help compare general capability, but cannot substitute for your language, authorization, timeliness, and business definition.

## The responsibility of first-stage recall

The first stage aims to put documents that are “possibly relevant and authorized” into a candidate window at acceptable cost:

```text
trusted identity + original query + system context
        ↓
query processing and hard filtering
        ↓
BM25 / dense / other recall
        ↓
fusion, deduplication, candidate budget
        ↓
reranker or direct return
```

It need not put the best evidence first every time, but downstream components must be able to see it. If a relevant document is absent from the candidates, neither [[reranking/00-index|Reranking]] nor [[rag/00-index|RAG]] can bring it back.

## No-answer and refusal are formal samples

The query set must include:

- cases where the corpus truly has no answer;
- cases with relevant content that the current identity cannot access;
- content not yet published or past its validity period;
- temporary invisibility due to indexing delay;
- queries with mutually conflicting or unsatisfiable conditions.

“No results,” “unauthorized,” “system fault,” and “weakly related result” are distinct states. Do not disable ACLs or return arbitrary similar documents merely to reduce the no-result rate.

## Common failures and diagnosis

- **Titles indexed but body text missing:** inspect document content and source span.
- **Near-duplicate chunks fill top-k:** cap candidates per canonical document and measure evidence coverage.
- **Qrels judge only one positive:** pool results from multiple systems and revisit unjudged candidates.
- **Evaluate whole papers but return chunks online:** unify the judgment unit.
- **Every query is a literal keyword hit:** add paraphrases, colloquial phrasing, typos, and hard negatives.
- **Unauthorized documents treated as positives:** model relevance and eligibility separately.
- **Top-1 accuracy treated as all of recall:** state denominators for Hit@k, Recall@k, and ranking metrics.

## Exercise

Write a task specification for an “internal IT help center”:

1. Define query, document, and source span.
2. Write 0–3 relevance guidelines with one example each.
3. Create two queries each for VPN, error codes, accounts, no-answer cases, and visitor overreach.
4. Write trusted tenant/groups/filters for each query.
5. Explain how qrels will be pooled, blindly annotated, and adjudicated.
6. Define the first-stage candidate window and the condition for entering a reranker.

## Mastery checklist

- [ ] Original query, rewritten query, and information need are explicitly distinct.
- [ ] The unit returned online matches the qrels judgment unit.
- [ ] Every document is traceable to a source revision/span and authorization state.
- [ ] Qrels permit multiple positives and graded relevance.
- [ ] No-answer, unauthorized, failure, and weak relevance are modeled separately.
- [ ] The first stage aims for high-recall candidates rather than pretending to complete the final answer.

Next: [[semantic-search/02-query-and-document-representations|Query and Document Representations]].

## References

- Nguyen et al., [MS MARCO](https://arxiv.org/abs/1611.09268)
- Karpukhin et al., [Dense Passage Retrieval](https://arxiv.org/abs/2004.04906)
- Thakur et al., [BEIR](https://arxiv.org/abs/2104.08663)

Sources were obtained on 2026-07-14. Return to the [[semantic-search/00-index|Semantic Search index]].

