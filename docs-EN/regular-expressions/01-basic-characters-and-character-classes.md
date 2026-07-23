---
title: "Regular Expressions: Basic Characters and Character Classes"
date: 2026-07-12
tags:
  - regular-expressions
  - tutorial
  - character-classes
aliases:
  - Regex Basic Characters and Character Classes
related: "[[regular-expressions/00-index]]"
lang: en
translation_key: "正则表达式/01-基础字符与字符类.md"
translation_source_hash: 0a4b60afd950f7f59e3333e8710779a685500372842daa4800d9af1f9b281e5c
translation_route: zh-CN/正则表达式/01-基础字符与字符类
translation_default_route: zh-CN/正则表达式/01-基础字符与字符类
---

# Regular Expressions: Basic Characters and Character Classes

This lesson begins with how a pattern matches one character. Unless noted otherwise, a 'regex' code block contains the pattern itself, without JavaScript '/.../' literal delimiters. Runnable exercises use Python 're' as the baseline; Unicode and ASCII differences are called out when character classes are involved.

## 1. Ordinary characters

Letters, digits, and most unreserved punctuation are ordinary regex characters. They match themselves and normally distinguish case. Adjacent ordinary characters match that text in order.

~~~regex
cat
~~~

Test text: 'a cat and a catalog'

