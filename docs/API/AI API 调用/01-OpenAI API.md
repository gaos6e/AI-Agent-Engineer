---
title: OpenAI API 调用
source: https://developers.openai.com/api/docs/quickstart
source_checked: 2026-07-12
execution_verified: false
verification_note: "仅核对官方资料并做语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - OpenAI
  - Python
aliases:
  - OpenAI API
---

# OpenAI API 调用

> [!source] 官方来源
> 本笔记按 Windows + Python 整理，主线采用 [Developer quickstart](https://developers.openai.com/api/docs/quickstart) 推荐的 `Responses API`。示例模型使用当前通用别名 `gpt-5.6`；正式项目应再查看 [Models](https://developers.openai.com/api/docs/models)，并按稳定性、成本和能力选择模型。

## 先认识常用入口

| Python 方法 | 用途 | 学习优先级 |
| --- | --- | --- |
| `client.responses.create()` | 文本、多模态、工具调用的统一入口 | 必学 |
| `client.responses.parse()` | 按 Pydantic 模型返回结构化数据 | 常用 |
| `client.files.create()` | 上传 PDF、文档、图片等文件 | 常用 |
| `client.embeddings.create()` | 生成向量，用于语义检索和 RAG | 常用 |
| `client.audio.transcriptions.create()` | 音频转文字 | 按需 |
| `client.images.generate()` | 直接使用 Images API 生成图片 | 按需 |
| `client.models.list()` | 查看当前项目可访问的模型 | 辅助 |

> [!tip] 学习顺序
> 先掌握文本生成、多轮对话和流式输出，再学习图片/文件、结构化输出与工具调用。Embedding、音频和图像生成可按项目需要补充。

## 安装与设置 API Key

```powershell
python -m pip install --upgrade openai
$env:OPENAI_API_KEY = Read-Host 'OPENAI_API_KEY' -MaskInput
```

## 1. 文本生成：`responses.create()`

```python
from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="gpt-5.6",
    reasoning={"effort": "low"},
    instructions="你是一个简洁、准确的中文技术老师。",
    input="用三点解释什么是 API 调用。",
)

print(response.output_text)
print(response.usage)
```

常用参数：

| 参数 | 作用 |
| --- | --- |
| `model` | 选择模型 |
| `input` | 用户输入，可为字符串或结构化消息列表 |
| `instructions` | 当前请求的高优先级开发者指令 |
| `reasoning` | 推理强度等配置；可用值取决于模型 |
| `max_output_tokens` | 限制本次最多生成的 token |
| `tools` | 启用内置工具、MCP 或自定义函数 |

> [!warning] 不要固定读取 `response.output[0]`
> `output` 中还可能出现推理项和工具调用项。只需要最终文本时优先用 SDK 提供的 `response.output_text`。

## 2. 结构化消息与多轮对话

### 使用消息角色

```python
response = client.responses.create(
    model="gpt-5.6",
    input=[
        {
            "role": "developer",
            "content": "回答时给出定义、例子和一个常见错误。",
        },
        {
            "role": "user",
            "content": "解释 Python 虚拟环境。",
        },
    ],
)

print(response.output_text)
```

- `developer`：应用规则和输出要求，优先级高于用户消息。
- `user`：最终用户输入。
- `assistant`：模型之前的回答；手动维护历史时会用到。

### 使用 `previous_response_id` 继续对话

```python
first = client.responses.create(
    model="gpt-5.6",
    input="我的项目使用 Python 和 FastAPI。",
)

second = client.responses.create(
    model="gpt-5.6",
    previous_response_id=first.id,
    input="请基于刚才的信息给我一个目录结构。",
)

print(second.output_text)
```

> [!note]
> `instructions` 只作用于当前请求。继续对话时如果仍需要同一规则，应再次传入。

## 3. 流式输出

流式输出适合聊天界面或长回答。它会在生成过程中持续返回事件：

```python
stream = client.responses.create(
    model="gpt-5.6",
    input="写一段 200 字的 Python 学习建议。",
    stream=True,
)

for event in stream:
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
    elif event.type == "response.completed":
        print("\n\n生成完成")
```

实际应用中还应处理 `response.failed`、`response.incomplete` 等事件。

## 4. 分析图片

图片可以来自公开 URL、Base64 data URL 或已上传文件的 `file_id`：

```python
response = client.responses.create(
    model="gpt-5.6",
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "描述图片，并提取可见文字。"},
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

读取本地图片时可先转为 Base64：

```python
import base64
from pathlib import Path

image_path = Path(r"D:\data\chart.png")
image_base64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")

response = client.responses.create(
    model="gpt-5.6",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "解释这张图表的趋势。"},
            {
                "type": "input_image",
                "image_url": f"data:image/png;base64,{image_base64}",
            },
        ],
    }],
)

print(response.output_text)
```

## 5. 上传并分析文件

适合 PDF、DOCX、PPTX、TXT、代码文件和表格等。PDF 在支持视觉的模型上会同时提取文本和页面图像。

```python
from pathlib import Path

file_path = Path(r"D:\data\paper.pdf")

with file_path.open("rb") as file_handle:
    uploaded = client.files.create(
        file=file_handle,
        purpose="user_data",
    )

response = client.responses.create(
    model="gpt-5.6",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_file", "file_id": uploaded.id},
            {"type": "input_text", "text": "总结文档，并列出三个关键结论。"},
        ],
    }],
)

