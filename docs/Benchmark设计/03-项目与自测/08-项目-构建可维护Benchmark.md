---
title: 项目：构建可维护Benchmark
aliases:
  - Maintainable benchmark project
  - 离线Benchmark项目
tags:
  - Benchmark
  - 项目
  - Python
source_checked: 2026-07-14
---

# 项目：构建可维护 Benchmark

## 项目目标

使用Windows 11、PowerShell 7和Python 3标准库，运行一个完全离线的订单Agent Benchmark。你将验证：

- spec、cases、results三类严格JSON契约；
- 重复key、非标准NaN、布尔冒充数字和未知字段被拒绝；
- 唯一ID、train/development/test、family污染和冻结私有测试完整覆盖；
- 环境、工具、reset、步数、超时、重试与trial数量完全一致才可比较；
- 最终状态、禁止副作用、工具权限、Unknown、时延、成本和多trial稳定性；
- 按task与slice汇总、固定种子配对bootstrap和证据指纹；
- 关键任务失败优先于总体分数提升，协议不一致优先判`INCOMPARABLE`。

> [!warning] 解释边界
> 这里只有5个可见的合成测试task，每个3次教学trial；`is_private`演示的是契约字段，不会把本地文件变成真正私有测试。结果不能估计真实用户、供应商模型或生产系统表现，成本单位也不是账单。

## 项目文件

- [[Benchmark设计/03-项目与自测/examples/run_benchmark.py|run_benchmark.py]]：契约验证、grader、指标、可比性和决策CLI；
- [[Benchmark设计/03-项目与自测/examples/benchmark_spec.json|benchmark_spec.json]]：声明、基线、冻结协议、门禁与bootstrap设置；
- [[Benchmark设计/03-项目与自测/examples/benchmark_cases.json|benchmark_cases.json]]：train/development/test、family、初始/最终状态和风险；
- [[Benchmark设计/03-项目与自测/examples/benchmark_results_pass.json|benchmark_results_pass.json]]：baseline与正常candidate的多trial结果；
- [[Benchmark设计/03-项目与自测/examples/benchmark_results_regression.json|benchmark_results_regression.json]]：总体优于baseline但关键安全task失败；
- [[Benchmark设计/03-项目与自测/examples/benchmark_spec_protocol_mismatch.json|benchmark_spec_protocol_mismatch.json]]：冻结步数与结果包不一致；
- [[Benchmark设计/03-项目与自测/examples/benchmark_cases_contract_error.json|benchmark_cases_contract_error.json]]：同一family跨train/test的非法fixture；
- [[Benchmark设计/03-项目与自测/examples/test_run_benchmark.py|test_run_benchmark.py]]：42项标准库`unittest`测试。

## 环境准备

项目没有第三方依赖，可以直接运行Python 3。若要练习隔离环境，请把venv建在vault之外：

```powershell
$venvDir = Join-Path $env:TEMP "ai-agent-engineer-benchmark-venv"
python -m venv $venvDir
& (Join-Path $venvDir "Scripts\Activate.ps1")
# 本项目无需 pip install。
```

进入项目目录：

```powershell
$projectDir = "X:\path\to\your-vault\Knowledge\AI Agent Engineer\docs\Benchmark设计\03-项目与自测\examples"
Push-Location $projectDir
```

所有命令使用`-B`，避免生成`__pycache__`和`.pyc`。

## 三类严格契约

### Benchmark spec

spec固定Benchmark ID/版本、声明、目标总体、baseline、主指标、私有测试冻结状态、protocol、gates和bootstrap。protocol包括环境、工具集、reset策略、最大步数、超时、重试和trial数量。任何影响比较条件的变化都必须显式进入协议或版本。

### Cases

每个case包含唯一ID、family、split、slice、critical、任务类型、私有标记、初始状态、期望最终状态、允许工具和禁止副作用。验证器要求：

- train、development和test都存在；
- 只有test可标记为private，且spec声明测试已冻结；
- 同一family不能跨split；
- test是唯一进入排名的划分。

### Results

结果包恰好包含一个baseline和一个candidate。每个系统必须对每个冻结test task提供`trial_count`条记录；case或trial缺失、重复、未知都返回契约错误，不能用剩余样本得到更好分数。记录显式保存`success/timeout/error/unknown`、最终状态、副作用、工具、时延和成本。

## 评分与统计

每个trial同时检查：

1. 状态是`success`；
2. 最终状态与契约一致；
3. 未发生禁止副作用；
4. 所用工具是允许工具的子集。

task通过要求其trial成功率达到独立的`task_min_trial_success_rate`冻结门；总体发布再检查`min_primary_task_success_rate`。critical task还必须达到更严格的critical门。报告包含task/family/slice成功率、最终状态trial率、副作用安全trial率、稳定task比例、Unknown数量、均值/p95时延、平均成本、slice差距和逐task/逐trial证据。

baseline与candidate在相同task上形成配对差$d_i$，固定种子bootstrap从这些task差值重采样。trial不被冒充为独立task；5个task仍然是很小的教学样本。

## 决策优先级

1. baseline或candidate协议与spec不一致：`INCOMPARABLE`，不计算排名；
2. critical task失败：`BLOCK`，即使总体成功率高于baseline；
3. 总体、最终状态、副作用安全或稳定性硬门未过：`BLOCK`；
4. slice差距、时延、成本或bootstrap下界触发软门：`REVIEW`；
5. 全部满足：`PASS`。

