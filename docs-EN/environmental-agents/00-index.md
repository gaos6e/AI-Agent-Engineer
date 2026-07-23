---
title: "Environment-based Agents"
tags:
  - ai-agent-engineer
  - environment-agent
  - learning-path
aliases:
  - Environment Agents
  - Browser, Desktop, and Coding Agents
source_checked: 2026-07-22
source_baseline:
  - WebArena arXiv:2307.13854
  - OSWorld arXiv:2404.07972
  - SWE-bench ICLR 2024
  - Playwright official documentation
  - OWASP AI Agent Security Cheat Sheet
  - NIST AI RMF Generative AI Profile
ai_learning_stage: 5. Single Agents and Tools
ai_learning_order: 32.5
ai_learning_schema: 2
ai_learning_id: environment-agent
ai_learning_domain: agent-runtime
ai_learning_catalog_order: 3250
ai_learning_hard_prerequisites: []
ai_learning_track_agent_app_order: 650
ai_learning_track_agent_app_kind: optional
ai_learning_track_agent_platform_order: 650
ai_learning_track_agent_platform_kind: optional
content_tier: advanced
difficulty: intermediate
estimated_hours: 12-16
content_origin: original
content_status: dynamic
lang: en
translation_key: 环境型Agent/00-目录.md
translation_source_hash: 027613fe229e85ecfc04a6482a20665084e8d81436c8125e1e227afd0eb7b66c
translation_route: zh-CN/环境型Agent/00-目录
translation_default_route: zh-CN/环境型Agent/00-目录
---

# Environment-based Agents

## Course overview

Browser Agents, desktop-control Agents, and coding Agents appear to use different tools, but they share the same engineering problem: the model sees only a bounded projection of an external state that continues to evolve and may be irreversible. A reliable system must model them as a controlled observation–action runtime, not as “give the model a screenshot or files, then execute whatever it says.”

This course gives the three environments one core contract:

```text
Reproducible initial state → versioned observation → structured action proposal
→ schema / policy / permission / approval / budget checks
→ sandbox adapter execution → receipt + new observation
→ checkpoint / trace → independent verifier checks final state and side effects
```

> [!info] Fact boundary
> Sources were obtained or rechecked on 2026-07-22. This course uses the original papers/projects for WebArena, OSWorld, and SWE-bench, Playwright official documentation, and OWASP/NIST engineering-governance materials to derive stable boundaries. It does not maintain model leaderboards or a specific product UI. Browsers, operating systems, repositories, and benchmark harnesses change; pin versions, images, permissions, and evaluation data again before applying this material to a real environment.

## Where this course fits

Complete these first:

- [[agent-core/00-index|Agent Core]]: state, checkpoints, idempotency, termination, and human control.
- [[tool-calling-function-calling/00-index|Tool Calling]]: schemas, authorization, call IDs, errors, and retries.

Before touching untrusted pages, email, repositories, or privileged actions, at least read [[ai-safety/01-foundations-and-risks/01-assets-trust-boundaries-and-threat-modeling|Threat Modeling]], [[ai-safety/01-foundations-and-risks/02-prompt-injection-and-indirect-injection|Prompt Injection and Indirect Injection]], and [[ai-safety/02-controls-and-governance/04-identity-least-privilege-and-supply-chain|Identity and Least Privilege]]. This is an early safety gate; it does not require completing the production-governance and incident-response sections of [[ai-safety/00-index|AI Safety]] first.

This course applies those invariants to interactive environments. Continue afterward with [[evaluation-framework/00-index|Evaluation Framework]], [[runtime-monitoring/00-index|Runtime Monitoring]], and [[llmops/00-index|LLMOps]] to turn a one-off demonstration into repeatable trials and release gates.

## Learning objectives

- Analyze browser, desktop, and coding environments with one observation–action loop.
- Distinguish hidden authoritative environment state, Agent observation, runtime state, and model context.
- Design action contracts with versions, scope, preconditions, risk, idempotency keys, and acceptance evidence.
- Clearly separate user goal, model plan, delegated authority, environment identity, approval, and adapter receipt. A plan, page text, or model self-report can never escalate permission.
- Use semantic locators and actionability in a browser instead of treating coordinate clicks as the default interface.
- Set sandbox, least-privilege, approval, rollback, or compensation boundaries for desktop and code execution.
- Recover long tasks with checkpoints, receipts, and external facts without repeating side effects.
- Evaluate environment Agents through initial state, final state, trajectory, side effects, cost, and latency together.
- Keep auditable identity, policy, digest, and time evidence while minimizing, redacting, and access-controlling sensitive raw content.

## Recommended sequence

