---
title: "Data Annotation and Splitting"
tags:
  - ai-agent-engineer
  - asr
  - data-annotation
aliases:
  - ASR dataset
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: 语音识别/01-基础与数据/03-数据标注与切分.md
translation_source_hash: e5144f1e31bee5f052985d170f2fb28b3d6de868380ae27a1b26d54407ffb01d
translation_route: zh-CN/语音识别/01-基础与数据/03-数据标注与切分
translation_default_route: zh-CN/语音识别/01-基础与数据/03-数据标注与切分
---

# Data Annotation and Splitting

## Objective

Design consistent transcription rules, segment boundaries, and train/validation/test splits while preventing speaker or program leakage.

## Transcription is not “write anything you hear”

An annotation guide should define capitalization, punctuation, numbers, abbreviations, filler words, stuttering, overlapping speech, unintelligible spans, language switching, and nonspeech events. It must distinguish **observed language/script** from a model guess. If language tags are used, declare the chosen BCP 47 subset and unknown/mixed-language handling; do not infer identity from a name, accent, or anonymous speaker label. Retain at least two layers:

- **verbatim_text**: records what was said as faithfully as possible.
- **normalized_text**: converts, for example, spoken “two thousand twenty-six” into “2026” under evaluation or product rules.

If only normalized text remains, you cannot determine whether an error came from the model or a rule. Unintelligible, overlapping, and nonspeech events must use data-version-specific standardized tags and record a reason; annotators must not guess. A tag is a transcription convention, not a word a model should invent.

## Segment boundaries

Segments that are too short split words. Segments that are too long increase latency and memory and can mix speakers. Combine silence, syntax, and a maximum duration when choosing boundaries. If segments retain context overlap, deduplicate during merging. Timestamps must state half-open or closed intervals, units, rounding rules, and zero point. For example, **[12.340, 14.200)** is a half-open seconds interval relative to **asset_start**. Upload wall clock, player position, and model-frame index are not one time axis.

If annotation includes an anonymous speaker label, **speaker_0** is only a label within that asset or session. Whether labels correspond across sessions, whether overlap exists, and whether a label is uncertain must be specified separately in the data contract. Do not treat diarization as identity authentication.

## Prevent data leakage

Segments from the same speaker, program, meeting, or recording are highly similar and must not be randomly scattered between training and test. Split by speaker, session, or source group first, and group derivative resampling, crops, augmentation, and text-normalization version with the original **source_revision**. Template introductions, background music, device noise, and reread versions of the same script can also become shortcuts.

The evaluation set should cover real slices by language, accent, age range, device, noise, and speech rate. The development set calibrates thresholds, vocabulary, and normalization; the final test set must not repeatedly “see” those choices. Collect and report sensitive attributes only under a clear purpose, authorization, and minimization measures.

## Quality checks

- Automatically check that end time exceeds start time, overlaps are valid under the contract, text encoding is valid, **segment_id** is unique, and language/tags are in an allowed set.
- Sample and listen again, and calculate annotator agreement or disagreement rate. Disputes return to the guide or review process rather than being silently “voted away.”
- Retain the guide, revision record, data/license version, and split manifest. Report revised test sets separately rather than comparing their score directly with the old one.

## Exercises and self-check

1. Write eight transcription rules for customer-service recordings.
2. Why cannot adjacent segments from the same speaker be split randomly? It overestimates generalization to a new speaker.
3. Design annotation and review for an unintelligible span and overlapping two-person speech.

## Next step and references

Continue with [[speech-recognition/engineering-and-quality/04-vad-segmentation-timestamps-and-speakers|VAD, segmentation, timestamps, and speakers]]. For evaluation-data design, see the [NIST OpenASR 2020 Evaluation Plan](https://www.nist.gov/system/files/documents/2021/08/03/OpenASR20_EvalPlan_v1_5.pdf), checked on 2026-07-22. Your annotation rules, split granularity, and data license must fit the actual task.
