---
title: "Token、上下文窗口与预算"
tags:
  - context-engineering
  - tokens
  - context-window
aliases:
  - 上下文预算
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline:
  - OpenAI Conversation state guide
  - Anthropic Context windows documentation
  - Google Gemini Long context documentation
lang: zh-CN
translation_key: 上下文工程/02-Token、上下文窗口与预算.md
translation_route: en/context-engineering/02-tokens-context-windows-and-budgets
translation_default_route: zh-CN/上下文工程/02-Token、上下文窗口与预算
---

# Token、上下文窗口与预算

## 本节目标

理解 token、上下文窗口、输入/输出用量与工程预算，并避免把“装得下”误认为“用得好”。

## 三个不同概念

**Token** 是模型处理输入和生成输出的计量单位，可能对应一个字、词的一部分、标点或空白；不同 tokenizer、模型、语言与内容类型结果不同。字符数或单词数只能做容量预估，不能冒充计费或实际窗口用量。发送前使用与目标模型匹配的计数工具或 API，发送后以响应 `usage` 校准；消息包装、工具 schema、图片、音频或推理 token 的计入方式要查当前供应商文档。

**上下文窗口** 是一次模型生成可引用的工作区上限，通常共同容纳指令、消息、工具描述、检索材料、工具结果、输出以及某些模型的推理 token。它不是模型训练语料，也不是长期记忆。具体上限和计入方式随 API、模型及调用模式变化。

**上下文预算** 是团队主动制定的分配，而不是模型上限。例如将可用容量分给：稳定指令、当前任务、必需状态、检索证据、工具结果、预期输出和安全余量。预算能防止一个来源吞掉全部空间。

## 为什么要留余量

若输入贴近上限，输出可能被截断，新工具结果无处插入，序列化差异也可能让估算失准。预算应保留输出和不可预见开销，并在发请求前做硬检查。上限、价格和缓存规则属于动态事实，不能硬编码在课程里；配置应可更新并从供应商当前文档核对。

可用一个概念式检查，而不是跨供应商硬套数字：

```text
窗口上限 >= 渲染后的全部输入 + 预留输出 + 供应商规定的其他计入项
context pack 预算 = 输入预算 - 稳定指令 - 工具定义 - 当前任务 - 安全余量
```

若计数接口与本地估算相差很大，应先查消息封装、工具 schema、多模态内容和模型版本，不要直接把误差吞进更大的窗口。

## 最小预算表

```text
总可用输入预算       12,000（示例单位，不代表任何模型限制）
稳定指令与工具说明    2,000
任务与结构化状态      1,500
检索证据              7,000
预留误差              1,500
```

先放必需项，再按价值挑选可选项；若必需项本身超限，应拒绝、拆任务或压缩，不能静默丢掉安全规则。

## 成本与性能

更多输入通常意味着更多传输、处理和费用，长上下文也可能增加延迟。缓存命中可能降低部分重复前缀的成本或延迟，但不改变语义正确性，也不保证输出一致。记录输入/输出/缓存相关用量的实际响应字段，避免用估算做结算。

## 练习与自测

为“阅读三份政策并回答问题”列出所有上下文组成，分出必需/可选并给出预算。自测：当第三份文档放不下时，系统会报错、检索片段、摘要还是直接截断？哪一种能让用户知道证据不完整？

## 掌握检查

- [ ] 我能区分 token、上下文窗口、输入预算、输出上限和实际 usage。
- [ ] 我的预算包含指令、工具定义、工具结果和输出余量，而不只计算文档正文。
- [ ] 我不会把字符数或样例中的 `estimated_tokens` 当成真实 tokenizer 结果。
- [ ] 必选内容超限时，系统会明确失败、拆分或受控压缩，不会静默删除安全规则。

## 下一步

进入 [[上下文工程/03-选择、相关性与来源|选择、相关性与来源]]，决定有限预算该给谁。

## 参考资料

- [OpenAI：Conversation state—Managing context for text generation](https://developers.openai.com/api/docs/guides/conversation-state#managing-context-for-text-generation)（访问于 2026-07-21）
- [Anthropic：Context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows)（访问于 2026-07-21）
- [Google：Long context](https://ai.google.dev/gemini-api/docs/long-context)（访问于 2026-07-21）
