---
title: "Flow State 与事件"
aliases:
  - CrewAI Flows State Events
  - CrewAI Flow 入门
tags:
  - crewai
  - flow
  - state
  - events
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
lang: zh-CN
translation_key: CrewAI/02-Flow State与事件.md
translation_route: en/crewai/02-flow-state-and-events
translation_default_route: zh-CN/CrewAI/02-Flow-State与事件
---

# Flow、State 与事件

## 本节目标

你将能用 `@start`、`@listen` 和 `@router` 理解 Flow 的事件图，选择结构化状态，设计有限循环和终态，并区分当前官方文档中的 `@persist` 与 checkpointing 能力。

## Flow 解决什么问题

Crew 适合让一个或多个 Agent 完成边界清楚的认知任务；Flow 适合把 Python 代码、外部服务、人工反馈、路由和一个或多个 Crew 连接为业务生命周期。常见分层：

```text
Flow：接收输入 -> 校验 -> 调用 Crew -> 评审路由 -> 审批 -> 写入
                              └─ revise（有上限）─┘

Crew：研究 Task -> 写作 Task -> 审核 Task
```

支付、文件写入、审批、重试预算和最终发布不应仅由角色提示控制。Flow 也不是自动安全边界；工具实现和服务权限仍需普通代码保护。

## 三个装饰器的直觉

当前官方 Flows 页面展示：

- `@start()` 标记入口；多个满足条件的 start 都会执行，官方说明它们通常可并行。
- `@listen(method_or_label)` 监听方法输出或路由标签。
- `@router(method)` 返回有限标签，后续 listener 根据标签执行。

最小代码形状如下。路由标签使用独立命名空间，避免与 handler 方法同名后形成自监听；该形状已在 `crewai==1.15.4` 验证：

```python
from crewai.flow.flow import Flow, FlowState, listen, router, start  # 导入 Flow 基类、状态基类和事件路由装饰器。

ROUTE_PUBLISH = "route_publish"  # 将“可发布”路由标签集中定义为有限常量。
ROUTE_REVISE = "route_revise"  # 将“需要修订”路由标签集中定义为有限常量。

class ReviewState(FlowState):  # 声明可恢复、可校验的审核流程状态。
    attempts: int = 0  # 记录已尝试次数，供预算与停止条件使用。
    passed: bool = False  # 保存可信校验后的审核结果，而非模型的自由文本。

class ReviewFlow(Flow[ReviewState]):  # 将该 Flow 绑定到上面的结构化状态类型。
    @start()  # 标记 Flow 启动时执行的入口步骤。
    def draft(self):  # 生成待审核草稿的示意步骤。
        self.state.attempts += 1  # 每次进入草稿步骤都显式累加重试计数。
        return {"draft": "..."}  # 向后续路由步骤返回最小的草稿载荷。

    @router(draft)  # 使用 draft 的返回值触发审核路由步骤。
    def review(self, result):  # 接收上一节点结果并选择下一条有限分支。
        self.state.passed = validate(result)  # 用应用提供的可信校验器写入布尔结果。
        return ROUTE_PUBLISH if self.state.passed else ROUTE_REVISE  # 只返回预先定义的路由标签。

    @listen(ROUTE_PUBLISH)  # 仅在审核通过标签出现时监听并执行。
    def handle_publish(self):  # 进入可发布前的确定性处理步骤。
        return "ready"  # 返回业务终态提示；真实发布仍需独立授权与执行层。
```

`validate` 需由应用提供。路由标签应来自有限集合；未知标签失败关闭，不能把模型自由文本直接当方法名。

## 结构化状态优先

官方文档同时支持字典状态与基于 Pydantic `BaseModel` 的结构化状态，并自动为 Flow state 维护唯一 ID。生产流程通常更适合结构化状态，因为字段、类型和迁移更明确。

状态只保存后续步骤需要的事实：

```json
{
  "schema_version": 1,
  "topic": "Agent 可靠性",
  "stage": "review",
  "attempt": 1,
  "max_attempts": 2,
  "artifact_ref": "sha256:...",
  "approval": null
}
```

字段阅读：

