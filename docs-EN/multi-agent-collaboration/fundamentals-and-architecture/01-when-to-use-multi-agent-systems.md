---
title: "When to Use Multi-Agent Systems"
tags:
  - multi-agent
  - architecture
  - decision
aliases:
  - Multi-Agent Decision
  - When Not to Use Multi-Agent Systems
source_checked: 2026-07-14
lang: en
translation_key: 多Agent协作/01-基础与架构/01-何时使用多Agent.md
translation_source_hash: a3411867737b4730d15b687c68933948b9894937ed1b63b7f247f7035903f183
translation_route: zh-CN/多Agent协作/01-基础与架构/01-何时使用多Agent
translation_default_route: zh-CN/多Agent协作/01-基础与架构/01-何时使用多Agent
---

# When to Use Multi-Agent Systems

## Goal

Learn to prove that the added complexity is necessary. The right question is not “can we split this into several roles?” but “does splitting produce repeatable gains in quality, context isolation, parallel speed, or permission isolation?”

## Start from the simplest baseline

Try four levels in order:

1. One model call — input is clear and one response completes the work.
2. One agent plus tools — steps are uncertain, but one control loop is enough.
3. A deterministic workflow — code can express the steps, dependencies, and branches.
4. Multiple agents — distinct expertise, isolated contexts or permissions, or genuinely independent open tasks exist.

“The task is complicated” is not enough. LangGraph's multi-agent guidance also notes that one agent with appropriate tools and prompts can often solve tasks that appear complex. Additional agents add model calls, message translation, error propagation, state synchronization, and debugging surface.

## Signals that justify a split

| Signal | Verifiable question | Possible topology |
| --- | --- | --- |
| Expertise conflict | Can one prompt not reliably satisfy two sets of rules at once? | Manager calls specialists |
| Context isolation | Does mixing material for different subtasks cause material interference? | Specialist sub-agents |
| Permission isolation | Must a read-only researcher be separated from a write-capable executor? | Approval pipeline |
| Genuine parallelism | Are subtasks dependency-free so the critical path can shrink? | Fan-out and aggregation |
| Organizational boundary | Does an external agent expose capability but not internal tools? | Peer protocol |
| Independent review | Does a high-risk result need independent evidence or an opposing review? | Generate and review |

Tie every signal to a metric. “Parallel is faster” means comparing end-to-end P50 and P95 latency. “Specialists are more accurate” means comparing task-success rate over the same test set, not showing one successful anecdote.

## Cases that do not warrant multiple agents

- Stable code rules can solve the task, yet every step is wrapped as an agent.
- Several roles read and write one file or record without one owner and a conflict protocol.
- Every agent uses the same model, context, and permissions and differs only by name.
- A subtask strongly depends on the previous one, so apparent parallelism merely waits.
- No budget, stopping condition, or human takeover is defined.
- Agents are allowed to critique one another indefinitely “for more discussion,” amplifying cost and correlated mistakes.

## A quantitative decision table

Score a candidate design, but do not treat the score as truth:

| Dimension | One agent | Multiple agents | Evidence |
| --- | ---: | ---: | --- |
| Success rate | 0.78 | 0.82 | Fixed set of 100 cases |
| Mean call count | 3.1 | 8.7 | Trace records |
| P95 latency | 11 s | 16 s | End-to-end timing |
| High-risk overreach | 0 | 0 | Red-team cases |

If success rises only slightly while cost and latency double, optimize the one-agent baseline first. The value of multiple agents is **constrained system benefit**, not role count.

## Practice

Choose one real task and write:

- the simplest viable baseline;
- the one primary metric expected to improve after splitting;
- the new failure modes;
- the experimental outcome that would make you abandon the multi-agent design.

## Common mistakes and debugging

- **Treating persona as capability** — Different role names do not create different tools, data, or acceptance criteria. Check whether the capability contract actually differs.
- **Measuring only the final answer** — After adding tracing, inspect duplicate work, message volume, recovery, and critical path.
- **Choosing the framework before defining the problem** — Draw data and control flow first, then choose a framework.

## Self-check

1. Why are three agents that sequentially execute fixed steps usually a workflow instead?
2. Which two isolation types most strongly justify a split: context, permission, organization, or “speaking style”?
3. If multi-agent accuracy rises 2% and cost rises 180%, what decision information is still missing?

## Next step

Continue with [[multi-agent-collaboration/fundamentals-and-architecture/02-roles-topologies-and-responsibility-boundaries|Roles, Topologies, and Responsibility Boundaries]].

## References

- [LangChain documentation: Multi-agent](https://docs.langchain.com/oss/python/langchain/multi-agent/index) — accessed 2026-07-14.
- [OpenAI Agents SDK: Agent orchestration](https://openai.github.io/openai-agents-python/multi_agent/) — accessed 2026-07-14.
