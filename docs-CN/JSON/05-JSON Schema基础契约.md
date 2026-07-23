---
title: "JSON Schema 基础契约"
tags:
  - ai-agent-engineer
  - JSON
  - JSON-Schema
aliases:
  - JSON Schema 入门
  - JSON 数据契约
source_checked: 2026-07-22
lang: zh-CN
translation_key: JSON/05-JSON Schema基础契约.md
translation_route: en/json/05-json-schema-core-contracts
translation_default_route: zh-CN/JSON/05-JSON-Schema基础契约
---

# JSON Schema 基础契约

## 本节目标

能区分语法、Schema 和业务验证；读写一个 Draft 2020-12 对象 Schema；正确使用 `type`、`properties`、`required`、`additionalProperties`、数组和范围关键字，并用 Python `jsonschema` 真正执行验证。

## Schema 验证位于哪一层

以 `{"amount": 1000}` 为例：

1. **语法层**：文本能否严格解析，是否有重复键、非标准数字和资源超限；
2. **Schema 层**：顶层类型、字段、范围和组合是否符合声明；
3. **业务层**：账户是否存在、余额是否足够、单位是否正确；
4. **授权层**：当前身份是否允许执行；
5. **副作用层**：幂等、审批、执行结果和审计是否正确。

JSON Schema 主要负责第 2 层。不要期待一个关键字替代外部数据库、权限系统或人工审批。

## 实例、Schema 与方言

- **instance**：被验证的 JSON 值；
- **schema**：描述约束的 JSON 文档；
- **dialect/draft**：关键字及其语义版本。

本库使用 Draft 2020-12，并在每份 Schema 顶部显式声明：

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object"
}
```

截至 2026-07-22，JSON Schema 官方站仍把 Draft 2020-12 列为当前正式发布方言。验证器可能只支持旧 draft，厂商结构化输出也可能只支持某个子集；使用前检查实现文档和 `$schema`，不要依赖“最新默认”。

## 一个可运行的 Agent 配置 Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "name", "max_steps", "tools"],
  "properties": {
    "schema_version": {"const": 1},
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 64
    },
    "max_steps": {
      "type": "integer",
      "minimum": 1,
      "maximum": 20
    },
    "tools": {
      "type": "array",
      "minItems": 1,
      "maxItems": 20,
      "items": {"type": "string"}
    }
  }
}
```

### `properties` 不表示必填

`properties` 只说明字段出现时怎样验证。要要求字段出现，必须把名称放入 `required`。

### 可选与可空不同

字段不在 `required` 中表示可以缺失。允许 `null` 表示字段存在时可以为空：

```json
{
  "type": ["string", "null"]
}
```

两者的业务含义要另写说明。

### `additionalProperties` 默认允许未知字段

工具参数和内部命令通常应显式决定是否拒绝未知字段。`false` 能捕获拼写错误并缩小攻击面，但也会提高版本升级成本。长期开放配置可以选择允许扩展、保留未知字段或告警；不要无意识依赖默认值。

## 常用验证关键字

| 数据类型 | 常用关键字 | 注意点 |
| --- | --- | --- |
| 通用 | `type`、`enum`、`const` | `enum` 候选应稳定且有迁移策略。 |
| object | `properties`、`required`、`additionalProperties`、`minProperties` | 字段存在、字段约束和未知字段是三个决定。 |
| array | `items`、`prefixItems`、`minItems`、`maxItems`、`uniqueItems` | 2020-12 的 tuple 语义使用 `prefixItems`；对象按整值判重。 |
| string | `minLength`、`maxLength`、`pattern`、`format` | `pattern` 是正则；`format` 默认常是注解。 |
| number | `minimum`、`maximum`、`exclusiveMinimum`、`multipleOf` | JSON Schema `integer` 按数学值，不等同 Python `type is int`。 |

`uniqueItems: true` 能拒绝完全相同的数组元素，却不能直接表达“对象数组中的 `name` 字段必须唯一”。这类跨项不变量通常由应用代码检查。

