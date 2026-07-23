"""Key-free LangChain retrieval with explicit score and metadata contracts.

The embedding is a tiny, deterministic teaching adapter. It demonstrates
LangChain wiring and testable retrieval behavior; it is not a semantic model
and must not be used to claim real-world retrieval quality.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from importlib.metadata import version
import json
import math
import sys
from typing import Any


try:
    import numpy  # noqa: F401 -- InMemoryVectorStore uses NumPy internally.
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings
    from langchain_core.vectorstores import InMemoryVectorStore
    from langsmith import tracing_context
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by the CLI
    raise SystemExit(
        "dependency_missing: install retrieval_layer_b/requirements.txt"
    ) from exc


MAX_TEXT_LENGTH = 500
MAX_K = 20
REQUIRED_METADATA = frozenset(
    {
        "tenant",
        "chunk_id",
        "document_id",
        "section",
        "version",
        "effective_at",
        "access_scope",
        "source_path",
    }
)
ALLOWED_ACCESS_SCOPES = frozenset({"support", "employees", "finance"})


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field} must not be empty")
    if len(normalized) > MAX_TEXT_LENGTH:
        raise ValueError(f"{field} exceeds {MAX_TEXT_LENGTH} characters")
    return normalized


def _require_k(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("k must be an integer")
    if not 1 <= value <= MAX_K:
        raise ValueError(f"k must be between 1 and {MAX_K}")
    return value


class ToyKeywordEmbedding(Embeddings):
    """Map a fixed teaching vocabulary into three transparent dimensions."""

    CONCEPTS = (
        ("refund", "return", "receipt"),
        ("security", "incident", "breach"),
        ("billing", "invoice", "charge"),
    )

    @classmethod
    def _embed(cls, text: object, field: str) -> list[float]:
        normalized = _require_text(text, field).casefold()
        vector = [
            float(sum(normalized.count(term) for term in aliases))
            for aliases in cls.CONCEPTS
        ]
        if not any(vector):
            raise ValueError(f"{field} has no term in the teaching vocabulary")
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text, f"documents[{index}]") for index, text in enumerate(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text, "query")


def sample_documents() -> list[Document]:
    return [
        Document(
            id="alpha:refund:v1",
            page_content="refund return receipt policy: requests are accepted within 30 days",
            metadata={
                "tenant": "alpha",
                "chunk_id": "alpha:refund:v1",
                "document_id": "alpha-refund-policy",
                "section": "returns",
                "version": "1",
                "effective_at": "2026-01-01",
                "access_scope": "support",
                "source_path": "policies/alpha/refund-v1.md",
            },
        ),
        Document(
            id="alpha:security:v2",
            page_content="security incident breach policy: report an incident immediately",
            metadata={
                "tenant": "alpha",
                "chunk_id": "alpha:security:v2",
                "document_id": "alpha-security-policy",
                "section": "incident-reporting",
                "version": "2",
                "effective_at": "2026-02-01",
                "access_scope": "employees",
                "source_path": "policies/alpha/security-v2.md",
            },
        ),
        Document(
            id="beta:refund:v3",
            page_content="refund return receipt policy: requests are accepted within 14 days",
            metadata={
                "tenant": "beta",
                "chunk_id": "beta:refund:v3",
                "document_id": "beta-refund-policy",
                "section": "returns",
                "version": "3",
                "effective_at": "2026-03-01",
                "access_scope": "support",
                "source_path": "policies/beta/refund-v3.md",
            },
        ),
        Document(
            id="beta:billing:v1",
            page_content="billing invoice charge policy: invoices are issued monthly",
            metadata={
                "tenant": "beta",
                "chunk_id": "beta:billing:v1",
                "document_id": "beta-billing-policy",
                "section": "invoices",
                "version": "1",
                "effective_at": "2026-01-15",
                "access_scope": "finance",
                "source_path": "policies/beta/billing-v1.md",
            },
        ),
    ]


def validate_documents(documents: Sequence[Document]) -> list[Document]:
    selected = list(documents)
    if not selected:
        raise ValueError("documents must not be empty")
    seen_ids: set[str] = set()
    for index, document in enumerate(selected):
        label = f"documents[{index}]"
        if not isinstance(document.id, str) or not document.id:
            raise ValueError(f"{label}.id must be a stable non-empty string")
        if document.id in seen_ids:
            raise ValueError(f"duplicate document id: {document.id}")
        seen_ids.add(document.id)
        _require_text(document.page_content, f"{label}.page_content")
        missing = REQUIRED_METADATA - document.metadata.keys()
        if missing:
            raise ValueError(f"{label} is missing metadata: {sorted(missing)}")
        for field in REQUIRED_METADATA:
            _require_text(document.metadata[field], f"{label}.metadata.{field}")
        if document.metadata["chunk_id"] != document.id:
            raise ValueError(f"{label}.metadata.chunk_id must equal Document.id")
        if document.metadata["access_scope"] not in ALLOWED_ACCESS_SCOPES:
            raise ValueError(f"{label}.metadata.access_scope is not allowed")
    return selected


def _document_id(document: Document) -> str:
    try:
        validated = validate_documents([document])[0]
    except ValueError as exc:
        raise RuntimeError(f"retrieved document violates the contract: {exc}") from exc
    if not isinstance(validated.id, str):  # Narrow the optional Document.id type.
        raise RuntimeError("retrieved document is missing a stable string id")
    return validated.id


def build_store(
    documents: Sequence[Document] | None = None,
) -> InMemoryVectorStore:
    selected = validate_documents(
        list(documents) if documents is not None else sample_documents()
    )
    expected_ids = [str(document.id) for document in selected]
    store = InMemoryVectorStore(embedding=ToyKeywordEmbedding())
    with tracing_context(enabled=False):
        stored_ids = store.add_documents(selected)
    if stored_ids != expected_ids:
        raise RuntimeError(
            f"vector store changed document ids: expected {expected_ids}, got {stored_ids}"
        )
    with tracing_context(enabled=False):
        round_trip = store.get_by_ids(list(reversed(expected_ids)))
    round_trip_by_id = {_document_id(document): document for document in round_trip}
    if len(round_trip_by_id) != len(round_trip) or set(round_trip_by_id) != set(expected_ids):
        raise RuntimeError("vector store did not round-trip the complete stable-id set")
    return store


def search(
    store: InMemoryVectorStore,
    query: object,
    *,
    tenant: object,
    k: object = 3,
    minimum_similarity: object = 0.5,
) -> list[dict[str, Any]]:
    normalized_query = _require_text(query, "query")
    normalized_tenant = _require_text(tenant, "tenant")
    selected_k = _require_k(k)
    if isinstance(minimum_similarity, bool) or not isinstance(
        minimum_similarity, (int, float)
    ):
        raise ValueError("minimum_similarity must be a finite number")
    threshold = float(minimum_similarity)
    if not math.isfinite(threshold) or not -1.0 <= threshold <= 1.0:
        raise ValueError("minimum_similarity must be between -1 and 1")

    # This callable filter is specific to InMemoryVectorStore and runs in this
    # process before similarity scoring. It is not a substitute for a remote
    # vector database's server-side tenant/ACL enforcement.
    with tracing_context(enabled=False):
        raw_results = store.similarity_search_with_score(
            normalized_query,
            k=selected_k,
            filter=lambda document: document.metadata.get("tenant")
            == normalized_tenant,
        )
    hits: list[dict[str, Any]] = []
    for document, raw_score in raw_results:
        score = float(raw_score)
        if not math.isfinite(score):
            raise RuntimeError("vector store returned a non-finite similarity score")
        if score < threshold:
            continue
        hits.append(
            {
                "document_id": _document_id(document),
                "metadata": dict(document.metadata),
                "page_content": document.page_content,
                "raw_score": score,
                "score_semantics": "cosine_similarity_higher_is_more_similar",
            }
        )
    return hits


def retrieve_batch(
    store: InMemoryVectorStore,
    queries: Sequence[object],
    *,
    tenant: object,
    k: object = 1,
) -> list[list[str]]:
    normalized_tenant = _require_text(tenant, "tenant")
    selected_k = _require_k(k)
    normalized_queries = [
        _require_text(query, f"queries[{index}]")
        for index, query in enumerate(queries)
    ]
    if not normalized_queries:
        raise ValueError("queries must not be empty")
    retriever = store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": selected_k,
            "filter": lambda document: document.metadata.get("tenant")
            == normalized_tenant,
        },
    )
    with tracing_context(enabled=False):
        batches = retriever.batch(normalized_queries)
    return [
        [_document_id(document) for document in documents]
        for documents in batches
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--query",
        default="How can I return an item with a receipt?",
    )
    parser.add_argument("--tenant", default="alpha")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--minimum-similarity", type=float, default=0.5)
    args = parser.parse_args(argv)

    try:
        store = build_store()
        hits = search(
            store,
            args.query,
            tenant=args.tenant,
            k=args.k,
            minimum_similarity=args.minimum_similarity,
        )
        batch_ids = retrieve_batch(
            store,
            [args.query, "How should I report a security incident?"],
            tenant=args.tenant,
        )
    except (RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {"status": "invalid", "error": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            {
                "status": "ok",
                "dependencies": {
                    "langchain-core": version("langchain-core"),
                    "numpy": version("numpy"),
                },
                "embedding_boundary": "deterministic teaching vocabulary, not semantic quality",
                "hits": hits,
                "retriever_batch_document_ids": batch_ids,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


