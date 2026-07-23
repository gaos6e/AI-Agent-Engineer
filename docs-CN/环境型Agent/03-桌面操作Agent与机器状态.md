---
title: "桌面操作 Agent 与机器状态"
tags:
  - environment-agent
  - computer-use
  - desktop-agent
aliases:
  - 桌面 Agent
source_checked: 2026-07-22
lang: zh-CN
translation_key: 环境型Agent/03-桌面操作Agent与机器状态.md
translation_route: en/environmental-agents/03-desktop-agents-and-machine-state
translation_default_route: zh-CN/环境型Agent/03-桌面操作Agent与机器状态
---

# 桌面操作 Agent 与机器状态

## 本节目标

- 识别桌面环境中焦点、窗口、模态框、文件与跨应用状态。
- 用可访问性信息和 typed action 替代无限制键鼠回放。
- 设计可复现机器初态和执行式终态评测。

## 为什么桌面 Agent 更难约束

浏览器通常有相对结构化的 DOM 和 origin；桌面任务可能跨应用、文件系统、系统设置、剪贴板、通知和原生对话框。相同坐标会因分辨率、缩放、窗口层叠或弹窗而指向不同对象；一次快捷键也可能发送到错误焦点。安装、删除、发送消息和系统设置还可能产生难以回滚的副作用。

OSWorld 的原始设计同时提供任务初态设置与自定义 execution-based evaluator，说明“给一张截图和目标”不足以形成可复现评测。

## 怎样实现

| 控制层 | 需要记录或限制 |
| --- | --- |
| 机器初态 | VM/镜像、OS 与应用版本、locale、时区、分辨率、缩放、账号、文件/应用数据 |
| observation | screenshot、可访问性树、窗口列表、active window、焦点、光标、文件元数据、时间戳 |
| action | `focus(window)`、`invoke(control)`、`type(text)`、`open_file(path)` 等 typed schema |
| 权限 | 可启动应用、可访问目录、网络目的地、剪贴板、设备、系统设置 |
| 恢复 | VM snapshot、任务工作目录、事件日志、幂等 receipt、人工接管点 |
| verifier | 文件内容、应用内部数据、系统设置、跨应用结果和未预期副作用 |

优先使用可访问性 role/name 或应用公开接口；只有缺少结构化接口时才使用坐标，并在每次动作前重新验证窗口、焦点、目标区域和截图版本。高风险动作应分成“准备—预览—批准—提交”，批准必须绑定文件、收件人或设置值，而不是笼统的“允许继续”。

桌面 sandbox 最稳妥的默认是一次性 VM/容器化桌面和专用低权限账号。真实宿主机操作应使用路径、应用和网络 allowlist，并默认拒绝凭据库、系统目录、浏览器 profile、摄像头/麦克风与管理员权限。

机器身份、应用 session 与任务 subject 必须分别建模。窗口标题、头像、可访问性树中的用户名以及屏幕上显示的目录都只是 observation，既不能证明当前登录账号，也不能授权对该账号的数据操作；runtime 应从受信 VM harness、OS/SSO adapter 或任务固定的低权限测试账号取得主体与环境实例 ID。可访问性信息适合缩小 UI 目标，却不是业务对象的所有权证明。涉及发送、导出、权限修改或凭据使用时，还应把外部账号、收件人/对象 ID、数据分类和目标应用一起纳入 action scope，并在 adapter 执行前再次检查。

## 常见失败

- 窗口焦点漂移，文字输入到聊天框、终端或密码框。
- 模态框、升级提示、通知或 DPI 改变坐标语义。
- 复制/粘贴泄露敏感数据，截图或日志意外收集通知和凭据。
- “关闭窗口”触发未保存确认；重试造成覆盖或重复导出。
- 评测只看最后截图，忽略文件已写到错误目录或应用设置已改变。
- VM 初态不一致导致任务难度和结果不可比较。

## 怎样验证

每个 trial 从同一快照启动，记录 observation/action/receipt 序列和前后环境差异。注入焦点切换、弹窗、窗口移动、权限拒绝和执行后超时；验证 runtime 会暂停、重新观察或交给人，而不是盲重试。终态 verifier 应读取真实文件/应用状态，并核对允许副作用清单。

## 实践任务

为“在文本编辑器中打开模板、另存为指定文件并验证内容”写测试计划：固定 VM/应用版本与初始目录；给出可访问性定位和坐标 fallback；限制文件作用域；模拟覆盖确认框和焦点丢失；使用文件 hash 与目录 diff 验证结果，确认源文件未变。

## 参考

- Xie 等，[OSWorld 原始论文](https://arxiv.org/abs/2404.07972) 与 [官方代码库](https://github.com/xlang-ai/OSWorld)。
- [Playwright actionability](https://playwright.dev/docs/actionability) 虽面向网页，但“动作前验证目标可操作”的原则可迁移到桌面 adapter；具体检查必须按目标 OS 与应用重新实现。
- [OWASP AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)：外部数据不可信、最小权限和敏感操作独立授权（访问于 2026-07-22）。
