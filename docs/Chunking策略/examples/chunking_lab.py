"""离线 Chunking 实验：结构策略、固定窗口、稳定证据锚点与检索评测。

计量单位是本项目自定义 lexical unit，不是任何模型 tokenizer。
接入真实 embedding/LLM 前必须替换计数器并重新评测。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import statistics
import sys
from typing import Any, Iterable, Sequence
import unicodedata


UNIT_PATTERN = re.compile(
    r"[A-Za-z0-9_]+(?:[-.][A-Za-z0-9_]+)*|[\u4e00-\u9fff]|[^\s]"
)
SEARCHABLE_PATTERN = re.compile(r"[A-Za-z0-9_\u4e00-\u9fff]")
ALLOWED_KINDS = {
    "paragraph",
    "list_item",
    "code_block",
    "table_header",
    "table_row",
}


class ChunkingError(ValueError):
    """输入契约、边界或评测锚点错误。"""


@dataclass(frozen=True)
class Unit:
    value: str
    char_start: int
    char_end: int


@dataclass(frozen=True)
class Element:
    source_id: str
    source_revision: str
    element_id: str
    kind: str
    text: str
    section_path: tuple[str, ...]
    acl: tuple[str, ...]
    line_start: int
    line_end: int


@dataclass(frozen=True)
class ElementSpan:
    element_id: str
    unit_start: int
    unit_end: int


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_id: str
    source_revision: str
    strategy_version: str
    ordinal: int
    family: str
    text: str
    retrieval_text: str
    unit_count: int
    retrieval_unit_count: int
    overlap_units: int
    section_path: tuple[str, ...]
    acl: tuple[str, ...]
    element_spans: tuple[ElementSpan, ...]
    content_sha256: str
    retrieval_sha256: str


@dataclass(frozen=True)
class EvidenceAnchor:
    element_id: str
    quote: str
    unit_start: int
    unit_end: int


@dataclass(frozen=True)
class QueryCase:
    query_id: str
    query: str
    subject_groups: tuple[str, ...]
    evidence: tuple[EvidenceAnchor, ...]


@dataclass(frozen=True)
class ChunkConfig:
    max_units: int = 64
    overlap_units: int = 8
    strategy_version: str = "structure-v1"

    def validate(self) -> None:
        if not isinstance(self.max_units, int) or isinstance(self.max_units, bool):
            raise ChunkingError("max_units 必须是整数")
        if not isinstance(self.overlap_units, int) or isinstance(self.overlap_units, bool):
            raise ChunkingError("overlap_units 必须是整数")
        if self.max_units <= 0 or not 0 <= self.overlap_units < self.max_units:
            raise ChunkingError("要求 max_units > 0 且 0 <= overlap_units < max_units")
        _clean_token("strategy_version", self.strategy_version)


@dataclass(frozen=True)
class RankedChunk:
    rank: int
    score: int
    chunk: Chunk


@dataclass
class _Draft:
    source_id: str
    source_revision: str
    family: str
    section_path: tuple[str, ...]
    acl: tuple[str, ...]
    parts: list[tuple[Element, int, int, str]]
    overlap_units: int = 0


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


def _clean_token(name: str, value: str, maximum: int = 300) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ChunkingError(f"{name} 必须是无首尾空白的非空字符串")
    if len(value) > maximum or any(ord(character) < 32 for character in value):
        raise ChunkingError(f"{name} 长度或控制字符不合法")
    return value


def lexical_units(text: str) -> tuple[Unit, ...]:
    return tuple(Unit(match.group(0), match.start(), match.end()) for match in UNIT_PATTERN.finditer(text))


def count_units(text: str) -> int:
    return len(lexical_units(text))


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ChunkingError(f"JSON 出现重复字段：{key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise ChunkingError(f"JSON 不允许非有限数值：{value}")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ChunkingError(f"{path.name} JSON 错误：{exc.lineno}:{exc.colno}") from exc


def _require_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ChunkingError(
            f"{label} 字段必须精确为 {sorted(expected)}，实际为 {sorted(actual)}"
        )


def load_elements(path: Path) -> list[Element]:
    payload = _load_json(path)
    if not isinstance(payload, list) or not payload:
        raise ChunkingError("corpus 顶层必须是非空数组")
    elements: list[Element] = []
    seen: set[str] = set()
    expected = {
        "source_id",
        "source_revision",
        "element_id",
        "kind",
        "text",
        "section_path",
        "acl",
        "line_start",
        "line_end",
    }
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ChunkingError(f"corpus[{index}] 必须是 object")
        _require_fields(item, expected, f"corpus[{index}]")
        source_id = _clean_token("source_id", item["source_id"])
        source_revision = _clean_token("source_revision", item["source_revision"])
        element_id = _clean_token("element_id", item["element_id"])
        if element_id in seen:
            raise ChunkingError(f"element_id 重复：{element_id}")
        seen.add(element_id)
        kind = _clean_token("kind", item["kind"])
        if kind not in ALLOWED_KINDS:
            raise ChunkingError(f"不支持的 kind：{kind}")
        if not isinstance(item["text"], str):
            raise ChunkingError("text 必须是字符串")
        text = _normalise_text(item["text"])
        if not text.strip() or not lexical_units(text):
            raise ChunkingError(f"{element_id} text 不得为空")
        if not isinstance(item["section_path"], list) or not item["section_path"]:
            raise ChunkingError(f"{element_id} section_path 必须是非空数组")
        section_path = tuple(_clean_token("section", part) for part in item["section_path"])
        if not isinstance(item["acl"], list) or not item["acl"]:
            raise ChunkingError(f"{element_id} acl 必须是非空数组")
        acl_values = tuple(_clean_token("acl", group) for group in item["acl"])
        if len(set(acl_values)) != len(acl_values):
            raise ChunkingError(f"{element_id} acl 不得重复")
        acl = tuple(sorted(acl_values))
        line_start = item["line_start"]
        line_end = item["line_end"]
        if (
            not isinstance(line_start, int)
            or isinstance(line_start, bool)
            or not isinstance(line_end, int)
            or isinstance(line_end, bool)
            or line_start <= 0
            or line_end < line_start
        ):
            raise ChunkingError(f"{element_id} 行号范围不合法")
        elements.append(
            Element(
                source_id,
                source_revision,
                element_id,
                kind,
                text,
                section_path,
                acl,
                line_start,
                line_end,
            )
        )
    return elements


def _anchor_from_quote(element: Element, quote: str) -> EvidenceAnchor:
    quote = _normalise_text(_clean_token("quote", quote, maximum=2_000))
    first = element.text.find(quote)
    if first < 0 or element.text.find(quote, first + 1) >= 0:
        raise ChunkingError(f"quote 必须在 {element.element_id} 中唯一出现：{quote}")
    char_end = first + len(quote)
    units = lexical_units(element.text)
    starts = [index for index, unit in enumerate(units) if unit.char_start == first]
    ends = [index + 1 for index, unit in enumerate(units) if unit.char_end == char_end]
    if not starts or not ends or starts[0] >= ends[-1]:
        raise ChunkingError(f"quote 必须与 lexical unit 边界对齐：{quote}")
    return EvidenceAnchor(element.element_id, quote, starts[0], ends[-1])


def load_query_cases(path: Path, elements: Sequence[Element]) -> list[QueryCase]:
    payload = _load_json(path)
    if not isinstance(payload, list) or not payload:
        raise ChunkingError("queries 顶层必须是非空数组")
    by_id = {element.element_id: element for element in elements}
    cases: list[QueryCase] = []
    seen: set[str] = set()
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ChunkingError(f"queries[{index}] 必须是 object")
        _require_fields(
            item,
            {"query_id", "query", "subject_groups", "evidence"},
            f"queries[{index}]",
        )
        query_id = _clean_token("query_id", item["query_id"])
        if query_id in seen:
            raise ChunkingError(f"query_id 重复：{query_id}")
        seen.add(query_id)
        query = _clean_token("query", item["query"], maximum=2_000)
        if not isinstance(item["subject_groups"], list):
            raise ChunkingError("subject_groups 必须是数组")
        groups = tuple(sorted({_clean_token("subject_group", value) for value in item["subject_groups"]}))
        if not isinstance(item["evidence"], list):
            raise ChunkingError("evidence 必须是数组")
        anchors: list[EvidenceAnchor] = []
        for evidence_index, evidence in enumerate(item["evidence"]):
            if not isinstance(evidence, dict):
                raise ChunkingError(f"evidence[{evidence_index}] 必须是 object")
            _require_fields(evidence, {"element_id", "quote"}, "evidence")
            element_id = _clean_token("element_id", evidence["element_id"])
            if element_id not in by_id:
                raise ChunkingError(f"evidence 指向不存在元素：{element_id}")
            anchors.append(_anchor_from_quote(by_id[element_id], evidence["quote"]))
        cases.append(QueryCase(query_id, query, groups, tuple(anchors)))
    return cases


def _family(kind: str) -> str:
    if kind.startswith("table_"):
        return "table"
    if kind == "code_block":
        return "code"
    return "prose"


def _window_slices(text: str, max_units: int, overlap_units: int) -> list[tuple[str, int, int, int]]:
    units = lexical_units(text)
    if not units:
        return []
    if len(units) <= max_units:
        return [(text.strip(), 0, len(units), 0)]
    step = max_units - overlap_units
    result: list[tuple[str, int, int, int]] = []
    start = 0
    while start < len(units):
        end = min(start + max_units, len(units))
        char_start = units[start].char_start
        char_end = units[end - 1].char_end
        actual_overlap = 0 if not result else max(0, result[-1][2] - start)
        result.append((text[char_start:char_end], start, end, actual_overlap))
        if end == len(units):
            break
        start += step
    return result


def _common_prefix(paths: Sequence[tuple[str, ...]]) -> tuple[str, ...]:
    if not paths:
        return ()
    prefix = list(paths[0])
    for path in paths[1:]:
        length = 0
        for left, right in zip(prefix, path):
            if left != right:
                break
            length += 1
        prefix = prefix[:length]
    return tuple(prefix)


def _draft_text(draft: _Draft) -> str:
    return "\n\n".join(part[3].strip() for part in draft.parts if part[3].strip())


def _build_chunk(
    draft: _Draft,
    *,
    ordinal: int,
    strategy_version: str,
    table_headers: dict[tuple[str, str, tuple[str, ...], tuple[str, ...]], str],
) -> Chunk:
    text = _draft_text(draft)
    if not text:
        raise ChunkingError("不得生成空 chunk")
    spans = tuple(ElementSpan(part[0].element_id, part[1], part[2]) for part in draft.parts)
    context: list[str] = []
    if draft.section_path:
        context.append("标题路径：" + " > ".join(draft.section_path))
    header_key = (draft.source_id, draft.source_revision, draft.section_path, draft.acl)
    includes_header = any(part[0].kind == "table_header" for part in draft.parts)
    if draft.family == "table" and not includes_header and header_key in table_headers:
        context.append("表头：" + table_headers[header_key])
    retrieval_text = "\n".join((*context, text)) if context else text
    content_hash = _digest(text)
    retrieval_hash = _digest(retrieval_text)
    identity = {
        "acl": list(draft.acl),
        "content_sha256": content_hash,
        "element_spans": [asdict(span) for span in spans],
        "source_id": draft.source_id,
        "source_revision": draft.source_revision,
        "strategy_version": strategy_version,
    }
    chunk_id = "chk_" + _digest(_canonical_json(identity))
    return Chunk(
        chunk_id,
        draft.source_id,
        draft.source_revision,
        strategy_version,
        ordinal,
        draft.family,
        text,
        retrieval_text,
        count_units(text),
        count_units(retrieval_text),
        draft.overlap_units,
        draft.section_path,
        draft.acl,
        spans,
        content_hash,
        retrieval_hash,
    )


def structured_chunks(elements: Sequence[Element], config: ChunkConfig) -> list[Chunk]:
    config.validate()
    if not elements:
        return []
    table_headers = {
        (element.source_id, element.source_revision, element.section_path, element.acl): element.text
        for element in elements
        if element.kind == "table_header"
    }
    drafts: list[_Draft] = []
    current: _Draft | None = None

    def flush() -> None:
        nonlocal current
        if current is not None and current.parts:
            drafts.append(current)
        current = None

    for element in elements:
        units = count_units(element.text)
        family = _family(element.kind)
        key = (
            element.source_id,
            element.source_revision,
            family,
            element.section_path,
            element.acl,
        )
        current_key = None if current is None else (
            current.source_id,
            current.source_revision,
            current.family,
            current.section_path,
            current.acl,
        )
        if units > config.max_units:
            flush()
            for piece, start, end, overlap in _window_slices(
                element.text, config.max_units, config.overlap_units
            ):
                drafts.append(
                    _Draft(
                        element.source_id,
                        element.source_revision,
                        family,
                        element.section_path,
                        element.acl,
                        [(element, start, end, piece)],
                        overlap,
                    )
                )
            continue
        if current is None or current_key != key:
            flush()
            current = _Draft(
                element.source_id,
                element.source_revision,
                family,
                element.section_path,
                element.acl,
                [],
            )
        candidate_parts = [*current.parts, (element, 0, units, element.text)]
        candidate = _Draft(
            current.source_id,
            current.source_revision,
            current.family,
            current.section_path,
            current.acl,
            candidate_parts,
        )
        if current.parts and count_units(_draft_text(candidate)) > config.max_units:
            flush()
            current = _Draft(
                element.source_id,
                element.source_revision,
                family,
                element.section_path,
                element.acl,
                [(element, 0, units, element.text)],
            )
        else:
            current.parts = candidate_parts
    flush()
    chunks = [
        _build_chunk(
            draft,
            ordinal=index,
            strategy_version=config.strategy_version,
            table_headers=table_headers,
        )
        for index, draft in enumerate(drafts, start=1)
    ]
    validate_chunks(chunks, elements, config)
    return chunks


def fixed_window_chunks(elements: Sequence[Element], config: ChunkConfig) -> list[Chunk]:
    config.validate()
    if not elements:
        return []
    table_headers: dict[tuple[str, str, tuple[str, ...], tuple[str, ...]], str] = {}
    drafts: list[_Draft] = []
    group: list[Element] = []

    def flush_group() -> None:
        nonlocal group
        if not group:
            return
        flat = "\n\n".join(element.text.strip() for element in group)
        offsets: list[tuple[Element, int, int]] = []
        cursor = 0
        for element in group:
            length = count_units(element.text)
            offsets.append((element, cursor, cursor + length))
            cursor += length
        for piece, start, end, overlap in _window_slices(
            flat, config.max_units, config.overlap_units
        ):
            parts: list[tuple[Element, int, int, str]] = []
            paths: list[tuple[str, ...]] = []
            for element, element_start, element_end in offsets:
                local_start = max(start, element_start) - element_start
                local_end = min(end, element_end) - element_start
                if local_start < local_end:
                    element_units = lexical_units(element.text)
                    char_start = element_units[local_start].char_start
                    char_end = element_units[local_end - 1].char_end
                    parts.append(
                        (
                            element,
                            local_start,
                            local_end,
                            element.text[char_start:char_end],
                        )
                    )
                    paths.append(element.section_path)
            if parts:
                drafts.append(
                    _Draft(
                        group[0].source_id,
                        group[0].source_revision,
                        "fixed",
                        _common_prefix(paths),
                        group[0].acl,
                        parts,
                        overlap,
                    )
                )
        group = []

    for element in elements:
        if group and (
            element.source_id != group[0].source_id
            or element.source_revision != group[0].source_revision
            or element.acl != group[0].acl
        ):
            flush_group()
        group.append(element)
    flush_group()
    strategy = "fixed-" + config.strategy_version
    chunks = [
        _build_chunk(
            draft,
            ordinal=index,
            strategy_version=strategy,
            table_headers=table_headers,
        )
        for index, draft in enumerate(drafts, start=1)
    ]
    validate_chunks(chunks, elements, config)
    return chunks


def validate_chunks(
    chunks: Sequence[Chunk], elements: Sequence[Element], config: ChunkConfig
) -> None:
    by_id = {element.element_id: element for element in elements}
    if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
        raise ChunkingError("chunk_id 必须唯一")
    expected_ordinals = list(range(1, len(chunks) + 1))
    if [chunk.ordinal for chunk in chunks] != expected_ordinals:
        raise ChunkingError("chunk ordinal 必须连续且从 1 开始")
    coverage: dict[str, set[int]] = {element.element_id: set() for element in elements}
    for chunk in chunks:
        if not chunk.text or chunk.unit_count > config.max_units:
            raise ChunkingError(f"chunk 为空或超过 hard max：{chunk.chunk_id}")
        if not chunk.acl:
            raise ChunkingError(f"chunk ACL 为空：{chunk.chunk_id}")
        if chunk.content_sha256 != _digest(chunk.text):
            raise ChunkingError(f"content hash 不一致：{chunk.chunk_id}")
        if chunk.retrieval_sha256 != _digest(chunk.retrieval_text):
            raise ChunkingError(f"retrieval hash 不一致：{chunk.chunk_id}")
        if chunk.unit_count != count_units(chunk.text):
            raise ChunkingError(f"unit_count 不一致：{chunk.chunk_id}")
        for span in chunk.element_spans:
            if span.element_id not in by_id:
                raise ChunkingError(f"chunk 指向不存在元素：{span.element_id}")
            element = by_id[span.element_id]
            if (
                element.source_id != chunk.source_id
                or element.source_revision != chunk.source_revision
                or element.acl != chunk.acl
            ):
                raise ChunkingError(f"chunk 跨 source/revision/ACL：{chunk.chunk_id}")
            total = count_units(element.text)
            if not 0 <= span.unit_start < span.unit_end <= total:
                raise ChunkingError(f"元素 span 越界：{span}")
            coverage[span.element_id].update(range(span.unit_start, span.unit_end))
    for element in elements:
        expected = set(range(count_units(element.text)))
        if coverage[element.element_id] != expected:
            raise ChunkingError(f"元素未被完整覆盖：{element.element_id}")


def _search_terms(text: str) -> set[str]:
    return {
        unit.value.casefold()
        for unit in lexical_units(text)
        if SEARCHABLE_PATTERN.search(unit.value)
    }


def retrieve(
    query: str,
    chunks: Sequence[Chunk],
    *,
    subject_groups: Sequence[str],
    k: int,
) -> list[RankedChunk]:
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise ChunkingError("k 必须是正整数")
    groups = set(subject_groups)
    if not groups:
        return []
    query_terms = _search_terms(query)
    scored: list[tuple[int, Chunk]] = []
    for chunk in chunks:
        if not groups.intersection(chunk.acl):
            continue
        score = len(query_terms.intersection(_search_terms(chunk.retrieval_text)))
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda item: (-item[0], item[1].retrieval_unit_count, item[1].chunk_id))
    return [
        RankedChunk(rank, score, chunk)
        for rank, (score, chunk) in enumerate(scored[:k], start=1)
    ]


def _covers(chunk: Chunk, anchor: EvidenceAnchor) -> bool:
    return any(
        span.element_id == anchor.element_id
        and span.unit_start <= anchor.unit_start
        and span.unit_end >= anchor.unit_end
        for span in chunk.element_spans
    )


def evaluate(
    chunks: Sequence[Chunk], cases: Sequence[QueryCase], *, k: int = 3
) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    complete_cases: list[float] = []
    no_answer_scores: list[float] = []
    context_costs: list[int] = []
    for case in cases:
        ranked = retrieve(
            case.query,
            chunks,
            subject_groups=case.subject_groups,
            k=k,
        )
        context_units = sum(item.chunk.retrieval_unit_count for item in ranked)
        context_costs.append(context_units)
        if case.evidence:
            covered = [
                any(_covers(item.chunk, anchor) for item in ranked)
                for anchor in case.evidence
            ]
            recall = sum(covered) / len(covered)
            first_rank = next(
                (
                    item.rank
                    for item in ranked
                    if any(_covers(item.chunk, anchor) for anchor in case.evidence)
                ),
                None,
            )
            reciprocal_rank = 0.0 if first_rank is None else 1.0 / first_rank
            complete = float(all(covered))
            recalls.append(recall)
            reciprocal_ranks.append(reciprocal_rank)
            complete_cases.append(complete)
        else:
            recall = None
            reciprocal_rank = None
            complete = None
            no_answer_scores.append(float(not ranked))
        details.append(
            {
                "query_id": case.query_id,
                "retrieved_chunk_ids": [item.chunk.chunk_id for item in ranked],
                "scores": [item.score for item in ranked],
                "anchor_recall_at_k": recall,
                "reciprocal_rank": reciprocal_rank,
                "complete_evidence_at_k": complete,
                "no_answer_correct": None if case.evidence else float(not ranked),
                "context_units": context_units,
            }
        )

    def mean(values: Sequence[float | int]) -> float:
        return 0.0 if not values else round(float(statistics.fmean(values)), 4)

    return {
        "k": k,
        "answerable_cases": len(recalls),
        "no_answer_cases": len(no_answer_scores),
        "mean_anchor_recall_at_k": mean(recalls),
        "mrr": mean(reciprocal_ranks),
        "complete_evidence_case_rate": mean(complete_cases),
        "no_answer_accuracy": mean(no_answer_scores),
        "mean_context_units": mean(context_costs),
        "details": details,
    }


def cost_report(chunks: Sequence[Chunk], elements: Sequence[Element]) -> dict[str, Any]:
    source_units = sum(count_units(element.text) for element in elements)
    body_units = sum(chunk.unit_count for chunk in chunks)
    retrieval_units = sum(chunk.retrieval_unit_count for chunk in chunks)
    lengths = [chunk.unit_count for chunk in chunks]
    return {
        "chunk_count": len(chunks),
        "source_units": source_units,
        "body_units": body_units,
        "retrieval_units": retrieval_units,
        "body_duplication_ratio": round((body_units - source_units) / source_units, 4),
        "min_chunk_units": min(lengths, default=0),
        "median_chunk_units": 0.0 if not lengths else float(statistics.median(lengths)),
        "max_chunk_units": max(lengths, default=0),
    }


def run_experiment(
    elements: Sequence[Element], cases: Sequence[QueryCase], config: ChunkConfig
) -> dict[str, Any]:
    structured = structured_chunks(elements, config)
    fixed = fixed_window_chunks(elements, config)
    return {
        "unit_definition": "regex lexical units; not a model tokenizer",
        "config": asdict(config),
        "strategies": {
            "structured": {
                "cost": cost_report(structured, elements),
                "evaluation": evaluate(structured, cases),
            },
            "fixed_window": {
                "cost": cost_report(fixed, elements),
                "evaluation": evaluate(fixed, cases),
            },
        },
    }


def main() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", newline="\n")
    base = Path(__file__).resolve().parent
    elements = load_elements(base / "corpus.json")
    cases = load_query_cases(base / "queries.json", elements)
    report = run_experiment(elements, cases, ChunkConfig())
    print(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()
