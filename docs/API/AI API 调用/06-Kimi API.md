---
title: Kimi API 调用
source: https://platform.kimi.com/docs/guide/start-using-kimi-api
source_checked: 2026-07-12
execution_verified: false
verification_note: "仅核对官方资料并做语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - Kimi
  - Moonshot
  - Python
aliases:
  - Moonshot API
  - Kimi API
---

# Kimi API 调用

> [!source] 官方来源
> 基于 Kimi 开放平台快速开始、Chat Completion、Tool Use 和 Files API 文档整理。Kimi 使用 OpenAI 兼容格式，Python 中通常使用 `openai` 包。

## 常用入口

| Python 方法 | 用途 |
| --- | --- |
| `client.chat.completions.create()` | 文本、多轮、思考和工具调用 |
| `stream=True` | 流式输出 |
| `client.files.create()` | 上传文件 |
| `client.files.content()` | 获取 Kimi 解析后的文件内容 |
| `client.files.list()` / `delete()` | 管理已上传文件 |

## 安装与设置 API Key

```powershell
python -m pip install --upgrade "openai>=1.0"
$env:MOONSHOT_API_KEY = Read-Host 'MOONSHOT_API_KEY' -MaskInput
```

## 1. endpoint 与客户端

| 平台 | `base_url` |
| --- | --- |
| 中国开放平台 | `https://api.moonshot.cn/v1` |
| 国际开放平台 | `https://api.moonshot.ai/v1` |

Key 必须与平台注册区域匹配。以下示例使用中国开放平台：

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["MOONSHOT_API_KEY"],
    base_url="https://api.moonshot.cn/v1",
)
```

## 2. 文本生成

```python
response = client.chat.completions.create(
    model="kimi-k2.6",
    messages=[
        {"role": "system", "content": "你是一个简洁的中文技术老师。"},
        {"role": "user", "content": "用三点解释 API 调用。"},
    ],
)

print(response.choices[0].message.content)
print(response.usage)
```

模型名称与可用能力可能按地区和套餐不同，应先查看控制台或当前模型列表。

## 3. 多轮对话

```python
messages = [
    {"role": "system", "content": "你是 Python 老师。"},
    {"role": "user", "content": "字典是什么？"},
]

first = client.chat.completions.create(model="kimi-k2.6", messages=messages)
messages.append({
    "role": "assistant",
    "content": first.choices[0].message.content,
})
messages.append({"role": "user", "content": "给一个按键读取值的例子。"})

second = client.chat.completions.create(model="kimi-k2.6", messages=messages)
print(second.choices[0].message.content)
```

长对话会持续消耗上下文。应用应控制历史长度，必要时做摘要，而不是无限追加。

## 4. 流式输出

```python
stream = client.chat.completions.create(
    model="kimi-k2.6",
    messages=[{"role": "user", "content": "写一份 Python API 学习建议。"}],
    stream=True,
)

for chunk in stream:
    if not chunk.choices:
        continue
    text = chunk.choices[0].delta.content or ""
    print(text, end="", flush=True)
```

思考模型可能额外返回 `reasoning_content`。做多轮工具调用时，是否必须保留该字段应以所选模型的官方说明为准。

## 5. 控制思考模式

Kimi 特有的顶层请求字段通过 `extra_body` 传入：

```python
response = client.chat.completions.create(
    model="kimi-k2.6",
    messages=[{"role": "user", "content": "比较两种数据库迁移方案。"}],
    extra_body={"thinking": {"type": "enabled"}},
)

print(response.choices[0].message.content)
```

不同模型允许的 `thinking` 值不同；不要把其他厂商的 `reasoning_effort` 直接照搬过来。

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
    model="kimi-k2.6",
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
        "content": json.dumps(result, ensure_ascii=False),
    })

if assistant_message.tool_calls:
    final = client.chat.completions.create(
        model="kimi-k2.6",
        messages=messages,
        tools=tools,
    )
    print(final.choices[0].message.content)
```

Kimi 思考模型进行多步工具调用时，通常要完整保留 assistant 消息中的扩展字段。最稳妥的做法是直接把 SDK 返回的 assistant message 追加到历史，而不是只复制文本。

## 7. 上传并解析文件

```python
from pathlib import Path

file_path = Path(r"D:\data\paper.pdf")

with file_path.open("rb") as file_handle:
    uploaded = client.files.create(
        file=file_handle,
        purpose="file-extract",
    )

file_content = client.files.content(file_id=uploaded.id).text

response = client.chat.completions.create(
    model="kimi-k2.6",
    messages=[
        {"role": "system", "content": file_content},
        {"role": "user", "content": "总结文档并列出三个关键结论。"},
    ],
)

print(response.choices[0].message.content)
```

较新的 Kimi API 也可能支持在消息中用 `ms://<file_id>` 引用文件。两种方式不要混写，应按当前 Chat API 的 File reference 说明选择。

文件管理示例：

```python
for item in client.files.list().data:
    print(item.id, item.filename)

client.files.delete(uploaded.id)
```

## 8. 查看模型

```python
models = client.models.list()
for model in models.data:
    print(model.id)
```

这比从旧博客复制模型名更可靠，但模型能力、上下文和计费仍要查官方模型说明。

## 常见易错点

- 中国与国际 endpoint、API Key 混用。
- 忘记配置 `base_url`，请求被发到 OpenAI。
- Kimi 特有字段没有放进 `extra_body`。
- 思考/工具调用只保留文本，丢失 `reasoning_content` 或 `tool_calls`。
- 文件上传后没有读取解析内容或按 API 要求引用文件。
- 长对话无限追加，最终超过上下文或成本过高。

## 官方延伸阅读

- [Kimi API 文档](https://platform.kimi.com/docs)
- [国际 API Overview](https://platform.kimi.ai/docs/api/overview)
- [Create Chat Completion](https://platform.kimi.ai/docs/api/chat)
- [Tool Use](https://platform.kimi.ai/docs/guide/use-kimi-k2-model)
- [Upload File](https://platform.kimi.ai/docs/api/files-upload)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
