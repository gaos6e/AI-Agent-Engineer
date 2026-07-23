---
title: "Python 解析、序列化与严格模式"
tags:
  - ai-agent-engineer
  - JSON
  - Python
aliases:
  - Python json 标准库
  - JSON 严格解析
source_checked: 2026-07-22
lang: zh-CN
translation_key: JSON/02-Python解析、序列化与严格模式.md
translation_route: en/json/02-python-parsing-serialization-and-strict-mode
translation_default_route: zh-CN/JSON/02-Python解析、序列化与严格模式
---

# Python 解析、序列化与严格模式

## 本节目标

正确选择 `load/loads/dump/dumps`，用 UTF-8 读写文件，保留解析错误位置；理解 Python 标准库默认接受重复键和非标准数字等扩展，并能按接口契约显式收紧输入与输出。

## 先准备最小环境

标准库 `json` 无需安装。综合项目额外使用 JSON Schema 验证器，应先建立隔离环境，再安装固定依赖。以下代码块从同时包含 `docs/` 与 `.website/` 的项目根目录运行：

```powershell
Push-Location -LiteralPath 'docs\JSON'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\examples\requirements.txt
Pop-Location
```

不要把 `.venv` 加入仓库。本库验证使用 Python 3.11.9；代码也兼容 `jsonschema` 4.26.0 支持的 Python 3.10+。使用其他版本时重新运行测试。

## 四个函数按“字符串还是文件对象”区分

| 方向 | 字符串/字节 | 已打开的文件对象 |
| --- | --- | --- |
| JSON → Python | `json.loads(text)` | `json.load(file)` |
| Python → JSON | `json.dumps(value)` | `json.dump(value, file)` |

`s` 可以记作 string。`load` 和 `dump` 接收具有 `read` 或 `write` 的文件对象，不直接接收 `Path`。

```python
import json

text = '{"name": "agent", "max_steps": 5}'
value = json.loads(text)
round_trip = json.dumps(value, ensure_ascii=False)

assert value["name"] == "agent"
assert json.loads(round_trip) == value
```

这里的 `assert` 只是讲解等价关系，不应替代项目测试；`python -O` 会移除裸断言。

## 捕获语法错误并保留位置

```python
import json

text = '{\n  "name": "agent",\n}'

try:
    config = json.loads(text)
except json.JSONDecodeError as error:
    print(f"invalid JSON at line {error.lineno}, column {error.colno}")
else:
    print(config)
```

生产日志不应顺手打印完整 `text`：载荷可能含 token、个人信息或提示注入文本。推荐记录稳定错误码、安全路径、行列号、request ID 和数据来源，而不是整段值。

## UTF-8 文件读写

```python
import json
from pathlib import Path

path = Path("agent_config.json")
data = {"name": "会议助理", "enabled": True}

with path.open("w", encoding="utf-8", newline="\n") as file:
    json.dump(
        data,
        file,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    )
    file.write("\n")

with path.open("r", encoding="utf-8") as file:
    loaded = json.load(file)
```

- `encoding="utf-8"` 不依赖 Windows 当前代码页；
- `ensure_ascii=False` 让中文保持可读，不改变逻辑字符串；
- `allow_nan=False` 阻止编码出 RFC 8259 禁止的 `NaN`/`Infinity`；
- `indent=2` 面向人读，网络 payload 可用紧凑格式；
- `sort_keys=True` 可稳定普通测试输出，但不是密码学 canonicalization；
- 末尾 LF 便于 diff，不属于 JSON 值。

## Python 默认行为比 RFC 8259 宽

截至 Python 3.14.6 官方文档，标准库默认有这些兼容行为：

```python
import json
import math

duplicate = json.loads('{"role":"reader","role":"admin"}')
non_standard = json.loads("NaN")

assert duplicate == {"role": "admin"}
assert math.isnan(non_standard)
```

这不表示重复键和 `NaN` 成了标准 JSON。解析层若先静默丢掉第一个键，Schema 已经无法发现冲突；权限字段重复时尤其危险。

### 用 hook 拒绝重复键和非标准常量

```python
import json
from typing import Any


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate object member")
        result[key] = value
    return result


def reject_constant(_: str) -> None:
    raise ValueError("non-standard numeric literal")


value = json.loads(
    '{"enabled": true}',
    object_pairs_hook=unique_object,
    parse_constant=reject_constant,
)
```

