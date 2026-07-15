---
title: 上下文
aliases:
  - Context
  - 上下文
source: https://docs.langchain.com/oss/python/concepts/context
source_md: https://docs.langchain.com/oss/python/concepts/context.md
retrieved: 2026-05-07
tags:
  - langchain
  - python
  - docs/learn
license: MIT
---

# 上下文

**上下文工程**是构建动态系统的实践，以正确的格式提供正确的信息和工具，以便人工智能应用程序能够完成任务。上下文可以通过两个关键维度来表征：

1. 通过**可变性**：
   * **静态上下文**：在执行期间不会更改的不可变数据（例如，用户元数据、数据库连接、工具）
   * **动态上下文**：随着应用程序运行而演变的可变数据（例如，对话历史记录、中间结果、工具调用观察）
2. 按**生命周期**：
   * **运行时上下文**：数据范围仅限于单次运行或调用
   * **跨对话上下文**：在多个对话或会话中持续存在的数据

> [!tip]
运行时上下文是指本地上下文：代码运行所需的数据和依赖项。它**不**指的是：

  * LLM 上下文，即传递到 LLM 提示中的数据。
  * “上下文窗口”，即可以传递给 LLM 的最大令牌数。

运行时上下文是依赖注入的一种形式，可用于优化 LLM 上下文。它允许在运行时向您的工具和节点提供依赖项（例如数据库连接、用户 ID 或 API 客户端），而不是对它们进行硬编码。例如，您可以在运行时上下文中使用用户元数据来获取用户首选项并将其输入到上下文窗口中。

LangGraph提供了三种管理上下文的方法，结合了可变性和生命周期维度：

