---
title: "Data Governance, Privacy, Licensing, and Worker Safety"
tags:
  - ai-agent-engineer
  - data-annotation
  - data-governance
  - privacy
aliases:
  - Annotation Data Governance
  - Annotation Worker Safety
content_origin: original
content_status: validated
source_checked: 2026-07-22
source_baseline:
  - NIST AI RMF
  - NIST Privacy Framework
  - W3C PROV-O
  - ILO digital labour and occupational safety guidance
  - Datasheets for Datasets
lang: en
translation_key: 数据标注/08-数据治理、隐私、许可与劳动安全.md
translation_source_hash: e048791c8de218443253b28dbefc61846467163ce112ef25dd2bbac0a65213e9
translation_route: zh-CN/数据标注/08-数据治理、隐私、许可与劳动安全
translation_default_route: zh-CN/数据标注/08-数据治理、隐私、许可与劳动安全
---

# Data Governance, Privacy, Licensing, and Worker Safety

## Objective

Treat annotation as controlled data processing and a labor arrangement. Before assignment, confirm source, purpose, minimization, access, content risk, licensing, retention, and accountability. When a problem occurs, be able to stop, triage, withdraw, and assess downstream impact.

This lesson provides an engineering-control checklist, not legal conclusions for any jurisdiction. Personal information, sensitive data, employment relationships, contracts, copyright or database rights, and cross-border processing must be confirmed by authorized organizational roles for the actual source and applicable requirements.

## Minimum governance gates before assignment

| Gate | Evidence to retain | What it cannot prove |
| --- | --- | --- |
| Purpose and necessity | Task card, use, affected people, minimum fields, and accountable owner | A legitimate purpose permits unlimited collection |
| Source and authorization | Source type plus controlled reference to license, contract, consent, or organizational authorization and allowed scope | Public accessibility permits training or republication |
| Sensitivity and minimization | Classification, field allowlist, de-identification or masking rule, prohibited fields, and residual risk | Removing a name or hashing always anonymizes |
| Secure access | access_scope, role, least privilege, controlled environment, download or copy limits, and audit | A link is already safely authorized |
| People and content risk | Content grade, notice, opt-out or escalation, exposure limits, support, and appeal path | An annotator “clicked agree,” so there is no risk |
| Retention and withdrawal | retention_class, expiry or deletion process, source-withdrawal contact, and downstream inventory | Deleting the entry file automatically removes every downstream use |

Separate original materials from annotation tasks first. Annotators receive only the minimum context needed for the current judgment; sensitive originals, identity mappings, authorization documents, and complete audit logs stay in controlled systems. Do not copy raw text, keys, personal information, private URLs, or screenshots into guidelines, public issues, free-text rationales, or external-model prompts.

## Licensing and source are not Boolean fields

One dataset can have source terms, contractual use restrictions, personal-information processing requirements, model-service terms, confidentiality duties, and republication restrictions. Preserve a **controlled reference** and state for every source or release scope rather than an unverifiable licensed: true field:

- Source or provider and acquisition time.
- Permitted uses, such as pilot annotation, internal training, evaluation, research, or public release, plus geographic and time limits.
- Required attribution, authorship, retained notices, and downstream restrictions.
- Owner, exceptions, review date, and withdrawal or expiry handling.
- Whether input, tool services, and exported artifacts cross the same scope.

“Open source,” “visible on a web page,” “synthetic,” and “de-identified” do not automatically authorize arbitrary training, republication, or transfer to an external service. When source status is unknown or review is pending, isolate the candidate or block broader assignment or release rather than having the data team infer a conclusion.

## Privacy and security: minimize before cleanup

De-identification is one exposure-reduction control, not a universal proof of reversibility, anonymity, or compliance. Combined quasi-identifiers, rare text, time or location, images, audio, and model output can still reidentify a person. Minimize fields before the pool, use role separation, short-lived credentials, controlled viewing environments, and on-demand audit. For high-risk tasks, validate the guideline first on synthetic or substitute samples.

An annotation project must also state whether it permits downloading, copying, screenshots, external-tool calls, raw-content export, and repetition of sensitive content in rationales. Do not send sensitive samples to an unapproved third-party API by default, and do not use annotators without access authorization as a fallback “human review.” See [[privacy-computing/00-index|Privacy Computing]] for further technical boundaries and [[ai-governance/00-index|AI Governance]] for data-asset, vendor, and approval responsibilities.

## Annotator safety, dignity, and appeals

