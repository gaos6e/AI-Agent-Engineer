---
title: 记忆
aliases:
  - Memory
  - 记忆
source: https://docs.langchain.com/oss/python/concepts/memory
source_md: https://docs.langchain.com/oss/python/concepts/memory.md
retrieved: 2026-05-07
tags:
  - langchain
  - python
  - docs/learn
license: MIT
---

# 记忆

[Memory](https://docs.langchain.com/oss/python/langgraph/add-memory) 是一个记住先前交互信息的系统。对于 AI 代理来说，记忆至关重要，因为它可以让它们记住之前的交互、从反馈中学习并适应用户偏好。随着代理通过大量用户交互处理更复杂的任务，此功能对于效率和用户满意度变得至关重要。

本概念指南根据记忆范围涵盖两种类型的记忆：

* [短期记忆](#short-term-memory) 或[线程](https://docs.langchain.com/oss/python/langgraph/persistence#threads) 作用域记忆通过维护会话中的消息历史记录来跟踪正在进行的对话。 LangGraph 将短期记忆作为代理 [状态](https://docs.langchain.com/oss/python/langgraph/graph-api#state) 的一部分进行管理。使用 [checkpointer](https://docs.langchain.com/oss/python/langgraph/persistence#checkpoints) 将状态保存到数据库中，以便可以随时恢复线程。当调用图或完成一个步骤时，短期记忆会更新，并且在每个步骤开始时读取状态。
* [长期记忆](#long-term-memory) 跨会话存储用户特定或应用程序级数据，并在*跨*会话线程之间共享。它可以在*任何时间*和*在任何线程*中被调用。记忆的作用域是任何自定义命名空间，而不仅仅是单个线程 ID 内。 LangGraph 提供了[stores](https://docs.langchain.com/oss/python/langgraph/persistence#memory-store)（[参考文档](https://langchain-ai.github.io/langgraph/reference/store/#langgraph.store.base.BaseStore)）来让您保存和调用长期记忆。

<img src="LangChain/attachments/oss/images/short-vs-long.png" alt="Short vs long" width="571" height="372" data-path="oss/images/short-vs-long.png" data-source="https://docs.langchain.com/oss/images/short-vs-long.png" />

## 短期记忆

[短期记忆](https://docs.langchain.com/oss/python/langgraph/add-memory#add-short-term-memory) 让您的应用程序记住单个[线程](https://docs.langchain.com/oss/python/langgraph/persistence#threads) 或对话中之前的交互。 [线程](https://docs.langchain.com/oss/python/langgraph/persistence#threads) 在会话中组织多个交互，类似于电子邮件在单个对话中对消息进行分组的方式。

LangGraph 将短期记忆作为代理状态的一部分进行管理，并通过线程范围的检查点进行持久化。此状态通常可以包括对话历史记录以及其他状态数据，例如上传的文件、检索的文档或生成的 artifact。通过将这些存储在图的状态中，机器人可以访问给定对话的完整上下文，同时保持不同线程之间的分离。

### 管理短期记忆

对话历史是短期记忆最常见的形式，而长时间对话对当今的 LLM 提出了挑战。完整的历史记录可能不适合 LLM 的上下文窗口，从而导致不可恢复的错误。即使您的 LLM 支持完整的上下文长度，大多数 LLM 在长上下文中仍然表现不佳。模型会被陈旧或偏离主题的内容“分散注意力”，同时还要承受响应时间较慢和成本较高的问题。

聊天模型使用消息接受上下文，其中包括开发人员提供的指令（系统消息）和用户输入（用户消息）。在聊天应用程序中，消息在用户输入和模型响应之间交替，导致消息列表随着时间的推移而变长。由于上下文窗口有限，并且令牌丰富的消息列表可能成本高昂，因此许多应用程序可以从使用手动删除或忘记过时信息的技术中受益。

<img src="LangChain/attachments/oss/images/filter.png" alt="Filter" width="594" height="200" data-path="oss/images/filter.png" data-source="https://docs.langchain.com/oss/images/filter.png" />

有关管理消息的常用技术的更多信息，请参阅[添加和管理记忆](https://docs.langchain.com/oss/python/langgraph/add-memory#manage-short-term-memory) 指南。

## 长期记忆

LangGraph 中的[长期记忆](https://docs.langchain.com/oss/python/langgraph/add-memory#add-long-term-memory) 允许系统在不同的对话或会话中保留信息。与**线程范围**的短期记忆不同，长期记忆保存在自定义“命名空间”中。

长期记忆是一项复杂的挑战，没有一刀切的解决方案。但是，以下问题提供了一个框架来帮助您驾驭不同的技术：

* 记忆的类型是什么？人类会使用记忆来记住事实（[语义记忆](#semantic-memory)）、经验（[情景记忆](#episodic-memory)）和规则（[程序记忆](#procedural-memory)）。AI 代理可以以相同的方式使用记忆。例如，AI 代理可以使用记忆来记住有关用户的特定事实以完成任务。
* [您想什么时候更新记忆？](#writing-memories) 记忆可以作为代理应用程序逻辑的一部分进行更新（例如，“在热路径上”）。在这种情况下，代理通常决定在响应用户之前记住事实。或者，可以将记忆更新为后台任务（在后台/异步运行并生成记忆的逻辑）。我们在[下面的部分](#writing-memories) 中解释了这些方法之间的权衡。

不同的应用程序需要不同类型的记忆。尽管这个类比并不完美，但检查[人类记忆类型](https://www.psychologytoday.com/us/basics/memory/types-of-memory?ref=blog.langchain.dev) 可能会很有洞察力。一些研究（例如，[CoALA 论文](https://arxiv.org/pdf/2309.02427)）甚至将这些人类记忆类型映射到 AI 代理中使用的记忆类型。

| 记忆类型 | 存储了什么 | 人类的例子 | 代理示例 |
| -------------------------------- | -------------- | -------------------------- | ------------------- |
| [语义](#semantic-memory) | 事实 | 我在学校学到的东西 | 有关用户的事实 |
| [情景](#episodic-memory) | 经验 | 我所做的事情 | 过去的代理行动 |
| [程序](#procedural-memory) | 指示 | 本能或运动技能 | 坐席系统提示 |

### 语义记忆

[语义记忆](https://en.wikipedia.org/wiki/Semantic_memory)，无论是在人类还是人工智能体中，都涉及到特定事实和概念的保留。对于人类来说，它可以包括在学校学到的信息以及对概念及其关系的理解。对于 AI 代理来说，语义记忆通常用于通过记住过去交互中的事实或概念来个性化应用程序。

> [!note]
语义记忆不同于“语义搜索”，“语义搜索”是一种使用“含义”（通常作为嵌入）查找相似内容的技术。语义记忆是心理学术语，指的是存储事实和知识，而语义搜索是一种基于含义而不是精确匹配来检索信息的方法。

语义记忆可以通过不同的方式进行管理：

#### 画像（Profile）

记忆可以是关于用户、组织或其他实体（包括代理本身）的范围明确的特定信息的单个、持续更新的“画像（profile）”。画像（profile）通常只是一个 JSON 文档，其中包含您选择用来表示域的各种键值对。

记住画像（profile）时，您需要确保每次都**更新**该 profile。因此，您需要传递之前的 profile，并[要求模型生成新的 profile](https://github.com/langchain-ai/memory-template)（或一些 [JSON 补丁](https://github.com/hinthornw/trustcall) 以应用于旧的 profile）。随着 profile 变大，这可能会变得容易出错，并且可能会受益于将 profile 拆分为多个文档或在生成文档时进行严格解码以确保记忆 schema 保持有效。

<img src="LangChain/attachments/oss/images/update-profile.png" alt="Update profile" width="507" height="516" data-path="oss/images/update-profile.png" data-source="https://docs.langchain.com/oss/images/update-profile.png" />

#### 记忆集合（Collection）

或者，记忆可以是随时间不断更新和扩展的文档集合。每条记忆的范围可以更窄，更容易生成，这意味着随着时间的推移，您不太可能**丢失**信息。对于 LLM 来说，为新信息生成“新”对象比将新信息与现有 profile 协调起来更容易。因此，文档集合往往会带来[更高的下游召回率](https://en.wikipedia.org/wiki/Precision_and_recall)。

然而，这改变了记忆更新的一些复杂性。该模型现在必须“删除”或“更新”列表中的现有项目，这可能很棘手。此外，某些模型可能默认为过度插入，而另一些模型可能默认为过度更新。请参阅 [Trustcall](https://github.com/hinthornw/trustcall) 包，了解管理此问题的一种方法并考虑评估（例如，使用 [LangSmith](https://docs.langchain.com/langsmith/evaluation) 等工具）来帮助您调整行为。

使用文档集合也会将复杂性转移到列表上的记忆**搜索**。 `Store` 目前支持[语义搜索](https://langchain-ai.github.io/langgraph/reference/store/#langgraph.store.base.SearchOp.query) 和[按内容过滤](https://langchain-ai.github.io/langgraph/reference/store/#langgraph.store.base.SearchOp.filter)。

最后，使用记忆集合可能会导致为模型提供全面的上下文变得具有挑战性。虽然个体记忆可能遵循特定的模式，但这种结构可能无法捕捉记忆之间的完整背景或关系。因此，当使用这些记忆生成响应时，模型可能缺乏重要的上下文信息，而这些信息在统一 profile 方法中更容易获得。

<img src="LangChain/attachments/oss/images/update-list.png" alt="Update list" width="483" height="491" data-path="oss/images/update-list.png" data-source="https://docs.langchain.com/oss/images/update-list.png" />

无论采用哪种记忆管理方法，关键点都是代理会使用语义记忆来[支撑其响应](https://docs.langchain.com/oss/python/langchain/retrieval)，这通常会带来更加个性化且更相关的交互。

### 情景记忆

在人类和 AI 智能体中，[情景记忆](https://en.wikipedia.org/wiki/Episodic_memory) 涉及回忆过去的事件或行为。 [CoALA 论文](https://arxiv.org/pdf/2309.02427) 很好地阐述了这一点：事实可以写入语义记忆，而*经验*可以写入情景记忆。对于 AI 代理来说，情景记忆通常用于帮助代理记住如何完成任务。

在实践中，情景记忆通常通过少样本提示实现：代理从过去的序列中学习如何正确执行任务。有时“展示”比“讲述”更容易，LLM 可以从示例中学到很多东西。少样本学习让您可以用输入输出示例更新提示，以说明预期行为，从而[“编程”](https://x.com/karpathy/status/1627366413840322562) 您的 LLM。虽然可以用各种最佳实践生成少样本示例，但挑战通常在于如何根据用户输入选择最相关的示例。

请注意，记忆 [store](https://docs.langchain.com/oss/python/langgraph/persistence#memory-store) 只是作为少数示例存储数据的一种方法。如果您希望有更多的开发人员参与，或者将 few-shot 示例与您的评估工具更紧密地联系起来，您还可以使用 [LangSmith 数据集](https://docs.langchain.com/langsmith/manage-datasets) 来存储您的数据并实现您自己的检索逻辑，以根据用户输入选择最相关的示例。

请参阅这篇[博客文章](https://blog.langchain.dev/few-shot-prompting-to-improve-tool-calling-performance/)，它展示了如何通过少样本提示提高工具调用性能；另请参阅这篇[博客文章](https://blog.langchain.dev/aligning-llm-as-a-judge-with-human-preferences/)，了解如何使用少量示例让 LLM 与人类偏好保持一致。

### 程序记忆

[程序记忆](https://en.wikipedia.org/wiki/Procedural_memory)，在人类和 AI 代理中，都涉及记住用于执行任务的规则。对于人类来说，程序记忆就像如何执行任务的内化知识，例如通过基本运动技能和平衡来骑自行车。另一方面，情景记忆涉及回忆特定的经历，例如您第一次成功地骑着没有辅助轮的自行车，或者一次难忘的自行车骑行穿过风景优美的路线。对于 AI 代理来说，程序记忆是模型权重、代理代码和代理提示的组合，它们共同决定代理的功能。

在实践中，代理修改模型权重或重写代码的情况相当罕见。然而，更常见的是代理修改自己的提示。

完善代理指令的一种有效方法是通过 [“Reflection”](https://blog.langchain.dev/reflection-agents/) 或元提示。这涉及用当前指令（例如系统提示）以及最近的对话或明确的用户反馈来提示代理。然后，代理根据此输入完善自己的指令。这种方法对于那些难以预先指定指令的任务特别有用，因为它允许代理从其交互中学习和适应。

例如，我们使用外部反馈和提示重写构建了一个[推文生成器](https://www.youtube.com/watch?v=Vn8A3BxfplE)，为 Twitter 生成高质量的论文摘要。在这种情况下，特定的摘要提示很难指定*先验*，但用户很容易批评生成的推文并提供有关如何改进摘要过程的反馈。

下面的伪代码显示了如何使用 LangGraph 记忆 [store](https://docs.langchain.com/oss/python/langgraph/persistence#memory-store) 来实现这一点，使用 store 保存提示，使用 `update_instructions` 节点获取当前提示（以及与 `state["messages"]` 中捕获的用户对话的反馈），更新提示，并将新提示保存回 store。然后，`call_model` 从 store 获取更新的提示并使用它生成响应。
```python
# 使用这些指令的节点：这里演示读取长期记忆中的说明。
def call_model(state: State, store: BaseStore):
    namespace = ("agent_instructions", )
    instructions = store.get(namespace, key="agent_a")[0]
    # 应用逻辑：这里放真正处理用户请求的业务代码。
    prompt = prompt_template.format(instructions=instructions.value["instructions"])
    ...

# 更新指令的节点：这里演示把新的偏好写回记忆。
def update_instructions(state: State, store: BaseStore):
    namespace = ("instructions",)
    instructions = store.search(namespace)[0]
    # 记忆逻辑：这里负责读取、搜索或更新长期记忆。
    prompt = prompt_template.format(instructions=instructions.value["instructions"], conversation=state["messages"])
    output = llm.invoke(prompt)
    new_instructions = output['new_instructions']
    store.put(("agent_instructions",), "agent_a", {"instructions": new_instructions})
    ...
```
<img src="LangChain/attachments/oss/images/update-instructions.png" alt="Update instructions" width="493" height="515" data-path="oss/images/update-instructions.png" data-source="https://docs.langchain.com/oss/images/update-instructions.png" />

### 书写回忆

代理写入记忆有两种主要方法：[“在热路径中”](#in-the-hot-path) 和 [“在后台”](#in-the-background)。

<img src="LangChain/attachments/oss/images/hot_path_vs_background.png" alt="Hot path vs background" width="842" height="418" data-path="oss/images/hot_path_vs_background.png" data-source="https://docs.langchain.com/oss/images/hot_path_vs_background.png" />

#### 在热路径中

在运行时创建记忆既有优点也有挑战。从积极的一面来看，这种方法允许实时更新，使新的记忆立即可用于后续的交互。它还实现了透明度，因为当创建和存储记忆时可以通知用户。

然而，这种方法也面临着挑战。如果代理需要新工具来决定将哪些内容写入记忆中，则可能会增加复杂性。此外，推理将哪些内容保存到记忆的过程可能会影响代理延迟。最后，代理必须在记忆创建和其他职责之间执行多任务，这可能会影响创建的记忆的数量和质量。

例如，ChatGPT 使用 [save\_memories](https://openai.com/index/memory-and-new-controls-for-chatgpt/) 工具将记忆作为内容字符串更新插入，决定是否以及如何在每个用户消息中使用此工具。请参阅 [Memory Agent](https://github.com/langchain-ai/memory-agent) 模板作为参考实现。

#### 在后台

创建记忆作为单独的后台任务有几个优点。它消除了主应用程序中的延迟，将应用程序逻辑与记忆管理分开，并允许代理更集中地完成任务。这种方法还提供了定时记忆创建的灵活性，以避免冗余工作。

然而，这种方法也有其自身的挑战。确定记忆写入的频率变得至关重要，因为不频繁的更新可能会使其他线程失去新的上下文。决定何时触发记忆形成也很重要。常见的策略包括在设定的时间段后进行调度（如果发生新事件则重新调度）、使用 cron 调度或允许用户或应用程序逻辑手动触发。

请参阅 [Memory Service](https://github.com/langchain-ai/memory-template) 模板作为参考实现。

### 记忆 store

LangGraph 将长期记忆作为 JSON 文档存储在 [store](https://docs.langchain.com/oss/python/langgraph/persistence#memory-store) 中。每条记忆都组织在自定义 `namespace` （类似于文件夹）和不同的 `key` （类似于文件名）下。命名空间通常包含用户或组织 ID 或其他标签，以便更轻松地组织信息。这种结构可以实现记忆的分层组织。然后通过内容过滤器支持跨命名空间搜索。
```python
from langgraph.store.memory import InMemoryStore

def embed(texts: list[str]) -> list[list[float]]:
    # 这里请替换为真实的 embedding 函数或 LangChain embeddings 对象。
    return [[1.0, 2.0] * len(texts)]

# InMemoryStore 只把数据保存在进程内存字典中；生产环境应换成数据库支持的 store。
store = InMemoryStore(index={"embed": embed, "dims": 2})
user_id = "my-user"
application_context = "chitchat"
namespace = (user_id, application_context)
store.put(
    namespace,
    "a-memory",
    {
        "rules": [
            "User likes short, direct language",
            "User only speaks English & python",
        ],
        "my-key": "my-value",
    },
)
# 按 ID 读取一条 memory。
item = store.get(namespace, "a-memory")
# 在这个 namespace 中搜索 memory：先按内容等价性过滤，再按向量相似度排序。
items = store.search(
    namespace, filter={"my-key": "my-value"}, query="language preferences"
)
```
有关记忆 store 的更多信息，请参阅[持久性](https://docs.langchain.com/oss/python/langgraph/persistence#memory-store) 指南。

## 了解更多

* [[05-Context|上下文概念概述]]
* [LangChain 中的短期记忆](https://docs.langchain.com/oss/python/langchain/short-term-memory)
* [LangGraph 中的记忆](https://docs.langchain.com/oss/python/langgraph/add-memory)
