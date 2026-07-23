"""用标准库进行配对 percentile bootstrap，演示 Agent A/B 评测不确定性。"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from random import Random
from statistics import fmean
from typing import Sequence


ScorePair = tuple[float, float]

PAIRED_SCORES: tuple[ScorePair, ...] = (
    (1, 1),
    (0, 1),
    (1, 1),
    (0, 0),
    (1, 1),
    (0, 1),
    (1, 1),
    (1, 1),
    (0, 1),
    (1, 0),
    (0, 1),
    (1, 1),
)


@dataclass(frozen=True)
class BootstrapResult:
    tasks: int
    a_mean: float
    b_mean: float
    difference: float
    lower: float
    upper: float
    confidence: float
    repeats: int
    seed: int


def linear_quantile(values: Sequence[float], probability: float) -> float:
    """Return an R7-style linearly interpolated sample quantile."""

    if not values:
        raise ValueError("values 不能为空")
    if (
        isinstance(probability, bool)
        or not isinstance(probability, (int, float))
        or not isfinite(probability)
        or not 0.0 <= probability <= 1.0
    ):
        raise ValueError("probability 必须是 [0, 1] 内的有限数")

    ordered = sorted(float(value) for value in values)
    if not all(isfinite(value) for value in ordered):
        raise ValueError("values 必须全部有限")

    position = (len(ordered) - 1) * probability
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = position - lower_index
    return (
        ordered[lower_index] * (1.0 - fraction)
        + ordered[upper_index] * fraction
    )


def _validate_pairs(pairs: Sequence[ScorePair]) -> None:
    if not pairs:
        raise ValueError("pairs 不能为空")
    for index, pair in enumerate(pairs, start=1):
        try:
            pair_size = len(pair)
        except TypeError:
            raise ValueError(f"pair {index} 必须是 A/B 得分序列") from None
        if pair_size != 2:
            raise ValueError(f"pair {index} 必须恰好包含 A/B 两个得分")
        a_score, b_score = pair
        if (
            isinstance(a_score, bool)
            or isinstance(b_score, bool)
            or not isinstance(a_score, (int, float))
            or not isinstance(b_score, (int, float))
        ):
            raise ValueError(f"pair {index} 的得分必须是数值 0 或 1")
        if not isfinite(a_score) or not isfinite(b_score):
            raise ValueError(f"pair {index} 的得分必须有限")
        if a_score not in (0, 1) or b_score not in (0, 1):
            raise ValueError(f"pair {index} 的二元得分必须是 0 或 1")


def paired_bootstrap(
    pairs: Sequence[ScorePair],
    *,
    repeats: int = 10_000,
    confidence: float = 0.95,
    seed: int = 20260714,
) -> BootstrapResult:
    """Estimate B-A and a paired percentile-bootstrap interval over tasks."""

    _validate_pairs(pairs)
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1_000:
        raise ValueError("repeats 必须是至少 1000 的整数")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not isfinite(confidence)
        or not 0.0 < confidence < 1.0
    ):
        raise ValueError("confidence 必须是 (0, 1) 内的有限数")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed 必须是整数")

    differences = [b_score - a_score for a_score, b_score in pairs]
    rng = Random(seed)
    bootstrap_estimates = [
        fmean(rng.choice(differences) for _ in differences)
        for _ in range(repeats)
    ]
    alpha = 1.0 - confidence

    return BootstrapResult(
        tasks=len(pairs),
        a_mean=fmean(a_score for a_score, _ in pairs),
        b_mean=fmean(b_score for _, b_score in pairs),
        difference=fmean(differences),
        lower=linear_quantile(bootstrap_estimates, alpha / 2.0),
        upper=linear_quantile(bootstrap_estimates, 1.0 - alpha / 2.0),
        confidence=confidence,
        repeats=repeats,
        seed=seed,
    )


def main() -> int:
    result = paired_bootstrap(PAIRED_SCORES)
    print("method=paired-percentile-bootstrap")
    print(f"tasks={result.tasks} repeats={result.repeats} seed={result.seed}")
    print(f"A mean={result.a_mean:.3f}")
    print(f"B mean={result.b_mean:.3f}")
    print(f"B-A={result.difference:.3f}")
    print(
        f"confidence={result.confidence:.3f} "
        f"interval=[{result.lower:.3f}, {result.upper:.3f}]"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
