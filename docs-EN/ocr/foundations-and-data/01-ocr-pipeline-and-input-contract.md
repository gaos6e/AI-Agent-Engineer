---
title: "The OCR Pipeline and Input Contract"
tags:
  - ai-agent-engineer
  - ocr
aliases:
  - OCR pipeline
source_checked: 2026-07-22
lang: en
translation_key: OCR/01-基础与数据/01-OCR全流程与输入契约.md
translation_source_hash: e9145cfe70601af43d38122b56f7910c62f70145b57e5620c74b1e84de1f6d7a
translation_route: zh-CN/OCR/01-基础与数据/01-OCR全流程与输入契约
translation_default_route: zh-CN/OCR/01-基础与数据/01-OCR全流程与输入契约
---

# The OCR Pipeline and Input Contract

## Objective

Understand why OCR is a data pipeline, and learn to write the result contract before selecting a model.

## From seeing to usable data

When a person sees an invoice, they understand text, position, tables, and hierarchy at the same time. A computer receives only pixels. An auditable OCR pipeline typically includes:

1. **Acquisition and decoding**: record the original file, page number, dimensions, color space, and orientation.
2. **Preprocessing**: correct rotation or perspective, suppress noise, and adjust contrast when necessary.
3. **Layout analysis**: locate titles, paragraphs, tables, images, headers, and other regions.
4. **Text detection**: predict bounding boxes or polygons for text regions.
5. **Text recognition**: convert the pixels in each region into a character sequence.
6. **Ordering and post-processing**: restore reading order, normalize characters, and apply bounded rules.
7. **Quality control**: calculate metrics and send uncertain or high-risk results to people.

Detection answers “where is the text?” Recognition answers “what is the text?” Direct full-page recognition can sometimes work, but once a complex layout is ordered incorrectly, text that is individually correct is still unusable for question answering or extraction.

## Define the output contract first

A minimal text block can be represented as:

~~~json
{
  "document_id": "sample-001",
  "page": 1,
  "block_id": "p1-b03",
  "type": "text",
  "bbox": [120, 80, 620, 150],
  "order": 3,
  "text": "Total: CNY 128.00",
  "confidence": 0.93,
  "source": {
    "asset_id": "original-sample-001",
    "asset_sha256": "record-at-runtime",
    "coordinate_space": "page_pixels",
    "transform_id": "record-at-runtime",
    "engine": "record-at-runtime",
    "model": "record-at-runtime"
  }
}
~~~

The **bbox** field is only a coordinate convention. The contract must also state whether it uses pixels or normalized coordinates, and whether the order is **[left, top, right, bottom]** or another format. **asset_sha256**, **transform_id**, and the coordinate space bind a text box to one original revision and its derivative image; after cropping, rotating, or rerunning OCR, do not reuse an old box. **confidence** is a model score, not a probability of correctness. Scores from different engines are not directly comparable, and thresholds must be calibrated on your own validation set.

## Failure boundaries

- Retaining only plain text loses the evidence location and prevents highlighting it on the original page.
- Retaining only average confidence can hide errors in critical fields such as amounts and identifiers.
- Overwriting the original image during preprocessing makes an error irreproducible. Keep the original read-only and record derivative parameters.
- Treating a filename as an identity breaks on duplicates or moves. Use a stable document ID and content digest instead.

## Evidence and authorization before RAG

When exporting blocks as chunks, carry at least **document_id**, page, block or table-cell ID, source revision, coordinates or reading order, classification, and active object-level authorization/ACL. Chunks, embeddings, vector projections, and retrieval caches are derivatives of the original. When a source is revoked, expires, or changes, filter it from online candidates immediately, then propagate revocation or deletion as described in [[knowledge-base-construction/03-versioning-deletion-and-authorization|Versioning, deletion, and authorization]]. Storing only OCR **text** in a vector database loses citable evidence and can continue retrieving content whose authorization was removed.

## Exercises and self-check

Draw the data flow for an anonymized two-page document whose second page contains a table, then answer:

1. Which fields locate the original image?
2. Where do the table's row and column relationships belong?
3. How can the same batch of documents be compared after an engine upgrade?

If the answer lacks versioning, a coordinate convention, or original provenance, the contract is not yet sufficient for auditability.

## Next step and references

Continue with [[ocr/foundations-and-data/02-imaging-principles-and-preprocessing|Imaging principles and preprocessing]]. See the [Tesseract User Manual (current 5.x line)](https://tesseract-ocr.github.io/tessdoc/) and the [PaddleOCR PP-StructureV3 output schema (latest/version3.x)](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PP-StructureV3.html), checked on 2026-07-22.
