---
title: Schema 设计、版本与错误定位
tags:
  - ai-agent-engineer
  - JSON
  - JSON-Schema
  - 数据契约
aliases:
  - JSON Schema 进阶
  - Schema 版本迁移
source_checked: 2026-07-14
---

# Schema 设计、版本与错误定位

## 本节目标

能用 `$defs/$ref`、组合和条件减少重复；为工具联合类型设计明确判别字段；用版本号与迁移函数处理不兼容变化；把验证错误转换为 RFC 6901 JSON Pointer、关键字和安全错误码。

## 先把复用单元放进 `$defs`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.invalid/schemas/tool-suggestion-v1",
  "$defs": {
    "request_id": {
      "type": "string",
      "pattern": "^req-[0-9]{4}$"
    }
  },
  "type": "object",
  "properties": {
    "request_id": {
      "$ref": "#/$defs/request_id"
    }
  }
}
```

- `$id` 给 Schema 一个基础标识；示例使用保留的 `.invalid` 域名，不会成为真实端点；
- `$defs` 保存可复用子 Schema；
- `#/$defs/request_id` 是文档内 JSON Pointer；
- 远程 `$ref` 会引入解析、缓存、版本和供应链边界，生产系统应预先注册可信 Schema，不让不可信 instance 控制任意 URL。

## `allOf`、`anyOf`、`oneOf` 不是同义词

| 关键字 | 语义 | 常见用途 |
| --- | --- | --- |
| `allOf` | 所有子 Schema 都必须匹配 | 叠加独立约束；不是面向对象继承。 |
| `anyOf` | 至少一个匹配 | 允许多个可重叠形状。 |
| `oneOf` | 恰好一个匹配 | 互斥联合；分支重叠会导致意外失败。 |
| `not` | 子 Schema 不得匹配 | 排除明确形状。 |

工具参数联合推荐使用清晰判别字段：

```json
{
  "oneOf": [
    {
      "properties": {
        "tool": {"const": "search_notes"},
        "arguments": {"$ref": "#/$defs/search_arguments"}
      }
    },
    {
      "properties": {
        "tool": {"const": "send_email"},
        "arguments": {"$ref": "#/$defs/email_arguments"}
      }
    }
  ]
}
```

外层仍需 `required` 和 `additionalProperties`。若分支没有 `const` 等互斥条件，同一 instance 可能匹配两个分支，从而违反 `oneOf`。

## 用 `if/then/else` 表达局部条件

```json
{
  "if": {
    "properties": {"mode": {"const": "write"}},
    "required": ["mode"]
  },
  "then": {
    "properties": {"requires_approval": {"const": true}}
  }
}
```

这能表达“声明为写操作时，配置必须要求审批”，但 `requires_approval: true` 仍只是配置声明。真实运行时的审批事实必须来自可信审批系统，不能由模型在参数里自报 `approved: true`。

## `additionalProperties` 与组合的陷阱

`additionalProperties` 只知道同一 Schema object 中声明的 `properties`，复杂 `allOf` 组合中可能意外拒绝其他分支定义的字段。Draft 2020-12 提供 `unevaluatedProperties` 处理“已由其他子 Schema 评估的属性”，但实现支持与语义更复杂。

初学项目优先：

1. 把外层共有字段集中在一个对象 Schema；
2. 用判别字段只细化 `arguments`；
3. 对每个具体 `arguments` 对象设置 `additionalProperties: false`；
4. 为每个分支写成功和额外字段失败测试。

不要为了炫技堆叠组合；可读和可测试的契约更重要。

## Schema 版本与数据版本是两个概念

- `$schema`：JSON Schema 方言，例如 Draft 2020-12；
- `$id`：这份 Schema 资源的标识；
- instance 中的 `schema_version`：你的业务数据格式版本。

```json
{
  "schema_version": 1,
  "name": "meeting-assistant"
}
```

业务版本发生不兼容变化时：

1. 保留 v1 Schema 和测试；
2. 定义 v1 → v2 的纯迁移函数；
3. 先严格验证 v1，迁移，再验证 v2；
4. 记录迁移来源和版本，不原地猜测字段含义；
5. 设计回滚或至少保留原输入；
6. 新写入只生成当前版本，旧读取在明确期限内兼容。

字段重命名、单位改变、枚举删除和 `null` 语义改变都可能是不兼容变化。只改 Schema 文件而不迁移数据，会把旧数据变成运行时事故。

## 错误定位使用 RFC 6901 JSON Pointer

JSON Pointer 把路径编码为 `/tools/1/name`。两个转义规则：

- `~` → `~0`
- `/` → `~1`

根值的 pointer 是空字符串。项目函数：

