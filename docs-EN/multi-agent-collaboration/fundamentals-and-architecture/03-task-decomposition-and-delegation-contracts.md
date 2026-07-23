---
title: "Task Decomposition and Delegation Contracts"
tags:
  - multi-agent
  - delegation
  - task-contract
aliases:
  - Agent Delegation Contract
  - Multi-Agent Task Decomposition
source_checked: 2026-07-22
lang: en
translation_key: 多Agent协作/01-基础与架构/03-任务分解与委派合同.md
translation_source_hash: 32ef94b140ea89565b714b6e495a8cdddbd8ee2f8c55c99ca99bad158d4e8cf0
translation_route: zh-CN/多Agent协作/01-基础与架构/03-任务分解与委派合同
translation_default_route: zh-CN/多Agent协作/01-基础与架构/03-任务分解与委派合同
---

# Task Decomposition and Delegation Contracts

## Goal

Rewrite “help me with one part” as an independent, minimal, acceptable subtask. Understand that delegation does not transfer final responsibility.

## Decompose backward from completion evidence

Write the completion evidence for the overall task before forming a work-breakdown structure:

1. What is the overall output?
2. Which evidence proves that it is correct?
3. Which artifacts can different roles produce independently?
4. Which dependencies must finish first?
5. Which steps share a mutable resource and therefore cannot run in parallel?

Good subtasks have high cohesion and low coupling: internal steps focus on one result and external connections use explicit inputs and outputs. Splitting by “what a role likes doing” creates overlap; splitting by an acceptable artifact is more stable.

## Minimal task contract

```json
{
  "task_id": "T-20",
  "delegation_id": "D-20-1",
  "owner": "evidence_agent",
  "goal": "Produce three sourced fact records",
  "inputs": ["question", "approved_sources"],
  "dependencies": ["T-10"],
  "output_schema": "evidence-list-v1",
  "permissions": ["read:web:allowlist"],
  "grant_ref": "grant:research-read-v3",
  "tenant_id": "workspace-demo",
  "budget": {"max_steps": 4, "deadline_s": 30},
  "acceptance": [
    "Every fact contains an accessible URL",
    "Every fact agrees with its source"
  ],
  "on_failure": "return_structured_error"
}
```

The contract must be independent of a natural-language role description. The runtime validates fields, permissions, and budget instead of trusting an agent to comply.

`owner` identifies responsibility for the task; it is not an identity that can access a resource. `permissions` are not copyable credentials. In production, a contract also refers to the issuer, runtime principal, tenant or trust domain, smallest permitted action and resource scope, start and end time, policy version, and the approval decision and input summary bound to high-risk action. The executing tool still makes a current decision from the authenticated principal and resource policy; it must not allow an action merely because an upstream agent said “authorized.” See [[multi-agent-collaboration/engineering-and-quality/08-identity-authorization-and-cross-boundary-trust|Identity, Authorization, and Cross-Boundary Trust]] for the cross-boundary contract and offline checks.

## What to pass during delegation

Pass only the smallest package needed to complete the task:

- goal and non-goals;
- verified inputs and sources;
- output structure and example;
- tool and data permissions;
- budget, deadline, and retry policy;
- acceptance conditions;
- sensitive-field handling rules;
- upstream trace ID and task ID.

Do not forward the whole chat history by default. Irrelevant history increases cost and can propagate user data or malicious tool text to more agents. If a summary is necessary, retain source pointers and uncertainty rather than treating the summary as primary evidence.

## Dependencies and parallelism

Express order with a directed acyclic graph (DAG). A task becomes ready only when it has no unfinished dependency and does not contend for the same exclusive resource. The concurrency limit must also respect global budget and service rate limits.

If A and B both write one draft, they are not truly independent. Let A and B produce suggestions and give one writer C ownership of the merge, or partition ownership by file.

## Acceptance and rework

An acceptor checks structure, evidence, and invariants; it does not redo the producer's work. Return a stable failure class:

- `invalid_input` — the upstream contract is incomplete; do not retry.
- `transient_failure` — a temporary fault; retry with bounded backoff.
- `quality_failure` — result does not meet the bar; rework may receive feedback.
- `policy_denied` — a permission or safety policy denied the action; do not evade it by switching agents.
- `budget_exhausted` — stop and report partial progress.

## Common mistakes

- **Writing a delegation as a new prompt** — task ID, structure, permissions, and acceptance are absent.
- **Unbounded recursive delegation** — every agent can create another agent, making budget uncontrollable.
- **Treating output as fact** — a downstream agent trusts upstream prose directly. Validate structure and sources.
- **Multiple owners** — nobody owns the conflict. Assign exactly one write owner to every mutable artifact.

## Exercise and self-check

Split “research three vector databases and recommend one” into at most four subtasks, with dependencies and acceptance. Can vendor-material collection run in parallel? Who writes the final trade-off table? If two experts disagree, does the contract define evidence format and an arbitrator?

## Next step

Continue with [[multi-agent-collaboration/engineering-and-quality/08-identity-authorization-and-cross-boundary-trust|Identity, Authorization, and Cross-Boundary Trust]], then proceed to messages and shared state.

## References

- [OpenAI Agents SDK: Agent orchestration](https://openai.github.io/openai-agents-python/multi_agent/) — accessed 2026-07-22.
- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/) — accessed 2026-07-22.
