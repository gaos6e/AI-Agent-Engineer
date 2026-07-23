---
title: "Offline Release Gate Project and Self-Check"
tags:
  - llmops
  - project
aliases:
  - LLMOps Release Gate Project
source_checked: 2026-07-22
execution_verified: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: LLMOps/03-项目与自测/08-离线发布门项目与自测.md
translation_source_hash: ec2267a25effcaf22cb339df6785633ecb52d3a5295456eb048c787741538f55
translation_route: zh-CN/LLMOps/03-项目与自测/08-离线发布门项目与自测
translation_default_route: zh-CN/LLMOps/03-项目与自测/08-离线发布门项目与自测
---

# Offline Release Gate Project and Self-Check

## Project goal

Run an LLMOps gate without calling a real LLM API. It does four things:

1. Strictly validates a composite release manifest and rejects duplicate, missing, or unknown fields, wrong types, and common floating aliases.
2. Binds an evaluation artifact to a release and returns `INCOMPARABLE` when the baseline and candidate differ in suite, dataset, rubric, grader, or harness.
3. Turns offline tests, quality, safety, performance, traces, redaction, Canary, rollback, and human approval into `promote` or `block`.
4. Binds a candidate gate's full SHA-256, display-only short fingerprint, promotion time, fixed audit time, concurrent control, time window, assignment, label coverage, sample denominators, and fallback evidence before turning an observation into `continue`, `investigate`, `pause`, `fallback`, `rollback`, or `human_review`.

Project files:

- [release_gate.py](llmops/examples/release_gate.py) — strict contracts, decision logic, and the CLI entry point.
- [release_candidates.json](llmops/examples/release_candidates.json) — local policy, baseline, and two candidates.
- [online_observations.json](llmops/examples/online_observations.json) — seven simulated Canary observations.
- [test_release_gate.py](llmops/examples/test_release_gate.py) — 74 Python-standard-library regression tests.

The quality, safety, latency, cost, and drift thresholds in the JSON are **local practice values** chosen to produce verifiable script results. They are not industry thresholds, provider prices, or safety guarantees. `local-llmops-policy-v6` identifies the current strict semantics for ratios, time, fallback evidence, and combined audit; the online-observation schema is `local-online-observation-v6`. Rates, drops, and relative-increase limits in this project are constrained to `0..1`. Each evaluation artifact also declares `artifact_digest_format`, and the observation bundle declares `evidence_digest_format` at its top level; both must use this project's currently supported, versioned teaching format. The reader converts raw invalid UTF-8, Unicode surrogates that cannot be encoded as strict UTF-8 scalar sequences, and numbers that cannot be represented as finite `float` values into controlled contract errors. That prevents uncontrolled exceptions while computing full digests. A production policy that needs a wider range must version its schema and approval rules; it must not silently disable safety gates with oversized values. Updating the policy, online-observation schema, or gate semantics changes the full digest of the corresponding evidence. Existing observation windows must be rebound; they cannot keep an old digest or rely only on a short fingerprint.

## Environment and execution

The script depends only on the standard library in a current stable Python 3 release. Learn the `venv + pip` isolation pattern, but keep the virtual environment outside the vault to avoid caches and many untracked files:

```powershell
Push-Location -LiteralPath 'docs-EN\llmops' # Enter the English LLMOps project directory.
$llmopsVenv = Join-Path $env:TEMP 'llmops-learning-venv' # Keep the temporary environment outside the knowledge base.
python -m venv $llmopsVenv # Create an isolated Python interpreter; this project still uses only the standard library.
& "$llmopsVenv\Scripts\Activate.ps1" # Activate it so later python/pip commands use the isolated interpreter.
python -m pip --version # Verify pip availability and interpreter ownership only; install no third-party package.

python -B .\examples\release_gate.py candidate --release-id release-safe # Evaluate only the offline candidate gate; expect PROMOTE.
python -B .\examples\release_gate.py observe --observation-id obs-healthy # Evaluate one fixed healthy online observation window.
python -B .\examples\release_gate.py audit --release-id release-safe --observation-id obs-healthy # Jointly check the candidate and correctly bound observation evidence.
Pop-Location # Restore the calling directory.
```

This project needs no `pip install`, does not read `.env`, and needs no API key. If you already have a suitable Python 3, run it directly without creating a virtual environment.

## What belongs in a release manifest

A candidate must pin:

- the application commit, API contract, and SDK lockfile digest;
- Prompt version and content digest, plus the context policy;
- retrieval snapshot and configuration;
- provider, model snapshot, and generation parameters;
- tool name, schema, and implementation. Tool names must be unique within one manifest so that the same name cannot point to two contracts;
- guardrails, data handling, routing, price-accounting convention, and the fallback release's `release_id`, full manifest SHA-256, and full gate-evidence SHA-256;
- evaluation suite, dataset, rubric, grader, harness, subject release, and full artifact SHA-256;
- contract tests, task and critical-slice evidence, safety sample count, latency, and cost evidence; and
- gate-decision time, actual `promoted_at`, Trace, redaction, Canary, rollback, and human-approval records.

The script rejects `latest`, `current`, `production`, `model:latest`, `HEAD`, and any `refs/heads/*`, `refs/remotes/*`, `origin/*`, or `upstream/*` branch reference. It does not falsely reject an ordinary identifier merely because it contains the substring `main`. This remains a teaching check: a real system must verify, according to field and provider semantics, that a content digest, model snapshot, or commit can reconstruct the behavior at the time. Baseline and candidate `release_id` values must be globally unique within the same manifest.

The baseline and candidate enter numeric comparison only when `suite/dataset/rubric/grader/harness` are exactly equal. Otherwise the result is `INCOMPARABLE` with exit code `1`. Full SHA-256 values and `subject_release_id` prevent obvious misbinding, but Layer A currently validates only the digests declared in the manifest. It does not read, sign, or validate the external evaluation or fallback artifact body. Production CI must actually load the report and fallback manifest, recompute digests, and verify provenance, gate results, and approval.

## Online-observation contract

Each observation window records all of the following:

- strict RFC 3339 UTC `window_start/end` values (`Z` or `+00:00`, never date-only values), assignment, and population revision;
- candidate and control releases plus eligible, labeled, critical-labeled, and safety-checked denominators;
- **integer numerators** for task success, critical-slice success, and safety violations. The script divides them by labeled, critical-labeled, and safety-checked denominators respectively; a zero denominator means the rate is unknown, not zero;
- maximum label age, P95, and actual cost; and
- the candidate gate's full `candidate_gate_evidence_sha256`, its display-only `candidate_gate_fingerprint`, Trace/redaction state, provider signals, and the observation-side `fallback_evidence` that is actually available. The bundle's top-level `evidence_digest_format` defines the digest format uniformly.

The time contract uses the fixed `policy.decision_as_of` in the fixture rather than the current wall clock, making historical recomputation deterministic. A candidate must satisfy `gate_decided_at <= promoted_at <= decision_as_of`; an online window must additionally satisfy `promoted_at <= window_start < window_end <= decision_as_of`. This rejects traffic from before a release masquerading as a Canary and rejects a “future window” beyond this audit time. The candidate-gate digest deliberately excludes `promoted_at`, which is written only after release, so moving the control plane forward cannot alter already approved offline evidence. `promoted_at` is still independently validated strictly before an observation is bound. To audit a later window, produce a new version of the policy/candidate-gate digest and bind it again; do not edit the clock of an old audit.

Online quality, latency, and cost are compared with the **concurrent control**, not with an aggregate from a frozen offline set presented as an online reference. Automatic quality or critical-slice rollback comparisons run only when both candidate and control pass their sample, coverage, critical-slice, safety-check, and label-freshness gates. A non-null observation-side `fallback_evidence` must exactly match the `candidate.routing.fallback_manifest` already bound by the candidate gate; a wrong digest or wrong release is a contract error. Provider degradation with missing evidence can only yield `HUMAN_REVIEW`. Even when the evidence fully matches, automatic `FALLBACK` is allowed only if the candidate's current window meets the evidence-sufficiency conditions above. Otherwise, even a previously validated fallback release produces `HUMAN_REVIEW` and stops automated expansion; sparse or stale signals must not drive an automatic switch. The manifest also rejects self-reference, known fallback-chain cycles, and known fallback candidates that did not pass their gate, were not promoted, or were promoted later than the primary candidate. A Boolean self-declaration that something is “ready” therefore cannot trigger an automatic switch. `audit --release-id A --observation-id B` must prove that B's candidate release is A; cross-release composition is a contract error with exit code `2`. `audit --release-id A` also requires at least one online window bound to A, so an offline-only candidate recomputation cannot masquerade as a “joint audit”; use the `candidate` subcommand for an offline-only check. A batch `audit` without parameters requires every candidate that passed the candidate gate to have at least one bound window. A candidate blocked offline does not need a fabricated online observation.

