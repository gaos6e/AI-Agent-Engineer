---
title: "编码 Agent 与可验证补丁"
tags:
  - environment-agent
  - coding-agent
  - software-evaluation
aliases:
  - 编码 Agent
source_checked: 2026-07-22
lang: zh-CN
translation_key: 环境型Agent/04-编码Agent与可验证补丁.md
translation_route: en/environmental-agents/04-coding-agents-and-verifiable-patches
translation_default_route: zh-CN/环境型Agent/04-编码Agent与可验证补丁
---

# 编码 Agent 与可验证补丁

## 本节目标

- 把编码 Agent 建模为对版本化仓库环境的受控操作。
- 设计读取、编辑、命令与测试的最小动作空间。
- 以目标测试、回归测试和 diff 共同验证补丁。

## 为什么代码生成不等于编码 Agent

编码 Agent 面对的不是一个函数提示，而是仓库状态：base commit、未提交修改、依赖、构建工具、测试数据、操作系统、环境变量和 issue 语义。补丁可能修复目标测试却破坏已有行为；shell 命令可能读出凭据、访问网络或改变仓库外文件；测试输出也可能包含恶意或误导性文本。

SWE-bench 把真实 GitHub issue、仓库基线和执行测试连在一起，提供了比字符串相似度更强的结果验证。但它仍是特定任务分布与 harness，不等于代码质量、安全、维护性或生产发布。

## 怎样实现

1. **建立任务封套**：任务 ID、issue、base commit、允许路径、语言/依赖锁、离线或网络策略、资源/时间预算、禁止行为和完成标准。
2. **保护用户工作树**：使用隔离 worktree、容器或临时副本；先记录现有 diff，绝不把“清理环境”实现成破坏性 reset。
3. **缩小动作空间**：优先 `search(query, scope)`、`read(path, range)`、`apply_patch(path, expected_hash, patch)`、`run_test(target)`；任意 shell 仅在强 sandbox 与命令策略下开放。
4. **版本化编辑**：动作绑定文件 hash/base revision；写入前检查路径和旧内容，冲突则重新观察。每次 patch 都有可逆 diff 与 receipt。
5. **分层验证**：先跑最小目标测试，再跑相关回归、静态检查和必要的完整 suite；测试环境必须固定且不依赖未知网络状态。
6. **完成门**：同时检查目标行为、原有行为、工作树 diff、禁止路径、生成产物、敏感信息和剩余失败；模型自述不是证据。

> [!warning] Git worktree 不是安全沙箱
> linked worktree 能把 checkout、`HEAD` 和 index 与用户当前工作树分开，适合保护未提交修改、固定 base revision 和并行 trial；它仍共享同一仓库的大部分对象，且默认共享 repository config。因此它不隔离进程、网络、凭据、全局配置或仓库外路径；由 common Git directory/config 触达的 hooks 与设置也应视为共同攻击面。把编码 Agent 放进独立 worktree 后，仍需另行限制文件系统、命令、网络、环境变量和可用凭据；生产 adapter 不能把“位于 worktree 内”误当作完整安全证明。[Git worktree 官方文档](https://git-scm.com/docs/git-worktree.html)（访问于 2026-07-22）

SWE-bench 的 `FAIL_TO_PASS` 可理解为目标缺陷是否修复，`PASS_TO_PASS` 可理解为原有行为是否保持。实际项目还应增加类型/lint、安全、性能、迁移与人工 review 门禁。

## 常见失败

- 未固定 base commit 或依赖，测试结果无法复现。
- Agent 看到用户未提交改动后覆盖、格式化或删除无关文件。
- 只跑一个目标测试，遗漏回归；或修改测试来“证明”实现正确。
- shell 权限过大，命令逃逸工作区、读取凭据或下载未审查依赖。
- 测试进程超时后盲重试，遗留服务、锁文件、端口或数据库写入。
- benchmark 通过率被误当真实工程能力，忽略数据污染和任务分布变化。

## 怎样验证

从干净且固定的 snapshot 运行多次 trial，记录每次读取、patch、命令、测试与环境 diff。至少注入：陈旧文件 hash、路径越界、命令拒绝、目标测试通过但回归失败、测试超时、修改测试文件、已有用户 diff。只有 verifier 基于当前 worktree 和当前测试 receipt 通过时才能完成。

## 实践任务

选择一个带失败测试的小型离线仓库：冻结 base commit 和依赖；只开放一个源码目录和精确测试命令；让 action 使用 expected file hash；修复后运行目标与回归测试；输出补丁、测试 receipt、未预期文件变化和回滚步骤。再写一个负向用例，证明 Agent 不能编辑测试来取巧。

## 参考

- Jimenez 等，[SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://openreview.net/forum?id=VTF8yNQM66)，ICLR 2024。
- [SWE-bench 官方项目与 evaluation harness](https://github.com/SWE-bench/SWE-bench)。
- Yang 等，[SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)：action interface 对 agent 能力的影响。
- [Git worktree 官方文档](https://git-scm.com/docs/git-worktree.html)：linked worktree 的共享与 per-worktree 状态边界（访问于 2026-07-22）。
- [OWASP Secure Coding with AI Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Coding_with_AI_Cheat_Sheet.html)：agentic coding 的多重信任边界（访问于 2026-07-22）。
