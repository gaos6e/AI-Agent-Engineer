---
title: "Structural and Semantic Chunking"
tags:
  - ai-agent-engineer
  - chunking
  - semantic-retrieval
aliases:
  - Semantic Chunking
  - Structure-Aware Chunking
source_checked: 2026-07-14
source_baseline: Unstructured, LlamaIndex, and Anthropic official material plus
  the original Late Chunking and RAPTOR papers, checked through 2026-07-14
lang: en
translation_key: Chunking策略/03-结构化与语义切分.md
translation_source_hash: e5ff7e1f4f36f8d9e841b48fab2dcac45dea8fbb08eb90e8cb8616de213113f9
translation_route: zh-CN/Chunking策略/03-结构化与语义切分
translation_default_route: zh-CN/Chunking策略/03-结构化与语义切分
---

# Structural and Semantic Chunking

## Learning objectives

You will learn to use trustworthy document structure first, handle headings, tables, code, and lists separately, and understand parent-child retrieval and retrieval context. Finally, you will judge when semantic chunking, Late Chunking, and hierarchical summarization are worth experimenting with instead of assuming that “smarter” automatically means better.

## Structure-aware chunking: respect boundaries the author already provided

[[document-parsing/00-index|Document Parsing]] commonly already produces element types, section paths, page or line positions, and reading order. Chunking should consume that information rather than flattening every element into one long string again.

A robust basic process is:

1. partition by source, revision, and ACL;
2. form candidate groups by section and content family (body text, code, and tables);
3. merge adjacent complete elements within the hard max;
4. use a family-specific fallback window only when one element is oversized;
5. generate element spans, heading paths, hashes, and a strategy version;
6. verify that all source units are covered and no safety boundary was crossed.

Unstructured’s current chunking likewise combines parsed elements first and only continues splitting when a single element exceeds the limit; its `by_title` strategy also retains section boundaries. Specific parameters can change, but the principle must still be validated on the target corpus.

## Different content needs different rules

### Headings and body text

A heading alone is usually not complete evidence. Put the heading path in `retrieval_text` while keeping the original body in `text`. This lets retrieval find “API Guide > Retries” without presenting a derived prefix as original source text in a citation.

Whether merging across sections is allowed depends on the corpus:

- Regulations and operating manuals: headings often represent strong boundaries, so do not cross them by default.
- FAQs with one sentence per section: elements may be merged under the same parent, but preserve every element span.
- A page number is not a semantic section: do not split only because the page changed, and do not merge across pages unconditionally.

### Tables

Column headers determine what each cell means. Recommended rules:

- keep a small table whole where possible;
- split an oversized table by complete rows;
- repeat the table title and header in each row segment’s retrieval text;
- keep only real rows in citable text rather than presenting a repeated header as row content;
- have parsing verify that a table crossing pages is truly the same table;
- preserve structural metadata for merged cells, footnotes, and units.

`production | 4 | SRE` loses its meaning when separated from `environment | replica count | approval`. The course project specifically tests the branch where the header enters retrieval context only.

### Code, JSON, and logs

For code, prioritize file → class/function → syntax-block boundaries; use statement or token windows only as a fallback for an oversized function. Preserve language, symbol name, file path, and line number. Do not force a split inside a string literal or multiline comment with ordinary newline rules.

For JSON or YAML, prioritize complete object or array entries and retain a JSON Pointer or equivalent path. Logs may be grouped by event, trace, or session, but must set a maximum event size and a redaction rule.

### Lists and definitions

A list item may depend on an introductory sentence such as “Retries are permitted only in the following cases.” When splitting, you can:

- put the introductory sentence and following list items in the same chunk;
- append that sentence to each child item as controlled retrieval context;
- still retain each source span to avoid citing text that does not exist as a single source span.

## Parent-child retrieval

Parent-child mode separates two granularities:

- index smaller children for more focused matches;
- when a child matches, return a larger parent to restore definitions, headings, or adjacent conditions.

Maintain `child_id -> parent_id` and address three risks:

1. **Permissions**: authorize both retrieval and parent expansion. The simplest safe baseline builds a parent only inside an exactly identical ACL.
2. **Versions**: a child and parent must belong to the same source revision, avoiding new/old combinations.
3. **Cost**: deduplicate when several children match the same parent; otherwise the full parent may be sent repeatedly.

Current LlamaIndex Node Parser documentation shows ways to organize nodes and relationships. Concrete classes and defaults are dynamic APIs and should be checked against the official version documentation when used.

## What semantic chunking is

One common approach embeds adjacent sentences or paragraphs and calculates cosine similarity between neighboring representations:

$$
\operatorname{cos}(a,b)=\frac{a\cdot b}{\lVert a\rVert_2\lVert b\rVert_2}
$$

When similarity drops substantially, that location becomes a candidate topic boundary. A model can also judge boundaries, but that adds cost, latency, randomness, and version dependence.

