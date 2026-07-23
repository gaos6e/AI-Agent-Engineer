---
title: "Project: an Auditable Model-Selection Scorecard"
tags:
  - llm
  - project
  - model-selection
  - testing
aliases:
  - Offline model-selection project
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
lang: en
translation_key: 现代LLM能力与模型选择/08-项目-可审计模型选择评分卡.md
translation_source_hash: 3ffb0819376489b8d436cc7639b6a10835d44237254180d2e5008e120f2dc544
translation_route: zh-CN/现代LLM能力与模型选择/08-项目-可审计模型选择评分卡
translation_default_route: zh-CN/现代LLM能力与模型选择/08-项目-可审计模型选择评分卡
---

# Project: an Auditable Model-Selection Scorecard

## Project goal

Run a fully offline candidate selector and observe the fixed sequence **strict input → hard gates → multi-trial aggregation → eligible-set scoring → Pareto → declared weight scenarios**.

Every candidate and metric in the fixture is fictional teaching data. It does not represent any real model or vendor.

## Files

- `examples/model_selection_scorecard.py`: strict parsing, evidence and behavioral gates, per-case repeated-trial aggregation, scoring, Pareto analysis, and a CLI;
- `examples/model_candidates.json`: five anonymous candidates; each runs three trials for each of two cases, with globally unique `trial_id` values;
- `examples/test_model_selection_scorecard.py`: 20 normal, `-O`, expected-failure, evidence-status, behavioral-gate, applicability-condition, dominance, and declared-weight-scenario tests.

## Run

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"  # Tell Python not to write .pyc files, so the knowledge base is not left with caches.
python -B -W error ".\docs-EN\modern-llm-capabilities-and-model-selection\examples\test_model_selection_scorecard.py"  # Run tests at normal optimization and treat warnings as errors so they are exposed.
python -B -O -W error ".\docs-EN\modern-llm-capabilities-and-model-selection\examples\test_model_selection_scorecard.py"  # Run the same tests with -O and confirm that assertions do not carry security or correctness responsibility.
python -B ".\docs-EN\modern-llm-capabilities-and-model-selection\examples\model_selection_scorecard.py" --fixture ".\docs-EN\modern-llm-capabilities-and-model-selection\examples\model_candidates.json"  # Read the teaching fixture and print an auditable scorecard result.
```

Run these commands from the `AI Agent Engineer` project root. No third-party packages, network, or API key are required. The environment variable and `-B` both prevent `__pycache__` creation. The script does not fetch dynamic model data; its fixture evidence objects only demonstrate that a production decision must retain status, location, owner, verification time, and expiry.

## Expected observations

1. Although `candidate-d` is fast and cheap, its structured-output and tool behavior are below the required-capability thresholds. It must enter `ineligible` and have no weighted score.
2. `candidate-e` has the best metrics but a blocked evidence status, so the report retains its missing items and refuses to score it. Changing otherwise-valid verified evidence to an expired date produces `evidence_expired`.
3. Every candidate has 2 cases × 3 trials. Cases may repeat, but `trial_id` must be globally unique; output shows `trial_count=6` and `min_trials_per_case=3`.
4. An eligible candidate that is worse than another on every Pareto metric must be removed from the frontier.
5. Quality-priority and efficiency-priority scenarios produce different winners, so `winner_stable_across_declared_weights: false`. This does not claim stability in a continuous weight space or in a statistical sense.
6. Unknown fields, duplicate JSON keys, `NaN`, contradictory evidence, duplicate trial IDs, inconsistent case counts, or invalid weights fail directly rather than being silently ignored.

## Core implementation boundaries

The scorecard intentionally does not do the following:

- Connect to vendors or maintain model rankings or price snapshots;
- Replace human quality review, security audits, or privacy and legal judgment;
- Infer statistical significance from a small sample;
- Treat nearest-rank p95 from six teaching samples as stable tail-latency evidence;
- Allow a score to override a gate;
- Present three declared weight scenarios as a complete proof of sensitivity or robustness.

For production use, replace the fixture with signed evidence exported from the evaluation pipeline and integrate a release manifest, approval, canary, and rollback process.

## Validation checklist

- [ ] Tests pass in both normal and `-O` modes, showing that business validation does not depend on `assert` statements.
- [ ] The CLI successfully outputs eligible/ineligible candidates, the frontier, and multiple rankings.
- [ ] An invalid fixture returns exit code 2 and stderr has no traceback.
- [ ] Every candidate has the same case set and per-case repetition count, and all `trial_id` values are globally unique.
- [ ] Blocked, missing, and expired evidence blocks only its candidate; a malformed schema rejects the input.
- [ ] Required structured output and tool calling both pass capability labels and measured behavioral thresholds.
- [ ] Gate reasons, raw metrics, weights, and formulas are all inspectable.
- [ ] I can explain why a responsible person must still judge preference and residual risk.

## Next step

Anonymize two of your own candidates and replace the fixture: write gates and cases first, import trials second, and set weights last. Then proceed to [[evaluation-framework/00-index|Evaluation Framework]], use [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and Regression Loop]] to control the handoff from frozen results to release and human regression, and let [[llmops/00-index|LLMOps]] integrate the scorecard into release gates.

## References

- [HELM](https://crfm.stanford.edu/helm/index.html)
- NIST, [AI 600-1](https://doi.org/10.6028/NIST.AI.600-1)
- Mitchell et al., [Model Cards](https://doi.org/10.1145/3287560.3287596)
