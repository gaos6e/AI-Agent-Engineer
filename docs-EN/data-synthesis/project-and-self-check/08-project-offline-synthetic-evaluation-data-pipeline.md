---
title: "Project: Offline Synthetic Evaluation Data Pipeline"
aliases:
  - Offline Synthetic Evaluation Data Project
  - Synthetic Data Python Project
tags:
  - synthetic-data
  - project
  - Python
source_checked: 2026-07-22
lang: en
translation_key: "数据合成/03-项目与自测/08-项目-离线合成评测数据流水线.md"
translation_source_hash: 081bb1b5027a6278e0abed62a3a23712263a73685b15799ddd4c9eb810839393
translation_route: zh-CN/数据合成/03-项目与自测/08-项目-离线合成评测数据流水线
translation_default_route: zh-CN/数据合成/03-项目与自测/08-项目-离线合成评测数据流水线
---

# Project: Offline Synthetic Evaluation Data Pipeline

## Project goal

Use Windows 11, PowerShell 7, and Python 3 standard library to build a synthetic-evaluation-data pipeline with no network, model call, real data, or key:

- strictly parse and validate a versioned JSON spec, rejecting duplicate keys, `NaN`, unknown fields, and booleans masquerading as numbers;
- generate candidates with stable ID, family, label, and provenance from a language × scenario condition matrix;
- quarantine Schema/source errors, likely personal information, and normalized exact duplicates while retaining rejection reason;
- split development/test by family and verify condition coverage and integrity;
- use a frozen quality gate that returns `PASS`, `REVIEW`, or `BLOCK`, with a separate exit code for contract error;
- generate content fingerprint, manifest, and limitation list, with 43 tests for critical boundaries.

> [!warning] Interpretation boundary
>
> Every text is an author-designed fictional template. `contains_real_data: false` is a source declaration, not a claim about similarity to every external corpus. Regex scanning and exact deduplication are not anonymization. The project has no real holdout, generator model, near-duplicate model, or differential-privacy mechanism, so it cannot claim production utility, distribution representativeness, absence of copyright risk, or a privacy guarantee.

## Project files

- [[data-synthesis/examples/build_synthetic_evalset.py|build_synthetic_evalset.py]]: strict contract, generation, filtering, deduplication, split, quality gate, and CLI;
- [[data-synthesis/examples/synthesis_spec.json|synthesis_spec.json]]: normal data contract and condition matrix;
- [[data-synthesis/examples/synthesis_spec_quality_regression.json|synthesis_spec_quality_regression.json]]: contract-valid but with a too-strict condition-coverage gate, demonstrating `BLOCK`;
- [[data-synthesis/examples/synthesis_spec_contract_error.json|synthesis_spec_contract_error.json]]: intentionally unknown field, demonstrating contract error;
- [[data-synthesis/examples/test_build_synthetic_evalset.py|test_build_synthetic_evalset.py]]: 43 standard-library `unittest` cases.

## Environment

The project has no third-party dependency. If an isolated environment helps practice, create it outside the vault:

```powershell
$syntheticDataVenv = Join-Path $env:TEMP 'ai-agent-engineer-synthetic-data-venv'
python -m venv $syntheticDataVenv
& (Join-Path $syntheticDataVenv 'Scripts\Activate.ps1')
# This project needs no pip install.
```

From the project root containing both `docs-EN/` and `.website/`, enter the example directory:

```powershell
$projectDir = (Resolve-Path -LiteralPath 'docs-EN\data-synthesis\examples').Path
Push-Location -LiteralPath $projectDir
```

All following commands use `-B` to avoid generating `__pycache__` or `.pyc` in the knowledge base.

## Strict spec contract

The spec turns implicit data-engineering decisions into auditable input:

| Area | Meaning | Does not replace |
| --- | --- | --- |
| Dataset ID/version/Schema | Identifies release and compatibility boundary | Content quality |
| Purpose/non-goals | Bounds supported uses and exclusions | Real-utility test |
| Generator | Type, version, checked date, real-data contact | Authorization or anonymity proof |
| Split | Seed and development-family count | Random per-row split |
| Quality gates | Per-cell/total/duplicate/coverage gates | Human labels and real holdout |
| Teaching faults | Whether traceable bad candidates are injected | Real failure distribution |
| Conditions | Language, scenario, oracle, criticality, and templates | Production incidence rate |

