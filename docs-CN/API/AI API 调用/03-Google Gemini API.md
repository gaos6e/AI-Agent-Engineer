---
title: "Google Gemini API 调用（Interactions 与 GenerateContent）"
source: https://ai.google.dev/gemini-api/docs/get-started
source_checked: 2026-07-22
source_baseline:
  - Gemini API Getting started、Interactions overview、Interactions
    migration、Gemini 3.5 GenerateContent migration
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "已核对 Interactions/GenerateContent 的当前主线边界并做离线语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - Gemini
  - Google
  - Python
aliases:
  - Gemini API
  - Google GenAI API
lang: zh-CN
translation_key: API/AI API 调用/03-Google Gemini API.md
translation_route: en/api/ai-api-reference/google-gemini-api
translation_default_route: zh-CN/API/AI-API-调用/03-Google-Gemini-API
---

# Google Gemini API 调用（Interactions 与 GenerateContent）

> [!source] 官方来源
> 本页按 [Gemini API Getting started](https://ai.google.dev/gemini-api/docs/get-started)、[Interactions API 概览](https://ai.google.dev/gemini-api/docs/interactions-overview) 和 [Gemini 3.5 的迁移说明](https://ai.google.dev/gemini-api/docs/generate-content/whats-new-gemini-3.5) 整理，核验日期为 **2026-07-22**。旧包 `google-generativeai` 不再作为本笔记主线。

> [!important] 先选对 API family
> **Interactions API 自 2026 年 6 月起 GA，官方推荐新项目优先使用它，并把新模型与新能力放在这条主线上。** 原 `generateContent` API 现被标为 legacy，但仍 fully supported；本页后半段保留它是为了维护已有代码、理解 `contents/candidates/parts` 和执行迁移，而不是把它当作新项目默认入口。两套 API 的历史、流式事件、工具结果和结构化输出不能混用。

## 环境准备

```powershell
python -m pip install --upgrade google-genai  # 安装或更新当前虚拟环境中的 Google Gen AI Python SDK。
$env:GEMINI_API_KEY = Read-Host 'GEMINI_API_KEY' -MaskInput  # 仅在当前 PowerShell 进程以遮罩方式读取 Key，不写入源码或历史记录。
```

`genai.Client()` 会从当前进程的 `GEMINI_API_KEY` 读取凭据；不要把真实 key 写入笔记、代码、命令历史或截图。

## 推荐主线：Interactions API

### 最小文本调用

```python
from google import genai  # 导入当前 Google Gen AI Python SDK 的主模块。

client = genai.Client()  # 从进程环境中的 GEMINI_API_KEY 创建客户端；不要硬编码凭据。
interaction = client.interactions.create(  # 创建一轮 Interactions API 请求。
    model="gemini-3.5-flash",  # 选择本课示例模型；上线前以官方模型页核对可用性。
    input="用三点解释 API 调用。",  # 传入本轮的用户输入。
)

print(interaction.output_text)  # 输出 SDK 提供的文本便利属性。
print(interaction.usage)  # 输出本轮实际用量，供成本和上下文诊断使用。
```

### 流式与有状态续接

```python
from google import genai  # 导入 SDK；独立示例可单独运行。

client = genai.Client()  # 创建从环境变量读取凭据的客户端。
stream = client.interactions.create(  # 请求以流式事件形式返回生成过程。
    model="gemini-3.5-flash",  # 选择支持本例的模型。
    input="用 200 字解释 REST API。",  # 指定本轮生成任务。
    stream=True,  # 开启流式模式，而非等待一个完整 Interaction 对象。
)
for event in stream:  # 按服务到达顺序消费每个流事件。
    print(event)  # 教学期先打印原始事件；生产代码应按事件类型解析和记录。

first = client.interactions.create(  # 创建一轮将作为后续引用上下文的已存储 Interaction。
    model="gemini-3.5-flash",  # 使用与续接轮一致的模型。
    input="我家有两只狗。",  # 给出需要被下一轮引用的上下文事实。
)
second = client.interactions.create(  # 创建第二轮 Interaction。
    model="gemini-3.5-flash",  # 使用本课示例模型。
    input="我家有多少只爪子？",  # 基于前一轮上下文提出追问。
    previous_interaction_id=first.id,  # 引用前一轮的 ID 以续接已存储历史。
)
print(second.output_text)  # 输出续接轮的文本结果。
```

`previous_interaction_id` 只带上已存储的历史，不会继承本轮的 `tools`、`system_instruction` 或 `generation_config`；需要时应在每个请求显式重发。Interactions 默认 `store=true`，免费层默认保留 1 天，付费层默认 55 天（可配置更短的 7/14/28 天）；`store=false` 不能再使用前序 ID，也不能用于 background execution。若选择无状态模式，必须原样保存并重放模型生成的全部 steps（包括 thought、function call/result），不要只保留可见文本。`create` 响应主要返回本轮模型生成的 steps，完整历史应以可检索 Interaction 快照核对。

### 与 GenerateContent 的能力边界

Interactions 是新能力的首选入口，但并不意味着两套 API 的字段可互换。迁移前应逐项核对工具、结构化输出、思考配置、文件/媒体和状态语义；例如 Gemini 3.x 不建议在请求中改变 `temperature`、`top_p` 或 `top_k`，应使用 `thinking_level`（`minimal`、`low`、`medium`、`high`）表达推理预算。旧代码若依赖 GenerateContent 独有或尚未迁移的能力，应明确留在兼容层并锁定模型与 API 版本。

## 兼容层：GenerateContent API（legacy but fully supported）

以下示例用于维护既有 `client.models.*` / `client.chats.*` 集成；新项目先阅读上面的 Interactions 主线。

### 常用入口

| Python 方法 | 用途 |
| --- | --- |
| `client.models.generate_content()` | 文本与多模态生成 |
| `client.models.generate_content_stream()` | 流式生成 |
| `client.chats.create()` / `chat.send_message()` | SDK 管理多轮聊天历史 |
| `client.files.upload()` | 上传图片、音频、视频和文档 |
| `client.models.embed_content()` | 生成文本向量 |
| `client.models.get()` / `client.models.list()` | 查看模型信息 |

学习示例使用稳定模型 `gemini-3.5-flash`。`latest` 别名可能自动切换版本，生产环境更适合固定稳定模型。

### 1. 最小文本调用

```python
from google import genai  # 导入 GenerateContent 兼容层所用的 SDK 模块。

client = genai.Client()  # 创建客户端；凭据由当前进程环境提供。

response = client.models.generate_content(  # 调用 legacy GenerateContent 兼容入口。
    model="gemini-3.5-flash",  # 选择示例模型；生产代码应固定并核验模型版本。
    contents="用三点解释 API 调用。",  # 传入单段文本内容。
)

print(response.text)  # 输出 SDK 的文本便利属性。
print(response.usage_metadata)  # 输出用量元数据，供成本和限额排查使用。
```

`response.text` 是便捷属性；需要查看候选结果、停止原因或安全信息时，再检查 `response.candidates`。

### 2. 配置系统指令与生成参数

```python
from google.genai import types  # 导入 SDK 的强类型配置对象。

response = client.models.generate_content(  # 调用兼容层文本生成入口。
    model="gemini-3.5-flash",  # 选择本例使用的稳定模型 ID。
    contents="解释 Python 虚拟环境。",  # 提供需要解释的主题。
    config=types.GenerateContentConfig(  # 将系统指令和生成预算放入显式配置对象。
        system_instruction="你是一个简洁、准确的中文技术老师。",  # 约束回答的身份与表达风格。
        thinking_config=types.ThinkingConfig(thinking_level="medium"),  # 为支持的模型选择中等推理预算。
        max_output_tokens=800,  # 限制本轮最多返回的 token 数。
    ),
)

print(response.text)  # 输出生成的文本结果。
```

常用配置包括 `system_instruction`、`thinking_config`、`max_output_tokens`、安全设置、工具和结构化输出。对 Gemini 3.x 不要设置 `temperature`、`top_p` 或 `top_k`；其他模型的可用参数仍须以对应模型文档为准。不同模型支持的参数不完全相同。

### 3. 多轮聊天

```python
chat = client.chats.create(model="gemini-3.5-flash")  # 创建由 SDK 在本地维护消息历史的聊天对象。

first = chat.send_message("Python 的字典是什么？")  # 发送第一轮问题并更新聊天历史。
print(first.text)  # 输出第一轮文本回答。

second = chat.send_message("给我一个按键读取值的例子。")  # 在同一 chat 中续接追问，SDK 会携带前文。
print(second.text)  # 输出第二轮文本回答。
```

`chat` 对象在客户端内维护历史，适合学习和简单会话。需要持久化会话时，应由自己的应用保存并恢复历史。

### 4. 流式输出

```python
for chunk in client.models.generate_content_stream(  # 调用兼容层的流式生成入口。
    model="gemini-3.5-flash",  # 选择流式请求的目标模型。
    contents="写一份 7 天 Python API 学习计划。",  # 提供本轮生成任务。
):  # 按到达顺序迭代服务返回的内容分片。
    if chunk.text:  # 有些事件没有文本，先判断再读取便利属性。
        print(chunk.text, end="", flush=True)  # 立即输出增量文本，模拟逐字展示。
```

聊天对象也支持流式发送：

```python
chat = client.chats.create(model="gemini-3.5-flash")  # 创建可在本地保存历史的聊天对象。

for chunk in chat.send_message_stream("用 200 字解释 REST API。"):  # 发送消息并以流式方式接收回答。
    if chunk.text:  # 跳过不包含文本的流事件。
        print(chunk.text, end="", flush=True)  # 立刻显示本次到达的文本片段。
```

### 5. 图片理解

```python
from PIL import Image  # 导入 Pillow 的图像读取接口。

image = Image.open(r"D:\data\chart.png")  # 打开拥有上传授权的本地图片；生产代码还应处理文件不存在和格式错误。

response = client.models.generate_content(  # 发送同时含文本和图片的多模态请求。
    model="gemini-3.5-flash",  # 选择支持视觉输入的模型；运行前核对能力限制。
    contents=["解释图表趋势，并提取坐标轴名称。", image],  # 将文字任务和 Pillow 图像对象一同传入。
)

print(response.text)  # 输出图片分析的文本结果。
```

安装 Pillow：

```powershell
python -m pip install --upgrade pillow  # 安装或更新读取本地图片所需的 Pillow 依赖。
```

图片、短音频等较小内容可直接传入；较大文件或需要重复使用的文件建议先上传。

### 6. 上传并分析文件

```python
uploaded = client.files.upload(file=r"D:\data\paper.pdf")  # 上传拥有处理授权的文件，并保存服务返回的文件引用。

response = client.models.generate_content(  # 基于已上传文件发起文档分析请求。
    model="gemini-3.5-flash",  # 选择支持该文件输入路径的模型。
    contents=[uploaded, "总结这份文档，并列出三个关键结论。"],  # 同时传入文件引用与分析指令。
)

print(response.text)  # 输出文档总结文本。
```

视频和较长音频上传后可能需要等待处理完成；应检查文件状态后再发起生成请求。文件大小、保留时间和支持格式以 [File input methods](https://ai.google.dev/gemini-api/docs/file-input-methods) 为准。

### 7. 结构化 JSON 输出

```powershell
python -m pip install --upgrade pydantic  # 安装或更新用 Python 类型描述响应 schema 的 Pydantic。
```

```python
from pydantic import BaseModel  # 导入 Pydantic 基类，用 Python 类型定义预期 JSON 结构。
from google.genai import types  # 导入 GenerateContent 的类型化配置对象。


class StudyPlan(BaseModel):  # 定义模型需要遵守、客户端也会校验的学习计划 schema。
    topic: str  # 学习计划的主题名称。
    days: int  # 计划覆盖的天数。
    tasks: list[str]  # 每天或每阶段的任务文本列表。


response = client.models.generate_content(  # 请求模型生成符合 schema 的结构化输出。
    model="gemini-3.5-flash",  # 选择支持结构化输出的目标模型。
    contents="为 Python API 入门制定一个 7 天学习计划。",  # 提供需要结构化回答的任务。
    config=types.GenerateContentConfig(  # 显式声明响应格式与 schema。
        response_mime_type="application/json",  # 要求服务以 JSON 媒体类型返回结果。
        response_schema=StudyPlan,  # 把 Pydantic 模型作为响应字段约束。
    ),
)

plan = StudyPlan.model_validate_json(response.text)  # 在本地再次验证和解析返回 JSON，失败时会抛出校验异常。
print(plan.tasks)  # 输出已验证的任务列表。
```

结构化输出适合数据抽取、写数据库和后续程序处理。不要仅靠提示词要求“输出 JSON”，应同时提供 schema。

### 8. 函数调用

Python SDK 可以根据函数签名生成工具声明，并自动调用普通 Python 函数：

```python
from google.genai import types  # 导入工具配置所需的 SDK 类型。


def get_weather(city: str) -> dict:  # 定义 SDK 可根据函数签名声明和调用的本地教学工具。
    """查询指定城市的当前天气。"""  # 说明工具用途，帮助模型理解何时调用。
    return {"city": city, "temperature": 25, "unit": "celsius"}  # 返回固定离线值，避免例子访问真实服务。


response = client.models.generate_content(  # 发起允许自动函数调用的生成请求。
    model="gemini-3.5-flash",  # 选择支持函数调用的模型。
    contents="上海现在多少度？",  # 提供可能触发该工具的用户问题。
    config=types.GenerateContentConfig(tools=[get_weather]),  # 把无副作用的本地函数作为可调用工具暴露给模型。
)

print(response.text)  # 输出 SDK 自动工具调用并续接后得到的文本回答。
```

> [!warning]
> 自动函数调用适合无副作用的学习示例。涉及删除、支付、发消息等操作时，应关闭自动执行或在函数内部增加严格校验与人工确认。

也可以手动声明 `FunctionDeclaration`、读取模型返回的函数调用，再自行执行和回传；复杂 Agent 更推荐手动流程。

### 9. Google Search 工具

```python
from google.genai import types  # 导入声明内置 Google Search 工具的类型。

response = client.models.generate_content(  # 发起允许模型使用受控搜索工具的生成请求。
    model="gemini-3.5-flash",  # 选择当前支持该工具的模型；能力和计费需以官方文档为准。
    contents="查找今天 Python 官方生态的重要更新，并给出来源。",  # 给出需要检索时效信息的任务。
    config=types.GenerateContentConfig(  # 在显式配置中开放内置工具。
        tools=[types.Tool(google_search=types.GoogleSearch())],  # 仅启用 Google Search，而不是让模型任意访问网络。
    ),
)

print(response.text)  # 输出模型整合搜索结果后的文本；生产代码还应读取 grounding 元数据。
```

是否支持搜索、如何计费以及返回何种 grounding metadata 取决于模型和账户，应以 [Grounding with Google Search](https://ai.google.dev/gemini-api/docs/google-search) 为准。

### 10. Embedding

```python
response = client.models.embed_content(  # 调用 Embedding 入口，把一批文本转换为数值向量。
    model="gemini-embedding-001",  # 选择入库和查询时必须保持一致的 embedding 模型。
    contents=[  # 批量提供待向量化的文本内容。
        "Python 适合快速开发。",  # 第一条输入文本。
        "Rust 重视性能和内存安全。",  # 第二条输入文本。
    ],
)

vectors = [item.values for item in response.embeddings]  # 按响应顺序提取每条文本对应的向量数值。
print(len(vectors), len(vectors[0]))  # 检查向量数量和单条维度，避免静默混用不同配置。
```

向量适合语义检索、聚类、分类和 RAG。入库与查询应使用同一模型和一致的任务类型、维度配置。

### 11. 异步调用

```python
import asyncio  # 导入 Python 标准异步事件循环工具。
from google import genai  # 导入 SDK，以便通过 client.aio 使用异步接口。


async def main() -> None:  # 定义异步脚本入口。
    client = genai.Client()  # 创建客户端，凭据从当前进程环境读取。
    response = await client.aio.models.generate_content(  # 等待异步 GenerateContent 请求完成。
        model="gemini-3.5-flash",  # 选择本例使用的模型。
        contents="解释 async/await。",  # 提供本轮用户问题。
    )
    print(response.text)  # 输出生成的文本回答。


asyncio.run(main())  # 在普通 Python 脚本中运行事件循环直到 main 完成。
```

### 常见易错点

- 安装了旧包 `google-generativeai`，却照 `google-genai` 的新文档写代码。
- 把模型名写成网页产品名；API 模型 ID 需从官方 Models 页复制。
- 使用 `latest` 别名后模型行为发生变化；生产项目应固定稳定版本。
- 上传大文件后立即调用，没有等待文件处理完成。
- 只读取 `response.text`，忽略停止原因、安全反馈或函数调用。
- 把自动函数调用用于高风险副作用操作。

## 官方延伸阅读

- [Gemini API Getting started（Interactions 主线）](https://ai.google.dev/gemini-api/docs/get-started)
- [Interactions API 概览](https://ai.google.dev/gemini-api/docs/interactions-overview)
- [从 GenerateContent 迁移到 Interactions](https://ai.google.dev/gemini-api/docs/migrate-to-interactions)
- [Gemini 3.5 Flash：GenerateContent 兼容层与参数迁移](https://ai.google.dev/gemini-api/docs/generate-content/whats-new-gemini-3.5)
- [Gemini API quickstart（旧版 GenerateContent 切换页）](https://ai.google.dev/gemini-api/docs/quickstart)
- [Text generation](https://ai.google.dev/gemini-api/docs/text-generation)
- [File input methods](https://ai.google.dev/gemini-api/docs/file-input-methods)
- [Function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
- [Models](https://ai.google.dev/gemini-api/docs/models)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
