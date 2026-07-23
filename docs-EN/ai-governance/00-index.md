---
title: "AI Governance Learning Path"
aliases:
  - Learning AI governance from scratch
  - AI Governance
tags:
  - ai-governance
  - ai-risk-management
  - ai-agent
source_checked: 2026-07-22
ai_learning_stage: 7. Production, evaluation, and governance
ai_learning_order: 46
ai_learning_schema: 2
ai_learning_id: ai-governance
ai_learning_domain: safety-governance
ai_learning_catalog_order: 4600
ai_learning_hard_prerequisites: []
ai_learning_track_agent_platform_order: 1500
ai_learning_track_agent_platform_kind: core
content_origin: original
content_status: dynamic
lang: en
translation_key: AI治理/00-目录.md
translation_source_hash: 2cc4cde3a104630926ad7ab4ce00342a1515a73320787c64b9df8c1b7dfdecae
translation_route: zh-CN/AI治理/00-目录
translation_default_route: zh-CN/AI治理/00-目录
---

# AI Governance Learning Path

## About this knowledge base

AI governance turns the question “how should we use AI responsibly?” into organizational mechanisms that can be executed, traced, and reviewed. It is neither an ethics slogan nor a pre-release checklist. It is a chain of accountability that runs through demand definition, procurement or development, validation, deployment, operation, change, incidents, and retirement: every system needs an accountable owner, every risk needs a decision-maker, every control needs evidence, and every change needs to trigger review.

This course uses the NIST AI RMF functions—Govern, Map, Measure, and Manage—as a general risk-management skeleton, and uses the OECD AI Principles to calibrate the perspectives of human rights, transparency, safety, and accountability. Laws and standards are only entry points for locating and checking sources; any conclusion about applicability or compliance must consider the role, intended use, region, industry, and current authoritative text.

## Where this course fits in the overall route

This course belongs to the Safety and Governance knowledge domain. It is a core course near the production-release gate on the Agent Platform Engineering path; learners on other paths can enter it when they take responsibility for a system or its risks. First build a working understanding of Agent Core and data and model fundamentals, then connect the material to [[evaluation-framework/00-index|Evaluation Framework]], [[runtime-monitoring/00-index|Runtime Monitoring]], [[ai-safety/00-index|AI Safety]], and [[privacy-computing/00-index|Privacy Computing]]. Governance connects that technical evidence to accountable people, risk tolerance, approvals, and lifecycle decisions; it does not replace technical validation.

## Learning objectives

- Build an AI-system inventory that covers in-house, procured, open-source, embedded, and experimental systems.
- Distinguish accountable, operating, reviewing, consulted, and informed roles, and identify who may accept residual risk.
- Tier risk and conduct impact assessments from the use case, affected people, and real-world consequences rather than the model name alone.
- Govern the full value chain of data, models, tools, vendors, and versions.
- Retain the minimum sufficient evidence for transparency statements, evaluation, approval, change, monitoring, incidents, and retirement.
- Produce an offline, reviewable minimum AI-governance package and explain why it is not proof of compliance.

## From framework functions to artifacts and responsibilities

The NIST AI RMF functions are not a one-time waterfall. Govern runs through the other functions, while Map, Measure, and Manage recur as use, evidence, operation, and external conditions change. The Playbook explicitly presents voluntary guidance, not a checklist that must be completed item by item.

| Function | Core artifacts in this course | Primary responsibility interfaces |
| --- | --- | --- |
| Govern | Inventory; roles and decision rights; policies; risk tolerance; supply-chain responsibility | Governance body, ultimate accountable owner, system and risk owners |
| Map | Intended use, affected people, scenarios, regions, impact paths, and non-AI baseline | Product and domain teams, data, privacy, security, and affected-person participation |
| Measure | Scenario-based evaluation, subgroup analysis, red teaming, control evidence, and uncertainty | Independent evaluation, security/privacy review, and domain review |
| Manage | Risk prioritization, release and exception decisions, monitoring, incidents, recovery, and retirement | Authorized approvers, operations and incident owners, and business owners |

Framework entries indicate the result that should exist. The organization must still assign a versioned artifact, owner, decision right, validation method, and review trigger to every result.

## Prerequisites

- Understand that an AI or Agent system commonly includes a model, prompts, data, retrieval, tools, identity, human steps, and runtime infrastructure.
- Have basic project-management, risk, testing, and versioning concepts; legal or audit training is not required.
- Read [[ai-safety/00-index|AI Safety]] and [[privacy-computing/00-index|Privacy Computing]] first to understand the boundary of technical controls.

## Recommended order

### 01 Foundations and risks

1. [[ai-governance/01-foundations-and-risks/01-system-inventory-and-accountability|System inventory and accountability]] — first answer “what is governed, who is responsible, and who can decide?”
2. [[ai-governance/01-foundations-and-risks/02-risk-tiering-and-impact-assessment|Risk tiering and impact assessment]] — derive review depth from the use case and affected people.

### 02 Controls and governance

