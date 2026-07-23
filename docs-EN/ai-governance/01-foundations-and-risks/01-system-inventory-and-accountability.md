---
title: "System Inventory and Accountability"
aliases:
  - AI System Inventory and Accountability
tags:
  - ai-governance
  - inventory
  - accountability
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: AI治理/01-基础与风险/01-系统清单与角色责任.md
translation_source_hash: 4de4e46c70d5242980d5c02aba93dce8adb72bb740be55e9a518e4b0d0697cf2
translation_route: zh-CN/AI治理/01-基础与风险/01-系统清单与角色责任
translation_default_route: zh-CN/AI治理/01-基础与风险/01-系统清单与角色责任
---

# System Inventory and Accountability

## Goal of this lesson

Build an AI-system inventory that can genuinely support decisions, and assign each responsibility to a person who has authority to act. Governance does not first fail because an organization lacks a complicated policy; it fails because the organization does not know which AI systems are being used by whom, for what purpose, and with consequences for whom.

## What counts as a system

Do not register only the foundation model. A governable AI system is the whole arrangement used for a particular purpose: its interface, prompts, model, RAG data, embeddings, tools, identities, human steps, vendors, logs, and downstream decisions all belong within the boundary. Using the same model for “marketing-copy drafts” and “candidate screening” should result in two use-case records because the affected people and risks are fundamentally different.

The inventory covers internally developed systems, procured SaaS, open-source models, AI built into office software, pilots, shadow use, and retired systems that still retain data. An experiment is not exempt from registration; manage it with lighter fields and an `experiment` status where appropriate.

For Agent systems, also register non-human identities and runtime-discovered components: workload or service identities, delegated users and tenants, MCP or tool servers, other Agents, queues, and automatic triggers. They are not merely “infrastructure details.” They define who may act for whom, what actions are possible, and where failures can propagate.

## Minimum inventory fields

| Field | Question it answers |
| --- | --- |
| `system_id`, name, and status | Which system does this uniquely identify? Is it proposed, experimental, in production, paused, or retired? |
| Purpose and prohibited uses | Why use AI here? What is explicitly not allowed? What is the non-AI alternative? |
| Business owner and system owner | Who owns the business outcome? Who can disable and remediate the system? |
| Users and affected people | Who operates it? Who may bear errors or be excluded? |
| Output and degree of autonomy | Is the output a draft, recommendation, ranking, decision, or automated action? Can a person revise or veto it? |
| Components and versions | Which models, data sources, prompts, tools, vendors, deployments, and critical dependencies are involved? |
| Data and regions | Which data categories are used? In which regions are processing, deployment, and affected people located? |
| Risk and evidence | Where are the current tier, impact assessment, testing, approvals, and residual-risk links? |
| Operation and lifecycle | Who owns monitoring? What are the review date, incident entry point, rollback conditions, and retirement conditions? |

An inventory is not a one-time questionnaire. Update its status at release, material change, and retirement. Asset discovery, procurement, expense, identity, network-traffic, and model-call logs can reveal unregistered systems, but they cannot replace a human confirmation of intended use.

## Roles and decision rights

- **Senior leadership or governance body**: sets risk tolerance and unacceptable uses, and handles risk acceptance that exceeds project authority.
- **Business owner (Accountable)**: owns the purpose, benefit, affected people, and ultimate use; a decision should normally have one clearly accountable owner.
- **System or product owner**: maintains boundaries, versions, controls, monitoring, changes, and the ability to disable the system.
- **Data and model owners**: provide evidence about provenance, quality, suitability, versions, and limitations.
- **Security, privacy, legal/compliance, and domain experts**: review within their respective responsibilities; none substitutes for the others.
- **Independent evaluators or risk challengers**: question assumptions and evidence; developers must not approve their own high-risk exceptions alone.
- **Operations and incident owners**: monitor, escalate, contain impact, recover, and conduct post-incident reviews.
- **Procurement or vendor owners**: manage contracts, change notices, exit arrangements, and third-party evidence.
- **Users and affected groups**: provide feedback about real workflows, usability, appeals, and potential impacts.

RACI (Responsible, Accountable, Consulted, Informed) can clarify division of work, but it is not a liability waiver. State separately who may release or pause a system, accept residual risk, approve an exception, respond to an appeal, and declare retirement.

## Example accountability chain

For a “customer-support reply-drafting Agent,” the customer-support operations owner is accountable for the purpose, the platform owner maintains the system, the security team reviews tool permissions, the privacy owner reviews data flows, a quality team validates independently, and the on-call manager can perform an emergency shutdown. The model vendor remains responsible for its own service, but cannot decide whether the organization should use that service with its customers.

## Exercise and self-check

List three AI use cases you encounter in daily work. For each, write its system boundary, prohibited uses, affected people, accountable owner, and emergency shutdown authority. If two people both say they “only provide advice,” accountability is still incomplete.

- [ ] Can distinguish a model, a component, and a complete AI system.
- [ ] Can identify pilots, SaaS-embedded AI, and shadow use.
- [ ] Every high-impact decision has a named, authorized accountable owner.
- [ ] Vendor responsibility does not replace the deployer's responsibility for the actual use context.

## Next step and source baseline

Continue with [[ai-governance/01-foundations-and-risks/02-risk-tiering-and-impact-assessment|Risk Tiering and Impact Assessment]]. Sources were accessed on 2026-07-21. Govern 1.6 of the NIST AI RMF Core calls for an AI-system inventory, and Govern 2 covers roles and senior accountability; see the [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) and [Govern Playbook](https://airc.nist.gov/airmf-resources/playbook/govern/). These are voluntary framework recommendations, not universal legal obligations.
