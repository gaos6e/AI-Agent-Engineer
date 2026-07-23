---
title: "When to Use AI and Select a System Shape"
tags:
  - ai-agent-engineer
  - ai-foundations
  - engineering-decisions
aliases:
  - AI solution selection
  - Should we use AI?
content_origin: original
content_status: validated
source_checked: 2026-07-22
lang: en
translation_key: AI基础认知/02-工程决策/08-何时使用AI与系统形态选择.md
translation_source_hash: 7d5d95313c9f93d129a50c8ec50b2575f1869a3ddaa75ee333de9d8299d517b0
translation_route: zh-CN/AI基础认知/02-工程决策/08-何时使用AI与系统形态选择
translation_default_route: zh-CN/AI基础认知/02-工程决策/08-何时使用AI与系统形态选择
---

# When to Use AI and Select a System Shape

## Learning objective

After this lesson, you should be able to start from a business outcome rather than a popular technology, compare no AI, rules, traditional machine learning, one LLM call, a fixed workflow, and a controlled Agent, and create an evidence-based record of the solution choice.

## The first step is not choosing a model, but defining the outcome

“Build an intelligent customer-service system” and “add an Agent” are solution slogans, not requirements. First answer:

- Who encounters what problem in which situation?
- How does the current process work, and where are its cost and errors?
- What output is expected, and how will it be judged correct?
- Which content is explicitly out of scope or which actions are forbidden?
- Who is affected by an error, and can it be detected, recovered from, or appealed?
- What do people do in input, review, execution, and accountability?

“Generate high-quality responses” starts to have verifiable boundaries only when rewritten as something like: “Generate evidence-backed drafts from approved policy; do not promise refunds; hand off to a human when evidence is missing.”

## Ask five questions first

1. **Can stable rules solve it?** File renaming, field validation, and fixed amount limits should usually begin with rules.
2. **Are inputs open and diverse?** A model may create net benefit only when language, vision, speech, or statistical inference is needed.
3. **Are representative examples and decision criteria available?** If correct and incorrect cannot be defined, improvement cannot be proven.
4. **Are errors controllable?** Errors that cannot be detected, reversed, or tolerated at high impact require a narrower scope, mandatory human involvement, or no AI.
5. **Does benefit cover full cost?** Count not only call fees, but also data, evaluation, monitoring, security, human review, vendors, and maintenance.

If question 3 or 4 cannot be answered, improve requirements and controls before launching anything.

## Six system shapes

| Shape | Suitable situation | Advantage | Main limitation |
| --- | --- | --- | --- |
| Leave the system unchanged / improve the process | The problem comes from responsibility, interface, or process rather than information-processing capability | Lowest cost and risk | Does not add automated inference |
| Rule-based program | Conditions are stable and outputs can be defined precisely | Reproducible, easy to test, low cost | Poor fit for open expression |
| Traditional machine learning | Historical examples exist and the task is classification, prediction, or ranking | Clear metrics; inference is usually light | Data drift and feature maintenance |
| One LLM call | One language task such as summarization, extraction, or rewriting | Fast to develop; unified interface | Factuality, format, and cost need validation |
| Fixed workflow | Steps and branches can be enumerated beforehand | Easy to audit; clear permissions | Poor fit for open paths |
| Controlled Agent | The next step depends on environmental feedback and the path is hard to enumerate | Can handle dynamic tasks | Larger variation, cost, and attack surface |

These shapes can be combined. For example, rules can validate identity and fields first, an LLM can extract candidates, a fixed workflow can call a read-only API, and a human can approve the final step. A combination does not imply that an Agent is needed.

## Narrow the scope with an autonomy ladder

The same requirement can be validated progressively from lower to higher autonomy:

1. **Provide information only:** search and show sources.
2. **Generate a draft:** a person decides whether to use it.
3. **Propose a tool action:** show arguments and impacts.
4. **Execute in a sandbox:** isolate and roll back side effects.
5. **Automate low-risk actions:** use allowlists, limits, and audit.
6. **Take high-impact actions:** require approval by qualified people, or keep execution manual.

Move upward only when the lower level cannot meet the goal and evidence shows the new risk can be controlled. Autonomy is not a maturity score.

## Compare net value, not just a model score

