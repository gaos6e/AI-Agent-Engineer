"""用标准库拟合 y = w*x + b，并验证最小二乘正交条件。"""

from __future__ import annotations

from dataclasses import dataclass
from math import fsum, isfinite
from statistics import fmean
from typing import Sequence


@dataclass(frozen=True)
class LineFit:
    observations: int
    weight: float
    bias: float
    mse: float
    residual_sum: float
    centered_residual_dot: float


def _finite_numbers(name: str, values: Sequence[float]) -> list[float]:
    try:
        raw_values = list(values)
    except TypeError:
        raise ValueError(f"{name} 必须是数值序列") from None

    numbers: list[float] = []
    for index, value in enumerate(raw_values, start=1):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name}[{index}] 必须是有限实数")
        number = float(value)
        if not isfinite(number):
            raise ValueError(f"{name}[{index}] 必须是有限实数")
        numbers.append(number)
    return numbers


def fit_line(xs: Sequence[float], ys: Sequence[float]) -> LineFit:
    """Return the ordinary-least-squares line and residual diagnostics."""

    x_values = _finite_numbers("xs", xs)
    y_values = _finite_numbers("ys", ys)
    if len(x_values) != len(y_values) or len(x_values) < 2:
        raise ValueError("xs/ys 必须等长且至少包含两个点")

    x_mean = fmean(x_values)
    y_mean = fmean(y_values)
    centered_x = [x - x_mean for x in x_values]
    denominator = fsum(value * value for value in centered_x)
    if denominator == 0:
        raise ValueError("所有 x 相同，无法识别斜率")

    numerator = fsum(
        x_offset * (y - y_mean)
        for x_offset, y in zip(centered_x, y_values)
    )
    weight = numerator / denominator
    bias = y_mean - weight * x_mean
    predictions = [weight * x + bias for x in x_values]
    residuals = [
        y - prediction for y, prediction in zip(y_values, predictions)
    ]

    return LineFit(
        observations=len(x_values),
        weight=weight,
        bias=bias,
        mse=fmean(residual * residual for residual in residuals),
        residual_sum=fsum(residuals),
        centered_residual_dot=fsum(
            x_offset * residual
            for x_offset, residual in zip(centered_x, residuals)
        ),
    )


def main() -> int:
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [2.1, 4.0, 6.2, 7.9, 10.1]
    result = fit_line(xs, ys)

    print(f"observations={result.observations}")
    print(
        f"weight={result.weight:.6f} "
        f"bias={result.bias:.6f} mse={result.mse:.6f}"
    )
    print(f"residual-sum={result.residual_sum:.12f}")
    print(
        "centered-x-dot-residuals="
        f"{result.centered_residual_dot:.12f}"
    )

    tolerance = 1e-10
    if abs(result.residual_sum) > tolerance:
        raise RuntimeError("残差和未通过正交检查")
    if abs(result.centered_residual_dot) > tolerance:
        raise RuntimeError("中心化 x 与残差未通过正交检查")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
