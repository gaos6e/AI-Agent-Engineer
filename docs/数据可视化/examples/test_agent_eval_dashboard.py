"""Tests for the offline Agent evaluation dashboard."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import struct
import tempfile
import unittest
from pathlib import Path

import agent_eval_dashboard as dashboard
import matplotlib.pyplot as plt


class AgentEvalDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sample_path = Path(__file__).with_name("sample_agent_eval.json")
        cls.sample_raw = json.loads(cls.sample_path.read_text(encoding="utf-8"))

    def write_data(self, directory: Path, data: object) -> Path:
        path = directory / "input.json"
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return path

    def test_sample_dataset_is_strict_and_auditable(self) -> None:
        data = dashboard.load_dataset(self.sample_path)
        self.assertEqual(data.dataset_version, "demo-2026-07-14-v1")
        self.assertEqual([item.name for item in data.versions], ["v1", "v2", "v3"])
        self.assertEqual(sum(sum(row) for row in data.routing.matrix), 200)
        self.assertEqual(data.routing.version, "v3")

    def test_duplicate_keys_and_non_finite_numbers_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            duplicate = root / "duplicate.json"
            duplicate.write_text('{"dataset_version":"a","dataset_version":"b"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                dashboard.load_dataset(duplicate)
            non_finite = root / "non-finite.json"
            non_finite.write_text('{"value": NaN}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-finite"):
                dashboard.load_dataset(non_finite)

    def test_version_count_latency_and_cost_invariants(self) -> None:
        mutations = (
            ("success", lambda raw: raw["versions"][0].update(success_count=201), "cannot exceed"),
            ("overlap", lambda raw: raw["versions"][0].update(timeout_count=60), "overlap"),
            ("all-timeout", lambda raw: raw["versions"][0].update(success_count=0, timeout_count=200), "at least one completed"),
            ("latency", lambda raw: raw["versions"][0].update(p95_latency_ms=100), "must be >="),
            ("cost", lambda raw: raw["versions"][0].update(mean_cost_usd=-1), "finite and >="),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, mutate, message in mutations:
                with self.subTest(name=name):
                    raw = copy.deepcopy(self.sample_raw)
                    mutate(raw)
                    with self.assertRaisesRegex(ValueError, message):
                        dashboard.load_dataset(self.write_data(root, raw))

    def test_unknown_fields_and_duplicate_versions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = copy.deepcopy(self.sample_raw)
            raw["unexpected"] = True
            with self.assertRaisesRegex(ValueError, "unknown"):
                dashboard.load_dataset(self.write_data(root, raw))
            raw = copy.deepcopy(self.sample_raw)
            raw["versions"][1]["name"] = "v1"
            with self.assertRaisesRegex(ValueError, "unique"):
                dashboard.load_dataset(self.write_data(root, raw))

    def test_confusion_shape_labels_and_total_are_validated(self) -> None:
        mutations = (
            ("shape", lambda raw: raw["routing"]["matrix"].pop(), "square"),
            ("labels", lambda raw: raw["routing"]["labels"].__setitem__(1, "account"), "unique"),
            ("total", lambda raw: raw["routing"]["matrix"][0].__setitem__(0, 59), "total"),
            ("version", lambda raw: raw["routing"].update(version="missing"), "evaluated version"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, mutate, message in mutations:
                with self.subTest(name=name):
                    raw = copy.deepcopy(self.sample_raw)
                    mutate(raw)
                    with self.assertRaisesRegex(ValueError, message):
                        dashboard.load_dataset(self.write_data(root, raw))

    def test_wilson_interval_handles_boundaries_and_known_midpoint(self) -> None:
        lower_zero, upper_zero = dashboard.wilson_interval(0, 10)
        lower_half, upper_half = dashboard.wilson_interval(5, 10)
        lower_all, upper_all = dashboard.wilson_interval(10, 10)
        self.assertAlmostEqual(lower_zero, 0.0, places=12)
        self.assertAlmostEqual(upper_zero, 0.2775328, places=6)
        self.assertAlmostEqual(lower_half, 0.2365931, places=6)
        self.assertAlmostEqual(upper_half, 0.7634069, places=6)
        self.assertAlmostEqual(lower_all, 0.7224672, places=6)
        self.assertAlmostEqual(upper_all, 1.0, places=12)
        with self.assertRaises(ValueError):
            dashboard.wilson_interval(2, 1)

    def test_pareto_frontier_excludes_dominated_v2(self) -> None:
        data = dashboard.load_dataset(self.sample_path)
        self.assertEqual(dashboard.pareto_versions(data.versions), ("v1", "v3"))
        with self.assertRaises(ValueError):
            dashboard.pareto_versions(())

    def test_dashboard_has_four_semantic_panels_and_colorbar(self) -> None:
        data = dashboard.load_dataset(self.sample_path)
        figure = dashboard.build_dashboard(data)
        try:
            self.assertEqual(len(figure.axes), 5)
            titles = [axis.get_title(loc="left") for axis in figure.axes[:4]]
            self.assertEqual([title[:3] for title in titles], ["(a)", "(b)", "(c)", "(d)"])
            self.assertEqual(tuple(figure.get_size_inches()), (11.0, 7.4))
            self.assertEqual(figure.axes[2].get_xlabel(), "Predicted route")
            self.assertEqual(figure.axes[2].get_ylabel(), "True route")
        finally:
            plt.close(figure)

    def test_png_svg_and_alt_text_are_written(self) -> None:
        data = dashboard.load_dataset(self.sample_path)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            png = root / "dashboard.png"
            svg = root / "dashboard.svg"
            alt = root / "dashboard.txt"
            figure = dashboard.build_dashboard(data)
            try:
                dashboard.save_dashboard(figure, png, dpi=180)
                dashboard.save_dashboard(figure, svg, dpi=180)
            finally:
                plt.close(figure)
            dashboard.write_alt_text(data, alt)
            self.assertEqual(png.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            width, height = struct.unpack(">II", png.read_bytes()[16:24])
            self.assertEqual((width, height), (1980, 1332))
            self.assertIn("<svg", svg.read_text(encoding="utf-8")[:1000])
            self.assertIn("Wilson 95%", alt.read_text(encoding="utf-8"))

    def test_alt_text_reports_data_not_visual_decoration(self) -> None:
        data = dashboard.load_dataset(self.sample_path)
        alt = dashboard.build_alt_text(data)
        self.assertIn("v3 has the highest", alt)
        self.assertIn("true technical predicted as refund (8 tasks)", alt)
        self.assertIn("v1, v3", alt)

    def test_cli_writes_two_formats_and_prints_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            png = root / "dashboard.png"
            svg = root / "dashboard.svg"
            alt = root / "dashboard.txt"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = dashboard.main(
                    [
                        "--data",
                        str(self.sample_path),
                        "--output",
                        str(png),
                        "--output",
                        str(svg),
                        "--alt-output",
                        str(alt),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertTrue(png.is_file())
            self.assertTrue(svg.is_file())
            self.assertTrue(alt.is_file())
            self.assertIn("pareto=v1,v3", stdout.getvalue())

    def test_output_contract_rejects_lossy_format_and_bad_dpi(self) -> None:
        data = dashboard.load_dataset(self.sample_path)
        figure = dashboard.build_dashboard(data)
        try:
            with self.assertRaisesRegex(ValueError, "suffix"):
                dashboard.save_dashboard(figure, Path("dashboard.jpg"))
            with self.assertRaisesRegex(ValueError, "dpi"):
                dashboard.save_dashboard(figure, Path("dashboard.png"), dpi=71)
        finally:
            plt.close(figure)


if __name__ == "__main__":
    unittest.main()
