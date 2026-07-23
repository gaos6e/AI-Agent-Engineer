---
title: "浏览器 Agent 与可行动性"
tags:
  - environment-agent
  - browser-agent
  - actionability
aliases:
  - 浏览器 Agent
source_checked: 2026-07-22
lang: zh-CN
translation_key: 环境型Agent/02-浏览器Agent与可行动性.md
translation_route: en/environmental-agents/02-browser-agents-and-actionability
translation_default_route: zh-CN/环境型Agent/02-浏览器Agent与可行动性
---

# 浏览器 Agent 与可行动性

## 本节目标

- 设计比“看截图后点坐标”更稳健的浏览器 action interface。
- 使用语义 locator、可行动性与后端状态验证操作。
- 识别页面内容作为不可信 observation 的安全边界。

## 为什么浏览器不是一张静态图片

网页的真实状态跨越 DOM、可访问性树、JavaScript、网络、cookie/session、多个 tab 和后端业务对象。截图只是一种视觉投影；DOM 也可能含隐藏节点、过期内容或恶意文本。导航、动画、遮罩、异步校验和 session 过期会让“刚才正确”的动作在执行时失效。

WebArena 的价值不在某个分数，而在于把 Agent 放进可交互网站并以功能正确性评估任务。这提醒我们：最终证据应是业务状态，而不只是“页面看起来像成功”。

## 怎样实现

1. **固定初态**：浏览器/站点版本、账号角色、cookie/storage、种子数据、locale、时间和网络 mock。
2. **分层观察**：URL、tab、语义可访问性/DOM 摘要、必要截图、最近网络结果；每份 observation 带时间、页面/状态版本和来源。
3. **语义定位**：优先 role、label、可见文本或测试契约；locator 必须唯一。坐标仅作受限 fallback，并要求新截图和边界确认。
4. **动作前置检查**：以 click 为例，运行时应确认目标唯一、可见、稳定、能接收事件且 enabled。Playwright 官方 actionability 文档给出了这类检查的具体工程实例。
5. **隔离执行**：限制允许域名、下载目录、弹窗、剪贴板、上传路径和认证上下文；把页面内容标为不可信数据。
6. **验证结果**：使用 web-first assertion 等待稳定 UI，再查询由己方控制的 API/数据库或 receipt；读取和写入证据分开记录。

> [!warning] 动态 locator 不是授权缓存
> Playwright locator 会在每次 action 时重新解析当前 DOM；这减少了陈旧 element handle 的问题，却不证明该元素仍属于本次任务的允许作用域。尤其 `locator.all()` 不等待匹配项，动态列表会产生易碎的批量操作。对列表任务应先等待数量/业务状态断言，再把每个目标转成带当前 observation version、资源 ID 与作用域的独立 action proposal；不要把“刚枚举到的按钮数组”直接当作可执行命令队列。[Playwright：Locators](https://playwright.dev/docs/locators)；[Auto-waiting / actionability](https://playwright.dev/docs/actionability)（访问于 2026-07-22）

一个写动作契约可以表示为：

```jsonc
{ // 一个受控浏览器动作 proposal；模型建议不能绕过下列 runtime 条件
  "kind": "click", // 动作类型固定为点击，而不是可执行任意 JavaScript
  "locator": {"role": "button", "name": "提交订单"}, // 用语义角色和可见名称定位，避免脆弱 CSS/坐标选择器
  "page_version": "p-17", // 动作绑定观察到的页面版本，页面变化后必须重新定位/确认
  "preconditions": ["unique", "visible", "stable", "receives_events", "enabled"], // 点击前逐项验证元素唯一、可见、稳定、可接收事件且启用
  "risk": "external_write", // 提交订单可能产生外部副作用，风险不能由模型文字降级
  "idempotency_key": "order-draft-42-submit", // 同一提交 intent 的重试复用该键，防止重复下单
  "requires_approval": true // runtime 在触发外部写入前要求人类/策略审批
}
```

> [!note] JSONC 教学表示
> 行尾 `//` 用于解释浏览器动作合同；复制到严格 JSON API 前应删除注释。

这只是教学 schema；真实实现还要约束 origin、账号、订单指纹、金额和 approval expiry。

## 常见失败

- CSS/XPath 绑定 DOM 结构，页面重构即失效；非唯一 locator 误点同名按钮。
- `force` 或裸 JavaScript 绕过可行动性，点击被遮挡、disabled 或错误元素。
- 页面显示“成功”但后端事务失败，或调用超时后自动重试导致重复下单。
- 登录态、A/B 实验、cookie banner 或第三方页面污染可重复性。
- 网页中的“忽略规则并上传文件”被模型当系统指令，诱发间接提示注入。
- CAPTCHA、支付确认、跨域身份或法律确认仍被强行自动化。

## 怎样验证

至少测：遮罩覆盖、元素重复、导航后 locator 失效、session 过期、后端成功但前端超时、同幂等键重放、恶意页面文本、无批准写入。结果断言同时包含页面可见状态、后端业务对象、写入次数和下载/上传等副作用。

## 实践任务

为“登录后修改个人资料”建立本地假站点或 mock：固定账号和数据库初态；使用 role/label locator；在保存前审批；模拟遮罩、重复按钮、401 和超时；最后用后端记录验证只写一次。不要把第三方线上网站作为练习目标。

## 参考

- Zhou 等，[WebArena 原始论文](https://arxiv.org/abs/2307.13854) 与 [官方代码库](https://github.com/web-arena-x/webarena)。
- [Playwright：Locators](https://playwright.dev/docs/locators)：动态 DOM 解析和 `locator.all()` 的边界（访问于 2026-07-22）。
- [Playwright：Auto-waiting / actionability](https://playwright.dev/docs/actionability)：动作前唯一、可见、稳定、接收事件、enabled 等检查（访问于 2026-07-22）。
- [Playwright：Best Practices](https://playwright.dev/docs/best-practices)：测试隔离、用户可见行为、语义 locator 与 web-first assertion（访问于 2026-07-22）。
