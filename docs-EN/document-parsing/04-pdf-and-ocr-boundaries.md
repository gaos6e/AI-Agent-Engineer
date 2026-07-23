---
title: "PDF and OCR boundaries"
tags:
  - ai-agent-engineer
  - document-parsing
  - PDF
  - OCR
aliases:
  - PDF parsing boundaries
source_checked: 2026-07-22
source_baseline:
  - pypdf 6.14.2 documentation
  - Tesseract 5.x user manual
  - OCRmyPDF 17.8.1 documentation
lang: en
translation_key: 文档解析/04-PDF与OCR边界.md
translation_source_hash: cda9e71f2c8205245fb509bce42c5cda9ab4c12c1a42a58032b25fc86a8019bb
translation_route: zh-CN/文档解析/04-PDF与OCR边界
translation_default_route: zh-CN/文档解析/04-PDF与OCR边界
---

# PDF and OCR boundaries

## Goal

Understand why a PDF is not “Word with page numbers”; choose native text extraction, OCR, layout/vision models, or human review by page; and retain enough version, location, and quality evidence for every path.

## A PDF describes page presentation first

A PDF can store characters, fonts, drawing instructions, and coordinates separately. A paragraph that a reader sees does not necessarily correspond to one internal text object; a space may be only glyph spacing, and a table may be lines plus text positioned by coordinates. The pypdf documentation explicitly discusses the difficulties of reading order, spaces, tables, image text, and memory, and it clearly states that pypdf is not OCR software.

Therefore, a non-empty result from `extract_text()` proves only that the parser found some text objects. It does not prove that:

- text is complete and in the correct order;
- a hidden text layer matches the page image;
- table rows/columns, formulas, and footnotes have been recovered; or
- pages contain no duplication, mojibake, or misalignment.

## Classify pages first

| Page type | Symptoms | Preferred path | Main risks |
| --- | --- | --- | --- |
| Digitally generated | Fonts and text objects are present | Native extraction + layout validation | wrong order, hyphenation, font mapping |
| Scanned image | The page is mostly a bitmap with little or no text | Render + OCR | recognition, rotation, columns, noise |
| Mixed page | Images and text objects coexist | Process by region or layer | duplicate text, missing captions |
| Hidden OCR layer | Invisible text overlays an image | Sample alignment, then reuse or redo | old OCR errors or misalignment |
| Form/signature/formula-heavy | The relationship between text and visuals matters | Specialized parser or VLM + human gate | field pairing, symbols, signature meaning |

Classify by page or region rather than making one decision for a whole file. A cover can be a scan while the body is digitally generated text.

## Decision order

1. **Native extraction:** low cost and preserves existing character information; first inspect text volume, character quality, order, and page coverage.
2. **OCR:** use it when no reliable text layer exists and a page contains image text; record language, resolution, engine, and word/line locations.
3. **Layout/table/formula models:** OCR recognizes characters and locations; it does not automatically restore semantic structure.
4. **VLMs:** useful for charts or complex visual understanding, but output can omit, paraphrase, or generate content; retain image regions and structural constraints.
5. **Human review:** cannot be omitted for critical amounts, doses, contract terms, formulas, low-confidence fields, or failed quality gates.

Running OCR across every digital PDF usually wastes resources and can turn correct native characters into recognition errors. One goal of OCRmyPDF is to add a searchable text layer to scanned PDFs. Its current 17.8 documentation consolidates existing-text-layer policy under `--mode default|force|skip|redo`; the older `--force-ocr`, `--skip-text`, and `--redo-ocr` remain compatibility aliases. An adapter must record the actual mode, software version, and input-page classification, rather than merely saying “OCR completed”; its trigger conditions must be explicit.

## OCR adapter contract

An OCR product should record at least:

- the raw PDF hash, page number, render region, and page-image hash;
- render DPI and preprocessing such as rotation, deskewing, or binarization;
- engine, version, language packs, and configuration;
- word, line, or block text with bounding boxes;
- confidence signals supplied by the engine, if any; and
- elapsed time, warnings, failures, and human-review state.

Tesseract language data and page-segmentation configuration affect results. A confidence score is an internal engine signal, not a probability that the field is factual, and it cannot be compared directly across engines.

An OCR cache key should include the source-page version and OCR configuration. Otherwise, an old result may be reused incorrectly after changing a language pack or DPI. A change in chunking parameters should not trigger OCR again.

