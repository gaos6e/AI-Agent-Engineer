---
title: "Project: Offline Privacy Solution Review"
aliases:
  - Offline Privacy Design Review
  - PET solution-review project
tags:
  - privacy
  - project
  - python
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: 隐私计算/03-项目与自测/07-项目-离线隐私方案评审.md
translation_source_hash: 9e20816a9d873b2f87d3ddf5af79f11b6c948598b20cd955a3004f380f1d8f93
translation_route: zh-CN/隐私计算/03-项目与自测/07-项目-离线隐私方案评审
translation_default_route: zh-CN/隐私计算/03-项目与自测/07-项目-离线隐私方案评审
---

# Project: Offline Privacy Solution Review

## Project goal

Describe a plan for “two institutions jointly releasing regional service statistics” in strict JSON metadata, then use deterministic Python rules to check field necessity, linkage risk, raw-data centralization, DP adjacency and budget, retention/deletion, data flow, FL/secure-aggregation boundaries, and lifecycle controls.

The script never loads real personal data, implements DP, FL, secure aggregation, MPC, FHE, or TEEs, or decides compliance. It trains a different skill: first express purpose, parties, threats, and claims as a reviewable contract, then submit conclusions to privacy, cryptography, domain, security, and legal responsibilities for review.

## File guide

| File | Purpose |
| --- | --- |
| `examples/privacy_review.py` | Strict parsing, contract validation, twelve teaching findings, decision, and CLI |
| `examples/privacy_scenario_vulnerable.json` | A deliberately over-collected scenario that combines techniques incorrectly; expected `BLOCK` |
| `examples/privacy_scenario_hardened.json` | A minimized, controlled, evidence-complete metadata scenario; expected `PASS` |
| `examples/privacy_scenario_contract_error.json` | Contains an unknown field; expected contract error |
| `examples/test_privacy_review.py` | Seventy-six contract, rule, budget, fingerprint, and CLI tests |

The contract covers purpose/non-goals, subject scope, fields' privacy classifications and output roles, party trust, protection-typed data flows, public output projection, structured adjacency, ε/δ ledger, protocol parties/collusion threshold, retention/deletion, lifecycle controls, adversaries, and risk policy. Public output cannot include direct identifiers or fields marked `not_released`. Declarations of MPC, HE, TEE, secure aggregation, and local training must match actual flow types. JSON numeric parameters are decimal strings so binary floating point does not inject noise into the teaching budget.

## Run it

Requires Windows 11, PowerShell 7, and current stable Python 3; it uses the standard library only. Run from this note's directory:

```powershell
Set-Location '.\examples' # Enter the directory containing scenarios, implementation, and tests so all relative paths are fixed.

# Vulnerable scenario: exit code 1, action=BLOCK, PR-001..PR-012
python -B .\privacy_review.py --scenario .\privacy_scenario_vulnerable.json # Run the deliberately over-collected scenario; expect BLOCK.

# Hardened scenario: exit code 0, action=PASS
python -B .\privacy_review.py --scenario .\privacy_scenario_hardened.json # Run the minimized, controlled metadata scenario; expect PASS.

# Unknown field: exit code 2, fail closed
python -B .\privacy_review.py --scenario .\privacy_scenario_contract_error.json # Verify strict-contract rejection with the unknown-field fixture.

python -B .\privacy_review.py --self-test # Run the script's built-in quick invariant checks.
python -B -m unittest discover -s . -p 'test_*.py' -v # Discover and run all regression tests verbosely in normal mode.
python -B -O -m unittest discover -s . -p 'test_*.py' # Confirm production rules do not rely on bare assert removed by -O.
python -B -W error -m unittest discover -s . -p 'test_*.py' # Treat warnings as failures for a stricter execution environment.
```

`BLOCK/REVIEW` returns 1 as a business gate, contract errors return 2, and only `PASS` returns 0. Use `$LASTEXITCODE` in PowerShell to inspect it.

## Understanding the implementation

### Strict input

`load_json` rejects duplicate keys, `NaN`, and invalid JSON. `validate_scenario` rejects unknown or missing fields, wrong types, invalid enums, duplicate IDs, dangling party/field references, and non-finite or invalid DP parameters. Input error cannot masquerade as a successful report.

### Twelve teaching findings

The rules check respectively: any unnecessary field; a public quasi-identifier dimension lacking linkage assessment; multi-holder raw-data centralization derived from flow topology; a public group that is too small; undefined structured adjacency/contribution bounds; a ledger above its limit; missing release approval/accounting; insufficient retention/deletion; sensitive raw fields flowing to an untrusted party; a real FL update visible to the server; unconstrained malicious updates in a real training scenario; and incomplete lifecycle or protocol evidence.

They are not universal regulatory thresholds. For example, `minimum_group_size < 10` and `retention > 90` are frozen teaching policies that demonstrate a gate. Production values must follow actual risk, intended use, and obligations.

### Budget and boundaries

The example performs only the most conservative basic ε/δ addition and explicitly labels itself “not a validated DP guarantee.” A real system also needs to validate adjacency, contribution clipping, mechanism, randomness, accounting method, sampling, concurrency, retries, utility, and every output bypass.

Candidate technologies include both fit and boundary so a “recommend MPC/DP” result cannot be misread as a complete design. An evidence fingerprint proves only that the report inputs agree; it does not prove that JSON claims are true or a mechanism is correct.

## Acceptance tasks

- [ ] The vulnerable scenario triggers `PR-001` through `PR-012` and has action `BLOCK`.
- [ ] The hardened scenario has no findings and action `PASS`.
- [ ] A contract error returns 2 and produces no valid report.
- [ ] All seventy-six tests pass in each of three modes, without caches or personal data.
- [ ] Can map every finding to this course and explain its residual boundary.

## Extension tasks

1. Copy the hardened scenario and change only `retention.days` to `365`; it should yield only `PR-008` and `REVIEW`.
2. Design “two banks compute the intersection of fraud sets”: write the threat model, candidate MPC/PSI guarantee, and output risk first, then fill in JSON.
3. Without changing thresholds, construct tests where the budget exactly equals the limit and where δ alone exceeds its limit.
4. If adding a schema field, first add a failing test, validator, and documentation; do not silently discard an unknown field.

## Self-test questions

1. Why is “data never left the institution” not a complete privacy guarantee?
2. Why does an ε number lack clear subject semantics without defined adjacency?
3. Which observation surface do secure aggregation and DP each protect?
4. Why cannot MPC repair an overly revealing final output?
5. Why does `PASS` not prove that a real DP/MPC/TEE implementation is correct?

Key answer: this project checks only declared metadata and limited teaching rules. It does not validate real data flows, mechanisms, protocols, keys, hardware, attackers, or legal facts.

## Related learning

- Revisit [[privacy-computing/01-foundations-and-risks/02-differential-privacy-intuition-and-budget|Differential Privacy Intuition and Budget]].
- Put the gate into [[evaluation-framework/00-index|Evaluation Framework]] and [[ai-governance/00-index|AI Governance]].
- Connect budget, access, proof, and deletion events to [[runtime-monitoring/00-index|Runtime Monitoring]].

## References

- [NIST SP 800-226](https://csrc.nist.gov/pubs/sp/800/226/final) (final, March 2025; accessed 2026-07-21)
- [NIST Privacy-Enhancing Cryptography](https://csrc.nist.gov/Projects/pec) (accessed 2026-07-21)
- [NIST Privacy Framework](https://www.nist.gov/privacy-framework) (accessed 2026-07-21)