```python
from collections.abc import Iterable


def json_pointer(parts: Iterable[str | int]) -> str:
    encoded: list[str] = []
    for part in parts:
        token = str(part).replace("~", "~0").replace("/", "~1")
        encoded.append(token)
    return "" if not encoded else "/" + "/".join(encoded)
```

不要把 JSON Pointer 与 JSONPath 混淆：Pointer 是定位单个值的标准语法；JSONPath（RFC 9535）是查询表达式。

## 验证错误要排序、归一化和脱敏

验证器可能返回多个错误，遍历顺序不应成为不稳定 API。一个可控策略：

1. 按 instance path 和 validator keyword 稳定排序；
2. 对外只返回第一个错误，或返回有上限的错误数组；
3. 记录 `code=schema_validation`、Pointer、keyword；
4. 不直接输出 `ValidationError.message` 中的 instance 值；
5. 把详细诊断留在访问受控的开发环境，并做脱敏。

例如：

```json
{
  "status": "rejected",
  "code": "schema_validation",
  "pointer": "/arguments/limit",
  "keyword": "maximum"
}
```

这个报告说明修复方向，但没有复制查询内容或邮件正文。

## Schema 测试应围绕边界与演进

每个重要字段至少测试：

- 最小合法值、最大合法值；
- 小 1、大 1；
- 缺失、`null`、错误类型；
- 未知字段；
- 每个联合分支；
- 会匹配多个/零个 `oneOf` 分支的输入；
- 旧版本、未知未来版本；
- Schema 本身能通过 `check_schema`；
- 验证错误 Pointer 和 keyword 稳定且不含敏感值。

Schema 文件与应用业务检查必须共同测试。Schema 无法表达的“工具名唯一”“ID 在数据库中存在”“写操作已审批”要有独立单元测试。

## 厂商 profile 与完整规范

LLM 厂商的 strict/structured output 常只支持 JSON Schema 的一个子集，并可能额外要求所有字段列入 `required`、每个对象写 `additionalProperties: false`，或用 `null` 表达可选。MCP 的当前版本也规定自身工具 Schema profile。

这些都是动态实现约束，不是 Draft 2020-12 的通用语义。实践时：

1. 先写领域契约；
2. 明确目标方言；
3. 为供应商编译/裁剪一个 profile；
4. 在本地再次验证模型输出；
5. 记录供应商文档获取日期和 Schema 子集限制。

## 常见错误与排查

- 把 `$schema`、`$id`、`schema_version` 当成同一版本：分别记录方言、资源和业务格式。
- `oneOf` 分支重叠：增加 `const` 判别字段和重叠失败测试。
- 让 instance 提供 `$ref` URL：只从可信注册表加载 Schema。
- 直接回显第三方错误 message：转成受控 code/pointer/keyword。
- 迁移时直接覆盖原文件：先验证、迁移到新对象、验证新版本，再原子写入。
- 把厂商子集写成“JSON Schema 不支持”：标注实现与日期。

## 练习

1. 用 `$defs/$ref` 提取一个可复用 `request_id`，并写合法/非法测试。
2. 为 `search_notes` 和 `send_email` 设计带 `const` 判别字段的 `oneOf`。
3. 构造一个同时匹配两个 `oneOf` 分支的反例，再修改 Schema 使分支互斥。
4. 设计 v1 字段 `timeout` 到 v2 `timeout_seconds` 的迁移、验证和回滚流程。
5. 把路径 `items/a~b/2` 编码成 JSON Pointer 并验证转义。

## 自测

1. `anyOf` 与 `oneOf` 的差别是什么？
2. `$schema` 和 instance 中 `schema_version` 分别控制什么？
3. 为什么 `requires_approval: true` 不能证明审批已经发生？
4. 根值的 JSON Pointer 是什么？
5. 为什么验证器原始错误消息不应直接进入普通日志？

## 小结与下一步

Schema 是版本化的结构契约，错误报告也是公共接口。下一节把它放进 API、LLM 和工具调用边界：[[JSON/07-API、LLM与工具调用中的JSON|API、LLM 与工具调用中的 JSON]]。返回 [[JSON/00-目录|JSON 学习目录]]。

## 参考资料

资料复核日期：**2026-07-14**。

- [Draft 2020-12：Core](https://json-schema.org/draft/2020-12/json-schema-core.html)
- [Draft 2020-12：Validation](https://json-schema.org/draft/2020-12/json-schema-validation.html)
- [Understanding JSON Schema：Schema Composition](https://json-schema.org/understanding-json-schema/reference/combining)
- [RFC 6901：JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901.html)
- [RFC 9535：JSONPath](https://www.rfc-editor.org/rfc/rfc9535.html)
- [`jsonschema` validator selection](https://python-jsonschema.readthedocs.io/en/stable/creating/)

