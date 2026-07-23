---
title: "A2A Protocol"
aliases:
  - Agent2Agent Protocol
  - Inter-agent interoperability protocol
tags:
  - ai-agent-engineer
  - a2a
  - interoperability
  - learning-roadmap
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline: A2A Protocol 1.0.0 official specification and migration notes
ai_learning_stage: 9. Frontier and references
ai_learning_order: 54
ai_learning_schema: 2
ai_learning_id: a2a-protocol
ai_learning_domain: frontier-reference
ai_learning_catalog_order: 5400
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 1450
ai_learning_track_agent_app_kind: optional
ai_learning_track_agent_platform_order: 1700
ai_learning_track_agent_platform_kind: optional
lang: en
translation_key: A2A/00-目录.md
translation_source_hash: 1e7ca425b2a6f169b15c83bd83e0e029eca8f25b1784182b1d604be2d9199bfc
translation_route: zh-CN/A2A/00-目录
translation_default_route: zh-CN/A2A/00-目录
---

# A2A Protocol

## Course overview

A2A (the Agent2Agent Protocol) addresses how **independently built, potentially opaque Agent applications** discover capabilities, exchange messages, manage long-running work, and deliver results. It does not prescribe an Agent's internal reasoning, nor does it replace [[mcp/00-index|MCP]], [[tool-calling-function-calling/00-index|Tool Calling]], or a specific Agent framework.

This course uses A2A Protocol \`1.0.0\` as its contract baseline. It develops testable engineering understanding of protocol boundaries, Agent Cards, Task lifecycles, the three standard bindings, asynchronous delivery, identity and authorization, multitenant isolation, version migration, and interoperability testing. The lessons and examples are original to this project; the official specification is used only as a factual source and does not reproduce its text or SDK.

> [!important] A moving boundary
> On 2026-07-21, the A2A official site listed \`1.0.0\` as the latest released version. The protocol core has reached a stable release, but SDKs, extensions, the TCK, and framework adapters can still change. Before a production integration, re-check the official specification, the target SDK version, and the server Agent Card. This course's offline validator is a teaching contract, not official conformance certification.

## Why this belongs in “Frontier and references”

\`frontier-reference\` accepts only topics that meet all of these conditions:

1. They have a public, versionable primary specification or original paper, rather than a marketing concept alone.
2. They can produce testable engineering artifacts rather than merely list news.
3. Their boundary with the main curriculum is clear, so they do not duplicate the existing knowledge base.
4. They explicitly record the observation date, adoption conditions, exit conditions, and migration risks.
5. Their core learning method remains transferable even if the ecosystem changes.

A2A 1.0 has a formal specification, version negotiation, standard bindings, a security section, and interoperability-test requirements. Learners can produce Agent Cards, Task-state contracts, negative test cases, and adoption records, so it meets the admission criteria. It remains an optional course on both role tracks; it is not presented as a default dependency for every Agent project.

## Where it fits in the overall roadmap

- Agent application development: study it after completing single-Agent, workflow, or multi-Agent practice, when cross-framework or cross-organization delegation is needed.
- Agent platforms and reliability: study it when building an Agent catalog, gateway, identity layer, version compatibility, or interoperability testing.
- In-process sub-Agents, handoffs inside one framework, and ordinary tool calls do not need A2A merely to “keep up with the trend.”

The following capabilities are recommended but are not whole-course hard prerequisites:

- Ability to read JSON, HTTP, authentication headers, and state machines.
- Understanding of delegation, routing, and failure isolation in [[multi-agent-collaboration/00-index|Multi-Agent Collaboration]].
- Understanding of trust boundaries and object-level authorization in [[ai-safety/00-index|AI Safety]].

## Learning objectives

- Accurately distinguish A2A, MCP, Tool Calling, Agent frameworks, and ordinary business APIs.
- Design an Agent Card that makes capabilities discoverable without overexposing internal details.
- Correctly distinguish Message, Task, TaskStatus, Part, and Artifact.
- Choose suitable delivery and recovery strategies for polling, streaming subscriptions, and webhooks.
- Separate authentication, authorization, tenant routing, credential acquisition, and approval into independent boundaries.
- Identify the breaking structural changes from A2A \`0.3\` to \`1.0\` and establish evidence for a dual-version migration.
- Run the offline contract-validation project and state which online properties it does not prove.

## Recommended sequence

1. [[a2a/01-protocol-boundaries-and-architecture|Protocol boundaries and architecture]]
2. [[a2a/02-agent-card-discovery-and-trust|Agent Cards, discovery, and trust]]
3. [[a2a/03-task-message-and-artifact-lifecycle|Task, Message, and Artifact lifecycles]]
4. [[a2a/04-transports-streaming-asynchrony-and-version-negotiation|Transports, streaming, asynchrony, and version negotiation]]
5. [[a2a/05-authentication-authorization-and-multitenant-security|Authentication, authorization, and multitenant security]]
6. [[a2a/06-interoperability-testing-migration-and-adoption|Interoperability testing, migration, and adoption decisions]]
7. [[a2a/07-offline-a2a-contract-validation-project|Project: offline A2A contract validation]]

## The protocol’s place at a glance

\`\`\`mermaid
flowchart LR
    U["User or upstream system"] --> CA["Client Agent"]
    CA -->|"A2A: discovery, messages, Tasks, Artifacts"| RA["Remote Agent"]
    CA -->|"MCP: tools and resources"| CT["Client Agent tools"]
    RA -->|"MCP or business API"| RT["Remote Agent tools"]
    CA -. "Framework-internal orchestration" .-> SUB["Local sub-Agent / workflow"]
\`\`\`

This diagram is an original redraw for this project. It expresses responsibility boundaries; it does not mean that every system must use both A2A and MCP.

## Mastery standard

- Decide from a requirement whether it needs protocol interoperability or an in-application function call.
- Inspect the required Agent Card fields, binding, version, capabilities, and security declarations.
- Explain the different recovery paths for \`INPUT_REQUIRED\`, \`AUTH_REQUIRED\`, and terminal states.
- Write negative tests for webhook replay, SSRF, unauthorized queries, cross-tenant IDs, and untrusted Artifacts.
- Explain why a \`0.3\` structure cannot impersonate \`1.0\`, and provide evidence for a gradual migration and rollback.
- Report offline schema/state checks separately from validation with a real SDK, TCK, TLS, identity provider, and production observability.

## Primary references

- [A2A Protocol 1.0.0 official specification](https://a2a-protocol.org/latest/specification/)
- [A2A Protocol v1.0 change notes](https://a2a-protocol.org/latest/whats-new-v1/)
- [Official A2A and MCP boundary guidance](https://a2a-protocol.org/latest/topics/a2a-and-mcp/)
- [A2A official roadmap](https://a2a-protocol.org/latest/roadmap/)
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785)
- [RFC 7515: JSON Web Signature](https://www.rfc-editor.org/rfc/rfc7515)
