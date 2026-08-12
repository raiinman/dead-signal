# Dead Signal Miner v1.4.0 — Blueprint Progression Patch

This build patches the packaged `normalize_weapons.py` extractor to preserve the full weapon blueprint attribute progression present in `gun_blueprint_attr_data.json`.

## What changed

- The miner no longer inspects only `(blueprint_id, 1)` for weapon blueprint attributes.
- Every tuple row shaped like `(blueprint_id, level)` is collected and sorted by level.
- The existing level-1 weapon effect/base-attribute behavior is preserved for backward compatibility.
- Each `weapons.json` weapon now includes `blueprint_attribute_progression` with:
  - source table
  - raw mined level number
  - normalized base attributes
  - fixed skill code/level
  - complete raw source fields
  - blueprint-row progression/grade/star hint fields when present
- A companion analysis file is written automatically:
  - `published/data/weapon-blueprint-progression.json`
- New counters are added to `weapons.json`:
  - `blueprint_attribute_rows`
  - `weapons_with_multiple_blueprint_attribute_levels`
  - `max_blueprint_attribute_level`

## Important interpretation rule

The second tuple value in `gun_blueprint_attr_data.json` is exported as a raw **level** only. This patch deliberately does **not** label it Blueprint Stars until the harvested sequences are compared against known in-game behavior.

Weapon quality/rarity and crafted Tier I–V remain separate fields, so the new output can be used to test the relationship among quality/grade, blueprint progression, and crafted weapon tier without conflating them.

## Compatibility

Existing fields and the existing `weapons.json` output remain intact. The patch only adds optional progression data plus the companion audit file.

## Validation

The patched normalizer was syntax-checked and run against a synthetic fixture containing:

- one Legendary Assault Rifle
- crafted Tiers I–V
- three distinct blueprint attribute levels

The test successfully exported all three blueprint levels separately while retaining all five crafted tiers.

---

## v1.4.1 — Exact Weapon Progression Investigator

This package now goes beyond preserving raw blueprint attribute levels. The normal combat-resolution pass automatically runs a dedicated progression investigator after `reference-tracer.sqlite` is available.

### New behavior

- Tests all mined weapon Tier I–V damage rows for a universal Tier multiplier model.
- Uses integer-display rounding intervals (`nearest`, `floor`, `ceil`) instead of relying only on noisy displayed ratios.
- Analyzes every `gun_blueprint_attr_data.json` level sequence by weapon, rarity, stat code, label, raw value, ratio, and raw numeric field progression.
- Detects Attack/Damage-like blueprint attributes as possible Star-side modifiers without assuming every raw level is a Blueprint Star.
- Generates falsifiable Star × Tier prediction matrices when an explicit fractional Attack/Damage-like progression value is found.
- Scans relevant raw game tables for Star/Tier/Attack/multiplier/coefficient/enhancement relationships and preserves the top source records.
- Uses `reference-tracer.sqlite` to follow weapon blueprint IDs, crafted item IDs, and gun IDs into progression-related source tables.
- Keeps Calibration Blueprint Attack bonuses explicitly outside the intrinsic Star × Tier model.

### New automatic outputs

- `published/data/weapon-progression-investigation.json`
- `published/reports/weapon-progression-report.md`
- `published/reports/weapon-progression-candidates.json`

`published/data/progression.json` is also annotated with the current investigation status and candidate factors.

### Proof standard

The miner will not label the combined formula as solved merely because a ratio looks plausible. A model must be supported by extracted source semantics or reproduce multiple weapons/levels with rounding accounting for the remaining display error.

---

## v1.4.2 — Direct Star Attack Ratio + Client Consumer Trace

This revision incorporates evidence from the latest 120-weapon harvest and fixes a v1.4.1 interpretation bug.

### Confirmed mined structure

Across the captured weapon corpus:

- all 545 `gun_blueprint_attr_data` tuple levels match the source `strength_lv` value;
- the progression level caps follow the rarity-dependent Blueprint enhancement/star structure while Gear Tier remains the separate five-level `corr_forge_lv` / `art_lv` path;
- all 545 progression rows contain `preset_attack_radio`;
- `preset_attack_radio` is treated as the **direct Attack multiplier already expressed as a ratio** (`1.05` means `x1.05`).

