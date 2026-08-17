# Dead Signal — Weapon Site Readiness Pass

Date: 2026-08-17
Canonical repo: `raiinman/dead-signal`
Branch: `main`
Released Miner: `v1.5.14.53`
Website target date: 2026-08-25

## Authority rule

Installed Once Human game data mined by Dead Signal is the database source of truth.
External/community websites are reference/question-set/UX inputs only. Their numbers, mechanics, recipes, labels, and semantics are never imported as evidence.

## New pass

The normal `COMPILE DATA INTELLIGENCE` flow now runs:

1. Weapon UI Consumer Trace
2. Research Suite
3. Weapon Schema + ownerless fixed-skill forensics
4. Hardened Weapons Corpus Audit
5. **Authoritative Weapon Site Readiness**
6. Discovery / Analytics / Publication Gate
7. Intelligence ZIP packaging

New report:

`published/reports/weapon-site-readiness.json`

## Reference player-question inventory

Every weapon is asked, where applicable:

- identity
- name
- rarity
- weapon class
- firing mode
- Gear Tier progression
- damage
- projectile/pellet count
- fire rate
- magazine
- range score
- effective/full-damage range
- ammo type
- reload score
- reload time
- mobility
- ADS time
- bullet speed
- full-damage range
- minimum-damage range
- minimum-damage percent
- crafting
- description
- Special Skill/evidence state
- Cradle compatibility
- image

## Dead Signal enhancement inventory

Separately scored:

- blueprint identity
- item identity
- prototype identity
- gun identity
- Tier I–V matrix
- Blueprint Stars as a separate axis
- recipes by tier
- accuracy
- stability
- selectable ammo
- acquisition
- attachment compatibility
- calibration compatibility
- variant lineage
- exact evidence provenance

## Evidence states

- `resolved-installed-game`
- `resolved-evidence-state`
- `resolved-partial`
- `exact-game-record-located-needs-semantic-proof`
- `unresolved`
- `not-applicable`

An exact game record is authoritative source material, but fields that still need typed owner/consumer semantics are not automatically promoted to a player-facing value.

## Supplemental exact-game scan

The site-readiness pass adds narrowly scoped exact-identity scanning for:

- rarity
- reload score/rating
- Cradle applicability/override relationships

It reuses the hardened record-boundary and typed-identity rules from the corpus audit, preventing sibling-record leakage and bare short-ID collisions.

## Output purpose

The report produces:

- whole-Weapons reference-question coverage score
- Dead Signal enhancement score
- per-weapon question ledger
- per-weapon enhancement ledger
- ranked `launch_blocker_queue`
- exact candidate evidence for unresolved player-facing questions

Use this report as the Weapons website completion checklist through the 2026-08-25 target.
