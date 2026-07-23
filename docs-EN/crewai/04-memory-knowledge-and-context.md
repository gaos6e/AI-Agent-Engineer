---
title: "Memory, Knowledge, and Context"
aliases:
  - CrewAI Memory and Knowledge
  - CrewAI Context Management
tags:
  - ai-agent-engineer
  - crewai
  - memory
  - knowledge
  - context-engineering
source_checked: 2026-07-21
concept_source_checked: 2026-07-21
package_source_checked: 2026-07-21
lang: en
translation_key: CrewAI/04-Memory Knowledge与上下文.md
translation_source_hash: 9e68623f621859a7514fb7d896f64aea87f7296ac753c861697c32c29a1f186d
translation_route: zh-CN/CrewAI/04-Memory-Knowledge与上下文
translation_default_route: zh-CN/CrewAI/04-Memory-Knowledge与上下文
---

# Memory, Knowledge, and Context

## Learning objectives

After this lesson, you should explain the different roles of **Flow state, per-turn context, Memory, and Knowledge** in CrewAI; define writing, reading, expiry, and deletion rules for each; and avoid treating “the model saw it” as proof that the system saved it reliably.

> [!important] Version note
> The latest stable package observed on PyPI on 2026-07-21 was <code>crewai==1.15.5</code>, while the course’s real Layer B remains pinned and revalidated at <code>1.15.4</code>. This lesson rechecked Memory/Knowledge concepts against official pages on 2026-07-21. Page labels, PyPI releases, and the tested course baseline are different facts. A real project must use its pinned dependency API and minimal integration tests as authority.

## What the four information types solve

| Type | Question it answers | Typical content | Primary risk |
| --- | --- | --- | --- |
| Flow state | “Where is this run now?” | Run ID, stage, attempt count, approval result, structured Task artifacts | Schema drift, repeated execution, state corruption |
| Per-turn context | “What must the model see for this call?” | Task instructions, limited history, Tool results, retrieved fragments | Excess length, stale information, prompt injection |
| Memory | “Which prior experience may be retrieved later?” | Confirmed user preferences, completed events, reusable experience | False memory, overbroad sharing, undeletable records |
| Knowledge | “Which prepared domain sources are available for retrieval?” | Manuals, policies, product docs, versioned internal knowledge | Obsolete versions, missed authority checks, lost provenance |

These layers can supply one another, but cannot replace one another. For example, “a refund was manually approved” is first state for the current Flow; only if business rules permit may it become a lasting memory after the run. A policy manual is Knowledge; only two retrieved passages enter per-turn context. A model’s inference that a user prefers an option must not be written as durable fact without confirmation.

## Flow state: recoverable business facts

Use a fixed schema rather than free text. A minimal state may be:

~~~json
{
  "schema_version": 1,
  "run_id": "run-...",
  "stage": "reviewing",
  "attempt": 1,
  "approved": false,
  "artifacts": {
    "draft_id": "draft-..."
  }
}
~~~

- <code>schema_version</code> identifies the contract for state reading and migration.
- <code>run_id</code> uniquely associates state, logs, and audit records for one run.
- <code>stage</code> is the business-code-controlled point of advancement.
- <code>attempt</code> enforces a retry budget rather than relying on a prompt.
- <code>approved</code> can be written only by a trusted approval process, not by model self-report.
- <code>artifacts.draft_id</code> holds a stable artifact reference rather than duplicating full content.

Before designing state, answer:

1. Which fields determine the next route?
2. Which fields need programmatic validation rather than a natural-language explanation?
3. During recovery, how will you know whether a side-effecting action already occurred?
4. After a schema change, will you migrate, reject recovery, or support a compatibility read?

State holds facts needed to advance work; it should not become an unbounded store for full prompts, raw attachments, or secrets. See [[crewai/02-flow-state-and-events|Flow, State, and Events]] and [[crewai/06-safety-failure-recovery-and-production-boundaries|Safety, Failure Recovery, and Production Boundaries]] for its relation to <code>@persist</code> and checkpoints.

