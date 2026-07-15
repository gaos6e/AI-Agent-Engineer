---
title: 核心对象：Crew Agent Task Process
aliases:
  - CrewAI Core Objects
  - CrewAI 核心对象
tags:
  - crewai
  - agent
  - task
  - process
source_checked: 2026-07-14
---

# 核心对象：Crew、Agent、Task、Process

## 本节目标

学完本节，你应能从职责而非人设理解四个核心对象，为 Task 写结构化契约，并选择 sequential 或 hierarchical Process。还要能建立隔离的 Windows 环境，确认“实际安装版本”而不是只看网页标题。

## 先验证安装事实

PyPI 在本次核对时给出 `crewai 1.15.2` 和 Python `>=3.10,<3.14`。若 `python --version` 是 3.14，就不满足该快照约束。应选择兼容解释器新建环境，不能期待 pip 忽略约束后仍可靠运行。

```powershell
py -0p
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install "crewai==1.15.2"
python -c "from importlib.metadata import version; print(version('crewai'))"
python -m pip check
```

这是学习项目中的版本快照。团队项目还应保存锁文件或带哈希的依赖清单，并在升级前重新运行回归集。官方文档当前主推 `uv`；理解虚拟环境、解释器和依赖解析后，再使用官方 CLI/`uv` 创建规范项目。

## 四个对象的责任

| 对象 | 负责什么 | 不负责什么 |
| --- | --- | --- |
| `Agent` | 角色、目标、模型、工具、委派和运行预算 | 不自动获得真实知识或业务权限 |
| `Task` | 具体工作、期望输出、上下文、guardrail 和产物格式 | 不应只是一句模糊愿望 |
| `Crew` | 收集 Agent 与 Task，配置 Process 并启动协作 | 不替业务定义安全终态 |
| `Process` | 决定任务推进与分派方式 | 不保证分解正确或结果真实 |

官方 Agents 页面把 `role`、`goal`、`backstory` 作为核心参数，并列出工具、模型、最大迭代、时间和速率等执行控制。角色描述帮助模型理解任务，但不能替代工具权限、来源和验收测试。

## Task 契约先于 Agent 人设

坏任务：

> 研究这个主题，写得专业一些。

可验收任务：

- 输入：三份允许使用的文档及稳定 `source_id`；
- 输出：`claims`、`source_ids`、`unknowns` 三类字段；
- 规则：每条 claim 至少一个已知来源；无证据时写入 unknowns；
- 禁止：联网补写、调用发布工具；
- 失败：schema 无效、未知来源、达到步骤预算。

官方 Tasks 页面提供 `output_pydantic` 与 `output_json` 来生成结构化 TaskOutput，也提供 `guardrail` 验证输出。但 schema 通过只证明结构正确；“来源是否真的支持主张”仍需应用代码或人工 grader 检查。

## 当前官方最小对象形状

下面代码形状来自 2026-07-14 访问的官方 Agents/Tasks/Crews 文档，用于识别对象关系；本库没有安装真实包或配置模型，因此未执行：

```python
from crewai import Agent, Crew, Process, Task

researcher = Agent(
    role="Local evidence researcher",
    goal="Extract claims only from approved sources",
    backstory="You work within strict evidence boundaries.",
    allow_delegation=False,
)

research_task = Task(
    description="Extract supported claims for {topic}.",
    expected_output="Structured claims with source identifiers and unknowns.",
    agent=researcher,
)

crew = Crew(
    agents=[researcher],
    tasks=[research_task],
    process=Process.sequential,
)

# result = crew.kickoff(inputs={"topic": "Agent reliability"})
```

注释掉 kickoff 是为了防止读者误以为示例无需模型配置即可运行。实际参数、默认模型和导入路径必须以锁定版本验证。

## sequential 与 hierarchical

官方当前文档明确列出：

- `Process.sequential` 按 Task 列表顺序执行；上游输出可成为下游上下文，也可通过 Task 的 `context` 显式指定。
- `Process.hierarchical` 由 manager 分派与验证任务，需要 `manager_llm` 或 `manager_agent`；Task 不预先绑定具体执行 Agent。

顺序过程适合依赖明确的研究→写作→审核。分层过程多了管理者模型的分派、复核、成本与停止条件，只有动态分工在评测中确实优于固定流程时才采用。不要为每个动词创建一个 Agent，也不要把“审核 Agent”当独立真相来源。

## Crew、Flow 还是普通 Python

- 固定 JSON 转换、校验、文件移动：普通 Python。
- 分支、审批、等待、持久状态与外部业务步骤：Flow 或普通状态机。
- 边界清楚但需要语言推理的多个 Task：Crew。
- 外层业务控制 + 内层认知协作：Flow 调用一个或多个 Crew。

如果一个模型加两个受限工具已经完成任务，就不必拆成三个 Agent。多 Agent 的价值要来自不同上下文、权限、专业评测或可证明的并行收益。

## YAML 项目与直接代码

官方 Agents/Crews 文档推荐用 YAML 配置 Agent 和 Task，并通过 CrewAI 项目结构收集它们；直接 Python 定义仍被列为替代方式。初学时可先用直接代码看清对象，随后用官方 Quickstart 生成独立项目，检查：

- YAML 变量是否由 `kickoff(inputs=...)` 提供；
- Agent 名称与 Task 引用是否一致；
- 凭据是否只来自环境；
- 项目锁定版本是否与示例匹配。

## 常见错误与排查

- **只写 backstory**：补上 Task 输入、输出、失败条件和工具 allowlist。
- **所有 Agent 都有全部工具**：按 Task 权限拆分，只把必要工具传给 Agent/Task。
- **下游解析上游自由文本**：使用 `output_pydantic` 或应用层 schema。
- **hierarchical 无 manager**：当前官方文档要求 `manager_llm` 或 `manager_agent`。
- **文档标签等于安装版**：用 `importlib.metadata.version('crewai')` 读取环境事实。
- **升级后只跑演示**：先跑冻结输入、结构、轨迹和权限回归集。

## 练习

把“生成每周项目状态”拆成最多三个 Task。为每个 Task 写：输入、输出 schema、执行 Agent、允许工具、完成条件和失败条件。然后回答：

1. 固定顺序是否足够？
2. manager 能解决什么未知分派问题？
3. manager 增加哪些模型调用与失败路径？
4. 能否用一个 Agent 加多个 Task 达到同样效果？

## 掌握检查

- [ ] 能解释四个核心对象而不依赖 API 背诵。
- [ ] 能从环境读取实际安装版本并运行 `pip check`。
- [ ] 能写机器可验证的 Task 产物与失败条件。
- [ ] 能说明 hierarchical 为何需要 manager 和额外评测。
- [ ] 能指出角色描述不能替代知识、权限和验收。

## 下一步

进入 [[CrewAI/02-Flow State与事件|Flow、State 与事件]]，把 Crew 放进受控业务生命周期。

## 参考资料

- [PyPI：crewai](https://pypi.org/project/crewai/)（1.15.2 与 Python 约束；核对：2026-07-14）
- [CrewAI Installation](https://docs.crewai.com/en/installation)（动态文档，页面标签 `v1.14.0`；核对：2026-07-14）
- [Agents](https://docs.crewai.com/en/concepts/agents)、[Tasks](https://docs.crewai.com/en/concepts/tasks)、[Crews](https://docs.crewai.com/en/concepts/crews)、[Processes](https://docs.crewai.com/en/concepts/processes)（官方动态文档；核对：2026-07-14）
