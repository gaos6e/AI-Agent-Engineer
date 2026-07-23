---
title: "Project: a fallback-capable rule reranker"
tags:
  - ai-agent-engineer
  - reranking
  - project
aliases:
  - Fallback-capable reranker project
  - Toy Reranker Project
source_checked: 2026-07-22
execution_verified: 2026-07-22
content_origin: original
content_status: validated
source_baseline: Teaching implementation and tests in this course, the BERT
  reranking paper, and current official reranking documentation, checked through
  2026-07-22; 30 unittest cases verified in normal, -O, -W error, and -O -W
  error modes
lang: en
translation_key: Reranking/07-项目-可降级规则重排器.md
translation_source_hash: 56a275b1ccb8fec01055ee49530d1df87222a0fece7000caa7410fc3b94f9c74
translation_route: zh-CN/Reranking/07-项目-可降级规则重排器
translation_default_route: zh-CN/Reranking/07-项目-可降级规则重排器
---

# Project: a fallback-capable rule reranker

## Project goal

This project does not train a neural model. Instead, it implements the parts of a production adaptation layer that are easiest to overlook:

```text
Strict candidate fixture
        ↓
Authorization revision + tenant / ACL / status / effective-time defense-in-depth recheck
        ↓
Safe candidate window
        ↓
Transparent rule provider (can simulate five states)
        ↓
Exact output-ID / finite-score / feature validation
        ↓
Normal reranking or same-safe-window first-stage fallback
        ↓
Complete input/decision evidence fingerprint + canonical cap + MRR/nDCG/Precision + security report
```

The rule score validates orchestration only. It is not a substitute for the quality of a Cross-Encoder, LTR system, or LLM.

## Project files

- [[reranking/examples/reranker-fixture.json|reranker-fixture.json]]: a schema-v2 query, authorization revision, nine candidates, graded qrels, must-not-return constraints, and settings.
- [[reranking/examples/toy_reranker.py|toy_reranker.py]]: strict loading, filtering, scoring, output validation, complete evidence fingerprinting, fallback, and metrics.
- [[reranking/examples/test_toy_reranker.py|test_toy_reranker.py]]: 30 tests.

Fixture parsing rejects duplicate JSON keys; NaN/Infinity; oversized integers that overflow on conversion to float; unknown or missing fields; wrong types; duplicate IDs/ranks; discontinuous first-stage ranks; invalid dates; invalid validity intervals; inaccessible qrels; and `must_not_return` candidates that remain accessible. The query must carry `authorization_revision`, which binds the candidate decision to an explicit authorization-snapshot version. The teaching script validates and records that value only; it does not fetch or validate a real IAM snapshot. Validity always uses the half-open interval `[effective_from, effective_to)`: effective on the start date and expired on the end date, matching the RAG project contract.

## Candidates and the quality ceiling

The query is “After a refund is approved, how long until the money arrives?” with `as_of=2026-07-14`. Of nine first-stage candidates:

- six satisfy alpha/guests, published status, and validity time;
- d-07 is excluded for the wrong tenant;
- d-08 is excluded because it is expired; and
- d-09 is excluded because its ACL denies access.

There are four positive qrels: application entry, grade 1; refund-arrival body, grade 3; FAQ, grade 2; and delayed-processing guidance, grade 2. Their safe-candidate first ranks are 2, 4, 5, and 6:

- `window=6`: 4/4, Candidate Recall=1.
- `window=3`: only rank 2, Candidate Recall=0.25.

This makes the window ceiling directly verifiable rather than merely claimed in prose.

## Transparent scoring

The analyzer applies NFKC/casefold normalization, ASCII alphanumeric tokens, and overlapping Chinese bigrams. Its rule features are:

- `title_coverage`;
- `body_coverage`;
- `exact_phrase`; and
- `score = 2 × title coverage + body coverage + exact phrase`.

These weights are a deterministic fixture design only and are not generalizable. The normal result still passes the same contract as an external model:

- IDs equal the exact set of the whole input window.
- Every ID appears exactly once.
- Scores and features are finite numeric values.
- Unknown, missing, duplicate, and empty results are all invalid.
- Ties use first-stage rank, then ID.

## Normal result

The default uses `window=6`, `top-n=3`, and at most two results per canonical source:

| Path | Ranking | MRR@3 | nDCG@3 | Precision@3 |
| --- | --- | ---: | ---: | ---: |
| First stage | d-01, d-02, d-03 | 0.500000 | 0.060708 | 0.333333 |
| Rule rerank | d-04, d-05, d-06 | 1.000000 | 1.000000 | 1.000000 |

