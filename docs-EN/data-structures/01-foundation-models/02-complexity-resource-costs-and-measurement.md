---
title: "Complexity, Resource Costs, and Measurement"
tags: [ ai-agent-engineer, data-structures, complexity ]
aliases: [ Big O primer, data-structure complexity ]
lang: en
translation_key: "数据结构基础/01-基础模型/02-复杂度资源成本与实测.md"
translation_source_hash: fc596c7db270ebb8eadeb5c8c35c02247e3b2f422987a41cddd5ad22db6d9954
translation_route: zh-CN/数据结构基础/01-基础模型/02-复杂度资源成本与实测
translation_default_route: zh-CN/数据结构基础/01-基础模型/02-复杂度资源成本与实测
---

# Complexity, Resource Costs, and Measurement

## Objective

Use Big O to describe how resource cost grows with input size, distinguish worst, average, and amortized complexity, and validate trends with reproducible measurements rather than inventing universal performance numbers.

## Complexity belongs to an operation, not a container name

Return to the operation profile from [[data-structures/01-foundation-models/01-data-structures-abstract-data-types-and-invariants|ADTs and Invariants]]. Before selecting a structure, ask:

- Do you need positional access or lookup by unique ID?
- Must order be preserved, and are duplicates allowed?
- Is tail append, head removal, or arbitrary-position insertion most common?
- Must the “most urgent” item be selected next?
- Are there parent-child or dependency relationships?

“Use a list” has no standalone complexity: `items[i]`, `value in items`, `append`, and `pop(0)` are different operations. State whether input size $n$ means task count, node count, edge count, or text length.

## Big O is a growth trend, not a stopwatch

For input size $n$:

- $O(1)$: cost does not grow in proportion to $n$, such as indexed list lookup.
- $O(\log n)$: each step substantially narrows the problem, such as depth in balanced search structures or heap operations.
- $O(n)$: doubling elements roughly doubles work, as in a list scan.
- $O(n\log n)$: the common order of efficient comparison sorting.
- $O(n^2)$: two layers consider all pairs and grow quickly for large data.

Big O ignores constants and lower-order terms to compare trends as scale increases. It does not describe actual elapsed time, network, disk, memory, or implementation constants. With small data, clear correct code is usually more valuable than a tiny performance difference.

## Worst, average, and amortized

- **Worst case**: the highest cost among allowed inputs.
- **Average case**: needs an explicit distribution or implementation assumption; “usually” is not a proof.
- **Amortized cost**: total cost across a sequence divided by operations, such as occasional dynamic-array growth while tail appends are usually amortized $O(1)$.

Dictionary/set membership is commonly modeled as average $O(1)$. That is neither a worst-case nor security guarantee. If an attacker controls input, consider hash collisions, resource limits, and implementation defenses.

## Two forms of the same need

Check whether a batch of `run_id` values has already been processed:

```python
processed_list = ["r1", "r2", "r3"]
print("r3" in processed_list)  # May scan the list: O(n).

processed_set = {"r1", "r2", "r3"}
print("r3" in processed_set)   # Average O(1).
```

A set suits frequent membership tests, but it is not an ordered history. To preserve processing order and deduplicate quickly, maintain both a list and set behind one update boundary so they cannot diverge.

## Intuitive cost of common Python operations

| Operation | Common structure | Typical complexity | Intuition |
| --- | --- | --- | --- |
| Indexed read | `list` | $O(1)$ | Directly locate the slot |
| Find a value | `list` | $O(n)$ | May compare one item at a time |
| Tail append | `list.append` | Amortized $O(1)$ | Occasional growth averaged across many operations |
| Remove from head | `list.pop(0)` | $O(n)$ | Later elements must move |
| Pop queue head | `deque.popleft` | $O(1)$ | End operations are its purpose |
| Key lookup | `dict` | Average $O(1)$ | Hash-based location |
| Set membership | `set` | Average $O(1)$ | Also hash-based |
| Heap push/pop | `heapq` | $O(\log n)$ | Restore heap order along tree height |

“Average” is not an unconditional guarantee: collisions, memory pressure, and adversarial input can affect actual behavior. This table is a practical cost model for Python/common CPython implementations, not a language-level time guarantee that every Python implementation must provide. Remeasure after version, data-type, or hardware changes.

