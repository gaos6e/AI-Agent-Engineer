---
title: "训练数据与 Hard Negatives"
tags:
  - ai-agent-engineer
  - reranking
  - training-data
aliases:
  - 重排训练数据
  - Reranker Training Data
source_checked: 2026-07-14
source_baseline: "DPR、BERT reranking、monoT5、BEIR 原始论文截至 2026-07-14"
lang: zh-CN
translation_key: Reranking/05-训练数据与Hard Negatives.md
translation_route: en/reranking/05-training-data-and-hard-negatives
translation_default_route: zh-CN/Reranking/05-训练数据与Hard-Negatives
---

# 训练数据与 Hard Negatives

## 本节目标

一个 reranker 学到的不是“真理”，而是训练 query、候选池、标签规则和负例分布。学完后，你应能选择 pointwise/pairwise/listwise 数据形式，从真实召回中挖 hard negatives，避免未标候选误作负例与近重复泄漏，并维护可审计的数据闭环。

## 三种监督形式

| 形式 | 样本 | 适合目标 | 常见风险 |
| --- | --- | --- | --- |
| Pointwise | (q,d,label/grade) | 分类/回归、独立打分 | 类别失衡、跨 query 尺度 |
| Pairwise | (q,d+,d−) | 学习正例高于负例 | pair 爆炸、顺序不传递 |
| Listwise | (q,[d…],ranking/qrels) | 直接优化列表 | 固定窗口/位置偏差、成本 |

数据形式应与模型 loss、线上输出和评测一致。若 qrels 是 0～3 级却训练成二元标签，要写明映射以及丢失的等级信息。

## Random negatives 为什么太容易

“退款到账”正例对随机的“会员续费”负例，模型只需识别主题就能分开，未学会真正的 relevance。上线时更难的是：

- 同主题但只讲如何申请，不回答到账时间；
- 旧版政策给出冲突数字；
- 同一错误码但另一产品；
- 包含所有关键词却是否定答案；
- 近重复 passage 缺失关键条件；
- first-stage 排名很高但人工判 0。

这些是 hard negatives：容易被当前检索器/模型混淆、经标注确认不相关的候选。

## 未在 Qrels 中不等于负例

大语料 qrels 不完整。把所有 unjudged top-k 当负例会惩罚模型发现的新正例。推荐流程：

1. 用多个 retriever/reranker pool 候选；
2. 对新系统独有高排候选补标；
3. 区分 judged negative 与 unjudged；
4. 训练时按置信度/来源处理；
5. 抽检高损失或频繁被选的 negatives。

“模型挖出的最难负例”可能其实是漏标正例，尤其需要人工复核。

## Hard-negative mining 闭环

```text
锁定 first-stage/reranker snapshot
        ↓
收集高排错误与线上失败
        ↓
去重、脱敏、权限隔离
        ↓
按指南盲标与裁决
        ↓
生成 point/pair/list 数据版本
        ↓
训练 → validation → 封存 test
        ↓
shadow/canary → 新失败进入下一轮
```

记录 query ID、candidate/source revision、retriever/model revision、first rank/score、标签/证据和采样原因。否则新模型上线后无法解释训练分布。

## 负例组合

一个训练 batch 可混合：

- random negatives：保持全局主题区分；
- in-batch negatives：成本低，但其他 query 的正例可能也相关；
- BM25 hard negatives：词面相似；
- dense hard negatives：语义相似；
- previous-reranker errors：最贴近线上；
- adversarial negatives：数字、否定、过期与提示注入。

比例需在 validation 集调，不应全用最难样本。过度 hard mining 可能损害简单 query 或让模型过拟合旧检索器。

## 数据切分与泄漏

至少按 canonical source/document 分组，避免相邻 chunk 跨 train/test。还要检查：

- 同一 query 的改写是否跨 split；
- 同一模板/FAQ 的近重复；
- 时间未来信息泄漏；
- 训练标签生成模型是否见过 benchmark；
- test 失败是否在每轮被加入训练；
- 点击日志中的展示位置与旧模型偏差。

主动学习每轮都应创建新 train/validation 版本，封存 test 不参与选择。

## 点击与行为日志

点击、停留和任务成功提供规模，但不是直接 relevance：

- 用户只能点击被展示的候选；
- 首位天然获得更多曝光；
- 无点击可能是无需点击或页面失败；
- 敏感 query 采集受隐私/合规约束；
- 旧排序决定了可见候选。

可通过随机探索、倾向校正、人工抽检和多信号组合缓解，仍要记录生成假设。不要把点击=1、未点击=0 当无偏真值。

## LLM 合成与蒸馏标签

LLM 可生成 query、负例或 relevance rationale，RankGPT 等研究也探索教师排序/蒸馏。但要防止：

- 教师偏好变成学生“真理”；
- 生成 query 语言过于规则；
- 原文外幻觉标签；
- 数据污染/benchmark contamination；
- prompt/model 更新导致标签漂移；
- 私密候选被发送给未授权服务。

保留生成 prompt/model/revision、输入 source、输出与人工审计；关键测试与安全边界仍由人工/规则确认。

## 版本与数据卡

每版至少写：

- 任务、语言、领域、时间范围；
- query/candidate 数、标签分布和 source groups；
- negative 类型与比例；
- 标注指南、一致性与裁决；
- 去重、脱敏与权限处理；
- train/validation/test 切分 checksum；
- 已知缺口、禁用用途和保留期；
- 对应模型/代码/特征 schema。

## 常见错误与排查

- **随机负例成绩很高、线上无提升**：加入真实 first-stage errors；
- **Hard negative 其实相关**：补标与裁决；
- **相邻 chunk 泄漏**：按 canonical source 分组；
- **只从旧 retriever 采样**：pool 多系统和探索样本；
- **点击直接当标签**：处理曝光/位置偏差；
- **Test 每轮加入训练**：封存 test，新建诊断集；
- **LLM 标签无 provenance**：锁定 prompt/model/source 并抽审。

## 练习

为“退款到账时间”构造：

1. 1 个 grade-3 正例、1 个 grade-1 部分相关；
2. 3 个 hard negatives：过期数字、只讲申请、否定条件；
3. 1 个 dense hard negative 和 1 个 random negative；
4. pointwise、pairwise、listwise 三种表示；
5. canonical-source 分组切分；
6. 一张包含采样原因、retriever revision 和标注证据的数据卡。

## 掌握检查

- [ ] 数据形式与 loss、输出和指标一致。
- [ ] Hard negatives 来自真实混淆且经标注确认。
- [ ] Unjudged 候选不自动视为负例。
- [ ] Random、retriever、adversarial negatives 有受控比例。
- [ ] Source/query 改写/时间近重复不跨 split。
- [ ] 点击与 LLM 标签的偏差、provenance 和隐私清楚。
- [ ] Test 封存，训练闭环版本化。

下一步：[[Reranking/06-指标延迟成本与降级|指标、延迟、成本与降级]]。

## 参考资料

- Nogueira & Cho, [Passage Re-ranking with BERT](https://arxiv.org/abs/1901.04085)
- Nogueira, Jiang & Lin, [monoT5](https://arxiv.org/abs/2003.06713)
- Karpukhin et al., [Dense Passage Retrieval](https://arxiv.org/abs/2004.04906)
- Thakur et al., [BEIR](https://arxiv.org/abs/2104.08663)

来源获取日期：2026-07-14。返回 [[Reranking/00-目录|Reranking 目录]]。
