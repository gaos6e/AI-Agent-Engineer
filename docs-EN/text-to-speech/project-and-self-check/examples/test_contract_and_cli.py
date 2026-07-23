from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from build_tts_plan import (
    FixtureError,
    SSML_NAMESPACE,
    build_plan,
    build_ssml,
    load_fixture,
    qname,
    validate_fixture,
    validate_generated_ssml,
)


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "build_tts_plan.py"
FIXTURE = HERE / "tts_requests.json"


def valid_payload() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TemporaryFileCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="tts-test-", dir=HERE)
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "fixture.json"

    def write_text(self, text: str) -> Path:
        self.path.write_text(text, encoding="utf-8")
        return self.path

    def write_payload(self, payload: object) -> Path:
        return self.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False))


class StrictJsonTests(TemporaryFileCase):
    def test_loads_valid_fixture(self) -> None:
        self.assertEqual(load_fixture(FIXTURE)["schema_version"], "1.1")

    def test_rejects_duplicate_key(self) -> None:
        raw = FIXTURE.read_text(encoding="utf-8").replace(
            '"schema_version": "1.1",',
            '"schema_version": "1.1", "schema_version": "1.1",',
            1,
        )
        with self.assertRaisesRegex(FixtureError, "duplicate JSON key"):
            load_fixture(self.write_text(raw))

    def test_rejects_nan(self) -> None:
        raw = FIXTURE.read_text(encoding="utf-8").replace("500", "NaN", 1)
        with self.assertRaisesRegex(FixtureError, "non-finite"):
            load_fixture(self.write_text(raw))

    def test_rejects_infinity(self) -> None:
        raw = FIXTURE.read_text(encoding="utf-8").replace("500", "Infinity", 1)
        with self.assertRaisesRegex(FixtureError, "non-finite"):
            load_fixture(self.write_text(raw))

    def test_rejects_malformed_json(self) -> None:
        with self.assertRaisesRegex(FixtureError, "invalid JSON"):
            load_fixture(self.write_text("{"))

    def test_rejects_missing_file(self) -> None:
        with self.assertRaisesRegex(FixtureError, "cannot read fixture"):
            load_fixture(self.path)

    def test_rejects_invalid_utf8(self) -> None:
        self.path.write_bytes(b"\xff\xfe")
        with self.assertRaisesRegex(FixtureError, "cannot read fixture"):
            load_fixture(self.path)

    def test_rejects_non_object_root(self) -> None:
        with self.assertRaisesRegex(FixtureError, "fixture must be an object"):
            load_fixture(self.write_text("[]"))


class TopAndPolicyContractTests(unittest.TestCase):
    def assert_invalid(self, payload: object, pattern: str) -> None:
        with self.assertRaisesRegex(FixtureError, pattern):
            validate_fixture(payload)

    def test_accepts_valid_payload(self) -> None:
        self.assertEqual(len(validate_fixture(valid_payload())["requests"]), 2)

    def test_top_missing_field(self) -> None:
        payload = valid_payload()
        del payload["policy"]
        self.assert_invalid(payload, "missing fields")

    def test_top_unknown_field(self) -> None:
        payload = valid_payload()
        payload["provider"] = "demo"
        self.assert_invalid(payload, "unknown fields")

    def test_wrong_schema_version(self) -> None:
        payload = valid_payload()
        payload["schema_version"] = "2.0"
        self.assert_invalid(payload, "schema_version")

    def test_policy_must_be_object(self) -> None:
        payload = valid_payload()
        payload["policy"] = []
        self.assert_invalid(payload, "policy must be an object")

    def test_policy_missing_field(self) -> None:
        payload = valid_payload()
        del payload["policy"]["allowed_rates"]
        self.assert_invalid(payload, "missing fields")

    def test_policy_unknown_field(self) -> None:
        payload = valid_payload()
        payload["policy"]["default_voice"] = "demo"
        self.assert_invalid(payload, "unknown fields")

    def test_max_characters_rejects_boolean(self) -> None:
        payload = valid_payload()
        payload["policy"]["max_characters"] = True
        self.assert_invalid(payload, "positive integer")

    def test_max_characters_rejects_zero(self) -> None:
        payload = valid_payload()
        payload["policy"]["max_characters"] = 0
        self.assert_invalid(payload, "positive integer")

    def test_voice_catalog_must_be_array(self) -> None:
        payload = valid_payload()
        payload["policy"]["voice_catalog"] = "demo"
        self.assert_invalid(payload, "non-empty array")

    def test_voice_catalog_rejects_duplicate_voice_id(self) -> None:
        payload = valid_payload()
        payload["policy"]["voice_catalog"].append(
            payload["policy"]["voice_catalog"][0].copy()
        )
        self.assert_invalid(payload, "voice_id values must be unique")

    def test_voice_catalog_rejects_invalid_supported_locale(self) -> None:
        payload = valid_payload()
        payload["policy"]["voice_catalog"][0]["supported_locales"] = ["zh_CN"]
        self.assert_invalid(payload, "supported_locales")

    def test_allowlist_must_not_be_empty(self) -> None:
        payload = valid_payload()
        payload["policy"]["allowed_rates"] = []
        self.assert_invalid(payload, "non-empty array")

    def test_allowlist_items_must_be_strings(self) -> None:
        payload = valid_payload()
        payload["policy"]["allowed_emphasis"] = [1]
        self.assert_invalid(payload, "non-empty strings")

    def test_allowlist_items_must_be_unique(self) -> None:
        payload = valid_payload()
        payload["policy"]["allowed_rates"] = ["medium", "medium"]
        self.assert_invalid(payload, "unique")

    def test_policy_revision_must_be_non_empty(self) -> None:
        payload = valid_payload()
        payload["policy"]["policy_revision"] = " "
        self.assert_invalid(payload, "policy_revision")

    def test_disclosure_required_must_be_boolean(self) -> None:
        payload = valid_payload()
        payload["policy"]["disclosure_required"] = "yes"
        self.assert_invalid(payload, "disclosure_required")

    def test_requests_must_be_array(self) -> None:
        payload = valid_payload()
        payload["requests"] = {}
        self.assert_invalid(payload, "non-empty array")

    def test_requests_must_not_be_empty(self) -> None:
        payload = valid_payload()
        payload["requests"] = []
        self.assert_invalid(payload, "non-empty array")


class RequestContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = valid_payload()

    @property
    def request(self) -> dict[str, Any]:
        return self.payload["requests"][0]

    def assert_invalid(self, pattern: str) -> None:
        with self.assertRaisesRegex(FixtureError, pattern):
            validate_fixture(self.payload)

    def test_request_must_be_object(self) -> None:
        self.payload["requests"][0] = []
        self.assert_invalid("must be an object")

    def test_request_missing_field(self) -> None:
        del self.request["rate"]
        self.assert_invalid("missing fields")

    def test_request_unknown_field(self) -> None:
        self.request["pitch"] = "high"
        self.assert_invalid("unknown fields")

    def test_each_field_must_be_string(self) -> None:
        for field in list(self.request):
            with self.subTest(field=field):
                payload = valid_payload()
                payload["requests"][0][field] = 1
                with self.assertRaisesRegex(FixtureError, field):
                    validate_fixture(payload)

    def test_each_field_must_be_non_empty(self) -> None:
        for field in list(self.request):
            with self.subTest(field=field):
                payload = valid_payload()
                payload["requests"][0][field] = "  "
                with self.assertRaisesRegex(FixtureError, field):
                    validate_fixture(payload)

    def test_locale_rejects_underscore(self) -> None:
        self.request["locale"] = "zh_CN"
        self.assert_invalid("BCP 47 teaching subset")

    def test_locale_rejects_one_letter_language(self) -> None:
        self.request["locale"] = "z-CN"
        self.assert_invalid("BCP 47 teaching subset")

    def test_locale_accepts_script_and_region(self) -> None:
        self.request["locale"] = "zh-Hans-CN"
        self.assertEqual(validate_fixture(self.payload)["requests"][0]["locale"], "zh-Hans-CN")


class SsmlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = valid_payload()["requests"][0]

    def test_builds_ssml_11_root(self) -> None:
        root = ET.fromstring(build_ssml(self.request))
        self.assertEqual(root.tag, qname("speak"))
        self.assertEqual(root.attrib["version"], "1.1")

    def test_sets_xml_language(self) -> None:
        root = ET.fromstring(build_ssml(self.request))
        self.assertEqual(
            root.attrib["{http://www.w3.org/XML/1998/namespace}lang"], "zh-CN"
        )

    def test_preserves_text_through_xml_round_trip(self) -> None:
        ssml = build_ssml(self.request)
        self.assertIn("&amp;", ssml)
        self.assertIn("&lt;", ssml)
        self.assertEqual("".join(ET.fromstring(ssml).itertext()), self.request["source_text"])

    def test_markup_like_source_remains_text(self) -> None:
        self.request["source_text"] = '<audio src="https://example.invalid/x"/>'
        root = ET.fromstring(build_ssml(self.request))
        self.assertNotIn(qname("audio"), [element.tag for element in root.iter()])
        self.assertEqual("".join(root.itertext()), self.request["source_text"])

    def test_medium_rate_omits_prosody(self) -> None:
        root = ET.fromstring(build_ssml(self.request))
        self.assertNotIn(qname("prosody"), [element.tag for element in root.iter()])

    def test_non_medium_rate_adds_prosody(self) -> None:
        self.request["rate"] = "slow"
        root = ET.fromstring(build_ssml(self.request))
        self.assertEqual(root.find(f".//{{{SSML_NAMESPACE}}}prosody").attrib["rate"], "slow")

    def test_none_emphasis_omits_element(self) -> None:
        self.request["emphasis"] = "none"
        root = ET.fromstring(build_ssml(self.request))
        self.assertNotIn(qname("emphasis"), [element.tag for element in root.iter()])

    def test_emphasis_adds_element(self) -> None:
        root = ET.fromstring(build_ssml(self.request))
        emphasis = root.find(f".//{{{SSML_NAMESPACE}}}emphasis")
        self.assertEqual(emphasis.attrib["level"], "moderate")

    def test_generated_ssml_validates(self) -> None:
        self.assertEqual(validate_generated_ssml(build_ssml(self.request)), [])

    def test_invalid_xml_is_rejected(self) -> None:
        self.assertIn("invalid XML", validate_generated_ssml("<speak>" )[0])

    def test_wrong_root_is_rejected(self) -> None:
        errors = validate_generated_ssml("<root/>")
        self.assertIn("root element", " ".join(errors))

    def test_unsupported_tag_is_rejected(self) -> None:
        ssml = (
            f'<speak xmlns="{SSML_NAMESPACE}" version="1.1" xml:lang="en-US">'
            "<audio/></speak>"
        )
        self.assertIn("unsupported generated tag", " ".join(validate_generated_ssml(ssml)))

    def test_unknown_attribute_is_rejected(self) -> None:
        ssml = build_ssml(self.request).replace('version="1.1"', 'version="1.1" bad="x"')
        self.assertIn("unsupported attributes", " ".join(validate_generated_ssml(ssml)))


