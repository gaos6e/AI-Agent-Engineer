---
title: "Testing, Evaluation, and Observability"
aliases:
  - CrewAI Testing Evaluation Observability
  - CrewAI Evaluation
tags:
  - ai-agent-engineer
  - crewai
  - testing
  - evaluation
  - observability
source_checked: 2026-07-21
concept_source_checked: 2026-07-21
package_source_checked: 2026-07-21
lang: en
translation_key: CrewAI/05-测试评测与可观测性.md
translation_source_hash: 45d5e2639a61161e1dc6af2a8995ef5b481021df272750e05772339cb047d4fe
translation_route: zh-CN/CrewAI/05-测试评测与可观测性
translation_default_route: zh-CN/CrewAI/05-测试评测与可观测性
---

# Testing, Evaluation, and Observability

## Learning objectives

You will turn “the Agent appears to work” into repeatable acceptance criteria: first use deterministic tests for data, Tools, Tasks, and Flows; then evaluate nondeterministic quality across repeated model runs; finally retain events and version information that explain where a failure occurred.

> [!important] Boundary for dynamic sources
> The latest stable package observed on PyPI on 2026-07-21 was <code>crewai==1.15.5</code>, while this course’s tested Layer B baseline remains <code>1.15.4</code>. Official test commands, default models, and provider limitations can change. For a real project, inspect <code>crewai test --help</code> in the pinned version first; do not infer future CLI behavior from this note.

## Why one successful demonstration is not acceptance

LLM output varies with model version, sampling, context, Tool returns, and network state. A successful example means only that this run did not expose a problem. It does not prove that:

- a failing input stops safely;
- a Tool cannot exceed authority or repeat a side effect;
- citations actually support conclusions;
- a Flow stops after its second attempt;
- dependency or Prompt changes introduce no regression;
- cost and latency satisfy production budgets.

Verify deterministic business controls separately from probabilistic content quality.

## Four layers of testing and evaluation

### Layer 1: pure-function and schema unit tests

Make no model call; cover the most stable and least expensive behavior:

- reject invalid input fields, types, lengths, and unknown fields;
- check Tool parameter allowlists and authority;
- validate Task output schemas and source IDs;
- test Flow state transition, attempt ceiling, and terminal states;
- test idempotent publication, repeated recovery, and refusal to overwrite different content;
- classify errors and identify which categories are retryable.

These tests must be effective under ordinary Python and <code>python -O</code>. Do not put essential checks in bare <code>assert</code>, because optimization removes them. Layer A has 39 tests at this level; Layer B has nine real CrewAI-runtime tests. Report those groups separately rather than collapsing them into an imprecise number.

### Layer 2: offline Agent or Task evaluation

For one Task, freeze inputs and graders and check:

- whether it produces parseable structured output;
- whether it uses only permitted sources;
- whether it records unknowns when evidence is missing;
- whether prohibited content or unauthorized Tool intent appears;
- pass rate and dominant failure categories across repeated identical inputs.

Model stubs verify control logic but do not represent real-model quality. Recorded responses can reduce cost, but can conceal changes after a model upgrade; record capture date, model, and SDK version.

### Layer 3: Crew trajectory evaluation

Evaluate collaboration process, not just final text:

- do Tasks run in permitted order?
- does every Agent use only its own Tools?
- does failure route to revision or human takeover?
- are Tool calls, total steps, tokens, and time within budget?
- can each important conclusion be traced to sources and intermediate artifacts?

Lively multi-Agent conversation is not a quality metric. A trajectory should show that the division of work creates independent artifacts or verification value.

### Layer 4: small real integration and online evaluation

With model, dependency, and data versions locked, run a small number of end-to-end samples using controlled credentials. Increase concurrency and real-data exposure gradually while recording quality, cost, latency, and safety. Substitute preview or sandbox behavior for high-risk writes until release gates are met.

## Designing an evaluation set

An effective set includes at least:

1. ordinary inputs;
2. boundary and empty values;
3. missing sources or unanswerable requests;
4. prompt injection in external documents;
5. Tool timeout, rate limiting, and permission denial;
6. repeated runs and checkpoint recovery;
7. human rejection;
8. data isolation across tenants or authority levels;
9. extremely long context;
10. old schema, outdated Knowledge, or incompatible state.

For each case, record a sample ID, input version, expected terminal state, allowed Tools, prohibited behavior, required citations, maximum attempts, and grading method. When judgment is subjective, write a rubric first and calibrate the grader against human samples.

## Metrics and release gates

