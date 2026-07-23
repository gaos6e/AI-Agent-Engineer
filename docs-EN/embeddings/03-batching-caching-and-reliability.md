---
title: "Batching, Caching, and Reliability"
tags:
  - ai-agent-engineer
  - embedding
  - batching
  - reliability
aliases:
  - Embedding batching
  - Embedding generation pipeline
source_checked: 2026-07-22
source_baseline: Sentence Transformers and official OpenAI, Gemini, and Cohere
  materials checked through 2026-07-22; reliability principles align with the
  API course
lang: en
translation_key: Embedding/03-批处理缓存与可靠性.md
translation_source_hash: 4063df9395df766c33fc6dedfc1a7849f1e4d1eb906ccb510771c7b8ea279fe3
translation_route: zh-CN/Embedding/03-批处理缓存与可靠性
translation_default_route: zh-CN/Embedding/03-批处理缓存与可靠性
---

# Batching, Caching, and Reliability

## Objective

You will turn one `embed(text)` call into a recoverable pipeline. Inputs have stable identities; batches honor multiple limits; responses are reconciled item by item; failures receive bounded retries; caches bind to the full space; writes validate dimensions, finite values, norms, and hashes; and logs do not expose source text.

## Experiment in an isolated environment first

On Windows 11 with PowerShell 7, the baseline remains `venv + pip`. Run this in an exercise directory outside the vault, ensure `.venv/` is ignored, and never commit the virtual environment:

```powershell
python -m venv .venv  # Create an isolated virtual environment in the current exercise directory instead of modifying system Python.
.\.venv\Scripts\Activate.ps1  # Activate the environment in the current PowerShell session.
python -m pip install --upgrade pip  # Upgrade the package installer associated with the active interpreter.
python -m pip install package-name  # Replace the placeholder with a confirmed version of the official SDK or local runtime.
```

`package-name` is a placeholder. Replace it with the selected official SDK or local runtime and pin a verified version. After learning the basics, you can use `uv` to manage environments; changing tools does not replace pinning dependencies and model revisions or reproducing experiments.

This course's offline project requires no third-party package.

## Use work items, not bare strings

Before entering a queue, turn every input into a stable work item:

```json
{
  "item_id": "chunk-018",
  "source_revision": "rev-7",
  "role": "document",
  "input_sha256": "<hash of exact embedding input>",
  "space_id": "candidate-2026-07",
  "attempt": 0,
  "state": "pending"
}
```

JSON does not permit legal end-of-line comments. `item_id` identifies canonical input; `source_revision` pins the source version; `role` selects the official query/document route; `input_sha256` binds the text actually sent to the model; `space_id` prevents cross-space cache hits; `attempt` counts retries; and `state` drives a recoverable state machine. Keep the code block valid JSON so it can be parsed directly as a queue example.

Read the actual body from controlled content storage by ID instead of copying it into ordinary queue logs. `input_sha256` must cover the text genuinely sent to the model, including model-required titles, query/document prefixes, or task instructions. Hashing only the displayed body lets cache and vector provenance diverge.

Recommended states are:

`pending → submitted → received → validated → indexed`

Classify failures as:

- `retryable`: network interruption, rate limiting, or an explicitly temporary service error;
- `permanent`: authentication, authorization, an invalid role, overlength input, or a bad payload;
- `unknown outcome`: the client timed out and it is unclear whether the service finished, requiring request-ID or idempotency handling and cost reconciliation; or
- `quarantined`: a repeatedly abnormal item that needs individual investigation.

## A batch has multiple simultaneous limits

“100 items per batch” is not enough. A job can have simultaneous limits for:

- maximum item count;
- input length per item;
- total tokens or characters in a batch;
- HTTP payload bytes;
- model or device memory;
- response size and database transaction size; and
- concurrency plus per-minute or daily quota.

The packer should apply first-fit or sequential bin packing against official limits and safety headroom, checking every constraint before adding the next item. Reject or rechunk one overlength item by itself; do not retry an entire batch indefinitely.

For a local model, record actual padding waste as well. Bucketing similar lengths may improve throughput, but restore correspondence by `item_id` after sorting.

## Do not blindly zip inputs and responses

A reliable adapter defines and verifies:

1. which stable IDs appear in the request;
2. whether the service guarantees response order;
3. whether a response includes an index or ID;
4. how partial failures are represented;
5. whether usage is returned per request or per item; and
6. how retries are deduplicated.

Even when current official documentation guarantees order, an adapter should check that:

