---
title: "2026-07-22 Phase 19 Deep Review Record: Ingestion, Data, Multimodal, and
  Realtime Contracts"
aliases:
  - Phase 19 optimization record
tags:
  - maintenance
  - ingestion
  - data-quality
  - multimodal
  - realtime
  - learning-path
source_checked: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: 维护记录/2026-07-22-第十九阶段摄取数据多模态与实时合同深审记录.md
translation_source_hash: 19ccc124bc12425808774ee17251bc98964d72eaec1bb9e40b56222b5ebfe4ec
translation_route: zh-CN/维护记录/2026-07-22-第十九阶段摄取数据多模态与实时合同深审记录
translation_default_route: zh-CN/维护记录/2026-07-22-第十九阶段摄取数据多模态与实时合同深审记录
---

# 2026-07-22 Phase 19 Deep Review Record: Ingestion, Data, Multimodal, and Realtime Contracts

## Phase conclusion

This phase turns upstream paths that are easily miswritten as “complete once the model can read or answer” into checkable engineering contracts. Files and sources have boundaries when entering the system; data, labels, and synthetic samples express their version and release relationship; media evidence, OCR, and retrieval do not cross object-level authorization; and realtime speech does not use “reconnected” to skip side-effect reconciliation after a disconnect.

It covers [[document-parsing/00-index|Document Parsing]], Knowledge Base Construction, [[data-cleaning/00-index|Data Cleaning]], Data Annotation, Synthetic Data, Multimodal AI, [[ocr/00-index|OCR]], [[speech-recognition/00-index|Speech Recognition]], [[text-to-speech/00-index|Text-to-Speech]], and Realtime Multimodal Interaction.

> [!important] What this phase does not prove
>
> Standard-library fixtures, SQLite, and a static-site build prove consistency among the teaching contracts, links, and current content. They do not prove that malicious-file isolation, real OCR/multimodal model quality, an identity provider, physical deletion from a vector store, external-tool receipts, browser or telephony media stacks, Provider retention policies, or legal obligations have been production-validated.

## Multi-Agent division of work and primary-Agent review

The primary Agent first fixed cross-course boundaries for stable asset/source versions, object-level authorization, derivative products, evidence support, release identity, actionable input, and deletion propagation, then divided three non-overlapping areas:

1. Document Parsing and Knowledge Base Construction: file budgets, parser/OCR boundaries, versions, outbox, ACL, and revocation.
2. Data Cleaning, Annotation, and Synthesis: schema/manifest, frozen splits, adjudication, provenance, and release.
3. Multimodal AI and OCR: media evidence, source integrity, OCR-to-RAG projection, C2PA, and safety.

The primary Agent independently reviewed Speech Recognition, Text-to-Speech, and Realtime Interaction; corrected state-machine and code contracts; and then checked cross-course terminology, links, test counts, and source boundaries individually. Each Agent changed only its assigned directory. None staged, committed, pushed, reverted user files, or changed generated site directories.

## Key changes

### Ingestion and knowledge bases: a controlled canonical form precedes a searchable projection

- Document Parsing no longer trusts file size merely after <code>stat()</code>. The teaching parser actually reads at most the budget plus one byte, and rejects rather than fully reads a file that grows after the check. The course also covers double extensions, path segments, post-decoding validation, Unicode normalization, TOCTOU, and the boundary that “OCR is not malicious-PDF isolation.”
- The Knowledge Base outbox worker now checks the event and <code>tenant/document/revision</code> identity. Only an upsert for the still-current, non-deleted revision materializes a search projection; a stale upsert is consumed but cannot make old content searchable again. Queries also recompute canonical-content/source/build hashes and ACL. Candidate window, ACL-group count, and request-group count have fail-closed limits.
- The index adds an original Mermaid overview of version release → outbox → search projection → revocation/deletion. Deletion, old revisions, caches/replicas, and physical purge remain explicitly distinct.

### Data quality: separate ledger facts, evaluation oracles, and release evidence

