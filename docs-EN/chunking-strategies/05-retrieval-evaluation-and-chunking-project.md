---
title: "Retrieval Evaluation and the Chunking Project"
tags:
  - ai-agent-engineer
  - chunking
  - retrieval-evaluation
  - project
aliases:
  - Chunking Evaluation Project
  - Chunking Lab
source_checked: 2026-07-22
source_baseline: Python 3.11 standard-library offline experiment; fixture and 32
  unittest cases verified on 2026-07-22 in normal and -O modes with -W error
execution_verified: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: Chunking策略/05-检索评测与切分项目.md
translation_source_hash: 3589f381fe70599c602a340cf95b0bf18c7fecbb890bfc82195b2d295e43d21c
translation_route: zh-CN/Chunking策略/05-检索评测与切分项目
translation_default_route: zh-CN/Chunking策略/05-检索评测与切分项目
---

# Retrieval Evaluation and the Chunking Project

## Project goal

You will compare two chunking strategies without concluding from “this looks more natural”:

- `structured`: never crosses source, revision, ACL, section, or content family; merges complete short elements first; uses overlap windows for oversized single elements; table rows may receive retrieval-only header context.
- `fixed_window`: groups only by source, revision, and ACL, then uses fixed lexical-unit windows that may cross sections as a simple baseline.

Both use the same corpus, queries, lexical retriever, ACL filter, `k=3`, and provenance anchors. This makes the main difference attributable to chunking.

> [!warning] Generalization boundary
> The project does not call a tokenizer, embedding model, vector database, reranker, or LLM. Term-overlap retrieval verifies the data flow and evaluation logic only; it cannot establish production quality for real RAG.

## Project files

- [[chunking-strategies/examples/chunking_lab.py|chunking_lab.py]]: input validation, two splitters, retrieval, evaluation, and cost reporting;
- [[chunking-strategies/examples/corpus.json|corpus.json]]: nine elements covering paragraphs, code blocks, table headers, table rows, two ACLs, and one oversized paragraph;
- [[chunking-strategies/examples/queries.json|queries.json]]: seven answerable queries and two unanswerable or unauthorized queries;
- [[chunking-strategies/examples/test_chunking_lab.py|test_chunking_lab.py]]: 32 standard-library `unittest` cases.

All JSON uses UTF-8 and contains no credentials; the script uses strict field sets and rejects duplicate keys and non-finite numeric values.

## Why gold data anchors sources

If gold data directly stores `chunk_id`, changing size or strategy changes IDs and invalidates the evaluation set. This project writes each evidence anchor as:

```json
{
  "element_id": "api-e3",
  "quote": "Authentication failures must not be retried"
}
```

JSON cannot legally put comments at the end of every line. `element_id` points to a source element that does not change with the chunking strategy; `quote` is a unique evidence phrase in that element and is converted to a unit interval during loading. Keeping this block as pure JSON makes it directly copyable into `queries.json`.

At load time, the project verifies:

1. the element actually exists;
2. the quote occurs exactly once in that element;
3. the quote’s start and end align with lexical-unit boundaries;
4. the quote is converted to a half-open unit interval.

At evaluation time, a retrieved chunk is a hit when its element span completely covers that interval. The gold data therefore remains anchored to the stable source even after chunks are rebuilt.

Production data can also use character offsets, page or line positions, JSON Pointers, and source hashes. An exact quote is easy to audit manually, but repeated sentences need extra disambiguation.

## Run the experiment

From the project root (which contains `docs-CN/`, `docs-EN/`, and `.website/`), run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Prevent Python from writing __pycache__ so the teaching directory stays free of unrelated generated files.
python -B -W error '.\docs-EN\chunking-strategies\examples\chunking_lab.py'  # Run the offline experiment and surface every warning as an error.
```

The output is JSON containing:

- `unit_definition`: explicitly states that this is not a model tokenizer;
- `config`: hard max, overlap, and strategy version;
- `index_revision`: the implementation version of this lexical index;
- `cost`: chunk count, source/body/retrieval units, duplication ratio, and length distribution;
- `evaluation`: Recall@k, MRR, complete-evidence rate, no-answer accuracy, context units, and `retrieved_index_entry_ids` for every query.

As of 2026-07-22, the deterministic local-fixture summary is:

| Strategy | Chunks | Body duplication ratio | Mean retrieval-context units | Anchor Recall@3 | MRR | Complete-evidence rate | No-answer accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| structured | 7 | 0.0319 | 96.2222 | 1.0 | 1.0 | 1.0 | 1.0 |
| fixed_window | 6 | 0.0956 | 126.7778 | 1.0 | 1.0 | 1.0 | 1.0 |

Read this correctly: on these nine queries, both strategies hit every anchor; with the current retriever and `k`, the structure-aware strategy sends less average context. This does not establish that “structural chunking has higher recall,” nor can it be generalized to another corpus.

## Explain each metric

### Anchor Recall@k

If a query has $m$ source anchors and the top-*k* fully cover $h$ of them:

$$
\operatorname{AnchorRecall@k}=\frac{h}{m}
$$

It can reveal “one paragraph was found, but another required condition was missed.”

### Complete evidence case rate

Only when all anchors for one query appear in the top-*k* does that query receive 1. For multi-evidence answers, this is stricter than “at least one hit.”

### MRR

The project takes the rank $r$ of the first result covering any relevant anchor, records $1/r$, and averages it across queries. It measures how soon the first evidence appears, but does not ensure that later required evidence is present, so it must be read together with complete evidence.

### No-answer accuracy

The project’s no-answer cases require the retriever to return empty results. One case uses a nonexistent term, and the other tests ACL isolation. In real RAG, a system should also abstain when there is a lexical match but insufficient evidence, so 1.0 here proves only local retrieval behavior, not end-to-end abstention capability.

### Context cost

Sum the `retrieval_unit_count` for every chunk returned for a query. This is closer to relative downstream cost than chunk count alone, but it is still not billable tokens; after integrating a model, replace it with the actual tokenizer and context packer.

## Permission and provenance invariants

The retrieval function first checks whether the subject groups and a chunk’s ACL intersect, and only then calculates term scores. An unauthorized table cannot enter scored candidates even if it shares all query terms.

Post-splitting validation also checks:

- chunk IDs are unique and ordinals are consecutive starting at 1;
- bodies are non-empty and do not exceed the hard max;
- ACLs are non-empty;
- content and retrieval hashes match actual text;
- `index_entry_id` binds `chunk_id`, the actual `retrieval_sha256`, `index_revision`, and the ACL snapshot;
- spans do not exceed their source;
- no chunk crosses source, revision, or ACL;
- every unit of every element is covered at least once.

This is a teaching security baseline, not a complete IAM system. Tenant isolation, deny rules, user/group inheritance, and auditing must be designed in the system’s authorization model.

## Run the tests

Both normal and optimized modes should pass. `-O` removes bare `assert` statements, so testing both modes prevents production checks from being implemented as asserts that disappear.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Continue to prevent bytecode caches and keep the repository clean.
python -B -W error -m unittest discover -s '.\docs-EN\chunking-strategies\examples' -p 'test_chunking_lab.py' -v  # Discover and run this project’s tests in normal interpreter mode.
python -B -O -W error -m unittest discover -s '.\docs-EN\chunking-strategies\examples' -p 'test_chunking_lab.py' -v  # Repeat with -O to verify that validation does not rely on removable asserts.
```

