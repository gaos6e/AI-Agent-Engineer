---
title: "OpenAI Platform API Keys and Codex OAuth: Authentication, Routing, and
  Runtime"
tags:
  - llm-api
  - openai
  - api-authentication
  - codex
  - openclaw
aliases:
  - OpenAI API Keys and Codex OAuth
  - OpenAI Authentication and Runtime Routing
source_checked: 2026-07-22
source_baseline:
  - OpenAI API Overview: Authentication
  - OpenAI Workload Identity Federation
  - OpenAI Codex Authentication
  - OpenClaw OpenAI provider, OAuth, Models and Agent runtimes documentation
content_origin: original
content_status: dynamic
lang: en
translation_key: LLM API集成/10-OpenAI Platform API Key 与 Codex OAuth：认证、路由与 Runtime.md
translation_source_hash: 3078463965dcf362680c03b9a472059f0f299f701d617abca4267619fe723103
translation_route: zh-CN/LLM-API集成/10-OpenAI-Platform-API-Key-与-Codex-OAuth：认证、路由与-Runtime
translation_default_route: zh-CN/LLM-API集成/10-OpenAI-Platform-API-Key-与-Codex-OAuth：认证、路由与-Runtime
---

# OpenAI Platform API Keys and Codex OAuth: Authentication, Routing, and Runtime

> Source review date: 2026-07-22. This page complements the “how to call it” material in [[llm-api-integration/09-common-openai-responses-api-patterns|09: Common OpenAI Responses API Patterns]]. It does not rewrite that page's request, streaming, or tool loop; instead it asks, “Under whose identity, through which backend, and runtime does this call actually execute?” Authentication methods, plan entitlements, model catalogs, and OpenClaw routing can change. Before deployment, use [OpenAI API Authentication](https://developers.openai.com/api/reference/overview#authentication), [Workload Identity Federation](https://developers.openai.com/api/docs/guides/workload-identity-federation), and the [OpenClaw OpenAI provider](https://docs.openclaw.ai/providers/openai) as authority.

## The conclusion first: distinguish three identity cards

