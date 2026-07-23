---
title: "Data Structures Fundamentals"
tags:
  - ai-agent-engineer
  - engineering-foundations
  - data-structures
aliases:
  - Data structures primer
  - Python data-structures route
source_checked: 2026-07-14
ai_learning_stage: "1. Engineering foundations"
ai_learning_order: 3
ai_learning_schema: 2
ai_learning_id: data-structures
ai_learning_domain: foundations
ai_learning_catalog_order: 300
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 30
ai_learning_track_agent_app_kind: recommended
ai_learning_track_rag_order: 30
ai_learning_track_rag_kind: optional
ai_learning_track_agent_platform_order: 30
ai_learning_track_agent_platform_kind: recommended
ai_learning_track_multimodal_realtime_order: 30
ai_learning_track_multimodal_realtime_kind: optional
lang: en
translation_key: "数据结构基础/00-目录.md"
translation_source_hash: ae33d0bc55ad4d31362ed9d05fc1c3bcfd80faaa9f6988a72e1466b06b4104ea
translation_route: zh-CN/数据结构基础/00-目录
translation_default_route: zh-CN/数据结构基础/00-目录
---

# Data Structures Fundamentals

## About this knowledge base

Data structures ask, “How should data be organized so the operations we need are clear, correct, and affordable?” This is not an algorithm-interview question bank. It builds decision-making ability from ADTs, invariants, and complexity through structural composition, using Agent-engineering concerns such as message history, tool registries, task queues, deduplication, priorities, and dependency graphs.

The course uses the Python 3 standard library. Python syntax is a prerequisite; this course explains why to choose `list`, `deque`, `dict`, `set`, `bisect`, `heapq`, and adjacency lists, along with their capacity, mutability, determinism, and failure boundaries.

> [!info] Sources and versions
>
> Dynamic Python behavior was checked against the official Python **3.14.6** documentation on **2026-07-14**. Course code avoids 3.14-only APIs for Python 3.11+ compatibility. Local verification used Python 3.11.9; that does not prove time or memory characteristics are the same across every interpreter implementation and version.

## Where this fits in the overall route

This course belongs to the Engineering and Mathematics Foundations domain of the AI Agent Engineer learning route. Before starting, complete the zero-background prerequisite gate and acquire local function/container ability in [[python-fundamentals/00-index|Python Fundamentals]]; you need not complete the whole Python course first. Then apply structure choices to API/JSON data, RAG, workflows, and Agent-state code.

This course covers only the minimum DFS/BFS, binary search, and topological progression required to choose structures. It does not expand into sorting proofs, shortest paths, dynamic programming, red-black or B-tree implementations, or competitive-programming algorithms.

## Learning objectives

- Distinguish ADTs, concrete representations, and algorithms; write preconditions, postconditions, and invariants for state.
- Explain time/space complexity, average/worst/amortized cost, and validate trends with measurement.
- Choose linear, hash, priority, and relational structures from their operations.
- Handle mutability, shallow copies, iterator exhaustion, ordering, and determinism.
- Use `bisect`, `deque`, `Counter`, `heapq`, and adjacency lists for small engineering problems.
- Combine `dict + set + graph + heap` into a testable dependency-task scheduler.
- Identify the boundary between in-memory containers and production persistence, concurrency, idempotency, and recovery.

## Prerequisites

- You can run `.py` files and `unittest` in Windows 11 and PowerShell 7.
- You know variables, `if`, `for`, functions, exceptions, list/dict/set, and basic type hints.
- If you cannot write a function that filters a list and counts frequencies without notes, return to [[python-fundamentals/00-index|Python Fundamentals]].
- The examples run offline and use no network, third-party packages, or secrets.

## Course structure and recommended order

### 1. Foundation models

1. [[data-structures/01-foundation-models/01-data-structures-abstract-data-types-and-invariants|Data Structures, Abstract Data Types, and Invariants]]: define operations, ownership, and rules that must always hold.
2. [[data-structures/01-foundation-models/02-complexity-resource-costs-and-measurement|Complexity, Resource Costs, and Measurement]]: compare growth trends and collect evidence with `timeit` / `tracemalloc`.

### 2. Linear structures

3. [[data-structures/02-linear-structures/03-contiguous-linked-and-binary-search|Contiguous, Linked, and Binary Search]]: understand list tradeoffs, linked-structure preconditions, and `bisect` boundaries.
4. [[data-structures/02-linear-structures/04-mutability-copying-and-iteration|Mutability, Copying, and Iteration]]: avoid accidental shared state and exhausted generators.
5. [[data-structures/02-linear-structures/05-stacks-queues-and-deques|Stacks, Queues, and Deques]]: express LIFO, FIFO, and bounded-window ordering policies.

### 3. Indexing and priority

6. [[data-structures/03-indexing-and-priority/06-hash-tables-dictionaries-sets-and-counting|Hash Tables, Dictionaries, Sets, and Counting]]: master mapping, membership, frequency, order, and deduplication/idempotency boundaries.
7. [[data-structures/03-indexing-and-priority/07-heaps-and-stable-priority-queues|Heaps and Stable Priority Queues]]: choose the next item only from the ready set, defining ties and starvation policy.

