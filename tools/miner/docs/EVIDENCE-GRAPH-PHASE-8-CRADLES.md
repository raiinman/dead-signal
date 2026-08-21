# Evidence Graph Phase 8 — Cradles

Phase 8 promotes the existing installed-data Cradle applicability work into a typed `cradle` Evidence Graph domain.

## Identity boundary

Current Cradle identity is the exact `cradle_override_entry_data` entry ID, but an entry is admitted into the current graph only when the installed `cradle_override_config_new_data.override_unlock_lst` evidence marks it active.

The engine does **not** hard-code the observed corpus size. The active corpus is derived on every run from installed configuration membership. This preserves the current 87-active-Cradle corpus without turning 87 into a permanent schema constant.

Inactive entry rows are historical/legacy evidence and are excluded from the current Cradle registry and adapter.

## Claims

The adapter exposes:

- `cradle.exact_identity`
- `cradle.active_configuration`
- `cradle.slot`
- `cradle.effect_owner`
- `cradle.weapon_applicability`
- `cradle.weapon_direction_consistency`
- `cradle.scenario_availability`
- `cradle.artwork`

## Weapon applicability

The authoritative exact chain remains:

```text
active cradle config
→ cradle entry
→ buff_id
→ buff / logic tree
→ positive hold_item_check(type, sub_type)
→ weapon item selector
```

A positive exact `hold_item_check` produces typed positive/negative weapon results. Raw attack, formula, keyword, weapon-number, and melee-event selectors remain `UNRESOLVED` until their typed weapon meaning is independently proven.

A Cradle with no weapon-identity selector is `NOT APPLICABLE` to weapon selection. That state does **not** mean the Cradle effect is inactive or unusable.

## Forward / reverse consistency

The adapter recomputes Cradle → weapon relationships from the retained selector evidence and weapon item selectors. It separately inverts the published weapon → Cradle lists.

The two directions must agree exactly. Any mismatch becomes `CONFLICT`; neither direction silently overwrites the other.

## Scenario gate

Installed `active_config_keys` and `active_season_ids` prove configuration/season membership. They do not prove which scenario/configuration is active for the player at runtime.

Therefore scenario availability remains a separate `PARTIAL` claim until current runtime scenario selection is independently proven.

Weapon compatibility cannot promote scenario availability, and scenario membership cannot promote weapon compatibility.

## Slot boundary

The existing applicability report preserves active configuration membership but currently flattens `override_unlock_lst`, so its outer nested slot/group position is not retained in the published evidence artifact.

Phase 8 therefore keeps `cradle.slot` as `UNRESOLVED` and explicitly names the missing exact slot-position owner. It does not infer a slot number from list order that is no longer present.

A later source-preserving extraction may promote this claim without changing Cradle identity or the applicability contract.

## Effect ownership

`cradle_override_entry_data.buff_id` is an exact effect reference. The existing applicability report also retains visited buff IDs and logic-tree names from the static traversal.

Missing buff or consumer evidence remains `PARTIAL`/`UNRESOLVED`; localized description text is not used as effect ownership proof.

## Registry

The Phase 3 entity registry now flattens Cradle browse families into exact `ds-cradle-<entry_id>` variants and filters them by installed active configuration membership.

Display-name families remain browsing aids only.

## False-proof controls

Phase 8 tests cover:

- inactive legacy Cradle exclusion;
- exact positive and negative weapon applicability;
- poisoned forward/reverse relationship disagreement → `CONFLICT`;
- unresolved raw keyword/attack selectors;
- no weapon selector → `NOT APPLICABLE`, not negative compatibility;
- scenario membership remaining separately gated;
- slot state failing closed while nested position evidence is absent;
- generalized graph validation and registry routing.

## Publication boundary

`CradleAdapter` cannot publish website data. It consumes reviewed Miner outputs and returns evidence contracts only.

Generated Miner output, raw game exports, research databases, and `tools/miner.zip` remain outside source control.
