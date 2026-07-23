---
title: "Obsidian Links, Attachments, and Embeds"
tags:
  - ai-agent-engineer
  - markdown
  - obsidian
  - links
aliases:
  - Obsidian internal links
  - Obsidian embeds
source_checked: 2026-07-14
lang: en
translation_key: "Markdown/03-Obsidian链接、附件与嵌入.md"
translation_source_hash: 3209c0c8f22ed89e413fcd5d37a3b72fc22a4deca92bddc9b25c124a400e488d
translation_route: zh-CN/Markdown/03-Obsidian链接、附件与嵌入
translation_default_route: zh-CN/Markdown/03-Obsidian链接、附件与嵌入
---

# Obsidian Links, Attachments, and Embeds

## Lesson goal

After this lesson, you should be able to build maintainable navigation in a vault with many identically named notes, link to headings and blocks, embed real files, and locate broken links after moves or renames. The point is not memorizing `[[ ]]`. It is understanding link targets, display text, and embedded content as separate concerns.

## A link is not a copy

A link retains where to go; an embed displays the target's content here. Both depend on the target file, and an embed's display changes when its source file changes.

| Form | Purpose | Copies content? |
| --- | --- | :---: |
| `[[path/note\|display text]]` | navigate to a note | no |
| `[[path/note#heading\|display text]]` | navigate to a heading | no |
| `[[path/note#^block-ID\|display text]]` | navigate to a block | no |
| `![[path/note]]` | embed an entire note | no |
| `![[path/image.png]]` | embed an attachment | no |
| `[text](https://...)` | open an external URL | no |

Deleting a target, changing a heading, or breaking a block ID can all affect links. An embed is neither a backup nor a security boundary.

## Choosing an internal-link form

Obsidian supports wikilinks and Markdown internal links. This vault uses wikilinks for note navigation and standard Markdown links for external web pages.

~~~markdown
[[Knowledge/AI Agent Engineer/docs-EN/markdown/00-index|Markdown learning path]]

