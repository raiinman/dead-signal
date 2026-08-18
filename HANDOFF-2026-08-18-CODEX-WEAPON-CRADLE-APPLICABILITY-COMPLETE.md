# Dead Signal — Weapon Cradle Applicability Complete

> Date: 2026-08-18 America/Phoenix  
> Implementation commit: `a266494`  
> Stable Miner remains: `v1.5.14.62`

Read after `PROJECT-RULES.md`, `HANDOFF-2026-08-18-CODEX-LOCAL-TAKEOVER.md`, and `HANDOFF-2026-08-18-CODEX-WEAPON-CRADLE-APPLICABILITY.md`.

## Result

The Weapons Cradle-applicability lane is complete at the installed `.62` evidence boundary. No broad scan was run. The implementation queried the persistent table and consumer indexes, then inspected only exact Cradle configuration, entry, Buff, Logic Tree, item-owner, and indexed consumer records.

The active model is:

- 14 current configuration records reference 87 unique active Cradle entries;
- active entry IDs resolve exactly to Cradle entry records and Buff owners;
- recursive, bounded Buff traversal resolves exact Logic Tree owners;
- `hold_item_check` selectors map to exact installed item `type` / `sub_type` fields;
- season and configuration identities are preserved rather than inferred from record existence;
- raw attack/formula/keyword/melee selector branches remain unresolved unless an exact `hold_item_check` also proves a relation.

Static consumer proof is recorded from the indexed `ui/data_model/UIEquipmentData.pyc` scope `get_show_equip_preset_cradle`. It co-locates active configuration lookup with entry/style/keyword consumption. Game bytecode was never executed.

## Applicability counts

Across 120 canonical Weapons and 87 active Cradles:

- 8 Cradles have exact weapon selectors;
- 17 Cradles have weapon-related selectors that remain unresolved;
- 62 Cradles are not weapon-selected (this is not a claim that their effects are inactive);
- 287 weapon–Cradle pairs are `compatible-exact`;
- 673 pairs are `incompatible-exact`;
- 2,040 pairs are `unresolved`;
- 7,440 pairs are `not-applicable` / not weapon-selected.

All nine canonical weapon categories were exercised by exact controls: Assault Rifle, Bow, Heavy, LMG, Melee, Pistol, Shotgun, Sniper Rifle, and SMG.

## Canonical integration

- `dead_signal_cradle_applicability.py` is a bounded analyzer and report producer.
- `miner_entry.py` runs it after normalization and before later publication stages.
- normalized Weapons and Cradles retain compact applicability/configuration evidence.
- web, extended-web, and Weapons v2 site projections preserve the relation.
- the lean feed receives compact statuses; detailed proof remains in the evidence/report path.
- semantic registry and coverage dashboard now recognize the relation.
- self-diagnostics block overlapping status sets or resolved records without exact item selectors.
- the typed reference graph records only proven positive and negative relations; unresolved and not-applicable cases are not promoted.

Local report:

`C:\Users\mikea\Documents\Dead Signal Miner\published\reports\weapon-cradle-applicability.json`

Local validation produced 120/120 resolved Weapon applicability records, zero self-diagnostic blockers, 287 compatible graph edges, and 673 incompatible graph edges.

## Tests

- Focused Cradle/publication/UI tests: 19 passed during development.
- Full Miner source suite: 189 passed.
- `git diff --check`: clean (line-ending notices only).

The untracked `tools/miner.zip` was not touched. No Miner release was cut.

## Remaining boundary

The 17 unresolved active Cradles intentionally remain unresolved because their weapon relation is expressed through raw selectors whose installed semantics are not yet exact enough for publication. Do not turn them into negative results and do not use English descriptions to decode them.

Return to the Weapons launch queue and select the next lane from the updated coverage dashboard. Likely candidates remain Attachment compatibility, Calibration compatibility, selectable Ammo, acquisition edge cases, melee display semantics, variant lineage, and the remaining description conflict.
