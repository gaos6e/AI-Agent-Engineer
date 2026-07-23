---
title: "Citations, Generation, and Abstention"
tags:
  - ai-agent-engineer
  - rag
  - citations
aliases:
  - Cited RAG Generation
  - RAG Citations and Abstention
source_checked: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: RAG/05-引用生成与拒答.md
translation_source_hash: bbb4a8d0ef2015cc64b4a3e36fd1bdf183cabe06a1e9438c80160f9340f81f99
translation_route: zh-CN/RAG/05-引用生成与拒答
translation_default_route: zh-CN/RAG/05-引用生成与拒答
---

# Citations, Generation, and Abstention

## Learning objectives

- Split answers into independently reviewable claims.
- Distinguish “a citation exists,” “a citation is accessible,” and “a citation supports the claim.”
- Constrain generated output with a structured contract and deterministic validation.
- Design distinct states for insufficient evidence, conflict, no permission, and dependency failure.

## Define the generation contract first

A generator should not return only a string. This knowledge base has two adjacent but distinct executable teaching schemas: Lesson 8 validates the online answering stage, whose public response has top-level `citations` and shorter `document_id + fact_id` references in claims; Lesson 9 validates the source-to-citation Layer B chain, whose claims embed complete source/span citations. The following generic target structure uses the Lesson 9 citation shape to explain field responsibilities. It is neither Lesson 8 nor Lesson 9's field-for-field exact CLI schema:

```json
{
  "status": "answered",
  "answer": "After a refund is approved, it usually returns to the original payment method within one to three business days.",
  "claims": [
    {
      "claim_id": "C1",
      "text": "After a refund is approved, it usually returns to the original payment method within one to three business days.",
      "citations": [
        {
          "document_id": "refund-policy",
          "source_uri": "kb://tenant-a/refund-policy",
          "source_version": "refund-2026-01",
          "raw_sha256": "<64 hex>",
          "canonical_revision_id": "can_<64 hex>",
          "parse_revision_id": "par_<64 hex>",
          "element_id": "el_<64 hex>",
          "chunk_id": "chk_<64 hex>",
          "index_entry_id": "idx_<64 hex>",
          "coordinate_space": "canonical-text-lf-nfc-char-v1",
          "char_start": 120,
          "char_end": 144,
          "span_sha256": "<64 hex>"
        }
      ]
    }
  ]
}
```

To keep the example parseable by a JSON parser, its field descriptions sit outside the block. Top-level `status` selects the response state; `answer` is deterministic text rendered for the user; `claims` splits facts into reviewable units. Each citation's `document_id/source_uri/source_version` identifies the source, hash and revision fields connect raw, canonical, parsed, chunk, and index identities, and `coordinate_space + char_start/char_end + span_sha256` precisely locates and validates the cited passage. A real project must use its corresponding exact schema instead of copying this conceptual example.

Production structures vary by product, but should at least express:

- answer state;
- a user-readable answer;
- checkable claims;
- a mapping from claims to source/span/revision;
- reasons for uncertainty, conflict, or abstention.

JSON Schema can establish structural correctness, not semantic support.

If citations or evaluation artifacts cross services or languages and participate in signing/verification, separately specify the **exact bytes**, version, and consumer validation rules. Local serialization habits such as `json.dumps(sort_keys=True)` are not cross-implementation canonicalization guarantees. If choosing RFC 8785 JCS, also obey its restrictions on duplicate keys, Unicode, and IEEE-754 numbers, and test independently implemented consumers against each other. SHA-256 detects disagreement only when a consumer holds and compares a trusted expected digest; it does not prove producer identity, factual content, or read permission.

Lesson 9 keeps global `index_generation_id` in a protected audit projection rather than a public citation. Otherwise, a global generation change caused by an unauthorized document could change a public response and become a corpus-existence side channel. The validator associates a public `index_entry_id` with the selected entry set in the current protected audit, then checks the generation it points to. If a product deliberately makes snapshot version public, document that disclosure tradeoff in the threat model.

> [!note] How to use the two schemas
> Lesson 8's `privileged_audit` and Lesson 9's `protected_audit` both mean “protected audit” conceptually, but they are fixed enums in two independent schemas. Lesson 8 can prove only fixture fact/revision association; only Lesson 9 declares canonical character spans and recomputes derived identities. Do not copy fields from one project into the other and skip the corresponding validator.

## Why claims matter

