---
title: Graph API
aliases:
  - Graph API
source: https://docs.langchain.com/oss/python/langgraph/graph-api
source_md: https://docs.langchain.com/oss/python/langgraph/graph-api.md
source_url: https://docs.langchain.com/oss/python/langgraph/graph-api
retrieved: 2026-05-07
source_checked: 2026-07-20
content_origin: third-party
content_status: frozen-reference
attribution: LangChain project documentation contributors
local_changes: "Translation, formatting, links, and local code notes"
tags:
  - langchain
  - python
  - docs/learn
license: MIT
---

# Graph API

> [!quote] 冻结的第三方参考页
> 本页是 [LangGraph Graph API 官方文档](https://docs.langchain.com/oss/python/langgraph/graph-api)于 2026-05-07 获取版本的中文翻译与格式整理，并保留本地解释性注释和窄范围代码纠错，按上游文档仓库的 MIT License 保留。当前无法证明本地正文对应的精确 Git commit，代码签名与运行行为也未在本页重新执行；主线请结合 [[LangChain/00-初学者路线/06-LangGraph边界审批恢复与评测|LangGraph 边界、审批、恢复与评测]]和锁定版本的官方 Reference 使用。

## 图

LangGraph 的核心是将代理工作流建模为图。您可以使用三个关键组件来定义代理的行为：

1. [`State`](#state)：表示应用程序当前快照的共享数据结构。它可以是任何数据类型，但通常使用共享状态 schema 定义。

2. [`Nodes`](#nodes)：对代理逻辑进行编码的函数。它们接收当前状态作为输入，执行一些计算或副作用，并返回更新的状态。

3. [`Edges`](#edges)：根据当前状态确定接下来要执行哪个 `Node` 的函数。它们可以是条件分支或固定转换。

通过组合 `Nodes` 和 `Edges`，您可以创建复杂的循环工作流，随着时间的推移不断演变状态。然而，真正的力量来自 LangGraph 管理该状态的方式。

强调一下：`Nodes` 和 `Edges` 本质上只是函数——它们可以包含 LLM，也可以只是普通代码。

简而言之：*节点完成工作，边告诉下一步做什么*。

LangGraph 的底层图算法使用[消息传递](https://en.wikipedia.org/wiki/Message_passing)来定义通用程序。当节点完成其操作时，它会沿着一条或多条边向其他节点发送消息。然后，这些接收节点执行其功能，将结果消息传递给下一组节点，然后该过程继续。受 Google 的 [Pregel](https://research.google/pubs/pregel-a-system-for-large-scale-graph-processing/) 系统的启发，该程序以离散的“超级步骤”进行。

超级步骤可以被认为是图节点上的单次迭代。并行运行的节点是同一超级步骤的一部分，而顺序运行的节点则属于单独的超级步骤。在图执行开始时，所有节点都以 `inactive` 状态开始。当节点在其任何传入边（或“通道”）上接收到新消息（状态）时，该节点将变为 `active` 。然后，活动节点运行其功能并以更新进行响应。在每个超级步骤结束时，没有传入消息的节点通过将自己标记为 `inactive` 来投票给 `halt`。当所有节点均为 `inactive` 并且没有消息在传输时，图执行终止。

### 状态图

[`StateGraph`](https://reference.langchain.com/python/langgraph/graph/state/StateGraph) 类是要使用的主要图类。这是由用户定义的 `State` 对象参数化的。

### 编译图

要构建图，首先定义 [状态](#state)，然后添加 [节点](#nodes) 和 [边](#edges)，然后编译它。到底是什么在编译图以及为什么需要它？

编译是一个非常简单的步骤。它提供了对图结构的一些基本检查（没有孤立节点等）。您还可以在其中指定运行时参数，例如 [checkpointers](https://docs.langchain.com/oss/python/langgraph/persistence) 和断点。您只需调用 `.compile` 方法即可编译图：
```python
# compile 会把定义好的 graph/workflow 编译成可执行对象；这里也是接入 checkpointer、store 或 cache 的位置。
graph = graph_builder.compile(...)
```
> [!warning]
您**必须**先编译图，然后才能使用它。

## 状态

定义图时要做的第一件事是定义图的 `State`。`State` 由[图的 schema](#schema) 以及 [`reducer` 函数](#reducers) 组成，它们指定如何将更新应用于状态。`State` 的 schema 将是图中所有 `Nodes` 和 `Edges` 的输入 schema，并且可以是 `TypedDict` 或 `Pydantic` 模型。所有 `Nodes` 都会向 `State` 发出更新，然后使用指定的 `reducer` 函数应用这些更新。

### 模式

指定图 schema 的主要记录方法是使用 [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)。如果您想提供状态的默认值，请使用 [`dataclass`](https://docs.python.org/3/library/dataclasses.html)。如果您想要递归数据验证，我们还支持使用 Pydantic [`BaseModel`](https://docs.langchain.com/oss/python/langgraph/use-graph-api#use-pydantic-models-for-graph-state) 作为图状态（但请注意，Pydantic 的性能低于 `TypedDict` 或 `dataclass`）。

默认情况下，图将具有相同的输入和输出 schema。如果你想改变这一点，你也可以直接指定显式的输入和输出 schema。当您有很多键并且其中一些键明确用于输入而其他键明确用于输出时，这非常有用。请参阅[指南](https://docs.langchain.com/oss/python/langgraph/use-graph-api#define-input-and-output-schemas) 了解更多信息。

> [!info]
`langchain` 中的更高级别的 [`create_agent`](https://docs.langchain.com/oss/python/langchain/agents) 工厂不支持 Pydantic 状态 schema。

#### 多种模式

通常，所有图节点都与单个 schema 通信。这意味着它们将读取和写入相同的状态通道。但是，在某些情况下我们希望对此有更多的控制：

* 内部节点可以传递图的输入/输出中不需要的信息。
* 我们可能还想对图使用不同的输入/输出 schema。例如，输出可能仅包含单个相关输出键。

可以让节点写入图中的私有状态通道以进行内部节点通信。我们可以简单地定义一个私有 schema，`PrivateState`。

还可以为图定义显式的输入和输出 schema。在这些情况下，我们定义一个“内部” schema，其中包含与图操作相关的*所有*键。但是，我们还定义了 `input` 和 `output` schema，它们是“内部” schema 的子集，以约束图的输入和输出。有关更多详细信息，请参阅[定义输入和输出 schema](https://docs.langchain.com/oss/python/langgraph/use-graph-api#define-input-and-output-schemas)。

让我们看一个例子：
```python
# State schema 定义节点之间传递的数据结构；字段名会影响后续节点能读取和写入什么。
class InputState(TypedDict):
    user_input: str

class OutputState(TypedDict):
    graph_output: str

class OverallState(TypedDict):
    foo: str
    user_input: str
    graph_output: str

class PrivateState(TypedDict):
    bar: str

def node_1(state: InputState) -> OverallState:
    # 写入 OverallState：这个字段会进入图的全局 state。
    return {"foo": state["user_input"] + " name"}

def node_2(state: OverallState) -> PrivateState:
    # 从 OverallState 读取，并写入 PrivateState。
    return {"bar": state["foo"] + " is"}

def node_3(state: PrivateState) -> OutputState:
    # 从 PrivateState 读取，并写入 OutputState。
    return {"graph_output": state["bar"] + " Lance"}

# StateGraph 用来定义 LangGraph 工作流：node 负责计算，edge 负责控制执行顺序。
builder = StateGraph(OverallState,input_schema=InputState,output_schema=OutputState)
# add_node 注册一个 graph 节点；节点通常接收 state，并返回要写回 state 的局部更新。
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)
# add_edge 定义固定执行顺序，表示一个节点完成后继续运行下一个节点。
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", "node_3")
builder.add_edge("node_3", END)

# compile 会把定义好的 graph/workflow 编译成可执行对象；这里也是接入 checkpointer、store 或 cache 的位置。
graph = builder.compile()
graph.invoke({"user_input":"My"})
# 示例输出：{'graph_output': 'My name is Lance'}。
```
这里有两个微妙而重要的点需要注意：

1. 我们将 `state: InputState` 作为输入 schema 传递给 `node_1`。但是，我们写入 `foo`，即 `OverallState` 中的一个通道。我们如何写入不包含在输入 schema 中的状态通道？这是因为节点*可以写入图状态中的任何状态通道。*图状态是初始化时定义的状态通道的并集，其中包括 `OverallState` 以及过滤器 `InputState` 和 `OutputState`。

2. 我们用以下方法初始化图：
```python
# StateGraph 用来定义 LangGraph 工作流：node 负责计算，edge 负责控制执行顺序。
StateGraph(
    OverallState,
    input_schema=InputState,
    output_schema=OutputState
)
```
我们如何在 `node_2` 中写入 `PrivateState` ？如果没有在 `StateGraph` 初始化中传递，图如何访问此模式？

我们可以这样做，因为只要状态 schema 定义存在，`_nodes` 也可以声明附加状态 `channels_`。在本例中，定义了 `PrivateState` schema，因此我们可以将 `bar` 添加为图中的新状态通道并写入它。

### Reducers

reducer 是理解节点更新如何应用于 `State` 的关键。`State` 中的每个键都有自己独立的 reducer 函数。如果没有显式指定 reducer 函数，则假定对该键的所有更新都应覆盖它。reducer 有几种不同类型，先从默认 reducer 开始：

#### 默认 reducer

这两个示例展示了如何使用默认的 reducer：
```python
from typing_extensions import TypedDict

# State schema 定义节点之间传递的数据结构；字段名会影响后续节点能读取和写入什么。
class State(TypedDict):
    foo: int
    bar: list[str]
```
在此示例中，没有为任何键指定 reducer 函数。我们假设图的输入是：

`{"foo": 1, "bar": ["hi"]}`。然后我们假设第一个 `Node` 返回 `{"foo": 2}`。这被视为对状态的更新。请注意，`Node` 不需要返回整个 `State` schema - 只需要更新即可。应用此更新后，`State` 将变为 `{"foo": 2, "bar": ["hi"]}`。如果第二个节点返回 `{"bar": ["bye"]}` 那么 `State` 将是 `{"foo": 2, "bar": ["bye"]}`
```python
from typing import Annotated
from typing_extensions import TypedDict
from operator import add

# State schema 定义节点之间传递的数据结构；字段名会影响后续节点能读取和写入什么。
class State(TypedDict):
    foo: int
    bar: Annotated[list[str], add]
```
在此示例中，我们使用 `Annotated` 类型为第二个键 (`bar`) 指定 reducer 函数 (`operator.add`)。请注意，第一个键保持不变。我们假设图的输入是 `{"foo": 1, "bar": ["hi"]}`。然后我们假设第一个 `Node` 返回 `{"foo": 2}`。这被视为对状态的更新。请注意，`Node` 不需要返回整个 `State` schema - 只需要更新即可。应用此更新后，`State` 将变为 `{"foo": 2, "bar": ["hi"]}`。如果第二个节点返回 `{"bar": ["bye"]}`，则 `State` 将是 `{"foo": 2, "bar": ["hi", "bye"]}`。请注意，此处 `bar` 键是通过将两个列表添加在一起来更新的。

#### 覆盖

> [!tip]
在某些情况下，您可能希望绕过 reducer 并直接覆盖状态值。LangGraph 为此提供了 [`Overwrite`](https://reference.langchain.com/python/langgraph/types/) 类型。[在此处了解如何使用 `Overwrite`](https://docs.langchain.com/oss/python/langgraph/use-graph-api#bypass-reducers-with-overwrite)。

### 在图状态下处理消息

#### 为什么要使用消息？

大多数现代 LLM 提供商都有聊天模型接口，接受消息列表作为输入。LangChain 的[聊天模型接口](https://docs.langchain.com/oss/python/langchain/models)同样接受消息对象列表作为输入。这些消息有多种形式，例如 [`HumanMessage`](https://reference.langchain.com/python/langchain-core/messages/human/HumanMessage)（用户输入）或 [`AIMessage`](https://reference.langchain.com/python/langchain-core/messages/ai/AIMessage)（LLM 响应）。

要了解有关消息对象的更多信息，请参阅[消息概念指南](https://docs.langchain.com/oss/python/langchain/messages)。

#### 在图中使用消息

在许多情况下，将先前的对话历史记录存储为图状态中的消息列表会很有帮助。为此，我们可以向图状态添加一个键（通道）来存储 `Message` 对象列表，并使用 reducer 函数对其进行注释（请参阅下面示例中的 `messages` 键）。reducer 函数用于告诉图在每次状态更新时（例如节点发送更新时）如何更新状态中的 `Message` 对象列表。如果不指定 reducer，每次状态更新都会用最近提供的值覆盖消息列表。如果您只想把消息追加到现有列表，可以使用 `operator.add` 作为 reducer。

但是，您可能还想手动更新图状态中的消息（例如人在回路）。如果您要使用 `operator.add`，您发送到图的手动状态更新将附加到现有消息列表中，而不是更新现有消息。为了避免这种情况，您需要一个可以跟踪消息 ID 并覆盖现有消息（如果更新）的 reducer。为此，您可以使用预构建的 [`add_messages`](https://reference.langchain.com/python/langgraph/graph/message/add_messages) 函数。对于全新的消息，它只会附加到现有列表，但它也会正确处理现有消息的更新。

#### 序列化

除了跟踪消息 ID 之外，每当 `messages` 通道上收到状态更新时，[`add_messages`](https://reference.langchain.com/python/langgraph/graph/message/add_messages) 函数还会尝试将消息反序列化为 LangChain `Message` 对象。

更多信息请参见[LangChain序列化/反序列化](https://python.langchain.com/docs/how_to/serialization/)。这允许以以下格式发送图输入/状态更新：
```python
# 这种写法是支持的。
{"messages": [HumanMessage(content="message")]}

# 这种写法同样是支持的。
{"messages": [{"type": "human", "content": "message"}]}
```
由于使用 [`add_messages`](https://reference.langchain.com/python/langgraph/graph/message/add_messages) 时状态更新总是反序列化为 LangChain `Messages`，因此您应该使用点表示法来访问消息属性，例如 `state["messages"][-1].content`。

下面是使用 [`add_messages`](https://reference.langchain.com/python/langgraph/graph/message/add_messages) 作为其归约函数的图示例。
```python
from langchain.messages import AnyMessage
# add_messages 是 messages 字段常用的 reducer，作用是追加新消息而不是覆盖整段历史。
from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict

# State schema 定义节点之间传递的数据结构；字段名会影响后续节点能读取和写入什么。
class GraphState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
```
#### 消息状态

由于在您的状态中拥有消息列表非常常见，因此存在一个名为 `MessagesState` 的预构建状态，这使得使用消息变得很容易。 `MessagesState` 使用单个 `messages` 键定义，该键是 `AnyMessage` 对象的列表，并使用 [`add_messages`](https://reference.langchain.com/python/langgraph/graph/message/add_messages) 缩减器。通常，要跟踪的状态不仅仅是消息，因此我们看到人们对此状态进行子类化并添加更多字段，例如：
```python
from langgraph.graph import MessagesState

class State(MessagesState):
    documents: list[str]
```
## 节点

在 LangGraph 中，节点是接受以下参数的 Python 函数（同步或异步）：

1. `state`—图的[状态](#state)
2. `config` - [`RunnableConfig`](https://reference.langchain.com/python/langchain-core/runnables/config/RunnableConfig) 对象，包含 `thread_id` 等配置信息和 `tags` 等跟踪信息
3. `runtime` - 一个 `Runtime` 对象，包含 [运行时 `context`](#runtime-context) 和其他信息，如 `store`、`stream_writer`、`execution_info`、`server_info`、`heartbeat`（用于空闲超时刷新）和 `control`（用于 [正常关闭](https://docs.langchain.com/oss/python/langgraph/durable-execution#graceful-shutdown)）

与 `NetworkX` 类似，您可以使用 [`add_node`](https://reference.langchain.com/python/langgraph/graph/state/StateGraph/add_node) 方法将这些节点添加到图中：
```python
from dataclasses import dataclass
from typing_extensions import TypedDict

from langgraph.graph import StateGraph
from langgraph.runtime import Runtime

# State schema 定义节点之间传递的数据结构；字段名会影响后续节点能读取和写入什么。
class State(TypedDict):
    input: str
    results: str

@dataclass
class Context:
    user_id: str

# StateGraph 用来定义 LangGraph 工作流：node 负责计算，edge 负责控制执行顺序。
builder = StateGraph(State)

def plain_node(state: State):
    return state

# Runtime/context 用来传入运行时配置，例如用户信息或 thread_id；它通常不应该写进持久化 state。
def node_with_runtime(state: State, runtime: Runtime[Context]):
    print("In node: ", runtime.context.user_id)
    return {"results": f"Hello, {state['input']}!"}

def node_with_execution_info(state: State, runtime: Runtime):
    print("In node with thread_id: ", runtime.execution_info.thread_id)  # [!code highlight]
    return {"results": f"Hello, {state['input']}!"}

# add_node 注册一个 graph 节点；节点通常接收 state，并返回要写回 state 的局部更新。
builder.add_node("plain_node", plain_node)
builder.add_node("node_with_runtime", node_with_runtime)
builder.add_node("node_with_execution_info", node_with_execution_info)
...
```
在幕后，函数被转换为 [`RunnableLambda`](https://reference.langchain.com/python/langchain-core/runnables/base/RunnableLambda)，这为您的函数添加了批处理和异步支持，以及 [本机跟踪和调试](https://docs.langchain.com/langsmith/home)。

如果将节点添加到图中而不指定名称，则会为其指定一个与函数名称等效的默认名称。
```python
# add_node 注册一个 graph 节点；节点通常接收 state，并返回要写回 state 的局部更新。
builder.add_node(my_node)
# 之后可以用 `"my_node"` 这个名称为该节点创建入边或出边。
```
### `START` 节点

[`START`](https://reference.langchain.com/python/langgraph/constants/START) 节点是一个特殊节点，表示将用户输入发送到图的节点。引用该节点的主要目的是确定应该首先调用哪些节点。
```python
from langgraph.graph import START

# add_edge 定义固定执行顺序，表示一个节点完成后继续运行下一个节点。
graph.add_edge(START, "node_a")
```
### `END` 节点

`END` 节点是代表终端节点的特殊节点。当您想要指示哪些边完成后没有任何操作时，将引用此节点。
```python
from langgraph.graph import END

# add_edge 定义固定执行顺序，表示一个节点完成后继续运行下一个节点。
graph.add_edge("node_a", END)
```
### 节点缓存

LangGraph 支持根据节点的输入来缓存任务/节点。使用缓存：

* 编译图时指定缓存（或指定入口点）
* 指定节点的缓存策略。每个缓存策略支持：
  * `key_func` 用于根据节点的输入生成缓存键，默认为 pickle 输入的 `hash` 。
  * `ttl`，缓存的生存时间（以秒为单位）。如果不指定，缓存将永远不会过期。

例如：
```python
import time
from typing_extensions import TypedDict
from langgraph.graph import StateGraph
from langgraph.cache.memory import InMemoryCache
from langgraph.types import CachePolicy

# State schema 定义节点之间传递的数据结构；字段名会影响后续节点能读取和写入什么。
class State(TypedDict):
    x: int
    result: int

# StateGraph 用来定义 LangGraph 工作流：node 负责计算，edge 负责控制执行顺序。
builder = StateGraph(State)

def expensive_node(state: State) -> dict[str, int]:
    # 模拟耗时计算：用于展示 cache 命中前后的区别。
    time.sleep(2)
    return {"result": state["x"] * 2}

# add_node 注册一个 graph 节点；节点通常接收 state，并返回要写回 state 的局部更新。
builder.add_node("expensive_node", expensive_node, cache_policy=CachePolicy(ttl=3))
builder.set_entry_point("expensive_node")
builder.set_finish_point("expensive_node")

# compile 会把定义好的 graph/workflow 编译成可执行对象；这里也是接入 checkpointer、store 或 cache 的位置。
graph = builder.compile(cache=InMemoryCache())

# 这里是实际运行入口：传入 messages 或 state 后，系统会执行推理、工具调用和状态更新。
print(graph.invoke({"x": 5}, stream_mode='updates'))    # [!code highlight]
# 示例输出：第一次执行会真正运行 expensive_node。
print(graph.invoke({"x": 5}, stream_mode='updates'))    # [!code highlight]
# 示例输出：第二次执行命中 cache，metadata 会标记 cached=True。
```
1. 第一次运行需要两秒钟才能运行（由于模拟的昂贵计算）。
2. 第二次运行利用缓存并快速返回。

## 边

边定义逻辑如何路由以及图如何决定停止。这是代理如何工作以及不同节点如何相互通信的重要组成部分。有几种关键的边类型：

* 普通边：直接从一个节点到下一个节点。
* 条件边：调用函数来确定下一个要转到的节点。
* 入口点：当用户输入到达时首先调用哪个节点。
* 条件入口点：调用函数来确定当用户输入到达时首先调用哪个节点。

一个节点可以有多个出边。如果一个节点有多个传出边，则所有这些目标节点将作为下一个超级步骤的一部分并行执行。

> [!warning]
对于每个节点，选择一种路由机制：使用普通边进行静态路由，或使用条件边 / [`Command`](https://reference.langchain.com/python/langgraph/types/Command) 进行动态路由。不要混合来自同一节点的普通边和动态路由，因为这两条路径都可以执行并使图行为更难以推理。

### 普通边

如果你**总是**想从节点A到节点B，你可以直接使用[`add_edge`](https://reference.langchain.com/python/langgraph/pregel/_draw/add_edge)方法。
```python
# add_edge 定义固定执行顺序，表示一个节点完成后继续运行下一个节点。
graph.add_edge("node_a", "node_b")
```
### 条件边

如果您想**可选地**路由到一条或多条边（或可选地终止），则可以使用 [`add_conditional_edges`](https://reference.langchain.com/python/langgraph/graph/state/StateGraph/add_conditional_edges) 方法。此方法接受节点的名称和在该节点执行后调用的“路由函数”：
```python
# conditional edge 会根据条件函数返回值动态选择下一步节点。
graph.add_conditional_edges("node_a", routing_function)
```
与节点类似，`routing_function` 接受图的当前 `state` 并返回一个值。

默认情况下，返回值 `routing_function` 用作将状态发送到下一个的节点（或节点列表）的名称。所有这些节点将作为下一个超级步骤的一部分并行运行。

您可以选择提供一个字典，将 `routing_function` 的输出映射到下一个节点的名称。
```python
# conditional edge 会根据条件函数返回值动态选择下一步节点。
graph.add_conditional_edges("node_a", routing_function, {True: "node_b", False: "node_c"})
```
> [!tip]
如果要将状态更新和路由合并到单个函数中，请使用 [`Command`](#command) 而不是条件边。

### 切入点

入口点是图启动时运行的第一个节点。您可以使用从虚拟 [`START`](https://reference.langchain.com/python/langgraph/constants/START) 节点到第一个要执行的节点的 [`add_edge`](https://reference.langchain.com/python/langgraph/pregel/_draw/add_edge) 方法来指定进入图的位置。
```python
from langgraph.graph import START

# add_edge 定义固定执行顺序，表示一个节点完成后继续运行下一个节点。
graph.add_edge(START, "node_a")
```
### 条件进入点

条件入口点可让您根据自定义逻辑从不同的节点开始。您可以使用虚拟 [`START`](https://reference.langchain.com/python/langgraph/constants/START) 节点中的 [`add_conditional_edges`](https://reference.langchain.com/python/langgraph/graph/state/StateGraph/add_conditional_edges) 来完成此操作。
```python
from langgraph.graph import START

# conditional edge 会根据条件函数返回值动态选择下一步节点。
graph.add_conditional_edges(START, routing_function)
```
您可以选择提供一个字典，将 `routing_function` 的输出映射到下一个节点的名称。
```python
# conditional edge 会根据条件函数返回值动态选择下一步节点。
graph.add_conditional_edges(START, routing_function, {True: "node_b", False: "node_c"})
```
## `Send`

默认情况下，`Nodes` 和 `Edges` 是提前定义的，并在相同的共享状态上运行。但是，在某些情况下，可能无法提前知道确切的边和/或您可能希望同时存在不同版本的 `State`。一个常见的例子是 [map-reduce](https://docs.langchain.com/oss/python/langgraph/use-graph-api#map-reduce-and-the-send-api) 设计模式。在此设计模式中，第一个节点可能会生成对象列表，并且您可能希望将一些其他节点应用于所有这些对象。对象的数量可能提前未知（意味着边的数量可能未知），并且下游 `Node` 的输入 `State` 应该不同（每个生成的对象一个）。

为了支持这种设计模式，LangGraph 支持从条件边返回 [`Send`](https://reference.langchain.com/python/langgraph/types/Send) 对象。 `Send` 有两个参数：第一个是节点的名称，第二个是传递给该节点的状态。
```python
from langgraph.types import Send

def continue_to_jokes(state: OverallState):
    # Send 用于创建并行分支，每个分支可以携带自己的局部 state。
    return [Send("generate_joke", {"subject": s}) for s in state['subjects']]

# conditional edge 会根据条件函数返回值动态选择下一步节点。
graph.add_conditional_edges("node_a", continue_to_jokes)
```
## `Command`

[`Command`](https://reference.langchain.com/python/langgraph/types/Command) 是用于控制图执行的通用原语。它接受四个参数：

* `update`：应用状态更新（类似于从节点返回更新）。
* `goto`：导航到特定节点（类似于[条件边](#conditional-edges)）。
* `graph`：从[子图](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)导航时定位父图。
* `resume`：提供一个值以在[中断](https://docs.langchain.com/oss/python/langgraph/interrupts)后恢复执行。

`Command` 在三种情况下使用：

* **[从节点返回](#return-from-nodes)**：使用 `update`、`goto` 和 `graph` 将状态更新与控制流结合起来。
* **[输入到`invoke`或`stream`](#input-to-invoke-or-stream)**：中断后使用`resume`继续执行。
* **[从工具返回](#return-from-tools)**：与从节点返回类似，结合了工具内部的状态更新和控制流。

### 从节点返回

#### `update` 和 `goto`

从节点函数返回 [`Command`](https://reference.langchain.com/python/langgraph/types/Command) 以更新状态并一步路由到下一个节点：
```python
def my_node(state: State) -> Command[Literal["my_other_node"]]:
    # Command 可以同时表达 state 更新和下一步跳转，适合工具返回后改变流程的场景。
    return Command(
        # state 更新：返回的字段会合并回图状态。
        update={"foo": "bar"},
        # 控制流：这里决定下一步跳转到哪个节点。
        goto="my_other_node"
    )
```
使用 [`Command`](https://reference.langchain.com/python/langgraph/types/Command) 您还可以实现动态控制流行为（与 [条件边](#conditional-edges) 相同）：
```python
def my_node(state: State) -> Command[Literal["my_other_node"]]:
    if state["foo"] == "bar":
        # Command 可以同时表达 state 更新和下一步跳转，适合工具返回后改变流程的场景。
        return Command(update={"foo": "baz"}, goto="my_other_node")
```
当您需要**同时**更新状态**和**路由到不同的节点时，请使用 [`Command`](https://reference.langchain.com/python/langgraph/types/Command)。如果您只需要路由而不更新状态，请使用 [条件边](#conditional-edges) 代替。

> [!note]
在节点函数中返回 [`Command`](https://reference.langchain.com/python/langgraph/types/Command) 时，必须添加返回类型注释以及节点路由到的节点名称列表，例如`Command[Literal["my_other_node"]]`。这对于图渲染是必要的，并告诉 LangGraph `my_node` 可以导航到 `my_other_node`。

> [!warning]
[`Command`](https://reference.langchain.com/python/langgraph/types/Command) 仅添加动态边 - 使用 `add_edge` / `addEdge` 定义的静态边仍然执行。例如，如果 `node_a` 返回 `Command(goto="my_other_node")` 并且您还有 `graph.add_edge("node_a", "node_b")`，则 `node_b` 和 `my_other_node` 都会运行。对于每个节点，使用 [`Command`](https://reference.langchain.com/python/langgraph/types/Command) 或静态边路由到下一个节点，而不是同时使用两者。

查看此[操作指南](https://docs.langchain.com/oss/python/langgraph/use-graph-api#combine-control-flow-and-state-updates-with-command)，了解如何使用 [`Command`](https://reference.langchain.com/python/langgraph/types/Command) 的端到端示例。

#### `graph`

如果您使用 [subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)，则可以通过在 [`Command`](https://reference.langchain.com/python/langgraph/types/Command) 中指定 `graph=Command.PARENT` 来从子图中的节点导航到父图中的不同节点：
```python
def my_node(state: State) -> Command[Literal["other_subgraph"]]:
    # Command 可以同时表达 state 更新和下一步跳转，适合工具返回后改变流程的场景。
    return Command(
        update={"foo": "bar"},
        goto="other_subgraph",  # 其中 `other_subgraph` 是父 graph 中的一个节点。
        graph=Command.PARENT
    )
```
> [!note]
将 `graph` 设置为 `Command.PARENT` 将导航到最近的父图。

当您将父图和子图 [状态 schema](#schema) 共享的键的更新从子图节点发送到父图节点时，您**必须**为要在父图状态中更新的键定义一个 [reducer](#reducers)。请参阅此[示例](https://docs.langchain.com/oss/python/langgraph/use-graph-api#navigate-to-a-node-in-a-parent-graph)。

这在实现[多代理切换](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)时特别有用。查看[导航到父图中的节点](https://docs.langchain.com/oss/python/langgraph/use-graph-api#navigate-to-a-node-in-a-parent-graph) 了解详细信息。

### 输入到 `invoke` 或 `stream`

> [!warning]
`Command(resume=...)` 是**唯一** `Command` 模式，旨在作为 `invoke()`/`stream()` 的输入。不要使用 `Command(update=...)` 作为输入来继续多轮对话 - 因为传递任何 `Command` 作为输入会从最新的检查点（即运行的最后一步，而不是 `__start__`）恢复，如果已经完成，图将显示为卡住。要在现有线程上继续对话，请传递一个简单的输入字典：
```python
# 错误示例：graph 会从最近的 checkpoint 恢复。
# 也就是从上次已运行的步骤继续，因此看起来像卡住。
graph.invoke(Command(update={  # [!code --]
    "messages": [{"role": "user", "content": "follow up"}]  # [!code --]
}), config)  # [!code --]

# 正确示例：传入普通 dict 会从 __start__ 重新开始。
graph.invoke( {  # [!code ++]
    "messages": [{"role": "user", "content": "follow up"}]  # [!code ++]
}, config)  # [!code ++]
```
#### `resume`

使用 `Command(resume=...)` 提供一个值并在 [中断](https://docs.langchain.com/oss/python/langgraph/interrupts) 后恢复图执行。传递给 `resume` 的值成为暂停节点内 `interrupt()` 调用的返回值：
```python
from langgraph.types import Command, interrupt

def human_review(state: State):
    # 暂停 graph，并等待外部传回一个值。
    answer = interrupt("Do you approve?")
    return {"messages": [{"role": "user", "content": answer}]}

# 第一次调用：执行到 interrupt 后暂停。
result = graph.invoke({"messages": [...]}, config)

# 带值恢复执行：interrupt() 调用会返回 "yes"。
result = graph.invoke(Command(resume="yes"), config)
```
查看[中断概念指南](https://docs.langchain.com/oss/python/langgraph/interrupts)，了解有关中断模式的完整详细信息，包括多个中断和验证循环。

### 从工具返回

您可以从工具返回 [`Command`](https://reference.langchain.com/python/langgraph/types/Command) 来更新图状态和控制流。使用 `update` 修改状态（例如，保存在对话期间查找的客户信息），并使用 `goto` 在工具完成后路由到特定节点。

> [!warning]
当在工具内部使用时，`goto` 添加动态边 - 调用该工具的节点上已定义的任何静态边仍将执行。对于每个节点，使用工具驱动的动态路由或静态边来路由到下一个节点，而不是同时使用两者。

详情请参阅[使用内部工具](https://docs.langchain.com/oss/python/langgraph/use-graph-api#use-inside-tools)。

## 图迁移

即使使用 checkpointer 来跟踪状态，LangGraph 也可以轻松处理图定义（节点、边和状态）的迁移。

* 对于图末尾的线程（即不中断），您可以更改图的整个拓扑（即所有节点和边、删除、添加、重命名等）
* 对于当前中断的线程，我们支持除重命名/删除节点之外的所有拓扑更改（因为该线程现在可能即将进入不再存在的节点）——如果这是一个阻碍因素，请联系我们，我们可以优先考虑解决方案。
* 对于修改状态，我们具有添加和删除键的完全向后和向前兼容性
* 重命名的状态键会丢失其在现有线程中保存的状态
* 其类型以不兼容方式更改的状态键目前可能会导致更改前状态线程出现问题——如果这是一个阻碍，请与我们联系，我们可以优先考虑解决方案。

## 运行时上下文

创建图时，您可以为传递给节点的运行时上下文指定 `context_schema`。这适合传递不属于图状态的依赖信息。例如，您可能想要传递模型名称或数据库连接等依赖项。
```python
@dataclass
class ContextSchema:
    llm_provider: str = "openai"

# StateGraph 用来定义 LangGraph 工作流：node 负责计算，edge 负责控制执行顺序。
graph = StateGraph(State, context_schema=ContextSchema)
```
然后，您可以使用 `invoke` 方法的 `context` 参数将此上下文传递到图中。
```python
# 这里是实际运行入口：传入 messages 或 state 后，系统会执行推理、工具调用和状态更新。
graph.invoke(inputs, context={"llm_provider": "anthropic"})
```
然后，您可以在节点或条件边内访问和使用此上下文：
```python
from langgraph.runtime import Runtime

# Runtime/context 用来传入运行时配置，例如用户信息或 thread_id；它通常不应该写进持久化 state。
def node_a(state: State, runtime: Runtime[ContextSchema]):
    llm = get_llm(runtime.context.llm_provider)
    # ...
```
有关配置的完整详细信息，请参阅[添加运行时配置](https://docs.langchain.com/oss/python/langgraph/use-graph-api#add-runtime-configuration)。

### 递归限制

递归限制设置图在单次执行期间可以执行的最大[超级步](#graphs) 数。一旦达到限制，LangGraph 将提高 `GraphRecursionError`。从版本 1.0.6 开始，默认递归限制设置为 1000 步。可以在运行时在任何图上设置递归限制，并通过配置字典传递给 `invoke`/`stream` 。重要的是，`recursion_limit` 是一个独立的 `config` 密钥，不应像所有其他用户定义的配置一样在 `configurable` 密钥内传递。请参阅下面的示例：
```python
# 这里是实际运行入口：传入 messages 或 state 后，系统会执行推理、工具调用和状态更新。
graph.invoke(inputs, config={"recursion_limit": 5}, context={"llm": "anthropic"})
```
请阅读 [递归限制](https://docs.langchain.com/oss/python/langgraph/graph-api#recursion-limit) 以了解有关递归限制如何工作的更多信息。

### 访问和处理递归计数器

当前步计数器可在任何节点内的 `config["metadata"]["langgraph_step"]` 中访问，从而允许在达到递归限制之前进行主动递归处理。这使您能够在图逻辑中实施优雅的降级策略。

#### 它是如何运作的

步数计数器存储在 `config["metadata"]["langgraph_step"]` 中。递归限制检查遵循以下逻辑：`step > stop` 其中 `stop = step + recursion_limit + 1`。当超出限制时，LangGraph 会引发 `GraphRecursionError`。

#### 访问当前计步器

您可以访问任何节点内的当前步计数器以监控执行进度。
```python
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph

def my_node(state: dict, config: RunnableConfig) -> dict:
    current_step = config["metadata"]["langgraph_step"]
    print(f"Currently on step: {current_step}")
    return state
```
#### 主动递归处理

LangGraph 提供了一个 `RemainingSteps` 托管值，用于跟踪在达到递归限制之前剩余的步数。这允许图内进行优雅的降级。
```python
from typing import Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.managed import RemainingSteps

# State schema 定义节点之间传递的数据结构；字段名会影响后续节点能读取和写入什么。
class State(TypedDict):
    messages: Annotated[list, lambda x, y: x + y]
    remaining_steps: RemainingSteps  # 托管值：用于追踪距离步数上限还剩多少步。

def reasoning_node(state: State) -> dict:
    # RemainingSteps 会由 LangGraph 自动填充。
    remaining = state["remaining_steps"]

    # 检查剩余步数是否过低，避免递归执行超过限制。
    if remaining <= 2:
        return {"messages": ["Approaching limit, wrapping up..."]}

    # 正常处理流程。
    return {"messages": ["thinking..."]}

def route_decision(state: State) -> Literal["reasoning_node", "fallback_node"]:
    """Route based on remaining steps"""
    if state["remaining_steps"] <= 2:
        return "fallback_node"
    return "reasoning_node"

def fallback_node(state: State) -> dict:
    """Handle cases where recursion limit is approaching"""
    return {"messages": ["Reached complexity limit, providing best effort answer"]}

# 构建 graph。
builder = StateGraph(State)
# add_node 注册一个 graph 节点；节点通常接收 state，并返回要写回 state 的局部更新。
builder.add_node("reasoning_node", reasoning_node)
builder.add_node("fallback_node", fallback_node)
# add_edge 定义固定执行顺序，表示一个节点完成后继续运行下一个节点。
builder.add_edge(START, "reasoning_node")
# conditional edge 会根据条件函数返回值动态选择下一步节点。
builder.add_conditional_edges("reasoning_node", route_decision)
builder.add_edge("fallback_node", END)

# compile 会把定义好的 graph/workflow 编译成可执行对象；这里也是接入 checkpointer、store 或 cache 的位置。
graph = builder.compile()

# RemainingSteps 可以配合任意 recursion_limit 使用。
result = graph.invoke({"messages": []}, {"recursion_limit": 10})
```
#### 主动与被动方法

处理递归限制有两种主要方法：主动式（在图内监控）和被动式（在外部捕获错误）。
```python
from typing import Annotated, Literal, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.managed import RemainingSteps
from langgraph.errors import GraphRecursionError

# State schema 定义节点之间传递的数据结构；字段名会影响后续节点能读取和写入什么。
class State(TypedDict):
    messages: Annotated[list, lambda x, y: x + y]
    remaining_steps: RemainingSteps

# 主动处理方式（推荐）：使用 RemainingSteps 提前判断。
def agent_with_monitoring(state: State) -> dict:
    """Proactively monitor and handle recursion within the graph"""
    remaining = state["remaining_steps"]

    # 提前识别特殊情况，并路由到内部处理逻辑。
    if remaining <= 2:
        return {
            "messages": ["Approaching limit, returning partial result"]
        }

    # 正常处理流程。
    return {"messages": [f"Processing... ({remaining} steps remaining)"]}

def route_decision(state: State) -> Literal["agent", END]:
    if state["remaining_steps"] <= 2:
        return END
    return "agent"

# 构建 graph。
builder = StateGraph(State)
# add_node 注册一个 graph 节点；节点通常接收 state，并返回要写回 state 的局部更新。
builder.add_node("agent", agent_with_monitoring)
# add_edge 定义固定执行顺序，表示一个节点完成后继续运行下一个节点。
builder.add_edge(START, "agent")
# conditional edge 会根据条件函数返回值动态选择下一步节点。
builder.add_conditional_edges("agent", route_decision)
# compile 会把定义好的 graph/workflow 编译成可执行对象；这里也是接入 checkpointer、store 或 cache 的位置。
graph = builder.compile()

# 主动方式：graph 可以优雅结束。
result = graph.invoke({"messages": []}, {"recursion_limit": 10})

# 被动兜底方式：在外部捕获错误。
try:
    result = graph.invoke({"messages": []}, {"recursion_limit": 10})
except GraphRecursionError as e:
    # graph 执行失败后，在外部进行兜底处理。
    result = {"messages": ["Fallback: recursion limit exceeded"]}
```
这些方法之间的主要区别是：

| 方法 | 检测 | 处理 | 控制流程 |
| ----------------------------------------- | -------------------- | ------------------------------------ | ---------------------------------- |
| 主动（使用 `RemainingSteps`） | 达到限制之前 | 通过条件路由的内部图 | 图继续完成节点 |
| 反应式（捕获 `GraphRecursionError`） | 超过限制后 | try/catch 中的外部图 | 图执行终止 |

**主动优势：**

* 图内的优雅降级
* 可以在检查点保存中间状态
* 部分结果带来更好的用户体验
* 图正常完成（无异常）

**反应式优势：**

* 更简单的实施
* 无需修改图逻辑
* 集中错误处理

#### 其他可用的元数据

除了 `langgraph_step` 之外，`config["metadata"]` 中还提供以下元数据：
```python
def inspect_metadata(state: dict, config: RunnableConfig) -> dict:
    metadata = config["metadata"]

    print(f"Step: {metadata['langgraph_step']}")
    print(f"Node: {metadata['langgraph_node']}")
    print(f"Triggers: {metadata['langgraph_triggers']}")
    print(f"Path: {metadata['langgraph_path']}")
    print(f"Checkpoint NS: {metadata['langgraph_checkpoint_ns']}")

    return state
```
## 可视化

能够可视化图通常是件好事，尤其是当它们变得更加复杂时。 LangGraph 附带了几种内置的图可视化方法。有关详细信息，请参阅[可视化图](https://docs.langchain.com/oss/python/langgraph/use-graph-api#visualize-your-graph)。

## 可观察性和追踪

要跟踪、调试和评估您的代理，请使用 [LangSmith](https://docs.langchain.com/langsmith/home)。

## 了解更多

* [如何使用Graph API](https://docs.langchain.com/oss/python/langgraph/use-graph-api)
* [[07-Functional API|函数式 API 概念概述]]
* [Graph API 和 Function API 之间的选择](https://docs.langchain.com/oss/python/langgraph/choosing-apis)
