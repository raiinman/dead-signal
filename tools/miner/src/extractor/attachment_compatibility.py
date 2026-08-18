"""Extract direct player-facing Attachment compatibility wording without inference."""

from __future__ import annotations

import re
from typing import Any


COMPATIBILITY_PATTERN = re.compile(
    r"(?i)(?:can be equipped on|fits all)\s+[^.]+"
)

CATEGORY_PATTERNS = (
    ("Assault Rifle", re.compile(r"\bassault rifles?\b", re.IGNORECASE)),
    ("Bow / Crossbow", re.compile(r"\b(?:bows?|crossbows?)\b", re.IGNORECASE)),
    ("Heavy Weapon", re.compile(r"\bheavy weapons?\b", re.IGNORECASE)),
    ("Light Machine Gun", re.compile(r"\blight machine guns?\b", re.IGNORECASE)),
    ("Pistol", re.compile(r"\bpistols?\b", re.IGNORECASE)),
    ("Shotgun", re.compile(r"\bshotguns?\b", re.IGNORECASE)),
    ("Sniper Rifle", re.compile(r"\bsniper rifles?\b", re.IGNORECASE)),
    ("Submachine Gun", re.compile(r"\b(?:submachine guns?|SMGs?)\b", re.IGNORECASE)),
)


def _structured_scope(text: str) -> dict[str, Any]:
    all_weapons = bool(re.search(r"\ball weapons\b", text, re.IGNORECASE))
    categories = [name for name, pattern in CATEGORY_PATTERNS if pattern.search(text)]
    residual = re.sub(r"(?i)^(?:can be equipped on|fits all)\s+", "", text)
    for _, pattern in CATEGORY_PATTERNS:
        residual = pattern.sub("", residual)
    residual = re.sub(
        r"(?i)\b(?:all|types?|of|and|series|weapons?|above|common|rarity)\b|[(),]",
        " ",
        residual,
    )
    named_weapon_text_present = bool(re.search(r"[A-Za-z0-9]", residual)) and not all_weapons
    if all_weapons:
        scope = "all-weapons"
    elif categories and named_weapon_text_present:
        scope = "mixed-categories-and-named-weapons"
    elif categories:
        scope = "weapon-categories"
    elif named_weapon_text_present:
        scope = "named-weapons-only"
    else:
        scope = "unresolved"
    return {
        "scope": scope,
        "compatible_weapon_categories": categories,
        "all_weapons": all_weapons,
        "named_weapon_text_present": named_weapon_text_present,
    }


def direct_compatibility_evidence(description: Any) -> dict[str, Any]:
    text = str(description or "").strip().replace("\n", " ")
    match = COMPATIBILITY_PATTERN.search(text)
    if not match:
        return {
            "status": "unresolved",
            "text": "",
            "source_field": "description",
            "scope": "unresolved",
            "compatible_weapon_categories": [],
            "all_weapons": False,
            "named_weapon_text_present": False,
        }
    matched_text = match.group(0).strip()
    return {
        "status": "direct-localized-installed-game-text",
        "text": matched_text,
        "source_field": "description",
        **_structured_scope(matched_text),
    }
