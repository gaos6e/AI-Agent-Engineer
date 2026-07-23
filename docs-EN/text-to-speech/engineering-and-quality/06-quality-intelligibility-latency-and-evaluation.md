---
title: "Quality, intelligibility, latency, and evaluation"
tags:
  - ai-agent-engineer
  - tts
  - evaluation
aliases:
  - TTS evaluation
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: 语音合成/02-工程与质量/06-质量可懂度延迟与评测.md
translation_source_hash: bd4ce2c1b1bdf27daca39bcb1007ddc126cea600a0d180671013481c31be638b
translation_route: zh-CN/语音合成/02-工程与质量/06-质量可懂度延迟与评测
translation_default_route: zh-CN/语音合成/02-工程与质量/06-质量可懂度延迟与评测
---

# Quality, intelligibility, latency, and evaluation

## Goal of this lesson

Break “sounds good” into intelligibility, naturalness, content correctness, speaker consistency, stability, and system latency.

## Subjective evaluation

MOS (Mean Opinion Score) normally asks listeners to rate samples on a defined scale, then averages the ratings. It is highly sensitive to experimental instructions, samples, playback equipment, listener language, and scale; MOS values from different studies cannot be compared directly without their designs. Paired preference (A/B) asks listeners to select the preferred version and is useful for small differences, but still needs randomized order, hidden system labels, counterbalanced ordering, and enough participants.

At minimum, separate these questions:

- **Naturalness:** does it sound like natural speech?
- **Intelligibility:** can the content be heard correctly?
- **Content correctness:** are numbers, names, negation, and units spoken correctly?
- **Appropriateness:** does the tone suit the scenario, rather than whether a particular voice is liked?

When a recognizable voice is involved, listener evaluation and sample presentation must also stay within the authorization scope.

Record at least the text/`source_revision`, voice-catalog/model/configuration version, output format, listener eligibility and language ability, playback-device/volume rules, randomization, exclusion rules, sample count, and uncertainty. In accessibility scenarios, involve target users rather than treating laboratory naturalness scores as a substitute for accessibility.

## Objective and system metrics

ASR round-tripping can provide an intelligibility proxy: synthesize, transcribe again, and calculate WER. Its result is also affected by ASR bias, so it cannot replace human listening. Also measure pronunciation-lexicon hits, exact match for numbers/dates, manual checks for high-risk semantics such as negation and amounts, silence proportion, clipping, anomalous audio duration, and failure rate. Objective audio features can flag anomalies but do not equal “natural,” “safe,” or “authorized.”

On the system side, record p50/p95/p99 time to first audio, time to the first **playable** byte, total generation/playback-completion latency, real-time factor, timeouts, cancellation success rate, unknown-terminal-state rate, and cache hits. Slice by short/long sentence, language, voice, output format, streaming/batch mode, network condition, and client capability. Do not treat a server's first byte as proof that the user has heard audio.

## Experimental design

Freeze the text set, voices, configuration, devices, and versions. Randomize sample order, normalize volume, and hide system labels. Report listener count, samples per condition, rating instructions, and uncertainty. Do not select only the strongest demo sentences; include numbers, abbreviations, multilingual text, long sentences, names, negation, warnings, and interruption/cancellation boundaries.

Bind a candidate release through `release_id` to the evaluation report, authorization/disclosure policy, and output contract. A change to the model, lexicon, normalization, or codec can require reevaluation; identical text is not enough to reuse an old conclusion.

## Exercise and self-check

1. Design 20 evaluation texts covering numbers, names, lists, questions, and warnings.
2. Why does low ASR round-trip WER not prove naturalness? A robotic voice can still be clear.
3. Should a system ship immediately if p95 time to first audio improves but cancellation failures increase? No; one metric is insufficient.

## Next step and reference

Next, study [[text-to-speech/engineering-and-quality/07-cloning-risk-disclosure-and-traceability|Cloning risk, disclosure, and traceability]]. For subjective listening methods, see [ITU-T P.800](https://www.itu.int/rec/T-REC-P.800) (accessed 2026-07-22). Follow the body of the version used for a real experiment rather than merely citing the name “MOS.”
