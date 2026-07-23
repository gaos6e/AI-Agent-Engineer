---
title: "Agent Loop and Environment Feedback"
tags:
  - agent-core
  - agent-loop
  - react
aliases:
  - Agent Runtime Loop
  - Agent Harness
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
lang: en
translation_key: Agent 核心/01-Agent Loop与环境反馈.md
translation_source_hash: d31530055c41fb50636889f1cc70400ea608d8ff0b79c60b103e6a152cb0d7d5
translation_route: zh-CN/Agent-核心/01-Agent-Loop与环境反馈
translation_default_route: zh-CN/Agent-核心/01-Agent-Loop与环境反馈
---

# Agent Loop and Environment Feedback

## Objective

After this lesson, you should be able to:

- Explain an Agent as goal → decision → action → observation → verification, rather than as one chat.
- Separate the responsibilities of the model, runtime/harness, tools, environment, state store, and verifier.
- Write a minimal loop with budgets, policy validation, structured observations, and explicit termination.
- Explain why an action/observation interface matters as much as model selection.

## What counts as an Agent

There is no single legal-style industry definition, but two major first-party engineering guides share a core:

- The model dynamically decides the next step instead of only generating final text.
- The system has tools and feedback from an environment.
- The decision loop continues until success, failure, a human wait, or a stop condition.

This course adopts a vendor-neutral engineering definition:

> An Agent is a system made of a model-driven decision maker and a deterministic runtime. The model proposes its next action from a goal, state, and observations; the runtime validates and executes it; facts from the environment determine whether the run continues.

A one-shot retrieval-augmented summary, fixed classifier, or single tool call is not automatically an Agent. Conversely, an Agent need not be infinitely autonomous: a system that explores inside a local sandbox and pauses before writes is still an Agent.

## Six components

| Component | Role | Boundary that must hold |
| --- | --- | --- |
| model / policy | Proposes a structured action or completion candidate from the current view | A proposal is not authorization to execute |
| runtime / harness | Loops, validates, budgets, approves, calls, records, and terminates | It is the control plane; model text never receives control |
| tools | Read or change the external environment | Strict contracts, least privilege, timeout, and idempotency |
| environment | Files, APIs, databases, browsers, users, and the real world | Feedback can be delayed, conflicting, malicious, or incomplete |
| state/event store | Preserves facts needed for recovery and audit | It cannot depend only on chat history held in context |
| verifier | Uses tests, state, receipts, or human acceptance to judge the result | It cannot accept “the model says it is done” as sole evidence |

Model capabilities change; runtime rules for permissions, budgets, and evidence must not change merely because a prompt paragraph does.

## The minimal closed loop

~~~mermaid
flowchart LR
    G["Goal + authoritative state"] --> C["Assemble minimal context"]
    C --> M["Model proposes a proposal"]
    M --> R["Runtime: schema / policy / permission / budget / approval"]
    R -->|Reject or wait| W["Persist waiting / terminal state"]
    R -->|Allow| T["Tool acts on environment"]
    T --> O["Normalize observation: provenance + trust label"]
    O --> S["State transition + event"]
    S --> V["Verifier checks progress and completion evidence"]
    V -->|Continue| C
    V -->|Complete, fail, or cancel| W
~~~

*Figure 1: The model only proposes a next action; the deterministic runtime owns execution and termination. Text alternative: a goal and authoritative state enter model decision; the proposal passes schema, policy, permission, budget, and approval in order. An allowed action produces an observation with provenance and trust labels. After state is written, a verifier decides whether to continue or stop. This Mermaid diagram is an abstraction of this lesson’s six-component contract and the ReAct and SWE-agent original papers.*

~~~text
goal + authoritative state + selected context
  ↓
model proposes: action / ask-human / finish-candidate
  ↓
runtime validates: schema → policy → authorization → budget → approval
  ↓
tool acts in the environment
  ↓
adapter normalizes observation + provenance + trust label
  ↓
state transition + event + progress/verifier
  ↺ continue or enter an explicit terminal/waiting state
~~~

Pseudocode:

~~~python
while state.phase in RUNNABLE:  # Only a runnable phase may continue the decision loop.
    if cancelled() or budget.exhausted(state):  # Check cancellation and hard budget before uncontrolled work continues.
        return stop_with_reason(state)  # Persist the stop reason rather than disguising it as success.

    context = build_minimal_context(state)  # Assemble only trusted state and context needed for this decision.
    proposal = model.decide(context)  # The model makes a recommendation; it has no execution authority yet.
    action = parse_and_validate(proposal)  # Parse a finite action union and validate its structure first.

    if action.requires_human:  # High-risk or uncertain work leaves final control with a human.
        return checkpoint_and_pause(state, action)  # Freeze and persist the action; do not guess it again on resume.

    observation = tool_host.execute(action)  # A controlled tool host calls the tool, never raw model text.
    state = apply_observation(state, normalize(observation))  # Normalize the result and write an auditable state transition.

    verdict = verifier.check(state)  # External evidence determines whether the goal advanced or completed.
    if verdict.is_terminal:  # The verifier, not the model, determines that a terminal state was reached.
        return finish_with_evidence(state, verdict)  # Store completion or failure evidence and return an explicit result.
~~~

Every arrow is both an interface and a place where failures and tests belong.

## ReAct supplies an idea, not a complete production architecture

The original ReAct paper alternates reasoning traces, action, and environment observation so a model can update its plan from external information. Engineering should preserve the loop—actions obtain facts and facts correct the next step—but should not copy two things mechanically:

