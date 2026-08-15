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

  const minedStarAxisFor = (weapon, progression) => {
    const rarity = String(weapon?.rarity || '').trim().toLowerCase();
    const rarityCap = STAR_CAPS[rarity];
    if (!rarityCap) return null;
    const axis = progression?.blueprint_stars;
    if (!axis || axis.semantic_status !== 'validated-source-axis' || !Array.isArray(axis.stars) || !axis.stars.length) return null;
    const values = axis.stars.map((row) => row?.blueprint_stars);
    if (values.some((value) => !Number.isInteger(value) || value < 1)) return null;
    if (new Set(values).size !== values.length) return null;
    const maximum = Math.max(...values);
    const expected = Array.from({ length: maximum }, (_, index) => index + 1);
    if (!hasExactNumbers(values, expected) || maximum > rarityCap) return null;
    return expected;
  };

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

    const expectedStars = minedStarAxisFor(weapon, progression);
    if (!expectedStars) return false;

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

/* Build Lab weapon arsenal picker enhancement. Scoped to the planner route. */
(() => {
  'use strict';
  if (!/^\/build-planner\/?$/i.test(location.pathname)) return;

  const RARITY_RANK = { Common: 1, Uncommon: 2, Rare: 3, Epic: 4, Legendary: 5 };
  const FAVORITES_KEY = 'dead-signal-weapon-favorites';
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const finite = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
  const num = (value) => finite(value) ? Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—';
  const damage = (value, projectiles) => finite(value) && finite(projectiles) && Number(projectiles) > 1 ? `${num(value)}×${num(projectiles)}` : num(value);
  const imageUrl = (weapon) => {
    const path = String(weapon?.image_asset || '').replace(/\\/g, '/').trim();
    if (!path) return '';
    if (/^(https?:|data:|\/)/i.test(path)) return path.startsWith('/assets/') ? `/build-planner${path}` : path;
    return `/build-planner/${path.replace(/^\.\//, '')}`;
  };
  const allWeapons = () => Array.isArray(window.DS_WEAPON_MATH?.weapons) ? window.DS_WEAPON_MATH.weapons : [];
  const byName = () => new Map(allWeapons().map((weapon) => [String(weapon.name || '').trim(), weapon]));
  const tierOne = (weapon) => weapon?.tier_star_matrix?.[0]?.blueprint_star_values?.[0] || null;
  const ranged = (weapon) => weapon?.static_inputs?.ranged_stats || {};
  const effectText = (weapon) => {
    const effect = weapon?.static_inputs?.weapon_effect;
    return typeof effect === 'string' ? effect.trim() : String(effect?.description || effect?.text || '').trim();
  };
  const effectStatus = (weapon) => String(weapon?.public_contract?.effect_resolution?.status || weapon?.public_contract?.effect_evidence?.status || '').trim();
  const mechanicLabel = (weapon) => {
    if (effectText(weapon)) return 'Resolved mechanic';
    const status = effectStatus(weapon);
    if (status === 'no-fixed-skill-reference') return 'No fixed-skill reference';
    if (status === 'exact-fixed-skill-record-missing') return 'Exact skill record missing';
    return status ? status.replace(/-/g, ' ') : 'No resolved mechanic text';
  };
  const acquisition = (weapon) => {
    const contract = weapon?.public_contract || {};
    const tiers = contract.progression?.gear_tiers || [];
    const recipeCount = tiers.filter((tier) => tier?.recipe).length;
    const gain = String(contract.acquisition?.gain_path || weapon?.item_gain_path || '').trim();
    const hint = String(contract.acquisition?.hint || weapon?.acquisition_hint || '').trim();
    if (tiers.length && recipeCount === tiers.length) return { status: 'craftable', label: 'Recipes proven', detail: `${recipeCount}/${tiers.length} Gear Tier recipes`, source: hint || gain || 'Installed-game recipe evidence' };
    if (/stronghold exploration/i.test(gain)) return { status: 'direct', label: 'Direct acquisition', detail: gain, source: hint || gain };
    return { status: 'unresolved', label: 'Acquisition unresolved', detail: recipeCount ? `${recipeCount}/${tiers.length} recipes found` : 'No exact recipe or direct path proven', source: hint || gain || 'Exact source unresolved' };
  };
  const recordForButton = (button, nameMap) => {
    const name = String(button.querySelector('strong')?.textContent || '').trim();
    return nameMap.get(name) || null;
  };
  const favorites = () => {
    try { return new Set(JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]')); } catch (_) { return new Set(); }
  };
  const saveFavorites = (set) => { try { localStorage.setItem(FAVORITES_KEY, JSON.stringify([...set])); } catch (_) {} };

  let pendingButton = null;
  let pendingWeapon = null;
  let allowOriginal = false;
  let compare = new Set();
  let observer = null;

  function rarityClass(weapon) { return `ars-rarity-${String(weapon?.rarity || 'unknown').toLowerCase()}`; }
  function cardDetails(button, weapon) {
    if (!weapon || button.dataset.arsenalEnhanced === '1') return;
    button.dataset.arsenalEnhanced = '1';
    button.classList.add('arsenal-card', rarityClass(weapon));
    const cell = tierOne(weapon);
    const stats = ranged(weapon);
    const acquisitionInfo = acquisition(weapon);
    const image = imageUrl(weapon);
    const mechanic = effectText(weapon);
    const existingCopy = button.querySelector(':scope > span:last-child');
    const favs = favorites();
    button.innerHTML = `
      <span class="arsenal-check" aria-hidden="true"></span>
      <span class="arsenal-art">${image ? `<img src="${esc(image)}" alt="${esc(weapon.name)}" loading="lazy" decoding="async">` : `<b>${esc((weapon.category || 'WP').slice(0,3).toUpperCase())}</b><small>IMAGE PENDING</small>`}</span>
      <span class="arsenal-copy">
        <span class="arsenal-title"><strong>${esc(weapon.name)}</strong><span class="arsenal-favorite ${favs.has(weapon.canonical_id) ? 'active' : ''}" data-ars-favorite="${esc(weapon.canonical_id)}" title="Favorite">★</span></span>
        <span class="arsenal-chips"><i class="${rarityClass(weapon)}">${esc(weapon.rarity || 'Unverified')}</i><i>${esc(weapon.category || 'Type unresolved')}</i><i>Tier I · 1★</i></span>
        <span class="arsenal-mechanic">${esc(mechanic || mechanicLabel(weapon))}</span>
        <span class="arsenal-stats"><span><small>DMG</small><b>${damage(cell?.base_attack, stats.projectile_count)}</b></span><span><small>FIRE RATE</small><b>${num(stats.rpm)}</b></span><span><small>RANGE</small><b>${num(stats.range_meters)}</b></span></span>
        <span class="arsenal-evidence ${acquisitionInfo.status}"><b>${esc(acquisitionInfo.label)}</b><small>${esc(acquisitionInfo.detail)}</small></span>
        <span class="arsenal-actions"><span data-ars-preview>Preview</span><span data-ars-select>Select</span></span>
      </span>`;
    if (existingCopy) existingCopy.remove();
  }

  function inspector(weapon) {
    const host = document.getElementById('arsenalInspector');
    if (!host) return;
    if (!weapon) {
      host.innerHTML = '<div class="arsenal-inspector-empty"><b>Select a weapon</b><span>Highlight a record to inspect its exact player-facing evidence before confirming.</span></div>';
      return;
    }
    const cell = tierOne(weapon);
    const stats = ranged(weapon);
    const image = imageUrl(weapon);
    const acq = acquisition(weapon);
    const mechanic = effectText(weapon);
    host.innerHTML = `
      <div class="arsenal-inspector-head"><small>SELECTED WEAPON</small><h3>${esc(weapon.name)}</h3><div><span class="ars-chip ${rarityClass(weapon)}">${esc(weapon.rarity || 'Unverified')}</span><span class="ars-chip">${esc(weapon.category || 'Type unresolved')}</span></div></div>
      <div class="arsenal-inspector-art">${image ? `<img src="${esc(image)}" alt="${esc(weapon.name)}">` : '<span>IMAGE PENDING</span>'}</div>
      <dl class="arsenal-inspector-stats"><div><dt>Tier I · 1★ DMG</dt><dd>${damage(cell?.base_attack, stats.projectile_count)}</dd></div><div><dt>Fire Rate</dt><dd>${num(stats.rpm)}</dd></div><div><dt>Range</dt><dd>${num(stats.range_meters)}</dd></div><div><dt>Accuracy</dt><dd>${num(stats.accuracy)}</dd></div><div><dt>Stability</dt><dd>${num(stats.stability)}</dd></div><div><dt>Mobility</dt><dd>${num(stats.mobility)}</dd></div></dl>
      <section><small>EVIDENCE & ACQUISITION</small><p><b>${esc(acq.label)}</b><br>${esc(acq.source)}<br><span>${esc(acq.detail)}</span></p></section>
      <section><small>WEAPON MECHANIC</small><p>${esc(mechanic || mechanicLabel(weapon))}</p></section>
      <a class="arsenal-detail-link" href="/database/weapons/detail/?weapon=${encodeURIComponent(weapon.blueprint_id || '')}">View Full Details ↗</a>`;
  }

  function applyFilters() {
    const dialog = document.getElementById('picker');
    if (!dialog?.classList.contains('arsenal-mode')) return;
    const query = String(document.getElementById('pickerSearch')?.value || '').trim().toLowerCase();
    const type = document.getElementById('pickerFilter')?.value || '';
    const rarity = document.getElementById('arsRarity')?.value || '';
    const acqFilter = document.getElementById('arsAcquisition')?.value || '';
    const mechanicFilter = document.getElementById('arsMechanic')?.value || '';
    const favOnly = document.getElementById('arsFavorites')?.classList.contains('active');
    const craftOnly = document.getElementById('arsCraftable')?.classList.contains('active');
    const favs = favorites();
    const nameMap = byName();
    const cards = [...dialog.querySelectorAll('#pickerList > .bl-pick')];
    const visible = [];
    for (const card of cards) {
      const weapon = recordForButton(card, nameMap);
      if (!weapon) continue;
      cardDetails(card, weapon);
      const acq = acquisition(weapon);
      const mech = effectText(weapon) ? 'resolved' : effectStatus(weapon) || 'none';
      const haystack = `${weapon.name} ${weapon.category} ${weapon.rarity} ${effectText(weapon)} ${acq.label} ${acq.detail}`.toLowerCase();
      const show = (!query || haystack.includes(query))
        && (!type || weapon.category === type)
        && (!rarity || weapon.rarity === rarity)
        && (!acqFilter || acq.status === acqFilter)
        && (!mechanicFilter || mech === mechanicFilter)
        && (!favOnly || favs.has(weapon.canonical_id))
        && (!craftOnly || acq.status === 'craftable');
      card.hidden = !show;
      if (show) visible.push({ card, weapon });
    }
    const sort = document.getElementById('arsSort')?.value || 'name';
    visible.sort((a, b) => {
      if (sort === 'rarity') return (RARITY_RANK[b.weapon.rarity] || 0) - (RARITY_RANK[a.weapon.rarity] || 0) || a.weapon.name.localeCompare(b.weapon.name);
      if (sort === 'damage') return (Number(tierOne(b.weapon)?.base_attack) || 0) - (Number(tierOne(a.weapon)?.base_attack) || 0) || a.weapon.name.localeCompare(b.weapon.name);
      if (sort === 'rpm') return (Number(ranged(b.weapon).rpm) || 0) - (Number(ranged(a.weapon).rpm) || 0) || a.weapon.name.localeCompare(b.weapon.name);
      return a.weapon.name.localeCompare(b.weapon.name);
    });
    const list = document.getElementById('pickerList');
    visible.forEach(({ card }) => list.append(card));
    const count = document.getElementById('arsResultCount');
    if (count) count.textContent = `${visible.length} of ${cards.length} weapons`;
  }

  function ensureArsenal() {
    const dialog = document.getElementById('picker');
    if (!dialog || document.getElementById('pickerTitle')?.textContent !== 'Weapon') return;
    dialog.classList.add('arsenal-mode');
    const tools = dialog.querySelector('.bl-picker-tools');
    const list = document.getElementById('pickerList');
    if (!tools || !list) return;
    if (!document.getElementById('arsenalBody')) {
      const weaponTypes = [...new Set(allWeapons().map((weapon) => weapon.category).filter(Boolean))].sort();
      const rarities = [...new Set(allWeapons().map((weapon) => weapon.rarity).filter(Boolean))].sort((a, b) => (RARITY_RANK[b] || 0) - (RARITY_RANK[a] || 0));
      tools.insertAdjacentHTML('beforeend', `
        <select id="arsRarity" aria-label="Rarity"><option value="">All Rarities</option>${rarities.map((v) => `<option>${esc(v)}</option>`).join('')}</select>
        <select id="arsAcquisition" aria-label="Acquisition"><option value="">All Acquisition</option><option value="craftable">Recipes proven</option><option value="direct">Direct acquisition</option><option value="unresolved">Unresolved</option></select>
        <select id="arsMechanic" aria-label="Mechanic evidence"><option value="">All Mechanic Evidence</option><option value="resolved">Resolved mechanic</option><option value="no-fixed-skill-reference">No fixed-skill reference</option><option value="exact-fixed-skill-record-missing">Exact skill record missing</option></select>
        <select id="arsSort" aria-label="Sort"><option value="name">Sort: Name A–Z</option><option value="rarity">Sort: Rarity</option><option value="damage">Sort: Damage high–low</option><option value="rpm">Sort: Fire rate high–low</option></select>
        <button id="arsCraftable" type="button">Craftable</button><button id="arsFavorites" type="button">★ Favorites</button><button type="button" disabled title="Owned inventory is not connected to a player account contract">Owned — not connected</button>`);
      const body = document.createElement('div');
      body.id = 'arsenalBody';
      body.className = 'arsenal-body';
      const rail = document.createElement('aside');
      rail.className = 'arsenal-rail';
      rail.innerHTML = `<small>WEAPON TYPE</small><button class="active" data-ars-type="">All Weapons</button>${weaponTypes.map((v) => `<button data-ars-type="${esc(v)}">${esc(v)}</button>`).join('')}<small>RARITY</small>${rarities.map((v) => `<button data-ars-rarity="${esc(v)}">${esc(v)}</button>`).join('')}`;
      const center = document.createElement('div'); center.className = 'arsenal-center';
      list.parentNode.insertBefore(body, list); center.append(list); body.append(rail, center);
      const inspect = document.createElement('aside'); inspect.id = 'arsenalInspector'; inspect.className = 'arsenal-inspector'; body.append(inspect);
      const footer = document.createElement('div'); footer.className = 'arsenal-footer'; footer.innerHTML = '<span id="arsResultCount">Weapons</span><span class="arsenal-footer-spacer"></span><button id="arsCancel" type="button">Cancel</button><button id="arsConfirm" type="button" class="primary" disabled>Confirm Selection</button>'; dialog.append(footer);
      inspector(null);
      tools.querySelectorAll('select').forEach((control) => control.addEventListener('change', applyFilters));
      ['arsCraftable', 'arsFavorites'].forEach((id) => document.getElementById(id)?.addEventListener('click', (event) => { event.currentTarget.classList.toggle('active'); applyFilters(); }));
      rail.addEventListener('click', (event) => {
        const typeButton = event.target.closest('[data-ars-type]');
        const rarityButton = event.target.closest('[data-ars-rarity]');
        if (typeButton) { document.getElementById('pickerFilter').value = typeButton.dataset.arsType; rail.querySelectorAll('[data-ars-type]').forEach((b) => b.classList.toggle('active', b === typeButton)); }
        if (rarityButton) { document.getElementById('arsRarity').value = rarityButton.dataset.arsRarity; rail.querySelectorAll('[data-ars-rarity]').forEach((b) => b.classList.toggle('active', b === rarityButton)); }
        applyFilters();
      });
      document.getElementById('arsCancel').onclick = () => dialog.close();
      document.getElementById('arsConfirm').onclick = () => {
        if (!pendingButton) return;
        allowOriginal = true;
        pendingButton.click();
        allowOriginal = false;
      };
      document.getElementById('pickerSearch')?.addEventListener('input', () => requestAnimationFrame(applyFilters));
      document.getElementById('pickerFilter')?.addEventListener('change', () => requestAnimationFrame(applyFilters));
    }
    requestAnimationFrame(() => { applyFilters(); if (!pendingWeapon) { const first = dialog.querySelector('#pickerList > .bl-pick:not([hidden])'); if (first) choosePending(first); } });
  }

  function choosePending(button) {
    const weapon = recordForButton(button, byName());
    if (!weapon) return;
    pendingButton = button;
    pendingWeapon = weapon;
    document.querySelectorAll('#pickerList > .bl-pick').forEach((card) => card.classList.toggle('arsenal-selected', card === button));
    const confirm = document.getElementById('arsConfirm'); if (confirm) confirm.disabled = false;
    inspector(weapon);
  }

  function bind() {
    const picker = document.getElementById('picker');
    if (!picker) return;
    picker.addEventListener('click', (event) => {
      if (!picker.classList.contains('arsenal-mode') || allowOriginal) return;
      const favorite = event.target.closest('[data-ars-favorite]');
      if (favorite) {
        event.preventDefault(); event.stopPropagation();
        const set = favorites(); const id = favorite.dataset.arsFavorite;
        set.has(id) ? set.delete(id) : set.add(id); saveFavorites(set); favorite.classList.toggle('active', set.has(id)); applyFilters(); return;
      }
      const card = event.target.closest('#pickerList > .bl-pick');
      if (card) { event.preventDefault(); event.stopImmediatePropagation(); choosePending(card); }
    }, true);
    observer = new MutationObserver(() => requestAnimationFrame(ensureArsenal));
    observer.observe(picker, { childList: true, subtree: true, characterData: true });
    picker.addEventListener('close', () => { picker.classList.remove('arsenal-mode'); pendingButton = null; pendingWeapon = null; compare.clear(); const confirm = document.getElementById('arsConfirm'); if (confirm) confirm.disabled = true; });
    ensureArsenal();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, { once: true }); else bind();
})();