### Digest format and the boundary of real evidence

`python-json-sorted-utf8-v1` precisely names this project's Python byte representation: positional arguments are put in an outer array, serialized with `json.dumps(ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)`, UTF-8 encoded, and hashed with SHA-256. `Decision.evidence_digest_format`, each evaluation artifact's `artifact_digest_format`, and the observation bundle's `evidence_digest_format` must all carry this value. An online decision also includes the bundle's `schema_version` and format field in its full digest, so either upgrade changes the evidence. A fixed golden-vector test locks both the format label and the byte digest of the same input, preventing the three offline teaching projects from silently drifting apart.

This provides reproducible handoff within a controlled implementation and rejects unknown formats. It does not read external artifact bodies or prove that a 64-character digest came from an upstream system, that an artifact was not replaced, that its provenance was signed, or that approval exists. The current fixtures are independent; they must not be presented as one real evaluation-to-gate-to-Canary handoff. Cross-language hashing or signing should exchange verified original bytes or use a precisely specified, interoperability-tested standard such as [RFC 8785 JCS](https://www.rfc-editor.org/rfc/rfc8785.html). The local profile is not universal canonical JSON and cannot replace controlled artifact storage, access control, signatures, or human approval. See [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and Regression Loop]] for the full handoff diagram and field boundaries.

## Expected results

Candidate releases:

- `release-safe` meets the strict contract and every local gate, prints `PROMOTE`, and exits with `0`.
- `release-regression` fails the tool contract, critical slice, safety sample count, cost, and human approval checks, prints `BLOCK`, and exits with `1`.

Online observations:

| Observation | Expected action | Why |
| --- | --- | --- |
| `obs-healthy` | `CONTINUE` | Evidence is complete and meets local policy. |
| `obs-low-sample` | `INVESTIGATE` | Insufficient samples must not be mistaken for success. |
| `obs-provider-drift` | `FALLBACK` | Provider signals degraded and the validated fallback path is ready. |
| `obs-provider-insufficient-evidence` | `HUMAN_REVIEW` | Fallback is bound, but the candidate safety-check denominator is insufficient, so it cannot switch automatically. |
| `obs-quality-regression` | `ROLLBACK` | Task, critical-slice, and safety gates fail. |
| `obs-no-fallback` | `HUMAN_REVIEW` | The provider degraded but no validated alternative exists. |
| `obs-capacity-cost` | `PAUSE` | Latency and cost degraded; pause expansion first. |

Without an ID, a command checks every example. If any example is blocked or requires action, the aggregate exit code is `1`. A missing input file, invalid JSON, or contract error produces exit code `2`.

Reproduce the conservative “fallback bound but evidence insufficient” result directly:

```powershell
Push-Location -LiteralPath 'docs-EN\llmops'
python -B .\examples\release_gate.py audit --release-id release-safe --observation-id obs-provider-insufficient-evidence # Verify that insufficient evidence leads conservatively to HUMAN_REVIEW rather than automatic fallback.
Pop-Location
```

This prints `HUMAN_REVIEW` and exits with `1`, stopping automatic expansion. It is not a successful automatic-fallback path.

## Tests and verification

```powershell
Push-Location -LiteralPath 'docs-EN\llmops\examples' # Keep relative fixture paths stable by entering the test directory.
$env:PYTHONDONTWRITEBYTECODE = '1' # Prevent Python from creating __pycache__ in the knowledge base.
try {
    python -B -c "from pathlib import Path; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in (Path('release_gate.py'), Path('test_release_gate.py'))]" # Compile implementation and tests in memory before execution.
    python -B -m unittest -v .\test_release_gate.py # Run all regression tests under the ordinary interpreter.
    python -B -O -m unittest -v .\test_release_gate.py # Verify production logic does not rely on bare assert removed by optimization.
    python -B -W error -m unittest -v .\test_release_gate.py # Treat warnings as failures to reveal compatibility problems.
    python -B -O -W error -m unittest -v .\test_release_gate.py # Combine the strict interpreter and warning conditions.
} finally {
    Pop-Location # Restore the original working directory even if a test fails.
}
```

The in-memory `compile()` syntax check writes no `.pyc`. `-O` removes ordinary `assert` statements, so the tests explicitly verify that the gate still works in optimized mode. Production decisions do not depend on `assert`; `self.assert*` calls in tests are test-framework assertions and are not silently removed by optimization. The 74 tests also verify full-digest tampering, that a short fingerprint cannot replace full binding, unknown digest formats, bundle schema/profile effects on online decision digests, format labels and a fixed golden vector, result numerators no greater than denominators, rejection of duplicate tool names, controlled errors for raw invalid UTF-8, unencodable surrogates, and values not representable as finite `float`; they also verify that provider drift with insufficient evidence in fixture and CLI cannot auto-fallback, and that `promoted_at` cannot rewrite approved candidate-gate evidence.

## Guided practice

1. Run the healthy joint audit and record the policy version and evidence fingerprint.
2. Run `release-regression` and map each reason to a tool, quality, safety, cost, or governance risk.
3. Keep the safety-violation rate at zero but change the safety sample count to `1`; explain why it is still blocked.
4. Change a model snapshot to `latest` and confirm that this is an input-contract error (exit code `2`), not an ordinary candidate failure.
5. Change the candidate dataset version so that it differs from the baseline and confirm the `INCOMPARABLE` result.
6. Try a joint audit of `release-regression` and `obs-healthy`; confirm that incorrect binding fails with exit code `2`.
7. Change `obs-provider-drift.fallback_evidence.manifest_sha256` to another valid 64-character digest and confirm that binding fails with a contract error. Then make the entire field `null` and confirm that provider degradation can only enter human review. Finally run the fixture's `obs-provider-insufficient-evidence` and confirm that insufficient candidate safety-check denominator permits only human review even though fallback is bound.
8. Add an observation with normal quality but `redaction_check_passed=false`; confirm that privacy failure takes priority over performance signals.
9. When adding “effective time, risk rationale, and approval-record digest” to policy, extend the strict contract and tests before changing a fixture.

## Self-check questions

1. Why should Prompt, API contract, tool schema, and grader all enter the manifest?
2. Why can a high-risk slice still block a release when overall task-success rate improves?
3. Why must “zero observed safety violations” still be checked against sample count and coverage?
4. Why is Trace completeness a release condition rather than an optional post-incident feature?
5. During provider drift, why is an observation-side Boolean insufficient to trigger an automatic switch, and why must it match the fallback release identity and digest bound by the candidate gate?
6. Why must a historical cost recalculation pin the price-policy version that applied at the time?
7. What can an evidence fingerprint prove, and what can it not prove?

## Mastery checklist

- [ ] I can explain that strict JSON contracts and business gates are separate layers.
- [ ] I can distinguish exit codes `0`, `1`, and `2`, and handle them correctly in CI.
- [ ] I can explain the production risk corresponding to each candidate check.
- [ ] I can map a Canary observation to continue, investigate, pause, fallback, rollback, or human review.
- [ ] I can add a fixture and tests that pass under ordinary, `-O`, warnings-as-errors, and `-O` plus warnings-as-errors modes.
- [ ] I can explain why the local digest format supports controlled recomputation but cannot replace cross-language canonicalization, artifact-provenance verification, or approval.
- [ ] I can distinguish “the local practice gate passed” from “the real system is safe.”

## Project boundary and next steps

This project validates evidence structure, release/window/fallback binding, and decision logic. It does not call a real model, load an external evaluation or fallback artifact, measure real tokens or cost, perform a real Canary, or prove a provider, data region, randomized assignment, label correctness, or business causal effect. A full SHA-256 can detect whether the same declared input changed only after the receiver has verified the same algorithm version, format, and bytes; a short fingerprint is merely its display prefix. Neither proves that input is real, content is complete, provenance is signed, or approval occurred. The fixture's fixed `decision_as_of` supplies only a reproducible upper time bound, not a real trusted-timestamp service.

Next, connect the same manifest to CI and use [[runtime-monitoring/00-index|Runtime Monitoring]] to build a real observation surface. Triage online anomalies as controlled human candidates first; do not automatically write them into an evaluation set. The complete boundary is in [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and Regression Loop]]. Any real provider integration must recheck its current API, pricing, retention capability, and contract.

## References

All dynamic materials below were checked on 2026-07-22:

- [OpenAI Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
- [OpenAI Production best practices](https://developers.openai.com/api/docs/guides/production-best-practices)
- [OpenAI Trace grading](https://developers.openai.com/api/docs/guides/trace-grading)
- [NIST AI 600-1: Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html) — choose and test an explicit byte convention for cross-system hashing or signing; this project does not treat its local Python profile as JCS.
