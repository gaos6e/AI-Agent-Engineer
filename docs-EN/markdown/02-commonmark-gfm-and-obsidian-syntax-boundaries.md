---
title: "CommonMark, GFM, and Obsidian Syntax Boundaries"
tags:
  - ai-agent-engineer
  - markdown
  - commonmark
  - obsidian
aliases:
  - Markdown dialect boundaries
  - Markdown compatibility
source_checked: 2026-07-14
lang: en
translation_key: "Markdown/02-CommonMark、GFM与Obsidian语法边界.md"
translation_source_hash: 2baf24d79a4d0f6e4fa4070b24b6f2b7c94ddb4d0177efa1d3cb8164d4bb03d7
translation_route: zh-CN/Markdown/02-CommonMark、GFM与Obsidian语法边界
translation_default_route: zh-CN/Markdown/02-CommonMark、GFM与Obsidian语法边界
---

# CommonMark, GFM, and Obsidian Syntax Boundaries

## Lesson goal

This lesson addresses an engineering question: why can Markdown look correct in Obsidian but change after being copied to GitHub, a documentation site, or model context? Afterward, you should be able to label the layer to which each syntax feature belongs and choose between portability and fully using Obsidian for a delivery target.

## Markdown is not one runtime

“Markdown” is a family name. The actual result is determined jointly by the syntax dialect, host parser, and rendering environment.

~~~mermaid
flowchart TD
    Core["CommonMark: portable core"] --> GFM["GFM: GitHub user-content dialect"]
    Core --> Obsidian["Obsidian Flavored Markdown"]
    GFM --> Obsidian
    Obsidian --> Host["Obsidian version, settings, theme, and plugins"]
~~~

As of **2026-07-14**:

- The latest released specification listed by the CommonMark site is **0.31.2 (2024-01-28)**.
- GFM's formal specification page is still **0.29-gfm (2019-04-06)**. It is a dialect for GitHub user content, not a version-number relationship of “the newest CommonMark plus a few features.”
- On top of CommonMark/GFM, Obsidian provides host capabilities such as wikilinks, embeds, callouts, Properties, comments, and Mermaid.

These versions are checked facts, not permanent guarantees. Revisit the official pages when reusing a note later.

## Three-layer capability matrix

| Capability | CommonMark 0.31.2 | GFM 0.29-gfm | Obsidian | Engineering guidance |
| --- | :---: | :---: | :---: | --- |
| headings, paragraphs, lists, quotations | yes | yes | yes | use as the portable skeleton |
| emphasis, links, images, code fences | yes | yes | yes | prefer for external delivery |
| tables | no | extension | supported | use only for short comparisons |
| strikethrough | no | extension | supported | do not make it the only state evidence |
| task lists | no | extension | supported and interactive | interaction may change after export |
| bare-URL extension autolinks | limited | extension | host-dependent | write descriptive text for important links |
| `[[wikilink]]` | no | no | yes | use for navigation within the vault |
| `![[embed]]` | no | no | yes | convert before leaving Obsidian |
| `> [!note]` callout | no | no | yes | do not assume another renderer displays it identically |
| YAML Properties | not defined by the spec | not defined by the spec | native structured properties | some platform contexts have separate frontmatter behavior; do not classify it as GFM |
| Mermaid fence | only a code fence with an info string | GFM spec does not define diagram rendering | host can render it | Mermaid is a host capability, not a GFM syntax guarantee |

> [!important] Keep specifications and platform features separate
> GitHub's web UI can render Mermaid, but Mermaid is not part of GFM 0.29-gfm. Likewise, GitHub's `@mention` syntax, issue references, and commit-hash recognition are platform behavior. Compatibility notes should say which host provides which capability.

## Writing a portable core

When a document must be read in Obsidian, GitHub, and ordinary Markdown tools, prefer:

- ATX headings such as `## Heading`;
- blank lines between paragraphs;
- `-` lists and `1.` steps;
- standard Markdown external links and relative file links;
- fenced code with language tags;
- simple quotations;
- text that does not need CSS to be understood.

A portable README fragment:

~~~~markdown
## Run

Run this from the repository root:

```powershell
python -m unittest
```

Expected: the test process exits with code `0`. Fill actual results in the change record; do not claim success before it has happened.
~~~~

Even when the syntax is portable, paths, shells, and commands can remain incompatible. Markdown compatibility is not execution-environment compatibility.

## When to use GFM extensions

If GitHub is the main delivery target, you can use tables, task lists, strikethrough, and extended autolinks, while keeping their boundaries in mind:

