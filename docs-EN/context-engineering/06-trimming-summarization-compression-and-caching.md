---
title: "Trimming, Summarization, Compression, and Caching"
tags:
  - context-engineering
  - summarization
  - prompt-caching
aliases:
  - Context Compression and Caching
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline:
  - OpenAI Compaction and Prompt Caching guides
  - Anthropic Context Windows, Context Editing, and Prompt Caching documentation
  - Google Gemini Context Caching documentation
lang: en
translation_key: 上下文工程/06-裁剪、摘要、压缩与缓存.md
translation_source_hash: 453e3502638d5715b3ba45dd4d27aedc693d6e27a8df328b7337e4758d4013b5
translation_route: zh-CN/上下文工程/06-裁剪、摘要、压缩与缓存
translation_default_route: zh-CN/上下文工程/06-裁剪、摘要、压缩与缓存
---

# Trimming, Summarization, Compression, and Caching

## Objective

Choose trimming, extraction, summarization, or caching according to risk, and establish fidelity checks and invalidation policy.

## Five techniques solve different problems

- **Trimming**: Remove content confirmed to be irrelevant or duplicate. It is cheapest, but needs reliable selection rules.
- **Extraction**: Retain key original sentences, table rows, or fields. Provenance is clear, but surrounding conditions may be lost.
- **Summarization**: Rewrite content more briefly. It achieves high compression, but can introduce omissions and interpretive bias.
- **Provider compaction**: An API or SDK turns a long conversation into a smaller state that can continue to be used. Its format, readability, and scope are provider-specific.
- **Caching**: Reuse repeated prefixes that meet a provider’s rules to reduce some repeated processing cost or latency. It normally does not reduce the semantically counted content in the model window, and it does not guarantee deterministic output.

Perform deterministic deduplication and field extraction before summarizing low-risk narrative. Legal, medical, and safety limits; monetary values; dates; and explicit user refusals should not survive only as free-text summaries. Retain their structured original values and provenance.

## Summary contract

Require summary output such as:

~~~json
{
  "facts": [{"text": "…", "source_ids": ["s1"]}],
  "constraints": [{"key": "budget_cny", "value": 3000, "source_id": "u7"}],
  "open_questions": ["…"],
  "omitted_sections": ["…"]
}
~~~

Field notes (to keep this JSON directly parseable, explain fields outside the code block):

- facts holds traceable fact summaries. Each item carries source_ids so later systems can return to the original source for verification.
- constraints holds structured constraints that compression must not lose. key, value, and source_id respectively identify the constraint, its value, and its evidence.
- open_questions explicitly retains unresolved questions, preventing a summary from compressing “unknown” into an apparently certain conclusion.
- omitted_sections records content deliberately not brought forward, leaving a trail for later loading, human audit, and failure diagnosis.

Code should verify that every reference exists and regression-test summaries against critical source text. A summary also needs an input version and generation version; it should become invalid when the source changes.

## Do not conflate summaries and compaction

A human-readable summary should permit auditing of facts, provenance, and omissions. Provider compaction may return machine state that is not meant for human interpretation. For example, OpenAI’s current compaction guide describes server-side threshold-triggered compaction or a separate compact endpoint that can return a new window containing an encrypted, opaque compaction item. A window returned by the separate endpoint must be passed through unchanged as the canonical input to the next call; do not parse it as an ordinary summary or alter it yourself. This is OpenAI’s current API semantic, not a uniform format for all providers.

Whichever method is used, test whether critical constraints, open questions, tool results, and citations remain recoverable after compression. Compression is capacity management performed while the old window is still processable, not a universal remedy after overflow.

## Caching strategy

Place stable policy, tool definitions, and fixed reference material in the prefix; place user input, the current time, and dynamic retrieval results later. Monitor cache reads, writes, and hit rates, but do not hard-code universal cross-provider thresholds, lifetimes, or fields. OpenAI currently uses repeated-prefix matching and reports cache usage; Google’s current APIs vary in their support for implicit and explicit caching; Anthropic has its own breakpoints and counting semantics. Every implementation must return to the current page for the API in use.

## Failure modes

- A summary writes “confirmed” when the user has not yet confirmed it.
- Extraction keeps only a conclusion and omits a condition such as “only in this region.”
- A cache does not expire with permission or document version and reuses content for the wrong user.
- Budget decisions continue to use the old token estimate after compression.
- An opaque compaction item is edited as a human summary, breaking the continuous state required by the provider.

## Exercise and self-check

From one page of refund policy, extract the amount, period, exceptions, and effective date, retaining an original ID for each. Design a cache-invalidation key for a document update. Self-check: if the summarizer is completely wrong, is raw evidence still traceable, and will program rules block a critical action?

## Mastery check

- [ ] I can distinguish the problems and risks addressed by trimming, extraction, summarization, compaction, and caching.
- [ ] Monetary values, dates, authorization, user refusals, and safety rules retain structured original values and provenance rather than only free-text summaries.
- [ ] Compression has regression tests before and after it for key facts, open state, citations, and tool continuity.
- [ ] I know that a cache hit neither enlarges the context window nor repairs incorrect or stale content.
- [ ] When using provider compaction, I follow the provider’s current semantics for handling, storing, and protecting its output.

## Next

Continue to [[context-engineering/07-long-context-failure-modes-and-evaluation|Long-Context Failure Modes and Evaluation]].

## References

- [OpenAI: Compaction](https://developers.openai.com/api/docs/guides/compaction) (accessed 2026-07-21)
- [OpenAI: Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) (accessed 2026-07-21)
- [Anthropic: Context editing](https://platform.claude.com/docs/en/build-with-claude/context-editing) (accessed 2026-07-21)
- [Anthropic: Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) (accessed 2026-07-21)
- [Google: Context caching](https://ai.google.dev/gemini-api/docs/caching) (accessed 2026-07-21)

