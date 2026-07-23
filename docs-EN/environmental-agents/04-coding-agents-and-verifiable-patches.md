---
title: "Coding Agents and Verifiable Patches"
tags:
  - environment-agent
  - coding-agent
  - software-evaluation
aliases:
  - Coding Agents
source_checked: 2026-07-22
lang: en
translation_key: 环境型Agent/04-编码Agent与可验证补丁.md
translation_source_hash: 2cb84e8f95f826024c64ab5eb77f867e14b6dca58ca5c001a6489b1fcebad274
translation_route: zh-CN/环境型Agent/04-编码Agent与可验证补丁
translation_default_route: zh-CN/环境型Agent/04-编码Agent与可验证补丁
---

# Coding Agents and Verifiable Patches

## Objectives

- Model a coding Agent as controlled work on a versioned repository environment.
- Design a minimal action space for reading, editing, commands, and tests.
- Verify a patch through target tests, regression tests, and its diff together.

## Why code generation is not a coding Agent

A coding Agent confronts repository state, not a function prompt: base commit, uncommitted changes, dependencies, build tools, test data, operating system, environment variables, and issue semantics. A patch can repair a target test while breaking existing behavior; a shell command can expose credentials, reach the network, or alter files outside the repository; test output can itself be hostile or misleading text.

SWE-bench connects real GitHub issues, repository baselines, and executable tests, providing stronger outcome verification than string similarity. It is still a particular task distribution and harness—not a guarantee of code quality, security, maintainability, or production readiness.

## How to implement it

1. **Create a task envelope:** task ID, issue, base commit, allowed paths, language/dependency lock, offline/network policy, resource/time budget, prohibited behavior, and completion standard.
2. **Protect the user's worktree:** use an isolated worktree, container, or temporary copy; record current diffs first and never implement “clean the environment” as a destructive reset.
3. **Shrink the action space:** prefer `search(query, scope)`, `read(path, range)`, `apply_patch(path, expected_hash, patch)`, and `run_test(target)`. Open arbitrary shell only behind a strong sandbox and command policy.
4. **Version edits:** bind an action to file hash/base revision; check path and old content before writing, and re-observe on conflict. Every patch has a reversible diff and receipt.
5. **Validate in layers:** run the smallest target test first, then related regression, static checks, and necessary full suite; freeze the test environment and avoid unknown network state.
6. **Completion gate:** check target behavior, existing behavior, worktree diff, prohibited paths, generated artifacts, sensitive information, and remaining failures together. A model self-report is not evidence.

> [!warning] Git worktree is not a security sandbox
> A linked worktree separates checkout, `HEAD`, and index from the user's current worktree, so it helps preserve uncommitted changes, pin base revision, and run trials in parallel. It still shares most repository objects and normally shares repository configuration. Hooks and settings reachable from the common Git directory/config are therefore shared attack surface. A coding Agent in a separate worktree still needs separate restrictions on file system, commands, network, environment variables, and available credentials. A production adapter must not treat “inside a worktree” as complete security evidence. [Git worktree documentation](https://git-scm.com/docs/git-worktree.html), checked 2026-07-22.

SWE-bench `FAIL_TO_PASS` can represent whether the target defect is repaired, while `PASS_TO_PASS` can represent whether existing behavior remains intact. A real project still needs type/lint, security, performance, migration, and human-review gates.

## Common failures

- Base commit or dependencies are not pinned, so results cannot be reproduced.
- The Agent sees uncommitted user changes and overwrites, reformats, or deletes unrelated files.
- Only one target test runs, missing regressions; or tests are modified to “prove” an implementation correct.
- Shell permission is too broad: a command escapes the workspace, reads credentials, or downloads an unreviewed dependency.
- A timed-out test process is retried blindly, leaving services, lock files, ports, or database writes behind.
- Benchmark pass rate is presented as real engineering ability, ignoring data contamination and task-distribution shift.

## How to validate

Run multiple trials from a clean pinned snapshot and record every read, patch, command, test, and environment diff. Inject at least: stale file hash, path escape, command denial, target test passing with regression failure, test timeout, modification of a test file, and pre-existing user diff. Completion is allowed only when the verifier succeeds from the current worktree and current test receipt.

## Practice task

Choose a small offline repository with a failing test. Freeze base commit and dependencies; expose only one source directory and exact test command; require expected file hash for every action; run target and regression tests after the repair; output patch, test receipt, unexpected file changes, and rollback steps. Then write one negative test proving that the Agent cannot edit a test to cheat.

## References

- Jimenez et al., [SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://openreview.net/forum?id=VTF8yNQM66), ICLR 2024.
- [SWE-bench official project and evaluation harness](https://github.com/SWE-bench/SWE-bench).
- Yang et al., [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793) — impact of the action interface on Agent capability.
- [Git worktree documentation](https://git-scm.com/docs/git-worktree.html) — shared and per-worktree state boundaries; checked 2026-07-22.
- [OWASP Secure Coding with AI Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Coding_with_AI_Cheat_Sheet.html) — multiple trust boundaries in agentic coding; checked 2026-07-22.

