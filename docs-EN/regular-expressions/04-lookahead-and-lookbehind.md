---
title: "Regular Expressions: Lookahead and Lookbehind"
date: 2026-07-12
tags:
  - regular-expressions
  - tutorial
  - assertions
aliases:
  - Regex Lookahead and Lookbehind
  - Regex Lookaround
related: "[[regular-expressions/00-index]]"
lang: en
translation_key: "正则表达式/04-先行与后行断言.md"
translation_source_hash: 8c76b5866e10295b9a4038b1f5d43c556b7949b1b7666600dea595a6e22048a9
translation_route: zh-CN/正则表达式/04-先行与后行断言
translation_default_route: zh-CN/正则表达式/04-先行与后行断言
---

# Regular Expressions: Lookahead and Lookbehind

Assertions (lookaround) check whether text before or after a match position meets a condition, but the asserted text is not included in the final match. They fit cases such as “extract this value, but require a particular context.”

> [!warning] Compatibility
> Positive and negative lookahead are widely supported; RE2 explicitly does not support lookaround. Python 're' requires the inside of a lookbehind to match a fixed length, while other engines impose their own limits on variable-length patterns and branch lengths. JavaScript support also depends on the deployed runtime version. If compatibility is a problem, use a capture group and read the target portion from the result.

## 1. Positive lookahead

### What it does

Positive lookahead '(?=...)' requires text after the current position to match the pattern in parentheses, but does not include that later text in the result. It is often used to “match a number only when it is followed by a specific unit.”

### Syntax

~~~regex
target(?=following condition)
~~~

### Example

~~~regex
\d+(?=ms)
~~~

Test text: 'latency 120ms, quantity 3 items'

### Result

The result is '120', not '120ms'. 'ms' is only a required following condition, not part of the match; '3' is followed by 'items' and therefore does not match.

## 2. Negative lookahead

### What it does

Negative lookahead '(?!...)' requires text after the current position not to match a specified pattern. It is useful for excluding suffixes, keywords, or formats, but must be placed correctly so it does not exclude only part of the unwanted text.

### Syntax

~~~regex
target(?!disallowed following condition)
~~~

### Example

~~~regex
\b\w+\.(?!exe\b)\w+\b
~~~

Test text: 'readme.txt setup.exe image.png'

### Result

The results are 'readme.txt' and 'image.png'. After the period, the assertion requires that the extension not be the complete word 'exe', so 'setup.exe' is excluded. This rule only checks extension structure; it does not prove a file is safe.

## 3. Positive lookbehind

### What it does

Positive lookbehind '(?<=...)' requires text before the current position to match a pattern, but does not include that earlier text in the result. It is often used to extract only the body of a field with a prefix.

### Syntax

~~~regex
(?<=preceding condition)target
~~~

### Example

~~~regex
(?<=\$)\d+
~~~

Test text: '$120 €80 60'

### Result

The result is '120', because it directly follows a dollar sign. '80' and '60' do not meet the preceding condition. If the runtime does not support lookbehind, first match '\$(\d+)' and then read the first capture group.

## 4. Negative lookbehind

### What it does

Negative lookbehind '(?<!...)' requires text before the current position not to match a specified pattern. It is useful for matching content without a particular prefix. As with positive lookbehind, account for engine limits on lookbehind length and syntax.

### Syntax

~~~regex
(?<!disallowed preceding condition)target
~~~

### Example

~~~regex
(?<!\$)\b\d+\b
~~~

Test text: '$120 80 €60'

### Result

The results are '80' and '60'; '120' in '$120' does not match because the preceding character is '$'. This pattern checks only an adjacent position. If a business rule is “the text segment must contain no currency symbol,” write a more complete rule or parse its structure first.

## 5. Choosing between assertions and capture groups

### What it does

Use an assertion for context you need to check but not return; use a capture group for context you need to match and extract. Either can sometimes solve a task, so choose first for compatibility and how easily later code can read the result.

### Syntax

~~~regex
assertion: (?<=prefix)target
capture:   prefix(target)
~~~

### Example

~~~regex
(?<=ID:)\d+
ID:(\d+)
~~~

Test text: 'ID:42'

### Result

The overall match of the first pattern is '42'. The overall match of the second is 'ID:42', but its first capture group is '42'. The second form is more portable when lookbehind is unsupported.

## Practice and self-check

1. Use lookahead to extract only the number followed by 'ms' from '120ms 80s', then implement it with a capture group.
2. In Python, try compiling '(?<=a+)b', record the exception, and explain what “fixed-length lookbehind” means.
3. Test a rule that excludes an '.exe' suffix with 'readme.txt', 'archive.exe', and 'archive.exe.bak'. Define first which form you intend to exclude.
4. Why does an assertion not consume text but still potentially participate in backtracking?
5. If the target engine is RE2, how would you split extraction that depends on lookaround into an ordinary match plus a program check?

---

Previous: [[regular-expressions/03-groups-alternation-and-backreferences|Groups, alternation, and backreferences]] | Next: [[regular-expressions/05-flags-and-replacement|Flags and replacement]].
