---
title: "Agent Tool Function Design"
tags: [ ai-agent-engineer, Python, tools, agent ]
aliases: [ Python Agent tool contracts, tool-function design ]
lang: en
translation_key: "Python基础/Agent工程路线/03-并发与交付/10-Agent工具函数设计.md"
translation_source_hash: a59817a297854fa7c195a610ccee3726cd9d25cf0fb8485e4b986beba68d1dd0
translation_route: zh-CN/Python基础/Agent工程路线/03-并发与交付/10-Agent工具函数设计
translation_default_route: zh-CN/Python基础/Agent工程路线/03-并发与交付/10-Agent工具函数设计
---

# Agent Tool Function Design

## Objective

Elevate an ordinary Python function into a tool boundary an Agent can call safely: inputs are narrow and validatable; side effects and permissions are explicit; outputs are stable and parseable; failures are recoverable or escalatable; and the complete boundary is testable without calling a real model.

## A tool is not “expose every function to the model”

A model proposes a call; the application still validates, authorizes, executes, and records it. A tool contract includes at least:

```text
Name and purpose
├─ input schema; length, enum, and format limits
├─ pre-call authorization and business conditions
├─ explicit read, write, and network side effects
├─ timeout, concurrency, idempotency, and retry semantics
├─ stable result and error categories
└─ audit fields, human approval, and stop conditions
```

Python type hints help developers and tool generators understand structure, but they do not perform runtime validation automatically. JSON Schema or an SDK declaration is also only the first gate; before execution, still check paths, resource ownership, current identity, size limits, and business state.

## Start with a narrow function

“Manage files” is too broad. “Read one UTF-8 text file inside the workspace, up to 64 KiB” is easier to authorize and test:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ReadTextResult:
    relative_path: str
    content: str
    size_bytes: int


class ToolInputError(ValueError):
    pass


def read_workspace_text(
    relative_path: str,
    *,
    workspace: Path,
    max_bytes: int = 65_536,
) -> ReadTextResult:
    if max_bytes < 1:
        raise ToolInputError("max_bytes must be at least 1")
    if not relative_path or Path(relative_path).is_absolute():
        raise ToolInputError("a workspace-relative path is required")

    root = workspace.resolve(strict=True)
    candidate = (root / relative_path).resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ToolInputError("path escapes the workspace") from exc

    if not candidate.is_file():
        raise ToolInputError("target must be a regular file")
    size = candidate.stat().st_size
    if size > max_bytes:
        raise ToolInputError("file exceeds the read limit")
    return ReadTextResult(
        relative_path=candidate.relative_to(root).as_posix(),
        content=candidate.read_text(encoding="utf-8"),
        size_bytes=size,
    )
```

This example is still not a general security sandbox. Windows reparse points, permission changes, time-of-check/time-of-use replacement, and special files need stronger operating-system isolation. The key lesson is not to mistake a string-prefix comparison for reliable path authorization.

## Separate the pure core from execution adapters

A recommended data flow is:

```text
Model/workflow proposal
  → schema validation
  → business and authorization validation
  → human approval when needed
  → restricted Python adapter executes
  → stable result envelope
  → logs / metrics / trace
```

Keep parsing and decisions as pure functions where possible. Concentrate files, networks, databases, and command execution in small adapters. That lets policy be tested with fake adapters without allowing unit tests to touch the real system.

## Use stable results, not arbitrary strings

Tool output should let a caller distinguish success, correctable input, a temporary failure, and human intervention:

```python
from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ToolResult(Generic[T]):
    status: Literal["ok", "invalid_input", "temporary_failure", "denied"]
    data: T | None = None
    message: str | None = None
    retryable: bool = False
```

A real system can use an SDK-defined result shape rather than this class. Whatever the format, keep error categories stable and content minimal, excluding stacks, keys, and complete service responses. Retain detailed causes in controlled logs and correlate them with a non-personal operation ID.

## Side effects, idempotency, and authorization

Every tool should answer:

- Is it read-only or does it write? Where does it write?
- Does a repeated call produce the same result, overwrite, create duplicate records, or make an irreversible change?
- Which parameters are proposed by the model, and which are injected by a trusted application?
- Where are caller identity and resource ownership verified?
- Does it need preview, confirmation, dual approval, or compensating actions?

Do not let a model supply `workspace`, database connections, API keys, or maximum privilege. Configure and inject those through the application. For high-risk writes, use least privilege, allowlists, and approval; a prompt is not an enforceable control.

## Test matrix

Cover at least:

| Dimension | Example |
| --- | --- |
| Valid input | Smallest file, Unicode, upper boundary |
| Invalid input | Empty path, absolute path, escape path, oversized file |
| Authorization | Unauthorized resource, revoked authorization, denied approval |
| Fault | Missing file, timeout, transient dependency failure |
| Repetition | Same idempotency key, repeated execution, retry after partial success |
| Cancellation | Before execution, during execution, before a write |
| Observability | Error category and `operation_id` exist; logs have no secret |

The Tool Calling course covers how a protocol declares schemas, how a model proposes a call, and how an application returns results. This lesson builds only the Python execution boundary that such a protocol invokes.

## Exercises

1. Implement `read_workspace_text` above, using a temporary directory to test a valid file, escape, oversize, and nonexistent file.
2. Write the side-effect declaration, idempotency key, and human-approval condition for a “create ticket” tool without making a network call.
3. Change a function that returns free-text errors into stable error categories; state which content goes to logs and which returns to the model.
4. Draw trust boundaries from model proposal to real execution and identify who controls each layer.

## Self-check

- [ ] I can explain why Python type hints cannot replace runtime validation.
- [ ] I can separate trusted dependencies such as paths, connections, and keys from model parameters.
- [ ] I can make a tool's permission, side-effect, idempotency, timeout, and approval semantics explicit.
- [ ] I can design stable success and failure results without leaking internals.
- [ ] I can test the execution boundary without a model or a real external service.

## Related concepts and next step

- Prerequisite: [[python-fundamentals/engineering-route/03-concurrency-and-delivery/09-project-layout-cli-and-reproducible-runs|Project Layout, CLI, and Reproducible Runs]].
- Next, [[python-fundamentals/engineering-route/04-project-and-self-assessment/11-project-reliable-task-queue|Project: Reliable Task Queue]].
- See the JSON course, [[tool-calling-function-calling/00-index|Tool Calling]], and MCP for protocols and schemas.
- The Agent Core course covers planning, memory, stopping, and authorization loops.

## References

Retrieved on **2026-07-14**.

- [Python: `typing`](https://docs.python.org/3.14/library/typing.html)
- [Python: `pathlib`](https://docs.python.org/3.14/library/pathlib.html)
- [OWASP: Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal)
- [NIST AI RMF Generative AI Profile](https://doi.org/10.6028/NIST.AI.600-1)
