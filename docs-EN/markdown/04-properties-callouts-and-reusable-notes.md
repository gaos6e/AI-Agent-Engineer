---
title: "Properties, Callouts, and Reusable Notes"
tags:
  - ai-agent-engineer
  - markdown
  - obsidian
  - properties
aliases:
  - Introduction to Obsidian Properties
  - Reusable note structure
source_checked: 2026-07-14
lang: en
translation_key: "Markdown/04-Properties、Callouts与可复用笔记.md"
translation_source_hash: 404f8f81842e1c7e9a927666570ca258f69c673e2dfb196bf32f738343ffd164
translation_route: zh-CN/Markdown/04-Properties、Callouts与可复用笔记
translation_default_route: zh-CN/Markdown/04-Properties、Callouts与可复用笔记
---

# Properties, Callouts, and Reusable Notes

## Lesson goal

This lesson upgrades a Markdown note that merely “displays” into an Obsidian note that is searchable, reusable, and maintainable over time. You will learn to design simple Properties, choose callout types, and avoid putting body text, secrets, or complex objects into frontmatter.

## Properties are metadata, not body text

Properties live in YAML frontmatter at the top of a file, enclosed by paired `---` delimiters. They are suitable for short, atomic, searchable information such as title, tags, aliases, dates, and Boolean status.

~~~yaml
---
title: Reliable API client runbook
tags:
  - AI-Agent-Engineer
  - API
aliases:
  - API Runbook
status: draft
reviewed: false
source_checked: 2026-07-14
related:
  - "[[Knowledge/AI Agent Engineer/docs-EN/api/00-index|API]]"
---
~~~

Key rules:

- Frontmatter must begin on the first line of the file.
- A property name can appear only once in one note.
- `tags`, `aliases`, and `cssclasses` are Obsidian default property names.
- Quote internal links in properties so YAML does not interpret square brackets as another structure.
- `title` is a metadata value; it does not automatically replace the real filename. Links still target the file path.
- Properties are not an encrypted area. Their values remain in a plain-text file after display is hidden.

## Choose the right property type

Obsidian currently supports text, list, number, checkbox, date, date-time, and tags property types. One property name carries one type across the vault, so do not write the same key as a list in one note and free text in another.

| Type | Example | Suitable for | Not suitable for |
| --- | --- | --- | --- |
| Text | `status: draft` | short states, version labels | multi-paragraph explanation |
| List | several entries below `aliases:` | aliases, related topics, owners | ordered operational steps |
| Number | `score: 8` | comparable values | expressions such as `8/10` |
| Checkbox | `reviewed: false` | yes/no state | a multi-state workflow |
| Date | `source_checked: 2026-07-14` | review dates, deadlines | a vague “recently” |
| Date-time | ISO 8601 timestamp | event time | cross-system logs without a time zone |
| Tags | list below `tags:` | stable categories | a full-sentence description |

Obsidian's official documentation explicitly says that Properties do not render Markdown and do not natively support visual editing of nested properties. Put complex objects, long reasons, or multi-step workflows in the body. If a machine must consume complex structure, consider a separate JSON or YAML file with a defined contract.

## Common YAML errors

### Colons, hashes, and quotes

When a value contains `: `, `#`, `[`, `]`, or text that might parse as a Boolean or date, quoting is safer:

~~~yaml
summary: "Boundary: read local files only"
ticket: "#123"
literal_date: "2026-07-14"
~~~

Do not mechanically quote every value; the goal is to make its type clear. If a date must be searchable as a date, retain the date type instead of forcing it to text.

### Duplicate keys

The following is not “two tag groups”; it is a conflicting duplicate key:

~~~yaml
tags:
  - Markdown
tags:
  - Obsidian
~~~

Merge it into one list. Some YAML tools silently retain the final value, causing data loss, so static checks must explicitly reject duplicate keys.

### Treating sensitive information as metadata

Wrong examples include `api_key`, cookies, a full internal-service address, and real customer names. Properties can be read by search, plugins, and sync tools; “not displayed in Reading View” does not mean “not leaked.” Keep keys only in controlled environment variables, and provide only `.env.example` files or placeholders in instructional material.

## Callouts provide semantic emphasis

A callout is Obsidian's blockquote extension. Its basic form is:

~~~markdown
> [!warning] Stop condition
> If the input contains real customer data, stop immediately and do not continue testing.
~~~

Place a collapse state after the type:

~~~markdown
> [!example]- Expand to view the example
> This is a supplementary example collapsed by default.

