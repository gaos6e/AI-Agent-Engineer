---
title: "CI, CD, and Automated Quality Gates"
tags:
  - mlops
  - cicd
aliases:
  - ML Continuous Delivery
source_checked: 2026-07-14
lang: en
translation_key: MLOps/02-生产工程/04-CI、CD与自动化质量门.md
translation_source_hash: 62783aaf8cf2381ea4c3bcdbcb3c02b4a2c7f719a9edebaa613c16635189ece5
translation_route: zh-CN/MLOps/02-生产工程/04-CI、CD与自动化质量门
translation_default_route: zh-CN/MLOps/02-生产工程/04-CI、CD与自动化质量门
---

# CI, CD, and Automated Quality Gates

## Goal

Distinguish continuous integration, continuous training, and continuous delivery, then turn model evaluation into explainable release gates.

## Three automation paths

| Path | Trigger | Main output | Core question |
| --- | --- | --- | --- |
| CI (continuous integration) | Code or configuration change | Tested code package | Is the change mergeable? |
| CT (continuous training) | New data, schedule, or drift signal | New candidate model | Is producing a new candidate warranted? |
| CD (continuous delivery/deployment) | Candidate approval | Deployable or released version | Can it enter the target environment safely? |

Automation does not mean every change deploys directly. High-risk systems, sparse-label systems, or systems with hard-to-reverse impact can retain human approval. The important property is that required approval evidence is produced automatically and consistently.

## What CI checks

- code formatting, static checks, and unit tests;
- feature-function boundaries and offline/online consistency;
- data contracts, schemas, and leakage-prevention tests;
- a minimal training-script smoke run;
- dependency vulnerabilities, licenses, and sensitive-information checks;
- repeatable artifact build, clear entrypoint, and configuration.

Do not run expensive full training on every small commit. Start with a small-data smoke test, then trigger complete training after merge or on a schedule.

## Quality-gate shape

An auditable gate emits **pass/block, every reason, and the policy version used**. Common conditions are:

1. required lineage fields are complete;
2. data and code tests pass;
3. overall candidate metric meets policy relative to the champion;
4. no critical slice degrades beyond its allowed amount;
5. latency, memory, or batch duration stays in budget;
6. artifact digest, signature, and rollback version are available.

“Accuracy exceeds a fixed number” is usually insufficient. With imbalanced data, inspect recall, precision, or cost; with metric randomness, compare confidence intervals or repeated-run stability.

## Safe CD steps

```text
Resolve fixed artifact → build environment → deploy to test environment → smoke test
→ shadow or Canary → observe user SLI and model signals → expand or roll back
```

Keep input version and result at every step. If a release tool receives only “deploy champion” without recording the resolved version, later incident review cannot be precise.

## Failure must be understandable

Unhelpful: `gate failed`.

Actionable:

```text
BLOCK: critical_slice.recall=0.72, below baseline=0.78;
allowed regression by this policy=0.02; policy_version=promotion-v3.
```

The latter gives comparison target, observation, and policy source. The threshold remains a project decision, not an industry-wide truth.

## Exercise and self-check

Design CI, CT, and CD for a daily fraud-detection model. Mark failures that only block a code merge, block candidate generation, block release while retaining the candidate, or need human approval. Why should a drift alert not directly trigger unreviewed deployment? Why must a quality gate retain both policy and baseline version?

## Next step

Quality gates decide whether release is worth attempting; deployment strategy limits the attempt's blast radius. Continue with [[mlops/production-engineering/05-deployment-canary-and-rollback|Deployment, Canary, and Rollback]].

## References

- [Google Cloud: MLOps continuous delivery and automation pipelines](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning) — checked 2026-07-14; CI/CD/CT are vendor architecture guidance.
- [MLflow Model Deployment](https://mlflow.org/docs/latest/ml/deployment) — checked 2026-07-14.
- [Kubernetes Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) — checked 2026-07-14.
