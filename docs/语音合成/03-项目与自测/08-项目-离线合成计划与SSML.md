---
title: 项目：离线合成计划与 SSML
tags:
  - ai-agent-engineer
  - tts
  - project
aliases:
  - TTS 合成计划项目
source_checked: 2026-07-14
---

# 项目：离线合成计划与 SSML

## 项目目标

从匿名 JSON 请求生成结构化“合成计划”和基础 SSML，校验声音白名单、授权引用、语言、输入长度和 XML 结构。程序明确把每项状态设为 `not_generated`，不调用服务、不下载模型，也不生成音频。

资产：

- [[语音合成/03-项目与自测/examples/tts_requests.json|tts_requests.json]]
- [[语音合成/03-项目与自测/examples/build_tts_plan.py|build_tts_plan.py]]
- [[语音合成/03-项目与自测/examples/test_contract_and_cli.py|test_contract_and_cli.py]]

## 运行

```powershell
Set-Location 'X:\path\to\your-vault\Knowledge\AI Agent Engineer\docs\语音合成\03-项目与自测\examples'
python -B .\build_tts_plan.py .\tts_requests.json
python -B .\build_tts_plan.py --self-test
python -B -m unittest discover -s . -p 'test_*.py'
python -B -O -m unittest discover -s . -p 'test_*.py'
python -B -W error -m unittest discover -s . -p 'test_*.py'
```

程序只向终端打印 JSON，不提供写文件参数，避免在练习时留下合成计划或敏感文本副本。当前回归集共 **63 项**；普通、`-O` 和 warnings-as-errors 三种模式都应通过。

## 输入与退出码合同

输入必须是 UTF-8 严格 JSON；重复键、`NaN`/`Infinity`、未知字段、错误类型和不符合本项目 BCP 47 子集的语言标签会被拒绝。策略白名单必须非空且无重复，请求字段为封闭集合；这套教学合同不等于任一供应商 API。

- 退出码 `0`：结构合同与全部策略检查通过。
- 退出码 `1`：结构合同有效，但声音/速率/强调不在白名单、文本超长或请求 ID 重复。
- 退出码 `2`：文件、UTF-8、JSON 或结构合同错误。

## 安全设计

- 用户文本通过 `xml.etree.ElementTree` 写入节点，特殊字符自动转义。
- 语言、声音、速率和强调来自白名单，不接受任意 XML。
- 每个请求有授权引用和用途；缺失时返回契约错误。
- `source_text_sha256` 支持不保存全文的关联检查，但摘要也可能被字典猜测，不能视为匿名化。
- 输出含 `generation_status: not_generated`，防止把计划误报为已生成音频。

## 扩展任务

1. 删除授权引用，确认脚本非零退出。
2. 输入 `A&B <测试>`，检查 SSML 中的安全转义与解析结果。
3. 增加供应商适配层前，先定义核心标签白名单和降级行为。
4. 新增一个策略失败夹具，在测试内创建并清理临时文件，确认退出码为 `1` 且不产生音频或报告文件。

## 验收标准

- [ ] 默认夹具退出码为 `0`，策略失败为 `1`，结构合同失败为 `2`。
- [ ] 63 项测试在普通、`-O` 和 warnings-as-errors 三种模式均通过，工作区无缓存、报告或音频文件。
- [ ] 能解释 SSML 命名空间、文本转义和供应商子集差异。
- [ ] 能区分“计划校验成功”和“音频质量已验证”；本项目只证明前者。
- [ ] 能为一个新增语言补声音授权、读法规则和评测计划，而不是只换语言代码。

完成后回到 [[语音合成/00-目录|语音合成目录]]，并将授权与评测接入 [[AI治理/00-目录|AI 治理]] 和 [[评测体系/00-目录|评测体系]]。
