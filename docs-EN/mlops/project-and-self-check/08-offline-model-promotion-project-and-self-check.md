---
title: "Offline Model Promotion Project and Self-Check"
tags:
  - mlops
  - project
  - testing
aliases:
  - MLOps Promotion Gate Project
source_checked: 2026-07-21
execution_verified: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: MLOps/03-项目与自测/08-离线模型晋级项目与自测.md
translation_source_hash: 3c65db09def455ae9df94fec3975cd8aad8ddec6b6fbd6f33c286cedbc87fb22
translation_route: zh-CN/MLOps/03-项目与自测/08-离线模型晋级项目与自测
translation_default_route: zh-CN/MLOps/03-项目与自测/08-离线模型晋级项目与自测
---

# Offline Model Promotion Project and Self-Check

## Project goal

This project does not train or load a real model, access a network, registry, Kubernetes, or cloud service, and needs no secret. It uses the Python standard library to connect five commonly confused kinds of MLOps evidence:

1. A candidate manifest binds data, label, code, environment, training configuration, model digest, and signature.
2. A promotion gate compares tests, overall metrics, critical slices, latency, size, and interface compatibility.
3. Production observation first binds an approved candidate-gate fingerprint, fixed artifact, and reference identity, then distinguishes shadow from Canary.
4. It explicitly checks total samples, labeled samples, critical-slice samples, and label coverage, distinguishing healthy behavior, insufficient evidence, drift alone, label-confirmed quality regression, and technical failure.
5. Decision output includes release, stage, policy version, evidence fingerprint, reasons, and continue, investigate, block-rollout, or rollback action.

Every threshold is local teaching policy, not an industry recommendation. Real thresholds derive from business loss, sample size, measurement variation, risk tolerance, and SLO.

## Project files

- [promotion_gate.py](mlops/examples/promotion_gate.py) — strict schema validation, promotion gate, production assessment, and CLI.
- [candidates.json](mlops/examples/candidates.json) — policy, champion baseline, and two candidate manifests.
- [observations.json](mlops/examples/observations.json) — one fixed release and five shadow/Canary observation windows.
- [test_promotion_gate.py](mlops/examples/test_promotion_gate.py) — 52 `unittest` cases covering duplicate JSON keys, nonstandard constants, bad input, candidate-gate binding, stages, sample denominators, drift, rollback, and CLI.

The digests in `candidates.json` are syntactically valid teaching placeholders and do not correspond to real model files. The project validates evidence organization and control logic, not model quality.

## Runtime environment

Run the blocks in order from the project root containing `docs-EN/` and `.website/`:

```powershell
Push-Location -LiteralPath 'docs-EN\mlops' # Enter the project directory; the final Pop-Location restores the original directory.
python --version # Confirm the Python version actually invoked by this environment.
```

