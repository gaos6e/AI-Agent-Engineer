---
title: 项目：Agent 回答质量标注
tags:
  - ai-agent-engineer
  - data-annotation
  - project
aliases:
  - Agent Answer Annotation Project
source_checked: 2026-07-14
source_baseline:
  - Cohen 1960 original kappa paper
  - Python 3 json and unittest documentation
---

# 项目：Agent 回答质量标注

## 目标

用 [[数据标注/examples/sample_annotations.jsonl|sample_annotations.jsonl]] 的固定双人标注计算一致率、Cohen's kappa、混淆计数和冲突列表，再把冲突转成指南修订。[[数据标注/examples/audit_annotations.py|audit_annotations.py]]先验证 JSONL、标签、数据/指南版本和全批次标注者身份；[[数据标注/examples/test_audit_annotations.py|test_audit_annotations.py]]覆盖 10 类正常与失败行为。示例内容虚构，只含匿名 ID、版本与标签。

## 环境与运行

从 vault 根目录在 Windows 11 / PowerShell 7 中运行；环境放在 vault 外，脚本只读输入、不联网、不生成数据文件：

```powershell
$exampleDir = (Resolve-Path '.\Knowledge\AI Agent Engineer\docs\数据标注\examples').Path
$venv = Join-Path $env:LOCALAPPDATA 'Gao-venvs\annotation-audit'
$python = Join-Path $venv 'Scripts\python.exe'

py -3.11 -m venv $venv
& $python -m pip --version
& $python -B (Join-Path $exampleDir 'audit_annotations.py') `
  (Join-Path $exampleDir 'sample_annotations.jsonl')
& $python -B -O (Join-Path $exampleDir 'audit_annotations.py') `
  (Join-Path $exampleDir 'sample_annotations.jsonl')
& $python -B -m unittest discover -s $exampleDir -p 'test_*.py' -v
& $python -B -O -m unittest discover -s $exampleDir -p 'test_*.py' -v
```

项目没有第三方依赖，`pip --version` 只确认解释器归属。普通与 `-O` 模式应得到相同审计输出；关键校验使用显式异常而不是会被优化掉的裸 `assert`。

## 预期结果与手算

样例有 8 个 sample，每个都由 `ann-a` 与 `ann-b` 在 `data_version=v1`、`guideline_version=1.0` 下独立标注：

- 一致 6 个，所以 $p_o=6/8=0.75$。
- A 的 `helpful/not_helpful/unsafe` 数量为 4/2/2；B 为 3/4/1。
- $p_e=(4/8)(3/8)+(2/8)(4/8)+(2/8)(1/8)=22/64=0.34375$。
- $\kappa=(0.75-0.34375)/(1-0.34375)=13/21\approx0.619$。
- 冲突为 `s-003: unsafe ↔ not_helpful` 与 `s-005: helpful ↔ not_helpful`。

这个结果只描述 8 个虚构样本上的双人名义标签一致性。它不证明指南正确、样本代表线上分布，也不提供统计稳定的质量结论。

## 输入契约

- 每行必须是无重复键的标准 JSON 对象，空行、`NaN`/`Infinity` 和未知字段会被拒绝。
- 必填 `sample_id`、`data_version`、`guideline_version`、`annotator`、`label`，值必须是非空字符串。
- 标签只能是 `helpful/not_helpful/unsafe/cannot_judge/exclude`。
- 整批必须恰好两名固定标注者，且数据与指南版本各自唯一；每个 sample 两人各一条。
- `evidence`、`created_at` 可选，但存在时必须是字符串；项目不声称审计其内容质量。

## 本轮验证

> [!success] 2026-07-14 验证通过
> Python 3.11.9 下 `py_compile` 通过；CLI 普通与 `-O` 输出一致；10 项 `unittest` 在普通与 `-O` 模式下均通过；项目内 `__pycache__` 已清理，未创建其他产物。

测试覆盖样例版本/配对、手算指标、冲突/混淆、常量完美一致时 `kappa=undefined`、重复/缺失标注者、三名标注者、混合版本、未知标签、非法/重复键 JSON、空 pairs 和 CLI 上下文。

## 项目步骤

1. 先阅读 JSONL，确认每个 `sample_id` 有 `ann-a`、`ann-b` 两条记录，且数据/指南版本一致。
2. 运行脚本并记录 observed agreement、expected agreement、kappa。
3. 查看混淆与冲突；两人没有“多数票”，不要随意选一方，为每条写出缺失的指南规则和裁决证据。
4. 新增 5 个样本和两名标注者的独立答案，再运行。
5. 选择一条冲突，模拟专家裁决并记录规则引用与指南版本。

## 验收

- [ ] 能解释脚本如何按 `sample_id` 配对。
- [ ] 能手算其中至少四个样本的一致率。
- [ ] 能说明高一致率为何不证明标签正确。
- [ ] 能提出至少一项指南修订和一项抽样改进。
- [ ] 不把示例结果当作任何真实系统的质量结论。
- [ ] 能构造“所有样本都标 helpful”的批次，并解释 observed=expected=1 时 kappa 为什么未定义。

## 自测

1. 类别极不平衡时，为什么 kappa 和百分比一致率可能差很多？
2. 标注者看到模型建议后，一致率升高一定是好事吗？
3. 哪些样本需要双标，哪些需要专家裁决？
4. 指南升级后，怎样判断旧标签要不要重做？

完成标准：能运行审计、解释每个量、定位冲突，并将冲突反馈为可执行指南变更。

返回 [[数据标注/00-目录|数据标注目录]]。

## 参考资料

资料核验日期：2026-07-14。

- Cohen, J. (1960). [A coefficient of agreement for nominal scales](https://doi.org/10.1177/001316446002000104)
- [Python `json`](https://docs.python.org/3/library/json.html)
- [Python `unittest`](https://docs.python.org/3/library/unittest.html)
