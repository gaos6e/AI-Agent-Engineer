---
title: "Prompt Engineering"
tags:
  - ai-agent-engineer
  - prompt-engineering
  - learning-path
aliases:
  - Prompt Engineering course index
  - Prompt Engineering learning path
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline:
  - OpenAI Prompt engineering and Structured Outputs guides
  - Anthropic Prompt engineering overview
  - Google Gemini Prompt design strategies
  - JSON Schema 2020-12 documentation
  - OpenAI reusable-prompts and Evals-platform deprecation notices
  - Anthropic prompt-injection mitigation guide
  - Perez and Ribeiro prompt-injection paper
ai_learning_stage: 3. LLM Application Foundations
ai_learning_order: 19
ai_learning_schema: 2
ai_learning_id: prompt-engineering
ai_learning_domain: model-and-context
ai_learning_catalog_order: 1900
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 200
ai_learning_track_agent_app_kind: core
ai_learning_track_rag_order: 200
ai_learning_track_rag_kind: core
ai_learning_track_agent_platform_order: 200
ai_learning_track_agent_platform_kind: core
lang: en
translation_key: 提示词工程/00-目录.md
translation_source_hash: 3e55615cdd9c52514ca2e4a67dcae58a5c79d5f456f2a92326a62274446d88ea
translation_route: zh-CN/提示词工程/00-目录
translation_default_route: zh-CN/提示词工程/00-目录
---

# Prompt Engineering

> [!warning] Source-check date
> This material was checked on **2026-07-21**. Prompting strategies evolve with models, APIs, and safety mechanisms. This knowledge base separates transferable engineering methods from provider-specific behavior. Before using an online model, recheck the current documentation for the selected provider and validate it against your own evaluation set.

## Course overview

Prompt engineering is not a search for a magic phrase. It is the work of expressing a business goal as a testable input contract: define the task, input boundary, constraints, output format, and success criteria, then validate them with representative examples. Transferable methods include task definition, separating data from instructions, contract validation, version management, and evaluation. Role names, supported schema features, prompt caching, and hosting mechanisms can vary by provider and model. A prompt cannot replace correct data, model selection, retrieval, access control, or programmatic validation.

## Where this fits in the overall path

This course belongs to the LLM Application Foundations stage. After learning the basics of APIs, JSON, and Markdown, use [[modern-llm-capabilities-and-model-selection/00-index|Modern LLM Capabilities and Model Selection]] to define the required capabilities and hard gates, then learn here how to communicate an intent precisely. Continue with [[context-engineering/00-index|Context Engineering]] to organize evidence and state, and [[llm-api-integration/00-index|LLM API Integration]] to connect prompts to reliable software.

## Learning objectives

- Turn an ambiguous request into a task statement with success criteria.
- Use roles, delimiters, examples, and counterexamples correctly, and identify which practices are provider-specific.
- Constrain machine-readable output with JSON Schema or an equivalent contract, then continue validating semantics in application code.
- Version prompt templates and drive iterations with fixed cases and metrics.
- Recognize prompt injection and establish a trust boundary between instructions and untrusted data.

## Prerequisites

- Read basic Markdown, JSON, and Python.
- Understand the basic idea of HTTP requests and responses.
- No machine-learning mathematics background or model API key is required.

## Recommended order

1. [[prompt-engineering/01-task-definition-instruction-hierarchy-and-boundaries|Task definition, instruction hierarchy, and boundaries]]: define success before writing instructions.
2. [[prompt-engineering/02-zero-shot-examples-and-counterexamples|Zero-shot prompting, examples, and counterexamples]]: learn when examples help and how to avoid example bias.
3. [[prompt-engineering/03-structured-output-and-contracts|Structured output and contracts]]: make output safe for programs to consume.
4. [[prompt-engineering/04-templates-variables-and-version-management|Templates, variables, and version management]]: turn a one-off prompt into a maintainable asset.
5. [[prompt-engineering/05-evaluation-driven-iteration|Evaluation-driven iteration]]: use evidence, not impressions, to decide whether a change improves the task.
6. [[prompt-engineering/06-prompt-injection-and-trust-boundaries|Prompt injection and trust boundaries]]: treat external text as data and minimize possible impact.
7. [[prompt-engineering/07-prompt-experiment-project-and-self-check|Prompt experiment project and self-check]]: complete an offline classification-contract experiment.

## Hands-on entry point

Start with the [[prompt-engineering/07-prompt-experiment-project-and-self-check|prompt experiment project]]. It includes an [[prompt-engineering/examples/prompt_lab.py|offline experiment script]], [[prompt-engineering/examples/cases.json|12 versioned cases]], a [[prompt-engineering/examples/response.schema.json|response schema]], and [[prompt-engineering/examples/test_prompt_lab.py|unit tests]]. It requires neither network access nor credentials. It verifies role separation, strict JSON, version bindings between prompt code and schema, case annotation evidence, fail-closed contract drift, grounded evidence, asset hashes, exit codes, and slice statistics. It does not validate the real quality of any online model.

## Mastery criteria

- Write the input, output, constraints, and refusal conditions for a real task.
- Explain the difference between valid JSON and an output that both matches a schema and is semantically correct.
- Compare two prompt versions with at least ten representative cases; record failures by slice and risk rather than relying only on a global average.
- Explain why a single defensive sentence cannot solve prompt injection, and propose permission, validation, and human-confirmation controls.
- Make template changes, model configuration, and evaluation results traceable to one another.
- Run the course's 19 offline tests and ensure bad responses, malformed cases, or contract drift fail with the specified nonzero status.

## Connections to other knowledge bases

- [[modern-llm-capabilities-and-model-selection/00-index|Modern LLM Capabilities and Model Selection]] determines whether a candidate has the reasoning, structured-output, tool, and modality capabilities that the task requires. Prompting cannot compensate for a missed capability or privacy hard gate.
- [[context-engineering/00-index|Context Engineering]] decides which material enters a prompt, in what order, and within what budget.
- [[llm-api-integration/00-index|LLM API Integration]] handles role mapping, timeouts, retries, streaming events, usage, and logs.
- [[rag/00-index|RAG]] supplies traceable evidence; [[evaluation-framework/00-index|Evaluation Framework]] determines whether a prompt change actually improves task performance.
- [[ai-safety/00-index|AI Safety]] and the authorization system limit impact after failure. [[tool-calling-function-calling/00-index|Tool Calling]] connects validated model suggestions to real actions.

## Primary references

- [OpenAI: Prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering) (accessed 2026-07-21)
- [OpenAI: Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) (accessed 2026-07-21)
- [OpenAI: Deprecations](https://developers.openai.com/api/docs/deprecations) (accessed 2026-07-21)
- [OpenAI: Safety best practices](https://developers.openai.com/api/docs/guides/safety-best-practices) (accessed 2026-07-21)
- [Anthropic: Prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview) (accessed 2026-07-21)
- [Anthropic: Mitigate jailbreaks and prompt injections](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks) (accessed 2026-07-21)
- [Google AI for Developers: Prompt design strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies) (accessed 2026-07-21)
- [JSON Schema: Getting started](https://json-schema.org/learn/getting-started-step-by-step) (accessed 2026-07-21)
- Perez and Ribeiro, [Ignore Previous Prompt: Attack Techniques For Language Models](https://arxiv.org/abs/2211.09527) (original paper)
