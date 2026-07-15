---
title: Cohere API 调用
source: https://docs.cohere.com/v2/cohere-documentation
source_checked: 2026-07-12
execution_verified: false
verification_note: "仅核对官方资料并做语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - Cohere
  - Python
aliases:
  - Cohere API
---

# Cohere API 调用

> [!source] 官方来源
> 基于 Cohere v2 的 Chat、Embed、Rerank、Tool Use 与 Structured Outputs 文档整理。当前 Python 主客户端是 `cohere.ClientV2`。

## 常用入口

| Python 方法 | 用途 |
| --- | --- |
| `co.chat()` | 文本、多轮、RAG、JSON 和工具调用 |
| `co.chat_stream()` | 流式聊天 |
| `co.embed()` | 文本、图片或混合内容向量化 |
| `co.rerank()` | 按查询相关性重新排序文档 |

Cohere 的特色是生成、Embedding 与 Rerank 可以组合成 RAG 流程。

## 安装与设置 API Key

```powershell
python -m pip install --upgrade cohere
$env:COHERE_API_KEY = Read-Host 'COHERE_API_KEY' -MaskInput
```

## 1. 文本生成

```python
import os
import cohere

co = cohere.ClientV2(api_key=os.environ["COHERE_API_KEY"])

response = co.chat(
    model="command-a-plus-05-2026",
    messages=[
        {"role": "system", "content": "你是一个简洁的中文技术老师。"},
        {"role": "user", "content": "用三点解释 API 调用。"},
    ],
)

print(response.message.content[0].text)
print(response.usage)
```

模型更新较快，应从 [Models](https://docs.cohere.com/v2/docs/models) 核对当前可用 ID，不要继续使用 v1 时代的旧 `command` 别名。

## 2. 多轮对话

```python
messages = [
    {"role": "system", "content": "你是 Python 老师。"},
    {"role": "user", "content": "字典是什么？"},
]

first = co.chat(model="command-a-plus-05-2026", messages=messages)
assistant_text = first.message.content[0].text

messages.append({"role": "assistant", "content": assistant_text})
messages.append({"role": "user", "content": "给一个读取键值的例子。"})

second = co.chat(model="command-a-plus-05-2026", messages=messages)
print(second.message.content[0].text)
```

v2 已把当前消息和历史统一放入 `messages`，不要照搬 v1 的 `message=` 与 `chat_history=` 写法。

## 3. 流式输出

```python
stream = co.chat_stream(
    model="command-a-plus-05-2026",
    messages=[
        {"role": "user", "content": "写一份 Python API 学习建议。"},
    ],
)

for event in stream:
    if event.type == "content-delta":
        print(event.delta.message.content.text, end="", flush=True)
```

工具调用和流式响应还会出现其他事件类型；复杂应用应按 `event.type` 分支处理，而不是假设所有事件都有文本。

## 4. 结构化 JSON 输出

```python
import json

response = co.chat(
    model="command-a-plus-05-2026",
    messages=[{
        "role": "user",
        "content": "生成一个 7 天 Python API 学习计划，并输出 JSON。",
    }],
    response_format={
        "type": "json_object",
        "schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "days": {"type": "integer"},
                "tasks": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["topic", "days", "tasks"],
        },
    },
)

data = json.loads(response.message.content[0].text)
print(data["tasks"])
```

启用 JSON 输出时，提示中也应明确提到 JSON。若当前 SDK 的 schema 字段签名有变化，以 v2 Chat API Reference 为准。

## 5. 给 Chat 提供检索文档

```python
documents = [
    "venv 用于隔离项目依赖。",
    "pip 用于安装 Python 包。",
]

response = co.chat(
    model="command-a-plus-05-2026",
    messages=[{"role": "user", "content": "venv 有什么作用？"}],
    documents=documents,
)

print(response.message.content[0].text)
print(response.message.citations)
```

这适合把已经检索到的少量相关文档交给模型回答。大规模 RAG 通常先 Embed 检索，再 Rerank，最后 Chat。

## 6. Embedding

```python
response = co.embed(
    model="embed-v4.0",
    texts=[
        "Python 适合快速开发。",
        "Rust 重视性能和内存安全。",
    ],
    input_type="search_document",
    output_dimension=1024,
    embedding_types=["float"],
)

vectors = response.embeddings.float
print(len(vectors), len(vectors[0]))
```

语义搜索时必须区分输入类型：

- 入库文档：`input_type="search_document"`
- 用户查询：`input_type="search_query"`
- 分类：`classification`
- 聚类：`clustering`

查询向量示例：

```python
query_response = co.embed(
    model="embed-v4.0",
    texts=["哪种语言适合快速开发？"],
    input_type="search_query",
    output_dimension=1024,
    embedding_types=["float"],
)

query_vector = query_response.embeddings.float[0]
```

入库与查询要保持同一模型、输出维度和 embedding 类型。

## 7. Rerank

Rerank 接收一个查询和若干候选文档，返回按相关性重新排序的结果：

```python
documents = [
    "venv 用于隔离 Python 项目的依赖。",
    "Git 用于版本控制。",
    "pip 用于安装 Python 包。",
]

response = co.rerank(
    model="rerank-v4.0-pro",
    query="如何避免两个 Python 项目的依赖冲突？",
    documents=documents,
    top_n=2,
)

for result in response.results:
    print(result.index, result.relevance_score, documents[result.index])
```

`rerank-v4.0-pro` 偏质量，`rerank-v4.0-fast` 偏低延迟与高吞吐。Rerank 不生成答案，只负责排序。

## 8. Function Calling

```python
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

response = co.chat(
    model="command-a-plus-05-2026",
    messages=[{"role": "user", "content": "上海现在多少度？"}],
    tools=tools,
)

for tool_call in response.message.tool_calls or []:
    print(tool_call.function.name, tool_call.function.arguments)
```

完整流程还需由 Python 执行函数，并使用对应的 `tool_call_id` 把工具结果作为 `tool` 消息发回。执行前必须验证参数。

## 常见易错点

- 使用 `Client` 或 v1 的 `message=` 写法，却按 v2 文档取响应。
- 流式事件不判断 `event.type`。
- Embedding 入库和查询都使用同一个 `input_type`。
- 向量维度或模型不一致，导致无法比较。
- 把 Rerank 当作生成模型；它只返回排序和相关性分数。
- 使用过时 Command 模型 ID。

## 官方延伸阅读

- [Cohere Documentation](https://docs.cohere.com/v2/cohere-documentation)
- [Chat API](https://docs.cohere.com/v2/docs/chat-api)
- [Chat Streaming](https://docs.cohere.com/v2/reference/chat-stream)
- [Embeddings](https://docs.cohere.com/v2/docs/embeddings)
- [Rerank](https://docs.cohere.com/v2/docs/rerank)
- [Tool Use](https://docs.cohere.com/v2/docs/tool-use-overview)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
