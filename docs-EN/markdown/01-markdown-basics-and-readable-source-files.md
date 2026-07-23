---
title: "Markdown Basics and Readable Source Files"
tags:
  - ai-agent-engineer
  - markdown
  - engineering-foundations
aliases:
  - Markdown basic syntax
  - Readable source files
source_checked: 2026-07-14
lang: en
translation_key: "Markdown/01-Markdown基础语法与可读源文件.md"
translation_source_hash: 54c94a2fabe20546b57a2445bb45c8244bd55e64f0b82afe8ad7cb5d22444937
translation_route: zh-CN/Markdown/01-Markdown基础语法与可读源文件
translation_default_route: zh-CN/Markdown/01-Markdown基础语法与可读源文件
---

# Markdown Basics and Readable Source Files

## Lesson goal

After this lesson, you should be able to write a technical note from scratch that remains understandable without a special theme, and explain why the same `.md` file can behave slightly differently in different tools. This lesson covers only the high-frequency core; use [[markdown/markdown-tutorial|The Complete Markdown Tutorial]] as a reference manual when you need to look up a symbol.

## Build the right mental model first

This vault requires `.md` files to be **UTF-8 plain text**. CommonMark defines parsing rules by characters; it does not prescribe the file's byte encoding. A project must still state its encoding when documents move across tools. Characters such as `#`, `-`, and backticks are parser markers. Obsidian, GitHub, or a documentation site then renders the parsed result as headings, lists, and code blocks.

~~~mermaid
flowchart LR
    Source["Source text .md"] --> Parser["Parser: recognizes block and inline markers"]
    Parser --> Model["Document structure"]
    Model --> Renderer["Renderer and theme"]
    Renderer --> View["Reading View / HTML"]
~~~

Therefore, evaluate three things separately:

1. **Is the source text clear?** Can someone still understand its hierarchy, commands, and evidence without rendering it?
2. **Does the syntax belong to the active dialect?** Is it CommonMark core, a GFM extension, or an Obsidian-specific capability?
3. **Does the host support and enable it?** Themes, plugins, host versions, and security settings can all affect the final display.

Markdown is not an execution environment. A code fence only says “this is code”; it does not run a command automatically or isolate hostile content.

## Block structure and inline structure

Parsers normally recognize blocks first and then process inline content within each block. That explains many seemingly surprising results.

| Layer | Common elements | Key boundaries |
| --- | --- | --- |
| Block structure | headings, paragraphs, lists, quotations, code blocks, thematic breaks | line-start markers, blank lines, indentation, fences |
| Inline structure | emphasis, links, images, inline code | paired delimiters, escaping, target addresses |

For example, `- ` at the start of a line first establishes a list item; `**important**` inside it is then recognized as bold. If a code block below a list has incorrect indentation, the problem is block structure, not the Python code itself.

## Everyday syntax you must know

### Headings and paragraphs

- `#` through `######` represent heading levels one through six; leave a space after `#`.
- An independent note normally has one level-one heading, with body content beginning at level two.
- Leave a blank line between paragraphs. Do not use long runs of spaces or blank lines to “push” content apart.
- Headings express information hierarchy, not merely font size; do not jump directly from level two to level four.

### Lists, quotations, and tasks

~~~markdown
- Items with no required order
  - Child items use consistent indentation

1. Steps with a required order
2. Each step expresses only one action

> A quotation, or text whose source boundary must be retained

- [ ] To check
- [x] Complete
~~~

Task lists are a common extension and should not replace a status explanation. `- [x] Tested` still needs to say what was tested and where the evidence is.

### Emphasis, inline code, and code fences

- `**bold**` is for a small amount of emphasis; `*italic*` is commonly for lighter emphasis or terminology.
- ``config.json`` is appropriate for a filename, command, field, or short code fragment.
- Use fences for multi-line commands, programs, and output, and add a language tag such as `powershell`, `python`, `json`, or `text`.

Commands and output must be separate:

~~~powershell
python --version
~~~

~~~text
Python 3.x.y
~~~

