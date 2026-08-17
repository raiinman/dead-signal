# Dead Signal Weapons Corpus Audit Handoff — 2026-08-17

## Objective

Run one unattended overnight Data Intelligence compile that measures every canonical weapon against a competitor-grade player-facing field contract while preserving Dead Signal's exact installed-game evidence rules.

## Miner version

Target release: `1.5.14.50`

## New analyzer

`tools/miner/src/dead_signal_weapon_corpus_audit.py`

Integrated into the normal **COMPILE DATA INTELLIGENCE** path in:

`tools/miner/src/dead_signal_intelligence_compiler.py`

Output report:

`published/reports/weapon-corpus-audit.json`

The normal Intelligence ZIP includes this report automatically.

## Coverage contract

Competitor baseline research targets:

- damage
- fire rate
- magazine
- range
- reload
- mobility
- ADS time
- bullet / projectile speed
- damage falloff
- ammo
- firing mode
- description
- special skill
- crafting
- acquisition

Dead Signal advantage targets:

- accuracy
- stability
- projectile / pellet count
- durability
- weight
- perk / calibration slots
- attachment compatibility
- calibration compatibility
- image identity

Competitor sites are gap detectors only. They are never publication truth.

## Exact corpus scan

The audit starts with canonical weapon identities from `published/data/weapons.json` and derives exact identity seeds including:

- blueprint ID
- item ID
- prototype ID
- fragment ID
- tier item IDs
- tier gun IDs
- ammo item IDs
- bullet-pattern ID where present

Both retained Base and Current NeoX JSON snapshot layers are scanned. A record is associated with a weapon only when one of those exact identity scalar values occurs in the record. Similar IDs and name matches do not qualify.

For exact matched records, field names are classified into the player-facing coverage families above. Candidate values remain research-only.

## PYC consumer scan

When snapshot metadata exposes retained raw source roots, every retained `.pyc` file is scanned for exact relevant stat/handling/compatibility symbol bytes. Compatible PYC payloads are unmarshaled for static `CodeType` metadata only.

No game module or game bytecode is executed.

## Report shape

`weapon-corpus-audit.json` contains:

- global record counts
- coverage contract
- group summary
- ranked `gap_queue`
- per-weapon coverage state
- per-weapon exact corpus evidence
- top exact-match tables
- PYC consumer candidates grouped by field family
- evidence / publication policy

Coverage states include:

- `published`
- `published-partial`
- `candidate-evidence-found`
- `unresolved-evidence-state`
- `missing`
- `not-applicable`

## Priority behavior

Player-facing competitor baseline gaps rank above Dead Signal bonus fields. Gaps with exact corpus candidates receive an additional priority boost so the next research pass starts with actionable evidence rather than blind searching.

## Run instructions

1. Update Miner to `1.5.14.50`.
2. Open Data Intelligence.
3. Run **COMPILE DATA INTELLIGENCE** against the existing completed snapshot.
4. Leave the scan running unattended. It intentionally walks the complete retained Base + Current JSON corpus and retained PYC roots.
5. When complete, upload the resulting `Dead-Signal-Intelligence-*.zip`.
6. Review `published/reports/weapon-corpus-audit.json` first, especially `group_summary` and `gap_queue`.

## Interpretation rules

- Exact installed-game evidence remains authoritative.
- Candidate field co-occurrence is a locator, not automatic semantic proof.
- No fuzzy name or similar-ID promotion.
- Missing recipe evidence does not prove non-craftable.
- Missing mechanic ownership does not prove no player-facing mechanic.
- No candidate found does not prove the game lacks the concept.
- Nothing from this audit automatically rewrites published weapon data.

## Regression coverage

`tools/miner/tests/test_weapon_corpus_audit.py`

The regression fixture explicitly verifies that exact gun ID `888` does not inherit candidate evidence from similar ID `8880`, and that newly modeled ADS-time / bullet-speed evidence can be discovered without automatic publication.
