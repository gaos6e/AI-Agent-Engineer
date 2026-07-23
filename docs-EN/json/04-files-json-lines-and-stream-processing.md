---
title: "Files, JSON Lines, and Stream Processing"
tags:
  - ai-agent-engineer
  - JSON
  - JSONL
  - file-processing
aliases:
  - JSON Lines
  - Safe JSON file writes
source_checked: 2026-07-14
lang: en
translation_key: "JSON/04-文件、JSON Lines与流式处理.md"
translation_source_hash: 66528ba35cdb99b79fe6b0b41ba7fedaefcb0e2a448675d159f692f656b520a3
translation_route: zh-CN/JSON/04-文件、JSON-Lines与流式处理
translation_default_route: zh-CN/JSON/04-文件、JSON-Lines与流式处理
---

# Files, JSON Lines, and Stream Processing

## Goals

Choose an appropriate format for “one complete state” versus “many independent records”; locate JSONL errors line by line, limit file resources, and atomically replace one output file; and accurately explain that atomic replacement is not a transaction, concurrency control, or an absolute power-loss durability guarantee.

## A single JSON document has no record framing

One `.json` document represents one JSON value. This code writes two objects consecutively, but the complete file is not valid JSON text:

```python
import json

with open("events.json", "w", encoding="utf-8") as file:
    json.dump({"id": 1}, file)
    json.dump({"id": 2}, file)
```

The right alternative depends on the access pattern:

- One small configuration or state snapshot: write one object.
- A small ordered collection that must be read as a whole: write an array.
- A continuously appended log or record-by-record dataset: agree on JSON Lines/NDJSON.
- A formal IETF sequence format: evaluate RFC 7464 JSON Text Sequences.
- Large-scale random queries and concurrent updates: use a database or log system; do not force a JSON file to act like a database.

## JSON Lines means “one JSON value per physical line”

A common `.jsonl` file:

```text
{"event_id":"evt-0001","type":"tool_requested"}
{"event_id":"evt-0002","type":"tool_validated"}
```

Each line is valid JSON independently; the whole file is usually not a valid single-document JSON array. The JSON Lines community convention normally requires UTF-8, no BOM, and one value per line, and recommends a final LF. A blank line is not a JSON value; receivers should explicitly decide whether to reject it, skip it, or record a warning.

The escaped logical newline `\n` inside a string does not split the physical record:

```text
{"message":"first\nsecond"}
```

Producers must use a JSON encoder to escape a real newline, not concatenate lines by hand.

## JSONL, NDJSON, and JSON Text Sequences are not identical

| Format | Delimiter | Standard status and common media type | Important distinction |
| --- | --- | --- | --- |
| JSON | one value | RFC 8259; `application/json` | Has no multi-record framing. |
| JSON Lines | one JSON value per line | community convention; `.jsonl` | No universal IETF rule for blank lines or a MIME type. |
| NDJSON | LF after each JSON text | community specification; commonly `application/x-ndjson` | Very close to JSONL, but receiver rules still need agreement. |
| JSON Text Sequences | RS `0x1E` before each text, LF after it | RFC 7464; `application/json-seq` | RS can help recover after a damaged record; it is not ordinary newline-delimited JSONL. |
| JSON5 | extended syntax | separate format | Comments, trailing commas, and single quotes are not standard JSON. |

A protocol document must state the format name, encoding, blank-line policy, final-newline policy, top-level record type, error recovery, and size limits. It is not enough to say “returns a JSON stream.”

## Line-by-line processing must retain physical line numbers

```python
import json
from pathlib import Path


def read_objects(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                raise ValueError(f"blank record at line {line_number}")
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON at physical line {line_number}") from error
            if type(value) is not dict:
                raise ValueError(f"record at line {line_number} must be an object")
            records.append(value)
    return records
```

This is a minimum pattern, but it still accepts duplicate keys, `NaN`, and unlimited-length lines. The project’s `scan_json_lines` reads bytes, limits line size/record count/total bytes, strictly decodes UTF-8, and turns per-line errors into results that omit the original payload so later valid records can still be processed. The project defines the “single-line limit” as the UTF-8 byte count of that record’s JSON text, excluding LF/CRLF; the total-file limit includes delimiters. Readers and writers use the same definition and test exact-limit and limit+1 behavior.

## Failure policy depends on the scenario

