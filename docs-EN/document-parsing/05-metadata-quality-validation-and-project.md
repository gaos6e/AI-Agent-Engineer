---
title: "Metadata, quality validation, and the project"
tags:
  - ai-agent-engineer
  - document-parsing
  - project
  - quality-gate
aliases:
  - Document-parsing quality project
source_checked: 2026-07-22
execution_verified: 2026-07-22
content_origin: original
content_status: validated
source_baseline:
  - Python 3.11 standard library
  - JSON Schema draft 2020-12
  - Offline deterministic test suite
lang: en
translation_key: 文档解析/05-元数据质量验证与项目.md
translation_source_hash: 45477aedd9d05fc869648cb3f1abf1a7d96a33f2ad1184e0c1e90c1aa2e22e3e
translation_route: zh-CN/文档解析/05-元数据质量验证与项目
translation_default_route: zh-CN/文档解析/05-元数据质量验证与项目
---

# Metadata, quality validation, and the project

## Goal

Turn the preceding four lessons into a small runnable, regression-tested project with explicit capability boundaries. Be able to reconstruct the input version, parser, configuration, element locations, and failure reason from a manifest, and design automated gates and human acceptance.

## Three metadata layers

### Source layer

- business `document_id` and content-version `source_id`;
- original URI or controlled relative path;
- `raw_sha256`, size, and acquisition status;
- source system, permission labels, and validity period;
- declared and detected types.

### Parsing layer

- parser/adapter name, version, and configuration hash;
- run status, error code, warnings, and resource consumption;
- normalization-rule version; and
- parent source version and derived-artifact hash.

### Element layer

- `element_id`, kind, and order;
- locations such as page, line, and bounding box;
- `section_path` and structure source;
- text hash and table/code attributes; and
- permission inheritance and human-review state.

This project demonstrates only fields that an offline file inspector can determine. A production system also needs business identity, permissions, time, and isolated-execution records.

## Quality is not one score

| Dimension | Example automated signal | Example human acceptance |
| --- | --- | --- |
| Completeness | file/page/element count, empty-page rate | whether appendices and captions are missing |
| Correctness | invalid characters, table-column count, field validation | whether amounts, formulas, and negations are correct |
| Order/structure | unique order, heading levels, repeated headers | whether a two-column reading order is natural |
| Traceability | complete location fields, recomputable hashes | whether the original page and region can be reached quickly |
| Stability | identical input/configuration gives identical output | whether an upgrade difference is explainable |
| Security | type conflicts, limits exceeded, symbolic links | permissions, prompt injection, and sensitive-content governance |

Automated metrics mainly reveal symptoms. Critical scenarios still need stratified gold sets, plus annotation guidance, sample versions, and reviewer agreement.

## Project capability contract

The project includes:

- [[document-parsing/examples/inspect_documents.py|inspect_documents.py]]: a read-only scanner;
- [[document-parsing/examples/test_inspect_documents.py|test_inspect_documents.py]]: 27 standard-library regression tests; and
- [[document-parsing/examples/document-manifest.schema.json|document-manifest.schema.json]]: the output contract.

Implemented:

- routing by allowlisted extensions, magic bytes, HTML content features, and ZIP container signatures;
- rejection of conflicts such as “PDF suffix + HTML content”;
- strict decoding of UTF-8/UTF-8 BOM/UTF-16 BOM plus LF + NFC normalization;
- minimal structural elements for Markdown, HTML, CSV, JSON, and plain text;
- rejection of duplicate JSON keys and non-finite values, and support for commas/newlines embedded in CSV fields;
- relative paths, source hashes, configuration hashes, `parse_revision_sha256`, element hashes, explicit coordinate spaces, line ranges, and heading paths. A parse revision binds the raw hash, parser name/version, and configuration hash; an element ID additionally binds the parse revision, kind, location, and text hash;
- file-count, single-file, and total-byte budgets without following symbolic links. After a `stat()` precheck, bounded reading enforces the budget again: the application requests at most one byte beyond the limit and rejects growth when detected; and
- `pass`, `review_required`, and `fail` gates with deterministic output.

Explicitly not implemented:

- PDF/Office/image content parsing, OCR, VLMs, or container expansion;
- OS sandboxes, antivirus, content sanitization, or a permissions system. Bounded reading also cannot replace a controlled file descriptor or isolated execution that resists TOCTOU attacks;
- browser-grade HTML error recovery, CSS layout, or complete Markdown dialects; and
- automatic encoding guessing, language detection, production-grade concurrency, or enforced time/memory isolation.

These omissions are interface boundaries, not problems to hide. For those formats, the manifest returns `external_adapter_required` rather than producing false text.

## First run

From the project root (which contains `docs-CN/`, `docs-EN/`, and `.website/`), use PowerShell 7:

