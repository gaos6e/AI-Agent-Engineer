"""Regression tests for the paired Agent-evaluation bootstrap example."""

from __future__ import annotations

import math
import unittest

from bootstrap_eval import PAIRED_SCORES, linear_quantile, paired_bootstrap


class LinearQuantileTests(unittest.TestCase):
    def test_endpoints_and_interpolation(self) -> None:
        values = [10.0, 0.0]
        self.assertEqual(linear_quantile(values, 0.0), 0.0)
        self.assertEqual(linear_quantile(values, 1.0), 10.0)
        self.assertEqual(linear_quantile(values, 0.25), 2.5)

    def test_invalid_quantile_inputs_are_rejected(self) -> None:
        for probability in (-0.1, 1.1, math.nan, True, "0.5"):
            with self.subTest(probability=probability):
                with self.assertRaises(ValueError):
                    linear_quantile([0.0, 1.0], probability)
        with self.assertRaises(ValueError):
            linear_quantile([], 0.5)
        with self.assertRaises(ValueError):
            linear_quantile([0.0, math.inf], 0.5)


class PairedBootstrapTests(unittest.TestCase):
    def test_all_ties_produce_zero_width_zero_interval(self) -> None:
        result = paired_bootstrap([(0, 0), (1, 1), (0, 0)], repeats=1_000)
        self.assertEqual(result.difference, 0.0)
        self.assertEqual((result.lower, result.upper), (0.0, 0.0))

    def test_all_b_wins_produce_unit_interval(self) -> None:
        result = paired_bootstrap([(0, 1)] * 4, repeats=1_000)
        self.assertEqual(result.difference, 1.0)
        self.assertEqual((result.lower, result.upper), (1.0, 1.0))

    def test_fixed_fixture_is_reproducible_and_keeps_direction(self) -> None:
        first = paired_bootstrap(PAIRED_SCORES, repeats=2_000, seed=42)
        second = paired_bootstrap(PAIRED_SCORES, repeats=2_000, seed=42)
        self.assertEqual(first, second)
        self.assertEqual(first.tasks, 12)
        self.assertAlmostEqual(first.a_mean, 7 / 12)
        self.assertAlmostEqual(first.b_mean, 10 / 12)
        self.assertAlmostEqual(first.difference, 3 / 12)
        self.assertLessEqual(first.lower, first.difference)
        self.assertGreaterEqual(first.upper, first.difference)

    def test_seed_does_not_change_observed_statistics(self) -> None:
        first = paired_bootstrap(PAIRED_SCORES, repeats=1_000, seed=1)
        second = paired_bootstrap(PAIRED_SCORES, repeats=1_000, seed=2)
        self.assertEqual(first.a_mean, second.a_mean)
        self.assertEqual(first.b_mean, second.b_mean)
        self.assertEqual(first.difference, second.difference)
        self.assertTrue(-1.0 <= first.lower <= first.upper <= 1.0)
        self.assertTrue(-1.0 <= second.lower <= second.upper <= 1.0)

    def test_invalid_pairs_are_rejected(self) -> None:
        invalid_cases = (
            [],
            [(0.5, 1.0)],
            [(0.0, math.inf)],
            [(True, 1.0)],
            [("0", 1.0)],
            [(0.0, 1.0, 0.0)],
            [None],
        )
        for pairs in invalid_cases:
            with self.subTest(pairs=pairs):
                with self.assertRaises(ValueError):
                    paired_bootstrap(pairs, repeats=1_000)  # type: ignore[arg-type]

    def test_invalid_controls_are_rejected(self) -> None:
        invalid_arguments = (
            {"repeats": 999},
            {"repeats": True},
            {"confidence": 0.0},
            {"confidence": 1.0},
            {"confidence": math.nan},
            {"confidence": "0.95"},
            {"seed": True},
        )
        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                with self.assertRaises(ValueError):
                    paired_bootstrap(PAIRED_SCORES, **arguments)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()

