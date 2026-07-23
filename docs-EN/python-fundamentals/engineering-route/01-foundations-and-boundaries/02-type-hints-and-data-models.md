---
title: "Type Hints and Data Models"
tags: [ ai-agent-engineer, Python, typing ]
aliases: [ Python type hints, dataclass primer ]
lang: en
translation_key: "Python基础/Agent工程路线/01-基础与边界/02-类型提示与数据模型.md"
translation_source_hash: a60fdeb3775147e4e5523561a5a5b3897ab2fa528c35f4d6afc04aec70ccf630
translation_route: zh-CN/Python基础/Agent工程路线/01-基础与边界/02-类型提示与数据模型
translation_default_route: zh-CN/Python基础/Agent工程路线/01-基础与边界/02-类型提示与数据模型
---

# Type Hints and Data Models

## Objective

By the end of this lesson, you should be able to write type hints for functions, collections, and nullable values; use `dataclass` to express validated domain objects; and explain why static type hints cannot replace runtime input validation.

## Why a dynamic language still needs type hints

Python remains dynamically typed at runtime. Type hints primarily help readers, editors, and static checkers understand a contract; the interpreter normally does not reject an integer merely because a parameter is annotated as `str`.

```python
def normalize_query(query: str, limit: int = 200) -> str:
    cleaned = query.strip()
    if not cleaned:
        raise ValueError("query must not be empty")
    if len(cleaned) > limit:
        raise ValueError(f"query must not exceed {limit} characters")
    return cleaned
```

`query: str` documents an expectation for tools and readers. `isinstance`, length checks, and business rules form the runtime validation.

## Master five common forms first

```python
def find_title(task_id: str) -> str | None: ...

def summarize(items: list[str]) -> dict[str, int]: ...

def choose(value: str, allowed: set[str]) -> str: ...

def pair() -> tuple[str, int]: ...

def render(lines: list[str], *, compact: bool = False) -> str: ...
```

- `str | None` means that no value may be present; it is not an empty string.
- `list[str]` denotes a mutable ordered collection.
- `dict[str, int]` states the expected key and value types.
- `tuple[str, int]` is a fixed-position heterogeneous result.
- Parameters after `*` must be supplied by name, reducing misuse of positional Boolean flags.

Do not use `Any` everywhere in the name of “complete typing.” `Any` tells a static checker to give up its constraints, so restrict it to genuinely untrusted or dynamic boundaries and narrow it to known types promptly.

## Use `dataclass` for validated objects

A dictionary is suitable for parsing external JSON, but a business core full of `value["status"]` makes field spelling and state constraints difficult to track. Validate at the boundary, then convert to an immutable data class:

```python
from dataclasses import dataclass
from typing import Literal

Status = Literal["pending", "running", "done", "failed"]


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    title: str
    status: Status
```

- `frozen=True` prevents ordinary reassignment of fields and suits value objects.
- `slots=True` restricts instance attributes and reduces some overhead.
- `Literal` helps a static checker understand a finite set of strings.

None of these options is a security boundary. JSON parsing must still validate types, empty values, unknown fields, and allowed states; passing an arbitrary string at runtime will not fail merely because `Literal` appears in the annotation.

## Keep external shapes separate from internal objects

A useful data flow is:

```text
Untrusted dict/list
  ↓ parse, validate fields and business rules
Immutable Task
  ↓ pure business functions
Report data model
  ↓ explicit serialization
JSON/CLI/API output
```

Give a parsing function an `object` input so its implementation must explicitly narrow the type:

```python
def parse_task(value: object) -> Task:
    if not isinstance(value, dict):
        raise ValueError("task must be an object")
    # Validate each field next; do not call Task(**value) directly.
    ...
```

Calling `Task(**value)` directly produces only some Python parameter errors. It cannot consistently express unknown fields, empty strings, an allowed state set, or user-facing error locations.

## `TypedDict`, `dataclass`, and ordinary dictionaries

| Choice | Good fit | Caveat |
| --- | --- | --- |
| `dict[str, object]` | Truly dynamic data that has just crossed a boundary | Validate and narrow it quickly |
| `TypedDict` | A stable set of keys still passed as a dictionary | It is mainly static description, not runtime validation |
| `dataclass` | Internal domain objects needing attributes and invariants | Parse external input separately |

`TypedDict` is useful for dictionary shapes required by a framework; `dataclass` is often better for the business core. Do not make a class for every transient two-field dictionary, and do not let untrusted dictionaries pass through the entire system.

Python 3.14 evaluates annotations lazily by default. If a framework reflects on annotations at runtime, do not assume direct `__annotations__` access has exactly the same meaning as earlier releases; prefer `typing.get_type_hints()` and consult the `annotationlib` documentation for lower-level handling. Ordinary business code that does not reflect on annotations need not gain complexity because of this.

## Enum or strings?

`Enum` centralizes finite states and can reduce spelling errors, but JSON still ultimately needs strings. Beginner projects can use strings plus an explicit allowed set; consider `Enum` once a state has behavior or is reused across modules. Whichever you choose, keep parsing, serialization, documentation, and tests aligned.

## Common mistakes

- Treating type hints as runtime validation.
- Using `dict[str, Any]` to let unknown data into every function.
- Using `None`, an empty string, and an absent field for the same meaning without a rule.
- Leaving data classes mutable so multiple steps silently alter the same object.
- Maintaining output types only in code while tool schemas and documentation drift separately.

## Exercise

Design a read-only `search_notes(query, limit, tags)` tool: specify its external JSON shape, internal immutable request and result objects, and runtime validation rules. State the distinct meanings of missing `tags`, an empty array, and `null`.

## Self-check

1. Do type hints automatically reject invalid values at runtime?
2. How does `str | None` differ from an empty string?
3. Why should external JSON not be unpacked directly into a data class?
4. What are the typical boundaries of `TypedDict` and `dataclass`?
5. Can `frozen=True` prove that every nested value in an object is immutable?

## Related concepts and next step

- Learn the computational properties of lists, mappings, and sets in the Data Structures Fundamentals course; review JSON types in the JSON course.
- Next, [[python-fundamentals/engineering-route/01-foundations-and-boundaries/03-functions-modules-and-dependency-injection|Functions, Modules, and Dependency Injection]] puts data models behind testable interfaces.

## References

Retrieved on **2026-07-14**.

- [Python `typing`](https://docs.python.org/3.14/library/typing.html)
- [Python `dataclasses`](https://docs.python.org/3.14/library/dataclasses.html)
- [Python typing specification](https://typing.python.org/en/latest/spec/)
- [Python 3.14: annotation best practices](https://docs.python.org/3.14/howto/annotations.html)