The scripts need only the Python 3 standard library, with no `pip install`. To isolate an interpreter, follow the [[mlops/00-index#environment-route-start-with-venv-and-pip-then-choose-a-platform|environment route in the course index]] to create `.venv` outside the vault, then return here. Never create `.venv` inside the knowledge base.

## Step 1: inspect candidate promotion

### Complete evidence that passes local policy

```powershell
python -B .\examples\promotion_gate.py candidate --id candidate-safe # Run the offline promotion gate for a complete candidate; -B writes no bytecode cache.
$LASTEXITCODE # Display the stable exit code to compare with the 0/1/2 contract below.
```

Expected: `decision` is `promote` and exit code is `0`. Output includes `policy_version` and an `evidence_fingerprint` derived from candidate, baseline, and policy.

### Better overall metric but failed critical slice and data test

```powershell
python -B .\examples\promotion_gate.py candidate --id candidate-regression # Run the fixture with a critical-slice and data failure.
$LASTEXITCODE # Expected 1: the script completed correctly and blocked promotion.
```

Expected: `decision` is `block` and exit code is `1`. Reasons include `required test failed: data` and the critical slice below its policy gate. An overall average cannot offset a critical-slice or data-contract failure.

### Manifest lineage

Every candidate needs:

- immutable data snapshot and label version;
- code commit, environment digest, and training-configuration digest;
- model artifact digest, format, size, and input/output schema;
- explicit test results plus overall, slice, and latency metrics.

The validator rejects unknown or missing fields, `latest`, invalid SHA-256, Boolean pseudo-numbers, nonfinite numbers, and duplicate IDs. Strict schemas require explicit migration on upgrade but do not silently ignore misspelled fields.

An online fixture must also prove its deployed candidate passed current policy, `promotion_evidence_fingerprint` exactly matches that candidate decision, and model ID, artifact digest, and observation reference identity match each other. Fingerprint binding catches obvious errors such as swapping an artifact after evaluation or reusing an old policy conclusion. It is not a signature and does not prove that a claimed external artifact exists.

## Step 2: interpret drift and rollback

### Healthy window

```powershell
python -B .\examples\promotion_gate.py observe --id window-healthy # Evaluate a healthy production window with sufficient evidence.
```

Expected `action`: `continue`, exit code 0.

### Input drift with insufficient ground truth

```powershell
python -B .\examples\promotion_gate.py observe --id window-drift-no-label # Drift plus insufficient labels must enter investigation only.
$LASTEXITCODE # Expected 1: action is required, not a Python failure.
```

Expected `action`: `investigate`. Input drift is an investigation signal; insufficient label coverage must not become “quality declined” or “retrain automatically.”

### Drift plus labeled critical-slice regression

```powershell
python -B .\examples\promotion_gate.py observe --id window-quality-regression # Validate rollback priority with a labeled critical-slice regression.
```

Expected `action`: `rollback_and_review_retraining`. Contain impact first, then review whether data and labels can produce a new candidate; `review_retraining` does not mean automatically releasing one.

### Technical failure

```powershell
python -B .\examples\promotion_gate.py observe --id window-technical-failure # Simulate service error-rate/P95-latency failure separately from model quality.
```

When error rate and P95 latency exceed local policy, action is `rollback_and_investigate`. A technical failure is not misclassified as model retraining need.

### Shadow technical failure

```powershell
python -B .\examples\promotion_gate.py observe --id window-shadow-technical-failure # Shadow can only block expansion; it cannot claim to have rolled back user traffic.
```

Expected `action`: `block_rollout_and_investigate`. A shadow candidate has not made user decisions, so block transition to Canary rather than claiming “user traffic was rolled back.” If a shadow path accidentally performs a real write, treat that side effect as an incident.

The windows use `sample_count`, `labeled_count`, and `critical_labeled_count` as denominators. The script calculates label coverage from the first two and requires absolute count, coverage, and critical-slice count to pass. “80% labeled” from only a few samples must not automatically expand.

## Inspect all teaching scenarios once

```powershell
python -B .\examples\promotion_gate.py audit # Summarize offline fixtures without treating it as one release gate.
```

`audit` returns 0 whenever both JSON contracts are valid because it summarizes examples. Its output still contains promote, block, investigate, and rollback results. Automation must not use only the `audit` process code; use a single-candidate/window command or parse every structured decision.

## Run tests

```powershell
Push-Location .\examples # Keep source and tests together for module discovery.
$env:PYTHONDONTWRITEBYTECODE = "1" # A second cache guard keeps this teaching directory clean.

python -B -m unittest -q test_promotion_gate.py # Run all regressions under the ordinary interpreter.
python -B -O -m unittest -q test_promotion_gate.py # Ensure production validation does not rely on bare assert removed by -O.
python -B -W error -m unittest -q test_promotion_gate.py # Treat warnings as failures to reveal compatibility issues.
python -B -O -W error -m unittest -q test_promotion_gate.py # Run the combined strict mode too.

Pop-Location # Return from examples to this project directory.
```

The modes verify 52 contract and behavior cases: ordinary behavior, no optimization-removable assertions, warnings as failures, and their combination. You can also parse both Python files in memory without generating `.pyc`:

```powershell
python -B -c "from pathlib import Path; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in map(Path, ['examples/promotion_gate.py', 'examples/test_promotion_gate.py'])]"
Pop-Location # Return to the initial project root.
```

## Control-boundary map

| Code | Engineering meaning |
| --- | --- |
| `validate_candidates_fixture` | Manifest schema and immutable-lineage entry point |
| `evaluate_candidate` | Candidate/champion comparison under a versioned policy |
| `validate_observations_fixture` | Deployment binds to passed candidate-gate fingerprint; reference identity matches fixed artifact |
| `assess_observation` | Separates stage, denominator, drift, label evidence, quality, and technical failure |
| `evidence_fingerprint` | Stable decision-input fingerprint, not a digital signature or authorization |
| CLI exit code | `0` continue/promote, `1` block or action required, `2` input error |

`evidence_fingerprint` can detect whether the same JSON evidence changed; it cannot establish source trust. A production system additionally needs identity, immutable storage, signature or attestation, access control, and audit.

## Extension tasks

1. Set policies for two named critical slices without using the average as the only criterion.
2. Add intervals from multiple repeated runs rather than comparing one point metric.
3. Add a candidate-risk approval object bound to reviewer, summary, target environment, and validity.
4. Add a read-only tool or simulated side-effect invariant for shadow, then prove the system blocks the error before Canary.
5. Simulate a deployment alias moving after evaluation and prove fixed digest and candidate-gate fingerprint block the wrong artifact.
6. Write each decision to a newly created, non-overwritable temporary report and design an idempotency key for repeats.
7. Write an explicit migration for an old schema rather than weakening validation to silently accept it.

## Mastery checklist

- [ ] I can explain the lineage supplied separately by data, labels, code, environment, training configuration, and artifact digest.
- [ ] I can explain why a candidate with a better overall metric can still be blocked.
- [ ] I can distinguish drift, label-confirmed quality regression, and technical service failure.
- [ ] I can explain why drift must not directly trigger automatic retraining and release.
- [ ] I can run the 52 tests and explain `-O`.
- [ ] I can distinguish an offline fingerprint, registry version, approval, and artifact signature.
- [ ] I can list real platform capability the project has not verified.

## Project boundary

This project does not verify real MLflow 3.14.0, Kubeflow, KServe, Kubernetes, cloud object storage, containers, model inference, production traffic, or business causal effect, and produces no model weights. Its fixed reference is not a concurrent randomized control and differences cannot be called causal release effects. See the more stringent parallel-control binding in [[llmops/project-and-self-check/08-offline-release-gate-project-and-self-check|LLMOps Offline Release Gate Project]]. When integrating a real platform, pin versions in an independent environment and run integration, permission, recovery, and progressive-release tests with the same contracts.

## References

All materials below were checked on 2026-07-21:

- [MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/)
- [MLflow Model Registry workflow](https://www.mlflow.org/docs/latest/ml/model-registry/workflow/)
- [Google Cloud: MLOps continuous delivery and automation pipelines](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning)
- [Kubernetes Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [NIST AI RMF 1.0](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)
