---
title: "Evaluation-Driven Iteration"
tags:
  - prompt-engineering
  - evaluation
aliases:
  - Prompt evaluation
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline:
  - Anthropic Develop tests documentation
  - OpenAI Prompt engineering guide
  - OpenAI Evals-platform deprecation notice
  - Zheng et al. LLM-as-a-judge paper
lang: en
translation_key: 提示词工程/05-评测驱动迭代.md
translation_source_hash: 47701d9361f5d148f3a9e4a14f44e9a26bd629160f6a61c74d87601ca3fa232d
translation_route: zh-CN/提示词工程/05-评测驱动迭代
translation_default_route: zh-CN/提示词工程/05-评测驱动迭代
---

# Evaluation-Driven Iteration

## Goal of this lesson

Establish a loop of “find a failure, change one hypothesis, run regression checks” rather than tuning prompts based on a few chat impressions.

## Build a minimal evaluation set

For a teaching experiment or initial prototype, start with 20–50 de-identified, clearly labeled, representative cases, then expand by risk and failure mode. This is an engineering recommendation for getting started, not a claim of statistical sufficiency. Each case should contain at least an input, expected result or scoring rule, business slice, risk level, and annotation rationale. Include normal, boundary, empty, overlong, language-changing, and adversarial text.

This course's [[prompt-engineering/examples/cases.json|12 cases]] are a minimal teaching fixture for the code contract and are deliberately insufficient for estimating production quality. Every case contains an expected label, slice, risk, and annotation rationale. Their purpose is to validate data format, slice statistics, and failure paths before you build a larger evaluation set.

Split data into three parts:

- **Development set:** viewed frequently to locate failures.
- **Regression set:** run for every release to prevent fixing one error while breaking another.
- **Held-out set:** viewed rarely or late, to estimate generalization to new cases.

Fixed repository fixtures, scoring code, versions, and CI results should be the reproducible baseline; provider evaluation products are interchangeable runners only. Check the lifecycle of dynamic products. As of **2026-07-21**, OpenAI had announced that its Evals platform was deprecated: existing evals are scheduled to become read-only on **2026-10-31**, and its dashboard and API are scheduled to stop service on **2026-11-30**. Do not make a hosted product ID the only evaluation asset, and do not extrapolate this OpenAI timeline to other providers.

## Metrics and thresholds

For classification, use accuracy and per-class precision and recall. For extraction, use field-level exact match. For generation, use human review against an explicit rubric or a validated automated grader. Also record non-quality metrics: parse success rate, refusal rate, latency, input/output usage, and cost per task.

An overall average can hide critical failures. Slice by language, input length, customer type, risk level, and other relevant factors. A high-risk false-positive case can have a no-regression hard gate instead of being offset by the overall score.

## Validate one hypothesis at a time

For example, suppose **other** is often misclassified as **technical**, and the hypothesis is that an insufficient-information example is missing. Add only that boundary example, fix the model and retrieval, run regression tests, and compare confidence intervals or at least case-by-case differences. If the gain comes only from already-seen cases, add the new failures to the taxonomy and revisit the label definition.

Model outputs vary. Run critical cases repeatedly and record the pass-rate distribution, model identifier, sampling configuration, and call time. Do not declare a fix after one success. Where a provider allows it, pin a model snapshot and run regression tests before an upgrade. If you use an LLM-as-a-judge, calibrate the grader against human-labeled cases, freeze the rubric, and inspect position bias, style bias, and same-family self-grading bias. Online, also watch for distribution drift and human corrections.

## Common pitfalls

- Generating answers and having the same model score itself without audit.
- Only judging that an answer “looks good,” with no task-level success criteria.
- Putting real sensitive information in an evaluation set or overlapping it with training or prompt examples.
- Accepting higher scores while cost, latency, or safety failures are unacceptable.

## Practice and self-check

List 12 evaluation cases and four slices for ticket classification. Write a release threshold and a failure type that always requires human review. Self-check: if a new version improves overall results by 2% but doubles missed cases for high-value customers, does your threshold block release?

## Mastery check

- [ ] Every case has an expectation, slice, risk, and annotation rationale.
- [ ] Development, regression, and held-out cases have separate purposes; prompt examples do not contaminate the held-out set.
- [ ] I check task quality, parsing, refusals, latency, usage, cost, and safety failures together.
- [ ] My release threshold protects critical slices, and I can identify case-level improvements and regressions.
- [ ] My online-model conclusions come from repeated runs, not one good-looking answer.

## Next step

Continue to [[prompt-engineering/06-prompt-injection-and-trust-boundaries|Prompt injection and trust boundaries]] to connect adversarial cases with actual permission control.

## References

- [Anthropic: Develop tests](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests) (accessed 2026-07-21)
- [OpenAI: Prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering) (accessed 2026-07-21)
- [OpenAI: API deprecations—Evals platform](https://developers.openai.com/api/docs/deprecations#2026-06-03-evals-platform) (accessed 2026-07-21)
- Zheng et al., [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685) (NeurIPS 2023 Datasets and Benchmarks Track)

