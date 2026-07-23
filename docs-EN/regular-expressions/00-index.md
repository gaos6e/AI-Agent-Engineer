---
title: "Regular Expressions"
date: 2026-07-12
tags:
  - ai-agent-engineer
  - engineering-foundations
  - regular-expressions
  - text-processing
aliases:
  - Regex course index
  - Regular Expression course index
  - Regular Expressions learning path
source_checked: 2026-07-14
source_baseline:
  - Python 3.14.6 re documentation
  - PowerShell 7.6 and .NET regular-expression documentation
ai_learning_stage: 1. Engineering foundations
ai_learning_order: 9
ai_learning_schema: 2
ai_learning_id: regular-expressions
ai_learning_domain: foundations
ai_learning_catalog_order: 900
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 75
ai_learning_track_agent_app_kind: optional
ai_learning_track_rag_order: 75
ai_learning_track_rag_kind: recommended
ai_learning_track_agent_platform_order: 75
ai_learning_track_agent_platform_kind: optional
ai_learning_track_multimodal_realtime_order: 75
ai_learning_track_multimodal_realtime_kind: optional
lang: en
translation_key: "正则表达式/00-目录.md"
translation_source_hash: 993caedc2c2d02cffd37c72b41476a7da2ae83fb8c634fecece6338266cc488f
translation_route: zh-CN/正则表达式/00-目录
translation_default_route: zh-CN/正则表达式/00-目录
---

# Regular Expressions

## About this knowledge base

Regular expressions—often shortened to Regex or RegExp—are a small language for describing text patterns. They work well for searching, extraction, controlled format validation, batch replacement, and coarse log parsing. They do not understand business meaning and are not suitable for fully parsing JSON, HTML, programming languages, or natural language. This course begins with task modeling, uses Python 're' as the runnable baseline, and notes differences in the .NET engine used by Windows 11 / PowerShell 7.

> [!warning] Confirm the engine first
> “Regex syntax” is not one standard. Python 're', PowerShell/.NET, ECMAScript, GNU grep, and RE2 differ in character classes, group names, lookbehind, replacement references, and backtracking. Plain 'regex' code blocks in this course show patterns only. Runnable examples prefer local Python 3.11+ and PowerShell 7, and label engine-specific features where they are used.

## Place in the overall path

This course belongs to engineering foundations. Agent engineering commonly uses regex for log filtering, coarse structural checks, identifier extraction, and redaction, but no single pattern should be responsible for complete JSON parsing, natural-language understanding, or validation of business truth.

## Learning objectives

After completing the course, you can:

- construct patterns step by step from ordinary characters, character classes, boundaries, and quantifiers;
- distinguish literal search, globbing, regex, and specialized parsers before choosing a tool;
- choose search, full match, extraction, and replacement correctly;
- distinguish pattern escaping from programming-language string escaping;
- call common matching APIs in Python 're' and PowerShell/.NET;
- identify engine differences, catastrophic backtracking, and untrusted-input risk;
- write positive, negative, boundary, and performance tests for a pattern;
- complete a log-parsing project with Python 're'.

## Prerequisites

You only need to be able to read strings and run one PowerShell command. The project uses only the Python 3 standard library and needs no third-party package, network, or API key. Basic Python strings, functions, and file reading are recommended first.

## Recommended order

1. [[regular-expressions/00b-task-modeling-and-engine-differences|Task modeling and engine differences]]: decide whether regex is needed and fix the target engine.
2. [[regular-expressions/01-basic-characters-and-character-classes|Basic characters and character classes]]: start with one character and distinguish literals, metacharacters, and Unicode character classes.
3. [[regular-expressions/02-boundaries-and-quantifiers|Boundaries and quantifiers]]: constrain position, length, and repetition.
4. [[regular-expressions/03-groups-alternation-and-backreferences|Groups, alternation, and backreferences]]: combine rules, extract fields, and reuse captured content.
5. [[regular-expressions/04-lookahead-and-lookbehind|Lookahead and lookbehind]]: check context without including it in the result.
6. [[regular-expressions/05-flags-and-replacement|Flags and replacement]]: understand cross-engine flags and replacement references.
7. [[regular-expressions/05a-python-re-and-powershell-practical-apis|Practical Python re and PowerShell APIs]]: run search, full match, iterative extraction, and replacement code.
8. [[regular-expressions/06-performance-and-debugging|Performance and debugging]]: identify backtracking, ReDoS, input limits, and engine trade-offs.
9. [[regular-expressions/07-python-log-parser-project-and-self-test|Python log-parser project and self-test]]: complete extraction, error location, and regression tests under a clear input contract.

