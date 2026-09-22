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
        require_publication=False,
    )
    filtered = search_pdc_tmt_studies(
        known_accessions=known,
        allowed_plexes=allowed,
        reject_plexes=reject,
        min_channels=int(pdc_cfg.get("min_plex_channels") or 7),
        exclude_programs=pdc_cfg.get("exclude_programs") or [],
        require_publication=False,
    )

    assert all(p.get("inferred_plex") not in reject for p in filtered if p.get("inferred_plex") is not None)
    with_plex = [p for p in filtered if p.get("inferred_plex") is not None]
    assert all(p["inferred_plex"] >= 7 for p in with_plex)
    assert all(p["inferred_plex"] <= 18 for p in with_plex)
    assert len(filtered) < len(all_ok)
def test_pdc_publication_for_study_uses_index():
    from atlas_agent.sources import pdc as pdc_mod

    pdc_mod._PDC_PUB_INDEX = {
        "PDC000606": {"pmid": "41512870", "title": "Gallbladder proteogenomics"}
    }
    rec = pdc_mod.pdc_publication_for_study("pdc000606")
    assert rec and rec["pmid"] == "41512870"


def test_pdc_search_skips_studies_without_article(monkeypatch):
    from atlas_agent.sources import pdc as pdc_mod

    studies = [
        {
            "pdc_study_id": "PDC000001",
            "experiment_type": "TMT10",
            "submitter_id_name": "With paper",
            "program_name": "Other",
        },
        {
            "pdc_study_id": "PDC000002",
            "experiment_type": "TMT10",
            "submitter_id_name": "No paper",
            "program_name": "Other",
        },
    ]
    monkeypatch.setattr(pdc_mod, "fetch_study_summary", lambda: studies)
    pdc_mod._PDC_PUB_INDEX = {
        "PDC000001": {"pmid": "38765432", "title": "A real gallbladder paper"}
    }
    stats: dict = {}
    out = search_pdc_tmt_studies(stats=stats)
    assert [p["accession"] for p in out] == ["PDC000001"]
    assert out[0]["pmid"] == "38765432"
    assert stats.get("skipped_no_publication") == 1
