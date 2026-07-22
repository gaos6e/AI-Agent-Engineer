---
title: 离线 DAG 工作流项目
tags:
  - workflow-automation
  - dag
  - project
aliases:
  - 工作流自动化项目
source_checked: 2026-07-22
---

# 离线 DAG 工作流项目

## 项目目标

从零运行一个订单工作流：验证一个**严格订单应用 profile** 的 CloudEvent，执行 `validate`，让 `reserve_inventory` 与 `risk_check` 进入同一 ready batch，等待对 `charge` 的绑定审批，再执行扣款与通知。失败路径会有限重试、对已提交结果做幂等恢复，并在永久失败时补偿已经完成的副作用。

项目只使用 Python 标准库，适合在 Windows 11 + PowerShell 7 离线完成。它是教学型单进程模拟器，不声称提供生产级事务、队列或 exactly-once。

## 文件

- [workflow_engine.py](%E5%B7%A5%E4%BD%9C%E6%B5%81%E8%87%AA%E5%8A%A8%E5%8C%96/examples/workflow_engine.py)：定义校验、严格 CloudEvent 应用 profile、状态机、重试、审批、检查点、幂等副作用、补偿和安全事件。
- [workflow.json](%E5%B7%A5%E4%BD%9C%E6%B5%81%E8%87%AA%E5%8A%A8%E5%8C%96/examples/workflow.json)：固定版本的 DAG 与每步策略。
- [test_workflow_engine.py](%E5%B7%A5%E4%BD%9C%E6%B5%81%E8%87%AA%E5%8A%A8%E5%8C%96/examples/test_workflow_engine.py)：覆盖正常路径和故障路径的标准库测试。

## 环境准备

先使用 `venv + pip`；本项目没有第三方依赖，因此无需安装包。以下代码块按顺序从同时包含 `docs/` 与 `.website/` 的项目根目录开始运行；测试结束后会返回项目根目录：

```powershell
Push-Location -LiteralPath 'docs\工作流自动化' # 临时进入课程目录，之后可用 Pop-Location 恢复原路径
python -m venv .venv # 创建仅供本机实验使用的 Python 虚拟环境
.\.venv\Scripts\Activate.ps1 # 在当前 PowerShell 会话激活该虚拟环境
python -m pip --version # 确认当前会话确实使用虚拟环境中的 pip
```

`.venv` 仅用于本地学习，不要加入版本控制。也可以直接使用已有 Python 3 运行。

## 第一步：验证定义

```powershell
python -B .\examples\workflow_engine.py --validate # 只验证 DAG 定义、边和合同；-B 不生成 __pycache__
```

定义验证会拒绝未知顶层字段、重复节点、未知依赖、自依赖、环、非法重试配置和错误类型。输出定义名、版本与 SHA-256 指纹；指纹用于恢复时检测加载了不同定义，不是安全签名。

触发 profile 只接受本项目定义的 event type 和 data 形状，并对可选 `time` 要求带显式 UTC 偏移、可由标准库解析的 RFC 3339 子集；它有意不接受通用 CloudEvents 的扩展属性。事件身份使用规范化的 `(source, id)` 编码而非分隔符拼接，因此 `/a + b::c` 与 `/a::b + c` 不会相撞。真实 HTTP/webhook 入口仍必须在交给该函数之前完成原始 body 的签名/调用方验证、大小限制、新鲜度/nonce 检查和服务端授权。

## 第二步：运行演示

```powershell
python -B .\examples\workflow_engine.py # 运行离线工作流 demo，观察成功、等待和恢复状态而不访问外部服务
```

演示完成三条证据链：

1. 订单事件在库存提交后模拟一次进程未知结果，重试复用同一幂等结果，只产生一次库存预留；
2. 工作流暂停审批、序列化检查点、恢复并使用与实例/步骤/载荷/版本/有效期绑定的批准完成；
3. 第二个实例的通知步骤永久失败，系统按已注册补偿记录先退款、再释放库存，最终进入 `failed_compensated`。

脚本使用临时目录检查检查点，不会在知识库中留下运行产物。

## 第三步：运行测试

```powershell
$env:PYTHONWARNINGS = 'error' # 将 Python 警告提升为错误，避免资源/兼容问题被忽略
python -B -m unittest discover -s .\examples -p 'test_*.py' -v # 普通模式详细运行工作流引擎回归测试
python -B -O -m unittest discover -s .\examples -p 'test_*.py' -v # 优化模式验证控制逻辑没有依赖 bare assert
Remove-Item Env:PYTHONWARNINGS # 清理仅为本段测试设置的环境变量，避免影响后续命令
Pop-Location # 返回进入课程目录前的原始 PowerShell 工作目录
```

普通模式与 `-O` 都要通过。`-O` 会移除裸 `assert`，因此项目验证使用显式异常和 `unittest` 断言；这能发现“测试只在非优化模式有效”的问题。

