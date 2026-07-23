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
            raise StoreError("dimension 必须是 1..100000 的整数")
        if self.metric not in ALLOWED_METRICS:
            raise StoreError(f"不支持的 metric：{self.metric}")
        if not isinstance(self.normalized, bool):
            raise StoreError("normalized 必须是 boolean")
        if self.dtype not in ALLOWED_DTYPES:
            raise StoreError(f"不支持的 dtype：{self.dtype}")

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
            raise StoreError("payload embedding_revision 与 store contract 不一致")
        if (
            not isinstance(self.content_sha256, str)
            or len(self.content_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.content_sha256)
        ):
            raise StoreError("content_sha256 必须是 64 位小写十六进制")
        if not isinstance(self.acl, tuple) or not self.acl:
            raise StoreError("acl 必须是非空 tuple")
        for group in self.acl:
            _clean_token("acl", group)
        if len(set(self.acl)) != len(self.acl) or self.acl != tuple(sorted(self.acl)):
            raise StoreError("acl 必须去重并按字典序排列")
        if self.status not in ALLOWED_STATUSES:
            raise StoreError(f"不支持的 status：{self.status}")


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
        raise StoreError(f"{name} 必须是无首尾空白的非空字符串")
    if len(value) > maximum or any(ord(character) < 32 for character in value):
        raise StoreError(f"{name} 长度或控制字符不合法")
    return value


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StoreError(f"JSON 出现重复字段：{key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise StoreError(f"JSON 不允许非有限数值：{value}")


def _require_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise StoreError(
            f"{label} 字段必须精确为 {sorted(expected)}，实际为 {sorted(actual)}"
        )


def _read_json(path: Path) -> Any:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise StoreError(f"无法读取 store：{path}") from exc
    if size > MAX_STORE_BYTES:
        raise StoreError("store 超过 20 MiB 教学上限")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except UnicodeDecodeError as exc:
        raise StoreError("store 必须是 UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise StoreError(
            f"{path.name} JSON 错误：{exc.lineno}:{exc.colno}"
        ) from exc


def _parse_contract(value: Any) -> StoreContract:
    if not isinstance(value, dict):
        raise StoreError("contract 必须是 object")
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
        raise StoreError(f"{label} 必须是非空数组")
    cleaned = tuple(_clean_token(label, group) for group in value)
    if len(set(cleaned)) != len(cleaned):
        raise StoreError(f"{label} 不得重复")
    return tuple(sorted(cleaned))


def _parse_payload(value: Any, contract: StoreContract, label: str) -> Payload:
    if not isinstance(value, dict):
        raise StoreError(f"{label} 必须是 object")
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
        actual = len(value) if isinstance(value, Sequence) else "非序列"
        raise StoreError(
            f"{label} 维度必须是 {contract.dimension}，实际为 {actual}"
        )
    parsed: list[float] = []
    for index, item in enumerate(value):
        if (
            not isinstance(item, (int, float))
            or isinstance(item, bool)
            or not isfinite(float(item))
        ):
            raise StoreError(f"{label}[{index}] 必须是有限数值")
        parsed.append(float(item))
    vector = tuple(parsed)
    norm = sqrt(sum(item * item for item in vector))
    if norm == 0.0 or not isfinite(norm):
        raise StoreError(f"{label} 不得是零向量")
    if contract.normalized and not isclose(
        norm,
        1.0,
        rel_tol=0.0,
        abs_tol=NORMALIZED_ABS_TOLERANCE,
    ):
        raise StoreError(
            f"{label} 声明 normalized=true，但 L2 norm={norm:.9f}"
        )
    return vector


def _parse_point(value: Any, contract: StoreContract, index: int) -> Point:
    label = f"points[{index}]"
    if not isinstance(value, dict):
        raise StoreError(f"{label} 必须是 object")
    _require_fields(value, {"id", "vector", "payload"}, label)
    point_id = _clean_token("point_id", value["id"])
    vector_value = value["vector"]
    if not isinstance(vector_value, list):
        raise StoreError(f"{label}.vector 必须是数组")
    vector = _validate_vector(vector_value, contract, f"{label}.vector")
    payload = _parse_payload(value["payload"], contract, f"{label}.payload")
    return Point(point_id=point_id, vector=vector, payload=payload)


def _parse_tombstone(value: Any, store_revision: int, index: int) -> Tombstone:
    label = f"tombstones[{index}]"
    if not isinstance(value, dict):
        raise StoreError(f"{label} 必须是 object")
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
        raise StoreError(f"{label}.deleted_at_store_revision 不合法")
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
        raise StoreError("store 顶层必须是 object")
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
            "schema_version 1 tombstone 缺少 source/delete fence，"
            "无法安全自动迁移；请从 canonical source 重建 schema_version 2"
        )
    if value["schema_version"] != SCHEMA_VERSION:
        raise StoreError(
            f"不支持 schema_version：{value['schema_version']}"
        )
    revision = value["store_revision"]
    if (
        not isinstance(revision, int)
        or isinstance(revision, bool)
        or revision < 0
    ):
        raise StoreError("store_revision 必须是非负整数")
    contract = _parse_contract(value["contract"])
    if not isinstance(value["points"], list):
        raise StoreError("points 必须是数组")
    if not isinstance(value["tombstones"], list):
        raise StoreError("tombstones 必须是数组")
    if len(value["points"]) + len(value["tombstones"]) > MAX_RECORDS:
        raise StoreError("records 超过教学上限")
    points: dict[str, Point] = {}
    for index, point_value in enumerate(value["points"]):
        point = _parse_point(point_value, contract, index)
        if point.point_id in points:
            raise StoreError(f"point_id 重复：{point.point_id}")
        points[point.point_id] = point
    tombstones: dict[str, Tombstone] = {}
    for index, tombstone_value in enumerate(value["tombstones"]):
        tombstone = _parse_tombstone(tombstone_value, revision, index)
        if tombstone.point_id in tombstones:
            raise StoreError(f"tombstone 重复：{tombstone.point_id}")
        if tombstone.point_id in points:
            raise StoreError(
                f"point 与 tombstone 不得同时存在：{tombstone.point_id}"
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
    if metric not in ALLOWED_METRICS:  # 只执行 store contract 声明支持的度量。
        raise StoreError(f"不支持的 metric：{metric}")  # 拼写或契约错误不能静默选用默认算法。
    if not left or len(left) != len(right):  # 所有三种度量都要求非空且同维的向量。
        raise StoreError("向量必须非空且维度相同")  # 不允许 zip 截断掩盖错维问题。
    if not all(isfinite(value) for value in (*left, *right)):  # NaN/Inf 会破坏排序稳定性和 JSON 持久化。
        raise StoreError("向量包含 NaN/Inf")  # 在计算前 fail closed。
    if metric == "dot":  # 点积保留向量长度信息，适用于契约明确采用 dot 的空间。
        return sum(a * b for a, b in zip(left, right))  # 每一维相乘后求和，分数越大越相似。
    if metric == "euclidean":  # 欧氏距离本身越小越近，但本 API 统一按分数降序。
        return -sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))  # 因此返回负距离。
    left_norm = sqrt(sum(value * value for value in left))  # 计算左向量的 L2 长度。
    right_norm = sqrt(sum(value * value for value in right))  # 计算右向量的 L2 长度。
    if left_norm == 0.0 or right_norm == 0.0:  # 零向量没有方向，cosine 没有定义。
        raise StoreError("零向量没有 cosine 方向")  # 不伪造为 0 分，避免隐藏数据质量问题。
    return sum(a * b for a, b in zip(left, right)) / (  # 以点积除两边范数得到 cosine similarity。
        left_norm * right_norm  # 分母为两个向量长度的乘积。
    )


