---
title: "Chunking Units, Budgets, and Baselines"
tags:
  - ai-agent-engineer
  - chunking
aliases:
  - Chunk Size Fundamentals
  - Chunk Budgets
source_checked: 2026-07-14
source_baseline: tiktoken, Azure AI Search, and Unstructured official material
  checked through 2026-07-14
lang: en
translation_key: Chunking策略/01-切分单位预算与基线.md
translation_source_hash: 893c00bc8b22a464a8fc3d490be5f659537ede0a74afe4f8fb235d19c3a11271
translation_route: zh-CN/Chunking策略/01-切分单位预算与基线
translation_default_route: zh-CN/Chunking策略/01-切分单位预算与基线
---

# Chunking Units, Budgets, and Baselines

## Learning objectives

After this lesson, you will be able to answer three distinct questions in the right order:

1. What length am I measuring?
2. Why should a chunk have this limit?
3. How do I establish a baseline that can still be compared fairly later?

## First distinguish elements, chunks, and context

An `element` output by a parser is a source-structure unit, such as a paragraph, one table row, or a code block. A `chunk` is an evidence unit combined or split for indexing and retrieval. The final context sent to a model may consist of several chunks, headings, and a system prompt.

Therefore:

- one element may be split into several chunks by an oversized-element fallback rule;
- several short elements may be merged into one chunk;
- a matching child chunk may map back to a larger parent context;
- a chunk cannot replace a source record: final citations must still return to an element or span.

This distinction underpins stable incremental updates, deletion, permissions, and evaluation.

## Length units are not interchangeable

| Unit | Strength | Risk | Suitable use |
| --- | --- | --- | --- |
| Unicode characters | Dependency-free and easy to reproduce | No fixed ratio to model tokens | A minimal teaching baseline and text-integrity checks |
| Whitespace-tokenized words | Intuitive for English | Unstable for Chinese, code, URLs, and punctuation | Rough statistics for a specific English corpus |
| Tokenizer tokens | Closest to a model input constraint | Bound to a model and encoding version | Production hard maxima and cost budgets |
| Sentences or paragraphs | More natural boundaries | Highly long-tailed; sentence splitting can fail | Candidate boundaries for recursive splitting |
| Parsed elements | Preserves heading, table, and code semantics | Depends on parsing quality | Preferred input for structure-aware chunking |

“About how many tokens are 500 characters?” can only be an empirical observation for a particular language, corpus, and tokenizer. Do not turn a conversion ratio into a system constant. OpenAI’s `tiktoken` is a tokenizer tool, but a real project still needs to check the chosen model, encoding, and current limits.

The `lexical unit` used by this course’s experiment is a regex-recognized English word, single Han character, or non-whitespace symbol. It is only for offline demonstration, and the output explicitly states that it is “not a model tokenizer.”

## Derive the budget from total input

The retrieved chunks do not occupy a generation model’s entire input. Estimate every part with the same meter:

$$
B_{\text{retrieval}}
=
B_{\text{input}}
-
(B_{\text{system}}+B_{\text{history}}+B_{\text{query}}+B_{\text{tools}}+B_{\text{output reserve}}+B_{\text{safety}})
$$

If you plan to send at most $k$ chunks, and each one also needs headings, separators, and citation metadata, an initial body budget can be written as:

$$
B_{\text{chunk body}}
\le
\left\lfloor\frac{B_{\text{retrieval}}}{k}\right\rfloor
-
B_{\text{per-chunk overhead}}
$$

This is only an initial upper bound. It must also satisfy:

- the embedding model’s single-input limit;
- the reranker’s input and candidate-count limits;
- database-field or batch-processing limits;
- boundaries such as intact table rows and code blocks that must not be damaged arbitrarily.

> [!example] Teaching-only calculation
> Suppose the total budget is 800 units measured in the same way, all other parts and safety margin take 320, you plan to include at most 4 chunks, and heading/citation overhead is about 20 per chunk. The initial body upper bound is $(800-320)/4-20=100$. These numbers are not specifications of any real model; obtain real values from current official documentation and measurement.

## Soft max and hard max

- `hard max`: no output may exceed it. An oversized single element must enter a windowed fallback.
- `soft max`: the target at which merging adjacent complete elements should normally stop, preventing excessive fragmentation.
- `minimum useful size`: not a demand to fill every chunk, but a signal for isolated headings, lone punctuation, or context-free short chunks.

Keep complete elements first and merge small ones without exceeding the hard max. Do not cut table rows, function signatures, or conditional sentences merely to make a round number.

