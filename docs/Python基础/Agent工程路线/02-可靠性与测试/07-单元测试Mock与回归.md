---
title: 单元测试、Mock 与回归
tags: [ai-agent-engineer, Python, testing]
aliases: [Python 单元测试, Python Mock]
---

# 单元测试、Mock 与回归

## 本节目标

用快速、确定、可重复的测试证明核心逻辑和失败契约；在文件、时钟、网络客户端等外部边界使用替身，而不是把实现细节全部 mock 掉。

## 测试要回答什么

一个有价值的测试至少固定一条可观察契约：

```text
给定什么输入/状态 → 执行什么公开行为 → 得到什么输出/副作用/错误
```

常见层级：

| 层级 | 关注点 | 示例 |
| --- | --- | --- |
| 单元测试 | 一个函数/模块的逻辑与边界 | 非法任务状态被拒绝 |
| 集成测试 | 两个真实组件能否协作 | 真实文件读写后可解析 |
| 端到端测试 | 用户路径是否完成 | CLI 输入文件后生成报告 |
| 回归测试 | 已发生缺陷不再出现 | 重复 ID 曾被漏检 |

Mock 测试不等于集成测试。测试组合应让大部分核心逻辑无需联网即可运行，再用少量受控集成测试检查真实 SDK、服务或文件格式。

## Arrange—Act—Assert

```python
import unittest


class RetryTests(unittest.TestCase):
    def test_succeeds_after_one_transient_failure(self) -> None:
        # Arrange
        outcomes = iter([TemporaryDependencyFailure(), "ok"])
        delays: list[float] = []

        def operation() -> str:
            value = next(outcomes)
            if isinstance(value, Exception):
                raise value
            return value

        # Act
        result = retry_transient(
            operation, attempts=2, sleep=delays.append, base_delay=0.1
        )

        # Assert
        self.assertEqual(result, "ok")
        self.assertEqual(delays, [0.1])
```

测试名应描述行为。断言只检查契约相关结果，失败消息才容易定位。

## 边界值与失败路径

对一个 JSON 工具，至少覆盖：

- 最小合法输入和典型合法输入；
- 空输入、上限值、刚好超过上限；
- 根类型错误、缺字段、未知字段、非法枚举；
- 文件不存在、UTF-8/JSON 解析失败；
- 重复标识、顺序和确定性输出；
- 输出写入失败时的错误行为。

用 `subTest` 组织同一契约的表格案例：

```python
def test_invalid_statuses(self) -> None:
    for status in ("", "DONE", None, 3):
        with self.subTest(status=status):
            with self.assertRaises(TaskValidationError):
                parse_task({"id": "a", "title": "x", "status": status}, 0)
```

不要只断言“抛了异常”。尽量断言稳定异常类型或错误类别；自然语言全文容易随文案变化而脆弱。

## 让副作用可替换

最简单的测试替身往往不是 `mock.patch`，而是显式依赖：

```python
from collections.abc import Callable


def create_report(fetch: Callable[[], list[Task]]) -> dict[str, object]:
    return summarize(fetch())
```

测试传入 `lambda: [...]`，生产代码传入真实客户端。这样契约清楚，也不会依赖模块内部名字。

确需 `patch()` 时，要 patch **被测模块查找名称的位置**。若 `worker.py` 使用 `from client import send`，应 patch `worker.send`，而不是 `client.send`。`autospec=True` 可以检查属性和调用签名，但不能证明网络协议正确；动态属性或有副作用的 property 也可能让 autospec 受限。

异步依赖使用 `AsyncMock`，但仍要测试取消、超时和并发上限等真实控制流。

## 文件、时间和随机数

- 文件：使用 `tempfile.TemporaryDirectory()`，不要写仓库固定路径；
- 时间：注入 `clock()`，不要在断言中依赖当前墙钟；
- 等待：注入 `sleep()`，测试不真实休眠；
- 随机：注入带固定种子的随机源，或断言范围而非某次偶然值；
- 环境变量：给加载函数传字典，或用 patch 且测试后恢复。

确定性不仅让测试稳定，也让 Agent 工具更容易重放和审计。

## 回归测试的最小证据

修复缺陷时先保留最小失败输入：

1. 写一个在修复前失败的测试；
2. 让测试名表达缺陷，而非工单编号；
3. 做最小修复；
4. 同时跑邻近测试；
5. 若协议或安全边界变化，补集成测试和变更说明。

测试覆盖率只能说明“哪些行执行过”，不能证明断言充分、数据代表真实分布或系统安全。把覆盖率用作发现盲区的线索，不当作质量目标本身。

## 运行本库测试

从 vault 根目录运行：

```powershell
python -B -m unittest discover `
  -s '.\Knowledge\AI Agent Engineer\docs\Python基础\examples' `
  -p 'test_*.py' `
  -v
```

`-B` 禁止 Python 在测试过程中写 `.pyc`；测试自身使用临时目录。

## 练习

1. 为任务队列补齐根节点非数组、非法 JSON、未知字段、非法状态和空字符串测试。
2. 写一个顺序改变但汇总计数一致的测试；再判断 `unfinished_ids` 是否应保留输入顺序。
3. 为 `load_settings()` 使用普通字典测试，不修改真实 `os.environ`。
4. 找出一个不必要的 mock，把它重构为纯函数或显式依赖。

## 自测

- [ ] 每个测试都能说清 Given—When—Then。
- [ ] 能区分单元、集成、端到端和回归测试。
- [ ] 知道 patch 名称查找位置，而不是盲目 patch 定义位置。
- [ ] 能在测试中控制文件、时间、等待和随机性。
- [ ] 不会把覆盖率或 mock 通过误称为真实服务已验证。

## 相关概念与下一步

- 前置：[[Python基础/Agent工程路线/02-可靠性与测试/06-配置日志与敏感信息|配置、日志与敏感信息]]。
- 下一节：[[Python基础/Agent工程路线/03-并发与交付/08-异步并发取消与限流|异步、并发、取消与限流]]。
- 评测数据与模型行为见 [[评测体系/00-目录|评测体系]]，不要用普通单元测试替代模型质量评测。

## 参考资料

获取日期：**2026-07-14**。

- [Python：`unittest`](https://docs.python.org/3.14/library/unittest.html)
- [Python：`unittest.mock`](https://docs.python.org/3.14/library/unittest.mock.html)
- [Python：`tempfile`](https://docs.python.org/3.14/library/tempfile.html)

