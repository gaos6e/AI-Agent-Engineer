---
title: Trace 与隐私边界
tags:
  - llmops
  - tracing
aliases:
  - LLM Trace
  - LLM 链路追踪
source_checked: 2026-07-21
---

# Trace 与隐私边界

## 本节目标

把一次LLM/Agent请求拆成可关联的spans，用于定位延迟、重试、工具错误和版本回归，同时设计内容采集、脱敏和保留边界。

## Trace、span和event

- **Trace**：一个端到端任务的因果链，由共享`trace_id`关联。
- **Span**：其中一段工作，有开始/结束、状态、属性和父子关系。
- **Event**：某个span内的离散事件，例如“第二次重试开始”或“输出策略拒绝”。

一条客服Agent Trace可以是：

```text
request
├─ assemble_context
│  └─ retrieve_documents
│     └─ rerank
├─ model_call attempt=1
├─ tool_call lookup_ticket
├─ model_call attempt=2
└─ output_policy
```

如果只记录总请求30秒，无法判断是检索、模型、工具还是循环导致。

## 每个span记什么

优先记录可检索的元数据：

| Span | 建议元数据 | 默认不记的内容 |
| --- | --- | --- |
| request | release ID、租户/任务类型的受控标签、结果状态 | 认证header、完整用户输入 |
| retrieval | 快照、配置、命中数、耗时 | 未脱敏文档全文 |
| model | 供应商/模型版本、参数、token统计、缓存统计、请求ID | 密钥、默认全量Prompt/输出 |
| tool | 工具与schema版本、状态、耗时、幂等键摘要 | 完整参数、密码、返回的个人信息 |
| policy | 策略版本、通过/拒绝、原因代码 | 为“方便”而重复原文 |

内容与元数据应分开开关和保留策略。为调试开启内容采样时，应限定环境、租户、百分比、访问角色和到期时间，而不是久久打开“全量记录”。

若要把离线门与线上窗口关联，Trace或受控审计Log可记录`release_id`、发布清单SHA-256和candidate gate的**完整**SHA-256摘要；短指纹只用于人读对照。完整摘要、Trace ID、request ID和用户ID均不得作为Metric label：它们会造成高基数，后两者还可能扩大隐私风险。摘要也不应成为内容采集的借口；真实原文仍遵循最小化、授权与保留边界。

## 上下文传播

分布式系统需要将Trace上下文从网关传给检索、模型代理和工具服务。W3C Trace Context定义HTTP传播格式；实施时应用成熟库生成和验证，不手工拼接ID。

来自外部的Trace字段不是可信业务身份。不能用`trace_id`代替用户认证，也不能允许请求者通过伪造采样标记迫使系统记录敏感内容。

## 采样与高基数

全量Trace成本可能过高。常见策略包括概率采样、优先保留错误/慢请求的尾部采样，以及对高风险任务保留更高比例。采样必须可见：否则你可能将“没采集到”误解为“没发生”。

不要将`user_id`、整个Prompt或文档ID作为Metrics label，这会导致高基数爆炸和隐私风险。具体请求用Trace查，集合趋势用受控低基数Metrics。

## 敏感内容的决策顺序

1. **必要性**：没有原文是否仍能诊断？能则不收集。
2. **最小化**：只收集必要字段、长度或摘要。
3. **脱敏**：在离开应用信任边界前处理，并测试脱敏失败路径。
4. **隔离**：按环境和租户设置访问控制。
5. **保留与删除**：设置过期、删除和审计证据。

供应商的数据保留和区域能力会随端点、功能和客户配置而异。只能根据当前合同与官方控制面说明，不能从一句概述推断所有API都零保留。

## 练习与自测

为一个会调用“读取客户资料”和“创建工单”工具的Agent画span树，列出每个span的元数据、不应记录的内容与保留期。再回答：

1. 为什么一个`request_id`无法替代带父子关系的Trace？
2. 为什么统计用Metric label不应直接放用户ID？
3. 如果采样只保留错误请求，它能用来估计全体成功请求的延迟分布吗？为什么？

## 小结与下一步

Trace是诊断和谱系的连接层，不是“把所有内容都存下来”。下一步在 [[LLMOps/01-基础与生命周期/05-离线评测门与回归集|离线评测门与回归集]] 中把Trace中的真实失败转成待人工分诊的回归候选；完整接纳流程见 [[评测体系/02-方法与质量/08-离线到线上证据交接与回归闭环|离线到线上证据交接与回归闭环]]。

## 参考资料

- [OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/)（访问于2026-07-21）
- [OpenTelemetry GenAI semantic conventions repository](https://github.com/open-telemetry/semantic-conventions-genai)（访问于2026-07-21；GenAI约定已迁移到此官方仓库，接入时固定实际修订和schema URL）
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)（W3C Recommendation，访问于2026-07-21）
- [OpenAI Data controls](https://developers.openai.com/api/docs/guides/your-data)（访问于2026-07-21；存储与保留条件会随端点、功能与账户资格改变）
