#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path

ASSIGN_RE = re.compile(r'^(\s*window\.DS_COMMUNITY\s*=\s*)(\{.*\})(\s*;?\s*)$', re.S)
HASHED_STEM_RE = re.compile(r'^(.*)-([0-9a-f]{12})$', re.I)

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
        raise SystemExit(f'player image pack not found: {assets_root}')

    text = data_file.read_text(encoding='utf-8')
    m = ASSIGN_RE.match(text)
    if not m:
        raise SystemExit('community-data.js is not a recognized window.DS_COMMUNITY assignment')
    data = json.loads(m.group(2))

    by_logical: dict[str, str] = {}
    ambiguous: set[str] = set()
    for p in assets_root.rglob('*'):
        if not p.is_file():
            continue
        stem = p.stem
        hm = HASHED_STEM_RE.match(stem)
        logical = hm.group(1) if hm else stem
        rel = p.relative_to(root).as_posix()
        if logical in by_logical and by_logical[logical] != rel:
            ambiguous.add(logical)
        else:
            by_logical[logical] = rel
    for key in ambiguous:
        by_logical.pop(key, None)

    patched = 0
    already = 0
    unresolved: list[str] = []
    for category, records in data.items():
        if not isinstance(records, list):
            continue
        for rec in records:
            if not isinstance(rec, dict):
                continue
            if rec.get('imageAsset'):
                already += 1
                continue
            ref = str(rec.get('imageRef') or '').strip().replace('\\', '/')
            if not ref:
                continue
            logical = Path(ref).stem
            asset = by_logical.get(logical)
            if asset:
                rec['imageAsset'] = asset
                patched += 1
            else:
                unresolved.append(f"{category}:{rec.get('name') or rec.get('id') or logical}:{ref}")

    out = m.group(1) + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + m.group(3)
    data_file.write_text(out, encoding='utf-8')

    print(f'Dead Signal player image resolver: indexed={len(by_logical)} patched={patched} already={already} unresolved={len(unresolved)}')
    if ambiguous:
        print(f'ambiguous logical image keys skipped: {len(ambiguous)}')
    if unresolved:
        report = root / 'data' / 'image-unresolved-v1.3.txt'
        report.write_text('\n'.join(unresolved) + '\n', encoding='utf-8')
        print(f'unresolved image report: {report}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
