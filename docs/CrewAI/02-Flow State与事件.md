---
title: Flow State 与事件
aliases:
  - CrewAI Flows State Events
  - CrewAI Flow 入门
tags:
  - crewai
  - flow
  - state
  - events
source_checked: 2026-07-14
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

最小代码形状如下；它来自官方当前示例，未在本库真实 CrewAI 环境执行：

```python
from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

class ReviewState(BaseModel):
    attempts: int = 0
    passed: bool = False

class ReviewFlow(Flow[ReviewState]):
    @start()
    def draft(self):
        self.state.attempts += 1
        return {"draft": "..."}

    @router(draft)
    def review(self, result):
        self.state.passed = validate(result)
        return "publish" if self.state.passed else "revise"

    @listen("publish")
    def publish(self):
        return "ready"
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

## 持久化与 checkpointing 的当前边界

Flows 页面说明 `@persist` 可用于类或方法，默认示例使用 SQLiteFlowPersistence 保存 state；还区分按 ID 恢复与从既有状态 fork。另一个官方 Checkpointing 页面展示 `CheckpointConfig`，可作用于 Crew、Flow 和 Agent，并提供 JSON/SQLite provider 及 `from_checkpoint(...)`。

这两组文档能力可能随版本演进，页面标签又不一致。工程步骤应是：

1. 锁定 `crewai` 版本；
2. 在最小程序中验证导入、保存位置和恢复入口；
3. 模拟步骤完成后崩溃；
4. 验证哪些节点会重放、哪些结果被跳过；
5. 对写动作另设幂等回执。

官方 Checkpointing 页面还说明手动 checkpoint 写入是 best-effort：写失败会记录错误但继续执行。这意味着“启用 checkpoint”不等于业务已获得强持久性保证。

## 并行与汇聚

多个 start 或异步步骤可能并行，但只有无数据依赖、无共享写入的任务才能安全并发。汇聚层要检查预期分支、超时、部分失败和冲突。若两个 Agent 同时覆盖同一 state 字段，完成顺序可能改变结果。

把 worker 结果作为独立事件返回，由一个 join 节点统一合并；写工具留在 join/审批之后。

## 常见错误与排查

- **把聊天历史当 Flow state**：提取有限字段、版本和产物引用。
- **router 返回任意文本**：校验为固定标签并设置 unknown 分支。
- **循环没有预算**：增加 attempts、超时、成本和人工终态。
- **认为持久化等于幂等**：检查点记录内部位置，回执证明外部动作。
- **多个 listener 写同一字段**：返回不可变结果，由单一汇聚器合并。
- **页面示例直接复制**：先用锁定版本做最小导入和恢复测试。

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

进入 [[CrewAI/03-Tools边界与结构化输出|Tools 边界与结构化输出]]，定义 Agent 能做什么和如何验收产物。

## 参考资料

- [CrewAI Flows](https://docs.crewai.com/en/concepts/flows)（页面标签 `v1.14.5`；核对：2026-07-14）
- [CrewAI Checkpointing](https://docs.crewai.com/en/concepts/checkpointing)（动态文档；核对：2026-07-14）
- [CrewAI Event Listeners](https://docs.crewai.com/en/concepts/event-listener)（动态文档；核对：2026-07-14）
