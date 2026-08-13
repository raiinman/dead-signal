'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const adapterSource = fs.readFileSync(
  path.join(ROOT, 'database', 'weapons', 'weapon-public-adapter.js'),
  'utf8',
);

function makeWeapon() {
  const tiers = [1, 2, 3, 4, 5];
  const ratios = [1, 1.05, 1.1, 1.15, 1.2, 1.25];
  return {
    canonical_id: 'ds-w-test',
    blueprint_id: 100,
    item_id: 200,
    name: 'Test Weapon',
    category: 'Sniper Rifle',
    rarity: 'Legendary',
    baseline: { ranged: { rpm: 100 } },
    progression: {
      formula_status: 'proven-static-base-attack',
      validation_issues: [],
      gear_tiers: tiers.map((tier) => ({ tier })),
      tier_star_matrix: tiers.map((gearTier) => {
        const tierBase = 100 * gearTier;
        return {
          gear_tier: gearTier,
          tier_base_attack_at_1_star: tierBase,
          blueprint_star_values: ratios.map((ratio, index) => ({
            blueprint_stars: index + 1,
            preset_attack_ratio: ratio,
            base_attack: Math.trunc(tierBase * ratio),
          })),
        };
      }),
    },
  };
}

function runWith(weapon) {
  const window = {
    DS_WEAPONS_WEB: {
      schema: 'dead-signal-weapons',
      schema_version: 1,
      generated_utc: '2026-08-13T00:00:00Z',
      record_counts: { weapons: 1 },
      weapons: [weapon],
    },
  };
  vm.runInNewContext(adapterSource, { window });
  return window.DS_WEAPON_MATH;
}

assert.ok(runWith(makeWeapon()), 'valid proven progression should be promoted');

{
  const weapon = makeWeapon();
  weapon.progression.tier_star_matrix[0].blueprint_star_values.pop();
  assert.strictEqual(runWith(weapon), undefined, 'missing legal Blueprint Star must fail closed');
}

{
  const weapon = makeWeapon();
  weapon.progression.tier_star_matrix[1].gear_tier = 1;
  assert.strictEqual(runWith(weapon), undefined, 'duplicate/missing Gear Tier must fail closed');
}

{
  const weapon = makeWeapon();
  weapon.progression.tier_star_matrix[2].blueprint_star_values[5].base_attack += 1;
  assert.strictEqual(runWith(weapon), undefined, 'Base Attack formula mismatch must fail closed');
}

{
  const weapon = makeWeapon();
  weapon.progression.tier_star_matrix[3].blueprint_star_values[0].preset_attack_ratio = null;
  assert.strictEqual(runWith(weapon), undefined, 'missing ratio evidence must fail closed');
}

{
  const weapon = makeWeapon();
  weapon.rarity = 'Unknown';
  assert.strictEqual(runWith(weapon), undefined, 'unsupported rarity must fail closed');
}

console.log('weapon-public-adapter contract tests: PASS');
