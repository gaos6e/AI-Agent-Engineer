---
title: 需求、边界与 Schema
tags:
  - ai-agent-engineer
  - 知识库
  - schema
aliases:
  - 知识库 Schema
source_checked: 2026-07-22
source_baseline:
  - JSON Schema draft 2020-12
  - W3C PROV-DM Recommendation
---

# 需求、边界与 Schema

## 本节目标

从用户问题和风险边界定义知识库，而不是从某个向量数据库的字段开始；建立稳定身份、canonical/derived 分层、版本轴和可演进的来源记录契约。

## 先写“谁用它做什么”

员工政策问答、代码搜索、论文证据库和客服知识库都可能使用 RAG，但它们的正确性标准完全不同。至少回答：

| 维度 | 要问的问题 | 可验收输出 |
| --- | --- | --- |
| 用户与租户 | 谁提问？租户是否隔离？ | 主体/租户模型、越权用例 |
| 问题 | 高频、长尾、无答案问题是什么？ | 代表性 query 与拒答集 |
| 来源 | 哪些系统/目录被授权？ | 来源允许清单与 owner |
| 时效 | 更新后多久必须可见？ | freshness/propagation SLO |
| 证据 | 引用到文档、页还是表格单元？ | provenance 与定位契约 |
| 权限 | 哪些条件下允许候选进入检索？ | ACL/ABAC 属性和测试 |
| 删除 | 源删除、撤权、到期怎样传播？ | 墓碑、确认与保留策略 |
| 质量 | 哪些错误必须阻止发布？ | 分层指标、阈值与 gold set |

“准确率越高越好”不可验收。要写成可观察目标，例如“来源确认删除后 5 分钟内不再出现在任何在线候选中”；具体数值应由业务风险与能力决定，不能凭空照抄。

## 四层对象

1. **原始来源（raw source）**：原文件/API 响应、来源版本、许可与获取证据；
2. **canonical revision**：业务稳定 ID 下的规范修订，含权限和来源状态；
3. **派生产物（derived artifacts）**：解析元素、chunks、embeddings、关键词/图索引记录；
4. **已发布视图（published view）**：查询实际可见的版本指针与授权投影。

canonical 是可重建依据，索引是加速投影。原始来源可能受更严格的存储权限；“canonical”也不意味着永远保留，仍受删除与保留规则约束。

W3C PROV-DM 用 entity、activity、agent 和 derivation 表达“什么实体经什么活动由谁负责地产生”。在知识库中可映射为：源文件和 revision 是实体，采集/解析/切块是活动，connector 或负责团队是 agent，chunk/embedding 是派生实体。无需为了采用这些概念就强制使用 RDF。

## 身份与版本不要混在一起

- `document_id`：业务对象的稳定身份，如 `policy:leave`；
- `source_sequence`：某 connector 对该对象给出的单调顺序，本项目用整数教学；
- `source_version`：来源系统的 ETag、revision 或业务版本；
- `revision_number`：canonical store 内的修订序号；
- `pipeline_version`：解析、规范化、切块等配置版本；
- `model/index version`：embedding 模型和索引 schema；
- `run_id`：一次处理运行，不等于内容版本。

标题、路径和 URL 可能变化，不宜单独作为永久 ID。哈希识别内容状态，但相同内容在不同租户/ACL 下也不能随意合并。

## 来源记录契约

```json
{
  "tenant_id": "tenant-a",
  "document_id": "policy:leave",
  "source_sequence": 7,
  "source_uri": "https://kb.example.invalid/policy/leave",
  "source_version": "v3",
  "content": "请假政策要求提前两天提交。",
  "allowed_groups": ["employees"]
}
```

对应 [[知识库构建/examples/source-record.schema.json|来源记录 JSON Schema]] 明确 required、类型、长度、唯一组和 `additionalProperties: false`。但 schema 不是全部业务规则：JSON Schema 的 `maxLength` 统计字符，不是 UTF-8 bytes，所以项目用 `x-maxUtf8Bytes` 作为说明性注解，并在应用代码中执行真实字节上限。未知自定义 keyword 可能被验证器忽略，不能把“写进 schema”误当成“已执行”。

> [!warning] 扁平 `allowed_groups` 不是授权事实源
>
> 示例中的 `allowed_groups` 是已经由上游解析好的教学输入，只能检验后续 revision 与投影是否一致。真实 connector 还要保存可重算的 permission snapshot、来源 scope/owner、授权决策或 policy revision、观察时间与失败状态；schema 校验成功不等于调用者确实拥有读取该来源的权利。

## Schema 演进

每个 schema 要声明 dialect 与版本，并定义：

- 新增 optional 字段的旧消费者行为；
- required/枚举变化的迁移窗口；
- 未知字段是拒绝、保留还是忽略；
- 新旧数据是否并存、如何回填和回滚；
- 哪些变化只需重算局部派生物，哪些必须全量重建；
- schema、transformer 和索引 reader/writer 的兼容矩阵。

不要直接原地改完所有历史数据再发现 reader 不兼容。常见做法是双读/双写或新版本投影，验证后切换 published pointer。

## 需求驱动的最小字段

来源与身份：tenant、document ID、source URI/ID、source version/sequence、owner。内容与语言：raw/content hash、标题、语言、元素关系。治理：ACL/属性、classification、许可、有效期、保留/删除状态。处理：schema/pipeline/model/index version、run ID、状态、警告。发布：current revision、published revision、发布时间与回滚指针。

“最小”不是字段越少越好，而是每个字段都能对应查询、治理、重放或验收需求。

## 常见错误与排查

- **先照抄向量库字段**：会把存储限制误当成业务模型。
- **一个表兼任事实、任务状态和搜索索引**：更新失败时无法区分 current 与 published。
- **路径/标题当永久主键**：重命名导致重复或删除失效。
- **只存 content hash**：解释不了来源、ACL、pipeline 和模型版本。
- **schema 无版本**：升级后旧记录含义不可复现。
- **同文去重忽略租户/ACL**：可能把受限内容投影为公开对象。

## 练习

1. 为“内部政策助手”写 15 个查询、3 个无答案和 5 个越权用例。
2. 画出 `document_id → revision → element → chunk → embedding → published projection`。
3. 给来源 schema 增加 `effective_from`；说明旧数据、reader 和索引如何迁移。
4. 解释为什么 `source_sequence=7` 不能自动与另一个 connector 的 `7` 比较。

## 自测

- [ ] 我能从用户任务反推来源、引用粒度、权限和时效要求。
- [ ] 我能区分业务身份、来源顺序、canonical revision 和运行 ID。
- [ ] 我会把 canonical、派生产物和 published view 分层。
- [ ] 我知道 JSON Schema 注解不一定由验证器执行。
- [ ] 我能为 schema 变化设计兼容、迁移与回滚。

## 参考资料与下一步

- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [W3C PROV-DM](https://www.w3.org/TR/prov-dm/)

来源获取日期：2026-07-22。下一步：[[知识库构建/02-采集来源与规范化|采集、来源与规范化]]。
