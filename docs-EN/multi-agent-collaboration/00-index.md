---
title: "Multi-Agent Collaboration Learning Path"
tags:
  - ai-agent-engineer
  - multi-agent
  - learning-path
aliases:
  - Multi-Agent Collaboration Index
  - Multi-Agent Systems
source_checked: 2026-07-22
ai_learning_stage: 8. Extended Applications and Complex Collaboration
ai_learning_order: 47
ai_learning_schema: 2
ai_learning_id: multi-agent-collaboration
ai_learning_domain: agent-runtime
ai_learning_catalog_order: 4700
ai_learning_hard_prerequisites:
  - agent-core
ai_learning_track_agent_app_order: 1400
ai_learning_track_agent_app_kind: optional
ai_learning_track_agent_platform_order: 1600
ai_learning_track_agent_platform_kind: recommended
ai_learning_track_multimodal_realtime_order: 1300
ai_learning_track_multimodal_realtime_kind: optional
content_origin: original
content_status: dynamic
lang: en
translation_key: 多Agent协作/00-目录.md
translation_source_hash: acf2779b5fc62566823bd7ff03572eb743eee7ced6d2ab8b75ca95e5fbd28247
translation_route: zh-CN/多Agent协作/00-目录
translation_default_route: zh-CN/多Agent协作/00-目录
---

# Multi-Agent Collaboration

> Sources were checked on 2026-07-22. Multi-agent frameworks, SDKs, and interoperability protocols are changing quickly. This course emphasizes vendor-neutral collaboration contracts, state machines, and validation methods; version-specific facts are snapshots for that date only.

## Course overview

A multi-agent system has several agents with different responsibilities, tools, or contexts work on one task. It is not a way to “make a model smarter by opening several copies.” It is a distributed work system: the runtime must define task decomposition, control ownership, evidence and message transfer, recovery from failure, and stopping conditions. This course first establishes that multiple agents are actually needed, then covers topology, delegation, shared state, conflict control, and observability.

## Where this course fits

[[agent-core/00-index|Agent Core]] is the complete course-level hard prerequisite. The DAG, retry, and compensation knowledge in [[workflow-automation/00-index|Workflow Automation]] is recommended before complex collaboration, but it is not a hard prerequisite. Choose LangChain, CrewAI, or another framework only when the project needs it; none is a universal prerequisite. If one agent plus tools or a deterministic workflow is enough, stay with the simpler design.

## Learning objectives

- Decide with measurable reasons whether multiple agents are necessary, and establish a single-agent baseline.
- Choose a manager, handoff, pipeline, parallel, hierarchy, or peer topology.
- Write delegations as contracts with inputs, outputs, identity and authorization references, budgets, dependencies, and acceptance evidence.
- Design traceable messages, authoritative shared state, version control, and idempotent updates.
- Handle concurrent conflicts, timeout, failure, retry, compensation, cancellation, and human takeover.
- Evaluate end-to-end success, collaboration gain, cost, latency, recovery, and security boundaries.

## Prerequisites

- Complete [[agent-core/00-index|Agent Core]] and understand the run loop, state, and termination conditions.
- Understand parameter validation and tool permissions in [[tool-calling-function-calling/00-index|Tool Calling]].
- Read and write Python and JSON, and understand the basics of timeout, retry, idempotence, and logs.

## Recommended sequence

1. [[multi-agent-collaboration/fundamentals-and-architecture/01-when-to-use-multi-agent-systems|When to Use Multi-Agent Systems]] — establish a decision baseline and counterexample for not using them.
2. [[multi-agent-collaboration/fundamentals-and-architecture/02-roles-topologies-and-responsibility-boundaries|Roles, Topologies, and Responsibility Boundaries]] — choose a control structure and prevent overlapping duties.
3. [[multi-agent-collaboration/fundamentals-and-architecture/03-task-decomposition-and-delegation-contracts|Task Decomposition and Delegation Contracts]] — turn vague collaboration into acceptable subtasks.
4. [[multi-agent-collaboration/engineering-and-quality/08-identity-authorization-and-cross-boundary-trust|Identity, Authorization, and Cross-Boundary Trust]] — separate roles, runtime principals, delegation, approval, and receipts before treating orchestration as permission.
5. [[multi-agent-collaboration/engineering-and-quality/04-message-protocols-and-shared-state|Message Protocols and Shared State]] — establish a source of truth, message correlation, and state versions.
6. [[multi-agent-collaboration/engineering-and-quality/05-conflicts-synchronization-and-failure-recovery|Conflicts, Synchronization, and Failure Recovery]] — control concurrent writes, repeated execution, and partial failure.
7. [[multi-agent-collaboration/engineering-and-quality/06-budgets-stopping-and-human-intervention|Budgets, Stopping, and Human Intervention]] — give collaboration hard limits and explicit control ownership.
8. [[multi-agent-collaboration/engineering-and-quality/07-evaluation-observability-and-security-boundaries|Evaluation, Observability, and Security Boundaries]] — prove a collaboration benefit rather than admiring a polished conversation.
9. [[multi-agent-collaboration/project-and-self-check/08-offline-collaboration-simulator-project|Offline Collaboration Simulator Project]] — run a deterministic simulator with dependencies, permissions, retries, budget, and tracing.