`security_violations` must be empty. The result proves only that the hand-written rules work as designed on this nine-item fixture; it does not demonstrate real model benefit.

## Evidence fingerprints and output boundary

The report supplies two complete 64-character lowercase-hex SHA-256 values:

- `fixture.signature` / `evidence.fixture_sha256` binds the parsed canonical input: query ID/text/tenant/groups/as-of/authorization revision; every candidate’s ID/canonical ID/title/text/tenant/ACL/status/half-open validity interval/source revision/first rank/score; plus fixture settings, qrels, and must-not-return values.
- `evidence.evidence_sha256` additionally binds actual run parameters, failure mode, model revision, filtering/window/fallback, first/final rankings, metrics, and security result.

Tests change each safety or scoring input in turn and verify that both fingerprints change. A CLI override does not change the fixture fingerprint, but must change the evidence fingerprint. This detects a report that still points at old input, but a hash does not prove data truth, correct authorization, or a trustworthy execution environment. A production system still needs signed manifests, trusted time, and tamper-evident storage.

The entire CLI JSON is explicitly marked `visibility=protected_audit`. It contains candidate IDs, filtering reasons, windows, qrels metrics, and failure information. It belongs only in controlled audit or teaching channels, never directly in an end-user RAG or public-search response. `visibility` is a contract label, not an authorization mechanism.

## Failure modes

The CLI provides:

| failure | Simulation | fallback_reason |
| --- | --- | --- |
| `none` | Complete valid result | `null` |
| `timeout` | Provider timeout | `timeout` |
| `error` | Provider/server error | `provider_error` |
| `empty` | Empty list | `invalid_output` |
| `malformed` | Duplicate and missing IDs | `invalid_output` |

All four failures must:

- set `rerank_applied=false`;
- make the final ranking exactly equal to the safe first stage;
- rank d-01, d-02, d-03;
- leave `security_violations` empty; and
- never bring back wrong-tenant, expired, or ACL-denied candidates through fallback.

## Run normal and failure paths

From the project root (which contains `docs-CN/`, `docs-EN/`, and `.website/`), run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Prevent Python bytecode caches so project files remain auditable.
$script = '.\docs-EN\reranking\examples\toy_reranker.py'  # Store the executable local teaching-script path.
$fixture = '.\docs-EN\reranking\examples\reranker-fixture.json'  # Store the strict fixture path consumed by the script.

python -B -W error $script --fixture $fixture  # Run the healthy path; normal output should set rerank_applied=true.
if ($LASTEXITCODE -ne 0) {  # Enter only when the Python process itself exits abnormally; provider fallback still returns 0.
    throw "Normal path failed, exit code: $LASTEXITCODE"  # Stop so later output is not interpreted as trustworthy.
}

foreach ($mode in @('timeout', 'error', 'empty', 'malformed')) {  # Cover each recoverable provider or output failure.
    python -B -W error $script --fixture $fixture --failure $mode  # Request a controlled fallback report, not an unhandled exception.
    if ($LASTEXITCODE -ne 0) {  # Only real fixture or CLI-parameter errors should produce a nonzero exit code.
        throw "Failure simulation $mode did not produce a controlled report, exit code: $LASTEXITCODE"  # Surface an adaptation-layer failure.
    }
}
```

A provider failure is a business state successfully handled by the adaptation layer, so the CLI returns 0 and emits a fallback report. Fixture or parameter errors return 2.

## Run the tests

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Do not commit caches created by tests into the knowledge base.
$project = '.\docs-EN\reranking'  # Store the project directory for predictable relative example discovery.

Push-Location $project  # Enter the project directory temporarily so unittest relative paths are predictable.
try {  # finally restores the working directory even if a test fails.
    python -B -m unittest discover -s .\examples -p 'test_toy_reranker.py' -v  # Run every test in normal interpreter mode.
    if ($LASTEXITCODE -ne 0) {  # Inspect the external Python exit code rather than relying on PowerShell exceptions.
        throw "Normal-mode tests failed, exit code: $LASTEXITCODE"  # Stop immediately; do not hide the first failure.
    }

    python -B -O -m unittest discover -s .\examples -p 'test_toy_reranker.py' -v  # Repeat under -O so production checks do not rely on bare assert.
    if ($LASTEXITCODE -ne 0) {  # A nonzero result remains reproducible under optimized mode.
        throw "Optimized-mode tests failed, exit code: $LASTEXITCODE"  # Preserve the exit code for diagnosis.
    }

    python -B -W error -m unittest discover -s .\examples -p 'test_toy_reranker.py' -v  # Repeat with all warnings promoted to errors.
    if ($LASTEXITCODE -ne 0) {  # This exposes deprecations or resource problems ignored by normal mode.
        throw "Warnings-as-errors tests failed, exit code: $LASTEXITCODE"  # Keep the failure readable for a beginner.
    }

    python -B -O -W error -m unittest discover -s .\examples -p 'test_toy_reranker.py' -v  # Cover the strictest combination of -O and warnings-as-errors.
    if ($LASTEXITCODE -ne 0) {  # Any nonzero value means the contract is unmet under this combination.
        throw "Optimized warnings-as-errors tests failed, exit code: $LASTEXITCODE"  # Identify the exact failure mode for the caller.
    }
}
finally {  # Executes even after throw.
    Pop-Location  # Restore the PowerShell working directory used before the command block.
}
```

