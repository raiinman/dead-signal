(() => {
  'use strict';

  const mathData = window.DS_WEAPON_MATH || {};
  const normalizeName = (value) => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const defaultCell = (math) => math?.tier_star_matrix?.at(-1)?.blueprint_star_values?.[0] || null;
  const weapons = (mathData.weapons || []).map((math) => {
    const ranged = math.static_inputs?.ranged_stats || {};
    const melee = math.static_inputs?.melee_stats || {};
    const cell = defaultCell(math);
    return {
      id: math.canonical_id, plannerId: math.canonical_id,
      itemId: String(math.item_id), blueprintId: String(math.blueprint_id), name: math.name, type: math.category,
      rarity: math.rarity, feature: math.static_inputs?.weapon_effect?.description || math.short_description || '',
      acquisition: math.acquisition_hint || math.item_gain_path || '', imageAsset: math.image_asset || '',
      stats: { damage: cell?.base_attack, rpm: ranged.rpm, magazine: ranged.magazine,
        reload: ranged.reload_seconds, range: ranged.range_meters, accuracy: ranged.accuracy,
        stability: ranged.stability, mobility: ranged.mobility ?? melee.mobility },
      coverage: 'Installed-game Miner v1.5.11.0', sources: [{ site: 'Installed game snapshot' }], math,
    };
  });
  const rarityRank = { Common: 1, Rare: 2, Epic: 3, Legendary: 4 };

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const number = (value, fallback = '—') => Number.isFinite(Number(value)) ? Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 }) : fallback;
  const effect = (item) => String(item.feature || item.effect || item.description || '').trim();
  const rarityClass = (item) => `rarity-${String(item.rarity || 'unknown').toLowerCase()}`;
  const imageUrl = (item) => {
    const path = String(item.imageAsset || item.imageRef || '').replace(/\\/g, '/');
    if (!path) return '';
    if (/^(https?:|data:|\/)/.test(path)) return path.startsWith('/assets/') ? `/build-planner${path}` : path;
    return `/build-planner/${path.replace(/^\.\//, '')}`;
  };
  const detailUrl = (item) => `detail/?weapon=${encodeURIComponent(item.blueprintId)}`;
  const plannerUrl = (item, tier, stars) => {
    const params = new URLSearchParams({ 'catalogue-weapon': item.plannerId || item.itemId, 'catalogue-name': item.name,
      'catalogue-slot': item.type === 'Melee' ? 'melee' : 'primary' });
    if (tier) params.set('catalogue-tier', tier);
    if (stars) params.set('catalogue-stars', stars);
    return `/build-planner/?${params.toString()}#weapons`;
  };

  function card(item) {
    const stats = item.stats || {};
    const source = item.sources?.[0]?.site || 'Source pending';
    const image = imageUrl(item);
    return `<article class="weapon-card ${rarityClass(item)}" data-name="${esc(item.name)}">
      <a class="weapon-art" href="${detailUrl(item)}" aria-label="View ${esc(item.name)} details">${image ? `<img src="${esc(image)}" alt="${esc(item.name)}" loading="lazy" decoding="async">` : '<span>IMAGE PENDING</span>'}<i>${esc(item.rarity || 'Unverified')}</i></a>
      <div class="weapon-card-body"><p class="weapon-type">${esc(item.type || 'Type unverified')}</p><h2><a href="${detailUrl(item)}">${esc(item.name)}</a></h2>
      <dl><div><dt>Base Attack</dt><dd>${number(stats.damage)}</dd></div><div><dt>Fire Rate</dt><dd>${number(stats.rpm)}</dd></div><div><dt>Magazine</dt><dd>${number(stats.magazine)}</dd></div></dl>
      <p class="effect-preview">${esc(effect(item) || 'Detailed weapon effect has not been indexed for this record.')}</p>
      <p class="source-line">Source: ${esc(source)}</p>
      <div class="card-actions"><a href="${detailUrl(item)}">Inspect</a><button type="button" data-compare-id="${esc(item.id)}">Compare</button><a class="configure" href="${plannerUrl(item)}">Add to Build</a></div></div>
    </article>`;
  }

  function initBrowse() {
    const grid = document.getElementById('weaponGrid');
    const error = document.getElementById('catalogueError');
    if (!weapons.length) { error.hidden = false; grid.hidden = true; document.getElementById('resultStatus').textContent = 'No verified records loaded.'; return; }
    document.getElementById('weaponTotal').textContent = weapons.length;
    const search = document.getElementById('weaponSearch');
    const type = document.getElementById('typeFilter');
    const rarity = document.getElementById('rarityFilter');
    const sort = document.getElementById('weaponSort');
    const status = document.getElementById('resultStatus');
    const selected = new Set();

    [...new Set(weapons.map((item) => item.type).filter(Boolean))].sort().forEach((value) => type.add(new Option(value, value)));
    [...new Set(weapons.map((item) => item.rarity).filter(Boolean))].sort((a, b) => (rarityRank[b] || 0) - (rarityRank[a] || 0)).forEach((value) => rarity.add(new Option(value, value)));

    function render() {
      const query = search.value.trim().toLowerCase();
      let items = weapons.filter((item) => (!query || `${item.name} ${item.type} ${item.rarity} ${effect(item)}`.toLowerCase().includes(query)) && (!type.value || item.type === type.value) && (!rarity.value || item.rarity === rarity.value));
      const [key, direction] = sort.value.split('-');
      items.sort((a, b) => {
        if (key === 'name') return a.name.localeCompare(b.name);
        if (key === 'rarity') return (rarityRank[b.rarity] || 0) - (rarityRank[a.rarity] || 0) || a.name.localeCompare(b.name);
        return ((Number(b.stats?.[key]) || 0) - (Number(a.stats?.[key]) || 0)) * (direction === 'desc' ? 1 : -1) || a.name.localeCompare(b.name);
      });
      grid.innerHTML = items.map(card).join('');
      status.textContent = `${items.length} of ${weapons.length} weapons shown${selected.size ? ` · ${selected.size}/2 selected to compare` : ''}.`;
    }

    [search, type, rarity, sort].forEach((control) => control.addEventListener(control === search ? 'input' : 'change', render));
    document.getElementById('clearFilters').addEventListener('click', () => { search.value = ''; type.value = ''; rarity.value = ''; sort.value = 'name'; render(); search.focus(); });
    document.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => { document.querySelectorAll('[data-view]').forEach((item) => { item.classList.toggle('active', item === button); item.setAttribute('aria-pressed', String(item === button)); }); grid.classList.toggle('list-view', button.dataset.view === 'list'); }));
    grid.addEventListener('click', (event) => {
      const button = event.target.closest('[data-compare-id]');
      if (!button) return;
      selected.has(button.dataset.compareId) ? selected.delete(button.dataset.compareId) : selected.size < 2 && selected.add(button.dataset.compareId);
      grid.querySelectorAll('[data-compare-id]').forEach((item) => { const active = selected.has(item.dataset.compareId); item.classList.toggle('selected', active); item.textContent = active ? 'Selected' : 'Compare'; });
      if (selected.size === 2) showCompare([...selected]);
      renderStatus();
    });
    function renderStatus() { const visible = grid.querySelectorAll('.weapon-card').length; status.textContent = `${visible} of ${weapons.length} weapons shown${selected.size ? ` · ${selected.size}/2 selected to compare` : ''}.`; }
    render();
  }

  function showCompare(ids) {
    const items = ids.map((id) => weapons.find((item) => item.id === id)).filter(Boolean);
    if (items.length !== 2) return;
    let dialog = document.getElementById('catalogueCompare');
    if (!dialog) { dialog = document.createElement('dialog'); dialog.id = 'catalogueCompare'; dialog.className = 'compare-dialog'; document.body.append(dialog); }
    const rows = [['damage', 'Base Attack'], ['rpm', 'Fire Rate'], ['magazine', 'Magazine'], ['reload', 'Reload'], ['critRate', 'Crit Rate'], ['critDamage', 'Crit DMG'], ['weakspot', 'Weakspot'], ['range', 'Range'], ['mobility', 'Mobility']];
    dialog.innerHTML = `<div class="compare-head"><div><p class="eyebrow"><span></span> Raw indexed comparison</p><h2>${esc(items[0].name)} <em>vs</em> ${esc(items[1].name)}</h2></div><button type="button" aria-label="Close comparison">×</button></div><p class="compare-note">Tier, Blueprint Stars, Calibration, attachments, and derived DPS are not applied.</p><div class="compare-table"><div class="compare-row headings"><b>${esc(items[0].name)}</b><span>STAT</span><b>${esc(items[1].name)}</b></div>${rows.map(([key, label]) => `<div class="compare-row"><b>${number(items[0].stats?.[key])}</b><span>${label}</span><b>${number(items[1].stats?.[key])}</b></div>`).join('')}</div>`;
    dialog.querySelector('button').addEventListener('click', () => dialog.close());
    dialog.showModal();
  }

  function initDetail() {
    const shell = document.getElementById('weaponDetail');
    const id = document.body.dataset.detailId || new URLSearchParams(location.search).get('weapon');
    const item = weapons.find((weapon) => weapon.blueprintId === id || weapon.id === id || normalizeName(weapon.name) === normalizeName(id));
    if (!item) { shell.innerHTML = '<div class="catalogue-error"><strong>WEAPON RECORD UNAVAILABLE</strong><p>No verified record matched this route.</p><a href="../">Return to all weapons</a></div>'; return; }
    const stats = item.stats || {};
    const tiers = item.math?.tier_star_matrix || [];
    const image = imageUrl(item);
    shell.innerHTML = `<nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../../../">Database</a><span>/</span><a href="../">Weapons</a><span>/</span><b>${esc(item.name)}</b></nav>
      <section class="detail-hero ${rarityClass(item)}"><div class="detail-art">${image ? `<img src="${esc(image)}" alt="${esc(item.name)}">` : '<span>IMAGE PENDING</span>'}</div><div><p class="eyebrow"><span></span> ${esc(item.type)} // ${esc(item.rarity)}</p><h1>${esc(item.name)}</h1><p>${esc(item.acquisition || 'Acquisition information is not indexed for this record.')}</p><div class="detail-actions"><a class="configure" id="plannerLink" href="${plannerUrl(item)}">Configure in Build Planner</a><a href="../">Compare with another weapon</a></div></div></section>
      <section class="detail-grid"><article><p class="section-code">01 // Indexed stats</p><h2>Player-facing baseline</h2><dl class="detail-stats">${[['damage','Tier V Base Attack'],['rpm','Fire Rate'],['magazine','Magazine'],['reload','Reload'],['accuracy','Accuracy'],['stability','Stability'],['range','Range'],['mobility','Mobility']].map(([key,label])=>`<div><dt>${label}</dt><dd>${number(stats[key])}</dd></div>`).join('')}</dl></article>
      <article><p class="section-code">02 // Weapon mechanic</p><h2>Indexed effect</h2><p class="full-effect">${esc(effect(item) || 'No weapon effect is attached to this installed-game record.')}</p></article></section>
      <section class="progression-panel"><p class="section-code">03 // Proven static math</p><h2>Gear Tier and Blueprint Stars</h2><p>Choose a legal configuration. Base Attack is calculated from installed-game tier and blueprint data; it is not configured DPS.</p>${tiers.length ? `<div class="math-config"><label><span>Gear Tier</span><select id="gearTier">${tiers.map((tier) => `<option value="${tier.gear_tier}"${tier === tiers.at(-1) ? ' selected' : ''}>Tier ${['I','II','III','IV','V'][tier.gear_tier - 1]}</option>`).join('')}</select></label><label><span>Blueprint Stars</span><select id="blueprintStars"></select></label><div class="math-result"><span>Verified Base Attack</span><strong id="calculatedAttack">—</strong><small id="calculationTrace"></small></div></div><div class="tier-grid">${tiers.map((tier)=>`<div><span>Tier ${['I','II','III','IV','V'][tier.gear_tier - 1]}</span><strong>${number(tier.tier_base_attack_at_1_star)}</strong><small>Base Attack at 1★</small></div>`).join('')}</div>` : '<p class="pending">Tier progression is not available for this record.</p>'}</section>
      <section class="provenance-panel"><p class="section-code">04 // Verification</p><h2>Source and limits</h2><div><p><b>Coverage</b><span>${esc(item.coverage)}</span></p><p><b>Source</b><span>Installed game snapshot</span></p><p><b>Blueprint ID</b><span>${esc(item.blueprintId)}</span></p></div><p class="limits">Formula: <code>${esc(mathData.formula_contract?.base_attack || 'Not recorded')}</code>. Calibration, attachments, conditional effects, enemy defenses, and configured DPS are not applied.</p></section>`;

    const tierControl = document.getElementById('gearTier');
    const starControl = document.getElementById('blueprintStars');
    const attack = document.getElementById('calculatedAttack');
    const trace = document.getElementById('calculationTrace');
    const plannerLink = document.getElementById('plannerLink');
    function renderCell(tier, cell) {
      attack.textContent = number(cell?.base_attack);
      trace.textContent = `${number(tier?.tier_base_attack_at_1_star)} × ${number(cell?.preset_attack_ratio)} = ${number(cell?.unrounded_attack)} → ${number(cell?.base_attack)}`;
      plannerLink.href = plannerUrl(item, tier?.gear_tier, cell?.blueprint_stars);
    }
    function updateTier() {
      const tier = tiers.find((row) => String(row.gear_tier) === tierControl.value) || tiers.at(-1);
      const previousStars = starControl.value;
      starControl.innerHTML = tier.blueprint_star_values.map((row) => `<option value="${row.blueprint_stars}">${row.blueprint_stars}★</option>`).join('');
      if ([...starControl.options].some((option) => option.value === previousStars)) starControl.value = previousStars;
      else starControl.value = starControl.options[starControl.options.length - 1]?.value || '1';
      renderCell(tier, tier.blueprint_star_values.find((row) => String(row.blueprint_stars) === starControl.value));
    }
    tierControl?.addEventListener('change', updateTier);
    starControl?.addEventListener('change', () => {
      const tier = tiers.find((row) => String(row.gear_tier) === tierControl.value);
      renderCell(tier, tier?.blueprint_star_values.find((row) => String(row.blueprint_stars) === starControl.value));
    });
    if (tiers.length) updateTier();
  }

  document.body.dataset.catalogueView === 'detail' ? initDetail() : initBrowse();
})();
