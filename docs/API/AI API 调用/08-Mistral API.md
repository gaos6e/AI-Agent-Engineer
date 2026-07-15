---
title: Mistral API 调用
source: https://docs.mistral.ai/resources/sdks
source_checked: 2026-07-12
execution_verified: false
verification_note: "仅核对官方资料并做语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - Mistral
  - Python
aliases:
  - Mistral AI API
---

# Mistral API 调用

> [!source] 官方来源
> 基于 [Mistral SDK Clients](https://docs.mistral.ai/resources/sdks)、Chat Completions、Vision、Function Calling、Embeddings 与 OCR 文档整理。官方 Python 包名为 `mistralai`。

## 常用入口

| Python 方法 | 用途 |
| --- | --- |
| `client.chat.complete()` | 文本、多轮、图片、JSON 和工具调用 |
| `client.chat.stream()` | 流式聊天 |
| `client.embeddings.create()` | 文本向量 |
| `client.files.upload()` | 上传文件 |
| `client.files.get_signed_url()` | 为已上传文件生成临时访问 URL |
| `client.ocr.process()` | OCR 与文档解析 |

## 安装与设置 API Key

```powershell
python -m pip install --upgrade mistralai
$env:MISTRAL_API_KEY = Read-Host 'MISTRAL_API_KEY' -MaskInput
```

## 1. 文本生成

```python
import os
from mistralai.client import Mistral

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

response = client.chat.complete(
    model="mistral-medium-latest",
    messages=[
        {"role": "system", "content": "你是一个简洁的中文技术老师。"},
        {"role": "user", "content": "用三点解释 API 调用。"},
    ],
)

print(response.choices[0].message.content)
print(response.usage)
```

`*-latest` 会指向系列的较新版本，便于学习但可能随时间变化。生产项目应查看 [Models](https://docs.mistral.ai/getting-started/models) 并评估是否固定快照。

## 2. 多轮对话

```python
messages = [
    {"role": "system", "content": "你是 Python 老师。"},
    {"role": "user", "content": "字典是什么？"},
]

first = client.chat.complete(
    model="mistral-medium-latest",
    messages=messages,
)

messages.append({
    "role": "assistant",
    "content": first.choices[0].message.content,
})
messages.append({"role": "user", "content": "给一个读取键值的例子。"})

second = client.chat.complete(
    model="mistral-medium-latest",
    messages=messages,
)

print(second.choices[0].message.content)
```

## 3. 流式输出

```python
stream = client.chat.stream(
    model="mistral-medium-latest",
    messages=[
        {"role": "user", "content": "写一份 Python API 学习建议。"},
    ],
)

for event in stream:
    text = event.data.choices[0].delta.content
    if text:
        print(text, end="", flush=True)
```

流式响应的外层通常是事件对象，实际增量在 `event.data` 中，这与 OpenAI SDK 的 chunk 结构不同。

## 4. 图片理解

```python
response = client.chat.complete(
    model="mistral-small-latest",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "解释图表趋势并提取坐标轴名称。"},
                {
                    "type": "image_url",
                    "image_url": "https://docs.mistral.ai/img/eiffel-tower-paris.jpg",
                },
            ],
        }
    ],
)

print(response.choices[0].message.content)
```

图片可使用公开 URL 或 Base64。普通视觉问答使用 Chat Completions；文档版面、表格和扫描件解析更适合 OCR。

## 5. JSON 输出

```python
import json

response = client.chat.complete(
    model="mistral-medium-latest",
    messages=[{
        "role": "user",
        "content": "请用 JSON 返回学习计划，字段为 topic、days、tasks。",
    }],
    response_format={"type": "json_object"},
)

data = json.loads(response.choices[0].message.content)
print(data["tasks"])
```

如果业务要求固定字段与类型，应进一步使用 JSON Schema 或 SDK 的结构化输出能力，并继续做本地校验。

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
first = client.chat.complete(
    model="mistral-medium-latest",
    messages=messages,
    tools=tools,
)

assistant_message = first.choices[0].message
messages.append(assistant_message)

for tool_call in assistant_message.tool_calls or []:
    arguments = json.loads(tool_call.function.arguments)
    result = get_weather(**arguments)
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "name": tool_call.function.name,
        "content": json.dumps(result, ensure_ascii=False),
    })

if assistant_message.tool_calls:
    final = client.chat.complete(
        model="mistral-medium-latest",
        messages=messages,
        tools=tools,
    )
    print(final.choices[0].message.content)
```

参数来自模型，执行前必须验证。模型一次可能要求调用多个工具。

## 7. Embedding

```python
response = client.embeddings.create(
    model="mistral-embed",
    inputs=[
        "Python 适合快速开发。",
        "Rust 重视性能和内存安全。",
    ],
)

vectors = [item.embedding for item in response.data]
print(len(vectors), len(vectors[0]))
```

注意这里的参数名是 `inputs`，不是一些兼容 SDK 中常见的 `input`。

## 8. OCR：解析本地 PDF

```python
from pathlib import Path

pdf_path = Path(r"D:\data\paper.pdf")

with pdf_path.open("rb") as pdf_file:
    uploaded = client.files.upload(
        file={
            "file_name": pdf_path.name,
            "content": pdf_file,
        },
        purpose="ocr",
    )

signed_url = client.files.get_signed_url(file_id=uploaded.id)

ocr_response = client.ocr.process(
    model="mistral-ocr-latest",
    document={
        "type": "document_url",
        "document_url": signed_url.url,
    },
)

for page in ocr_response.pages:
    print(page.markdown)
```

OCR 适合提取文档的文本、表格和版面。公开 PDF 也可直接传 `document_url`，无需先上传。

## 常见错误

- `401`：API Key 无效或环境变量未在新终端生效。
- `402`：账户或付款状态问题。
- `429`：触发限流。
- 把 `client.chat.stream()` 的事件当作普通 completion 读取。
- Embedding 使用了错误参数名 `input`。
- 用普通视觉问答代替文档 OCR，导致表格或版面提取不稳定。
- `latest` 指向发生变化却没有回归测试。

## 官方延伸阅读

- [SDK Clients](https://docs.mistral.ai/resources/sdks)
- [Chat Completions](https://docs.mistral.ai/capabilities/completion)
- [Vision](https://docs.mistral.ai/studio-api/conversations/vision)
- [Function Calling](https://docs.mistral.ai/capabilities/function_calling)
- [Embeddings](https://docs.mistral.ai/capabilities/embeddings)
- [Document AI / OCR](https://docs.mistral.ai/capabilities/document_ai)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
