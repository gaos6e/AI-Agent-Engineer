"""Offline embedding-space contracts, exact retrieval, evaluation, and migration audit.

All vectors come from local teaching fixtures; it neither downloads nor runs a real model. This script validates
data-flow and metric implementations; it does not represent the performance of any production embedding model.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import isclose, isfinite, log2, sqrt
from pathlib import Path
import statistics
import sys
from typing import Any, Sequence
import unicodedata


Vector = tuple[float, ...]
ALLOWED_METRICS = {"cosine", "dot", "euclidean"}
ALLOWED_DTYPES = {"float32", "float64"}
MAX_FIXTURE_BYTES = 5 * 1024 * 1024
NORMALIZED_ABS_TOLERANCE = 1e-6


class EmbeddingError(ValueError):
    """The space contract, fixture, or evaluation input is invalid."""


@dataclass(frozen=True)
class EmbeddingContract:
    space_id: str
    provider: str
    model: str
    revision: str
    dimension: int
    metric: str
    normalized: bool
    query_role: str
    document_role: str
    dtype: str

    def validate(self) -> None:
        for name in (
            "space_id",
            "provider",
            "model",
            "revision",
            "query_role",
            "document_role",
            "dtype",
        ):
            _clean_token(name, getattr(self, name))
        if (
            not isinstance(self.dimension, int)
            or isinstance(self.dimension, bool)
            or not 1 <= self.dimension <= 100_000
        ):
            raise EmbeddingError("dimension must be an integer in 1..100000")
        if self.metric not in ALLOWED_METRICS:
            raise EmbeddingError(f"unsupported metric: {self.metric}")
        if not isinstance(self.normalized, bool):
            raise EmbeddingError("normalized must be boolean")
        if self.query_role == self.document_role:
            raise EmbeddingError("query_role and document_role must differ")
        if self.dtype not in ALLOWED_DTYPES:
            raise EmbeddingError(f"unsupported dtype: {self.dtype}")

    def signature(self) -> str:
        """Return a fingerprint for the mathematical/encoding space contract."""
        payload = {
            "dimension": self.dimension,
            "document_role": self.document_role,
            "dtype": self.dtype,
            "metric": self.metric,
            "model": self.model,
            "normalized": self.normalized,
            "provider": self.provider,
            "query_role": self.query_role,
            "revision": self.revision,
        }
        return _digest(_canonical_json(payload))


@dataclass(frozen=True)
class EmbeddedItem:
    item_id: str
    space_id: str
    role: str
    text: str
    vector: Vector
    acl: tuple[str, ...]
    source_revision: str
    content_sha256: str


@dataclass(frozen=True)
class QueryCase:
    case_id: str
    query_item_id: str
    subject_groups: tuple[str, ...]
    relevance: tuple[tuple[str, int], ...]
    subgroups: tuple[str, ...]

    def relevance_map(self) -> dict[str, int]:
        return dict(self.relevance)


@dataclass(frozen=True)
class Fixture:
    contracts: tuple[EmbeddingContract, ...]
    items: tuple[EmbeddedItem, ...]
    queries: tuple[QueryCase, ...]


@dataclass(frozen=True)
class RankedItem:
    rank: int
    item_id: str
    score: float


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _normalise_text(value: str) -> str:
    return unicodedata.normalize(
        "NFC", value.replace("\r\n", "\n").replace("\r", "\n")
    )


def _clean_token(name: str, value: Any, maximum: int = 300) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise EmbeddingError(f"{name} must be a nonempty string without leading or trailing whitespace")
    if len(value) > maximum or any(ord(character) < 32 for character in value):
        raise EmbeddingError(f"{name} has invalid length or control characters")
    return value


def _clean_text(name: str, value: Any, maximum: int = 100_000) -> str:
    if not isinstance(value, str):
        raise EmbeddingError(f"{name} must be a string")
    text = _normalise_text(value)
    if not text.strip() or len(text) > maximum:
        raise EmbeddingError(f"{name} must be nonempty text within the length limit")
    return text


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EmbeddingError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise EmbeddingError(f"JSON does not permit a non-finite number: {value}")


def _load_json(path: Path) -> Any:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise EmbeddingError(f"cannot read fixture: {path}") from exc
    if size > MAX_FIXTURE_BYTES:
        raise EmbeddingError("fixture exceeds the 5 MiB limit")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except UnicodeDecodeError as exc:
        raise EmbeddingError("fixture must be UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise EmbeddingError(
            f"{path.name} JSON error: {exc.lineno}:{exc.colno}"
        ) from exc


def _require_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise EmbeddingError(
            f"{label} fields must be exactly {sorted(expected)}, actual value is {sorted(actual)}"
        )


def _clean_string_list(
    name: str,
    value: Any,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty):
        requirement = "array" if allow_empty else "nonempty array"
        raise EmbeddingError(f"{name} must be a {requirement}")
    cleaned = tuple(_clean_token(name, item) for item in value)
    if len(set(cleaned)) != len(cleaned):
        raise EmbeddingError(f"{name} must not contain duplicates")
    return tuple(sorted(cleaned))


def _vector_norm(vector: Sequence[float]) -> float:
    return sqrt(sum(value * value for value in vector))


def _finite_float(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise EmbeddingError(f"{label} must be a finite number")
    try:
        parsed = float(value)
    except (OverflowError, ValueError) as exc:
        raise EmbeddingError(f"{label} must be a finite number") from exc
    if not isfinite(parsed):
        raise EmbeddingError(f"{label} must be a finite number")
    return parsed


def _parse_vector(
    value: Any,
    *,
    contract: EmbeddingContract,
    label: str,
) -> Vector:
    if not isinstance(value, list) or len(value) != contract.dimension:
        raise EmbeddingError(
            f"{label} must have dimension {contract.dimension}, actual value is "
            f"{len(value) if isinstance(value, list) else 'non-array'}"
        )
    parsed: list[float] = []
    for index, item in enumerate(value):
        parsed.append(_finite_float(item, f"{label}[{index}]"))
    vector = tuple(parsed)
    norm = _vector_norm(vector)
    if norm == 0.0 or not isfinite(norm):
        raise EmbeddingError(f"{label} must not be a zero vector")
    if contract.normalized and not isclose(
        norm,
        1.0,
        rel_tol=0.0,
        abs_tol=NORMALIZED_ABS_TOLERANCE,
    ):
        raise EmbeddingError(
            f"{label} declares normalized=True, but L2 norm={norm:.9f}"
        )
    return vector


def _parse_contracts(value: Any) -> tuple[EmbeddingContract, ...]:
    if not isinstance(value, list) or not value:
        raise EmbeddingError("contracts must be a nonempty array")
    expected = {
        "space_id",
        "provider",
        "model",
        "revision",
        "dimension",
        "metric",
        "normalized",
        "query_role",
        "document_role",
        "dtype",
    }
    result: list[EmbeddingContract] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise EmbeddingError(f"contracts[{index}] must be an object")
        _require_fields(item, expected, f"contracts[{index}]")
        contract = EmbeddingContract(
            space_id=item["space_id"],
            provider=item["provider"],
            model=item["model"],
            revision=item["revision"],
            dimension=item["dimension"],
            metric=item["metric"],
            normalized=item["normalized"],
            query_role=item["query_role"],
            document_role=item["document_role"],
            dtype=item["dtype"],
        )
        contract.validate()
        if contract.space_id in seen:
            raise EmbeddingError(f"duplicate space_id: {contract.space_id}")
        seen.add(contract.space_id)
        result.append(contract)
    return tuple(sorted(result, key=lambda contract: contract.space_id))


def _parse_items(
    value: Any,
    contracts: dict[str, EmbeddingContract],
) -> tuple[EmbeddedItem, ...]:
    if not isinstance(value, list) or not value:
        raise EmbeddingError("items must be a nonempty array")
    expected = {
        "item_id",
        "space_id",
        "role",
        "text",
        "vector",
        "acl",
        "source_revision",
    }
    result: list[EmbeddedItem] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise EmbeddingError(f"items[{index}] must be an object")
        _require_fields(item, expected, f"items[{index}]")
        item_id = _clean_token("item_id", item["item_id"])
        space_id = _clean_token("space_id", item["space_id"])
        if space_id not in contracts:
            raise EmbeddingError(f"item points to an unknown space: {space_id}")
        key = (space_id, item_id)
        if key in seen:
            raise EmbeddingError(f"duplicate item: {space_id}/{item_id}")
        seen.add(key)
        contract = contracts[space_id]
        role = _clean_token("role", item["role"])
        if role not in {contract.query_role, contract.document_role}:
            raise EmbeddingError(
                f"{space_id}/{item_id} role violates the space contract: {role}"
            )
        text = _clean_text("text", item["text"])
        vector = _parse_vector(
            item["vector"],
            contract=contract,
            label=f"{space_id}/{item_id}.vector",
        )
        acl = _clean_string_list("acl", item["acl"])
        source_revision = _clean_token(
            "source_revision", item["source_revision"]
        )
        result.append(
            EmbeddedItem(
                item_id=item_id,
                space_id=space_id,
                role=role,
                text=text,
                vector=vector,
                acl=acl,
                source_revision=source_revision,
                content_sha256=_digest(text),
            )
        )
    return tuple(sorted(result, key=lambda item: (item.space_id, item.item_id)))


def _parse_queries(
    value: Any,
    *,
    contracts: Sequence[EmbeddingContract],
    items: Sequence[EmbeddedItem],
) -> tuple[QueryCase, ...]:
    if not isinstance(value, list) or not value:
        raise EmbeddingError("queries must be a nonempty array")
    by_key = {(item.space_id, item.item_id): item for item in items}
    expected = {
        "case_id",
        "query_item_id",
        "subject_groups",
        "relevance",
        "subgroups",
    }
    result: list[QueryCase] = []
    seen: set[str] = set()
    for index, value_item in enumerate(value):
        if not isinstance(value_item, dict):
            raise EmbeddingError(f"queries[{index}] must be an object")
        _require_fields(value_item, expected, f"queries[{index}]")
        case_id = _clean_token("case_id", value_item["case_id"])
        if case_id in seen:
            raise EmbeddingError(f"duplicate case_id: {case_id}")
        seen.add(case_id)
        query_item_id = _clean_token(
            "query_item_id", value_item["query_item_id"]
        )
        subject_groups = _clean_string_list(
            "subject_groups", value_item["subject_groups"]
        )
        subgroups = _clean_string_list("subgroups", value_item["subgroups"])
        relevance_value = value_item["relevance"]
        if not isinstance(relevance_value, dict) or not relevance_value:
            raise EmbeddingError("relevance must be a nonempty object")
        relevance: list[tuple[str, int]] = []
        for document_id, grade in relevance_value.items():
            _clean_token("relevant document_id", document_id)
            if (
                not isinstance(grade, int)
                or isinstance(grade, bool)
                or not 1 <= grade <= 3
            ):
                raise EmbeddingError("relevance grade must be an integer in 1..3")
            relevance.append((document_id, grade))

        for contract in contracts:
            query_key = (contract.space_id, query_item_id)
            if query_key not in by_key:
                raise EmbeddingError(
                    f"{case_id} is missing a query item in {contract.space_id}"
                )
            query_item = by_key[query_key]
            if query_item.role != contract.query_role:
                raise EmbeddingError(
                    f"{contract.space_id}/{query_item_id} is not a query-role item"
                )
            for document_id, _ in relevance:
                document_key = (contract.space_id, document_id)
                if document_key not in by_key:
                    raise EmbeddingError(
                        f"{case_id} is missing a relevant document in {contract.space_id}: "
                        f"{document_id}"
                    )
                document = by_key[document_key]
                if document.role != contract.document_role:
                    raise EmbeddingError(
                        f"{contract.space_id}/{document_id} is not a document-role item"
                    )
                if not set(subject_groups).intersection(document.acl):
                    raise EmbeddingError(
                        f"{case_id}  has gold data containing a document the subject is not authorized to read: {document_id}"
                    )
        result.append(
            QueryCase(
                case_id=case_id,
                query_item_id=query_item_id,
                subject_groups=subject_groups,
                relevance=tuple(sorted(relevance)),
                subgroups=subgroups,
            )
        )
    return tuple(sorted(result, key=lambda case: case.case_id))


def load_fixture(path: Path) -> Fixture:
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise EmbeddingError("fixture root must be an object")
    _require_fields(payload, {"contracts", "items", "queries"}, "fixture")
    contracts = _parse_contracts(payload["contracts"])
    by_space = {contract.space_id: contract for contract in contracts}
    items = _parse_items(payload["items"], by_space)
    queries = _parse_queries(
        payload["queries"],
        contracts=contracts,
        items=items,
    )
    for contract in contracts:
        roles = {
            item.role for item in items if item.space_id == contract.space_id
        }
        if contract.query_role not in roles or contract.document_role not in roles:
            raise EmbeddingError(
                f"{contract.space_id} must contain both query and document items"
            )
    return Fixture(contracts=contracts, items=items, queries=queries)


def normalize(vector: Vector) -> Vector:
    if not vector:  # Empty vectors have no direction and cannot participate in cosine similarity or normalization.
        raise EmbeddingError("vector must be nonempty and contain only finite values")  # Reject meaningless input before mathematical computation.
    parsed = tuple(  # Convert every dimension to a finite float so bool, NaN, and Inf cannot enter later computation.
        _finite_float(value, f"vector[{index}]") for index, value in enumerate(vector)  # Include the exact dimension position in an error.
    )
    norm = _vector_norm(parsed)  # Calculate the L2 norm, the vector length.
    if norm == 0.0 or not isfinite(norm):  # A zero vector cannot be divided by its norm, and a non-finite norm contaminates scores.
        raise EmbeddingError("vector norm must be finite and positive")  # Fail closed rather than return a bogus normalized result.
    return tuple(value / norm for value in parsed)  # Divide every dimension by the same magnitude to obtain a unit vector of length 1.


def similarity(
    left: Vector,
    right: Vector,
    *,
    metric: str,
) -> float:
    if metric not in ALLOWED_METRICS:  # Allow only the three metrics explicitly implemented and tested by this experiment.
        raise EmbeddingError(f"unsupported metric: {metric}")  # Do not silently fall back to another algorithm on a spelling error.
    if not left or len(left) != len(right):  # Dot product, cosine similarity, and distance all require nonempty vectors of equal dimension.
        raise EmbeddingError("vectors must be nonempty and have the same dimension")  # Vectors with different dimensions must never be silently compared by truncation or zip.
    left_values = tuple(  # Validate every dimension of the left vector.
        _finite_float(value, f"left[{index}]") for index, value in enumerate(left)  # Keep the failing dimension to diagnose the fixture.
    )
    right_values = tuple(  # Validate every dimension of the right vector.
        _finite_float(value, f"right[{index}]") for index, value in enumerate(right)  # Reject non-finite values here as well.
    )
    if metric == "cosine":  # Cosine similarity compares direction, so first convert both sides to unit vectors.
        left_unit = normalize(left_values)  # Divide the left vector by its L2 norm.
        right_unit = normalize(right_values)  # Divide the right vector by its L2 norm.
        return sum(a * b for a, b in zip(left_unit, right_unit))  # The dot product of unit vectors is cosine similarity.
    if metric == "dot":  # Dot product retains original magnitude and is valid only for spaces that allow it.
        return sum(a * b for a, b in zip(left_values, right_values))  # Multiply by dimension and then sum.
    squared = sum((a - b) ** 2 for a, b in zip(left_values, right_values))  # First calculate squared Euclidean distance.
    return -sqrt(squared)  # Search uses a uniform higher-score-is-better order, so return negative distance.


def _contract_for(fixture: Fixture, space_id: str) -> EmbeddingContract:
    for contract in fixture.contracts:
        if contract.space_id == space_id:
            return contract
    raise EmbeddingError(f"unknown embedding space: {space_id}")


def _item_map(fixture: Fixture, space_id: str) -> dict[str, EmbeddedItem]:
    return {
        item.item_id: item
        for item in fixture.items
        if item.space_id == space_id
    }


def search(
    fixture: Fixture,
    *,
    space_id: str,
    query_item_id: str,
    subject_groups: Sequence[str],
    k: int,
) -> list[RankedItem]:
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:  # k is an API boundary and cannot accept zero, negative values, or booleans.
        raise EmbeddingError("k must be a positive integer")  # An invalid k must fail explicitly rather than silently become a default.
    contract = _contract_for(fixture, space_id)  # Read the target space's metric, role, and dimension contract.
    items = _item_map(fixture, space_id)  # Build a candidate map only within the same space_id to prevent cross-space comparison.
    if query_item_id not in items:  # The query ID must belong to the target space.
        raise EmbeddingError(f"query item does not exist: {space_id}/{query_item_id}")  # A missing ID is not a no-results outcome.
    query = items[query_item_id]  # Load the query vector and its role metadata.
    if query.role != contract.query_role:  # A document must not be passed as a query.
        raise EmbeddingError(f"{query_item_id} is not a query-role item")  # Reject a role error even when the dimensions happen to match.
    groups = {  # Normalize the subject's groups for the later ACL OR-semantics check.
        _clean_token("subject_group", group) for group in subject_groups  # Reject blank or control-character group names one at a time.
    }
    if not groups:  # Without identity context, do not default to seeing every document.
        return []  # Fail closed: return no candidates rather than perform open retrieval.

    scored: list[tuple[float, str]] = []  # Store score-and-ID pairs until all authorization filtering is complete.
    for item in items.values():  # Traverse every teaching item in this space.
        if item.role != contract.document_role:  # The query itself and other roles are not retrievable documents.
            continue  # Skip non-documents so query-query comparisons do not enter results.
        if not groups.intersection(item.acl):  # At least one subject group must be authorized by the document ACL.
            continue  # Filter before similarity scoring so unauthorized documents cannot affect ranking or logs.
        score = similarity(query.vector, item.vector, metric=contract.metric)  # Calculate the exact score using the metric declared by the target space.
        scored.append((score, item.item_id))  # Temporarily store sortable results for authorized documents.
    scored.sort(key=lambda row: (-row[0], row[1]))  # Sort scores descending and IDs ascending on ties so results are reproducible.
    return [  # Convert the first k entries into immutable output records ranked from 1.
        RankedItem(rank=index, item_id=item_id, score=score)  # Preserve raw values; let the presentation layer decide how to round.
        for index, (score, item_id) in enumerate(scored[:k], start=1)  # Take top-k first, then number the entries consecutively.
    ]


def _validate_metric_inputs(
    results: Sequence[str], relevance: dict[str, int]
) -> tuple[str, ...]:
    if isinstance(results, (str, bytes)):
        raise EmbeddingError("results must be an ID sequence ordered by rank")
    identifiers = tuple(
        _clean_token(f"results[{index}]", item_id)
        for index, item_id in enumerate(results)
    )
    if len(identifiers) != len(set(identifiers)):
        raise EmbeddingError("results contain duplicate item_id values")
    if not isinstance(relevance, dict) or not relevance:
        raise EmbeddingError("relevance must be a nonempty object")
    for item_id, grade in relevance.items():
        _clean_token("relevance item_id", item_id)
        if (
            not isinstance(grade, int)
            or isinstance(grade, bool)
            or not 1 <= grade <= 3
        ):
            raise EmbeddingError("relevance grade must be an integer in 1..3")
    return identifiers


def recall_at_k(results: Sequence[str], relevance: dict[str, int]) -> float:
    identifiers = _validate_metric_inputs(results, relevance)
    return len(set(identifiers).intersection(relevance)) / len(relevance)


def reciprocal_rank(results: Sequence[str], relevance: dict[str, int]) -> float:
    identifiers = _validate_metric_inputs(results, relevance)
    for rank, item_id in enumerate(identifiers, start=1):
        if item_id in relevance:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(results: Sequence[str], relevance: dict[str, int], k: int) -> float:
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise EmbeddingError("k must be a positive integer")
    identifiers = _validate_metric_inputs(results, relevance)

    def dcg(grades: Sequence[int]) -> float:
        return sum(
            (2**grade - 1) / log2(rank + 1)
            for rank, grade in enumerate(grades, start=1)
        )

    observed = [relevance.get(item_id, 0) for item_id in identifiers[:k]]
    ideal = sorted(relevance.values(), reverse=True)[:k]
    ideal_score = dcg(ideal)
    score = 0.0 if ideal_score == 0.0 else dcg(observed) / ideal_score
    if not isfinite(score) or not 0.0 <= score <= 1.0 + 1e-12:
        raise EmbeddingError("nDCG is outside 0..1; the ranking or qrels contract is invalid")
    return min(1.0, score)


def _mean(values: Sequence[float | int]) -> float:
    return 0.0 if not values else round(float(statistics.fmean(values)), 4)


def evaluate_space(
    fixture: Fixture,
    *,
    space_id: str,
    k: int,
) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    ndcgs: list[float] = []
    subgroup_values: dict[str, dict[str, list[float]]] = {}

    for case in fixture.queries:
        ranked = search(
            fixture,
            space_id=space_id,
            query_item_id=case.query_item_id,
            subject_groups=case.subject_groups,
            k=k,
        )
        result_ids = [item.item_id for item in ranked]
        relevance = case.relevance_map()
        recall = recall_at_k(result_ids, relevance)
        rr = reciprocal_rank(result_ids, relevance)
        ndcg = ndcg_at_k(result_ids, relevance, k)
        recalls.append(recall)
        reciprocal_ranks.append(rr)
        ndcgs.append(ndcg)
        for subgroup in case.subgroups:
            metrics = subgroup_values.setdefault(
                subgroup,
                {"recall_at_k": [], "reciprocal_rank": [], "ndcg_at_k": []},
            )
            metrics["recall_at_k"].append(recall)
            metrics["reciprocal_rank"].append(rr)
            metrics["ndcg_at_k"].append(ndcg)
        details.append(
            {
                "case_id": case.case_id,
                "query_item_id": case.query_item_id,
                "result_ids": result_ids,
                "scores": [round(item.score, 6) for item in ranked],
                "recall_at_k": round(recall, 4),
                "reciprocal_rank": round(rr, 4),
                "ndcg_at_k": round(ndcg, 4),
                "subgroups": list(case.subgroups),
            }
        )

    subgroup_report = {
        subgroup: {
            metric: _mean(values)
            for metric, values in metrics.items()
        }
        for subgroup, metrics in sorted(subgroup_values.items())
    }
    return {
        "space_id": space_id,
        "k": k,
        "query_count": len(fixture.queries),
        "mean_recall_at_k": _mean(recalls),
        "mrr": _mean(reciprocal_ranks),
        "mean_ndcg_at_k": _mean(ndcgs),
        "subgroups": subgroup_report,
        "details": details,
    }


def inventory_report(
    fixture: Fixture,
    *,
    space_id: str,
) -> dict[str, Any]:
    contract = _contract_for(fixture, space_id)
    items = [
        item for item in fixture.items if item.space_id == space_id
    ]
    documents = [
        item for item in items if item.role == contract.document_role
    ]
    queries = [item for item in items if item.role == contract.query_role]
    norms = [_vector_norm(item.vector) for item in items]
    bytes_per_value = 4 if contract.dtype == "float32" else 8
    return {
        "space_id": space_id,
        "contract_signature": contract.signature(),
        "item_count": len(items),
        "document_count": len(documents),
        "query_item_count": len(queries),
        "dimension": contract.dimension,
        "metric": contract.metric,
        "normalized": contract.normalized,
        "dtype": contract.dtype,
        "estimated_raw_vector_bytes": (
            len(items) * contract.dimension * bytes_per_value
        ),
        "norm_min": round(min(norms), 6),
        "norm_median": round(float(statistics.median(norms)), 6),
        "norm_max": round(max(norms), 6),
    }


def migration_audit(
    fixture: Fixture,
    *,
    old_space_id: str,
    new_space_id: str,
    k: int,
) -> dict[str, Any]:
    if old_space_id == new_space_id:
        raise EmbeddingError("migration audit requires two different space_id values")
    old_contract = _contract_for(fixture, old_space_id)
    new_contract = _contract_for(fixture, new_space_id)
    old_items = _item_map(fixture, old_space_id)
    new_items = _item_map(fixture, new_space_id)
    old_ids = set(old_items)
    new_ids = set(new_items)
    only_old = sorted(old_ids - new_ids)
    only_new = sorted(new_ids - old_ids)
    canonical_mismatches: list[str] = []
    for item_id in sorted(old_ids.intersection(new_ids)):
        old = old_items[item_id]
        new = new_items[item_id]
        old_canonical = (
            old.role,
            old.text,
            old.acl,
            old.source_revision,
            old.content_sha256,
        )
        new_canonical = (
            new.role,
            new.text,
            new.acl,
            new.source_revision,
            new.content_sha256,
        )
        if old_canonical != new_canonical:
            canonical_mismatches.append(item_id)

    old_evaluation = evaluate_space(
        fixture, space_id=old_space_id, k=k
    )
    new_evaluation = evaluate_space(
        fixture, space_id=new_space_id, k=k
    )
    old_details = {
        detail["case_id"]: detail for detail in old_evaluation["details"]
    }
    new_details = {
        detail["case_id"]: detail for detail in new_evaluation["details"]
    }
    agreements: list[dict[str, Any]] = []
    jaccards: list[float] = []
    for case_id in sorted(set(old_details).intersection(new_details)):
        old_results = set(old_details[case_id]["result_ids"])
        new_results = set(new_details[case_id]["result_ids"])
        union = old_results.union(new_results)
        jaccard = 1.0 if not union else len(old_results.intersection(new_results)) / len(union)
        jaccards.append(jaccard)
        agreements.append(
            {
                "case_id": case_id,
                "top_k_jaccard": round(jaccard, 4),
            }
        )

    quality_keys = ("mean_recall_at_k", "mrr", "mean_ndcg_at_k")
    quality_delta = {
        key: round(new_evaluation[key] - old_evaluation[key], 4)
        for key in quality_keys
    }
    inventory_match = not only_old and not only_new
    canonical_match = not canonical_mismatches
    return {
        "old_space_id": old_space_id,
        "new_space_id": new_space_id,
        "vectors_directly_comparable": (
            old_contract.signature() == new_contract.signature()
        ),
        "inventory_match": inventory_match,
        "canonical_match": canonical_match,
        "only_old": only_old,
        "only_new": only_new,
        "canonical_mismatches": canonical_mismatches,
        "mechanical_gates_pass": inventory_match and canonical_match,
        "quality_delta_new_minus_old": quality_delta,
        "mean_top_k_jaccard": _mean(jaccards),
        "per_query_agreement": agreements,
        "quality_decision_required": True,
    }


def run_experiment(fixture: Fixture, *, k: int = 3) -> dict[str, Any]:
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise EmbeddingError("k must be a positive integer")
    space_ids = [contract.space_id for contract in fixture.contracts]
    evaluations = {
        space_id: evaluate_space(fixture, space_id=space_id, k=k)
        for space_id in space_ids
    }
    inventories = {
        space_id: inventory_report(fixture, space_id=space_id)
        for space_id in space_ids
    }
    migrations = [
        migration_audit(
            fixture,
            old_space_id=space_ids[0],
            new_space_id=space_id,
            k=k,
        )
        for space_id in space_ids[1:]
    ]
    return {
        "fixture_notice": (
            "hand-authored vectors; validates contracts and metrics, "
            "not real model quality"
        ),
        "k": k,
        "spaces": {
            contract.space_id: {
                "contract": asdict(contract),
                "inventory": inventories[contract.space_id],
                "evaluation": evaluations[contract.space_id],
            }
            for contract in fixture.contracts
        },
        "migrations": migrations,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Offline embedding-space evaluation and migration audit"
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=base / "embedding-fixture.json",
        help="path to a strict JSON fixture",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=3,
        help="number of exact-retrieval results to return (positive integer)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", newline="\n")
    args = parse_args(argv)
    try:
        fixture = load_fixture(args.fixture.resolve())
        report = run_experiment(fixture, k=args.k)
    except EmbeddingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
