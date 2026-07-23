---
title: "Qwen API Calls"
source: https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen
source_checked: 2026-07-22
source_baseline:
  - Model Studio first Qwen API call, text-generation models, structured output,
    and tool calling
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "Current model recommendations, capability matrix, and
  primary call paths were checked with offline syntax validation; no real
  credentials or network calls were used."
tags: [ api, ai-api, qwen, dashscope, python ]
aliases: [ Qwen API, DashScope API ]
lang: en
translation_key: API/AI API 调用/05-Qwen API.md
translation_source_hash: f9236c6f2b308cb230d3035109e4a09d2966763865c6bd45db0a25812dbbc423
translation_route: zh-CN/API/AI-API-调用/05-Qwen-API
translation_default_route: zh-CN/API/AI-API-调用/05-Qwen-API
---

# Qwen API Calls

> [!source] Official source
> Based on Alibaba Cloud Model Studio documentation for [the first Qwen API call](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen), text generation, streaming, and Function Calling. Start with the OpenAI-compatible interface; learn the DashScope SDK as native capabilities require it.

## Common entry points and regional boundary

| Form | Use |
| --- | --- |
| `client.chat.completions.create()` | Text, history, images, JSON, and tool calls. |
| `stream=True` | Stream output. |
| `client.embeddings.create()` | OpenAI-compatible text vectors. |
| `dashscope.Generation.call()` | Native DashScope text generation. |

The key and regional endpoint must match:

| Region | `base_url` |
| --- | --- |
| Mainland China | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| Singapore (international) | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |

A dedicated Workspace can use an endpoint containing `{WorkspaceId}`; copy it from the current console or official documentation.

```powershell
python -m pip install --upgrade openai
$env:DASHSCOPE_API_KEY = Read-Host 'DASHSCOPE_API_KEY' -MaskInput
```

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DASHSCOPE_API_KEY"],
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
messages = [
    {"role": "system", "content": "You are a concise technical teacher."},
    {"role": "user", "content": "Explain an API call in three points."},
]
response = client.chat.completions.create(model="qwen3.7-plus", messages=messages)
print(response.choices[0].message.content, response.usage)
```

On 2026-07-22, the official text-model page listed `qwen3.7-plus` as a balanced Agent/general-task recommendation with 1M context, thinking, Function Calling, built-in tools, and structured-output support. The matrix is not proof of entitlement for every region, account, endpoint, or plan. Re-select low-latency, code, vision, or long-context models in the [model list](https://help.aliyun.com/zh/model-studio/models) and target-region console.

## History, streaming, vision, and JSON

The compatible interface is stateless; append assistant text and the next user turn to the same ordered `messages` list before sending it again.

```python
stream = client.chat.completions.create(
    model="qwen3.7-plus",
    messages=[{"role": "user", "content": "Write a Python API study plan."}],
    stream=True,
    stream_options={"include_usage": True},
)
for chunk in stream:
    if chunk.choices:
        print(chunk.choices[0].delta.content or "", end="", flush=True)
    elif chunk.usage:
        print("\nTokens:", chunk.usage.total_tokens)
```

The final usage-only chunk can have no `choices`; guard it before indexing.

```python
import json

vision = client.chat.completions.create(
    model="qwen3-vl-plus",
    messages=[{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"}},
        {"type": "text", "text": "Explain the chart trend and name its axes."},
    ]}],
)

structured = client.chat.completions.create(
    model="qwen3.7-plus",
    messages=[{"role": "user", "content": "Return JSON with topic, days, and tasks."}],
    response_format={"type": "json_object"},
)
data = json.loads(structured.choices[0].message.content)
```

Do not mix text-model, Qwen-VL, and Qwen-Omni input shapes. JSON mode needs an explicit JSON instruction plus local parsing and field/range validation.

## Tools, embeddings, and native SDK

Use the compatible tool loop exactly as a normal Chat Completions contract: validate model JSON locally; execute only allowlisted, authorized tools; append one `role: "tool"` result with the matching `tool_call_id`; then send the full history for a final answer. Some thinking models require retaining `reasoning_content`; check current Function Calling notes for the selected model.

```python
embedding_response = client.embeddings.create(
    model="text-embedding-v4",
    input=["Python is suitable for rapid development.", "Rust emphasizes performance and memory safety."],
)
vectors = [item.embedding for item in embedding_response.data]
print(len(vectors), len(vectors[0]))
```

Indexing and query need the same embedding model and dimension; available region, dimensions, and input type vary by model.

```powershell
python -m pip install --upgrade dashscope
```

```python
import os
import dashscope
from dashscope import Generation

dashscope.api_key = os.environ["DASHSCOPE_API_KEY"]
response = Generation.call(
    model="qwen3.7-plus",
    messages=[{"role": "user", "content": "Explain an API call in three points."}],
    result_format="message",
)
print(response.output.choices[0].message.content)
```

The compatible interface eases migration; DashScope SDK exposes Alibaba-native features. Select one primary call style in a project and do not read both response objects as though their shapes were identical.

## Common mistakes and sources

- Mismatched key and regional endpoint.
- Directly indexing `choices` in the final usage-only stream chunk.
- Mixing text, vision, and Omni input shapes.
- Returning no `tool_call_id`-matched tool result.
- Relying on aliases while ignoring upgrade and retirement notices.
- Mixing OpenAI SDK and DashScope SDK response conventions.

- [First Qwen API call](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen)
- [Text generation](https://help.aliyun.com/zh/model-studio/text-generation)
- [Streaming](https://help.aliyun.com/zh/model-studio/stream)
- [Function Calling](https://help.aliyun.com/zh/model-studio/qwen-function-calling)
- [Vision](https://help.aliyun.com/zh/model-studio/vision-model)
- [Embeddings](https://help.aliyun.com/zh/model-studio/embedding)

Return to [[api/ai-api-reference/00-index|Vendor AI API Reference Index]]; general HTTP reliability remains in [[api/00-index|API Learning Path]].

