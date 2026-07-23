---
title: "Project: Offline Agent Threat Review"
aliases:
  - Offline Agent Threat Review
  - Agent Security Review Project
tags:
  - ai-security
  - project
  - python
source_checked: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: AI安全/03-项目与自测/07-项目-离线Agent威胁评审.md
translation_source_hash: 33ae8bf162982e2925a699cfc64886d6802debddb64ccc8eaf0445b15139784b
translation_route: zh-CN/AI安全/03-项目与自测/07-项目-离线Agent威胁评审
translation_default_route: zh-CN/AI安全/03-项目与自测/07-项目-离线Agent威胁评审
---

# Project: Offline Agent Threat Review

## What you will build

Create a strict scenario contract for an Agent that “reads one email and produces a draft, never sending automatically.” Use deterministic Python rules to find risks from untrusted email through tools, identity, data egress, supply chain, and operational controls. The project runs offline: it calls no model, connector, or network and requires no secret.

This is not a vulnerability scanner or penetration test. It trains a reusable engineering chain:

```text
Intended use / non-goals → assets and boundaries → capabilities / identities / dependencies → control contract
                         → deterministic findings → PASS / REVIEW / BLOCK → regression tests
```

## Files

| File | Purpose |
| --- | --- |
| `examples/threat_review.py` | Strict JSON parsing, contract validation, eleven teaching rules, decisions, and CLI |
| `examples/agent_scenario_vulnerable.json` | A deliberately over-capable scenario; expected result: `BLOCK` |
| `examples/agent_scenario_hardened.json` | A least-privilege, read-only scenario; expected result: `PASS` |
| `examples/agent_scenario_contract_error.json` | An unknown-field fixture; expected result: contract error |
| `examples/test_threat_review.py` | Regression tests for the contract, rules, fingerprints, CLI, and self-test |

The input explicitly declares asset classification, trust boundaries, non-authoritative sources, identity scopes and expiration, tool execution identities, side effects, concrete endpoints and resources, data egress, dependency summaries, approval, sandboxing, memory flow, and risk policy. The strict contract rejects duplicate JSON keys, `NaN`, unknown fields, dangling references, conflicting mode/effect combinations, broad destinations, and uncovered severities. This prevents silently interpreting dirty input.

## Runtime environment

- Windows 11 with PowerShell 7.
- Current stable Python 3.
- Standard library only; install no dependencies.

Run the following from this note's directory:

```powershell
Set-Location '.\examples' # Enter the directory containing scenarios, implementation, and tests so the following relative paths work directly.

# Vulnerable scenario: exit code 1, action=BLOCK
python -B .\threat_review.py --scenario .\agent_scenario_vulnerable.json # Run the deliberately overprivileged scenario and verify that it reliably produces BLOCK.

# Hardened scenario: exit code 0, action=PASS
python -B .\threat_review.py --scenario .\agent_scenario_hardened.json # Run the least-privilege hardened scenario and verify that it produces PASS.

# Input contract error: exit code 2
python -B .\threat_review.py --scenario .\agent_scenario_contract_error.json # Use the unknown-field fixture to verify that the input contract fails closed.

# Built-in smoke check
python -B .\threat_review.py --self-test # Run the script's built-in quick self-check path.

# 80 tests; then use -O and warnings-as-errors to verify tests do not depend on assert or warnings
python -B -m unittest discover -s . -p 'test_*.py' -v # Discover and run all tests verbosely in normal mode.
python -B -O -m unittest discover -s . -p 'test_*.py' # Verify production rules do not depend on bare assert under -O.
python -B -W error -m unittest discover -s . -p 'test_*.py' # Turn warnings into failures to check stricter runtime conditions.
```

In PowerShell, inspect the exit code through `$LASTEXITCODE`. Here, `BLOCK` and `REVIEW` return 1 as expected business decisions; they do not mean the program crashed.

## Read the implementation

### 1. Strict contract

