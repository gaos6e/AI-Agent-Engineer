---
title: "MLOps Learning Path"
tags:
  - ai-agent-engineer
  - mlops
  - learning-path
aliases:
  - MLOps
  - MLOps from Zero
source_checked: 2026-07-21
mlflow_snapshot: mlflow==3.14.0
ai_learning_stage: 7. Production, Evaluation, and Governance
ai_learning_order: 38
ai_learning_schema: 2
ai_learning_id: mlops
ai_learning_domain: production-ops
ai_learning_catalog_order: 3800
ai_learning_hard_prerequisites: []
ai_learning_track_agent_platform_order: 1150
ai_learning_track_agent_platform_kind: recommended
content_origin: original
content_status: dynamic
lang: en
translation_key: MLOps/00-目录.md
translation_source_hash: 1083bb67335b8fa0c8216de9b0e51217b8b07f1627920ecc2d415877614fcc18
translation_route: zh-CN/MLOps/00-目录
translation_default_route: zh-CN/MLOps/00-目录
---

# MLOps

## Course overview

MLOps (Machine Learning Operations) turns a one-off machine-learning experiment into an engineering system that is repeatable, reviewable, releasable, and reversible. It is not merely “deploying a model behind an API.” Problem definition, data and label versions, feature code, training environment, model artifact, evaluation evidence, and production feedback must be traceable through one chain.

This course focuses on the lifecycle of classical machine-learning and deep-learning models. [[llmops/00-index|LLMOps]] owns the composite release unit specific to LLM applications — prompts, retrievers, tools, and model-provider orchestration. [[runtime-monitoring/00-index|Runtime Monitoring]] expands logs, metrics, traces, SLOs, and alerts.

| Responsibility boundary | MLOps | LLMOps |
| --- | --- | --- |
| Release unit | Data and label version, feature/training code, environment, and model artifact; this course is authoritative | Composite release of prompt, context, retrieval snapshot, model provider, tools, and policy; [[llmops/00-index\|LLMOps]] is authoritative |
| Shared mechanism | General model-lifecycle methods for traceability, quality gates, progressive release, and rollback | Reuses those methods, extending them for LLM nondeterminism and multi-component boundaries without maintaining a duplicate general definition |
| Adjacent responsibility | [[evaluation-framework/00-index\|Evaluation Framework]] defines evaluation methods and [[runtime-monitoring/00-index\|Runtime Monitoring]] owns runtime evidence | Same; LLMOps binds that evidence to one complete LLM-application release |

> [!important] Separate version facts from vendor recommendations
> - **Version fact** — When PyPI was checked on 2026-07-21, MLflow's latest stable release was `3.14.0`, released 2026-06-17 and declaring Python `>=3.10`. This course does not install MLflow; the version is only a dynamic source snapshot.
> - **Vendor architecture recommendation** — Google Cloud's MLOps architecture article discusses CI, CD, continuous training (CT), and automation maturity. Its page says it was last reviewed on 2024-08-28. It is valuable vendor guidance, not a maturity certification every team must copy.
> - **Standard status** — NIST AI RMF 1.0 was published in 2023, while NIST's current page says the framework is under revision. This course names version 1.0 rather than presenting it as a permanently latest requirement.

## Where this course fits

Learn the machine-learning train–validate–test flow, Git, and basic APIs first. MLOps sits between “a model can train” and “a model can provide reliable value over time,” and is an engineering foundation for later LLMOps, evaluation, and AI governance.

## Learning objectives

- Record traceable evidence for a training run: data, code, parameters, environment, metrics, and artifacts.
- Design a pipeline for data checks, training, evaluation, registration, release, and rollback.
- Distinguish the jobs of model registry, quality gate, deployment strategy, and production monitoring.
- Explain why data drift, concept drift, and declining model quality are not interchangeable.
- Implement offline candidate-promotion decisions with auditable output.

## Prerequisites

- Run Python 3 scripts and understand functions, dictionaries, JSON, and exception handling.
- Understand training, validation, test sets, classification metrics, and overfitting.
- Use Git to inspect a commit identifier and understand virtual environments and dependency files.
- Have a conceptual understanding of HTTP services, batch jobs, and containers; Kubernetes experience is not required.

## Environment route: start with venv and pip, then choose a platform

Do not create `.venv` inside the Obsidian vault. To try MLflow, use a separate practice directory and lock the snapshot version:

```powershell
$practiceRoot = Join-Path $env:USERPROFILE 'Projects\mlops-learning' # Use an approved location outside the vault.
New-Item -ItemType Directory -Path $practiceRoot -Force | Out-Null # Remain idempotent when it already exists.
Set-Location $practiceRoot # Keep the environment out of the knowledge base.

py -3 -m venv .venv # Create an isolated Python 3 environment.
.\.venv\Scripts\Activate.ps1 # Activate it so pip affects only this directory.
python -m pip install --upgrade pip # Apply current pip fixes inside the environment.
python -m pip install "mlflow==3.14.0" # Install only the frozen demonstration version; recheck version and policy before real use.
python -c "from importlib.metadata import version; print(version('mlflow'))" # Verify the installed version.
python -m pip check # Check installed dependency consistency.
```

This installation command was not run for the course's offline project and requires no cloud credential. Before future use, recheck PyPI, release notes, Python constraints, and organizational security policy. Learn `venv + pip` first, then adopt `uv`, containers, or lock files by team convention.

A platform is an implementation choice, not a learning order: MLflow can provide Tracking and Registry; Kubeflow Pipelines can organize components, parameters, artifacts, and control flow on Kubernetes; KServe provides Kubernetes model-serving abstractions; a Kubernetes Deployment manages workload rollout. Begin with ordinary Python to make contracts and decisions clear, then decide whether those platforms are needed.

