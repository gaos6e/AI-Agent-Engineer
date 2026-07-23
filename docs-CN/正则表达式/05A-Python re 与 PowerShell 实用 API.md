---
title: "正则表达式：Python re 与 PowerShell 实用 API"
tags:
  - AI-Agent-Engineer
  - 正则表达式
  - Python
  - PowerShell
aliases:
  - Python re 实用 API
  - PowerShell 正则实用 API
source_checked: 2026-07-14
source_baseline:
  - Python 3.14.6 re documentation
  - PowerShell 7.6 regular-expression documentation
related: "[[正则表达式/00-目录]]"
lang: zh-CN
translation_key: 正则表达式/05A-Python re 与 PowerShell 实用 API.md
translation_route: en/regular-expressions/05a-python-re-and-powershell-practical-apis
translation_default_route: zh-CN/正则表达式/05A-Python-re-与-PowerShell-实用-API
---

# 正则表达式：Python re 与 PowerShell 实用 API

## 本节目标

把模式放进真实程序：能在 Python 中选择 `search`、`fullmatch`、`finditer` 与 `sub`，并能在 PowerShell 中正确使用 `-match`、`$Matches`、`Select-String` 和 `-replace`。所有示例只依赖 Python 标准库与 PowerShell 自带的 .NET 引擎。

## Python：先使用 raw string

```python
import re

RUN_ID = re.compile(r"[A-Za-z0-9_-]{3,32}")
assert RUN_ID.fullmatch("agent_01") is not None
assert RUN_ID.fullmatch("bad id") is None
```

`r"..."` 让反斜杠较少受 Python 字符串语法干扰；它不会关闭正则语法。raw string 也不能以奇数个反斜杠结束，因此它不是所有字符串问题的万能开关。

`re.compile` 把模式与标志放在一个可复用对象中。Python 也会缓存近期模块级模式，所以“为了性能必须手动编译”不是绝对规则；工程上更重要的价值是命名、集中配置和测试。

## Python：根据任务选 API

| API | 检查范围 | 典型用途 |
| --- | --- | --- |
| `search` | 从任意位置寻找第一个命中 | 判断一行是否包含目标模式。 |
| `match` | 只从字符串开头尝试，但允许尾部剩余 | 解析带固定前缀的文本；不要把它误当完整校验。 |
| `fullmatch` | 整个字符串必须匹配 | 验证一个完整字段或一条固定格式记录。 |
| `finditer` | 迭代所有不重叠命中并返回 `Match` | 需要文本、分组、起止位置时优先。 |
| `findall` | 返回所有不重叠结果，但返回形状受捕获组影响 | 简单提取；复杂任务要小心组导致的返回值变化。 |
| `sub` / `subn` | 替换所有或限定次数的命中 | 脱敏、规范化；`subn` 额外返回替换次数。 |

```python
import re

line = "INFO run_id=r1 parent=r0"
run_id = re.compile(r"\brun_id=(?P<value>[A-Za-z0-9_-]+)\b")

first = run_id.search(line)
assert first is not None
assert first.group("value") == "r1"
assert first.span("value") == (12, 14)

values = [match.group("value") for match in run_id.finditer(line)]
assert values == ["r1"]
```

不要只写 `if match:` 后就假设某个组必定存在。可选分支可能让 `group(...)` 返回 `None`；为重要输出写类型和边界测试。

## 命名组与 `groupdict`

```python
import re

pattern = re.compile(
    r"level=(?P<level>INFO|WARNING|ERROR)\s+"
    r"latency_ms=(?P<latency_ms>[0-9]+)"
)

match = pattern.fullmatch("level=ERROR latency_ms=2200")
assert match is not None
fields = match.groupdict()
record = {
    "level": fields["level"],
    "latency_ms": int(fields["latency_ms"]),
}
assert record == {"level": "ERROR", "latency_ms": 2200}
```

正则捕获的是文本；数值、日期和枚举仍应在捕获后转换并做业务检查。`[0-9]` 明确表示 ASCII 数字，避免 Python 默认 `\d` 接受其他 Unicode 十进制数字。

## 标志与可读模式

```python
import re

pattern = re.compile(
    r"""
    ^
    (?P<name>[A-Za-z][A-Za-z0-9_-]{2,31})
    $
    """,
    flags=re.VERBOSE | re.ASCII,
)

assert pattern.fullmatch("agent_01") is not None
```

- `re.IGNORECASE` / `re.I`：忽略大小写；Unicode 大小写折叠可能超出 ASCII 直觉。
- `re.MULTILINE` / `re.M`：改变 `^` 和 `$` 的行边界语义。
- `re.DOTALL` / `re.S`：让点号匹配换行。
- `re.VERBOSE` / `re.X`：允许空白与注释；字符类内和被转义的空白仍有特殊规则。
- `re.ASCII` / `re.A`：让 `\w`、`\d`、`\s`、`\b` 等采用 ASCII 语义；只在契约确实要求 ASCII 时使用。

## 安全拼入字面文本

用户输入若只是要按原样搜索，必须先转义，而不是把它当模式：