| Order | Lesson | Core question | Completion evidence |
| --- | --- | --- | --- |
| 1 | [[environmental-agents/01-unified-environment-interaction-contract\|A Unified Environment-Interaction Contract]] | How should goals, identity, state, observations, actions, and authorization be layered? | Can draw delegation, control, and evidence boundaries |
| 2 | [[environmental-agents/02-browser-agents-and-actionability\|Browser Agents and Actionability]] | When is a page element safe to operate? | Locator + actionability + final-state verifier |
| 3 | [[environmental-agents/03-desktop-agents-and-machine-state\|Desktop Agents and Machine State]] | How can focus, dialogs, and cross-application side effects be controlled? | VM initial state and typed-action design |
| 4 | [[environmental-agents/04-coding-agents-and-verifiable-patches\|Coding Agents and Verifiable Patches]] | How can “tests passed” become bounded completion evidence? | Repository snapshot + patch + bidirectional tests |
| 5 | [[environmental-agents/05-sandboxes-permissions-approvals-and-rollback\|Sandboxes, Permissions, Approvals, and Rollback]] | Which controls must live outside the model? | Risk tiers and authorization matrix |
| 6 | [[environmental-agents/06-long-running-task-checkpoints-and-idempotent-recovery\|Long-running Task Checkpoints and Idempotent Recovery]] | How can work continue safely after a crash? | Checkpoint schema and crash-window table |
| 7 | [[environmental-agents/07-environment-evaluation-and-integrated-project\|Environment Evaluation and Integrated Project]] | How can you prove task success without out-of-scope side effects? | Evaluation card and 103 offline tests |

Plan 12–16 hours: 60–90 minutes for each of the first six lessons and 4–6 hours for the integrated project.

## A unified view of three environments

| Environment | Example observation | Example action contract | Authoritative state | Completion evidence |
| --- | --- | --- | --- | --- |
| Browser | URL, accessibility tree, DOM summary, screenshot, network result | Navigate, locator click/fill, download | Session, tab, storage, site backend | Page assertion + backend business state + receipt |
| Desktop | Screen, accessibility tree, windows/focus, file metadata | Focus, click, type, launch, file operation | OS, application, file system, clipboard | Executable final-state check + side-effect inventory |
| Coding | Commit, worktree, files, index, test output | Read/search/edit/test/build | Repository snapshot, dependencies, worktree | Target tests + regression tests + diff/policy checks |

Screenshots, DOM, terminal output, and issue text are observations. They are not automatically trusted instructions; neither does a model-proposed action automatically obtain permission.

## Hands-on entry point

The course project uses only Python's standard library and an in-memory sandbox. It never calls a real browser, desktop, shell, network, or model:

```powershell
Set-Location ".\docs-EN\environmental-agents"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B .\examples\environment_runtime.py
python -B -W error .\examples\test_environment_runtime.py
python -B -O -W error .\examples\test_environment_runtime.py
```

The project includes strict fixture/action/checkpoint schemas; path and test-target scope; permission denials; model-external HMAC approvals; binding to environment instance and pre/post-state fingerprints; proposal and wall-clock expiry; frozen expired pending intents and recovery with a fresh approval; proposal/step budgets; idempotent replay whose authority is the adapter receipt; complete receipt fingerprints; human reconciliation through `needs_review`; HMAC checkpoints with an external monotonic high-water mark; crash-window recovery; versioned verification; cancellation; and termination. The current baseline is 103 offline tests.

## Mastery checklist

- [ ] I can explain the difference between environment state, observation, runtime state, and context.
- [ ] I can write schema, scope, precondition, risk, idempotency, and evidence fields for an action.
- [ ] I can explain why locator uniqueness, visibility, stability, event reception, and enabled state are runtime checks.
- [ ] I can freeze VM, application, account, locale, window, and data initial state for a desktop task.
- [ ] I can freeze base commit, dependencies, tests, and network policy for a coding task.
- [ ] I can bind a high-risk write to short-lived approval with exact scope.
- [ ] I can handle the crash window where a side effect happened but its checkpoint was not written.
- [ ] I can check initial state, final state, trajectory, side effects, cost, and latency together.
- [ ] I can run 103 tests and explain at least five negative cases.
- [ ] I can identify when to fall back to a fixed workflow or human operation.

## Primary references

| Topic | Primary source | How this course uses it |
| --- | --- | --- |
| Real web environments and functional correctness | Zhou et al., [WebArena](https://arxiv.org/abs/2307.13854); [official repository](https://github.com/web-arena-x/webarena) | Initial state, real sites, and functional final-state evaluation |
| Real computer environments and executable evaluation | Xie et al., [OSWorld](https://arxiv.org/abs/2404.07972); [official repository](https://github.com/xlang-ai/OSWorld) | Machine initial state, cross-application state, and executable verifier |
| Real repository issue-to-patch tasks | Jimenez et al., [SWE-bench (ICLR 2024)](https://openreview.net/forum?id=VTF8yNQM66); [official repository](https://github.com/SWE-bench/SWE-bench) | Base commit, patch, FAIL_TO_PASS, and PASS_TO_PASS |
| Locators and action preconditions | [Playwright: Auto-waiting / actionability](https://playwright.dev/docs/actionability) | Checks for uniqueness, visibility, stability, event reception, enabled state, and more |
| Environment isolation and robust locators | [Playwright: Best Practices](https://playwright.dev/docs/best-practices) | Isolation, user-visible behavior, semantic locators, and web-first assertions |
| Agent tools and human control | [OWASP AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html) | Least privilege, untrusted external data, separate authorization for sensitive actions, and adversarial testing |
| Organization-level risk governance | [NIST AI RMF and Generative AI Profile](https://www.nist.gov/itl/ai-risk-management-framework) | Risk, measurement, human oversight, and why release evidence is more than one benchmark score |

## Course boundary

This course does not teach steps for a specific browser SDK, desktop product, or coding-Agent CLI. Those APIs change and do not define the control plane. It also does not treat one benchmark score as production capability: deployment still needs validation of identity, data, organizational process, concurrency, compliance, maintainability, and incident recovery.

