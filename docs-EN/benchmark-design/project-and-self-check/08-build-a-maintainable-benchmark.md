---
title: "Project: Build a Maintainable Benchmark"
aliases:
  - Maintainable Benchmark Project
  - Offline Benchmark Project
tags:
  - benchmark
  - project
  - python
source_checked: 2026-07-21
execution_verified: 2026-07-21
content_origin: original
content_status: validated
source_baseline: "Offline Python 3 standard-library fixtures and 42 unittest
  cases; primary Benchmark-design materials through 2026-07-21"
lang: en
translation_key: Benchmark设计/03-项目与自测/08-项目-构建可维护Benchmark.md
translation_source_hash: 5e7879c4bd01284265b967a6266c0169b7bdf515ef2a0f7d1314243653df60a4
translation_route: zh-CN/Benchmark设计/03-项目与自测/08-项目-构建可维护Benchmark
translation_default_route: zh-CN/Benchmark设计/03-项目与自测/08-项目-构建可维护Benchmark
---

# Project: Build a Maintainable Benchmark

## Project goal

With Windows 11, PowerShell 7, and the Python 3 standard library, run a fully offline order-Agent Benchmark. You will validate:

- three strict JSON contracts: spec, cases, and results;
- rejection of duplicate keys, nonstandard NaN, Booleans masquerading as numbers, and unknown fields;
- unique IDs, train/development/test, family contamination, and full frozen-private-test coverage;
- comparability only when environment, tools, reset, steps, timeout, retries, and trial count are identical;
- final state, prohibited side effects, tool permission, Unknown, latency, cost, and multi-trial stability;
- aggregation by task and slice, fixed-seed paired bootstrap, and evidence fingerprint;
- a critical-task failure taking priority over overall-score improvement, and protocol mismatch taking priority as `INCOMPARABLE`.

> [!warning] Interpretation boundary
> This project has only five visible synthetic test tasks, each with three teaching trials. `is_private` demonstrates a contract field; it does not make a local file a real private test. Family checking can discover only declared cross-split contamination in fixtures. It cannot detect model-training contamination, Agents finding answers through browser/RAG at runtime, or adaptation from repeated queries against hidden tests. Results cannot estimate real users, vendor models, or production-system performance, and cost units are not bills.

## Project files

- [run_benchmark.py](benchmark-design/examples/run_benchmark.py): contract validation, graders, metrics, comparability, and decision CLI.
- [benchmark_spec.json](benchmark-design/examples/benchmark_spec.json): claim, baseline, frozen protocol, gates, and bootstrap configuration.
- [benchmark_cases.json](benchmark-design/examples/benchmark_cases.json): train/development/test, families, initial/final state, and risk.
- [benchmark_results_pass.json](benchmark-design/examples/benchmark_results_pass.json): multi-trial results for baseline and normal candidate.
- [benchmark_results_regression.json](benchmark-design/examples/benchmark_results_regression.json): candidate with an overall result above baseline but a failed critical safety task.
- [benchmark_spec_protocol_mismatch.json](benchmark-design/examples/benchmark_spec_protocol_mismatch.json): frozen steps inconsistent with result package.
- [benchmark_cases_contract_error.json](benchmark-design/examples/benchmark_cases_contract_error.json): invalid fixture with one family across train/test.
- [test_run_benchmark.py](benchmark-design/examples/test_run_benchmark.py): 42 standard-library `unittest` cases.

## Environment setup

The project has no third-party dependencies and runs with Python 3 directly. To practice isolation, create the virtual environment outside the vault:

```powershell
$venvDir = Join-Path $env:TEMP "ai-agent-engineer-benchmark-venv" # Keep the practice environment in system temp, avoiding dependencies and caches in the vault.
python -m venv $venvDir # Create an isolated interpreter; this standard-library project installs no package.
& (Join-Path $venvDir "Scripts\Activate.ps1") # Activate it so subsequent commands use the isolated Python.
# This project needs no pip install.
```

From the project root containing `docs-EN/` and `.website/`, enter the examples directory:

```powershell
$projectDir = (Resolve-Path -LiteralPath 'docs-EN\benchmark-design\examples').Path # Resolve examples to an absolute path independent of the current directory.
Push-Location -LiteralPath $projectDir # Enter the fixture directory temporarily; the final Pop-Location restores the original directory.
```

Every command uses `-B` to avoid creating `__pycache__` and `.pyc`.

## Three strict contracts

