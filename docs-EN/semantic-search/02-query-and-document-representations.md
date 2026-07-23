---
title: "Query and Document Representations"
tags:
  - ai-agent-engineer
  - semantic-search
  - embedding
aliases:
  - Asymmetric retrieval representations
  - Asymmetric Retrieval
source_checked: 2026-07-14
source_baseline: "DPR, SPLADE, ColBERT original papers and Sentence Transformers
  official semantic-search documentation through 2026-07-14"
lang: en
translation_key: 语义搜索/02-Query与Document表示.md
translation_source_hash: e5b82b80d9fcb0893aa13e8bcd81eb32c8cfd3cef74efcb9f78de975e5c85d84
translation_route: zh-CN/语义搜索/02-Query与Document表示
translation_default_route: zh-CN/语义搜索/02-Query与Document表示
---

# Query and Document Representations

## Learning objective

The same text can become terms, sparse weights, one dense vector, or multiple token vectors. This lesson does not rush to choose a model. It first makes explicit what each representation keeps, what it loses, and which contracts query-side and document-side processing must share.

## Lexical representation starts with an analyzer

Keyword retrieval does not “compare raw strings directly.” An analyzer commonly performs Unicode/case normalization, tokenization, optional morphological processing, stop-word policy, and synonym policy, producing terms. Chinese, English, error codes, and model numbers require different decisions:

- Preserve identifiers such as E042 and RTX-5090 as whole units whenever possible.
- Chinese can start with characters, words, or n-grams, but granularity changes document frequency and noise.
- Amounts, dates, versions, and negation must not be casually removed.
- The query analyzer and index analyzer need not be identical, but their compatibility must be locked and tested.
- Analyzer changes alter the index and scores, usually requiring an index rebuild or a new index version.

BM25 consumes term frequency, the number of documents containing a term, and document length. Tokenization errors directly become recall errors; tuning BM25 parameters cannot compensate for them.

## Symmetric and asymmetric tasks

| Task | Query | Document | Interchangeable? |
| --- | --- | --- | --- |
| Similar questions | One question | Another question | Usually approximately symmetric |
| Paper similarity | Title and abstract | Title and abstract | Usually approximately symmetric |
| Question answering retrieval | Short question/keywords | A passage that can answer the question | Asymmetric |
| Product search | User wording | Title, attributes, description | Asymmetric |

Most RAG work retrieves a longer evidence passage for a short query, so it is asymmetric retrieval. Dense Passage Retrieval encodes queries and passages separately with dual encoders. They enter compatible comparison spaces, but their input roles and encoding paths must not be casually swapped.

The current Sentence Transformers documentation offers `encode_query` and `encode_document` entry points for asymmetric semantic search, and says that a model may use query/document prompts or task routing. This is a current library/model fact; other SDKs and models need their own model-card review, rather than copying function names.

## Dense representation contracts

Offline document encoding and online query encoding must jointly lock at least:

| Field | Why it is needed |
| --- | --- |
| model/provider/revision | Even a model with the same name can change weights or service behavior |
| query/document role | Determines prefix, prompt, or route |
| tokenizer and maximum length | Determines what content remains |
| input template | How title, path, body, and field labels are concatenated |
| truncation | Head/tail truncation, sliding window, or segmentation strategy |
| pooling | How token representations become one vector |
| dimension/dtype | Storage and computation contract |
| normalization | Determines the relationship between dot product and cosine |
| metric | Ranking direction for cosine, dot product, or L2 |
| language/domain | Training coverage does not equal local-task performance |

Checking dimension alone is insufficient: two 768-dimensional models can use entirely different coordinate systems. During migration, use a new space/collection, compare under dual reads, then explicitly switch; do not intermix old and new vectors.

## How to organize document input

A passage often needs its title or hierarchy to disambiguate its subject:

```text
title: Refund Rules
section: Arrival Time
content: After approval, refunds normally return through the original channel within one to three business days.
```

This is not a universal best template. Compare body-only, title + body, and path + title + body through ablation. Repeated site navigation, copyright notices, and boilerplate may dominate the representation, so clean them during parsing or chunking.

