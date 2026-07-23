from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys
import unittest

from in_memory_retrieval import (
    ToyKeywordEmbedding,
    build_store,
    retrieve_batch,
    sample_documents,
    search,
)
from langchain_core.documents import Document


class ToyEmbeddingTests(unittest.TestCase):
    def test_embedding_dimensions_are_explicit(self) -> None:
        embedding = ToyKeywordEmbedding()
        self.assertEqual(embedding.embed_query("return with receipt"), [2.0, 0.0, 0.0])
        self.assertEqual(embedding.embed_query("security incident"), [0.0, 2.0, 0.0])

    def test_unknown_vocabulary_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "teaching vocabulary"):
            ToyKeywordEmbedding().embed_query("weather forecast")

    def test_empty_text_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            ToyKeywordEmbedding().embed_query("   ")


class InMemoryRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = build_store()

    def test_stable_ids_are_preserved(self) -> None:
        expected_ids = {
            "alpha:refund:v1",
            "alpha:security:v2",
            "beta:refund:v3",
            "beta:billing:v1",
        }
        returned = self.store.get_by_ids(list(reversed(sorted(expected_ids))))
        self.assertEqual(
            {document.id for document in returned},
            expected_ids,
        )
        self.assertTrue(
            all(document.metadata["chunk_id"] == document.id for document in returned)
        )

    def test_duplicate_ids_are_rejected_before_indexing(self) -> None:
        documents = sample_documents()
        documents.append(documents[0])
        with self.assertRaisesRegex(ValueError, "duplicate document id"):
            build_store(documents)

    def test_missing_metadata_is_rejected_before_indexing(self) -> None:
        invalid = Document(
            id="alpha:invalid:v1",
            page_content="refund receipt",
            metadata={"tenant": "alpha"},
        )
        with self.assertRaisesRegex(ValueError, "missing metadata"):
            build_store([invalid])

    def test_tenant_filter_excludes_equally_similar_other_tenant(self) -> None:
        hits = search(
            self.store,
            "return with a receipt",
            tenant="alpha",
            k=3,
            minimum_similarity=0.5,
        )
        self.assertEqual([hit["document_id"] for hit in hits], ["alpha:refund:v1"])
        self.assertTrue(all(hit["metadata"]["tenant"] == "alpha" for hit in hits))

    def test_current_in_memory_raw_score_is_cosine_similarity(self) -> None:
        hits = search(
            self.store,
            "refund return receipt",
            tenant="alpha",
            k=2,
            minimum_similarity=-1.0,
        )
        self.assertEqual(hits[0]["document_id"], "alpha:refund:v1")
        self.assertAlmostEqual(hits[0]["raw_score"], 1.0)
        self.assertGreater(hits[0]["raw_score"], hits[1]["raw_score"])
        self.assertEqual(
            hits[0]["score_semantics"],
            "cosine_similarity_higher_is_more_similar",
        )

    def test_required_provenance_metadata_is_returned(self) -> None:
        hit = search(
            self.store,
            "security incident",
            tenant="alpha",
            k=1,
        )[0]
        self.assertEqual(hit["metadata"]["document_id"], "alpha-security-policy")
        self.assertEqual(hit["metadata"]["version"], "2")
        self.assertEqual(hit["metadata"]["access_scope"], "employees")

    def test_retriever_batch_keeps_filter_and_order(self) -> None:
        ids = retrieve_batch(
            self.store,
            ["return receipt", "security incident"],
            tenant="alpha",
        )
        self.assertEqual(ids, [["alpha:refund:v1"], ["alpha:security:v2"]])

    def test_unknown_tenant_returns_no_hits(self) -> None:
        self.assertEqual(
            search(self.store, "refund", tenant="gamma", minimum_similarity=-1.0),
            [],
        )

    def test_invalid_k_is_rejected_without_assert(self) -> None:
        for value in (True, 0, 21, 1.5):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "k"):
                    search(self.store, "refund", tenant="alpha", k=value)

    def test_non_finite_threshold_is_rejected(self) -> None:
        for value in (float("nan"), float("inf"), -2.0, 2.0):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "minimum_similarity"):
                    search(
                        self.store,
                        "refund",
                        tenant="alpha",
                        minimum_similarity=value,
                    )

    def test_empty_batch_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "queries must not be empty"):
            retrieve_batch(self.store, [], tenant="alpha")

    def test_runtime_example_contains_no_assert_statement(self) -> None:
        source = Path(__file__).with_name("in_memory_retrieval.py").read_text(
            encoding="utf-8"
        )
        parsed = ast.parse(source)
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(parsed)))


class CliTests(unittest.TestCase):
    def test_cli_emits_versioned_json(self) -> None:
        script = Path(__file__).with_name("in_memory_retrieval.py")
        completed = subprocess.run(
            [sys.executable, "-B", str(script)],
            check=False,
            capture_output=True,
            encoding="utf-8",
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["dependencies"]["langchain-core"], "1.4.9")
        self.assertEqual(payload["dependencies"]["numpy"], "2.4.6")
        self.assertEqual(payload["hits"][0]["document_id"], "alpha:refund:v1")
        self.assertEqual(
            payload["retriever_batch_document_ids"],
            [["alpha:refund:v1"], ["alpha:security:v2"]],
        )

    def test_cli_rejects_out_of_vocabulary_query(self) -> None:
        script = Path(__file__).with_name("in_memory_retrieval.py")
        completed = subprocess.run(
            [sys.executable, "-B", str(script), "--query", "weather forecast"],
            check=False,
            capture_output=True,
            encoding="utf-8",
            timeout=30,
        )
        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stderr)
        self.assertEqual(payload["status"], "invalid")
        self.assertIn("teaching vocabulary", payload["error"])


if __name__ == "__main__":
    unittest.main()


