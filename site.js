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

function formatNewsDate(value) {
  if (!value) return 'Date pending';
  const date = new Date(`${value}T12:00:00Z`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(date);
}

function renderOfficialNews(payload) {
  const container = document.getElementById('officialNewsFeed');
  const updated = document.getElementById('officialNewsUpdated');
  if (!container) return;

  const articles = Array.isArray(payload?.articles) ? payload.articles.slice(0, 5) : [];
  if (!articles.length) throw new Error('No official news records available');

  container.replaceChildren();
  articles.forEach((article, index) => {
    const item = document.createElement('article');
    item.className = 'official-news-item';
    item.style.setProperty('--news-delay', `${index * 45}ms`);

    const meta = document.createElement('div');
    meta.className = 'official-news-item-meta';
    const category = document.createElement('span');
    category.textContent = article.category || 'Official news';
    const date = document.createElement('time');
    date.dateTime = article.date || '';
    date.textContent = formatNewsDate(article.date);
    meta.append(category, date);

    const title = document.createElement('h3');
    title.textContent = article.title || 'Untitled Once Human update';

    item.append(meta, title);
    container.append(item);
  });

  if (updated && payload?.updated_at) {
    const stamp = new Date(payload.updated_at);
    updated.textContent = Number.isNaN(stamp.getTime()) ? 'Cached official feed' : `Feed checked ${stamp.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}`;
  }
}

async function initOfficialNews() {
  const container = document.getElementById('officialNewsFeed');
  if (!container) return;

  const cacheSlot = Math.floor(Date.now() / 900000);
  const sources = [
    `https://raw.githubusercontent.com/raiinman/dead-signal/main/data/official-news.json?v=${cacheSlot}`,
    `data/official-news.json?v=${cacheSlot}`,
  ];

  for (const source of sources) {
    try {
      const response = await fetch(source, { cache: 'no-store' });
      if (!response.ok) throw new Error(`Feed request failed: ${response.status}`);
      renderOfficialNews(await response.json());
      return;
    } catch (_) {}
  }

  container.innerHTML = '<div class="official-news-error"><strong>OFFICIAL FEED TEMPORARILY UNAVAILABLE</strong><span>Dead Signal will retry on the next visit.</span></div>';
}

initOfficialNews();
