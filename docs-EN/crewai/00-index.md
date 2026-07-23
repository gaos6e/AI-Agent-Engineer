---
title: "CrewAI Learning Index"
aliases:
  - CrewAI Learning Path from Scratch
  - CrewAI Hands-on Entry Point
tags:
  - crewai
  - ai-agent
  - framework
package_snapshot: crewai==1.15.4
package_released: 2026-07-17
latest_package_observed: crewai==1.15.5
latest_package_released: 2026-07-20
source_checked: 2026-07-21
concept_source_checked: 2026-07-21
package_source_checked: 2026-07-21
content_origin: original
content_status: dynamic
ai_learning_stage: 6. Framework Practice
ai_learning_order: 37
ai_learning_schema: 2
ai_learning_id: crewai
ai_learning_domain: framework-practice
ai_learning_catalog_order: 3700
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 750
ai_learning_track_agent_app_kind: optional
ai_learning_track_agent_platform_order: 750
ai_learning_track_agent_platform_kind: optional
lang: en
translation_key: CrewAI/00-目录.md
translation_source_hash: d86eba94227dbf31f23c0905c37543cf5eefb2e7b07518abb6aa3fa1c107e473
translation_route: zh-CN/CrewAI/00-目录
translation_default_route: zh-CN/CrewAI/00-目录
---

# CrewAI Learning Index

## Course overview

CrewAI is a Python Agent-orchestration framework with two complementary abstractions: **Crews** organize collaborative work with Agents, Tasks, and Processes, while **Flows** use events, routing, and state to control an application workflow. The official PyPI description distinguishes them explicitly: Crews favor autonomous collaboration, while Flows favor fine-grained, event-driven execution control.

This course does not treat “multiple Agents” as the default answer. Determine the task, state, tool authority, and completion criteria first; then choose ordinary Python, a Flow, a Crew, or a combination. The eight lessons move from installation and core objects through state, tools, memory, evaluation, recovery, and production boundaries, then complete a framework-independent Layer A and a real CrewAI Layer B in that order.

> [!important] Three distinct version facts
> - **Tested package baseline:** installation and Layer B pin <code>crewai 1.15.4</code>. It was released on 2026-07-17, declares Python <code>>=3.10,&lt;3.14</code>, and is the version covered by the nine real-runtime tests.
> - **Latest-package observation:** PyPI showed <code>crewai 1.15.5</code> as the latest stable release on 2026-07-21, released on 2026-07-20. This course checked only version and release information; it did not rerun the examples on <code>1.15.5</code>. “Latest installable” therefore does not mean “validated by this course.”
> - **Documentation snapshot:** Flow, Checkpointing, Tools, Memory, Knowledge, Testing, Telemetry, and Tracing pages were rechecked on 2026-07-21. The Agents/Tasks/Processes object shapes retain the per-page deep-reading record from 2026-07-14. Page labels are not PyPI package versions and cannot replace a minimal integration test against the pinned wheel.
>
> Page labels, the latest PyPI version, and the tested baseline are different facts. A real project must pin its installation version and verify the corresponding source, API reference, minimal import test, and integration tests. This course records a dated learning baseline, not a permanent API guarantee.

## Where this course fits

This course belongs to the “Framework Practice” stage. Before taking the CrewAI branch, understand the relevant capabilities from [[agent-core/00-index|Agent Core]], [[tool-calling-function-calling/00-index|Tool Calling (including Function Calling)]], and [[agentic-design-patterns/00-index|Agentic Design Patterns]], then map framework-independent loops, tools, state, approvals, and evaluation to CrewAI. That is a recommended framework-learning order; it does not mean every Agent role must complete every course, nor that CrewAI is a universal hard prerequisite for Agents or RAG.

## Learning objectives

- Explain the responsibilities of Agent, Task, Crew, Process, Flow, State, and Event.
- Choose the least-complex solution among ordinary Python, Flow, Crew, and Flow + Crew.
- Use Task contracts and structured output to isolate data boundaries between Agents.
- Distinguish Flow state, current context, Memory, and Knowledge.
- Give tools least privilege, parameter validation, error categories, idempotency, and approval.
- Design offline unit tests, trajectory evaluation, real-model experiments, and production gates.
- Recognize documentation/package drift and verify APIs instead of guessing.

