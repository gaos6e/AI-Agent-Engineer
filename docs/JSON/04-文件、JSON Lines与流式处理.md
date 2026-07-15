---
title: 文件、JSON Lines 与流式处理
tags:
  - ai-agent-engineer
  - JSON
  - JSONL
  - 文件处理
aliases:
  - JSON Lines
  - JSON 文件安全写入
source_checked: 2026-07-14
---

# 文件、JSON Lines 与流式处理

## 本节目标

能为“一个完整状态”和“很多独立记录”选择合适格式；会逐行定位 JSONL 错误、限制文件资源并原子替换单个输出文件；能准确说明原子替换不等于事务、并发控制或断电绝对持久。

## 单个 JSON 文档没有记录 framing

一个 `.json` 文档表示一个 JSON 值。以下写法连续输出两个对象，但文件整体不是一个合法 JSON 文本：

```python
import json

with open("events.json", "w", encoding="utf-8") as file:
    json.dump({"id": 1}, file)
    json.dump({"id": 2}, file)
```

可选方案取决于访问模式：

- 一个小型配置或状态快照：写一个对象；
- 需要整体读取、保留顺序的小集合：写一个数组；
- 持续追加、逐条处理的日志或数据集：约定 JSON Lines/NDJSON；
- 正式的 IETF 序列格式：评估 RFC 7464 JSON Text Sequences；
- 大规模随机查询和并发更新：使用数据库或日志系统，不把 JSON 文件硬扮成数据库。

## JSON Lines 是“每个物理行一个 JSON 值”

常见 `.jsonl` 文件：

```text
{"event_id":"evt-0001","type":"tool_requested"}
{"event_id":"evt-0002","type":"tool_validated"}
```

每一行分别是合法 JSON；整个文件通常不是一个合法的单文档 JSON 数组。JSON Lines 社区约定通常要求 UTF-8、无 BOM、每行一个值，并建议文件末尾保留 LF。空行不是 JSON 值；接收方应明确“拒绝、跳过还是记录告警”。

字符串中的 `\n` 是转义后的逻辑换行，不会切开物理记录：

```text
{"message":"first\nsecond"}
```

生产者必须用 JSON 编码器把真实换行转义，不能手工拼接行。

## JSONL、NDJSON 与 JSON Text Sequences 不完全相同

| 格式 | 分隔方式 | 标准状态与常见媒体类型 | 不能混淆的点 |
| --- | --- | --- | --- |
| JSON | 一个值 | RFC 8259；`application/json` | 没有多记录 framing。 |
| JSON Lines | 每行一个 JSON 值 | 社区约定；`.jsonl` | 空行策略和 MIME 尚无统一 IETF 标准。 |
| NDJSON | 每条 JSON 文本后跟 LF | 社区规范；常见 `application/x-ndjson` | 与 JSONL 很接近，但接收规则仍需双方约定。 |
| JSON Text Sequences | 每条前置 RS `0x1E`，后接 LF | RFC 7464；`application/json-seq` | RS 能帮助从损坏记录恢复，不是普通换行 JSONL。 |
| JSON5 | 扩展语法 | 独立格式 | 注释、尾逗号、单引号等不是标准 JSON。 |

协议文档要写出格式名、编码、空行、末尾换行、记录顶层类型、错误恢复和大小上限，不能只写“返回 JSON 流”。

## 逐行处理要保留物理行号

```python
import json
from pathlib import Path


def read_objects(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                raise ValueError(f"blank record at line {line_number}")
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON at physical line {line_number}") from error
            if type(value) is not dict:
                raise ValueError(f"record at line {line_number} must be an object")
            records.append(value)
    return records
```

这是最小模式，但仍会接受重复键、`NaN` 和无限长行。综合项目 `scan_json_lines` 以二进制读取、限制单行/记录数/总字节、严格 UTF-8，并把单行错误变成不含原载荷的结果，使后续合法记录仍可处理。项目把“单行上限”定义为该记录 JSON 文本的 UTF-8 字节数，不含 LF/CRLF；总文件上限则包含分隔符。读写端用同一定义，并测试 exact-limit 与 limit+1。

## 失败策略必须由场景决定

遇到第 17 行损坏时可以：

