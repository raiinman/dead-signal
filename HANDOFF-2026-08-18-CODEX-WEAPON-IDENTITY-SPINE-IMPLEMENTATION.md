# Dead Signal — Codex Weapon Identity Spine Implementation Handoff

> Date: 2026-08-18 America/Phoenix  
> Canonical repository: `raiinman/dead-signal`  
> Branch: `main`  
> Stable Miner release boundary: `v1.5.14.62`  
> Starting canonical commit: `fa51c4e4d8970f968f2fd19a8a9d86cee5cf6bf4`

Read completely, in order:

1. `PROJECT-RULES.md`
2. `AI-CONTINUITY.md`
3. `HANDOFF-2026-08-18-CODEX-LOCAL-TAKEOVER.md`
4. `HANDOFF-2026-08-18-CODEX-WEAPON-CRADLE-APPLICABILITY-COMPLETE.md`
5. `HANDOFF-2026-08-18-WEAPON-IDENTITY-SPINE-TRACE.md`
6. this file

This handoff converts the completed identity trace into the next implementation pass. Work directly on canonical `main` unless a destructive ambiguity genuinely requires user input.

## Objective

Rebuild canonical Weapon discovery around the installed item/equipment identity spine so Dead Signal can distinguish:

```text
weapon identity
availability / scenario activation
blueprint ownership
craftability
progression
combat stat ownership
```

Do not preserve the old assumption that a Weapon must have a conventional Base `gun_blueprint_data` owner plus five-tier forge progression in order to exist as a player weapon.

The target is not an externally dictated count. The target is an evidence-correct installed Weapon set and explicit state model.

## Authoritative discovery spine

Primary identity route:

```text
Current item_data.json
  type / sub_type / temp_item / private_server_item
        ↓
Current equip_data.json
  blueprint_no / equip_origin_id / gun_no
        ↓
Current/Base equip_origin_data.json
  combat-origin evidence
        ↓
achieve_item_data.json
  arms_gun_* / arms_hand family corroboration
```

Conditional blueprint enrichment:

```text
equip_data.blueprint_no
        ↓
Current-over-Base gun_blueprint_data owner when exact
        ↓
blueprint attributes / fixed skill / progression / recipes when exact
```

Independent combat route:

```text
equip_data.gun_no
        ↓
gun_base_params_data
        ↓
magazine / RPM / handling / fire-mode / bullet-pattern relationships
```

The static consumer trace already proves that the Equipment UI consumes owned/equippable item identity separately from the blueprint/workbench list. Do not rerun a broad scan unless the local persistent indexes cannot answer a specific missing question.

## Required identity states

Implement an explicit state field rather than making inclusion itself encode progression semantics.

Minimum states:

```text
standard-blueprint
  exact installed weapon identity
  exact blueprint owner
  conventional progression present

nonstandard-blueprint
  exact installed weapon identity
  exact blueprint identity/number
  conventional five-tier progression absent or nonstandard

special-equipped
  exact installed item/equipment/origin/family identity
  no conventional blueprint owner
  scenario/universal availability unresolved unless separately proven
```

If additional exact states are needed, add them declaratively and document their proof requirements. Do not use external catalog membership as a state.

Also add or preserve separate booleans/status fields for:

- installed weapon identity
- scenario availability / activation
- blueprint owner status
- craftability status
- conventional progression status
- combat owner status

Unknown must remain unknown.

## Current disputed controls

The trace established these six standard-looking omissions from the old 120 admission rule:

| Weapon | Item ID | Expected identity treatment |
|---|---:|---|
| Morgan | `10219901` | nonstandard blueprint unless stronger exact progression evidence is found |
| Nail Gun | `10351101` | nonstandard blueprint unless stronger exact progression evidence is found |
| P90 | `10341101` | nonstandard blueprint unless stronger exact progression evidence is found |
| M870 | `10241101` | current equipment blueprint reference; stale/missing Base owner must not erase identity |
| MK14 | `10561101` | current equipment blueprint reference; stale/missing Base owner must not erase identity |
| TEC9 | `10361101` | current equipment blueprint reference; stale/missing Base owner must not erase identity |