The environment-variable name `OPENAI_API_KEY` can easily mislead: in the normal Python SDK it represents an **OpenAI Platform API credential**, not “any token from OpenAI.” Current official API documentation lists exactly two kinds of API Bearer credential: a Platform API key or a short-lived OpenAI access token issued through workload identity federation (WIF). [API Authentication](https://developers.openai.com/api/reference/overview#authentication)

| Authentication method | Principal and acquisition | Calling surface | Billing, authorization, and model catalog | Do not treat it as |
| --- | --- | --- | --- | --- |
| **OpenAI Platform API key** | API key in a Platform organization/project, supplied by a backend or secret manager | Standard Platform API at `api.openai.com`, for example Python `OpenAI().responses.create(...)` | API usage belongs to the corresponding organization/project and follows that project's budget, limits, API prices, and API-model availability | a ChatGPT/Codex subscription login state |
| **Workload short-lived access token (WIF)** | A trusted cloud/CI/Kubernetes workload obtains an external OIDC subject token and exchanges it for a short-lived OpenAI token | The same standard Platform API Bearer call, suitable for server workloads without long-lived static keys | Mapped to a service account in one OpenAI project; still Platform API governance and usage, not a ChatGPT plan | a browser/frontend temporary credential or Codex OAuth token |
| **ChatGPT/Codex OAuth** | A human signs into ChatGPT/Codex through OAuth/PKCE; OpenClaw or Codex manages access/refresh tokens | Codex app-server, Codex clients, or an OpenClaw route that explicitly supports the bridge | Uses ChatGPT/Codex subscription, quota windows, workspace policy, and the visible Codex model catalog; it is not billed as a Platform API token | `OPENAI_API_KEY` or a general Bearer token for arbitrary Platform REST APIs |

Two rules must therefore both hold:

1. **The standard Python Responses API defaults to Platform.** `OpenAI()` reads a Platform API key from `OPENAI_API_KEY`. When using WIF instead, explicitly pass the short-lived OpenAI access token to the client as a server-runtime credential. Do not put a ChatGPT/Codex OAuth access token in this variable.
2. **`openclaw models auth login --provider openai` defaults to Codex OAuth.** OpenClaw's `openai` provider contains both API-key and ChatGPT/Codex OAuth profiles. Without `--method`, the command intends a ChatGPT/Codex login. To add a Platform key, explicitly select `--method api-key` or `paste-api-key`. [OpenClaw Models](https://docs.openclaw.ai/cli/models)

## 1. Why this page's Python examples must use Platform credentials

The following form from page 09 is a **direct Platform API** call:

```python
from openai import OpenAI  # Import the Python client that calls the OpenAI Platform API directly.

client = OpenAI()  # Read a Platform API key from OPENAI_API_KEY, not a Codex OAuth profile.
response = client.responses.create(  # Send a request to the standard Platform Responses endpoint.
    model="<Platform model verified and allowed for this project>",  # Use a model identifier verified and authorized for this Platform project.
    input="Explain API authentication in three sentences.",  # Supply the current user task.
)
print(response.output_text)  # Read the final-text convenience property supplied by the SDK.
```

This client targets the Responses endpoint at `api.openai.com`. Official documentation specifies a Platform API key or a short-lived OpenAI access token obtained through WIF; it does not list ChatGPT/Codex OAuth as a standard Responses API authentication option. [API Authentication](https://developers.openai.com/api/reference/overview#authentication)

A safe local learning configuration is:

```powershell
# Inject a Platform-project key supplied by a secret manager only into the current PowerShell session; the placeholder is not a usable key.
$env:OPENAI_API_KEY = "<Platform project API key from secret manager>"  # Read only by the Platform SDK in this terminal; never put it in a persistent file.
$env:OPENAI_MODEL = "<Platform model allowed by this project>"  # Centralize runtime model selection instead of scattering it through business code.

# Do not put a ChatGPT/Codex OAuth access token into OPENAI_API_KEY.
# Do not put real values into .ps1 files, real configuration, Markdown, Git, or frontend code; .env.example may contain only placeholders.
```

### WIF is Platform API without a long-lived key, not a third plan

The workload identity federation flow is: a trusted identity provider describes an external identity -> a service-account mapping authorizes particular identity attributes for one OpenAI project -> the workload exchanges an external subject token -> it receives a **short-lived OpenAI access token** -> that token calls the standard API as a Bearer credential. [How WIF works](https://developers.openai.com/api/docs/guides/workload-identity-federation#how-it-works)

It solves “a production workload must not store a long-lived API key,” not “a user's ChatGPT subscription can call the Python SDK.” The following shows only the SDK's **injection point**. A controlled workload-identity component, not business prompts or a frontend, must exchange, cache, and refresh the short-lived token:

```python
import os  # Read a short-lived workload-identity token and model configuration from the controlled runtime environment.

from openai import OpenAI  # Import the same Platform SDK; the caller supplies authentication material explicitly.

# This must be a short-lived OpenAI access token just obtained through WIF on the server; do not log, print, or commit it.
client = OpenAI(api_key=os.environ["OPENAI_WIF_ACCESS_TOKEN"])  # Use the short-lived WIF access token as this process's Bearer credential.

response = client.responses.create(  # Still send a standard Platform request through the Responses API.
    model=os.environ["OPENAI_MODEL"],  # Read a project-allowed model from controlled configuration.
    input="This is a Platform API call made through workload identity.",  # Supply the user input for this turn.
)
```

At the HTTP layer, both an API key and this short-lived token use `Authorization: Bearer ...`, but they have different issuers, rotation mechanisms, and runtime scenarios. WIF requires an organization owner to configure an identity provider and service-account mapping in advance. It fits controlled cloud workloads or private CI, not delivery of tokens to a browser. [How WIF works](https://developers.openai.com/api/docs/guides/workload-identity-federation#how-it-works)

## 2. Why OpenClaw's same `login` command is Codex OAuth

OpenClaw places both authentication mechanisms under the canonical provider ID `openai`, so a matching provider name cannot establish the authentication type. Official CLI documentation states:

```bash
# Default: sign in to ChatGPT/Codex through a browser or device code and obtain an OpenAI Codex OAuth profile.
openclaw models auth login --provider openai  # Create OpenClaw's Codex-login profile through the default OAuth flow.

# Explicit: interactively add an OpenAI Platform API-key profile.
openclaw models auth login --provider openai --method api-key  # Choose Platform API-key authentication explicitly rather than OAuth.

# Inspect profile metadata only; do not print a key or OAuth secret.
openclaw models auth list --provider openai  # Review configured profile metadata and the active authentication choice.
```

The first command uses ChatGPT/Codex OAuth. OpenClaw saves an OAuth profile for each agent and refreshes an expired access token with its refresh token. Treat this token storage as a password: do not copy `auth-profiles.json`, Codex `auth.json`, callback URLs, or browser-login results into a repository, issue, or chat record. [OpenClaw OAuth](https://docs.openclaw.ai/concepts/oauth)

This also explains a common but incorrect inference:

> “I have already logged into `openai` in OpenClaw, so Python `OpenAI()` should be able to call too.”

It does not follow. The OpenClaw login produces an OAuth profile for its supported Codex app-server/OpenClaw bridge. An independent Python process neither automatically reads it nor should read or reuse its refresh token. A direct Python Platform API requires a separately configured Platform API key or WIF.

## 3. Authentication, model name, backend, and runtime are four different layers

During troubleshooting, ask these four questions rather than looking only at whether a model name looks familiar:

| Layer | Question to answer | Example |
| --- | --- | --- |
| **Authentication (auth profile)** | Who pays and is authorized? | Platform API key, WIF short-lived token, ChatGPT/Codex OAuth |
| **Model reference (provider/model)** | Which provider and model are requested? | `openai/<model>` |
| **Actual backend/request routing** | Is the request direct Platform API, Codex app-server, or OpenClaw internal transport? | `api.openai.com/v1/responses`, Codex Responses backend |
| **Agent runtime** | Who owns the agent loop, tool loop, session state, and compaction? | `openclaw` or `codex` |

OpenClaw documentation particularly stresses that provider, model, runtime, and channel are distinct layers. `openai/*` is a canonical model reference, not a switch that “must use an API key” or “must run Codex.” [OpenAI provider](https://docs.openclaw.ai/providers/openai) [Agent runtimes](https://docs.openclaw.ai/concepts/agent-runtimes)

### The same model name does not mean the same path or behavior

Even when `<model>` text is identical, these can be materially different systems:

| Apparent model choice | Credential and backend | Who runs the agent loop | Differences to expect |
| --- | --- | --- | --- |
| Python `model="<model>"` | Platform API key/WIF -> direct Responses API | your Python application | Platform-project billing, project model catalog, and your own history/tool loop/retry |
| OpenClaw `openai/<model>` + Codex OAuth + `agentRuntime: { id: "codex" }` | OAuth -> Codex app-server | Codex | ChatGPT/Codex subscription quota and account model catalog; Codex owns more of thread, tools, and compaction |
| OpenClaw `openai/<model>` + API-key profile + `agentRuntime: { id: "openclaw" }` | Platform key -> OpenClaw direct-provider route | OpenClaw | Platform API billing; OpenClaw owns transcript, tool loop, and context lifecycle |
| OpenClaw `openai/<model>` + OAuth + `agentRuntime: { id: "openclaw" }` | OAuth -> OpenClaw-supported internal Codex-auth transport | OpenClaw | A bridge path chosen for compatibility/explicit policy; OAuth is still not a general Platform API key |

Thus, seeing `openai/<model>` does not prove that capability, context limit, tool semantics, session storage, available catalog, usage attribution, or failure recovery is identical. OpenClaw separately tracks subscription and direct-API-key catalogs; a model in one catalog can be suppressed or unavailable through another route. [OpenAI provider](https://docs.openclaw.ai/providers/openai)

## 4. How `agentRuntime: openclaw`, `codex`, and `auto` select the actual runtime

Runtime decides only who runs the agent loop; it does not substitute for authentication selection. OpenClaw resolves in this order: **exact model policy -> provider policy -> `auto` claim by a registered harness -> fallback to `openclaw` when there is no match**. An old runtime pin on an entire agent or session no longer participates in selection. Use provider/model-scoped `agentRuntime`, and use `openclaw doctor --fix` to clear legacy configuration. [Agent runtimes](https://docs.openclaw.ai/concepts/agent-runtimes)

| Runtime setting | Actual meaning | Strictness and use case |
| --- | --- | --- |
| `id: "codex"` | Force the bundled Codex harness / Codex app-server to execute embedded agent turns | **fail closed**: do not silently switch to OpenClaw when the harness is absent, routing is incompatible, or it fails. Use where the Codex path must be verified. |
| `id: "openclaw"` | Force the built-in OpenClaw embedded runtime | OpenClaw owns model loop, canonical transcript, dynamic tools, and most context lifecycle. It can use an API-key profile; with an OAuth profile, it uses the explicitly supported Codex-auth transport. |
| `id: "auto"` or unset | Let a registered harness claim a compatible route; fall back to OpenClaw otherwise | A Codex harness can be selected implicitly for a qualifying official HTTPS OpenAI agent route. Custom endpoints, explicit Completions adapters, and custom request overrides that do not qualify remain in OpenClaw. Do not read `auto` as “always Codex.” |

The following three examples contain **no keys**. They demonstrate only runtime policy; establish authentication separately through the preceding commands.

```json5
// Option A: require the Codex app-server. Matching OpenAI provider turns use Codex; failure raises an error.
{
  plugins: { entries: { codex: { enabled: true } } }, // Enable the bundled Codex-harness plugin.
  models: { // Configure provider-level model-routing policy.
    providers: { // Enter provider-specific configuration.
      openai: { agentRuntime: { id: "codex" } }, // Force Codex runtime for the OpenAI provider.
    },
  },
  agents: { defaults: { model: { primary: "openai/<Codex account-visible model>" } } }, // Select a model reference visible to the current Codex account.
}
```

```json5
// Option B: explicitly make OpenClaw run the agent loop. It can use a Platform API-key profile and API usage billing.
{
  models: { // Configure provider-level model-routing policy.
    providers: { // Enter provider-specific configuration.
      openai: { agentRuntime: { id: "openclaw" } }, // Force OpenClaw itself to maintain agent loop and context.
    },
  },
  agents: { defaults: { model: { primary: "openai/<Platform project-visible model>" } } }, // Select a model reference authorized for this Platform project.
}
```

```json5
// Option C: auto. Only on a compatible effective route may a registered Codex harness claim the turn; OpenClaw runs it otherwise.
{
  plugins: { entries: { codex: { enabled: true } } }, // Provide a Codex harness claimable by auto policy.
  agents: { defaults: { model: { primary: "openai/<model>" } } }, // Set only the model reference and do not force one runtime.
}
```

An exact model policy takes precedence over a provider-wide policy. To send only one model through Codex while leaving other `openai/*` models in OpenClaw, put `agentRuntime` on that model's model-scoped entry instead of configuring the entire `openai` provider. [OpenClaw agent configuration](https://docs.openclaw.ai/gateway/config-agents)

## 5. Capabilities that cannot use Codex OAuth as a Platform API key

Do not exchange OAuth access tokens and API keys merely because both can appear as Bearer credentials. ChatGPT/Codex OAuth is **not** a general credential for the public Platform API. Choose a Platform API key, or WIF for controlled production workloads, for these needs:

- **Direct standard Python/Node/HTTP API calls**: for example `OpenAI().responses.create(...)`, `GET /v1/models`, and application-directed Platform REST resources such as files, vector stores, batches, and fine-tuning. Platform API documentation defines its authentication boundary only for API keys/WIF short-lived tokens.
- **Independent services, CI/CD, scheduled jobs, and multi-instance backends**: these need a machine identity that can be rotated, revoked, budgeted, and audited by project. Configure WIF if you do not want a long-lived key; do not plant a personal OAuth refresh token in a runner.
- **Automation for Platform project billing, limits, model availability, and Admin/organization APIs**: these are Platform organization/project governance; having a ChatGPT subscription is not a substitute for project API permission.
- **Any OpenAI-compatible base URL or third-party proxy**: OAuth is not a bearer secret that can be forwarded arbitrarily to any endpoint. Send a Platform key only to a verified Platform endpoint, or use the authentication the proxy explicitly specifies.

One important qualification applies: OpenClaw can bridge Codex OAuth for **surfaces it explicitly implements**. For example, its current OpenAI-provider documentation lists image generation/editing through the Codex Responses backend. That is a supported OpenClaw integration. It does not mean OAuth can call arbitrary `/v1/*` endpoints, nor does it extend to an independent Python SDK. [OpenClaw OpenAI image route](https://docs.openclaw.ai/providers/openai)

## 6. Choose by calling objective, not model name

| Your goal | Preferred authentication and runtime | Why |
| --- | --- | --- |
| Use Responses API, File Search, or your own function tools in a Python service | Platform API key; WIF for a production cloud workload | a standard, auditable Platform API contract consistent with page 09 examples |
| Kubernetes, cloud functions, or private CI without a long-lived static key | WIF short-lived token | identity binds to workload/service account rather than placing an API key in a deployment secret |
| Run an OpenClaw agent with an existing ChatGPT/Codex subscription | `models auth login --provider openai` plus `codex`, or `auto` on an eligible route | OAuth and Codex app-server form the corresponding account-based path |
| Keep Platform-project billing in OpenClaw while OpenClaw owns the agent loop | OpenAI API-key profile plus `agentRuntime: { id: "openclaw" }` | authentication, billing, and runtime are all explicit and easy to troubleshoot |
| Require OAuth in OpenClaw while intentionally keeping its own loop/tool behavior | Codex OAuth profile plus `agentRuntime: { id: "openclaw" }` | an explicitly supported bridge; test tool, context, and session semantics rather than assuming they match Codex runtime |

When a login works but a call fails, identically named models behave differently, or usage appears in the wrong place, inspect in this order:

1. Is this Platform API, Codex app-server, or OpenClaw embedded runtime?
2. Is the agent currently using an API-key profile, OAuth profile, or a WIF server token?
3. Is the effective policy model-scoped, provider-scoped, or `auto` runtime?
4. Does the account/project actually expose this model and capability in the **corresponding catalog**?

Start with diagnostic commands that do not expose credentials:

```bash
openclaw models status  # View aggregate diagnostics for model, provider, authentication, and runtime.
openclaw models auth list --provider openai  # List only OpenAI profile metadata, never authentication secrets.
openclaw config get agents.defaults.model --json  # Inspect effective configuration for the agent's default model reference.
openclaw config get models.providers.openai.agentRuntime --json  # Inspect the actual OpenAI-provider runtime policy.
```

## 7. Minimum security checklist

- API keys, WIF access tokens, OAuth access tokens, and refresh tokens are all secrets. Do not print them, paste them into Markdown, commit them to Git, put them in a browser frontend, or forward them through chat.
- Production services should prefer a secret manager. Use WIF when long-lived API keys must be eliminated; do not substitute copied personal OAuth profiles for a machine identity.
- Give every OpenClaw agent an explicit auth profile and necessary `auth.order`. After changing OAuth login, recheck `models auth list` and runtime rather than guessing which token is active.
- Pinning a model reference does not pin behavior. After upgrading OpenClaw, Codex app-server, model catalogs, or provider configuration, revalidate runtime, tools, context limits, billing path, and failure recovery.
- For automated work, prefer a Platform API key/WIF. Codex documentation also treats an API key as the default for shared automated environments, while ChatGPT/Codex access tokens are only for trusted automated environments. [Codex Authentication](https://learn.chatgpt.com/docs/auth)

## Primary references

- [OpenAI: API Overview — Authentication](https://developers.openai.com/api/reference/overview#authentication) (accessed 2026-07-22)
- [OpenAI: Workload Identity Federation — How it works](https://developers.openai.com/api/docs/guides/workload-identity-federation#how-it-works) (accessed 2026-07-22)
- [OpenAI Codex: Authentication](https://learn.chatgpt.com/docs/auth) (accessed 2026-07-22)
- [OpenClaw: OpenAI provider](https://docs.openclaw.ai/providers/openai) (accessed 2026-07-22)
- [OpenClaw: Agent runtimes](https://docs.openclaw.ai/concepts/agent-runtimes) (accessed 2026-07-22)
- [OpenClaw: Models CLI](https://docs.openclaw.ai/cli/models) (accessed 2026-07-22)
- [OpenClaw: OAuth](https://docs.openclaw.ai/concepts/oauth) (accessed 2026-07-22)
- [OpenClaw: Agent configuration](https://docs.openclaw.ai/gateway/config-agents) (accessed 2026-07-22)
