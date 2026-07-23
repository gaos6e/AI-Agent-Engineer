---
title: "DeepSeek API Calls"
source: https://api-docs.deepseek.com/
source_checked: 2026-07-22
source_baseline:
  - DeepSeek Your First API Call, Models & Pricing, Thinking Mode, Tool Calls
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "The official entry point and model-migration notice were
  checked with offline syntax validation; no real credentials or network calls
  were used."
tags: [ api, ai-api, deepseek, python ]
aliases: [ DeepSeek API ]
lang: en
translation_key: API/AI API 调用/04-DeepSeek API.md
translation_source_hash: 9a989505f3456b8381b93dd55a5317d7a6fbbe80973a2e66852de9b7e8346e26
translation_route: zh-CN/API/AI-API-调用/04-DeepSeek-API
translation_default_route: zh-CN/API/AI-API-调用/04-DeepSeek-API
---

# DeepSeek API Calls

> [!source] Official source
> Based on [DeepSeek API Docs](https://api-docs.deepseek.com/) and [Create Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion). DeepSeek uses an OpenAI-compatible Chat Completions shape and commonly uses the `openai` Python package.

> [!warning] Legacy model migration has a fixed deadline
> The official home page checked on 2026-07-22 scheduled `deepseek-chat` and `deepseek-reasoner` for deprecation at **2026-07-24 15:59 UTC**. During compatibility, they correspond respectively to non-thinking and thinking modes of `deepseek-v4-flash`. Do not use legacy names as new defaults. A controlled migration explicitly sets and evaluates `thinking` / `reasoning_effort`, tool calls, context, and cost—not just a model string.

## Main capabilities

| Form | Use |
| --- | --- |
| `client.chat.completions.create()` | Text, multi-turn history, thinking mode, JSON, and function calls. |
| `stream=True` | Stream text and thinking content. |
| `response_format={"type": "json_object"}` | JSON mode. |
| `tools=[...]` | Function Calling. |

## Client, text, and history

```powershell
python -m pip install --upgrade openai
$env:DEEPSEEK_API_KEY = Read-Host 'DEEPSEEK_API_KEY' -MaskInput
```

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

messages = [
    {"role": "system", "content": "You are a concise technical teacher."},
    {"role": "user", "content": "Explain an API call in three points."},
]
response = client.chat.completions.create(
    model="deepseek-v4-flash", messages=messages
)
assistant_text = response.choices[0].message.content
print(assistant_text, response.usage)

messages.extend([
    {"role": "assistant", "content": assistant_text},
    {"role": "user", "content": "Give an append example."},
])
second = client.chat.completions.create(
    model="deepseek-v4-flash", messages=messages
)
print(second.choices[0].message.content)
```

The API is stateless: preserve and resend ordered history. `deepseek-v4-flash` is the teaching default; select a stronger model only after checking current model documentation. Do not guess API model IDs from a chat-product display name.

## Thinking, streaming, and JSON

```python
thoughtful = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[{"role": "user", "content": "Compare merge sort and quicksort."}],
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}},
)

stream = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": "Write a Python API study plan."}],
    stream=True,
)
for chunk in stream:
    if chunk.choices:
        delta = chunk.choices[0].delta
        if delta.content:
            print(delta.content, end="", flush=True)
```

Thinking configuration, supported effort levels, and returned fields are model-specific. Use `extra_body` for DeepSeek-specific extensions rather than treating them as standard OpenAI SDK arguments. A streaming reasoning model can expose `reasoning_content` through the SDK; do not display internal reasoning to an end user or feed it into subsequent conversation unless the current model documentation explicitly requires it.

```python
import json

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": "Return a JSON study plan with topic, days, and tasks."}],
    response_format={"type": "json_object"},
)
data = json.loads(response.choices[0].message.content)
print(data["tasks"])
```

JSON mode still requires a prompt that explicitly requests JSON plus local `json.loads()` and business-field validation.

## Function Calling

```python
import json


def get_weather(city: str) -> dict:
    return {"city": city, "temperature": 25, "unit": "celsius"}


tools = [{"type": "function", "function": {
    "name": "get_weather",
    "description": "Look up weather for a city.",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
}}]
messages = [{"role": "user", "content": "What is the temperature in Shanghai now?"}]
first = client.chat.completions.create(
    model="deepseek-v4-pro", messages=messages, tools=tools
)
assistant_message = first.choices[0].message
messages.append(assistant_message)
for tool_call in assistant_message.tool_calls or []:
    if tool_call.function.name != "get_weather":
        raise ValueError("unknown tool")
    arguments = json.loads(tool_call.function.arguments)
    result = get_weather(**arguments)
    messages.append({
        "role": "tool", "tool_call_id": tool_call.id,
        "content": json.dumps(result, ensure_ascii=False),
    })
if assistant_message.tool_calls:
    final = client.chat.completions.create(
        model="deepseek-v4-pro", messages=messages, tools=tools
    )
    print(final.choices[0].message.content)
```

Validate tool arguments, authorization, and side-effect approval before execution. Process every returned call, return one `tool_call_id`-matched tool message per call, then request a final answer. A missing history, an unreturned tool result, or unvalidated JSON breaks the protocol.

## Parameters, failures, and sources

| Parameter | Meaning |
| --- | --- |
| `temperature` | Randomness; not all thinking models recommend changing it. |
| `max_tokens` | Maximum output length. |
| `stream` | Stream response chunks. |
| `response_format` | Request JSON output. |
| `tools` / `tool_choice` | Offer and control tools. |
| `extra_body` | Pass DeepSeek-specific extensions. |

Capture `openai.AuthenticationError`, `RateLimitError`, `APITimeoutError`, `APIConnectionError`, and `APIStatusError`; typical causes are key/quota, rate limit, stale model ID, and incorrect `base_url`. Do not omit `base_url`, treat DeepSeek extensions as universal SDK parameters, drop multi-turn history, skip JSON validation, or fail to return tool results.

- [DeepSeek API Docs](https://api-docs.deepseek.com/)
- [Create Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion)
- [Multi-round Conversation](https://api-docs.deepseek.com/guides/multi_round_chat)
- [JSON Output](https://api-docs.deepseek.com/guides/json_mode)
- [Function Calling](https://api-docs.deepseek.com/guides/function_calling)

Return to [[api/ai-api-reference/00-index|Vendor AI API Reference Index]]; use [[api/00-index|API Learning Path]] for HTTP reliability.