- the response count equals the expected count;
- every index or ID is unique and in range;
- no item is missing or duplicated;
- every vector satisfies space validation; and
- results are written back by `item_id`.

Do not use only `zip(items, vectors)` and assume that networking, SDKs, and batches will always be complete and ordered.

## Validate each vector before writing

For every item, verify:

- length equals `contract.dimension`;
- every value is numeric rather than boolean;
- no value is NaN or Inf;
- the L2 norm is finite and greater than 0;
- if the contract says normalized, the norm is close to 1 within the agreed tolerance;
- role, model/revision, dimension, metric, and dtype agree with the target index;
- the returned item corresponds to the current source and input hash; and
- ACL, tenant, and source metadata are present.

An HTTP 200 means only that the request succeeded. It does not show that a vector belongs to the correct input and space. A sudden distribution-wide shift in norms can reveal a role, preprocessing, model-alias, or normalization change; it should trigger an alert and sample regression.

## Cache keys must describe the whole space

One auditable form is:

$$
key=H(
provider,\ model,\ revision,\ role,\ task,\ dimension,\ dtype,\ normalization,\ input\_hash
)
$$

You can also hash normalized JSON directly:

```python
from hashlib import sha256  # Import SHA-256 to construct a fixed-length, irreversible cache key.
import json  # Import the standard JSON encoder so a composite contract can be serialized deterministically.
from typing import Any  # Import Any because contract field values can use several JSON-compatible types.


def cache_key(contract: dict[str, Any], input_sha256: str) -> str:  # Compress the complete space contract and actual input hash into one cache identity.
    payload = {  # Explicitly construct the smallest object that participates in identity calculation.
        "contract": contract,  # The contract should contain provider, model, revision, role, dimension, normalization, and related fields.
        "input_sha256": input_sha256,  # Accept only a hash calculated over the true embedding input.
    }  # Missing contract fields can cause incorrect reuse, so callers must validate first.
    encoded = json.dumps(  # Serialize stably inside this teaching Python process; this is not a cross-language JSON Canonicalization Scheme.
        payload,  # Encode the complete cache-identity object built above.
        ensure_ascii=False,  # Preserve non-ASCII characters instead of adding unnecessary escapes.
        allow_nan=False,  # Reject NaN and Infinity so non-standard JSON cannot become a cache key.
        sort_keys=True,  # Fix dictionary-key order so insertion order does not change identity for the same Python object.
        separators=(",", ":"),  # Remove insignificant whitespace so formatting does not change identity.
    ).encode("utf-8")  # Encode explicit UTF-8 bytes for the hash function.
    return sha256(encoded).hexdigest()  # Return a hexadecimal digest; it is a key, not source text or a vector.
```

`sort_keys=True` solves only the order of Python `dict` keys. It does not specify how numbers, Unicode strings, or every JSON value become the same byte sequence across languages. This example is appropriate for restricted fields in one controlled runtime; do not call it a general “canonical JSON” or signing format. If a key must be shared across services or languages, first freeze the field schema and serialization revision, then use an implementation-verified cross-language canonicalization such as the [RFC 8785 JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html), or feed a versioned byte protocol directly into the hash. One contract needs cross-implementation test vectors.

A changed model alias, revision, query/document role, dimension, or normalization must not hit an old vector. If an SDK version can change default preprocessing, include traceable build information too.

Cached vectors are derived from source text and must not be public by default. They inherit tenant, ACL, retention, and deletion policy; backups and debugging exports require the same control.

## Bounded retries and a total-attempt budget

Follow the patterns in [[api/00-index|APIs]] and [[llm-api-integration/00-index|LLM API Integration]]:

- set explicit connect timeout, read timeout, and total deadline;
- use bounded exponential backoff plus jitter for 429 and explicitly temporary errors;
- honor an official `Retry-After` or equivalent header;
- repair authentication, authorization, and input 4xx cases before retrying rather than replaying them unchanged;
- combine SDK-internal retries and outer queue retries into one total-attempt count;
- make an already validated success a no-op by item or cache key instead of recomputing it; and
- store provider request ID, attempt, error class, items/tokens, duration, and cost attribution.

If only one item in a batch fails permanently, bisect or isolate it. Do not retry the whole batch and bill successful items repeatedly. Whether a service supports an idempotency key depends on its current API; check provider documentation rather than assuming it does.

## Reproducibility contract for local models

Record at least:

