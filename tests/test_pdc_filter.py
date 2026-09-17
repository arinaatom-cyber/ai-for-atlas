from atlas_agent.config import load_config
from atlas_agent.discovery.agent import _known_accessions, load_catalog_readonly
from atlas_agent.sources.pdc import (
    MIN_ATLAS_CHANNELS,
    REJECT_PLEXES,
    _infer_plex_from_experiment,
    search_pdc_tmt_studies,
)


def test_reject_tmt6_allow_tmt18():
    assert _infer_plex_from_experiment("TMT6") == 6
    assert _infer_plex_from_experiment("TMT7") == 7
    assert _infer_plex_from_experiment("TMT18") == 18
    assert 6 in REJECT_PLEXES
    assert 7 not in REJECT_PLEXES
    assert 18 not in REJECT_PLEXES
    assert MIN_ATLAS_CHANNELS == 7


def test_pdc_excludes_low_plex_and_cptac_program():
    cfg = load_config()
    df = load_catalog_readonly(cfg)
    known = _known_accessions(df, cfg)
    pdc_cfg = (cfg.get("discovery") or {}).get("pdc") or {}
    allowed = set(pdc_cfg.get("allowed_plexes") or list(range(7, 19)))
    reject = set(pdc_cfg.get("reject_plexes") or [2, 6])

    all_ok = search_pdc_tmt_studies(
        known_accessions=known,
        allowed_plexes=allowed,
        reject_plexes=reject,
        min_channels=int(pdc_cfg.get("min_plex_channels") or 7),
        exclude_programs=[],
    )
    filtered = search_pdc_tmt_studies(
        known_accessions=known,
        allowed_plexes=allowed,
        reject_plexes=reject,
        min_channels=int(pdc_cfg.get("min_plex_channels") or 7),
        exclude_programs=pdc_cfg.get("exclude_programs") or [],
    )

    assert all(p.get("inferred_plex") not in reject for p in filtered if p.get("inferred_plex") is not None)
    with_plex = [p for p in filtered if p.get("inferred_plex") is not None]
    assert all(p["inferred_plex"] >= 7 for p in with_plex)
    assert all(p["inferred_plex"] <= 18 for p in with_plex)
    assert len(filtered) < len(all_ok)
    assert not any(
        "Clinical Proteomic Tumor" in (p.get("program") or "") for p in filtered
    )
