---
title: "How Agents Complete Tasks"
tags:
  - ai-agent-engineer
  - ai-foundations
  - agent
aliases:
  - Agent system intuition
  - Introduction to Agents
content_origin: original
content_status: dynamic
source_checked: 2026-07-22
lang: en
translation_key: AI基础认知/01-概念地图/06-Agent如何完成任务.md
translation_source_hash: 30c8443faea3c9abc027226d4c8b17a8253c144b5fcb3633b47ab151e45f5d96
translation_route: zh-CN/AI基础认知/01-概念地图/06-Agent如何完成任务
translation_default_route: zh-CN/AI基础认知/01-概念地图/06-Agent如何完成任务
---

# How Agents Complete Tasks

## Learning objective

You will understand that an Agent is not “a longer prompt,” but a controlled system operating around a goal. After this lesson, you can draw an Agent loop, distinguish a workflow from an Agent, and identify tool permissions, state, and stop conditions.

## A minimum Agent model

In engineering, this decomposition is enough to begin working without debating one unique definition:

```text
Agent = goal + current state + decision mechanism + available tools + control policy + feedback
```

- **Goal:** what success means, such as “produce a meeting action-item draft that a human can send.”
- **State:** known task information, completed steps, tool results, and errors.
- **Decision mechanism:** chooses the next step from the goal and current state; modern applications often use an LLM, but it is not the only option.
- **Tools:** external capabilities such as search, database queries, file reads, and sending messages.
- **Control policy:** permissions, budgets, retries, approvals, and stop conditions.
- **Feedback:** tool return values, environmental changes, user clarification, or evaluation results.

## The observe–decide–act loop

A controlled loop can be written as:

```text
Receive goal
  ↓
Observe current state and available information
  ↓
Choose next step ──insufficient information──→ Request clarification
  ↓
Generate structured tool arguments
  ↓ Authorization and argument validation
Execute tool
  ↓
Read result and update state
  ↓
Goal reached / approval required / stop condition triggered
```

The ReAct paper demonstrates one research approach in which a language model alternates reasoning and actions, then reads environmental feedback. **Stable fact:** this pattern of “model proposes an action—environment returns an observation” is representative. **Engineering recommendation:** production systems should not expose or rely on unconstrained free-text reasoning; record key decisions, tool arguments, evidence, and results in auditable structures instead.

## Workflow or Agent?

| Situation | A fixed workflow is more suitable | An Agent is more likely to add value |
| --- | --- | --- |
| Steps | Order is known and branches are limited | The next step depends on open-environment feedback |
| Input | Format is stable | Information is incomplete and expression varies |
| Risk | Rules can enumerate it | Model judgment is needed, but boundaries and approvals can be set |
| Testing | Every path can be enumerated | A task set must estimate success rates and inspect traces |
| Cost | Low latency and low variation are required | The task benefit justifies repeated calls |

Real systems are often hybrids: a fixed workflow owns the broad frame, and an Agent selects an action at one low-risk point. This is usually easier to validate than letting every step decide autonomously.

## A tool is a contract, not a one-line description

Suppose an Agent has `create_ticket(title, severity, evidence)`. Define at least:

- Field types, lengths, required fields, and allowed values.
- Caller identity and least privilege.
- Which arguments come from trusted data and which from the model.
- How timeouts, failures, duplicate calls, and partial success are handled.
- Whether the call can be reversed and whether it requires human confirmation.
- How return values are validated and when the system must not continue.

Model-generated valid JSON proves only that the format passed; it does not prove that creating the ticket is authorized for the business case. **Authorization must be decided by the system execution layer, not self-declared by the model.**

> [!warning] A model is not an authorization principal
> For tools that create external side effects, the execution layer should bind, validate, and record facts from trusted identity and authorization systems: who initiated the request, which service identity is used, which user or tenant is represented, which action and object are allowed, and when authorization or approval expires. A model may propose an action and business arguments, but cannot generate, expand, or replace those authorization facts. Shared backend credentials do not bypass object-level authorization.

