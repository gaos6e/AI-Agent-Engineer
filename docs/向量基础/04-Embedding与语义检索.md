---
title: Embedding 与语义检索
tags: [ ai-agent-engineer, 向量, Embedding, retrieval ]
aliases: [ 向量语义检索 ]
source_checked: 2026-07-14
source_baseline:
  - Google Machine Learning Crash Course embeddings
  - Google Measuring Similarity from Embeddings
---

# Embedding 与语义检索

## 本节目标

把“对象→向量→候选→过滤/精排→评测”串成可审计链路，理解分数、top-k、阈值、模型版本和相关性标签分别解决什么问题。

## 从对象到向量

Embedding 模型 $f$ 把文本、图片或其他对象映射到固定维向量：

$$v=f(object)\in\mathbb R^d$$

训练目标让任务上相似对象在所选几何中更近。Embedding 不是原文压缩包，无法可靠还原全部内容；它保留的是训练目标偏好的关系。

## 最小检索流程

1. 确定模型与版本；
2. 按模型要求预处理文档并生成向量；
3. 保存向量、文档 ID、版本和可过滤元数据；
4. 用同一兼容模型处理 query；
5. 按匹配度量取 top-k；
6. 应用权限/业务过滤；
7. 可用 reranker 精排；
8. 用标注相关集评测。

query/document 可能需要不同前缀或不同 encoder，必须遵守模型说明。“都转向量”不等于调用方式相同。

## top-k 与阈值

top-k 固定候选数量，阈值固定最低分数。top-k 在无相关文档时仍返回结果；阈值可能一个也不返回。常结合：先取较大的候选 k，再经阈值、元数据和 reranker 筛选。

阈值需基于代表性相关/不相关对校准，并随着模型、chunking 和语料变化重新评测。原始 cosine 不是概率。

## 最小评测

对每个 query 有相关文档集合 $R_q$，返回前 $k$ 个 $S_q^k$：

$$Recall@k=\frac{|R_q\cap S_q^k|}{|R_q|}$$

若只标一个答案文档，Recall@k 退化为它是否进入 top-k。还可看 Precision@k、MRR、nDCG；选择取决于是否多相关、排序重要性和标注完整度。

当 $R_q$ 为空时，上式分母为 0，不能静默记作满分或零分。评测方案应预先决定：把“无相关文档”查询单独评估拒答/空结果能力，或从该项 Recall 聚合中排除并单独报告数量。

## 版本与迁移

更换 embedding 模型/维度通常需要重新嵌入语料并建新索引。不要把不同空间的向量混在同一索引。迁移应双写或建新版本，离线比较检索质量，再灰度切流，并保留回滚。

## 风险与常见误区

- 语义相似不等于事实正确、时间最新或权限可见。
- chunk 过大/过小都会影响向量代表性；这是 Chunking 与 RAG 的共同问题。
- 只展示几个“看起来不错”的 query，不构成评测。
- 向量库元数据缺模型版本，未来无法重建与排查。
- 对敏感原文生成向量不等于匿名化；隐私与访问控制仍需治理。

## 练习与自测

1. 为每条向量设计最低元数据：document/chunk ID、模型、版本、维度、生成时间、内容哈希。
2. 构造 5 个 query 的相关集合，手算 Recall@1 与 Recall@3。
3. 说明何时选择“无结果”比强行返回 top-k 更安全。

- [ ] 我能画出 embedding 检索全链路。
- [ ] 我知道模型迁移需重新建空间。
- [ ] 我会用标注集选择 k/阈值，而非凭感觉。

## 参考资料

- [Google ML Crash Course: Embeddings](https://developers.google.com/machine-learning/crash-course/embeddings)
- [Google: Embedding space](https://developers.google.com/machine-learning/crash-course/embeddings/embedding-space)
- [Google: Measuring Similarity from Embeddings](https://developers.google.com/machine-learning/clustering/dnn-clustering/supervised-similarity)

资料核验日期：2026-07-14。下一步：[[向量基础/05-项目-最小向量检索器|项目：最小向量检索器]]。
