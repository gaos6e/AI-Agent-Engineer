---
title: "Configuration, Logging, and Sensitive Information"
tags: [ ai-agent-engineer, Python, observability, security ]
aliases: [ Python configuration and logging, Python sensitive-data protection ]
lang: en
translation_key: "Python基础/Agent工程路线/02-可靠性与测试/06-配置日志与敏感信息.md"
translation_source_hash: ed3b83305d4249cacac15f6f97616c64c7213d11c8547aa31348ba9781982a6c
translation_route: zh-CN/Python基础/Agent工程路线/02-可靠性与测试/06-配置日志与敏感信息
translation_default_route: zh-CN/Python基础/Agent工程路线/02-可靠性与测试/06-配置日志与敏感信息
---

# Configuration, Logging, and Sensitive Information

## Objective

Separate values that vary by environment from code, validate configuration at startup, and produce log evidence so an Agent tool call can be located, correlated, and reviewed—without recording keys, complete prompts, or unnecessary personal data.

## Configuration is not scattered global state

Configuration answers “how does this same code run in this environment?” Examples include timeouts, concurrency limits, service addresses, and feature flags. Business input answers “what should this one invocation process?” A secret is protected configuration, but it must not enter the repository.

Precedence must be explicit, for example:

```text
Safe defaults in code < configuration file < environment variables < explicit CLI arguments
```

Not every project needs all four layers. The important point is one centralized parsing entry point that produces a validated object once at startup:

```python
import os
from dataclasses import dataclass, field


class ConfigError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Settings:
    request_timeout_seconds: float
    max_concurrency: int
    api_key: str = field(repr=False)


def load_settings(environ: dict[str, str] | None = None) -> Settings:
    source = os.environ if environ is None else environ
    api_key = source.get("EXAMPLE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("EXAMPLE_API_KEY is required")
    try:
        timeout = float(source.get("REQUEST_TIMEOUT_SECONDS", "20"))
        concurrency = int(source.get("MAX_CONCURRENCY", "4"))
    except ValueError as exc:
        raise ConfigError("timeout and concurrency must be numbers") from exc
    if not 0 < timeout <= 120:
        raise ConfigError("REQUEST_TIMEOUT_SECONDS must be in (0, 120]")
    if not 1 <= concurrency <= 32:
        raise ConfigError("MAX_CONCURRENCY must be in [1, 32]")
    return Settings(timeout, concurrency, api_key)
```

Taking `environ` as a parameter lets tests pass a fake dictionary without polluting the real process environment.

`repr=False` reduces the chance of displaying a key in debugging output, but it is not a security boundary: the value can still be read, serialized, or logged elsewhere. Higher-risk systems should use a dedicated secret provider and prevent secret objects from entering general configuration printing, exception, and telemetry paths.

## Secrets receive placeholder instructions only

A repository can include `.env.example`, but it must contain only variable names and invalid placeholders:

```dotenv
EXAMPLE_API_KEY=replace-with-your-own-key
REQUEST_TIMEOUT_SECONDS=20
MAX_CONCURRENCY=4
```

Real `.env` files, tokens, cookies, and service-account files must not enter the vault or Git. In production, prefer the platform secret-management service and constrain who can read a secret, why, and for how long. Once a secret enters Git history, a new `.gitignore` entry cannot eliminate the leak; stop the submission, revoke or rotate the credential, and handle history only with authorization.

## Logs and user output are separate channels

- **User output**: task results or actionable failure guidance.
- **Diagnostic logs**: time, level, event, correlation ID, duration, and stable error category.
- **Metrics**: aggregable counts and distributions.
- **Trace**: the causal path of one request across steps or services.

Library modules should only obtain a logger and emit records; the application entry point configures handlers and levels:

