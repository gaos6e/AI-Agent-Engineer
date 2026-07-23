---
title: "Project: Structured OCR Result Audit"
tags:
  - ai-agent-engineer
  - ocr
  - project
aliases:
  - OCR audit project
source_checked: 2026-07-22
lang: en
translation_key: OCR/03-项目与自测/08-项目-结构化OCR结果审计.md
translation_source_hash: 7d396c08fedd6db3044b86d40cdddd883215c8bad75fb358d055462fa54006ed
translation_route: zh-CN/OCR/03-项目与自测/08-项目-结构化OCR结果审计
translation_default_route: zh-CN/OCR/03-项目与自测/08-项目-结构化OCR结果审计
---

# Project: Structured OCR Result Audit

## Project objective

Install no OCR engine and read no real images. Instead, audit an anonymized structured-result fixture. This makes the result contract, reading order, text error, low-confidence review, and table structure into stable regression gates.

Assets:

- [[ocr/project-and-self-check/examples/ocr_fixture.json|ocr_fixture.json]]: anonymized, manually written input and reference answers.
- [[ocr/project-and-self-check/examples/audit_ocr_fixture.py|audit_ocr_fixture.py]]: uses only the Python 3 standard library.
- [[ocr/project-and-self-check/examples/test_contract_and_cli.py|test_contract_and_cli.py]]: regression tests for strict JSON, the input contract, metrics, audit behavior, and the CLI.

## Run it

In PowerShell 7, run the following from the project root that contains both **docs-EN/** and **.website/**:

~~~powershell
Push-Location -LiteralPath 'docs-EN\ocr\project-and-self-check\examples'
python -B .\audit_ocr_fixture.py .\ocr_fixture.json
python -B .\audit_ocr_fixture.py --self-test
python -B -m unittest discover -s . -p 'test_*.py'
python -B -O -m unittest discover -s . -p 'test_*.py'
python -B -W error -m unittest discover -s . -p 'test_*.py'
Pop-Location
~~~

The **-B** option prevents **__pycache__** and **.pyc** creation. The program only reads the fixture and writes its report to standard output; it changes no files. The current regression suite contains **74 tests**. Normal mode, **-O**, and warnings-as-errors mode should all pass.

## Input and exit-code contract

The loader requires strict UTF-8 JSON. It rejects duplicate keys, **NaN/Infinity**, unknown fields, out-of-range coordinates, and incorrect types. The top level must contain exactly **schema_version**, **document_id**, **review_threshold**, and **pages**. Pages, blocks, and tables also use closed field sets. This is a teaching contract, not any OCR product's native output format.

- Exit code **0**: the contract is valid and no audit-level error is found. Low confidence or a critical-field mismatch can enter the review queue without making the program fail.
- Exit code **1**: the contract is valid, but an audit error such as duplicate block IDs, duplicate per-page order, or reverse order was found.
- Exit code **2**: a file, UTF-8, JSON, or input-contract error occurred.

## How to read the report

- **cer/wer**: edit error rates against the reference text. When the reference sequence is empty and the prediction is nonempty, the value is **null** because there is no usable denominator. Review it separately as an unexpected-output slice.
- **order_valid**: whether block order is unique and increasing on each page.
- **table_structure_match**: whether reference and prediction have the same row and column counts.
- **review_queue**: blocks below the threshold or failing a critical-field check.
- **errors**: audit-level errors after the contract passes. Their presence makes the program return exit code **1**.

## Extension tasks

1. Duplicate one block and confirm that the script rejects the repeated **block_id**.
2. Change one **order** to an already used value and confirm that ordering validation fails.
3. Add an anonymized vertical-text slice and a **document_type** field, then summarize CER by type.
4. Add format validation for a critical amount while preserving **raw_text**.

## Acceptance criteria

- [ ] I can explain how dynamic programming calculates edit distance.
- [ ] I can identify the real OCR capabilities the script does not validate: imaging, detection boxes, and model inference are not run.
- [ ] I can add schema validation and a failing case for a new field.
- [ ] The default fixture returns exit code **0**; a deliberately introduced audit error returns **1**; a broken contract field returns **2**.
- [ ] All 74 tests pass in normal, **-O**, and warnings-as-errors modes, and the working tree has no cache or output files.

## Common questions

- **CER is low but the table is unusable**: inspect structural matching and cell position, not text alone.
- **WER differs from expectation**: the script tokenizes on whitespace; Chinese and other languages require an explicit tokenizer.
- **The confidence threshold is difficult to set**: the fixture threshold is only a demonstration. Production thresholds need calibration on a representative validation set.

After finishing, return to the [[ocr/00-index|OCR index]], then consider how to connect the audit report to [[evaluation-framework/00-index|Evaluation Framework]].
