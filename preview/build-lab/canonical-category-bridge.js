(() => {
  'use strict';

  const norm = (value) => String(value ?? '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const ids = (row) => [row?.id, row?.itemId, row?.item_id, row?.canonicalId, row?.canonical_id]
    .filter((value) => value !== null && value !== undefined && value !== '')
    .map(String);

  const configs = {
    calibrations: {
      source: window.DS_CALIBRATIONS_WEB,
      schema: 'dead-signal-calibrations-current',
      records: (data) => (data.families || []).map((family) => ({
        canonical_id: family.canonical_id,
        name: family.name,
        source: (family.variants || [])[0] || {},
      })),
      legacyKeys: ['calibrations', 'calibrationBlueprints'],
    },
    attachments: {
      source: window.DS_ATTACHMENTS_WEB,
      schema: 'dead-signal-attachments',
      records: (data) => (data.attachments || []).map((row) => ({ canonical_id: row.canonical_id, name: row.name, source: row })),
      legacyKeys: ['attachments', 'weaponAttachments'],
    },
    deviations: {
      source: window.DS_DEVIATIONS_WEB,
      schema: 'dead-signal-deviations',
      records: (data) => (data.families || []).map((family) => ({
        canonical_id: family.canonical_id,
        name: family.name,
        source: (family.variants || [])[0] || {},
      })),
      legacyKeys: ['deviations', 'combatDeviations'],
    },
    cradles: {
      source: window.DS_CRADLES_WEB,
      schema: 'dead-signal-cradles',
      records: (data) => (data.families || []).map((family) => ({
        canonical_id: family.canonical_id,
        name: family.name,
        source: (family.variants || [])[0] || {},
      })),
      legacyKeys: ['cradles', 'cradleOverrides'],
    },
  };

  const community = window.DS_COMMUNITY || {};
  const report = { schema: 'dead-signal-build-lab-canonical-bridge', schema_version: 1, categories: {} };

  function legacyPool(keys) {
    for (const key of keys) if (Array.isArray(community[key])) return { key, rows: community[key] };
    return null;
  }

  function findMatch(legacy, record) {
    const sourceIds = new Set([...ids(record), ...ids(record.source)]);
    const byId = legacy.filter((row) => ids(row).some((id) => sourceIds.has(id)));
    if (byId.length === 1) return byId[0];
    const targetName = norm(record.name || record.source?.name);
    if (!targetName) return null;
    const byName = legacy.filter((row) => norm(row.name) === targetName);
    return byName.length === 1 ? byName[0] : null;
  }

  function mergeLegacy(legacy, record) {
    const source = record.source || {};
    return {
      ...legacy,
      canonicalId: record.canonical_id,
      name: record.name || source.name || legacy.name,
      rarity: source.rarity || source.quality || legacy.rarity,
      description: source.description || legacy.description || '',
      imageAsset: source.image_asset || source.image_reference || legacy.imageAsset,
      acquisition: source.gain_path || source.acquisition || legacy.acquisition,
      minedSource: source,
    };
  }

  for (const [category, config] of Object.entries(configs)) {
    const data = config.source;
    if (!data) {
      report.categories[category] = { status: 'contract-not-loaded', applied: false };
      continue;
    }
    if (data.schema !== config.schema) {
      report.categories[category] = { status: 'schema-mismatch', applied: false, schema: data.schema };
      continue;
    }
    const pool = legacyPool(config.legacyKeys);
    if (!pool) {
      report.categories[category] = { status: 'legacy-pool-not-found', applied: false, tried_keys: config.legacyKeys };
      continue;
    }
    const canonical = config.records(data);
    const mapped = [];
    const unmatched = [];
    const used = new Set();
    for (const record of canonical) {
      const match = findMatch(pool.rows, record);
      if (!match) {
        unmatched.push({ canonical_id: record.canonical_id, name: record.name });
        continue;
      }
      const index = pool.rows.indexOf(match);
      if (used.has(index)) {
        unmatched.push({ canonical_id: record.canonical_id, name: record.name, reason: 'duplicate-legacy-match' });
        continue;
      }
      used.add(index);
      mapped.push(mergeLegacy(match, record));
    }
    if (unmatched.length || mapped.length !== canonical.length) {
      report.categories[category] = {
        status: 'mapping-incomplete', applied: false, legacy_key: pool.key,
        canonical_records: canonical.length, mapped_records: mapped.length, unmatched,
      };
      continue;
    }
    community[pool.key] = Object.freeze(mapped);
    report.categories[category] = {
      status: 'canonical-applied', applied: true, legacy_key: pool.key,
      canonical_records: canonical.length, replaced_legacy_records: pool.rows.length,
    };
  }

  window.DS_COMMUNITY = community;
  window.DSCanonicalCategoryBridge = Object.freeze(report);
})();
