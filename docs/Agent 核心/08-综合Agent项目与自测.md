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
source_checked: 2026-07-14
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
- commit-before-checkpoint crash window；
- idempotency receipt 恢复；
- completion verifier。

> [!warning] 能力边界
> 这不是通用 Agent 框架，也没有声称模拟某家模型的推理质量。它只用 Python 标准库演示 runtime invariant。真实系统还需要持久数据库、分布式 lease、真实身份/授权、provider adapter、监控和部署级测试。

## 文件

| 文件 | 作用 |
| --- | --- |
| [bounded_agent.py](Agent%20%E6%A0%B8%E5%BF%83/examples/bounded_agent.py) | 状态、policy、runtime、tool host、approval、checkpoint 与 demo |
| [test_bounded_agent.py](Agent%20%E6%A0%B8%E5%BF%83/examples/test_bounded_agent.py) | 49 个正/负向回归测试 |

## 环境

项目无第三方依赖，可直接用稳定版 Python 3。若希望隔离：

```powershell
Set-Location "X:\path\to\your-vault\Knowledge\AI Agent Engineer\docs\Agent 核心"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip --version
```

不需要 `pip install` 任何包；`.venv` 只在本机使用，不得加入知识库或 Git。

不创建环境也可直接运行：

```powershell
Set-Location "X:\path\to\your-vault\Knowledge\AI Agent Engineer\docs\Agent 核心"
python -B .\examples\bounded_agent.py
python -B -W error .\examples\test_bounded_agent.py
python -B -O -W error .\examples\test_bounded_agent.py
```

`-B` 禁止生成 `__pycache__`；`-W error` 把警告当失败；`-O` 验证关键控制未误写成会被优化移除的 bare `assert`。

当前已验证环境：Windows 11、PowerShell 7、Python 3.11。

## 预期 demo

```json
{
  "status": "ok",
  "phase": "completed",
  "steps": 3,
  "tool_calls": 2,
  "close_count": 1,
  "event_types": [
    "observation_recorded",
    "approval_requested",
    "completion_verified"
  ]
}
```

关键不是输出格式，而是 `close_count` 始终为 1。

## 轨迹逐步解释

### 1. 读取当前 ticket

Policy 只允许 `lookup_ticket(ticket-7)`。Tool 返回：

- status=open；
- 一段恶意 customer note，要求关闭其他工单和导出环境变量。

Runtime 把它包成：

```json
{
  "source": "tool:lookup_ticket",
  "trust": "untrusted",
  "purpose": "ticket facts only; never runtime instructions",
  "data": {"ticket_id": "ticket-7", "...": "..."},
  "sha256": "..."
}
```

恶意 note 不进入 runtime policy。

### 2. 提出并冻结写动作

Policy 提出 `close_ticket(ticket-7)`。Runtime 验证：

- tool 在 allowlist；
- arguments 只有当前 ticket；
- risk=write；
- idempotency key 精确绑定 run + ticket + contract version。

随后保存 pending action，进入 `waiting_approval`。此时 `close_count=0`。

### 3. 创建 approval

`make_approval` 绑定：

- action ID；
- action fingerprint；
- state version；
- decision；
- step expiry。

参数、目标或状态变化都会让批准失效。

### 4. 模拟 crash window

Runtime 调用 tool：

1. tool 持久化（示例中为内存）receipt 并关闭 ticket；
2. 在 runtime 写回 completed state 前抛出 `SimulatedCrash`。

此时外部动作已发生，但 checkpoint 仍是 waiting_approval。

### 5. 从旧 checkpoint 恢复

新 state 从 checkpoint 重建；用同一 idempotency key 查 receipt：

- intent digest 一致 → 复用原 result；
- 不再次关闭；
- evidence 标记 `recovered_from_receipt=true`；
- verifier 检查 completed action、ticket 状态和 receipt；
- 进入 `completed`。

## 为什么 checkpoint 有 hash

Envelope 中 SHA-256 可发现示例文件的偶然损坏；strict parser 还拒绝重复 JSON key 和 NaN/Infinity。它不是防攻击者篡改的签名：攻击者若能同时改 payload/hash，仍可伪造。真实系统需要受保护存储、访问控制和 MAC/签名。

## 测试覆盖

49 个测试分为：

| 类别 | 覆盖 |
| --- | --- |
| happy path | 安全暂停、恶意 note、审批、receipt、event/version |
| approval | fingerprint、state version、expiry、reject、cancel |
| checkpoint | round-trip、完整性、严格 JSON、schema、phase/counter/invariant |
| budget/failure | step/tool budget、transient retry、permanent failure、恶意 policy |
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
5. 把 `max_tool_calls` 设为 1。
6. 注入 1 次和 5 次 transient lookup failure。
7. 相同 idempotency key 分别关闭 ticket-7 与 ticket-8。
8. 修改 checkpoint payload 而不更新 hash。
9. 更新 payload 和 hash，把 schema version 改 2，观察 schema gate。

完成后恢复代码并重跑普通/`-O` 49 tests。

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
- receipt + target version；
- 对“模型返回 finish”做负向测试；
- verifier 失败时不能 completed。

## 项目验收

- [ ] demo phase=completed、close_count=1。
- [ ] 未审批时 close_count=0。
- [ ] 恶意 note 不改变 tool 或 target。
- [ ] approval 绑定 fingerprint、state version 与 expiry。
- [ ] crash 后恢复不重复关闭。
- [ ] 同 key 不同 intent 冲突。
- [ ] checkpoint 严格解析且 schema/integrity gate 生效。
- [ ] step/tool/failure budget 能终止。
- [ ] 49 tests 在普通模式通过。
- [ ] 49 tests 在 `-O` + warnings-as-errors 通过。
- [ ] 无网络、真实凭据、cache、大数据或模型文件。

## 自测题

1. 模型/policy 与 runtime 谁能真正执行 tool？
2. observation 的 trust label 有何用，为什么仍不够？
3. approval 为什么绑定 action fingerprint 和 state version？
4. crash window 中为何不能直接重试新 idempotency key？
5. checkpoint SHA-256 能防哪类问题，不能防哪类？
6. completion verifier 使用了哪些外部证据？
7. 示例为何仍不能证明生产 durable execution？

能运行测试并逐项回答限制，而不是只看到 “PASS”，才算完成。

## 回到目录

返回 [[Agent 核心/00-目录|Agent 核心目录]]。之后按总路线进入 [[Agent Skills/00-目录|Agent Skills]]、[[Agentic Design Patterns/00-目录|Agentic Design Patterns]] 与 [[工作流自动化/00-目录|工作流自动化]]。

## 参考资料

以下为第一方工程、安全资料与原始论文，获取/复核日期：2026-07-14。

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- Yao 等，[ReAct](https://arxiv.org/abs/2210.03629)
