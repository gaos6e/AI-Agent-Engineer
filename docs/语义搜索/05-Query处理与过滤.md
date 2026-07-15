---
title: Query 处理与过滤
tags:
  - ai-agent-engineer
  - semantic-search
  - query-processing
aliases:
  - 查询处理与安全过滤
  - Query Processing
source_checked: 2026-07-14
source_baseline: "Sentence Transformers 与 Qdrant 官方文档、DPR/BEIR 论文截至 2026-07-14"
---

# Query 处理与过滤

## 本节目标

把一条带错别字、指代、时间和权限的用户输入转换成可回放检索计划，同时保证任何改写或降级都不能越过 tenant/ACL。完成后，你应能画出 query pipeline，区分硬约束与可选增强，并为每一步设置版本、超时和回退。

## 一条安全的 Query 流程

```text
认证身份 + original query + 可信会话状态
        ↓
Unicode/大小写等最小规范化
        ↓
识别语言、意图、实体、时间与精确标识符
        ↓
构造不可放宽的 tenant / ACL / status / effective-time filter
        ↓
可选：别名扩展、改写、拆分、多 query
        ↓
BM25 / dense / 其他通道并行召回
        ↓
融合、去重、预算与可解释日志
```

身份和硬过滤应在改写前已确定，并传给所有通道。LLM 或用户文本不能覆盖可信 tenant/groups。

## 最小规范化

可以安全起步的处理包括：

- Unicode NFKC 或项目约定的规范化；
- 英文大小写与空白统一；
- 保留 original query；
- 识别错误码、型号、URL、金额、日期和版本；
- 按锁定 analyzer 切词。

不要盲目删除标点、数字和停用词。“不要续费”中的否定、“Python 2”中的版本、“1.5%”中的数值都可能改变意图。规范化前后文本都要可回放。

## 别名、拼写与领域扩展

稳定领域词典可将 VPN、虚拟专用网络等同义表达加入额外 query，但应：

- 保存词典版本和触发项；
- 区分精确替换与 OR 扩展；
- 防止一个缩写映射多个领域后候选爆炸；
- 对错误码、账号、订单号等精确标识符保持原词通道；
- 用 hard negatives 验证扩展不会扩大到相邻产品。

拼写纠正宜作为额外候选或明确提示，不要静默覆盖原 query。错误码被“纠正”为普通词尤其危险。

## 会话指代与时间

“上次那个退款规则现在还有效吗”至少需要：

1. 从可信会话状态解析“那个”对应哪项规则，而不是让模型猜；
2. 将 now 转为明确时区和时间戳；
3. 把 effective_from/effective_to 作为 filter；
4. 保留 original query 与补全后的 retrieval query；
5. 上下文缺失时请求澄清，而不是检索所有退款文档。

时间过滤是硬条件时不能被高相似度覆盖。若索引尚未同步最新 revision，应返回“数据可能未更新”的状态，而非悄悄使用过期内容。

## LLM 改写的边界

LLM 可以生成同义 query、扩展缩写或拆分复杂问题，但它是会失败的动态组件：

- 可能改变否定、数字、实体和权限；
- 可能生成语料不存在的术语；
- 用户文本中的指令可能诱导它改变检索范围；
- 网络/模型超时会增加尾延迟；
- 模型升级会改变 rewrite 分布。

工程要求：

- original query 始终作为独立通道或降级路径；
- rewrite 有 prompt/model/revision、父 query、耗时和 checksum；
- 设置总 query 数、token、并发、候选与超时预算；
- query 文本只作为数据，不执行其中的工具/系统指令；
- 离线回放 original-only 与 rewrite 两条基线；
- 安全 filter 在所有 rewrite 外层强制合取。

## 多查询与问题拆分

“VPN 连不上并且收不到验证码”可能拆为两个子问题。每增加一路都带来延迟和噪声，应记录：

- subquery ID 与父 query；
- 每路召回通道和贡献文档；
- 合并/去重规则；
- 总候选与每个原文上限；
- 任一路失败时是部分结果、重试还是整体失败。

多跳问题还要区分“需要两个证据”与“两个独立问题”。Qrels 可以标证据组；普通 Recall@k 只看单文档时可能不足。

## 硬过滤从可信上下文构造

常见 hard filters：