### Critical v1.4.1 correction

v1.4.1 could incorrectly treat a value such as `1.05` as a fractional bonus and test `1 + 1.05 = 2.05`.

v1.4.2 removes that path for the mined `preset_attack_radio` field. Candidate intrinsic Attack is now evaluated as:

`Tier gun_preset_attack × preset_attack_radio[strength_lv]`

Only the final client/UI integer conversion remains unresolved until client bytecode or independent displayed-stat evidence proves it.

### Progression effect modes found in the current 120-weapon snapshot

The star axis is not Attack-only. The latest corpus contains:

- 82 weapons whose `preset_attack_radio` changes with `strength_lv`;
- 13 weapons whose `fixed_skill_lv` changes with `strength_lv` while Attack ratio remains 1.0;
- 25 weapons with neither field changing across the captured levels;
- 0 weapons where both Attack ratio and fixed skill level change together in this snapshot.

The normalized weapon record now reports this per weapon as `progression_effect_mode` instead of pretending every Blueprint Star is simply +Attack.

### First-class normalized output

`weapons.json` and `weapon-blueprint-progression.json` now expose:

- `blueprint_star_progression`
- `source_strength_lv`
- `preset_attack_ratio`
- original source field name `preset_attack_radio`
- fixed skill level at each progression level
- explicit separation from Gear Tier I–V
- rounding status

The raw source row is still retained for provenance.

### PYC consumer hunt

The normal PYC export stage now scans **every extracted `.pyc`**, not just bindict tables, for these progression operands:

- `preset_attack_radio`
- `preset_attack_ratio`
- `strength_lv`
- `gun_preset_attack`
- `corr_forge_lv`
- `gun_blueprint_attr_data`

When the PYC bytecode version is compatible with the bundled Python runtime, the miner recursively inspects code objects and saves instruction windows around those names. Nearby multiplication, calls, and `round` / `int` / `floor` / `ceil` / truncation-like operations are ranked as high-value consumer candidates.

The PYC is never executed.

The export stage persists the evidence immediately as:

- `<base/current snapshot>/pyc-progression-symbols.json`

so the evidence survives even if a temporary extracted-PYC folder is later removed.

The combat-resolution pass merges those stable indexes and writes:

- `published/reports/weapon-progression-pyc-consumers.json`

alongside the existing progression investigation/report files.

## v1.4.3 — Focus Consumer Code Capsules

The v1.4.2 pass located the exact high-value client consumers but CPython's standard `dis` module raised `IndexError: tuple index out of range` while decoding their bodies. The affected functions include:

- `dcs_extend/common/shoot_utility.py :: get_gun_preset_attack_radio`
- `dcs_extend/common/shoot_utility.py :: get_gun_omg_value`
- `ui/data_tools/ItemDataTools.py :: get_gun_attack_base`

v1.4.3 treats this as a decoder problem rather than losing the evidence.

For those focus functions the miner now preserves:

- PYC magic/header bytes;
- complete `co_names`, `co_varnames`, free/cell variables, and scalar constants;
- complete raw `co_code` hex;
- raw two-byte opcode/argument rows;
- exception/line table bytes where present;
- full standard disassembly when it succeeds;
- a clearly-labelled padded-metadata diagnostic disassembly when normal `dis` fails.

The padded diagnostic stream is never treated as proof on its own. Raw opcode numbers and the code-object capsule remain authoritative for offline reconstruction.

The static scan also explicitly indexes the three focus function names, so callers/wrappers that reference the helper without embedding `preset_attack_radio` themselves are retained as candidates.

No game bytecode is executed.

## v1.4.4 — Proven Multiply Tail + Caller Chain Trace

The v1.4.3 code capsules exposed a stable remapped opcode tail in the real Once Human client.
The client preserves standard BINARY_OP argument semantics while remapping several opcode numbers.
For the captured progression consumers the tail mapping is unambiguous:

- opcode 100 -> STORE_FAST
- opcode 94 -> LOAD_FAST
- opcode 125 -> BINARY_OP
- opcode 122 -> RETURN_VALUE
- BINARY_OP argument 5 -> NB_MULTIPLY (`*`)

