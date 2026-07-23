---
title: "OCR"
tags:
  - ai-agent-engineer
  - ocr
  - multimodal
aliases:
  - Optical Character Recognition learning path
  - OCR knowledge base
ai_learning_stage: 8. Extended applications and complex collaboration
ai_learning_order: 49
ai_learning_schema: 2
ai_learning_id: ocr
ai_learning_domain: multimodal
ai_learning_catalog_order: 4900
ai_learning_hard_prerequisites: []
ai_learning_track_rag_order: 450
ai_learning_track_rag_kind: optional
ai_learning_track_multimodal_realtime_order: 250
ai_learning_track_multimodal_realtime_kind: recommended
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: OCR/00-目录.md
translation_source_hash: 1db1ade03d044df619ee8afb995aa26d12dc9fa4ee82117c2ed1a35ad79d28bf
translation_route: zh-CN/OCR/00-目录
translation_default_route: zh-CN/OCR/00-目录
---

# OCR

## Course overview

OCR (Optical Character Recognition) converts visible text in photographs, scans, or PDF pages into searchable and computable data. A genuinely usable system does more than turn an image into a string: it retains page numbers, text boxes, reading order, table structure, confidence, and provenance so that an Agent can cite source material, trigger human review, and trace errors.

This course starts with imaging and layout intuition, then covers recognition, post-processing, evaluation, and privacy-aware deployment. It concludes with a fully offline auditor for structured results that ties the pipeline together. Product capabilities may change by version; dynamic material was checked on **2026-07-22**, and you should still consult the official documentation for the target version before using it.

## Where this fits in the overall path

OCR belongs to the Extended applications and complex collaboration stage. It turns document images into structured input that [[document-parsing/00-index|Document Parsing]] and [[rag/00-index|RAG]] can consume, and it provides an auditable text channel for [[multimodal-ai/00-index|Multimodal AI]].

## Learning objectives

- Explain the full pipeline from imaging, preprocessing, and layout analysis to text recognition and post-processing.
- Design a stable result contract for text blocks, tables, reading order, pages, and confidence.
- Use CER, WER, field metrics, and structural metrics to locate errors instead of relying on one aggregate score.
- Design low-confidence human review, privacy boundaries, and regression-ready offline test sets.
- Complete a standard-library project that validates structure, order, text errors, and a review queue.

## Prerequisites

- [[python-fundamentals/00-index|Python Fundamentals]], [[json/00-index|JSON]], and [[data-annotation/00-index|Data Annotation]] are recommended.
- No image-processing or deep-learning background is required. The course introduces intuition first and then establishes the engineering boundaries.

## Recommended order

1. [[ocr/foundations-and-data/01-ocr-pipeline-and-input-contract|The OCR pipeline and input contract]]: define inputs, outputs, and traceability fields first.
2. [[ocr/foundations-and-data/02-imaging-principles-and-preprocessing|Imaging principles and preprocessing]]: learn why resolution, skew, noise, and binarization affect recognition.
3. [[ocr/foundations-and-data/03-text-detection-recognition-and-data-annotation|Text detection, recognition, and data annotation]]: distinguish where text is from what it says.
4. [[ocr/engineering-and-quality/04-layout-tables-and-reading-order|Layout, tables, and reading order]]: avoid joining columns, tables, and headers incorrectly.
5. [[ocr/engineering-and-quality/05-language-postprocessing-and-confidence|Language post-processing and confidence]]: normalize with defined boundaries and route work to review.
6. [[ocr/engineering-and-quality/06-evaluation-error-analysis-and-human-review|Evaluation, error analysis, and human review]]: establish text, field, and structural evaluations.
7. [[ocr/engineering-and-quality/07-privacy-deployment-and-operational-troubleshooting|Privacy, deployment, and operational troubleshooting]]: make data minimization, logging, and rollback part of the design.
8. [[ocr/project-and-self-check/08-project-structured-ocr-result-audit|Project: structured OCR result audit]]: run the offline project and complete its acceptance checks.

## Hands-on entry point

- Main project: [[ocr/project-and-self-check/08-project-structured-ocr-result-audit|Structured OCR result audit]].
- Project assets: [[ocr/project-and-self-check/examples/audit_ocr_fixture.py|audit script]], [[ocr/project-and-self-check/examples/ocr_fixture.json|structured fixture]], and [[ocr/project-and-self-check/examples/test_contract_and_cli.py|contract and CLI regression tests]].
- The entire project uses only the Python 3 standard library. It reads no real documents, downloads no models, and creates no workspace artifacts.

## Mastery criteria

- [ ] I can draw and explain the OCR data flow for detection, recognition, layout, post-processing, and review.
- [ ] I can explain why merely increasing image dimensions does not necessarily improve quality, and design a reversible preprocessing comparison.
- [ ] I can define reading order and structured output for a multi-column page and a table.
- [ ] I can calculate a CER/WER example by hand and explain why the denominator is the reference-text length.
- [ ] I can combine low confidence, critical-field rules, and sampling review into a human work queue.
- [ ] I can run the project, interpret its report, and add an anonymized fixture for a new document type.

## Connections to other knowledge bases

- Image acquisition and multimodal understanding are covered in [[multimodal-ai/00-index|Multimodal AI]].
- OCR output is chunked, enriched with metadata, and cited through [[document-parsing/00-index|Document Parsing]], [[chunking-strategies/00-index|Chunking Strategies]], [[rag/00-index|RAG]], and [[knowledge-base-construction/00-index|Knowledge Base Construction]]. Page, block or cell, source revision, ACL, and deletion state must propagate with every chunk and embedding.
- Operational metrics, drift, and alerts should feed into [[runtime-monitoring/00-index|Runtime Monitoring]]. For sensitive documents, consult [[privacy-computing/00-index|Privacy Computing]] and [[ai-governance/00-index|AI Governance]].

## Primary references

The following sources were checked on **2026-07-22**:

- [Tesseract User Manual (official; the current documentation line is 5.x)](https://tesseract-ocr.github.io/tessdoc/)
- [Tesseract: Improving the quality of the output (official)](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)
- [PaddleOCR PP-StructureV3 documentation (official latest/version3.x)](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PP-StructureV3.html)
- [PaddleOCR Layout Detection (official latest/version3.x)](https://www.paddleocr.ai/latest/en/version3.x/module_usage/layout_detection.html)
- [Unicode Standard Annex #15: Unicode Normalization Forms (Unicode 17.0.0, Revision 57)](https://www.unicode.org/reports/tr15/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

> [!warning] Version boundary
> Model names, parameters, language coverage, and deployment methods in official documentation can change. This course teaches stable engineering concepts; it does not treat an example on a current documentation page as a permanent API. Before an integration, pin dependencies and run regression tests on the target document set.
