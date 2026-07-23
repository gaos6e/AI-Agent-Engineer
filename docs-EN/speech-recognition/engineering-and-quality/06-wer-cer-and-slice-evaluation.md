---
title: "WER, CER, and Slice Evaluation"
tags:
  - ai-agent-engineer
  - asr
  - evaluation
aliases:
  - ASR evaluation
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: 语音识别/02-工程与质量/06-WER-CER与切片评测.md
translation_source_hash: d176af909681fbf1743474188e3a69fdaee6902d8ed9f878e23629b14a2ba174
translation_route: zh-CN/语音识别/02-工程与质量/06-WER-CER与切片评测
translation_default_route: zh-CN/语音识别/02-工程与质量/06-WER-CER与切片评测
---

# WER, CER, and Slice Evaluation

## Objective

Calculate and interpret WER/CER correctly, freeze normalization rules, and use slices to find problems a total score hides.

## Edit distance

Let **N** be the reference word-sequence length and let **S**, **D**, and **I** be the substitutions, deletions, and insertions required to transform it into a prediction:

$$
\mathrm{WER}=\frac{S+D+I}{N}
$$

Character-level calculation is CER. A reference of “we test agents” and prediction of “we tested agent” involve word-level substitutions; dynamic programming finds the actual minimum edits. WER can exceed 100% when there are many insertions.

When the number of reference units is $N=0$, WER/CER is **undefined**, not zero. “Text was produced where silence was expected” needs a separately reported no-reference segment count, false-trigger rate, or errors per hour; it cannot be forced into a WER with zero denominator. Retain error count and reference-unit count as well as a rounded percentage.

## Normalization determines comparability

Freeze case, punctuation, number form, abbreviations, filler words, Unicode normalization, and tokenizer before calculation. Whitespace tokenization often makes Chinese WER meaningless, so declare a tokenizer or use CER. Do not devise prediction-specific rules just to improve a number; the same function must process reference and prediction.

**Micro averaging** pools all errors and reference tokens, giving long segments more weight. **Macro averaging** calculates each session or speaker first and then averages, which better exposes short examples. Macro averages are especially unstable for empty-reference or very short segments, so state exclusions and separate-reporting rules. Report aggregation method, versioned tokenizer, and reasons for sample filtering.

## Slices and uncertainty

Slice at least by language, noise, device, speech rate, duration, speaking style, and business scenario. When there is a legitimate purpose, authorization, and sufficient protection, inspect differences by sensitive attributes relevant to fairness risk as well. Small-sample slices fluctuate strongly, so report sample size and estimate intervals with methods such as bootstrap.

Beyond text, measure no-speech false triggers, segment-boundary error, word-level timestamps, speaker error, real-time factor, latency to first and final result, and human-edit rate. These are not substitutes: low WER does not prove accurate boundaries, accurate speaker labels, nondiscrimination, or real-time usability; confidence is not a replacement for WER. Diarization evaluation needs a best mapping between anonymous labels and separate handling for overlap/unknown speakers.

For each candidate upgrade, freeze **data_revision**, **model_revision**, **frontend_revision**, **decode_config_revision**, **normalization_revision**, and evaluation-script version. Otherwise a score change cannot be attributed. When online traffic has no references, report sampled human annotation, complaint/edit rate, and observable proxies separately; do not pretend they are “online WER.”

## Exercises and self-check

1. Reference **a b c**, prediction **a x c d**: one substitution and one insertion, so WER is $2/3$.
2. If group A has lower WER than group B, can you attribute that directly to accent? No. Device, noise, sample difficulty, and other confounders need control.
3. Why retain old normalization code during a model upgrade? Otherwise a like-for-like regression cannot be calculated.

## Next step and references

Continue with [[speech-recognition/engineering-and-quality/07-fairness-privacy-deployment-and-troubleshooting|Fairness, privacy, deployment, and troubleshooting]]. See the [NIST OpenASR 2020 Evaluation Plan](https://www.nist.gov/system/files/documents/2021/08/03/OpenASR20_EvalPlan_v1_5.pdf) and [NIST SCTK](https://github.com/usnistgov/SCTK), checked on 2026-07-22. Verify tool parameters against the current README. [[speech-recognition/project-and-self-check/08-project-offline-transcript-evaluation|The offline project]] implements a teaching-scale edit distance and reports an empty-reference rate as undefined.
