---
title: "Environment, Dependencies, and Secret Management"
tags:
  - llm-api
  - python
  - secrets
aliases:
  - LLM Development Environment
source_checked: 2026-07-21
source_baseline:
  - Python venv documentation
  - Python Packaging User Guide
  - Official OpenAI, Anthropic, and Google Python SDK documentation
content_origin: original
content_status: dynamic
lang: en
translation_key: LLM API集成/01-环境、依赖与密钥管理.md
translation_source_hash: 034cf9f70aea60fdf15afabb24a9aec356e683b377eda0ff4c52266677733509
translation_route: zh-CN/LLM-API集成/01-环境、依赖与密钥管理
translation_default_route: zh-CN/LLM-API集成/01-环境、依赖与密钥管理
---

# Environment, Dependencies, and Secret Management

## Objectives

Set up an isolated environment in Windows 11 and PowerShell 7, understand dependency pinning and secret boundaries, and never write real credentials into code, notes, or logs.

## Start with `venv + pip`

```powershell
$lab = Join-Path $HOME "projects\llm-api-lab"  # Choose a practice directory outside the vault so the environment and caches do not enter the knowledge base.
New-Item -ItemType Directory -Path $lab -Force | Out-Null  # Create the directory if absent and suppress unrelated output.
Set-Location $lab  # Switch to the practice directory so .venv belongs only to this lab project.
py -3.11 -m venv .venv  # Create an isolated virtual environment with the course-baseline Python.
.\.venv\Scripts\Activate.ps1  # Activate it so subsequent python and pip commands target .venv.
python -m pip install --upgrade pip  # Upgrade the installer inside the environment to avoid dependency issues caused by older resolvers.
```

The lab directory is deliberately outside the vault so that `.venv`, caches, and SDK artifacts are not committed. Install each provider package according to its **current official Python SDK documentation**, and record the actually verified version in a lockfile. A team should not merely write unbounded `openai`, `anthropic`, or `google-genai` requirements: SDK methods, default endpoints, event types, and retry behavior can change. Before upgrading, at minimum regression-test the adapter, structured output, streaming events, error mapping, and continuation payload. After mastering `venv + pip`, you can evaluate tools such as `uv`; they do not change the principles of isolation, pinning, and verification.

The provider-contract project currently fixes the following **review baselines**. They do not require every project to remain on these versions forever:

| Provider | PyPI package | Common credential entry | Pinned SDK baseline in this course |
| --- | --- | --- | --- |
| OpenAI | `openai` | `OPENAI_API_KEY` | `openai-python 2.46.0` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | `anthropic-python 0.117.0` |
| Google Gemini | `google-genai` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | `google-genai 2.12.1` |

When both Google variables exist, its SDK prefers `GOOGLE_API_KEY`. Do not set both to different values and rely on implicit priority; choose one, record its source, and validate it at startup. The three SDK version sets were rechecked against their official releases on 2026-07-21, but a real project must still rely on its own lockfile and regression results after installation.

## Let secrets enter only through a security boundary

The current PowerShell session can use a placeholder value for demonstration:

```powershell
$env:LLM_API_KEY = "replace-with-a-local-secret"  # Set a placeholder only for this session; real keys must come from a controlled secret manager.
```

Python should only check that the variable exists, never print its value:

```python
import os  # Import the standard library to read a secret variable from the runtime environment.

api_key = os.environ.get("LLM_API_KEY")  # Read the variable without printing it, preventing log disclosure.
if not api_key:  # Confirm that the runtime injected credentials before any real request begins.
    raise RuntimeError("LLM_API_KEY is not configured")  # Fail closed when credentials are absent rather than continuing anonymously or using a wrong default.
```

In production, use the platform secret manager and separate least-privilege credentials for development, test, and production. Browsers, mobile clients, and public desktop applications must not carry long-lived provider keys directly; access providers through a controlled backend or short-lived restricted credentials. Do not place keys in URL query strings, `.env.example`, exception text, screenshots, notebook output, or full HTTP logs. If you use a local `.env`, it must be ignored; example files may contain only variable names and placeholders.

Environment variables solve only how a secret enters the process. They do not automatically solve authorization, rotation, or disclosure. Scope a key to the project/environment that needs it and establish rotation and revocation procedures. If a key enters Git history, stop using it and rotate it under the organizational process; adding `.gitignore` afterward is not enough.