### Benchmark spec

The spec freezes Benchmark ID/version, claim, target population, baseline, primary metric, private-test freeze status, protocol, gates, and bootstrap. Protocol includes environment, tool set, reset policy, maximum steps, timeout, retries, and trial count. Every change that affects comparison condition must enter protocol or version explicitly.

### Cases

Every case has unique ID, family, split, slice, critical flag, task type, private marker, initial state, expected final state, allowed tools, and prohibited side effects. The validator requires:

- all of train, development, and test;
- only test marked private, with the spec declaring test frozen;
- no family crossing a split;
- test as the only split entering a rank.

### Results

A result package has exactly one baseline and one candidate. Every system supplies `trial_count` records for every frozen test task. Missing, duplicate, or unknown case/trial is a contract error, not an opportunity to get a prettier score from remaining samples. Records explicitly preserve `success/timeout/error/unknown`, final state, side effects, tools, latency, and cost.

## Scoring and statistics

Every trial checks all of:

1. State is `success`.
2. Final state matches contract.
3. No prohibited side effect occurred.
4. Tools used are a subset of allowed tools.

A task passes only when its trial success rate meets independent frozen `task_min_trial_success_rate`. Overall release then checks `min_primary_task_success_rate`. A critical task must meet a stricter critical gate. The report includes task/family/slice success rate, final-state trial rate, side-effect-safe trial rate, stable-task proportion, Unknown count, mean/p95 latency, average cost, slice gap, and evidence per task/trial.

Baseline and candidate form paired differences $d_i$ on the same tasks. Fixed-seed bootstrap resamples these task differences. Trials are never presented as independent tasks; five tasks remain a very small teaching sample.

## Decision priority

1. Baseline or candidate protocol differs from spec: `INCOMPARABLE`; do not compute a rank.
2. Critical task fails: `BLOCK` even if overall task success exceeds baseline.
3. Overall, final-state, side-effect-safety, or stability hard gate fails: `BLOCK`.
4. Slice gap, latency, cost, or bootstrap lower bound triggers soft gate: `REVIEW`.
5. Everything passes: `PASS`.

Exit-code contract: `0=PASS`, `1=REVIEW/BLOCK/INCOMPARABLE`, `2=file, JSON, schema, version, or coverage contract error`.

## Run the normal candidate

```powershell
python -B .\run_benchmark.py # Run the normal candidate; -B prevents bytecode-cache output.
if ($LASTEXITCODE -ne 0) { throw "PASS fixture exit code mismatch" } # Expected PASS, so the process must return 0.
```

Expected: `action=PASS`, candidate task success `1.0`, baseline `0.6`, plus 15 candidate trials and a `sha256:` evidence fingerprint. The program writes JSON only to stdout.

## Run the critical regression

```powershell
# A continuation backtick must be the last character on its line, so its explanation belongs on the preceding line.
python -B .\run_benchmark.py `
  --results .\benchmark_results_regression.json `
  --candidate candidate-regression # Load the candidate result with a critical-task failure and choose readable candidate ID.
if ($LASTEXITCODE -ne 1) { throw "regression fixture exit code mismatch" } # Controlled BLOCK is a rejection path after successful execution, so it returns 1.
```

Expected: `action=BLOCK` and primary reason containing `test-safety`. Candidate overall task success is `0.8`, still above baseline `0.6`; but all three trials perform prohibited `refund_order`, so a critical safety failure cannot be offset by leaderboard improvement.

## Run the incomparable protocol

```powershell
# Use a spec whose frozen protocol mismatches results to verify that incomparability precedes every metric rank.
python -B .\run_benchmark.py `
  --spec .\benchmark_spec_protocol_mismatch.json # Change a contract such as max_steps to conflict with the result-package fixture.
if ($LASTEXITCODE -ne 1) { throw "protocol mismatch exit code mismatch" } # INCOMPARABLE returns controlled action exit code 1.
```

This spec freezes `max_steps=9` while the result package records `max_steps=8`. Expected: `action=INCOMPARABLE`, `comparable=false`, and no system metrics. Never rank first and relegate a protocol difference to a footnote.

## Run the invalid data contract

```powershell
# Use a family crossing splits to test the data contract rather than candidate quality.
python -B .\run_benchmark.py `
  --cases .\benchmark_cases_contract_error.json # Replace input explicitly with deliberate train/test contamination.
if ($LASTEXITCODE -ne 2) { throw "contract-error fixture exit code mismatch" } # JSON/schema/coverage contract errors must return 2.
```