## Minimum output contract

A maintainable chunk must at least answer “where did it come from, how was it produced, who can see it, and how can it be verified?”

```json
{
  "chunk_id": "chk_<content-derived digest>",
  "source_id": "api-guide",
  "source_revision": "rev-3",
  "strategy_version": "structure-v1",
  "ordinal": 7,
  "text": "Citable source text",
  "retrieval_text": "Heading path + retrievable text",
  "element_spans": [
    {"element_id": "api-e3", "unit_start": 0, "unit_end": 25}
  ],
  "section_path": ["API Guide", "Retries"],
  "acl": ["employees"],
  "content_sha256": "<digest>",
  "retrieval_sha256": "<digest>"
}
```

JSON does not allow end-of-line comments. To keep the preceding block directly parseable, its field explanations are outside it: `chunk_id` is a content-derived identity; `source_id/source_revision` identify a stable source version; `strategy_version/ordinal` explain generation order; `text` preserves citable source text; `retrieval_text` serves retrieval only; `element_spans` retain locations in the source; `section_path/acl` record structure and visibility respectively; and the two SHA-256 fields detect drift in the body or retrieval text.

`ordinal` is for display order and should not determine an ID by itself. Inserting a paragraph at the beginning of a document should not make every later ID drift. One auditable approach includes the source and revision, strategy version, element spans, content hash, and permissions in a normalized hash. The exact identity rule is an architectural choice, but it needs tests and documented migration effects.

## Establish a minimal baseline

The first version does not need to be “intelligent.” A fixed-window baseline is valuable because it is deterministic, inexpensive, and easy to debug. Hold these variables fixed:

- the same parsed elements and source revision;
- the same meter;
- the same query and gold set;
- the same retriever, candidate count, and filters;
- the same evaluation code;
- only one changed chunking factor.

At minimum, observe:

| Correctness | Retrieval quality | Cost |
| --- | --- | --- |
| Full source-unit coverage, order, hard max, and boundary isolation | Anchor Recall@k, MRR, complete-evidence rate, no-answer accuracy | Chunk count, duplicated units, retrieval-context units, indexing rebuild volume |

In addition to overall averages, slice results by fact lookup, cross-paragraph conditions, tables, code, and no-answer cases. Two strategies can have the same average while one fails consistently for a query type.

## Common mistakes and diagnosis

- **Using the model’s maximum context window as chunk size directly**: this forgets the system prompt, tool schema, history, and output reserve.
- **Using inconsistent meters**: splitting by characters but monitoring with another model’s tokens makes a hard max meaningless.
- **Looking only at average length**: one long tail can still cause truncation or request failure.
- **Changing chunking and embedding together**: you cannot attribute the difference to either change.
- **Hard-coding chunk IDs in gold data**: rebuilding a strategy invalidates the entire evaluation set.
- **Mixing source text with retrieval prefixes**: a citation may misrepresent a derived heading as original text.

## Exercises

1. For short FAQs, long policies, a codebase, and cross-page tables, write down the preferred element boundary and the boundary that must never be crossed.
2. Assume a total budget of 2,000, a reserved portion of 800, $k=5$, and 40 units of overhead per chunk. Calculate the initial body upper bound, then explain why it is still not the final optimal size.
3. Add page numbers or line numbers to the preceding JSON schema, but do not give one chunk two differently meant `start/end` pairs.
4. Design a failed experiment that changes the tokenizer and overlap at the same time, and explain why its result cannot be attributed.

## Mastery checklist

- [ ] I can distinguish an element, a chunk, and final context.
- [ ] I measure with the current model tokenizer rather than quoting a fixed conversion.
- [ ] I can derive an initial chunk upper bound from total input budget and retain a safety margin.
- [ ] I distinguish soft max from hard max.
- [ ] Every chunk has source, version, position, ACL, strategy, and hashes.
- [ ] My baseline changes one factor at a time.

## Summary and next step

Write down the units, budget, identity, and comparability conditions before discussing which strategy is better. Next, implement deterministic splitting and lock down correctness with property tests: [[chunking-strategies/02-fixed-windows-and-recursive-splitting|Fixed Windows and Recursive Splitting]].

## References

- [OpenAI tiktoken](https://github.com/openai/tiktoken)
- [Azure AI Search: Chunk documents](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-chunk-documents)
- [Unstructured: Chunking](https://docs.unstructured.io/open-source/core-functionality/chunking)

Sources checked on 2026-07-14. Return to [[chunking-strategies/00-index|the Chunking Strategies course index]].
