---
title: "Context Engineering Learning Path"
tags:
  - ai-agent-engineer
  - context-engineering
  - learning-path
aliases:
  - Context Engineering Index
  - Context Engineering Learning Roadmap
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline:
  - Anthropic Effective context engineering for AI agents
  - OpenAI Conversation State, Compaction, and Prompt Caching guides
  - Anthropic Context Windows and Context Editing documentation
  - Google Gemini Long Context and Context Caching documentation
  - Lost in the Middle original paper
ai_learning_stage: 3. LLM Application Foundations
ai_learning_order: 20
ai_learning_schema: 2
ai_learning_id: context-engineering
ai_learning_domain: model-and-context
ai_learning_catalog_order: 2000
ai_learning_hard_prerequisites:
  - prompt-engineering
ai_learning_track_agent_app_order: 300
ai_learning_track_agent_app_kind: core
ai_learning_track_rag_order: 300
ai_learning_track_rag_kind: core
ai_learning_track_agent_platform_order: 300
ai_learning_track_agent_platform_kind: core
lang: en
translation_key: 上下文工程/00-目录.md
translation_source_hash: 2db0669476fea09d83c9ab0517aa3f34f4d7bb1cf27e916f63b7fd532423ffa2
translation_route: zh-CN/上下文工程/00-目录
translation_default_route: zh-CN/上下文工程/00-目录
---

# Context Engineering

> Sources checked on 2026-07-21. Context windows, pricing, caching, conversation continuation, and compaction capabilities vary by provider, API, and model. For live limits, consult the official documentation, counting interfaces, and usage fields returned by the request.

## Course overview

Context engineering is the engineering discipline of selecting, organizing, compressing, and tracing the full working state for a model decision. It covers more than a user prompt: stable instructions, tool definitions, MCP and tool results, retrieved evidence, message history, structured state, and memory. A prompt primarily answers “what to do”; context must also answer “what to rely on, what state the work is in, and which information is trustworthy and permitted.” Filling a window with an entire database or chat history does not automatically improve understanding. Irrelevant, conflicting, stale, and untraceable information reduces reliability and raises cost.

## Where this course fits

This course follows [[prompt-engineering/00-index|Prompt Engineering]] and precedes [[llm-api-integration/00-index|LLM API Integration]]. It is a shared foundation for RAG, Agent memory, tool-result handling, and long-running conversation management. Complete Prompt Engineering first, then pass the context pack built here to LLM API Integration for a model call.

## Learning objectives

- Distinguish tokens, context windows, and budgets; never present character-count estimates as real token counts.
- Select evidence by relevance, trustworthiness, freshness, and permission, while preserving provenance.
- Design clear context partitions and ordering so that instructions, data, and state do not blur together.
- Distinguish conversation records, structured state, long-term memory, and retrieved material.
- Use just-in-time loading, trimming, summarization, provider compaction, and caching while verifying that important information was not lost.
- Build long-context tests for position effects, conflicts, omissions, and prompt injection.

## Prerequisites

- Read JSON and simple Python.
- Understand the task, input, and output contract in a prompt.
- Embedding or RAG knowledge helps, but is not required to begin this course.

## Recommended order

1. [[context-engineering/01-context-engineering-in-one-guide|Context Engineering: One Guide Is Enough]]: Build a panoramic view through What–Why–How and learn the four practices of writing, selecting, compressing, and isolating.
2. [[context-engineering/02-tokens-context-windows-and-budgets|Tokens, Context Windows, and Budgets]]: Understand capacity, consumption, and reserve headroom.
3. [[context-engineering/03-selection-relevance-and-provenance|Selection, Relevance, and Provenance]]: Decide which information deserves a place in the window.
4. [[context-engineering/04-organization-order-and-trust-boundaries|Organization, Order, and Trust Boundaries]]: Make the boundaries between instructions, evidence, and state legible to the model.
5. [[context-engineering/05-conversation-history-state-and-memory|Conversation History, State, and Memory]]: Manage a multi-turn task instead of replaying chat indefinitely.
6. [[context-engineering/06-trimming-summarization-compression-and-caching|Trimming, Summarization, Compression, and Caching]]: Reduce redundancy without losing key constraints.
7. [[context-engineering/07-long-context-failure-modes-and-evaluation|Long-Context Failure Modes and Evaluation]]: Test position, conflict, omission, and contamination.
8. [[context-engineering/08-context-pack-project-and-self-test|Context Pack Project and Self-Test]]: Implement a deterministic budget selector.

## Hands-on project

Complete the [[context-engineering/08-context-pack-project-and-self-test|Context Pack project]]. It consists of the [[context-engineering/examples/context_budget.py|deterministic selector]], [[context-engineering/examples/chunks.json|versioned fixture]], [[context-engineering/examples/context-pack.schema.json|output schema]], and [[context-engineering/examples/test_context_budget.py|unit tests]]. In order, it applies permission, trust, date, deduplication, and budget gates, and records an explicit reason for every exclusion.

## Mastery criteria

- Draw the context sources and trust boundaries for an Agent request.
- Allocate a budget across inputs, outputs, and safety headroom, then calibrate estimates with a provider’s real token and usage data.
- Explain why the most relevant chunk may not be the most trustworthy or most current.
- Distill conversation history into verifiable task state while retaining commitments and open questions.
- Design regression tests for evidence at the beginning, middle, and end; conflicting sources; and summary omissions.
- Run all 18 offline tests and show that required context fails closed when it cannot pass a permission or budget gate, and that deduplication cannot cross section, permission, or trust boundaries.

## Relationships to other courses

- [[prompt-engineering/00-index|Prompt Engineering]] defines the task and output contract; context engineering supplies evidence and state.
- [[llm-api-integration/00-index|LLM API Integration]] maps partitioned content to messages or content blocks and collects usage and caching information.
- [[rag/00-index|Retrieval-Augmented Generation (RAG)]] and [[reranking/00-index|Reranking]] determine how candidate evidence is recalled and ranked; [[agent-core/00-index|Agent Core]] determines how state advances.
- [[privacy-computing/00-index|Privacy Computing]] and [[ai-safety/00-index|AI Safety]] determine which content must never enter model context and bound the impact of tool failures.

## Key references

- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (accessed 2026-07-21)
- [OpenAI: Conversation state](https://developers.openai.com/api/docs/guides/conversation-state) (accessed 2026-07-21)
- [OpenAI: Compaction](https://developers.openai.com/api/docs/guides/compaction) (accessed 2026-07-21)
- [OpenAI: Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) (accessed 2026-07-21)
- [Anthropic: Context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows) (accessed 2026-07-21)
- [Google: Long context](https://ai.google.dev/gemini-api/docs/long-context) (accessed 2026-07-21)
- [Google: Context caching](https://ai.google.dev/gemini-api/docs/caching) (accessed 2026-07-21)
- Liu et al., [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172) (original paper)