| 上下文类型 | 描述 | 可变性 | 寿命 | 接入方式 |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------ | ---------- | ------------------ | --------------------------------------- |
| [**静态运行时上下文**](#static-runtime-context) | 启动时传递的用户元数据、工具、数据库连接 | 静止的 | 单次运行 | `context` 参数到 `invoke`/`stream` |
| [**动态运行时上下文（状态）**](#dynamic-runtime-context) | 在单次运行期间演变的可变数据 | 动态的 | 单次运行 | LangGraph 状态对象 |
| [**动态交叉对话上下文（存储）**](#dynamic-cross-conversation-context) | 跨对话共享的持久数据 | 动态的 | 交叉对话 | LangGraph store |

## 静态运行时上下文

**静态运行时上下文**表示不可变的数据，例如用户元数据、工具和数据库连接，这些数据在运行开始时通过 `invoke`/`stream` 的 `context` 参数传递给应用程序。该数据在执行期间不会改变。
```python
@dataclass
class ContextSchema:
    user_name: str

# 这里是实际运行入口：传入 messages 或 state 后，系统会执行推理、工具调用和状态更新。
graph.invoke(
    {"messages": [{"role": "user", "content": "hi!"}]},
    context={"user_name": "John Smith"}  # [!code highlight]
)
```
#### 代理提示
```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest

@dataclass
class ContextSchema:
    user_name: str

# dynamic_prompt 会在每次模型调用前动态生成系统提示词，适合加入用户画像或当前步骤信息。
@dynamic_prompt  # [!code highlight]
def personalized_prompt(request: ModelRequest) -> str:  # [!code highlight]
    user_name = request.runtime.context.user_name
    return f"You are a helpful assistant. Address the user as {user_name}."

# create_agent 会把模型、tools、系统提示词和 middleware 组装成一个可运行的 agent。
agent = create_agent(
    model="claude-sonnet-4-6",
    tools=[get_weather],
    middleware=[personalized_prompt],
    context_schema=ContextSchema
)

# 这里是实际运行入口：传入 messages 或 state 后，系统会执行推理、工具调用和状态更新。
agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather in sf"}]},
    context=ContextSchema(user_name="John Smith")  # [!code highlight]
)
```
有关详细信息，请参阅[代理](https://docs.langchain.com/oss/python/langchain/agents)。

#### 工作流节点
```python
from langgraph.runtime import Runtime

# Runtime/context 用来传入运行时配置，例如用户信息或 thread_id；它通常不应该写进持久化 state。
def node(state: State, runtime: Runtime[ContextSchema]):  # [!code highlight]
    user_name = runtime.context.user_name
    ...
```
    * 有关详细信息，请参阅[Graph API](https://docs.langchain.com/oss/python/langgraph/use-graph-api#add-runtime-configuration)。

#### 在一个工具中
```python
from langchain.tools import tool, ToolRuntime

# 使用 @tool 可以把普通 Python 函数暴露给 agent，模型会根据函数名、参数和 docstring 判断何时调用。
@tool
def get_user_email(runtime: ToolRuntime[ContextSchema]) -> str:
    """Retrieve user information based on user ID."""
    # 模拟从数据库读取用户信息。
    email = get_user_email_from_db(runtime.context.user_name)  # [!code highlight]
    return email
```
详情请参见[工具调用指南](https://docs.langchain.com/oss/python/langchain/tools#context)。

> [!tip]
`Runtime` 对象可用于访问静态上下文和其他实用程序，例如活动存储和流编写器。
  有关详细信息，请参阅 [`Runtime`](https://reference.langchain.com/python/langgraph/runtime/Runtime) 文档。

## 动态运行时上下文

**动态运行时上下文**表示可以在单次运行期间演变的可变数据，并通过 LangGraph 状态对象进行管理。这包括对话历史记录、中间结果以及从工具或 LLM 输出得出的值。在 LangGraph 中，状态对象在运行期间充当[[04-Memory|短期记忆]]。

#### 在代理中
示例展示了如何将状态合并到代理**提示**中。

状态也可以通过代理的**工具**访问，它可以根据需要读取或更新状态。详情请参见[工具调用指南](https://docs.langchain.com/oss/python/langchain/tools#short-term-memory-state)。
```python
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain.agents import AgentState

# State schema 定义节点之间传递的数据结构；字段名会影响后续节点能读取和写入什么。
class CustomState(AgentState):  # [!code highlight]
    user_name: str

# dynamic_prompt 会在每次模型调用前动态生成系统提示词，适合加入用户画像或当前步骤信息。
@dynamic_prompt  # [!code highlight]
def personalized_prompt(request: ModelRequest) -> str:  # [!code highlight]
    user_name = request.state.get("user_name", "User")
    return f"You are a helpful assistant. User's name is {user_name}"

# create_agent 会把模型、tools、系统提示词和 middleware 组装成一个可运行的 agent。
agent = create_agent(
    model="claude-sonnet-4-6",
    tools=[...],
    state_schema=CustomState,  # [!code highlight]
    middleware=[personalized_prompt],  # [!code highlight]
)

# 这里是实际运行入口：传入 messages 或 state 后，系统会执行推理、工具调用和状态更新。
agent.invoke({
    "messages": "hi!",
    "user_name": "John Smith"
})
```
#### 在工作流中
```python
from typing_extensions import TypedDict
from langchain.messages import AnyMessage
from langgraph.graph import StateGraph

# State schema 定义节点之间传递的数据结构；字段名会影响后续节点能读取和写入什么。
class CustomState(TypedDict):  # [!code highlight]
    messages: list[AnyMessage]
    extra_field: int

def node(state: CustomState):  # [!code highlight]
    messages = state["messages"]
    ...
    return {  # [!code highlight]
        "extra_field": state["extra_field"] + 1  # [!code highlight]
    }

# StateGraph 用来定义 LangGraph 工作流：node 负责计算，edge 负责控制执行顺序。
builder = StateGraph(State)
# add_node 注册一个 graph 节点；节点通常接收 state，并返回要写回 state 的局部更新。
builder.add_node(node)
builder.set_entry_point("node")
# compile 会把定义好的 graph/workflow 编译成可执行对象；这里也是接入 checkpointer、store 或 cache 的位置。
graph = builder.compile()
```
> [!tip]
**启用记忆**
  有关如何启用记忆的更多详细信息，请参阅[记忆指南](https://docs.langchain.com/oss/python/langgraph/add-memory)。这是一个强大的功能，允许您在多次调用中保留代理的状态。否则，状态的范围仅限于单次运行。

## 动态交叉对话上下文

**动态交叉对话上下文**表示跨越多个对话或会话的持久、可变数据，并通过 LangGraph 存储进行管理。这包括用户 profile、偏好和历史交互。 LangGraph store 在多次运行中充当[长期记忆](https://docs.langchain.com/oss/python/concepts/memory#long-term-memory)。这可用于读取或更新持久事实（例如，用户 profile、偏好、先前的交互）。

## 了解更多

* [[04-Memory|记忆概念概述]]
* [LangChain 中的短期记忆](https://docs.langchain.com/oss/python/langchain/short-term-memory)
* [LangGraph 中的记忆](https://docs.langchain.com/oss/python/langgraph/add-memory)
