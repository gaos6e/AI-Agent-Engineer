"""Tests for the offline chunking experiment.

The suite deliberately covers input contracts, provenance, ACL boundaries and
determinism.  It uses only the Python standard library.
"""

from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import chunking_lab as lab


HERE = Path(__file__).resolve().parent
CORPUS_PATH = HERE / "corpus.json"
QUERIES_PATH = HERE / "queries.json"


def make_element(
    element_id: str,
    text: str,
    *,
    source_id: str = "source-a",
    source_revision: str = "rev-1",
    kind: str = "paragraph",
    section_path: tuple[str, ...] = ("标题",),
    acl: tuple[str, ...] = ("readers",),
) -> lab.Element:
    return lab.Element(
        source_id=source_id,
        source_revision=source_revision,
        element_id=element_id,
        kind=kind,
        text=text,
        section_path=section_path,
        acl=acl,
        line_start=1,
        line_end=1,
    )


class JsonFixtureMixin:
    def write_json(self, value: object) -> Path:
        handle = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".json", delete=False
        )
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        with handle:
            json.dump(value, handle, ensure_ascii=False, allow_nan=False)
        return Path(handle.name)

    def write_raw(self, value: str) -> Path:
        handle = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".json", delete=False
        )
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        with handle:
            handle.write(value)
        return Path(handle.name)


class UnitAndConfigTests(unittest.TestCase):
    def test_lexical_units_keep_exact_character_offsets(self) -> None:
        text = "API 超时 3.5 秒"
        units = lab.lexical_units(text)
        self.assertEqual([unit.value for unit in units], ["API", "超", "时", "3.5", "秒"])
        self.assertEqual(
            [text[unit.char_start : unit.char_end] for unit in units],
            [unit.value for unit in units],
        )

    def test_config_accepts_zero_overlap(self) -> None:
        lab.ChunkConfig(max_units=1, overlap_units=0, strategy_version="v1").validate()

    def test_config_rejects_invalid_numeric_boundaries_and_bool(self) -> None:
        invalid = [
            lab.ChunkConfig(max_units=0),
            lab.ChunkConfig(max_units=True),
            lab.ChunkConfig(max_units=4, overlap_units=4),
            lab.ChunkConfig(max_units=4, overlap_units=-1),
            lab.ChunkConfig(max_units=4, overlap_units=False),
        ]
        for config in invalid:
            with self.subTest(config=config), self.assertRaises(lab.ChunkingError):
                config.validate()

    def test_config_rejects_blank_strategy_version(self) -> None:
        with self.assertRaises(lab.ChunkingError):
            lab.ChunkConfig(strategy_version=" ").validate()


