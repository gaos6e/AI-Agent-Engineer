---
title: 项目：离线研究简报 Flow
aliases:
  - Offline Research Brief Flow
  - CrewAI 离线项目
tags:
  - ai-agent-engineer
  - crewai
  - project
  - flow
  - python
source_checked: 2026-07-14
---

# 项目：离线研究简报 Flow

## 项目目标

本项目让你在**不安装 CrewAI、不调用模型、不访问网络、不使用 API key** 的情况下，练习 Crew 与 Flow 最重要的工程边界：

- researcher、writer、reviewer 三个角色各自只完成一个 Task；
- Task 输入输出是可校验的 JSON 结构；
- Flow 记录状态、连续事件、尝试预算和明确终态；
- 缺引用时有限修订，预算耗尽后进入人工审核；
- 发布只接受通过审核的产物，并验证重复恢复与拒绝覆盖。

它不是 CrewAI SDK 的替代实现，也不能证明真实模型质量。它先把确定性业务控制做成可运行、可测试的基线，之后才逐步替换为真实 Agent/Task/Crew。

## 文件说明

| 文件 | 作用 |
| --- | --- |
| `examples/offline_research_flow.py` | 严格数据校验、三个 Task 桩、Crew 顺序执行、Flow 路由和幂等发布 |
| `examples/sources.json` | 两条离线资料，含 schema 版本、稳定来源 ID、主题和断言 |
| `examples/test_offline_research_flow.py` | 36 个 `unittest`，覆盖目录、Task、Flow、发布和 CLI |

先阅读 `sources.json`，再顺着 `load_catalog → run_researcher_task → run_writer_task → run_reviewer_task → run_crew → run_flow` 阅读代码。最后看 `publish_report`，理解为什么副作用需要单独的前置条件和恢复规则。

## 环境准备

本项目只使用 Python 标准库。若要练习虚拟环境，请把环境建在 vault 之外，再回到课程目录运行：

```powershell
$practice = Join-Path $HOME "Projects\crewai-offline-practice"
New-Item -ItemType Directory -Path $practice -Force | Out-Null
Set-Location $practice
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version

Set-Location "X:\path\to\your-vault\Knowledge\AI Agent Engineer\docs\CrewAI"
```

> [!note]
> 课程仓库不应保存 `.venv`。若 PowerShell 执行策略阻止激活，可以使用外部环境中的 `python.exe` 绝对路径运行后续命令。

项目没有第三方依赖，因此无需执行 `pip install`，也不要为运行示例而关闭整机安全设置。

## 第一次运行：正常路径

以下命令均从 `CrewAI` 文件夹运行：

```powershell
python -B .\examples\offline_research_flow.py --topic "Agent 可靠性"
```

`-B` 禁止写入 `.pyc`。标准输出是一份 JSON。检查：

- `stage` 为 `ready_to_publish`；
- `attempt` 为 `1`；
- `result.research.claims` 中每条断言都有 `source_ids`；
- `result.draft.markdown` 中出现 `[source-1]` 和 `[source-2]`；
- `events` 的 `sequence` 从 1 连续递增。

CLI 返回码为 `0`，表示到达 `ready_to_publish` 或 `published`，并不表示真实世界中的事实已经被独立核验。

## 观察修订和人工接管

### 第一次缺引用，第二次修复

```powershell
python -B .\examples\offline_research_flow.py --topic "Agent 可靠性" --force-revision
```

第一次 writer 故意漏掉一个引用。reviewer 发现后，Flow 产生 `routed:revise` 事件；第二次补上修订记录并进入 `ready_to_publish`。检查 `attempt` 等于 2，证明路由而非无限循环控制重试。

### 两次都失败，转人工处理

```powershell
python -B .\examples\offline_research_flow.py --topic "Agent 可靠性" --force-failure
$LASTEXITCODE
```

输出 `stage` 应为 `human_review`，`attempt` 为 2，进程返回码为 `1`。人工接管是预期终态，不是程序崩溃。

### 没有匹配来源

```powershell
python -B .\examples\offline_research_flow.py --topic "不存在的主题"
```

researcher 不编造结论，而是在 `unknowns` 中记录缺口；reviewer 拒绝无来源发布，最终进入 `human_review`。

## 发布与重复恢复

选择临时目录中的唯一文件作为输出，避免修改课程文件或碰到旧文件：

```powershell
$output = Join-Path $env:TEMP ("crewai-offline-brief-{0}.md" -f [guid]::NewGuid())

python -B .\examples\offline_research_flow.py `
  --topic "Agent 可靠性" `
  --output $output

Get-Content -LiteralPath $output
```

首次运行使用临时文件加原子替换写入，终态为 `published`。用完全相同的输入再次运行：

```powershell
python -B .\examples\offline_research_flow.py `
  --topic "Agent 可靠性" `
  --output $output
```

第二次不会重复改写内容，`publication.recovered` 为 `true`。如果已有文件内容不同，项目会拒绝覆盖并返回错误码 `2`。完成后可删除自己创建的临时文件：

```powershell
Remove-Item -LiteralPath $output
```

## 运行完整测试

测试从 `examples` 目录运行，以便 Python 正确导入同目录模块：

