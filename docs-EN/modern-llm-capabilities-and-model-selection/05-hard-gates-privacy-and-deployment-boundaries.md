---
title: "Hard Gates, Privacy, and Deployment Boundaries"
tags:
  - llm
  - privacy
  - deployment
  - risk
aliases:
  - Hard gates for model selection
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
lang: en
translation_key: 现代LLM能力与模型选择/05-硬门槛、隐私与部署边界.md
translation_source_hash: c0b1b832a1fe2a243207780cd1bdb862884b855cfe0e9ad91a0c84e259ba800f
translation_route: zh-CN/现代LLM能力与模型选择/05-硬门槛、隐私与部署边界
translation_default_route: zh-CN/现代LLM能力与模型选择/05-硬门槛、隐私与部署边界
---

# Hard Gates, Privacy, and Deployment Boundaries

## Goal

Express requirements that cannot be offset by an average score as gates executed first, and retain verifiable evidence for every gate.

## Core concepts

A **hard gate** is a Boolean condition that every candidate must satisfy. A candidate that does not pass cannot enter weighted ranking, even when its quality, speed, or price is better. Common gates include:

| Category | Example | Evidence owner |
| --- | --- | --- |
| Capability | Structured output, target language, tool protocol | Engineering probes + official documentation |
| Data | Training use, retention, residency, deletion, cross-border transfer | Privacy/legal + contract |
| Security | Identity isolation, encryption, auditing, vulnerability response | Security review + control tests |
| Deployment | Hosting region, self-hosting, hardware, offline availability | Platform team + capacity tests |
| License | Weights, code, outputs, and derivative use | Legal + license text |
| Operations | Maximum p95, unit cost, quota, and availability | Load tests + SLA |
| Quality | Minimum success rate/zero-tolerance failures for critical slices | Frozen evaluation + human review |

“Evidence unknown” is not a pass. It should be a **parseable, candidate-level blocked status** that an authorized person can resolve with evidence or an approved exception. Do not silently substitute `false/0` for unknown, and do not let one candidate needing more evidence hide the report for every other candidate.

## Why this matters

A candidate that fails data-residency requirements cannot “offset” a compliance gap with high accuracy. A candidate that can perform unauthorized writes cannot compensate with low cost. The NIST Generative AI Profile emphasizes identifying, measuring, managing, and governing risk throughout the lifecycle, so a selection record is not merely a performance table: it also contains sources, responsibility, and residual risk.

## How to implement it

Fix these fields for every gate:

```text
gate_id, predicate, threshold/unit,
evidence_uri, evidence_checked_at, evidence_owner,
result(PASS/FAIL/BLOCKED), exception_id, expiry
```

The offline project represents candidate evidence as a strict object:

```json
{
  "status": "verified",
  "uri": "urn:example:model-card:v3",
  "checked_on": "2026-07-17",
  "owner": "model-governance",
  "expires_on": "2026-08-17",
  "missing_items": []
}
```

How to read the fields (strict JSON cannot contain end-of-line comments, so the example remains a parseable configuration):

- `status` states the result of the current evidence verification. Here, `verified` is not the model’s self-report but the conclusion of a controlled process.
- `uri` identifies where the original evidence or record can be checked. It should not be an unverifiable natural-language description.
- `checked_on` records the date of the most recent human or controlled-process verification, making it possible to judge whether the conclusion is stale.
- `owner` is the role accountable for the evidence and able to provide it or explain an exception; it is not a substitute for the model vendor’s name.
- `expires_on` states when this evidence becomes invalid. Reverify it after that date instead of continuing to rely on it.
- `missing_items` lists material that is still absent. A verified status uses an empty array; a `blocked` status must explicitly list its gaps.

`verified` requires a URI, owner, verification date, expiry date, and no missing items; expiration produces an `evidence_expired` gate failure. `blocked` must list `missing_items` and produces candidate-level `evidence_status_blocked` plus one failure for each missing item. Missing fields, unknown fields, or contradictory statuses are still a malformed schema and reject the whole input. Only “the schema is valid but evidence is incomplete” is a blocked candidate within a comparable report.

A useful execution order is: evidence completeness → legal/data/security → interface and deployment → critical quality → cost and latency. Stop further score polishing after a failure, while retaining raw evaluation for diagnosis.

For hosted models, verify the particular service, region, account tier, and contract rather than assuming the policy is identical for the same model on different clouds. For self-hosted models, include hardware, quantization, inference engine, concurrency, and patch responsibility in the selection object. Static capability labels cannot replace behavioral gates either: when a task requires structured output or tool calling, check `min_structured_output_rate` and `min_tool_success_rate` separately.

## Common failures

- Describing privacy as a vendor’s `yes/no` marketing field.
- Using a weighted total to offset a security or license failure with a high-quality candidate.
- Retaining only webpage screenshots, not the URL, date, contract version, and scope.
- Equating self-hosting with automatic security and ignoring image, weights, runtime, and operations responsibility.
- Reusing a conclusion after a gate expires, or creating an exception without an owner and expiry.

## How to validate

Inject a failure: set the highest-quality candidate’s `training_use` to disallowed and remove its data-residency evidence. The scorecard must exclude it and give it no weighted score. Then check that every exception has an explicit approver, scope, and expiration time.

## Practice task

Write 10 gates for a RAG application containing personal data. Ask security, platform, and product stakeholders to each identify one question that a model benchmark cannot answer, and retain evidence gaps as blocking results too.

## References

- NIST, [AI 600-1: Generative Artificial Intelligence Profile](https://doi.org/10.6028/NIST.AI.600-1)
- Mitchell et al., [Model Cards for Model Reporting](https://doi.org/10.1145/3287560.3287596)
- [NIST AI Resource Center](https://airc.nist.gov/)
- [[privacy-computing/00-index|This knowledge base: Privacy Computing]]
