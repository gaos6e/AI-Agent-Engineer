---
title: Python日志解析项目与自测
tags:
  - AI-Agent-Engineer
  - 正则表达式
  - 综合实践
aliases:
  - Regex 日志项目
source_checked: 2026-07-14
source_baseline:
  - Python 3.14.6 re documentation
---

# Python 日志解析项目与自测

## 项目目标

读取一份虚构 Agent 运行日志，把时间、级别、run ID、延迟和消息提取为字典，并明确拒绝格式不符的行。项目只用 Python 标准库，不连接真实日志系统。

## 输入契约

每行格式：

```text
2026-07-13T10:00:01Z level=INFO run_id=r1 latency_ms=120 message="completed"
```

约束：

- 时间采用固定的 UTC `Z` 形式和 ASCII 数字；本项目只检查形状，不证明日期真实存在。
- `level` 只允许 `INFO`、`WARNING`、`ERROR`。
- `run_id` 长度为 1～64，只允许 ASCII 字母、数字、下划线和连字符。
- `latency_ms` 只允许 ASCII 数字，转换后必须不大于 `300000`；这个上限是教学契约，不代表所有系统的通用阈值。
- `message` 不能含双引号或换行；真实系统更适合结构化日志而不是不断扩展这一正则。

## 为什么使用完整匹配

若只用 `search`，一行前后多出的恶意或损坏文本可能被忽略。项目使用 `fullmatch`，要求整行符合契约。`^`/`$` 与多行模式在不同场景有细节差异，完整记录验证优先使用 `fullmatch` 表意。

## 可读模式

脚本使用 `re.VERBOSE` 将模式分行并添加注释。Python 模式写成 raw string `r"..."`，减少 Python 字符串层先处理反斜杠的问题。模式可读不代表性能自动安全，仍需边界测试。

## 运行

```powershell
Set-Location 'X:\path\to\your-vault\Knowledge\AI Agent Engineer\docs\正则表达式'
python .\examples\log_parser.py
python -m unittest discover -s .\examples -p 'test_*.py' -v
```

预期：

```text
parsed=3 errors=1 max_latency_ms=2200
line 3: invalid log format
all checks passed
```

`sample.txt` 故意包含一条格式错误记录。脚本报告行号；演示统计使用逐行捕获错误的方式，不能在生产中无记录地丢弃失败行。单元测试应显示 9 个测试全部通过。

实现入口：[[正则表达式/examples/log_parser.py|log_parser.py]]｜测试入口：[[正则表达式/examples/test_log_parser.py|test_log_parser.py]]｜样例：[[正则表达式/examples/sample.txt|sample.txt]]。

> [!success] 本轮实测
> 2026-07-14 在 Python 3.11.9 以普通模式和 `-O` 模式运行脚本，并运行 9 个 `unittest` 与两份 Python 文件的语法编译，结果全部通过；测试生成的 `__pycache__` 已清理。此结果证明本地固定样例与测试契约，不代表所有第三方正则引擎的兼容性。

## 代码阅读顺序

1. `LOG_PATTERN` 的命名组决定输出字段。
2. `parse_line` 用 `fullmatch`，失败时抛出带行号的异常。
3. 数字捕获后再转换为 `int`，并检查范围。
4. `parse_file` 逐行读取 UTF-8，分别保存成功结果和错误。
5. `main` 对固定样例做结果校验，失败时返回非零退出状态；它不依赖可被 `python -O` 移除的 `assert`。
6. `test_log_parser.py` 独立覆盖结构、Unicode 数字、数值与 run ID 边界、长消息、文件行号和字面转义。

## 字面文本必须转义

若用户要搜索字面字符串 `agent.v2+beta`，不能直接拼进正则，因为 `.` 和 `+` 有特殊意义：

```python
import re

literal = "agent.v2+beta"
pattern = re.compile(re.escape(literal))
assert pattern.search("use agent.v2+beta now")
```

`re.escape` 用于模式中的字面部分，不应不加区分地用于替换字符串。

## 扩展任务

1. 加入 `DEBUG` 级别，并补正例、反例和统计断言。
2. 将错误分为结构错误与数值范围错误，保持准确行号。
3. 允许消息包含转义双引号；先写清输入契约，再修改模式和测试。
4. 为 run ID 增加产品前缀或大小写规则，先补正反例再修改模式。
5. 在受控测试中加入近似失败长输入并计时，记录环境、长度与结果，不在生产进程放大危险模式。
6. 将日志改为每行一个 JSON 对象，比较标准解析器与正则的维护成本。

## 何时停止增加正则复杂度

出现嵌套结构、任意转义、跨行语法、递归或需要精确错误恢复时，优先使用对应解析器。JSON、HTML、编程语言和自然语言都不应靠不断增长的一条正则完整解析。

## 自测

1. 字符类中的 `^` 与模式开头的 `^` 有何不同？
2. 贪婪与非贪婪是否等同“性能差”与“性能好”？
3. 捕获组、非捕获组和命名组如何选择？
4. 先行/后行断言为什么不消耗匹配文本？
5. Python raw string 解决的是哪一层转义？
6. `search`、`match`、`fullmatch` 分别适合什么任务？
7. 为什么不能直接把用户输入拼进模式？
8. 灾难性回溯通常与什么结构有关？
9. 同一模式为何可能在 JavaScript、Python 与 grep 中行为不同？
10. 正则验证邮箱形状为什么不能证明邮箱真实存在？

## 项目验收

- [ ] 脚本和 `unittest` 在当前 Python 3 环境运行通过。
- [ ] 能解释模式每个命名组与边界。
- [ ] 错误行不会静默丢弃，并带有准确行号。
- [ ] 至少新增两个正例、两个反例和一个长输入测试。
- [ ] 用户字面输入经过 `re.escape`。
- [ ] 能说明何时改用 JSON 或专用解析器。

完成后回到 [[正则表达式/00-目录|正则表达式目录]]。

## 参考资料

核验日期：**2026-07-14**。

- [Python 标准库：re](https://docs.python.org/3/library/re.html)
- [Python Regular Expression HOWTO](https://docs.python.org/3/howto/regex.html)
- [GNU grep：Regular Expressions](https://www.gnu.org/software/grep/manual/html_node/Regular-Expressions.html)