- model repository and immutable revision;
- tokenizer revision;
- library version, Python, and OS;
- pooling, prompt, normalization, and dimension;
- device, dtype, and batch size;
- maximum input and truncation policy;
- whether `eval()` is used and whether an approximate or quantized backend is used; and
- a small set of canary inputs with output shape, norm, and retrieval ordering.

Do not promise bitwise equality across CPU/GPU, drivers, or precision modes. Release gates should examine tolerance, ranking, and business metrics rather than only exact float-by-float equality.

## Observability and privacy

Record:

| Category | Suggested fields |
| --- | --- |
| Identity | `space_id`, job/batch/item ID, source revision |
| Performance | queue wait, request duration, items/tokens, throughput |
| Reliability | attempt, HTTP/provider code, retry class, partial failure |
| Quality | dimension, norm distribution, zero/non-finite/rejected count |
| Cost | cache hit, billable units, estimated/actual cost |
| Traceability | provider request ID, deployment/model revision |

By default, do not log API keys, complete source text, complete vectors, or user queries. Use authorized IDs to look up diagnostic samples, minimizing, redacting, and time-limiting any necessary content.

## Failure-recovery procedure

For 1,000 chunks:

1. create work items from canonical source;
2. mark cache hits with the same complete contract as validated;
3. pack the remaining items by item, token, and payload limits;
4. submit each batch and save its request ID;
5. validate the response and persist successful items individually;
6. return temporary failures to the queue with incremented attempts;
7. send permanent overlength items back to Chunking and isolate other permanent errors;
8. compute `expected item IDs - validated IDs`; and
9. publish only after reconciling total count, ACLs, dimensions, norms, and hashes.

A recovery job resumes from its state table; it does not rerun the entire corpus from the beginning.

## Common mistakes and investigation

- **Throughput suddenly falls:** inspect length distribution, padding, quota, retry amplification, and cache-hit rate.
- **Vectors and IDs are misaligned:** inspect response order or index, batch splitting, and sorting restoration.
- **A cache hit but quality drifts:** the cache key lacks model revision, role, or input hash.
- **One bad item blocks the queue:** there is no permanent-error class or isolation.
- **Cost doubles:** SDK and outer retries stack, or a batch with unknown outcome is replayed wholesale.
- **Database body and vector differ:** silent truncation occurred or only original body was hashed.
- **Logs leak text:** an error object serialized the request payload directly.

## Exercises

1. Design a packer for 1,000 chunks of different lengths with simultaneous item-count, total-token, and payload-byte limits.
2. When item 3 in batch 7 fails permanently because it is overlength, draw how every other item proceeds and how that item returns to Chunking.
3. List a complete cache key, then remove the role and construct one incorrect cache hit.
4. For “the service completed but the client timed out,” define request-ID, state, and cost-reconciliation handling.
5. Design a norm-distribution canary: normal range, alert condition, lookup data, and data that must not be logged.
6. Compare local CPU float32 with GPU float16 and define acceptance criteria more useful than bitwise equality.

## Mastery check

- [ ] I create an isolated `venv + pip` environment outside the vault and do not commit `.venv`.
- [ ] My batch observes item, length, payload, memory, and quota limits at once.
- [ ] I reconcile every input and response by stable ID instead of blindly zipping lists.
- [ ] Before writes, I validate space, dimension, finite values, norm, hash, and ACL.
- [ ] My cache key contains the entire space contract and the actual input hash.
- [ ] Retries have a total budget, permanent failures are isolated, and unknown outcomes are reconciled.
- [ ] Logs retain diagnostic metadata without keys, full text, or complete vectors.
- [ ] Recovery continues from validated state rather than rerunning the whole corpus.

## Summary and next step

Reliable batching establishes that every vector truly belongs to this input and space. Next, make retrieval configuration agree with the space, and upgrade models without mixed writes, downtime, or lost deletions: [[embeddings/04-similarity-indexing-and-space-migration|Similarity, Indexing, and Space Migration]].

## References

- [Sentence Transformers Usage](https://www.sbert.net/docs/sentence_transformer/usage/usage.html)
- [OpenAI: Vector embeddings](https://developers.openai.com/api/docs/guides/embeddings)
- [Gemini API: Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
- [Cohere: Introduction to Embeddings](https://docs.cohere.com/docs/embeddings)
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html)

Sources were obtained on 2026-07-22. Batch limits, quotas, error codes, and retry headers are dynamic API facts; verify the relevant official reference on the integration date. Return to [[embeddings/00-index|Embeddings]].
