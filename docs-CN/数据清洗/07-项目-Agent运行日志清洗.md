---
title: "项目：Agent 运行日志清洗"
tags:
  - ai-agent-engineer
  - data-quality
  - project
aliases:
  - Agent Log Cleaning Project
source_checked: 2026-07-14
source_baseline:
  - Python 3 csv, datetime, tempfile and unittest documentation
  - RFC 4180 and RFC 3339
lang: zh-CN
translation_key: 数据清洗/07-项目-Agent运行日志清洗.md
translation_route: en/data-cleaning/07-project-agent-run-log-cleaning
translation_default_route: zh-CN/数据清洗/07-项目-Agent运行日志清洗
---

# 项目：Agent 运行日志清洗

## 目标

把故意含空格、重复 ID、非法状态、缺失字段和异常延迟的 [[数据清洗/examples/dirty_agent_runs.csv|dirty_agent_runs.csv]] 分成清洁数据与问题报告。[[数据清洗/examples/clean_agent_runs.py|clean_agent_runs.py]]只使用 Python 标准库，适合先理解契约、审计和发布边界，再迁移到 pandas；[[数据清洗/examples/test_clean_agent_runs.py|test_clean_agent_runs.py]]固定 10 类正常、边界和失败行为。

## 环境与运行

从 vault 根目录在 Windows 11 / PowerShell 7 中运行。环境放在 vault 外，输出放入临时目录；脚本通过绝对路径核对，永远拒绝输入、清洁输出和问题报告指向同一文件。

```powershell
$exampleDir = (Resolve-Path '.\Knowledge\AI Agent Engineer\docs\数据清洗\examples').Path
$venv = Join-Path $env:LOCALAPPDATA 'Gao-venvs\data-cleaning'
$python = Join-Path $venv 'Scripts\python.exe'
$runDir = Join-Path $env:TEMP 'gao-agent-log-cleaning'
$out = Join-Path $runDir 'clean_agent_runs.csv'
$report = Join-Path $runDir 'agent_run_issues.csv'

py -3.11 -m venv $venv
& $python -m pip --version
New-Item -ItemType Directory -Path $runDir -Force | Out-Null
& $python -B (Join-Path $exampleDir 'clean_agent_runs.py') `
  --input (Join-Path $exampleDir 'dirty_agent_runs.csv') `
  --output $out `
  --report $report `
  --overwrite
Get-Content -LiteralPath $out
Get-Content -LiteralPath $report
& $python -B -m unittest discover -s $exampleDir -p 'test_*.py' -v
& $python -B -O -m unittest discover -s $exampleDir -p 'test_*.py' -v
```

项目没有第三方依赖，`pip --version` 只确认解释器归属。`--overwrite` 只显式允许替换既有 output/report；即使提供该开关，输入路径重合仍会被拒绝。输出位于 `%TEMP%`，不会在 vault 中制造生成物。

## 预期结果与解释

教学输入共有 8 行：3 行接受、5 行隔离。命令行摘要应包含：

```text
accepted=3 rejected=5 reasons=duplicate:run_id=1,invalid:latency_ms_range=1,invalid:started_at=1,invalid:status=1,missing:run_id=1
```

清洁文件保留 `run-001`、`run-002`、`run-003`；其中 `2026-07-13T09:02:00+08:00` 统一为 `2026-07-13T01:02:00Z`。问题报告只保存 CSV 结束行号、规范化 `run_id`、稳定 reason code 和原始行 SHA-256，不复制 query 正文。

> [!warning] 摘要不是匿名化
> `row_sha256` 用于验证和关联同一原始行，不会自动消除低熵值的枚举风险；真实系统仍需限制报告访问、最小化 `run_id` 并设置留存周期。

## 规则说明

- 表头必须与五个字段的名称和顺序完全一致，防止未知列被静默丢弃。
- 标识、状态、时间和延迟去首尾空格；query 只统一换行和首尾空白，保留内部连续空格。
- 把 `ok/failed/canceled` 映射为固定枚举 `success/error/cancelled`。
- 时间必须能解析且含时区，输出统一为 UTC `Z`；输入含微秒时保留微秒精度。
- 延迟必须是十进制整数并位于 `0..300000`；`-5` 是范围错误，`1_000` 是表示/类型错误。
- `run_id`、`started_at`、`status`、`latency_ms`、`query` 都是本练习必填字段。
- `run_id` 首次出现即占有身份，即使该行随后无效；同 ID 后续行进入问题报告，不静默用“更干净”的后到记录改写历史。
- 两个输出均先在目标目录完整写入临时文件再替换目标；同输入与规则可逐字节复现。

## 本轮验证

> [!success] 2026-07-14 验证通过
> Python 3.11.9 下 `py_compile` 通过；10 项 `unittest` 在普通与 `-O` 模式下均通过；CLI 普通/`-O` 的 stdout、清洁 CSV 和问题报告分别一致；样例源文件哈希保持不变；临时验证目录与项目内 `__pycache__` 已清理。

测试覆盖 UTC 转换、query 内部空白、状态映射、首次无效 ID 的身份策略、稳定 reason code、样例 3/5 分流、逐字节幂等、显式覆盖/路径重合、严格 schema 和 CLI 摘要。

## 验收与扩展

- [ ] 清洁文件只含有效、唯一 ID。
- [ ] 问题报告包含原始行号和明确原因代码。
- [ ] 修改输入后重复运行，规则与结果仍可解释。
- [ ] 新增 `model` 字段及允许列表，并为未知模型增加规则。
- [ ] 比较“拒绝异常延迟”与“保留并标记异常”对 p95 的影响。
- [ ] 删除 `--overwrite` 后验证既有输出会被拒绝，再说明这为何是安全默认值。
- [ ] 增加一条含多行 Markdown/代码的 query，证明内部空白不会被折叠。

## 自测

1. 为什么不能把非法延迟统一改成 0？
2. 为什么重复 `run_id` 不能总是保留最后一条？
3. 哪些规范化可以划分前做，哪些统计填补只能训练集拟合？
4. 怎样证明脚本没有覆盖原始文件？

完成标准：能运行脚本、解释每个拒绝原因，并写出一条新的契约规则与相应测试样本。

返回 [[数据清洗/00-目录|数据清洗目录]]。

## 参考资料

资料核验日期：2026-07-14。

- [Python `csv`](https://docs.python.org/3/library/csv.html)
- [Python `datetime`](https://docs.python.org/3/library/datetime.html)
- [Python `tempfile`](https://docs.python.org/3/library/tempfile.html)
- [RFC 4180: CSV](https://www.rfc-editor.org/rfc/rfc4180)
- [RFC 3339: Internet timestamps](https://www.rfc-editor.org/rfc/rfc3339)
