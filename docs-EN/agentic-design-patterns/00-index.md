---
title: "Agentic Design Patterns"
aliases:
  - Agentic Design Patterns Learning Path
english_title: Agentic Design Patterns Documentation Index
source_url: https://github.com/xindoo/agentic-design-patterns/tree/effb52f1730913be650a04e5ffb251c093096894/chapters
source_path: chapters/README.md
overview_source_url: https://github.com/xindoo/agentic-design-patterns/blob/effb52f1730913be650a04e5ffb251c093096894/chapters/Agentic%20Design%20Patterns.md
overview_source_path: chapters/Agentic Design Patterns.md
source_commit: effb52f1730913be650a04e5ffb251c093096894
retrieved: 2026-06-15
source_checked: 2026-07-22
tags:
  - agentic-design-patterns
  - ai-agent
  - design-patterns
  - index
ai_learning_stage: 5. Single Agent and Tools
ai_learning_order: 34
ai_learning_schema: 2
ai_learning_id: agentic-design-patterns
ai_learning_domain: agent-runtime
ai_learning_catalog_order: 3400
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 700
ai_learning_track_agent_app_kind: optional
ai_learning_track_agent_platform_order: 700
ai_learning_track_agent_platform_kind: optional
content_tier: practice-reference
difficulty: intermediate
estimated_hours: 6-10
content_origin: mixed
content_status: dynamic
reference_layer_status: frozen-reference
reference_layer_license: unknown
lang: en
translation_key: Agentic Design Patterns/00-目录.md
translation_source_hash: bdf6fcef1f1f3d1ec4b5b2edc480cbadd9eafa8e73e26814048aba9164fabeb7
translation_route: zh-CN/Agentic-Design-Patterns/00-目录
translation_default_route: zh-CN/Agentic-Design-Patterns/00-目录
---

# Agentic Design Patterns

## About this knowledge base

