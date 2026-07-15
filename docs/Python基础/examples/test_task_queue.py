import json
import tempfile
import unittest
from pathlib import Path

from task_queue import TaskValidationError, load_tasks, summarize, write_report


class TaskQueueTests(unittest.TestCase):
    def _input(self, directory: str, value: object) -> Path:
        path = Path(directory) / "tasks.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
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

    def test_missing_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._input(directory, [{"id": "a", "status": "done"}])
            with self.assertRaisesRegex(TaskValidationError, "缺少字段"):
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

    def test_write_report_uses_utf8_json(self) -> None:
        report = {"total": 1, "by_status": {"done": 1}, "unfinished_ids": []}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            write_report(report, output)
            loaded = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(loaded, report)


if __name__ == "__main__":
    unittest.main()