[Obsidian Internal links](https://obsidian.md/help/links)
~~~

Why write a full path? The main learning route alone has dozens of identically named `00-index.md` files, and their number can change as courses evolve; nested indexes are also possible. If you write only `[[00-index]]`, the target depends on Obsidian's resolution and the current context, which a static check cannot reliably disambiguate. A full path begins at the vault root and always uses `/`, even on Windows.

> [!tip] Display text is not the target
> In `[[real/file/path|short name]]`, the portion left of `|` determines the target; the right portion only determines what readers see. `aliases` enter link suggestions and can be display text; a custom `title` is only a searchable property and does not replace the filename. For determinism, do not use an alias or `title` by itself as a link target.

## Linking to headings and blocks

### Heading links

~~~markdown
[[Knowledge/AI Agent Engineer/docs-EN/markdown/01-markdown-basics-and-readable-source-files#Whitespace, line breaks, and escaping|Line-break rules]]
~~~

Heading links are readable, but changing heading text affects the anchor. Obsidian may update links when a rename happens in the app, while external scripts or plain filesystem operations may not cover every case. After a rename, inspect the diff and backlinks anyway.

### Block links

When a small passage needs a stable reference, add a block ID:

~~~markdown
Proceed to the next step only after validation passes. ^validation-gate
~~~

Reference it with:

~~~markdown
[[Knowledge/AI Agent Engineer/docs-EN/markdown/examples/link-and-embed-practice-target#^validation-gate|Validation-gate guidance]]
~~~

Block IDs should be short, unique, and meaningful. For structural blocks such as a list, quotation, callout, or table, Obsidian's documentation recommends putting the block ID on its own line with blank lines before and after it. Do not give every sentence an ID; that increases maintenance cost.

## Embed real content

The following embeds a real practice block from this knowledge base:

![[markdown/examples/link-and-embed-practice-target#^validation-gate]]

What you see is the target file's current content, not a copy. Editing the target changes this embed too.

Common embeds:

~~~markdown
![[Knowledge/AI Agent Engineer/docs-EN/markdown/examples/link-and-embed-practice-target]]
![[Knowledge/AI Agent Engineer/docs-EN/markdown/examples/link-and-embed-practice-target#Observable result]]
![[adjacent-directory/attachments/flow-diagram.png]]
![[materials.pdf#page=3]]
~~~

The final two forms are syntax examples only; this knowledge base does not create those attachments. Active links and embeds in the course must point to real targets; instructional code fences may use clearly labeled fictional paths.

## Attachment location and naming

Obsidian can place new attachments at the vault root, in a configured directory, beside the current note, or in a subdirectory beneath the current folder. This vault has a more specific attachment-organization convention: read the vault's attachment-organization rules first. Embedded resources such as images normally go in an `attachments/` directory beside the note, while source materials remain according to project rules.

Practical rules:

- A filename should communicate its contents, such as `http-retry-flow.png`. Do not keep `Pasted image 20260714...png` indefinitely.
- Keep embedded resources for one topic adjacent to its note to reduce the scope affected by moves.
- When renaming or moving an attachment, check every embed at the same time.
- Do not use an absolute Windows path for a vault-internal link; it cannot work across machines.
- Do not embed real credentials, sensitive screenshots, or remote resources of unknown origin.
- Before a move, bound the scope and check whether the target exists; do not conduct unfiltered bulk cleanup.

## Responsibilities of rename and alias

| Need | Preferred mechanism | Reason |
| --- | --- | --- |
| Change a file's real identity | Rename the file and update links | filename and topic remain aligned |
| Retain an old name, abbreviation, or Chinese name | `aliases` | several names point to one file |
| Show short wording in a sentence | `[[path\|display text]]` | does not change metadata |
| Cite a fixed small passage | block ID | does not depend on full heading text |

An alias in Properties is not a second file. The deterministic form is still a real target plus display text:

~~~markdown
[[Knowledge/AI Agent Engineer/docs-EN/markdown/markdown-tutorial|The Complete Markdown Tutorial]]
~~~

## Link-audit workflow

1. **Enumerate active links:** exclude instructional examples inside code fences.
2. **Split targets:** remove `!`, display text, heading fragments, and block fragments to obtain the file path.
3. **Verify files:** determine whether the target exists and whether case and extension follow host rules.
4. **Verify fragments:** determine whether heading text or block ID exists and is unique.
5. **Check duplicates:** determine whether a short basename appears more than once in the vault.
6. **Review backlinks and Git diff:** confirm that callers changed together before and after a move.
7. **Spot-check Reading View:** confirm that embeds, PDF page references, image dimensions, and embeds inside callouts really render.

A static “file exists” result is not proof that Reading View was verified; record them separately.

## Hands-on practice

1. From this lesson, create a full-path link to the [[markdown/examples/link-and-embed-practice-target|link-practice target]].
2. Link separately to its heading “Observable result” and its `validation-gate` block.
3. Embed that block and confirm a source-file change is reflected in the embed.
4. Change the display text, then confirm that the target file was not renamed.
5. Put an intentionally wrong target in a code fence and write how you would locate the problem; do not create the missing note.

At acceptance, you should be able to identify which links are active, which are only code examples, and which checks must happen in the Obsidian UI.

## Common errors and investigation

- **Writing only `[[00-index]]`:** use a full path to avoid ambiguity from many identically named entry points.
- **Treating an alias as a file path:** use `[[real path|alias]]`.
- **A heading link fails:** validate the file first, then check heading text; use a stable block ID when necessary.
- **An embed is blank:** check `!`, extension, fragment, and host support for the format.
- **Git shows only a deletion and addition after a move:** confirm that the rename is intended and inspect every caller; do not rely on Git similarity to prove links are safe.
- **An image appears on one machine but not another:** check for an accidental absolute path or an attachment outside the shared scope.

## Self-check and mastery criteria

1. What do the two portions of `[[target|display text]]` each control?
2. What maintenance cost does each of heading links and block links have?
3. Why is an embed not a content copy?
4. Why should a Windows user still use `/` in vault paths?
5. Why cannot automatic internal-link updates replace a final audit?

- [ ] I can create full-path note, heading, and block links.
- [ ] I can embed a real note block and explain the update relationship.
- [ ] I can choose an attachment location under vault rules.
- [ ] I can distinguish file existence, link resolution, and Reading View rendering as three validations.

Previous: [[markdown/02-commonmark-gfm-and-obsidian-syntax-boundaries|CommonMark, GFM, and Obsidian syntax boundaries]].  
Next: [[markdown/04-properties-callouts-and-reusable-notes|Properties, callouts, and reusable notes]].

## References

Checked: **2026-07-14**.

- [Obsidian: Internal links](https://obsidian.md/help/links)
- [Obsidian: Aliases](https://obsidian.md/help/aliases)
- [Obsidian: Embed files](https://obsidian.md/help/embeds)
- [Obsidian: Attachments](https://obsidian.md/help/attachments)
