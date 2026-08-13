"""Extract direct player-facing Attachment compatibility wording without inference."""

from __future__ import annotations

import re
from typing import Any


COMPATIBILITY_PATTERN = re.compile(
    r"(?i)(?:can be equipped on|fits all)\s+[^.]+"
)


def direct_compatibility_evidence(description: Any) -> dict[str, str]:
    text = str(description or "").strip().replace("\n", " ")
    match = COMPATIBILITY_PATTERN.search(text)
    if not match:
        return {
            "status": "unresolved",
            "text": "",
            "source_field": "description",
        }
    return {
        "status": "direct-localized-installed-game-text",
        "text": match.group(0).strip(),
        "source_field": "description",
    }