本轮基线共有 74 项测试，并额外在 `PYTHONWARNINGS=error` 下复跑。测试数只是覆盖面的线索；真正证据是每项对应了定义非法形状、RFC 3339 时间 profile、结构化事件身份、重复事件、幂等冲突、未知结果、审批篡改、检查点损坏、重试耗尽和补偿失败等可观察断言。

## 阅读代码的顺序

1. `load_definition()`：如何对 JSON 做严格形状检查和 DAG 环检测。
2. `validate_event()`、`event_identity_key()` 与 `WorkflowCoordinator.start()`：如何收窄 CloudEvents 为应用 profile，用规范化 `(source, id)` 去重并拒绝同身份异载荷。
3. `EffectStore.perform()`：如何绑定幂等键、意图哈希与已有结果。
4. `run_until_blocked()`：ready batch、有限重试、审批等待和终止状态。
5. `encode_checkpoint()/decode_checkpoint()`：检查点完整性与严格恢复。
6. `_compensate()`：补偿的独立幂等键、失败状态和可观察事件。

## 需要亲自完成的扩展

### 基础扩展

1. 在 `workflow.json` 增加 `manual_review` 分支，并为未知 decision 设置安全默认。
2. 为 `notify` 加最大延迟；超过 deadline 时不再发送过时消息。
3. 新增一个同键不同金额的冲突案例，确认不会复用旧扣款结果。

### 工程扩展

1. 用 SQLite 事务保存实例、step attempt、租约和幂等结果；进程内字典不再作为保证边界。
2. 加入两个 worker 并发领取同一步的条件更新测试。
3. 添加 schedule logical fire time 与时区/补跑策略。
4. 将 `risk_check` 替换为 mock LLM 节点：输出 schema、固定评测集、模型/提示版本和无效输出回退缺一不可。
5. 为 `compensation_failed` 增加只允许受控操作的人工队列。

## 生产化差距清单

- 状态与幂等表需要事务型持久存储、备份和访问控制；
- 多 worker 需要租约、心跳和 compare-and-set；
- 外部回调需要真实身份认证、防重放和服务端授权；
- `source + id` 只是经过认证后可用的事件身份；本例只检查 `source` 非空，生产网关应由协议库验证 URI-reference，并在去重账本保存结构化键、载荷指纹、TTL/保留策略与冲突处置；
- 检查点需要受保护的完整性/认证机制，不能只靠普通哈希；
- 日志、指标、trace 与告警需接入受控后端；
- 凭据必须来自密钥管理，不能放入定义或环境示例的真实值；
- 发布需兼容旧实例并用脱敏历史做恢复/重放测试。

## 运行手册练习

假设支付供应商持续 503、队列年龄增长：

1. 停止哪些新触发，保留哪些已批准实例？
2. 如何确认 retry budget 没有继续放大故障？
3. 哪些支付状态需要按幂等键对账？
4. 恢复后如何小批量排空，设置什么回退门槛？
5. 哪些实例必须人工处理而不能自动重跑？

## 自测题

1. ready batch 表示什么，为什么不等于已经并行执行？
2. 同一 `source + id` 的事件为何还要比较载荷哈希，为什么键不能用未转义分隔符拼接？
3. 副作用提交后抛出暂时错误，重试为何不会再次提交？
4. 审批为什么同时绑定载荷指纹、定义版本、状态版本和有效期？
5. 补偿失败为什么不能把实例标成普通 `failed`？
6. 检查点 SHA-256 能防止哪类问题，不能防止哪类攻击？

## 掌握检查

- [ ] 我能运行定义校验、演示和两种测试模式。
- [ ] 我能解释正常、等待审批、重试耗尽、拒绝补偿和补偿失败的状态转换。
- [ ] 我能证明重复事件与崩溃后重试不会产生第二次逻辑副作用。
- [ ] 我能构造并识别同一幂等键不同意图的冲突。
- [ ] 我能写出上线、暂停、排空、回退和人工处置的运行手册。
- [ ] 我不会把单进程示例的内存记录宣传为生产级 exactly-once。

## 回到目录

返回 [[工作流自动化/00-目录|工作流自动化学习目录]]。

## 参考资料

- [Open Workflow Specification 1.0.3](https://serverlessworkflow.io/)（访问于 2026-07-22）
- [CloudEvents Specification 1.0.2](https://github.com/cloudevents/spec/tree/v1.0.2)（访问于 2026-07-22）
- [Temporal Platform Documentation](https://docs.temporal.io/)（产品实现参考，访问于 2026-07-22）
- [Microsoft：Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)（访问于 2026-07-22）
- [GitHub：Validating webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries)（签名应覆盖原始 payload，访问于 2026-07-22）
