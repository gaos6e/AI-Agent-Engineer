---
title: Tools 边界与结构化输出
aliases:
  - CrewAI Tools and Structured Output
  - CrewAI 工具与输出契约
tags:
  - crewai
  - tools
  - structured-output
source_checked: 2026-07-14
---

# Tools 边界与结构化输出

## 本节目标

你将能为 CrewAI 工具定义参数、返回、权限、副作用和错误类别，理解官方当前 `BaseTool` / `@tool` 形状，并用 Task 的 Pydantic/JSON 输出与 guardrail 建立 Agent 间契约。

## 工具首先是权限接口

工具把模型建议变成数据读取或外部动作。每个 Agent 只获得当前 Task 需要的工具：研究者可读本地来源，写作者只消费结构化研究结果，审核者不应拥有发布权限。

工具契约至少包含：

| 字段 | 问题 |
| --- | --- |
| 名称/描述 | 何时用，何时不能用？ |
| 参数 schema | 类型、范围、规范化和拒绝条件是什么？ |
| 返回 schema | 成功、空结果和错误怎样区分？ |
| 权限 | 使用哪种身份，可访问哪些资源？ |
| 副作用 | 只读、可撤销还是不可逆？ |
| 超时 | 超时意味着失败还是提交状态未知？ |
| 重试 | 哪些类别可重试，预算多少？ |
| 幂等 | 如何识别同一个业务动作？ |
| 审计 | 保留什么摘要，哪些秘密绝不记录？ |

模型输出的参数必须经过执行层校验。Tool description 帮助选择工具，不授予权限。

## 当前官方自定义工具形状

官方 Tools 页面给出两种主要方法：继承 `BaseTool` 并声明 Pydantic `args_schema`，或使用 `@tool` 装饰函数。以下是用于阅读的最小形状，未在本库真实安装环境执行：

```python
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class LocalSearchInput(BaseModel):
    topic: str = Field(min_length=1, max_length=120)

class LocalSearchTool(BaseTool):
    name: str = "search_approved_local_sources"
    description: str = "Search only the approved local source catalog."
    args_schema: Type[BaseModel] = LocalSearchInput

    def _run(self, topic: str) -> str:
        return search_catalog(topic)
```

`search_catalog` 是你自己的受控实现。返回 JSON 字符串前要明确 schema；不要在异常中泄露文件系统、凭据或服务端堆栈。官方页面也展示同步/异步工具和 `cache_function`，但缓存只能用于确认可复用的读操作，不能缓存付款、发送等副作用结果。

## 读写工具分离

高风险动作拆为：

1. `preview_publish`：只读，生成规范化动作、目标和差异；
2. Flow 保存动作指纹并请求批准；
3. `publish_report`：验证可信审批、目标和幂等 ID；
4. `get_publication_receipt`：恢复时查询是否已提交。

不要让工具从 Task 文本中搜索“已批准”三个字。批准记录应来自受控 state 或授权服务。

## Task 的结构化输出

官方 Tasks 文档列出：

- `output_pydantic=Model`：TaskOutput 的 `pydantic` 包含模型实例；
- `output_json=Model`：TaskOutput 的 `json_dict` 包含 JSON 结果；
- 默认只保证 `raw`；
- `guardrail` 可在进入下游前验证 Task 输出。

概念示例：

```python
from pydantic import BaseModel
from crewai import Task

class Claim(BaseModel):
    text: str
    source_ids: list[str]

class ResearchResult(BaseModel):
    claims: list[Claim]
    unknowns: list[str]

task = Task(
    description="Extract claims only from approved sources.",
    expected_output="Claims with source IDs plus explicit unknowns.",
    output_pydantic=ResearchResult,
)
```

真实版本是否允许省略 `agent`、guardrail 的确切签名和重试行为，应在锁定版本验证。结构校验通过不代表事实正确，仍要检查每个 `source_id` 存在且正文支持 claim。

## guardrail 的职责

适合确定性 guardrail 的内容：

- JSON/Pydantic 类型；
- 必填字段、长度、枚举；
- 引用 ID 存在；
- 禁止的工具或目标；
- 文件路径是否位于允许目录；
- 是否达到迭代或成本预算。

文风、论证质量可用模型 grader 辅助，但必须固定量表并通过人工样本校准。审核 Agent 若与生成 Agent 使用相同缺失来源，并不会天然更可信。

## 工具错误分类

推荐返回稳定错误类别：`invalid_input`、`not_found`、`permission_denied`、`transient`、`permanent`、`unknown_commit`。只有瞬时故障有限重试；权限和政策拒绝不应换 Agent 绕过；提交状态未知先查回执。

```json
{
  "ok": false,
  "error": {
    "category": "permission_denied",
    "retryable": false,
    "message": "caller cannot publish to this target"
  }
}
```

## 外部内容是不可信数据

网页、文档、MCP 返回和 Knowledge 片段可能含提示注入。工具层必须限制路径、网络目标、SQL/命令参数和身份；模型不能依据文档中的指令扩大 allowlist。需要 Shell 或代码执行时使用隔离服务和一次性环境，不在主机直接执行模型生成字符串。

## 常见错误与排查

- **所有 Agent 共享一组工具**：按 Task 建最小白名单。
- **只验证 JSON 可解析**：再验证字段语义、来源和业务约束。
- **把错误自然语言交给重试器**：适配成有限类别。
- **写操作自动缓存/重试**：使用业务幂等 ID 和回执。
- **输出文件路径由模型自由决定**：规范化后确认位于允许根目录。
- **复制官方示例中的密钥占位写法**：真实值只从环境或密钥服务读取。

## 练习

为研究 Crew 设计 `search_local_sources`、`read_source`、`preview_publish`、`publish_report`：

1. 写参数与返回 schema；
2. 标出每个 Agent 的工具白名单；
3. 为 publish 设计审批、动作指纹和幂等回执；
4. 写 8 个失败样本，包括路径越界、未知来源、权限拒绝和提交超时；
5. 说明哪些校验属于 Task guardrail，哪些必须在工具服务执行。

## 掌握检查

- [ ] 能说明工具描述与执行授权的差别。
- [ ] 能识别 `BaseTool`、`args_schema` 与 `@tool` 的当前官方形状。
- [ ] 能用 `output_pydantic`/`output_json` 约束 Task 产物。
- [ ] 能同时验证 schema、来源和业务语义。
- [ ] 能为写工具设计预览、批准、幂等和回执。

## 下一步

进入 [[CrewAI/04-Memory Knowledge与上下文|Memory、Knowledge 与上下文]]，决定哪些信息进入哪一层生命周期。

## 参考资料

- [CrewAI Tools](https://docs.crewai.com/en/concepts/tools)（页面标签 `v1.14.0`；核对：2026-07-14）
- [CrewAI Tasks](https://docs.crewai.com/en/concepts/tasks)（页面标签 `v1.12.1`；核对：2026-07-14）
- [CrewAI Agents](https://docs.crewai.com/en/concepts/agents)（页面标签 `v1.14.6`；核对：2026-07-14）
- [[Agentic Design Patterns/00-初学者路线/04-工具记忆与状态边界|工具、记忆与状态边界]]
