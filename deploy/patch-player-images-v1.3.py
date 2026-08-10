#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ASSIGN_RE = re.compile(r'^(\s*window\.DS_COMMUNITY\s*=\s*)(\{.*\})(\s*;?\s*)$', re.S)
HASHED_STEM_RE = re.compile(r'^(.*)-([0-9a-f]{12})$', re.I)
WEB_PREFIX = '/build-planner/'
MEDIA_FIELDS = ('imageUrl', 'imageAsset', 'imageRef', 'image', 'iconUrl', 'icon', 'assetPath', 'imagePath')


def clean_candidate(value: object) -> str:
    return str(value or '').strip().replace('\\', '/').split('?', 1)[0].split('#', 1)[0]


def logical_stem(value: str) -> str:
    stem = Path(value).stem
    match = HASHED_STEM_RE.match(stem)
    return match.group(1) if match else stem


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: patch-player-images-v1.3.py <deploy-path>', file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    data_file = root / 'data' / 'community-data.js'
    assets_root = root / 'assets' / 'reference-images'

    if not data_file.is_file():
        raise SystemExit(f'community data not found: {data_file}')
    if not assets_root.is_dir():
        raise SystemExit(f'player image directory not found: {assets_root}')

    text = data_file.read_text(encoding='utf-8')
    match = ASSIGN_RE.match(text)
    if not match:
        raise SystemExit('community-data.js is not a recognized window.DS_COMMUNITY assignment')
    data = json.loads(match.group(2))

    by_filename: dict[str, str] = {}
    filename_ambiguous: set[str] = set()
    by_logical: dict[str, str] = {}
    logical_ambiguous: set[str] = set()

    for path in assets_root.rglob('*'):
        if not path.is_file():
            continue

        rel_from_root = path.relative_to(root).as_posix()
        web_url = WEB_PREFIX + rel_from_root

        filename = path.name.lower()
        if filename in by_filename and by_filename[filename] != web_url:
            filename_ambiguous.add(filename)
        else:
            by_filename[filename] = web_url

        logical = logical_stem(path.name).lower()
        if logical in by_logical and by_logical[logical] != web_url:
            logical_ambiguous.add(logical)
        else:
            by_logical[logical] = web_url

    for key in filename_ambiguous:
        by_filename.pop(key, None)
    for key in logical_ambiguous:
        by_logical.pop(key, None)

    def resolve_record(rec: dict) -> str:
        candidates = [clean_candidate(rec.get(field)) for field in MEDIA_FIELDS]
        candidates = [candidate for candidate in candidates if candidate]

        # First honor an exact path beneath reference-images if it exists on disk.
        for candidate in candidates:
            marker = 'reference-images/'
            pos = candidate.lower().find(marker)
            if pos >= 0:
                suffix = candidate[pos + len(marker):]
                exact = assets_root / suffix
                if exact.is_file():
                    return WEB_PREFIX + exact.relative_to(root).as_posix()

        # Then resolve by exact physical filename.
        for candidate in candidates:
            hit = by_filename.get(Path(candidate).name.lower())
            if hit:
                return hit

        # Finally resolve miner logical filenames to the hashed production file.
        for candidate in candidates:
            hit = by_logical.get(logical_stem(candidate).lower())
            if hit:
                return hit

        return ''

    resolved = 0
    normalized = 0
    unresolved: list[str] = []

    for category, records in data.items():
        if not isinstance(records, list):
            continue
        for rec in records:
            if not isinstance(rec, dict):
                continue

            has_media_hint = any(clean_candidate(rec.get(field)) for field in MEDIA_FIELDS)
            url = resolve_record(rec)
            if url:
                resolved += 1
                if rec.get('imageAsset') != url or rec.get('imageUrl') != url:
                    normalized += 1
                # imageUrl is intentionally set too because the presentation layer
                # gives it first priority. Both fields now point at the hosted asset.
                rec['imageAsset'] = url
                rec['imageUrl'] = url
            elif has_media_hint:
                label = rec.get('name') or rec.get('id') or 'unknown'
                hints = ' | '.join(clean_candidate(rec.get(field)) for field in MEDIA_FIELDS if clean_candidate(rec.get(field)))
                unresolved.append(f'{category}:{label}:{hints}')

    out = match.group(1) + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + match.group(3)
    data_file.write_text(out, encoding='utf-8')

    print(
        'Dead Signal player image resolver: '
        f'physical={len(list(assets_root.rglob("*.png")))} '
        f'resolved_records={resolved} normalized_records={normalized} '
        f'unresolved_records={len(unresolved)}'
    )

    report = root / 'data' / 'image-unresolved-v1.3.txt'
    if unresolved:
        report.write_text('\n'.join(unresolved) + '\n', encoding='utf-8')
        print(f'unresolved image report: {report}')
    elif report.exists():
        report.unlink()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