The pattern matches 'cat' twice: the independent word and the start of 'catalog'. To match only a whole word, combine it with [[regular-expressions/02-boundaries-and-quantifiers#2-word-boundaries-b-and-b|word boundaries]].

## 2. Metacharacters

Metacharacters have special meaning. Common ones include '.', '^', '$', '*', '+', '?', '(', ')', '[', ']', '{', '}', '|', and backslash. They express rules such as any character, boundary, repetition, grouping, and alternation rather than matching literal text.

~~~regex
ca.t
~~~

Test text: 'cat cart cast'

The period matches one arbitrary character by default, normally excluding newlines. Therefore 'ca.t' matches 'cart' and 'cast', but not the three-character string 'cat'. To match a literal period, use '\.'.

## 3. Escaping

A backslash escapes a metacharacter or introduces a special class or boundary such as '\d' or '\b'. When a pattern is inside a programming-language string, it can also pass through a second string-escaping layer.

~~~regex
file\.txt
~~~

Test text: 'file.txt fileXtxt'

'\.' matches the literal period, so only 'file.txt' matches. In Python write 're.compile(r"file\.txt")'; in PowerShell, prefer a single-quoted pattern such as ''file\.txt''; in JavaScript, write '/file\.txt/'. If you use an ordinary program string, inspect the host-language escaping layer too.

## 4. Character set: '[abc]'

A character set, also called a character class, says “match any one of these characters.” '[abc]' matches one character at a time.

~~~regex
gr[ae]y
~~~

Test text: 'gray grey gruy'

'gr[ae]y' matches 'gray' and 'grey', because that position permits 'a' or 'e'; it does not match 'gruy'. Most metacharacters lose their special role inside brackets, but ']', '-', '^', and backslash still need care.

## 5. Character range: '[a-z]'

Inside a set, '-' can express a range. '[a-z]' represents any lower-case ASCII letter from 'a' through 'z'; ranges can combine, as in '[A-Za-z0-9]'.

~~~regex
[A-Z][a-z]+
~~~

Test text: 'Alice BOB alice Zhang'

It matches 'Alice' and 'Zhang': the first character must be upper-case and at least one following character must be lower-case. 'BOB' lacks following lower-case letters, and 'alice' does not begin upper-case. Ranges depend on engine and encoding; do not assume '[a-z]' covers every letter in internationalized text.

## 6. Negated character set: '[^0-9]'

When '^' is the first character in a set, it means “none of these characters.” '[^0-9]' matches one non-ASCII-digit character. Its meaning here differs from the start-of-line anchor because position determines the role.

~~~regex
[^0-9]+
~~~

Test text: 'A12-B_3'

It matches two nondigit runs: 'A' and '-B_'. The trailing '+' merges adjacent nondigits into one match; '1', '2', and '3' are not matched.

## 7. Digit class: '\d'

'\d' is a digit class. In ECMAScript it means '[0-9]'; Python Unicode 'str' patterns and .NET defaults also accept other Unicode decimal digits. For machine protocols, timestamps, and identifiers that allow ASCII digits only, write '[0-9]' explicitly or deliberately use 're.ASCII' in Python.

~~~regex
\d{4}
~~~

Test text: 'No. 2026, batch 73'

It matches '2026', because '{4}' requires four consecutive digits. '73' is only two digits.

## 8. Nondigit class: '\D'

'\D' matches one nondigit character, the complement of '\d'. It can extract or exclude digits, but it does not automatically prove that remaining text is alphabetic.

~~~regex
\D+
~~~

Test text: 'v2.0-beta'

The successive results are 'v', '.', and '-beta'. Digits '2' and '0' are skipped; '+' joins adjacent nondigits into one match.

## 9. Word class: '\w'

'\w' matches a “word character,” where “word” is an engine term rather than natural-language tokenization. Python Unicode 'str' patterns include Unicode alphanumerics and underscore by default; ECMAScript's basic set is close to '[A-Za-z0-9_]'; .NET follows Unicode categories. For machine identifiers, write the permitted set rather than relying on default '\w'.

~~~regex
\w+
~~~

Test text: 'user_name-01' followed by two non-ASCII names

Under basic ECMAScript semantics it matches 'user_name' and '01'. Default Python also matches Unicode word characters. Hyphen and whitespace are not word characters. This is why a pattern cannot be discussed separately from its engine and flags.

## 10. Nonword class: '\W'

'\W' matches one nonword character, the complement of '\w'. It is useful for locating punctuation, separators, and whitespace, but its exact range changes with the definition of '\w'.

~~~regex
\W+
~~~

Test text: 'name@example.com!'

The results are '@', '.', and '!'. Letters belong to '\w', so this pattern does not match them.

## 11. Whitespace class: '\s'

'\s' matches one whitespace character such as a space, tab, or newline; whether it includes more Unicode whitespace depends on the engine. It is useful for irregular spaces and line breaks.

~~~regex
\s+
~~~

Test text: 'name   age<TAB>city'

It returns two whitespace pieces: three consecutive spaces and one tab. '+' merges contiguous whitespace rather than returning one character at a time.

## 12. Nonwhitespace class: '\S'

'\S' matches one nonwhitespace character, the complement of '\s'. It extracts whitespace-separated nonblank chunks, not natural-language words.

~~~regex
\S+
~~~

Test text: '  one<TAB>two  three '

The results are 'one', 'two', and 'three'. Leading, trailing, and intervening spaces or tabs are not matched.

## 13. Period: '.'

The period normally matches one arbitrary character, but most engines do not let it match a newline by default. In dotAll mode it normally can match newlines as well. Use '\.' for a literal period.

~~~regex
a.c
~~~

Test text: 'abc a-c ac'

It matches 'abc' and 'a-c': the period matches their middle character. 'ac' has no middle character and does not match. Do not use '.*' as a substitute for every structured rule; it easily produces overmatching and poor performance.

## Practice and self-check

1. Write a character class that allows only ASCII hexadecimal characters, then test '0fA9', '0x10', and the empty string.
2. In Python, match full-width digits with 'r"\d+"' and 'r"[0-9]+"' and explain the difference.
3. Write a pattern that matches the literal text 'a+b.c'; identify the characters that need escaping.
4. Is '[^0-9]' equivalent to “a letter”? Why not?
5. Why can '.' in default mode not reliably mean “any byte” or “any line of JSON”?

---

Previous: [[regular-expressions/00b-task-modeling-and-engine-differences|Task modeling and engine differences]] | Next: [[regular-expressions/02-boundaries-and-quantifiers|Boundaries and quantifiers]].
