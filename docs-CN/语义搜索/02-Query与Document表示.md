---
title: "Query 与 Document 表示"
tags:
  - ai-agent-engineer
  - semantic-search
  - embedding
aliases:
  - 不对称检索表示
  - Asymmetric Retrieval
source_checked: 2026-07-14
source_baseline: "DPR、SPLADE、ColBERT 原始论文及 Sentence Transformers 官方语义搜索文档截至 2026-07-14"
lang: zh-CN
translation_key: 语义搜索/02-Query与Document表示.md
translation_route: en/semantic-search/02-query-and-document-representations
translation_default_route: zh-CN/语义搜索/02-Query与Document表示
---

# Query 与 Document 表示

## 本节目标

同一段文本可以变成词项、稀疏权重、单个稠密向量或多个 token 向量。本节不急着选模型，而是先明确每种表示保存了什么、丢掉了什么，以及 query 端与 document 端必须共享哪些契约。

## 词面表示从 analyzer 开始

关键词检索不是“直接比较原字符串”。Analyzer 通常执行 Unicode/大小写规范化、分词、可选词形处理、停用词和同义词策略，最终产生词项。中文、英文、错误码和型号需要不同判断：

- E042、RTX-5090 等标识符应尽量保持整体；
- 中文可从字、词或 n-gram 起步，但颗粒度会改变文档频率和噪声；
- 金额、日期、版本和否定词不能被随意删除；
- query analyzer 与 index analyzer 不一定完全相同，但必须锁定并测试兼容性；
- analyzer 变更会改变索引与分数，通常需要重建或新版本索引。

BM25 读取的是词项频率、包含该词项的文档数和文档长度。分词错误会直接变成召回错误，不能靠调 BM25 参数弥补。

## 对称与不对称任务

| 任务 | Query | Document | 是否可互换 |
| --- | --- | --- | --- |
| 相似问题 | 一句问题 | 另一句问题 | 通常近似对称 |
| 论文相似性 | 标题与摘要 | 标题与摘要 | 通常近似对称 |
| 问答检索 | 短问题/关键词 | 能回答问题的段落 | 不对称 |
| 商品搜索 | 用户措辞 | 标题、属性、描述 | 不对称 |

RAG 多数是短 query 找较长证据 passage，因此是 asymmetric retrieval。Dense Passage Retrieval 使用双编码器分别编码 query 与 passage；它们进入兼容比较空间，但输入角色和编码路径不应随意互换。

当前 Sentence Transformers 官方文档为不对称语义搜索提供 encode_query 与 encode_document 入口，并说明模型可能使用 query/document prompt 或任务路由。这个行为属于当前库与模型事实；其他 SDK 或模型的角色约定必须查其 model card，不应照抄函数名。

## Dense 表示契约

Document 离线编码与 query 在线编码至少共同锁定：

| 字段 | 为什么需要 |
| --- | --- |
| model/provider/revision | 同名模型也可能更新权重或服务行为 |
| query/document role | 决定前缀、prompt 或路由 |
| tokenizer 与最大长度 | 决定哪些内容被保留 |
| input template | 标题、路径、正文和字段标签如何拼接 |
| truncation | 从头/尾截断、滑窗或分段策略 |
| pooling | token 表示如何变成单向量 |
| dimension/dtype | 存储与计算契约 |
| normalization | 决定 dot 与 cosine 的关系 |
| metric | cosine、dot 或 L2 的排序方向 |
| language/domain | 训练覆盖不等于本地任务表现 |

只检查 dimension 不够：两个 768 维模型的坐标系也可能完全不同。迁移时使用新 space/collection，双读比较后显式切换，不能把新旧向量混排。

## Document 输入怎么组织

一个 passage 往往需要标题或层级才能消解主语：

```text
title: 退款规则
section: 到账时间
content: 审核通过后通常在一至三个工作日原路返回。
```

这不是通用最佳模板。要通过消融比较正文 only、标题 + 正文、路径 + 标题 + 正文。重复的站点导航、版权声明和统一模板可能支配表示；应在解析或 Chunking 阶段清理。

