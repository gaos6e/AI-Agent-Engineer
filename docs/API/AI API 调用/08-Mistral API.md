---
title: Mistral API 调用
source: https://docs.mistral.ai/resources/sdks
source_checked: 2026-07-22
source_baseline:
  - Mistral SDK Clients、Chat、Vision、Function Calling、Embeddings 与 OCR
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "已核对当前官方 Python SDK 主入口与离线语法；未使用真实凭据执行网络调用"
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

当前 SDK 文档的 Python 主线为 `from mistralai.client import Mistral` 与 `client.chat.complete(...)`。即便其他供应商也有“chat completion”名称，也不要复用其 stream event、tool result、OCR 或 JSON 参数结构；这些示例只说明 Mistral 当前 SDK 外形，生产前仍要以精确 SDK 版本和 API reference 做集成验证。

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
python -m pip install --upgrade mistralai  # 安装或更新 Mistral 官方 Python SDK。
$env:MISTRAL_API_KEY = Read-Host 'MISTRAL_API_KEY' -MaskInput  # 仅在当前 PowerShell 进程以遮罩方式读取 Key，不写入代码。
```

## 1. 文本生成

```python
import os  # 导入环境变量访问接口，避免将 API Key 硬编码到源码中。
from mistralai.client import Mistral  # 导入当前 SDK 的同步客户端类。

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])  # 从进程环境读取 Key 并创建客户端。

response = client.chat.complete(  # 发起一轮 Mistral Chat 请求。
    model="mistral-medium-latest",  # 使用学习方便的 latest 别名；生产应评估是否固定快照。
    messages=[  # 按角色和时间顺序传入上下文。
        {"role": "system", "content": "你是一个简洁的中文技术老师。"},  # 约束回答风格。
        {"role": "user", "content": "用三点解释 API 调用。"},  # 当前用户问题。
    ],
)

print(response.choices[0].message.content)  # 输出第一候选助手消息的文本。
print(response.usage)  # 输出服务返回的实际用量。
```

`*-latest` 会指向系列的较新版本，便于学习但可能随时间变化。生产项目应查看 [Models](https://docs.mistral.ai/getting-started/models) 并评估是否固定快照。

## 2. 多轮对话

```python
messages = [  # 在应用侧保存完整历史；API 调用之间不会自动记忆。
    {"role": "system", "content": "你是 Python 老师。"},  # 固定系统指令。
    {"role": "user", "content": "字典是什么？"},  # 第一轮用户问题。
]

first = client.chat.complete(  # 发送首轮消息并取得回答。
    model="mistral-medium-latest",  # 使用本例模型。
    messages=messages,  # 传入当前历史。
)

messages.append({  # 将首轮回答追加进历史，供下一轮看到。
    "role": "assistant",  # 声明消息来自助手。
    "content": first.choices[0].message.content,  # 保存第一候选回答文本。
})
messages.append({"role": "user", "content": "给一个读取键值的例子。"})  # 添加基于前文的追问。

second = client.chat.complete(  # 用完整历史发起第二轮请求。
    model="mistral-medium-latest",  # 保持模型一致，避免无意改变行为。
    messages=messages,  # 包含首轮问答与追问。
)

print(second.choices[0].message.content)  # 输出第二轮文本回答。
```

## 3. 流式输出

```python
stream = client.chat.stream(  # 请求服务以 Mistral 事件对象形式流式返回内容。
    model="mistral-medium-latest",  # 选择流式生成的目标模型。
    messages=[  # 提供本轮用户消息。
        {"role": "user", "content": "写一份 Python API 学习建议。"},  # 本轮生成任务。
    ],
)

for event in stream:  # 按到达顺序消费每个 Mistral 流事件。
    text = event.data.choices[0].delta.content  # 从事件的 data 层读取第一候选文本增量。
    if text:  # 仅在本次确有可见文字时输出。
        print(text, end="", flush=True)  # 立即打印增量文本，模拟流式界面。
```

流式响应的外层通常是事件对象，实际增量在 `event.data` 中，这与 OpenAI SDK 的 chunk 结构不同。

## 4. 图片理解

```python
response = client.chat.complete(  # 发起同时包含图片和文本指令的视觉请求。
    model="mistral-small-latest",  # 选择支持视觉输入的模型；能力需按当前文档核对。
    messages=[  # 构造一条多模态用户消息。
        {  # 单条用户消息对象。
            "role": "user",  # 指定消息角色。
            "content": [  # 使用内容块数组组合任务和图片。
                {"type": "text", "text": "解释图表趋势并提取坐标轴名称。"},  # 描述图片分析任务。
                {  # 第二个内容块提供图片。
                    "type": "image_url",  # 声明图片以 URL 引用。
                    "image_url": "https://docs.mistral.ai/img/eiffel-tower-paris.jpg",  # 使用官方公开示例图片地址。
                },
            ],
        }
    ],
)

print(response.choices[0].message.content)  # 输出视觉理解的文本结果。
```

图片可使用公开 URL 或 Base64。普通视觉问答使用 Chat Completions；文档版面、表格和扫描件解析更适合 OCR。

## 5. JSON 输出

```python
import json  # 导入标准 JSON 解析器，用于在本地验证返回内容。

response = client.chat.complete(  # 请求模型以 JSON 模式生成学习计划。
    model="mistral-medium-latest",  # 选择支持 JSON 输出的模型。
    messages=[{  # 将格式要求明确写入用户消息。
        "role": "user",  # 声明消息来自用户。
        "content": "请用 JSON 返回学习计划，字段为 topic、days、tasks。",  # 同时指定 JSON 和预期字段。
    }],
    response_format={"type": "json_object"},  # 请求 API 输出 JSON 对象。
)

