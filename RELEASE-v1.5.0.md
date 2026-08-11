# Dead Signal Build Lab v1.5.0

## Calibration Style-first workflow

Calibration Blueprints are no longer presented as one flat list of rarity-duplicated records.

### New selection order

1. **Calibration Style / Mod Type** — the first picker groups compatible calibration records by their fixed style family (for example `Energy`, `Heavy`, `Precision`, `Rapid`, `Vanguard`).
2. **Rarity** — after selecting a style, the native planner cards are filtered to only the available Rare / Epic / Legendary records for that style.
3. The selected native Calibration Blueprint continues to drive compatibility and item identity.
4. **My Gear RNG inputs** remain on the weapon after selection: Weapon DMG roll, rolled secondary attribute, and exact secondary value.

For the current AUG-compatible corpus, the 13 native calibration records collapse into five first-step Styles: Energy, Heavy, Precision, Rapid, and Vanguard.

### Picker presentation

- The legacy `Current Calibration` filter is hidden while the Style-first Calibration picker is active.
- Picker cards remain clean: name, rarity, and description only.
- RNG attributes are not dumped into the picker cards.

### Style naming source

v1.5.0 derives the short Mod Type label from the current Calibration Blueprint name (for example `Rapid Assault Rifle` -> `Rapid`, `Vanguard Rifle` -> `Vanguard`). Dead Signal Miner v1.5.7 is separately tracing the exact localized in-game Style name and description so these derived labels can later be replaced with the game's canonical Style text when available.

### Deployment

Use the established copy-only workflow:

1. cPanel Git Version Control -> Update from Remote
2. Deploy HEAD Commit
3. Hard refresh (`Ctrl+F5`)
