---
title: OpenAI Platform API Key 与 Codex OAuth：认证、路由与 Runtime
tags:
  - llm-api
  - openai
  - api-authentication
  - codex
  - openclaw
aliases:
  - OpenAI API Key 与 Codex OAuth
  - OpenAI 认证与 Runtime 路由
source_checked: 2026-07-22
source_baseline:
  - OpenAI API Overview: Authentication
  - OpenAI Workload Identity Federation
  - OpenAI Codex Authentication
  - OpenClaw OpenAI provider, OAuth, Models and Agent runtimes documentation
content_origin: original
content_status: dynamic
---

# OpenAI Platform API Key 与 Codex OAuth：认证、路由与 Runtime

> 资料核验日期：2026-07-22。本文补充 [[LLM API集成/09-OpenAI Responses API常见用法|09-OpenAI Responses API 常见用法]] 的“怎样调用”部分：它不改写 09 的请求、流式和工具循环，而是回答“这次调用究竟以谁的身份、经由哪个后端和 runtime 执行”。认证方法、套餐权限、模型目录和 OpenClaw 路由都可能变化，部署前以 [OpenAI API Authentication](https://developers.openai.com/api/reference/overview#authentication)、[Workload Identity Federation](https://developers.openai.com/api/docs/guides/workload-identity-federation) 与 [OpenClaw OpenAI provider](https://docs.openclaw.ai/providers/openai) 为准。

## 先给结论：先分清三张“身份证”

`OPENAI_API_KEY` 这个环境变量名很容易造成误解：它在常规 Python SDK 中代表 **OpenAI Platform API 凭据**，不是“任何来自 OpenAI 的 token”。当前官方 API 文档列出的 API Bearer 凭据只有两类：Platform API Key，或由工作负载身份联合（WIF）签发的短期 OpenAI access token。[API Authentication](https://developers.openai.com/api/reference/overview#authentication)

| 认证方式 | 主要主体与获取方式 | 应使用的调用面 | 计费、权限与模型目录 | 不应把它当作 |
| --- | --- | --- | --- | --- |
| **OpenAI Platform API Key** | Platform 组织/项目中的 API key；由后端或 secret manager 提供 | `api.openai.com` 的标准 Platform API；例如 Python `OpenAI().responses.create(...)` | API 用量归入对应组织/项目，遵循该项目的预算、限额、API 价格与 API 模型可用性 | ChatGPT/Codex 订阅登录态 |
| **工作负载短期 access token（WIF）** | 受信任云/CI/Kubernetes 等工作负载先取得外部 OIDC subject token，再交换得到短期 OpenAI token | 同样是标准 Platform API 的 Bearer 调用；适合无长期静态密钥的服务端工作负载 | 映射到某个 OpenAI 项目的 service account；仍是 Platform API 治理与用量，不会变成 ChatGPT 套餐 | 浏览器/前端临时凭据，或 Codex OAuth token |
| **ChatGPT/Codex OAuth** | 人登录 ChatGPT/Codex 后完成 OAuth/PKCE；OpenClaw 或 Codex 管理 access/refresh token | Codex app-server、Codex 客户端或明确支持该桥接的 OpenClaw 路由 | 使用 ChatGPT/Codex 的订阅、额度窗口、工作区策略与可见的 Codex 模型目录；不等同于 Platform API token 计费 | `OPENAI_API_KEY`，或任意 Platform REST API 的通用 Bearer token |

因此有两条必须同时成立的规则：

1. **标准 Python Responses API 默认走 Platform。** `OpenAI()` 从 `OPENAI_API_KEY` 读取的是 Platform API Key；若改用 WIF，则应显式把短期 OpenAI access token 作为服务端运行时凭据传给 client。不要把 ChatGPT/Codex OAuth access token 填进这个变量。
2. **`openclaw models auth login --provider openai` 默认走 Codex OAuth。** OpenClaw 的 `openai` provider 同时容纳 API-key profile 与 ChatGPT/Codex OAuth profile；该命令不带 `--method` 时的默认意图是 ChatGPT/Codex 登录。要添加 Platform key，须显式选择 `--method api-key` 或 `paste-api-key`。[OpenClaw Models](https://docs.openclaw.ai/cli/models)

## 1. 为什么 09 的 Python 示例必须使用 Platform 凭据

09 中的下列形态是一个**直接 Platform API**调用：

```python
from openai import OpenAI  # 导入直接调用 OpenAI Platform API 的 Python 客户端。

client = OpenAI()  # 从 OPENAI_API_KEY 读取 Platform API Key，而不是 Codex OAuth profile。
response = client.responses.create(  # 向标准 Platform Responses endpoint 发起请求。
    model="<项目已验证可用的 Platform 模型>",  # 使用该 Platform 项目已验证、已获授权的模型标识。
    input="用三句话解释 API 认证。",  # 传入本轮用户任务。
)
print(response.output_text)  # 读取 SDK 提供的最终文本便利属性。
```

该 client 面向 `api.openai.com` 的 Responses endpoint。官方文档规定它接受 Platform API Key 或 WIF 交换得到的短期 OpenAI access token；这里没有把 ChatGPT/Codex OAuth 列为标准 Responses API 的认证选项。[API Authentication](https://developers.openai.com/api/reference/overview#authentication)

安全的本机学习配置可以是：

```powershell
# 只在当前 PowerShell 会话注入由 secret manager 提供的 Platform 项目密钥；占位符不是可用密钥。
$env:OPENAI_API_KEY = "<Platform project API key from secret manager>"  # 仅供当前终端内的 Platform SDK 读取，绝不写入持久文件。
$env:OPENAI_MODEL = "<Platform model allowed by this project>"  # 将模型选择集中到运行时配置，而不是散落在业务代码中。

# 不要把 ChatGPT/Codex OAuth access token 写进 OPENAI_API_KEY。
# 不把真实值写入 .ps1、真实配置、Markdown、Git 或前端代码；.env.example 也只能保留占位符。
```

### WIF 是 Platform API 的无长期密钥替代，不是第三种套餐

工作负载身份联合的流程是：受信任 identity provider 描述外部身份 → service-account mapping 把特定身份属性授权给某一 OpenAI 项目 → 工作负载交换外部 subject token → 得到**短期 OpenAI access token** → 该 token 作为 Bearer 凭据调用标准 API。[WIF 工作方式](https://developers.openai.com/api/docs/guides/workload-identity-federation#how-it-works)

它解决的是“生产工作负载不落地长期 API key”，而不是“让用户的 ChatGPT 订阅可以调用 Python SDK”。例如，下面只展示 SDK 的**传入位置**；短期 token 的交换、缓存和刷新应由受控的工作负载身份组件完成，而不是手写在业务提示词或前端中：

```python
import os  # 从受控运行环境读取短期工作负载身份 token 与模型配置。

from openai import OpenAI  # 导入同一个 Platform SDK；认证材料由调用方显式传入。

# 此值必须是服务端刚通过 WIF 获得的短期 OpenAI access token；不记录、不打印、不提交。
client = OpenAI(api_key=os.environ["OPENAI_WIF_ACCESS_TOKEN"])  # 将短期 WIF access token 作为本进程的 Bearer 凭据。

response = client.responses.create(  # 仍通过标准 Responses API 发起一轮 Platform 请求。
    model=os.environ["OPENAI_MODEL"],  # 从受控配置读取项目已允许的模型。
    input="这是一次由工作负载身份发起的 Platform API 调用。",  # 提供本轮待处理的用户输入。
)
```

对 HTTP 而言，API Key 与该短期 token 都放在 `Authorization: Bearer ...`；但它们的签发者、轮换方式和运行场景不同。WIF 需要组织 owner 预先配置 identity provider 与 service-account mapping，适合受控的云工作负载或私有 CI，而不是把 token 下发给浏览器。[WIF 工作方式](https://developers.openai.com/api/docs/guides/workload-identity-federation#how-it-works)

## 2. 为什么 OpenClaw 的同一条 `login` 命令是 Codex OAuth

OpenClaw 把两种认证都放在 canonical provider id `openai` 下，因此 provider 名相同，不能推导出认证类型。官方 CLI 文档明确说明：

```bash
# 默认：浏览器/设备码登录 ChatGPT/Codex，得到 OpenAI Codex OAuth profile。
openclaw models auth login --provider openai  # 以默认 OAuth 流建立 OpenClaw 的 Codex 登录 profile。

# 显式：交互式添加 OpenAI Platform API-key profile。
openclaw models auth login --provider openai --method api-key  # 明确选择 Platform API-key 认证，而不是 OAuth。

# 只查看 profile 元数据，不打印密钥或 OAuth secret。
openclaw models auth list --provider openai  # 查看已配置 profile 的元数据并核对当前认证选择。
```

第一条命令会走 ChatGPT/Codex OAuth；OpenClaw 为每个 agent 保存 OAuth profile，并在 access token 过期时用 refresh token 刷新。该 token 存储应视为密码：不把 `auth-profiles.json`、Codex 的 `auth.json`、回调 URL 或浏览器登录结果复制到仓库、Issue 或聊天记录中。[OpenClaw OAuth](https://docs.openclaw.ai/concepts/oauth)

这也解释了一个常见但错误的推理：

> “我已经在 OpenClaw 中登录 `openai`，所以 Python `OpenAI()` 也应该能调用。”

不成立。OpenClaw 登录得到的是供其 Codex app-server/OpenClaw 已支持桥接使用的 OAuth profile；独立 Python 进程不会自动读取它，更不应读取或复用其 refresh token。Python 的直接 Platform API 应另行配置 Platform API Key 或 WIF。

## 3. 认证、模型名、后端与 runtime 是四个不同层

排障时请分四个问题问，而不是只看“模型名像不像”：

| 层 | 要回答的问题 | 示例 |
| --- | --- | --- |
| **认证（auth profile）** | 谁在付费/被授权？ | Platform API Key、WIF 短期 token、ChatGPT/Codex OAuth |
| **模型引用（provider/model）** | 希望选择哪个 provider 与模型？ | `openai/<model>` |
| **实际后端/请求路由** | 请求是直接 Platform API、Codex app-server，还是 OpenClaw 的内部 transport？ | `api.openai.com/v1/responses`、Codex Responses backend |
| **Agent runtime** | 谁拥有 agent loop、工具循环、会话状态和 compaction？ | `openclaw` 或 `codex` |

OpenClaw 官方文档特别强调 provider、model、runtime 与 channel 是不同层；`openai/*` 是 canonical 模型引用，不是“必然使用 API Key”或“必然运行 Codex”的开关。[OpenAI provider](https://docs.openclaw.ai/providers/openai) [Agent runtimes](https://docs.openclaw.ai/concepts/agent-runtimes)

### 同一模型名不等于同一调用路径或行为

下面的 `<model>` 即使文字相同，仍可能代表不同的实际系统：

| 表面上的模型选择 | 凭据与后端 | 谁执行 agent loop | 应预期的差异 |
| --- | --- | --- | --- |
| Python `model="<model>"` | Platform API Key/WIF → 直接 Responses API | 你的 Python 应用 | Platform 项目计费、项目模型目录、你自己的 history/工具循环与重试 |
| OpenClaw `openai/<model>` + Codex OAuth + `agentRuntime: { id: "codex" }` | OAuth → Codex app-server | Codex | ChatGPT/Codex 订阅额度与账号模型目录；Codex 拥有 thread、工具与 compaction 的更多部分 |
| OpenClaw `openai/<model>` + API-key profile + `agentRuntime: { id: "openclaw" }` | Platform key → OpenClaw 的直接 provider 路径 | OpenClaw | Platform API 计费；OpenClaw 拥有 transcript、工具循环与上下文生命周期 |
| OpenClaw `openai/<model>` + OAuth + `agentRuntime: { id: "openclaw" }` | OAuth → OpenClaw 支持的内部 Codex-auth transport | OpenClaw | 这是兼容性/显式选择的桥接路径；仍不能因此把 OAuth 当成通用 Platform API key |

所以“模型显示为 `openai/<model>`”不足以证明模型能力、上下文上限、工具语义、会话存储、可用目录、用量归属或失败恢复完全一致。OpenClaw 甚至分别跟踪 subscription catalog 与 direct API-key catalog；一个目录中有的模型，另一路由可能被抑制或不可用。[OpenAI provider](https://docs.openclaw.ai/providers/openai)

## 4. `agentRuntime: openclaw`、`codex`、`auto` 如何选择实际 runtime

Runtime 只决定 agent loop 的执行者，不替代认证选择。OpenClaw 的解析顺序是：**精确模型策略 → provider 策略 → `auto` 由已注册 harness 认领 → 无匹配时回退 `openclaw`**。整 agent 或整 session 的旧 runtime pin 不再参与选择；应使用 provider/model 范围的 `agentRuntime`，并用 `openclaw doctor --fix` 清理旧配置。[Agent runtimes](https://docs.openclaw.ai/concepts/agent-runtimes)

| runtime 设置 | 实际含义 | 严格性与适用场景 |
| --- | --- | --- |
| `id: "codex"` | 强制使用 bundled Codex harness / Codex app-server 执行嵌入 agent turn | **fail closed**：harness 缺失、路由不兼容或运行失败时不静默改用 OpenClaw。适合必须验证 Codex 路径的部署。 |
| `id: "openclaw"` | 强制使用内置 OpenClaw embedded runtime | OpenClaw 拥有模型循环、canonical transcript、动态工具和大部分上下文生命周期。可配 API-key profile；若选择 OAuth profile，则走 OpenClaw 明确支持的 Codex-auth transport。 |
| `id: "auto"` 或未设置 | 让已注册 harness 按支持合约认领；无匹配则回退 OpenClaw | 对满足条件的官方 HTTPS OpenAI agent route，Codex harness 可被隐式选择；自定义 endpoint、显式 Completions adapter 或自定义 request override 等不符合条件的路由会留在 OpenClaw。不要把 `auto` 当成“永远是 Codex”。 |

下面三段都**不含密钥**，只演示 runtime policy；认证仍按上一节的命令单独建立。

```json5
// 方案 A：必须通过 Codex app-server。对匹配 OpenAI provider 的 turn 强制 Codex，失败即报错。
{
  plugins: { entries: { codex: { enabled: true } } }, // 启用 bundled Codex harness 插件。
  models: { // 配置 Provider 级模型路由策略。
    providers: { // 进入各 Provider 的专属配置。
      openai: { agentRuntime: { id: "codex" } }, // 对 OpenAI Provider 强制选择 Codex runtime。
    },
  },
  agents: { defaults: { model: { primary: "openai/<Codex account-visible model>" } } }, // 选择当前 Codex 账号可见的模型引用。
}
```

```json5
// 方案 B：明确由 OpenClaw 执行 agent loop；可配 Platform API-key profile，按 API 用量计费。
{
  models: { // 配置 Provider 级模型路由策略。
    providers: { // 进入各 Provider 的专属配置。
      openai: { agentRuntime: { id: "openclaw" } }, // 强制由 OpenClaw 自己维护 agent loop 与上下文。
    },
  },
  agents: { defaults: { model: { primary: "openai/<Platform project-visible model>" } } }, // 选择该 Platform 项目已授权的模型引用。
}
```

```json5
// 方案 C：auto。只有在可兼容的有效路由上，已注册 Codex harness 才可以认领；否则由 OpenClaw 执行。
{
  plugins: { entries: { codex: { enabled: true } } }, // 提供可被 auto 策略认领的 Codex harness。
  agents: { defaults: { model: { primary: "openai/<model>" } } }, // 只指定模型引用，不强制特定 runtime。
}
```

精确模型策略比 provider-wide 策略优先。例如要只让一个模型走 Codex，而其他 `openai/*` 留在 OpenClaw，应把 `agentRuntime` 写在该模型的 model-scoped entry，而不是直接设置整个 `openai` provider。[OpenClaw agent configuration](https://docs.openclaw.ai/gateway/config-agents)

## 5. 哪些能力不能把 Codex OAuth 当作 Platform API Key 使用

不要因为 OAuth access token 和 API Key 都可能以 Bearer 形式出现，就把它们互换。ChatGPT/Codex OAuth **不是**公开 Platform API 的泛用凭据。以下需求应选择 Platform API Key；在受控生产工作负载中可选择 WIF：

- **标准 Python/Node/HTTP 的直接 API 调用**：例如 `OpenAI().responses.create(...)`、`GET /v1/models`，以及应用直接调用的 files、vector stores、batches、fine-tuning 等 Platform REST 资源。Platform API 文档只为 API Key/WIF short-lived token 定义认证边界。
- **独立服务、CI/CD、定时任务和多实例后端**：需要可按项目轮换、撤销、预算和审计的机器身份。若不希望保存长期 key，配置 WIF；不要把个人 OAuth refresh token 种进 runner。
- **Platform 项目级账单、限额、模型可用性和 Admin/组织 API 的自动化**：这些属于 Platform 组织/项目治理，不能用“我有 ChatGPT 订阅”替代项目 API 权限。
- **任意 OpenAI-compatible base URL 或第三方代理**：OAuth 不是可随意转发给任意 endpoint 的 bearer secret；仅把 Platform key 发送给已核验的 Platform endpoint，或使用该代理明确规定的认证方式。

有一个很重要的限定：OpenClaw 可以为**它明确实现的表面**桥接 Codex OAuth。例如其当前 OpenAI provider 文档列出了通过 Codex Responses backend 的图像生成/编辑支持。这是 OpenClaw 的受支持集成，不等价于“OAuth 可以拿去调用任意 `/v1/*` 接口”，也不能推广到独立 Python SDK。[OpenClaw OpenAI image route](https://docs.openclaw.ai/providers/openai)

## 6. 选择方案：按调用目标，而不是按模型名字

| 你的目标 | 首选认证与 runtime | 原因 |
| --- | --- | --- |
| 在 Python 服务中使用 Responses API、File Search 或自建函数工具 | Platform API Key；生产云工作负载可用 WIF | 标准、可审计的 Platform API 合同；与 09 的示例一致 |
| 无长期静态密钥的 Kubernetes、云函数或私有 CI | WIF 短期 token | 身份绑定到 workload/service account，而不是把 API key 放进部署 secret |
| 用已有 ChatGPT/Codex 订阅运行 OpenClaw agent | `models auth login --provider openai` + `codex` 或合格路由上的 `auto` | OAuth 与 Codex app-server 是对应的账户型路径 |
| OpenClaw 仍要使用 API 项目计费，且希望它拥有 agent loop | OpenAI API-key profile + `agentRuntime: { id: "openclaw" }` | 认证、计费与 runtime 都是显式的，便于排障 |
| OpenClaw 需要 OAuth，但故意要求其自身 loop/工具行为 | Codex OAuth profile + `agentRuntime: { id: "openclaw" }` | 这是受支持的显式桥接；测试工具、上下文和会话语义，不要假定与 Codex runtime 相同 |

遇到“能登录但调用失败”“同名模型效果不同”“额度没有扣到预期位置”时，按下列顺序检查：

1. 这是 Platform API、Codex app-server，还是 OpenClaw embedded runtime？
2. 该 agent 当前选中的是 API-key profile、OAuth profile，还是 WIF 的服务端 token？
3. 生效的是 model-scoped、provider-scoped，还是 `auto` runtime policy？
4. 该账号/项目在**对应目录**中是否真的提供此模型与能力？

可先运行不暴露凭据的诊断命令：

```bash
openclaw models status  # 查看模型、Provider、认证和 runtime 的聚合诊断状态。
openclaw models auth list --provider openai  # 仅列出 OpenAI profile 元数据，不输出认证秘密。
openclaw config get agents.defaults.model --json  # 检查 agent 默认模型引用的有效配置。
openclaw config get models.providers.openai.agentRuntime --json  # 检查 OpenAI Provider 的实际 runtime 策略。
```

## 7. 最小安全清单

- API Key、WIF access token、OAuth access token 与 refresh token 都是秘密；不要打印、粘贴到 Markdown、提交 Git、放进浏览器前端或通过聊天转发。
- 生产服务优先使用 secret manager；需要消除长期 API key 时使用 WIF，不要以复制个人 OAuth profile 代替机器身份。
- 每个 OpenClaw agent 使用明确的 auth profile 与必要的 `auth.order`；更换 OAuth 登录后，重新检查 `models auth list` 和 runtime，而不是猜测哪个 token 生效。
- 固定模型引用不等于固定行为。升级 OpenClaw、Codex app-server、模型目录或 provider 配置后，重新验证 runtime、工具、上下文上限、计费路径和失败恢复。
- 对自动化任务优先采用 Platform API Key/WIF；Codex 官方也将 API Key 视为共享自动化环境的默认选择，而 ChatGPT/Codex access token 仅适用于受信任的自动化环境。[Codex Authentication](https://learn.chatgpt.com/docs/auth)

## 主要参考资料

- [OpenAI：API Overview — Authentication](https://developers.openai.com/api/reference/overview#authentication)（访问于 2026-07-22）
- [OpenAI：Workload Identity Federation — How it works](https://developers.openai.com/api/docs/guides/workload-identity-federation#how-it-works)（访问于 2026-07-22）
- [OpenAI Codex：Authentication](https://learn.chatgpt.com/docs/auth)（访问于 2026-07-22）
- [OpenClaw：OpenAI provider](https://docs.openclaw.ai/providers/openai)（访问于 2026-07-22）
- [OpenClaw：Agent runtimes](https://docs.openclaw.ai/concepts/agent-runtimes)（访问于 2026-07-22）
- [OpenClaw：Models CLI](https://docs.openclaw.ai/cli/models)（访问于 2026-07-22）
- [OpenClaw：OAuth](https://docs.openclaw.ai/concepts/oauth)（访问于 2026-07-22）
- [OpenClaw：Agent configuration](https://docs.openclaw.ai/gateway/config-agents)（访问于 2026-07-22）
