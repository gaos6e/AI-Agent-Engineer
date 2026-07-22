---
title: OpenAI API 调用
source: https://developers.openai.com/api/docs/quickstart
source_checked: 2026-07-20
source_baseline:
  - OpenAI Responses, Conversation state, Your data, Function calling and
    Streaming guides
  - openai-python v2.46.0 source and official examples
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "依据官方文档与 SDK 源码核对并做离线语法检查；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - OpenAI
  - Python
aliases:
  - OpenAI API
---

# OpenAI API 调用

> [!source] 官方来源
> 本笔记按 Windows + Python 整理，主线采用 [Developer quickstart](https://developers.openai.com/api/docs/quickstart) 推荐的 `Responses API`。Chat Completions 仍受支持，但 OpenAI 建议新项目优先使用 Responses；迁移边界见 [Migrate to the Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses)。示例模型使用 2026-07-20 的通用别名 `gpt-5.6`，当日解析到 GPT-5.6 Sol；别名和可用模型会变化，正式项目应查看 [Models](https://developers.openai.com/api/docs/models)、记录实测模型，并在升级前重跑自己的回归评测。

## 先认识常用入口

| Python 方法 | 用途 | 学习优先级 |
| --- | --- | --- |
| `client.responses.create()` | 文本、多模态、工具调用的统一入口 | 必学 |
| `client.responses.parse()` | 按 Pydantic 模型返回结构化数据 | 常用 |
| `client.files.create()` | 上传 PDF、文档、图片等文件 | 常用 |
| `client.embeddings.create()` | 生成向量，用于语义检索和 RAG | 常用 |
| `client.audio.transcriptions.create()` | 音频转文字 | 按需 |
| `client.images.generate()` | 直接使用 Images API 生成图片 | 按需 |
| `client.models.list()` | 查看当前项目可访问的模型 | 辅助 |

> [!tip] 学习顺序
> 先掌握文本生成、多轮对话和流式输出，再学习图片/文件、结构化输出与工具调用。Embedding、音频和图像生成可按项目需要补充。

## 安装与设置 API Key

```powershell
python -m pip install --upgrade openai  # 安装或更新当前虚拟环境中的官方 Python SDK。
$env:OPENAI_API_KEY = Read-Host 'OPENAI_API_KEY' -MaskInput  # 仅在当前 PowerShell 进程以遮罩方式读取 Key，不回显它。

try {  # 不论脚本成功或异常，finally 都会清理这次会话的敏感环境变量。
    python .\your_script.py  # 运行你自己的 SDK 示例脚本；替换为真实文件名。
} finally {  # finally 保证异常路径也不会保留当前进程的 Key。
    Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue  # 删除精确变量名；若不存在也不影响清理流程。
}  # 结束本次敏感环境变量的清理边界。
```

这里的 `your_script.py` 是你的脚本名。不要把 Key 写入笔记、源码、Notebook、日志或前端；临时环境变量也应在命令结束后清理。

## 1. 文本生成：`responses.create()`

```python
from openai import OpenAI  # 导入官方 SDK 的同步客户端类。

client = OpenAI()  # 从当前进程环境读取 OPENAI_API_KEY 并创建客户端；不要把 Key 传进源码。


def require_completed(response, *, context: str):  # 把 SDK 响应收窄为可提交的成功终态。
    if response.status != "completed":  # failed、incomplete 等状态都不能当成业务成功。
        raise RuntimeError(f"{context}未完整完成：status={response.status}")  # 将当前状态附入安全的诊断错误。
    for item in getattr(response, "output", ()) or ():  # 逐项检查输出，兼容 output 缺失或为 null 的异常形状。
        for content in getattr(item, "content", ()) or ():  # 一个 output item 可能含多个内容块。
            if getattr(content, "type", None) == "refusal":  # 即使同时有文本，出现拒答也不能直接提交。
                raise RuntimeError(f"{context}包含拒答，不能作为业务结果提交")  # 强制上层处理拒答，而不是只读 output_text。
    return response  # 交还已确认终态且未发现 refusal 的原始响应对象。


def require_text(response, *, context: str) -> str:  # 在合法完成的基础上取得非空聚合文本。
    require_completed(response, context=context)  # 先复用上面的终态与拒答检查。
    text = response.output_text  # 读取 SDK 提供的文本聚合便利属性。
    if not text:  # 没有文本时可能是工具路径、空结果或其他非文本输出。
        raise RuntimeError(f"{context}没有可提交的最终文本")  # 不让空字符串静默进入下游业务。
    return text  # 返回可供本例文本路径使用的最终文本。


response = client.responses.create(  # 通过 Responses API 发起一次文本生成请求。
    model="gpt-5.6",  # 使用本页核对时的教学模型别名；真实运行前应重新确认可用性。
    reasoning={"effort": "low"},  # 请求较低推理强度；允许值与支持情况依模型而变。
    instructions="你是一个简洁、准确的中文技术老师。",  # 提供本次请求的开发者级输出规则。
    input="用三点解释什么是 API 调用。",  # 传入最终用户问题。
    store=False,  # 显式选择不保存本次 Response application state；这不等于 ZDR。
)

text = require_text(response, context="文本响应")  # 只有完整、无拒答且有文本的响应才能通过此检查。
print(text)  # 输出最终文本；真实日志应先考虑其中是否含敏感内容。
print(response.usage)  # 查看 SDK 返回的用量对象，便于成本归因。
print(response._request_id)  # 输出供应商诊断 ID；它不是业务幂等键或用户身份。
```

后续示例复用 `require_completed()` 与 `require_text()`：前者先验证合法终态并逐项拒绝 `refusal`，后者再要求存在可提交文本。这样即使一个响应对象同时含有部分文本和拒答，也不会误把 `output_text` 当成业务成功结果。

常用参数：

| 参数 | 作用 |
| --- | --- |
| `model` | 选择模型 |
| `input` | 用户输入，可为字符串或结构化消息列表 |
| `instructions` | 当前请求的高优先级开发者指令 |
| `reasoning` | 推理强度等配置；可用值取决于模型 |
| `max_output_tokens` | 限制本次最多生成的 token |
| `tools` | 启用内置工具、MCP 或自定义函数 |
| `store` | 是否保存 Response application state；应按数据治理显式选择 |

> [!warning] 不要固定读取 `response.output[0]`
> `output` 中还可能出现推理项和工具调用项。`response.output_text` 只是聚合文本的便利属性；只有已经确认合法终态、没有待处理工具调用或拒绝，而且业务确实需要文本时，才把它作为最终结果提交。

## 2. 结构化消息与多轮对话

### 使用消息角色

```python
response = client.responses.create(  # 用结构化消息列表发起一次新的 Responses 请求。
    model="gpt-5.6",  # 使用运行前仍需确认的目标模型别名。
    store=False,  # 不让本例自动保留 Response application state。
    input=[  # 按顺序提供开发者规则和用户问题。
        {  # 第一条消息承载应用定义的输出规范。
            "role": "developer",  # developer 消息优先级高于 user 消息。
            "content": "回答时给出定义、例子和一个常见错误。",  # 约束本次答案的组织方式。
        },
        {  # 第二条消息代表最终用户输入。
            "role": "user",  # 明确此内容来自用户而非应用规则。
            "content": "解释 Python 虚拟环境。",  # 提出需要回答的问题。
        },
    ],
)

print(require_text(response, context="消息响应"))  # 先验证终态/拒答，再输出最终文本。
```

- `developer`：应用规则和输出要求，优先级高于用户消息。
- `user`：最终用户输入。
- `assistant`：模型之前的回答；手动维护历史时会用到。

### 使用 `previous_response_id` 继续对话

```python
first = client.responses.create(  # 创建会被下一轮引用的前序 Response。
    model="gpt-5.6",  # 选择本例的教学模型别名。
    input="我的项目使用 Python 和 FastAPI。",  # 提供需要在续接轮次中使用的上下文。
    store=True,  # 允许后续 previous_response_id 继续解析这条 Response。
)
require_completed(first, context="前序 Response")  # 前序对象异常或拒答时，不能继续构造对话链。

second = client.responses.create(  # 使用前序 ID 请求服务端续接对话状态。
    model="gpt-5.6",  # 延续时仍显式声明模型，避免隐式依赖旧配置。
    previous_response_id=first.id,  # 关联已完成且仍可解析的前序 Response。
    input="请基于刚才的信息给我一个目录结构。",  # 提供本轮新增的用户要求。
    store=False,  # 本例到此结束，不再为下一轮保存这次 Response。
)

print(require_text(second, context="续接响应"))  # 验证续接轮终态、拒答与文本后再显示结果。
```

> [!note]
> `instructions` 只作用于当前请求。继续对话时如果仍需要同一规则，应再次传入。

### 选择状态与存储方式

| 方式 | 适用场景 | 必须理解的边界 |
| --- | --- | --- |
| `store=False` + 应用手工历史 | 数据最小化、可移植上下文或获批的 ZDR 项目 | 应用要重放完整输入及需要保留的 output items；`store=False` 本身不等于 ZDR |
| `previous_response_id` | 短链式服务端续接 | 前序 Response 必须仍可解析；每轮重新声明 `instructions` 与 `store` |
| Conversations API | 跨会话、设备或任务保存长期状态 | Conversation items 不采用普通 Response 的同一 30 天生命周期；必须另设删除和保留策略 |

截至 2026-07-20，[数据控制文档](https://developers.openai.com/api/docs/guides/your-data#v1responses)说明 Responses 默认保存 application state 30 天；`store=False` 只改变这层状态保存，不自动获得 Zero Data Retention，也不等于关闭滥用监控日志。使用 `previous_response_id` 并不会免除历史输入 token 的计费。上传到 Files API 的对象也有独立生命周期，不能假设请求结束后自动删除。处理敏感数据前，应同时核对组织的数据保留资格、端点支持范围与本地合规要求。

## 3. 流式输出

流式输出适合聊天界面或长回答。它会在生成过程中持续返回事件：

```python
stream = client.responses.create(  # 请求 SDK 返回可逐事件迭代的流，而非一次性响应对象。
    model="gpt-5.6",  # 选择流式请求要使用的模型别名。
    input="写一段 200 字的 Python 学习建议。",  # 提供本轮生成任务。
    store=False,  # 不保存本轮 Response application state。
    stream=True,  # 打开流式事件模式。
)

fragments = []  # 只暂存文本 delta；在确认终态前它们都不是可提交结果。
terminal_event = None  # 记录是否收到合法的流终态事件。
refusal_seen = False  # 独立记录流中是否出现 refusal，避免被文本 delta 掩盖。

for event in stream:  # 按 SDK 实际到达顺序读取每一个流事件。
    if event.type == "response.output_text.delta":  # 只把文本增量作为临时预览内容。
        fragments.append(event.delta)  # 先缓存片段，终态确认后才可组合为可提交文本。
        # 这里只是临时预览，不应写入最终记录或触发下游动作。
        print(event.delta, end="", flush=True)  # 立即显示增量以改善交互体验，但不表示业务成功。
    elif event.type in {"response.refusal.delta", "response.refusal.done"}:  # 拒答事件可能与普通文本事件交错出现。
        refusal_seen = True  # 记录拒答，最终检查时会拒绝提交已有文本片段。
    elif event.type in {  # 只把明确列出的事件当作本例的可能终态。
        "response.completed",  # 表示服务端确认完整成功。
        "response.failed",  # 表示服务端确认失败。
        "response.incomplete",  # 表示响应未完整生成。
        "error",  # 表示顶层流错误。
    }:  # 只允许这组显式事件结束本轮流式状态机。
        terminal_event = event.type  # 保存终态种类，留给循环后的统一提交门检查。
        break  # 收到终态后不再继续消费本轮流。

if terminal_event != "response.completed" or refusal_seen:  # 没有 completed 或出现 refusal 时均不允许提交文本。
    raise RuntimeError(  # 用一个稳定异常把流状态交给上层失败处理。
        f"流没有合法完成：terminal={terminal_event}, refusal={refusal_seen}"  # 仅记录事件类型和布尔值，不记录内容。
    )

committed_text = "".join(fragments)  # 只有通过终态门后才把临时 delta 合成为业务文本。
print("\n\n生成完成；现在才可提交文本")  # 提醒读者预览输出与可提交结果的边界。
```

迭代器异常、顶层 `error`、`response.failed`、`response.incomplete`、拒绝和 EOF 未见合法 terminal 都必须让本轮失败；已显示的 delta 仍是 provisional。完整的跨 Provider 事件状态机与离线负向测试见 [[LLM API集成/04-结构化输出与流式响应|结构化输出与流式响应]]和[[LLM API集成/08-项目-三家Provider合同测试|三家 Provider 合同测试]]。

## 4. 分析图片

图片可以来自公开 URL、Base64 data URL 或已上传文件的 `file_id`：

```python
response = client.responses.create(  # 发送带图像输入的 Responses 请求。
    model="gpt-5.6",  # 选择支持该输入类型的模型；真实运行前核对模型能力。
    store=False,  # 不保存本例的 Response application state。
    input=[  # 用结构化内容列表同时传入文字任务和图片。
        {  # 构造一条 user 消息。
            "role": "user",  # 明确本轮多模态输入属于用户内容。
            "content": [  # 一条消息可包含多个输入内容块。
                {"type": "input_text", "text": "描述图片，并提取可见文字。"},  # 说明模型应如何处理紧随其后的图片。
                {  # 第二个内容块提供公开图片 URL。
                    "type": "input_image",  # 指定此内容是图像输入。
                    "image_url": "https://api.nga.gov/iiif/a2e6da57-3cd1-4235-b20e-95dcaefed6c8/full/!800,800/0/default.jpg",  # 真实项目需先校验 URL 来源、权限和数据边界。
                },
            ],
        }
    ],
)

print(require_text(response, context="图片分析"))  # 只有完成、无拒答且有文本时才显示图片分析结果。
```

读取本地图片时可先转为 Base64：

```python
import base64  # 导入 Base64 编码器，用于把本地二进制图片包装为 data URL。
from pathlib import Path  # 用 Path 安全表示本地图片文件路径。

image_path = Path(r"D:\data\chart.png")  # 替换为你有权读取且允许发送的本地图片路径。
image_base64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")  # 读取二进制后转为可嵌入 JSON 字符串的 Base64 文本。

response = client.responses.create(  # 将文字任务和 data URL 图片一起交给模型。
    model="gpt-5.6",  # 使用支持图像输入的目标模型。
    store=False,  # 明确不保存本轮 Response application state。
    input=[{  # 本例只包含一条 user 消息。
        "role": "user",  # 将图像分析任务标记为用户输入。
        "content": [  # 内容数组按顺序提供任务说明和图片数据。
            {"type": "input_text", "text": "解释这张图表的趋势。"},  # 要求模型给出图表趋势解释。
            {  # 构造 data URL 图像内容块。
                "type": "input_image",  # 声明该内容块是输入图片。
                "image_url": f"data:image/png;base64,{image_base64}",  # 将上面得到的 Base64 字符串嵌入 PNG data URL。
            },
        ],
    }],
)

print(require_text(response, context="本地图片分析"))  # 验证响应后再输出本地图片的分析文本。
```

## 5. 上传并分析文件

适合 PDF、DOCX、PPTX、TXT、代码文件和表格等。PDF 在支持视觉的模型上会同时提取文本和页面图像。

```python
from pathlib import Path  # 用 Path 表示待上传文件，避免手工拼接路径字符串。

file_path = Path(r"D:\data\paper.pdf")  # 替换为你有权上传、且符合数据治理规则的文件路径。

with file_path.open("rb") as file_handle:  # 以二进制只读方式打开本地文件，并在上传后自动关闭句柄。
    uploaded = client.files.create(  # 把文件发送到 Files API，得到可在后续输入中引用的 file ID。
        file=file_handle,  # 传入已打开的二进制文件句柄。
        purpose="user_data",  # 声明该文件用于用户数据输入用途。
        expires_after={"anchor": "created_at", "seconds": 86_400},  # 请求从创建时起 24 小时的服务端过期兜底。
    )

try:  # 不论分析成功或失败，finally 都会删除本次上传文件。
    response = client.responses.create(  # 用上传后得到的 file ID 发起文档分析请求。
        model="gpt-5.6",  # 选择支持文件输入的模型；运行前需核对能力与账户范围。
        store=False,  # 不保存本轮 Response application state。
        input=[{  # 用一条 user 消息同时提供文件和任务文本。
            "role": "user",  # 明确这是用户提交的文件分析任务。
            "content": [  # 文件块与文字块构成同一请求上下文。
                {"type": "input_file", "file_id": uploaded.id},  # 通过已上传资源 ID 引用文件，而不是重复传输内容。
                {"type": "input_text", "text": "总结文档，并列出三个关键结论。"},  # 说明希望从文件得到什么结果。
            ],
        }],
    )
    print(require_text(response, context="文件分析"))  # 只有通过统一终态检查后才显示文档分析文本。
# 即使网络、模型或本地代码失败，也必须收口远端临时资源生命周期。
finally:
    client.files.delete(uploaded.id)  # 请求删除刚上传的文件；生产系统还需处理崩溃后的补偿清理。
```

`expires_after` 是服务端兜底，`finally` 主动删除是本次任务的生命周期收口；生产系统还需要清理失败重试和进程崩溃遗留文件。单次分析少量文件可用 `input_file`；大量文件、重复检索或知识库场景应进一步学习 [File search](https://developers.openai.com/api/docs/guides/tools-file-search)。

## 6. 内置工具：Web Search

```python
response = client.responses.create(  # 发起允许模型使用内置 Web Search 工具的请求。
    model="gpt-5.6",  # 使用当前支持该工具的模型；能力随模型和账户变化。
    tools=[{"type": "web_search"}],  # 明确启用内置检索工具，而不是让模型自行访问任意 URL。
    input="查找今天与 Python 相关的重要官方更新，并附来源。",  # 给出需要时效性和来源的用户任务。
    store=False,  # 不保存本例 Response application state。
)

print(require_text(response, context="Web Search 响应"))  # 通过终态和拒答检查后再显示聚合文本。
```

工具结果不一定只有文本，因此调试时可以检查各输出项：

```python
for item in response.output:  # 遍历所有输出项，文本、工具项和其他项目都可能出现。
    print(item.type)  # 打印每项类型，帮助调试时避免只假设存在文本。
```

其他常见内置工具包括 `file_search`、`code_interpreter`、`image_generation` 和远程 MCP；不同模型与账户的可用范围可能不同。

## 7. 自定义函数调用

模型只负责决定“调用哪个函数、参数是什么”，真正执行函数的是你的 Python 程序。

```python
import json  # 使用标准 JSON 解析/序列化函数验证模型返回的函数参数。


def get_weather(city: str) -> dict:  # 定义一个只读教学工具，真实系统应替换为受控天气服务适配器。
    # 学习示例；真实项目应在这里调用天气 API。
    return {"city": city, "temperature": 25, "unit": "celsius"}  # 返回固定假数据，避免示例产生网络调用或副作用。


def reject_non_finite(value: str) -> None:  # 作为 json.loads 的钩子，拒绝 NaN/Infinity 等非标准常量。
    raise ValueError(f"JSON 中不允许非有限常量：{value}")  # 让参数验证在执行工具前失败关闭。


def parse_weather_arguments(raw: str) -> dict:  # 把模型给出的 JSON 字符串收窄为安全的天气工具参数。
    arguments = json.loads(raw, parse_constant=reject_non_finite)  # 解析 JSON，同时拒绝非有限数值常量。
    if not isinstance(arguments, dict) or set(arguments) != {"city"}:  # 只接受包含且仅包含 city 的 object。
        raise ValueError("参数必须且只能包含 city")  # 未知字段不能自动透传给工具。
    city = arguments["city"]  # 取出经过 exact-field 检查的城市值。
    if not isinstance(city, str) or not city.strip() or len(city) > 100:  # 验证字符串类型、非空性和长度上限。
        raise ValueError("city 必须是 1 到 100 个字符的非空字符串")  # 不把畸形输入交给实际 provider。
    return {"city": city.strip()}  # 规范化首尾空白后返回最小参数对象。


tools = [  # 声明模型可选择的函数 allowlist；没有出现在此列表的函数不能被模型调用。
    {  # 定义 get_weather 的名称、描述和 JSON Schema 参数契约。
        "type": "function",  # 告诉 Responses API 这是应用提供的函数工具。
        "name": "get_weather",  # 工具名必须与本地分发器允许的名称完全一致。
        "description": "查询指定城市的当前天气。",  # 提供给模型的用途说明，不是执行授权。
        "parameters": {  # 使用 JSON Schema 描述模型可生成的参数形状。
            "type": "object",  # 顶层参数必须是 object。
            "properties": {  # 列出可接受的字段。
                "city": {"type": "string", "description": "城市名"},  # city 是字符串城市名。
            },
            "required": ["city"],  # city 是调用此工具不可缺少的字段。
            "additionalProperties": False,  # 拒绝模型臆造的额外参数字段。
        },
        "strict": True,  # 请求严格结构化输出；它仍不能替代下面的业务校验与授权。
    }  # 结束 get_weather 的工具定义。
]

MAX_TOOL_ROUNDS = 4  # 设置单次任务允许的最大工具往返次数，防止模型循环调用。
seen_call_ids = set()  # 在本进程内记录已处理的 call_id；崩溃恢复需使用持久化 ledger。

response = client.responses.create(  # 首先让模型决定是否需要调用允许的天气工具。
    model="gpt-5.6",  # 选择本例的模型别名。
    tools=tools,  # 仅暴露上面定义的函数 allowlist。
    input="上海现在多少度？",  # 提供用户提出的天气问题。
    store=True,  # 后续用 previous_response_id 回传工具输出，需要前序 Response 可解析。
)

for _round in range(MAX_TOOL_ROUNDS):  # 对每个允许轮次重复“检查响应→执行安全工具→回传结果”。
    require_completed(response, context=f"工具轮次 {_round + 1}")  # 每轮先确认模型响应已完成且没有拒答。

    calls = [item for item in response.output if item.type == "function_call"]  # 只挑出模型请求由应用执行的函数调用项。
    if not calls:  # 没有函数调用说明模型已给出最终文本或其他非工具输出。
        print(require_text(response, context="工具调用最终响应"))  # 验证最终文本后显示给用户。
        break  # 正常完成工具循环。

    tool_outputs = []  # 收集每个已执行工具的结构化回传项。
    for item in calls:  # 逐项处理模型请求的函数调用，不能批量盲目执行。
        if item.name != "get_weather":  # 二次执行 allowlist 检查，避免模型或响应形状被篡改。
            raise ValueError(f"未知工具：{item.name}")  # 未知工具绝不因名字相似而执行。
        if item.call_id in seen_call_ids:  # 同一 call_id 重复出现可能导致重复副作用。
            raise RuntimeError(f"重复的 call_id：{item.call_id}")  # 本例在内存层拒绝重放。
        seen_call_ids.add(item.call_id)  # 在真正执行前占用 call_id，避免同轮重复处理。

        arguments = parse_weather_arguments(item.arguments)  # 将模型 JSON 参数通过严格本地验证。
        # get_weather 是只读示例；有副作用的工具还要先做身份、授权与审批。
        result = get_weather(**arguments)  # 仅在工具名和参数都通过检查后执行本地函数。
        tool_outputs.append({  # 将结果包装为 API 要求的函数输出项。
            "type": "function_call_output",  # 标识这是回传给模型的工具执行结果。
            "call_id": item.call_id,  # 用原 call_id 将结果绑定到对应模型调用。
            "output": json.dumps(result, ensure_ascii=False, allow_nan=False),  # 生成不含 NaN/Infinity 的严格 JSON 文本。
        })

    response = client.responses.create(  # 将所有已验证工具结果回传给同一对话链，要求模型继续。
        model="gpt-5.6",  # 再次显式指定目标模型。
        tools=tools,  # 保持同一 allowlist，避免续接轮扩大工具面。
        previous_response_id=response.id,  # 关联刚刚处理的前序 Response。
        input=tool_outputs,  # 传入本轮工具执行的结构化输出列表。
        store=True,  # 允许下一轮继续使用新的 Response ID。
    )
else:  # for 循环未通过 break 正常结束，说明模型超过安全轮数上限。
    raise RuntimeError("超过工具调用轮数上限")  # 终止任务而不是无限循环消耗工具预算。
```

> [!warning]
> 函数参数来自模型，`strict: True` 也不能替代业务校验、身份授权和审批。涉及删除、支付、发消息等副作用时，不要未经确认直接执行；SDK 自动重试、Provider `call_id` 和业务幂等键是三种不同机制。进程崩溃与不确定提交需要 durable operation/execution ledger，而不是只靠内存中的 `seen_call_ids`。完整的 SQLite ledger/outbox 实践见 [[Tool Calling（含 Function Calling）/08-项目-SQLite持久化幂等与Outbox恢复|SQLite 持久化幂等与 Outbox 恢复]]。

## 8. 结构化输出：`responses.parse()`

当程序需要稳定字段，而不是一段自然语言时，使用 Pydantic 模型：

```powershell
python -m pip install --upgrade pydantic  # 安装或更新当前虚拟环境的结构化输出模型库。
```

```python
from pydantic import BaseModel  # 导入 Pydantic 基类，用 Python 类型定义结构化输出 schema。


class StudyPlan(BaseModel):  # 定义本例期待模型返回的学习计划对象。
    topic: str  # 学习主题必须是文本字段。
    days: int  # 计划天数必须是整数。
    tasks: list[str]  # 每天/阶段任务以字符串列表表示。


response = client.responses.parse(  # 让 SDK 根据 Pydantic 模型请求并解析结构化文本输出。
    model="gpt-5.6",  # 使用支持结构化输出的目标模型。
    input="为 Python API 入门制定一个 7 天计划。",  # 描述需要生成的计划任务。
    text_format=StudyPlan,  # 将上面定义的 Pydantic 类型作为期望输出格式。
    store=False,  # 不保存本例 Response application state。
)

require_completed(response, context="结构化响应")  # 先确认响应已完成且没有 refusal。
plan = response.output_parsed  # 读取 SDK 提供的首个已解析结构化输出便利属性。
if plan is None:  # 终态成功并不自动保证一定存在一个可用 parsed 对象。
    raise RuntimeError("响应已完成且无拒答，但没有可用的结构化结果")  # 让上层处理缺失结构化结果。

print(plan.topic)  # 显示通过 Pydantic 验证的主题字段。
print(plan.tasks)  # 显示通过 Pydantic 验证的任务列表。
```

`output_parsed` 是 openai-python v2.46.0 仍提供的便利属性，适合预期只有一个结构化文本结果的路径；需要保留多个 message/content 或定位 refusal 时，应逐项检查 `output[*].content[*].parsed`。结构化输出适合写数据库、调用后续函数、生成配置或做数据抽取，但仍应先处理拒答、输出不完整、`None` 与校验失败。

## 9. Embedding：`embeddings.create()`

```python
response = client.embeddings.create(  # 调用 Embeddings API，把一批文本转换为数值向量。
    model="text-embedding-3-small",  # 指定入库和检索时必须保持一致的 embedding 模型。
    input=[  # 用列表一次提交两段待向量化文本；批量大小仍受模型限制。
        "Python 适合快速开发。",  # 第一条输入文本。
        "Rust 重视性能和内存安全。",  # 第二条输入文本。
    ],
)

vectors = [item.embedding for item in response.data]  # 按返回顺序取出每条文本对应的浮点向量。
print(len(vectors), len(vectors[0]))  # 检查获得的向量数量和单条向量维度。
```

Embedding 本身不会回答问题，它把文本变成向量，常用于语义搜索、聚类、推荐与 RAG。入库和查询必须使用同一模型与同一维度。

## 10. 音频转文字

```python
from pathlib import Path  # 用 Path 表示本地音频路径，避免手工拼接文件分隔符。

audio_path = Path(r"D:\data\meeting.mp3")  # 改为拥有上传授权的实际音频文件路径。

with audio_path.open("rb") as audio_file:  # 以二进制只读方式打开文件，并在结束后自动关闭句柄。
    transcription = client.audio.transcriptions.create(  # 提交音频文件并请求语音转写。
        model="gpt-4o-transcribe",  # 选择当前可用的转写模型；运行前核对模型和语言支持。
        file=audio_file,  # 将已打开的二进制文件对象作为 multipart 上传内容。
    )

print(transcription.text)  # 输出服务返回的纯文本转写结果。
```

实时麦克风转写或语音对话不走这个文件上传示例，应学习 Realtime API。

## 11. 生成图片

Responses API 可以把图像生成作为工具：

```python
import base64  # 导入 Base64 解码器，用于还原工具返回的图像字节。

response = client.responses.create(  # 请求模型调用内置图像生成工具。
    model="gpt-5.6",  # 选择支持该工具的模型；实际能力和名称需要以当前文档为准。
    input="生成一张极简风格的 Python API 学习路线图。",  # 用自然语言描述想生成的图像。
    tools=[{"type": "image_generation"}],  # 显式向模型开放图像生成工具。
    store=False,  # 不自动保留本例的 Response application state。
)

require_completed(response, context="图像生成")  # 在读取工具输出前确认响应已成功完成。
images = [item for item in response.output if item.type == "image_generation_call"]  # 筛选实际执行过图像生成的输出项。
if not images:  # 防止后续访问空列表而把“未生成图片”误判为其他错误。
    raise RuntimeError("响应已完成，但没有图像结果")  # 让调用方显式处理缺少图像结果的异常。

for index, item in enumerate(images, start=1):  # 为每张生成图编号，避免写文件时互相覆盖。
    image_bytes = base64.b64decode(item.result, validate=True)  # 严格解码 Base64，格式异常时立即报错。
    Path(f"api-roadmap-{index}.png").write_bytes(image_bytes)  # 将图像二进制保存到当前工作目录。
```

如果应用只需要图片生成与编辑，也可进一步学习 `client.images.generate()` 和 `client.images.edit()`。

## 错误处理与重试

```python
import openai  # 导入 SDK 异常类型，以便按可恢复性分类处理失败。

try:  # 将一次远程 API 调用及其响应校验放入可捕获的异常边界。
    response = client.responses.create(  # 发起一个最小文本请求，用于演示错误分类。
        model="gpt-5.6",  # 使用运行前应确认仍可用的模型别名。
        input="你好",  # 提供本次请求的简单用户输入。
        store=False,  # 不自动保留本例的 Response application state。
        timeout=60,  # 约束单次 SDK attempt 的超时秒数，而非整个业务流程期限。
    )
    require_completed(response, context="请求")  # 在把响应视为成功前检查完成状态。
    print("request_id:", response._request_id)  # 记录诊断关联 ID；不要把它当作业务幂等键。
except openai.AuthenticationError:  # 身份认证失败通常不能靠重试恢复。
    print("API Key 无效或没有权限。")  # 提示用户检查凭据来源和项目权限，不输出 Key。
except openai.RateLimitError:  # 限流或额度问题需要等待、退避或检查账户配额。
    print("触发限流或额度不足，请稍后重试并检查账户。")  # 面向交互用户给出可行动提示，不泄露请求正文。
except openai.APITimeoutError:  # 单次请求在 SDK 超时前未完成。
    print("请求超时。")  # 由业务层根据总 deadline 决定是否受控重试。
except openai.APIConnectionError:  # 无法与 API 建立或维持网络连接。
    print("网络连接失败。")  # 提示检查网络和服务可达性，不把底层异常细节直接暴露给用户。
except openai.APIStatusError as exc:  # 服务返回其他可解析的 HTTP 状态错误。
    print("API 错误：", exc.status_code, exc.request_id)  # 输出状态和诊断 ID，避免打印敏感正文。
```

生产代码可在客户端级设置超时与有限重试：

```python
client = OpenAI(timeout=60.0, max_retries=2)  # 为该客户端设置单次 attempt 超时及有限 SDK 级重试次数。
```

openai-python 当前默认就会对连接错误、408、409、429 与 5xx 自动重试两次，因此上面的 `max_retries=2` 是把默认值显式写入合同，不是新增一层重试。`timeout=60` 约束一次 SDK 请求/attempt，不是覆盖所有 attempts、排队和下游工作的业务总 deadline。生产系统应只选一个重试 owner：若由外层工作流统一管理预算，就把 SDK `max_retries` 设为 `0`；若交给 SDK，则外层不要再无界重试。对支付、写库等副作用，不要假设 Responses API 提供通用 exactly-once 或 HTTP 幂等合同，业务系统仍需自己的 operation key、ledger 与 outbox。

成功响应可记录 `_request_id`；API 状态错误使用异常上的 `request_id`。它们用于关联诊断，不是业务幂等键，也不应与用户输入、凭据或完整敏感正文一起无界记录。

## 常见错误

- `401`：API Key 错误、变量未在新终端生效或项目权限不足。
- `429`：触发速率限制，也可能是额度或账单问题。
- 模型不存在：当前项目无权访问，或模型名已变更；用模型页或 `client.models.list()` 核对。
- 把 ChatGPT 订阅当作 API 额度：ChatGPT 与 API 的计费和权限是分开的。
- 把 Key 写进 `.py`、Notebook 或 Git：应使用环境变量，发现泄露后立即撤销并重建。
- 流式输出只拼文本：工具调用和失败事件也需要单独处理。

> [!info] 本页验证边界
> 2026-07-20 已对 16 个 Python fenced block 运行 `ast.parse`，并以官方文档、openai-python v2.46.0 源码和官方示例核对主要方法形状；未使用真实 API Key、未发起网络请求、未产生费用。因此这里证明的是语法与文档合同，不证明你的账户权限、模型可用性、远程返回形状或端到端延迟。严格终态、重复 `call_id`、未知工具、非法 JSON 与多轮工具调用的离线合同测试由 [[LLM API集成/08-项目-三家Provider合同测试|三家 Provider 合同测试]]承担。

## 官方延伸阅读

- [Developer quickstart](https://developers.openai.com/api/docs/quickstart)
- [Migrate to the Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses)
- [Text generation](https://developers.openai.com/api/docs/guides/text)
- [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)
- [Your data / data controls](https://developers.openai.com/api/docs/guides/your-data)
- [Images and vision](https://developers.openai.com/api/docs/guides/images-vision)
- [File inputs](https://developers.openai.com/api/docs/guides/file-inputs)
- [Using tools](https://developers.openai.com/api/docs/guides/tools)
- [Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [Streaming API responses](https://developers.openai.com/api/docs/guides/streaming-responses)
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [openai-python retries and timeouts](https://github.com/openai/openai-python#retries)
- [openai-python v2.46.0 parsed Responses source](https://github.com/openai/openai-python/blob/v2.46.0/src/openai/types/responses/parsed_response.py)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
