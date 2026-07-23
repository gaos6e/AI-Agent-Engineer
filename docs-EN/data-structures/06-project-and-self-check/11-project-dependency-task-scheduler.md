---
title: "Project: Dependency Task Scheduler"
tags: [ ai-agent-engineer, data-structures, project, scheduler ]
aliases: [ data-structures integrated project, dependency-scheduling project ]
lang: en
translation_key: "数据结构基础/06-项目与自测/11-项目-依赖任务调度器.md"
translation_source_hash: 265abf040e83da12446f207de779e2e14bad1e8a876ecc7c1b13723c4445641e
translation_route: zh-CN/数据结构基础/06-项目与自测/11-项目-依赖任务调度器
translation_default_route: zh-CN/数据结构基础/06-项目与自测/11-项目-依赖任务调度器
---

# Project: Dependency Task Scheduler

## Project goal

Build a deterministic task order from in-memory Python objects. Only a task whose dependencies are all complete enters the ready min-heap; lower numeric priority runs first, and equal priority sorts by `task_id`. The project composes `dict`, `set`, an adjacency list, in-degree, heap, and output list, and validates the contract with 24 unit tests.

It neither reads JSON nor executes external tools, and it uses no threads, network, file writes, or secrets. Scheduling **order** is not proof of successful business execution. Persistence, retry, leases, authorization, and recovery for production workflows are outside this project.

## Input contract

The task collection must be a built-in `list` or `tuple`. Generators and other one-shot iterators are intentionally rejected: after a scheduler consumes one, the caller cannot iterate it again, which makes “input unchanged” ambiguous. Each task is a mapping with exactly three fields:

```python
{
    "id": "validate",
    "priority": 1,
    "depends_on": ["extract"],
}
```

| Field | Rule |
| --- | --- |
| `id` | Built-in `str`; nonempty, no leading/trailing whitespace, globally unique |
| `priority` | Required and `type(value) is int`; explicitly rejects `bool` |
| `depends_on` | List; every item is a built-in `str`, nonempty, without leading/trailing whitespace; no duplicates |

Every dependency ID must exist. Direct self-dependency is rejected immediately; indirect cycles are reported after topological progress. Unknown/missing fields, invalid task objects, and dirty dependencies all become `ScheduleInputError` rather than leaking an `AttributeError` or a bare `TypeError` from an unhashable value.

## Selection and invariants

```text
by_id: id → immutable Task          # single source of truth
remaining: id → unfinished predecessor count  # in-degree working copy
dependents: predecessor id → successor id list # reverse adjacency list
ready: (priority, task_id) min-heap # current executable view
order: selected task_id values       # result
```

The following must hold:

1. `remaining` and `dependents` refer only to IDs in `by_id`.
2. Every ready task has in-degree zero.
3. Each dependency edge decrements its successor's in-degree once.
4. A task enters the heap at most once and appears in output at most once.
5. Priority is compared only among **currently ready tasks**.
6. Scheduling does not mutate the caller's list/tuple, task mapping, or dependency list.
7. Repeated calls with identical input yield identical order.

## Algorithm

1. `parse_task` turns each untrusted mapping into a frozen `Task`.
2. `_parse_tasks` builds `by_id` and checks unique IDs and dependency existence.
3. Compute `remaining` for every task while building `dependents`.
4. Push every zero-in-degree task into the min-heap.
5. Pop the current smallest `(priority, task_id)` and decrement its successors.
6. Push a successor when its in-degree reaches zero, until `ready` is empty.
7. If output count is below task count, one or more cycles block the remaining tasks.

Graph construction and in-degree update cost $O(V+E)$. Each task enters/leaves the heap at most once, adding $O(V\log V)$. Total time is $O(V+E+V\log V)$ and auxiliary space $O(V+E)$. This is not a throughput claim for a real distributed scheduler.

## Run it

From the vault root, run the demonstration:

```powershell
python -B '.\docs-EN\data-structures\examples\task_scheduler.py'
```

Expected:

```text
execution order: extract -> validate -> summarize -> review
```

Run tests:

```powershell
python -B -m unittest discover `
  -s '.\docs-EN\data-structures\examples' `
  -p 'test_*.py' `
  -v
```

`-B` prevents `.pyc` generation. The example installs no dependency and writes no file. If `python` is not the expected interpreter, check `Get-Command python`, `python --version`, and `sys.executable` first.

## Test matrix

| Category | Covered |
| --- | --- |
| Core | Collection root type; rejecting without consuming a one-shot iterator; empty input; one task; chain; diamond; independent components |
| Priority | Compare only within ready set; break peer ties by ID, not input order |
| Identity | Empty/trimmed/non-built-in string IDs, including unhashable subclasses; duplicate ID |
| Fields | Missing, unknown, non-mapping object, and normalized error for unhashable field names |
| Priority type | Reject `bool`, `float`, `str`, and `None` |
| Dependencies | Non-list, dirty member, duplicate, missing target, and direct self-dependency |
| Cycle | Indirect cycle plus downstream blocked by it; do not call every blocked node a cycle member |
| Properties | Input unchanged and repeated deterministic run |

Test count is evidence of the current implementation, not a goal to maximize. When changing the contract, update documentation and failure tests before implementation.

## Required exercises

1. Without reading the completed implementation, write `Task` and its parser from the data contract and make invalid-input tests fail first.
2. Draw predecessor map, successor map, and per-step in-degree change for a diamond dependency.
3. Add two peer tasks, change tie policy to input FIFO, introduce `sequence`, and update contract and tests.
4. Make `schedule` return a ready snapshot per round without exposing the mutable internal heap.
5. Add a read-only `payload` extension; prove scheduling does not mutate it and state the limit of shallow copying.

## Optional advanced work

- Reimplement a version that seeks only any valid topological order with `graphlib.TopologicalSorter`, and compare its peer order.
- Return stable error codes rather than depending on a complete English sentence, while retaining a human-readable message.
- Separately implement exact cycle-path or strongly-connected-component analysis, then distinguish cycle members from downstream blocked nodes; do not guess from the remaining set.

Do not add real API calls, a persistent queue, or asynchronous workers to this script. They blend data-structure correctness with side-effect recovery and make the result difficult to validate.

## Common mistakes

- Treating `bool` as a valid integer priority.
- Starting scheduling before parsing every input, so a dirty priority is hidden by a cycle error.
- Rescanning every task and rebuilding dependencies every round, causing needless higher-order growth.
- Comparing incomparable payloads on equal priority.
- Treating heap removal as proof that an external task succeeded.
- Calling every remaining blocked node a cycle member.
- Using `assert` for untrusted input validation, which optimization mode may remove.

## Project acceptance

- [ ] The demonstration and 24 tests pass on Python 3.11+.
- [ ] I can explain the responsibilities and invariants of the five internal structures.
- [ ] I can hand-calculate in-degree changes for a chain, diamond, and cyclic graph.
- [ ] I can prove that priority applies only inside `ready` and peers sort by ID.
- [ ] I can explain every term in $O(V+E+V\log V)$.
- [ ] I can distinguish cycle members, nodes blocked by a cycle, and unrelated runnable components.
- [ ] I can name production semantics not covered instead of claiming external execution is verified.

After completion, proceed to [[data-structures/06-project-and-self-check/12-course-self-check-and-mastery-review|Course Self-Check and Mastery Review]].

## References

Retrieved on **2026-07-14**.

- [Python 3.14: `heapq`](https://docs.python.org/3.14/library/heapq.html)
- [Python 3.14: `graphlib`](https://docs.python.org/3.14/library/graphlib.html)
- [MIT OCW 6.006: Introduction to Algorithms](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/)
