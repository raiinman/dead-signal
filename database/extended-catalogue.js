(() => {
  'use strict';

  const category = document.body.dataset.category;
  const configs = {
    calibrations: ['dead-signal-calibrations-current', window.DS_CALIBRATIONS_WEB, 'families', 'Calibration families'],
    mods: ['dead-signal-mods', window.DS_MODS_WEB, 'families', 'Mod families'],
    attachments: ['dead-signal-attachments', window.DS_ATTACHMENTS_WEB, 'attachments', 'Weapon attachments'],
    deviations: ['dead-signal-deviations', window.DS_DEVIATIONS_WEB, 'families', 'Deviation families'],
    cradles: ['dead-signal-cradles', window.DS_CRADLES_WEB, 'families', 'Cradle families'],
  };
  const config = configs[category];
  if (!config) return;

  const [schema, data, collection, label] = config;
  const grid = document.getElementById('dbGrid');
  const unavailable = document.getElementById('dbUnavailable');
  const status = document.getElementById('dbStatus');
  const search = document.getElementById('dbSearch');
  const primary = document.getElementById('dbPrimary');
  const rarity = document.getElementById('dbRarity');
  const count = document.getElementById('dbCount');
  const clear = document.getElementById('dbClear');
  const text = (value) => String(value ?? '').trim();
  const variants = (row) => Array.isArray(row.variants) ? row.variants : [row];
  const name = (row) => text(row.name) || text(variants(row)[0]?.name) || 'Unnamed record';
  const rarities = (row) => [...new Set(variants(row).map((item) => text(item.rarity)).filter(Boolean))];

  function verifiedContract() {
    if (!data || data.schema !== schema || !Array.isArray(data[collection])) return false;
    if (category !== 'calibrations') return true;
    return data.schema_version === 2
      && data.publication_status === 'ready-current-system'
      && data.expected_current_families === 94
      && data[collection].length === 94
      && !(data.ambiguous_family_ids || []).length
      && data[collection].every((row) => Array.isArray(row.variants) && row.variants.length === 1);
  }

  if (!verifiedContract()) {
    grid.hidden = true;
    unavailable.hidden = false;
    status.textContent = `${label} route prepared · verified compact contract not materialized.`;
    return;
  }

  const records = data[collection];
  count.textContent = records.length.toLocaleString();

  function calibrationSummary(row, item) {
    const roll = item?.roll_range || {};
    const minimum = Number(roll.minimum_percent);
    const maximum = Number(roll.maximum_percent);
    const range = Number.isFinite(minimum) && Number.isFinite(maximum)
      ? `${minimum}–${maximum}% Weapon DMG roll`
      : 'Weapon DMG roll range unresolved';
    const compatibility = (item?.weapon_type_codes || []).length
      ? `Weapon types ${item.weapon_type_codes.join(', ')}`
      : 'Weapon compatibility unresolved';
    return [`Style ${item?.style_code ?? '—'}`, text(item?.description), `${range} · ${compatibility}`];
  }

  function summary(row) {
    const list = variants(row);
    if (category === 'attachments') {
      return [text(row.attachment_type) || 'Weapon attachment', text(row.effects || row.description), `Accessory ${row.accessory_code ?? '—'} · Affix ${row.affix_code ?? '—'}`];
    }
    if (category === 'calibrations') return calibrationSummary(row, list[0]);
    if (category === 'mods') {
      return [`Mod code ${row.family_key ?? '—'}`, list.length > 1 ? 'All mined variants for this proven mod family are preserved.' : text(list[0]?.description), `${list.length} variant${list.length === 1 ? '' : 's'} · ${rarities(row).join(', ') || 'rarity unresolved'}`];
    }
    if (category === 'deviations') {
      return [list.length > 1 ? `${list.length} source variants` : 'Player-facing Deviation', text(list[0]?.skills?.[0]?.description || list[0]?.skill_catalog?.[0]?.description), `Source IDs ${list.map((item) => item.id).filter((value) => value != null).join(', ') || '—'}`];
    }
    return [list.length > 1 ? `${list.length} source variants` : 'Cradle Override', text(list[0]?.description), `Source IDs ${list.map((item) => item.id).filter((value) => value != null).join(', ') || '—'}`];
  }

  function addOption(select, value) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    select.append(option);
  }

  [...new Set(records.map((row) => summary(row)[0]).filter(Boolean))].sort().forEach((value) => addOption(primary, value));
  const rarityValues = [...new Set(records.flatMap(rarities))].sort();
  rarityValues.forEach((value) => addOption(rarity, value));
  if (!rarityValues.length) rarity.closest('label')?.setAttribute('hidden', '');

  function appendText(parent, tag, value, className = '') {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = value;
    parent.append(node);
    return node;
  }

  function card(row) {
    const [primaryText, description, details] = summary(row);
    const list = variants(row);
    const rs = rarities(row);
    const article = document.createElement('article');
    article.className = 'db-card';
    if (rs.length === 1) article.classList.add(`rarity-${rs[0]}`);
    appendText(article, 'small', primaryText);
    appendText(article, 'h2', name(row));
    appendText(article, 'p', description || 'No player-facing description is resolved in the current compact contract.');

    const meta = document.createElement('div');
    meta.className = 'meta';
    const evidence = document.createElement('div');
    appendText(evidence, 'span', 'Evidence');
    appendText(evidence, 'b', details);
    const variantCount = document.createElement('div');
    appendText(variantCount, 'span', 'Variants');
    appendText(variantCount, 'b', String(list.length));
    meta.append(evidence, variantCount);
    article.append(meta);

    if (list.length > 1) {
      const variantList = document.createElement('div');
      variantList.className = 'variant-list';
      appendText(variantList, 'small', 'Source variants preserved');
      list.slice(0, 6).forEach((item) => {
        const variant = document.createElement('div');
        variant.className = 'variant';
        appendText(variant, 'strong', text(item.name) || `Source ${item.id ?? item.item_id ?? 'record'}`);
        const suffix = item.item_id ? ` · item ${item.item_id}` : '';
        appendText(variant, 'span', `${text(item.rarity)}${suffix}`);
        variantList.append(variant);
      });
      article.append(variantList);
    }
    return article;
  }

  function render() {
    const query = search.value.trim().toLowerCase();
    const visible = records.filter((row) => {
      const [primaryText, description, details] = summary(row);
      const haystack = `${name(row)} ${primaryText} ${description} ${details}`.toLowerCase();
      return (!query || haystack.includes(query))
        && (!primary.value || primaryText === primary.value)
        && (!rarity.value || rarities(row).includes(rarity.value));
    });
    grid.replaceChildren(...visible.map(card));
    status.textContent = `${visible.length} of ${records.length} ${label.toLowerCase()} shown · ${text(data.publication_status) || 'compact Miner contract'}.`;
  }

  search.addEventListener('input', render);
  primary.addEventListener('change', render);
  rarity.addEventListener('change', render);
  clear.addEventListener('click', () => {
    search.value = '';
    primary.value = '';
    rarity.value = '';
    render();
    search.focus();
  });
  render();
})();