- `schema_version` 用于决定能否安全读取或迁移此状态。
- `topic` 是本次运行冻结的业务输入；恢复时不能由模型随意改写。
- `stage` 是受控路由阶段，应该来自有限枚举。
- `attempt` 与 `max_attempts` 一起构成可验证的重试预算。
- `artifact_ref` 指向外部产物的稳定摘要或标识，而不是把大段文本塞进状态。
- `approval` 在未取得可信审批前为 `null`，不能由模型文本替代。

长篇模型文本是产物，不应兼任路由字段。`passed`、错误类别和审批状态都要经过可信代码验证。schema 升级时显式迁移或拒绝，不静默猜测旧字段。

## 事件是有契约的业务消息

无论是否使用官方 event bus，建议每个事件带：运行 ID、连续序号、类型、来源、相关版本和最小载荷。事件处理器应考虑重复调用；有副作用的 handler 使用稳定动作 ID 和回执。

```json
{
  "sequence": 4,
  "type": "review_completed",
  "payload": {"attempt": 1, "passed": false}
}
```

字段阅读：

- `sequence` 让消费者可以检测事件遗漏、乱序或重复。
- `type` 是固定业务事件名，处理器不应把自由文本当作事件类型。
- `payload` 只承载本事件所需的最小事实；此处记录审核次数与结果。

不要在事件中记录 API key、完整用户隐私或不必要的模型上下文。

## 循环与停止条件

“审核失败就重写”必须补齐：最大次数、同类错误停止、时间/成本预算、不可重试错误和人工接管。推荐路由：

```text
passed -> ready_to_publish
failed && attempts < 2 -> revise
failed && attempts == 2 -> human_review
permission_denied -> failed
```

离线项目正是这张图的确定性实现。即使真实 CrewAI 的 Agent 可自行规划，外层 Flow 仍应保留业务预算和终态。

## 框架暂停不等于业务授权

官方当前 Flow 文档提供 `@human_feedback`：它可暂停 Flow 收集人工反馈，并把 `emit` 中限定的结果路由给相应 listener。下面是**当前文档的 API 形状**，不是本库的已运行示例；Layer B 仍故意不调用模型、Slack 或任何审批服务：

```python
from crewai.flow.flow import Flow, listen, start  # 导入 Flow 入口与事件监听装饰器。
from crewai.flow.human_feedback import HumanFeedbackResult, human_feedback  # 导入人工反馈暂停与结果类型。

class ReviewFlow(Flow):  # 定义一个需要人工反馈才能继续的审核 Flow。
    @start()  # 将草稿步骤声明为 Flow 的初始入口。
    @human_feedback(  # 在执行 draft 前暂停，收集人工意见并转换为受限 outcome。
        message="请审核此草稿。",  # 提示人工审核者需要做出的判断。
        emit=["approved", "rejected", "needs_revision"],  # 将可路由结果限制在三个预定义标签。
        default_outcome="needs_revision",  # 无法归类时保守地进入修订，而不是默认批准。
    )
    def draft(self):  # 返回供人工查看的草稿内容。
        return "待审核内容"  # 示例载荷；真实场景还应绑定版本与动作摘要。

    @listen("approved")  # 仅监听已归类为 approved 的反馈结果。
    def continue_after_review(self, result: HumanFeedbackResult):  # 接收框架包装后的人工反馈。
        return result.feedback  # 返回原始意见供后续非高风险步骤参考。
```

这里有一个容易忽略的边界：当设置 `emit` 时，官方文档说明自由文本反馈会由 LLM 归类为一个 outcome。它适合**工作流路由和人工意见收集**，却不能单独构成付款、发送或发布的授权事实。高影响动作仍要在 Tool/服务边界核对可信身份、资源、规范化载荷摘要、有效期和一次性回执；把 `approved` 标签直接当授权令牌会把一次模型分类错误升级为权限绕过。锁定的 `1.15.4` wheel 也暴露该 decorator，但其默认 LLM 是易变实现细节，因此真实项目应显式配置并测试，而不是依赖默认模型。

若需要“修改后再次审核”，不要让 `@start()` 自己循环：官方文档说明 start 只在 Flow 开始时触发一次。把初始触发和 `needs_revision` 放进一个 listener 的有限 `or_(...)` 路由，并继续保留本节前面的 attempts、时间/成本预算和人工终态。

## 持久化与 checkpointing 的当前边界

