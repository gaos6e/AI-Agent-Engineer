---
title: "Risk Tiering and Impact Assessment"
aliases:
  - AI Risk Tiering and Impact Assessment
tags:
  - ai-governance
  - risk-assessment
  - impact-assessment
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
lang: en
translation_key: AI治理/01-基础与风险/02-风险分级与影响评估.md
translation_source_hash: 977b48c60b24a7494c862d0bd3ac66b8b32eda7f8365066bf7ced3db24381459
translation_route: zh-CN/AI治理/01-基础与风险/02-风险分级与影响评估
translation_default_route: zh-CN/AI治理/01-基础与风险/02-风险分级与影响评估
---

# Risk Tiering and Impact Assessment

## Goal of this lesson

Use the question “what impact could this system have on whom in this context?” to decide the depth of review and produce a reviewable impact assessment. Identical model capabilities do not imply identical use-case risk: the consequences of an error in meeting summarization and in a benefits-eligibility decision cannot be treated as equivalent.

## Tiers are not legal classifications

An internal risk tier allocates review, testing, and approval resources. A legal classification as prohibited, high-risk, or regulated must be determined separately by qualified people under the applicable text. Do not present a `low/medium/high` field as a compliance conclusion, and do not skip scenario assessment merely because a vendor calls its product “low risk.”

First establish hard gates. A proposal that violates an organizationally unacceptable use, cannot lawfully obtain required data, cannot provide necessary human redress, or cannot be disabled should stop—not have its score “reduced” with more controls. Tier the remaining proposals along these dimensions:

- **Severity**: How seriously could life and health, rights, employment, education, credit, public services, property, privacy, or reputation be affected?
- **Conditions and likelihood**: How likely is harm in ordinary use, foreseeable misuse, attack, data drift, or vendor change? How strong is the evidence?
- **Scale and exposure**: How many people are affected, how often, and for how long? Are vulnerable groups or people with little practical voice affected?
- **Reversibility and redress**: Can an error be found promptly, reversed, compensated, appealed, and restored?
- **Autonomy and reliance**: Is the output a reference, default option, ranking, decision, or automated action? Does a person have the time, information, and authority to override it?
- **Data and connections**: Does it use sensitive data, children's data, or cross-domain data, or connect to write-capable tools or public-distribution channels?
- **Uncertainty**: A new use, unrepresentative data, missing tests, or an opaque supply chain should itself increase review intensity.

## Eight steps for an impact assessment

1. **Purpose and boundary**: State the objective, prohibited uses, users, environment, frequency, inputs, outputs, and non-AI alternative.
2. **Stakeholders**: Identify users, directly and indirectly affected people, groups that find it hard to appeal, operators, and third parties.
3. **Expected benefit and baseline**: Compare with the current human or rule-based process; do not treat “using AI” as the benefit itself.
4. **Impact paths**: For ordinary errors, bias, overreliance, misuse, attack, privacy, safety, and vendor failure, write “cause → output/action → consequence.”
5. **Subgroups and accessibility**: Check whether average metrics conceal failures for smaller groups, languages, disabilities, or edge cases.
6. **Controls and evidence**: For each control, record its owner, test, threshold, failure action, and evidence location.
7. **Residual risk and decision**: State what may still happen after controls, then let an authorized person choose rejection, experiment, conditional release, or acceptance.
8. **Review triggers**: Redo the relevant parts when the purpose, population, region, model, data, tools, autonomy, threshold, or incident changes.

An impact assessment is not a document completed once before release. ISO/IEC 42005:2025 provides guidance for AI-system impact assessment, but neither its official overview nor this lesson's template replaces the full standard, regional assessment duties, or professional judgment. A production system should feed runtime evidence, complaints, incidents, and material changes back into the assessment and the residual-risk decision.

## Simple without pretending to be complete

A severity × likelihood matrix can help prioritize work, but retain the written rationale, evidence, and uncertainty behind every score. In high-impact domains, set an override such as “maximum severity is at least high risk” so an optimistic low probability cannot dilute catastrophic impact. Scores help queue work; they do not replace judgment.

For example, an internal FAQ search that returns only source passages and whose mistakes employees can correct can usually start with lighter review. Candidate ranking for hiring, even with similar measured accuracy, affects employment opportunities, subgroup differences, automated bias, and redress; it needs more rigorous assessment and independent approval.

## Exercise and self-check

Assess “meeting summarization” and “scholarship-candidate ranking” separately. For each, write the affected people, worst credible consequence, reversibility, human oversight, three evidence items, and review triggers. Do not provide only a score.

- [ ] Can trace a risk tier to a scenario and its consequences.
- [ ] Can assess benefits, the non-AI baseline, and impacts on different groups together.
- [ ] Can distinguish pre-control risk, controls, and residual risk.
- [ ] Know that an internal matrix cannot replace regional legal classification.

## Next step and source baseline

Continue with [[ai-governance/02-controls-and-governance/03-data-model-and-vendor-governance|Data, Model, and Vendor Governance]]. Sources were accessed on 2026-07-21. See the Map, Measure, and Manage functions of the [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/), the [ISO/IEC 42005:2025 overview](https://www.iso.org/standard/42005), and the [Government of Canada Algorithmic Impact Assessment and Directive](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592). The Canadian tool applies only within its stated scope; its question design can inform work elsewhere but cannot be transplanted as a legal conclusion. For the scope of a fundamental-rights impact assessment for certain EU deployers, see Article 27 of [Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj); confirm applicability timing against the current legislative status in [[ai-governance/02-controls-and-governance/07-regulations-standards-and-regional-review|Regulations, Standards, and Regional Review]].
