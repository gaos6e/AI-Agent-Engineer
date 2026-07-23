---
title: "The Complete Markdown Tutorial"
date: 2026-07-12
tags:
  - markdown
  - tutorial
  - writing-tools
aliases:
  - Markdown beginner tutorial
  - Markdown syntax tutorial
lang: en
translation_key: "Markdown/Markdown 教程.md"
translation_source_hash: 49848d5f19605edc722aba97dc6693e675d9973d94ea6bdb2c1c21ad019203d9
translation_route: zh-CN/Markdown/Markdown-教程
translation_default_route: zh-CN/Markdown/Markdown-教程
---

# The Complete Markdown Tutorial

The point of learning Markdown is not memorizing every symbol. It is mastering three principles: simple source, readable plain text, and clear rendered output. Examples in this tutorial primarily follow CommonMark, with common forms from GitHub Flavored Markdown (GFM) and Obsidian added where useful.

> [!tip] How to use this tutorial
> In Obsidian, open Editor View and Reading View together when possible. Copy a “Markdown source” example first, then switch to Reading View to observe the rendering. Markdown parsers on different platforms can have small differences.

## Contents

- [[#1. What Markdown is and common uses]]
- [[#2. Headings]]
- [[#3. Ordinary paragraphs and line breaks]]
- [[#4. Bold, italic, and strikethrough]]
- [[#5. Ordered and unordered lists]]
- [[#6. Task lists]]
- [[#7. Links]]
- [[#8. Images]]
- [[#9. Blockquotes]]
- [[#10. Inline code and code blocks]]
- [[#11. Tables]]
- [[#12. Thematic breaks]]
- [[#13. Escaping characters]]
- [[#14. Mixing HTML and Markdown]]
- [[#15. Common GitHub Flavored Markdown syntax]]
- [[#16. Common Markdown extensions in Obsidian]]
- [[#17. Integrated practice]]

---

## 1. What Markdown is and common uses

### What it does

Markdown is a lightweight markup language. It uses ordinary characters such as `#`, `*`, `-`, and backticks to express document structure, then Obsidian, GitHub, blogging systems, and other tools render it as formatted content.

Common uses include:

- writing README files, project documentation, and API documentation;
- recording knowledge, journals, and research notes in Obsidian;
- writing blogs, static websites, and online tutorials;
- recording meeting notes, task lists, and experiment logs;
- creating plain-text documents that Git can manage and compare.

Markdown's strengths are readable source, lightweight files, cross-platform use, and suitability for version control. Its limitation is that extensions are not supported identically by every renderer; complex layout normally still needs HTML, CSS, or a dedicated layout tool.

### Markdown source

~~~markdown
# Project overview

This is a data-analysis project written in **Python**.

## Quick start

1. Install dependencies.
2. Run the program.
3. Review the results.
~~~

### Rendered-result explanation

A renderer recognizes text beginning with `#` as headings, blank-line-separated text as paragraphs, `**Python**` as bold, and number-prefixed content as an ordered list. Even before rendering, the source remains easy to read.

---

## 2. Headings

### What they do

Using one through six `#` characters at the start of a line creates heading levels one through six. Leave a space after `#`. Heading levels express document structure, not only font size; one note normally uses a single level-one heading.

### Markdown source

~~~markdown
# Level-one heading
## Level-two heading
### Level-three heading
#### Level-four heading
##### Level-five heading
###### Level-six heading
~~~

### Rendered-result explanation

The six lines render as headings from level one through level six. A level-one heading has the highest hierarchy and is usually largest; later headings are children of earlier headings. Obsidian also builds an outline from them and allows links to a heading.

---

## 3. Ordinary paragraphs and line breaks

### What they do

Continuous text forms an ordinary paragraph. Leave one blank line between paragraphs. Pressing Enter once in source normally does not make a new paragraph. To force a line break inside one paragraph, write two spaces at line end or, in CommonMark-supporting environments, use a trailing backslash `\`.

### Markdown source

~~~markdown
This is the first paragraph. Adjacent source lines
are normally combined into one paragraph.

This is the second paragraph because a blank line separates it from the first.

This line ends with a backslash\
and continues on the next line.
~~~

### Rendered-result explanation

Blank lines create new paragraphs; two trailing spaces or a trailing backslash create a break inside a paragraph. When unsure whether a platform preserves trailing spaces, prefer blank lines for paragraph boundaries.

---

## 4. Bold, italic, and strikethrough

### What they do

Bold emphasizes important content, italic provides lighter emphasis or identifies a term, and strikethrough marks content as retired, replaced, or no longer applicable. Common forms are `**bold**`, `*italic*`, and `~~strikethrough~~`.

### Markdown source

~~~markdown
This is **bold text**.

This is *italic text*.

This is ***bold italic text***.

This is ~~struck-through text~~.
~~~

### Rendered-result explanation

The paired asterisks or tildes do not display; they control the style of their contents. Strikethrough is not an earliest-core Markdown feature but is widely supported by GFM, Obsidian, and other common hosts.

---

## 5. Ordered and unordered lists

### What they do

Unordered lists suit items with no required order and commonly begin with `-`, `*`, or `+`. Ordered lists suit steps or priorities and begin with “number plus period.” Leave a space after the marker. Indentation creates sublists; use one indentation style consistently in a document.

### Markdown source

~~~markdown
- Fruit
  - Apple
  - Banana
- Vegetables

1. Open the editor
2. Create a Markdown file
3. Enter content
   1. Add a heading
   2. Add a paragraph
4. Save the file
~~~

### Rendered-result explanation

An unordered list shows bullet points, an ordered list shows numbers, and indented items form nested levels. Most renderers correct displayed ordered-list numbers automatically, but source should still use actual order for readability and maintenance.

---

## 6. Task lists

### What they do

A task list adds `[ ]` or `[x]` after an unordered-list marker. `[ ]` means unfinished and `[x]` means complete. It suits to-do lists, learning plans, checklists, and project-progress records, and is a common GFM extension.

### Markdown source

~~~markdown
- [x] Understand what Markdown is
- [x] Learn basic syntax
- [ ] Finish the integrated practice
- [ ] Create a personal quick reference
~~~

### Rendered-result explanation

Each item displays as a checkbox. In Obsidian, a checkbox can normally be clicked to change state; whether other platforms allow interaction depends on the implementation.

---

## 7. Links

### What they do

A standard Markdown link has display text in square brackets and a target in parentheses: `[display text](URL)`. It can include an optional title: `[display text](URL "title")`. A target can be a web address, a relative file path, or a heading anchor in the same page.

### Markdown source

~~~markdown
[Visit an example website](https://example.com)

[Link with a title](https://example.com "This title may appear on hover")

[Jump to this tutorial's tables section](#11-tables)

<https://example.com>
~~~

### Rendered-result explanation

The text in square brackets becomes clickable. A full URL enclosed in angle brackets becomes a clickable autolink. Exact heading-anchor rules differ by platform; when linking a note inside Obsidian, prefer a wikilink such as `[[note name]]`.

---

## 8. Images

### What they do

Image syntax is an ordinary link prefixed with an exclamation mark: `![alternative text](image address)`. Alternative text appears if an image cannot load and helps screen readers understand its information. The address can be a web URL or relative path and may have an optional title.

### Markdown source

~~~markdown
![Markdown logo](https://upload.wikimedia.org/wikipedia/commons/4/48/Markdown-mark.svg "Markdown logo")

![Experiment flow diagram](attachments/experiment-flow.png)
~~~

### Rendered-result explanation

The first line tries to load and display a remote image. The second represents a local image in an `attachments` directory beside the current note. If the target does not exist or the network is unavailable, the renderer normally shows alternative text or a broken-image indication. Obsidian also supports internal embedding in the form `![[image-name.png]]`.

---

## 9. Blockquotes

### What they do

Adding `>` at the start of a line creates a blockquote, suitable for quoting other people, highlighting a definition, or showing supplementary explanation. Consecutive lines can each use `>`; several `>` characters create nested quotations.

### Markdown source

~~~markdown
> One goal of Markdown is to make plain text itself easy to read.
>
> A blockquote can contain multiple paragraphs.

> First-level quote
>> Second-level quote
~~~

### Rendered-result explanation

Rendered quotations normally have a left vertical bar, indentation, and a different text color. An empty quotation line `>` separates paragraphs within the same quotation block.

---

## 10. Inline code and code blocks

### What they do

Inline code uses one pair of backticks and suits commands, variable names, filenames, or short code. Multi-line code uses a block enclosed by three backticks. Write a language name after the opening backticks to enable syntax highlighting. Markdown symbols inside code are not interpreted as formatting.

### Markdown source

~~~~markdown
Use `git status` to inspect repository state.

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"

print(greet("Markdown"))
```
~~~~

### Rendered-result explanation

Inline code sits inside a paragraph and uses a monospaced font. A code block occupies its own region and preserves spacing, indentation, and line breaks. With the `python` label, renderers that support highlighting color keywords and strings.

Use `git status` to inspect repository state.

~~~python
def greet(name: str) -> str:
    return f"Hello, {name}!"

print(greet("Markdown"))
~~~

---

## 11. Tables

### What they do

GFM tables use vertical bars `|` to separate columns and a hyphen row below the header. Colons in that separator control alignment: a left colon means left aligned, colons on both sides mean centered, and a right colon means right aligned. Source vertical bars need not align perfectly, but alignment makes them easier to read.

### Markdown source

~~~~markdown
| Syntax | Purpose | Mastery |
| :--- | :---: | ---: |
| `#` | heading | 100% |
| `**` | bold | 80% |
| `` ` | inline code | 60% |
~~~~

### Rendered-result explanation

This renders as a three-column table: the first column left aligned, second centered, and third right aligned. If a cell itself must display a vertical bar, write it as `\|`.

---

## 12. Thematic breaks

### What they do

At least three hyphens, asterisks, or underscores on a line by themselves create a horizontal thematic break. To avoid ambiguity with headings or lists, leave a blank line before and after it and use `---` consistently.

### Markdown source

~~~markdown
First section content.

---

Second section content.
~~~

### Rendered-result explanation

Three hyphens render as a horizontal separator between content areas. Note that paired `---` at the very top of a document can be recognized as YAML frontmatter rather than an ordinary separator.

---

## 13. Escaping characters

### What it does

When you need to display a special symbol used by Markdown without triggering its formatting, add a backslash `\` before it. Common escapable characters include `\`, backticks, `*`, `_`, `{}`, `[]`, `()`, `#`, `+`, `-`, `.`, `!`, `|`, and `>`, among other ASCII punctuation.

### Markdown source

~~~markdown
\# This is not a heading

\*This is not italic\*

\[This is not link text\]

Write a literal backslash as: \\
~~~

### Rendered-result explanation

When rendered, the first escaping backslash normally does not appear, while the following special character displays as ordinary text. Symbols in a code span or code block are already not parsed as Markdown and normally need no further escaping.

---

## 14. Mixing HTML and Markdown

### What it does

Many Markdown renderers allow some raw HTML to supplement details Markdown does not express well, such as keyboard keys, disclosure areas, superscripts, subscripts, or precise layout. HTML availability depends on the platform; some sites filter tags, attributes, scripts, and styles for safety.

### Markdown source

~~~markdown
Press <kbd>Ctrl</kbd> + <kbd>S</kbd> to save the file.

The formula for water is H<sub>2</sub>O, and a square can be written x<sup>2</sup>.

<mark>This text uses HTML highlighting.</mark>

<details>
<summary>Click to reveal the answer</summary>

The answer can still contain **Markdown bold**.

</details>
~~~

### Rendered-result explanation

When these tags are supported, `kbd` displays a keycap, `sub` and `sup` display subscripts and superscripts, `mark` highlights text, and `details` creates a collapsible area. If a platform disables raw HTML, tags can be removed, escaped, or displayed as text.

---

## 15. Common GitHub Flavored Markdown syntax

### What it does

GitHub Flavored Markdown (GFM) is a dialect that adds common extensions to core Markdown. Its representative extensions include tables, task lists, strikethrough, and autolinks. Fenced code blocks come from CommonMark and are a frequently used core syntax on GitHub too. GitHub pages also recognize platform-specific constructs such as `@username`, issue numbers, and commit hashes, but those features may not work in other Markdown tools.

### Markdown source

~~~~markdown
~~A retired approach~~

- [x] Complete
- [ ] To do

| Item | Status |
| --- | --- |
| Documentation | Complete |

Visit https://github.com to see an autolink.

```javascript
console.log("GFM fenced code block");
```
~~~~

### Rendered-result explanation

In a GFM-supporting host, the content renders as strikethrough, task checkboxes, a table, clickable bare URL, and syntax-highlighted code. Obsidian supports most of these common forms, but its platform-specific behavior does not exactly match GitHub's.

~~A retired approach~~

- [x] Complete
- [ ] To do

| Item | Status |
| --- | --- |
| Documentation | Complete |

Visit https://github.com to see an autolink.

~~~javascript
console.log("GFM fenced code block");
~~~

---

## 16. Common Markdown extensions in Obsidian

### What they do

Beyond standard Markdown and GFM, Obsidian provides extensions for bidirectional links, embeds, callouts, highlighting, and more. They suit personal knowledge bases well but do not necessarily render the same way outside Obsidian.

### Markdown source

~~~markdown
[[The Complete Markdown Tutorial]]

[[The Complete Markdown Tutorial#11-tables|Jump to the tables section]]

==This is highlighted text==

> [!note] Obsidian note block
> This is a callout.
~~~

### Rendered-result explanation

Double square brackets create a vault-internal link, and `|` can set display text. Double equals signs create highlighting; a quotation starting with `[!note]` displays as an Obsidian callout. Obsidian tracks internal links and can update them when a target note is renamed.

---

## 17. Integrated practice

### What it does

The next exercise combines headings, paragraphs, emphasis, lists, tasks, links, quotations, code, and tables into a short note. Type the source manually, then switch to Reading View to check it; that builds memory more effectively than only reading syntax.

### Markdown source

~~~~markdown
# Markdown learning record

Today I studied **Markdown** and completed:

- [x] Headings and paragraphs
- [x] Lists and tasks
- [ ] Tables and code blocks

> Ten minutes of daily practice is more effective than memorizing all syntax at once.

A useful command is `git status`:

```powershell
git status --short
```

| Topic | Status |
| --- | --- |
| Basic syntax | mastered |
| GFM | practicing |

Reference: [CommonMark](https://commonmark.org/)
~~~~

### Rendered-result explanation

After rendering, this becomes a clearly structured learning record: a level-one heading at the top, a task list and quotation in the middle, a command shown as inline code and a code block, learning progress summarized in a table, and a clickable external link at the end.

> [!success] Completion criterion
> If you can write most of the integrated-practice structure independently without looking at the tutorial, you have mastered the Markdown basics needed for daily writing.

---

## Quick reference

| Goal | Common source |
| --- | --- |
| Level-one heading | `# Heading` |
| Bold | `**text**` |
| Italic | `*text*` |
| Strikethrough | `~~text~~` |
| Unordered list | `- item` |
| Ordered list | `1. item` |
| Task list | `- [ ] task` |
| Link | `[text](URL)` |
| Image | `![alternative text](image address)` |
| Quotation | `> quotation` |
| Inline code | ``code`` |
| Code block | Code enclosed by three backticks |
| Table | Columns separated by <code>&#124;</code> (write <code>&#92;&#124;</code> to display a bar inside a cell) |
| Thematic break | `---` |
| Escape | `\*not italic*` |
