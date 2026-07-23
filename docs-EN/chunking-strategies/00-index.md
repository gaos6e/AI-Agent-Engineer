---
title: "Chunking Strategies"
tags:
  - ai-agent-engineer
  - chunking
  - rag
aliases:
  - Document Chunking Strategies
  - Chunking
source_checked: 2026-07-22
source_baseline: Official live documentation checked through 2026-07-22; offline
  examples use the Python 3.11 standard library and a custom lexical unit
execution_verified: 2026-07-22
content_origin: original
content_status: dynamic
ai_learning_stage: 4. RAG and knowledge bases
ai_learning_order: 24
ai_learning_schema: 2
ai_learning_id: chunking
ai_learning_domain: retrieval-and-data
ai_learning_catalog_order: 2400
ai_learning_hard_prerequisites: []
ai_learning_track_rag_order: 700
ai_learning_track_rag_kind: core
lang: en
translation_key: Chunking策略/00-目录.md
translation_source_hash: 953f72704c3582601735236127d1d83f2303516825c468486221405cfd3bf9da
translation_route: zh-CN/Chunking策略/00-目录
translation_default_route: zh-CN/Chunking策略/00-目录
---

# Chunking Strategies

## Course overview

Chunking organizes parsed document elements into evidence units that can be retrieved independently, traced back to their source, and fit into a model context. It is not simply cutting a long text shorter: chunk boundaries affect embedding representations, retrieval granularity, citation precision, access-control filtering, update scope, and inference cost at the same time.

There is no universal size for every corpus. FAQs, policies, code, tables, and long narratives need different boundaries preserved; the same strategy can also behave oppositely for a question that asks for one number and one that synthesizes conditions across paragraphs. A reliable process defines the input and evidence anchors first, establishes a simple baseline, and then compares quality and cost on a target query set.

> [!important] Evidence boundary in this course
> The `lexical unit` used in the examples is a regex-based measurement unit for reproducible offline experiments, not a tokenizer for any model. When you integrate a real embedding model or LLM, recheck its tokenizer, input limits, and current official documentation.

## Where this course fits

[[document-parsing/00-index|Document Parsing]] produces elements with structure, position, version, and permissions; this course turns those elements into chunks; [[knowledge-base-construction/00-index|Knowledge Base Construction]] manages their lifecycle and publication. The candidate chain then runs through [[embeddings/00-index|Embeddings]], [[vector-databases/00-index|Vector Databases]], [[semantic-search/00-index|Semantic Search]], and [[reranking/00-index|Reranking]]. Finally, [[rag/00-index|Retrieval-Augmented Generation (RAG)]] verifies that the evidence can be found, ranked correctly, and used to support an answer.

## Learning objectives

After completing this course, you should be able to:

- distinguish characters, words, tokens, sentences, paragraphs, parsed elements, and chunks;
- turn a model input limit into an explainable chunk budget instead of copying a number;
- implement fixed-window, recursive-boundary, and structure-aware baselines;
- handle headings, lists, code, tables, and oversized single elements;
- design overlap, parent-child chunks, retrieval context, provenance anchors, ACLs, and stable IDs;
- build a gold set anchored to original elements or spans and compare Recall@k, MRR, evidence-completeness rate, and cost;
- design dual-version rebuilding, validation, cutover, and rollback for a strategy upgrade.

## Prerequisites

- Read and write Python lists, functions, JSON, and command-line programs.
- Understand the basic structure of HTTP documentation or Markdown.
- Know the basic flow: retrieval finds candidates before a model receives them. The formulas start from first principles.

If you need a refresher, start with [[python-fundamentals/00-index|Python Fundamentals]], [[json/00-index|JSON]], and [[document-parsing/00-index|Document Parsing]].

## Core terms

| Term | Beginner-friendly explanation | Constraint in this course |
| --- | --- | --- |
| element | A paragraph, heading, table row, or code block recognized by a parser | A stable source anchor; not the same thing as a chunk |
| chunk | The basic evidence unit for indexing and retrieval | Must be traceable to source, version, position, and permissions |
| hard max | A limit that no chunk may exceed | Oversized elements must be split again |
| soft max | The target at which further merging should normally stop | It may be slightly under or over to preserve a whole element, but never beyond the hard max |
| overlap | The source range repeated by adjacent windows | It serves boundary evidence only and counts toward cost |
| retrieval text | Text used for retrieval or vectorization | It may include headings or table headers, but must be separate from citable source text |
| provenance | Evidence about source, version, elements, and positions | Supports citation, deletion, rebuilding, and audit |

## Recommended sequence

| Order | Lesson | Learning outcome |
| --- | --- | --- |
| 1 | [[chunking-strategies/01-units-budgets-and-baselines\|Units, budgets, and baselines]] | Define measurement units, input budgets, a chunk schema, and a comparable baseline. |
| 2 | [[chunking-strategies/02-fixed-windows-and-recursive-splitting\|Fixed windows and recursive splitting]] | Write a splitter that terminates, covers all input, and never exceeds the hard max. |
| 3 | [[chunking-strategies/03-structural-and-semantic-chunking\|Structural and semantic chunking]] | Choose strategies for headings, tables, code, and weakly structured text. |
| 4 | [[chunking-strategies/04-overlap-metadata-and-context\|Overlap, metadata, and context]] | Control duplication cost while preserving ACLs, citations, and version traceability. |
| 5 | [[chunking-strategies/05-retrieval-evaluation-and-chunking-project\|Retrieval evaluation and the chunking project]] | Run an offline comparison, evaluate two strategies with provenance anchors, and verify that a changed retrieval representation produces a new index-record identity. |

