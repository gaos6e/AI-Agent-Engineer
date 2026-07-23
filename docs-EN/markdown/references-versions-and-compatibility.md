---
title: "Markdown References, Versions, and Compatibility Notes"
tags:
  - ai-agent-engineer
  - markdown
  - compatibility
  - sources
aliases:
  - Markdown version notes
  - Mermaid compatibility corrections
source_checked: 2026-07-14
lang: en
translation_key: "Markdown/参考资料、版本与兼容性说明.md"
translation_source_hash: 0638470629f23fbc3542d4c8e5cdc8ad1fc7177397e10d99d258860cc580e286
translation_route: zh-CN/Markdown/参考资料、版本与兼容性说明
translation_default_route: zh-CN/Markdown/参考资料、版本与兼容性说明
---

# Markdown References, Versions, and Compatibility Notes

## What this note resolves

This knowledge base retains [[markdown/markdown-tutorial|The Complete Markdown Tutorial]] and [[markdown/mermaid-tutorial|The Complete Mermaid Tutorial]] as large reference materials rather than rewriting them into one uniform format. Large tutorials suit topic-by-topic lookup, but host capabilities and upstream syntax can change. This page records the checked versions, compatibility boundaries, and preferred precise wording.

## Version facts as of the check date

Checked: **2026-07-14**.

| Item | Checked fact | Boundary when using it |
| --- | --- | --- |
| CommonMark | The latest released specification on the official site is 0.31.2 (2024-01-28). | It is a community-maintained explicit specification, not proof that every Markdown tool behaves identically. |
| GFM | The formal specification page is 0.29-gfm (2019-04-06). | Tables, task lists, strikethrough, and extended autolinks are GFM extensions. |
| Obsidian | Uses Obsidian Flavored Markdown and provides wikilinks, embeds, Properties, callouts, Mermaid, and related capabilities. | Actual rendering in this vault still depends on the local version, settings, theme, and plugins. |
| Mermaid upstream | The official documentation currently shows capabilities associated with 11.16.0. | New upstream syntax does not mean the host already bundles it. |
| Obsidian Mermaid | Obsidian 1.13.0 release notes state that it bundles Mermaid 11.13.0 and adds vault-level Mermaid-rendering confirmation. | This does not establish that the local machine is running 1.13.0; this knowledge base did not read or confirm its local Obsidian version. |
| GitHub Mermaid | GitHub documents Mermaid as a platform diagram feature and provides an `info` diagram that shows its current version. | This is not a syntax extension of GFM 0.29-gfm. |

Version facts are accountable only for their check date. Before copying new syntax, run a minimal rendering test in the target host.

## Compatibility notes for the large Markdown tutorial

### Markdown inside HTML elements

In Obsidian, Markdown syntax does not continue parsing inside an HTML element. If bold text is needed in `<details>`, use HTML:

~~~html
<details>
<summary>Reveal the answer</summary>
<strong>This is predictable bold text in Obsidian.</strong>
</details>
~~~

Do not generalize a mixed-parsing result in GitHub or a browser to Obsidian. A more portable choice is moving Markdown body text out of the HTML container.

### An alias is not a bare link target

To display “The Complete Markdown Tutorial,” the deterministic form is a real path plus display text:

~~~markdown
[[Knowledge/AI Agent Engineer/docs-EN/markdown/markdown-tutorial|The Complete Markdown Tutorial]]

[[Knowledge/AI Agent Engineer/docs-EN/markdown/markdown-tutorial#11. Tables|Jump to the tables section]]
~~~

Do not place only a `title` value or alias text to the left of `[[...]]` and assume it will always resolve to the real file.

### Say what “standard Markdown” means

This knowledge base prefers “CommonMark-compatible syntax,” “GFM extension,” or “Obsidian-specific syntax,” avoiding the implication that one single standard is fully implemented by every host.

## Mermaid large-tutorial compatibility notes

The following accurate boundaries take priority over broader claims in the large tutorial:

1. **Check syntax and host together:** a missing diagram can come from syntax errors, a disabled host, an older bundled version, security confirmation, or permissions. Do not first assert that it “normally is not a syntax problem.”
2. **Subgraph direction is conditional:** when a node in a subgraph connects to a node outside it, Mermaid's official documentation says that the subgraph `direction` is ignored and inherits the parent diagram's direction.
3. **Sequence arrows define only line form and endpoints:** `-->>` is a dashed arrow and `--x` is a dashed line ending in a cross. “Return” and “failure” are message semantics supplied by the author, not automatically guaranteed by syntax.
4. **Class-diagram relations must be exact:** `-->` is association; `..>` is dependency. Whether either means “uses” must follow the domain relationship and label.
5. **State-diagram endpoints use an exact token:** `[*]`, with no space in the middle.
6. **Mindmap remains experimental:** basic syntax is available, but integration capabilities and details can change. If the target host does not support it, fall back to a flowchart.
7. **GitHub rendering is not GFM:** GitHub Mermaid support is a platform feature. Its documentation says you can use an `info` diagram to inspect the current Mermaid version.
8. **Nested fences need a longer outer fence:** the large tutorial's former “Obsidian recommendation” example used fences of the same length and caused subsequent text to be swallowed. This revision changed only its outer fence to four backticks, without rewriting the tutorial content.

### Host-version probe

GitHub documents this `info` diagram, which displays the Mermaid version used by GitHub's renderer. It is not a universal version probe for Obsidian:

~~~~markdown
```mermaid
info
```
~~~~

In Obsidian, check the current application version and release notes, then test target syntax directly with a two-node minimal diagram. Do not infer that the current vault supports a syntax merely because a website example works.

## Priority of sources

When sources conflict, decide in this order:

1. official documentation and release notes for the current target host;
2. the relevant formal syntax page for CommonMark, GFM, or Mermaid;
3. newly created formal course notes in this knowledge base;
4. historical examples in the two large tutorials;
5. memory, search summaries, or unverified community answers.

When evidence remains insufficient, say “currently can only infer” or “not verified in the target version.”

## Primary sources

- [Current CommonMark specification](https://spec.commonmark.org/)
- [GitHub Flavored Markdown Specification](https://github.github.com/gfm/)
- [Obsidian Flavored Markdown](https://obsidian.md/help/obsidian-flavored-markdown)
- [Obsidian: Properties](https://obsidian.md/help/properties)
- [Obsidian: Internal links](https://obsidian.md/help/links)
- [Obsidian: Aliases](https://obsidian.md/help/aliases)
- [Obsidian: Embed files](https://obsidian.md/help/embeds)
- [Obsidian: Callouts](https://obsidian.md/help/callouts)
- [Obsidian: Advanced formatting syntax](https://obsidian.md/help/advanced-syntax)
- [Obsidian Desktop 1.13.0 changelog](https://obsidian.md/changelog/2026-05-28-desktop-v1.13.0/)
- [Mermaid: Flowcharts](https://mermaid.js.org/syntax/flowchart.html)
- [Mermaid: Sequence diagrams](https://mermaid.js.org/syntax/sequenceDiagram.html)
- [Mermaid: Class diagrams](https://mermaid.js.org/syntax/classDiagram.html)
- [Mermaid: State diagrams](https://mermaid.js.org/syntax/stateDiagram.html)
- [Mermaid: Mindmaps](https://mermaid.js.org/syntax/mindmap.html)
- [GitHub: Creating diagrams](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams)

Return to the [[markdown/00-index|Markdown index]].
