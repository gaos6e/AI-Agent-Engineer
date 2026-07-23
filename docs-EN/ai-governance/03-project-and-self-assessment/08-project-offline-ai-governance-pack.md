---
title: "Project: Offline AI Governance Pack"
aliases:
  - Offline AI Governance Pack
tags:
  - ai-governance
  - project
  - python
source_checked: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: AI治理/03-项目与自测/08-项目-离线AI治理包.md
translation_source_hash: 9336d96e18c1cb2b1387522349a4af0651c3ed4cafe6150861d84b77c882d07b
translation_route: zh-CN/AI治理/03-项目与自测/08-项目-离线AI治理包
translation_default_route: zh-CN/AI治理/03-项目与自测/08-项目-离线AI治理包
---

# Project: Offline AI Governance Pack

## Project goal

Run `examples/governance_pack.py` to generate a JSON governance pack for a fully synthetic system that assists the organization of benefit-application materials. The scenario may only organize materials and generate a list of missing items; it explicitly must not decide eligibility or contact applicants automatically. The script connects the system inventory, responsibilities, risks and impacts, data, models, vendors, approvals, changes, monitoring, incidents, and retirement plan into a versioned evidence pack.

Run these commands from this note's directory:

```powershell
python -B .\examples\governance_pack.py # Generate the governance pack for the synthetic scenario; -B prevents bytecode caches.
python -B .\examples\governance_pack.py --self-test # Run the script's built-in quick invariant checks.
python -B -m unittest discover -s .\examples -p 'test_*.py' -v # Discover and run the governance-pack regression tests verbosely in normal mode.
python -B -O -m unittest discover -s .\examples -p 'test_*.py' # Confirm production validation does not rely on bare assert removed by -O.
python -B -W error -m unittest discover -s .\examples -p 'test_*.py' # Treat warnings as failures to reveal potential compatibility problems.
```

The script uses only the Python standard library, writes to standard output, does not write files or access the network, and does not read environment variables or real data. The organizations, vendors, people, and regions in the example are fictional placeholders.

## Reading order

1. `SCENARIO`: the system's intended and prohibited uses, affected people, data, components, and risk facts.
2. `tier_risk`: how the teaching internal matrix prioritizes risk, including its override for high-impact scenarios.
3. `build_pack`: how one set of facts produces cross-referencing registers and plans. Data sources carry versions and owners; vendor records carry a due-diligence snapshot, owner, and exit boundary.
4. `validate_scenario` and `validate_pack`: explicit deterministic validation of status and decision roles, data-risk consistency, every nested artifact, ISO dates, approval scope and versions. The scenario's SHA-256 binds approval to the original facts so simultaneous tampering with two version tables does not pass. The digest uses this project's stable local JSON serialization only for change detection; it is not a digital signature, a cross-system canonicalization standard, or proof of real provenance. Validation does not rely on `assert`, which `python -O` removes.

## Governance-pack acceptance criteria

- [ ] `system_register` has a unique ID, status, intended and prohibited uses, owners, affected people, and review date.
- [ ] `role_assignment` distinguishes ultimate accountability, execution, independent review, consultation, and informed parties.
- [ ] The risk tier has written rationale; the impact assessment contains benefits, non-AI baseline, impact paths, controls, and residual risk.
- [ ] Data have provenance, version, and owner; models, prompts, and tools have versions and owners; the fictional vendor record has a due-diligence snapshot, owner, and exit boundary.
- [ ] Approval permits only a synthetic-data sandbox and binds versions, conditions, expiry, and change triggers.
- [ ] Monitoring metrics have thresholds and actions; incident and retirement plans are executable.
- [ ] `--self-test` passes, all 73 tests pass in normal, `-O`, and warnings-as-errors modes, and output contains no real data, credentials, or compliance claim.

## Hands-on extensions

Copy `SCENARIO` and make three rounds of change: add real users, allow automatic email sending, and switch the hosted model. For each, compare the risk tier, approval result, monitoring, and evidence that must be obtained again. Do not force a proposal through by reducing its severity score; stop directly for unacceptable uses.

You can next add local JSON input and JSON Schema while continuing to use synthetic data, record the framework retrieval date with `source_status`, and create an offline test ID for each risk that cross-references the evaluation report.

## Common mistakes

- A passing script proves only that the teaching data structure satisfies its assertions; it does not prove that a real system is safe, fair, effective, or compliant.
- The risk score is an internal prioritization example, not a legal classification under the EU AI Act or any other region.
- Complete documentation does not demonstrate that controls are implemented. Production evidence must also come from configuration, tests, logs, contracts, and real human decisions.
- A synthetic scenario cannot replace affected-person participation, domain review, or regional legal review.

## Self-assessment and mastery check

- [ ] Can explain which facts produce each governance artifact, who owns it, and when it is updated.
- [ ] Can trace one model change through impact assessment, evaluation, approval, documentation, and monitoring.
- [ ] Can identify the real production evidence missing from the governance pack instead of treating JSON as a certificate.
- [ ] Can design four decision paths: reject release, time-limited pilot, conditional release, and retirement.

## Source baseline and boundary

The project fields are independently organized from the [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/), [NIST AI RMF Playbook](https://airc.nist.gov/airmf-resources/playbook/), [OECD AI Principles](https://oecd.ai/en/ai-principles), and the [OECD framework for reporting AI incidents](https://oecd.ai/en/ai-publications/towards-a-common-reporting-framework-for-ai-incidents), accessed on 2026-07-22. Return to the [[ai-governance/00-index|AI Governance Learning Path]]. This project is not legal, audit, certification, or compliance advice.
