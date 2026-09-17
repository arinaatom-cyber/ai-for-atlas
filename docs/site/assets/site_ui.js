/** Theme + tab panels (works with AtlasI18n). */
(function () {
  const THEME_KEY = "atlas_site_theme";

  function getTheme() {
    return localStorage.getItem(THEME_KEY) || "light";
  }

  function setTheme(theme) {
    const t = theme === "dark" ? "dark" : "light";
    localStorage.setItem(THEME_KEY, t);
    document.documentElement.setAttribute("data-theme", t);
    document.querySelectorAll(".theme-toggle button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.theme === t);
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
    setTheme(getTheme());
    document.querySelectorAll(".theme-toggle button").forEach((btn) => {
      btn.addEventListener("click", () => setTheme(btn.dataset.theme));
    });
    initTabs();
  });

  window.AtlasUI = { setTheme, getTheme };
})();
