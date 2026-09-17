(function () {
  const THEME_KEY = "atlas_site_theme";

  function applyTheme(mode) {
    const root = document.documentElement;
    if (mode === "auto") {
      delete root.dataset.theme;
    } else {
      root.dataset.theme = mode;
    }
    document.querySelectorAll(".theme-toggle button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.theme === mode);
    });
  }

  function setTheme(mode) {
    try {
      localStorage.setItem(THEME_KEY, mode);
    } catch (e) {}
    applyTheme(mode);
  }

  function initTheme() {
    let mode = "auto";
    try {
      mode = localStorage.getItem(THEME_KEY) || "auto";
    } catch (e) {}
    applyTheme(mode);
    document.querySelectorAll(".theme-toggle button").forEach((btn) => {
      btn.addEventListener("click", () => setTheme(btn.dataset.theme || "auto"));
    });
  }

  function initTabs() {
    const tabs = document.querySelectorAll(".page-tab");
    const panels = document.querySelectorAll(".tab-panel");
    if (!tabs.length) return;

    function show(tabId) {
      tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === tabId));
      panels.forEach((panel) => panel.classList.toggle("active", panel.id === "panel-" + tabId));
    }

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => show(tab.dataset.tab || "projects"));
    });

    const hash = (location.hash || "").replace("#", "");
    if (hash && document.getElementById("panel-" + hash)) {
      show(hash);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initTabs();
  });
})();
