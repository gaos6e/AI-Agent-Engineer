"""Regression tests for the standard-library least-squares example."""

from __future__ import annotations

import math
import unittest

from least_squares import fit_line


class FitLineTests(unittest.TestCase):
    def test_exact_line_is_recovered(self) -> None:
        result = fit_line([0, 1, 2, 3], [-1, 1, 3, 5])
        self.assertAlmostEqual(result.weight, 2.0)
        self.assertAlmostEqual(result.bias, -1.0)
        self.assertAlmostEqual(result.mse, 0.0)

    def test_two_distinct_points_define_a_line(self) -> None:
        result = fit_line([2, 5], [7, 16])
        self.assertAlmostEqual(result.weight, 3.0)
        self.assertAlmostEqual(result.bias, 1.0)

    def test_noisy_fixture_satisfies_orthogonality(self) -> None:
        result = fit_line(
            [1.0, 2.0, 3.0, 4.0, 5.0],
            [2.1, 4.0, 6.2, 7.9, 10.1],
        )
        self.assertEqual(result.observations, 5)
        self.assertGreater(result.mse, 0.0)
        self.assertLess(abs(result.residual_sum), 1e-10)
        self.assertLess(abs(result.centered_residual_dot), 1e-10)

    def test_row_order_does_not_change_the_fit(self) -> None:
        forward = fit_line([1, 2, 3, 4], [3, 5, 8, 9])
        reverse = fit_line([4, 3, 2, 1], [9, 8, 5, 3])
        self.assertAlmostEqual(forward.weight, reverse.weight)
        self.assertAlmostEqual(forward.bias, reverse.bias)
        self.assertAlmostEqual(forward.mse, reverse.mse)

    def test_large_coordinate_offset_remains_finite(self) -> None:
        result = fit_line(
            [1_000_000_000, 1_000_000_001, 1_000_000_002],
            [2, 5, 8],
        )
        self.assertAlmostEqual(result.weight, 3.0)
        self.assertTrue(math.isfinite(result.bias))
        self.assertAlmostEqual(result.mse, 0.0)

    def test_constant_x_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            fit_line([2, 2, 2], [1, 2, 3])

    def test_length_and_minimum_size_are_checked(self) -> None:
        for xs, ys in (([], []), ([1], [2]), ([1, 2], [3])):
            with self.subTest(xs=xs, ys=ys):
                with self.assertRaises(ValueError):
                    fit_line(xs, ys)

    def test_nonfinite_nonnumeric_and_boolean_values_are_rejected(self) -> None:
        invalid_cases = (
            ([1, math.nan], [1, 2]),
            ([1, math.inf], [1, 2]),
            ([1, True], [1, 2]),
            ([1, "2"], [1, 2]),
            ([1, 2], [1, None]),
        )
        for xs, ys in invalid_cases:
            with self.subTest(xs=xs, ys=ys):
                with self.assertRaises(ValueError):
                    fit_line(xs, ys)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
