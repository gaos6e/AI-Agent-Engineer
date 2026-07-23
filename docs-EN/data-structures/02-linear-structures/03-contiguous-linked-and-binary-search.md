---
title: "Contiguous, Linked, and Binary Search"
tags: [ ai-agent-engineer, data-structures, sequence, bisect ]
aliases: [ Sequential and linked structures, Python bisect ]
lang: en
translation_key: "数据结构基础/02-线性结构/03-顺序链式与二分查找.md"
translation_source_hash: d132586a827fe190a5e62e1ace2e5202a140c9c0392762110b63ffb931f208cb
translation_route: zh-CN/数据结构基础/02-线性结构/03-顺序链式与二分查找
translation_default_route: zh-CN/数据结构基础/02-线性结构/03-顺序链式与二分查找
---

# Contiguous, Linked, and Binary Search

## Objective

Understand why contiguous structures suit positional access, why linked structures suit changing links near a known node, and how to use `bisect` correctly for small sequences that remain sorted. The focus is operational trade-offs, not hand-writing a production linked list.

## Linear structures have one before-and-after direction

In a linear structure, elements are arranged in one sequence. Common operations include:

- retrieving item $i$ by index;
- inserting or removing at the beginning, end, or middle;
- traversing from beginning to end;
- searching by value; and
- maintaining sort order or retaining only one window.

“Has an order” does not mean “is sorted.” A message list is ordered by arrival; a priority sequence is sorted by a key; a dictionary preserves insertion order but is not automatically sorted by key.

## A practical model of Python `list`

For common CPython implementations, it is useful to picture a `list` as a growable array of object references:

- locating an item by index is normally $O(1)$;
- tail `append` is normally amortized $O(1)$;
- insertion or removal at the middle or head moves later references and is normally $O(n)$;
- `value in items` may compare items one by one and is $O(n)$; and
- a slice produces a new outer list, with cost growing with slice length.

This is a useful implementation-cost model, not a Python language-specification promise of one fixed memory layout for every implementation. Do not hard-code “bytes per item” in teaching material.

```python
messages = ["system", "user", "assistant"]
first = messages[0]
tail = messages[1:]      # A new outer list.
messages.append("tool")  # Update the original list at its tail.
```

## Trade-offs of linked structures

A linked-list node stores a value and a reference to its next node; a doubly linked list also stores a reference to its previous node. If you already hold the target node, changing nearby links can be $O(1)$; finding item $i$ still normally requires walking from one end in $O(n)$.

```text
[A | next] → [B | next] → [C | None]
```

In ordinary Python application code, a hand-written linked list often adds extra objects, references, and boundary bugs, and its locality can be worse than contiguous storage. Prefer `collections.deque` for a queue with both ends; implement a linked list only for a data-structure exercise or a real node-level splicing need, then justify it with benchmarks and invariants.

## Sorted sequences and binary boundaries

If a sequence is already sorted by one consistent rule, binary search discards half of the remaining range at each step, so locating a boundary is $O(\log n)$. Python `bisect` returns an **insertion point**; it does not directly test equality:

```python
from bisect import bisect_left, bisect_right

timestamps = [10, 20, 20, 35]
left = bisect_left(timestamps, 20)    # 1: before the first 20
right = bisect_right(timestamps, 20)  # 3: after the last 20
print(timestamps[left:right])         # [20, 20]
```

To find an exact value, still test the boundary and equality:

```python
def find_exact(sorted_values: list[int], target: int) -> int | None:
    index = bisect_left(sorted_values, target)
    if index != len(sorted_values) and sorted_values[index] == target:
        return index
    return None
```

`bisect` relies only on `<` to locate a position; it does not verify that input is truly sorted. If the sort key, case rule, or data changes while searching, its result is no longer trustworthy.

## `insort` is not $O(\log n)$ insertion

```python
from bisect import insort

latencies = [80, 120, 250]
insort(latencies, 100)
print(latencies)  # [80, 100, 120, 250]
```

Locating the insertion point is $O(\log n)$, but a list must move later elements, so overall `insort` cost is normally $O(n)$. It suits small, read-heavy, occasionally inserted sorted collections. For frequent lookup by a unique key, use a `dict`; to repeatedly retrieve only the lowest-priority item, use a heap; for large data volumes or concurrent writes, choose a dedicated index or store.

The official documentation also states that `bisect` functions are not thread-safe: concurrently modifying the same sequence can yield undefined or unsorted results.

## Agent-engineering examples

- Use `bisect_left` to find the left boundary of a log-time window.
- Use `bisect_right` to slice sorted scores no later than a threshold.
- Insert into a small sorted candidate collection.
- Do not use it as a replacement for a vector index, database index, or priority queue.

## Exercises

1. For `[10, 20, 20, 35]`, calculate the left and right insertion points for targets `5`, `20`, and `40`, then run code to verify them.
2. Write `within_range(sorted_values, low, high)` that returns the slice in the closed interval without changing input.
3. Compare list and linked-list costs for indexed reads, insertion after a known node, and full traversal.
4. Deliberately pass an unsorted list and explain why “the function did not raise an error” does not prove its result is correct.
5. Test `find_exact` with an empty list, first item, last item, duplicates, and an absent value.

## Self-check

- [ ] I can distinguish preserving order from being sorted.
- [ ] I can explain why a middle insertion into a Python `list` normally moves elements.
- [ ] I can state that $O(1)$ linked-list insertion assumes the node has already been found.
- [ ] I can correctly distinguish `bisect_left` from `bisect_right`.
- [ ] I do not describe total `insort` cost as $O(\log n)$.

## Next step and related concepts

- Next: [[data-structures/02-linear-structures/04-mutability-copying-and-iteration|Mutability, Copying, and Iteration]].
- See [[vector-databases/00-index|Vector Databases]] for specialized vector-retrieval indexes; they are outside this lesson's scope.

## References

Retrieved on **2026-07-14**.

- [Python 3.14: Sequence Types](https://docs.python.org/3.14/library/stdtypes.html#sequence-types-list-tuple-range)
- [Python 3.14: `bisect`](https://docs.python.org/3.14/library/bisect.html)
- [MIT OCW 6.006: Lecture 2, Data Structures](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/resources/mit6_006s20_lec2/)

