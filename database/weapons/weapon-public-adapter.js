(() => {
  'use strict';

  const published = window.DS_WEAPONS_WEB;
  const validContract = !!published
    && published.schema === 'dead-signal-weapons'
    && published.schema_version === 1
    && Array.isArray(published.weapons)
    && published.weapons.length > 0;
  if (!validContract) return;

  const canonicalIds = published.weapons.map((weapon) => String(weapon?.canonical_id || '').trim());
  const uniqueIds = canonicalIds.length === new Set(canonicalIds).size && canonicalIds.every(Boolean);
  const validProgression = published.weapons.every((weapon) => (
    weapon
    && weapon.progression?.formula_status === 'proven-static-base-attack'
    && Array.isArray(weapon.progression?.tier_star_matrix)
    && weapon.progression.tier_star_matrix.length === 5
    && !(weapon.progression?.validation_issues || []).length
  ));
  if (!uniqueIds || !validProgression) return;

  const weapons = published.weapons.map((weapon) => ({
    canonical_id: weapon.canonical_id,
    blueprint_id: weapon.blueprint_id,
    item_id: weapon.item_id,
    name: weapon.name,
    category: weapon.category,
    rarity: weapon.rarity,
    image_asset: weapon.image_asset || '',
    acquisition_hint: weapon.acquisition?.hint || '',
    item_gain_path: weapon.acquisition?.gain_path || '',
    static_inputs: {
      weapon_effect: weapon.effect || null,
      ranged_stats: weapon.baseline?.ranged || null,
      melee_stats: weapon.baseline?.melee || null,
    },
    tier_star_matrix: weapon.progression?.tier_star_matrix || [],
    formula_status: weapon.progression?.formula_status,
    validation_issues: weapon.progression?.validation_issues || [],
    public_contract: weapon,
  }));

  window.DS_WEAPON_MATH = {
    schema: 'dead-signal-weapon-math-public-compat',
    schema_version: published.schema_version,
    generated_utc: published.generated_utc,
    formula_contract: published.formula_contract || {},
    source_contract: 'dead-signal-weapons',
    record_counts: published.record_counts || {},
    weapons,
  };
})();
