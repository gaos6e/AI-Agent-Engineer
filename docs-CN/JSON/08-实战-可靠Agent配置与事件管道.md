---
title: "实战：可靠 Agent 配置与事件管道"
tags:
  - ai-agent-engineer
  - JSON
  - 综合实践
  - Agent工程
aliases:
  - JSON 综合项目
  - Agent JSON 管道项目
source_checked: 2026-07-22
lang: zh-CN
translation_key: JSON/08-实战-可靠Agent配置与事件管道.md
translation_route: en/json/08-project-reliable-agent-configuration-and-event-pipeline
translation_default_route: zh-CN/JSON/08-实战-可靠Agent配置与事件管道
---

# 实战：可靠 Agent 配置与事件管道

## 项目目标

在完全本地、无真实凭据和无线上副作用的环境中完成：

1. 有限读取 UTF-8 JSON；
2. 拒绝 BOM、重复键、`NaN/Infinity`、溢出浮点、孤立 surrogate 和资源超限；
3. 运行真实 Draft 2020-12 Schema；
4. 应用 Schema 无法表达的业务不变量；
5. 按物理行处理 JSONL，坏行不污染后续记录；
6. 用可信工具策略把建议分为“仅验证”和“需要审批”；
7. 生成不含参数值的脱敏报告；
8. 在同目录临时文件上 flush、fsync、关闭并 `os.replace`；
9. 在普通与 `python -O` 模式运行同一套测试。

项目不会调用搜索、邮件、日历或任何模型。`send_email` 只是 Schema 分支名称，管线只输出 `approval_required`。

## 环境准备

以下代码块按顺序从同时包含 `docs/` 与 `.website/` 的项目根目录开始运行；最后一组独立检查会返回项目根目录：

```powershell
Push-Location -LiteralPath 'docs\JSON'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\examples\requirements.txt
```

依赖文件固定 `jsonschema==4.26.0`。这是截至 2026-07-22 的当前正式 PyPI 版本，也是本机实际测试版本；升级时先阅读 changelog，再复跑普通与 `-O` 测试。不要提交 `.venv`。

## 文件结构与责任边界

| 文件 | 单一责任 |
| --- | --- |
| `strict_json.py` | 严格编解码、资源树检查、JSONL、原子替换；不懂 Agent 业务。 |
| `agent_config.json` | 虚构会议助理配置，无端点和凭据。 |
| `agent_config.schema.json` | Draft 2020-12 配置结构、范围和写工具审批声明。 |
| `validate_agent_config.py` | Schema validator、RFC 6901 Pointer 和业务不变量。 |
| `tool_calls.jsonl` | 两条本地工具建议：只读查询、需审批邮件。 |
| `tool_call.schema.json` | 用 `oneOf + const` 区分工具参数。 |
| `validate_tool_calls.py` | 逐行验证、request ID 去重、可信策略分类和脱敏报告。 |
| `demo.py` | 在 `TemporaryDirectory` 中做原子写和读回，不留生成文件。 |
| `test_strict_json.py` | 编解码、Unicode、数字、限制、JSONL 和原子失败测试。 |
| `test_agent_pipeline.py` | Schema、业务、审批、继续处理和脱敏测试。 |

## 第一步：运行完整演示

```powershell
python -B .\examples\demo.py
```

预期输出：

```text
validated config: meeting-assistant
report statuses: {'approval_required': 1, 'validated_not_executed': 1}
no tools executed; temporary report removed
```

三个句子分别证明：配置通过三层验证；两条记录进入不同安全状态；项目没有执行工具且临时报告已删除。它不证明 Schema 适合你的生产业务，也不证明真实外部系统可用。

## 第二步：理解严格解析层

`strict_json.py` 的默认上限：

| 限制 | 默认值 | 防护目标 |
| --- | ---: | --- |
| 单 JSON 文本/文件 | 65,536 bytes | 编码文本受限；写文件时末尾 LF 也计入文件总字节。 |
| 最大深度 | 24 | 深递归和复杂结构。 |
| 单容器成员 | 1,000 | 巨大数组/对象。 |
| 总值节点 | 10,000 | 多层小容器组合放大。 |
| 单字符串 | 16,384 characters | 超长文本与日志风险。 |
| 数字 token | 100 characters | 巨大整数转换和异常范围。 |
| JSONL 单条内容 | 16,384 bytes | 按 JSON 文本 UTF-8 字节计，不含 LF/CRLF。 |
| JSONL 记录数 | 1,000 | 无界批次。 |
| JSONL 总量 | 1,048,576 bytes | 批量输入上限。 |

顺序是“有限字节 → UTF-8 → 严格解析 hooks → 迭代结构检查”。`object_pairs_hook` 在对象构造时拒绝重复键；`parse_constant` 拒绝 `NaN` 等字面量；自定义 float parser 和结构检查再拒绝 `1e9999` 产生的无穷值。

错误统一成 `JsonDataError(code, line, column)`，消息不含原 payload。上限是教学选择，不是通用推荐值；生产参数应由真实载荷分布、压力测试和拒绝策略决定。

## 第三步：运行 Schema 与业务检查

```powershell
python -B .\examples\validate_agent_config.py
```

流程：

1. 严格读取 Schema 并要求顶层对象；
2. `Draft202012Validator.check_schema` 检查 Schema 本身；
3. 严格读取配置；
4. Schema 检查字段、类型、范围、未知字段和条件；
5. 应用代码检查“必须用整数 token”“工具名唯一”等不变量。

