---
title: Cross-Encoder 重排
tags:
  - ai-agent-engineer
  - reranking
  - cross-encoder
aliases:
  - 交叉编码器重排
  - Cross Encoder Reranker
source_checked: 2026-07-14
source_baseline: "BERT/monoT5/RankT5 原始论文及 Sentence Transformers、Elasticsearch 官方资料截至 2026-07-14"
---

# Cross-Encoder 重排

## 本节目标

理解 Cross-Encoder 为何能细看 query—document 关系、为何不能直接扫描全库，以及输入截断、输出语义、批处理和服务化如何决定实际质量。完成后你应能写出一个可回放的 cross-encoder 推理契约。

## Bi-Encoder 与 Cross-Encoder

| 维度 | Bi-Encoder | Cross-Encoder |
| --- | --- | --- |
| 输入 | query/document 分别编码 | query 与一篇 document 联合输入 |
| 文档计算 | 可离线缓存向量 | 每个 query—document pair 实时计算 |
| token 交互 | 编码后只比较向量 | Transformer 内直接跨文本交互 |
| 典型角色 | 大规模 first-stage 召回 | 有限窗口精排 |
| 主要瓶颈 | 索引/ANN 与表示质量 | pair 数、token、批处理和推理队列 |

Cross-Encoder 可能更好地区分否定、数字、词序和局部证据，但“通常更强”不是目标语料保证。模型训练域、语言、文本长度和 qrels 定义不匹配时，重排也会退化。

## 输入构造

一个可追溯模板可以是：

```text
[QUERY] 退款审核通过后多久到账
[TITLE] 退款到账时间
[BODY] 退款审核通过后通常在一至三个工作日原路返回。
```

需锁定：

- model/provider/revision 与 tokenizer revision；
- query/title/body/metadata 的顺序、分隔符和字段标签；
- 最大 token 数、特殊 token 和 padding；
- query 与 document 各自 token 预算；
- truncation 方向或 chunking/滑窗策略；
- 输入规范化、语言与 source revision；
- batch size、dtype、device 和推理库版本。

把 tenant、ACL 或系统 prompt 拼成自然语言不会替代服务端过滤。无关 metadata 还会消耗窗口并改变模型行为。

## 截断是隐形召回

模型只能判断送入 token window 的文本。若答案位于文档尾部而被截断，Cross-Encoder 会把“已召回正例”变成“模型从未看见证据”。监控：

- query/body token 分布；
- 截断比例和被截断字段；
- 正例答案 span 是否保留；
- 文本长度与 nDCG/错误的关系。

优先让 first stage 返回可引用 passage。对必须处理的长文，可滑窗评分并聚合，但 max/mean/top-m 都会改变偏差，见 [[Reranking/04-候选窗口长文与多样性|候选窗口、长文与多样性]]。

## 输出分数是什么

模型可能输出：

- 二分类 logit；
- sigmoid 后概率；
- 回归 relevance score；
- true/false token 的生成分数；
- 多等级类别概率。

其语义由训练目标决定。Logit 可用于同 query 排序，不自动是跨 query 概率；sigmoid 也只有在数据分布和校准成立时才可解释。阈值应在独立 validation 集按 query 类型、语言和错误成本校准，模型升级后重做。

排序必须定义：

1. 分数越大还是越小越优；
2. 缺失/错误分数如何处理；
3. 平局使用 first-stage rank、稳定 ID 还是其他键；
4. 是否允许模型淘汰候选；
5. 输出必须覆盖全部输入 ID 还是允许 partial。

## 批处理与动态 batching

候选 window 为 w，就有 w 个 pairs。批量推理能提高 GPU/CPU 利用率，但会引入：

- 等待组 batch 的排队延迟；
- 长短文本 padding 浪费；
- 显存峰值和 OOM；
- 单个大请求拖慢同批其他 query；
- timeout 后已完成计算被浪费。

基准应覆盖不同 window、token 长度、并发和 batch policy，报告模型计算、队列、序列化/网络和端到端 p50/p95/p99。单 batch 吞吐不能代表在线尾延迟。

## 服务化契约

请求至少包含 request/query ID、模型 revision、query、候选 ID 与文本、deadline 和 schema version；响应包含每个 ID 的有限 score、可选 label/reason、model revision、耗时和错误。

客户端校验：

- HTTP/传输成功不等于业务输出有效；
- ID exact set、唯一性和数量；
- 分数类型与有限性；
- 响应 model/schema revision；
- deadline 剩余时间；
- 日志中不暴露不必要正文或凭据。

重试只适用于明确可重试错误，并受总 deadline/幂等和容量限制。Rerank 是纯评分时重复请求通常不改变外部状态，但会重复计费和占资源。

## 当前库/产品事实如何使用

Sentence Transformers 当前 CrossEncoder 文档提供 predict/rank 等本地推理入口，并有专门 reranking 示例。Elasticsearch 当前 semantic reranking 文档描述有限 rank window、cross-encoder 推理端点和长文处理选项。它们适合作为实现案例，不代表所有模型的 score 可跨 query 比较，也不保证默认 truncation 适合你的 corpus。

## 常见错误与排查

- **模型看不到答案 span**：记录 token/span，改 passage 或分块；
- **训练模板与线上模板不同**：冻结模板 checksum；
- **分数方向反了**：用已知正/负 pair 单测；
- **只测单请求平均延迟**：加入并发、动态 batch 和 p99；
- **输出漏 ID 仍继续**：触发 invalid-output fallback；
- **跨 query 共用任意阈值**：在目标分布校准；
- **模型升级只看离线均值**：检查关键切片、延迟和 fallback 容量。

## 练习

设计一条 bi-encoder 召回 100、Cross-Encoder 重排 30、输出 8 的管线：

1. 写 query/title/body 模板和 token 预算；
2. 构造答案位于头/中/尾的长文测试；
3. 明确 output score 语义与 tie-break；
4. 设计 batch size × window × token length 基准；
5. 写空、重复、未知、NaN 和 revision mismatch 校验；
6. 定义 timeout、重试和安全 fallback。

## 掌握检查

- [ ] Bi-Encoder 与 Cross-Encoder 的缓存和计算边界清楚。
- [ ] 输入模板、tokenizer、截断和模型版本可回放。
- [ ] 分数语义来自训练目标，不被猜成概率。
- [ ] 批处理同时评估吞吐、队列和尾延迟。
- [ ] Provider 输出经过 exact ID/有限数值/schema 校验。
- [ ] 长文与模型升级有分层回归和 fallback。

下一步：[[Reranking/03-LLM规则与组合重排|LLM、规则与组合重排]]。

## 参考资料

- Nogueira & Cho, [Passage Re-ranking with BERT](https://arxiv.org/abs/1901.04085)
- Nogueira, Jiang & Lin, [monoT5](https://arxiv.org/abs/2003.06713)
- Zhuang et al., [RankT5](https://arxiv.org/abs/2210.10634)
- [Sentence Transformers: CrossEncoder API](https://www.sbert.net/docs/package_reference/cross_encoder/model.html)
- [Sentence Transformers: Cross-Encoder Applications](https://www.sbert.net/examples/cross_encoder/applications/README.html)
- [Elasticsearch: Semantic reranking](https://www.elastic.co/docs/solutions/search/ranking/semantic-reranking)

来源获取日期：2026-07-14。返回 [[Reranking/00-目录|Reranking 目录]]。
