---
title: "Agent Environments, State, and Repeated Runs"
aliases:
  - Agent Benchmark Environments
  - Agent Run Protocol
tags:
  - benchmark
  - agent
  - run-protocol
source_checked: 2026-07-21
content_origin: original
content_status: validated
source_baseline: "Anthropic and OpenAI primary Agent-evaluation materials plus
  original papers for SWE-bench, WebArena, OSWorld, and tau-bench through
  2026-07-21"
lang: en
translation_key: Benchmark设计/02-方法与质量/07-Agent环境状态与多次运行.md
translation_source_hash: fb51ee5ded0f0dda15b8ed4bc1b562a232cb43cc67c7a76eb1151ec2ea3666f6
translation_route: zh-CN/Benchmark设计/02-方法与质量/07-Agent环境状态与多次运行
translation_default_route: zh-CN/Benchmark设计/02-方法与质量/07-Agent环境状态与多次运行
---

# Agent Environments, State, and Repeated Runs

## Goal

Extend a text-question Benchmark into a truly reproducible Agent task: freeze environment and tools, declare initial state, permitted actions, and expected final state, isolate side effects, and use repeated trials to present a stochastic system's success rate and stability.

## Intuition

For a question-answering model, input is commonly text and output is text. An Agent reads and writes the external world. It can call a wrong tool, duplicate a payment, contaminate the next database run, or say “completed” while the environment never changed. The measurement unit for an Agent Benchmark is not the final sentence:

> Run one complete task under a determined initial state, permissions, tools, and budget, then verify final state, action side effects, and operational cost.

## Terms introduced here

- **environment:** external systems an Agent can observe or change, such as directory, database, website, or simulated order service.
- **initial state:** a verifiable environment snapshot before each trial starts.
- **final state / outcome:** the state that actually exists when task ends, not what the Agent self-reports.
- **side effect:** an additional state change from execution. It can be permitted or prohibited, such as duplicate write or unauthorized read.
- **harness:** code that performs setup, starts the system, supplies tools, imposes budget, records trace, grades, and resets.
- **trial:** one independent execution of the same system under one case contract.
- **reset:** restore environment to the known initial state for the case and remove caches, sessions, and temporary data.

## Minimum contract for an Agent case

| Field | Question it answers | Example |
| --- | --- | --- |
| Task ID / family ID | What is this task, and which variants share its source? | `test-safety` / `refund-family` |
| Environment ID | Which reconstructable environment runs it? | `offline-order-fixture-v1` |
| Initial state | How is clean state verified before start? | Order exists and is not refunded |
| Instruction | What does the user ask for? | Look up status and request an immediate refund |
| Tool schema and permissions | What can it observe or change? | Read-only `order_lookup` |
| Success outcome | What final state counts as success? | Return status and refuse write |
| Forbidden side effects | What must not happen even if task completes? | `refund_order` |
| Budgets | Maximum steps, time, retries, and cost? | 8 steps, 30 seconds, 0 retries |
| Trials | How many independent repetitions? | 3 teaching trials |
| Teardown/reset | How are cleanup and verification done? | Restore fixture and check hash |

A task template saves setup and grader together. A natural-language instruction alone leaves later readers unable to know whether an order was already refunded, a tool return was fixed, or a write really occurred.

## Setup, run, grade, and reset

1. **setup:** create environment from a versioned snapshot; check initial state and tool version. A failure is a harness error, not a task handed to the Agent.
2. **run:** start a fresh session with the same tool definition and permissions; record every action, state, latency, and cost.
3. **stop:** stop under a predeclared rule at success, explicit failure, maximum steps, timeout, or unrecoverable error.
4. **grade:** verify final state first, then prohibited side effects, tool permissions, and resource constraints. Text explanation is supporting evidence only.
5. **reset:** destroy or restore environment and verify equality with initial snapshot. If reset fails, pause later trials; never continue through contamination.

> [!warning] Unknown is not a missing value
> If a run log is corrupted, a grader cannot read state, or reset fails, record it explicitly as `Unknown` or harness error. Under frozen rules, it enters the denominator or triggers a rerun review. Deleting it makes a failing system look better.

## Repeated trials and minimal statistical intuition

Even with temperature 0, service, tools, network, concurrency, and implementation details can introduce nondeterminism. If one case runs `R` times, giving success `x_r=1` and failure 0, empirical success rate is:

$$
\hat p=\frac{1}{R}\sum_{r=1}^{R}x_r
$$

For example, `[1, 1, 0]` has empirical success rate $2/3$; it must not be presented as success by selecting its best run. Report:

- trial success rate per task;
- stability across trials;
- overall and slice task success rate;
- count of timeout, error, and Unknown;
- mean and p95 latency, cost, or tool calls.

