---
title: "Python Log Parser Project and Self-Test"
tags:
  - ai-agent-engineer
  - regular-expressions
  - integrated-practice
aliases:
  - Regex Log Parser Project
source_checked: 2026-07-14
source_baseline:
  - Python 3.14.6 re documentation
lang: en
translation_key: "正则表达式/07-Python日志解析项目与自测.md"
translation_source_hash: 4b85ac6757b2592890d3d7d67e488c0066aa2605da12b3026a7c2388db24eec3
translation_route: zh-CN/正则表达式/07-Python日志解析项目与自测
translation_default_route: zh-CN/正则表达式/07-Python日志解析项目与自测
---

# Python Log Parser Project and Self-Test

## Project goal

Read a fictional Agent execution log, extract timestamp, level, run ID, latency, and message into dictionaries, and explicitly reject lines whose format does not conform. The project uses only the Python standard library and does not connect to a real log system.

## Input contract

Each line has this format:

~~~text
2026-07-13T10:00:01Z level=INFO run_id=r1 latency_ms=120 message="completed"
~~~

Constraints:

- The timestamp uses a fixed UTC 'Z' form and ASCII digits. This project checks only its shape, not whether the date really exists.
- 'level' permits only 'INFO', 'WARNING', and 'ERROR'.
- 'run_id' has length 1 through 64 and permits only ASCII letters, digits, underscores, and hyphens.
- 'latency_ms' permits only ASCII digits and must be no greater than '300000' after conversion. That limit is a teaching contract, not a general threshold for every system.
- 'message' cannot contain a double quote or newline. A real system should use structured logging rather than continually expanding this regex.

## Why use a full match

With only 'search', malicious or damaged text before or after a line could be ignored. The project uses 'fullmatch' so the whole line must meet the contract. '^'/'$' and multiline mode have contextual details, while 'fullmatch' states the intent more directly for complete-record validation.

## A readable pattern

The script uses 're.VERBOSE' to put the pattern on separate lines and add comments. The Python pattern is a raw string, 'r"..."', which reduces Python's first-pass handling of backslashes. A readable pattern is not automatically performance-safe, so boundary tests are still required.

## Run it

Run these commands from the project root that contains both 'docs-EN/' and '.website/':

~~~powershell
Push-Location -LiteralPath 'docs-EN\regular-expressions'
python .\examples\log_parser.py
python -m unittest discover -s .\examples -p 'test_*.py' -v
Pop-Location
~~~

Expected output:

~~~text
parsed=3 errors=1 max_latency_ms=2200
line 3: invalid log format
all checks passed
~~~

'sample.txt' intentionally contains one malformed record. The script reports its line number; the demonstration records errors while it processes lines and must not silently discard failures in production. The unit-test run should show all nine tests passing.

Implementation: [[regular-expressions/examples/log_parser.py|log_parser.py]] | Tests: [[regular-expressions/examples/test_log_parser.py|test_log_parser.py]] | Sample: [[regular-expressions/examples/sample.txt|sample.txt]].

> [!success] Local verification for this revision
> On 2026-07-14, the script was run under Python 3.11.9 in ordinary and '-O' modes; nine 'unittest' cases and syntax compilation for both Python files also passed. The generated '__pycache__' was removed. This result verifies the fixed local fixture and test contract, not compatibility with every third-party regex engine.

## Code-reading order

1. The named groups in 'LOG_PATTERN' determine the output fields.
2. 'parse_line' uses 'fullmatch' and raises a line-numbered exception on failure.
3. Captured numeric text is converted to 'int', then checked against the range.
4. 'parse_file' reads UTF-8 one line at a time and stores successful records and errors separately.
5. 'main' checks the fixed sample result and returns a nonzero status on failure; it does not rely on 'assert', which 'python -O' can remove.
6. 'test_log_parser.py' independently covers structure, Unicode digits, numeric and run-ID boundaries, a long message, file line numbers, and literal escaping.

## Literal text must be escaped

If a user needs to search for the literal text 'agent.v2+beta', it cannot be pasted into a regex because '.' and '+' have special meanings:

~~~python
import re

literal = "agent.v2+beta"
pattern = re.compile(re.escape(literal))
assert pattern.search("use agent.v2+beta now")
~~~

're.escape' is for literal portions of a pattern and should not be applied indiscriminately to replacement strings.

## Extension tasks

1. Add a 'DEBUG' level and positive, negative, and statistics assertions.
2. Separate errors into structural errors and numeric-range errors while preserving exact line numbers.
3. Allow escaped double quotes in messages. State the input contract first, then change the pattern and tests.
4. Add a product prefix or case rule to run IDs. Add negative cases before changing the pattern.
5. In a controlled test, add and time a long approximate-failure input, recording environment, length, and result. Do not magnify dangerous patterns in a production process.
6. Change the log to one JSON object per line and compare the maintenance cost of a standard parser and regex.

## When to stop increasing regex complexity

Prefer a dedicated parser when nested structure, arbitrary escaping, multiline syntax, recursion, or precise error recovery appears. JSON, HTML, programming languages, and natural language should not be completely parsed with one continually growing regex.

## Self-check

1. How does '^' inside a character class differ from '^' at the start of a pattern?
2. Do greedy and lazy quantifiers mean “slow” and “fast,” respectively?
3. How do you choose among capturing, noncapturing, and named groups?
4. Why do lookahead and lookbehind not consume matched text?
5. Which escaping layer does a Python raw string address?
6. Which tasks suit 'search', 'match', and 'fullmatch'?
7. Why can user input not be pasted directly into a pattern?
8. What kind of structure commonly causes catastrophic backtracking?
9. Why can the same pattern behave differently in JavaScript, Python, and grep?
10. Why can a regex that validates an email shape not prove that the address exists?

## Project acceptance

- [ ] The script and 'unittest' run successfully in the current Python 3 environment.
- [ ] I can explain every named group and boundary in the pattern.
- [ ] Invalid lines are not silently discarded and report an exact line number.
- [ ] At least two new positive cases, two negative cases, and one long-input test have been added.
- [ ] User literal input passes through 're.escape'.
- [ ] I can explain when to switch to JSON or a dedicated parser.

When finished, return to the [[regular-expressions/00-index|Regular Expressions index]].

## References

Checked: **2026-07-14**.

- [Python standard library: re](https://docs.python.org/3/library/re.html)
- [Python Regular Expression HOWTO](https://docs.python.org/3/howto/regex.html)
- [GNU grep: Regular Expressions](https://www.gnu.org/software/grep/manual/html_node/Regular-Expressions.html)
