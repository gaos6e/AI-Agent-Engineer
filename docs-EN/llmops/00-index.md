---
title: "LLMOps Learning Path"
tags:
  - ai-agent-engineer
  - llmops
  - learning-path
aliases:
  - LLMOps
  - Large Language Model Operations
  - LLMOps from Zero
ai_learning_stage: 7. Production, Evaluation, and Governance
ai_learning_order: 41
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
ai_learning_schema: 2
ai_learning_id: llmops
ai_learning_domain: production-ops
ai_learning_catalog_order: 4100
ai_learning_hard_prerequisites:
  - evaluation
ai_learning_track_agent_app_order: 1100
ai_learning_track_agent_app_kind: recommended
ai_learning_track_agent_platform_order: 1200
ai_learning_track_agent_platform_kind: core
lang: en
translation_key: LLMOps/00-目录.md
translation_source_hash: 4bdf3610b3eb52ed470412ae09e79bf46b5fe3a38af5b5aa78e856ab6e03469e
translation_route: zh-CN/LLMOps/00-目录
translation_default_route: zh-CN/LLMOps/00-目录
---

# LLMOps

## Course overview

LLMOps is the engineering practice that makes a Large Language Model (LLM) application evaluable, releasable, traceable, observable, and reversible. It operates not only a model file but a composite application: application code; API/SDK contract; prompt; context assembly; retrieval snapshot; model and parameters; tools; routing; data and safety policy; evaluators; and price-accounting convention.

The smallest control loop is:

```text
Fixed release manifest → offline evaluation gate → human approval → Canary
        ↑                                             ↓
Regression suite and policy updates ← online observation/feedback ← degrade, roll back, or continue
```

This course focuses on controlling one LLM-application change with evidence. For prompt writing see [[prompt-engineering/00-index|Prompt Engineering]], for retrieval principles see [[rag/00-index|RAG]], and for model training, registry, and deployment pipelines see [[mlops/00-index|MLOps]].

## Where this course fits

LLMOps sits between “can call an LLM” and “can operate an LLM application over time.” Learn LLM API integration, prompting, context, RAG, Tool Calling, basic MLOps, and [[evaluation-framework/00-index|Evaluation Framework]] first; at minimum you must define an objective, build a dataset, and set a release gate. Continue with runtime monitoring, linking AI safety and AI governance into the same evidence chain.

## Learning objectives

- Define a complete LLM-application release unit and trace every key version from a production output.
- Use a gateway to centralize authentication, rate limits, timeout, retry, routing, and cost attribution.
- Make evidence-based caching and routing decisions across quality, latency, cost, and data boundaries.
- Trace model, retrieval, and tool calls while limiting sensitive-content exposure.
- Combine regression suites, deterministic checks, model grading, human review, and statistical uncertainty into a release gate.
- Recognize provider failures, API changes, and behavioral drift, and switch only to prevalidated fallback paths.
- Design Canary, human approval, rollback, incident evidence collection, and review.

## Prerequisites

- Read and write JSON in Python 3, and understand HTTP, API-key placeholders, timeout, and error handling.
- Know prompts, tokens, context windows, Embeddings, RAG, and Tool Calling.
- Understand Git commits, immutable versions, offline evaluation, and progressive release.
- No cloud platform or Kubernetes experience is required.

## Recommended sequence

1. [[llmops/foundations-and-lifecycle/01-release-units-and-version-lineage|Release Units and Version Lineage]] — answer “what exactly is running in production?”
2. [[llmops/production-engineering/02-gateways-quotas-and-resilience|Gateways, Quotas, and Resilience]] — converge provider calls at a controlled entry.
3. [[llmops/production-engineering/03-caching-latency-and-cost|Caching, Latency, and Cost]] — distinguish optimizations that improve the end-to-end task.
4. [[llmops/production-engineering/04-traces-and-privacy-boundaries|Traces and Privacy Boundaries]] — trace every decision in a request without retaining unnecessary content.
5. [[llmops/foundations-and-lifecycle/05-offline-evaluation-gates-and-regression-suites|Offline Evaluation Gates and Regression Suites]] — decide whether a change can reach production using task evidence.
6. [[llmops/production-engineering/06-canary-rollback-and-change-management|Canary, Rollback, and Change Management]] — limit blast radius and preserve a way back.
7. [[llmops/production-engineering/08-continuous-evaluation-provider-drift-and-governance|Continuous Evaluation, Provider Drift, and Governance]] — turn online feedback into auditable decisions rather than automatic rewrites.
8. [[llmops/production-engineering/07-incident-response-and-continuous-improvement|Incident Response and Continuous Improvement]] — improve tests, alerts, and release policy from failure timelines.
9. [[llmops/project-and-self-check/08-offline-release-gate-project-and-self-check|Offline Release Gate Project and Self-Check]] — run candidate gate, online observation gate, and audit tests without a real API.

## Hands-on entry point

The main project is [[llmops/project-and-self-check/08-offline-release-gate-project-and-self-check|Offline Release Gate Project and Self-Check]]. It uses only the Python standard library. It rejects duplicate JSON fields, raw invalid UTF-8, surrogate values that cannot encode stably as UTF-8 scalar sequences, and values not representable as finite `float`. It binds evaluation artifact to subject release; validates baseline/candidate comparison before binding Canary with full `candidate_gate_evidence_sha256`, display-only short fingerprint, `promoted_at`, fixed `decision_as_of`, and concurrent control. `artifact_digest_format` and the observation bundle's `evidence_digest_format` jointly declare this repository's versioned local teaching byte profile; the bundle schema/profile also enters every online decision's full digest. Do not mistake this for a signature or universal canonical JSON. Online quality and safety results derive from verifiable integer numerators and denominators, where zero denominator means unknown. Automated fallback must match the gate-bound fallback release identity and full digest, have sufficient current candidate evidence, and reject self-reference, known cycles, and known failing fallback candidates. The 74 tests cover bad binding, full-digest tampering, format mismatch, schema/profile binding, pre-release/future windows, fallback-evidence bypass, ratio-bound errors, numerator/denominator consistency, insufficient evidence preventing automatic fallback in fixtures/CLI, label coverage, and `INCOMPARABLE`. Observation can become `continue`, `investigate`, `pause`, `fallback`, `rollback`, or `human_review`.

