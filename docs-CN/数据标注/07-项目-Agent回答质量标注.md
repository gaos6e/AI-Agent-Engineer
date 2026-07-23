---
title: "项目：Agent 回答质量标注"
tags:
  - ai-agent-engineer
  - data-annotation
  - project
aliases:
  - Agent Answer Annotation Project
content_origin: original
content_status: validated
source_checked: 2026-07-22
source_baseline:
  - Cohen 1960 original kappa paper
  - Python 3 json and unittest documentation
  - W3C PROV-O
lang: zh-CN
translation_key: 数据标注/07-项目-Agent回答质量标注.md
translation_route: en/data-annotation/07-project-agent-answer-quality-annotation
translation_default_route: zh-CN/数据标注/07-项目-Agent回答质量标注
---

# 项目：Agent 回答质量标注

## 目标与边界

用 [[数据标注/examples/sample_annotations.jsonl|sample_annotations.jsonl]] 的固定双人初标，计算百分比一致率、Cohen's kappa、混淆计数和冲突列表；再把冲突转成一份需要补写的指南/裁决计划。[[数据标注/examples/audit_annotations.py|audit_annotations.py]] 先验证 JSONL、输入快照、合同版本和全批次配对；[[数据标注/examples/test_audit_annotations.py|test_audit_annotations.py]] 覆盖 12 类正常与失败行为。

示例内容完全虚构，只含匿名 ID、版本与简短虚构证据，不联网、不读取真实日志、不调用模型。它是**双人名义标签的教学审计器**，不是标注平台、裁决系统、隐私/许可审查器或生产发布工具。

## 环境与运行

从 vault 根目录在 Windows / PowerShell 中运行。环境放在 vault 外，脚本只读输入、不生成数据文件：

```powershell
$exampleDir = (Resolve-Path '.\Knowledge\AI Agent Engineer\docs\数据标注\examples').Path
$venv = Join-Path $env:LOCALAPPDATA 'Gao-venvs\annotation-audit'
$python = Join-Path $venv 'Scripts\python.exe'

py -3.11 -m venv $venv
& $python --version
& $python -B (Join-Path $exampleDir 'audit_annotations.py') `
  (Join-Path $exampleDir 'sample_annotations.jsonl')
& $python -O -B (Join-Path $exampleDir 'audit_annotations.py') `
  (Join-Path $exampleDir 'sample_annotations.jsonl')
& $python -B -W error -m unittest discover -s $exampleDir -p 'test_*.py' -v
& $python -O -B -W error -m unittest discover -s $exampleDir -p 'test_*.py' -v
```

项目仅依赖 Python 3.11+ 标准库；`-B` 防止生成 `__pycache__`，`-O` 验证关键合同检查没有依赖会被优化掉的裸 `assert`，`-W error` 使意外警告成为失败。

## 输入合同

每行必须是无重复键、无 `NaN`/`Infinity` 的标准 JSON 对象。示例要求以下非空字符串：

| 字段 | 用途 | 本项目验证的范围 |
| --- | --- | --- |
| `annotation_id` | 追加初标事件的唯一标识 | 整个 JSONL 内不得重复 |
| `sample_id` | 逻辑样本 | 两名固定标注者各一条 |
| `source_revision` | 标注者实际看到的虚构输入版本 | 同一 `sample_id` 的两条必须相同 |
| `data_version` | 本批数据快照 | 整批唯一 |
| `guideline_version` | 判断规则 | 整批唯一 |
| `label_set_version` | 标签本体 | 整批唯一 |
| `task_config_version` | 界面/Schema 合同 | 整批唯一 |
| `annotator` | 匿名标注者角色 | 整批恰好两名 |
| `label` | `helpful/not_helpful/unsafe/cannot_judge/exclude` | 枚举校验 |
| `evidence` | 对该初标的简短证据 | 只验证非空，不评价事实性 |
| `created_at` | 初标发生时间 | 只接受 `YYYY-MM-DDTHH:MM:SSZ` 的 UTC 秒级教学格式 |

`source_revision` 只是输入追溯：它不证明内容来源已授权、没有个人信息或标签正确。示例故意不接受任意扩展字段，以便教学中暴露合同漂移；真实系统可在版本化 schema 中添加 assignment、访问、模型建议、复审和裁决字段，而不要把它们塞进初标记录后覆盖历史。

