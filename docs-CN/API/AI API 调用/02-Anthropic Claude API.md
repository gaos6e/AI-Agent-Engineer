---
title: "Anthropic Claude API 调用"
source: https://platform.claude.com/docs/en/claude_api_primer
source_checked: 2026-07-22
source_baseline:
  - Anthropic API usage primer、Python SDK、Messages tool handling、Model IDs and
    versioning
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "已核对当前 Messages 主入口、模型 ID 语义与离线语法；未使用真实凭据执行网络调用"
tags:
  - API
  - AI-API
  - Anthropic
  - Claude
  - Python
aliases:
  - Claude API
  - Anthropic API
lang: zh-CN
translation_key: API/AI API 调用/02-Anthropic Claude API.md
translation_route: en/api/ai-api-reference/anthropic-claude-api
translation_default_route: zh-CN/API/AI-API-调用/02-Anthropic-Claude-API
---

# Anthropic Claude API 调用

> [!source] 官方来源
> 基于 [API usage primer](https://platform.claude.com/docs/en/claude_api_primer)、[Python SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python)、[Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls) 与 Messages API 文档整理。Claude 的主入口是 `Messages API`，Python 包名为 `anthropic`。

## 常用入口

| Python 方法 | 用途 |
| --- | --- |
| `client.messages.create()` | 单轮、多轮、图片和工具调用 |
| `client.messages.stream()` | 流式输出并可汇总最终消息 |
| `client.messages.count_tokens()` | 请求前估算输入 token |
| `client.models.list()` | 查看可用模型 |
| `client.beta.files.upload()` | 上传可复用文件；属于 beta 能力，按官方文档核对后再用 |

示例使用 `claude-sonnet-5`。它适合作为通用学习模型，但上线前仍应查看 [Models overview](https://platform.claude.com/docs/en/about-claude/models/overview)。

> [!note] 4.6 代及以后，dateless 并不等于“永远最新”
> 2026-07-22 的 Anthropic 模型版本文档说明，4.6 代及以后如 `claude-sonnet-5` 的无日期 ID 是该发布的 canonical pinned snapshot，而不是自动转向下一代的 evergreen alias。升级应显式改 ID、记录其退役计划并重跑自己的工具/结构化输出/安全回归；不要把名称里没有日期误读为无需版本治理。

## 安装与设置 API Key

```powershell
python -m pip install --upgrade anthropic  # 安装或更新当前虚拟环境中的 Anthropic 官方 Python SDK。
$env:ANTHROPIC_API_KEY = Read-Host 'ANTHROPIC_API_KEY' -MaskInput  # 仅在当前 PowerShell 进程以遮罩方式读取 Key，不把凭据写入脚本。
```

## 1. 最小文本调用

```python
from anthropic import Anthropic  # 导入同步客户端类。

client = Anthropic()  # 从进程环境中的 ANTHROPIC_API_KEY 创建客户端；不要在代码中硬编码 Key。

message = client.messages.create(  # 调用无状态的 Messages API 创建一轮回复。
    model="claude-sonnet-5",  # 选择本课示例模型；上线前以官方模型页核对可用性。
    max_tokens=1024,  # 显式限定本轮最多生成的 token 数。
    system="你是一个简洁、准确的中文技术老师。",  # 将本课模型的系统指令作为顶层参数传入。
    messages=[  # 按时间顺序传入本轮及历史对话消息。
        {"role": "user", "content": "用三点解释 API 调用。"},  # 当前用户问题。
    ],
)

print(message.content[0].text)  # 演示读取第一个文本块；混合内容响应应遍历全部 content。
print(message.usage)  # 输出服务实际统计的用量，供成本和上下文诊断使用。
```

> [!important]
> 对本课使用的 `claude-sonnet-5`，以及需要广泛模型兼容的默认实现，`system` 应作为顶层参数；`max_tokens` 需要显式设置。不要据此推出“Messages API 永远没有 system role”：Anthropic 当前只为部分已核验模型提供 mid-conversation system message，且有严格的位置约束。

如果响应可能包含工具调用等不同内容块，不要只假设 `content[0]` 一定是文本：

```python
for block in message.content:  # 遍历响应中的每个内容块，而非只假设第一个块是文本。
    if block.type == "text":  # 只对文本块读取 text 属性，跳过工具调用等其他类型。
        print(block.text)  # 输出这一段文本内容。
```

## 2. 多轮对话

Messages API 本身无状态，需要把历史消息重新传入：

```python
history = [  # 保存完整历史；Messages API 不会替客户端自动记忆上一轮。
    {"role": "user", "content": "Python 的列表是什么？"},  # 第一轮用户提问。
    {"role": "assistant", "content": "列表是可变、有序的容器。"},  # 第一轮助手回答。
    {"role": "user", "content": "给我一个追加元素的例子。"},  # 第二轮用户在前文基础上追问。
]

message = client.messages.create(  # 将完整历史作为一次新请求发送给 API。
    model="claude-sonnet-5",  # 选择本课示例模型。
    max_tokens=512,  # 为这轮回答设定较小的生成上限。
    messages=history,  # 传入按时间顺序排列的对话记录。
)

print(message.content[0].text)  # 输出本例预期的第一个文本内容块。
```

消息通常使用 `user` 与 `assistant` 两种角色，并按时间顺序排列。顶层 `system` 可用字符串或 text-block 数组。若确实需要在长会话中途更新系统指令，应先查 [Mid-conversation system messages](https://platform.claude.com/docs/en/build-with-claude/mid-conversation-system-messages)：截至 2026-07-19，官方列出的支持模型包括 Fable 5、Mythos 5 与 Opus 4.8，不包括 Sonnet 5；中途 system 也不能打断尚待客户端回传结果的 tool-use turn。生产 adapter 应按模型能力显式放行，不要仅凭 role 字段存在就发送。

## 3. 流式输出

```python
with client.messages.stream(  # 打开一个可逐事件消费的流式 Messages 请求。
    model="claude-sonnet-5",  # 选择流式请求的目标模型。
    max_tokens=1024,  # 限制本轮最多生成的 token 数。
    messages=[  # 提供本轮用户消息。
        {"role": "user", "content": "写一份 Python API 学习建议。"},  # 要求模型给出学习建议。
    ],
) as stream:  # 上下文管理器会在读取结束或异常时关闭流连接。
    for text in stream.text_stream:  # 使用 SDK 的文本便利迭代器逐段取得增量文本。
        print(text, end="", flush=True)  # 不换行地立即打印，模拟聊天界面的逐字显示。

    final_message = stream.get_final_message()  # 在流结束后取得 SDK 汇总的最终完整消息。

print("\nToken：", final_message.usage)  # 输出最终消息的用量，而不是猜测流中 token 数。
```

如果只想逐事件处理且不需要 SDK 汇总最终消息，可用 `client.messages.create(..., stream=True)`。`text_stream` 是文本便利接口；涉及工具、thinking 或流内错误时，应处理 typed event/content block 并核对最终 `stop_reason` 与 `message_stop`，不要把“出现过文本”当作一轮完整成功。

## 4. 图片理解

```python
import base64  # 导入 Base64 编码器，把本地图片字节包装成 API 可传输的文本。
from pathlib import Path  # 用 Path 表示本地图片路径。

image_path = Path(r"D:\data\chart.png")  # 替换成拥有上传权限的实际图片路径。
image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")  # 读取二进制图片并编码为 UTF-8 Base64 字符串。

message = client.messages.create(  # 发起包含图片和文本的多模态消息请求。
    model="claude-sonnet-5",  # 选择支持视觉输入的模型；运行前核对能力和限制。
    max_tokens=1024,  # 限制模型对图片分析的输出长度。
    messages=[  # 构造一条用户多模态消息。
        {  # 这一层表示单条消息对象。
            "role": "user",  # 指定消息来自用户。
            "content": [  # 使用内容块数组组合图片与文字指令。
                {  # 第一个内容块是图片。
                    "type": "image",  # 声明内容块类型为图片。
                    "source": {  # 描述图片数据的来源和格式。
                        "type": "base64",  # 表示 data 字段保存 Base64 编码内容。
                        "media_type": "image/png",  # 声明实际文件媒体类型，需与上传文件一致。
                        "data": image_data,  # 放入上一步编码得到的图片数据。
                    },
                },
                {"type": "text", "text": "解释图表趋势并提取坐标轴名称。"},  # 第二个内容块给出图片分析任务。
            ],
        }
    ],
)

print(message.content[0].text)  # 输出本例预期的文本分析结果；生产代码应处理所有内容块。
```

也可使用 URL 图片；具体支持格式、大小和图片数量限制应以 [Vision](https://platform.claude.com/docs/en/build-with-claude/vision) 为准。

## 5. 工具调用

```python
import json  # 使用标准库把本地工具结果序列化为稳定的 JSON 文本。


def get_weather(city: str) -> dict:  # 定义由宿主程序实际执行的示例工具。
    return {"city": city, "temperature": 25, "unit": "celsius"}  # 返回离线固定值，避免示例悄悄访问真实天气服务。


tools = [  # 向模型声明可选择的工具及其输入契约。
    {  # 定义一个函数工具的 schema。
        "name": "get_weather",  # 工具名必须与宿主允许执行的名称完全一致。
        "description": "查询指定城市的天气。",  # 告诉模型何时适合调用该工具。
        "input_schema": {  # 使用 JSON Schema 限制工具参数结构。
            "type": "object",  # 要求工具输入是一个对象。
            "properties": {"city": {"type": "string"}},  # 只定义 city 这个字符串参数。
            "required": ["city"],  # 要求模型调用时必须提供 city。
            "additionalProperties": False,  # 拒绝未声明字段，缩小可执行输入面。
        },
    }
]

messages = [{"role": "user", "content": "上海现在多少度？"}]  # 初始化会在工具轮次间持续累积的消息历史。

first = client.messages.create(  # 先让模型决定是否需要调用声明的工具。
    model="claude-sonnet-5",  # 使用本课示例模型。
    max_tokens=1024,  # 限制工具决策轮的输出长度。
    tools=tools,  # 将允许的工具 schema 发送给模型。
    messages=messages,  # 发送当前对话历史。
)

# 只有明确的 tool_use 终态才允许宿主执行；max_tokens、拒绝或其他终态
# 必须进入显式恢复路径，不能因为 content 中出现了 tool_use 就执行。
if first.stop_reason != "tool_use":  # 只在 API 明确结束于工具调用时允许宿主进入执行阶段。
    raise RuntimeError(f"tool turn is not executable: {first.stop_reason}")  # 其他终态必须走显式恢复逻辑。

messages.append({"role": "assistant", "content": first.content})  # 原样保留完整 assistant 内容，供下一轮模型关联上下文。
tool_results = []  # 收集每个 tool_use 对应的一条 tool_result。

for block in first.content:  # 遍历模型本轮返回的全部内容块。
    if block.type != "tool_use":  # 仅处理真正的本地工具调用块。
        continue  # 文本、thinking 等内容由原 assistant 消息保留，不在此执行。

    is_error = False  # 默认把本次工具执行视为成功，验证或执行失败时再标记。
    if block.name != "get_weather":  # 先做名称白名单校验，绝不按模型给出的任意名称调函数。
        result = {"error": "unsupported_tool"}  # 面向模型返回稳定、可处理的错误分类。
        is_error = True  # 标记该工具结果为失败。
    elif (  # 再验证输入对象的形状、字段和值域。
        not isinstance(block.input, dict)  # 参数必须已解析为字典。
        or set(block.input) != {"city"}  # 只能包含预期的 city 字段。
        or not isinstance(block.input["city"], str)  # city 必须是字符串。
        or not block.input["city"].strip()  # city 去除空白后不能为空。
        or len(block.input["city"]) > 100  # 限制长度，防止异常大或无意义输入。
    ):  # 上述任一项不满足时，都将这次工具调用视为不可执行。
        result = {"error": "invalid_tool_input"}  # 向模型说明参数不符合本地执行契约。
        is_error = True  # 标记该工具结果为失败。
    else:
        try:  # 只有通过白名单和语义校验后才实际执行工具。
            result = get_weather(block.input["city"].strip())  # 传入清理过的城市名并取得离线工具结果。
        except Exception:  # 捕获工具内部异常，避免把原始堆栈或敏感细节暴露给模型。
            # 面向模型只返回稳定分类；内部日志另记异常细节并脱敏。
            result = {"error": "tool_execution_failed"}  # 用统一错误码通知模型本次工具未成功。
            is_error = True  # 标记该工具结果为失败。

    tool_result = {  # 构造与本次 tool_use 绑定的回传内容块。
        "type": "tool_result",  # 声明这是 API 要求的工具结果内容块。
        "tool_use_id": block.id,  # 精确关联模型发起的那一次工具调用。
        "content": json.dumps(result, ensure_ascii=False),  # 将本地结果编码为 JSON，同时保留中文字符。
    }
    if is_error:  # 若验证或执行失败，则按协议明确标记错误结果。
        tool_result["is_error"] = True  # 让模型能区分正常数据与失败分类。
    tool_results.append(tool_result)  # 将这一调用的结果加入批量回传列表。

if tool_results:  # 只有确实执行过工具时才追加结果并发起续接轮。
    messages.append({"role": "user", "content": tool_results})  # 以 user 消息回传所有结果，保持每个 ID 一一对应。
    final = client.messages.create(  # 让模型基于工具结果生成面向用户的最终回答。
        model="claude-sonnet-5",  # 使用与工具决策轮一致的模型。
        max_tokens=1024,  # 限制最终回答的生成长度。
        tools=tools,  # 继续提供同一工具契约，供模型保持协议一致。
        messages=messages,  # 传入 assistant tool_use 与对应 tool_result 在内的完整历史。
    )
    for block in final.content:  # 检查最终轮的每个输出内容块。
        if block.type == "text":  # 对正常文本回答进行展示。
            print(block.text)  # 输出模型给用户的文字说明。
        elif block.type == "tool_use":  # 本短示例不实现无限工具循环。
            raise RuntimeError("model requested another tool turn; loop with a bound")  # 生产实现应使用有轮数和预算上限的循环。
```

流程是：模型返回 `tool_use` → 宿主校验工具名、schema、语义、权限与审批 → Python 执行函数 → 以匹配 `tool_use_id` 的 `tool_result` 返回 → 模型生成最终回答。并行调用必须做到每个 `tool_use` 恰有一个结果；参数无效、未知工具或执行失败都应回传稳定的 `is_error=true` 结果，同时把内部异常细节留在受保护日志，不能伪装成成功文本。

上面的短示例只展示一轮，并对第二轮再次出现 `tool_use` 显式报错；生产循环应设置最大轮数、总 deadline、重复调用检测和审批状态，而不是无限递归。

流式工具还有三条容易漏掉的合同：

- `input_json_delta.partial_json` 只有在对应 content block 结束后才能作为完整对象解析；空分片和零参数工具本身不等于错误。
- 显式启用 fine-grained/eager tool input streaming 时，末尾可能得到不完整 JSON；此时只允许回传错误结果，不能执行部分参数。
- thinking、redacted thinking、签名、普通文本与 server-tool blocks 都属于完整 assistant content；续接时应按原顺序保留。`server_tool_use` 由 Anthropic 执行，不应改名后交给本地函数。

这些边界可在 [[LLM API集成/08-项目-三家Provider合同测试|三家 Provider 合同测试]] 的 Anthropic 状态机与负向测试中离线练习。

## 6. 预估输入 Token

```python
count = client.messages.count_tokens(  # 在正式生成前请求服务估算该输入会占用的 token。
    model="claude-sonnet-5",  # 估算时使用将要实际调用的模型。
    system="你是中文技术老师。",  # 将顶层系统指令一并计入输入。
    messages=[  # 将准备发送的用户消息一并传入。
        {"role": "user", "content": "详细解释 Python 装饰器。"},  # 待估算的用户问题。
    ],
)

print(count.input_tokens)  # 输出估算的输入 token 数，用于决定是否截断、分块或拒绝请求。
```

它适合在发送长文档或长对话前检查上下文规模，但实际计费仍以正式响应的 `usage` 为准。

## 7. 异步调用

```python
import asyncio  # 导入 Python 标准异步事件循环工具。
from anthropic import AsyncAnthropic  # 导入与 await 配合使用的异步客户端类。


async def main() -> None:  # 定义异步入口函数，方便在其中 await 网络调用。
    client = AsyncAnthropic()  # 从环境变量创建异步客户端，凭据仍不应硬编码。
    message = await client.messages.create(  # 等待异步 Messages API 请求完成。
        model="claude-sonnet-5",  # 选择本例使用的模型。
        max_tokens=512,  # 限制该轮回答的最大 token 数。
        messages=[{"role": "user", "content": "解释 async/await。"}],  # 提供本轮用户问题。
    )
    print(message.content[0].text)  # 输出第一个文本块；生产代码应兼容多种 content 类型。


asyncio.run(main())  # 在普通 Python 脚本中创建并运行事件循环直到 main 完成。
```

Web 服务或多个独立请求并发时再学习异步；单个脚本先用同步客户端更容易调试。

## 错误处理

```python
import anthropic  # 导入 SDK 异常类型，以便按失败类别处理远程调用。

try:  # 将一次 API 调用包在可分类处理的异常边界内。
    message = client.messages.create(  # 发起最小文本请求，用于演示错误处理结构。
        model="claude-sonnet-5",  # 选择运行前应确认仍可用的模型。
        max_tokens=512,  # 限制本轮输出上限。
        messages=[{"role": "user", "content": "你好"}],  # 提供简单用户输入。
    )
except anthropic.AuthenticationError:  # 认证或权限错误通常不能通过立即重试恢复。
    print("API Key 无效或权限不足。")  # 提醒检查凭据来源和项目权限，不输出 Key。
except anthropic.RateLimitError:  # 命中速率或配额限制时应受预算控制地退避。
    print("触发限流，请稍后重试。")  # 向交互用户给出可行动提示，不泄露请求正文。
except anthropic.APITimeoutError:  # SDK 在超时时间内未等到完成结果。
    print("请求超时。")  # 由业务层结合总 deadline 决定是否受控重试。
except anthropic.APIConnectionError:  # 网络连接建立或传输失败。
    print("网络连接失败。")  # 提示检查网络或服务可达性，不吞掉内部诊断日志。
except anthropic.APIStatusError as exc:  # 服务返回其他 HTTP 状态错误。
    print(exc.status_code, exc.request_id)  # 输出状态和诊断 ID，避免记录完整敏感请求正文。
```

## 常见易错点

- 在未核验模型能力与位置约束时把 `system` 放进 `messages`；本课的 Sonnet 5 示例应使用顶层参数。
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
- [Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)
- [Fine-grained tool streaming](https://platform.claude.com/docs/en/agents-and-tools/tool-use/fine-grained-tool-streaming)
- [Mid-conversation system messages](https://platform.claude.com/docs/en/build-with-claude/mid-conversation-system-messages)
- [Token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting)

返回 [[API/AI API 调用/00-目录|厂商 AI API 参考目录]]；通用 HTTP 契约与可靠性见 [[API/00-目录|API 学习目录]]。
