---
title: "Regular Expressions: Practical Python re and PowerShell APIs"
tags:
  - ai-agent-engineer
  - regular-expressions
  - python
  - powershell
aliases:
  - Practical Python re APIs
  - Practical PowerShell Regex APIs
source_checked: 2026-07-14
source_baseline:
  - Python 3.14.6 re documentation
  - PowerShell 7.6 regular-expression documentation
related: "[[regular-expressions/00-index]]"
lang: en
translation_key: "正则表达式/05A-Python re 与 PowerShell 实用 API.md"
translation_source_hash: fe3abc74c9086410c2d52f05ce769a3bc9ddb55037be5b4e6bfb59dc0b00b096
translation_route: zh-CN/正则表达式/05A-Python-re-与-PowerShell-实用-API
translation_default_route: zh-CN/正则表达式/05A-Python-re-与-PowerShell-实用-API
---

# Regular Expressions: Practical Python re and PowerShell APIs

## Lesson goal

Put patterns into real programs: choose 'search', 'fullmatch', 'finditer', and 'sub' in Python, and correctly use '-match', '$Matches', 'Select-String', and '-replace' in PowerShell. Every example uses only the Python standard library and PowerShell's built-in .NET engine.

## Python: use raw strings first

~~~python
import re

RUN_ID = re.compile(r"[A-Za-z0-9_-]{3,32}")
assert RUN_ID.fullmatch("agent_01") is not None
assert RUN_ID.fullmatch("bad id") is None
~~~

'r"..."' keeps backslashes from being interpreted as much by Python's string syntax; it does not turn off regex syntax. A raw string also cannot end with an odd number of backslashes, so it is not a universal switch for every string problem.

're.compile' puts a pattern and its flags into a reusable object. Python also caches recent module-level patterns, so manual compilation is not an absolute performance requirement. In engineering work, the greater value is usually naming, central configuration, and tests.

## Python: choose an API for the task

| API | Scope checked | Typical use |
| --- | --- | --- |
| 'search' | Finds the first match at any position | Decide whether a line contains the target pattern. |
| 'match' | Attempts only from the start, but permits remaining text | Parse text with a fixed prefix; do not mistake it for whole-field validation. |
| 'fullmatch' | The complete string must match | Validate a complete field or a fixed-format record. |
| 'finditer' | Iterates over all nonoverlapping matches and returns 'Match' objects | Prefer it when text, groups, and start/end positions are needed. |
| 'findall' | Returns all nonoverlapping results, but capture groups affect the return shape | Simple extraction; be careful when groups alter the returned values. |
| 'sub' / 'subn' | Replaces every match or a limited number of them | Redaction and normalization; 'subn' also returns the replacement count. |

~~~python
import re

line = "INFO run_id=r1 parent=r0"
run_id = re.compile(r"\brun_id=(?P<value>[A-Za-z0-9_-]+)\b")

first = run_id.search(line)
assert first is not None
assert first.group("value") == "r1"
assert first.span("value") == (12, 14)

values = [match.group("value") for match in run_id.finditer(line)]
assert values == ["r1"]
~~~

Do not write only 'if match:' and assume that a group necessarily exists. An optional branch can make 'group(...)' return 'None'; write type and boundary tests for important output.

## Named groups and 'groupdict'

~~~python
import re

pattern = re.compile(
    r"level=(?P<level>INFO|WARNING|ERROR)\s+"
    r"latency_ms=(?P<latency_ms>[0-9]+)"
)

match = pattern.fullmatch("level=ERROR latency_ms=2200")
assert match is not None
fields = match.groupdict()
record = {
    "level": fields["level"],
    "latency_ms": int(fields["latency_ms"]),
}
assert record == {"level": "ERROR", "latency_ms": 2200}
~~~

Regex captures text. Numbers, dates, and enumerations still need conversion and business checks after capture. '[0-9]' explicitly means ASCII digits, avoiding Python's default '\d' acceptance of other Unicode decimal digits.

## Flags and readable patterns

~~~python
import re

pattern = re.compile(
    r"""
    ^
    (?P<name>[A-Za-z][A-Za-z0-9_-]{2,31})
    $
    """,
    flags=re.VERBOSE | re.ASCII,
)

assert pattern.fullmatch("agent_01") is not None
~~~

- 're.IGNORECASE' / 're.I': ignore case; Unicode case folding can exceed ASCII intuition.
- 're.MULTILINE' / 're.M': changes the line-boundary meaning of '^' and '$'.
- 're.DOTALL' / 're.S': lets '.' match newlines.
- 're.VERBOSE' / 're.X': allows whitespace and comments; whitespace inside a character class and escaped whitespace have special rules.
- 're.ASCII' / 're.A': gives '\w', '\d', '\s', '\b', and related constructs ASCII semantics; use it only when the contract genuinely requires ASCII.

## Safely insert literal text

If user input is only meant to be searched literally, escape it before putting it in a pattern:

~~~python
import re

