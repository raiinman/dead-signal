# Dead Signal — Weapon Identity Spine Complete

## Status

The Weapon Identity Spine implementation is complete on canonical `main` source and has been exercised against the local `.62` output. No external catalog or expected weapon count is used by admission or validation.

## Canonical implementation

- `weapon_identity_spine.py` discovers exact current `item_data + equip_data + equip_origin_data` identities.
- `achieve_item_data.attrs` corroborates weapon family and rejects explicit Level-0 records; it is not counted as an identity list.
- Current blueprint owners overlay Base owners.
- Blueprint and progression data are conditional enrichment.
- Identity, availability, craftability, and progression are separate states.
- Temporary, private, explicit test, tier/variant duplicates, duplicate exact gun owners, and tab/family mismatches fail closed.
- Missing conventional owners and blueprint-free scenario/special records retain explicit unresolved states.
- Downstream corpus, readiness, site, browser, Cradle, and public-web joins use canonical identity keys so blueprint-free records cannot collide on `None`.

## Installed result

The current source-derived `.62` result is 130 identities:

- 117 `standard-blueprint`
- 7 `nonstandard-blueprint`
- 6 `special-equipped`
- 107 ranged
- 23 melee

This is an observed output, not a hard-coded invariant or a universal active-scenario claim. All six special identities are present, including Stealthblade. Their scenario availability remains unresolved.

## Cradle and publication recomputation

Cradle applicability was recomputed for all 130 identities and 87 active Cradles:

- 303 exact compatible relationships
- 737 exact incompatible relationships
- 2,210 unresolved relationships
- 8,060 not-applicable relationships

Downstream results:

- hardened corpus audit: 130 identities, 1,030 ranked gaps
- site readiness: 130 identities
- website projection: 130 identities
- lean browser publication: 130 identities
- Cradle applicability resolved/gated for all 130 identities
- public web quality: `PARTIAL`, not blocked; remaining warnings are unresolved effects, recipes, progression, and artwork

Generated local outputs are under `C:\Users\mikea\Documents\Dead Signal Miner\published` and are not committed to the Miner source repository.

## Verification

The complete Miner suite passes:

```text
Ran 195 tests
OK
```

Regression coverage includes the six standard omissions, six special identities, six installed conventional records absent from the external reference, naming aliases, explicit test records, Level-0 records, tier duplicates, private/temporary records, and canonical downstream joins.

## Operational boundary

- Do not replace this model with a fixed list or expected count.
- Do not treat `130` as universal scenario availability.
- Do not import external catalog values into publication.
- Do not cut a Miner release solely from this handoff; release packaging remains a separate explicit task.
- Leave the pre-existing untracked `tools/miner.zip` untouched.

## Launch-warning follow-up

The first launch-impact cleanup pass is also complete:

- effect publication now distinguishes 76 resolved effects, 27 exact no-fixed-skill records, 14 dangling fixed-skill text owners, and 13 unresolved nonstandard/special effect owners;
- the prior blanket 54-effect absence warning is replaced by 27 genuine unresolved effect owners;
- the 14 dangling fixed-skill records remain gated by the already-closed ownerless fixed-skill forensics branch;
- exact item-to-forge fallback uses `client_data/forge_formula_map_data.json:ITEM_NO_TO_FORGE_NO_MAP` only when the blueprint forge number has no exact recipe owner;
- Machete now resolves through exact server-222 forge formula `3301401`;
- 10 conventional melee recipe paths remain unresolved because the installed formula map has no exact owner for their tier-one items;
- six nonstandard weapons with exact five-tier equipment rows publish `exact-five-tier-nonstandard-progression` instead of being grouped with missing progression;
- Morgan remains the one unresolved progression owner;
- all six special-equipped identities publish progression as not applicable and availability remains unresolved;
- the extracted artwork linker resolves all 130 Weapon artwork references, clearing the Weapon artwork warning;
- public quality remains `PARTIAL` with 27 effect, 10 recipe, and 1 progression warning; artwork warning is zero.

The full Miner suite still passes 195 tests after this follow-up.

