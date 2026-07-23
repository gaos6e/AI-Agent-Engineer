---
title: "Async Concurrency, Cancellation, and Rate Limits"
tags: [ ai-agent-engineer, Python, asyncio, concurrency ]
aliases: [ Python async concurrency, asyncio primer ]
lang: en
translation_key: "Python基础/Agent工程路线/03-并发与交付/08-异步并发取消与限流.md"
translation_source_hash: 46b5f3050934fc8468de6e1f59a1215f68316ee61698d5acb1d41cb608be9deb
translation_route: zh-CN/Python基础/Agent工程路线/03-并发与交付/08-异步并发取消与限流
translation_default_route: zh-CN/Python基础/Agent工程路线/03-并发与交付/08-异步并发取消与限流
---

# Async Concurrency, Cancellation, and Rate Limits

## Objective

Understand why coroutines suit wait-heavy I/O, manage task lifecycles with structured concurrency, and design explicit behavior for timeouts, cancellation, concurrency caps, and partial failures. This lesson neither treats concurrency as a default optimization nor mistakes it for CPU parallelism.

## Decide whether concurrency is needed first

| Work type | Where most time goes | Common choice |
| --- | --- | --- |
| I/O-bound | Waiting for network, disk, database, or model services | `asyncio`, or controlled threads |
| CPU-bound | Encoding, image processing, or extensive Python computation | Measure first; then consider processes, native libraries, or another runtime |
| Very small or strictly sequential | Data has dependencies or call volume is low | Ordinary synchronous code is clearer |

Concurrency means the execution intervals of several tasks overlap; parallelism means work genuinely runs on multiple computing resources at the same moment. A single-threaded event loop can wait concurrently efficiently, but it does not automatically make CPU-intensive Python faster.

## Coroutines and the event loop

Calling an `async def` function merely creates a coroutine object. It runs only after it is awaited or registered as a task:

```python
import asyncio


async def fetch_one(name: str) -> str:
    await asyncio.sleep(0.05)  # Simulate non-blocking waiting.
    return name.upper()


async def main() -> None:
    result = await fetch_one("rag")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
```

Library code normally does not call `asyncio.run()`; it belongs to the outermost application entry point. Notebooks, web frameworks, and async services already own an event loop, so starting another one raises an error.

## Manage lifecycles with TaskGroup

Python 3.11+'s `asyncio.TaskGroup` puts “which tasks are created, when they are awaited, and what happens to the others after one fails” in a single scope:

```python
async def fetch_all(names: list[str]) -> list[str]:
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(fetch_one(name)) for name in names]
    return [task.result() for task in tasks]
```

When a child task first raises a non-cancellation exception, `TaskGroup` cancels the remaining unfinished tasks; on exit, it can aggregate several exceptions in an `ExceptionGroup`. This suits fail-fast semantics where child tasks jointly form one operation.

When business rules permit partial success, explicitly model each item's success or failure record. Do not use broad `gather(..., return_exceptions=True)` and then forget to inspect exceptions.

## Concurrency caps and backpressure

Creating 100,000 requests at once can exhaust connections, memory, or service quota even if every request is asynchronous. A `Semaphore` caps how many tasks enter an external boundary concurrently:

```python
async def bounded_map(names: list[str], limit: int) -> list[str]:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    semaphore = asyncio.Semaphore(limit)

    async def run(name: str) -> str:
        async with semaphore:
            return await fetch_one(name)

    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(run(name)) for name in names]
    return [task.result() for task in tasks]
```

A concurrency cap is not a per-second rate limit. The former constrains the number in flight; the latter constrains requests in a time window. Production clients often need both, alongside server quota, queue length, and the total task budget.

## Timeouts and cancellation are control flow

```python
async def fetch_with_deadline(name: str) -> str:
    try:
        async with asyncio.timeout(2.0):
            return await fetch_one(name)
    except TimeoutError as exc:
        raise TemporaryDependencyFailure("read timed out") from exc
```

A timeout scope cancels the current task and converts the result to built-in `TimeoutError` outside the scope. Cancellation can arrive at any `await`; clean up with `try/finally`, then re-raise `CancelledError`:

```python
async def worker() -> None:
    resource = await open_resource()
    try:
        await use_resource(resource)
    except asyncio.CancelledError:
        # Record only necessary cancellation information or state changes.
        raise
    finally:
        await resource.aclose()
```

Swallowing `CancelledError` breaks `TaskGroup`, timeout, and application-shutdown semantics. Propagate it unless cancellation genuinely becomes a defined business result.

## Do not block the event loop

These calls block the current thread and should not be put directly on an async hot path:

- `time.sleep()`;
- synchronous HTTP or database SDKs;
- synchronous reads and writes of large files; and
- CPU-intensive loops.

Small unavoidable synchronous I/O can be isolated with `await asyncio.to_thread(function, *args)`, but its thread can continue after coroutine cancellation. Set lower-level timeouts and control submission volume; `to_thread` is not a way to forcibly terminate arbitrary code.

## Result order, repetition, and shared state

- Completion order is not necessarily input order; an interface should state which it uses.
- An external call may have succeeded before its timeout, so retries still need idempotency semantics.
- Avoid having several coroutines mutate one shared dictionary directly; prefer returned values and summarize them in one place.
- If shared state is essential, use a lock, keep the critical section small, and never await slow I/O while holding it.

## Exercises

1. Simulate 20 tasks with `asyncio.sleep()`, set the concurrency cap to 3, and record evidence that the peak never exceeds 3.
2. Make item 5 fail; compare `TaskGroup` fail-fast behavior with a partial-success design where each item returns a result object.
3. Set a 0.3-second total deadline for a batch and verify that every task cleans up.
4. Put `time.sleep()` in a coroutine by mistake and measure it, then replace it with `asyncio.sleep()` and explain the difference.

## Self-check

- [ ] I can distinguish a coroutine object, a task, and an event loop.
- [ ] I can explain concurrency, parallelism, concurrency caps, and rate limits.
- [ ] I can state what happens when one task in a `TaskGroup` fails.
- [ ] I can correctly propagate cancellation and identify the resource-close path.
- [ ] I can recognize synchronous calls that block the event loop.

## Related concepts and next step

- Prerequisite: [[python-fundamentals/engineering-route/02-reliability-and-testing/07-unit-testing-mocks-and-regression|Unit Testing, Mocks, and Regression]].
- Next, [[python-fundamentals/engineering-route/03-concurrency-and-delivery/09-project-layout-cli-and-reproducible-runs|Project Layout, CLI, and Reproducible Runs]].
- Server-side rate strategy appears in [[api/00-index|API]]; workflow parallelism and recovery appear in Workflow Automation.

## References

Retrieved on **2026-07-14**. The course uses stable Python 3.11+ APIs and does not depend on the parameters added to `TaskGroup.create_task()` in Python 3.14.

- [Python: `asyncio` coroutines and tasks](https://docs.python.org/3.14/library/asyncio-task.html)
- [Python: task groups](https://docs.python.org/3.14/library/asyncio-task.html#task-groups)
- [Python: synchronization primitives](https://docs.python.org/3.14/library/asyncio-sync.html)
