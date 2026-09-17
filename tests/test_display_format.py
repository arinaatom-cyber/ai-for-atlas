"""Display formatting — capitalization for labels and titles."""

from atlas_agent.viz.display_format import (
    format_bullet_text,
    format_design_label,
    format_metadata_part,
    format_title,
    infer_disease,
    infer_organ,
    sentence_cap,
)


def test_design_label_capitalized():
    assert format_design_label("cancer_only") == "Cancer-only"
    assert format_design_label("case-control") == "Case-control"


def test_metadata_part_not_reported():
    assert format_metadata_part("not reported") == "Not reported"
    assert format_metadata_part("Pediatric/AYA Brain Tumors") == "Pediatric/AYA Brain Tumors"


def test_bullet_design_line():
    assert format_bullet_text("design: cancer_only") == "Design: Cancer-only"


def test_sentence_cap():
    assert sentence_cap("human lung epithelial cells") == "Human lung epithelial cells"
    assert sentence_cap("Этот абстракт подходит") == "Этот абстракт подходит"
    assert sentence_cap("TMT18-labeled proteome") == "TMT18-labeled proteome"
    assert sentence_cap('"human lung" study') == '"Human lung" study'


def test_format_title():
    assert format_title("human tmt colon proteome") == "Human tmt colon proteome"
    assert format_title("tmt-based proteomics of HT-1080 cells").startswith("Tmt")


def test_infer_disease_from_title():
    item = {"title": "Quantitative proteomics of melanoma lymphatic fluid"}
    assert infer_disease(item) == "Melanoma"


def test_infer_organ_from_title():
    item = {"title": "Brain glioma TMT proteomics cohort"}
    assert infer_organ(item) == "Brain"
