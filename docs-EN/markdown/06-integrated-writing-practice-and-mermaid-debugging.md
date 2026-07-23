---
title: "Integrated Writing Practice and Mermaid Debugging"
tags:
  - ai-agent-engineer
  - markdown
  - practice
aliases:
  - Markdown practice
  - Markdown rendering debugging
source_checked: 2026-07-14
lang: en
translation_key: "Markdown/06-综合写作练习与Mermaid排错.md"
translation_source_hash: 4272ca90624993f7b7c332b46ac6fb2c92bf3619e5f2f16d5c6e2d7f9eef772f
translation_route: zh-CN/Markdown/06-综合写作练习与Mermaid排错
translation_default_route: zh-CN/Markdown/06-综合写作练习与Mermaid排错
---

# Integrated Writing Practice and Mermaid Debugging

## Lesson goal

Use a set of short tasks to connect the first five lessons and diagnose problems across the three layers “source text → parsing rules → renderer.” Complete the tasks independently before comparing against the acceptance checklist. When syntax is unfamiliar, consult [[markdown/markdown-tutorial|The Complete Markdown Tutorial]] rather than repeatedly trying characters by luck.

## Exercise 1: turn a messy instruction into structure

Original text:

~~~text
Start the service. Python is required. Create an environment first. Install dependencies. Run app.py. Check logs on failure. Do not commit .env.
~~~

Rewrite requirements:

- The level-one heading is the document name; body content begins at level two.
- Add five sections: prerequisites, procedure, verification, failure handling, and safety.
- Use a fenced command with the `powershell` language tag.
- Use inline code for filenames and variables.
- State “do not commit `.env`” as an explicit safety rule, not as text hidden at the end of a paragraph.

When complete, inspect the source alone for a clear hierarchy, then inspect Reading View to ensure lists and code blocks remain continuous.

## Exercise 2: lists, tasks, and tables

Write a three-stage checklist: preparation, execution, and acceptance. Give each stage at least three tasks and give one task two nested items. Then use a table to record check item, owner, evidence, and status.

Common errors:

- no blank line before a list, so some renderers join it to the paragraph;
- inconsistent nested indentation;
- a table separator row whose column count differs from the heading;
- an unescaped `|` in a cell, unexpectedly splitting a column;
- manually aligning body text with spaces, which fails after a font change.

## Exercise 3: link strategy

Design three kinds of link for a knowledge note:

1. A vault-internal note: use a folder-qualified wikilink to avoid ambiguity from many `00-index` pages.
2. An external specification: use `[descriptive text](https://...)`.
3. An image or PDF embed: use an Obsidian embed and confirm the target file truly exists.

Link text should describe its target; do not repeatedly use “click here.” Revalidate paths after modifying or moving a file.

## Exercise 4: code and output

An engineering document must distinguish commands, output, and placeholders:

~~~powershell
python --version
~~~

~~~text
Python 3.x.y
~~~

The `3.x.y` above denotes the actual version on the reader's machine, not a fixed version claimed as verified. If a command was not run, write “expected” rather than “run result.” Do not put real tokens, cookies, or internal addresses in code blocks.

## Exercise 5: a minimal Mermaid diagram

First draw a three-node flow: input, validation, output. Add only one structure at a time rather than starting with extensive styling. Quote node text containing parentheses or punctuation, then verify it in Reading View.

Diagrams express relationships and flows. Exact parameters, long explanations, and copyable commands still belong in prose or tables.

First complete the flowchart:

~~~mermaid
flowchart LR
    Input["Input: meeting text"] --> Validate{"Format valid?"}
    Validate -->|yes| Output["Output: summary draft"]
    Validate -->|no| Stop["Stop and report an error"]
~~~

Then rewrite the same task as a minimal sequence diagram to experience the difference between a step flow and interaction among participants:

~~~mermaid
sequenceDiagram
    participant U as User
    participant A as Summary tool
    U->>A: Submit local text
    A-->>U: Return a summary draft or validation error
