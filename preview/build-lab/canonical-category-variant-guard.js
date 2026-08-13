(() => {
  'use strict';

  const blocked = {};
  const block = (globalName, category, data, reason, extra = {}) => {
    blocked[category] = Object.freeze({
      schema: data?.schema,
      schema_version: data?.schema_version,
      publication_status: data?.publication_status,
      reason,
      ...extra,
    });
    window[globalName] = null;
  };

  const attachments = window.DS_ATTACHMENTS_WEB;
  if (attachments) {
    const slots = attachments.slot_types || [];
    const requiredSlots = ['Magazine', 'Muzzle', 'Sight', 'Tactical'];
    const ready = attachments.schema === 'dead-signal-attachments'
      && attachments.schema_version === 1
      && attachments.publication_status === 'ready'
      && Array.isArray(attachments.attachments)
      && !(attachments.duplicate_canonical_ids || []).length
      && requiredSlots.every((slot) => slots.includes(slot));
    if (!ready) block('DS_ATTACHMENTS_WEB', 'attachments', attachments, 'attachment-contract-not-ready');
  }

  const guardFamilyContract = (globalName, category, expectedSchema, expectedStatus) => {
    const data = window[globalName];
    if (!data) return;
    if (data.schema !== expectedSchema || data.schema_version !== 1 || data.publication_status !== expectedStatus || !Array.isArray(data.families)) {
      block(globalName, category, data, 'family-contract-not-ready');
      return;
    }
    const ambiguous = data.families.filter((family) => !Array.isArray(family.variants) || family.variants.length !== 1);
    if (!ambiguous.length) return;
    block(globalName, category, data, 'ambiguous-family-variants', {
      family_count: data.families.length,
      ambiguous_family_count: ambiguous.length,
      ambiguous_family_ids: ambiguous.map((family) => family.canonical_id || family.family_key || null),
    });
  };

  guardFamilyContract(
    'DS_DEVIATIONS_WEB',
    'deviations',
    'dead-signal-deviations',
    'display-name-families-with-source-variants-preserved',
  );
  guardFamilyContract(
    'DS_CRADLES_WEB',
    'cradles',
    'dead-signal-cradles',
    'display-name-families-with-source-variants-preserved',
  );
  window.DSCanonicalCategoryVariantGuard = Object.freeze(blocked);
})();