*Agentic Design Patterns: A Hands-on Guide to Building Intelligent Systems* is written by [Antonio Gulli](https://www.linkedin.com/in/searchguy/). This knowledge tree preserves the 21 core patterns, seven appendices, reference materials, and related assets imported from the Chinese translation of `xindoo/agentic-design-patterns` at a fixed commit. It adds an original seven-lesson beginner route and an offline-verifiable project that turn the reference material into practical choices about architecture, authorization, recovery, and evaluation.

> [!info] Source and version
>
> - Repository: <https://github.com/xindoo/agentic-design-patterns>
> - Fixed commit: [`effb52f1730913be650a04e5ffb251c093096894`](https://github.com/xindoo/agentic-design-patterns/commit/effb52f1730913be650a04e5ffb251c093096894)
> - Source directory: <https://github.com/xindoo/agentic-design-patterns/tree/effb52f1730913be650a04e5ffb251c093096894/chapters>
> - Retrieved: 2026-06-15
> - License status: the fixed repository root declares neither LICENSE nor COPYING. This course therefore makes no redistribution-license inference.

> [!important] Boundary between two content layers
>
> `upstream-references` and their adjacent source assets are frozen public-reference material from the fixed commit and are not rewritten here. `beginner-route` is an original course organized for this learning path; its protocol, authorization, approval, and recovery boundaries were checked against current primary specifications on 2026-07-22. Examples in the frozen layer can change with upstream library versions and must not be treated as current API guarantees.

> [!note] Scope alongside Agent Core
>
> [[agent-core/00-index|Agent Core]] is the canonical route for state, context/memory, planning and termination, checkpoint/idempotency, approval, untrusted observations, and runtime control. This course does not redefine those basics in parallel. Learners who already know Agent Core can use lessons 3–6 here as a pattern map and review, focusing on combined structures such as routing, parallelism, reflection, planner/evaluator, and “when not to add an Agent.” The frozen translation stays reference material only.

## Place in the overall learning path

This course belongs to the “single Agent and tools” stage. Before entering it, learn Tool Calling and the Agent Core state loop; then use patterns to compose routing, parallelism, reflection, planning, memory, human approval, recovery, and evaluation into a controlled system. This is a recommended bridge, not a claim that every role must finish two entire courses first. The course answers “which structure should I choose, and when?” rather than binding you to one framework.

## Boundary between patterns and protocols

“Tools,” “delegation,” and “recovery” here are architectural patterns. When interoperability is required, choose a protocol based on whether the remote party is a **capability** or an **independent Agent application**. The three can coexist, but none replaces authorization, approval, idempotency, or outcome acceptance outside the model.

| Boundary | Learn or adopt first | What it solves | What the application still owns |
| --- | --- | --- | --- |
| In-process or owned-backend capability | [[tool-calling-function-calling/00-index\|Tool Calling]] | Model proposes constrained calls; runtime schedules a local handler | Actual principal, object-level authorization, approval, idempotency, receipt |
| Standardized tools, resources, and context connection | [[mcp/00-index\|MCP]] | Capability, transport, and authorization protocol between host/client/server | Mapping protocol capability to business policy; validating call/resource results |
| Independent and possibly opaque Agent application | [[a2a/00-index\|A2A]] | Discovery, tasks, state, and multi-turn Agent-to-Agent collaboration | Delegation scope, tenant/principal, remote task access, approval, outcome acceptance |

For example, a maintenance Agent might delegate to a supplier Agent with A2A while each uses MCP or ordinary Tool Calling internally. This illustrates layered responsibilities; it does not mean every system should introduce both protocols. See the protocol-boundary explanations in [[a2a/00-index|A2A]] and [[mcp/00-index|MCP]].

## Learning objectives

- Choose the lowest-complexity solution among deterministic workflow, single Agent, and multi-Agent systems.
- Draw state, branches, tool permission, stopping conditions, and failure paths.
- Require human approval for high-risk actions and add checkpoints, retry, and idempotency keys to long tasks.
- Evaluate a system with task success, cost, latency, safety-violation, and human-takeover rates.

## Prerequisites

- Be able to read basic Python functions, JSON state, and HTTP requests. You can start without concurrency programming.
- [[agent-core/00-index|Agent Core]] and [[tool-calling-function-calling/00-index|Tool Calling and Function Calling]] are recommended; framework knowledge is not required.

## Recommended beginner sequence

1. [[agentic-design-patterns/beginner-route/01-pattern-selection-and-minimal-architecture|Pattern Selection and Minimal Architecture]] — decide first whether an Agent is needed at all.
2. [[agentic-design-patterns/beginner-route/02-routing-parallelism-and-joining|Routing, Parallelism, and Joining]] — master the most common deterministic compositions.
3. [[agentic-design-patterns/beginner-route/03-reflection-planning-and-stopping-conditions|Reflection, Planning, and Stopping Conditions]] — give iteration a budget and an exit.
4. [[agentic-design-patterns/beginner-route/04-tools-memory-and-state-boundaries|Tools, Memory, and State Boundaries]] — define responsibility for external actions and persistent data.
5. [[agentic-design-patterns/beginner-route/05-human-approval-and-safety-boundaries|Human Approval and Safety Boundaries]] — stop irreversible actions behind an authorization gate.
6. [[agentic-design-patterns/beginner-route/06-failure-recovery-evaluation-and-observability|Failure Recovery, Evaluation, and Observability]] — use evidence to decide whether the system is reliable.
7. [[agentic-design-patterns/beginner-route/07-project-recoverable-task-workflow|Project: Recoverable Task Workflow]] — finish a key-free offline project.

## How to use the reference layer

1. Complete the seven beginner lessons first; beginners do not need to read the large reference layer front to back.
2. Use the reference-layer links in lessons for the relevant chapter, then expand to multi-Agent, RAG, safety, and evaluation as needed.
3. Framework or product material in appendices is tied to a fixed upstream version; check current official documentation before use.
4. Use the glossary, term index, and FAQ to revisit ideas; do not treat opinions in a translation as the sole engineering specification.

## Frozen reference layer: core patterns

- [[agentic-design-patterns/upstream-references/section-01/reference-01-2096542b|Chapter 1: Prompt Chaining]]
- [[agentic-design-patterns/upstream-references/section-01/reference-02-309c9286|Chapter 2: Routing]]
- [[agentic-design-patterns/upstream-references/section-01/reference-03-3c744b3e|Chapter 3: Parallelization]]
- [[agentic-design-patterns/upstream-references/section-01/reference-04-723b19d0|Chapter 4: Reflection]]
- [[agentic-design-patterns/upstream-references/section-01/reference-05-55ea9480|Chapter 5: Tool Use]]
- [[agentic-design-patterns/upstream-references/section-01/reference-06-0f14c0e3|Chapter 6: Planning]]
- [[agentic-design-patterns/upstream-references/section-01/reference-07-3da9af34|Chapter 7: Multi-Agent Collaboration]]
- [[agentic-design-patterns/upstream-references/section-01/reference-08-37694282|Chapter 8: Memory Management]]
- [[agentic-design-patterns/upstream-references/section-01/reference-09-0c07af01|Chapter 9: Learning and Adaptation]]
- [[agentic-design-patterns/upstream-references/section-01/mcp-89aae3f4|Chapter 10: Model Context Protocol (MCP)]]
- [[agentic-design-patterns/upstream-references/section-01/reference-11-b5ffee0a|Chapter 11: Goal Setting and Monitoring]]
- [[agentic-design-patterns/upstream-references/section-01/reference-12-61cdc65d|Chapter 12: Exception Handling and Recovery]]
- [[agentic-design-patterns/upstream-references/section-01/reference-13-5273fb19|Chapter 13: Human–Machine Collaboration]]
- [[agentic-design-patterns/upstream-references/section-01/rag-f15ced59|Chapter 14: Knowledge Retrieval (RAG)]]
- [[agentic-design-patterns/upstream-references/section-01/a2a-e6dae401|Chapter 15: Agent-to-Agent Communication (A2A)]]
- [[agentic-design-patterns/upstream-references/section-01/reference-16-8f6a3d13|Chapter 16: Resource-Aware Optimization]]
- [[agentic-design-patterns/upstream-references/section-01/reference-17-9b558c3e|Chapter 17: Reasoning Techniques]]
- [[agentic-design-patterns/upstream-references/section-01/reference-18-de2d72c3|Chapter 18: Guardrail and Safety Patterns]]
- [[agentic-design-patterns/upstream-references/section-01/reference-19-9f8e599b|Chapter 19: Evaluation and Monitoring]]
- [[agentic-design-patterns/upstream-references/section-01/reference-20-21fc4355|Chapter 20: Prioritization]]
- [[agentic-design-patterns/upstream-references/section-01/reference-21-b87566e1|Chapter 21: Exploration and Discovery]]

## Frozen reference layer: appendices

- [[agentic-design-patterns/upstream-references/section-02/reference-01-4f001232|Appendix A: Advanced Prompting Techniques]]
- [[agentic-design-patterns/upstream-references/section-02/ai-gui-77c963b4|Appendix B: AI Agent Interaction from GUI to Real-World Environments]]
- [[agentic-design-patterns/upstream-references/section-02/agentic-4b6d888c|Appendix C: Rapid Overview of Agentic Frameworks]]
- [[agentic-design-patterns/upstream-references/section-02/agentspace-65fa3ae7|Appendix D: Building Agents with AgentSpace]]
- [[agentic-design-patterns/upstream-references/section-02/ai-agent-358ed3e7|Appendix E: AI Agents in the Command Line]]
- [[agentic-design-patterns/upstream-references/section-02/reference-06-75c54855|Appendix F: Internals of an Agent Reasoning Engine]]
- [[agentic-design-patterns/upstream-references/section-02/reference-07-dcac094b|Appendix G: Coding Agents]]

## Frozen reference layer: reference material

- [[agentic-design-patterns/upstream-references/section-03/reference-01-6c5cc709|Conclusion]]
- [[agentic-design-patterns/upstream-references/section-03/reference-02-d6866ccb|FAQ]]
- [[agentic-design-patterns/upstream-references/section-03/reference-03-575320a4|Glossary]]
- [[agentic-design-patterns/upstream-references/section-03/reference-04-d37c230d|Term Index]]

## Upstream chapter notes

The upstream `chapters/README.md` says this directory stores translated chapter files, requires UTF-8, preservation of Markdown structure, correct code-block language identifiers, and image references to the repository `images/` directory. The local import follows those principles and stores images in sibling `attachments/` directories under the vault convention.

> [!note] Original README
>
> The upstream README has 21 lines. Its operational guidance is consolidated above rather than copied into a duplicate document.

## Hands-on entry

- Complete each lesson's paper design, then build [[agentic-design-patterns/beginner-route/07-project-recoverable-task-workflow|the Recoverable Task Workflow]].
- Offline script: `beginner-route/examples/resilient_workflow.py`. Tests: `beginner-route/examples/test_resilient_workflow.py`. They use only the Python standard library and verify strict checkpoints, routing, parallel join without shared writes, approval binding, classified retry, idempotent receipts, and post-commit-crash recovery.

## Mastery standard

- [ ] Given a new request, I can explain why to choose a workflow, single Agent, or multi-Agent system.
- [ ] I can write maximum steps, completion criteria, and failure criteria for a loop.
- [ ] I can distinguish retryable fault, business rejection, and an exception needing human intervention.
- [ ] I can design an offline replay set and give quality, cost, latency, and safety thresholds.
- [ ] I can prove approval binds the current action and repeated recovery does not repeat a side effect.
- [ ] I can inspect both trace and final environmental state rather than only an Agent's text claim.

## Relationships to other knowledge bases

- [[langchain/00-index|LangChain]] supplies high-level components; LangGraph can express explicit state, pause, and recovery. Check current official API documentation for implementation details.
- [[crewai/00-index|CrewAI]] offers collaboration and flow implementations; first define the state, permission, and acceptance constraints in this course.
- [[multi-agent-collaboration/00-index|Multi-Agent Collaboration]] goes deeper on roles, handoffs, and communication. Add Agents only when isolation or coordination benefit is evidenced.
- [[mcp/00-index|MCP]] owns protocol interoperability for tools, resources, and context. It does not grant business-action permission or replace this course's approval, receipt, and recovery contracts.
- [[a2a/00-index|A2A]] owns discovery, tasks, and collaboration among independent Agent applications. Use it only when cross-product, cross-framework, or cross-organization delegation has clear benefit, and reauthorize remote tasks and artifacts on each request.
- [[evaluation-framework/00-index|Evaluation Framework]] and [[ai-safety/00-index|AI Safety]] are production-depth paths after this offline project: the former expands statistical and release evidence, while the latter expands identity, object-level authorization, supply chain, and incident response.
- Choose patterns before frameworks. Preserve state, permission, evaluation, and recovery constraints when migrating frameworks.

## Primary references

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) — workflows, Agents, and composition patterns; checked 2026-07-14.
- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) — tools, orchestration, and guardrails; checked 2026-07-14.
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — tasks, trials, traces, and outcomes; checked 2026-07-14.
- [LangGraph: Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) and [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) — dynamic implementation documentation; checked 2026-07-14.
- [MCP 2025-11-25: Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) — HTTP authorization, resource/audience, and no token passthrough; checked 2026-07-22.
- [A2A 1.0: A2A and MCP](https://a2a-protocol.org/latest/topics/a2a-and-mcp/) and [A2A 1.0 specification](https://a2a-protocol.org/latest/specification/) — independent-Agent collaboration and per-request authorization; checked 2026-07-22.
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) — a starting point for security risk; checked 2026-07-14.
- [ReAct](https://arxiv.org/abs/2210.03629), [Reflexion](https://arxiv.org/abs/2303.11366), [Plan-and-Solve](https://arxiv.org/abs/2305.04091), and [Toolformer](https://arxiv.org/abs/2302.04761) — checked 2026-07-14.
- The fixed-commit Chinese translation is reference-layer material; its license status is limited to the source-and-version note above.
