---
title: "Privacy Evaluation and Leak Response"
aliases:
  - Privacy Evaluation and Breach Response
  - Privacy validation and incident response
tags:
  - privacy
  - evaluation
  - incident-response
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: 隐私计算/02-控制与治理/06-隐私评测与泄露响应.md
translation_source_hash: 8b27b7093badb4319235e3528e9fc0f45268ba4f18b424f789c907f692bebe4a
translation_route: zh-CN/隐私计算/02-控制与治理/06-隐私评测与泄露响应
translation_default_route: zh-CN/隐私计算/02-控制与治理/06-隐私评测与泄露响应
---

# Privacy Evaluation and Leak Response

## Goal of this lesson

Break a privacy claim into five layers of evidence—design, mechanism, implementation, system, and attack. Monitor purpose, budget, access, output, proofs, and deletion, and contain impact without creating secondary data spread when a leak or inference-risk incident occurs.

## Privacy evaluation is not one score

### 1. Design and governance evidence

Check purpose and non-goals, field necessity, subjects and contribution, parties, trust boundaries, retention and deletion, output recipients, responsibility, and legal or policy questions still to confirm. Without this layer, a technical mechanism does not know whom to protect.

### 2. Mechanism evidence

For DP, check adjacency, clipping, parameters, randomized mechanism, and accounting. For MPC and secure aggregation, check adversaries, collusion, dropout, and output. For FHE, check parameters, keys, and supported computation. For TEEs, check the attestation chain, measurements, and patches. A paper proof covers only its explicit model; it does not automatically cover a product implementation.

### 3. Implementation and configuration evidence

Check versions, provenance, parameters, randomness, numeric bounds, concurrent budget, access controls, keys, logs, failures/retries, default configuration, and upgrade regressions. A cryptographic library called incorrectly can provide none of its theoretical guarantee.

### 4. End-to-end system evidence

Trace raw data, prompts/RAG, training, inference, metrics, caches, embeddings, models, output, debugging, and backups. Check for an export, administrator, offline-copy, or vendor path that bypasses the formal mechanism.

### 5. Attack and misuse evaluation

Within authorized scope, test linkage re-identification, membership or attribute inference, model inversion or extraction, differencing and small-group queries, malicious clients, collusion, participant-set manipulation, side channels, and output bypasses. Use synthetic or explicitly authorized data, recording attacker knowledge, samples, versions, success criteria, and limits. One failed attack does not prove absence of risk.

## Report utility and privacy together

Report overall and group utility, random variation, error types, latency/resources, budget, and privacy claim. Optimizing average accuracy alone can hurt smaller groups; reporting theoretical ε alone can hide implementation bypasses. Freeze data, mechanism, accounting, and grading rules before comparing versions.

## Runtime monitoring

| Object | Signals |
| --- | --- |
| Purpose and access | Off-purpose query, cross-tenant access, unusual export, sudden administrator increase |
| Release and budget | Budget reservation and consumption, concurrent conflict, too-small group, repeat/differencing query |
| Protocol and cryptography | Changed participant/dropout/collusion assumptions, attestation failure, key operation, version drift |
| Data lifecycle | New field, expired retention, deletion failure, recurrence after backup restore, model/vector residue |
| Attack results | Linkage or membership-inference success rate, sensitive-output hit, unusual recipient |

Telemetry still follows minimization. Use event IDs, classifications, hashes, and controlled evidence locations instead of copying complete personal data. Restrict access, protect integrity, and set retention periods.

## Privacy incident response

1. **Prepare**: create data and system inventory, contacts, severity, processing pause, export block, credential revocation, release withdrawal, key handling, and deletion runbooks.
2. **Detect and scope**: establish data categories, subjects, regions, recipients, versions, time window, query/model/log paths, and whether access remains possible.
3. **Contain**: stop affected processing/output, isolate data and identities, freeze budget or knowledge source, withdraw public artifacts. Do not let “continue forensics” expand the leak.
4. **Preserve evidence**: retain the minimum necessary incident, configuration, version, and hash evidence with controlled access and chain of custody; avoid copying raw personal data.
5. **Eradicate and recover**: fix fields, authorization, mechanism, budget, or protocol; rotate keys; clear cache/vector/backup paths; rerun attack and ordinary regressions; restore in stages.
6. **Review**: add the real path to risk assessment, regression, monitoring, and deletion/incident drills; record residual risk and owner.

Whether an event is legally a breach, whom to notify, and the deadline depend on region, data, role, and facts. Qualified privacy and legal teams must decide; this course gives no universal notification period.

## Common errors

- Declaring a model free of privacy risk after one membership-inference attempt fails.
- Testing only an algorithm notebook, not API, cache, log, or administrator export.
- Copying an entire dataset into an uncontrolled spreadsheet or chat tool for incident investigation.
- Deleting the primary database but ignoring recoverable backup, model, vector, and downstream recipient.
- Changing mechanism parameters without rerunning utility, fairness, and attack evaluation.

## Exercise and self-check

Simulate public statistics that identify a small group. Write the discovery signal, immediate withdrawal/block, scope of historical queries and recipients, evidence minimization, mechanism/group repair, recovery gate, and legal escalation points. Then turn the path into two automated regressions and one drill.

- [ ] Can distinguish mechanism guarantee, implementation evidence, and end-to-end privacy outcome.
- [ ] Can evaluate privacy, utility, group impact, and runtime cost together.
- [ ] Can monitor budget, access, output, attestation, keys, and deletion.
- [ ] Can retain required evidence during investigation without creating secondary data spread.

## Next step

Finish with [[privacy-computing/03-project-and-self-assessment/07-project-offline-privacy-solution-review|Offline Privacy Solution Review]].

## References

- [NIST Privacy Framework](https://www.nist.gov/privacy-framework) and the [PF 1.1 project page](https://www.nist.gov/privacy-framework/new-projects/privacy-framework-version-11) (accessed 2026-07-21; PF 1.1 final had not been published, and the page remained Initial Public Draft/coming soon)
- [NIST SP 800-226](https://csrc.nist.gov/pubs/sp/800/226/final) (final, March 2025)
- [NIST IR 8053](https://doi.org/10.6028/NIST.IR.8053) (de-identification risk)
