---
title: Kimi API 调用
source: https://platform.kimi.com/docs/guide/start-using-kimi-api
source_checked: 2026-07-22
source_baseline:
  - Kimi API overview、Kimi K2.6 quickstart、Chat Completion 与 Tool Use
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "已核对当前官方 quickstart 与模型能力边界并做离线语法检查；未使用真实凭据执行网络调用"
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

> [!warning] 不把 Kimi 的 `web_search` 作为新生产依赖
> 2026-07-22 的 K2.6 quickstart 明示该工具正在升级、现有文档已过时且近期不建议使用。需要联网检索时，选择有当前稳定合同的检索提供方，并把引用、时效、访问控制和失败回退留在应用层；不要因模型能调用工具就跳过这些门。

## 安装与设置 API Key

```powershell
python -m pip install --upgrade "openai>=1.0"  # 安装或更新用于调用兼容接口的 OpenAI Python SDK。
$env:MOONSHOT_API_KEY = Read-Host 'MOONSHOT_API_KEY' -MaskInput  # 仅在当前 PowerShell 进程以遮罩方式读取 Key，不写入代码。
```

## 1. endpoint 与客户端

| 平台 | `base_url` |
| --- | --- |
| 中国开放平台 | `https://api.moonshot.cn/v1` |
| 国际开放平台 | `https://api.moonshot.ai/v1` |

Key 必须与平台注册区域匹配。以下示例使用中国开放平台：

```python
import os  # 导入环境变量访问接口，避免将 API Key 硬编码到源码中。
from openai import OpenAI  # 导入可调用 OpenAI 兼容协议的客户端类。

client = OpenAI(  # 创建指向中国 Kimi 开放平台 endpoint 的客户端。
    api_key=os.environ["MOONSHOT_API_KEY"],  # 从当前进程环境读取 Key；缺失时让程序尽早失败。
    base_url="https://api.moonshot.cn/v1",  # 选择中国 endpoint；国际 Key 应改用对应国际地址。
)
```

## 2. 文本生成

```python
response = client.chat.completions.create(  # 发起一轮聊天生成请求。
    model="kimi-k2.6",  # 选择本课示例模型；实际可用性需按区域和套餐核对。
    messages=[  # 按角色和时间顺序传入消息。
        {"role": "system", "content": "你是一个简洁的中文技术老师。"},  # 约束回答风格的系统指令。
        {"role": "user", "content": "用三点解释 API 调用。"},  # 当前用户问题。
    ],
)

print(response.choices[0].message.content)  # 输出第一候选助手消息的文本。
print(response.usage)  # 输出服务返回的实际用量。
```

模型名称与可用能力可能按地区和套餐不同，应先查看控制台或当前模型列表。

## 3. 多轮对话

```python
messages = [  # 在应用侧保存完整对话历史；API 请求之间不会自动记忆。
    {"role": "system", "content": "你是 Python 老师。"},  # 固定行为约束。
    {"role": "user", "content": "字典是什么？"},  # 第一轮用户提问。
]

first = client.chat.completions.create(model="kimi-k2.6", messages=messages)  # 发送首轮历史并取得回答。
messages.append({  # 将首轮回答加入历史，供下一轮看到。
    "role": "assistant",  # 声明消息来自助手。
    "content": first.choices[0].message.content,  # 保存第一候选回答文本。
})
messages.append({"role": "user", "content": "给一个按键读取值的例子。"})  # 添加基于前文的追问。

second = client.chat.completions.create(model="kimi-k2.6", messages=messages)  # 发送完整历史发起第二轮。
print(second.choices[0].message.content)  # 输出第二轮文本回答。
```

长对话会持续消耗上下文。应用应控制历史长度，必要时做摘要，而不是无限追加。

## 4. 流式输出

