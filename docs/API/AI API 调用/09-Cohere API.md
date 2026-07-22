---
title: Cohere API 调用
source: https://docs.cohere.com/v2/cohere-documentation
source_checked: 2026-07-22
source_baseline:
  - Cohere v2 Chat、Embed、Rerank、Tool Use 与 Structured Outputs
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "已核对当前 v2 Chat reference 与模型/组合限制并做离线语法检查；未使用真实凭据执行网络调用"
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
python -m pip install --upgrade cohere  # 安装或更新 Cohere 官方 Python SDK。
$env:COHERE_API_KEY = Read-Host 'COHERE_API_KEY' -MaskInput  # 仅在当前 PowerShell 进程以遮罩方式读取 Key，不写入代码。
```

## 1. 文本生成

```python
import os  # 导入环境变量访问接口，避免将 API Key 硬编码到源码中。
import cohere  # 导入 Cohere SDK 主模块。

co = cohere.ClientV2(api_key=os.environ["COHERE_API_KEY"])  # 从当前进程读取 Key 并创建 v2 客户端。

response = co.chat(  # 发起一轮 v2 Chat 请求。
    model="command-a-plus-05-2026",  # 选择本课示例模型；运行前以官方模型页核对可用性。
    messages=[  # 按角色和时间顺序传入上下文。
        {"role": "system", "content": "你是一个简洁的中文技术老师。"},  # 约束回答风格。
        {"role": "user", "content": "用三点解释 API 调用。"},  # 当前用户问题。
    ],
)

print(response.message.content[0].text)  # 输出第一个文本内容块。
print(response.usage)  # 输出服务返回的实际用量。
```

模型更新较快，应从 [Models](https://docs.cohere.com/v2/docs/models) 核对当前可用 ID，不要继续使用 v1 时代的旧 `command` 别名。

## 2. 多轮对话

```python
messages = [  # 在应用侧保存完整历史；API 请求之间不会自动记忆。
    {"role": "system", "content": "你是 Python 老师。"},  # 固定系统指令。
    {"role": "user", "content": "字典是什么？"},  # 第一轮用户问题。
]

first = co.chat(model="command-a-plus-05-2026", messages=messages)  # 发送首轮历史并取得回答。
assistant_text = first.message.content[0].text  # 取出第一个文本内容块。

messages.append({"role": "assistant", "content": assistant_text})  # 将首轮回答写回历史。
messages.append({"role": "user", "content": "给一个读取键值的例子。"})  # 添加基于前文的追问。

second = co.chat(model="command-a-plus-05-2026", messages=messages)  # 用完整历史发起第二轮。
print(second.message.content[0].text)  # 输出第二轮文本回答。
```

v2 已把当前消息和历史统一放入 `messages`，不要照搬 v1 的 `message=` 与 `chat_history=` 写法。

## 3. 流式输出

```python
stream = co.chat_stream(  # 请求 v2 Chat 以事件流形式返回生成内容。
    model="command-a-plus-05-2026",  # 选择流式生成的目标模型。
    messages=[  # 提供本轮用户消息。
        {"role": "user", "content": "写一份 Python API 学习建议。"},  # 本轮生成任务。
    ],
)

for event in stream:  # 按到达顺序消费每个 Cohere 流事件。
    if event.type == "content-delta":  # 只处理增量文本事件，其他事件有不同结构。
        print(event.delta.message.content.text, end="", flush=True)  # 立即显示这段文本增量。
```

工具调用和流式响应还会出现其他事件类型；复杂应用应按 `event.type` 分支处理，而不是假设所有事件都有文本。

## 4. 结构化 JSON 输出

```python
import json  # 导入标准 JSON 解析器，用于在本地验证结构化响应。

response = co.chat(  # 请求模型生成符合 JSON Schema 的学习计划。
    model="command-a-plus-05-2026",  # 选择支持结构化输出的目标模型。
    messages=[{  # 将任务和 JSON 要求明确写进用户消息。
        "role": "user",  # 声明消息来自用户。
        "content": "生成一个 7 天 Python API 学习计划，并输出 JSON。",  # 指定内容目标和输出格式。
    }],
    response_format={  # 声明响应的 JSON 格式及字段约束。
        "type": "json_object",  # 要求响应主体是 JSON 对象。
        "json_schema": {  # 使用 Cohere v2 的 json_schema 字段给出 schema。
            "type": "object",  # 顶层必须是对象。
            "properties": {  # 定义允许的字段和类型。
                "topic": {"type": "string"},  # 学习主题字段。
                "days": {"type": "integer"},  # 计划天数字段。
                "tasks": {"type": "array", "items": {"type": "string"}},  # 任务字符串数组。
            },
            "required": ["topic", "days", "tasks"],  # 要求三个关键字段均存在。
        },
    },
)

data = json.loads(response.message.content[0].text)  # 将结构化文本解析为 Python 对象；异常应被调用边界处理。
print(data["tasks"])  # 读取任务列表；生产代码还应校验值域和业务约束。
```

启用 JSON 输出时，提示中也应明确提到 JSON。v2 Chat reference 中 schema 字段名为 `json_schema`，不是通用的 `schema`。同时，`response_format` 当前**不能**与 `documents` 或 `tools` 组合；需要检索/工具和稳定结构时，应拆成可审计的阶段（例如先检索/执行并核对结果，再由结构化生成步骤消费最小必要事实），而不是假设单次请求能同时承担全部职责。

## 5. 给 Chat 提供检索文档

```python
documents = [  # 模拟已由上游检索出的少量相关文档。
    "venv 用于隔离项目依赖。",  # 与问题直接相关的候选事实。
    "pip 用于安装 Python 包。",  # 另一条可供模型引用的候选事实。
]