Trials are not magic population expansion. Repeated outcomes for one case are correlated; do not present 15 trials as 15 independent tasks. Preserve task-level comparison and trial-level variation separately.

`pass@k` means at least one success in `k` attempts, appropriate only when a product really permits multiple independent attempts. `pass^k` means all `k` attempts succeed, appropriate when consecutive reliability is required. Deriving `1-(1-p)^k` or `p^k` from one-run success probability `p` requires identically distributed independent trials. Shared cache, environment state, retry adaptation, or vendor outage can invalidate the formula. Report these measures from actual trials and real retry strategy when possible, along with cost per attempt, total budget, and **expected cost per successful result**. A high `pass@k` dependent on expensive retries is not one-run reliability.

## Comparable runs and incomparable conditions

| Change | Default treatment | Reason |
| --- | --- | --- |
| Same protocol; only system implementation differs | Comparable | Target variable is clear |
| Candidate has one more budget step or retry | Not directly rankable | Resource condition changed |
| Tool schema or permission differs | Cannot attribute directly to model capability | SUT boundary changed |
| Environment snapshot differs | Incomparable | Initial difficulty and data can differ |
| Same protocol, but stochastic trials differ | Retain all and use paired/repeated analysis | This is system variation |
| Continue after reset failure | Batch is invalid | Trials are no longer independent and initial state is unknown |

Architecture differences can truly need different tools or budgets. In that case, open a separate track or change the claim to “utility-cost comparison of complete systems under their own resource constraints,” but do not continue to claim a same-resource capability rank.

## Design lessons from original Benchmarks

- SWE-bench supplies a code repository and issue, then executes tests through a reproducible containerized harness. It shows why code patches must be verified in fixed repository state and test environment.
- WebArena builds interactive web environments and scores functional task completion. Web Agents therefore need real state, not only final natural language.
- The OSWorld paper explicitly includes initial-state setup and execution-based evaluation, directly matching “restore environment first, then verify final state.”
- tau-bench studies tool–Agent–user interaction and emphasizes multi-turn tool tasks and repeated-run reliability. This course adopts its design questions only and does not cite leaderboard ranks that change.

These examples come from original sources; no team is required to copy their exact tasks, containers, or metrics.

## Common mistakes and diagnostics

- **Judge only whether the final sentence contains “completed”:** query final database, file, or page state instead.
- **Allow candidate more steps:** either unify budget or establish a separate resource track.
- **Share session or cache across trials:** create a fresh session and verify reset every time.
- **Retry after timeout until success and retain only that run:** retain each result under predeclared retry rule.
- **Safety of actions equals task success:** they are independent; refusing every action can be safe but useless.
- **Delete a case because grader crashes:** record Unknown/harness error, repair, then rerun the complete comparable batch.

## Exercises

1. For “summarize a CSV into a report,” write initial state, final state, allowed files, prohibited side effects, and reset steps.
2. Design a comparison where one candidate gets one more retry. Write both an incomparable conclusion and an acceptable separate-track name.
3. For `[1,1,0]` and `[1,0,1]` trial results, state success rate, stability interpretation, and missing evidence.

## Self-check

1. Why is an Agent saying “success” insufficient for grading? Real task result is in external environment and may have undeclared side effects.
2. Why is reset part of Benchmark protocol instead of cleanup detail? It determines the next trial's initial condition and therefore comparability.
3. Can three trials prove production success rate? No. They show finite repeated results for this case under this protocol.
4. If tool permissions differ and candidate scores higher, can the model be called stronger? No. At most compare different complete systems while disclosing resource differences.

## Summary and next step

An Agent Benchmark needs reconstructable environment, state verification, side-effect constraints, budget, and independent repetition. Continue to [[benchmark-design/project-and-self-check/08-build-a-maintainable-benchmark|Project: Build a Maintainable Benchmark]] to verify why protocol mismatch must be incomparable before any rank.

## References

All sources below were retrieved or checked on 2026-07-21 and are cited for design methods only, not dynamic leaderboard results:

- [SWE-bench official repository and harness](https://github.com/SWE-bench/SWE-bench)
- [SWE-bench original paper](https://arxiv.org/abs/2310.06770)
- [WebArena original paper](https://arxiv.org/abs/2307.13854)
- [OSWorld original paper](https://arxiv.org/abs/2404.07972)
- [tau-bench original paper](https://arxiv.org/abs/2406.12045)
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — published 2026-01-09; tasks, trials, isolation, `pass@k`, and `pass^k`.
- [OpenAI: A shared playbook for trustworthy third party evaluations](https://openai.com/index/trustworthy-third-party-evaluations-foundations/) — published 2026-05-29; system budgets and cost per successful task.
