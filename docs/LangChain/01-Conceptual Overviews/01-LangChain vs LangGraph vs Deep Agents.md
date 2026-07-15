---
title: LangChain、LangGraph 与 Deep Agents 对比
aliases:
  - LangChain vs. LangGraph vs. Deep Agents
  - LangChain、LangGraph 与 Deep Agents 对比
source: https://docs.langchain.com/oss/python/concepts/products
source_md: https://docs.langchain.com/oss/python/concepts/products.md
retrieved: 2026-05-07
tags:
  - langchain
  - python
  - docs/learn
license: MIT
---

# LangChain、LangGraph 与 Deep Agents 对比

> 了解 LangChain、LangGraph 和 Deep Agents 之间的区别以及何时使用每一种

LangChain 维护了多个开源包来帮助您构建代理。每个包在代理开发栈中都有不同用途。了解[代理框架](#agent-frameworks-like-langchain)、[代理运行时](#agent-runtimes-like-langgraph) 和[代理 harness](#agent-harnesses-like-the-deep-agents-sdk) 之间的区别，有助于选择适合需求的工具。

<table>
  <thead>
    <tr>
      <th></th>

<th>框架</th>
      <th>运行时</th>
      <th>Harness</th>
    </tr>
  </thead>

<tbody>
    <tr>
      <td>增值</td>
      <td class="tdlist"><ul><li>抽象</li><li>集成</li></ul></td>
      <td class="tdlist"><ul><li>持久执行</li><li>Streaming</li><li>HITL</li><li>持久性</li></ul></td>
      <td class="tdlist"><ul><li>预定义工具</li><li>提示</li><li>子代理</li></ul></td>
    </tr>

<tr>
      <td>何时使用</td>
      <td class="tdlist"><ul><li>快速入门</li><li>标准化团队建设方式</li></ul></td>
      <td class="tdlist"><ul><li>低级控制</li><li>长时间运行、有状态的工作流和代理</li></ul></td>
      <td class="tdlist"><ul><li>更多自主代理</li><li>面临复杂、不确定性任务的代理</li></ul></td>
    </tr>

<tr>
      <td>选项</td>
      <td class="tdlist"><ul><li>LangChain</li><li>Vercel 的 AI SDK</li><li>CrewAI</li><li>OpenAI Agents SDK</li><li>Google ADK</li><li>LlamaIndex</li></ul></td>
      <td class="tdlist"><ul><li>LangGraph</li><li>Temporal</li><li>Inngest</li></ul></td>
      <td class="tdlist"><ul><li>Deep Agents SDK</li><li>Claude Agent SDK</li><li>Manus</li></ul></td>
    </tr>
  </tbody>
</table>

## 代理框架（如 LangChain）

代理框架提供了抽象，让使用 LLM 构建应用时更容易上手。

[LangChain](https://docs.langchain.com/oss/python/langchain/overview) 是一个代理框架，提供结构化内容块、代理循环和中间件等抽象。

LangChain 的抽象设计易于上手，同时仍提供高级用例所需的灵活性。

虽然 LangChain 构建在 [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) 之上，但您无需了解 LangGraph 即可使用 LangChain。

代理框架的其他示例包括 [Vercel 的 AI SDK](https://ai-sdk.dev/docs/introduction)、[CrewAI](https://www.crewai.com/)、[OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)、[Google ADK](https://google.github.io/adk-docs/)、[LlamaIndex](https://www.llamaindex.ai/) 等等。

### 何时使用 LangChain

在以下情况下使用 LangChain：

* 您想要快速构建代理和自主应用程序。
* 您需要模型、工具和代理循环的标准抽象。
* 您需要一个易于使用但仍提供灵活性的框架。
* 您正在构建简单的代理应用程序，无需复杂的编排需求。

## 代理运行时（如 LangGraph）

代理运行时提供了在生产中运行代理的工具。
支持的工具可能包括：

* **持久执行**：代理在出现故障时仍能持续运行，并且可以长时间运行，从中断处恢复。
* **流式传输**：支持流式工作流和响应。
* **人在回路**：通过检查和修改代理状态来纳入人工监督。
* **持久化**：状态管理的线程级和跨线程持久化。
* **低级控制**：直接控制代理编排，无需高级抽象。

[LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) 是一个低级编排框架和运行时，用于构建、管理和部署长期运行的有状态代理。

代理框架通常是更高级别的并且在代理运行时上运行。
例如，LangChain 1.0 是建立在 LangGraph 之上的。

代理运行时的其他示例包括 [Temporal](https://temporal.io/)、[Inngest](https://www.inngest.com/) 和其他持久执行引擎。

### 何时使用 LangGraph

在以下情况下使用 LangGraph：

* 您需要对代理编排进行细粒度、低级别的控制。
* 您需要长期运行、有状态代理的持久执行。
* 您正在构建结合了确定性步骤和代理步骤的复杂工作流。
* 您需要用于代理部署的生产就绪基础设施。

## 代理工具（如 Deep Agents SDK）

代理束是一种带有内置工具和功能的主观框架，内置工具和功能，用于构建复杂且长期运行的代理。
支持的工具可能包括：

* **规划功能**：使用待办事项列表跟踪多个任务。
* **任务委派**：委派工作并使用子代理保持上下文干净。
* **文件系统**：对不同可插拔存储后端上的文件进行读写访问。
* **令牌管理**：对话历史摘要和大型工具结果驱逐。

[Deep Agents SDK](https://docs.langchain.com/oss/python/deepagents/overview) 构建在 LangGraph 之上，并添加了规划功能、用于上下文管理的文件系统、生成子代理的功能等。
Deep Agents 专为需要规划和分解的复杂、多步骤任务而设计。

示例任务包括处理搜索结果、脚本和其他状态中的 artifact。

代理工具的其他示例包括 [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)、[Manus](https://manus.im/) 和其他编码 CLI。

### 何时使用 Deep Agents SDK

在以下情况下使用 [Deep Agents SDK](https://docs.langchain.com/oss/python/deepagents/overview)：

* 您正在构建长期运行的代理。
* 您正在构建需要处理复杂、多步骤任务的代理。
* 您想要使用预定义的工具，例如文件系统操作、bash 执行和自动化上下文工程。
* 您想要使用预定义的提示和子代理。

## 特性比较

虽然您可以使用 LangChain、LangGraph 和 Deep Agents 完成类似的任务，但集成它们的层级有所不同：

| 特征 | LangChain | LangGraph | Deep Agents |
| ----------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 短期记忆 | [短期记忆](https://docs.langchain.com/oss/python/langchain/short-term-memory) | [短期记忆](https://docs.langchain.com/oss/python/langgraph/add-memory#add-short-term-memory) | [`StateBackend`](https://docs.langchain.com/oss/python/deepagents/backends#statebackend-ephemeral) |
| 长期记忆 | [长期记忆](https://docs.langchain.com/oss/python/langchain/long-term-memory) | [长期记忆](https://docs.langchain.com/oss/python/langgraph/add-memory#add-long-term-memory) | [长期记忆](https://docs.langchain.com/oss/python/deepagents/memory) |
| 技能 | [多代理技能](https://docs.langchain.com/oss/python/langchain/multi-agent/skills) | - | [技能](https://docs.langchain.com/oss/python/deepagents/skills) |
| 子代理 | [多代理子代理](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents) | [子图](https://docs.langchain.com/oss/python/langgraph/use-subgraphs) | [子代理](https://docs.langchain.com/oss/python/deepagents/subagents) |
| 人在回路 | [人在回路中间件](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) | [中断](https://docs.langchain.com/oss/python/langgraph/interrupts) | [`interrupt_on` 参数](https://docs.langchain.com/oss/python/deepagents/harness#human-in-the-loop) |
| 流式传输 | [Agent Streaming](https://docs.langchain.com/oss/python/langchain/streaming/overview) | [流式传输](https://docs.langchain.com/oss/python/langgraph/streaming) | [流式传输](https://docs.langchain.com/oss/python/deepagents/streaming/overview) |

## 了解更多

* [LangChain 概述](https://docs.langchain.com/oss/python/langchain/overview)
* [LangGraph 概述](https://docs.langchain.com/oss/python/langgraph/overview)
* [Deep Agents 概述](https://docs.langchain.com/oss/python/deepagents/overview)