退出码契约：`0=PASS`，`1=REVIEW/BLOCK/INCOMPARABLE`，`2=文件、JSON、schema、版本或覆盖契约错误`。

## 运行正常候选

```powershell
python -B .\run_benchmark.py
if ($LASTEXITCODE -ne 0) { throw "PASS fixture exit code mismatch" }
```

预期`action=PASS`、candidate task success为`1.0`、baseline为`0.6`，且输出包含15个candidate trial和`sha256:`证据指纹。程序只向stdout写JSON。

## 运行关键回归

```powershell
python -B .\run_benchmark.py `
  --results .\benchmark_results_regression.json `
  --candidate candidate-regression
if ($LASTEXITCODE -ne 1) { throw "regression fixture exit code mismatch" }
```

预期`action=BLOCK`，首要理由包含`test-safety`。candidate总体task success为`0.8`，仍高于baseline的`0.6`；但三次trial都执行了禁止的`refund_order`，关键安全失败不能被排行榜提升抵消。

## 运行协议不可比

```powershell
python -B .\run_benchmark.py `
  --spec .\benchmark_spec_protocol_mismatch.json
if ($LASTEXITCODE -ne 1) { throw "protocol mismatch exit code mismatch" }
```

该spec冻结`max_steps=9`，结果包记录`max_steps=8`。预期`action=INCOMPARABLE`、`comparable=false`且不输出系统指标；不能先排名再把协议差异放进脚注。

## 运行非法数据契约

```powershell
python -B .\run_benchmark.py `
  --cases .\benchmark_cases_contract_error.json
if ($LASTEXITCODE -ne 2) { throw "contract-error fixture exit code mismatch" }
```

预期stderr包含`split contamination`，因为`family-leaked-status`同时出现在train和test。

## 三模式测试与语法检查

```powershell
python -B -m unittest -v test_run_benchmark
if ($LASTEXITCODE -ne 0) { throw "normal tests failed" }

python -B -O -m unittest -v test_run_benchmark
if ($LASTEXITCODE -ne 0) { throw "optimized tests failed" }

python -B -W error -m unittest -v test_run_benchmark
if ($LASTEXITCODE -ne 0) { throw "warnings-as-errors tests failed" }

python -B -c "from pathlib import Path; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in map(Path, ('run_benchmark.py', 'test_run_benchmark.py'))]"
if ($LASTEXITCODE -ne 0) { throw "syntax check failed" }
Pop-Location
```

## 动手练习

1. 删除candidate的一条trial记录，确认整个结果包退出2，而不是静默缩小分母；
2. 新增`candidate-review`fixture，只超过p95软门，验证退出1且决策为REVIEW；
3. 让一个case的三次结果为`[通过,通过,失败]`，说明task成功门和trial稳定性分别如何变化；
4. 新增一个critical privacy task，先写“总体均值仍高但必须BLOCK”的失败测试；
5. 把按task bootstrap改为按family重采样，并说明当前每个test family只有一个task时为何结果相同；
6. 设计真正的私有测试服务：公开spec与grader接口，但控制case访问、提交预算和反馈粒度。

## 自测题

1. 为什么缺失case应是契约错误，而Unknown可以是已记录的失败状态？
2. candidate总体优于baseline时，什么情况仍应BLOCK？
3. 协议多一步预算为什么不是普通warning？
4. trial数量变多是否等于任务总体覆盖变广？
5. 证据指纹能证明数据合法或运行机器可信吗？

## 掌握检查

- [ ] 能解释spec、cases和results的职责与版本关系；
- [ ] 能区分PASS、REVIEW、BLOCK、INCOMPARABLE和契约错误；
- [ ] 能证明关键任务与协议一致性优先于总体均值或排名；
- [ ] 能从task、trial、slice、最终状态和副作用读取结果；
- [ ] 能运行42项测试和四类CLI场景并解释退出码；
- [ ] 能列出真实系统仍需补充的容器/服务、权限隔离、私有测试、人工审计和线上证据。

## 项目边界与下一步

项目验证的是离线契约、固定fixture和确定性grader，没有真实模型/API、容器、浏览器、用户模拟器、生产账单或在线监控。真实Agent Benchmark应结合 [[Benchmark设计/02-方法与质量/07-Agent环境状态与多次运行|Agent环境、状态与多次运行]] 构建可重建harness，并用 [[Benchmark设计/02-方法与质量/06-Leaderboard机制与维护|Leaderboard机制与维护]] 管理私有测试和版本。

## 参考资料

以下来源获取/复核于2026-07-14：

- [MLPerf Inference官方规则](https://github.com/mlcommons/inference_policies/blob/master/inference_rules.adoc)（公平、协议、复现与审计案例；采用时核对当期规则）
- [SWE-bench官方仓库](https://github.com/SWE-bench/SWE-bench)（容器化可复现harness案例）
- [OSWorld原始论文](https://arxiv.org/abs/2404.07972)（初始状态setup与execution-based evaluation案例）
- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- [NIST/SEMATECH置信区间](https://www.itl.nist.gov/div898/handbook/prc/section1/prc14.htm)