~~~

The completion criterion is not “the more complex the diagram, the better.” A reader should be able to answer who supplies input, when the process stops, and who receives the result. Read the [[markdown/references-versions-and-compatibility#Mermaid large-tutorial compatibility notes|Mermaid compatibility notes]] first, then consult [[markdown/mermaid-tutorial|The Complete Mermaid Tutorial]] as needed.

## Exercise 6: Properties, links, and embeds

Create a practice note that:

1. uses `title`, `tags`, and `aliases` in frontmatter, with each key appearing only once;
2. uses a full-path wikilink to this knowledge-base index;
3. uses a heading link to [[markdown/03-obsidian-links-attachments-and-embeds#Linking to headings and blocks|Linking to headings and blocks]];
4. writes one collapsible `[!example]-` callout;
5. explains the difference between a link and an embed without creating a fictitious attachment.

Do not put a token, account, or internal-server address in Properties; hidden display does not equal encryption.

## Rendering-debugging order

1. Reduce the issue to the smallest failing fragment.
2. Check whether fences are paired and use matching counts of backticks.
3. Check blank lines before lists and nested indentation.
4. Check `|`, line breaks, and inline code in tables.
5. Check the real target of a wikilink or embed.
6. Distinguish CommonMark syntax, a GFM extension, and Obsidian-specific syntax.
7. Recheck in the actual Reading View instead of trusting editor highlighting alone.

If the problem occurs only in Mermaid:

1. Reduce the diagram to “diagram type + two nodes + one edge.”
2. Confirm that the code-block language is `mermaid` and fences are paired.
3. When node text has parentheses, colons, slashes, or angle brackets, quote it first.
4. Check that every `subgraph` has an `end` and node IDs do not repeat.
5. Add original content back a section at a time to find the first failing increment.
6. Finally recheck in the current Obsidian Reading View, because the embedded host version can lag behind Mermaid's website.

> [!warning] Nested code fences
> To show a three-backtick code block inside another Markdown code block, the outer fence must use four or more backticks, or use tildes instead. Fences of the same length will close the outer block early.

## Exercise acceptance

- [ ] The document source remains understandable without rendering.
- [ ] Headings do not skip levels, and list hierarchy is clear.
- [ ] Commands and output are separately labeled; expectations are not presented as measurements.
- [ ] Internal and external links use the correct form and their targets are accessible.
- [ ] The Mermaid diagram expresses a flow instead of repeating a full body paragraph.
- [ ] After rewriting one task as a flowchart and a sequence diagram, I can explain the question each answers.
- [ ] Property keys are unique, value types are clear, and internal links use real full paths.
- [ ] There are no real credentials, unexplained dangerous commands, or ambiguous placeholders.

Score every item from 0 to 2: 0 means missing, 1 means present but still needs oral explanation, and 2 means another beginner can review it from the file alone. If the total is below 12, repair structure and evidence before visual decoration.

## Self-check and sources

1. Why do both source clarity and attractive rendering matter?
2. When should you use a wikilink, and when a standard Markdown link?
3. Why should code fences have language tags?
4. What information cannot be replaced by a Mermaid diagram?
5. Why can outer and inner code fences not be the same length?
6. If Mermaid's website renders but Obsidian does not, how should you locate the boundary of the problem?

Previous: [[markdown/05-structured-technical-writing-for-agent-engineering|Structured technical writing for Agent engineering]].  
Next: [[markdown/07-knowledge-base-runbook-project-and-self-test|Knowledge-base runbook project and self-test]].

Checked: **2026-07-14**.

- [CommonMark Specification](https://spec.commonmark.org/0.31.2/)
- [Obsidian: Basic formatting syntax](https://obsidian.md/help/syntax)
- [Mermaid: Flowcharts](https://mermaid.js.org/syntax/flowchart.html)
- [Mermaid: Sequence diagrams](https://mermaid.js.org/syntax/sequenceDiagram.html)
