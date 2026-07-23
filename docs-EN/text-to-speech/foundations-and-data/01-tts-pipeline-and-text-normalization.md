---
title: "The TTS pipeline and text normalization"
tags:
  - ai-agent-engineer
  - tts
  - text-normalization
aliases:
  - TTS pipeline
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: 语音合成/01-基础与数据/01-TTS全流程与文本规范化.md
translation_source_hash: 3bda7950d4514de550ca6e9001f42e5727825c5beb7b2cfffa68508112fdd922
translation_route: zh-CN/语音合成/01-基础与数据/01-TTS全流程与文本规范化
translation_default_route: zh-CN/语音合成/01-基础与数据/01-TTS全流程与文本规范化
---

# The TTS pipeline and text normalization

## Goal of this lesson

Understand the chain of responsibilities from source text to audio, and establish an auditable normalization layer for numbers, abbreviations, symbols, and language switches.

## The complete pipeline

```text
source text -> language/sentence analysis -> text normalization -> pronunciation/phonemes
-> prosody and acoustic representation -> vocoder/waveform generation -> encoding/streaming -> quality checks and records
```

**Text normalization** converts written form into a speakable form. For example, `￥128.50` might be read as “one hundred and twenty-eight yuan and fifty jiao,” while how `2026/07/13` is read depends on language and context. It is not simple substitution: `120` is read differently as a street number, quantity, or hotline number. Declare the language/locale, script, product context, and rule version first. Do not infer a user's language or identity solely from a name, the appearance of text, or a voice label.

## Three text layers

- `source_text`: original user or system text, never overwritten; associated with `source_revision`.
- `spoken_form`: speakable text transformed by versioned rules; associated with `normalization_revision`.
- `display_text`: caption or interface text, which can retain original formatting; it cannot be used to reconstruct the complete original from `spoken_form`.

Record every conversion rule and input location so a person can explain why a phrase was read that way. For high-risk fields such as names, medication, and account identifiers, ask for confirmation or spell them out when uncertain rather than guessing. Text from users, RAG, tools, or models is untrusted content: complete policy, authorization, and result confirmation in the runtime before handing it to TTS. A spoken string must not trigger an action on its own.

## Sentence boundaries and length

Overlong input increases latency, memory, and error-recovery cost. Split by punctuation, paragraphs, and a maximum length while retaining semantic integrity. Give each segment a stable `utterance_id`, `source_revision`, and source-text range; retry idempotently per segment and concatenate in order at playback. Periods in abbreviations and numbers must not be mistaken for sentence endings.

After synthesis, declare an output contract too: container, codec, sample rate, channels, duration, voice/model/configuration version, and playable state. These determine player compatibility, cache keys, and evaluation criteria. A “downloadable MP3” is not proof that every client, language, or low-latency path can play it unconditionally.

## Common mistakes

- Sending Markdown markers, URLs, or code blocks directly to TTS.
- Logging complete sensitive text.
- Deleting source text after normalization and losing accountability.
- Sharing one set of number and date rules across every language.
- Releasing unconfirmed tool results or model partial tokens directly; played content cannot be recalled.

## Exercise and self-check

For “The meeting starts at 09:30 on 2026-07-14, with a budget of ¥1,280.50,” write `source_text`, a Chinese `spoken_form`, and a conversion record. Then answer: can the date's reading be determined from the string alone? No: it also needs language and product context.

## Next step and references

Next, study [[text-to-speech/foundations-and-data/02-phonemes-prosody-and-vocoder-intuition|Phonemes, prosody, and vocoder intuition]]. SSML's `say-as`, `sub`, and language markers can express some readings; see [W3C SSML 1.1](https://www.w3.org/TR/speech-synthesis11/) (W3C Recommendation, accessed 2026-07-22). Actual interpretation depends on the engine.
