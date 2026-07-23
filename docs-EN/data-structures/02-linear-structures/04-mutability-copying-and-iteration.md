---
title: "Mutability, Copying, and Iteration"
tags: [ ai-agent-engineer, data-structures, python ]
aliases: [ Python mutability, Python iterators and generators ]
lang: en
translation_key: "数据结构基础/02-线性结构/04-可变性复制与迭代.md"
translation_source_hash: e9c88ce0ac646f7b4b79f9284327cefd7969c4d293b27d4603034b2bd2c38210
translation_route: zh-CN/数据结构基础/02-线性结构/04-可变性复制与迭代
translation_default_route: zh-CN/数据结构基础/02-线性结构/04-可变性复制与迭代
---

# Mutability, Copying, and Iteration

## Objective

Understand that variables bind objects, the layers of mutability and copying, and how to prevent accidental sharing of Agent state. Distinguish iterables, iterators, and generators, and reduce peak memory when downstream processing remains streaming.

## Sequence recap

Sequences arrange elements by position and normally support:

```python
messages = ["system", "user", "assistant"]

print(messages[0])   # First element.
print(messages[-1])  # Last element.
print(messages[1:])  # A new list from index 1 to the end.
print(len(messages))
```

Indexes start at 0. A `start:stop` slice includes `start` and excludes `stop`. Accessing one nonexistent index raises `IndexError`; an out-of-range slice is safely truncated.

## `list`, `tuple`, and `str`

| Type | Mutable? | Common uses |
| --- | --- | --- |
| `list` | Mutable | Messages, steps, batch results |
| `tuple` | The tuple itself is immutable | Fixed coordinates, immutable record fragments, unpacking |
| `str` | Immutable | Text, IDs, and string path representations |

“A tuple is immutable” means that a position cannot be rebound. If a tuple contains a list, that list can still be changed:

```python
record = ("run-1", ["created"])
record[1].append("finished")  # Legal: mutate the nested list.
```

An immutable container therefore does not automatically make the whole nested object tree immutable.

## Aliasing: two variables can refer to one list

```python
history = ["hello"]
backup = history
backup.append("world")
print(history)  # ['hello', 'world']
```

Assignment does not copy a list; it binds two names to the same object. To obtain an independent outer list:

```python
backup = history.copy()
```

But this is a **shallow copy**. If elements are themselves lists or dictionaries, nested objects remain shared:

```python
messages = [{"role": "user", "content": "hi"}]
snapshot = messages.copy()
snapshot[0]["content"] = "changed"
print(messages[0]["content"])  # changed
```

To isolate nested state, create new dictionaries, use `copy.deepcopy`, or design immutable data. First decide which layers may change; do not blindly deep-copy a large context.

## The mutable-default-argument trap

```python
# Incorrect: one list is shared across calls.
def add_message(message, history=[]):
    history.append(message)
    return history


# Correct: create a new list whenever none is passed.
def add_message(message, history=None):
    if history is None:
        history = []
    history.append(message)
    return history
```

Shared mutable state is particularly risky when an Agent processes multiple tasks in parallel. Isolate state by `run_id` and update it through a clear interface.

## Modifying a container while iterating

Removing or inserting list items during iteration changes later indexes and can cause skipped items:

```python
items = [1, 2, 3, 4]
for value in items.copy():
    if value % 2 == 0:
        items.remove(value)
```

A clearer approach is normally to create a new list: `items = [x for x in items if x % 2 != 0]`. Adding or deleting entries while iterating a dictionary view can raise `RuntimeError` or skip entries; iterate a snapshot of keys with `list(mapping)`, or collect keys to delete first. Concurrent tasks still need higher-level synchronization: copying a key list is not concurrency control.

## Iterable, iterator, and generator

- An **iterable** can be passed to `iter()`, such as a list, tuple, dictionary, or file.
- An **iterator** yields items one at a time through `next()` and signals completion with `StopIteration`.
- A **generator** is an iterator produced by a generator expression or a function containing `yield`, retaining execution state.

```python
def batched_ids(prefix: str, count: int):
    for index in range(count):
        yield f"{prefix}-{index}"


ids = batched_ids("run", 3)
print(next(ids))  # run-0
print(list(ids))  # ['run-1', 'run-2']; the generator continues and is exhausted.
print(list(ids))  # []
```

The same generator object is a one-shot iterator and does not reset after exhaustion; call the generator function again to create a new object. If multiple steps need independent reads, have each create a generator or deliberately materialize an immutable snapshot. Do not implicitly share a half-consumed iterator with multiple consumers.

## Streaming does not automatically save memory

```python
def normalized(lines):
    for line in lines:
        cleaned = line.strip()
        if cleaned:
            yield cleaned
```

Peak memory falls only when the downstream consumer also processes items one at a time:

```python
for line in normalized(source):
    process(line)
```

`list(normalized(source))` materializes every value again. A generator can also delay read or parse errors until consumption; define resource closing, error location, and whether repeat traversal is allowed. [[document-parsing/00-index|Document Parsing]] develops large-file chunking; this lesson covers only Python iteration semantics.

## List comprehensions: transformation, not hidden side effects

```python
latencies = [120, 250, 80, 500]
slow = [value for value in latencies if value >= 200]
```

Comprehensions suit building a new collection. If logic includes network calls, exception handling, or multistep state updates, an ordinary `for` loop is clearer.

## Exercises

1. Predict this output, then run it:

```python
a = [[1], [2]]
b = a.copy()
b[0].append(9)
print(a)
```

2. Write `last_n(messages, n)`: return the last `n` messages without changing the original list; return an empty list for `n <= 0`.
3. Represent `(tool_name, call_id)` as a tuple and unpack its two fields.
4. Explain why giving the same `history` list to two concurrent tasks makes their state leak into one another.
5. Write a `non_empty(lines)` generator and show that it can be consumed only once; then write a factory that gives two consumers independent generators.
6. Delete dictionary keys during iteration, observe the error, then change it to “collect first, delete later.”

## Self-check

1. Which indexes does `items[1:3]` include?
2. Can a `tuple` contain a `list`? Can that list change?
3. Why can `copy()` not isolate every nested object?
4. When should an ordinary loop be preferred to a list comprehension?
5. What is the distinction between an iterable and an iterator?
6. Why can a generator lower peak memory only when downstream processing stays streaming?
7. After a generator is consumed by `list()`, can it be read again from the beginning?

## Next step and related concepts

Next: [[data-structures/02-linear-structures/05-stacks-queues-and-deques|Stacks, Queues, and Deques]].

## References

Retrieved on **2026-07-14**.

- [Python 3.14: Sequence Types](https://docs.python.org/3.14/library/stdtypes.html#sequence-types-list-tuple-range)
- [Python 3.14: Iterators](https://docs.python.org/3.14/tutorial/classes.html#iterators)
- [Python 3.14: Generators](https://docs.python.org/3.14/tutorial/classes.html#generators)
- [Python 3.14: Data Model](https://docs.python.org/3.14/reference/datamodel.html)
