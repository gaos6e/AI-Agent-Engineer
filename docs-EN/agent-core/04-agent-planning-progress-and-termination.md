---
title: "Agent Planning, Progress, and Termination"
tags:
  - agent-core
  - planning
  - progress
  - termination
aliases:
  - Agent Planning and Termination
  - Agent Stop Conditions
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
lang: en
translation_key: Agent 核心/04-计划、进度与终止条件.md
translation_source_hash: ef00635651ed8070418a54e64251044c99d36f941e76475769ae7600f8219a19
translation_route: zh-CN/Agent-核心/04-计划、进度与终止条件
translation_default_route: zh-CN/Agent-核心/04-计划、进度与终止条件
---

# Agent Planning, Progress, and Termination

## Objective

After this lesson, you should be able to:

- Design a plan as a revisable working hypothesis rather than an unauditable long reasoning trace.
- Define state changes, success evidence, and failure branches for each subgoal.
- Detect no progress, repeated actions, oscillation, and false completion.
- Model every exit path, including success, failure, waiting, cancellation, and budget exhaustion.

## What a plan solves

A plan does not predict every future step. Its value is to:

- Decompose a goal into verifiable subgoals.
- Record dependencies, constraints, and risks explicitly.
- Allow new observations to update the next step.
- Show users and runtime progress and unresolved items.
- Structure stopping, recovery, and takeover.

A usable plan item is:

~~~yaml
id: verify-current-state # Stable subgoal ID for events, tests, and recovery.
status: in_progress # Runtime may continue because this item is not finished.
goal: Confirm whether ticket-7 is still open # Narrow a natural-language goal into a verifiable question.
allowed_actions: # Minimal tool set permitted for this subgoal.
  - lookup_ticket # Read-only lookup; this stage cannot write the ticket.
success_evidence: # Required external evidence for subgoal success.
  - Lookup receipt with version and provenance # The receipt proves the queried object and result source.
failure_policy: # Predictable terminal behavior for each error class.
  transient: Retry at most twice # Retry transient errors finitely to avoid an infinite loop.
  permanent: failed # An unrecoverable error enters a failed terminal state.
~~~

“Analyze first, then solve the problem” is not an executable plan when it lacks external evidence and boundaries.

## A plan is a working hypothesis

An Agent often starts with incomplete information. A plan can change when:

- Environment state contradicts a hypothesis.
- A tool fails or permission is insufficient.
- A user clarifies the goal.
- A verifier exposes a missing subgoal.
- A lower-risk or lower-cost path is found.

Replanning must not change immutable constraints:

- Explicit user scope.
- Tool allowlist and authorization.
- Budget.
- Approval result.
- Data and security policy.
- Termination rules.

Persist which plan items changed and which observation justified the change. There is no need to preserve or expose a model’s private reasoning chain.

## Three planning granularities

### Reactive

Decide only the next action each turn. This fits short tasks and high-feedback environments and keeps context small, but can become locally greedy or cycle.

### High-level plan plus stepwise refinement

List subgoals first, then create concrete actions when an item is reached. This fits most engineering Agents: it supplies global direction without pretending to know every tool call.

### Fixed workflow plus a local Agent

Code defines the high-risk main path; an Agent explores only at one node. This is the most predictable option and is often suitable for production.

Do not assume a longer plan is smarter. Plans themselves consume context and become stale as the environment changes.

## Progress must be observable

Every step should change at least one category:

- **Environment**: a file, record, or task state changes.
- **Evidence**: a test, receipt, source, or conflict is added.
- **Uncertainty**: candidates shrink or an open question is answered.
- **Plan**: a subgoal completes, fails, or becomes blocked.
- **Control state**: the run enters approval wait, cancellation, or explicit termination.

You can define a progress vector:

~~~jsonc
{ // Observable indicators for determining whether work is really advancing.
  "subgoals_done": 2, // Number of subgoals supported by external evidence.
  "subgoals_total": 5, // Total plan items; plan rewrites must retain a version history.
  "open_questions": 1, // Unanswered questions; failure to decline can trigger a pause or path change.
  "verified_evidence": 3, // Verified receipts, tests, or human decisions.
  "state_version": 8, // Authoritative state version for these metrics; avoids mixing stale snapshots.
  "consecutive_failures": 0 // Consecutive failure count used by the failure budget.
}
~~~

> [!note] JSONC teaching notation
> Text after slash comments explains each line; remove it before copying the payload as strict JSON.

Do not force progress into one percentage. In a research task, “found more links” is not necessarily progress; “the key claim has two independent primary sources” can be.

## Detect no progress and loops

### Repeated action

Normalize tool + arguments + relevant state version and compute a digest. If the same state repeatedly produces the same action and observation, stop blind retry.

### Oscillation

Detect A → B → A → B, such as switching back and forth between two tools or plans. Maintain signatures for the most recent N actions and phases to find cycles.

### Text expansion

If every turn produces more plans or summaries but no new evidence or state change, limit consecutive turns without external action.

### Same-class failure