```python
stream = client.chat.completions.create(  # 请求服务器以增量 chunk 返回生成内容。
    model="kimi-k2.6",  # 选择流式生成的目标模型。
    messages=[{"role": "user", "content": "写一份 Python API 学习建议。"}],  # 提供本轮用户任务。
    stream=True,  # 开启流式模式。
)

for chunk in stream:  # 按到达顺序消费每个流分片。
    if not chunk.choices:  # 某些分片不包含候选内容。
        continue  # 跳过空 choices，避免下标访问错误。
    text = chunk.choices[0].delta.content or ""  # 读取第一候选文本增量；缺失时使用空字符串。
    print(text, end="", flush=True)  # 立即输出增量文本，模拟流式界面。
```

思考模型可能额外返回 `reasoning_content`。做多轮工具调用时，是否必须保留该字段应以所选模型的官方说明为准。

## 5. K2.6 的思考模式：可显式关闭，不臆造跨厂商开关

K2.6 的官方 quickstart 将长思考作为模型能力，并展示了**关闭**它的顶层请求字段。通过 OpenAI SDK 时把厂商扩展放入 `extra_body`：

```python
response = client.chat.completions.create(  # 发起一个显式关闭思考模式的兼容请求。
    model="kimi-k2.6",  # 选择 K2.6 模型；扩展字段应以当前官方说明为准。
    messages=[{"role": "user", "content": "比较两种数据库迁移方案。"}],  # 提供需要比较的用户问题。
    extra_body={"thinking": {"type": "disabled"}},  # 将 Kimi 特有的关闭思考字段透传给服务。
)

print(response.choices[0].message.content)  # 输出模型最终可见文本，而非假设存在推理内容。
```

`kimi-k2.6` 的当前示例不要求调用者传入 `enabled`；不要从其他厂商照搬 `reasoning_effort` 或自造 `thinking` 值。若成本、时延或工具轨迹依赖思考配置，先在目标地区、精确模型和 SDK 版本上做非敏感集成验证，再把结果写入路由/评测基线。

## 6. Function Calling

```python
import json  # 用于解析模型函数参数和序列化工具结果。


def get_weather(city: str) -> dict:  # 定义由宿主程序实际执行的无副作用教学工具。
    return {"city": city, "temperature": 25, "unit": "celsius"}  # 返回离线固定数据，避免例子访问真实天气服务。


tools = [{  # 声明模型可选择调用的函数工具。
    "type": "function",  # 指定工具类别。
    "function": {  # 描述函数名称、用途和输入 schema。
        "name": "get_weather",  # 必须与宿主的工具白名单一致。
        "description": "查询指定城市的天气。",  # 帮助模型选择工具。
        "parameters": {  # 使用 JSON Schema 限制参数。
            "type": "object",  # 参数必须是对象。
            "properties": {"city": {"type": "string"}},  # 只允许 city 字符串字段。
            "required": ["city"],  # 调用时必须提供 city。
        },
    },
}]

messages = [{"role": "user", "content": "上海现在多少度？"}]  # 初始化会在工具轮次间保存的消息历史。
first = client.chat.completions.create(  # 先让模型决定是否需要调用工具。
    model="kimi-k2.6",  # 选择支持工具调用的模型。
    messages=messages,  # 发送当前用户问题。
    tools=tools,  # 提供允许执行的工具契约。
)

assistant_message = first.choices[0].message  # 取得模型消息及可能存在的 tool_calls。
messages.append(assistant_message)  # 原样保存 assistant 消息，保留扩展字段和调用关联信息。

for tool_call in assistant_message.tool_calls or []:  # 遍历所有工具调用；未调用时安全跳过。
    arguments = json.loads(tool_call.function.arguments)  # 解析模型传来的 JSON 参数；生产代码须先做 schema、权限和语义校验。
    result = get_weather(**arguments)  # 将通过校验的参数解包传给本地函数。
    messages.append({  # 添加一条与当前调用 ID 对应的工具结果。
        "role": "tool",  # 声明消息承载本地工具执行结果。
        "tool_call_id": tool_call.id,  # 精确关联模型发起的调用。
        "content": json.dumps(result, ensure_ascii=False),  # 序列化结果为 JSON，并保留中文字符。
    })

if assistant_message.tool_calls:  # 只有实际执行过工具时才请求模型续接。
    final = client.chat.completions.create(  # 让模型基于回传的工具结果生成最终答案。
        model="kimi-k2.6",  # 使用与工具决策轮一致的模型。
        messages=messages,  # 包含完整 assistant 消息与对应 tool 结果。
        tools=tools,  # 继续提供同一工具 schema。
    )
    print(final.choices[0].message.content)  # 输出最终文本回答。
```

