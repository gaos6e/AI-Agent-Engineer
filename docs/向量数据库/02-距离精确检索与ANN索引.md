---
title: 距离、精确检索与 ANN 索引
tags:
  - ai-agent-engineer
  - vector-database
  - ann
  - hnsw
aliases:
  - ANN Index Basics
  - 向量索引
source_checked: 2026-07-14
source_baseline: "HNSW/Faiss 原始论文及 Faiss、pgvector 官方资料截至 2026-07-14"
---

# 距离、精确检索与 ANN 索引

## 本节目标

你将区分 similarity 与 distance、exact kNN 与 ANN；理解 HNSW、IVF 和量化的基本机制；会以 exact top-k 为近似误差基线，并把真实 filter、写入和硬件纳入实验。

## 先统一“越大越相似”还是“越小越近”

常见 metric：

### Cosine similarity

$$
\operatorname{cos}(x,y)=
\frac{x\cdot y}{\lVert x\rVert_2\lVert y\rVert_2}
$$

越大越相似，零向量无定义。

### Dot product

$$
x\cdot y=\sum_i x_i y_i
$$

越大越相似；未归一化时模长会影响分数。

### Euclidean distance

$$
d_2(x,y)=\sqrt{\sum_i(x_i-y_i)^2}
$$

越小越近。API 有时返回 distance，有时返回负距离或 similarity score；应用必须读当前官方文档，不能只看字段名 `score`。

在单位向量上，cosine、dot 和 Euclidean distance 的排序等价；非单位向量不一定。Metric 与 normalization 必须和 `[[Knowledge/AI Agent Engineer/docs/Embedding/00-目录|Embedding]]`空间契约一致。

## Exact kNN

给定授权候选集合 $D$，逐一计算 query 与每个 vector 的分数，再取 top-k。它的优势：

- 在给定 metric、filter 和 tie-breaking 下确定；
- 没有 ANN 近似遗漏；
- 容易作为小规模单元/离线质量基线；
- 能验证量化、过滤和索引参数造成的差异。

它仍不保证业务相关：exact 最近的 vector 可能不是人工 gold。Exact 只消除了“索引近似”这一层误差。

当 $N$、维度或 QPS 增大，逐项计算的 CPU/内存带宽代价可能超过 SLO，于是使用 ANN。

## 两种 Recall 不要混淆

### ANN Recall@k

同一空间、同一 filter、同一 query：

$$
\operatorname{ANNRecall@k}
=
\frac{|ANN_k\cap Exact_k|}{k}
$$

它问“近似索引找回多少 exact 邻居”。

### Business Recall@k

$$
\operatorname{BusinessRecall@k}
=
\frac{|Retrieved_k\cap Relevant|}{|Relevant|}
$$

它问“找回多少人工/行为相关证据”。

ANN Recall 1.0 但业务 Recall 很低，说明表示或 gold 不匹配；业务 Recall 足够而 ANN Recall 略低，可能是遗漏的 exact 邻居本来就不相关。两者都报告。

## HNSW 直觉

Hierarchical Navigable Small World（HNSW）构建多层近邻图：

1. 高层节点较稀疏，用于大步导航；
2. 查询从入口点开始向更近邻居移动；
3. 逐层下降到密集底层；
4. 在候选搜索范围内返回近邻。

常见实现暴露类似：

- 图连接度（常见名 `M`）：更高通常增加内存/构建与连通机会；
- 构建候选范围（常见 `ef_construction`）；
- 查询候选范围（常见 `ef_search`）：更大通常提高 recall，也增加延迟。

“通常”不是单调保证；数据分布、过滤、删除、并发和实现会影响。参数名、合法范围、默认和是否可在线修改必须查锁定产品版本。

HNSW 常见优势是查询性能和无需先训练 coarse centroids；代价包括图内存、构建时间、动态更新/删除维护和冷启动。

## IVF 直觉

Inverted File Index（IVF）先训练 coarse quantizer，把向量分配到多个 cell/list：

1. 训练 centroids；
2. 每个 document vector 进入最近列表；
3. Query 先找相近 centroids；
4. 只扫描若干列表的候选。

常见参数：

- 列表数（Faiss 常见 `nlist`）；
- 查询探测列表数（`nprobe`）。

探测更多列表通常提高 ANN recall，同时增加工作。训练样本若不代表生产分布，cell 不平衡或召回可能变差；新增数据分布漂移也需监控。

pgvector 当前提供 HNSW 与 IVFFlat，并说明二者在构建、查询和内存/训练上的不同；具体 operator class、参数和版本能力以仓库文档为准。

## Product Quantization 与压缩

Product Quantization（PQ）把向量分成子空间，用 codebook 近似每段，从而减少内存和距离计算带宽。其他系统还可能支持 scalar、binary 或 float16/half precision。

压缩引入单独误差层：

```text
business relevance
  <- embedding representation
  <- dimension reduction
  <- dtype / quantization
  <- ANN traversal
  <- filtering / top-k
```

