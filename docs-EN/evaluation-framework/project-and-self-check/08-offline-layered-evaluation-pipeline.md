---
title: "Project: Offline Layered Evaluation Pipeline"
aliases:
  - Offline Layered Evaluation Project
tags:
  - evaluation
  - project
source_checked: 2026-07-22
execution_verified: 2026-07-22
content_origin: original
content_status: validated
source_baseline: "Offline Python 3 standard-library fixtures and 43 unittest
  cases; OpenAI, Anthropic, NIST, and IETF methodological material through
  2026-07-22"
lang: en
translation_key: 评测体系/03-项目与自测/08-项目-离线分层评测流水线.md
translation_source_hash: 7ab61c0c6cb67cd672803a227119e6ab6563169fce5df2c9025a3124d1d13dcc
translation_route: zh-CN/评测体系/03-项目与自测/08-项目-离线分层评测流水线
translation_default_route: zh-CN/评测体系/03-项目与自测/08-项目-离线分层评测流水线
---

# Project: Offline Layered Evaluation Pipeline

## Project goal

Using Windows 11, PowerShell 7, and the Python 3 standard library, build a release-evaluation chain that stays offline, makes no model call, and needs no key:

- strictly validate JSON contracts for dataset, rubric, and predictions;
- check unique IDs, train/development/test isolation, family-level leakage, and frozen-test coverage;
- run deterministic graders for labels, tools, evidence, and prohibited actions;
- calculate confusion matrix, precision, recall, F1, mean, p95, and slice gaps;
- report uncertainty of a candidate versus baseline with fixed-seed paired bootstrap;
- make BLOCK for critical safety or privacy cases take precedence over an overall mean;
- output evaluator version, a complete SHA-256 evidence digest with digest encoding format, a display-only short fingerprint, and stable CLI exit codes, verified by 43 tests.

> [!warning] Interpretation boundary
> The dataset has only six frozen test cases, all synthetic teaching material. Its results cannot estimate production performance of any real system. A small-sample slice gap is not a fairness conclusion, and estimated cost is not a vendor bill.

## Project files

- [evaluate_agent_outputs.py](evaluation-framework/examples/evaluate_agent_outputs.py): contract validation, graders, metrics, bootstrap, and gate CLI.
- [eval_dataset.json](evaluation-framework/examples/eval_dataset.json): a versioned dataset with train, development, and test splits.
- [eval_rubric.json](evaluation-framework/examples/eval_rubric.json): frozen metrics, thresholds, baseline, and bootstrap configuration.
- [predictions_pass.json](evaluation-framework/examples/predictions_pass.json): normal candidate and baseline.
- [predictions_regression.json](evaluation-framework/examples/predictions_regression.json): a candidate that remains above overall thresholds but fails a critical safety case.
- [eval_dataset_contract_error.json](evaluation-framework/examples/eval_dataset_contract_error.json): an invalid fixture deliberately reusing a `family_id` across splits.
- [test_evaluate_agent_outputs.py](evaluation-framework/examples/test_evaluate_agent_outputs.py): standard-library `unittest` coverage.

## Environment setup

The script has no third-party dependency and runs with Python 3 directly. To practice a standard isolation workflow, create the virtual environment outside the vault:

```powershell
$venvDir = Join-Path $env:TEMP "ai-agent-engineer-evaluation-venv" # Put the temporary virtual environment in the system temp directory, outside the knowledge base.
python -m venv $venvDir # Create an isolated interpreter; this example needs no network dependency installation.
& (Join-Path $venvDir "Scripts\Activate.ps1") # Activate it so later python commands point to that interpreter.
# This project has no third-party dependency, so no pip install is needed.
```

From the project root containing `docs-EN/` and `.website/`, enter the examples directory:

```powershell
$projectDir = (Resolve-Path -LiteralPath 'docs-EN\evaluation-framework\examples').Path # Resolve the examples directory to an absolute path so terminal location cannot change meaning.
Push-Location -LiteralPath $projectDir # Enter temporarily; Pop-Location will restore the original location at the end.
```

Every Python command uses `-B` to prevent `__pycache__` or `.pyc` from being created in the knowledge base.

## Strict contracts

### Dataset

Every case has `id`, `family_id`, split, slice, critical flag, teaching input, expected binary label, expected tool, prohibited actions, and evidence requirement. The validator requires:

- exact top-level and case fields, so spelling mistakes or extras are not silently ignored;
- unique IDs and the presence of all `train`, `development`, and `test` splits;
- each `family_id` in exactly one split, blocking leakage among sessions, documents, and paraphrased samples;
- a release gate to read only test cases with `frozen_test: true`.

### Rubric

The rubric freezes positive label, baseline release, test split, quality/slice/latency/cost gates, plus bootstrap sample count, seed, and confidence. Numbers must be representable as finite Python `float` values; oversized JSON integers and nonfinite values become contract errors, and Booleans cannot masquerade as `0/1` numbers.

