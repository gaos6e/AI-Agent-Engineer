"""Validate a synthetic media manifest and build an offline evidence plan.

The router never opens media paths and never calls a model or network service.
Its cost units are teaching-only estimates, not vendor prices or token counts.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


PRIVACY_CLASSES = {"public", "internal", "personal", "restricted"}
SUPPORTED_MODALITIES = {"image", "audio", "video", "document", "text"}


class ManifestError(ValueError):
    """Raised when the manifest itself is structurally invalid."""


def load_manifest(path: Path) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ManifestError(f"non-standard JSON constant is forbidden: {value}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ManifestError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestError(f"cannot read {path}: {exc}") from exc
    try:
        data = json.loads(
            text,
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicate_keys,
        )
    except ManifestError:
        raise
    except json.JSONDecodeError as exc:
        raise ManifestError(f"invalid JSON in {path}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ManifestError("manifest root must be an object")
    return data


def positive_int(value: Any, field: str, *, allow_zero: bool = False) -> int:
    minimum = 0 if allow_zero else 1
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < minimum
    ):
        comparator = "non-negative" if allow_zero else "positive"
        raise ManifestError(f"{field} must be a {comparator} integer")
    return value


def modality_for(mime: str) -> str | None:
    if mime == "application/pdf":
        return "document"
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("audio/"):
        return "audio"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("text/"):
        return "text"
    return None


PROCESSING_PLAN: dict[str, dict[str, list[str]]] = {
    "image": {
        "processors": ["image_decoder", "ocr"],
        "evidence_kinds": ["image_region"],
    },
    "audio": {
        "processors": ["audio_decoder", "asr", "timestamp_index"],
        "evidence_kinds": ["audio_interval"],
    },
    "video": {
        "processors": [
            "video_probe",
            "scene_sampler",
            "audio_extractor",
            "timestamp_index",
        ],
        "evidence_kinds": ["video_interval", "frame_region"],
    },
    "document": {
        "processors": ["document_parser", "layout_extractor"],
        "evidence_kinds": ["page_region"],
    },
    "text": {
        "processors": ["text_parser"],
        "evidence_kinds": ["text_span"],
    },
}


class MultimodalRouter:
    """Build a deterministic plan from metadata and policy."""

    def __init__(self, manifest: dict[str, Any]) -> None:
        if not isinstance(manifest, dict) or set(manifest) != {
            "policy", "query", "assets"
        }:
            raise ManifestError(
                "manifest fields must be exactly: policy, query, assets"
            )
        self.policy = self._validate_policy(manifest.get("policy"))
        self.required_modalities = self._validate_query(manifest.get("query"))
        self.assets = self._validate_assets(manifest.get("assets"))

    @staticmethod
    def _validate_policy(raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise ManifestError("policy must be an object")
        if set(raw) != {
            "allowed_mime",
            "max_bytes_per_asset",
            "budget_units",
            "external_processing_allowed_for",
        }:
            raise ManifestError("policy fields do not match the frozen contract")
        allowed_mime = raw.get("allowed_mime")
        if (
            not isinstance(allowed_mime, list)
            or not allowed_mime
            or not all(isinstance(item, str) and item for item in allowed_mime)
        ):
            raise ManifestError("policy.allowed_mime must be non-empty strings")
        if len(allowed_mime) != len(set(allowed_mime)):
            raise ManifestError("policy.allowed_mime must not contain duplicates")
        external = raw.get("external_processing_allowed_for", [])
        if (
            not isinstance(external, list)
            or not all(item in PRIVACY_CLASSES for item in external)
        ):
            raise ManifestError(
                "policy.external_processing_allowed_for has an unknown class"
            )
        if len(external) != len(set(external)):
            raise ManifestError(
                "policy.external_processing_allowed_for must not contain duplicates"
            )
        return {
            "allowed_mime": set(allowed_mime),
            "max_bytes_per_asset": positive_int(
                raw.get("max_bytes_per_asset"), "policy.max_bytes_per_asset"
            ),
            "budget_units": positive_int(
                raw.get("budget_units"), "policy.budget_units"
            ),
            "external_processing_allowed_for": set(external),
        }

    @staticmethod
    def _validate_query(raw: Any) -> list[str]:
        if not isinstance(raw, dict):
            raise ManifestError("query must be an object")
        if set(raw) != {"required_modalities"}:
            raise ManifestError("query fields do not match the frozen contract")
        required = raw.get("required_modalities")
        if (
            not isinstance(required, list)
            or not required
            or not all(item in SUPPORTED_MODALITIES for item in required)
        ):
            raise ManifestError("query.required_modalities contains invalid values")
        if len(set(required)) != len(required):
            raise ManifestError("query.required_modalities contains duplicates")
        return list(required)

    @staticmethod
    def _validate_assets(raw: Any) -> list[dict[str, Any]]:
        if not isinstance(raw, list) or not raw:
            raise ManifestError("assets must be a non-empty array")
        assets: list[dict[str, Any]] = []
        seen: set[str] = set()
        required = {
            "asset_id",
            "file_name",
            "declared_mime",
            "detected_mime",
            "bytes",
            "privacy",
        }
        optional_fields = {"duration_ms", "width", "height", "pages"}
        for original in raw:
            if not isinstance(original, dict):
                raise ManifestError("every asset must be an object")
            missing = required - original.keys()
            if missing:
                raise ManifestError(f"asset is missing fields: {sorted(missing)}")
            unknown = set(original) - required - optional_fields
            if unknown:
                raise ManifestError(f"asset has unknown fields: {sorted(unknown)}")
            asset = deepcopy(original)
            asset_id = asset["asset_id"]
            if not isinstance(asset_id, str) or not asset_id:
                raise ManifestError("asset_id must be a non-empty string")
            if asset_id in seen:
                raise ManifestError(f"duplicate asset_id: {asset_id}")
            seen.add(asset_id)
            for field in ("file_name", "declared_mime", "detected_mime"):
                if not isinstance(asset[field], str) or not asset[field]:
                    raise ManifestError(f"{asset_id}.{field} must be a string")
            asset["bytes"] = positive_int(asset["bytes"], f"{asset_id}.bytes")
            if asset["privacy"] not in PRIVACY_CLASSES:
                raise ManifestError(f"{asset_id}.privacy is unknown")
            for optional_field in ("duration_ms", "width", "height", "pages"):
                if optional_field in asset:
                    asset[optional_field] = positive_int(
                        asset[optional_field], f"{asset_id}.{optional_field}"
                    )
            assets.append(asset)
        return assets

    def _privacy_action(self, privacy: str) -> str:
        if privacy == "restricted":
            return "local_only"
        allowed = self.policy["external_processing_allowed_for"]
        if privacy not in allowed:
            return "local_only"
        if privacy == "personal":
            return "redact_then_external"
        return "external_allowed"

    @staticmethod
    def _estimate_units(asset: dict[str, Any], modality: str) -> int:
        units = max(1, math.ceil(asset["bytes"] / 1_000_000))
        if modality in {"audio", "video"}:
            duration = positive_int(
                asset.get("duration_ms"), f"{asset['asset_id']}.duration_ms"
            )
            units += math.ceil(duration / 30_000)
        if modality in {"image", "video"}:
            width = positive_int(
                asset.get("width"), f"{asset['asset_id']}.width"
            )
            height = positive_int(
                asset.get("height"), f"{asset['asset_id']}.height"
            )
            units += math.ceil((width * height) / 1_000_000)
        if modality == "document":
            pages = positive_int(
                asset.get("pages"), f"{asset['asset_id']}.pages"
            )
            units += math.ceil(pages / 5)
        return units

    def build_plan(self) -> dict[str, Any]:
        errors: list[str] = []
        planned: list[dict[str, Any]] = []
        present_modalities: set[str] = set()
        total_units = 0
        for asset in self.assets:
            asset_id = asset["asset_id"]
            if asset["declared_mime"] != asset["detected_mime"]:
                errors.append(f"mime_mismatch:{asset_id}")
                continue
            mime = asset["detected_mime"]
            if mime not in self.policy["allowed_mime"]:
                errors.append(f"mime_not_allowed:{asset_id}:{mime}")
                continue
            if asset["bytes"] > self.policy["max_bytes_per_asset"]:
                errors.append(f"asset_too_large:{asset_id}")
                continue
            modality = modality_for(mime)
            if modality is None:
                errors.append(f"unsupported_modality:{asset_id}:{mime}")
                continue
            try:
                units = self._estimate_units(asset, modality)
            except ManifestError as error:
                errors.append(f"invalid_media_metadata:{asset_id}:{error}")
                continue
            present_modalities.add(modality)
            total_units += units
            template = PROCESSING_PLAN[modality]
            planned.append(
                {
                    "asset_id": asset_id,
                    "file_name": asset["file_name"],
                    "modality": modality,
                    "processors": list(template["processors"]),
                    "evidence_kinds": list(template["evidence_kinds"]),
                    "privacy_action": self._privacy_action(asset["privacy"]),
                    "cost_units": units,
                }
            )
        for modality in self.required_modalities:
            if modality not in present_modalities:
                errors.append(f"missing_required_modality:{modality}")
        if total_units > self.policy["budget_units"]:
            errors.append(
                f"budget_exceeded:{total_units}>{self.policy['budget_units']}"
            )
        return {
            "status": "ready" if not errors else "blocked",
            "required_modalities": list(self.required_modalities),
            "present_modalities": sorted(present_modalities),
            "total_cost_units": total_units,
            "budget_units": self.policy["budget_units"],
            "assets": planned,
            "errors": errors,
            "notes": [
                "cost_units are synthetic teaching estimates",
                "no media file was opened",
                "no network or model call was made",
                (
                    "asset privacy labels are synthetic teaching inputs; production "
                    "must resolve classification from a trusted policy record"
                ),
            ],
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="UTF-8 synthetic manifest")
    parser.add_argument(
        "--output", type=Path, help="optional JSON report path; stdout is always used"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = MultimodalRouter(load_manifest(args.manifest)).build_plan()
        rendered = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    except ManifestError as exc:
        print(f"manifest error: {exc}", file=sys.stderr)
        return 2

    if args.output is not None:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"output error: {exc}", file=sys.stderr)
            return 2
    print(rendered)
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
