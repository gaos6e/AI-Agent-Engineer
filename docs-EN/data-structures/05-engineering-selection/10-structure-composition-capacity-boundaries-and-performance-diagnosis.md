---
title: "Structure Composition, Capacity Boundaries, and Performance Diagnosis"
tags: [ ai-agent-engineer, data-structures, design, performance ]
aliases: [ data-structure engineering selection, capacity and invariants ]
lang: en
translation_key: "数据结构基础/05-工程选择/10-结构组合容量边界与性能诊断.md"
translation_source_hash: 29be2f96a92ecc35a2787f0213dd25f96cea55219e35626f209aa41b6a4e5cce
translation_route: zh-CN/数据结构基础/05-工程选择/10-结构组合容量边界与性能诊断
translation_default_route: zh-CN/数据结构基础/05-工程选择/10-结构组合容量边界与性能诊断
---

# Structure Composition, Capacity Boundaries, and Performance Diagnosis

## Objective

Turn the first nine lessons from “container knowledge” into engineering decisions. Choose structures from principal operations, scale, order, mutability, and capacity; give composed structures a single update entry point and invariants; and diagnose a performance anomaly with evidence first.

## Structure-selection card

Every state component should answer at least:

| Dimension | Question |
| --- | --- |
| Main operation | How frequent are append, key lookup, membership test, minimum extraction, and neighbor traversal? |
| Scale | How many nodes/events/bytes now and one year later? How do edges grow? |
| Order | Insertion order, sorted order, FIFO, priority, or no order? |
| Duplicates | Are duplicates allowed, counted, deduplicated, or handled by business idempotency? |
| Mutability | Who owns the object? Snapshot or shared reference? |
| Capacity | Is there a limit, eviction, backpressure, or overflow behavior? |
| Persistence | Must it survive process restart? |
| Concurrency | One thread, many coroutines, threads, processes, or machines? |
| Determinism | Is replay, audit, or stable test output required? |

Only after these questions are answered does a complexity table become useful.

## Common Agent-scenario mapping

| Scenario | Primary structure | Key boundary |
| --- | --- | --- |
| Ordered conversation messages | `list` | Context capacity, snapshots, and sensitive content |
| Last N latency values | `deque(maxlen=N)` | Eviction is not audit retention |
| Tool name to definition | `dict` | Name uniqueness and consistent authorization index |
| Processed call IDs | `set` | In-process deduplication is not durable idempotency |
| Error-category counts | `Counter` | Time window and label cardinality |
| Small time boundary | Sorted `list` plus `bisect` | Insertion remains $O(n)$; concurrent modification risk |
| Currently ready tasks | `heapq` | Ties, starvation, and lazy deletion |
| Step dependencies | Adjacency list plus in-degree | Missing node, cycle, and direction convention |

Vector retrieval is not complete merely because Embeddings are put into a normal list and scanned linearly. Dedicated indexing, filtering, persistence, and recall tradeoffs belong to [[vector-databases/00-index|Vector Databases]].

## Composed structures need one source of truth

A task scheduler may keep:

```text
by_id: task_id → Task              # source of truth
dependents: predecessor → children # derived index
remaining: task_id → int           # derived count
ready: heap                         # current runnable view
```

If outside code may change every layer freely, you get states such as “the dictionary has a task but the in-degree table does not.” Keep building and updating inside one module; if a derived index can be rebuilt, state how. Typical invariants:

- every task ID in all four structures belongs to `by_id`;
- `remaining[id]` equals unfinished-predecessor count and is never negative;
- `ready` contains only valid unfinished tasks with `remaining == 0`;
- each valid task has at most one current heap entry, or version markers skip stale entries.

## Capacity is not “for later”

Unbounded lists, sets, and dictionaries grow with runtime. Decide:

- maximum entries, bytes, depth, or edge count;
- reject, evict, sample, persist, or apply backpressure at the limit;
- whether eviction affects audit, idempotency, or recovery;
- how to observe low-cardinality fields separately from high-cardinality IDs;
- complexity and concurrency semantics of cleanup itself.

A bounded `deque(maxlen=N)` silently drops elements from the end opposite a newly added item when full. Only when you always use `append` to add in time order is a dropped left-hand element the oldest one. It suits a window with an explicit direction convention, not a critical queue needing an explicit alarm.

## Performance-diagnosis order

1. State the user-visible symptom and budget.
2. Record input scale, operation frequency, Python/dependency version, and environment.
3. Use a profiler, `timeit`, `tracemalloc`, or Metrics to find the actual hot spot.
4. Decide whether the bottleneck is algorithmic growth, object allocation, I/O, locking, or an external service.
5. Replace only the hot structure and retain correctness and regression tests.
6. Retest with the same workload and record the cost in memory, complexity, and maintainability.

Do not replace code merely because you see nested loops, and do not replace a whole system with a complex structure based on one microbenchmark. In Agent systems, model/API waiting often dominates local container work, but that does not excuse unbounded memory or $O(n^2)$ scans.

## Determinism and replay

Set order, peer topological nodes, and equal-priority heap tasks can change with construction order when no rule is defined. When replay matters:

- use a stable unique ID;
- define a sequence number or sort key for ties;
- do not depend on set iteration;
- record structure-input versions and rules;
- test that identical input produces item-by-item identical output repeatedly.

Determinism is not correctness, but it lowers debugging and audit cost.

## Integrated exercise: a decision table

For each of these eight scenarios, fill in “main operation → candidate structure → time/space model → order/capacity risk → alternative”: message history, tool registry, recent errors, idempotency records, ready tasks, dependency graph, log time window, and document-chunk stream.

Then choose one composition (`list + set` or `graph + heap`):

1. Write its one public update function.
2. Write four invariants.
3. Introduce a bug that updates only one structure.
4. Catch it with a test.
5. State how to rebuild the derived index.

## Self-check

- [ ] I start from operations and scale, not a familiar container.
- [ ] I can distinguish source of truth, derived index, and cache.
- [ ] I can give every unbounded state a limit and behavior at the limit.
- [ ] I can identify invariants most likely to break in a multi-structure composition.
- [ ] Before optimizing I record a baseline; after optimizing I retest on the same workload.
- [ ] When replay is required, I do not rely on set order or undefined tie order.

## Next step and related concepts

- Integrated project: [[data-structures/06-project-and-self-check/11-project-dependency-task-scheduler|Project: Dependency Task Scheduler]].
- Observability evidence and capacity alerts continue in [[runtime-monitoring/00-index|Runtime Monitoring]].

## References

Retrieved on **2026-07-14**.

- [MIT OCW 6.006: Introduction to Algorithms](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/)
- [Python 3.14: Data Structures](https://docs.python.org/3.14/tutorial/datastructures.html)
- [Python 3.14: `timeit`](https://docs.python.org/3.14/library/timeit.html)
- [Python 3.14: `tracemalloc`](https://docs.python.org/3.14/library/tracemalloc.html)
