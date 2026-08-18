# Dead Signal — Weapon Identity Spine Trace Handoff

> Date: 2026-08-18 America/Phoenix  
> Canonical repository: `raiinman/dead-signal`  
> Branch: `main`  
> Stable Miner remains: `v1.5.14.62`  
> Installed evidence boundary: local `.62` Base/Current snapshots

Read this after `PROJECT-RULES.md`, `HANDOFF-2026-08-18-CODEX-LOCAL-TAKEOVER.md`, and `HANDOFF-2026-08-18-CODEX-WEAPON-CRADLE-APPLICABILITY-COMPLETE.md`.

## Purpose

This handoff transfers the Weapons lane to a normal GPT session. The Cradle-applicability implementation is complete. The next architectural correction is weapon discovery itself.

Do not implement from the external comparison alone. The external site was used only to identify disputed records; installed Once Human data and static client consumers remain authoritative.

## Discovery

The existing normalizer admits a weapon through `gun_blueprint_data.json` and requires a conventional five-tier forge progression. That produces 120 canonical records, but the trace proves blueprint completeness is not weapon identity.

The stronger installed identity spine is:

```text
item_data.json
  type / sub_type
→ equip_data.json
  equip_origin_id / gun_no / blueprint_no
→ equip_origin_data.json
  combat-origin attributes
→ achieve_item_data.json
  explicit arms_gun_* / arms_hand family classification
```

Blueprint and progression become conditional enrichment:

```text
equip_data.blueprint_no
→ gun_blueprint_data.json when present
→ forge progression / blueprint attributes / fixed skills
```

Combat parameters follow the independent route:

```text
equip_data.gun_no
→ gun_base_params_data.json
→ handling / firing / magazine / RPM / stability
```

This separates “is a weapon” from “has the standard crafting progression.”

## Static client trace

No game bytecode was executed. Exact code objects were unmarshaled only, using the persistent consumer index first.

### Workbench / blueprint list

```text
ui/data_model/UIWeaponMakePCData.pyc
  UIWeaponMakePCData.get_weapon_list_data
```

Exact static fields/symbols:

```text
gun_blueprint_data
blueprint_template_no
gun_item_no
prototype_no
SeasonHelper.get_template_info_by_server_num
weapon_type_filter_gun_item_no
```

Exact local variables include:

```text
target_blueprint_template_no
blueprint_template_no
weapon_prototype_map
weapon_list
```

This is a season-template-driven blueprint/workbench surface, not a universal weapon catalog.

### Equipment / owned weapon list

```text
ui/data_model/UIEquipmentData.pyc
  UIEquipmentData.get_weapon_list_data
  UIEquipmentData.get_weapon_list_pc_data
  UIEquipmentData.get_gun_items_by_sub_type
```

Exact inputs include:

```text
all_owned_gun_data
all_owned_melee_data
all_owned_gun_sub_type_data
item_rarity
```

The Equipment surface displays owned/equippable weapon entities, including records without conventional blueprints.

### Type filtering

```text
ui/data_tools/EquipmentDataTools.pyc
  weapon_type_filter_gun_item_no
```

Exact inputs include `ItemHelper.get_item_property_value`, `sub_type`, and the melee test. Weapon class therefore comes from item identity/type evidence rather than blueprint progression.

## External comparison and exact installed result

Reference comparison: `https://www.oncehumandb.com/weapons` reported 126 entries on 2026-08-18. The page metadata reported a modification date of 2026-08-03. It is not authoritative.

Comparison against the local `.62` installed corpus:

- 112 names match directly;
- 2 more match by exact entity ID under different names;
- 114 identities definitely overlap;
- the site has 12 installed weapon identities absent from Dead Signal's canonical 120;
- Dead Signal has 6 conventional installed blueprint identities absent from the site;
- the installed union is 132 distinct credible weapon identities.

The union count does **not** prove that all 132 are simultaneously active in one scenario.

### Exact naming aliases