This proves that both `get_gun_omg_value()` and `get_gun_attack_base()` return:

`preset_attack * attack_radio`

and that `get_gun_preset_attack_radio()` returns `attack_radio` directly. No integer conversion is present in those recognized return tails, so display rounding is downstream.

v1.4.4 adds:

- automatic recognition/reporting of those exact remapped return tails;
- focus capture for `get_gun_attack()` and `get_gun_attack_guncore()`;
- caller-chain discovery for any code object whose `co_names` references the progression functions;
- metadata-only detection of `int`, `round`, `floor`, `ceil`, `trunc`, `format`, and `str`, which remains valid even when normal disassembly fails;
- full raw code capsules for progression-chain callers, not only the original three focus functions;
- report summaries ranking caller functions that combine a progression-chain call with rounding/format names.

The next evidence target is therefore downstream only: identify which caller converts or formats the raw intrinsic float for the UI.

## v1.4.5 — D0100 Display Chain + Remapped-Disassembly Safety

The v1.4.4 pass proved the raw intrinsic calculation but also exposed a decoder trap:
stock Python 3.11 `dis` can sometimes *appear* to decode Once Human bytecode without
raising an exception even though the client has remapped opcode numbers. In the captured
client, opcode 122 is proven to mean `RETURN_VALUE`, while stock Python labels opcode 122
as `BINARY_OP`. Therefore a superficially successful standard disassembly is not
necessarily authoritative.

### Safety correction

v1.4.5 detects the proven opcode-remapping profile at the PYC level. When detected:

- stock disassembly is retained only as diagnostic context;
- arithmetic operation names from stock `dis` are not promoted to evidence;
- rounding/format function names are taken from trustworthy code-object metadata
  (`co_names` / string constants), not from mislabelled opcodes;
- exact recognized raw tails (`preset_attack * attack_radio`, direct `attack_radio` return)
  remain authoritative because they are reconstructed from the remapped opcode pattern and
  preserved `BINARY_OP` argument semantics.

This specifically removes the false appearance that `ItemDataTools.get_gun_attack()`
contained a downstream `+` operation. The captured function is consistent with reading the
Attack stat from the aggregate stat dictionary; no new arithmetic/rounding is proven there.

### D0100 display/stat-chain trace

The latest run shows the proven raw Attack is stored and transported under stat ID `D0100`.
The miner now follows that representation into the generic attribute/UI layer instead of
continuing to chase only the already-solved progression helper names.

New focus targets include:

- `D0100`
- `get_weapon_base_attr_dict`
- `get_weapon_base_attr_list`
- `get_weapon_base_attr_new`
- `convert_data_show_attr`
- `convert_data_adjust_show_attr`
- `get_affix_name_and_val`
- `get_gun_attack`

The scanner captures full code capsules for these functions and their callers. It also records
trustworthy metadata references to `round`, `int`, `floor`, `ceil`, `trunc`, `format`, `str`,
`float`, and common integer-format strings such as `%d` / `%.0f` / `{:.0f}`.

The next evidence target is the exact generic display conversion applied to `D0100` after the
proven raw value `gun_preset_attack * preset_attack_radio` has entered the stat dictionary.

## v1.4.6 — Display Integer Conversion Proven

The v1.4.5 D0100 pass captured enough raw code-object evidence to resolve the remaining intrinsic display conversion without trusting the remapped client's stock disassembly.

### Proven client chain

The miner now recognizes these exact raw-code relationships:

1. `get_gun_omg_value()` returns:

   `preset_attack * attack_radio`

2. `get_gun_attr_property_value(..., "weapon_omg_affix_value", star=star)` directly returns:

   `get_gun_omg_value(gun_no, star)`

3. `get_weapon_base_attr_new()` wraps that property result in built-in `int(...)` before storing `weapon_omg`.

Therefore the positive intrinsic weapon Attack display path is:

`DisplayedIntrinsicAttack = int(gun_preset_attack[Tier] * preset_attack_radio[BlueprintStars])`

For positive Attack values, Python `int()` truncation toward zero is equivalent to `floor()`.

