---
title: "WER、CER 与切片评测"
tags:
  - ai-agent-engineer
  - asr
  - evaluation
aliases:
  - ASR 评测
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: zh-CN
translation_key: 语音识别/02-工程与质量/06-WER-CER与切片评测.md
translation_route: en/speech-recognition/engineering-and-quality/06-wer-cer-and-slice-evaluation
translation_default_route: zh-CN/语音识别/02-工程与质量/06-WER-CER与切片评测
---

# WER、CER 与切片评测

## 本节目标

正确计算并解释 WER/CER，固定规范化规则，并通过切片发现总分掩盖的问题。

## 编辑距离

参考词序列长度为 $N$，将其变成预测序列所需的替换、删除、插入数分别为 $S,D,I$：

$$
\mathrm{WER}=\frac{S+D+I}{N}
$$

按字符计算就是 CER。参考“we test agents”，预测“we tested agent”会涉及词级替换；实际最小操作由动态规划求得。插入很多时 WER 可超过 100%。

当参考单位数 $N=0$ 时，WER/CER **未定义**，不是 0；“本该静音却输出文字”应另报无参考片段数、误触发率或每小时错误，而不能把它塞进分母为零的 WER。报告还应保留错误数和参考单位数，避免只展示四舍五入后的百分比。

## 规范化决定可比性

计算前要冻结：大小写、标点、数字写法、缩写、填充词、Unicode 规范化和 tokenizer。中文按空白算 WER 往往无意义，应明确分词器或使用 CER。不要为让数字好看而针对预测结果制定规则；同一函数必须同时处理参考与预测。

**微平均**汇总所有错误与参考 token，长片段权重大；**宏平均**先算每个会话/说话人再平均，更能暴露短样本。宏平均遇到空参考或极短片段时尤其不稳定，必须说明排除/单列规则。报告应注明聚合方法、版本化的 tokenizer 和样本过滤原因。

## 切片与不确定性

至少按语言、噪声、设备、语速、时长、说话风格和业务场景切片。若合规且有授权，也可按与公平风险相关的人群属性检查差异。小样本切片波动很大，应同时报告样本量，并用 bootstrap 等方法估计区间。

除文本外，还可测：无语音误触发、片段边界偏差、词级时间戳、说话人错误、实时率、首字/最终结果延迟和人工修改率。它们不能互相替代：低 WER 不等于边界准、说话人标签准、无歧视或可实时使用；置信度也不是 WER 的替身。diarization 评测需要对匿名标签做最佳映射，并单列重叠语音/未知说话人策略。

每次候选升级都固定 `data_revision`、`model_revision`、`frontend_revision`、`decode_config_revision`、`normalization_revision` 和评测脚本版本；否则分数变化无法归因。线上没有参考文本时，把抽样人工标注、投诉/修改率和可观测代理分开报告，不能伪称“线上 WER”。

## 练习与自测

1. 参考 `a b c`，预测 `a x c d`：一次替换、一次插入，WER 为 $2/3$。
2. A 组 WER 低于 B 组能否直接归因于口音？不能，设备、噪声、样本难度等混杂因素需控制。
3. 模型升级时为何保留旧 normalization 代码？否则无法做同口径回归。

## 下一步与参考

下一步学习 [[语音识别/02-工程与质量/07-公平隐私部署与排查|公平、隐私、部署与排查]]。参考 [NIST OpenASR 2020 Evaluation Plan](https://www.nist.gov/system/files/documents/2021/08/03/OpenASR20_EvalPlan_v1_5.pdf) 与 [NIST SCTK](https://github.com/usnistgov/SCTK)（获取日期：2026-07-22）。工具的具体参数需按当前 README 核对；[[语音识别/03-项目与自测/08-项目-离线转录评估|本课程离线项目]]实现的是教学用最小编辑距离，并会把空参考的 rate 标为未定义。
