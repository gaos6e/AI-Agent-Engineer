---
title: Overlap、元数据与上下文
tags:
  - ai-agent-engineer
  - chunking
  - metadata
  - security
aliases:
  - Chunk Overlap
  - Chunk 元数据
source_checked: 2026-07-14
source_baseline: "Unstructured、Azure AI Search 与 Anthropic 官方资料截至 2026-07-14"
---

# Overlap、元数据与上下文

## 本节目标

你将理解 overlap 只解决边界附近的一类问题，并会计算其重复成本；随后建立一套把原文、检索上下文、来源位置、权限与版本分开的 chunk 契约。

## Overlap 解决的是边界风险

假设一句条件恰好在固定窗口边界被切开，两个块都可能缺少完整证据。让下一窗口重复上一窗口尾部，可以提高至少一个块覆盖完整条件的机会。

它不解决：

- 原文根本没有答案；
- 解析顺序错误；
- 标题或表头丢失；
- embedding 不适配查询；
- ACL 过滤错误；
- 需要跨很远章节综合的查询。

结构边界干净时，overlap 甚至会把上一主题带入下一主题。Unstructured 当前默认只对被硬切的超长元素使用 overlap；也允许配置为所有块重叠，但其文档明确提示这可能带来意外行为。应把这种默认值当作实现事实，而不是普遍最优结论。

## 重复成本怎么算

若来源长度为 $L$，窗口大小 $S$、overlap 为 $O$，stride 是 $S-O$。实际重复单位数最可靠的计算是：

$$
D=\sum_{i=1}^{N}\operatorname{units}(chunk_i)-L
$$

重复率可写为：

$$
R_{\text{dup}}=\frac{D}{L}
$$

不要简单用 `overlap / size` 代替真实重复率，因为最后一块可能较短，结构策略也可能只对少数超长元素重叠。

本库 fixture 在当前默认配置下：

- 结构策略只对超长 element 使用 overlap，正文重复率约 0.0319；
- 固定窗口对连续来源使用 overlap，正文重复率约 0.0956。

这些数值只描述本地样例，不证明结构策略在其他数据上必然更省或更准。

## 重复召回与上下文去重

高度相似的相邻块可能占满 top-k。常见处理顺序：

1. 权限与 metadata 过滤；
2. 候选召回；
3. rerank；
4. 按 source/parent/overlapping spans 合并或去重；
5. 在模型预算内打包上下文。

去重时不能只比较字符串相似度。两个块文字相近但来源、版本或 ACL 不同，不应合并；同一来源的相邻 spans 可以拼接，但需保留每段 provenance 和命中分数。多个 child 指向同一 parent 时，通常只展开一次 parent。

## 原文与检索文本必须分开

推荐至少区分：

- `text`：从规范来源 span 得到的可引用正文；
- `retrieval_text`：用于词法检索或 Embedding 的文本，可加标题路径、表头、实体名或受控上下文；
- `display/citation`：最终展示时从来源与 span 重建的内容；
- `generated context`：模型生成的派生说明，单独记录生成方法和版本。

例如：

```text
text:
production | 4 | SRE

retrieval_text:
标题路径：部署指南 > 环境矩阵
表头：环境 | 副本数 | 审批
production | 4 | SRE
```

引用时只能把第一部分当作原始表格行；标题和表头应按各自来源 span 呈现。分别保存 `content_sha256` 与 `retrieval_sha256`，才能判断向量对应哪一版输入。

Anthropic 的 Contextual Retrieval 是生成 chunk-specific context 的一种方案。它可能改善特定检索任务，但生成内容仍是派生数据；要保留原文、模型/提示版本、失败策略和重建能力。

## Metadata 最小集合

| 类别 | 建议字段 | 用途 |
| --- | --- | --- |
| 身份 | `chunk_id`、`strategy_version`、`ordinal` | 去重、排序、迁移 |
| 来源 | `source_id`、`source_revision`、`element_spans` | 引用、更新、删除 |
| 结构 | `section_path`、`family`、`language` | 解释、过滤、专用策略 |
| 安全 | `tenant_id`、`acl`、`classification` | 检索前授权 |
| 完整性 | `content_sha256`、`retrieval_sha256` | 检测旧向量与内容漂移 |
| 向量 | `embedding_model`、`embedding_version`、`dimensions` | 兼容检查与重建 |
| 生命周期 | `created_at`、`published_revision`、`tombstone` | 审计、切换、删除 |

字段并非越多越好。每个字段要有类型、来源和更新规则；过滤字段尤其不能在有时为字符串、有时为数组。

## ACL 必须在检索前生效

若先召回再在展示阶段删除未授权块，向量分数、日志或模型上下文已经可能泄露信息。安全基线是：

1. 查询带 tenant 与主体 groups；
2. 数据库或检索层先执行 fail-closed 过滤；
3. 只对授权候选评分/返回；
4. parent 展开和相邻块合并时再次校验；
5. 缺失 ACL 的 chunk 不进入发布索引。

