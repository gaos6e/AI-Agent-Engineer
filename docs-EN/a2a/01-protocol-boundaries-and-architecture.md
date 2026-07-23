---
title: "A2A Protocol Boundaries and Architecture"
aliases:
  - A2A architecture
  - A2A protocol boundary
tags:
  - a2a
  - agent-architecture
  - interoperability
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline: A2A Protocol 1.0.0 official specification
lang: en
translation_key: A2A/01-协议边界与架构.md
translation_source_hash: 16dbae31833d16245f32fd0a1501104f3c13118a6a46654418394a2c947ce58c
translation_route: zh-CN/A2A/01-协议边界与架构
translation_default_route: zh-CN/A2A/01-协议边界与架构
---

# A2A Protocol Boundaries and Architecture

## Goals of this lesson

- Decide whether a problem actually needs A2A.
- Distinguish an inter-Agent protocol, a tool protocol, in-application orchestration, and an ordinary API.
- Design protocol interoperability separately from business trust.

## What A2A solves

A2A is for two independently deployed Agent applications, potentially built by different teams or frameworks. The caller depends only on the other application's public capabilities, communication interface, and Task semantics; it does not need to read the other application's prompt, memory, tool inventory, or internal execution graph.

Its core interoperability surface includes:

- Describing identity, capabilities, skills, bindings, versions, and security requirements through an Agent Card.
- Starting or continuing an interaction with a Message.
- Representing stateful, potentially long-running work as a Task.
- Delivering Task outputs as Artifacts.
- Receiving progress through polling, streaming subscriptions, or webhooks.
- Keeping semantics equivalent across bindings and explicitly negotiating the protocol version.

## Five boundaries that are often confused

| Mechanism | Primary endpoints | Problem it solves | What it does not cover |
| --- | --- | --- | --- |
| Tool Calling | Model/runtime ↔ application tool executor | The model proposes a structured call; the application validates and executes it | Cross-organization Agent discovery and a long-task protocol |
| MCP | Host/client ↔ MCP Server | Connects context capabilities such as tools, resources, and prompts | Task collaboration between independent Agent applications |
| Agent framework | Components inside one application | State graphs, handoffs, sub-Agents, and persistence | An open, cross-implementation network contract |
| A2A | Client Agent ↔ Remote Agent | Capability discovery, messages, Tasks, Artifacts, and asynchronous collaboration | Internal reasoning algorithms and concrete tool implementations |
| Ordinary business API | Service consumer ↔ domain service | A business contract for an explicit resource or command | A general Agent Task lifecycle |

> [!warning] A protocol is not trust
> A party claiming to speak A2A does not make its identity, skill descriptions, results, or security declarations trustworthy. The deploying party must still establish discovery, authentication, authorization, output validation, auditing, and contractual accountability.

## When adoption is worthwhile

The more of these conditions apply, the more valuable A2A becomes:

- Agents evolve independently across teams, vendors, or technology stacks.
- Calls need long-running Tasks, streaming progress, human-supplied input, or asynchronous recovery.
- A discoverable capability catalog is needed instead of shared internal code.
- The same semantic model should be preserved across JSON-RPC, gRPC, and HTTP+JSON.
- Protocol versions, extensions, and cross-organization security boundaries require explicit management.

The following situations normally call for a smaller interface first:

- Handing a task to a Python function in the same process.
- A subgraph or handoff inside the same LangGraph or CrewAI application.
- An ordinary domain service with one fixed request and one fixed response.
- No separate release, permission, or version boundary—only a desire to add an “Agent protocol” label.

## Minimal deployment view

\`\`\`mermaid
sequenceDiagram
    participant C as Client Agent
    participant D as Discovery Endpoint
    participant S as A2A Server
    participant I as Identity Provider

    C->>D: Fetch Agent Card
    D-->>C: Interfaces, versions, skills, and security declarations
    C->>C: Verify origin, version, and local adoption policy
    C->>I: Obtain credentials through an out-of-protocol flow
    I-->>C: Least-privilege credentials
    C->>S: Send A2A request + identity credentials
    S->>S: Authenticate, authorize objects, execute, and audit
    S-->>C: Message / Task / streaming event / Artifact
\`\`\`

The Identity Provider is not implemented by A2A. The specification describes how security schemes are declared and carried with requests, but credential acquisition, policy decisions, and resource authorization belong to the deployment system.

## Six questions before adoption

1. Which two independently released units need to interoperate?
2. Why is an ordinary API insufficient? Is discovery, Task state, or asynchronous delivery missing?
3. Who issues the caller identity, and by which objects and tenants does the server authorize it?
4. Which data may cross the boundary, and which Artifacts must be sanitized or isolated?
5. How are the protocol version, SDK version, and business contract each upgraded and rolled back?
6. How will you prove equivalent behavior across bindings, rather than merely showing that each can return \`200\`?

If these questions have no answers, introducing A2A merely turns an unclear system boundary into a larger network boundary.

## Self-check

1. Why is “exposing a retrieval tool through MCP” not the same contract as “delegating to a research Agent through A2A”?
2. Must two sub-Agents in the same process use A2A? Why or why not?
3. Can an Agent Card prove a Remote Agent's actual capabilities? What evidence is still missing?

## References

- [A2A Protocol home page](https://a2a-protocol.org/latest/)
- [A2A Protocol 1.0.0 specification](https://a2a-protocol.org/latest/specification/)
- [A2A and MCP](https://a2a-protocol.org/latest/topics/a2a-and-mcp/)
