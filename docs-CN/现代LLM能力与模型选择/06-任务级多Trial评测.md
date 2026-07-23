---
title: "任务级多 Trial 评测"
tags:
  - llm
  - evaluation
  - trials
aliases:
  - 模型候选评测协议
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: zh-CN
translation_key: 现代LLM能力与模型选择/06-任务级多Trial评测.md
translation_route: en/modern-llm-capabilities-and-model-selection/06-task-level-multi-trial-evaluation
translation_default_route: zh-CN/现代LLM能力与模型选择/06-任务级多Trial评测
---

# 任务级多 Trial 评测

## 本节目标

用同一任务分布、harness 和多次运行得到可比较证据，避免把单次随机输出当模型属性。

## 核心概念

- `task`：待完成工作及成功标准；
- `case`：一次冻结输入、环境初态和期望证据；
- `trial`：某候选对某 case 的一次独立运行，拥有全局唯一 `trial_id`；同一 `case_id` 可以且通常应重复；
- `trace`：模型、工具、重试、usage、延迟和状态变化；
- `outcome`：外部 grader 或环境终态判定的结果。

LLM 服务和 Agent 轨迹可能具有随机性或运行时波动。多 trial 的目标不是假装消除所有不确定性，而是暴露成功率、尾部失败和方差。

## 为什么需要

一个候选在同一 case 上可能成功两次、失败一次；只挑最好输出会高估它。单次平均延迟也看不到尾部。HELM 的标准化思想要求候选使用一致场景与适配策略；私有评测还需固定 provider adapter、prompt、工具、温度、预算和重试。

## 怎样实现

### 冻结协议

记录：dataset 版本与切片、请求的模型 ID/别名、响应中实际返回的模型/版本（接口提供时）、endpoint/region、prompt/tool schema、采样参数、最大 token/步骤、缓存、并发、重试、grader 和代码 commit。不要把 `latest`、预览或便捷别名当作天然固定的实验单元；当模型生命周期、版本解析、服务区域或 runtime 控制面变化时，建立新的评测版本并比较回归。

### 运行设计

1. 每个候选先 warm-up，不把初始化混入正式延迟；
2. 随机化候选运行顺序，减少时段偏差；
3. 每个候选、每个 case 运行预先约定的 trial 数，以 `trial_id` 区分重复运行；`min_trials_per_case` 不能用不同 case 的总数替代；
4. 保留 timeout、拒答和解析失败，不丢弃“异常值”；
5. 分别报告 overall 与关键切片，记录 p50/p95、usage 和单位任务成本。

> [!warning] 小样本分位数边界
> 项目使用 nearest-rank p95 只为展示确定性聚合。在每候选仅 6 次教学 trial 时，p95 实际等于样本最大值；它只能描述这批已记录运行，不能证明稳定尾延迟、SLA 或统计不确定性。生产评测应预注册足够样本量，并结合时间窗口、负载分层、置信区间或 bootstrap 等适合当前决策的方法。

确定性 assertion 优先；主观维度用有锚点 rubric，并用人工金标准校准 grader。涉及高风险决策时，不把未校准的模型 judge 当唯一门槛。

## 常见失败

- 候选之间 prompt、工具或 retry 不同，却归因于模型。
- 只跑一次或只展示成功样本。
- 只报告平均值，不报告失败类别、切片和尾延迟。
- 在看到结果后调整 case、阈值或权重，却不建立新评测版本。
- 测试集泄漏到 prompt 优化或人工挑选过程。

## 怎样验证

检查每个结果能否沿 `decision → candidate → case_id → trial_id → trace → grader → outcome` 回溯。重复运行一个固定小样本，若差异超过发布阈值，应增加 trial、隔离基础设施波动或调查模型/服务版本。

## 实践任务

对两个候选、12 个 case 各运行至少 3 次。按“成功、schema、工具、超时、拒答”分类，报告总体与高风险切片成功率、p95 延迟和平均成本；禁止手工删掉失败 trial。

## 参考资料

- [HELM](https://crfm.stanford.edu/helm/index.html)
- Liang 等，[Holistic Evaluation of Language Models](https://arxiv.org/abs/2211.09110)
- [Gemini API 模型版本命名](https://ai.google.dev/gemini-api/docs/models)
- [Claude 模型 ID 与版本](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions)
- [[评测体系/00-目录|本库：评测体系]]
