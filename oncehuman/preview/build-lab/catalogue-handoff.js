(() => {
  'use strict';

  const params = new URLSearchParams(location.search);
  const weaponId = params.get('catalogue-weapon');
  const weaponName = params.get('catalogue-name');
  const requestedTier = Number(params.get('catalogue-tier'));
  const requestedStars = Number(params.get('catalogue-stars'));
  if (!weaponId && !weaponName) return;

  const slot = ['primary', 'secondary', 'melee'].includes(params.get('catalogue-slot'))
    ? params.get('catalogue-slot')
    : 'primary';
  const normalize = (value) => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const weapon = (window.DS_WEAPON_DATA || []).find((item) => String(item.id) === weaponId)
    || (window.DS_WEAPON_DATA || []).find((item) => normalize(item.name) === normalize(weaponName));
  if (!weapon) return;

  function applyConfiguration() {
    const card = [...document.querySelectorAll('.weapon-card')]
      .find((item) => normalize(item.querySelector('.item-name')?.textContent) === normalize(weapon.name));
    if (!card) return false;
    const tier = card.querySelector('[data-wm-tier], [data-weapon-tier]');
    if (tier && Number.isInteger(requestedTier) && [...tier.options].some((option) => Number(option.value) === requestedTier)) {
      tier.value = String(requestedTier);
      tier.dispatchEvent(new Event('change', { bubbles: true }));
    }
    setTimeout(() => {
      const stars = card.querySelector('[data-wm-star], [data-weapon-stars]');
      if (stars && Number.isInteger(requestedStars) && [...stars.options].some((option) => Number(option.value) === requestedStars)) {
        stars.value = String(requestedStars);
        stars.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }, 0);
    return true;
  }

  function watchConfiguration() {
    if (applyConfiguration()) return;
    const observer = new MutationObserver(() => {
      if (applyConfiguration()) observer.disconnect();
    });
    observer.observe(document.getElementById('weapons') || document.body, { childList: true, subtree: true });
    setTimeout(() => observer.disconnect(), 120000);
  }

  function openFilteredPicker(attempt = 0) {
    const trigger = document.querySelector(`[data-pick="weapon"][data-slot="${slot}"]`);
    const picker = document.getElementById('picker');
    const search = document.getElementById('pickerSearch');
    if ((!trigger || !picker || !search) && attempt < 20) {
      setTimeout(() => openFilteredPicker(attempt + 1), 100);
      return;
    }
    if (!trigger || !picker || !search) return;

    trigger.click();
    search.value = weapon.name;
    search.dispatchEvent(new Event('input', { bubbles: true }));
    watchConfiguration();
    const cleanUrl = new URL(location.href);
    cleanUrl.searchParams.delete('catalogue-weapon');
    cleanUrl.searchParams.delete('catalogue-slot');
    cleanUrl.searchParams.delete('catalogue-name');
    cleanUrl.searchParams.delete('catalogue-tier');
    cleanUrl.searchParams.delete('catalogue-stars');
    history.replaceState(null, '', `${cleanUrl.pathname}${cleanUrl.search}#weapons`);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => openFilteredPicker(), { once: true });
  } else {
    openFilteredPicker();
  }
})();
