---
title: "Pareto 权衡与敏感性分析"
tags:
  - llm
  - pareto
  - decision-analysis
aliases:
  - 模型选择多目标决策
source_checked: 2026-07-18
content_origin: original
content_status: dynamic
lang: zh-CN
translation_key: 现代LLM能力与模型选择/07-Pareto权衡与敏感性分析.md
translation_route: en/modern-llm-capabilities-and-model-selection/07-pareto-trade-offs-and-sensitivity-analysis
translation_default_route: zh-CN/现代LLM能力与模型选择/07-Pareto权衡与敏感性分析
---

# Pareto 权衡与敏感性分析

## 本节目标

在通过硬门槛的候选中识别不可被全面超越的方案，并检验结论是否依赖脆弱权重。

## 核心概念

若候选 A 在所有关心指标上都不差于 B，且至少一项更好，则 A **支配** B。未被其他候选支配的集合是 **Pareto 前沿**。

加权分数可以辅助排序，但它有三个前提：

1. 只对通过 gate 的候选计算；
2. 每个指标方向、单位和归一化方式公开；
3. 权重来源、变更和敏感性可追溯。

总分不是自然真理。它把不同价值判断压缩成一个数字，不能替代原始指标和失败样本。

## 为什么需要

高质量、低延迟和低成本通常不能同时达到最优。直接把所有维度平均会隐藏真实选择：一个候选可能更可靠但更慢，另一个更便宜但关键切片稍弱。Pareto 前沿先删除“全面更差”的候选，再让责任人对真实权衡做决定。

## 怎样实现

### 统一方向但保留原值

质量类越大越好；延迟、成本和失败率越小越好。可把预算内余量转为 0–1 utility，例如：

```text
latency_headroom = max(0, 1 - p95_latency / latency_gate)
cost_headroom = max(0, 1 - avg_cost / cost_gate)
```

同时必须展示原始 `p95_ms` 和 `avg_cost`，避免 utility 隐去单位。

### 做敏感性分析

至少准备基准、质量优先和效率优先三组预注册权重。记录每组完整排名、赢家是否变化、分差是否接近测量噪声。若轻微权重变化就换赢家，结论应标为“偏好敏感”，而不是宣布绝对最佳。

离线项目只做这三组**声明权重情景**的离散比较，输出 `sensitivity_scope: declared_weight_sets_only`。`winner_stable_across_declared_weights=true` 仅表示这几个点的赢家相同，不等于对所有合理权重局部稳定，更不包含 trial 统计不确定性。生产决策可另做权重区间扫描、局部扰动和测量误差传播，但应明确方法与范围。

### 形成决策记录

写明选择、拒绝原因、残余风险、owner、有效期、模型版本和重新评测触发器。模型目录、价格、政策或任务分布变化都可能触发重评。

## 常见失败

- 在 gate 之前算总分，违规候选仍排第一。
- 用当前候选的 min–max 动态归一化，加入一个差候选就改变所有分数。
- 只给最终分数，不给原值、公式和权重。
- 在看完结果后调权重直到偏好候选获胜。
- 分差小于 trial 波动仍作确定性排名。

## 怎样验证

手工构造一个候选：它在每项指标都比另一个差，程序必须将其标为被支配。再让质量权重和效率权重互换；若赢家改变，报告必须显式显示不稳定，而不是只输出基准排名。

## 实践任务

用三位相关方独立给出权重，再讨论差异。先不看候选名称，只看匿名原始指标、gate 和 Pareto 前沿；记录最终取舍及哪项新证据会改变决定。

## 参考资料

- [HELM：多场景、多指标与透明评测](https://crfm.stanford.edu/helm/index.html)
- NIST，[AI 600-1](https://doi.org/10.6028/NIST.AI.600-1)
- Mitchell 等，[Model Cards for Model Reporting](https://doi.org/10.1145/3287560.3287596)