When line 17 is damaged, you can:

- **fail fast**: configuration imports and financial batches require all-or-nothing;
- **isolate bad records and continue**: for telemetry, crawling, or training-data preprocessing, but emit line numbers and failure counts;
- **retry the source**: a network chunk may be truncated; first determine whether the protocol permits recovery;
- **send it to a dead-letter queue**: preserve controlled evidence for human handling without writing sensitive payloads to ordinary logs.

“Skipping errors” without a count, alert, and replay policy disguises data loss as success.

## Limit bytes before parsing, not character count after reading

The number of UTF-8 characters does not equal the number of bytes. A safe small-file read pattern is:

1. Open in binary mode.
2. Read only `max_bytes + 1`.
3. Reject immediately if the limit is exceeded.
4. Reject a BOM and decode as strict UTF-8.
5. Apply unique-key, numeric, and structural limits.
6. Then perform Schema and business validation.

Calling `stat()` before an unbounded `read_text()` leaves a change window between check and read and can allocate too much memory at once. The project reads a bounded amount directly.

## Atomic replacement avoids exposing half a file

Do not truncate the target path and slowly write into it. A common single-file pattern is:

```python
import json
import os
from pathlib import Path
import tempfile


def replace_json(path: Path, value: object) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary = Path(file.name)
            json.dump(value, file, ensure_ascii=False, allow_nan=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
```

The important points are: create the temporary file in the target’s directory, close its handle before `os.replace` on Windows, and clean it up after an exception. The project also verifies that the old target remains intact after an encoding failure and a simulated replacement failure.

## Boundaries of atomic replacement

It solves only part of the problem: after a successful replacement, readers normally see the old complete file or the new complete file, rather than a partial file. It does not automatically provide:

- protection from lost updates when two processes both “read–modify–write”;
- consistent multi-file commits;
- database isolation levels;
- absolute durability after power loss on all platforms and file systems;
- the same semantics on a network share;
- version-conflict detection, locks, or compare-and-swap.

For concurrent state, introduce version numbers, file locks, or transactional storage, then validate with fault injection on the target platform.

## Common errors and troubleshooting

- Passing a complete JSONL file to `json.load`: read it line by line, or use an array.
- Calling `line.strip()` before parsing and losing the original line number: remove only protocol-permitted CR/LF and preserve the physical position.
- Allowing an unlimited-length line: use bounded `readline` or a bounded streaming parser.
- Continuing silently after a line fails: emit an explicit status and totals, then decide the exit code.
- Truncating configuration in place: write a same-directory temporary file, flush, fsync, close, and replace.
- Describing atomic replacement as a transactional database: document file-level and concurrency boundaries.

## Exercises

1. Convert a three-element JSON array into three JSONL lines, then read it back line by line while retaining line numbers.
2. Construct four samples: a blank line, a damaged second line, an oversized line, and no final LF; define a policy for each.
3. Test an atomic write in a temporary directory; simulate a serialization failure and prove the old file did not change.
4. Compare the delimiter mechanisms of JSONL and RFC 7464 when recovering from a damaged record.
5. Design a concurrent Agent-state scenario that needs a database rather than a JSON file.

## Self-test

1. Why do two calls to `json.dump` not automatically form two records?
2. Does `\n` in a JSON string split a JSONL physical line?
3. How do JSON Lines and `application/json-seq` differ in their delimiters?
4. Why limit bytes before decoding UTF-8?
5. Can `os.replace` prevent two writers from overwriting one another’s updates?

## Summary and next step

A file format determines record boundaries; atomic replacement guarantees only limited single-file visibility. The next lesson uses JSON Schema to describe the shape every record should have: [[json/05-json-schema-core-contracts|JSON Schema Core Contracts]]. Return to the [[json/00-index|JSON Learning Index]].

## References

Source review date: **2026-07-14**.

- [JSON Lines](https://jsonlines.org/)
- [NDJSON specification](https://github.com/ndjson/ndjson-spec)
- [RFC 7464: JSON Text Sequences](https://www.rfc-editor.org/rfc/rfc7464.html)
- [Python `os.replace`](https://docs.python.org/3/library/os.html#os.replace)
- [Python `tempfile.NamedTemporaryFile`](https://docs.python.org/3/library/tempfile.html#tempfile.NamedTemporaryFile)
