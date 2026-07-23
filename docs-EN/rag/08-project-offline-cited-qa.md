---
title: "Project: Offline Cited Q&A"
tags:
  - ai-agent-engineer
  - rag
  - project
aliases:
  - Offline Cited QA Project
  - Offline RAG Project
source_checked: 2026-07-22
execution_verified: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: RAG/08-项目-离线可引用问答.md
translation_source_hash: 919100b52f39f7724d39aec9b0ab65f6e0374a865d9592f397057b7bdb316822
translation_route: zh-CN/RAG/08-项目-离线可引用问答
translation_default_route: zh-CN/RAG/08-项目-离线可引用问答
---

# Project: Offline Cited Q&A

## Project goal

Run a fully offline, traceable teaching pipeline that supports fault injection:

```text
Stable query fixture → trusted execution context → tenant/ACL/half-open-validity filters → character recall
                     → topic-rule reranking → canonical deduplication and budget
                     → extractive claims → citation/revision validation → public response
                                                          ↘ protected audit trace → layered evaluation artifact
```

The project addresses “how each RAG layer's contract is verified,” not “how to perform high-quality semantic search with character rules.” It intentionally uses no embeddings, ANN, LLM, network, or API key.

## Project files

| File | Contents |
| --- | --- |
| [[rag/examples/rag-fixture.json\|rag-fixture.json]] | 10 versioned documents, 8 queries, risk slices, and an evaluation policy. |
| [[rag/examples/offline_cited_qa.py\|offline_cited_qa.py]] | Strict JSON, dual public/audit schemas, an evidence pipeline, an evaluation report, and a CLI. |
| [[rag/examples/test_offline_cited_qa.py\|test_offline_cited_qa.py]] | 73 tests for schema, UTF-8/numeric resource limits, noninterference, authorization, audit binding, failures, grounding, evaluation, and CLI behavior. |

## Environment

- Windows 11 and PowerShell 7.
- Python 3.11 is verified; the code uses only the standard library.
- No dependency installation or key is needed.
- Use `-B` and `PYTHONDONTWRITEBYTECODE` to avoid creating `__pycache__`.

If you need an isolated Python environment, put a virtual environment outside the vault, for example `$env:TEMP\rag-lab-venv`; do not put `.venv`, caches, or real credentials in the knowledge base.

## Step 1: Run every case

Run from the project root (which contains `docs-EN/` and `.website/`):

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Do not write __pycache__; keep the local teaching project clean.
$env:PYTHONIOENCODING = 'utf-8'  # Force terminal JSON to UTF-8.
$script = '.\docs-EN\rag\examples\offline_cited_qa.py'  # Store the main script path for reuse in later stages.
$fixture = '.\docs-EN\rag\examples\rag-fixture.json'  # Store the teaching fixture path that is strictly loaded and hash-bound.