这仍不是完整安全边界：`1e9999` 可被默认 `float` 转成正无穷；孤立 UTF-16 surrogate、超深嵌套、超长数组和大文件也需要额外检查。综合项目的 `strict_json.py` 把这些规则集中到一个可测试入口。

## 数值精度与 `Decimal`

```python
import json
from decimal import Decimal

data = json.loads('{"price": 0.1}', parse_float=Decimal)
assert data["price"] == Decimal("0.1")
```

`Decimal` 只改变本端解析结果。它不是 JSON 原生类型；写回时仍要约定以字符串、最小货币单位整数或其他明确结构传输。跨 JavaScript 系统的超大整数 ID 通常也应使用字符串契约。

## 非原生 Python 类型要显式编码

`datetime`、`Decimal`、UUID、`Path`、`set` 和自定义类都不是 JSON 原生值。不要写一个“见到任何对象就 `str(obj)`”的兜底编码器，否则类型错误会静默变成字符串。先为字段定义契约，再写窄转换：

```python
from datetime import datetime, timezone
import json

payload = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "tags": sorted({"json", "agent"}),
}
text = json.dumps(payload, ensure_ascii=False, allow_nan=False)
```

时间字符串还要规定时区、精度和解析规则；“能序列化”不代表双方理解一致。

## 双重编码

```python
import json

payload = {"name": "agent"}
once = json.dumps(payload)
twice = json.dumps(once)

print(once)   # {"name": "agent"}
print(twice)  # "{\"name\": \"agent\"}"
```

第二次得到的是 JSON 字符串值，不是对象。HTTP 客户端若提供 `json=payload`，通常应传 Python 对象；若使用 `data=`，要自行处理编码与媒体类型，具体以客户端文档为准。

## 命令行快速检查

Python 3.11 可使用：

```powershell
Push-Location -LiteralPath 'docs\JSON'
python -m json.tool .\examples\agent_config.json
Pop-Location
```

Python 3.14 增加了 `python -m json` 入口，但为了兼容本项目环境，课程命令继续使用 `json.tool`。它能检查语法与美化输出，不能替代 Schema 或业务验证。

## 常见错误与排查

- 用 `eval` 解析 JSON：不可信文本会进入代码执行边界；只用数据解析器。
- 只在输出端设置 `allow_nan=False`：输入端还需 `parse_constant` 和解析后有限性检查。
- 用 `skipkeys=True` 隐藏非字符串键：这会丢数据；契约应显式拒绝。
- 对同一文件连续调用多次 `json.dump`：JSON 没有记录 framing，结果不是一个合法单文档。
- 捕获 `Exception` 后只打印“解析失败”：保留安全的错误类型、行列与处理动作。

## 练习

1. 用 `loads` 解析一段文本，用 `load` 读取同内容文件，断言结果相同。
2. 分别输入尾逗号、空文本和未闭合字符串，记录 `lineno` 与 `colno`。
3. 用 `allow_nan=False` 编码 `float("nan")`，解释异常来自哪一层。
4. 实现上面的重复键 hook，并对顶层和嵌套对象各写一个失败测试。
5. 解释为何 `json.loads(json.dumps({1: "x"}))` 不等于原字典。

## 自测

1. `load` 与 `loads` 的输入差别是什么？
2. `ensure_ascii=False` 是否改变字符串逻辑内容？
3. `sort_keys=True` 是否足以支撑数字签名？
4. 为什么 Schema 无法补救解析阶段已丢失的重复键？
5. `parse_constant` 能否单独拒绝 `1e9999` 产生的无穷值？

## 小结与下一步

标准库提供机制，应用负责选择 profile。下一节把严格边界扩展到 Unicode、数字范围、对象顺序和资源耗尽：[[JSON/03-互操作性、Unicode与数字边界|互操作性、Unicode 与数字边界]]。返回 [[JSON/00-目录|JSON 学习目录]]。

## 参考资料

资料复核日期：**2026-07-22**。

- [Python 3.14 `json`：Encoder and Decoder、Standard Compliance](https://docs.python.org/3.14/library/json.html)
- [Python `decimal`](https://docs.python.org/3/library/decimal.html)
- [RFC 8259：Parsers、Generators、Security Considerations](https://www.rfc-editor.org/rfc/rfc8259.html)
