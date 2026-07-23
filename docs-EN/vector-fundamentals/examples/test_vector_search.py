"""Regression tests for the standard-library vector-retrieval project."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from math import inf, nan
import unittest

from vector_search import (
    cosine,
    dot,
    euclidean,
    main,
    norm,
    normalize,
    recall_at_k,
    top_k,
)


class VectorSearchTests(unittest.TestCase):
    def test_dot_norm_and_normalize_known_values(self) -> None:
        self.assertEqual(dot((1, -2, 2), (2, 1, 0)), 0.0)
        self.assertEqual(norm((3, 4)), 5.0)
        self.assertEqual(normalize((3, 4)), (0.6, 0.8))
        self.assertAlmostEqual(norm(normalize((1, -2, 2))), 1.0)

    def test_cosine_and_euclidean_known_values(self) -> None:
        self.assertAlmostEqual(cosine((1, 1), (2, 2)), 1.0)
        self.assertAlmostEqual(cosine((1, 0), (-1, 0)), -1.0)
        self.assertAlmostEqual(euclidean((0, 0), (3, 4)), 5.0)

    def test_metric_choice_can_change_ranking(self) -> None:
        query = (1.0, 1.0)
        documents = {
            "same-direction": (2.0, 2.0),
            "large-norm": (10.0, 0.0),
        }
        cosine_ids = [
            item[0]
            for item in top_k(query, documents, k=2, metric="cosine")
        ]
        dot_ids = [
            item[0]
            for item in top_k(query, documents, k=2, metric="dot")
        ]
        self.assertEqual(cosine_ids, ["same-direction", "large-norm"])
        self.assertEqual(dot_ids, ["large-norm", "same-direction"])

    def test_normalized_dot_and_cosine_rankings_match(self) -> None:
        query = normalize((1.0, 2.0, 0.0))
        documents = {
            "a": normalize((2.0, 1.0, 0.0)),
            "b": normalize((1.0, 3.0, 1.0)),
            "c": normalize((-1.0, 0.0, 1.0)),
        }
        cosine_ids = [
            item[0]
            for item in top_k(query, documents, k=3, metric="cosine")
        ]
        dot_ids = [
            item[0]
            for item in top_k(query, documents, k=3, metric="dot")
        ]
        self.assertEqual(cosine_ids, dot_ids)

    def test_euclidean_sorts_ascending_and_ties_by_id(self) -> None:
        results = top_k(
            (1.0, 0.0),
            {"b": (1.0, 0.0), "a": (1.0, 0.0), "far": (4.0, 0.0)},
            k=3,
            metric="euclidean",
        )
        self.assertEqual([item[0] for item in results], ["a", "b", "far"])

    def test_recall_at_k_uses_external_relevance_labels(self) -> None:
        results = [("a", 0.9), ("b", 0.8)]
        self.assertEqual(recall_at_k(results, {"a", "c"}), 0.5)
        with self.assertRaises(ValueError):
            recall_at_k([("a", 1.0), ("a", 0.5)], {"a"})

    def test_invalid_vectors_are_rejected(self) -> None:
        invalid_vectors = ((), (True,), ("1",), (nan,), (inf,))
        for vector in invalid_vectors:
            with self.subTest(vector=vector):
                with self.assertRaises(ValueError):
                    norm(vector)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            dot((1.0,), (1.0, 2.0))
        with self.assertRaises(ValueError):
            normalize((0.0, 0.0))
        with self.assertRaises(ValueError):
            cosine((0.0, 0.0), (1.0, 0.0))

    def test_invalid_search_controls_are_rejected(self) -> None:
        documents = {"doc": (1.0, 0.0)}
        invalid_k = (0, -1, True, 1.5, "1")
        for k in invalid_k:
            with self.subTest(k=k):
                with self.assertRaises(ValueError):
                    top_k((1.0, 0.0), documents, k=k)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            top_k((1.0, 0.0), {}, k=1)
        with self.assertRaises(ValueError):
            top_k((1.0, 0.0), {"doc": (1.0,)}, k=1)
        with self.assertRaises(ValueError):
            top_k((1.0, 0.0), {"": (1.0, 0.0)}, k=1)
        with self.assertRaises(ValueError):
            top_k((1.0, 0.0), documents, k=1, metric="unknown")  # type: ignore[arg-type]

    def test_main_is_successful_and_auditable(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(), 0)
        text = output.getvalue()
        self.assertIn("cosine top-2:", text)
        self.assertIn("euclidean top-2:", text)
        self.assertIn("Recall@2=1.000", text)


if __name__ == "__main__":
    unittest.main()
