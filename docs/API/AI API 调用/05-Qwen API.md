---
title: Qwen API 调用
source: https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen
source_checked: 2026-07-12
execution_verified: false
verification_note: "仅核对官方资料并做语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - Qwen
  - DashScope
  - Python
aliases:
  - 通义千问 API
  - DashScope API
---

# Qwen API 调用

> [!source] 官方来源
> 基于阿里云百炼 [首次调用通义千问 API](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen)、文本生成、流式输出和 Function Calling 文档整理。初学阶段优先使用 OpenAI 兼容接口，熟悉后再按需学习 DashScope SDK。

## 常用入口

| Python 写法 | 用途 |
| --- | --- |
| `client.chat.completions.create()` | 文本、多轮、图片、JSON 和工具调用 |
| `stream=True` | 流式输出 |
| `client.embeddings.create()` | OpenAI 兼容的文本向量接口 |
| `dashscope.Generation.call()` | DashScope 原生文本生成接口 |

## 安装与设置 API Key

```powershell
python -m pip install --upgrade openai
$env:DASHSCOPE_API_KEY = Read-Host 'DASHSCOPE_API_KEY' -MaskInput
```

## 1. 地域与客户端

API Key 与地域 endpoint 必须匹配。常见兼容地址包括：

| 地域 | `base_url` |
| --- | --- |
| 中国内地 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| 新加坡（国际） | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |

专属 Workspace 可能使用带 `{WorkspaceId}` 的地址，应直接复制控制台或当前官方文档给出的 endpoint。

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DASHSCOPE_API_KEY"],
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
```

## 2. 文本生成

```python
response = client.chat.completions.create(
    model="qwen3.7-plus",
    messages=[
        {"role": "system", "content": "你是一个简洁的中文技术老师。"},
        {"role": "user", "content": "用三点解释 API 调用。"},
    ],
)

print(response.choices[0].message.content)
print(response.usage)
```

模型系列更新较快。`qwen3.7-plus` 适合通用学习示例，低延迟、代码、视觉或超长上下文任务应从 [模型列表](https://help.aliyun.com/zh/model-studio/models) 重新选型。

## 3. 多轮对话

```python
messages = [
    {"role": "system", "content": "你是 Python 老师。"},
    {"role": "user", "content": "字典是什么？"},
]

first = client.chat.completions.create(
    model="qwen3.7-plus",
    messages=messages,
)

messages.append({
    "role": "assistant",
    "content": first.choices[0].message.content,
})
messages.append({"role": "user", "content": "给一个读取键值的例子。"})

second = client.chat.completions.create(
    model="qwen3.7-plus",
    messages=messages,
)

print(second.choices[0].message.content)
```

## 4. 流式输出与 Token 统计

```python
stream = client.chat.completions.create(
    model="qwen3.7-plus",
    messages=[{"role": "user", "content": "写一份 Python API 学习建议。"}],
    stream=True,
    stream_options={"include_usage": True},
)

for chunk in stream:
    if chunk.choices:
        text = chunk.choices[0].delta.content or ""
        print(text, end="", flush=True)
    elif chunk.usage:
        print("\nToken：", chunk.usage.total_tokens)
```

最后一个仅含 `usage` 的 chunk 可能没有 `choices`，因此要先判断。

## 5. 图片理解

```python
response = client.chat.completions.create(
    model="qwen3-vl-plus",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"
                    },
                },
                {"type": "text", "text": "解释图表趋势并提取坐标轴名称。"},
            ],
        }
    ],
)

print(response.choices[0].message.content)
```

图像、视频、音频的支持取决于模型系列。不要把文本模型与 `Qwen-VL`、`Qwen-Omni` 的输入格式混用。

## 6. JSON 模式

```python
import json

response = client.chat.completions.create(
    model="qwen3.7-plus",
    messages=[{
        "role": "user",
        "content": "请用 JSON 返回学习计划，字段为 topic、days、tasks。",
    }],
    response_format={"type": "json_object"},
)

data = json.loads(response.choices[0].message.content)
print(data["tasks"])
```

提示中必须明确要求 JSON，并在 Python 中继续做解析和字段校验。

## 7. Function Calling

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
    model="qwen3.7-plus",
    messages=messages,
    tools=tools,
    tool_choice="auto",
)

assistant_message = first.choices[0].message
messages.append(assistant_message)

for tool_call in assistant_message.tool_calls or []:
    arguments = json.loads(tool_call.function.arguments)
    result = get_weather(**arguments)
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": json.dumps(result, ensure_ascii=False),
    })

if assistant_message.tool_calls:
    final = client.chat.completions.create(
        model="qwen3.7-plus",
        messages=messages,
        tools=tools,
    )
    print(final.choices[0].message.content)
```

思考模型做工具调用时，部分模型要求保留 `reasoning_content`；应查看所选模型的 Function Calling 注意事项。

## 8. 文本 Embedding

```python
embedding_response = client.embeddings.create(
    model="text-embedding-v4",
    input=[
        "Python 适合快速开发。",
        "Rust 重视性能和内存安全。",
    ],
)

vectors = [item.embedding for item in embedding_response.data]
print(len(vectors), len(vectors[0]))
```

不同 embedding 模型支持的地域、维度和输入类型不同；向量入库与查询必须保持相同模型和维度。

## 9. DashScope SDK 基础写法

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
    messages=[
        {"role": "user", "content": "用三点解释 API 调用。"},
    ],
    result_format="message",
)

print(response.output.choices[0].message.content)
```

OpenAI 兼容接口便于迁移；DashScope SDK 更接近阿里云原生能力。一个项目中应明确主调用方式，避免响应对象混用。

## 常见易错点

- API Key 与地域 endpoint 不匹配。
- 最后一个流式 chunk 没有 `choices`，代码却直接访问下标。
- 文本、视觉、Omni 模型的输入格式混用。
- 工具调用没有回传 `tool_call_id` 对应结果。
- 依赖模型别名却不关注升级和下线公告。
- 同时使用 OpenAI SDK 与 DashScope SDK，却按同一种响应结构取值。

## 官方延伸阅读

- [首次调用通义千问 API](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen)
- [文本生成](https://help.aliyun.com/zh/model-studio/text-generation)
- [流式输出](https://help.aliyun.com/zh/model-studio/stream)
- [Function Calling](https://help.aliyun.com/zh/model-studio/qwen-function-calling)
- [视觉理解](https://help.aliyun.com/zh/model-studio/vision-model)
- [向量化](https://help.aliyun.com/zh/model-studio/embedding)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
