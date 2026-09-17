/** Tab panels (works with AtlasI18n). */
(function () {
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

  document.addEventListener("DOMContentLoaded", initTabs);
})();
