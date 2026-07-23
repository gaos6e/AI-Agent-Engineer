---
title: "Data Minimization and De-identification"
aliases:
  - Data Minimization and De-identification
  - Privacy-engineering foundations
tags:
  - privacy
  - data-minimization
  - de-identification
source_checked: 2026-07-22
content_origin: original
content_status: dynamic
lang: en
translation_key: 隐私计算/01-基础与风险/01-数据最小化与去标识.md
translation_source_hash: 3160f2b4482e6a734b45bfc835aed1efe0c940b728789c81e13cb07a183e8415
translation_route: zh-CN/隐私计算/01-基础与风险/01-数据最小化与去标识
translation_default_route: zh-CN/隐私计算/01-基础与风险/01-数据最小化与去标识
---

# Data Minimization and De-identification

## Goal of this lesson

Justify necessity field by field from an explicit purpose; distinguish anonymity, de-identification, and pseudonymization; identify linkage attacks through quasi-identifiers; and extend minimization, retention, and deletion to logs, embeddings, models, caches, and backups.

## The strongest privacy control is not holding the data

Cryptographic techniques can protect only data that still needs processing. Data never collected cannot leak through a database, log, model, or vendor. Begin design by answering:

1. What explicit purpose is being served, and for whom?
2. Why is each field necessary for that purpose, and is a less granular alternative available?
3. Between which systems, people, models, and vendors does the data flow?
4. How long is it retained, what triggers deletion, and how will copies be shown to have been handled too?
5. What output will be released, and can auxiliary external data increase inference ability?

“It may be useful later” and “the model may perform better” are not sufficient purposes. A changed purpose needs new approval and assessment, not an unlimited expansion of original consent.

## Data categories and risk

| Category | Examples | Risk |
| --- | --- | --- |
| Direct identifiers | Name, account number, phone number | Can be directly linked to a person |
| Quasi-identifiers | Postal code, age, time, occupation, rare event | Can re-identify when combined with external data |
| Sensitive attributes | Health, finance, biometrics, precise location | Disclosure can cause serious harm even without a name |
| Free text or media | Email, medical record, recording, image | Identifiers can occur anywhere, including metadata |
| Derived data | Embeddings, scores, profiles, labels | Can encode source information and affect people |

Specific legal definitions vary by jurisdiction and context. This table supports engineering threat modeling; it is not a legal classification conclusion.

## Three easily conflated terms

- **Pseudonymization**: replace direct identifiers with a token while a mapping or reconnectable path remains. It supports internal separation and least privilege, but the data still relate to a person.
- **De-identification**: use technical and organizational measures to reduce identification risk. The guarantee depends on the data, auxiliary information, recipient, and use constraints.
- **Anonymous**: a stronger conclusion that data cannot reasonably be related to a person in a particular legal or risk context. Do not claim it merely because names were removed.

NIST IR 8053 emphasizes that de-identification risk must be evaluated with the data, release model, and information available to an attacker. A combination of postal code, date of birth, and sex—or a rare event—may be unique. Time, trajectories, and writing style can also be quasi-identifiers.

## A de-identification workflow

### 1. Build a field-to-purpose table

Record field, source, purpose, classification, necessity, granularity, recipients, retention period, outputs, and alternatives. Delete unnecessary fields before discussing transformations.

### 2. Transform and isolate

Remove direct identifiers; generalize dates, locations, and ages; suppress rare combinations; inspect free text, media, and metadata separately; and physically or logically isolate the mapping table from analytical data with different identities and audit.

### 3. Assess by release model

An adversary's capability differs across controlled internal access, partner sharing, and public download. Simulate linkage, differencing, small-group, and membership inference. Record auxiliary-data assumptions, failed outcomes, and residual risk. One unsuccessful attack does not prove anonymity.

NIST SP 800-188 further places release models, measurable de-identification objectives, disclosure review, and re-identification research in one governance process. It directly addresses US government datasets and cannot be transplanted as a legal standard for other organizations or regions. Its useful lesson is to choose a sharing/query/controlled-environment model first and validate risk against it—not to use a fixed threshold.

### 4. Apply use and output constraints

Least privilege, purpose limitation, query review, re-identification prohibition, minimum group size, output checks, contracts, and incident response together reduce risk. Management controls cannot make high-risk raw public data “anonymous,” but they change the actual threat model.