## State, memory, and context are not the same term

- **Context:** input visible to this model call.
- **Task state:** structured facts saved by the system, such as `ticket_id`, step state, and approval results.
- **Short-term memory:** the current task’s history summary or working draft.
- **Long-term memory:** information retained across tasks, such as user preferences; it needs provenance, updates, deletion, and access control.

Putting all chat history directly into context is not reliable memory. The application should maintain structured state, and tools or rules should validate critical fields.

## Three safety boundaries

1. **Separate reads from writes:** allow read-only queries first; authorize writing, sending, deletion, and payment tools separately.
2. **Approval points:** before high-impact actions, show the action, object, rationale, and visible consequences for human confirmation.
3. **Stop conditions:** stop and hand off to a human when maximum steps, retries, time or cost budgets, repeated state, or risk rules are reached.

Stopping is not failure. Exiting safely in uncertain situations is often an important Agent capability.

> [!info] Current engineering discussion of tool classification
> A 2025 NIST AISIC workshop summary proposed describing Agent tools along dimensions such as function, access method, risk, reliability, modality, observability, and autonomy, with particular attention to read/write and trusted/untrusted environments. It is a public workshop summary rather than a formal standard, but can serve as a permission-review checklist. NIST material on software-Agent identity and authority from 2026 is still a concept project document and should not be described as a settled standard.

## Exercise: design a read-only troubleshooting Agent

Scenario: a user reports that a website is unavailable. The Agent may read service status, recent alerts, and public runbooks, but may not restart a service.

Write:

1. The goal and explicit non-goals.
2. Inputs, outputs, and errors for three read-only tools.
3. What missing information requires asking the user.
4. A maximum step count and stop conditions.
5. How output distinguishes observed facts from inferences.
6. How a restart recommendation is handed to an authorized person for approval.

A passing answer needs no framework code, but another engineer must be able to implement and test from it.

## Self-check

1. Why does “can call a tool” not mean “may perform any action”?
2. Why should Agent state not exist only in chat text?
3. Why should fixed-step invoice processing usually start with a workflow?
4. Give two normal stop conditions and two abnormal ones.

Suggested answer points: tool capability is also constrained by identity, arguments, business rules, and approval; structured state is easier to validate, recover, and audit; a fixed path is more stable as a workflow; normal stops include goal completion and user cancellation, while abnormal stops include loops, budget exhaustion, persistent tool failure, or a risk rule.

## Related concepts

- [[tool-calling-function-calling/00-index|Tool Calling]] provides the controlled interface from model output to tool arguments, and [[mcp/00-index|MCP]] provides an open protocol boundary between clients and servers.
- [[agent-core/00-index|Agent Core]] goes deeper into state, loops, termination, memory, and checkpoints; [[agentic-design-patterns/00-index|Agentic Design Patterns]] compares reusable control patterns.
- When steps can be enumerated in advance, prefer [[workflow-automation/00-index|Workflow Automation]] rather than using autonomy in place of a clear process.

## Summary and next step

An Agent’s core is not “the more autonomy, the better,” but using a controlled loop to complete tasks under uncertainty. Next, [[ai-foundations/02-engineering-decisions/07-capability-boundaries-and-failure-modes|Capability Boundaries and Failure Modes]] turns common problems into executable tests.

## References

Accessed **2026-07-22**.

- Yao et al., [ReAct](https://arxiv.org/abs/2210.03629)
- [NIST: Lessons Learned from the Consortium—Tool Use in Agent Systems](https://www.nist.gov/news-events/news/2025/08/lessons-learned-consortium-tool-use-agent-systems) (workshop summary, not a standard)
- [NIST NCCoE: Identity and Authority of Software Agents concept project](https://www.nist.gov/news-events/news/2026/02/new-concept-paper-identity-and-authority-software-agents) (concept document, not a final specification; used here for identity, authorization, and audit boundaries)
- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- [NIST AI RMF Playbook: Map](https://airc.nist.gov/airmf-resources/playbook/map/)
