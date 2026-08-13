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

function initTwitterDiagnostic() {
  const params = new URLSearchParams(location.search);
  if (params.get('twitter-debug') !== '1') return;

  const body = document.querySelector('.official-feed-body');
  const title = document.getElementById('official-feed-title');
  const meta = document.querySelector('.official-feed-meta');
  if (!body) return;

  title.textContent = 'X Embed A/B Test';
  body.style.height = '520px';
  body.style.overflow = 'auto';
  body.innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(2,minmax(280px,1fr));gap:12px;padding:12px;min-width:600px">
      <section style="min-width:0;border:1px solid #293238;background:#07090b">
        <div style="padding:9px 10px;border-bottom:1px solid #293238;color:#58c7cc;font:800 11px/1.2 system-ui;text-transform:uppercase;letter-spacing:.08em">Control — @lightdotgg</div>
        <a class="twitter-timeline" data-height="430" data-theme="dark" href="https://twitter.com/lightdotgg?ref_src=twsrc%5Etfw">Tweets by lightdotgg</a>
      </section>
      <section style="min-width:0;border:1px solid #293238;background:#07090b">
        <div style="padding:9px 10px;border-bottom:1px solid #293238;color:#e6323e;font:800 11px/1.2 system-ui;text-transform:uppercase;letter-spacing:.08em">Target — @OnceHuman_</div>
        <a class="twitter-timeline" data-height="430" data-theme="dark" href="https://twitter.com/OnceHuman_?ref_src=twsrc%5Etfw">Tweets by OnceHuman_</a>
      </section>
    </div>`;
  if (meta) meta.innerHTML = '<span>Diagnostic mode</span><span>Same domain · same widget · different account</span>';

  const render = () => {
    try { window.twttr?.widgets?.load?.(body); } catch (_) {}
  };

  if (window.twttr?.widgets?.load) {
    render();
    return;
  }

  let script = document.querySelector('script[src*="platform.twitter.com/widgets.js"],script[src*="platform.x.com/widgets.js"]');
  if (!script) {
    script = document.createElement('script');
    script.src = 'https://platform.twitter.com/widgets.js';
    script.async = true;
    script.charset = 'utf-8';
    document.body.append(script);
  }
  script.addEventListener('load', render, { once: true });
}

initTwitterDiagnostic();