- Data Cleaning separates schema, data contract, and release manifest. It requires freezing <code>group_id → family_id</code> and split mappings before fitting any learned statistic to avoid family leakage and post hoc splitting.
- Data Annotation states that <code>final_label</code> is an adjudicated annotation-ledger fact. It must be projected through a frozen <code>guideline_version → rubric_version</code> mapping into an evaluation <code>expected_label</code>, tool oracle, or rubric; these are not one field. Adjudication, guideline updates, bridge samples, and relabeling are now visualized.
- The Synthetic Data project moves beyond the presence of a provenance field: it validates generator type/version, the template ID for the condition, variable mapping, and the declaration of real data. Regressions rise from 40 to 43. <code>release_id</code> now binds suite, dataset, rubric, grader, harness, per-case results, and approval, rather than treating dataset version as release identity.

### Multimodal and OCR: a citation's existence is neither evidence support nor authorization

- Media and OCR courses consistently retain <code>asset_id</code>, <code>source_revision</code>, derivative-processing version, coordinates/time ranges, classification, and object-level authorization. <code>evidence_bound</code> means only that a pointer is parseable and currently readable; <code>evidence_supported</code> means that evidence actually entails the claim.
- C2PA is explicitly limited to a provenance/integrity signal for content. It cannot be promoted to factual truth, speaker identity, or business authorization. Source revocation/deletion is described as “fail closed online, then confirm layered propagation through OCR/ASR text, chunks, Embedding, indexes, cache, evaluation copies, and backups.”
- The OCR teaching auditor no longer falsely reports CER/WER as <code>1.0</code> when reference text is empty and prediction is nonempty. It returns <code>null</code> and requires separate slice analysis. The Multimodal router returns <code>2</code> and prints no partial report when report writing fails.

### Speech and realtime interaction: observation, actionable input, and side-effect recovery are distinct

- The ASR course distinguishes <code>partial</code>, <code>provisional_final</code>, and <code>committed</code>. Revisable transcripts cannot trigger a writing tool directly; only an independent <code>turn.commit</code> or user confirmation can elevate one to actionable input. It also corrects the terminology boundary between diarization and source separation.
- The TTS SSML course uses the W3C-described valid XML prolog and namespaced <code>speak</code> form, rather than claiming an XML declaration is the one required form for every integration.
- The realtime state diagram changes the post-reconnection path to <code>Reconciling</code>. The teaching simulator adds a gate: if an old write call is awaiting reconciliation, recovery rejects new work and permits only receipt/result, another disconnect, or timeout. Only after every conclusion is auditable does it return to <code>Listening</code>. Project regressions rise from 24 to 25.

## Cross-course terminology and responsibility boundaries

| Term | Stable meaning in this phase | It must not be substituted for |
| --- | --- | --- |
| <code>asset_id</code> / <code>source_revision</code> | A media/document object and its current readable version | Content truth, authorization, or a complete RAG object identity |
| <code>source_lineage_id</code> | An abstract source reference in synthetic/data engineering | The RAG contract of <code>tenant_id + document_id + source sequence/revision + generation + ACL/tombstone</code> |
| <code>final_label</code> / <code>expected_label</code> | The former is adjudicated annotation; the latter is a versioned evaluation expectation | Model output, free-text rubric, or an unadjudicated initial label |
| <code>evidence_bound</code> / <code>evidence_supported</code> | The former is a parseable, authorized pointer; the latter is evidence entailment determined by a human/controlled grader | Valid schema, a model's self-claim, or a source hash |
| <code>release_id</code> | Identity of an auditable evaluation/release evidence set | Dataset version, model alias, or a single demo |
| <code>authorization</code> / ACL | A server-side conclusion that the current object, subject, and policy permit handling/reading | Filename, EXIF, source label, or self-reported user field |
| Revocation/deletion propagation | Immediate online block, then layer-by-layer verification of derivatives and retention policy | “The original/one vector was deleted” or a missing hash |
| <code>turn</code> / <code>response</code> / <code>call</code> | Separate correlation domains for realtime input, one output attempt, and tool intent/result | Transport connection, transcript partial, or a playback queue |

## Key sources and material boundary