```python
import logging

logger = logging.getLogger(__name__)


def run_task(task_id: str) -> None:
    # process and KnownDependencyError are defined by the application's execution adapter.
    logger.info("task_started task_id=%s", task_id)
    try:
        process(task_id)
    except KnownDependencyError:
        logger.exception("task_failed task_id=%s category=dependency", task_id)
        raise
    else:
        logger.info("task_completed task_id=%s", task_id)
```

`logger.info("count=%d", count)` uses deferred formatting, so do not construct an expensive string just for logging. Use `logger.exception()` in an exception context; it automatically includes the stack trace.

An entry-point configuration example:

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
```

`basicConfig()` may do nothing when the root logger already has a handler. Configure it once in the application; reusable libraries must not call it on their own. When production uses JSON logs, an audited logging adapter should encode them consistently instead of hand-building strings that merely look like JSON.

## What to record and what to avoid

Recommended fields:

- `trace_id` / `operation_id` to connect one operation;
- a stable event name and error category;
- stage, attempt count, duration, and input/output sizes;
- non-sensitive version identifiers for models, tools, or configuration; and
- whether caching, degradation, or human approval was used.

Do not log by default:

- API keys, Authorization headers, cookies, or connection strings;
- complete prompts, model replies, uploaded documents, or user private data;
- local absolute paths, raw database records, or complete external-error bodies; or
- any data that “might be useful later” without a diagnostic purpose.

When the business genuinely needs content-level audit, define purpose, minimum fields, redaction, access controls, retention period, and deletion procedure first. String-replacement “redaction” cannot guarantee coverage of nested objects, encoded values, or new fields; use allowlists at the structured-data layer instead.

## Correlation IDs are not idempotency keys

A `trace_id` observes one execution; an idempotency key lets a service recognize a repeated business request. They may appear together, but are not interchangeable. A correlation ID should not directly use an email address, national ID, or other personal information either.

## Common mistakes

| Mistake | Consequence | Improvement |
| --- | --- | --- |
| Read all environment variables during module import | Testing and reuse are difficult | Load explicitly at the application-start boundary |
| Silently use a dangerous default when configuration is missing | Behavior is unpredictable | Fail at startup and name the variable |
| Log a complete request object | Credentials and personal data leak | Use a field allowlist and minimize data |
| Use `print` instead of diagnostic logging | No levels, timestamps, or correlation context | Logs are for diagnosis; stdout is for results |
| Re-log the same stack in every layer | Noise and cost increase | Log where there is context and handling responsibility |

## Exercises

1. Write four tests for `load_settings()`: success, missing secret, invalid timeout, and out-of-range concurrency.
2. Design a tool-log event: list allowed fields, prohibited fields, and retention period.
3. Add `--verbose` to the task-queue project without changing JSON standard output; decide whether logs belong on stdout or stderr.
4. Write a field-allowlist transformation for nested dictionaries and prove that a new unknown field is not logged automatically.

## Self-check

- [ ] I can distinguish business input, non-sensitive configuration, and secrets.
- [ ] I can explain why configuration should be centrally validated at startup.
- [ ] I can distinguish results, logs, metrics, and traces.
- [ ] I can design correlation fields that do not expose content.
- [ ] I know that `.gitignore` cannot fix a credential already tracked by Git.

## Related concepts and next step

- Prerequisite: [[python-fundamentals/engineering-route/02-reliability-and-testing/05-exceptions-timeouts-retries-and-resource-management|Exceptions, Timeouts, Retries, and Resource Management]].
- Next, [[python-fundamentals/engineering-route/02-reliability-and-testing/07-unit-testing-mocks-and-regression|Unit Testing, Mocks, and Regression]] verifies those contracts.
- Production logging and alerts belong to the observability course; privacy boundaries belong to AI Safety and Privacy Computing.

## References

Retrieved on **2026-07-14**.

- [Python: `logging`](https://docs.python.org/3.14/library/logging.html)
- [Python: `os.environ`](https://docs.python.org/3.14/library/os.html#os.environ)
- [OWASP: Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
