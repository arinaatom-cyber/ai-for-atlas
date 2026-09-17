from atlas_agent.discovery.tmt_plex import infer_tmt_plex
from atlas_agent.sources.pdc import _infer_plex_from_experiment, _study_to_record


def test_infer_word_and_based_plex():
    assert infer_tmt_plex("sixteen-plex TMT of human tumors") == 16
    assert infer_tmt_plex("TMT-based 16plex proteomics") == 16
    assert infer_tmt_plex("16-channel TMTpro") == 16
    assert infer_tmt_plex("TMTpro 18-channel") == 18
    assert infer_tmt_plex("TMT6 plasma") == 6


def test_pdc_experiment_unspecified_not_dropped_in_record():
    assert _infer_plex_from_experiment("TMT11-Plex") == 11
    rec = _study_to_record(
        {
            "pdc_study_id": "PDC000999",
            "experiment_type": "TMT",
            "submitter_id_name": "Study X",
            "program_name": "CPTAC",
            "disease_type": "Lung adenocarcinoma",
            "analytical_fraction": "Proteome",
            "primary_site": "Lung",
        }
    )
    assert rec["inferred_plex"] is None
    assert rec["tmt_detected"] is True
    assert rec["tmt_plex_unspecified_pdc"] is True
    assert rec["human"] is True
    assert rec.get("human_assumed") is True
