/* PromptmaX Theme Toggle — Vanilla JS */
(function () {
  var KEY = 'promptmax-theme';

  function getTheme() {
    return document.documentElement.getAttribute('data-theme') || 'light';
  }

  function setTheme(mode) {
    document.documentElement.setAttribute('data-theme', mode);
    localStorage.setItem(KEY, mode);
    updateIcon(mode);
    updateMetaColor(mode);
  }

  function toggle() {
    setTheme(getTheme() === 'dark' ? 'light' : 'dark');
  }

  function updateIcon(mode) {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    var icon = btn.querySelector('[data-lucide]');
    if (icon) {
      icon.setAttribute('data-lucide', mode === 'dark' ? 'sun' : 'moon');
      if (window.lucide) lucide.createIcons({ nodes: [icon] });
    }
    btn.setAttribute('aria-label', mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
  }

  function updateMetaColor(mode) {
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.content = mode === 'dark' ? '#0F1A15' : '#f7f6e5';
    }
  }

  // Listen for OS-level preference changes (only when no manual preference saved)
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
    if (!localStorage.getItem(KEY)) {
      document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
      updateIcon(e.matches ? 'dark' : 'light');
      updateMetaColor(e.matches ? 'dark' : 'light');
    }
  });

  // Keyboard shortcut: Ctrl/Cmd + D
  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
      e.preventDefault();
      toggle();
    }
  });

  // Bind toggle button
  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', toggle);
      updateIcon(getTheme());
    }
  });

  // Expose API
  window.PromptMaxTheme = { toggle: toggle, getTheme: getTheme, setTheme: setTheme };
})();