- **fail fast**：配置导入、财务批次等要求全有或全无；
- **隔离坏记录并继续**：遥测、爬取或训练数据预处理，但必须输出行号和失败统计；
- **重试来源**：网络分片可能截断；先确认协议是否允许恢复；
- **进入 dead-letter 队列**：保留受控证据供人工处理，不把敏感 payload 写入普通日志。

“跳过错误”若没有计数、告警和重放策略，会把数据丢失伪装成成功。

## 解析前限制字节，而不是读取后才检查字符数

UTF-8 的字符数不等于字节数。安全读取的小文件模式是：

1. 以二进制打开；
2. 只读 `max_bytes + 1`；
3. 超限立即拒绝；
4. 拒绝 BOM，并用 strict UTF-8 解码；
5. 进入唯一键、数字与结构限制；
6. 再做 Schema 和业务验证。

先 `stat()` 再无界 `read_text()` 存在检查和读取之间的变化窗口，也可能一次分配过多内存。项目直接做有限读取。

## 原子替换避免“看见半个文件”

不要在目标路径上直接截断后慢慢写。常见单文件模式：

```python
import json
import os
from pathlib import Path
import tempfile


def replace_json(path: Path, value: object) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary = Path(file.name)
            json.dump(value, file, ensure_ascii=False, allow_nan=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
```

关键点：临时文件与目标同目录，Windows 上在 `os.replace` 前关闭句柄，异常时清理临时文件。项目还在编码失败和模拟替换失败时验证“旧目标保持不变”。

## 原子替换能力边界

它只解决一部分问题：成功替换时，读者通常看到旧完整文件或新完整文件，而非半文件。它不自动提供：

- 两个进程同时“读—改—写”的丢失更新防护；
- 多文件一致提交；
- 数据库隔离级别；
- 所有平台与文件系统上的断电绝对持久；
- 网络共享盘的相同语义；
- 版本冲突检测、锁或 compare-and-swap。

需要并发状态时，引入版本号、文件锁或事务存储，并在目标平台做故障注入验证。

## 常见错误与排查

- 把 JSONL 整体交给 `json.load`：逐行读取，或改成数组。
- 用 `line.strip()` 后再解析并丢失原行号：只移除协议允许的 CR/LF，保留物理位置。
- 允许无限长单行：用有限 `readline` 或有限流式解析器。
- 某行失败后默默继续：输出明确状态和总数，决定退出码。
- 原地截断配置：写同目录临时文件、flush、fsync、关闭并替换。
- 把原子替换描述成事务数据库：写清单文件和并发边界。

## 练习

1. 把一个三元素 JSON 数组改成三行 JSONL，再逐行读回并保留行号。
2. 构造空行、损坏第二行、超长行和无末尾 LF 四个样例，定义各自策略。
3. 在临时目录测试原子写；模拟序列化失败并证明旧文件未改变。
4. 比较 JSONL 与 RFC 7464 在损坏记录恢复上的分隔机制。
5. 设计一个需要数据库而不适合 JSON 文件的并发 Agent 状态场景。

## 自测

1. 两次 `json.dump` 为什么不会自动形成两条记录？
2. JSON 字符串中的 `\n` 会不会切开 JSONL 物理行？
3. JSON Lines 与 `application/json-seq` 的分隔符有何不同？
4. 为什么要先限制字节再 UTF-8 解码？
5. `os.replace` 能否防止两个写者相互覆盖更新？

## 小结与下一步

文件格式决定记录边界，原子替换只保证有限的单文件可见性。下一节用 JSON Schema 描述每条记录应有的形状：[[JSON/05-JSON Schema基础契约|JSON Schema 基础契约]]。返回 [[JSON/00-目录|JSON 学习目录]]。

## 参考资料

资料复核日期：**2026-07-14**。

- [JSON Lines](https://jsonlines.org/)
- [NDJSON specification](https://github.com/ndjson/ndjson-spec)
- [RFC 7464：JSON Text Sequences](https://www.rfc-editor.org/rfc/rfc7464.html)
- [Python `os.replace`](https://docs.python.org/3/library/os.html#os.replace)
- [Python `tempfile.NamedTemporaryFile`](https://docs.python.org/3/library/tempfile.html#tempfile.NamedTemporaryFile)
