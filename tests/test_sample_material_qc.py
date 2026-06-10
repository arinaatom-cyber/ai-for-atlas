"""Unit tests for sample material QC rules."""

from atlas_agent.discovery.sample_material_qc import assess_sample_material





def _item(**kwargs):

    base = {"source": "pride_api", "human": True}

    base.update(kwargs)

    return base





def test_human_tumor_tissue_candidate():

    r = assess_sample_material(_item(title="TMT phosphoproteomics of FFPE tumor tissue from patients"))

    assert r["qc_status"] == "candidate"

    assert "human_tumor_tissue" in r["material_signals"]["included"]





def test_adjacent_normal_candidate():

    r = assess_sample_material(_item(description="paired tumor and adjacent normal tissue TMT 11-plex"))

    assert r["qc_status"] == "candidate"





def test_patient_plasma_candidate():

    r = assess_sample_material(_item(title="Plasma proteomics from cancer patients TMT10"))

    assert r["qc_status"] == "candidate"





def test_cancer_cell_line_candidate():

    r = assess_sample_material(_item(description="Proteomics of MCF7 and A549 cancer cell lines TMT"))

    assert r["qc_status"] == "candidate"





def test_organoid_only_rejected():

    r = assess_sample_material(_item(

        title="Proteomics of patient-derived organoids TMT 11-plex",

        description="3D organoid culture only",

    ))

    assert r["qc_status"] == "rejected"

    assert "3d_model" in r["material_signals"]["excluded"]





def test_spheroid_only_rejected():

    r = assess_sample_material(_item(title="TMT analysis of tumor spheroids"))

    assert r["qc_status"] == "rejected"





def test_mixed_tissue_organoid_manual():

    r = assess_sample_material(_item(

        title="FFPE tumor tissue and matched organoids",

        description="surgical specimen plus patient-derived organoids",

    ))

    assert r["qc_status"] == "requires_manual_check"





def test_pdx_only_rejected():

    r = assess_sample_material(_item(title="TMT proteomics of PDX models in nude mice"))

    assert r["qc_status"] == "rejected"





def test_pdx_with_human_tissue_manual_or_candidate():

    r = assess_sample_material(_item(

        title="Patient tumor tissue and PDX comparison",

        description="FFPE biopsy from patients and xenograft",

    ))

    assert r["qc_status"] in ("candidate", "requires_manual_check")





def test_mouse_tissue_rejected():

    r = assess_sample_material(_item(title="Murine liver proteomics TMT"))

    assert r["qc_status"] == "rejected"





def test_non_human_cell_line_rejected():

    r = assess_sample_material(_item(description="Proteomics of CHO cell line TMT 10-plex"))

    assert r["qc_status"] == "rejected"





def test_msc_rejected():

    r = assess_sample_material(_item(title="Proteomic analysis of hBM-MSCs and derived EVs TMT"))

    assert r["qc_status"] == "rejected"





def test_hcmi_organoids_pdc_rejected():

    r = assess_sample_material(_item(

        source="pdc_api",

        consortium="PDC",

        title="CPTAC-HCMI-Organoids — Human Cancer Models Initiative",

        program="CPTAC-HCMI-Organoids",

    ))

    assert r["qc_status"] == "rejected"





def test_pdc_clinical_tumor_candidate():

    r = assess_sample_material(_item(

        source="pdc_api",

        consortium="PDC",

        title="CPTAC-CCRCC — clear cell renal cell carcinoma",

        disease="Renal Cell Carcinoma",

    ))

    assert r["qc_status"] == "candidate"

    assert "pdc_clinical_tumor" in r["material_signals"]["included"]





def test_unclear_human_manual():

    r = assess_sample_material(_item(

        title="Human clinical proteomics cohort TMT",

        description="homosapiens subjects cohort analysis",

    ))

    assert r["qc_status"] == "requires_manual_check"


