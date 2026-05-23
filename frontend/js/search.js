// Search modal — import this in any page that has a search button
import api from './api.js';

const MODAL_HTML = `
<div id="search-modal" class="fixed inset-0 z-[100] flex items-start justify-center pt-24 px-4" style="display:none!important">
  <div id="search-backdrop" class="absolute inset-0 bg-on-background/50 backdrop-blur-sm"></div>
  <div class="relative w-full max-w-2xl bg-surface rounded-2xl shadow-2xl border border-outline-variant/30 overflow-hidden">
    <!-- Search input -->
    <div class="flex items-center gap-4 p-6 border-b border-outline-variant/20">
      <span class="material-symbols-outlined text-primary">search</span>
      <input
        id="search-input"
        type="text"
        placeholder="Search stories, poems, essays…"
        autocomplete="off"
        class="flex-1 bg-transparent text-on-surface font-body-lg text-body-lg placeholder:text-on-surface-variant/50 focus:outline-none"
      />
      <button id="search-close" class="material-symbols-outlined text-on-surface-variant hover:text-primary transition-colors">close</button>
    </div>
    <!-- Results -->
    <div id="search-results" class="max-h-[60vh] overflow-y-auto divide-y divide-outline-variant/10">
      <p id="search-hint" class="p-6 text-on-surface-variant font-body-md text-center">Start typing to search stories…</p>
    </div>
  </div>
</div>`;

function renderResults(articles, query) {
  const el = document.getElementById('search-results');
  if (!articles.length) {
    el.innerHTML = `<p class="p-6 text-on-surface-variant font-body-md text-center">No results for "<strong>${query}</strong>"</p>`;
    return;
  }
  el.innerHTML = articles.map(a => {
    const cat = a.category || 'essay';
    const catIcons = { essay:'article', poetry:'auto_stories', op_ed:'diversity_3', interview:'mic', visual_art:'palette' };
    const icon = catIcons[cat] || 'auto_awesome';
    return `
      <a href="./article.html?slug=${encodeURIComponent(a.slug)}" class="flex items-start gap-4 p-5 hover:bg-surface-container-low transition-colors group">
        <span class="material-symbols-outlined text-primary mt-0.5">${icon}</span>
        <div class="flex-1 min-w-0">
          <p class="font-headline-md text-headline-md text-on-surface group-hover:text-primary transition-colors truncate">${a.title}</p>
          <p class="text-caption font-caption text-outline mt-1">${(cat).replace('_',' ')} · Anonymous</p>
        </div>
        <span class="material-symbols-outlined text-on-surface-variant opacity-0 group-hover:opacity-100 transition-opacity mt-0.5">arrow_forward</span>
      </a>`;
  }).join('');
}

let allArticles = [];
let debounceTimer = null;

async function prefetch() {
  try {
    const data = await api.articles.list();
    allArticles = (data && data.items) ? data.items : [];
  } catch (_) {}
}

function openModal() {
  const modal = document.getElementById('search-modal');
  modal.style.removeProperty('display');
  modal.style.display = 'flex';
  document.getElementById('search-input').focus();
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  const modal = document.getElementById('search-modal');
  modal.style.display = 'none';
  document.getElementById('search-input').value = '';
  document.getElementById('search-results').innerHTML =
    '<p id="search-hint" class="p-6 text-on-surface-variant font-body-md text-center">Start typing to search stories…</p>';
  document.body.style.overflow = '';
}

function search(query) {
  const q = query.toLowerCase().trim();
  if (!q) {
    document.getElementById('search-results').innerHTML =
      '<p class="p-6 text-on-surface-variant font-body-md text-center">Start typing to search stories…</p>';
    return;
  }
  const results = allArticles.filter(a =>
    (a.title || '').toLowerCase().includes(q) ||
    (a.category || '').toLowerCase().includes(q) ||
    (a.summary || '').toLowerCase().includes(q) ||
    (a.tags || []).some(t => (t.name || t).toLowerCase().includes(q))
  );
  renderResults(results, query);
}

export function initSearch() {
  // Inject modal HTML
  document.body.insertAdjacentHTML('beforeend', MODAL_HTML);

  // Wire close
  document.getElementById('search-close').addEventListener('click', closeModal);
  document.getElementById('search-backdrop').addEventListener('click', closeModal);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

  // Wire input
  document.getElementById('search-input').addEventListener('input', e => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => search(e.target.value), 200);
  });

  // Wire every search button on the page
  document.querySelectorAll('button.material-symbols-outlined, button[aria-label="search"]').forEach(btn => {
    if (btn.textContent.trim() === 'search') {
      btn.addEventListener('click', openModal);
    }
  });

  // Also support keyboard shortcut: Cmd/Ctrl + K
  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      openModal();
    }
  });

  // Prefetch articles in background
  prefetch();
}