Authentication methods are also dynamic capabilities, so do not treat an API key as the permanent sole option. OpenAI's official Python SDK 2.46.0 supports short-lived workload identity through `workload_identity` and documents Kubernetes service-account tokens, Azure managed identity, and Google Cloud ID-token providers; Anthropic's current authentication documentation likewise presents both API keys and Workload Identity Federation (WIF). The providers' parameters, identity-provider configuration, and organizational authorization are not interchangeable, and must be integrated according to the pinned SDK and platform documentation. In supported managed environments, short-lived workload identity can reduce distribution of long-lived keys.

Google is currently migrating the Gemini API to its Auth key system. As of 2026-07-21, newly created keys are Auth keys by default, and the Gemini API rejects **unrestricted Standard keys**; Standard keys with explicit restrictions may still work temporarily. Google explicitly states that it will reject all Standard keys from **September 2026**, so even restricted Standard keys must migrate to Auth keys before then. Recheck console state and the current migration documentation before launch; do not encode this date as a long-term assumption.

## Configuration layers

- Non-secret configuration: provider identifier, logical model alias, timeout, and maximum attempts can enter version control.
- Secrets: API keys and temporary tokens come only from the environment or a secret service.
- Dynamic limits: pricing, rates, and model availability should be checked through official documentation or a management API rather than scattered among code constants.

Validate configuration at startup. Logs should report only whether fields exist and which non-secret configuration ID is in use.

## Control startup and shutdown as well

Create a client during application startup and explicitly close it at process or worker shutdown. Do not create a new connection pool for every request or rely on interpreter exit to release streams and sockets. The current Python SDKs for all three providers offer synchronous/asynchronous client-lifecycle APIs, but exact names and context-manager usage must follow the pinned version. Use a fake transport or local client in tests; in production, give client lifecycle to the application container and ensure a cancelled stream also leaves its context.

Check for secret presence only on a startup path that actually needs the provider. Offline unit tests, documentation builds, and fixture validation should not fail because a production secret is absent; live integration tests must instead be gated by an explicit switch and independent low-privilege credentials.

## Exercise and self-check

Create a new venv, then write a script that only checks whether `LLM_API_KEY` is configured and prints a Boolean. Close the terminal and confirm the session-scoped environment variable no longer exists. Self-check: does your error-tracking system automatically collect environment variables or request headers? If so, how will you filter them?

## Mastery checklist

- [ ] The virtual environment is outside the vault, dependency versions are reproducible, and upgrades have regression tests.
- [ ] Secrets come only from the environment or a secret manager; code, `.env.example`, logs, and screenshots contain no real values.
- [ ] Development, test, and production credentials are isolated and have least privilege, rotation, and revocation procedures.
- [ ] A startup failure reports only which configuration is missing; it never echoes credentials or authentication headers.
- [ ] Provider clients reuse connection pools and close at shutdown; cancelled streams leave no connection or background task behind.
- [ ] Offline tests do not read secrets; live tests are gated by an explicit switch and independent credentials.
- [ ] I master `venv + pip` before introducing tools such as `uv`, while retaining the same security boundary.

## Next step

Continue to [[llm-api-integration/02-http-sdks-and-request-lifecycle|HTTP, SDKs, and the Request Lifecycle]].

## References

- [Python: venv](https://docs.python.org/3/library/venv.html) (accessed 2026-07-21)
- [Python Packaging User Guide: Installing packages](https://packaging.python.org/en/latest/tutorials/installing-packages/) (accessed 2026-07-21)
- [OpenAI: official Python SDK](https://github.com/openai/openai-python) (API-key and workload-identity authentication, accessed 2026-07-21)
- [Anthropic: Python SDK](https://github.com/anthropics/anthropic-sdk-python) (accessed 2026-07-21)
- [Anthropic: Authentication](https://platform.claude.com/docs/en/manage-claude/authentication) (API key and WIF, accessed 2026-07-21)
- [Google Gen AI SDK for Python](https://github.com/googleapis/python-genai) (accessed 2026-07-21)
- [Google: Using Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key) (environment-variable priority and the 2026 Auth-key migration, accessed 2026-07-21)
