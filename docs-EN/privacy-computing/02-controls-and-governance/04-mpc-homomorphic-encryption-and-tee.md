---
title: "MPC, Homomorphic Encryption, and TEEs"
aliases:
  - MPC FHE TEE
  - Privacy-enhancing cryptography and confidential computing
tags:
  - privacy
  - mpc
  - homomorphic-encryption
  - tee
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
lang: en
translation_key: 隐私计算/02-控制与治理/04-MPC同态加密与TEE.md
translation_source_hash: 8ec2be98474b0a4322c1918a0ffe25a10270e828932cfdeca556b530124ebf9d
translation_route: zh-CN/隐私计算/02-控制与治理/04-MPC同态加密与TEE
translation_default_route: zh-CN/隐私计算/02-控制与治理/04-MPC同态加密与TEE
---

# MPC, Homomorphic Encryption, and TEEs

## Goal of this lesson

Compare MPC, HE/FHE, and TEEs by participants, keys, collusion, input/output visibility, integrity, and hardware trust. Identify unresolved boundaries around performance, side channels, access patterns, malicious input, and key operations.

## Do not start with a technology name

First write the function and threat model. Who has input, who needs output, who may collude or deviate from protocol, whether inputs, outputs, the function, or access patterns must be hidden, whether hardware can be trusted, and how much latency and operational complexity are allowed? If removing a field or calculating local statistics at the data holder serves the purpose, a complex cryptographic protocol may not be necessary.

## Secure multi-party computation (MPC)

MPC allows several parties to jointly compute a function while limiting what each can learn about others' inputs under the protocol's security definition. Intuitively, inputs can be split into several shares. Fewer than a threshold of shares cannot recover the secret; the protocol operates on shares and reconstructs an approved output.

The real guarantee depends on semi-honest or malicious adversaries; corruption and collusion threshold; whether an honest majority exists; fairness and liveness; who can abort; network and synchrony assumptions; and protocol and implementation. Hiding inputs does not make output safe. If a function outputs “whether this person has a disease,” correct protocol execution still leaks that fact. A malicious participant may also provide false data, so input-validity checks, range proofs, or governance controls are needed.

## Homomorphic encryption (HE/FHE)

HE allows specified computation over ciphertexts, and the key holder decrypts the result. FHE aims to support any expressible computation. It can delegate computation to a party that should not see plaintext and often reduces multi-round interaction, but requires attention to:

- supported numeric or circuit forms, approximation precision, noise growth, and parameters;
- computation, memory, ciphertext expansion, and latency;
- key generation, custody, rotation, threshold decryption, and disaster recovery;
- result integrity—encrypted inputs do not automatically prove that a server executed the approved program; and
- access patterns, metadata, output, and application bypasses.

As of 2026-07-21, NIST PEC describes FHE as an actively tracked area for future standardization or recommendations. Do not market every solution as an existing uniform NIST standard. Have cryptographic experts review library parameters against current implementations.

## Trusted execution environments (TEEs)

TEEs and confidential computing use hardware isolation to protect code and data in use, and remote attestation lets a verifier check particular hardware and software measurements. They can host more general existing programs, but move trust to the CPU and firmware, vendor roots, attestation service, loaded code, cloud control plane, and patch process.

Remote attestation is meaningful only when you verify the correct measurement, configuration, freshness, and certificate chain. Side channels, rollback, I/O, network, access patterns, host denial of service, and implementation flaws still need handling. A malicious program inside a TEE can still send a secret as a “legitimate output,” so code review, egress policy, and output minimization remain necessary.

## Comparison table

| Dimension | MPC | HE/FHE | TEE |
| --- | --- | --- | --- |
| Primary trust | Protocol assumptions and no collusion below threshold | Key holder, parameters, implementation | Hardware/firmware/attestation chain and loaded code |
| Interaction | Often requires multiple parties online and many rounds | Computing party can operate non-interactively | Similar to ordinary service interaction |
| Generality | Depends on protocol and framework | Limited by expressible computation and performance | Closer to general programs |
| Main cost | Communication, coordination, dropout | Computation, memory, ciphertext expansion | Hardware availability, attestation, and patch operations |
| Does not automatically guarantee | Output privacy or input authenticity | Computation integrity, access patterns, or output privacy | Benign program, side-channel resistance, or output privacy |

## Composition and integrity

MPC, HE, and TEEs often reduce visibility of inputs or intermediates to some parties during computation, but the precise guarantee depends on protocol, adversary model, keys or hardware, and implementation. Some MPC protocols also provide malicious security or result integrity; others cover only semi-honest confidentiality. HE ordinarily does not prove that computation is correct. TEEs depend on the attestation chain and loaded code. DP can limit a released result's influence from an individual. Zero-knowledge proofs can show that an input or computation satisfies a relation in some designs. Composition is not “strength added together”: each layer's subjects, assumptions, parameters, failure modes, and outputs must be consistent in one end-to-end data flow.

## Exercise and self-check

Review separately: two banks computing the intersection of fraud lists; cloud computation of encrypted risk scores; and a general sensitive analysis in the cloud. For each, state inputs/outputs, candidate technology, keys or attestation, collusion, integrity, performance, and metadata that can still leak. Propose at least one simpler minimization alternative.

- [ ] Can state where MPC, HE/FHE, and TEEs each place trust.
- [ ] Can distinguish confidentiality, integrity, availability, and output privacy.
- [ ] Can explain why remote attestation, thresholds, and key management are part of the protocol guarantee.
- [ ] Can reject “privacy computing” marketing claims without a threat model, version, and benchmark.

## Next step

Proceed to [[privacy-computing/02-controls-and-governance/05-pet-selection-and-composition-boundaries|PET Selection and Composition Boundaries]] to create a reviewable decision record.

## References

- [NIST Privacy-Enhancing Cryptography](https://csrc.nist.gov/Projects/pec) (page updated 2026-07-01; accessed 2026-07-21)
- [NIST PEC: Fully Homomorphic Encryption](https://csrc.nist.gov/Projects/pec/fhe) (accessed 2026-07-21)
- [NIST PEC: MPC and Threshold Schemes](https://csrc.nist.gov/Projects/pec/threshold) and [NIST IR 8214C](https://csrc.nist.gov/pubs/ir/8214/c/final) (First Call final, January 2026; it establishes an entry point for reference-material collection and evaluation, not a set of already standardized MPC/FHE/ZKP solutions; accessed 2026-07-21)
- [Confidential Computing Consortium: About](https://confidentialcomputing.io/about/) (accessed 2026-07-21)