print(response.output_text)
```

单次分析少量文件可用 `input_file`；大量文件、重复检索或知识库场景应进一步学习 [File search](https://developers.openai.com/api/docs/guides/tools-file-search)。

## 6. 内置工具：Web Search

```python
response = client.responses.create(
    model="gpt-5.6",
    tools=[{"type": "web_search"}],
    input="查找今天与 Python 相关的重要官方更新，并附来源。",
)

print(response.output_text)
```

工具结果不一定只有文本，因此调试时可以检查各输出项：

```python
for item in response.output:
    print(item.type)
```

其他常见内置工具包括 `file_search`、`code_interpreter`、`image_generation` 和远程 MCP；不同模型与账户的可用范围可能不同。

## 7. 自定义函数调用

模型只负责决定“调用哪个函数、参数是什么”，真正执行函数的是你的 Python 程序。

```python
import json


def get_weather(city: str) -> dict:
    # 学习示例；真实项目应在这里调用天气 API。
    return {"city": city, "temperature": 25, "unit": "celsius"}


tools = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "查询指定城市的当前天气。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名"},
            },
            "required": ["city"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]

response = client.responses.create(
    model="gpt-5.6",
    tools=tools,
    input="上海现在多少度？",
)

tool_outputs = []
for item in response.output:
    if item.type == "function_call" and item.name == "get_weather":
        arguments = json.loads(item.arguments)
        result = get_weather(**arguments)
        tool_outputs.append(
            {
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": json.dumps(result, ensure_ascii=False),
            }
        )

if tool_outputs:
    final_response = client.responses.create(
        model="gpt-5.6",
        tools=tools,
        previous_response_id=response.id,
        input=tool_outputs,
    )
    print(final_response.output_text)
else:
    print(response.output_text)
```

> [!warning]
> 函数参数来自模型，必须先解析、校验并限制权限。涉及删除、支付、发消息等副作用时，不要未经确认直接执行。

## 8. 结构化输出：`responses.parse()`

当程序需要稳定字段，而不是一段自然语言时，使用 Pydantic 模型：

```powershell
python -m pip install --upgrade pydantic
```

```python
from pydantic import BaseModel


class StudyPlan(BaseModel):
    topic: str
    days: int
    tasks: list[str]


response = client.responses.parse(
    model="gpt-5.6",
    input="为 Python API 入门制定一个 7 天计划。",
    text_format=StudyPlan,
)

plan = response.output_parsed
print(plan.topic)
print(plan.tasks)
```

结构化输出适合写数据库、调用后续函数、生成配置或做数据抽取。仍应处理拒答、输出不完整和校验失败。

## 9. Embedding：`embeddings.create()`

```python
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=[
        "Python 适合快速开发。",
        "Rust 重视性能和内存安全。",
    ],
)

vectors = [item.embedding for item in response.data]
print(len(vectors), len(vectors[0]))
```

Embedding 本身不会回答问题，它把文本变成向量，常用于语义搜索、聚类、推荐与 RAG。入库和查询必须使用同一模型与同一维度。

## 10. 音频转文字

```python
from pathlib import Path

audio_path = Path(r"D:\data\meeting.mp3")

with audio_path.open("rb") as audio_file:
    transcription = client.audio.transcriptions.create(
        model="gpt-4o-transcribe",
        file=audio_file,
    )

print(transcription.text)
```

实时麦克风转写或语音对话不走这个文件上传示例，应学习 Realtime API。

## 11. 生成图片

Responses API 可以把图像生成作为工具：

```python
import base64

response = client.responses.create(
    model="gpt-5.6",
    input="生成一张极简风格的 Python API 学习路线图。",
    tools=[{"type": "image_generation"}],
)

for item in response.output:
    if item.type == "image_generation_call":
        with open("api-roadmap.png", "wb") as image_file:
            image_file.write(base64.b64decode(item.result))
```

如果应用只需要图片生成与编辑，也可进一步学习 `client.images.generate()` 和 `client.images.edit()`。

## 错误处理与重试

```python
import openai

try:
    response = client.responses.create(
        model="gpt-5.6",
        input="你好",
        timeout=60,
    )
except openai.AuthenticationError:
    print("API Key 无效或没有权限。")
except openai.RateLimitError:
    print("触发限流或额度不足，请稍后重试并检查账户。")
except openai.APITimeoutError:
    print("请求超时。")
except openai.APIConnectionError:
    print("网络连接失败。")
except openai.APIStatusError as exc:
    print("API 错误：", exc.status_code, exc.request_id)
```

生产代码可在客户端级设置超时与有限重试：

```python
client = OpenAI(timeout=60.0, max_retries=2)
```

## 常见错误

- `401`：API Key 错误、变量未在新终端生效或项目权限不足。
- `429`：触发速率限制，也可能是额度或账单问题。
- 模型不存在：当前项目无权访问，或模型名已变更；用模型页或 `client.models.list()` 核对。
- 把 ChatGPT 订阅当作 API 额度：ChatGPT 与 API 的计费和权限是分开的。
- 把 Key 写进 `.py`、Notebook 或 Git：应使用环境变量，发现泄露后立即撤销并重建。
- 流式输出只拼文本：工具调用和失败事件也需要单独处理。

## 官方延伸阅读

- [Developer quickstart](https://developers.openai.com/api/docs/quickstart)
- [Text generation](https://developers.openai.com/api/docs/guides/text)
- [Images and vision](https://developers.openai.com/api/docs/guides/images-vision)
- [File inputs](https://developers.openai.com/api/docs/guides/file-inputs)
- [Using tools](https://developers.openai.com/api/docs/guides/tools)
- [Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [Streaming API responses](https://developers.openai.com/api/docs/guides/streaming-responses)
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