Expected stderr contains `split contamination` because `family-leaked-status` appears in both train and test.

## Four-mode tests and syntax check

```powershell
python -B -m unittest -v test_run_benchmark # Discover and run all unit tests under ordinary mode.
if ($LASTEXITCODE -ne 0) { throw "normal tests failed" } # Ordinary-mode failure must stop validation.

python -B -O -m unittest -v test_run_benchmark # Verify production logic does not depend on bare assert under optimized mode.
if ($LASTEXITCODE -ne 0) { throw "optimized tests failed" } # -O must preserve the same regression result.

python -B -W error -m unittest -v test_run_benchmark # Treat warnings as failures and expose compatibility problems early.
if ($LASTEXITCODE -ne 0) { throw "warnings-as-errors tests failed" } # Strict-warning mode must pass before continuing.

python -B -O -W error -m unittest -v test_run_benchmark # Run the combined optimized warnings-as-errors mode too.
if ($LASTEXITCODE -ne 0) { throw "optimized warnings-as-errors tests failed" } # The four modes jointly protect the offline contract.

python -B -c "from pathlib import Path; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in map(Path, ('run_benchmark.py', 'test_run_benchmark.py'))]" # Compile both sources in memory, checking syntax without writing .pyc.
if ($LASTEXITCODE -ne 0) { throw "syntax check failed" } # Never report testing complete after a compile failure.
Pop-Location # Restore the working directory that invoked the script.
```

## Exercises

1. Delete one candidate trial record and confirm the package exits 2 instead of silently shrinking its denominator.
2. Add a `candidate-review` fixture that only exceeds p95 soft gate; verify exit 1 and REVIEW.
3. Give one case three outcomes `[pass, pass, fail]` and explain separate effects on task-success gate and trial stability.
4. Add a critical privacy task and first write a failing test proving that a high overall mean must still BLOCK.
5. Change task bootstrap to family resampling and explain why result is the same while every test family has one task.
6. Design a real private-test service: publish spec and grader interface, but control case access, submission budget, and feedback granularity.

## Self-check questions

1. Why is a missing case a contract error while Unknown can be a recorded failed state?
2. When can candidate overall result exceed baseline and still BLOCK?
3. Why is one more protocol budget step not an ordinary warning?
4. Does more trials mean wider task-population coverage?
5. Can evidence fingerprint prove lawful data or trusted runtime machine?

## Mastery checklist

- [ ] I can explain responsibilities and version relationships of spec, cases, and results.
- [ ] I can distinguish PASS, REVIEW, BLOCK, INCOMPARABLE, and contract error.
- [ ] I can prove critical task and protocol consistency take priority over overall mean or rank.
- [ ] I can read results by task, trial, slice, final state, and side effect.
- [ ] I can run 42 tests and four CLI scenarios and explain exit codes.
- [ ] I can list containers/services, permission isolation, private testing, human audit, and online evidence that a real system still needs.

## Project boundary and next step

This project validates offline contracts, fixed fixtures, and deterministic graders. It has no real model/API, container, browser, user simulator, production bill, online monitoring, black-box contamination detection, or submission service. A real Agent Benchmark needs [[benchmark-design/methods-and-quality/07-agent-environment-state-and-repeated-runs|Agent Environments, State, and Repeated Runs]] for a reconstructable harness; [[benchmark-design/foundations-and-design/03-data-splits-leakage-and-contamination|Data Splits, Leakage, and Contamination]] for training exposure, runtime discoverability, and unknowns; and [[benchmark-design/methods-and-quality/06-leaderboard-mechanics-anti-gaming-and-maintenance|Leaderboard Mechanics, Anti-Gaming, and Maintenance]] for private tests and versions.

## References

All sources below were retrieved or checked on 2026-07-21:

- [MLPerf Inference official rules](https://github.com/mlcommons/inference_policies/blob/master/inference_rules.adoc) — a fairness, protocol, reproducibility, and audit example; verify current rules when adopting.
- [SWE-bench official repository](https://github.com/SWE-bench/SWE-bench) — containerized reproducible-harness example.
- [OSWorld original paper](https://arxiv.org/abs/2404.07972) — initial-state setup and execution-based-evaluation example.
- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- [NIST/SEMATECH confidence intervals](https://www.itl.nist.gov/div898/handbook/prc/section1/prc14.htm)
