---
title: "Data Annotation Learning Path"
tags:
  - ai-agent-engineer
  - data-annotation
  - learning-path
aliases:
  - Data Annotation index
  - Data Annotation learning path
content_origin: original
content_status: validated
source_checked: 2026-07-22
source_baseline:
  - Label Studio official documentation
  - Google People + AI Guidebook
  - Cohen 1960 kappa paper
  - Artstein and Poesio 2008 agreement survey
  - Lewis and Gale 1994 active-learning paper
  - Ratner et al. 2017 weak-supervision paper
  - Datasheets for Datasets and Data Statements for NLP
  - NIST AI RMF and Privacy Framework
ai_learning_stage: 2. Mathematics and data foundations
ai_learning_order: 17
ai_learning_schema: 2
ai_learning_id: data-annotation
ai_learning_domain: retrieval-and-data
ai_learning_catalog_order: 1700
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 850
ai_learning_track_agent_app_kind: recommended
ai_learning_track_rag_order: 1050
ai_learning_track_rag_kind: recommended
ai_learning_track_agent_platform_order: 875
ai_learning_track_agent_platform_kind: recommended
ai_learning_track_multimodal_realtime_order: 650
ai_learning_track_multimodal_realtime_kind: recommended
lang: en
translation_key: 数据标注/00-目录.md
translation_source_hash: ded8a8ccafa1cc4d86dffbe688482d1638448f95061024ac00461b6857447cb0
translation_route: zh-CN/数据标注/00-目录
translation_default_route: zh-CN/数据标注/00-目录
---

# Data Annotation

## About this knowledge base

Data annotation turns ambiguous business judgment into a repeatable, reviewable measurement protocol. It supports supervised training, RAG relevance assessment, Agent-trajectory review, safety red-teaming, and offline evaluation. The real deliverable is a “task definition + guideline + controlled input + annotation events + quality evidence + release manifest,” not a column of labels that merely appears complete.

> [!info] Content and evidence boundary
> This course is an original engineering synthesis based on the sources listed at the end. Tool interfaces, platform features, and regulations change; source links are for verifying concepts and tool behavior, not substitutes for a particular organization’s privacy, labor, contract, or legal review.

## Where this course fits in the overall route

This course belongs to the Mathematics and Data Foundations stage. Study it after basic data cleaning; it supplies reliable supervision signals for Machine Learning, Reranking, RAG, Evaluation Systems, Data Synthesis, and production feedback. If the task touches high-stakes decisions, personal data, or harmful content, complete data-governance and safety boundaries before beginning a pilot annotation.

## Master five objects first

| Object | Question it answers | What it must not stand in for |
| --- | --- | --- |
| `sample_id` | Which logical sample is being judged? | The exact input content or version |
| `source_revision` | Which controlled input snapshot did the annotator actually see? | Source authorization, privacy safety, or factual correctness |
| `annotation_id` | Who submitted one initial annotation under which protocol and when? | Ground truth or adjudication |
| `final_label` | What label resulted from the established adjudication process? | Any projection used for training/evaluation |
| `release_id` | Which frozen set of samples, contracts, quality gates, and splits will downstream users consume? | Permanent representativeness of future online distribution |

Keep `guideline_version`, `label_set_version`, and `task_config_version` with every annotation event as well. They respectively identify the rules, available labels, and UI/schema; a label with the same name need not measure the same object across versions.

## Learning objectives

- Define annotation units, the target population, label ontology, exclusion conditions, and visible evidence.
- Write guidelines, paired examples, and escalation rules that unfamiliar annotators can execute.
- Control quality with pilots, overlapping annotation, blinded review, adjudication, and bridge samples.
- Interpret percent agreement and Cohen’s kappa correctly without conflating agreement, correctness, and representativeness.
- Treat active learning, weak supervision, and synthetic samples as candidate sources rather than unverified “true labels.”
- Manage the boundaries of sensitive data, licenses, worker exposure, versioning, withdrawal, and production feedback.

## Prerequisites

Understand JSONL/CSV and sampling concepts, and be able to run a Python 3 standard-library script. It is recommended to first complete the sampling and uncertainty sections of [[data-cleaning/00-index|Data Cleaning]], [[json/00-index|JSON]], and [[probability-and-statistics/00-index|Probability and Statistics]]. Before starting, confirm least-privilege access, de-identification approach, source licensing, retention period, and escalation paths for harmful content.

## Recommended order

