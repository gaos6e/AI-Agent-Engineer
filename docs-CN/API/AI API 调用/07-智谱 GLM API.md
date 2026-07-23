---
title: "智谱 GLM API 调用"
source: https://docs.bigmodel.cn/cn/guide/develop/python/introduction
source_checked: 2026-07-22
source_baseline:
  - 智谱官方 Python SDK、模型概览、流式消息、工具调用与思考模式
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "已核对当前官方 Python SDK 与模型概览并做离线语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - GLM
  - Zhipu
  - Python
aliases:
  - 智谱 API
  - BigModel API
  - Z.AI API
lang: zh-CN
translation_key: API/AI API 调用/07-智谱 GLM API.md
translation_route: en/api/ai-api-reference/zhipu-glm-api
translation_default_route: zh-CN/API/AI-API-调用/07-智谱-GLM-API
---

# 智谱 GLM API 调用

> [!source] 官方来源
> 基于 [官方 Python SDK](https://docs.bigmodel.cn/cn/guide/develop/python/introduction)、流式消息、视觉理解和工具调用文档整理。中国智谱开放平台使用 `ZhipuAiClient`，Python 包名为 `zai-sdk`。

> [!important] 本页教学默认值已随官方 SDK 升级
> 2026-07-22 的官方 Python SDK 用 `glm-5.2` 演示文本、流式与工具调用，并以 `glm-5v-turbo` 演示视觉输入；本页对应默认值已更新。它们只是当前课程基线，不保证每个账户、套餐或地域可用，也不代表旧 `glm-5.1` 在已有回归/路由中可以无评测直接替换。

## 常用入口

| Python 方法 | 用途 |
| --- | --- |
| `client.chat.completions.create()` | 文本、多轮、流式、视觉和工具调用 |
| `client.embeddings.create()` | 文本向量 |
| `client.images.generations()` | 图像生成；按当前 SDK 版本核对签名 |
| `client.models.list()` | 查看可用模型；若当前 SDK/账户支持 |

## 安装与设置 API Key

```powershell
python -m pip install --upgrade zai-sdk  # 安装或更新当前官方 zai-sdk Python 包。
$env:ZAI_API_KEY = Read-Host 'ZAI_API_KEY' -MaskInput  # 仅在当前 PowerShell 进程以遮罩方式读取 Key，不写进代码。
```

> [!note]
> 历史代码可能使用 `zhipuai` 包或 `ZHIPUAI_API_KEY`。本笔记使用当前 `zai-sdk` 与 `ZAI_API_KEY`，不要混用两套示例。

## 1. 文本生成

```python
from zai import ZhipuAiClient  # 导入当前官方 SDK 的客户端类。

client = ZhipuAiClient()  # 从进程环境中的 ZAI_API_KEY 创建客户端；不要硬编码凭据。

response = client.chat.completions.create(  # 发起一轮 Chat Completions 请求。
    model="glm-5.2",  # 选择本课教学模型；上线前以官方模型页和账户权限核对。
    messages=[  # 按角色和时间顺序传入上下文。
        {"role": "system", "content": "你是一个简洁的中文技术老师。"},  # 约束回答风格。
        {"role": "user", "content": "用三点解释 API 调用。"},  # 当前用户问题。
    ],
    temperature=0.6,  # 设置适度随机性；模型支持的范围应以当前文档为准。
)

print(response.choices[0].message.content)  # 输出第一候选助手消息的文本内容。
print(response.usage)  # 输出服务返回的实际用量。
```

模型名更新较快，应从 [模型概览](https://docs.bigmodel.cn/cn/guide/start/model-overview) 选择。文本、视觉、图像生成和视频生成使用不同模型系列。

## 2. 多轮对话

```python
messages = [  # 在客户端保存完整历史；API 不会自动记住上一轮请求。
    {"role": "system", "content": "你是 Python 老师。"},  # 固定的系统指令。
    {"role": "user", "content": "字典是什么？"},  # 第一轮用户提问。
]

first = client.chat.completions.create(model="glm-5.2", messages=messages)  # 发起首轮请求。
messages.append({  # 将首轮回答追加进历史，供下一轮上下文使用。
    "role": "assistant",  # 声明消息来自助手。
    "content": first.choices[0].message.content,  # 保存第一候选的回答文本。
})
messages.append({"role": "user", "content": "给一个读取键值的例子。"})  # 添加基于前文的追问。

second = client.chat.completions.create(model="glm-5.2", messages=messages)  # 将完整历史发送给第二轮。
print(second.choices[0].message.content)  # 输出第二轮文本回答。
```

## 3. 流式输出

```python
stream = client.chat.completions.create(  # 请求服务以增量 chunk 形式返回生成内容。
    model="glm-5.2",  # 选择流式生成的模型。
    messages=[{"role": "user", "content": "写一份 Python API 学习建议。"}],  # 提供本轮用户任务。
    stream=True,  # 开启流式模式。
)

for chunk in stream:  # 按到达顺序消费每个流分片。
    if not chunk.choices:  # 有些分片不含候选内容。
        continue  # 跳过空 choices，避免下标访问错误。
    delta = chunk.choices[0].delta  # 读取第一候选的本次增量字段。
    if delta.content:  # 只在有可见文本时输出。
        print(delta.content, end="", flush=True)  # 立即打印文本增量，模拟流式界面。
```

思考模型可能在 `delta.reasoning_content` 中返回思考增量，最后一个 chunk 还可能包含 `finish_reason` 和 `usage`。

## 4. 图片理解

```python
response = client.chat.completions.create(  # 发起包含公开图片 URL 的视觉理解请求。
    model="glm-5v-turbo",  # 选择视觉模型，不能将图像内容格式发送给纯文本模型。
    messages=[  # 构造一条多模态用户消息。
        {  # 单条用户消息对象。
            "role": "user",  # 指定消息角色。
            "content": [  # 使用内容块数组组合文字任务和图片。
                {"type": "text", "text": "解释图表趋势并提取坐标轴名称。"},  # 说明图片分析任务。
                {  # 第二个内容块提供图片 URL。
                    "type": "image_url",  # 声明图片由 URL 引用。
                    "image_url": {  # 包装实际的图片地址。
                        "url": "https://api.nga.gov/iiif/a2e6da57-3cd1-4235-b20e-95dcaefed6c8/full/!800,800/0/default.jpg"  # 使用公开示例图片，生产中须遵守访问和版权规则。
                    },
                },
            ],
        }
    ],
)

print(response.choices[0].message.content)  # 输出视觉分析得到的文本。
```

本地图片可编码为 `data:image/png;base64,...`。图片格式、大小与模型能力以视觉模型文档为准。

## 5. Function Calling

```python
import json  # 用于解析模型函数参数并序列化本地工具结果。


def get_weather(city: str) -> dict:  # 定义由宿主实际执行的无副作用教学工具。
    return {"city": city, "temperature": 25, "unit": "celsius"}  # 返回固定离线值，避免示例访问真实服务。


tools = [{  # 声明模型可选择调用的函数工具。
    "type": "function",  # 指定工具类别。
    "function": {  # 描述函数名称、用途和输入 schema。
        "name": "get_weather",  # 工具名必须匹配宿主白名单。
        "description": "查询指定城市的天气。",  # 帮助模型判断何时调用。
        "parameters": {  # 使用 JSON Schema 限制参数形状。
            "type": "object",  # 参数必须是对象。
            "properties": {"city": {"type": "string"}},  # 只允许 city 字符串字段。
            "required": ["city"],  # 调用时必须提供 city。
        },
    },
}]

messages = [{"role": "user", "content": "上海现在多少度？"}]  # 初始化会在工具轮次间保存的对话历史。
first = client.chat.completions.create(  # 先让模型决定是否调用工具。
    model="glm-5.2",  # 选择支持 Function Calling 的模型。
    messages=messages,  # 发送当前用户问题。
    tools=tools,  # 提供允许执行的工具 schema。
    tool_choice="auto",  # 允许模型自行决定是否调用工具。
)

assistant_message = first.choices[0].message  # 取得模型消息及可能存在的 tool_calls。
messages.append(assistant_message.model_dump())  # 序列化并保留完整 assistant 消息，避免丢失工具关联字段。

for tool_call in assistant_message.tool_calls or []:  # 遍历全部工具调用；未调用时安全跳过。
    arguments = json.loads(tool_call.function.arguments)  # 解析模型给出的 JSON 参数；生产代码应先做 schema、权限和语义校验。
    result = get_weather(**arguments)  # 将通过校验的参数解包传给本地函数。
    messages.append({  # 添加与当前调用 ID 对应的工具结果消息。
        "role": "tool",  # 声明该消息承载工具执行结果。
        "tool_call_id": tool_call.id,  # 精确关联模型的调用 ID。
        "content": json.dumps(result, ensure_ascii=False),  # 将结果编码为 JSON，并保留中文字符。
    })

if assistant_message.tool_calls:  # 只有实际执行过工具时才发起续接轮。
    final = client.chat.completions.create(  # 让模型基于工具结果生成最终回答。
        model="glm-5.2",  # 使用与工具决策轮一致的模型。
        messages=messages,  # 传入 assistant tool-call 和匹配的 tool 结果。
        tools=tools,  # 继续提供同一工具契约。
    )
    print(final.choices[0].message.content)  # 输出最终文本回答。
```

如果一次返回多个 `tool_calls`，应全部执行并回传。高风险函数必须做参数校验和人工确认。

## 6. 内置 Web Search

```python
response = client.chat.completions.create(  # 发起允许模型使用内置 Web Search 的请求。
    model="glm-5.2",  # 选择当前支持该工具的模型；能力与计费需以官方文档为准。
    messages=[  # 提供需要检索时效信息的用户任务。
        {"role": "user", "content": "查找今天 Python 官方生态的重要更新。"},  # 当前检索请求。
    ],
    tools=[  # 显式声明模型能够使用的内置工具。
        {  # 定义 Web Search 工具配置。
            "type": "web_search",  # 声明工具类别为内置网络检索。
            "web_search": {  # 配置检索关键词和结果返回方式。
                "search_query": "Python 官方更新",  # 设定工具实际发送的查询词。
                "search_result": True,  # 请求在响应中附带搜索结果信息。
            },
        }
    ],
)

print(response.choices[0].message.content)  # 输出模型整合搜索后的文本；生产代码还应核对引用和来源。
```

工具支持情况取决于模型和套餐，生产中应检查搜索结果及引用，而不是只信最终总结。

## 7. Embedding

```python
response = client.embeddings.create(  # 调用 Embeddings API，把多段文本转换为数值向量。
    model="embedding-3",  # 选择入库和查询时必须保持一致的 embedding 模型。
    input=[  # 批量提供待向量化文本。
        "Python 适合快速开发。",  # 第一条输入。
        "Rust 重视性能和内存安全。",  # 第二条输入。
    ],
)

vectors = [item.embedding for item in response.data]  # 按返回顺序取出每条文本对应的向量。
print(len(vectors), len(vectors[0]))  # 检查向量数量和单条维度。
```

Embedding 用于语义搜索、相似度、聚类和 RAG。向量入库与查询要使用同一模型及相同维度。

## 错误处理

```python
import zai  # 导入 SDK 模块，以便捕获其公开异常类型。

try:  # 将一次远程调用置于可分类处理的异常边界内。
    response = client.chat.completions.create(  # 发起最小聊天请求以演示异常捕获。
        model="glm-5.2",  # 使用运行前应确认仍可用的模型。
        messages=[{"role": "user", "content": "你好"}],  # 提供简单用户输入。
    )
except zai.core.APIStatusError as exc:  # 服务返回可识别的 API 状态错误。
    print("API 状态错误：", exc)  # 输出错误摘要；生产日志应脱敏并关联请求 ID。
except zai.core.APITimeoutError:  # SDK 等待服务响应超时。
    print("请求超时。")  # 提示调用方按整体预算决定是否受控重试。
```

这里只捕获当前示例能采取明确动作的 SDK 异常；未识别异常应保留调用栈并由应用边界统一记录，不用宽泛 `except Exception` 吞掉。

## 常见易错点

- `zai-sdk` 与旧 `zhipuai` 包混用。
- `ZAI_API_KEY` 与历史环境变量名混用。
- 通用 API endpoint 与 Coding 套餐 endpoint 混用。
- 文本模型处理图片，或把不同视觉模型的参数直接套用。
- 工具执行后没有回传 `tool_call_id`。
- 没有根据当前 SDK 版本核对图像生成、视频生成等低频方法签名。

## 官方延伸阅读

- [官方 Python SDK](https://docs.bigmodel.cn/cn/guide/develop/python/introduction)
- [流式消息](https://docs.bigmodel.cn/cn/guide/capabilities/streaming)
- [工具调用](https://docs.bigmodel.cn/cn/guide/capabilities/function-calling)
- [思考模式](https://docs.bigmodel.cn/cn/guide/capabilities/thinking-mode)
- [模型概览](https://docs.bigmodel.cn/cn/guide/start/model-overview)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
