---
title: "LangChain"
aliases:
  - LangChain Python Learn
  - LangChain Learning Route
retrieved: 2026-05-07
source_checked: 2026-07-22
tags:
  - langchain
  - python
  - docs/learn
content_origin: mixed
content_status: dynamic
reference_layer_status: frozen-reference
reference_layer_license: MIT
ai_learning_stage: 6. Framework Practice
ai_learning_order: 36
ai_learning_schema: 2
ai_learning_id: langchain
ai_learning_domain: framework-practice
ai_learning_catalog_order: 3600
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 725
ai_learning_track_agent_app_kind: optional
ai_learning_track_rag_order: 1275
ai_learning_track_rag_kind: optional
ai_learning_track_agent_platform_order: 725
ai_learning_track_agent_platform_kind: optional
lang: en
translation_key: "LangChain/00-目录.md"
translation_source_hash: d8ad111ba098ea63f830e289f45e01ed316d9d3cb2916984fb0f816423c495e7
translation_route: zh-CN/LangChain/00-目录
translation_default_route: zh-CN/LangChain/00-目录
---

# LangChain

## About this knowledge base

This knowledge base has two layers. Start with `beginner-route/` to build an end-to-end engineering path from components, LCEL, models, and messages through tools, retrieval, state, LangGraph, and testing. Then consult the official-documentation translations and case studies as needed. Framework APIs change quickly, so the learning priority is stable input/output contracts and control boundaries—not memorizing an import path from one release.

Existing files form a reference layer of official documentation retrieved on fixed dates; `beginner-route/` is the new explanatory layer for learners starting from zero. Keeping the layers separate preserves provenance and licensing while letting dependency upgrades focus review on executable boundaries.

> [!info] Current version baseline
> At the 2026-07-22 review, PyPI listed `langchain 1.3.14` (2026-07-16), `langgraph 1.2.9` (2026-07-10), and `langchain-core 1.5.0` (2026-07-21). These figures describe this material snapshot only; they do not mean the three packages can be combined arbitrarily outside dependency resolution. New projects should install in an isolated environment, generate a lockfile, and run tests. The LCEL, retrieval, and `create_agent` exercises that pin `langchain-core==1.4.9` retain their verified teaching contract and must not be replaced blindly merely because the latest core release changed. The existing official translations were retrieved on 2026-05-07 and may predate the current API, so treat them as a reference layer rather than copy-paste instructions that need no review.

> [!warning] A frozen reference layer is not a directly executable tutorial
> `01-Learn.md` and the existing translations under numbered sections `01`–`06` retain their original sources, retrieval dates, and licenses for conceptual orientation and historical comparison. Complete `beginner-route/` first. Before copying an import, model ID, provider parameter, or production-deployment pattern from those pages, return to the linked current official documentation and the project lockfile. In particular, never treat illustrative RAG, SQL, Deep Agents, or multi-agent reference code as proof that authorization, evaluation, or production validation is complete.