### Predictions

Each release must cover exactly the frozen test IDs. Structured records contain a predicted label, tool, actions, whether evidence is present, latency, and estimated cost. A missing or unknown case, duplicate release or action, or mismatched dataset version produces a contract error.

### Observation-source and system-under-test boundary

`predictions_*.json` contains **prewritten synthetic teaching fixtures**, not facts collected by this script from a running Agent. Here, `tool`, `actions`, and `evidence_present` are controlled observations for grader practice. The validator can only check their consistency with the contract; it cannot prove that they came from real tools, environment state, or an untampered candidate.

A production harness must collect model-generated text and call requests separately from tool receipts, traces, and final environment state produced by trusted executors. Evaluation input must also bind to an immutable release manifest containing code, prompt, retrieval index, tools, policy, and runtime configuration, protected by controlled storage, access control, and, where needed, signatures or attestations. This project neither runs an SUT nor collects these observations nor verifies artifact origin. A `PASS` must not be treated as real release approval.

### Decision evidence

The stdout JSON includes `evaluator_version`, `evidence_digest_format`, a 64-character `evidence_sha256`, and its first 16 characters as `evidence_fingerprint`. The full digest binds evaluator version, dataset, rubric, predictions, and candidate release; the short fingerprint is for human reading only. The example's format is `python-json-sorted-utf8-v1`: it serializes values with `json.dumps(ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)`, encodes UTF-8, and computes SHA-256. It is useful for recomputation by the same implementation. Raw invalid UTF-8 bytes, escaped lone surrogates, nonfinite values, and numbers that cannot become finite `float` values are rejected as controlled contract errors when read or validated. Fixed golden-vector tests lock this byte representation and format label so this repository's release-gate and monitoring projects can verify the same teaching profile.

It **is not** a cross-language JSON-normalization standard. Cross-release approval, Canary, or later monitoring windows must pass the complete digest and its encoding format and verify identical bytes. A real cross-language hashing or signing requirement needs an explicitly agreed and tested specification, such as RFC 8785 JCS; do not call this Python teaching format canonical JSON. A digest still cannot replace signatures, provenance verification, or human approval. See [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and the Regression Loop]] for the handoff boundary.

## Graders and metrics

Every test case has four deterministic checks:

1. The binary label is correct.
2. The tool matches the expectation.
3. Actions avoid all prohibited items.
4. Evidence is explicitly present when required.

All four must pass for a case to pass; the report retains each check for diagnosis. Predicted labels separately form TP/FP/TN/FN and produce precision, recall, and F1. Latency reports mean and nearest-rank p95. Cost is only a teaching estimate stored in fixtures.

Candidate and baseline are paired on the same test cases. Per-case pass differences enter a fixed-seed bootstrap. The interval demonstrates uncertainty; it does not turn six hand-authored cases into a random population sample.

## Gate priority

The decision order is explicit in code and tests:

1. Any failed critical safety or privacy case is `BLOCK`.
2. Failed critical slice, overall pass rate, precision, recall, or F1 hard gate is also `BLOCK`.
3. Slice gap, mean/p95 latency, estimated cost, or bootstrap lower bound can trigger `REVIEW`.
4. Only when all gates pass is the result `PASS`.

The regression fixture deliberately gives the candidate overall pass rate `5/6≈0.833` and F1 `1.0`, both at or above frozen quality gates, but it executes the prohibited `refund_order` action. Therefore its primary reason remains the critical safety failure and it must be `BLOCK`.

## Run the normal candidate

```powershell
python -B .\evaluate_agent_outputs.py # Run the normal candidate; -B prevents __pycache__ writes.
if ($LASTEXITCODE -ne 0) { throw "PASS fixture exit code mismatch" } # A PASS scenario must finish successfully with 0.
```

Expected: `action=PASS`, baseline pass rate approximately `0.667`, candidate pass rate `1.0`, paired difference approximately `0.333`, 95% teaching bootstrap interval `[0.0, 0.667]`, and candidate p95 `1010 ms`. Output is stdout JSON and writes no file.

## Run the critical regression

```powershell
# The backtick must be the last character on its line, so its explanation is on the preceding line rather than after a continuation.
python -B .\evaluate_agent_outputs.py `
  --predictions .\predictions_regression.json `
  --candidate candidate-regression # Inject the critical-safety regression fixture and use a readable candidate release ID.
if ($LASTEXITCODE -ne 1) { throw "regression fixture exit code mismatch" } # BLOCK or REVIEW is a controlled release rejection, so it must return 1.
```

Expected: `action=BLOCK` and a primary reason containing `test-safety-negative`. Exit code `1` means evaluation completed and rejected release; it is not a script crash.

## Run the invalid contract

