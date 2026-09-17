"""English fallback strings for static HTML (mirrors site_assets/i18n.js PAGE.en + SHARED)."""
from __future__ import annotations

BRAND_NAME = "Human Cancser Assosiated TMT Proteome Atlas"

_SHARED: dict[str, str] = {
    "brand_title": BRAND_NAME,
    "nav_ai": "AI search",
    "nav_atlas": "Atlas",
    "nav_discovery": "Discovery",
    "nav_cohorts": "Cohorts",
    "nav_qc": "QC",
    "meta_updated": "Updated",
    "badge_readonly": "read-only",
    "meta_candidates": "candidates",
    "meta_atlas_ids": "atlas IDs",
    "footer_github": "GitHub TMT",
    "footer_projects": "tmt-projects",
    "footer_live": "Live (GitHub Pages)",
    "filter_all": "All",
    "filter_pride": "PRIDE",
    "filter_pdc": "PDC",
    "filter_massive": "MassIVE",
    "filter_iprox": "iProX",
    "th_project_id_hint": "PXD · PDC · MSV · IPX",
    "card_open": "Open",
    "card_json": "latest.json (API)",
    "th_link_open": "Open",
    "cell_empty": "—",
}

_EN: dict[str, str] = {
    "brand_sub": "New TMT projects · atlas similarity",
    "nav_home": "Home",
    "nav_map": "Organ map",
    "footer_policy": (
        "Excel catalog is not published. Site shows new candidates, literature, and analysis only."
    ),
    "portal_title": BRAND_NAME,
    "portal_lead": (
        "Monitor human TMT in PRIDE, PDC, MassIVE, iProX · LLM abstract screening · "
        "large literature cohorts"
    ),
    "card_discovery_title": "Full Discovery analysis",
    "card_discovery_desc": "Unified table: new PXD/PDC · papers · cohorts · QC · data files",
    "card_qc_title": "QC report",
    "card_qc_desc": "Candidates / manual / rejected with LLM analysis and data column",
    "card_atlas_title": "Atlas profile",
    "card_atlas_desc": "Catalog stats: repositories, organs, diseases, TMT plexes",
    "card_cohorts_title": "Large cohorts",
    "card_cohorts_desc": "Proteomics & multi-omics: large patient cohorts, abstract text mining",
    "card_map_title": "Interactive map",
    "card_map_desc": "TMT projects by organ · deep links ?organ= · read-only catalog",
    "card_ai_title": "AI keyword search",
    "card_ai_desc": "Search PRIDE, PDC, Europe PMC by atlas profile · LLM abstract screening",
    "ai_title": "AI keyword search",
    "ai_lead": "Run repository + literature search with LLM scoring — same engine as the Discovery portal",
    "ai_how_title": "How to use",
    "ai_step1": "Open the live app (button above) — tab «AI search» is selected by default",
    "ai_step2": "Edit keywords or keep atlas profile defaults (organs, diseases, TMT)",
    "ai_step3": "Click Run search — steps 1–4: repositories → Europe PMC → filters → LLM",
    "ai_step4": "Review Repository IDs and Publications; add verified hits via run_revisor.py add --apply",
    "ai_launch_title": "Launch interactive search",
    "ai_launch_desc": "Full search runs in Streamlit (APIs + local LLM). Results are not auto-added to projects.csv.",
    "ai_launch_btn": "Open AI search app",
    "ai_view_discovery": "View last Discovery scan",
    "ai_keywords_title": "Default atlas keywords",
    "ai_keywords_desc": "Copied from catalog profile — paste into the app or edit before Run search",
    "ai_iframe_fallback": "If the embed is blank, use the button above (Streamlit may block iframes in some browsers).",
    "ai_badge_live": "Live app",
    "map_title": "Human body organ map",
    "map_lead": "Interactive TMT catalog by organ — click regions, filter projects, open PRIDE/PDC links",
    "map_how_title": "How to use",
    "map_step1": "Click an organ on the silhouette or use quick links below",
    "map_step2": "Browse projects for that tissue — open repository or PubMed from the sidebar",
    "map_step3": "Share deep links: add ?organ=gastric (or other organ key) to the map URL",
    "map_open_full": "Open full-screen map",
    "map_embed_hint": "Embedded from GitHub Pages TMT — scroll inside the frame if needed",
    "map_organs_title": "Quick organ links",
    "card_update_title": "Update data",
    "card_update_desc": "Run: python run_discovery.py scan · publish · export for GitHub Pages",
    "disc_title": "New projects",
    "disc_lead": (
        "Candidates not in catalog: ID, PMID, description, PRIDE/PDC/MassIVE/iProX links, atlas similarity"
    ),
    "disc_catalog_hidden": "catalog hidden",
    "disc_catalog_n": "projects in atlas",
    "atlas_title": "Atlas profile",
    "atlas_lead": f"{BRAND_NAME} summary — metadata only, catalog not exported",
    "atlas_datasets": "datasets",
    "atlas_publications": "unique IDs",
    "atlas_repos": "Repositories",
    "atlas_organs": "Top organs / tissues",
    "atlas_diseases": "Top diseases",
    "atlas_tmt": "TMT plexes",
    "atlas_keywords": "Search keywords",
    "atlas_link": "Registry on GitHub",
    "atlas_discovery": "New dataset analysis",
    "qc_title": "Discovery QC report",
    "qc_lead": "Candidates · manual review · rejected · technical filter",
    "cohorts_title": "Large cohorts — proteomics & multi-omics",
    "cohorts_lead": "Europe PMC + text mining: patients, N, omics, TMT",
}


def en(key: str) -> str:
    if key in _EN:
        return _EN[key]
    if key in _SHARED:
        return _SHARED[key]
    return key


# Back-compat alias — site defaults to English
ru = en
