---
title: Google Gemini API 调用
source: https://ai.google.dev/gemini-api/docs/quickstart
source_checked: 2026-07-12
execution_verified: false
verification_note: "仅核对官方资料并做语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - Gemini
  - Google
  - Python
aliases:
  - Gemini API
  - Google GenAI API
---

# Google Gemini API 调用

> [!source] 官方来源
> 基于 [Gemini API quickstart](https://ai.google.dev/gemini-api/docs/quickstart) 和 `google-genai` 官方文档整理。旧包 `google-generativeai` 不再作为本笔记主线。

## 常用入口

| Python 方法 | 用途 |
| --- | --- |
| `client.models.generate_content()` | 文本与多模态生成 |
| `client.models.generate_content_stream()` | 流式生成 |
| `client.chats.create()` / `chat.send_message()` | SDK 管理多轮聊天历史 |
| `client.files.upload()` | 上传图片、音频、视频和文档 |
| `client.models.embed_content()` | 生成文本向量 |
| `client.models.get()` / `client.models.list()` | 查看模型信息 |

学习示例使用稳定模型 `gemini-3.5-flash`。`latest` 别名可能自动切换版本，生产环境更适合固定稳定模型。

## 安装与设置 API Key

```powershell
python -m pip install --upgrade google-genai
$env:GEMINI_API_KEY = Read-Host 'GEMINI_API_KEY' -MaskInput
```

## 1. 最小文本调用

```python
from google import genai

client = genai.Client()

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="用三点解释 API 调用。",
)

print(response.text)
print(response.usage_metadata)
```

`response.text` 是便捷属性；需要查看候选结果、停止原因或安全信息时，再检查 `response.candidates`。

## 2. 配置系统指令与生成参数

```python
from google.genai import types

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="解释 Python 虚拟环境。",
    config=types.GenerateContentConfig(
        system_instruction="你是一个简洁、准确的中文技术老师。",
        temperature=0.3,
        max_output_tokens=800,
    ),
)

print(response.text)
```

常用配置包括 `system_instruction`、`temperature`、`max_output_tokens`、安全设置、工具和结构化输出。不同模型支持的参数不完全相同。

## 3. 多轮聊天

```python
chat = client.chats.create(model="gemini-3.5-flash")

first = chat.send_message("Python 的字典是什么？")
print(first.text)

second = chat.send_message("给我一个按键读取值的例子。")
print(second.text)
```

`chat` 对象在客户端内维护历史，适合学习和简单会话。需要持久化会话时，应由自己的应用保存并恢复历史。

## 4. 流式输出

```python
for chunk in client.models.generate_content_stream(
    model="gemini-3.5-flash",
    contents="写一份 7 天 Python API 学习计划。",
):
    if chunk.text:
        print(chunk.text, end="", flush=True)
```

聊天对象也支持流式发送：

```python
chat = client.chats.create(model="gemini-3.5-flash")

for chunk in chat.send_message_stream("用 200 字解释 REST API。"):
    if chunk.text:
        print(chunk.text, end="", flush=True)
```

## 5. 图片理解

```python
from PIL import Image

image = Image.open(r"D:\data\chart.png")

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=["解释图表趋势，并提取坐标轴名称。", image],
)

print(response.text)
```

安装 Pillow：

```powershell
python -m pip install --upgrade pillow
```

图片、短音频等较小内容可直接传入；较大文件或需要重复使用的文件建议先上传。

## 6. 上传并分析文件

```python
uploaded = client.files.upload(file=r"D:\data\paper.pdf")

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=[uploaded, "总结这份文档，并列出三个关键结论。"],
)

print(response.text)
```

视频和较长音频上传后可能需要等待处理完成；应检查文件状态后再发起生成请求。文件大小、保留时间和支持格式以 [File input methods](https://ai.google.dev/gemini-api/docs/file-input-methods) 为准。

## 7. 结构化 JSON 输出

```powershell
python -m pip install --upgrade pydantic
```

```python
from pydantic import BaseModel
from google.genai import types


class StudyPlan(BaseModel):
    topic: str
    days: int
    tasks: list[str]


response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="为 Python API 入门制定一个 7 天学习计划。",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=StudyPlan,
    ),
)

plan = StudyPlan.model_validate_json(response.text)
print(plan.tasks)
```

结构化输出适合数据抽取、写数据库和后续程序处理。不要仅靠提示词要求“输出 JSON”，应同时提供 schema。

## 8. 函数调用

Python SDK 可以根据函数签名生成工具声明，并自动调用普通 Python 函数：

```python
from google.genai import types


def get_weather(city: str) -> dict:
    """查询指定城市的当前天气。"""
    return {"city": city, "temperature": 25, "unit": "celsius"}


response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="上海现在多少度？",
    config=types.GenerateContentConfig(tools=[get_weather]),
)

print(response.text)
```

> [!warning]
> 自动函数调用适合无副作用的学习示例。涉及删除、支付、发消息等操作时，应关闭自动执行或在函数内部增加严格校验与人工确认。

也可以手动声明 `FunctionDeclaration`、读取模型返回的函数调用，再自行执行和回传；复杂 Agent 更推荐手动流程。

## 9. Google Search 工具

```python
from google.genai import types

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="查找今天 Python 官方生态的重要更新，并给出来源。",
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
    ),
)

print(response.text)
```

是否支持搜索、如何计费以及返回何种 grounding metadata 取决于模型和账户，应以 [Grounding with Google Search](https://ai.google.dev/gemini-api/docs/google-search) 为准。

## 10. Embedding

```python
response = client.models.embed_content(
    model="gemini-embedding-001",
    contents=[
        "Python 适合快速开发。",
        "Rust 重视性能和内存安全。",
    ],
)

vectors = [item.values for item in response.embeddings]
print(len(vectors), len(vectors[0]))
```

向量适合语义检索、聚类、分类和 RAG。入库与查询应使用同一模型和一致的任务类型、维度配置。

## 11. 异步调用

```python
import asyncio
from google import genai


async def main() -> None:
    client = genai.Client()
    response = await client.aio.models.generate_content(
        model="gemini-3.5-flash",
        contents="解释 async/await。",
    )
    print(response.text)


asyncio.run(main())
```

## 常见易错点

- 安装了旧包 `google-generativeai`，却照 `google-genai` 的新文档写代码。
- 把模型名写成网页产品名；API 模型 ID 需从官方 Models 页复制。
- 使用 `latest` 别名后模型行为发生变化；生产项目应固定稳定版本。
- 上传大文件后立即调用，没有等待文件处理完成。
- 只读取 `response.text`，忽略停止原因、安全反馈或函数调用。
- 把自动函数调用用于高风险副作用操作。

## 官方延伸阅读

- [Gemini API quickstart](https://ai.google.dev/gemini-api/docs/quickstart)
- [Text generation](https://ai.google.dev/gemini-api/docs/text-generation)
- [File input methods](https://ai.google.dev/gemini-api/docs/file-input-methods)
- [Function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
- [Models](https://ai.google.dev/gemini-api/docs/models)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
