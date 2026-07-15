---
title: Functional API
aliases:
  - Functional API
source: https://docs.langchain.com/oss/python/langgraph/functional-api
source_md: https://docs.langchain.com/oss/python/langgraph/functional-api.md
retrieved: 2026-05-07
tags:
  - langchain
  - python
  - docs/learn
license: MIT
---

# Functional API

**函数式 API** 允许您将 LangGraph 的关键功能（[持久性](https://docs.langchain.com/oss/python/langgraph/persistence)、[内存](https://docs.langchain.com/oss/python/langgraph/add-memory)、[人在回路](https://docs.langchain.com/oss/python/langgraph/interrupts) 和 [流](https://docs.langchain.com/oss/python/langgraph/streaming)）添加到您的应用程序中，只需对现有代码进行最少的更改。

它旨在将这些功能集成到现有代码中，这些代码可以使用标准语言原语进行分支和控制流，例如 `if` 语句、`for` 循环和函数调用。与许多需要将代码重组为显式管道或 DAG 的数据编排框架不同，函数式 API 允许您合并这些功能，而无需强制执行严格的执行模型。

函数式 API 使用两个关键构建块：

* **`@entrypoint`**：将函数标记为工作流的起点，封装逻辑并管理执行流，包括处理长时间运行的任务和中断。
* **[`@task`](https://reference.langchain.com/python/langgraph/func/task)**：表示可以在入口点内异步执行的离散工作单元，例如 API 调用或数据处理步骤。任务返回一个类似 future 的对象，可以同步等待或解析。

这为构建具有状态管理和流的工作流提供了最小的抽象。

> [!tip]
有关如何使用函数式 API 的信息，请参阅[使用函数式 API](https://docs.langchain.com/oss/python/langgraph/use-functional-api)。

## 函数式 API 与Graph API

对于喜欢更具声明性方法的用户，LangGraph 的 [[06-Graph API|Graph API]] 允许您使用 Graph 范式定义工作流。这两个 API 共享相同的底层运行时，因此您可以在同一应用程序中一起使用它们。

以下是一些主要区别：

* **控制流**：Functional API 不需要考虑图结构。您可以使用标准 Python 结构来定义工作流。这通常会减少您需要编写的代码量。
* **短期记忆**：**GraphAPI** 需要声明 [**State**](https://docs.langchain.com/oss/python/langgraph/graph-api#state)，并且可能需要定义 [**reducers**](https://docs.langchain.com/oss/python/langgraph/graph-api#reducers) 来管理图状态的更新。 `@entrypoint` 和 `@tasks` 不需要显式状态管理，因为它们的状态仅限于函数范围，并且不会在函数之间共享。
* **检查点**：两个 API 都会生成并使用检查点。在 **Graph API** 中，每个 [[06-Graph API|superstep]] 后都会生成一个新的检查点。在 **Functional API** 中，执行任务时，其结果将保存到与给定入口点关联的现有检查点，而不是创建新检查点。
* **可视化**：Graph API 可以轻松地将工作流可视化为图，这对于调试、理解工作流以及与他人共享非常有用。函数式 API 不支持可视化，因为图是在运行时动态生成的。

## 例子

下面我们演示一个简单的应用程序，它可以编写一篇文章并[中断](https://docs.langchain.com/oss/python/langgraph/interrupts) 来请求人工审核。
```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.func import entrypoint, task
from langgraph.types import interrupt

@task
def write_essay(topic: str) -> str:
    """Write an essay about the given topic."""
    time.sleep(1) # 长耗时任务的占位函数。
    return f"An essay about topic: {topic}"

# checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
@entrypoint(checkpointer=InMemorySaver())
def workflow(topic: str) -> dict:
    """A simple workflow that writes an essay and asks for a review."""
    essay = write_essay("cat").result()
    # interrupt 会暂停执行并把请求交给外部人类或 UI，之后用 Command(resume=...) 恢复。
    is_approved = interrupt({
        # interrupt 的参数可以是任意可 JSON 序列化的 payload。
        # 流式传输数据时，它会在客户端表现为一个 Interrupt。
        # 从 workflow 中返回。
        "essay": essay, # 需要用户审阅的文章。
        # 这里可以加入任何额外需要的信息。
        # 例如，添加一个名为 "action" 的键，并放入相关指令。
        "action": "Please approve/reject the essay",
    })

    return {
        "essay": essay, # 已经生成的文章。
        "is_approved": is_approved, # 来自 human-in-the-loop 的响应。
    }
```
### 详细说明
此工作流将写一篇有关“猫”主题的文章，然后暂停以获取人工审核意见。工作流可以无限期中断，直到提供审核。

当工作流恢复时，它会从头开始执行，但由于 `writeEssay` 任务的结果已经保存，因此任务结果将从检查点加载，而不是重新计算。
```python
import time
from langchain_core.utils.uuid import uuid7
from langgraph.func import entrypoint, task
from langgraph.types import interrupt
from langgraph.checkpoint.memory import InMemorySaver

@task
def write_essay(topic: str) -> str:
    """Write an essay about the given topic."""
    time.sleep(1)  # 这是长耗时任务的占位实现。
    return f"An essay about topic: {topic}"

# checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
@entrypoint(checkpointer=InMemorySaver())
def workflow(topic: str) -> dict:
    """A simple workflow that writes an essay and asks for a review."""
    essay = write_essay("cat").result()
    # interrupt 会暂停执行并把请求交给外部人类或 UI，之后用 Command(resume=...) 恢复。
    is_approved = interrupt(
        {
            # interrupt 的参数可以是任意可 JSON 序列化的 payload。
            # 流式传输数据时，它会在客户端表现为一个 Interrupt。
            # 从 workflow 中返回。
            "essay": essay,  # 需要用户审阅的文章。
            # 这里可以加入任何额外需要的信息。
            # 例如，添加一个名为 "action" 的键，并放入相关指令。
            "action": "Please approve/reject the essay",
        }
    )
    return {
        "essay": essay,  # 已经生成的文章。
        "is_approved": is_approved,  # 来自 human-in-the-loop 的响应。
    }

thread_id = str(uuid7())
config = {"configurable": {"thread_id": thread_id}}
for item in workflow.stream("cat", config):
    print(item)
# 示例输出：> {'write_essay': 'An essay about topic: cat'}
# > {
# 示例输出：>     '__interrupt__': (
# 示例输出：>        Interrupt(
# 示例输出：>            value={
# 示例输出：>                'essay': 'An essay about topic: cat',
# 示例输出：>                'action': 'Please approve/reject the essay'
# >            },
# 示例输出：>            id='b9b2b9d788f482663ced6dc755c9e981'
# >        ),
# >    )
# > }
```
一篇论文已经写好，准备供审阅。一旦提供审核，我们就可以恢复工作流：
```python
from langgraph.types import Command

# resume 值可以是任意可 JSON 序列化的数据，这里用 bool 做最简单的示例。
# 这里使用 bool 作为示例，但实际可以是任意可 JSON 序列化的值。
human_review = True

# Command 可以同时表达 state 更新和下一步跳转，适合工具返回后改变流程的场景。
for item in workflow.stream(Command(resume=human_review), config):
    print(item)
```

```pycon
{'workflow': {'essay': 'An essay about topic: cat', 'is_approved': False}}
```
工作流已完成，评论已添加到论文中。

## 入口点

[`@entrypoint`](https://reference.langchain.com/python/langgraph/func/entrypoint) 装饰器可用于从函数创建工作流。它封装工作流逻辑并管理执行流，包括处理*长时间运行的任务*和[中断](https://docs.langchain.com/oss/python/langgraph/interrupts)。

### 定义

**入口点**是通过使用 `@entrypoint` 装饰器装饰函数来定义的。

该函数**必须接受单个位置参数**，用作工作流输入。如果需要传递多条数据，请使用字典作为第一个参数的输入类型。

使用 `entrypoint` 修饰函数会生成一个 [`Pregel`](https://reference.langchain.com/python/langgraph/pregel/#langgraph.pregel.Pregel.stream) 实例，该实例有助于管理工作流的执行（例如，处理流式传输、恢复和检查点）。

您通常需要将 **checkpointer** 传递给 `@entrypoint` 装饰器以启用持久性并使用 **人在回路 ** 等功能。

#### 同步
```python
from langgraph.func import entrypoint

# checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
@entrypoint(checkpointer=checkpointer)
def my_workflow(some_input: dict) -> int:
    # 这里可能包含 API 调用等耗时逻辑。
    # 并且可能为了 human-in-the-loop 而被中断。
    ...
    return result
```
#### 异步
```python
from langgraph.func import entrypoint

# checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
@entrypoint(checkpointer=checkpointer)
async def my_workflow(some_input: dict) -> int:
    # 这里可能包含 API 调用等耗时逻辑。
    # 并且可能为了 human-in-the-loop 而被中断。
    ...
    return result
```
> [!warning]
**序列化**
  入口点的 **输入** 和 **输出** 必须是 JSON 可序列化的才能支持检查点。请参阅[序列化](#serialization) 部分了解更多详细信息。

### 可注入参数

声明 `entrypoint` 时，您可以请求访问将在运行时自动注入的其他参数。这些参数包括：

| 范围 | 描述 |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **以前的** | 访问与给定线程的前一个 `checkpoint` 关联的状态。请参阅[短期记忆](#short-term-memory)。 |
| **store** | \[BaseStore]\[langgraph.store.base.BaseStore] 的实例。对于[长期记忆](https://docs.langchain.com/oss/python/langgraph/use-functional-api#long-term-memory)很有用。 |
| **作家** | 使用异步 Python \< 3.11 时用于访问 StreamWriter。有关详细信息，请参阅[使用函数式 API 进行流式传输](https://docs.langchain.com/oss/python/langgraph/use-functional-api#streaming)。 |
| **配置** | 用于访问运行时配置。有关信息，请参阅 [RunnableConfig](https://python.langchain.com/docs/concepts/runnables/#runnableconfig)。 |

> [!warning]
使用适当的名称和类型注释来声明参数。

### 请求可注入参数
```python
from langchain_core.runnables import RunnableConfig
from langgraph.func import entrypoint
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import StreamWriter

# 内存版 checkpointer 适合教程和本地实验；进程结束后数据通常不会持久保留。
in_memory_checkpointer = InMemorySaver(...)
# InMemoryStore 是内存版长期 store，适合理解 API；生产环境通常要替换为数据库或外部存储。
in_memory_store = InMemoryStore(...)  # 用于长期记忆的 InMemoryStore 实例。

@entrypoint(
    # checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
    checkpointer=in_memory_checkpointer,  # 指定 checkpointer，用来保存短期会话状态。
    store=in_memory_store  # 指定 store，用来保存跨会话数据。
)
def my_workflow(
    some_input: dict,  # 输入内容，例如通过 `invoke` 传入的数据。
    *,
    previous: Any = None, # 用于短期记忆。
    store: BaseStore,  # 用于长期记忆。
    writer: StreamWriter,  # 用于流式传输自定义数据。
    config: RunnableConfig  # 用于访问传给 entrypoint 的配置。
) -> ...:
```
### 执行中

使用 [`@entrypoint`](#entrypoint) 生成一个 [`Pregel`](https://reference.langchain.com/python/langgraph/pregel/#langgraph.pregel.Pregel.stream) 对象，可以使用 `invoke`、`ainvoke`、`stream` 和 `astream` 方法执行该对象。

#### 调用
```python
config = {
    "configurable": {
        "thread_id": "some_thread_id"
    }
}
my_workflow.invoke(some_input, config)  # 同步等待结果。
```
#### 异步调用
```python
config = {
    "configurable": {
        "thread_id": "some_thread_id"
    }
}
await my_workflow.ainvoke(some_input, config)  # 异步等待结果。
```
#### 溪流
```python
config = {
    "configurable": {
        "thread_id": "some_thread_id"
    }
}

for chunk in my_workflow.stream(some_input, config):
    print(chunk)
```
#### 异步流
```python
config = {
    "configurable": {
        "thread_id": "some_thread_id"
    }
}

# async for 会逐个处理异步事件，常用于 streaming、语音转写和实时 UI。
async for chunk in my_workflow.astream(some_input, config):
    print(chunk)
```
### 恢复中

在 [中断](https://reference.langchain.com/python/langgraph/types/interrupt) 之后恢复执行可以通过将 **resume** 值传递给 [`Command`](https://reference.langchain.com/python/langgraph/types/Command) 原语来完成。

#### 调用
```python
from langgraph.types import Command

config = {
    "configurable": {
        "thread_id": "some_thread_id"
    }
}

# Command 可以同时表达 state 更新和下一步跳转，适合工具返回后改变流程的场景。
my_workflow.invoke(Command(resume=some_resume_value), config)
```
#### 异步调用
```python
from langgraph.types import Command

config = {
    "configurable": {
        "thread_id": "some_thread_id"
    }
}

# Command 可以同时表达 state 更新和下一步跳转，适合工具返回后改变流程的场景。
await my_workflow.ainvoke(Command(resume=some_resume_value), config)
```
#### 溪流
```python
from langgraph.types import Command

config = {
    "configurable": {
        "thread_id": "some_thread_id"
    }
}

# Command 可以同时表达 state 更新和下一步跳转，适合工具返回后改变流程的场景。
for chunk in my_workflow.stream(Command(resume=some_resume_value), config):
    print(chunk)
```
#### 异步流
```python
from langgraph.types import Command

config = {
    "configurable": {
        "thread_id": "some_thread_id"
    }
}

# Command 可以同时表达 state 更新和下一步跳转，适合工具返回后改变流程的场景。
async for chunk in my_workflow.astream(Command(resume=some_resume_value), config):
    print(chunk)
```
**发生错误后恢复**

要在发生错误后恢复，请使用 `None` 和相同的 **线程 id**（配置）运行 `entrypoint`。

这假设底层的**错误**已得到解决并且执行可以成功进行。

#### 调用
```python

config = {
    "configurable": {
        "thread_id": "some_thread_id"
    }
}

my_workflow.invoke(None, config)
```
#### 异步调用
```python

config = {
    "configurable": {
        "thread_id": "some_thread_id"
    }
}

await my_workflow.ainvoke(None, config)
```
#### 溪流
```python

config = {
    "configurable": {
        "thread_id": "some_thread_id"
    }
}

for chunk in my_workflow.stream(None, config):
    print(chunk)
```
#### 异步流
```python

config = {
    "configurable": {
        "thread_id": "some_thread_id"
    }
}

# async for 会逐个处理异步事件，常用于 streaming、语音转写和实时 UI。
async for chunk in my_workflow.astream(None, config):
    print(chunk)
```
### 短期记忆

当 `entrypoint` 与 `checkpointer` 一起定义时，它会将同一 **线程 id** 上的连续调用之间的信息存储在 [检查点](https://docs.langchain.com/oss/python/langgraph/persistence#checkpoints) 中。

这允许使用 `previous` 参数访问先前调用的状态。

默认情况下，`previous` 参数是上一次调用的返回值。
```python
# checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
@entrypoint(checkpointer=checkpointer)
def my_workflow(number: int, *, previous: Any = None) -> int:
    previous = previous or 0
    return number + previous

config = {
    "configurable": {
        "thread_id": "some_thread_id"
    }
}

my_workflow.invoke(1, config)  # 示例输出：1（previous 原本是 None）。
my_workflow.invoke(2, config)  # 示例输出：3（previous 是上一次调用得到的 1）。
```
#### `entrypoint.final`

[`entrypoint.final`](https://reference.langchain.com/python/langgraph/func/entrypoint/final) 是一个特殊原语，可以从入口点返回，并允许将检查点中保存的值与入口点的返回值**解耦**。

第一个值是入口点的返回值，第二个值是将保存在检查点中的值。类型注释是 `entrypoint.final[return_type, save_type]`。
```python
# checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
@entrypoint(checkpointer=checkpointer)
def my_workflow(number: int, *, previous: Any = None) -> entrypoint.final[int, int]:
    previous = previous or 0
    # 这里会把上一次的值返回给调用方，从而保存中间结果。
    # 把 2 * number 写入 checkpoint，下一次调用会继续使用它。
    # 对应 `previous` 参数。
    return entrypoint.final(value=previous, save=2 * number)

config = {
    "configurable": {
        "thread_id": "1"
    }
}

my_workflow.invoke(3, config)  # 示例输出：0（previous 原本是 None）。
my_workflow.invoke(1, config)  # 示例输出：6（previous 是上一次调用得到的 3 * 2）。
```
## 任务

**任务**代表一个离散的工作单元，例如 API 调用或数据处理步骤。它有两个关键特征：

* **异步执行**：任务被设计为异步执行，允许多个操作同时运行而不会阻塞。
* **检查点**：任务结果保存到检查点，从而可以从上次保存的状态恢复工作流。 （有关更多详细信息，请参阅[持久性](https://docs.langchain.com/oss/python/langgraph/persistence)）。

### 定义

任务是使用 `@task` 装饰器定义的，它包装了常规的 Python 函数。
```python
from langgraph.func import task

@task()
def slow_computation(input_value):
    # 模拟一个长耗时操作。
    ...
    return result
```
> [!warning]
**序列化**
  任务的 **输出** 必须是 JSON 可序列化的以支持检查点。

### 执行

**任务**只能从**入口点**、另一个**任务**或[状态图节点](https://docs.langchain.com/oss/python/langgraph/graph-api#nodes)内调用。

任务*不能*直接从主应用程序代码调用。

当您调用 **任务** 时，它会“立即”返回一个 future 对象。`future` 是稍后可用结果的占位符。

要获取 **任务** 的结果，您可以同步等待（使用 `result()`）或异步等待（使用 `await`）。

#### 同步调用
```python
# checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
@entrypoint(checkpointer=checkpointer)
def my_workflow(some_input: int) -> int:
    future = slow_computation(some_input)
    return future.result()  # 同步等待结果。
```
#### 异步调用
```python
# checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
@entrypoint(checkpointer=checkpointer)
async def my_workflow(some_input: int) -> int:
    return await slow_computation(some_input)  # 异步等待结果。
```
## 何时使用任务

**任务**在以下场景中很有用：

* **检查点**：当您需要将长时间运行的操作的结果保存到检查点时，以便在恢复工作流时不需要重新计算它。
* **人在回路**：如果您正在构建需要人工干预的工作流，则必须使用**任务**来封装任何随机性（例如 API 调用），以确保工作流可以正确恢复。有关更多详细信息，请参阅[决定论](#determinism) 部分。
* **并行执行**：对于 I/O 密集型任务，**任务**启用并行执行，允许多个操作同时运行而不会阻塞（例如，调用多个 API）。
* **可观察性**：将操作包装在**任务**中提供了一种跟踪工作流进度并使用 [LangSmith](https://docs.langchain.com/langsmith/home) 监视各个操作执行情况的方法。
* **可重试工作**：当需要重试工作来处理失败或不一致时，**任务**提供了一种封装和管理重试逻辑的方法。

## 序列化

LangGraph 中的序列化有两个关键方面：

1. `entrypoint` 输入和输出必须是 JSON 可序列化的。
2. `task` 输出必须是 JSON 可序列化的。

这些要求对于启用检查点和工作流恢复是必要的。使用字典、列表、字符串、数字和布尔值等 Python 基元来确保输入和输出可序列化。

序列化可确保工作流状态（例如任务结果和中间值）能够可靠地保存和恢复。这对于实现人在回路、容错和并行执行至关重要。

当工作流配置了检查点时，提供不可序列化的输入或输出将导致运行时错误。

## 决定论

要利用“人在回路”等功能，任何随机性都应该封装在“任务”中。这保证了当执行停止时（例如，对于循环中的人）然后恢复，它将遵循相同的*步骤序列*，即使**任务**结果是不确定的。

LangGraph 通过在执行时保留 **task** 和 [**subgraph**](https://docs.langchain.com/oss/python/langgraph/use-subgraphs) 结果来实现此行为。精心设计的工作流可确保恢复执行遵循“相同的步骤顺序”，从而可以正确检索先前计算的结果，而无需重新执行它们。这对于长时间运行的**任务**或具有不确定结果的**任务**特别有用，因为它避免重复以前完成的工作并允许从基本相同的工作中恢复。

虽然工作流的不同运行可能会产生不同的结果，但恢复**特定**运行应始终遵循相同的记录步骤顺序。这使得 LangGraph 能够有效地查找在图被中断之前执行的 **任务** 和 **子图** 结果，并避免重新计算它们。

## 幂等性

幂等性确保多次运行相同的操作会产生相同的结果。如果某个步骤因失败而重新运行，这有助于防止重复的 API 调用和冗余处理。始终将 API 调用放置在 **tasks** 函数中以进行检查点，并将它们设计为在重新执行时具有幂等性。如果 **任务** 启动但未成功完成，则可能会发生重新执行。然后，如果工作流恢复，**任务**将再次运行。使用幂等性密钥或验证现有结果以避免重复。

## 常见陷阱

### 处理副作用

将副作用（例如，写入文件、发送电子邮件）封装在任务中，以确保在恢复工作流时不会多次执行它们。

#### 不正确
在本例中，副作用（写入文件）直接包含在工作流中，因此在恢复工作流时将再次执行。
```python
# checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
@entrypoint(checkpointer=checkpointer)
def my_workflow(inputs: dict) -> int:
    # 恢复 workflow 时，这段代码会再次执行。
    # 这里的文件写入是副作用；如果恢复时重跑，会再次写入文件。
    with open("output.txt", "w") as f:  # [!code highlight]
        f.write("Side effect executed")  # [!code highlight]
    # interrupt 会暂停执行并把请求交给外部人类或 UI，之后用 Command(resume=...) 恢复。
    value = interrupt("question")
    return value
```
#### 正确的
在此示例中，副作用被封装在任务中，确保恢复时执行的一致性。
```python
from langgraph.func import task

@task  # [!code highlight]
def write_to_file():  # [!code highlight]
    with open("output.txt", "w") as f:
        f.write("Side effect executed")

# checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
@entrypoint(checkpointer=checkpointer)
def my_workflow(inputs: dict) -> int:
    # 副作用现在被封装进 task，恢复执行时更容易避免重复副作用。
    write_to_file().result()
    # interrupt 会暂停执行并把请求交给外部人类或 UI，之后用 Command(resume=...) 恢复。
    value = interrupt("question")
    return value
```
### 非确定性控制流

每次可能给出不同结果的操作（例如获取当前时间或随机数）应封装在任务中，以确保在恢复时返回相同的结果。

* 在任务中：获取随机数（5）→中断→恢复→（再次返回5）→...
* 不在任务中：获取随机数（5）→中断→恢复→获取新的随机数（7）→...

当使用带有多个中断调用的**人在回路**工作流时，这一点尤其重要。 LangGraph 保留每个任务/入口点的恢复值列表。当遇到中断时，它会与相应的恢复值相匹配。这种匹配严格**基于索引**，因此恢复值的顺序应与中断的顺序匹配。

如果恢复时未保持执行顺序，则一次 [`interrupt`](https://reference.langchain.com/python/langgraph/types/interrupt) 调用可能会与错误的 `resume` 值匹配，从而导致不正确的结果。

请阅读[决定论](#determinism) 部分了解更多详细信息。

#### 不正确
在此示例中，工作流使用当前时间来确定要执行哪个任务。这是不确定的，因为工作流的结果取决于它的执行时间。
```python
from langgraph.func import entrypoint

# checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
@entrypoint(checkpointer=checkpointer)
def my_workflow(inputs: dict) -> int:
    t0 = inputs["t0"]
    t1 = time.time()  # [!code highlight]

    delta_t = t1 - t0

    if delta_t > 1:
        result = slow_task(1).result()
        # interrupt 会暂停执行并把请求交给外部人类或 UI，之后用 Command(resume=...) 恢复。
        value = interrupt("question")
    else:
        result = slow_task(2).result()
        value = interrupt("question")

    return {
        "result": result,
        "value": value
    }
```
#### 正确的
在此示例中，工作流使用输入 `t0` 来确定要执行哪个任务。这是确定性的，因为工作流的结果仅取决于输入。
```python
import time

from langgraph.func import task

@task  # [!code highlight]
def get_time() -> float:  # [!code highlight]
    return time.time()

# checkpointer 保存线程内的执行状态，用于多轮对话、暂停恢复和 human-in-the-loop。
@entrypoint(checkpointer=checkpointer)
def my_workflow(inputs: dict) -> int:
    t0 = inputs["t0"]
    t1 = get_time().result()  # [!code highlight]

    delta_t = t1 - t0

    if delta_t > 1:
        result = slow_task(1).result()
        # interrupt 会暂停执行并把请求交给外部人类或 UI，之后用 Command(resume=...) 恢复。
        value = interrupt("question")
    else:
        result = slow_task(2).result()
        value = interrupt("question")

    return {
        "result": result,
        "value": value
    }
```
## 了解更多

* [如何使用函数式API](https://docs.langchain.com/oss/python/langgraph/use-functional-api)
* [[06-Graph API|Graph API 概念概述]]
* [Graph API 和 Function API 之间的选择](https://docs.langchain.com/oss/python/langgraph/choosing-apis)
