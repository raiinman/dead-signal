"""Complete malformed Armor Tier series from exact installed-game variant evidence."""

from __future__ import annotations

import copy

EXPECTED_TIERS = {1, 2, 3, 4, 5}


def tier_number(row):
    try:
        return int(row.get("data_level"))
    except (TypeError, ValueError, AttributeError):
        return None


def suffix_matches_tier(item_id, tier):
    text = str(item_id or "")
    return text.isdigit() and len(text) >= 2 and int(text[-2:]) == tier


def attribute_templates(tiers):
    result = {}
    for tier in tiers:
        for attribute in tier.get("attributes") or []:
            code = str(attribute.get("code") or "")
            if code and code not in result:
                result[code] = copy.deepcopy(attribute)
    return result


def exact_variant_candidates(equipment, origins, blueprint_id, suit_id, tier):
    candidates = []
    for item_id, record in equipment.items():
        if int(record.get("blueprint_no") or 0) != blueprint_id:
            continue
        if int(record.get("suit_id") or 0) != suit_id:
            continue
        if not suffix_matches_tier(item_id, tier):
            continue
        origin_id = str(record.get("equip_origin_id") or item_id)
        origin = origins.get(origin_id)
        if isinstance(origin, dict):
            candidates.append((str(item_id), record, origin_id, origin))
    return candidates


def build_exact_tier(item_id, record, origin, item, tier, blueprint_id, templates):
    codes = [str(value) for value in origin.get("base_attr_name_list") or []]
    values = list(origin.get("base_attr_val_list") or [])
    if not codes or len(codes) != len(values):
        return None, "origin stat code/value lengths are invalid"
    if set(codes) != set(templates):
        return None, "origin stat schema does not match sibling Tier schema"

    attributes = []
    for code, value in zip(codes, values):
        attribute = copy.deepcopy(templates[code])
        attribute["code"] = code
        attribute["value"] = value
        attributes.append(attribute)

    def stat(code):
        return next(
            (entry.get("value") for entry in attributes if entry.get("code") == code),
            None,
        )

    return {
        "item_id": int(item_id),
        "data_level": tier,
        "tier_label": f"Tier {tier}",
        "hp": stat("A0200"),
        "pollution_resistance": stat("R3600"),
        "psi_intensity": stat("D4100"),
        "attributes": attributes,
        "durability": item.get("durability"),
        "weight": item.get("weight"),
        "icon": item.get("icon", ""),
        "forge_icon": item.get("forge_icon", ""),
        "blueprint_id": record.get("blueprint_no") or blueprint_id,
        "recovery_status": "recovered-exact-blueprint-suit-tier-series",
    }, ""


def complete_piece_tiers(piece, suit_id, record_type, equipment, origins, items):
    tiers = [row for row in piece.get("tiers") or [] if isinstance(row, dict)]
    existing = {tier_number(row) for row in tiers}
    existing.discard(None)
    if existing == EXPECTED_TIERS:
        return [], [], []

    blueprint_id = int(piece.get("blueprint_id") or 0)
    templates = attribute_templates(tiers)
    sibling_invariant = bool(templates) and all(
        tier_number(row) in EXPECTED_TIERS
        and suffix_matches_tier(row.get("item_id"), int(tier_number(row)))
        for row in tiers
    )
    if not blueprint_id or not sibling_invariant:
        return [], [{
            "record_type": record_type,
            "name": piece.get("name"),
            "blueprint_id": blueprint_id,
            "suit_id": suit_id,
            "reason": "Existing Tier series does not prove exact variant recovery invariants",
        }], []

    recipes = {
        int(row.get("tier")): row
        for row in piece.get("crafting_recipes") or []
        if isinstance(row, dict) and str(row.get("tier") or "").isdigit()
    }
    recovered = []
    unresolved = []
    conflicts = []

    for tier in sorted(EXPECTED_TIERS - existing):
        candidates = exact_variant_candidates(
            equipment, origins, blueprint_id, suit_id, tier
        )
        if len(candidates) != 1:
            unresolved.append({
                "record_type": record_type,
                "name": piece.get("name"),
                "blueprint_id": blueprint_id,
                "suit_id": suit_id,
                "tier": tier,
                "candidate_item_ids": [int(value[0]) for value in candidates],
                "reason": "Missing Tier did not resolve one unique exact variant row",
            })
            continue

        item_id, record, origin_id, origin = candidates[0]
        item = items.get(item_id, {})
        tier_row, error = build_exact_tier(
            item_id, record, origin, item, tier, blueprint_id, templates
        )
        if tier_row is None:
            unresolved.append({
                "record_type": record_type,
                "name": piece.get("name"),
                "blueprint_id": blueprint_id,
                "suit_id": suit_id,
                "tier": tier,
                "candidate_item_ids": [int(item_id)],
                "reason": error,
            })
            continue

        tiers.append(tier_row)
        recovered.append({
            "record_type": record_type,
            "name": piece.get("name"),
            "blueprint_id": blueprint_id,
            "suit_id": suit_id,
            "tier": tier,
            "item_id": int(item_id),
            "origin_id": int(origin_id) if origin_id.isdigit() else origin_id,
            "classification": "recovered-exact-variant-series-evidence",
        })

        recipe = recipes.get(tier)
        recipe_output = int(recipe.get("output_item_id") or 0) if recipe else 0
        if recipe_output and recipe_output != int(item_id):
            conflict = {
                "record_type": record_type,
                "name": piece.get("name"),
                "blueprint_id": blueprint_id,
                "suit_id": suit_id,
                "tier": tier,
                "stat_item_id": int(item_id),
                "recipe_output_item_id": recipe_output,
                "classification": "crafting-output-variant-conflict",
                "reason": "Recipe output is not the exact player-facing suit-variant stat row",
            }
            conflicts.append(conflict)
            recipe["variant_identity_status"] = "unresolved-output-variant"
            recipe["variant_stat_item_id"] = int(item_id)

    piece["tiers"] = sorted(
        tiers, key=lambda row: int(row.get("data_level") or 0)
    )
    return recovered, unresolved, conflicts
