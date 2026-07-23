---
title: "Synthetic Data"
aliases:
  - Synthetic Data
  - AI Data Generation
tags:
  - ai-agent-engineer
  - synthetic-data
  - learning-path
source_checked: 2026-07-22
ai_learning_stage: 7. Production, Evaluation, and Governance
ai_learning_order: 43
ai_learning_schema: 2
ai_learning_id: synthetic-data
ai_learning_domain: evaluation-reliability
ai_learning_catalog_order: 4300
ai_learning_hard_prerequisites:
  - data-cleaning
  - data-annotation
  - evaluation
ai_learning_track_agent_platform_order: 1050
ai_learning_track_agent_platform_kind: recommended
content_origin: original
content_status: dynamic
lang: en
translation_key: "数据合成/00-目录.md"
translation_source_hash: f454be789dd3f3c0d013b621c4972cce06b12fb33b09cab05a68251780fe3760
translation_route: zh-CN/数据合成/00-目录
translation_default_route: zh-CN/数据合成/00-目录
---

# Synthetic Data

## About this knowledge base

Synthetic data is new data constructed through rules, simulators, statistical models, or generative models. It can fill rare conditions, create controlled tests, reduce manual drafting effort, and support training or privacy research. It is not automatically realistic, unbiased, private, free of copyright risk, or fit for the target task.

This knowledge base follows synthetic evaluation data for AI Agent engineering: define purpose and data contract first; use templates and models to cover conditions; then filter, deduplicate, split by family, calibrate against real data, review risk, and publish a versioned dataset. Its core principle is: **generation only produces candidate samples; independent validation supplies quality evidence.**

The course covers four method classes: template/combinatorial generation, state machines/simulators, statistical synthesis, and model generation. Their guarantees differ. Templates are easy to verify but offer limited linguistic variation; simulators produce trajectories and terminal states but depend on an environment model; statistical synthesis can approximate selected statistics but does not automatically protect privacy; generative models expand open-ended expression but introduce label, memorization, bias, and source risks. Choose the purpose before choosing a popular tool.

> [!warning] Important boundary
>
> “Synthetic” is not a privacy guarantee. A generative model may reproduce training content, and statistical synthesis based on sensitive originals may leak too. Only a clearly specified, correctly implemented, and audited mechanism—such as differential privacy—provides its corresponding guarantee. Qualified people in the organization must assess law, license, and personal-information handling against the data source and jurisdiction.

## Position in the overall route

This course belongs to “Production, Evaluation, and Governance.” Learn [[data-cleaning/00-index|Data Cleaning]], [[data-annotation/00-index|Data Annotation]], and [[evaluation-framework/00-index|Evaluation Framework]] first. Then use it to add stress layers for [[benchmark-design/00-index|Benchmark Design]] or prepare candidate data for model/Agent training.

## Learning objectives

- Write data contracts and stop conditions for evaluation, training, simulation, or privacy-release purposes.
- Generate reproducible, traceable samples from templates, factor matrices, and fixed seeds.
- Design model-generation pipelines that control condition quotas rather than blindly maximizing count.
- Perform Schema/rule/quality/exact-or-near-duplicate filtering and family-level splits.
- Evaluate fidelity, coverage, diversity, downstream utility, and privacy risk independently.
- Distinguish sample validity, dataset coverage, held-out-real-data utility, and formal privacy guarantees rather than substituting one aggregate score for another.
- Recognize memorization leakage, bias amplification, copyright/license risk, and synthetic-data contamination.
- Publish maintainable datasets through Data Cards, content fingerprints, versions, and changelogs.
- Record sample-level provenance, source/authorization evidence reference, access scope, and withdrawal impact separately; none of those fields alone is a legal or privacy conclusion.

## Prerequisites

- Read and write JSON and understand train/dev/test and group splits.
- Run Python 3 standard-library scripts in PowerShell 7.
- Understand basic proportions, distributions, and sampling; no deep-learning training is required.
- Know that model-generated fluent text still needs validation and cannot be treated as a correct label.

## Recommended sequence

