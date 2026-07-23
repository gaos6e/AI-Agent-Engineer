---
title: "Privacy-Enhancing Technologies Learning Path"
aliases:
  - Privacy-enhancing technologies learning route
  - Learning privacy-enhancing technologies from scratch
tags:
  - privacy
  - privacy-enhancing-technologies
  - ai-engineering
source_checked: 2026-07-21
ai_learning_stage: 7. Production, evaluation, and governance
ai_learning_order: 45
ai_learning_schema: 2
ai_learning_id: privacy-enhancing-technologies
ai_learning_domain: safety-governance
ai_learning_catalog_order: 4500
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 1250
ai_learning_track_agent_app_kind: recommended
ai_learning_track_rag_order: 1500
ai_learning_track_rag_kind: recommended
ai_learning_track_agent_platform_order: 1450
ai_learning_track_agent_platform_kind: recommended
ai_learning_track_multimodal_realtime_order: 1000
ai_learning_track_multimodal_realtime_kind: recommended
content_origin: original
content_status: dynamic
lang: en
translation_key: 隐私计算/00-目录.md
translation_source_hash: 69e0fd5fce50ca4473ef5e977880dda9b51726b66c2d6ddddf5d3f66f50db31d
translation_route: zh-CN/隐私计算/00-目录
translation_default_route: zh-CN/隐私计算/00-目录
---

# Privacy-Enhancing Technologies Learning Path

## About this knowledge base

“Privacy computing” is not one algorithm. It is a family of methods that reduce privacy risk in collection, sharing, training, inference, and publication. The first controls are usually to not collect, collect less, limit purpose, shorten retention, and control output. Differential privacy, federated learning, secure aggregation, MPC, homomorphic encryption, and TEEs provide specific guarantees only under explicit threat models, parameters, and implementations.

The course path is: minimization and de-identification → differential privacy → distributed training and aggregation → cryptography and trusted hardware → selection and composition → evaluation and response → offline solution review. The goal is not to memorize acronyms, but to state clearly: “who is protected, which information, against which adversary, under which assumptions, and what can still leak?”

## Where this course fits in the overall route

This course belongs to the Safety and Governance knowledge domain. It is a recommended specialization on all four role tracks after the full [[ai-safety/00-index|AI Safety]] course. Relevant knowledge from probability and statistics, machine learning, and data cleaning helps explain methods and evaluation, but none of those full courses is a hard prerequisite. Practice privacy minimization, purpose limitation, and retention during the early safety milestone; this course then goes deeper into differential privacy, federated learning, MPC, homomorphic encryption, and TEEs, together with [[evaluation-framework/00-index|Evaluation Framework]], [[runtime-monitoring/00-index|Runtime Monitoring]], and [[ai-governance/00-index|AI Governance]].

## Learning objectives

- Demonstrate field-by-field necessity from purpose and data subjects, covering models, embeddings, logs, caches, and backups.
- Explain the differences among de-identification, pseudonymization, anonymity, quasi-identifiers, and linkage attacks.
- Use minimal formulas to explain DP adjacency, contribution, sensitivity, ε/δ, mechanisms, and composition budgets.
- Distinguish FL, contribution clipping, secure aggregation, robust aggregation, and privacy of the final model.
- Compare MPC, HE/FHE, and TEEs by parties, collusion, keys, integrity, output, and performance.
- Derive candidate PETs from a privacy goal, and record guarantee, unprotected scope, evidence, rollback, and responsibility.
- Design end-to-end evaluation, budget/access/deletion monitoring, and leak response.
- Run a strict offline solution-review project that does not process personal data.

## Prerequisites

- Probability and random variables, machine-learning training and evaluation, and basic identity, cryptography, and networking concepts.
- You need not prove cryptographic protocols, but must respect their adversaries, collusion, keys, parameters, and implementation assumptions.
- The legal meaning of personal information, lawful basis, cross-border processing, rights, and notification duties must be determined by appropriate professional responsibilities in the applicable jurisdiction.

## Recommended order

### 01 Foundations and risks

1. [[privacy-computing/01-foundations-and-risks/01-data-minimization-and-de-identification|Data minimization and de-identification]] — first reduce data and lifecycle attack surface.
2. [[privacy-computing/01-foundations-and-risks/02-differential-privacy-intuition-and-budget|Differential privacy intuition and budget]] — quantify one subject's influence on randomized releases.
3. [[privacy-computing/01-foundations-and-risks/03-federated-learning-and-secure-aggregation|Federated learning and secure aggregation]] — distinguish local training, update visibility, and final-model leakage.

### 02 Controls and governance

