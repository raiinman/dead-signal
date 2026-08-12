"""Attach extracted web artwork to every published Dead Signal data record."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath


IGNORED_FILES = {"reference-images.json", "image-coverage.json"}


def stem(value: str) -> str:
    filename = PureWindowsPath(value.replace("/", "\\")).name.strip()
    return Path(filename).stem.casefold()


def write_json(path: Path, payload) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def link_record_images(value, lookup: dict[str, str], counts: dict) -> None:
    if isinstance(value, list):
        for child in value:
            link_record_images(child, lookup, counts)
        return
    if not isinstance(value, dict):
        return

    # Weapons and Armor predate the common contract and expose `icon` directly.
    # Give identifiable content rows the same image_reference field as every new
    # category without disturbing technical dictionaries that happen to use icons.
    if not value.get("image_reference") and value.get("name"):
        for candidate in ("icon", "icon_path", "forge_icon", "pal_icon", "skill_icon"):
            reference = value.get(candidate)
            if isinstance(reference, str) and reference.strip():
                value["image_reference"] = reference.strip()
                break

    reference_fields = [
        key
        for key, child in value.items()
        if (key == "image_reference" or key.endswith("_image_reference"))
        and isinstance(child, str)
    ]
    if (value.get("id") is not None or value.get("item_id") is not None or value.get("name")):
        counts["records_with_identity"] += 1
        if not reference_fields:
            counts["records_without_image_reference"] += 1

    for field in reference_fields:
        reference = value[field].strip()
        asset_field = field.replace("_reference", "_asset")
        status_field = field.replace("_reference", "_status")
        if not reference:
            value[asset_field] = None
            value[status_field] = "no-reference"
            counts["empty_image_references"] += 1
            continue
        counts["image_references"] += 1
        asset = lookup.get(stem(reference))
        value[asset_field] = asset
        if asset:
            value[status_field] = "resolved"
            counts["resolved_image_references"] += 1
        else:
            value[status_field] = "unresolved"
            counts["unresolved_image_references"] += 1

    for child in list(value.values()):
        if isinstance(child, (dict, list)):
            link_record_images(child, lookup, counts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    lookup = manifest.get("lookup", {})
    if not isinstance(lookup, dict) or not lookup:
        raise RuntimeError("The reference artwork manifest has no usable lookup table")

    files = {}
    totals = {
        "records_with_identity": 0,
        "records_without_image_reference": 0,
        "image_references": 0,
        "empty_image_references": 0,
        "resolved_image_references": 0,
        "unresolved_image_references": 0,
    }
    for path in sorted(args.data_dir.glob("*.json")):
        if path.name in IGNORED_FILES:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        counts = {key: 0 for key in totals}
        link_record_images(payload, lookup, counts)
        payload["image_coverage"] = counts
        write_json(path, payload)
        files[path.name] = counts
        for key, amount in counts.items():
            totals[key] += amount

    report = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "artwork_manifest": str(args.manifest.resolve()),
        "manifest_assets": len(lookup),
        "files": files,
        "totals": totals,
    }
    output = args.output or args.data_dir / "image-coverage.json"
    write_json(output, report)
    print(json.dumps(report["totals"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
