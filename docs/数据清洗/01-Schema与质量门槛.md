---
title: Schema 与质量门槛
tags:
  - ai-agent-engineer
  - data-quality
aliases:
  - 数据契约
  - Data Schema
source_checked: 2026-07-14
source_baseline:
  - JSON Schema 2020-12
  - pandas 3.0 stable user guide
---

# Schema 与质量门槛

## 本节目标

先定义数据单元、字段语义与失败动作，再把“数据干净”改写成可执行、可版本化、可审计的契约。

## 先定义一行代表什么

清洗的第一步不是调用 `dropna()`，而是定义**数据单元**。一行可能代表一次 Agent 运行、一次工具调用、一个文档或一个 chunk。如果一行含义不清，唯一性、统计量和标签都会失去解释。

## 最小数据契约

| 字段 | 含义 | 类型 | 约束示例 |
| --- | --- | --- | --- |
| `run_id` | 一次运行的稳定标识 | string | 必填、唯一、不可复用 |
| `started_at` | 开始时间 | datetime | 含时区、不得晚于采集时间太多 |
| `status` | 终态 | category | `success/error/cancelled` |
| `latency_ms` | 总延迟 | integer | `>=0`，单位固定为毫秒 |
| `query` | 用户输入 | string | 可空策略明确、保留原文 |

契约至少包括：字段名、业务含义、数据类型、是否必填、允许值/范围、唯一性、单位、时区、敏感级别与产生时点。

契约本身也要有版本。新增可选字段通常可向后兼容，删除字段、改变类型或收紧枚举可能破坏旧消费者；生产系统应写清未知字段是拒绝、保留还是隔离，不能静默丢弃。

## 完整性、有效性、一致性、唯一性

- **完整性**：必须字段是否存在，覆盖率是否达标。
- **有效性**：值是否能解析并满足范围或枚举。
- **一致性**：相关字段是否互相矛盾，例如 `success` 却有必填 `error_code`。
- **唯一性**：主键是否重复，重复是否代表重放、重试还是采集错误。
- **及时性**：数据是否在允许延迟内到达。

质量门槛应量化，例如“`run_id` 非空率 100%，重复率 0%；未知 `status` 比例小于 0.1% 且全部隔离”。阈值是工程决策，不是自然常数，应记录负责人和变更原因。

## 拒绝、隔离还是修复

- 可确定、无损的格式问题可自动规范，如首尾空格。
- 可能改变语义的问题应隔离，如冲突主键、非法时间。
- 无法恢复的关键字段缺失应拒绝，不要静默猜测。
- 原始数据必须只读保留；清洗结果带规则版本和时间。

## 练习

为 RAG 文档写契约，至少包含 `document_id`、`source_uri`、`title`、`content`、`updated_at`、`access_scope`。说明哪一项缺失会让文档禁止入库。

## 掌握检查

- [ ] 我能说清“一行代表什么”以及主键识别什么实体或事件。
- [ ] 我能为每个字段写类型、可空性、枚举/范围、单位、时区和敏感级别。
- [ ] 我会区分阻断、隔离、告警和确定性修复，并记录规则版本。
- [ ] 我能说明 schema 变更如何影响上游生产者和下游消费者。

下一步：[[数据清洗/02-缺失值与缺失机制|缺失值与缺失机制]]。

## 参考资料

资料核验日期：2026-07-14。

- [pandas: Intro to data structures](https://pandas.pydata.org/docs/user_guide/dsintro.html)
- [JSON Schema 2020-12 specification](https://json-schema.org/specification)
- [JSON Schema: Getting started](https://json-schema.org/learn/getting-started-step-by-step)
