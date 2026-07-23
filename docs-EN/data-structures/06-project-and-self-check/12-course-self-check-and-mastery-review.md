---
title: "Course Self-Check and Mastery Review"
tags: [ ai-agent-engineer, data-structures, self-assessment ]
aliases: [ data-structures course self-check, data-structures mastery review ]
lang: en
translation_key: "数据结构基础/06-项目与自测/12-全库自测与掌握检查.md"
translation_source_hash: 418daac6bd46c661f25d802b2a88c47a90c5611e57aa7d6e632dc5da5f177309
translation_route: zh-CN/数据结构基础/06-项目与自测/12-全库自测与掌握检查
translation_default_route: zh-CN/数据结构基础/06-项目与自测/12-全库自测与掌握检查
---

# Course Self-Check and Mastery Review

## How to use this page

Answer closed-book first, then compare against the key points. Each question is worth four points, for 100 total. A score of 80 is required, and questions 3, 8, 12, 15, and 19 (complexity, mutability, hashing, heaps, and graphs) may not score zero. Passing the tests in [[data-structures/06-project-and-self-check/11-project-dependency-task-scheduler|Dependency Task Scheduler]] is required evidence too.

The point is not terminology recall; it is confirming that you can choose structures from operations, maintain invariants, explain costs, and acknowledge engineering boundaries.

## Closed-book questions

### Abstraction and complexity

1. Distinguish an ADT, a concrete data structure, and an algorithm, using a queue.
2. Write three invariants and one failure postcondition for a tool registry.
3. Why does $O(1)$ not mean one machine instruction? What do average, worst-case, and amortized analysis answer?
4. Why is `list.append` often amortized $O(1)$? Does that guarantee identical time for every call?
5. Why is `sys.getsizeof(list)` not total memory for all nested elements? What would be stronger measurement evidence?

### Linear structures and state

6. What are common cost models for Python-list indexed read, middle insertion, and membership search?
7. What premise does “linked-list insertion is $O(1)$” hide? Why do ordinary Python projects rarely implement linked lists themselves?
8. Draw references for `a = [[1]]; b = a.copy(); b[0].append(2)` and state final `a`.
9. How do iterable, iterator, and generator relate? Why can a generator be consumed once?
10. Where do `bisect_left` and `bisect_right` return different bounds for duplicates? Why is `insort` still $O(n)$ overall?

### Stacks, queues, hashing, and priority

11. Which Agent scenario suits a stack, FIFO queue, and bounded deque respectively? Which reliable-queue semantics are absent from an in-memory deque?
12. What limits average $O(1)$ dictionaries/sets? Why can a mutable list not be a key, and why cannot `hash()` be a persistent ID?
13. Does dictionary insertion order mean key-sorted order? How do you make set output deterministic?
14. How do deduplication and business idempotency differ? Why cannot a single-process set protect multi-instance writes?
15. Which invariant does a heap maintain? Why is it not a fully sorted list? How do peer priorities avoid `TypeError`?
16. Can numeric priority bypass a dependency? What is low-priority starvation?

### Trees, graphs, and engineering composition

17. Define a tree's root, leaf, depth, and subtree. How do DFS and BFS auxiliary structures differ?
18. Why maintain `visited` when enqueueing/pushing in graph traversal? How do you choose adjacency list versus matrix?
19. How is “A depends on B” represented in predecessor and successor maps? How does Kahn topological progress change in-degree?
20. Does a graph cycle mean no node can execute? Why is a blocked node not necessarily a cycle member?
21. In a `dict + indegree + adjacency + heap` composition, which structure is source of truth and which are derived indexes?
22. What capacity/cleanup policies do unbounded message history, a seen set, and a ready heap need?
23. How do you make scheduler output deterministic for identical input? State at least three rules.
24. Why should you not rewrite code merely after seeing nested loops? Give an evidence chain.
25. Why cannot this course's list/dict/heap directly replace a vector database?

## Answer key

