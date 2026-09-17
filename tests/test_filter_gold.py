from atlas_agent.discovery.filter_gold import evaluate_filter_gold


def test_filter_gold_no_false_includes():
    m = evaluate_filter_gold()
    assert m["fp"] == 0
    assert m["pmid_date_not_strict"] is True
    assert m["pmid_date_is_loose"] is True
    assert m["review_ok"] == m["review_n"]
    assert m["plex_cases_ok"] == m["plex_cases_n"]
    assert m["organism_cases_ok"] == m["organism_cases_n"]
    assert m["precision"] == 1.0
    assert m["recall"] >= 0.5
    assert m["n"] >= 8
    assert m["label_source"] == "unit_cases"