`load_json` rejects duplicate keys and nonstandard constants. `validate_scenario` checks exact fields, types, enumerations, unique IDs, and referential integrity at every layer, then returns a deep copy. Contract errors always exit with code 2.

### 2. Eleven teaching findings

The rules cover indirect injection reaching a side-effect tool, unnecessary functionality, shared, long-lived, or overbroad identities, weak approval, unconstrained destinations, sensitive data without egress validation, unpinned or unverified dependencies, inadequate sandboxing, unvalidated tool parameters, memory poisoning, and missing audit, rate limits, or emergency shutdown.

Every finding contains the asset, attack path, impact, recommended control, owner, and verification method. Results are sorted stably by severity and ID for diffs and gates.

These eleven rules are not an automated compliance mapping for the OWASP Agentic Top 10. They do not fully validate inter-Agent message identity or integrity, cross-Agent cascades, human trust calibration, or autonomous deviation or rogue behavior. A multi-Agent project must create separate scenarios, end-state assertions, and exercises for those risks rather than substitute this project's `PASS`. You can connect collaboration-side negative contracts to [[multi-agent-collaboration/engineering-and-quality/08-identity-authorization-and-cross-boundary-trust|Identity, Authorization, and Cross-Boundary Trust for Multi-Agent Systems]] and place the two result sets together in a release gate.

### 3. Decisions and evidence fingerprints

The scenario freezes which severities `BLOCK` and which require `REVIEW`; only no triggered findings produces `PASS`. The report calculates a SHA-256 fingerprint from canonical JSON for the scenario and findings. This helps establish that the same evidence is being compared, but the fingerprint is not a digital signature and cannot prove that the input is genuine.

## Acceptance tasks

### Basic acceptance

- [ ] The vulnerable scenario produces `AS-001` through `AS-011` and the action `BLOCK`.
- [ ] The hardened scenario produces no findings and the action `PASS`.
- [ ] The contract-error scenario returns exit code 2 without producing a plausible-looking report.
- [ ] All three test modes pass without producing caches.

### Understanding acceptance

Explain, rule by rule, why the vulnerable scenario triggers all eleven findings and map each to the corresponding lesson in this course. In particular, explain why removing `send_mail` is stronger than telling the model “do not send”; why a tool schema still needs authorization; and why `PASS` cannot claim that a system is secure.

### Extension task

Copy the hardened scenario and change only its dependency's `pinned` value to `false`; verify that it yields `REVIEW` and `AS-007`. Then design your own “shared drive to ticket” JSON. Write the expected findings and decision before running it. If you add a field, change the contract and failure test first; never let unknown fields pass silently.

## Self-test questions

1. Why should external content, model output, and tool results all be treated as untrusted?
2. How does `required_for_purpose` help identify excessive functionality? Why cannot it replace human threat modeling?
3. What is the blast radius of one identity that has both `mail.read` and `mail.send`?
4. Why must approval bind normalized arguments and a state version?
5. What can a report fingerprint prove, and what can it not prove?
6. If no rule fires, what real validation is still missing?

Key points for the answers: deterministic rules can inspect only a limited declared contract. They do not execute a real model, identity provider, tool, sandbox, or network, and they do not prove that JSON declarations match a deployment. Therefore, `PASS` means only that “this input did not trigger the teaching rules.”

## Further study

- Review [[ai-safety/01-foundations-and-risks/01-assets-trust-boundaries-and-threat-modeling|Assets, Trust Boundaries, and Threat Modeling]].
- Turn findings into security regressions and release gates in [[evaluation-framework/00-index|Evaluation Framework]].
- Connect denials, approval, and emergency-shutdown events to [[runtime-monitoring/00-index|Runtime Monitoring]].

## References

- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) (accessed 2026-07-22)
- [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) (published December 2025; accessed 2026-07-22)
- [MITRE ATLAS](https://atlas.mitre.org/) (accessed 2026-07-22)
