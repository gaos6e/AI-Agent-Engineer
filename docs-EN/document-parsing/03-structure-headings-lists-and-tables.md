---
title: "Structure, headings, lists, and tables"
tags:
  - ai-agent-engineer
  - document-parsing
  - document-structure
aliases:
  - Document-structure parsing
source_checked: 2026-07-22
source_baseline:
  - Python 3.11 html.parser
  - pypdf 6.14.2 documentation
  - Docling documentation retrieved 2026-07-22
lang: en
translation_key: 文档解析/03-结构标题列表与表格.md
translation_source_hash: d4c1f9de3746ea89f6fbf9fbb70d32e0690e914f212130233fff0d6b0064c4ed
translation_route: zh-CN/文档解析/03-结构标题列表与表格
translation_default_route: zh-CN/文档解析/03-结构标题列表与表格
---

# Structure, headings, lists, and tables

## Goal

Upgrade “plain-text extraction” into structured elements. Preserve heading hierarchy, lists, code, tables, reading order, and source locations, and distinguish structure explicitly supplied by a source document from structure inferred by a parser.

## Why one string of text is not enough

The sentence “External tools must be disabled” takes its meaning and scope from whether it appears beneath a “High-risk operations” heading. A `0.92` in a table cannot support a safe answer if its row label, column label, and unit are lost. For RAG, structure supports chunking and retrieval, but it is also evidence for citation and human review.

Common element types include:

- `title`, `heading`, and `paragraph`;
- ordered/unordered `list_item` elements and nested levels;
- `code_block`, its language, and original whitespace;
- `table`, rows, columns, headers, merge relationships, and a caption;
- images, formulas, footnotes, headers, and footers; and
- pages, coordinates, character/word spans, and reading order.

## Explicit and inferred structure

An HTML `<h2>`, Markdown `##`, or DOCX style can explicitly express a heading. “Large and bold text” on a PDF page is only a visual feature; it is not necessarily a heading. Record the following for each element:

- `structure_source: explicit | inferred`;
- the inferencer and version;
- the rule or model configuration used;
- optional confidence signals and warnings; and
- the original location, so a human can revisit the page.

Confidence signals can prioritize review; they cannot automatically prove semantic correctness. Vision-model output is also probabilistic inference and must not overwrite native structure or original coordinates.

## A traceable element contract

```json
{
  "element_id": "sha256:abc...:e0012",
  "kind": "paragraph",
  "text": "Requests must set a timeout.",
  "text_sha256": "...",
  "order": 12,
  "location": {"page": 3, "bbox": [72, 120, 510, 158]},
  "section_path": ["Reliability", "Timeouts"],
  "attributes": {"structure_source": "explicit"}
}
```

`element_id` should be stable within one source version and parsing configuration; `order` expresses the selected reading order; and `location` returns to the source. The course project uses `line_start/line_end` for text files; PDFs can use page numbers and bounding boxes. A coordinate system must state its origin, units, rotation, and crop box, or its numbers are uninterpretable.

Do not copy sensitive full text into every log or index record. Text and metadata can have different storage permissions, but the citation chain must remain intact.

## Headings, lists, and code

### Heading paths

Maintain a stack while parsing headings: when an H2 occurs, close preceding headings at the same or deeper level, then push the new heading. If a document jumps directly from H1 to H3, do not invent an intermediate heading; retain a skipped-level warning instead. Repeated headings are common, so `section_path + order` is more reliable than a heading string.

### Lists

A list item should preserve whether it is ordered or unordered, its level, its number (if any), its checked state, and its parent relationship. Flattening a nested list into paragraphs loses step dependencies and exception conditions.

### Code

Newlines and indentation in a code block are semantic. Preserve its language marker, original text, and source location; perform secret detection and safety controls before display or execution. Code in a document is never trustworthy merely because it came from a knowledge base.

## Tables: retain both structure and derived text

At minimum, a table needs:

- rows, columns, and headers;
- merged cells and cross-page relationships, when available;
- its caption, footnotes, and units;
- page/coordinate data and original cell text; and
- structure-inference warnings.

For retrieval, you can derive a row such as “Model A has a latency of 120 ms,” but that sentence must point to the original table and must not replace structured cells. Otherwise, a shifted column becomes a more fluent-looking error.

Typical difficulties include borderless tables, repeated headers, cross-page tables, line breaks within cells, nested tables, footnotes, and merged cells. A `DataFrame` being constructible proves only syntactic success, not that its row/column facts are correct.

## Reading order and layout

The internal order of PDF objects might be “left-column first line, right-column first line, left-column second line,” or it might inject headers and footnotes into the body. Simply sorting by `(y, x)` fails on multiple columns, floating images, and rotated pages.

Use a layered strategy:

1. Prefer trustworthy logical structure in the format.
2. Establish layout regions and columns for each page.
3. Order elements within each region.
4. Label roles such as header, footer, caption, and footnote.
5. Validate order using human samples from target document types.

Modern parsing frameworks such as Docling treat layout, reading order, tables, formulas, and a unified document representation as separate capabilities. That means choosing a library does not remove contract and evaluation work: changing versions, models, or configuration still requires re-acceptance.

## Quality checks

Automated checks can detect:

- abnormal heading levels or every piece of content becoming one paragraph;
- duplicate element `order`, out-of-bounds locations, or missing page counts;
- repeated page headers/footers leaking into the body on every page;
- table-column drift, empty headers, or unhandled repeated headers;
- abnormally long lines, many empty elements, or a surge of zero-width characters; and
- derived text that cannot locate its source element.

A human gold set should also label reading order, heading parent/child relations, critical table cells, formulas, and figure captions item by item. High automated completeness does not equal semantic correctness.

## Common mistakes and troubleshooting

- **Hard-coding headings from font size:** different templates, footnotes, and covers break the rule.
- **Discarding page numbers/coordinates before chunking:** later citation and repair become unreliable.
- **Treating structure parsing and chunking as one step:** a changed chunking strategy then forces expensive parsing to run again.
- **Keeping only Markdown generated by an LLM/VLM:** generated text can add, reorder, or omit content; retain intermediate structure and original locations.
- **Ignoring repeated headings:** IDs generated from heading names alone collide.

## Exercises

1. Extend the preceding element schema for headings, paragraphs, nested lists, code, tables, and captions.
2. For a two-column page, draw its regions and reading order, and name three cases in which `(y, x)` sorting fails.
3. Convert one table row into retrieval text and write its pointer back to original cells.
4. Design a gold set for 20 target documents that covers repeated headers, cross-page tables, footnotes, mixed Chinese/English text, and code.

## Self-check

- [ ] I can distinguish explicit structure from inferred structure.
- [ ] I can store a stable identity, order, and interpretable location for any element.
- [ ] I know that derived table text cannot replace original structure.
- [ ] I evaluate reading order, hierarchy, and critical cells separately.

## References and next step

- [Python `html.parser`](https://docs.python.org/3.11/library/html.parser.html)
- [pypdf: Extract Text from a PDF](https://pypdf.readthedocs.io/en/latest/user/extract-text.html)
- [Docling document model](https://docling-project.github.io/docling/concepts/docling_document/)

Sources retrieved on 2026-07-22. Next: [[document-parsing/04-pdf-and-ocr-boundaries|PDF and OCR boundaries]].
