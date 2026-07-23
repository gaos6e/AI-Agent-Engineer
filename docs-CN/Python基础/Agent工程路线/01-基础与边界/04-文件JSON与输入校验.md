---
title: "文件、JSON 与输入校验"
tags: [ ai-agent-engineer, Python, JSON, I-O ]
aliases: [ Python 文件边界, Python JSON 校验 ]
lang: zh-CN
translation_key: Python基础/Agent工程路线/01-基础与边界/04-文件JSON与输入校验.md
translation_route: en/python-fundamentals/engineering-route/01-foundations-and-boundaries/04-files-json-and-input-validation
translation_default_route: zh-CN/Python基础/Agent工程路线/01-基础与边界/04-文件JSON与输入校验
---

# 文件、JSON 与输入校验

## 本节目标

学完本节，你应能用 `pathlib` 与显式 UTF-8 读写文件，区分 JSON 语法、数据类型和业务契约错误，并把不可信 `object` 转换为已校验对象。

## 文件路径不是普通字符串

`pathlib.Path` 提供跨平台的路径组合和文件操作：

```python
from pathlib import Path

base = Path("examples")
input_path = base / "tasks.json"
text = input_path.read_text(encoding="utf-8")
```

不要用字符串拼接 `"examples/" + name`。外部提供的路径还可能包含绝对路径或 `..`；若应用只允许某个工作目录，应在解析后验证目标仍位于允许根目录，并拒绝符号链接/重解析点带来的越界风险，而不是只检查字符串前缀。

## 文本必须明确编码

```python
text = path.read_text(encoding="utf-8")
path.write_text(rendered + "\n", encoding="utf-8")
```

依赖操作系统默认编码会导致“我这里能读、服务器乱码”。遇到终端乱码时先区分文件编码、终端输出编码和字体问题，不要直接重写文件。

## 三层错误要分开

```text
文件层：不存在、无权限、太大、读取中断
JSON 语法层：括号、逗号、引号或编码后的文本非法
业务契约层：根节点不对、字段缺失、类型错误、状态不允许
```

```python
import json


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InputError(f"文件不存在: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(
            f"JSON 格式错误: line={exc.lineno}, column={exc.colno}"
        ) from exc
```

只转换你能解释的异常。权限错误、磁盘故障等若没有适当策略，应继续向上抛或映射为不同错误，不能都伪装成“文件不存在”。

## JSON 类型与 Python 类型

| JSON | Python `json.loads` |
| --- | --- |
| object | `dict` |
| array | `list` |
| string | `str` |
| number | `int` 或 `float` |
| true/false | `True`/`False` |
| null | `None` |

布尔值在 Python 中是整数的子类，因此校验“必须为整数”时如果不允许布尔值，要显式排除 `bool`。JSON 数字也没有自动保证金额精度、范围或单位。

## 白名单校验

```python
REQUIRED = {"id", "title", "status"}


def parse_task(value: object, index: int) -> Task:
    if not isinstance(value, dict):
        raise TaskValidationError(f"第 {index} 项必须是对象")

    keys = set(value)
    missing = REQUIRED - keys
    unknown = keys - REQUIRED
    if missing:
        raise TaskValidationError(f"第 {index} 项缺少字段: {sorted(missing)}")
    if unknown:
        raise TaskValidationError(f"第 {index} 项包含未知字段: {sorted(unknown)}")
    ...
```

未知字段是拒绝、忽略还是保留，取决于兼容性策略。工具写操作通常更适合严格白名单；面向长期兼容的读取 API 可能允许未知字段。无论选择哪种，都要写进契约和测试。

不要静默把字符串 `"3"` 转整数、把空字符串转 `None`，除非业务规则明确允许且转换可追溯。自动纠错会隐藏上游质量问题。

## 大小、深度和资源限制

合法 JSON 仍可能非常大或深。读取前后可检查：

- 文件大小上限；
- 记录数量与字符串长度；
- 允许的嵌套深度；
- 单条字段范围；
- 处理总时限和内存预算。

标准库 `json.load` 不提供流式大数据处理保证。本库只处理小型教学文件；大文件应选择适合的流式格式/解析器，并在数据工程知识库中设计。

## 确定性输出与原子写入

教学报告可固定键顺序、缩进和换行：

```python
rendered = json.dumps(
    report,
    ensure_ascii=False,
    indent=2,
    sort_keys=True,
    allow_nan=False,
)
path.write_text(rendered + "\n", encoding="utf-8")
```

标准库默认允许输出 `NaN`/`Infinity` 等不属于严格 JSON 的常量；跨系统契约可用 `allow_nan=False` 让这类值立即失败。连续向同一个文件多次 `json.dump()` 也不会自动形成合法的“多记录 JSON”，需要数组、JSON Lines 等明确 framing。

若写入失败不能接受半文件，可先在同一文件系统写临时文件，刷新后用原子替换；同时决定覆盖策略、权限、备份和崩溃恢复。不要默认所有文件系统都提供相同原子语义。

## 常见错误

- `except Exception` 后返回空对象；
- 只验证 JSON 能解析，不验证业务字段；
- 将缺失、`null` 和空字符串混为一谈；
- 错误信息包含完整敏感输入；
- 接受用户路径后直接读写任意位置；
- 写文件前不说明覆盖、重复执行和中断行为。

## 练习

为任务列表补齐：空文件、无效 JSON、根节点为对象、未知字段、重复 ID、非法状态、超长标题和 1,001 条记录测试。为每类错误定义稳定错误类型与可安全展示的信息。

## 自测

1. 文件错误、JSON 语法错误和业务错误为什么要分开？
2. 类型提示能替代解析时的 `isinstance` 吗？
3. 缺失字段、`null` 与空字符串有什么区别？
4. 路径安全为什么不能只做字符串前缀检查？
5. JSON 合法为什么仍可能消耗过多资源？

## 相关概念与下一步

- JSON 语义与 Schema 进入 [[JSON/00-目录|JSON]]；数据批处理进入 [[数据清洗/00-目录|数据清洗]]。
- 下一节 [[Python基础/Agent工程路线/02-可靠性与测试/05-异常超时重试与资源管理|异常、超时、重试与资源管理]] 处理边界失败后的控制流。

## 参考资料

获取日期：**2026-07-14**。

- [Python `pathlib`](https://docs.python.org/3.14/library/pathlib.html)
- [Python `json`](https://docs.python.org/3.14/library/json.html)
- [Python 异常](https://docs.python.org/3.14/tutorial/errors.html)
