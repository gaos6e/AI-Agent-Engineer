---
title: "Regular Expression Reference Notes"
lang: en
translation_key: "正则表达式/00A-笔记.md"
translation_source_hash: ca91da541e70cfd87106401e09c67efa6083cefd55ef5ae6d7c074ffa6b373cd
translation_route: zh-CN/正则表达式/00A-笔记
translation_default_route: zh-CN/正则表达式/00A-笔记
---

## Regex metacharacters

| Metacharacter | Meaning | Example |
| --- | --- | --- |
| '.' | Matches any single character except a newline | 'a.c' can match 'abc' and 'a1c' |
| '^' | Matches the beginning of a string or line | '^Hello' |
| '$' | Matches the end of a string or line | 'end$' |
| '*' | The preceding item occurs zero or more times | 'ab*' can match 'a', 'ab', and 'abb' |
| '+' | The preceding item occurs one or more times | 'ab+' can match 'ab' and 'abb' |
| '?' | The preceding item occurs zero or one time; it can also make a quantifier lazy | 'colou?r' matches 'color' and 'colour' |
| '{n,m}' | Repeats the preceding item a specified number of times | 'a{2,4}' matches two to four 'a' characters |
| '[]' | A character set; matches one character in the set | '[abc]' matches 'a', 'b', or 'c' |
| '[^]' | A negated character set | '[^0-9]' matches a nondigit character |
| '()' | Groups or captures | '(ab)+' matches 'ab' and 'abab' |
| <code>&#92;&#124;</code> | Alternation, meaning “or” | <code>cat&#92;&#124;dog</code> matches 'cat' or 'dog' |
| <code>&#92;</code> | Escape character, or the start of a special sequence | <code>&#92;.</code> matches a literal period |

## Escapes and special sequences

### Escape metacharacters

Put a backslash before a metacharacter to match the symbol itself.

| Form | Literal character matched | Example |
| --- | --- | --- |
| <code>&#92;.</code> | '.' | '3\.14' matches '3.14' |
| <code>&#92;^</code> | '^' | '\^start' matches '^start' |
| <code>&#92;$</code> | '$' | '\$100' matches '$100' |
| <code>&#92;*</code> | '*' | 'a\*b' matches 'a*b' |
| <code>&#92;+</code> | '+' | 'A\+' matches 'A+' |
| <code>&#92;?</code> | '?' | 'why\?' matches 'why?' |
| <code>&#92;{</code> | '{' | '\{name}' matches the opening brace in '{name}' |
| <code>&#92;}</code> | '}' | 'name\}' matches 'name}' |
| <code>&#92;[</code> | '[' | '\[abc]' matches the opening bracket in '[abc]' |
| <code>&#92;]</code> | ']' | 'abc\]' matches 'abc]' |
| <code>&#92;(</code> | '(' | '\(text' matches '(text' |
| <code>&#92;)</code> | ')' | 'text\)' matches 'text)' |
| <code>&#92;&#124;</code> | <code>&#124;</code> | <code>cat&#92;&#124;dog</code> matches the literal text <code>cat&#124;dog</code> |
| <code>&#92;&#92;</code> | <code>&#92;</code> | 'C:\\Temp' matches 'C:\Temp' |

### Common special sequences

A backslash followed by a letter or number usually introduces a character class, boundary, control character, or backreference.

| Form | Meaning | Example |
| --- | --- | --- |
| '\d' | A digit; whether this is ASCII-only depends on engine and flags | '\d+' matches a run of digits |
| '\D' | A nondigit character | '\D+' matches a run of nondigits |
| '\w' | A word character; the exact Unicode range depends on engine and flags | '\w+' matches a run of word characters |
| '\W' | A nonword character | '\W+' matches punctuation, whitespace, and other nonword characters |
| '\s' | Whitespace such as spaces, tabs, and newlines | 'a\s+b' matches 'a' and 'b' separated by whitespace |
| '\S' | A nonwhitespace character | '\S+' matches a run of nonwhitespace text |
| '\b' | A word boundary; its meaning can differ inside a character set '[]' | '\bcat\b' matches the whole word 'cat' |
| '\B' | A nonword boundary | '\Bcat\B' matches 'cat' inside a word |
| '\n' | Newline | 'a\nb' matches 'a' and 'b' on separate lines |
| '\r' | Carriage return | '\r\n' matches the common Windows newline sequence |
| '\t' | Tab | 'a\tb' matches 'a' and 'b' separated by a tab |
| '\f' | Form feed | '\f' matches a form-feed character |
| '\v' | Vertical tab; support varies by engine | '\v' matches a vertical-tab character |
| '\xHH' | A character represented by a two-digit hexadecimal value | '\x41' matches 'A' |
| '\uHHHH' | A Unicode code point written with four hexadecimal digits; syntax varies by engine | '\u4E2D' matches the character U+4E2D |
| '\1', '\2' | References a previously captured group by number | '(ab)\1' matches 'abab' |

> [!note] Engine differences
> Special sequences such as '\A', '\Z', '\z', named backreferences, and Unicode properties do not use the same syntax in every regex engine. Check the documentation for the target engine before using them.
