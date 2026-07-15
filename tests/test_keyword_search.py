from atlas_agent.discovery.keyword_search import build_literature_query, default_search_keywords


def test_build_literature_query_includes_years():
    q = build_literature_query(["TMT", "colon cancer"], 2024, 2026)
    assert "PUB_YEAR:[2024 TO 2026]" in q
    assert "TMT" in q


def test_default_keywords_merge_config_and_profile():
    cfg = {"discovery": {"pride_keywords": ["TMT", "isobaric"]}}
    profile = {"search_keywords": ["TMT", "colon", "PDC"]}
    kw = default_search_keywords(cfg, profile)
    assert kw[0] == "TMT"
    assert "colon" in kw
    assert "PDC" in kw