Follow the sequence. Lessons 1–2 establish correctness, lessons 3–4 establish engineering boundaries, and lesson 5 turns “this feels better” into reproducible evidence.

## Hands-on entry point

The project files are part of this knowledge base:

- [[chunking-strategies/examples/chunking_lab.py|chunking_lab.py]]: a structure-aware strategy, fixed-window baseline, ACL filtering, and evaluation;
- [[chunking-strategies/examples/corpus.json|corpus.json]]: paragraphs, code, tables, and oversized elements;
- [[chunking-strategies/examples/queries.json|queries.json]]: a query set anchored by `element_id + exact quote`;
- [[chunking-strategies/examples/test_chunking_lab.py|test_chunking_lab.py]]: 32 tests for input contracts, coverage, boundaries, stable IDs, `index_entry_id` invalidation semantics, and determinism.

From the project root (which contains `docs-CN/`, `docs-EN/`, and `.website/`), run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Prevent __pycache__ generation so the run does not pollute the knowledge base.
python -B -W error '.\docs-EN\chunking-strategies\examples\chunking_lab.py'  # Run the offline chunking, retrieval, and evaluation experiment.
python -B -W error -m unittest discover -s '.\docs-EN\chunking-strategies\examples' -p 'test_chunking_lab.py' -v  # Discover and run the adjacent test file verbosely.
```

The project is fully offline, needs no API key, and does not represent production performance for real vector retrieval.

## Mastery checklist

- [ ] I can explain why a chunk is not synonymous with a page, paragraph, or tokenizer token.
- [ ] I can derive a chunk hard max from the total input budget and document the meter and its version.
- [ ] The split result covers every source unit, has deterministic order, cannot loop forever, and never crosses a source, revision, or ACL boundary.
- [ ] Tables, code, headings, and oversized elements have explicit, testable strategies.
- [ ] Overlap has a boundary assumption, a duplication metric, and a condition for turning it off.
- [ ] I store retrieval text, citable source text, and derived context separately and hash them separately.
- [ ] `index_entry_id` binds the chunk, retrieval-text hash, index version, and ACL snapshot, so a changed heading or table-header context cannot silently reuse an old index record.
- [ ] Gold data anchors stable sources instead of becoming invalid whenever chunk IDs are rebuilt.
- [ ] I report retrieval quality, evidence completeness, context cost, and indexing cost together.
- [ ] A strategy upgrade can be validated, switched, and rolled back in two versions.

## Relationship to other courses

| Course | Input or output relationship |
| --- | --- |
| [[document-parsing/00-index\|Document Parsing]] | Supplies structural elements, page or line positions, source revisions, and parsing warnings. |
| [[knowledge-base-construction/00-index\|Knowledge Base Construction]] | Manages chunk revisions, publication pointers, deletion, and rebuilding. |
| [[embeddings/00-index\|Embeddings]] | Determines the actual tokenizer, vector input, and model version. |
| [[vector-databases/00-index\|Vector Databases]] | Stores vectors, filter fields, and chunk metadata. |
| [[semantic-search/00-index\|Semantic Search]] | Checks candidate recall, filtering, and ranking behavior. |
| [[reranking/00-index\|Reranking]] | Reorders candidates and controls repeated context. |
| [[rag/00-index\|Retrieval-Augmented Generation (RAG)]] | Verifies final citation support, answer correctness, and abstention. |

After completing this course project, first study [[rag/09-project-offline-provenance-from-source-to-citation|the offline evidence chain from source to citation]] to understand the target invariants. Then run [[rag/10-project-cross-layer-provenance-adaptation-and-atomic-publication|cross-module provenance adaptation and atomic publication]] to see how real chunking lexical spans, native ID schemes, KB releases, and citations connect through an explicit crosswalk. Finally, use [[rag/11-project-external-provenance-artifact-v2|External Provenance Artifact v2]] to verify that a complete chunk or entry payload can still reconstruct its route, ACL, and coverage after leaving the producer process.

## Primary references

- [LangChain Text Splitters](https://docs.langchain.com/oss/python/integrations/splitters): current official splitter categories and the entry point for recursive splitting.
- [Unstructured: Chunking](https://docs.unstructured.io/open-source/core-functionality/chunking): parsed-element chunking, hard and soft maxima, tables, and overlap behavior.
- [Azure AI Search: Chunk documents](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-chunk-documents): chunking units, layout awareness, and vector-retrieval practices.
- [OpenAI tiktoken](https://github.com/openai/tiktoken): the official repository for a model-related token-measurement tool.
- [Anthropic: Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval): one engineering approach for adding retrieval context to chunks.
- [LlamaIndex Node Parser](https://developers.llamaindex.ai/python/framework/module_guides/loading/node_parsers/): current official documentation on node parsing and relationship organization.

Sources checked on 2026-07-22. Recheck dynamic SDKs, model limits, and cloud-service behavior on the day of implementation.
