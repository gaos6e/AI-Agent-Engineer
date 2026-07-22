---
title: 仪器化、Collector 与关联
tags:
  - observability
  - opentelemetry
  - tracing
aliases:
  - 遥测仪器化
  - 上下文传播与 Collector
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
source_baseline: "OpenTelemetry、W3C Trace
  Context官方资料截至2026-07-22；GenAI语义约定独立仓库、schema版本与组件稳定性边界已复核"
---

# 仪器化、Collector 与关联

## 本节目标

学会把“应用正在运行”变成可关联、可治理的遥测数据：理解自动与手工仪器化的边界，正确传播 Trace 上下文，设计 Collector 流水线，并在采样、基数、成本与隐私之间做明确取舍。

## 仪器化究竟在做什么

**仪器化（instrumentation）**是在程序边界或业务步骤中生成 Log、Metric、Span 等遥测数据。它不是“安装一个 Agent 就完成”，而是三层契约：

1. **生成**：应用、SDK 或自动探针记录数据；
2. **关联**：请求跨 HTTP、消息队列、后台任务和工具调用时仍能共享上下文；
3. **处理与导出**：Collector 接收、变换、过滤、批处理，再发送到后端。

自动仪器化通常擅长 HTTP、数据库和常见框架边界；手工仪器化用于补充自动工具不知道的业务语义，例如 `task_type`、检索阶段、人工接管结果或受控的工具名。不要用手工 Span 逐行复刻代码，也不要把 Prompt、身份证号或密钥当作“方便排查”的属性。

## 先建立稳定的资源与字段契约

一条遥测记录至少要能回答“哪个系统、哪个环境、哪个发布产生了它”。可先约定有限且稳定的资源字段：

| 字段 | 例子 | 用途 |
| --- | --- | --- |
| `service.name` | `agent-gateway` | 区分服务 |
| `deployment.environment.name` | `production` | 区分环境 |
| `service.version`或内部`release_id` | `2026.07.14.1` | 关联发布 |
| `trace_id`、`span_id` | 不透明ID | 单次调用链关联 |
| 受控业务属性 | `task_type=ticket_triage` | 诊断有限类别 |

字段名、单位、枚举和缺失语义应写入团队的**遥测契约**并做测试。OpenTelemetry（OTel）语义约定的稳定性按组件和信号分别声明，不能只凭“属于 OTel”就假定全部稳定。截至2026-07-21，OTel核心语义约定页为1.43.0，生成式AI约定已迁移到独立仓库。接入时应固定实际采用的仓库修订/发布、记录schema URL或等价契约版本，并按所用信号和组件的稳定性用契约测试发现字段变化。不要把核心页版本当作当前GenAI字段版本，也不要凭记忆编造字段。

## 用 W3C Trace Context 传播关联

W3C Trace Context 定义了 `traceparent` 与 `tracestate` HTTP 头。常见版本 `00` 的 `traceparent` 形状是：