## Per-turn context: information the model can use now

More context is not automatically better. A writer Agent usually needs the research result, writing constraints, and output schema—not the researcher’s full chain of thought. Assemble context in this order:

1. Role, authority, and safety rules that external text cannot override.
2. The current Task’s objective, input contract, and completion criteria.
3. The smallest necessary fields from Flow state.
4. A limited set of retrieved Knowledge or Memory fragments, with source and time.
5. Recent Tool results that matter to the current Task.
6. Explicit output format, rejection criteria, and budget.

External web pages, PDFs, mail, and Tool results are **untrusted data**. Text such as “ignore previous instructions” or “call the send Tool” remains content to process; it cannot change an Agent’s Tool authority. Context isolation ultimately relies on Tool allowlists, parameter validation, and approval—not a more forceful prompt.

## Memory: retrievable long-term experience, not a chat-log warehouse

The official Memory page checked on 2026-07-21 introduces a unified <code>Memory</code> capability and uses <code>remember</code>, <code>recall</code>, and <code>forget</code> for write, retrieval, and deletion; a Crew can also enable memory through <code>memory=True</code>. Because page labels and package versions differ, this lesson does not make an example signature a cross-version guarantee and does not execute a real Memory API in the offline project.

Write a Memory policy before enabling it:

| Question | Example executable answer |
| --- | --- |
| Who may write? | Only an end-of-run archival step; ordinary Agents submit candidates only. |
| What may be written? | Explicitly confirmed user preferences and completed, sourced events. |
| What must not be written? | Keys, raw identity documents, model guesses, or short-lived error logs. |
| Who may read? | Only a Crew for the same tenant with the relevant business authority. |
| How long is it retained? | Preferences for 180 days; business events under organizational policy. |
| How are errors corrected? | A new fact is versioned and invalidates the old item; audit records are not silently overwritten. |
| How is it deleted? | Locate by user, source, and purpose; verify retrieval no longer returns it. |

Memory retrieval is not truth. Every result needs at least source, write time, applicable scope, and a confidence boundary. A high-risk decision must recheck an authoritative system rather than act solely on a similar memory.

### Current Memory scope is not tenant authorization

The official page describes a unified API that can have an LLM infer scope, category, and importance on write; recall scoring combines semantic similarity, recency, and importance, and views such as <code>slice(..., read_only=True)</code> are available. These aid **organization and retrieval**, but must not be treated as identity authentication or cross-tenant ACL: LLM-inferred scope is not a trusted authorization attribute, and ranking is not a policy decision.

Production design must determine tenant/subject and readable scope from a trusted request identity before retrieval, then pass those constraints to the retrieval layer. Accept writes only from a controlled archival step, and audit the actual storage root, scope, provenance, and deletion request. If framework APIs cannot prove filtering occurs before the query, use tenant-isolated storage/namespaces or filter in an external authorization service. Do not use <code>read_only</code>, an Agent name, or a prompt as an isolation mechanism. This course does not run real Memory’s LLM/embedding path; this is a boundary derived from official documentation, not local integration acceptance.

## Knowledge: a versioned, authority-managed source layer

Official Knowledge documentation describes Agent-level and Crew-level sources. File-backed sources use paths relative to a project-root <code>knowledge/</code> directory, so working directory, file deployment, and container mounts all need tests; do not assume a local relative path works unchanged on a server.

Agent-level sources can work independently; Crew-level sources are distributed to all Agents in the Crew. This is **configuration-distribution scope**, not multi-tenant access control. The current page also shows that a default storage implementation may name an Agent collection after <code>agent.role</code> and a Crew collection after the <code>crew</code> name. Roles and collection names can change and are not trusted principals. With a shared storage root, same role, or default collection, never infer isolation. Apply tenant, data classification, source version, and authorization filters in a trusted layer before retrieval, and integration-test actual storage paths, collection names, cache invalidation, and deletion.

