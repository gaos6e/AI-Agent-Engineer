---
title: "Heaps and Stable Priority Queues"
tags: [ ai-agent-engineer, data-structures, heap, priority-queue ]
aliases: [ Python heapq, priority queue ]
lang: en
translation_key: "数据结构基础/03-索引与优先/07-堆与稳定优先队列.md"
translation_source_hash: 4aa107d07108ecd51d93e5c0f34c3853eee51f9e5147ea911451eba301933fd7
translation_route: zh-CN/数据结构基础/03-索引与优先/07-堆与稳定优先队列
translation_default_route: zh-CN/数据结构基础/03-索引与优先/07-堆与稳定优先队列
---

# Heaps and Stable Priority Queues

## Objective

Understand that a heap maintains only local order, use `heapq` to repeatedly take the highest-priority item from tasks that are currently ready, and specify policies for equal priorities, incomparable payloads, cancellation, and starvation.

## A heap is not a sorted list

Python's `heapq` implements a min-heap by default:

- `heap[0]` is the smallest element;
- `heappush` and `heappop` are $O(\log n)$;
- examining the smallest item is $O(1)$;
- `heapify(items)` builds a heap in place in $O(n)$; and
- except for the top, the full list is not guaranteed to be sorted.

```python
import heapq

ready = [(3, "review"), (1, "validate"), (2, "extract")]
heapq.heapify(ready)
while ready:
    print(heapq.heappop(ready))
```

If all data only needs sorting once, `sorted` is clearer. A heap delivers its value when tasks keep arriving while you repeatedly need the minimum or maximum.

## Make priority direction explicit

A min-heap pops lower values first. This course uses the convention “a lower numeric value is more urgent”:

```python
heapq.heappush(ready, (1, "urgent"))
```

Python 3.14 added max-heap APIs such as `heapify_max`, `heappush_max`, and `heappop_max`. To remain compatible with Python 3.11+ and preserve one mental model, the main course uses min-heaps. A real project should choose according to its supported version and must not mix negative-number conventions with max-heap semantics.

## Equal priorities need a stable tie rule

If you store `(priority, task)` directly, equal priorities compare `task` next; incomparable objects can raise `TypeError`. Add a monotonically increasing sequence number:

```python
import heapq
from itertools import count

sequence = count()
ready: list[tuple[int, int, str]] = []

heapq.heappush(ready, (2, next(sequence), "task-b"))
heapq.heappush(ready, (2, next(sequence), "task-a"))

_, _, first = heapq.heappop(ready)
print(first)  # task-b: equal priority follows heap-entry order.
```

This is a FIFO tie policy. You can instead use a task ID to make output deterministic regardless of input order; those semantics differ and must be fixed in the interface and tests. If a payload object comes last, earlier fields must uniquely break the tie so the payload itself is never compared.

## Why updates and deletion are difficult

`heapq` has no efficient arbitrary deletion or decrease-priority-by-ID interface. A common approach is:

1. Store `task_id → current valid entry/version` in a dictionary.
2. On update, push a new entry and mark the previous entry invalid.
3. Skip invalid entries when popping.
4. Rebuild the heap when necessary to control stale entries.

This is lazy deletion. It adds a dictionary-and-heap consistency invariant; for a small project with rare updates, rebuilding the heap can be clearer. Do not directly alter an arbitrary heap-list element without restoring the heap invariant.

## Priority compares only currently ready items

In dependency-task scheduling, a high-priority task whose prerequisite is incomplete cannot run ahead of the prerequisite. A graph determines what is ready; the heap chooses the next task only inside the ready set. Once structures are composed, each layer still has its own responsibility.

## Starvation, fairness, and production boundaries

A continual stream of high-priority tasks can keep low-priority tasks from running indefinitely. Possible policies include:

- increase effective priority after waiting (aging);
- use a separate quota or round-robin for each priority;
- set a maximum wait time; or
- separate an urgent channel from an ordinary channel and monitor both.

An in-memory heap does not provide persistence, leases, acknowledgement, retries, or multi-process consistency. It is a priority-selection structure, not a production messaging system.

## Exercises

1. Implement a `(priority, sequence, task_id)` queue and demonstrate equal-priority FIFO behavior.
2. Change it to `(priority, task_id)` and explain the difference between deterministic output and FIFO.
3. Use two incomparable dictionaries as payloads and demonstrate that a unique sequence avoids comparing payloads.
4. Design fields and three invariants for lazy-deletion entries.
5. Design one anti-starvation policy for a steady high-priority stream and state its possible side effects.

## Self-check

- [ ] Does a heap guarantee that its whole internal list is sorted?
- [ ] How do `heapify` and repeated `heappush` differ in heap-construction cost?
- [ ] Why do equal-priority tasks need a second sort key?
- [ ] Why can arbitrary modification of `heap[index]` be incorrect?
- [ ] Can priority allow a task with unmet dependencies to execute early?

## Next step and related concepts

- Next: [[data-structures/04-relational-structures/08-trees-and-hierarchical-traversal|Trees and Hierarchical Traversal]].
- See [[workflow-automation/00-index|Workflow Automation]] for production scheduling, retry, and recovery.

## References

Retrieved on **2026-07-14**.

- [Python 3.14: `heapq`](https://docs.python.org/3.14/library/heapq.html)
- [MIT OCW 6.006: Heaps and Priority Queues](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/pages/lecture-notes/)

