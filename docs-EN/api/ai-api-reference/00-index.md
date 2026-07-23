---
title: "Vendor AI API Reference Index"
tags:
  - ai-agent-engineer
  - api
  - ai-api
aliases:
  - AI API reference index
  - Vendor API reference
source_checked: 2026-07-22
content_origin: curated
content_status: dynamic
lang: en
translation_key: API/AI API 调用/00-目录.md
translation_source_hash: 5febb751566d1b49d5c21741b203fa9e033dfb5e96048d8768c7074479dca2eb
translation_route: zh-CN/API/AI-API-调用/00-目录
translation_default_route: zh-CN/API/AI-API-调用/00-目录
---

# Vendor AI API Reference Index

## What these notes are

This section holds Python call references for ten providers so you can compare endpoints, SDKs, model identifiers, streaming events, structured output, and tool calling. It is a **dynamic reference layer**. It does not replace the [[api/00-index|general API learning path]] and should not be a beginner's first stop.

Individual model names, aliases, SDK methods, beta labels, pricing, and regional endpoints change. Every note retains its official sources and `source_checked` date. On **2026-07-22**, this index and the main entry point, default teaching model, or critical capability boundary for every provider except OpenAI were checked again. This round checked only OpenAI's tool guide in part; its page remains governed by its own `source_checked: 2026-07-20`. In particular, Google's Interactions API reached GA in June 2026 and is the recommended entry for new projects; the original `generateContent` API remains fully supported but is legacy. The Gemini note separates the two API families, and their example fields must not be mixed. Before a real call, revisit the provider documentation and the models available to your account.

## Verification boundary

- Done: official-source review, Python fenced-code syntax parsing, internal-link resolution, and credential-safety review for examples.
- Not done: installing every provider SDK, creating ten accounts, using real keys, making potentially billable calls, or comparing live price or performance.
- Therefore, “the source was checked” does not mean “the network call ran.” Only the local `api/examples` project executed real loopback HTTP.

## Minimum cross-provider runtime contract

“OpenAI-compatible” commonly means only that some request/response shape can be reused. It does **not** guarantee identical model IDs, streaming events, tool-result handling, structured output, data retention, retry behavior, billing, or authorization semantics. For every real call, retain at least this provider contract rather than only final text:

| Record | Purpose | What it does not replace |
| --- | --- | --- |
| Official documentation URL, `source_checked`, SDK version | Records the documentation snapshot behind this code | Proof of account or region availability |
| Provider, endpoint/region, exact `model` | Fixes the request destination and model semantics | Business version, quality baseline, or data-residency compliance |
| Stream terminal state, refusal/tool items, structured-field validation | Prevents treating a delta, text fragment, or syntactically valid JSON as a finished result | Fact checking, identity authorization, or approval of side effects |
| Provider `request_id` and local `operation_id` | Correlate provider diagnosis and local business intent separately | Each other, user identity, idempotency/deduplication ledger, or final outcome |
| Redacted summary of tool result, citations, usage, and error type | Supports evaluation, diagnosis, and cost attribution | Full prompt, credentials, raw sensitive input, or factual proof |

Tools, structured output, and remote search are model capabilities only. Before writing to a database, sending a message, charging, or deploying, still enforce local schema, trusted actor, object-level ACL, approval, business idempotency, and receipt/outcome verification through [[tool-calling-function-calling/00-index|Tool Calling]], [[json/00-index|JSON]], and [[llm-api-integration/00-index|LLM API Integration]].

## Enter credentials safely for the current session only

Never put a real key in Markdown, `.py`, command history, screenshots, or Git. PowerShell 7 can read a masked value for the current process:

```powershell
$env:EXAMPLE_API_KEY = Read-Host 'EXAMPLE_API_KEY' -MaskInput
try {
    python .\your_example.py
}
finally {
    Remove-Item Env:EXAMPLE_API_KEY -ErrorAction SilentlyContinue
}
```