> [!info]+ Expanded by default
> This is extra context, not a required step.
~~~

Common semantics:

| Type | Purpose | Use boundary |
| --- | --- | --- |
| `note` / `info` | background and supplementary material | do not hide required steps |
| `tip` | efficiency suggestion | not required for correctness |
| `warning` / `danger` | data loss, security, or irreversible risk | few, explicit, and not collapsed by default |
| `example` | reference case or answer | separated from the main flow |
| `question` | self-check or unresolved decision | state how to answer or who owns it |

Callouts can nest and contain links, embeds, and ordinary Markdown, but deep nesting makes source text harder to read. If content is part of the main flow, use a normal heading and body text rather than hiding it in a collapsed block.

## Design a reusable note skeleton

The value of a template is reducing omissions, not making every topic look the same. An engineering description can begin with this skeleton:

~~~~markdown
---
title: Tool name and task
tags:
  - AI-Agent-Engineer
aliases:
  - A searchable former name
source_checked: 2026-07-14
---

# Tool name and task

## Goal and non-goals

State what the reader will accomplish and what is explicitly out of scope.

## Prerequisites

List the environment and verification commands.

## Input/output contract

Define format, sensitivity level, and failure conditions.

## Procedure

In dependency order, state purpose, command, expectation, and stop condition.

## Verification and unverified items

Distinguish actual execution, expected results, and work that needs human review.

## References

Record primary sources and their check date.
~~~~

Concept notes, experiment records, and runbooks can reuse metadata keys but should choose different body structures. Do not mistake a “complete template” for correct content.

## A small property contract

When several people maintain content, define high-frequency keys first:

| Key | Type | Constraint | Example |
| --- | --- | --- | --- |
| `title` | text | one per note; describes the real topic | `Markdown link audit` |
| `tags` | list | use existing categories; avoid synonym explosion | `AI-Agent-Engineer` |
| `aliases` | list | only real former names or common abbreviations | `GFM` |
| `source_checked` | date | update only after sources were actually checked | `2026-07-14` |
| `status` | text | controlled enumeration, such as `draft/reviewed` | `reviewed` |

Keep engineering recommendations and Obsidian-enforced rules separate. The table is course guidance, not an Obsidian built-in schema.

## Hands-on practice

1. Design frontmatter for a “local log analysis” note, including at least `title`, `tags`, `aliases`, `source_checked`, and one checkbox.
2. In the body, write four sections: goal, input/output, procedure, and verification. Do not put procedures into Properties.
3. Add one non-collapsed security warning and one example collapsed by default.
4. Deliberately duplicate a property key, observe the source, then delete the duplicate. Do not rely on a parser to decide which value to retain.
5. List three things that must not enter Properties and explain why.

Acceptance: another reader can filter notes using Properties alone and understand the task using body text alone; neither section duplicates the other's responsibility.

## Common misconceptions

- **Treating `title` as a file alias:** use `aliases`; a link target remains the path.
- **More tags make search easier:** synonymous tags make classification unmanageable, and full-text search still exists.
- **All information should be structured:** put long explanations in the body and keep Properties atomic.
- **A collapsed warning is cleaner:** important risks should not be hidden by default.
- **Every template field must be filled:** deleting a meaningless field is clearer than filling it with “none.”
- **Changing a date means sources were rechecked:** change `source_checked` only after sources and behavior were actually reviewed.

## Self-check and mastery criteria

1. What should Properties and body text each store?
2. Why should a same-named property retain the same type?
3. Why do wikilinks in a property need quotes?
4. Which callouts should not be collapsed by default?
5. Why does hiding Properties from view not make them safe?

- [ ] I can write valid frontmatter with no duplicate keys.
- [ ] I can choose text, list, date, and checkbox types.
- [ ] I can use callouts for supplements, examples, and real warnings.
- [ ] I can design a concise property contract and distinguish engineering guidance from product rules.

Previous: [[markdown/03-obsidian-links-attachments-and-embeds|Obsidian links, attachments, and embeds]].  
Next: [[markdown/05-structured-technical-writing-for-agent-engineering|Structured technical writing for Agent engineering]].

## References

Checked: **2026-07-14**.

- [Obsidian: Properties](https://obsidian.md/help/properties)
- [Obsidian: Aliases](https://obsidian.md/help/aliases)
- [Obsidian: Callouts](https://obsidian.md/help/callouts)
- [YAML 1.2.2 Specification](https://yaml.org/spec/1.2.2/)
