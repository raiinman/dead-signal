(() => {
  'use strict';

  const source = window.DS_WEAPON_MATH || {};
  const finite = (value) => value !== null && value !== undefined && value !== '' && typeof value !== 'boolean' && Number.isFinite(Number(value));
  const attrValue = (cell, key) => {
    const value = cell?.base_attributes?.find((item) => item.key === key)?.value;
    return finite(value) ? Number(value) * 100 : undefined;
  };

  const weapons = (source.weapons || []).map((record) => {
    const tier = record.tier_star_matrix?.at(-1);
    const cell = tier?.blueprint_star_values?.[0];
    const ranged = record.static_inputs?.ranged_stats || {};
    const melee = record.static_inputs?.melee_stats || {};
    return {
      id: record.canonical_id,
      itemId: String(record.item_id),
      blueprintId: String(record.blueprint_id),
      name: record.name,
      type: record.category,
      rarity: record.rarity,
      description: '',
      acquisition: record.acquisition_hint || record.item_gain_path || '',
      feature: record.static_inputs?.weapon_effect?.description || '',
      imageAsset: record.image_asset || '',
      imageStatus: record.image_status || 'unresolved',
      coverage: 'Installed-game Miner weapon projection',
      sources: [{ site: 'Installed game snapshot' }],
      stats: {
        damage: cell?.base_attack,
        rpm: ranged.rpm,
        magazine: ranged.magazine,
        reload: ranged.reload_seconds,
        range: ranged.range_meters,
        effectiveRange: ranged.full_damage_distance,
        accuracy: ranged.accuracy,
        stability: ranged.stability,
        mobility: ranged.mobility,
        attackSpeed: melee.attack_speed,
        attackRange: melee.attack_range,
        critRate: attrValue(cell, 'crit_rate'),
        critDamage: attrValue(cell, 'crit_dam_rate'),
        weakspot: attrValue(cell, 'weak_dam_rate'),
      },
    };
  });

  window.DS_WEAPON_DATA = Object.freeze(weapons);

  // The unchecked-in legacy planner core still reads this container. Replace
  // only its weapon pool before app.js initializes; no legacy weapon survives.
  window.DS_COMMUNITY = { ...(window.DS_COMMUNITY || {}), weapons: window.DS_WEAPON_DATA };
})();
