---
title: "Regulations, Standards, and Regional Review"
aliases:
  - AI Regulation Standards Jurisdiction Review
tags:
  - ai-governance
  - regulation
  - standards
  - jurisdiction
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: AI治理/02-控制与治理/07-法规标准与地区复核.md
translation_source_hash: 62780d8c27859ed4124493098b0081d0abbe982aec61b2c395033dda377975e3
translation_route: zh-CN/AI治理/02-控制与治理/07-法规标准与地区复核
translation_default_route: zh-CN/AI治理/02-控制与治理/07-法规标准与地区复核
---

# Regulations, Standards, and Regional Review

## Goal of this lesson

Distinguish voluntary risk frameworks, international principles, management-system standards, organizational policies, and legally binding rules, and establish an engineering interface for review by role, intended use, and region. A governance team's job is to turn authoritative conclusions into actionable controls and evidence; it is not to act as legal counsel on its own.

## Do not conflate five kinds of material

- **Law and regulatory rules**: applicability depends on jurisdictional connection, actor role, intended use, industry, data, and effective date; primary texts, implementing rules, and competent-authority interpretations take priority.
- **Standards**: state requirements or guidance and may be referenced by contracts, certification schemes, or regulation; purchasing a standard or obtaining certification does not automatically demonstrate compliance for a particular system.
- **Risk frameworks and playbooks**: provide common language and recommendations, normally tailored to context, but are not legal classifiers.
- **Principles and recommendations**: provide value and policy direction that must be turned into roles, processes, controls, and evidence.
- **Organizational policies**: may be stricter than external minimums and must state their scope, decision rights, and exceptions.

The same system is often simultaneously affected by data-protection, consumer, anti-discrimination, intellectual-property, cybersecurity, product-safety, labor, medical, financial, and other existing rules. Do not search only for laws whose title contains “AI.”

## Current official baseline (as of 2026-07-22)

### NIST AI RMF