Harmful, violent, hateful, sexual, child-related, or personally distressing material can create psychological, social, or safety risks. The task type and people’s situation should drive risk assessment. At minimum:

1. Before assignment, provide understandable content warnings, task purpose, data-processing boundaries, and compensation or performance rules. Offer voluntary participation or equivalent alternative work for high-exposure tasks rather than treating refusal or abstention as poor performance.
2. Set risk-adjusted access, batch size, continuous exposure time, breaks or rotation, two-person or expert escalation, and emergency-stop mechanisms. Do not use pure output volume to compress judgment or recovery time.
3. Provide confidential reporting, anti-harassment, and appeal channels. State who handles harmful content, platform or customer pressure, incorrect deductions, or tool failures. Retain necessary audit while minimizing monitoring data about annotators.
4. Match training, support resources, and incident response to the actual risk. Reading a warning is not sufficient control of harm.

The ILO identifies occupational safety, psychosocial risks, algorithmic management, and worker participation in digital or platform work as topics requiring active governance. This course therefore treats people’s safety as an engineering gate; particular protections and labor duties still depend on employers, platforms, contracting parties, and applicable regimes.

## Withdrawal, deletion, and downstream impact

~~~mermaid
flowchart TD
    A[Review source, purpose, and authorization] --> B[Minimization and content grading]
    B --> C[Controlled-access annotation task]
    C --> D[Appended annotation / adjudication events]
    D --> E[Release gate: quality, leakage, privacy, licensing, and people risk]
    E --> F[Controlled release_id and use inventory]
    R[Withdrawal, expiry, or incident] --> S[Stop new assignment and record tombstone]
    S --> T[Query affected source_revision / release_id]
    T --> U[Assess dataset, evaluation, training, and report impact]
    U --> V[Isolate, replace, rebuild, or notify under an approved plan]
    V --> W[Keep minimum audit evidence and conclusions]
~~~

tombstone means that a source or version can no longer be consumed by new workflows and triggers an impact query. It does not prove that a model has “forgotten,” nor does it authorize deleting every audit record. For trained models, derived features, evaluation sets, caches, and published reports, assess isolation, rebuilding, retraining, notification, or retention based on their traceability relationship and record who approved the disposition.

A controlled ledger can store access_scope, license_or_authorization_ref, retention_class, content_risk, worker_safety_plan_ref, and deletion_request_ref for each sample or release. These fields point to evidence or process; they must not be mistaken for automatic legal or privacy determinations.

## When a problem occurs

For unauthorized content, a suspected sensitive-information leak, severely harmful content, an annotator safety incident, or source withdrawal: stop further assignment and copying; retain a necessary controlled event reference; do not expand the content into chat, screenshots, or public logs just to investigate. Triage through the established incident response, privacy, security, labor-owner, and release-withdrawal paths. If necessary, change affected samples to exclude or freeze them pending review, but do not state that downstream removal is complete without evidence.

## Exercise

Write a one-page governance appendix for an “review Agent failure trajectories” task. Specify the source scope of target data, prohibited fields, three access_scope values, one opt-out or escalation path for high-exposure content, the minimum retention class, the release_id inventory to query after a source withdrawal, and conclusions that still need qualified people inside the organization to confirm.

## Mastery check

- [ ] I distinguish source and authorization evidence, access permission, privacy risk, and release eligibility instead of reducing them to one Boolean field.
- [ ] I give annotators only the necessary minimum and do not copy raw sensitive data into guidelines, rationales, or external tools.
- [ ] I can design notice, opt-out, exposure limits, support, reporting, and escalation for harmful content without punishing abstention by volume.
- [ ] I know that withdrawal requires a source_revision → release_id → downstream-use query and that tombstone does not prove a model has forgotten.

Next: [[data-annotation/09-versioning-release-and-production-feedback|Versioning, Release, and Production Feedback]].

## References

Sources checked on 2026-07-22.

- [NIST Privacy Framework](https://www.nist.gov/privacy-framework)
- [NIST AI RMF Core: Governance, Third-Party Data, Human Oversight, and Continuous Monitoring](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- [W3C PROV-O: entities, activities, agents, and derivation](https://www.w3.org/TR/prov-o/)
- Gebru et al. (2021). [Datasheets for Datasets](https://arxiv.org/abs/1803.09010)
- [ILO: Occupational safety and health in AI and digitalized work](https://www.ilo.org/publications/revolutionizing-health-and-safety-role-ai-and-digitalization-work)
