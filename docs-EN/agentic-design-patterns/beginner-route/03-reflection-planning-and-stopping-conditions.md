---
title: "Reflection, Planning, and Stopping Conditions"
aliases:
  - Reflection Planning Termination
  - Controlled Agent Loops
tags:
  - ai-agent
  - reflection
  - planning
source_checked: 2026-07-14
lang: en
translation_key: Agentic Design Patterns/00-初学者路线/03-反思规划与停止条件.md
translation_source_hash: b5b5abdab8506463a228a209bbff6acd2cbf9e33008d39cc25321d2252862d08
translation_route: zh-CN/Agentic-Design-Patterns/00-初学者路线/03-反思规划与停止条件
translation_default_route: zh-CN/Agentic-Design-Patterns/00-初学者路线/03-反思规划与停止条件
---

# Reflection, Planning, and Stopping Conditions

## Goal

You will turn “let the model think a few more times” into a controlled loop with external feedback, error categories, budgets, and terminal states. You will also distinguish upfront planning from rolling planning and verify that a plan still rests on current observations.

## Reflection needs a feedback signal

**Reflection** is not simply generating again with the same model. It is revising an artifact in response to feedback that can be located. Reliable feedback can come from:

- compiler or type-checking errors;
- failed unit tests and the failing cases;
- JSON Schema validation;
- missing citations or evidence that does not support a claim; or
- a fixed human or model-review rubric.

The minimum loop is:

```text
Generate -> Check -> Classify failure -> Targeted revision -> Check again
```

Without an independent criterion, resampling can damage parts that were already correct. Model review is appropriate for subjective goals such as style and completeness, but it needs a fixed rubric, retained comments, and calibration against human-labeled samples. Deterministic checkers suit syntax, structure, existence, and execution results.

Anthropic's evaluator–optimizer workflow likewise has one model generate and another provide feedback against clear criteria before iterating. “Another” does not automatically mean an independent source of truth: if both share the same missing information, they can fail together.

## A plan is not a wish list

An executable plan contains at least:

```json
{
  "step_id": "S2",
  "depends_on": ["S1"],
  "action": "query_inventory",
  "expected_output": "inventory-result-v1",
  "done_when": "status is ok and item_id matches request"
}
```

- `step_id` gives a plan step a stable, referable identifier.
- `depends_on` states which steps must finish first, preventing a data dependency from being mistaken for parallel work.
- `action` must map to an allowed tool or business action, never to an arbitrary model-generated string.
- `expected_output` describes the contract or version of a verifiable downstream artifact.
- `done_when` turns completion into an assertion a program or reviewer can check.

- **Upfront planning** suits tasks with clear goals and stable dependencies. Decompose at the start and revise only when facts change.
- **Rolling planning** suits environments in which tool observations arrive over time. Commit only to the next segment, preventing distant steps from resting on guesses.

The original ReAct paper alternates reasoning and action so a model can adjust later actions from environmental observations; Plan-and-Solve plans before execution. These are research paradigms, not a requirement to expose a model's private thinking. Engineering logs should preserve concise decision rationale, selected action, parameter summary, and observation—not depend on unverifiable long-form chain-of-thought.

## Write stopping conditions before the loop

Every loop needs at least:

| Condition | Example | Terminal state or action |
| --- | --- | --- |
| Success assertion | All five tests pass | `success` |
| Unrecoverable error | Permission explicitly denied | `failed` |
| Repeated error class | Same error signature twice consecutively | `human_review` |
| Step budget | Eight steps reached | `budget_exhausted` |
| Retry budget | Transient failure retried twice | `degraded` or `failed` |
| Time/cost budget | Deadline or spending limit | Save state and exit |
| Human request | Missing business judgment | `awaiting_input` |

“At most two rounds” is not a universal truth, but “until satisfied” leaves an open door to infinite looping. Set budgets from task risk and benefit, then tune them in offline evaluation.

## Error classification chooses the next action

Do not send every failure to “reflection”:

- `invalid_input`: ask for clarification or reject; do not retry.
- `permission_denied`: stop and report; do not bypass it by changing the prompt.
- `transient`: use limited retries and backoff.
- `deterministic_validation`: make a targeted revision from the concrete error.
- `policy_rejected`: a normal business terminal state; do not retry.
- `unknown`: retain evidence and hand off to a human or safe degradation path.

If a tool may already have caused a side effect but its response timed out, do not retry directly. Query the receipt with an idempotency key first to determine whether the action committed.

## State-machine example: generate and verify a Python function

State includes `spec_digest`, `candidate_path`, `test_report`, `revision_count`, `last_error_signature`, and budgets. The flow is:

1. Generate a candidate file from a fixed specification.
2. Run syntax and unit tests in an isolated environment.
3. If every test passes, save the report and finish.
4. If tests fail, send structured failure information to a revision step.
5. If the same error repeats or a budget is reached, stop and hand off to a human instead of rewriting again.

Completion is the result in the test environment, not the model's claim that “the code is correct now.” Tests can also be incomplete, so evaluate coverage and security boundaries before release.

## Plan invalidation and replanning

After every tool observation, ask:

1. Is the observation consistent with the plan's assumptions?
2. Did a data version needed by later steps change?
3. Does an existing approval still bind the same action and parameters?
4. Is there sufficient budget to continue?

If action parameters change, prior approval must expire. When a critical dependency changes, replan only affected steps and record old and new plan versions. Do not erase history and “guess again from the beginning.”

## Common mistakes and troubleshooting

- **Generator and reviewer share a blind spot**: add tool evidence, human labels, or a different deterministic check.
- **Revision request is too broad**: provide concrete failing assertions and an allowed edit scope.
- **Plan complete equals task complete**: verify an environmental result or acceptance test.
- **Retry transient failures forever**: set a count, total duration, and circuit-break condition.
- **Stale observations remain in context**: keep the latest fact and source version in state and explicitly retire outdated results.
- **Only final text is recorded**: retain actions, parameter summaries, observations, check results, and terminal state.

## Exercise

Draw a state machine for “generate one function and pass five tests,” and submit:

1. Nodes for generation, testing, classification, revision, completion, failure, and human takeover.
2. Budgets for maximum steps, maximum revisions, and total elapsed time.
3. Three non-retryable errors and one retryable error.
4. Two observations that invalidate an old plan.
5. A test sample proving that “model self-review passed” while the environment still failed.

## Mastery check

- [ ] I can identify the source of feedback used by each reflection step.
- [ ] I can distinguish upfront from rolling planning.
- [ ] I can give a loop exits for success, failure, budget, and human takeover.
- [ ] I can distinguish revisable, retryable, and unrecoverable errors.
- [ ] I can judge completion from environmental state rather than a model declaration.

## Next

Continue with [[agentic-design-patterns/beginner-route/04-tools-memory-and-state-boundaries|Tools, Memory, and State Boundaries]] to separate loop actions from persistent data.

## References

- [ReAct paper](https://arxiv.org/abs/2210.03629) — checked 2026-07-14.
- [Reflexion paper](https://arxiv.org/abs/2303.11366) — checked 2026-07-14.
- [Plan-and-Solve paper](https://arxiv.org/abs/2305.04091) — checked 2026-07-14.
- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) — checked 2026-07-14.
- [[agentic-design-patterns/upstream-references/section-01/reference-04-723b19d0|Reference layer: Reflection]] and [[agentic-design-patterns/upstream-references/section-01/reference-06-0f14c0e3|Planning]].
