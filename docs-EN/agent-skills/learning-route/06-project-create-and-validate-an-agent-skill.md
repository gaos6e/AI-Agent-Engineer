---
title: "Project: Create and Validate an Agent Skill"
aliases:
  - Agent Skill creation project
tags:
  - agent-skills
  - project
source_checked: 2026-07-22
lang: en
translation_key: Agent Skills/学习路线/06-项目-创建并验证技能.md
translation_source_hash: 7d453ef88d93c2377a52f6e14cc43f83785f22e3a67bed6a59d82f00cb063b7e
translation_route: zh-CN/Agent-Skills/学习路线/06-项目-创建并验证技能
translation_default_route: zh-CN/Agent-Skills/学习路线/06-项目-创建并验证技能
---

# Project: Create and Validate an Agent Skill

## Project goal

Inspect a complete `text-statistics` Skill: valid frontmatter, a clear trigger boundary, an offline script, structured output, and evaluation cases. Then make a small change and use a negative test to prove the validation is effective.

## Project layout

```text
examples/
├── validate_skill.py                 # Strict teaching-profile validator
├── test_validate_skill.py            # 56 offline regression tests
└── text-statistics/
    ├── SKILL.md
    ├── scripts/
    │   └── text_stats.py
    └── evals/
        └── evals.json
```

The example reads only explicit command-line text or a UTF-8 file no larger than 1 MiB. The two input paths apply the same byte limit, write statistics to stdout, never use the network, never write a business file, need no credentials, and never echo the original text.

## Run it in PowerShell 7

Run the following from the project root that contains both `docs-EN/` and `.website/`:

```powershell
Push-Location -LiteralPath 'docs-EN\agent-skills' # Enter the course directory so the relative examples below resolve correctly
python -B .\examples\validate_skill.py .\examples\text-statistics # Validate frontmatter, resource references, trigger corpus, and script syntax
python -B .\examples\text-statistics\scripts\text_stats.py --text "Hello Agent world" # Demonstrate stable JSON for direct text; -B prevents bytecode caches
python -B .\examples\text-statistics\scripts\text_stats.py --help # Show non-interactive parameters and safety notes without side effects
python -B .\examples\test_validate_skill.py # Run the full offline regression suite in normal mode
python -B -O .\examples\test_validate_skill.py # Verify the validator does not rely on bare assert
python -B -W error .\examples\test_validate_skill.py # Promote warnings to failures to surface compatibility issues early
python -B -O -W error .\examples\test_validate_skill.py # Repeat in the strictest combined mode
Pop-Location # Restore the PowerShell working directory from before this block
```

Expected result: the first command prints JSON with `status: ok`, ten positive and ten negative trigger cases, and the scripts it checked. The second prints `words`, `characters`, and `lines`. The third shows non-interactive argument help. All four test modes should report 56 passing tests. `-B` avoids `__pycache__`; rerunning with `-O` shows that tests do not rely on bare `assert` statements removed by optimization; `-W error` converts warnings into errors.

## Reading order

1. Open [SKILL.md](agent-skills/examples/text-statistics/SKILL.md) and find both “what it does” and “when to use it.”
2. Check that `name` exactly matches the parent directory, `text-statistics`.
3. Check when the body tells the agent to run [text_stats.py](agent-skills/examples/text-statistics/scripts/text_stats.py), and verify that both `--text` and file input enforce the 1 MiB UTF-8 byte limit.
4. Read [evals.json](agent-skills/examples/text-statistics/evals/evals.json) and review whether its positive and near-miss negative cases are realistic. It is this course's trigger-corpus format, not an official universal schema.
5. Run the validator and tests. Then copy the example to a temporary location, deliberately change the name to `Text-Statistics`, and confirm validation fails. Do not damage the course original.

Resource references are themselves an auditable text contract: they must be canonical POSIX paths beginning with `scripts/`, `references/`, or `assets/`. Although `scripts/../SKILL.md` resolves inside the Skill root, the local validator rejects it so the same resource cannot appear under multiple confusing spellings. This is not an additional official-certification claim.

## Extension task

Before adding `--top-words N`, write the contract: input scope, Chinese and English token rules, casing, punctuation, and output schema. Then:

- update the script and `--help`;
- update the description only if the capability boundary truly changes;
- add one ordinary, one empty-text, and one invalid-`N` test;
- confirm that default output never exposes the original full text.

## Acceptance checklist

- [ ] The local teaching validator exits with code 0.
- [ ] The script is non-interactive and offline, writes JSON to stdout, and gives actionable errors for missing arguments.
- [ ] The description names a capability and its use condition without overreaching into rewriting or translation.
- [ ] The evaluation corpus has ten positive and ten negative trigger cases, and negatives cover adjacent tasks rather than obviously irrelevant ones.
- [ ] The 56 regression tests pass in normal, `-O`, `-W error`, and `-O -W error` modes.
- [ ] I can explain that the local validator is neither a complete YAML parser nor certification of the official specification.
- [ ] If official `skills-ref` is available, I also run `skills-ref validate ./examples/text-statistics`; if it is unavailable, I record that it was not run.

## Self-check

1. Why is the parent directory name part of the contract? It keeps discovery and Skill identity stable.
2. Why does a should-not-trigger case not require script output? It tests whether the Skill should load, not the result of execution.
3. If the script needs to write real files, which protections should be added? At minimum: target scoping, dry run or confirmation, idempotence or rollback, and redacted logs.

## References

- [Agent Skills Specification](https://agentskills.io/specification) — retrieved 2026-07-14.
- [Quickstart](https://agentskills.io/skill-creation/quickstart) — retrieved 2026-07-14.
- [Evaluating skills](https://agentskills.io/skill-creation/evaluating-skills) — retrieved 2026-07-14.
- [Using scripts in skills](https://agentskills.io/skill-creation/using-scripts) — retrieved 2026-07-14.