## Recommended sequence

1. [[mlops/foundations-and-lifecycle/01-experiment-and-reproducibility-tracking|Experiment and Reproducibility Tracking]] — answer “where did this result come from?”
2. [[mlops/foundations-and-lifecycle/02-data-features-and-training-pipelines|Data, Features, and Training Pipelines]] — turn the data contract and training steps into a repeatable process.
3. [[mlops/foundations-and-lifecycle/03-model-registry-and-candidate-promotion|Model Registry and Candidate Promotion]] — understand versions, aliases, signatures, and promotion evidence.
4. [[mlops/production-engineering/04-ci-cd-and-automated-quality-gates|CI, CD, and Automated Quality Gates]] — put tests and evaluation in the release path.
5. [[mlops/production-engineering/05-deployment-canary-and-rollback|Deployment, Canary, and Rollback]] — choose batch, online, shadow, or progressive release.
6. [[mlops/production-engineering/06-model-monitoring-drift-and-feedback|Model Monitoring, Drift, and Feedback]] — observe changes in data, predictions, and labeled quality.
7. [[mlops/production-engineering/07-incidents-rollback-and-retraining-decisions|Incidents, Rollback, and Retraining Decisions]] — decide whether evidence calls for loss containment, repair, or retraining.
8. [[mlops/production-engineering/08-platform-security-and-governance|Platform Security and Governance]] — put identity, secrets, supply chain, audit, and risk accountability into the lifecycle.
9. [[mlops/project-and-self-check/08-offline-model-promotion-project-and-self-check|Offline Model Promotion Project and Self-Check]] — complete lineage, candidate-promotion, drift-investigation, and rollback decisions.

## Hands-on entry point

The main project is [[mlops/project-and-self-check/08-offline-model-promotion-project-and-self-check|Offline Model Promotion Project and Self-Check]]. It uses only the Python standard library. It reads a candidate-artifact manifest and a production observation window, then strictly checks data, code, environment, training configuration lineage, tests, metrics, signature, drift, and rollback conditions. The production window must bind to the approved candidate-gate fingerprint and fixed artifact, explicitly record shadow or Canary stage, total samples, labeled samples, and critical-slice samples, then emit an auditable action.

## Mastery checklist

- [ ] I can trace a prediction back to data snapshot, code commit, environment, parameters, and model artifact.
- [ ] I can explain why reproducibility does not mean bit-for-bit equality on every hardware platform.
- [ ] I can write a minimal contract for data, model input/output, and release artifact.
- [ ] I can distinguish CI, continuous training (CT), and CD.
- [ ] I can design candidate promotion, Canary observation, and rollback evidence from business risk rather than copying a fixed threshold.
- [ ] I can distinguish data drift, concept drift, and true performance decline.
- [ ] I can define identity, secrets, artifact-integrity, audit, and human-approval boundaries for a training platform and model service.
- [ ] I can run the project's passing and blocked cases and explain every decision.

## Relationships to other courses

- [[llmops/00-index|LLMOps]] reuses versioning, evaluation gates, and release concepts, but expands a release unit to a combination of prompt, context, retrieval, model, and tools.
- [[runtime-monitoring/00-index|Runtime Monitoring]] owns logs, metrics, and traces from model services, including SLOs, alerts, dashboards, and incident response.
- [[machine-learning/00-index|Machine Learning]] and [[deep-learning/00-index|Deep Learning]] supply model and metric foundations. [[data-cleaning/00-index|Data Cleaning]] supplies usable data. [[evaluation-framework/00-index|Evaluation Framework]] determines how offline evidence is constructed. [[ai-governance/00-index|AI Governance]] constrains approval, audit, and accountability.

## Primary references

All materials below were checked on 2026-07-21. Commands and UI can change by version; real projects should pin versions and run minimal verification.

- [PyPI: MLflow 3.14.0](https://pypi.org/project/mlflow/) — snapshot of stable release, date, and Python constraint.
- [MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/) — tracking experiments, runs, parameters, metrics, and artifacts.
- [MLflow Model Registry workflow](https://www.mlflow.org/docs/latest/ml/model-registry/workflow/) — model versions, aliases, tags, and provenance; fixed stages are deprecated and should not anchor a new workflow.
- [MLflow Model Deployment](https://mlflow.org/docs/latest/ml/deployment) — overview of packaging, dependencies, and targets.
- [Google Cloud: MLOps continuous delivery and automation pipelines](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning) — CI, CD, CT, and predictive-ML automation architecture.
- [Kubeflow Pipelines: Pipeline](https://www.kubeflow.org/docs/components/pipelines/concepts/pipeline/) — components, parameters, artifacts, control flow, and runs.
- [KServe documentation](https://kserve.github.io/website/) — `InferenceService`, model serving, traffic, and versioning capabilities.
- [Kubernetes Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) and [Canary Deployments](https://kubernetes.io/docs/concepts/workloads/management/#canary-deployments) — progressive replacement, revision history, rollback, and stable/Canary parallel modes.
- [Google SRE: Service Level Objectives](https://sre.google/sre-book/service-level-objectives/) — user-centered metrics and objectives.
- [NIST AI RMF 1.0](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10) — published AI risk-governance framework version 1.0.
- [NIST SP 800-218 SSDF 1.1](https://csrc.nist.gov/pubs/sp/800/218/final) — integrating secure practice into the software-development lifecycle.
- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) — incident response and risk-management framework.