- tenant_id / organization_id；
- ACL 群组或主体 ID；
- status=published；
- effective time；
- 数据驻留、法律保留和删除状态。

常见业务 filters：

- language、product、document_type；
- region、版本、价格范围；
- 用户明确选择的类别。

客户端可提出业务偏好，但服务端必须从认证会话派生 tenant/ACL，并对允许字段、类型、范围和组合做 schema 校验。空群组、未知字段或解析失败应 fail-closed。

## 过滤必须在评分前约束候选

先全局 top-k 再删除无权限文档会导致：

- 越权内容可能已进入缓存、trace 或下游模型；
- 删除后不足 k 条，授权文档无法补位；
- 分数/排名泄露另一租户存在某内容；
- 高选择率过滤下 recall 崩溃。

数据库具体采用 pre-filter、filter-aware ANN、扩大候选或 exact fallback 取决于产品与参数；无论执行计划如何，最终候选集合都不得越权。当前 Qdrant filtering/hybrid API 是可核验案例，不是所有数据库语义。

## 失败状态与降级

| 失败 | 正确动作示例 | 禁止动作 |
| --- | --- | --- |
| Rewrite 超时 | original query 检索 | 放宽 ACL |
| 无 subject groups | 返回空/鉴权错误 | 视为公开用户 |
| Filter schema 错误 | 拒绝请求并记录 | 忽略未知字段 |
| Dense 服务失败 | 标记降级到 BM25 | 伪造 dense 空结果为正常 |
| 索引 revision 落后 | 返回新鲜度状态/旧版本明确标记 | 声称已是最新 |
| 多查询部分失败 | 标记 partial 并保留成功路 | 重复无限重试 |

## 可观察性与隐私

为了回放，应记录 query ID、版本、过滤字段名/摘要、通道、耗时、候选 ID/rank、降级原因和 trace ID。不要把完整私密 query、原文、身份 token 或 ACL 全量写入普通日志；使用最小化、脱敏、访问控制与保留期。

监控至少分层：

- original-only 与 rewrite 的增益/回退率；
- analyzer/词典/model revision；
- query 类型、语言、租户规模和过滤选择率；
- no-result、partial、timeout 和越权门禁；
- 每路候选贡献与 p95/p99。

## 常见错误与排查

- **改写替换原 query**：保留原始独立通道；
- **LLM 改掉数字/否定**：结构化抽取并做不变量校验；
- **用户可传 tenant_id**：服务端从认证身份覆盖；
- **过滤过严就自动取消**：返回明确无结果原因，绝不放宽安全条件；
- **同义词扩展候选爆炸**：限制映射、query 数和总预算；
- **缓存 key 没包含 ACL/revision**：将身份授权摘要和版本纳入；
- **日志含敏感 query/凭据**：最小化、脱敏并限制访问。

## 练习

把“上次那个退款规则现在还有效吗”写成检索计划：

1. 列出必须从会话获取的字段；
2. 写 original、补全 query 和可能的澄清问题；
3. 定义 tenant/ACL/status/effective-time filter；
4. 说明 rewrite 超时、时间解析失败和索引落后如何降级；
5. 设计缓存 key，不记录真实凭据；
6. 构造 5 条否定/数字 hard negatives 和 3 条权限测试。

## 掌握检查

- [ ] Original query 与每个 rewrite 都可追溯。
- [ ] Tenant/ACL 来自可信身份，不被用户或模型覆盖。
- [ ] 数字、时间、否定和标识符有不变量检查。
- [ ] 每个动态步骤有版本、超时、预算和回退。
- [ ] 空权限、未知 filter 和解析异常 fail-closed。
- [ ] 日志足够回放但不暴露完整敏感数据。

下一步：[[语义搜索/06-召回与离线评测|召回与离线评测]]。

## 参考资料

- Karpukhin et al., [Dense Passage Retrieval](https://arxiv.org/abs/2004.04906)
- Thakur et al., [BEIR](https://arxiv.org/abs/2104.08663)
- [Sentence Transformers: Semantic Search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)
- [Qdrant: Filtering](https://qdrant.tech/documentation/concepts/filtering/)
- [Qdrant: Hybrid and Multi-Stage Queries](https://qdrant.tech/documentation/search/hybrid-queries/)

来源获取日期：2026-07-14。返回 [[语义搜索/00-目录|语义搜索目录]]。