Here, `3.x.y` is a placeholder example, not a version that this course claims was measured. Technical documentation must clearly distinguish a command, expected output, and an actual record.

### Links, images, and tables

- External web page: `[CommonMark](https://spec.commonmark.org/)`.
- A note inside the vault: use a path-explicit Obsidian wikilink; the next lesson explains this in detail.
- External image: `![alternative text](https://example.com/image.png)`. Alternative text should describe the information, not simply say “image.”
- Tables work well for column-by-column comparison. Steps, long explanations, and nested content work better as lists or sections.

Write `\|` when a table cell must display `|`. Do not pack multi-step procedures into a table, because narrow screens and plain-text diffs become difficult to read.

## Whitespace, line breaks, and escaping

This is where beginners most often make mistakes.

| Goal | Recommended form | Note |
| --- | --- | --- |
| New paragraph | Leave one blank line in between | Most stable and readable |
| Forced line break in one paragraph | Two spaces or a backslash at line end | Depends on parser rules; use sparingly |
| Display a special character | Prefix a backslash, such as `\#` | A code span normally needs no escaping |
| Nested code fences | Use more backticks for the outer fence | The outer fence must be longer than the inner one |

Obsidian line-break display is also affected by the **Strict line breaks** setting. In cross-platform documents, do not rely on “pressing Enter once looks like a new line in the editor.” A blank line between paragraphs expresses structure more reliably.

The next example uses four backticks to display a Markdown document that contains a three-backtick code block:

~~~~markdown
# Local tool run record

## Prerequisites

- Windows 11
- PowerShell 7
- Python 3

## Command

```powershell
python --version
```

## Result boundary

The command above must be run by the reader; this document does not record actual output.
~~~~

## Minimal readability check

After writing a note, inspect its source before switching to Reading View:

1. Do the filename and level-one heading explain the topic?
2. Can you restate the document structure from headings alone?
3. Are commands, output, placeholders, and explanations separate?
4. Do lists express peer items, and do numbers really mean order?
5. Does the information still hold after theme styling is removed?
6. Is there any real credential, personal data, or unprovable “verified” claim?

## Hands-on practice: build a rendering experiment

Create a temporary note named `Markdown-rendering-experiment.md` and add, in order:

- two adjacent text lines and two paragraphs separated by a blank line;
- a list immediately below a level-two heading, plus a code block below a blank line after the list;
- a table cell containing `|`;
- a three-backtick code block and a display block that wraps it with four backticks;
- one external link and one full-path wikilink to this index.

For each experiment, record three columns: source text, Reading View observation, and your inferred reason. Do not write an observation as a fact guaranteed by every renderer.

## Common misconceptions

- **“It looks normal in the editor, so the file is fine.”** Editor highlighting is not the target renderer.
- **“More spaces make alignment easier.”** Proportional fonts and different window widths break manual alignment.
- **“A language tag executes code.”** It normally only selects syntax highlighting.
- **“There is only one Markdown standard.”** In practice there are CommonMark, GFM, and host extensions.
- **“A longer README is more complete.”** Executable order, boundaries, and evidence matter more than length.

## Self-check and mastery check

1. What do source text, parser, and renderer each do?
2. Why is a code block in a list first a block-structure problem?
3. How do a soft line break, a new paragraph, and a hard line break differ?
4. Why should commands and output use different fences?
5. How can a document display another three-backtick code block?

- [ ] I can independently write headings, paragraphs, lists, quotations, links, tables, and code blocks.
- [ ] I can identify a document's structure from its source alone.
- [ ] I can explain at least three sources of rendering differences.
- [ ] I can clearly label expected output and actual verification.

Next: [[markdown/02-commonmark-gfm-and-obsidian-syntax-boundaries|CommonMark, GFM, and Obsidian syntax boundaries]].

## References

Checked: **2026-07-14**.

- [CommonMark Specification 0.31.2](https://spec.commonmark.org/0.31.2/)
- [GitHub Flavored Markdown Specification 0.29-gfm](https://github.github.com/gfm/)
- [Obsidian: Basic formatting syntax](https://obsidian.md/help/syntax)
