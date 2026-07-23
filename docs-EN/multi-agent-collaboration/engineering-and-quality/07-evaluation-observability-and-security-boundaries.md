---
title: "Evaluation, Observability, and Security Boundaries"
tags:
  - multi-agent
  - evaluation
  - observability
  - security
aliases:
  - Multi-Agent Evaluation
  - Multi-Agent Observability
source_checked: 2026-07-22
lang: en
translation_key: 多Agent协作/02-工程与质量/07-评测、可观测性与安全边界.md
translation_source_hash: 5d59bd4e5d844caf31ce61c4d812949460bae3fe616c23cad71ae2de2d5f49b3
translation_route: zh-CN/多Agent协作/02-工程与质量/07-评测、可观测性与安全边界
translation_default_route: zh-CN/多Agent协作/02-工程与质量/07-评测、可观测性与安全边界
---

# Evaluation, Observability, and Security Boundaries

## Goal

Establish evaluation and tracing from one task to the system level. Identify permission amplification, prompt-injection propagation, and sensitive-data spread introduced by a delegation chain.

## Compare a baseline first

Compare at least three designs:

1. One model call or one agent;
2. A fixed workflow;
3. The candidate multi-agent topology.

Use the same test set, model and tool conditions, and success criteria. Express collaboration gain as:

```text
Incremental success rate = multi-agent success rate - best simpler-baseline success rate
Cost per incremental gain = added cost / additional successful tasks
```

When incremental success is near zero, there is no reason to use the more complex system.

## Layered metrics

### Outcome

- End-to-end task-success rate;
- required-evidence coverage;
- factual or operational error rate;
- human acceptance and rework rate.

### Collaboration

- routing and delegation accuracy;
- subtask acceptance rate;
- duplicate-work ratio;
- conflict rate and recovery-success rate;
- same-key/different-digest conflict rate, time spent in `needs_review`, and human-reconciliation conclusion;
- invalid messages and no-progress rounds.

### Resources

- total model and tool calls;
- tokens and cost;
- P50/P95 end-to-end and critical-path latency;
- parallel utilization and approval-wait time.

### Security

- unauthorized-tool-call rate;
- malicious-message propagation rate across agents;
- sensitive-field exposure rate;
- approval bypass, stopping failure, and missing-audit rate.

## Minimal tracing model

Each user request gets a `trace_id`. Every agent, model, tool, handoff, and approval gets a span. A span records its parent relationship, `task_id`, attempt, start and end time, input/output summary or hash, state, error class, budget change, and policy decision.

As of 2026-07-22, the OpenAI Agents SDK tracing documentation lists spans for model generation, tools, handoffs, guardrails, and related work. It also warns that tracing can contain sensitive input and output. In any product, decide whether to record raw content from data classification; prefer structured metadata, hashes, and redacted summaries by default.

## Debugging method

From the failed terminal state, walk backward through `task_id` and parent spans:

1. Find the earliest state transition that diverged from expectation.
2. Inspect the input version and evidence at that point.
3. Inspect routing and permission decisions.
4. Look for duplicates or late messages.
5. Check whether retries hid the root cause.

Do not read only the final chat. Multi-agent failures commonly occur in message trimming, incorrect routing, shared-state overwrite, or manager aggregation rather than a particular model “answering badly.”

## Security boundaries

- Give each agent least-privilege tools and data; a delegation must not inherit all manager permissions.
- Agent messages and tool results are untrusted input; after structural validation, apply policy checks again.
- Do not pass hidden internal reasoning as authorization evidence.
- Require approval for high-risk tools at the execution boundary rather than only telling an upstream prompt to “be careful.”
- Minimize material sent to an external agent by task, and record data destination and retention period.
- Preserve sources and uncertainty in an aggregate so “several agents agree” is not mistaken for fact.

NIST AI RMF and the Generative AI Profile provide the Govern, Map, Measure, Manage risk-management framework. They do not prescribe multi-agent code, but they are useful for organizing responsibility, measurement, monitoring, and treatment.

## Test matrix

Cover at least normal completion, no suitable specialist, incorrect routing, one specialist timeout, duplicate message, state conflict, budget exhaustion, malicious sub-agent output, approval rejection, cancellation, and recovery without repeated side effect.

## Exercise and self-check

Design ten cases for a three-agent system, at least four of them failure or attack paths. Do two agents reaching the same conclusion count as two pieces of evidence? Why not when they used the same input or one copied the other?

## Next step

Enter [[multi-agent-collaboration/project-and-self-check/08-offline-collaboration-simulator-project|Offline Collaboration Simulator Project]].

## References

- [OpenAI Agents SDK: Tracing](https://openai.github.io/openai-agents-python/tracing/) — accessed 2026-07-22.
- [NIST AI RMF 1.0](https://www.nist.gov/itl/ai-risk-management-framework) — accessed 2026-07-22.
- [NIST AI RMF Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence) — accessed 2026-07-22.
