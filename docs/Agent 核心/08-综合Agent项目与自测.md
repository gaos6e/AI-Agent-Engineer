---
title: 综合 Agent 项目与自测
tags:
  - agent-core
  - project
  - checkpoint
  - approval
aliases:
  - Agent 核心项目
  - 有边界离线 Agent
source_checked: 2026-07-21
execution_verified: 2026-07-22
content_origin: original
content_status: validated
---

# 综合 Agent 项目与自测

## 项目目标

运行一个确定性、离线、有边界的工单 Agent runtime。模型被 `DeterministicPolicy` 替代，使注意力放在可测试的工程控制：

- action/observation loop；
- tool allowlist 与目标约束；
- 不可信工具文本；
- 步数、工具调用和连续失败预算；
- 写动作审批；
- checkpoint 完整性；
- checkpoint 的 phase/pending action、event chain 与 completion evidence 不变量；
- commit-before-checkpoint crash window；
- idempotency receipt 恢复；
- 畸形 action、approval 与 tool result 的失败关闭及写入结果不确定时的 reconciliation 记录；
- 目标已由外部状态满足时的无写入完成；
- completion verifier。

> [!warning] 能力边界
> 这不是通用 Agent 框架，也没有声称模拟某家模型的推理质量。它只用 Python 标准库演示 runtime invariant。真实系统还需要持久数据库、分布式 lease、真实身份/授权、provider adapter、监控和部署级测试。

## 文件

| 文件 | 作用 |
| --- | --- |
| [bounded_agent.py](Agent%20%E6%A0%B8%E5%BF%83/examples/bounded_agent.py) | 状态、policy、runtime、tool host、approval、checkpoint 与 demo |
| [test_bounded_agent.py](Agent%20%E6%A0%B8%E5%BF%83/examples/test_bounded_agent.py) | 68 个正/负向回归测试 |

## 环境

项目无第三方依赖，可直接用稳定版 Python 3。以下代码块都从同时包含 `docs/` 与 `.website/` 的项目根目录运行。若希望隔离：

```powershell
Push-Location -LiteralPath 'docs\Agent 核心' # 临时进入示例所在目录，避免把虚拟环境建在项目根目录
python -m venv .venv # 创建只供本机使用的 Python 虚拟环境
.\.venv\Scripts\Activate.ps1 # 在当前 PowerShell 会话激活该虚拟环境
python -m pip --version # 确认此会话调用的是虚拟环境中的 pip
Pop-Location # 恢复进入该代码块前的工作目录
```

不需要 `pip install` 任何包；`.venv` 只在本机使用，不得加入知识库或 Git。

不创建环境也可直接运行：

```powershell
Push-Location -LiteralPath 'docs\Agent 核心' # 进入项目目录，使相对示例路径可解析
python -B .\examples\bounded_agent.py # 运行 demo；-B 不生成字节码缓存
python -B .\examples\test_bounded_agent.py # 普通模式运行全部回归测试
python -B -O .\examples\test_bounded_agent.py # 优化模式检查控制逻辑不依赖 bare assert
python -B -W error .\examples\test_bounded_agent.py # 把警告升级为错误，及早发现兼容性问题
python -B -O -W error .\examples\test_bounded_agent.py # 两项严格模式一起运行，覆盖组合风险
Pop-Location # 恢复原工作目录
```

`-B` 禁止生成 `__pycache__`；`-W error` 把警告当失败；`-O` 验证关键控制未误写成会被优化移除的 bare `assert`。

当前已验证环境：2026-07-21，Windows 11、PowerShell 7、Python 3.11。

## 预期 demo

```jsonc
{ // demo 成功结束时输出的摘要，而非完整审计日志
  "status": "ok", // 进程成功运行；不单独证明外部目标已完成
  "phase": "completed", // runtime 已通过 verifier 进入完成终态
  "steps": 3, // demo 中记录的逻辑决策步骤数
  "tool_calls": 2, // 恢复后 checkpoint 可见的工具调用计数
  "close_count": 1, // 关键幂等性证据：同一 ticket 只实际关闭一次
  "event_types": [ // 省略细节后的关键事件类型列表
    "observation_recorded", // 已记录来自查询工具的规范化观察
    "approval_requested", // 写动作在执行前请求了人工审批
    "completion_verified" // verifier 用外部回执确认了完成
  ] // 结束事件类型数组
}
```

> [!note] JSONC 教学表示
> 为保留逐行中文说明，本示例使用 JSONC；复制为严格 JSON 时请移除 `//` 注释。

关键不是输出格式，而是 `close_count` 始终为 1。

`tool_calls=2` 是**恢复后 checkpoint** 里的逻辑计数：初次 lookup 加恢复时的 receipt 查询。为了演示 crash window，崩溃分支发生的查询/写入没有写回这个旧 checkpoint；因此它不能证明跨崩溃的配额记账。生产系统要在外部 I/O 前持久记录 attempt，并依靠 provider 侧限额和审计，详见 [[Agent 核心/05-长任务检查点、恢复与幂等|检查点、恢复与幂等]]。

