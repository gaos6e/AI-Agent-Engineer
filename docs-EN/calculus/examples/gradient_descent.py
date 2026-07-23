"""Implement linear-regression gradient checking and full-batch gradient descent with the standard library."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import fmean
from typing import Sequence


XS = (-2.0, -1.0, 0.0, 1.0, 2.0)
YS = (-3.0, -1.0, 1.0, 3.0, 5.0)


@dataclass(frozen=True)
class TrainingResult:
    observations: int
    steps: int
    learning_rate: float
    weight: float
    bias: float
    initial_loss: float
    final_loss: float
    gradient_error: float


def _finite_numbers(name: str, values: Sequence[float]) -> list[float]:
    try:
        raw_values = list(values)
    except TypeError:
        raise ValueError(f"{name} must be a numeric sequence") from None

    numbers: list[float] = []
    for index, value in enumerate(raw_values, start=1):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name}[{index}] must be a finite real number")
        number = float(value)
        if not isfinite(number):
            raise ValueError(f"{name}[{index}] must be a finite real number")
        numbers.append(number)
    return numbers


def _validated_data(
    xs: Sequence[float], ys: Sequence[float]
) -> tuple[list[float], list[float]]:
    x_values = _finite_numbers("xs", xs)
    y_values = _finite_numbers("ys", ys)
    if len(x_values) != len(y_values) or len(x_values) < 2:
        raise ValueError("xs and ys must have equal length and contain at least two points")
    if min(x_values) == max(x_values):
        raise ValueError("all x values are identical; slope is not identifiable")
    return x_values, y_values


def _mse(
    xs: Sequence[float],
    ys: Sequence[float],
    weight: float,
    bias: float,
) -> float:
    return fmean(
        (weight * x + bias - y) ** 2 for x, y in zip(xs, ys)
    )


def _gradient(
    xs: Sequence[float],
    ys: Sequence[float],
    weight: float,
    bias: float,
) -> tuple[float, float]:
    errors = [weight * x + bias - y for x, y in zip(xs, ys)]
    d_weight = 2.0 * fmean(
        error * x for error, x in zip(errors, xs)
    )
    d_bias = 2.0 * fmean(errors)
    return d_weight, d_bias


def loss(
    xs: Sequence[float],
    ys: Sequence[float],
    weight: float,
    bias: float,
) -> float:
    """Return mean squared error after validating data and parameters."""

    x_values, y_values = _validated_data(xs, ys)
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        for value in (weight, bias)
    ):
        raise ValueError("weight/bias must be finite numbers")
    return _mse(x_values, y_values, weight, bias)


def gradient(
    xs: Sequence[float],
    ys: Sequence[float],
    weight: float,
    bias: float,
) -> tuple[float, float]:
    """Return analytical gradients of MSE with respect to weight and bias."""

    x_values, y_values = _validated_data(xs, ys)
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        for value in (weight, bias)
    ):
        raise ValueError("weight/bias must be finite numbers")
    return _gradient(x_values, y_values, weight, bias)


def finite_difference(
    xs: Sequence[float],
    ys: Sequence[float],
    weight: float,
    bias: float,
    *,
    step: float = 1e-6,
) -> tuple[float, float]:
    """Approximate both parameter derivatives with centered differences."""

    x_values, y_values = _validated_data(xs, ys)
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        for value in (weight, bias)
    ):
        raise ValueError("weight/bias must be finite numbers")
    if (
        isinstance(step, bool)
        or not isinstance(step, (int, float))
        or not isfinite(step)
        or step <= 0.0
    ):
        raise ValueError("step must be a positive finite number")

    d_weight = (
        _mse(x_values, y_values, weight + step, bias)
        - _mse(x_values, y_values, weight - step, bias)
    ) / (2.0 * step)
    d_bias = (
        _mse(x_values, y_values, weight, bias + step)
        - _mse(x_values, y_values, weight, bias - step)
    ) / (2.0 * step)
    return d_weight, d_bias


def train(
    xs: Sequence[float],
    ys: Sequence[float],
    *,
    learning_rate: float = 0.05,
    steps: int = 2_000,
    initial_weight: float = 0.0,
    initial_bias: float = 0.0,
    difference_step: float = 1e-6,
    gradient_tolerance: float = 1e-6,
) -> TrainingResult:
    """Validate the initial gradient, then run full-batch gradient descent."""

    x_values, y_values = _validated_data(xs, ys)
    if (
        isinstance(learning_rate, bool)
        or not isinstance(learning_rate, (int, float))
        or not isfinite(learning_rate)
        or learning_rate <= 0.0
    ):
        raise ValueError("learning_rate must be a positive finite number")
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        raise ValueError("steps must be a positive integer")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        for value in (initial_weight, initial_bias)
    ):
        raise ValueError("initial parameters must be finite numbers")
    if (
        isinstance(gradient_tolerance, bool)
        or not isinstance(gradient_tolerance, (int, float))
        or not isfinite(gradient_tolerance)
        or gradient_tolerance <= 0.0
    ):
        raise ValueError("gradient_tolerance must be a positive finite number")

    analytical = _gradient(
        x_values, y_values, initial_weight, initial_bias
    )
    numerical = finite_difference(
        x_values,
        y_values,
        initial_weight,
        initial_bias,
        step=difference_step,
    )
    gradient_error = max(
        abs(exact - estimate)
        for exact, estimate in zip(analytical, numerical)
    )
    if gradient_error > gradient_tolerance:
        raise RuntimeError(
            "analytical gradient failed the finite-difference check: "
            f"error={gradient_error:.3e}"
        )

    weight = float(initial_weight)
    bias = float(initial_bias)
    initial_loss = _mse(x_values, y_values, weight, bias)
    divergence_limit = max(1.0, initial_loss) * 1e12

    for _ in range(steps):
        d_weight, d_bias = _gradient(x_values, y_values, weight, bias)
        weight -= learning_rate * d_weight
        bias -= learning_rate * d_bias
        current_loss = _mse(x_values, y_values, weight, bias)
        if not all(isfinite(value) for value in (weight, bias, current_loss)):
            raise RuntimeError("training produced a non-finite value and may have diverged")
        if current_loss > divergence_limit:
            raise RuntimeError("loss grew sharply relative to initial loss; training diverged")

    return TrainingResult(
        observations=len(x_values),
        steps=steps,
        learning_rate=float(learning_rate),
        weight=weight,
        bias=bias,
        initial_loss=initial_loss,
        final_loss=_mse(x_values, y_values, weight, bias),
        gradient_error=gradient_error,
    )


def main() -> int:
    result = train(XS, YS)
    print(
        f"observations={result.observations} steps={result.steps} "
        f"learning_rate={result.learning_rate:.6f}"
    )
    print(
        f"initial-loss={result.initial_loss:.12f} "
        f"final-loss={result.final_loss:.12f}"
    )
    print(f"weight={result.weight:.6f} bias={result.bias:.6f}")
    print(f"gradient-check-max-abs-error={result.gradient_error:.3e}")

    if abs(result.weight - 2.0) > 1e-6:
        raise RuntimeError("weight did not converge to the expected value")
    if abs(result.bias - 1.0) > 1e-6:
        raise RuntimeError("bias did not converge to the expected value")
    if result.final_loss > 1e-12:
        raise RuntimeError("final loss did not meet the project threshold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


