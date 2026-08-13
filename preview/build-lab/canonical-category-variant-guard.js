(() => {
  'use strict';

  const blocked = {};
  const guardFamilyContract = (globalName, category) => {
    const data = window[globalName];
    if (!data || !Array.isArray(data.families)) return;
    const ambiguous = data.families.filter((family) => !Array.isArray(family.variants) || family.variants.length !== 1);
    if (!ambiguous.length) return;
    blocked[category] = Object.freeze({
      schema: data.schema,
      family_count: data.families.length,
      ambiguous_family_count: ambiguous.length,
      ambiguous_family_ids: ambiguous.map((family) => family.canonical_id || family.family_key || null),
    });
    window[globalName] = null;
  };

  guardFamilyContract('DS_DEVIATIONS_WEB', 'deviations');
  guardFamilyContract('DS_CRADLES_WEB', 'cradles');
  window.DSCanonicalCategoryVariantGuard = Object.freeze(blocked);
})();