## 轨迹逐步解释

### 1. 读取当前 ticket

Policy 只允许 `lookup_ticket(ticket-7)`。Runtime 先验证 tool result 必须是精确字段、当前 ticket 和预期基础类型，再把它记录为 observation；畸形或错目标的**读取**结果进入 `failed / invalid_tool_result`，不能继续到写操作。写入路径若收到畸形 receipt/result，则不把它当成功或可安全重试，而以 `tool_result_uncertain` 失败并保留 reconciliation 所需的 action/target/idempotency 信息。合法读取结果包含：

- status=open；
- 一段恶意 customer note，要求关闭其他工单和导出环境变量。

Runtime 把它包成：

```jsonc
{ // 对 lookup 工具结果的受控封装
  "source": "tool:lookup_ticket", // 精确说明该 observation 来自哪个工具
  "trust": "untrusted", // 即使工具返回文本也不能把其中命令当成 runtime 指令
  "purpose": "ticket facts only; never runtime instructions", // 允许提取事实，但禁止改变控制面规则
  "data": {"ticket_id": "ticket-7", "...": "..."}, // 经 schema 和目标校验后的最小业务数据
  "sha256": "..." // 用摘要关联受控原文，避免把整段敏感内容写入状态
}
```

恶意 note 不进入 runtime policy。

### 1.1 目标已满足时直接停止

如果通过结构校验的查询结果已经是 `status=closed`，目标当前已由外部状态满足。Runtime 记录查询动作与 observation，以 `stop_reason=already_satisfied` 进入 `completed`，不再提出 `close_ticket`，因此也不需要写审批或写回执。这个分支证明的是“经查询确认的当前状态已经满足目标”，不是用模型的 `finish` 声明替代外部证据。

后续步骤描述默认 demo 的 `status=open` 写入路径。写入路径仍必须经过冻结动作、审批、幂等执行与回执验证。

### 2. 提出并冻结写动作

Policy 提出 `close_ticket(ticket-7)`。Runtime 验证：

- tool 在 allowlist；
- action ID、tool、arguments 和 risk 都匹配此阶段的固定 contract；
- idempotency key 精确绑定 run + ticket + contract version。

随后保存这个精确的 pending action，进入 `waiting_approval`。恢复时 runtime 使用冻结对象，不重新调用 policy 产生另一个动作；此时 `close_count=0`。

### 3. 创建 approval

`make_approval` 绑定：

- action ID；
- action fingerprint；
- state version；
- decision；
- step expiry。
- target scope（本例是 `ticket_id`）。

参数、目标或状态变化都会让批准失效。

### 4. 模拟 crash window

Runtime 调用 tool：

1. receipt 查询与写入各自消耗一次工具调用预算；
2. tool 持久化（示例中为内存）receipt 并关闭 ticket；
3. 在 runtime 写回 completed state 前抛出 `SimulatedCrash`。

此时外部动作已发生，但 checkpoint 仍是 waiting_approval。

### 5. 从旧 checkpoint 恢复

新 state 从 checkpoint 重建；用同一 idempotency key 查 receipt：

- intent digest 一致 → 复用原 result；
- 不再次关闭；
- evidence 标记 `recovered_from_receipt=true`；
- verifier 检查 completed action、ticket 状态和 receipt；
- 进入 `completed`。

## 为什么 checkpoint 有 hash

Envelope 中 SHA-256 可发现示例文件的偶然损坏；strict parser 还拒绝重复 JSON key 和 NaN/Infinity。恢复还检查 event sequence/state version 连续、`pending_action` 只存在于 `waiting_approval` 且精确等于当前 run 的冻结 close contract、等待状态已有查询证据，并要求 `completed` 精确符合一条合法证据路径：`already_satisfied` 只能有查询动作、已关闭 observation，且没有 close action/evidence；写入完成则必须有查询/关闭两个动作，以及绑定当前 action fingerprint、target、closed status 和 receipt ID 的 evidence。这可避免“JSON 形状合法但状态不可能”的 checkpoint 继续执行。Terminal transition 会清除待审批动作，使旧审批不能挂在已取消或已耗尽预算的 run 上。

这些业务不变量仍不是防攻击者篡改的签名：攻击者若能同时改 payload/hash，并伪造一套相互一致的状态与 evidence，仍可能绕过普通 hash。真实系统需要受保护存储、访问控制、MAC/签名以及对外部 receipt 的独立核验。

## 测试覆盖

68 个测试分为：

