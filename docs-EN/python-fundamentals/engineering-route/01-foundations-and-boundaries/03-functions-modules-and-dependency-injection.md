---
title: "Functions, Modules, and Dependency Injection"
tags: [ ai-agent-engineer, Python, design ]
aliases: [ Python function boundaries, Python dependency injection ]
lang: en
translation_key: "Python基础/Agent工程路线/01-基础与边界/03-函数模块与依赖注入.md"
translation_source_hash: 5c918ea5edb0e974e56ce11853b84c47ad84f1c12b58b57e847a759703804136
translation_route: zh-CN/Python基础/Agent工程路线/01-基础与边界/03-函数模块与依赖注入
translation_default_route: zh-CN/Python基础/Agent工程路线/01-基础与边界/03-函数模块与依赖注入
---

# Functions, Modules, and Dependency Injection

## Objective

By the end of this lesson, you should be able to use small functions to separate parsing, business calculations, and side effects; organize code into importable modules; and inject clocks, network clients, or storage through explicit parameters instead of hiding global calls in core logic.

## A function is the smallest contract

An engineering function should let a reader see at least:

- what its inputs are and whether they are validated;
- what it returns;
- which business-relevant exceptions it can raise;
- whether it reads files, makes network calls, writes state, or reads environment variables; and
- whether repeated calls create additional side effects.

```python
def unfinished_ids(tasks: list[Task]) -> list[str]:
    return [task.task_id for task in tasks if task.status != "done"]
```

This is a pure function: its result depends only on its inputs and it has no hidden I/O. Purity is not a moral requirement; it makes testing, caching, concurrency, and reuse easier.

## Functional core, imperative shell

You can divide a program as follows:

```text
Imperative shell: read files / call APIs / read the clock / write logs
       ↓ convert to validated objects
Functional core: calculate, decide, sort, summarize
       ↓ return an explicit result or error
Imperative shell: write files / call tools / emit output
```

Do not make one function read a file, parse JSON, call a model, modify a database, and print a result. Failures become difficult to locate and tests must assemble every dependency.

## Positional arguments, keyword arguments, and defaults

```python
def search(
    query: str,
    *,
    limit: int = 5,
    include_archived: bool = False,
) -> list[Result]:
    ...
```

`*` makes later arguments keyword-only: `search("RAG", limit=10)` is clearer than `search("RAG", 10, False)`. Defaults should be immutable values; do not use a mutable list or dictionary as a default argument.

## Modules and entry points

A module is an importable `.py` file. A testable module should not perform real work merely because it is imported:

```python
def main() -> int:
    # Parse CLI arguments, invoke application functions, and return an exit code.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Tests can import functions without triggering a command line, network access, or file writes. Reading secrets, constructing clients, or starting background tasks at import time makes tests and tool discovery unpredictable.

## Explicit dependency injection

**Dependency injection** simply supplies an external capability as a parameter instead of hard-coding its creation inside a function. Its smallest form can be a callable:

```python
from collections.abc import Callable


def with_retry(
    operation: Callable[[], str],
    *,
    attempts: int,
    sleep: Callable[[float], None],
) -> str:
    ...
```

Production code injects real `time.sleep` and API calls; tests inject a fake operation that records calls and a non-waiting `sleep`. This is more reliable than changing global objects or actually making network calls in tests.

When a dependency is more complex, use a `Protocol` to describe the required methods:

```python
from typing import Protocol


class NoteStore(Protocol):
    def search(self, query: str, limit: int) -> list[str]: ...


def answer(store: NoteStore, query: str) -> list[str]:
    return store.search(query, limit=5)
```

The caller depends on the smallest capability rather than on a particular database or SDK class.

## Return an error or raise an exception?

- For an expected branch such as “no matches,” return an empty collection or an explicit result type.
- For invalid input or an unavailable dependency that cannot continue on the normal path, raise a specific exception.
- Do not simultaneously return `None`, print an error, and raise an exception; callers will not know which behavior is the interface.

Public functions should document exception semantics, but should not expose raw vendor exceptions, secrets, or full requests to a model or user.

## Suggested module boundaries

For a small project, start with this division:

```text
app/
├── models.py       # Validated objects and result types
├── parsing.py      # External data → internal objects
├── service.py      # Pure business use cases
├── adapters.py     # File/API/database boundaries
└── cli.py          # Arguments, output, and exit codes
tests/
```

Not every project needs these files. Split according to reasons for change and side-effect boundaries, not in pursuit of more directories.

## Common mistakes

- Reading environment variables and constructing real clients at module top level.
- Adding a large abstraction layer “for testability” without a second implementation or a clear boundary.
- Catching every exception and returning an empty list so a dependency failure looks like “no results.”
- Sharing mutable state through global variables.
- Letting `main()` omit an exit code, so a failed CLI still reports success.

## Exercise

Split “read task JSON → validate → summarize → write a report” into at least four functions. Mark pure functions, I/O functions, exception boundaries, and the side effects of repeated execution. Then inject “the current time” as a parameter or callable dependency to prove that tests do not depend on a real clock.

## Self-check

1. Why are pure functions easier to test?
2. Why should importing a module not perform real work?
3. Does dependency injection require a framework or container?
4. Should a `Protocol` describe an entire vendor SDK or the smallest required capability?
5. Why cannot an empty result and a dependency failure both return `[]`?

## Related concepts and next step

- Tool contracts and authorization are covered in [[tool-calling-function-calling/00-index|Tool Calling]]; this lesson focuses only on Python interface testability.
- Next, [[python-fundamentals/engineering-route/01-foundations-and-boundaries/04-files-json-and-input-validation|Files, JSON, and Input Validation]] implements the boundary from untrusted data to internal objects.

## References

Retrieved on **2026-07-14**.

- [Defining Python functions](https://docs.python.org/3.14/tutorial/controlflow.html#defining-functions)
- [Python modules](https://docs.python.org/3.14/tutorial/modules.html)
- [Python `typing.Protocol`](https://docs.python.org/3.14/library/typing.html#typing.Protocol)
- [Python `collections.abc`](https://docs.python.org/3.14/library/collections.abc.html)
