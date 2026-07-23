---
title: "Evaluation, Error Analysis, and Human Review"
tags:
  - ai-agent-engineer
  - ocr
  - evaluation
aliases:
  - OCR evaluation
source_checked: 2026-07-22
lang: en
translation_key: OCR/02-工程与质量/06-评测错误分析与人工复核.md
translation_source_hash: 8e75e0af5e74e1e5288900274d8b51281d4755ac5473dfbdbb97a42494d8f1ed
translation_route: zh-CN/OCR/02-工程与质量/06-评测错误分析与人工复核
translation_default_route: zh-CN/OCR/02-工程与质量/06-评测错误分析与人工复核
---

# Evaluation, Error Analysis, and Human Review

## Objective

Calculate character and word error rates, and turn text, field, and structural quality into actionable error categories and a review queue.

## CER and WER

Let **S**, **D**, and **I** be the minimum substitutions, deletions, and insertions needed to transform a reference sequence into a predicted sequence, and let **N** be the reference length:

$$
\mathrm{ErrorRate}=\frac{S+D+I}{N}
$$

Character segmentation yields CER (Character Error Rate); word segmentation yields WER (Word Error Rate). For example, a reference of “Total 128” and a prediction of “TotaI 1280” contain at least one substitution and one insertion at the character level. Because insertions can be numerous, an error rate can exceed 100%; that is not a calculation error. When the reference length is zero but the prediction is nonempty, the denominator is zero. Do not disguise that as “100% error”: report it as an unexpected-output or false-positive slice, with **null** or a count, and retain the original block for review.

Chinese WER depends on a tokenization method, so the tokenizer must be recorded. CER is more direct, but cannot express word meaning or field structure. Compare two systems only under the same normalization and segmentation rules.

## More than one aggregate score

- **Text level**: CER/WER, sliced by language, document type, and clarity.
- **Field level**: exact match and parse-success rate for amounts, dates, and identifiers.
- **Structural level**: block type, reading order, and table row/column/cell relationships.
- **Process level**: rejection rate, human-review rate, per-page latency, and failure rate.

Macro averaging calculates each document first and then averages, avoiding domination by long documents. Micro averaging pools all edit counts before dividing by total length, reflecting overall character volume. They serve different purposes and are best reported together.

## The human-review loop

A review interface should present the original image region, original text, normalized text, candidates, and the rule reason together. Record **confirmed**, **corrected**, or **cannot determine**, but do not let production feedback enter a training set directly. First de-identify, check quality, verify licenses, and version the data.

Example error categories include missed detection boxes, cropped truncation, character confusion, language errors, ordering errors, table misalignment, and harmful rule changes. Bind each category to a responsible module so that a problem reaches the correct repair loop.

## Exercises and self-check

1. Calculate the CER for reference **ABC** and prediction **ADCX**: one substitution and one insertion, or $2/3$.
2. Why can a lower overall CER still hurt the business? The critical-amount slice may have become worse.
3. If the review rate falls after a model upgrade, is the system necessarily better? No. The threshold or score scale may also have changed, so inspect human-confirmed quality.

## Next step and references

Continue with [[ocr/engineering-and-quality/07-privacy-deployment-and-operational-troubleshooting|Privacy, deployment, and operational troubleshooting]]. The edit-distance metric family is consistent with NIST speech evaluation; see the [NIST OpenASR 2020 Evaluation Plan](https://www.nist.gov/system/files/documents/2021/08/03/OpenASR20_EvalPlan_v1_5.pdf), checked on 2026-07-22. OCR structural metrics are engineering contracts defined for the task; this course does not claim there is one universal standard.
