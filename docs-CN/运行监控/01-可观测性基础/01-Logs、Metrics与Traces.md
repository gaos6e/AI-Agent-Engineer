---
title: "Logs、Metrics 与 Traces"
tags:
  - observability
  - telemetry
aliases:
  - 可观测性三大信号
source_checked: 2026-07-14
lang: zh-CN
translation_key: 运行监控/01-可观测性基础/01-Logs、Metrics与Traces.md
translation_route: en/runtime-monitoring/foundations/01-logs-metrics-and-traces
translation_default_route: zh-CN/运行监控/01-可观测性基础/01-Logs、Metrics与Traces
---

# Logs、Metrics 与 Traces

## 本节目标

理解Log、Metric和Trace的数据形状、适合回答的问题与成本取舍，并设计能从集合趋势下钻到单次请求的关联键。

## 三类信号的直觉

| 信号 | 数据形状 | 擅长的问题 | 主要风险 |
| --- | --- | --- | --- |
| Log | 带时间和元数据的离散记录 | “当时发生了什么？具体错误是什么？” | 体量、敏感内容、自由文本难聚合 |
| Metric | 按时间聚合的数值序列 | “错误率、p95延迟、费用如何变化？” | 聚合丢失细节、高基数label成本 |
| Trace | 由父子spans组成的端到端路径 | “时间耗在哪？哪次重试或工具失败？” | 采样偏差、传播断链、内容泄露 |

它们不是三个完全独立的数据孤岛。一个请求的结构化Log可带`trace_id`和`span_id`；一个Metric exemplar或Dashboard下钻链接可指向相关Trace；三者应共享稳定的service、environment、release等资源语义。

## 从自由文本到结构化Log

难以查询的日志：

```text
something went wrong for user 93827
```

更可操作的结构：

```json
{
  "timestamp": "2026-07-13T08:30:10Z",
  "severity": "ERROR",
  "service": "agent-gateway",
  "environment": "production",
  "release_id": "agent-2026-07-13.1",
  "trace_id": "opaque-trace-id",
  "event_name": "tool_timeout",
  "tool_name": "lookup_ticket",
  "error_type": "deadline_exceeded"
}
```

这里同样保留严格 JSON：`timestamp`、`service`、`environment` 与 `release_id` 确定发生位置和版本；`trace_id` 只承担跨信号关联；`event_name`、`tool_name` 和 `error_type` 让告警与排障能按结构聚合；`severity` 只表达事件级别，不能单独替代 SLO 或业务质量判断。

这是教学样例。真实日志应使用平台的时间和Trace ID格式，不记录密钥、Authorization header、完整个人资料或不必要的Prompt。如果需用户关联，使用受控、有保留期且不能当认证凭据的代理标识。

## Metric类型与单位

初学时可先掌握：

- **Counter**：只累积增长的事件数，如请求数、错误数、token数；通常查速率或区间增量。
- **Gauge**：可上下变化的当前值，如队列长度、在飞请求、当前快照时龄。
- **Histogram**：记录分布区间，用于延迟、输出长度或成本分布；分桶边界应围绕SLO和诊断需求设计。

指标名称应包含单位或通过数据模型明确单位。`latency=4`不知道是秒、毫秒还是分钟，结果可能比没指标更危险。

## 用RED、USE与黄金信号开始排查

三套方法帮助初学者避免漏看关键症状，但它们是检查框架，不自动等于SLI或根因：

- **RED方法**面向服务请求：Rate（速率）、Errors（错误）、Duration（耗时分布）；
- **USE方法**面向每项资源：Utilization（利用率）、Saturation（饱和/排队）、Errors（错误）；
- Google SRE的**四个黄金信号**是Latency、Traffic、Errors、Saturation，适合从用户影响和容量症状组织监控。

例如，Agent API先看请求率、错误率和延迟分布；发现延迟升高后，再用USE检查CPU利用率、线程/队列饱和度和资源错误。CPU高只是候选解释，仍要结合Trace和变更证据验证。

## 直方图与百分位

p95表示约95%的观测值不超过该值，它不是“最慢5%的平均值”，也不能由各实例p95再求平均得到整体p95。要计算尾延迟，需要保存足够的分布信息：Histogram按预设边界累计计数，分桶应围绕SLO阈值和诊断尺度；分辨率太粗会让估算失真。

Prometheus当前文档区分经典Histogram、原生Histogram与Summary：经典Histogram可在服务端聚合分桶，Summary在客户端预计算分位数且跨实例聚合受限；官方在可行时建议考虑原生Histogram。这是Prometheus的当前实现建议，不是所有监控系统的通用API。选型前应按所用版本重新核对支持状态、迁移成本和存储开销。

## Labels与基数

Metric label用于按有限类别分组，例如`environment`、`release`、`result`和受控的`task_type`。每个唯一label组合都可能建立新时间序列，因此不应放入用户ID、request ID、整段Prompt或无界URL。这些高基数细节应放在可控的Trace/Log中，通过ID下钻。

## Trace的完整性

一个span应记录操作名、开始/结束、状态、父span、关键版本和受控业务属性。将上下文传到HTTP、消息队列和后台任务时需使用标准传播机制。对LLM/Agent路径，至少区分检索、模型、工具、重试和输出策略spans。

采样后“查不到Trace”可能意味着未采集，不能被解释为“请求没发生”。采样策略、采样率和传播丢失率也应被监控。

## 一条实用诊断路径

1. Dashboard显示某release的p95延迟上升；
2. 按release、任务类型和时间窗口筛选，排除聚合口径变化；
3. 从延迟分布选择慢Trace；
4. 比较检索、模型、工具和重试spans；
5. 用`trace_id`查找相关结构化Log和具体错误类型；
6. 形成可验证假设，而不是直接将相关组件当根因。

## 练习与自测

将一条“Agent回答太慢”拆为至少5个spans，为每个span设计两个元数据，再列出两个Metric和两条Log。回答：

1. 为什么Metric非常适合看趋势，却不足以解释单次请求？
2. 为什么request ID不应成为Metric label？
3. 为什么自动仪器化后仍需要业务语义和版本字段？

## 小结与下一步

三类信号的价值在于共同回答“是否有问题、影响谁、为什么”。下一步在 [[运行监控/01-可观测性基础/02-仪器化、Collector与关联|仪器化、Collector 与关联]] 中把这些信号跨进程可靠关联并治理。

## 参考资料

- [OpenTelemetry Logs](https://opentelemetry.io/docs/concepts/signals/logs/)（访问于2026-07-14；各语言SDK支持状态会变化）
- [OpenTelemetry Metrics](https://opentelemetry.io/docs/concepts/signals/metrics/)（访问于2026-07-14）
- [OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/)（访问于2026-07-14）
- [Prometheus Histograms and summaries](https://prometheus.io/docs/practices/histograms/)（访问于2026-07-14；按部署版本核对原生Histogram支持）
- [Tom Wilkie: The RED Method](https://grafana.com/blog/2018/08/02/the-red-method-how-to-instrument-your-services/)（原始方法说明，访问于2026-07-14）
- [Brendan Gregg: The USE Method](https://www.brendangregg.com/usemethod.html)（原始方法说明，访问于2026-07-14）
- [Google SRE: Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)（访问于2026-07-14）
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)（W3C Recommendation，访问于2026-07-14）
