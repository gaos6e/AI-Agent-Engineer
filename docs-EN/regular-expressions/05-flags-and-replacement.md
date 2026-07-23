---
title: "Regular Expressions: Flags and Replacement"
date: 2026-07-12
tags:
  - regular-expressions
  - tutorial
  - flags
  - replacement
aliases:
  - Regex Flags and Replacement
related: "[[regular-expressions/00-index]]"
lang: en
translation_key: "正则表达式/05-标志与替换.md"
translation_source_hash: 9a64ce960b11f89cce90e2e2b90277cc8a1521197745b9d8d3ec80aeec15e4ea
translation_route: zh-CN/正则表达式/05-标志与替换
translation_default_route: zh-CN/正则表达式/05-标志与替换
---

# Regular Expressions: Flags and Replacement

Flags change matcher behavior, for example by ignoring case or working line by line. Replacement rewrites matched results as new text. This lesson uses JavaScript '/pattern/flags' literals to show the common letters directly, then maps them to Python and PowerShell APIs in the next lesson. Do not paste JavaScript literal syntax directly into Python.

> [!note] Flags are not fully universal
> In JavaScript, 'g' means “continue finding” results. Python more often gets all results with APIs such as 'findall', 'finditer', or 'sub'. Many engines have 'i', 'm', and 's', but their names, inline forms, and Unicode details can differ. PowerShell '-match' is case-insensitive by default; use '-cmatch' when the contract distinguishes case.

## 1. Global matching: 'g'

### What it does

In JavaScript, 'g' makes matching or replacement APIs continue to later results instead of processing only the first match. Whether an API truly returns every result also depends on the method: 'matchAll' and 'replace' behave differently from 'test'.

### Syntax

~~~javascript
/pattern/g
~~~

### Example

~~~javascript
"id=12; id=34".match(/\d+/g)
~~~

### Result

The result is an array containing '12' and '34'. Without 'g', 'match(/\d+/)' normally returns only the first number, '12', along with additional match information. In Python, 're.findall(r"\d+", text)' returns the same two results.

## 2. Ignore case: 'i'

### What it does

'i' makes letter matching case-insensitive. It is mainly useful for scripts such as English that distinguish letter case. Unicode case folding is more complex than ASCII case folding, so test against the target engine for multilingual data.

### Syntax

~~~javascript
/pattern/i
~~~

### Example

~~~javascript
"Error ERROR error".match(/error/gi)
~~~

### Result

The result is an array containing 'Error', 'ERROR', and 'error'. 'g' finds all results and 'i' ignores letter case. Without 'i', the pattern 'error' matches only the last lowercase instance.

## 3. Multiline mode: 'm'

### What it does

'm' changes the meaning of '^' and '$': besides matching the start and end of the entire input, they can match the start and end of each line. Multiline mode does not make '.' cross a newline automatically; dotAll mode controls that.

### Syntax

~~~javascript
/^pattern$/m
~~~

### Example

~~~javascript
"ok\nERROR: disk full\nok".match(/^ERROR:.*$/m)
~~~

### Result

The result is 'ERROR: disk full'. Without 'm', '^' and '$' constrain the whole three-line string, so the middle error line does not match.

## 4. Single-line (dotAll) mode: 's'

### What it does

's' is often called single-line mode or dotAll mode: it makes '.' match newlines too. “Single-line” is a misleading name. It does not change '^' or '$'; use 'm' for those.

### Syntax

~~~javascript
/start.*end/s
~~~

### Example

~~~javascript
"<p>first line\nsecond line</p>".match(/<p>.*<\/p>/s)
~~~

### Result

The result is the entire '<p>first line\nsecond line</p>' fragment. Without 's', '.' cannot cross the newline and the pattern fails. For text with nested structure such as HTML or JSON, regex can only handle controlled small fragments; it is not a replacement for a real parser.

## 5. Regex replacement

### What it does

A replacement first finds targets with a regex, then produces new content with specified text or a function. It is often used to normalize whitespace, redact data, or change formats in bulk. Inspect matches first, and run replacements on copies or test data when possible.

### Syntax

~~~javascript
text.replace(/pattern/g, "replacement text")
~~~

### Example

~~~javascript
"name   age\tcity".replace(/\s+/g, " ")
~~~

### Result

The result is 'name age city'. '\s+' finds each consecutive whitespace run, and 'g' ensures that all runs become one ordinary space. Without 'g', normally only the first run is replaced.

## 6. Capture groups in replacements

### What they do

A replacement can reference capture groups to reorder, retain, or format matched subcontent. JavaScript replacement strings commonly use '$1' and '$2'; Python commonly uses '\g<1>' and '\g<2>'. Do not mix the two syntaxes.

### Syntax

~~~javascript
text.replace(/(group 1)(group 2)/g, "$2$1")
~~~

### Example

~~~javascript
"date: 2026-07-12".replace(/(\d{4})-(\d{2})-(\d{2})/g, "$3/$2/$1")
~~~

### Result

The result is 'date: 12/07/2026'. The regex first captures year, month, and day as groups 1, 2, and 3, then writes them in day/month/year order. JavaScript can use '$<name>' for named captures, which is normally clearer.

## 7. Be aware of the limits of common patterns

### What they do

Common patterns can do initial structural filtering for integers, simple email addresses, or version numbers. But “looks like” does not mean “valid for the business”: email deliverability, date existence, and telephone ownership all need additional validation and should not depend on regex alone.

### Syntax

~~~regex
integer:              ^-?\d+$
simple version:       ^\d+\.\d+\.\d+$
simple email shape:   ^[^\s@]+@[^\s@]+\.[^\s@]+$
~~~

### Example

~~~regex
^\d+\.\d+\.\d+$
~~~

Test text: '1.2.3', 'v1.2.3', '1.2', and '1.2.3.4'

### Result

Only '1.2.3' matches because it has exactly three numeric segments separated by periods. It does not validate version ranges or semantics: for example, '999.999.999' still matches structurally.

## Practice and self-check

1. What do 'm' and 's' change respectively? Why does “multiline” not mean “dot crosses lines”?
2. In Python, use 're.MULTILINE' to find every line that starts with 'ERROR:', then use 'finditer' to output positions within the line.
3. Write “replace consecutive whitespace with one space” in JavaScript, Python, and PowerShell, noting their different replacement-reference syntax.
4. Use a function replacement to add one to every number. Why should complex replacement logic not be forced into a replacement string?
5. Add a maximum segment length to the simple version pattern, then explain the boundary between structural validation and version-semantic validation.

---

Previous: [[regular-expressions/04-lookahead-and-lookbehind|Lookahead and lookbehind]] | Next: [[regular-expressions/05a-python-re-and-powershell-practical-apis|Practical Python re and PowerShell APIs]].