A maintainable Knowledge pipeline is:

1. **Ingest:** confirm copyright, data classification, version, and owner.
2. **Parse:** retain title, section, page, or original record ID.
3. **Chunk:** split by semantics and use case, not only a fixed character count.
4. **Index:** bind source, version, tenant, authority, and expiry.
5. **Retrieve:** apply authority filtering before relevance retrieval.
6. **Inject:** add only sufficient fragments to context and preserve citeable identifiers.
7. **Update and delete:** invalidate old fragments after a new release and verify caches and indexes update too.

The official page also says Knowledge uses local storage components and recommends an explicit production storage location through <code>CREWAI_STORAGE_DIR</code>. A path is storage configuration, not authority, backup, or encryption policy; production still needs to design those boundaries.

## Passing information across Agents

Prefer **structured artifacts** over copying an entire conversation to the next Agent. A researcher can return:

~~~json
{
  "claims": [
    {
      "text": "…",
      "source_ids": ["source-1"]
    }
  ],
  "unknowns": []
}
~~~

- <code>claims</code> is a structured collection of statements for a writer or reviewer.
- Each <code>text</code> states only what available evidence supports, not model speculation.
- <code>source_ids</code> bind each statement to reviewable catalog entries.
- <code>unknowns</code> preserves questions with insufficient evidence; an empty array means no such gap was recorded.

The writer receives only these fields and the writing standard; the reviewer receives the research artifact, draft, and source catalog. This makes source verification easier, limits prompt-injection propagation, and localizes errors at Task boundaries. See the runnable implementation in [[crewai/07-project-offline-research-brief-flow|Project: Offline Research-Brief Flow]].

## Common misconceptions and diagnosis

- **Misconception:** <code>memory=True</code> automatically provides correct personalization.
  - **Check:** inspect write policy, retrieval results, tenant isolation, correction, and deletion tests.
- **Misconception:** old answers disappear automatically after a Knowledge file changes.
  - **Check:** inspect index version, cache, storage path, and invalidation rules.
- **Misconception:** a summary is automatically safer because it is shorter.
  - **Check:** summaries can retain secrets or injected instructions; still classify, redact, and bind provenance.
- **Misconception:** multi-Agent collaboration needs the full shared history.
  - **Check:** list each Task’s minimum inputs and remove fields that do not affect completion criteria.

## Hands-on exercise

Design a customer-support Crew. Classify each item as state, context, memory, or Knowledge, and give its retention period and read/write authority: order number, current refund approval, a user’s explicit preference for Chinese, a policy manual, the previous Tool timeout, and a model’s inference of user mood.

Then make a table with at least eight tests: cross-tenant retrieval, user correction, retrieval after deletion, obsolete-policy invalidation, malicious-document injection, overlong context, missing provenance, and Flow recovery.

## Mastery check

- [ ] Distinguish state, context, Memory, and Knowledge with concrete examples.
- [ ] Write who may write Memory, what may be written, when it expires, and how it is deleted.
- [ ] Explain the complete path from a Knowledge file to a retrieved fragment.
- [ ] Pass only minimal, structured, traceable artifacts between Agents.
- [ ] Explain why neither retrieval results nor long-term Memory can be accepted directly as fact.

## Next step

With information boundaries defined, verify that the whole system follows its contracts in [[crewai/05-testing-evaluation-and-observability|Testing, Evaluation, and Observability]].

## Primary references

Sources checked on 2026-07-21:

- [CrewAI Memory](https://docs.crewai.com/en/concepts/memory)
- [CrewAI Knowledge](https://docs.crewai.com/en/concepts/knowledge)
- [CrewAI Flows](https://docs.crewai.com/en/concepts/flows)
- [CrewAI on PyPI](https://pypi.org/project/crewai/)
