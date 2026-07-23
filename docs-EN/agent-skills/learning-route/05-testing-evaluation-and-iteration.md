---
title: "Agent Skills Testing, Evaluation, and Iteration"
aliases:
  - Skill evaluation
tags:
  - agent-skills
  - evaluation
source_checked: 2026-07-14
lang: en
translation_key: Agent Skills/学习路线/05-测试评测与迭代.md
translation_source_hash: 5f3bba2fb4cfcc1be3f4124f879f8b86a01c31e68105e2d419559ab4c0ed632e
translation_route: zh-CN/Agent-Skills/学习路线/05-测试评测与迭代
translation_default_route: zh-CN/Agent-Skills/学习路线/05-测试评测与迭代
---

# Agent Skills Testing, Evaluation, and Iteration

## Goal

Turn “it seems to work” into four layers of evidence — format, triggering, execution, and artifacts — and iterate from that evidence.

## Four validation layers

1. **Format** — The `SKILL.md` frontmatter parses, and the name, description, and directory follow the specification. The official format provides `skills-ref validate ./my-skill`.
2. **Triggering** — Real should-trigger and near-miss should-not-trigger queries load the Skill as expected.
3. **Execution** — Steps, scripts, and error recovery reproduce in a clean context.
4. **Artifacts** — Output satisfies observable assertions and improves over a no-Skill or old-version baseline.

Format validation alone does not prove task quality. One attractive output can hide false triggers, boundary failures, and work that the baseline already performs just as well.

## Designing evaluation cases

Official guidance divides a case into a realistic prompt, expected output, and optional input files. Start with two or three execution cases to expose the output shape, then expand concrete assertions. Trigger boundaries need more balanced positive and negative samples. This course's `evals.json` adds `should_trigger` and `reason` as local teaching fields; do not present it as a universal evaluation schema for every client.

Useful assertions include:

- “stdout is valid JSON”;
- “the JSON contains `words`, `characters`, and `lines`”;
- “without `--text`, the exit code is nonzero and the error identifies the missing argument.”

“The output is good” cannot be verified. “The output must exactly equal this sentence” is often needlessly brittle.

## Skill versus baseline

Run every case twice in a clean context: once with the Skill loaded and once without it (or with an older version). Keep the prompt, input, and runtime environment identical, and record:

- PASS or FAIL for every assertion, with concrete evidence;
- time and token cost, if the client can provide them reliably;
- error recovery, additional tool calls, and human intervention;
- a human review of usability, safety, and writing quality.

Prefer scripts for mechanical checks. Reserve human review for style and properties such as whether the result is genuinely helpful. If both versions pass, the assertion may be too easy or the Skill may add no value. If both fail, first check whether the case and assertion are reasonable.

## Iteration order

1. Find a specific failure from an execution trace instead of expanding the entire Skill by intuition. First determine whether the agent discovered the right Skill, which resources it read, and which command it ran.
2. Classify the issue as triggering, instruction, resource, script, or test.
3. Make the smallest change and retain the old version as a baseline.
4. Re-run the original cases and new validation cases that did not guide the change.
5. Record benefit and cost; remove material that produces no stable gain.

## What the local validator does

This knowledge base's `examples/validate_skill.py` uses only the standard library to check the example's core teaching constraints and resource references. It does not parse all YAML and does not replace the official `skills-ref`. The project acceptance checks run this local validator. If `skills-ref` is not installed, record it as unverified rather than claiming the official validation passed.

## Exercises and self-check

1. Write one ordinary case, one boundary case, and one near-miss negative case for your own Skill.
2. Give every output at least one mechanical assertion and one question for human review.
3. Self-check: why refine assertions only after an initial run? Actual outputs reveal which quality dimensions are observable and prevent you from inventing a wrong check.

## Next step

Finish with [[agent-skills/learning-route/06-project-create-and-validate-an-agent-skill|Project: Create and Validate an Agent Skill]].

## References

- [Evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills) — retrieved 2026-07-14.
- [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) — retrieved 2026-07-14.
- [Agent Skills Specification: Validation](https://agentskills.io/specification#validation) — retrieved 2026-07-14.
