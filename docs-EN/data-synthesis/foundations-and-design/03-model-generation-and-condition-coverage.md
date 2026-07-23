---
title: "Model Generation and Condition Coverage"
aliases:
  - Model-Generated Synthetic Data
  - LLM Data Generation
tags:
  - synthetic-data
  - LLM
  - coverage
source_checked: 2026-07-14
lang: en
translation_key: "数据合成/01-基础与设计/03-模型生成与条件覆盖.md"
translation_source_hash: 3b8265193d6f1384c51010e306c5e901cb9323d520a97895b7a80ed4f5c32b02
translation_route: zh-CN/数据合成/01-基础与设计/03-模型生成与条件覆盖
translation_default_route: zh-CN/数据合成/01-基础与设计/03-模型生成与条件覆盖
---

# Model Generation and Condition Coverage

## Objective

Treat a generative model as a constrained candidate producer. Use condition quotas, structured output, provenance, and independent validation to expand task and linguistic variation.

## Intuition

Asking a model to “generate 1,000 diverse records” often repeats frequent patterns and produces fluent but incorrect labels. A more reliable method lists gaps first, generates one condition cell at a time, and treats model output as an unvalidated proposal.

## Core concepts

- **Seed examples** — a small set of human-confirmed task samples that explain form and boundary.
- **Teacher / generator model** — proposes candidate data; it is not the source of label truth.
- **Conditional generation** — explicitly state language, intent, difficulty, tool state, and risk condition.
- **Quota** — target count to produce or keep for each condition cell.
- **Structured output** — request JSON/Schema to reduce parsing ambiguity, not to guarantee semantic correctness.
- **Model collapse / homogenization risk** — repeated model generation may narrow a distribution or amplify existing patterns.
- **Generator lock-in** — data becomes overly aligned with one model's language and preference.

## Separate generator, oracle, and judge

All three roles can use models, but their evidence responsibility differs. A generator proposes candidates, an oracle defines expected behavior, and a judge decides whether a candidate meets a rubric. Making one call play all three creates circular proof. Prefer rules/simulators for deterministic fields; use human-calibrated judges for subjective fields; retain expert arbitration for high-risk or disputed samples. Switching to a second model reduces only some shared-origin bias—it does not create truth automatically.

For tool-using Agents, generate a task contract rather than free-text answers: input condition, tool Schema, permission, initial state, allowed action, prohibited side effect, and expected terminal state. Natural-language wording can be rewritten later, but the rewriter must not change task semantics or label.

## Method

1. Select gaps from the coverage matrix; do not let the model choose the task distribution.
2. Provide a few positive examples, negative examples, Schema, and prohibitions; rules or experts can supply reference answers.
3. Generate one clear condition cell at a time, requiring the source condition and an uncertainty marker.
4. Record exact model identifier/snapshot, provider, prompt version, decoding settings, seed, and time.
5. Send parse failures, label conflicts, real personal information, and prohibited content to quarantine; do not silently repair and retain them.
6. Validate through rules, a second method, and human sampling. Never let one generation call become the only judge.
7. Use pass rate and newly added coverage—not raw generation volume—to decide the next round.

One generation run must record failures and selection process too: request count, parse failure, policy rejection, human rejection, duplicate, and retained count. Saving successes alone hides selection bias and prevents generator-version comparison. Model aliases may change at a service. If a snapshot can be pinned, record it; otherwise retain provider-returned model ID, date, region, and prompt content and state the reproduction limitation in the Data Card.

## Example

A condition-specific request skeleton:

```json
{
  "task": "propose a read-only order-Agent evaluation case",
  "condition": {
    "language": "zh-CN",
    "intent": "status",
    "input_state": "missing-id",
    "difficulty": "edge"
  },
  "required_output_schema": {
    "input": "string",
    "expected_action": "ask-for-order-id",
    "reason": "string",
    "uncertain": "boolean"
  },
  "forbidden": ["real names", "real order IDs", "execute a refund"]
}
```

SELF-INSTRUCT demonstrates a research flow of generating instruction/input/output, then filtering invalid or similar items. It proves one feasible method, not that every task, model, or filter produces the same effect. This course does not restate its specific performance figures.

## Common mistakes and diagnosis

- **Treating generator answers as gold.** Validate with rules, experts, or independent evidence.
- **Changing only temperature for diversity.** Cover conditions first, then inspect semantic duplication.
- **Not recording a model snapshot.** Results cannot be reproduced; record exact identifier and retrieval date.
- **Letting the candidate system generate its own tests.** Shared blind spots or targeted advantage can result; add independent sources and real holdouts.
- **Silently retrying until success.** Record attempt count and failure distribution to avoid selection bias.

## Exercises

1. Write a generation request for a tool task with Schema, condition, and prohibited items.
2. Design three layers: rule check, independent judge, and human sample review.
3. Name two risks when the generator and system under test share origin, plus one mitigation.

## Self-check

1. Does parseable JSON prove a label is correct? No.
2. Does producing equal counts per cell equal real representativeness? No: it is diagnostic balance and needs separate production weights.
3. Is data generated by a new generator still the same version? If content or distribution changes, publish a new version and record lineage.

## Summary and next step

Model generation expands candidate space; the condition matrix and independent validation decide which samples can be trusted. Continue with [[data-synthesis/methods-and-quality/04-filtering-deduplication-and-group-splits|Filtering, Deduplication, and Group-Level Splits]].

## References

- [SELF-INSTRUCT original paper](https://aclanthology.org/2023.acl-long.754/) — accessed 2026-07-14.
- [NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1) — accessed 2026-07-14.
- [Data Cards original paper and official page](https://research.google/pubs/data-cards-purposeful-and-transparent-dataset-documentation-for-responsible-ai/) — accessed 2026-07-14.