```powershell
$project = '.\docs-EN\document-parsing\examples'
$sample = Join-Path $env:TEMP 'document-inspector-sample'
$report = Join-Path $env:TEMP 'document-inspector-report.json'
New-Item -ItemType Directory -Path $sample -Force | Out-Null
Set-Content -LiteralPath (Join-Path $sample 'guide.md') -Encoding utf8 -Value "# Timeouts`n`nRequests must set a timeout."
Set-Content -LiteralPath (Join-Path $sample 'cases.csv') -Encoding utf8 -Value 'name,note','A,"contains, a comma"'
py -3.11 -B "$project\inspect_documents.py" $sample --output $report
$manifest = Get-Content -LiteralPath $report -Raw -Encoding utf8 | ConvertFrom-Json
$manifest.summary | Format-List
```

When every input is in scope, parses successfully, and has no warning, the process exit code is 0 and `summary.gate` is `pass`. Output must be outside the input directory so a subsequent scan does not treat its own manifest as a new input.

Adding a PDF, DOCX, PNG, or ZIP makes the manifest record `external_adapter_required`; warnings such as UTF-16, BOMs, or control characters also require review. The gate is then `review_required`, with process exit code 2. Type conflicts, decoding failures, unknown extensions, and resource-limit excess produce `fail`. Exit code 2 does not mean that the program crashed: it requires the caller to explicitly handle the unpublished state.

## Run the regression tests

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location '.\docs-EN\document-parsing\examples'
try {
    py -3.11 -B -W error -m unittest -v test_inspect_documents.py
    py -3.11 -B -O -W error -m unittest -v test_inspect_documents.py
} finally {
    Pop-Location
}
```

The 27 tests cover normal and failure paths, including Markdown structure and NFC, CSV quoting/newlines, duplicate JSON keys/`NaN`, UTF-16 boundaries, invalid UTF-8, ignored HTML scripts, format disguises, PDF/OOXML routing, unknown extensions, three resource limits, the byte budget during reading, deterministic output, recomputation of parse-revision/element identities, hash changes, path privacy, and output-location restrictions.

`-O` removes Python `assert` statements, so production gates cannot be bare `assert` statements. This implementation uses explicit exceptions and states; tests still use `unittest` assertion methods.

After completing the project, use the [[rag/09-project-offline-provenance-from-source-to-citation|Source-to-citation evidence-chain project]] to connect a parse revision with canonical revision, chunk/index generation, and a final source-span citation. This page’s independent manifest still does not include a business document ID, ACL lifecycle, or publication pointer.

## How to read a manifest

Read `summary.gate` first, then inspect every document:

1. Do `extension_media_type` and `detected_media_type` agree?
2. Does `status` permit publication?
3. Is each item in `issues` a warning or an error?
4. Can `raw_sha256`, parser/version, and `config_sha256` locate the version?
5. Are every element’s `order`, `location`, `section_path`, and `text_sha256` complete?
6. Does rerunning with the same input produce byte-for-byte identical JSON?

Do not count only `parsed` documents. A document can generate elements successfully but still have semantically wrong order or shifted table columns; this project does not replace a gold set.

## Integrated task: add a controlled PDF adapter

Without changing the core manifest schema, design an adapter (you may begin with an interface and a fake implementation):

1. Its input must include a controlled file handle/content version, page limit, timeout, parsing configuration, and permission context.
2. Its output contains per-page elements, page/bounding-box data, parser version, warnings, and resource use.
3. Digital pages use native extraction first; scanned pages use OCR.
4. An OCR cache key includes page hash, DPI, language pack, engine, and version.
5. Type conflicts, encryption, corruption, timeouts, zero text, and low quality each have a state.
6. Validate with a stratified gold set of at least 12 pages, and never commit real sensitive files to the repository.

Definition of done: the same input and configuration are replayable; every element returns to its original page; an unavailable external service does not publish a partial result; and critical tables and fields receive human spot checks.

## Extension exercises

1. Write the test first, then add an explicit extension and delimiter contract for TSV; do not automatically guess arbitrary dialects.
2. Add warnings for unclosed HTML blocks and skipped Markdown heading levels while retaining deterministic output.
3. Add a schema-validation step; if you introduce `jsonschema`, put it in a separate `venv` and do not commit the environment to the vault.
4. For a real business case, design the mapping between `document_id` and `source_id` and its permission inheritance.

## Mastery checklist

- [ ] I can explain the object and purpose of every hash layer in a manifest.
- [ ] I can distinguish syntactic parsing success, quality acceptance, and publication eligibility.
- [ ] I can read `pass/review_required/fail` and do not ignore non-zero exit codes.
- [ ] I can write success, disguise, corruption, over-limit, and determinism tests for a new format.
- [ ] I can state clearly that the standard-library project has not validated PDF/OCR content quality.
- [ ] I can design combined acceptance using automated metrics and a human gold set.

## References

- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [Python `unittest`](https://docs.python.org/3.11/library/unittest.html)
- [Python `hashlib`](https://docs.python.org/3.11/library/hashlib.html)
- [Python `csv`](https://docs.python.org/3.11/library/csv.html)
- [Python `json`](https://docs.python.org/3.11/library/json.html)
- [Python `html.parser`](https://docs.python.org/3.11/library/html.parser.html)

Sources retrieved on 2026-07-22. Return to [[document-parsing/00-index|Document Parsing]]; the next course is [[knowledge-base-construction/00-index|Knowledge Base Construction]].
