document.getElementById('year').textContent = new Date().getFullYear();

const query = document.getElementById('databaseQuery');
const cards = [...document.querySelectorAll('.landing-category, .category')];
const status = document.getElementById('searchStatus');
const empty = document.getElementById('noResults');
const mirror = document.querySelector('[data-search-mirror]');

function searchDatabase() {
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
