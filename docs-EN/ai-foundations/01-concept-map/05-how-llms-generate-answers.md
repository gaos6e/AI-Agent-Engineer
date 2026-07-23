---
title: "How LLMs Generate Answers"
tags:
  - ai-agent-engineer
  - ai-foundations
  - llm
aliases:
  - Large language model intuition
content_origin: original
content_status: validated
source_checked: 2026-07-22
lang: en
translation_key: AI基础认知/01-概念地图/05-LLM如何生成答案.md
translation_source_hash: a3133b3c940cc86f7e89120dcef996753695cc4b9c38d80ce409343a2524d10c
translation_route: zh-CN/AI基础认知/01-概念地图/05-LLM如何生成答案
translation_default_route: zh-CN/AI基础认知/01-概念地图/05-LLM如何生成答案
---

# How LLMs Generate Answers

## Learning objective

You will use one complete data flow to explain how an LLM processes input and understand tokens, context, parameters, Transformers, generation, and randomness. The goal is sound intuition, not deriving network formulas.

## One-sentence intuition: predict what best follows from context

A **large language model (LLM)** is a class of model that processes sequences of language tokens. A `token` is a piece of text used by the model; it can be a character, part of a word, punctuation, or a code fragment. It is not the same as one character or one English word.

During generation, the model computes a probability distribution for the next token from the current context, selects one token, appends it to the context, and predicts again:

```text
Input text
  ↓ Tokenization
Sequence of token IDs
  ↓ Vector representations + Transformer computation
Probability distribution for the next token
  ↓ Select one token
Append it to the sequence and repeat until stopping
```

For example, after “Remember to bring an” the model may assign a high probability to “umbrella” in a rainy-day context. It is not retrieving a fixed sentence from a database; it computes a continuation from learned parameters and the current context.

## Six core components

### 1. Tokenizer: turn text into processable IDs

Before computation, a text LLM uses a tokenizer to encode input as tokens and map them to integer IDs. Different models split text differently, so character count is not a reliable token count.

### 2. Embedding: turn discrete IDs into vectors

A vector is a sequence of numbers. The model maps token IDs to vectors so later computation can represent their relationships in the current context. This embedding is an internal model representation. Text embeddings used later in vector databases represent a whole sentence or document chunk; the concepts share vector intuition but differ in objective and use.

### 3. Transformer: exchange information across positions

The Transformer is a neural-network architecture commonly used by modern LLMs. Attention lets the model calculate attention weights for a position from the current input and learned parameters, then combine information from other positions; the weights are not one fixed table for every input. **Stable fact:** Vaswani et al. introduced the attention-centered Transformer architecture in 2017. Modern models contain many extensions, so this fact does not reveal the full internal implementation of a specific product.

### 4. Parameters: values retained after training

Training adjusts many parameters to reduce prediction error for the training objective. Parameters encode distributed statistical patterns, not a row-by-row, addressable fact table. A model can reproduce common knowledge, but can also conflate facts, become stale, or generate nonexistent details.

### 5. Context window: what this inference can see

System instructions, user input, conversation history, retrieved passages, and tool results commonly share the context window. Content beyond the window must be truncated, summarized, or stored externally. **Changeable fact:** exact context lengths, pricing, structured-output support, and multimodal capabilities vary by model and service version. Check current official documentation during implementation.

### 6. Decoding: choose output from a probability distribution

Always choosing the highest-probability token can be more stable, but may also become repetitive or rigid; sampling from the distribution can add diversity but also variation. `temperature` commonly adjusts the sampling distribution, but API support and semantics must follow current documentation. Lower temperature does not automatically make facts correct.

## Why LLMs are powerful and can still be confidently wrong

A language model’s training objective is not the same as “every sentence is supported by reliable evidence.” It is good at producing contextually coherent, well-formed sequences, but has no built-in fact-database transaction and does not naturally know which evidence it lacks.

This leads to two conclusions that are both true:

- **Stable fact:** An LLM can use one text interface for summarization, extraction, rewriting, classification, question answering, code, and other tasks.
- **Engineering recommendation:** Whenever an answer needs a fact guarantee, real-time state, or business authorization, connect trusted data sources, validate the output, and add human approval according to risk. Do not treat fluency as correctness.

## A verifiable input design

Task: extract action items from this sentence.

```text
The meeting decided that Lee will submit the test report by Friday; the budget still needs finance confirmation.
```

A more testable request than “summarize this” is:

```text
Extract only action items stated explicitly. Output a JSON array.
Fields are task, owner, deadline, and status.
Use null for fields not provided in the source; do not guess.
```

The expected result should list “submit the test report” as an action item and mark “the budget still needs finance confirmation” as an unresolved issue. If the model fills in a specific budget amount, that is unsupported completion. The point is not prompt tricks; it is making correct and incorrect outcomes decidable.

## Common misconceptions and diagnosis

| Misconception | Why it fails | Better practice |
| --- | --- | --- |
| “The answer is detailed, so it is more credible.” | Details can also be generated. | Require evidence locations and independently verify critical facts. |
| “More context is always better.” | Noise, conflict, and cost also increase. | Provide only task-relevant, sourced context. |
| “The same input always yields the same output.” | Sampling and service updates can change results. | Fix controllable parameters, preserve version information, and accept with a test set. |
| “An LLM automatically knows today’s data.” | Training knowledge and current state differ. | Supply real-time data through an API, retrieval, or database. |
| “One reflection makes the model reliable.” | The same model can repeat or rationalize an error. | Validate with external rules, tool results, and independent tests. |

## Exercise

1. Explain in your own words why tokens and words are not one-to-one.
2. Write three decidable output rules for “extract an order number from a customer-service email.”
3. Add an exceptional case to the meeting example: what should be returned when there is no owner or deadline?
4. List fields that must come from a real-time system rather than model memory.

## Self-check

1. Why can next-token prediction still produce a long article?
2. Why cannot parameters be treated as a queryable database?
3. Can a lower temperature guarantee factual correctness?
4. What is the difference between context and trained parameters?

Suggested answers: generated tokens are repeatedly added to context, so the model can form a long sequence; parameters are distributed numerical patterns rather than individual records; reducing randomness does not introduce evidence; context is visible for this call, whereas parameters are model state formed by training and usually fixed during inference.

## Related concepts

- This lesson’s token and context-window budgets become selection, trimming, and compression strategies in [[context-engineering/00-index|Context Engineering]].
- Internal token representations and retrieval-oriented [[embeddings/00-index|Embeddings]] share vector intuition, but differ in training objective, granularity, and engineering purpose.
- [[rag/00-index|RAG]] supplies external evidence, and [[prompt-engineering/00-index|Prompt Engineering]] defines the task contract. Neither automatically turns probabilistic generation into factual guarantees.

## Summary and next step

An LLM provides language inference based on context. Next, [[ai-foundations/01-concept-map/06-how-agents-complete-tasks|How Agents Complete Tasks]] places that capability in a system loop with state, tools, and feedback.

## References

Accessed **2026-07-22**.

- Vaswani et al., [Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [NIST Generative AI Profile, NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1)
- Mitchell et al., [Model Cards for Model Reporting](https://doi.org/10.1145/3287560.3287596)
