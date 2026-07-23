---
title: "Python Agent 工程最小实践"
tags:
  - ai-agent-engineer
  - Python
  - project
aliases:
  - Python 任务队列项目
  - Agent 工程 Python 实践
lang: zh-CN
translation_key: Python基础/00-Agent工程实践.md
translation_route: en/python-fundamentals/00-python-agent-engineering-minimum-practice
translation_default_route: zh-CN/Python基础/00-Agent工程实践
---

# Python Agent 工程最小实践

## 项目目标

把一组 JSON 任务读入 Python，拒绝非法记录，统计状态并生成 JSON 报告。它不调用模型，却练习了 Agent 工具最重要的工程边界：输入契约、纯函数、明确错误、确定性输出和自动化测试。

配套文件：

```text
examples/
├── tasks.json
├── task_queue.py
└── test_task_queue.py
```

## 输入与输出契约

每个任务必须包含：

- `id`：非空字符串，且在文件内唯一；
- `title`：非空字符串；
- `status`：只能是 `pending`、`running`、`done` 或 `failed`。

输出不是原数据的复制，而是一个可供下一步消费的报告：

```json
{
  "total": 3,
  "by_status": {
    "done": 1,
    "pending": 2
  },
  "unfinished_ids": ["task-002", "task-003"]
}
```

未知字段、缺失字段、重复 ID 和非法状态都应报错。不要“尽量猜”；在工程边界上，显式失败比静默修正更容易追踪。

## 从零实现步骤

1. 先写 `Task` 数据类，明确三个字段及其类型。
2. 写 `parse_task(value)`，只负责把一个不可信对象变成 `Task` 或抛出 `TaskValidationError`。
3. 写 `load_tasks(path)`：读取 UTF-8、解析 JSON、确认根节点是数组、检查 ID 唯一。
4. 写 `summarize(tasks)`：只根据已校验对象产生统计，不读写文件。
5. 写 `write_report(report, path)`，明确何时发生文件副作用。
6. 写命令行入口，把输入、输出路径作为参数，而不是硬编码本机绝对路径。

这种拆分让“解析”“业务计算”“I/O”分别测试。未来把任务来源换成 API、数据库或模型工具时，核心统计函数仍可复用。

## 运行方式

从 vault 根目录运行：

```powershell
python -B '.\Knowledge\AI Agent Engineer\docs\Python基础\examples\task_queue.py' `
  '.\Knowledge\AI Agent Engineer\docs\Python基础\examples\tasks.json'
```

不指定 `--output` 时只向标准输出写 JSON，不创建文件。要测试文件输出：

```powershell
python -B '.\Knowledge\AI Agent Engineer\docs\Python基础\examples\task_queue.py' `
  '.\Knowledge\AI Agent Engineer\docs\Python基础\examples\tasks.json' `
  --output "$env:TEMP\task-report.json"
```

运行测试：

```powershell
python -B -m unittest discover `
  -s '.\Knowledge\AI Agent Engineer\docs\Python基础\examples' `
  -p 'test_*.py' `
  -v
```

`-B` 禁止生成 `.pyc`；测试使用临时目录，不会在 vault 中留下报告。

## 必做练习

1. 删除一条任务的 `title`，确认程序拒绝并指出位置。
2. 制造重复 `id`，为该失败补一个单元测试。
3. 新增可选 `owner` 字段：明确 `null`、缺失和空字符串分别表示什么。
4. 新增 `cancelled` 状态，同时修改校验、统计和测试；不要只改其中一处。
5. 解释：如果这个程序将来变成 Agent 工具，哪些错误可返回给模型，哪些必须中止并交给人工？

## 常见错误与排查

- **直接对原字典做业务计算**：未校验值会把错误拖到更远的位置。先转换成受约束对象。
- **`except Exception: pass`**：会让坏数据像成功一样继续流动。只捕获能处理的异常。
- **函数同时读文件、联网、计算、写文件**：测试困难且副作用不清。把 I/O 放在边界。
- **测试只看“没有报错”**：还要断言输出值和错误类型。
- **把路径写死为本机目录**：改用参数与 `pathlib.Path`。

## 自测与掌握检查

- [ ] 能解释数据类、字典和 JSON 对象的区别。
- [ ] 能说出 `parse_task` 为什么比在主函数里连续取字段更易测试。
- [ ] 能预测空数组、根节点为对象、重复 ID 和非法状态的结果。
- [ ] 能证明重复运行同一输入会产生相同报告。
- [ ] 能指出程序的唯一持久写入发生在哪里。
- [ ] 能在不看成品的情况下重写一个等价实现，并让全部测试通过。

完成后回到 [[Python基础/00-目录|Python基础目录]]，再进入 API 与 JSON。

## 参考资料

获取日期：**2026-07-13**。

- [Python `json` 标准库](https://docs.python.org/3/library/json.html)
- [Python `dataclasses`](https://docs.python.org/3/library/dataclasses.html)
- [Python `pathlib`](https://docs.python.org/3/library/pathlib.html)
- [Python `unittest`](https://docs.python.org/3/library/unittest.html)

