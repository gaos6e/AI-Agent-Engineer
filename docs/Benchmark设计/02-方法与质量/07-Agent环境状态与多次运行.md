---
title: Agent环境状态与多次运行
aliases:
  - Agent benchmark environments
  - Agent运行协议
tags:
  - Benchmark
  - Agent
  - 运行协议
source_checked: 2026-07-21
content_origin: original
content_status: validated
source_baseline: "Anthropic与OpenAI官方Agent评测资料，以及SWE-bench、WebArena、OSWorld和tau-\
  bench原始论文，截至2026-07-21"
---

# Agent 环境、状态与多次运行

## 本节目标

把文本题目的 Benchmark 扩展为真正可复现的 Agent 任务：冻结环境与工具，声明初始状态、允许动作和期望最终状态，隔离副作用，并用多次 trial 呈现随机系统的成功率与稳定性。

## 直觉解释

评测问答模型时，常见输入是一段文本、输出是一段文本；Agent 却会读写外部世界。它可能调用错误工具、重复付款、污染下一次运行的数据库，或者虽然回答“完成了”但环境根本没改变。因此 Agent Benchmark 的测量单位不是最后一句话，而是：

> 在确定的初始状态、权限、工具和预算下运行一次完整任务，再验证最终状态、动作副作用与运行成本。

## 首次出现的术语

- **environment（环境）**：Agent 能观察和改变的外部系统，例如文件夹、数据库、网页或模拟订单服务。
- **initial state（初始状态）**：每个 trial 开始前可验证的环境快照。
- **final state / outcome（最终状态）**：任务结束后真正存在的状态，不等于 Agent 自报的结果。
- **side effect（副作用）**：执行带来的额外状态变化；它可以是允许的，也可能是重复写入、越权读取等禁止行为。
- **harness（运行框架）**：负责 setup、启动系统、提供工具、施加预算、记录轨迹、评分和 reset 的代码。
- **trial（试次）**：同一系统在同一 case 契约下的一次独立运行。
- **reset（重置）**：把环境恢复到该 case 的已知初始状态，并清除缓存、会话和临时数据。

## 一个 Agent case 的最小契约

| 字段 | 要回答的问题 | 示例 |
| --- | --- | --- |
| task ID / family ID | 这是什么任务，和哪些变体同源？ | `test-safety` / `refund-family` |
| environment ID | 运行在哪个可重建环境？ | `offline-order-fixture-v1` |
| initial state | 开始前怎样验证干净状态？ | 订单存在且未退款 |
| instruction | 用户要求什么？ | 查询状态并要求直接退款 |
| tool schema与权限 | 可以观察或改变什么？ | 只读`order_lookup` |
| success outcome | 最终怎样才算成功？ | 返回状态并拒绝写操作 |
| forbidden side effects | 即使完成也不能发生什么？ | `refund_order` |
| budgets | 最多步数、时间、重试和成本？ | 8步、30秒、0重试 |
| trials | 独立重复多少次？ | 3次教学trial |
| teardown/reset | 如何检查并清理？ | 恢复fixture并核对哈希 |

任务模板应同时保存 setup 与 grader。只保存自然语言指令会让后来的人无法知道“订单是否原本已退款”“工具返回是否固定”或“写操作是否真的发生”。

## Setup、运行、评分与 Reset

1. **setup**：从版本化快照创建环境，检查初始状态和工具版本；失败则标记 harness error，不把任务交给 Agent。
2. **run**：启动全新的会话，注入同一工具定义和权限，记录每一步动作、状态、时延和成本。
3. **stop**：达到成功、显式失败、最大步数、超时或不可恢复错误时，按预先规则停止。
4. **grade**：先验证最终状态，再检查禁止副作用、工具权限和资源约束；文本解释只是辅助证据。
5. **reset**：销毁或恢复环境，并验证与初始快照一致；重置失败时暂停后续 trial，不能带污染继续跑。

> [!warning] Unknown 不是缺失值
> 若运行日志损坏、grader无法读取状态或reset失败，结果应显式记为`Unknown`或harness error，并按冻结规则进入分母或触发重跑审查。删除这条记录会让失败系统看起来更好。

## 多 trial 与最小统计直觉

即使temperature为0，服务、工具、网络、并发和实现细节也可能带来非确定性。一个 case 运行 $R$ 次，令成功记为$x_r=1$、失败记为0，经验成功率是：

$$
\hat p=\frac{1}{R}\sum_{r=1}^{R}x_r
$$

例如三次结果为`[1, 1, 0]`，经验成功率是$2/3$，不能只挑最好的一次写成“成功”。同时报告：

- 每个 task 的 trial 成功率；
- 在 trial 间是否稳定；
- 总体与切片的 task 成功率；
- 超时、error、Unknown 的数量；
- 均值和p95时延、成本或工具调用数。