## Hands-on entry point

Start with [[multi-agent-collaboration/project-and-self-check/08-offline-collaboration-simulator-project|Offline Collaboration Simulator Project]]. It uses only the Python 3 standard library and synthetic JSON scenarios; it makes no model or network call. Its audit events include state versions so you can validate dependency scheduling, permission denials, finite retry, conflict freezing for the same idempotency key, and stopping reasons.

## Mastery checklist

- I can state the simplest single-agent or workflow baseline before explaining a measurable multi-agent benefit.
- I can draw roles, control ownership, shared state, message directions, and human-approval points.
- I can show that every subtask has one clear owner and complete input, output, and acceptance conditions.
- I can distinguish a role name, runtime principal, delegation reference, short-lived approval, and an external receipt, and never pass long-lived credentials in agent messages.
- I can produce a deterministic terminal state under duplicate messages, concurrent updates, partial failure, and budget exhaustion.
- I can compare designs with task success, incremental gain, total cost, critical-path latency, and security-violation rate.

## Relationships to other courses

- [[agent-core/00-index|Agent Core]] supplies the single-agent loop, state, and authorization boundary.
- [[workflow-automation/00-index|Workflow Automation]] supplies DAGs, scheduling, retry, and compensation; multi-agent systems are only one way to organize executors.
- [[mcp/00-index|MCP]] addresses how agents connect to tools and data; [[a2a/00-index|A2A]] addresses discovery, tasks, and artifact interoperability between independent agent applications. Neither replaces this course's task ownership and collaboration design.
- [[evaluation-framework/00-index|Evaluation Framework]], [[runtime-monitoring/00-index|Runtime Monitoring]], and [[ai-safety/00-index|AI Safety]] respectively extend quality, runtime evidence, and risk governance.

## Protocol landscape and observation status

| Boundary | Protocol or method | Status on 2026-07-22 | How this course uses it |
| --- | --- | --- | --- |
| Agent ↔ tools and data | MCP | Stable core and independent extensions coexist | A capability-integration boundary, not a replacement for task ownership or collaboration state |
| Agent ↔ agent | [[a2a/00-index\|A2A]] | The official specification page lists 1.0.0 as the latest released specification; patch release records do not change negotiated `Major.Minor` | Use only when cross-process or cross-organization interoperability is truly needed; pin Agent Card, Task/Message/Artifact, identity, and version contracts |
| Agent ↔ user-facing app | AG-UI | First-party documentation describes an event protocol and lists Draft Proposals; adoption is not independently audited in this knowledge base | Treat as an observation point for UI streaming, state, interrupts, and tool events, not as a multi-agent prerequisite |

The three interfaces solve different problems and must not be conflated because their names sound similar. Integrations listed on the AG-UI site are project claims, not proof of broad production adoption in this knowledge base. Before adopting it, pin an event version and test reordering, duplication, reconnect recovery, permissions, and front-end side effects before promoting it into a stable course.

## Primary references

- [OpenAI Agents SDK: Agent orchestration](https://openai.github.io/openai-agents-python/multi_agent/) — accessed 2026-07-22.
- [LangChain documentation: Multi-agent](https://docs.langchain.com/oss/python/langchain/multi-agent/index) — accessed 2026-07-22.
- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/) and its [official changelog](https://github.com/a2aproject/A2A/blob/main/CHANGELOG.md) — accessed 2026-07-22; the specification page lists 1.0.0 as the latest release, and patch versions do not participate in protocol compatibility negotiation.
- [AG-UI Overview](https://docs.ag-ui.com/introduction) — accessed 2026-07-18; observed as an agent-to-user-interface protocol, with draft proposals also listed by the site.
- Wu et al., [AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation](https://arxiv.org/abs/2308.08155) — original paper.
- [NIST AI RMF 1.0](https://www.nist.gov/itl/ai-risk-management-framework) and its [Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence) — accessed 2026-07-18; the official 1.0 page indicates it is being revised.