Normal, `-O`, `-W error`, and `-O -W error` modes each run 30 tests. Correctness must not depend on bare `assert`, which optimization can remove, or on ignoring warnings in normal mode.

## Key experiments

### Experiment A: window ceiling

```powershell
python -B -W error $script --fixture $fixture --candidate-window 3 --output-top-n 3  # Shrink the safe candidate window and observe the candidate-recall ceiling.
```

Confirm `candidate_recall_at_window=0.25`; the grade-3 refund-arrival body is not in the window. Even a perfect reranking rule cannot bring it into top 3.

### Experiment B: canonical cap

```powershell
python -B -W error $script --fixture $fixture --max-per-canonical 1  # Retain at most one result per canonical source to demonstrate diversity post-processing.
```

By default d-04 and d-05 belong to the same canonical document. With `cap=1`, the second item is skipped and d-06 and d-02 fill the vacancies. Compare item-level nDCG with source/evidence coverage; do not merely claim that the result is “more diverse.”

### Experiment C: output attacks

In tests, construct an unknown ID, duplicate ID, missing ID, NaN score, and nonnumeric feature. Confirm that every case triggers `OutputContractError` or fallback and never enters the final ranking.

### Experiment D: connect a real Cross-Encoder

When replacing `simulate_provider`, preserve:

1. the same safe window;
2. request/response schema and exact-ID validation;
3. model/tokenizer/input-template revisions;
4. token/truncation, batch, deadline, and duration fields;
5. normal operation and every failure path; and
6. comparisons among first stage, rule baseline, new model, key slices, and end-to-end behavior.

## Gap to a production system

This project has no neural model, GPU/queue, real network, batching, tokenizer/truncation, rate limit, retry/circuit breaking, cache, distributed trace, real IAM or authorization-snapshot validation, audit-channel access control, or sensitive-log governance. `authorization_revision` and `visibility` are strictly bound teaching-contract fields, not authorization implementations. The transparent n-gram rules are for teaching only and must not be presented as a relevance service.

## Project acceptance

- [ ] The candidate-recall ceiling can be reproduced as the window changes.
- [ ] Hard filtering occurs before the model, and fallback uses the safe window only.
- [ ] Output IDs are exact, unique, and complete; scores/features are finite.
- [ ] All four failures produce deterministic, observable fallback.
- [ ] First-stage, model, and final provenance are separate for normal and fallback paths.
- [ ] Authorization revision and every safety/scoring input enter complete fixture/evidence SHA-256 records.
- [ ] The protected-audit envelope is not a public response and has independently implemented access control.
- [ ] The canonical cap fills vacancies from later candidates.
- [ ] All 30 tests pass in normal, `-O`, `-W error`, and `-O -W error` modes.
- [ ] There are no credentials, network dependencies, caches, or third-party dependencies.
- [ ] Current rule metrics are not extrapolated as model performance.

## Self-check

1. Why can a grade-3 positive not be reranked to first place when `window=3`?
2. Why cannot an empty model output automatically mean “everything is irrelevant”?
3. Why must fallback reuse the safe window rather than the original unfiltered list?
4. Why does the output contract require an exact ID set?
5. How can a canonical cap improve diversity while lowering item-level nDCG?
6. Why can neither `authorization_revision` nor `visibility` replace real authorization?
7. Which version and latency fields must be added after connecting a real Cross-Encoder?

When finished, return to the [[reranking/00-index|Reranking course overview]] and continue with [[rag/00-index|RAG]].

## References

- Nogueira & Cho, [Passage Re-ranking with BERT](https://arxiv.org/abs/1901.04085)
- [Sentence Transformers: Cross-Encoder Applications](https://www.sbert.net/examples/cross_encoder/applications/README.html)
- [Elasticsearch: Semantic reranking](https://www.elastic.co/docs/solutions/search/ranking/semantic-reranking)

Sources checked on 2026-07-22. Teaching behavior is defined by the current fixture, script, and tests; verify dynamic models and APIs again against a pinned version.
