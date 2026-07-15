---
title: 项目：离线 Agent 威胁评审
aliases:
  - Offline Agent Threat Review
  - Agent 安全评审项目
tags:
  - ai-security
  - project
  - python
source_checked: 2026-07-14
---

# 项目：离线 Agent 威胁评审

## 你要完成什么

对一个“读取一封邮件并生成草稿，绝不自动发送”的 Agent 建立严格场景契约，并用确定性 Python 规则找出从不可信邮件到工具、身份、数据出站、供应链和运营控制的风险。项目离线运行，不调用模型、连接器或网络，不需要密钥。

这不是漏洞扫描器或渗透测试。它训练的是一条可复用工程链：

```text
用途/非目标 → 资产与边界 → 能力/身份/依赖 → 控制契约
           → 确定性发现 → PASS/REVIEW/BLOCK → 回归测试
```

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `examples/threat_review.py` | 严格 JSON 解析、契约校验、11 条教学规则、决策与 CLI |
| `examples/agent_scenario_vulnerable.json` | 故意暴露过多能力的场景，预期 `BLOCK` |
| `examples/agent_scenario_hardened.json` | 最小权限只读场景，预期 `PASS` |
| `examples/agent_scenario_contract_error.json` | 含未知字段，预期契约错误 |
| `examples/test_threat_review.py` | 合同、规则、指纹、CLI 与自测的回归测试 |

输入显式声明资产分类、信任边界、不可信来源、身份 scope/有效期、工具副作用与目的地、依赖来源、审批/沙箱/出站/记忆/审计控制和风险政策。严格契约拒绝重复 JSON key、`NaN`、未知字段、悬空引用和错误类型，避免“脏输入被静默解释”。

## 运行环境

- Windows 11 + PowerShell 7；
- 当前稳定 Python 3；
- 只使用标准库，不安装依赖。

从本笔记所在目录运行：

```powershell
Set-Location '.\examples'

# 漏洞场景：退出码 1，action=BLOCK
python -B .\threat_review.py --scenario .\agent_scenario_vulnerable.json

# 加固场景：退出码 0，action=PASS
python -B .\threat_review.py --scenario .\agent_scenario_hardened.json

# 输入契约错误：退出码 2
python -B .\threat_review.py --scenario .\agent_scenario_contract_error.json

# 内置冒烟检查
python -B .\threat_review.py --self-test

# 50 项测试；再用 -O 和 warnings-as-errors 验证测试不依赖 assert/警告
python -B -m unittest discover -s . -p 'test_*.py' -v
python -B -O -m unittest discover -s . -p 'test_*.py'
python -B -W error -m unittest discover -s . -p 'test_*.py'
```

PowerShell 中退出码在 `$LASTEXITCODE`。这里 `BLOCK/REVIEW` 返回 1 是预期业务决策，不等于程序崩溃。

## 阅读实现

### 1. 严格契约

`load_json` 拒绝重复 key 和非标准常量；`validate_scenario` 对每层做精确字段、类型、枚举、唯一 ID 与引用完整性检查，并返回深拷贝。契约错误统一退出 2。

### 2. 11 条教学发现

规则覆盖间接注入到副作用工具、非必要功能、共享/长期/过宽身份、弱审批、目的地缺少约束、敏感数据无出站验证、依赖未固定/未验证、沙箱不足、工具参数未验证、记忆投毒以及审计/限流/紧急停用缺失。

每条发现都含资产、攻击路径、影响、建议控制、负责人和验证方法。结果按严重度与 ID 稳定排序，便于 diff 和门禁。

### 3. 决策与证据指纹

场景内冻结哪些严重度 `BLOCK`、哪些需要 `REVIEW`；无触发项才 `PASS`。报告用场景与发现的规范 JSON 计算 SHA-256 指纹，帮助确认比较的是同一证据，但指纹不是数字签名，也不能证明输入真实。

## 验收任务

### 基础验收

- [ ] 漏洞场景产生 `AS-001` 到 `AS-011`，动作为 `BLOCK`。
- [ ] 加固场景无发现，动作为 `PASS`。
- [ ] 契约错误场景返回退出码 2，不产生看似有效报告。
- [ ] 三种测试模式全部通过且不生成缓存。

### 理解验收

逐条解释为什么漏洞场景触发 11 项规则，并把每项映射到本库相应课程。特别说明：为什么删除 `send_mail` 比提示模型“不要发送”更强；为什么工具 schema 仍需授权；为什么 `PASS` 不能声称系统已安全。

### 扩展任务

复制加固场景，构造一个只把依赖 `pinned` 改为 `false` 的场景，确认得到 `REVIEW` 和 `AS-007`。再设计自己的“共享盘转工单”JSON；先写预期发现和决策，再运行。若要新增字段，先改契约和失败测试，不要让未知字段静默通过。

## 自测题

1. 为什么外部内容、模型输出和工具返回都应视为不可信？
2. `required_for_purpose` 如何帮助发现功能过多？它为什么不能代替人工威胁建模？
3. 同一个身份同时有 `mail.read` 与 `mail.send` 的爆炸半径是什么？
4. 为什么批准要绑定规范化参数与状态版本？
5. 报告指纹能证明什么，不能证明什么？
6. 规则全部未触发时，还缺哪些真实验证？

参考答案要点：确定性规则只能检查声明的有限契约；没有执行真实模型、身份提供方、工具、沙箱或网络，也没有验证 JSON 声明是否符合部署。因此 `PASS` 只表示“该输入未触发教学规则”。

## 进一步学习

- 回看 [[AI安全/01-基础与风险/01-资产信任边界与威胁建模|资产、信任边界与威胁建模]]。
- 把发现转为 [[评测体系/00-目录|评测体系]] 中的安全回归与发布门。
- 将拒绝、审批与紧急停用事件接入 [[运行监控/00-目录|运行监控]]。

## 参考资料

- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)（获取日期：2026-07-14）
- [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)（2025 年 12 月发布；获取日期：2026-07-14）
- [MITRE ATLAS](https://atlas.mitre.org/)（获取日期：2026-07-14）
