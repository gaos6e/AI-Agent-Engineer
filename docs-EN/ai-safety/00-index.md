---
title: "AI Safety Learning Path"
aliases:
  - AI safety from-zero learning path
  - Agent security knowledge base
tags:
  - ai-security
  - ai-agent
  - security
source_checked: 2026-07-22
ai_learning_stage: 7. Production, evaluation, and governance
ai_learning_order: 44
ai_learning_schema: 2
ai_learning_id: ai-safety
ai_learning_domain: safety-governance
ai_learning_catalog_order: 4400
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 1200
ai_learning_track_agent_app_kind: core
ai_learning_track_rag_order: 1400
ai_learning_track_rag_kind: core
ai_learning_track_agent_platform_order: 1400
ai_learning_track_agent_platform_kind: core
ai_learning_track_multimodal_realtime_order: 900
ai_learning_track_multimodal_realtime_kind: core
content_origin: original
content_status: dynamic
lang: en
translation_key: AI安全/00-目录.md
translation_source_hash: 44010a97326be71fc4bfff3effba321ae6faddb0f470c99060de3748d7f44694
translation_route: zh-CN/AI安全/00-目录
translation_default_route: zh-CN/AI安全/00-目录
---

# AI Safety Learning Path

## About this knowledge base

AI safety examines whether a system continues to protect confidentiality, integrity, availability, and human safety and autonomy during ordinary use, failure, misuse, and attack. Once an Agent connects a probabilistic model to private data, identities, and tools, a mistaken string of text can become a real-world side effect. This course follows a path from assets and trust boundaries, through injection and tool risks, to identity and supply chain controls, defense in depth, and red teaming and incident response.

This course does not treat a model refusal, a system prompt, or a single filter as a complete defense. Its central principle is that external content and model output are untrusted proposals; permissions, authorization, destinations, approval, and execution must be determined at testable boundaries outside the model.

## Where this course fits in the overall route

This course belongs to the Safety and Governance knowledge domain and is a core course near the production-release gate in four role tracks. Earlier practice should still complete the overall route's minimum security milestone. When studying the full course, apply the concrete system boundaries from [[tool-calling-function-calling/00-index|Tool Calling]], [[agent-core/00-index|Agent Core]], [[workflow-automation/00-index|Workflow Automation]], and [[runtime-monitoring/00-index|Runtime Monitoring]], together with [[privacy-computing/00-index|Privacy Computing]], [[evaluation-framework/00-index|Evaluation Framework]], and [[ai-governance/00-index|AI Governance]].

## Terminology boundaries

- **AI security**: resisting attacks, misuse, and failures in order to protect systems and assets.
- **AI safety**: the broader effort to prevent a system's behavior from harming people and society, including but not limited to security attacks.
- **privacy**: whether data collection, use, sharing, and data-subject rights are protected.
- **governance**: how accountability, policy, risk acceptance, oversight, and responsibility are organized.

The four areas support one another but are not substitutes. This is engineering education material; it is not legal, compliance, penetration-testing, or risk-acceptance advice.

## Learning objectives

- Identify assets, attackers, data flows, and trust boundaries from an intended use and unacceptable outcomes.
- Distinguish direct and indirect prompt injection, jailbreaks, and memory/context poisoning, and limit their maximum impact.
- Apply least functionality, least privilege, object-level authorization, destination controls, and egress controls to tools.
- Establish supply-chain evidence for identities, models, data, prompts, MCP servers, Skills, dependencies, and deployment artifacts.
- Combine guardrails, deterministic policy, sandboxes, parameter-bound approvals, audit, and emergency shutdown correctly.
- Derive red-team sets, release gates, monitoring signals, and incident-response runbooks from a threat model.
- Run a strict-contract, regression-tested, appropriately scoped offline threat-review project.

## Prerequisites

- Basic concepts in HTTP, JSON, Python, and identity authentication.
- An understanding that Tool Calling generates candidate calls; it does not itself provide authorization.
- An understanding that model output is probabilistic and that web pages, email, RAG, tool results, and other Agents may be untrusted.