> [!warning] Bedrock model lifecycle
> The legacy/retirement-migration window includes the old reference-layer ID `anthropic.claude-3-5-sonnet-20240620-v1:0`; examples now use `anthropic.claude-sonnet-4-6` from the current AWS model card. Bedrock model IDs, regional availability, and `bedrock_converse` support must still be verified in the target account against the [AWS model catalog](https://docs.aws.amazon.com/bedrock/latest/userguide/models.html). Do not treat IDs in these notes as permanent guarantees.

## Position in the overall learning route

This knowledge base belongs to the Framework Practice stage. The foundation LCEL and model units require only the Python, HTTP/JSON, and LLM API concepts listed below. When moving into tools, RAG, or state graphs, add Tool Calling, retrieval, and Agent-state knowledge as appropriate. This is a recommended module-by-module progression, not a claim that LangChain or any upstream full course is a hard prerequisite for every Agent or RAG role. Move down to LangGraph only when a workflow actually needs explicit branching, persistent state, pause-and-resume behavior, or fine-grained orchestration.

## Learning objectives

- Understand the responsibility boundaries among LangChain, LangGraph, `langchain-core` Runnables (LCEL), and Deep Agents.
- Compose deterministic steps with LCEL and decide when ordinary Python, a Runnable, an Agent, or a state graph is appropriate.
- Describe a minimal Agent loop using messages, models, tools, and structured output.
- Connect a retriever to generation while distinguishing short-term state from long-term memory.
- Recognize when LangGraph checkpoints, interrupts, and explicit state graphs are needed.
- Design boundaries for tool permissions, failure recovery, offline evaluation, and production observability.

## Prerequisites

- Python functions, type hints, virtual environments, and exception handling.
- Basic HTTP/JSON and LLM API concepts; prior LangChain experience is not required.
- When using real models, choose a provider and inject credentials through environment variables; this route does not include real secrets.

## Recommended order

1. [[langchain/beginner-route/01-component-map-and-minimal-invocation|Component Map, Environment, and a Minimal LCEL Invocation]]: establish product, version, and composition boundaries.
2. [[langchain/beginner-route/02-models-messages-prompts-and-structured-output|Models, Messages, Prompts, and Structured Output]]: master input/output contracts.
3. [[langchain/beginner-route/03-tools-and-agent-loops|Tools and Agent Loops]]: understand how a model requests external actions.
4. [[langchain/beginner-route/04-retrieval-and-rag-components|Retrieval and RAG Components]]: connect private knowledge to an application.
5. [[langchain/beginner-route/05-memory-state-and-persistence|Memory, State, and Persistence]]: store short- and long-term information correctly.
6. [[langchain/beginner-route/06-langgraph-boundaries-approval-recovery-and-evaluation|LangGraph Boundaries, Approval, Recovery, and Evaluation]]: move into explicit orchestration.
7. [[langchain/beginner-route/07-project-offline-tool-agent-skeleton|Project: Offline Tool-Agent Skeleton]]: verify the core loop without dependencies or keys.
8. [[langchain/beginner-route/10-project-keyless-create-agent-runtime-contract|Project: Keyless `create_agent` Runtime Contract]]: verify messages, tool results, and fail-closed boundaries in a real LangChain harness.
9. [[langchain/beginner-route/08-project-langgraph-recoverable-approval-flow|Project: LangGraph Recoverable Approval Flow]]: verify SQLite checkpoints, interrupts, and cross-process recovery in a real runtime.
10. [[langchain/beginner-route/09-testing-evaluation-and-upgrade-checklist|Testing, Evaluation, and Upgrade Checklist]]: turn a prototype into a regression-tested engineering asset.

- `00-index.md`: this course index.
- [[langchain/upstream-references/learn|01-Learn]]: translated Learn landing page (source: <https://docs.langchain.com/oss/python/learn>).
- `LICENSE-LangChain-docs.md`: [[langchain/upstream-references/license-langchain-docs|LangChain docs MIT License]].
- Documentation-index check: <https://docs.langchain.com/llms.txt>.

## 01-Conceptual Overviews

- [[langchain/upstream-references/conceptual-overviews/langchain-vs-langgraph-vs-deep-agents|01-LangChain vs LangGraph vs Deep Agents]]: understand how LangChain, LangGraph, and Deep Agents differ and when each fits. Source: <https://docs.langchain.com/oss/python/concepts/products>.
- [[langchain/upstream-references/conceptual-overviews/providers-and-models|02-Providers and Models]]: understand how LangChain uses a unified API for models from different providers. Source: <https://docs.langchain.com/oss/python/concepts/providers-and-models>.
- [[langchain/upstream-references/conceptual-overviews/component-architecture|03-Component Architecture]]: learn the LangChain component architecture. Source: <https://docs.langchain.com/oss/python/langchain/component-architecture>.
- [[langchain/upstream-references/conceptual-overviews/memory|04-Memory]]: understand persistence across interactions within and between threads. Source: <https://docs.langchain.com/oss/python/concepts/memory>.
- [[langchain/upstream-references/conceptual-overviews/context|05-Context]]: learn how to provide an AI application with the information and tools it needs to complete a task. Source: <https://docs.langchain.com/oss/python/concepts/context>.
- [[langchain/upstream-references/conceptual-overviews/graph-api|06-Graph API]]: learn LangGraph’s declarative graph-building API. Source: <https://docs.langchain.com/oss/python/langgraph/graph-api>.
- [[langchain/upstream-references/conceptual-overviews/functional-api|07-Functional API]]: build Agents as individual functions. Source: <https://docs.langchain.com/oss/python/langgraph/functional-api>.

## 02-LangChain

- [[langchain/upstream-references/langchain/semantic-search|01-Semantic Search]]: build a PDF-backed semantic search engine with LangChain components. Source: <https://docs.langchain.com/oss/python/langchain/knowledge-base>.
- [[langchain/upstream-references/langchain/rag-agent|02-RAG Agent]]: build a RAG Agent with LangChain. Source: <https://docs.langchain.com/oss/python/langchain/rag>.
- [[langchain/upstream-references/langchain/sql-agent|03-SQL Agent]]: build a SQL Agent that queries databases with human review. Source: <https://docs.langchain.com/oss/python/langchain/sql-agent>.
- [[langchain/upstream-references/langchain/voice-agent|04-Voice Agent]]: build a voice Agent that can listen and speak. Source: <https://docs.langchain.com/oss/python/langchain/voice-agent>.

## 03-LangGraph

- [[langchain/upstream-references/langgraph/custom-rag-agent|01-Custom RAG Agent]]: use LangGraph primitives to build a RAG Agent with fine-grained control. Source: <https://docs.langchain.com/oss/python/langgraph/agentic-rag>.
- [[langchain/upstream-references/langgraph/custom-sql-agent|02-Custom SQL Agent]]: implement a SQL Agent directly with LangGraph for maximum flexibility. Source: <https://docs.langchain.com/oss/python/langgraph/sql-agent>.

## 04-Multi-agent

- [[langchain/upstream-references/multi-agent/subagents-personal-assistant|01-Subagents Personal Assistant]]: build a personal assistant that delegates to subagents. Source: <https://docs.langchain.com/oss/python/langchain/multi-agent/subagents-personal-assistant>.
- [[langchain/upstream-references/multi-agent/handoffs-customer-support|02-Handoffs Customer Support]]: build a customer-support workflow that uses handoffs. Source: <https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs-customer-support>.
- [[langchain/upstream-references/multi-agent/router-knowledge-base|03-Router Knowledge Base]]: build a multi-source knowledge base that routes queries to specialized Agents. Source: <https://docs.langchain.com/oss/python/langchain/multi-agent/router-knowledge-base>.
- [[langchain/upstream-references/multi-agent/skills-sql-assistant|04-Skills SQL Assistant]]: build a SQL assistant that progressively loads specialized skills on demand. Source: <https://docs.langchain.com/oss/python/langchain/multi-agent/skills-sql-assistant>.

## 05-Deep Agents

- [[langchain/upstream-references/deep-agents/data-analysis|01-Data Analysis]]: build a Deep Agent that analyzes data files, creates visualizations, and shares results. Source: <https://docs.langchain.com/oss/python/deepagents/data-analysis>.
- [[langchain/upstream-references/deep-agents/deep-research|02-Deep Research]]: build a multi-step web-research Agent with subagent delegation. Source: <https://docs.langchain.com/oss/python/deepagents/deep-research>.
- [[langchain/upstream-references/deep-agents/content-builder|03-Content Builder]]: build a content-writing Agent with brand memory, skills, subagents, and image-generation capabilities. Source: <https://docs.langchain.com/oss/python/deepagents/content-builder>.

## 06-Additional Resources

- [[langchain/upstream-references/additional-resources/langchain-academy|01-LangChain Academy]]: official courses and exercises; because the in-site Learn sidebar redirects to an external Academy site, this course preserves only the external link and does not fetch its body.
- [[langchain/upstream-references/additional-resources/case-studies|02-Case Studies]]: see how teams use LangChain and LangGraph in production. Source: <https://docs.langchain.com/oss/python/langgraph/case-studies>.
- [[langchain/upstream-references/additional-resources/get-help|03-Get Help]]: connect with the LangChain community, learning resources, and support channels. Source: <https://docs.langchain.com/oss/python/langchain/get-help>.

## Hands-on practice and project entry points

- Every beginner note includes a design exercise; the integrated entry point is [[langchain/beginner-route/07-project-offline-tool-agent-skeleton|the offline tool-agent skeleton]].
- `beginner-route/examples/offline_agent_loop.py` uses only the Python standard library to simulate the loop “model proposes a tool call → executor validates it → tool returns a result → model produces a final answer.”
- `beginner-route/examples/lcel_no_key.py` is an LCEL composition example that needs no model key. The base environment does not keep `langchain-core` installed, but the example was run successfully in isolation with `langchain-core==1.4.9`.
- `beginner-route/examples/test_offline_agent_loop.py` runs deterministic, network-free unit tests for the offline loop.
- `beginner-route/examples/retrieval_layer_b/` pins `langchain-core==1.4.9` and NumPy 2.4.6 compatible with Python 3.11. Its 17 tests cover stable IDs, metadata, tenant filtering before retrieval, `InMemory` raw cosine scores, and Retriever `invoke`/`batch`; the transparent teaching embedding does not prove real semantic-retrieval quality.
- `beginner-route/examples/langchain_layer_b/` runs `create_agent` with pinned `langchain==1.3.14`, `langchain-core==1.4.9`, and `langgraph==1.2.9`. Its eight tests cover success, unknown tools, strict-schema rejection, and fail-closed version drift in normal, `-O`, `-W error`, and `-O -W error` modes. Its scripted model intentionally bypasses provider-schema conversion and cannot replace a real provider smoke test.
- `beginner-route/examples/langgraph_layer_b/` runs `langgraph==1.2.9` directly with a SQLite checkpointer. Its ten tests cover cross-process interrupt/resume, `thread_id` normalization, version/state contract guards, and node replay. It requires no model credentials and does not promise exactly-once external side effects.
- Examples that need real models must still be installed and pinned in a separate `venv`; without provider credentials, do not claim the model has run end to end.

## Mastery criteria

- [ ] Explain the high-level scenarios suited to `create_agent` and when to use LangGraph instead.
- [ ] Distinguish a real LangChain runtime contract from evidence about provider schemas, model quality, authorization, and network integration.
- [ ] Explain the contracts for LCEL’s `RunnableSequence`, `RunnableParallel`, and `invoke`/`batch`/`stream`, without treating legacy `LLMChain` tutorials as the default v1 entry point.
- [ ] Define clear input, error, and permission boundaries for a tool.
- [ ] Distinguish message history, run state, checkpoints, and long-term memory.
- [ ] Design a minimal application with retrieval, citations, human approval, recovery, and offline evaluation.

## Relationship to other knowledge bases

- [[agentic-design-patterns/00-index|Agentic Design Patterns]] answers pattern-selection questions first; this course then maps patterns onto LangChain/LangGraph components.
- [[tool-calling-function-calling/00-index|Tool Calling (including Function Calling)]] explains protocol and executor boundaries; this course shows how they map to `@tool` and an Agent loop.
- [[rag/00-index|Retrieval-Augmented Generation]] explains retrieval quality and generation evaluation; this course focuses on component assembly rather than replacing RAG fundamentals.
- [[crewai/00-index|CrewAI]] emphasizes Crew role collaboration and Flow event processing; do not select between them merely by comparing example length.
- RAG, Tool Calling, and evaluation knowledge bases provide independent fundamentals; a framework does not replace data quality, permissions, or test design.

## Primary references

- [LangChain v1 changes](https://docs.langchain.com/oss/python/releases/langchain-v1), [v1 migration guide](https://docs.langchain.com/oss/python/migrate/langchain-v1), and [versioning policy](https://docs.langchain.com/oss/python/versioning) (checked 2026-07-21).
- [LangChain Agents](https://docs.langchain.com/oss/python/langchain/agents), [Models](https://docs.langchain.com/oss/python/langchain/models), [Tools](https://docs.langchain.com/oss/python/langchain/tools), [Structured output](https://docs.langchain.com/oss/python/langchain/structured-output), [Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval), and [Agent Evals](https://docs.langchain.com/oss/python/langchain/test/evals) (checked 2026-07-21).
- [LangChain Core Runnables API Reference](https://reference.langchain.com/python/langchain-core/runnables) and [Runnable.pipe](https://reference.langchain.com/python/langchain-core/runnables/base/Runnable/pipe) (checked 2026-07-14).
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview), [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts), and [Test](https://docs.langchain.com/oss/python/langgraph/test) (checked 2026-07-21).
- [PyPI: langchain](https://pypi.org/project/langchain/), [PyPI: langchain-core](https://pypi.org/project/langchain-core/), and [PyPI: langgraph](https://pypi.org/project/langgraph/) (version snapshot checked 2026-07-22).
- [[langchain/upstream-references/license-langchain-docs|Existing reference-layer license notice]]; the retrieval date for each existing translation remains in its frontmatter.