Key limitations:

- no “how large a drop” threshold works across corpora;
- an embedding-model upgrade changes similarities and boundaries;
- sentences can still be too long, so the hard-max fallback cannot be removed;
- semantically similar neighboring paragraphs may not cross ACL, source, or structural boundaries;
- plausible-looking boundaries do not imply better retrieval and answering metrics.

Semantic chunking is therefore a strategy to validate. Fix the corpus, model, threshold, and code version, then run a layered comparison on weakly structured long-form text first.

## Do not confuse three advanced directions

### Contextual Retrieval

Anthropic’s Contextual Retrieval generates or adds a brief document-related context for each chunk and then uses it for retrieval. It changes `retrieval_text` but does not necessarily change original chunk boundaries. Derived context can be wrong, so retain the generation method, version, and hash, and return to original text for citations.

### Late Chunking

The original Late Chunking paper proposes using a document’s long-context encoding first and then pooling token representations by chunk, reducing the loss of global information from “split first, encode second.” It depends on an embedding process that supports the corresponding long context and token-level representations; it is not simply reversing the order of ordinary API calls. Reproduce any benefit on the target model and corpus.

### RAPTOR

The original RAPTOR paper builds a tree of clusters and summaries for retrieval at different abstraction levels. It adds summary generation, hierarchical-update, and error-propagation risks. It can suit experiments that need synthesis across paragraphs, but should not replace a simple baseline or source-level citations.

## Strategy selection table

| Corpus or query | Preferred starting point | When to upgrade |
| --- | --- | --- |
| Short FAQs with clear entries | One question-answer pair or structural elements | Try parent-child when several questions share background |
| Regulations and operating manuals | Element merging within a section | Try child-parent or contextual prefixes when cross-paragraph conditions are missed |
| Large tables | Header plus row segments | Add a table-level parent when cross-row aggregation is needed |
| Codebases | AST or symbol boundaries | Use token fallback for oversized functions; create separate symbol relationships for cross-file questions |
| Untitled long narratives | Paragraph or recursive baseline | Try semantic boundaries after the baseline fails |
| Cross-section synthesis | Structural chunks plus reranking | Try hierarchical summaries after gold data proves the baseline is insufficient |

## Common mistakes and diagnosis

- **Making every heading its own chunk**: this produces isolated headings that cannot answer questions.
- **Splitting tables by character**: data rows lose their headers, so numeric meaning cannot be explained.
- **Mixing code with body text**: vector topics become contaminated and citation line numbers are hard to recover.
- **Not validating LLM boundaries**: returned positions may not exist, overlap, or exceed the hard max.
- **Upgrading the semantic model without rebuilding a version**: the same strategy name now produces different boundaries.
- **Giving the parent a broader ACL than the child**: a matching authorized child leaks other content in the parent.
- **Presenting a research method as universal best practice**: there is no reproduction evidence on the target data.

## Exercises

1. Draw an element → child chunk → parent mapping for a tutorial with three heading levels, a cross-page table, code blocks, and lists.
2. Mark boundaries that must never be crossed (source, revision, ACL), boundaries that normally are not crossed (section, family), and boundaries that evaluation may justify relaxing.
3. For a semantic-chunking experiment, specify fixed variables, the sole independent variable, gold-boundary or retrieval metrics, and rollback conditions.
4. Design an incorrect contextual prefix and explain why retrieval can improve while citation trustworthiness declines.

## Mastery checklist

- [ ] I use parsed structure before losing it and guessing it back.
- [ ] Tables, code, lists, and body text each use their own boundary rules.
- [ ] Parent-child versioning, ACLs, deduplication, and cost all have constraints.
- [ ] I can explain why a semantic-chunking threshold is not a universal constant.
- [ ] I can distinguish semantic boundaries, contextual prefixes, Late Chunking, and RAPTOR.
- [ ] Advanced strategies enter the production candidate set only when a baseline and gold set prove they are needed.

## Summary and next step

Structure is an inexpensive, explainable signal; semantic methods are an experimental supplement, not a replacement for correctness. Next, place overlap, retrieval context, stable IDs, ACLs, and versions into one data contract: [[chunking-strategies/04-overlap-metadata-and-context|Overlap, Metadata, and Context]].

## References

- [Unstructured: Chunking](https://docs.unstructured.io/open-source/core-functionality/chunking)
- [LlamaIndex Node Parser](https://developers.llamaindex.ai/python/framework/module_guides/loading/node_parsers/)
- [Anthropic: Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)
- [Late Chunking: Contextual Chunk Embeddings Using Long-Context Embedding Models](https://arxiv.org/abs/2409.04701)
- [RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval](https://arxiv.org/abs/2401.18059)

Sources checked on 2026-07-14. Engineering suitability of the paper methods must be revalidated against the specific implementation and model. Return to [[chunking-strategies/00-index|the Chunking Strategies course index]].