class ToyVectorStore:
    """Strict, single-process teaching store backed by one JSON file."""

    def __init__(self, path: Path, contract: StoreContract) -> None:
        contract.validate()
        self.path = path.resolve()
        if self.path.exists():
            loaded = _load_state(self.path)
            if loaded.contract != contract:
                raise StoreError("现有 store contract 与请求契约不一致")
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
            raise WriteConflictError("store 文件在加载后消失")
        if not self._file_seen and exists:
            raise WriteConflictError("store 文件被另一写入者创建")
        if exists:
            loaded = _load_state(self.path)
            if loaded.contract != self.contract:
                raise WriteConflictError("磁盘 contract 已变化")
            if loaded.store_revision != self.store_revision:
                raise WriteConflictError(
                    "磁盘 revision 已变化，拒绝覆盖较新状态"
                )

    def _commit(
        self,
        points: dict[str, Point],
        tombstones: dict[str, Tombstone],
    ) -> None:
        if len(points) + len(tombstones) > MAX_RECORDS:  # 先限制 live point 与 tombstone 的总数。
            raise StoreError("records 超过教学上限")  # 超限时不创建临时文件，也不修改内存状态。
        self._check_disk_revision()  # 提交前检查磁盘是否已被其他实例推进。
        next_revision = self.store_revision + 1  # 每次真实状态变更都分配单调递增版本。
        value = _state_to_json(  # 将内存对象转成严格、可持久化的 JSON 状态。
            self.contract,
            next_revision,
            points,
            tombstones,
        )
        encoded = json.dumps(  # 规范序列化，确保写盘时拒绝 NaN 并使用稳定键顺序。
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        ) + "\n"
        if len(encoded.encode("utf-8")) > MAX_STORE_BYTES:  # 按真实 UTF-8 字节而非 Python 字符数执行容量边界。
            raise StoreError("序列化 store 的 UTF-8 bytes 超过教学上限")  # 超限时保持旧状态不变。
        self.path.parent.mkdir(parents=True, exist_ok=True)  # 确保父目录存在，再创建同目录临时文件。
        temporary = self.path.with_name(  # 临时文件与目标同目录，os.replace 才尽可能保持原子替换语义。
            f"{self.path.name}.{os.getpid()}.tmp"
        )
        try:  # 无论写入或替换是否失败，finally 都会清除残留临时文件。
            with temporary.open(  # 以 UTF-8/LF 写出跨平台稳定的 JSON 文件。
                "w", encoding="utf-8", newline="\n"
            ) as handle:
                handle.write(encoded)  # 一次写入已验证大小和语法的完整状态。
                handle.flush()  # 把 Python 缓冲区内容交给操作系统。
                os.fsync(handle.fileno())  # 请求同步文件数据；这仍不等同 WAL 或事务。
            os.replace(temporary, self.path)  # 用同目录替换发布新版本文件。
        finally:  # 替换成功后文件不存在，失败后则负责删除临时残片。
            temporary.unlink(missing_ok=True)  # 只删除上面明确构造的临时路径。
        self.points = points  # 仅在落盘替换成功后更新本实例的内存状态。
        self.tombstones = tombstones  # 同步更新当前 deletion fence 映射。
        self.store_revision = next_revision  # 记录已成功发布的新 revision。
        self._file_seen = True  # 后续操作将要求该文件持续存在且 revision 不漂移。

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
                raise StoreError("resurrect_from 必须是 ResurrectionToken")
            resurrect_from.validate()
        if not isinstance(payload, Payload):
            raise StoreError("payload 必须是 Payload")
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
                raise StoreError("同一 point_id 不得跨 tenant 转移")
            if existing == candidate:
                self._check_disk_revision()
                return "unchanged"
            if existing.payload.source_revision == payload.source_revision:
                raise WriteConflictError(
                    "same source revision 对应不同 vector/payload，拒绝覆盖"
                )
            if resurrect_from is not None:
                raise WriteConflictError(
                    "当前 point 未删除，不接受 resurrection token"
                )
            if expected_source_revision != existing.payload.source_revision:
                raise WriteConflictError(
                    "expected source revision 与当前值不一致，拒绝 stale upsert"
                )
            outcome = "updated"
        else:
            tombstone = self.tombstones.get(point_id)
            if tombstone is not None:
                if tombstone.tenant_id != payload.tenant_id:
                    raise StoreError("已删除 point_id 不得跨 tenant 复用")
                expected_token = ResurrectionToken(
                    tombstone.deleted_source_revision,
                    tombstone.delete_event_id,
                )
                if resurrect_from != expected_token:
                    raise WriteConflictError(
                        "resurrection token 与 tombstone fence 不一致"
                    )
                if payload.source_revision == tombstone.deleted_source_revision:
                    raise WriteConflictError(
                        "resurrection 必须使用 new source revision"
                    )
                if expected_source_revision is not None:
                    raise WriteConflictError(
                        "resurrection 使用 tombstone token，不接受 active revision CAS"
                    )
                outcome = "resurrected"
            else:
                if resurrect_from is not None:
                    raise WriteConflictError(
                        "point 没有 tombstone，resurrection token 无匹配对象"
                    )
                if expected_source_revision is not None:
                    raise WriteConflictError(
                        "point 不存在，expected source revision 无匹配对象"
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
                "delete replay 与 tombstone 的 tenant/source/event fence 不一致"
            )
        if existing.payload.tenant_id != tenant_id:
            raise WriteConflictError("delete 不得跨 tenant")
        if existing.payload.source_revision != expected_source_revision:
            raise WriteConflictError(
                "expected source revision 与当前值不一致，拒绝 stale delete"
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
        self._check_disk_revision()  # 公开读取前先拒绝 stale 实例，避免返回旧 ACL 或删除状态。
        if (
            not isinstance(top_k, int)
            or isinstance(top_k, bool)
            or top_k <= 0
        ):
            raise StoreError("top_k 必须是正整数")
        tenant_id = _clean_token("tenant_id", tenant_id)  # 规范化可信调用方传入的租户标识。
        groups = {  # 逐个验证主体组，再转为集合以便 ACL 求交。
            _clean_token("subject_group", group)  # 空白或控制字符组名会在这里被拒绝。
            for group in subject_groups  # 遍历调用方的所有已认证组。
        }
        if not groups:  # 没有组上下文时不能默认把任何 point 视为可见。
            return []  # fail closed，返回空结果。
        checked_query = _validate_vector(
            query,
            self.contract,
            "query",
        )
        filters = filters or {}  # 未提供业务 filter 时使用空对象，但安全 filter 仍会执行。
        if not isinstance(filters, Mapping):  # 只接受键值映射，避免列表等形状带来歧义。
            raise StoreError("filters 必须是 mapping")  # API 边界明确失败。
        checked_filters: dict[str, str] = {}  # 只保存 allow-list 中通过校验的业务 predicate。
        for key, value in filters.items():  # 逐字段处理，绝不把任意 payload 字段开放给客户端。
            if key not in ALLOWED_FILTERS:  # tenant、ACL、status 等安全字段不在用户 filter allow-list 内。
                raise StoreError(f"不允许的 filter 字段：{key}")  # 拒绝未知或越权筛选字段。
            checked_filters[key] = _clean_token(f"filter.{key}", value)  # 规范化合法业务 filter 的字符串值。

        scored: list[tuple[float, Point]] = []  # 仅保存已通过所有强制过滤的候选。
        for point in self.points.values():  # 这个玩具实现逐条扫描，因此是 exact 而非 ANN。
            payload = point.payload  # 读取与向量绑定的 tenant、ACL、状态和版本元数据。
            if payload.tenant_id != tenant_id:  # 首先执行最强的租户隔离。
                continue  # 其他租户的向量绝不能进入评分。
            if payload.status != "published":  # 草稿和归档记录不应服务在线检索。
                continue  # 在算相似度前剔除不可发布内容。
            if not groups.intersection(payload.acl):  # 主体至少要命中一个 ACL group。
                continue  # ACL 失败同样不能产生分数、日志候选或缓存条目。
            payload_dict = _payload_to_json(payload)  # 将受控 payload 转成统一字段表示以检查业务 filter。
            if any(  # 所有用户业务 filter 都必须匹配，语义为 AND。
                payload_dict.get(key) != value
                for key, value in checked_filters.items()
            ):
                continue  # 某一个业务条件不满足就跳过该 point。
            score = similarity(  # 只对已授权、已发布且业务匹配的 point 计算分数。
                checked_query,
                point.vector,
                metric=self.contract.metric,
            )
            scored.append((score, point))  # 保存 exact 分数和 point，供稳定排序。
        scored.sort(key=lambda row: (-row[0], row[1].point_id))  # 分数降序、ID 升序打破平分，结果可重放。
        return [  # 转换为不含原始向量或 ACL 的最小搜索结果。
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
                text="连接超时为三秒。",
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
                text="网络超时可以重试。",
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
                text="另一租户的私有内容。",
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
                text="网络超时可以重试，认证失败不得重试。",
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
            text="网络超时可以重试，认证失败不得重试。",
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
        description="严格 JSON 上的单进程教学向量存储"
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
        raise StoreError(f"不支持的 command：{args.command}")
    print(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()
