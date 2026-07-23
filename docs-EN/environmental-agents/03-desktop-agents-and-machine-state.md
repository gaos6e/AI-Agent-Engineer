---
title: "Desktop Agents and Machine State"
tags:
  - environment-agent
  - computer-use
  - desktop-agent
aliases:
  - Desktop Agents
source_checked: 2026-07-22
lang: en
translation_key: 环境型Agent/03-桌面操作Agent与机器状态.md
translation_source_hash: 63f89243c91ba4731ad263e90b8c5e310e3e3cdc5ab62c03a7dc55c8f3f609d1
translation_route: zh-CN/环境型Agent/03-桌面操作Agent与机器状态
translation_default_route: zh-CN/环境型Agent/03-桌面操作Agent与机器状态
---

# Desktop Agents and Machine State

## Objectives

- Identify focus, windows, modal dialogs, files, and cross-application state in desktop environments.
- Use accessibility information and typed actions instead of unrestricted keyboard/mouse replay.
- Design reproducible machine initial states and executable final-state evaluation.

## Why desktop Agents are harder to constrain

Browsers usually expose a relatively structured DOM and origin. A desktop task may cross applications, file systems, system settings, clipboard, notifications, and native dialogs. The same coordinates point to different objects as resolution, scaling, window stacking, or popups change; a shortcut can reach the wrong focus. Installation, deletion, messaging, and system settings can also cause hard-to-reverse side effects.

OSWorld provides both task initial-state setup and a custom execution-based evaluator. That design shows why “give a screenshot and goal” cannot create reproducible evaluation.

## How to implement it

| Control layer | What to record or constrain |
| --- | --- |
| Machine initial state | VM/image; OS and application versions; locale; time zone; resolution; scaling; account; file/application data |
| Observation | Screenshot, accessibility tree, window list, active window, focus, cursor, file metadata, timestamp |
| Action | Typed schema such as `focus(window)`, `invoke(control)`, `type(text)`, and `open_file(path)` |
| Permission | Launchable applications, accessible directories, network destinations, clipboard, devices, system settings |
| Recovery | VM snapshot, task workspace, event log, idempotent receipt, human-takeover point |
| Verifier | File contents, application-internal data, system settings, cross-application outcome, and unexpected side effects |

Prefer accessibility role/name or an application public interface. Use coordinates only when no structured interface exists, and before every action revalidate window, focus, target region, and screenshot version. Divide high-risk work into “prepare → preview → approve → commit”; bind approval to the file, recipient, or setting value rather than a vague “allow continuation.”

The safest desktop-sandbox default is a disposable VM/containerized desktop with a dedicated low-privilege account. Real host operation needs path, application, and network allowlists and should deny credential stores, system directories, browser profiles, cameras/microphones, and administrator privilege by default.

Model machine identity, application session, and task subject separately. A window title, avatar, username in an accessibility tree, or directory displayed on screen is merely an observation: none proves the account currently logged in or authorizes data access. The runtime should obtain subject and environment-instance ID from a trusted VM harness, OS/SSO adapter, or task-fixed low-privilege test account. Accessibility data helps narrow a UI target but does not prove ownership of a business object. For send, export, permission-change, or credential-use actions, include external account, recipient/object ID, data classification, and target application in action scope and check them again before the adapter executes.

## Common failures

- Window-focus drift sends text to chat, terminal, or password field.
- Modal dialogs, upgrade prompts, notifications, or DPI changes alter coordinate meaning.
- Copy/paste leaks sensitive data; screenshots or logs accidentally capture notifications and credentials.
- “Close window” triggers an unsaved-changes confirmation; retry overwrites or exports twice.
- Evaluation looks only at a final screenshot and misses a file written to the wrong directory or an application-setting change.
- Inconsistent VM initial state makes task difficulty and results incomparable.

## How to validate

Start each trial from the same snapshot and record observation/action/receipt sequence plus before/after environment diff. Inject focus changes, popups, window movement, permission denials, and timeout after execution; verify that the runtime pauses, re-observes, or hands control to a person rather than retrying blindly. The final verifier should read real file/application state and check the allowed-side-effect inventory.

## Practice task

For “open a template in a text editor, save it under a specified filename, and verify contents,” write a test plan: freeze VM/application version and initial directory; provide accessibility location and coordinate fallback; constrain file scope; simulate overwrite confirmation and lost focus; verify with file hash and directory diff while confirming the source file is unchanged.

## References

- Xie et al., [OSWorld original paper](https://arxiv.org/abs/2404.07972) and [official repository](https://github.com/xlang-ai/OSWorld).
- [Playwright actionability](https://playwright.dev/docs/actionability) is web-specific, but its principle of verifying a target before action transfers to a desktop adapter; reimplement the concrete checks for the target OS and application.
- [OWASP AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html) — untrusted external data, least privilege, and separate authorization for sensitive operations; checked 2026-07-22.