python -B -W error $script --fixture $fixture demo  # Run every built-in scenario once and observe business states and citation boundaries.
```

Expected business states:

| Query ID | Scenario | State |
| --- | --- | --- |
| `Q-refund` | Current refund policy; the old version has expired. | `answered` |
| `Q-duplicate` | Duplicate-charge handling. | `answered` |
| `Q-phone-guest` | An ordinary user asks for an internal phone number. | `insufficient_evidence`, without disclosing `S3`. |
| `Q-phone-oncall` | Caller has the oncall group permission. | `answered` |
| `Q-conflict` | Two current accommodation standards conflict. | `conflict` |
| `Q-mars` | The corpus has no answer. | `insufficient_evidence` |
| `Q-untrusted-content` | Authorized external content containing a fake instruction. | `answered`; control fields do not change with the body text. |
| `Q-order-live` | Live order status. | `tool_required` |

## Step 2: Compare public response and protected audit trace

Public command:

```powershell
python -B -W error $script --fixture $fixture ask --query-id Q-refund  # Output the public answered projection for the refund policy.
```

The teaching envelope from the public CLI contains only `mode` and public `result`. The latter has only stable state, an answer rendered from claims, authorized citations, and a teaching `trace_id`; it excludes candidates, filter counts, internal versions, and the caller-supplied fixture's local path. This example computes the ID deterministically from pipeline revision and query ID only for test recomputation. It is not a random opaque production ID and cannot serve as identity or authorization. For local teaching diagnosis, explicitly run:

```powershell
python -B -W error $script --fixture $fixture inspect --query-id Q-refund --operator-view  # Explicitly request the protected audit trace for the same case in local teaching.
```

`--operator-view` only prevents mistakenly treating internal structure as a public response; it does not provide real authentication. Inspect the protected trace:

1. This project's fixed enum is `visibility=privileged_audit`, called “protected audit” here; it is a different schema from Lesson 9's `protected_audit`.
2. The trace binds `authorization_revision`.
3. `filter_summary`, candidates, and dropped reasons exist only in the internal trace.
4. `retrieved`, `reranked`, and `selected` are retained separately.
5. The filter summary, rank/score, selected/context characters, stage transitions, and degraded/fallback state are recomputed from trusted inputs.
6. `dropped` shows canonical-duplicate or budget reasons.
7. `citations` record document, fact, and source revision; every claim citation must support that claim verbatim.
8. `trace_id` and the public response are recomputed from trusted runtime input and each stage's result; they cannot be arbitrarily replaced in an audit envelope.
9. The runtime validator does not read offline `expected_*` oracles.

Character/bigram scores rank only within this query; they are not probabilities and cannot be compared to real vector scores.

## Step 3: Compare authorization

```powershell
python -B $script --fixture $fixture ask --query-id Q-phone-guest  # Run as ordinary public group; identical text must not disclose the internal phone number.
python -B $script --fixture $fixture ask --query-id Q-phone-oncall  # Run with the trusted fixture identity that contains oncall; the authorized fact may be returned.
```

The two queries have the same text but different `subject_groups` parsed by the trusted identity layer. Public access explicitly includes the `public` group, not an empty group or magic bypass. Observe that the ordinary user's public result has:

- no internal phone number;
- no `S3`;
- no private title;
- no filter reason or count.

Internal `inspect` can distinguish reasons; a public response remains byte-identical when a new unauthorized document is added, preventing private-resource probing through counts.

## Step 4: Observe conflict and tool routing

```powershell
python -B $script --fixture $fixture ask --query-id Q-conflict  # View conflict state when effective sources contradict each other.
python -B $script --fixture $fixture ask --query-id Q-order-live  # View a live question routed to tool_required rather than disguised as a knowledge answer.
```

`Q-conflict` keeps two contradictory effective facts; it neither averages them nor chooses one arbitrarily by authority. `Q-order-live` short-circuits before retrieval because a knowledge snapshot cannot answer current order status.

## Step 5: Simulate dependency failures

```powershell
python -B $script --fixture $fixture inspect --query-id Q-refund --failure retrieval_error --operator-view  # Inject retrieval failure; observe dependency_unavailable and the audit reason.
python -B $script --fixture $fixture inspect --query-id Q-refund --failure reranker_error --operator-view  # Inject reranker failure; observe reuse of the same safe candidate set.
python -B $script --fixture $fixture inspect --query-id Q-refund --failure generation_error --operator-view  # Inject generation failure; observe refusal to emit an unvalidated claim.
```

| Failure | Behavior |
| --- | --- |
| retrieval_error | Stop and return `dependency_unavailable`. |
| reranker_error | Keep retrieval order on the same safe candidate set and mark degraded. |
| generation_error | Keep the retrieval trace but do not emit an unvalidated claim. |

## Step 6: Run regression in four interpreter modes

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Do not leave bytecode caches after four test runs.
$env:PYTHONIOENCODING = 'utf-8'  # Keep failure messages and JSON assertions in UTF-8.
$tests = '.\docs-EN\rag\examples'  # Store the unittest-discovery test directory.

python -B -m unittest discover -s $tests -p 'test_offline_cited_qa.py' -v  # Run all 73 offline cited-Q&A tests verbosely in normal mode.
python -O -B -m unittest discover -s $tests -p 'test_offline_cited_qa.py'  # Run again optimized; verify no critical check relies on bare assert.
python -B -W error -m unittest discover -s $tests -p 'test_offline_cited_qa.py'  # Run with warnings strict so runtime warnings are not ignored.
python -O -B -W error -m unittest discover -s $tests -p 'test_offline_cited_qa.py'  # Cover optimized + strict-warning mode together.
```