## Space cost and peak memory

Fast time does not imply low memory. Consider:

- how input, auxiliary indexes, and output grow with scale;
- containers usually hold object references, and shallow copies do not recursively copy referenced objects;
- a generator becomes fully materialized if immediately wrapped in `list(...)`; and
- keeping both a `list` and `set` trades $O(n)$ auxiliary space and an invariant for faster membership checks.

`sys.getsizeof()` reports only an object's direct allocation, not recursively referenced objects. Use `tracemalloc` to measure a real segment of Python allocation, while remembering that results depend on version and environment.

## Use timeit to validate trends

Compare only growth trends on the same machine and interpreter:

```python
from timeit import timeit


def compare_membership(size: int) -> tuple[float, float]:
    values = list(range(size))
    value_set = set(values)
    target = size - 1
    list_seconds = timeit(lambda: target in values, number=2_000)
    set_seconds = timeit(lambda: target in value_set, number=2_000)
    return list_seconds, set_seconds


for n in (100, 1_000, 10_000):
    print(n, compare_membership(n))
```

Record Python version, data size, repetitions, and data distribution. Do not turn one laptop result into “lists are always X times slower”: caches, startup, background load, and hash costs affect measurements.

A minimum memory measurement:

```python
import tracemalloc

tracemalloc.start()
values = [str(i) for i in range(10_000)]
current, peak = tracemalloc.get_traced_memory()
print({"current_bytes": current, "peak_bytes": peak})
tracemalloc.stop()
```

This observes Python allocations during tracing, not the whole process or a fixed cross-version result. `tracemalloc` itself costs CPU and memory; compare the same configuration and workload.

## Agent-engineering choices

- Time-ordered message append and traversal: `list`.
- Most recent N events: `deque(maxlen=N)`.
- `tool_name → tool_definition`: `dict`.
- Processed event IDs: `set`.
- Next item by priority: `heapq`.
- Step dependencies: adjacency list `dict[str, set[str]]`.

A structure cannot replace business rules. A set can identify repeated IDs, but not whether two requests are business-equivalent; that needs an idempotency key and defined semantics.

## Exercise

Choose a structure and explain its primary operation for each need:

1. Preserve conversation messages and send them to a model in original order.
2. Keep only the most recent 100 latency samples.
3. Fetch a parameter schema quickly by tool name.
4. Repeatedly take the highest-priority, earliest-entered task.
5. Determine whether task dependencies contain a cycle.

Then run the `timeit` code above. Answer only whether growth trends from $n=100$ to $10,000$ fit the model; retain raw output, interpreter version, and anomalies.

## Self-check

1. Does $O(1)$ mean one machine instruction?
2. Why is `list.pop(0)` unsuitable for a large queue?
3. What does amortized mean in “amortized $O(1)$”?
4. Why can two equal-complexity solutions differ noticeably in speed?
5. Why is `sys.getsizeof(container)` not the total memory of a nested object graph?
6. What qualification is missing from “dictionary lookup is O(1)”?

Answers: $O(1)$ means cost does not grow with input size; head removal shifts later list elements; occasional high cost is averaged over a sequence; implementation constants, caches, memory, I/O, and data distributions affect measurements; `getsizeof` does not recurse into referenced objects; dictionary membership normally refers to average cost under implementation/input assumptions.

## Next step and related concepts

Next: [[data-structures/02-linear-structures/03-contiguous-linked-and-binary-search|Contiguous, Linked, and Binary Search]].

## References

Retrieved on **2026-07-14**.

- [MIT OCW 6.006: Introduction to Algorithms](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/)
- [Python 3.14: Data Structures](https://docs.python.org/3.14/tutorial/datastructures.html)
- [Python 3.14: `timeit`](https://docs.python.org/3.14/library/timeit.html)
- [Python 3.14: `sys.getsizeof`](https://docs.python.org/3.14/library/sys.html#sys.getsizeof)
- [Python 3.14: `tracemalloc`](https://docs.python.org/3.14/library/tracemalloc.html)
- [Python Wiki: TimeComplexity](https://wiki.python.org/moin/TimeComplexity): a community-maintained supplemental table, not the sole authority.