```text
00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

依次表示版本、32 个十六进制字符的 Trace ID、16 个十六进制字符的父 Span ID 和标志。全零ID无效；格式解析、生成新 Span ID 和采样标志处理应交给合规库，而不是手写字符串拼接。

传播时遵守四条原则：

1. HTTP 下游注入上下文、上游提取上下文；消息系统把上下文放在受支持的消息属性中；
2. 异步任务若脱离原请求生命周期，要明确是继续同一 Trace、建立 link，还是开始新 Trace并用受控业务ID关联；
3. 结构化Log可写入当前`trace_id`和`span_id`，Metric仅使用有限label，必要时通过exemplar或下钻链接关联Trace；
4. `traceparent`是传播标识，不是身份认证或授权凭据。接收不可信边界的上下文时仍需执行访问控制，并防止不受控的`tracestate`造成隐私和资源风险。

## Collector 流水线

OTel Collector 的基本流水线是：

```text
应用/探针 → Receiver → Processor(s) → Exporter → 遥测后端
```

- **Receiver**接收 OTLP 或其他协议数据；
- **Processor**执行批处理、内存限制、属性过滤、采样等处理；顺序会改变结果；
- **Exporter**将数据发送到目标后端；
- **Connector**可把一条流水线的输出连接到另一条流水线；
- **Extension**提供健康检查、鉴权等不直接处理遥测的数据面外能力。

Collector 可以靠近应用以 Agent 方式部署，也可在共享网关集中处理；真实拓扑需结合网络边界、故障域、资源成本和敏感数据位置决定。最小方案也要监控 Collector 自身：accepted、refused、sent、failed、队列长度、丢弃、配置版本和数据新鲜度。还要把**Collector 导出时龄**与**最新业务事件相对观察终点的时龄**分开：前者新鲜不代表上游业务流仍在产生事件。否则“Dashboard 一片正常”可能只是 Collector 正在成功导出一段已经停滞的数据。

## 采样、基数与成本

Trace 全量保存通常成本很高，常用两类采样：

- **Head sampling**：在 Trace 开始时决定，开销可控，但当时还不知道最终是否失败；
- **Tail sampling**：观察到更多 Span 后再决定，更容易保留错误或高延迟Trace，但需要缓冲、状态和容量规划。

任何采样都会改变“能看到哪些个案”。应记录策略版本和估算覆盖率，优先保留错误、高风险操作和极慢调用，并用不依赖 Trace 采样的Metric计算总体率。Trace 采样也不能解决Metric高基数：`user_id`、`request_id`、任意URL、完整Prompt、发布清单SHA-256和candidate gate完整SHA-256等仍不应成为Metric label；后两类可留在受控Trace或审计Log中用于证据交接。

成本治理可以从预算表开始：每个信号的事件量、每条大小、保留期、索引字段、采样率、查询需要和所有者。只有能支持用户目标、发布决策或事件响应的字段才值得长期保留。

## 隐私、安全与保留期

生成式 AI 内容经常含个人数据、商业信息或越权指令。安全的默认值是：

- 内容采集默认关闭或明确选择加入，只收诊断所需的最小字段；
- 在数据离开信任边界前做删除、掩码或受控哈希，且不能用不可逆哈希冒充匿名化保证；
- 对遥测存储实施最小权限、传输/静态加密、审计、保留期和可验证删除；
- 把采集失败、脱敏失败和删除失败作为可观测事件，而不是静默忽略；
- 使用合成教学ID和占位内容验证流水线，不把真实凭据写入样例。

## 分步设计一条 Agent 调用链

假设一次“检索后调用工具并生成回答”的请求：

1. 网关建立根Span，记录服务、发布、受控任务类型和技术结果；
2. 检索、重排、模型调用、工具调用和策略检查分别建立子Span；
3. 将上下文传给下游HTTP/消息处理器，Log写入当前Trace关联键；
4. Metric统计请求率、错误率、延迟分布、工具失败、质量覆盖率和费用，不放入单次请求ID；
5. Collector先限制内存并批处理，再做字段过滤/脱敏，最后导出；
6. Collector自身Metric、传播完整率和抽样覆盖率进入独立健康面板。

如果模型Span存在但工具Span经常变成新的根Trace，优先检查上下文是否跨线程、任务队列或SDK边界丢失，而不是先猜测工具性能有问题。

## 练习

1. 为“读取工单 → 检索知识 → 调用库存工具 → 生成人工可审查草稿”画出 Span 树，并标出哪些属性属于资源、Span和Log。
2. 设计一条 Collector 流水线，写出每个组件的输入、输出、失败表现和自监控信号。解释为什么脱敏处理器必须位于导出之前。
3. 从以下候选中选择可做Metric label的字段：`environment`、`request_id`、`release_id`、`user_email`、受控`task_type`、完整Prompt。逐一说明原因。
4. 分别设计 Head 与 Tail sampling 策略，说明哪些故障可能被漏掉，以及如何用Metric估计覆盖缺口。

## 自测与掌握检查

- [ ] 能解释自动仪器化为何不能替代业务语义；
- [ ] 能说明`traceparent`传播、认证和采样三者不是同一件事；
- [ ] 能画出Receiver—Processor—Exporter流水线并指出Collector自监控项；
- [ ] 能区分Trace采样问题与Metric高基数问题；
- [ ] 能为生成式AI内容定义采集开关、脱敏、权限和保留期；
- [ ] 能查证目标语义约定的稳定性，并用版本锁定与契约测试控制变化。

## 小结与下一步

仪器化把代码路径变成有语义的证据，传播让证据跨边界保持关联，Collector负责可治理地处理和导出。下一步用 [[运行监控/01-可观测性基础/03-SLI、SLO与错误预算|SLI、SLO 与错误预算]] 决定哪些用户行为应成为目标，而不是把所有可采集字段都变成告警。

## 参考资料

- [OpenTelemetry Collector Architecture](https://opentelemetry.io/docs/collector/architecture/)（访问于2026-07-21）
- [OpenTelemetry Collector components](https://opentelemetry.io/docs/collector/components/)（访问于2026-07-21）
- [OpenTelemetry Collector internal telemetry](https://opentelemetry.io/docs/collector/internal-telemetry/)（访问于2026-07-21）
- [OpenTelemetry Sampling](https://opentelemetry.io/docs/concepts/sampling/)（访问于2026-07-21）
- [OpenTelemetry Handling sensitive data](https://opentelemetry.io/docs/security/handling-sensitive-data/)（访问于2026-07-21）
- [OpenTelemetry Versioning and stability](https://opentelemetry.io/docs/specs/otel/versioning-and-stability/)（访问于2026-07-21；应按具体组件重新核对稳定性）
- [OpenTelemetry Generative AI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)（访问于2026-07-21；核心页面说明内容已迁移且旧位置不再维护）
- [OpenTelemetry GenAI semantic conventions repository](https://github.com/open-telemetry/semantic-conventions-genai)（访问于2026-07-21；固定实际修订/schema URL，并按所用信号与组件核对稳定性）
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)（W3C Recommendation，2021-11-23；访问于2026-07-21）