长文被 tokenizer 截断时，尾部答案可能永远没有进入向量。记录 token 数、截断比例和被截断字段；若比例高，先调整 chunk，而不是假设模型“理解了整篇”。

## Query 输入怎么组织

Query 端优先保存：

- original query；
- 规范化版本；
- 每个 rewrite/subquery 及其父 query；
- 使用的会话字段、时间与身份；
- query encoder revision、输入长度和是否截断；
- 超时、降级和缓存命中。

领域缩写可以扩展，但数字、专名、否定和时间条件应原样保留。LLM 改写可能让“不要自动续费”变成“自动续费”，因此原 query 通道必须能独立运行并作为降级路径。

## Sparse、dense 与 multi-vector

- **BM25/传统 sparse**：词项可解释、适合精确标识符；同义改写可能没有共享词；
- **学习式 sparse**：模型给词表维度赋权，可做语义扩展并使用倒排结构；行为仍依赖训练与词表；
- **single dense vector**：存储与检索简单，但把整段压到一个向量会丢局部匹配；
- **multi-vector/late interaction**：保留多个 token/片段向量，能表达细粒度交互，但存储、查询和重排成本更高。

SPLADE 是学习式 sparse 的研究代表，ColBERT 是 late interaction 的研究代表。它们是进阶候选，不是“更复杂所以一定更好”；先用 BM25 与单向量基线定位失败类型。

## Toy fixture 的边界

[[语义搜索/examples/semantic-search-fixture.json|项目 fixture]] 使用 7 维手工一热向量：退款、重复扣款、上传、网络等主题由人直接指定维度。它能稳定演示“词面漏召回、dense 命中”和 RRF，但没有训练、tokenizer、跨语言或真实泛化能力。

迁移到真实模型时必须替换：

1. 手工 document/query vectors；
2. representation name/revision/dimension；
3. 编码批处理与缓存；
4. exact 线性扫描；
5. 用真实 query/qrels 重跑所有指标。

## 常见错误与排查

- **Query/document 使用相反角色**：核对 model card 与编码调用日志；
- **离线文档更新、在线 query 仍用旧 revision**：门禁 space signature；
- **标题重复导致所有向量相似**：做字段消融并检查近邻；
- **长文本静默截断**：记录 token 数和截断率；
- **语言覆盖靠宣传页推断**：按语言分层评测；
- **更换模型只看 cosine 分布**：重建 qrels 指标，旧分数不可直接比较。

## 练习

为“VPN 连不上”检索 300 字排障段落设计表示协议：

1. 写 query/document input template；
2. 说明 VPN、错误码、版本号如何被 analyzer 保留；
3. 定义模型 revision、角色、最大长度、截断、归一化和 metric；
4. 比较正文 only 与标题 + 正文；
5. 构造 5 个同义 query、3 个数字/否定 hard negatives；
6. 写出模型升级的双空间切换与回滚条件。

## 掌握检查

- [ ] 我能判断任务是对称还是不对称。
- [ ] Sparse analyzer 与 dense encoder 都有可重放版本。
- [ ] Query/document 角色、模板与截断不是隐含默认。
- [ ] 模型兼容性不只由维度判断。
- [ ] 我知道 single vector、learned sparse、late interaction 的责任与成本差异。
- [ ] Toy vectors 不被宣称为真实 Embedding 结果。

下一步：[[语义搜索/03-相似度分数与阈值|相似度、分数与阈值]]。

## 参考资料

- Karpukhin et al., [Dense Passage Retrieval](https://arxiv.org/abs/2004.04906)
- Formal et al., [SPLADE v2](https://arxiv.org/abs/2109.10086)
- Khattab & Zaharia, [ColBERT](https://arxiv.org/abs/2004.12832)
- [Sentence Transformers: Semantic Search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)

来源获取日期：2026-07-14。返回 [[语义搜索/00-目录|语义搜索目录]]。