```powershell
# Deliberately switch to an invalid dataset so an input-contract error is not mistaken for an ordinary metric failure.
python -B .\evaluate_agent_outputs.py `
  --dataset .\eval_dataset_contract_error.json # Point to the fixture with cross-split family leakage.
if ($LASTEXITCODE -ne 2) { throw "contract-error fixture exit code mismatch" } # Schema or data errors must stably return 2.
```

Expected stderr identifies `split leakage`. The CLI exit-code contract is:

- `0`: `PASS`;
- `1`: `REVIEW` or `BLOCK`;
- `2`: file, JSON, schema, version, coverage, or argument contract error.

## Four-mode tests

Ordinary mode, optimized mode with `assert` disabled, warnings-as-errors, and their combination must all pass:

```powershell
python -B -m unittest -v test_evaluate_agent_outputs # Discover and run every unit test under the ordinary interpreter.
if ($LASTEXITCODE -ne 0) { throw "normal tests failed" } # Any test failure stops this validation script.

python -B -O -m unittest -v test_evaluate_agent_outputs # Repeat with -O to prove production validation does not depend on removable bare assert.
if ($LASTEXITCODE -ne 0) { throw "optimized tests failed" } # Optimized mode must retain the same behavior.

python -B -W error -m unittest -v test_evaluate_agent_outputs # Promote warnings to errors and reveal deprecation or resource problems.
if ($LASTEXITCODE -ne 0) { throw "warnings-as-errors tests failed" } # Warnings cannot be silently ignored.

python -B -O -W error -m unittest -v test_evaluate_agent_outputs # Combine the strict interpreter and warning conditions.
if ($LASTEXITCODE -ne 0) { throw "optimized warnings-as-errors tests failed" } # All four modes must pass before the basic regression is reliable.
```

Then perform a syntax check that creates no cache:

```powershell
python -B -c "from pathlib import Path; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in map(Path, ('evaluate_agent_outputs.py', 'test_evaluate_agent_outputs.py'))]" # Compile both files in memory only, without creating .pyc.
if ($LASTEXITCODE -ne 0) { throw "syntax check failed" } # Syntax errors must fail before leaving the examples directory.
Pop-Location # Restore the working directory from before entering the examples directory.
```

## Exercises

1. Add a `candidate-review` fixture that only exceeds the p95 soft gate; verify `REVIEW` and exit code `1`.
2. Place the same `family_id` in development and test, then explain why it remains leakage even if its text differs.
3. Add a critical privacy case and first write a failing test proving that a high overall mean must still `BLOCK`.
4. Make one release omit a test case and confirm the validator rejects it rather than calculating a prettier score from remaining cases.
5. Change row-level bootstrap to sample by `family_id`; explain why the result is identical here when every test family has one case.

## Self-check questions

1. Why can candidate F1 equal 1.0 and still be BLOCKed by a safety gate?
2. Why isolate train, development, and test by family rather than random row?
3. Why should precision be undefined rather than 0 when its denominator is zero?
4. What does a fixed random seed guarantee, and what does it not guarantee?
5. Why cannot an evidence fingerprint replace data-origin authenticity or access control?

## Mastery checklist

- [ ] I can explain the three versioned contracts: dataset, rubric, and predictions.
- [ ] I can calculate precision, recall, and F1 from a confusion matrix.
- [ ] I can state evidence boundaries for mean, p95, slice gap, and bootstrap interval.
- [ ] I can prove that a critical safety or privacy failure outranks an overall quality mean.
- [ ] I can run 43 tests and three CLI scenarios in all four interpreter/warning modes and explain distinct uses of full digest, short fingerprint, digest format, and exit code.
- [ ] I can list human calibration, online progressive rollout, privacy, and governance that a real project still needs.

## Project boundary and next step

This project validates offline contracts, deterministic graders, metrics, and decision priority. It does not run an Agent under test or obtain tool receipts and final environment state from a trusted executor. It does not call a human or model judge, connect to real traces, users, monitoring backends, bills, or online experiments, and cannot make fairness or compliance conclusions. Its local sorted-JSON serialization is not a cross-language normalization or signature protocol. A real release also needs [[evaluation-framework/methods-and-quality/07-evaluation-reporting-audit-and-governance|Evaluation Reporting, Audit, and Governance]], [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Evidence Handoff and the Regression Loop]], and the progressive-rollout guardrails in [[runtime-monitoring/00-index|Runtime Monitoring]].

## References

- [OpenAI Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) — checked 2026-07-22; methodological reference while the Evals platform is in transition.
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — published 2026-01-09; checked 2026-07-22.
- [NIST/SEMATECH: Confidence intervals](https://www.itl.nist.gov/div898/handbook/prc/section1/prc14.htm) — checked 2026-07-22.
- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) — checked 2026-07-22.
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html) — cross-system hash/signature interoperability needs explicit normalization; this example uses only a versioned local serialization.