The loader rejects duplicate JSON keys and nonstandard `NaN/Infinity`. Fields match exactly at every layer. Numeric gates reject `true/false` because booleans subclass integers in Python and could otherwise silently become `1`.

## Generation, quarantine, and deduplication

The normal spec defines two languages × three scenarios × two templates per cell, producing 12 valid candidates. The script additionally injects:

1. one candidate with identical content but a different ID, to verify normalized-exact deduplication;
2. one candidate missing `expected_action`, to verify contract quarantine.

The `zh-CN` templates intentionally remain Chinese fixture inputs: they are records in a language condition under test, rather than untranslated explanatory prose.

Every candidate has `candidate_id`, `family_id`, condition, input, oracle, critical flag, `synthetic: true`, and provenance. Provenance does not merely require field presence: generator type/version, real-data declaration, condition-prefix of template ID, and variable mapping must agree with the frozen spec. This prevents an old generator or template from another condition posing as this batch. It remains a technical trace, not proof of authorization, copyright, or anonymity. Filtering order is:

1. exact field/Schema and oracle consistency;
2. provenance fields and real-data declaration;
3. teaching email/phone-pattern scan;
4. candidate-ID uniqueness;
5. exact deduplication of language, scenario, and normalized input.

Rejected items enter `rejection_log` with stage and reason. A clean scan only says this rule set found nothing; it cannot establish no personal information. Near duplication and semantic copying still require additional tools and human review.

## Family split and quality gates

Variants of a language/scenario/template family enter development or test together so near rewrites do not cross. After splitting, verify unique IDs, unique normalized input, no family across splits, both splits present, full condition-cell coverage, every record synthetic, and complete provenance.

The quality-gate order is:

1. Missing condition, too few records per cell, too few total records, or unreviewed real-source declaration → `BLOCK`.
2. Duplicate fraction above the soft gate → `REVIEW`.
3. Every frozen gate passes → `PASS`.
4. Invalid file, JSON, or Schema → contract error and no data report.

`BLOCK` means the pipeline ran successfully but release is disallowed. A contract error means the precondition for comparison/generation itself did not hold. Do not combine them as “script failure.”

## Run the normal spec

```powershell
python -B .\build_synthetic_evalset.py --spec .\synthesis_spec.json
if ($LASTEXITCODE -ne 0) { throw 'PASS fixture exit code mismatch' }
```

Expected:

- `action=PASS` and exit code `0`;
- `raw=14`, `contract_rejected=1`, `duplicate_rejected=1`, `released=12`;
- two retained records in each of six condition cells;
- two families/four records in development and four families/eight records in test;
- a `sha256:` content fingerprint in the manifest;
- JSON on stdout and no output file.

## Run a quality regression

```powershell
python -B .\build_synthetic_evalset.py `
  --spec .\synthesis_spec_quality_regression.json
if ($LASTEXITCODE -ne 1) { throw 'quality regression exit code mismatch' }
```

The spec and generation logic are valid, but it freezes `min_records_per_cell` at 3 while each cell has 2. Expected result is `action=BLOCK` and exit code `1`. This proves that successfully generating many lines does not satisfy a release gate.

## Run a contract error

```powershell
python -B .\build_synthetic_evalset.py `
  --spec .\synthesis_spec_contract_error.json
if ($LASTEXITCODE -ne 2) { throw 'contract error exit code mismatch' }
```

This fixture deliberately has an unknown top-level field. Expected stderr describes field mismatch, stdout is empty, and exit code is `2`.

CLI contract:

- `0`: `PASS`;
- `1`: `REVIEW` or `BLOCK`;
- `2`: file, JSON, field, type, or value contract error.

## Three-mode tests and syntax check

