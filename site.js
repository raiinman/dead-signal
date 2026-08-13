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

function initOfficialXFrame() {
  const body = document.querySelector('.official-feed-body');
  if (!body) return;

  document.querySelectorAll('script[src*="platform.twitter.com/widgets.js"], script[src*="platform.x.com/widgets.js"]').forEach((script) => script.remove());

  const frame = document.createElement('iframe');
  frame.className = 'official-x-frame';
  frame.title = 'Official Once Human posts on X';
  frame.loading = 'eager';
  frame.referrerPolicy = 'same-origin';
  frame.setAttribute('scrolling', 'yes');
  frame.style.cssText = 'display:block;width:100%;height:100%;border:0;background:#07090b';
  frame.src = '/api/twitter/cache/';

  body.replaceChildren(frame);
}

initOfficialXFrame();