### 4. Relational structures

8. [[data-structures/04-relational-structures/08-trees-and-hierarchical-traversal|Trees and Hierarchical Traversal]]: use DFS/BFS for hierarchies and cap depth and node count.
9. [[data-structures/04-relational-structures/09-graphs-dependencies-and-topological-order|Graphs, Dependencies, and Topological Order]]: make edge direction, indegree, DAGs, cycles, and blocked nodes explicit.

### 5. Engineering decisions

10. [[data-structures/05-engineering-selection/10-structure-composition-capacity-boundaries-and-performance-diagnosis|Composed Structures, Capacity Boundaries, and Performance Diagnostics]]: establish sources of truth, derived indexes, limits, and a measurement loop.

### 6. Project and self-assessment

11. [[data-structures/06-project-and-self-check/11-project-dependency-task-scheduler|Project: Dependency Task Scheduler]]: use adjacency lists, indegrees, and a heap to produce a deterministic order.
12. [[data-structures/06-project-and-self-check/12-course-self-check-and-mastery-review|Course-Wide Self-Check and Mastery]]: closed-book questions, live tasks, and transfer design.

## Hands-on practice and project entry point

Supporting code is located at:

```text
data-structures/examples/
├── task_scheduler.py
└── test_task_scheduler.py
```

From the vault root, run:

```powershell
python -B '.\docs-EN\data-structures\examples\task_scheduler.py'
python -B -m unittest discover `
  -s '.\docs-EN\data-structures\examples' `
  -p 'test_*.py' `
  -v
```

The current implementation has 24 offline tests covering valid graphs, ties, malformed input, rejection of one-shot iterators, cycles, input immutability, and determinism. Implement it yourself first, then compare the solution; simply running tests is not evidence that you can explain the structure choice.

## Mastery standard

- [ ] I can choose a structure from primary operations, scale, and ordering requirements instead of merely saying “dictionaries are fast.”
- [ ] I can distinguish worst, average, and amortized complexity and account for space cost.
- [ ] I can draw alias/shallow-copy reference diagrams and correctly handle one-shot iterator consumption.
- [ ] I can explain why `insort` is overall `O(n)` and why a heap is not a fully sorted list.
- [ ] I can distinguish dict insertion order, sorting, and the lack of a stable-order guarantee for sets.
- [ ] I can write DFS/BFS and Kahn topological progression and accurately explain cycles and blocked nodes.
- [ ] I can define one source of truth, derived indexes, and invariants for multiple structures.
- [ ] All 24 scheduler tests pass, and I can calculate complexity and tie rules by hand.
- [ ] I do not mistake an in-memory queue, set-based deduplication, or scheduling order for production reliability semantics.

## Relationships with other knowledge bases

| Knowledge base | Boundary with this course |
| --- | --- |
| [[python-fundamentals/00-index\|Python Fundamentals]] | Provides syntax, functions, types, exceptions, and tests; this course covers operation cost and structural choice. |
| [[json/00-index\|JSON]] | Parsed JSON commonly maps to list/dict; encoding, schema, and compatibility are outside this course. |
| [[vector-fundamentals/00-index\|Vector Fundamentals]] and [[vector-databases/00-index\|Vector Databases]] | Vectors and specialized indexes have their own mathematics, retrieval, persistence, and sharding semantics. |
| [[rag/00-index\|RAG]] | General containers can hold chunks and candidates; chunking, retrieval, citations, and evaluation belong to the RAG route. |
| [[workflow-automation/00-index\|Workflow Automation]] and [[agent-core/00-index\|Agent Core]] | This course supplies queue/graph/heap intuition; execution, authorization, stopping, retry, and recovery are in later courses. |
| Runtime Monitoring | This course explains windows and counting structures; monitoring systems govern metrics, alerts, and retention. |

## Verification record

- No public replicated material required freezing before the directory reorganization; valuable original content was preserved by concept.
- Under Python 3.11.9, the examples and 24 `unittest` tests passed. A further 500 random DAGs verified every dependency precedes its successor and input permutations of the same task set do not change output.
- All 39 Python code blocks in the 12 course notes were parsed as AST syntax; all 50 full-path wikilinks pointed to existing files.
- Python 3.14, PyPy, production task systems, and real concurrency environments were not run. Complexity tables are models, not fixed performance promises across implementations.

## Primary references

Retrieved on **2026-07-14**.

- [Python 3.14: Data Structures](https://docs.python.org/3.14/tutorial/datastructures.html)
- [Python 3.14: Built-in Types](https://docs.python.org/3.14/library/stdtypes.html)
- [Python 3.14: `collections`](https://docs.python.org/3.14/library/collections.html)
- [Python 3.14: `bisect`](https://docs.python.org/3.14/library/bisect.html)
- [Python 3.14: `heapq`](https://docs.python.org/3.14/library/heapq.html)
- [Python 3.14: `graphlib`](https://docs.python.org/3.14/library/graphlib.html)
- [MIT OCW 6.006: Introduction to Algorithms](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/)
