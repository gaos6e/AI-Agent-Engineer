---
title: "Qwen API 调用"
source: https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen
source_checked: 2026-07-22
source_baseline:
  - 百炼首次调用千问 API、文本生成模型、结构化输出与工具调用
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "已核对当前模型推荐、能力矩阵与主调用入口并做离线语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - Qwen
  - DashScope
  - Python
aliases:
  - 通义千问 API
  - DashScope API
lang: zh-CN
translation_key: API/AI API 调用/05-Qwen API.md
translation_route: en/api/ai-api-reference/qwen-api
translation_default_route: zh-CN/API/AI-API-调用/05-Qwen-API
---

# Qwen API 调用

> [!source] 官方来源
> 基于阿里云百炼 [首次调用通义千问 API](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen)、文本生成、流式输出和 Function Calling 文档整理。初学阶段优先使用 OpenAI 兼容接口，熟悉后再按需学习 DashScope SDK。

## 常用入口

| Python 写法 | 用途 |
| --- | --- |
| `client.chat.completions.create()` | 文本、多轮、图片、JSON 和工具调用 |
| `stream=True` | 流式输出 |
| `client.embeddings.create()` | OpenAI 兼容的文本向量接口 |
| `dashscope.Generation.call()` | DashScope 原生文本生成接口 |

## 安装与设置 API Key

```powershell
python -m pip install --upgrade openai  # 安装或更新调用兼容接口所需的 Python SDK。
$env:DASHSCOPE_API_KEY = Read-Host 'DASHSCOPE_API_KEY' -MaskInput  # 仅在当前 PowerShell 进程以遮罩方式读取 Key，不写入代码。
```

## 1. 地域与客户端

API Key 与地域 endpoint 必须匹配。常见兼容地址包括：

| 地域 | `base_url` |
| --- | --- |
| 中国内地 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| 新加坡（国际） | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |

专属 Workspace 可能使用带 `{WorkspaceId}` 的地址，应直接复制控制台或当前官方文档给出的 endpoint。

```python
import os  # 导入环境变量访问接口，避免将 API Key 硬编码进源码。
from openai import OpenAI  # 导入可调用 OpenAI 兼容协议的客户端类。

client = OpenAI(  # 创建指向阿里云百炼兼容端点的客户端。
    api_key=os.environ["DASHSCOPE_API_KEY"],  # 从当前进程读取 Key；缺失时尽早失败。
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 选择中国内地兼容 endpoint；需与 Key 地域匹配。
)
```

## 2. 文本生成

```python
response = client.chat.completions.create(  # 发起一轮 OpenAI 兼容的聊天生成请求。
    model="qwen3.7-plus",  # 使用本课默认模型；部署前按目标地域和账户能力核对。
    messages=[  # 按角色和时间顺序提供本轮上下文。
        {"role": "system", "content": "你是一个简洁的中文技术老师。"},  # 约束回答的身份与表达风格。
        {"role": "user", "content": "用三点解释 API 调用。"},  # 当前用户问题。
    ],
)

print(response.choices[0].message.content)  # 输出第一候选助手消息的文本内容。
print(response.usage)  # 输出服务返回的实际 token 用量。
```

