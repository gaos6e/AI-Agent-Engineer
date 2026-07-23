---
title: "PET Selection and Composition Boundaries"
aliases:
  - PET Selection
  - Privacy-enhancing technology selection
tags:
  - privacy
  - architecture
  - decision-making
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: 隐私计算/02-控制与治理/05-隐私技术选型与组合边界.md
translation_source_hash: 9086fdbfed3b81346ac43419fbae1ef05c2540231dff9bf1c4efbf5c1ed4ac06
translation_route: zh-CN/隐私计算/02-控制与治理/05-隐私技术选型与组合边界
translation_default_route: zh-CN/隐私计算/02-控制与治理/05-隐私技术选型与组合边界
---

# PET Selection and Composition Boundaries

## Goal of this lesson

Derive candidate PETs from purpose, data actions, parties, and attackers rather than product names; state each technique's guarantees and unprotected scope; compare performance, utility, operations, and evidence cost; and reach a decision that can be rolled back.

## Start with the privacy problem

First complete one verifiable statement:

> Under which assumptions about participants and attackers, we want whom to be unable to learn what information about whom from which observations, while still obtaining which necessary output.

Then ask whether you can avoid collection, collect less, reduce granularity, compute locally, shorten retention, or restrict output. A PET is not a license to collect excessive data.

## Privacy goals and candidate technologies

| Privacy goal | Common candidates | Still requires attention |
| --- | --- | --- |
| Reduce holding and linkage risk | Minimization, aggregation, de-identification, access and retention controls | External linkage, free text, output, and deletion |
| Quantify a subject's influence on statistics | Differential privacy | Adjacency, contribution, parameters, composition, implementation, and utility |
| Train without centralizing raw data | Federated learning or local computation | Updates, participant set, final model, and malicious clients |
| Hide a single party's update | Secure aggregation | Multiple rounds, collusion, dropout, input authenticity, and final aggregate |
| Compute a joint function among parties | MPC or PSI | Protocol and corruption model, output, performance, and liveness |
| Compute ciphertexts in the cloud | HE/FHE | Operations and precision, performance, keys, integrity, and metadata |
| Protect general computation in use | TEE | Hardware and attestation trust, side channels, code, and output |
| Prove a claim without revealing a witness | ZKP | Correct relation/circuit, parameters, implementation, public inputs, and metadata |

The table generates candidates; it does not select one automatically.

## A seven-step decision method

1. **Purpose and subjects**: state intended use, non-goals, the individual or organizational contribution unit, and rights/governance constraints.
2. **Data flow**: list collection, training, inference, output, logs, models, backups, and retirement paths.
3. **Threat model**: party trust, malicious or semi-honest behavior, collusion, dropout, external auxiliary information, and side channels.
4. **Guarantee statement**: precisely state who and which input/output are protected, under which assumptions and parameters.
5. **Candidate prototypes**: compare with the simplest baseline, measuring latency, throughput, memory, network, accuracy, failure recovery, and operations.
6. **Validation evidence**: protocol or product version, parameters, code source, review, tests, attestation chain, accounting, and attack evaluation.
7. **Responsibility and exit**: residual-risk owner, monitoring, incident response, key revocation, vendor alternative, and rollback.

## Combined guarantees need to be proved again

- **MPC + DP**: MPC reduces raw-input exposure; DP limits output inference. DP still must be implemented over the correct aggregate and contribution bounds.
- **FL + secure aggregation + DP**: respectively address data location, individual-update visibility, and release influence. Dropout, sampling, and multiple rounds change the overall analysis.
- **TEE + DP**: a TEE protects mechanism data and keys during execution, but you still need to establish the loaded code, parameters, and output are correct. DP does not protect non-DP log bypasses.
- **De-identification + controlled access**: both reduce practical risk, but they do not automatically make linkable data anonymous.

The weakest end-to-end boundary determines the result. If public output is too granular, even very strong cryptography during computation cannot help; if an administrator credential is stolen, DP statistics do not protect the raw database.

## Decision-record template

Record: purpose and non-goals; subjects and contribution; assets; parties; attackers; data flow; candidates and baseline; guarantee; unprotected scope; protocol/product/parameter versions; performance and utility benchmarks; keys/identities/attestation; failure behavior; tests and review; unresolved compliance matters; residual risk and owner; review triggers; and exit plan.

Vendor phrases such as “zero trust,” “confidential AI,” or “military-grade encryption” are not guarantees. Request protocol, threat model, version, parameters, audit scope, deployment configuration, and reproducible evidence.

## Common errors

- Procuring a product first and searching for a privacy problem to justify it.
- Comparing only theoretical strength rather than configuration errors and bypasses caused by implementation complexity.
- Combining “encrypted at rest/in transit/in use” into one phrase without saying who can see keys and outputs.
- Inferring anonymity or lifecycle compliance from one component's guarantee.
- Having no downgrade, revocation, rollback, or vendor-exit path.

## Exercise and self-check

For two hospitals jointly publishing disease statistics, write two designs: A uses only minimization, local aggregation, and controlled sharing; B uses MPC + DP. Compare trust, output, attacks, utility, performance, keys, operations, validation, and failure recovery item by item. Explain under what conditions A is actually more appropriate.

- [ ] Can map a privacy goal to candidate technologies rather than brands.
- [ ] Can state “what it protects / what it does not protect” for every candidate.
- [ ] Can model parties, outputs, and bypasses again after composition.
- [ ] Can treat performance and operational feasibility as part of whether a guarantee can be realized.

## Next step

Use [[privacy-computing/02-controls-and-governance/06-privacy-evaluation-and-leak-response|Privacy Evaluation and Leak Response]] to check whether a selection holds in the real implementation.

## References

- [NIST PEC Tools](https://csrc.nist.gov/Projects/pec/pec-tools) (accessed 2026-07-21)
- [NIST: Privacy-Enhancing Cryptography to Complement Differential Privacy](https://www.nist.gov/blogs/cybersecurity-insights/privacy-enhancing-cryptography-complement-differential-privacy) (accessed 2026-07-21)
- [NIST SP 800-226](https://csrc.nist.gov/pubs/sp/800/226/final) (final, March 2025)