Replace `EXAMPLE_API_KEY` with the target provider's variable name. This deliberately does not use `setx`: it writes user environment state, affects only later new processes, and encourages learners to leave a real value in command history. Teams and production deployments should use a platform secret manager. If a project uses `.env`, commit only an empty `.env.example` and verify that a real `.env` was never tracked by Git.

## Reference entry points

| Provider | Note | Common environment variable | Main official entry checked in this round |
| --- | --- | --- |
| OpenAI | [[api/ai-api-reference/openai-api\|OpenAI API]] | `OPENAI_API_KEY` | [Tools](https://developers.openai.com/api/docs/guides/tools) (partially rechecked this round; page date remains 2026-07-20) |
| Anthropic | [[api/ai-api-reference/anthropic-claude-api\|Anthropic Claude API]] | `ANTHROPIC_API_KEY` | [Model IDs](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions) |
| Google | [[api/ai-api-reference/google-gemini-api\|Gemini API: Interactions and GenerateContent]] | `GEMINI_API_KEY` | [Getting started](https://ai.google.dev/gemini-api/docs/get-started) |
| DeepSeek | [[api/ai-api-reference/deepseek-api\|DeepSeek API]] | `DEEPSEEK_API_KEY` | [Updates](https://api-docs.deepseek.com/updates/) |
| Alibaba Cloud | [[api/ai-api-reference/qwen-api\|Qwen API]] | `DASHSCOPE_API_KEY` | [Text generation models](https://help.aliyun.com/zh/model-studio/text-generation-model) |
| Moonshot AI | [[api/ai-api-reference/kimi-api\|Kimi API]] | `MOONSHOT_API_KEY` | [Kimi K2.6 quickstart](https://platform.kimi.com/docs/guide/kimi-k2-6-quickstart) |
| Zhipu AI | [[api/ai-api-reference/zhipu-glm-api\|Zhipu GLM API]] | `ZAI_API_KEY` | [Model overview](https://docs.bigmodel.cn/cn/guide/start/model-overview) |
| Mistral AI | [[api/ai-api-reference/mistral-api\|Mistral API]] | `MISTRAL_API_KEY` | [SDKs](https://docs.mistral.ai/resources/sdks) |
| Cohere | [[api/ai-api-reference/cohere-api\|Cohere API]] | `COHERE_API_KEY` | [Chat API](https://docs.cohere.com/v2/reference/chat) |
| xAI | [[api/ai-api-reference/xai-grok-api\|xAI Grok API]] | `XAI_API_KEY` | [Grok 4.5](https://docs.x.ai/developers/grok-4-5) |

Environment-variable names follow each note and its official SDK. Some SDKs, including Cohere's, can also accept explicit constructor parameters; do not infer deployment behavior from this table alone.

## Use checklist

Before selecting a provider:

- [ ] Confirm base URL, region, SDK package name, and current model ID in official documentation.
- [ ] Confirm input, output, streaming-event, and tool-call schema rather than copying another provider's shape.
- [ ] Set connection/read timeout, overall deadline, and a clear retry layer.
- [ ] Record source/SDK/model verification date and distinguish documentation review from actual execution.
- [ ] Use a test project or low-risk non-sensitive input to confirm error types and usage fields.
- [ ] Keep keys, complete prompts, files, and response bodies out of ordinary logs.

## Boundaries with later courses

- Unified vendor-SDK wrapping, streaming events, token use, and error normalization belong in [[llm-api-integration/00-index|LLM API Integration]].
- A model's structured tool request belongs in [[tool-calling-function-calling/00-index|Tool Calling (including Function Calling)]].
- Vector interfaces belong in [[embeddings/00-index|Embeddings]]; image, audio, and video capabilities return to their dedicated courses.
- General HTTP contract, retries, idempotency, and safe logging still follow [[api/00-index|API Learning Path]].

## Primary references

The main sources appear in the table and each provider note's frontmatter. Dynamic material follows the `source_checked` date on each page. This index was updated on **2026-07-22**; the OpenAI page retains its separate **2026-07-20** verification date.
