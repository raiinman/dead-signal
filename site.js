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

  const frame = document.createElement('iframe');
  frame.className = 'official-x-frame';
  frame.title = 'Official Once Human posts on X';
  frame.loading = 'eager';
  frame.referrerPolicy = 'strict-origin-when-cross-origin';
  frame.setAttribute('scrolling', 'yes');
  frame.style.cssText = 'display:block;width:100%;height:100%;border:0;background:#07090b';
  frame.srcdoc = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<style>
html,body{margin:0;min-height:100%;background:#07090b;color:#d9e1e5;font-family:Inter,"Segoe UI",system-ui,sans-serif}body{overflow-x:hidden}.twitter-timeline{display:grid;place-items:center;min-height:340px;padding:24px;color:#58c7cc;text-align:center;text-decoration:none;font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;box-sizing:border-box}iframe{display:block!important;width:100%!important;max-width:100%!important;margin:0!important;border:0!important}.feed-status{display:none;min-height:340px;place-content:center;padding:28px;box-sizing:border-box;text-align:center;color:#7f8b92;font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase}.feed-status strong{display:block;margin-bottom:8px;color:#ef5b64}.feed-status a{color:#58c7cc}
</style>
</head>
<body>
<a class="twitter-timeline" data-height="360" data-theme="dark" href="https://x.com/OnceHuman_">Tweets by OnceHuman_</a>
<div class="feed-status" id="feedStatus"><div><strong>X timeline did not initialize</strong><span>The current X embed service did not render the timeline. </span><a href="https://x.com/OnceHuman_" target="_blank" rel="noopener noreferrer">Open @OnceHuman_ on X</a></div></div>
<script async src="https://platform.x.com/widgets.js" charset="utf-8"><\/script>
<script>window.setTimeout(function(){var rendered=document.querySelector('iframe.twitter-timeline-rendered,iframe[id^="twitter-widget-"]');if(rendered)return;var a=document.querySelector('a.twitter-timeline'),s=document.getElementById('feedStatus');if(a)a.style.display='none';if(s)s.style.display='grid'},8000)<\/script>
</body>
</html>`;

  body.replaceChildren(frame);
}

initOfficialXFrame();
