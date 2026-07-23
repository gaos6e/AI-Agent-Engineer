---
title: "Exceptions, Timeouts, Retries, and Resource Management"
tags: [ ai-agent-engineer, Python, reliability ]
aliases: [ Python reliability boundaries, controlled retries ]
lang: en
translation_key: "Python基础/Agent工程路线/02-可靠性与测试/05-异常超时重试与资源管理.md"
translation_source_hash: 010a675ee022420efbde038bf48dbe5432e1f6a3e46a057629114bee0e32ae77
translation_route: zh-CN/Python基础/Agent工程路线/02-可靠性与测试/05-异常超时重试与资源管理
translation_default_route: zh-CN/Python基础/Agent工程路线/02-可靠性与测试/05-异常超时重试与资源管理
---

# Exceptions, Timeouts, Retries, and Resource Management

## Objective

Treat failure as part of an interface: distinguish failure types, set a total time budget, retry only operations that may recover and may be repeated, and ensure that files, connections, and tasks are cleaned up after both success and failure.

## Draw failure boundaries first

An Agent tool does not end with “call one function.” One operation can validate input, read a local file, call an external service, parse a result, and persist output. Each layer should handle only exceptions it can genuinely recover from.

| Failure type | Example | Usual handling |
| --- | --- | --- |
| Input/contract error | Missing field or forbidden status | Reject immediately and tell the caller how to correct it |
| Transient external failure | Brief connection interruption or temporarily unavailable service | Retry a bounded number of times when retry conditions hold |
| Permanent external failure | Unauthorized access, missing resource, invalid parameter | Do not retry; return a stable error category |
| Program defect | Uncovered state or failed assertion | Preserve evidence and fail; do not disguise it as invalid input |
| Cancellation / exhausted total deadline | User stops or an upstream deadline expires | Propagate promptly and clean up resources |

Exception classes should express an action a caller can take, not just a lower-level library name:

```python
class TaskError(Exception):
    """Base class for task-processing failures."""


class InvalidTask(TaskError):
    """Can succeed only after the caller corrects the input."""


class TemporaryDependencyFailure(TaskError):
    """A transient external dependency failure that may permit a retry."""
```

Preserve the causal chain when translating an exception:

```python
try:
    text = path.read_text(encoding="utf-8")
except OSError as exc:
    raise TaskError(f"unable to read input file: {path.name}") from exc
```

`raise ... from exc` retains the root cause in logs, while a user-facing message can still conceal local absolute paths or sensitive responses.

## Keep `try` scopes small

Wrap only a statement you expect to fail. A broad scope can misclassify your own bug as a recoverable error.

```python
try:
    raw = path.read_text(encoding="utf-8")
except FileNotFoundError as exc:
    raise InvalidTask("input file does not exist") from exc
else:
    return parse_document(raw)  # A parsing defect is not mistaken for a missing file.
```

- `except`: catch only a specific exception you can explain or recover from.
- `else`: run only when no exception occurred.
- `finally`: perform cleanup required on success and failure alike.
- Context managers `with` / `async with`: prefer these for files, locks, connections, and temporary resources.

Do not use `except Exception: pass`. If a top level catches a broad exception to produce a uniform error response, it must still record the cause, return a failure state, and make the failure visible to monitoring.

## A timeout is a budget, not a string of unrelated numbers

A connection timeout, a per-request timeout, and the total deadline for a task are different. If every retry receives a fresh full timeout, three “10-second requests” plus backoff can make a user wait far longer than intended.

Define a total budget first, then allocate its remaining time to each step:

```text
20-second total task deadline
├─ input validation ≤ 1 second
├─ external call, including all retries ≤ 15 seconds
└─ reserve 4 seconds for parsing, writing, and cleanup
```

The standard library has no universal safe switch that forcibly interrupts an arbitrary synchronous function. Real network, database, or SDK calls must use their explicit timeout parameters; use `asyncio.timeout()` for asynchronous code. Do not assume `Future.result(timeout=...)` automatically terminates blocking background work.

## When retries are allowed

Retry only when all of these conditions hold:

1. The failure is explicitly classified as transient.
2. The operation is idempotent, or an idempotency key prevents duplicate side effects.
3. The maximum attempts and total deadline have not been exceeded.
4. The upstream has not canceled the work.
5. Every failure is observable and the final result preserves the last cause.

Reading is usually safer to retry than “charge a card, send an email, or create a ticket.” Even if a client sees a timeout, the server may have completed the latter operations; a blind retry without an idempotency key can duplicate work.

This is a testable synchronous retry skeleton. `sleep` is injected, so tests need not actually wait:

```python
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry_transient(
    operation: Callable[[], T],
    *,
    attempts: int,
    sleep: Callable[[float], None],
    base_delay: float = 0.2,
) -> T:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except TemporaryDependencyFailure:
            if attempt == attempts:
                raise
            sleep(base_delay * (2 ** (attempt - 1)))
    raise AssertionError("the loop should have returned or raised")
```

Production systems normally add randomized jitter so many clients do not retry at the same time. The random source should also be injectable so tests remain deterministic. Learn HTTP status-code details, `Retry-After`, authentication, and idempotency semantics in [[api/00-index|API]]; this lesson addresses only Python control flow.

> [!warning] This skeleton does not implement a total deadline
>
> It demonstrates only “bounded attempts + testable backoff.” A real external call must pass remaining time into lower-level timeout parameters and check a total deadline with a monotonic clock before each call and sleep. If a synchronous function does not support interruption, outer timing cannot force it to stop. Cancellation propagation must also be designed for the actual synchronous or asynchronous execution model.

## Cleanup and cancellation

- Prefer `with path.open(...) as file:` for files.
- Use `tempfile.TemporaryDirectory()` for temporary directories.
- Write a temporary file, validate success, then atomically replace the target to avoid half-finished output.
- Do not raise a new unrelated exception in `finally` that hides the original failure.
- When an async task receives `CancelledError`, perform necessary cleanup first, then re-raise it; do not swallow cancellation.

## Exercises

1. Test `retry_transient` above: fail twice, succeed on the third call, and assert the call count and a `0.2, 0.4` backoff sequence.
2. Add tests for “permanent errors are not retried” and “attempts are exhausted.”
3. Choose a side-effecting operation and describe the idempotency key or compensation mechanism it needs before retrying.
4. Draw the worst-case timeline for one 10-second total budget, including individual calls, backoff, and cleanup.

## Self-check

- [ ] I can explain why input errors, transient failures, permanent failures, and program defects cannot all share one retry policy.
- [ ] I can distinguish a per-call timeout from a total task deadline.
- [ ] I can prove whether an operation is idempotent instead of merely saying it “should be fine.”
- [ ] I can preserve an exception causal chain without leaking sensitive details to a caller.
- [ ] I can identify where resources are closed on success, exception, and cancellation paths.

## Related concepts and next step

- Prerequisite: [[python-fundamentals/engineering-route/01-foundations-and-boundaries/04-files-json-and-input-validation|Files, JSON, and Input Validation]].
- Next, [[python-fundamentals/engineering-route/02-reliability-and-testing/06-configuration-logging-and-sensitive-information|Configuration, Logging, and Sensitive Information]] turns failures into diagnosable evidence.
- See the observability and workflow-automation courses for system-level recovery strategies.

## References

Retrieved on **2026-07-14**.

- [Python: exception handling](https://docs.python.org/3.14/tutorial/errors.html)
- [Python: `contextlib`](https://docs.python.org/3.14/library/contextlib.html)
- [Python: `asyncio.timeout`](https://docs.python.org/3.14/library/asyncio-task.html#timeouts)
