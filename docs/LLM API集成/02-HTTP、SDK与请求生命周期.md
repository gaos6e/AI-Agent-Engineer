---
title: HTTP、SDK 与请求生命周期
tags:
  - llm-api
  - http
  - sdk
aliases:
  - LLM 请求生命周期
source_checked: 2026-07-14
source_baseline:
  - RFC 9110 HTTP Semantics
  - OpenAI API errors and official Python SDK documentation
  - Anthropic API errors documentation
---

# HTTP、SDK 与请求生命周期

## 本节目标

理解 SDK 是 HTTP API 的封装，能定位序列化、连接、服务端处理、解析与业务验证各阶段的故障。

## 一次调用经过什么

1. 应用验证输入、上下文预算和权限。
2. adapter 把供应商无关请求映射为当前 SDK/HTTP 字段。
3. SDK 序列化 JSON、加入认证与版本头，通过 TLS 发送 HTTP 请求。
4. 服务端鉴权、限流并执行模型推理。
5. 客户端接收完整 JSON 或 SSE 事件流。
6. adapter 转换为统一结果；应用校验 schema、语义与授权。
7. 记录脱敏指标和请求 ID，再返回用户或执行下一步。

知道阶段才能正确分类：本地 JSON 序列化错误不应重试；DNS 或连接中断可能暂时可恢复；HTTP 401 多半需要修复认证；HTTP 429 需要遵循限流信息；响应成功也可能在业务校验阶段失败。

## SDK 还是直接 HTTP

官方 SDK 通常提供类型、认证、流式迭代和错误类，适合大多数项目。直接 HTTP 便于学习协议或处理 SDK 未覆盖的能力，但你要自己维护版本头、事件解析、错误形状与兼容性。无论哪种，都应把供应商对象限制在 adapter 层。

SDK 可能自带重试和很长的默认超时。若外层、SDK、网关和队列各自重试，最坏请求次数会相乘。以 2026-07-14 的官方 `openai-python` README 为例，连接错误、408、409、429 与部分 5xx 会由 SDK 默认重试；这只是一个当前实现示例，不应推广给其他 SDK。查阅并记录实际 SDK 版本与默认值，明确唯一重试负责人，再为总 attempts 和业务截止时间设上限。

超时也不是一个数字：至少区分连接、读取/流空闲、单次调用和业务总截止时间。SDK 能限制单次网络等待，应用层截止时间决定这次业务请求是否还值得继续。真实副作用应在生成之后由独立、幂等的业务步骤执行。

## 响应元数据

保留服务端请求 ID、HTTP 状态、完成/停止原因、用量、缓存信息与原始错误类型；不要依赖错误消息字符串，因为文案会变化。原始请求/响应若含个人信息或机密，默认不持久化。

HTTP 请求 ID 与应用 `operation_id` 不同：前者通常每次 attempt 都变化，用于供应商排障；后者在同一业务操作的所有 attempts 中稳定，用于本地去重与追踪。不要用请求 ID 代替业务幂等键。

## 练习与自测

画出一次 SDK 调用的七阶段时序，并把“无密钥、连接超时、429、JSON 字段缺失、模型拒答、业务规则失败”放到对应阶段。自测：哪些失败可自动重试，哪些必须修改请求或请求人工处理？

## 掌握检查

- [ ] 我能把序列化、连接、服务端、流解析、业务校验和授权错误定位到具体层。
- [ ] 我已查明所用 SDK 的版本、默认超时与默认重试，不让多层策略相乘。
- [ ] 连接、读取/流空闲、单次调用和业务截止时间都有明确负责人。
- [ ] 服务端 request ID 与应用 operation ID 分开记录，不把前者当幂等键。
- [ ] 供应商原始对象只存在于 adapter 层，应用合同不依赖其私有字段。

## 下一步

进入 [[LLM API集成/03-消息、配置与版本意识|消息、配置与版本意识]]。

## 参考资料

- [RFC 9110：HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110)
- [OpenAI：API errors](https://developers.openai.com/api/docs/guides/error-codes)（访问于 2026-07-14）
- [OpenAI：official Python SDK—Retries and timeouts](https://github.com/openai/openai-python#retries)（访问于 2026-07-14）
- [Anthropic：API errors](https://platform.claude.com/docs/en/api/errors)（访问于 2026-07-14）
