---
title: "Agent Core"
tags:
  - AI-Agent-Engineer
  - agent-core
  - learning-path
aliases:
  - Agent Core Index
  - Core AI Agent Runtime
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
ai_learning_stage: 5. Single Agents and Tools
ai_learning_order: 32
ai_learning_schema: 2
ai_learning_id: agent-core
ai_learning_domain: agent-runtime
ai_learning_catalog_order: 3200
ai_learning_hard_prerequisites:
  - tool-calling
ai_learning_track_agent_app_order: 600
ai_learning_track_agent_app_kind: core
ai_learning_track_agent_platform_order: 600
ai_learning_track_agent_platform_kind: core
ai_learning_track_multimodal_realtime_order: 600
ai_learning_track_multimodal_realtime_kind: core
lang: en
translation_key: Agent 核心/00-目录.md
translation_source_hash: 5080563d124ffe9edd19845ae37e0639c9ce74865a4b9f3b6906446759cafe3f
translation_route: zh-CN/Agent-核心/00-目录
translation_default_route: zh-CN/Agent-核心/00-目录
---

# Agent Core

## Course overview

An Agent is not “a model that keeps thinking.” It is a controlled system made of model decisions and a deterministic runtime:

~~~text
goal + state + observations
→ model proposes a structured next action
→ runtime validates policy, permission, budget, and approval
→ a tool reads or changes the environment
→ observation is written back to state
→ a verifier decides to continue, wait, or stop
~~~

This course builds a vendor-neutral core for a single Agent from first principles: the loop, the Agent/workflow boundary, state/context/memory, plans and termination, checkpoints and idempotency, human control, untrusted observations, and a runnable offline runtime.

> [!info] Dynamic-fact boundary
> Sources were obtained or rechecked on 2026-07-21. Agent SDKs, hosted sessions, approval, memory, and tracing APIs change by provider; this course depends only on stable engineering boundaries. Recheck the official SDK documentation, versions, and actual behavior on both sides of a product integration. On that date, the official NIST AI RMF 1.0 page still stated that the framework was under revision. This course uses its general principles for roles and oversight, not as industry compliance advice.

## Where this course fits

This is the core runtime course in the “Single Agents and Tools” stage. Course order numbers support discovery; they do not require every earlier course. Its universal hard prerequisite is:

- [[tool-calling-function-calling/00-index|Tool Calling (including Function Calling)]]: tool contracts, orchestration, errors, and approval.