### 5. Delete through the lifecycle

The deletion scope includes the primary database, object storage, temporary files, logs, caches, vector indexes, evaluation sets, fine-tuning data, model checkpoints, and recoverable backups. When a model or embedding encodes the information, a deletion request may need rebuilding, retraining, or an explicit statement of the technical limitation. Retain deletion jobs, coverage, and sampling-verification evidence, not unnecessary original data.

## RAG, Agents, and propagation of deletion and authorization

RAG splits one source into original text, parsed elements, chunks, embeddings, index generations, caches, citations, and runtime records. Therefore, neither “the vector was deleted” nor “the source used to be accessible” demonstrates that a current read is lawful. At ingestion, bind source and revision, tenant or data scope, purpose, permission, and ACL to a traceable chunk. At query time, a trusted host resolves subject, tenant, and authorization revision first, then restricts the visible set before scoring. Display-layer filtering after retrieval lets caches, candidate sets, or fallback paths cross a boundary that should apply before retrieval.

Revocation, deletion, or a source tombstone should invalidate or place under an explicit retention/rebuild process old chunks, index generations, retrieval caches, citations, Agent memory references, and regenerable evaluation fixtures. A deletion ticket must record whether every copy type is deleted, expired, awaiting rebuild, or continuing under lawful retention. Do not promise immediate clearing of models or backups that cannot be demonstrated. A model should receive only authorized, purpose-minimized segments. Audit with controlled references, classifications, and summaries rather than copying source text into a general trace.

A source hash, document ACL, or “comes from the internal knowledge base” cannot replace current object-level authorization. If retrieved content later influences Tool Calling, the executor must still recheck subject, object, purpose, and destination. The offline reference model in [[rag/09-project-offline-provenance-from-source-to-citation|Source-to-Citation Evidence Chain]] demonstrates the contracts of ACL-before-score, generations, and tombstones, but assumes that the host has already resolved identity trustworthily and does not implement authentication or a real policy service. See [[ai-safety/01-foundations-and-risks/03-tool-overreach-and-data-exfiltration|Tool Overreach and Data Exfiltration]] for the independent tool-side authorization boundary.

## Synthetic data is not automatically anonymous

A generative model may reproduce training records, and low-frequency combinations may remain. Assess synthetic data for provenance, training-member leakage, nearest-neighbor or duplication, attribute inference, utility, and intended use. Public training data and synthetic output have different risk models. You can use provenance and release gates in [[data-synthesis/00-index|Data Synthesis]], but cannot skip privacy assessment merely because output is generated.

## Common errors

- Labeling data anonymous after removing names without assessing quasi-identifiers and external data.
- Treating only the training table and ignoring raw logs, prompts, vector stores, models, and backups.
- Copying full personal data for audit, thereby creating a new high-privilege data store.
- Stating a retention period in documentation without automatic expiry, failure alerts, and deletion evidence.
- Treating encryption as de-identification; key holders can still restore data, and access patterns and output can still leak.

## Exercise and self-check

Review a customer-churn dataset. For each field, record purpose, classification, necessity, contribution granularity, retention period, recipients, and alternatives. Choose three quasi-identifiers and explain how external data could link them; then list at least six kinds of copies outside the primary database that must be deleted.

- [ ] Can distinguish the strength of evidence for pseudonymization, de-identification, and anonymity.
- [ ] Can explain why quasi-identifiers and free text make “remove names” insufficient.
- [ ] Can trace each field, sharing event, and retention period back to an explicit purpose.
- [ ] Can verify the lifecycle of logs, vectors, models, caches, and backups.

## Next step

When you need to quantify one subject's effect on published statistics, continue with [[privacy-computing/01-foundations-and-risks/02-differential-privacy-intuition-and-budget|Differential Privacy Intuition and Budget]].

## References

- [NIST IR 8053: De-Identification of Personal Information](https://doi.org/10.6028/NIST.IR.8053) (2015; accessed 2026-07-22)
- [NIST SP 800-188: De-Identifying Government Datasets](https://csrc.nist.gov/pubs/sp/800/188/final) (final, September 2023; see the body text for scope limits)
- [NIST Privacy Framework](https://www.nist.gov/privacy-framework) (accessed 2026-07-22; 1.0 is published, while 1.1 remains Initial Public Draft/coming soon)