> [!success]- Expand to check
>
> 1. An ADT specifies operation semantics; a structure is a representation; an algorithm implements operations. A queue can use `deque` or a persistent messaging system.
> 2. Keys unique; key matches object name; auxiliary indexes stay synchronized. On failure all indexes keep their pre-call state.
> 3. Big O describes growth with scale; average depends on distribution/assumptions; worst case takes highest cost; amortized analysis averages total cost across a series.
> 4. A dynamic array occasionally expands. A run of operations averages out, but one call can resize.
> 5. It counts only direct object allocation. Record version and workload; use `tracemalloc` or process Metrics and state their scope.
> 6. Common models are $O(1)$, $O(n)$, and $O(n)$.
> 7. You already hold the insertion-position node. Finding it can still cost $O(n)$, while Python object/reference overhead and boundary bugs often remove the value.
> 8. The outer lists share the inner list, so final `a == [[1, 2]]`.
> 9. An iterable produces an iterator; `next` consumes an iterator; a generator is a stateful iterator that does not reset after exhaustion.
> 10. Left locates the left edge of equals and right the right edge. Lookup is $O(\log n)$ but list shifting is $O(n)$.
> 11. Backtracking, FIFO tasks, and recent-window storage; missing persistence, acknowledgement, leases, retry, recovery, and multi-machine consistency.
> 12. Average is not worst-case guarantee; keys need stable hashing/equality; built-in `hash` is not promised stable across processes.
> 13. It is not sorting. Use `sorted` with a stable comparable key or an independent ordered structure.
> 14. Deduplication identifies repeated identifiers; idempotency ensures repeated business execution has no extra side effect and needs a durable atomic record.
> 15. The root is smallest and parent/child obey heap order; remaining items are not fully sorted. Use a unique sequence or stable ID to break ties.
> 16. No: priority compares only ready tasks. Continual high-priority arrivals can starve a lower-priority task.
> 17. DFS uses a stack and BFS a queue; both need node/depth limits.
> 18. It prevents cycles and duplicate multi-path visits. Sparse graphs normally use adjacency lists; use a matrix only for dense graphs with frequent edge lookup.
> 19. Predecessor map `A: {B}`; successor map `B: {A}`. Completing a predecessor decrements successor in-degree.
> 20. Unrelated DAG components can advance; downstream nodes may depend on a cycle without being cycle-path members.
> 21. The task mapping is source of truth; all other structures are rebuildable. Updates need one entry point and invariants.
> 22. State entry/byte caps and reject/evict/persist/backpressure semantics plus audit impact.
> 23. Stable IDs, fixed edge direction, a tie key, no set-order dependence, identical input, and pinned version/rules.
> 24. Record scale, operation frequency, and baseline; locate the hot path with profiler/timeit/tracemalloc; change the hot path and retest at the same workload.
> 25. A dedicated index also addresses approximate retrieval, filtering, persistence, sharding, recall/latency tradeoffs, and concurrent updates.

## Practical task A: bounded event window

Implement a local `EventWindow`:

- retain only the latest 100 `(timestamp, event_id, category)` values;
- `event_id` is unique inside the current window;
- count by `category`;
- return closed-interval time events using binary search;
- order events by nondecreasing `timestamp`, then `event_id` on ties;
- after a failed add, deque/list, seen set, and `Counter` remain unchanged;
- write at least 12 tests for capacity eviction, duplicate, unordered input, time bounds, input immutability, and determinism.

Write the structure-selection card and invariants before implementation. Explain why evicting an event must also remove it from `seen` and the counter, and why this is still not an audit log.

## Practical task B: migration design

An existing program scans a list of one million tool calls on every lookup, retains only recent results, and frequently looks up by ID. Write a migration design:

1. State current primary operations and complexity.
2. Select source of truth, ID index, and capacity window.
3. Define consistency when a multi-structure update fails.
4. State when a single-process structure is no longer enough.
5. Give a method for benchmark-data generation, measurement, and regression validation.
6. List problems you intentionally do not solve.

Do not invent “times faster.” Without measurement, state only a growth model and experiment plan.

## Final mastery standard

- [ ] I can select structures from operation, scale, order, duplicates, capacity, and concurrency.
- [ ] I can explain time/space and average/worst/amortized cost without treating Big O as a stopwatch.
- [ ] I can handle mutability, shallow copy, iterator exhaustion, and mutation during iteration.
- [ ] I can use `deque`, `dict/set/Counter`, `bisect`, and `heapq` correctly.
- [ ] I can write tree DFS/BFS and DAG topological progress and accurately explain a cycle.
- [ ] I can define sources of truth, derived indexes, and invariants for composed structures.
- [ ] The Dependency Task Scheduler's 24 tests pass and I can explain its complexity.
- [ ] I can state that in-memory examples lack production persistence, concurrency, recovery, and authorization semantics.

If you do not meet a point, return to its individual lesson and repeat its exercise. Do not hide a foundation gap by adding advanced trees or competitive-programming algorithms.

## Next step

- Return to [[data-structures/00-index|Data Structures Fundamentals]].
- Data interchange continues in [[json/00-index|JSON]]; vectors and indexes continue in [[vector-fundamentals/00-index|Vector Fundamentals]] and [[vector-databases/00-index|Vector Databases]].
- Workflow execution and recovery continue in [[workflow-automation/00-index|Workflow Automation]].

## References

This page combines mastery checks from the course. See individual lessons for exact facts and version sources. Retrieved on **2026-07-14**.