## Prerequisites

- Python functions, classes, decorators, type hints, exceptions, JSON, and basic <code>unittest</code>.
- An understanding that LLM calls cost money and have variable output, plus basic Tool Calling and Agent loops.
- The ability to create a virtual environment in Windows 11 PowerShell 7.

## Installation path: start with venv + pip

Do not create <code>.venv</code> inside the Obsidian vault. In a separate practice-project directory, the following uses a compatible Python 3.13:

~~~powershell
py -3.13 -m venv .venv  # Create an isolated environment in this practice directory with compatible Python 3.13.
.\.venv\Scripts\Activate.ps1  # Activate it so subsequent python and pip commands use .venv.
python -m pip install --upgrade pip  # Upgrade pip inside the environment first to avoid old-resolver installation issues.
python -m pip install "crewai==1.15.4"  # Install the CrewAI baseline actually validated by this course.
python -c "from importlib.metadata import version; print(version('crewai'))"  # Read and confirm the installed distribution version.
~~~

Install an extra tool set only when the task truly needs it:

~~~powershell
python -m pip install "crewai[tools]==1.15.4"  # Install optional dependencies only when a course task needs the extra tool set.
~~~

<code>1.15.4</code> is this course’s tested runtime baseline, not the latest package observed on 2026-07-21. If a new project adopts <code>1.15.5</code> or a later release, recheck PyPI, release notes, and Python constraints, then rerun minimal-import and integration tests on that exact version. The official installation guidance currently emphasizes <code>uv</code> and the CrewAI CLI. Once you understand <code>venv + pip</code>, use the official documentation to manage a project with <code>uv</code>, but do not casually mix two locking sources in one environment.

> [!warning] Decide telemetry policy before running
> CrewAI’s current PyPI telemetry description says that the framework sends anonymous usage telemetry by default. Its scope includes CrewAI/Python/OS versions, Agent/Task counts, process, memory/delegation, parallelism, models, roles, and tool names. The vendor states that prompts, Task bodies, backstories/goals, API calls, and responses are not collected by default. Setting <code>share_crew=True</code> additionally shares detailed execution data such as <code>goal</code>, <code>backstory</code>, <code>context</code>, and Task <code>output</code>.
>
> For private code, customer data, or regulated environments, complete a privacy review first and disable unnecessary outbound telemetry by default. Prefer the CrewAI-specific <code>CREWAI_DISABLE_TELEMETRY=true</code>; <code>OTEL_SDK_DISABLED=true</code> also disables other OpenTelemetry instrumentation in the same process. AMP tracing has its own configuration, so disabling anonymous telemetry does not prove that every trace is disabled. In pinned <code>1.15.4</code>, instance-level <code>tracing=False</code> is the explicit override; an environment value of <code>false</code> can still fall back to locally saved consent. A production deployment should record and test whether telemetry is disabled, permitted, or routed to an owned exporter. Do not use <code>share_crew=True</code> as a debugging shortcut.

Real model providers commonly require credentials. This course does not provide, read, or validate real keys. Use environment variables or a secret-management service only in a separate project; never place values in YAML, Markdown, test fixtures, or Git.

## Recommended order

1. [[crewai/01-core-objects-crew-agent-task-and-process|Core Objects: Crew, Agent, Task, and Process]]: installation snapshot, object responsibilities, Task contracts, and Process choice.
2. [[crewai/02-flow-state-and-events|Flow, State, and Events]]: use <code>start</code>, <code>listen</code>, <code>router</code>, structured state, and persistence to control a workflow.
3. [[crewai/03-tool-boundaries-and-structured-output|Tool Boundaries and Structured Output]]: tool permissions, Pydantic output, and guardrails.
4. [[crewai/04-memory-knowledge-and-context|Memory, Knowledge, and Context]]: distinguish data lifecycles, storage, and authority.
5. [[crewai/05-testing-evaluation-and-observability|Testing, Evaluation, and Observability]]: move from deterministic testing to multi-trial online evaluation.
6. [[crewai/06-safety-failure-recovery-and-production-boundaries|Safety, Failure Recovery, and Production Boundaries]]: checkpoints, idempotency, sandboxes, and deployment gates.
7. [[crewai/07-project-offline-research-brief-flow|Project: Offline Research-Brief Flow]]: run, test, and adapt a standard-library project.
8. [[crewai/08-project-real-crewai-persistent-flow|Project: Real CrewAI Persistent Flow]]: validate the pinned runtime, SQLite state hydration, forks, and receipt-after-crash recovery.