- `10211301`: external `DBSG - Dual Fury`; Dead Signal `Dual Fury`
- `10361401`: external `TEC9 - Additional Rules`; Dead Signal `FP9 - Additional Rules`

### Six standard-looking omissions caused by current admission rules

| Weapon | Item ID | Exact installed evidence |
|---|---:|---|
| Morgan | `10219901` | blueprint `13219901`; no standard five-tier forge list |
| Nail Gun | `10351101` | blueprint `13351101`; no standard five-tier forge list |
| P90 | `10341101` | blueprint `13341101`; no standard five-tier forge list |
| M870 | `10241101` | `equip_data.blueprint_no=13241101`; owner absent from Base blueprint table |
| MK14 | `10561101` | `equip_data.blueprint_no=13561101`; owner absent from Base blueprint table |
| TEC9 | `10361101` | `equip_data.blueprint_no=13361101`; owner absent from Base blueprint table |

All six have current non-temporary/non-private player weapon items, equipment records, origin records, weapon-family achievement classification, and usable gun/equipment identities. The absence of a five-tier Base blueprint owner must not erase them.

### Six special/scenario identities

| Weapon | Item ID | Exact installed family |
|---|---:|---|
| Aurora Fort | `12621401` | LMG / `arms_gun_machinegun` |
| Fate of the Mystic | `12131101` | special subtype `21` / pistol family |
| Star Vortex | `12311401` | SMG family |
| Stealthblade | `10912000` | melee / `arms_hand` |
| The Trial of the Mystic | `12321101` | special subtype `23` / SMG family |
| Ultra Force | `12411401` | Assault Rifle family |

These have exact current records in `item_data`, `equip_data`, `equip_origin_data`, and `achieve_item_data`, but no conventional blueprint. Their weapon identity is proven; universal availability is not. Publish them only with explicit special/scenario applicability unresolved until activation gates are proven.

### Six Dead Signal identities absent from the external catalog

- AUG — `10451101`
- AUG - Electron Cloud — `10451401`
- Compound Bow - The Burden of Betrayal — `10742201`
- QBJ97 - Firey Trees and Silver Flowers — `10641201`
- SN700 — `10511101`
- SN700 - Finale — `10512301`

These have exact installed blueprint and five-tier progression evidence. Do not delete them based on external-site absence. Version or scenario difference is plausible but remains an inference.

## Required canonical change

Rebase weapon discovery on the current item/equipment identity spine. Do not merely add a hard-coded list of 12 names.

Recommended states:

```text
standard-blueprint
  exact weapon identity plus conventional progression

nonstandard-blueprint
  exact weapon and blueprint identity without conventional five-tier progression

special-equipped
  exact item/equipment/origin/family identity without a conventional blueprint;
  scenario applicability separately gated
```

Requirements:

1. Overlay Current over Base for identity owners where appropriate; do not let a stale/missing Base blueprint owner erase a Current weapon.
2. Discover candidates from exact current `item_data` + `equip_data` identities.
3. Require player weapon type/subtype and reject temporary/private/test records through exact fields and consumer-backed rules.
4. Use `achieve_item_data.attrs` as corroborating family classification, not as a unique-weapon counter; it contains tier and variant records.
5. Attach blueprint/progression only when exact owners exist.
6. Preserve unresolved scenario activation rather than collapsing it into exclusion.
7. Keep identity, availability, craftability, and progression as separate fields/states.
8. Add regression controls for the six standard omissions, six special identities, six local-only conventional records, test melee records, tier duplicates, and naming aliases.
9. Recompute Cradle applicability and downstream publication after the canonical weapon identity set changes.
10. Do not cut a release until the new identity model, counts, publication, and packaged tests form a coherent boundary.

## Definition of done

The next session is complete when Dead Signal can answer separately:

```text
Is this an installed weapon entity?
Is it active/available in this scenario?
Does it have a conventional blueprint?
Is it craftable through standard tier progression?
What exact combat owner supplies its stats?
```

No code was changed during this comparison/trace. The existing Cradle implementation and `.62` release remain intact. The untracked `tools/miner.zip` must remain untouched.
