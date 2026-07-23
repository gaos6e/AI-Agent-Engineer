---
title: "Layout, Tables, and Reading Order"
tags:
  - ai-agent-engineer
  - ocr
  - document-layout
aliases:
  - OCR layout analysis
source_checked: 2026-07-22
lang: en
translation_key: OCR/02-工程与质量/04-版面表格与阅读顺序.md
translation_source_hash: 9c26675e15aca2655c2c044799f286407f3cb6b6270eac85621b2891fbc32b62
translation_route: zh-CN/OCR/02-工程与质量/04-版面表格与阅读顺序
translation_default_route: zh-CN/OCR/02-工程与质量/04-版面表格与阅读顺序
---

# Layout, Tables, and Reading Order

## Objective

Understand why a document can still be unusable when every text string is correct, and establish structured representations for paragraphs, tables, and reading order.

## Layout is not decoration

If a two-column paper is concatenated row by row according to coordinates, the first line of the left column can be joined to the first line of the right column. If headers and footers enter the body text on every page, they pollute retrieval. Layout analysis first partitions a page into regions such as titles, paragraphs, tables, images, and formulas, then orders content inside and across those regions.

A basic ordering strategy can begin with geometric rules: group by column, then sort by **top**. Cross-column titles, side notes, and vertical text break that simple rule. In production, retain:

- **block_id**, **block_type**, and coordinates;
- **order** or an explicit **next_block_id**;
- a header or footer marker instead of deleting content immediately;
- the method and version used to produce the order.

## Tables are two-dimensional structures

Turning a table into tab-delimited text alone loses merged cells and header hierarchy. Prefer to output the table boundary, row and column counts, each cell's coordinates, **row_span/col_span**, cell text, and source box. Evaluate tables at least at three levels:

1. Was the table region found?
2. Are rows, columns, and merge relationships correct?
3. Is the text in each cell correct?

“The structure is correct but one amount is wrong” and “all text is correct but columns are shifted” are different failures with different repair paths.

### A table remains structured before retrieval

For [[rag/00-index|RAG]] or an extraction Agent, retain table JSON first: tables, rows, columns, cells, spans, header paths, and coordinates. Render relevant cells as text or Markdown for a question only afterward. Flattening the entire table into a paragraph before splitting can join row/column ownership, units, and headers incorrectly. Every retrieved fragment should still lead back to a page and cell ID.

## Processing order

~~~text
Page -> layout regions -> text/table recognition inside regions -> reading order -> Markdown/JSON export
~~~

PaddleOCR's official PP-StructureV3 documentation illustrates output fields for layout blocks, reading order, and tables. Those fields can change across versions, so an adapter should convert them to your own stable contract.

## Exercises and self-check

- Draw blocks for “two-column body text + a cross-column title + a footer” and assign an order.
- Design JSON for a 2×3 table that contains a horizontally merged cell.
- If exported Markdown appears correct, can coordinates be deleted? No. Coordinates are the evidence trail and the entry point for correction.

## Next step and references

Continue with [[ocr/engineering-and-quality/05-language-postprocessing-and-confidence|Language post-processing and confidence]]. See the official [PaddleOCR PP-StructureV3 documentation](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PP-StructureV3.html) and [Layout Detection documentation](https://www.paddleocr.ai/latest/en/version3.x/module_usage/layout_detection.html) (latest/version3.x; checked on 2026-07-22).
