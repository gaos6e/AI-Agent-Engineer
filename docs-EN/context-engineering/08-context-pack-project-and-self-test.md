---
title: "Context Pack Project and Self-Test"
tags:
  - context-engineering
  - project
  - self-test
aliases:
  - Context Engineering Project
source_checked: 2026-07-21
execution_verified: 2026-07-21
content_origin: original
content_status: validated
source_baseline:
  - Python 3.11 standard-library documentation
  - JSON Schema 2020-12 documentation
  - OpenAI and Anthropic context-management documentation
lang: en
translation_key: 上下文工程/08-Context Pack项目与自测.md
translation_source_hash: 896aa1707d73d25039769df4d721bea11b6e16bf3d93c17cf75596a479b94708
translation_route: zh-CN/上下文工程/08-Context-Pack项目与自测
translation_default_route: zh-CN/上下文工程/08-Context-Pack项目与自测
---

# Context Pack Project and Self-Test

## Project objective and boundary

Implement a deterministic context-pack builder. It performs strict JSON validation, permission, trust, date, explicit deduplication, and budget gates in that order, then outputs chunks and provenance in policy → state → evidence → current-input order. Every excluded chunk has a machine-readable reason.

The project does not call a tokenizer or model API. The fixture’s estimated_tokens values are externally supplied teaching data: they can validate the selection algorithm, but cannot prove real token counts, cost, or model quality. A production system must calibrate with the target model’s counting capability and response usage.

> [!important] Trusted control-plane boundary
> To support offline teaching, the fixture puts request policy and candidate chunks in one JSON file. Production systems must separate their trust sources: granted_permissions comes from an authenticated subject and authorization service; allowed_trust comes from application policy; and a chunk’s trust, required_permission, required, and dedupe_key are assigned by a controlled ingestion process. Untrusted body text must not raise its own trust, grant permission, declare itself required, or determine a deduplication relationship. This selector validates the consistency of the declared values; it does not authenticate them.

## Project files

| File | Responsibility |
| --- | --- |
| [[context-engineering/examples/context_budget.py\|context_budget.py]] | Strictly loads the fixture, performs five classes of gates, builds the deterministic context pack, and supplies CLI exit codes |
| [[context-engineering/examples/chunks.json\|chunks.json]] | Eleven versioned chunks carrying provenance, version, permission, trust, effective period, priority, and budget |
| [[context-engineering/examples/context-pack.schema.json\|context-pack.schema.json]] | JSON Schema 2020-12 contract for the output pack |
| [[context-engineering/examples/test_context_budget.py\|test_context_budget.py]] | Eighteen unit tests covering invalid input, failure-closed behavior, deduplication boundaries, determinism, schema, and CLI |

## Runtime environment

The script uses only the Python standard library and requires no network access, third-party dependency, or API key. In Windows 11 PowerShell 7, run the following blocks in order from the repository root, which contains both docs-EN and .website. The final block returns to that root after creating an inspection pack:

~~~powershell
Push-Location -LiteralPath 'docs-EN\context-engineering'  # Enter the course directory temporarily so relative example paths work.
py -3.11 --version  # Confirm the interpreter version selected by Python Launcher.
py -3.11 -m unittest discover -s .\examples -p 'test_context_budget.py' -v  # Run all context-pack tests in normal mode.
py -3.11 -O -m unittest discover -s .\examples -p 'test_context_budget.py' -v  # Repeat with -O to prove fail-closed gates do not depend on assert.
~~~

For a typical project, study virtual environments and pip in [[python-fundamentals/00-index|Python Fundamentals]] first. This project has no dependencies, so it uses the installed Python directly to avoid creating a virtual environment in the vault. If you need to practice isolation, create the virtual environment outside the vault.

## Step-by-step experiment

### 1. Read the input contract

Open [[context-engineering/examples/chunks.json|chunks.json]] first. The top-level request supplies the observation date, granted permissions, allowed trust labels, and pack budget. Each chunk includes:

- A stable id, source_uri, and source_version.
- effective_from and an exclusive expires_on.
- required_permission and trust.
- A controlled dedupe_key, priority, required flag, and estimated_tokens value.
- The section and content that will ultimately enter context.

Apply dedupe_key only to chunks that the business has confirmed are interchangeable. Conflicting sources must not share a key merely to save tokens, or conflict will be mistaken for duplication. Even if business content is equivalent, all members of the same group must have the same section, required_permission, and trust; otherwise priority ordering could allow a lower-permission or lower-trust chunk to replace another safety category, and the loader rejects the fixture directly.

### 2. Build the default pack

~~~powershell
py -3.11 .\examples\context_budget.py  # Build one deterministic context pack with the default teaching fixture.
$LASTEXITCODE  # Show the CLI exit code; 0 means the build and every gate passed.
~~~

