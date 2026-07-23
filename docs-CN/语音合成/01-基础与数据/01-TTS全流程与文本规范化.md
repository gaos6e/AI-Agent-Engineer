---
title: "TTS 全流程与文本规范化"
tags:
  - ai-agent-engineer
  - tts
  - text-normalization
aliases:
  - TTS pipeline
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: zh-CN
translation_key: 语音合成/01-基础与数据/01-TTS全流程与文本规范化.md
translation_route: en/text-to-speech/foundations-and-data/01-tts-pipeline-and-text-normalization
translation_default_route: zh-CN/语音合成/01-基础与数据/01-TTS全流程与文本规范化
---

# TTS 全流程与文本规范化

## 本节目标

理解从原始文本到音频的职责链，并为数字、缩写、符号和语言切换建立可审计的规范化层。

## 完整流程

```text
原始文本 -> 语言/句子分析 -> 文本规范化 -> 发音/音素
-> 韵律与声学表示 -> 声码器/波形生成 -> 编码/流式 -> 质检与记录
```

**文本规范化（text normalization）** 把书写形式转换成朗读形式。例如 `￥128.50` 可能读作“人民币一百二十八元五角”，`2026/07/13` 的读法取决于语言和语境。它不是简单替换：`120` 在门牌、数量、热线号码中的读法不同。先声明语言/地区、脚本、产品语境和规则版本；不要仅由姓名、文字外观或声音标签自动推断用户语言或身份。

## 三层文本

- `source_text`：用户或系统原文，不覆盖，关联 `source_revision`。
- `spoken_form`：经版本化规则转换的朗读文本，关联 `normalization_revision`。
- `display_text`：字幕或界面文本，可能仍保留原格式；它不能从 `spoken_form` 反推完整原文。

记录每条转换规则和输入位置，使人工能解释“为什么这样读”。对姓名、药品、账号等高风险字段，不确定时应请求确认或使用拼读策略，而非猜测。来自用户、RAG、工具或模型的文本都是不可信内容；先在 runtime 完成策略、权限和结果确认，再交给 TTS，不能让一段朗读文本自行触发动作。

## 分句与长度

过长输入会增加延迟、内存和错误恢复成本。按标点、段落和最大长度切分，同时保留语义完整性。每段有稳定 `utterance_id`、`source_revision` 和原文范围；重试按段幂等，播放端按顺序拼接。缩写、数字中的句点不能被误当句末。

合成后还要声明输出合同：container、codec、采样率、声道、时长、声音/模型/配置版本和可播放状态。它们决定播放器兼容性、缓存键和评测口径；不要把“可下载的 MP3”当成所有客户端、语言或低延迟路径都能无条件播放。

## 常见错误

- 直接把 Markdown 符号、URL 或代码块交给 TTS。
- 在日志中记录完整敏感文本。
- 规范化后删除原文，无法追责。
- 为所有语言共享一套数字和日期规则。
- 把未确认的工具结果或模型 partial token 直接外放；已播放内容不能撤回。

## 练习与自测

为“会议在 2026-07-14 09:30 开始，预算 ¥1,280.50”写 `source_text`、中文 `spoken_form` 与转换记录。然后回答：日期是否可仅凭字符串确定读法？不能，还需语言和产品语境。

## 下一步与参考

下一步学习 [[语音合成/01-基础与数据/02-音素韵律与声码器直觉|音素、韵律与声码器直觉]]。SSML 中的 `say-as`、`sub` 和语言标记可表达部分读法，参考 [W3C SSML 1.1](https://www.w3.org/TR/speech-synthesis11/)（W3C Recommendation，获取日期：2026-07-22）；具体解释能力取决于引擎实现。