`-O` removes Python bare `assert` statements. Passing all four modes establishes that critical checks do not depend on assertions optimized away and that the combined mode ignores no warnings; it does not prove that every production risk is covered.

## Step 7: Generate layered evaluation evidence

```powershell
python -B -W error $script --fixture $fixture evaluate  # Generate a normal-path layered evaluation artifact; expect PASS.
python -B -W error $script --fixture $fixture evaluate --failure retrieval_error  # Inject retrieval failure; expect a release-blocking BLOCK artifact.
```

The normal report is `PASS` with exit code `0`; fault injection is `BLOCK` with exit code `1`. The artifact also reports case/critical pass rate, status accuracy, retrieval/context/citation fact recall, non-disclosure violation count, pipeline revisions, and complete fixture/evidence SHA-256. Current fact-count statistics and strict audit validation are identified by `offline-rag-harness-v3`; any change to metrics or validation semantics must advance that version. Cases output only non-sensitive failure codes, never private canaries.

## Fixture contract

The strict loader limits a fixture before parsing to 2,000,000 UTF-8 bytes and JSON container depth 64, and limits documents, queries, facts per document, lists, stage candidates, and context-character budget. JSON-escaped lone surrogates are rejected before hashing/retrieval; an oversized integer that must become a finite numeric value is also a schema error, not a leaked `OverflowError`. Read failures report only error type, not the local path. These are teaching resource-exhaustion boundaries, not throughput-test conclusions; production systems still need budgets at ingress, queues, parsers, and every retrieval stage.

### Documents

Every document contains:

- stable/canonical ID, title, and text;
- tenant, ACL, status, and validity period;
- source revision and teaching authority;
- one or more facts: topic, verbatim statement, value, and unit.

`statement` must appear verbatim in `text` so citation support is deterministically verifiable. Real systems usually use source spans rather than pre-structured facts.

### Queries

Every query case contains two kinds of fields:

- **Runtime fields**: text, tenant, trusted groups, `authorization_revision`, as_of, route, and stable topic.
- **Offline oracles**: slice, critical, expected status/facts, forbidden document IDs, and private body canaries.

The code uses an `_runtime_query()` allowlist projection for runtime fields; expectation fields never reach the answerer. `effective_from` includes its start and `effective_to` excludes its end: `[from, to)`. If a business field means “effective through the end date,” convert it during ingestion to the following day's exclusive date.

> [!warning] The real boundary of two fields
> This project treats `subject_groups` as execution context already resolved as trusted by the host. `authorization_revision` is only an opaque teaching label bound to the trace; the code does not call an authorization resolver or verify the revision's real meaning for groups, tenant, or resource policy. Any non-empty label can still pass fixture validation, so this project cannot prove identity/policy-snapshot compatibility.
>
> Citations bind only the fixture's hand-authored `document_id + fact_id + source_revision` and verify that the fact statement is in the current `document.text`. They do not include raw/canonical hashes, precise source spans, parse/chunk/index generation, or a deletion-tombstone chain. To verify these upstream contracts, continue with [[rag/09-project-offline-provenance-from-source-to-citation|Project: Offline Source-to-Citation Provenance]].

## Practice tasks

### Task A: Add an archived/unpublished document

Add a highly similar `status=archived` document and query. Require:

- Fixture schema still passes.
- The document never enters `retrieved`.
- Its document ID never appears in public response or citations.
- New tests cover normal and `-O` modes.

