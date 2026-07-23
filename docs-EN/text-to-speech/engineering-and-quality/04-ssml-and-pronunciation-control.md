---
title: "SSML and pronunciation control"
tags:
  - ai-agent-engineer
  - tts
  - ssml
aliases:
  - Speech Synthesis Markup Language
source_checked: 2026-07-22
lang: en
translation_key: 语音合成/02-工程与质量/04-SSML与发音控制.md
translation_source_hash: 1a6b9fe582dff6f6f337ef11e14548469fd68bcda3e080f485d660bda1d517a4
translation_route: zh-CN/语音合成/02-工程与质量/04-SSML与发音控制
translation_default_route: zh-CN/语音合成/02-工程与质量/04-SSML与发音控制
---

# SSML and pronunciation control

## Goal of this lesson

Understand the XML structure of SSML 1.1, express language, sentences, pauses, emphasis, prosody, and pronunciation safely, and handle engine differences.

## Minimal SSML

SSML (Speech Synthesis Markup Language) is a W3C Recommendation. A standalone SSML document follows a valid XML prolog and has a namespace-qualified `speak` root. The following XML declaration is a readable complete-document example. A vendor API can instead accept an SSML fragment or wrap the root itself, so verify the request form for the target interface separately:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<speak version="1.1"
       xmlns="http://www.w3.org/2001/10/synthesis"
       xml:lang="en-US">
  <p><s>Welcome to the voice assistant.</s></p>
</speak>
```

Common concepts are `break` for pauses, `emphasis` for emphasis, `prosody` for rate/pitch/volume, `say-as` for hints about numbers or dates, `phoneme` for pronunciation, `sub` for a replacement reading, and `voice` for requested voice characteristics or a name.

## Safe construction

Do not concatenate user text directly into XML. Create elements with an XML library so characters such as `<` and `&` are escaped automatically. Limit allowed tags, attributes, input length, and external resources; disable or reject unneeded external `audio` references. SSML is not HTML, so browser escaping rules do not transfer directly.

The course project creates SSML from plain text and controlled enumerations; it accepts no arbitrary XML. That reduces injection risk and leakage of vendor extensions.

## Portability

The standard defines semantics, but a vendor can:

- support only a subset of tags or attributes;
- add private namespaces for emotion or style;
- produce different audible results for the same `prosody` value;
- error, ignore, or degrade invalid tags.

Build a “portable core SSML + vendor adapter” layer and regression-test every target voice. A pronunciation lexicon can refer to W3C PLS, but engine support must still be verified.

## Exercise and self-check

- Use an XML library to construct text containing `A&B <test>` and confirm it is escaped instead of treated as tags.
- Design `say-as` for a telephone number and explain how to fall back to an explicit spoken form if the engine does not support it.
- Why should an arbitrary URL not be placed in `<audio>`? It introduces network, tracking, format, and content-safety risks.

## Next step and references

Next, study [[text-to-speech/engineering-and-quality/05-voice-selection-batch-processing-and-streaming|Voice selection, batch processing, and streaming]]. See [W3C SSML 1.1](https://www.w3.org/TR/speech-synthesis11/) and the [W3C Pronunciation Lexicon Specification 1.0](https://www.w3.org/TR/pronunciation-lexicon/) (both W3C Recommendations, accessed 2026-07-22).
