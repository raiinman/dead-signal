(() => {
  'use strict';
  const data = window.DS_ARMOR_WEB;
  const results = document.getElementById('armorResults');
  const unavailable = document.getElementById('armorUnavailable');
  const status = document.getElementById('armorStatus');
  const search = document.getElementById('armorSearch');
  const slot = document.getElementById('armorSlot');
  const rarity = document.getElementById('armorRarity');
  const tabs = [...document.querySelectorAll('[data-armor-view]')];
  let view = 'sets';

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const art = (row) => row?.image_asset ? `<img src="${esc(row.image_asset)}" alt="${esc(row.name || '')}" loading="lazy">` : '<span>IMAGE PENDING</span>';
  const tierLabel = (row) => ['I','II','III','IV','V'][Number(row?.data_level ?? row?.tier ?? 0)-1] || '—';
  const tierNumber = (row) => Number(row?.data_level ?? row?.tier ?? 0);

  function validPiece(piece, parentSuit = null, keyArmor = false) {
    if (!piece || typeof piece !== 'object' || !String(piece.name || '').trim() || !String(piece.slot || '').trim()) return false;
    const blueprint = String(piece.blueprint_id ?? '');
    const canonical = String(piece.canonical_id || '');
    if (!blueprint || !canonical) return false;
    if (keyArmor) {
      if (canonical !== `ds-ka-${blueprint}`) return false;
    } else {
      const suit = String(piece.suit_id ?? '');
      if (!suit || suit !== String(parentSuit) || canonical !== `ds-a-${suit}-${blueprint}`) return false;
    }
    const tiers = Array.isArray(piece.tiers) ? piece.tiers : [];
    const tierNumbers = tiers.map(tierNumber);
    return tiers.length === 5 && new Set(tierNumbers).size === 5 && [1,2,3,4,5].every((value) => tierNumbers.includes(value));
  }

  function validContract(payload) {
    if (!payload || payload.schema !== 'dead-signal-armor' || payload.schema_version !== 1 || !Array.isArray(payload.armor_sets) || !Array.isArray(payload.key_armor)) return false;
    const ids = new Set();
    let pieces = 0;
    for (const armorSet of payload.armor_sets) {
      const suit = String(armorSet?.suit_id ?? '');
      const canonical = String(armorSet?.canonical_id || '');
      if (!suit || canonical !== `ds-as-${suit}` || !String(armorSet?.name || '').trim() || !Array.isArray(armorSet?.pieces)) return false;
      if (ids.has(canonical)) return false;
      ids.add(canonical);
      if (armorSet.piece_count != null && Number(armorSet.piece_count) !== armorSet.pieces.length) return false;
      for (const piece of armorSet.pieces) {
        if (!validPiece(piece, suit, false) || ids.has(piece.canonical_id)) return false;
        ids.add(piece.canonical_id);
        pieces += 1;
      }
    }
    for (const piece of payload.key_armor) {
      if (!validPiece(piece, null, true) || ids.has(piece.canonical_id)) return false;
      ids.add(piece.canonical_id);
      pieces += 1;
    }
    const counts = payload.record_counts || {};
    if (counts.armor_sets != null && Number(counts.armor_sets) !== payload.armor_sets.length) return false;
    if (counts.key_armor != null && Number(counts.key_armor) !== payload.key_armor.length) return false;
    if (counts.armor_pieces != null && Number(counts.armor_pieces) !== pieces) return false;
    return true;
  }

  if (!validContract(data)) {
    results.hidden = true;
    unavailable.hidden = false;
    status.textContent = 'Armor route prepared · verified compact contract not materialized.';
    return;
  }

  const sets = data.armor_sets;
  const keyArmor = data.key_armor;
  const allPieces = sets.flatMap((row) => row.pieces || []).concat(keyArmor);
  document.getElementById('setCount').textContent = sets.length;
  document.getElementById('pieceCount').textContent = allPieces.length;
  document.getElementById('keyCount').textContent = keyArmor.length;

  [...new Set(allPieces.map((row) => row.slot).filter(Boolean))].sort().forEach((value) => slot.add(new Option(value, value)));
  [...new Set(allPieces.map((row) => row.rarity).filter(Boolean))].sort().forEach((value) => rarity.add(new Option(value, value)));

  function pieceMatches(piece, query) {
    const haystack = `${piece.name || ''} ${piece.slot || ''} ${piece.rarity || ''} ${piece.key_effect || ''}`.toLowerCase();
    return (!query || haystack.includes(query)) && (!slot.value || piece.slot === slot.value) && (!rarity.value || piece.rarity === rarity.value);
  }

  function tierSummary(piece) {
    const tiers = piece.tiers || [];
    if (!tiers.length) return 'No Tier rows resolved';
    return tiers.map((row) => `Tier ${tierLabel(row)}`).join(' · ');
  }

  function pieceCard(piece) {
    return `<article class="armor-piece rarity-${esc(piece.rarity || '')}"><header><div><small>${esc(piece.slot || 'Slot unresolved')} · ${esc(piece.rarity || 'Rarity unresolved')}</small><h3>${esc(piece.name || 'Unnamed Armor')}</h3></div></header><div class="piece-meta"><div><span>Blueprint</span><b>${esc(piece.blueprint_id ?? '—')}</b></div><div><span>Tiers</span><b>${esc((piece.tiers || []).length)}</b></div><div><span>Recipes</span><b>${esc((piece.crafting_recipes || []).length)}</b></div></div><p class="recipe-note">${esc(tierSummary(piece))}. Missing recipe rows remain unresolved evidence, not proof of non-craftability.</p></article>`;
  }

  function bonuses(set) {
    const rows = (set.set_bonuses || []).filter((row) => row?.description || row?.effect || row?.name);
    return rows.length ? `<div class="bonus-list">${rows.map((row) => `<div><b>${esc(row.pieces_required ?? row.required_pieces ?? '?')} pieces</b><span>${esc(row.description || row.effect || row.name)}</span></div>`).join('')}</div>` : '<p class="armor-set-summary">No player-facing set bonus text is resolved in this contract.</p>';
  }

  function renderSets(query) {
    const output = [];
    let visiblePieces = 0;
    for (const set of sets) {
      const setText = `${set.name || ''} ${(set.set_bonuses || []).map((row) => row.description || row.effect || '').join(' ')}`.toLowerCase();
      const setMatch = !query || setText.includes(query);
      const pieces = (set.pieces || []).filter((piece) => pieceMatches(piece, setMatch ? '' : query));
      const shown = pieces.filter((piece) => (!slot.value || piece.slot === slot.value) && (!rarity.value || piece.rarity === rarity.value));
      if (!setMatch && !shown.length) continue;
      if ((slot.value || rarity.value) && !shown.length) continue;
      visiblePieces += shown.length;
      output.push(`<article class="armor-set"><div class="armor-set-head"><div class="armor-art">${art(set)}</div><div><p class="armor-code">SET // ${esc(set.suit_id ?? '—')}</p><h2>${esc(set.name || 'Unnamed Armor Set')}</h2><p class="armor-set-summary">${esc(set.piece_count ?? (set.pieces || []).length)} recorded pieces</p>${bonuses(set)}</div></div><div class="armor-pieces">${shown.map(pieceCard).join('')}</div></article>`);
    }
    results.innerHTML = output.join('');
    status.textContent = `${output.length} of ${sets.length} Armor Sets shown · ${visiblePieces} pieces visible.`;
  }

  function renderKey(query) {
    const rows = keyArmor.filter((piece) => pieceMatches(piece, query));
    results.innerHTML = `<div class="key-grid">${rows.map((piece) => `<article class="key-card rarity-${esc(piece.rarity || '')}"><div class="armor-art">${art(piece)}</div><p class="armor-code">KEY ARMOR // ${esc(piece.slot || 'Slot unresolved')}</p><h2>${esc(piece.name || 'Unnamed Key Armor')}</h2><p class="key-effect">${esc(piece.key_effect || 'No player-facing Key Armor effect is resolved in the current contract.')}</p>${pieceCard(piece)}</article>`).join('')}</div>`;
    status.textContent = `${rows.length} of ${keyArmor.length} Key Armor records shown.`;
  }

  function render() {
    const query = search.value.trim().toLowerCase();
    if (view === 'key') renderKey(query); else renderSets(query);
  }

  [search, slot, rarity].forEach((control) => control.addEventListener(control === search ? 'input' : 'change', render));
  document.getElementById('armorClear').addEventListener('click', () => { search.value = ''; slot.value = ''; rarity.value = ''; render(); });
  tabs.forEach((button) => button.addEventListener('click', () => {
    view = button.dataset.armorView;
    tabs.forEach((item) => { const active = item === button; item.classList.toggle('active', active); item.setAttribute('aria-selected', String(active)); });
    render();
  }));
  render();
})();
