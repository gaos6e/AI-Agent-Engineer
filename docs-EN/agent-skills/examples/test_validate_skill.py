"""Regression tests for the offline Agent Skill teaching project."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


EXAMPLES_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = EXAMPLES_ROOT / "text-statistics"
VALIDATOR_PATH = EXAMPLES_ROOT / "validate_skill.py"
SCRIPT_PATH = SKILL_ROOT / "scripts" / "text_stats.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_module("agent_skill_validator", VALIDATOR_PATH)
text_stats = load_module("text_statistics_script", SCRIPT_PATH)


class TextStatisticsUnitTests(unittest.TestCase):
    def test_empty_text(self) -> None:
        self.assertEqual(text_stats.calculate(""), {"words": 0, "characters": 0, "lines": 0})

    def test_ascii_runs(self) -> None:
        self.assertEqual(text_stats.calculate("one two_2")["words"], 2)

    def test_han_characters_are_individual_tokens(self) -> None:
        self.assertEqual(text_stats.calculate("\u4f60\u597d Agent")["words"], 3)

    def test_punctuation_is_not_a_word(self) -> None:
        self.assertEqual(text_stats.calculate("...!? ")["words"], 0)

    def test_unicode_character_count_includes_space(self) -> None:
        self.assertEqual(text_stats.calculate("\u4f60 a")["characters"], 3)

    def test_lf_line_count(self) -> None:
        self.assertEqual(text_stats.logical_line_count("a\nb"), 2)

    def test_crlf_is_one_separator(self) -> None:
        self.assertEqual(text_stats.logical_line_count("a\r\nb"), 2)

    def test_lone_cr_is_a_separator(self) -> None:
        self.assertEqual(text_stats.logical_line_count("a\rb"), 2)

    def test_trailing_separator_adds_empty_line(self) -> None:
        self.assertEqual(text_stats.logical_line_count("a\n"), 2)

    def test_read_utf8_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.txt"
            path.write_text("\u4f60\u597d", encoding="utf-8")
            self.assertEqual(text_stats.read_utf8_file(path), "\u4f60\u597d")

    def test_read_utf8_file_rejects_more_than_one_mib(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "large.txt"
            path.write_bytes(b"x" * (text_stats.MAX_INPUT_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "exceeds"):
                text_stats.read_utf8_file(path)

    def test_text_argument_limit_counts_utf8_bytes(self) -> None:
        oversized = "\u754c" * (text_stats.MAX_INPUT_BYTES // len("\u754c".encode("utf-8")) + 1)
        with self.assertRaisesRegex(ValueError, "--text exceeds"):
            text_stats.require_bounded_utf8_text(oversized, source="--text")


class TextStatisticsCliTests(unittest.TestCase):
    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT_PATH), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_text_success_is_json(self) -> None:
        result = self.run_script("--text", "Hello \u4e16\u754c")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["words"], 3)
        self.assertEqual(result.stderr, "")

    def test_input_file_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.txt"
            path.write_text("one\ntwo", encoding="utf-8")
            result = self.run_script("--input", str(path))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["lines"], 2)

    def test_missing_source_fails(self) -> None:
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required", result.stderr)

    def test_mutually_exclusive_sources_fail(self) -> None:
        result = self.run_script("--text", "x", "--input", "x.txt")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not allowed", result.stderr)

    def test_missing_file_fails_without_stdout(self) -> None:
        result = self.run_script("--input", "definitely-missing.txt")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("not a file", result.stderr)

    def test_directory_input_fails(self) -> None:
        result = self.run_script("--input", str(SKILL_ROOT))
        self.assertEqual(result.returncode, 2)
        self.assertIn("not a file", result.stderr)

    def test_invalid_utf8_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.txt"
            path.write_bytes(b"\xff\xfe")
            result = self.run_script("--input", str(path))
        self.assertEqual(result.returncode, 2)
        self.assertIn("valid UTF-8", result.stderr)

    def test_oversized_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "large.txt"
            path.write_bytes(b"x" * (text_stats.MAX_INPUT_BYTES + 1))
            result = self.run_script("--input", str(path))
        self.assertEqual(result.returncode, 2)
        self.assertIn("exceeds", result.stderr)

    def test_oversized_text_fails_with_controlled_cli_error(self) -> None:
        code = (
            "import runpy, sys; "
            "module = runpy.run_path(sys.argv[1]); "
            "count = module['MAX_INPUT_BYTES'] // len('\u754c'.encode('utf-8')) + 1; "
            "raise SystemExit(module['main'](['--text', '\u754c' * count]))"
        )
        result = subprocess.run(
            [sys.executable, "-B", "-c", code, str(SCRIPT_PATH)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("--text exceeds", result.stderr)

    def test_help_is_noninteractive(self) -> None:
        result = self.run_script("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--input", result.stdout)

    def test_output_does_not_echo_input(self) -> None:
        secret_marker = "redaction-test-marker"
        result = self.run_script("--text", secret_marker)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn(secret_marker, result.stdout)


class ValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.skill = Path(self.temporary.name) / "text-statistics"
        shutil.copytree(SKILL_ROOT, self.skill)

    @property
    def skill_file(self) -> Path:
        return self.skill / "SKILL.md"

    @property
    def eval_file(self) -> Path:
        return self.skill / "evals" / "evals.json"

    def replace_skill_text(self, old: str, new: str) -> None:
        text = self.skill_file.read_text(encoding="utf-8")
        self.skill_file.write_text(text.replace(old, new, 1), encoding="utf-8")

    def load_evals(self) -> dict[str, object]:
        return json.loads(self.eval_file.read_text(encoding="utf-8"))

    def save_evals(self, data: dict[str, object]) -> None:
        self.eval_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_bundled_example_is_valid(self) -> None:
        result = validator.validate_skill(self.skill)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["trigger_cases"], {"total": 20, "positive": 10, "negative": 10})
        self.assertEqual(result["python_scripts"], ["scripts/text_stats.py"])

    def test_missing_directory_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "directory not found"):
            validator.validate_skill(self.skill / "missing")

    def test_missing_skill_file_fails(self) -> None:
        self.skill_file.unlink()
        with self.assertRaisesRegex(ValueError, "SKILL.md not found"):
            validator.validate_skill(self.skill)

    def test_missing_opening_delimiter_fails(self) -> None:
        self.replace_skill_text("---\n", "",)
        with self.assertRaisesRegex(ValueError, "must start"):
            validator.validate_skill(self.skill)

    def test_missing_closing_delimiter_fails(self) -> None:
        text = self.skill_file.read_text(encoding="utf-8")
        second = text.index("\n---\n", 4)
        self.skill_file.write_text(text[:second] + text[second + 4 :], encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "no closing"):
            validator.validate_skill(self.skill)

    def test_uppercase_name_fails(self) -> None:
        self.replace_skill_text("name: text-statistics", "name: Text-statistics")
        with self.assertRaisesRegex(ValueError, "lowercase"):
            validator.validate_skill(self.skill)

    def test_consecutive_hyphen_name_fails(self) -> None:
        self.replace_skill_text("name: text-statistics", "name: text--statistics")
        with self.assertRaisesRegex(ValueError, "single hyphens"):
            validator.validate_skill(self.skill)

    def test_name_must_match_directory(self) -> None:
        self.replace_skill_text("name: text-statistics", "name: text-counts")
        with self.assertRaisesRegex(ValueError, "match the parent"):
            validator.validate_skill(self.skill)

    def test_empty_description_fails(self) -> None:
        line = next(line for line in self.skill_file.read_text(encoding="utf-8").splitlines() if line.startswith("description:"))
        self.replace_skill_text(line, "description:")
        with self.assertRaisesRegex(ValueError, "needs a scalar"):
            validator.validate_skill(self.skill)

    def test_long_description_fails(self) -> None:
        line = next(line for line in self.skill_file.read_text(encoding="utf-8").splitlines() if line.startswith("description:"))
        self.replace_skill_text(line, "description: " + ("x" * 1025))
        with self.assertRaisesRegex(ValueError, "1-1024"):
            validator.validate_skill(self.skill)

    def test_long_compatibility_fails(self) -> None:
        line = next(line for line in self.skill_file.read_text(encoding="utf-8").splitlines() if line.startswith("compatibility:"))
        self.replace_skill_text(line, "compatibility: " + ("x" * 501))
        with self.assertRaisesRegex(ValueError, "1-500"):
            validator.validate_skill(self.skill)

    def test_duplicate_top_level_field_fails(self) -> None:
        self.replace_skill_text("name: text-statistics", "name: text-statistics\nname: text-statistics")
        with self.assertRaisesRegex(ValueError, "duplicate frontmatter"):
            validator.validate_skill(self.skill)

    def test_unknown_top_level_field_fails(self) -> None:
        self.replace_skill_text("license: CC0-1.0", "mystery: value\nlicense: CC0-1.0")
        with self.assertRaisesRegex(ValueError, "unsupported top-level"):
            validator.validate_skill(self.skill)

    def test_metadata_is_parsed_as_strings(self) -> None:
        result = validator.validate_skill(self.skill)
        self.assertEqual(result["name"], "text-statistics")

    def test_empty_metadata_fails(self) -> None:
        self.replace_skill_text(
            "metadata:\n  version: 1.0.0\n  source: ai-agent-engineer-course",
            "metadata:",
        )
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            validator.validate_skill(self.skill)

    def test_duplicate_metadata_key_fails(self) -> None:
        self.replace_skill_text("  source: ai-agent-engineer-course", "  version: duplicate")
        with self.assertRaisesRegex(ValueError, "duplicate metadata"):
            validator.validate_skill(self.skill)

    def test_empty_body_fails(self) -> None:
        text = self.skill_file.read_text(encoding="utf-8")
        closing = text.index("\n---\n", 4) + len("\n---\n")
        self.skill_file.write_text(text[:closing], encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "body must not be empty"):
            validator.validate_skill(self.skill)

    def test_missing_referenced_resource_fails(self) -> None:
        self.replace_skill_text("scripts/text_stats.py", "scripts/missing.py")
        with self.assertRaisesRegex(ValueError, "missing resource"):
            validator.validate_skill(self.skill)

    def test_resource_traversal_fails(self) -> None:
        self.replace_skill_text("scripts/text_stats.py", "scripts/../../outside.py")
        with self.assertRaisesRegex(ValueError, "canonical relative POSIX"):
            validator.validate_skill(self.skill)

    def test_noncanonical_resource_path_fails_even_when_it_stays_within_root(self) -> None:
        self.replace_skill_text("scripts/text_stats.py", "scripts/../SKILL.md")
        with self.assertRaisesRegex(ValueError, "canonical relative POSIX"):
            validator.validate_skill(self.skill)

    def test_invalid_python_script_fails(self) -> None:
        (self.skill / "scripts" / "text_stats.py").write_text("def broken(:\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "invalid Python script"):
            validator.validate_skill(self.skill)

    def test_eval_skill_name_must_match(self) -> None:
        data = self.load_evals()
        data["skill_name"] = "other"
        self.save_evals(data)
        with self.assertRaisesRegex(ValueError, "skill_name must match"):
            validator.validate_skill(self.skill)

    def test_eval_ids_must_be_unique(self) -> None:
        data = self.load_evals()
        evals = data["evals"]
        self.assertIsInstance(evals, list)
        evals[1]["id"] = evals[0]["id"]
        self.save_evals(data)
        with self.assertRaisesRegex(ValueError, "duplicate eval id"):
            validator.validate_skill(self.skill)

    def test_eval_prompt_must_be_nonempty(self) -> None:
        data = self.load_evals()
        data["evals"][0]["prompt"] = ""
        self.save_evals(data)
        with self.assertRaisesRegex(ValueError, "non-empty prompt"):
            validator.validate_skill(self.skill)

    def test_eval_trigger_must_be_boolean(self) -> None:
        data = self.load_evals()
        data["evals"][0]["should_trigger"] = "yes"
        self.save_evals(data)
        with self.assertRaisesRegex(ValueError, "boolean should_trigger"):
            validator.validate_skill(self.skill)

    def test_eval_reason_is_required(self) -> None:
        data = self.load_evals()
        data["evals"][0]["reason"] = ""
        self.save_evals(data)
        with self.assertRaisesRegex(ValueError, "non-empty reason"):
            validator.validate_skill(self.skill)

    def test_eval_expected_output_is_required(self) -> None:
        data = self.load_evals()
        data["evals"][0]["expected_output"] = ""
        self.save_evals(data)
        with self.assertRaisesRegex(ValueError, "expected_output"):
            validator.validate_skill(self.skill)

    def test_too_few_positive_cases_fail(self) -> None:
        data = self.load_evals()
        for case in data["evals"][:3]:
            case["should_trigger"] = False
        self.save_evals(data)
        with self.assertRaisesRegex(ValueError, "positive trigger"):
            validator.validate_skill(self.skill)

    def test_too_few_negative_cases_fail(self) -> None:
        data = self.load_evals()
        for case in data["evals"][10:13]:
            case["should_trigger"] = True
        self.save_evals(data)
        with self.assertRaisesRegex(ValueError, "negative trigger"):
            validator.validate_skill(self.skill)

    def test_duplicate_json_key_fails(self) -> None:
        self.eval_file.write_text('{"skill_name":"text-statistics","skill_name":"other","evals":[]}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            validator.validate_skill(self.skill)

    def test_missing_evals_directory_is_allowed(self) -> None:
        shutil.rmtree(self.skill / "evals")
        result = validator.validate_skill(self.skill)
        self.assertEqual(result["trigger_cases"]["total"], 0)

    def test_long_skill_file_is_warning_not_false_conformance_failure(self) -> None:
        with self.skill_file.open("a", encoding="utf-8") as stream:
            stream.write("\n" + "\n".join(f"line {index}" for index in range(510)))
        result = validator.validate_skill(self.skill)
        self.assertTrue(any("under 500" in warning for warning in result["warnings"]))


class ValidatorCliTests(unittest.TestCase):
    def test_noncanonical_resource_path_is_a_controlled_cli_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill = Path(temp) / "text-statistics"
            shutil.copytree(SKILL_ROOT, skill)
            skill_file = skill / "SKILL.md"
            skill_file.write_text(
                skill_file.read_text(encoding="utf-8").replace(
                    "scripts/text_stats.py", "scripts/../SKILL.md", 1
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-B", str(VALIDATOR_PATH), str(skill)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        error = json.loads(result.stderr)
        self.assertEqual(error["status"], "error")
        self.assertIn("canonical relative POSIX", error["message"])


if __name__ == "__main__":
    unittest.main(verbosity=2)


