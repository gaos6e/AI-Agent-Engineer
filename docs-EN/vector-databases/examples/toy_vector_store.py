"""Single-process JSON vector store for teaching, never for production.

The example demonstrates a versioned space contract, strict persistence,
source-CAS upsert/delete, tenant/ACL filtering, fenced tombstones and exact
search.  It does not provide multi-process locking, database transactions, ANN,
authentication, replication or a production backup protocol.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import isclose, isfinite, sqrt
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence
import unicodedata


Vector = tuple[float, ...]
ALLOWED_METRICS = {"cosine", "dot", "euclidean"}
ALLOWED_DTYPES = {"float32", "float64"}
ALLOWED_STATUSES = {"draft", "published", "archived"}
ALLOWED_FILTERS = {
    "document_id",
    "source_revision",
    "embedding_revision",
    "content_sha256",
    "status",
}
MAX_STORE_BYTES = 20 * 1024 * 1024
MAX_RECORDS = 100_000
NORMALIZED_ABS_TOLERANCE = 1e-6
SCHEMA_VERSION = 2


class StoreError(ValueError):
    """Invalid contract, point, persisted state or query."""


class WriteConflictError(StoreError):
    """A store or source compare-and-set precondition did not hold."""


@dataclass(frozen=True)
class StoreContract:
    space_id: str
    model: str
    embedding_revision: str
    dimension: int
    metric: str
    normalized: bool
    dtype: str

    def validate(self) -> None:
        for name in ("space_id", "model", "embedding_revision", "dtype"):
            _clean_token(name, getattr(self, name))
        if (
            not isinstance(self.dimension, int)
            or isinstance(self.dimension, bool)
            or not 1 <= self.dimension <= 100_000
        ):
            raise StoreError("dimension must be an integer in 1..100000")
        if self.metric not in ALLOWED_METRICS:
            raise StoreError(f"unsupported metric: {self.metric}")
        if not isinstance(self.normalized, bool):
            raise StoreError("normalized must be a boolean")
        if self.dtype not in ALLOWED_DTYPES:
            raise StoreError(f"unsupported dtype: {self.dtype}")

    def signature(self) -> str:
        return _digest(_canonical_json(asdict(self)))


@dataclass(frozen=True)
class Payload:
    tenant_id: str
    document_id: str
    source_revision: str
    embedding_revision: str
    content_sha256: str
    acl: tuple[str, ...]
    status: str

    def validate(self, contract: StoreContract) -> None:
        for name in (
            "tenant_id",
            "document_id",
            "source_revision",
            "embedding_revision",
            "status",
        ):
            _clean_token(name, getattr(self, name))
        if self.embedding_revision != contract.embedding_revision:
            raise StoreError("payload embedding_revision does not match the store contract")
        if (
            not isinstance(self.content_sha256, str)
            or len(self.content_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.content_sha256)
        ):
            raise StoreError("content_sha256 must be 64 lowercase hexadecimal characters")
        if not isinstance(self.acl, tuple) or not self.acl:
            raise StoreError("acl must be a non-empty tuple")
        for group in self.acl:
            _clean_token("acl", group)
        if len(set(self.acl)) != len(self.acl) or self.acl != tuple(sorted(self.acl)):
            raise StoreError("acl must be deduplicated and sorted lexicographically")
        if self.status not in ALLOWED_STATUSES:
            raise StoreError(f"unsupported status: {self.status}")


@dataclass(frozen=True)
class Point:
    point_id: str
    vector: Vector
    payload: Payload


@dataclass(frozen=True)
class ResurrectionToken:
    """Replay fence for one tombstone; it is not an authorization credential."""

    deleted_source_revision: str
    delete_event_id: str

    def validate(self) -> None:
        _clean_token("deleted_source_revision", self.deleted_source_revision)
        _clean_token("delete_event_id", self.delete_event_id)


@dataclass(frozen=True)
class Tombstone:
    point_id: str
    tenant_id: str
    deleted_source_revision: str
    delete_event_id: str
    deleted_at_store_revision: int


@dataclass(frozen=True)
class SearchResult:
    rank: int
    point_id: str
    score: float
    document_id: str
    source_revision: str


@dataclass(frozen=True)
class _LoadedState:
    contract: StoreContract
    store_revision: int
    points: dict[str, Point]
    tombstones: dict[str, Tombstone]


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
        raise StoreError(f"{name} must be a non-empty string without surrounding whitespace")
    if len(value) > maximum or any(ord(character) < 32 for character in value):
        raise StoreError(f"{name} has invalid length or control characters")
    return value


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StoreError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise StoreError(f"non-finite JSON number is not allowed: {value}")


def _require_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise StoreError(
            f"{label} fields must match exactly: expected {sorted(expected)}, actual {sorted(actual)}"
        )


def _read_json(path: Path) -> Any:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise StoreError(f"cannot read store: {path}") from exc
    if size > MAX_STORE_BYTES:
        raise StoreError("store exceeds the 20 MiB teaching limit")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except UnicodeDecodeError as exc:
        raise StoreError("store must be UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise StoreError(
            f"{path.name} JSON error: {exc.lineno}:{exc.colno}"
        ) from exc


def _parse_contract(value: Any) -> StoreContract:
    if not isinstance(value, dict):
        raise StoreError("contract must be an object")
    _require_fields(
        value,
        {
            "space_id",
            "model",
            "embedding_revision",
            "dimension",
            "metric",
            "normalized",
            "dtype",
        },
        "contract",
    )
    contract = StoreContract(
        space_id=value["space_id"],
        model=value["model"],
        embedding_revision=value["embedding_revision"],
        dimension=value["dimension"],
        metric=value["metric"],
        normalized=value["normalized"],
        dtype=value["dtype"],
    )
    contract.validate()
    return contract


def _parse_acl(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise StoreError(f"{label} must be a non-empty list")
    cleaned = tuple(_clean_token(label, group) for group in value)
    if len(set(cleaned)) != len(cleaned):
        raise StoreError(f"{label} must not contain duplicates")
    return tuple(sorted(cleaned))


def _parse_payload(value: Any, contract: StoreContract, label: str) -> Payload:
    if not isinstance(value, dict):
        raise StoreError(f"{label} must be an object")
    _require_fields(
        value,
        {
            "tenant_id",
            "document_id",
            "source_revision",
            "embedding_revision",
            "content_sha256",
            "acl",
            "status",
        },
        label,
    )
    payload = Payload(
        tenant_id=value["tenant_id"],
        document_id=value["document_id"],
        source_revision=value["source_revision"],
        embedding_revision=value["embedding_revision"],
        content_sha256=value["content_sha256"],
        acl=_parse_acl(value["acl"], f"{label}.acl"),
        status=value["status"],
    )
    payload.validate(contract)
    return payload


def _validate_vector(
    value: Sequence[float],
    contract: StoreContract,
    label: str,
) -> Vector:
    if (
        isinstance(value, (str, bytes))
        or not isinstance(value, Sequence)
        or len(value) != contract.dimension
    ):
        actual = len(value) if isinstance(value, Sequence) else "not a sequence"
        raise StoreError(
            f"{label} dimension must be {contract.dimension}, actual {actual}"
        )
    parsed: list[float] = []
    for index, item in enumerate(value):
        if (
            not isinstance(item, (int, float))
            or isinstance(item, bool)
            or not isfinite(float(item))
        ):
            raise StoreError(f"{label}[{index}] must be finite")
        parsed.append(float(item))
    vector = tuple(parsed)
    norm = sqrt(sum(item * item for item in vector))
    if norm == 0.0 or not isfinite(norm):
        raise StoreError(f"{label} must not be a zero vector")
    if contract.normalized and not isclose(
        norm,
        1.0,
        rel_tol=0.0,
        abs_tol=NORMALIZED_ABS_TOLERANCE,
    ):
        raise StoreError(
            f"{label} declares normalized=true, but L2 norm={norm:.9f}"
        )
    return vector


def _parse_point(value: Any, contract: StoreContract, index: int) -> Point:
    label = f"points[{index}]"
    if not isinstance(value, dict):
        raise StoreError(f"{label} must be an object")
    _require_fields(value, {"id", "vector", "payload"}, label)
    point_id = _clean_token("point_id", value["id"])
    vector_value = value["vector"]
    if not isinstance(vector_value, list):
        raise StoreError(f"{label}.vector must be a list")
    vector = _validate_vector(vector_value, contract, f"{label}.vector")
    payload = _parse_payload(value["payload"], contract, f"{label}.payload")
    return Point(point_id=point_id, vector=vector, payload=payload)


def _parse_tombstone(value: Any, store_revision: int, index: int) -> Tombstone:
    label = f"tombstones[{index}]"
    if not isinstance(value, dict):
        raise StoreError(f"{label} must be an object")
    _require_fields(
        value,
        {
            "point_id",
            "tenant_id",
            "deleted_source_revision",
            "delete_event_id",
            "deleted_at_store_revision",
        },
        label,
    )
    point_id = _clean_token("point_id", value["point_id"])
    tenant_id = _clean_token("tenant_id", value["tenant_id"])
    deleted_source_revision = _clean_token(
        "deleted_source_revision",
        value["deleted_source_revision"],
    )
    delete_event_id = _clean_token(
        "delete_event_id",
        value["delete_event_id"],
    )
    revision = value["deleted_at_store_revision"]
    if (
        not isinstance(revision, int)
        or isinstance(revision, bool)
        or not 1 <= revision <= store_revision
    ):
        raise StoreError(f"{label}.deleted_at_store_revision is invalid")
    return Tombstone(
        point_id,
        tenant_id,
        deleted_source_revision,
        delete_event_id,
        revision,
    )


def _load_state(path: Path) -> _LoadedState:
    value = _read_json(path)
    if not isinstance(value, dict):
        raise StoreError("store top level must be an object")
    _require_fields(
        value,
        {
            "schema_version",
            "store_revision",
            "contract",
            "points",
            "tombstones",
        },
        "store",
    )
    if value["schema_version"] == 1:
        raise StoreError(
            "schema_version 1 tombstone lacks a source/delete fence; "
            "automatic migration is unsafe; rebuild schema_version 2 from canonical source"
        )
    if value["schema_version"] != SCHEMA_VERSION:
        raise StoreError(
            f"unsupported schema_version: {value['schema_version']}"
        )
    revision = value["store_revision"]
    if (
        not isinstance(revision, int)
        or isinstance(revision, bool)
        or revision < 0
    ):
        raise StoreError("store_revision must be a non-negative integer")
    contract = _parse_contract(value["contract"])
    if not isinstance(value["points"], list):
        raise StoreError("points must be a list")
    if not isinstance(value["tombstones"], list):
        raise StoreError("tombstones must be a list")
    if len(value["points"]) + len(value["tombstones"]) > MAX_RECORDS:
        raise StoreError("records exceed the teaching limit")
    points: dict[str, Point] = {}
    for index, point_value in enumerate(value["points"]):
        point = _parse_point(point_value, contract, index)
        if point.point_id in points:
            raise StoreError(f"duplicate point_id: {point.point_id}")
        points[point.point_id] = point
    tombstones: dict[str, Tombstone] = {}
    for index, tombstone_value in enumerate(value["tombstones"]):
        tombstone = _parse_tombstone(tombstone_value, revision, index)
        if tombstone.point_id in tombstones:
            raise StoreError(f"duplicate tombstone: {tombstone.point_id}")
        if tombstone.point_id in points:
            raise StoreError(
                f"point and tombstone must not coexist: {tombstone.point_id}"
            )
        tombstones[tombstone.point_id] = tombstone
    return _LoadedState(contract, revision, points, tombstones)


def _payload_to_json(payload: Payload) -> dict[str, Any]:
    return {
        "tenant_id": payload.tenant_id,
        "document_id": payload.document_id,
        "source_revision": payload.source_revision,
        "embedding_revision": payload.embedding_revision,
        "content_sha256": payload.content_sha256,
        "acl": list(payload.acl),
        "status": payload.status,
    }


def _point_to_json(point: Point) -> dict[str, Any]:
    return {
        "id": point.point_id,
        "vector": list(point.vector),
        "payload": _payload_to_json(point.payload),
    }


def _state_to_json(
    contract: StoreContract,
    store_revision: int,
    points: Mapping[str, Point],
    tombstones: Mapping[str, Tombstone],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "store_revision": store_revision,
        "contract": asdict(contract),
        "points": [
            _point_to_json(points[point_id]) for point_id in sorted(points)
        ],
        "tombstones": [
            asdict(tombstones[point_id]) for point_id in sorted(tombstones)
        ],
    }


def similarity(
    left: Vector,
    right: Vector,
    *,
    metric: str,
) -> float:
    if metric not in ALLOWED_METRICS:  # Teaching rationale: see the matching English course lesson.
        raise StoreError(f"unsupported metric: {metric}")  # Teaching rationale: see the matching English course lesson.
    if not left or len(left) != len(right):  # Teaching rationale: see the matching English course lesson.
        raise StoreError("vectors must be non-empty and have the same dimension")  # Teaching rationale: see the matching English course lesson.
    if not all(isfinite(value) for value in (*left, *right)):  # Teaching rationale: see the matching English course lesson.
        raise StoreError("vector contains NaN/Inf")  # Teaching rationale: see the matching English course lesson.
    if metric == "dot":  # Teaching rationale: see the matching English course lesson.
        return sum(a * b for a, b in zip(left, right))  # Teaching rationale: see the matching English course lesson.
    if metric == "euclidean":  # Teaching rationale: see the matching English course lesson.
        return -sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))  # Teaching rationale: see the matching English course lesson.
    left_norm = sqrt(sum(value * value for value in left))  # Teaching rationale: see the matching English course lesson.
    right_norm = sqrt(sum(value * value for value in right))  # Teaching rationale: see the matching English course lesson.
    if left_norm == 0.0 or right_norm == 0.0:  # Teaching rationale: see the matching English course lesson.
        raise StoreError("a zero vector has no cosine direction")  # Teaching rationale: see the matching English course lesson.
    return sum(a * b for a, b in zip(left, right)) / (  # Teaching rationale: see the matching English course lesson.
        left_norm * right_norm  # Teaching rationale: see the matching English course lesson.
    )


class ToyVectorStore:
    """Strict, single-process teaching store backed by one JSON file."""

    def __init__(self, path: Path, contract: StoreContract) -> None:
        contract.validate()
        self.path = path.resolve()
        if self.path.exists():
            loaded = _load_state(self.path)
            if loaded.contract != contract:
                raise StoreError("existing store contract does not match the requested contract")
            self.contract = loaded.contract
            self.store_revision = loaded.store_revision
            self.points = loaded.points
            self.tombstones = loaded.tombstones
            self._file_seen = True
        else:
            self.contract = contract
            self.store_revision = 0
            self.points: dict[str, Point] = {}
            self.tombstones: dict[str, Tombstone] = {}
            self._file_seen = False

    def _check_disk_revision(self) -> None:
        exists = self.path.exists()
        if self._file_seen and not exists:
            raise WriteConflictError("store file disappeared after loading")
        if not self._file_seen and exists:
            raise WriteConflictError("store file was created by another writer")
        if exists:
            loaded = _load_state(self.path)
            if loaded.contract != self.contract:
                raise WriteConflictError("on-disk contract changed")
            if loaded.store_revision != self.store_revision:
                raise WriteConflictError(
                    "on-disk revision changed; refusing to overwrite newer state"
                )

    def _commit(
        self,
        points: dict[str, Point],
        tombstones: dict[str, Tombstone],
    ) -> None:
        if len(points) + len(tombstones) > MAX_RECORDS:  # Teaching rationale: see the matching English course lesson.
            raise StoreError("records exceed the teaching limit")  # Teaching rationale: see the matching English course lesson.
        self._check_disk_revision()  # Teaching rationale: see the matching English course lesson.
        next_revision = self.store_revision + 1  # Teaching rationale: see the matching English course lesson.
        value = _state_to_json(  # Teaching rationale: see the matching English course lesson.
            self.contract,
            next_revision,
            points,
            tombstones,
        )
        encoded = json.dumps(  # Teaching rationale: see the matching English course lesson.
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        ) + "\n"
        if len(encoded.encode("utf-8")) > MAX_STORE_BYTES:  # Teaching rationale: see the matching English course lesson.
            raise StoreError("serialized store UTF-8 bytes exceed the teaching limit")  # Teaching rationale: see the matching English course lesson.
        self.path.parent.mkdir(parents=True, exist_ok=True)  # Teaching rationale: see the matching English course lesson.
        temporary = self.path.with_name(  # Teaching rationale: see the matching English course lesson.
            f"{self.path.name}.{os.getpid()}.tmp"
        )
        try:  # Teaching rationale: see the matching English course lesson.
            with temporary.open(  # Teaching rationale: see the matching English course lesson.
                "w", encoding="utf-8", newline="\n"
            ) as handle:
                handle.write(encoded)  # Teaching rationale: see the matching English course lesson.
                handle.flush()  # Teaching rationale: see the matching English course lesson.
                os.fsync(handle.fileno())  # Teaching rationale: see the matching English course lesson.
            os.replace(temporary, self.path)  # Teaching rationale: see the matching English course lesson.
        finally:  # Teaching rationale: see the matching English course lesson.
            temporary.unlink(missing_ok=True)  # Teaching rationale: see the matching English course lesson.
        self.points = points  # Teaching rationale: see the matching English course lesson.
        self.tombstones = tombstones  # Teaching rationale: see the matching English course lesson.
        self.store_revision = next_revision  # Teaching rationale: see the matching English course lesson.
        self._file_seen = True  # Teaching rationale: see the matching English course lesson.

    def upsert(
        self,
        point_id: str,
        vector: Sequence[float],
        payload: Payload,
        *,
        expected_source_revision: str | None = None,
        resurrect_from: ResurrectionToken | None = None,
    ) -> str:
        """Create, idempotently replay, CAS-update or explicitly resurrect."""

        point_id = _clean_token("point_id", point_id)
        if expected_source_revision is not None:
            expected_source_revision = _clean_token(
                "expected_source_revision",
                expected_source_revision,
            )
        if resurrect_from is not None:
            if not isinstance(resurrect_from, ResurrectionToken):
                raise StoreError("resurrect_from must be a ResurrectionToken")
            resurrect_from.validate()
        if not isinstance(payload, Payload):
            raise StoreError("payload must be a Payload")
        payload.validate(self.contract)
        checked_vector = _validate_vector(
            vector,
            self.contract,
            f"{point_id}.vector",
        )
        candidate = Point(point_id, checked_vector, payload)
        existing = self.points.get(point_id)
        if existing is not None:
            if existing.payload.tenant_id != payload.tenant_id:
                raise StoreError("the same point_id must not move across tenants")
            if existing == candidate:
                self._check_disk_revision()
                return "unchanged"
            if existing.payload.source_revision == payload.source_revision:
                raise WriteConflictError(
                    "same source revision has different vector/payload; refusing overwrite"
                )
            if resurrect_from is not None:
                raise WriteConflictError(
                    "the current point is not deleted; resurrection token is not accepted"
                )
            if expected_source_revision != existing.payload.source_revision:
                raise WriteConflictError(
                    "expected source revision does not match current value; refusing stale upsert"
                )
            outcome = "updated"
        else:
            tombstone = self.tombstones.get(point_id)
            if tombstone is not None:
                if tombstone.tenant_id != payload.tenant_id:
                    raise StoreError("a deleted point_id must not be reused across tenants")
                expected_token = ResurrectionToken(
                    tombstone.deleted_source_revision,
                    tombstone.delete_event_id,
                )
                if resurrect_from != expected_token:
                    raise WriteConflictError(
                        "resurrection token does not match the tombstone fence"
                    )
                if payload.source_revision == tombstone.deleted_source_revision:
                    raise WriteConflictError(
                        "resurrection must use a new source revision"
                    )
                if expected_source_revision is not None:
                    raise WriteConflictError(
                        "resurrection uses a tombstone token and does not accept active-revision CAS"
                    )
                outcome = "resurrected"
            else:
                if resurrect_from is not None:
                    raise WriteConflictError(
                        "point has no tombstone matching the resurrection token"
                    )
                if expected_source_revision is not None:
                    raise WriteConflictError(
                        "point does not exist and expected source revision has no match"
                    )
                outcome = "created"

        points = dict(self.points)
        points[point_id] = candidate
        tombstones = dict(self.tombstones)
        tombstones.pop(point_id, None)
        self._commit(points, tombstones)
        return outcome

    def delete(
        self,
        point_id: str,
        *,
        tenant_id: str,
        expected_source_revision: str,
        delete_event_id: str,
    ) -> bool:
        """Persist a fenced deletion intent, even before the point is indexed."""

        point_id = _clean_token("point_id", point_id)
        tenant_id = _clean_token("tenant_id", tenant_id)
        expected_source_revision = _clean_token(
            "expected_source_revision",
            expected_source_revision,
        )
        delete_event_id = _clean_token("delete_event_id", delete_event_id)
        existing = self.points.get(point_id)
        if existing is None:
            tombstone = self.tombstones.get(point_id)
            if tombstone is None:
                tombstones = dict(self.tombstones)
                tombstones[point_id] = Tombstone(
                    point_id,
                    tenant_id,
                    expected_source_revision,
                    delete_event_id,
                    self.store_revision + 1,
                )
                self._commit(dict(self.points), tombstones)
                return True
            if (
                tombstone.tenant_id == tenant_id
                and tombstone.deleted_source_revision == expected_source_revision
                and tombstone.delete_event_id == delete_event_id
            ):
                self._check_disk_revision()
                return False
            raise WriteConflictError(
                "delete replay does not match the tombstone tenant/source/event fence"
            )
        if existing.payload.tenant_id != tenant_id:
            raise WriteConflictError("delete must not cross tenants")
        if existing.payload.source_revision != expected_source_revision:
            raise WriteConflictError(
                "expected source revision does not match current value; refusing stale delete"
            )
        points = dict(self.points)
        del points[point_id]
        tombstones = dict(self.tombstones)
        tombstones[point_id] = Tombstone(
            point_id,
            tenant_id,
            expected_source_revision,
            delete_event_id,
            self.store_revision + 1,
        )
        self._commit(points, tombstones)
        return True

    def search(
        self,
        query: Sequence[float],
        *,
        top_k: int,
        tenant_id: str,
        subject_groups: Sequence[str],
        filters: Mapping[str, str] | None = None,
    ) -> list[SearchResult]:
        self._check_disk_revision()  # Teaching rationale: see the matching English course lesson.
        if (
            not isinstance(top_k, int)
            or isinstance(top_k, bool)
            or top_k <= 0
        ):
            raise StoreError("top_k must be a positive integer")
        tenant_id = _clean_token("tenant_id", tenant_id)  # Teaching rationale: see the matching English course lesson.
        groups = {  # Teaching rationale: see the matching English course lesson.
            _clean_token("subject_group", group)  # Teaching rationale: see the matching English course lesson.
            for group in subject_groups  # Teaching rationale: see the matching English course lesson.
        }
        if not groups:  # Teaching rationale: see the matching English course lesson.
            return []  # Teaching rationale: see the matching English course lesson.
        checked_query = _validate_vector(
            query,
            self.contract,
            "query",
        )
        filters = filters or {}  # Teaching rationale: see the matching English course lesson.
        if not isinstance(filters, Mapping):  # Teaching rationale: see the matching English course lesson.
            raise StoreError("filters must be a mapping")  # Teaching rationale: see the matching English course lesson.
        checked_filters: dict[str, str] = {}  # Teaching rationale: see the matching English course lesson.
        for key, value in filters.items():  # Teaching rationale: see the matching English course lesson.
            if key not in ALLOWED_FILTERS:  # Teaching rationale: see the matching English course lesson.
                raise StoreError(f"disallowed filter field: {key}")  # Teaching rationale: see the matching English course lesson.
            checked_filters[key] = _clean_token(f"filter.{key}", value)  # Teaching rationale: see the matching English course lesson.

        scored: list[tuple[float, Point]] = []  # Teaching rationale: see the matching English course lesson.
        for point in self.points.values():  # Teaching rationale: see the matching English course lesson.
            payload = point.payload  # Teaching rationale: see the matching English course lesson.
            if payload.tenant_id != tenant_id:  # Teaching rationale: see the matching English course lesson.
                continue  # Teaching rationale: see the matching English course lesson.
            if payload.status != "published":  # Teaching rationale: see the matching English course lesson.
                continue  # Teaching rationale: see the matching English course lesson.
            if not groups.intersection(payload.acl):  # Teaching rationale: see the matching English course lesson.
                continue  # Teaching rationale: see the matching English course lesson.
            payload_dict = _payload_to_json(payload)  # Teaching rationale: see the matching English course lesson.
            if any(  # Teaching rationale: see the matching English course lesson.
                payload_dict.get(key) != value
                for key, value in checked_filters.items()
            ):
                continue  # Teaching rationale: see the matching English course lesson.
            score = similarity(  # Teaching rationale: see the matching English course lesson.
                checked_query,
                point.vector,
                metric=self.contract.metric,
            )
            scored.append((score, point))  # Teaching rationale: see the matching English course lesson.
        scored.sort(key=lambda row: (-row[0], row[1].point_id))  # Teaching rationale: see the matching English course lesson.
        return [  # Teaching rationale: see the matching English course lesson.
            SearchResult(
                rank=index,
                point_id=point.point_id,
                score=score,
                document_id=point.payload.document_id,
                source_revision=point.payload.source_revision,
            )
            for index, (score, point) in enumerate(
                scored[:top_k], start=1
            )
        ]

    def snapshot_summary(self) -> dict[str, Any]:
        self._check_disk_revision()
        return {
            "schema_version": SCHEMA_VERSION,
            "store_revision": self.store_revision,
            "contract_signature": self.contract.signature(),
            "point_count": len(self.points),
            "tombstone_count": len(self.tombstones),
            "point_ids": sorted(self.points),
            "tombstone_ids": sorted(self.tombstones),
        }


def _demo_payload(
    *,
    tenant_id: str,
    document_id: str,
    source_revision: str,
    text: str,
    acl: tuple[str, ...],
) -> Payload:
    return Payload(
        tenant_id=tenant_id,
        document_id=document_id,
        source_revision=source_revision,
        embedding_revision="toy-embedding-r1",
        content_sha256=_digest(_normalise_text(text)),
        acl=tuple(sorted(acl)),
        status="published",
    )


def demo(path: Path) -> dict[str, Any]:
    contract = StoreContract(
        space_id="toy-space-v1",
        model="hand-authored-vectors",
        embedding_revision="toy-embedding-r1",
        dimension=2,
        metric="cosine",
        normalized=True,
        dtype="float32",
    )
    store = ToyVectorStore(path, contract)
    outcomes = {
        "a-1": store.upsert(
            "a-1",
            (1.0, 0.0),
            _demo_payload(
                tenant_id="alpha",
                document_id="doc-timeout",
                source_revision="r1",
                text="The connection timeout is three seconds.",
                acl=("employees",),
            ),
        ),
        "a-2-initial": store.upsert(
            "a-2",
            (0.8, 0.6),
            _demo_payload(
                tenant_id="alpha",
                document_id="doc-retry",
                source_revision="r1",
                text="A network timeout can be retried.",
                acl=("employees",),
            ),
        ),
        "b-1": store.upsert(
            "b-1",
            (1.0, 0.0),
            _demo_payload(
                tenant_id="beta",
                document_id="doc-private",
                source_revision="r1",
                text="Private content from another tenant.",
                acl=("employees",),
            ),
        ),
        "a-2-update": store.upsert(
            "a-2",
            (0.6, 0.8),
            _demo_payload(
                tenant_id="alpha",
                document_id="doc-retry",
                source_revision="r2",
                text="A network timeout can be retried; authentication failure must not be retried.",
                acl=("employees",),
            ),
            expected_source_revision="r1",
        ),
    }
    outcomes["a-2-repeat"] = store.upsert(
        "a-2",
        (0.6, 0.8),
        _demo_payload(
            tenant_id="alpha",
            document_id="doc-retry",
            source_revision="r2",
            text="A network timeout can be retried; authentication failure must not be retried.",
            acl=("employees",),
        ),
        expected_source_revision="r1",
    )
    before_delete = store.search(
        (1.0, 0.0),
        top_k=5,
        tenant_id="alpha",
        subject_groups=("employees",),
    )
    deleted = store.delete(
        "a-1",
        tenant_id="alpha",
        expected_source_revision="r1",
        delete_event_id="delete-a-1-r1",
    )
    after_delete = store.search(
        (1.0, 0.0),
        top_k=5,
        tenant_id="alpha",
        subject_groups=("employees",),
    )
    return {
        "notice": (
            "single-process teaching store; no ANN, transactions, "
            "authentication, replication or production backup"
        ),
        "outcomes": outcomes,
        "alpha_before_delete": [asdict(item) for item in before_delete],
        "deleted_a_1": deleted,
        "alpha_after_delete": [asdict(item) for item in after_delete],
        "summary": store.snapshot_summary(),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Single-process teaching vector store backed by strict JSON"
    )
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("command", choices=("demo",))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", newline="\n")
    args = parse_args(argv)
    if args.command == "demo":
        report = demo(args.db)
    else:
        raise StoreError(f"unsupported command: {args.command}")
    print(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()
