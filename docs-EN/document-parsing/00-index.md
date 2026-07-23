---
title: "Document Parsing"
tags:
  - ai-agent-engineer
  - document-parsing
  - rag
aliases:
  - Document parsing learning path
source_checked: 2026-07-22
source_baseline:
  - Unicode 17.0.0 / UAX
  - pypdf 6.14.2 documentation
  - OCRmyPDF 17.8.1 documentation
  - Python 3.11 standard library project
execution_verified: 2026-07-22
content_origin: original
content_status: dynamic
ai_learning_stage: 4. RAG and knowledge bases
ai_learning_order: 22
ai_learning_schema: 2
ai_learning_id: document-parsing
ai_learning_domain: retrieval-and-data
ai_learning_catalog_order: 2200
ai_learning_hard_prerequisites:
  - data-cleaning
  - json
ai_learning_track_rag_order: 500
ai_learning_track_rag_kind: core
lang: en
translation_key: 文档解析/00-目录.md
translation_source_hash: ace5365539e3d5a7a2800646665cc76caf8ecac5c3909f614269affb66ec8438
translation_route: zh-CN/文档解析/00-目录
translation_default_route: zh-CN/文档解析/00-目录
---

# Document Parsing

## Course overview

Document parsing converts the bytes, pages, and layout in a file into structured elements that can be retrieved, cited, and verified. For RAG, obtaining “one long string of text” is not enough: heading hierarchy, reading order, table cells, page numbers, coordinates, permissions, and parsing warnings all affect later chunking and answer evidence.

This course follows an important boundary: **use deterministic detection and native parsing first, and use OCR or vision models only when needed; every probabilistic result must retain its provenance and quality state.** The learning project does not pretend that the standard library alone can parse PDF or Office files. Instead, it demonstrates how to register, route, and reject them safely.

## Where this course fits

This is an entry point in the RAG and knowledge bases stage. Complete [[data-cleaning/00-index|Data Cleaning]] and [[json/00-index|JSON]] first, then study this course. Its parsing output is versioned by [[knowledge-base-construction/00-index|Knowledge Base Construction]] and composed into retrieval units by [[chunking-strategies/00-index|Chunking Strategies]].

## Learning objectives

After completing this course, you should be able to:

- distinguish filename extensions, transport `Content-Type`, magic bytes, and inspection inside containers;
- design a replayable pipeline of discovery, registration, detection, parsing, normalization, acceptance, and publication;
- handle UTF-8, BOMs, line endings, and Unicode normalization with strict decoding;
- preserve headings, lists, code, tables, reading order, and provenance coordinates;
- distinguish the capability boundaries of digital PDFs, scanned PDFs, hidden text layers, OCR, and VLMs;
- set gates for type, size, count, time, permissions, and isolation for untrusted files; and
- determine usability with automated metrics and human gold sets instead of merely checking whether a process exited successfully.

## Prerequisites

- Know how to use Python strings, dictionaries, exceptions, `pathlib`, and `unittest`.
- Understand media types and requests/responses in [[api/00-index|API]].
- Understand the basic structure of [[markdown/00-index|Markdown]], [[json/00-index|JSON]], and CSV.

## Recommended sequence

1. [[document-parsing/01-format-identification-and-parsing-pipeline|Format identification and the parsing pipeline]]: build a safe routing contract from bytes, filenames, and content signals.
2. [[document-parsing/02-encoding-text-and-normalization|Encoding, text, and normalization]]: avoid mojibake, silent character loss, and unauditable “cleanup.”
3. [[document-parsing/03-structure-headings-lists-and-tables|Structure, headings, lists, and tables]]: turn body text into elements with hierarchy, order, and coordinates.
4. [[document-parsing/04-pdf-and-ocr-boundaries|PDF and OCR boundaries]]: choose native extraction, OCR, layout models, or human review by page.
5. [[document-parsing/05-metadata-quality-validation-and-project|Metadata, quality validation, and the project]]: run the offline inspector and interpret pass, review, and fail gates.

