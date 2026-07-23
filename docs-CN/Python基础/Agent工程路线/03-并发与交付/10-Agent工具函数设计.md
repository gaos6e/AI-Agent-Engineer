---
title: "Agent 工具函数设计"
tags: [ ai-agent-engineer, Python, tools, agent ]
aliases: [ Python Agent 工具契约, Tool 函数设计 ]
lang: zh-CN
translation_key: Python基础/Agent工程路线/03-并发与交付/10-Agent工具函数设计.md
translation_route: en/python-fundamentals/engineering-route/03-concurrency-and-delivery/10-agent-tool-function-design
translation_default_route: zh-CN/Python基础/Agent工程路线/03-并发与交付/10-Agent工具函数设计
---

# Agent 工具函数设计

## 本节目标

把一个普通 Python 函数提升为可被 Agent 安全调用的工具边界：输入窄且可验证，副作用和权限明确，输出稳定可解析，失败可恢复或可升级，并能在不调用真实模型的情况下完整测试。

## 工具不是“把所有函数暴露给模型”

模型产生的是调用建议；应用仍负责验证、授权、执行和记录。一个工具契约至少包含：

```text
名称与用途
├─ 输入 schema、长度/枚举/格式限制
├─ 调用前权限和业务前置条件
├─ 明确的读/写/网络副作用
├─ 超时、并发、幂等与重试语义
├─ 稳定结果和错误类别
└─ 审计字段、人工审批与停止条件
```

Python 类型提示帮助开发者和工具生成器理解结构，但不会自动做运行时校验。JSON Schema 或 SDK 声明也只是第一道门；执行前仍需检查路径、资源所有权、当前身份、大小上限和业务状态。

## 先写窄函数

“管理文件”太宽；“读取工作区内一个 UTF-8 文本文件，最多 64 KiB”更容易授权和测试：

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ReadTextResult:
    relative_path: str
    content: str
    size_bytes: int


class ToolInputError(ValueError):
    pass


def read_workspace_text(
    relative_path: str,
    *,
    workspace: Path,
    max_bytes: int = 65_536,
) -> ReadTextResult:
    if max_bytes < 1:
        raise ToolInputError("max_bytes 必须至少为 1")
    if not relative_path or Path(relative_path).is_absolute():
        raise ToolInputError("必须提供工作区内相对路径")

    root = workspace.resolve(strict=True)
    candidate = (root / relative_path).resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ToolInputError("路径越出工作区") from exc

    if not candidate.is_file():
        raise ToolInputError("目标必须是普通文件")
    size = candidate.stat().st_size
    if size > max_bytes:
        raise ToolInputError("文件超过读取上限")
    return ReadTextResult(
        relative_path=candidate.relative_to(root).as_posix(),
        content=candidate.read_text(encoding="utf-8"),
        size_bytes=size,
    )
```

这个示例仍不是通用安全沙箱：Windows reparse point、权限变化、检查后替换（TOCTOU）和特殊文件需要更强的操作系统级隔离。关键是不要把字符串前缀比较误当成可靠路径授权。

## 分离纯核心与执行适配器

推荐数据流：

```text
模型/工作流建议
  → schema 校验
  → 业务与权限校验
  → 需要时人工审批
  → 受限 Python 适配器执行
  → 稳定结果封装
  → 日志/指标/trace
```

解析与决策尽量是纯函数；文件、网络、数据库和命令执行集中在小适配器中。这样可以用假适配器测试策略，而不让单元测试触碰真实系统。

## 稳定结果而非随意字符串

工具输出需要让调用者区分成功、可修正输入、暂时失败和需要人工处理：

```python
from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ToolResult(Generic[T]):
    status: Literal["ok", "invalid_input", "temporary_failure", "denied"]
    data: T | None = None
    message: str | None = None
    retryable: bool = False
```

实际系统可以采用 SDK 定义的结果结构，不必照抄本类。无论格式如何，都应保持错误类别稳定、内容最小且不包含堆栈、密钥或完整服务响应。详细根因留在受控日志，并用不含个人信息的操作 ID 关联。

## 副作用、幂等与授权

每个工具都应回答：

- 只读还是写入？写到哪里？
- 重复调用会产生同一结果、覆盖、重复记录，还是不可逆操作？
- 哪些参数由模型提出，哪些由可信应用注入？
- 调用者身份和资源所有权在哪里验证？
- 是否需要预览、确认、双人审批或补偿动作？

不要让模型传入 `workspace`、数据库连接、API key 或最大权限；这些由应用配置并注入。高风险写操作采用最小权限、允许列表和审批，不用提示词代替强制控制。

## 测试矩阵

至少覆盖：

| 维度 | 示例 |
| --- | --- |
| 合法输入 | 最小文件、Unicode、上限边界 |
| 非法输入 | 空路径、绝对路径、越界路径、过大文件 |
| 权限 | 无权资源、已撤销授权、审批拒绝 |
| 故障 | 文件消失、超时、瞬时依赖失败 |
| 重复 | 相同幂等键、重复执行、部分成功后重试 |
| 取消 | 执行前、执行中、写入前取消 |
| 观测 | 错误类别和 operation_id 存在，日志无秘密 |

Tool Calling 协议如何声明 schema、模型如何提出调用、应用如何回传结果，放在 [[Tool Calling（含 Function Calling）/00-目录|Tool Calling（含 Function Calling）]]。本节只建立可被该协议调用的 Python 执行边界。

## 练习

1. 实现上面的 `read_workspace_text`，使用临时目录测试合法、越界、过大与不存在文件。
2. 为一个“创建工单”工具写副作用声明、幂等键和人工审批条件，不必联网。
3. 把一个返回自由文本错误的函数改为稳定错误类别；说明哪些内容写日志、哪些返回模型。
4. 画出模型建议到真实执行的信任边界，标明每一层由谁控制。

## 自测

- [ ] 能解释 Python 类型提示为何不能替代运行时校验。
- [ ] 能把路径、连接和密钥等可信依赖与模型参数分开。
- [ ] 能明确工具的权限、副作用、幂等、超时和审批语义。
- [ ] 能设计稳定的成功/失败结果而不泄露内部信息。
- [ ] 能在没有模型和真实外部服务时测试执行边界。

## 相关概念与下一步

- 前置：[[Python基础/Agent工程路线/03-并发与交付/09-项目结构CLI与可复现运行|项目结构、CLI 与可复现运行]]。
- 下一节：[[Python基础/Agent工程路线/04-项目与自测/11-项目-可靠任务队列|项目：可靠任务队列]]。
- 协议与 schema 见 [[JSON/00-目录|JSON]]、[[Tool Calling（含 Function Calling）/00-目录|Tool Calling（含 Function Calling）]] 与 [[MCP/00-目录|MCP]]。
- Agent 的规划、记忆、停止和授权闭环见 [[Agent 核心/00-目录|Agent 核心]]。

## 参考资料

获取日期：**2026-07-14**。

- [Python：`typing`](https://docs.python.org/3.14/library/typing.html)
- [Python：`pathlib`](https://docs.python.org/3.14/library/pathlib.html)
- [OWASP：Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal)
- [NIST AI RMF Generative AI Profile](https://doi.org/10.6028/NIST.AI.600-1)