4. [[privacy-computing/02-controls-and-governance/04-mpc-homomorphic-encryption-and-tee|MPC, homomorphic encryption, and TEEs]] — compare protocol, keys, hardware, and output boundaries.
5. [[privacy-computing/02-controls-and-governance/05-pet-selection-and-composition-boundaries|PET selection and composition boundaries]] — derive candidates from goals and redraw guarantees after composition.
6. [[privacy-computing/02-controls-and-governance/06-privacy-evaluation-and-leak-response|Privacy evaluation and leak response]] — validate implementation, monitor operation, and handle incidents safely.

### 03 Project and self-assessment

7. [[privacy-computing/03-project-and-self-assessment/07-project-offline-privacy-solution-review|Project: Offline Privacy Solution Review]] — review a synthetic-metadata scenario with a strict contract, twelve rules, and seventy-six tests.

## Suggested study rhythm

On the first pass, complete the threat model and exercise for each lesson. On the second, choose a real system but record only field names, categories, and data-flow metadata—not personal data—and work through the full path. On the third, turn guarantee claims into tests, runtime events, and responsibility gates. Have experts review current implementations and parameters before using complex cryptographic schemes in production.

## Project entry point

Start with [[privacy-computing/03-project-and-self-assessment/07-project-offline-privacy-solution-review|Offline Privacy Solution Review]]. The project supplies vulnerable, hardened, and contract-error paths. It strictly rejects duplicate keys, unknown fields, invalid references, and non-finite parameters; it explicitly identifies teaching thresholds, basic budget composition, and the evidence boundary of `PASS`.

## Mastery checklist

- [ ] Can give a clear purpose and alternative for every field, output, recipient, and retention period.
- [ ] Can explain why removing names, encryption, pseudonymization, synthetic data, and “data does not leave the boundary” do not each equal anonymity.
- [ ] Can define DP subject, adjacency, and contribution, and maintain a cross-release budget without inventing one universal compliant ε.
- [ ] Can state server, client, collusion, dropout, multi-round, and final-model boundaries for FL and secure aggregation.
- [ ] Can state input/output, keys/proofs, integrity, performance, and side-channel assumptions for MPC, FHE, and TEEs.
- [ ] Can compare the simplest baseline with a complex PET, recording versions, parameters, tests, residual risk, and exit plan.
- [ ] Can monitor budget, access, output, proofs, and deletion without copying personal data.
- [ ] Can explain why the offline project is not a DP or cryptographic implementation, production assessment, compliance conclusion, or legal conclusion.

## Relationship to other knowledge bases

- [[ai-safety/00-index|AI Safety]] protects identities, permissions, supply chain, and infrastructure; PETs cannot fix a stolen administrator credential.
- Output from [[data-synthesis/00-index|Data Synthesis]] still needs membership, duplication, and linkage assessment; it is not automatically free of personal information.
- [[ai-governance/00-index|AI Governance]] determines purpose approval, responsibility, vendors, risk acceptance, and retirement. This course supplies technical evidence and boundaries.
- [[evaluation-framework/00-index|Evaluation Framework]] makes privacy, utility, fairness, and runtime cost comparable version gates.

## Primary references and current status

- [NIST Privacy Framework](https://www.nist.gov/privacy-framework) and the [Privacy Framework 1.1 project page](https://www.nist.gov/privacy-framework/new-projects/privacy-framework-version-11) (accessed 2026-07-21). At that date, Version 1.0 remained the published version; the 1.1 page was still marked Initial Public Draft/coming soon and must not be called final.
- [NIST SP 800-226: Guidelines for Evaluating Differential Privacy Guarantees](https://csrc.nist.gov/pubs/sp/800/226/final) (final, March 2025).
- [NIST Privacy-Enhancing Cryptography](https://csrc.nist.gov/Projects/pec) (page updated 2026-07-01; accessed 2026-07-21).
- [NIST IR 8053: De-Identification of Personal Information](https://doi.org/10.6028/NIST.IR.8053).
- [NIST SP 800-188: De-Identifying Government Datasets](https://csrc.nist.gov/pubs/sp/800/188/final) (final, September 2023; its direct audience is US government agencies, so this course uses only its approach to release models, measurable objectives, and disclosure review).
- [McMahan et al. 2017 Federated Learning](https://proceedings.mlr.press/v54/mcmahan17a.html) and [Bonawitz et al. Practical Secure Aggregation](https://eprint.iacr.org/2017/281).

> [!warning] Scope boundary
> This course is not legal, compliance, cryptographic-audit, or production privacy-assessment advice. Verify laws, definitions of personal information, lawful bases, cross-border processing, data-subject rights, and notification duties against the actual region, purpose, role, and facts. Recheck dynamic standards and product implementations at deployment time.
