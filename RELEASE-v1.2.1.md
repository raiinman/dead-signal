# Dead Signal Ultimate Planner v1.2.1

## Purpose
Production layout/cache hotfix plus current July 2026 catalog refresh.

## Layout / production fixes
- Replaced the run-on Community Corpus strip with a structured responsive status deck.
- Coverage metrics are individual cards with wrapping, spacing, and compact progress treatment.
- Community reference totals are explicitly snapshots; when Dead Signal has more current indexed records than a reference total, the UI marks the reference as stale rather than treating the newer records as invalid.
- Added asset query-versioning for CSS, planner JS, and community data.
- Changed active-development cache policy to revalidate HTML/CSS/JS so mixed-version layouts do not persist after cPanel deployment.

## Catalog refresh
Added current official 2026 records without inventing unknown comparable T5 values:
- FP-9
- EBR-14 - Octopus! Grilled Rings!
- QBJ97 - Fiery Trees and Silver Flowers (LMG)
- SN700 - Finale
- Wind Interpreter Cap
- Ankh Mask
- Ghost Link Set and its six armor pieces

QBJ97's LMG classification is confirmed by the official Once Human Version 3.0.1 July 9 update, which identifies QBJ97 as a Light Machine Gun.

## Data rules retained
- Gear Tier remains I-V only.
- Blueprint Stars remain separate and rarity-capped.
- Unknown values remain unknown/pending rather than being represented as zero.
- Source names remain available for provenance, with no outbound source URLs shipped in the client data.
- Planner remains planner-first; no speculative advanced damage math.

## Schema
Planner schema remains 14; this release does not require a saved-build state migration.
