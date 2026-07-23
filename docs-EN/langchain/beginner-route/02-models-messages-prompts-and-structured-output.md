---
title: "Models, Messages, Prompts, and Structured Output"
aliases:
  - Models Messages Prompts Structured Output
tags:
  - langchain
  - llm
  - structured-output
source_checked: 2026-07-14
lang: en
translation_key: "LangChain/00-初学者路线/02-模型消息Prompt与结构化输出.md"
translation_source_hash: 06ff8c680aaac09b66a876166d07e32ee4e42fe24096957e2cdaad8a56f9b09e
translation_route: zh-CN/LangChain/00-初学者路线/02-模型消息Prompt与结构化输出
translation_default_route: zh-CN/LangChain/00-初学者路线/02-模型消息Prompt与结构化输出
---

# Models, Messages, Prompts, and Structured Output

## Objectives

Understand the distinct responsibilities of the model adapter, messages, prompt, runtime parameters, and structured output in one LangChain model call. You should also be able to design a business contract that is verifiable without treating model output as fact.

## Five layers

1. **Model (chat model)**: adapts a unified interface to a specific provider. Provider capabilities and parameters are not fully interchangeable.
2. **Message**: the basic unit of context, carrying a role, content, tool calls, tool results, and metadata.
3. **Prompt**: organizes task rules, trusted context, and output requirements into model input.
4. **Invocation configuration**: runtime choices such as timeouts, retries, streaming, tags, and provider parameters.
5. **Structured output**: constrains the final result to a schema so code can validate and consume it.

Do not combine system rules, user input, retrieved content, and tool results into one string of unknown provenance. An external document or web page that says “ignore previous rules” remains data; it does not gain system authority.

## Messages are not ordinary strings

LangChain provides standardized message types across providers. Common roles include system, human/user, AI/assistant, and tool. Tool calls especially need correlated IDs: a tool call emitted by the model must correspond to `ToolMessage.tool_call_id` in the returned result, or the model may not know which result belongs to which request.

Messages can also contain multimodal content blocks, token usage, response metadata, or an artifact. An `artifact` is appropriate for downstream data such as document IDs and page numbers, without sending the entire content to the model again. Whether a particular content block is supported still depends on the provider integration.

## What to record explicitly when initializing a model

The current official API offers `init_chat_model` as a unified initialization entry point and also permits direct provider classes. A project should record at least:

- Package and model identifiers; do not treat a display name as a stable ID.
- The actual temperature, maximum-output, timeout, retry, and other parameters passed.
- Whether streaming, tool calling, structured output, or multimodal input is enabled.
- The prompt, tool schema, and data version.
- Provider response IDs, usage, and error categories, with sensitive data redacted from logs.

A “unified interface” does not mean “identical capabilities.” Each integration interprets parameters; dynamic facts such as model context length, parallel tool use, and structured-output mechanisms must be checked on provider pages and confirmed through integration tests.

## Minimal prompt components

Consider extracting fields from a support ticket:

- **Task**: extract fields from the input; do not resolve the ticket.
- **Trust boundary**: system rules are trusted; email bodies and attachments are untrusted data.
- **Decision rules**: mark a date or account as missing when it is unclear; do not guess.
- **Output contract**: category enum, summary length, whether human escalation is needed, and evidence-span IDs.
- **Failure path**: use a bounded retry for schema-validation failures; if it still fails, hand off to a person.

Examples are for disambiguation. Do not crowd out the real input with dozens of samples, and do not use a prompt as a substitute for authorization checks.

## What structured output is

Structured output turns free text into a verifiable object. For example:

~~~json
{
  "category": "billing",
  "urgency": "normal",
  "summary": "The user asks about a duplicate charge",
  "needs_human": true,
  "evidence_ids": ["mail-17:paragraph-2"]
}
~~~

Read the fields as follows:

- `category` is a finite business classification. Validate it against an allowed enum downstream instead of accepting arbitrary labels.
- `urgency` represents the urgency proposed by the model; business rules must still review high-risk cases.
- `summary` is a short explanation for a human or downstream consumer and must not replace the original evidence.
- `needs_human` explicitly expresses whether human takeover is needed; do not treat it as an authorization decision.
- `evidence_ids` connect the result to reviewable input spans. Verify that the IDs exist and that the current caller is permitted to access them.

In the current LangChain Agent API, `create_agent(..., response_format=...)` can receive a schema. The official documentation distinguishes `ProviderStrategy`, which uses provider-native structured output, from `ToolStrategy`, which obtains structure through tool calling. Passing a schema type directly selects a strategy based on model capability, and the final validated result is placed in the Agent state’s `structured_response`. This behavior depends on the current package and model profile, so test it on the locked version.

Structure guarantees **shape**, not **truth**. An `evidence_ids` value may refer to a nonexistent span, an amount may be copied incorrectly, and a category may still be wrong. Downstream processing also needs enum, range, foreign-key, permission, and provenance validation.

## Handling validation failures

1. Preserve the original error category without logging the complete sensitive text.
2. Attempt a bounded repair for recoverable formatting errors; avoid unbounded retries.
3. Escalate factual gaps, uncertain permission, or business conflicts to a person rather than letting the model fabricate an answer.
4. Add failed samples to an offline dataset and compare behavior before and after prompt, model, or schema changes.

> [!example] Structurally valid but business-invalid
> `urgency="normal"` may satisfy an enum, but if the body explicitly says “the account was compromised,” a business rule should force high priority or human escalation. Schema validation and business rules are separate layers.

## Common errors and investigation

- **The model class imports but execution fails**: check the provider package, environment variables, model permissions, and versions before changing the prompt.
- **A tool result cannot be correlated**: verify that the tool-call ID is returned unchanged.
- **A field is occasionally absent**: confirm that the chosen model and strategy actually support the schema, and record the validation error.
- **Chats become increasingly expensive**: quantify message composition before truncating, summarizing, or selecting context; summaries must remain traceable.
- **The output parses but cannot be used**: add business validation, evidence checks, and a terminal failure state.

## Practice

Design a schema for “extract an appointment from a meeting email.” It must include a subject, start time, time zone, participants, missing fields, and evidence IDs. Prepare eight samples: normal, missing date, unknown time zone, two conflicting dates, a malicious instruction, an overlong body, an irrelevant email, and an attachment reference. Write both schema validation and business validation for them.

## Self-check

- [ ] Distinguish message content, metadata, a tool call, and an artifact.
- [ ] Explain why valid formatting and factual correctness are different things.
- [ ] Explain the conceptual difference between `ProviderStrategy` and `ToolStrategy` without assuming every model supports the former.
- [ ] Define a retry limit and a human terminal state for parsing failures.

## Next

Continue to [[langchain/beginner-route/03-tools-and-agent-loops|Tools and Agent Loops]] to separate model suggestions from real side effects.

## Source baseline

Official facts checked on 2026-07-14.

- [LangChain Models](https://docs.langchain.com/oss/python/langchain/models)
- [LangChain Messages](https://docs.langchain.com/oss/python/langchain/messages)
- [LangChain Structured output](https://docs.langchain.com/oss/python/langchain/structured-output)
- [LangChain Context engineering](https://docs.langchain.com/oss/python/langchain/context-engineering)
- [LangChain v1 migration guide](https://docs.langchain.com/oss/python/migrate/langchain-v1)
