---
title: xAI Grok API 调用
source: https://docs.x.ai/developers/quickstart
source_checked: 2026-07-12
execution_verified: false
verification_note: "仅核对官方资料并做语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - xAI
  - Grok
  - Python
aliases:
  - Grok API
  - xAI API
---

# xAI Grok API 调用

> [!source] 官方来源
> 基于 [xAI Quickstart](https://docs.x.ai/developers/quickstart)、官方 Python SDK、Responses API、Function Calling 和 Agent Tools 文档整理。xAI 同时提供原生 `xai-sdk` 和 OpenAI 兼容接口。

## 两种调用方式

| 方式 | 适合场景 |
| --- | --- |
| `xai-sdk` | 多轮聊天、xAI 原生搜索/代码工具、图片和视频等能力 |
| `openai` 兼容接口 | 已熟悉 Responses API，或从 OpenAI 代码迁移 |

初学者可以先选一种主线。下面先介绍原生 SDK，再补充 OpenAI 兼容写法。

## 安装与设置 API Key

```powershell
python -m pip install --upgrade xai-sdk openai
$env:XAI_API_KEY = Read-Host 'XAI_API_KEY' -MaskInput
```

## 1. xAI SDK 文本调用

```python
from xai_sdk import Client
from xai_sdk.chat import system, user

client = Client()

chat = client.chat.create(model="grok-4.5")
chat.append(system("你是一个简洁、准确的中文技术老师。"))
chat.append(user("用三点解释 API 调用。"))

response = chat.sample()
print(response.content)
```

模型名更新较快，应从 [Models](https://docs.x.ai/developers/models) 复制当前 ID。不要把网页产品名称直接当成 API 模型名。

## 2. xAI SDK 多轮对话

```python
chat = client.chat.create(model="grok-4.5")

chat.append(user("Python 的字典是什么？"))
first = chat.sample()
print(first.content)
chat.append(first)

chat.append(user("给一个读取键值的例子。"))
second = chat.sample()
print(second.content)
```

底层 API 仍是无状态的，`chat` 对象只是在客户端帮助维护历史。需要跨进程恢复时，应由应用持久化会话。

## 3. xAI SDK 流式输出

```python
chat = client.chat.create(model="grok-4.5")
chat.append(user("写一份 Python API 学习建议。"))

final_response = None
for response, chunk in chat.stream():
    final_response = response
    print(chunk.content, end="", flush=True)

if final_response is not None:
    chat.append(final_response)
```

`chat.stream()` 同时返回持续累积的 `response` 与当前 `chunk`，这与 OpenAI SDK 的流式事件结构不同。

## 4. OpenAI 兼容 Responses API

```python
import os
from openai import OpenAI

openai_client = OpenAI(
    api_key=os.environ["XAI_API_KEY"],
    base_url="https://api.x.ai/v1",
)

response = openai_client.responses.create(
    model="grok-4.5",
    instructions="你是一个简洁、准确的中文技术老师。",
    input="用三点解释 API 调用。",
)

print(response.output_text)
```

常用入口仍是 `responses.create()`；旧 Chat Completions 主要用于兼容既有项目，新功能优先看 Responses 文档。

## 5. 兼容接口的流式输出

```python
stream = openai_client.responses.create(
    model="grok-4.5",
    input="写一份 Python API 学习建议。",
    stream=True,
)

for event in stream:
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
```

工具调用、失败和完成也会产生其他事件，应按 `event.type` 处理。

## 6. 图片理解

```python
response = openai_client.responses.create(
    model="grok-4.5",
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "解释图表趋势并提取坐标轴名称。"},
                {
                    "type": "input_image",
                    "image_url": "https://api.nga.gov/iiif/a2e6da57-3cd1-4235-b20e-95dcaefed6c8/full/!800,800/0/default.jpg",
                },
            ],
        }
    ],
)

print(response.output_text)
```

必须使用支持视觉输入的模型。图片格式、大小和 token 计算以当前 Image Understanding 文档为准。

## 7. 服务端搜索工具

xAI 原生 SDK 可让 Grok 使用 Web 搜索、X 搜索等服务端工具：

```python
from xai_sdk.chat import user
from xai_sdk.tools import web_search, x_search

chat = client.chat.create(
    model="grok-4.5",
    tools=[web_search(), x_search()],
)
chat.append(user("查找今天 Python 官方生态的重要更新，并附来源。"))

response = chat.sample()
print(response.content)
```

可用工具与返回引用结构会随 SDK 和账户变化。需要可核验结果时，应检查工具调用详情和 citations，而不是只保存最终文本。

## 8. 自定义函数调用

以下使用 OpenAI 兼容 Responses 格式：

```python
import json


def get_weather(city: str) -> dict:
    return {"city": city, "temperature": 25, "unit": "celsius"}


tools = [{
    "type": "function",
    "name": "get_weather",
    "description": "查询指定城市的天气。",
    "parameters": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
        "additionalProperties": False,
    },
}]

response = openai_client.responses.create(
    model="grok-4.5",
    input="上海现在多少度？",
    tools=tools,
)

tool_outputs = []
for item in response.output:
    if item.type == "function_call" and item.name == "get_weather":
        arguments = json.loads(item.arguments)
        result = get_weather(**arguments)
        tool_outputs.append({
            "type": "function_call_output",
            "call_id": item.call_id,
            "output": json.dumps(result, ensure_ascii=False),
        })

if tool_outputs:
    final = openai_client.responses.create(
        model="grok-4.5",
        input=tool_outputs,
        tools=tools,
        previous_response_id=response.id,
    )
    print(final.output_text)
```

xAI 默认可并行请求多个函数。应处理全部调用、校验参数，再继续对话。

## 9. 常见原生 SDK 能力

官方 xAI SDK 还提供以下入口，属于按需学习内容：

| 能力 | 常见入口 |
| --- | --- |
| 图像生成 | `client.image` 相关方法 |
| 视频生成 | `client.video.generate()` |
| 模型信息 | `client.models` 相关方法 |
| Tokenization | `client.tokenize` 相关方法 |
| 延迟任务 | deferred chat / polling |

这些能力的模型、参数和返回对象变化较快，使用前应直接打开当前 SDK 示例，不建议从旧教程复制整段代码。

## 常见易错点

- 原生 `xai-sdk` 与 OpenAI 兼容 SDK 的响应对象混用。
- 兼容调用忘记 `base_url="https://api.x.ai/v1"`。
- 流式代码混用 `chat.stream()` 的 tuple 与 Responses 的 event。
- 使用旧 Chat Completions 示例学习新工具能力。
- 搜索工具只读取最终文本，没有保留引用。
- 并行函数调用只处理第一个工具。
- 模型名来自聊天产品界面，而不是 API Models 页。

## 官方延伸阅读

- [xAI Quickstart](https://docs.x.ai/developers/quickstart)
- [Official Python SDK](https://github.com/xai-org/xai-sdk-python)
- [Responses API](https://docs.x.ai/developers/api-reference#responses)
- [Function Calling](https://docs.x.ai/developers/tools/function-calling)
- [Web Search](https://docs.x.ai/developers/tools/web-search)
- [Image Understanding](https://docs.x.ai/developers/image-understanding)
- [Models](https://docs.x.ai/developers/models)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
