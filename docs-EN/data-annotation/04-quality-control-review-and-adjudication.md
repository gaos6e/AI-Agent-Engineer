---
title: "Quality Control, Review, and Adjudication"
tags:
  - ai-agent-engineer
  - data-annotation
aliases:
  - Annotation Quality Control
source_checked: 2026-07-22
source_baseline:
  - Label Studio official collaboration documentation
  - Google People + AI Guidebook
lang: en
translation_key: 数据标注/04-质检复审与裁决.md
translation_source_hash: 2e26d29f25505a9ee4241fafa66cea1f88b644db6d03a391922c623f89837dc9
translation_route: zh-CN/数据标注/04-质检复审与裁决
translation_default_route: zh-CN/数据标注/04-质检复审与裁决
---

# Quality Control, Review, and Adjudication

## Objective

Combine format checks, independent agreement, gold-answer accuracy, and stratified audits to design review and adjudication that can find systematic errors, rather than sampling one overall percentage at the end.

## Quality comes from process design

An end-of-project check of 1% cannot discover systematic guideline defects. Quality control should run throughout: pilots expose ambiguity, format checks stop invalid submissions, overlapping annotation measures agreement, blinded review checks correctness, and adjudication captures new rules.

## Four complementary kinds of evidence

- **Format validity:** required fields, enumerations, span boundaries, and rationale length.
- **Agreement:** whether multiple annotators give the same sample similar judgments.
- **Gold-answer accuracy:** performance on a small set of expert-confirmed gold samples.
- **Stratified audits:** samples inspected by annotator, class, source, time, difficulty, and model suggestion.

High agreement can mean that everyone shares the same misunderstanding; high scores on gold items can mean that annotators only know previously seen items. The evidence must be combined.

Gold samples can also become stale or leak. Limit repeated exposure, rotate item sets, record their version, and validate with unannounced random audits. Expert gold answers also require evidence and review.

## Overlapping annotation and blinded review

High-risk, long-tail, and random samples should receive independent annotations from multiple people. Independent means that the first judgment does not reveal others’ answers, model confidence, or adjudication outcomes. Otherwise anchoring and conformity are likely.

Review sampling must not select only short samples or high-confidence cases. It can combine random sampling, risk strata, low-agreement samples, and new-annotator samples, while clearly stating the denominator for each.

## Adjudication

An adjudicator assigns a final label using the guideline and evidence, while recording the initial labels, reason for conflict, adjudicated label, rule citation, and whether the guideline needs updating. If many conflicts cluster at the same boundary, pause bulk annotation and repair the rule first.

Adjudication is an appended event, not an in-place change of an initial annotation into a “correct answer.” Without preventing verification of evidence, hide annotator identity, model suggestions, and productivity information from the adjudicator to reduce authority and conformity bias. Whether prior labels are shown, and in which order, must also be specified in the protocol. Disagreement between two annotators has no majority vote: the final label must come from guideline evidence or an escalation rule, not an arbitrary choice of one side.

~~~mermaid
flowchart LR
    A[Freeze task, guideline, and configuration] --> B[Independent initial annotation]
    B --> C{Format and agreement checks}
    C -->|Agrees and passes audit| D[Candidate release set]
    C -->|Conflict or high risk| E[Identity-masked adjudication]
    E --> F[Append adjudication record]
    F --> G{Does the rule need to change?}
    G -->|No| D
    G -->|Yes| H[Guideline version and changelog]
    H --> I[Bridge samples / relabeling-scope decision]
    I --> D
~~~

## Bridging and relabeling after guideline changes

A major guideline change changes the measurement object; new and old labels cannot be treated as one population. Retain a set of **bridge samples** spanning common, long-tail, and disputed boundaries. Under both the old and new guidelines, record labels, evidence, and adjudication differences. Use this to determine which historical batches need relabeling and which can only be reported side by side with versions. Bridge samples help understand a version break; they must not let a team choose whichever rule looks better. If comparable evidence does not exist, stop longitudinal comparisons and state the break in the report.

A minimum adjudication record includes adjudication_id, sample_id, initial-annotation record IDs, visible evidence scope, guideline version, rule citation, adjudicated label and rationale, adjudicator role, time, whether it triggered a guideline change, and the affected relabeling scope. Personnel identities can be held separately in a controlled system; public data should retain only necessary anonymous role identifiers.

## Avoid perverse incentives

Speed, volume, and agreement rate cannot individually be performance goals. Optimizing only speed skips evidence; optimizing only agreement suppresses justified abstention. Repair the task and guideline before focusing on personnel training.

## Exercise

Design a quality-control plan for 1,000 RAG-relevance annotations. Specify the overlap rate, random audit, long-tail strata, gold samples, pause threshold, and adjudication artifacts.

## Mastery check

- [ ] I can distinguish format validity, agreement, gold accuracy, and representative audits.
- [ ] Initial judgments remain blinded to others’ answers, model confidence, and adjudication outcomes.
- [ ] An adjudication records initial labels, evidence, rule citation, final label, and whether the guideline changed.
- [ ] Sampling reports denominators for every stratum rather than hiding long-tail or high-risk failures behind a high overall score.
- [ ] I treat adjudication as an appended record and use bridge samples after a major guideline change to determine relabeling and metric-comparison boundaries.

Next: [[data-annotation/05-inter-annotator-agreement-metrics|Inter-Annotator Agreement Metrics]].

## References

Sources checked on 2026-07-22. Current Label Studio documentation still distinguishes tasks, annotations, and export formats. Tool features do not substitute for independent annotation, blinded review, or a versioned adjudication protocol.

- [Label Studio: Data labeling documentation](https://labelstud.io/guide?hsLang=en)
- [Label Studio: Export annotations and data](https://labelstud.io/guide/export.html)
