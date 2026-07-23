---
title: "Trees and Hierarchical Traversal"
tags:
  - ai-agent-engineer
  - data-structures
  - tree
aliases:
  - Tree Introduction
  - Tree DFS and BFS
lang: en
translation_key: "数据结构基础/04-关系结构/08-树与层级遍历.md"
translation_source_hash: cd781cb3aa317c51110c94393d223f26939dd5b1464e94fe96f68441604c022a
translation_route: zh-CN/数据结构基础/04-关系结构/08-树与层级遍历
translation_default_route: zh-CN/数据结构基础/04-关系结构/08-树与层级遍历
---

# Trees and Hierarchical Traversal

## Objective

Represent a hierarchy below one root as a tree; understand roots, parents, children, leaves, depth, and subtrees; traverse it with depth-first search (DFS) and breadth-first search (BFS); and bound untrusted nesting depth and node count.

## A tree: one node to many children

Common tree terms are root, parent, child, leaf, and depth. A file hierarchy, nested JSON object, or decision steps can all be viewed as a tree.

```python
tree = {
    "label": "root",
    "children": [
        {"label": "option-a", "children": []},
        {"label": "option-b", "children": []},
    ],
}
```

When traversing, decide explicitly between DFS (go deep first) and BFS (process one level at a time). Both visit every node once; their differences are visit order and auxiliary space.

## Iterative DFS

```python
def node_parts(value: object) -> tuple[str, list[object]]:
    if not isinstance(value, dict):
        raise ValueError("tree node must be an object")
    if set(value) != {"label", "children"}:
        raise ValueError("tree node fields must be exactly label and children")
    label = value["label"]
    children = value["children"]
    if not isinstance(label, str) or not isinstance(children, list):
        raise ValueError("invalid tree node format")
    return label, children


def dfs_labels(root: object, *, max_nodes: int = 1_000) -> list[str]:
    if max_nodes < 1:
        raise ValueError("max_nodes must be at least 1")
    result: list[str] = []
    stack = [root]
    while stack:
        if len(result) >= max_nodes:
            raise ValueError("tree node count exceeds limit")
        node = stack.pop()
        label, children = node_parts(node)
        result.append(label)
        # Push in reverse so the leftmost original child is visited first.
        stack.extend(reversed(children))
    return result
```

An explicit stack avoids using Python recursion depth as input control, but total nodes, maximum depth, and children per node still need limits. To focus on traversal, this example omits full recursive Schema validation. Validate untrusted input level by level before or during traversal.

## BFS and levels

```python
from collections import deque


def bfs_levels(
    root: object, *, max_depth: int = 100, max_nodes: int = 1_000
) -> list[tuple[int, str]]:
    if max_depth < 0 or max_nodes < 1:
        raise ValueError("invalid max_depth/max_nodes limit")
    result: list[tuple[int, str]] = []
    queue = deque([(root, 0)])
    while queue:
        if len(result) >= max_nodes:
            raise ValueError("tree node count exceeds limit")
        node, depth = queue.popleft()
        if depth > max_depth:
            raise ValueError("tree depth exceeds limit")
        label, children = node_parts(node)
        result.append((depth, label))
        queue.extend((child, depth + 1) for child in children)
    return result
```

BFS suits level-by-level display or finding the shallowest matching node. DFS suits subtree processing, path search, and explicit entry/exit semantics. Neither is automatically best.

## Trees, DAGs, and general graphs

A tree normally has one root, exactly one parent for every non-root node, and no cycle. A DAG can give a node several predecessors; a general graph can also contain cycles. A folder hierarchy is a tree, but mutual note links are usually a graph. Do not assume that a business relation is a tree merely because its data is nested JSON.

## Resource and security boundaries

- Bound maximum depth, total node count, children per node, and label length.
- Do not let user input control unbounded recursion.
- If a structure can share nodes or contain back edges, use `visited`; it is no longer a strict tree.
- State output order explicitly; do not rely on set iteration.
- When calculating paths, choose between copying lists and reconstructing from parent pointers to avoid excessive path copies.

## Exercises

1. Draw a three-level directory as a tree; mark root, internal nodes, leaves, and maximum depth.
2. Hand-calculate DFS and BFS orders for one seven-node tree, then run code to verify them.
3. Extend BFS to fail immediately past `max_depth` and write boundary tests.
4. Write `leaf_labels(root)` without modifying input; test no children, one node, and multiple branches.
5. Give an example that looks hierarchical but is actually a multi-parent DAG.

## Self-check

1. What are the root, leaf, and depth of a tree?
2. Which auxiliary structure does DFS use, and which does BFS use?
3. Why does iterative DFS still need depth/node limits?
4. Is a hierarchy with multiple parents still a strict tree?
5. Why use `visited` if input can have a back edge?

## Next step and related concepts

Next: [[data-structures/04-relational-structures/09-graphs-dependencies-and-topological-order|Graphs, Dependencies, and Topological Order]].

## References

Retrieved on **2026-07-14**.

- [MIT OCW 6.006: Graph Search](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/pages/lecture-notes/)
- [Python 3.14: `collections.deque`](https://docs.python.org/3.14/library/collections.html#collections.deque)