```powershell
python -B -m unittest -v test_build_synthetic_evalset
if ($LASTEXITCODE -ne 0) { throw 'normal tests failed' }

python -B -O -m unittest -v test_build_synthetic_evalset
if ($LASTEXITCODE -ne 0) { throw 'optimized tests failed' }

python -B -W error -m unittest -v test_build_synthetic_evalset
if ($LASTEXITCODE -ne 0) { throw 'warnings-as-errors tests failed' }

python -B -c "from pathlib import Path; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in map(Path, ('build_synthetic_evalset.py', 'test_build_synthetic_evalset.py'))]"
if ($LASTEXITCODE -ne 0) { throw 'syntax check failed' }
Pop-Location
```

Tests cover duplicate keys, `NaN`, unknown/missing fields, Boolean numeric values, invalid gates, empty template, candidate/source errors, mismatched generator version/template lineage/variable mapping, likely personal information, duplicate ID, family split, coverage, PASS/REVIEW/BLOCK, real-source hard gate, fingerprint, and three CLI exit-code classes. Production code does not use `assert`, so `-O` does not remove critical validation.

## Hands-on exercises

1. Set `max_duplicate_fraction` to `0.01` and verify `REVIEW` rather than `BLOCK`.
2. Add a `tool-timeout` condition with oracle, critical flag, and two templates; explain which scenario combinations have business meaning.
3. Add email-shaped content to one candidate, verify it enters the rejection log, and explain why that is not a complete PII scan.
4. Design an n-gram/Embedding candidate-pair report, but leave final merge to evidence-based rules or human review.
5. Prepare an authorized real small holdout that participates in neither generation nor tuning, then design a utility experiment on system error patterns.
6. Before using real logs, draw authorization, minimization, retention, access, deletion, and release approval flow. Do not disable the hard gate merely to make `contains_real_data` work.

## Self-check

1. Why is `contains_real_data: false` not proof of anonymity?
2. Why can duplicate fraction be a soft gate while missing critical conditions are usually a hard gate?
3. What can and cannot a fixed seed guarantee?
4. Why must rewrites in one family not cross development/test?
5. What can and cannot a changed fingerprint establish?
6. After 43 tests pass, why can we still not claim that data improves training on a real model?

## Mastery check

- [ ] I can explain the responsibility of spec, candidate, released record, rejection log, and manifest.
- [ ] I can distinguish sample-contract error, dataset-quality BLOCK, and soft-gate REVIEW.
- [ ] I can prove family split and condition coverage are checked by code.
- [ ] I can run 43 tests and three CLI scenarios and explain exit codes.
- [ ] I can name remaining boundaries for near duplication, real utility, privacy, license, and human review.
- [ ] I do not present synthetic, hash, scanning, or no-real-input declaration as a formal privacy guarantee.

## Project boundary and next step

This project builds a transparent reproducible template-synthesis baseline. When connecting model generation, retain the same contract, provenance, rejection log, and independent validation, then return to [[data-synthesis/foundations-and-design/03-model-generation-and-condition-coverage|Model Generation and Condition Coverage]]. Before formal release, use independent real evidence from [[data-synthesis/methods-and-quality/05-quality-utility-and-real-data-calibration|Quality, Utility, and Real-Data Calibration]], then complete risk and maintenance approval through [[data-synthesis/methods-and-quality/06-privacy-memorization-bias-and-copyright|Privacy, Memorization, Bias, and Copyright]] and [[data-synthesis/methods-and-quality/07-versioning-evaluation-and-release|Versioning, Evaluation, and Release]].

## References

- [SELF-INSTRUCT original paper](https://aclanthology.org/2023.acl-long.754/) — accessed 2026-07-22.
- [NIST SDNist Synthetic Data Report Tool](https://www.nist.gov/services-resources/software/sdnist-synthetic-data-report-tool) — v1.4 utility/privacy multidimensional-reporting example; accessed 2026-07-22.
- [NIST SP 800-226](https://doi.org/10.6028/NIST.SP.800-226) — differential-privacy claim and implementation-risk boundary; final 2025-03.
- [Google Data Cards official paper page](https://research.google/pubs/data-cards-purposeful-and-transparent-dataset-documentation-for-responsible-ai/) — accessed 2026-07-22.
