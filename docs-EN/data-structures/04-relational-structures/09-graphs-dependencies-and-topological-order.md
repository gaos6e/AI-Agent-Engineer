---
title: "Graphs, Dependencies, and Topological Order"
tags: [ ai-agent-engineer, data-structures, graph, DAG ]
aliases: [ dependency graph and topological sorting, Python graphlib ]
lang: en
translation_key: "数据结构基础/04-关系结构/09-图依赖与拓扑顺序.md"
translation_source_hash: 96cb1b91bb6196ee62cc6b28709a032d1f4025c40fda23e13becba51f5b88f2d
translation_route: zh-CN/数据结构基础/04-关系结构/09-图依赖与拓扑顺序
translation_default_route: zh-CN/数据结构基础/04-关系结构/09-图依赖与拓扑顺序
---

# Graphs, Dependencies, and Topological Order

## Objective

Use nodes and edges to express arbitrary relationships; make edge direction and adjacency representation explicit; traverse a cyclic graph without revisiting nodes; and determine when a topological order covering every node exists.

## Nodes, edges, and direction

A graph $G=(V,E)$ has a node set $V$ and edge set $E$. Edges may be directed or undirected. Agent workflows commonly use directed dependency graphs.

“summarize depends on validate” has two common representations:

```python
# Predecessor map: task -> tasks it depends on.
predecessors = {
    "extract": set(),
    "validate": {"extract"},
    "summarize": {"validate"},
}

# Successor map: prerequisite -> tasks it may unlock.
successors = {
    "extract": {"validate"},
    "validate": {"summarize"},
    "summarize": set(),
}
```

Both are correct but their directions are opposite. In `graphlib.TopologicalSorter(graph)`, mapping values are **predecessors** of the key node. A project commonly builds a successor map while it updates in-degree. Names must state direction; calling everything `graph` invites guessing.

## Adjacency lists and matrices

- An adjacency list, `node → neighboring nodes`, usually uses $O(V+E)$ space and fits sparse dependency graphs.
- An adjacency matrix is a $V\times V$ table; it tests one edge directly but uses $O(V^2)$ space.
- An edge list stores `(source, target)` and suits transport or batch processing, but normally needs indexing before frequent neighbor lookup.

Workflow edges are usually far fewer than possible node pairs, so an adjacency list is more natural. A database or graph engine's internal index is not the same as this in-memory dictionary model.

## Graph traversal must record `visited`

A general graph can have cycles or several paths to one node. A minimal BFS:

```python
from collections import deque


def reachable(
    successors: dict[str, set[str]], start: str
) -> list[str]:
    if start not in successors:
        raise KeyError(start)
    seen = {start}
    queue = deque([start])
    order: list[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in sorted(successors[node]):
            if neighbor not in seen:
                if neighbor not in successors:
                    raise ValueError(f"missing node: {neighbor}")
                seen.add(neighbor)
                queue.append(neighbor)
    return order
```

Update `seen` when enqueuing to avoid adding one node repeatedly. `sorted` fixes teaching output. If nodes cannot be compared, use a stable ID or an explicit ordering key.

## DAGs and topological order

A Directed Acyclic Graph (DAG) has a topological order: in each `predecessor → successor` edge, the predecessor appears before its successor. A valid order need not be unique; deterministic output needs an additional tie rule.

Kahn's method:

1. Compute each node's in-degree: number of unfinished predecessors.
2. Put all zero-in-degree nodes into `ready`.
3. Take one ready node and decrement every successor's in-degree.
4. Add a successor when its in-degree becomes zero.
5. If final processed count is lower than node count, one or more dependency cycles block the remaining nodes.

With no priority, the process is $O(V+E)$. Selecting the next ready task from a heap adds $O(\log V)$ per heap insertion/removal.

## What still works with a cycle

A cycle means no complete topological order covers **all nodes**. It does not mean no node can start. Acyclic components unrelated to the cycle may still run; cycle nodes and downstream dependents are eventually blocked.

`TopologicalSorter.prepare()` raises `CycleError` when it detects a cycle, but a caller can still obtain runnable nodes through `get_ready()`. If an error reports “remaining blocked nodes,” do not call every blocked node a cycle member: a downstream node can be blocked only by a cycle. Precise cycle-member reporting needs separate strongly-connected-component or cycle-path analysis and is not required in this course.

## Two ways to use `TopologicalSorter`

Static ordering:

```python
from graphlib import TopologicalSorter

predecessors = {
    "extract": set(),
    "validate": {"extract"},
    "summarize": {"validate"},
}
order = tuple(TopologicalSorter(predecessors).static_order())
```

Peer order in `static_order()` can depend on insertion order. If a result must replay byte-for-byte, define a tie rule when building input or in a custom ready-selection layer. Concurrent `prepare()` / `get_ready()` / `done()` manages dependency availability only; it does not execute threads, handle failure, or persist state for you.

## Exercises

1. Write both predecessor and successor maps for “read → parse → validate → index.”
2. Hand-calculate in-degrees and at least one topological order for a chain, diamond, and independent components.
3. Add `index → parse` to make a cycle; distinguish cycle members from downstream nodes blocked by the cycle.
4. Traverse a graph with a back edge using `reachable` and prove that each node appears once.
5. Compare adjacency-list and matrix space growth for 10,000 nodes and 20,000 edges; do not invent fixed byte counts.

## Self-check

- [ ] How is “A depends on B” represented in a predecessor map?
- [ ] Why does BFS add `seen` at enqueue time?
- [ ] Is a DAG's topological order necessarily unique?
- [ ] Does a graph cycle stop all unrelated nodes?
- [ ] Are all remaining blocked nodes necessarily in a cycle?
- [ ] Do `TopologicalSorter` mapping values mean predecessors or successors?

## Next step and related concepts

- Next: [[data-structures/05-engineering-selection/10-structure-composition-capacity-boundaries-and-performance-diagnosis|Structure Composition, Capacity Boundaries, and Performance Diagnosis]].
- See [[workflow-automation/00-index|Workflow Automation]] for workflow execution, state recovery, and retry.

## References

Retrieved on **2026-07-14**.

- [Python 3.14: `graphlib`](https://docs.python.org/3.14/library/graphlib.html)
- [MIT OCW 6.006: Graph Search](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/pages/lecture-notes/)