And these six special/scenario-equipped identities:

| Weapon | Item ID |
|---|---:|
| Aurora Fort | `12621401` |
| Fate of the Mystic | `12131101` |
| Star Vortex | `12311401` |
| Stealthblade | `10912000` |
| The Trial of the Mystic | `12321101` |
| Ultra Force | `12411401` |

Their installed weapon identity is proven by exact current records. Their universal scenario availability is not proven. Include them only with explicit unresolved/special availability state; do not silently label them universally obtainable.

Retain these six conventional installed records even though the comparison site omitted them:

- AUG — `10451101`
- AUG - Electron Cloud — `10451401`
- Compound Bow - The Burden of Betrayal — `10742201`
- QBJ97 - Firey Trees and Silver Flowers — `10641201`
- SN700 — `10511101`
- SN700 - Finale — `10512301`

External absence is not evidence for removal.

Alias controls:

- `10211301`: `Dual Fury` / external alias `DBSG - Dual Fury`
- `10361401`: installed Dead Signal naming `FP9 - Additional Rules`; external comparison called it `TEC9 - Additional Rules`

Identity matching must prefer exact installed IDs over display-name equality.

## Implementation requirements

### 1. Replace blueprint-first admission

Refactor `tools/miner/src/extractor/normalize_weapons.py` so discovery starts from exact current player weapon item/equipment candidates rather than iterating only Base `gun_blueprint_data`.

Do not simply append twelve hard-coded IDs after the old loop.

The old checks for:

- current item existence
- current equipment existence
- `temp_item`
- `private_server_item`
- item type/subtype

remain useful, but they must participate in item/equipment-first candidate discovery.

The old `blueprint_template_no == 90 => alternate-template => exclude` rule must not survive as an unexplained semantic shortcut. If template 90 still needs exclusion anywhere, prove its meaning through installed fields/client consumers and model it explicitly.

### 2. Current-over-Base ownership

Where identity-owner tables exist in both snapshots, use an explicit Current-over-Base policy appropriate to that table.

A missing Base blueprint record must not erase a Current weapon entity referenced by Current equipment.

Do not merge unrelated sibling rows or use fuzzy IDs.

### 3. Blueprint/progression as enrichment

For each discovered identity:

- attach exact blueprint owner when present;
- attach five-tier progression only when exact;
- preserve nonstandard progression without manufacturing five tiers;
- preserve recipe absence as unresolved/not-present-in-known-layer, never as proof of non-craftability unless consumer-backed evidence proves it;
- preserve fixed-skill evidence policy from the closed fixed-skill branch.

### 4. Publication contract

Update the Weapon publication/projection/readiness path so it understands the new state model.

Likely affected modules include, but are not limited to:

- `normalize_weapons.py`
- `dead_signal_weapon_site_projection.py`
- `dead_signal_weapon_site_publish.py`
- `dead_signal_weapon_site_readiness.py`
- `dead_signal_weapon_launch_gap_trace.py`
- `dead_signal_coverage_dashboard.py`
- `dead_signal_self_diagnostics.py`
- `dead_signal_semantic_registry.py`
- `dead_signal_reference_graph.py`
- website materialization/audit code if it assumes 120 or five-tier progression

Do not expose internal implementation labels if a cleaner player-facing availability/progression label is appropriate, but keep the exact evidence state in the evidence sidecar.

### 5. Recompute Cradle applicability

The prior Cradle run covered the old 120 canonical set. After Weapon identity changes:

- rerun the Cradle applicability compiler against the new canonical weapon set;
- compute relationships for every newly admitted weapon identity;
- preserve exact compatible / exact incompatible / unresolved / not-weapon-selected states;
- update persistent graph edges, semantic reports, diagnostics, coverage dashboard, site publication and counts;
- do not infer compatibility by display category alone.

### 6. Downstream count hygiene

Search source/tests/site tools for hard-coded assumptions around `120`, `95 ranged`, `25 melee`, or the old exclusion counts.