Before work that reads untrusted observations or executes tools, complete the roadmap’s [[all-of-ai#early-safety-and-evaluation-milestone|early safety and evaluation milestone]]. This reuses existing chapters to create an early quality gate; it does not make a full AI Safety or Evaluation Systems course a hard prerequisite for this course.

If a project needs to connect outside capabilities or context through a standard protocol, study [[mcp/00-index|MCP]] before or after this course as interoperability requires. Direct SDKs, in-process functions, and existing services can also form an Agent runtime. MCP is not a universal prerequisite for loops, state, termination, or recovery.

This course answers who decides the next step, how state is retained, when to stop, and how to recover safely. Continue afterward with:

- [[environmental-agents/00-index|Environment-based Agents]]: apply the observation–action runtime to browsers, desktops, and coding environments.
- [[agent-skills/00-index|Agent Skills]]: reusable procedural knowledge.
- [[agentic-design-patterns/00-index|Agentic Design Patterns]]: compositions such as routing, parallel work, and planner/evaluator patterns.
- [[workflow-automation/00-index|Workflow Automation]]: scheduling, DAGs, queues, compensation, and production orchestration.
- [[multi-agent-collaboration/00-index|Multi-Agent Collaboration]]: division of work, communication, and governance among multiple Agents.

## Learning objectives

- Implement an observe–decide–act loop that separates model proposals from runtime execution.
- Choose a single call, workflow, or Agent according to path uncertainty, verification, risk, and cost.
- Distinguish authoritative state, an event log, context, working summaries, and long-term memory.
- Make plan items, progress, success evidence, and every terminal state auditable.
- Identify crash windows and recover through checkpoints, idempotency keys, intent digests, and receipts.
- Model clarification, approval, rejection, takeover, and cancellation as persistent state.
- Treat all tool and resource content as untrusted observation.
- Test a runtime with deterministic policy and offline tools; do not treat a model’s incidental behavior as safety evidence.

## Prerequisites

- [[prompt-engineering/00-index|Prompt Engineering]] and [[context-engineering/00-index|Context Engineering]].
- Timeouts, usage, and provider adapters from [[llm-api-integration/00-index|LLM API Integration]].
- Tool Calling schemas, call IDs, authorization, idempotency, and errors.
- Python dataclasses, exceptions, JSON, hashes, and basic tests.
- API retries, deadlines, idempotency, and authentication.

LangChain or CrewAI is not required. First understand the runtime contract; a framework is only one implementation.

## Core-responsibility map

| Component | May do | Must not decide alone |
| --- | --- | --- |
| model/policy | Propose an action, ask a question, or produce a finish candidate | Permission, approval, or real completion |
| runtime/harness | Validate, budget, execute, transition state, and terminate | Replace the business goal defined by the user |
| tool adapter | Call an external system and normalize observations | Elevate its own permission or trust |
| state/event store | Preserve facts, checkpoints, and audit records | Turn a summary into an approval fact |
| verifier | Check tests, receipts, external state, or human acceptance | Bypass negative criteria or failure conditions |
| human | Clarify, approve, reject, or take over | Be forced into a rubber-stamp decision when information is insufficient |

## Recommended order

| Order | Lesson | Key question | Completion evidence |
| --- | --- | --- | --- |
| 1 | [[agent-core/01-agent-loop-and-environment-feedback\|Agent Loop and Environment Feedback]] | How do the model and runtime form a loop? | Six-component diagram plus one iteration |
| 2 | [[agent-core/02-boundary-between-agents-and-workflows\|The Boundary Between Agents and Workflows]] | When should an Agent not be used? | ADR with baseline, risk, and fallback |
| 3 | [[agent-core/03-agent-state-context-and-memory\|Agent State, Context, and Memory]] | What is a source of truth, and what is only this turn’s view? | Five-layer data model |
| 4 | [[agent-core/04-agent-planning-progress-and-termination\|Agent Planning, Progress, and Termination]] | How can progress and completion be proven? | Plan + progress + verifier + stop envelope |
| 5 | [[agent-core/05-long-running-agent-checkpoints-recovery-and-idempotency\|Long-Running Agent Checkpoints, Recovery, and Idempotency]] | How do crashes avoid repeating side effects? | Four crash windows and a recovery protocol |
| 6 | [[agent-core/06-human-in-the-loop-and-control\|Human-in-the-Loop and Control]] | How can human control be durable and expire safely? | Approval contract and UI |
| 7 | [[agent-core/07-untrusted-tool-results-and-defenses\|Untrusted Tool Results and Defenses]] | How can the runtime stay safe when a model follows malicious text? | Defense matrix outside the model |
| 8 | [[agent-core/08-integrated-agent-project-and-self-test\|Integrated Agent Project and Self-Test]] | How do boundaries become runtime evidence? | Demo plus 68 tests |

For a first pass, allow 12–16 hours: 60–90 minutes for each of the first seven lessons and 3–5 hours for the project.

## Hands-on entry point

The project uses only the Python standard library. It makes no network calls, uses no real model, and needs no key. Run the following from the repository root that contains docs-EN and .website:

~~~powershell
Push-Location -LiteralPath 'docs-EN\agent-core' # Enter this course temporarily, then restore the original working directory.
python -B .\examples\bounded_agent.py # Run the offline demo; -B prevents __pycache__ output.
python -B .\examples\test_bounded_agent.py # Run every regression test in normal mode.
python -B -O .\examples\test_bounded_agent.py # Prove critical controls do not depend on bare assert under optimization.
python -B -W error .\examples\test_bounded_agent.py # Treat every Python warning as a test failure.
python -B -O -W error .\examples\test_bounded_agent.py # Combine optimization and warnings-as-errors checks.
Pop-Location # Return to the prior working directory.
~~~

Current baseline:

- Demo: malicious observation → pause before write → checkpoint → approval → simulated crash after commit → receipt recovery → completed.
- Already-satisfied path: lookup confirms that the ticket is already closed → no write is proposed and no approval is requested → completed with already_satisfied.
- The close side effect occurs exactly once.
- 68 tests.
- Normal, -O, -W error, and -O -W error modes all pass.
- Zero network calls, third-party dependencies, or credentials.

## Mastery criteria

- [ ] Explain that the model/policy proposes actions while the runtime owns execution control.
- [ ] Compare deterministic programs, single calls, workflows, and Agents for a real task.
- [ ] Reconstruct the next step from state and events without a complete chat history.
- [ ] Explain why a summary cannot overwrite approval or state.
- [ ] Define progress, completion evidence, and waiting or terminal states.
- [ ] Draw the four crash windows.
- [ ] Design caching for the same key and intent, and a conflict for the same key with a different intent.
- [ ] Design an approval bound to fingerprint, state version, scope, and expiry.
- [ ] Ensure a malicious observation cannot exceed authorization even if it hijacks the model.
- [ ] Run and explain all 68 tests and the project’s limitations.
- [ ] State when to fall back to a fixed workflow.

## Relationships to other courses

- [[context-engineering/00-index|Context Engineering]] decides which state and observations enter the model each turn; this course owns the sources of truth and runtime state.
- [[tool-calling-function-calling/00-index|Tool Calling (including Function Calling)]] supplies single-call contracts; this course puts calls into a multi-turn state machine.
- [[mcp/00-index|MCP]] is a possible capability-integration boundary, not a planner.
- [[workflow-automation/00-index|Workflow Automation]] supplies fuller durable orchestration, schedulers, queues, and compensation.
- [[environmental-agents/00-index|Environment-based Agents]] reuse this runtime contract and further constrain browser, desktop, and coding-environment initial states, actions, sandboxes, terminal states, and side-effect evaluation.
- [[runtime-monitoring/00-index|Runtime Monitoring]] turns events, traces, budgets, and stop reasons into production observability.
- [[evaluation-framework/00-index|Evaluation Framework]] measures task success, trajectories, safety, cost, and recovery.
- [[ai-safety/00-index|AI Safety]] extends prompt injection, identity, supply-chain, sandbox, and governance controls.

## Key references

The following prioritize original papers, first-party engineering guides, and public security or risk frameworks. Sources were obtained or rechecked on 2026-07-21.

| Topic | Source |
| --- | --- |
| Agents, workflows, and simple architectures | [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) |
| Agent-building foundations | [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) |
| Reasoning–action–observation | Yao et al., [ReAct](https://arxiv.org/abs/2210.03629) |
| Action interfaces | Yang et al., [SWE-agent](https://arxiv.org/abs/2405.15793) |
| Multi-turn context | [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) |
| Durable workflows | [Temporal: Workflow concepts](https://docs.temporal.io/workflows) |
| Agentic security | [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) |
| Human roles and risk | [NIST AI Risk Management Framework](https://airc.nist.gov/airmf-resources/airmf/) |

## Course boundary

This course covers single-Agent runtime invariants. It does not repeat:

- Prompt-writing details: Prompt Engineering.
- The full retrieval and compression toolkit for context: Context Engineering.
- Framework APIs: LangChain and CrewAI.
- Multi-Agent division of work: Multi-Agent Collaboration.
- Production metrics platforms: Runtime Monitoring and LLMOps.
- System-level security and regulation: AI Safety and AI Governance.

For product APIs or version-dependent facts, defer to the corresponding official documentation and real tests.
