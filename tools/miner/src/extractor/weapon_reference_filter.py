"""Tighten blank-fixed-skill mechanic-reference classification.

The first fallback tracer intentionally starts from exact weapon identities, but
its outbound-reference filter must also be fail-closed. Generic words such as
"effect" and "trigger" occur in ordinary numeric gameplay parameters
(effect_index, trigger distance, checker flags, etc.) and are not identity
references. This module narrows the classifier to fields that explicitly encode
mechanic identifiers or references.
"""

from __future__ import annotations

import re
from typing import Any


STRICT_MECHANIC_FIELD = re.compile(
    r"(?:"
    r"^(?:buff|skill|status|keyword|logic|behavior|ability|passive)$"
    r"|(?:^|_)(?:buff|skill|status|keyword)_?(?:id|ids|no|code|ref)(?:$|_)"
    r"|(?:^|_)(?:logic(?:_tree)?|behavior|ability|passive(?:_skill)?)"
    r"_?(?:id|ids|no|code|ref|name|data)(?:$|_)"
    r"|(?:^|_)(?:effect|trigger)_?(?:id|ids|no|code|ref)(?:$|_)"
    r")",
    re.IGNORECASE,
)


def is_mechanic_reference_field(field: Any) -> bool:
    """Return True only for explicit mechanic identity/reference fields."""
    return bool(STRICT_MECHANIC_FIELD.search(str(field or "")))


def install(module: Any) -> None:
    """Install the strict classifier into weapon_evidence_enrichment."""
    module.MECHANIC_FIELD = STRICT_MECHANIC_FIELD
