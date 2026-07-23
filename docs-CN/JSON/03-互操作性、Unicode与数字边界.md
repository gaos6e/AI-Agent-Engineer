---
title: "互操作性、Unicode 与数字边界"
tags:
  - ai-agent-engineer
  - JSON
  - 互操作性
  - 安全
aliases:
  - JSON 互操作边界
  - 严格 JSON profile
source_checked: 2026-07-14
lang: zh-CN
translation_key: JSON/03-互操作性、Unicode与数字边界.md
translation_route: en/json/03-interoperability-unicode-and-number-boundaries
translation_default_route: zh-CN/JSON/03-互操作性、Unicode与数字边界
---

# 互操作性、Unicode 与数字边界

## 本节目标

理解“某个解析器接受”为什么不足以证明跨系统可靠；能为重复键、UTF-8、Unicode scalar、数字范围、对象顺序和资源上限制定接收策略；知道稳定格式化与 RFC 8785 canonicalization 的区别。

## 规范、实现与应用 profile

工程判断要分三层：

1. **RFC 8259 语法与互操作建议**：描述 JSON 文本；
2. **解析器实现行为**：可能接受扩展，或暴露不同语言类型；
3. **应用 profile**：在特定接口中进一步限制顶层类型、大小、数字、字段和错误策略。

例如，对象成员名在 RFC 8259 中是 `SHOULD` 唯一。重复键文本可能仍被某些解析器接受，但不同实现会保留第一项、最后一项、全部项或直接报错。安全接口应把“唯一”提升为应用硬约束。

## 重复键必须在解析阶段处理

```text
{"role": "reader", "role": "admin"}
```

若网关保留第一项、后端保留最后一项，双方会对同一请求做出不同授权判断。Schema 验证的是解析后的对象；第一个值若已经被丢弃，就无法恢复冲突证据。因此顺序是：

```text
字节上限 → UTF-8 解码 → 唯一键/有限数字解析 → 结构资源检查 → Schema → 业务/授权
```

项目使用 `object_pairs_hook` 在每个嵌套对象构造 `dict` 前检查重复名。

## 对象无业务顺序，数组有顺序

Python `dict` 保留插入顺序，`json` 模块也默认保留输入和输出顺序；这是一项实现行为，不应被误写成 JSON 对象的跨系统业务语义。

- 对象适合按名称访问独立字段；
- 数组适合表达有先后关系的步骤、消息或排序结果；
- 若顺序对对象成员很重要，应改成数组，例如 `[{"name":"a"}, {"name":"b"}]`；
- 测试对象时比较解析值，不要仅比较任意 pretty-printed 文本。

## UTF-8、BOM 与 Unicode scalar

RFC 8259 要求开放系统之间的 JSON 使用 UTF-8，网络发送方不得添加 BOM。解析器可以选择忽略 BOM，但应用为了单一确定 profile 可以拒绝它。

还要区分：

- Unicode 字符（code point）与 UTF-8 字节编码；
- 组合字符与视觉上相同的预组字符；
- 合法 Unicode scalar 与孤立 UTF-16 surrogate，例如 `"\uDEAD"`。

RFC 8259 的语法可能让孤立 surrogate 进入文本，但接收实现的结果不可预测。项目严格拒绝 U+D800–U+DFFF 范围的孤立值。不要擅自对所有字符串做 Unicode normalization：用户名、签名材料和外部 ID 是否归一化必须由字段契约决定。

```python
text_a = "é"          # U+00E9
text_b = "e\u0301"   # U+0065 + U+0301

assert text_a != text_b
```

两者显示可能接近，却不是相同码点序列。

## 数字语法不承诺无限精度

JSON 的 `number` 没有 `int64`、`float32` 或 Decimal 标记。RFC 8259 指出，在广泛使用的 IEEE 754 binary64 系统间，整数区间 `[-(2^53)+1, (2^53)-1]` 能获得一致精确值；超出范围的整数和过高精度小数可能发生互操作问题。

| 数据 | 推荐契约 | 原因 |
| --- | --- | --- |
| 计数、步数 | 有范围的 integer | 可做算术，边界明确。 |
| 数据库/雪花 ID | string | 避免精度丢失、前导零和误算。 |
| 金额 | 最小单位 integer 或规范化十进制 string | 明确舍入与精度。 |
| 时间 | 含时区/偏移的 string | JSON 没有日期类型。 |
| 非有限计算结果 | 错误或显式状态对象 | `NaN`、`Infinity` 不是 RFC 8259 number。 |

