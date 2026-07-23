---
title: "Platform Security and Governance"
tags:
  - mlops
  - platform-security
  - ai-governance
aliases:
  - MLOps Platform Security
  - MLOps Governance
source_checked: 2026-07-14
lang: en
translation_key: MLOps/02-生产工程/08-平台安全与治理.md
translation_source_hash: ba695204ae96a609f78a3af2638b9c6486f81eebf9e9d66a2c9fb38d184ccad5
translation_route: zh-CN/MLOps/02-生产工程/08-平台安全与治理
translation_default_route: zh-CN/MLOps/02-生产工程/08-平台安全与治理
---

# Platform Security and Governance

## Goal

Draw MLOps trust boundaries, give people, pipelines, model services, and artifact repositories least privilege, and turn risk, approval, audit, deletion, and incident response into inspectable lifecycle evidence.

> [!important] Standard version and dynamic platform facts
> NIST AI RMF 1.0 was published in 2023. When the NIST page was checked on 2026-07-14, it explicitly said 1.0 was being revised. This lesson uses its `GOVERN / MAP / MEASURE / MANAGE` organization and does not call it a permanently latest requirement. Kubernetes, Kubeflow, KServe, and MLflow interfaces and configuration are dynamic facts; real deployment must pin versions and read their matching documentation.

## Identify principals and assets first

A minimal platform commonly contains:

- developers, reviewers, publishers, and platform administrators;
- CI, training, evaluation, registration, deployment, and monitoring workloads;
- source repository, data repository, tracking, registry, and artifact storage;
- online service, batch job, logs, label backfill, and alerting systems;
- databases, queues, model supply chain, and external APIs.

Assets are more than model files. Training data, labels, features, environment lockfiles, container images, signatures, evaluation sets, approval records, service identity, and logs can change model behavior or expose sensitive information.

In a diagram, mark principal, identity, network boundary, allowed action, and audit location for each data flow. An arrow labeled “train → deploy” alone cannot reveal who can bypass a quality gate, replace an artifact, or read production data.

## Least privilege and separation of duties

Split identity by workload:

| Principal | Example least privilege | Must not own by default |
| --- | --- | --- |
| CI | Read source, write test report | Production data or deployment authority |
| Training job | Read approved data snapshot, write a new artifact | Move production alias |
| Evaluation job | Read candidate and frozen evaluation set, write report | Modify candidate artifact |
| Promotion service | Read report, write candidate status | Rewrite evaluation result |
| Deployment service | Read approved fixed digest, update target environment | Arbitrary training-data read |
| Online model | Read its artifact and required features | Registry administration or training-environment write |
| Human reviewer | View redacted evidence, approve one action | Replace artifact content directly |

“Platform administrator can do everything” can be operationally real, but high-risk operations still need short-lived authority, dual review, and independent audit. Do not share service accounts. Bind an approval to candidate version, artifact digest, policy version, target environment, and validity period.

## Secrets and private data

- Inject credentials only from a secret-management boundary, never code, notebook, manifest, log, or model metadata.
- Use different identities and data for development, test, and production.
- Prefer minimized, redacted, or synthetic examples for training and debugging.
- Define data purpose, retention period, deletion process, and cross-region restriction.
- Do not log raw sensitive features; keep stable request ID and version instead of full payload when needed.
- A deletion request covers data copies, features, indexes, cache, artifacts, and reasonably removable backups.

A Kubernetes `Secret` is an API object for sensitive data, not an automatic vault. Kubernetes documentation notes that, unless encryption at rest is configured, the API server stores data in etcd in a plaintext representation. A real cluster also needs RBAC, encryption at rest, backup protection, rotation, and access audit. Base64 is not encryption.

## Artifacts and software supply chain

A candidate must prove more than “it can download”; prove it is the object evaluated:

1. bind model, preprocessor, signature, and environment in one release manifest;
2. identify immutable artifact with content digest;
3. record builder, source commit, data snapshot, training configuration, and pipeline run;
4. minimize build environment; lock dependencies and check vulnerabilities, licenses, and provenance;
5. at release, verify digest, provenance, and approval rather than accepting movable `latest`;
6. retain old versions and dependencies and rehearse loading and rollback;
7. if training or release is compromised, revoke identity, isolate artifact, and trace affected versions.

NIST SP 800-218 SSDF 1.1 supplies a general framework for integrating security practice into a software-development lifecycle. It is not an MLOps-specific tool list; apply it to software builds, data, and model artifacts together.