The sentence “A refund arrives in three days and is always fee-free” contains two claims. One citation may support only the first. Splitting a long answer into claims makes it possible to check each one:

1. Does the claim require evidence?
2. Did the citation come from this request's selected context?
3. Does the source's specific span support the claim?
4. Is the source currently effective and accessible to the user?
5. Are multiple sources consistent or conflicting?

General advice, value judgments, and inferences should state their nature; they must not masquerade as source facts.

## Four layers of citation validation

### 1. Structure and IDs

- Fields are complete and correctly typed.
- document/chunk/span IDs exist.
- IDs are unique, with no unknown or duplicate items.
- The source revision matches the current context.

### 2. Provenance

- Citations must originate in the current selected context.
- They cannot cite documents retrieved but not admitted to context.
- They cannot cite material filtered by ACL, tenant, or validity period.
- Source locator, raw/canonical hash, parse/chunk/entry identity, and coordinate space must be recomputable layer by layer.
- Protected audit must bind selected entries to the current published generation, authorization revision, snapshot, and tombstone state.

### 3. Entailment / support

- Does the cited passage actually support the claim?
- Does **every** citation in a claim support it, without one valid citation masking unrelated or redundant citations?
- Do conditions, negation, numbers, time, and applicable scope agree?
- Does the inference go beyond the evidence?

Lesson 8 establishes a deterministic lower bound for the online pipeline by requiring every claim to exactly equal a fixture fact statement. Lesson 9 goes further by requiring every extractive claim to exactly equal a canonical source span and recomputing all derived identities. Real generation is more flexible and needs help from human rubrics, rules, NLI, or LLM judges, but high-risk cases still need sampled human review.

You must also check **answer coverage by claims**. Validating hidden `claims/citations` while allowing the user-visible `answer` to add “arrival is guaranteed today and there is no fee” does not implement grounding. The offline project therefore renders `answer` deterministically from validated `status + claims`. If real generation permits free wording, split the answer into atomic claims again, reject added facts without a support mapping, and evaluate “answer correctness” separately from “citation faithfulness.”

### 4. User verifiability

- Can the user open the source?
- Does the link locate the correct page/passage?
- Are displayed title and version clear?
- Are private sources rendered according to authorization?

An inaccessible “mystery S1” does not provide a fully verifiable experience.

### Citation displays and jumps also require reauthorization

Access at answer time does not guarantee that a user can still access the same revision later. Citation detail pages, download links, and verification APIs should reapply object-level authorization using the current principal, resource lifecycle, and product-permitted snapshot semantics. After revocation or deletion, an old answer, cache, or citation URL must not continue to serve the body. If the display layer cannot safely confirm accessibility, return a general state that does not disclose another resource's existence—not “this document was just revoked,” a mirror replacement, or an explanation regenerated from private candidates.

This also shows why three statements must not be conflated: a citation locator says “which passage the system claims to cite”; a complete derivation chain says “how that passage was produced from a revision”; trusted source admission, signatures/attestations, and authorization decide “whether this chain may be trusted, shown, or relied upon.” The first two cannot by themselves guarantee factual correctness of the source.

## Abstention is not one state

| State | Meaning | User-facing information | Must not do |
| --- | --- | --- | --- |
| insufficient_evidence | Accessible material cannot support an answer. | Say evidence is insufficient; suggest additional material or human review. | Hint that private material exists. |
| conflict | Currently effective sources conflict. | Show the conflict boundary and sources. | Choose one unilaterally. |
| tool_required | The request asks for live state or an action. | Send it to an authorized tool/confirmation flow. | Present a knowledge snapshot as a live value. |
| dependency_unavailable | A retrieval dependency failed. | State that retrieval is temporarily unavailable. | Let the model answer internal facts from memory. |
| generation_unavailable | Evidence was retrieved but generation failed. | Return original text or retry later, by policy. | Output an unvalidated draft. |
| policy_denied | A security/compliance rule refused. | Offer a safe alternative path. | Reveal detection details. |

“No permission” and “no material” differ in internal diagnosis; external information must avoid enumerating private content via titles, IDs, candidate counts, or differing errors.

## Parametric memory and the evidence boundary

Even if a prompt says “use only the context,” a model may use parametric memory. For traceable scenarios such as internal policy, medicine, law, or finance:

- require citations for every factual claim;
- remove or reject claims that cannot align with evidence;
- label general advice separately rather than mixing it with policy facts;
- deterministically check key numbers and negation;
- provide human escalation or secondary verification.

