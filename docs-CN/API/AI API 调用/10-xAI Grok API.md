---
title: "xAI Grok API 调用"
source: https://docs.x.ai/developers/quickstart
source_checked: 2026-07-22
source_baseline:
  - xAI Quickstart、Grok 4.5、Responses API、Function Calling 与 Web Search
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "已核对当前 Grok 4.5 与 Responses API 文档并做离线语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - xAI
  - Grok
  - Python
aliases:
  - Grok API
  - xAI API
lang: zh-CN
translation_key: API/AI API 调用/10-xAI Grok API.md
translation_route: en/api/ai-api-reference/xai-grok-api
translation_default_route: zh-CN/API/AI-API-调用/10-xAI-Grok-API
---

# xAI Grok API 调用

> [!source] 官方来源
> 基于 [xAI Quickstart](https://docs.x.ai/developers/quickstart)、官方 Python SDK、Responses API、Function Calling 和 Agent Tools 文档整理。xAI 同时提供原生 `xai-sdk` 和 OpenAI 兼容接口。

## 两种调用方式

| 方式 | 适合场景 |
| --- | --- |
| `xai-sdk` | 多轮聊天、xAI 原生搜索/代码工具、图片和视频等能力 |
| `openai` 兼容接口 | 已熟悉 Responses API，或从 OpenAI 代码迁移 |

初学者可以先选一种主线。下面先介绍原生 SDK，再补充 OpenAI 兼容写法。

## 安装与设置 API Key

```powershell
python -m pip install --upgrade xai-sdk openai  # 安装或更新原生 xAI SDK 与 OpenAI 兼容客户端依赖。
$env:XAI_API_KEY = Read-Host 'XAI_API_KEY' -MaskInput  # 仅在当前 PowerShell 进程以遮罩方式读取 Key，不写入代码。
```

## 1. xAI SDK 文本调用

```python
from xai_sdk import Client  # 导入 xAI 原生 SDK 的客户端类。
from xai_sdk.chat import system, user  # 导入构造系统和用户聊天消息的辅助函数。

client = Client()  # 从进程环境中的 XAI_API_KEY 创建原生客户端；不要硬编码凭据。

chat = client.chat.create(model="grok-4.5")  # 创建由 SDK 在本地维护历史的聊天对象。
chat.append(system("你是一个简洁、准确的中文技术老师。"))  # 追加系统指令，约束回答风格。
chat.append(user("用三点解释 API 调用。"))  # 追加当前用户问题。

response = chat.sample()  # 请求模型基于当前聊天历史生成一轮回答。
print(response.content)  # 输出模型返回的可见内容。
```

模型名更新较快，应从 [Models](https://docs.x.ai/developers/models) 复制当前 ID。不要把网页产品名称直接当成 API 模型名。

## 2. xAI SDK 多轮对话

```python
chat = client.chat.create(model="grok-4.5")  # 创建独立会话对象来保存本例历史。

chat.append(user("Python 的字典是什么？"))  # 追加第一轮用户问题。
first = chat.sample()  # 生成第一轮回答。
print(first.content)  # 输出第一轮文本内容。
chat.append(first)  # 将完整模型回复追加回历史，而不是只复制可见文本。

chat.append(user("给一个读取键值的例子。"))  # 在同一会话中追加追问。
second = chat.sample()  # 生成第二轮回答，SDK 会携带前文。
print(second.content)  # 输出第二轮文本内容。
```

底层 API 仍是无状态的，`chat` 对象只是在客户端帮助维护历史。需要跨进程恢复时，应由应用持久化会话。

## 3. xAI SDK 流式输出

```python
chat = client.chat.create(model="grok-4.5")  # 创建用于流式生成的聊天对象。
chat.append(user("写一份 Python API 学习建议。"))  # 追加本轮流式生成任务。

final_response = None  # 预留变量保存流结束时累计的完整模型回复。
for response, chunk in chat.stream():  # 原生 SDK 每次同时提供累计 response 和当前增量 chunk。
    final_response = response  # 持续更新为当前完整回复，供流结束后写入历史。
    print(chunk.content, end="", flush=True)  # 立即输出当前文本增量，模拟流式界面。

if final_response is not None:  # 正常收到至少一个流事件后才更新会话历史。
    chat.append(final_response)  # 保存完整回复，避免下一轮丢失模型内容结构。
```

`chat.stream()` 同时返回持续累积的 `response` 与当前 `chunk`，这与 OpenAI SDK 的流式事件结构不同。

## 4. OpenAI 兼容 Responses API

```python
import os  # 导入环境变量访问接口，避免把 API Key 写进源码。
from openai import OpenAI  # 导入用于 xAI OpenAI 兼容 Responses 接口的客户端类。

openai_client = OpenAI(  # 创建指向 xAI 兼容 endpoint 的客户端。
    api_key=os.environ["XAI_API_KEY"],  # 从当前进程环境读取 Key。
    base_url="https://api.x.ai/v1",  # 覆盖默认地址，指向 xAI 的兼容 API。
)

response = openai_client.responses.create(  # 发起一轮 Responses API 请求。
    model="grok-4.5",  # 选择本课示例模型；部署前以官方模型页核对。
    instructions="你是一个简洁、准确的中文技术老师。",  # 设置本轮的高层行为指令。
    input="用三点解释 API 调用。",  # 提供当前用户输入。
)

print(response.output_text)  # 输出 SDK 汇总的文本便利属性。
```

常用入口仍是 `responses.create()`；旧 Chat Completions 主要用于兼容既有项目，新功能优先看 Responses 文档。

当前 Grok 4.5 文档建议对连续会话设置 `prompt_cache_key`，以增加命中同一缓存服务器的机会。它只影响供应商的缓存路由/成本表现，**不是**用户、tenant、会话授权或本地业务幂等键；应用仍要分别保存可信 actor、对象级 ACL 和自己的 `operation_id`，也不应把原始敏感 prompt 当作缓存键写入日志。

## 5. 兼容接口的流式输出

```python
stream = openai_client.responses.create(  # 请求 Responses API 返回可逐事件消费的流。
    model="grok-4.5",  # 选择流式生成的目标模型。
    input="写一份 Python API 学习建议。",  # 提供本轮生成任务。
    stream=True,  # 开启事件流模式。
)

for event in stream:  # 按到达顺序消费每个 Responses 事件。
    if event.type == "response.output_text.delta":  # 只处理文本增量事件，其他事件有不同含义。
        print(event.delta, end="", flush=True)  # 立即显示这段文本增量。
```

工具调用、失败和完成也会产生其他事件，应按 `event.type` 处理。

## 6. 图片理解

```python
response = openai_client.responses.create(  # 发起包含公开图片 URL 的多模态 Responses 请求。
    model="grok-4.5",  # 选择支持视觉输入的模型；能力应按当前官方文档核对。
    input=[  # 使用结构化输入数组传入用户多模态消息。
        {  # 单条用户消息对象。
            "role": "user",  # 指定消息角色。
            "content": [  # 使用内容块数组组合文字任务和图片。
                {"type": "input_text", "text": "解释图表趋势并提取坐标轴名称。"},  # 描述图片分析任务。
                {  # 第二个内容块提供图片。
                    "type": "input_image",  # 声明这是图像输入。
                    "image_url": "https://api.nga.gov/iiif/a2e6da57-3cd1-4235-b20e-95dcaefed6c8/full/!800,800/0/default.jpg",  # 使用公开示例图片；生产须遵守访问与版权规则。
                },
            ],
        }
    ],
)

print(response.output_text)  # 输出 SDK 汇总的视觉分析文本。
```

必须使用支持视觉输入的模型。图片格式、大小和 token 计算以当前 Image Understanding 文档为准。

## 7. 服务端搜索工具

xAI 原生 SDK 可让 Grok 使用 Web 搜索、X 搜索等服务端工具：

```python
from xai_sdk.chat import user  # 导入构造用户聊天消息的辅助函数。
from xai_sdk.tools import web_search, x_search  # 导入 xAI 原生的服务端搜索工具工厂。

chat = client.chat.create(  # 创建允许模型使用受控服务端搜索工具的会话。
    model="grok-4.5",  # 选择当前支持该工具的模型；能力和计费需以官方文档为准。
    tools=[web_search(), x_search()],  # 显式开放 Web 和 X 搜索工具，而不是允许任意网络访问。
)
chat.append(user("查找今天 Python 官方生态的重要更新，并附来源。"))  # 追加需要时效检索的用户任务。

response = chat.sample()  # 让模型按工具合同完成一轮回答。
print(response.content)  # 输出最终文本；生产代码还应读取 citations 和工具调用详情。
```

可用工具与返回引用结构会随 SDK 和账户变化。需要可核验结果时，应检查工具调用详情和 citations，而不是只保存最终文本。

## 8. 自定义函数调用

以下使用 OpenAI 兼容 Responses 格式：

```python
import json  # 用于解析模型函数参数并序列化本地工具结果。


def get_weather(city: str) -> dict:  # 定义由宿主程序实际执行的无副作用教学工具。
    return {"city": city, "temperature": 25, "unit": "celsius"}  # 返回固定离线数据，避免真实网络调用。


tools = [{  # 向模型声明一个可调用的 Responses 函数工具。
    "type": "function",  # 指定工具类别。
    "name": "get_weather",  # 工具名必须与宿主白名单一致。
    "description": "查询指定城市的天气。",  # 帮助模型判断何时调用。
    "parameters": {  # 使用 JSON Schema 限制参数形状。
        "type": "object",  # 参数必须为对象。
        "properties": {"city": {"type": "string"}},  # 只允许 city 字符串字段。
        "required": ["city"],  # 调用时必须提供 city。
        "additionalProperties": False,  # 拒绝未声明字段，缩小可执行输入面。
    },
}]

response = openai_client.responses.create(  # 先让模型决定是否需要调用该函数。
    model="grok-4.5",  # 选择支持 Function Calling 的模型。
    input="上海现在多少度？",  # 提供可能触发工具的用户问题。
    tools=tools,  # 发送允许执行的工具 schema。
)

tool_outputs = []  # 收集每个 function_call 对应的一条 function_call_output。
for item in response.output:  # 遍历模型本轮的全部输出项。
    if item.type == "function_call" and item.name == "get_weather":  # 仅处理白名单内的函数调用。
        arguments = json.loads(item.arguments)  # 解析模型给出的 JSON 参数；生产代码必须先做 schema、权限和语义校验。
        result = get_weather(**arguments)  # 将通过校验的参数传给本地函数。
        tool_outputs.append({  # 追加与本次函数调用精确绑定的输出项。
            "type": "function_call_output",  # 声明这是工具执行结果。
            "call_id": item.call_id,  # 关联模型给出的函数调用 ID。
            "output": json.dumps(result, ensure_ascii=False),  # 将结果编码为 JSON，并保留中文字符。
        })

if tool_outputs:  # 只有实际执行过函数时才创建续接轮。
    final = openai_client.responses.create(  # 让模型基于工具结果生成最终回答。
        model="grok-4.5",  # 使用与工具决策轮一致的模型。
        input=tool_outputs,  # 将全部工具输出一次性回传。
        tools=tools,  # 继续提供同一工具契约。
        previous_response_id=response.id,  # 关联上一 Response，以保留本轮工具调用上下文。
    )
    print(final.output_text)  # 输出基于工具结果生成的文本回答。
```

xAI 默认可并行请求多个函数。应处理全部调用、校验参数，再继续对话。

## 9. 常见原生 SDK 能力

官方 xAI SDK 还提供以下入口，属于按需学习内容：

| 能力 | 常见入口 |
| --- | --- |
| 图像生成 | `client.image` 相关方法 |
| 视频生成 | `client.video.generate()` |
| 模型信息 | `client.models` 相关方法 |
| Tokenization | `client.tokenize` 相关方法 |
| 延迟任务 | deferred chat / polling |

这些能力的模型、参数和返回对象变化较快，使用前应直接打开当前 SDK 示例，不建议从旧教程复制整段代码。

## 常见易错点

- 原生 `xai-sdk` 与 OpenAI 兼容 SDK 的响应对象混用。
- 兼容调用忘记 `base_url="https://api.x.ai/v1"`。
- 流式代码混用 `chat.stream()` 的 tuple 与 Responses 的 event。
- 使用旧 Chat Completions 示例学习新工具能力。
- 搜索工具只读取最终文本，没有保留引用。
- 并行函数调用只处理第一个工具。
- 模型名来自聊天产品界面，而不是 API Models 页。

## 官方延伸阅读

- [xAI Quickstart](https://docs.x.ai/developers/quickstart)
- [Official Python SDK](https://github.com/xai-org/xai-sdk-python)
- [Responses API](https://docs.x.ai/developers/api-reference#responses)
- [Function Calling](https://docs.x.ai/developers/tools/function-calling)
- [Web Search](https://docs.x.ai/developers/tools/web-search)
- [Image Understanding](https://docs.x.ai/developers/image-understanding)
- [Models](https://docs.x.ai/developers/models)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
