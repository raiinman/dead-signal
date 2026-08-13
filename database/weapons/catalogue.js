(() => {
  'use strict';

  const mathData = window.DS_WEAPON_MATH || {};
  const normalizeName = (value) => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const defaultTier = (math) => math?.tier_star_matrix?.at(-1) || null;
  const defaultCell = (math) => defaultTier(math)?.blueprint_star_values?.[0] || null;
  const rarityRank = { Common: 1, Rare: 2, Epic: 3, Legendary: 4 };
  const romanTier = (tier) => ['I', 'II', 'III', 'IV', 'V'][Number(tier) - 1] || String(tier || '—');

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const finite = (value) => Number.isFinite(Number(value));
  const number = (value, fallback = '—') => finite(value) ? Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 }) : fallback;
  const percentage = (value, fallback = '—') => {
    if (!finite(value)) return fallback;
    const numeric = Number(value);
    const scaled = Math.abs(numeric) <= 1 ? numeric * 100 : numeric;
    return `${scaled.toLocaleString(undefined, { maximumFractionDigits: 2 })}%`;
  };
  const rarityClass = (item) => `rarity-${String(item.rarity || 'unknown').toLowerCase()}`;

  const attributeRow = (cell, patterns) => {
    const rows = cell?.base_attributes || [];
    return rows.find((row) => {
      const haystack = `${row?.label || ''} ${row?.key || ''} ${row?.code || ''}`.toLowerCase();
      return patterns.some((pattern) => haystack.includes(pattern));
    }) || null;
  };
  const attributeDisplay = (cell, patterns) => {
    const row = attributeRow(cell, patterns);
    if (!row) return '—';
    if (row.display_value !== '' && row.display_value !== null && row.display_value !== undefined) return String(row.display_value);
    return finite(row.value) ? percentage(row.value) : String(row.value ?? '—');
  };

  const weapons = (mathData.weapons || []).map((math) => {
    const ranged = math.static_inputs?.ranged_stats || {};
    const melee = math.static_inputs?.melee_stats || {};
    const cell = defaultCell(math);
    return {
      id: math.canonical_id,
      plannerId: math.canonical_id,
      itemId: String(math.item_id),
      blueprintId: String(math.blueprint_id),
      name: math.name,
      type: math.category,
      rarity: math.rarity,
      feature: math.static_inputs?.weapon_effect?.description || '',
      mechanicName: math.static_inputs?.weapon_effect?.name || '',
      acquisition: math.acquisition_hint || math.item_gain_path || '',
      imageAsset: math.image_asset || '',
      damageProfile: {
        fullDamageDistance: ranged.full_damage_distance,
        minimumDamageDistance: ranged.minimum_damage_distance,
        minimumDamageMultiplier: ranged.minimum_damage_multiplier,
      },
      ammoItemId: ranged.ammo_item_id,
      stats: {
        damage: cell?.base_attack,
        rpm: ranged.rpm,
        magazine: ranged.magazine,
        reload: ranged.reload_seconds,
        range: ranged.range_meters,
        accuracy: ranged.accuracy,
        stability: ranged.stability,
        mobility: ranged.mobility,
        meleeAttackSpeed: melee.attack_speed,
        meleeAttackRange: melee.attack_range,
      },
      coverage: 'Installed-game Miner weapon projection',
      sources: [{ site: 'Installed game snapshot' }],
      math,
    };
  });

  const effect = (item) => String(item.feature || '').trim();
  const imageUrl = (item) => {
    const path = String(item.imageAsset || item.imageRef || '').replace(/\\/g, '/');
    if (!path) return '';
    if (/^(https?:|data:|\/)/.test(path)) return path.startsWith('/assets/') ? `/build-planner${path}` : path;
    return `/build-planner/${path.replace(/^\.\//, '')}`;
  };
  const detailUrl = (item) => `detail/?weapon=${encodeURIComponent(item.blueprintId)}`;
  const plannerUrl = (item, tier, stars) => {
    const params = new URLSearchParams({
      'catalogue-weapon': item.plannerId || item.itemId,
      'catalogue-name': item.name,
      'catalogue-slot': item.type === 'Melee' ? 'melee' : 'primary',
    });
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
      <p class="effect-preview">${esc(effect(item) || 'Weapon mechanic unresolved or absent in the current Miner projection.')}</p>
      <p class="source-line">Source: ${esc(source)}</p>
      <div class="card-actions"><a href="${detailUrl(item)}">Inspect</a><button type="button" data-compare-id="${esc(item.id)}">Compare</button><a class="configure" href="${plannerUrl(item)}">Add to Build</a></div></div>
    </article>`;
  }

  function initBrowse() {
    const grid = document.getElementById('weaponGrid');
    const error = document.getElementById('catalogueError');
    if (!weapons.length) {
      error.hidden = false;
      grid.hidden = true;
      document.getElementById('resultStatus').textContent = 'No verified records loaded.';
      return;
    }
    document.getElementById('weaponTotal').textContent = weapons.length;
    const search = document.getElementById('weaponSearch');
    const type = document.getElementById('typeFilter');
    const rarity = document.getElementById('rarityFilter');
    const sort = document.getElementById('weaponSort');
    const status = document.getElementById('resultStatus');
    const selected = new Set();

    [...new Set(weapons.map((item) => item.type).filter(Boolean))].sort().forEach((value) => type.add(new Option(value, value)));
    [...new Set(weapons.map((item) => item.rarity).filter(Boolean))]
      .sort((a, b) => (rarityRank[b] || 0) - (rarityRank[a] || 0))
      .forEach((value) => rarity.add(new Option(value, value)));

    function render() {
      const query = search.value.trim().toLowerCase();
      let items = weapons.filter((item) => (
        !query || `${item.name} ${item.type} ${item.rarity} ${effect(item)}`.toLowerCase().includes(query)
      ) && (!type.value || item.type === type.value) && (!rarity.value || item.rarity === rarity.value));
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
    document.getElementById('clearFilters').addEventListener('click', () => {
      search.value = '';
      type.value = '';
      rarity.value = '';
      sort.value = 'name';
      render();
      search.focus();
    });
    document.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => {
      document.querySelectorAll('[data-view]').forEach((item) => {
        item.classList.toggle('active', item === button);
        item.setAttribute('aria-pressed', String(item === button));
      });
      grid.classList.toggle('list-view', button.dataset.view === 'list');
    }));
    grid.addEventListener('click', (event) => {
      const button = event.target.closest('[data-compare-id]');
      if (!button) return;
      selected.has(button.dataset.compareId) ? selected.delete(button.dataset.compareId) : selected.size < 2 && selected.add(button.dataset.compareId);
      grid.querySelectorAll('[data-compare-id]').forEach((item) => {
        const active = selected.has(item.dataset.compareId);
        item.classList.toggle('selected', active);
        item.textContent = active ? 'Selected' : 'Compare';
      });
      if (selected.size === 2) showCompare([...selected]);
      renderStatus();
    });
    function renderStatus() {
      const visible = grid.querySelectorAll('.weapon-card').length;
      status.textContent = `${visible} of ${weapons.length} weapons shown${selected.size ? ` · ${selected.size}/2 selected to compare` : ''}.`;
    }
    render();
  }

  function configuration(item, tierValue, starValue) {
    const tiers = item.math?.tier_star_matrix || [];
    const tier = tiers.find((row) => String(row.gear_tier) === String(tierValue)) || tiers.at(-1) || null;
    const cells = tier?.blueprint_star_values || [];
    const cell = cells.find((row) => String(row.blueprint_stars) === String(starValue)) || cells[0] || null;
    return { tier, cell, tiers };
  }

  function compareValue(row, item, config) {
    switch (row.key) {
      case 'damage': return config.cell?.base_attack;
      case 'critRate': return attributeDisplay(config.cell, ['crit rate', 'critical rate']);
      case 'critDamage': return attributeDisplay(config.cell, ['crit dmg', 'crit damage', 'critical dmg', 'critical damage']);
      case 'weakspot': return attributeDisplay(config.cell, ['weakspot dmg', 'weakspot damage', 'weak spot dmg', 'weak spot damage', 'weakspot', 'weak spot']);
      case 'fullDamageDistance': return item.damageProfile?.fullDamageDistance;
      case 'minimumDamageDistance': return item.damageProfile?.minimumDamageDistance;
      case 'minimumDamageMultiplier': return finite(item.damageProfile?.minimumDamageMultiplier) ? percentage(item.damageProfile.minimumDamageMultiplier) : '—';
      default: return item.stats?.[row.key];
    }
  }

  function displayCompareValue(row, value) {
    if (value === '—' || value === '' || value === null || value === undefined) return '—';
    if (row.format === 'seconds') return finite(value) ? `${number(value)} s` : String(value);
    if (row.format === 'meters') return finite(value) ? `${number(value)} m` : String(value);
    return finite(value) ? number(value) : String(value);
  }

  function deltaText(left, right) {
    if (!finite(left) || !finite(right)) return '';
    const delta = Number(left) - Number(right);
    if (!delta) return 'Δ 0';
    return `Δ ${delta > 0 ? '+' : ''}${number(delta)}`;
  }

  function showCompare(ids) {
    const items = ids.map((id) => weapons.find((item) => item.id === id)).filter(Boolean);
    if (items.length !== 2) return;
    let dialog = document.getElementById('catalogueCompare');
    if (!dialog) {
      dialog = document.createElement('dialog');
      dialog.id = 'catalogueCompare';
      dialog.className = 'compare-dialog';
      document.body.append(dialog);
    }

    const initial = items.map((item) => {
      const tier = item.math?.tier_star_matrix?.at(-1);
      return { tier: String(tier?.gear_tier || ''), stars: String(tier?.blueprint_star_values?.[0]?.blueprint_stars || '') };
    });
    const rows = [
      { key: 'damage', label: 'Base Attack' },
      { key: 'rpm', label: 'Fire Rate' },
      { key: 'magazine', label: 'Magazine' },
      { key: 'reload', label: 'Reload', format: 'seconds' },
      { key: 'critRate', label: 'Crit Rate' },
      { key: 'critDamage', label: 'Crit DMG' },
      { key: 'weakspot', label: 'Weakspot DMG' },
      { key: 'accuracy', label: 'Accuracy' },
      { key: 'stability', label: 'Stability' },
      { key: 'range', label: 'Range', format: 'meters' },
      { key: 'mobility', label: 'Mobility' },
      { key: 'fullDamageDistance', label: 'Full-Damage Distance', format: 'meters' },
      { key: 'minimumDamageDistance', label: 'Minimum-Damage Distance', format: 'meters' },
      { key: 'minimumDamageMultiplier', label: 'Minimum-Damage Multiplier' },
    ];

    dialog.innerHTML = `<div class="compare-head"><div><p class="eyebrow"><span></span> Verified configured comparison</p><h2>${esc(items[0].name)} <em>vs</em> ${esc(items[1].name)}</h2></div><button type="button" aria-label="Close comparison">×</button></div>
      <p class="compare-note">Gear Tier and Blueprint Stars are applied to proven Base Attack and star attributes. Calibration, attachments, conditional effects, enemy defenses, and derived DPS are not applied.</p>
      <div class="math-config">${items.map((item, index) => {
        const tiers = item.math?.tier_star_matrix || [];
        const selectedTier = tiers.find((row) => String(row.gear_tier) === initial[index].tier) || tiers.at(-1);
        return `<label><span>${esc(item.name)} · Gear Tier</span><select data-compare-tier="${index}">${tiers.map((tier) => `<option value="${tier.gear_tier}"${String(tier.gear_tier) === initial[index].tier ? ' selected' : ''}>Tier ${romanTier(tier.gear_tier)}</option>`).join('')}</select></label><label><span>${esc(item.name)} · Blueprint Stars</span><select data-compare-stars="${index}">${(selectedTier?.blueprint_star_values || []).map((cell) => `<option value="${cell.blueprint_stars}"${String(cell.blueprint_stars) === initial[index].stars ? ' selected' : ''}>${cell.blueprint_stars}★</option>`).join('')}</select></label>`;
      }).join('')}</div>
      <div id="compareTable" class="compare-table"></div>`;

    const close = dialog.querySelector('.compare-head button');
    close.addEventListener('click', () => dialog.close());

    function syncStars(index) {
      const tierControl = dialog.querySelector(`[data-compare-tier="${index}"]`);
      const starControl = dialog.querySelector(`[data-compare-stars="${index}"]`);
      const item = items[index];
      const previousStars = starControl.value;
      const config = configuration(item, tierControl.value, previousStars);
      const cells = config.tier?.blueprint_star_values || [];
      starControl.innerHTML = cells.map((cell) => `<option value="${cell.blueprint_stars}">${cell.blueprint_stars}★</option>`).join('');
      if ([...starControl.options].some((option) => option.value === previousStars)) starControl.value = previousStars;
      else starControl.value = starControl.options[0]?.value || '';
    }

    function renderCompareTable() {
      const configs = items.map((item, index) => configuration(
        item,
        dialog.querySelector(`[data-compare-tier="${index}"]`)?.value,
        dialog.querySelector(`[data-compare-stars="${index}"]`)?.value,
      ));
      const visibleRows = rows.map((row) => {
        const left = compareValue(row, items[0], configs[0]);
        const right = compareValue(row, items[1], configs[1]);
        return { row, left, right };
      }).filter(({ left, right }) => left !== '—' || right !== '—');
      dialog.querySelector('#compareTable').innerHTML = `<div class="compare-row headings"><b>${esc(items[0].name)}</b><span>STAT</span><b>${esc(items[1].name)}</b></div>${visibleRows.map(({ row, left, right }) => {
        const delta = deltaText(left, right);
        return `<div class="compare-row"><b>${esc(displayCompareValue(row, left))}</b><span>${esc(row.label)}${delta ? `<small style="display:block;margin-top:.2rem">${esc(delta)}</small>` : ''}</span><b>${esc(displayCompareValue(row, right))}</b></div>`;
      }).join('')}`;
    }

    items.forEach((item, index) => {
      dialog.querySelector(`[data-compare-tier="${index}"]`)?.addEventListener('change', () => {
        syncStars(index);
        renderCompareTable();
      });
      dialog.querySelector(`[data-compare-stars="${index}"]`)?.addEventListener('change', renderCompareTable);
    });
    renderCompareTable();
    dialog.showModal();
  }

  function statBlock(rows) {
    return rows.filter(([, , value]) => value !== null && value !== undefined && value !== '').map(([label, format, value]) => {
      let display = number(value);
      if (!finite(value)) display = String(value || '—');
      if (format === 'seconds' && finite(value)) display = `${number(value)} s`;
      if (format === 'meters' && finite(value)) display = `${number(value)} m`;
      if (format === 'percent' && finite(value)) display = percentage(value);
      return `<div><dt>${esc(label)}</dt><dd>${esc(display)}</dd></div>`;
    }).join('');
  }

  function initDetail() {
    const shell = document.getElementById('weaponDetail');
    const id = document.body.dataset.detailId || new URLSearchParams(location.search).get('weapon');
    const item = weapons.find((weapon) => weapon.blueprintId === id || weapon.id === id || normalizeName(weapon.name) === normalizeName(id));
    if (!item) {
      shell.innerHTML = '<div class="catalogue-error"><strong>WEAPON RECORD UNAVAILABLE</strong><p>No verified record matched this route.</p><a href="../">Return to all weapons</a></div>';
      return;
    }
    const stats = item.stats || {};
    const tiers = item.math?.tier_star_matrix || [];
    const image = imageUrl(item);
    const ranged = item.type !== 'Melee';
    const generated = mathData.generated_utc ? new Date(mathData.generated_utc) : null;
    const generatedLabel = generated && !Number.isNaN(generated.getTime()) ? generated.toLocaleString() : 'Snapshot timestamp unavailable';
    const damageProfileRows = ranged ? statBlock([
      ['Full-Damage Distance', 'meters', item.damageProfile?.fullDamageDistance],
      ['Minimum-Damage Distance', 'meters', item.damageProfile?.minimumDamageDistance],
      ['Minimum-Damage Multiplier', 'percent', item.damageProfile?.minimumDamageMultiplier],
      ['Ammo Item ID', 'number', item.ammoItemId],
    ]) : statBlock([
      ['Attack Speed', 'text', stats.meleeAttackSpeed],
      ['Attack Range', 'text', stats.meleeAttackRange],
    ]);

    shell.innerHTML = `<nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../../../">Database</a><span>/</span><a href="../">Weapons</a><span>/</span><b>${esc(item.name)}</b></nav>
      <section class="detail-hero ${rarityClass(item)}"><div class="detail-art">${image ? `<img src="${esc(image)}" alt="${esc(item.name)}">` : '<span>IMAGE PENDING</span>'}</div><div><p class="eyebrow"><span></span> ${esc(item.type)} // ${esc(item.rarity)}</p><h1>${esc(item.name)}</h1><p>${esc(item.acquisition || 'Acquisition information is not resolved in the current website projection.')}</p><div class="detail-actions"><a class="configure" id="plannerLink" href="${plannerUrl(item)}">Configure in Build Planner</a><a href="../">Compare with another weapon</a></div></div></section>
      <section class="detail-grid"><article><p class="section-code">01 // Combat</p><h2>Core combat stats</h2><dl class="detail-stats">${statBlock([
        ['Tier V · 1★ Base Attack', 'number', stats.damage],
        ['Fire Rate', 'number', stats.rpm],
        ['Magazine', 'number', stats.magazine],
        ['Reload', 'seconds', stats.reload],
      ]) || '<div><dt>Combat data</dt><dd>—</dd></div>'}</dl></article>
      <article><p class="section-code">02 // Handling</p><h2>Weapon handling</h2><dl class="detail-stats">${statBlock([
        ['Accuracy', 'number', stats.accuracy],
        ['Stability', 'number', stats.stability],
        ['Range', 'meters', stats.range],
        ['Mobility', 'number', stats.mobility],
      ]) || '<div><dt>Handling data</dt><dd>—</dd></div>'}</dl></article>
      <article><p class="section-code">03 // Damage profile</p><h2>${ranged ? 'Distance behavior' : 'Melee profile'}</h2><dl class="detail-stats">${damageProfileRows || '<div><dt>Profile data</dt><dd>—</dd></div>'}</dl></article>
      <article><p class="section-code">04 // Weapon mechanic</p><h2>${esc(item.mechanicName || 'Indexed effect')}</h2><p class="full-effect">${esc(effect(item) || 'No player-facing weapon mechanic is resolved for this record in the current Miner projection. Dead Signal does not substitute flavor text or guessed mechanics.')}</p></article></section>
      <section class="progression-panel"><p class="section-code">05 // Proven static math</p><h2>Gear Tier and Blueprint Stars</h2><p>Choose a legal configuration. Base Attack is calculated from installed-game Tier and Blueprint Star data; it is not configured DPS.</p>${tiers.length ? `<div class="math-config"><label><span>Gear Tier</span><select id="gearTier">${tiers.map((tier) => `<option value="${tier.gear_tier}"${tier === tiers.at(-1) ? ' selected' : ''}>Tier ${romanTier(tier.gear_tier)}</option>`).join('')}</select></label><label><span>Blueprint Stars</span><select id="blueprintStars"></select></label><div class="math-result"><span>Verified Base Attack</span><strong id="calculatedAttack">—</strong><small id="calculationTrace"></small></div></div><div class="tier-grid">${tiers.map((tier) => `<div><span>Tier ${romanTier(tier.gear_tier)}</span><strong>${number(tier.tier_base_attack_at_1_star)}</strong><small>Base Attack at 1★</small></div>`).join('')}</div>` : '<p class="pending">Tier progression is not available for this record.</p>'}</section>
      <section class="provenance-panel"><p class="section-code">06 // Verification</p><h2>Source and limits</h2><div><p><b>Coverage</b><span>${esc(item.coverage)}</span></p><p><b>Source</b><span>Installed game snapshot</span></p><p><b>Blueprint ID</b><span>${esc(item.blueprintId)}</span></p></div><p class="limits">Snapshot generated: ${esc(generatedLabel)}. Formula: <code>${esc(mathData.formula_contract?.base_attack || 'Not recorded')}</code>. Calibration, attachments, conditional effects, enemy defenses, and configured DPS are not applied. Known-bad flavor descriptions are intentionally excluded.</p></section>`;

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
      starControl.innerHTML = (tier?.blueprint_star_values || []).map((row) => `<option value="${row.blueprint_stars}">${row.blueprint_stars}★</option>`).join('');
      if ([...starControl.options].some((option) => option.value === previousStars)) starControl.value = previousStars;
      else starControl.value = starControl.options[0]?.value || '1';
      renderCell(tier, tier?.blueprint_star_values?.find((row) => String(row.blueprint_stars) === starControl.value));
    }
    tierControl?.addEventListener('change', updateTier);
    starControl?.addEventListener('change', () => {
      const tier = tiers.find((row) => String(row.gear_tier) === tierControl.value);
      renderCell(tier, tier?.blueprint_star_values?.find((row) => String(row.blueprint_stars) === starControl.value));
    });
    if (tiers.length) updateTier();
  }

  document.body.dataset.catalogueView === 'detail' ? initDetail() : initBrowse();
})();
