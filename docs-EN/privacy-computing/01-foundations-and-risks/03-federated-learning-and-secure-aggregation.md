---
title: "Federated Learning and Secure Aggregation"
aliases:
  - Federated Learning and Secure Aggregation
  - FL and Secure Aggregation
tags:
  - privacy
  - federated-learning
  - secure-aggregation
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: 隐私计算/01-基础与风险/03-联邦学习与安全聚合.md
translation_source_hash: 2a012bbc8439c6d553530ebf5b549b0dd8aad3072fd6f79610f4b48efd9e8857
translation_route: zh-CN/隐私计算/01-基础与风险/03-联邦学习与安全聚合
translation_default_route: zh-CN/隐私计算/01-基础与风险/03-联邦学习与安全聚合
---

# Federated Learning and Secure Aggregation

## Goal of this lesson

Explain what federated learning (FL) and secure aggregation each do; draw what clients, servers, a single-round update, the participant set, and the final model can see; and analyze non-IID data, dropout, collusion, malicious clients, inference, and model memorization.

## Two different concepts

Federated learning sends a model to the party holding data, computes updates locally, then aggregates them at a server. It reduces centralized movement of raw data, but a server can usually still see updates and the final model can still reveal training information.

Secure aggregation is a family of cryptographic protocols through which a server obtains the aggregate of several client updates rather than each update. It protects visibility of individual inputs under the protocol's stated conditions. It does not automatically provide differential privacy, guarantee that a client input is honest, or limit what the final aggregate or model reveals.

“Using secure aggregation” does not specify semi-honest versus malicious security, or a collusion threshold among server, client, and protocol roles. If a protocol proves input privacy only against an honest-but-curious server, do not extend that conclusion to a malicious server manipulating the participant set, messages, or recovery process.

```text
server distributes model
  → client trains/computes locally
  → (optional: clipping, DP, local validation)
  → secure-aggregation protocol hides individual updates
  → server receives aggregate and updates model
```

## Write the threat model first

At minimum, state:

- Is the server honest, honest-but-curious, or able to deviate maliciously from the protocol?
- How many clients or servers may collude?
- What are the minimum participant count and dropout threshold, and what can recovery reveal?
- Can a client submit poisoned, out-of-bounds, or malformed updates?
- Can a server manipulate participant sets across rounds to differ or isolate one client?
- Who can see updates, aggregates, metrics, the final model, and logs?
- How are keys, identities, device enrollment, versions, and revocation managed?

“Data did not leave the device” describes location, not a complete guarantee.

## Engineering challenges

### Non-IID data and participation bias

Client data distributions, amounts, and online times differ. An average update can favor always-online clients, large datasets, or devices in particular regions. Beyond global results, inspect group or client distributions, dropout, and populations that do not participate.

### Communication and versions

Models are large, networks slow, and devices heterogeneous. Compression, quantization, and multiple local training steps affect convergence and privacy analysis. Clients must verify the model and code version; the server must reject stale, duplicate, or wrong-shaped updates.

### Malicious clients and poisoning

Secure aggregation hides individual updates, which can also reduce the server's ability to detect anomalies. Use contribution clipping, format/range proofs or validation, robust aggregation, participant identity, and isolated experiments. Each control has bypasses and utility trade-offs.

### Leakage over many rounds

Small participant groups, repeated selection of one client, differencing participant sets, or server-customized models can increase inference. Aggregates, training metrics, debug logs, and the final model are all outputs. Secure aggregation cannot repair output that is too granular.

## Combining with differential privacy

A common combination first limits each client or subject's contribution, then adds accounted noise to the aggregate, while secure aggregation reduces the server's chance to see individual updates. The roles differ: contribution bounds control sensitivity, secure aggregation protects visibility during computation, and DP limits the influence of an individual on released results. A combined guarantee must match the threat model, sampling, dropout, and implementation; do not simply add technology names.

## Three-organization joint-training checklist

1. Do all organizations have aligned data purposes and legal or governance bases?
2. What are the identities and trust relationships of clients, coordinator, aggregator, and model recipients?
3. What are the minimum participant count, collusion threshold, dropout, and recovery arrangements?
4. What is the order of update clipping, validation, aggregation, DP, and accounting?
5. How are metrics and model access, and membership, attribute, and inversion attacks evaluated?
6. How are versioning, audit, revocation, incident response, and post-exit data or model handling performed?

## Common misconceptions

- Equating FL with “data stays in-domain, therefore privacy is solved.”
- Equating secure aggregation with DP, or assuming it protects the final model.
- Defending only against a curious server while ignoring client poisoning, collusion, and participant-set manipulation.
- Retaining every per-client update for debugging and thereby bypassing the protocol's goal.
- Inferring properties of your protocol implementation directly from a paper's participant count, performance, or threshold.

## Exercise and self-check

Draw a visibility matrix for joint training by three institutions: which party can see raw data, an individual update, an aggregate, metrics, and the final model? Analyze four cases separately: one client drops out, the server colludes with one client, a malicious client poisons updates, and a group contains only two people.

- [ ] Can distinguish the guarantees of FL, contribution clipping, secure aggregation, robust aggregation, and DP.
- [ ] Can explain why participant sets across rounds change privacy risk.
- [ ] Can address both a curious server and malicious clients.
- [ ] Can evaluate the final model and runtime logs rather than only the location of raw data.

## Next step

Continue by comparing the trust models of [[privacy-computing/02-controls-and-governance/04-mpc-homomorphic-encryption-and-tee|MPC, Homomorphic Encryption, and TEEs]].

## References

- [McMahan et al., Communication-Efficient Learning of Deep Networks from Decentralized Data](https://proceedings.mlr.press/v54/mcmahan17a.html) (AISTATS 2017)
- [Bonawitz et al., Practical Secure Aggregation for Privacy-Preserving Machine Learning](https://eprint.iacr.org/2017/281) (CCS 2017 version; accessed 2026-07-21)