1. [[data-annotation/01-task-definition-and-annotation-units|Task definition and annotation units]] — turn “is it good?” into an observable, adjudicable measurement task.
2. [[data-annotation/08-data-governance-privacy-licensing-and-worker-safety|Data governance, privacy, licensing, and worker safety]] — complete the minimum governance gate before handling real data or assigning it to real workers; return to other governance details after workflow practice.
3. [[data-annotation/02-annotation-guidelines-and-edge-cases|Annotation guidelines and edge cases]] — make ambiguity explicit with rules, paired examples, abstention, and escalation.
4. [[data-annotation/03-annotation-workflow-and-data-formats|Annotation workflow and data formats]] — bring samples, input snapshots, people, tools, and versions into one pipeline.
5. [[data-annotation/04-quality-control-review-and-adjudication|Quality control, review, and adjudication]] — use independent judgments, bridge samples, and additive adjudication to handle disputes.
6. [[data-annotation/05-inter-annotator-agreement-metrics|Inter-annotator agreement metrics]] — calculate and diagnose agreement, reporting denominators, distributions, and uncertainty.
7. [[data-annotation/06-active-learning-and-human-in-the-loop|Active learning, weak supervision, and human-in-the-loop work]] — improve efficiency without contaminating evaluation, amplifying bias, or anchoring human judgment.
8. [[data-annotation/09-versioning-release-and-production-feedback|Versioning, release, and production feedback]] — turn annotation output into a traceable, withdrawable release that does not feed back into frozen sets.
9. [[data-annotation/07-project-agent-answer-quality-annotation|Project: Agent answer-quality annotation]] — run a strict two-annotator audit, explain conflicts, and write the next adjudication/release plan.

## Hands-on project

[[data-annotation/examples/audit_annotations.py|audit_annotations.py]] runs strict JSON, input-snapshot, contract-version, and two-annotator-pair checks on [[data-annotation/examples/sample_annotations.jsonl|sample_annotations.jsonl]], calculating percent agreement, Cohen’s kappa, confusion counts, and conflicting samples. [[data-annotation/examples/test_audit_annotations.py|test_audit_annotations.py]] covers 12 normal and failure behaviors. The project needs no third-party package, real data, or API key.

## Mastery checklist

- [ ] Can have two people who did not design the task independently perform a pilot, then turn ambiguity into versioned rules.
- [ ] Can distinguish “labels agree,” “labels are correct,” “the target population is represented,” and “it is safe to release.”
- [ ] Can choose quality evidence suitable for multiclass, sequence-labeling, or generative-rating measurement objects.
- [ ] Can trace every label to its input snapshot, guideline, label space, UI, annotator role, and time.
- [ ] Can explain how model pre-labeling, weak supervision, and synthetic candidates can anchor judgment or contaminate statistics.
- [ ] Can run normal/`-O` modes and all 12 tests, and explain why kappa is undefined when a constant label has perfect agreement.

## Relationship to other knowledge bases

- [[data-cleaning/00-index|Data Cleaning]] handles corrupt, duplicate, sensitive fields and controlled release manifests before annotation.
- [[machine-learning/00-index|Machine Learning]] consumes labels for training/evaluation but cannot exceed the bounds of their definition, split, and version.
- [[evaluation-framework/00-index|Evaluation Framework]] and [[benchmark-design/00-index|Benchmark Design]] project adjudicated labels into frozen cases and rubrics; `cannot_judge` and `exclude` must not be silently collapsed into positive/negative classes.
- [[rag/00-index|RAG]] and [[reranking/00-index|Reranking]] often need graded query-document relevance and evidence spans rather than simple binary labels.
- [[data-synthesis/00-index|Data Synthesis]] can supplement candidates and edge cases; synthetic origin, generator version, and final human label must be stored in layers and cannot substitute for validation on a real distribution.
- [[ai-governance/00-index|AI Governance]], [[privacy-computing/00-index|Privacy Computing]], and [[ai-safety/00-index|AI Safety]] constrain data sources, access, retention, affected people, and high-risk escalation.

## Primary references

Sources were checked on 2026-07-22. The following are representative sources for concepts and tool behavior; a concrete project must lock its tool version, task protocol, organization policies, and applicable requirements.

- [Label Studio: Set up and configure projects](https://labelstud.io/guide/setup_project), [import tasks](https://labelstud.io/guide/tasks), and [export annotations](https://labelstud.io/guide/export.html)
- [Google PAIR: People + AI Guidebook](https://pair.withgoogle.com/guidebook/)
- Cohen, J. (1960). [A coefficient of agreement for nominal scales](https://doi.org/10.1177/001316446002000104)
- Artstein, R., & Poesio, M. (2008). [Inter-Coder Agreement for Computational Linguistics](https://aclanthology.org/J08-4004/)
- Lewis, D. D., & Gale, W. A. (1994). [A Sequential Algorithm for Training Text Classifiers](https://aclanthology.org/P94-1019/)
- Ratner et al. (2017). [Snorkel: Rapid Training Data Creation with Weak Supervision](https://arxiv.org/abs/1711.10160)
- Gebru et al. (2021). [Datasheets for Datasets](https://arxiv.org/abs/1803.09010); Bender & Friedman (2018). [Data Statements for NLP](https://aclanthology.org/Q18-1041/)
- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/), [NIST Privacy Framework](https://www.nist.gov/privacy-framework), and [W3C PROV-O](https://www.w3.org/TR/prov-o/)
- [ILO: Digital work and occupational safety and health](https://www.ilo.org/publications/revolutionizing-health-and-safety-role-ai-and-digitalization-work)
