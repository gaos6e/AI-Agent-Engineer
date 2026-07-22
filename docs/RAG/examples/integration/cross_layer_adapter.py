"""Cross-layer adapter capstone for the local parsing, KB, chunking, and RAG labs.

The module imports the four existing teaching implementations and joins their
real contracts.  It remains an offline reference implementation: the source
connector is a deterministic fixture materializer, SQLite is local, retrieval
is lexical, and no model or network is used.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sqlite3
import sys
import tempfile
from typing import Any, Iterable, Sequence
import unicodedata


FIXTURE_SCHEMA_VERSION = "cross-layer-fixture-v1"
PUBLIC_SCHEMA_VERSION = "cross-layer-public-v1"
AUDIT_SCHEMA_VERSION = "cross-layer-audit-v1"
CAPTURE_SCHEMA_VERSION = "cross-layer-capture-v1"
ARTIFACT_SCHEMA_VERSION = "cross-layer-eval-v1"
EXTERNAL_BUNDLE_SCHEMA_VERSION = "external-provenance-bundle-v2"
EXTERNAL_CANONICALIZATION_REVISION = (
    "ai-agent-engineer/restricted-canonical-json/v1"
)
ADAPTER_REVISION = "cross-layer-adapter-v1"
MAPPING_REVISION = "parser-line-to-namespaced-lexical-v1"
HARNESS_REVISION = "cross-layer-harness-v1"
NORMALIZER_REVISION = "utf8-no-bom-lf-nfc-v1"
SOURCE_ID_SCHEME = "ai-agent-engineer/logical-source/v1"
ELEMENT_ID_SCHEME = "ai-agent-engineer/namespaced-parser-element/v1"
CHUNK_ID_SCHEME = "chunking-lab/chunk/v1"
INDEX_ID_SCHEME = "chunking-lab/index-entry/v1"
KB_REVISION_SCHEME = "ai-agent-engineer/knowledge-revision/v1"
KB_LOCATOR_SCHEME = "knowledge-store/sqlite-revision/v1"
GENERATION_ID_SCHEME = "ai-agent-engineer/cross-layer-generation/v1"
PARSER_REVISION_SCHEME = "document-inspector/parse-revision/v2"
PARSER_ELEMENT_SCHEME = "document-inspector/element/v2"
LEXICAL_COORDINATE_SPACE = "element-lexical-unit-0-based-half-open-v1"
KNOWLEDGE_STATE_REVISION = "knowledge-store/source-build-state/v1"
EVIDENCE_LEVEL = "document-revision-bridge"
HEX64 = r"^[0-9a-f]{64}$"
MAX_SOURCE_BYTES = 100_000
MAX_DOCUMENTS = 32
MAX_QUERIES = 64
MAX_FIXTURE_BYTES = 2_000_000
MAX_JSON_DEPTH = 64


class IntegrationError(ValueError):
    """The fixture, native artifact, adapter, or evidence chain is invalid."""


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


DOCS_ROOT = Path(__file__).resolve().parents[3]
PARSER_PATH = DOCS_ROOT / "文档解析" / "examples" / "inspect_documents.py"
KB_PATH = DOCS_ROOT / "知识库构建" / "examples" / "knowledge_store.py"
CHUNK_PATH = DOCS_ROOT / "Chunking策略" / "examples" / "chunking_lab.py"
PROVENANCE_PATH = (
    DOCS_ROOT / "RAG" / "examples" / "provenance" / "offline_provenance_pipeline.py"
)

PARSER = _load_module("cross_layer_parser", PARSER_PATH)
KB = _load_module("cross_layer_kb", KB_PATH)
CHUNK = _load_module("cross_layer_chunk", CHUNK_PATH)
PROVENANCE = _load_module("cross_layer_provenance", PROVENANCE_PATH)


def _reject_constant(value: str) -> None:
    raise IntegrationError(f"JSON 不允许非有限数值：{value}")


def _reject_float(_value: str) -> None:
    raise IntegrationError("JSON 浮点数不属于本项目受限 canonical 域")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise IntegrationError("JSON 对象含重复 key")
        result[key] = value
    return result


def _reject_invalid_unicode(value: Any) -> None:
    """Reject decoded JSON strings/keys that cannot form strict UTF-8 evidence."""

    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise IntegrationError("JSON 含非法 Unicode") from exc
        return
    if isinstance(value, list):
        for item in value:
            _reject_invalid_unicode(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_invalid_unicode(key)
            _reject_invalid_unicode(item)


def _reject_excessive_json_nesting(text: str) -> None:
    """Bound container nesting before CPython's recursive decoder runs."""

    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise IntegrationError(
                    f"JSON 容器嵌套不得超过 {MAX_JSON_DEPTH} 层"
                )
        elif character in "]}":
            depth = max(0, depth - 1)


def strict_json_loads(text: str) -> Any:
    if not isinstance(text, str):
        raise IntegrationError("fixture 必须是 JSON 文本")
    try:
        raw = text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise IntegrationError("fixture 含非法 Unicode") from exc
    if len(raw) > MAX_FIXTURE_BYTES:
        raise IntegrationError(f"fixture 不得超过 {MAX_FIXTURE_BYTES} UTF-8 bytes")
    _reject_excessive_json_nesting(text)
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_reject_float,
        )
    except IntegrationError:
        raise
    except json.JSONDecodeError as exc:
        raise IntegrationError(f"JSON 语法错误：{exc.msg}") from exc
    except RecursionError as exc:
        raise IntegrationError("JSON 嵌套超过解析器上限") from exc
    except ValueError as exc:
        raise IntegrationError("JSON 数值超出解析器边界") from exc
    _reject_invalid_unicode(parsed)
    return parsed


def canonical_json(value: Any) -> str:
    """Use the provenance lab's restricted canonical JSON domain."""

    try:
        return PROVENANCE.canonical_json(value)
    except (TypeError, ValueError, PROVENANCE.ContractError) as exc:
        raise IntegrationError(f"值不属于受限 canonical JSON 域：{exc}") from exc


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_text(value: str) -> str:
    try:
        return digest_bytes(value.encode("utf-8", errors="strict"))
    except UnicodeEncodeError as exc:
        raise IntegrationError("文本含非法 Unicode，不能计算 UTF-8 摘要") from exc


def digest_object(value: Any) -> str:
    return digest_text(canonical_json(value))


def _exact_fields(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IntegrationError(f"{label} 必须是对象")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise IntegrationError(f"{label} 字段不精确：missing={missing}, extra={extra}")
    return value


def _token(name: str, value: Any, maximum: int = 300) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise IntegrationError(f"{name} 必须是 1..{maximum} 字符的字符串")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise IntegrationError(f"{name} 不允许控制字符")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise IntegrationError(f"{name} 含非法 Unicode") from exc
    return value


def _positive_int(name: str, value: Any, *, maximum: int = 1_000_000) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value <= 0
        or value > maximum
    ):
        raise IntegrationError(f"{name} 必须是 1..{maximum} 的整数")
    return value