- Table cells suit short inline content only and cannot reliably contain complex blocks.
- The task-list specification defines checkbox structure, while clickability depends on the implementation.
- Strikethrough communicates “retired” clearly, but does not preserve the reason or time of retirement.
- Some hosts recognize bare URLs, but formal documentation should still use `[description](URL)`.

## When to use Obsidian extensions

Internal knowledge-base collaboration can take advantage of:

- full-path wikilinks, with backlinks and rename updates;
- note, heading, block, and attachment embeds;
- Properties for search and downstream consumers such as Dataview;
- callouts for warnings, examples, and supplements;
- Mermaid for flows and relationships.

The cost is greater lock-in. Before export, decide whether to retain source, convert to ordinary links or images, or explicitly require readers to use Obsidian.

## HTML is not a universal escape hatch

CommonMark permits raw HTML blocks, but a host may filter, escape, or parse them internally in different ways. Obsidian's official documentation states that **Markdown syntax does not continue to parse inside HTML elements**. Therefore:

~~~html
<details>
<summary>Reveal the answer</summary>
<strong>This uses HTML bold, not Markdown asterisks.</strong>
</details>
~~~

Do not assert that a mixed form behaves the same in Obsidian or a publication system just because it works on GitHub. HTML also reduces plain-text readability; use it only when core syntax cannot express the need and the target host has been verified.

## Compatibility decision flow

1. **Identify readers and target hosts:** only this vault, GitHub too, or unknown tools?
2. **Write a portable skeleton:** headings, paragraphs, lists, code, and ordinary links.
3. **Add extensions one at a time:** every extension should answer “what problem does it solve?”
4. **Record a fallback:** callout to quotation, embed to link, Mermaid to SVG or text explanation.
5. **Verify in the real targets:** check editor preview, Obsidian Reading View, and GitHub separately.
6. **Record versions and unverified items:** especially Mermaid, plugins, and publication systems.

## Hands-on practice: label the syntax

Label each item below as `CommonMark`, `GFM`, `Obsidian`, or `platform feature`, then state a fallback after it leaves its original host:

1. `## Heading`
2. `- [ ] Task`
3. `[[Knowledge/AI Agent Engineer/docs-EN/markdown/00-index|Markdown]]`
4. `> [!warning]`
5. A Mermaid code fence rendered as an SVG diagram
6. `#123` automatically turning into an issue link on GitHub

Reference classification: item 1 is CommonMark; item 2 is a GFM extension also supported by Obsidian; items 3 and 4 are Obsidian extensions; item 5 depends on host rendering; item 6 is GitHub platform behavior.

Next, choose a note in this vault containing a wikilink, callout, and Mermaid. Copy it to a temporary file and design a “plain Markdown fallback.” You do not need to publish it, but list what would be lost.

## Common misconceptions

- **Calling GFM the one standard Markdown:** it is a particular dialect.
- **Treating a fence language name as a promise of execution:** `mermaid` and `python` are only info strings; the host decides what to do.
- **Treating Obsidian preview as a cross-platform test:** it proves behavior only in the current host with the current settings.
- **Rejecting every extension for portability:** an internal knowledge base can use extensions if it records boundaries and fallbacks.
- **Forcing HTML to fix all layout:** this increases security, compatibility, and maintenance cost.

## Self-check and mastery criteria

1. How are GFM and CommonMark related, and why should their version numbers not be mixed?
2. Why is Mermaid not a formal extension in the way GFM tables are?
3. Which syntax is suitable for a cross-platform skeleton?
4. Which Obsidian-specific abilities should be checked before export?
5. Why must Markdown behavior inside HTML be verified per host?

- [ ] I can label the layer of common syntax.
- [ ] I can design fallbacks for wikilinks, embeds, callouts, and Mermaid.
- [ ] I can distinguish specification facts, host capabilities, and engineering recommendations.
- [ ] I can record the target host, check date, and unverified items.

Previous: [[markdown/01-markdown-basics-and-readable-source-files|Markdown basics and readable source files]].  
Next: [[markdown/03-obsidian-links-attachments-and-embeds|Obsidian links, attachments, and embeds]].

## References

Checked: **2026-07-14**.

- [Current CommonMark specification](https://spec.commonmark.org/)
- [GitHub Flavored Markdown Specification 0.29-gfm](https://github.github.com/gfm/)
- [Obsidian Flavored Markdown](https://obsidian.md/help/obsidian-flavored-markdown)
- [GitHub: Creating diagrams](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams)