Compare at least these dimensions:

| Dimension | Question |
| --- | --- |
| Task quality | How much does it improve on the current process and simple baseline? |
| Coverage and long tail | Which languages, formats, users, and exceptions still fail? |
| Risk | Are errors visible, reversible, and appealable? |
| Data | Is its use authorized, and does it contain sensitive information? |
| Permissions | What can the system read or write, and whom does it represent? |
| Operations | How do latency, availability, rate limits, dependencies, and degradation work? |
| Cost | What are call, engineering, human, evaluation, and incident costs? |
| Replaceability | Can the system fall back if a vendor, model, or terms change? |

“A model scores higher on a benchmark” answers only a small part of this, and usually not on your data and process.

## Decision-record template

```text
Problem and target users:
Current process and baseline:
Decidable success/failure:
Candidate shapes: rules / ML / LLM / workflow / Agent
Reasons for choosing and not choosing:
Allowed inputs and outputs:
Forbidden actions and explicit non-goals:
Main risks and affected people:
Human responsibilities and appeals:
Offline evidence and minimum thresholds:
Pilot scope:
Fallback and exit conditions:
Owner, approver, and review date:
```

“Do not choose an Agent because the path is fixed and writes are high-risk” is also a valuable engineering decision.

## Example: Meeting Action-Item Assistant

The candidate task is to extract tasks, owners, dates, and source evidence from meeting records.

- A rules baseline can recognize explicit date and responsibility patterns.
- One LLM call can handle open expression, but output must be validated against a schema and source evidence.
- A fixed workflow can segment, extract, validate, and request human confirmation in sequence.
- There is no current need to choose external actions from intermediate feedback, so a full Agent adds unnecessary permissions and complexity.
- The first version produces drafts only; it neither sends messages nor creates tasks.

The selection is not based on “the LLM is smarter,” but on whether the candidate improves correct coverage on real examples over a rules baseline while retaining evidence and human gates.

## Common misconceptions

| Misconception | Correction |
| --- | --- |
| “More AI features create more competitiveness.” | Implement only capabilities that create verifiable net value. |
| “Build the prototype first and consider risk later.” | Define data, permissions, and forbidden actions during prototyping. |
| “A human in the loop makes it safe.” | The person needs time, evidence, ability, and veto power. |
| “Workflows are not advanced enough.” | Fixed paths are often more stable and auditable than autonomous Agents. |
| “Choosing a famous vendor transfers responsibility.” | The deployer still must evaluate the specific use, integration, and impacts. |

## Exercise

Original requirement: “Let AI automatically read résumés and select the best people.”

1. Write at least eight questions that must be clarified.
2. Identify affected people and unacceptable consequences.
3. Give a no-AI baseline.
4. Narrow the scope to a low-risk assistive feature.
5. Compare rules, LLM summarization, a fixed workflow, and automatic ranking.
6. Define human responsibilities, appeals, and shutdown conditions.

A more conservative scope is to generate a structured summary only from candidate-authorized fields, leaving missing fields blank; do not rank or reject automatically; require hiring staff to inspect original materials and record their decision. This still needs validation for bias, privacy, and accessibility.

## Self-check

1. Why can “uses AI” not be an acceptance criterion?
2. When are rules better than a model?
3. What is the key difference between a fixed workflow and an Agent?
4. Why should the autonomy ladder rise one level at a time?
5. Why is vendor replacement part of solution selection?

## Scope and next step

This lesson covers solution selection before a go/no-go decision, not release steps. Failure hypotheses come from [[ai-foundations/02-engineering-decisions/07-capability-boundaries-and-failure-modes|Capability Boundaries and Failure Modes]]. Once the scope is chosen, continue with [[ai-foundations/02-engineering-decisions/09-from-prototype-to-launch-and-exit|From Prototype to Launch and Exit]].

## References

Accessed **2026-07-22**.

- [OECD: Explanatory memorandum on the updated definition of an AI system](https://oecd.ai/en/ai-publications/explanatory-memorandum-on-the-updated-oecd-definition-of-an-ai-system)
- [NIST AI Risk Management Framework 1.0](https://doi.org/10.6028/NIST.AI.100-1)
- [NIST Generative AI Profile, NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1)
