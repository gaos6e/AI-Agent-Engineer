---
title: "前沿专题：MCP 扩展、Apps 与版本兼容"
aliases:
  - MCP extensions and Apps
  - MCP 前沿观察
tags:
  - MCP
  - frontier
  - compatibility
source_checked: 2026-07-19
content_tier: frontier
content_origin: original
content_status: dynamic
lang: zh-CN
translation_key: MCP/学习路线/07-前沿专题-扩展Apps与版本兼容.md
translation_route: en/mcp/learning-path/07-frontier-extensions-apps-and-version-compatibility
translation_default_route: zh-CN/MCP/学习路线/07-前沿专题-扩展Apps与版本兼容
---

# 前沿专题：MCP 扩展、Apps 与版本兼容

## 本节目标

学完后，你应能：

- 把当前稳定规范、独立扩展、实验扩展和下一版草案分开记录；
- 说明工具动态发现与“只把少量工具交给模型”分别属于协议和 host 策略的哪一层；
- 为扩展协商、缺失支持、降级、授权和 breaking change 写兼容矩阵；
- 解释 MCP Apps 与 Tasks 的价值，同时不把它们误写成所有实现都支持的 core 能力。

> [!warning] 观察状态，不是稳定前置
> 本页按 2026-07-19 的 MCP 第一方资料记录。`2025-11-25` 仍是官方 latest 稳定规范；`2026-07-28` 是锁定但尚未正式发布的 release candidate，仍位于 `/specification/draft`。扩展独立演进，host、SDK 和 server 的支持会不同。实现前必须重新核对规范版本、扩展版本、支持矩阵和实际协商结果。

## 先建立四层版本账本

| 层 | 2026-07-19 状态 | 可以下什么结论 |
| --- | --- | --- |
| core stable | `2025-11-25`，官方版本页标为 latest | 可按该版本的 MUST/SHOULD 写协议测试；仍要验证双方真实实现 |
| official extension | 位于 MCP 组织的 `ext-*` 仓库，独立于 core 演进 | 只有双方显式协商支持时才可使用；SDK 不实现扩展也能符合 core |
| experimental extension | 位于 `experimental-ext-*`，用于孵化 | 只能作为实验依赖，需固定版本、隔离和退出方案 |
| draft core/SEP | 官方 Draft 或尚在推进的提案 | 可用于迁移预研，不能替代当前稳定规范的互操作合同 |

记录“我们支持 MCP”没有可操作性。至少记录：core 规范版本、initialize 实际协商版本、扩展标识与版本、host/client/server/SDK 版本、验证日期和降级行为。

## 动态发现不等于把所有工具塞进 context

稳定规范已有 `tools/list`、分页和可选的 `notifications/tools/list_changed`。这解决“client 怎样取得当前工具目录”，但不替 host 决定每轮把哪些 schema 暴露给模型。

一个可控的按需工具层通常分三步：

1. **同步目录**：从已授权 server 读取名称、描述、input/output schema 和版本指纹；列表变化后失效缓存。
2. **确定性预筛**：按租户、身份、任务类型、数据域、风险和环境删去不可用工具；安全策略不能交给模型排序。
3. **任务级选择**：检索或分类少量候选 schema，再交给模型选择；调用前仍由 runtime 重新校验参数、权限、审批与预算。

常见失败是把 tool description 当可信授权声明、缓存列表却不处理变化、依名称而不是 schema 指纹做审批，以及为了节省 token 隐去工具的副作用或错误语义。验证时应同时覆盖：新增/删除工具、同名 schema 变化、无权限候选、分页、缓存失效和模型选择错误。

Draft 页面目前加入 server discovery，并把基础协议描述为无状态、自包含 request 与逐请求 capability negotiation。这是下一版候选设计，不应反向套用到 `2025-11-25` 的有状态连接和初始化协商。

## 扩展的协商与降级

官方扩展规则要求扩展默认关闭，由 client 和 server 显式 opt in。扩展支持通过 capability 中的 `extensions` 交换；某一方不支持时，应用必须：

- 回退到有意义的 core 结果；或
- 若扩展确为安全/业务硬要求，以明确错误拒绝，而不是静默改变语义。

capability 只说明“实现声称能说这种协议”，不等于身份已认证、资源已授权、用户已审批或返回内容可信。授权、审批和 observation 清洗仍由 host/runtime 承担。

