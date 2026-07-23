---
title: "Stacks, Queues, and Deques"
tags: [ ai-agent-engineer, data-structures, queue ]
aliases: [ Stack Queue Deque primer ]
lang: en
translation_key: "数据结构基础/02-线性结构/05-栈队列与双端队列.md"
translation_source_hash: 19d5f4b3b2674bf336326a121cfa726f0d965b66a2f694a2310461b905107700
translation_route: zh-CN/数据结构基础/02-线性结构/05-栈队列与双端队列
translation_default_route: zh-CN/数据结构基础/02-线性结构/05-栈队列与双端队列
---

# Stacks, Queues, and Deques

## Objective

Distinguish last-in, first-out from first-in, first-out; use `list` for a stack and `collections.deque` for a queue; and design empty-queue and capacity boundaries for task consumers.

## Stack: last in, first out

A stack is like a pile of plates: the last item placed on it is removed first, known as LIFO (Last In, First Out).

```python
steps = []
steps.append("open_file")
steps.append("parse_json")

current = steps.pop()
print(current)  # parse_json
```

Stacks support parsing nested structures, undo histories, and depth-first traversal. The call stack is also an important model for function execution, but do not reduce business compensation to a simple `pop()`: external side effects such as sent email or completed payments need an explicit compensation process.

## Queue: first in, first out

A queue is like a line: the earliest item is processed first, known as FIFO (First In, First Out). Removing from the head of a Python list moves elements; a double-ended queue, `deque`, suits appending and removing at both ends:

```python
from collections import deque

jobs = deque(["run-1", "run-2"])
jobs.append("run-3")

while jobs:
    run_id = jobs.popleft()
    print(run_id)
```

Check whether a queue is empty before the loop, otherwise `popleft()` raises `IndexError`.

## Operations and the empty-structure contract

| Abstraction | Python structure | Add | Remove | Empty behavior |
| --- | --- | --- | --- | --- |
| Stack | `list` | `append(x)` | `pop()` | `IndexError` |
| FIFO queue | `deque` | `append(x)` | `popleft()` | `IndexError` |
| Double-ended queue | `deque` | `append/appendleft` | `pop/popleft` | `IndexError` |

An API should choose among “check first,” “catch the specific exception,” or “return an explicit empty result,” then stay consistent. Do not use `None` both for “the queue is empty” and “the queue legally holds `None`.” Single-threaded teaching code can use `if jobs:`; in concurrent code, “check then take” can race, so use queue primitives that provide atomic operations.

## Bounded buffers

Monitoring systems often retain only the most recent N records:

```python
from collections import deque

recent_errors = deque(maxlen=3)
for code in [500, 502, 429, 503]:
    recent_errors.append(code)

print(list(recent_errors))  # [502, 429, 503]
```

This example always adds in time order with `append`, so when capacity is full the earliest-added item at the left end is discarded. That suits a sliding window, not an event log requiring permanent audit.

The general rule is that when a bounded `deque` is full, an add discards an item from the **opposite end**. Only when a time-ordered convention always adds at one end may the discarded item be called “the oldest.” `maxlen` cannot change after creation. Silent loss is container semantics; it does not automatically write an audit entry or raise an alert. If data cannot be dropped, explicitly check capacity before adding, or delegate backpressure to a more suitable queue system.

`rotate(k)` moves positions between ends, but it is not a business retry or fairness policy; any rotation order needs a clear business rule.

## `deque` is not a concurrent queue

`collections.deque` is an in-memory container. For producer/consumer threads, consider `queue.Queue`; for asynchronous coroutines, use `asyncio.Queue`. Those provide blocking/waiting and capacity semantics too. Even so, they do not provide cross-process persistence, crash recovery, or distributed acknowledgement.

Ask first: do you need container operations only, or coordination among multiple executors? Do not assume queues share a contract merely because their names are alike.

## What a production task queue still lacks

An in-memory `deque` explains FIFO but cannot provide cross-process persistence. A real Agent worker normally also needs:

- task IDs and idempotency keys;
- acknowledgement, retries, backoff, and a dead-letter queue;
- timeouts, leases, and recovery after consumer failure;
- priority, concurrency limits, and backpressure; and
- persistence, monitoring, and authorization.

These are system semantics; switching containers does not make them appear automatically.

## Exercises

1. Use a list to implement a browser “back” stack: visit A, B, and C, then go back twice.
2. Use `deque` to simulate FIFO processing of three tasks.
3. Create `deque(maxlen=5)` for recent latencies and calculate the mean after each append.
4. If task handling fails, should it immediately return to the queue head, go to the tail, or enter a separate retry queue? Explain the risk of each.
5. For a stack and queue, implement both “raise when empty” and “return an optional value” interfaces; explain which one cannot be confused with a valid `None`.
6. Test which end `append` and `appendleft` each evict from `deque(maxlen=3)`, and state the result as a contract.

## Self-check

1. What are the removal orders of a stack and a queue?
2. Why not use `list.pop(0)` for a large queue?
3. Does a `maxlen` queue suit an audit log?
4. Why can an in-memory queue not directly serve as a reliable multi-machine task system?
5. Why should concurrent consumers not rely on a two-step “`if queue`, then take” check?
6. Do `deque`, `queue.Queue`, and `asyncio.Queue` solve exactly the same problem?

## Next step and related concepts

Next: [[data-structures/03-indexing-and-priority/06-hash-tables-dictionaries-sets-and-counting|Hash Tables, Dictionaries, Sets, and Counting]].

## References

Retrieved on **2026-07-14**.

- [Python 3.14: `collections.deque`](https://docs.python.org/3.14/library/collections.html#collections.deque)
- [Python 3.14: `queue`](https://docs.python.org/3.14/library/queue.html)

