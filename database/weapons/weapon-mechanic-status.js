(() => {
  'use strict';

  const published = window.DS_WEAPONS_WEB;
  if (!published || !Array.isArray(published.weapons)) return;

  const byBlueprint = new Map(
    published.weapons.map((weapon) => [String(weapon?.blueprint_id ?? ''), weapon])
  );
  const byCanonical = new Map(
    published.weapons.map((weapon) => [String(weapon?.canonical_id ?? ''), weapon])
  );

  const contractForRequest = (value) => (
    byBlueprint.get(String(value ?? ''))
    || byCanonical.get(String(value ?? ''))
    || null
  );

  function mechanicMessage(weapon) {
    if (!weapon || weapon.effect) return '';
    const resolution = weapon.effect_resolution || {};
    const status = String(resolution.status || '').trim();
    const skill = String(resolution.fixed_skill_code || '').trim();

    if (status === 'no-fixed-skill-reference') {
      return 'Installed-game blueprint data contains no fixed weapon mechanic reference for this record.';
    }
    if (status === 'exact-fixed-skill-record-missing') {
      return skill
        ? `Mechanic unresolved — exact skill ${skill} is referenced, but that record is absent from the installed passive_skill_data.`
        : 'Mechanic unresolved — the exact fixed-skill record referenced by this weapon is absent from the installed passive_skill_data.';
    }
    if (status === 'fixed-skill-record-present-player-facing-text-unresolved') {
      return skill
        ? `Mechanic identity ${skill} is present, but its player-facing effect text is unresolved in the current installed-game evidence.`
        : 'The fixed weapon mechanic record is present, but its player-facing effect text is unresolved in the current installed-game evidence.';
    }
    return 'No player-facing weapon mechanic is resolved for this record in the current Miner projection.';
  }

  function patchCards() {
    document.querySelectorAll('.weapon-card').forEach((card) => {
      const detail = card.querySelector('a[href*="detail/?weapon="]');
      const preview = card.querySelector('.effect-preview');
      if (!detail || !preview) return;
      let requested = '';
      try {
        requested = new URL(detail.href, location.href).searchParams.get('weapon') || '';
      } catch (_) {
        return;
      }
      const weapon = contractForRequest(requested);
      if (!weapon || weapon.effect) return;
      preview.textContent = mechanicMessage(weapon);
      preview.dataset.mechanicStatus = String(weapon.effect_resolution?.status || 'unresolved');
    });

    document.querySelectorAll('.weapon-card dl dt').forEach((label) => {
      if (label.textContent.trim() === 'Base Attack') label.textContent = 'Tier I · 1★ DMG';
    });
  }

  function patchDetail() {
    const requested = new URLSearchParams(location.search).get('weapon') || document.body.dataset.detailId || '';
    const weapon = contractForRequest(requested);
    if (!weapon || weapon.effect) return;
    const section = [...document.querySelectorAll('#weaponDetail article')].find((article) => (
      article.querySelector('.section-code')?.textContent.includes('Weapon mechanic')
    ));
    if (!section) return;
    const heading = section.querySelector('h2');
    const body = section.querySelector('.full-effect');
    if (!body) return;

    const status = String(weapon.effect_resolution?.status || '').trim();
    const skill = String(weapon.effect_resolution?.fixed_skill_code || '').trim();
    if (heading) {
      if (status === 'no-fixed-skill-reference') heading.textContent = 'No fixed mechanic reference';
      else if (status === 'exact-fixed-skill-record-missing') heading.textContent = skill ? `Unresolved skill ${skill}` : 'Unresolved fixed skill';
      else if (status === 'fixed-skill-record-present-player-facing-text-unresolved') heading.textContent = skill ? `Unresolved text for ${skill}` : 'Mechanic text unresolved';
    }
    body.textContent = mechanicMessage(weapon);
    body.dataset.mechanicStatus = status || 'unresolved';
  }

  function patch(attempt = 0) {
    patchCards();
    patchDetail();
    const browseReady = document.body.dataset.catalogueView !== 'browse' || document.querySelector('.weapon-card');
    const detailReady = document.body.dataset.catalogueView !== 'detail' || document.querySelector('#weaponDetail .full-effect');
    if ((!browseReady || !detailReady) && attempt < 30) setTimeout(() => patch(attempt + 1), 50);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => patch(), { once: true });
  } else {
    patch();
  }
})();