## Recommended order

### 01 Foundations and risks

1. [[ai-safety/01-foundations-and-risks/01-assets-trust-boundaries-and-threat-modeling|Assets, trust boundaries, and threat modeling]] — build verifiable risk records from losses, assets, and data flows.
2. [[ai-safety/01-foundations-and-risks/02-prompt-injection-and-indirect-injection|Prompt injection and indirect injection]] — understand why untrusted text cannot share control authority.
3. [[ai-safety/01-foundations-and-risks/03-tool-overreach-and-data-exfiltration|Tool overreach and data exfiltration]] — turn security boundaries into authorization, destination, and side-effect controls.

### 02 Controls and governance

4. [[ai-safety/02-controls-and-governance/04-identity-least-privilege-and-supply-chain|Identity, least privilege, and the supply chain]] — constrain execution identities and trace every Agent component.
5. [[ai-safety/02-controls-and-governance/05-guardrails-sandboxes-and-human-approval|Guardrails, sandboxes, and human approval]] — use controls outside the model to limit the blast radius of failures.
6. [[ai-safety/02-controls-and-governance/06-red-teaming-monitoring-and-incident-response|Red teaming, monitoring, and incident response]] — continuously validate, detect, contain, recover, and learn.

### 03 Project and self-assessment

7. [[ai-safety/03-project-and-self-assessment/07-project-offline-agent-threat-review|Project: Offline Agent Threat Review]] — run a strict JSON contract, eleven teaching rules, and eighty tests.

## Coverage of the 2026 Agentic Top 10

The OWASP Agentic Top 10 for 2026 can help identify omissions, but it does not replace a system-specific view of assets, attack paths, authorization boundaries, and validation evidence. The table only shows where this course enters each risk; reading a section does not mean the risk has been eliminated.

| OWASP category | Main entry points in this course | Required end state to verify |
| --- | --- | --- |
| ASI01 Agent Goal Hijack; ASI06 Memory & Context Poisoning | [[ai-safety/01-foundations-and-risks/02-prompt-injection-and-indirect-injection\|Prompt injection and indirect injection]], [[ai-safety/02-controls-and-governance/06-red-teaming-monitoring-and-incident-response\|Red teaming and incident response]] | Untrusted content cannot expand capability; poisoned state can be isolated, removed, and rolled back. |
| ASI02 Tool Misuse & Exploitation; ASI05 Unexpected Code Execution | [[ai-safety/01-foundations-and-risks/03-tool-overreach-and-data-exfiltration\|Tool overreach and data exfiltration]], [[ai-safety/02-controls-and-governance/05-guardrails-sandboxes-and-human-approval\|Sandboxes and approval]] | Unauthorized side effects are denied; code execution is constrained by explicit file, network, and resource boundaries. |
| ASI03 Identity & Privilege Abuse; ASI04 Agentic Supply Chain Vulnerabilities | [[ai-safety/02-controls-and-governance/04-identity-least-privilege-and-supply-chain\|Identity, least privilege, and the supply chain]] | Every call is reauthorized using the actual subject, object, and state; runtime components can be traced, disabled, and rolled back. |
| ASI07 Insecure Inter-Agent Communication; ASI08 Cascading Failures | [[ai-safety/01-foundations-and-risks/01-assets-trust-boundaries-and-threat-modeling\|Threat modeling]], [[ai-safety/02-controls-and-governance/06-red-teaming-monitoring-and-incident-response\|Red teaming and incident response]] | Inter-Agent messages have identity, integrity, and permission boundaries; errors do not amplify across workflows without a budget. |
| ASI09 Human-Agent Trust Exploitation; ASI10 Rogue Agents | [[ai-safety/02-controls-and-governance/05-guardrails-sandboxes-and-human-approval\|Sandboxes and approval]], [[ai-safety/02-controls-and-governance/06-red-teaming-monitoring-and-incident-response\|Red teaming and incident response]] | People can see and reject the real action; runtime boundary violations can be detected, disabled, and recovered. |

