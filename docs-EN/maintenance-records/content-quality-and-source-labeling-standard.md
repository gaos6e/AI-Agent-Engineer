---
title: "Content Quality and Source Labeling Standard"
aliases:
  - AI Agent Engineer content-source standard
  - Course quality-status standard
tags:
  - AI-Agent-Engineer
  - content-governance
  - provenance
content_origin: original
content_status: validated
source_checked: 2026-07-19
lang: en
translation_key: 维护记录/内容质量与来源标记规范.md
translation_source_hash: e06b22deea382477a665842796e6c77a585c90191b8393365dffae9133a5633d
translation_route: zh-CN/维护记录/内容质量与来源标记规范
translation_default_route: zh-CN/维护记录/内容质量与来源标记规范
---

# Content Quality and Source Labeling Standard

This standard lets learners and maintainers distinguish who wrote a page, what it is based on, when it was checked, and whether it may be published. It prevents original explanations, curated material, and third-party reproductions from being treated as one kind of content. It applies to new pages and existing pages that have completed a deep review. Historical pages without these fields are **unclassified**; missing fields must not be interpreted as proof that a page is original or validated.

## Source types

<code>content_origin</code> has the following finite set of values:

| Value | Meaning | Minimum requirement |
| --- | --- | --- |
| <code>original</code> | This project independently created the argument structure, explanation, exercise, or example; external sources support facts and boundaries only. | List key primary sources; record <code>source_checked</code> for dynamic facts; state the actual verification scope for examples. |
| <code>curated</code> | The page reorganizes, summarizes, or rewrites one or more identified sources and its organization materially depends on them, but it is not a near reproduction. | Identify the main sources, retrieval date, and rewriting boundary; do not present source claims as this project's independent conclusions. |
| <code>third-party</code> | The page retains third-party original text, a near translation, a mirror, attachments, or code. | Record upstream URL or commit, author or copyright holder, license, and local changes. If permission is unknown, retain it only in the private layer and generate a source stub in the public layer. |
| <code>mixed</code> | The same page genuinely contains multiple source types that cannot reasonably be separated. | Label the source type next to each section. Prefer separate pages whenever the material can be separated. |

“Original” does not mean facts need no citations, and “curated” does not permit omitting copyright or license information. Changing the wording alone does not turn a third-party reproduction into original work.

## Quality status

<code>content_status</code> describes the state of evidence, not whether an article merely “looks complete”:

| Value | Meaning | Usage rule |
| --- | --- | --- |
| <code>validated</code> | Key facts, links, and adjacent practice have been checked within the current page scope. | Retain the check date; do not extrapolate to untested environments. |
| <code>dynamic</code> | Models, SDKs, APIs, protocol extensions, pricing, laws, or product behavior change quickly. | Record the specific date or version, and separate durable principles from the product snapshot. |
| <code>needs-review</code> | Known gaps remain in sources, formulas, implementation, or currency. | Do not include it in core mastery criteria; visibly mark the parts that cannot be relied upon. |
| <code>frozen-reference</code> | Retained for historical or upstream comparison and no longer updated as recommended current practice. | The main path must offer an alternative entry point; retain upstream version, license, and reason for freezing. |

<code>content_tier</code> (core, advanced, frontier, practice, reference) answers how to learn a course. It cannot replace <code>content_origin</code> or <code>content_status</code>.

A mixed course entry point may additionally use <code>reference_layer_status</code> and <code>reference_layer_license</code> to describe a subordinate reference layer—for example, “the entry page is actively maintained, but a fixed translated layer is frozen and its license is unknown.” These fields describe only the explicitly named sublayer. They cannot replace each third-party page's own <code>content_origin</code>, <code>content_status</code>, <code>source_url</code>, and <code>license</code>, nor can they be treated as one license for the entire entry page.

## Recommended frontmatter

~~~yaml
---
title: Example page
content_origin: original
content_status: dynamic
source_checked: 2026-07-19
source_baseline: Official specifications, current SDK documentation, and local tests
execution_verified: 2026-07-19
---
~~~

Add the following for third-party material when applicable:

~~~yaml
source_url: https://example.org/upstream
source_commit: 0123456789abcdef
retrieved: 2026-07-19
license: Apache-2.0
~~~

Do not guess licenses. When redistribution evidence is absent, use <code>license: unknown</code> or explain the condition in the body, and retain the public-layer stub or exclusion policy.

Use these governance fields only as root-level, block-style, one-line <code>key: value</code> scalars in frontmatter. Do not express the same fields through flow mappings, indented or sequence mappings, YAML merges, alias keys, tags or anchors on governance keys, escaped keys, or folded explicit keys. The public build fails closed using YAML AST semantics rather than treating those forms as missing fields. A third-party <code>source_url</code> must be an absolute HTTP(S) URL with no embedded credentials. Public body content must also match a verified source or project registry, a license permitted for that project, and a local license declaration; an unregistered source always generates a stub.

## Evidence boundaries within a page

Every course that has completed a deep review must at least state:

1. Which claims are durable engineering invariants and which are product or version snapshots on a specified date.
2. Which conclusions come from official specifications, original papers, local tests, or engineering inference.
3. What the example actually ran, what it did not run, and whether it used the network, required a key, or incurred cost.
4. Whether images, tables, and Mermaid diagrams are original, redrawn, or third-party assets, and how they can be regenerated.
5. When the approach should not be used, and how failures should be verified and recovered.

When quoting third-party original text, prefer a short quotation with a direct link. A long translation or complete reproduction must enter the <code>third-party</code> layer and record its license. Recommendations synthesized from multiple sources must be explicitly described as this project's curation or recommendation, not presented as a quotation from one source.

## Deep review and status updates

Review a page in this order:

1. Read the current page, neighboring index, examples, tests, and existing sources.
2. Check key claims only against current code, official documentation or specifications, original papers, and similarly strong evidence.
3. Fix specific errors, gaps, and contradictions; do not perform mechanical repository-wide replacements.
4. Run the smallest relevant tests, link checks, and necessary rendering checks.
5. Only then update <code>source_checked</code>, <code>content_status</code>, and execution records, and describe the uncovered scope in a maintenance record.

If only wording changed or only some sources were sampled, the whole page must not be upgraded to <code>validated</code>.

## Current migration policy

- New pages must declare <code>content_origin</code> and <code>content_status</code>.
- Pages that are substantially rewritten or deeply reviewed section by section receive the fields in the same batch.
- Historical reference layers are assessed course by course; do not bulk-fill fields or infer licenses.
- Pages without the fields remain unclassified and enter the later review queue.
- Publication remains gated conservatively by the course map, project publication scripts, and <code>.website/PUBLISHING.md</code>.

## Basis for this standard

This page is an original project maintenance convention. It was developed from the current vault's publication boundary, existing source fields, and issues found in the 2026-07-18 full-repository audit; it does not reproduce a third-party standard. See the related decision record: [[maintenance-records/2026-07-18-content-audit-and-restructuring-record|2026-07-18 content audit and restructuring record]].