literal = "agent.v2+beta"
pattern = re.compile(re.escape(literal))
assert pattern.search("deploy agent.v2+beta now") is not None
assert pattern.search("deploy agentXv22beta now") is None
~~~

're.escape' is for **literal fragments in a pattern**. Replacement strings have a different rule set. If replacement content comes from a variable, prefer a function replacement to avoid misunderstandings about backslashes and group references:

~~~python
import re

replacement = r"archive\1"
result = re.sub(r"TOKEN", lambda _: replacement, "TOKEN")
assert result == replacement
~~~

## PowerShell: matching and '$Matches'

PowerShell uses the .NET regex engine. '-match' is case-insensitive by default; '-cmatch' explicitly distinguishes case:

~~~powershell
$line = 'level=ERROR run_id=r2'
$pattern = '^level=(?<level>INFO|WARNING|ERROR) run_id=(?<runId>[A-Za-z0-9_-]+)$'

if ($line -cmatch $pattern) {
    [pscustomobject]@{
        Level = $Matches.level
        RunId = $Matches.runId
    }
}
~~~

For a successful scalar-input match, '$Matches[0]' holds the overall match and named keys hold captured groups. The next successful scalar match overwrites it; a failed match does not clear the old value, so read it only inside the branch for the current successful match. When a collection is on the left of '-match', PowerShell returns matching elements rather than establishing a dependable '$Matches' value for each element. Loop explicitly to capture each one:

~~~powershell
$pattern = '^run_id=(?<runId>[A-Za-z0-9_-]+)$'
$ids = foreach ($line in 'run_id=r1', 'invalid', 'run_id=r2') {
    if ($line -cmatch $pattern) {
        $Matches.runId
    }
}

if (@($ids).Count -ne 2) {
    throw 'unexpected match count'
}
~~~

## PowerShell: search files and replace

~~~powershell
$path = Join-Path $PWD 'examples\sample.txt'
$errors = Select-String -LiteralPath $path -Pattern 'level=ERROR' -AllMatches

if (@($errors).Count -ne 1) {
    throw 'expected exactly one ERROR line'
}

$normalized = 'name   age' -replace '\s+', ' '
if ($normalized -cne 'name age') {
    throw 'replacement failed'
}
~~~

'Select-String' returns objects with file, line, and match information, which is useful for investigating files. '-replace' replaces every match by default. In a replacement string, '$1' and '${name}' are .NET capture references. Inside a PowerShell double-quoted string they can also trigger variable expansion first, so fixed replacement templates generally use single quotes.

Use '[regex]::Escape' for literal input:

~~~powershell
$literal = 'agent.v2+beta'
$escaped = [regex]::Escape($literal)
if ('use agent.v2+beta now' -cnotmatch $escaped) {
    throw 'literal search failed'
}
~~~

## Common mistakes and investigation

- An online tester did not use the same engine, version, and flags.
- Python 'match' was treated as a full match; field validation should prefer 'fullmatch'.
- 'findall' was used directly: adding one capture group changes results into that group's text, while adding several normally changes them into tuples, silently changing what callers receive.
- A Python pattern with backslashes was written in an ordinary string, or a PowerShell double-quoted pattern accidentally expanded '$'.
- PowerShell '-match' was assumed to be case-sensitive.
- An old '$Matches' value was read outside the branch for the current successful match.
- User literal input was concatenated directly into a pattern, causing pattern-injection or performance risk.

## Practice

1. Use Python 'finditer' to extract the two values and start/end positions from 'run_id=r1 run_id=r2'.
2. Use 'fullmatch' to validate a 3–32 character ASCII run ID, testing an empty value, a space, Chinese text, and 33 characters.
3. Use PowerShell 'Select-String' to find error-level lines in 'examples/sample.txt' and output their line numbers.
4. Use 're.escape' and '[regex]::Escape' respectively to search for the literal string 'a+b.c'.
5. Normalize a text segment with multiple spaces to one space, then assert the replacement count or final result.

## Self-check

- What scope do 'search', 'match', and 'fullmatch' check?
- Why does complex extraction usually prefer 'finditer' over 'findall'?
- Can 're.escape' be applied indiscriminately to replacement strings?
- How do '-match' and '-cmatch' differ in PowerShell?
- Why must '$Matches' be read immediately after a successful scalar match?

Previous: [[regular-expressions/05-flags-and-replacement|Flags and replacement]] | Next: [[regular-expressions/06-performance-and-debugging|Performance and debugging]].

## References

Checked: **2026-07-14**.

- [Python standard library: re](https://docs.python.org/3/library/re.html)
- [Python Regular Expression HOWTO](https://docs.python.org/3/howto/regex.html)
- [Microsoft Learn: PowerShell Regular Expressions](https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_regular_expressions)
- [Microsoft Learn: PowerShell Comparison Operators](https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_comparison_operators)
- [Microsoft Learn: .NET Regular Expressions](https://learn.microsoft.com/dotnet/standard/base-types/regular-expressions)
