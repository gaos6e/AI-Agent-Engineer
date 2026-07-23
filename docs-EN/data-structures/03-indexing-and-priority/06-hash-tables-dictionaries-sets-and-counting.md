---
title: "Hash Tables, Dictionaries, Sets, and Counting"
tags: [ ai-agent-engineer, data-structures, hashing ]
aliases: [ Python dict and set primer, hash tables and counting ]
lang: en
translation_key: "数据结构基础/03-索引与优先/06-哈希表字典集合与计数.md"
translation_source_hash: ab47c3cbcfc5d55f289e78983278ebbff32ae76a58f6c707ddd72f44d1b35107
translation_route: zh-CN/数据结构基础/03-索引与优先/06-哈希表字典集合与计数
translation_default_route: zh-CN/数据结构基础/03-索引与优先/06-哈希表字典集合与计数
---

# Hash Tables, Dictionaries, Sets, and Counting

## Objective

Use dictionaries for key-value mappings, sets for unique membership, and `Counter` for frequencies. Understand the boundaries around hashing, hashable keys, order, absent values, and idempotent deduplication.

## Dictionary: find a value from a key

```python
tools = {
    "search": {"read_only": True},
    "send_email": {"read_only": False},
}

print(tools["search"])
print(tools.get("unknown"))  # Returns None when absent.
```

Dictionary keys must be unique. `tools["unknown"]` raises `KeyError`; use `get` where absence is a normal branch, but use a membership test when `None` is also a valid value:

```python
if "unknown" not in tools:
    print("tool is not registered")
```

Do not expect `dict.get(key, expensive_call())` to call the function only for an absent key: function arguments are evaluated first. Write an explicit `if` when that behavior matters.

Python dictionaries preserve insertion order, but that does not mean keys are sorted. Deleting and reinserting normally moves an item to the end; if an interface requires output by key, time, or priority, use `sorted(...)` explicitly and test it. A set has no guaranteed iteration order you can rely on; sort it or maintain a separate ordering structure before deterministic output.

## Set: only membership matters

```python
seen_call_ids = set()

call_id = "call-42"
if call_id in seen_call_ids:
    raise ValueError("duplicate call")
seen_call_ids.add(call_id)
```

A set removes duplicates automatically and supports union `|`, intersection `&`, and difference `-`. It does not retain duplicate counts; use a dictionary or `collections.Counter` to count them.

## `Counter` and `defaultdict`

```python
from collections import Counter, defaultdict

errors = Counter(["timeout", "rate_limit", "timeout"])
print(errors["timeout"])  # 2
print(errors["missing"])  # 0; no KeyError.

by_tool: defaultdict[str, list[str]] = defaultdict(list)
by_tool["search"].append("run-1")
```

`Counter` expresses counting semantics, not merely “a dictionary with default value 0”; inspect the documentation for behavior involving zero/negative counts and set-like operations. `defaultdict` calls its `default_factory` only when `__getitem__` accesses an absent key; `mapping.get(key)` does not trigger the factory. Do not let an apparently read-only query unexpectedly create a large number of keys.

## A minimum intuition for hashing

Dictionaries and sets use a hash value to help locate a slot. A key needs to retain hashable semantics while used as a key, so strings, integers, and tuples containing only hashable elements normally work; lists and dictionaries do not.

```python
cache = {}
cache[("model-a", "prompt-v1")] = "result"

mutable_key = ["model-a", "prompt-v1"]
# cache[mutable_key] = "result"  # TypeError
```

Different keys can have hash collisions, so runtime lookup compares further when necessary. Average $O(1)$ lookup is not a cryptographic security guarantee; do not treat built-in `hash()` as a stable persistent ID because it is not guaranteed to be stable across processes.

## Nested state and safe updates

```python
runs = {
    "run-1": {"status": "queued", "attempt": 0},
}

run = runs["run-1"]
run["attempt"] += 1
run["status"] = "running"
```

`run` and `runs["run-1"]` refer to the same nested dictionary. This makes updates convenient, but concurrent environments need locks, transactions, or an external state store. Do not assume one dictionary line constitutes a complete business-level atomic operation.

## Deduplication and idempotency are different

- **Deduplication** identifies whether the same identifier has appeared.
- **Idempotency** means repeating the same business request produces no additional side effect.

An in-memory set can detect a duplicate `call_id` in the current process, but loses it after a process restart and is not shared among instances. Writes such as sending messages or charging money need a persistent idempotency key and a storage operation that keeps “check and write result” consistent.

## Hashing and equality must agree

If two objects compare equal with `==`, they must produce the same hash to be safely used as keys. A custom mutable object that participates in equality comparisons normally must not change fields that affect equality or hashing after it is inserted. Built-in `hash()` is also not guaranteed to be stable across processes, so it cannot replace a content digest, database primary key, or idempotency key.

## Exercises

1. Convert a tool list into a `tool_name → read_only` dictionary.
2. Given capability sets for two models, find shared capabilities and those available only in the first model.
3. Count a batch of error codes with `Counter`.
4. Design an idempotency record containing at least a request key, status, result reference, and creation time.
5. Verify that `defaultdict.get("missing")` does not create a key while `mapping["missing"]` does, then explain why.
6. Before serializing a set directly to JSON, design deterministic sorting and a strategy for incomparable elements.

## Self-check

1. Why can a list not be a dictionary key?
2. How should you choose between `mapping[key]` and `mapping.get(key)`?
3. What information does set deduplication discard?
4. Why is an in-memory set insufficient to guarantee idempotency for a production write?
5. Does insertion-order preservation mean dictionary keys are sorted?
6. Does `defaultdict.get()` invoke `default_factory`?

## Next step and related concepts

Next: [[data-structures/03-indexing-and-priority/07-heaps-and-stable-priority-queues|Heaps and Stable Priority Queues]].

## References

Retrieved on **2026-07-14**.

- [Python 3.14: Sets and Dictionaries](https://docs.python.org/3.14/tutorial/datastructures.html#sets)
- [Python 3.14: Mapping Types](https://docs.python.org/3.14/library/stdtypes.html#mapping-types-dict)
- [Python 3.14: `collections`](https://docs.python.org/3.14/library/collections.html)
- [Python 3.14 Data Model: `__hash__`](https://docs.python.org/3.14/reference/datamodel.html#object.__hash__)

