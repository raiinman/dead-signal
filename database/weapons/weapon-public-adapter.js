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
  const isFiniteNumber = (value) => typeof value === 'number' && Number.isFinite(value);
  const hasExactNumbers = (values, expected) => values.length === expected.length
    && new Set(values).size === expected.length
    && expected.every((value) => values.includes(value));

  const minedStarAxisFor = (weapon, progression) => {
    const rarityCap = STAR_CAPS[String(weapon?.rarity || '').trim().toLowerCase()];
    const axis = progression?.blueprint_stars;
    if (!rarityCap || !axis || axis.semantic_status !== 'validated-source-axis' || !Array.isArray(axis.stars) || !axis.stars.length) return null;
    const values = axis.stars.map((row) => row?.blueprint_stars);
    if (values.some((value) => !Number.isInteger(value) || value < 1) || new Set(values).size !== values.length) return null;
    const maximum = Math.max(...values);
    const expected = Array.from({ length: maximum }, (_, index) => index + 1);
    return hasExactNumbers(values, expected) && maximum <= rarityCap ? expected : null;
  };

  const validProgressionFor = (weapon) => {
    const progression = weapon?.progression;
    if (!progression || progression.formula_status !== 'proven-static-base-attack' || (progression.validation_issues || []).length) return false;
    const gearTiers = progression.gear_tiers;
    const matrix = progression.tier_star_matrix;
    if (!Array.isArray(gearTiers) || gearTiers.length !== 5 || !hasExactNumbers(gearTiers.map((row) => row?.tier), LEGAL_TIERS)) return false;
    if (!Array.isArray(matrix) || matrix.length !== 5 || !hasExactNumbers(matrix.map((row) => row?.gear_tier), LEGAL_TIERS)) return false;
    const expectedStars = minedStarAxisFor(weapon, progression);
    if (!expectedStars) return false;
    return matrix.every((row) => {
      if (!isFiniteNumber(row?.tier_base_attack_at_1_star)) return false;
      const stars = row?.blueprint_star_values;
      if (!Array.isArray(stars) || stars.length !== expectedStars.length || !hasExactNumbers(stars.map((star) => star?.blueprint_stars), expectedStars)) return false;
      return stars.every((star) => isFiniteNumber(star?.preset_attack_ratio)
        && Number.isInteger(star?.base_attack)
        && star.base_attack === Math.trunc(row.tier_base_attack_at_1_star * star.preset_attack_ratio));
    });
  };

  const canonicalIds = published.weapons.map((weapon) => String(weapon?.canonical_id || '').trim());
  if (!(canonicalIds.length === new Set(canonicalIds).size && canonicalIds.every(Boolean) && published.weapons.every(validProgressionFor))) return;

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

