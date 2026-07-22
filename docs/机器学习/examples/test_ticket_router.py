"""Regression tests for the offline ticket-routing learning project."""

from __future__ import annotations

from collections import Counter
from contextlib import redirect_stdout
from io import StringIO
import unittest
import warnings

from ticket_router import (
    SAMPLES,
    build_model,
    evaluate,
    main,
    split_dataset,
    validate_samples,
)


class TicketRouterTests(unittest.TestCase):
    def test_teaching_samples_are_unique_and_balanced(self) -> None:
        rows = validate_samples(SAMPLES)
        counts = Counter(label for _, label in rows)
        self.assertEqual(counts, {"账号": 8, "退款": 8, "技术": 8})
        self.assertEqual(len({text for text, _ in rows}), len(rows))

    def test_split_is_deterministic_disjoint_and_stratified(self) -> None:
        first = split_dataset(SAMPLES)
        second = split_dataset(SAMPLES)
        self.assertEqual(first, second)
        self.assertEqual(len(first.train_texts), 18)
        self.assertEqual(len(first.test_texts), 6)
        self.assertTrue(set(first.train_texts).isdisjoint(first.test_texts))
        self.assertEqual(Counter(first.test_labels), {"账号": 2, "退款": 2, "技术": 2})

    def test_pipeline_keeps_vectorizer_and_classifier_together(self) -> None:
        model = build_model()
        self.assertEqual([name for name, _ in model.steps], ["tfidf", "classifier"])
        self.assertEqual(model.named_steps["tfidf"].ngram_range, (2, 4))
        self.assertEqual(model.named_steps["classifier"].max_iter, 1_000)

    def test_evaluation_returns_bounded_metrics_and_shapes(self) -> None:
        result = evaluate()
        self.assertEqual(result.labels, ("技术", "账号", "退款"))
        self.assertTrue(0.0 <= result.baseline_accuracy <= 1.0)
        self.assertTrue(0.0 <= result.accuracy <= 1.0)
        self.assertTrue(0.0 <= result.macro_f1 <= 1.0)
        self.assertEqual(len(result.confusion), 3)
        self.assertTrue(all(len(row) == 3 for row in result.confusion))
        self.assertEqual(sum(sum(row) for row in result.confusion), 6)

    def test_report_and_errors_are_auditable(self) -> None:
        result = evaluate()
        self.assertIn("macro avg", result.report_text)
        for label in result.labels:
            self.assertIn(label, result.report_text)
        for error in result.errors:
            self.assertNotEqual(error.expected, error.predicted)
            self.assertTrue(0.0 <= error.confidence <= 1.0)

    def test_evaluation_is_reproducible(self) -> None:
        first = evaluate()
        second = evaluate()
        self.assertEqual(first, second)

    def test_evaluation_emits_no_warnings(self) -> None:
        # The locked 1.9 API does not need an explicit penalty/l1_ratio setting;
        # reject any new warnings in the local compatibility check as well.
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            evaluate()

    def test_invalid_samples_are_rejected(self) -> None:
        invalid_cases = (
            [],
            [("", "账号"), ("a", "账号"), ("b", "退款"), ("c", "退款")],
            [("same", "账号")] * 8,
            [("a", "账号"), ("b", "账号"), ("c", "账号"), ("d", "账号")],
            [("a", "账号"), ("b", "账号"), ("c", "账号"), ("d", "账号"), ("e", "退款")],
            [(1, "账号")],
            [("text",)],
        )
        for rows in invalid_cases:
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):
                    validate_samples(rows)  # type: ignore[arg-type]

    def test_invalid_split_controls_are_rejected(self) -> None:
        invalid_arguments = (
            {"test_size": 0.0},
            {"test_size": 1.0},
            {"test_size": True},
            {"test_size": "0.25"},
            {"test_size": 24},
            {"random_state": True},
            {"random_state": "42"},
            {"random_state": -1},
            {"random_state": 2**32},
        )
        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                with self.assertRaises(ValueError):
                    split_dataset(SAMPLES, **arguments)  # type: ignore[arg-type]

    def test_main_returns_success_and_reports_version(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(), 0)
        self.assertIn("scikit-learn=", output.getvalue())
        self.assertIn("baseline-accuracy=", output.getvalue())
        self.assertIn("macro-f1=", output.getvalue())


if __name__ == "__main__":
    unittest.main()
