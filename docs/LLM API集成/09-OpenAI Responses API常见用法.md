---
title: OpenAI Responses API 常见用法
tags:
  - llm-api
  - openai
  - responses-api
  - python
aliases:
  - OpenAI Responses API 教程
  - OpenAI Responses API 实战
source_checked: 2026-07-22
source_baseline:
  - OpenAI Responses API Reference and official guides
content_origin: original
content_status: dynamic
---

# OpenAI Responses API 常见用法

> 资料核验日期：2026-07-22。模型标识、SDK 类型、工具参数、数据保留和价格都会变化；复制示例前请以项目锁定的 SDK 版本与 [Responses API Reference](https://developers.openai.com/api/docs/api-reference/responses) 为准。本文以 Python SDK 为主，默认把模型名放在环境变量中，避免把可变模型选择散落在业务代码里。

Responses API 是 OpenAI 面向新项目推荐的统一生成接口。一次请求可以接收文本或图像，返回文本、结构化结果或工具调用，并可通过 `previous_response_id`、手动 history 或 Conversations API 保持上下文。它不是“自动替你执行业务操作”的框架：模型提出 function call 后，仍必须由你的服务端验证、授权、执行并把结果回传。

## 先建立全局心智模型

一次 Responses 调用可以简化为：

```text
model + instructions + input + 可选 tools / state
                    ↓
response: id, status, output[], output_text, usage
```

| 需求 | 请求重点 | 应读取的结果 |
| --- | --- | --- |
| 普通问答、改写、总结 | `input` + 可选 `instructions` | `response.output_text` |
| 多轮聊天 | `previous_response_id`、手动 `history` 或 `conversation` | 新 response 的 `id` 与文本 |
| 长回答的实时显示 | `stream=True` | `response.output_text.delta` 等事件 |
| 给程序消费的固定字段 | `responses.parse(..., text_format=...)` 或 `text.format` | 已解析对象或 JSON |
| 调用你的数据库、订单系统 | `tools=[{"type": "function", ...}]` | `response.output` 中的 `function_call` |
| 查询最新网页资料 | `tools=[{"type": "web_search"}]` | 文本及 `url_citation` 标注 |
| 查询已上传的私有资料 | `tools=[{"type": "file_search", ...}]` | 文本及 `file_citation` 标注 |
| 看图、OCR、截图理解 | `input_image` 内容块 | `response.output_text` |

`output_text` 是“只想拿最终文本”时的便利属性。涉及工具、推理项或其他多模态输出时，应遍历 `response.output`，按每个 item 的 `type` 处理；不要假定 `output[0]` 永远是文本。

## 0. 安装与安全配置

在 PowerShell 7 中创建隔离环境。下面的环境变量只在当前终端会话有效；生产环境应使用部署平台的 secret manager 或受控环境变量，绝不把真实密钥放进前端、Markdown、Git 或日志。

```powershell
python -m venv .venv  # 在当前目录创建隔离的 Python 虚拟环境。
.\.venv\Scripts\Activate.ps1  # 激活虚拟环境，使后续 pip 安装只影响本项目。
python -m pip install --upgrade openai pydantic  # 安装 OpenAI SDK；结构化输出示例还会使用 Pydantic。

$env:OPENAI_API_KEY = "<从安全的密钥管理工具读取>"  # 仅放入当前终端；不要把真实值写进代码或 Git。
$env:OPENAI_MODEL = "gpt-5.6"  # 集中指定本教程使用的模型，业务项目应改为自己的配置值。
```

所有 Python 示例默认共享下面的初始化。若项目规定了固定模型、区域、代理或重试策略，应在自己的 adapter 配置层统一注入，而不是逐个调用硬编码。

```python
import os  # 用于读取操作系统环境变量。

from openai import OpenAI  # 导入 OpenAI Python SDK 的同步客户端。

client = OpenAI()  # 创建客户端；默认从 OPENAI_API_KEY 读取密钥。
MODEL = os.environ["OPENAI_MODEL"]  # 从集中环境变量读取模型名；缺失时立即报错而非静默选错模型。
```

## 1. 最小文本调用

`instructions` 放稳定的行为约束，`input` 放本轮任务。最小调用只需读取 `output_text`。

```python
response = client.responses.create(  # 向 Responses API 发起一次非流式生成请求。
    model=MODEL,  # 指定由集中配置提供的模型。
    instructions="你是一位耐心的 Python 助教，用中文、分步骤解释概念。",  # 给本轮模型稳定的行为指导。
    input="用一个短例子解释列表推导式。",  # 传入本轮用户任务。
)

print(response.output_text)  # 读取 SDK 汇总好的最终文本。
print("response id:", response.id)  # 输出 response ID，便于排障、续接或审计。
print("token usage:", response.usage)  # 输出本次调用的 token 用量对象。
```

当需要显式表示某轮用户消息时，`input` 也可以是 item 列表：

```python
response = client.responses.create(  # 发起一次使用 typed input item 的请求。
    model=MODEL,  # 指定本次调用的模型。
    instructions="回答不超过三条要点；不确定时明确说明。",  # 限制回答风格与不确定性表达。
    input=[  # 用列表显式描述输入 item，后续可扩展为多条消息或多模态内容。
        {  # 开始定义一条用户消息 item。
            "role": "user",  # 标识这条内容来自用户。
            "content": "比较列表和元组最重要的两个区别。",  # 放入用户的具体问题。
        }
    ],
    max_output_tokens=300,  # 限制本轮最多生成的输出 token 数。
)

print(response.output_text)  # 打印最终文本答案。
```

`instructions` 是当前请求顶层的系统/开发者指导。尤其在使用 `previous_response_id` 时，前一轮的顶层 `instructions` 不会自动继承，因此稳定规则应在每一轮重新发送。

## 2. 多轮对话：先选择状态策略

| 策略 | 适合什么情况 | 你需要保存什么 |
| --- | --- | --- |
| `previous_response_id` | 简单串行聊天，允许服务端保存 response | 最近一轮 response ID |
| 手动 history | 要裁剪、审计或自行托管上下文；`store=False` 场景 | 输入 item 与完整 `response.output` |
| `conversation` | 跨会话、跨设备或长期任务的持久会话 | Conversation ID |

### 2.1 用 `previous_response_id` 续接

这是聊天原型最短的写法。`store=True` 在此显式写出，便于读者看出它依赖服务端保存的 response；当前 API 的默认保存行为及保留规则仍须按项目合规要求复核。

```python
BASE_INSTRUCTIONS = "你是中文学习助手。每次先给结论，再给一个可验证的小例子。"  # 把每轮都要重发的稳定指导集中保存。

first = client.responses.create(  # 创建对话的第一轮 response。
    model=MODEL,  # 指定模型。
    instructions=BASE_INSTRUCTIONS,  # 发送第一轮的稳定行为指导。
    input="解释什么是闭包。",  # 发送第一轮用户问题。
    store=True,  # 显式允许服务端保存此 response，供下一轮引用。
)

follow_up = client.responses.create(  # 创建会引用上一轮上下文的第二轮 response。
    model=MODEL,  # 指定模型。
    instructions=BASE_INSTRUCTIONS,  # 必须重新发送稳定指导，因为它不会由 previous_response_id 自动继承。
    previous_response_id=first.id,  # 用第一轮 response ID 串联上下文。
    input="请把刚才的例子改成计数器。",  # 传入当前轮的新问题。
    store=True,  # 继续保存本轮 response，便于再续接下一轮。
)

print(follow_up.output_text)  # 输出带有前序语境的第二轮答案。
```

这会保留前序语境，但不意味着前序 token 不计费；链中既有输入仍会计入后续请求的 input tokens。需要截断、摘要或去除敏感内容时，优先使用手动 history。

### 2.2 手动维护 history（适合 `store=False`）

关键点是追加完整的 `response.output`，而不只是最后一段文本。这样 function call、推理 item 和 assistant message 都能以正确类型回放。

```python
history = [{"role": "user", "content": "讲一个关于递归的笑话。"}]  # 从第一条用户消息开始维护调用方自己的 history。

first = client.responses.create(  # 用当前 history 发起第一轮请求。
    model=MODEL,  # 指定模型。
    input=history,  # 把调用方维护的完整上下文传给模型。
    store=False,  # 禁止保存 Response 对象，改由调用方自行保存所需上下文。
)
print(first.output_text)  # 显示第一轮生成的笑话。

history += first.output  # 追加完整 typed output，而非只追加文本，以保留可续接的上下文。
history.append({"role": "user", "content": "解释笑点。"})  # 再追加第二轮用户消息。

second = client.responses.create(  # 将手动维护后的 history 发送给模型。
    model=MODEL,  # 指定模型。
    input=history,  # 传入第一轮输入、第一轮输出和第二轮用户问题。
    store=False,  # 继续采用调用方维护状态的方式。
)
print(second.output_text)  # 显示模型根据前序内容生成的解释。
```

`store=False` 只控制 Response 对象的存储，不应被表述为“整条业务链路没有任何数据保留”。应用日志、反向代理、数据库、文件存储与第三方工具仍需分别设计和审计。

## 3. 流式文本：只在完成事件后视为成功

设置 `stream=True` 后，SDK 返回可迭代的语义事件。前端可以在 `response.output_text.delta` 到来时渲染，但服务端应当等到 `response.completed` 才把该轮标记为完整；流中 `error`、`response.failed`、连接中断或缺少终态都不能当作成功。

```python
stream = client.responses.create(  # 发起返回语义事件流的 Responses 请求。
    model=MODEL,  # 指定模型。
    input="用通俗语言解释为什么 HTTP 请求需要超时。",  # 设置本轮待回答的问题。
    stream=True,  # 打开 SSE 流式模式；返回值会成为可迭代事件序列。
)

completed = False  # 先假定请求未完整结束，避免半截输出被误判为成功。

for event in stream:  # 逐个消费 SDK 解码后的流事件。
    # `response.output_text.delta` 表示：模型又生成了一小段新的文本。
    # `response.completed` 表示：整个 Response 已经完整完成。
    if event.type == "response.output_text.delta":  # 此事件携带一小段新增文本。
        print(event.delta, end="", flush=True)  # 立即显示增量文本，并强制刷新终端缓冲区。
    elif event.type == "response.completed":  # 只有此终态说明整轮 response 已完成。
        completed = True  # 记录已收到合法完成信号。
    elif event.type in {"response.failed", "error"}:  # 同时处理 response 失败和通用流错误。
        raise RuntimeError(f"响应流失败：{event}")  # 中止业务流程，避免继续使用不完整结果。

print()  # 在流式文本结束后补一个换行，保持终端输出整洁。
if not completed:  # 连接结束却没有终态时，仍必须判定为失败。
    raise RuntimeError("流在收到 response.completed 前结束，结果不可视为完整。")  # 明确拒绝半截结果。
```

函数参数也可能以增量事件到达。不要对半截 JSON 执行工具；应等待相应的 function-call 参数完成事件，并在下一节的正常工具循环中解析、校验、授权。

## 4. 结构化输出：让程序拿到对象，而不是猜 JSON

当你的程序需要固定字段（分类、表单、任务拆解）时，优先使用 Structured Outputs，而不是只在提示词里要求“请返回 JSON”。Pydantic helper 会把类型定义转成 schema，并把成功解析的结果放在输出内容的 `parsed` 字段。

```python
from typing import Literal  # 为 priority 字段声明有限的字符串集合。

from pydantic import BaseModel, Field  # 用 Pydantic 定义并校验结构化输出类型。


class SupportTicket(BaseModel):  # 定义应用希望模型返回的工单对象。
    title: str = Field(description="不超过 40 字的标题")  # 标题字段及其对模型的说明。
    priority: Literal["low", "medium", "high"]  # 仅允许三种优先级，避免任意字符串。
    summary: str  # 保存可供后续人工阅读的简短摘要。
    needs_human: bool  # 标识此工单是否应转交人工处理。


response = client.responses.parse(  # 请求 SDK 按 Pydantic 类型发送 schema 并解析成功结果。
    model=MODEL,  # 指定模型。
    instructions="从用户消息中提取工单；信息不足时如实说明，不要编造订单号。",  # 约束抽取时的真实性边界。
    input="我的订单两周没到，客服邮件也没有回复。",  # 放入待抽取的原始用户文本。
    text_format=SupportTicket,  # 指定最终输出必须匹配的 Pydantic 类型。
)

ticket = None  # 先保留空值，用于检测最终是否取得了可解析对象。
for output_item in response.output:  # 遍历每个 typed output item，而不假设它们的位置。
    if output_item.type != "message":  # 只在 message item 中查找最终结构化文本。
        continue  # 跳过工具调用等其他类型的 item。
    for content in output_item.content:  # 遍历 message 内的每个内容块。
        if content.type == "refusal":  # 安全拒绝不保证遵循目标 schema。
            raise RuntimeError(f"模型拒绝：{content.refusal}")  # 将拒绝交给上层 UI 或业务策略处理。
        if content.type == "output_text" and content.parsed is not None:  # 仅接受 SDK 已成功解析的文本块。
            ticket = content.parsed  # 取出 Pydantic SupportTicket 对象。

if ticket is None:  # 没有 parsed 对象时，不能把原始文本误作结构化数据使用。
    raise RuntimeError("没有得到可解析的结构化结果。")  # 让调用方显式处理不完整或异常结果。

print(ticket.model_dump())  # 转为普通字典后打印，便于查看字段值。
```

若 schema 由多个语言或服务共享，可直接使用 `text.format` 发送 JSON Schema：

```python
import json  # 用于把最终 JSON 文本解析为 Python 对象。

ticket_schema = {  # 定义可被多个服务或语言复用的 JSON Schema。
    "type": "object",  # 要求最终根节点是对象。
    "properties": {  # 列出对象允许的字段。
        "category": {"type": "string", "enum": ["billing", "shipping", "other"]},  # 限制分类只能取给定枚举值。
        "needs_human": {"type": "boolean"},  # 要求人工作转字段只能是布尔值。
    },
    "required": ["category", "needs_human"],  # 要求两个字段都必须出现。
    "additionalProperties": False,  # 拒绝 schema 中未定义的额外字段。
}

response = client.responses.create(  # 使用原始 JSON Schema 请求结构化输出。
    model=MODEL,  # 指定模型。
    instructions="输出与给定 JSON Schema 一致的 JSON。",  # 明确告诉模型最终内容应是 JSON。
    input="包裹显示已签收，但我没有收到。",  # 传入需要分类的用户描述。
    text={  # 配置 Responses API 最终文本的格式。
        "format": {  # 进入具体的格式约束对象。
            "type": "json_schema",  # 选择严格 JSON Schema 输出模式。
            "name": "ticket_routing",  # 给该 schema 一个便于审计和识别的名称。
            "strict": True,  # 要求模型严格遵循 schema 支持的约束。
            "schema": ticket_schema,  # 传入上面定义的 schema 内容。
        }
    },
)

data = json.loads(response.output_text)  # 将已完成的 JSON 文本转为 Python 字典。
print(data)  # 输出解析后的结构化结果。
```

Schema 合规不等于事实正确、业务逻辑正确或动作已获授权。仍要做领域校验，例如确认订单属于当前用户、金额范围合法，且写操作已获得明确确认。

## 5. Function calling：模型提议，应用执行

Function calling 的完整循环是：定义工具 → 模型返回一个或多个 `function_call` → 应用验证并执行 → 以同一个 `call_id` 回传 `function_call_output` → 再次请求模型。模型可能一次不调用、调用一个或调用多个工具，因此不要写成只处理第一项的 `if`。

```python
import json  # 用于解析模型返回的函数参数，并序列化工具执行结果。


TOOLS = [  # 声明本轮允许模型选择的全部自定义工具。
    {  # 开始定义 get_order_status 工具的完整合同。
        "type": "function",  # 指明这是 JSON Schema 定义的函数工具。
        "name": "get_order_status",  # 提供应用侧可路由的稳定工具名。
        "description": "按订单号查询订单状态；只能用于读取当前用户有权访问的订单。",  # 说明何时能用及权限边界。
        "parameters": {  # 定义模型可提交给函数的参数 schema。
            "type": "object",  # 要求参数整体是一个对象。
            "properties": {  # 声明可接受的参数字段。
                "order_id": {  # 定义订单号字段。
                    "type": "string",  # 要求订单号必须是字符串。
                    "description": "订单号，例如 ORD-2026-001",  # 向模型说明字段格式。
                }
            },
            "required": ["order_id"],  # 要求调用时一定提供订单号。
            "additionalProperties": False,  # 拒绝 schema 之外的多余参数。
        },
        "strict": True,  # 要求函数参数尽可能严格匹配 schema。
    }
]


def get_order_status(order_id: str) -> dict:  # 模拟一个只读的订单查询函数。
    # 真实项目：先从登录会话取得 user_id，再做权限检查，然后查询数据库。
    return {"order_id": order_id, "status": "shipping", "eta": "2026-07-25"}  # 返回可安全回传给模型的查询结果。


def call_tool(name: str, args: dict) -> dict:  # 将模型提出的工具名路由到受控的应用函数。
    if name == "get_order_status":  # 只允许调用已登记的读取工具。
        order_id = args.get("order_id")  # 从模型提供的 JSON 参数中读取订单号。
        if not isinstance(order_id, str) or not order_id.startswith("ORD-"):  # 再次在服务端校验类型和业务格式。
            raise ValueError("订单号格式不合法。")  # 参数异常时拒绝执行，而非依赖模型自行修正。
        return get_order_status(order_id)  # 通过了本地校验后才访问订单数据。
    raise ValueError(f"不允许调用未知工具：{name}")  # 阻止模型请求未显式开放的能力。


def parse_tool_arguments(raw_arguments: str) -> dict:  # 把模型返回的 JSON 参数限制为对象形状。
    arguments = json.loads(raw_arguments)  # 先按 JSON 语法解析原始参数字符串。
    if not isinstance(arguments, dict):  # 防止数组、字符串等值绕过后续的字段校验逻辑。
        raise ValueError("工具参数必须是 JSON 对象。")  # 参数合同不成立时停止执行该工具。
    return arguments  # 仅把受控的字典参数交给应用侧路由器。


MAX_TOOL_ROUNDS = 4  # 为单个用户请求设置连续工具回合上限，避免失控循环和费用扩张。


input_items = [  # 初始化将持续追加的 Responses input item 列表。
    {"role": "user", "content": "帮我查询订单 ORD-2026-001 的状态。"}  # 放入第一轮用户请求。
]

for _ in range(MAX_TOOL_ROUNDS):  # 在受限回合内处理模型可能提出的多轮工具调用。
    response = client.responses.create(  # 带着当前上下文和工具定义请求模型决定下一步。
        model=MODEL,  # 指定模型。
        instructions="需要订单状态时调用工具；不要编造工具查询结果。",  # 约束模型应以工具结果为准。
        input=input_items,  # 传入用户消息、先前 output 和已有工具结果。
        tools=TOOLS,  # 向模型公开本轮可用的函数工具。
    )

    function_calls = [  # 从所有 typed output item 中筛出本轮请求执行的函数调用。
        item for item in response.output if item.type == "function_call"  # 保留零个、一个或多个 function_call item。
    ]
    if not function_calls:  # 没有工具调用时，模型已经给出了最终文本回答。
        print(response.output_text)  # 输出最终的自然语言回答。
        break  # 退出工具循环。

    # 回传所有本轮 output，保留 function call 及可能出现的其他 typed item。
    input_items += response.output  # 追加本轮完整 output，确保 call_id 和其他上下文不丢失。

    for call in function_calls:  # 逐个处理模型本轮提出的所有函数调用。
        args = parse_tool_arguments(call.arguments)  # 只接受 JSON 对象，再交给服务端业务校验。
        result = call_tool(call.name, args)  # 在应用侧完成路由、权限校验和真实工具执行。
        input_items.append(  # 把每个工具结果作为新的 input item 回传给模型。
            {  # 开始构造与当前 call_id 关联的函数输出 item。
                "type": "function_call_output",  # 明确标识这是某个函数调用的输出。
                "call_id": call.call_id,  # 用原调用 ID 将结果准确关联到模型请求。
                "output": json.dumps(result, ensure_ascii=False, allow_nan=False),  # 将受控结果编码为标准 JSON，保留中文且拒绝非有限数值。
            }
        )
else:  # 到达上限仍有待处理调用时，不继续发送请求。
    raise RuntimeError(f"工具调用超过 {MAX_TOOL_ROUNDS} 轮上限，已停止执行。")  # 把受控失败交给上层记录、告警或引导用户重试。
```

`strict=True` 约束参数形状，不替代服务器端身份认证、参数语义校验、幂等、审计或高风险动作的人工确认。示例刻意把连续工具回合限制为四次；生产环境还应按请求设置总截止时间，并按工具设置调用次数、速率/成本阈值和幂等保护。对于退款、删除、发送邮件等写操作，应让工具本身执行最小权限与确认门槛，不能因为模型调用了函数就立即产生副作用。

## 6. Web search：获取最新信息并显示引用

新项目使用 `web_search`，不要继续使用遗留的 `web_search_preview`。`tool_choice="auto"` 允许模型自行决定是否搜索；需求明确要求查询时，可用 `"required"`。网页回答中的 `url_citation` 必须在面向用户的 UI 中清晰、可点击地展示。

```python
response = client.responses.create(  # 发起一轮必须使用网页检索工具的请求。
    model=MODEL,  # 指定模型。
    input="查找 OpenAI Responses API 的官方流式响应说明，给出两条要点和来源。",  # 明确检索目标和回答格式。
    tools=[  # 配置本轮可用的托管网页检索工具。
        {  # 开始定义网页检索工具的配置。
            "type": "web_search",  # 使用新项目应采用的网页检索工具类型。
            "search_context_size": "low",  # 为简单事实查询选择较小的检索上下文。
            "filters": {  # 限制允许搜索的站点范围。
                "allowed_domains": ["developers.openai.com"],  # 只允许官方开发者文档域名。
            },
        }
    ],
    tool_choice="required",  # 要求模型本轮实际执行网页检索，而非只凭既有知识回答。
    include=["web_search_call.action.sources"],  # 请求返回检索动作所用的完整来源列表。
)

print(response.output_text)  # 先显示模型汇总出的带内联引用的文本。

for output_item in response.output:  # 遍历所有输出 item，以便提取文本引用标注。
    if output_item.type != "message":  # 只在模型 message item 中查找最终文本。
        continue  # 跳过 web_search_call 等非文本 item。
    for content in output_item.content:  # 遍历 message 的内容块。
        if content.type != "output_text":  # 只处理输出文本块。
            continue  # 跳过拒绝或其他内容类型。
        for annotation in content.annotations:  # 逐个读取文本携带的标注。
            if annotation.type == "url_citation":  # 识别网页 URL 引用标注。
                print(f"- {annotation.title}: {annotation.url}")  # 输出可用于 UI 渲染的标题和链接。
```

域名过滤只写主机名，不写 `https://`；它适合缩小证据来源，并不替代你对结果质量的判断。默认允许实时联网；若业务只允许缓存/索引内容，可在工具对象中设定 `external_web_access=False`。需要读取所有被检索 URL 时可保留上例的 `include`，但要同时评估成本、延迟和日志中的外部内容暴露。

## 7. File search：让模型检索你的文档库

File search 是由 OpenAI 托管的内置工具：先上传文件并建立 vector store，等索引完成后，把 vector store ID 放到 `file_search` 工具中。模型决定调用后，平台会执行检索；应用不需要像 function calling 那样自行回传 tool output。

下面的初始化通常只做一次，应在业务数据库中保存 `vector_store.id`，避免每次提问重复上传和建库。

```python
from time import monotonic, sleep  # 用单调时钟限制等待窗口，并在轮询间隔内短暂等待。


POLL_INTERVAL_SECONDS = 1.0  # 控制查询索引状态的频率，避免无间隔轮询。
INDEX_TIMEOUT_SECONDS = 120  # 为这次初始化等待设置明确的最长时长。

with open("employee_handbook.pdf", "rb") as file_content:  # 以二进制方式打开待入库的本地 PDF。
    uploaded_file = client.files.create(  # 先把本地文件上传到 OpenAI Files API。
        file=file_content,  # 传入已打开的二进制文件对象。
        purpose="assistants",  # 声明该文件用于可检索的知识库场景。
    )

vector_store = client.vector_stores.create(name="employee_handbook")  # 创建承载该知识库的 vector store。
client.vector_stores.files.create(  # 将刚上传的文件关联并提交到 vector store 索引。
    vector_store_id=vector_store.id,  # 指定目标知识库 ID。
    file_id=uploaded_file.id,  # 指定要加入知识库的上传文件 ID。
)

# 只有完成索引后才能稳定地用于检索。
indexing_deadline = monotonic() + INDEX_TIMEOUT_SECONDS  # 记录本次轮询的单调时钟截止点。
while monotonic() < indexing_deadline:  # 仅在受限等待窗口内查询文件索引状态。
    indexed_file = client.vector_stores.files.retrieve(  # 读取当前文件关联对象的最新状态。
        vector_store_id=vector_store.id,  # 指定要查询的 vector store。
        file_id=uploaded_file.id,  # 指定刚上传并关联的文件。
    )
    if indexed_file.status == "completed":  # 只有完成索引后才允许进入查询阶段。
        break  # 结束轮询。
    if indexed_file.status in {"failed", "cancelled"}:  # 显式识别不可恢复的索引终态。
        raise RuntimeError(f"文件索引失败：{indexed_file.status}")  # 不把失败文件当作可检索资料。
    sleep(POLL_INTERVAL_SECONDS)  # 未完成时按固定间隔等待，避免无间隔轮询。
else:  # 截止时仍未获得完成或失败终态。
    raise TimeoutError(f"文件索引在 {INDEX_TIMEOUT_SECONDS} 秒内未完成。")  # 由上层记录状态并决定是否受控重试。

print("保存这个 ID 以供后续提问复用：", vector_store.id)  # 输出需持久化保存的知识库 ID。
```

超时只代表本次等待窗口耗尽，不等同于索引服务永久失败；应记录 `vector_store.id`、文件 ID 与最后状态，再由受控的重试任务或人工流程决定后续动作。提问时只需引用现有的 vector store：

```python
response = client.responses.create(  # 对已建好的知识库发起一次带 file_search 的问答请求。
    model=MODEL,  # 指定模型。
    instructions="只基于检索到的员工手册回答；未找到依据时明确说明。",  # 约束模型不以猜测替代文档证据。
    input="远程办公需要提前多久申请？",  # 传入用户关于手册的具体问题。
    tools=[  # 配置本轮可使用的托管文件检索工具。
        {  # 开始定义 file_search 工具的配置。
            "type": "file_search",  # 指定使用 vector store 的文件检索能力。
            "vector_store_ids": [vector_store.id],  # 将查询限定在前面创建的知识库中。
            "max_num_results": 5,  # 最多取回五条检索结果，平衡质量、成本和延迟。
        }
    ],
    include=["file_search_call.results"],  # 让响应额外包含原始检索结果，便于审计或调试。
)

print(response.output_text)  # 输出模型基于检索资料生成的答案。
```

最终文本会携带 `file_citation` 标注。向最终用户展示答案时也应把文件名/引用位置一并呈现；生产系统还应在上传前做租户隔离、文件授权、生命周期与删除策略。

## 8. 图像输入：URL、Data URL 或 file ID

图像可以使用公网 URL、Base64 Data URL 或 Files API 的 `file_id`。下例把本地文件转为 Data URL；`detail="low"` 适合快速、低成本的粗略理解，涉及小字、空间位置或复杂图表时要根据模型能力、成本和准确性选择 `high`、`original` 或自行预处理图片。

```python
import base64  # 用于把本地图片字节编码成 Base64 文本。
import mimetypes  # 用于根据文件名推断图片 MIME 类型。
from pathlib import Path  # 用面向对象的路径 API 读取本地图片。


def as_data_url(path: str) -> str:  # 将本地图片转成 Responses API 可接收的 Data URL。
    image_path = Path(path)  # 把字符串路径转换为 Path 对象。
    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"  # 推断 MIME 类型；未知时采用常见 JPEG 默认值。
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")  # 读取图片字节、Base64 编码并转为文本。
    return f"data:{mime_type};base64,{encoded}"  # 组装标准 data: URL 字符串。


response = client.responses.create(  # 发起一轮同时包含文字与图片的多模态请求。
    model=MODEL,  # 指定支持图像输入的模型。
    input=[  # 用用户消息 item 承载多个不同模态的内容块。
        {  # 开始定义包含文本与图片的一条用户消息。
            "role": "user",  # 指明这组内容来自用户。
            "content": [  # 以列表顺序发送文字指令和图片。
                {"type": "input_text", "text": "提取图片中的标题和三个主要要点。"},  # 告诉模型要对图片完成什么任务。
                {  # 开始定义图像内容块。
                    "type": "input_image",  # 指定此内容块是图像输入。
                    "image_url": as_data_url("report_screenshot.png"),  # 将本地截图转为 Data URL 后传入。
                    "detail": "low",  # 请求低细节视觉处理，以降低一般场景的成本和延迟。
                },
            ],
        }
    ],
)

print(response.output_text)  # 输出模型根据图像生成的文本结果。
```

图片也会消耗 input tokens。不要把验证码发给模型；医学影像、精确计数、复杂空间定位和低清晰度小字等任务存在已知局限，关键结论应加入专门的校验或人工复核。

## 9. 交付前检查：把“能跑”变成“可用”

- [ ] API key 只在服务端或受控运行环境中读取，没有进入浏览器、仓库或日志。
- [ ] 模型名从集中配置读取，并已用项目账户实际验证其可用性。
- [ ] 只在 `response.status` 完成、或流收到 `response.completed` 后将一轮标记为成功。
- [ ] 结构化输出同时处理 refusal、解析失败与领域语义校验。
- [ ] function call 的参数、身份、权限、幂等和高风险确认由业务代码把关。
- [ ] Web/file search 的引用在 UI 中可追溯；检索范围按租户和数据权限隔离。
- [ ] 按 [[LLM API集成/05-超时、错误、限流与重试|超时、错误、限流与重试]]设置超时、受限重试与限流，不把 SDK 默认行为和应用重试叠成无限重试。
- [ ] 记录 `response.id`、模型、提示版本、耗时、用量和受控的错误分类；不要记录不必要的原始敏感内容。参见 [[LLM API集成/06-用量、可观测性与供应商适配|用量、可观测性与供应商适配]]。

## 下一步

- 需要系统掌握工具的选择、参数、权限与多轮循环时，继续学习 [[Tool Calling（含 Function Calling）/00-目录|Tool Calling（含 Function Calling）]]。
- 需要把上述代码变成可靠 SDK adapter 时，完成本库的 [[LLM API集成/07-可靠客户端项目与自测|可靠客户端项目与自测]]，并将真实 API 调用与离线合同测试分开。
- 需要长期知识库时，再阅读 [[RAG/00-目录|RAG]]，不要只把 file search 当成全部检索系统设计。

## 参考资料

- [OpenAI：Responses API Reference](https://developers.openai.com/api/docs/api-reference/responses)（访问于 2026-07-22）
- [OpenAI：Migrate to the Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses)（`input`/`output`、`output_text`、状态策略，访问于 2026-07-22）
- [OpenAI：Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)（`previous_response_id`、手动 history、Conversations API 与保留边界，访问于 2026-07-22）
- [OpenAI：Streaming API responses](https://developers.openai.com/api/docs/guides/streaming-responses)（语义事件与终态，访问于 2026-07-22）
- [OpenAI：Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs)（Pydantic/Zod helper、`text.format` 与 refusal，访问于 2026-07-22）
- [OpenAI：Function calling](https://developers.openai.com/api/docs/guides/function-calling)（函数循环、`call_id` 与严格 schema，访问于 2026-07-22）
- [OpenAI：Web search](https://developers.openai.com/api/docs/guides/tools-web-search)（`web_search`、引用与域名过滤，访问于 2026-07-22）
- [OpenAI：File search](https://developers.openai.com/api/docs/guides/tools-file-search)（vector store、索引与文件引用，访问于 2026-07-22）
- [OpenAI：Images and vision](https://developers.openai.com/api/docs/guides/images-vision)（`input_image`、detail 与限制，访问于 2026-07-22）
