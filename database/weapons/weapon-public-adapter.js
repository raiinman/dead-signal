(() => {
  'use strict';

  const published = window.DS_WEAPONS_WEB;
  const validContract = !!published
    && published.schema === 'dead-signal-weapons'
    && published.schema_version === 1
    && Array.isArray(published.weapons)
    && published.weapons.length > 0;
  if (!validContract) return;

  const STAR_CAPS = Object.freeze({ common: 3, rare: 4, epic: 5, legendary: 6 });
  const LEGAL_TIERS = Object.freeze([1, 2, 3, 4, 5]);

  const isFiniteNumber = (value) => (
    typeof value === 'number' && Number.isFinite(value)
  );

  const hasExactNumbers = (values, expected) => (
    values.length === expected.length
    && new Set(values).size === expected.length
    && expected.every((value) => values.includes(value))
  );

  const validProgressionFor = (weapon) => {
    const progression = weapon?.progression;
    if (!progression || progression.formula_status !== 'proven-static-base-attack') return false;
    if ((progression.validation_issues || []).length) return false;

    const gearTiers = progression.gear_tiers;
    if (!Array.isArray(gearTiers) || gearTiers.length !== 5) return false;
    const tierNumbers = gearTiers.map((row) => row?.tier);
    if (!hasExactNumbers(tierNumbers, LEGAL_TIERS)) return false;

    const matrix = progression.tier_star_matrix;
    if (!Array.isArray(matrix) || matrix.length !== 5) return false;
    const matrixTiers = matrix.map((row) => row?.gear_tier);
    if (!hasExactNumbers(matrixTiers, LEGAL_TIERS)) return false;

    const rarity = String(weapon?.rarity || '').trim().toLowerCase();
    const starCap = STAR_CAPS[rarity];
    if (!starCap) return false;
    const expectedStars = Array.from({ length: starCap }, (_, index) => index + 1);

    return matrix.every((row) => {
      if (!isFiniteNumber(row?.tier_base_attack_at_1_star)) return false;
      const stars = row?.blueprint_star_values;
      if (!Array.isArray(stars) || stars.length !== expectedStars.length) return false;
      const starNumbers = stars.map((star) => star?.blueprint_stars);
      if (!hasExactNumbers(starNumbers, expectedStars)) return false;

      return stars.every((star) => {
        if (!isFiniteNumber(star?.preset_attack_ratio)) return false;
        if (!Number.isInteger(star?.base_attack)) return false;
        const expectedAttack = Math.trunc(row.tier_base_attack_at_1_star * star.preset_attack_ratio);
        return star.base_attack === expectedAttack;
      });
    });
  };

  const canonicalIds = published.weapons.map((weapon) => String(weapon?.canonical_id || '').trim());
  const uniqueIds = canonicalIds.length === new Set(canonicalIds).size && canonicalIds.every(Boolean);
  const validProgression = published.weapons.every(validProgressionFor);
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