You can reuse the data → script → PNG → alternative-text loop in [[data-visualization/07-project-agent-evaluation-dashboard#generated-results|the Agent Evaluation Dashboard]], but a release gate remains based on raw trials, slices, and gate evidence; never infer or hand-edit data from a chart.

On Windows 11 and PowerShell 7 this project runs directly. If you need an isolated interpreter, create it outside the vault:

```powershell
$llmopsVenv = Join-Path $env:TEMP 'llmops-learning-venv' # Keep the isolated environment outside the vault.
python -m venv $llmopsVenv # Create the standard-library Python environment used by this project.
& "$llmopsVenv\Scripts\Activate.ps1" # Pin subsequent python/pip to the isolated interpreter.
python -m pip --version # Verify pip/interpreter only; install no package.
python ".\docs-EN\llmops\examples\release_gate.py" audit --release-id release-safe --observation-id obs-healthy # Audit a fixed candidate and healthy observation.
```

The project has no third-party dependency. Do not create `.venv` in the knowledge base or write real keys.

## Mastery checklist

- [ ] I can name the code, API, prompt, context, retrieval, model, tools, policy, evaluation, routing, and price-accounting versions behind one online answer.
- [ ] I can distinguish rate limiting, concurrency control, timeout, retry, circuit breaking, fallback, and capacity reservation.
- [ ] I can explain different risks of prefix caching, exact-answer caching, and semantic caching.
- [ ] I can use a trace to locate whether model, retrieval, tool, or retry caused a latency/cost anomaly.
- [ ] I can block a regression in important task, safety slice, or cost with a regression suite and release gate.
- [ ] I can write Canary expansion, pause, fallback, and rollback conditions while handling delayed labels.
- [ ] I can explain why provider drift must not trigger an unvalidated automatic model switch.
- [ ] I can run ordinary, `-O`, warnings-as-errors, and combined tests and explain each blocking reason.

## Relationships to other courses

- [[mlops/00-index|MLOps]] supplies general traceability, evaluation-gate, release, and rollback ideas; LLMOps extends the release unit to a composite LLM application.
- [[runtime-monitoring/00-index|Runtime Monitoring]] owns Logs, Metrics, Traces, SLI/SLO, and alerting platform. LLMOps defines which LLM versions and quality evidence enter observation. A full evidence digest may be a Trace/Log or controlled audit field, never a Metric label.
- [[evaluation-framework/00-index|Evaluation Framework]] designs samples, metrics, and scorers. LLMOps versions and connects them to release and continuous evaluation. Online anomalies first enter controlled human triage; an alert or dashboard may not rewrite a frozen evaluation suite automatically.
- [[ai-safety/00-index|AI Safety]] and [[ai-governance/00-index|AI Governance]] define threats, approval, audit, and accountability. LLMOps makes them concrete in gates, runbooks, and evidence chains.

## Version and source notes

This route, offline project evidence, and the external material below were checked on 2026-07-22. Provider APIs, model aliases, prices, product UI, and retention capabilities can change; production implementation must recheck current documents and contracts. OpenAI appears as a provider example only and is not a required LLMOps platform.

Current OpenAI documentation marks older Evals/Graders products as in a deprecation-migration period. This course therefore uses general principles — task-specific evaluation, continuous evaluation, human calibration, and fixed scorer version — rather than treating an old product interface as a stable dependency. Current MLflow documentation distinguishes classic-ML `mlflow.models.evaluate()/EvaluationMetric` from GenAI `mlflow.genai.evaluate()/Scorer`, which are not interchangeable. The OpenTelemetry core semantic-conventions page is currently 1.43.0, while GenAI conventions moved to a separate repository; integration must pin the actual revision/schema URL and test compatibility by signal/component stability instead of applying the core-page version mechanically.

## Primary references

- [OpenAI Production best practices](https://developers.openai.com/api/docs/guides/production-best-practices) — official entry point for secrets, environment isolation, quotas, scaling, latency, and cost.
- [OpenAI Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) — prefix hits and cache usage; verify conditions by model and date.
- [OpenAI Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) — task-specific evaluation, real distribution, continuous evaluation, and human calibration.
- [OpenAI Trace grading](https://developers.openai.com/api/docs/guides/trace-grading) — structured grading of end-to-end agent traces.
- [OpenAI Data controls](https://developers.openai.com/api/docs/guides/your-data) — endpoint retention, abuse monitoring, and customer eligibility differences; it does not mean every request has zero retention.
- [MLflow for GenAI applications](https://mlflow.org/docs/latest/genai/overview/) — an example loop of production traces, feedback, evaluation datasets, and version comparison.
- [MLflow Evaluation APIs](https://mlflow.org/docs/latest/ml/evaluation/) — classic ML/GenAI evaluation-object and migration boundary.
- [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai) — official repository and schema URLs.
- [NIST AI 600-1: Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) — generative-AI lifecycle risk management.
- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) — incident response in organizational risk management.