扩展独立升级。新增 required 字段、改字段类型/语义、删除字段都可能 breaking；兼容设计优先使用扩展内版本或 capability flag，并保留旧路径的明确 sunset 条件。

## MCP Apps：交互 UI 是额外信任边界

MCP Apps 允许 tool 引用交互式 UI resource，让 host 在对话中渲染表单、图表或播放器。第一方文档描述其通过 sandboxed iframe 与 `postMessage` 通信；host 控制桥接能力和安全策略，client 支持并不普遍一致。

采用前回答四个问题：

1. 纯文本或普通 web app 是否已经足够？
2. 不支持 Apps 的 client 能否得到等价的文本/结构化 fallback？
3. iframe 的网络、脚本、资源、工具代理和持久状态分别由谁授权？
4. UI 发起写操作时，是否重新经过身份、参数、审批、幂等和审计，而不是继承“已在对话中展示”的信任？

沙箱是隔离机制，不是业务授权。还应测试 CSP/允许来源、超大消息、重放、伪造 tool result、跨租户状态和 host 拒绝能力后的行为。

## Tasks：不要混用两套 wire contract

`2025-11-25` core 中的 Tasks 标为实验性。`2026-07-28` release candidate 把 Tasks 移到扩展并重构 capability/discovery；相关 SEP 明确说明，新扩展与 `2025-11-25` 的实验性 Tasks **wire 不兼容**。在 2026-07-28 正式发布前，仍应把它记录为 Draft candidate，而不是当前稳定版。

因此迁移不能只改一个 feature flag：

- 按协商的 core 版本与 extension capability 选择消息形状；
- 将 legacy task ID 与 extension task ID 分域保存；
- 分别测试创建、轮询、输入请求、取消、终态、TTL 和重连；
- 不支持 Tasks 时回退为同步结果、外部 job handle 或明确拒绝；
- 在草案发布为稳定版且双方实现通过互操作测试前，不删除旧路径。

## 最小兼容矩阵

为每个目标 host/server 填写实测结果，而不是抄支持列表：

| 场景 | 预期 | 必测证据 |
| --- | --- | --- |
| core 版本相同，无扩展 | 正常使用 core | initialize/协商记录、schema 契约测试 |
| 一方不支持可选扩展 | core fallback | 返回内容仍有意义，未调用扩展方法 |
| 一方不支持必需扩展 | 连接或请求明确拒绝 | 稳定错误码、无部分副作用 |
| tool list 运行中变化 | 缓存失效并重选 | list-changed、schema 指纹、审批失效 |
| Apps host 不支持 UI | 文本/结构化 fallback | 无空白消息、无隐藏写操作 |
| legacy Tasks 对新扩展 | 不混用 wire shape | 双版本 fixture 与负向测试 |
| 掉线后恢复 task | 从持久 handle 恢复 | 重连、重复轮询、终态不可逆 |

## 实践任务

选择一个真实 host、一个 client SDK 和一个 server，提交一份版本兼容记录：

1. 保存脱敏后的 initialize 请求/响应和实际协商版本。
2. 列出 core capabilities、extensions、授权范围与用户审批范围；四者不得合并为一列。
3. 让 tool list 增删一次，证明缓存与候选 schema 会更新。
4. 关闭一项扩展支持，验证 fallback 或明确拒绝。
5. 若测试 Apps/Tasks，固定扩展版本并补一个不支持 client 的负向用例。

完成标准不是“demo 能显示”，而是每一种协商组合都有确定结果、无越权副作用，并能从日志重建采用了哪套 contract。

## 参考资料

以下均为 MCP 第一方资料，核验于 2026-07-19：

- [MCP 2025-11-25 Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [MCP Draft Specification](https://modelcontextprotocol.io/specification/draft)
- [2026-07-28 Release Candidate](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/)
- [Extensions Overview](https://modelcontextprotocol.io/extensions/overview)
- [MCP Apps Overview](https://modelcontextprotocol.io/extensions/apps/overview)
- [MCP Tasks Extension Overview](https://modelcontextprotocol.io/extensions/tasks/overview)
- [SEP-2663: Tasks Extension](https://modelcontextprotocol.io/seps/2663-tasks-extension)

下一步返回 [[MCP/00-目录|MCP 目录]]，把本页的观察项与稳定项目测试分开维护。
