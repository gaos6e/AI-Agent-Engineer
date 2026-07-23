---
title: "Versioning, Release, and Production Feedback"
tags:
  - ai-agent-engineer
  - data-annotation
  - data-versioning
  - production-feedback
aliases:
  - Annotation Release and Feedback
  - Annotation Lineage
content_origin: original
content_status: validated
source_checked: 2026-07-22
source_baseline:
  - W3C PROV-O
  - NIST AI RMF
  - Datasheets for Datasets
  - Label Studio import and export documentation
lang: en
translation_key: 数据标注/09-版本、发布与生产反馈.md
translation_source_hash: b93d1e6906b3b5f3586814180deb509a3f9894c5997134ae6a13dc15f1b63ce4
translation_route: zh-CN/数据标注/09-版本、发布与生产反馈
translation_default_route: zh-CN/数据标注/09-版本、发布与生产反馈
---

# Versioning, Release, and Production Feedback

## Objective

Turn annotation from an editable spreadsheet into a traceable release artifact. Distinguish input snapshots, initial labels, adjudications, training or evaluation projections, and frozen releases. Make online failures controlled candidates rather than feedback that contaminates frozen labels or evaluation evidence.

## Five layers of artifacts: do not overwrite one with another

| Layer | Minimum content | Key boundary |
| --- | --- | --- |
| Input snapshot | sample_id, source_revision, source or access reference, sampling stratum, and content fingerprint or controlled URI | A changed input URL, document, or media cannot pretend to be the same evidence |
| Annotation event | annotation_id, input version, guideline, label, and UI versions, anonymous role, label, evidence, and time | An initial label is an observation, not final truth; append rather than overwrite it |
| Adjudication event | Initial annotation IDs, visible evidence, rule citation, final_label, adjudication rationale, and whether a guideline change was triggered | Adjudication cannot erase disagreement, model suggestions, or original versions |
| Downstream projection | A training label, expected_label, rubric, prohibited action, or weight created by a frozen mapping | cannot_judge and exclude cannot silently collapse into positive or negative classes |
| Release artifact | release_id, immutable manifest, schema, split mapping, quality and governance gates, changelog, and use or access scope | “Passed” covers only checks declared in the manifest, not perpetual online representativeness |

This is a minimum lineage suitable for engineering implementation, not a requirement that every project implement a complete ontology. W3C PROV’s entity, activity, agent, and derivation concepts help distinguish which data, who did what, and what was derived from where. The project still defines its fields, permissions, and retention policy.

## From input to a consumable release

~~~mermaid
flowchart LR
    A[Controlled input snapshot<br/>sample_id + source_revision] --> B[Independent initial annotation<br/>annotation_id]
    B --> C[Review or adjudication<br/>final_label]
    C --> D[Frozen projection mapping<br/>Training label or evaluation case]
    D --> E[Release manifest<br/>Splits, contracts, quality, and governance gates]
    E --> F[Training, evaluation, or controlled consumption]
    O[Online telemetry, appeal, or failure] --> P[Candidate triage<br/>Minimization, licensing, de-duplication, and root cause]
    P --> Q[New task card and input snapshot]
    Q --> B
    F -. Do not modify in place .-> E
~~~

*Text alternative: every production feedback item first receives triage and a new task or input version, then follows independent annotation, adjudication, and release. An already released artifact is not rewritten in place by online data.*

## Hard release gates and investigation gates

| Check | Examples | Default action on failure |
| --- | --- | --- |
| Contract and integrity | Schema, duplicate IDs, input snapshots, label, guideline, and UI versions, required evidence | Reject release; repair records or export again |
| Splits and contamination | Entity, session, or near-duplicate groups; time windows; frozen-evaluation isolation; training-prompt leakage | Block consumption; regroup or resplit |
| Label quality | Overlap coverage, conflicts, gold or expert audit, stratified denominators, adjudication gaps | Review, add labels, repair guideline, or relabel |
| Source and people boundaries | access_scope, license or authorization status, retention, withdrawal, and content risk | Isolate or block if unknown or a hard failure; never guess status as passed |
| Reproducibility and use | release_id manifest, code or tool versions, mapping, owner, and allowed uses | Do not release as consumable when reproduction or accountability is unclear |