3. [[ai-governance/02-controls-and-governance/03-data-model-and-vendor-governance|Data, model, and vendor governance]] — govern the value chain from data to external services.
4. [[ai-governance/02-controls-and-governance/04-documentation-transparency-and-traceable-evidence|Documentation, transparency, and traceable evidence]] — retain verifiable evidence for different audiences.
5. [[ai-governance/02-controls-and-governance/05-release-approval-and-change-management|Release approval and change management]] — bind evidence to versions, conditions, and decisions.
6. [[ai-governance/02-controls-and-governance/06-runtime-monitoring-incidents-and-retirement|Runtime monitoring, incidents, and retirement]] — govern real change and harm after release.
7. [[ai-governance/02-controls-and-governance/07-regulations-standards-and-regional-review|Regulations, standards, and regional review]] — distinguish voluntary frameworks, standards, organizational policy, and legal obligations.

### 03 Project and self-assessment

8. [[ai-governance/03-project-and-self-assessment/08-project-offline-ai-governance-pack|Project: Offline AI Governance Pack]] — integrate the first seven lessons into a reviewable JSON evidence pack.

## Hands-on project

- The capstone is [[ai-governance/03-project-and-self-assessment/08-project-offline-ai-governance-pack|Offline AI Governance Pack]].
- `03-project-and-self-assessment/examples/governance_pack.py` uses a synthetic scenario—assisting the organization of benefit-application materials—to produce an inventory, roles, impacts and risks, components, approvals, monitoring, incident, and retirement plan. It is offline, never touches real personal data, and requires no credentials.
- After each lesson, update the same governance pack for a “customer-support reply-drafting Agent” and compare how its scope, risks, and approval conditions change.

## Mastery checklist

- [ ] Every AI use case has a unique inventory ID, purpose, owner, status, components, regions, and review date.
- [ ] High-impact decisions have named accountable owners and an independent challenge channel; neither the model nor a vendor can accept residual risk on its own.
- [ ] A risk tier can be traced to severity, likelihood, scope of impact, reversibility, autonomy, and affected groups.
- [ ] Records for data, models, vendors, evaluation, approvals, and changes can be joined through version identifiers.
- [ ] Monitoring metrics have thresholds, actions, owners, and escalation paths; both incidents and danger signals enter a closed loop.
- [ ] Retirement revokes access, stops calls, handles data and logs, retains necessary evidence, and notifies dependent parties.
- [ ] You can explain why governance materials do not automatically demonstrate compliance with a particular law or standard.

## Relationship to other knowledge bases

- [[ai-safety/00-index|AI Safety]] produces threat models, red-team results, access controls, and incident evidence; governance determines responsibility, thresholds, and risk acceptance.
- [[privacy-computing/00-index|Privacy Computing]] provides data-minimization and privacy-enhancing technologies; governance approves purpose, budget, vendors, and lifecycle.
- [[evaluation-framework/00-index|Evaluation Framework]] and [[runtime-monitoring/00-index|Runtime Monitoring]] provide quantitative evidence before release and during operation.
- [[llmops/00-index|LLMOps]] governs versions, releases, and observability; governance specifies which changes require reassessment and approval.

## Primary references

- [NIST AI RMF 1.0](https://doi.org/10.6028/NIST.AI.100-1), the [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/), and the [Playbook](https://airc.nist.gov/airmf-resources/playbook/) (accessed 2026-07-22; NIST states that 1.0 is being revised and that the Playbook will be updated afterward)
- [NIST AI 600-1: Generative AI Profile](https://doi.org/10.6028/NIST.AI.600-1) (July 2024; accessed 2026-07-22)
- [OECD AI Principles](https://oecd.ai/en/ai-principles) and [OECD/LEGAL/0449](https://legalinstruments.oecd.org/en/instruments/OECD-LEGAL-0449) (principles updated May 2024; accessed 2026-07-22)
- [ISO/IEC 42001:2023 overview](https://www.iso.org/standard/42001), [ISO/IEC 42005:2025 overview](https://www.iso.org/standard/42005), and [ISO/IEC 42006:2025 overview](https://www.iso.org/standard/42006) (accessed 2026-07-22; the standard texts may require lawful access; 42006 concerns AIMS audit/certification bodies, not certification of a system or product itself)
- [Official text of Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj), [AI Omnibus final adopted text PE 30 2026 REV 1](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=consil%3APE_30_2026_REV_1), [Council of the EU final-adoption announcement of 2026-06-29](https://www.consilium.europa.eu/en/press/press-releases/2026/06/29/artificial-intelligence-council-gives-final-green-light-to-simplify-and-streamline-rules/), and the [European Commission AI Act timeline](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) (accessed 2026-07-22; check the Official Journal, effective status, and consolidated text again for a specific decision)

> [!warning] Scope boundary
> This course is engineering education material, not legal, compliance, certification, or audit advice. A production project must be reviewed by authorized people against its deployment location, users' location, industry, data, organizational role, and the latest authoritative texts. “Adopting a framework” does not equal “complying with a law.”