data = json.loads(response.choices[0].message.content)  # 解析文本结果；无效 JSON 会立即抛出异常。
print(data["tasks"])  # 读取 tasks 字段；生产代码还应校验类型和值域。
```

如果业务要求固定字段与类型，应进一步使用 JSON Schema 或 SDK 的结构化输出能力，并继续做本地校验。

## 6. Function Calling

```python
import json  # 用于解析模型函数参数并序列化本地工具结果。


def get_weather(city: str) -> dict:  # 定义宿主实际执行的无副作用教学工具。
    return {"city": city, "temperature": 25, "unit": "celsius"}  # 返回固定离线数据，避免真实网络调用。


tools = [{  # 向模型声明一个可调用的函数工具。
    "type": "function",  # 指定工具类别。
    "function": {  # 描述函数名称、用途和输入 schema。
        "name": "get_weather",  # 名称必须与宿主白名单中的函数一致。
        "description": "查询指定城市的天气。",  # 帮助模型判断何时调用。
        "parameters": {  # 使用 JSON Schema 限制输入。
            "type": "object",  # 参数必须是对象。
            "properties": {"city": {"type": "string"}},  # 只允许 city 字符串字段。
            "required": ["city"],  # 调用时必须提供 city。
        },
    },
}]

messages = [{"role": "user", "content": "上海现在多少度？"}]  # 初始化会在工具轮次间保存的消息历史。
first = client.chat.complete(  # 先让模型决定是否需要工具调用。
    model="mistral-medium-latest",  # 选择支持 Function Calling 的模型。
    messages=messages,  # 发送当前用户问题。
    tools=tools,  # 提供允许执行的工具 schema。
)

assistant_message = first.choices[0].message  # 取得模型消息及可能存在的 tool_calls。
messages.append(assistant_message)  # 原样保存 assistant 消息，供回传工具结果时关联上下文。

for tool_call in assistant_message.tool_calls or []:  # 遍历所有工具调用；空值时安全跳过。
    arguments = json.loads(tool_call.function.arguments)  # 解析模型给出的 JSON 参数；生产代码应先做 schema、权限和语义校验。
    result = get_weather(**arguments)  # 将通过校验的参数解包传给本地函数。
    messages.append({  # 添加与当前调用 ID 对应的工具结果消息。
        "role": "tool",  # 声明该消息承载工具执行结果。
        "tool_call_id": tool_call.id,  # 精确关联模型原始调用 ID。
        "name": tool_call.function.name,  # 回传该工具名称，满足此 SDK 的工具消息结构。
        "content": json.dumps(result, ensure_ascii=False),  # 将结果编码为 JSON，并保留中文字符。
    })

if assistant_message.tool_calls:  # 只有实际执行工具后才发起续接轮。
    final = client.chat.complete(  # 让模型基于工具结果生成最终回答。
        model="mistral-medium-latest",  # 使用与工具决策轮一致的模型。
        messages=messages,  # 传入 assistant tool-call 和匹配的 tool 结果。
        tools=tools,  # 继续提供同一工具契约。
    )
    print(final.choices[0].message.content)  # 输出最终文本回答。
```

参数来自模型，执行前必须验证。模型一次可能要求调用多个工具。

## 7. Embedding

```python
response = client.embeddings.create(  # 调用 Embeddings API，将多段文本转换为数值向量。
    model="mistral-embed",  # 选择入库和查询时必须保持一致的 embedding 模型。
    inputs=[  # 注意 Mistral SDK 使用 inputs 作为批量输入参数名。
        "Python 适合快速开发。",  # 第一条输入文本。
        "Rust 重视性能和内存安全。",  # 第二条输入文本。
    ],
)

vectors = [item.embedding for item in response.data]  # 按响应顺序取出每条文本对应的向量。
print(len(vectors), len(vectors[0]))  # 检查向量数量和单条维度。
```

注意这里的参数名是 `inputs`，不是一些兼容 SDK 中常见的 `input`。

## 8. OCR：解析本地 PDF

```python
from pathlib import Path  # 用 Path 表示本地 PDF 路径。

pdf_path = Path(r"D:\data\paper.pdf")  # 替换为拥有上传和处理授权的实际 PDF 文件。

with pdf_path.open("rb") as pdf_file:  # 以二进制只读方式打开文件，并在结束后自动关闭句柄。
    uploaded = client.files.upload(  # 上传 PDF 并保存服务返回的文件对象。
        file={  # 按 SDK 需要的对象形式提供文件元数据与内容。
            "file_name": pdf_path.name,  # 传递原始文件名。
            "content": pdf_file,  # 传递已打开的二进制文件对象。
        },
        purpose="ocr",  # 声明上传用途为 OCR 解析。
    )

signed_url = client.files.get_signed_url(file_id=uploaded.id)  # 为已上传文件申请临时受控访问 URL。

ocr_response = client.ocr.process(  # 将文件 URL 提交给 OCR 处理入口。
    model="mistral-ocr-latest",  # 选择 OCR 模型；生产环境需评估 latest 漂移风险。
    document={  # 按 OCR schema 构造文档输入。
        "type": "document_url",  # 表示 document_url 字段保存可访问的文档地址。
        "document_url": signed_url.url,  # 使用刚获取的临时签名 URL。
    },
)

for page in ocr_response.pages:  # 遍历 OCR 返回的每个页面。
    print(page.markdown)  # 输出该页的 Markdown 表示；生产代码应按数据保留策略存储或删除。
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
