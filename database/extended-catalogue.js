(() => {
  'use strict';
  const category = document.body.dataset.category;
  const config = {
    calibrations: ['dead-signal-calibrations', window.DS_CALIBRATIONS_WEB, 'families', 'Calibration families'],
    mods: ['dead-signal-mods', window.DS_MODS_WEB, 'families', 'Mod families'],
    attachments: ['dead-signal-attachments', window.DS_ATTACHMENTS_WEB, 'attachments', 'Weapon attachments'],
    deviations: ['dead-signal-deviations', window.DS_DEVIATIONS_WEB, 'families', 'Deviation families'],
    cradles: ['dead-signal-cradles', window.DS_CRADLES_WEB, 'families', 'Cradle families'],
  }[category];
  if (!config) return;
  const [schema, data, collection, label] = config;
  const grid = document.getElementById('dbGrid');
  const unavailable = document.getElementById('dbUnavailable');
  const status = document.getElementById('dbStatus');
  const search = document.getElementById('dbSearch');
  const primary = document.getElementById('dbPrimary');
  const rarity = document.getElementById('dbRarity');
  const count = document.getElementById('dbCount');
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const text = (value) => String(value ?? '').trim();
  const variants = (row) => Array.isArray(row.variants) ? row.variants : [row];
  const name = (row) => text(row.name) || text(variants(row)[0]?.name) || 'Unnamed record';
  const rarities = (row) => [...new Set(variants(row).map((item) => text(item.rarity)).filter(Boolean))];

  if (!data || data.schema !== schema || !Array.isArray(data[collection])) {
    grid.hidden = true;
    unavailable.hidden = false;
    status.textContent = `${label} route prepared · verified compact contract not materialized.`;
    return;
  }
  const records = data[collection];
  count.textContent = records.length.toLocaleString();

  function summary(row) {
    const list = variants(row);
    if (category === 'attachments') return [text(row.attachment_type) || 'Weapon attachment', text(row.effects || row.description), `Accessory ${row.accessory_code ?? '—'} · Affix ${row.affix_code ?? '—'}`];
    if (category === 'calibrations') return [list.length > 1 ? `${list.length} source variants` : `Style ${list[0]?.style_code ?? '—'}`, list.length > 1 ? 'Current and legacy source variants are preserved until provenance selects the current record.' : text(list[0]?.description), `Group ${row.family_key ?? '—'} · ${rarities(row).join(', ') || 'rarity unresolved'}`];
    if (category === 'mods') return [`Mod code ${row.family_key ?? '—'}`, list.length > 1 ? 'All mined variants for this proven mod family are preserved.' : text(list[0]?.description), `${list.length} variant${list.length === 1 ? '' : 's'} · ${rarities(row).join(', ') || 'rarity unresolved'}`];
    if (category === 'deviations') return [list.length > 1 ? `${list.length} source variants` : 'Player-facing Deviation', text(list[0]?.skills?.[0]?.description || list[0]?.skill_catalog?.[0]?.description), `Source IDs ${list.map((item) => item.id).filter((value) => value != null).join(', ') || '—'}`];
    return [list.length > 1 ? `${list.length} source variants` : 'Cradle Override', text(list[0]?.description), `Source IDs ${list.map((item) => item.id).filter((value) => value != null).join(', ') || '—'}`];
  }

  [...new Set(records.map((row) => summary(row)[0]).filter(Boolean))].sort().forEach((value) => primary.add(new Option(value, value)));
  const rarityValues = [...new Set(records.flatMap(rarities))].sort();
  rarityValues.forEach((value) => rarity.add(new Option(value, value)));
  if (!rarityValues.length) rarity.closest('label')?.setAttribute('hidden', '');

  function card(row) {
    const [primaryText, description, details] = summary(row);
    const list = variants(row);
    const rs = rarities(row);
    const rarityClass = rs.length === 1 ? ` rarity-${esc(rs[0])}` : '';
    return `<article class="db-card${rarityClass}"><small>${esc(primaryText)}</small><h2>${esc(name(row))}</h2><p>${esc(description || 'No player-facing description is resolved in the current compact contract.')}</p><div class="meta"><div><span>Evidence</span><b>${esc(details)}</b></div><div><span>Variants</span><b>${esc(list.length)}</b></div></div>${list.length > 1 ? `<div class="variant-list"><small>Source variants preserved</small>${list.slice(0,6).map((item) => `<div class="variant"><strong>${esc(text(item.name) || `Source ${item.id ?? item.item_id ?? 'record'}`)}</strong><span>${esc(text(item.rarity))}${item.item_id ? ` · item ${esc(item.item_id)}` : ''}</span></div>`).join('')}</div>` : ''}</article>`;
  }

  function render() {
    const query = search.value.trim().toLowerCase();
    const visible = records.filter((row) => {
      const [primaryText, description, details] = summary(row);
      const haystack = `${name(row)} ${primaryText} ${description} ${details}`.toLowerCase();
      return (!query || haystack.includes(query)) && (!primary.value || primaryText === primary.value) && (!rarity.value || rarities(row).includes(rarity.value));
    });
    grid.innerHTML = visible.map(card).join('');
    status.textContent = `${visible.length} of ${records.length} ${label.toLowerCase()} shown · ${text(data.publication_status) || 'compact Miner contract'}.`;
  }

  [search, primary, rarity].forEach((control) => control.addEventListener(control === search ? 'input' : 'change', render));
  document.getElementById('dbClear').addEventListener('click', () => { search.value = ''; primary.value = ''; rarity.value = ''; render(); search.focus(); });
  render();
})();