```python
import re

literal = "agent.v2+beta"
pattern = re.compile(re.escape(literal))
assert pattern.search("deploy agent.v2+beta now") is not None
assert pattern.search("deploy agentXv22beta now") is None
```

`re.escape` 用于 **模式中的字面片段**。替换字符串有另一套规则；如果替换内容来自变量，优先使用函数替换，避免对反斜杠和组引用产生误解：

```python
import re

replacement = r"archive\1"
result = re.sub(r"TOKEN", lambda _: replacement, "TOKEN")
assert result == replacement
```

## PowerShell：匹配与 `$Matches`

PowerShell 使用 .NET 正则引擎。`-match` 默认不区分大小写，`-cmatch` 明确区分大小写：

```powershell
$line = 'level=ERROR run_id=r2'
$pattern = '^level=(?<level>INFO|WARNING|ERROR) run_id=(?<runId>[A-Za-z0-9_-]+)$'

if ($line -cmatch $pattern) {
    [pscustomobject]@{
        Level = $Matches.level
        RunId = $Matches.runId
    }
}
```

标量输入匹配成功时，`$Matches[0]` 保存整体命中，命名键保存捕获组。下一次成功的标量匹配会覆盖它；失败匹配不会清空旧值，因此只能在当前成功分支内读取。集合放在 `-match` 左侧时会返回匹配元素，而不是为每个元素建立可依赖的 `$Matches`。需要逐条捕获时显式循环：

```powershell
$pattern = '^run_id=(?<runId>[A-Za-z0-9_-]+)$'
$ids = foreach ($line in 'run_id=r1', 'invalid', 'run_id=r2') {
    if ($line -cmatch $pattern) {
        $Matches.runId
    }
}

if (@($ids).Count -ne 2) {
    throw 'unexpected match count'
}
```

## PowerShell：搜索文件与替换

```powershell
$path = Join-Path $PWD 'examples\sample.txt'
$errors = Select-String -LiteralPath $path -Pattern 'level=ERROR' -AllMatches

if (@($errors).Count -ne 1) {
    throw 'expected exactly one ERROR line'
}

$normalized = 'name   age' -replace '\s+', ' '
if ($normalized -cne 'name age') {
    throw 'replacement failed'
}
```

`Select-String` 返回带文件、行号和匹配信息的对象，适合调查文件；`-replace` 默认替换所有命中。替换字符串中的 `$1`、`${name}` 是 .NET 捕获引用，若放在 PowerShell 双引号字符串里还可能先触发变量展开，因此固定替换模板通常使用单引号。

字面输入使用 `[regex]::Escape`：

```powershell
$literal = 'agent.v2+beta'
$escaped = [regex]::Escape($literal)
if ('use agent.v2+beta now' -cnotmatch $escaped) {
    throw 'literal search failed'
}
```

## 常见错误与排查

- 在线测试器未选择相同引擎、版本和标志。
- 把 Python `match` 当成完整匹配；字段校验应优先 `fullmatch`。
- 直接使用 `findall`，加入一个捕获组后结果会变成该组文本，加入多个捕获组后通常变成元组；调用方因此悄然失去原来的整体命中形状。
- Python 用普通字符串写反斜杠模式，或 PowerShell 用双引号模式误展开 `$`。
- 忘记 PowerShell `-match` 默认忽略大小写。
- 读取旧的 `$Matches`，却没有把读取放在当前成功匹配的分支中。
- 将用户字面输入直接拼入模式，导致模式注入或性能风险。

## 练习

1. 用 Python `finditer` 提取 `run_id=r1 run_id=r2` 中的两个值和起止位置。
2. 用 `fullmatch` 验证 3～32 位 ASCII run ID，并测试空值、空格、中文、33 位输入。
3. 用 PowerShell `Select-String` 找出 `examples/sample.txt` 中的错误级别行，并输出行号。
4. 分别用 `re.escape` 与 `[regex]::Escape` 搜索字面字符串 `a+b.c`。
5. 将一段多空格文本规范为单空格，断言替换次数或最终结果。

## 自测

- `search`、`match` 与 `fullmatch` 的检查范围分别是什么？
- 为什么复杂提取通常优先 `finditer` 而不是 `findall`？
- `re.escape` 能否不加区分地用于替换字符串？
- PowerShell 中 `-match` 与 `-cmatch` 有何差异？
- `$Matches` 为什么必须紧邻成功的标量匹配读取？

上一节：[[正则表达式/05-标志与替换|标志与替换]]｜下一节：[[正则表达式/06-性能与调试|性能与调试]]。

## 参考资料

核验日期：**2026-07-14**。

- [Python 标准库：re](https://docs.python.org/3/library/re.html)
- [Python Regular Expression HOWTO](https://docs.python.org/3/howto/regex.html)
- [Microsoft Learn：PowerShell Regular Expressions](https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_regular_expressions)
- [Microsoft Learn：PowerShell Comparison Operators](https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_comparison_operators)
- [Microsoft Learn：.NET Regular Expressions](https://learn.microsoft.com/dotnet/standard/base-types/regular-expressions)
