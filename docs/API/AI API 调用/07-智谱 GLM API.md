---
title: 智谱 GLM API 调用
source: https://docs.bigmodel.cn/cn/guide/develop/python/introduction
source_checked: 2026-07-12
execution_verified: false
verification_note: "仅核对官方资料并做语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - GLM
  - Zhipu
  - Python
aliases:
  - 智谱 API
  - BigModel API
  - Z.AI API
---

# 智谱 GLM API 调用

> [!source] 官方来源
> 基于 [官方 Python SDK](https://docs.bigmodel.cn/cn/guide/develop/python/introduction)、流式消息、视觉理解和工具调用文档整理。中国智谱开放平台使用 `ZhipuAiClient`，Python 包名为 `zai-sdk`。

## 常用入口

| Python 方法 | 用途 |
| --- | --- |
| `client.chat.completions.create()` | 文本、多轮、流式、视觉和工具调用 |
| `client.embeddings.create()` | 文本向量 |
| `client.images.generations()` | 图像生成；按当前 SDK 版本核对签名 |
| `client.models.list()` | 查看可用模型；若当前 SDK/账户支持 |

## 安装与设置 API Key

```powershell
python -m pip install --upgrade zai-sdk
$env:ZAI_API_KEY = Read-Host 'ZAI_API_KEY' -MaskInput
```

> [!note]
> 历史代码可能使用 `zhipuai` 包或 `ZHIPUAI_API_KEY`。本笔记使用当前 `zai-sdk` 与 `ZAI_API_KEY`，不要混用两套示例。

## 1. 文本生成

```python
from zai import ZhipuAiClient

client = ZhipuAiClient()

response = client.chat.completions.create(
    model="glm-5.1",
    messages=[
        {"role": "system", "content": "你是一个简洁的中文技术老师。"},
        {"role": "user", "content": "用三点解释 API 调用。"},
    ],
    temperature=0.6,
)

print(response.choices[0].message.content)
print(response.usage)
```

模型名更新较快，应从 [模型概览](https://docs.bigmodel.cn/cn/guide/start/model-overview) 选择。文本、视觉、图像生成和视频生成使用不同模型系列。

## 2. 多轮对话

```python
messages = [
    {"role": "system", "content": "你是 Python 老师。"},
    {"role": "user", "content": "字典是什么？"},
]

first = client.chat.completions.create(model="glm-5.1", messages=messages)
messages.append({
    "role": "assistant",
    "content": first.choices[0].message.content,
})
messages.append({"role": "user", "content": "给一个读取键值的例子。"})

second = client.chat.completions.create(model="glm-5.1", messages=messages)
print(second.choices[0].message.content)
```

## 3. 流式输出

```python
stream = client.chat.completions.create(
    model="glm-5.1",
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

思考模型可能在 `delta.reasoning_content` 中返回思考增量，最后一个 chunk 还可能包含 `finish_reason` 和 `usage`。

## 4. 图片理解

```python
response = client.chat.completions.create(
    model="glm-4.6v",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "解释图表趋势并提取坐标轴名称。"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://api.nga.gov/iiif/a2e6da57-3cd1-4235-b20e-95dcaefed6c8/full/!800,800/0/default.jpg"
                    },
                },
            ],
        }
    ],
)

print(response.choices[0].message.content)
```

本地图片可编码为 `data:image/png;base64,...`。图片格式、大小与模型能力以视觉模型文档为准。

## 5. Function Calling

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
    model="glm-5.1",
    messages=messages,
    tools=tools,
    tool_choice="auto",
)

assistant_message = first.choices[0].message
messages.append(assistant_message.model_dump())

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
        model="glm-5.1",
        messages=messages,
        tools=tools,
    )
    print(final.choices[0].message.content)
```

如果一次返回多个 `tool_calls`，应全部执行并回传。高风险函数必须做参数校验和人工确认。

## 6. 内置 Web Search

```python
response = client.chat.completions.create(
    model="glm-5.1",
    messages=[
        {"role": "user", "content": "查找今天 Python 官方生态的重要更新。"},
    ],
    tools=[
        {
            "type": "web_search",
            "web_search": {
                "search_query": "Python 官方更新",
                "search_result": True,
            },
        }
    ],
)

print(response.choices[0].message.content)
```

工具支持情况取决于模型和套餐，生产中应检查搜索结果及引用，而不是只信最终总结。

## 7. Embedding

```python
response = client.embeddings.create(
    model="embedding-3",
    input=[
        "Python 适合快速开发。",
        "Rust 重视性能和内存安全。",
    ],
)

vectors = [item.embedding for item in response.data]
print(len(vectors), len(vectors[0]))
```

Embedding 用于语义搜索、相似度、聚类和 RAG。向量入库与查询要使用同一模型及相同维度。

## 错误处理

```python
import zai

try:
    response = client.chat.completions.create(
        model="glm-5.1",
        messages=[{"role": "user", "content": "你好"}],
    )
except zai.core.APIStatusError as exc:
    print("API 状态错误：", exc)
except zai.core.APITimeoutError:
    print("请求超时。")
```

这里只捕获当前示例能采取明确动作的 SDK 异常；未识别异常应保留调用栈并由应用边界统一记录，不用宽泛 `except Exception` 吞掉。

## 常见易错点

- `zai-sdk` 与旧 `zhipuai` 包混用。
- `ZAI_API_KEY` 与历史环境变量名混用。
- 通用 API endpoint 与 Coding 套餐 endpoint 混用。
- 文本模型处理图片，或把不同视觉模型的参数直接套用。
- 工具执行后没有回传 `tool_call_id`。
- 没有根据当前 SDK 版本核对图像生成、视频生成等低频方法签名。

## 官方延伸阅读

- [官方 Python SDK](https://docs.bigmodel.cn/cn/guide/develop/python/introduction)
- [流式消息](https://docs.bigmodel.cn/cn/guide/capabilities/streaming)
- [工具调用](https://docs.bigmodel.cn/cn/guide/capabilities/function-calling)
- [思考模式](https://docs.bigmodel.cn/cn/guide/capabilities/thinking-mode)
- [模型概览](https://docs.bigmodel.cn/cn/guide/start/model-overview)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