When a long document is truncated by a tokenizer, an answer near the end may never enter the vector. Record token count, truncation rate, and truncated fields. If the rate is high, adjust chunks first instead of assuming the model “understands the entire document.”

## How to organize query input

The query side should retain:

- the original query;
- the normalized version;
- every rewrite/subquery and its parent query;
- conversation fields, time, and identity used;
- query-encoder revision, input length, and whether it was truncated;
- timeouts, degradation, and cache hits.

Domain abbreviations can expand, but numbers, proper nouns, negation, and temporal conditions should remain intact. An LLM rewrite can turn “do not auto-renew” into “auto-renew,” so the original-query channel must run independently and serve as a fallback.

## Sparse, dense, and multi-vector representations

- **BM25/traditional sparse:** terms are interpretable and suit exact identifiers, but paraphrases may share no terms.
- **Learned sparse:** a model weights vocabulary dimensions, supporting semantic expansion with inverted-index structures; behavior still depends on training and vocabulary.
- **Single dense vector:** storage and retrieval are simple, but compressing a passage into one vector can lose local matches.
- **Multi-vector/late interaction:** retains multiple token/segment vectors and can express finer-grained interaction, but costs more to store, query, and rerank.

SPLADE is a research representative of learned sparse retrieval, and ColBERT of late interaction. They are advanced options, not automatically better merely because they are more complex. Start with BM25 and a single-vector baseline to locate failure types.

## The boundary of the toy fixture

The [[semantic-search/examples/semantic-search-fixture.json|project fixture]] uses hand-authored, seven-dimensional one-hot vectors: a human directly assigns dimensions for topics such as refunds, duplicate charges, uploads, and networks. It reliably demonstrates “lexical recall misses; dense retrieval hits” and RRF, but has no training, tokenizer, cross-language ability, or real generalization.

When migrating to a real model, replace:

1. hand-authored document/query vectors;
2. representation name/revision/dimension;
3. encoding batches and cache;
4. exact linear scanning;
5. all metrics rerun on real queries/qrels.

## Common failures and diagnosis

- **Query and document roles reversed:** inspect the model card and encoding-call logs.
- **Offline documents updated while online queries still use an old revision:** gate with a space signature.
- **Repeated titles make every vector similar:** run field ablation and inspect nearest neighbors.
- **Long text silently truncated:** record token count and truncation rate.
- **Language coverage inferred from a marketing page:** evaluate by language slice.
- **Model change evaluated only by cosine distribution:** rebuild qrels metrics; old scores are not directly comparable.

## Exercise

Design a representation protocol for retrieving a 300-word troubleshooting passage for “VPN cannot connect”:

1. Write query/document input templates.
2. State how the analyzer preserves VPN, error codes, and version numbers.
3. Define model revision, role, maximum length, truncation, normalization, and metric.
4. Compare body-only with title + body.
5. Construct five paraphrase queries and three numeric/negation hard negatives.
6. Write the dual-space switching and rollback conditions for a model upgrade.

## Mastery checklist

- [ ] Can decide whether a task is symmetric or asymmetric.
- [ ] Both the sparse analyzer and dense encoder have replayable versions.
- [ ] Query/document roles, templates, and truncation are not hidden defaults.
- [ ] Model compatibility is not judged by dimension alone.
- [ ] Understand the responsibility and cost differences among single-vector, learned-sparse, and late-interaction retrieval.
- [ ] Do not present toy vectors as real embedding results.

Next: [[semantic-search/03-similarity-scores-and-thresholds|Similarity, Scores, and Thresholds]].

## References

- Karpukhin et al., [Dense Passage Retrieval](https://arxiv.org/abs/2004.04906)
- Formal et al., [SPLADE v2](https://arxiv.org/abs/2109.10086)
- Khattab & Zaharia, [ColBERT](https://arxiv.org/abs/2004.12832)
- [Sentence Transformers: Semantic Search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)

Sources were obtained on 2026-07-14. Return to the [[semantic-search/00-index|Semantic Search index]].