response = co.chat(  # 让模型基于显式文档集合回答问题。
    model="command-a-plus-05-2026",  # 选择本例的聊天模型。
    messages=[{"role": "user", "content": "venv 有什么作用？"}],  # 提出需要依据文档回答的问题。
    documents=documents,  # 传入检索阶段已筛选出的文本，不替代检索和权限控制。
)

print(response.message.content[0].text)  # 输出模型回答的第一个文本块。
print(response.message.citations)  # 输出引用信息，便于展示或审计证据来源。
```

这适合把已经检索到的少量相关文档交给模型回答。大规模 RAG 通常先 Embed 检索，再 Rerank，最后 Chat。

## 6. Embedding

```python
response = co.embed(  # 调用 Embed API，将一批文档文本转换为向量。
    model="embed-v4.0",  # 选择入库与查询时应保持一致的 embedding 模型。
    texts=[  # 批量提供待向量化文本。
        "Python 适合快速开发。",  # 第一条候选文档。
        "Rust 重视性能和内存安全。",  # 第二条候选文档。
    ],
    input_type="search_document",  # 标记这些向量用于检索库中的文档，而不是用户查询。
    output_dimension=1024,  # 指定输出维度；向量库 schema 需与之匹配。
    embedding_types=["float"],  # 请求浮点向量输出。
)

vectors = response.embeddings.float  # 取出 SDK 返回的浮点向量列表。
print(len(vectors), len(vectors[0]))  # 检查向量数量和单条维度。
```

语义搜索时必须区分输入类型：

- 入库文档：`input_type="search_document"`
- 用户查询：`input_type="search_query"`
- 分类：`classification`
- 聚类：`clustering`

查询向量示例：

```python
query_response = co.embed(  # 为用户查询生成可与文档向量比较的向量。
    model="embed-v4.0",  # 与入库文档使用同一 embedding 模型。
    texts=["哪种语言适合快速开发？"],  # 提供单条用户查询。
    input_type="search_query",  # 标记这是查询侧输入，与 document 侧语义不同。
    output_dimension=1024,  # 与入库向量维度保持一致。
    embedding_types=["float"],  # 请求浮点向量输出。
)

query_vector = query_response.embeddings.float[0]  # 取出第一条查询的向量。
```

入库与查询要保持同一模型、输出维度和 embedding 类型。

## 7. Rerank

Rerank 接收一个查询和若干候选文档，返回按相关性重新排序的结果：

```python
documents = [  # 模拟上游向量检索获得的候选文档。
    "venv 用于隔离 Python 项目的依赖。",  # 与依赖隔离高度相关。
    "Git 用于版本控制。",  # 相关性较低的干扰候选。
    "pip 用于安装 Python 包。",  # 与 Python 依赖管理相关的候选。
]

response = co.rerank(  # 根据查询与候选文本的语义相关性进行重排。
    model="rerank-v4.0-pro",  # 选择偏质量的 Rerank 模型；实际选型要评估延迟和成本。
    query="如何避免两个 Python 项目的依赖冲突？",  # 提供用户检索意图。
    documents=documents,  # 传入待重排的候选集合。
    top_n=2,  # 只请求排名最靠前的两个结果。
)

for result in response.results:  # 遍历服务按相关性排序后的结果。
    print(result.index, result.relevance_score, documents[result.index])  # 输出原始索引、分数和对应文档文本。
```

`rerank-v4.0-pro` 偏质量，`rerank-v4.0-fast` 偏低延迟与高吞吐。Rerank 不生成答案，只负责排序。

## 8. Function Calling

```python
tools = [{  # 向模型声明一个可选择的函数工具。
    "type": "function",  # 指定工具类别为函数。
    "function": {  # 描述工具名称、用途和输入 schema。
        "name": "get_weather",  # 名称必须和宿主允许执行的工具一致。
        "description": "查询指定城市的天气。",  # 帮助模型选择工具。
        "parameters": {  # 使用 JSON Schema 限制参数。
            "type": "object",  # 参数必须是对象。
            "properties": {"city": {"type": "string"}},  # 只允许 city 字符串字段。
            "required": ["city"],  # 调用时必须提供 city。
        },
    },
}]

response = co.chat(  # 请求模型根据用户问题决定是否调用声明工具。
    model="command-a-plus-05-2026",  # 选择支持工具调用的模型。
    messages=[{"role": "user", "content": "上海现在多少度？"}],  # 提供当前用户问题。
    tools=tools,  # 将允许执行的工具 schema 发送给模型。
)

for tool_call in response.message.tool_calls or []:  # 遍历模型返回的工具调用；没有调用时安全跳过。
    print(tool_call.function.name, tool_call.function.arguments)  # 仅展示名称和原始参数；执行前仍须做校验与授权。
```

完整流程还需由 Python 执行函数，并使用对应的 `tool_call_id` 把工具结果作为 `tool` 消息发回。执行前必须验证参数。

## 常见易错点

- 使用 `Client` 或 v1 的 `message=` 写法，却按 v2 文档取响应。
- 流式事件不判断 `event.type`。
- 把 `response_format` 与 `documents` 或 `tools` 合用；当前 v2 Chat reference 不支持该组合。
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
