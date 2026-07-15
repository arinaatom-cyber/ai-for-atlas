"""English fallback strings for static HTML (mirrors site_assets/i18n.js PAGE.en + SHARED)."""
from __future__ import annotations

BRAND_NAME = "Human Cancser Assosiated TMT Proteome Atlas"

_SHARED: dict[str, str] = {
    "brand_title": BRAND_NAME,
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
    "card_open": "Open",
    "card_json": "latest.json (API)",
    "th_link_open": "Open",
    "cell_empty": "—",
}

_EN: dict[str, str] = {
    "brand_sub": "Discovery · Cohorts · QC · read-only catalog",
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
    "card_update_title": "Update data",
    "card_update_desc": "Run: python run_discovery.py scan · publish · export for GitHub Pages",
    "disc_title": "Discovery — full analysis",
    "disc_lead": (
        "New human TMT projects · semantic abstract screening · material QC · data availability"
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
