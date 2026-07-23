---
title: "Structured Output and Contracts"
tags:
  - prompt-engineering
  - structured-output
  - json-schema
aliases:
  - Prompt structured output
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline:
  - OpenAI Structured Outputs guide
  - Google Gemini Structured output guide
  - JSON Schema 2020-12 documentation
lang: en
translation_key: 提示词工程/03-结构化输出与契约.md
translation_source_hash: b8aa9adc7966d181791f6421e666ceaea579dbbf22a5ce535ca3c01b01945521
translation_route: zh-CN/提示词工程/03-结构化输出与契约
translation_default_route: zh-CN/提示词工程/03-结构化输出与契约
---

# Structured Output and Contracts

## Goal of this lesson

Distinguish output that merely looks like JSON from parseable JSON, schema-conforming JSON, and business-semantically correct output. Then establish validation layers between model output and a business action.

## Four layers of checks

Suppose the expected output is:

~~~json
{"label":"billing","reason":"The customer was charged twice.","evidence":"charged twice"}
~~~

1. **Syntax:** Can a JSON parser read it? Single quotes, trailing commas, and Markdown code fences can all fail.
2. **Structure:** Are required fields present, types correct, enum values valid, and extra fields absent? JSON Schema can describe this layer.
3. **Business rules:** Must **unknown** include a reason? Does the cited evidence actually appear in the input? Are currency, amount, and status mutually consistent?
4. **Authorization:** Even if the first three layers pass, may the system automatically refund money, send email, or delete data? High-impact actions still require independent authorization or human confirmation.

Provider schema constraints, supported keywords, and failure representations can change. According to OpenAI documentation checked on **2026-07-21**, JSON mode guarantees only valid JSON, not conformance to your schema. Structured Outputs provides schema-adherence guarantees for supported models, interfaces, and schema subsets. Even then, the application must handle refusals, incomplete output, and values that are structurally valid but semantically wrong. Google's current documentation likewise says that it supports only a JSON Schema subset and that applications must validate semantic values. Do not assume that a Draft 2020-12 schema works unchanged across providers merely because both features are called structured output.

## A minimal schema

~~~json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "label": {"type": "string", "enum": ["billing", "technical", "other"]},
    "reason": {"type": "string", "minLength": 1, "maxLength": 160},
    "evidence": {"type": ["string", "null"], "maxLength": 120}
  },
  "required": ["label", "reason", "evidence"],
  "additionalProperties": false
}
~~~

The JSON example must remain parseable, so its explanation is outside the block:

- **$schema** says which JSON Schema draft interprets this example. It does not mean every provider API fully supports that draft.
- Root **type: object** requires an object rather than an array, string, or bare number.
- **properties** lists the permitted fields. **label** may contain only the three categories, while **reason** must be nonempty and at most 160 characters.
- **evidence** permits a string or **null**, making “no citable evidence” an explicit state rather than inviting fabrication.
- **required** requires all three fields. If evidence has no value, return **null** explicitly.
- **additionalProperties: false** rejects undeclared keys so downstream consumers do not silently consume temporary model-added fields.

Explain field semantics in the prompt, enable the schema features currently supported by the provider at the API layer where possible, then parse and validate again in application code. The prompt, API parameters, and code should be generated from the same contract asset or checked for drift, rather than evolving independently. See this course's [[prompt-engineering/examples/response.schema.json|response.schema.json]]. To remain dependency-free, the [[prompt-engineering/examples/prompt_lab.py|offline validator]] is not a general JSON Schema engine. It accepts only the exact teaching subset implemented by the handwritten runtime. The root object, three fields, and **anyOf** branches all have keyword allowlists; unsupported constraints such as **pattern** and **allOf** fail closed. It then applies business rules: **billing** and **technical** require evidence, and evidence must occur in the input.

## Failure handling

- **Parsing fails:** log a redacted response fragment, request ID, and prompt version; retry only when policy allows it.
- **Schema does not match:** do not guess a repair in business code. A policy may allow a limited repair request, but its result must pass all checks again. Stop after consecutive failures instead of retrying indefinitely.
- **Content refusal or safety block:** treat it as an explicit result, not as an empty success.
- **Output truncation:** reduce the task, raise a reasonable output limit, or use a multi-step flow. Never splice together half of a JSON object.
- **Untrustworthy semantics:** fall back to human review; do not treat **confidence** as a calibrated probability.

## Practice and self-check

Write a schema for extracting currency and total from invoice text. Then decide: is the total a string or a number? How are thousands separators handled? If the text contains no currency, should the output be **null**, **unknown**, or a failure? Until these choices are explicit, the schema is not a complete contract.

## Mastery check

- [ ] I can explain JSON syntax, schema, business rules, and authorization as four separate layers.
- [ ] I do not describe JSON mode as a schema-adherence guarantee.
- [ ] I handle refusals, incomplete output, extra fields, and semantic errors explicitly.
- [ ] I can make prompt instructions, API schema, and program validation refer to the same contract version.

## Next step

Continue to [[prompt-engineering/04-templates-variables-and-version-management|Templates, variables, and version management]] to make the contract and prompt traceable and releasable.

## References

- [OpenAI: Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) (accessed 2026-07-21)
- [Google: Structured output](https://ai.google.dev/gemini-api/docs/structured-output) (accessed 2026-07-21)
- [JSON Schema Draft 2020-12: Validation](https://json-schema.org/draft/2020-12/json-schema-validation) (accessed 2026-07-21)