本库项目按 ACL 过滤后才做词项重叠评分，并有“员工查询 production 表格必须返回空”的测试。它只演示 OR group 语义；真实授权模型需要单独定义用户、组、租户、继承与拒绝规则。

## 稳定 ID 与版本

只用 `source_id + ordinal` 会在文档前方插入一段后导致后续 ID 全变。一个内容派生 ID 可以包含：

- source ID 与 source revision；
- strategy version；
- element IDs 与半开单位区间；
- content hash；
- ACL 或租户边界。

是否把 retrieval context 哈希纳入 chunk ID 取决于身份定义：若正文相同但标题前缀变化应重做向量，可以保留 chunk ID、更新 `retrieval_sha256` 与 embedding revision；也可以生成新 ID。两种都可行，但索引层必须有一条不可选的失效规则：

```text
index_entry_id = H(chunk_id + retrieval_sha256
                   + index_revision + acl_snapshot_sha256)
```

因此，即使业务选择保留 `chunk_id`，标题路径、表头或生成式检索上下文变化也会产生新的 `index_entry_id`；索引版本或 ACL 快照变化同样不能复用旧记录。正文身份与索引记录身份分层，才能同时支持稳定引用和确定性重建。本库项目已为这四项绑定及标题/表头变化编写测试；[[RAG/09-项目-从来源到引用证据链|RAG 来源到引用证据链]]继续把该身份接到发布 generation 与 citation。

`ordinal` 仍需保存，用于恢复阅读顺序，但不参与本库示例的 ID 身份。测试会在前面插入无关来源，验证旧 chunks 的 ID 不变。

## 增量更新与删除

来源 revision 变化时：

1. 解析新 revision 并生成候选 chunks；
2. 校验覆盖、ACL、hard max 与哈希；
3. 只为 `retrieval_sha256` 变化的块重算向量；
4. 在影子/待发布版本完成检索评测；
5. 原子切换 published pointer；
6. 旧版本保留短期回滚窗口；
7. 删除请求通过 tombstone/清除任务传播到 chunk、向量、缓存和备份策略。

不要先删旧索引再慢慢建新索引；中间态会产生缺文。`[[Knowledge/AI Agent Engineer/docs/知识库构建/00-目录|知识库构建]]`中的 revision/outbox/published pointer 模式可承接这条生命周期。

## 常见错误与排查

- **默认 20% overlap**：没有说明边界假设，也没有对照 `O=0`。
- **召回结果几乎相同**：检查相邻 spans 重叠率和 top-k 多样性。
- **标题写进正文**：引用把派生上下文误称为原文。
- **只有 parent 有 ACL**：child 向量已可被未授权查询命中。
- **内容变了但向量没变**：缺少 retrieval hash/model version 对账。
- **策略名未升级**：同名版本产生不同边界，实验不可重放。
- **删除来源后旧 chunk 仍可搜到**：生命周期没有覆盖索引、缓存或发布指针。

## 练习

1. 用 $L=10{,}000,S=1{,}000$ 分别计算 `O=0` 与 `O=200` 的窗口区间、正文总单位和真实重复率。
2. 为表格行设计 `text` 与 `retrieval_text`，列出每一行的来源 span。
3. 设计“标题改名、正文不变”时的 ID/向量更新规则，并说明选择。
4. 写出 ACL 缺失、ACL 变化、parent/child ACL 不同的三条 fail-closed 测试。
5. 给出 overlap 的停止条件，例如“证据完整率提升不足且上下文重复率增加”。

## 掌握检查

- [ ] 我能计算实际重复单位与重复率。
- [ ] 我知道 overlap 只针对边界证据，不是普遍增益开关。
- [ ] 我分开保存原文、检索文本、派生上下文与各自哈希。
- [ ] ACL 在召回/评分之前执行，并在 parent 展开时复核。
- [ ] chunk ID、ordinal、revision 和 embedding revision 各有明确职责。
- [ ] index entry 身份绑定检索表示、索引版本与 ACL；仅标题/表头变化也会使旧索引记录失效。
- [ ] 策略升级支持影子重建、对账、原子切换和回滚。

## 小结与下一步

Chunking 的工程质量不只看边界；它还取决于重复成本、来源可追溯性、权限与生命周期。下一步把这些契约放进可运行实验：`[[Knowledge/AI Agent Engineer/docs/Chunking策略/05-检索评测与切分项目|检索评测与切分项目]]`。

## 参考资料

- [Unstructured: Chunking](https://docs.unstructured.io/open-source/core-functionality/chunking)
- [Azure AI Search: Chunk documents](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-chunk-documents)
- [Anthropic: Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)

来源获取日期：2026-07-14。返回 `[[Knowledge/AI Agent Engineer/docs/Chunking策略/00-目录|Chunking 策略目录]]`。
