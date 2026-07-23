"""Render an offline Agent evaluation dashboard from strict synthetic JSON data."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.ticker import PercentFormatter  # noqa: E402


DEFAULT_DATA = Path(__file__).with_name("sample_agent_eval.json")
SUPPORTED_OUTPUT_SUFFIXES = {".png", ".svg"}
OKABE_ITO = ("#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9")
MARKERS = ("o", "s", "^", "D", "P")
Z_95 = 1.959963984540054


@dataclass(frozen=True)
class VersionMetrics:
    """Aggregated metrics for one evaluated system version."""

    name: str
    success_count: int
    task_count: int
    timeout_count: int
    p50_latency_ms: float
    p95_latency_ms: float
    mean_cost_usd: float

    @property
    def success_rate(self) -> float:
        return self.success_count / self.task_count

    @property
    def timeout_rate(self) -> float:
        return self.timeout_count / self.task_count


@dataclass(frozen=True)
class RoutingConfusion:
    """Routing confusion matrix for one version; rows are true labels."""

    version: str
    labels: tuple[str, ...]
    matrix: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class EvaluationDataset:
    """Validated dashboard input."""

    dataset_version: str
    note: str
    versions: tuple[VersionMetrics, ...]
    routing: RoutingConfusion


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a JSON object")
    return value


def _require_exact_fields(
    value: dict[str, Any], required: set[str], context: str
) -> None:
    missing = required - value.keys()
    unknown = value.keys() - required
    if missing or unknown:
        parts: list[str] = []
        if missing:
            parts.append(f"missing={sorted(missing)}")
        if unknown:
            parts.append(f"unknown={sorted(unknown)}")
        raise ValueError(f"{context} has invalid fields: {', '.join(parts)}")


def _require_text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-blank string")
    return value.strip()


def _require_int(value: Any, context: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{context} must be an integer >= {minimum}")
    return value


def _require_number(value: Any, context: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context} must be a number")
    number = float(value)
    if not math.isfinite(number) or number < minimum:
        raise ValueError(f"{context} must be finite and >= {minimum}")
    return number


def _parse_version(raw: Any, index: int) -> VersionMetrics:
    context = f"versions[{index}]"
    value = _require_object(raw, context)
    _require_exact_fields(
        value,
        {
            "name",
            "success_count",
            "task_count",
            "timeout_count",
            "p50_latency_ms",
            "p95_latency_ms",
            "mean_cost_usd",
        },
        context,
    )
    task_count = _require_int(value["task_count"], f"{context}.task_count", minimum=1)
    success_count = _require_int(value["success_count"], f"{context}.success_count")
    timeout_count = _require_int(value["timeout_count"], f"{context}.timeout_count")
    if success_count > task_count:
        raise ValueError(f"{context}.success_count cannot exceed task_count")
    if timeout_count > task_count:
        raise ValueError(f"{context}.timeout_count cannot exceed task_count")
    if success_count + timeout_count > task_count:
        raise ValueError(f"{context}: success_count and timeout_count overlap")
    completed_count = task_count - success_count - timeout_count
    if completed_count < 1:
        raise ValueError(
            f"{context}: at least one completed run is required for latency metrics"
        )
    p50 = _require_number(value["p50_latency_ms"], f"{context}.p50_latency_ms")
    p95 = _require_number(value["p95_latency_ms"], f"{context}.p95_latency_ms")
    if p95 < p50:
        raise ValueError(f"{context}.p95_latency_ms must be >= p50_latency_ms")
    return VersionMetrics(
        name=_require_text(value["name"], f"{context}.name"),
        success_count=success_count,
        task_count=task_count,
        timeout_count=timeout_count,
        p50_latency_ms=p50,
        p95_latency_ms=p95,
        mean_cost_usd=_require_number(
            value["mean_cost_usd"], f"{context}.mean_cost_usd"
        ),
    )


def _parse_routing(raw: Any, versions: tuple[VersionMetrics, ...]) -> RoutingConfusion:
    value = _require_object(raw, "routing")
    _require_exact_fields(value, {"version", "labels", "matrix"}, "routing")
    version = _require_text(value["version"], "routing.version")
    version_by_name = {metrics.name: metrics for metrics in versions}
    if version not in version_by_name:
        raise ValueError("routing.version must name one evaluated version")

    labels_raw = value["labels"]
    if not isinstance(labels_raw, list) or not 2 <= len(labels_raw) <= 10:
        raise ValueError("routing.labels must contain 2 to 10 labels")
    labels = tuple(
        _require_text(label, f"routing.labels[{index}]")
        for index, label in enumerate(labels_raw)
    )
    if len(set(labels)) != len(labels):
        raise ValueError("routing.labels must be unique")

    matrix_raw = value["matrix"]
    if not isinstance(matrix_raw, list) or len(matrix_raw) != len(labels):
        raise ValueError("routing.matrix must be square and match routing.labels")
    rows: list[tuple[int, ...]] = []
    for row_index, row_raw in enumerate(matrix_raw):
        if not isinstance(row_raw, list) or len(row_raw) != len(labels):
            raise ValueError("routing.matrix must be square and match routing.labels")
        row = tuple(
            _require_int(cell, f"routing.matrix[{row_index}][{column_index}]")
            for column_index, cell in enumerate(row_raw)
        )
        if sum(row) == 0:
            raise ValueError(f"routing.matrix row {row_index} has no observations")
        rows.append(row)
    if sum(sum(row) for row in rows) != version_by_name[version].task_count:
        raise ValueError("routing.matrix total must equal the selected version task_count")
    return RoutingConfusion(version=version, labels=labels, matrix=tuple(rows))


def load_dataset(path: Path) -> EvaluationDataset:
    """Load and strictly validate one dashboard JSON file."""
    if not path.is_file():
        raise ValueError(f"data file does not exist: {path}")
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(
            handle,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_constant,
        )
    value = _require_object(raw, "root")
    _require_exact_fields(
        value, {"dataset_version", "note", "versions", "routing"}, "root"
    )
    versions_raw = value["versions"]
    if not isinstance(versions_raw, list) or not 2 <= len(versions_raw) <= 5:
        raise ValueError("versions must contain 2 to 5 entries; split denser comparisons")
    versions = tuple(_parse_version(item, index) for index, item in enumerate(versions_raw))
    names = [metrics.name for metrics in versions]
    if len(set(names)) != len(names):
        raise ValueError("version names must be unique")
    return EvaluationDataset(
        dataset_version=_require_text(value["dataset_version"], "dataset_version"),
        note=_require_text(value["note"], "note"),
        versions=versions,
        routing=_parse_routing(value["routing"], versions),
    )


def wilson_interval(
    successes: int, total: int, *, z: float = Z_95
) -> tuple[float, float]:
    """Return a two-sided Wilson score interval for a binomial proportion."""
    successes = _require_int(successes, "successes")
    total = _require_int(total, "total", minimum=1)
    if successes > total:
        raise ValueError("successes cannot exceed total")
    if not math.isfinite(z) or z <= 0:
        raise ValueError("z must be finite and positive")
    proportion = successes / total
    z_squared = z * z
    denominator = 1.0 + z_squared / total
    center = (proportion + z_squared / (2.0 * total)) / denominator
    half_width = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z_squared / (4.0 * total * total)
        )
        / denominator
    )
    return max(0.0, center - half_width), min(1.0, center + half_width)


def pareto_versions(versions: Sequence[VersionMetrics]) -> tuple[str, ...]:
    """Return versions not dominated on lower cost and higher success rate."""
    if not versions:
        raise ValueError("at least one version is required")
    candidates: list[str] = []
    for current in versions:
        dominated = any(
            other is not current
            and other.mean_cost_usd <= current.mean_cost_usd
            and other.success_rate >= current.success_rate
            and (
                other.mean_cost_usd < current.mean_cost_usd
                or other.success_rate > current.success_rate
            )
            for other in versions
        )
        if not dominated:
            candidates.append(current.name)
    return tuple(candidates)


def build_dashboard(dataset: EvaluationDataset) -> Figure:
    """Build a four-panel dashboard at its final 11 x 7.4 inch size."""
    style = {
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
    with plt.rc_context(style):
        figure, axes = plt.subplots(
            2, 2, figsize=(11.0, 7.4), layout="constrained", facecolor="white"
        )
        success_ax, latency_ax, confusion_ax, tradeoff_ax = axes.ravel()

        rates = [metrics.success_rate for metrics in dataset.versions]
        intervals = [
            wilson_interval(metrics.success_count, metrics.task_count)
            for metrics in dataset.versions
        ]
        positions = list(range(len(dataset.versions)))

        for index, (metrics, rate, interval) in enumerate(
            zip(dataset.versions, rates, intervals)
        ):
            color = OKABE_ITO[index % len(OKABE_ITO)]
            marker = MARKERS[index % len(MARKERS)]
            success_ax.errorbar(
                index,
                rate,
                yerr=((rate - interval[0],), (interval[1] - rate,)),
                fmt=marker,
                color=color,
                ecolor=color,
                markeredgecolor="black",
                markeredgewidth=0.5,
                markersize=8,
                capsize=4,
                linewidth=1.2,
            )
            success_ax.text(
                index,
                min(0.98, interval[1] + 0.055),
                f"{rate:.1%}\nn={metrics.task_count}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
        success_ax.set_xticks(positions, [item.name for item in dataset.versions])
        success_ax.set_ylim(0.0, 1.0)
        success_ax.yaxis.set_major_formatter(PercentFormatter(1.0))
        success_ax.set_ylabel("End-to-end task success")
        success_ax.set_title("(a) Success rate with Wilson 95% CI", loc="left")
        success_ax.grid(axis="y", color="#D9D9D9", linewidth=0.6, alpha=0.7)

        max_p95 = max(metrics.p95_latency_ms for metrics in dataset.versions)
        for index, metrics in enumerate(dataset.versions):
            latency_ax.hlines(
                index,
                metrics.p50_latency_ms,
                metrics.p95_latency_ms,
                color="#7F7F7F",
                linewidth=1.4,
                zorder=1,
            )
            latency_ax.scatter(
                metrics.p50_latency_ms,
                index,
                marker="o",
                s=55,
                color=OKABE_ITO[0],
                edgecolor="black",
                linewidth=0.5,
                label="p50" if index == 0 else None,
                zorder=2,
            )
            latency_ax.scatter(
                metrics.p95_latency_ms,
                index,
                marker="^",
                s=65,
                color=OKABE_ITO[1],
                edgecolor="black",
                linewidth=0.5,
                label="p95" if index == 0 else None,
                zorder=2,
            )
            latency_ax.text(
                metrics.p95_latency_ms + max_p95 * 0.035,
                index,
                f"timeout {metrics.timeout_rate:.1%}",
                va="center",
                fontsize=8,
            )
        latency_ax.set_yticks(positions, [item.name for item in dataset.versions])
        latency_ax.set_xlim(0, max_p95 * 1.27)
        latency_ax.set_xlabel("Completed-run latency (ms)")
        latency_ax.set_title("(b) Tail latency and timeout rate", loc="left")
        latency_ax.legend(
            frameon=False,
            ncols=2,
            loc="lower right",
            bbox_to_anchor=(1.0, 1.0),
            borderaxespad=0.0,
        )
        latency_ax.grid(axis="x", color="#D9D9D9", linewidth=0.6, alpha=0.7)

        routing = dataset.routing
        row_totals = [sum(row) for row in routing.matrix]
        normalized = [
            [cell / row_total for cell in row]
            for row, row_total in zip(routing.matrix, row_totals)
        ]
        image = confusion_ax.pcolormesh(
            normalized,
            cmap="cividis",
            vmin=0.0,
            vmax=1.0,
            shading="flat",
            edgecolors="white",
            linewidth=0.8,
        )
        cell_centers = [index + 0.5 for index in range(len(routing.labels))]
        confusion_ax.set_xlim(0, len(routing.labels))
        confusion_ax.set_ylim(len(routing.labels), 0)
        confusion_ax.set_aspect("equal")
        confusion_ax.set_xticks(cell_centers, routing.labels, rotation=25, ha="right")
        confusion_ax.set_yticks(cell_centers, routing.labels)
        confusion_ax.set_xlabel("Predicted route")
        confusion_ax.set_ylabel("True route")
        confusion_ax.set_title(
            f"(c) {routing.version} routing confusion: count / row %", loc="left"
        )
        for row_index, (row, normalized_row) in enumerate(
            zip(routing.matrix, normalized)
        ):
            for column_index, (count, proportion) in enumerate(
                zip(row, normalized_row)
            ):
                red, green, blue, _ = image.cmap(image.norm(proportion))
                luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
                confusion_ax.text(
                    column_index + 0.5,
                    row_index + 0.5,
                    f"{count}\n{proportion:.0%}",
                    ha="center",
                    va="center",
                    color="black" if luminance > 0.55 else "white",
                    fontsize=8,
                )
        colorbar = figure.colorbar(image, ax=confusion_ax, fraction=0.046, pad=0.04)
        colorbar.set_label("Row proportion")
        colorbar.ax.yaxis.set_major_formatter(PercentFormatter(1.0))

        pareto = set(pareto_versions(dataset.versions))
        pareto_points = sorted(
            (
                metrics.mean_cost_usd,
                metrics.success_rate,
            )
            for metrics in dataset.versions
            if metrics.name in pareto
        )
        if len(pareto_points) > 1:
            tradeoff_ax.plot(
                [point[0] for point in pareto_points],
                [point[1] for point in pareto_points],
                color="#666666",
                linestyle="--",
                linewidth=1.0,
                zorder=1,
            )
        for index, (metrics, interval) in enumerate(zip(dataset.versions, intervals)):
            color = OKABE_ITO[index % len(OKABE_ITO)]
            marker = MARKERS[index % len(MARKERS)]
            tradeoff_ax.errorbar(
                metrics.mean_cost_usd,
                metrics.success_rate,
                yerr=(
                    (metrics.success_rate - interval[0],),
                    (interval[1] - metrics.success_rate,),
                ),
                fmt=marker,
                color=color,
                ecolor=color,
                markeredgecolor="black",
                markeredgewidth=0.5,
                markersize=8,
                capsize=3,
                linewidth=1.0,
                zorder=3,
            )
            if metrics.name in pareto:
                tradeoff_ax.scatter(
                    metrics.mean_cost_usd,
                    metrics.success_rate,
                    s=165,
                    facecolors="none",
                    edgecolors="black",
                    linewidths=1.0,
                    label="Pareto candidate" if metrics.name == sorted(pareto)[0] else None,
                    zorder=2,
                )
            tradeoff_ax.annotate(
                metrics.name,
                (metrics.mean_cost_usd, metrics.success_rate),
                xytext=(6, 6),
                textcoords="offset points",
                fontsize=8,
            )
        costs = [metrics.mean_cost_usd for metrics in dataset.versions]
        cost_padding = max(0.001, (max(costs) - min(costs)) * 0.2)
        tradeoff_ax.set_xlim(min(costs) - cost_padding, max(costs) + cost_padding * 1.6)
        tradeoff_ax.set_ylim(0.0, 1.0)
        tradeoff_ax.yaxis.set_major_formatter(PercentFormatter(1.0))
        tradeoff_ax.set_xlabel("Mean cost per task (synthetic USD)")
        tradeoff_ax.set_ylabel("End-to-end task success")
        tradeoff_ax.set_title("(d) Cost-success trade-off", loc="left")
        tradeoff_ax.legend(frameon=False, loc="lower right")
        tradeoff_ax.grid(color="#D9D9D9", linewidth=0.6, alpha=0.7)

        figure.suptitle(
            f"Offline Agent Evaluation - synthetic dataset {dataset.dataset_version}",
            fontsize=14,
            fontweight="bold",
        )
    return figure


def save_dashboard(figure: Figure, output: Path, *, dpi: int = 300) -> None:
    """Save one PNG or SVG; reject ambiguous or lossy formats."""
    if isinstance(dpi, bool) or not isinstance(dpi, int) or not 72 <= dpi <= 1200:
        raise ValueError("dpi must be an integer between 72 and 1200")
    suffix = output.suffix.lower()
    if suffix not in SUPPORTED_OUTPUT_SUFFIXES:
        raise ValueError("output suffix must be .png or .svg")
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "Title": "Offline Agent Evaluation - synthetic teaching example",
        "Creator": "agent_eval_dashboard.py",
    }
    # Keep the declared 11 x 7.4 inch canvas exact. ``layout="constrained"``
    # handles spacing; a tight bounding box would silently change final pixels.
    figure.savefig(output, dpi=dpi, metadata=metadata)


def build_alt_text(dataset: EvaluationDataset) -> str:
    """Create a concise text alternative from the same validated data."""
    best = max(dataset.versions, key=lambda item: item.success_rate)
    slowest_tail = max(dataset.versions, key=lambda item: item.p95_latency_ms)
    routing = dataset.routing
    off_diagonal = [
        (count, routing.labels[row_index], routing.labels[column_index])
        for row_index, row in enumerate(routing.matrix)
        for column_index, count in enumerate(row)
        if row_index != column_index
    ]
    largest_conflict = max(off_diagonal, key=lambda item: item[0])
    pareto = ", ".join(pareto_versions(dataset.versions))
    return (
        "Four-panel dashboard from synthetic evaluation data. "
        f"{best.name} has the highest end-to-end success rate "
        f"({best.success_count}/{best.task_count}, {best.success_rate:.1%}). "
        f"{slowest_tail.name} has the largest completed-run p95 latency "
        f"({slowest_tail.p95_latency_ms:.0f} ms) and a "
        f"{slowest_tail.timeout_rate:.1%} timeout rate. "
        f"The largest off-diagonal {routing.version} routing confusion is "
        f"true {largest_conflict[1]} predicted as {largest_conflict[2]} "
        f"({largest_conflict[0]} tasks). "
        f"Cost-success Pareto candidates are {pareto}. "
        "Success intervals are Wilson 95% confidence intervals; routing cells show "
        "counts and row percentages."
    )


def write_alt_text(dataset: EvaluationDataset, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_alt_text(dataset) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a reproducible dashboard from strict synthetic JSON data."
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument(
        "--output",
        action="append",
        required=True,
        type=Path,
        help="Repeat for PNG and SVG outputs.",
    )
    parser.add_argument("--alt-output", type=Path)
    parser.add_argument("--dpi", type=int, default=300)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dataset = load_dataset(args.data)
    outputs = [path.resolve() for path in args.output]
    if len(set(outputs)) != len(outputs):
        raise ValueError("output paths must be unique")
    figure = build_dashboard(dataset)
    try:
        for output in outputs:
            save_dashboard(figure, output, dpi=args.dpi)
    finally:
        plt.close(figure)
    if args.alt_output is not None:
        write_alt_text(dataset, args.alt_output)
    rates = ", ".join(
        f"{metrics.name}={metrics.success_rate:.1%}" for metrics in dataset.versions
    )
    print(
        f"dataset={dataset.dataset_version} rates=[{rates}] "
        f"pareto={','.join(pareto_versions(dataset.versions))}"
    )
    for output in outputs:
        print(f"wrote {output}")
    if args.alt_output is not None:
        print(f"wrote {args.alt_output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


