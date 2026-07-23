---
title: "Routing, Parallelism, and Joining"
aliases:
  - Routing and Parallelization
  - Routing, Parallelism, and Joining
tags:
  - ai-agent
  - workflow
  - routing
source_checked: 2026-07-14
lang: en
translation_key: Agentic Design Patterns/00-初学者路线/02-路由并行与汇聚.md
translation_source_hash: d3a7b789d7b7d9e221249b15465dcc079f58375247cabb53488179e309449a83
translation_route: zh-CN/Agentic-Design-Patterns/00-初学者路线/02-路由并行与汇聚
translation_default_route: zh-CN/Agentic-Design-Patterns/00-初学者路线/02-路由并行与汇聚
---

# Routing, Parallelism, and Joining

## Goal

You will learn five foundational structures—prompt chaining, gating, routing, parallel fan-out, and joining—and define a schema for every intermediate artifact. You will also be able to identify which steps must not run in parallel.

## Write the workflow as data dependencies first

A workflow is more than “call a few functions in sequence.” Every node needs an input contract, output contract, and failure semantics; edges represent dependencies or conditions. A common shape is:

```text
Input -> Parse -> Gate -> Route ─┬─ Branch A ─┐
                                 ├─ Branch B ─┼─ Join -> Accept
                                 └─ Branch C ─┘
```

- A **chain** uses the previous step's output as the next step's input.
- A **gate** uses rules to decide whether an intermediate result is acceptable; otherwise it stops or repairs.
- **Routing** selects one or more following paths.
- **Fan-out** dispatches independent work.
- A **join / reduce** checks branch completeness, handles conflicts, and determines the overall state.

Anthropic introduces prompt chaining, routing, parallelization, orchestrator-workers, and evaluator-optimizer as composable patterns. They are design vocabulary, not a requirement to bind to one provider API.

## Routing: rules first; fail closed for unknown values

Prefer explainable rules for deterministic traits such as file type, amount threshold, permission level, or missing fields. Use model classification only when a semantic boundary is ambiguous, and require a constrained label:

```json
{
  "label": "billing",
  "evidence_ids": ["message-17"],
  "needs_clarification": false
}
```

Read the fields this way:

- `label` must be checked against the application-defined routing allowlist before selecting a branch.
- `evidence_ids` connects the classification to reviewable source messages or fragments.
- `needs_clarification` explicitly represents insufficient information. When it is `true`, do not default to a high-privilege path.

Never concatenate free text directly into a function name. After parsing, verify that the label is allowed, cited evidence exists, and the business threshold is met. `unknown` should go to clarification or a human branch, never to the tool with the highest privilege.

Routing tests should cover at least:

- every legal branch;
- empty input and missing fields;
- unknown labels;
- extra fields, invalid JSON, or contradictory model output;
- both sides of threshold values; and
- adversarial content trying to change routing rules.

## Parallelism: only dependency-free work may run together

Two tasks may run in parallel only when all of the following hold:

1. Neither reads a result the other has not yet produced.
2. They do not compete to mutate the same state.
3. Failure and retry cannot repeat an irreversible side effect.
4. The join layer knows which branches are expected.

“Entity extraction” and “sensitive-data scanning” can run in parallel against the same immutable document copy. “Retrieve evidence” and “write a conclusion from that evidence” cannot. Threads or async can improve waiting-bound work; they do not automatically speed CPU-bound work or repair a wrong data dependency.

Parallel workers should return their own results rather than writing a shared dictionary. The main thread updates state once after joining. That makes replay order and tests more stable.

## Joining: more than concatenation

A robust joiner answers at least these questions:

- Did every expected branch return?
- Which input and execution version produced each result?
- How are timeout, cancellation, and partial success represented?
- Do rules, a model, or a human resolve conflicts?
- May a degraded result proceed?

A suitable intermediate structure is:

```json
{
  "branch": "risk_scan",
  "status": "ok",
  "input_digest": "sha256:...",
  "claims": [{"text": "...", "evidence_id": "chunk-03"}],
  "latency_ms": 128
}
```

- `branch` identifies the expected worker branch so the joiner can check completeness.
- `status` is a stable result category; success and retryability must not be inferred from free text.
- `input_digest` binds the branch to the input version it processed, preventing an old result from entering a new task.
- `claims` keeps assertions with evidence IDs, preserving traceability after joining.
- `latency_ms` is observability data for locating slow branches and setting time budgets.

“Looks fine” is an unsuitable intermediate structure: a joiner cannot determine completeness, origin, or retryability from it.

## Map–Reduce and orchestrator–workers

Long-document processing can map chunks to several workers, each returning `{chunk_id, claims, citations}`, then reduce by deduplicating, checking citations, and summarizing. The important design work is input partitioning, result schema, and join rules—not how many Agents are used.

When the number of subtasks cannot be known in advance, an orchestrator can create worker tasks dynamically. This is more flexible than fixed parallelism, and adds decomposition mistakes, duplicate tasks, uncontrolled budget, and missed joins. First prove on fixed samples that dynamic decomposition improves results; then introduce it.

## Complete example: customer-support entry point

Requirement: account problems may use automatic read-only queries; refund requests may only produce recommendations and wait for approval; unclassifiable requests ask the user to clarify.

1. `validate_input` checks ticket structure.
2. `route_intent` returns only `account | refund | unknown`.
3. The account branch runs identity-status lookup and service-health checks in parallel.
4. The refund branch runs policy lookup and a read-only order query in parallel.
5. The join requires both checks; a permission denial must never be retried with higher privilege.
6. The unknown branch calls no business tool and only asks a clarifying question.

Acceptance must inspect more than reply text: also inspect called tools, parameter ranges, and whether any forbidden write occurred.

## Common mistakes and troubleshooting

- **Routing-label drift**: define enums and schemas centrally; do not duplicate strings in nodes.
- **Parallel branches write shared state**: use worker return values and merge once in the join.
- **Wait only for the first result**: if the business requires complete evidence, verify every expected branch.
- **Treat timeout as failure**: timeout means an unknown outcome; inspect the action receipt before retrying.
- **Lose sources in reduce**: carry source IDs with intermediate results and preserve mappings in final output.
- **Treat model confidence as a probability guarantee**: confidence is only a signal; calibration data must prove usefulness.

## Exercise

Design a “upload a contract and generate a risk summary” flow:

1. Draw parsing, format gating, clause classification, parallel risk scans, and joining.
2. Write an input/output schema for every node.
3. Design responses for a timed-out branch, a branch with invalid fields, and two branches with conflicting conclusions.
4. Write eight routing tests, including at least two unknown or adversarial samples.

## Mastery check

- [ ] I can distinguish chains, gates, routing, fan-out, and joins.
- [ ] I can prove that two steps lack a data dependency before running them in parallel.
- [ ] I can define a safe default for unknown routing values.
- [ ] I can make the join layer check completeness, origin, conflict, and partial failure.
- [ ] I can explain why a worker should not directly mutate shared state.

## Next

Continue with [[agentic-design-patterns/beginner-route/03-reflection-planning-and-stopping-conditions|Reflection, Planning, and Stopping Conditions]] to constrain dynamic iteration within testable boundaries.

## References

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) — checked 2026-07-14.
- [[agentic-design-patterns/upstream-references/section-01/reference-02-309c9286|Reference layer: Routing]]
- [[agentic-design-patterns/upstream-references/section-01/reference-03-3c744b3e|Reference layer: Parallelization]]
