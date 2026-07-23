---
title: "Data Structures, Abstract Data Types, and Invariants"
tags: [ ai-agent-engineer, data-structures, ADT, invariants ]
aliases: [ Data-structure selection primer, abstract data types ]
lang: en
translation_key: "数据结构基础/01-基础模型/01-数据结构抽象类型与不变量.md"
translation_source_hash: 6b5af7c61264dad947212b4e779a794226882cfd5003658ff58e28ad7fc62142
translation_route: zh-CN/数据结构基础/01-基础模型/01-数据结构抽象类型与不变量
translation_default_route: zh-CN/数据结构基础/01-基础模型/01-数据结构抽象类型与不变量
---

# Data Structures, Abstract Data Types, and Invariants

## Objective

Start with “which operations must this support?” rather than “how many containers can I remember.” Distinguish data, Abstract Data Types (ADTs), concrete representations, and algorithms, then use invariants to prove a structure remains valid after an update.

## Keep four layers separate

| Layer | Question it answers | Task-scheduling example |
| --- | --- | --- |
| Data element | What is stored? | Task ID, priority, dependency ID |
| ADT / interface | What is allowed? | Add a task, take the next ready task, query status |
| Data structure / representation | How is data organized? | `dict` index, `set` dependencies, `heapq` ready heap |
| Algorithm | How is one operation completed? | Topological progression, heap push/pop, cycle detection |

A queue ADT specifies enqueue and FIFO removal. It can be implemented by `collections.deque`, a persistent messaging system, or another structure. The interface is the requirement; the representation is a solution. Write the interface and constraints first to know which operation costs matter.

## Choose from an operation profile

Before selecting, state:

1. data scale and growth pattern;
2. the most frequent reads, writes, deletions, and traversals;
3. whether order matters, duplicates are allowed, and access is by key or priority;
4. whether in-place mutation is allowed and who owns the object;
5. capacity, persistence, concurrency, and failure requirements; and
6. whether results must be deterministic and replayable.

For the same message batch, `list` is natural when append and whole-batch traversal dominate; `deque(maxlen=100)` suits only the most recent 100 messages; frequent lookup by message ID calls for a `dict` index. There is no best data structure apart from its operations.

## Invariants are rules that always hold

An **invariant** is a condition that must be true after a structure is built and after every public operation completes. For example, a tool registry could require:

- every tool name is unique and non-empty;
- each dictionary key matches the `name` within its tool object;
- every write tool has an explicit approval level; and
- removal leaves no entry in a risk-group auxiliary index.

When maintaining both a list and set:

```python
class OrderedUniqueIds:
    def __init__(self) -> None:
        self._items: list[str] = []
        self._seen: set[str] = set()

    def add(self, item: str) -> bool:
        if item in self._seen:
            return False
        self._seen.add(item)
        self._items.append(item)
        return True

    def snapshot(self) -> tuple[str, ...]:
        assert len(self._items) == len(self._seen)
        assert set(self._items) == self._seen
        return tuple(self._items)
```

One method updates both structures, so callers cannot alter only one. The `assert` statements express internal development-time invariants. Untrusted input still needs ordinary validation and exceptions: optimization mode can remove assertions.

## Preconditions, postconditions, and ownership

- **Precondition**: true before a call, such as a task ID passing format validation.
- **Postcondition**: guaranteed after success, such as finding the new task by ID.
- **Ownership**: who may mutate an object and whether a function copies input.
- **Failure atomicity**: whether failure leaves the structure unchanged or can partially update it.

```text
add_task(task)
Precondition: task.id is non-empty; dependency format is valid
After success: task count +1; by_id[id] refers to the task; no execution before ready
After failure: every index remains as it was before the call
```

This is closer to a verifiable engineering contract than “it uses a dictionary, so it is fast.”

## Abstraction does not mean over-encapsulation

A small script may use `dict` and `set` directly. Introduce a class or module boundary only when multiple locations must maintain invariants together, an implementation must be replaceable, or side effects need control. Do not wrap every list, and do not let callers freely mutate several public containers.

## Exercise: ADT card

Create a card for an Agent tool registry:

1. List `register`, `get`, `remove`, and `list_by_risk`.
2. Write each operation's precondition, success postcondition, and failure behavior.
3. State at least three global invariants.
4. Compare list-only, dictionary-only, and dictionary-plus-group-index representations.
5. Explain which operation determines the final choice.

## Self-check

1. Are a queue ADT and `deque` the same concept?
2. Why list operations before comparing complexity?
3. Which invariant is easiest to break when a list and set are maintained together?
4. Why cannot `assert` validate untrusted input?
5. What must failure atomicity answer?

## Next step and related concepts

- Next: [[data-structures/01-foundation-models/02-complexity-resource-costs-and-measurement|Complexity, Resource Costs, and Measurement]].
- See [[python-fundamentals/00-index|Python Fundamentals]] for functions, exceptions, and testing boundaries.

## References

Retrieved on **2026-07-14**.

- [MIT OCW 6.006: Lecture 2, Data Structures](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/resources/mit6_006s20_lec2/)
- [Python 3.14: Data Structures](https://docs.python.org/3.14/tutorial/datastructures.html)
