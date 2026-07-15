---
title: SKILL.md 前置元数据与渐进式披露
aliases:
  - SKILL.md frontmatter
tags:
  - Agent-Skills
  - 上下文工程
source_checked: 2026-07-14
---

# SKILL.md 前置元数据与渐进式披露

## 本节目标

能写出合法 frontmatter，并解释 metadata、完整指令和资源为什么分三层加载。

## 文件的两个部分

`SKILL.md` 由文件开头两个 `---` 之间的 YAML frontmatter 和其后的 Markdown body 组成：

```markdown
---
name: text-statistics
description: Count words, characters, and lines. Use when a user needs deterministic text-size statistics.
compatibility: Requires Python 3; no network access.
---

# Text Statistics

Follow the workflow below...
```

YAML 不是任意 `key: value` 文本。值中含冒号等特殊字符时应加引号或使用合适 YAML 多行语法，并用正式解析器/官方校验器检查。

不要用课程里的简化解析器证明任意 YAML 合法：锚点、多行块、转义、布尔值和嵌套结构都可能超出它的支持范围。发布前应运行官方 `skills-ref validate`，再在目标 client 中测试发现、激活与资源读取。

## 字段约束

根据 2026-07-14 官方规范：

- `name` 必需，1～64 字符，只能用小写 `a-z`、数字和连字符；不能以连字符开头/结尾，不能连续两个连字符，并且必须匹配父目录名。
- `description` 必需，1～1024 字符；同时说明“做什么”和“何时使用”，包含有助于发现的具体关键词。
- `license` 可选，写许可证名称或随包许可证文件引用。
- `compatibility` 可选，1～500 字符；只在存在产品、系统包、网络等环境要求时使用。
- `metadata` 可选，是字符串键值映射；键名宜避免与其他实现冲突。
- `allowed-tools` 可选且仍为实验字段，不同实现支持程度可能不同，不能当通用安全保证。

## 三层渐进式披露

1. **发现层**：启动时只加载所有 Skill 的 `name` 与 `description`，成本约为每项少量 metadata。
2. **激活层**：任务匹配后加载完整 `SKILL.md` body。官方建议主文件保持在 500 行以内，并在渐进披露说明中以少于约 5000 tokens 为目标；这是上下文经济建议，不是“超过就不兼容”的规范断言。
3. **资源层**：脚本、references、assets 只在指令明确需要时读取或执行。

因此 `description` 决定“能否被发现”，body 决定“激活后怎么做”，资源承担“条件性细节”。把长 API 参考放进 body 会让每次激活都支付上下文成本；只把路径丢进目录又会让 agent 不知何时读取。

## 拆分示例

一个“处理支付 API 错误”的 Skill：

- `SKILL.md` 保留正常流程、重试边界、绝不能记录 token 的 gotcha。
- `references/api-errors.md` 保存错误码详解，并写明“仅当响应非 2xx 时读取”。
- `scripts/validate_payload.py` 做确定性 schema 校验。
- `assets/report-template.md` 是最终审计报告模板。

安全限制若必须在执行前知道，放 `SKILL.md`，不要深藏在可能永远不读的 reference。

## 练习与自测

1. 找出非法 name：`PDF-tools`、`-pdf`、`pdf--tools`、`pdf-tools`。只有最后一个合法（仍须与目录名一致）。
2. 将一份 700 行错误码文档拆成 body + reference，并写一句精确的加载条件。
3. 自测：为什么“有 `allowed-tools`”不能证明脚本安全？因为字段是实验性的，client 支持和实际脚本行为仍需独立验证。

## 下一步

学习 [[Agent Skills/学习路线/03-触发描述与范围边界|触发描述与范围边界]]。

## 参考资料

- [Agent Skills Specification](https://agentskills.io/specification)（获取日期：2026-07-14）
- [Adding skills support: progressive disclosure](https://agentskills.io/client-implementation/adding-skills-support)（获取日期：2026-07-14；用于理解 client 侧三层加载，不作为本轮官方译文树）