[NIST AI RMF 1.0](https://doi.org/10.6028/NIST.AI.100-1) is a voluntary, cross-sector, use-case-neutral risk-management resource organized around Govern, Map, Measure, and Manage throughout the lifecycle. The [official NIST page](https://www.nist.gov/itl/ai-risk-management-framework) explicitly says that 1.0 is being revised and that the Playbook will be updated afterward. A project may identify the specific adopted version and entries, but must not make the blanket claim “NIST compliant.” For supplementary generative-AI risks and actions, see [NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1).

### OECD AI Principles

The [OECD AI Principles](https://oecd.ai/en/ai-principles) were first adopted in 2019 and updated in May 2024. They emphasize inclusive growth and well-being, human rights and fairness, transparency and explainability, robustness and safety, and accountability. See the formal recommendation in [OECD/LEGAL/0449](https://legalinstruments.oecd.org/en/instruments/OECD-LEGAL-0449). They help calibrate impact assessment and transparency goals, but do not replace obligations in a particular region.

### ISO/IEC standards

[ISO/IEC 42001:2023](https://www.iso.org/standard/42001) is a published requirements standard for AI management systems. [ISO/IEC 42005:2025](https://www.iso.org/standard/42005) is published guidance for AI-system impact assessment. [ISO/IEC 42006:2025](https://www.iso.org/standard/42006) adds requirements for bodies auditing and certifying AI management systems, supplementing ISO/IEC 17021-1. The subject of 42006 is a certification or audit body, so an AIMS certification must not be described as safety or compliance certification of a particular AI system, model, product, or service. Official summaries cannot replace the copyright-protected complete standards. For implementation, audit, or certification, lawfully obtain the applicable version and have qualified people determine scope and evidence.

### EU AI Act

The [official text of Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) is the starting point for checking the original regulation's articles, roles, and scope, but it alone does not represent the complete timeline after subsequent amendments. The following is a **regulatory-status snapshot as of 2026-07-22**, not a compliance conclusion for any organization:

| Layer | Verified status | What engineering must not omit because of this |
| --- | --- | --- |
| Base Regulation | Entered into force on 2024-08-01; prohibitions, definitions, and AI-literacy obligations apply from 2025-02-02; governance rules and GPAI-model obligations apply from 2025-08-02. | You must still determine the actual provider, deployer, and other roles, the system's use, and obligations under other sectoral law. |
| General application date | The European Commission's current page states that most rules apply on **2026-08-02**; this snapshot predates that date. | Do not write “currently applicable” for a rule that is only about to apply, and do not treat a date as automatic classification of any use case. |
| 2026 AI Omnibus amendment | [PE 30 2026 REV 1](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=consil%3APE_30_2026_REV_1) is available through EUR-Lex. The Council announced final adoption on 2026-06-29 and said it would enter into force on the third day after publication in the *Official Journal of the European Union*. | The PE text, press release, and Commission explanation are not consolidated law that can replace the Official Journal on their own. Preserve the OJ/ELI, publication date, and consolidated text current at the time in the decision record. |
| High-risk-system timing | The Council announcement lists 2027-12-02 for standalone high-risk systems and 2028-08-02 for high-risk systems embedded in regulated products; the Commission's current policy page lists the same dates. | The Commission's standardization page presents these as latest dates and says support tools may affect earlier application. The Official Journal, Commission decisions, latest guidance, and applicable sector rules take priority over this table. |

Therefore, preserve “source status” separately from “legal conclusion”: `checked_at`, primary text or ELI, version or consolidation date, unresolved questions, the person responsible for confirmation, and the next review trigger. The European Parliament completed first-reading adoption on [2026-06-16](https://oeil.europarl.europa.eu/oeil/en/document-summary?id=1905596). The Council's [2026-06-29 announcement](https://www.consilium.europa.eu/en/press/press-releases/2026/06/29/artificial-intelligence-council-gives-final-green-light-to-simplify-and-streamline-rules/) and the Commission's [AI Act timeline](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) are first-party entry points for locating current status. If they conflict with the Official Journal or a later consolidated text, follow the latter.

## Regional and applicability review sheet

Maintain the following record for every system, with confirmation by authorized professionals:

1. What are the actual roles in development or provision, deployment or use, import or distribution, employment, and data control or processing?
2. Where are the organization, infrastructure, vendors, users, affected people, and output use located?
3. Does the intended use involve specially scrutinized domains such as employment, education, credit, health care, public services, biometrics, or safety products?
4. What personal, sensitive, child, or protected information is processed? Is it cross-border, or used for training or monitoring?
5. What are the official name, version, provision, status, effective date, authority, and interpretive source of each applicable material?
6. Which control, evidence item, owner, and deadline maps to an obligation? Which conclusions still need legal advice?
7. Which changes could alter role, classification, regional connection, or application timing, and when will review recur?

Retain the retrieval date and links, but a dynamic web page is not a substitute for a primary-text snapshot or professional judgment. When sources conflict, escalate the conflict and unresolved status rather than choose the most permissive interpretation.

## Exercise and self-check

Assume a team in China procures a US-hosted model and provides EU customers with assisted ranking for recruitment. Do not give a direct compliance conclusion. Instead, list the roles, regional connections, employment use, data, vendor, primary texts to check, and professionals responsible for confirmation. Explain why the model's location is not the only relevant factor.

- [ ] Can distinguish frameworks, principles, standards, internal policies, and legal rules.
- [ ] Every time-sensitive conclusion records status, version or date, and a first-party entry point.
- [ ] Can leave legal conclusions to qualified people, then turn them into engineering controls and evidence.
- [ ] Do not claim system compliance from “adopting NIST/ISO” or a vendor certification.

## Next step and source baseline

Finish with [[ai-governance/03-project-and-self-assessment/08-project-offline-ai-governance-pack|Project: Offline AI Governance Pack]]. This page's sources were accessed on 2026-07-22. Application timing, official publication, and amendment status are highly time-sensitive. Before any production decision, revisit the first-party sources above. This lesson is not legal advice.
