---
title: 项目结构、CLI 与可复现运行
tags: [ ai-agent-engineer, Python, cli, packaging ]
aliases: [ Python 项目结构, Python CLI ]
---

# 项目结构、CLI 与可复现运行

## 本节目标

把零散脚本整理为有入口、有依赖声明、有测试边界的最小项目；能设计可自动化调用的命令行接口，并区分“源代码可运行”“环境可重建”和“构建产物可发布”。

## 从单文件开始，不为结构而结构

学习阶段，一个无第三方依赖的工具可以这样开始：

```text
task-reporter/
├── task_reporter.py
├── sample_tasks.json
└── test_task_reporter.py
```

当模块增多、需要安装命令或要避免测试误导入工作目录文件时，再采用包结构：

```text
task-reporter/
├── pyproject.toml
├── README.md
├── src/
│   └── task_reporter/
│       ├── __init__.py
│       ├── cli.py
│       └── core.py
└── tests/
    └── test_core.py
```

目录表达边界：`core.py` 放纯逻辑，`cli.py` 负责命令行与退出码，外部客户端放适配器，测试不依赖真实凭据。不要把所有模块都命名成泛化的 `utils.py`。

## CLI 是稳定接口

命令行会被人、脚本和工作流调用，应明确：

- 参数名、类型、默认值与互斥关系；
- 标准输出（stdout）是否机器可读；
- 诊断日志和错误是否写标准错误（stderr）；
- 成功与各类失败的退出码；
- 是否写文件、覆盖规则和重复执行语义。

最小 `argparse` 入口：

```python
import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成任务摘要")
    parser.add_argument("input", type=Path, help="UTF-8 JSON 输入")
    parser.add_argument("--output", type=Path, help="可选输出文件")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run(args.input, args.output)
    except TaskValidationError as exc:
        print(f"输入错误: {exc}", file=sys.stderr)
        return 2
    print(render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

把 `argv` 作为参数使 CLI 可直接测试；返回整数并在最外层 `SystemExit`，避免核心逻辑主动退出整个解释器。约定需写进 README，而非依赖读者猜测。`argparse` 的彩色帮助和错误建议是 3.14 新增能力；兼容 3.11+ 的基础代码不传这些新构造参数。

## `pyproject.toml` 管什么

`pyproject.toml` 是 Python 项目配置标准入口，可包含构建系统、项目元数据和各工具配置。它不是锁文件。

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "task-reporter"
version = "0.1.0"
requires-python = ">=3.11,<3.15"
dependencies = []

[project.scripts]
task-reporter = "task_reporter.cli:main"
```

这是说明结构的示例，不要求在 vault 中安装 `hatchling`。可分发包需要经过选择和锁定的构建后端；仅给工具保存配置的 `pyproject.toml` 可以没有 `[build-system]`。`requires-python` 是安装约束，PyPI classifier 不是约束。

## 可复现运行的证据链

可复现不是“我机器上能跑”，至少要记录：

1. 源代码与配置的版本；
2. 支持的 Python 范围和实际测试版本；
3. 直接依赖声明以及所用锁定/约束策略；
4. 创建环境和运行测试的精确命令；
5. 外部服务、模型、数据或环境变量的版本/契约；
6. 生成物来源、哈希或构建记录（风险需要时）。

使用 `pip freeze` 可以快照当前环境，但它不解释哪些是直接依赖，也不等于标准项目元数据。使用 `uv` 时，通常提交 `pyproject.toml` 与 `uv.lock`，不提交 `.venv`。截至本页获取日期，`uv sync` 默认执行 exact sync，会删除锁定环境外的包；`uv run` 默认允许保留额外包（inexact）。这类工具语义变化较快，团队应按锁定版本和当前官方文档固定命令。

## 本地运行清单

在项目根目录：

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip --version
python -m pip install -e .
python -B -m unittest discover -s .\tests -p 'test_*.py' -v
python -m task_reporter.cli --help
```

`src/` 布局下，项目根目录本身不直接把 `src` 加入导入路径；上述可编辑安装后，测试和 `python -m` 才能按包名导入。示例的构建后端会产生网络安装与本机环境写入，本知识库未执行这组安装命令；请只在独立练习目录按锁定策略运行。若只做本库的单文件任务队列，则不需要安装项目。

实际项目若要求 Python 3.14，应使用 `py -3.14` 或环境管理工具选择解释器，并在 CI 中验证。不要只凭 `python --version` 文档声称跨版本兼容。

## 交付前最小检查

- 仓库没有 `.venv`、`__pycache__`、真实 `.env`、密钥或大数据；
- 新环境能从声明重建，测试不依赖个人绝对路径；
- `--help` 与错误退出码符合文档；
- stdout 可被下游稳定解析，日志不会混入 JSON；
- 文件写入有覆盖策略，失败不会留下误认为成功的半成品；
- 构建、安装和运行是三种不同动作，说明中没有混淆。

## 练习

1. 把一个单文件脚本重构为 `core.py` 与 `cli.py`，核心函数不读取 `sys.argv`。
2. 为 CLI 的成功、输入错误和未知参数断言退出码、stdout 与 stderr。
3. 写一个最小 `pyproject.toml`，逐项解释 `[build-system]`、`[project]` 和 `[project.scripts]`。
4. 在全新临时目录重建环境，记录所有命令；指出仍未固定的外部状态。

## 自测

- [ ] 能解释为何先保持单文件、何时再采用 `src/` 布局。
- [ ] 能设计机器可用的 stdout、stderr 与退出码。
- [ ] 能区分 `pyproject.toml`、requirements 文件和锁文件。
- [ ] 能列出复现一次运行所需的代码外证据。
- [ ] 不会把“语法可解析”误称为依赖、集成和版本都已验证。

## 相关概念与下一步

- 前置：[[Python基础/Agent工程路线/03-并发与交付/08-异步并发取消与限流|异步、并发、取消与限流]]。
- 下一节：[[Python基础/Agent工程路线/03-并发与交付/10-Agent工具函数设计|Agent 工具函数设计]]。
- 版本协作见 [[Git/00-目录|Git]]；自动部署与环境治理见 [[MLOps/00-目录|MLOps]] 和 [[LLMOps/00-目录|LLMOps]]。

## 参考资料

获取日期：**2026-07-14**。

- [Python：`argparse`](https://docs.python.org/3.14/library/argparse.html)
- [PyPA：编写 `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [PyPA：项目元数据规范](https://packaging.python.org/en/latest/specifications/pyproject-toml/)
- [uv：项目与锁定](https://docs.astral.sh/uv/guides/projects/)
