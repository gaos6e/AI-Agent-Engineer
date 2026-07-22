---
title: 多模态、Embedding 与专用模型
tags:
  - llm
  - multimodal
  - embedding
aliases:
  - 多模态模型选择
  - Embedding 模型选择
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
---

# 多模态、Embedding 与专用模型

## 本节目标

根据流水线角色选择生成、感知或 embedding 模型，避免用一个通用总分替代端到端任务证据。

## 核心概念

多模态系统不是一个“是否支持图片”的布尔值，而是一条可能包含 OCR/ASR、视觉理解、生成、embedding、reranking 和业务验证的流水线。每个模型要按它改变的接口评测：

- 图像/文档：分辨率、页数、版面、表格、旋转、文字语言和引用坐标；
- 音频：噪声、口音、重叠、时间戳、流式延迟和打断；
- 视频：采样、时序、长片段、音画关系和成本；
- embedding：query/document 约定、语言、领域、向量维度、归一化、最大输入和版本迁移。

Embedding 是检索或聚类组件，不应用生成模型的流畅度指标评估。MTEB 覆盖多种 embedding 任务且原始研究未发现一种方法统治所有任务，这正是“按任务选”的证据。

## 为什么需要

单页截图 demo 不能证明多页 PDF、低清扫描和表格可靠；语义相似度高也不能证明你的检索 top-k 命中权限正确的证据。流水线中上游错误还会被下游语言模型掩饰为流畅答案，必须保留分层指标。

## 怎样实现

1. 画出输入到 outcome 的阶段和中间契约；
2. 为每层准备真实分布、困难切片与拒绝样本；
3. 分别测感知正确性、检索质量、引用/定位和端到端成功；
4. 记录预处理、压缩、采样、embedding 前缀、维度和相似度函数；
5. 版本升级时先双写/回填索引，不能直接混用不同 embedding 空间。

Embedding 候选至少在私有 query–corpus–relevance 集上报告 Recall@k、MRR/nDCG、无结果、延迟、吞吐、索引体积和重建成本。公开 MTEB/VHELM 可用于发现候选和设计切片，但不能代替私有评测。

## 常见失败

- 把“多模态输入”理解为所有文件类型、大小和语言都等价。
- 只看最终答案，不保存 OCR/ASR/检索中间证据。
- 用 STS 分数直接选择 RAG embedding。
- 更换 embedding 后复用旧向量，造成不可解释的距离。
- 忽略图片 token、音频时长、视频采样带来的成本与尾延迟。

## 怎样验证

做层级消融：固定下游、替换上游；再固定上游、替换下游。若最终质量变化无法由中间指标解释，检查数据对齐、缓存和 harness，而不是立刻归因于模型。

## 实践任务

从真实知识库抽取 30 个 query，标注相关文档和不可回答项。比较两个 embedding 候选的 Recall@5、nDCG@10、p95 延迟和索引体积；再抽查 top-k 是否受切分、语言或权限过滤影响。

## 参考资料

- Muennighoff 等，[MTEB](https://aclanthology.org/2023.eacl-main.148/)
- Stanford CRFM，[VHELM](https://crfm.stanford.edu/helm/vhelm/v2.0.0/)
- [[Embedding/00-目录|本库：Embedding]]
- [[多模态AI/00-目录|本库：多模态 AI]]