`1e400` 在语法上可以是 JSON number，但接收方用 binary64 时可能溢出。因此项目限制 token 长度并在解析后检查 `math.isfinite`；真正业务还应给字段设置 `minimum`、`maximum` 或字符串格式。

## 不可信输入的资源上限

“只是数据”不等于没有拒绝服务风险。一个小入口可以触发大对象分配、深递归或昂贵验证。至少考虑：

- 解析前总字节数；
- UTF-8 解码错误；
- 最大嵌套深度；
- 单个数组元素数和对象成员数；
- 总节点数；
- 单字符串字符数；
- 数字 token 长度；
- JSONL 单行、记录数和总文件大小；
- 请求层的读取超时与压缩解压上限。

上限不是越小越好，而是由真实用例、压力测试与故障策略共同确定。错误应归一化，不能把 `RecursionError` 或含载荷的原始异常直接暴露给调用方。

## 文本稳定化不等于 canonicalization

```python
import json

stable_for_tests = json.dumps(
    {"b": 2, "a": 1},
    ensure_ascii=False,
    allow_nan=False,
    sort_keys=True,
    separators=(",", ":"),
)
```

这对本项目快照测试很有用，但不自动满足 RFC 8785 JSON Canonicalization Scheme（JCS）。签名与哈希还涉及：

- 数字序列化规则；
- 字符串转义；
- Unicode 处理；
- 属性排序；
- 重复键和 I-JSON 限制。

需要数字签名时使用经过验证的 JCS 实现和明确协议，不能自己拼接 JSON 字符串。

## JSON 值相等与业务等价

- 文本空白或对象字段顺序不同，解析值仍可能相等；
- 数字 `1` 和 `1.0` 在 JSON Schema 中可按数学值都满足 `integer`，但 Python 解码类型分别是 `int` 与 `float`；
- Unicode 视觉相同不保证码点相同；
- Schema 相等不等于业务状态相同；
- 反复解析和序列化可能改变空白、转义、数字文本和字段顺序。

如果业务要求“必须使用整数 token”，需要像项目那样在 Schema 后增加应用规则 `type(value) is int`，并把这个要求写进契约。

## 常见错误与排查

- 只靠 WAF/Schema 检查重复键：解析器若已覆盖旧值，证据消失。
- 把 Python 字典顺序当协议顺序：改用数组或显式 `order` 字段。
- 把 UTF-16/UTF-32 输入也叫“UTF-8 接口”：在字节边界严格解码并测试 BOM。
- 只拒绝字面量 `NaN`：还要拒绝有限范围外的 `1e9999` 结果。
- 在错误日志中复制完整 payload：使用错误码、行列、JSON Pointer 和 request ID。
- 把 `sort_keys=True` 宣称为可签名 canonical form：引用并实现明确标准。

## 练习

1. 用 Python 默认 `json.loads` 解析重复 `role`，记录结果；再用 hook 改成拒绝。
2. 为一个 ID、金额、时间和概率字段分别选择 JSON 表示，并说明取舍。
3. 设计四组资源限制及其边界测试，包括恰好等于上限和超出 1。
4. 比较 `{"a":1,"b":2}` 与 `{"b":2,"a":1}` 的文本、解析值与哈希。
5. 说明为什么对签名材料随意做 Unicode normalization 可能破坏验证。

## 自测

1. RFC 8259 是否要求每个解析器都必须拒绝重复键？
2. 为什么 Schema 无法发现已经被解析器覆盖的重复值？
3. JSON 对象和数组的顺序语义有何差别？
4. `1e400` 为什么可能语法合法却不可互操作？
5. `sort_keys=True` 为什么不等于 RFC 8785？

## 小结与下一步

严格 profile 是明确选择的契约，不是某个库的默认标签。下一节把这些边界用于文件、逐行记录和原子替换：[[JSON/04-文件、JSON Lines与流式处理|文件、JSON Lines 与流式处理]]。返回 [[JSON/00-目录|JSON 学习目录]]。

## 参考资料

资料复核日期：**2026-07-14**。

- [RFC 8259：Objects、Numbers、Character Encoding、Security](https://www.rfc-editor.org/rfc/rfc8259.html)
- [RFC 7493：The I-JSON Message Format](https://www.rfc-editor.org/rfc/rfc7493.html)
- [RFC 8785：JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html)
- [Python `json`：Standard Compliance and Interoperability](https://docs.python.org/3.14/library/json.html#standard-compliance-and-interoperability)

