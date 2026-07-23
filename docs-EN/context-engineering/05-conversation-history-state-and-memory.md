---
title: "Conversation History, State, and Memory"
tags:
  - context-engineering
  - conversation-state
  - memory
aliases:
  - Agent State and Memory
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline:
  - OpenAI Conversation State guide
  - Anthropic Context Windows documentation
  - Anthropic Effective context engineering for AI agents
lang: en
translation_key: 上下文工程/05-对话历史、状态与记忆.md
translation_source_hash: d47c1bf502b17a6506ecda8fda9cfe91512698b4def7355f9fbc04b5a8f3fda9
translation_route: zh-CN/上下文工程/05-对话历史、状态与记忆
translation_default_route: zh-CN/上下文工程/05-对话历史、状态与记忆
---

# Conversation History, State, and Memory

## Objective

Distinguish raw chat history, task state, conversation summaries, and long-term memory. Avoid replaying indefinitely and spreading incorrect memories.

## Four objects

- **Raw history**: The actual user and assistant messages. It is suitable for auditing, but can be long and contain stale plans.
- **Structured state**: The current goal, constraints, completed actions, open questions, and authorization scope. It is the factual source for an Agent advancing the task.
- **Conversation summary**: A narrative compressed to save space. It is derived data and may omit or misstate information.
- **Long-term memory**: Stable preferences or facts retained across sessions. It needs explicit write conditions, provenance, permission, updating, and deletion.

Do not infer a long-term preference automatically from an offhand remark. A model-generated summary must not directly overwrite state confirmed by the user.

Long-term memory needs a write policy: what information is stable enough, who confirms it, how long it is retained, who may read it, and how it is corrected or deleted. Retrieved memory is still context data and must again pass permission, freshness, and prompt-injection checks. “It was remembered before” does not mean “it is still correct and permitted now.”

## A state machine is more reliable than a long chat

~~~json
{
  "goal": "Book a business trip",
  "constraints": {"budget_cny": 3000, "refundable": true},
  "confirmed": ["departure date"],
  "pending": ["destination airport"],
  "completed_actions": [],
  "state_version": 4
}
~~~

Field notes (do not put comments inside strict JSON, which would leave learners with invalid state if they copy it):

- goal is the readable objective of the current task. It should be confirmed by a user or controlled process, not inferred automatically from casual chat.
- constraints holds hard constraints that remain valid. The example records both a budget ceiling and whether a refundable option is required.
- confirmed and pending list information already confirmed and information still needing clarification, so the system does not treat an unknown as a known fact.
- completed_actions records actions that have already occurred, so idempotency, duplicate-prevention, and recovery flows can check them. An empty array means no action has occurred yet.
- state_version is the version number for concurrent updates. Compare it before and after a write so that a later request cannot silently overwrite state someone else just confirmed.

Read the current version before every tool call, then update it with an event after the call. When a concurrent modification occurs, reject a silent overwrite. Chat can explain state, but it cannot be the only database.

## History-trimming rules

Prioritize the latest user goal, still-valid constraints, unresolved questions, necessary summaries of tool results, and recent confirmations and refusals. You can remove greetings, repeated explanations, and intermediate reasoning that structured state has replaced. Every trimming operation must retain who confirmed what and the IDs of key evidence.

A provider may offer server-side conversations or response-chaining features, and an application may replay messages manually. Neither option means that history is free, permanent, or automatically carries every high-level instruction. Verify current billing, retention, and inheritance semantics in official documentation.

### A current provider example

According to OpenAI documentation checked on 2026-07-21, the Responses API commonly supports three ways to manage state: use previous_response_id so the service references a previous response, manually return previous output items with the next request, or use a persistent conversation object. previous_response_id does not automatically inherit the previous top-level instructions, and previous input tokens in a response chain are still billed as input. The example shows that **saving a conversation, inheriting instructions, and charging for context are three different things**. Verify other providers’ semantics separately.

## Exercise and self-check

Turn a ten-turn “choose a hotel” conversation into structured state. Retain the budget, dates, cancellation policy, rejected options, and pending items. Then remove the raw history and decide whether the next step can continue safely; if not, list the missing facts and their provenance.

## Mastery check

- [ ] I can distinguish raw history, structured state, derived summaries, and long-term memory.
- [ ] Confirmations, rejections, open items, and external actions all have versions and provenance, rather than existing only in conversational prose.
- [ ] Concurrent state updates use version checks and do not silently overwrite another turn’s or another Agent’s result.
- [ ] Memory writing, reading, correction, expiry, and deletion have permission and audit rules.
- [ ] I verify the state-inheritance, storage, and billing semantics of the API I use instead of assuming that continuing a chat automatically restores every instruction.

## Next

Continue to [[context-engineering/06-trimming-summarization-compression-and-caching|Trimming, Summarization, Compression, and Caching]].

## References

- [OpenAI: Conversation state](https://developers.openai.com/api/docs/guides/conversation-state) (accessed 2026-07-21)
- [OpenAI: Migrate to the Responses API—Update multi-turn conversations](https://developers.openai.com/api/docs/guides/migrate-to-responses#3-update-multi-turn-conversations) (accessed 2026-07-21)
- [Anthropic: Context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows) (accessed 2026-07-21)
- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (accessed 2026-07-21)