The current fixture has a budget of 170 **estimated tokens**, uses 162, and leaves 8. Selection order is policy, task-state, current-refund-policy, refund-faq, current-input. The exit code should be 0.

Each of the six exclusion reasons appears once: insufficient permission, disallowed trust, not yet effective, expired, explicit duplicate, and insufficient budget. The selector applies security and validity gates before deduplication and budget allocation; low-priority content cannot crowd out required policy or current state.

### 3. Create an inspectable JSON pack

~~~powershell
$pack = Join-Path $env:TEMP "context-pack.json"  # Use the system temporary directory so no vault artifact is created.
py -3.11 .\examples\context_budget.py --json-pack $pack  # Write selected and excluded results to an inspectable JSON pack.
Get-Content -LiteralPath $pack -Raw -Encoding utf8  # Read the complete pack as UTF-8 and inspect budget and provenance fields.
Pop-Location  # Return to the repository root used before the experiment.
~~~

The output includes the version, observation date, budget, estimated usage and remainder, selected chunks with provenance, and exclusion records without bodies. The teaching pack includes sample content so you can inspect the final context. Production logs must not retain real bodies by default; design that separately around privacy, permission, and retention.

### 4. Prove that required items fail closed

The test suite creates four required-item failures in temporary directories: missing permission, a disallowed trust label, not yet effective, and expired. It also lowers the budget beneath the total for required items. The builder must return an error rather than silently drop the item; the CLI returns 2 without printing a traceback. The canonical fixture is not modified.

### 5. Check determinism

One test shuffles the eleven input chunks with a fixed random seed and compares the complete pack. Every field must be identical. Determinism makes version differences auditable, but it does not make this greedy priority strategy optimal for every business case. Task evaluation must still validate coverage, diversity, and combinatorial value.

## Local verification record

On Python 3.11, completed on 2026-07-21:

- py -3.11 -m py_compile passed for the script and tests.
- Normal mode: all eighteen tests passed with warnings treated as errors.
- Python -O mode: the same eighteen tests passed; critical gates do not depend on bare assert statements that optimization can remove.
- CLI: the default fixture selected five chunks and excluded six, with estimated usage 162/170.
- Normal and -O CLI text and JSON packs were byte-for-byte identical.

These results cover only the offline contract and selector. They do not call a provider tokenizer or model API, and they do not verify real answer quality or the Obsidian reading view.

## Extension tasks

1. Add a counting adapter matching the target model while retaining the offline estimated_tokens tests; compare pre-send counts with response usage.
2. Add constraints for at least one evidence item per subquestion and source diversity, then demonstrate the limits of simple greedy priority.
3. Retain conflicting sources as independent groups and require the answer to cite both old and new versions and explain the effective-date rule.
4. Add state invariants before and after summarization or compaction: monetary values, dates, refusals, open questions, and source IDs must not be lost.
5. After studying [[evaluation-framework/00-index|Evaluation Framework]], run a matrix of position, interference, multiple evidence, injection, latency, and cost across pack strategies.

## Self-test questions

1. Why can character counts and estimated_tokens not serve as evidence of real tokens or cost?
2. Why must permission, trust, and date gates precede relevance ranking and budget selection?
3. How can misuse of dedupe_key silently delete a source conflict?
4. Why does a cache hit neither enlarge the window nor prove the context pack is correct?
5. When are failure, task splitting, and controlled compression each appropriate for required context that exceeds the limit?
6. Why does deterministic selection still not equal optimal task quality?

## Mastery check

- [ ] I can run normal and -O tests and explain the failure modes covered by the eighteen tests.
- [ ] I can trace every selected chunk to its source, version, validity period, trust, and permission.
- [ ] I can make a required item’s permission or budget failure return a nonzero status instead of continuing silently.
- [ ] I do not present fixture estimates as real tokens or record production bodies by default.
- [ ] I can design tests for conflict, deduplication, coverage, and information fidelity after compression.
- [ ] I can explain what evidence still separates offline pack validation from real-model long-context evaluation.

## Key references

- [Python 3.11: json](https://docs.python.org/3.11/library/json.html) (accessed 2026-07-21)
- [Python 3.11: unittest](https://docs.python.org/3.11/library/unittest.html) (accessed 2026-07-21)
- [JSON Schema: Getting started](https://json-schema.org/learn/getting-started-step-by-step) (accessed 2026-07-21)
- [OpenAI: Compaction](https://developers.openai.com/api/docs/guides/compaction) (accessed 2026-07-21)
- [Anthropic: Context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows) (accessed 2026-07-21)

## Return to the index

Return to [[context-engineering/00-index|Context Engineering Learning Path]], or continue to [[llm-api-integration/00-index|LLM API Integration]].