The error category, target, and parameters are identical. Retry only when a prerequisite changed, such as backoff, refreshed credentials, or environment change.

Respond in this order:

1. Use structured error to guide one parameter correction.
2. Switch to an allowed strategy.
3. Request human input.
4. End as blocked, failed, or budget_exhausted.

Maximum steps are only a final guardrail; they cannot replace progress semantics.

## Completion is a verifier conclusion

A model may return finish_candidate; runtime then checks:

| Task | External success evidence |
| --- | --- |
| Fix code | Relevant tests, diff, lint, and type checks |
| Data migration | Input/output counts, checksum, and failure list |
| Business write | Downstream persistent state, receipt, and target-resource version |
| Research | Claim–source coverage, dates, and unresolved questions |
| File organization | Target inventory, links, and no omissions or conflicts |

A verifier must also check negative conditions: no out-of-scope changes, no real secret, and no unconfirmed side effect. A model checking off its own plan item is not evidence.

## Terminal-state machine

At minimum, distinguish:

| State | Meaning | Recoverable? |
| --- | --- | --- |
| completed | Verifier confirmed success criteria | Usually not needed |
| failed | Unrecoverable error or retry budget exhausted | After conditions are fixed, a new run or recovery |
| waiting_input | User information is missing | Yes |
| waiting_approval | Action is frozen and awaits approval | Yes |
| blocked | External dependency, permission, or service unavailable | When conditions change |
| budget_exhausted | Step, time, cost, or call limit reached | Budget adjustment needs new authorization |
| cancelled | User or system cancelled | Depends on product policy |
| rejected | A human explicitly rejected the action | An alternative without side effects may be possible |

Do not treat waiting as failed, and do not treat “policy has no next action” as completed automatically.

## Stop reason and result envelope

At termination, return:

~~~jsonc
{ // Recoverable budget-exhaustion result that never pretends to be success.
  "run_id": "run-42", // Identifies the run a user or scheduler must handle.
  "phase": "budget_exhausted", // States that budget, not goal completion, caused termination.
  "stop_reason": "max_tool_calls", // Names the exact exhausted budget.
  "goal_progress": { // Shows the boundary between completed and incomplete work.
    "completed": ["lookup-current-ticket"], // Evidence-backed action that must not be repeated.
    "pending": ["close-current-ticket"] // Unexecuted action that must pass all gates again before resume.
  }, // End progress object.
  "side_effects": [], // Known external effects; unknown ones must require reconciliation explicitly.
  "evidence": ["lookup-receipt-abc"], // Controlled evidence IDs supporting the current decision.
  "safe_resume": { // Preconditions before a run may continue.
    "condition": "Increase write-tool budget and reapprove", // Resume is controlled completion of prerequisites, not automatic retry.
    "checkpoint_version": 7 // Resume only while this checkpoint remains valid.
  } // End safe-resume object.
}
~~~

This tells the user what happened, what did not happen, whether side effects exist, and how to continue.

## Budget layers

- Per-model-call timeout and token limit.
- Per-tool timeout and output-size limit.
- Per-step deadline.
- Whole-run wall-clock deadline.
- Model and tool-call counts and cost.
- Consecutive failures and retries.
- Human-wait expiry.
- Subtask and concurrency limit.

Progress events can show that a task remains active, but an absolute deadline is still required so a malicious or uncontrolled tool cannot extend work forever.

## Running example

Goal: “Close ticket-7, but only the current ticket and only after approval.”

Plan:

1. Read ticket-7; success evidence is a state observation with provenance.
2. If it does not exist or is already closed, terminate normally rather than retry a write.
3. Create an action only for ticket-7 and freeze its fingerprint.
4. Wait for approval; request it again if it expires or parameters change.
5. Close using an idempotency key and retain a receipt.
6. The verifier must confirm ticket-7 is closed and the receipt matches before completed.

A malicious customer note asking to close another ticket does not change the plan constraints.

## Exercise

For “migrate 100 files,” design:

- Five verifiable subgoals.
- A checkpoint and progress vector every 20 files.
- Duplicate-name, permission-failure, and cancellation branches.
- The applicable states from the eight terminal or waiting states.
- Completion evidence and negative evidence that no unnecessary changes were made.

Simulate a failure at file 70. Can the user tell whether the first 69 committed, which ones require compensation, and which state supports resume?

## Self-check

1. Why is a plan a hypothesis rather than an immutable script?
2. Why can continuously generating new text still be no progress?
3. What does a verifier check after a model says “done”?
4. How does waiting_approval behave differently from failed?
5. Why cannot maximum steps alone detect oscillation?

You have mastered this lesson when you can write a plan item, progress vector, verifier, and stop envelope.

## Next

Continue to [[agent-core/05-long-running-agent-checkpoints-recovery-and-idempotency|Long-Running Agent Checkpoints, Recovery, and Idempotency]] to handle process crashes and uncertain side effects.

## References

The following are original papers or first-party engineering sources, obtained or rechecked on 2026-07-21.

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- Yao et al., [ReAct](https://arxiv.org/abs/2210.03629)
