---
title: "Messages, Configuration, and Version Awareness"
tags:
  - llm-api
  - messages
  - configuration
aliases:
  - LLM Request Contract
source_checked: 2026-07-21
source_baseline:
  - OpenAI Responses conversation-state and function-calling documentation
  - Anthropic Messages and mid-conversation system-message documentation
  - Gemini Interactions v1 overview and reference
content_origin: original
content_status: dynamic
lang: en
translation_key: LLM API集成/03-消息、配置与版本意识.md
translation_source_hash: c0f233dcdb48d15252e49875a432041376eb6bf583611a91e002909c830498bf
translation_route: zh-CN/LLM-API集成/03-消息、配置与版本意识
translation_default_route: zh-CN/LLM-API集成/03-消息、配置与版本意识
---

# Messages, Configuration, and Version Awareness

## Objectives

Design a stable application request contract, leaving roles, content, model selection, and provider-specific features at an explicit adapter boundary.

## A provider-neutral contract

The application layer can first define the smallest set of fields it actually needs:

```json
{
  "operation_id": "ticket-42-attempt-group-1",
  "prompt_version": "ticket-router-1.3.0",
  "model_profile": "fast-structured-classifier",
  "required_capabilities": ["structured_final"],
  "messages": [
    {"role": "user", "content": "..."}
  ],
  "output_schema_id": "ticket-label-1.1.0"
}
```

Read the fields as follows:

- `operation_id` relates multiple network attempts for one business intent. Do not use a request ID from each call as the business-unique key.
- `prompt_version` lets logs, evaluation, and regression work locate the instruction version actually used.
- `model_profile` is an internal selection role; deployment configuration maps it to a concrete provider and model ID.
- `required_capabilities` lists capabilities required for correctness. The adapter should validate support before calling.
- `messages` retains application-normalized input; the adapter must still explicitly map roles and content blocks.
- `output_schema_id` relates the expected downstream structured contract and its version.

`model_profile` is an internal logical configuration, not a provider model name. Deployment configuration maps it to a provider, model identifier, output limit, and supported features. That makes selection auditable and swappable, but does not pretend that all model parameter semantics are identical.

An internal contract should also distinguish required capabilities from preferences. For example, strict schema conformance, tool calling, or image input must undergo a capability check before sending if correctness depends on them; a latency tier or caching might be merely an optimization. When a required capability is unsupported, an adapter must return `unsupported_capability`; it must not silently downgrade to plain text and let downstream code believe the contract still holds.

## Mapping roles and content

Different APIs constrain system/developer/user/assistant roles, content blocks, images, tool results, and conversation state differently. An adapter should map them explicitly and reject functionality it cannot represent, rather than silently downgrading it. Whether high-level instructions persist across response chains, how history is billed, and how long server state remains are dynamic facts.

The central differences across the current API families follow. This table describes only the families verified on 2026-07-21; it does not represent other APIs from the same provider.

| API family | High-level instructions and current-turn input | Multi-turn state | Boundary that must be handled explicitly |
| --- | --- | --- | --- |
| OpenAI Responses | `instructions` and `input` | `previous_response_id` is available, or Items can be replayed manually | `instructions` **do not** inherit through a previous ID; earlier input tokens on the chain are still billed; for manual history with `store=false`, replay every `response.output` Item, not only visible text |
| Anthropic Messages | Usually top-level `system` plus `messages` | The caller replays complete message history | Top-level `system` has the broadest coverage; a mid-conversation system message is enabled only for declared models such as Fable 5, Mythos 5, and Opus 4.8 when positional rules are met |
| Gemini Interactions v1 | `system_instruction`, `input`/Steps | `previous_interaction_id` is available, or unified Steps can be submitted | A previous interaction does not inherit tools, system instruction, or generation configuration, so continuations must resend them explicitly |

“The server remembers history” does not mean configuration is inherited, much less that history is free. An adapter should construct complete caller-owned controls for every request and treat whether a server handle can be retrieved as an explicit precondition. When a handle expires, do not silently degrade to a text summary that lacks reasoning/thought/tool blocks.