All new explanations, Mermaid diagrams, tests, and teaching code in this phase are original. Third-party material is cited only through links, fact boundaries, and small terminology explanations; no complete material with unknown redistribution permission is included. Dynamic/specification claims prioritize primary material:

- [OCRmyPDF documentation](https://ocrmypdf.readthedocs.io/en/latest/), [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html), [Unicode UAX #15](https://unicode.org/reports/tr15/), and [Microsoft Graph Delta](https://learn.microsoft.com/en-us/graph/delta-query-overview): ingestion, normalization, and incremental-boundary guidance.
- [Debezium Outbox Event Router](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html), [SQLite foreign keys](https://www.sqlite.org/foreignkeys.html), and [FTS5](https://www.sqlite.org/fts5.html): projections, referential integrity, and search teaching boundaries.
- [JSON Schema 2020-12](https://json-schema.org/specification), [Label Studio import](https://labelstud.io/guide/tasks), [Label Studio export](https://labelstud.io/guide/export.html), [NIST SP 800-226](https://doi.org/10.6028/NIST.SP.800-226), [NIST SP 800-188](https://csrc.nist.gov/pubs/sp/800/188/final), and [NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1): boundaries for data, synthesis, and risk.
- [C2PA 2.4](https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html), [W3C WebVTT](https://www.w3.org/TR/webvtt1/), [Tesseract documentation](https://tesseract-ocr.github.io/tessdoc/), and [PaddleOCR documentation](https://www.paddleocr.ai/latest/): multimodal/OCR evidence and implementation boundaries.
- [W3C SSML 1.1](https://www.w3.org/TR/speech-synthesis11/), [PLS 1.0](https://www.w3.org/TR/pronunciation-lexicon/), [W3C WebRTC](https://www.w3.org/TR/webrtc/), [Media Capture and Streams](https://www.w3.org/TR/mediacapture-streams/), and [RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455): speech markup, media, and transport responsibilities.

## Verification evidence

| Check | Phase result |
| --- | --- |
| Document Parsing / Knowledge Base Construction | 27 / 41 tests; normal and <code>-O</code> passed under <code>-B -W error</code>. |
| Data Cleaning / Data Annotation / Synthetic Data | 10 / 10 / 43 tests; normal and <code>-O</code> passed under <code>-B -W error</code>. |
| Multimodal AI / OCR | 58 / 74 tests; normal and <code>-O</code> passed under <code>-B -W error</code>. |
| Speech Recognition / Text-to-Speech / Realtime Multimodal Interaction | 63 / 63 / 25 tests; normal and <code>-O</code> passed under <code>-B -W error</code>. |
| Consolidated specialist regressions | 414 tests per mode across the preceding 10 groups; warnings-as-errors passed and no current-phase <code>.pyc</code> was generated. |
| Final website unit tests | <code>.website npm test</code>: 47/47 passed. |
| Final public build | 913 source Markdown pages, 573 full pages, 340 fail-closed stubs, and 229 assets; 916 staged Markdown pages, 2,462 HTML pages, and 2,815 public files. Broken local links, sensitive leaks, table wikilinks, interactive checkboxes, and KaTeX errors were all 0. |

Two <code>docs/document-parsing/examples/__pycache__/inspect_documents.cpython-311*.pyc</code> files were confirmed read-only to predate this phase, be untracked, and be ignored. The current <code>-B</code> runs did not update them, so they were retained under the policy of preserving existing local state.

## Follow-up queue

1. Use controlled malicious samples, real parsers/OCR, object-level identity, connector revocation, message buses, and search engines for integration and load verification. Do not elevate the teaching SQLite projection into proof of production deletion.
2. Continue page-by-page review of untouched data-course content that retains an early <code>source_checked</code> date; update by page evidence, not by bulk date changes.
3. Add device, network, media, Provider retention-policy, constrained smoke-test, and human-review processes before real speech/multimodal rollout. The offline event simulator does not validate codecs, echo, NAT, or real side-effect receipts.
4. Inspect new Mermaid diagrams, long tables, callouts, and mobile reading experience in Obsidian desktop. A Quartz build does not replace local Reading View verification.

This record covers only Phase 19. It does not mean the long-running <code>/goal</code> is complete.
