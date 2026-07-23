---
title: "Context Engineering: One Guide Is Enough"
tags:
  - context-engineering
  - ai-agent
  - agentic-system
aliases:
  - Context Engineering in One Guide
  - A Panoramic Introduction to Context Engineering
content_origin: curated
content_status: dynamic
source_checked: 2026-07-21
source_url: https://zhuanlan.zhihu.com/p/1938967453951571269
source_author: Duo Huang
original_url: https://huangduo.me/2025/08/15/context-engineering/
original_published: 2025-08-15
retrieved: 2026-07-21
source_baseline:
  - Duo Huang's Zhihu article, "Context Engineering: One Guide Is Enough"
  - The original article of the same title on the author's personal site
lang: en
translation_key: 上下文工程/01-Context Engineering，一篇就够了.md
translation_source_hash: 0743e208a360111bf5d05e47a856c06ae256e5a7648211319eb30383a5afef04
translation_route: zh-CN/上下文工程/01-Context-Engineering，一篇就够了
translation_default_route: zh-CN/上下文工程/01-Context-Engineering，一篇就够了
---

# Context Engineering: One Guide Is Enough

> [!source] Source and adaptation boundary
> This page is a structured adaptation of Duo Huang's [Zhihu article](https://zhuanlan.zhihu.com/p/1938967453951571269) and [the original post on the author's site](https://huangduo.me/2025/08/15/context-engineering/), following its What–Why–How structure. It retains the core concepts, relationships among examples, four practices, and references without reproducing the source verbatim. The diagrams below are editable Mermaid diagrams redesigned from the concepts in the article; no third-party images are copied. The original post was published on 2025-08-15 under CC BY-NC-SA 4.0. Product behavior and engineering judgments change with models and tools, so verify them against the rest of this knowledge base and current official sources before applying them.

> “Most AI Agent failures are not failures of model capability; they are failures of context engineering.”

## Orientation: From one good prompt to an information-supply system

Context engineering has become important not merely because it names a new idea. As Agentic Systems move from demos into production, the engineering problem changes: a beautifully worded single prompt cannot ensure that every step of a long-running task has sufficient, relevant, trustworthy, and non-overwhelming information.

This article is organized around three questions:

- **What**: What is context engineering, and how does it relate to Prompt Engineering and RAG?
- **Why**: Why are a stronger model or more context alone still insufficient?
- **How**: How can writing, selection, compression, and isolation manage context?

Its central position is that context engineering is neither “more complicated Prompt Engineering” nor “packing as many RAG results as possible into the window.” It is an engineering discipline for dynamic systems. At every Agent step, the system must decide what the model should receive now, where to retrieve it, how to structure it, and which content should be removed or isolated.

## 1. What: Context engineering

### 1.1 Context is much larger than chat history

Here, context means all information the model can see to complete its **next reasoning or generation step**, not just historical messages. The source groups it into three categories:

| Context type | Question it answers | Typical contents |
| --- | --- | --- |
| Guiding context | What should be done, and how? | System Prompt, task instructions, few-shot examples, output schema |
| Informational context | What must be known to finish the task? | RAG evidence, short- and long-term memory, structured state, scratchpad |
| Actionable context | What can be done, and what happened after action? | Tool definitions, tool calls, tool results, execution traces |

Together, these three forms of information determine the model’s next action. [[prompt-engineering/00-index|Prompt Engineering]] primarily improves guiding context; RAG chiefly provides dynamic informational context; tools and MCP connect actionable context with part of the informational context.

~~~mermaid
flowchart LR
    G["Guiding context<br/>System Prompt · Task · Examples · Schema"] --> P["Dynamic Context Pack<br/>Relevant · Trustworthy · Timely · Actionable"]
    I["Informational context<br/>RAG · Memory · State · Scratchpad"] --> P
    A["Actionable context<br/>Tool Definitions · Calls · Results · Traces"] --> P
    P --> L["LLM next-step reasoning"]
    L --> O["Answer / decision / tool action"]
    classDef guiding fill:#dbeafe,stroke:#2563eb,color:#172033,stroke-width:2px
    classDef info fill:#dcfce7,stroke:#16a34a,color:#172033,stroke-width:2px
    classDef action fill:#fef3c7,stroke:#d97706,color:#172033,stroke-width:2px
    classDef core fill:#ede9fe,stroke:#7c3aed,color:#172033,stroke-width:3px
    classDef output fill:#fce7f3,stroke:#db2777,color:#172033,stroke-width:2px
    class G guiding
    class I info
    class A action
    class P,L core
    class O output
~~~

*Figure 1: Three forms of context flow into a dynamic Context Pack and drive the next reasoning step and action (Mermaid redraw).*

### 1.2 Context engineering is a dynamic assembly mechanism

Context engineering can be understood as **designing, building, and maintaining a dynamic system that assembles an appropriate combination of context for the next model call at every step of an Agent task.** “Appropriate” includes relevance, trustworthiness, freshness, permission, structure, token budget, and the current task stage.

A useful analogy treats the LLM as a CPU and the context window as capacity-limited RAM. Context engineering is the memory manager: it does not try to fill the window, but decides what should be loaded, retained, swapped out, compressed, or raised in priority. The goal is not “more,” but a sufficiently clear signal for the next decision.

~~~mermaid
flowchart LR
    S["External information sources<br/>Documents · Memory · State · Tools"] --> M["Context manager<br/>Write · Select · Compress · Isolate"]
    M --> R["Context window<br/>RAM: finite capacity"]
    R <--> C["LLM<br/>CPU: reasoning and generation"]
    C --> N["Next task step"]
    N -. "New state and results" .-> M
    classDef source fill:#f1f5f9,stroke:#64748b,color:#172033,stroke-width:2px
    classDef manager fill:#ede9fe,stroke:#7c3aed,color:#172033,stroke-width:3px
    classDef memory fill:#dbeafe,stroke:#2563eb,color:#172033,stroke-width:2px
    classDef cpu fill:#fef3c7,stroke:#d97706,color:#172033,stroke-width:3px
    classDef next fill:#dcfce7,stroke:#16a34a,color:#172033,stroke-width:2px
    class S source
    class M manager
    class R memory
    class C cpu
    class N next
~~~

*Figure 2: The LLM-as-OS analogy—context engineering schedules and manages a finite window (Mermaid redraw).*

### 1.3 Its relationship to Prompt Engineering and RAG

These are not competing replacements; they are components at different levels:

- **Prompt Engineering** designs instructions, roles, examples, and output contracts, usually for one interaction or a class of interactions.
- **RAG** retrieves evidence from external knowledge sources and is an important way to construct informational context.
- **Context Engineering** owns the entire information-supply system: what to retrieve, when to retrieve it, how to combine it with instructions and state, how to control the budget, and what fallback path to use when retrieval fails.

Prompt Engineering can therefore be viewed as a subset of context engineering, while RAG is one key technology for dynamically selecting information. In a mature system, a particular step may not call RAG at all; it may use memory, files, databases, search tools, or deterministic rules instead.

## 2. Why context engineering is needed

### 2.1 Separate model-capability problems from context problems first

When a result is disappointing, begin diagnosis in two directions:

1. **Insufficient model capability**: Even with complete, clear, and trustworthy input, the model cannot finish the task.
2. **Context-supply failure**: The model lacks key facts, rules, state, permissions, or available tools and can only guess.

Where base-model capability has already crossed a usable threshold, many failures are closer to the second category. Changing models directly can hide the problem, but it cannot fix bad retrieval, stale memory, missing tool results, or incomplete state propagation.

~~~mermaid
flowchart LR
    A["Output falls short"] --> B{"Is the context complete, relevant, and trustworthy?"}
    B -- "No" --> C["Context-supply failure"]
    C --> C1["Add facts / state / rules / tools"]
    C1 --> T["Evaluate again"]
    B -- "Yes" --> D{"Does the task exceed model capability?"}
    D -- "Yes" --> E["Upgrade model / decompose task / specialize training"]
    D -- "No" --> F["Check prompt, decoding, and evaluation design"]
    E --> T
    F --> T
    classDef start fill:#fce7f3,stroke:#db2777,color:#172033,stroke-width:2px
    classDef decision fill:#fef3c7,stroke:#d97706,color:#172033,stroke-width:3px
    classDef context fill:#dbeafe,stroke:#2563eb,color:#172033,stroke-width:2px
    classDef model fill:#ede9fe,stroke:#7c3aed,color:#172033,stroke-width:2px
    classDef test fill:#dcfce7,stroke:#16a34a,color:#172033,stroke-width:2px
    class A start
    class B,D decision
    class C,C1 context
    class E,F model
    class T test
~~~

*Figure 3: When output is wrong, investigate context supply before deciding that the model has reached a capability boundary (Mermaid redraw).*

### 2.2 Example one: Missing context prevents an Agent from advancing a task

Suppose an assistant receives a short email asking, “Can we meet tomorrow?” With only the email body, it can at most ask for a time. If the system can also access the calendar, the contact relationship, the past communication style, and the ability to create an invitation, it can see that tomorrow is full, propose an alternative time, and create a tentative invite.

The difference between the two responses need not come from model intelligence. It comes from the context assembled before the call:

- Calendar data provides available times.
- Contact information determines priority.
- Email history determines tone.
- Tool definitions provide the ability to take the next action.

This illustrates that the gap between answering a sentence and genuinely moving work forward is often filled by the context system.

~~~mermaid
flowchart LR
    U["Email<br/>Could we get together tomorrow?"]
    subgraph Poor["Sparse context"]
        P1["Only the email body is visible"] --> P2["Mechanically asks for a time"]
    end
    subgraph Rich["Sufficient context"]
        C1["Calendar<br/>Tomorrow is full"] --> B["Dynamic assembly"]
        C2["Contact<br/>Important partner"] --> B
        C3["Email history<br/>Informal tone"] --> B
        C4["Tool definition<br/>Send invitation"] --> B
        B --> R["Propose Thursday<br/>and create a tentative invite"]
    end
    U --> P1
    U --> C1
    U --> C2
    U --> C3
    U --> C4
    classDef input fill:#f1f5f9,stroke:#64748b,color:#172033,stroke-width:2px
    classDef poor fill:#fee2e2,stroke:#dc2626,color:#172033,stroke-width:2px
    classDef rich fill:#dcfce7,stroke:#16a34a,color:#172033,stroke-width:2px
    classDef build fill:#ede9fe,stroke:#7c3aed,color:#172033,stroke-width:3px
    class U input
    class P1,P2 poor
    class C1,C2,C3,C4,R rich
    class B build
~~~

*Figure 4: The same email produces different action capacity under sparse and sufficient context (Mermaid redraw).*

### 2.3 Example two: Too much context also fails

The opposite extreme is to keep accumulating everything. Imagine a multi-day coding task spanning several files: on every turn, the system includes every user instruction, file read, compiler error, failed retry, and tool result. At first this may seem to prevent forgetting, but it eventually creates a failure cascade:

1. Resolved errors and old paths continue to distract the current step, reducing the signal-to-noise ratio.
2. Input tokens grow linearly with the history, increasing cost and latency.
3. The context eventually overflows, is hard-truncated, or triggers an API failure.
4. When old conclusions coexist with new state, the model is more likely to choose the wrong basis.

Context is therefore a finite resource that must be managed actively. Both scarcity and excess can damage a task; pursuing a larger window alone cannot replace management.

~~~mermaid
flowchart LR
    E["Continuous events<br/>Instructions · files · errors · tool results"]
    subgraph Raw["Naive accumulation"]
        H["The full history keeps growing"] --> D["Interference intensifies"]
        D --> C["Cost and latency rise"]
        C --> O["Overflow / truncation / failure"]
    end
    subgraph Managed["Active management"]
        W["Write stage state"] --> S["Select currently relevant information"]
        S --> K["Compress completed work"]
        K --> P["Compact Context Pack"]
        P --> R["Advance the next step reliably"]
    end
    E --> H
    E --> W
    classDef event fill:#f1f5f9,stroke:#64748b,color:#172033,stroke-width:2px
    classDef bad fill:#fee2e2,stroke:#dc2626,color:#172033,stroke-width:2px
    classDef good fill:#dcfce7,stroke:#16a34a,color:#172033,stroke-width:2px
    classDef pack fill:#ede9fe,stroke:#7c3aed,color:#172033,stroke-width:3px
    class E event
    class H,D,C,O bad
    class W,S,K,R good
    class P pack
~~~

*Figure 5: Unlimited accumulation leads to interference, cost, and overflow; active management preserves high-value working state (Mermaid redraw).*

## 3. How: Failure patterns and four practices

### 3.1 Four forms of context degradation

Beyond missing information caused by RAG retrieval failures, long-running Agents face four common forms of degradation:

| Failure mode | Meaning | Typical consequence |
| --- | --- | --- |
| Context poisoning | Hallucinations, wrong conclusions, or untrustworthy material enter later context | Errors are repeatedly cited and spread |
| Context distraction | A large volume of historical detail hides the signal for the current task | The model drifts from the current goal or ignores capabilities it already has |
| Context confusion | Redundant or irrelevant information is mixed with the task | The system chooses the wrong tool, evidence, or execution path |
| Context clash | New and old state, different sources, or earlier wrong answers contradict one another | Output becomes unstable and it is hard to know what to trust |

These patterns often occur together. For a more systematic testing method, see [[context-engineering/07-long-context-failure-modes-and-evaluation|Long-Context Failure Modes and Evaluation]].

~~~mermaid
flowchart TB
    C["Long-running Agent context"]
    P["Context poisoning<br/>Wrong conclusions enter later state"]
    D["Context distraction<br/>Old detail hides the current signal"]
    F["Context confusion<br/>Redundancy causes wrong selection"]
    X["Context clash<br/>New and old facts conflict"]
    C --> P
    C --> D
    C --> F
    C --> X
    P -. "Error propagation" .-> X
    D -. "Signal dilution" .-> F
    classDef core fill:#ede9fe,stroke:#7c3aed,color:#172033,stroke-width:3px
    classDef poison fill:#fee2e2,stroke:#dc2626,color:#172033,stroke-width:2px
    classDef distract fill:#fef3c7,stroke:#d97706,color:#172033,stroke-width:2px
    classDef confuse fill:#dbeafe,stroke:#2563eb,color:#172033,stroke-width:2px
    classDef clash fill:#fce7f3,stroke:#db2777,color:#172033,stroke-width:2px
    class C core
    class P poison
    class D distract
    class F confuse
    class X clash
~~~

*Figure 6: Poisoning, distraction, confusion, and clash can reinforce one another (Mermaid redraw).*

### 3.2 Write

Writing saves valuable information from the current window outside the window so it can be retrieved when needed later:

- **In-session writing**: Save plans, stage results, temporary data, and open questions in a scratchpad or working file; discard them when the task ends.
- **Persistent writing**: Store facts, user preferences, and stable conclusions that remain valuable across sessions in memory, a database, a vector store, or a knowledge graph.

The key is not to save every trace. Define the write conditions, structure, provenance, validity period, and update method. Writing sub-process results to a file can also reduce information loss from repeated verbal handoffs, but file content must still pass trust, permission, and freshness checks when reloaded.

### 3.3 Select

Selection extracts the parts most relevant to the current subtask from all available information sources before each model call. Common approaches include:

- **Deterministic selection**: Load project instructions, policy files, or current state according to predefined rules. It is predictable and easy to test.
- **Model-driven selection**: Let a model semantically filter a large set of tools, memories, or candidate materials. It is flexible but needs defenses against wrong selection.
- **Retrieval-based selection**: Use keywords, vector similarity, hybrid retrieval, or reranking to obtain candidate evidence from a knowledge base, memory, or working files.

Selection must consider more than relevance. It must also handle source trustworthiness, freshness, permissions, deduplication, and token budget. For a deterministic implementation, see [[context-engineering/08-context-pack-project-and-self-test|Context Pack Project and Self-Test]].

### 3.4 Compress

Compression preserves the core signal in fewer tokens before information enters the window. It can extract key fields, produce structured summaries or stage summaries, deduplicate content, trim tool output, or perform compaction near the context limit.

Compression inevitably makes trade-offs: a summary may omit a constraint, hard truncation may lose context, and automatic compaction may misjudge what matters most. Retain traceable source material, state the coverage of each summary, and use regression tests to check whether commitments, errors, open questions, citations, and state were lost. See [[context-engineering/06-trimming-summarization-compression-and-caching|Trimming, Summarization, Compression, and Caching]].

~~~mermaid
flowchart TB
    subgraph R1["Information persistence and selection"]
        direction LR
        S["Raw information flow<br/>Conversation · documents · tools · state"] --> W["Write<br/>Save stage state"]
        W --> L["External storage<br/>Scratchpad · memory · files"]
        L --> E["Select<br/>Rules · model · retrieval"]
    end
    subgraph R2["Information density and execution boundary"]
        direction LR
        C["Compress<br/>Summaries · deduplication · trimming"] --> I["Isolate<br/>Subtasks · tools · sandboxes"]
        I --> P["Context Pack<br/>Provenance · permission · freshness · budget"]
        P --> M["LLM next decision"]
    end
    E --> C
    M -. "Results and new state" .-> W
    classDef source fill:#f1f5f9,stroke:#64748b,color:#172033,stroke-width:2px
    classDef write fill:#dbeafe,stroke:#2563eb,color:#172033,stroke-width:2px
    classDef select fill:#dcfce7,stroke:#16a34a,color:#172033,stroke-width:2px
    classDef compress fill:#fef3c7,stroke:#d97706,color:#172033,stroke-width:2px
    classDef isolate fill:#fce7f3,stroke:#db2777,color:#172033,stroke-width:2px
    classDef pack fill:#ede9fe,stroke:#7c3aed,color:#172033,stroke-width:3px
    class S source
    class W,L write
    class E select
    class C compress
    class I isolate
    class P,M pack
~~~

*Figure 7: Write, Select, Compress, and Isolate jointly produce a verifiable Context Pack (Mermaid redraw).*

### 3.5 Isolate

Isolation establishes boundaries in the information flow at the architecture level. A sub-process reads and processes substantial raw material in its own context, then gives the main process only selected and compressed conclusions. Typical forms include subagents, tool-call boundaries, sandboxes, task-specific workspaces, and separate retrieval–summarization chains.

Isolation can reduce the lead Agent’s cognitive load and limit contamination and conflict between tasks, but it does not guarantee correctness. A sub-process may compress away critical evidence or produce conclusions that conflict with another one. Handoffs should include provenance, confidence boundaries, open questions, and verifiable artifacts.

Compression and isolation can be distinguished as follows:

- **Compression** mainly acts on a single information flow to raise its internal information density.
- **Isolation** mainly manages boundaries among multiple information flows and achieves broad compression by passing on only the key results.

~~~mermaid
flowchart TB
    L["Lead Agent<br/>Maintains the global goal and final decision"]
    subgraph A["Isolated context A"]
        S1["Research Agent"] --> D1["Documents and search results"]
        D1 --> R1["Summary + provenance + open questions"]
    end
    subgraph B["Isolated context B"]
        S2["Coding Agent"] --> D2["Code · tests · logs"]
        D2 --> R2["Patch + test evidence + risks"]
    end
    subgraph C["Isolated context C"]
        S3["Review Agent"] --> D3["Standards · constraints · diffs"]
        D3 --> R3["Review conclusion + evidence locations"]
    end
    L --> S1
    L --> S2
    L --> S3
    R1 --> L
    R2 --> L
    R3 --> L
    classDef lead fill:#ede9fe,stroke:#7c3aed,color:#172033,stroke-width:3px
    classDef agent fill:#dbeafe,stroke:#2563eb,color:#172033,stroke-width:2px
    classDef data fill:#f1f5f9,stroke:#64748b,color:#172033,stroke-width:2px
    classDef result fill:#dcfce7,stroke:#16a34a,color:#172033,stroke-width:2px
    class L lead
    class S1,S2,S3 agent
    class D1,D2,D3 data
    class R1,R2,R3 result
~~~

*Figure 8: Sub-processes work in isolated contexts and return only evidence-bearing, compressed conclusions to the Lead Agent (Mermaid redraw).*

### 3.6 Where Prompt Engineering fits in the four-step framework

“Write, Select, Compress, Isolate” primarily describes the flow of dynamic information. A System Prompt, task contract, and output schema are more like relatively stable core configuration. They still belong to context, but are normally loaded deterministically through selection at runtime and combined with dynamic evidence, state, and tool results. The four-step framework therefore does not exclude Prompt Engineering; it situates it in a larger context lifecycle.

## 4. Conclusion: Context engineering is systems engineering for Agents

Context engineering shifts the center of work from finding a single “perfect prompt” to designing a system that reliably supplies information for every model decision. That system must handle content sources, trust boundaries, permissions, freshness, state, tools, budget, and degradation tests together.

MCP plays an infrastructure role here. It exposes external tools and data sources to an Agent through standard interfaces, helping a system construct actionable context and part of its informational context. MCP itself does not decide what belongs in the window, and it does not replace selection, compression, or validation.

Whether a system uses prompts, RAG, memory, MCP, or multiple Agents, the goal remains the same: **before the model makes its next decision, let it see context that is sufficient, relevant, trustworthy, and actionable.**

## References retained from the source article

The following list preserves the source article’s reference paths. Their current content was not individually re-verified in this adaptation:

- [Tobi Lütke: post about Context Engineering](https://x.com/tobi/status/1935533422589399127)
- [Andrej Karpathy: post about Context Engineering](https://x.com/karpathy/status/1937902205765607626)
- [Context Engineering 101 cheat sheet](https://x.com/lenadroid/status/1943685060785524824)
- [Philipp Schmid: The New Skill in AI is Not Prompting, It's Context Engineering](https://www.philschmid.de/context-engineering)
- [LlamaIndex: Context Engineering - What it is, and techniques to consider](https://www.llamaindex.ai/blog/context-engineering-what-it-is-and-techniques-to-consider)
- [LangChain: The rise of “context engineering”](https://blog.langchain.com/the-rise-of-context-engineering/)
- [Andrej Karpathy: Software Is Changing (Again)](https://www.youtube.com/watch?v=LCEmiRjPEtQ&t=620s)
- [12-factor-agents: Own your context window](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-03-own-your-context-window.md)
- [Lance Martin: Context Engineering for Agents](https://rlancemartin.github.io/2025/06/23/context_engineering/)
- [Cognition: Don’t Build Multi-Agents](https://cognition.ai/blog/dont-build-multi-agents#principles-of-context-engineering)
- [Drew Breunig: How Long Contexts Fail](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html)

## Continue in this knowledge base

- [[context-engineering/03-selection-relevance-and-provenance|Selection, Relevance, and Provenance]]
- [[context-engineering/05-conversation-history-state-and-memory|Conversation History, State, and Memory]]
- [[context-engineering/06-trimming-summarization-compression-and-caching|Trimming, Summarization, Compression, and Caching]]
- [[context-engineering/07-long-context-failure-modes-and-evaluation|Long-Context Failure Modes and Evaluation]]
- [[context-engineering/08-context-pack-project-and-self-test|Context Pack Project and Self-Test]]
