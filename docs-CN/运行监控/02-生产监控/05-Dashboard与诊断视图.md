---
title: "Dashboard 与诊断视图"
tags:
  - observability
  - dashboard
aliases:
  - AI 运行看板
source_checked: 2026-07-14
lang: zh-CN
translation_key: 运行监控/02-生产监控/05-Dashboard与诊断视图.md
translation_route: en/runtime-monitoring/production-monitoring/05-dashboards-and-diagnostic-views
translation_default_route: zh-CN/运行监控/02-生产监控/05-Dashboard与诊断视图
---

# Dashboard 与诊断视图

## 本节目标

设计一个能快速回答“用户是否受影响、从何时开始、哪些版本/任务受影响、去哪下钻”的Dashboard，并避免用双轴图、均值和不完整数据制造虚假结论。

## 先定义观众和问题

一个面向值班人员的事件Dashboard，与面向产品负责人的周度质量/成本看板不应完全相同。每个看板顶部先写：

- 对象、用途和负责人；
- 环境、时区、默认窗口和数据新鲜度；
- SLI/指标口径版本；
- 什么决策可以从本看板做出，什么不能；
- runbook、发布记录、告警和Trace搜索入口。

## 一个四层结构

### 1. 用户影响概览

- 可用性与延迟SLI、SLO、错误预算燃烧；
- 任务质量、标签覆盖/新鲜度、安全事件和单任务成本；
- 当前流量、与基线的变化和数据缺失告警。

### 2. 范围分解

按环境、release、任务类型、有业务意义的风险切片、供应商/模型和结果类型分解。分解不等于无限labels；用户ID、request ID和自由文本应通过Log/Trace查询。

### 3. 诊断信号

- 检索、模型、工具、网关、队列和观测管线的延迟/错误/饱和度；
- 服务按RED组织Rate、Errors、Duration，资源按USE组织Utilization、Saturation、Errors；
- token、缓存、重试、Agent步数和费用分解；
- 标签回流延迟、Trace完整率和日志丢弃量。

### 4. 证据下钻

从异常点进入筛选后的Trace列表，再进入单次span与相关结构化Log。下钻应传递当前时间窗口、release和任务过滤，避免值班人员到新页后重新猜条件。

## 发布和口径注释

在时间线上标注：应用/模型/Prompt/检索/工具release，网关路由或安全策略变化，数据口径变更，供应商公告与业务活动。注释提供关联线索，不是因果证明。“发布后指标变了”仍需对比release切片、Trace和共同外部变化。

## 诚实展示数据不完整

看板应显示：

- 最后成功采集时间和端到端数据延迟；
- 发送、接收、丢弃和采样的记录量；
- 标签覆盖率、安全检查覆盖率、Trace完整率；
- 样本量过少或无数据状态；
- 口径版本和历史曲线的不可比较分界。

不要把无数据绘成零。“安全事件=0”和“安全采集中断”需要完全不同的视觉语义和行动。

## 图表选择和易误导方式

- 延迟用p50/p95/p99或直方图，不只显示平均数；
- 比率同时显示分子、分母或样本量；
- 对release对比使用相同窗口、任务分布和口径；
- 费用与流量分开：总费用、每请求、每成功任务均可能需要；
- 尽量避免两个独立Y轴制造视觉相关；
- 用一致单位和明确时区，指标名不用“分数”等没有语义的词。

## 练习与自测

在纸上为一个Tool-Calling Agent画一页事件Dashboard wireframe，必须包含用户SLI、质量/安全/成本、release注释、范围分解、观测完整性与Trace下钻。回答：

1. 为什么p95比单独平均延迟更能暴露尾部问题？
2. 为什么数据中断时不能显示为0？
3. 为什么release注释与指标异常同时出现仍不能自动证明release是根因？

## 小结与下一步

好Dashboard是一条决策与诊断路径，不是指标墙。当分布变化进入看板时，需用 [[运行监控/02-生产监控/06-漂移、反馈与标签延迟|漂移、反馈与标签延迟]] 的证据边界解释。

## 参考资料

- [Google SRE: Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)（访问于2026-07-14；百分位、用户视角与指标口径）
- [OpenTelemetry Observability primer](https://opentelemetry.io/docs/concepts/observability-primer/)（访问于2026-07-14）
- [Prometheus Metric and label naming](https://prometheus.io/docs/practices/naming/)（访问于2026-07-14；若使用Prometheus，需再核对当前命名约定）
- [Prometheus Histograms and summaries](https://prometheus.io/docs/practices/histograms/)（访问于2026-07-14；不同Histogram类型的聚合和版本能力不同）
