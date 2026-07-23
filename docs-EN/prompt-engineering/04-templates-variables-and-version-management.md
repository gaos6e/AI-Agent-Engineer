---
title: "Templates, Variables, and Version Management"
tags:
  - prompt-engineering
  - prompt-template
  - versioning
aliases:
  - Prompt-template version management
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline:
  - OpenAI Prompt engineering guide
  - OpenAI reusable-prompt migration and deprecation guides
  - Anthropic Prompt engineering overview
lang: en
translation_key: 提示词工程/04-模板、变量与版本管理.md
translation_source_hash: 09f7bcde43b62729088bf973ef65592bba35fa7de2857c6ac14ab4b389c04b9b
translation_route: zh-CN/提示词工程/04-模板、变量与版本管理
translation_default_route: zh-CN/提示词工程/04-模板、变量与版本管理
---

# Templates, Variables, and Version Management

## Goal of this lesson

Turn strings scattered through code into engineering assets with an owner, a version, and evaluation evidence.

## Parts of a template

Separate stable content from variables:

- **policy:** task objective, output contract, and non-negotiable boundaries;
- **examples:** a small set of reviewed examples;
- **context:** retrieved evidence with its source;
- **input:** current user data;
- **metadata:** template version, language, and experiment group. Fields not sent to the model stay in application code.

Do not pass arbitrary JSON containing braces directly to Python **str.format()**, and do not render user input by executing template expressions. Choose a simple renderer that substitutes declared variables only, and validate their length, type, and provenance.

### Where templates belong

A robust default is to keep prompt bodies, schemas, and cases next to application code as reviewed assets: put them under version control, send them through code review, and make them rollback-able with the application version. If a provider-hosted feature still exists, treat it only as a dynamic release or runtime mechanism. Tested repository assets and their release mapping remain the auditable source of truth.

This is changing functionality, so old tutorials are not enough. According to OpenAI prompt-engineering, migration, and deprecation pages checked on **2026-07-21**, reusable prompt objects were announced as deprecated on **2026-06-03**, and **v1/prompts** and related objects are scheduled to stop service on **2026-11-30**. The stated migration direction is to move prompt content into application code and manage it with typed parameters, repository review, tests, and release processes. This timeline describes OpenAI's current announcement only; it does not apply to other providers and may change in the future.

## A version is not a filename ending in v2

At minimum, a reproducible call records:

~~~text
prompt_id: ticket-router
prompt_version: 1.3.0
schema_version: 1.1.0
model_configuration_id: provider-alias-2026-07
evaluation_set: routing-golden-2026-07
~~~

A wording fix with no expected behavior change can use a patch version. A field or rule change should use a larger version increment and migrate consumers. The specific versioning scheme matters less than ensuring an old request can identify the prompt, schema, and configuration used at the time. A version string can still be forgotten, so important experiments should also record content hashes of the prompt, schema, and dataset. This course project rejects a case whose declared version differs from the code assets.

## Release process

1. Submit a narrowly scoped prompt and schema change.
2. Evaluate it on fixed offline cases and controlled online shadow traffic.
3. Inspect overall metrics and critical slices, especially high-risk failures.
4. Roll out to a small share, monitoring parsing errors, latency, usage, and human corrections.
5. Expand only after the threshold is met; retain the ability to quickly return to the prior version.

Do not change the prompt, model, retrieval, and post-processing in the same experiment, because the result cannot then be attributed to a cause.

## Privacy and logging

Do not log full raw prompts by default. Hashes, versions, field lengths, redacted error categories, and request IDs are often sufficient. If samples must be retained, determine access controls, retention duration, and deletion procedures first. Keys may come only from environment variables or a secret-management service, never from a template.

## Practice and self-check

Design a prompt-change record that includes the reason for change, the failure category expected to improve, evaluation-set version, passing threshold, rollback condition, and owner. Self-check: three months later, can you reproduce the exact contract that produced a particular bad output?

## Mastery check

- [ ] Prompt body, schema, cases, and model configuration all have traceable versions.
- [ ] Variables have an explicit type, length, and provenance; high-privilege policy is not concatenated with user text.
- [ ] An experiment changes one major factor at a time and states rollout and rollback thresholds in advance.
- [ ] Before using a provider-hosted object, I check its current lifecycle and migration announcements.

## Next step

Continue to [[prompt-engineering/05-evaluation-driven-iteration|Evaluation-driven iteration]] to add executable evidence to the release process.

## References

- [OpenAI: Prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering) (accessed 2026-07-21)
- [OpenAI: Migrate from prompt objects](https://developers.openai.com/api/docs/guides/prompting/migrate-from-prompt-object) (accessed 2026-07-21)
- [OpenAI: API deprecations—Reusable prompts](https://developers.openai.com/api/docs/deprecations#2026-06-03-reusable-prompts) (accessed 2026-07-21)
- [Anthropic: Prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview) (accessed 2026-07-21)

