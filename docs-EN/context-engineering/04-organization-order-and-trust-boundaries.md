---
title: "Organization, Order, and Trust Boundaries"
tags:
  - context-engineering
  - context-layout
  - trust-boundary
aliases:
  - Context Organization
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline:
  - OpenAI Prompt Caching guide
  - Anthropic Effective context engineering for AI agents
  - Google Gemini Long Context documentation
lang: en
translation_key: 上下文工程/04-组织、顺序与信任分区.md
translation_source_hash: 2282c93c4b588d5906c64fec2febfa71dcce7038f199bad90ce185d28581163f
translation_route: zh-CN/上下文工程/04-组织、顺序与信任分区
translation_default_route: zh-CN/上下文工程/04-组织、顺序与信任分区
---

# Organization, Order, and Trust Boundaries

## Objective

Partition policy, task, state, evidence, and output contract, then use a stable order to reduce confusion and cache misses.

## A recommended logical layout

APIs differ in their roles and content blocks, but you can preserve this logical order:

1. **Stable policy**: Task responsibilities, safety boundaries, and tool-use rules.
2. **Output contract**: Schema, allowed refusal states, and citation rules.
3. **A small set of stable examples**: Retain only examples shown to help.
4. **Structured task state**: Goal, completed steps, open questions, and user confirmations.
5. **Evidence with provenance**: Every passage has an ID, trust tier, and date.
6. **Current input**: The question or event for this turn.

Place stable, repeated prefixes first and dynamic content later. This is also commonly better for prefix caching with some providers. Google’s current long-context guide additionally recommends placing a query after long material, but that is guidance for a specific model family, not a cross-model law; validate it with position evaluation. Tool definitions also consume context, so discover them on demand or load only the schemas needed for the current step when there are many tools.

## Partition example

~~~text
<policy>…rules maintained by the application…</policy>
<state>{"goal":"compare two policies","open_questions":["applicable region"]}</state>
<sources>
  <source id="policy-A" trust="official" date="2026-04-01">…</source>
  <source id="forum-B" trust="unverified">…</source>
</sources>
<user_request>…current request…</user_request>
~~~

Tags help a model interpret content, but real permission boundaries remain in the application layer. forum-B does not gain the ability to call tools, rewrite policy, or access secrets merely by appearing inside sources.

## Order and conflicts

Information position in a long text can affect performance. For a critical constraint, restate it concisely in stable policy and the final checklist, but do not copy several slightly different versions of the same rule. When sources conflict, mark version and priority in metadata and require the output to explain the conflict; code may discard superseded versions in advance according to business rules.

Caching is a performance mechanism, not a context-selection mechanism. In OpenAI’s current documentation, cache matching is based on repeated prefixes; inserting dynamic fields into the middle of a prefix breaks later matches. Even on a cache hit, these tokens remain visible model context, and caching does not repair stale, unauthorized, or conflicting information.

## Common errors

- Putting dynamic content such as the current date or user input inside a cacheable prefix, leading to poor hit rates or incorrect reuse.
- Putting a large body of evidence first, while the task question is buried in the middle and unclear.
- Keeping three versions of the same fact in conversation history, a summary, and structured state.
- Removing source IDs to save tokens and making answers unauditable.

## Exercise and self-check

Take a prompt that mixes system rules, a user question, web-page text, and JSON output requirements, and divide it into six partitions. For each partition, label the owner, trust level, update frequency, and maximum length. Self-check: if a web page tries to change the output schema, which layer rejects it?

## Mastery check

- [ ] I can separate policy, contract, examples, state, evidence, and current input, and label their owners.
- [ ] Untrusted evidence cannot gain permission to rewrite policy or call tools through tags or message position.
- [ ] My stable-prefix and dynamic-suffix layout has cache and position-evaluation evidence, rather than being copied from a template by intuition.
- [ ] Tool definitions and tool results are both budgeted; unneeded tools do not all remain resident in the window.
- [ ] Conflicting sources retain versions and priority, and code does not make the model silently guess one.

## Next

Continue to [[context-engineering/05-conversation-history-state-and-memory|Conversation History, State, and Memory]] to manage change across turns.

## References

- [OpenAI: Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) (accessed 2026-07-21)
- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (accessed 2026-07-21)
- [Anthropic: Manage tool context](https://platform.claude.com/docs/en/agents-and-tools/tool-use/manage-tool-context) (accessed 2026-07-21)
- [Google: Long context](https://ai.google.dev/gemini-api/docs/long-context) (accessed 2026-07-21)