## `default` 和 `format` 的真实语义

- `default` 是注解，标准验证过程不保证把缺失字段写入 instance；
- Draft 2020-12 把 `format` 分为 annotation 和 assertion vocabulary，具体验证器是否拒绝非法邮箱/日期需要显式配置；
- 若应用要应用默认值、规范化时间或检查域名，必须用代码执行并测试，不要假设 Schema 自动修改数据。

## 在 Python 中真实验证

本项目固定 `jsonschema==4.26.0`。安装后：

```python
from jsonschema import Draft202012Validator

schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["max_steps"],
    "properties": {
        "max_steps": {"type": "integer", "minimum": 1, "maximum": 20}
    },
    "additionalProperties": False,
}

Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema)
errors = list(validator.iter_errors({"max_steps": 0}))

if errors:
    print(errors[0].validator)  # minimum
```

工程顺序：先严格解析 Schema 本身，调用 `check_schema`；再构造明确 draft 的 validator；最后对 instance 使用 `iter_errors`。不要用验证器自动选择“当前最新 draft”代替显式契约。

## 错误信息要稳定且脱敏

第三方 `ValidationError.message` 可能包含实际值。普通日志可以记录：

- 内部错误码，例如 `schema_validation`；
- instance 的 JSON Pointer；
- 失败关键字，例如 `required`、`maximum`；
- request ID、Schema 版本和来源；
- 是否可重试或需要修复输入。

不要记录完整 instance、邮件正文、token 或未经清洗的模型文本。项目把第一个确定排序的错误转换成 `code + pointer + keyword`。

## Schema 不能证明的事

即便 `{"document_id":"doc-42"}` 通过 Schema，也不能证明：

- 文档真实存在；
- ID 属于当前租户；
- 调用者可以读取；
- 文档内容可信；
- 模型选择这个 ID 有事实依据；
- 工具已经成功执行。

这些检查必须留在可信应用层。

## 常见错误与排查

- 写了 `properties` 却忘记 `required`：为缺失字段增加失败测试。
- 认为 `default` 自动补值：在应用层显式应用并保存迁移结果。
- 认为 `format: email` 必定拒绝：核对 validator 的 format assertion 配置。
- 直接把 Python 类型等同 JSON Schema 类型：特别测试 `True`、`1`、`1.0`。
- 只验证成功样例：为每个重要关键字写恰好在边界和越界 1 的测试。
- Schema 通过后直接执行工具：继续业务、授权与审批层。

## 练习

1. 为 `timeout_seconds` 写 1–120 的整数约束，并测试 1、120、0、121 和 `true`。
2. 为 `log_level` 写四个枚举值；设计未来新增枚举时的兼容策略。
3. 比较“可选字符串”和“必填但可为 null 的字符串”。
4. 把未知字段策略分别设计为拒绝、允许和嵌套扩展对象，说明取舍。
5. 运行 `Draft202012Validator.check_schema`，故意写错一个 `type` 并观察 SchemaError。

## 自测

1. `properties` 是否要求字段存在？
2. `required` 是否保证字符串非空？
3. `default` 是否保证验证器修改 instance？
4. 为什么要显式声明 `$schema`？
5. Schema 通过后还要做哪些层次的检查？

## 小结与下一步

基础 Schema 表达单值与局部结构；复杂契约还需要复用、组合、版本和稳定错误路径。继续 [[JSON/06-Schema设计、版本与错误定位|Schema 设计、版本与错误定位]]。返回 [[JSON/00-目录|JSON 学习目录]]。

## 参考资料

资料复核日期：**2026-07-22**。

- [JSON Schema Specification](https://json-schema.org/specification)
- [Draft 2020-12](https://json-schema.org/draft/2020-12)
- [Understanding JSON Schema](https://json-schema.org/understanding-json-schema/)
- [`jsonschema` 4.26.0 documentation](https://python-jsonschema.readthedocs.io/en/stable/)
- [`jsonschema` 4.26.0 on PyPI](https://pypi.org/project/jsonschema/)