class LoadingTests(JsonFixtureMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        self.queries = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))

    def test_checked_fixtures_load_and_anchor_quotes(self) -> None:
        elements = lab.load_elements(CORPUS_PATH)
        cases = lab.load_query_cases(QUERIES_PATH, elements)
        self.assertEqual(len(elements), 9)
        self.assertEqual(len(cases), 9)
        first_anchor = cases[0].evidence[0]
        self.assertEqual(first_anchor.element_id, "api-e1")
        self.assertGreater(first_anchor.unit_end, first_anchor.unit_start)

    def test_duplicate_json_key_is_rejected(self) -> None:
        path = self.write_raw('[{"source_id":"a","source_id":"b"}]')
        with self.assertRaisesRegex(lab.ChunkingError, "重复字段"):
            lab.load_elements(path)

    def test_nonfinite_json_number_is_rejected(self) -> None:
        path = self.write_raw('[{"value":NaN}]')
        with self.assertRaisesRegex(lab.ChunkingError, "非有限"):
            lab.load_elements(path)

    def test_corpus_requires_exact_fields(self) -> None:
        del self.corpus[0]["line_end"]
        with self.assertRaisesRegex(lab.ChunkingError, "字段必须精确"):
            lab.load_elements(self.write_json(self.corpus))

    def test_corpus_rejects_duplicate_element_id(self) -> None:
        self.corpus[1]["element_id"] = self.corpus[0]["element_id"]
        with self.assertRaisesRegex(lab.ChunkingError, "element_id 重复"):
            lab.load_elements(self.write_json(self.corpus))

    def test_corpus_rejects_kind_acl_and_line_errors(self) -> None:
        mutations = [
            ("kind", "image", "不支持的 kind"),
            ("acl", ["employees", "employees"], "acl 不得重复"),
            ("line_start", 0, "行号范围不合法"),
            ("line_end", False, "行号范围不合法"),
        ]
        for field, value, message in mutations:
            corpus = json.loads(json.dumps(self.corpus, ensure_ascii=False))
            corpus[0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                lab.ChunkingError, message
            ):
                lab.load_elements(self.write_json(corpus))

    def test_crlf_is_normalised_and_acl_is_sorted(self) -> None:
        self.corpus[0]["text"] = "第一行\r\n第二行"
        self.corpus[0]["acl"] = ["z", "a"]
        element = lab.load_elements(self.write_json([self.corpus[0]]))[0]
        self.assertEqual(element.text, "第一行\n第二行")
        self.assertEqual(element.acl, ("a", "z"))

    def test_query_requires_existing_element_and_unique_id(self) -> None:
        elements = lab.load_elements(CORPUS_PATH)
        missing = json.loads(json.dumps(self.queries, ensure_ascii=False))
        missing[0]["evidence"][0]["element_id"] = "missing"
        with self.assertRaisesRegex(lab.ChunkingError, "不存在元素"):
            lab.load_query_cases(self.write_json(missing), elements)
        duplicated = [self.queries[0], self.queries[0]]
        with self.assertRaisesRegex(lab.ChunkingError, "query_id 重复"):
            lab.load_query_cases(self.write_json(duplicated), elements)

    def test_quote_must_exist_once_and_align_to_unit_boundaries(self) -> None:
        element = make_element("e1", "abc abc")
        cases = [{
            "query_id": "q1",
            "query": "abc",
            "subject_groups": ["readers"],
            "evidence": [{"element_id": "e1", "quote": "abc"}],
        }]
        with self.assertRaisesRegex(lab.ChunkingError, "唯一出现"):
            lab.load_query_cases(self.write_json(cases), [element])
        element = make_element("e1", "abcdef")
        cases[0]["evidence"][0]["quote"] = "bc"
        with self.assertRaisesRegex(lab.ChunkingError, "边界对齐"):
            lab.load_query_cases(self.write_json(cases), [element])


class ChunkConstructionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.elements = lab.load_elements(CORPUS_PATH)
        self.config = lab.ChunkConfig(max_units=64, overlap_units=8)

    def test_empty_input_produces_no_chunks(self) -> None:
        self.assertEqual(lab.structured_chunks([], self.config), [])
        self.assertEqual(lab.fixed_window_chunks([], self.config), [])

    def test_structured_chunks_obey_hard_max_and_cover_every_unit(self) -> None:
        chunks = lab.structured_chunks(self.elements, self.config)
        self.assertTrue(chunks)
        self.assertTrue(all(0 < chunk.unit_count <= 64 for chunk in chunks))
        lab.validate_chunks(chunks, self.elements, self.config)

    def test_structured_chunks_do_not_cross_boundary_keys(self) -> None:
        by_id = {element.element_id: element for element in self.elements}
        for chunk in lab.structured_chunks(self.elements, self.config):
            sources = {by_id[span.element_id].source_id for span in chunk.element_spans}
            revisions = {
                by_id[span.element_id].source_revision for span in chunk.element_spans
            }
            acls = {by_id[span.element_id].acl for span in chunk.element_spans}
            sections = {
                by_id[span.element_id].section_path for span in chunk.element_spans
            }
            families = {lab._family(by_id[span.element_id].kind) for span in chunk.element_spans}
            self.assertEqual(len(sources), 1)
            self.assertEqual(len(revisions), 1)
            self.assertEqual(len(acls), 1)
            self.assertEqual(len(sections), 1)
            self.assertEqual(len(families), 1)

    def test_short_elements_are_not_split(self) -> None:
        chunks = lab.structured_chunks(self.elements, self.config)
        for element in self.elements:
            if lab.count_units(element.text) <= self.config.max_units:
                matching = [
                    span
                    for chunk in chunks
                    for span in chunk.element_spans
                    if span.element_id == element.element_id
                ]
                self.assertEqual(matching, [lab.ElementSpan(element.element_id, 0, lab.count_units(element.text))])

    def test_oversized_element_uses_actual_overlap_and_terminates(self) -> None:
        element = make_element("long", " ".join(f"u{i}" for i in range(25)))
        config = lab.ChunkConfig(max_units=10, overlap_units=3)
        chunks = lab.structured_chunks([element], config)
        self.assertEqual([chunk.unit_count for chunk in chunks], [10, 10, 10, 4])
        self.assertEqual([chunk.overlap_units for chunk in chunks], [0, 3, 3, 3])
        self.assertEqual(
            [(span.unit_start, span.unit_end) for chunk in chunks for span in chunk.element_spans],
            [(0, 10), (7, 17), (14, 24), (21, 25)],
        )

    def test_table_header_is_retrieval_context_not_row_body(self) -> None:
        # A deliberately small budget separates the header from later rows and
        # therefore exercises the retrieval-only header propagation branch.
        chunks = lab.structured_chunks(
            self.elements, lab.ChunkConfig(max_units=10, overlap_units=2)
        )
        row_chunk = next(
            chunk
            for chunk in chunks
            if any(span.element_id == "deploy-e2" for span in chunk.element_spans)
            and not any(span.element_id == "deploy-e1" for span in chunk.element_spans)
        )
        self.assertNotIn("环境 | 副本数 | 审批", row_chunk.text)
        self.assertIn("表头：环境 | 副本数 | 审批", row_chunk.retrieval_text)
        self.assertNotEqual(row_chunk.content_sha256, row_chunk.retrieval_sha256)

    def test_chunk_id_is_stable_when_unrelated_chunk_is_inserted_before_it(self) -> None:
        original = lab.structured_chunks(self.elements, self.config)
        unrelated = make_element(
            "new-e1", "完全无关的来源", source_id="new-source", section_path=("新来源",)
        )
        changed = lab.structured_chunks([unrelated, *self.elements], self.config)
        original_ids = {chunk.chunk_id for chunk in original}
        changed_ids = {chunk.chunk_id for chunk in changed}
        self.assertTrue(original_ids.issubset(changed_ids))

    def test_chunk_id_changes_with_revision_content_or_strategy(self) -> None:
        element = make_element("e1", "alpha beta")
        base = lab.structured_chunks([element], lab.ChunkConfig())[0].chunk_id
        variants = [
            replace(element, source_revision="rev-2"),
            replace(element, text="alpha gamma"),
        ]
        for variant in variants:
            self.assertNotEqual(
                base, lab.structured_chunks([variant], lab.ChunkConfig())[0].chunk_id
            )
        self.assertNotEqual(
            base,
            lab.structured_chunks(
                [element], lab.ChunkConfig(strategy_version="structure-v2")
            )[0].chunk_id,
        )

    def test_fixed_baseline_can_cross_sections_but_not_security_boundaries(self) -> None:
        chunks = lab.fixed_window_chunks(self.elements, self.config)
        by_id = {element.element_id: element for element in self.elements}
        self.assertTrue(
            any(
                len({by_id[span.element_id].section_path for span in chunk.element_spans}) > 1
                for chunk in chunks
            )
        )
        for chunk in chunks:
            self.assertEqual(
                {by_id[span.element_id].source_id for span in chunk.element_spans},
                {chunk.source_id},
            )
            self.assertEqual(
                {by_id[span.element_id].source_revision for span in chunk.element_spans},
                {chunk.source_revision},
            )
            self.assertEqual(
                {by_id[span.element_id].acl for span in chunk.element_spans},
                {chunk.acl},
            )

    def test_validation_detects_hash_and_coverage_tampering(self) -> None:
        chunks = lab.structured_chunks(self.elements, self.config)
        bad_hash = [replace(chunks[0], content_sha256="0" * 64), *chunks[1:]]
        with self.assertRaisesRegex(lab.ChunkingError, "content hash"):
            lab.validate_chunks(bad_hash, self.elements, self.config)
        missing = chunks[1:]
        renumbered = [replace(chunk, ordinal=index) for index, chunk in enumerate(missing, 1)]
        with self.assertRaisesRegex(lab.ChunkingError, "完整覆盖"):
            lab.validate_chunks(renumbered, self.elements, self.config)


class RetrievalAndReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.elements = lab.load_elements(CORPUS_PATH)
        cls.cases = lab.load_query_cases(QUERIES_PATH, cls.elements)
        cls.config = lab.ChunkConfig()
        cls.chunks = lab.structured_chunks(cls.elements, cls.config)

    def test_acl_is_filtered_before_ranking(self) -> None:
        employees = lab.retrieve(
            "production 4 SRE", self.chunks, subject_groups=["employees"], k=5
        )
        platform = lab.retrieve(
            "production 4 SRE", self.chunks, subject_groups=["platform"], k=5
        )
        self.assertEqual(employees, [])
        self.assertTrue(platform)
        self.assertTrue(all(item.chunk.acl == ("platform",) for item in platform))

    def test_zero_score_empty_groups_and_invalid_k_return_safely(self) -> None:
        self.assertEqual(
            lab.retrieve("ZXQ-991", self.chunks, subject_groups=["employees"], k=3),
            [],
        )
        self.assertEqual(
            lab.retrieve("超时", self.chunks, subject_groups=[], k=3),
            [],
        )
        for value in (0, -1, True):
            with self.subTest(k=value), self.assertRaises(lab.ChunkingError):
                lab.retrieve("超时", self.chunks, subject_groups=["employees"], k=value)

    def test_evaluation_uses_anchored_evidence_and_no_answer_cases(self) -> None:
        report = lab.evaluate(self.chunks, self.cases, k=3)
        self.assertEqual(report["answerable_cases"], 7)
        self.assertEqual(report["no_answer_cases"], 2)
        self.assertEqual(report["mean_anchor_recall_at_k"], 1.0)
        self.assertEqual(report["no_answer_accuracy"], 1.0)
        self.assertEqual(len(report["details"]), len(self.cases))

    def test_cost_report_exposes_overlap_and_context_cost(self) -> None:
        report = lab.cost_report(self.chunks, self.elements)
        self.assertGreater(report["retrieval_units"], report["body_units"])
        self.assertGreaterEqual(report["body_duplication_ratio"], 0.0)
        self.assertLessEqual(report["max_chunk_units"], self.config.max_units)

    def test_experiment_is_deterministic_in_process(self) -> None:
        first = lab.run_experiment(self.elements, self.cases, self.config)
        second = lab.run_experiment(self.elements, self.cases, self.config)
        self.assertEqual(first, second)
        self.assertEqual(
            first["unit_definition"], "regex lexical units; not a model tokenizer"
        )

    def test_cli_output_matches_under_normal_and_optimized_python(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        command = [sys.executable, "-B", "-W", "error", str(HERE / "chunking_lab.py")]
        normal = subprocess.run(
            command,
            cwd=HERE,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        optimized = subprocess.run(
            [sys.executable, "-B", "-O", "-W", "error", str(HERE / "chunking_lab.py")],
            cwd=HERE,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(normal.stdout, optimized.stdout)
        json.loads(normal.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
