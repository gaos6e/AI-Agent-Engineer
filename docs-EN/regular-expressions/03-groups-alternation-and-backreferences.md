---
title: "Regular Expressions: Groups, Alternation, and Backreferences"
date: 2026-07-12
tags:
  - regular-expressions
  - tutorial
  - groups
  - backreferences
aliases:
  - Regex Groups and Backreferences
related: "[[regular-expressions/00-index]]"
lang: en
translation_key: "正则表达式/03-分组、分支与反向引用.md"
translation_source_hash: c4dda93635bd05f41e3b91da5250848a74b165ad79a20633fc23a9f278840814
translation_route: zh-CN/正则表达式/03-分组、分支与反向引用
translation_default_route: zh-CN/正则表达式/03-分组、分支与反向引用
---

# Regular Expressions: Groups, Alternation, and Backreferences

Groups treat several pattern parts as one unit and can retain matched text. Alternation expresses “one of these choices.” Together, they are central to building more complex rules.

## 1. Capturing groups

### What they do

Parentheses '( ... )' create a capturing group. They let the inner pattern participate as a unit in a quantifier or alternation, and retain the matched text for program APIs, backreferences, or replacements. Capturing groups are numbered from left to right starting at 1.

### Syntax

~~~regex
(pattern)
~~~

### Example

~~~regex
(\d{4})-(\d{2})-(\d{2})
~~~

Test text: '2026-07-12'

### Result

The overall match is '2026-07-12'. Capture group 1 is '2026', group 2 is '07', and group 3 is '12'. Languages return capture groups differently: Python uses 'Match.group(1)', while a successful scalar PowerShell '-match' exposes '$Matches[1]'.

## 2. Noncapturing groups

### What they do

'(?: ... )' is a noncapturing group. It groups a pattern, scopes a quantifier, or organizes alternation without retaining inner text. Prefer it for parentheses whose contents do not need to be read: group numbering changes less easily and the pattern is usually clearer.

### Syntax

~~~regex
(?:pattern)
~~~

### Example

~~~regex
(?:https?://)?example\.com
~~~

Test text: 'example.com http://example.com https://example.com'

### Result

All three addresses match: the 's' after 'http' is optional, and the entire protocol portion is optional. The parentheses produce no capture group, so API callers do not need to handle a meaningless protocol group.

## 3. Named capturing groups

### What they do

Named capturing groups give captured text a semantic name instead of relying on fragile numeric positions. JavaScript, .NET, and newer PCRE-style engines commonly use '(?<name>pattern)'; Python's 're' module uses '(?P<name>pattern)'. Name rules also vary slightly by engine.

### Syntax

~~~regex
(?<name>pattern)
~~~

### Example

~~~regex
(?<year>\d{4})-(?<month>\d{2})-(?<day>\d{2})
~~~

Test text: '2026-07-12'

### Result

The overall match is '2026-07-12', and the named groups 'year', 'month', and 'day' retain '2026', '07', and '12'. In Python, write the same rule as '(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'.

## 4. Alternation: '|'

### What it does

The vertical bar '|' selects an alternative: match the left pattern or the right pattern. Groups define its scope; without grouping, alternation can cover more text than intended. Backtracking engines such as Python, ECMAScript, and .NET usually accept the first successful branch from left to right, so put a more specific overlapping branch first. POSIX tools can use a leftmost-longest rule, so do not unconditionally carry branch-order assumptions into grep.

### Syntax

~~~regex
patternA|patternB
(?:patternA|patternB)
~~~

### Example

~~~regex
\b(?:cat|dog)\b
~~~

Test text: 'cat dog catalog bird'

### Result

The results are 'cat' and 'dog'. 'catalog' has no word boundary on its right, so it does not match. The noncapturing group makes '\b' constrain both candidate words.

## 5. Numeric backreferences

### What they do

A backreference matches the same text that a previous capturing group matched. '\1' refers to the first capture group and '\2' to the second. It is useful for duplicate words, paired tags, or repeated separators, but can increase matching complexity and should not be used unnecessarily.

### Syntax

~~~regex
(captured text)\1
~~~

### Example

~~~regex
\b(\w+)\s+\1\b
~~~

Test text: 'the the cat dog dog'

### Result

The results are 'the the' and 'dog dog'. The first capture group first captures a word, then '\1' requires exactly the same word afterwards; 'cat dog' does not match. Use an 'i' flag when comparisons should ignore case.

## 6. Named backreferences

### What they do

A named backreference refers to text already captured by group name, which is easier to read than '\1'. JavaScript commonly uses '\k<name>'; Python commonly uses '(?P=name)'. Check the target engine's supported syntax first.

### Syntax

~~~regex
(?<name>pattern)\k<name>
~~~

### Example

~~~regex
^(?<quote>["']).*?\k<quote>$
~~~

Test text: a double-quoted 'hello', a single-quoted 'hello', and mismatched opening and closing quotes

### Result

The first two items match because the opening and closing quote are the same kind. The third item does not match because its closing quote differs from the captured 'quote'. This is JavaScript-style syntax; in Python, write '^(?P<quote>["']).*?(?P=quote)$'.

## Practice and self-check

1. Use named groups to extract 'level=ERROR latency_ms=2200', then call 'groupdict()' in Python.
2. Compare '^cat|dog$' and '^(?:cat|dog)$' for 'catalog', 'hotdog', 'cat', and 'dog'.
3. Change unneeded parentheses in a date pattern to noncapturing groups and observe whether group numbering is more stable.
4. Write a pattern that finds consecutive repeated ASCII words, and test separate case-sensitive and case-insensitive rules.
5. Why does RE2 not support backreferences? When is “capture first, compare in ordinary code” easier to maintain?

---

Previous: [[regular-expressions/02-boundaries-and-quantifiers|Boundaries and quantifiers]] | Next: [[regular-expressions/04-lookahead-and-lookbehind|Lookahead and lookbehind]].
