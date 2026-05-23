/**
 * theme.js — Dark/light mode + TTS + Bookmark utilities
 * Import this in any page to get persistent dark mode.
 */

export function initTheme() {
  const saved = localStorage.getItem('episodic_dark_mode');
  if (saved === 'dark') {
    document.documentElement.classList.add('dark');
  }
}

export function toggleDarkMode() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('episodic_dark_mode', isDark ? 'dark' : 'light');
  // Update all dark mode buttons on this page
  document.querySelectorAll('[data-dark-toggle]').forEach(btn => updateDarkBtn(btn, isDark));
}

export function updateDarkBtn(btn, isDark) {
  if (!btn) return;
  const icon = btn.querySelector('.material-symbols-outlined');
  if (icon) icon.textContent = isDark ? 'light_mode' : 'dark_mode';
  btn.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
  btn.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
}

// Run immediately when imported
initTheme();
