---
title: "Agent Skills Trigger Descriptions and Scope Boundaries"
aliases:
  - Skill description triggering
tags:
  - agent-skills
  - evaluation
source_checked: 2026-07-22
lang: en
translation_key: Agent Skills/学习路线/03-触发描述与范围边界.md
translation_source_hash: 833c9cb16f2e280bd5a206b13ead36eb0f70f9c8fff65cc8bc7032925fbbd4af
translation_route: zh-CN/Agent-Skills/学习路线/03-触发描述与范围边界
translation_default_route: zh-CN/Agent-Skills/学习路线/03-触发描述与范围边界
---

# Agent Skills Trigger Descriptions and Scope Boundaries

## Goal

Write a discoverable but not overbroad `description`, then test it with positive and negative trigger queries.

## What the description does

At discovery time, a progressive-disclosure client normally sees only a Skill's name and description. The description is therefore the principal clue for automatic selection. It answers at least two questions:

1. **What does it do?** — the task and artifacts it can produce.
2. **When should it be used?** — user intent, input type, typical context, or keywords.

A weak description:

```yaml
description: Helps with text. # Counterexample: too broad; it can incorrectly route unrelated translation, rewriting, or RAG requests to this Skill
```

A stronger description:

```yaml
description: Count words, characters, and lines with deterministic JSON output. Use when a user asks for text-size statistics, word counts, or a machine-readable text summary. # States a specific capability, likely trigger wording, and deterministic output without promising rewriting or summarization
```

The latter names both the capability and its trigger context while making no claim to provide translation, rewriting, or semantic summarization.

## Describe user intent, not implementation detail

Users rarely say “run `scripts/text_stats.py`.” A description should cover the result they seek, not the internal filename. Official guidance recommends clear action language, a few sentences to a short paragraph, and compliance with the 1,024-character limit.

## Positive and negative trigger sets

Write two kinds of realistic request for every Skill:

- **should-trigger** — explicit requests, implicit needs, conversational wording, varying levels of detail, and needs embedded in a multi-step task.
- **should-not-trigger** — near-miss negative cases that overlap in terminology but belong to an adjacent capability.

For `text-statistics`:

| Query | Label | Reason |
| --- | --- | --- |
| “Count the words in this description and return JSON.” | Should trigger | Both the task and output match |
| “How many lines and English words are in my report?” | Should trigger | It does not name the Skill, but the intent matches |
| “Polish this English text to make it more concise.” | Should not trigger | This is rewriting, not counting |
| “Draw a bar chart of word frequency.” | Should not trigger | It requires frequency analysis and visualization, outside the scope |

Negative cases should not all be obviously unrelated prompts such as “What is today's weather?” They cannot test the boundary.

## Triggering is not a deterministic function

Model behavior can be nondeterministic. Run the same query several times and record a trigger rate rather than drawing a conclusion from one run. The official optimization guide suggests starting around 20 queries, with eight to ten positive and eight to ten negative cases, then running every query multiple times. Three runs are a reasonable starting point, and roughly five change rounds often reveal a direction. Those are engineering starting points, not performance promises for any model.

When evaluating automatic triggering, record **explicit `/skill-name` calls, fixed preloading in a custom agent, and manual Skill selection** separately. Do not mix them into an automatic-selection score based on the description. Determine selection from observable evidence in the target client — logs, traces, supplied context, or official diagnostics — not just by guessing from the final answer that the Skill was probably read.

Split cases into a debugging set and a validation set. Change the description only from the debugging set; run the validation set when the text is ready. Continuously adding failed validation keywords produces a description that memorizes the test instead of defining a boundary that generalizes to real user intent.

## Exercises and self-check

1. Write three should-trigger queries and three near-miss negative cases for “generate a quality report from CSV.”
2. Run identical queries multiple times before and after a description change. Record trigger and non-trigger outcomes instead of selecting only successful examples.
3. Self-check: is adding every popular keyword to a description better? No. It increases false triggers, context cost, and conflicts.

## Next step

Continue with [[agent-skills/learning-route/04-scripts-resources-and-safety|Scripts, Resources, and Safety]].

## References

- [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) — checked 2026-07-22.
- [Agent Skills Specification](https://agentskills.io/specification) — checked 2026-07-22.
- [GitHub Copilot CLI reference: Skills](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference) — examples of explicit invocation and client fields; checked 2026-07-22.
