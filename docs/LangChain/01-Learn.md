---
title: 学习
aliases:
  - Learn
  - 学习
source: https://docs.langchain.com/oss/python/learn
source_md: https://docs.langchain.com/oss/python/learn.md
source_url: https://docs.langchain.com/oss/python/learn
retrieved: 2026-05-07
source_checked: 2026-07-21
content_origin: third-party
content_status: frozen-reference
attribution: LangChain project documentation contributors
tags:
  - langchain
  - python
  - docs/learn
license: MIT
---

# 学习

> [!warning] 冻结的来源导航，不是当前课程或可执行基线
> 本页及其链接的译文快照于 2026-05-07 获取，用来保留 LangChain 官方学习入口、来源和 MIT 许可，并不保证导入、模型 ID、集成包、环境变量或生产建议仍然有效。先学习 [[LangChain/00-目录|本库的当前路线]]；再把本页当作按主题回到当前官方文档的导航。涉及 RAG、SQL、代码执行、外部消息或密钥时，不能直接复制示例运行，必须先完成数据/工具授权、依赖锁定、测试与安全审查。

> 帮助您入门的教程、概念指南和资源。

在文档的 **学习** 部分，您将找到一系列教程、概念概述和其他资源，以帮助您使用 LangChain 和 LangGraph 构建强大的应用程序。

## 使用案例

以下是按框架组织的常见用例教程。

### Deep Agents

[Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview) 包括用于管理上下文、虚拟文件系统和其他常见代理要求的内置功能。

- [[01-Data Analysis|数据分析]]：构建一个数据分析代理，将报告发送到 Slack。

- [[02-Deep Research|深度研究]]：构建一个具有子代理委托和战略反思的多步骤网络研究代理。

- [[03-Content Builder|Content Builder]]：构建带品牌记忆、技能、子代理和图像生成能力的内容写作代理。

### LangChain

[LangChain](https://docs.langchain.com/oss/python/langchain/overview) [agent](https://docs.langchain.com/oss/python/langchain/agents) 实现使简单用例变得容易上手。

- [[01-Semantic Search|语义搜索]]：使用 LangChain 组件在 PDF 上构建语义搜索引擎。

- [[02-RAG Agent|RAG Agent]]：创建检索增强生成（RAG）代理。

- [[03-SQL Agent|SQL Agent]]：构建 SQL 代理，通过人在回路审核与数据库交互。

- [[04-Voice Agent|语音代理]]：建立一个你能说、能听的代理。

### LangGraph

LangChain 的 [agent](https://docs.langchain.com/oss/python/langchain/agents) 实现使用 [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) 原语。
如果需要更深入的定制，可以直接在 LangGraph 中实现代理。

- [[01-Custom RAG Agent|Custom RAG Agent]]：使用 LangGraph 原语构建 RAG 代理以进行细粒度控制。

- [[02-Custom SQL Agent|自定义 SQL 代理]]：直接在LangGraph中实现SQL代理以获得最大的灵活性。

### 多代理

这些教程演示了[多代理模式](https://docs.langchain.com/oss/python/langchain/multi-agent)，将 LangChain 代理与 LangGraph 工作流混合在一起。

- [[01-Subagents Personal Assistant|子代理：个人助理]]：构建一个委派给子代理的个人助理。

- [[02-Handoffs Customer Support|Handoffs：客户支持]]：构建单个客服代理在不同状态之间转换的客户支持工作流。

- [[03-Router Knowledge Base|路由器：知识库]]：构建一个多源知识库，将查询路由到专门的代理。

- [[04-Skills SQL Assistant|技能：SQL Assistant]]：构建一个使用按需上下文加载逐步加载专业技能的代理。

## 概念概述

这些指南解释了 LangChain 和 LangGraph 的核心概念和 API。

- [[04-Memory|记忆]]：了解线程内和线程间交互的持久性。

- [[05-Context|上下文工程]]：学习为人工智能应用程序提供完成任务所需的正确信息和工具的方法。

- [[06-Graph API|Graph API]]：探索 LangGraph 的声明式图构建 API。

- [[07-Functional API|Functional API]]：将代理构建为单个功能。

## 其他资源

- [[01-LangChain Academy|LangChain Academy]]：提升 LangChain 技能的课程和练习。

- [[02-Case Studies|案例研究]]：了解团队如何在生产中使用 LangChain 和 LangGraph。

- [[03-Get Help|获取帮助]]：连接 LangChain 社区、学习资源和支持渠道。
