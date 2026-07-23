---
title: "Project: Agent Run-Log Cleaning"
tags:
  - ai-agent-engineer
  - data-quality
  - project
aliases:
  - Agent log cleaning project
source_checked: 2026-07-14
source_baseline:
  - Python 3 csv, datetime, tempfile and unittest documentation
  - RFC 4180 and RFC 3339
lang: en
translation_key: 数据清洗/07-项目-Agent运行日志清洗.md
translation_source_hash: 4f638aeb24676098721872ec39b7023595c945b0710d4b4c3a74843af31c92c5
translation_route: zh-CN/数据清洗/07-项目-Agent运行日志清洗
translation_default_route: zh-CN/数据清洗/07-项目-Agent运行日志清洗
---

# Project: Agent Run-Log Cleaning

## Goal

Split [[data-cleaning/examples/dirty_agent_runs.csv|dirty_agent_runs.csv]], which intentionally contains whitespace, duplicate IDs, invalid status, missing fields, and unusual latency, into clean data and an issue report. [[data-cleaning/examples/clean_agent_runs.py|clean_agent_runs.py]] uses only the Python standard library. Learn the contract, audit, and release boundaries first, then migrate the approach to pandas if needed. [[data-cleaning/examples/test_clean_agent_runs.py|test_clean_agent_runs.py]] fixes ten normal, boundary, and failure behaviors.

## Environment and execution

Run this from the repository root on Windows 11 / PowerShell 7. Keep the virtual environment outside the repository and outputs in a temporary directory. The script compares absolute paths and always rejects any case where input, clean output, or issue report refer to the same file.

~~~powershell
$exampleDir = (Resolve-Path '.\docs-EN\data-cleaning\examples').Path
$venv = Join-Path $env:LOCALAPPDATA 'Gao-venvs\data-cleaning'
$python = Join-Path $venv 'Scripts\python.exe'
$runDir = Join-Path $env:TEMP 'gao-agent-log-cleaning'
$out = Join-Path $runDir 'clean_agent_runs.csv'
$report = Join-Path $runDir 'agent_run_issues.csv'

py -3.11 -m venv $venv
& $python -m pip --version
New-Item -ItemType Directory -Path $runDir -Force | Out-Null
& $python -B (Join-Path $exampleDir 'clean_agent_runs.py') --input (Join-Path $exampleDir 'dirty_agent_runs.csv') --output $out --report $report --overwrite
Get-Content -LiteralPath $out
Get-Content -LiteralPath $report
& $python -B -m unittest discover -s $exampleDir -p 'test_*.py' -v
& $python -B -O -m unittest discover -s $exampleDir -p 'test_*.py' -v
~~~

The project has no third-party dependency; **pip --version** only confirms the interpreter's ownership. **--overwrite** explicitly permits replacing an existing output or report. Even with the option, overlap with the input path is rejected. Outputs live under **%TEMP%**, so the repository receives no generated artifacts.

## Expected result and explanation

The teaching input has eight rows: three accepted and five quarantined. The command-line summary should contain:

~~~text
accepted=3 rejected=5 reasons=duplicate:run_id=1,invalid:latency_ms_range=1,invalid:started_at=1,invalid:status=1,missing:run_id=1
~~~

The clean file retains **run-001**, **run-002**, and **run-003**. It normalizes **2026-07-13T09:02:00+08:00** to **2026-07-13T01:02:00Z**. The issue report stores only the original CSV end-line number, normalized **run_id**, stable reason code, and SHA-256 of the raw row; it does not copy query body text.

> [!warning] A digest is not anonymization
> **row_sha256** supports verification and correlation of the same raw row, but it does not automatically remove enumeration risk for low-entropy values. A real system still needs restricted report access, minimization of **run_id**, and a retention period.

## Rules

- The header must match the names and order of five fields exactly, so unknown columns are not silently dropped.
- Identifiers, status, time, and latency trim leading/trailing whitespace. Query normalizes only line endings and outer whitespace while preserving internal repeated whitespace.
- Map **ok/failed/canceled** to the fixed enumeration **success/error/cancelled**.
- Timestamps must parse and carry a time zone; output uses UTC **Z** and preserves microsecond precision when supplied.
- Latency must be a decimal integer in **0..300000**. **-5** is a range error; **1_000** is a representation/type error.
- **run_id**, **started_at**, **status**, **latency_ms**, and **query** are all required in this exercise.
- A **run_id** occupies its identity on first appearance even if that row is later invalid. Any later row with the same ID enters the issue report; a “cleaner” later record must not silently rewrite history.
- Both outputs are written completely to temporary files in the target directory before replacement, and are byte-for-byte reproducible for the same input and rules.

## Verification for this version

> [!success] Verified on 2026-07-14
> Under Python 3.11.9, **py_compile** passed; ten **unittest** cases passed in normal and **-O** modes. Normal and **-O** CLI stdout, clean CSV, and issue report matched respectively; the source fixture hash was unchanged; temporary validation directories and project **__pycache__** were cleaned.

The tests cover UTC conversion, internal query whitespace, status mapping, the identity policy for an initially invalid ID, stable reason codes, the 3/5 fixture split, byte-for-byte idempotency, explicit overwrite/path overlap, strict schema, and CLI summary behavior.

## Acceptance and extensions

- [ ] The clean file contains only valid, unique IDs.
- [ ] The issue report contains original row numbers and explicit reason codes.
- [ ] After modifying input and rerunning, rules and results remain explainable.
- [ ] Add a **model** field and allowlist, then add a rule for an unknown model.
- [ ] Compare the effect of rejecting anomalous latency with retaining and marking it on p95.
- [ ] Remove **--overwrite**, verify that existing output is rejected, then explain why this is the safe default.
- [ ] Add a query with multiline Markdown or code and show that internal whitespace is not collapsed.

## Self-check

1. Why must an invalid latency not always become zero?
2. Why can duplicate **run_id** not always keep the last record?
3. Which normalizations can run before splitting, and which statistical imputations can fit only on training data?
4. How can you prove that the script did not overwrite its source?

Completion standard: run the script, explain every rejection reason, and write one new contract rule with its corresponding test sample.

Return to the [[data-cleaning/00-index|Data Cleaning index]].

## References

Sources were checked on 2026-07-14.

- [Python csv](https://docs.python.org/3/library/csv.html)
- [Python datetime](https://docs.python.org/3/library/datetime.html)
- [Python tempfile](https://docs.python.org/3/library/tempfile.html)
- [RFC 4180: CSV](https://www.rfc-editor.org/rfc/rfc4180)
- [RFC 3339: Internet timestamps](https://www.rfc-editor.org/rfc/rfc3339)