Kimi 思考模型进行多步工具调用时，通常要完整保留 assistant 消息中的扩展字段。最稳妥的做法是直接把 SDK 返回的 assistant message 追加到历史，而不是只复制文本。

## 7. 上传并解析文件

```python
from pathlib import Path  # 用 Path 表示本地文件路径，避免手工拼接分隔符。

file_path = Path(r"D:\data\paper.pdf")  # 替换为拥有上传和处理授权的实际 PDF 路径。

with file_path.open("rb") as file_handle:  # 以二进制只读方式打开文件，并在退出后自动关闭句柄。
    uploaded = client.files.create(  # 上传文件并保存服务返回的文件对象。
        file=file_handle,  # 将已打开的二进制文件作为上传内容。
        purpose="file-extract",  # 声明该文件用于服务端解析提取。
    )

file_content = client.files.content(file_id=uploaded.id).text  # 读取服务解析出的文本；生产代码要考虑大小和敏感数据边界。

response = client.chat.completions.create(  # 基于解析后的文档文本发起总结请求。
    model="kimi-k2.6",  # 选择本例的文本模型。
    messages=[  # 将提取内容和用户任务作为对话上下文。
        {"role": "system", "content": file_content},  # 将文件正文作为系统上下文；真实应用应做分块、权限与长度控制。
        {"role": "user", "content": "总结文档并列出三个关键结论。"},  # 指定文档分析任务。
    ],
)

print(response.choices[0].message.content)  # 输出文档总结文本。
```

较新的 Kimi API 也可能支持在消息中用 `ms://<file_id>` 引用文件。两种方式不要混写，应按当前 Chat API 的 File reference 说明选择。

文件管理示例：

```python
for item in client.files.list().data:  # 遍历当前账号可见的已上传文件。
    print(item.id, item.filename)  # 显示文件标识和名称，避免打印不必要的文件内容。

client.files.delete(uploaded.id)  # 删除本例刚上传的文件；生产代码应确认保留策略和目标 ID。
```

## 8. 查看模型

```python
models = client.models.list()  # 向服务查询当前账户可见的模型列表。
for model in models.data:  # 遍历每个模型对象。
    print(model.id)  # 输出 API 模型 ID，供后续在官方能力表中核验。
```

这比从旧博客复制模型名更可靠，但模型能力、上下文和计费仍要查官方模型说明。

## 常见易错点

- 中国与国际 endpoint、API Key 混用。
- 忘记配置 `base_url`，请求被发到 OpenAI。
- Kimi 特有字段没有放进 `extra_body`。
- 思考/工具调用只保留文本，丢失 `reasoning_content` 或 `tool_calls`。
- 依赖正在升级且当前文档明确不建议使用的 `web_search` 作为生产检索合同。
- 文件上传后没有读取解析内容或按 API 要求引用文件。
- 长对话无限追加，最终超过上下文或成本过高。

## 官方延伸阅读

- [Kimi API 文档](https://platform.kimi.com/docs)
- [国际 API Overview](https://platform.kimi.ai/docs/api/overview)
- [Create Chat Completion](https://platform.kimi.ai/docs/api/chat)
- [Tool Use](https://platform.kimi.ai/docs/guide/use-kimi-k2-model)
- [Upload File](https://platform.kimi.ai/docs/api/files-upload)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