Change only assumptions that truly represent canonical Weapon cardinality. Do not blindly replace numeric test fixtures unrelated to the real corpus.

The evidence trace found an installed union of 132 credible identities, but **132 is not a required hard-coded final count**. Recompute from the local snapshot. If the implementation yields a different exact set, explain every difference with installed evidence.

### 7. Scenario gating

Do not claim the six special identities are universally active merely because their current item/equipment records exist.

Use the persistent consumer index/table registry/reference graph to search for exact scenario/season activation gates if such evidence is inexpensive and directly connected to those records.

If the gate remains unresolved, publish:

```text
installed identity = proven
availability = unresolved/special-scenario
```

That is acceptable for launch.

Do not open an unbounded scenario research project during this pass.

## Required regression tests

Add focused tests that prove at minimum:

1. conventional blueprint weapon still publishes normally;
2. Morgan is not erased solely for lacking conventional five-tier forge progression;
3. Nail Gun is not erased solely for lacking conventional five-tier forge progression;
4. P90 is not erased solely for lacking conventional five-tier forge progression;
5. M870 identity survives missing/stale Base blueprint owner when Current exact equipment identity exists;
6. MK14 same control;
7. TEC9 same control;
8. each of the six special-equipped identities can be represented without inventing a conventional blueprint;
9. temporary/private/test item controls remain excluded;
10. tier duplicates and derivative equipment rows do not become duplicate canonical identities;
11. exact ID identity beats name aliases;
12. local-only conventional records remain admitted;
13. old `blueprint_template_no == 90` behavior is either removed or backed by a new explicit proven rule;
14. Cradle applicability recomputes for the expanded canonical set;
15. public projection does not require five-tier progression for every Weapon;
16. availability/craftability/progression unknown states are preserved rather than collapsed;
17. no external catalog names/counts appear as canonical hard-coded source data.

Run the full Miner test suite after focused tests.

## Evidence/reporting requirements

Produce a bounded local report that makes the new discovery decision inspectable. Suggested report:

`published/reports/weapon-identity-spine.json`

For each canonical identity include at least:

- item ID
- display name
- item type/subtype
- equipment owner key
- equip origin owner key
- gun_no
- blueprint_no/reference
- exact blueprint owner present/missing
- identity state
- progression state
- craftability state
- availability state
- family corroboration
- inclusion evidence

Also include excluded candidate counts/reasons, with enough detail to audit test/temp/private/nonweapon filtering without bloating the shareable bundle.

If this report is useful to normal GPT review, add only a bounded summary to the shareable Intelligence bundle; persistent/heavy detail stays local.

## Release policy

Do **not** create a new Miner release merely because implementation commits land.

First reach a coherent boundary where:

- canonical discovery is stable;
- new identity counts are explained;
- Cradle relationships are recomputed;
- publication/readiness/diagnostics agree;
- focused tests pass;
- full Miner suite passes;
- site/public contract checks pass;
- no generated local databases/ZIPs are committed;
- `tools/miner.zip` remains untouched.

Then report whether the changes justify the next release boundary. Do not publish the updater manifest until a full Windows package/release gate is explicitly undertaken.

## Stop conditions

Do not stop for ordinary implementation decisions. Continue through discovery, publication, Cradle recomputation, and tests.

Stop and ask only if:

- exact installed evidence gives two mutually incompatible canonical identity interpretations that materially change publication;
- a destructive repository/filesystem action becomes necessary;
- release publication is requested but a release-critical prerequisite cannot be proven.

## Completion report

When done, update the handoff/read-order documentation and report:

- canonical commit SHA(s)
- exact canonical Weapon count
- count by identity state
- ranged/melee/special breakdown if provable
- the status of all 12 previously omitted controls
- excluded candidate counts/reasons
- Cradle relationship counts after recomputation
- publication/readiness/diagnostic status
- focused test results
- full Miner suite result
- whether a new release was created (default: no)
- confirmation that `tools/miner.zip` remained untouched

The guiding rule for this pass is:

> Prove that an entity is a Weapon first. Prove how it is obtained, activated, crafted, progressed, and modified separately.
