# Dead Signal Build Lab v1.4.9

## Calibration picker cleanup

This release corrects the Calibration Blueprint picker after the v1.4.8 RNG-pool presentation proved too dense and semantically misleading.

### Picker card rules

Calibration cards now show only what is true for the blueprint before a specific dropped instance is entered:

- **Guaranteed Weapon DMG RNG range** for the blueprint rarity.
- **Secondary Attribute: Random on drop.**
- Compatibility text remains as supporting information.
- The four possible secondary outcomes are no longer dumped onto every picker card as though all four are active stats.
- The legacy `Current Calibration` label is removed from Calibration Blueprint cards.

The actual secondary stat identity and exact RNG value remain My Gear inputs after the Calibration Blueprint has been selected.

### Fixed Calibration Style

The picker does not invent a Style name or description. Dead Signal Miner v1.5.7 patches the missing `buff_level_data` field aliases and publishes the fixed Style's localized `buff_desc` when the current English translation table resolves it.

### Deployment

Use the established copy-only workflow:

1. cPanel Git Version Control -> Update from Remote
2. Deploy HEAD Commit
3. Hard refresh (`Ctrl+F5`)
