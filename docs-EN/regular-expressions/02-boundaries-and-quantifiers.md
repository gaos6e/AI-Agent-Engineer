---
title: "Regular Expressions: Boundaries and Quantifiers"
date: 2026-07-12
tags:
  - regular-expressions
  - tutorial
  - boundaries
  - quantifiers
aliases:
  - Regex Boundaries and Quantifiers
related: "[[regular-expressions/00-index]]"
lang: en
translation_key: "正则表达式/02-边界与数量词.md"
translation_source_hash: e704cee1d405103edcc0e818ca211fbf3b13f8062d6a64d21a56dfb48f1aacc5
translation_route: zh-CN/正则表达式/02-边界与数量词
translation_default_route: zh-CN/正则表达式/02-边界与数量词
---

# Regular Expressions: Boundaries and Quantifiers

Boundaries control where a match starts and ends; quantifiers control how often an item repeats. Combined with character classes, they make complete format rules possible.

## 1. Start and end anchors: '^' and '$'

### What they do

'^' matches the start of an input or line, and '$' matches the end of an input or line. They match positions rather than consuming characters. In multiline mode, they can also constrain each line. In Python, '$' can match before a final newline, and other engines have their own syntax for an absolute end. When validating a Python field, prefer 'fullmatch' rather than guessing completeness from '^...$'.

### Syntax

~~~regex
^pattern$
~~~

### Example

~~~regex
^[0-9]{4}-[0-9]{2}-[0-9]{2}$
~~~

Test text: '2026-07-12', 'date: 2026-07-12', and '2026-07-12 confirmed'

### Result

Only '2026-07-12' has the required shape; the other two have ordinary extra text before or after it. For real Python validation, use 're.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value)' to avoid anchor details such as a trailing newline. The rule still does not prove that the date exists.

## 2. Word boundaries: '\b' and '\B'

### What they do

'\b' matches a position between a word character and a nonword character, or at a string boundary. '\B' matches a position that is not a word boundary. Neither matches an actual character. Because the definition of a word character depends on '\w', test carefully when processing Chinese or other Unicode text.

### Syntax

~~~regex
\bword\b
\Bfragment\B
~~~

### Example

~~~regex
\bcat\b
~~~

Test text: 'cat catalog copycat cat-1'

### Result

The results are the first 'cat' and the 'cat' in 'cat-1'. The 'cat' in 'catalog' and 'copycat' touches other word characters, so it does not have word boundaries on both sides.

## 3. Quantifiers: '*', '+', '?', '{n}', '{n,}', and '{n,m}'

### What they do

Quantifiers apply to the immediately preceding repeatable item: an ordinary character, character class, or group. '*' means zero or more, '+' means one or more, '?' means zero or one, '{n}' means exactly n, '{n,}' means at least n, and '{n,m}' means n through m. Whether assertions can be quantified, and what that means, is not portable across engines, so this course does not treat it as portable syntax.

### Syntax

~~~text
item*       zero or more
item+       one or more
item?       zero or one
item{n}     exactly n
item{n,}    at least n
item{n,m}   n through m
~~~

### Example

~~~regex
colou?r
\d{4}
[A-Za-z]{3,8}
~~~

Test text: 'color colour 2026 a abcd abcdefghi'

### Result

'colou?r' matches 'color' and 'colour', because 'u' is optional. '\d{4}' matches '2026'. '[A-Za-z]{3,8}' matches alphabetic fragments from three through eight characters long; in a search, 'abcdefghi' may yield only its first eight characters. To reject an entire overlong input, combine the rule with '^' and '$'.

## 4. Greedy and lazy matching

### What they do

Quantifiers are greedy by default: while allowing the whole expression to succeed, they consume as much text as possible. Adding a '?' suffix makes a quantifier lazy (or non-greedy): it first tries the fewest characters, then expands as needed. Lazy does not mean “never backtracks”; it can still backtrack to let the overall match succeed.

### Syntax

~~~regex
greedy: .*  .+  \d{2,}
lazy:   .*? .+? \d{2,}?
~~~

### Example

~~~regex
".+"
".+?"
~~~

Test text: '"first" and "second"'

### Result

The greedy pattern '".+"' runs from the first quote through the last quote, returning the entire '"first" and "second"' text. In a global search, the lazy pattern '".+?"' returns two results: '"first"' and '"second"'. If content can contain escaped quotes or span lines, define a more specific rule and flags.

## 5. Quantifier scope

### What they do

A quantifier applies only to the atom immediately before it. To quantify several characters, first group that part of the pattern. This is a common beginner misunderstanding.

### Syntax

~~~regex
ab+      # repeats only b
(ab)+    # repeats the entire ab
~~~

### Example

~~~regex
(ha){2,3}
~~~

Test text: 'ha haha hahaha hahahaha'

### Result

The pattern matches 'haha' and 'hahaha'. In a search, the first six characters of 'hahahaha' can also match as 'hahaha'. If the goal is to validate the whole string, use '^(ha){2,3}$'.

## Practice and self-check

1. In Python, compare 're.search(r"^abc$", value)' and 're.fullmatch(r"abc", value)' for '"abc\n"', then explain the difference.
2. Write a pattern for one through five ASCII decimal digits. Test '0', '001', full-width digits, and '123456'; then decide whether the business rule permits leading zeroes.
3. Explain the scope difference between 'ab+' and '(?:ab)+'.
4. Replace '".*"' for matching double-quoted content with a more specific character class. Why should escaped quotes make you redefine the input contract?
5. Does a lazy quantifier mean that no backtracking occurs?

---

Previous: [[regular-expressions/01-basic-characters-and-character-classes|Basic characters and character classes]] | Next: [[regular-expressions/03-groups-alternation-and-backreferences|Groups, alternation, and backreferences]].