| 类别 | 覆盖 |
| --- | --- |
| happy path | 安全暂停、已满足目标无写入完成、恶意 note、冻结动作恢复、审批、receipt、event/version |
| approval | fingerprint、state version、target scope、expiry、畸形字段、reject、cancel 与 terminal pending 清理 |
| checkpoint | round-trip、完整性、严格 JSON、schema、event chain、phase/pending/evidence invariant |
| budget/failure | step/tool budget（含 receipt 查询）、transient/permanent write failure、畸形 action/result、reconciliation 与恶意 policy |
| idempotency/recovery | 同 intent 缓存、不同 intent 冲突、crash 恢复、evidence |

测试故意注入非 allowlist tool 和其他 ticket，证明真正的最后防线是 runtime，而不只是“安全 policy 恰好没被骗”。

## 代码阅读顺序

1. `ActionProposal` 与 fingerprint。
2. `Approval`、`Budget`。
3. `AgentState` 的 validate/transition/checkpoint/restore。
4. `DeterministicPolicy`。
5. `OfflineToolHost` 的 receipt 和 intent conflict。
6. `BoundedAgentRuntime._validate_action`。
7. `run` 的预算、暂停、执行、恢复和 verifier。
8. `run_demo` 与测试。

## 实验

每次只改一项，先预测测试结果：

1. 把恶意 note 改成另一种提示注入。
2. 让 policy 提议 ticket-8，观察 runtime rejection。
3. 把 write tool 改成非 allowlist 名称。
4. 审批后修改 action fingerprint 或 state version。
5. 分别把 `max_tool_calls` 设为 1 和 2，确认 receipt 查询也会消耗预算，且没有配额时不能关闭。
6. 注入 1 次和 5 次 transient lookup failure。
7. 相同 idempotency key 分别关闭 ticket-7 与 ticket-8。
8. 修改 checkpoint payload 而不更新 hash。
9. 更新 payload 和 hash，把 schema version 改 2，观察 schema gate。
10. 让 lookup tool 返回另一 ticket 或缺字段，观察 `invalid_tool_result`。
11. 让 waiting checkpoint 丢失 pending action/observation，或破坏 event sequence，观察恢复拒绝。
12. 把初始 ticket 状态改为 `closed`，确认 `stop_reason=already_satisfied`、`close_count=0` 且不产生写审批。

完成后恢复代码并重跑普通、`-O`、`-W error` 和 `-O -W error` 四组 68 tests。

## 进阶扩展

### SQLite 持久化

- run/state/event/receipt 四张表；
- transaction + optimistic version；
- 跨进程测试；
- 真实临时数据库放系统 temp，不加入 vault。

### Lease

- owner、lease version、expires_at；
- 两 worker 竞争恢复；
- 旧 worker lease 过期后不能提交。

### Provider adapter

- 用一个 fake provider fixture 先定义 action/ask/finish union；
- 再接真实 LLM API；
- 真实网络测试与离线 runtime tests 分开；
- key 只来自环境变量，占位配置用 `.env.example`。

### Completion verifier

- 独立 query 工具；
- 无写入完成核验当前外部状态，写入完成核验 receipt + target version；
- 对“模型返回 finish”做负向测试；
- verifier 失败时不能 completed。

## 项目验收

- [ ] demo phase=completed、close_count=1。
- [ ] 未审批时 close_count=0。
- [ ] 恶意 note 不改变 tool 或 target。
- [ ] approval 绑定 fingerprint、state version、target scope 与 expiry。
- [ ] crash 后恢复不重复关闭。
- [ ] ticket 已关闭时无审批、无写入且以 `already_satisfied` 完成。
- [ ] 同 key 不同 intent 冲突。
- [ ] checkpoint 严格解析且 schema/integrity gate 生效。
- [ ] step/tool/failure budget 能终止。
- [ ] 68 tests 在普通模式通过。
- [ ] 68 tests 在 `-O`、`-W error` 和 `-O -W error` 模式通过。
- [ ] 无网络、真实凭据、cache、大数据或模型文件。

## 自测题

1. 模型/policy 与 runtime 谁能真正执行 tool？
2. observation 的 trust label 有何用，为什么仍不够？
3. approval 为什么绑定 action fingerprint 和 state version？
4. crash window 中为何不能直接重试新 idempotency key？
5. checkpoint SHA-256 能防哪类问题，不能防哪类？
6. 无写入完成与写入完成分别需要哪些外部证据？
7. completion verifier 为何不能只相信模型返回 `finish`？
8. 示例为何仍不能证明生产 durable execution？

能运行测试并逐项回答限制，而不是只看到 “PASS”，才算完成。

## 回到目录

返回 [[Agent 核心/00-目录|Agent 核心目录]]。之后按总路线进入 [[Agent Skills/00-目录|Agent Skills]]、[[Agentic Design Patterns/00-目录|Agentic Design Patterns]] 与 [[工作流自动化/00-目录|工作流自动化]]。

## 参考资料

以下为第一方工程、安全资料与原始论文，获取/复核日期：2026-07-21。

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- Yao 等，[ReAct](https://arxiv.org/abs/2210.03629)
