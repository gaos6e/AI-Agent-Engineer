---
title: DeepSeek API 调用
source: https://api-docs.deepseek.com/
source_checked: 2026-07-12
execution_verified: false
verification_note: "仅核对官方资料并做语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - DeepSeek
  - Python
aliases:
  - DeepSeek API
---

# DeepSeek API 调用

> [!source] 官方来源
> 基于 [DeepSeek API Docs](https://api-docs.deepseek.com/) 与 [Create Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion) 整理。DeepSeek 使用 OpenAI 兼容的 Chat Completions 格式，Python 中通常直接使用 `openai` 包。

## 常用能力

| 写法 | 用途 |
| --- | --- |
| `client.chat.completions.create()` | 文本、多轮、思考模式、JSON 和工具调用 |
| `stream=True` | 流式返回文本和思考内容 |
| `response_format={"type": "json_object"}` | JSON 模式 |
| `tools=[...]` | Function Calling |

## 安装与设置 API Key

```powershell
python -m pip install --upgrade openai
$env:DEEPSEEK_API_KEY = Read-Host 'DEEPSEEK_API_KEY' -MaskInput
```

## 1. 创建客户端与文本调用

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "你是一个简洁的中文技术老师。"},
        {"role": "user", "content": "用三点解释 API 调用。"},
    ],
)

print(response.choices[0].message.content)
print(response.usage)
```

`deepseek-v4-flash` 适合常规学习示例；更复杂任务可查看官方模型页后改用能力更强的模型。不要根据聊天网页显示名猜 API 模型名。

## 2. 多轮对话

API 无状态，需要把历史消息继续放进 `messages`：

```python
messages = [
    {"role": "system", "content": "你是 Python 老师。"},
    {"role": "user", "content": "列表是什么？"},
]

first = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=messages,
)

assistant_text = first.choices[0].message.content
messages.append({"role": "assistant", "content": assistant_text})
messages.append({"role": "user", "content": "给我一个 append 的例子。"})

second = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=messages,
)

print(second.choices[0].message.content)
```

## 3. 思考模式

DeepSeek 的扩展请求字段可通过 OpenAI SDK 的 `extra_body` 传入：

```python
response = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[
        {"role": "user", "content": "比较归并排序和快速排序。"},
    ],
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}},
)

message = response.choices[0].message
print(message.content)
```

思考配置、可用强度与返回字段会随模型变化，应按当前模型文档设置，不要默认所有模型都支持同一参数。

## 4. 流式输出

```python
stream = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": "写一份 Python API 学习建议。"}],
    stream=True,
)

for chunk in stream:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    if delta.content:
        print(delta.content, end="", flush=True)
```

思考模型流式返回时，可用 `getattr(delta, "reasoning_content", None)` 检查 SDK 暴露的思考增量，但不要把内部思考直接展示给最终用户或写入后续对话，除非官方模型文档明确要求保留。

## 5. JSON 模式

```python
import json

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {
            "role": "user",
            "content": (
                "请以 JSON 返回 Python 学习计划，字段为 topic、days、tasks。"
            ),
        }
    ],
    response_format={"type": "json_object"},
)

data = json.loads(response.choices[0].message.content)
print(data["tasks"])
```

启用 JSON 模式时，提示中也应明确要求输出 JSON。返回内容仍要经过 `json.loads()` 和业务字段校验。

## 6. Function Calling

```python
import json


def get_weather(city: str) -> dict:
    return {"city": city, "temperature": 25, "unit": "celsius"}


tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询指定城市的天气。",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
}]

messages = [{"role": "user", "content": "上海现在多少度？"}]
first = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=messages,
    tools=tools,
)

assistant_message = first.choices[0].message
messages.append(assistant_message)

for tool_call in assistant_message.tool_calls or []:
    if tool_call.function.name == "get_weather":
        arguments = json.loads(tool_call.function.arguments)
        result = get_weather(**arguments)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result, ensure_ascii=False),
        })

if assistant_message.tool_calls:
    final = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=messages,
        tools=tools,
    )
    print(final.choices[0].message.content)
else:
    print(assistant_message.content)
```

工具参数必须校验。若模型一次返回多个工具调用，应全部处理后再请求最终回答。

## 7. 常用生成参数

| 参数 | 作用 |
| --- | --- |
| `temperature` | 控制随机性；并非所有思考模型都建议修改 |
| `max_tokens` | 限制最大输出长度 |
| `stream` | 是否流式输出 |
| `response_format` | 请求 JSON 输出 |
| `tools` / `tool_choice` | 提供工具并控制使用方式 |
| `extra_body` | 传递 DeepSeek 特有扩展字段 |

## 错误处理

DeepSeek 使用 OpenAI Python SDK，因此可捕获 `openai.AuthenticationError`、`RateLimitError`、`APITimeoutError`、`APIConnectionError` 和 `APIStatusError`。常见问题包括 Key/额度错误、限流、模型名失效以及 `base_url` 配置错误。

## 常见易错点

- 忘记配置 `base_url="https://api.deepseek.com"`。
- 把 DeepSeek 特有字段直接当成 OpenAI SDK 标准参数；扩展字段通常放入 `extra_body`。
- 多轮对话没有保留历史消息。
- JSON 模式没有在提示中明确要求 JSON，或没有校验字段。
- 函数调用只执行工具，没有把 `tool` 消息回传给模型。
- 继续使用已废弃的旧模型名；应查看官方变更日志。

## 官方延伸阅读

- [DeepSeek API Docs](https://api-docs.deepseek.com/)
- [Create Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion)
- [Multi-round Conversation](https://api-docs.deepseek.com/guides/multi_round_chat)
- [JSON Output](https://api-docs.deepseek.com/guides/json_mode)
- [Function Calling](https://api-docs.deepseek.com/guides/function_calling)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
