---
title: "Context Pack 项目与自测"
tags:
  - context-engineering
  - project
  - self-test
aliases:
  - 上下文工程项目
source_checked: 2026-07-21
execution_verified: 2026-07-21
content_origin: original
content_status: validated
source_baseline:
  - Python 3.11 standard-library documentation
  - JSON Schema 2020-12 documentation
  - OpenAI and Anthropic context-management documentation
lang: zh-CN
translation_key: 上下文工程/08-Context Pack项目与自测.md
translation_route: en/context-engineering/08-context-pack-project-and-self-test
translation_default_route: zh-CN/上下文工程/08-Context-Pack项目与自测
---

# Context Pack 项目与自测

## 项目目标与边界

实现一个确定性的 context pack 构建器。它依次执行严格 JSON 校验、权限、信任、日期、显式去重和预算门禁，再按 `policy → state → evidence → current-input` 的顺序输出片段及来源。每个被排除的片段都有机器可读原因。

项目不调用 tokenizer 或模型 API。案例中的 `estimated_tokens` 是外部给定的教学数据，只能验证选择算法，不能证明真实 token、费用或模型质量。生产系统必须用目标模型的计数能力和响应 `usage` 校准。

> [!important] 信任控制面边界
> 为便于离线教学，fixture 把请求策略和候选片段放在同一 JSON 文件中。生产系统必须拆开信任来源：`granted_permissions` 来自已认证主体与授权服务，`allowed_trust` 来自应用策略，chunk 的 `trust`、`required_permission`、`required` 与 `dedupe_key` 由受控摄取流程赋值。不可信正文不能自行抬高信任、授予权限、声明为必选项或决定去重关系；本选择器只校验声明的一致性，不负责认证这些声明。

## 项目文件

| 文件 | 职责 |
| --- | --- |
| [[上下文工程/examples/context_budget.py\|context_budget.py]] | 严格加载案例，执行五类门禁，构建确定性 context pack 与 CLI 退出码 |
| [[上下文工程/examples/chunks.json\|chunks.json]] | 11 个带来源、版本、权限、信任、有效期、优先级和预算的版本化片段 |
| [[上下文工程/examples/context-pack.schema.json\|context-pack.schema.json]] | 输出 pack 的 JSON Schema 2020-12 契约 |
| [[上下文工程/examples/test_context_budget.py\|test_context_budget.py]] | 18 项单元测试，覆盖非法输入、失败关闭、去重边界、确定性、schema 和 CLI |

## 运行环境

脚本只使用 Python 标准库，不需要联网、第三方依赖或 API key。在 Windows 11 的 PowerShell 7 中，以下代码块按顺序从同时包含 `docs/` 与 `.website/` 的项目根目录开始执行；生成检查包后会返回项目根目录：

```powershell
Push-Location -LiteralPath 'docs\上下文工程'  # 临时进入课程目录，使 examples 的相对路径可直接使用。
py -3.11 --version  # 先核对 Python Launcher 解析出的解释器版本。
py -3.11 -m unittest discover -s .\examples -p 'test_context_budget.py' -v  # 正常模式运行 context pack 的全部单元测试。
py -3.11 -O -m unittest discover -s .\examples -p 'test_context_budget.py' -v  # 用 -O 复跑，确认失败关闭逻辑不依赖 assert。
```

普通项目应先学习 [[Python基础/00-目录|Python 基础]]中的 `venv + pip`。本项目零依赖，直接使用已安装的 Python，以免在 vault 中生成 `.venv`；如需练习隔离环境，请把虚拟环境建在 vault 外。

## 分步骤实验

### 1. 阅读输入合同

先打开 [[上下文工程/examples/chunks.json|chunks.json]]。顶层 `request` 给出观察日期、已授予权限、允许的信任标签和 pack 预算。每个 chunk 都有：

- 稳定 `id`、`source_uri` 与 `source_version`；
- `effective_from` 与排他的 `expires_on`；
- `required_permission` 与 `trust`；
- 受控 `dedupe_key`、`priority`、`required` 和 `estimated_tokens`；
- 最终进入上下文的 `section` 与 `content`。

`dedupe_key` 只应用于业务上确认可互换的片段。相互矛盾的来源不能为了省 token 共用一个 key，否则会把冲突误当重复。即使业务内容等价，同一组成员也必须拥有相同 `section`、`required_permission` 与 `trust`；否则优先级排序可能让低权限或低信任片段替换另一安全类别，加载器会直接拒绝该 fixture。

### 2. 构建默认 pack

```powershell
py -3.11 .\examples\context_budget.py  # 使用默认教学夹具构建一次确定性的 context pack。
$LASTEXITCODE  # 显示 CLI 的退出码，0 表示构建与所有门禁均通过。
```

当前案例预算为 170 个**估算 token**，使用 162，剩余 8；选择顺序为 `policy`、`task-state`、`current-refund-policy`、`refund-faq`、`current-input`。退出码应为 `0`。

