---
title: "Language Post-processing and Confidence"
tags:
  - ai-agent-engineer
  - ocr
  - quality-control
aliases:
  - OCR post-processing
source_checked: 2026-07-22
lang: en
translation_key: OCR/02-工程与质量/05-语言后处理与置信度.md
translation_source_hash: 5408e5c616057392879e2240450ec1bc129cfd94a61685911986b154be5924df
translation_route: zh-CN/OCR/02-工程与质量/05-语言后处理与置信度
translation_default_route: zh-CN/OCR/02-工程与质量/05-语言后处理与置信度
---

# Language Post-processing and Confidence

## Objective

Apply character normalization, domain rules, and confidence routing without silently rewriting evidence.

## Source text, normalized text, and business values

Keep three layers separate:

- **raw_text**: the engine's original output, retained for reproduction and comparison.
- **normalized_text**: Unicode, whitespace, or punctuation normalization under published rules.
- **parsed_value**: a business interpretation of text as a date, amount, identifier, or other value.

Unicode normalization handles characters that look similar but have different encoded sequences. The choice between NFC and NFKC changes compatibility characters, so NFKC cannot be applied unconditionally to names, code, or formulas. Rules need versions and a record of each change.

## Bounded post-processing

Dictionaries, regular expressions, and context can repair common confusions, but they must satisfy all of these conditions:

1. The rule applies to a defined field, such as an invoice number, rather than arbitrary body text.
2. The original value and reason for the change are retained.
3. Multiple candidates are not guessed automatically; they enter human review.
4. An independent validation set measures the net benefit of corrections versus harmful changes.

For example, if an identifier field is specified to contain only uppercase letters and digits, a low-confidence **O/0** can be marked as a candidate. Without that field constraint, it should not be replaced automatically.

## How to interpret confidence

Confidence is normally an internal model score; it is not guaranteed to be probability-calibrated. Set thresholds by document type and risk: a critical amount can require a higher threshold, while ordinary body text may allow sampled checks. A combined score can be:

~~~text
Review score = low confidence + critical-field failure + layout anomaly + random sampling
~~~

Reviewing only low-scoring samples misses cases that are wrong with high confidence. Random sampling estimates that error class.

## Exercises and self-check

- Design a normalization record for **raw_text="１２８．００"**, including the rule version.
- Explain why a model score of **0.98** cannot be described directly as “98% accuracy.”
- Design a review strategy that treats critical fields and ordinary body text appropriately.

## Next step and references

Continue with [[ocr/engineering-and-quality/06-evaluation-error-analysis-and-human-review|Evaluation, error analysis, and human review]]. See [Unicode Normalization Forms (UAX #15, Unicode 17.0.0, Revision 57)](https://www.unicode.org/reports/tr15/) and [Tesseract's guidance on dictionaries, word lists, and patterns](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html#dictionaries-word-lists-and-patterns), checked on 2026-07-22.