JSON Schema 把数学值为整的 `1.0` 视作 integer；本配置文件另要求词法整数，因此代码检查 Python 解码类型必须是精确 `int`。这是应用 profile，应写进文档并测试，不能冒充 JSON Schema 通用语义。

## 第四步：理解工具建议管线

输入 `tool_calls.jsonl` 有两个分支：

```json
{"schema_version":1,"request_id":"req-0001","tool":"search_notes","arguments":{"query":"JSON 严格解析","limit":5}}
```

```json
{"schema_version":1,"request_id":"req-0002","tool":"send_email","arguments":{"recipient":"team@example.test","subject":"教学演示","body":"这是本地验证样例，不会发送。"}}
```

`tool_call.schema.json` 只允许 `search_notes` 与 `send_email` 两个名称，并为参数各自设置 `additionalProperties: false`。可信代码 registry 再决定 `send_email` 需要审批。

输出报告最多含：

```json
{
  "line": 2,
  "request_id": "req-0002",
  "status": "approval_required",
  "code": "human_approval_required"
}
```

报告不会复制 `arguments`、查询、收件人、正文或原始 ValidationError message。无论状态为何，这个项目都没有 `executed` 或 `succeeded` 状态。

## 第五步：运行测试

```powershell
python -B -W error::ResourceWarning -m unittest discover `
  -s '.\examples' `
  -p 'test_*.py' `
  -v
```

再验证优化模式不会移除测试：

```powershell
python -B -O -W error::ResourceWarning -m unittest discover `
  -s '.\examples' `
  -p 'test_*.py' `
  -v
```

本轮实际两种模式各运行 **42 项测试**，全部通过。`-B` 禁止生成 `.pyc`，`ResourceWarning` 视为错误；测试使用 `unittest` 断言，不用会被 `-O` 删除的裸 `assert`。

覆盖范围包括：

- 六类值与精确 Python 类型；
- 中文、Windows 路径、转义和 LF；
- 顶层/嵌套重复键；
- `NaN`、正负 Infinity、`1e9999`、长整数；
- 非法 UTF-8、BOM、孤立 surrogate；
- 文档、深度、容器、字符串、总节点、JSONL 上限；
- LF、CRLF、无末尾换行、空行、损坏行后继续；
- 原子替换成功和模拟失败时旧文件保持；
- Schema 自检、必填、未知字段、类型、范围、条件和业务不变量；
- 只读、需审批、重复 request ID、提示注入作为普通数据；
- 敏感哨兵不进入报告。

## 第六步：独立检查 JSON 文件

```powershell
python -B -m json.tool .\examples\agent_config.json *> $null
python -B -m json.tool .\examples\agent_config.schema.json *> $null
python -B -m json.tool .\examples\tool_call.schema.json *> $null
Pop-Location
```

`tool_calls.jsonl` 不能整体交给 `json.tool`；它应由项目逐行解析。语法工具也不能替代 Draft 验证。

## 安全与能力边界

- 无真实 API key、token、cookie、个人邮箱、线上 endpoint 或客户数据；
- `.invalid` 与 `example.test` 是保留示例域，不会成为真实服务；
- 不使用 `eval`、`exec`、动态 `getattr` 或模型控制的输出路径；
- 工具风险来自可信 registry，不来自输入字段；
- 原子写只保证有限单文件替换语义，不提供事务与并发一致性；
- `jsonschema` 是第三方依赖，需供应链管理、版本固定和升级测试；
- 解析、Schema 和业务通过仍不代表外部事实正确或动作获授权。

## 扩展任务

每项都先写失败测试，再实现：

1. 添加只读工具 `lookup_document`，给 `document_id` 使用字符串契约并限制长度。
2. 添加 config v2，将 `timeout_seconds` 拆成连接/读取超时，并实现 v1 → v2 纯迁移。
3. 为 JSONL 处理增加有上限的汇总错误数组，同时保持 payload 脱敏。
4. 增加可信审批输入参数（由调用者提供，不在模型 JSON 中），让测试证明未审批时永不执行。
5. 把报告写入用户指定的临时输出目录，模拟 `os.replace` 失败并验证退出码。
6. 比较 `sort_keys=True` 输出与 RFC 8785 canonicalization，禁止把前者用于签名。

## 项目验收

- [ ] 能解释每个文件的单一责任。
- [ ] 能手工追踪一条合法和一条非法 JSONL 记录。
- [ ] 能区分严格解析、Schema、业务 registry 与审批。
- [ ] 能解释 42 项测试中至少 10 个失败边界保护什么风险。
- [ ] 能在普通和 `-O` 模式复现全部测试通过。
- [ ] 扩展一个字段或工具时，同时更新 Schema、代码、成功/失败测试和文档。
- [ ] 能证明项目无持久生成物、真实凭据和工具副作用。

## 小结与下一步

项目把“格式正确”推进到“边界可证明”，但刻意停在执行之前。现在完成 [[JSON/09-练习、自测与掌握标准|练习、自测与掌握标准]]，再回到 [[JSON/00-目录|JSON 学习目录]] 复核全库清单。

## 参考资料

资料与依赖复核日期：**2026-07-22**。

- [Python `json`](https://docs.python.org/3.14/library/json.html)
- [Python `os.replace`](https://docs.python.org/3/library/os.html#os.replace)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [`jsonschema` 4.26.0](https://python-jsonschema.readthedocs.io/en/stable/)
- [RFC 6901：JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901.html)