六个排除原因各出现一次：权限不足、信任不允许、尚未生效、已经过期、显式重复和预算不足。选择器先执行安全与有效期门禁，再去重和分配预算；低优先级内容不能挤掉必选策略或当前状态。

### 3. 生成可检查的 JSON pack

```powershell
$pack = Join-Path $env:TEMP "context-pack.json"  # 选择系统临时目录作为报告位置，避免产生 vault 工件。
py -3.11 .\examples\context_budget.py --json-pack $pack  # 将本次入选与排除结果输出为可检查的 JSON pack。
Get-Content -LiteralPath $pack -Raw -Encoding utf8  # 以 UTF-8 查看完整 pack，核对预算和来源字段。
Pop-Location  # 回到执行前的项目根目录，避免影响后续命令的相对路径。
```

输出包含版本、观察日期、预算、已用/剩余估算、带来源的入选片段和不含正文的排除记录。教学 pack 含样例 `content`，便于查看最终上下文；生产日志不应默认保存真实正文，必须按隐私、权限和保留期另行设计。

### 4. 证明必选项会失败关闭

测试套件会在临时目录构造四种必选项失败：缺权限、信任标签不允许、尚未生效和已经过期；还会把预算降到必选项总量以下。构建器必须返回错误而不是静默丢弃，CLI 返回 `2` 且不打印 traceback。正式 fixture 不会被修改。

### 5. 检查确定性

同一测试将 11 个输入片段以固定随机种子打乱，再比较完整 pack。结果必须逐字段相同。确定性让版本差异可审计，但不意味着这个贪心优先级策略在所有业务上最优；覆盖度、多样性或组合价值仍需由任务评测验证。

## 本机验证记录

2026-07-21 在 Python 3.11 上完成：

- `py -3.11 -m py_compile`：脚本与测试均通过。
- 普通模式：18 项测试全部通过，warnings-as-errors。
- `python -O` 模式：同一 18 项测试全部通过，关键门禁不依赖可被优化移除的裸 `assert`。
- CLI：默认案例 5 个入选、6 个排除，估算用量 `162/170`。
- 普通模式与 `-O` 模式的 CLI 文本和 JSON pack 逐字一致。

这些结果只覆盖离线合同和选择器；未调用供应商 tokenizer、模型 API，也未验证真实回答质量或 Obsidian 阅读视图。

## 扩展任务

1. 新增与目标模型匹配的计数 adapter，同时保留离线 `estimated_tokens` 测试；比较发送前计数与响应 `usage`。
2. 增加“每个子问题至少一个证据”和来源多样性约束，证明简单按优先级贪心的局限。
3. 把冲突来源作为独立组保留，要求回答同时引用新旧版本并解释生效规则。
4. 增加摘要/compaction 前后状态不变量：金额、日期、拒绝项、未决问题和来源 ID 不得丢失。
5. 在学完 [[评测体系/00-目录|评测体系]] 后，对不同 pack 策略运行位置、干扰、多证据、注入、延迟和成本矩阵。

## 自测题

1. 为什么字符数和 `estimated_tokens` 不能作为真实 token 或费用证据？
2. 为什么权限、信任和日期门禁必须早于相关性排序与预算选择？
3. `dedupe_key` 用错会怎样把来源冲突静默删除？
4. 为什么缓存命中不扩大窗口，也不证明 context pack 正确？
5. 必选上下文超限时，失败、拆任务和受控压缩各适合什么情况？
6. 确定性选择为什么仍不等于任务质量最优？

## 掌握检查

- [ ] 我能运行普通与 `-O` 测试，并解释 18 项测试覆盖的失败类型。
- [ ] 我能从每个入选片段追到来源、版本、有效期、信任和权限。
- [ ] 我能让必选项的权限或预算失败返回非零状态，而不是静默继续。
- [ ] 我不会把样例估算称为真实 token，也不会默认记录生产正文。
- [ ] 我能为冲突、去重、覆盖度和压缩后的信息保真设计测试。
- [ ] 我能说明离线 pack 验证与真实模型长上下文评测之间仍缺哪些证据。

## 主要参考资料

- [Python 3.11：`json`](https://docs.python.org/3.11/library/json.html)（访问于 2026-07-21）
- [Python 3.11：`unittest`](https://docs.python.org/3.11/library/unittest.html)（访问于 2026-07-21）
- [JSON Schema：Getting started](https://json-schema.org/learn/getting-started-step-by-step)（访问于 2026-07-21）
- [OpenAI：Compaction](https://developers.openai.com/api/docs/guides/compaction)（访问于 2026-07-21）
- [Anthropic：Context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows)（访问于 2026-07-21）

## 回到目录

返回 [[上下文工程/00-目录|上下文工程学习目录]]，或继续 [[LLM API集成/00-目录|LLM API 集成]]。