Flows 页面说明 persistence decorator 可用于类或方法，默认后端是 SQLite。锁定的 `1.15.4` API 要写成 `@persist()` 或 `@persist(SQLiteFlowPersistence(path))`；裸 `@persist` 会把目标替换成尚未调用的 decorator function，不能据动态网页示例猜测。

同一系统还要区分两种水合：`kickoff(inputs={"id": uuid})` 在同一 UUID 下加载最新 state，`kickoff(restore_from_state_id=uuid)` 从该快照 fork 到新 UUID。两者都会重新进入满足条件的 Flow 图，不自动跳过已完成节点；未知 UUID 还可能静默按新流程开始，因此应用包装层应先检查 state 是否存在。另一个官方 Checkpointing 页面介绍 `CheckpointConfig` 与节点跳过，它不是 `@persist` 的同义词。

这两组文档能力可能随版本演进，页面标签又不一致。工程步骤应是：

1. 锁定 `crewai` 版本，并以 wheel/API reference 为实际执行依据；
2. 在最小程序中验证导入、保存位置和恢复入口；
3. 模拟步骤完成后崩溃；
4. 验证哪些节点会重放、哪些结果被跳过；
5. 对写动作另设幂等回执。

官方 Checkpointing 页面还说明手动 checkpoint 写入是 best-effort：写失败会记录错误但继续执行。这意味着“启用 checkpoint”不等于业务已获得强持久性保证。

## 并行与汇聚

官方当前文档更精确地写的是：所有满足条件的 `@start()` 都会执行，**通常可能并行**。这描述的是 runtime 调度可能性，不是业务并发安全保证。Layer B 只有一个 `@start()` 和一个会写 receipt 的 listener，所以其测试只证明该 fixture 的单进程、串行恢复；不能外推为多个 start、多个 worker 或任何共享 state 写入会按固定顺序完成。

多个 start 或异步步骤可能并行，但只有无数据依赖、无共享写入的任务才能安全并发。汇聚层要检查预期分支、超时、部分失败和冲突。若两个 Agent 同时覆盖同一 state 字段，完成顺序可能改变结果。

把 worker 结果作为独立事件返回，由一个 join 节点统一合并；写工具留在 join/审批之后。

## 常见错误与排查

- **把聊天历史当 Flow state**：提取有限字段、版本和产物引用。
- **router 返回任意文本**：校验为固定标签并设置 unknown 分支。
- **循环没有预算**：增加 attempts、超时、成本和人工终态。
- **认为持久化等于幂等**：检查点记录内部位置，回执证明外部动作。
- **多个 listener 写同一字段**：返回不可变结果，由单一汇聚器合并。
- **页面示例直接复制**：先用锁定版本做最小导入和恢复测试，尤其验证 decorator 是否需要括号、路由标签是否自监听。

## 练习

为“收集需求→生成报价草案→人工批准→发送”画 Flow，提交：

1. start、listen、router 节点与路由标签；
2. Pydantic state 字段和 schema 版本；
3. 拒绝、过期、发送失败和人工接管终态；
4. 发送动作的幂等 ID 与回执；
5. 恢复测试：批准前崩溃、发送后保存前崩溃。

## 掌握检查

- [ ] 能区分 Flow state、事件和模型文本产物。
- [ ] 能说明 start、listen 与 router 的职责。
- [ ] 能为循环写预算和终态。
- [ ] 能解释持久化、checkpoint 和幂等回执的不同作用。
- [ ] 能设计锁定版本下的恢复实验，而非依赖文档推测。

## 下一步

进入 [[CrewAI/03-Tools边界与结构化输出|Tools 边界与结构化输出]]，定义 Agent 能做什么和如何验收产物；完成主线后用 [[CrewAI/08-项目-真实CrewAI持久化Flow|真实 CrewAI 持久化 Flow]] 实测本节语义。

## 参考资料

- [CrewAI Flows](https://docs.crewai.com/en/concepts/flows)（动态文档与 `1.15.4` wheel 交叉核对：2026-07-21）
- [CrewAI Human Feedback in Flows](https://docs.crewai.com/en/learn/human-feedback-in-flows)（暂停、反馈与路由；核对：2026-07-21）
- [CrewAI Checkpointing](https://docs.crewai.com/en/concepts/checkpointing)（动态文档；核对：2026-07-14）
- [CrewAI Event Listeners](https://docs.crewai.com/en/concepts/event-listener)（动态文档；核对：2026-07-14）
