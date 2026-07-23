---
title: "Capability Contracts and the Selection Object"
tags:
  - llm
  - model-selection
  - capability-contract
aliases:
  - Defining the model-selection problem
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: 现代LLM能力与模型选择/01-能力契约与选择对象.md
translation_source_hash: 216ae330037771c157a90a624c680ed03e7cd2635401e72399f59a2a108303bb
translation_route: zh-CN/现代LLM能力与模型选择/01-能力契约与选择对象
translation_default_route: zh-CN/现代LLM能力与模型选择/01-能力契约与选择对象
---

# Capability Contracts and the Selection Object

## Goal

Rewrite “choose a good model” as a verifiable task, system boundary, and candidate change unit.

## Core concepts

A **capability contract** is not a vendor feature list. It is observable behavior a model must satisfy for a specified input distribution, invocation configuration, and runtime. A minimum contract includes:

| Dimension | Question that must be specified | Verifiable evidence |
| --- | --- | --- |
| task | What must the user actually accomplish? What is the cost of failure? | Cases, expected outcomes, severity |
| input | What languages, lengths, modalities, dirty values, and adversarial inputs occur? | Frozen samples and slices |
| output | Free text, a schema, citations, or a tool proposal? | Validator, rubric, final environment state |
| system | How are the prompt, RAG, tools, budget, and retries fixed? | Harness version and configuration hash |
| operations | What are the latency, throughput, cost, region, retention, and SLA requirements? | Telemetry and contract evidence |
| change unit | Are you comparing model weights, a model ID, or a complete system version? | Rollback-capable release manifest |

The model, prompt, tool descriptions, sampling parameters, and retriever interact. If they change at the same time, a difference cannot be attributed to the model.

### The selection object must be reidentifiable

A model alias in a request is not necessarily a fixed snapshot: some vendors point `latest` at a replaceable current version, while others pin a version ID to a model snapshot. Even when weights do not change, routing, safety layers, or other service infrastructure can change observable behavior. Therefore do not write only “we used model X” in a report. For every trial, record at least the requested model identifier; the actual model/version returned in the response when the API provides it; the endpoint/region; the API/adapter version; the date; and the sampling configuration. After a model lifecycle, capability claim, or runtime control-plane change, rerun the contract tests instead of carrying forward the old conclusion.

## Why this matters

Public benchmarks cover only limited scenarios. HELM is useful because it makes scenarios, metrics, and gaps explicit, not because it offers an overall ranking ready for procurement. Your task may involve internal terminology, special permissions, and real side effects; public averages cannot replace evidence about those conditions.

Establish a non-LLM baseline first as well: rules, search, a smaller model, or a fixed workflow. If it already meets quality and risk requirements, a stronger model may not deliver a net benefit.

## How to implement it

Start with a one-page `decision brief`:

```yaml
decision: Choose a generative model for ticket routing and constrained tool proposals  # State the business scenario this decision serves in one sentence.
unit: pinned-model-id + prompt-v7 + tool-schema-v3  # Pin the model, prompt, and tool contract together instead of comparing model names only.
must:  # List hard constraints; failing any one prevents a candidate from qualifying.
  - Chinese ticket structured output passes JSON Schema  # Require an output shape that software can validate first.
  - Propose tools only from an allowlist  # Keep the model from inventing or exceeding authorized tool choices.
  - Data is not used for training and is retained no longer than the agreed number of days  # Express data-processing commitments as verifiable conditions.
measure:  # List raw metrics to collect while comparing candidates.
  - Recall for severe tickets  # Focus on avoiding missed high-impact tickets.
  - Schema pass rate and tool-argument correctness  # Check formatting correctness separately from action-argument correctness.
  - p50/p95 latency and per-trial cost  # Record typical latency, tail latency, and per-run cost.
gate:  # Set minimum thresholds that determine whether evaluation can continue.
  - task_success >= 0.75  # A task-success rate below this value cannot advance to the next selection stage.
  - structured_output_valid >= 0.95  # Enable this threshold only when structured output is a required capability.
  - tool_success >= 0.90  # Enable this threshold only when tool calling is a required capability.
baseline: Rule classifier + human handling  # Use a simpler, rollback-capable existing solution as the comparison baseline.
rollback: Return to the previous release manifest  # State exactly which verified release record restores service after failure.
```

Candidate discovery may consult model cards, official catalogs, and public benchmarks, but qualification requires your own contract and hard gates. `capabilities: [structured-output]` means only that a candidate is worth probing; it cannot replace a measured schema-pass rate.

## Common failures

- Replacing the task and failure definition with “stronger general intelligence.”
- Treating a model name as the selection object while using different prompts, retries, or tools for candidates.
- Evaluating with a `latest` or preview alias, then treating it as a reproducible long-lived fixed version.
- Comparing only with other LLMs and omitting a rules or human baseline.
- Treating a successful demo as proof of capability without frozen cases and failure slices.
- Failing to pin the model ID, date, and serving configuration, leaving results irreproducible.

## How to validate

Ask someone who did not design the brief to answer, using only the brief: Which candidates will be eliminated? Which metrics determine release? How can the evaluation be rerun? How can it roll back? If the answers require verbal clarification, the contract is incomplete.

## Practice task

Choose one real Agent step. Write 10 typical cases, 5 difficult cases, 3 prohibited actions, and one non-LLM baseline. Specify outcome evidence for each case; “feels better” is not allowed.

## References

- [HELM](https://crfm.stanford.edu/helm/index.html)
- Liang et al., [Holistic Evaluation of Language Models](https://arxiv.org/abs/2211.09110)
- Mitchell et al., [Model Cards for Model Reporting](https://doi.org/10.1145/3287560.3287596)
- [Gemini API model version naming](https://ai.google.dev/gemini-api/docs/models): examples of the change semantics of stable, preview, `latest`, and experimental models.
- [Claude model IDs and versions](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions): examples of the boundary between a pinned model ID and service infrastructure that may still change.