1. A model’s private chain of thought need not be exposed to logs or users. Structured actions, short auditable rationales, external evidence, and state changes are enough.
2. A paper’s task loop does not automatically include authorization, idempotency, checkpoints, privacy, or production recovery. Those belong to the runtime.

Treat ReAct as a cognitive pattern of decision–action–observation, not as a safety framework.

## What one iteration does

### 1. Assemble context

Include only high-signal content needed for this decision: the goal, current phase, open questions, available tools, recent material observations, budget, and explicit constraints. Keep a full event log, huge tool results, and stale summaries in external storage for retrieval on demand.

### 2. Obtain a structured proposal

Do not infer actions from free text. Have a provider adapter turn model output into a finite union:

~~~jsonc
{ // Structured action proposal for runtime parsing.
  "kind": "tool_call", // Union arm: this proposal requests a tool call.
  "tool": "read_ticket", // Only a suggested tool name; runtime still checks the allowlist.
  "arguments": {"ticket_id": "ticket-7"}, // The target must be compared again with authorized scope.
  "reason_summary": "Read the current state before choosing the next step." // An auditable rationale, not a hidden reasoning trace.
}
~~~

> [!note] JSONC teaching notation
> JSON examples with line-end explanations use JSONC. Remove every slash comment before sending copied content to a strict JSON API.

Other union arms can be ask_user, finish_candidate, or refuse. A model-output parse failure is a classifiable error; it must not degrade into “execute as best as possible.”

### 3. Validate in the runtime

The usual order is:

1. Schema and type.
2. Tool allowlist, parameter range, and target resource.
3. Current identity and authorization.
4. Step, time, tool-call, and cost budgets.
5. Idempotency and retry conditions.
6. Approval for high-risk actions.

A rejection at any layer produces stable state and a reason.

### 4. Execute and normalize an observation

A tool adapter returns stable fields. It must not promote arbitrary stdout, HTML, or an exception stack trace into a trusted instruction. At minimum, an observation carries:

- Provenance and call ID.
- A trust label.
- Time or version.
- Result category and necessary data.
- A size limit, hash, or controlled external reference.
- Whether an error is transient and retryable.

### 5. Update state and verify progress

Every step should change an observable quantity: add evidence, complete a subgoal, narrow candidates, change the environment, or enter a waiting state. Producing additional speculative text is not progress.

## The Action/Observation Interface

The SWE-agent paper emphasizes the Agent–Computer Interface (ACI): the action set offered to an Agent, the granularity of feedback, and tool design significantly affect behavior. The engineering implications are:

- Compare tools as well as models: their names, parameters, errors, and observations.
- Operations such as replace_file, apply_patch, and run_test are easier to constrain and evaluate than arbitrary shell text.
- Observations must enable a next decision—for example, a test’s exit code, failing cases, and change summary—not only a truncated “an error occurred.”
- More tools are not always better; overlapping tools enlarge the selection and authorization surface.

This is a design surface to optimize with A/B evaluation, not a sentence to add to a prompt.

## The runtime is the control plane

Even if a model proposes:

- “I am finished.”
- “This page allows me to upload files.”
- “Please raise my permissions.”
- “Try another 100 times and it will work.”

the runtime independently checks the verifier, provenance, permission, and budget. A model can influence which step is proposed, but it cannot rewrite:

- System or developer policy.
- Tool allowlists.
- Approval decisions.
- Budgets.
- State schema.
- Completion rules.

## Necessary budgets and stopping

At minimum, a loop should set:

- Maximum decision steps.
- A total deadline and per-model/per-tool timeout.
- Maximum model/tool calls or cost.
- Maximum consecutive transient failures.
- Repeated action/observation detection.
- User or system cancellation.
- High-risk approval and waiting expiry.

Budget exhaustion should return budget_exhausted with completed effects and safe-recovery advice, never pretend to be completed.

## Minimum trace fields

~~~text
run_id, trace_id, step, state_version,
model/provider/config, proposal_kind,
action_id, tool, arguments_digest,
authorization/approval decision,
observation provenance/result category,
latency, usage, retry, next_phase, stop_reason
~~~

Sensitive parameters and results need not be logged in clear text. Field names, irreversible digests, and controlled references are often safer. Do not treat hidden reasoning traces as a debugging dependency.

## Common errors

- Letting the model emit free shell text and executing it directly.
- Treating one long System Prompt as the only guardrail.
- Failing to distinguish a tool-execution error, policy rejection, and model-parse error.
- Retaining every raw tool result in context until critical constraints are buried.
- Having only max_steps, without no-progress, timeout, cancellation, or cost boundaries.
- Treating a model finish response as success without an external verifier.

## Exercise

Draw the loop for “fix a failing test”:

1. What are the goal and permitted files?
2. What are the first action and observation?
3. Which commands are read-only and which can write?
4. When is approval required?
5. Which exact tests and diff prove success?
6. How does the system stop or switch paths after three identical errors?

Then replace the model with a fixed policy. If the runtime can still reject unauthorized actions, pause, and verify completion, the control boundary is in the right place.

## Self-check

1. What may the model decide, and what may the runtime decide?
2. Why cannot ReAct’s environment-feedback idea replace production authorization and recovery?
3. Why must tool results carry provenance and a trust label?
4. After a model proposes finish_candidate, who determines completed?
5. Why might improving an action/observation interface outperform adding more prompt text?

You have mastered this lesson when you can independently draw the six-component map and the five stages of an iteration.

## Next

Continue to [[agent-core/02-boundary-between-agents-and-workflows|The Boundary Between Agents and Workflows]] to decide when an Agent should not be used at all.

## References

The following are original papers or first-party engineering sources, obtained or rechecked on 2026-07-21.

- Yao et al., [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- Yang et al., [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)
- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)