## Hands-on projects

Layer A uses three deterministic Task stubs to simulate research, writing, and review, then lets an outer Flow control the revision budget, terminal states, and publication:

- <code>examples/offline_research_flow.py</code>
- <code>examples/sources.json</code>
- <code>examples/test_offline_research_flow.py</code>

Layer A does not import CrewAI, access the network, or call a model; it tests architecture contracts. Layer B is in <code>examples/crewai_layer_b/</code>. It runs <code>crewai==1.15.4</code> directly and uses nine tests to cover Flow decorators, SQLite persistence, same-UUID hydration, <code>flow_id</code> normalization, fail-closed resume/fork for unknown IDs, operation/payload conflicts, forks, and independent receipts. It still makes no model calls, so it claims only that the runtime control plane was validated—not real-model quality or production concurrency.

## Mastery standard

- [ ] Distinguish a Crew from a Flow in one sentence and name a task each is not suitable for.
- [ ] Set capability and tool boundaries for an Agent and write a verifiable Task artifact.
- [ ] Explain the extra cost and requirements of sequential and hierarchical Processes.
- [ ] Control loops and terminal states with structured state and bounded routing.
- [ ] Distinguish Memory, Knowledge, state, and per-turn context.
- [ ] Send writing tools through execution-layer validation, approval, and idempotency protection.
- [ ] Run offline tests in normal, <code>-O</code>, and warnings-as-errors modes.
- [ ] Run real Flow recovery tests in a pinned dependency environment and distinguish a state UUID from a business operation ID.
- [ ] Record package version, page labels, model, tool schema, data, and evaluation-set versions.

## Relationship to other courses

- [[agentic-design-patterns/00-index|Agentic Design Patterns]] supplies framework-independent patterns for routing, parallelism, approval, recovery, and evaluation.
- [[langchain/00-index|LangChain]] and LangGraph provide another set of component and state-orchestration abstractions. Compare them using the same task set, model, and cost accounting.
- [[mcp/00-index|MCP]] can expose remote tools to an Agent, but a protocol connection does not mean that a tool is authorized or trustworthy.
- CrewAI covers only part of the runtime; LLMOps, monitoring, security, and governance still require separate engineering.

## Primary references

- [PyPI: current crewai release](https://pypi.org/project/crewai/) (latest observed: 1.15.5, released 2026-07-20; checked 2026-07-21) and [PyPI: crewai 1.15.4](https://pypi.org/project/crewai/1.15.4/) (the tested baseline, release date, and Python constraints).
- [CrewAI Telemetry](https://docs.crewai.com/en/telemetry) (default anonymous telemetry, <code>share_crew</code>, <code>CREWAI_DISABLE_TELEMETRY</code>, and the global OTel boundary; checked 2026-07-21).
- [CrewAI documentation home](https://docs.crewai.com/) and [llms.txt](https://docs.crewai.com/llms.txt) (page index; checked 2026-07-21).
- [CrewAI official repository](https://github.com/crewAIInc/crewAI) and [Releases](https://github.com/crewAIInc/crewAI/releases) (source and release information; checked 2026-07-21).
- [Agents](https://docs.crewai.com/en/concepts/agents), [Tasks](https://docs.crewai.com/en/concepts/tasks), [Crews](https://docs.crewai.com/en/concepts/crews), [Processes](https://docs.crewai.com/en/concepts/processes), [Flows](https://docs.crewai.com/en/concepts/flows), and [Human Feedback in Flows](https://docs.crewai.com/en/learn/human-feedback-in-flows) (dynamic official documentation; see the version note for page-specific labels).
