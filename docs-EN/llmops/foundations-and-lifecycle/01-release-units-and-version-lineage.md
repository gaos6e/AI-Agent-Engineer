---
title: "Release Units and Version Lineage"
tags:
  - llmops
  - versioning
aliases:
  - LLM Application Version Lineage
source_checked: 2026-07-14
lang: en
translation_key: LLMOps/01-基础与生命周期/01-发布单元与版本谱系.md
translation_source_hash: b11b3bee073255f76f98d76f8291dae6932885a5197beabe22968a55bf4eafaf
translation_route: zh-CN/LLMOps/01-基础与生命周期/01-发布单元与版本谱系
translation_default_route: zh-CN/LLMOps/01-基础与生命周期/01-发布单元与版本谱系
---

# Release Units and Version Lineage

## Goal

Expand “we changed the model” into version management for the whole composite LLM application, and preserve reconstructable lineage for each answer.

## Why a model name is not enough

The same model behaves like a different system under a different prompt, knowledge base, retrieval `top-k`, tool schema, or safety policy. Conversely, an unchanged provider model name cannot prove behavior will remain unchanged. The operations object is therefore a **release manifest**, not an isolated string.

## Minimal release unit

| Component | Evidence to pin | Common hidden change |
| --- | --- | --- |
| Application code | Git commit, built-artifact digest | Uncommitted local edit |
| API and SDK | API-contract version, SDK-lock digest | Automatic SDK upgrade, field/error semantic change |
| Prompt | Template ID, content digest, variable contract | Direct edit in a management UI |
| Context | Assembly policy, system-message order, truncation rule | Token budget or conversation-summary change |
| Retrieval | Index/snapshot ID, embedding, chunking, filters, top-k, reranker | A document overwritten at the same path |
| Model | Provider, pinned model version or verifiable identifier, inference parameters | `latest` or floating alias |
| Tools | Name, schema digest, implementation version, permission policy | Same tool name but changed side effect |
| Guardrails | Input/output policy, classifier version, fallback policy | Hot policy update missing from release record |
| Evaluation | Regression suite, scorer, human-label rubric, gate-policy version | Only total score retained, losing per-case outcome |
| Routing and price | Routing/fallback manifest, price convention and effective time | Automatic provider switch or recomputing history with current price |

## Immutable versions and movable aliases

An immutable version refers to determined content. `production`, `champion`, and `latest` are movable pointers. Aliases are useful operationally, but a release system must:

1. resolve an alias when execution begins;
2. write actual version and content digest into the release record;
3. never resolve it again in the middle of that release;
4. record actual version in a Trace, not only the alias.

When a provider offers no fixed model snapshot, record the strongest evidence available, strengthen regression evaluation and Canary, and explicitly state that server-side weights cannot be proved unchanged.

## A simplified manifest

```json
{
  "release_id": "support-agent-2026-07-14.1",
  "app": {"commit": "6f1a2c9"},
  "api": {"contract": "responses-v3", "sdk_lock": "sha256:..."},
  "prompt": {"id": "triage-v4", "sha256": "sha256:..."},
  "context_policy": "context-v3",
  "retrieval": {"snapshot": "kb-2026-07-10", "config": "retrieval-v7"},
  "model": {"provider": "provider-a", "version": "pinned-model-id"},
  "tools": [{"name": "lookup_ticket", "schema": "sha256:...", "implementation": "tool-v5"}],
  "guardrail_policy": "guardrails-v2",
  "eval": {"suite": "support-regression-v8", "rubric": "rubric-v4", "grader": "grader-v5"},
  "routing": {"policy": "routing-v3", "fallback": "fallback-release-v2"},
  "pricing_policy": "price-snapshot-2026-07-12"
}
```

This is strict JSON, so comments must not be appended to its lines. `release_id` identifies one immutable release; `app` and `api` pin code and interface contract; `prompt`, `context_policy`, `retrieval`, `model`, and `tools` jointly define model input and external capability; `guardrail_policy` binds safety controls; `eval` fixes offline evidence; `routing` fixes routing/fallback; `pricing_policy` fixes the cost interpretation. `sha256:...` is a teaching placeholder, not a real digest. A real manifest also needs creator, creation time, evaluation evidence, approval, and rollback target.

## Questions a lineage query answers

Starting from any online `request_id`, you should answer: which release was running; which documents or tools it used; which versioned gates evaluated it; whether an external dependency can have drifted the same release; and if not, why the system has logs but not complete lineage.

## Common mistakes and debugging

- **Use a filename as version** — `prompt.txt` can be overwritten. Preserve content digest and immutable snapshot.
- **Version tool schema but not implementation** — identical parameters can acquire a new side effect. Pin both.
- **Record only a knowledge-base name** — documents evolve. Record a snapshot or index-build ID.
- **Treat raw conversation as lineage** — it can contain personal data and secrets. Lineage records versions and digests first; content needs separate necessity, redaction, and retention policy.

## Exercise and self-check

Write a manifest for an assistant that answers reimbursement questions from internal documents, including prompt, context, retrieval, model, tools, guardrails, and evaluation. Why cannot a Git commit replace a prompt content digest? What can and cannot be proved when a provider offers only a floating model name? Why must rollback operate on a whole manifest?

## Next step

The first LLMOps step is giving behavior change a name, evidence, and comparability. Continue with [[llmops/production-engineering/02-gateways-quotas-and-resilience|Gateways, Quotas, and Resilience]] to control how release units access external models.

## References

- [OpenAI API backwards compatibility](https://developers.openai.com/api/reference/overview#backwards-compatibility) — accessed 2026-07-14; explains the role of pinned model versions and evaluation.
- [MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/) — accessed 2026-07-14; general patterns for run/artifact tracing.