```powershell
Push-Location .\examples
$env:PYTHONDONTWRITEBYTECODE = "1"

python -B -m unittest -v test_offline_research_flow.py
python -B -O -m unittest -v test_offline_research_flow.py
python -B -W error -m unittest -q test_offline_research_flow.py

Pop-Location
```

三种模式分别验证：

- 普通模式：36 个行为测试全部通过；
- `-O`：证明关键校验没有依赖会被移除的普通 `assert`；
- `-W error`：把 Python warning 当成失败，暴露潜在兼容问题。

如果某个命令失败，先保留第一个失败测试的完整名称和异常，再进行最小复现；不要只重复运行直到偶然通过。

## 离线实现与 CrewAI 概念映射

| 离线项目 | 对应 CrewAI 概念 | 不能直接推断的内容 |
| --- | --- | --- |
| `run_researcher_task` 等纯函数 | Agent 承担的有限角色 | 真实 LLM 能稳定遵守角色 |
| `validate_research/draft/review` | Task 输出契约、结构化输出、guardrail | 结构正确就代表事实正确 |
| `run_crew` | 三个 Task 的 sequential Crew | 多 Agent 一定优于单 Agent |
| `run_flow` | Flow state、事件、路由与尝试预算 | 官方装饰器在任意版本签名相同 |
| `publish_report` | 有副作用 Tool 前的业务边界 | 本地原子替换等于远程事务 |
| `sources.json` | 最小 Knowledge/检索来源目录 | 两条样本足以代表真实 RAG |

## 逐步迁移到真实 CrewAI

真实集成应放在独立项目或新增的隔离示例中，不改坏这条离线基线。

1. 创建新的 `venv`，锁定已验证的 CrewAI、Python 和模型 SDK 版本；
2. 先用一个真实 Agent/Task 替换 researcher 桩，保留同一输出 schema；
3. 让现有 deterministic reviewer 检查它，运行固定评测集；
4. 再替换 writer，仍保留来源 ID、未知项和尝试预算；
5. 使用真实 `Crew(process=Process.sequential)` 组织 Task；
6. 在锁定版本中验证 `Flow`、`@start`、`@listen` 和 `@router` 的导入与行为；
7. 最后接入真实 Tool、Memory、Knowledge、事件监听和检查点；
8. 有副作用的工具先用 preview/sandbox，再加入审批和幂等键；
9. 记录模型、Prompt、依赖、评测集、成本和未验证风险。

迁移每次只替换一个边界，这样失败时能判断问题来自模型、Tool、Crew 编排还是 Flow 控制。本课程未执行真实 CrewAI、模型提供商、官方装饰器或外部存储，因此不能声称这些集成已经通过。

## 综合任务

在不访问网络的前提下扩展项目：

1. 为 `sources.json` 新增一个主题和两条来源；
2. 增加显式 `awaiting_approval` 状态，只有传入一次性审批对象才发布；
3. 模拟一次可重试工具超时和一次不可重试权限拒绝；
4. 保证重试总次数有上限；
5. 为审批内容变化、重复发布、未知来源和旧 schema 写测试；
6. 在 README 或实验记录中列出实际执行的命令、测试数和未验证项。

## 验收清单

- [ ] 正常样本一次通过，进入 `ready_to_publish`。
- [ ] 强制修订样本只修订一次，第二次通过。
- [ ] 强制失败和未知主题都进入 `human_review`。
- [ ] 每条可发布 claim 都有已知 source ID 和草稿引用。
- [ ] 事件编号连续，尝试次数没有超过预算。
- [ ] 同内容重复发布可恢复，不同内容拒绝覆盖。
- [ ] 36 个测试在普通、`-O` 和 warnings-as-errors 模式都通过。
- [ ] 运行没有产生 `.pyc`、真实凭据或课程目录内输出文件。
- [ ] 能说明离线项目没有验证哪些真实 CrewAI 能力。

## 与课程其他部分的关系

- 对象与顺序执行：[[CrewAI/01-核心对象-Crew Agent Task Process|核心对象：Crew、Agent、Task、Process]]
- Flow 和事件：[[CrewAI/02-Flow State与事件|Flow、State 与事件]]
- Tool 与结构化输出：[[CrewAI/03-Tools边界与结构化输出|Tools 边界与结构化输出]]
- 信息边界：[[CrewAI/04-Memory Knowledge与上下文|Memory、Knowledge 与上下文]]
- 评测：[[CrewAI/05-测试评测与可观测性|测试、评测与可观测性]]
- 生产边界：[[CrewAI/06-安全失败恢复与生产边界|安全、失败恢复与生产边界]]

## 主要参考资料

资料获取日期：2026-07-14。

- [CrewAI Agents](https://docs.crewai.com/en/concepts/agents)
- [CrewAI Tasks](https://docs.crewai.com/en/concepts/tasks)
- [CrewAI Crews](https://docs.crewai.com/en/concepts/crews)
- [CrewAI Processes](https://docs.crewai.com/en/concepts/processes)
- [CrewAI Flows](https://docs.crewai.com/en/concepts/flows)
- [CrewAI Testing](https://docs.crewai.com/en/concepts/testing)
- [CrewAI on PyPI](https://pypi.org/project/crewai/)