## Example conventions

- A 'regex' code block contains the regex pattern itself, such as '\d+'.
- Python patterns are usually raw strings, for example 're.compile(r"\d+")'; PowerShell patterns are preferably single-quoted, for example ''\d+''.
- A JavaScript regex literal is '/\d+/g'; the trailing 'g' is a flag. Python has no 'g' flag and instead uses 'finditer', 'findall', or 'sub' to handle all results.
- A pattern inside an ordinary program string is also parsed by the host language. Always inspect the string value and regex meaning as separate layers.
- “Match result” lists only matched text. Whether positions, capture groups, or every result are returned also depends on the API used.

## Study advice

- Validate rules on short strings before applying them to real data.
- Add one condition at a time and record whether it changes the match result.
- For business data such as usernames, email addresses, or dates, state permitted and forbidden formats first. Regex supplies structure; it does not automatically guarantee real-world validity.
- When a rule becomes complex, prefer splitting it, adding comments, or writing unit tests over relying on an unmaintainable “one-line universal regex.”

## Hands-on and project entry points

- API warm-up: [[regular-expressions/05a-python-re-and-powershell-practical-apis|Practical Python re and PowerShell APIs]].
- Capstone: [[regular-expressions/07-python-log-parser-project-and-self-test|Python log-parser project and self-test]]. The script reads only fictional logs and uses 're.VERBOSE', named groups, and 'fullmatch'. Independent 'unittest' cases cover positive, negative, Unicode-digit, length-boundary, and long-input cases.

## Mastery criteria

- [ ] I can explain the scope of character classes, boundaries, quantifiers, groups, assertions, and flags.
- [ ] I can distinguish 'search', 'match', 'fullmatch', and global finding.
- [ ] I use raw strings first for Python patterns containing backslashes.
- [ ] I apply 're.escape' to user-supplied literal text rather than concatenating it directly into a pattern.
- [ ] Every business pattern has positive, negative, boundary, and oversized-input tests.
- [ ] I review complex nested quantifiers for performance and use a parser or staged logic when necessary.
- [ ] I can run the log project and locate the precise failing line rather than silently skipping dirty data.

## Relationship to other knowledge bases

| Next knowledge base | Connection |
| --- | --- |
| Python fundamentals | Uses 're' APIs, exceptions, tests, and file reading. |
| [[data-cleaning/00-index\|Data Cleaning]] | Regex handles local patterns; it does not replace complete parsing or quality rules. |
| Runtime monitoring | Fix the log contract and control cardinality before extracting fields from logs. |
| [[ai-safety/00-index\|AI Safety]] | Covers regex denial of service (ReDoS), faulty redaction, and untrusted patterns. |

## Primary references

Checked: **2026-07-14**. This revision uses Python 3.14.6 documentation and PowerShell 7.6 / .NET documentation as the current source baseline; the local hands-on environment is Python 3.11.9 and PowerShell 7.6.1. Engine syntax evolves, so recheck the deployment environment before use.

- [ECMAScript Language Specification: RegExp](https://tc39.es/ecma262/multipage/text-processing.html#sec-regexp-regular-expression-objects)
- [Python standard library: re](https://docs.python.org/3/library/re.html)
- [Python Regular Expression HOWTO](https://docs.python.org/3/howto/regex.html)
- [Microsoft Learn: PowerShell Regular Expressions](https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_regular_expressions)
- [.NET regular expressions](https://learn.microsoft.com/dotnet/standard/base-types/regular-expressions)
- [GNU grep: Regular Expressions](https://www.gnu.org/software/grep/manual/html_node/Regular-Expressions.html)
- [Google RE2](https://github.com/google/re2)
- [OWASP: Regular expression Denial of Service](https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS)