trial 不是扩大样本总体的魔法。同一 case 的重复结果相关，不能把15次trial冒充15个独立任务；任务层比较和trial层波动应分别保留。

`pass@k`表示$k$次中至少一次成功，适合产品确实允许多次独立尝试的场景；`pass^k`表示$k$次都成功，适合要求连续可靠的场景。由单次成功率$p$推导`1-(1-p)^k`或$p^k`要求试次同分布且独立；共享缓存、环境状态、重试适配或供应商故障会让公式失真。因此应优先从实际trial与真实重试策略报告这两个量，并同时给出每次尝试成本、总预算和**每个成功结果的期望成本**。高`pass@k`若依赖昂贵的反复重试，不等于一次运行可靠。

## 可比运行与不可比条件

| 变化 | 默认处理 | 原因 |
| --- | --- | --- |
| 同一协议，仅系统实现不同 | 可以比较 | 目标变量明确 |
| 候选多一步预算或多一次重试 | 不可直接排名 | 资源条件改变 |
| 工具schema或权限不同 | 不可直接归因于模型能力 | SUT边界改变 |
| 环境快照不同 | 不可比较 | 初始难度和数据可能不同 |
| 同协议但随机trial结果不同 | 保留全部并做配对/重复分析 | 这是系统变异 |
| reset失败后继续运行 | 该批次无效 | trial不再独立且初始状态未知 |

架构差异确实可能需要不同工具或预算。此时可另开赛道，或把声明改为“完整系统在各自资源约束下的效用—成本比较”，但不能继续声称是同资源下的能力排名。

## 原始 Benchmark 给出的设计启发

- SWE-bench把代码仓库与issue交给系统，并用可复现的容器化harness执行测试；它提醒我们代码补丁必须在固定仓库状态与测试环境中验证。
- WebArena构建可交互网站环境，并以任务执行的功能正确性评分；这说明网页Agent需要真实状态，而不是只评最终自然语言。
- OSWorld原始论文明确包含初始状态setup与execution-based evaluation；这直接对应“先还原环境，再验证最终状态”的设计。
- $\tau$-bench研究工具—Agent—用户交互，并强调多轮工具任务和多次运行的可靠性；课程只借鉴其设计问题，不引用会变化的排行榜名次。

这些是原始来源中的案例，不是要求所有团队复制其任务、容器或指标。

## 常见错误与排查

- **只判最后一句是否包含“完成”**：改为查询数据库、文件或网页最终状态。
- **允许候选获得更多步数**：要么统一预算，要么建立不同资源赛道。
- **多个trial共享会话或缓存**：每次创建新会话并验证reset。
- **超时后重跑到成功再保留**：按预先retry规则保存每次结果。
- **动作安全就等于任务成功**：安全与成功是两条独立条件；拒绝所有动作可能很安全但无用。
- **grader崩溃就删case**：标记Unknown/harness error，修复后重跑完整可比较批次。

## 练习

1. 为“把CSV汇总成报告”写initial state、final state、允许文件、禁止副作用和reset步骤。
2. 设计一个候选多一次重试的对比，分别写“不可比”结论与可接受的独立赛道名称。
3. 给`[1,1,0]`与`[1,0,1]`两组trial结果写出成功率、稳定性解释和仍缺少的证据。

## 自测

1. 为什么Agent自报“成功”不足以评分？因为真正的任务结果在外部环境，且可能伴随未声明副作用。
2. reset为什么属于Benchmark协议而不是清理细节？它决定下一个trial的初始条件，直接影响可比性。
3. 三次trial能否证明生产成功率？不能；它只展示当前case、当前协议下的有限重复结果。
4. 工具权限不同但候选更高分，能否宣布模型更强？不能；最多比较不同完整系统，且要公开资源差异。

## 小结与下一步

Agent Benchmark 的核心是可重建环境、状态验证、副作用约束、预算和独立重复。接下来完成 [[Benchmark设计/03-项目与自测/08-项目-构建可维护Benchmark|项目：构建可维护 Benchmark]]，亲自验证协议不一致为什么必须先判不可比。

## 参考资料

以下资料获取/复核于2026-07-21；只引用设计方法，不引用动态榜单成绩：

- [SWE-bench官方仓库与harness](https://github.com/SWE-bench/SWE-bench)
- [SWE-bench原始论文](https://arxiv.org/abs/2310.06770)
- [WebArena原始论文](https://arxiv.org/abs/2307.13854)
- [OSWorld原始论文](https://arxiv.org/abs/2404.07972)
- [$\tau$-bench原始论文](https://arxiv.org/abs/2406.12045)
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)（发布于2026-01-09；task、trial、隔离、`pass@k`与`pass^k`）
- [OpenAI: A shared playbook for trustworthy third party evaluations](https://openai.com/index/trustworthy-third-party-evaluations-foundations/)（发布于2026-05-29；系统预算与每成功任务成本）
