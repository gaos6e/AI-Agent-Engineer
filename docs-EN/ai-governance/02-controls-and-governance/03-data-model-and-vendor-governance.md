---
title: "Data, Model, and Vendor Governance"
aliases:
  - AI Data Model Vendor Governance
tags:
  - ai-governance
  - data-governance
  - model-governance
  - vendor-risk
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
lang: en
translation_key: AI治理/02-控制与治理/03-数据模型与供应商治理.md
translation_source_hash: 8c4813961a8af1b38d7c931ceb3ddf45ba816db0b0730ddcfa137ca04e100bd2
translation_route: zh-CN/AI治理/02-控制与治理/03-数据模型与供应商治理
translation_default_route: zh-CN/AI治理/02-控制与治理/03-数据模型与供应商治理
---

# Data, Model, and Vendor Governance

## Goal of this lesson

Decompose an AI system into traceable components and responsibility boundaries, and govern risks from the introduction through exit of data, models, tools, and vendors. The object of governance is not an API name; it is a value chain that may change at any time.

## Evidence for data governance

For every data source, record its provenance and owner; collection and use purpose; fields and data subjects; license or other authorization basis; representativeness and known gaps; labeling process; quality checks; sensitive categories; access; retention and deletion; cross-border processing or sharing; version; and lineage. Training, RAG, evaluation, human feedback, logs, and caches must be registered separately. Do not collapse them into the phrase “public data.”

Data quality must be tied to the task. A large history of customer-service tickets does not make the data suitable for medical advice; high label consistency does not make a historical process fair. If provenance or permission cannot be demonstrated, do not dismiss the problem by claiming that “the model will not reproduce it verbatim.”

## Governing models and system components

At minimum, a model record contains its provider; model or weight identifier; version or snapshot date; license; intended and prohibited uses; context limits; training or fine-tuning summary when available; evaluation; known limitations; security configuration; data-processing path; update policy; and rollback version.

Prompts, retrieval indexes, embeddings, thresholds, tool schemas, guardrails, and human processes also change behavior and therefore belong in the component inventory and version chain. When a hosted model has no fixed weight version, record the provider-visible version, call date, region, and regression results, and treat uncontrollable change as a risk.

The component inventory can extend a conventional SBOM, but must not merely list package names. Each item should also link to provenance or license, integrity or pinning evidence, runtime identity, accessible data, network destinations, change notices, and rollback. Dynamically discovered MCP servers, tools, and other Agents must first form a versioned snapshot and diff, then pass an allowlist and authorization gate before entering runtime.

## Vendor due diligence

Before procurement, replace marketing terms with verifiable questions:

- Which inputs, outputs, logs, and feedback can the service receive, retain, train on, or expose to human review? What are the defaults, and what is configurable?
- Where are data, subprocessors, and support personnel located? Which notifications and approvals does the organization need?
- How are model, policy, filter, and API changes announced? Are pinned versions, transition windows, rollback, or export available?
- Which evaluation, safety, privacy, availability, and incident evidence is provided? Does that evidence cover your specific configuration?
- Who notifies whom of a serious incident, data issue, or service change, within what period? How will the vendor assist investigation, deletion, appeals, and regulatory inquiries?
- At exit, how are necessary records exported, data deleted, identities revoked, and service switched to a manual or alternative path?

A contract can address data use, retention, subprocessors, change notices, service levels, incident cooperation, audit evidence, intellectual property, allocation of responsibility, and termination assistance; procurement and legal teams determine specific clauses. A certification or report is input evidence, not proof that your intended use, configuration, and integration are safe.

## Shared responsibility and concentrated failure

A vendor is responsible for its components, while the organization remains responsible for selection, configuration, downstream actions, and the actual use experienced by affected people. Build a matrix of “control → responsible party → evidence → action on failure,” with special attention to gaps where each party assumes the other is responsible.

Avoid a single dependency point. Prepare rate limiting, network isolation, model fallback, manual handling, data export, and exit arrangements. When a vendor cannot provide necessary transparency, reduce the system's permissions, narrow its use, or do not adopt it; contractual wording cannot fill an unverifiable technical fact.

## Exercise and self-check

For an Agent that combines an external LLM, internal RAG, and a ticket-creation tool, make a component table. For each item, record data destination, version, responsible party, change notice, validation evidence, and exit action. Identify at least two paths by which a vendor failure could propagate into the business.

- [ ] Data, models, prompts, indexes, tools, and human processes all have versions and owners.
- [ ] Can distinguish a vendor statement, independent evidence, and a test of the organization's own configuration.
- [ ] Contracts, technical controls, and runtime monitoring complement rather than replace one another.
- [ ] Exit and manual fallback are designed before adoption.

## Next step and source baseline

Continue with [[ai-governance/02-controls-and-governance/04-documentation-transparency-and-traceable-evidence|Documentation, Transparency, and Traceable Evidence]]. Sources were accessed on 2026-07-21. See Govern 6 and Map 4 of the [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/), the value-chain and component-integration guidance in [NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1), and the [NIST Govern Playbook](https://airc.nist.gov/airmf-resources/playbook/govern/). These sources provide risk-management guidance, not an endorsement of vendor compliance.
