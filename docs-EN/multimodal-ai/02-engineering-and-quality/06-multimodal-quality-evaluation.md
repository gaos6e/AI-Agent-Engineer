---
title: "Multimodal Quality Evaluation"
tags:
  - multimodal-ai
  - evaluation
  - grounding
aliases:
  - Multimodal evaluation
  - Multimodal quality system
source_checked: 2026-07-22
lang: en
translation_key: 多模态AI/02-工程与质量/06-多模态质量评测.md
translation_source_hash: 4ec3dc9a2991d93926c820de2ff5d3d7cd15b75441ce4059a7beede86d12e6dd
translation_route: zh-CN/多模态AI/02-工程与质量/06-多模态质量评测
translation_default_route: zh-CN/多模态AI/02-工程与质量/06-多模态质量评测
---

# Multimodal Quality Evaluation

## Goal of this lesson

Break an end-to-end result into input quality, unimodal perception, cross-modal alignment, reasoning, evidence location, and business outcome instead of looking only at one leaderboard score.

## Six evaluation layers

### 1. Input and preprocessing

Measure format-parsing success, corruption-detection rate, time or coordinate-mapping error, frame-sampling coverage, and transcription-segmentation completeness. A preprocessing error can make every downstream model fail regardless of its capability.

### 2. Unimodal perception

- OCR: character error rate (CER) and field accuracy;
- ASR: word error rate (WER) and timestamp error;
- objects and regions: detection precision, recall, and intersection over union (IoU);
- video events: segment temporal IoU and event recall; and
- documents: reading-order and table-cell recovery rate.

Beyond average metrics, slice by language, font, noise, resolution, accent, duration, and asset source.

### 3. Cross-modal retrieval and alignment

Use Recall@k, MRR, and similar measures for retrieval. For region-to-phrase and audio/video temporal alignment, measure localization error. Include hard negatives: images that look similar but contain different text, and segments with the same keyword but different events.

### 4. Reasoning and structure

Check logical correctness, values and units, consistency, and `schema_valid_rate`. A legal structure and a semantically correct answer must be measured separately.

### 5. Evidence grounding

Does every claim cite a real `asset_id` and page, region, or time reference? Does that cited segment support the conclusion? You can measure `evidence_precision`, `evidence_recall`, and `unsupported_claim_rate`.

Also add **evidence-intervention tests**: mask or replace a cited region or time window while keeping other input as stable as possible, then observe whether the conclusion changes. Mask uncited regions too, to detect apparent citations that actually depend on other cues. These tests can reveal empty citations, shortcuts, and fragility, but cannot alone prove causality or factual truth. Use annotated evidence entailment and human review to judge `evidence_supported`.

### 6. End to end and safety

Measure business-task success, human acceptance, rework, latency, and cost, while also measuring sensitive-data exposure, media prompt injection, handling of modality conflicts, and correct refusals.

## Required baselines and ablations

- Text or metadata baseline: prevents a model from guessing solely from the question.
- Unimodal baseline: shows that another modality adds genuine value.
- Missing modality: checks whether the system degrades or refuses correctly.
- Conflicting modalities: checks whether it identifies contradiction instead of blindly fusing.
- Random or blank media: checks whether the model ignores media.
- Different sampling or resolution: quantifies preprocessing trade-offs.

If removing the image does not change the result, the supposed visual capability may be only a language prior.

## Dataset design

Sample in strata derived from real failure modes. Retain original-asset authorization, annotation guidelines, agreement among multiple annotators, and versions. Isolate train and test by source or entity so clips from one video do not leak across sets.

The reference answer should include not only the final conclusion but also evidence pages, boxes, or time ranges and acceptable variations. For open responses, prefer rules or expert review for critical fields; calibrate and spot-check any model judge.

## Proper use of public benchmarks

The original MMMU paper created expert-level multimodal questions spanning disciplines and heterogeneous image types. MMMU-Pro further filters questions answerable from text alone, adds options, and introduces visual-input variations to test more strictly whether a model actually uses vision. They are useful for understanding research capability, not as evidence for your invoice, meeting, or industrial-video task.

Do not directly compare scores across different versions, prompts, input resolutions, or test subsets. Fix your own task set and acceptance criteria first.

## An example results table

| Slice | Success rate | Evidence support rate | P95 latency | Notes |
| --- | ---: | ---: | ---: | --- |
| Clear image and text | 0.91 | 0.95 | 4.2 s | Baseline |
| Screenshot with small text | 0.62 | 0.70 | 4.4 s | Needs tiled OCR |
| Audio-visual conflict | 0.48 | 0.86 | 7.1 s | Weak conflict arbitration |

The numbers are only a table demonstration, not measured results for any model.

## Exercise and self-check

Design 20 minimal evaluations for “extract decisions from a meeting video,” including at least no audio, incorrect subtitles, a fleeting visual, multiple overlapping speakers, audio-visual conflict, and injected text. Self-check: does a 100% structured-JSON pass rate mean the model answers are correct?

## Next step

Continue with [[multimodal-ai/02-engineering-and-quality/07-latency-cost-privacy-and-safety|Latency, Cost, Privacy, and Safety]].

## References

- Yue et al., [MMMU](https://arxiv.org/abs/2311.16502)
- Yue et al., [MMMU-Pro](https://arxiv.org/abs/2409.02813)
- [Google Gemini API: Video understanding](https://ai.google.dev/gemini-api/docs/video-understanding) (accessed 2026-07-22)
