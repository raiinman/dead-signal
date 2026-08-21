# Evidence Graph Phase 7 — Mod 2.0 Graph

## Scope

Phase 7 adds current Mod 2.0 as a typed Evidence Graph domain. It does not merge
legacy randomly rolled Mods into the current system and it does not assign
runtime meanings that have not been proven by an exact owner/consumer.

## Exact identity

The compact web dataset groups rows by `mod_code` for browsing, but a browse
family is not identity proof. The registry indexes exact source variants as:

```text
ds-mod-var-<item_id>
```

`mod_code` remains a searchable alias/family relationship. If multiple exact
item variants share one `mod_code`, a bare code is ambiguous and the adapter
fails closed.

## Current versus legacy

The current normalized Mod pipeline starts from:

```text
new_mod_item_data
→ new_mod_property_data
→ mod_entry_data
→ new_mod_frame_lib_data
```

`mod_frame_enrichment.py` stamps normalized rows with:

- `mod_system = current-mod-2.0`
- `owner_state = exact-new-mod-item-owner`
- `owner_source_table = game_common/data/new_mod_item_data.json`

The compact projector carries that classification forward and records any source
variant whose classification does not match the current system. Legacy randomly
rolled Mod records are not included in this graph.

## Claims

### Identity and system

`mod.exact_identity` requires one exact item-backed Mod variant.

`mod.system_classification` records the current Mod 2.0 lane separately from
legacy random-roll data.

### Slot compatibility

`mod.slot_compatibility` preserves the exact `apply_range` selector from
`new_mod_property_data`. Phase 7 does not invent a display-slot label from the
numeric code without an exact typed mapping owner.

### Family and main attribute

`mod.family_main_attribute` preserves:

- `genre_lib` as the exact Mod family selector;
- `main_entry_no` as the exact main entry family owner.

Shared codes do not merge Mod identities.

### Levels 1–17

`mod.levels_1_17` enumerates exact `mod_entry_data` rows for the main entry.

- all Levels 1–17 present: `PROVEN`;
- some present: `PARTIAL`, naming the missing levels;
- no exact rows: `UNRESOLVED`.

Missing levels are never synthesized.

### Fixed sub-attributes

The existing frame enrichment proves:

```text
frame_code
→ new_mod_frame_lib_data
→ four source-ordered sub_entry_item_no IDs
→ stable mod_entry_data family identities
```

When all four exact families are present,
`mod.fixed_sub_attributes` is `PROVEN` for those family identities.

### Suffix / frame family boundary

`mod.suffix_frame_family` preserves the exact frame and the source order of its
four sub-entry families. The claim remains `PARTIAL` because no exact runtime
consumer has yet proven:

```text
source position 0..3 → frame_lv_1..4
```

No positional suffix-level assignment may be published from resemblance or list
position alone.

### Shiny Mods

`mod.shiny_classification` uses the exact `is_shiny_mod` property owner. Shiny
records also preserve `shiny_buff_id` and `shiny_replace_mod_code`. A Shiny row
without its expected exact buff owner remains partial rather than inventing an
effect.

### Effect ownership

`mod.effect_ownership` requires an exact `main_entry_no` and exact
`mod_entry_data` rows. Every effect row must name an attribute owner or a buff
owner. If neither exists, the unresolved level explicitly names the missing
owner.

### Acquisition and artwork

Localized installed-game gain-path text and exact item artwork references are
separate claims. Missing text/art remains unresolved.

## False-proof controls

Phase 7 tests require that:

1. two item variants sharing one `mod_code` stay separate;
2. a shared bare `mod_code` fails as ambiguous;
3. Levels 1–17 are counted from exact rows rather than assumed;
4. exact four frame sub-entry families do not imply frame-level positions;
5. Shiny classification names its exact buff owner;
6. effect rows without attribute/buff owners remain partial;
7. the normalized/current pipeline stamps Mod 2.0 ownership explicitly;
8. the compact projector reports classification mismatches instead of silently
   treating a legacy-looking record as current.

## Publication boundary

The adapter has no publication authority. It resolves typed evidence for the
Evidence Graph only.

## Exit criteria

Phase 7 is complete when:

- current Mod 2.0 relationships are exact and typed;
- legacy random-roll records remain isolated;
- Levels 1–17 and Shiny/frame relationships fail closed when evidence is
  incomplete;
- every unresolved effect identifies the missing owner or consumer;
- the full Miner source/package workflow passes on `main`.