| Dimension | Example metrics | Gate-design principle |
| --- | --- | --- |
| Task | Task success rate, correct terminal-state rate | Report by scenario, not only a global mean. |
| Facts | Citation-support rate, unknown-recognition rate | Every critical conclusion must be traceable. |
| Tools | Tool-selection accuracy, parameter pass rate | Unauthorized calls are severe failures reported separately. |
| Reliability | Retry-success rate, repeated-side-effect rate | Repeated side effects normally must be zero. |
| Safety | Injection-success rate, secret-leak rate | A high-risk violation cannot be averaged away by quality. |
| Runtime | P50/P95 latency, steps, and cost | Include sample size and versions. |
| Human | Takeover rate, false-rejection rate, review time | Takeover may itself be the correct terminal state. |

Define red lines before average quality. For example, a citation-support threshold cannot offset one real credential leak. Gates come from concrete business risk and a baseline, not copied numbers.

## Positioning CrewAI’s built-in testing

The official Testing page provides <code>crewai test</code> as an entry point for Crew testing. Its page still described default iterations, a default model, and current provider limits on 2026-07-21; those are volatile implementation facts. This course has no real credentials and did not run this command. If you adopt it:

~~~powershell
# In a real project’s activated virtual environment, inspect the pinned CLI first.
crewai test --help  # See actual parameters, defaults, and available test entry points.

# Only run after confirming cost, model, and samples.
crewai test  # Run framework-level Crew testing; application tests still cover safety and business contracts.
~~~

The framework command can complement real Crew evaluation. It cannot replace unit tests for your schema, authority, idempotency, or Flow routes.

## Observability: retain explainable evidence for failure

Generate a unique <code>run_id</code> for every run. At minimum, events record:

- event sequence, type, and time;
- stable Crew, Agent, Task, and Tool IDs;
- schema versions and security digests of inputs and outputs;
- Tool success, error category, retries, and duration;
- route decisions, approver, or reason for human takeover;
- dependency, model, Prompt, Tool-schema, Knowledge, and evaluation-set versions;
- terminal state, cost, and key quality verdicts.

Do not indiscriminately log full Prompts, keys, personal data, or raw Tool responses. The observability system is itself a data receiver and needs least privilege, redaction, retention limits, and access audit.

CrewAI’s built-in tracing and anonymous telemetry are different channels. The current tracing page says enabled tracing can show Agent decisions, Tool use, and LLM-call prompts/responses; turning it on for diagnosis is therefore a data-egress and access-control decision. Layer B verifies the runtime control plane only with <code>tracing=False</code> in a pinned fixture and performs no network capture. It does not prove that a deployment, plug-in, or exporter has no additional data exit. Include trace destination, field minimization, access roles, retention, and sampling in pre-release tests.

The official Event Listeners page offers event-bus listeners and concepts such as <code>BaseEventListener</code>. Event types and import paths can change; perform a minimal import test against the pinned version before integrating. A listener failure must not silently alter core business semantics.

## Locating a regression

1. Confirm the versions of sample, dependency, model, Prompt, Tool schema, and Knowledge index.
2. Find the first event and Task where failure appears.
3. Separate model-output, Tool, routing, and grader errors.
4. Replay the smallest failing unit with fixed input.
5. Change one major variable at a time.
6. Add a test that reproduces the fault, then confirm the fix preserves other scenarios.

When evidence cannot localize the failure, say “the cause cannot currently be proven” rather than guessing from final text.

## Hands-on exercise

For a research-brief Crew, design 12 evaluation samples: four ordinary, three with insufficient evidence, two Tool failures, two prompt injections, and one repeat recovery. For each sample, define:

- expected terminal state;
- Tools allowed to run;
- source IDs that must appear;
- maximum attempts;
- one automatic grader and one human spot-check.

Then run the three modes for [[crewai/07-project-offline-research-brief-flow|Offline Research-Brief Flow]] and explain why normal mode, <code>-O</code>, and warnings-as-errors provide different evidence.

## Mastery check

- [ ] Distinguish deterministic testing, model evaluation, trajectory evaluation, and online evaluation.
- [ ] Give every evaluation sample an expected terminal state and prohibited behavior.
- [ ] Report quality, reliability, safety, cost, and latency together.
- [ ] Reproduce a failure from run events and version information.
- [ ] Know that <code>crewai test</code> does not replace business-control or safety tests.

## Next step

Once testing exposes a problem, decide how the system stops safely, recovers, and reaches production in [[crewai/06-safety-failure-recovery-and-production-boundaries|Safety, Failure Recovery, and Production Boundaries]].

## Primary references

Sources checked on 2026-07-21:

- [CrewAI Testing](https://docs.crewai.com/en/concepts/testing)
- [CrewAI Event Listeners](https://docs.crewai.com/en/concepts/event-listener)
- [CrewAI Flows](https://docs.crewai.com/en/concepts/flows)
- [CrewAI on PyPI](https://pypi.org/project/crewai/)
