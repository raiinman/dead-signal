(() => {
  'use strict';

  const published = window.DS_WEAPONS_WEB;
  const validContract = !!published
    && published.schema === 'dead-signal-weapons'
    && published.schema_version === 2
    && published.schema_contract?.name === 'Weapons v1'
    && published.schema_contract?.status === 'locked'
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
    if (!progression) return false;
    if (weapon.progression_state === 'not-applicable-special-equipped') {
      return Array.isArray(progression.gear_tiers) && progression.gear_tiers.length === 1;
    }
    if (weapon.progression_state === 'exact-blueprint-star-owner-gear-tier-owner-unresolved') {
      return !(progression.gear_tiers || []).length && !(progression.tier_star_matrix || []).length;
    }
    if (!['proven-static-base-attack', 'partial-nonstandard-progression'].includes(progression.formula_status)) return false;
    const gearTiers = progression.gear_tiers;
    const matrix = progression.tier_star_matrix;
    if (!Array.isArray(gearTiers) || gearTiers.length !== 5 || !hasExactNumbers(gearTiers.map((row) => row?.tier), LEGAL_TIERS)) return false;
    if (!Array.isArray(matrix) || matrix.length !== 5 || !hasExactNumbers(matrix.map((row) => row?.gear_tier), LEGAL_TIERS)) return false;
    if (progression.formula_status === 'partial-nonstandard-progression') {
      return matrix.every((row) => isFiniteNumber(row?.tier_base_attack_at_1_star)
        && Array.isArray(row?.blueprint_star_values) && row.blueprint_star_values.length === 0);
    }
    if ((progression.validation_issues || []).length) return false;
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

  const validRelationship = (relationship) => relationship?.state === 'resolved-four-state-relationship'
    && ['compatible_ids', 'incompatible_ids', 'unresolved_ids', 'not_applicable_ids']
      .every((key) => Array.isArray(relationship[key]));
  const validBuildContract = (weapon) => weapon?.schema_contract === 'weapons-v1'
    && validRelationship(weapon.attachment_compatibility)
    && validRelationship(weapon.calibration_compatibility)
    && ['resolved-selectable-options', 'unresolved', 'not-applicable'].includes(weapon?.ammo_configuration?.state);

  const canonicalIds = published.weapons.map((weapon) => String(weapon?.canonical_id || '').trim());
  if (!(canonicalIds.length === new Set(canonicalIds).size && canonicalIds.every(Boolean)
    && published.weapons.every((weapon) => validProgressionFor(weapon) && validBuildContract(weapon)))) return;

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
    attachment_compatibility: weapon.attachment_compatibility,
    calibration_compatibility: weapon.calibration_compatibility,
    ammo_configuration: weapon.ammo_configuration,
    crafting: weapon.crafting,
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

/* Build Lab visual + weapon-selector layer. Exact public contract only. */
(() => {
  'use strict';
  if (typeof location === 'undefined' || !/^\/build-planner\/?$/i.test(location.pathname)) return;

  const PAGE_SIZE = 10;
  const FAVORITES_KEY = 'dead-signal-weapon-favorites';
  const RARITY_RANK = Object.freeze({ Common: 1, Uncommon: 2, Rare: 3, Epic: 4, Legendary: 5 });
  const selector = {
    active: false,
    page: 1,
    pendingButton: null,
    allowBaseSelection: false,
    listObserver: null,
    installed: false,
  };

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const finite = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
  const num = (value) => finite(value) ? Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—';
  const allWeapons = () => Array.isArray(window.DS_WEAPON_MATH?.weapons) ? window.DS_WEAPON_MATH.weapons : [];
  const weaponMap = () => new Map(allWeapons().map((weapon) => [String(weapon?.name || '').trim(), weapon]));
  const tierOne = (weapon) => weapon?.tier_star_matrix?.find((row) => Number(row?.gear_tier) === 1)?.blueprint_star_values?.find((row) => Number(row?.blueprint_stars) === 1) || null;
  const statsFor = (weapon) => weapon?.static_inputs?.ranged_stats || weapon?.static_inputs?.melee_stats || {};
  const projectileCount = (stats) => Number(stats?.projectile_count ?? stats?.pellets ?? 1) || 1;
  const damageFor = (weapon) => {
    const attack = tierOne(weapon)?.base_attack;
    const projectiles = projectileCount(statsFor(weapon));
    return finite(attack) && projectiles > 1 ? `${num(attack)}×${num(projectiles)}` : num(attack);
  };
  const rangeFor = (weapon) => {
    const stats = statsFor(weapon);
    return num(stats?.range_meters ?? stats?.range);
  };
  const imageUrl = (weapon) => {
    const path = String(weapon?.image_asset || '').replace(/\\/g, '/').trim();
    if (!path) return '';
    if (/^https?:/i.test(path) || /^data:/i.test(path)) return path;
    if (path.startsWith('/assets/')) return `/build-planner${path}`;
    if (path.startsWith('/')) return path;
    return `/build-planner/${path.replace(/^\.\//, '')}`;
  };
  const effectText = (weapon) => {
    const effect = weapon?.static_inputs?.weapon_effect;
    if (typeof effect === 'string') return effect.trim();
    return String(effect?.description || effect?.text || effect?.name || '').trim();
  };
  const effectStatus = (weapon) => String(weapon?.public_contract?.effect_resolution?.status || weapon?.public_contract?.effect_evidence?.status || '').trim();
  const specialSkill = (weapon) => {
    const text = effectText(weapon);
    if (text) return { state: 'resolved', label: 'RESOLVED', text };
    const status = effectStatus(weapon);
    if (status === 'no-fixed-skill-reference') {
      return { state: 'no-fixed', label: 'NO FIXED SKILL', text: 'No fixed-skill reference is present in the current exact weapon progression path.' };
    }
    if (status === 'exact-fixed-skill-record-missing') {
      return { state: 'unresolved', label: 'UNRESOLVED', text: 'A fixed-skill reference exists, but its exact passive-skill record is unresolved.' };
    }
    if (status === 'exact-fixed-skill-record-present-effect-text-unresolved') {
      return { state: 'unresolved', label: 'UNRESOLVED', text: 'The exact skill record is present, but player-facing effect text is unresolved.' };
    }
    return { state: 'review', label: 'REVIEW', text: 'No player-facing special-skill text is currently resolved for this weapon.' };
  };
  const publishedText = (value) => {
    if (typeof value === 'string') return value.trim();
    if (!value || typeof value !== 'object') return '';
    const status = String(value.publication_status || value.status || '').toLowerCase();
    if (status && /(withheld|unresolved|conflict|suspect|blocked)/.test(status)) return '';
    const candidate = value.text || value.description || value.value || value.published_text || value.player_facing_text || '';
    return typeof candidate === 'string' ? candidate.trim() : '';
  };
  const weaponDescription = (weapon) => {
    const contract = weapon?.public_contract || {};
    for (const value of [contract.player_facing_description, contract.weapon_description, contract.catalog_description, contract.description]) {
      const text = publishedText(value);
      if (text) return { text, verified: true };
    }
    const evidence = contract.short_description_evidence;
    if (evidence && typeof evidence === 'object') {
      const publication = String(evidence.publication_status || '').toLowerCase();
      if (/(published|verified|approved|resolved-for-publication)/.test(publication) && !/(withheld|suspect|conflict|unresolved)/.test(publication)) {
        const text = publishedText(evidence.published_text || evidence.player_facing_text || evidence.resolved_text || evidence.description);
        if (text) return { text, verified: true };
      }
    }
    return { text: 'No verified player-facing weapon description is currently published for this record.', verified: false };
  };
  const acquisition = (weapon) => {
    const contract = weapon?.public_contract || {};
    const tiers = Array.isArray(contract.progression?.gear_tiers) ? contract.progression.gear_tiers : [];
    const recipeCount = tiers.filter((tier) => tier?.recipe).length;
    const gain = String(contract.acquisition?.gain_path || weapon?.item_gain_path || '').trim();
    if (tiers.length && recipeCount === tiers.length) return { state: 'craftable', label: 'Recipes proven', detail: `${recipeCount}/${tiers.length} Gear Tier recipes` };
    if (/stronghold exploration/i.test(gain)) return { state: 'direct', label: 'Direct acquisition', detail: gain };
    if (recipeCount) return { state: 'partial', label: 'Recipe evidence partial', detail: `${recipeCount}/${tiers.length || 5} Gear Tier recipes` };
    return { state: 'unresolved', label: 'Acquisition unresolved', detail: 'No exact recipe or direct path proven' };
  };
  const evidenceLabel = (weapon) => {
    const status = effectStatus(weapon);
    if (effectText(weapon)) return 'MECHANIC RESOLVED';
    if (status === 'no-fixed-skill-reference') return 'NO FIXED SKILL';
    if (status === 'exact-fixed-skill-record-missing') return 'SKILL RECORD MISSING';
    return 'REVIEW';
  };
  const favorites = () => {
    try { return new Set(JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]')); }
    catch (_) { return new Set(); }
  };
  const storeFavorites = (set) => {
    try { localStorage.setItem(FAVORITES_KEY, JSON.stringify([...set])); }
    catch (_) {}
  };
  const cardName = (card) => String(card?.dataset?.weaponName || card?.querySelector('.arsenal-title strong')?.textContent || card?.querySelector('strong')?.textContent || '').trim();
  const recordForCard = (card) => weaponMap().get(cardName(card)) || null;
  const rarityClass = (weapon) => `ars-rarity-${String(weapon?.rarity || 'unknown').toLowerCase()}`;

  function installStyle() {
    document.getElementById('ds-build-lab-render-v4')?.remove();
    const style = document.createElement('style');
    style.id = 'ds-build-lab-render-v4';
    style.textContent = `
      body{background:#05080b!important}
      .bl-app{background:radial-gradient(circle at 70% -8%,rgba(28,221,229,.07),transparent 34rem),radial-gradient(circle at 16% 0,rgba(242,58,67,.06),transparent 28rem),linear-gradient(rgba(255,255,255,.012) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.012) 1px,transparent 1px),#05080b!important;background-size:auto,auto,36px 36px,36px 36px!important}
      .bl-command{min-height:82px!important;padding:13px clamp(18px,2vw,30px)!important;background:rgba(4,8,11,.97)!important;border-bottom:1px solid #1d2c34!important;box-shadow:0 12px 34px rgba(0,0,0,.28)!important}
      .bl-command::before{width:2px!important;background:linear-gradient(#24dce4,#f23a43)!important}
      .bl-command-mark{width:38px!important;height:38px!important;border-color:#235b62!important;background:#08191d!important;color:#6de5ea!important}
      .bl-command h1{font-size:clamp(1.55rem,2.1vw,2rem)!important}
      .bl-command-copy{font-size:var(--ds-type-tiny)!important}
      .bl-action-group{padding-top:16px!important;background:#080d11!important;border-color:#22313a!important}
      .bl-actions button{min-height:32px!important;background:#0a1116!important;border-color:#2b3942!important}
      .bl-actions .primary{background:linear-gradient(180deg,#f23a43,#aa1e29)!important;border-color:#cf303a!important}
      .bl-statusbar{min-height:40px!important;background:#060a0d!important;border-bottom-color:#18242b!important}
      .bl-main{width:min(1660px,100%)!important;padding:18px clamp(16px,2vw,28px) 34px!important}
      .bl-intro{display:block!important;min-height:198px!important;margin-bottom:12px!important;border:1px solid #22343e!important;border-radius:11px!important;overflow:hidden!important;background:radial-gradient(circle at 84% 28%,rgba(33,219,228,.08),transparent 24%),linear-gradient(120deg,#081017,#081117 55%,#070c10 100%)!important;box-shadow:none!important}
      .bl-intro::before{content:""!important;position:absolute!important;inset:0!important;pointer-events:none!important;background:linear-gradient(rgba(33,219,228,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(33,219,228,.035) 1px,transparent 1px)!important;background-size:24px 24px!important;mask:linear-gradient(90deg,#000 0 74%,transparent 96%)!important}
      .bl-intro::after{content:"DS"!important;left:auto!important;right:3%!important;top:auto!important;bottom:-34%!important;width:auto!important;height:auto!important;transform:none!important;border:0!important;background:none!important;box-shadow:none!important;color:rgba(242,58,67,.055)!important;font-size:clamp(8rem,15vw,14rem)!important;font-weight:950!important;letter-spacing:-.08em!important}
      .bl-intro-card{min-height:198px!important;padding:25px clamp(24px,3vw,42px)!important;background:transparent!important;border:0!important;box-shadow:none!important}
      .bl-intro-card::before,.bl-intro-card::after{display:none!important}
      .bl-eyebrow{margin-bottom:8px!important;color:#ff5059!important}
      .bl-intro h2{max-width:760px!important;font-size:clamp(2.15rem,3.4vw,3.25rem)!important;line-height:.98!important}
      .bl-intro h2 em{color:#27dbe3!important;text-shadow:0 0 18px rgba(39,219,227,.10)!important}
      .bl-intro-card>p:not(.bl-eyebrow){max-width:760px!important;margin-top:13px!important;color:#9aa7ae!important;font-size:var(--ds-type-sm)!important;line-height:1.55!important}
      .bl-intro>.bl-health-card{display:none!important}
      .bl-layout{grid-template-columns:minmax(0,1fr) minmax(330px,370px)!important;gap:12px!important}
      .bl-stack{gap:10px!important}
      .bl-panel,.bl-summary{border:1px solid #20313a!important;border-radius:10px!important;background:linear-gradient(180deg,#081016,#060b0f)!important;box-shadow:none!important}
      .bl-panel{padding:13px!important}.bl-panel::before{height:52px!important}
      .bl-panel-title{margin-bottom:11px!important;gap:9px!important}.bl-panel-title>b{width:28px!important;height:28px!important;border-radius:6px!important}.bl-panel-title h2,.bl-summary-title h2{font-size:var(--ds-type-lg)!important}
      .bl-fields{grid-template-columns:2fr 1fr .8fr 1.2fr!important;gap:7px!important}.bl-field{gap:4px!important}.bl-field input,.bl-field select{min-height:36px!important;padding:7px 9px!important;background:#060b0f!important;border-color:#26343c!important}.bl-field textarea{min-height:116px!important;background:#060b0f!important}
      .bl-slots{gap:7px!important}.bl-slots.weapons{grid-template-columns:repeat(3,minmax(0,1fr))!important}.bl-slots.armor{grid-template-columns:repeat(6,minmax(0,1fr))!important}
      .bl-slot{min-height:145px!important;padding:10px!important;border-radius:8px!important;background:linear-gradient(145deg,#081116,#060b0f)!important}.bl-slots.armor .bl-slot{min-height:136px!important}.bl-slot-head{gap:5px!important}.bl-slot-actions button{min-height:25px!important;padding:4px 6px!important}.bl-empty{min-height:82px!important}
      .bl-item{grid-template-columns:72px minmax(0,1fr)!important;gap:9px!important;margin-top:8px!important}.bl-item-art{width:72px!important;height:64px!important;border-radius:7px!important;background:linear-gradient(rgba(33,219,228,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(33,219,228,.035) 1px,transparent 1px),#071016!important;background-size:16px 16px!important;overflow:hidden!important}.bl-item-art.ds-weapon-art img{width:100%!important;height:100%!important;object-fit:contain!important;padding:6px!important;filter:drop-shadow(0 8px 10px rgba(0,0,0,.55))!important}.bl-item h3{font-size:var(--ds-type-sm)!important}.bl-item-meta{gap:4px!important;margin-top:4px!important}.bl-chip{min-height:19px!important;padding:2px 5px!important}
      .bl-item-note{display:-webkit-box!important;margin-top:5px!important;overflow:hidden!important;font-size:var(--ds-type-tiny)!important;line-height:1.4!important;-webkit-box-orient:vertical!important;-webkit-line-clamp:2!important}
      .ds-planner-weapon-stats{display:grid!important;grid-template-columns:repeat(3,1fr)!important;gap:4px!important;margin-top:7px!important}.ds-planner-weapon-stats span{padding:5px 6px!important;border:1px solid #20313a!important;border-radius:4px!important;background:#060c10!important}.ds-planner-weapon-stats small{display:block!important;color:#6e7e87!important;font-size:var(--ds-type-micro)!important}.ds-planner-weapon-stats b{display:block!important;margin-top:1px!important;color:#edf3f5!important;font-size:var(--ds-type-tiny)!important}.ds-planner-evidence{display:flex!important;justify-content:space-between!important;gap:8px!important;margin-top:5px!important;color:#5edeb9!important;font-size:var(--ds-type-micro)!important}.ds-planner-evidence span{color:#77858d!important}
      .bl-slot-footer{margin-top:7px!important;gap:4px!important}.bl-slot-footer label{min-width:80px!important}.bl-slot-footer button{min-height:29px!important;font-size:var(--ds-type-micro)!important}
      .bl-systems{gap:7px!important}.bl-system-card{min-height:120px!important;padding:11px!important;border-radius:8px!important}.bl-system-card button{min-height:30px!important;margin-top:9px!important}.bl-cradles{grid-template-columns:repeat(5,minmax(0,1fr))!important;gap:6px!important;margin-top:8px!important}.bl-cradle{min-height:72px!important;padding:8px!important}
      .bl-summary{position:sticky!important;top:94px!important;padding:14px!important;background:radial-gradient(circle at 14% 0,rgba(33,219,228,.045),transparent 24%),linear-gradient(180deg,#071118,#060b0f)!important}.bl-summary-title{padding-bottom:11px!important;border-bottom-color:#22343d!important}.bl-summary-title>b{width:31px!important;height:31px!important}
      .ds-summary-health{display:grid!important;grid-template-columns:repeat(2,1fr)!important;gap:6px!important;padding:11px 0!important;border-bottom:1px solid #1d2a31!important}.ds-summary-health>div{min-height:57px!important;padding:8px 9px!important;border:1px solid #22343d!important;border-radius:6px!important;background:#060d11!important}.ds-summary-health strong{display:block!important;color:#eef4f6!important;font-size:var(--ds-type-md)!important}.ds-summary-health span{display:block!important;margin-top:2px!important;color:#72818a!important;font-size:var(--ds-type-micro)!important}.ds-summary-health>div:nth-child(1){border-top-color:#f23a43!important}.ds-summary-health>div:nth-child(2){border-top-color:#2f8dff!important}.ds-summary-health>div:nth-child(3){border-top-color:#a54cff!important}.ds-summary-health>div:nth-child(4){border-top-color:#ffb52c!important}.bl-summary-section{padding:11px 0!important}.bl-summary-row{padding:5px 0!important}.bl-progress{height:7px!important}.bl-progress i{background:linear-gradient(90deg,#24cfe1,#27d7c5,#42d68d)!important}.bl-footer{padding-top:18px!important}
      #picker.arsenal-mode{width:min(1320px,calc(100vw - 34px))!important;height:min(88vh,900px)!important;max-height:none!important;padding:0!important;border:1px solid #29404b!important;border-radius:12px!important;background:#050b0f!important;overflow:hidden!important;box-shadow:0 34px 110px rgba(0,0,0,.72)!important}
      #picker.arsenal-mode::backdrop{background:rgba(0,0,0,.78)!important;backdrop-filter:blur(5px)!important}
      #picker.arsenal-mode .bl-picker-head{min-height:78px!important;padding:14px 18px 13px 76px!important;position:relative!important;border-bottom:1px solid #22343e!important;background:radial-gradient(circle at 32px 36px,rgba(242,58,67,.16),transparent 26px),linear-gradient(90deg,rgba(33,219,228,.04),transparent 38%)!important}
      #picker.arsenal-mode .bl-picker-head::before{content:"◎"!important;position:absolute!important;left:22px!important;top:18px!important;display:grid!important;place-items:center!important;width:40px!important;height:40px!important;border:1px solid #6c232a!important;border-radius:50%!important;background:#170b0f!important;color:#ff4b55!important;font-size:1.25rem!important;font-weight:900!important}
      #picker.arsenal-mode .bl-picker-head small{color:#ff525b!important;letter-spacing:.14em!important}.arsenal-subtitle{display:block!important;margin-top:3px!important;color:#7e8b93!important;font-size:var(--ds-type-xs)!important}
      #picker.arsenal-mode .bl-picker-tools{display:grid!important;grid-template-columns:minmax(250px,1.65fr) repeat(4,minmax(130px,.75fr))!important;gap:7px!important;padding:11px 16px 7px!important;border-bottom:0!important;background:#060b0f!important}
      #picker.arsenal-mode .bl-picker-tools input,#picker.arsenal-mode .bl-picker-tools select,#picker.arsenal-mode .arsenal-tool{min-height:38px!important;padding:7px 10px!important;border:1px solid #2b3b44!important;border-radius:5px!important;background:#071014!important;color:#dce3e6!important;outline:none!important}
      #picker.arsenal-mode .bl-picker-tools input:focus,#picker.arsenal-mode .bl-picker-tools select:focus{border-color:#2ccbd4!important;box-shadow:0 0 0 2px rgba(44,203,212,.08)!important}
      .arsenal-secondary-tools{display:grid!important;grid-template-columns:minmax(250px,1.65fr) repeat(4,minmax(130px,.75fr))!important;gap:7px!important;padding:0 16px 11px!important;background:#060b0f!important;border-bottom:1px solid #20303a!important}.arsenal-secondary-tools button,.arsenal-secondary-tools .arsenal-static{min-height:36px!important;border:1px solid #273740!important;border-radius:5px!important;background:#071014!important;color:#aeb8be!important;font-size:var(--ds-type-tiny)!important;font-weight:800!important}.arsenal-secondary-tools button:hover{border-color:#2ccbd4!important;color:#fff!important}.arsenal-secondary-tools button.active{border-color:#24755e!important;background:#071813!important;color:#73dfad!important}.arsenal-secondary-tools button:disabled{opacity:.46!important;cursor:not-allowed!important}
      .arsenal-body{display:block!important;min-height:0!important;height:calc(100% - 78px - 92px - 54px)!important;overflow:hidden!important}.arsenal-center{height:100%!important;min-width:0!important}
      #picker.arsenal-mode .bl-picker-list{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;align-content:start!important;gap:9px!important;height:100%!important;max-height:none!important;padding:10px!important;overflow:auto!important;background:#050a0d!important}
      #picker.arsenal-mode .arsenal-card{--ars-color:#93a0a7;--ars-wash:rgba(147,160,167,.05);position:relative!important;display:grid!important;grid-template-columns:170px minmax(0,1fr)!important;min-height:292px!important;height:auto!important;padding:0!important;border:1px solid color-mix(in srgb,var(--ars-color) 36%,#26343c)!important;border-radius:8px!important;background:linear-gradient(145deg,var(--ars-wash),transparent 32%),#071014!important;color:#eaf0f2!important;text-align:left!important;overflow:hidden!important;box-shadow:inset 2px 0 var(--ars-color)!important}
      #picker.arsenal-mode .arsenal-card:hover,#picker.arsenal-mode .arsenal-card:focus-visible{border-color:color-mix(in srgb,var(--ars-color) 70%,#fff 5%)!important;outline:0!important;background:linear-gradient(145deg,color-mix(in srgb,var(--ars-wash) 140%,transparent),transparent 36%),#081116!important}#picker.arsenal-mode .arsenal-card.arsenal-selected{box-shadow:inset 3px 0 var(--ars-color),0 0 0 1px #26d6de,0 0 20px rgba(38,214,222,.10)!important}
      .arsenal-check{position:absolute!important;z-index:3!important;left:11px!important;top:11px!important;width:16px!important;height:16px!important;border:1px solid #41515a!important;border-radius:4px!important;background:#061015!important}.arsenal-selected .arsenal-check{border-color:#2bd5dd!important;background:#2bd5dd!important;box-shadow:inset 0 0 0 4px #071014!important}.arsenal-favorite{position:absolute!important;z-index:3!important;right:11px!important;top:8px!important;color:#627078!important;font-size:1rem!important}.arsenal-favorite.active{color:#ffc34c!important;text-shadow:0 0 10px rgba(255,195,76,.25)!important}
      .arsenal-art{display:grid!important;place-items:center!important;min-height:292px!important;padding:24px 16px 14px!important;border-right:1px solid #1f3038!important;background:linear-gradient(rgba(33,219,228,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(33,219,228,.035) 1px,transparent 1px),radial-gradient(circle at 50% 48%,var(--ars-wash),transparent 56%),#071015!important;background-size:24px 24px,24px 24px,auto,auto!important}.arsenal-art img{width:100%!important;height:132px!important;object-fit:contain!important;filter:drop-shadow(0 14px 15px rgba(0,0,0,.62))!important}.arsenal-art b{color:#7d8b93!important}.arsenal-art small{display:block!important;margin-top:6px!important;color:#5d6b73!important}
      .arsenal-copy{display:flex!important;flex-direction:column!important;min-width:0!important;padding:11px 13px 10px!important}.arsenal-title{display:block!important;padding-right:25px!important}.arsenal-title strong{font-size:var(--ds-type-md)!important;line-height:1.2!important}.arsenal-chips{display:flex!important;flex-wrap:wrap!important;gap:4px!important;margin-top:5px!important}.arsenal-chips i{display:inline-flex!important;min-height:18px!important;align-items:center!important;padding:2px 5px!important;border:1px solid #304049!important;border-radius:4px!important;background:#071015!important;color:#99a5ab!important;font-size:var(--ds-type-micro)!important;font-style:normal!important;font-weight:900!important;text-transform:uppercase!important}.arsenal-chips i:first-child{border-color:color-mix(in srgb,var(--ars-color) 58%,#25343c)!important;color:var(--ars-color)!important}
      .arsenal-description,.arsenal-skill{display:grid!important;gap:3px!important;margin-top:7px!important}.arsenal-section-label{color:#75848d!important;font-size:var(--ds-type-micro)!important;font-weight:900!important;letter-spacing:.105em!important;text-transform:uppercase!important}.arsenal-description-copy{display:-webkit-box!important;overflow:hidden!important;color:#a8b3b9!important;font-size:var(--ds-type-tiny)!important;line-height:1.42!important;-webkit-box-orient:vertical!important;-webkit-line-clamp:2!important}.arsenal-description.unavailable .arsenal-description-copy{color:#69777f!important;font-style:italic!important}.arsenal-skill-head{display:flex!important;align-items:center!important;gap:6px!important}.arsenal-skill-state{display:inline-flex!important;align-items:center!important;min-height:17px!important;padding:1px 5px!important;border:1px solid #354650!important;border-radius:999px!important;background:#071014!important;color:#86949b!important;font-size:var(--ds-type-micro)!important;font-weight:900!important}.arsenal-skill.resolved .arsenal-skill-state{border-color:#266650!important;color:#6fe0a7!important;background:#06150f!important}.arsenal-skill.unresolved .arsenal-skill-state,.arsenal-skill.review .arsenal-skill-state{border-color:#71531c!important;color:#efbd5d!important;background:#150f03!important}.arsenal-skill-copy{display:-webkit-box!important;overflow:hidden!important;color:#a9b4ba!important;font-size:var(--ds-type-tiny)!important;line-height:1.42!important;-webkit-box-orient:vertical!important;-webkit-line-clamp:3!important}.arsenal-skill.no-fixed .arsenal-skill-copy{color:#7f8d95!important}
      .arsenal-stats{display:grid!important;grid-template-columns:repeat(3,1fr)!important;gap:5px!important;margin-top:auto!important;padding-top:8px!important}.arsenal-stats>span{min-height:41px!important;padding:6px 7px!important;border:1px solid #22343d!important;border-radius:5px!important;background:#060d11!important}.arsenal-stats small{display:block!important;color:#6f7e87!important;font-size:var(--ds-type-micro)!important}.arsenal-stats b{display:block!important;margin-top:1px!important;color:#eef3f5!important;font-size:var(--ds-type-xs)!important}
      .arsenal-evidence{display:grid!important;grid-template-columns:auto auto minmax(0,1fr) auto!important;align-items:center!important;gap:7px!important;margin-top:7px!important;padding-top:7px!important;border-top:1px solid #1d2d35!important;font-size:var(--ds-type-micro)!important}.arsenal-evidence>strong{color:#36d9c5!important;letter-spacing:.06em!important}.arsenal-evidence>span{color:#99a7ad!important}.arsenal-evidence>small{color:#67767f!important;overflow:hidden!important;text-overflow:ellipsis!important;white-space:nowrap!important}.arsenal-evidence .evidence-state{justify-self:end!important;color:#49daca!important;font-weight:900!important}
      .ars-rarity-legendary{--ars-color:#e9b84e!important;--ars-wash:rgba(233,184,78,.10)!important}.ars-rarity-epic{--ars-color:#b769ff!important;--ars-wash:rgba(183,105,255,.10)!important}.ars-rarity-rare{--ars-color:#4da5ff!important;--ars-wash:rgba(77,165,255,.10)!important}.ars-rarity-uncommon{--ars-color:#56d486!important;--ars-wash:rgba(86,212,134,.10)!important}.ars-rarity-common{--ars-color:#9aa6ac!important;--ars-wash:rgba(154,166,172,.07)!important}
      .arsenal-footer{display:flex!important;align-items:center!important;gap:10px!important;min-height:54px!important;padding:8px 14px!important;border-top:1px solid #20313a!important;background:#060b0f!important;color:#75838b!important;font-size:var(--ds-type-tiny)!important}.arsenal-footer-spacer{flex:1!important}.arsenal-page-controls{display:flex!important;align-items:center!important;gap:4px!important}.arsenal-page-controls button{min-width:30px!important;height:30px!important;padding:0 7px!important;border:1px solid #293942!important;border-radius:5px!important;background:#071014!important;color:#a7b2b8!important}.arsenal-page-controls button.active{border-color:#a92a33!important;background:#170b0e!important;color:#ff5c65!important}.arsenal-page-controls button:disabled{opacity:.35!important;cursor:not-allowed!important}.arsenal-page-size{padding:6px 9px!important;border:1px solid #293942!important;border-radius:5px!important;background:#071014!important;color:#9aa7ae!important}.arsenal-footer>.arsenal-cancel,.arsenal-footer>.arsenal-confirm{min-height:36px!important;padding:7px 14px!important;border:1px solid #34424a!important;border-radius:5px!important;background:#0a1115!important;color:#cbd3d7!important;font-weight:850!important}.arsenal-footer>.arsenal-confirm{min-width:160px!important;border-color:#c72e39!important;background:linear-gradient(180deg,#f23a43,#aa1f29)!important;color:#fff!important}.arsenal-footer>.arsenal-confirm:disabled{opacity:.42!important;cursor:not-allowed!important}
      @media(max-width:1320px){.bl-slots.armor{grid-template-columns:repeat(3,minmax(0,1fr))!important}.bl-layout{grid-template-columns:minmax(0,1fr) 330px!important}#picker.arsenal-mode .arsenal-card{grid-template-columns:145px minmax(0,1fr)!important}.arsenal-art{padding-inline:10px!important}}
      @media(max-width:1050px){.bl-layout{grid-template-columns:1fr!important}.bl-summary{position:static!important}.bl-slots.weapons{grid-template-columns:1fr!important}.bl-slots.armor{grid-template-columns:repeat(2,minmax(0,1fr))!important}#picker.arsenal-mode .bl-picker-tools,.arsenal-secondary-tools{grid-template-columns:repeat(2,minmax(0,1fr))!important}#picker.arsenal-mode .bl-picker-list{grid-template-columns:1fr!important}.arsenal-body{height:calc(100% - 78px - 138px - 54px)!important}}
      @media(max-width:680px){.bl-fields,.bl-slots.armor,.bl-systems,.bl-cradles{grid-template-columns:1fr!important}.bl-panel-title .right{display:none!important}#picker.arsenal-mode{width:calc(100vw - 12px)!important;height:94vh!important}#picker.arsenal-mode .bl-picker-tools,.arsenal-secondary-tools{grid-template-columns:1fr!important}.arsenal-body{height:calc(100% - 78px - 256px - 54px)!important}#picker.arsenal-mode .arsenal-card{grid-template-columns:1fr!important}.arsenal-art{min-height:135px!important;border-right:0!important;border-bottom:1px solid #1f3038!important}.arsenal-art img{height:105px!important}.arsenal-footer{flex-wrap:wrap!important}.arsenal-footer-spacer{display:none!important}}
    `;
    document.head.append(style);
    document.getElementById('ds-build-lab-weapon-card-geometry')?.remove();
  }

  function syncSummaryHealth() {
    const summary = document.querySelector('.bl-summary');
    const source = document.querySelector('.bl-intro .bl-health-card');
    if (!summary || !source) return;
    let host = summary.querySelector('.ds-summary-health');
    if (!host) {
      host = document.createElement('div');
      host.className = 'ds-summary-health';
      summary.querySelector('.bl-summary-title')?.insertAdjacentElement('afterend', host);
    }
    const rows = [
      ['healthWeapons', 'Weapons'],
      ['healthArmor', 'Armor Pieces'],
      ['healthMods', 'Mod Families'],
      ['healthSystems', 'Build-system Families'],
    ];
    host.innerHTML = rows.map(([id, label]) => `<div><strong>${esc(document.getElementById(id)?.textContent || '—')}</strong><span>${esc(label)}</span></div>`).join('');
  }

  function enhancePlannerWeaponArt(scope = document) {
    const map = weaponMap();
    scope.querySelectorAll?.('#weaponSlots .bl-slot.has-item').forEach((slot) => {
      const name = String(slot.querySelector('.bl-item h3')?.textContent || '').trim();
      const weapon = map.get(name);
      const art = slot.querySelector('.bl-item-art');
      if (!weapon || !art || art.dataset.dsWeaponImage === weapon.canonical_id) return;
      const image = imageUrl(weapon);
      if (!image) return;
      art.dataset.dsWeaponImage = weapon.canonical_id;
      art.classList.add('ds-weapon-art');
      art.innerHTML = `<img src="${esc(image)}" alt="" loading="lazy" decoding="async">`;
      const item = slot.querySelector('.bl-item>div:last-child');
      if (item && !item.querySelector('.ds-planner-weapon-stats')) {
        const stats = statsFor(weapon);
        const acq = acquisition(weapon);
        item.insertAdjacentHTML('beforeend', `<div class="ds-planner-weapon-stats"><span><small>DMG</small><b>${esc(damageFor(weapon))}</b></span><span><small>FIRE RATE</small><b>${esc(num(stats?.rpm ?? stats?.fire_rate))}</b></span><span><small>RANGE</small><b>${esc(rangeFor(weapon))}</b></span></div><div class="ds-planner-evidence"><b>${esc(acq.label)}</b><span>${esc(evidenceLabel(weapon))}</span></div>`);
      }
    });
  }

  function installPlannerEnhancements() {
    syncSummaryHealth();
    enhancePlannerWeaponArt();
    const health = document.querySelector('.bl-intro .bl-health-card');
    if (health) new MutationObserver(syncSummaryHealth).observe(health, { childList: true, subtree: true, characterData: true });
    const weaponSlots = document.getElementById('weaponSlots');
    if (weaponSlots) new MutationObserver(() => enhancePlannerWeaponArt(weaponSlots)).observe(weaponSlots, { childList: true, subtree: true });
  }

  function buildSelectorControls() {
    const picker = document.getElementById('picker');
    const tools = picker?.querySelector('.bl-picker-tools');
    const list = document.getElementById('pickerList');
    if (!picker || !tools || !list) return;
    picker.classList.add('arsenal-mode');
    ['arsRarity','arsAcquisition','arsMechanic'].forEach((id) => { const node=document.getElementById(id); if(node) node.hidden=false; });
    const secondaryExisting=document.getElementById('arsSecondaryTools'); if(secondaryExisting) secondaryExisting.hidden=false;
    const footerExisting=document.getElementById('arsFooter'); if(footerExisting) footerExisting.hidden=false;
    const head = picker.querySelector('.bl-picker-head>div');
    if (head && !head.querySelector('.arsenal-subtitle')) head.insertAdjacentHTML('beforeend', '<span class="arsenal-subtitle">Choose from current player-facing records.</span>');
    document.getElementById('pickerSearch')?.setAttribute('placeholder', 'Search weapons by name, skill, or description…');
    const baseType = document.getElementById('pickerFilter');
    if (baseType) baseType.setAttribute('aria-label', 'Weapon type');

    if (!document.getElementById('arsRarity')) {
      const rarities = [...new Set(allWeapons().map((weapon) => weapon.rarity).filter(Boolean))].sort((a, b) => (RARITY_RANK[b] || 0) - (RARITY_RANK[a] || 0));
      tools.insertAdjacentHTML('beforeend', `
        <select id="arsRarity" aria-label="Rarity"><option value="">All Rarities</option>${rarities.map((value) => `<option value="${esc(value)}">${esc(value)}</option>`).join('')}</select>
        <select id="arsAcquisition" aria-label="Acquisition"><option value="">All Acquisition</option><option value="craftable">Recipes proven</option><option value="direct">Direct acquisition</option><option value="partial">Partial recipe evidence</option><option value="unresolved">Unresolved</option></select>
        <select id="arsMechanic" aria-label="Mechanic evidence"><option value="">All Mechanic Evidence</option><option value="resolved">Resolved mechanic</option><option value="no-fixed-skill-reference">No fixed-skill reference</option><option value="exact-fixed-skill-record-missing">Exact skill record missing</option></select>`);
    }
    if (!document.getElementById('arsSecondaryTools')) {
      tools.insertAdjacentHTML('afterend', `<div class="arsenal-secondary-tools" id="arsSecondaryTools">
        <select id="arsSort" class="arsenal-tool" aria-label="Sort weapons"><option value="name">Sort: Name A–Z</option><option value="rarity">Sort: Rarity high → low</option><option value="damage">Sort: Tier I · 1★ DMG high → low</option><option value="rpm">Sort: Fire Rate high → low</option></select>
        <button id="arsCraftable" type="button">⚒ Craftable</button>
        <button id="arsFavorites" type="button">★ Favorites</button>
        <button type="button" disabled title="Player inventory is not connected">◉ Owned — not connected</button>
        <button id="arsClear" type="button">× Clear Filters</button>
      </div>`);
    }
    if (!picker.querySelector('.arsenal-body')) {
      const body = document.createElement('div');
      body.className = 'arsenal-body';
      const center = document.createElement('div');
      center.className = 'arsenal-center';
      list.parentNode.insertBefore(body, list);
      center.appendChild(list);
      body.appendChild(center);
    }
    if (!document.getElementById('arsFooter')) {
      picker.insertAdjacentHTML('beforeend', `<div class="arsenal-footer" id="arsFooter">
        <span id="arsResultCount">0 weapons</span>
        <div class="arsenal-page-controls" id="arsPages"></div>
        <span class="arsenal-page-size">10 per page</span>
        <span class="arsenal-footer-spacer"></span>
        <button class="arsenal-cancel" id="arsCancel" type="button">Cancel</button>
        <button class="arsenal-confirm" id="arsConfirm" type="button" disabled>Confirm Selection (0)</button>
      </div>`);
    }
  }

  function enrichCard(card, weapon) {
    if (!weapon) return;
    if (card.dataset.dsRichFor === weapon.canonical_id && card.querySelector('.arsenal-description') && card.querySelector('.arsenal-skill')) return;
    card.dataset.dsRichFor = weapon.canonical_id;
    card.dataset.weaponName = weapon.name;
    card.classList.add('arsenal-card', rarityClass(weapon));
    const stats = statsFor(weapon);
    const description = weaponDescription(weapon);
    const skill = specialSkill(weapon);
    const acq = acquisition(weapon);
    const image = imageUrl(weapon);
    const fav = favorites().has(weapon.canonical_id);
    card.innerHTML = `
      <span class="arsenal-check" aria-hidden="true"></span>
      <span class="arsenal-favorite ${fav ? 'active' : ''}" data-ars-favorite="${esc(weapon.canonical_id)}" title="Favorite" aria-label="Favorite">★</span>
      <span class="arsenal-art">${image ? `<img src="${esc(image)}" alt="${esc(weapon.name)}" loading="lazy" decoding="async">` : `<span><b>${esc((weapon.category || 'WP').slice(0, 3).toUpperCase())}</b><small>IMAGE PENDING</small></span>`}</span>
      <span class="arsenal-copy">
        <span class="arsenal-title"><strong>${esc(weapon.name)}</strong></span>
        <span class="arsenal-chips"><i>${esc(weapon.rarity || 'Unverified')}</i><i>${esc(weapon.category || 'Type unresolved')}</i><i>Tier I · 1★</i></span>
        <span class="arsenal-description ${description.verified ? '' : 'unavailable'}"><span class="arsenal-section-label">WEAPON DESCRIPTION</span><span class="arsenal-description-copy">${esc(description.text)}</span></span>
        <span class="arsenal-skill ${skill.state}"><span class="arsenal-skill-head"><span class="arsenal-section-label">SPECIAL SKILL</span><span class="arsenal-skill-state">${esc(skill.label)}</span></span><span class="arsenal-skill-copy">${esc(skill.text)}</span></span>
        <span class="arsenal-stats"><span><small>DMG</small><b>${esc(damageFor(weapon))}</b></span><span><small>FIRE RATE</small><b>${esc(num(stats?.rpm ?? stats?.fire_rate))}</b></span><span><small>RANGE</small><b>${esc(rangeFor(weapon))}</b></span></span>
        <span class="arsenal-evidence"><strong>ACQUISITION</strong><span>${esc(acq.label)}</span><small>${esc(acq.detail)}</small><b class="evidence-state">${esc(evidenceLabel(weapon))}</b></span>
      </span>`;
  }

  function filterAndSortCards() {
    const list = document.getElementById('pickerList');
    if (!list) return [];
    const map = weaponMap();
    const query = String(document.getElementById('pickerSearch')?.value || '').trim().toLowerCase();
    const type = String(document.getElementById('pickerFilter')?.value || '');
    const rarity = String(document.getElementById('arsRarity')?.value || '');
    const acqFilter = String(document.getElementById('arsAcquisition')?.value || '');
    const mechanicFilter = String(document.getElementById('arsMechanic')?.value || '');
    const craftableOnly = document.getElementById('arsCraftable')?.classList.contains('active');
    const favoriteOnly = document.getElementById('arsFavorites')?.classList.contains('active');
    const favs = favorites();
    const items = [];
    [...list.querySelectorAll(':scope > .bl-pick')].forEach((card) => {
      const name = cardName(card);
      const weapon = map.get(name);
      if (!weapon) { card.hidden = true; return; }
      card.dataset.weaponName = weapon.name;
      const description = weaponDescription(weapon).text;
      const skill = specialSkill(weapon);
      const acq = acquisition(weapon);
      const haystack = `${weapon.name} ${weapon.category} ${weapon.rarity} ${description} ${skill.text} ${acq.label} ${acq.detail}`.toLowerCase();
      const rawStatus = effectText(weapon) ? 'resolved' : effectStatus(weapon) || 'review';
      const show = (!query || haystack.includes(query))
        && (!type || weapon.category === type)
        && (!rarity || weapon.rarity === rarity)
        && (!acqFilter || acq.state === acqFilter)
        && (!mechanicFilter || rawStatus === mechanicFilter)
        && (!craftableOnly || acq.state === 'craftable')
        && (!favoriteOnly || favs.has(weapon.canonical_id));
      card.hidden = !show;
      if (show) items.push({ card, weapon });
    });
    const sort = document.getElementById('arsSort')?.value || 'name';
    items.sort((a, b) => {
      if (sort === 'rarity') return (RARITY_RANK[b.weapon.rarity] || 0) - (RARITY_RANK[a.weapon.rarity] || 0) || a.weapon.name.localeCompare(b.weapon.name);
      if (sort === 'damage') return (Number(tierOne(b.weapon)?.base_attack) || 0) - (Number(tierOne(a.weapon)?.base_attack) || 0) || a.weapon.name.localeCompare(b.weapon.name);
      if (sort === 'rpm') return (Number(statsFor(b.weapon)?.rpm ?? statsFor(b.weapon)?.fire_rate) || 0) - (Number(statsFor(a.weapon)?.rpm ?? statsFor(a.weapon)?.fire_rate) || 0) || a.weapon.name.localeCompare(b.weapon.name);
      return a.weapon.name.localeCompare(b.weapon.name);
    });
    return items;
  }

  function renderPages(pageCount) {
    const host = document.getElementById('arsPages');
    if (!host) return;
    const page = selector.page;
    const buttons = [];
    buttons.push(`<button type="button" data-ars-page="${Math.max(1, page - 1)}" ${page <= 1 ? 'disabled' : ''} aria-label="Previous page">‹</button>`);
    const pages = new Set([1, page - 1, page, page + 1, pageCount].filter((value) => value >= 1 && value <= pageCount));
    let previous = 0;
    [...pages].sort((a, b) => a - b).forEach((value) => {
      if (previous && value - previous > 1) buttons.push('<span aria-hidden="true">…</span>');
      buttons.push(`<button type="button" data-ars-page="${value}" class="${value === page ? 'active' : ''}" aria-current="${value === page ? 'page' : 'false'}">${value}</button>`);
      previous = value;
    });
    buttons.push(`<button type="button" data-ars-page="${Math.min(pageCount, page + 1)}" ${page >= pageCount ? 'disabled' : ''} aria-label="Next page">›</button>`);
    host.innerHTML = buttons.join('');
  }

  function updatePendingUi() {
    document.querySelectorAll('#pickerList > .bl-pick').forEach((card) => card.classList.toggle('arsenal-selected', card === selector.pendingButton));
    const confirm = document.getElementById('arsConfirm');
    if (confirm) {
      confirm.disabled = !selector.pendingButton;
      confirm.textContent = `Confirm Selection (${selector.pendingButton ? 1 : 0})`;
    }
  }

  function renderArsenal({ resetPage = false } = {}) {
    if (!selector.active || document.getElementById('pickerTitle')?.textContent !== 'Weapon') return;
    if (resetPage) selector.page = 1;
    const items = filterAndSortCards();
    const pageCount = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
    selector.page = Math.min(Math.max(1, selector.page), pageCount);
    const start = (selector.page - 1) * PAGE_SIZE;
    const end = Math.min(items.length, start + PAGE_SIZE);
    const visible = new Set(items.slice(start, end).map(({ card }) => card));
    items.forEach(({ card, weapon }, index) => {
      card.style.order = String(index);
      card.hidden = !visible.has(card);
      if (visible.has(card)) enrichCard(card, weapon);
    });
    const count = document.getElementById('arsResultCount');
    if (count) count.textContent = items.length ? `${start + 1}–${end} of ${items.length} weapons` : '0 weapons';
    renderPages(pageCount);
    updatePendingUi();
  }

  function resetFilters() {
    const search = document.getElementById('pickerSearch');
    const type = document.getElementById('pickerFilter');
    const rarity = document.getElementById('arsRarity');
    const acq = document.getElementById('arsAcquisition');
    const mechanic = document.getElementById('arsMechanic');
    const sort = document.getElementById('arsSort');
    if (search) search.value = '';
    if (type) type.value = '';
    if (rarity) rarity.value = '';
    if (acq) acq.value = '';
    if (mechanic) mechanic.value = '';
    if (sort) sort.value = 'name';
    document.getElementById('arsCraftable')?.classList.remove('active');
    document.getElementById('arsFavorites')?.classList.remove('active');
    selector.pendingButton = null;
    renderArsenal({ resetPage: true });
  }

  function activateWeaponPicker() {
    const picker = document.getElementById('picker');
    if (!picker?.open || document.getElementById('pickerTitle')?.textContent !== 'Weapon') return;
    selector.active = true;
    selector.page = 1;
    selector.pendingButton = null;
    buildSelectorControls();
    renderArsenal({ resetPage: true });
  }

  function deactivateWeaponPicker() {
    selector.active = false;
    selector.pendingButton = null;
    const picker=document.getElementById('picker');
    picker?.classList.remove('arsenal-mode');
    ['arsRarity','arsAcquisition','arsMechanic'].forEach((id) => { const node=document.getElementById(id); if(node) node.hidden=true; });
    const secondary=document.getElementById('arsSecondaryTools'); if(secondary) secondary.hidden=true;
    const footer=document.getElementById('arsFooter'); if(footer) footer.hidden=true;
    picker?.querySelector('.arsenal-subtitle')?.remove();
  }

  function bindSelector() {
    if (selector.installed) return;
    selector.installed = true;
    const picker = document.getElementById('picker');
    const list = document.getElementById('pickerList');
    const title = document.getElementById('pickerTitle');
    if (!picker || !list || !title) return;

    const scheduleActivation = () => queueMicrotask(() => {
      if (picker.open && title.textContent === 'Weapon') activateWeaponPicker();
      else if (!picker.open) deactivateWeaponPicker();
    });
    new MutationObserver(scheduleActivation).observe(picker, { attributes: true, attributeFilter: ['open'] });
    new MutationObserver(scheduleActivation).observe(title, { childList: true, subtree: true });
    selector.listObserver = new MutationObserver((mutations) => {
      if (!selector.active) return;
      if (mutations.some((mutation) => mutation.target === list && mutation.type === 'childList')) queueMicrotask(() => renderArsenal());
    });
    selector.listObserver.observe(list, { childList: true });

    list.addEventListener('click', (event) => {
      if (!selector.active || selector.allowBaseSelection) return;
      const favorite = event.target.closest('[data-ars-favorite]');
      if (favorite) {
        event.preventDefault();
        event.stopImmediatePropagation();
        const set = favorites();
        const id = favorite.dataset.arsFavorite;
        set.has(id) ? set.delete(id) : set.add(id);
        storeFavorites(set);
        favorite.classList.toggle('active', set.has(id));
        if (document.getElementById('arsFavorites')?.classList.contains('active')) renderArsenal({ resetPage: true });
        return;
      }
      const card = event.target.closest('.bl-pick');
      if (!card) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      selector.pendingButton = card;
      updatePendingUi();
    }, true);

    document.addEventListener('input', (event) => {
      if (!selector.active) return;
      if (event.target?.id === 'pickerSearch') queueMicrotask(() => renderArsenal({ resetPage: true }));
    });
    document.addEventListener('change', (event) => {
      if (!selector.active) return;
      if (['pickerFilter', 'arsRarity', 'arsAcquisition', 'arsMechanic', 'arsSort'].includes(event.target?.id)) queueMicrotask(() => renderArsenal({ resetPage: true }));
    });
    document.addEventListener('click', (event) => {
      if (!selector.active) return;
      const pageButton = event.target.closest('[data-ars-page]');
      if (pageButton && !pageButton.disabled) {
        selector.page = Number(pageButton.dataset.arsPage) || 1;
        renderArsenal();
        document.getElementById('pickerList')?.scrollTo({ top: 0, behavior: 'auto' });
        return;
      }
      if (event.target.closest('#arsCraftable')) {
        event.target.closest('#arsCraftable').classList.toggle('active');
        renderArsenal({ resetPage: true });
        return;
      }
      if (event.target.closest('#arsFavorites')) {
        event.target.closest('#arsFavorites').classList.toggle('active');
        renderArsenal({ resetPage: true });
        return;
      }
      if (event.target.closest('#arsClear')) { resetFilters(); return; }
      if (event.target.closest('#arsCancel')) { picker.close(); return; }
      if (event.target.closest('#arsConfirm')) {
        if (!selector.pendingButton) return;
        selector.allowBaseSelection = true;
        selector.pendingButton.click();
        selector.allowBaseSelection = false;
      }
    });
  }

  function boot() {
    installStyle();
    installPlannerEnhancements();
    bindSelector();
    setTimeout(() => {
      syncSummaryHealth();
      enhancePlannerWeaponArt();
      if (document.getElementById('picker')?.open && document.getElementById('pickerTitle')?.textContent === 'Weapon') activateWeaponPicker();
    }, 0);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