## Multi-tenant and compute isolation

When GPUs, notebooks, object storage, or clusters are shared, check:

- namespace, project, account, and storage-path isolation;
- nonprivileged workload identity plus restricted host mounts and network;
- CPU, memory, GPU, temporary disk, and task-duration quotas;
- whether user-submitted code or model formats can execute arbitrary code;
- whether cache can cross tenants and whether its key includes permission and data version;
- whether failure logs, core dumps, or temporary directories leak data.

Never directly load an untrusted executable model serialization format. Even with a safe format, preprocessing plugins, container entrypoints, and custom code require supply-chain verification and sandboxing.

## Governance is not one pre-release approval form

Use the four NIST AI RMF 1.0 functions to organize evidence:

- **GOVERN** — owners, policy, risk tolerance, third parties, and incident-escalation path.
- **MAP** — use, users, affected groups, data source, setting, and possible harm.
- **MEASURE** — data quality, task metrics, critical slices, robustness, security, privacy, and monitoring coverage.
- **MANAGE** — accept, mitigate, transfer, or avoid risk; set release, stop, rollback, and retirement conditions.

These functions span problem definition, experiment, candidate promotion, deployment, monitoring, incident, and retirement. A low-risk internal batch job and a high-impact automated decision must not share exactly the same approval bar.

## Auditable promotion record

At minimum answer:

```text
Who: reviewer and executing-service identity
What: fixed candidate_id, artifact_digest, code and data versions
Basis: tests, overall/slice metrics, risk exception, and policy version
Where: target environment, traffic scope, and release time
How to contain loss: observation window, stop condition, rollback version, and owner
Result: deployed digest, events, monitoring conclusion, and follow-up
```

An alias is convenient for deployment, but an audit record stores the fixed version and digest it resolved at the time. Moving an alias later must not alter historical meaning.

## Common mistakes and debugging

- **CI uses production-admin credentials** — give each stage a separate identity with constrained resource targets.
- **Correct model digest but ignore preprocessor** — bind the whole release unit in the manifest.
- **Kubernetes Secret is base64, therefore encrypted** — inspect at-rest encryption and etcd/backup protection.
- **Approval says only “approve release”** — bind artifact digest, policy, environment, validity, and observation plan.
- **More detailed logs always help audit** — minimize data first; secrets and raw personal data do not belong in logs.
- **Retirement means stop serving** — also revoke routing, credentials, aliases, manage artifact/data retention, and update documentation.

## Practical exercise

Threat-model a platform that “trains and publishes a fraud model nightly”:

1. draw source, data, CI, training, registry, deployment, online service, and monitoring boundaries;
2. write read/write permission for each principal;
3. design one candidate-promotion approval record;
4. simulate artifact-digest mismatch, leaked CI credential, and production data entering logs;
5. write containment, evidence preservation, recovery, and credential rotation;
6. identify which risks enter automated gates and which need human review.

## Mastery checklist

- [ ] I can distinguish a Secret object, encryption, RBAC, and external secret management.
- [ ] I can assign different least privilege to CI, training, evaluation, promotion, and deployment.
- [ ] I can bind model, preprocessing, signature, environment, and provenance in one manifest.
- [ ] I can organize lifecycle risk evidence with GOVERN, MAP, MEASURE, and MANAGE.
- [ ] I can design an approval containing fixed digest, policy version, stop condition, and rollback owner.

## Next step

Enter [[mlops/project-and-self-check/08-offline-model-promotion-project-and-self-check|Offline Model Promotion Project and Self-Check]] to practice lineage, promotion, drift investigation, and rollback with strict JSON and runnable tests.

## References

All materials below were checked on 2026-07-14:

- [NIST AI RMF 1.0](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)
- [NIST AI Risk Management Framework current page](https://www.nist.gov/itl/ai-risk-management-framework) — says version 1.0 is under revision.
- [NIST SP 800-218 SSDF 1.1](https://csrc.nist.gov/pubs/sp/800/218/final)
- [Kubernetes: Good practices for Secrets](https://kubernetes.io/docs/concepts/security/secrets-good-practices/)
- [Kubernetes: Encrypting Confidential Data at Rest](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/)
- [Kubeflow Pipelines: Pipeline](https://www.kubeflow.org/docs/components/pipelines/concepts/pipeline/)
- [KServe documentation](https://kserve.github.io/website/)
