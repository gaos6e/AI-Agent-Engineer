---
title: DeepSeek API 调用
source: https://api-docs.deepseek.com/
source_checked: 2026-07-22
source_baseline:
  - DeepSeek Your First API Call、Models & Pricing、Thinking Mode、Tool Calls
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "已核对当前官方主入口和模型迁移公告并做离线语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - DeepSeek
  - Python
aliases:
  - DeepSeek API
---

# DeepSeek API 调用

> [!source] 官方来源
> 基于 [DeepSeek API Docs](https://api-docs.deepseek.com/) 与 [Create Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion) 整理。DeepSeek 使用 OpenAI 兼容的 Chat Completions 格式，Python 中通常直接使用 `openai` 包。

> [!warning] 旧模型迁移有明确截止时间
> 在 2026-07-22 核对的官方首页中，`deepseek-chat` 与 `deepseek-reasoner` 计划于 **2026-07-24 15:59 UTC** 弃用；兼容期内它们分别对应 `deepseek-v4-flash` 的非思考和思考模式。新代码不要再把旧名写成默认值；迁移时仍须显式设置并评测 `thinking` / `reasoning_effort`、工具调用、上下文和成本，而不是只替换模型字符串。

## 常用能力

| 写法 | 用途 |
| --- | --- |
| `client.chat.completions.create()` | 文本、多轮、思考模式、JSON 和工具调用 |
| `stream=True` | 流式返回文本和思考内容 |
| `response_format={"type": "json_object"}` | JSON 模式 |
| `tools=[...]` | Function Calling |

## 安装与设置 API Key

```powershell
python -m pip install --upgrade openai  # 安装或更新用于调用 OpenAI 兼容接口的 Python SDK。
$env:DEEPSEEK_API_KEY = Read-Host 'DEEPSEEK_API_KEY' -MaskInput  # 仅在当前 PowerShell 进程以遮罩方式读取 Key，不写入代码。
```

## 1. 创建客户端与文本调用

```python
import os  # 导入环境变量访问接口，避免把 API Key 写在源码中。
from openai import OpenAI  # 导入兼容 Chat Completions 协议的客户端类。

client = OpenAI(  # 创建指向 DeepSeek 服务端点的客户端。
    api_key=os.environ["DEEPSEEK_API_KEY"],  # 从进程环境读取 Key；缺失时让程序尽早报错。
    base_url="https://api.deepseek.com",  # 覆盖默认 OpenAI 地址，指向 DeepSeek 的兼容 API。
)

response = client.chat.completions.create(  # 发起一轮 Chat Completions 请求。
    model="deepseek-v4-flash",  # 选择本课示例模型；运行前按官方模型页核对迁移状态。
    messages=[  # 按角色和时间顺序提供上下文。
        {"role": "system", "content": "你是一个简洁的中文技术老师。"},  # 约束回答风格的系统指令。
        {"role": "user", "content": "用三点解释 API 调用。"},  # 当前用户问题。
    ],
)

print(response.choices[0].message.content)  # 输出第一候选消息的文本内容。
print(response.usage)  # 输出服务返回的实际用量。
```

`deepseek-v4-flash` 适合常规学习示例；更复杂任务可查看官方模型页后改用能力更强的模型。不要根据聊天网页显示名猜 API 模型名。

## 2. 多轮对话

API 无状态，需要把历史消息继续放进 `messages`：

```python
messages = [  # 在应用侧保存完整多轮历史；API 不会自动记忆上一请求。
    {"role": "system", "content": "你是 Python 老师。"},  # 固定的行为约束。
    {"role": "user", "content": "列表是什么？"},  # 第一轮用户提问。
]

first = client.chat.completions.create(  # 发送第一轮历史并取得回答。
    model="deepseek-v4-flash",  # 使用本例模型。
    messages=messages,  # 传入当前积累的消息列表。
)

assistant_text = first.choices[0].message.content  # 取出第一候选助手文本。
messages.append({"role": "assistant", "content": assistant_text})  # 将回答回写进历史，供下一轮看到。
messages.append({"role": "user", "content": "给我一个 append 的例子。"})  # 追加基于前文的第二轮追问。

second = client.chat.completions.create(  # 将完整历史再次发送，发起第二轮请求。
    model="deepseek-v4-flash",  # 保持模型一致，避免对话行为无意改变。
    messages=messages,  # 包含系统指令、首轮问答和追问。
)

print(second.choices[0].message.content)  # 输出第二轮的文本回答。
```

## 3. 思考模式

DeepSeek 的扩展请求字段可通过 OpenAI SDK 的 `extra_body` 传入：

```python
response = client.chat.completions.create(  # 发起启用模型推理配置的 Chat Completions 请求。
    model="deepseek-v4-pro",  # 选择本例的复杂任务模型；字段支持需以当前文档为准。
    messages=[  # 提供需要比较的用户问题。
        {"role": "user", "content": "比较归并排序和快速排序。"},  # 本轮用户输入。
    ],
    reasoning_effort="high",  # 请求较高推理预算；不是所有模型都支持此参数。
    extra_body={"thinking": {"type": "enabled"}},  # 将 DeepSeek 特有的扩展字段透传给兼容 API。
)

message = response.choices[0].message  # 取出第一候选消息对象。
print(message.content)  # 输出最终可见文本，而不默认展示内部推理内容。
```

思考配置、可用强度与返回字段会随模型变化，应按当前模型文档设置，不要默认所有模型都支持同一参数。

## 4. 流式输出

```python
stream = client.chat.completions.create(  # 请求服务器以增量 chunk 形式返回回答。
    model="deepseek-v4-flash",  # 选择流式生成的目标模型。
    messages=[{"role": "user", "content": "写一份 Python API 学习建议。"}],  # 提供本轮用户任务。
    stream=True,  # 开启流式模式。
)

for chunk in stream:  # 按服务到达顺序消费每个增量响应。
    if not chunk.choices:  # 某些 chunk 不含候选内容，先跳过。
        continue  # 避免访问空 choices 列表。
    delta = chunk.choices[0].delta  # 取得第一候选的本次增量字段。
    if delta.content:  # 只在本次确有可见文本时输出。
        print(delta.content, end="", flush=True)  # 立即打印文本分片，模拟流式界面。
```

思考模型流式返回时，可用 `getattr(delta, "reasoning_content", None)` 检查 SDK 暴露的思考增量，但不要把内部思考直接展示给最终用户或写入后续对话，除非官方模型文档明确要求保留。

## 5. JSON 模式

```python
import json  # 导入标准 JSON 解析器，用于在本地验证模型返回内容。

response = client.chat.completions.create(  # 请求模型以 JSON 模式生成学习计划。
    model="deepseek-v4-flash",  # 选择支持该响应模式的模型。
    messages=[  # 将格式要求也明确写进用户指令。
        {  # 构造单条用户消息。
            "role": "user",  # 声明该消息来自用户。
            "content": (  # 使用括号书写较长的字符串字面量。
                "请以 JSON 返回 Python 学习计划，字段为 topic、days、tasks。"  # 明确要求 JSON 以及预期字段。
            ),
        }
    ],
    response_format={"type": "json_object"},  # 请求 API 约束输出为 JSON 对象。
)

data = json.loads(response.choices[0].message.content)  # 将文本解析为 Python 对象；格式异常会立即报错。
print(data["tasks"])  # 读取 tasks 字段；生产代码还应校验字段类型和值域。
```

启用 JSON 模式时，提示中也应明确要求输出 JSON。返回内容仍要经过 `json.loads()` 和业务字段校验。

## 6. Function Calling

```python
import json  # 用于解析模型声明的函数参数并序列化工具结果。


def get_weather(city: str) -> dict:  # 定义由宿主程序真正执行的无副作用教学工具。
    return {"city": city, "temperature": 25, "unit": "celsius"}  # 返回固定离线数据，避免示例访问真实服务。


tools = [{  # 向模型声明一个可调用的函数工具。
    "type": "function",  # 指定工具类别为函数。
    "function": {  # 描述函数名称、用途和参数 schema。
        "name": "get_weather",  # 名称必须与宿主白名单中的函数一致。
        "description": "查询指定城市的天气。",  # 帮助模型判断何时选择该函数。
        "parameters": {  # 使用 JSON Schema 描述允许的输入。
            "type": "object",  # 参数必须是对象。
            "properties": {"city": {"type": "string"}},  # 仅允许 city 字符串字段。
            "required": ["city"],  # 调用时必须提供 city。
        },
    },
}]

messages = [{"role": "user", "content": "上海现在多少度？"}]  # 初始化会在工具轮次间保留的对话历史。
first = client.chat.completions.create(  # 先让模型选择是否发起工具调用。
    model="deepseek-v4-pro",  # 选择支持函数调用的模型。
    messages=messages,  # 发送当前用户问题。
    tools=tools,  # 提供允许调用的工具 schema。
)

assistant_message = first.choices[0].message  # 取出模型返回的 assistant 消息和可能的 tool_calls。
messages.append(assistant_message)  # 原样保留 assistant tool-call 消息，供后续回传结果时关联上下文。

for tool_call in assistant_message.tool_calls or []:  # 遍历所有请求，空值时安全地使用空列表。
    if tool_call.function.name == "get_weather":  # 仅执行明确允许的工具名称。
        arguments = json.loads(tool_call.function.arguments)  # 解析模型给出的 JSON 参数；生产代码应先做 schema 和权限校验。
        result = get_weather(**arguments)  # 将通过校验的参数解包传给本地函数。
        messages.append({  # 追加与这次调用一一对应的 tool 消息。
            "role": "tool",  # 声明该消息承载本地工具执行结果。
            "tool_call_id": tool_call.id,  # 绑定模型最初给出的调用 ID。
            "content": json.dumps(result, ensure_ascii=False),  # 将结果序列化为 JSON，并保留中文字符。
        })

if assistant_message.tool_calls:  # 有工具调用时，将结果回传给模型继续生成答案。
    final = client.chat.completions.create(  # 发起包含 tool 结果的续接请求。
        model="deepseek-v4-pro",  # 使用与工具决策轮一致的模型。
        messages=messages,  # 发送 assistant tool-call 和匹配的 tool 结果。
        tools=tools,  # 继续提供同一工具契约。
    )
    print(final.choices[0].message.content)  # 输出基于工具结果生成的最终文本。
else:  # 模型没有要求工具时，直接显示它已给出的回答。
    print(assistant_message.content)  # 输出无需工具续接的文本内容。
```

工具参数必须校验。若模型一次返回多个工具调用，应全部处理后再请求最终回答。

## 7. 常用生成参数

| 参数 | 作用 |
| --- | --- |
| `temperature` | 控制随机性；并非所有思考模型都建议修改 |
| `max_tokens` | 限制最大输出长度 |
| `stream` | 是否流式输出 |
| `response_format` | 请求 JSON 输出 |
| `tools` / `tool_choice` | 提供工具并控制使用方式 |
| `extra_body` | 传递 DeepSeek 特有扩展字段 |

## 错误处理

DeepSeek 使用 OpenAI Python SDK，因此可捕获 `openai.AuthenticationError`、`RateLimitError`、`APITimeoutError`、`APIConnectionError` 和 `APIStatusError`。常见问题包括 Key/额度错误、限流、模型名失效以及 `base_url` 配置错误。

## 常见易错点

- 忘记配置 `base_url="https://api.deepseek.com"`。
- 把 DeepSeek 特有字段直接当成 OpenAI SDK 标准参数；扩展字段通常放入 `extra_body`。
- 多轮对话没有保留历史消息。
- JSON 模式没有在提示中明确要求 JSON，或没有校验字段。
- 函数调用只执行工具，没有把 `tool` 消息回传给模型。
- 继续使用 `deepseek-chat` 或 `deepseek-reasoner`；它们计划于 2026-07-24 15:59 UTC 弃用，应先完成受控迁移和回归评测。

## 官方延伸阅读

- [DeepSeek API Docs](https://api-docs.deepseek.com/)
- [Create Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion)
- [Multi-round Conversation](https://api-docs.deepseek.com/guides/multi_round_chat)
- [JSON Output](https://api-docs.deepseek.com/guides/json_mode)
- [Function Calling](https://api-docs.deepseek.com/guides/function_calling)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
