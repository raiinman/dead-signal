document.getElementById('year').textContent = new Date().getFullYear();

const query = document.getElementById('databaseQuery');
const cards = [...document.querySelectorAll('.landing-category, .category')];
const status = document.getElementById('searchStatus');
const empty = document.getElementById('noResults');
const mirror = document.querySelector('[data-search-mirror]');
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

function applySearchDatabase() {
  const term = query.value.trim().toLowerCase();
  let visible = 0;
  cards.forEach((card) => {
    const matches = !term || `${card.textContent} ${card.dataset.search}`.toLowerCase().includes(term);
    card.classList.toggle('filtered-out', !matches);
    if (matches) visible += 1;
  });
  empty.hidden = visible !== 0;
  status.textContent = term ? `${visible} database ${visible === 1 ? 'category' : 'categories'} match “${query.value.trim()}”.` : 'Search across the current player-facing database.';
}

function searchDatabase() {
  if (!document.startViewTransition || reduceMotion.matches) {
    applySearchDatabase();
    return;
  }
  document.startViewTransition(applySearchDatabase);
}

query.addEventListener('input', searchDatabase);
mirror?.addEventListener('input', () => {
  query.value = mirror.value;
  searchDatabase();
});
mirror?.addEventListener('keydown', (event) => {
  if (event.key !== 'Enter') return;
  document.getElementById('database')?.scrollIntoView({ behavior: 'smooth' });
  query.focus();
});
document.addEventListener('keydown', (event) => {
  if (event.key === '/' && document.activeElement !== query) {
    event.preventDefault();
    query.focus();
  }
});

function initOfficialFeed() {
  const timeline = document.querySelector('.twitter-timeline');
  if (!timeline) return;

  const container = timeline.parentElement;
  timeline.href = 'https://x.com/OnceHuman_';
  timeline.dataset.dnt = 'true';

  const renderTimeline = () => {
    try {
      window.twttr?.widgets?.load?.(container);
    } catch (_) {}
  };

  if (window.twttr?.widgets?.load) {
    renderTimeline();
  } else {
    let script = document.getElementById('ds-x-widgets');
    if (!script) {
      script = document.createElement('script');
      script.id = 'ds-x-widgets';
      script.src = 'https://platform.x.com/widgets.js';
      script.async = true;
      script.charset = 'utf-8';
      document.body.append(script);
    }
    script.addEventListener('load', renderTimeline, { once: true });
  }

  setTimeout(() => {
    if (container.querySelector('iframe')) return;
    timeline.textContent = 'Official X feed could not load in this browser. Open @OnceHuman_ on X.';
    timeline.setAttribute('aria-label', 'Open the official Once Human account on X');
  }, 8000);
}

initOfficialFeed();