This proves only a lifecycle hard filter, not deletion. Verify actual deletion in [[knowledge-base-construction/03-versioning-deletion-and-authorization|Versioning, Deletion, and Authorization]] through delete events, source sequence, tombstones, projection/cache propagation, prevention of old-snapshot resurrection, and retention/physical-clearance evidence.

### Task B: Budget compression

Reduce `max_context_chars` and inspect `dropped.reason`. When an answer is refused, decide whether it was a retrieval miss or caused by the context budget.

### Task C: Replace rule components with real components

Replace in order:

1. character recall → BM25, retaining the old version as comparison;
2. add an embedding/dense channel and fusion;
3. topic rule → reranker;
4. extractive generation → LLM structured output;
5. add model judges gradually while retaining deterministic authorization and citation-ID checks;
6. integrate Lesson 9's source-span/generation manifest; do not treat a hand-authored `source_revision` label as proof of content binding.

Replace one layer at a time, pin revisions, and run the same suite.

### Task D: Red-team input and public-output boundaries

Copy the fixture and make two minimum changes: insert a JSON-escaped lone surrogate into any string, then replace one `min_*` threshold with an oversized integer that cannot convert to a finite float. Both CLI calls must return a controlled contract error with exit code `2`, not a traceback. Then run `ask` with an absolute `--fixture` path and confirm public stdout does not echo that path, candidates, or audit fields. This exercise validates local input/projection boundaries only; it does not replace gateway rate limiting, log redaction, or real authentication.

## Production migration checklist

- [ ] Identity, tenant, and groups come from a trusted authentication layer.
- [ ] Parser/chunk/embedding/index all have revisions.
- [ ] Deletion, expiration, and permission changes propagate to caches and replicas.
- [ ] Sparse/dense are observed separately and fusion has qrels experiments.
- [ ] Reranker output validates unknown, duplicate, missing, and non-finite values.
- [ ] Token budgets use the actual tokenizer.
- [ ] Evidence carries source/span/revision.
- [ ] LLM output has schema, timeout, rate limit, and failure states.
- [ ] Claim support is human-calibrated and critical fields have deterministic checks.
- [ ] External documents are untrusted data and tools use least privilege.
- [ ] Logs are redacted, access-restricted, and retained for defined periods.
- [ ] Offline, shadow, low-traffic, and rollback gates are complete.

## Project acceptance

- [ ] Normal state of all eight queries matches the fixture.
- [ ] Old-version, cross-tenant, and ACL documents are filtered before scoring.
- [ ] Canonical mirrors do not consume context twice.
- [ ] Conflicting evidence is not combined into a third answer.
- [ ] Live questions do not enter knowledge retrieval.
- [ ] Answers can be rendered only from validated claims, and claim/citation can be traced to selected context.
- [ ] Public responses contain no filter/candidate trace; changes to unauthorized corpus material do not change public output.
- [ ] Three dependency failures have deterministic, safe, observable behavior.
- [ ] Layered evaluation is `PASS` normally and `BLOCK` under fault injection; complete SHA-256 is reproducible.
- [ ] All 73 tests pass in normal, `-O`, warnings-as-errors, and combined modes.
- [ ] No network, keys, caches, models, or large-data dependencies exist.

## Self-check

1. Why can expected fields in a fixture not become online answering input?
2. Why can this project verify citation provenance but not every semantic-faithfulness property of a real LLM?
3. Why should a public response not even display aggregate filter counts?
4. Why can reranker fallback not expand candidate authorization scope again?
5. Which contracts should not change when character retrieval is replaced by vector retrieval?

Return to the [[rag/00-index|RAG index]].

## References

- Lewis et al., [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)
- Es et al., [RAGAS](https://arxiv.org/abs/2309.15217)
- [OWASP GenAI Security Project: LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
- [OWASP GenAI Security Project: LLM08:2025 Vector and Embedding Weaknesses](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/)
- [OWASP Cheat Sheet Series: RAG Security](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html)

Sources accessed: 2026-07-22.
