---
title: Retrieval 与 RAG 组件
aliases:
  - LangChain Retrieval and RAG
tags:
  - langchain
  - retrieval
  - rag
source_checked: 2026-07-14
---

# Retrieval 与 RAG 组件

## 本节目标

把 RAG 拆成可验证的数据管线，理解 LangChain 中 Document、loader、splitter、embedding、vector store、retriever 与 Agent 工具之间的关系，并能判断 2-step RAG 和 Agentic RAG 的取舍。

## Retrieval 解决什么

模型参数中的知识不等于你的最新私有资料。检索先根据问题找到外部知识片段，生成再依据片段回答。LangChain 提供统一组件和集成，但框架不会自动修复坏 PDF、错误切分、缺失权限或过时索引。

```text
离线：资料 -> 解析 -> 清洗 -> 切分 -> 元数据 -> Embedding -> 索引
在线：问题 -> 查询处理 -> Retriever -> 候选片段 -> 排序/过滤 -> 生成 -> 引用校验
```

每一箭头都应能独立观察和评测。先在 5～20 篇可人工检查的文档上跑通，再扩大数据量。

## LangChain 组件地图

- **Document loader**：把文件或服务读成 Document；读取成功不代表版面语义正确。
- **Text splitter**：按长度、结构或语义切片；chunk size 是实验参数，不是固定答案。
- **Embedding model**：把文本映射为向量；模型和归一化方式必须版本化。
- **Vector store**：保存向量和元数据并执行相似度查询；不同实现的过滤能力不同。
- **Retriever**：给定文本查询返回 Document，是比 vector store 更通用的读取接口。
- **Reranker / 规则过滤**：重排候选并应用权限、时间或来源约束。
- **Tool**：把检索能力暴露给 Agent；模型决定何时调用时，循环会更动态。

LangChain v1 将部分历史 retriever 和 indexing API 移到 `langchain-classic`，但核心 Retriever 接口仍由 `langchain-core` 定义。看到旧导入路径时，应先查迁移指南和当前集成页。

## 元数据先于向量库选型

每个片段至少考虑：

```json
{
  "chunk_id": "policy-v3-section-4-chunk-02",
  "document_id": "policy-v3",
  "title": "退款政策",
  "section": "4. 特殊情形",
  "version": "3",
  "effective_at": "2026-06-01",
  "access_scope": "support-team",
  "source_path": "policies/refund-v3.md"
}
```

权限过滤应在检索执行层实现，不要先检出无权内容再要求模型“忽略”。文档撤回和版本更新也依赖稳定 ID 与可删除索引。

## 2-step RAG 与 Agentic RAG

| 方案 | 数据流 | 优点 | 主要风险 |
| --- | --- | --- | --- |
| 2-step RAG | 固定检索一次，再生成一次 | 延迟和路径可预测，易评测 | 复杂问题可能需要查询改写或多跳 |
| Agentic RAG | 模型决定何时、如何、多次检索 | 灵活处理开放任务 | 循环、成本、遗漏检索和工具误用 |
| Hybrid | 确定性检索为主，必要时进入 Agent | 保留基线又允许升级 | 路由条件和两套轨迹需评测 |

官方 Retrieval 页面把 RAG Agent 和 2-step chain 都列为教程路径。工程建议是先建立 2-step 基线：只有数据证明固定检索不足时，才引入动态循环。

## 分层评测

1. **解析**：标题、表格、页码和段落是否保留？
2. **切分**：答案证据是否落在可用片段，是否被截断？
3. **检索**：Recall@k、MRR/nDCG 或人工命中，权限过滤是否正确？
4. **生成**：答案是否被证据支持、引用是否真实、无答案时是否拒答？
5. **系统**：索引版本、延迟、成本、失败率和数据新鲜度。

测试集至少覆盖：库中可答、多片段、库中无答案、过时版本、权限不允许、同义查询、拼写错误和带提示注入的恶意文档。生成流畅不能补救检索为空。

## 常见错误与排查

- 召回差就换向量数据库：先抽查解析和 chunk，再比较 embedding 与查询。
- 检索结果无来源 ID：无法引用、撤回和定位错误。
- 把片段放进 system message：外部文本获得了不应有的指令优先级。
- 索引更新不记录版本：线上问题无法复现。
- 只评最终答案：不能知道失败来自检索还是生成。

## 动手实践

选 5 篇本地 Markdown，人工设计 15 个问题和期望文档。先不接模型：实现关键字基线，记录 top-3 命中与错误；再为每个片段增加 `document_id`、section、version 和 access_scope。最后写出“无命中”和“权限过滤后无结果”的确定性响应。

## 自测

- [ ] 能画出索引阶段与查询阶段，并指出每层可测指标。
- [ ] 能解释 retriever 比 vector store 更一般的原因。
- [ ] 能说明 2-step RAG 相对 Agentic RAG 的工程优势。
- [ ] 能设计不会把未授权片段送入模型的过滤位置。

## 下一步

进入 [[LangChain/00-初学者路线/05-Memory State与Persistence|Memory、State 与 Persistence]]，区分检索知识、运行状态和长期记忆。

## 资料基线

官方事实核对日期：2026-07-14。

- [LangChain Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval)
- [LangChain v1 迁移指南](https://docs.langchain.com/oss/python/migrate/langchain-v1)
- [langchain-core Retriever API 概述](https://reference.langchain.com/python/langchain-core/langchain_core)
- [[LangChain/02-LangChain/01-Semantic Search|既有官方案例：Semantic Search]]
- [[LangChain/02-LangChain/02-RAG Agent|既有官方案例：RAG Agent]]
- [[RAG/00-目录|RAG 原理与系统路线]]