An attack often spans several categories: for example, a malicious document can hijack a goal, misuse an overprivileged tool, spread through collaborating Agents, and induce human approval. Keep the full chain in the review instead of splitting it into ten disconnected checks merely to align with the Top 10.

For ASI07, continue with [[multi-agent-collaboration/engineering-and-quality/08-identity-authorization-and-cross-boundary-trust|Identity, authorization, and cross-boundary trust for multi-Agent systems]] for protocol-level contracts and cross-boundary authorization. This course connects those failures back to threat modeling, red teaming, release gates, and incident response.

## Suggested study rhythm

On the first pass, complete each exercise and draw a system diagram of your own. On the second, enter the real tools, identities, data, and dependencies of an existing Agent into the project contract. On the third, turn high-risk findings into negative tests, monitoring alerts, and incident runbooks. Do not only memorize OWASP category names.

## Hands-on project

Start with [[ai-safety/03-project-and-self-assessment/07-project-offline-agent-threat-review|Offline Agent Threat Review]]. The project is entirely offline. It provides vulnerable, hardened, and contract-error paths; exit codes distinguish a blocked business decision, a pass, and invalid input. Its tests cover strict parsing, complete references, eleven findings, decisions, evidence fingerprints, and the CLI.

## Mastery checklist

- [ ] Can derive the minimum capability from an intended use and draw identities, policies, tools, and data boundaries outside the model.
- [ ] Can write an attack path with preconditions, steps, assets, impact, and an end state.
- [ ] Can prevent external content from expanding tools, permissions, destinations, or approval.
- [ ] Can distinguish the responsibilities of schema validation, authentication, authorization, approval, sandboxing, and guardrails.
- [ ] Can trace and disable or roll back models, data, prompts, Skills/MCP, dependencies, and deployments.
- [ ] Can create security regression gates from malicious inputs, tool end states, and data-flow assertions.
- [ ] Can revoke access, isolate, preserve the minimum evidence, recover safely, and create a lasting regression during an incident.
- [ ] Can explain the evidence boundary of a project `PASS` without claiming it equals a penetration test or absolute system security.

## Relationship to other knowledge bases

- [[privacy-computing/00-index|Privacy Computing]] focuses on data use and privacy protection, but cannot replace authorization, supply-chain security, or incident response.
- [[ai-governance/00-index|AI Governance]] determines risk responsibility, approval, oversight, and accountability; this course supplies verifiable technical evidence.
- [[evaluation-framework/00-index|Evaluation Framework]] and [[benchmark-design/00-index|Benchmark Design]] turn red-team paths into version gates and comparable experiments.
- [[runtime-monitoring/00-index|Runtime Monitoring]] carries signals for tool denials, identities, versions, unusual destinations, and emergency controls.
- [[multi-agent-collaboration/00-index|Multi-Agent Collaboration]] handles delegation, messaging, and cross-boundary identity contracts; this course closes the safety-control loop around their attack paths, end states, and incident evidence.

## Primary references

- [OWASP Top 10 for Large Language Model Applications 2025](https://genai.owasp.org/llm-top-10/) (accessed 2026-07-22)
- [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) (published December 2025; accessed 2026-07-22)
- [MITRE ATLAS](https://atlas.mitre.org/) and the [ATLAS data repository and release history](https://github.com/mitre-atlas/atlas-data/releases) (continuously updated; production mappings should pin the release or tag used; accessed 2026-07-22)
- [NIST AI 600-1, Generative AI Profile](https://doi.org/10.6028/NIST.AI.600-1) (July 2024; accessed 2026-07-22)
- [NIST SP 800-218A](https://csrc.nist.gov/pubs/sp/800/218/a/final) (final, July 2024; accessed 2026-07-22)
- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) (final, April 2025; accessed 2026-07-22)

> [!warning] Dynamic-fact boundary
> OWASP, MITRE ATLAS, models, frameworks, and attack techniques continue to change. Versions and publication dates were checked against official material accessible on 2026-07-22. Before deployment, recheck the current versions, vendor documentation, applicable regional law, and organizational policy.
