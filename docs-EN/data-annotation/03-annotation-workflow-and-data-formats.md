---
title: "Annotation Workflow and Data Formats"
tags:
  - ai-agent-engineer
  - data-annotation
aliases:
  - Annotation Workflow
source_checked: 2026-07-22
source_baseline:
  - Label Studio official import, setup and export documentation
  - Datasheets for Datasets
  - Data Statements for NLP
lang: en
translation_key: 数据标注/03-标注流程与数据格式.md
translation_source_hash: 08b37b55a150346782b5d342ba3991a47672b064b45de16db8926423d1e71035
translation_route: zh-CN/数据标注/03-标注流程与数据格式
translation_default_route: zh-CN/数据标注/03-标注流程与数据格式
---

# Annotation Workflow and Data Formats

## Objective

Organize sample selection, tool configuration, independent annotation, review, adjudication, and release into a traceable pipeline. Preserve data, guideline, and tool versions with every label.

## From sample pool to release set

1. Clean, deduplicate, and de-identify data while retaining a stable sample_id.
2. Sample by strata that cover category, source, time, length, language, and risk scenarios.
3. Run a small pilot and revise the guideline and tool configuration.
4. Train annotators and use qualification samples without exposing formal quality-control answers.
5. Run formal independent annotation, with overlap for important samples.
6. Perform automatic format checks, blinded review, and conflict adjudication.
7. Freeze the version and publish a data card and quality report.

## Minimal JSONL record

~~~json
{"sample_id":"s-001","data_version":"v1","guideline_version":"1.2","annotator":"ann-a","label":"helpful","evidence":"The answer provides actionable steps.","created_at":"2026-07-14T01:00:00Z"}
~~~

Do not use a person’s name or email as a public annotator ID. Store raw samples, annotations, adjudications, and model pre-labels in separate fields so that history is not overwritten.

## Input snapshots, task configuration, and exports are different evidence

A task ID in an annotation tool is not data lineage. Before annotation starts, freeze a controlled task manifest containing sample_id, a data snapshot or content fingerprint or controlled URI, source_id, access_scope, sampling batch, and data_version. Record label_config_version or a configuration hash separately. Then, even if a source URL changes, expires, or is withdrawn, you can explain what the label was based on at the time without copying sensitive body text into a public export.

Export formats from tools such as Label Studio do not always carry complete task data; when a task uses a URL reference, the source content might not be stored in the tool at all. Before release, round-trip-check a small sample across exported annotations, task manifest, configuration snapshot, and adjudication records, and state which artifacts are access-controlled. An exported JSON or CSV file alone does not establish that the work can be replayed or used for training.

The final_label in an annotation ledger is a fact with adjudication provenance. When it enters an evaluation set, it must pass through a versioned projection that creates the expected_label, expected_tool, prohibited actions, or rubric dimensions used by the evaluation. Preserve the guideline_version → rubric_version mapping. Do not collapse annotation cannot_judge, exclude, or an unadjudicated initial label directly into an evaluation positive or negative class. See [[evaluation-framework/project-and-self-check/08-offline-layered-evaluation-pipeline|Offline Layered Evaluation Pipeline]] for a concrete evaluation-case contract.

## Data versions and splits

- Near-duplicate samples of the same entity or document must stay in the same training or test partition.
- Test and evaluation samples must not enter an active-learning training pool.
- A material guideline change must receive a new version, and old-label compatibility must be assessed.
- A release set records sample source, license, privacy treatment, label distribution, and known limitations.

## Tool configuration is not a label definition

Tools such as Label Studio present tasks, controls, import and export, and collaboration. The fact that a UI can create a button does not mean a label is well defined. Write the schema and guideline first, configure the UI second, and validate the import–annotation–export round trip with a small sample.

At minimum, the round-trip check compares task ID, raw-data reference, label or span, annotator, time, model prediction, and human annotation to ensure they remain separate. Export formats can contain annotations without full task data; do not infer completeness from a file extension.

## Exercise

Extend the JSONL above with source_id, split, model_suggestion, reviewer_id, and final_label. Identify which fields an annotator must not see at first judgment.

## Mastery check

- [ ] Every label can be traced to sample, data, guideline, tool, and annotator versions and to its controlled input snapshot.
- [ ] Model suggestions, initial human annotations, reviews, and adjudications use separate fields rather than overwriting history.
- [ ] The same entity or near-duplicate samples do not cross training and frozen-evaluation partitions.
- [ ] I have tested an import–annotation–export round trip on a small sample rather than assuming the format is lossless.

Next: [[data-annotation/04-quality-control-review-and-adjudication|Quality Control, Review, and Adjudication]].

## References

Sources checked on 2026-07-22. Official import and export documentation warns that task data referenced by URL may not be stored or carried in an export. A project should validate its controlled input snapshot and annotation export separately.

- [Label Studio: Set up your labeling project](https://labelstud.io/guide/setup_project.html)
- [Label Studio: Import data](https://labelstud.io/guide/tasks)
- [Label Studio: Export annotations and data](https://labelstud.io/guide/export.html)
- [Datasheets for Datasets](https://arxiv.org/abs/1803.09010)
- [Data Statements for Natural Language Processing](https://aclanthology.org/Q18-1041/)