class PlanTests(unittest.TestCase):
    def test_valid_fixture_builds_two_valid_items(self) -> None:
        plan, errors = build_plan(valid_payload())
        self.assertEqual(errors, [])
        self.assertEqual(len(plan["items"]), 2)
        self.assertTrue(all(item["plan_valid"] for item in plan["items"]))

    def test_plan_never_claims_audio_generation(self) -> None:
        plan, _ = build_plan(valid_payload())
        self.assertFalse(plan["audio_generated"])
        self.assertTrue(all(item["generation_status"] == "not_generated" for item in plan["items"]))

    def test_hash_matches_source_text(self) -> None:
        payload = valid_payload()
        plan, _ = build_plan(payload)
        expected = hashlib.sha256(payload["requests"][0]["source_text"].encode("utf-8")).hexdigest()
        self.assertEqual(plan["items"][0]["source_text_sha256"], expected)

    def test_plan_carries_governance_revisions_without_raw_text_or_ssml(self) -> None:
        payload = valid_payload()
        plan, _ = build_plan(payload)
        item = plan["items"][0]
        self.assertEqual(item["source_revision"], "synthetic-script-zh-v1")
        self.assertEqual(item["acl_reference"], "synthetic-training-audience")
        self.assertEqual(item["policy_revision"], "synthetic-voice-policy-v1")
        self.assertTrue(item["disclosure_required"])
        self.assertNotIn("ssml", set(item))
        self.assertEqual(
            item["ssml_sha256"],
            hashlib.sha256(build_ssml(payload["requests"][0]).encode("utf-8")).hexdigest(),
        )
        rendered_plan = json.dumps(plan, ensure_ascii=False)
        self.assertNotIn(payload["requests"][0]["source_text"], rendered_plan)
        self.assertFalse(plan["source_text_exposed"])

    def test_acl_reference_is_structural_only_in_the_offline_project(self) -> None:
        payload = valid_payload()
        payload["requests"][0]["acl_reference"] = "external-object-acl-not-checked"
        plan, errors = build_plan(payload)
        self.assertEqual(errors, [])
        self.assertEqual(
            plan["items"][0]["acl_reference"], "external-object-acl-not-checked"
        )
        self.assertIn("object authorization was not evaluated", " ".join(plan["notes"]))

    def test_unknown_voice_is_policy_error(self) -> None:
        payload = valid_payload()
        payload["requests"][0]["voice_id"] = "not-allowed"
        plan, errors = build_plan(payload)
        self.assertIn("voice_id is not allowed", " ".join(errors))
        self.assertFalse(plan["items"][0]["plan_valid"])

    def test_mismatched_voice_locale_is_policy_error(self) -> None:
        payload = valid_payload()
        payload["requests"][0]["locale"] = "en-US"
        plan, errors = build_plan(payload)
        self.assertIn("locale is not supported", " ".join(errors))
        self.assertFalse(plan["items"][0]["plan_valid"])

    def test_disallowed_voice_purpose_is_policy_error(self) -> None:
        payload = valid_payload()
        payload["requests"][0]["purpose"] = "advertising"
        plan, errors = build_plan(payload)
        self.assertIn("purpose is not allowed", " ".join(errors))
        self.assertFalse(plan["items"][0]["plan_valid"])

    def test_authorization_reference_must_match_voice_policy(self) -> None:
        payload = valid_payload()
        payload["requests"][0]["authorization_reference"] = "unverified-reference"
        plan, errors = build_plan(payload)
        self.assertIn("authorization_reference does not match", " ".join(errors))
        self.assertFalse(plan["items"][0]["plan_valid"])

    def test_unknown_rate_is_policy_error(self) -> None:
        payload = valid_payload()
        payload["requests"][0]["rate"] = "very-fast"
        plan, errors = build_plan(payload)
        self.assertIn("rate is not allowed", " ".join(errors))
        self.assertFalse(plan["items"][0]["plan_valid"])

    def test_unknown_emphasis_is_policy_error(self) -> None:
        payload = valid_payload()
        payload["requests"][0]["emphasis"] = "shout"
        plan, errors = build_plan(payload)
        self.assertIn("emphasis is not allowed", " ".join(errors))
        self.assertFalse(plan["items"][0]["plan_valid"])

    def test_text_length_is_policy_error(self) -> None:
        payload = valid_payload()
        payload["policy"]["max_characters"] = 3
        plan, errors = build_plan(payload)
        self.assertIn("exceeds max_characters", " ".join(errors))
        self.assertFalse(plan["items"][0]["plan_valid"])

    def test_duplicate_operation_id_is_policy_error(self) -> None:
        payload = valid_payload()
        payload["requests"][1]["operation_id"] = payload["requests"][0]["operation_id"]
        plan, errors = build_plan(payload)
        self.assertIn("duplicate operation_id", " ".join(errors))
        self.assertFalse(plan["items"][1]["plan_valid"])

    def test_provider_request_id_is_not_a_local_contract_field(self) -> None:
        payload = valid_payload()
        payload["requests"][0]["provider_request_id"] = "provider-trace-123"
        with self.assertRaisesRegex(FixtureError, "unknown fields"):
            validate_fixture(payload)

    def test_one_invalid_item_does_not_mark_next_item_invalid(self) -> None:
        payload = valid_payload()
        payload["requests"][0]["voice_id"] = "not-allowed"
        plan, _ = build_plan(payload)
        self.assertFalse(plan["items"][0]["plan_valid"])
        self.assertTrue(plan["items"][1]["plan_valid"])

    def test_plan_revalidates_direct_input(self) -> None:
        payload = valid_payload()
        del payload["requests"][0]["rate"]
        with self.assertRaises(FixtureError):
            build_plan(payload)

    def test_notes_disclose_no_external_effects(self) -> None:
        plan, _ = build_plan(valid_payload())
        notes = " ".join(plan["notes"])
        self.assertIn("no audio", notes)
        self.assertIn("network", notes)
        self.assertIn("no raw source text", notes)
        self.assertIn("object authorization was not evaluated", notes)


class CliTests(TemporaryFileCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            check=False,
        )

    def test_valid_fixture_exit_zero(self) -> None:
        result = self.run_cli(str(FIXTURE))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["errors"], [])
        self.assertNotIn("Welcome to the A&B <test> assistant.", result.stdout)

    def test_policy_error_exit_one(self) -> None:
        payload = valid_payload()
        payload["requests"][0]["voice_id"] = "not-allowed"
        result = self.run_cli(str(self.write_payload(payload)))
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_contract_error_exit_two(self) -> None:
        payload = valid_payload()
        payload["extra"] = True
        result = self.run_cli(str(self.write_payload(payload)))
        self.assertEqual(result.returncode, 2)
        self.assertIn("fixture error", result.stderr)

    def test_missing_file_exit_two(self) -> None:
        self.assertEqual(self.run_cli(str(self.path)).returncode, 2)

    def test_missing_argument_exit_two(self) -> None:
        self.assertEqual(self.run_cli().returncode, 2)

    def test_self_test_exit_zero(self) -> None:
        result = self.run_cli("--self-test")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_output_option_is_not_exposed(self) -> None:
        result = self.run_cli(str(FIXTURE), "--output", "report.json")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((HERE / "report.json").exists())

    def test_production_code_has_no_assert_statement(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))


if __name__ == "__main__":
    unittest.main()
