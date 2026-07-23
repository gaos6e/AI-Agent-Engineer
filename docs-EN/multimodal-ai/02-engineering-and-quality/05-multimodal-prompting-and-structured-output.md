---
title: "Multimodal Prompting and Structured Output"
tags:
  - multimodal-ai
  - prompting
  - structured-output
aliases:
  - Multimodal prompt design
  - Multimodal structured output
source_checked: 2026-07-22
lang: en
translation_key: 多模态AI/02-工程与质量/05-多模态提示与结构化输出.md
translation_source_hash: 392a83a0e31f28cc0bf7fb39695b7fd8d4de3a52fbd095d1c1cec302a92e823c
translation_route: zh-CN/多模态AI/02-工程与质量/05-多模态提示与结构化输出
translation_default_route: zh-CN/多模态AI/02-工程与质量/05-多模态提示与结构化输出
---

# Multimodal Prompting and Structured Output

## Goal of this lesson

Separate media, task, evidence scope, and output contract explicitly so important conclusions can be located, refused when necessary, and checked in code.

## Five components of a prompt

1. **Task**: compare, extract, locate, or decide.
2. **Media manifest**: asset ID, modality, order, and purpose.
3. **Evidence rules**: which pages, regions, or time spans may be cited.
4. **Decision rules**: how to handle missing or conflicting modalities, low confidence, and unreadable inputs.
5. **Output schema**: fields, types, enums, length, and citation format.

Do not only say “look at the image and answer.” For example:

~~~text
Task: verify whether an invoice image agrees with order text.
Inputs: A1 = invoice image; T1 = order JSON.
Compare only invoice_number, total, and currency.
Every difference must cite A1's normalized region box and T1's JSON path.
If an image field is unreadable, set status=insufficient_evidence; do not guess.
Return only JSON that conforms to the given schema.
~~~

## Input order and roles

State what every medium is; do not infer it from upload order. Assign each asset a stable ID and refer to it in the question. When several screenshots look alike, state their time, page, and purpose.

Providers differ in media placement, file methods, and structured-output support. As of 2026-07-22, Google's Gemini official documentation still recommends structured output for complex JSON; its JSON Schema support is a subset and is only a vendor-capability snapshot. Validate JSON Schema locally anyway. “The model supports structured output” does not imply that a business fact is true.

## Output-schema example

~~~json
{
  "status": "supported | conflict | insufficient_evidence",
  "claims": [
    {
      "field": "total",
      "value": "100.00",
      "evidence": [
        {
          "asset_id": "A1",
          "source_revision": "sha256:record-at-runtime",
          "kind": "image_region",
          "box": [0.62, 0.71, 0.91, 0.79]
        }
      ]
    }
  ],
  "warnings": []
}
~~~

At runtime, check enums, array lengths, coordinate bounds, asset existence, in-range times, and whether the source revision is still the current readable version. A passing schema proves format only, not the claim. Track separately **schema_valid** (format), **evidence_bound** (the pointer resolves to an allowed asset), and **evidence-supported** (the citation actually supports the conclusion; a field can be named `evidence_supported`). A model must not declare the latter two true on its own.

## Space and time in prompts

- Images: state whole image or region, and return normalized boxes.
- Documents: state page number, table or paragraph, and region.
- Audio: require `start_ms` and `end_ms`, plus speaker if reliable.
- Video: cite visual and audio intervals separately, and say whether synchronized evidence is required.

“Find the anomaly in the video” must define the anomaly type and temporal precision; otherwise a model may return only a vague description.

## Missing and conflicting modalities

State explicitly that the system must:

- return `missing_modalities` when a required modality is absent;
- return `invalid_asset` when media are corrupted;
- return `insufficient_evidence` when evidence is inadequate;
- list image, caption, and audio conflicts separately instead of silently merging them; and
- not use filenames, EXIF, or captions as the only proof of authenticity.

## Prompt injection in media

Text in images, PDF pages, captions, and audio transcripts can contain malicious instructions such as “ignore previous instructions.” They are data to analyze, not system instructions. Layer trusted instructions separately from media content. Model output still needs an authorization policy; text inside media must not trigger tools.

This is the same boundary as indirect prompt-injection controls in [[ai-safety/00-index|AI Safety]] and server-side authorization in [[tool-calling-function-calling/00-index|Tool Calling]]. Structured JSON helps parsing, but cannot turn media content or a model field into execution authority.

## Multi-turn strategy

Have the system locate candidate segments first, then analyze a small amount of high-resolution evidence in a second turn. Pass `asset_id`, coordinates or time, and provenance between turns rather than only the first-turn summary. If the second result conflicts with the first, retain both evidence sets and the processing versions.

## Common errors

- **Asking for too many tasks**: transcription, summary, emotion judgment, and compliance review all at once make errors hard to locate. Split work into evaluable stages.
- **Putting coordinates in free text**: use a numeric schema and boundary checks instead.
- **Asking the model to be “more confident”**: define refusal conditions and verifiable evidence instead.
- **Trusting JSON because it is JSON**: after schema validation, facts and policy still need validation.

## Exercise and self-check

Write a prompt and minimum schema for “determine whether the steps demonstrated in a video agree with the manual.” Self-check: if subtitles are correct but the visual step is absent, what should `status` be? Why must an instruction inside media not change tool permissions?

## Next step

Continue with [[multimodal-ai/02-engineering-and-quality/06-multimodal-quality-evaluation|Multimodal Quality Evaluation]].

## References

- [Google Gemini API: Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) (accessed 2026-07-22; supports only a JSON Schema subset, so application-side validation remains necessary)
- [Google Gemini API: Prompt design strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies) (accessed 2026-07-22)
- [Google Gemini API: File input methods](https://ai.google.dev/gemini-api/docs/file-input-methods) (accessed 2026-07-22)