## 预期结果与手算

样例有 8 个 `sample_id`，每个均由 `ann-a` 与 `ann-b` 对同一 `source_revision` 独立初标，且所有记录使用 `data_version=v1`、`guideline_version=1.0`、`label_set_version=1.0`、`task_config_version=agent-answer-v1`：

- 一致 6 个，所以 $p_o=6/8=0.75$。
- A 的 `helpful/not_helpful/unsafe` 数量为 4/2/2；B 为 3/4/1。
- $p_e=(4/8)(3/8)+(2/8)(4/8)+(2/8)(1/8)=22/64=0.34375$。
- $\kappa=(0.75-0.34375)/(1-0.34375)=13/21\approx0.619$。
- 冲突为 `s-003 (demo-s-003-r1): unsafe ↔ not_helpful` 与 `s-005 (demo-s-005-r1): helpful ↔ not_helpful`。

这个结果只描述 8 个虚构样本上的双人名义标签一致性。它不证明指南正确、样本代表线上分布、`final_label` 已存在、许可/隐私已通过，或任何真实系统的质量结论。

## 本轮验证

> [!success] 2026-07-22 验证通过
> `python -B -W error -m unittest discover` 与 `python -O -B -W error -m unittest discover` 均通过 12 项；CLI 普通与 `-O` 输出一致。测试使用临时目录，不留下项目内缓存或数据产物。

测试覆盖样例合同/配对、手算指标、冲突/混淆、常量完美一致时 `kappa=undefined`、重复/缺失标注者、第三人、混合数据/标签/界面版本、未知标签、重复 `annotation_id`、输入快照不一致、缺失追溯字段、空证据、非 UTC 时间、未知字段、非法/重复键 JSON、非标准常量、空 pairs 和 CLI 上下文。

## 项目步骤

1. 先阅读 JSONL，确认每个 `sample_id` 有 `ann-a`、`ann-b` 两条记录，并对比其 `source_revision` 与合同版本。
2. 运行普通与 `-O` CLI，记录 observed agreement、expected agreement、kappa、混淆和冲突。
3. 对每条冲突写出“当前指南缺什么规则/证据”，不要在两人之间随意选一方；设计追加的裁决记录，包括规则引用、裁决者角色和 `final_label`。
4. 新增 5 个**虚构**样本和两名独立答案；每对使用同一新 `source_revision`，不要改变既有样本的历史记录。
5. 设计一个 release manifest：用途、输入范围、切分、版本、质量门、访问范围和已知限制；再讨论这一教学 batch 为什么不能直接发布为评测集。

完整的裁决、release 与线上候选边界见 [[数据标注/09-版本、发布与生产反馈|版本、发布与生产反馈]]；敏感/真实内容进入任务前先完成 [[数据标注/08-数据治理、隐私、许可与劳动安全|治理审查]]。

## 验收

- [ ] 能解释脚本如何按 `sample_id` 配对，并拒绝两个标注者看了不同 `source_revision` 的伪配对。
- [ ] 能手算 observed、expected 与 kappa，并解释其不等于正确性或代表性。
- [ ] 能提出至少一项指南修订、一项抽样改进和一份追加裁决记录。
- [ ] 能列出从 `annotation_id` 到 `release_id` 之间仍需由生产系统补齐的工件。
- [ ] 不把虚构示例结果当作真实系统质量、许可、隐私或劳动安全结论。

## 自测

1. 两条标签 `sample_id` 相同但 `source_revision` 不同，为什么不能计算有意义的一致性？
2. 类别极不平衡时，为什么 kappa 和百分比一致率可能差很多？
3. 标注者看到模型建议后，一致率升高一定是好事吗？
4. 若来源撤回，哪些 release 和下游用途需要查询，为什么不能直接说模型已遗忘？

完成标准：能运行审计、解释每个量、定位冲突，并把冲突反馈为可执行的指南、裁决和发布计划。

返回 [[数据标注/00-目录|数据标注目录]]。

## 参考资料

资料核验日期：2026-07-22。

- Cohen, J. (1960). [A coefficient of agreement for nominal scales](https://doi.org/10.1177/001316446002000104)
- [Python `json`](https://docs.python.org/3/library/json.html)、[Python `unittest`](https://docs.python.org/3/library/unittest.html)
- [W3C PROV-O](https://www.w3.org/TR/prov-o/)