“The model is confident” is not evidence.

## Conflict-answer example

If two effective sources say “500 per night” and “600 per night,” a valid result is neither the average, 550, nor automatic top-1 selection:

```text
State: conflict
Conclusion: Current effective material is inconsistent, so a single standard cannot yet be given.
Evidence A: 500 per night (source A, revision ...)
Evidence B: 600 per night (source B, revision ...)
Next step: Ask the policy owner to confirm applicable scope or correct the document.
```

If a deterministic rule for authority tier, region, or effective date already exists, resolve through that rule first; its rule and version must also enter the trace.

## Hands-on practice

First run the Lesson 8 project and inspect top-level `status`, `claims`, and `citations` through its public boundary. These commands do not output the complete Lesson 9 span citation shown above:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'  # Do not write Python bytecode caches for this exercise.
$script = '.\docs-EN\rag\examples\offline_cited_qa.py'  # Store the Lesson 8 offline cited-Q&A script path.
$fixture = '.\docs-EN\rag\examples\rag-fixture.json'  # Store the strict-fixture path that the script validates.

python -B $script --fixture $fixture ask --query-id Q-refund  # View the public answered response with sufficient evidence.
python -B $script --fixture $fixture ask --query-id Q-conflict  # View the public conflict response for two effective sources.
python -B $script --fixture $fixture ask --query-id Q-phone-guest  # View the guest response that does not disclose a private source.
python -B $script --fixture $fixture ask --query-id Q-order-live  # View a live-order question routed as tool_required.
```

`selected` belongs only to the protected audit surface. In a local teaching environment, only after confirming operator permission, inspect it explicitly:

```powershell
python -B $script --fixture $fixture inspect --query-id Q-refund --operator-view  # Request the protected audit trace for the refund case locally.
python -B $script --fixture $fixture inspect --query-id Q-conflict --operator-view  # Request the protected audit trace for the conflict case locally.
```

A real service cannot treat a declaration such as `--operator-view` as authentication; the host must complete identity and audit authorization before invocation.

Then make three changes in a test copy:

1. Change a citation to an unselected document ID.
2. Change a claim to “arrival is guaranteed today.”
3. Change `source_revision` to `wrong`.

Explain which layer should reject each one.

## Common mistakes

- Use only a regex to confirm that an answer contains `[S1]`.
- Put one citation after a paragraph containing multiple independent claims.
- Take citations from retrieved instead of selected context.
- Let a generator invent source IDs.
- Quietly switch to uncited free-form answers when no answer exists.
- Let an abstention disclose a filtered document's title or ID.

## Self-check

1. Why does the existence of a citation ID still not prove that an answer is supported?
2. What does claim-level citation solve that a single paragraph-end citation does not?
3. How do structured-output validation and semantic-support validation differ?
4. Why should a live-order question return `tool_required`?
5. Why may the user-visible result not contain a filtered source ID when authorization is insufficient?
6. Why must a citation URL in an old answer still receive object-level authorization when the user clicks it?

## Summary and next step

Reliable answers need a claim–evidence–version chain and clear abstention semantics. The next lesson works backward from wrong answers to locate the data, recall, context, generation, or citation layer: [[rag/06-failure-taxonomy-and-system-debugging|Failure Taxonomy and System Debugging]].

## References

- Es et al., [RAGAS: Automated Evaluation of Retrieval Augmented Generation](https://arxiv.org/abs/2309.15217)
- Saad-Falcon et al., [ARES: An Automated Evaluation Framework for RAG Systems](https://arxiv.org/abs/2311.09476)
- [W3C PROV Overview](https://www.w3.org/TR/prov-overview/) and [PROV-O](https://www.w3.org/TR/prov-o/): vocabulary for entities, activities, and derivation in citation lineage.
- [OWASP LLM08:2025 Vector and Embedding Weaknesses](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/): permission-aware retrieval, multi-tenant isolation, and vector-data risks.
- [OWASP RAG Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html): production controls for source attribution, verification endpoints, chunk-level ACLs, and cache invalidation.
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html): JCS boundaries for cross-implementation hashes/signatures; adoption requires handling I-JSON, numeric, and Unicode restrictions.

Sources accessed: 2026-07-22. Automated judges are measurement tools, not infallible truth; pin rubrics/versions and align them with human annotations.
