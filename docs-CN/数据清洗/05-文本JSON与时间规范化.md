---
title: "文本、JSON 与时间规范化"
tags:
  - ai-agent-engineer
  - data-quality
aliases:
  - 半结构化数据清洗
source_checked: 2026-07-14
source_baseline:
  - RFC 8259 JSON
  - RFC 3339 timestamps
  - JSON Schema 2020-12
  - Python 3 standard-library documentation
lang: zh-CN
translation_key: 数据清洗/05-文本JSON与时间规范化.md
translation_route: en/data-cleaning/05-text-json-and-time-normalization
translation_default_route: zh-CN/数据清洗/05-文本JSON与时间规范化
---

# 文本、JSON 与时间规范化

## 本节目标

在不破坏代码、Markdown、标识符和凭据边界的前提下规范文本、JSON 与时间，并为每次有损变化保留来源和审计证据。

## 文本

先统一 UTF-8 读写，保留原文，再生成规范字段。对自然语言字段，可在契约允许时去首尾空格和统一换行；不要默认折叠内部连续空白，因为它会改变 Python 缩进、Markdown 代码块、表格和用户原始格式。Unicode NFC/NFKC 可能改变字符表现；NFKC 会把部分兼容字符合并，涉及密码、代码、标识符或法律原文时不能盲用。

大小写、标点、emoji、代码块和 Markdown 结构可能承载语义。RAG 清洗不应为了“干净”删除标题、列表、表格或页码来源。

## JSON

JSON 对象应验证必填字段、类型、枚举和嵌套结构。注意：

- JSON 标准不允许注释，键名必须是字符串。
- `null` 与字段不存在应按契约区分。
- 数字范围需结合消费端实现；超大整数可能在其他语言丢精度。
- 不要把未知字段静默丢弃；记录 schema 版本和兼容策略。

JSON Schema 应声明具体 `$schema` 版本（当前规范为 2020-12）。`format: "date-time"` 在不同验证器中可能只是注解，是否作为阻断断言需要显式配置并用失败样例测试，不能只看 schema 文件“写了 format”。

## 时间

时间至少包含事件时刻、时区和精度。内部常统一到 UTC，展示时再转本地时区。只有 `2026-07-13 09:00` 而无时区时，不能可靠排序跨地区事件。

区分：事件发生时间、服务接收时间、入库时间。延迟到达和时钟偏差会让它们不同。不要用文件修改时间代替业务事件时间。

## 隐私与凭据

清洗前后都不得在日志中输出 token、cookie、API key、完整邮箱或不必要的用户内容。脱敏规则应在源字段副本上执行并测试，不能只靠正则假设覆盖所有秘密格式。

哈希适合做完整性和关联摘要，但不是自动匿名化：低熵标识符可被枚举反推，相同输入也会暴露关联。敏感数据仍需最小化、访问控制、留存和删除策略。

## 练习

设计一条工具调用 JSON 事件，包含 `schema_version`、`event_id`、UTC 时间、工具名、状态、错误码和经过脱敏的参数摘要。说明哪些字段禁止进入训练数据。

## 掌握检查

- [ ] 我知道何时只能规范换行/首尾空白，不能折叠内部空白或应用 NFKC。
- [ ] 我能区分 JSON `null`、字段缺失与空字符串，并声明未知字段策略。
- [ ] 我会把含时区时间转换为 UTC，同时保留事件/接收/入库三种时刻的语义。
- [ ] 我不会把哈希、掩码或正则替换直接称为匿名化。

下一步：[[数据清洗/06-质量验证与可复现管线|质量验证与可复现管线]]。

## 参考资料

资料核验日期：2026-07-14。

- [RFC 8259: JSON](https://www.rfc-editor.org/rfc/rfc8259)
- [RFC 3339: Date and Time on the Internet](https://www.rfc-editor.org/rfc/rfc3339)
- [JSON Schema 2020-12 specification](https://json-schema.org/specification)
- [Python `unicodedata`](https://docs.python.org/3/library/unicodedata.html)
- [Python `datetime`](https://docs.python.org/3/library/datetime.html)
