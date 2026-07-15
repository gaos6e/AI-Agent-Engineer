---
title: Anthropic Claude API 调用
source: https://platform.claude.com/docs/en/claude_api_primer
source_checked: 2026-07-12
execution_verified: false
verification_note: "仅核对官方资料并做语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - Anthropic
  - Claude
  - Python
aliases:
  - Claude API
  - Anthropic API
---

# Anthropic Claude API 调用

> [!source] 官方来源
> 基于 [API usage primer](https://platform.claude.com/docs/en/claude_api_primer)、[Python SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python) 与 Messages API 文档整理。Claude 的主入口是 `Messages API`，Python 包名为 `anthropic`。

## 常用入口

| Python 方法 | 用途 |
| --- | --- |
| `client.messages.create()` | 单轮、多轮、图片和工具调用 |
| `client.messages.stream()` | 流式输出并可汇总最终消息 |
| `client.messages.count_tokens()` | 请求前估算输入 token |
| `client.models.list()` | 查看可用模型 |
| `client.beta.files.upload()` | 上传可复用文件；属于 beta 能力，按官方文档核对后再用 |

示例使用 `claude-sonnet-5`。它适合作为通用学习模型，但上线前仍应查看 [Models overview](https://platform.claude.com/docs/en/about-claude/models/overview)。

## 安装与设置 API Key

```powershell
python -m pip install --upgrade anthropic
$env:ANTHROPIC_API_KEY = Read-Host 'ANTHROPIC_API_KEY' -MaskInput
```

## 1. 最小文本调用

```python
from anthropic import Anthropic

client = Anthropic()

message = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=1024,
    system="你是一个简洁、准确的中文技术老师。",
    messages=[
        {"role": "user", "content": "用三点解释 API 调用。"},
    ],
)

print(message.content[0].text)
print(message.usage)
```

> [!important]
> Claude 的 `system` 是顶层参数，不要写成 `messages` 中的 `system` role。`max_tokens` 需要显式设置。

如果响应可能包含工具调用等不同内容块，不要只假设 `content[0]` 一定是文本：

```python
for block in message.content:
    if block.type == "text":
        print(block.text)
```

## 2. 多轮对话

Messages API 本身无状态，需要把历史消息重新传入：

```python
history = [
    {"role": "user", "content": "Python 的列表是什么？"},
    {"role": "assistant", "content": "列表是可变、有序的容器。"},
    {"role": "user", "content": "给我一个追加元素的例子。"},
]

message = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=512,
    messages=history,
)

print(message.content[0].text)
```

消息通常使用 `user` 与 `assistant` 两种角色，并按时间顺序排列。

## 3. 流式输出

```python
with client.messages.stream(
    model="claude-sonnet-5",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "写一份 Python API 学习建议。"},
    ],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

    final_message = stream.get_final_message()

print("\nToken：", final_message.usage)
```

如果只想逐事件处理且不需要 SDK 汇总最终消息，可用 `client.messages.create(..., stream=True)`。

## 4. 图片理解

```python
import base64
from pathlib import Path

image_path = Path(r"D:\data\chart.png")
image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")

message = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_data,
                    },
                },
                {"type": "text", "text": "解释图表趋势并提取坐标轴名称。"},
            ],
        }
    ],
)

print(message.content[0].text)
```

也可使用 URL 图片；具体支持格式、大小和图片数量限制应以 [Vision](https://platform.claude.com/docs/en/build-with-claude/vision) 为准。

## 5. 工具调用

```python
import json


def get_weather(city: str) -> dict:
    return {"city": city, "temperature": 25, "unit": "celsius"}


tools = [
    {
        "name": "get_weather",
        "description": "查询指定城市的天气。",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    }
]

messages = [{"role": "user", "content": "上海现在多少度？"}]

first = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=1024,
    tools=tools,
    messages=messages,
)

messages.append({"role": "assistant", "content": first.content})
tool_results = []

for block in first.content:
    if block.type == "tool_use" and block.name == "get_weather":
        result = get_weather(**block.input)
        tool_results.append(
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, ensure_ascii=False),
            }
        )

if tool_results:
    messages.append({"role": "user", "content": tool_results})
    final = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        tools=tools,
        messages=messages,
    )
    print(final.content[0].text)
```

流程是：模型返回 `tool_use` → Python 执行函数 → 以 `tool_result` 返回 → 模型生成最终回答。必须校验模型给出的参数，并限制高风险操作。

## 6. 预估输入 Token

```python
count = client.messages.count_tokens(
    model="claude-sonnet-5",
    system="你是中文技术老师。",
    messages=[
        {"role": "user", "content": "详细解释 Python 装饰器。"},
    ],
)

print(count.input_tokens)
```

它适合在发送长文档或长对话前检查上下文规模，但实际计费仍以正式响应的 `usage` 为准。

## 7. 异步调用

```python
import asyncio
from anthropic import AsyncAnthropic


async def main() -> None:
    client = AsyncAnthropic()
    message = await client.messages.create(
        model="claude-sonnet-5",
        max_tokens=512,
        messages=[{"role": "user", "content": "解释 async/await。"}],
    )
    print(message.content[0].text)


asyncio.run(main())
```

Web 服务或多个独立请求并发时再学习异步；单个脚本先用同步客户端更容易调试。

## 错误处理

```python
import anthropic

try:
    message = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=512,
        messages=[{"role": "user", "content": "你好"}],
    )
except anthropic.AuthenticationError:
    print("API Key 无效或权限不足。")
except anthropic.RateLimitError:
    print("触发限流，请稍后重试。")
except anthropic.APITimeoutError:
    print("请求超时。")
except anthropic.APIConnectionError:
    print("网络连接失败。")
except anthropic.APIStatusError as exc:
    print(exc.status_code, exc.request_id)
```

## 常见易错点

- 把 `system` 放进 `messages`。
- 忘记设置 `max_tokens`。
- 多轮对话只发送最新问题，导致模型看不到历史。
- 只读取第一个内容块，遗漏 `tool_use` 或其他块。
- 工具调用后没有回传与 `tool_use_id` 对应的 `tool_result`。
- 使用过时模型名；模型 ID 与退役时间应在官方模型页核对。

## 官方延伸阅读

- [API usage primer](https://platform.claude.com/docs/en/claude_api_primer)
- [Python SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python)
- [Streaming Messages](https://platform.claude.com/docs/en/build-with-claude/streaming)
- [Vision](https://platform.claude.com/docs/en/build-with-claude/vision)
- [Tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [Token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
