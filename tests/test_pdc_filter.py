from atlas_agent.config import load_config
from atlas_agent.discovery.agent import _known_accessions, load_catalog_readonly
from atlas_agent.sources.pdc import (
    REJECT_PLEXES,
    _infer_plex_from_experiment,
    search_pdc_tmt_studies,
)


def test_reject_tmt6_and_tmt18():
    assert _infer_plex_from_experiment("TMT6") == 6
    assert _infer_plex_from_experiment("TMT18") == 18
    assert 6 in REJECT_PLEXES
    assert 18 in REJECT_PLEXES


def test_pdc_excludes_low_plex_and_cptac_program():
    cfg = load_config()
    df = load_catalog_readonly(cfg)
    known = _known_accessions(df, cfg)
    pdc_cfg = (cfg.get("discovery") or {}).get("pdc") or {}

    all_ok = search_pdc_tmt_studies(
        known_accessions=known,
        allowed_plexes=set(pdc_cfg.get("allowed_plexes") or [10, 11, 12, 16]),
        reject_plexes=set(pdc_cfg.get("reject_plexes") or [6, 7, 8, 9, 18]),
        min_channels=int(pdc_cfg.get("min_plex_channels") or 10),
        exclude_programs=[],
    )
    filtered = search_pdc_tmt_studies(
        known_accessions=known,
        allowed_plexes=set(pdc_cfg.get("allowed_plexes") or [10, 11, 12, 16]),
        reject_plexes=set(pdc_cfg.get("reject_plexes") or [6, 7, 8, 9, 18]),
        min_channels=int(pdc_cfg.get("min_plex_channels") or 10),
        exclude_programs=pdc_cfg.get("exclude_programs") or [],
    )

    assert all(p.get("inferred_plex") not in (6, 18) for p in filtered)
    assert all(p.get("inferred_plex", 0) >= 10 for p in filtered)
    assert len(filtered) < len(all_ok)
    assert not any(
        "Clinical Proteomic Tumor" in (p.get("program") or "") for p in filtered
    )
