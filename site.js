document.getElementById('year').textContent = new Date().getFullYear();

const query = document.getElementById('databaseQuery');
const cards = [...document.querySelectorAll('.landing-category, .category')];
const status = document.getElementById('searchStatus');
const empty = document.getElementById('noResults');
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

function applySearchDatabase() {
  const term = query.value.trim().toLowerCase();
  let visible = 0;

  cards.forEach((card) => {
    const matches = !term || `${card.textContent} ${card.dataset.search || ''}`.toLowerCase().includes(term);
    card.classList.toggle('filtered-out', !matches);
    if (matches) visible += 1;
  });

  empty.hidden = visible !== 0;
  status.hidden = !term;
  status.textContent = term ? `${visible} database ${visible === 1 ? 'system' : 'systems'} match “${query.value.trim()}”.` : '';
}

function searchDatabase() {
  if (!document.startViewTransition || reduceMotion.matches) {
    applySearchDatabase();
    return;
  }

  document.startViewTransition(applySearchDatabase);
}

query.addEventListener('input', searchDatabase);
query.addEventListener('keydown', (event) => {
  if (event.key !== 'Enter') return;
  document.getElementById('database')?.scrollIntoView({ behavior: reduceMotion.matches ? 'auto' : 'smooth', block: 'start' });
});

document.addEventListener('keydown', (event) => {
  const active = document.activeElement;
  const typing = active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.isContentEditable);

  if (event.key === '/' && !typing) {
    event.preventDefault();
    query.focus();
  }
});
