(() => {
  'use strict';

  if (document.body.dataset.catalogueView !== 'detail') return;

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));
  const finite = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
  const normalize = (value) => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const romanTier = (tier) => ['I', 'II', 'III', 'IV', 'V'][Number(tier) - 1] || String(tier || '—');

  function currentRecord() {
    const requested = document.body.dataset.detailId || new URLSearchParams(location.search).get('weapon') || '';
    return (window.DS_WEAPON_MATH?.weapons || []).find((row) => (
      String(row.blueprint_id) === String(requested)
      || String(row.canonical_id) === String(requested)
      || normalize(row.name) === normalize(requested)
    )) || null;
  }

  function publicContract(record) {
    if (record?.public_contract) return record.public_contract;
    const published = window.DS_WEAPONS_WEB;
    if (!published?.weapons) return null;
    return published.weapons.find((row) => (
      String(row.blueprint_id) === String(record?.blueprint_id)
      || String(row.canonical_id) === String(record?.canonical_id)
    )) || null;
  }

  function acquisitionRows(contract, record) {
    const acquisition = contract?.acquisition || {};
    const fallbackHint = record?.acquisition_hint || '';
    const fallbackGain = record?.item_gain_path || '';
    const rows = [];
    const hint = acquisition.hint || fallbackHint;
    const gainPath = acquisition.gain_path || fallbackGain;
    if (hint) rows.push(['Acquisition hint', hint]);
    if (gainPath && gainPath !== hint) rows.push(['Gain path', gainPath]);
    if (finite(acquisition.fragment_id) && Number(acquisition.fragment_id) > 0) rows.push(['Blueprint fragment ID', acquisition.fragment_id]);
    if (finite(acquisition.fragments_to_unlock) && Number(acquisition.fragments_to_unlock) > 0) rows.push(['Fragments to unlock', acquisition.fragments_to_unlock]);
    if (acquisition.endowed_blueprint === true) rows.push(['Blueprint source', 'Endowed blueprint']);
    return rows;
  }

  function materialList(recipe) {
    const materials = Array.isArray(recipe?.fixed_materials) ? recipe.fixed_materials : [];
    if (!materials.length) return '<p class="weapon-evidence-empty">No fixed material rows are resolved for this Tier recipe.</p>';
    return `<ul class="weapon-material-list">${materials.map((row) => {
      const quantity = finite(row?.quantity) ? ` × ${Number(row.quantity).toLocaleString()}` : '';
      return `<li><b>${esc(row?.name || `Item ${row?.item_id || 'unresolved'}`)}</b><span>${esc(quantity || 'Quantity unresolved')}</span></li>`;
    }).join('')}</ul>`;
  }

  function recipeHtml(contract, selectedTier) {
    const tiers = contract?.progression?.gear_tiers || [];
    if (!tiers.length) {
      return '<div class="weapon-recipe-status unresolved"><strong>Recipe evidence not loaded</strong><p>The compact Miner contract is not present in this browser build. Dead Signal does not infer crafting from the legacy math payload.</p></div>';
    }
    const tier = tiers.find((row) => String(row.tier) === String(selectedTier)) || tiers.at(-1) || null;
    const recipe = tier?.recipe || null;
    if (!recipe) {
      return `<div class="weapon-recipe-status unresolved"><strong>Tier ${esc(romanTier(tier?.tier || selectedTier))} recipe unresolved</strong><p>No forge recipe is resolved for this recorded Gear Tier in the mined snapshot. This is <b>not</b> classified as non-craftable without stronger evidence.</p></div>`;
    }
    const currency = recipe.currency || {};
    const meta = [];
    if (finite(recipe.craft_time_seconds) && Number(recipe.craft_time_seconds) > 0) meta.push(`<span><b>Craft time</b>${esc(`${Number(recipe.craft_time_seconds)} s`)}</span>`);
    if (currency.name && finite(currency.quantity)) meta.push(`<span><b>${esc(currency.name)}</b>${esc(Number(currency.quantity).toLocaleString())}</span>`);
    if (finite(recipe.output_item_id) && Number(recipe.output_item_id) > 0) meta.push(`<span><b>Output item</b>${esc(recipe.output_item_id)}</span>`);
    return `<div class="weapon-recipe-status proven"><strong>Tier ${esc(romanTier(tier?.tier || selectedTier))} crafting evidence</strong><p>Recipe data is published from the installed-game forge tables. Presence proves a recipe row; it does not imply current-world availability.</p>${materialList(recipe)}${meta.length ? `<div class="weapon-recipe-meta">${meta.join('')}</div>` : ''}</div>`;
  }

  function installStyles() {
    if (document.getElementById('weaponDetailExtrasStyle')) return;
    const style = document.createElement('style');
    style.id = 'weaponDetailExtrasStyle';
    style.textContent = `
      .weapon-evidence-panel{margin-top:1rem;background:var(--panel);border:1px solid var(--line);padding:1.5rem}
      .weapon-evidence-panel h2{margin:.3rem 0 1.25rem}
      .weapon-evidence-grid{display:grid;grid-template-columns:minmax(240px,.8fr) minmax(320px,1.2fr);gap:1rem}
      .weapon-acquisition-card,.weapon-recipe-card{background:var(--panel-2);border:1px solid var(--line);padding:1rem}
      .weapon-acquisition-card h3,.weapon-recipe-card h3{margin:.15rem 0 1rem}
      .weapon-acquisition-list{display:grid;gap:.55rem;margin:0}
      .weapon-acquisition-list div{display:grid;grid-template-columns:minmax(120px,.7fr) 1.3fr;gap:.7rem;border-top:1px solid var(--line);padding-top:.55rem}
      .weapon-acquisition-list dt{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.07em}
      .weapon-acquisition-list dd{margin:0;overflow-wrap:anywhere}
      .weapon-recipe-card label{display:grid;gap:.4rem;color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.07em;margin-bottom:.8rem}
      .weapon-recipe-card select{min-height:44px;border:1px solid var(--line);background:var(--panel);color:var(--text);padding:.6rem;font:inherit}
      .weapon-recipe-status{border-left:3px solid var(--cyan);padding:.8rem 1rem;background:rgba(90,200,216,.06)}
      .weapon-recipe-status.unresolved{border-left-color:var(--rose);background:rgba(194,85,120,.07)}
      .weapon-recipe-status p,.weapon-evidence-empty{color:var(--muted);line-height:1.55}
      .weapon-material-list{list-style:none;padding:0;margin:.9rem 0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.5rem}
      .weapon-material-list li{display:flex;justify-content:space-between;gap:.8rem;border:1px solid var(--line);padding:.65rem .75rem}
      .weapon-material-list span{color:var(--muted);white-space:nowrap}
      .weapon-recipe-meta{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.5rem;margin-top:.8rem}
      .weapon-recipe-meta span{display:grid;gap:.25rem;border-top:1px solid var(--line);padding-top:.55rem}
      .weapon-recipe-meta b{color:var(--muted);font-size:.68rem;text-transform:uppercase}
      @media(max-width:760px){.weapon-evidence-grid{grid-template-columns:1fr}.weapon-material-list,.weapon-recipe-meta{grid-template-columns:1fr}}
    `;
    document.head.append(style);
  }

  function mount(attempt = 0) {
    const record = currentRecord();
    const shell = document.getElementById('weaponDetail');
    const progression = shell?.querySelector('.progression-panel');
    const provenance = shell?.querySelector('.provenance-panel');
    if ((!record || !progression || !provenance) && attempt < 40) {
      setTimeout(() => mount(attempt + 1), 50);
      return;
    }
    if (!record || !progression || !provenance || shell.querySelector('.weapon-evidence-panel')) return;

    installStyles();
    const contract = publicContract(record);
    const rows = acquisitionRows(contract, record);
    const tiers = contract?.progression?.gear_tiers || [];
    const pageTier = document.getElementById('gearTier');
    const selectedTier = pageTier?.value || tiers.at(-1)?.tier || 5;

    const panel = document.createElement('section');
    panel.className = 'weapon-evidence-panel';
    panel.innerHTML = `<p class="section-code">05B // Acquisition & crafting</p><h2>How this weapon is obtained and built</h2><div class="weapon-evidence-grid"><article class="weapon-acquisition-card"><h3>Acquisition evidence</h3>${rows.length ? `<dl class="weapon-acquisition-list">${rows.map(([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl>` : '<p class="weapon-evidence-empty">No player-facing acquisition path is resolved in the current projection.</p>'}</article><article class="weapon-recipe-card"><h3>Tier recipe</h3>${tiers.length ? `<label><span>Gear Tier recipe</span><select id="weaponRecipeTier">${tiers.map((row) => `<option value="${esc(row.tier)}"${String(row.tier) === String(selectedTier) ? ' selected' : ''}>Tier ${esc(romanTier(row.tier))}</option>`).join('')}</select></label>` : ''}<div id="weaponRecipeEvidence">${recipeHtml(contract, selectedTier)}</div></article></div>`;
    provenance.before(panel);

    const recipeTier = panel.querySelector('#weaponRecipeTier');
    const recipeEvidence = panel.querySelector('#weaponRecipeEvidence');
    const renderRecipe = (value) => { if (recipeEvidence) recipeEvidence.innerHTML = recipeHtml(contract, value); };
    recipeTier?.addEventListener('change', () => renderRecipe(recipeTier.value));
    pageTier?.addEventListener('change', () => {
      if (!recipeTier || ![...recipeTier.options].some((option) => option.value === pageTier.value)) return;
      recipeTier.value = pageTier.value;
      renderRecipe(recipeTier.value);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => mount(), { once: true });
  else mount();
})();