先保存 full-precision exact baseline，再逐层加入降维、量化和 ANN，才能定位退化。不要同时换模型、PQ、索引和 filter 参数后只报一个总分。

## Filter 会改变 ANN 工作负载

如果先得到全局 ANN top-k 再 post-filter，授权结果可能不足；如果 filter 集成在 traversal 中，选择率和图连通会影响搜索；如果先构造过滤候选，极小集合可能直接 exact 更合适。

pgvector 当前文档说明 approximate index 查询中 filter 的执行与 PostgreSQL planner/scan 相关，并提供 iterative scan 能力；Qdrant 等专用系统有自己的 filter-aware 机制。产品策略不同，必须用同一 filter 在 exact 与 ANN 两侧建立可比较候选集合。

## 索引生命周期

索引不只有查询：

- 建索引时 CPU、内存、磁盘和写入影响；
- 新写入何时可搜索；
- 批量导入先写后建还是边写边建；
- 删除是否留下 tombstone，何时回收；
- 更新是否造成图/列表碎片；
- 崩溃恢复是否重建；
- 扩容/迁移是否传输索引或在目标重建；
- 参数修改是否在线生效。

Benchmark 只测 steady-state read QPS 会漏掉大部分生产代价。

## 可复现 ANN 实验

### 数据

- 真实 document vectors 和 query vectors；
- 固定 space contract 与 snapshot/hash；
- query/gold 子组；
- 高频与低选择率 filters；
- 真实更新/删除比例。

随机高斯向量可做功能/压力 sanity check，不能替代生产几何。

### Exact ground truth

对每个 query、每个 filter 先跑 exact top-k，保存 IDs、metric、tie 规则。若 corpus 太大，可用代表性子集或离线分片合并，但方法必须记录。

### 固定环境

- 产品/库与配置版本；
- CPU/GPU、RAM、磁盘、文件系统；
- 单/多线程、并发和连接池；
- 冷启动/预热方式；
- index build 参数和 query 参数；
- 数据量、维度、filter 分布；
- 重复轮次和时间窗口。

### 报告

| 质量 | 查询 | 构建/写入 | 资源 |
| --- | --- | --- | --- |
| ANN Recall@k、业务 Recall/MRR/nDCG | P50/P95/P99、QPS、timeout | build time、upsert/delete latency、searchable lag | RAM、disk、CPU/GPU、网络 |
| 子组和过滤选择率 | cold/warm、并发曲线 | 写入期间读退化、rebuild | 峰值而非只报均值 |

Latency 图应说明是否包含网络、序列化、filter 和 rerank；否则不同报告不能比较。

## 常见错误与排查

- **QPS 高但找错**：先看 ANN/business recall 与 gold。
- **Exact 与 ANN filter 不同**：ground truth 不可比。
- **只记录 query 参数**：索引构建参数和数据 snapshot 也决定结果。
- **随机向量得出产品结论**：换真实语料/查询/过滤分布。
- **索引建完后写入变慢**：加入 mixed read/write workload。
- **删除后内存不降**：查 tombstone/compaction/重建语义。
- **照抄另一产品 `ef/nprobe`**：回到当前实现文档。
- **新模型继续用旧阈值**：分数刻度与空间已变。

## 练习

1. 用 100 个小向量手写 exact cosine top-5，并把它作为 ANN fixture。
2. 设计 HNSW 三档 query candidate 范围实验，固定其余参数，画 Recall@10—P95 曲线。
3. 为 IVF 写出训练集选择、list 数、probe 数和分布漂移检查。
4. 构造 1%、10%、80% 三种 filter 选择率，分别比较 exact/ANN 返回数量与延迟。
5. 设计 full float → reduced dimension → quantized → ANN 的分层实验。
6. 解释“ANN Recall 下降但业务 nDCG 不变”可能意味着什么。

## 掌握检查

- [ ] 我明确 score/distance 的方向和 metric 契约。
- [ ] Exact top-k 只消除索引近似，不等于业务真值。
- [ ] 我区分 ANN Recall 与 business Recall。
- [ ] 我能解释 HNSW 图搜索、IVF coarse lists 与 PQ 压缩。
- [ ] 参数名和默认值只引用锁定产品版本。
- [ ] Filter、写入、删除、构建和恢复进入 benchmark。
- [ ] 模型、维度、量化和 ANN 分层测试，结果可归因。

## 小结与下一步

ANN 解决“更快找近邻”，但只有在 tenant/ACL/business filter 正确时结果才可用。下一步：`[[Knowledge/AI Agent Engineer/docs/向量数据库/03-过滤与多租户|过滤与多租户]]`。

## 参考资料

- [Malkov & Yashunin, HNSW](https://arxiv.org/abs/1603.09320)
- [Johnson, Douze & Jégou, Billion-scale similarity search with GPUs](https://arxiv.org/abs/1702.08734)
- [Faiss official repository](https://github.com/facebookresearch/faiss)
- [pgvector official repository](https://github.com/pgvector/pgvector)

来源获取日期：2026-07-14。返回 `[[Knowledge/AI Agent Engineer/docs/向量数据库/00-目录|向量数据库目录]]`。