模型系列更新较快。2026-07-22 的官方文本模型页将 `qwen3.7-plus` 列为 Agent/通用任务的平衡推荐，并标注 1M 上下文、思考、Function Calling、内置工具和结构化输出支持；本页因此使用它作为教学默认值。能力矩阵不是每个地域、账户、endpoint 或套餐的实际授权证明，低延迟、代码、视觉或超长上下文任务仍应从 [模型列表](https://help.aliyun.com/zh/model-studio/models) 与目标地域控制台重新选型。

## 3. 多轮对话

```python
messages = [  # 在应用侧保存完整历史；兼容接口本身无跨请求记忆。
    {"role": "system", "content": "你是 Python 老师。"},  # 固定的系统指令。
    {"role": "user", "content": "字典是什么？"},  # 第一轮用户问题。
]

first = client.chat.completions.create(  # 发送首轮消息并取得回答。
    model="qwen3.7-plus",  # 使用本课示例模型。
    messages=messages,  # 传入当前对话记录。
)

messages.append({  # 将模型回答追加进历史，供下一轮看到。
    "role": "assistant",  # 声明该条消息来自助手。
    "content": first.choices[0].message.content,  # 保存第一候选回答文本。
})
messages.append({"role": "user", "content": "给一个读取键值的例子。"})  # 追加基于前文的追问。

second = client.chat.completions.create(  # 将完整历史再次发送，发起第二轮请求。
    model="qwen3.7-plus",  # 保持模型一致，避免对话行为无意改变。
    messages=messages,  # 包含系统指令、首轮问答和追问。
)

print(second.choices[0].message.content)  # 输出第二轮文本回答。
```

## 4. 流式输出与 Token 统计

```python
stream = client.chat.completions.create(  # 请求服务以增量 chunk 形式返回回答。
    model="qwen3.7-plus",  # 选择流式生成的模型。
    messages=[{"role": "user", "content": "写一份 Python API 学习建议。"}],  # 提供本轮用户任务。
    stream=True,  # 开启流式返回。
    stream_options={"include_usage": True},  # 请求在末尾额外返回用量信息。
)

for chunk in stream:  # 按到达顺序消费每个增量响应。
    if chunk.choices:  # 普通文本 chunk 通常包含候选列表。
        text = chunk.choices[0].delta.content or ""  # 读取第一候选的文本增量；空值时替换为空字符串。
        print(text, end="", flush=True)  # 立即打印可见文本，模拟流式界面。
    elif chunk.usage:  # 最后一个仅含用量的 chunk 可能没有 choices。
        print("\nToken：", chunk.usage.total_tokens)  # 输出本轮总 token 数。
```

最后一个仅含 `usage` 的 chunk 可能没有 `choices`，因此要先判断。

## 5. 图片理解

```python
response = client.chat.completions.create(  # 发起包含远程图片 URL 的视觉理解请求。
    model="qwen3-vl-plus",  # 选择视觉模型，不要将这种输入格式发给纯文本模型。
    messages=[  # 构造一条多模态用户消息。
        {  # 单条用户消息对象。
            "role": "user",  # 指定消息角色。
            "content": [  # 使用内容块数组组合图片与文字任务。
                {  # 第一个内容块提供图片。
                    "type": "image_url",  # 声明图片以 URL 形式提供。
                    "image_url": {  # 包装实际图片地址。
                        "url": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"  # 使用官方公开示例图片 URL。
                    },
                },
                {"type": "text", "text": "解释图表趋势并提取坐标轴名称。"},  # 第二个内容块说明图片分析任务。
            ],
        }
    ],
)

print(response.choices[0].message.content)  # 输出第一候选的视觉分析文本。
```

图像、视频、音频的支持取决于模型系列。不要把文本模型与 `Qwen-VL`、`Qwen-Omni` 的输入格式混用。

## 6. JSON 模式

```python
import json  # 导入标准 JSON 解析器，用于在本地验证返回内容。

response = client.chat.completions.create(  # 请求模型以 JSON 模式生成学习计划。
    model="qwen3.7-plus",  # 选择支持 JSON 响应模式的模型。
    messages=[{  # 将格式要求明确写入用户消息。
        "role": "user",  # 声明消息来自用户。
        "content": "请用 JSON 返回学习计划，字段为 topic、days、tasks。",  # 同时指定输出格式和预期字段。
    }],
    response_format={"type": "json_object"},  # 请求 API 返回 JSON 对象。
)

data = json.loads(response.choices[0].message.content)  # 解析文本结果；格式不合法时会立即报错。
print(data["tasks"])  # 读取 tasks 字段；生产代码还应校验类型和值域。
```

提示中必须明确要求 JSON，并在 Python 中继续做解析和字段校验。

## 7. Function Calling

```python
import json  # 用于解析模型声明的函数参数并序列化本地工具结果。


def get_weather(city: str) -> dict:  # 定义由宿主实际执行的无副作用教学工具。
    return {"city": city, "temperature": 25, "unit": "celsius"}  # 返回离线固定值，避免示例访问真实服务。


tools = [{  # 向模型声明一个允许调用的函数工具。
    "type": "function",  # 工具类别为函数调用。
    "function": {  # 描述函数的名称、用途和输入 schema。
        "name": "get_weather",  # 必须与宿主白名单中的函数名一致。
        "description": "查询指定城市的天气。",  # 帮助模型判断何时调用工具。
        "parameters": {  # 使用 JSON Schema 限制输入结构。
            "type": "object",  # 参数必须是一个对象。
            "properties": {"city": {"type": "string"}},  # 只定义 city 字符串字段。
            "required": ["city"],  # 调用时必须提供 city。
        },
    },
}]

messages = [{"role": "user", "content": "上海现在多少度？"}]  # 初始化会在工具轮次间积累的对话历史。
first = client.chat.completions.create(  # 先让模型决定是否调用工具。
    model="qwen3.7-plus",  # 选择支持 Function Calling 的模型。
    messages=messages,  # 发送当前用户问题。
    tools=tools,  # 提供宿主允许执行的工具 schema。
    tool_choice="auto",  # 允许模型自行决定是否以及调用哪个声明工具。
)

assistant_message = first.choices[0].message  # 取出模型回复和可能包含的 tool_calls。
messages.append(assistant_message)  # 原样保留 assistant 调用消息，供回传结果时关联上下文。

for tool_call in assistant_message.tool_calls or []:  # 遍历模型请求的所有工具调用；空值时安全跳过。
    arguments = json.loads(tool_call.function.arguments)  # 解析模型传来的 JSON 参数；生产代码必须先做 schema、权限和语义校验。
    result = get_weather(**arguments)  # 将通过校验的参数传入本地函数。
    messages.append({  # 追加与这次调用 ID 对应的工具结果消息。
        "role": "tool",  # 声明消息承载本地工具执行结果。
        "tool_call_id": tool_call.id,  # 精确绑定模型发起的调用 ID。
        "content": json.dumps(result, ensure_ascii=False),  # 将结果编码为 JSON，并保留中文字符。
    })

if assistant_message.tool_calls:  # 只有实际发生工具调用时才发起续接轮。
    final = client.chat.completions.create(  # 让模型根据返回的工具结果生成最终回答。
        model="qwen3.7-plus",  # 使用与工具决策轮一致的模型。
        messages=messages,  # 传入 assistant tool-call 与每个工具结果。
        tools=tools,  # 继续提供同一工具契约。
    )
    print(final.choices[0].message.content)  # 输出最终文本回答。
```

思考模型做工具调用时，部分模型要求保留 `reasoning_content`；应查看所选模型的 Function Calling 注意事项。

## 8. 文本 Embedding

```python
embedding_response = client.embeddings.create(  # 调用 Embeddings API，将多段文本转换为数值向量。
    model="text-embedding-v4",  # 选择入库与查询时必须保持一致的 embedding 模型。
    input=[  # 批量提供待向量化的文本。
        "Python 适合快速开发。",  # 第一条输入。
        "Rust 重视性能和内存安全。",  # 第二条输入。
    ],
)

vectors = [item.embedding for item in embedding_response.data]  # 按服务返回顺序取出每个向量。
print(len(vectors), len(vectors[0]))  # 检查向量数量和单条维度。
```

不同 embedding 模型支持的地域、维度和输入类型不同；向量入库与查询必须保持相同模型和维度。

## 9. DashScope SDK 基础写法

```powershell
python -m pip install --upgrade dashscope  # 安装或更新阿里云原生 DashScope Python SDK。
```

```python
import os  # 导入环境变量访问接口。
import dashscope  # 导入 DashScope SDK 主模块。
from dashscope import Generation  # 导入原生文本生成调用入口。

dashscope.api_key = os.environ["DASHSCOPE_API_KEY"]  # 从进程环境配置 SDK Key；不要硬编码真实凭据。

response = Generation.call(  # 通过 DashScope 原生 SDK 发起生成请求。
    model="qwen3.7-plus",  # 选择本课示例模型。
    messages=[  # 传入本轮用户消息。
        {"role": "user", "content": "用三点解释 API 调用。"},  # 当前用户问题。
    ],
    result_format="message",  # 请求按消息对象格式返回，而不是其他结果结构。
)

print(response.output.choices[0].message.content)  # 输出第一候选消息的文本内容。
```

OpenAI 兼容接口便于迁移；DashScope SDK 更接近阿里云原生能力。一个项目中应明确主调用方式，避免响应对象混用。

## 常见易错点

- API Key 与地域 endpoint 不匹配。
- 最后一个流式 chunk 没有 `choices`，代码却直接访问下标。
- 文本、视觉、Omni 模型的输入格式混用。
- 工具调用没有回传 `tool_call_id` 对应结果。
- 依赖模型别名却不关注升级和下线公告。
- 同时使用 OpenAI SDK 与 DashScope SDK，却按同一种响应结构取值。

## 官方延伸阅读

- [首次调用通义千问 API](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen)
- [文本生成](https://help.aliyun.com/zh/model-studio/text-generation)
- [流式输出](https://help.aliyun.com/zh/model-studio/stream)
- [Function Calling](https://help.aliyun.com/zh/model-studio/qwen-function-calling)
- [视觉理解](https://help.aliyun.com/zh/model-studio/vision-model)
- [向量化](https://help.aliyun.com/zh/model-studio/embedding)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
