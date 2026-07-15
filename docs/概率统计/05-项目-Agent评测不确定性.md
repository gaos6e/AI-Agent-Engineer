---
title: 项目：Agent 评测不确定性
tags:
  - AI-Agent-Engineer
  - 概率统计
  - 综合实践
aliases:
  - 配对 Bootstrap 项目
source_checked: 2026-07-14
source_baseline:
  - NIST Bootstrap Plot and Percentiles
  - Efron 1979 bootstrap paper
  - Python 3.14.6 statistics and random documentation
---

# 项目：Agent 评测不确定性

## 项目目标

对同一批 12 个任务的 A/B 二元得分做配对比较，报告 $B-A$ 平均差和 95% percentile bootstrap 区间。你需要验证方向、配对、输入边界、分位数方法与可复现性，并用证据边界解释结果。

实现：[[概率统计/examples/bootstrap_eval.py|bootstrap_eval.py]]｜测试：[[概率统计/examples/test_bootstrap_eval.py|test_bootstrap_eval.py]]。

## 输入契约

- 每个 `(A_i, B_i)` 对应同一个唯一任务，顺序不能打乱。
- 得分只能是 `0` 或 `1`，其中 1 表示按预先冻结的评分规则通过。
- 12 个任务只是教学样本，不宣称代表所有 Agent 流量。
- 差值方向固定为 $d_i=B_i-A_i$；正数有利于 B。
- Bootstrap 的重抽样单位是“任务差值”，不是单个 A/B 得分，也不是 bootstrap 生成的行。

## 方法分解

1. 计算每个任务的差值 $d_i=B_i-A_i$。
2. 从 12 个差值中有放回抽取 12 个，计算均值。
3. 重复 10,000 次，形成 bootstrap 统计量经验分布。
4. 用 R7 风格线性插值取 2.5% 和 97.5% 分位数。
5. 报告原始平均差、区间、任务数、重复次数、随机种子和方法名。

这是一种简单的 **paired percentile bootstrap**。分位数存在多种约定，percentile 区间也不是所有统计量和小样本的最优方法。本项目用它建立重抽样直觉，不把它包装成通用统计结论。

固定随机种子只让 Monte Carlo 重抽样可复现，不会增加任务代表性、评分可靠性或因果证据。提高 `repeats` 只减少模拟误差，不会把 12 个任务变成更大的真实样本。

## 运行与测试

在 vault 根目录运行：

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B '.\Knowledge\AI Agent Engineer\docs\概率统计\examples\bootstrap_eval.py'
python -B -m unittest discover `
    -s '.\Knowledge\AI Agent Engineer\docs\概率统计\examples' `
    -p 'test_*.py' `
    -v
```

脚本预期输出：

```text
method=paired-percentile-bootstrap
tasks=12 repeats=10000 seed=20260714
A mean=0.583
B mean=0.833
B-A=0.250
confidence=0.950 interval=[-0.083, 0.583]
```

测试应有 8 项通过，覆盖：

- 分位数端点、插值与非法输入；
- 全部平局和全部 B 获胜的退化情形；
- 固定数据、方向与随机种子可复现性；
- 非法得分、空样本、重复次数、置信水平和 seed。

> [!success] 2026-07-14 实际验证
> 在 Python 3.11.9 下，脚本以普通模式和 `python -O` 模式运行结果一致；8 项 `unittest` 全部通过，两个 Python 文件也通过 `py_compile` 语法检查。验证生成的 `__pycache__` 已在验收后删除，未作为知识库内容保留。

## 逐步读代码

1. `PAIRED_SCORES` 保留同一任务的 A/B 对应关系。
2. `linear_quantile` 先排序，再按 $(n-1)p$ 位置做线性插值；函数拒绝空值、越界概率和非有限数。
3. `_validate_pairs` 明确拒绝非二元分数与损坏的 pair。
4. `paired_bootstrap` 先计算观测差，再对差值有放回抽样。
5. `BootstrapResult` 将方法参数和结果放在同一不可变记录中。
6. 测试验证特殊情况，不只检查“脚本能打印”。

## 结果解释

本样例观测到 B 比 A 高 `0.25`，即 25 个百分点；但区间约为 `[-0.083, 0.583]`，跨过 0。对当前设计，合理表述是：

> 在这 12 个预先选定任务上，B 相对 A 的平均二元得分差为 +0.25；配对 percentile bootstrap 95% 区间为约 [-0.083, 0.583]。区间同时容许轻微退化与较大提升，当前样本不足以确定方向。该区间只近似当前任务抽样的不确定性；任务代表性、评分误差和生成随机性仍未覆盖。

不能写成“B 有 95% 概率更好”，也不能因点估计为正就宣称上线。即使区间不跨 0，也仍要对照预设的最小实际差异、延迟、成本与安全护栏。

## 必做扩展

1. **重复样本陷阱**：将每个任务机械复制 20 次，观察区间如何虚假变窄；解释为何行数增长不等于独立信息增长。
2. **分层报告**：给任务补 `检索型/工具型` 标签，分别报告样本量、点估计和区间；不要只挑表现最好的层。
3. **真实样本量**：增加新的、代表目标总体的唯一任务，而不是只提高 bootstrap 次数。
4. **生成层级**：每个任务为 A/B 各生成 5 次，先明确 estimand，再决定按任务聚合还是做层级重抽样。
5. **工程决策**：同时报告延迟与费用，写出上线所需的最小实际改善和护栏阈值。
6. **方法敏感性**：比较不同分位数定义或区间方法时，记录实现与差异，不只挑最窄区间。

## 常见错误

- 分别重抽 A 与 B，破坏同一任务的配对。
- 看到 B-A 为正就忽略宽区间。
- 把 `repeats=100000` 当作 10 万个真实任务。
- 复制任务、重复生成或评分者打分被当作独立样本。
- 改随机种子直到区间看起来更有利。
- 事后删除超时、失败或“异常任务”，却不报告排除规则。
- 把 percentile 区间称作无需假设、对任何问题都准确的 95% 保证。

## 自测与掌握标准

- [ ] 我能解释有放回抽样以及为何每次仍抽 12 个差值。
- [ ] 我没有分别打乱 A/B，且能说明差值方向。
- [ ] 我报告点估计、区间、样本量、方法、重复次数和 seed。
- [ ] 我知道分位数算法有多种定义，percentile bootstrap 有适用限制。
- [ ] 我没有把 bootstrap 当成修复选择偏差或相关样本的方法。
- [ ] 我能列出任务抽样、生成、评分和线上分布四类未覆盖不确定性。
- [ ] 我能把统计结果与最小实际差异、延迟、成本和安全护栏连接起来。

上一节：[[概率统计/04A-评测设计、效应量与统计陷阱|评测设计、效应量与统计陷阱]]｜完成后返回 [[概率统计/00-目录|概率统计]]。

## 参考资料

核验日期：**2026-07-14**。

- [NIST：Bootstrap Plot](https://www.itl.nist.gov/div898/handbook/eda/section3/bootplot.htm)
- [NIST：Percentiles](https://www.itl.nist.gov/div898/handbook/prc/section2/prc262.htm)
- [Efron (1979), Bootstrap Methods: Another Look at the Jackknife](https://doi.org/10.1214/aos/1176344552)
- [Python `statistics`](https://docs.python.org/3/library/statistics.html)
- [Python `random`](https://docs.python.org/3/library/random.html)