## Stateful and stateless continuation

The two approaches have different engineering responsibilities:

- Stateful continuation: save the provider response/interaction ID and verify whether the preceding object was stored, its retention, data governance, and fields that do not inherit. When the handle expires or is deleted, fail explicitly or rebuild from a trusted snapshot.
- Stateless continuation: the application retains canonical provider Items/blocks/steps and replays every object needed for continuation in original order. It needs size limits, encryption, integrity, and version-migration policies.

Do not save only assistant-visible text. Tool-call identity, tool results, reasoning/thinking signatures, refusal/truncation states, and hosted-tool steps can all affect the validity of a next turn. If a summary is needed, treat it as a new input and state clearly that it is not a lossless recovery of the original provider conversation.

## Make configuration traceable

Record:

- provider-adapter version;
- logical model-configuration ID and actual model identifier;
- prompt, schema, tool-definition, and context-selector versions;
- critical generation parameters and their “unset/explicitly set” states;
- request time and application operation ID.

Do not copy `temperature`, `top_p`, or reasoning parameters from one provider to every model. First check support, then demonstrate the value of a setting through task evaluation. Model aliases can drift; when strong reproducibility is required, use the provider's stable-version mechanism and retain the release evaluation.

Configuration records should retain both the requested model configuration and the model/version actually reported by the response. An alias, router, or backend update can make them differ; an internal `model_profile` without the actual response identifier cannot explain a regression.

For dynamic contracts, save two versions: human-readable `prompt_version/schema_id/toolset_id`, plus a digest of canonicalized content. A version label describes release intent; a digest detects rewritten content under the same name. Do not put raw secrets or personal data in high-cardinality metric labels. A digest is not a universal redaction mechanism either: low-entropy sensitive values can still be enumerated.

## Output limits and stop states

An output that reaches its limit, a safety refusal, a pending tool call, and normal completion are not the same kind of success. An adapter should map provider stop reasons to a bounded internal state while retaining the raw type. Explicitly surface an unknown new type rather than treating it as completion.

## Exercise and self-check

Design a minimal internal request/response dataclass for “structured ticket classification.” List the fields that must be adapted when changing providers. Self-check: if a new provider does not support the required schema subset, does the system report a capability mismatch or quietly switch to plain text?

## Mastery checklist

- [ ] The application contract contains only business needs, and the adapter explicitly maps provider fields.
- [ ] Required capabilities and performance preferences are distinct; an unrepresentable required capability fails closed.
- [ ] Both requests and responses retain actual model, adapter, prompt, schema, tool, and context versions.
- [ ] I can distinguish a stateful handle from stateless replay and know which instructions/configuration do not inherit and which history remains billed.
- [ ] Conversation snapshots retain provider identity and necessary block/item/step data; I do not mistake visible text for lossless history.
- [ ] Unset and explicitly set parameters are distinguishable; I do not mechanically copy a parameter from one provider to another.
- [ ] Completion, refusal, truncation, waiting for a tool, and unknown stop reasons map to distinct internal states.

## Next step

Continue to [[llm-api-integration/04-structured-output-and-streaming-responses|Structured Output and Streaming Responses]].

## References

- [OpenAI: Conversation state](https://developers.openai.com/api/docs/guides/conversation-state) (state, storage, billing, and manual Items; accessed 2026-07-21)
- [OpenAI: Function calling](https://developers.openai.com/api/docs/guides/function-calling) (tool Items and continuation; accessed 2026-07-21)
- [Anthropic: Using the Messages API](https://platform.claude.com/docs/en/build-with-claude/working-with-messages) (accessed 2026-07-21)
- [Anthropic: Mid-conversation system messages](https://platform.claude.com/docs/en/build-with-claude/mid-conversation-system-messages) (model and positional gates; accessed 2026-07-21)
- [Google: Gemini Interactions overview](https://ai.google.dev/gemini-api/docs/interactions-overview) (continuation and non-inherited configuration; accessed 2026-07-21)
- [Google: Interactions API v1 reference](https://ai.google.dev/api/interactions-api-v1) (accessed 2026-07-21)