The tests cover:

- lexical-unit character offsets and invalid configurations;
- duplicate JSON keys, non-finite values, exact field sets, and bad references;
- quote uniqueness and unit boundaries;
- hard maxima, full coverage, and every isolation boundary;
- actual overlap and termination for oversized elements;
- table headers in retrieval text rather than row bodies;
- chunk IDs that are stable under an unrelated prefix insertion and sensitive to content, version, and strategy;
- changes to a heading path or table-header context, which must change `retrieval_sha256` and `index_entry_id` even when the body chunk identity can remain;
- `index_entry_id` sensitivity to index version and ACL snapshot, and its presence in per-query results;
- ACL filtering before scoring;
- deterministic metrics and CLI behavior in normal and `-O` modes.

## How to extend this into a real experiment

Change only one layer at a time and save versions:

1. **Real tokenizer**: replace the meter and record package version, encoding/model identifier, and the model’s official input limit.
2. **Real embeddings**: retain the same chunks, queries, and gold data; record model, dimensions, normalization, and batch failures.
3. **Vector retrieval**: record distance metric, filtering semantics, top-*k*, and index version.
4. **Reranker**: fix the initial candidate set and report metrics and latency before and after reranking.
5. **Answer evaluation**: add citation support, answer correctness, no-answer abstention, and safety tests.
6. **Shadow rebuilding**: write a new strategy to a new version, reconcile it, then switch the published pointer.

If a network experiment lacks keys or dependencies, do not fabricate results; configuration templates may contain placeholders or `.env.example` only.

## Practical assignments

### Required assignment A: create unequal quality results

Extend the corpus and queries so that a fixed window cuts through a multi-unit evidence anchor while the structure-aware strategy retains the complete element. Do not change the evaluation code to “manufacture a win”; explain why the added case represents a real query type.

### Required assignment B: conduct an overlap ablation

Hold all other variables fixed. Run `overlap_units=0,4,8,16` and record:

- Anchor Recall@3;
- complete-evidence rate;
- body duplication ratio;
- mean context units.

Use a table to state the choice and its stopping condition. If every quality metric is identical, prefer lower duplication rather than claiming that larger overlap is better.

### Required assignment C: classify errors

Manually inspect failed queries and classify their cause as: missing heading, broken condition, mixed topic, broken table, code boundary, ACL, lexical mismatch, insufficient top-*k*, or incorrect gold data. Give at least one executable correction and possible side effect for each class.

### Advanced assignment: replace the retriever

Implement a new `retrieve` adapter while retaining `QueryCase`, `EvidenceAnchor`, and `evaluate`. This permits an independent comparison of retrieval backends without rewriting gold data and metrics at the same time.

## Mastery checklist

- [ ] I can explain the one main difference between the two strategies.
- [ ] Gold data anchors elements or spans rather than a fixed chunk sequence number.
- [ ] I can distinguish Recall, MRR, complete-evidence rate, and no-answer accuracy.
- [ ] I report quality, duplication, context, and rebuilding cost together.
- [ ] I do not generalize an offline lexical experiment into a production-RAG conclusion.
- [ ] Permission filtering occurs before scoring and is rechecked during parent or merge operations.
- [ ] I can explain why a heading or table-header change may preserve a body chunk but must invalidate an old index record.
- [ ] Both normal and `-O` tests pass and CLI output is deterministic.
- [ ] Every dynamic model or API fact has a version and source-check date.

## References

- [LangChain Text Splitters](https://docs.langchain.com/oss/python/integrations/splitters)
- [Unstructured: Chunking](https://docs.unstructured.io/open-source/core-functionality/chunking)
- [Azure AI Search: Chunk documents](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-chunk-documents)

Sources checked on 2026-07-22; offline execution rechecked on 2026-07-22. On completion, return to [[chunking-strategies/00-index|the Chunking Strategies course index]] and continue to [[embeddings/00-index|Embeddings]]. After completing the downstream retrieval courses, use [[rag/09-project-offline-provenance-from-source-to-citation|the RAG source-to-citation evidence chain]] to verify the cross-layer identity from an index entry to a citation.
