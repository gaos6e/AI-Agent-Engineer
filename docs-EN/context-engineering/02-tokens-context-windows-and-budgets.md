---
title: "Tokens, Context Windows, and Budgets"
tags:
  - context-engineering
  - tokens
  - context-window
aliases:
  - Context Budgeting
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline:
  - OpenAI Conversation State guide
  - Anthropic Context Windows documentation
  - Google Gemini Long Context documentation
lang: en
translation_key: 上下文工程/02-Token、上下文窗口与预算.md
translation_source_hash: 9ab63a587b3d469caa9cc99b8592365c3dcfdb0e4d1bc75a60e4149f82177dd9
translation_route: zh-CN/上下文工程/02-Token、上下文窗口与预算
translation_default_route: zh-CN/上下文工程/02-Token、上下文窗口与预算
---

# Tokens, Context Windows, and Budgets

## Objective

Understand tokens, context windows, input and output consumption, and engineering budgets. Do not mistake “it fits” for “it works well.”

## Three distinct concepts

A **token** is a unit a model uses to process input and generate output. It may correspond to a character, part of a word, punctuation, or whitespace; results differ by tokenizer, model, language, and content type. Character or word counts are useful only for capacity estimates, never as substitutes for billing or actual window usage. Before sending a request, use the counting tool or API that matches the target model; after sending it, calibrate with response usage. Consult current provider documentation for how message wrappers, tool schemas, images, audio, and reasoning tokens are counted.

A **context window** is the upper bound on the working space that one model generation can reference. It usually holds instructions, messages, tool descriptions, retrieved material, tool results, output, and for some models reasoning tokens. It is neither the model’s training corpus nor long-term memory. Its exact limit and accounting vary by API, model, and invocation mode.

A **context budget** is an allocation made deliberately by the team, not the model’s limit. For example, divide available capacity among stable instructions, the current task, required state, retrieved evidence, tool results, expected output, and a safety reserve. A budget prevents one source from consuming all available space.

## Why reserve headroom

If the input approaches the limit, output can be truncated, new tool results may have nowhere to go, and serialization differences can make estimates inaccurate. A budget should reserve capacity for output and unanticipated overhead, then enforce a hard check before a request is sent. Limits, prices, and caching rules are dynamic facts and must not be hard-coded into a course; keep configuration updateable and verify it against the provider’s current documentation.

Use a conceptual check rather than transplanting numbers across providers:

~~~text
window limit >= all rendered input + reserved output + other provider-counted items
context-pack budget = input budget - stable instructions - tool definitions - current task - safety reserve
~~~

If a counting interface differs substantially from a local estimate, investigate message wrapping, tool schemas, multimodal content, and model version before simply absorbing the error into a larger window.

## A minimal budget table

~~~text
Total available input budget    12,000 (example units; not a model limit)
Stable instructions and tools    2,000
Task and structured state        1,500
Retrieved evidence               7,000
Reserved error margin            1,500
~~~

Place required content first, then select optional content by value. If required content alone exceeds the limit, reject, split the task, or compress it; never silently drop a safety rule.

## Cost and performance

More input generally means more transmission, processing, and cost, and a long context can also increase latency. A cache hit may reduce the cost or latency of processing some repeated prefixes, but it does not change semantic correctness or guarantee identical output. Record actual response fields for input, output, and cache-related usage; do not settle costs from estimates.

## Exercise and self-check

For “read three policies and answer a question,” list every context component, separate required from optional material, and assign a budget. Self-check: when the third document does not fit, does the system error, retrieve excerpts, summarize, or truncate directly? Which outcome makes incomplete evidence visible to the user?

## Mastery check

- [ ] I can distinguish a token, a context window, an input budget, an output limit, and actual usage.
- [ ] My budget includes instructions, tool definitions, tool results, and output headroom—not just document text.
- [ ] I do not treat character counts or example estimated_tokens as real tokenizer results.
- [ ] When required content exceeds the limit, the system explicitly fails, splits the task, or performs controlled compression; it does not silently remove safety rules.

## Next

Continue to [[context-engineering/03-selection-relevance-and-provenance|Selection, Relevance, and Provenance]] to decide what receives the limited budget.

## References

- [OpenAI: Conversation state—Managing context for text generation](https://developers.openai.com/api/docs/guides/conversation-state#managing-context-for-text-generation) (accessed 2026-07-21)
- [Anthropic: Context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows) (accessed 2026-07-21)
- [Google: Long context](https://ai.google.dev/gemini-api/docs/long-context) (accessed 2026-07-21)

