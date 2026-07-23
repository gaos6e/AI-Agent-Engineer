---
title: "SSML 与发音控制"
tags:
  - ai-agent-engineer
  - tts
  - ssml
aliases:
  - Speech Synthesis Markup Language
source_checked: 2026-07-22
lang: zh-CN
translation_key: 语音合成/02-工程与质量/04-SSML与发音控制.md
translation_route: en/text-to-speech/engineering-and-quality/04-ssml-and-pronunciation-control
translation_default_route: zh-CN/语音合成/02-工程与质量/04-SSML与发音控制
---

# SSML 与发音控制

## 本节目标

理解 SSML 1.1 的 XML 结构，安全表达语言、句子、停顿、强调、韵律和发音，同时处理引擎差异。

## 最小 SSML

SSML（Speech Synthesis Markup Language）是 W3C 推荐标准。独立 SSML 文档遵循合法的 XML prolog，随后以带标准命名空间的 `speak` 为根；下面使用 XML 声明作为可读的完整文档示例。供应商 API 也可能只接受 SSML 片段或自行包裹根元素，因此请求形态要按目标接口另行核验：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<speak version="1.1"
       xmlns="http://www.w3.org/2001/10/synthesis"
       xml:lang="zh-CN">
  <p><s>欢迎使用语音助手。</s></p>
</speak>
```

常用概念：`break` 控制停顿，`emphasis` 表达强调，`prosody` 控制速率/音高/音量，`say-as` 提示数字或日期读法，`phoneme` 指定发音，`sub` 提供替代读法，`voice` 请求声音特征或名称。

## 安全构造

不要把用户文本直接拼接进 XML；用 XML 库创建元素，让 `<`、`&` 等字符自动转义。限制允许标签、属性、输入长度和外部资源；禁用或拒绝不需要的 `audio` 外部引用。SSML 不等于 HTML，浏览器转义规则不能直接套用。

本知识库项目从纯文本和受控枚举生成 SSML，不接受任意 XML。这样减少注入和供应商扩展泄漏。

## 可移植性

标准定义语义，但供应商可能：

- 只支持标签或属性子集；
- 为情绪、风格加入私有命名空间；
- 对相同 `prosody` 值产生不同听感；
- 对无效标签报错、忽略或降级。

建立“核心可移植 SSML + 供应商适配层”，并用每个目标声音回归。发音词典可参考 W3C PLS，但引擎支持仍需核验。

## 练习与自测

- 用 XML 库构造含 `A&B <测试>` 的文本，确认被转义而非当标签。
- 为电话号码设计 `say-as`，并说明若引擎不支持如何降级成明确 spoken form。
- 为什么不应把任意 URL 放入 `<audio>`？会引入网络、追踪、格式和内容安全风险。

## 下一步与参考

下一步学习 [[语音合成/02-工程与质量/05-声音选择批处理与流式|声音选择、批处理与流式]]。参考 [W3C SSML 1.1](https://www.w3.org/TR/speech-synthesis11/) 与 [W3C Pronunciation Lexicon Specification 1.0](https://www.w3.org/TR/pronunciation-lexicon/)（均为 W3C Recommendation，获取日期：2026-07-22）。