Use a rhythm of “read one lesson, complete its exercises, change one project rule, and run the tests.” Do not install a large parsing framework first. Understand the input, output, failure, and evidence contracts before deciding whether a framework result is trustworthy.

## Hands-on entry point

Project files:

- [[document-parsing/examples/inspect_documents.py|Offline document-manifest inspector]]
- [[document-parsing/examples/test_inspect_documents.py|Inspector regression tests]]
- [[document-parsing/examples/document-manifest.schema.json|Manifest JSON Schema]]

It scans a specified directory read-only and produces deterministic manifests for UTF text, Markdown, HTML, CSV, and JSON. It stops at `external_adapter_required` for PDF, Office files, archives, and images. Its 27 tests cover format disguises, strict decoding, duplicate JSON keys, CSV embedded newlines, parse revisions, source line numbers, content and element hashes, symbolic links, and resource budgets. If a file grows after the `stat()` precheck, bounded reading rejects it rather than reading the whole file into memory.

The focused project validates only a parser manifest. First study the [[rag/09-project-offline-provenance-from-source-to-citation|Source-to-citation reference model]] for target invariants. Then, in the [[rag/10-project-cross-layer-provenance-adaptation-and-atomic-publication|Cross-module source-adaptation project]], call the current parser fresh and handle native line coordinates, namespaced element IDs, and a release crosswalk. [[rag/11-project-external-provenance-artifact-v2|External Provenance Artifact v2]] continues by validating whether a parser record, raw/canonical representations, and a crosswalk can be rebuilt fresh across a strict JSON boundary.

## Mastery criteria

- [ ] I can explain why a `.pdf` suffix, an HTTP `Content-Type`, or one magic pattern cannot independently prove a file type.
- [ ] I can design an element schema for headings, paragraphs, tables, and code that includes `source_id`, order, location, and hashes.
- [ ] I will not disguise a decoding failure as success with `errors="ignore"`.
- [ ] I can decide whether a page needs native extraction, OCR, vision understanding, or human review.
- [ ] I can explain why OCR confidence is not a probability that a fact is correct.
- [ ] I can make identical inputs and configuration produce the same manifest, and produce a new version ID when the source file changes.
- [ ] I can design automated gates, stratified samples, and human acceptance for critical fields.
- [ ] I can state clearly which format capabilities the project has and has not verified.

## Connections to other courses

- [[knowledge-base-construction/00-index|Knowledge Base Construction]]: manages raw files, parsing versions, failure queues, and publication state.
- [[chunking-strategies/00-index|Chunking Strategies]]: composes parsed elements and should not repeat expensive OCR.
- [[ocr/00-index|OCR]]: covers image preprocessing, text recognition, and OCR evaluation in depth.
- [[multimodal-ai/00-index|Multimodal AI]]: handles charts, formulas, visual question answering, and other tasks beyond text-only parsing.
- [[rag/00-index|RAG]]: retrieval and answer quality are bounded by parsing completeness and traceability.
- [[ai-safety/00-index|AI Safety]]: untrusted documents can contain malicious containers, scripts, prompt injection, and sensitive information.

## Primary references

- [IANA Media Types registry](https://www.iana.org/assignments/media-types/media-types.xhtml)
- [Apache Tika: Content Detection](https://tika.apache.org/3.3.1/detection.html)
- [Unicode Standard Annex #15: Normalization Forms](https://www.unicode.org/reports/tr15/)
- [RFC 8259: The JavaScript Object Notation (JSON) Data Interchange Format](https://www.rfc-editor.org/rfc/rfc8259.html)
- [RFC 4180: Common Format and MIME Type for CSV Files](https://www.rfc-editor.org/rfc/rfc4180.html)
- [pypdf: Extract Text from a PDF](https://pypdf.readthedocs.io/en/latest/user/extract-text.html)
- [Tesseract User Manual](https://tesseract-ocr.github.io/tessdoc/)
- [OCRmyPDF Introduction](https://ocrmypdf.readthedocs.io/en/latest/introduction.html)
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [Docling documentation](https://docling-project.github.io/docling/)

Sources retrieved on 2026-07-22. Tool versions change; when installation options or supported formats matter, consult the current official documentation.
