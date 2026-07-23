"""Regression tests for the gradient-descent calculus example."""

from __future__ import annotations

import math
import unittest

from gradient_descent import XS, YS, finite_difference, gradient, loss, train


class GradientDescentTests(unittest.TestCase):
    def test_initial_loss_and_analytical_gradient(self) -> None:
        self.assertAlmostEqual(loss(XS, YS, 0.0, 0.0), 9.0)
        self.assertEqual(gradient(XS, YS, 0.0, 0.0), (-8.0, -2.0))

    def test_centered_difference_matches_analytical_gradient(self) -> None:
        analytical = gradient(XS, YS, 0.25, -0.5)
        numerical = finite_difference(XS, YS, 0.25, -0.5)
        for exact, estimate in zip(analytical, numerical):
            self.assertAlmostEqual(exact, estimate, places=6)

    def test_exact_line_converges(self) -> None:
        result = train(XS, YS)
        self.assertAlmostEqual(result.weight, 2.0, places=6)
        self.assertAlmostEqual(result.bias, 1.0, places=6)
        self.assertLess(result.final_loss, 1e-12)
        self.assertLess(result.gradient_error, 1e-6)

    def test_row_order_does_not_change_training_result(self) -> None:
        forward = train(XS, YS, steps=500)
        reverse = train(tuple(reversed(XS)), tuple(reversed(YS)), steps=500)
        self.assertAlmostEqual(forward.weight, reverse.weight)
        self.assertAlmostEqual(forward.bias, reverse.bias)
        self.assertAlmostEqual(forward.final_loss, reverse.final_loss)

    def test_constant_x_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            train([1, 1, 1], [0, 1, 2])

    def test_length_and_minimum_size_are_checked(self) -> None:
        for xs, ys in (([], []), ([1], [2]), ([1, 2], [3])):
            with self.subTest(xs=xs, ys=ys):
                with self.assertRaises(ValueError):
                    train(xs, ys)

    def test_invalid_data_are_rejected(self) -> None:
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
                    train(xs, ys)  # type: ignore[arg-type]

    def test_invalid_controls_are_rejected(self) -> None:
        invalid_arguments = (
            {"learning_rate": 0.0},
            {"learning_rate": math.nan},
            {"learning_rate": True},
            {"steps": 0},
            {"steps": True},
            {"initial_weight": math.inf},
            {"difference_step": 0.0},
            {"difference_step": "1e-6"},
            {"gradient_tolerance": 0.0},
            {"gradient_tolerance": "1e-6"},
        )
        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                with self.assertRaises(ValueError):
                    train(XS, YS, **arguments)  # type: ignore[arg-type]

    def test_excessive_learning_rate_is_reported_as_divergence(self) -> None:
        with self.assertRaises(RuntimeError):
            train(XS, YS, learning_rate=1.0, steps=100)


if __name__ == "__main__":
    unittest.main()