/* Detailed Build Lab weapon selector. Only active on the planner route. */
(() => {
  'use strict';
  if (typeof location === 'undefined' || !/^\/build-planner\/?$/i.test(location.pathname)) return;

  const RARITY_RANK = { Common: 1, Uncommon: 2, Rare: 3, Epic: 4, Legendary: 5 };
  const FAVORITES_KEY = 'dead-signal-weapon-favorites';
  const PAGE_SIZE = 10;
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const finite = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
  const num = (value) => finite(value) ? Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—';
  const formatDamage = (value, projectiles) => finite(value) && finite(projectiles) && Number(projectiles) > 1 ? `${num(value)}×${num(projectiles)}` : num(value);
  const allWeapons = () => Array.isArray(window.DS_WEAPON_MATH?.weapons) ? window.DS_WEAPON_MATH.weapons : [];
  const weaponMap = () => new Map(allWeapons().map((weapon) => [String(weapon.name || '').trim(), weapon]));
  const tierOne = (weapon) => weapon?.tier_star_matrix?.[0]?.blueprint_star_values?.[0] || null;
  const ranged = (weapon) => weapon?.static_inputs?.ranged_stats || {};
  const imageUrl = (weapon) => {
    const path = String(weapon?.image_asset || '').replace(/\\/g, '/').trim();
    if (!path) return '';
    if (/^(https?:|data:|\/)/i.test(path)) return path.startsWith('/assets/') ? `/build-planner${path}` : path;
    return `/build-planner/${path.replace(/^\.\//, '')}`;
  };
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
    if (tiers.length && recipeCount === tiers.length) return { status: 'craftable', label: 'Recipes proven', detail: `${recipeCount}/${tiers.length} Gear Tier recipes` };
    if (/stronghold exploration/i.test(gain)) return { status: 'direct', label: 'Direct acquisition', detail: gain };
    return { status: 'unresolved', label: 'Acquisition unresolved', detail: recipeCount ? `${recipeCount}/${tiers.length} recipes found` : 'No exact recipe or direct path proven' };
  };
  const favorites = () => { try { return new Set(JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]')); } catch (_) { return new Set(); } };
  const storeFavorites = (set) => { try { localStorage.setItem(FAVORITES_KEY, JSON.stringify([...set])); } catch (_) {} };
  const recordForCard = (card) => weaponMap().get(String(card.querySelector('strong')?.textContent || '').trim()) || null;
  const rarityClass = (weapon) => `ars-rarity-${String(weapon?.rarity || 'unknown').toLowerCase()}`;

  let pendingButton = null;
  let pendingWeapon = null;
  let allowBaseSelection = false;
  let currentPage = 1;

  function enforceTwoColumnLayout() {
    const body = document.getElementById('arsenalBody');
    if (body) body.style.gridTemplateColumns = 'minmax(0,1fr)';
    document.querySelectorAll('#arsenalInspector,.arsenal-inspector,.arsenal-rail').forEach((node) => node.remove());
  }

  function enrichCard(card, weapon) {
    if (!weapon || card.dataset.arsenalEnhanced === '1') return;
    card.dataset.arsenalEnhanced = '1';
    card.classList.add('arsenal-card', rarityClass(weapon));
    const stats = ranged(weapon);
    const cell = tierOne(weapon);
    const acq = acquisition(weapon);
    const image = imageUrl(weapon);
    const mechanic = effectText(weapon);
    const fav = favorites().has(weapon.canonical_id);
    card.innerHTML = `
      <span class="arsenal-check" aria-hidden="true"></span>
      <span class="arsenal-art">${image ? `<img src="${esc(image)}" alt="${esc(weapon.name)}" loading="lazy" decoding="async">` : `<b>${esc((weapon.category || 'WP').slice(0, 3).toUpperCase())}</b><small>IMAGE PENDING</small>`}</span>
      <span class="arsenal-copy">
        <span class="arsenal-title"><strong>${esc(weapon.name)}</strong><span class="arsenal-favorite ${fav ? 'active' : ''}" data-ars-favorite="${esc(weapon.canonical_id)}" title="Favorite">★</span></span>
        <span class="arsenal-chips"><i class="${rarityClass(weapon)}">${esc(weapon.rarity || 'Unverified')}</i><i>${esc(weapon.category || 'Type unresolved')}</i><i>Tier I · 1★</i></span>
        <span class="arsenal-mechanic">${esc(mechanic || mechanicLabel(weapon))}</span>
        <span class="arsenal-stats"><span><small>DMG</small><b>${formatDamage(cell?.base_attack, stats.projectile_count)}</b></span><span><small>FIRE RATE</small><b>${num(stats.rpm)}</b></span><span><small>RANGE</small><b>${num(stats.range_meters)}</b></span></span>
        <span class="arsenal-evidence ${acq.status}"><b>${esc(acq.label)}</b><small>${esc(acq.detail)}</small></span>
        <span class="arsenal-actions"><span>Preview</span><span>Select</span></span>
      </span>`;
  }

  function choosePending(card) {
    const weapon = recordForCard(card);
    if (!weapon) return;
    pendingButton = card;
    pendingWeapon = weapon;
    document.querySelectorAll('#pickerList > .bl-pick').forEach((item) => item.classList.toggle('arsenal-selected', item === card));
    const confirm = document.getElementById('arsConfirm');
    if (confirm) confirm.disabled = false;
  }

  function renderPagination(totalItems, totalPages) {
    const host = document.getElementById('arsPagination');
    if (!host) return;
    host.innerHTML = '';

    const addButton = (label, page, disabled = false, active = false) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = label;
      button.disabled = disabled;
      button.className = active ? 'active' : '';
      button.addEventListener('click', () => {
        if (disabled || page === currentPage) return;
        currentPage = page;
        applyFilters(false);
        document.getElementById('pickerList')?.scrollTo({ top: 0, behavior: 'auto' });
      });
      host.append(button);
    };

    addButton('‹', Math.max(1, currentPage - 1), currentPage <= 1);

    const pages = [];
    if (totalPages <= 7) {
      for (let page = 1; page <= totalPages; page += 1) pages.push(page);
    } else {
      pages.push(1);
      const start = Math.max(2, currentPage - 1);
      const end = Math.min(totalPages - 1, currentPage + 1);
      if (start > 2) pages.push('…');
      for (let page = start; page <= end; page += 1) pages.push(page);
      if (end < totalPages - 1) pages.push('…');
      pages.push(totalPages);
    }

    pages.forEach((page) => {
      if (page === '…') {
        const ellipsis = document.createElement('span');
        ellipsis.className = 'ars-page-ellipsis';
        ellipsis.textContent = '…';
        host.append(ellipsis);
      } else {
        addButton(String(page), page, false, page === currentPage);
      }
    });

    addButton('›', Math.min(totalPages, currentPage + 1), currentPage >= totalPages);

    const label = document.getElementById('arsPageLabel');
    if (label) label.textContent = totalItems ? `Page ${currentPage} of ${totalPages}` : 'No results';
  }

  function applyFilters(resetPage = false) {
    const picker = document.getElementById('picker');
    if (!picker?.classList.contains('arsenal-mode')) return;
    enforceTwoColumnLayout();
    if (resetPage) currentPage = 1;

    const query = String(document.getElementById('pickerSearch')?.value || '').trim().toLowerCase();
    const type = document.getElementById('pickerFilter')?.value || '';
    const rarity = document.getElementById('arsRarity')?.value || '';
    const acquisitionFilter = document.getElementById('arsAcquisition')?.value || '';
    const mechanicFilter = document.getElementById('arsMechanic')?.value || '';
    const favoriteOnly = document.getElementById('arsFavorites')?.classList.contains('active');
    const craftableOnly = document.getElementById('arsCraftable')?.classList.contains('active');
    const favs = favorites();
    const cards = [...picker.querySelectorAll('#pickerList > .bl-pick')];
    const matches = [];

    for (const card of cards) {
      const weapon = recordForCard(card);
      card.hidden = true;
      if (!weapon) continue;
      const acq = acquisition(weapon);
      const mechanic = effectText(weapon) ? 'resolved' : effectStatus(weapon) || 'none';
      const haystack = `${weapon.name} ${weapon.category} ${weapon.rarity} ${effectText(weapon)} ${acq.label} ${acq.detail}`.toLowerCase();
      const show = (!query || haystack.includes(query))
        && (!type || weapon.category === type)
        && (!rarity || weapon.rarity === rarity)
        && (!acquisitionFilter || acq.status === acquisitionFilter)
        && (!mechanicFilter || mechanic === mechanicFilter)
        && (!favoriteOnly || favs.has(weapon.canonical_id))
        && (!craftableOnly || acq.status === 'craftable');
      if (show) matches.push({ card, weapon });
    }

    const sort = document.getElementById('arsSort')?.value || 'name';
    matches.sort((a, b) => {
      if (sort === 'rarity') return (RARITY_RANK[b.weapon.rarity] || 0) - (RARITY_RANK[a.weapon.rarity] || 0) || a.weapon.name.localeCompare(b.weapon.name);
      if (sort === 'damage') return (Number(tierOne(b.weapon)?.base_attack) || 0) - (Number(tierOne(a.weapon)?.base_attack) || 0) || a.weapon.name.localeCompare(b.weapon.name);
      if (sort === 'rpm') return (Number(ranged(b.weapon).rpm) || 0) - (Number(ranged(a.weapon).rpm) || 0) || a.weapon.name.localeCompare(b.weapon.name);
      return a.weapon.name.localeCompare(b.weapon.name);
    });

    const totalPages = Math.max(1, Math.ceil(matches.length / PAGE_SIZE));
    currentPage = Math.min(Math.max(1, currentPage), totalPages);
    const start = (currentPage - 1) * PAGE_SIZE;
    const pageItems = matches.slice(start, start + PAGE_SIZE);
    const list = document.getElementById('pickerList');

    pageItems.forEach(({ card, weapon }) => {
      enrichCard(card, weapon);
      card.hidden = false;
      list.append(card);
    });

    const count = document.getElementById('arsResultCount');
    if (count) {
      const first = matches.length ? start + 1 : 0;
      const last = Math.min(start + PAGE_SIZE, matches.length);
      count.textContent = matches.length ? `Showing ${first}–${last} of ${matches.length} weapons` : '0 weapons';
    }
    renderPagination(matches.length, totalPages);
  }

  function installArsenal() {
    const picker = document.getElementById('picker');
    if (!picker || document.getElementById('pickerTitle')?.textContent !== 'Weapon') return;
    picker.classList.add('arsenal-mode');
    const tools = picker.querySelector('.bl-picker-tools');
    const list = document.getElementById('pickerList');
    if (!tools || !list) return;

    if (!document.getElementById('arsenalBody')) {
      const rarities = [...new Set(allWeapons().map((weapon) => weapon.rarity).filter(Boolean))].sort((a, b) => (RARITY_RANK[b] || 0) - (RARITY_RANK[a] || 0));
      tools.insertAdjacentHTML('beforeend', `<select id="arsRarity"><option value="">All Rarities</option>${rarities.map((value) => `<option>${esc(value)}</option>`).join('')}</select><select id="arsAcquisition"><option value="">All Acquisition</option><option value="craftable">Recipes proven</option><option value="direct">Direct acquisition</option><option value="unresolved">Unresolved</option></select><select id="arsMechanic"><option value="">All Mechanic Evidence</option><option value="resolved">Resolved mechanic</option><option value="no-fixed-skill-reference">No fixed-skill reference</option><option value="exact-fixed-skill-record-missing">Exact skill record missing</option></select><select id="arsSort"><option value="name">Sort: Name A–Z</option><option value="rarity">Sort: Rarity</option><option value="damage">Sort: Damage high–low</option><option value="rpm">Sort: Fire rate high–low</option></select><button id="arsCraftable" type="button">Craftable</button><button id="arsFavorites" type="button">★ Favorites</button><button type="button" disabled title="Owned inventory is not connected to a player account contract">Owned — not connected</button>`);

      const body = document.createElement('div');
      body.id = 'arsenalBody';
      body.className = 'arsenal-body';
      body.style.gridTemplateColumns = 'minmax(0,1fr)';

      const center = document.createElement('div');
      center.className = 'arsenal-center';
      list.parentNode.insertBefore(body, list);
      center.append(list);
      body.append(center);

      const footer = document.createElement('div');
      footer.className = 'arsenal-footer';
      footer.innerHTML = '<span id="arsResultCount">Weapons</span><span id="arsPageLabel" class="ars-page-label">Page 1</span><span id="arsPagination" class="ars-pagination" aria-label="Weapon pages"></span><span class="arsenal-footer-spacer"></span><button id="arsCancel" type="button">Cancel</button><button id="arsConfirm" type="button" class="primary" disabled>Confirm Selection</button>';
      picker.append(footer);

      tools.querySelectorAll('select').forEach((control) => control.addEventListener('change', () => applyFilters(true)));
      document.getElementById('pickerSearch')?.addEventListener('input', () => requestAnimationFrame(() => applyFilters(true)));
      document.getElementById('pickerFilter')?.addEventListener('change', () => requestAnimationFrame(() => applyFilters(true)));
      ['arsCraftable', 'arsFavorites'].forEach((id) => document.getElementById(id)?.addEventListener('click', (event) => {
        event.currentTarget.classList.toggle('active');
        applyFilters(true);
      }));
      document.getElementById('arsCancel').onclick = () => picker.close();
      document.getElementById('arsConfirm').onclick = () => {
        if (!pendingButton) return;
        allowBaseSelection = true;
        pendingButton.click();
        allowBaseSelection = false;
      };
    }

    enforceTwoColumnLayout();
    requestAnimationFrame(() => {
      applyFilters(false);
      if (!pendingWeapon) {
        const first = picker.querySelector('#pickerList > .bl-pick:not([hidden])');
        if (first) choosePending(first);
      }
    });
  }

  function bind() {
    const picker = document.getElementById('picker');
    if (!picker) return;

    picker.addEventListener('click', (event) => {
      if (!picker.classList.contains('arsenal-mode') || allowBaseSelection) return;
      const favorite = event.target.closest('[data-ars-favorite]');
      if (favorite) {
        event.preventDefault();
        event.stopImmediatePropagation();
        const set = favorites();
        const id = favorite.dataset.arsFavorite;
        set.has(id) ? set.delete(id) : set.add(id);
        storeFavorites(set);
        favorite.classList.toggle('active', set.has(id));
        applyFilters(false);
        return;
      }
      const card = event.target.closest('#pickerList > .bl-pick');
      if (card) {
        event.preventDefault();
        event.stopImmediatePropagation();
        choosePending(card);
      }
    }, true);

    new MutationObserver((mutations) => {
      enforceTwoColumnLayout();
      const needsRefresh = mutations.some((mutation) => [...mutation.addedNodes].some((node) => node.nodeType === 1 && ((node.matches?.('.bl-pick') && node.dataset.arsenalEnhanced !== '1') || node.querySelector?.('.bl-pick:not([data-arsenal-enhanced="1"])'))));
      if (needsRefresh || (document.getElementById('pickerTitle')?.textContent === 'Weapon' && !picker.classList.contains('arsenal-mode'))) requestAnimationFrame(installArsenal);
    }).observe(picker, { childList: true, subtree: true });

    picker.addEventListener('close', () => {
      picker.classList.remove('arsenal-mode');
      pendingButton = null;
      pendingWeapon = null;
      currentPage = 1;
      const confirm = document.getElementById('arsConfirm');
      if (confirm) confirm.disabled = true;
    });

    installArsenal();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, { once: true }); else bind();
})();
