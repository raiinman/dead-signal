document.getElementById('year').textContent = new Date().getFullYear();

const query = document.getElementById('databaseQuery');
const cards = [...document.querySelectorAll('.category')];
const status = document.getElementById('searchStatus');
const empty = document.getElementById('noResults');

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
document.addEventListener('keydown', (event) => {
  if (event.key === '/' && document.activeElement !== query) {
    event.preventDefault();
    query.focus();
  }
});
