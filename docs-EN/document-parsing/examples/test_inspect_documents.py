from __future__ import annotations

from contextlib import redirect_stderr
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import tempfile
import unittest

import inspect_documents as subject


class InspectDocumentsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "inputs"
        self.root.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_text(self, relative: str, text: str, encoding: str = "utf-8") -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding=encoding, newline="")
        return path

    def write_bytes(self, relative: str, value: bytes) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
        return path

    def scan(self, limits: subject.Limits = subject.Limits()) -> dict:
        return subject.scan_root(self.root, limits)

    def test_markdown_preserves_structure_location_and_nfc(self) -> None:
        self.write_text(
            "guide.md",
            "# Getting Started\r\n\r\ne\u0301 is an example\r\n\r\n- First step\r\n\r\n```python\r\nprint('ok')\r\n```\r\n",
        )

        manifest = self.scan()
        document = manifest["documents"][0]

        self.assertEqual("pass", manifest["summary"]["gate"])
        self.assertEqual(
            ["heading", "paragraph", "list_item", "code_block"],
            [element["kind"] for element in document["elements"]],
        )
        self.assertEqual("é is an example", document["elements"][1]["text"])
        self.assertEqual(["Getting Started"], document["elements"][2]["section_path"])
        self.assertEqual(1, document["elements"][0]["location"]["line_start"])
        self.assertEqual(
            "normalized-text-lines-1-based-inclusive-v1",
            document["elements"][0]["location"]["coordinate_space"],
        )
        self.assertEqual("python", document["elements"][3]["attributes"]["language"])

    def test_csv_handles_quoted_comma_and_embedded_newline(self) -> None:
        self.write_text("data.csv", 'name,note\r\nA,"contains, comma"\r\nB,"spans\r\nlines"\r\n')

        document = self.scan()["documents"][0]
        rows = [json.loads(element["text"]) for element in document["elements"]]

        self.assertEqual("parsed", document["status"])
        self.assertEqual("contains, comma", rows[0]["note"])
        self.assertEqual("spans\nlines", rows[1]["note"])
        self.assertEqual(3, document["elements"][1]["location"]["line_start"])
        self.assertEqual(4, document["elements"][1]["location"]["line_end"])

    def test_json_rejects_duplicate_fields(self) -> None:
        self.write_text("duplicate.json", '{"id": 1, "id": 2}')

        document = self.scan()["documents"][0]

        self.assertEqual("rejected", document["status"])
        self.assertIn("duplicate JSON field", document["issues"][0]["message"])

    def test_json_rejects_non_finite_numbers(self) -> None:
        self.write_text("nonfinite.json", '{"score": NaN}')

        document = self.scan()["documents"][0]

        self.assertEqual("rejected", document["status"])
        self.assertIn("non-finite", document["issues"][0]["message"])

    def test_json_rejects_utf16_for_open_exchange(self) -> None:
        self.write_bytes("data.json", codecs_utf16('{"ok": true}'))

        document = self.scan()["documents"][0]

        self.assertEqual("rejected", document["status"])
        self.assertIn("JSON for open-system exchange must use UTF-8", document["issues"][0]["message"])

    def test_plain_text_accepts_utf16_bom_and_records_warning(self) -> None:
        self.write_bytes("note.txt", codecs_utf16("English paragraph"))

        document = self.scan()["documents"][0]

        self.assertEqual("parsed", document["status"])
        self.assertEqual("utf-16", document["encoding"])
        self.assertEqual("utf16_bom", document["issues"][0]["code"])
        self.assertEqual("review_required", self.scan()["summary"]["gate"])

    def test_invalid_utf8_fails_closed(self) -> None:
        self.write_bytes("broken.txt", b"ok\xffbad")

        document = self.scan()["documents"][0]

        self.assertEqual("rejected", document["status"])
        self.assertIn("strict decoding failed", document["issues"][0]["message"])

    def test_nul_text_is_treated_as_binary_or_corrupt(self) -> None:
        self.write_bytes("binary.txt", b"header\x00payload")

        document = self.scan()["documents"][0]

        self.assertEqual("rejected", document["status"])
        self.assertIn("NUL", document["issues"][0]["message"])

    def test_other_c0_control_characters_require_review_warning(self) -> None:
        self.write_bytes("legacy.txt", b"page-one\x0cpage-two")

        manifest = self.scan()
        document = manifest["documents"][0]

        self.assertEqual("parsed", document["status"])
        self.assertEqual("control_characters_present", document["issues"][0]["code"])
        self.assertEqual("review_required", manifest["summary"]["gate"])

    def test_html_ignores_script_and_keeps_table_cells(self) -> None:
        self.write_text(
            "page.html",
            "<html><h1>API</h1><p>Set the <strong>timeout</strong>.</p>"
            "<script>secret()</script><table><tr><th>Item</th><th>Value</th></tr>"
            "<tr><td>timeout</td><td>10</td></tr></table></html>",
        )

        document = self.scan()["documents"][0]
        texts = [element["text"] for element in document["elements"]]

        self.assertNotIn("secret()", " ".join(texts))
        self.assertIn("Set the timeout.", texts)
        self.assertEqual(2, sum(element["kind"] == "table_row" for element in document["elements"]))
        self.assertEqual(["API"], document["elements"][-1]["section_path"])

    def test_html_disguised_as_pdf_is_rejected(self) -> None:
        self.write_text("report.pdf", "<!doctype html><html><p>download failed</p></html>")

        document = self.scan()["documents"][0]

        self.assertEqual("rejected", document["status"])
        self.assertEqual("media_type_mismatch", document["issues"][0]["code"])
        self.assertEqual("text/html", document["detected_media_type"])

    def test_pdf_is_registered_without_claiming_pdf_parsing(self) -> None:
        self.write_bytes("paper.pdf", b"%PDF-1.7\nnot-a-complete-pdf")

        manifest = self.scan()
        document = manifest["documents"][0]

        self.assertEqual("external_adapter_required", document["status"])
        self.assertEqual("review_required", manifest["summary"]["gate"])
        self.assertEqual([], document["elements"])

    def test_ooxml_container_is_not_unzipped(self) -> None:
        self.write_bytes("report.docx", b"PK\x03\x04minimal-placeholder")

        document = self.scan()["documents"][0]

        self.assertEqual("external_adapter_required", document["status"])
        self.assertEqual(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            document["detected_media_type"],
        )
        self.assertEqual("container-signature+extension", document["detection_method"])

    def test_unknown_extension_does_not_guess_a_parser(self) -> None:
        self.write_text("mystery.bin", "looks like text")

        document = self.scan()["documents"][0]

        self.assertEqual("rejected", document["status"])
        self.assertEqual("unknown_extension", document["issues"][0]["code"])

    def test_single_file_limit_rejects_before_reading(self) -> None:
        self.write_bytes("large.txt", b"12345")

        document = self.scan(subject.Limits(10, 4, 100))["documents"][0]

        self.assertEqual("file_too_large", document["issues"][0]["code"])
        self.assertIsNone(document["raw_sha256"])

    def test_bounded_read_rejects_bytes_that_exceed_the_read_budget(self) -> None:
        path = self.write_bytes("changed-during-read.txt", b"12345")

        with self.assertRaisesRegex(subject.DocumentError, "file exceeded the 4-byte read budget"):
            subject._read_bounded_bytes(path, 4)

    def test_total_budget_stops_later_file(self) -> None:
        self.write_text("a.txt", "1234")
        self.write_text("b.txt", "5678")

        manifest = self.scan(subject.Limits(10, 10, 5))

        self.assertEqual("parsed", manifest["documents"][0]["status"])
        self.assertEqual("total_budget_exceeded", manifest["documents"][1]["issues"][0]["code"])
        self.assertEqual(4, manifest["summary"]["consumed_bytes"])

    def test_file_count_limit_fails_closed(self) -> None:
        self.write_text("a.txt", "a")
        self.write_text("b.txt", "b")

        manifest = self.scan(subject.Limits(1, 10, 10))

        self.assertEqual(1, len(manifest["documents"]))
        self.assertEqual(2, manifest["summary"]["discovered_file_count"])
        self.assertEqual(1, manifest["summary"]["processed_file_count"])
        self.assertEqual("file_limit_exceeded", manifest["issues"][0]["code"])
        self.assertEqual("fail", manifest["summary"]["gate"])

    def test_manifest_is_deterministic_for_unchanged_input(self) -> None:
        self.write_text("stable.json", '{"b": 2, "a": 1}')

        first = self.scan()
        second = self.scan()

        self.assertEqual(first, second)
        self.assertEqual('{"a":1,"b":2}', first["documents"][0]["elements"][0]["text"])

    def test_parse_revision_is_full_sha256_and_recomputable(self) -> None:
        self.write_text("versioned.txt", "stable body")

        manifest = self.scan()
        document = manifest["documents"][0]
        payload = json.dumps(
            {
                "config_sha256": manifest["config_sha256"],
                "parser": document["parser"],
                "parser_version": document["parser_version"],
                "raw_sha256": document["raw_sha256"],
            },
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        expected = sha256(payload.encode("utf-8")).hexdigest()

        self.assertEqual(expected, document["parse_revision_sha256"])
        self.assertRegex(document["parse_revision_sha256"], r"^[0-9a-f]{64}$")

    def test_parse_revision_and_element_ids_change_when_config_changes(self) -> None:
        self.write_text("versioned.txt", "stable body")

        first = self.scan(subject.Limits(100, 1_000_000, 5_000_000))["documents"][0]
        second = self.scan(subject.Limits(101, 1_000_000, 5_000_000))["documents"][0]

        self.assertEqual(first["raw_sha256"], second["raw_sha256"])
        self.assertNotEqual(first["parse_revision_sha256"], second["parse_revision_sha256"])
        self.assertNotEqual(first["elements"][0]["element_id"], second["elements"][0]["element_id"])

    def test_element_id_binds_parse_revision_kind_span_and_text_hash(self) -> None:
        parse_revision = "a" * 64
        variants = (
            subject.ParsedBlock("paragraph", "alpha", 1, 1),
            subject.ParsedBlock("list_item", "alpha", 1, 1),
            subject.ParsedBlock("paragraph", "alpha", 2, 2),
            subject.ParsedBlock("paragraph", "beta", 1, 1),
        )

        element_ids = {
            subject._make_elements(parse_revision, [block])[0].element_id
            for block in variants
        }

        self.assertEqual(len(variants), len(element_ids))
        self.assertTrue(all(re.fullmatch(r"elm_[0-9a-f]{64}", value) for value in element_ids))

    def test_hash_and_source_id_change_when_raw_bytes_change(self) -> None:
        path = self.write_text("version.txt", "v1")
        first = self.scan()["documents"][0]
        path.write_text("v2", encoding="utf-8")
        second = self.scan()["documents"][0]

        self.assertNotEqual(first["raw_sha256"], second["raw_sha256"])
        self.assertNotEqual(first["source_id"], second["source_id"])

    def test_nested_paths_are_relative_and_do_not_leak_temp_root(self) -> None:
        self.write_text("nested/guide.txt", "hello")

        manifest = self.scan()

        self.assertEqual("nested/guide.txt", manifest["documents"][0]["relative_path"])
        self.assertEqual(".", manifest["root"])
        self.assertNotIn(self.temporary.name, json.dumps(manifest))

    def test_output_inside_input_is_refused(self) -> None:
        self.write_text("guide.txt", "hello")
        output = self.root / "manifest.json"

        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            subject.main([str(self.root), "--output", str(output)])

        self.assertEqual(2, caught.exception.code)
        self.assertFalse(output.exists())

    def test_explicit_output_outside_input_is_valid_json(self) -> None:
        self.write_text("guide.txt", "hello")
        output = Path(self.temporary.name) / "manifest.json"

        exit_code = subject.main([str(self.root), "--output", str(output)])
        manifest = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(0, exit_code)
        self.assertEqual("pass", manifest["summary"]["gate"])

    def test_schema_file_declares_required_manifest_fields(self) -> None:
        schema_path = Path(__file__).with_name("document-manifest.schema.json")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        self.assertEqual("https://json-schema.org/draft/2020-12/schema", schema["$schema"])
        self.assertEqual("2.0", schema["properties"]["schema_version"]["const"])
        self.assertEqual(
            {
                "schema_version",
                "parser",
                "config",
                "config_sha256",
                "root",
                "documents",
                "summary",
                "issues",
            },
            set(schema["required"]),
        )
        document = schema["$defs"]["document"]
        self.assertIn("parse_revision_sha256", document["required"])
        self.assertEqual(
            "normalized-text-lines-1-based-inclusive-v1",
            schema["$defs"]["element"]["properties"]["location"]["properties"]
            ["coordinate_space"]["const"],
        )


def codecs_utf16(text: str) -> bytes:
    return text.encode("utf-16")


if __name__ == "__main__":
    unittest.main()