Every “quality gate passed” claim must include its check name, version, time, denominator, exception, and owner. A hash can prove bytes did not change; it does not prove that source is compliant, labels are correct, statistics are representative, or approval remains valid.

## Version rules: did the measurement object change, or was a record repaired?

- **Input update:** source text, retrieval corpus, media, or visible tool result changed. Create a new source_revision and relabel when needed; an old judgment must not impersonate a new input.
- **Major guideline, label-space, or UI change:** may change the measurement object. Use bridge samples to compare old and new rules and determine relabeling scope; do not merely increase the version number and merge trend charts.
- **Adjudication or data defect:** append an adjudication or correction event, and mark whether an old release is superseded or deprecated. Preserve the minimum audit chain and impact scope.
- **Release-mapping change:** create a new release when training or evaluation projection, split, or weight changes even if final_label does not.
- **Source withdrawal or expiry:** issue a tombstone, stop new consumption, query associated releases and downstream uses, then isolate, replace, rebuild, retrain, or notify under an approved plan. Do not claim that “the model deleted this knowledge” without verifiable evidence.

## A controlled intake for production feedback

Online logs, user appeals, human overrides, red-team findings, and monitored drift indicate **what merits investigation**; they do not automatically state **what the correct label is**. At minimum:

1. Confirm minimization, access, source or licensing, and content risk under [[data-annotation/08-data-governance-privacy-licensing-and-worker-safety|the governance boundary]]. Do not copy complete production content into an open queue.
2. Deduplicate and associate root cause by user, session, document, tool or model version, and time. Record whether the item is an incident, appeal, random monitoring, or active-selection candidate.
3. Decide whether it leaks frozen evaluation answers or treats model output as a label. If necessary, place it in an isolation pool or create a new evaluation or training version.
4. Use a new task card, guideline, and independent annotation to make a candidate label. Only after review and adjudication can it enter the next release_id.
5. Report comparison boundaries between old and new releases, known uncovered strata, and rollback or withdrawal paths rather than declaring model improvement from one online success or failure.

For the connection to Agent and RAG evaluation, see [[evaluation-framework/methods-and-quality/08-offline-to-online-evidence-handoff-and-regression-loop|Offline-to-Online Evidence Handoff and Regression Loop]]. RAG corpus updates, ACLs, and tombstone propagation must also follow the ingestion boundary in [[rag/07-end-to-end-evaluation-and-monitoring|RAG End-to-End Evaluation and Monitoring]].

## Project implementation and limitations

The [[data-annotation/07-project-agent-answer-quality-annotation|course project]] deliberately validates only the smallest teaching contract: two fixed annotators, the same input snapshot, and one consistent contract version. It does not implement personnel identity mapping, gold answers, an adjudication ledger, access control, splits, statistical intervals, licenses, or production writes. When connecting a real system, keep these artifacts in controlled storage and avoid bundling sensitive body text or credentials into a public dataset.

## Exercise

For a RAG-relevance annotation release package, design a manifest with release_id, purpose, input-snapshot scope, guideline_version → rubric_version mapping, group-level split, quality gates, access_scope, withdrawal-impact query, and one path that converts an online failure to a candidate. Then explain which change forces a new release and which is only an appended adjudication.

## Mastery check

- [ ] I can distinguish input snapshots, initial labels, adjudications, downstream projections, and releases without overwriting history in place.
- [ ] I place training or evaluation isolation, group-level splits, and source or access gates in an auditable manifest.
- [ ] I know why a major guideline change, input change, mapping change, and withdrawal can each require a new release or impact assessment.
- [ ] I do not automatically write online failures, user behavior, model self-evaluation, or appeals as training or evaluation ground truth.

Next: [[data-annotation/07-project-agent-answer-quality-annotation|Project: Agent Answer-Quality Annotation]].

## References

Sources checked on 2026-07-22.

- [W3C PROV-O](https://www.w3.org/TR/prov-o/)
- [NIST AI RMF Core: Documentation, Data Selection, Evaluation, and Production Monitoring](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- Gebru et al. (2021). [Datasheets for Datasets](https://arxiv.org/abs/1803.09010)
- [Label Studio: Import tasks](https://labelstud.io/guide/tasks) and [export annotations](https://labelstud.io/guide/export.html)
