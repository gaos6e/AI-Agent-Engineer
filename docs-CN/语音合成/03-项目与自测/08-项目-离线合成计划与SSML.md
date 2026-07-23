---
title: "项目：离线合成计划与 SSML"
tags:
  - ai-agent-engineer
  - tts
  - project
aliases:
  - TTS 合成计划项目
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: zh-CN
translation_key: 语音合成/03-项目与自测/08-项目-离线合成计划与SSML.md
translation_route: en/text-to-speech/project-and-self-check/08-project-offline-synthesis-plan-and-ssml
translation_default_route: zh-CN/语音合成/03-项目与自测/08-项目-离线合成计划与SSML
---

# 项目：离线合成计划与 SSML

## 项目目标

从匿名 JSON 请求生成结构化“合成计划”并在内存中构造/校验基础 SSML，校验声音目录、语言—声音匹配、允许用途、策略内授权引用、`acl_reference` 的结构存在性、输入长度和 XML 结构。程序明确把每项状态设为 `not_generated`，不调用服务、不下载模型，也不生成音频。

资产：

- [[语音合成/03-项目与自测/examples/tts_requests.json|tts_requests.json]]
- [[语音合成/03-项目与自测/examples/build_tts_plan.py|build_tts_plan.py]]
- [[语音合成/03-项目与自测/examples/test_contract_and_cli.py|test_contract_and_cli.py]]

## 运行

以下命令从同时包含 `docs/` 与 `.website/` 的项目根目录运行：

```powershell
Push-Location -LiteralPath 'docs\语音合成\03-项目与自测\examples'
python -B .\build_tts_plan.py .\tts_requests.json
python -B .\build_tts_plan.py --self-test
python -B -m unittest discover -s . -p 'test_*.py'
python -B -O -m unittest discover -s . -p 'test_*.py'
python -B -W error -m unittest discover -s . -p 'test_*.py'
Pop-Location
```

程序只向终端打印脱敏 JSON，不提供写文件参数；计划只含原文/SSML 的 SHA-256 和结构 profile，不回显原文或完整 SSML，避免在练习时留下敏感文本副本。当前回归集共 **73 项**；普通、`-O` 和 warnings-as-errors 三种模式都应通过。

## 输入与退出码合同

输入必须是 UTF-8 严格 JSON；重复键、`NaN`/`Infinity`、未知字段、错误类型和不符合本项目 BCP 47 子集的语言标签会被拒绝。顶层 `schema_version` 为 `"1.1"`；`policy` 要有 `policy_revision`、非空 `voice_catalog`、速率/强调白名单和 `disclosure_required`。每个声音 profile 显式列出 `voice_id`、支持语言、允许用途与策略内授权引用；每个请求使用本地 `operation_id`，并带 `source_revision`、`acl_reference`、用途和授权引用。真实接入时的 `provider_request_id` 由供应商响应产生，应与 provider、响应/receipt 分开记录；它不是本项目的输入字段，不能用于本地幂等或去重。这套教学合同不等于任一供应商 API、声音目录或权利审核系统。

- 退出码 `0`：结构合同与全部策略检查通过。
- 退出码 `1`：结构合同有效，但声音/语言/用途/策略内授权引用不匹配、速率/强调不在白名单、文本超长或 `operation_id` 重复。
- 退出码 `2`：文件、UTF-8、JSON 或结构合同错误。

## 安全设计

- 用户文本通过 `xml.etree.ElementTree` 写入节点，特殊字符自动转义。
- 语言、声音、速率和强调来自本地策略，不接受任意 XML；语言必须与所选声音 profile 的允许集合匹配。
- 每个请求有 `source_revision`、`acl_reference`、授权引用和用途；缺失时返回契约错误。脚本只做 `acl_reference` 的非空结构检查并把它写入计划，**不查询、allowlist 或验证对象级 ACL**；真实对象授权必须由外部身份/授权系统在生成、读取、发布前判定。脚本同样不验证真实合同、同意、有效期或法律充分性。
- `source_text_sha256` 支持不保存全文的关联检查，但摘要也可能被字典猜测，不能视为匿名化。
- 输出含 `ssml_sha256` 与 `ssml_profile`，但不输出完整 SSML；完整 XML 行为由单元测试中的合成夹具验证。
- 输出含 `generation_status: not_generated`、`audio_generated: false` 与 `source_text_exposed: false`，防止把计划误报为已生成音频或把默认终端输出当成安全存储。

## 扩展任务

1. 删除 `source_revision` 或 `acl_reference`，确认脚本以结构错误退出；再替换为任意非空引用，观察离线项目只记录它而不声称授权通过。
2. 输入 `A&B <测试>`，通过单元测试检查 SSML 中的安全转义与解析结果，而不是把敏感原文打印到默认 CLI。
3. 把中文声音改为 `en-US`，确认语言—声音策略失败；再改变用途或策略内授权引用，观察不同错误。
4. 增加供应商适配层前，先定义核心标签、输出格式、披露、降级和未知终态行为。
5. 新增一个策略失败夹具，在测试内创建并清理临时文件，确认退出码为 `1` 且不产生音频或报告文件。

## 验收标准

- [ ] 默认夹具退出码为 `0`，策略失败为 `1`，结构合同失败为 `2`。
- [ ] 73 项测试在普通、`-O` 和 warnings-as-errors 三种模式均通过，工作区无缓存、报告或音频文件。
- [ ] 能解释 SSML 命名空间、文本转义和供应商子集差异。
- [ ] 能区分“计划校验成功”和“音频质量已验证”；本项目只证明前者。
- [ ] 能为一个新增语言补声音授权、读法规则和评测计划，而不是只换语言代码。

完成后回到 [[语音合成/00-目录|语音合成目录]]，并将授权与评测接入 [[AI治理/00-目录|AI 治理]] 和 [[评测体系/00-目录|评测体系]]。