1. [[data-synthesis/foundations-and-design/01-purpose-and-data-contract|Purpose and Data Contract]] — define use, population, Schema, and acceptance first.
2. [[data-synthesis/foundations-and-design/02-template-and-programmatic-generation|Template and Programmatic Generation]] — build a deterministic, inexpensive, coverable baseline.
3. [[data-synthesis/foundations-and-design/03-model-generation-and-condition-coverage|Model Generation and Condition Coverage]] — expand linguistic and task variation under strict provenance.
4. [[data-synthesis/methods-and-quality/04-filtering-deduplication-and-group-splits|Filtering, Deduplication, and Group-Level Splits]] — turn the candidate pool into usable data.
5. [[data-synthesis/methods-and-quality/05-quality-utility-and-real-data-calibration|Quality, Utility, and Real-Data Calibration]] — show that data helps the target decision.
6. [[data-synthesis/methods-and-quality/06-privacy-memorization-bias-and-copyright|Privacy, Memorization, Bias, and Copyright]] — identify risks generation cannot remove.
7. [[data-synthesis/methods-and-quality/07-versioning-evaluation-and-release|Versioning, Evaluation, and Release]] — record lineage, limits, and updates.
8. [[data-synthesis/project-and-self-check/08-project-offline-synthetic-evaluation-data-pipeline|Project: Offline Synthetic Evaluation Data Pipeline]] — run condition matrix, filtering, deduplication, split, and fingerprint.

## Hands-on entry point

- Main project: [[data-synthesis/project-and-self-check/08-project-offline-synthetic-evaluation-data-pipeline|Offline Synthetic Evaluation Data Pipeline]]. It uses a strict JSON specification, condition matrix, source declaration, rejection log, family split, and quality gate. It supplies executable PASS, BLOCK, and contract-error cases plus 43 tests.
- Design task: begin with one production failure, write three real variants and six synthetic stress variants, and state their different weight in reporting.
- Audit task: write provenance, model/template version, filtering record, and known risks for any synthetic dataset.

## Mastery criteria

- [ ] I can explain why “more synthetic samples” is not “more useful information.”
- [ ] I can define coverage targets with a task-factor matrix and retain family IDs.
- [ ] I can distinguish Schema validity, semantic correctness, realism, diversity, and downstream utility.
- [ ] I can do normalized exact deduplication and explain when near-duplicate or semantic review is needed.
- [ ] I can test training or evaluation utility against an independent real holdout.
- [ ] I can state the guarantee difference between ordinary synthetic data and differentially private synthesis.
- [ ] I can publish a Data Card with version, hash, source, license, risk, and limitation.
- [ ] I can run the offline project and its 43 three-mode tests on Windows 11 / PowerShell 7, and explain why PASS still does not prove production utility or anonymity.

## Relationships to other knowledge bases

- [[data-cleaning/00-index|Data Cleaning]] supplies Schema, dirty-value, and anomaly handling.
- [[data-annotation/00-index|Data Annotation]] owns rubrics, human calibration, and disagreement resolution.
- [[evaluation-framework/00-index|Evaluation Framework]] decides how synthetic cases are scored; synthetic data cannot be its own only validator.
- [[benchmark-design/00-index|Benchmark Design]] owns frozen splits, contamination control, and comparison protocol.
- [[privacy-computing/00-index|Privacy Computing]] studies formal techniques such as differential privacy in more depth.
- [[ai-governance/00-index|AI Governance]] owns authorization, data responsibility, release approval, and risk acceptance.

## Primary references

The following official material, standards, or original papers were retrieved/checked on 2026-07-22:

- [SELF-INSTRUCT original paper](https://aclanthology.org/2023.acl-long.754/)
- [Deduplicating Training Data Makes Language Models Better original paper](https://aclanthology.org/2022.acl-long.577/)
- [NIST SDNist Synthetic Data Report Tool](https://www.nist.gov/services-resources/software/sdnist-synthetic-data-report-tool) — page lists software v1.4 and last update 2022-02-01; used only as a utility/privacy multidimensional-reporting example.
- [NIST SP 800-226: Evaluating Differential Privacy Guarantees](https://doi.org/10.6028/NIST.SP.800-226) — final 2025-03.
- [NIST AI 600-1: Generative AI Profile](https://doi.org/10.6028/NIST.AI.600-1)
- [Data Cards original paper and official page](https://research.google/pubs/data-cards-purposeful-and-transparent-dataset-documentation-for-responsible-ai/)
- [Datasheets for Datasets original paper](https://arxiv.org/abs/1803.09010)
