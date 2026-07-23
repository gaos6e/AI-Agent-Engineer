import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from task_queue import (
    TaskValidationError,
    load_tasks,
    main,
    summarize,
    write_report,
)


class TaskQueueTests(unittest.TestCase):
    def _input(self, directory: str, value: object) -> Path:
        path = Path(directory) / "tasks.json"
        path.write_text(
            json.dumps(value, ensure_ascii=False, allow_nan=False),
            encoding="utf-8",
        )
        return path

    def test_load_and_summarize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(
                directory,
                [
                    {"id": "a", "title": "检索", "status": "done"},
                    {"id": "b", "title": "校验", "status": "pending"},
                ],
            )
            report = summarize(load_tasks(path))

        self.assertEqual(report["total"], 2)
        self.assertEqual(report["by_status"], {"done": 1, "pending": 1})
        self.assertEqual(report["unfinished_ids"], ["b"])

    def test_empty_array_produces_empty_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(directory, [])
            report = summarize(load_tasks(path))

        self.assertEqual(
            report,
            {"total": 0, "by_status": {}, "unfinished_ids": []},
        )

    def test_status_keys_are_sorted_and_unfinished_ids_keep_input_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(
                directory,
                [
                    {"id": "任务乙", "title": "检索", "status": "pending"},
                    {"id": "task-a", "title": "生成", "status": "done"},
                    {"id": "任务甲", "title": "校验", "status": "failed"},
                ],
            )
            report = summarize(load_tasks(path))

        self.assertEqual(
            list(report["by_status"]),
            ["done", "failed", "pending"],
        )
        self.assertEqual(report["unfinished_ids"], ["任务乙", "任务甲"])

    def test_missing_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            with self.assertRaisesRegex(TaskValidationError, "输入文件不存在"):
                load_tasks(path)

    def test_missing_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(directory, [{"id": "a", "status": "done"}])
            with self.assertRaisesRegex(TaskValidationError, "缺少字段"):
                load_tasks(path)

    def test_unknown_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(
                directory,
                [{"id": "a", "title": "检索", "status": "done", "owner": "x"}],
            )
            with self.assertRaisesRegex(TaskValidationError, "未知字段"):
                load_tasks(path)

    def test_invalid_status_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(
                directory,
                [{"id": "a", "title": "检索", "status": "complete"}],
            )
            with self.assertRaisesRegex(TaskValidationError, "status=.*非法"):
                load_tasks(path)

    def test_blank_string_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(
                directory,
                [{"id": "  ", "title": "检索", "status": "done"}],
            )
            with self.assertRaisesRegex(TaskValidationError, "id 必须是非空字符串"):
                load_tasks(path)

    def test_surrounding_whitespace_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(
                directory,
                [{"id": " a", "title": "检索", "status": "done"}],
            )
            with self.assertRaisesRegex(TaskValidationError, "首尾空白"):
                load_tasks(path)

    def test_duplicate_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(
                directory,
                [
                    {"id": "a", "title": "一", "status": "done"},
                    {"id": "a", "title": "二", "status": "failed"},
                ],
            )
            with self.assertRaisesRegex(TaskValidationError, "id 重复"):
                load_tasks(path)

    def test_root_must_be_array(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(directory, {"tasks": []})
            with self.assertRaisesRegex(TaskValidationError, "根节点必须是数组"):
                load_tasks(path)

    def test_array_item_must_be_object(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(directory, ["not-an-object"])
            with self.assertRaisesRegex(TaskValidationError, "第 0 项必须是 JSON 对象"):
                load_tasks(path)

    def test_invalid_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.json"
            path.write_text("[{", encoding="utf-8")
            with self.assertRaisesRegex(TaskValidationError, "JSON 格式错误"):
                load_tasks(path)

    def test_invalid_utf8_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.json"
            path.write_bytes(b"\xff\xfe")
            with self.assertRaisesRegex(TaskValidationError, "有效 UTF-8"):
                load_tasks(path)

    def test_input_size_limit_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(directory, [])
            with self.assertRaisesRegex(TaskValidationError, "字节上限"):
                load_tasks(path, max_bytes=1)

    def test_non_finite_json_number_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.json"
            path.write_text("[NaN]", encoding="utf-8")
            with self.assertRaisesRegex(TaskValidationError, "非有限数值"):
                load_tasks(path)

    def test_write_report_uses_utf8_json(self) -> None:
        report = {"total": 1, "by_status": {"done": 1}, "unfinished_ids": []}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            write_report(report, output)
            loaded = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(loaded, report)

    def test_cli_returns_two_for_expected_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(directory, {"tasks": []})
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main([str(path)])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("输入错误", stderr.getvalue())

    def test_cli_prints_json_and_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(
                directory,
                [{"id": "a", "title": "检索", "status": "done"}],
            )
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main([str(path)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(json.loads(stdout.getvalue())["total"], 1)

    def test_cli_stdout_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(
                directory,
                [{"id": "任务一", "title": "检索", "status": "pending"}],
            )
            outputs: list[str] = []
            for _ in range(2):
                stdout = StringIO()
                stderr = StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = main([str(path)])
                self.assertEqual(exit_code, 0)
                self.assertEqual(stderr.getvalue(), "")
                outputs.append(stdout.getvalue())

        self.assertEqual(outputs[0], outputs[1])
        self.assertIn("任务一", outputs[0])

    def test_cli_writes_parseable_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(
                directory,
                [{"id": "a", "title": "检索", "status": "pending"}],
            )
            output = Path(directory) / "report.json"
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main([str(path), "--output", str(output)])
            report = json.loads(output.read_text(encoding="utf-8"))

            stdout_only = StringIO()
            with redirect_stdout(stdout_only), redirect_stderr(StringIO()):
                stdout_exit_code = main([str(path)])
            stdout_report = json.loads(stdout_only.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout_exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("报告已写入", stdout.getvalue())
        self.assertEqual(report["unfinished_ids"], ["a"])
        self.assertEqual(report, stdout_report)

    def test_same_input_and_output_path_is_rejected_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(
                directory,
                [{"id": "a", "title": "检索", "status": "done"}],
            )
            original = path.read_bytes()
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main([str(path), "--output", str(path)])
            current = path.read_bytes()

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("不能与输入文件相同", stderr.getvalue())
        self.assertEqual(current, original)

    def test_output_write_failure_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(directory, [])
            output_directory = Path(directory) / "report-directory"
            output_directory.mkdir()
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [str(path), "--output", str(output_directory)]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("输出错误", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