## Formulas, tables, and images are not ordinary OCR

- `0/O`, `1/l/I`, decimal points, minus signs, and superscripts/subscripts are high-risk confusions;
- mathematical formulas require two-dimensional structure, and linear plain text often loses fractions, radicals, and superscripts/subscripts;
- OCR provides words and coordinates, not necessarily table headers, merged cells, or cross-page relationships;
- extracting chart values requires understanding axes, legends, and visual elements; and
- recognizing handwriting, stamps, and signatures is different from determining their legal meaning.

Define domain rules for high-risk fields, such as amount formats, sum checks, date ranges, and table-column consistency, and retain human confirmation.

## How to evaluate

Sample in strata by document type, language, scan quality, and layout. Evaluate at least separately:

- **character error rate (CER) / word error rate (WER):** measure transcription difference, but do not directly express factual risk;
- **critical-field accuracy:** compare amounts, dates, identifiers, doses, and similar fields exactly;
- **reading order:** have a human judge whether paragraphs are readable and footnotes are inserted correctly;
- **table cells:** inspect rows, columns, headers, merge relationships, and critical values;
- **traceability:** determine whether every output can return to its page and region; and
- **coverage:** measure empty pages, missing pages, unrecognized regions, and duplicated content.

Even a low average CER can conceal one wrong decimal point in a critical value. Acceptance thresholds must follow the use case and risk, not copied marketing figures from a tool.

## Security, privacy, and cost

PDFs and images can contain personal information, hidden layers, attachments, and metadata. Before using remote OCR/VLM services, confirm data residency, retention policy, permissions, and vendor contracts. Logs should not copy full text; caches must inherit source-document permissions and have a deletion policy.

> [!warning] OCR tools are not malicious-PDF isolation
>
> The current OCRmyPDF documentation explicitly says that it is not designed to defend against PDFs carrying malicious content. File detection, page limits, and OCR mode cannot replace an isolated process, least privilege, malicious-content scanning, and human publication gates. The teaching project only records these boundaries; it does not run PDF/OCR.

OCR/VLM processing also consumes pages, resolution, GPU/CPU, money, and latency. Set per-page pixel limits, total-page limits, timeouts, and concurrency limits; send over-limit work to a queue or human handling rather than run without bound in an interactive request.

## Common mistakes and troubleshooting

- **Skipping OCR because text is non-empty:** a hidden OCR layer can be misaligned with the image, so sample alignment.
- **OCRing every PDF first:** this increases cost and can lower quality for digital PDFs.
- **Checking only one page that “looks right”:** cover real layouts and critical fields.
- **Treating OCR confidence as accuracy:** it does not replace gold labels.
- **Letting a VLM emit final Markdown directly:** intermediate coordinates, versions, and omission checks are missing.
- **Claiming PDF support with tests that use only a fake header:** file-registration tests are not PDF-parsing tests.

## Exercises

1. For digital, scanned, mixed, and hidden-OCR-layer pages, write trigger rules, cache keys, and fallback states.
2. Design a 12-page gold set that covers Chinese, English, two columns, rotation, low resolution, formulas, tables, stamps, and critical numbers.
3. For an “invoice total,” design character-level, field-level, and human-review gates.
4. Write an external OCR-adapter interface: its input must contain more than a file path, and its output must contain more than one full-text string.

## Self-check

- [ ] I can explain the difference between PDF text objects and visual reading order.
- [ ] I select native extraction, OCR, vision models, or human review one page at a time.
- [ ] I can preserve the engine, configuration, page, and coordinates for an OCR result.
- [ ] I know which questions CER, confidence scores, and critical-field accuracy answer.
- [ ] I do not misrepresent the teaching project’s format registration as validated PDF/OCR content quality.

## References and next step

- [pypdf: Extract Text from a PDF](https://pypdf.readthedocs.io/en/latest/user/extract-text.html)
- [Tesseract User Manual](https://tesseract-ocr.github.io/tessdoc/)
- [OCRmyPDF Introduction](https://ocrmypdf.readthedocs.io/en/latest/introduction.html)
- [Docling supported formats and pipelines](https://docling-project.github.io/docling/usage/supported_formats/)

Sources retrieved on 2026-07-22. The behavior and installation of these tools can change by version. Next: [[document-parsing/05-metadata-quality-validation-and-project|Metadata, quality validation, and the project]].
