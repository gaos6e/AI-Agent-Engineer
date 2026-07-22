---
title: RAG、生成与 Agent 分层评测
aliases:
  - Layered RAG and agent evaluation
tags:
  - 评测
  - RAG
  - Agent
source_checked: 2026-07-14
content_origin: original
content_status: dynamic
---

# RAG、生成与 Agent 分层评测

## 本节目标

把端到端失败拆到检索、生成、决策、工具、轨迹和 outcome 层，缩短定位路径。

## 直觉解释

最终回答错误只是症状。分层评测像沿数据流逐站检查：先确认找到了正确证据，再确认使用了证据；Agent 还要检查选择、参数、轨迹和真实最终状态。

## RAG 两层起步

### 检索层

- query 是否正确表达用户意图；
- gold evidence 是否进入 top-k，可用 Recall@k；
- 返回内容中相关比例，可用 Precision@k；
- 权限、版本、新鲜度和去重是否正确；
- 结果顺序、元数据和上下文预算是否合理。

### 生成层

- 关键结论是否被检索证据支持；
- 引用能否定位到真实片段；
- 是否遗漏必要信息或加入证据外断言；
- 无充分证据时是否正确拒答/澄清；
- 格式、语言与用户任务是否满足。

仅看最终答案无法区分“没检到”与“检到了但没用”。RAGAS 原始论文提出无参考的自动化维度，但模型指标仍需与领域人工判断校准，不能当绝对真值。

还要分开“答案正确”与“引用忠实”：一个答案可能碰巧正确却引用错来源，也可能 claims/citations 结构合法但用户可见答案额外加入无证据事实。[[RAG/08-项目-离线可引用问答|RAG 离线项目]] 的 `evaluate` 子命令实际输出 retrieval/context/citation fact recall、status accuracy、关键切片与 non-disclosure 门；它同时让 answer 由已验证 claims 渲染，并把公共响应与受保护 audit trace 分成两个 schema。

## Agent 的更多层

| 层 | 典型检查 |
| --- | --- |
| 意图/规划 | 是否识别目标与约束、是否需要澄清 |
| 工具选择 | 工具名是否合适，是否调用禁用工具 |
| 参数 | ID、路径、范围、幂等键是否正确 |
| 轨迹 | 是否重复、循环、跳过关键验证；避免过度限定唯一步骤 |
| outcome | 外部状态是否达到目标且无副作用 |
| 运行 | turns、token、时延、重试和失败恢复 |

官方指南建议优先评价产物和状态，而非强迫 Agent 按唯一工具序列执行；同时 trace 对诊断、越权和无效循环仍很重要。

## Trace评分不是“路径越像越好”

**Trace评分（trace grading）**给一次端到端调用轨迹的决策、工具、参数或步骤分配结构化标签。适合检查：是否调用禁用工具、参数范围、是否使用证据、是否循环、策略步骤是否缺失。它不适合把一种正确工具顺序写成唯一答案，也不能仅凭Agent在文本中声称的意图证明最终状态。

Trace grader需要明确：

- 必须出现/禁止出现的行为，以及允许的多种合法路径；
- 采样、缺失span、并发和重试如何计分；
- 敏感Prompt、工具结果和推理材料的访问/保留边界；
- grader版本、人工校准与`Unknown`处理；
- Trace判断如何与outcome、结构化Log和环境状态交叉验证。

OpenAI当前Trace grading页面将trace定义为决策、工具调用和推理步骤的端到端记录，并强调其诊断价值；但页面仍引导到已宣布弃用的Evals dashboard。本课程保留方法，不教授该旧dashboard流程。MLflow当前`latest`文档也把trace作为离线/自动评测载体；具体API必须按实际安装版本核对。

## 组件测试与端到端测试

- 组件测试固定检索结果，只评生成；或固定工具响应，只评参数与决策。
- 端到端测试使用真实相似环境，评完整系统与恢复能力。
- 契约测试验证 JSON/schema/权限边界。
- 安全测试尝试提示注入、越权和数据外泄。

组件测试定位快但可能漏掉交互问题；端到端真实但噪声更大。两者都需要。

## 一个诊断示例

回答引用了错误政策：先查 gold 文档是否在 top-k；若不在，查 query、索引和过滤；若在，查上下文截断和生成 grounding；若文本正确但用户仍不满意，再看任务定义与呈现。每步保留 case ID、配置、文档版本和 trace。

## 失败分类与证据链

对每个失败先标注发生层，再写证据，而不是立即写根因：

1. **数据/任务**：gold错误、文档过期、任务无解或定义含糊；
2. **检索**：gold未召回、权限过滤错、排序/截断问题；
3. **生成**：证据已在上下文却未使用、无据扩写或格式失败；
4. **工具/轨迹**：选择错、参数错、重复/循环、跳过关键安全检查；
5. **outcome**：文本正确但外部状态未完成，或产生隐藏副作用；
6. **grader/harness**：评分bug、环境残留、预算不等或Trace缺失。

根因结论至少链接到case、grader结果、Trace/outcome证据和配置差异。仅凭相关时间或某个失败span，只能形成待验证假设。

## 常见错误与排查

- 只看最终文本：补检索 ID、工具参数、trace 和环境状态。
- 强迫唯一工具序列：只约束必要安全步骤，允许多个正确路径。
- 自动 RAG 指标当真值：用领域人工样本校准并保留失败案例。

## 练习

1. 为“从知识库查退款政策并创建工单”写每层一个 assertion。
2. 设计一个固定 tool response 的单元测试和一个真实沙箱的端到端测试。

## 自测

最终回答正确时是否可以忽略 trace？不能；可能发生越权读取、无效循环或隐藏副作用。

## 小结与下一步

进入 [[评测体系/02-方法与质量/06-离线在线统计与回归|离线、在线、统计与回归]]。

## 参考资料

- [OpenAI Evaluation best practices: architecture layers](https://developers.openai.com/api/docs/guides/evaluation-best-practices)（核对于2026-07-14）
- [OpenAI Trace grading](https://developers.openai.com/api/docs/guides/trace-grading)（核对于2026-07-14；方法参考，不作为新Evals API教程）
- [MLflow LLM Judges and Scorers](https://mlflow.org/docs/latest/genai/eval-monitor/scorers/index.html)（`latest`文档核对于2026-07-14）
- [Anthropic: Agent eval structure and graders](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)（发布于2026-01-09；核对于2026-07-14）
- [RAGAS: Automated Evaluation of Retrieval Augmented Generation](https://aclanthology.org/2024.eacl-demo.16/)（原始论文，核对于2026-07-14）
