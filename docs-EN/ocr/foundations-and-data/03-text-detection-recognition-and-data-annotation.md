---
title: "Text Detection, Recognition, and Data Annotation"
tags:
  - ai-agent-engineer
  - ocr
  - data-annotation
aliases:
  - OCR detection and recognition
source_checked: 2026-07-22
lang: en
translation_key: OCR/01-基础与数据/03-文字检测识别与数据标注.md
translation_source_hash: f46a7a26a24a7db8ca6eba9763770335b020ee1ead862c83ac7e1a10353e5563
translation_route: zh-CN/OCR/01-基础与数据/03-文字检测识别与数据标注
translation_default_route: zh-CN/OCR/01-基础与数据/03-文字检测识别与数据标注
---

# Text Detection, Recognition, and Data Annotation

## Objective

Distinguish text detection, line or word recognition, and end-to-end document parsing, and design a dataset that does not mistake annotation noise for model error.

## Three task types

- **Text detection**: output coordinates for text regions and a detection score.
- **Text recognition**: take a cropped text image and output a character sequence and recognition score.
- **End-to-end OCR**: combine detection and recognition, possibly with orientation, layout, and language modules.

When detection misses a line, even an excellent recognizer cannot recover it. When a detection box includes a neighboring column, a recognizer can produce text that looks plausible but is in the wrong order. Evaluation must therefore observe detection coverage and recognition errors separately.

## Data and annotation contract

Each training or evaluation example should record at least an image reference, page number, region coordinates, transcription, language or script, legibility, annotator, and version. Annotation rules must define:

- Whether original capitalization, whitespace, and punctuation are retained or normalized for the task.
- Whether ambiguous characters are written as a guess, a special marker, or skipped.
- How coordinates are defined for rotated and vertical text.
- How merged and empty cells are represented in tables.

Retain a **verbatim transcription** first, then create a normalized copy for evaluation. Otherwise, model errors cannot be separated from evaluation-cleaning rules.

## Splits and leakage

Do not randomly split pages from the same multi-page document: the same template, font, and stamp can leak into both training and test data. More reliable grouping keys can be the document, source organization, template, or acquisition batch. The test set should include real difficult slices such as low resolution, handwritten annotations, and mixed language, but should not contain only extreme failures.

## Exercises and troubleshooting

1. Design six annotation fields for a Chinese receipt and state when full-width and half-width forms are handled.
2. If a detection box is correct but the recognized text is wrong, should you first check the language model, crop quality, or reading order? Check the crop and recognition first; reading order belongs to later aggregation.
3. If two annotators disagree about **1/l/I**, fix and review the rule first rather than automatically blaming the model.

## Next step and references

Continue with [[ocr/engineering-and-quality/04-layout-tables-and-reading-order|Layout, tables, and reading order]]. See the [PaddleOCR OCR pipeline documentation (latest/version3.x)](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html) and [Tesseract command-line usage (5.x)](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), checked on 2026-07-22. PaddleOCR's current default models and interfaces can change; these sources illustrate modules and output rather than a permanent API. Record the runtime version and configuration for any real integration.