The `round()` calls also present in `get_weapon_base_attr_new()` belong to later affix/percentage normalization logic and are not the conversion applied to the base `weapon_omg` value.

### Safety

Recognition uses exact function metadata and raw remapped opcode/argument ordering. It does not promote stock CPython `dis` output from the remapped Once Human bytecode to authoritative evidence.


## v1.4.7 — Calibration RNG Range + Consumer Chain

- Preserves `gun_correct_print_data.affix_val_range` and `affix_ids_weight` in `calibrations.json`.
- Adds neutral `calibration_roll_range` fields with raw and percent-normalized min/max values.
- Adds `reports/calibration-investigation.json` with current rarity/range distribution.
- Links each calibration record to its resolved fixed style buff as `style_buff` without assuming unresolved Attack value semantics.
- Extends static PYC scanning to calibration RNG generation/serialization/application helpers including `gen_rand_correct_affixs`, `rand_term_affix_data`, `generate_gun_correct_print_detail`, `get_gun_calibration_attr`, `convert_gun_correct_affix_val_to_affix_list`, and `get_gun_correct_affix_add`.
- Adds `affix_val_range`, `gun_correct_print_data`, `gun_correct_common_terms_data`, and `gun_calibration_affix_option_data` as static scan targets.
- Does not execute game bytecode.


## v1.4.8 — Calibration Attack Ratio + Weighted Drop Trace

The v1.4.7 calibration pass exposed enough static evidence to separate the
Calibration Blueprint's independent random layers.

### New static findings encoded by this build

- `generate_correct_print_term_id()` is focus-captured. Its surviving metadata
  and raw operation pattern show a single weighted selection from `affix_ids`
  using `affix_ids_weight`, `sum`, `random.uniform`, a cumulative
  `weight_sum`, and one selected `term_id`.
- `generate_gun_correct_print_info()` is recognized as the calibration roll
  generator. The captured client path is:

  `round(random.uniform(affix_val_range[0], affix_val_range[1]), 3)`

  stored as `gun_correct_affix_val`.

  The 0.001 raw precision corresponds to 0.1 percentage-point increments.
- `convert_gun_correct_affix_val_to_affix_list()` is captured as the bridge
  that injects the calibration roll into generated gun-affix entries under
  `affix_val`.
- `D0102` is now an explicit calibration trace target.
- `get_gun_attack_guncore()` is recognized when its metadata/raw pattern shows
  `D0101` and `D0102` in the Attack-ratio bucket around base `D0100`, with
  preserved BINARY_OP arguments for += and multiplication.

### Additional preserved data

`reports/calibration-investigation.json` now also attempts to preserve:

- raw `calibration_option_gun` / `calibration_style_gun` global parameters,
  including provenance, when found in extracted global-parameter tables;
- every `gun_blueprint_terms_pool` row whose affix id is `D0102`.

### Expanded focus chain

This build adds focused static capture for:

- `generate_correct_print_term_id`
- `generate_correct_term_data`
- `gen_rand_gun_affixs`
- `_rand_term_no_lst`
- `init_gun_correct_print_info`
- `get_gun_base_affix_add`
- `get_gun_attack_guncore`
- `get_gun_average_tire`
- `get_gun_info`
- `calc_gun_attr_data`
- `refresh_base_prop`

The remaining target is the final calibrated Attack presentation path:
determine whether the D0102-calibrated result is integer-converted at the
guncore layer or only by the later UI formatter, and identify any additional
Attack-ratio values combined with D0102 before multiplication.

No game bytecode is executed.

## v1.4.9 — Calibration Layers Separated + Combined Attack Bucket Trace

- Promotes the v1.4.8 Calibration Blueprint findings into explicit separate systems:
  - dropped blueprint `gun_correct_affix_val` rarity roll from `affix_val_range`;
  - one weighted dropped blueprint term from `affix_ids` / `affix_ids_weight`, materialized by `generate_correct_term_data`;
  - weapon calibration-level `affix_options`, unlocked through `calibration_option_gun` level gates and resolved through `gun_calibration_affix_option_data`.