def _sorted_strings(name: str, value: Any, *, nonempty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise IntegrationError(f"{name} 必须是数组")
    result = tuple(_token(name, item) for item in value)
    if nonempty and not result:
        raise IntegrationError(f"{name} 不得为空")
    if result != tuple(sorted(set(result))):
        raise IntegrationError(f"{name} 必须排序且不得重复")
    return result


def _unique_strings(name: str, value: Any, *, nonempty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise IntegrationError(f"{name} 必须是数组")
    result = tuple(_token(name, item) for item in value)
    if nonempty and not result:
        raise IntegrationError(f"{name} 不得为空")
    if len(result) != len(set(result)):
        raise IntegrationError(f"{name} 不得重复")
    return result


def _relative_markdown_path(value: Any) -> str:
    text = _token("relative_path", value)
    if "\\" in text:
        raise IntegrationError("relative_path 必须使用 POSIX 分隔符")
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise IntegrationError("relative_path 不得绝对化或包含 traversal")
    if path.suffix.lower() != ".md":
        raise IntegrationError("集成 fixture 只接受 .md 来源")
    return path.as_posix()


def normalize_source_text(value: str) -> str:
    if not isinstance(value, str):
        raise IntegrationError("source content 必须是字符串")
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise IntegrationError("source content 含非法 Unicode") from exc
    if len(encoded) > MAX_SOURCE_BYTES:
        raise IntegrationError("source content 超过教学上限")
    if value.startswith("\ufeff"):
        raise IntegrationError("fixture 不接受 BOM；真实 connector 应显式登记解码")
    normalized = unicodedata.normalize(
        "NFC", value.replace("\r\n", "\n").replace("\r", "\n")
    )
    if not normalized.strip():
        raise IntegrationError("source content 不得为空")
    return normalized


def _module_sha256(path: Path) -> str:
    return digest_bytes(path.read_bytes())


@dataclass(frozen=True)
class AdapterContract:
    parser_schema_version: str
    knowledge_store_schema_version: str
    chunk_strategy_version: str
    index_revision: str
    authorization_revision: str
    max_units: int
    overlap_units: int

    def as_identity(self) -> dict[str, Any]:
        return {
            "adapter_revision": ADAPTER_REVISION,
            "authorization_revision": self.authorization_revision,
            "chunk_config": {
                "max_units": self.max_units,
                "overlap_units": self.overlap_units,
            },
            "chunk_strategy_version": self.chunk_strategy_version,
            "index_revision": self.index_revision,
            "knowledge_store_schema_version": self.knowledge_store_schema_version,
            "mapping_revision": MAPPING_REVISION,
            "parser_schema_version": self.parser_schema_version,
        }


@dataclass(frozen=True)
class RevisionInput:
    tenant_id: str
    document_id: str
    source_uri: str
    source_version: str
    source_sequence: int
    connector: str
    upstream_event_id: str
    run_id: str
    media_type: str
    relative_path: str
    root_section_path: tuple[str, ...]
    allowed_groups: tuple[str, ...]
    raw_content: str
    raw_size_bytes: int
    raw_sha256: str
    canonical_text: str
    canonical_text_sha256: str
    parser_config_sha256: str
    parser_record: dict[str, Any]
    parser_record_sha256: str


RevisionInputKey = tuple[
    str,
    str,
    int,
    str,
    str,
    str,
    tuple[str, ...],
    str,
]


def _revision_input_key(value: RevisionInput) -> RevisionInputKey:
    return (
        value.tenant_id,
        value.document_id,
        value.source_sequence,
        value.source_uri,
        value.source_version,
        value.canonical_text_sha256,
        value.allowed_groups,
        value.run_id,
    )


def _revision_row_input_key(row: dict[str, Any]) -> RevisionInputKey:
    return (
        row["tenant_id"],
        row["document_id"],
        row["source_sequence"],
        row["source_uri"],
        row["source_version"],
        row["content_hash"],
        tuple(row["allowed_groups"]),
        row["run_id"],
    )


@dataclass
class PublishedDocument:
    tenant_id: str
    document_id: str
    source_uri: str
    source_version: str
    raw_sha256: str
    parser_record_sha256: str
    parse_revision_sha256: str
    kb_revision_id: int
    kb_revision_number: int
    kb_revision_ref: str
    kb_snapshot_sha256: str
    control_binding_sha256: str
    allowed_groups: tuple[str, ...]
    source_id: str
    elements: tuple[Any, ...]
    element_context: dict[str, dict[str, Any]]
    crosswalk: tuple[dict[str, Any], ...]


@dataclass
class AdapterGeneration:
    generation_id: str
    capture_state_sha256: str
    capture_artifact_sha256: str
    pipeline_fingerprint: str
    authorization_revision: str
    entry_set_sha256: str
    manifest_sha256: str
    status: str
    documents: dict[tuple[str, str], PublishedDocument]
    chunks: tuple[Any, ...]
    chunk_documents: dict[str, tuple[str, str]]
    manifest: dict[str, Any]
    capture: dict[str, Any]


ROOT_FIELDS = {"schema_version", "contract", "documents", "queries"}
CONTRACT_FIELDS = {
    "adapter_revision",
    "mapping_revision",
    "parser_schema_version",
    "knowledge_store_schema_version",
    "chunk_strategy_version",
    "index_revision",
    "authorization_revision",
    "chunk_config",
}
DOCUMENT_FIELDS = {
    "tenant_id",
    "document_id",
    "source_sequence",
    "source_uri",
    "source_version",
    "connector",
    "upstream_event_id",
    "run_id",
    "media_type",
    "relative_path",
    "root_section_path",
    "allowed_groups",
    "content",
}
QUERY_FIELDS = {
    "query_id",
    "tenant_id",
    "subject_groups",
    "authorization_revision",
    "query",
    "top_k",
    "expected_claim_texts",
    "forbidden_document_ids",
}
RUNTIME_QUERY_FIELDS = {
    "query_id",
    "tenant_id",
    "subject_groups",
    "authorization_revision",
    "query",
    "top_k",
}


def validate_fixture(value: Any) -> dict[str, Any]:
    root = _exact_fields(value, ROOT_FIELDS, "fixture")
    if root["schema_version"] != FIXTURE_SCHEMA_VERSION:
        raise IntegrationError("fixture schema_version 不匹配")

    contract_value = _exact_fields(root["contract"], CONTRACT_FIELDS, "contract")
    if contract_value["adapter_revision"] != ADAPTER_REVISION:
        raise IntegrationError("adapter_revision 不匹配")
    if contract_value["mapping_revision"] != MAPPING_REVISION:
        raise IntegrationError("mapping_revision 不匹配")
    chunk_config = _exact_fields(
        contract_value["chunk_config"], {"max_units", "overlap_units"}, "chunk_config"
    )
    max_units = _positive_int("chunk_config.max_units", chunk_config["max_units"], maximum=4096)
    overlap = chunk_config["overlap_units"]
    if not isinstance(overlap, int) or isinstance(overlap, bool) or not 0 <= overlap < max_units:
        raise IntegrationError("chunk_config.overlap_units 必须满足 0 <= overlap < max")
    contract = AdapterContract(
        parser_schema_version=_token(
            "parser_schema_version", contract_value["parser_schema_version"]
        ),
        knowledge_store_schema_version=_token(
            "knowledge_store_schema_version",
            contract_value["knowledge_store_schema_version"],
        ),
        chunk_strategy_version=_token(
            "chunk_strategy_version", contract_value["chunk_strategy_version"]
        ),
        index_revision=_token("index_revision", contract_value["index_revision"]),
        authorization_revision=_token(
            "authorization_revision", contract_value["authorization_revision"]
        ),
        max_units=max_units,
        overlap_units=overlap,
    )
    if contract.parser_schema_version != PARSER.SCHEMA_VERSION:
        raise IntegrationError("fixture parser schema 与当前实现不兼容")
    if contract.knowledge_store_schema_version != KB.SCHEMA_VERSION:
        raise IntegrationError("fixture KB schema 与当前实现不兼容")
    if contract.index_revision != CHUNK.LEXICAL_INDEX_REVISION:
        raise IntegrationError("fixture index revision 与当前 Chunking 实现不兼容")

    documents_value = root["documents"]
    if not isinstance(documents_value, list) or not 1 <= len(documents_value) <= MAX_DOCUMENTS:
        raise IntegrationError("documents 数量超出教学范围")
    documents: list[dict[str, Any]] = []
    document_keys: set[tuple[str, str]] = set()
    relative_paths: set[str] = set()
    upstream_event_ids: set[str] = set()
    for index, raw in enumerate(documents_value):
        item = _exact_fields(raw, DOCUMENT_FIELDS, f"documents[{index}]")
        tenant = _token("tenant_id", item["tenant_id"])
        document_id = _token("document_id", item["document_id"])
        key = (tenant, document_id)
        if key in document_keys:
            raise IntegrationError(f"document identity 重复：{key}")
        document_keys.add(key)
        relative_path = _relative_markdown_path(item["relative_path"])
        if relative_path in relative_paths:
            raise IntegrationError(f"relative_path 重复：{relative_path}")
        relative_paths.add(relative_path)
        upstream_event_id = _token("upstream_event_id", item["upstream_event_id"])
        if upstream_event_id in upstream_event_ids:
            raise IntegrationError(f"upstream_event_id 重复：{upstream_event_id}")
        upstream_event_ids.add(upstream_event_id)
        media_type = _token("media_type", item["media_type"])
        if media_type != "text/markdown":
            raise IntegrationError("adapter v1 只接受 text/markdown")
        content = item["content"]
        normalize_source_text(content)
        documents.append(
            {
                "tenant_id": tenant,
                "document_id": document_id,
                "source_sequence": _positive_int(
                    "source_sequence", item["source_sequence"]
                ),
                "source_uri": _token("source_uri", item["source_uri"], maximum=1000),
                "source_version": _token("source_version", item["source_version"]),
                "connector": _token("connector", item["connector"]),
                "upstream_event_id": upstream_event_id,
                "run_id": _token("run_id", item["run_id"]),
                "media_type": media_type,
                "relative_path": relative_path,
                "root_section_path": list(
                    _unique_strings("root_section_path", item["root_section_path"])
                ),
                "allowed_groups": list(
                    _sorted_strings("allowed_groups", item["allowed_groups"])
                ),
                "content": content,
            }
        )

    queries_value = root["queries"]
    if not isinstance(queries_value, list) or not 1 <= len(queries_value) <= MAX_QUERIES:
        raise IntegrationError("queries 数量超出教学范围")
    queries: list[dict[str, Any]] = []
    query_ids: set[str] = set()
    for index, raw in enumerate(queries_value):
        item = _exact_fields(raw, QUERY_FIELDS, f"queries[{index}]")
        query_id = _token("query_id", item["query_id"])
        if query_id in query_ids:
            raise IntegrationError(f"query_id 重复：{query_id}")
        query_ids.add(query_id)
        expected = item["expected_claim_texts"]
        forbidden = item["forbidden_document_ids"]
        if not isinstance(expected, list) or not all(
            isinstance(text, str) and text for text in expected
        ):
            raise IntegrationError("expected_claim_texts 必须是非空字符串数组或空数组")
        if not isinstance(forbidden, list):
            raise IntegrationError("forbidden_document_ids 必须是数组")
        forbidden_values = [_token("forbidden_document_id", value) for value in forbidden]
        if forbidden_values != sorted(set(forbidden_values)):
            raise IntegrationError("forbidden_document_ids 必须排序且不得重复")
        queries.append(
            {
                "query_id": query_id,
                "tenant_id": _token("tenant_id", item["tenant_id"]),
                "subject_groups": list(
                    _sorted_strings("subject_groups", item["subject_groups"])
                ),
                "authorization_revision": _token(
                    "authorization_revision", item["authorization_revision"]
                ),
                "query": _token("query", item["query"], maximum=2000),
                "top_k": _positive_int("top_k", item["top_k"], maximum=20),
                "expected_claim_texts": list(expected),
                "forbidden_document_ids": forbidden_values,
            }
        )

    return {
        "schema_version": FIXTURE_SCHEMA_VERSION,
        "contract": contract.as_identity(),
        "documents": documents,
        "queries": queries,
    }


def load_fixture(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            raw_bytes = handle.read(MAX_FIXTURE_BYTES + 1)
        if len(raw_bytes) > MAX_FIXTURE_BYTES:
            raise IntegrationError(f"fixture 不得超过 {MAX_FIXTURE_BYTES} UTF-8 bytes")
        raw = raw_bytes.decode("utf-8", errors="strict")
    except IntegrationError:
        raise
    except (OSError, UnicodeError) as exc:
        raise IntegrationError(f"无法读取 fixture：{type(exc).__name__}") from exc
    parsed = validate_fixture(strict_json_loads(raw))
    parsed["fixture_sha256"] = digest_text(raw)
    parsed["fixture_model_sha256"] = fixture_model_sha256(parsed)
    return parsed


def fixture_model_sha256(fixture: dict[str, Any]) -> str:
    model = {
        key: copy.deepcopy(value)
        for key, value in fixture.items()
        if key not in {"fixture_sha256", "fixture_model_sha256"}
    }
    return digest_object(validate_fixture(model))


def require_fixture_integrity(fixture: dict[str, Any]) -> None:
    supplied = fixture.get("fixture_model_sha256")
    if not isinstance(supplied, str) or supplied != fixture_model_sha256(fixture):
        raise IntegrationError("fixture_model_sha256 与当前类型化模型不一致")


def _contract_from_fixture(fixture: dict[str, Any]) -> AdapterContract:
    value = fixture["contract"]
    return AdapterContract(
        parser_schema_version=value["parser_schema_version"],
        knowledge_store_schema_version=value["knowledge_store_schema_version"],
        chunk_strategy_version=value["chunk_strategy_version"],
        index_revision=value["index_revision"],
        authorization_revision=value["authorization_revision"],
        max_units=value["chunk_config"]["max_units"],
        overlap_units=value["chunk_config"]["overlap_units"],
    )


def _runtime_query(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "query_id": value["query_id"],
        "tenant_id": value["tenant_id"],
        "subject_groups": list(value["subject_groups"]),
        "authorization_revision": value["authorization_revision"],
        "query": value["query"],
        "top_k": value["top_k"],
    }


def validate_runtime_query(value: Any) -> dict[str, Any]:
    item = _exact_fields(value, RUNTIME_QUERY_FIELDS, "runtime query")
    return {
        "query_id": _token("query_id", item["query_id"]),
        "tenant_id": _token("tenant_id", item["tenant_id"]),
        "subject_groups": list(
            _sorted_strings("subject_groups", item["subject_groups"])
        ),
        "authorization_revision": _token(
            "authorization_revision", item["authorization_revision"]
        ),
        "query": _token("query", item["query"], maximum=2000),
        "top_k": _positive_int("top_k", item["top_k"], maximum=20),
    }


def _absolute_without_symlink_components(path: Path, *, label: str) -> Path:
    absolute = path.absolute()
    parts = absolute.parts
    if not parts:
        raise IntegrationError(f"{label} 不是绝对路径")
    current = Path(parts[0])
    for part in parts[1:]:
        current = current / part
        if current.is_symlink():
            raise IntegrationError(f"{label} 不得包含 symlink component")
    return absolute


def _safe_output_path(root: Path, relative_path: str) -> Path:
    # Check every materialized component before resolve(): resolving first
    # dereferences the final symlink and makes an in-root link invisible to a
    # later is_symlink() check.  This is a single-process teaching boundary,
    # not a race-free openat/O_NOFOLLOW replacement.
    root_absolute = _absolute_without_symlink_components(
        root, label="materialization root"
    )
    target_unresolved = root_absolute.joinpath(*PurePosixPath(relative_path).parts)
    current = root_absolute
    for part in PurePosixPath(relative_path).parts:
        current = current / part
        if current.is_symlink():
            raise IntegrationError("adapter v1 不跟随 source 或 parent symlink")

    root_resolved = root_absolute.resolve()
    target = target_unresolved.resolve()
    try:
        target.relative_to(root_resolved)
    except ValueError as exc:
        raise IntegrationError("source path 逃逸 materialization root") from exc
    return target


def _parser_element_identity(record: dict[str, Any], element: dict[str, Any]) -> str:
    identity = {
        "kind": element["kind"],
        "location": element["location"],
        "parse_revision_sha256": record["parse_revision_sha256"],
        "text_sha256": element["text_sha256"],
    }
    return "elm_" + digest_object(identity)


def _validate_parser_record(
    manifest: dict[str, Any], record: dict[str, Any], source: dict[str, Any]
) -> None:
    if record.get("status") != "parsed":
        raise IntegrationError(f"来源未成功解析：{source['relative_path']}")
    raw = source["content"].encode("utf-8")
    if record.get("raw_sha256") != digest_bytes(raw):
        raise IntegrationError("parser raw hash 与 fixture bytes 不一致")
    expected_parse = PARSER._parse_revision_sha256(
        record["raw_sha256"],
        parser=record["parser"],
        parser_version=record["parser_version"],
        config_sha256=manifest["config_sha256"],
    )
    if record.get("parse_revision_sha256") != expected_parse:
        raise IntegrationError("parse revision 无法从 raw/parser/config 重算")
    elements = record.get("elements")
    if not isinstance(elements, list) or not elements:
        raise IntegrationError("parser record 缺少 elements")
    seen: set[str] = set()
    for order, element in enumerate(elements, start=1):
        _exact_fields(
            element,
            {
                "element_id",
                "kind",
                "text",
                "text_sha256",
                "order",
                "location",
                "section_path",
                "attributes",
            },
            "parser element",
        )
        if element["order"] != order:
            raise IntegrationError("parser element order 不连续")
        if digest_text(element["text"]) != element["text_sha256"]:
            raise IntegrationError("parser element 正文哈希不一致")
        if _parser_element_identity(record, element) != element["element_id"]:
            raise IntegrationError("parser element identity 无法重算")
        if element["element_id"] in seen:
            raise IntegrationError("parser element ID 重复")
        seen.add(element["element_id"])
        location = _exact_fields(
            element["location"],
            {"coordinate_space", "line_start", "line_end"},
            "parser element location",
        )
        if location["coordinate_space"] != PARSER.LINE_COORDINATE_SPACE:
            raise IntegrationError("parser coordinate space 不受 adapter 支持")
        start = location["line_start"]
        end = location["line_end"]
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start <= 0
            or end < start
        ):
            raise IntegrationError("parser line span 非法")


def _source_id(tenant_id: str, document_id: str) -> str:
    return "xsrc_" + digest_object(
        {
            "document_id": document_id,
            "id_scheme": SOURCE_ID_SCHEME,
            "tenant_id": tenant_id,
        }
    )


def _adapter_element_id(
    tenant_id: str, document_id: str, kb_revision_ref: str, parser_element_id: str
) -> str:
    return "xel_" + digest_object(
        {
            "document_id": document_id,
            "id_scheme": ELEMENT_ID_SCHEME,
            "kb_revision_ref": kb_revision_ref,
            "parser_element_id": parser_element_id,
            "tenant_id": tenant_id,
        }
    )


class CrossLayerEngine:
    """Materialize sources, publish KB projections, adapt elements, and answer."""

    def __init__(
        self,
        fixture: dict[str, Any],
        source_root: Path,
        *,
        database_path: str = ":memory:",
    ) -> None:
        require_fixture_integrity(fixture)
        self.fixture = copy.deepcopy(fixture)
        self.contract = _contract_from_fixture(fixture)
        # Preserve and inspect the caller-supplied path before any resolve().
        # Resolving first would erase evidence that source_root itself points
        # through a symlink and could redirect materialization outside the
        # intended logical root.
        self.source_root = _absolute_without_symlink_components(
            source_root, label="source_root"
        )
        self.source_root.mkdir(parents=True, exist_ok=True)
        self.source_root = _absolute_without_symlink_components(
            self.source_root, label="source_root"
        )
        self.connection: sqlite3.Connection = KB.connect(database_path)
        self.active_authorization_revision = self.contract.authorization_revision
        self.source_specs: dict[tuple[str, str], dict[str, Any]] = {
            (item["tenant_id"], item["document_id"]): copy.deepcopy(item)
            for item in fixture["documents"]
        }
        self.revision_inputs: dict[RevisionInputKey, RevisionInput] = {}
        self.generations: dict[str, AdapterGeneration] = {}
        self.published_generation_id: str | None = None
        self.pipeline_fingerprint = digest_object(
            {
                "contract": self.contract.as_identity(),
                "modules": {
                    "adapter": _module_sha256(Path(__file__).resolve()),
                    "chunking": _module_sha256(CHUNK_PATH),
                    "knowledge_store": _module_sha256(KB_PATH),
                    "parser": _module_sha256(PARSER_PATH),
                    "provenance": _module_sha256(PROVENANCE_PATH),
                },
            }
        )
        self._materialize_all_sources()
        self._ingest_initial_sources()
        KB.drain_outbox(self.connection)
        KB.require_reconciled(self.connection)
        self.publish_capture(self.capture_published_state())

    def close(self) -> None:
        self.connection.close()

    def _materialize_all_sources(self) -> None:
        for source in self.source_specs.values():
            path = _safe_output_path(self.source_root, source["relative_path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(source["content"].encode("utf-8"))

    def _scan_manifest(self) -> dict[str, Any]:
        manifest = PARSER.scan_root(
            self.source_root,
            PARSER.Limits(
                max_files=MAX_DOCUMENTS,
                max_file_bytes=MAX_SOURCE_BYTES,
                max_total_bytes=MAX_DOCUMENTS * MAX_SOURCE_BYTES,
            ),
        )
        if manifest["schema_version"] != self.contract.parser_schema_version:
            raise IntegrationError("parser manifest schema 漂移")
        if manifest["summary"]["gate"] != "pass":
            raise IntegrationError(f"parser gate 未通过：{manifest['summary']['gate']}")
        return manifest

    def _capture_revision_input(
        self,
        manifest: dict[str, Any],
        source: dict[str, Any],
    ) -> RevisionInput:
        source_path = _safe_output_path(self.source_root, source["relative_path"])
        if source_path.is_symlink():
            raise IntegrationError("adapter v1 不跟随 source symlink")
        raw_bytes = source_path.read_bytes()
        expected_bytes = source["content"].encode("utf-8")
        if raw_bytes != expected_bytes:
            raise IntegrationError("materialized source 已变化，必须 fresh scan")
        record = next(
            (
                item
                for item in manifest["documents"]
                if item["relative_path"] == source["relative_path"]
            ),
            None,
        )
        if record is None:
            raise IntegrationError(f"parser manifest 缺少来源：{source['relative_path']}")
        _validate_parser_record(manifest, record, source)
        canonical = normalize_source_text(source["content"])
        revision_input = RevisionInput(
            tenant_id=source["tenant_id"],
            document_id=source["document_id"],
            source_uri=source["source_uri"],
            source_version=source["source_version"],
            source_sequence=source["source_sequence"],
            connector=source["connector"],
            upstream_event_id=source["upstream_event_id"],
            run_id=source["run_id"],
            media_type=source["media_type"],
            relative_path=source["relative_path"],
            root_section_path=tuple(source["root_section_path"]),
            allowed_groups=tuple(source["allowed_groups"]),
            raw_content=source["content"],
            raw_size_bytes=len(raw_bytes),
            raw_sha256=record["raw_sha256"],
            canonical_text=canonical,
            canonical_text_sha256=digest_text(canonical),
            parser_config_sha256=manifest["config_sha256"],
            parser_record=copy.deepcopy(record),
            parser_record_sha256=digest_object(record),
        )
        return revision_input

    def _remember_revision_input(self, value: RevisionInput) -> RevisionInputKey:
        key = _revision_input_key(value)
        existing = self.revision_inputs.get(key)
        if existing is not None and canonical_json(asdict(existing)) != canonical_json(
            asdict(value)
        ):
            raise IntegrationError("同一 KB revision binding 对应不同 protected source sidecar")
        self.revision_inputs.setdefault(key, value)
        return key

    def _upsert_revision_input(self, value: RevisionInput, *, run_id: str) -> Any:
        return KB.upsert_record(
            self.connection,
            KB.SourceRecord(
                tenant_id=value.tenant_id,
                document_id=value.document_id,
                source_sequence=value.source_sequence,
                source_uri=value.source_uri,
                source_version=value.source_version,
                content=value.canonical_text,
                allowed_groups=value.allowed_groups,
            ),
            KB.BuildConfig(
                pipeline_version=f"{ADAPTER_REVISION}:{self.pipeline_fingerprint}"
            ),
            run_id=run_id,
        )

    def _ingest_initial_sources(self) -> None:
        manifest = self._scan_manifest()
        for source in self.source_specs.values():
            value = self._capture_revision_input(manifest, source)
            result = self._upsert_revision_input(value, run_id=value.run_id)
            if result.action not in {"inserted", "noop"}:
                raise IntegrationError(f"初始 ingest 行为异常：{result.action}")
            self._remember_revision_input(value)

    def _document_states(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT tenant_id, document_id, last_source_sequence,
                   current_event_version, current_revision_id,
                   published_revision_id, deleted, access_blocked
            FROM documents ORDER BY tenant_id, document_id
            """
        ).fetchall()
        return [
            {
                "tenant_id": str(row["tenant_id"]),
                "document_id": str(row["document_id"]),
                "last_source_sequence": int(row["last_source_sequence"]),
                "current_event_version": int(row["current_event_version"]),
                "current_revision_id": row["current_revision_id"],
                "published_revision_id": row["published_revision_id"],
                "deleted": bool(row["deleted"]),
                "access_blocked": bool(row["access_blocked"]),
            }
            for row in rows
        ]

    def _tombstones(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT tenant_id, document_id, event_version, source_sequence,
                   reason_code, run_id
            FROM tombstones ORDER BY tenant_id, document_id, event_version
            """
        ).fetchall()
        return [
            {
                "tenant_id": str(row["tenant_id"]),
                "document_id": str(row["document_id"]),
                "event_version": int(row["event_version"]),
                "source_sequence": int(row["source_sequence"]),
                "reason_code": str(row["reason_code"]),
                "run_id": str(row["run_id"]),
            }
            for row in rows
        ]

    def _published_rows(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT r.revision_id, r.tenant_id, r.document_id,
                   r.revision_number, r.source_sequence, r.source_uri,
                   r.source_version, r.pipeline_version, r.content,
                   r.content_hash, r.source_state_hash,
                   r.build_state_hash, r.run_id
            FROM documents AS d
            JOIN revisions AS r ON r.revision_id = d.published_revision_id
            WHERE d.deleted = 0 AND d.published_revision_id IS NOT NULL
            ORDER BY r.tenant_id, r.document_id
            """
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            groups = tuple(
                item["group_id"]
                for item in self.connection.execute(
                    "SELECT group_id FROM revision_acl WHERE revision_id = ? ORDER BY group_id",
                    (row["revision_id"],),
                ).fetchall()
            )
            content = str(row["content"])
            if digest_text(content) != row["content_hash"]:
                raise IntegrationError("published canonical content hash 不一致")
            expected_hashes = KB._state_hashes(
                KB.SourceRecord(
                    tenant_id=str(row["tenant_id"]),
                    document_id=str(row["document_id"]),
                    source_sequence=int(row["source_sequence"]),
                    source_uri=str(row["source_uri"]),
                    source_version=str(row["source_version"]),
                    content=content,
                    allowed_groups=groups,
                ),
                KB.BuildConfig(pipeline_version=str(row["pipeline_version"])),
            )
            if tuple(
                str(row[name])
                for name in ("content_hash", "source_state_hash", "build_state_hash")
            ) != expected_hashes:
                raise IntegrationError("published KB source/build hash 无法重算")
            result.append(
                {
                    "revision_id": int(row["revision_id"]),
                    "tenant_id": str(row["tenant_id"]),
                    "document_id": str(row["document_id"]),
                    "revision_number": int(row["revision_number"]),
                    "source_sequence": int(row["source_sequence"]),
                    "source_uri": str(row["source_uri"]),
                    "source_version": str(row["source_version"]),
                    "pipeline_version": str(row["pipeline_version"]),
                    "content": content,
                    "content_hash": str(row["content_hash"]),
                    "source_state_hash": str(row["source_state_hash"]),
                    "build_state_hash": str(row["build_state_hash"]),
                    "run_id": str(row["run_id"]),
                    "allowed_groups": list(groups),
                }
            )
        return result

    def _outbox_rows(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT event_id, tenant_id, document_id, event_version,
                   event_kind, revision_id, processed, attempts, last_error
            FROM outbox ORDER BY tenant_id, document_id, event_version
            """
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            event_kind = str(row["event_kind"])
            expected_id = KB._event_id(
                str(row["tenant_id"]),
                str(row["document_id"]),
                int(row["event_version"]),
                event_kind,
            )
            if str(row["event_id"]) != expected_id:
                raise IntegrationError("capture outbox event ID 无法重算")
            result.append(
                {
                    "event_id": str(row["event_id"]),
                    "tenant_id": str(row["tenant_id"]),
                    "document_id": str(row["document_id"]),
                    "event_version": int(row["event_version"]),
                    "event_kind": event_kind,
                    "revision_id": row["revision_id"],
                    "processed": bool(row["processed"]),
                    "attempts": int(row["attempts"]),
                    "last_error": row["last_error"],
                }
            )
        return result

    def capture_published_state(self) -> dict[str, Any]:
        report = KB.reconcile(self.connection)
        documents = self._published_rows()
        states = self._document_states()
        tombstones = self._tombstones()
        outbox = self._outbox_rows()
        body = {
            "authorization_revision": self.active_authorization_revision,
            "document_states": states,
            "documents": documents,
            "outbox": outbox,
            "pipeline_fingerprint": self.pipeline_fingerprint,
            "tombstones": tombstones,
        }
        return {
            "schema_version": CAPTURE_SCHEMA_VERSION,
            **body,
            "reconcile_sha256": digest_object(report),
            "state_sha256": digest_object(body),
        }

    def _validate_capture(self, capture: Any) -> dict[str, Any]:
        value = _exact_fields(
            capture,
            {
                "schema_version",
                "authorization_revision",
                "document_states",
                "documents",
                "outbox",
                "pipeline_fingerprint",
                "tombstones",
                "reconcile_sha256",
                "state_sha256",
            },
            "capture",
        )
        if value["schema_version"] != CAPTURE_SCHEMA_VERSION:
            raise IntegrationError("capture schema_version 不匹配")
        body = {
            "authorization_revision": value["authorization_revision"],
            "document_states": value["document_states"],
            "documents": value["documents"],
            "outbox": value["outbox"],
            "pipeline_fingerprint": value["pipeline_fingerprint"],
            "tombstones": value["tombstones"],
        }
        if digest_object(body) != value["state_sha256"]:
            raise IntegrationError("capture state_sha256 不一致")
        if value["pipeline_fingerprint"] != self.pipeline_fingerprint:
            raise IntegrationError("capture pipeline fingerprint 过期")
        if value["authorization_revision"] != self.active_authorization_revision:
            raise IntegrationError("capture authorization revision 过期")
        return value

    def _revision_input_for_row(self, row: dict[str, Any]) -> RevisionInput:
        key = _revision_row_input_key(row)
        value = self.revision_inputs.get(key)
        if value is None:
            raise IntegrationError(f"published revision 缺少 parser/source 输入映射：{key}")
        if value.canonical_text != row["content"]:
            raise IntegrationError("published revision 与 adapter canonical snapshot 不一致")
        return value

    def _published_document(self, row: dict[str, Any]) -> PublishedDocument:
        revision_input = self._revision_input_for_row(row)
        # Publication is a trust-boundary transition.  Recompute the immutable
        # raw/canonical/parser evidence (including a fresh parser run) before
        # this sidecar can contribute to a new published pointer; query-time
        # validation alone would allow forged evidence to be published first.
        self._validate_revision_input(revision_input)
        record = revision_input.parser_record
        groups = tuple(row["allowed_groups"])
        control_projection = {
            "allowed_groups": groups,
            "document_id": row["document_id"],
            "run_id": row["run_id"],
            "source_sequence": row["source_sequence"],
            "source_uri": row["source_uri"],
            "source_version": row["source_version"],
            "tenant_id": row["tenant_id"],
        }
        expected_control_projection = {
            "allowed_groups": revision_input.allowed_groups,
            "document_id": revision_input.document_id,
            "run_id": revision_input.run_id,
            "source_sequence": revision_input.source_sequence,
            "source_uri": revision_input.source_uri,
            "source_version": revision_input.source_version,
            "tenant_id": revision_input.tenant_id,
        }
        if control_projection != expected_control_projection:
            raise IntegrationError("KB revision 与 trusted control binding 不一致")
        kb_identity = {
            "allowed_groups": list(groups),
            "canonical_text_sha256": row["content_hash"],
            "document_id": row["document_id"],
            "id_scheme": KB_REVISION_SCHEME,
            "parse_revision_sha256": record["parse_revision_sha256"],
            "pipeline_version": row["pipeline_version"],
            "source_state_hash": row["source_state_hash"],
            "build_state_hash": row["build_state_hash"],
            "run_id": row["run_id"],
            "revision_number": row["revision_number"],
            "source_uri": row["source_uri"],
            "source_version": row["source_version"],
            "tenant_id": row["tenant_id"],
        }
        kb_revision_ref = "kbr_" + digest_object(kb_identity)
        control_binding = {
            "allowed_groups": list(revision_input.allowed_groups),
            "connector": revision_input.connector,
            "document_id": revision_input.document_id,
            "media_type": revision_input.media_type,
            "raw_sha256": revision_input.raw_sha256,
            "relative_path": revision_input.relative_path,
            "root_section_path": list(revision_input.root_section_path),
            "run_id": revision_input.run_id,
            "source_sequence": revision_input.source_sequence,
            "source_uri": revision_input.source_uri,
            "source_version": revision_input.source_version,
            "tenant_id": revision_input.tenant_id,
            "upstream_event_id": revision_input.upstream_event_id,
        }
        control_binding_sha256 = digest_object(control_binding)
        source_id = _source_id(row["tenant_id"], row["document_id"])
        elements: list[Any] = []
        contexts: dict[str, dict[str, Any]] = {}
        crosswalk: list[dict[str, Any]] = []
        for native in record["elements"]:
            native_id = {
                "scheme": "document-inspector/element/v2",
                "value": native["element_id"],
            }
            coordinate_mapping = {
                "mapping_status": "unavailable",
                "reason_code": "parser_projection_is_not_one_exact_canonical_span",
            }
            if native["kind"] == "heading":
                crosswalk.append(
                    {
                        "adapter_element_id": None,
                        "native_element_id": native_id,
                        "native_location": copy.deepcopy(native["location"]),
                        "projection_relation": "context_only",
                        "canonical_char_mapping": coordinate_mapping,
                    }
                )
                continue
            if native["kind"] not in CHUNK.ALLOWED_KINDS:
                raise IntegrationError(
                    f"parser kind 尚无显式 Chunking 投影：{native['kind']}"
                )
            section_path = tuple(native["section_path"]) or revision_input.root_section_path
            if not section_path:
                raise IntegrationError("body element 缺少 trusted root_section_path")
            adapter_id = _adapter_element_id(
                row["tenant_id"],
                row["document_id"],
                kb_revision_ref,
                native["element_id"],
            )
            element = CHUNK.Element(
                element_id=adapter_id,
                source_id=source_id,
                source_revision=kb_revision_ref,
                kind=native["kind"],
                text=native["text"],
                section_path=section_path,
                acl=groups,
                line_start=native["location"]["line_start"],
                line_end=native["location"]["line_end"],
            )
            elements.append(element)
            contexts[adapter_id] = {
                "native": copy.deepcopy(native),
                "revision_input": revision_input,
            }
            crosswalk.append(
                {
                    "adapter_element_id": {
                        "scheme": ELEMENT_ID_SCHEME,
                        "value": adapter_id,
                    },
                    "native_element_id": native_id,
                    "native_location": copy.deepcopy(native["location"]),
                    "projection_relation": "projected_as_body",
                    "canonical_char_mapping": coordinate_mapping,
                }
            )
        if not elements:
            raise IntegrationError("published document 没有可供 Chunking 的元素")
        snapshot = {
            "kb_identity": kb_identity,
            "kb_revision_ref": kb_revision_ref,
            "kb_revision_scheme": KB_REVISION_SCHEME,
            "normalizer_revision": NORMALIZER_REVISION,
            "parser_record_sha256": revision_input.parser_record_sha256,
            "parser_config_sha256": revision_input.parser_config_sha256,
            "raw_sha256": revision_input.raw_sha256,
            "raw_size_bytes": revision_input.raw_size_bytes,
            "source_id": {"scheme": SOURCE_ID_SCHEME, "value": source_id},
            "crosswalk_sha256": digest_object(crosswalk),
            "control_binding_sha256": control_binding_sha256,
        }
        return PublishedDocument(
            tenant_id=row["tenant_id"],
            document_id=row["document_id"],
            source_uri=row["source_uri"],
            source_version=row["source_version"],
            raw_sha256=revision_input.raw_sha256,
            parser_record_sha256=revision_input.parser_record_sha256,
            parse_revision_sha256=record["parse_revision_sha256"],
            kb_revision_id=row["revision_id"],
            kb_revision_number=row["revision_number"],
            kb_revision_ref=kb_revision_ref,
            kb_snapshot_sha256=digest_object(snapshot),
            control_binding_sha256=control_binding_sha256,
            allowed_groups=groups,
            source_id=source_id,
            elements=tuple(elements),
            element_context=contexts,
            crosswalk=tuple(crosswalk),
        )

    def publish_capture(self, capture: dict[str, Any]) -> AdapterGeneration:
        value = self._validate_capture(copy.deepcopy(capture))
        KB.require_reconciled(self.connection)
        current = self.capture_published_state()
        if canonical_json(current) != canonical_json(value):
            raise IntegrationError("stale capture 不得发布")

        documents: dict[tuple[str, str], PublishedDocument] = {}
        all_elements: list[Any] = []
        for row in value["documents"]:
            document = self._published_document(row)
            key = (document.tenant_id, document.document_id)
            documents[key] = document
            all_elements.extend(document.elements)

        config = CHUNK.ChunkConfig(
            max_units=self.contract.max_units,
            overlap_units=self.contract.overlap_units,
            strategy_version=self.contract.chunk_strategy_version,
        )
        chunks = tuple(CHUNK.structured_chunks(all_elements, config))
        CHUNK.validate_chunks(chunks, all_elements, config)
        chunk_documents: dict[str, tuple[str, str]] = {}
        source_to_document = {
            document.source_id: key for key, document in documents.items()
        }
        entry_rows: list[dict[str, Any]] = []
        for chunk in chunks:
            key = source_to_document.get(chunk.source_id)
            if key is None:
                raise IntegrationError("chunk source_id 无法映射 published document")
            chunk_documents[chunk.chunk_id] = key
            entry_rows.append(
                {
                    "chunk_id": {
                        "scheme": CHUNK_ID_SCHEME,
                        "value": chunk.chunk_id,
                    },
                    "document_key": list(key),
                    "index_entry_id": {
                        "scheme": INDEX_ID_SCHEME,
                        "value": CHUNK.index_entry_id(
                            chunk, index_revision=self.contract.index_revision
                        ),
                    },
                    "retrieval_sha256": chunk.retrieval_sha256,
                }
            )
        entry_rows.sort(key=lambda item: item["index_entry_id"]["value"])
        entry_set_sha = digest_object(entry_rows)
        generation_identity = {
            "authorization_revision": value["authorization_revision"],
            "capture_artifact_sha256": digest_object(value),
            "capture_state_sha256": value["state_sha256"],
            "evidence_level": EVIDENCE_LEVEL,
            "external_chunk_to_citation_verified": False,
            "entry_set_sha256": entry_set_sha,
            "generation_id_scheme": GENERATION_ID_SCHEME,
            "pipeline_fingerprint": self.pipeline_fingerprint,
            "publication_mode": "offline-single-process-no-concurrent-readers",
        }
        generation_id = "xgen_" + digest_object(generation_identity)
        manifest = {
            **generation_identity,
            "generation_id": generation_id,
            "documents": [
                {
                    "document_id": document.document_id,
                    "crosswalk_sha256": digest_object(document.crosswalk),
                    "control_binding_sha256": document.control_binding_sha256,
                    "kb_revision_ref": document.kb_revision_ref,
                    "kb_revision_locator": {
                        "scheme": KB_LOCATOR_SCHEME,
                        "value": document.kb_revision_id,
                    },
                    "kb_snapshot_sha256": document.kb_snapshot_sha256,
                    "parse_revision_sha256": document.parse_revision_sha256,
                    "parser_record_sha256": document.parser_record_sha256,
                    "raw_sha256": document.raw_sha256,
                    "source_id": {
                        "scheme": SOURCE_ID_SCHEME,
                        "value": document.source_id,
                    },
                    "tenant_id": document.tenant_id,
                }
                for _key, document in sorted(documents.items())
            ],
        }
        previous_id = self.published_generation_id
        if previous_id is not None and previous_id != generation_id:
            self.generations[previous_id].status = "superseded"
        generation = AdapterGeneration(
            generation_id=generation_id,
            capture_state_sha256=value["state_sha256"],
            capture_artifact_sha256=digest_object(value),
            pipeline_fingerprint=self.pipeline_fingerprint,
            authorization_revision=value["authorization_revision"],
            entry_set_sha256=entry_set_sha,
            manifest_sha256=digest_object(manifest),
            status="published",
            documents=documents,
            chunks=chunks,
            chunk_documents=chunk_documents,
            manifest=copy.deepcopy(manifest),
            capture=copy.deepcopy(value),
        )
        self.generations[generation_id] = generation
        self.published_generation_id = generation_id
        return generation

    @staticmethod
    def _document_projection(document: PublishedDocument) -> dict[str, Any]:
        revision_input = next(
            iter(document.element_context.values())
        )["revision_input"]
        return {
            "allowed_groups": list(document.allowed_groups),
            "canonical_text_sha256": revision_input.canonical_text_sha256,
            "crosswalk": copy.deepcopy(list(document.crosswalk)),
            "control_binding_sha256": document.control_binding_sha256,
            "document_id": document.document_id,
            "elements": [asdict(element) for element in document.elements],
            "kb_revision_id": document.kb_revision_id,
            "kb_revision_number": document.kb_revision_number,
            "kb_revision_ref": document.kb_revision_ref,
            "kb_snapshot_sha256": document.kb_snapshot_sha256,
            "parse_revision_sha256": document.parse_revision_sha256,
            "parser_record_sha256": document.parser_record_sha256,
            "raw_sha256": document.raw_sha256,
            "source_id": document.source_id,
            "source_uri": document.source_uri,
            "source_version": document.source_version,
            "tenant_id": document.tenant_id,
        }

    def _validate_revision_input(self, value: RevisionInput) -> None:
        if value.media_type != "text/markdown":
            raise IntegrationError("revision input media type 漂移")
        raw_bytes = value.raw_content.encode("utf-8")
        if len(raw_bytes) != value.raw_size_bytes:
            raise IntegrationError("revision input raw size 漂移")
        if digest_bytes(raw_bytes) != value.raw_sha256:
            raise IntegrationError("revision input raw hash 漂移")
        canonical = normalize_source_text(value.raw_content)
        if canonical != value.canonical_text:
            raise IntegrationError("revision input canonical text 漂移")
        if digest_text(canonical) != value.canonical_text_sha256:
            raise IntegrationError("revision input canonical hash 漂移")
        if digest_object(value.parser_record) != value.parser_record_sha256:
            raise IntegrationError("revision input parser record hash 漂移")
        _validate_parser_record(
            {"config_sha256": value.parser_config_sha256},
            value.parser_record,
            {"relative_path": value.relative_path, "content": value.raw_content},
        )
        with tempfile.TemporaryDirectory(prefix="cross-layer-reparse-") as temporary:
            rebuild_root = Path(temporary).resolve()
            rebuild_path = _safe_output_path(rebuild_root, value.relative_path)
            rebuild_path.parent.mkdir(parents=True, exist_ok=True)
            rebuild_path.write_bytes(raw_bytes)
            fresh_manifest = PARSER.scan_root(
                rebuild_root,
                PARSER.Limits(
                    max_files=MAX_DOCUMENTS,
                    max_file_bytes=MAX_SOURCE_BYTES,
                    max_total_bytes=MAX_DOCUMENTS * MAX_SOURCE_BYTES,
                ),
            )
            if fresh_manifest["config_sha256"] != value.parser_config_sha256:
                raise IntegrationError("revision input parser config 无法 fresh rebuild")
            fresh_record = next(
                (
                    item
                    for item in fresh_manifest["documents"]
                    if item["relative_path"] == value.relative_path
                ),
                None,
            )
            if fresh_record is None or canonical_json(fresh_record) != canonical_json(
                value.parser_record
            ):
                raise IntegrationError("revision input parser record 无法 fresh rebuild")

    def _revision_row(self, revision_id: int) -> dict[str, Any]:
        row = self.connection.execute(
            """
            SELECT revision_id, tenant_id, document_id, revision_number,
                   source_sequence, source_uri, source_version,
                   pipeline_version, content, content_hash,
                   source_state_hash, build_state_hash, run_id
            FROM revisions WHERE revision_id = ?
            """,
            (revision_id,),
        ).fetchone()
        if row is None:
            raise IntegrationError(f"KB revision 已消失：{revision_id}")
        groups = [
            str(item["group_id"])
            for item in self.connection.execute(
                "SELECT group_id FROM revision_acl WHERE revision_id = ? ORDER BY group_id",
                (revision_id,),
            ).fetchall()
        ]
        content = str(row["content"])
        if digest_text(content) != row["content_hash"]:
            raise IntegrationError("KB revision content hash 无法重算")
        record = KB.SourceRecord(
            tenant_id=str(row["tenant_id"]),
            document_id=str(row["document_id"]),
            source_sequence=int(row["source_sequence"]),
            source_uri=str(row["source_uri"]),
            source_version=str(row["source_version"]),
            content=content,
            allowed_groups=tuple(groups),
        )
        expected_hashes = KB._state_hashes(
            record, KB.BuildConfig(pipeline_version=str(row["pipeline_version"]))
        )
        if tuple(
            str(row[name])
            for name in ("content_hash", "source_state_hash", "build_state_hash")
        ) != expected_hashes:
            raise IntegrationError("KB source/build state hash 无法重算")
        events = self.connection.execute(
            """
            SELECT event_id, tenant_id, document_id, event_version, event_kind
            FROM outbox WHERE revision_id = ? ORDER BY event_version
            """,
            (revision_id,),
        ).fetchall()
        if len(events) != 1:
            raise IntegrationError("KB revision 必须精确绑定一个 outbox event")
        event = events[0]
        if (
            str(event["tenant_id"]) != str(row["tenant_id"])
            or str(event["document_id"]) != str(row["document_id"])
            or str(event["event_kind"]) != "document.upserted"
            or str(event["event_id"])
            != KB._event_id(
                str(row["tenant_id"]),
                str(row["document_id"]),
                int(event["event_version"]),
                str(event["event_kind"]),
            )
        ):
            raise IntegrationError("KB outbox event identity 无法重算")
        return {
            "revision_id": int(row["revision_id"]),
            "tenant_id": str(row["tenant_id"]),
            "document_id": str(row["document_id"]),
            "revision_number": int(row["revision_number"]),
            "source_sequence": int(row["source_sequence"]),
            "source_uri": str(row["source_uri"]),
            "source_version": str(row["source_version"]),
            "pipeline_version": str(row["pipeline_version"]),
            "content": content,
            "content_hash": str(row["content_hash"]),
            "source_state_hash": str(row["source_state_hash"]),
            "build_state_hash": str(row["build_state_hash"]),
            "run_id": str(row["run_id"]),
            "allowed_groups": groups,
        }

    def _entry_rows(self, generation: AdapterGeneration) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for chunk in generation.chunks:
            key = generation.chunk_documents.get(chunk.chunk_id)
            if key is None:
                raise IntegrationError("generation chunk 缺少 document crosswalk")
            rows.append(
                {
                    "chunk_id": {
                        "scheme": CHUNK_ID_SCHEME,
                        "value": chunk.chunk_id,
                    },
                    "document_key": list(key),
                    "index_entry_id": {
                        "scheme": INDEX_ID_SCHEME,
                        "value": CHUNK.index_entry_id(
                            chunk, index_revision=self.contract.index_revision
                        ),
                    },
                    "retrieval_sha256": chunk.retrieval_sha256,
                }
            )
        rows.sort(key=lambda item: item["index_entry_id"]["value"])
        return rows

    def _expected_generation_manifest(
        self, generation: AdapterGeneration
    ) -> dict[str, Any]:
        identity = {
            "authorization_revision": generation.authorization_revision,
            "capture_artifact_sha256": generation.capture_artifact_sha256,
            "capture_state_sha256": generation.capture_state_sha256,
            "evidence_level": EVIDENCE_LEVEL,
            "external_chunk_to_citation_verified": False,
            "entry_set_sha256": generation.entry_set_sha256,
            "generation_id_scheme": GENERATION_ID_SCHEME,
            "pipeline_fingerprint": generation.pipeline_fingerprint,
            "publication_mode": "offline-single-process-no-concurrent-readers",
        }
        return {
            **identity,
            "generation_id": generation.generation_id,
            "documents": [
                {
                    "document_id": document.document_id,
                    "crosswalk_sha256": digest_object(document.crosswalk),
                    "control_binding_sha256": document.control_binding_sha256,
                    "kb_revision_ref": document.kb_revision_ref,
                    "kb_revision_locator": {
                        "scheme": KB_LOCATOR_SCHEME,
                        "value": document.kb_revision_id,
                    },
                    "kb_snapshot_sha256": document.kb_snapshot_sha256,
                    "parse_revision_sha256": document.parse_revision_sha256,
                    "parser_record_sha256": document.parser_record_sha256,
                    "raw_sha256": document.raw_sha256,
                    "source_id": {
                        "scheme": SOURCE_ID_SCHEME,
                        "value": document.source_id,
                    },
                    "tenant_id": document.tenant_id,
                }
                for _key, document in sorted(generation.documents.items())
            ],
        }

    def _validate_generation(self, generation: AdapterGeneration) -> None:
        if generation.status != "published":
            raise IntegrationError("只能查询 published generation")
        if generation.generation_id != self.published_generation_id:
            raise IntegrationError("generation 不再是 published pointer")
        if generation.pipeline_fingerprint != self.pipeline_fingerprint:
            raise IntegrationError("generation pipeline fingerprint 漂移")
        if generation.authorization_revision != self.active_authorization_revision:
            raise IntegrationError("generation authorization revision 漂移")
        validated_capture = self._validate_capture(copy.deepcopy(generation.capture))
        if validated_capture["state_sha256"] != generation.capture_state_sha256:
            raise IntegrationError("generation 与 capture state 绑定漂移")
        if digest_object(validated_capture) != generation.capture_artifact_sha256:
            raise IntegrationError("generation capture artifact hash 漂移")
        capture_revision_refs = sorted(
            (
                row["tenant_id"],
                row["document_id"],
                row["revision_id"],
            )
            for row in validated_capture["documents"]
        )
        generation_revision_refs = sorted(
            (key[0], key[1], document.kb_revision_id)
            for key, document in generation.documents.items()
        )
        if capture_revision_refs != generation_revision_refs:
            raise IntegrationError("generation documents 与 capture published rows 不一致")

        fresh_documents: dict[tuple[str, str], PublishedDocument] = {}
        all_elements: list[Any] = []
        for key, document in sorted(generation.documents.items()):
            contexts = list(document.element_context.values())
            if not contexts:
                raise IntegrationError("published document 缺少 protected element context")
            revision_inputs = {id(item["revision_input"]): item["revision_input"] for item in contexts}
            if len(revision_inputs) != 1:
                raise IntegrationError("document elements 未绑定同一 immutable revision input")
            self._validate_revision_input(next(iter(revision_inputs.values())))
            row = self._revision_row(document.kb_revision_id)
            if (row["tenant_id"], row["document_id"]) != key:
                raise IntegrationError("KB numeric revision 与 logical document 交叉替换")
            fresh = self._published_document(row)
            if canonical_json(self._document_projection(fresh)) != canonical_json(
                self._document_projection(document)
            ):
                raise IntegrationError("published document artifact 无法 fresh rebuild")
            fresh_documents[key] = fresh
            all_elements.extend(fresh.elements)

        config = CHUNK.ChunkConfig(
            max_units=self.contract.max_units,
            overlap_units=self.contract.overlap_units,
            strategy_version=self.contract.chunk_strategy_version,
        )
        fresh_chunks = tuple(CHUNK.structured_chunks(all_elements, config))
        CHUNK.validate_chunks(fresh_chunks, all_elements, config)
        if canonical_json([asdict(item) for item in fresh_chunks]) != canonical_json(
            [asdict(item) for item in generation.chunks]
        ):
            raise IntegrationError("generation chunks 无法 fresh rebuild")
        fresh_source_map = {
            document.source_id: key for key, document in fresh_documents.items()
        }
        expected_crosswalk = {
            chunk.chunk_id: fresh_source_map[chunk.source_id] for chunk in fresh_chunks
        }
        if expected_crosswalk != generation.chunk_documents:
            raise IntegrationError("chunk-to-document crosswalk 漂移")
        entry_set_sha = digest_object(self._entry_rows(generation))
        if entry_set_sha != generation.entry_set_sha256:
            raise IntegrationError("generation entry set hash 漂移")
        identity = {
            "authorization_revision": generation.authorization_revision,
            "capture_artifact_sha256": generation.capture_artifact_sha256,
            "capture_state_sha256": generation.capture_state_sha256,
            "evidence_level": EVIDENCE_LEVEL,
            "external_chunk_to_citation_verified": False,
            "entry_set_sha256": generation.entry_set_sha256,
            "generation_id_scheme": GENERATION_ID_SCHEME,
            "pipeline_fingerprint": generation.pipeline_fingerprint,
            "publication_mode": "offline-single-process-no-concurrent-readers",
        }
        if "xgen_" + digest_object(identity) != generation.generation_id:
            raise IntegrationError("generation identity 无法重算")
        expected_manifest = self._expected_generation_manifest(generation)
        if canonical_json(expected_manifest) != canonical_json(generation.manifest):
            raise IntegrationError("generation manifest 漂移")
        if digest_object(expected_manifest) != generation.manifest_sha256:
            raise IntegrationError("generation manifest hash 漂移")

    @staticmethod
    def _revision_input_from_document(document: PublishedDocument) -> RevisionInput:
        contexts = list(document.element_context.values())
        if not contexts:
            raise IntegrationError("external export document 缺少 protected context")
        values = {
            id(item["revision_input"]): item["revision_input"] for item in contexts
        }
        if len(values) != 1:
            raise IntegrationError(
                "external export document 未绑定单一 immutable revision input"
            )
        return next(iter(values.values()))

    def _external_document(
        self,
        document: PublishedDocument,
        generation: AdapterGeneration,
    ) -> dict[str, Any]:
        revision_input = self._revision_input_from_document(document)
        row = self._revision_row(document.kb_revision_id)
        if (row["tenant_id"], row["document_id"]) != (
            document.tenant_id,
            document.document_id,
        ):
            raise IntegrationError("external export KB revision route 交叉绑定")

        access_body = {
            "allowed_groups": list(document.allowed_groups),
            "authorization_revision": generation.authorization_revision,
        }
        access_snapshot = {
            **access_body,
            "sha256": digest_object(access_body),
        }
        source_event = {
            "connector": revision_input.connector,
            "media_type": revision_input.media_type,
            "relative_path": revision_input.relative_path,
            "root_section_path": list(revision_input.root_section_path),
            "run_id": revision_input.run_id,
            "sequence": revision_input.source_sequence,
            "source_uri": revision_input.source_uri,
            "source_version": revision_input.source_version,
            "upstream_event_id": revision_input.upstream_event_id,
        }
        control_binding = {
            "allowed_groups": list(revision_input.allowed_groups),
            "connector": revision_input.connector,
            "document_id": revision_input.document_id,
            "media_type": revision_input.media_type,
            "raw_sha256": revision_input.raw_sha256,
            "relative_path": revision_input.relative_path,
            "root_section_path": list(revision_input.root_section_path),
            "run_id": revision_input.run_id,
            "source_sequence": revision_input.source_sequence,
            "source_uri": revision_input.source_uri,
            "source_version": revision_input.source_version,
            "tenant_id": revision_input.tenant_id,
            "upstream_event_id": revision_input.upstream_event_id,
        }
        if digest_object(control_binding) != document.control_binding_sha256:
            raise IntegrationError("external export control binding 无法复算")

        crosswalk: list[dict[str, Any]] = []
        for item in document.crosswalk:
            mapping = item["canonical_char_mapping"]
            if mapping != {
                "mapping_status": "unavailable",
                "reason_code": "parser_projection_is_not_one_exact_canonical_span",
            }:
                raise IntegrationError("external export 不得升级 canonical mapping")
            crosswalk.append(
                {
                    "adapter_element_id": copy.deepcopy(
                        item["adapter_element_id"]
                    ),
                    "canonical_mapping": {
                        "mapping_revision": MAPPING_REVISION,
                        "reason_code": mapping["reason_code"],
                        "status": "unavailable",
                    },
                    "native_element_id": copy.deepcopy(item["native_element_id"]),
                    "native_location": copy.deepcopy(item["native_location"]),
                    "projection_relation": item["projection_relation"],
                }
            )
        crosswalk_sha256 = digest_object(crosswalk)

        adapter_elements = [
            {
                "access_snapshot_sha256": access_snapshot["sha256"],
                "allowed_groups": list(element.acl),
                "element_id": {
                    "scheme": ELEMENT_ID_SCHEME,
                    "value": element.element_id,
                },
                "kind": element.kind,
                "logical_source_id": {
                    "scheme": SOURCE_ID_SCHEME,
                    "value": element.source_id,
                },
                "native_location": {
                    "coordinate_space": PARSER.LINE_COORDINATE_SPACE,
                    "line_end": element.line_end,
                    "line_start": element.line_start,
                },
                "section_path": list(element.section_path),
                "source_revision_ref": {
                    "scheme": KB_REVISION_SCHEME,
                    "value": element.source_revision,
                },
                "text": element.text,
                "text_sha256": digest_text(element.text),
            }
            for element in document.elements
        ]

        kb_identity = {
            "allowed_groups": list(document.allowed_groups),
            "build_state_hash": row["build_state_hash"],
            "canonical_text_sha256": row["content_hash"],
            "document_id": document.document_id,
            "id_scheme": KB_REVISION_SCHEME,
            "parse_revision_sha256": document.parse_revision_sha256,
            "pipeline_version": row["pipeline_version"],
            "revision_number": row["revision_number"],
            "run_id": row["run_id"],
            "source_state_hash": row["source_state_hash"],
            "source_uri": row["source_uri"],
            "source_version": row["source_version"],
            "tenant_id": document.tenant_id,
        }
        if "kbr_" + digest_object(kb_identity) != document.kb_revision_ref:
            raise IntegrationError("external export KB revision ref 无法复算")
        external_snapshot_body = {
            "control_binding_sha256": document.control_binding_sha256,
            "crosswalk_sha256": crosswalk_sha256,
            "identity_inputs": kb_identity,
            "logical_source_id": {
                "scheme": SOURCE_ID_SCHEME,
                "value": document.source_id,
            },
            "normalizer_revision": NORMALIZER_REVISION,
            "parser_config_sha256": revision_input.parser_config_sha256,
            "parser_record_sha256": revision_input.parser_record_sha256,
            "raw_sha256": revision_input.raw_sha256,
            "raw_size_bytes": revision_input.raw_size_bytes,
            "revision_ref": {
                "scheme": KB_REVISION_SCHEME,
                "value": document.kb_revision_ref,
            },
        }
        return {
            "access_snapshot": access_snapshot,
            "adapter_elements": adapter_elements,
            "canonical_representation": {
                "mode": "inline_text",
                "normalizer_revision": NORMALIZER_REVISION,
                "sha256": revision_input.canonical_text_sha256,
                "text": revision_input.canonical_text,
            },
            "crosswalk": crosswalk,
            "crosswalk_sha256": crosswalk_sha256,
            "document_id": document.document_id,
            "knowledge_revision": {
                "external_snapshot_sha256": digest_object(external_snapshot_body),
                "identity_inputs": kb_identity,
                "producer_snapshot_sha256": document.kb_snapshot_sha256,
                "ref": {
                    "scheme": KB_REVISION_SCHEME,
                    "value": document.kb_revision_ref,
                },
                "revision_number": document.kb_revision_number,
            },
            "logical_source_id": {
                "scheme": SOURCE_ID_SCHEME,
                "value": document.source_id,
            },
            "parser_artifact": {
                "config_sha256": revision_input.parser_config_sha256,
                "name": revision_input.parser_record["parser"],
                "parse_revision_id": {
                    "scheme": PARSER_REVISION_SCHEME,
                    "value": document.parse_revision_sha256,
                },
                "record": copy.deepcopy(revision_input.parser_record),
                "record_sha256": revision_input.parser_record_sha256,
                "schema_version": self.contract.parser_schema_version,
                "version": revision_input.parser_record["parser_version"],
            },
            "raw_representation": {
                "encoding": "utf-8",
                "mode": "inline_utf8",
                "sha256": revision_input.raw_sha256,
                "size_bytes": revision_input.raw_size_bytes,
                "text": revision_input.raw_content,
            },
            "source_event": source_event,
            "tenant_id": document.tenant_id,
        }

    def export_external_provenance_bundle(self) -> dict[str, Any]:
        """Export a complete protected v2 bundle after a fresh local rebuild.

        The embedded hash establishes deterministic self-consistency only.  A
        consumer must pin the digest through an independently trusted policy
        before the producer's bytes can cross a trust boundary.
        """

        generation = self._published_generation()
        documents = [
            self._external_document(document, generation)
            for _key, document in sorted(generation.documents.items())
        ]
        document_by_source = {
            item["logical_source_id"]["value"]: item for item in documents
        }
        chunks: list[dict[str, Any]] = []
        index_entries: list[dict[str, Any]] = []
        for chunk in generation.chunks:
            document = document_by_source.get(chunk.source_id)
            if document is None:
                raise IntegrationError("external export chunk source 悬空")
            item = {
                "access_snapshot_sha256": document["access_snapshot"]["sha256"],
                "allowed_groups": list(chunk.acl),
                "chunk_id": {
                    "scheme": CHUNK_ID_SCHEME,
                    "value": chunk.chunk_id,
                },
                "content_sha256": chunk.content_sha256,
                "element_spans": [
                    {
                        "element_id": {
                            "scheme": ELEMENT_ID_SCHEME,
                            "value": span.element_id,
                        },
                        "unit_end": span.unit_end,
                        "unit_start": span.unit_start,
                    }
                    for span in chunk.element_spans
                ],
                "family": chunk.family,
                "logical_source_id": {
                    "scheme": SOURCE_ID_SCHEME,
                    "value": chunk.source_id,
                },
                "ordinal": chunk.ordinal,
                "overlap_units": chunk.overlap_units,
                "retrieval_sha256": chunk.retrieval_sha256,
                "retrieval_text": chunk.retrieval_text,
                "retrieval_unit_count": chunk.retrieval_unit_count,
                "section_path": list(chunk.section_path),
                "source_revision_ref": {
                    "scheme": KB_REVISION_SCHEME,
                    "value": chunk.source_revision,
                },
                "strategy_version": chunk.strategy_version,
                "text": chunk.text,
                "unit_count": chunk.unit_count,
            }
            chunks.append(item)
            index_entries.append(
                {
                    "access_snapshot_sha256": item["access_snapshot_sha256"],
                    "chunk_id": copy.deepcopy(item["chunk_id"]),
                    "document_id": document["document_id"],
                    "index_entry_id": {
                        "scheme": INDEX_ID_SCHEME,
                        "value": CHUNK.index_entry_id(
                            chunk, index_revision=self.contract.index_revision
                        ),
                    },
                    "index_revision": self.contract.index_revision,
                    "logical_source_id": copy.deepcopy(item["logical_source_id"]),
                    "retrieval_sha256": chunk.retrieval_sha256,
                    "source_revision_ref": copy.deepcopy(
                        item["source_revision_ref"]
                    ),
                    "tenant_id": document["tenant_id"],
                }
            )
        index_entries.sort(key=lambda item: item["index_entry_id"]["value"])

        parser_contracts = {
            (
                item["parser_artifact"]["name"],
                item["parser_artifact"]["version"],
                item["parser_artifact"]["config_sha256"],
            )
            for item in documents
        }
        if len(parser_contracts) != 1:
            raise IntegrationError("external export 要求单一 parser contract")
        parser_name, parser_version, parser_config_sha256 = next(
            iter(parser_contracts)
        )
        producer_contract = {
            "adapter_revision": ADAPTER_REVISION,
            "chunk_config": {
                "max_units": self.contract.max_units,
                "overlap_units": self.contract.overlap_units,
            },
            "chunk_strategy_version": self.contract.chunk_strategy_version,
            "coordinate_schemes": {
                "canonical_mapping": "external-provenance/canonical-mapping/v2",
                "lexical": LEXICAL_COORDINATE_SPACE,
                "native_location": PARSER.LINE_COORDINATE_SPACE,
            },
            "identity_schemes": {
                "chunk": CHUNK_ID_SCHEME,
                "generation": GENERATION_ID_SCHEME,
                "index_entry": INDEX_ID_SCHEME,
                "knowledge_revision": KB_REVISION_SCHEME,
                "logical_source": SOURCE_ID_SCHEME,
                "namespaced_element": ELEMENT_ID_SCHEME,
                "parser_element": PARSER_ELEMENT_SCHEME,
                "parser_revision": PARSER_REVISION_SCHEME,
            },
            "index_revision": self.contract.index_revision,
            "knowledge_state_revision": KNOWLEDGE_STATE_REVISION,
            "knowledge_store_schema_version": (
                self.contract.knowledge_store_schema_version
            ),
            "lexical_unit_revision": "chunking-lab/regex-lexical-unit/v1",
            "mapping_revision": MAPPING_REVISION,
            "normalizer_revision": NORMALIZER_REVISION,
            "parser": {
                "config_sha256": parser_config_sha256,
                "name": parser_name,
                "schema_version": self.contract.parser_schema_version,
                "version": parser_version,
            },
            "pipeline_fingerprint": generation.pipeline_fingerprint,
        }
        source_manifest = [
            {
                "canonical_representation": {
                    key: item["canonical_representation"][key]
                    for key in ("mode", "normalizer_revision", "sha256")
                },
                "logical_source_id": copy.deepcopy(item["logical_source_id"]),
                "raw_representation": {
                    key: item["raw_representation"][key]
                    for key in ("encoding", "mode", "sha256", "size_bytes")
                },
                "source_event": copy.deepcopy(item["source_event"]),
            }
            for item in documents
        ]
        document_refs = [
            {
                "logical_source_id": copy.deepcopy(item["logical_source_id"]),
                "source_revision_ref": copy.deepcopy(
                    item["knowledge_revision"]["ref"]
                ),
            }
            for item in documents
        ]
        entry_refs = [
            copy.deepcopy(item["index_entry_id"]) for item in index_entries
        ]
        payload = {
            "authorization_contract": {
                "acl_enforcement": "tenant-and-acl-before-score",
                "authorization_revision": generation.authorization_revision,
                "consumer_live_authorization_check": "required-before-publish-and-query",
                "subject_membership_evidence": "not-in-bundle-host-resolved",
            },
            "canonicalization_revision": EXTERNAL_CANONICALIZATION_REVISION,
            "chunks": chunks,
            "documents": documents,
            "index_entries": index_entries,
            "producer_contract": producer_contract,
            "release": {
                "authorization_revision": generation.authorization_revision,
                "capture_artifact_sha256": generation.capture_artifact_sha256,
                "capture_state_sha256": generation.capture_state_sha256,
                "document_refs": document_refs,
                "entry_refs": entry_refs,
                "entry_set_sha256": digest_object(index_entries),
                "evidence_level": EVIDENCE_LEVEL,
                "generation_id": {
                    "scheme": GENERATION_ID_SCHEME,
                    "value": generation.generation_id,
                },
                "pipeline_fingerprint": generation.pipeline_fingerprint,
                "producer_entry_set_sha256": generation.entry_set_sha256,
                "producer_release_manifest_reference": {
                    "sha256": generation.manifest_sha256,
                    "verification": "opaque-producer-reference-only",
                },
                "publication_mode": "producer-published-consumer-must-stage",
                "source_manifest_sha256": digest_object(source_manifest),
                "tombstone_state_sha256": digest_object(
                    generation.capture["tombstones"]
                ),
            },
            "schema_version": EXTERNAL_BUNDLE_SCHEMA_VERSION,
        }
        return {
            **payload,
            "integrity": {
                "attestation": {
                    "mode": "none",
                    "trust_scope": "self-consistency-only",
                },
                "canonicalization_revision": EXTERNAL_CANONICALIZATION_REVISION,
                "payload_sha256": digest_object(payload),
                "producer_validation": "fresh-local-rebuild-before-export",
            },
        }

    def _published_generation(self) -> AdapterGeneration:
        if self.published_generation_id is None:
            raise IntegrationError("没有 published generation")
        generation = self.generations.get(self.published_generation_id)
        if generation is None:
            raise IntegrationError("published generation pointer 悬空")
        self._validate_generation(generation)
        return generation

    def _document_live(self, document: PublishedDocument) -> bool:
        row = self.connection.execute(
            """
            SELECT published_revision_id, deleted, access_blocked
            FROM documents WHERE tenant_id = ? AND document_id = ?
            """,
            (document.tenant_id, document.document_id),
        ).fetchone()
        if row is None:
            return False
        if bool(row["deleted"]) or bool(row["access_blocked"]):
            return False
        if row["published_revision_id"] != document.kb_revision_id:
            return False

        search = self.connection.execute(
            """
            SELECT content, content_hash FROM search_revisions
            WHERE revision_id = ? AND tenant_id = ? AND document_id = ?
            """,
            (document.kb_revision_id, document.tenant_id, document.document_id),
        ).fetchone()
        if search is None:
            raise IntegrationError("live KB pointer 缺少 search projection")
        content = str(search["content"])
        if digest_text(content) != search["content_hash"]:
            raise IntegrationError("live search content hash 漂移")
        revision_input = next(iter(document.element_context.values()))["revision_input"]
        if content != revision_input.canonical_text:
            raise IntegrationError("live search projection 与 release revision 不一致")
        search_groups = tuple(
            str(item["group_id"])
            for item in self.connection.execute(
                "SELECT group_id FROM search_acl WHERE revision_id = ? ORDER BY group_id",
                (document.kb_revision_id,),
            ).fetchall()
        )
        if search_groups != document.allowed_groups:
            raise IntegrationError("live search ACL 与 release snapshot 不一致")
        return True

    def _eligible_chunks(
        self, query: dict[str, Any], generation: AdapterGeneration
    ) -> tuple[list[Any], dict[str, int]]:
        tenant_chunks: list[Any] = []
        live_chunks: list[Any] = []
        acl_chunks: list[Any] = []
        groups = set(query["subject_groups"])
        for chunk in generation.chunks:
            key = generation.chunk_documents[chunk.chunk_id]
            document = generation.documents[key]
            if document.tenant_id != query["tenant_id"]:
                continue
            tenant_chunks.append(chunk)
            if not self._document_live(document):
                continue
            live_chunks.append(chunk)
            if groups.intersection(document.allowed_groups):
                acl_chunks.append(chunk)
        summary = {
            "all_chunks": len(generation.chunks),
            "tenant_chunks": len(tenant_chunks),
            "live_chunks": len(live_chunks),
            "acl_chunks": len(acl_chunks),
            "selected_chunks": 0,
        }
        return acl_chunks, summary

    def _citation_for_span(
        self, document: PublishedDocument, chunk: Any, span: Any
    ) -> tuple[str, dict[str, Any]]:
        element = next(
            (item for item in document.elements if item.element_id == span.element_id),
            None,
        )
        if element is None:
            raise IntegrationError("citation span 指向未知 adapter element")
        context = document.element_context.get(span.element_id)
        if context is None:
            raise IntegrationError("citation span 缺少 protected crosswalk")
        units = CHUNK.lexical_units(element.text)
        if not 0 <= span.unit_start < span.unit_end <= len(units):
            raise IntegrationError("citation lexical span 越界")
        char_start = units[span.unit_start].char_start
        char_end = units[span.unit_end - 1].char_end
        exact = element.text[char_start:char_end]
        if not exact:
            raise IntegrationError("citation exact quote 不得为空")
        native = context["native"]
        body = {
            "adapter_element_id": {
                "scheme": ELEMENT_ID_SCHEME,
                "value": element.element_id,
            },
            "canonical_char_mapping": {
                "mapping_status": "unavailable",
                "reason_code": "parser_projection_is_not_one_exact_canonical_span",
            },
            "chunk_id": {"scheme": CHUNK_ID_SCHEME, "value": chunk.chunk_id},
            "document_id": document.document_id,
            "exact": exact,
            "exact_sha256": digest_text(exact),
            "index_entry_id": {
                "scheme": INDEX_ID_SCHEME,
                "value": CHUNK.index_entry_id(
                    chunk, index_revision=self.contract.index_revision
                ),
            },
            "kb_revision_ref": {
                "scheme": KB_REVISION_SCHEME,
                "value": document.kb_revision_ref,
            },
            "lexical_coordinate": {
                "coordinate_space": "element-lexical-unit-0-based-half-open-v1",
                "unit_start": span.unit_start,
                "unit_end": span.unit_end,
            },
            "native_location": copy.deepcopy(native["location"]),
            "parser_element_id": {
                "scheme": "document-inspector/element/v2",
                "value": native["element_id"],
            },
            "parser_record_sha256": document.parser_record_sha256,
            "parse_revision_sha256": document.parse_revision_sha256,
            "prefix": element.text[max(0, char_start - 24):char_start],
            "raw_sha256": document.raw_sha256,
            "source_uri": document.source_uri,
            "source_version": document.source_version,
            "suffix": element.text[char_end:char_end + 24],
        }
        return exact, {"citation_id": "xcit_" + digest_object(body), **body}

    def _derive(
        self, query_value: dict[str, Any], *, observed_failure: str | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        query = validate_runtime_query(copy.deepcopy(query_value))
        if observed_failure not in {None, "retrieval_unavailable"}:
            raise IntegrationError("未知 failure injection")
        generation = self._published_generation()
        query_binding = digest_object(query)
        eligible: list[Any] = []
        filter_summary = {
            "all_chunks": len(generation.chunks),
            "tenant_chunks": 0,
            "live_chunks": 0,
            "acl_chunks": 0,
            "selected_chunks": 0,
        }
        failure: dict[str, Any] | None = None
        selected: list[Any] = []
        if query["authorization_revision"] == generation.authorization_revision:
            eligible, filter_summary = self._eligible_chunks(query, generation)
        if observed_failure == "retrieval_unavailable":
            status = "dependency_unavailable"
            failure = {"code": observed_failure, "retryable": True}
            claims: list[dict[str, Any]] = []
        else:
            selected = CHUNK.retrieve(
                query["query"],
                eligible,
                subject_groups=query["subject_groups"],
                k=query["top_k"],
                index_revision=self.contract.index_revision,
            )
            filter_summary["selected_chunks"] = len(selected)
            claims = []
            seen_spans: set[tuple[str, int, int]] = set()
            for ranked in selected:
                key = generation.chunk_documents[ranked.chunk.chunk_id]
                document = generation.documents[key]
                for span in ranked.chunk.element_spans:
                    span_key = (span.element_id, span.unit_start, span.unit_end)
                    if span_key in seen_spans:
                        continue
                    seen_spans.add(span_key)
                    text, citation = self._citation_for_span(
                        document, ranked.chunk, span
                    )
                    claim_body = {
                        "citations": [citation],
                        "text": text,
                    }
                    claims.append(
                        {
                            "claim_id": "xclm_"
                            + digest_object(
                                {"query_id": query["query_id"], **claim_body}
                            ),
                            **claim_body,
                        }
                    )
            status = "answered" if claims else "insufficient_evidence"
        trace_body = {
            "claims": claims,
            "query_id": query["query_id"],
            "status": status,
        }
        trace_id = "xtr_" + digest_object(trace_body)
        public = {
            "schema_version": PUBLIC_SCHEMA_VERSION,
            "query_id": query["query_id"],
            "status": status,
            "claims": claims,
            "trace_id": trace_id,
        }
        audit = {
            "schema_version": AUDIT_SCHEMA_VERSION,
            "visibility": "protected",
            "trace_id": trace_id,
            "authorization_revision": generation.authorization_revision,
            "index_generation_id": generation.generation_id,
            "selected_entry_ids": [item.index_entry_id for item in selected],
            "filter_summary": filter_summary,
            "query_binding_sha256": query_binding,
            "failure": failure,
        }
        return public, audit

    def query(
        self, query_value: dict[str, Any], *, observed_failure: str | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return self._derive(query_value, observed_failure=observed_failure)  # 统一由可信派生函数生成公共与受保护两种投影。

    def validate_evidence(
        self,
        query_value: dict[str, Any],
        public: Any,
        audit: Any,
        *,
        observed_failure: str | None = None,
    ) -> list[str]:
        errors: list[str] = []
        try:
            validate_public_projection(public)
        except IntegrationError as exc:
            errors.append(f"public_shape:{exc}")
        try:
            validate_audit_projection(audit)
        except IntegrationError as exc:
            errors.append(f"audit_shape:{exc}")
        if errors:
            return errors
        try:
            expected_public, expected_audit = self._derive(
                query_value, observed_failure=observed_failure
            )
        except (IntegrationError, CHUNK.ChunkingError, KB.StoreError) as exc:
            return [f"trusted_recompute_failed:{exc}"]
        if canonical_json(public) != canonical_json(expected_public):
            errors.append("public_projection_mismatch")
        if canonical_json(audit) != canonical_json(expected_audit):
            errors.append("protected_audit_mismatch")
        return errors

    def stage_update(
        self,
        *,
        tenant_id: str,
        document_id: str,
        source_sequence: int,
        source_version: str,
        content: str,
        allowed_groups: Sequence[str],
        upstream_event_id: str | None = None,
        run_id: str | None = None,
    ) -> Any:
        key = (_token("tenant_id", tenant_id), _token("document_id", document_id))
        current = self.source_specs.get(key)
        if current is None:
            raise IntegrationError("stage_update 只更新 fixture 已声明的 logical document")
        groups = _sorted_strings("allowed_groups", list(allowed_groups))
        next_source = copy.deepcopy(current)
        next_source.update(
            {
                "source_sequence": _positive_int("source_sequence", source_sequence),
                "source_version": _token("source_version", source_version),
                "content": content,
                "allowed_groups": list(groups),
                "upstream_event_id": _token(
                    "upstream_event_id",
                    upstream_event_id or f"event-{tenant_id}-{document_id}-{source_sequence}",
                ),
                "run_id": _token(
                    "run_id", run_id or f"run-{tenant_id}-{document_id}-{source_sequence}"
                ),
            }
        )
        normalize_source_text(content)
        candidate_raw_sha256 = digest_bytes(content.encode("utf-8"))
        for previous in self.revision_inputs.values():
            if previous.upstream_event_id != next_source["upstream_event_id"]:
                continue
            if (
                previous.tenant_id,
                previous.document_id,
                previous.source_sequence,
                previous.source_version,
                previous.raw_sha256,
            ) != (
                next_source["tenant_id"],
                next_source["document_id"],
                next_source["source_sequence"],
                next_source["source_version"],
                candidate_raw_sha256,
            ):
                raise IntegrationError("upstream_event_id 不能绑定不同 source event")
        path = _safe_output_path(self.source_root, next_source["relative_path"])
        previous_bytes = path.read_bytes()
        revision_key: RevisionInputKey | None = None
        previous_revision_input: RevisionInput | None = None
        try:
            path.write_bytes(content.encode("utf-8"))
            manifest = self._scan_manifest()
            revision_input = self._capture_revision_input(manifest, next_source)
            revision_key = _revision_input_key(revision_input)
            previous_revision_input = self.revision_inputs.get(revision_key)
            self._remember_revision_input(revision_input)
            result = self._upsert_revision_input(
                revision_input, run_id=next_source["run_id"]
            )
            if result.action in {"stale_ignored", "noop", "checkpoint_advanced"}:
                if previous_revision_input is None:
                    self.revision_inputs.pop(revision_key, None)
                else:
                    self.revision_inputs[revision_key] = previous_revision_input
            if result.action in {"stale_ignored", "noop"}:
                path.write_bytes(previous_bytes)
                return result
            self.source_specs[key] = next_source
            return result
        except BaseException:
            path.write_bytes(previous_bytes)
            if revision_key is not None:
                if previous_revision_input is None:
                    self.revision_inputs.pop(revision_key, None)
                else:
                    self.revision_inputs[revision_key] = previous_revision_input
            raise

    def delete_document(
        self,
        *,
        tenant_id: str,
        document_id: str,
        source_sequence: int,
        reason_code: str = "source_deleted",
        run_id: str = "adapter-delete",
    ) -> Any:
        return KB.delete_document(
            self.connection,
            tenant_id,
            document_id,
            source_sequence,
            reason_code=reason_code,
            run_id=run_id,
        )

    def _preflight_current_state(self) -> None:
        rows = self.connection.execute(
            """
            SELECT tenant_id, document_id, current_revision_id, deleted
            FROM documents ORDER BY tenant_id, document_id
            """
        ).fetchall()
        documents: list[PublishedDocument] = []
        for state in rows:
            if bool(state["deleted"]):
                continue
            revision_id = state["current_revision_id"]
            if revision_id is None:
                raise IntegrationError("live document 缺少 current revision")
            row = self._revision_row(int(revision_id))
            if (
                row["tenant_id"] != str(state["tenant_id"])
                or row["document_id"] != str(state["document_id"])
            ):
                raise IntegrationError("current revision pointer 交叉绑定")
            document = self._published_document(row)
            contexts = list(document.element_context.values())
            if not contexts:
                raise IntegrationError("preflight document 缺少 protected context")
            revision_input = contexts[0]["revision_input"]
            self._validate_revision_input(revision_input)
            documents.append(document)
        elements = [element for document in documents for element in document.elements]
        config = CHUNK.ChunkConfig(
            max_units=self.contract.max_units,
            overlap_units=self.contract.overlap_units,
            strategy_version=self.contract.chunk_strategy_version,
        )
        chunks = CHUNK.structured_chunks(elements, config)
        CHUNK.validate_chunks(chunks, elements, config)
        for chunk in chunks:
            CHUNK.index_entry_id(chunk, index_revision=self.contract.index_revision)

    def project_and_publish(self) -> AdapterGeneration:
        # 先以当前 revision 重新构建；内容构建失败时，旧 published pointer 仍可服务。
        # ACL 变化和删除已由原生 live state 拒绝，不能等到 adapter 发布后再补救。
        self._preflight_current_state()  # 验证解析、切分、索引身份和当前状态能在不切换指针前完成。
        KB.drain_outbox(self.connection)  # 先消费待处理事件，避免用滞后数据库状态发布。
        KB.require_reconciled(self.connection)  # 要求 source/KB 对账完成，否则 fail closed。
        return self.publish_capture(self.capture_published_state())  # 捕获已验证快照并原子生成新的 adapter generation。


def _sha256(name: str, value: Any) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise IntegrationError(f"{name} 必须是完整小写 SHA-256")
    return value


def _id_object(value: Any, *, scheme: str, label: str) -> dict[str, str]:
    item = _exact_fields(value, {"scheme", "value"}, label)
    if item["scheme"] != scheme:
        raise IntegrationError(f"{label} id scheme 不匹配")
    return {"scheme": scheme, "value": _token(f"{label}.value", item["value"])}


CITATION_FIELDS = {
    "citation_id",
    "adapter_element_id",
    "canonical_char_mapping",
    "chunk_id",
    "document_id",
    "exact",
    "exact_sha256",
    "index_entry_id",
    "kb_revision_ref",
    "lexical_coordinate",
    "native_location",
    "parser_element_id",
    "parser_record_sha256",
    "parse_revision_sha256",
    "prefix",
    "raw_sha256",
    "source_uri",
    "source_version",
    "suffix",
}


def validate_public_projection(value: Any) -> dict[str, Any]:
    public = _exact_fields(
        value,
        {"schema_version", "query_id", "status", "claims", "trace_id"},
        "public projection",
    )
    if public["schema_version"] != PUBLIC_SCHEMA_VERSION:
        raise IntegrationError("public schema_version 不匹配")
    _token("public.query_id", public["query_id"])
    if public["status"] not in {
        "answered",
        "insufficient_evidence",
        "dependency_unavailable",
    }:
        raise IntegrationError("public status 非法")
    _token("public.trace_id", public["trace_id"])
    claims = public["claims"]
    if not isinstance(claims, list):
        raise IntegrationError("public claims 必须是数组")
    claim_ids: set[str] = set()
    for claim_index, claim_value in enumerate(claims):
        claim = _exact_fields(
            claim_value, {"claim_id", "text", "citations"}, f"claim[{claim_index}]"
        )
        claim_id = _token("claim_id", claim["claim_id"])
        if claim_id in claim_ids:
            raise IntegrationError("claim_id 重复")
        claim_ids.add(claim_id)
        text = _token("claim.text", claim["text"], maximum=MAX_SOURCE_BYTES)
        citations = claim["citations"]
        if not isinstance(citations, list) or len(citations) != 1:
            raise IntegrationError("教学 adapter 每个 claim 必须有且仅有一个 citation")
        citation = _exact_fields(citations[0], CITATION_FIELDS, "citation")
        _token("citation_id", citation["citation_id"])
        _id_object(
            citation["adapter_element_id"], scheme=ELEMENT_ID_SCHEME, label="element"
        )
        _id_object(citation["chunk_id"], scheme=CHUNK_ID_SCHEME, label="chunk")
        _id_object(
            citation["index_entry_id"], scheme=INDEX_ID_SCHEME, label="index entry"
        )
        _id_object(
            citation["kb_revision_ref"], scheme=KB_REVISION_SCHEME, label="KB revision"
        )
        _id_object(
            citation["parser_element_id"],
            scheme="document-inspector/element/v2",
            label="parser element",
        )
        mapping = _exact_fields(
            citation["canonical_char_mapping"],
            {"mapping_status", "reason_code"},
            "canonical char mapping",
        )
        if mapping != {
            "mapping_status": "unavailable",
            "reason_code": "parser_projection_is_not_one_exact_canonical_span",
        }:
            raise IntegrationError("adapter v1 不得声称未经验证的 canonical char span")
        lexical = _exact_fields(
            citation["lexical_coordinate"],
            {"coordinate_space", "unit_start", "unit_end"},
            "lexical coordinate",
        )
        if lexical["coordinate_space"] != "element-lexical-unit-0-based-half-open-v1":
            raise IntegrationError("lexical coordinate space 不匹配")
        start = lexical["unit_start"]
        end = lexical["unit_end"]
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 0
            or end <= start
        ):
            raise IntegrationError("lexical coordinate 越界")
        native = _exact_fields(
            citation["native_location"],
            {"coordinate_space", "line_start", "line_end"},
            "native location",
        )
        if native["coordinate_space"] != PARSER.LINE_COORDINATE_SPACE:
            raise IntegrationError("native coordinate space 不匹配")
        if (
            not isinstance(native["line_start"], int)
            or isinstance(native["line_start"], bool)
            or not isinstance(native["line_end"], int)
            or isinstance(native["line_end"], bool)
            or native["line_start"] <= 0
            or native["line_end"] < native["line_start"]
        ):
            raise IntegrationError("native line coordinate 非法")
        exact = _token("citation.exact", citation["exact"], maximum=MAX_SOURCE_BYTES)
        if exact != text:
            raise IntegrationError("claim text 与 exact quote 不一致")
        if digest_text(exact) != citation["exact_sha256"]:
            raise IntegrationError("exact quote hash 不一致")
        for name in {
            "exact_sha256",
            "parser_record_sha256",
            "parse_revision_sha256",
            "raw_sha256",
        }:
            _sha256(name, citation[name])
        for name in {"document_id", "source_uri", "source_version"}:
            _token(name, citation[name], maximum=1000)
        for name in {"prefix", "suffix"}:
            if not isinstance(citation[name], str) or len(citation[name]) > 24:
                raise IntegrationError(f"{name} 必须是不超过 24 字符的字符串")
        claim_body = {"citations": citations, "text": text}
        expected_claim_id = "xclm_" + digest_object(
            {"query_id": public["query_id"], **claim_body}
        )
        if claim_id != expected_claim_id:
            raise IntegrationError("claim_id 无法重算")
        citation_body = {
            key: copy.deepcopy(item)
            for key, item in citation.items()
            if key != "citation_id"
        }
        if citation["citation_id"] != "xcit_" + digest_object(citation_body):
            raise IntegrationError("citation_id 无法重算")
    if public["status"] == "answered" and not claims:
        raise IntegrationError("answered 必须含 claims")
    if public["status"] != "answered" and claims:
        raise IntegrationError("非 answered 状态不得含 claims")
    expected_trace = "xtr_" + digest_object(
        {
            "claims": claims,
            "query_id": public["query_id"],
            "status": public["status"],
        }
    )
    if public["trace_id"] != expected_trace:
        raise IntegrationError("public trace_id 无法重算")
    return public


def validate_audit_projection(value: Any) -> dict[str, Any]:
    audit = _exact_fields(
        value,
        {
            "schema_version",
            "visibility",
            "trace_id",
            "authorization_revision",
            "index_generation_id",
            "selected_entry_ids",
            "filter_summary",
            "query_binding_sha256",
            "failure",
        },
        "protected audit",
    )
    if audit["schema_version"] != AUDIT_SCHEMA_VERSION:
        raise IntegrationError("audit schema_version 不匹配")
    if audit["visibility"] != "protected":
        raise IntegrationError("audit visibility 必须是 protected")
    for name in {"trace_id", "authorization_revision", "index_generation_id"}:
        _token(name, audit[name])
    _sha256("query_binding_sha256", audit["query_binding_sha256"])
    selected = audit["selected_entry_ids"]
    if not isinstance(selected, list) or not all(
        isinstance(item, str) and item for item in selected
    ):
        raise IntegrationError("selected_entry_ids 必须是字符串数组")
    if len(selected) != len(set(selected)):
        raise IntegrationError("selected_entry_ids 不得重复")
    summary = _exact_fields(
        audit["filter_summary"],
        {
            "all_chunks",
            "tenant_chunks",
            "live_chunks",
            "acl_chunks",
            "selected_chunks",
        },
        "filter_summary",
    )
    counts: list[int] = []
    for name in (
        "all_chunks",
        "tenant_chunks",
        "live_chunks",
        "acl_chunks",
        "selected_chunks",
    ):
        count = summary[name]
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise IntegrationError(f"filter_summary.{name} 必须是非负整数")
        counts.append(count)
    if not all(left >= right for left, right in zip(counts, counts[1:])):
        raise IntegrationError("filter_summary 计数不满足逐层过滤关系")
    if counts[-1] != len(selected):
        raise IntegrationError("selected count 与 selected_entry_ids 不一致")
    failure = audit["failure"]
    if failure is not None:
        item = _exact_fields(failure, {"code", "retryable"}, "failure")
        if item != {"code": "retrieval_unavailable", "retryable": True}:
            raise IntegrationError("failure 内容非法")
        if selected:
            raise IntegrationError("dependency failure 不得含 selected entries")
    return audit


def initialize_fixture(
    fixture: dict[str, Any], source_root: Path, *, database_path: str = ":memory:"
) -> CrossLayerEngine:
    return CrossLayerEngine(fixture, source_root, database_path=database_path)


def evaluate_fixture(
    engine: CrossLayerEngine,
    fixture: dict[str, Any],
    *,
    observed_failure: str | None = None,
) -> dict[str, Any]:
    require_fixture_integrity(fixture)
    cases: list[dict[str, Any]] = []
    passed_count = 0
    for oracle in fixture["queries"]:
        query = _runtime_query(oracle)
        public, audit = engine.query(query, observed_failure=observed_failure)
        evidence_errors = engine.validate_evidence(
            query,
            public,
            audit,
            observed_failure=observed_failure,
        )
        actual_claim_texts = [claim["text"] for claim in public["claims"]]
        observed_document_ids = sorted(
            {
                citation["document_id"]
                for claim in public["claims"]
                for citation in claim["citations"]
            }
        )
        expected_status = (
            "answered" if oracle["expected_claim_texts"] else "insufficient_evidence"
        )
        errors = list(evidence_errors)
        if public["status"] != expected_status:
            errors.append("status_mismatch")
        if actual_claim_texts != oracle["expected_claim_texts"]:
            errors.append("claim_oracle_mismatch")
        if set(observed_document_ids).intersection(oracle["forbidden_document_ids"]):
            errors.append("forbidden_document_observed")
        passed = not errors
        passed_count += int(passed)
        cases.append(
            {
                "query_id": oracle["query_id"],
                "expected_status": expected_status,
                "actual_status": public["status"],
                "expected_claim_texts": list(oracle["expected_claim_texts"]),
                "actual_claim_texts": actual_claim_texts,
                "forbidden_document_ids": list(oracle["forbidden_document_ids"]),
                "observed_document_ids": observed_document_ids,
                "evidence_errors": errors,
                "passed": passed,
            }
        )
    generation = engine._published_generation()
    total = len(cases)
    body = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "fixture_sha256": _sha256("fixture_sha256", fixture["fixture_sha256"]),
        "fixture_model_sha256": _sha256(
            "fixture_model_sha256", fixture["fixture_model_sha256"]
        ),
        "pipeline_fingerprint": engine.pipeline_fingerprint,
        "capture_state_sha256": generation.capture_state_sha256,
        "capture_artifact_sha256": generation.capture_artifact_sha256,
        "index_generation_id": generation.generation_id,
        "release_manifest_sha256": generation.manifest_sha256,
        "harness_revision": HARNESS_REVISION,
        "failure_injection": observed_failure,
        "cases": cases,
        "summary": {
            "total": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "decision": "PASS" if passed_count == total else "BLOCK",
        },
    }
    return {**body, "artifact_sha256": digest_object(body)}


def validate_artifact(value: Any) -> list[str]:
    errors: list[str] = []
    try:
        artifact = _exact_fields(
            value,
            {
                "schema_version",
                "fixture_sha256",
                "fixture_model_sha256",
                "pipeline_fingerprint",
                "capture_state_sha256",
                "capture_artifact_sha256",
                "index_generation_id",
                "release_manifest_sha256",
                "harness_revision",
                "failure_injection",
                "cases",
                "summary",
                "artifact_sha256",
            },
            "evaluation artifact",
        )
        if artifact["schema_version"] != ARTIFACT_SCHEMA_VERSION:
            raise IntegrationError("artifact schema_version 不匹配")
        for name in {
            "fixture_sha256",
            "fixture_model_sha256",
            "pipeline_fingerprint",
            "capture_state_sha256",
            "capture_artifact_sha256",
            "release_manifest_sha256",
            "artifact_sha256",
        }:
            _sha256(name, artifact[name])
        for name in {"index_generation_id", "harness_revision"}:
            _token(name, artifact[name])
        if artifact["failure_injection"] not in {None, "retrieval_unavailable"}:
            raise IntegrationError("artifact failure_injection 非法")
        cases = artifact["cases"]
        if not isinstance(cases, list) or not cases:
            raise IntegrationError("artifact cases 必须是非空数组")
        passed = 0
        query_ids: set[str] = set()
        for index, case_value in enumerate(cases):
            case = _exact_fields(
                case_value,
                {
                    "query_id",
                    "expected_status",
                    "actual_status",
                    "expected_claim_texts",
                    "actual_claim_texts",
                    "forbidden_document_ids",
                    "observed_document_ids",
                    "evidence_errors",
                    "passed",
                },
                f"artifact case[{index}]",
            )
            query_id = _token("query_id", case["query_id"])
            if query_id in query_ids:
                raise IntegrationError("artifact query_id 重复")
            query_ids.add(query_id)
            if case["expected_status"] not in {"answered", "insufficient_evidence"}:
                raise IntegrationError("case expected_status 非法")
            if case["actual_status"] not in {
                "answered",
                "insufficient_evidence",
                "dependency_unavailable",
            }:
                raise IntegrationError("case actual_status 非法")
            for name in {
                "expected_claim_texts",
                "actual_claim_texts",
                "forbidden_document_ids",
                "observed_document_ids",
                "evidence_errors",
            }:
                items = case[name]
                if not isinstance(items, list) or not all(
                    isinstance(item, str) for item in items
                ):
                    raise IntegrationError(f"case.{name} 必须是字符串数组")
            if not isinstance(case["passed"], bool):
                raise IntegrationError("case.passed 必须是布尔值")
            if case["passed"] != (not case["evidence_errors"]):
                raise IntegrationError("case.passed 与 evidence_errors 矛盾")
            passed += int(case["passed"])
        summary = _exact_fields(
            artifact["summary"],
            {"total", "passed", "failed", "decision"},
            "artifact summary",
        )
        for name in {"total", "passed", "failed"}:
            if (
                not isinstance(summary[name], int)
                or isinstance(summary[name], bool)
                or summary[name] < 0
            ):
                raise IntegrationError(f"summary.{name} 必须是非负整数")
        if summary["total"] != len(cases):
            raise IntegrationError("summary.total 不一致")
        if summary["passed"] != passed or summary["failed"] != len(cases) - passed:
            raise IntegrationError("summary passed/failed 不一致")
        expected_decision = "PASS" if passed == len(cases) else "BLOCK"
        if summary["decision"] != expected_decision:
            raise IntegrationError("summary.decision 不一致")
        body = {key: copy.deepcopy(item) for key, item in artifact.items() if key != "artifact_sha256"}
        if digest_object(body) != artifact["artifact_sha256"]:
            raise IntegrationError("artifact_sha256 不一致")
    except IntegrationError as exc:
        errors.append(str(exc))
    return errors


def _fixture_query(fixture: dict[str, Any], query_id: str) -> dict[str, Any]:
    for query in fixture["queries"]:
        if query["query_id"] == query_id:
            return _runtime_query(query)
    raise IntegrationError(f"fixture 不存在 query_id：{query_id}")


def _write_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path(__file__).with_name("cross-layer-fixture.json"),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    ask = subparsers.add_parser("ask", help="只输出 public projection")
    ask.add_argument("--query-id", required=True)
    inspect = subparsers.add_parser("inspect", help="输出 public + protected audit")
    inspect.add_argument("--query-id", required=True)
    inspect.add_argument("--operator-view", action="store_true")
    manifest = subparsers.add_parser("manifest", help="输出受保护 release manifest")
    manifest.add_argument("--operator-view", action="store_true")
    evaluate = subparsers.add_parser("evaluate", help="运行 fixture release gate")
    evaluate.add_argument("--operator-view", action="store_true")
    evaluate.add_argument(
        "--failure", choices=["retrieval_unavailable"], default=None
    )
    subparsers.add_parser("demo", help="输出全部 public answers 与 gate 摘要")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fixture = load_fixture(args.fixture)
    with tempfile.TemporaryDirectory(prefix="cross-layer-adapter-") as temporary:
        engine = initialize_fixture(fixture, Path(temporary) / "sources")
        try:
            if args.command == "ask":
                public, _audit = engine.query(_fixture_query(fixture, args.query_id))
                _write_json(public)
                return 0
            if args.command == "inspect":
                if not args.operator_view:
                    raise IntegrationError("inspect 必须显式提供 --operator-view")
                public, audit = engine.query(_fixture_query(fixture, args.query_id))
                _write_json({"public": public, "protected_audit": audit})
                return 0
            if args.command == "manifest":
                if not args.operator_view:
                    raise IntegrationError(
                        "manifest 必须显式提供 --operator-view；该 flag 不替代真实鉴权"
                    )
                _write_json(engine._published_generation().manifest)
                return 0
            if args.command == "evaluate" and not args.operator_view:
                raise IntegrationError(
                    "evaluate 必须显式提供 --operator-view；该 flag 不替代真实鉴权"
                )
            artifact = evaluate_fixture(
                engine,
                fixture,
                observed_failure=getattr(args, "failure", None),
            )
            if validate_artifact(artifact):
                raise IntegrationError("evaluation artifact 自校验失败")
            if args.command == "evaluate":
                _write_json(artifact)
            else:
                answers = [
                    engine.query(_runtime_query(query))[0]
                    for query in fixture["queries"]
                ]
                _write_json({"answers": answers, "summary": artifact["summary"]})
            return 0 if artifact["summary"]["decision"] == "PASS" else 1
        finally:
            engine.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (IntegrationError, CHUNK.ChunkingError, KB.StoreError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