- Preserves the current `calibration_option_gun` global thresholds (`[7, 10]` in the current snapshot) and labels them as a separate +level option system rather than drop RNG.
- Adds static recognizers for:
  - `generate_correct_term_data` random term value generation;
  - `get_gun_calibration_affix_option_size` level-gate semantics;
  - `get_gun_affix_option_add` option-table stat additions;
  - `get_gun_correct_affix_add` dropped Calibration Blueprint affix-list additions;
  - `get_gun_affix_add` / `get_gun_calc_affix_add` combined D0101/D0102 Attack-ratio bucket.
- Expands PYC focus scanning to the final aggregation/display bridge (`get_gun_affix_add`, `get_gun_calc_affix_add`, `get_gun_affix_option_add`, `get_gun_base_affix_attack`, `cal_gun_attr_data_with_item_no`, `get_gun_base_random_attr_data`) and symbols such as `VM_GUN_FORMULAS`.
- Important current implication: Calibration D0102 joins a shared additive Attack-ratio bucket; it must not be modeled as an isolated multiplier until all concurrently active D0101/D0102 sources are accounted for.
- No game bytecode is executed. Static code-object metadata/raw wordcode only.


## v1.5.0 — Generic Weapon Stat Aggregator + Accessory Trace

- Moves the investigation from a Calibration-only view to the game's generic static weapon-card stat pipeline.
- Recognizes `get_gun_affix_add()` as a six-source aggregator with inputs:
  - `base_affix_add`
  - `accessory_affix_add`
  - `rand_affix_add`
  - `affix_option_add`
  - `cal_affix`
  - `correct_affix_add`
- Adds focus capture for the upstream producers of accessory, random-affix, calibration-option, and GunCore contributions.
- Adds `reports/weapon-stat-aggregator-investigation.json`.
- Tracks major accessory stat IDs including Accuracy, Stability, Range, Fire Rate, Magazine, Mobility, Reload, Bullet Velocity, and direct D0101/D0102 Attack-ratio contributions.
- Fixes attachment stat normalization: `gun_accessory_attr_data` stores many modifiers as `[stat_id, value]` pairs; the previous resolver expected parallel code/value arrays and therefore left many `resolved_stats` empty.
- Keeps static weapon-card aggregation separate from runtime combat buffs (mods, armor/set buffs, Cradles, Deviations, consumables) until their direct consumer paths are proven.
- Static inspection only; no game bytecode is executed.


## v1.5.1 — Accessory Stat Map + Proven Static Attack Aggregation

- Promotes the raw `get_gun_affix_add` / `get_gun_attack_guncore` operator sequence into the static Attack formula signature:
  - `attack_radio = 1.0 + sum(active D0101/D0102 values)`
  - `delta_attack = combined D0100 contribution - base D0100 contribution`
  - `combined_attack = base D0100 * attack_radio + delta_attack`
- Keeps the six normal static-card sources separate while allowing their stat IDs to enter the same aggregator:
  - base weapon affixes
  - equipped accessories
  - random weapon affixes
  - +7/+10 calibration options
  - calibration-level contribution
  - Calibration Blueprint contribution
- Fixes a critical normalization hole: raw `D0101` / `D0102` values are now resolved as Weapon DMG percentage modifiers against canonical `D01` rather than being omitted from `resolved_stats`.
- Adds a planner-facing per-slot accessory stat map for Sight, Muzzle, Tactical, and Magazine.
- Expands PYC scanning around `VM_GUN_FORMULAS`, `item_attack_base`, `item_attack_guncore`, `item_attack`, `attack_radio`, `delta_attack`, and the D0100/D0101/D0102 bridge.
- The static weapon-card layer remains separate from runtime conditional combat buffs.
- Static inspection only; no game bytecode is executed.

## v1.5.4 — D0100 Prototype Export-Root Fix

- Fixes v1.5.3 formatter prototype probing: parsed bindict JSON is searched in the exported base/current snapshot roots, not only the raw PYC source roots.
- Recovers `game_common/data/affix_prototype_data.json` rows for `D0100`, `D0101`, and `D0102` when present.
- Compares formatter/type/format metadata across D0100 vs the proven percentage stats D0101/D0102.
- Reports `D0100_formatter_binding` separately from the remaining `int()` branch proof.
- No game bytecode is executed.
